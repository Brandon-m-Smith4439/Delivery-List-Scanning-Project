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
        self.machine_terms: dict[str, list[str]] = {
            "denver": ["DENVER", "DENVER CNC"],
            "waterjet": ["WATER JET", "WATERJET", "WJ"],
        }
        # v0.476: machine colors are presentation settings shared by Scan,
        # Smart Search, and Order Details. They stay in the existing settings
        # metadata so no database migration is needed.
        self.machine_colors: dict[str, str] = {
            "denver": "#2563eb",
            "waterjet": "#7c3aed",
        }
        self.roots: dict[str, Path] = {
            "hardware": Path(config.hardware_lists_dir),
            "sketch": Path(config.sketches_dir),
            "program": Path(config.programs_dir),
            "completed_wj": Path(config.completed_wj_dir),
        }
        self._cache: dict[str, tuple[float, list[ProductionAsset]]] = {}
        self._asset_lookup: dict[str, ProductionAsset] = {}
        self._availability_cache: tuple[float, dict[str, bool]] | None = None
        self._availability_errors: dict[str, str] = {}
        # v0.476: resolved production roots are learned only by background/local
        # index work. Settings reads this cache instead of probing mapped shares
        # on the request thread.
        self._resolved_roots: dict[str, str] = {}
        self._fabrication_cache: dict[tuple[str, str, str, bool], tuple[float, dict[str, Any]]] = {}
        self._machine_text_cache: dict[str, tuple[float, str]] = {}
        # v0.474: PDF page assignments are parsed lazily per requested order.
        # The share index itself stays metadata-only so hundreds of recent sketches
        # cannot keep the entire application busy while Settings says Refreshing.
        self._sketch_page_cache: dict[str, tuple[float, str, list[dict[str, Any]]]] = {}
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
        next_colors = dict(self.machine_colors)
        for machine, default_color in self.machine_colors.items():
            raw_color = str(colors.get(machine) or default_color).strip()
            next_colors[machine] = raw_color if re.fullmatch(r"#[0-9A-Fa-f]{6}", raw_color) else default_color
        next_terms: dict[str, list[str]] = {}
        for machine, defaults in self.machine_terms.items():
            raw_terms = terms.get(machine, defaults)
            if isinstance(raw_terms, str):
                raw_terms = re.split(r"[,;\n]+", raw_terms)
            cleaned = [str(term or "").strip().upper() for term in (raw_terms or []) if str(term or "").strip()]
            next_terms[machine] = list(dict.fromkeys(cleaned)) or list(defaults)
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
            terms_changed = any(next_terms.get(machine, []) != self.machine_terms.get(machine, []) for machine in next_terms)
            colors_changed = any(next_colors.get(machine) != self.machine_colors.get(machine) for machine in next_colors)
            lookback_changed = lookback_days != self.lookback_days
            self.enabled = bool(values.get("enabled", True))
            self.enforce_staging = bool(values.get("enforceStaging", True))
            self.cache_seconds = cache_minutes * 60
            self.lookback_days = lookback_days
            self.machine_terms = next_terms
            self.machine_colors = next_colors
            if roots_changed or lookback_changed:
                self.roots = next_roots
                self._cache.clear()
                self._asset_lookup.clear()
                self._availability_cache = None
                self._availability_errors.clear()
                self._resolved_roots.clear()
                self._fabrication_cache.clear()
                self._machine_text_cache.clear()
                self._sketch_page_cache.clear()
                self._load_persisted_index()
            elif terms_changed:
                self._cache.pop("sketch", None)
                for asset_id in [key for key, asset in self._asset_lookup.items() if asset.kind == "sketch"]:
                    self._asset_lookup.pop(asset_id, None)
                self._fabrication_cache.clear()
                self._sketch_page_cache.clear()
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
                self._sketch_page_cache[asset_id] = (asset.modified_at, order_token, clean_assignments)

    def _persist_index(self) -> None:
        if not self._background_refresh_enabled:
            return
        with self._lock:
            payload = {
                "version": 3,
                "indexedAt": time.time(),
                "lookbackDays": int(self.lookback_days),
                "roots": {kind: str(root) for kind, root in self.roots.items()},
                "availability": dict(self._availability_cache[1]) if self._availability_cache else {},
                "assets": {
                    kind: [self._serialize_asset(asset) for asset in self._cache.get(kind, (0, []))[1]]
                    for kind in self.roots
                },
                "sketchPages": [
                    {
                        "assetId": asset_id,
                        "modifiedAt": modified_at,
                        "order": order_token,
                        "assignments": [dict(row) for row in assignments],
                    }
                    for asset_id, (modified_at, order_token, assignments) in self._sketch_page_cache.items()
                    if asset_id in self._asset_lookup
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
        if not self._background_refresh_enabled or not self._is_network_root(source_root):
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
            self._cache[kind] = (now, assets)
            prefix = f"{kind}-"
            for asset_id in [key for key in self._asset_lookup if key.startswith(prefix)]:
                self._asset_lookup.pop(asset_id, None)
            for asset in assets:
                self._asset_lookup[asset.asset_id] = asset
            availability = dict(self._availability_cache[1]) if self._availability_cache else {}
            availability[kind] = bool(available)
            self._availability_cache = (now, availability)
            self._fabrication_cache.clear()

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
        job_token = _compact(job)
        key = asset.search_key
        score = 0
        if order_token:
            if order_token not in key:
                return 0
            score += 100
        elif job_token and job_token in key:
            score += 65
        else:
            return 0
        if job_token and job_token in key:
            score += 20
        if str(item or "").strip():
            item_match = self._asset_mentions_item(asset, order, item)
            if require_item and not item_match:
                return 0
            score += 70 if item_match else -15
        # Prefer files with explicit production/fabrication extensions and newer
        # revisions when two files otherwise describe the same order/item.
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
        for asset in self.assets(kind, refresh=refresh):
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

    def _detect_machine(self, signals: str) -> str:
        """Resolve one configured sketch assignment without hard-coded request work."""
        if self._matches_machine_terms(signals, "denver"):
            return "Denver CNC"
        if self._matches_machine_terms(signals, "waterjet"):
            return "Waterjet"
        return ""

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
            return [dict(row) for row in cached[2]]
        if not allow_content_read:
            return []

        assignments: list[dict[str, Any]] = []
        try:
            from pypdf import PdfReader  # type: ignore

            reader = PdfReader(str(asset.path))
            # Exact sketch contract: order and item are separated by a decimal.
            marker = re.compile(rf"(?<!\d){re.escape(order_token)}\s*\.\s*0*(\d{{1,3}})(?!\d)", re.IGNORECASE)
            for page_index, page in enumerate(reader.pages):
                try:
                    text = page.extract_text() or ""
                except Exception:
                    text = ""
                if not text:
                    continue
                machine = self._detect_machine(text)
                for match in marker.finditer(text):
                    item_number = self._normalized_item_number(match.group(1))
                    if not item_number:
                        continue
                    assignments.append({
                        "item": item_number,
                        "marker": f"{order_token}.{item_number}",
                        "pageNumber": page_index + 1,
                        "machine": machine,
                    })
        except Exception:
            assignments = []

        # Keep one deterministic page per item when a PDF happens to repeat a
        # title/marker in annotations or revision notes.
        unique: dict[str, dict[str, Any]] = {}
        for row in assignments:
            unique.setdefault(str(row.get("item") or ""), row)
        result = list(unique.values())
        self._sketch_page_cache[asset.asset_id] = (asset.modified_at, order_token, [dict(row) for row in result])
        self._schedule_persist_index(asset.root)
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

    def sketch_item_views(self, order: Any, item: Any, job: Any = "") -> list[dict[str, Any]]:
        """Return exact sketch pages for one item from order-level sketch PDFs."""
        item_number = self._normalized_item_number(item)
        if not item_number:
            return []
        views: list[dict[str, Any]] = []
        # Sketch filenames identify the order, not the item. Item association is
        # determined only by the Order.Item marker inside each PDF page.
        for sketch in self.matches("sketch", order, "", job, limit=8, require_item=False):
            if sketch.extension == ".pdf":
                for assignment in self._sketch_page_assignments(sketch, order, allow_content_read=True):
                    if str(assignment.get("item") or "") != item_number:
                        continue
                    views.append(self._public_asset_view(
                        sketch,
                        page_number=int(assignment.get("pageNumber") or 0),
                        item_marker=str(assignment.get("marker") or ""),
                        machine_hint=str(assignment.get("machine") or ""),
                    ))
            elif self._asset_mentions_item(sketch, order, item):
                # Backward-compatible support for older item-named TXT/image
                # sketches. The plant PDF contract remains Order.Item-by-page.
                machine = self._detect_machine(self._read_machine_text(sketch)) if sketch.extension in _TEXT_EXTENSIONS else ""
                views.append(self._public_asset_view(sketch, machine_hint=machine))
        return views

    def machine_assignment(
        self,
        order: Any,
        item: Any = "",
        job: Any = "",
        *,
        allow_content_read: bool = True,
    ) -> dict[str, Any]:
        item_number = self._normalized_item_number(item)
        sketches = self.matches("sketch", order, "", job, limit=8, require_item=False)
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
                    return {
                        "machine": machine,
                        "confidence": "high" if machine else "item-matched",
                        "source": source,
                        "sketchMatched": True,
                    }
                continue

            # Legacy item-named text sketches remain readable on demand. They
            # are never parsed by the background index, preserving v0.474's
            # performance boundary while keeping old plant files functional.
            if item_number and self._asset_mentions_item(sketch, order, item):
                machine = ""
                if allow_content_read and sketch.extension in _TEXT_EXTENSIONS:
                    machine = self._detect_machine(self._read_machine_text(sketch))
                return {
                    "machine": machine,
                    "confidence": "high" if machine else "item-matched",
                    "source": self._public_asset_view(sketch, machine_hint=machine),
                    "sketchMatched": True,
                }

        return {
            "machine": "",
            "confidence": "unknown",
            "source": sketches[0].public() if sketches else None,
            "sketchMatched": False,
        }

    def fabrication_status(
        self,
        order: Any,
        item: Any = "",
        job: Any = "",
        *,
        refresh_missing: bool = False,
        allow_content_read: bool = True,
    ) -> dict[str, Any]:
        cache_key = (_compact(order), _compact(item), _compact(job), bool(allow_content_read))
        now = time.monotonic()
        cached = self._fabrication_cache.get(cache_key)
        cache_is_fresh = bool(cached and now - cached[0] < self.cache_seconds)
        if cache_is_fresh and (not refresh_missing or not cached[1].get("blockStaging")):
            # Return a shallow copy so UI-specific callers cannot mutate the cache.
            return dict(cached[1])

        # A previously missing evidence result requests a targeted index refresh
        # when Staging checks it again. Network shares remain off the scan/request
        # thread; local/test roots can refresh synchronously while production uses
        # the background recent-file index and its configured refresh interval.
        refresh_evidence = bool(cache_is_fresh and refresh_missing and cached[1].get("blockStaging"))
        availability = self.availability()
        assignment = self.machine_assignment(order, item, job, allow_content_read=allow_content_read)
        assigned_machine = str(assignment.get("machine") or "")
        actual_machine = assigned_machine
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
        denver_evidence = next((asset for asset in programs if asset.extension == ".egl"), None)
        waterjet_evidence = next((asset for asset in completed_wj if asset.extension == ".nce"), None)

        # The sketch is the assignment, but completed-file evidence is the
        # operational truth. If both machine evidence types exist for the exact
        # item, the newest completion wins; that reflects a rerun/machine change
        # instead of permanently preferring one machine type.
        if denver_evidence and waterjet_evidence:
            if float(waterjet_evidence.modified_at or 0) >= float(denver_evidence.modified_at or 0):
                actual_machine, evidence = "Waterjet", waterjet_evidence
            else:
                actual_machine, evidence = "Denver CNC", denver_evidence
        elif assigned_machine == "Waterjet" and denver_evidence:
            actual_machine, evidence = "Denver CNC", denver_evidence
        elif assigned_machine == "Denver CNC" and waterjet_evidence:
            actual_machine, evidence = "Waterjet", waterjet_evidence
        elif assigned_machine == "Denver CNC":
            evidence = denver_evidence
        elif assigned_machine == "Waterjet":
            evidence = waterjet_evidence
        elif denver_evidence:
            actual_machine, evidence = "Denver CNC", denver_evidence
        elif waterjet_evidence:
            actual_machine, evidence = "Waterjet", waterjet_evidence

        if assigned_machine == "Denver CNC":
            enforceable = bool(availability.get("program"))
        elif assigned_machine == "Waterjet":
            enforceable = bool(availability.get("completed_wj"))
        fabricated = bool(evidence) if assigned_machine and enforceable else (bool(evidence) if evidence else None)

        if actual_machine and fabricated is True:
            label = f"Fabricated - {actual_machine}"
        elif assigned_machine and fabricated is False:
            label = f"Not Fabricated - {assigned_machine}"
        elif assigned_machine:
            label = f"Fabrication status unavailable - {assigned_machine}"
        else:
            label = "Fabrication machine not assigned"

        result = {
            "machine": actual_machine,
            "assignedMachine": assigned_machine,
            "actualMachine": actual_machine if evidence else "",
            "machineOverride": bool(evidence and assigned_machine and actual_machine != assigned_machine),
            "machineConfidence": assignment.get("confidence") or "unknown",
            "machineSource": assignment.get("source"),
            "sketchMatched": bool(assignment.get("sketchMatched")),
            "required": bool(assigned_machine),
            "enforceable": bool(assigned_machine and enforceable),
            "fabricated": fabricated,
            "blockStaging": bool(assigned_machine and enforceable and fabricated is False),
            "label": label,
            "evidence": evidence.public() if evidence else None,
            "availability": availability,
            "programs": [asset.public() for asset in programs],
            "completedWaterjet": [asset.public() for asset in completed_wj],
        }
        self._fabrication_cache[cache_key] = (now, result)
        return dict(result)

    def item_assets(self, order: Any, item: Any = "", job: Any = "") -> dict[str, Any]:
        # Hardware lists are commonly order-level documents, but sketches and
        # programs are item-specific production records. Keep sibling item files
        # out of an item's Order Details card when an item number is available.
        require_item = bool(str(item or "").strip())
        return {
            "hardware": [asset.public() for asset in self.matches("hardware", order, item, job, limit=8)],
            "sketches": self.sketch_item_views(order, item, job) if require_item else [],
            "programs": [
                asset.public()
                for asset in self.matches("program", order, item, job, limit=12, require_item=require_item)
            ],
            "fabrication": self.fabrication_status(order, item, job),
        }

    def order_assets(self, order: Any, job: Any = "") -> dict[str, Any]:
        """Return order-level documents without assigning them to one item."""
        return {
            "hardware": [asset.public() for asset in self.matches("hardware", order, "", job, limit=20)],
            "sketches": [asset.public() for asset in self.matches("sketch", order, "", job, limit=40)],
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
