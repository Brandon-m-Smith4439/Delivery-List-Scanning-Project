#!/usr/bin/env python3
"""Build the database-safe Delivery List Scanner v097 release ZIP."""

from __future__ import annotations

from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "Delivery_List_Scanner_v097.zip"

ROOT_FILES = {
    ".dockerignore", ".env.azure.example", ".gitignore", "app.js", "azure_sql_compat.py",
    "azure_sql_schema.sql", "barefoot-builders-firstsource-logo.png", "barefoot-logo-sidebar.png",
    "barefoot-logo.png", "Configure-MicrosoftGraphEmail.bat", "Configure-MicrosoftGraphEmail.ps1",
    "Create Desktop Shortcut.bat", "Create-DeliveryScannerShortcut.ps1", "database_contract.py",
    "database_migrations.py", "delivery_store.py", "Dockerfile", "index.html",
    "migrate_sqlite_to_azure_sql.py", "pytest.ini", "README.md", "README_CHANGELOG.md",
    "requirements.txt", "scanner_config.py", "server.py", "Start-DeliveryScannerWebApp.bat",
    "Start-DeliveryScannerWebApp.ps1", "styles.css",
}


def included_files() -> list[Path]:
    files = [ROOT / name for name in ROOT_FILES if (ROOT / name).is_file()]
    for folder in ("assets", "docs", "tests", "tools"):
        files.extend(
            path for path in (ROOT / folder).rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
        )
    layout = ROOT / "data" / "indian-trail-bay-layout.json"
    if layout.exists():
        files.append(layout)
    return sorted(set(files), key=lambda path: path.relative_to(ROOT).as_posix().lower())


def main() -> int:
    if OUTPUT.exists():
        OUTPUT.unlink()
    files = included_files()
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            archive.write(path, path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(OUTPUT) as archive:
        names = set(archive.namelist())
        if any(name.endswith((".db", ".db-wal", ".db-shm")) for name in names):
            raise RuntimeError("Release package unexpectedly contains a database")
        required = {"server.py", "delivery_store.py", "database_migrations.py", "azure_sql_schema.sql"}
        missing = sorted(required - names)
        if missing:
            raise RuntimeError(f"Release package is missing: {', '.join(missing)}")
    print(f"Created {OUTPUT.name}: {len(files)} files, {OUTPUT.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

