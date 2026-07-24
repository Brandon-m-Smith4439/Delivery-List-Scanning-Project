#!/usr/bin/env python3
"""Patch the current v134 server with v135 operations routes safely and idempotently."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import py_compile
import shutil
import sys

MARKER = "DLS_V135_OPERATIONS_ROUTES"

IMPORT_ANCHOR = "from delivery_import_safety import install_safe_delivery_import\n"
IMPORT_BLOCK = "from operations_features import OperationsFeatureService\n"

GLOBAL_ANCHOR = "DELIVERY_AUTOMATION = DeliveryAutomationController(ROOT, CONFIG, STORE)\n"
GLOBAL_BLOCK = "OPERATIONS = OperationsFeatureService(STORE, CONFIG, ROOT)\n"

GET_ANCHOR = '''        if parsed.path == "/api/admin/delivery-automation":\n'''
GET_BLOCK = r'''        # DLS_V135_OPERATIONS_ROUTES: per-user line flags, rejects, and packing history.
        if parsed.path == "/api/operations/line-flags":
            user = self.require_permission("view_lists")
            if not user:
                return
            list_id = str(parse_qs(parsed.query).get("listId", [""])[0] or "").strip()
            if not list_id:
                self.send_json({"error": "listId is required"}, HTTPStatus.BAD_REQUEST)
                return
            if not STORE.user_can_access_list(user, list_id):
                self.send_json({"error": "Permission denied for this delivery-list stage"}, HTTPStatus.FORBIDDEN)
                return
            self.send_json(OPERATIONS.line_flags(list_id, user["username"]))
            return

        if parsed.path == "/api/rejects":
            if not self.require_permission("view_lists"):
                return
            params = parse_qs(parsed.query)
            self.send_json(
                OPERATIONS.list_rejects(
                    date_from=params.get("dateFrom", [""])[0],
                    date_to=params.get("dateTo", [""])[0],
                    query=params.get("q", [""])[0],
                    limit=int(params.get("limit", ["500"])[0] or 500),
                )
            )
            return

        if parsed.path == "/api/rejects/catalog":
            if not self.require_permission("view_lists"):
                return
            self.send_json(OPERATIONS.reject_catalog())
            return

        if parsed.path == "/api/rejects/matches":
            if not self.require_permission("view_lists"):
                return
            params = parse_qs(parsed.query)
            self.send_json(
                OPERATIONS.reject_matches(
                    params.get("order", [""])[0],
                    params.get("item", [""])[0],
                )
            )
            return

        packing_history_print_match = re.match(r"^/api/racks/packing-history/(\d+)/print$", parsed.path)
        if packing_history_print_match:
            if not self.require_any_permission("view_racks", "export_reports"):
                return
            self.send_html(OPERATIONS.packing_history_print_html(int(packing_history_print_match.group(1))))
            return

        if parsed.path == "/api/racks/packing-history":
            if not self.require_any_permission("view_racks", "export_reports"):
                return
            limit = int(parse_qs(parsed.query).get("limit", ["250"])[0] or 250)
            self.send_json(OPERATIONS.packing_history(limit))
            return

'''

POST_ANCHOR = '''            if parsed.path == "/api/scans":\n'''
POST_BLOCK = r'''            # DLS_V135_OPERATIONS_POST_ROUTES
            if parsed.path == "/api/operations/line-flags/acknowledge":
                user = self.require_permission("view_lists")
                if not user:
                    return
                list_id = str(data.get("listId") or "").strip()
                if not list_id:
                    self.send_json({"error": "listId is required"}, HTTPStatus.BAD_REQUEST)
                    return
                if not STORE.user_can_access_list(user, list_id):
                    self.send_json({"error": "Permission denied for this delivery-list stage"}, HTTPStatus.FORBIDDEN)
                    return
                notice_ids = data.get("noticeIds") if isinstance(data.get("noticeIds"), list) else []
                self.send_json(OPERATIONS.acknowledge_line_updates(list_id, notice_ids, user["username"]))
                return

            if parsed.path == "/api/rejects":
                user = self.require_any_permission("scan", "manual_adjust", "resolve_exceptions")
                if not user:
                    return
                self.send_json(OPERATIONS.create_reject(data, user["username"]))
                return

            if parsed.path == "/api/rejects/catalog":
                user = self.require_permission("view_admin")
                if not user:
                    return
                self.send_json(
                    OPERATIONS.upsert_reject_catalog(
                        str(data.get("kind") or ""),
                        str(data.get("label") or ""),
                        user["username"],
                    )
                )
                return

            if parsed.path == "/api/rejects/catalog/remove":
                user = self.require_permission("view_admin")
                if not user:
                    return
                self.send_json(
                    OPERATIONS.remove_reject_catalog(
                        str(data.get("kind") or ""),
                        int(data.get("id") or 0),
                        user["username"],
                    )
                )
                return

            if parsed.path == "/api/admin/manual-order":
                user = self.require_permission("edit_delivery_lists")
                if not user:
                    return
                self.send_json(OPERATIONS.create_manual_order(data, user["username"]))
                return

            if parsed.path == "/api/racks/packing-history":
                user = self.require_any_permission("view_racks", "export_reports")
                if not user:
                    return
                self.send_json(OPERATIONS.record_packing_print(data, user["username"]))
                return

'''

STORE_MARKER = "DLS_V135_PRESERVE_MANUAL_LINES"
STORE_DECLARATION_ANCHOR = '''            preserved_rack_items: list[dict[str, Any]] = []
            original_total_qty = 0
'''
STORE_DECLARATION_BLOCK = '''            preserved_rack_items: list[dict[str, Any]] = []
            # DLS_V135_PRESERVE_MANUAL_LINES: keep manually added orders through
            # every automatic folder/SQL refresh until the source file contains
            # the same order/item and takes ownership of it.
            preserved_manual_items: list[dict[str, Any]] = []
            original_total_qty = 0
'''
STORE_CAPTURE_ANCHOR = '''                original_total_qty += int(row["qty"] or 0)
                previous_by_id[line_key] = record
'''
STORE_CAPTURE_BLOCK = '''                manual_source = str(row_value(row, "manual_source", "") or "")
                manual_only = int(row_value(row, "manual_only", 0) or 0)
                if manual_source or manual_only:
                    preserved_manual_items.append(
                        {
                            "source_id": source_key,
                            "order_item_key": order_item_key,
                            "manual_only": manual_only,
                            "manual_source": manual_source,
                            "clone": {
                                "id": line_key,
                                "source_id": source_key,
                                "barcode": str(row["barcode"] or ""),
                                "order_no": str(row["order_no"] or ""),
                                "item_no": str(row["item_no"] or "").zfill(3),
                                "qty": int(row["qty"] or 0),
                                "scanned_qty": scanned_qty,
                                "dimensions": str(row["dimensions"] or ""),
                                "customer": str(row["customer"] or ""),
                                "route": str(row["route"] or ""),
                                "source_route": str(row_value(row, "source_route", "manual") or "manual"),
                                "job": str(row["job"] or ""),
                                "product": str(row["product"] or ""),
                                "process_state": str(row["process_state"] or ""),
                                "queue_state": str(row["queue_state"] or ""),
                                "suggested_bay": str(row["suggested_bay"] or ""),
                                "priority_delivery_date": str(row_value(row, "priority_delivery_date", "") or ""),
                                "priority_direct_to_truck": int(row_value(row, "priority_direct_to_truck", 0) or 0),
                                "internal_reject_count": int(row_value(row, "internal_reject_count", 0) or 0),
                                "last_reject_reason": str(row_value(row, "last_reject_reason", "") or ""),
                                "last_reject_location": str(row_value(row, "last_reject_location", "") or ""),
                                "last_rejected_at": str(row_value(row, "last_rejected_at", "") or ""),
                            },
                        }
                    )
                original_total_qty += int(row["qty"] or 0)
                previous_by_id[line_key] = record
'''
STORE_REINSERT_ANCHOR = '''            con.execute("DELETE FROM line_items WHERE list_id = ?", (list_id,))
            cloned_items = self.insert_line_items(con, list_id, items)
            summary["originalQty"] = original_total_qty
'''
STORE_REINSERT_BLOCK = '''            incoming_order_keys = {
                f"{str(item.get('order') or '').strip()}-{str(item.get('item') or '').strip().zfill(3)}"
                for item in items
            }
            preserved_manual_total = sum(
                int(record["clone"]["qty"] or 0)
                for record in preserved_manual_items
                if record["order_item_key"] not in incoming_order_keys
            )
            summary["totalQty"] = sum(int(item.get("qty") or 0) for item in items) + preserved_manual_total

            con.execute("DELETE FROM line_items WHERE list_id = ?", (list_id,))
            cloned_items = self.insert_line_items(con, list_id, items)
            for manual_record in preserved_manual_items:
                if manual_record["order_item_key"] in incoming_order_keys:
                    continue
                cloned = manual_record["clone"]
                con.execute(
                    "INSERT INTO line_items ("
                    "id, list_id, source_id, barcode, order_no, item_no, qty, scanned_qty, "
                    "dimensions, customer, route, source_route, job, product, process_state, "
                    "queue_state, suggested_bay, priority_delivery_date, priority_direct_to_truck, "
                    "manual_only, manual_source, internal_reject_count, last_reject_reason, "
                    "last_reject_location, last_rejected_at"
                    ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        cloned["id"], list_id, cloned["source_id"], cloned["barcode"],
                        cloned["order_no"], cloned["item_no"], cloned["qty"], cloned["scanned_qty"],
                        cloned["dimensions"], cloned["customer"], cloned["route"], cloned["source_route"],
                        cloned["job"], cloned["product"], cloned["process_state"], cloned["queue_state"],
                        cloned["suggested_bay"], cloned["priority_delivery_date"],
                        cloned["priority_direct_to_truck"], manual_record["manual_only"],
                        manual_record["manual_source"], cloned["internal_reject_count"],
                        cloned["last_reject_reason"], cloned["last_reject_location"], cloned["last_rejected_at"],
                    ),
                )
                cloned_items.append(cloned)
            summary["originalQty"] = original_total_qty
'''



def replace_once(text: str, anchor: str, block: str, label: str) -> str:
    if block.strip() in text:
        return text
    if anchor not in text:
        raise RuntimeError(f"Could not find the {label} anchor in the current project source")
    return text.replace(anchor, block + anchor, 1)


def replace_exact(text: str, anchor: str, replacement: str, label: str) -> str:
    """Replace one complete maintained block instead of appending a duplicate."""
    if anchor not in text:
        raise RuntimeError(f"Could not find the {label} anchor in the current project source")
    return text.replace(anchor, replacement, 1)


def patch_delivery_store(text: str) -> str:
    if STORE_MARKER in text:
        return text
    updated = replace_exact(text, STORE_DECLARATION_ANCHOR, STORE_DECLARATION_BLOCK, "manual-line declaration")
    updated = replace_exact(updated, STORE_CAPTURE_ANCHOR, STORE_CAPTURE_BLOCK, "manual-line capture")
    updated = replace_exact(updated, STORE_REINSERT_ANCHOR, STORE_REINSERT_BLOCK, "manual-line reinsert")
    return updated


def main() -> int:
    root = Path(__file__).resolve().parent
    server_path = root / "server.py"
    store_path = root / "delivery_store.py"
    required = [server_path, store_path, root / "operations_features.py", root / "database_migrations.py", root / "database_contract.py"]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing required v135 file(s): " + ", ".join(missing))

    original = server_path.read_text(encoding="utf-8")
    original_store = store_path.read_text(encoding="utf-8")
    updated = original
    updated = replace_once(updated, IMPORT_ANCHOR, IMPORT_BLOCK, "import")
    updated = replace_once(updated, GLOBAL_ANCHOR, GLOBAL_BLOCK, "service initialization")
    updated = replace_once(updated, GET_ANCHOR, GET_BLOCK, "GET route")
    updated = replace_once(updated, POST_ANCHOR, POST_BLOCK, "POST route")
    updated_store = patch_delivery_store(original_store)

    if updated == original and updated_store == original_store and MARKER in original and STORE_MARKER in original_store:
        print("v135 operations routes and manual-order preservation are already installed.")
        return 0

    temporary = server_path.with_suffix(".py.v135.tmp")
    store_temporary = store_path.with_suffix(".py.v135.tmp")
    temporary.write_text(updated, encoding="utf-8", newline="\n")
    store_temporary.write_text(updated_store, encoding="utf-8", newline="\n")
    try:
        py_compile.compile(str(temporary), doraise=True)
        py_compile.compile(str(store_temporary), doraise=True)
    except Exception:
        temporary.unlink(missing_ok=True)
        store_temporary.unlink(missing_ok=True)
        raise

    backup_dir = root / "backups" / "v135-operations-patch"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = backup_dir / f"server-{stamp}.py"
    store_backup_path = backup_dir / f"delivery_store-{stamp}.py"
    shutil.copy2(server_path, backup_path)
    shutil.copy2(store_path, store_backup_path)

    try:
        temporary.replace(server_path)
        store_temporary.replace(store_path)
        py_compile.compile(str(server_path), doraise=True)
        py_compile.compile(str(store_path), doraise=True)
    except Exception:
        shutil.copy2(backup_path, server_path)
        shutil.copy2(store_backup_path, store_path)
        temporary.unlink(missing_ok=True)
        store_temporary.unlink(missing_ok=True)
        raise

    print(f"v135 operations routes installed. Backups: {backup_path}; {store_backup_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"v135 patch failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
