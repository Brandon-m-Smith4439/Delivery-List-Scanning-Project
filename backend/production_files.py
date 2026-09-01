# File: backend/production_files.py
"""Cached access to production hardware, sketch, and fabrication files.

v0.470 keeps the network-share integration isolated from the database layer so
normal scans remain fast and the application can safely run when the production
I: drive is not mounted (for example, development laptops or the test runner).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any


_TEXT_EXTENSIONS = {".txt", ".csv", ".tsv", ".xml", ".json", ".html", ".htm", ".ini", ".log", ".nc", ".cnc", ".egl"}
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
        self.machine_terms: dict[str, list[str]] = {
            "denver": ["DENVER", "DENVER CNC"],
            "waterjet": ["WATER JET", "WATERJET", "WJ"],
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
        self._fabrication_cache: dict[tuple[str, str, str, bool], tuple[float, dict[str, Any]]] = {}
        self._machine_text_cache: dict[str, tuple[float, str]] = {}
        self._lock = threading.RLock()
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
        with self._lock:
            roots_changed = any(str(next_roots[kind]).casefold() != str(self.roots[kind]).casefold() for kind in self.roots)
            terms_changed = any(next_terms.get(machine, []) != self.machine_terms.get(machine, []) for machine in next_terms)
            self.enabled = bool(values.get("enabled", True))
            self.enforce_staging = bool(values.get("enforceStaging", True))
            self.cache_seconds = cache_minutes * 60
            self.machine_terms = next_terms
            if roots_changed:
                self.roots = next_roots
                self._cache.clear()
                self._asset_lookup.clear()
                self._availability_cache = None
                self._fabrication_cache.clear()
                self._machine_text_cache.clear()
                self._load_persisted_index()
            elif terms_changed:
                self._cache.pop("sketch", None)
                for asset_id in [key for key, asset in self._asset_lookup.items() if asset.kind == "sketch"]:
                    self._asset_lookup.pop(asset_id, None)
                self._fabrication_cache.clear()
        if terms_changed:
            self.refresh_async(["sketch"])

    def settings_snapshot(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "enforceStaging": self.enforce_staging,
            "cacheMinutes": max(self.cache_seconds // 60, 1),
            "roots": {
                "hardware": str(self.roots["hardware"]),
                "sketches": str(self.roots["sketch"]),
                "programs": str(self.roots["program"]),
                "completedWaterjet": str(self.roots["completed_wj"]),
            },
            "machineTerms": {key: list(values) for key, values in self.machine_terms.items()},
        }

    def _is_network_root(self, root: Path) -> bool:
        """Treat UNC and non-application drives as remote production shares."""
        raw = str(root)
        if raw.startswith(("\\\\", "//")):
            return True
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
            assets = [asset for row in rows if isinstance(row, dict) for asset in [self._deserialize_asset(kind, row)] if asset]
            self._cache[kind] = (indexed_at, assets)
            for asset in assets:
                self._asset_lookup[asset.asset_id] = asset
        availability = payload.get("availability")
        if isinstance(availability, dict):
            self._availability_cache = (indexed_at, {kind: bool(availability.get(kind)) for kind in self.roots})

    def _persist_index(self) -> None:
        if not self._background_refresh_enabled:
            return
        with self._lock:
            payload = {
                "version": 1,
                "indexedAt": time.time(),
                "roots": {kind: str(root) for kind, root in self.roots.items()},
                "availability": dict(self._availability_cache[1]) if self._availability_cache else {},
                "assets": {
                    kind: [self._serialize_asset(asset) for asset in self._cache.get(kind, (0, []))[1]]
                    for kind in self.roots
                },
            }
        try:
            self._index_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self._index_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
            temporary.replace(self._index_path)
        except OSError:
            # A read-only install can still use the in-memory index.
            return

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
        root = self.roots[kind]
        try:
            available = root.exists() and root.is_dir()
            assets = self._walk_root(kind, root) if available else []
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
            }

    def availability(self, *, refresh: bool = False) -> dict[str, bool]:
        """Return cached share availability so disconnected drives do not stall hot paths."""
        if not self.enabled:
            return {kind: False for kind in self.roots}
        now = time.time()
        if not any(self._is_network_root(root) for root in self.roots.values()):
            values = {kind: root.exists() and root.is_dir() for kind, root in self.roots.items()}
            self._availability_cache = (now, values)
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
        if not root.exists() or not root.is_dir():
            return []
        assets: list[ProductionAsset] = []
        # os.walk is noticeably cheaper than repeated Path.rglob calls on Windows
        # network shares and lets inaccessible subfolders fail independently.
        for folder, _dirs, files in os.walk(root, onerror=lambda _error: None):
            for filename in files:
                path = Path(folder) / filename
                try:
                    relative = path.relative_to(root).as_posix()
                    stat = path.stat()
                except (OSError, ValueError):
                    continue
                extension = path.suffix.lower()
                search_key = _compact(f"{relative} {path.stem}")
                asset = ProductionAsset(
                    kind=kind,
                    root=root,
                    path=path,
                    relative=relative,
                    name=path.name,
                    extension=extension,
                    asset_id=self._asset_id(kind, relative),
                    search_key=search_key,
                    modified_at=float(stat.st_mtime or 0),
                )
                if kind == "sketch":
                    signals = f"{asset.name}\n{asset.relative}\n{self._read_machine_text(asset)}"
                    asset = replace(asset, machine_hint=self._detect_machine(signals))
                assets.append(asset)
        assets.sort(key=lambda asset: (asset.relative.lower(), -asset.modified_at))
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
        available = root.exists() and root.is_dir()
        values = self._walk_root(clean_kind, root) if available else []
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
        if asset.extension == ".egl":
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

    def machine_assignment(
        self,
        order: Any,
        item: Any = "",
        job: Any = "",
        *,
        allow_content_read: bool = True,
    ) -> dict[str, Any]:
        sketches = self.matches(
            "sketch", order, item, job, limit=5, require_item=bool(str(item or "").strip())
        )
        for sketch in sketches:
            if sketch.machine_hint:
                return {"machine": sketch.machine_hint, "confidence": "high", "source": sketch.public()}
            content = self._read_machine_text(sketch) if allow_content_read else ""
            signals = f"{sketch.name}\n{sketch.relative}\n{content}"
            machine = self._detect_machine(signals)
            if machine:
                return {"machine": machine, "confidence": "high", "source": sketch.public()}
        return {"machine": "", "confidence": "unknown", "source": sketches[0].public() if sketches else None}

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

        # v0.470: A previously missing evidence result gets one targeted refresh
        # when Staging checks it again. This avoids making every scan re-walk a
        # network share while ensuring a newly-created .egl/WJ completion file
        # releases the item immediately instead of waiting for the normal TTL.
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
        waterjet_evidence = completed_wj[0] if completed_wj else None

        # The sketch is the assignment, but completed-file evidence is the
        # operational truth. Cross-machine evidence intentionally overrides the
        # sketch so WJ-assigned EGL work reports Denver, and vice versa.
        if assigned_machine == "Waterjet" and denver_evidence:
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
            label = f"Fabrication required - {assigned_machine}"
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
            "sketches": [
                asset.public()
                for asset in self.matches("sketch", order, item, job, limit=8, require_item=require_item)
            ],
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
