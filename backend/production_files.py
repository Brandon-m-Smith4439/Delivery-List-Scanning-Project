# File: backend/production_files.py
"""Cached access to production hardware, sketch, and fabrication files.

The network-share integration stays isolated from the database layer so normal
scans remain fast and the application can safely run when the production share
is unavailable. v0.473 adds a bounded recent-file index and explicit share-health
diagnostics without moving production binaries into the scanner database.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat as stat_module
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_TEXT_EXTENSIONS = {".txt", ".csv", ".tsv", ".xml", ".json", ".html", ".htm", ".ini", ".log", ".nc", ".nce", ".cnc", ".egl"}
_PREVIEW_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".txt", ".csv"}


def _compact(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", str(value or "").upper())



@dataclass(frozen=True)
class ProductionAsset:
    kind: str
    root: Path
    path: Path
    relative: str
    name: str
    extension: str
    asset_id: str
    search_key: str
    modified_at: float
    machine_hint: str = ""

    def public(self) -> dict[str, Any]:
        return {
            "id": self.asset_id,
            "kind": self.kind,
            "name": self.name,
            "relativePath": self.relative,
            "extension": self.extension,
            "modifiedAt": self.modified_at,
            "previewable": self.extension.lower() in _PREVIEW_EXTENSIONS,
            "machineHint": self.machine_hint,
        }


class ProductionFileService:
    """Read-only, TTL-cached index over the maintained production share."""

    def __init__(self, config: Any, cache_seconds: int = 60) -> None:
        self.config = config
        self.cache_seconds = max(int(cache_seconds or 60), 15)
        self.enabled = True
        self.enforce_staging = True
        # v0.473: only a recent working set is indexed from production shares.
        # This avoids recursively cataloging years of files on every refresh.
        self.lookback_days = 7
        # v0.521: machine definitions are one maintained configuration shared by
        # Lookup Manager, fabrication detection, progress placement, and UI color.
        # Stable codes keep Denver/Waterjet completion evidence compatible while
        # allowing operator-facing names, terms, colors, and progress positions to
        # change without a schema migration.
        self.machine_definitions: list[dict[str, Any]] = [
            {
                "code": "denver", "name": "Denver CNC",
                "terms": ["DENVER", "DENVER CNC"], "color": "#2563eb",
                "progressRank": 0, "active": True, "completionKind": "denver",
            },
            {
                "code": "waterjet", "name": "Waterjet",
                "terms": ["WATER JET", "WATERJET", "WJ"], "color": "#7c3aed",
                "progressRank": 0, "active": True, "completionKind": "waterjet",
            },
        ]
        self.machine_terms: dict[str, list[str]] = {
            row["code"]: list(row["terms"]) for row in self.machine_definitions
        }
        self.machine_colors: dict[str, str] = {
            row["code"]: str(row["color"]) for row in self.machine_definitions
        }
        self.roots: dict[str, Path] = {
            "hardware": Path(config.hardware_lists_dir),
            "sketch": Path(config.sketches_dir),
            "program": Path(config.programs_dir),
            "completed_wj": Path(config.completed_wj_dir),
        }
        self._cache: dict[str, tuple[float, list[ProductionAsset]]] = {}
        self._asset_lookup: dict[str, ProductionAsset] = {}
        # v0.485: once an exact Denver .egl is observed it remains durable fabrication
        # evidence even if the production share later deletes/archives the live file.
        # Historical entries are evidence-only and are never exposed as openable assets.
        self._egl_history: dict[str, tuple[ProductionAsset, float]] = {}
        self._availability_cache: tuple[float, dict[str, bool]] | None = None
        self._availability_errors: dict[str, str] = {}
        # v0.476: resolved production roots are learned only by background/local
        # index work. Settings reads this cache instead of probing mapped shares
        # on the request thread.
        self._resolved_roots: dict[str, str] = {}
        self._fabrication_cache: dict[tuple[str, str, str, bool, str, str], tuple[float, dict[str, Any]]] = {}
        self._fabrication_revision = str(time.time_ns())
        self._fabrication_check_locks = [threading.RLock() for _ in range(16)]
        self._machine_text_cache: dict[str, tuple[float, str]] = {}
        # v0.474: PDF page assignments are parsed lazily per requested order.
        # The share index itself stays metadata-only so hundreds of recent sketches
        # cannot keep the entire application busy while Settings says Refreshing.
        self._sketch_page_cache: dict[str, tuple[float, str, list[dict[str, Any]]]] = {}
        # Empty PDF page maps are kept only briefly in memory. A sketch can be
        # requested while A+W is still copying/writing the PDF on the network
        # share; treating that transient empty parse as durable made Order Details
        # intermittently miss a sketch that existed moments later.
        self._sketch_empty_cache_at: dict[str, float] = {}
        # Exact, operator-requested order PDFs live outside the rolling index.
        # Their metadata/page memory survives both TTL refresh and restart.
        self._requested_sketches: dict[str, ProductionAsset] = {}
        self._sketch_order_checked: dict[str, float] = {}
        self._sketch_order_lock = threading.Lock()
        self._reference_geometry_cache: dict[tuple[str, str, str], tuple[float, dict[str, Any] | None]] = {}
        # v0.516: exact sketch PDF pages that an operator has opened are cached
        # locally under data/. This is a read-through preview cache only; source
        # production files remain authoritative and are never replaced or moved.
        # Keeping the extracted item page locally avoids re-reading a large order
        # PDF from the production share every time Order Details is reopened.
        self._sketch_preview_cache_dir = Path(config.data_dir) / "production-sketch-page-cache"
        self._sketch_preview_lock = threading.Lock()
        self._lock = threading.RLock()
        self._persist_write_lock = threading.Lock()
        self._persist_pending = False
        self._refreshing: set[str] = set()
        self._index_path = Path(config.data_dir) / "production-file-index.json"
        try:
            self._background_refresh_enabled = Path(config.data_dir).resolve().parent == Path(config.root).resolve()
        except OSError:
            self._background_refresh_enabled = False
        self._load_persisted_index()

    def configure(self, settings: dict[str, Any] | None) -> None:
        """Apply persisted Admin settings without exposing storage details to callers."""
        values = settings or {}
        roots = values.get("roots") if isinstance(values.get("roots"), dict) else {}
        path_fields = {
            "hardware": "hardware",
            "sketch": "sketches",
            "program": "programs",
            "completed_wj": "completedWaterjet",
        }
        next_roots = dict(self.roots)
        for kind, field in path_fields.items():
            raw = str(roots.get(field) or "").strip()
            if raw:
                next_roots[kind] = Path(raw).expanduser()
        terms = values.get("machineTerms") if isinstance(values.get("machineTerms"), dict) else {}
        colors = values.get("machineColors") if isinstance(values.get("machineColors"), dict) else {}
        raw_machines = values.get("machines") if isinstance(values.get("machines"), list) else []
        current_by_code = {str(row.get("code") or "").strip().lower(): dict(row) for row in self.machine_definitions}
        next_machines: list[dict[str, Any]] = []
        if raw_machines:
            for raw in raw_machines:
                if not isinstance(raw, dict):
                    continue
                code = re.sub(r"[^a-z0-9_-]+", "-", str(raw.get("code") or "").strip().lower()).strip("-")
                if not code:
                    continue
                previous = current_by_code.get(code, {})
                name = str(raw.get("name") or previous.get("name") or code.replace("-", " ").title()).strip()[:64]
                raw_terms = raw.get("terms", previous.get("terms", terms.get(code, [])))
                if isinstance(raw_terms, str):
                    raw_terms = re.split(r"[,;\n]+", raw_terms)
                cleaned_terms = [str(term or "").strip().upper() for term in (raw_terms or []) if str(term or "").strip()]
                if not cleaned_terms:
                    cleaned_terms = list(previous.get("terms") or [name.upper()])
                fallback_color = str(previous.get("color") or colors.get(code) or "#64748b")
                color = str(raw.get("color") or fallback_color).strip()
                if not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
                    color = fallback_color if re.fullmatch(r"#[0-9A-Fa-f]{6}", fallback_color) else "#64748b"
                try:
                    progress_rank = max(-20, min(int(raw.get("progressRank", previous.get("progressRank", 0))), 50))
                except (TypeError, ValueError):
                    progress_rank = int(previous.get("progressRank") or 0)
                completion_kind = str(previous.get("completionKind") or raw.get("completionKind") or "custom").strip().lower()
                if code == "denver":
                    completion_kind = "denver"
                elif code == "waterjet":
                    completion_kind = "waterjet"
                next_machines.append({
                    "code": code, "name": name, "terms": list(dict.fromkeys(cleaned_terms)),
                    "color": color, "progressRank": progress_rank,
                    "active": bool(raw.get("active", previous.get("active", True))),
                    "completionKind": completion_kind,
                })
        else:
            for code, previous in current_by_code.items():
                raw_terms = terms.get(code, previous.get("terms", []))
                if isinstance(raw_terms, str):
                    raw_terms = re.split(r"[,;\n]+", raw_terms)
                cleaned_terms = [str(term or "").strip().upper() for term in (raw_terms or []) if str(term or "").strip()]
                color = str(colors.get(code) or previous.get("color") or "#64748b").strip()
                next_machines.append({
                    **previous,
                    "terms": list(dict.fromkeys(cleaned_terms)) or list(previous.get("terms") or []),
                    "color": color if re.fullmatch(r"#[0-9A-Fa-f]{6}", color) else str(previous.get("color") or "#64748b"),
                })
        # Denver and Waterjet are maintained system machine identities because
        # their completion evidence comes from dedicated .egl/.nce sources.
        for code, fallback in {
            "denver": {"code":"denver","name":"Denver CNC","terms":["DENVER","DENVER CNC"],"color":"#2563eb","progressRank":0,"active":True,"completionKind":"denver"},
            "waterjet": {"code":"waterjet","name":"Waterjet","terms":["WATER JET","WATERJET","WJ"],"color":"#7c3aed","progressRank":0,"active":True,"completionKind":"waterjet"},
        }.items():
            if not any(row.get("code") == code for row in next_machines):
                next_machines.append(fallback)
        next_terms = {str(row["code"]): list(row.get("terms") or []) for row in next_machines if row.get("active", True)}
        next_colors = {str(row["code"]): str(row.get("color") or "#64748b") for row in next_machines}
        try:
            cache_minutes = max(1, min(int(values.get("cacheMinutes") or max(self.cache_seconds // 60, 1)), 1440))
        except (TypeError, ValueError):
            cache_minutes = max(self.cache_seconds // 60, 1)
        try:
            lookback_days = max(1, min(int(values.get("lookbackDays") or self.lookback_days or 7), 365))
        except (TypeError, ValueError):
            lookback_days = max(int(self.lookback_days or 7), 1)
        with self._lock:
            roots_changed = any(str(next_roots[kind]).casefold() != str(self.roots[kind]).casefold() for kind in self.roots)
            program_root_changed = str(next_roots["program"]).casefold() != str(self.roots["program"]).casefold()
            terms_changed = next_terms != self.machine_terms
            colors_changed = next_colors != self.machine_colors
            machines_changed = next_machines != self.machine_definitions
            lookback_changed = lookback_days != self.lookback_days
            self.enabled = bool(values.get("enabled", True))
            self.enforce_staging = bool(values.get("enforceStaging", True))
            self.cache_seconds = cache_minutes * 60
            self.lookback_days = lookback_days
            self.machine_definitions = next_machines
            self.machine_terms = next_terms
            self.machine_colors = next_colors
            if machines_changed:
                # Presentation/rank/name edits invalidate only lightweight status
                # results; they must not trigger a production-share rescan.
                self._retain_completed_fabrication_memory()
                self._fabrication_revision = str(time.time_ns())
            if roots_changed or lookback_changed:
                self.roots = next_roots
                self._cache.clear()
                self._asset_lookup.clear()
                if program_root_changed:
                    self._egl_history.clear()
                self._availability_cache = None
                self._availability_errors.clear()
                self._resolved_roots.clear()
                self._retain_completed_fabrication_memory()
                self._machine_text_cache.clear()
                self._sketch_page_cache.clear()
                self._sketch_empty_cache_at.clear()
                self._requested_sketches.clear()
                self._sketch_order_checked.clear()
                self._reference_geometry_cache.clear()
                self._load_persisted_index()
            elif terms_changed:
                self._cache.pop("sketch", None)
                for asset_id in [key for key, asset in self._asset_lookup.items() if asset.kind == "sketch"]:
                    self._asset_lookup.pop(asset_id, None)
                self._retain_completed_fabrication_memory()
                self._sketch_page_cache.clear()
                self._sketch_empty_cache_at.clear()
        if roots_changed or lookback_changed:
            self.refresh_async()
        elif terms_changed:
            self.refresh_async(["sketch"])

    def settings_snapshot(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "enforceStaging": self.enforce_staging,
            "cacheMinutes": max(self.cache_seconds // 60, 1),
            "lookbackDays": int(self.lookback_days),
            "roots": {
                "hardware": str(self.roots["hardware"]),
                "sketches": str(self.roots["sketch"]),
                "programs": str(self.roots["program"]),
                "completedWaterjet": str(self.roots["completed_wj"]),
            },
            "machines": [dict(row, terms=list(row.get("terms") or [])) for row in self.machine_definitions],
            "machineTerms": {key: list(values) for key, values in self.machine_terms.items()},
            "machineColors": dict(self.machine_colors),
        }

    def _is_network_root(self, root: Path) -> bool:
        """Treat UNC and non-application Windows drives as remote shares.

        Windows drive syntax is recognized explicitly so ``I:/...`` behaves as
        a mapped production share even when regression tests run on Linux.
        """
        raw = str(root).strip()
        normalized = raw.replace("\\", "/")
        if raw.startswith(("\\\\", "//")):
            return True
        drive_match = re.match(r"^([A-Za-z]):/", normalized)
        if drive_match:
            root_drive = drive_match.group(1).upper()
            app_raw = str(self.config.root).strip().replace("\\", "/")
            app_match = re.match(r"^([A-Za-z]):/", app_raw)
            return not app_match or app_match.group(1).upper() != root_drive
        root_drive = root.drive.upper()
        app_drive = Path(self.config.root).drive.upper()
        return bool(root_drive and app_drive and root_drive != app_drive)

    def _serialize_asset(self, asset: ProductionAsset) -> dict[str, Any]:
        return {
            "relative": asset.relative,
            "name": asset.name,
            "extension": asset.extension,
            "modifiedAt": asset.modified_at,
            "machineHint": asset.machine_hint,
        }

    def _deserialize_asset(self, kind: str, row: dict[str, Any]) -> ProductionAsset | None:
        root = self.roots.get(kind)
        relative = str(row.get("relative") or "").strip()
        if root is None or not relative:
            return None
        path = root / Path(relative)
        name = str(row.get("name") or path.name)
        return ProductionAsset(
            kind=kind,
            root=root,
            path=path,
            relative=relative,
            name=name,
            extension=str(row.get("extension") or path.suffix).lower(),
            asset_id=self._asset_id(kind, relative),
            search_key=_compact(f"{relative} {Path(name).stem}"),
            modified_at=float(row.get("modifiedAt") or 0),
            machine_hint=str(row.get("machineHint") or ""),
        )

    def _load_persisted_index(self) -> None:
        if not self._background_refresh_enabled:
            return
        try:
            payload = json.loads(self._index_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return
        if not isinstance(payload, dict):
            return
        saved_roots = payload.get("roots") if isinstance(payload.get("roots"), dict) else {}
        saved_assets = payload.get("assets") if isinstance(payload.get("assets"), dict) else {}
        indexed_at = float(payload.get("indexedAt") or 0)
        saved_egl_history = payload.get("eglHistory") if isinstance(payload.get("eglHistory"), list) else []
        saved_program_root = str(saved_roots.get("program") or "")
        if saved_program_root.casefold() == str(self.roots.get("program") or "").casefold():
            for row in saved_egl_history:
                if not isinstance(row, dict):
                    continue
                asset = self._deserialize_asset("program", row)
                if not asset or asset.extension != ".egl":
                    continue
                last_seen = float(row.get("lastSeenAt") or indexed_at or asset.modified_at or 0)
                self._egl_history[asset.asset_id] = (asset, last_seen)
        for kind, root in self.roots.items():
            if not self._is_network_root(root):
                continue
            if str(saved_roots.get(kind) or "").casefold() != str(root).casefold():
                continue
            rows = saved_assets.get(kind)
            if not isinstance(rows, list):
                continue
            cutoff = self._recent_cutoff()
            assets = [
                asset
                for row in rows
                if isinstance(row, dict)
                for asset in [self._deserialize_asset(kind, row)]
                if asset
                and asset.modified_at >= cutoff
                and (kind != "completed_wj" or asset.extension == ".nce")
            ]
            self._cache[kind] = (indexed_at, assets)
            for asset in assets:
                self._asset_lookup[asset.asset_id] = asset
        availability = payload.get("availability")
        if isinstance(availability, dict):
            self._availability_cache = (indexed_at, {kind: bool(availability.get(kind)) for kind in self.roots})
        if str(saved_roots.get("sketch") or "").casefold() == str(self.roots["sketch"]).casefold():
            requested = payload.get("requestedSketches")
            for row in (requested if isinstance(requested, list) else [])[:512]:
                if not isinstance(row, dict):
                    continue
                asset = self._deserialize_asset("sketch", row)
                if asset and asset.extension == ".pdf":
                    self._requested_sketches[asset.asset_id] = asset
                    self._asset_lookup[asset.asset_id] = asset
        saved_pages = payload.get("sketchPages")
        if isinstance(saved_pages, list):
            for row in saved_pages:
                if not isinstance(row, dict):
                    continue
                asset_id = str(row.get("assetId") or "")
                order_token = str(row.get("order") or "")
                assignments = row.get("assignments")
                asset = self._asset_lookup.get(asset_id)
                if (
                    not asset
                    or asset.kind != "sketch"
                    or asset.extension != ".pdf"
                    or float(row.get("modifiedAt") or 0) != float(asset.modified_at or 0)
                    or not order_token
                    or not isinstance(assignments, list)
                ):
                    continue
                clean_assignments = [dict(value) for value in assignments if isinstance(value, dict)]
                # Empty page maps are intentionally not restored. They may have
                # been captured while a network PDF was still being written.
                if clean_assignments:
                    self._sketch_page_cache[asset_id] = (asset.modified_at, order_token, clean_assignments)

        # Persist results alongside the existing production index, never in the
        # scanner's transaction tables. Config signatures prevent stale machine
        # settings from reviving a result after a restart.
        self._restore_fabrication_memory(payload)

    def _restore_fabrication_memory(self, payload: dict[str, Any]) -> None:
        memory = payload.get("fabricationMemory") if isinstance(payload, dict) else None
        if isinstance(memory, dict) and memory.get("configuration") == self._fabrication_configuration_signature():
            self._fabrication_revision = str(memory.get("revision") or self._fabrication_revision)
            entries = memory.get("entries")
            for entry in (entries if isinstance(entries, list) else [])[:10000]:
                if not isinstance(entry, dict): continue
                key, result = entry.get("key"), entry.get("result")
                if (isinstance(key, list) and len(key) == 6 and all(isinstance(v, (str, bool)) for v in key)
                        and isinstance(result, dict) and result.get("checkedAt") and result.get("fabricated") is True):
                    self._fabrication_cache[tuple(key)] = (0.0, result)

    def _fabrication_configuration_signature(self) -> str:
        # This is progress memory, not a snapshot of one folder configuration.
        # A path/name/color setting change cannot make a completed physical pane
        # unfinished. Version the memory format itself and let lifecycle keys
        # handle the only valid resets (reject/remake).
        return "v522-production-progress-lifecycle-1"

    def _retain_completed_fabrication_memory(self) -> None:
        self._fabrication_cache = {
            key: value for key, value in self._fabrication_cache.items()
            if value[1].get("fabricated") is True
        }

    @staticmethod
    def _fabrication_lifecycle_signature(label_hint: dict[str, Any] | None) -> str:
        """Identify only events that start a new physical-piece lifecycle.

        Descriptions, dimensions, quantities, jobs, optimization numbers, and
        ordinary source updates may improve classification, but they do not make
        a completed pane become uncut or unfabricated. The store supplies a
        lifecycle revision made from reject/remake evidence and A+W KEYINDEX.
        """
        hint = label_hint if isinstance(label_hint, dict) else {}
        supplied = str(hint.get("lifecycleRevision") or "").strip()
        if supplied:
            return supplied
        return str(hint.get("keyIndex") or "0").strip() or "0"

    def fabrication_revision(self) -> str:
        """Cheap heartbeat token; does not touch production shares."""
        return self._fabrication_revision

    def _persist_index(self) -> None:
        if not self._background_refresh_enabled:
            return
        with self._lock:
            payload = {
                "version": 4,
                "indexedAt": time.time(),
                "lookbackDays": int(self.lookback_days),
                "roots": {kind: str(root) for kind, root in self.roots.items()},
                "availability": dict(self._availability_cache[1]) if self._availability_cache else {},
                "assets": {
                    kind: [self._serialize_asset(asset) for asset in self._cache.get(kind, (0, []))[1]]
                    for kind in self.roots
                },
                "eglHistory": [
                    {**self._serialize_asset(asset), "lastSeenAt": float(last_seen)}
                    for asset, last_seen in self._egl_history.values()
                ],
                "requestedSketches": [self._serialize_asset(asset) for asset in self._requested_sketches.values()],
                "fabricationMemory": {
                    "configuration": self._fabrication_configuration_signature(),
                    "revision": self._fabrication_revision,
                    "entries": [{"key": list(key), "result": result} for key, (_, result) in self._fabrication_cache.items()
                                if key[3] and result.get("checkedAt")][-10000:],
                },
                "sketchPages": [
                    {
                        "assetId": asset_id,
                        "modifiedAt": modified_at,
                        "order": order_token,
                        "assignments": [dict(row) for row in assignments],
                    }
                    for asset_id, (modified_at, order_token, assignments) in self._sketch_page_cache.items()
                    if asset_id in self._asset_lookup and assignments
                ],
            }
        with self._persist_write_lock:
            try:
                self._index_path.parent.mkdir(parents=True, exist_ok=True)
                temporary = self._index_path.with_suffix(".tmp")
                temporary.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
                temporary.replace(self._index_path)
            except OSError:
                # A read-only install can still use the in-memory index.
                return

    def _schedule_persist_index(self, source_root: Path) -> None:
        """Persist newly discovered PDF page matches away from request threads."""
        if not self._background_refresh_enabled:
            return
        with self._lock:
            if self._persist_pending:
                return
            self._persist_pending = True

        def worker() -> None:
            try:
                # Coalesce adjacent item lookups from one order-detail request.
                time.sleep(0.2)
                self._persist_index()
            finally:
                with self._lock:
                    self._persist_pending = False

        threading.Thread(target=worker, name="production-index-persist", daemon=True).start()

    def _recent_cutoff(self) -> float:
        """Return the oldest file timestamp retained by the production index."""
        return time.time() - (max(int(self.lookback_days or 7), 1) * 86400)

    @staticmethod
    def _normalized_folder_name(value: Any) -> str:
        """Normalize a production folder label without hiding meaningful names.

        Windows shares occasionally contain repeated spaces that are difficult
        to spot in Explorer (for example ``Completed  WJ``). Matching sibling
        directories by collapsed whitespace/case keeps a legacy saved path from
        failing while still exposing the exact resolved path to administrators.
        """
        return re.sub(r"\s+", " ", str(value or "").strip()).casefold()

    def _resolve_root_alias(self, root: Path) -> Path:
        """Resolve one missing child to a uniquely equivalent sibling name."""
        try:
            if root.is_dir():
                return root
        except OSError:
            pass
        parent = root.parent
        try:
            if not parent.is_dir():
                return root
            target = self._normalized_folder_name(root.name)
            matches = [entry for entry in parent.iterdir() if entry.is_dir() and self._normalized_folder_name(entry.name) == target]
        except OSError:
            return root
        return matches[0] if len(matches) == 1 else root

    def _probe_root(self, kind: str, root: Path) -> tuple[bool, str]:
        """Return share reachability plus a path-specific Admin failure reason.

        v0.475 deliberately separates a missing child folder from a missing
        mapped drive. Hardware, Sketches, Programs, and Completed WJ commonly
        share the same mapped production root; if the parent is reachable, a
        FileNotFoundError for just one child must not blame the whole drive.
        """
        try:
            root.stat()
        except PermissionError:
            return False, "Access denied"
        except FileNotFoundError:
            raw = str(root).strip().replace("\\", "/")
            is_windows_mapped = bool(re.match(r"^[A-Za-z]:/", raw) and self._is_network_root(root))
            if is_windows_mapped:
                parent = root.parent
                try:
                    parent_stat = parent.stat()
                except PermissionError:
                    return False, f"Parent folder access denied: {parent}"
                except FileNotFoundError:
                    # A non-Windows test host cannot meaningfully probe an I:\n                    # mapping: pathlib eventually resolves the lexical parent to
                    # the local working directory. Preserve mapped-drive semantics
                    # there; production Windows hosts can inspect real ancestors.
                    if os.name != "nt":
                        return False, "Mapped drive not reachable; use a UNC path if needed"
                    # Walk upward only until a reachable ancestor or drive root
                    # is found. This probe runs on the background index thread,
                    # never on the scanner request/transaction hot path.
                    current = parent
                    while current != current.parent:
                        current = current.parent
                        try:
                            current.stat()
                            return False, f"Folder not found below reachable path: {current}"
                        except PermissionError:
                            return False, f"Parent folder access denied: {current}"
                        except FileNotFoundError:
                            continue
                        except OSError as exc:
                            reason = str(getattr(exc, "strerror", "") or exc or "Folder unavailable").strip()
                            return False, reason[:500]
                    return False, "Mapped drive not reachable; use a UNC path if needed"
                except OSError as exc:
                    reason = str(getattr(exc, "strerror", "") or exc or "Folder unavailable").strip()
                    return False, reason[:500]
                if stat_module.S_ISDIR(parent_stat.st_mode):
                    return False, f"Folder not found; parent is reachable: {parent}"
                return False, f"Parent path is not a folder: {parent}"
            return False, "Folder not found"
        except OSError as exc:
            reason = str(getattr(exc, "strerror", "") or exc or "Folder unavailable").strip()
            return False, reason[:500]
        if not root.is_dir():
            return False, "Path is not a folder"
        return True, ""

    def _set_kind_availability(self, kind: str, available: bool, error: str = "") -> None:
        """Publish reachability before a potentially slower background index completes."""
        now = time.time()
        with self._lock:
            values = dict(self._availability_cache[1]) if self._availability_cache else {}
            values[kind] = bool(available)
            self._availability_cache = (now, values)
            if error:
                self._availability_errors[kind] = str(error)[:500]
            else:
                self._availability_errors.pop(kind, None)

    def _known_recent_directories(self, kind: str, root: Path, cutoff: float) -> set[str]:
        """Keep ancestors of already-indexed recent files eligible for incremental rescans."""
        with self._lock:
            cached_assets = list(self._cache.get(kind, (0, []))[1])
        known: set[str] = set()
        root_key = os.path.normcase(os.path.normpath(str(root)))
        for asset in cached_assets:
            if asset.modified_at < cutoff:
                continue
            current = Path(asset.path).parent
            guard = 0
            while guard < 32:
                current_key = os.path.normcase(os.path.normpath(str(current)))
                if current_key == root_key:
                    break
                known.add(current_key)
                parent = current.parent
                if parent == current:
                    break
                current = parent
                guard += 1
        return known

    def _replace_kind_cache(self, kind: str, assets: list[ProductionAsset], available: bool) -> None:
        now = time.time()
        with self._lock:
            previous = {a.asset_id: a for a in self._cache.get(kind, (0, []))[1]}
            changed = [a for a in assets if a.asset_id not in previous or a.modified_at != previous[a.asset_id].modified_at]
            removed = set(previous) - {a.asset_id for a in assets} if available else set()
            was_available = bool(self._availability_cache and self._availability_cache[1].get(kind))
            if kind == "program":
                for asset in assets:
                    if asset.extension == ".egl":
                        self._egl_history[asset.asset_id] = (asset, now)
            self._cache[kind] = (now, assets)
            prefix = f"{kind}-"
            for asset_id in [key for key in self._asset_lookup if key.startswith(prefix)]:
                self._asset_lookup.pop(asset_id, None)
            for asset in assets:
                self._asset_lookup[asset.asset_id] = asset
            if kind == "sketch":
                self._asset_lookup.update(self._requested_sketches)
            availability = dict(self._availability_cache[1]) if self._availability_cache else {}
            availability[kind] = bool(available)
            self._availability_cache = (now, availability)
            if kind in {"sketch", "program", "completed_wj"} and (changed or removed or was_available != available):
                tokens = set()
                for asset in changed:
                    for token in re.findall(r"\d{6,12}", asset.relative):
                        tokens.update((token, token[:6], token[:8]))
                for key, (_, result) in list(self._fabrication_cache.items()):
                    evidence = result.get("evidence") or {}
                    if evidence.get("id") in removed and result.get("fabricated") is True:
                        result["evidence"] = {**evidence, "historical": True, "existsNow": False}
                    result["programs"] = [a for a in result.get("programs", []) if a.get("id") not in removed]
                    result["completedWaterjet"] = [{**a, "historical": True, "existsNow": False} if a.get("id") in removed else a
                                                    for a in result.get("completedWaterjet", [])]
                    identity_tokens = {_compact(value) for value in result.get("identityTokens", []) if _compact(value)}
                    if result.get("fabricated") is not True and (
                        key[0] in tokens or bool(identity_tokens.intersection(tokens))
                        or (available and result.get("fabricated") is None)
                    ):
                        self._fabrication_cache.pop(key, None)
                self._fabrication_revision = str(time.time_ns())

    def _refresh_kind(self, kind: str) -> None:
        configured_root = self.roots[kind]
        resolved_root = self._resolve_root_alias(configured_root)
        try:
            # Reachability is published as soon as the background worker can open
            # the configured root. v0.476 also tolerates repeated-space/case
            # differences in the final folder component (e.g. Completed  WJ).
            available, availability_error = self._probe_root(kind, resolved_root)
            if available and str(resolved_root) != str(configured_root):
                availability_error = f"Resolved configured path to: {resolved_root}"
            with self._lock:
                self._resolved_roots[kind] = str(resolved_root)
            self._set_kind_availability(kind, available, availability_error)
            assets = self._walk_root(kind, resolved_root) if available else []
            self._replace_kind_cache(kind, assets, available)
            self._persist_index()
        finally:
            with self._lock:
                self._refreshing.discard(kind)

    def refresh_async(self, kinds: list[str] | None = None) -> None:
        """Refresh production shares without blocking a request or scanner transaction."""
        if not self.enabled or not self._background_refresh_enabled:
            return
        for kind in kinds or list(self.roots):
            if kind not in self.roots:
                continue
            with self._lock:
                if kind in self._refreshing:
                    continue
                self._refreshing.add(kind)
            threading.Thread(
                target=self._refresh_kind,
                args=(kind,),
                name=f"production-index-{kind}",
                daemon=True,
            ).start()

    def index_status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "refreshing": sorted(self._refreshing),
                "counts": {kind: len(self._cache.get(kind, (0, []))[1]) for kind in self.roots},
                "indexedAt": max((cached[0] for cached in self._cache.values()), default=0),
                "indexPath": str(self._index_path),
                "lookbackDays": int(self.lookback_days),
                "historicalEglCount": len(self._egl_history),
                "errors": dict(self._availability_errors),
                "resolvedRoots": {kind: self._resolved_roots.get(kind, str(root)) for kind, root in self.roots.items()},
            }

    def availability(self, *, refresh: bool = False) -> dict[str, bool]:
        """Return cached share availability so disconnected drives do not stall hot paths."""
        if not self.enabled:
            return {kind: False for kind in self.roots}
        now = time.time()
        if not any(self._is_network_root(root) for root in self.roots.values()):
            values: dict[str, bool] = {}
            errors: dict[str, str] = {}
            for kind, root in self.roots.items():
                resolved_root = self._resolve_root_alias(root)
                available, error = self._probe_root(kind, resolved_root)
                values[kind] = available
                if error:
                    errors[kind] = error
            self._availability_cache = (now, values)
            self._availability_errors = errors
            return dict(values)
        with self._lock:
            cached = self._availability_cache
        if cached and not refresh:
            if now - cached[0] >= self.cache_seconds:
                self.refresh_async()
            return {kind: bool(cached[1].get(kind)) for kind in self.roots}
        self.refresh_async()
        return {kind: bool(cached and cached[1].get(kind)) for kind in self.roots}

    def _asset_id(self, kind: str, relative: str) -> str:
        digest = hashlib.sha256(f"{kind}\0{relative}".encode("utf-8", "ignore")).hexdigest()[:24]
        return f"{kind}-{digest}"

    def _walk_root(self, kind: str, root: Path) -> list[ProductionAsset]:
        """Index only the configured recent window and prune old directory trees.

        A network filesystem still has to enumerate a directory's immediate
        entries to learn their timestamps, but v0.473 no longer recursively
        descends into old subtrees or stats/indexes old files. Newly-created
        production files update their containing directory timestamp, while
        ancestors of already-known recent files are also revisited.
        """
        if not root.exists() or not root.is_dir():
            return []
        cutoff = self._recent_cutoff()
        known_dirs = self._known_recent_directories(kind, root, cutoff)
        assets: list[ProductionAsset] = []
        stack = [root]
        visited: set[str] = set()

        while stack:
            folder = stack.pop()
            folder_key = os.path.normcase(os.path.normpath(str(folder)))
            if folder_key in visited:
                continue
            visited.add(folder_key)
            try:
                entries = list(os.scandir(folder))
            except OSError:
                continue

            for entry in entries:
                try:
                    if entry.is_dir(follow_symlinks=False):
                        stat = entry.stat(follow_symlinks=False)
                        child_key = os.path.normcase(os.path.normpath(entry.path))
                        if float(stat.st_mtime or 0) >= cutoff or child_key in known_dirs:
                            stack.append(Path(entry.path))
                        continue
                    if not entry.is_file(follow_symlinks=False):
                        continue
                    stat = entry.stat(follow_symlinks=False)
                except OSError:
                    continue

                modified_at = float(stat.st_mtime or 0)
                if modified_at < cutoff:
                    continue
                path = Path(entry.path)
                extension = path.suffix.lower()
                # Completed WJ uses .nce as the authoritative proof that the
                # order/item was actually run on the Waterjet. Ignore unrelated
                # recent exports instead of treating their presence as completion.
                if kind == "completed_wj" and extension != ".nce":
                    continue
                try:
                    relative = path.relative_to(root).as_posix()
                except ValueError:
                    continue
                # v0.474: indexing is intentionally metadata-only. Sketch PDF
                # parsing happens lazily for a requested order/item and is cached.
                # This keeps folder refresh quick even when hundreds of recent
                # sketches exist on the production share.
                assets.append(ProductionAsset(
                    kind=kind,
                    root=root,
                    path=path,
                    relative=relative,
                    name=path.name,
                    extension=extension,
                    asset_id=self._asset_id(kind, relative),
                    search_key=_compact(f"{relative} {path.stem}"),
                    modified_at=modified_at,
                ))

        assets.sort(key=lambda asset: (-asset.modified_at, asset.relative.lower()))
        return assets

    def assets(self, kind: str, *, refresh: bool = False) -> list[ProductionAsset]:
        clean_kind = str(kind or "").strip().lower()
        root = self.roots.get(clean_kind)
        if root is None or not self.enabled:
            return []
        now = time.time()
        with self._lock:
            cached = self._cache.get(clean_kind)
        if self._is_network_root(root):
            if refresh or not cached or now - cached[0] >= self.cache_seconds:
                self.refresh_async([clean_kind])
            return list(cached[1]) if cached else []
        if not refresh and cached and now - cached[0] < self.cache_seconds:
            return list(cached[1])
        resolved_root = self._resolve_root_alias(root)
        with self._lock:
            self._resolved_roots[clean_kind] = str(resolved_root)
        available = resolved_root.exists() and resolved_root.is_dir()
        values = self._walk_root(clean_kind, resolved_root) if available else []
        self._replace_kind_cache(clean_kind, values, available)
        return list(values)

    def resolve_asset(self, asset_id: str) -> ProductionAsset | None:
        clean = str(asset_id or "").strip()
        if not clean:
            return None
        asset = self._asset_lookup.get(clean)
        if asset and asset.path.exists():
            return asset
        kind = clean.split("-", 1)[0]
        for candidate in self.assets(kind, refresh=False):
            if candidate.asset_id == clean and candidate.path.exists():
                return candidate
        return None

    def _sketch_preview_cache_path(self, asset: ProductionAsset, page_number: int) -> Path:
        signature = f"{asset.asset_id}|{float(asset.modified_at or 0):.6f}|{int(page_number)}"
        digest = hashlib.sha256(signature.encode("utf-8")).hexdigest()
        return self._sketch_preview_cache_dir / f"{digest}.pdf"

    def cached_sketch_page(self, asset_id: str, page_number: int) -> tuple[Path, ProductionAsset] | None:
        """Return/create one exact sketch page in the local read-through cache.

        The cache is keyed by source asset id + source mtime + page, so a revised
        production PDF automatically receives a new cached page. A previously
        cached page can still be served when the network share is temporarily
        unavailable, provided the persisted production index still identifies the
        original asset metadata.
        """
        clean = str(asset_id or "").strip()
        page = max(int(page_number or 0), 0)
        if not clean or page <= 0:
            return None
        asset = self._asset_lookup.get(clean)
        if asset is None:
            kind = clean.split("-", 1)[0]
            # A network-backed persisted index can restore metadata before the
            # share is reachable; ``assets`` is non-blocking for network roots.
            for candidate in self.assets(kind, refresh=False):
                if candidate.asset_id == clean:
                    asset = candidate
                    break
        if asset is None or asset.kind != "sketch" or asset.extension.lower() != ".pdf":
            return None
        target = self._sketch_preview_cache_path(asset, page)
        if target.exists() and target.is_file() and target.stat().st_size > 0:
            return target, asset
        if not asset.path.exists():
            return None

        with self._sketch_preview_lock:
            if target.exists() and target.is_file() and target.stat().st_size > 0:
                return target, asset
            try:
                from pypdf import PdfReader, PdfWriter  # type: ignore

                reader = PdfReader(str(asset.path))
                page_index = page - 1
                if page_index < 0 or page_index >= len(reader.pages):
                    return None
                writer = PdfWriter()
                writer.add_page(reader.pages[page_index])
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_suffix(f".{os.getpid()}.{threading.get_ident()}.tmp")
                try:
                    with temporary.open("wb") as handle:
                        writer.write(handle)
                    temporary.replace(target)
                finally:
                    try:
                        temporary.unlink()
                    except FileNotFoundError:
                        pass
                    except OSError:
                        pass
            except Exception:
                return None
        return (target, asset) if target.exists() and target.stat().st_size > 0 else None


    def _asset_mentions_item(self, asset: ProductionAsset, order: Any, item: Any) -> bool:
        """Require item evidence tied to the order, avoiding date/revision digit false positives."""
        raw_item = str(item or "").strip()
        if not raw_item:
            return True

        raw_path = asset.relative.upper()
        path_parts = [part for part in raw_path.replace("\\", "/").split("/") if part]
        file_stem = Path(asset.name).stem.upper()
        order_token = _compact(order)
        item_digits = re.sub(r"\D+", "", raw_item)
        if item_digits:
            try:
                number = str(int(item_digits))
            except ValueError:
                number = item_digits.lstrip("0") or "0"
            item_pattern = re.compile(rf"(?<!\d)0*{re.escape(number)}(?!\d)")
            padded = item_digits.zfill(3)

            # Common production naming places order + item in the same filename
            # (or concatenates them). Require that relationship rather than
            # accepting any standalone digit elsewhere in a dated folder path.
            if order_token and order_token in _compact(file_stem) and item_pattern.search(file_stem):
                return True
            # Plant program naming uses six-digit Order Nr. + two-digit Item
            # (238001 item 1 -> 23800101, item 2 -> 23800102). Keep the older
            # three-digit form too for backward compatibility.
            if order_token and f"{order_token}{number.zfill(2)}" in _compact(file_stem):
                return True
            if order_token and f"{order_token}{padded}" in asset.search_key:
                return True

            # Also support order/item directory layouts such as 123456/001/file.
            # The numeric item folder must sit directly beside the order folder.
            for index, part in enumerate(path_parts):
                compact_part = _compact(part)
                if not item_pattern.fullmatch(part) and compact_part != padded:
                    continue
                neighbors = path_parts[max(0, index - 1): index] + path_parts[index + 1: index + 2]
                if order_token and any(order_token in _compact(neighbor) for neighbor in neighbors):
                    return True

        compact_item = _compact(raw_item)
        if compact_item and not compact_item.isdigit():
            item_pattern = re.compile(rf"(?<![A-Z0-9]){re.escape(raw_item.upper())}(?![A-Z0-9])")
            if order_token and order_token in _compact(file_stem) and item_pattern.search(file_stem):
                return True
        return False

    def _score(
        self,
        asset: ProductionAsset,
        order: Any,
        item: Any = "",
        job: Any = "",
        *,
        require_item: bool = False,
    ) -> int:
        order_token = _compact(order)
        job_tokens = self._job_identity_tokens(job)
        key = asset.search_key
        order_match = bool(order_token and order_token in key)
        matched_job = next((token for token in job_tokens if token and token in key), "")
        if not order_match and not matched_job:
            return 0

        # Order Nr. remains the strongest identity. Job Nr. is an explicit
        # secondary plant identity because Denver/WaterJet files are sometimes
        # named only with the Job Nr. rather than the scanner Order Nr.
        score = 100 if order_match else 78
        if matched_job:
            score += 22 if order_match else 0

        if str(item or "").strip():
            item_match = self._asset_mentions_item(asset, order, item)
            if not item_match and matched_job:
                item_match = self._asset_mentions_item(asset, matched_job, item)

            # Some completed machine files are named exactly as the Job Nr. with
            # no Order/Item suffix. For machine evidence only, an exact Job Nr.
            # filename is an accepted lower-confidence item identity; sketches
            # still require their page-level Order.Item marker.
            exact_job_machine_file = bool(
                matched_job
                and asset.kind in {"program", "completed_wj"}
                and _compact(Path(asset.name).stem) == matched_job
            )
            if require_item and not item_match and not exact_job_machine_file:
                return 0
            if item_match:
                score += 70
            elif exact_job_machine_file:
                score += 35
            else:
                score -= 15

        if asset.extension in {".egl", ".nce"}:
            score += 8
        return score

    def matches(
        self,
        kind: str,
        order: Any,
        item: Any = "",
        job: Any = "",
        limit: int = 8,
        *,
        require_item: bool = False,
        refresh: bool = False,
    ) -> list[ProductionAsset]:
        scored: list[tuple[int, float, ProductionAsset]] = []
        candidates = {a.asset_id: a for a in self.assets(kind, refresh=refresh)}
        if kind == "sketch":
            with self._lock:
                candidates.update(self._requested_sketches)
        for asset in candidates.values():
            score = self._score(asset, order, item, job, require_item=require_item)
            if score > 0:
                scored.append((score, asset.modified_at, asset))
        scored.sort(key=lambda row: (-row[0], -row[1], row[2].relative.lower()))
        return [asset for _score, _mtime, asset in scored[: max(int(limit or 8), 1)]]

    def search_hardware(self, query: str, limit: int = 30) -> list[dict[str, Any]]:
        tokens = [_compact(part) for part in re.split(r"\s+", str(query or "").strip()) if _compact(part)]
        if not tokens:
            return []
        rows = []
        for asset in self.assets("hardware"):
            if all(token in asset.search_key for token in tokens):
                rows.append(asset.public())
            if len(rows) >= max(1, int(limit or 30)):
                break
        return rows

    def _read_machine_text(self, asset: ProductionAsset, max_bytes: int = 2_000_000) -> str:
        cached = self._machine_text_cache.get(asset.asset_id)
        if cached and cached[0] == asset.modified_at:
            return cached[1]

        text = ""
        if asset.extension == ".pdf":
            # Digital A+W/shop sketches normally carry selectable machine text.
            # Use pypdf opportunistically when it exists on the scanner host; it
            # remains an optional enhancement so deployment does not gain a new
            # required package. Image-only PDFs stay unknown (no OCR/guessing).
            try:
                from pypdf import PdfReader  # type: ignore

                reader = PdfReader(str(asset.path))
                chunks: list[str] = []
                for page in reader.pages[:8]:
                    chunks.append(page.extract_text() or "")
                    if sum(len(chunk) for chunk in chunks) >= max_bytes:
                        break
                text = "\n".join(chunks)[:max_bytes]
            except Exception:
                text = ""

        if not text:
            try:
                with asset.path.open("rb") as handle:
                    raw = handle.read(max_bytes)
            except OSError:
                return ""
            if asset.extension in _TEXT_EXTENSIONS:
                text = raw.decode("utf-8", "ignore")
            else:
                # Some PDFs/documents expose uncompressed ASCII labels. This is
                # a lightweight fallback only; uncertain content stays unknown.
                text = raw.decode("latin-1", "ignore")

        self._machine_text_cache[asset.asset_id] = (asset.modified_at, text)
        return text

    def _matches_machine_terms(self, signals: str, machine: str) -> bool:
        normalized = str(signals or "").upper()
        for term in self.machine_terms.get(machine, []):
            clean = str(term or "").strip().upper()
            if not clean:
                continue
            if len(clean) <= 3:
                if re.search(rf"(?<![A-Z0-9]){re.escape(clean)}(?![A-Z0-9])", normalized):
                    return True
            elif clean in normalized:
                return True
        return False

    def _machine_definition(self, code_or_name: Any) -> dict[str, Any] | None:
        token = str(code_or_name or "").strip().casefold()
        if not token:
            return None
        for row in self.machine_definitions:
            code = str(row.get("code") or "").strip().casefold()
            name = str(row.get("name") or "").strip().casefold()
            if token in {code, name}:
                return row
            if code == "denver" and token in {"denver cnc", "denver"}:
                return row
            if code == "waterjet" and token in {"waterjet", "water jet", "wj"}:
                return row
        return None

    def _machine_name(self, code_or_name: Any) -> str:
        row = self._machine_definition(code_or_name)
        return str(row.get("name") or "").strip() if row else str(code_or_name or "").strip()

    def _machine_code(self, code_or_name: Any) -> str:
        row = self._machine_definition(code_or_name)
        return str(row.get("code") or "").strip() if row else ""

    def _detect_machine(self, signals: str) -> str:
        """Resolve one configured sketch/label assignment without request-wide scans."""
        for row in self.machine_definitions:
            if row.get("active", True) and self._matches_machine_terms(signals, str(row.get("code") or "")):
                return str(row.get("name") or "").strip()
        return ""

    @staticmethod
    def _fabrication_hint_signature(label_hint: dict[str, Any] | None) -> str:
        """Return a stable small cache signature for A+W Cutting Label evidence."""
        if not isinstance(label_hint, dict) or not label_hint:
            return ""
        try:
            payload = json.dumps(label_hint, sort_keys=True, separators=(",", ":"), default=str)
        except (TypeError, ValueError):
            payload = str(label_hint)
        return hashlib.sha256(payload.encode("utf-8", errors="ignore")).hexdigest()[:20]

    @staticmethod
    def _pdf_annotation_text(page: Any) -> str:
        """Read operator-entered PDF markup text that ``extract_text`` can miss.

        Manual shop edits are often stored as annotation ``/Contents`` rather
        than flattened page text. Reading only these tiny metadata fields keeps
        this deferred Order Details parse bounded and avoids OCR/image work.
        """
        values: list[str] = []
        try:
            annotations = page.get("/Annots") or []
        except Exception:
            annotations = []
        for reference in annotations:
            try:
                annotation = reference.get_object() if hasattr(reference, "get_object") else reference
            except Exception:
                continue
            if not hasattr(annotation, "get"):
                continue
            for key in ("/Contents", "/RC", "/Subj", "/T"):
                try:
                    value = annotation.get(key)
                except Exception:
                    value = None
                text = str(value or "").strip()
                if text:
                    values.append(text)
        return "\n".join(values)

    def _label_fabrication_assignment(self, label_hint: dict[str, Any] | None) -> dict[str, Any]:
        """Infer fabrication requirements from synchronized A+W Cutting Label data.

        Machine text on the label is authoritative when present. The one
        evidence-backed shop rule added in v0.518 is narrower: any Mirror with
        an internal cutout/cutout macro requires Waterjet. Generic fabrication
        operations are marked as required without inventing Denver/Waterjet when
        the A+W row does not identify the machine.
        """
        hint = label_hint if isinstance(label_hint, dict) else {}
        product = str(hint.get("productDescription") or hint.get("product") or "").strip()
        process_rows = hint.get("processRows") if isinstance(hint.get("processRows"), list) else []
        fields: list[str] = [product]
        for row in process_rows:
            if not isinstance(row, dict):
                continue
            fields.extend(str(row.get(key) or "").strip() for key in (
                "machine", "workType", "processProductDescription", "edgeData"
            ))
        signal = "\n".join(value for value in fields if value).upper()
        if not signal:
            return {"machine": "", "required": False, "confidence": "unknown", "reason": "", "signal": ""}

        explicit_machine = self._detect_machine(signal)
        if explicit_machine:
            return {
                "machine": explicit_machine, "required": True, "confidence": "label-machine",
                "reason": "A+W Cutting Label identifies the fabrication machine", "signal": signal[:600],
            }

        is_mirror = bool(re.search(r"\bMIRROR\b", product, flags=re.IGNORECASE))
        # Mirrors are not routed through the Denver workflow for cutouts. The
        # A+W label may describe the same operation as an internal cutout macro,
        # hole, drill, notch, or slot, so accept those concrete geometry terms
        # instead of relying on one exact phrase.
        has_cutout = bool(re.search(
            r"\bINTERNAL\s+CUT(?:\s*OUT|OUT)\b|\bCUT\s*OUT\b|\bCUTOUT\b|"
            r"\bHOLE(?:S)?\b|\bDRILL(?:ED|ING)?\b|\bNOTCH(?:ES|ED|ING)?\b|"
            r"\bSLOT(?:S|TED|TING)?\b",
            signal,
            flags=re.IGNORECASE,
        ))
        if is_mirror and has_cutout:
            return {
                "machine": self._machine_name("waterjet"), "required": True, "confidence": "label-mirror-cutout",
                "reason": "Mirror with an A+W cutout operation requires Waterjet", "signal": signal[:600],
            }

        generic_fabrication = bool(re.search(
            r"\bFABRICAT(?:E|ED|ING|ION)?\b|\bDRILL(?:ED|ING)?\b|\bHOLE(?:S)?\b|"
            r"\bNOTCH(?:ES|ED|ING)?\b|\bSLOT(?:S|TED|TING)?\b|\bCUT\s*OUT\b|\bCUTOUT\b",
            signal, flags=re.IGNORECASE,
        ))
        if generic_fabrication:
            return {
                "machine": "Fabrication", "required": True, "confidence": "label-required",
                "reason": "A+W Cutting Label contains a fabrication operation; machine needs review", "signal": signal[:600],
            }
        return {"machine": "", "required": False, "confidence": "unknown", "reason": "", "signal": signal[:600]}

    @staticmethod
    def _normalized_item_number(item: Any) -> str:
        digits = re.sub(r"\D+", "", str(item or "").strip())
        if not digits:
            return ""
        try:
            return str(int(digits))
        except ValueError:
            return digits.lstrip("0") or "0"

    def _sketch_page_assignments(
        self,
        asset: ProductionAsset,
        order: Any,
        *,
        allow_content_read: bool = True,
    ) -> list[dict[str, Any]]:
        """Map digital sketch PDF pages to exact Order.Item markers and machines.

        Plant sketches are order-level files. The authoritative item identity is
        the blue center text on each page (for example ``238245.2``), and WJ or
        DENVER text on that same page determines the assigned machine. Parsing is
        lazy/cached so the background share index never has to read every PDF.
        """
        order_token = re.sub(r"\D+", "", str(order or "").strip())
        if not order_token or asset.extension != ".pdf":
            return []
        cached = self._sketch_page_cache.get(asset.asset_id)
        if cached and cached[0] == asset.modified_at and cached[1] == order_token:
            if cached[2]:
                return [dict(row) for row in cached[2]]
            # Reuse an empty parse only long enough to coalesce adjacent item
            # lookups from one Order Details request. After that, try the PDF
            # again because A+W/network copies can become readable moments later.
            empty_at = float(self._sketch_empty_cache_at.get(asset.asset_id) or 0)
            if empty_at and time.time() - empty_at < 3.0:
                return []
            self._sketch_page_cache.pop(asset.asset_id, None)
            self._sketch_empty_cache_at.pop(asset.asset_id, None)
        if not allow_content_read:
            return []

        assignments: list[dict[str, Any]] = []
        parse_succeeded = False
        try:
            from pypdf import PdfReader  # type: ignore

            reader = PdfReader(str(asset.path))
            # Canonical shop pages use ``Order.Item``. Manual markups sometimes
            # rewrite that identity as ``Order / Item`` or ``Order ITEM n``; accept
            # those explicit separators without treating arbitrary nearby numbers
            # (dimensions/page counts) as item identities. Annotation text is also
            # included because Bluebeam/Acrobat machine notes may not be flattened.
            marker_patterns = [
                re.compile(rf"(?<!\d){re.escape(order_token)}\s*\.\s*0*(\d{{1,3}})(?!\d)", re.IGNORECASE),
                re.compile(rf"(?<!\d)(?:ORDER\s*)?{re.escape(order_token)}\s*(?:[/#-]\s*|ITEM\s*(?:NR\.?|NO\.?|#)?\s*)0*(\d{{1,3}})(?!\d)", re.IGNORECASE),
            ]
            for page_index, page in enumerate(reader.pages):
                try:
                    text = page.extract_text() or ""
                except Exception:
                    text = ""
                annotation_text = self._pdf_annotation_text(page)
                if annotation_text:
                    text = "\n".join(part for part in (text, annotation_text) if part)
                if not text:
                    continue
                machine = self._detect_machine(text)
                page_items: set[str] = set()
                for marker in marker_patterns:
                    for match in marker.finditer(text):
                        item_number = self._normalized_item_number(match.group(1))
                        if not item_number or item_number in page_items:
                            continue
                        page_items.add(item_number)
                        assignments.append({
                            "item": item_number,
                            "marker": f"{order_token}.{item_number}",
                            "pageNumber": page_index + 1,
                            "machine": machine,
                        })
            parse_succeeded = True
        except Exception:
            # A locked/partially copied network PDF is not authoritative evidence
            # that no sketch exists. Leave it uncached so the bounded frontend
            # retry can recover without waiting for a process restart.
            return []

        # Keep one deterministic page per item when a PDF happens to repeat a
        # title/marker in annotations or revision notes.
        unique: dict[str, dict[str, Any]] = {}
        for row in assignments:
            unique.setdefault(str(row.get("item") or ""), row)
        result = list(unique.values())
        if parse_succeeded:
            self._sketch_page_cache[asset.asset_id] = (asset.modified_at, order_token, [dict(row) for row in result])
            if result:
                self._sketch_empty_cache_at.pop(asset.asset_id, None)
                self._schedule_persist_index(asset.root)
            else:
                self._sketch_empty_cache_at[asset.asset_id] = time.time()
        return result

    def _public_asset_view(
        self,
        asset: ProductionAsset,
        *,
        page_number: int = 0,
        item_marker: str = "",
        machine_hint: str = "",
    ) -> dict[str, Any]:
        row = asset.public()
        if page_number:
            row["pageNumber"] = int(page_number)
        if item_marker:
            row["itemMarker"] = str(item_marker)
        if machine_hint:
            row["machineHint"] = str(machine_hint)
        return row

    @staticmethod
    def _job_identity_tokens(job: Any) -> list[str]:
        """Return bounded filename/search identities for a Job Nr.

        A+W/browser Job fields can carry descriptive text after the numeric Job Nr.
        Production files frequently use only that leading number (for example
        ``89883882.egl``), so do not require the whole display string to be present.
        """
        text = str(job or "").strip()
        if not text:
            return []
        numeric = re.findall(r"(?<!\d)\d{6,12}(?!\d)", text)
        if numeric:
            return list(dict.fromkeys(_compact(value) for value in numeric[:2] if _compact(value)))
        compact = _compact(text)
        return [compact] if compact else []

    def _exact_sketches_for_token(self, token: str) -> list[ProductionAsset]:
        """Probe one deferred sketch identity without walking the full share."""
        token = str(token or "").strip()
        if not self.enabled or not re.fullmatch(r"\d{6,12}", token):
            return []
        with self._sketch_order_lock:
            now = time.time()
            learned = [a for a in self._requested_sketches.values() if a.path.stem.startswith(token)]
            ttl = self.cache_seconds if learned else 3
            if now - self._sketch_order_checked.get(token, 0) < ttl:
                return learned
            root = Path(self._resolved_roots.get("sketch") or self.roots["sketch"])

            candidate_paths: list[Path] = []
            exact_path = root / f"{token}.pdf"
            try:
                info = exact_path.stat()
                if stat_module.S_ISREG(info.st_mode):
                    candidate_paths.append(exact_path)
            except FileNotFoundError:
                pass
            except OSError:
                self._sketch_order_checked[token] = now
                return learned

            # Manual/revised files can retain the Order or Job prefix while adding
            # a human note. Enumerate only that one prefix; never recurse the share.
            if not candidate_paths:
                try:
                    for path in root.glob(f"{token}*.pdf"):
                        stem = path.stem
                        if not stem.startswith(token):
                            continue
                        suffix = stem[len(token):]
                        if suffix and suffix[0].isdigit():
                            continue
                        try:
                            info = path.stat()
                        except OSError:
                            continue
                        if stat_module.S_ISREG(info.st_mode):
                            candidate_paths.append(path)
                        if len(candidate_paths) >= 8:
                            break
                except OSError:
                    self._sketch_order_checked[token] = now
                    return learned

            if not candidate_paths:
                try:
                    reachable = root.is_dir()
                except OSError:
                    reachable = False
                if reachable:
                    with self._lock:
                        for old in learned:
                            self._requested_sketches.pop(old.asset_id, None)
                            self._asset_lookup.pop(old.asset_id, None)
                    learned = []
                self._sketch_order_checked[token] = now
                return learned

            fresh_assets: list[ProductionAsset] = []
            for path in candidate_paths:
                try:
                    info = path.stat()
                    relative = path.relative_to(root).as_posix()
                except (OSError, ValueError):
                    continue
                asset = ProductionAsset(
                    "sketch", root, path, relative, path.name, ".pdf",
                    self._asset_id("sketch", relative), _compact(relative), info.st_mtime,
                )
                fresh_assets.append(asset)
            if not fresh_assets:
                self._sketch_order_checked[token] = now
                return learned

            with self._lock:
                fresh_ids = {asset.asset_id for asset in fresh_assets}
                for old in learned:
                    if old.asset_id not in fresh_ids:
                        self._requested_sketches.pop(old.asset_id, None)
                        self._asset_lookup.pop(old.asset_id, None)
                for asset in fresh_assets:
                    self._requested_sketches[asset.asset_id] = asset
                    self._asset_lookup[asset.asset_id] = asset
                self._sketch_order_checked[token] = now
                while len(self._requested_sketches) > 512:
                    oldest = next(iter(self._requested_sketches))
                    self._requested_sketches.pop(oldest)
                if len(self._sketch_order_checked) > 1024:
                    self._sketch_order_checked.pop(next(iter(self._sketch_order_checked)))

            previous = {(a.asset_id, float(a.modified_at or 0)) for a in learned}
            current = {(a.asset_id, float(a.modified_at or 0)) for a in fresh_assets}
            if current != previous:
                self._schedule_persist_index(root)
            return fresh_assets

    def _exact_order_sketches(self, order: Any, job: Any = "") -> list[ProductionAsset]:
        """Probe deferred exact/variant PDFs by Order Nr. and Job Nr.

        v0.520 keeps Order Nr. first, then tries bounded numeric Job Nr. identities.
        This covers manually named shop PDFs without adding a recursive network scan.
        """
        tokens = []
        order_token = str(order or "").strip()
        if re.fullmatch(r"\d{6,12}", order_token):
            tokens.append(order_token)
        tokens.extend(token for token in self._job_identity_tokens(job) if token not in tokens)
        assets: dict[str, ProductionAsset] = {}
        for token in tokens[:3]:
            for asset in self._exact_sketches_for_token(token):
                assets[asset.asset_id] = asset
        return list(assets.values())

    def sketch_item_views(self, order: Any, item: Any, job: Any = "") -> list[dict[str, Any]]:
        """Return exact sketch pages for one item from order-level sketch PDFs."""
        item_number = self._normalized_item_number(item)
        if not item_number:
            return []
        views: list[dict[str, Any]] = []
        # Sketch filenames identify the order, not the item. Item association is
        # determined only by the Order.Item marker inside each PDF page.
        try:
            recent_sketches = self.matches("sketch", order, "", job, limit=8, require_item=False)
        except OSError:
            recent_sketches = []
        candidates = {asset.asset_id: asset for asset in recent_sketches}
        candidates.update({asset.asset_id: asset for asset in self._exact_order_sketches(order, job)})
        for sketch in candidates.values():
            if sketch.extension == ".pdf":
                for assignment in self._sketch_page_assignments(sketch, order, allow_content_read=True):
                    if str(assignment.get("item") or "") != item_number:
                        continue
                    page_number = int(assignment.get("pageNumber") or 0)
                    views.append(self._public_asset_view(
                        sketch,
                        page_number=page_number,
                        item_marker=str(assignment.get("marker") or ""),
                        machine_hint=str(assignment.get("machine") or ""),
                    ))
            elif self._asset_mentions_item(sketch, order, item):
                # Backward-compatible support for older item-named TXT/image
                # sketches. The plant PDF contract remains Order.Item-by-page.
                machine = self._detect_machine(self._read_machine_text(sketch)) if sketch.extension in _TEXT_EXTENSIONS else ""
                views.append(self._public_asset_view(sketch, machine_hint=machine))
        if not views and self._is_network_root(self.roots["sketch"]):
            # ``assets()`` intentionally returns the current network snapshot while
            # a refresh runs. If a sketch was created after that snapshot, request
            # one background sketch-only refresh so Order Details can retry shortly
            # without synchronously walking the production share on this request.
            self.refresh_async(["sketch"])
        return views

    def reference_geometry(self, order: Any, item: Any, *, evidence_after: Any = "") -> dict[str, Any] | None:
        """Read exact item DXFs only when the authoritative PDF is unavailable."""
        from backend.sketch_geometry import read_reference_geometry

        order_token, item_token = str(order or "").strip(), self._normalized_item_number(item)
        if not self.enabled or not re.fullmatch(r"\d{6}", order_token) or not item_token:
            return None
        key = (order_token, item_token, str(evidence_after or ""))
        now = time.time()
        cached = self._reference_geometry_cache.get(key)
        if cached and now - cached[0] < (self.cache_seconds if cached[1] else 3):
            return cached[1]
        root = Path(self._resolved_roots.get("program") or self.roots["program"])
        # Shower Programmer sends six-digit Order + two-digit Item programs.
        # Also support the scanner's legacy three-digit Item representation.
        names = {f"{order_token}{int(item_token):02d}.dxf", f"{order_token}{int(item_token):03d}.dxf"}
        paths = {root / name for name in names}
        paths.update(a.path for a in self.matches("program", order_token, item_token, require_item=True, limit=12)
                     if a.extension == ".dxf" and a.name.lower() in names)
        candidates = []
        for path in paths:
            try:
                info = path.stat()
                if not stat_module.S_ISREG(info.st_mode): continue
                asset = ProductionAsset("program", root, path, path.name, path.name, ".dxf", "", "", info.st_mtime)
                cutoff = self._evidence_cutoff_timestamp(evidence_after)
                if not self._evidence_is_after(asset, cutoff): continue
                geometry = read_reference_geometry(path)
                if geometry: candidates.append(geometry)
            except (OSError, ValueError):
                continue
        # Multiple different outlines require review, even if their sizes agree.
        distinct = {json.dumps(g["paths"], separators=(",", ":")) for g in candidates}
        result = candidates[0] if candidates and len(distinct) == 1 else None
        self._reference_geometry_cache[key] = (now, result)
        while len(self._reference_geometry_cache) > 256:
            self._reference_geometry_cache.pop(next(iter(self._reference_geometry_cache)))
        return result

    def machine_assignment(
        self,
        order: Any,
        item: Any = "",
        job: Any = "",
        *,
        allow_content_read: bool = True,
        label_hint: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        item_number = self._normalized_item_number(item)
        label_assignment = self._label_fabrication_assignment(label_hint)
        # Current synchronized A+W label evidence is the cheapest and most current
        # source when it identifies an exact machine (including the Mirror+cutout
        # Waterjet rule). Resolve it before any deferred network PDF probe so Scan
        # status batches do not add one share lookup per visible order.
        if label_assignment.get("required") and self._machine_code(label_assignment.get("machine")) in {"denver", "waterjet"}:
            return {
                "machine": str(label_assignment.get("machine") or ""),
                "machineCode": self._machine_code(label_assignment.get("machine")),
                "required": True,
                "confidence": str(label_assignment.get("confidence") or "label-machine"),
                "source": {
                    "kind": "aw_label",
                    "name": "A+W Cutting Label",
                    "reason": str(label_assignment.get("reason") or ""),
                },
                "sketchMatched": False,
                "assignmentReason": str(label_assignment.get("reason") or "A+W Cutting Label identifies fabrication"),
                "labelFabricationSignal": str(label_assignment.get("signal") or ""),
            }
        try:
            recent_sketches = self.matches("sketch", order, "", job, limit=8, require_item=False)
        except OSError:
            recent_sketches = []
        candidates = {asset.asset_id: asset for asset in recent_sketches}
        # Exact/archived sketch probing is deliberately deferred to content reads.
        # Scan's allow_content_read=False hot path remains metadata-only.
        if allow_content_read:
            candidates.update({asset.asset_id: asset for asset in self._exact_order_sketches(order, job)})
        sketches = list(candidates.values())
        matched_source: dict[str, Any] | None = None
        matched_without_machine = False

        for sketch in sketches:
            if sketch.extension == ".pdf":
                assignments = self._sketch_page_assignments(sketch, order, allow_content_read=allow_content_read)
                if item_number:
                    assignment = next((row for row in assignments if str(row.get("item") or "") == item_number), None)
                    if not assignment:
                        continue
                    source = self._public_asset_view(
                        sketch,
                        page_number=int(assignment.get("pageNumber") or 0),
                        item_marker=str(assignment.get("marker") or ""),
                        machine_hint=str(assignment.get("machine") or ""),
                    )
                    machine = str(assignment.get("machine") or "")
                    if machine:
                        return {
                            "machine": machine,
                            "machineCode": self._machine_code(machine),
                            "required": True,
                            "confidence": "high",
                            "source": source,
                            "sketchMatched": True,
                            "assignmentReason": "Exact sketch page identifies the fabrication machine",
                        }
                    matched_source = source
                    matched_without_machine = True
                continue

            # Legacy item-named text sketches remain readable on demand. They
            # are never parsed by the background index, preserving v0.474's
            # performance boundary while keeping old plant files functional.
            if item_number and self._asset_mentions_item(sketch, order, item):
                machine = ""
                if allow_content_read and sketch.extension in _TEXT_EXTENSIONS:
                    machine = self._detect_machine(self._read_machine_text(sketch))
                source = self._public_asset_view(sketch, machine_hint=machine)
                if machine:
                    return {
                        "machine": machine, "machineCode": self._machine_code(machine), "required": True,
                        "confidence": "high", "source": source, "sketchMatched": True,
                        "assignmentReason": "Exact legacy sketch identifies the fabrication machine",
                    }
                matched_source = source
                matched_without_machine = True

        if label_assignment.get("required"):
            return {
                "machine": str(label_assignment.get("machine") or ""),
                "machineCode": self._machine_code(label_assignment.get("machine")),
                "required": True,
                "confidence": str(label_assignment.get("confidence") or "label-required"),
                "source": {
                    "kind": "aw_label",
                    "name": "A+W Cutting Label",
                    "reason": str(label_assignment.get("reason") or ""),
                },
                "sketchMatched": bool(matched_without_machine),
                "assignmentReason": str(label_assignment.get("reason") or "A+W Cutting Label requires fabrication"),
                "labelFabricationSignal": str(label_assignment.get("signal") or ""),
            }

        if matched_without_machine:
            return {
                "machine": "", "required": False, "confidence": "item-matched",
                "source": matched_source, "sketchMatched": True,
                "assignmentReason": "Exact sketch page matched the item but did not identify a fabrication machine",
            }
        return {
            "machine": "",
            "required": False,
            "confidence": "unknown",
            "source": sketches[0].public() if sketches else None,
            "sketchMatched": False,
            "assignmentReason": "",
        }

    def _historical_egl_match(
        self,
        order: Any,
        item: Any = "",
        job: Any = "",
        *,
        evidence_cutoff: float = 0.0,
    ) -> tuple[ProductionAsset, float] | None:
        """Return the best previously observed exact Denver program for evidence only."""
        require_item = bool(str(item or "").strip())
        with self._lock:
            rows = list(self._egl_history.values())
        scored: list[tuple[int, float, float, ProductionAsset]] = []
        for asset, last_seen in rows:
            if not self._evidence_is_after(asset, evidence_cutoff):
                continue
            score = self._score(asset, order, item, job, require_item=require_item)
            if score > 0:
                scored.append((score, float(last_seen or 0), float(asset.modified_at or 0), asset))
        if not scored:
            return None
        scored.sort(key=lambda row: (-row[0], -row[1], -row[2], row[3].relative.lower()))
        _score_value, last_seen, _mtime, asset = scored[0]
        return asset, last_seen

    @staticmethod
    def _evidence_cutoff_timestamp(value: Any) -> float:
        """Normalize a scanner reject timestamp to a UTC epoch cutoff."""
        text = str(value or "").strip()
        if not text:
            return 0.0
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return 0.0
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).timestamp()

    @staticmethod
    def _evidence_is_after(asset: ProductionAsset | None, cutoff: float) -> bool:
        if asset is None:
            return False
        if cutoff <= 0:
            return True
        # An overwritten program receives a new filesystem mtime, so the same
        # exact filename becomes valid evidence again once it changes after the
        # reject. lastSeenAt alone is never sufficient because merely observing
        # an old file after a reject must not make it look newly fabricated.
        return float(asset.modified_at or 0) > cutoff

    def invalidate_fabrication(self, order: Any = "", item: Any = "") -> None:
        """Drop cached fabrication answers after reject state or evidence changes."""
        order_token = _compact(order)
        item_token = _compact(item)
        with self._lock:
            if not order_token and not item_token:
                self._fabrication_cache.clear()
                return
            for key in list(self._fabrication_cache):
                if order_token and key[0] != order_token:
                    continue
                if item_token and key[1] != item_token:
                    continue
                self._fabrication_cache.pop(key, None)

    def _check_item_sources(self, order: Any, item: Any, job: Any) -> bool:
        """Manual refresh of one item's metadata; never recurse the share."""
        identities = [str(order or "").strip(), *self._job_identity_tokens(job)]
        identities = [token for token in identities if re.fullmatch(r"\d{6,12}", token)][:3]
        if not identities: return False
        with self._lock:
            for token in identities: self._sketch_order_checked.pop(token, None)
            known_sketches = {a.asset_id: a for a in self._cache.get("sketch", (0, []))[1]}
            known_sketches.update(self._requested_sketches)
            for asset in known_sketches.values():
                if self._score(asset, order, "", job) <= 0: continue
                self._sketch_page_cache.pop(asset.asset_id, None)
                self._sketch_empty_cache_at.pop(asset.asset_id, None)
                self._machine_text_cache.pop(asset.asset_id, None)
            for key in list(self._fabrication_cache):
                if key[0] == _compact(order) and key[1] == _compact(item): self._fabrication_cache.pop(key, None)
        sketches = self._exact_order_sketches(order, job)
        with self._lock:
            known_sketches.update({a.asset_id: a for a in sketches})
            self._cache["sketch"] = (time.time(), list(known_sketches.values()))
        reachable = False
        for kind, extension in (("program", ".egl"), ("completed_wj", ".nce")):
            root = Path(self._resolved_roots.get(kind) or self.roots[kind])
            try:
                if not root.is_dir():
                    self._set_kind_availability(kind, False)
                    continue
                reachable = True
                found = []
                for token in identities:
                    for path in root.glob(f"{token}*{extension}"):
                        info = path.stat()
                        relative = path.relative_to(root).as_posix()
                        asset = ProductionAsset(kind, root, path, relative, path.name, extension,
                                                self._asset_id(kind, relative), _compact(relative), info.st_mtime)
                        if self._score(asset, order, item, job, require_item=True) > 0: found.append(asset)
                        if len(found) >= 80: break
                with self._lock:
                    values = {a.asset_id: a for a in self._cache.get(kind, (0, []))[1]}
                    values.update({a.asset_id: a for a in found})
                    self._replace_kind_cache(kind, list(values.values()), True)
            except OSError as exc:
                self._set_kind_availability(kind, False, str(exc))
        return reachable or bool(sketches)

    def fabrication_status(self, order: Any, item: Any = "", job: Any = "", *,
                           refresh_missing: bool = False, allow_content_read: bool = True,
                           evidence_after: Any = "", label_hint: dict[str, Any] | None = None,
                           force_check: bool = False) -> dict[str, Any]:
        """Coalesce concurrent checks and reuse durable, evidence-aware results."""
        lock = self._fabrication_check_locks[hash(_compact(order)) % len(self._fabrication_check_locks)]
        with lock:
            key = (_compact(order), _compact(item), "", bool(allow_content_read), str(evidence_after or "").strip(), self._fabrication_lifecycle_signature(label_hint))
            previous = self._fabrication_cache.get(key)
            reachable = self._check_item_sources(order, item, job) if force_check else True
            result = self._compute_fabrication_status(order, item, job, refresh_missing=refresh_missing,
                                                     allow_content_read=allow_content_read,
                                                     evidence_after=evidence_after, label_hint=label_hint)
            if force_check:
                kind = {"denver": "program", "waterjet": "completed_wj"}.get(result.get("assignedMachineCode"))
                result["checkUnavailable"] = not result.get("availability", {}).get(kind) if kind else not reachable
                if result["checkUnavailable"] and previous:
                    result = {**previous[1], "remembered": True, "checkUnavailable": True,
                              "availability": result.get("availability"), "blockStaging": False, "enforceable": False}
                    self._fabrication_cache[key] = previous
                elif previous and previous[1].get("fabricated") is True and not result.get("evidence"):
                    # File archival is not a reject or a new generation. Keep
                    # the completion observation for this unchanged identity.
                    result = {**previous[1], "checkedAt": result["checkedAt"], "remembered": True,
                              "evidence": {**(previous[1].get("evidence") or {}), "historical": True, "existsNow": False}}
                    self._fabrication_cache[key] = (time.monotonic(), result)
            return result

    def _compute_fabrication_status(
        self,
        order: Any,
        item: Any = "",
        job: Any = "",
        *,
        refresh_missing: bool = False,
        allow_content_read: bool = True,
        evidence_after: Any = "",
        label_hint: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        evidence_after_text = str(evidence_after or "").strip()
        evidence_cutoff = self._evidence_cutoff_timestamp(evidence_after_text)
        lifecycle_signature = self._fabrication_lifecycle_signature(label_hint)
        cache_key = (_compact(order), _compact(item), "", bool(allow_content_read), evidence_after_text, lifecycle_signature)
        now = time.monotonic()
        cached = self._fabrication_cache.get(cache_key)
        # Positive completion is a durable milestone. Missing/unknown evidence is
        # only a snapshot and must expire so a cut-but-unfabricated pane is checked
        # again after the configured production refresh interval.
        remembered = bool(cached and cached[1].get("fabricated") is True)
        cache_is_fresh = bool(cached and (remembered or now - cached[0] < self.cache_seconds))
        if cache_is_fresh and (not refresh_missing or not cached[1].get("blockStaging")):
            # Return a shallow copy so UI-specific callers cannot mutate the cache.
            result = {**cached[1], "remembered": True}
            source = {"denver": "program", "waterjet": "completed_wj"}.get(result.get("assignedMachineCode"))
            available = self._availability_cache[1] if self._availability_cache else {}
            if source and source in available and not available[source]:
                result.update(blockStaging=False, enforceable=False, checkUnavailable=True)
            return result

        # A previously missing evidence result requests a targeted index refresh
        # when Staging checks it again. Network shares remain off the scan/request
        # thread; local/test roots can refresh synchronously while production uses
        # the background recent-file index and its configured refresh interval.
        refresh_evidence = bool(cache_is_fresh and refresh_missing and cached[1].get("blockStaging"))
        availability = self.availability()
        assignment = self.machine_assignment(order, item, job, allow_content_read=allow_content_read, label_hint=label_hint)
        assigned_machine = str(assignment.get("machine") or "")
        assigned_code = str(assignment.get("machineCode") or self._machine_code(assigned_machine) or "")
        actual_machine = assigned_machine
        actual_code = assigned_code
        programs: list[ProductionAsset] = []
        completed_wj: list[ProductionAsset] = []
        evidence: ProductionAsset | None = None
        fabricated: bool | None = None
        enforceable = False

        require_item = bool(str(item or "").strip())
        if availability.get("program"):
            programs = self.matches(
                "program", order, item, job, limit=12, require_item=require_item, refresh=refresh_evidence
            )
        if availability.get("completed_wj"):
            completed_wj = self.matches(
                "completed_wj", order, item, job, limit=12, require_item=require_item, refresh=refresh_evidence
            )
        live_denver_candidates = [asset for asset in programs if asset.extension == ".egl"]
        denver_evidence = next((asset for asset in live_denver_candidates if self._evidence_is_after(asset, evidence_cutoff)), None)
        historical_denver = None if denver_evidence else self._historical_egl_match(
            order, item, job, evidence_cutoff=evidence_cutoff
        )
        historical_denver_evidence = historical_denver[0] if historical_denver else None
        historical_denver_last_seen = historical_denver[1] if historical_denver else 0
        waterjet_evidence = next(
            (asset for asset in completed_wj if asset.extension == ".nce" and self._evidence_is_after(asset, evidence_cutoff)),
            None,
        )
        effective_denver_evidence = denver_evidence or historical_denver_evidence
        stale_denver = next((asset for asset in live_denver_candidates if not self._evidence_is_after(asset, evidence_cutoff)), None)
        stale_waterjet = next(
            (asset for asset in completed_wj if asset.extension == ".nce" and not self._evidence_is_after(asset, evidence_cutoff)),
            None,
        )

        # The sketch is the assignment, but completed-file evidence is the
        # operational truth. If both machine evidence types exist for the exact
        # item, the newest completion wins; that reflects a rerun/machine change
        # instead of permanently preferring one machine type.
        if effective_denver_evidence and waterjet_evidence:
            if float(waterjet_evidence.modified_at or 0) >= float(effective_denver_evidence.modified_at or 0):
                actual_code, actual_machine, evidence = "waterjet", self._machine_name("waterjet"), waterjet_evidence
            else:
                actual_code, actual_machine, evidence = "denver", self._machine_name("denver"), effective_denver_evidence
        elif assigned_code == "waterjet" and effective_denver_evidence:
            actual_code, actual_machine, evidence = "denver", self._machine_name("denver"), effective_denver_evidence
        elif assigned_code == "denver" and waterjet_evidence:
            actual_code, actual_machine, evidence = "waterjet", self._machine_name("waterjet"), waterjet_evidence
        elif assigned_code == "denver":
            actual_machine, evidence = self._machine_name("denver"), effective_denver_evidence
        elif assigned_code == "waterjet":
            actual_machine, evidence = self._machine_name("waterjet"), waterjet_evidence
        elif effective_denver_evidence:
            actual_code, actual_machine, evidence = "denver", self._machine_name("denver"), effective_denver_evidence
        elif waterjet_evidence:
            actual_code, actual_machine, evidence = "waterjet", self._machine_name("waterjet"), waterjet_evidence

        if assigned_code == "denver":
            enforceable = bool(availability.get("program"))
        elif assigned_code == "waterjet":
            enforceable = bool(availability.get("completed_wj"))
        required = bool(assignment.get("required"))
        fabricated = bool(evidence) if assigned_code and enforceable else (bool(evidence) if evidence else None)

        if actual_machine and fabricated is True:
            label = f"Fabricated - {actual_machine}"
        elif assigned_code in {"denver", "waterjet"} and fabricated is False:
            label = f"Not Fabricated - {self._machine_name(assigned_code)}"
        elif assigned_machine == "Fabrication":
            label = "Fabrication required - machine review"
        elif assigned_machine:
            label = f"Fabrication status unavailable - {self._machine_name(assigned_code) if assigned_code else assigned_machine}"
        elif required:
            label = "Fabrication required - machine review"
        else:
            label = "Fabrication machine not assigned"

        result = {
            "checkedAt": datetime.now(timezone.utc).isoformat(),
            "remembered": False,
            "machine": actual_machine,
            "machineCode": actual_code or assigned_code,
            "assignedMachine": self._machine_name(assigned_code) if assigned_code else assigned_machine,
            "assignedMachineCode": assigned_code,
            "actualMachine": actual_machine if evidence else "",
            "actualMachineCode": actual_code if evidence else "",
            "machineOverride": bool(evidence and assigned_code and actual_code and actual_code != assigned_code),
            "machineConfidence": assignment.get("confidence") or "unknown",
            "machineSource": assignment.get("source"),
            "machineAssignmentReason": str(assignment.get("assignmentReason") or ""),
            "labelFabricationSignal": str(assignment.get("labelFabricationSignal") or ""),
            "sketchMatched": bool(assignment.get("sketchMatched")),
            "required": required,
            "enforceable": bool(assigned_code in {"denver", "waterjet"} and enforceable),
            "fabricated": fabricated,
            "blockStaging": bool(assigned_code in {"denver", "waterjet"} and enforceable and fabricated is False),
            "label": label,
            "evidence": (
                {**evidence.public(), "historical": True, "existsNow": False, "lastSeenAt": historical_denver_last_seen}
                if evidence is historical_denver_evidence and historical_denver_evidence
                else ({**evidence.public(), "historical": False, "existsNow": True} if evidence else None)
            ),
            "availability": availability,
            "programs": [asset.public() for asset in programs],
            "completedWaterjet": [asset.public() for asset in completed_wj],
            "evidenceAfter": evidence_after_text,
            "evidenceResetRequired": bool(evidence_cutoff > 0),
            "lifecycleRevision": lifecycle_signature,
            "identityTokens": [str(order or "").strip(), *self._job_identity_tokens(job)],
            "staleEvidence": (
                {**stale_denver.public(), "reason": "Predates latest Internal Reject"}
                if stale_denver
                else ({**stale_waterjet.public(), "reason": "Predates latest Internal Reject"} if stale_waterjet else None)
            ),
        }
        result["retryAfterSeconds"] = 0 if fabricated is True else self.cache_seconds
        with self._lock:
            self._fabrication_cache[cache_key] = (now, result)
            while len(self._fabrication_cache) > 10000:
                self._fabrication_cache.pop(next(iter(self._fabrication_cache)))
        if allow_content_read:
            self._schedule_persist_index(self.roots["sketch"])
        return dict(result)

    def item_assets(
        self, order: Any, item: Any = "", job: Any = "", *,
        evidence_after: Any = "", label_hint: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        # Hardware lists are commonly order-level documents, but sketches and
        # programs are item-specific production records. Keep sibling item files
        # out of an item's Order Details card when an item number is available.
        require_item = bool(str(item or "").strip())
        sketches = self.sketch_item_views(order, item, job) if require_item else []
        with self._lock:
            sketch_refresh_pending = "sketch" in self._refreshing
        return {
            "hardware": [asset.public() for asset in self.matches("hardware", order, item, job, limit=8)],
            "sketches": sketches,
            "referenceGeometry": self.reference_geometry(order, item, evidence_after=evidence_after) if require_item and not sketches else None,
            "sketchRefreshPending": bool(sketch_refresh_pending),
            "programs": [
                asset.public()
                for asset in self.matches("program", order, item, job, limit=12, require_item=require_item)
            ],
            "fabrication": self.fabrication_status(order, item, job, evidence_after=evidence_after, label_hint=label_hint),
        }

    def order_assets(self, order: Any, job: Any = "") -> dict[str, Any]:
        """Return order-level documents without assigning them to one item."""
        sketches = {asset.asset_id: asset for asset in self.matches("sketch", order, "", job, limit=40)}
        for asset in self._exact_order_sketches(order, job):
            sketches[asset.asset_id] = asset
        ordered_sketches = sorted(sketches.values(), key=lambda asset: (-float(asset.modified_at or 0), asset.relative.lower()))
        return {
            "hardware": [asset.public() for asset in self.matches("hardware", order, "", job, limit=20)],
            "sketches": [asset.public() for asset in ordered_sketches[:40]],
        }

    def open_asset(self, asset_id: str) -> dict[str, Any]:
        asset = self.resolve_asset(asset_id)
        if not asset:
            raise FileNotFoundError("Production file was not found or is no longer available.")
        if os.name != "nt":
            return {"opened": False, "message": "Direct program opening is only available on the Windows scanner host.", "asset": asset.public()}
        try:
            os.startfile(str(asset.path))  # type: ignore[attr-defined]
        except OSError as exc:
            return {"opened": False, "message": str(exc), "asset": asset.public()}
        return {"opened": True, "message": f"Opened {asset.name}", "asset": asset.public()}
