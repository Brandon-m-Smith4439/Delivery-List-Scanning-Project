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
from datetime import datetime, timedelta, timezone
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


def _logical_order_item_key(store: Any, order_no: Any, item_no: Any) -> str:
    """Use the maintained duplicate key with a legacy/test-store fallback."""
    resolver = getattr(store, "logical_order_item_key", None)
    if callable(resolver):
        return str(resolver(order_no, item_no))

    def numeric_text(value: Any) -> str:
        text = str(value or "").strip()
        try:
            return str(int(float(text.replace(",", ""))))
        except (TypeError, ValueError):
            digits = "".join(character for character in text if character.isdigit())
            return str(int(digits)) if digits else text

    return f"{numeric_text(order_no)}-{numeric_text(item_no).zfill(3)}"


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
    """Remove transient import-state labels before applying the newest source state."""
    text = str(value or "")
    text = re.sub(r"\b(?:New|Updated|Removed) Line\b", " ", text, flags=re.IGNORECASE)
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


def _change_item_payload(
    row: Any,
    change_type: str,
    line_item_id: str = "",
    previous_row: Any | None = None,
) -> dict[str, Any]:
    """Return a durable import-history snapshot with exact before/after changes."""
    payload = {
        "changeType": str(change_type or "updated").lower(),
        "lineItemId": str(line_item_id or _row_value(row, "id", "") or ""),
        "order": str(_row_value(row, "order_no", "") or ""),
        "item": str(_row_value(row, "item_no", "") or ""),
        "qty": int(_row_value(row, "qty", 0) or 0),
        "scannedQty": int(_row_value(row, "scanned_qty", 0) or 0),
        "dimensions": str(_row_value(row, "dimensions", "") or ""),
        "customer": str(_row_value(row, "customer", "") or ""),
        "job": str(_row_value(row, "job", "") or ""),
        "product": str(_row_value(row, "product", "") or ""),
        "route": str(_row_value(row, "route", "") or ""),
        "processState": str(_row_value(row, "process_state", "") or ""),
        "queueState": str(_row_value(row, "queue_state", "") or ""),
        "sourceId": str(_row_value(row, "source_id", "") or ""),
        "barcode": str(_row_value(row, "barcode", "") or ""),
    }
    if previous_row is None:
        payload["previous"] = {}
        payload["changedFields"] = []
        return payload

    previous = {
        "qty": int(_row_value(previous_row, "qty", 0) or 0),
        "dimensions": str(_row_value(previous_row, "dimensions", "") or ""),
        "customer": str(_row_value(previous_row, "customer", "") or ""),
        "job": str(_row_value(previous_row, "job", "") or ""),
        "product": str(_row_value(previous_row, "product", "") or ""),
        "route": str(_row_value(previous_row, "route", "") or ""),
        "processState": str(_row_value(previous_row, "process_state", "") or ""),
        "queueState": str(_row_value(previous_row, "queue_state", "") or ""),
        "sourceId": str(_row_value(previous_row, "source_id", "") or ""),
        "barcode": str(_row_value(previous_row, "barcode", "") or ""),
    }
    comparable_fields = (
        "qty",
        "dimensions",
        "customer",
        "job",
        "product",
        "route",
        "queueState",
        "sourceId",
        "barcode",
    )
    payload["previous"] = previous
    payload["changedFields"] = [
        field_name
        for field_name in comparable_fields
        if previous.get(field_name) != payload.get(field_name)
    ]
    return payload


def _active_manual_priority_labels(
    connection: sqlite3.Connection,
    line_item_id: str,
) -> set[str]:
    """Return active operator-managed Rush/Remake labels for one line.

    Imported A+W remake markers must be allowed to clear when the source no
    longer marks the row. Only labels created by the explicit Priority Work
    workflow are preserved across authoritative imports.
    """
    if not _table_exists(connection, "audit_events"):
        return set()
    columns = _column_names(connection, "audit_events")
    required = {"entity_type", "entity_id", "action", "id"}
    if not required.issubset(columns):
        return set()

    rows = connection.execute(
        """
        SELECT action
        FROM audit_events
        WHERE entity_type = 'line_item'
          AND entity_id = ?
          AND action IN (
              'mark_rush_sdi',
              'mark_remake_sdi',
              'clear_rush_priority',
              'clear_rush_remake_sdi'
          )
        ORDER BY id DESC
        """,
        (line_item_id,),
    ).fetchall()
    actions = [str(_row_value(row, "action", "") or "") for row in rows]

    rush_relevant = {
        "mark_rush_sdi",
        "mark_remake_sdi",
        "clear_rush_priority",
        "clear_rush_remake_sdi",
    }
    remake_relevant = {
        "mark_remake_sdi",
        "mark_rush_sdi",
        "clear_rush_remake_sdi",
    }
    latest_rush = next((action for action in actions if action in rush_relevant), "")
    latest_remake = next((action for action in actions if action in remake_relevant), "")

    active: set[str] = set()
    if latest_rush == "mark_rush_sdi":
        active.add("Rush")
    if latest_remake == "mark_remake_sdi":
        active.add("Remake")
    return active


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
        "manual_only": 0,
        "manual_source": "",
        "protect_from_aw_import": 0,
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
    allow_source_removals: bool = True,
    verified_source_removal_keys: set[str] | None = None,
) -> dict[str, Any]:
    """Reconcile one imported stage without breaking immutable scanner history.

    A+W is authoritative for source-owned rows. Missing source rows are deleted when
    nothing references them. History-linked rows are soft-deleted and their active
    rack/bay assignments are retired, which removes them from the live application
    while preserving scan, machine, rack, and bay audit records.
    """
    verified_source_removal_keys = verified_source_removal_keys or set()

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
            timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    previous_rows = connection.execute(
        """
        SELECT *
        FROM line_items
        WHERE list_id = ?
        ORDER BY COALESCE(is_deleted, 0), id
        """,
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
        was_deleted = bool(int(_row_value(row, "is_deleted", 0) or 0))
        manual_source = str(_row_value(row, "manual_source", "") or "").strip()
        manual_only = bool(int(_row_value(row, "manual_only", 0) or 0))
        protect_from_aw_import = bool(int(_row_value(row, "protect_from_aw_import", 0) or 0))
        record = {
            "row": row,
            "id": line_id,
            "source_key": source_key,
            "business_key": store.import_business_key(row),
            "order_item_key": _logical_order_item_key(store, order_no, item_no),
            "was_deleted": was_deleted,
            "manual": manual_only or bool(manual_source),
            "protected_manual": (manual_only or bool(manual_source)) and protect_from_aw_import,
        }
        previous_by_id[line_id] = record
        # Protected manual rows are not eligible as source-row matches. If A+W
        # later publishes the same logical item, the import loop below suppresses
        # the source copy so protection never creates a duplicate active row.
        if not record["protected_manual"]:
            add_pool("source", source_key, record)
            add_pool("business", record["business_key"], record)
            add_pool("order_item", record["order_item_key"], record)
        if not was_deleted:
            original_total_qty += int(_row_value(row, "qty", 0) or 0)

    protected_manual_keys = {
        str(record["order_item_key"])
        for record in previous_by_id.values()
        if record.get("protected_manual") and not record.get("was_deleted")
    }
    protected_manual_total = sum(
        int(_row_value(record["row"], "qty", 0) or 0)
        for record in previous_by_id.values()
        if record.get("protected_manual") and not record.get("was_deleted")
    )

    used_previous_ids: set[str] = set()
    incoming_source_keys: set[str] = set()
    incoming_business_keys: set[str] = set()
    incoming_order_item_keys: set[str] = set()

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
        "duplicateManualLineCount": 0,
        "duplicateManualPieceQty": 0,
        "retainedSourceLineCount": 0,
        "retainedSourcePieceQty": 0,
        "sourceRemovalSuppressed": not allow_source_removals,
        "newLineIds": [],
        "updatedLineIds": [],
        "removedLineIds": [],
        "changeItems": [],
        "originalQty": original_total_qty,
        "totalQty": (
            sum(
                int(item.get("qty") or 0)
                for item in items
                if _logical_order_item_key(store, item.get("order"), item.get("item"))
                not in protected_manual_keys
            )
            + protected_manual_total
        ),
    }

    auto_assign_settings = store.get_bay_auto_assign_settings_con(connection)
    for index, item in enumerate(items, start=1):
        cloned = store.clone_item_for_list(item, list_id, index, auto_assign_settings)
        desired_id = str(cloned["id"])
        source_key = store.import_order_item_key(
            cloned["source_id"], cloned["order_no"], cloned["item_no"]
        )
        business_key = store.import_business_key(cloned)
        order_item_key = _logical_order_item_key(store, cloned["order_no"], cloned["item_no"])
        incoming_source_keys.add(source_key)
        incoming_business_keys.add(business_key)
        incoming_order_item_keys.add(order_item_key)

        # v0.343 duplicate hardening: while a manual line is explicitly protected
        # from A+W ownership, keep that one logical stage row authoritative and
        # suppress the incoming source copy. This preserves the operator override
        # without allowing two active rows for the same Order Nr. + Item Nr.
        if order_item_key in protected_manual_keys:
            continue

        exact = previous_by_id.get(desired_id)
        if exact and exact.get("protected_manual"):
            exact = None
        if exact and exact["id"] not in used_previous_ids:
            used_previous_ids.add(exact["id"])
            previous = exact
        else:
            previous = (
                pop_pool("source", source_key)
                or pop_pool("business", business_key)
                or pop_pool("order_item", order_item_key)
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
            summary["changeItems"].append(_change_item_payload(cloned, "new"))
            continue

        row = previous["row"]
        was_retired = bool(previous.get("was_deleted"))
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
        business_changed = previous_comparable != current_comparable
        previous_state = _strip_import_labels(_row_value(row, "process_state", ""))
        next_state = _strip_import_labels(cloned.get("process_state", ""))
        # Do not preserve stale A+W remake markers. Only operator-managed
        # Priority Work labels remain when the new source no longer supplies one.
        for priority_label in sorted(_active_manual_priority_labels(connection, previous["id"])):
            if not re.search(rf"\b{priority_label}\b", next_state, flags=re.IGNORECASE):
                next_state = _append_label(next_state, priority_label)
        changed = was_retired or business_changed or previous_state != next_state
        if was_retired:
            next_state = _append_label(next_state, "New Line")
        elif changed:
            next_state = _append_label(next_state, "Updated Line")

        previous_scanned = int(_row_value(row, "scanned_qty", 0) or 0)
        next_qty = int(cloned["qty"] or 0)
        values: dict[str, Any] = {
            "source_id": cloned["source_id"],
            "barcode": cloned["barcode"],
            "order_no": cloned["order_no"],
            "item_no": cloned["item_no"],
            "qty": next_qty,
            "scanned_qty": min(previous_scanned, next_qty) if not was_retired else 0,
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
            # Once A+W supplies the same business line, source data owns it.
            # Clearing manual flags ensures a later A+W removal retires it normally.
            "manual_only": 0,
            "manual_source": "",
            "protect_from_aw_import": 0,
        }
        _update_existing_line(connection, columns, previous["id"], values)

        if was_retired:
            summary["newPieceQty"] += next_qty
            summary["addedPieceQty"] += next_qty
            summary["changedPieceQty"] += next_qty
            summary["changedLineCount"] += 1
            summary["newLineIds"].append(str(previous["id"]))
            changed_row = dict(cloned)
            changed_row.update({"id": previous["id"], "scanned_qty": 0, "process_state": next_state})
            summary["changeItems"].append(_change_item_payload(changed_row, "new", str(previous["id"])))
        elif changed:
            quantity_delta = max(next_qty - int(previous_comparable["qty"] or 0), 0)
            summary["updatedPieceQty"] += next_qty
            summary["addedPieceQty"] += quantity_delta
            summary["changedPieceQty"] += next_qty
            summary["changedLineCount"] += 1
            summary["updatedLineIds"].append(str(previous["id"]))
            changed_row = dict(cloned)
            changed_row.update(
                {
                    "id": previous["id"],
                    "scanned_qty": min(previous_scanned, next_qty),
                    "process_state": next_state,
                }
            )
            summary["changeItems"].append(
                _change_item_payload(changed_row, "updated", str(previous["id"]), previous_row=row)
            )

    # Preserve a genuinely manual-only line that A+W does not know about. When a
    # manual row duplicates an incoming A+W order/item, however, A+W owns that
    # business line and the extra manual copy must be retired. This prevents a
    # test/manual duplicate from surviving every authoritative reconciliation.
    for record in previous_by_id.values():
        if record["id"] in used_previous_ids or record.get("was_deleted"):
            continue

        if record.get("protected_manual"):
            continue

        manual_source_collision = bool(record.get("manual")) and (
            record.get("source_key") in incoming_source_keys
            or record.get("business_key") in incoming_business_keys
            or record.get("order_item_key") in incoming_order_item_keys
        )
        if record.get("manual") and not manual_source_collision:
            continue

        row = record["row"]
        previous_qty = int(_row_value(row, "qty", 0) or 0)
        verified_source_removal = record.get("order_item_key") in verified_source_removal_keys
        if not record.get("manual") and not allow_source_removals and not verified_source_removal:
            # A raw delivery-date query is not authoritative for removals. Keep the
            # current source-owned row active until schedule/run membership proves
            # that it left Crystal. Exact operator-verified exclusions remain able
            # to retire known obsolete rows such as the eight 8/3/2026 duplicates.
            summary["retainedSourceLineCount"] += 1
            summary["retainedSourcePieceQty"] += previous_qty
            summary["totalQty"] += previous_qty
            continue
        summary["removedLineCount"] += 1
        summary["removedPieceQty"] += previous_qty
        summary["changedLineCount"] += 1
        summary["changedPieceQty"] += previous_qty
        summary["removedLineIds"].append(str(record["id"]))
        summary["changeItems"].append(_change_item_payload(row, "removed", str(record["id"])))
        if manual_source_collision:
            summary["duplicateManualLineCount"] += 1
            summary["duplicateManualPieceQty"] += previous_qty

        removal_reason = (
            "Duplicate manual line replaced by authoritative A+W source"
            if manual_source_collision
            else "Removed from latest A+W delivery list"
        )

        # Active physical locations must stop treating the removed source row as
        # current work, while their historical assignment records remain intact.
        if _table_exists(connection, "rack_items"):
            rack_columns = _column_names(connection, "rack_items")
            if {"line_item_id", "status"}.issubset(rack_columns):
                assignments = ["status = 'Removed'"]
                params: list[Any] = []
                if "removed_by" in rack_columns:
                    assignments.append("removed_by = 'A+W import'")
                if "removed_at" in rack_columns:
                    assignments.append("removed_at = ?")
                    params.append(timestamp)
                if "reason" in rack_columns:
                    assignments.append("reason = ?")
                    params.append(removal_reason)
                params.append(record["id"])
                connection.execute(
                    f"UPDATE rack_items SET {', '.join(assignments)} WHERE line_item_id = ? AND status = 'Active'",
                    tuple(params),
                )

        if _table_exists(connection, "bay_assignments"):
            bay_columns = _column_names(connection, "bay_assignments")
            if {"line_item_id", "status"}.issubset(bay_columns):
                assignments = ["status = 'Cancelled'"]
                params = []
                if "cleared_by" in bay_columns:
                    assignments.append("cleared_by = 'A+W import'")
                if "cleared_at" in bay_columns:
                    assignments.append("cleared_at = ?")
                    params.append(timestamp)
                if "reason" in bay_columns:
                    assignments.append("reason = ?")
                    params.append(removal_reason)
                params.append(record["id"])
                connection.execute(
                    f"UPDATE bay_assignments SET {', '.join(assignments)} "
                    "WHERE line_item_id = ? AND status NOT IN ('Cleared', 'Cancelled')",
                    tuple(params),
                )

        if not _has_dependency(connection, record["id"]):
            connection.execute("DELETE FROM line_items WHERE id = ?", (record["id"],))
            continue

        process_state = _append_label(
            _strip_import_labels(_row_value(row, "process_state", "")),
            "Removed Line",
        )
        queue_state = _append_label(
            _row_value(row, "queue_state", ""),
            removal_reason,
        )
        _update_existing_line(
            connection,
            columns,
            record["id"],
            {
                "process_state": process_state,
                "queue_state": queue_state,
                "updated_at_utc": timestamp,
                "is_deleted": 1,
                "deleted_at_utc": timestamp,
                "deleted_by_user_id": None,
            },
        )

    active_total = connection.execute(
        "SELECT COALESCE(SUM(qty), 0) AS total_qty FROM line_items WHERE list_id = ? AND COALESCE(is_deleted, 0) = 0",
        (list_id,),
    ).fetchone()
    summary["totalQty"] = int(active_total["total_qty"] or 0) if active_total else 0
    return summary


IMPORT_PREVIEW_RETENTION_DAYS = 365


def _local_today_iso() -> str:
    return datetime.now().astimezone().date().isoformat()


def _preview_retention_cutoff_iso() -> str:
    """Keep historical update previews without growing the notice table forever."""
    return (
        datetime.now().astimezone().date() - timedelta(days=IMPORT_PREVIEW_RETENTION_DAYS)
    ).isoformat()


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


def _notice_snapshot_payload(row: Any) -> dict[str, Any]:
    """Capture the display fields needed after a source row is physically removed."""
    return {
        "lineItemId": str(_row_value(row, "id", "") or ""),
        "order": str(_row_value(row, "order_no", "") or ""),
        "item": str(_row_value(row, "item_no", "") or ""),
        "qty": int(_row_value(row, "qty", 0) or 0),
        "scannedQty": int(_row_value(row, "scanned_qty", 0) or 0),
        "dimensions": str(_row_value(row, "dimensions", "") or ""),
        "customer": str(_row_value(row, "customer", "") or ""),
        "job": str(_row_value(row, "job", "") or ""),
        "product": str(_row_value(row, "product", "") or ""),
        "route": str(_row_value(row, "route", "") or ""),
        "processState": str(_row_value(row, "process_state", "") or ""),
        "queueState": str(_row_value(row, "queue_state", "") or ""),
        "sourceId": str(_row_value(row, "source_id", "") or ""),
        "barcode": str(_row_value(row, "barcode", "") or ""),
    }


def _snapshot_delivery_date(store: Any, delivery_date: str) -> dict[str, dict[str, dict[str, Any]]]:
    """Snapshot only source-visible active rows before an import starts."""
    if not delivery_date:
        return {}
    with store.connect() as connection:
        rows = connection.execute(
            """
            SELECT li.*, dl.status AS list_status
            FROM line_items li
            JOIN delivery_lists dl ON dl.id = li.list_id
            WHERE dl.delivery_date = ?
              AND dl.status = 'active'
              AND COALESCE(li.is_deleted, 0) = 0
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
            "active": True,
            "payload": _notice_business_payload(row),
            "snapshot": _notice_snapshot_payload(row),
        }
    return snapshot


def _notice_token(
    source_hash: str,
    delivery_date: str,
    list_id: str,
    stage_summary: dict[str, Any],
    recorded_at: str,
) -> str:
    """Return one shared token for every line changed in the same stage import."""
    material = {
        "sourceHash": str(source_hash or ""),
        "deliveryDate": delivery_date,
        "listId": list_id,
        "summary": stage_summary,
        "recordedAt": recorded_at,
    }
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _record_user_line_update_notices(
    store: Any,
    delivery_date: str,
    before: dict[str, dict[str, dict[str, Any]]],
    result: dict[str, Any],
    source_hash: str,
) -> int:
    """Persist the latest new, updated, and removed rows for each changed stage.

    Historical delivery dates are retained for Delivery List Management preview.
    The pending scan-page overlay still filters to current/future dates separately.
    """
    if not delivery_date:
        return 0

    stage_summaries = {
        str(row.get("listId") or ""): dict(row)
        for row in (result.get("stageSummaries") or [])
        if isinstance(row, dict) and str(row.get("listId") or "")
    }
    reactivated = {str(value) for value in (result.get("reactivatedListIds") or []) if value}
    changed_list_ids = {str(value) for value in (result.get("changedListIds") or []) if value}

    with store.connect() as connection:
        rows = connection.execute(
            """
            SELECT li.*, dl.status AS list_status
            FROM line_items li
            JOIN delivery_lists dl ON dl.id = li.list_id
            WHERE dl.delivery_date = ?
              AND dl.status = 'active'
              AND COALESCE(li.is_deleted, 0) = 0
            ORDER BY li.list_id, li.id
            """,
            (delivery_date,),
        ).fetchall()
        current_by_list: dict[str, dict[str, Any]] = {}
        for row in rows:
            list_id = str(_row_value(row, "list_id", "") or "")
            line_id = str(_row_value(row, "id", "") or "")
            if list_id and line_id:
                current_by_list.setdefault(list_id, {})[line_id] = row

        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        inserted = 0
        list_ids = sorted(set(before) | set(current_by_list) | changed_list_ids)
        for list_id in list_ids:
            prior_rows = before.get(list_id, {})
            current_rows = current_by_list.get(list_id, {})
            changes: list[tuple[str, str, dict[str, Any]]] = []

            for line_id, row in current_rows.items():
                current_payload = _notice_business_payload(row)
                prior = prior_rows.get(line_id)
                if list_id in reactivated or prior is None or not bool(prior.get("active")):
                    change_type = "new"
                elif prior.get("payload") != current_payload:
                    change_type = "updated"
                else:
                    continue
                snapshot = _notice_snapshot_payload(row)
                if change_type == "updated" and isinstance(prior, dict):
                    previous_snapshot = prior.get("snapshot")
                    previous_payload = prior.get("payload")
                    snapshot["previous"] = dict(previous_snapshot) if isinstance(previous_snapshot, dict) else {}
                    comparison_fields = (
                        ("qty", "qty"),
                        ("dimensions", "dimensions"),
                        ("customer", "customer"),
                        ("job", "job"),
                        ("product", "product"),
                        ("route", "route"),
                        ("queueState", "queue_state"),
                    )
                    snapshot["changedFields"] = [
                        output_name
                        for output_name, payload_name in comparison_fields
                        if isinstance(previous_payload, dict)
                        and previous_payload.get(payload_name) != current_payload.get(payload_name)
                    ]
                changes.append((line_id, change_type, snapshot))

            for line_id, prior in prior_rows.items():
                if line_id in current_rows:
                    continue
                snapshot = prior.get("snapshot") if isinstance(prior, dict) else None
                if not isinstance(snapshot, dict):
                    snapshot = {}
                changes.append((line_id, "removed", dict(snapshot)))

            if not changes:
                continue

            summary = stage_summaries.get(list_id, {})
            token = _notice_token(source_hash, delivery_date, list_id, summary, created_at)
            affected_line_ids = sorted({line_id for line_id, _change_type, _snapshot in changes})
            placeholders = ",".join("?" for _ in affected_line_ids)
            old_notice_ids = [
                int(row["id"])
                for row in connection.execute(
                    f"""
                    SELECT id
                    FROM line_update_notices
                    WHERE list_id = ? AND delivery_date = ?
                      AND line_item_id IN ({placeholders})
                    """,
                    (list_id, delivery_date, *affected_line_ids),
                ).fetchall()
            ]
            if old_notice_ids:
                old_placeholders = ",".join("?" for _ in old_notice_ids)
                connection.execute(
                    f"DELETE FROM line_update_receipts WHERE notice_id IN ({old_placeholders})",
                    old_notice_ids,
                )
                connection.execute(
                    f"DELETE FROM line_update_notices WHERE id IN ({old_placeholders})",
                    old_notice_ids,
                )

            for line_id, change_type, snapshot in changes:
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO line_update_notices (
                        line_item_id, list_id, delivery_date, change_type,
                        change_token, source_hash, snapshot_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        line_id,
                        list_id,
                        delivery_date,
                        change_type,
                        token,
                        source_hash,
                        json.dumps(snapshot, sort_keys=True, separators=(",", ":"), default=str),
                        created_at,
                    ),
                )
                inserted += max(int(cursor.rowcount or 0), 0)

        retention_cutoff = _preview_retention_cutoff_iso()
        connection.execute(
            "DELETE FROM line_update_receipts WHERE notice_id IN (SELECT id FROM line_update_notices WHERE delivery_date < ?)",
            (retention_cutoff,),
        )
        connection.execute(
            "DELETE FROM line_update_notices WHERE delivery_date < ?",
            (retention_cutoff,),
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
    removed_lines = sum(1 for values in line_states.values() if "removed" in values)
    return {
        "ok": True,
        "listId": str(list_id or ""),
        "pendingNoticeCount": len(notices),
        "pendingLineCount": len(line_states),
        "newLineCount": new_lines,
        "updatedLineCount": updated_lines,
        "removedLineCount": removed_lines,
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



def _ensure_manual_protection_schema(store: Any) -> bool:
    """Add v0.236 manual-import protection columns before reconciliation.

    Automation can run with normal store initialization disabled, so this small
    SQLite guard mirrors migration 9 and keeps direct imports backward-compatible.
    """
    if getattr(store, "_dls_manual_protection_schema_checked", False):
        return bool(getattr(store, "_dls_manual_protection_schema_repaired", False))

    connection = store.connect()
    try:
        if not isinstance(connection, sqlite3.Connection):
            setattr(store, "_dls_manual_protection_schema_checked", True)
            setattr(store, "_dls_manual_protection_schema_repaired", False)
            return False

        repaired = False
        line_columns = _column_names(connection, "line_items")
        if "protect_from_aw_import" not in line_columns:
            connection.execute(
                """
                ALTER TABLE line_items
                ADD COLUMN protect_from_aw_import INTEGER NOT NULL DEFAULT 0
                    CHECK (protect_from_aw_import IN (0, 1))
                """
            )
            repaired = True

        if _table_exists(connection, "manual_delivery_entries"):
            entry_columns = _column_names(connection, "manual_delivery_entries")
            if "protect_from_aw_import" not in entry_columns:
                connection.execute(
                    """
                    ALTER TABLE manual_delivery_entries
                    ADD COLUMN protect_from_aw_import INTEGER NOT NULL DEFAULT 0
                        CHECK (protect_from_aw_import IN (0, 1))
                    """
                )
                repaired = True

        if repaired:
            connection.commit()
        setattr(store, "_dls_manual_protection_schema_checked", True)
        setattr(store, "_dls_manual_protection_schema_repaired", repaired)
        return repaired
    finally:
        connection.close()


def _ensure_line_update_notice_schema(store: Any) -> bool:
    """Repair the SQLite update-notice tables before an import can use them.

    The automation can be configured with ``InitializeStore=false`` and some
    deployed databases recorded an earlier migration without receiving the
    ``snapshot_json`` column. Import safety must not depend solely on startup
    migrations, so this narrowly scoped repair validates and rebuilds the two
    notice tables in place while preserving notice ids and user receipts.
    """
    if getattr(store, "_dls_notice_schema_checked", False):
        return bool(getattr(store, "_dls_notice_schema_repaired", False))

    connection = store.connect()
    try:
        if not isinstance(connection, sqlite3.Connection):
            setattr(store, "_dls_notice_schema_checked", True)
            setattr(store, "_dls_notice_schema_repaired", False)
            return False

        notice_exists = _table_exists(connection, "line_update_notices")
        if not notice_exists and not _table_exists(connection, "users"):
            # A brand-new database is initialized immediately after the wrapper
            # is installed. Do not pre-create partial application tables here.
            setattr(store, "_dls_notice_schema_checked", True)
            setattr(store, "_dls_notice_schema_repaired", False)
            return False
        notice_columns = _column_names(connection, "line_update_notices") if notice_exists else set()
        schema_row = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'line_update_notices'"
        ).fetchone()
        schema_sql = str(_row_value(schema_row, "sql", "") or "").lower()
        schema_is_current = (
            notice_exists
            and "snapshot_json" in notice_columns
            and "'removed'" in schema_sql
        )
        if schema_is_current:
            setattr(store, "_dls_notice_schema_checked", True)
            setattr(store, "_dls_notice_schema_repaired", False)
            return False

        foreign_keys_enabled = bool(connection.execute("PRAGMA foreign_keys").fetchone()[0])
        connection.commit()
        if foreign_keys_enabled:
            connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute("BEGIN IMMEDIATE")
        try:
            connection.execute("DROP TABLE IF EXISTS line_update_receipts_v234")
            connection.execute("DROP TABLE IF EXISTS line_update_notices_v234")
            connection.execute(
                """
                CREATE TABLE line_update_notices_v234 (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    line_item_id TEXT NOT NULL,
                    list_id TEXT NOT NULL,
                    delivery_date TEXT NOT NULL,
                    change_type TEXT NOT NULL CHECK (change_type IN ('new', 'updated', 'removed')),
                    change_token TEXT NOT NULL,
                    source_hash TEXT NOT NULL DEFAULT '',
                    snapshot_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(snapshot_json)),
                    created_at TEXT NOT NULL,
                    UNIQUE(line_item_id, change_type, change_token)
                )
                """
            )

            if notice_exists:
                required_legacy_columns = {
                    "id",
                    "line_item_id",
                    "list_id",
                    "delivery_date",
                    "change_type",
                    "change_token",
                    "created_at",
                }
                missing = sorted(required_legacy_columns.difference(notice_columns))
                if missing:
                    raise RuntimeError(
                        "line_update_notices is missing required legacy columns: "
                        + ", ".join(missing)
                    )
                source_hash_expr = "COALESCE(source_hash, '')" if "source_hash" in notice_columns else "''"
                snapshot_expr = (
                    "CASE WHEN json_valid(snapshot_json) THEN snapshot_json ELSE '{}' END"
                    if "snapshot_json" in notice_columns
                    else "'{}'"
                )
                connection.execute(
                    f"""
                    INSERT INTO line_update_notices_v234 (
                        id, line_item_id, list_id, delivery_date, change_type,
                        change_token, source_hash, snapshot_json, created_at
                    )
                    SELECT
                        id,
                        line_item_id,
                        list_id,
                        delivery_date,
                        CASE
                            WHEN lower(change_type) IN ('new', 'updated', 'removed') THEN lower(change_type)
                            ELSE 'updated'
                        END,
                        change_token,
                        {source_hash_expr},
                        {snapshot_expr},
                        created_at
                    FROM line_update_notices
                    """
                )

            connection.execute(
                """
                CREATE TABLE line_update_receipts_v234 (
                    notice_id INTEGER NOT NULL REFERENCES line_update_notices_v234(id) ON DELETE CASCADE,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    seen_at TEXT NOT NULL,
                    PRIMARY KEY (notice_id, user_id)
                )
                """
            )
            if _table_exists(connection, "line_update_receipts"):
                receipt_columns = _column_names(connection, "line_update_receipts")
                if {"notice_id", "user_id", "seen_at"}.issubset(receipt_columns):
                    connection.execute(
                        """
                        INSERT OR IGNORE INTO line_update_receipts_v234 (notice_id, user_id, seen_at)
                        SELECT receipt.notice_id, receipt.user_id, receipt.seen_at
                        FROM line_update_receipts receipt
                        JOIN line_update_notices_v234 notice ON notice.id = receipt.notice_id
                        """
                    )
                connection.execute("DROP TABLE line_update_receipts")
            if notice_exists:
                connection.execute("DROP TABLE line_update_notices")

            connection.execute("ALTER TABLE line_update_notices_v234 RENAME TO line_update_notices")
            connection.execute("ALTER TABLE line_update_receipts_v234 RENAME TO line_update_receipts")
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_line_update_notices_list_date
                ON line_update_notices(list_id, delivery_date, created_at DESC, id DESC)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_line_update_receipts_user
                ON line_update_receipts(user_id, notice_id)
                """
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            if foreign_keys_enabled:
                connection.execute("PRAGMA foreign_keys = ON")

        setattr(store, "_dls_notice_schema_checked", True)
        setattr(store, "_dls_notice_schema_repaired", True)
        return True
    finally:
        connection.close()

def install_safe_delivery_import(store: Any) -> bool:
    """Install the SQLite-safe import wrapper on one configured store instance.

    Returns ``True`` when the wrapper is active. Non-SQLite stores are left untouched
    so the future Azure SQL adapter continues to use its native implementation.
    """

    # Validate additive schemas even when automation initialization is disabled
    # in the installed configuration.
    _ensure_manual_protection_schema(store)
    _ensure_line_update_notice_schema(store)

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
        allow_source_removals = bool(
            getattr(self, "_dls_allow_source_removals", True)
        )
        verified_source_removal_keys = set(
            getattr(self, "_dls_verified_source_removal_keys", set()) or set()
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
            allow_source_removals,
            verified_source_removal_keys,
        )

    def import_with_user_notices(self: Any, data: dict[str, Any]) -> dict[str, Any]:
        raw_payload = data.get("payload") if isinstance(data, dict) else None
        if not isinstance(raw_payload, dict):
            raw_payload = data if isinstance(data, dict) else {}
        delivery_date = str(raw_payload.get("deliveryDate") or "").strip()
        before = _snapshot_delivery_date(self, delivery_date) if delivery_date else {}
        allow_source_removals = bool(data.get("allowSourceRemovals", True)) if isinstance(data, dict) else True
        verified_entries = data.get("verifiedExcludedOrderItems") if isinstance(data, dict) else []
        verified_source_removal_keys = {
            f"{str(entry.get('orderNumber') or '').strip()}-{str(entry.get('itemNumber') or '').strip().zfill(3)}"
            for entry in (verified_entries or [])
            if isinstance(entry, dict)
            and str(entry.get("orderNumber") or "").strip()
            and str(entry.get("itemNumber") or "").strip()
            and (
                not delivery_date
                or not str(entry.get("deliveryDate") or "").strip()
                or str(entry.get("deliveryDate") or "").strip() == delivery_date
            )
        }
        marker = object()
        previous_allow = getattr(self, "_dls_allow_source_removals", marker)
        previous_verified = getattr(self, "_dls_verified_source_removal_keys", marker)
        self._dls_allow_source_removals = allow_source_removals
        self._dls_verified_source_removal_keys = verified_source_removal_keys
        try:
            result = original_import(data)
        finally:
            if previous_allow is marker:
                try:
                    delattr(self, "_dls_allow_source_removals")
                except AttributeError:
                    pass
            else:
                self._dls_allow_source_removals = previous_allow
            if previous_verified is marker:
                try:
                    delattr(self, "_dls_verified_source_removal_keys")
                except AttributeError:
                    pass
            else:
                self._dls_verified_source_removal_keys = previous_verified
        if delivery_date:
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
