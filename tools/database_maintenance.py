#!/usr/bin/env python3
"""Explicit SQLite maintenance utilities for the Delivery List Scanner."""

from __future__ import annotations

import argparse
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database_migrations import create_verified_backup  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", nargs="?", default=str(ROOT / "data" / "delivery-scanner-pilot.db"))
    parser.add_argument("--optimize", action="store_true", help="Run PRAGMA optimize")
    parser.add_argument("--checkpoint", action="store_true", help="Run a WAL TRUNCATE checkpoint")
    parser.add_argument("--vacuum", action="store_true", help="Create a verified backup, then run VACUUM")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = Path(args.database).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    if not any((args.optimize, args.checkpoint, args.vacuum)):
        raise ValueError("Select --optimize, --checkpoint, and/or --vacuum")
    if args.vacuum:
        backup = create_verified_backup(path)
        print(f"Verified backup: {backup}")
    connection = sqlite3.connect(path, timeout=60)
    try:
        connection.execute("PRAGMA busy_timeout = 60000")
        if args.checkpoint:
            print("WAL checkpoint:", connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone())
        if args.optimize:
            connection.execute("PRAGMA optimize")
            print("PRAGMA optimize complete")
        if args.vacuum:
            connection.execute("VACUUM")
            print("VACUUM complete")
    finally:
        connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

