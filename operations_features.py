"""Operational extensions for Delivery List Scanner v135.

This module keeps newer workflows isolated from the large legacy store class while
still using the store's maintained connection, item insertion, audit, and business
rules.  The HTTP server delegates reject tracking, manual order creation, per-user
line flags, and packing-list history here.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import html
import json
from pathlib import Path
import re
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean_text(value: Any, maximum: int = 500) -> str:
    return " ".join(str(value or "").split())[:maximum]


def clean_order(value: Any) -> str:
    text = re.sub(r"\D", "", str(value or ""))
    if not text:
        raise ValueError("Order number is required")
    return text[:32]


def clean_item(value: Any) -> str:
    text = re.sub(r"\D", "", str(value or ""))
    if not text:
        raise ValueError("Item number is required")
    return text.zfill(3)[-6:]


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def row_value(row: Any, key: str, default: Any = "") -> Any:
    if row is None:
        return default
    if isinstance(row, dict):
        return row.get(key, default)
    try:
        return row[key] if key in row.keys() else default
    except (AttributeError, KeyError, TypeError, IndexError):
        return default


class OperationsFeatureService:
    """Coordinate v135 workflows against the scanner's maintained store."""

    def __init__(self, store: Any, config: Any, project_root: Path) -> None:
        self.store = store
        self.config = config
        self.project_root = Path(project_root).resolve()

    def _require_sqlite(self) -> None:
        database_type = str(getattr(self.store, "database_type", "sqlite") or "sqlite").lower()
        if database_type != "sqlite":
            raise RuntimeError("This v135 operations extension currently requires the local SQLite backend.")

    @staticmethod
    def _user_id(con: Any, username: str) -> int:
        row = con.execute(
            "SELECT id FROM users WHERE lower(username) = lower(?) AND active = 1",
            (clean_text(username, 80),),
        ).fetchone()
        if not row:
            raise ValueError("Active user was not found")
        return int(row["id"])

    @staticmethod
    def _audit(con: Any, entity_type: str, entity_id: str, action: str, username: str, payload: dict[str, Any]) -> None:
        con.execute(
            """
            INSERT INTO audit_events (
                entity_type, entity_id, action, user_name, station, reason, payload_json, created_at
            ) VALUES (?, ?, ?, ?, '', '', ?, ?)
            """,
            (entity_type, entity_id, action, username, json.dumps(payload, separators=(",", ":")), utc_now()),
        )

    def line_flags(self, list_id: str, username: str) -> dict[str, Any]:
        """Return per-user update flags plus manual/reject metadata for one list."""
        self._require_sqlite()
        clean_list_id = clean_text(list_id, 255)
        with self.store.connect() as con:
            user_id = self._user_id(con, username)
            rows = con.execute(
                """
                SELECT li.id,
                       COALESCE(li.manual_only, 0) AS manual_only,
                       COALESCE(li.manual_source, '') AS manual_source,
                       COALESCE(li.internal_reject_count, 0) AS internal_reject_count,
                       COALESCE(li.last_reject_reason, '') AS last_reject_reason,
                       COALESCE(li.last_reject_location, '') AS last_reject_location,
                       COALESCE(li.last_rejected_at, '') AS last_rejected_at,
                       n.id AS notice_id,
                       n.change_type AS change_type,
                       n.created_at AS notice_created_at,
                       r.notice_id AS receipt_notice_id
                FROM line_items li
                LEFT JOIN line_update_notices n
                  ON n.line_item_id = li.id
                 AND n.list_id = li.list_id
                LEFT JOIN line_update_receipts r
                  ON r.notice_id = n.id
                 AND r.user_id = ?
                WHERE li.list_id = ?
                ORDER BY li.id, n.id
                """,
                (user_id, clean_list_id),
            ).fetchall()

        items: dict[str, dict[str, Any]] = {}
        notice_ids: list[int] = []
        for row in rows:
            item_id = str(row["id"])
            target = items.setdefault(
                item_id,
                {
                    "lineItemId": item_id,
                    "manualOnly": bool(row["manual_only"]),
                    "manualSource": str(row["manual_source"] or ""),
                    "internalRejectCount": int(row["internal_reject_count"] or 0),
                    "lastRejectReason": str(row["last_reject_reason"] or ""),
                    "lastRejectLocation": str(row["last_reject_location"] or ""),
                    "lastRejectedAt": str(row["last_rejected_at"] or ""),
                    "userUpdateState": "",
                    "userUpdateNoticeIds": [],
                    "hasUnseenUpdate": False,
                },
            )
            notice_id = as_int(row["notice_id"])
            receipt_notice_id = as_int(row["receipt_notice_id"])
            if notice_id > 0 and receipt_notice_id <= 0:
                target["hasUnseenUpdate"] = True
                target["userUpdateNoticeIds"].append(notice_id)
                notice_ids.append(notice_id)
                change_type = str(row["change_type"] or "updated").lower()
                if change_type == "new" or not target["userUpdateState"]:
                    target["userUpdateState"] = change_type

        values = list(items.values())
        return {
            "ok": True,
            "listId": clean_list_id,
            "pendingLineCount": sum(1 for item in values if item["hasUnseenUpdate"]),
            "newLineCount": sum(1 for item in values if item["userUpdateState"] == "new"),
            "updatedLineCount": sum(1 for item in values if item["userUpdateState"] == "updated"),
            "noticeIds": sorted(set(notice_ids)),
            "items": values,
        }

    def acknowledge_line_updates(self, list_id: str, notice_ids: list[Any], username: str) -> dict[str, Any]:
        """Mark only the explicitly reviewed notices read for one user and list."""
        self._require_sqlite()
        clean_list_id = clean_text(list_id, 255)
        requested_ids = sorted({as_int(value) for value in (notice_ids or []) if as_int(value) > 0})
        if not clean_list_id:
            raise ValueError("listId is required")
        if not requested_ids:
            raise ValueError("No reviewed delivery-list updates were supplied")

        with self.store.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            user_id = self._user_id(con, username)
            placeholders = ",".join("?" for _ in requested_ids)
            rows = con.execute(
                f"""
                SELECT id
                FROM line_update_notices
                WHERE list_id = ? AND id IN ({placeholders})
                ORDER BY id
                """,
                [clean_list_id, *requested_ids],
            ).fetchall()
            valid_ids = [int(row["id"]) for row in rows]
            if valid_ids != requested_ids:
                raise ValueError(
                    "The reviewed updates changed before they could be saved. Refresh the list and review the latest updates."
                )
            seen_at = utc_now()
            con.executemany(
                """
                INSERT OR IGNORE INTO line_update_receipts (notice_id, user_id, seen_at)
                VALUES (?, ?, ?)
                """,
                [(notice_id, user_id, seen_at) for notice_id in valid_ids],
            )
            self._audit(
                con,
                "delivery_list_updates",
                clean_list_id,
                "acknowledge_line_updates",
                username,
                {"noticeIds": valid_ids, "seenAt": seen_at},
            )
            con.commit()
        return self.line_flags(clean_list_id, username)

    def reject_catalog(self) -> dict[str, Any]:
        self._require_sqlite()
        with self.store.connect() as con:
            reasons = con.execute(
                "SELECT id, label, active, created_at FROM reject_reasons WHERE active = 1 ORDER BY sort_order, label"
            ).fetchall()
            locations = con.execute(
                "SELECT id, label, active, created_at FROM reject_locations WHERE active = 1 ORDER BY sort_order, label"
            ).fetchall()
        return {
            "reasons": [dict(row) for row in reasons],
            "locations": [dict(row) for row in locations],
        }

    def upsert_reject_catalog(self, kind: str, label: str, username: str) -> dict[str, Any]:
        self._require_sqlite()
        clean_kind = str(kind or "").strip().lower()
        if clean_kind not in {"reason", "location"}:
            raise ValueError("Catalog type must be reason or location")
        clean_label = clean_text(label, 120)
        if not clean_label:
            raise ValueError("A label is required")
        table = "reject_reasons" if clean_kind == "reason" else "reject_locations"
        with self.store.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute(
                f"""
                INSERT INTO {table} (label, active, sort_order, created_by, created_at, updated_at)
                VALUES (?, 1, 999, ?, ?, ?)
                ON CONFLICT(label) DO UPDATE SET active = 1, updated_at = excluded.updated_at
                """,
                (clean_label, username, utc_now(), utc_now()),
            )
            self._audit(con, "reject_catalog", clean_kind, "upsert_reject_catalog", username, {"label": clean_label})
            con.commit()
        return self.reject_catalog()

    def remove_reject_catalog(self, kind: str, catalog_id: int, username: str) -> dict[str, Any]:
        self._require_sqlite()
        clean_kind = str(kind or "").strip().lower()
        if clean_kind not in {"reason", "location"}:
            raise ValueError("Catalog type must be reason or location")
        table = "reject_reasons" if clean_kind == "reason" else "reject_locations"
        with self.store.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute(f"UPDATE {table} SET active = 0, updated_at = ? WHERE id = ?", (utc_now(), int(catalog_id)))
            self._audit(con, "reject_catalog", str(catalog_id), "remove_reject_catalog", username, {"kind": clean_kind})
            con.commit()
        return self.reject_catalog()

    def reject_matches(self, order_no: str, item_no: str) -> dict[str, Any]:
        self._require_sqlite()
        order = clean_order(order_no)
        item = clean_item(item_no)
        with self.store.connect() as con:
            rows = con.execute(
                """
                SELECT dl.delivery_date, li.order_no, li.item_no,
                       MAX(li.customer) AS customer, MAX(li.job) AS job, MAX(li.product) AS product,
                       MAX(li.qty) AS qty, MAX(li.internal_reject_count) AS reject_count,
                       GROUP_CONCAT(DISTINCT dl.stage) AS stages
                FROM line_items li
                JOIN delivery_lists dl ON dl.id = li.list_id
                WHERE dl.status = 'active' AND li.order_no = ? AND li.item_no = ?
                GROUP BY dl.delivery_date, li.order_no, li.item_no
                ORDER BY dl.delivery_date DESC
                """,
                (order, item),
            ).fetchall()
        return {"matches": [dict(row) for row in rows]}

    def list_rejects(self, date_from: str = "", date_to: str = "", query: str = "", limit: int = 500) -> dict[str, Any]:
        self._require_sqlite()
        clauses = ["1 = 1"]
        params: list[Any] = []
        if date_from:
            clauses.append("substr(rejected_at, 1, 10) >= ?")
            params.append(date_from)
        if date_to:
            clauses.append("substr(rejected_at, 1, 10) <= ?")
            params.append(date_to)
        if query:
            like = f"%{clean_text(query, 120)}%"
            clauses.append("(order_no LIKE ? OR item_no LIKE ? OR customer LIKE ? OR reason_label LIKE ? OR location_label LIKE ?)")
            params.extend([like, like, like, like, like])
        params.append(max(1, min(int(limit or 500), 2000)))
        with self.store.connect() as con:
            rows = con.execute(
                f"""
                SELECT * FROM reject_events
                WHERE {' AND '.join(clauses)}
                ORDER BY rejected_at DESC, id DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
        return {"rejects": [dict(row) for row in rows]}

    def create_reject(self, data: dict[str, Any], username: str) -> dict[str, Any]:
        """Log an internal reject and roll the rejected piece(s) back one process pass."""
        self._require_sqlite()
        order = clean_order(data.get("order"))
        item = clean_item(data.get("item"))
        reason = clean_text(data.get("reason"), 120)
        location = clean_text(data.get("location"), 120)
        delivery_date = clean_text(data.get("deliveryDate"), 10)
        qty = max(1, as_int(data.get("qty"), 1))
        notes = clean_text(data.get("notes"), 500)
        if not reason or not location:
            raise ValueError("Reject reason and break location are required")

        with self.store.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            if not delivery_date:
                date_row = con.execute(
                    """
                    SELECT dl.delivery_date
                    FROM line_items li JOIN delivery_lists dl ON dl.id = li.list_id
                    WHERE dl.status = 'active' AND li.order_no = ? AND li.item_no = ?
                    ORDER BY CASE WHEN dl.delivery_date >= date('now') THEN 0 ELSE 1 END,
                             ABS(julianday(dl.delivery_date) - julianday('now')), dl.delivery_date DESC
                    LIMIT 1
                    """,
                    (order, item),
                ).fetchone()
                delivery_date = str(row_value(date_row, "delivery_date", ""))
            rows = con.execute(
                """
                SELECT li.*, dl.delivery_date, dl.stage, dl.scanner
                FROM line_items li JOIN delivery_lists dl ON dl.id = li.list_id
                WHERE dl.status = 'active' AND dl.delivery_date = ?
                  AND li.order_no = ? AND li.item_no = ?
                ORDER BY dl.stage, li.id
                """,
                (delivery_date, order, item),
            ).fetchall()
            if not rows:
                raise ValueError("That order/item was not found on an active delivery list for the selected date")
            max_qty = max(int(row["qty"] or 0) for row in rows)
            if qty > max_qty:
                raise ValueError(f"Reject quantity cannot be greater than the line quantity ({max_qty})")

            rejected_at = utc_now()
            affected_lists: list[str] = []
            total_scan_reduction = 0
            for row in rows:
                line_id = str(row["id"])
                list_id = str(row["list_id"])
                affected_lists.append(list_id)
                before = int(row["scanned_qty"] or 0)
                reduction = min(before, qty)
                after = max(before - qty, 0)
                total_scan_reduction += reduction
                con.execute(
                    """
                    UPDATE line_items
                    SET scanned_qty = ?,
                        internal_reject_count = COALESCE(internal_reject_count, 0) + ?,
                        last_reject_reason = ?, last_reject_location = ?, last_rejected_at = ?,
                        updated_at_utc = ?
                    WHERE id = ?
                    """,
                    (after, qty, reason, location, rejected_at, rejected_at, line_id),
                )
                con.execute(
                    """
                    INSERT INTO scan_events (
                        list_id, line_item_id, barcode, canonical_barcode, user_name, station,
                        event_type, message, reason, qty_delta, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 'reject_reset', ?, ?, ?, ?)
                    """,
                    (
                        list_id,
                        line_id,
                        str(row["barcode"] or ""),
                        str(row["barcode"] or ""),
                        username,
                        location,
                        f"Internal reject reset {order}-{item}",
                        f"{reason} at {location}",
                        -reduction,
                        rejected_at,
                    ),
                )

                rack_rows = con.execute(
                    "SELECT id, qty FROM rack_items WHERE line_item_id = ? AND status = 'Active' ORDER BY id DESC",
                    (line_id,),
                ).fetchall()
                remaining = qty
                for rack_row in rack_rows:
                    if remaining <= 0:
                        break
                    rack_qty = int(rack_row["qty"] or 0)
                    take = min(rack_qty, remaining)
                    next_qty = rack_qty - take
                    con.execute(
                        """
                        UPDATE rack_items
                        SET qty = ?, status = CASE WHEN ? <= 0 THEN 'Removed' ELSE status END,
                            removed_by = CASE WHEN ? <= 0 THEN ? ELSE removed_by END,
                            removed_at = CASE WHEN ? <= 0 THEN ? ELSE removed_at END,
                            reason = ?, updated_at_utc = ?
                        WHERE id = ?
                        """,
                        (next_qty, next_qty, next_qty, username, next_qty, rejected_at, "Internal reject", rejected_at, rack_row["id"]),
                    )
                    remaining -= take

                bay_rows = con.execute(
                    """
                    SELECT id, assigned_qty FROM bay_assignments
                    WHERE line_item_id = ? AND status NOT IN ('Cleared', 'Cancelled')
                    ORDER BY id DESC
                    """,
                    (line_id,),
                ).fetchall()
                remaining = qty
                for bay_row in bay_rows:
                    if remaining <= 0:
                        break
                    assigned = int(bay_row["assigned_qty"] or 0)
                    take = min(assigned, remaining)
                    next_qty = assigned - take
                    con.execute(
                        """
                        UPDATE bay_assignments
                        SET assigned_qty = ?, status = CASE WHEN ? <= 0 THEN 'Cleared' ELSE status END,
                            cleared_by = CASE WHEN ? <= 0 THEN ? ELSE cleared_by END,
                            cleared_at = CASE WHEN ? <= 0 THEN ? ELSE cleared_at END,
                            reason = ?, updated_at_utc = ?
                        WHERE id = ?
                        """,
                        (next_qty, next_qty, next_qty, username, next_qty, rejected_at, "Internal reject", rejected_at, bay_row["id"]),
                    )
                    remaining -= take

            representative = rows[0]
            cursor = con.execute(
                """
                INSERT INTO reject_events (
                    delivery_date, order_no, item_no, qty, customer, job, product,
                    reason_label, location_label, notes, rejected_at, rejected_by,
                    source_list_id, source_line_item_id, affected_list_ids_json, scan_qty_reduced
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    delivery_date,
                    order,
                    item,
                    qty,
                    str(representative["customer"] or ""),
                    str(representative["job"] or ""),
                    str(representative["product"] or ""),
                    reason,
                    location,
                    notes,
                    rejected_at,
                    username,
                    str(representative["list_id"]),
                    str(representative["id"]),
                    json.dumps(sorted(set(affected_lists))),
                    total_scan_reduction,
                ),
            )
            reject_id = int(cursor.lastrowid)
            self._audit(
                con,
                "internal_reject",
                str(reject_id),
                "create_internal_reject",
                username,
                {
                    "deliveryDate": delivery_date,
                    "order": order,
                    "item": item,
                    "qty": qty,
                    "reason": reason,
                    "location": location,
                    "affectedListIds": sorted(set(affected_lists)),
                    "scanQtyReduced": total_scan_reduction,
                },
            )
            notifier = getattr(self.store, "create_app_notification", None)
            if callable(notifier):
                notifier(
                    con,
                    "warning",
                    "Internal reject logged",
                    f"Order {order} / Item {item}: {qty} piece{'s' if qty != 1 else ''} rejected at {location} ({reason}).",
                    username,
                    payload={
                        "source": "internal-reject",
                        "rejectId": reject_id,
                        "order": order,
                        "item": item,
                        "qty": qty,
                        "deliveryDate": delivery_date,
                        "reason": reason,
                        "location": location,
                        "rejectedAt": rejected_at,
                    },
                    expires_in_hours=72,
                    acknowledge_creator=False,
                )
            con.commit()
        return {
            "ok": True,
            "rejectId": reject_id,
            "message": f"Internal reject recorded for {order}-{item}. The rejected piece was returned to the start of the process.",
            **self.list_rejects(limit=500),
        }

    def _automation_window(self) -> tuple[str, str]:
        today = date.today()
        past_days, future_days = 7, 90
        candidates = [
            Path(r"C:\DeliveryListAutomation\Scripts\sql-export.config.json"),
            self.project_root / "automation" / "sql_delivery_export" / "sql-export.config.json",
        ]
        for path in candidates:
            try:
                payload = json.loads(path.read_text(encoding="utf-8-sig"))
                schedule = payload.get("Schedule") or {}
                past_days = max(as_int(schedule.get("FullPastDays"), past_days), 0)
                future_days = max(as_int(schedule.get("FullFutureDays"), future_days), 0)
                break
            except (OSError, ValueError, TypeError):
                continue
        return (today - timedelta(days=past_days)).isoformat(), (today + timedelta(days=future_days)).isoformat()

    @staticmethod
    def _route_matches_stage(route: str, stage: str, scanner: str) -> bool:
        text = f"{stage} {scanner}".lower()
        if "staging" in text or "outbound" in text:
            return True
        route = route.upper()
        if route == "CPU":
            return "pickup" in text or "cpu" in text
        if route == "DTC":
            return "dtc" in text or "deliver to customer" in text
        if route in {"GNV", "GREENVILLE"}:
            return "greenville" in text
        return "indian trail" in text or "inbound" in text

    def create_manual_order(self, data: dict[str, Any], username: str) -> dict[str, Any]:
        """Add one manually entered order/item across the correct workflow stages."""
        self._require_sqlite()
        selected_list_id = clean_text(data.get("listId"), 255)
        order = clean_order(data.get("order"))
        item = clean_item(data.get("item"))
        route = clean_text(data.get("route"), 40).upper()
        qty = as_int(data.get("qty"), 0)
        customer = clean_text(data.get("customer"), 240)
        product = clean_text(data.get("product"), 240)
        dimensions = clean_text(data.get("dimensions"), 120)
        job = clean_text(data.get("job"), 240)
        process_state = clean_text(data.get("processState"), 120)
        manual_only = bool(data.get("manualOnly"))
        if not selected_list_id:
            raise ValueError("Choose the delivery list that should receive the manual order")
        if route not in {"IT", "CPU", "DTC", "GNV", "GREENVILLE"}:
            raise ValueError("Choose a route before adding the order")
        if qty <= 0:
            raise ValueError("Quantity must be greater than zero")
        missing = [label for label, value in (("Customer", customer), ("Glass/product", product), ("Dimensions", dimensions)) if not value]
        if missing:
            raise ValueError("Complete the required fields: " + ", ".join(missing))

        date_from, date_to = self._automation_window()
        with self.store.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            selected = con.execute(
                "SELECT * FROM delivery_lists WHERE id = ? AND status = 'active'",
                (selected_list_id,),
            ).fetchone()
            if not selected:
                raise ValueError("Selected delivery list was not found")
            duplicate = con.execute(
                """
                SELECT dl.delivery_date, dl.stage
                FROM line_items li JOIN delivery_lists dl ON dl.id = li.list_id
                WHERE dl.status = 'active' AND dl.delivery_date BETWEEN ? AND ?
                  AND li.order_no = ? AND li.item_no = ?
                ORDER BY dl.delivery_date, dl.stage LIMIT 1
                """,
                (date_from, date_to, order, item),
            ).fetchone()
            if duplicate:
                raise ValueError(
                    f"Order {order}-{item} already exists in the automatic import window "
                    f"({duplicate['delivery_date']} - {duplicate['stage']})."
                )
            delivery_date = str(selected["delivery_date"])
            candidates = con.execute(
                "SELECT * FROM delivery_lists WHERE delivery_date = ? AND status = 'active' ORDER BY stage, id",
                (delivery_date,),
            ).fetchall()
            target_lists = [row for row in candidates if self._route_matches_stage(route, str(row["stage"]), str(row["scanner"]))]
            if not any(str(row["id"]) == selected_list_id for row in target_lists):
                target_lists.append(selected)
            unique_targets = {str(row["id"]): row for row in target_lists}
            created_at = utc_now()
            source_id = f"manual:{delivery_date}:{order}:{item}:{created_at}"
            inserted_ids: list[str] = []
            for target in unique_targets.values():
                payload = {
                    "id": source_id,
                    "order": order,
                    "item": item,
                    "qty": qty,
                    "dimensions": dimensions,
                    "customer": customer,
                    "route": "GNV" if route == "GREENVILLE" else route,
                    "sourceRoute": "manual",
                    "job": job,
                    "product": product,
                    "processState": " ".join(part for part in [process_state, "Manual Entry"] if part).strip(),
                    "queueState": "Manual scanning only" if manual_only else "",
                }
                inserted = self.store.insert_line_items(con, str(target["id"]), [payload])
                if not inserted:
                    continue
                line = inserted[0]
                line_id = str(line["id"])
                inserted_ids.append(line_id)
                if manual_only:
                    con.execute(
                        "UPDATE line_items SET barcode = ?, manual_only = 1, manual_source = ?, updated_at_utc = ? WHERE id = ?",
                        (f"MANUAL-{order}-{item}", username, created_at, line_id),
                    )
                else:
                    con.execute(
                        "UPDATE line_items SET manual_source = ?, updated_at_utc = ? WHERE id = ?",
                        (username, created_at, line_id),
                    )
                con.execute(
                    """
                    INSERT OR IGNORE INTO line_update_notices (
                        line_item_id, list_id, delivery_date, change_type, change_token, source_hash, created_at
                    ) VALUES (?, ?, ?, 'new', ?, 'manual-entry', ?)
                    """,
                    (line_id, str(target["id"]), delivery_date, source_id, created_at),
                )
            con.execute(
                """
                INSERT INTO manual_delivery_entries (
                    delivery_date, order_no, item_no, qty, route, customer, job, product,
                    dimensions, manual_only, created_by, created_at, target_list_ids_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    delivery_date,
                    order,
                    item,
                    qty,
                    route,
                    customer,
                    job,
                    product,
                    dimensions,
                    int(manual_only),
                    username,
                    created_at,
                    json.dumps(sorted(unique_targets)),
                ),
            )
            self._audit(
                con,
                "manual_delivery_entry",
                f"{delivery_date}:{order}:{item}",
                "create_manual_delivery_entry",
                username,
                {"targetListIds": sorted(unique_targets), "manualOnly": manual_only, "route": route, "qty": qty},
            )
            con.commit()
        return {
            "ok": True,
            "message": f"Manual order {order}-{item} was added to {len(inserted_ids)} workflow stage(s).",
            "lineItemIds": inserted_ids,
            "listIds": sorted(unique_targets),
            "deliveryDate": delivery_date,
        }

    def record_packing_print(self, data: dict[str, Any], username: str) -> dict[str, Any]:
        self._require_sqlite()
        rack_code = clean_text(data.get("rackCode"), 80)
        delivery_date = clean_text(data.get("deliveryDate"), 10)
        if not rack_code:
            raise ValueError("Rack code is required")
        with self.store.connect() as con:
            rack = con.execute("SELECT * FROM racks WHERE rack_code = ?", (rack_code,)).fetchone()
            if not rack:
                raise ValueError("Rack was not found")
            params: list[Any] = [rack_code]
            date_clause = ""
            if delivery_date:
                date_clause = " AND dl.delivery_date = ?"
                params.append(delivery_date)
            rows = con.execute(
                f"""
                SELECT li.order_no, li.item_no, ri.qty AS rack_qty, li.customer, li.job, li.product,
                       li.dimensions, li.route, dl.delivery_date, dl.stage, ri.added_at
                FROM rack_items ri
                JOIN racks r ON r.id = ri.rack_id
                JOIN line_items li ON li.id = ri.line_item_id
                JOIN delivery_lists dl ON dl.id = li.list_id
                WHERE r.rack_code = ? AND ri.status = 'Active' {date_clause}
                ORDER BY dl.delivery_date, CAST(li.order_no AS INTEGER), CAST(li.item_no AS INTEGER)
                """,
                params,
            ).fetchall()
            items = [dict(row) for row in rows]
            if not items:
                raise ValueError("No rack items were available to record in print history")
            print_date = delivery_date or (str(items[0].get("delivery_date") or "") if len({str(x.get('delivery_date') or '') for x in items}) == 1 else "")
            printed_at = utc_now()
            snapshot = {
                "rackCode": rack_code,
                "rackName": str(rack["display_name"] or rack_code),
                "rackType": str(rack["rack_type"] or ""),
                "rackStatus": str(rack["status"] or ""),
                "deliveryDate": print_date,
                "printedAt": printed_at,
                "printedBy": username,
                "items": items,
            }
            cursor = con.execute(
                """
                INSERT INTO packing_list_prints (
                    rack_code, rack_name, delivery_date, printed_at, printed_by,
                    piece_qty, line_count, snapshot_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rack_code,
                    str(rack["display_name"] or rack_code),
                    print_date,
                    printed_at,
                    username,
                    sum(int(row.get("rack_qty") or 0) for row in items),
                    len(items),
                    json.dumps(snapshot, separators=(",", ":")),
                ),
            )
            history_id = int(cursor.lastrowid)
            self._audit(con, "packing_list_print", str(history_id), "record_packing_list_print", username, {"rackCode": rack_code, "deliveryDate": print_date})
            con.commit()
        return {"ok": True, "historyId": history_id, "printedAt": printed_at}

    def packing_history(self, limit: int = 250) -> dict[str, Any]:
        self._require_sqlite()
        with self.store.connect() as con:
            rows = con.execute(
                """
                SELECT id, rack_code, rack_name, delivery_date, printed_at, printed_by, piece_qty, line_count
                FROM packing_list_prints ORDER BY printed_at DESC, id DESC LIMIT ?
                """,
                (max(1, min(int(limit or 250), 1000)),),
            ).fetchall()
        return {"history": [dict(row) for row in rows]}

    def packing_history_print_html(self, history_id: int) -> str:
        self._require_sqlite()
        with self.store.connect() as con:
            row = con.execute("SELECT * FROM packing_list_prints WHERE id = ?", (int(history_id),)).fetchone()
        if not row:
            raise KeyError("Packing-list history record not found")
        snapshot = json.loads(str(row["snapshot_json"] or "{}"))
        items = snapshot.get("items") or []
        title = f"Historical Packing List - {snapshot.get('rackName') or snapshot.get('rackCode') or ''}"
        lines = "".join(
            "<tr>"
            f"<td>{html.escape(str(item.get('order_no') or ''))}</td>"
            f"<td>{html.escape(str(item.get('item_no') or ''))}</td>"
            f"<td>{html.escape(str(item.get('rack_qty') or ''))}</td>"
            f"<td>{html.escape(str(item.get('customer') or ''))}</td>"
            f"<td>{html.escape(str(item.get('job') or item.get('product') or ''))}</td>"
            f"<td>{html.escape(str(item.get('dimensions') or ''))}</td>"
            f"<td>{html.escape(str(item.get('delivery_date') or ''))}</td>"
            "</tr>"
            for item in items
        )
        return f"""<!doctype html><html><head><meta charset='utf-8'><title>{html.escape(title)}</title>
<style>body{{font:14px Arial;margin:24px;color:#10213d}}h1{{margin:0 0 6px}}p{{margin:3px 0 14px}}table{{width:100%;border-collapse:collapse}}th,td{{border:1px solid #9aa8bd;padding:7px;text-align:left}}th{{background:#eaf1fb}}@media print{{button{{display:none}}body{{margin:0}}}}</style></head><body>
<button onclick='window.print()'>Print</button><h1>{html.escape(title)}</h1>
<p>Original print: {html.escape(str(snapshot.get('printedAt') or row['printed_at']))} by {html.escape(str(snapshot.get('printedBy') or row['printed_by']))}</p>
<p>Delivery date: {html.escape(str(snapshot.get('deliveryDate') or 'Mixed dates'))} &middot; Pieces: {html.escape(str(row['piece_qty']))}</p>
<table><thead><tr><th>Order</th><th>Item</th><th>Qty</th><th>Customer</th><th>Job / Glass</th><th>Dimensions</th><th>Delivery Date</th></tr></thead><tbody>{lines}</tbody></table>
<script>window.addEventListener('load',()=>setTimeout(()=>window.print(),250));</script></body></html>"""
