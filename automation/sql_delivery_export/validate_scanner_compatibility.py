#!/usr/bin/env python3
# File: automation/sql_delivery_export/validate_scanner_compatibility.py
"""Validate the current scanner's public configuration/store integration points.

This script imports the latest scanner code without initializing or modifying its
active database. It verifies only the interfaces required by the SQL exporter.
"""

from __future__ import annotations

import argparse
import inspect
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Delivery List Scanner compatibility.")
    parser.add_argument("--project-root", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.project_root).expanduser().resolve()
    required = [root / "backend" / "config.py", root / "backend" / "store.py"]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing scanner files: " + ", ".join(missing))

    sys.path.insert(0, str(root))
    from backend.config import load_config
    from backend.store import create_store

    config = load_config(root)
    store = create_store(config)
    importer = getattr(store, "import_delivery_folder", None)
    if not callable(importer):
        raise RuntimeError("The current scanner store does not expose import_delivery_folder(payload).")

    signature = inspect.signature(importer)
    if len(signature.parameters) < 1:
        raise RuntimeError("import_delivery_folder no longer accepts the expected payload argument.")

    notifier = getattr(store, "create_app_notification", None)
    connector = getattr(store, "connect", None)
    if not callable(notifier) or not callable(connector):
        raise RuntimeError(
            "The current scanner store does not expose create_app_notification(...) and connect()."
        )
    notification_signature = inspect.signature(notifier)

    result = {
        "projectRoot": str(root),
        "databaseType": str(getattr(config, "database_type", "")),
        "storeType": type(store).__name__,
        "importMethod": str(signature),
        "notificationMethod": str(notification_signature),
        "compatible": True,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Scanner compatibility validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
