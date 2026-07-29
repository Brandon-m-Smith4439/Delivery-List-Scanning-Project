#!/usr/bin/env python
# File: automation/crystal_delivery_export/import_delivery_folder.py
"""Import Crystal Report exports into the existing Delivery List Scanner store.

This wrapper intentionally reuses backend/config.py and backend/store.py instead
of duplicating the scanner's import rules. The PowerShell exporter supplies the
UNC folder through DLS_TEMP_DELIVERY_LISTS_PATH for this process only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import automated delivery-list exports.")
    parser.add_argument("--project-root", required=True, help="Delivery List Scanner project folder.")
    parser.add_argument("--folder", required=True, help="UNC folder containing exported workbooks.")
    parser.add_argument(
        "--date-from",
        default=(date.today() - timedelta(days=7)).isoformat(),
        help="Oldest delivery date to import, in YYYY-MM-DD format.",
    )
    parser.add_argument("--date-to", default="", help="Optional newest delivery date in YYYY-MM-DD format.")
    parser.add_argument("--user", default="crystal-auto-import", help="Audit username recorded by the importer.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).expanduser().resolve()
    if not (project_root / "backend" / "config.py").is_file():
        raise FileNotFoundError(f"backend/config.py was not found under {project_root}")
    if not (project_root / "backend" / "store.py").is_file():
        raise FileNotFoundError(f"backend/store.py was not found under {project_root}")

    os.environ["DLS_TEMP_DELIVERY_LISTS_PATH"] = args.folder
    sys.path.insert(0, str(project_root))

    from backend.config import load_config
    from backend.store import create_store

    config = load_config(project_root)
    store = create_store(config)
    store.initialize()
    result = store.import_delivery_folder(
        {
            "user": args.user,
            "dateFrom": args.date_from,
            "dateTo": args.date_to,
        }
    )
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Automatic delivery-list import failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
