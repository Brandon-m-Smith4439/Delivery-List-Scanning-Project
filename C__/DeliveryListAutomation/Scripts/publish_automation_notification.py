#!/usr/bin/env python3
# File: automation/sql_delivery_export/publish_automation_notification.py
"""Publish exporter results through the scanner's existing notification system.

v121 accepts a small JSON request file from PowerShell. This avoids Windows
command-line quoting limits for long notification messages and payloads while
continuing to use the scanner's maintained notification store API.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    """Parse either the v121 request file or the legacy individual arguments."""
    parser = argparse.ArgumentParser(description="Publish a delivery automation notification.")
    parser.add_argument("--request-file", default="", help="JSON request written by the automation runner.")
    parser.add_argument("--project-root", default="", help="Delivery List Scanner project folder.")
    parser.add_argument("--type", default="notice", choices=("success", "notice", "warning", "error"))
    parser.add_argument("--title", default="")
    parser.add_argument("--message", default="")
    parser.add_argument("--created-by", default="sql-delivery-automation")
    parser.add_argument("--payload-base64", default="")
    parser.add_argument("--expires-hours", type=int, default=12)
    parser.add_argument(
        "--initialize-store",
        choices=("true", "false"),
        default="false",
        help="Initialize the scanner store before publishing.",
    )
    return parser.parse_args()


def decode_payload(encoded: str) -> dict[str, Any]:
    """Decode the optional base64 JSON details object."""
    if not encoded:
        return {}
    raw = base64.b64decode(encoded.encode("ascii"), validate=True).decode("utf-8")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("Notification payload must decode to a JSON object.")
    return payload


def read_request(args: argparse.Namespace) -> dict[str, Any]:
    """Normalize request-file and legacy command-line inputs."""
    if args.request_file:
        path = Path(args.request_file).expanduser().resolve()
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            raise ValueError("Notification request file must contain a JSON object.")
        return {
            "project_root": str(data.get("projectRoot") or "").strip(),
            "notification_type": str(data.get("notificationType") or "notice").strip().lower(),
            "title": str(data.get("title") or "").strip(),
            "message": str(data.get("message") or "").strip(),
            "created_by": str(data.get("createdBy") or "sql-delivery-automation").strip(),
            "payload": data.get("payload") if isinstance(data.get("payload"), dict) else {},
            "expires_hours": int(data.get("expiresHours") or 12),
            "initialize_store": bool(data.get("initializeStore", False)),
        }

    return {
        "project_root": str(args.project_root or "").strip(),
        "notification_type": str(args.type or "notice").strip().lower(),
        "title": str(args.title or "").strip(),
        "message": str(args.message or "").strip(),
        "created_by": str(args.created_by or "sql-delivery-automation").strip(),
        "payload": decode_payload(args.payload_base64),
        "expires_hours": int(args.expires_hours or 12),
        "initialize_store": args.initialize_store == "true",
    }


def main() -> int:
    """Load the maintained scanner store and create one app notification."""
    request = read_request(parse_args())
    if request["notification_type"] not in {"success", "notice", "warning", "error"}:
        raise ValueError("Notification type must be success, notice, warning, or error.")
    if not request["project_root"]:
        raise ValueError("Project root is required.")
    if not request["title"]:
        raise ValueError("Notification title is required.")

    project_root = Path(request["project_root"]).expanduser().resolve()
    required_files = [project_root / "backend" / "config.py", project_root / "backend" / "store.py"]
    missing = [str(path) for path in required_files if not path.is_file()]
    if missing:
        raise FileNotFoundError("Required scanner files were not found: " + ", ".join(missing))

    sys.path.insert(0, str(project_root))
    from backend.config import load_config
    from backend.store import create_store

    config = load_config(project_root)
    store = create_store(config)
    if request["initialize_store"]:
        store.initialize()

    publisher = getattr(store, "create_app_notification", None)
    connector = getattr(store, "connect", None)
    if not callable(publisher) or not callable(connector):
        raise RuntimeError(
            "The configured scanner store does not expose create_app_notification(...) and connect()."
        )

    with connector() as connection:
        notification_id = publisher(
            connection,
            request["notification_type"],
            request["title"],
            request["message"],
            request["created_by"],
            payload=request["payload"],
            expires_in_hours=max(int(request["expires_hours"]), 1),
            acknowledge_creator=False,
        )
        connection.commit()

    print(json.dumps({"ok": True, "notificationId": notification_id}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Automation notification could not be published: {exc}", file=sys.stderr)
        raise SystemExit(1)
