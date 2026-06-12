#!/usr/bin/env python
"""Local pilot server for the delivery-list scanner web app."""

from __future__ import annotations

import json
from http.cookies import SimpleCookie
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from delivery_store import SESSION_COOKIE_NAME, create_store, request_station, request_user_name
from scanner_config import load_config


ROOT = Path(__file__).resolve().parent
CONFIG = load_config(ROOT)
STORE = create_store(CONFIG)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def session_token(self) -> str:
        cookie_header = self.headers.get("Cookie", "")
        if not cookie_header:
            return ""
        cookie = SimpleCookie(cookie_header)
        morsel = cookie.get(SESSION_COOKIE_NAME)
        return morsel.value if morsel else ""

    def current_user(self) -> dict | None:
        return STORE.get_user_by_session(self.session_token())

    def require_permission(self, permission: str) -> dict | None:
        user = self.current_user()
        if not user:
            self.send_json({"error": "Authentication required"}, HTTPStatus.UNAUTHORIZED)
            return None
        if permission not in user.get("permissions", []):
            self.send_json({"error": "Permission denied", "permission": permission}, HTTPStatus.FORBIDDEN)
            return None
        return user

    def set_session_cookie(self, token: str, expires_at: str) -> None:
        secure = "; Secure" if CONFIG.production else ""
        self.send_header(
            "Set-Cookie",
            f"{SESSION_COOKIE_NAME}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=43200{secure}",
        )

    def clear_session_cookie(self) -> None:
        self.send_header(
            "Set-Cookie",
            f"{SESSION_COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0",
        )

    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/api/health":
            self.send_json(STORE.health())
            return

        if parsed.path == "/api/session":
            user = self.current_user()
            self.send_json({"authenticated": bool(user), "user": user})
            return

        if parsed.path == "/api/delivery-lists":
            user = self.require_permission("view_lists")
            if not user:
                return
            self.send_json({"lists": STORE.get_delivery_lists(user)})
            return

        if parsed.path == "/api/stations":
            if not self.require_permission("view_stations"):
                return
            self.send_json({"stations": STORE.get_stations()})
            return

        if parsed.path == "/api/exceptions":
            if not self.require_permission("view_exceptions"):
                return
            filters = {key: values[0] for key, values in parse_qs(parsed.query).items()}
            self.send_json({"exceptions": STORE.get_exceptions(filters)})
            return

        if parsed.path == "/api/admin/summary":
            if not self.require_permission("view_admin"):
                return
            self.send_json(STORE.admin_summary())
            return

        if parsed.path == "/api/admin/users":
            if not self.require_permission("manage_users"):
                return
            self.send_json({"users": STORE.list_users()})
            return

        if parsed.path == "/api/admin/permissions":
            if not self.require_permission("manage_roles"):
                return
            self.send_json({"permissions": STORE.get_permissions()})
            return

        if parsed.path == "/api/admin/sessions":
            if not self.require_permission("view_active_sessions"):
                return
            self.send_json({"sessions": STORE.list_active_sessions()})
            return

        if parsed.path == "/api/search":
            user = self.require_permission("global_search")
            if not user:
                return
            query = parse_qs(parsed.query).get("q", [""])[0]
            self.send_json({"results": STORE.global_search(query, user)})
            return

        if parsed.path == "/api/reports/summary":
            if not self.require_permission("view_reports"):
                return
            self.send_json(STORE.reports_summary())
            return

        if parsed.path == "/api/indian-trail/summary":
            if not self.require_permission("view_indian_trail"):
                return
            self.send_json(STORE.indian_trail_summary())
            return

        if parsed.path == "/api/indian-trail/bays":
            if not self.require_permission("view_bays"):
                return
            self.send_json({"bays": STORE.get_bays()})
            return

        if parsed.path == "/api/indian-trail/layout":
            if not self.require_permission("view_bays"):
                return
            self.send_json(STORE.get_bay_layout())
            return

        if parsed.path == "/api/indian-trail/events":
            if not self.require_permission("view_bays"):
                return
            limit = parse_qs(parsed.query).get("limit", ["20"])[0]
            self.send_json({"events": STORE.get_bay_events(int(limit or 20))})
            return

        if parsed.path.startswith("/api/delivery-lists/"):
            user = self.require_permission("view_lists")
            if not user:
                return
            list_id = unquote(parsed.path.rsplit("/", 1)[-1])
            try:
                self.send_json(STORE.get_delivery_list(list_id, user=user))
            except PermissionError as exc:
                self.send_json({"error": str(exc)}, HTTPStatus.FORBIDDEN)
            except KeyError:
                self.send_json({"error": "Delivery list not found"}, HTTPStatus.NOT_FOUND)
            return

        if parsed.path == "/api/export.csv":
            user = self.require_permission("export_reports")
            if not user:
                return
            list_id = parse_qs(parsed.query).get("listId", [""])[0]
            if not STORE.user_can_access_list(user, list_id):
                self.send_json({"error": "Permission denied for this delivery-list stage"}, HTTPStatus.FORBIDDEN)
                return
            body = STORE.export_csv(list_id).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", "attachment; filename=delivery-list-export.csv")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            data = self.read_json()

            if parsed.path == "/api/login":
                try:
                    payload = STORE.authenticate_user(str(data.get("username") or ""), str(data.get("password") or ""))
                except PermissionError as exc:
                    self.send_json({"error": str(exc)}, HTTPStatus.UNAUTHORIZED)
                    return
                body = json.dumps({"authenticated": True, "user": payload["user"]}, indent=2).encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.set_session_cookie(payload["token"], payload["expiresAt"])
                self.end_headers()
                self.wfile.write(body)
                return

            if parsed.path == "/api/logout":
                STORE.delete_session(self.session_token())
                body = json.dumps({"ok": True}, indent=2).encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.clear_session_cookie()
                self.end_headers()
                self.wfile.write(body)
                return

            if parsed.path == "/api/scans":
                user = self.require_permission("scan")
                if not user:
                    return
                if not STORE.user_can_access_list(user, str(data.get("listId") or "")):
                    self.send_json({"error": "Permission denied for this delivery-list stage"}, HTTPStatus.FORBIDDEN)
                    return
                data["user"] = user["username"]
                self.send_json(STORE.record_scan(data))
                return

            if parsed.path == "/api/reset":
                user = self.require_permission("reset_lists")
                if not user:
                    return
                if not STORE.user_can_access_list(user, str(data.get("listId") or "")):
                    self.send_json({"error": "Permission denied for this delivery-list stage"}, HTTPStatus.FORBIDDEN)
                    return
                self.send_json(
                    STORE.reset_stage(
                        str(data.get("listId") or ""),
                        user["username"],
                        request_station(data),
                    )
                )
                return

            if parsed.path == "/api/undo":
                user = self.require_permission("undo_scan")
                if not user:
                    return
                if not STORE.user_can_access_list(user, str(data.get("listId") or "")):
                    self.send_json({"error": "Permission denied for this delivery-list stage"}, HTTPStatus.FORBIDDEN)
                    return
                self.send_json(
                    STORE.undo_last_scan(
                        str(data.get("listId") or ""),
                        user["username"],
                        request_station(data),
                    )
                )
                return

            if parsed.path == "/api/stations":
                if not self.require_permission("manage_stations"):
                    return
                self.send_json(STORE.add_station(str(data.get("name") or "")))
                return

            if parsed.path == "/api/stations/remove":
                if not self.require_permission("remove_stations"):
                    return
                self.send_json(STORE.remove_station(str(data.get("name") or "")))
                return

            if parsed.path == "/api/import":
                user = self.require_permission("import_delivery_lists")
                if not user:
                    return
                data["user"] = user["username"]
                self.send_json(STORE.import_delivery_list(data))
                return

            if parsed.path == "/api/import/preview":
                if not self.require_permission("preview_import"):
                    return
                self.send_json(STORE.preview_import(data.get("payload") or data))
                return

            if parsed.path == "/api/exceptions/resolve":
                user = self.require_permission("resolve_exceptions")
                if not user:
                    return
                self.send_json(STORE.resolve_exception(data, user["username"]))
                return

            if parsed.path == "/api/admin/users":
                user = self.require_permission("manage_users")
                if not user:
                    return
                self.send_json({"user": STORE.create_user(data, created_by=user["username"])})
                return

            if parsed.path == "/api/admin/users/deactivate":
                user = self.require_permission("deactivate_users")
                if not user:
                    return
                self.send_json(STORE.deactivate_user(str(data.get("username") or ""), deactivated_by=user["username"]))
                return

            if parsed.path == "/api/admin/line-item":
                user = self.require_permission("edit_delivery_lists")
                if not user:
                    return
                self.send_json(STORE.update_line_item(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/receive":
                user = self.require_permission("indian_trail_receive")
                if not user:
                    return
                if data.get("listId") and not STORE.user_can_access_list(user, str(data.get("listId") or "")):
                    self.send_json({"error": "Permission denied for this delivery-list stage"}, HTTPStatus.FORBIDDEN)
                    return
                self.send_json(STORE.receive_indian_trail_scan(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/assign":
                user = self.require_permission("assign_bay")
                if not user:
                    return
                self.send_json(STORE.assign_bay(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/move":
                user = self.require_permission("move_bay")
                if not user:
                    return
                self.send_json(STORE.move_bay_assignment(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/clear":
                user = self.require_permission("clear_bay")
                if not user:
                    return
                self.send_json(STORE.clear_bay(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/mark-sdi":
                user = self.require_permission("mark_sdi")
                if not user:
                    return
                self.send_json(STORE.mark_sdi(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/remove-sdi":
                user = self.require_permission("remove_sdi")
                if not user:
                    return
                self.send_json(STORE.remove_sdi(data, user["username"]))
                return

            if parsed.path == "/api/indian-trail/bay-check":
                user = self.require_permission("bay_check")
                if not user:
                    return
                self.send_json(STORE.bay_check(data, user["username"]))
                return

            self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
        except PermissionError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.FORBIDDEN)
        except Exception as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)


def main() -> int:
    STORE.initialize()
    server = ThreadingHTTPServer((CONFIG.host, CONFIG.port), Handler)
    print(f"Delivery List Scanner running at http://{CONFIG.host}:{CONFIG.port}/")
    print(f"Database type: {CONFIG.database_type}")
    print(f"Database: {CONFIG.database_path}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
