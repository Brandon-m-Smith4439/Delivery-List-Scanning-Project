#!/usr/bin/env python3
"""Build a clean full-project v148 ZIP from the installed local project folder."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import zipfile
from hashlib import sha256
from pathlib import Path

EXCLUDED_DIRS = {
    ".git",
    ".github",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "backups",
    "logs",
    "preview",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".db", ".sqlite", ".sqlite3", ".wal", ".shm"}
EXCLUDED_NAMES = {
    "delivery-scanner-pilot.db",
    "graph-email-config.json",
    "microsoft-graph-email.json",
}


def excluded(relative: Path) -> bool:
    if any(part.lower() in EXCLUDED_DIRS for part in relative.parts[:-1]):
        return True
    name = relative.name.lower()
    if name in EXCLUDED_NAMES:
        return True
    if any(name.endswith(suffix) for suffix in EXCLUDED_SUFFIXES):
        return True
    if name.startswith("delivery_list_scanner_v148_") and name.endswith(".zip"):
        return True
    return False


def file_hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parent))
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    project_root = Path(str(args.project_root).strip().strip('"')).expanduser().resolve()
    required = (
        project_root / "index.html",
        project_root / "app.js",
        project_root / "delivery_store.py",
        project_root / "README.md",
        project_root / "README_CHANGELOG.md",
        project_root / "bay-scanner-v148.css",
    )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError("v148 is not fully installed: " + ", ".join(missing))

    if "20260728-v148" not in (project_root / "index.html").read_text(encoding="utf-8"):
        raise RuntimeError("index.html is not using the v148 cache key")

    output = Path(args.output).expanduser().resolve() if args.output else (
        project_root.parent / "Delivery_List_Scanner_v148_Full_Project.zip"
    )

    with tempfile.TemporaryDirectory(prefix="delivery-scanner-v148-") as temp_name:
        staging = Path(temp_name) / "Delivery_List_Scanner_v148"
        staging.mkdir(parents=True)
        manifest: list[dict[str, object]] = []

        for source in sorted(project_root.rglob("*")):
            if not source.is_file():
                continue
            relative = source.relative_to(project_root)
            if excluded(relative):
                continue
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            manifest.append({
                "path": relative.as_posix(),
                "bytes": target.stat().st_size,
                "sha256": file_hash(target),
            })

        (staging / "FULL_PROJECT_PACKAGE_MANIFEST.json").write_text(
            json.dumps({"release": 148, "files": manifest}, indent=2) + "\n",
            encoding="utf-8",
        )

        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            output.unlink()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(staging.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(staging.parent).as_posix())

    print(f"Created: {output}")
    print("Production databases, secrets, logs, backups, caches, and generated preview folders were excluded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
