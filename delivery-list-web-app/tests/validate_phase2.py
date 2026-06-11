#!/usr/bin/env python
"""Phase 2 validation for auth, roles, admin, imports, search, and bay APIs."""

from __future__ import annotations

import gc
import http.client
import json
import os
import sqlite3
import sys
import threading
import time
from dataclasses import replace
from http.server import ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import server as server_mod  # noqa: E402
from delivery_store import SESSION_COOKIE_NAME, create_store  # noqa: E402
from scanner_config import load_config  # noqa: E402


def assert_true(name: str, condition: bool, details: dict | None = None) -> dict:
    if not condition:
        raise AssertionError(f"{name} failed: {details or {}}")
    return {"test": name, "ok": True, **(details or {})}


class ApiClient:
    def __init__(self, port: int) -> None:
        self.port = port

    def request(self, method: str, path: str, body: dict | None = None, cookie: str = "") -> tuple[int, dict, dict[str, str]]:
        payload = json.dumps(body or {}).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"}
        if cookie:
            headers["Cookie"] = cookie
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            connection.request(method, path, payload, headers)
            response = connection.getresponse()
            raw = response.read().decode("utf-8")
            headers_out = {key.lower(): value for key, value in response.getheaders()}
            try:
                data = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                data = {"raw": raw}
            return response.status, data, headers_out
        finally:
            connection.close()


def cookie_from(headers: dict[str, str]) -> str:
    value = headers.get("set-cookie", "")
    return value.split(";", 1)[0]


def main() -> int:
    validation_db = ROOT / "_verification" / f"validation-phase2-{os.getpid()}.db"
    validation_db.parent.mkdir(exist_ok=True)
    cleanup_db(validation_db)

    config = replace(load_config(ROOT), database_path=validation_db)
    store = create_store(config)
    store.initialize()

    results = []

    admin = store.authenticate_user("admin", "Admin123!")
    results.append(
        assert_true(
            "default_admin_login",
            admin["user"]["username"] == "admin" and "manage_users" in admin["user"]["permissions"],
            {"permissions": len(admin["user"]["permissions"])},
        )
    )

    with sqlite3.connect(validation_db) as con:
        password_hash = con.execute("SELECT password_hash FROM users WHERE username = 'admin'").fetchone()[0]
    results.append(
        assert_true(
            "admin_password_hashed",
            password_hash.startswith("pbkdf2_sha256$") and password_hash != "Admin123!",
            {"hashPrefix": password_hash.split("$", 1)[0]},
        )
    )

    operator_name = f"operator_phase2_{os.getpid()}"
    store.create_user(
        {
            "username": operator_name,
            "displayName": "Operator Phase 2",
            "password": "Operator123!",
            "roles": ["Operator"],
        },
        created_by="admin",
    )
    operator = store.authenticate_user(operator_name, "Operator123!")
    results.append(
        assert_true(
            "operator_permissions_limited",
            "scan" in operator["user"]["permissions"] and "manage_users" not in operator["user"]["permissions"],
            {"roles": operator["user"]["roles"]},
        )
    )

    sample = json.loads((ROOT / "data" / "sample-delivery-list.json").read_text(encoding="utf-8"))
    preview = store.preview_import(sample)
    results.append(
        assert_true(
            "import_preview_validates",
            preview["valid"] and preview["rowCount"] == len(sample["items"]) and preview["cpuCount"] == 7,
            {"rows": preview["rowCount"], "cpu": preview["cpuCount"]},
        )
    )

    summary = store.admin_summary()
    reports = store.reports_summary()
    search_results = store.global_search("KENT")
    bays = store.get_bays()
    results.append(assert_true("admin_summary_counts", summary["activeDeliveryLists"] == 4 and summary["activeUsers"] >= 2, summary))
    results.append(assert_true("reports_summary_shape", "badScanCount" in reports and "scansByOperator" in reports, reports))
    results.append(assert_true("global_search_results", len(search_results) > 0, {"count": len(search_results)}))
    results.append(assert_true("seeded_bays_from_workbook_layout", len(bays) >= 717, {"count": len(bays)}))

    dummy_it = store.authenticate_user("itoperator", "Trail123!")
    results.append(
        assert_true(
            "dummy_indian_trail_account_seeded",
            dummy_it["user"]["username"] == "itoperator" and dummy_it["user"]["stageAccess"] == ["Indian Trail"],
            {"stageAccess": dummy_it["user"]["stageAccess"]},
        )
    )

    receive = store.receive_indian_trail_scan(
        {"listId": "2026-04-01-inbound-indian-trail", "barcode": "T200231887001000", "station": "Indian Trail"},
        "admin",
    )
    results.append(assert_true("indian_trail_receive_assigns_bay", receive["ok"] and receive["bayCode"], {"bay": receive["bayCode"]}))

    server_mod.CONFIG = config
    server_mod.STORE = store
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server_mod.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    client = ApiClient(httpd.server_port)

    try:
        status, _, _ = client.request("GET", "/api/delivery-lists")
        results.append(assert_true("http_requires_auth", status == 401, {"status": status}))

        status, payload, _ = client.request("POST", "/api/login", {"username": "admin", "password": "wrong"})
        results.append(assert_true("http_invalid_login_unauthorized", status == 401 and "error" in payload, {"status": status}))

        status, payload, headers = client.request("POST", "/api/login", {"username": "admin", "password": "Admin123!"})
        admin_cookie = cookie_from(headers)
        results.append(
            assert_true(
                "http_admin_login_cookie",
                status == 200 and payload["authenticated"] and admin_cookie.startswith(f"{SESSION_COOKIE_NAME}="),
                {"status": status},
            )
        )

        status, payload, _ = client.request("GET", "/api/delivery-lists", cookie=admin_cookie)
        results.append(assert_true("http_delivery_lists", status == 200 and len(payload["lists"]) == 4, {"status": status}))

        status, payload, _ = client.request("GET", "/api/admin/summary", cookie=admin_cookie)
        results.append(assert_true("http_admin_summary", status == 200 and payload["activeBays"] >= 300, {"status": status, "activeBays": payload.get("activeBays")}))

        status, payload, _ = client.request("GET", "/api/admin/sessions", cookie=admin_cookie)
        results.append(assert_true("http_admin_sessions", status == 200 and len(payload["sessions"]) >= 1, {"status": status, "sessions": len(payload.get("sessions", []))}))

        status, payload, _ = client.request("POST", "/api/import/preview", {"payload": sample}, cookie=admin_cookie)
        results.append(assert_true("http_import_preview", status == 200 and payload["valid"], {"status": status}))

        status, payload, _ = client.request("GET", "/api/search?q=KENT", cookie=admin_cookie)
        results.append(assert_true("http_global_search", status == 200 and len(payload["results"]) > 0, {"status": status}))

        status, payload, _ = client.request("GET", "/api/indian-trail/bays", cookie=admin_cookie)
        results.append(assert_true("http_bays", status == 200 and len(payload["bays"]) >= 717, {"status": status, "count": len(payload.get("bays", []))}))

        status, payload, _ = client.request("GET", "/api/indian-trail/layout", cookie=admin_cookie)
        results.append(assert_true("http_bay_layout", status == 200 and len(payload["cells"]) >= 900, {"status": status, "cells": len(payload.get("cells", []))}))

        http_operator_name = f"operator_http_{os.getpid()}"
        status, payload, _ = client.request(
            "POST",
            "/api/admin/users",
            {
                "username": http_operator_name,
                "displayName": "HTTP Operator",
                "password": "Operator123!",
                "roles": ["Operator"],
            },
            cookie=admin_cookie,
        )
        results.append(assert_true("http_create_operator", status == 200 and payload["user"]["username"] == http_operator_name, {"status": status}))

        status, payload, headers = client.request("POST", "/api/login", {"username": http_operator_name, "password": "Operator123!"})
        operator_cookie = cookie_from(headers)
        results.append(assert_true("http_operator_login", status == 200 and payload["authenticated"], {"status": status}))

        status, _, _ = client.request("GET", "/api/admin/summary", cookie=operator_cookie)
        results.append(assert_true("http_operator_forbidden_admin", status == 403, {"status": status}))

        status, payload, _ = client.request("GET", "/api/delivery-lists", cookie=operator_cookie)
        results.append(
            assert_true(
                "http_operator_stage_filtered_lists",
                status == 200 and payload["lists"] and all("Indian Trail" not in f"{row['stage']} {row['scanner']}" for row in payload["lists"]),
                {"status": status, "lists": [row["id"] for row in payload.get("lists", [])]},
            )
        )

        status, _, _ = client.request("GET", "/api/delivery-lists/2026-04-01-inbound-indian-trail", cookie=operator_cookie)
        results.append(assert_true("http_operator_forbidden_indian_trail_list", status == 403, {"status": status}))

        status, payload, _ = client.request(
            "POST",
            "/api/scans",
            {"listId": "2026-04-01-staging-airport", "barcode": "T200231704003000", "station": "Airport Rd"},
            cookie=operator_cookie,
        )
        results.append(assert_true("http_operator_can_scan", status == 200 and payload["lastScan"]["ok"], {"status": status}))

        status, payload, _ = client.request("GET", "/api/export.csv?listId=2026-04-01-staging-airport", cookie=operator_cookie)
        results.append(assert_true("http_operator_can_export_current_list", status == 200 and "order" in payload.get("raw", "").lower(), {"status": status}))

        indian_trail_operator_name = f"it_operator_{os.getpid()}"
        status, payload, _ = client.request(
            "POST",
            "/api/admin/users",
            {
                "username": indian_trail_operator_name,
                "displayName": "Indian Trail Operator",
                "password": "Operator123!",
                "roles": ["Indian Trail Operator"],
            },
            cookie=admin_cookie,
        )
        results.append(assert_true("http_create_indian_trail_operator", status == 200 and payload["user"]["username"] == indian_trail_operator_name, {"status": status}))

        status, payload, headers = client.request("POST", "/api/login", {"username": indian_trail_operator_name, "password": "Operator123!"})
        indian_trail_cookie = cookie_from(headers)
        results.append(assert_true("http_indian_trail_operator_login", status == 200 and payload["authenticated"], {"status": status}))

        status, _, _ = client.request("GET", "/api/admin/summary", cookie=indian_trail_cookie)
        results.append(assert_true("http_indian_trail_forbidden_admin", status == 403, {"status": status}))

        status, payload, _ = client.request("GET", "/api/delivery-lists", cookie=indian_trail_cookie)
        results.append(
            assert_true(
                "http_indian_trail_stage_filtered_lists",
                status == 200 and payload["lists"] and all("Indian Trail" in f"{row['stage']} {row['scanner']}" for row in payload["lists"]),
                {"status": status, "lists": [row["id"] for row in payload.get("lists", [])]},
            )
        )

        status, _, _ = client.request("GET", "/api/delivery-lists/2026-04-01-staging-airport", cookie=indian_trail_cookie)
        results.append(assert_true("http_indian_trail_forbidden_airport_list", status == 403, {"status": status}))

        status, payload, _ = client.request(
            "POST",
            "/api/indian-trail/receive",
            {"listId": "2026-04-01-inbound-indian-trail", "barcode": "T200231704004000", "station": "Indian Trail"},
            cookie=indian_trail_cookie,
        )
        results.append(
            assert_true(
                "http_indian_trail_operator_receive",
                status == 200 and payload["ok"] and payload["bayCode"],
                {"status": status, "bay": payload.get("bayCode")},
            )
        )
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)

    print(json.dumps({"ok": True, "results": results}, indent=2))

    with sqlite3.connect(validation_db) as con:
        con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    del store
    gc.collect()
    time.sleep(0.5)
    cleanup_db(validation_db)
    return 0


def cleanup_db(path: Path) -> None:
    for suffix in ("", "-wal", "-shm"):
        target = Path(str(path) + suffix)
        if not target.exists():
            continue
        try:
            target.unlink()
        except PermissionError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
