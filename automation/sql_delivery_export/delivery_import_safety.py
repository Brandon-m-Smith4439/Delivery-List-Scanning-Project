# File: automation/sql_delivery_export/delivery_import_safety.py
"""Non-destructive delivery-list import reconciliation for SQLite scanner databases.

The scanner's immutable event triggers correctly prevent UPDATE/DELETE operations on
history tables.  SQLite's ``ON DELETE SET NULL`` action for ``scan_events`` becomes an
UPDATE, so deleting and recreating line-item rows fails as soon as a list has scan
history.  This module installs an isolated store-instance wrapper that updates matched
line items in place, inserts new lines, and safely retires removed history-linked rows.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import types
from datetime import datetime, timezone
from typing import Any


_CORE_LINE_COLUMNS = (
    "source_id",
    "barcode",
    "order_no",
    "item_no",
    "qty",
    "scanned_qty",
    "dimensions",
    "customer",
    "route",
    "source_route",
    "job",
    "product",
    "process_state",
    "queue_state",
    "suggested_bay",
    "priority_delivery_date",
    "priority_direct_to_truck",
)


def _row_value(row: Any, name: str, default: Any = "") -> Any:
    try:
        return row[name] if name in row.keys() else default
    except (AttributeError, KeyError, TypeError):
        return default


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    return bool(row)


def _column_names(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row["name"]) for row in connection.execute(f"PRAGMA table_info([{table}])").fetchall()}


def _append_label(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if re.search(rf"\b{re.escape(label)}\b", text, flags=re.IGNORECASE):
        return text
    return " ".join(part for part in (text, label) if part).strip()


def _strip_import_labels(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"\b(?:New|Updated) Line\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _business_payload(row: Any) -> dict[str, Any]:
    return {
        "qty": int(_row_value(row, "qty", 0) or 0),
        "dimensions": str(_row_value(row, "dimensions", "") or ""),
        "customer": str(_row_value(row, "customer", "") or ""),
        "route": str(_row_value(row, "route", "") or ""),
        "source_route": str(_row_value(row, "source_route", "") or ""),
        "job": str(_row_value(row, "job", "") or ""),
        "product": str(_row_value(row, "product", "") or ""),
        "queue_state": str(_row_value(row, "queue_state", "") or ""),
    }


def _has_dependency(connection: sqlite3.Connection, line_item_id: str) -> bool:
    checks: tuple[tuple[str, str], ...] = (
        ("scan_events", "line_item_id"),
        ("machine_events", "line_item_id"),
        ("rack_items", "line_item_id"),
        ("bay_assignments", "line_item_id"),
    )
    for table, column in checks:
        if not _table_exists(connection, table) or column not in _column_names(connection, table):
            continue
        row = connection.execute(
            f"SELECT 1 FROM [{table}] WHERE [{column}] = ? LIMIT 1",
            (line_item_id,),
        ).fetchone()
        if row:
            return True
    return False


def _insert_cloned_line(
    connection: sqlite3.Connection,
    columns: set[str],
    cloned: dict[str, Any],
) -> None:
    values: dict[str, Any] = {
        "id": cloned["id"],
        "list_id": cloned["list_id"],
        "source_id": cloned["source_id"],
        "barcode": cloned["barcode"],
        "order_no": cloned["order_no"],
        "item_no": cloned["item_no"],
        "qty": int(cloned["qty"] or 0),
        "scanned_qty": 0,
        "dimensions": cloned["dimensions"],
        "customer": cloned["customer"],
        "route": cloned["route"],
        "source_route": cloned["source_route"],
        "job": cloned["job"],
        "product": cloned["product"],
        "process_state": cloned["process_state"],
        "queue_state": cloned["queue_state"],
        "suggested_bay": cloned["suggested_bay"],
        "priority_delivery_date": "",
        "priority_direct_to_truck": 0,
        "created_at_utc": cloned.get("updated_at_utc", ""),
        "updated_at_utc": cloned.get("updated_at_utc", ""),
        "is_deleted": 0,
        "deleted_at_utc": "",
        "deleted_by_user_id": None,
    }
    selected = [name for name in values if name in columns]
    placeholders = ", ".join("?" for _ in selected)
    connection.execute(
        f"INSERT INTO line_items ({', '.join(f'[{name}]' for name in selected)}) VALUES ({placeholders})",
        tuple(values[name] for name in selected),
    )


def _update_existing_line(
    connection: sqlite3.Connection,
    columns: set[str],
    line_item_id: str,
    values: dict[str, Any],
) -> None:
    selected = [name for name in values if name in columns]
    assignments = ", ".join(f"[{name}] = ?" for name in selected)
    connection.execute(
        f"UPDATE line_items SET {assignments} WHERE id = ?",
        (*[values[name] for name in selected], line_item_id),
    )


def _safe_reconcile_delivery_list(
    store: Any,
    original_upsert: Any,
    connection: sqlite3.Connection,
    list_id: str,
    label: str,
    delivery_date: str,
    stage: str,
    scanner: str,
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    existing_list = connection.execute(
        "SELECT id, revision FROM delivery_lists WHERE id = ?",
        (list_id,),
    ).fetchone()
    if not existing_list:
        return original_upsert(
            connection,
            list_id,
            label,
            delivery_date,
            stage,
            scanner,
            items,
            True,
        )

    # Reuse the maintained metadata upsert without deleting line items, then keep the
    # historical revision behavior of a full replacement import.
    original_upsert(
        connection,
        list_id,
        label,
        delivery_date,
        stage,
        scanner,
        items,
        False,
    )
    connection.execute(
        "UPDATE delivery_lists SET revision = revision + 1 WHERE id = ?",
        (list_id,),
    )

    columns = _column_names(connection, "line_items")
    timestamp = str(getattr(store, "now_iso", lambda: "")() or "") if hasattr(store, "now_iso") else ""
    if not timestamp:
        try:
            from backend.store import now_iso  # type: ignore

            timestamp = now_iso()
        except Exception:
            timestamp = ""

    previous_rows = connection.execute(
        "SELECT * FROM line_items WHERE list_id = ? ORDER BY id",
        (list_id,),
    ).fetchall()
    previous_by_id: dict[str, dict[str, Any]] = {}
    pools: dict[str, dict[str, list[dict[str, Any]]]] = {
        "source": {},
        "business": {},
        "order_item": {},
    }

    def add_pool(pool: str, key: str, record: dict[str, Any]) -> None:
        if key:
            pools[pool].setdefault(key, []).append(record)

    original_total_qty = 0
    for row in previous_rows:
        line_id = str(row["id"])
        source_id = str(_row_value(row, "source_id", "") or "")
        order_no = str(_row_value(row, "order_no", "") or "")
        item_no = str(_row_value(row, "item_no", "") or "").zfill(3)
        source_key = store.import_order_item_key(source_id, order_no, item_no)
        record = {
            "row": row,
            "id": line_id,
            "source_key": source_key,
            "business_key": store.import_business_key(row),
            "order_item_key": f"{order_no}-{item_no}",
        }
        previous_by_id[line_id] = record
        add_pool("source", source_key, record)
        add_pool("business", record["business_key"], record)
        add_pool("order_item", record["order_item_key"], record)
        original_total_qty += int(_row_value(row, "qty", 0) or 0)

    used_previous_ids: set[str] = set()

    def pop_pool(pool: str, key: str) -> dict[str, Any] | None:
        values = pools[pool].get(key) or []
        while values:
            candidate = values.pop(0)
            if candidate["id"] not in used_previous_ids:
                used_previous_ids.add(candidate["id"])
                return candidate
        return None

    summary: dict[str, Any] = {
        "listId": list_id,
        "stage": stage,
        "scanner": scanner,
        "created": False,
        "safeInPlaceUpdate": True,
        "newPieceQty": 0,
        "updatedPieceQty": 0,
        "addedPieceQty": 0,
        "changedPieceQty": 0,
        "changedLineCount": 0,
        "removedLineCount": 0,
        "removedPieceQty": 0,
        "newLineIds": [],
        "updatedLineIds": [],
        "removedLineIds": [],
        "originalQty": original_total_qty,
        "totalQty": sum(int(item.get("qty") or 0) for item in items),
    }

    auto_assign_settings = store.get_bay_auto_assign_settings_con(connection)
    for index, item in enumerate(items, start=1):
        cloned = store.clone_item_for_list(item, list_id, index, auto_assign_settings)
        desired_id = str(cloned["id"])
        source_key = store.import_order_item_key(
            cloned["source_id"], cloned["order_no"], cloned["item_no"]
        )
        exact = previous_by_id.get(desired_id)
        if exact and exact["id"] not in used_previous_ids:
            used_previous_ids.add(exact["id"])
            previous = exact
        else:
            previous = (
                pop_pool("source", source_key)
                or pop_pool("business", store.import_business_key(cloned))
                or pop_pool(
                    "order_item",
                    f"{cloned['order_no']}-{str(cloned['item_no']).zfill(3)}",
                )
            )

        if previous is None:
            cloned["id"] = store.available_line_item_id(
                connection,
                desired_id,
                list_id,
                str(cloned["source_id"]),
                index,
            )
            cloned["list_id"] = list_id
            cloned["process_state"] = _append_label(cloned.get("process_state"), "New Line")
            cloned["updated_at_utc"] = timestamp
            _insert_cloned_line(connection, columns, cloned)
            quantity = int(cloned["qty"] or 0)
            summary["newPieceQty"] += quantity
            summary["addedPieceQty"] += quantity
            summary["changedPieceQty"] += quantity
            summary["changedLineCount"] += 1
            summary["newLineIds"].append(str(cloned["id"]))
            continue

        row = previous["row"]
        previous_comparable = _business_payload(row)
        current_comparable = {
            "qty": int(cloned["qty"] or 0),
            "dimensions": str(cloned["dimensions"] or ""),
            "customer": str(cloned["customer"] or ""),
            "route": str(cloned["route"] or ""),
            "source_route": str(cloned["source_route"] or ""),
            "job": str(cloned["job"] or ""),
            "product": str(cloned["product"] or ""),
            "queue_state": str(cloned["queue_state"] or ""),
        }
        changed = previous_comparable != current_comparable
        previous_state = str(_row_value(row, "process_state", "") or "")
        next_state = _strip_import_labels(cloned.get("process_state", ""))
        for priority_label in ("Rush", "Remake"):
            if re.search(rf"\b{priority_label}\b", previous_state, flags=re.IGNORECASE) and not re.search(
                rf"\b{priority_label}\b", next_state, flags=re.IGNORECASE
            ):
                next_state = _append_label(next_state, priority_label)
        if changed:
            next_state = _append_label(next_state, "Updated Line")

        previous_scanned = int(_row_value(row, "scanned_qty", 0) or 0)
        next_qty = int(cloned["qty"] or 0)
        values: dict[str, Any] = {
            "source_id": cloned["source_id"],
            "barcode": cloned["barcode"],
            "order_no": cloned["order_no"],
            "item_no": cloned["item_no"],
            "qty": next_qty,
            "scanned_qty": min(previous_scanned, next_qty),
            "dimensions": cloned["dimensions"],
            "customer": cloned["customer"],
            "route": cloned["route"],
            "source_route": cloned["source_route"],
            "job": cloned["job"],
            "product": cloned["product"],
            "process_state": next_state,
            "queue_state": cloned["queue_state"],
            "suggested_bay": cloned["suggested_bay"],
            "priority_delivery_date": str(_row_value(row, "priority_delivery_date", "") or ""),
            "priority_direct_to_truck": int(_row_value(row, "priority_direct_to_truck", 0) or 0),
            "updated_at_utc": timestamp,
            "is_deleted": 0,
            "deleted_at_utc": "",
            "deleted_by_user_id": None,
        }
        _update_existing_line(connection, columns, previous["id"], values)

        if changed:
            quantity_delta = max(next_qty - int(previous_comparable["qty"] or 0), 0)
            summary["updatedPieceQty"] += next_qty
            summary["addedPieceQty"] += quantity_delta
            summary["changedPieceQty"] += next_qty
            summary["changedLineCount"] += 1
            summary["updatedLineIds"].append(str(previous["id"]))

    # Source rows removed by A+W can be deleted only when nothing references them.
    # History-linked rows remain complete and visibly marked instead of breaking the
    # immutable event stream or becoming scannable ghost rows.
    for record in previous_by_id.values():
        if record["id"] in used_previous_ids:
            continue
        row = record["row"]
        previous_qty = int(_row_value(row, "qty", 0) or 0)
        previous_scanned = int(_row_value(row, "scanned_qty", 0) or 0)
        summary["removedLineCount"] += 1
        summary["removedPieceQty"] += previous_qty
        summary["changedLineCount"] += 1
        summary["changedPieceQty"] += previous_qty
        summary["removedLineIds"].append(str(record["id"]))

        if not _has_dependency(connection, record["id"]):
            connection.execute("DELETE FROM line_items WHERE id = ?", (record["id"],))
            continue

        retired_qty = max(previous_scanned, 0)
        process_state = _append_label(
            _strip_import_labels(_row_value(row, "process_state", "")),
            "Removed Line",
        )
        queue_state = _append_label(
            _row_value(row, "queue_state", ""),
            "Removed from latest import",
        )
        _update_existing_line(
            connection,
            columns,
            record["id"],
            {
                "qty": retired_qty,
                "scanned_qty": retired_qty,
                "process_state": process_state,
                "queue_state": queue_state,
                "updated_at_utc": timestamp,
            },
        )

    return summary


def _local_today_iso() -> str:
    return datetime.now().astimezone().date().isoformat()


def _notice_business_payload(row: Any) -> dict[str, Any]:
    return {
        "qty": int(_row_value(row, "qty", 0) or 0),
        "dimensions": str(_row_value(row, "dimensions", "") or ""),
        "customer": str(_row_value(row, "customer", "") or ""),
        "route": str(_row_value(row, "route", "") or ""),
        "source_route": str(_row_value(row, "source_route", "") or ""),
        "job": str(_row_value(row, "job", "") or ""),
        "product": str(_row_value(row, "product", "") or ""),
        "queue_state": str(_row_value(row, "queue_state", "") or ""),
    }


def _snapshot_delivery_date(store: Any, delivery_date: str) -> dict[str, dict[str, dict[str, Any]]]:
    if not delivery_date:
        return {}
    with store.connect() as connection:
        rows = connection.execute(
            """
            SELECT li.*, dl.status AS list_status
            FROM line_items li
            JOIN delivery_lists dl ON dl.id = li.list_id
            WHERE dl.delivery_date = ?
            """,
            (delivery_date,),
        ).fetchall()
    snapshot: dict[str, dict[str, dict[str, Any]]] = {}
    for row in rows:
        list_id = str(_row_value(row, "list_id", "") or "")
        line_id = str(_row_value(row, "id", "") or "")
        if not list_id or not line_id:
            continue
        snapshot.setdefault(list_id, {})[line_id] = {
            "active": str(_row_value(row, "list_status", "") or "").lower() == "active",
            "payload": _notice_business_payload(row),
        }
    return snapshot


def _notice_token(
    source_hash: str,
    list_id: str,
    line_item_id: str,
    change_type: str,
    payload: dict[str, Any],
) -> str:
    material = {
        "sourceHash": str(source_hash or ""),
        "listId": list_id,
        "lineItemId": line_item_id,
        "changeType": change_type,
        "payload": payload,
    }
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _record_user_line_update_notices(
    store: Any,
    delivery_date: str,
    before: dict[str, dict[str, dict[str, Any]]],
    result: dict[str, Any],
    source_hash: str,
) -> int:
    if not delivery_date or delivery_date < _local_today_iso():
        return 0
    reactivated = {str(value) for value in (result.get("reactivatedListIds") or []) if value}
    with store.connect() as connection:
        rows = connection.execute(
            """
            SELECT li.*, dl.status AS list_status
            FROM line_items li
            JOIN delivery_lists dl ON dl.id = li.list_id
            WHERE dl.delivery_date = ? AND dl.status = 'active'
            ORDER BY li.list_id, li.id
            """,
            (delivery_date,),
        ).fetchall()
        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        inserted = 0
        active_line_ids: set[str] = set()
        retired_line_ids: set[str] = set()
        for row in rows:
            list_id = str(_row_value(row, "list_id", "") or "")
            line_id = str(_row_value(row, "id", "") or "")
            if not list_id or not line_id:
                continue
            process_state = str(_row_value(row, "process_state", "") or "")
            queue_state = str(_row_value(row, "queue_state", "") or "")
            retired = bool(
                re.search(r"\bRemoved Line\b", process_state, flags=re.IGNORECASE)
                or re.search(r"\bRemoved from latest import\b", queue_state, flags=re.IGNORECASE)
            )
            if retired:
                retired_line_ids.add(line_id)
                continue
            active_line_ids.add(line_id)
            current = _notice_business_payload(row)
            prior = before.get(list_id, {}).get(line_id)
            if list_id in reactivated or prior is None or not bool(prior.get("active")):
                change_type = "new"
            elif prior.get("payload") != current:
                change_type = "updated"
            else:
                continue
            token = _notice_token(source_hash, list_id, line_id, change_type, current)
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO line_update_notices (
                    line_item_id, list_id, delivery_date, change_type,
                    change_token, source_hash, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (line_id, list_id, delivery_date, change_type, token, source_hash, created_at),
            )
            inserted += max(int(cursor.rowcount or 0), 0)

        # Removed or retired rows are intentionally excluded from the operator's
        # New/Updated review queue. Delete any older notice for a line that no
        # longer belongs to an active current/future delivery-list definition.
        stale_line_ids = set(retired_line_ids)
        existing_notice_rows = connection.execute(
            "SELECT DISTINCT line_item_id FROM line_update_notices WHERE delivery_date = ?",
            (delivery_date,),
        ).fetchall()
        stale_line_ids.update(
            str(row["line_item_id"])
            for row in existing_notice_rows
            if str(row["line_item_id"] or "") not in active_line_ids
        )
        if stale_line_ids:
            placeholders = ",".join("?" for _ in stale_line_ids)
            notice_ids = [
                int(row["id"])
                for row in connection.execute(
                    f"SELECT id FROM line_update_notices WHERE delivery_date = ? AND line_item_id IN ({placeholders})",
                    (delivery_date, *sorted(stale_line_ids)),
                ).fetchall()
            ]
            if notice_ids:
                notice_placeholders = ",".join("?" for _ in notice_ids)
                connection.execute(
                    f"DELETE FROM line_update_receipts WHERE notice_id IN ({notice_placeholders})",
                    notice_ids,
                )
                connection.execute(
                    f"DELETE FROM line_update_notices WHERE id IN ({notice_placeholders})",
                    notice_ids,
                )

        connection.execute(
            "DELETE FROM line_update_receipts WHERE notice_id IN (SELECT id FROM line_update_notices WHERE delivery_date < ?)",
            (_local_today_iso(),),
        )
        connection.execute(
            "DELETE FROM line_update_notices WHERE delivery_date < ?",
            (_local_today_iso(),),
        )
        connection.commit()
    return inserted


def _user_row(connection: sqlite3.Connection, username: str) -> Any:
    return connection.execute(
        "SELECT id FROM users WHERE lower(username) = lower(?) AND active = 1",
        (str(username or "").strip(),),
    ).fetchone()


def _pending_user_line_updates(store: Any, username: str, list_id: str = "") -> list[dict[str, Any]]:
    clean_username = str(username or "").strip()
    clean_list_id = str(list_id or "").strip()
    if not clean_username:
        return []
    with store.connect() as connection:
        user = _user_row(connection, clean_username)
        if not user:
            return []
        parameters: list[Any] = [int(user["id"]), _local_today_iso()]
        list_clause = ""
        if clean_list_id:
            list_clause = " AND n.list_id = ?"
            parameters.append(clean_list_id)
        rows = connection.execute(
            f"""
            SELECT n.*
            FROM line_update_notices n
            LEFT JOIN line_update_receipts r
              ON r.notice_id = n.id AND r.user_id = ?
            WHERE r.notice_id IS NULL
              AND n.delivery_date >= ?
              {list_clause}
            ORDER BY n.created_at DESC, n.id DESC
            """,
            tuple(parameters),
        ).fetchall()
    return [
        {
            "id": int(row["id"]),
            "lineItemId": str(row["line_item_id"]),
            "listId": str(row["list_id"]),
            "deliveryDate": str(row["delivery_date"]),
            "changeType": str(row["change_type"]),
            "createdAt": str(row["created_at"]),
        }
        for row in rows
    ]


def _get_user_line_update_summary(store: Any, username: str, list_id: str = "") -> dict[str, Any]:
    notices = _pending_user_line_updates(store, username, list_id)
    line_states: dict[str, set[str]] = {}
    for notice in notices:
        line_states.setdefault(notice["lineItemId"], set()).add(notice["changeType"])
    new_lines = sum(1 for values in line_states.values() if "new" in values)
    updated_lines = sum(1 for values in line_states.values() if "updated" in values)
    return {
        "ok": True,
        "listId": str(list_id or ""),
        "pendingNoticeCount": len(notices),
        "pendingLineCount": len(line_states),
        "newLineCount": new_lines,
        "updatedLineCount": updated_lines,
        "notices": notices,
    }


def _acknowledge_user_line_updates(
    store: Any,
    username: str,
    list_id: str,
    notice_ids: list[int] | None = None,
) -> dict[str, Any]:
    clean_username = str(username or "").strip()
    clean_list_id = str(list_id or "").strip()
    if not clean_username or not clean_list_id:
        raise ValueError("user and listId are required")
    selected_ids = sorted({int(value) for value in (notice_ids or []) if int(value or 0) > 0})
    with store.connect() as connection:
        user = _user_row(connection, clean_username)
        if not user:
            raise ValueError("User not found")
        parameters: list[Any] = [clean_list_id, _local_today_iso()]
        id_clause = ""
        if selected_ids:
            placeholders = ",".join("?" for _ in selected_ids)
            id_clause = f" AND id IN ({placeholders})"
            parameters.extend(selected_ids)
        rows = connection.execute(
            f"""
            SELECT id FROM line_update_notices
            WHERE list_id = ? AND delivery_date >= ? {id_clause}
            """,
            tuple(parameters),
        ).fetchall()
        seen_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for row in rows:
            connection.execute(
                """
                INSERT OR IGNORE INTO line_update_receipts (notice_id, user_id, seen_at)
                VALUES (?, ?, ?)
                """,
                (int(row["id"]), int(user["id"]), seen_at),
            )
        connection.commit()
    result = _get_user_line_update_summary(store, clean_username, clean_list_id)
    result["acknowledgedCount"] = len(rows)
    return result


def _apply_user_update_overlay(store: Any, payload: dict[str, Any], user: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or not user:
        return payload
    username = str(user.get("username") or user.get("displayName") or "").strip() if isinstance(user, dict) else str(user or "").strip()
    if not username:
        return payload
    list_id = str(payload.get("id") or payload.get("listId") or payload.get("list", {}).get("id") or "").strip()
    delivery_date = str(payload.get("deliveryDate") or payload.get("list", {}).get("deliveryDate") or "").strip()
    if not list_id:
        return payload
    if not delivery_date:
        with store.connect() as connection:
            row = connection.execute("SELECT delivery_date FROM delivery_lists WHERE id = ?", (list_id,)).fetchone()
            delivery_date = str(row["delivery_date"] or "") if row else ""
    if not delivery_date or delivery_date < _local_today_iso():
        return payload

    notices = _pending_user_line_updates(store, username, list_id)
    states: dict[str, set[str]] = {}
    notice_ids: dict[str, list[int]] = {}
    for notice in notices:
        states.setdefault(notice["lineItemId"], set()).add(notice["changeType"])
        notice_ids.setdefault(notice["lineItemId"], []).append(int(notice["id"]))

    items = payload.get("items")
    if not isinstance(items, list):
        return payload
    for item in items:
        if not isinstance(item, dict):
            continue
        line_id = str(item.get("id") or item.get("lineItemId") or "")
        base_state = _strip_import_labels(item.get("processState", item.get("process_state", "")))
        pending = states.get(line_id, set())
        next_state = base_state
        if "new" in pending:
            next_state = _append_label(next_state, "New Line")
        if "updated" in pending:
            next_state = _append_label(next_state, "Updated Line")
        item["processState"] = next_state
        if "process_state" in item:
            item["process_state"] = next_state
        item["userUpdateState"] = "new_updated" if pending == {"new", "updated"} else (next(iter(pending)) if pending else "")
        item["userUpdateNoticeIds"] = notice_ids.get(line_id, [])
        item["hasUnseenUpdate"] = bool(pending)
    payload["userUpdateSummary"] = _get_user_line_update_summary(store, username, list_id)
    return payload


def _apply_list_update_counts(store: Any, lists: list[dict[str, Any]], user: Any) -> list[dict[str, Any]]:
    if not user or not isinstance(lists, list):
        return lists
    username = str(user.get("username") or user.get("displayName") or "").strip() if isinstance(user, dict) else str(user or "").strip()
    if not username:
        return lists
    notices = _pending_user_line_updates(store, username)
    by_list: dict[str, set[str]] = {}
    for notice in notices:
        by_list.setdefault(notice["listId"], set()).add(notice["lineItemId"])
    for item in lists:
        if not isinstance(item, dict):
            continue
        count = len(by_list.get(str(item.get("id") or ""), set()))
        item["unseenUpdateCount"] = count
        item["hasUnseenUpdates"] = count > 0
    return lists


def _pending_notifications_without_automation(store: Any, original: Any, username: str, limit: int = 5) -> list[dict[str, Any]]:
    requested = max(1, min(int(limit or 5), 20))
    clean_username = str(username or "").strip()
    if not clean_username:
        return []

    # Query the pending queue directly so a long run of unread automation notices
    # cannot crowd a real Rush/priority notice out of the original 20-row limit.
    # Automation notices remain in notification history and the bell inbox; they
    # are excluded only from the full-screen priority/Rush delivery mechanism.
    try:
        with store.connect() as connection:
            user = _user_row(connection, clean_username)
            if not user:
                return []
            rows = connection.execute(
                """
                SELECT n.*
                FROM app_notifications n
                LEFT JOIN app_notification_receipts r
                  ON r.notification_id = n.id AND r.user_id = ?
                WHERE n.active = 1
                  AND r.notification_id IS NULL
                  AND (COALESCE(n.expires_at, '') = '' OR n.expires_at > ?)
                ORDER BY n.id ASC
                LIMIT 250
                """,
                (int(user["id"]), datetime.now(timezone.utc).isoformat(timespec="seconds")),
            ).fetchall()
    except Exception:
        candidates = original(clean_username, 20)
    else:
        candidates = []
        for row in rows:
            try:
                details = json.loads(str(_row_value(row, "payload_json", "") or "{}"))
            except (TypeError, ValueError, json.JSONDecodeError):
                details = {}
            candidates.append(
                {
                    "id": int(_row_value(row, "id", 0) or 0),
                    "type": str(_row_value(row, "notification_type", "notice") or "notice"),
                    "title": str(_row_value(row, "title", "Notification") or "Notification"),
                    "message": str(_row_value(row, "message", "") or ""),
                    "details": details,
                    "createdBy": str(_row_value(row, "created_by", "system") or "system"),
                    "createdAt": str(_row_value(row, "created_at", "") or ""),
                    "expiresAt": str(_row_value(row, "expires_at", "") or ""),
                }
            )

    visible = []
    for item in candidates:
        source = str((item.get("details") or {}).get("source") or "").strip().lower()
        if source == "sql-delivery-automation":
            continue
        visible.append(item)
        if len(visible) >= requested:
            break
    return visible


def install_safe_delivery_import(store: Any) -> bool:
    """Install the SQLite-safe import wrapper on one configured store instance.

    Returns ``True`` when the wrapper is active. Non-SQLite stores are left untouched
    so the future Azure SQL adapter continues to use its native implementation.
    """

    if getattr(store, "_dls_safe_delivery_import_installed", False):
        return True

    probe = store.connect()
    try:
        if not isinstance(probe, sqlite3.Connection):
            return False
    finally:
        probe.close()

    original_upsert = store.upsert_delivery_list
    original_import = getattr(store, "import_delivery_list", None)
    original_get_delivery_list = getattr(store, "get_delivery_list", None)
    original_get_delivery_lists = getattr(store, "get_delivery_lists", None)
    original_pending_notifications = getattr(store, "get_pending_notifications", None)

    def safe_upsert(
        self: Any,
        connection: sqlite3.Connection,
        list_id: str,
        label: str,
        delivery_date: str,
        stage: str,
        scanner: str,
        items: list[dict[str, Any]],
        replace_items: bool,
    ) -> dict[str, Any]:
        if not replace_items:
            return original_upsert(
                connection,
                list_id,
                label,
                delivery_date,
                stage,
                scanner,
                items,
                replace_items,
            )
        return _safe_reconcile_delivery_list(
            self,
            original_upsert,
            connection,
            list_id,
            label,
            delivery_date,
            stage,
            scanner,
            items,
        )

    def import_with_user_notices(self: Any, data: dict[str, Any]) -> dict[str, Any]:
        raw_payload = data.get("payload") if isinstance(data, dict) else None
        if not isinstance(raw_payload, dict):
            raw_payload = data if isinstance(data, dict) else {}
        delivery_date = str(raw_payload.get("deliveryDate") or "").strip()
        before = _snapshot_delivery_date(self, delivery_date) if delivery_date >= _local_today_iso() else {}
        result = original_import(data)
        if delivery_date >= _local_today_iso():
            inserted = _record_user_line_update_notices(
                self,
                delivery_date,
                before,
                result if isinstance(result, dict) else {},
                str(data.get("sourceHash") or "") if isinstance(data, dict) else "",
            )
            if isinstance(result, dict):
                result["userLineUpdateNoticeCount"] = inserted
        return result

    def get_delivery_list_with_user_updates(
        self: Any,
        list_id: str,
        last_scan: dict[str, Any] | None = None,
        user: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = original_get_delivery_list(list_id, last_scan, user)
        return _apply_user_update_overlay(self, payload, user)

    def get_delivery_lists_with_user_updates(
        self: Any,
        user: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        return _apply_list_update_counts(self, original_get_delivery_lists(user), user)

    def get_user_line_update_summary(
        self: Any,
        username: str,
        list_id: str = "",
    ) -> dict[str, Any]:
        return _get_user_line_update_summary(self, username, list_id)

    def acknowledge_user_line_updates(
        self: Any,
        username: str,
        list_id: str,
        notice_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        return _acknowledge_user_line_updates(self, username, list_id, notice_ids)

    def pending_notifications_without_automation(
        self: Any,
        username: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        return _pending_notifications_without_automation(
            self,
            original_pending_notifications,
            username,
            limit,
        )

    store.upsert_delivery_list = types.MethodType(safe_upsert, store)
    if callable(original_import):
        store.import_delivery_list = types.MethodType(import_with_user_notices, store)
    if callable(original_get_delivery_list):
        store.get_delivery_list = types.MethodType(get_delivery_list_with_user_updates, store)
    if callable(original_get_delivery_lists):
        store.get_delivery_lists = types.MethodType(get_delivery_lists_with_user_updates, store)
    store.get_user_line_update_summary = types.MethodType(get_user_line_update_summary, store)
    store.acknowledge_user_line_updates = types.MethodType(acknowledge_user_line_updates, store)
    if callable(original_pending_notifications):
        store.get_pending_notifications = types.MethodType(pending_notifications_without_automation, store)
    store._dls_safe_delivery_import_installed = True
    return True
