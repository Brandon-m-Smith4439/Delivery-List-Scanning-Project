#!/usr/bin/env python3
# File: automation/sql_delivery_export/import_delivery_folder.py
"""Import SQL-generated delivery workbooks through the maintained scanner store.

The wrapper deliberately reuses backend/config.py and backend/store.py. It
never reimplements route, stage, scan-preservation, rack, bay, or audit rules.
For SQL synchronization runs it performs a read-only source-row preflight:
unchanged workbooks are skipped only when every generated stage and source-owned
scanner row still matches the workbook. Missing, added, changed, or removed
scanner rows send that exact delivery date through the maintained importer.
"""

from __future__ import annotations

from collections import Counter
import argparse
import json
import os
import re
import sqlite3
import sys
import time
import traceback
from datetime import date, timedelta
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    """Parse the project, source folder, date window, audit user, and result path."""
    parser = argparse.ArgumentParser(description="Import automated SQL delivery-list workbooks.")
    parser.add_argument("--project-root", required=True, help="Delivery List Scanner project folder.")
    parser.add_argument("--folder", required=True, help="Folder containing generated workbooks.")
    parser.add_argument(
        "--date-from",
        default=(date.today() - timedelta(days=7)).isoformat(),
        help="Oldest delivery date to import, in YYYY-MM-DD format.",
    )
    parser.add_argument("--date-to", default="", help="Newest delivery date in YYYY-MM-DD format.")
    parser.add_argument("--user", default="sql-auto-import", help="Audit user recorded by the importer.")
    parser.add_argument("--run-id", default="", help="Stable automation request/run identifier.")
    parser.add_argument("--run-started-at", default="", help="Automation run start timestamp.")
    parser.add_argument(
        "--initialize-store",
        choices=("true", "false"),
        default="true",
        help="Initialize/upgrade the configured scanner store before importing.",
    )
    parser.add_argument(
        "--result-path",
        default="",
        help="Optional JSON file that receives the normalized import result.",
    )
    parser.add_argument(
        "--sync-request-path",
        default="",
        help=(
            "Optional JSON request for SQL synchronization. The request contains targetDates "
            "to verify and forceImportDates that must pass through the maintained importer."
        ),
    )
    return parser.parse_args()


def int_value(value: Any) -> int:
    """Return a non-negative integer for scanner result counters."""
    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError):
        return 0


def transient_database_busy_error(exc: BaseException) -> bool:
    """Return True only for retryable database lock/busy failures."""
    text = str(exc or "").lower()
    return isinstance(exc, sqlite3.OperationalError) and ("locked" in text or "busy" in text) or any(
        marker in text
        for marker in (
            "database is locked",
            "database is busy",
            "deadlock victim",
            "lock request time out",
            "timeout expired",
        )
    )


def run_with_database_retry(action: Any, label: str, attempts: int = 12) -> Any:
    """Favor active scanner writes by retrying a busy importer with backoff.

    SQLite and Azure SQL serialize conflicting writes. The importer should wait
    for a scan transaction instead of turning a temporary lock into a failed
    automated update. Non-lock errors are raised immediately.
    """
    delay = 0.25
    for attempt in range(1, attempts + 1):
        try:
            return action()
        except Exception as exc:
            if not transient_database_busy_error(exc) or attempt >= attempts:
                raise
            print(
                f"Scanner database is busy while {label}; waiting {delay:.2f}s "
                f"before retry {attempt + 1}/{attempts}.",
                flush=True,
            )
            time.sleep(delay)
            delay = min(delay * 1.7, 2.0)
    raise RuntimeError(f"Could not complete {label} after database-busy retries.")


def delivery_date_from_name(value: Any) -> str:
    """Read an MM-DD-YYYY style delivery date from a workbook name."""
    text = str(value or "")
    match = re.search(r"(?<!\d)(\d{1,2})[._-](\d{1,2})[._-](\d{2,4})(?!\d)", text)
    if not match:
        return ""
    month, day, year = (int(part) for part in match.groups())
    if year < 100:
        year += 2000
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return ""


def result_delivery_date(row: dict[str, Any]) -> str:
    """Return the explicit result date or derive it from the source filename."""
    return str(
        row.get("deliveryDate")
        or row.get("fileNameDate")
        or delivery_date_from_name(row.get("fileName") or row.get("sourceName"))
        or ""
    ).strip()


def file_result(row: dict[str, Any], result_type: str) -> dict[str, Any]:
    """Normalize one imported, updated, skipped, or failed file result."""
    created_count = int_value(row.get("createdCount"))
    updated_count = int_value(row.get("updatedCount"))
    reactivated_count = int_value(row.get("reactivatedCount"))
    list_ids = [
        str(value)
        for value in (row.get("listIds") or [])
        if value
    ]
    changed_list_ids = [
        str(value)
        for value in (row.get("changedListIds") or [])
        if value
    ]
    removed_line_count = int_value(row.get("removedLineCount"))
    removed_piece_qty = int_value(row.get("removedPieceQty"))
    duplicate_manual_line_count = int_value(row.get("duplicateManualLineCount"))
    duplicate_manual_piece_qty = int_value(row.get("duplicateManualPieceQty"))

    if result_type == "failed":
        classification = "failed"
        label = "Failed"
    elif result_type == "skipped":
        classification = "no_changes"
        label = "No Changes"
    elif created_count and updated_count:
        classification = "new_updated"
        label = "New + Updated"
    elif created_count:
        classification = "new"
        label = "New"
    elif updated_count or changed_list_ids or removed_line_count or removed_piece_qty:
        classification = "updated"
        label = "Updated"
    else:
        classification = "no_changes"
        label = "No Changes"

    errors = row.get("errors") or []
    if isinstance(errors, str):
        errors = [errors]

    return {
        "fileName": str(row.get("fileName") or row.get("sourceName") or ""),
        "deliveryDate": result_delivery_date(row),
        "classification": classification,
        "classificationLabel": label,
        "createdCount": created_count,
        "updatedCount": updated_count,
        "reactivatedCount": reactivated_count,
        "rowCount": int_value(row.get("rowCount")),
        "totalQty": int_value(row.get("totalQty")),
        "newPieceQty": int_value(row.get("newPieceQty")),
        "updatedPieceQty": int_value(row.get("updatedPieceQty")),
        "addedPieceQty": int_value(row.get("addedPieceQty")),
        "changedPieceQty": int_value(row.get("changedPieceQty")),
        "removedLineCount": removed_line_count,
        "removedPieceQty": removed_piece_qty,
        "duplicateManualLineCount": duplicate_manual_line_count,
        "duplicateManualPieceQty": duplicate_manual_piece_qty,
        "listIds": list_ids,
        "changedListIds": changed_list_ids,
        "reactivatedListIds": [
            str(value)
            for value in (row.get("reactivatedListIds") or [])
            if value
        ],
        "stageSummaries": [
            dict(value)
            for value in (row.get("stageSummaries") or row.get("stages") or [])
            if isinstance(value, dict)
        ],
        "reason": str(row.get("reason") or ""),
        "errors": [str(value) for value in errors if str(value).strip()],
    }


def normalize_result(
    result: dict[str, Any],
    date_from: str = "",
    date_to: str = "",
) -> dict[str, Any]:
    """Create one stable summary limited to the requested delivery-date window."""

    def in_requested_window(row: dict[str, Any]) -> bool:
        delivery_date = result_delivery_date(row)
        if not delivery_date:
            return True
        if date_from and delivery_date < date_from:
            return False
        if date_to and delivery_date > date_to:
            return False
        return True

    imported_rows = [
        file_result(row, "imported")
        for row in (result.get("importedFiles") or [])
        if isinstance(row, dict) and in_requested_window(row)
    ]
    updated_rows = [
        file_result(row, "updated")
        for row in (result.get("updatedFiles") or [])
        if isinstance(row, dict) and in_requested_window(row)
    ]
    skipped_rows = [
        file_result(row, "skipped")
        for row in (result.get("skippedFiles") or [])
        if isinstance(row, dict) and in_requested_window(row)
    ]
    failed_rows = [
        file_result(row, "failed")
        for row in (result.get("failedFiles") or [])
        if isinstance(row, dict) and in_requested_window(row)
    ]
    files = imported_rows + updated_rows + skipped_rows + failed_rows

    successful_dates = sorted(
        {
            row["deliveryDate"]
            for row in imported_rows + updated_rows + skipped_rows
            if row.get("deliveryDate")
        }
    )
    changed_dates = sorted(
        {
            row["deliveryDate"]
            for row in imported_rows + updated_rows
            if row.get("deliveryDate")
        }
    )
    failed_dates = sorted({row["deliveryDate"] for row in failed_rows if row.get("deliveryDate")})

    return {
        "ok": bool(result.get("ok", not failed_rows)) and not failed_rows,
        "activeListId": str(result.get("activeListId") or ""),
        "sourceFolder": str(result.get("sourceFolder") or ""),
        "dateFrom": str(result.get("dateFrom") or date_from or ""),
        "dateTo": str(result.get("dateTo") or date_to or ""),
        "totalFolderFiles": int_value(result.get("totalFolderFiles")),
        "candidateFiles": int_value(result.get("candidateFiles")),
        "checkedFiles": int_value(result.get("checkedFiles") or result.get("scannedFiles")),
        "newFileCount": len(imported_rows),
        "updatedFileCount": len(updated_rows),
        "noChangeFileCount": len(skipped_rows),
        "failedFileCount": len(failed_rows),
        "createdCount": sum(row["createdCount"] for row in imported_rows + updated_rows),
        "updatedCount": sum(row["updatedCount"] for row in imported_rows + updated_rows),
        "reactivatedCount": sum(row.get("reactivatedCount", 0) for row in imported_rows + updated_rows),
        "newPieceQty": sum(row["newPieceQty"] for row in imported_rows + updated_rows),
        "updatedPieceQty": sum(row["updatedPieceQty"] for row in imported_rows + updated_rows),
        "addedPieceQty": sum(row["addedPieceQty"] for row in imported_rows + updated_rows),
        "changedPieceQty": sum(row["changedPieceQty"] for row in imported_rows + updated_rows),
        "removedLineCount": sum(row["removedLineCount"] for row in imported_rows + updated_rows),
        "removedPieceQty": sum(row["removedPieceQty"] for row in imported_rows + updated_rows),
        "duplicateManualLineCount": sum(
            row["duplicateManualLineCount"] for row in imported_rows + updated_rows
        ),
        "duplicateManualPieceQty": sum(
            row["duplicateManualPieceQty"] for row in imported_rows + updated_rows
        ),
        "importedDates": successful_dates,
        "changedDates": changed_dates,
        "failedDates": failed_dates,
        "files": files,
    }


def summary_from_files(
    files: list[dict[str, Any]],
    source_folder: Path,
    date_from: str,
    date_to: str,
    active_list_id: str = "",
    recovered_dates: set[str] | None = None,
) -> dict[str, Any]:
    """Build the stable result summary used by PowerShell and the Admin UI."""
    recovered_dates = recovered_dates or set()
    normalized_files = [dict(row) for row in files if isinstance(row, dict)]
    successful = [row for row in normalized_files if row.get("classification") != "failed"]
    changed = [
        row
        for row in normalized_files
        if row.get("classification") in {"new", "updated", "new_updated"}
    ]
    failed = [row for row in normalized_files if row.get("classification") == "failed"]
    return {
        "ok": not failed,
        "activeListId": active_list_id,
        "sourceFolder": str(source_folder),
        "dateFrom": date_from,
        "dateTo": date_to,
        "totalFolderFiles": sum(1 for path in source_folder.iterdir() if path.is_file())
        if source_folder.is_dir()
        else 0,
        "candidateFiles": len(normalized_files),
        "checkedFiles": len(normalized_files),
        "newFileCount": sum(
            1 for row in normalized_files if row.get("classification") in {"new", "new_updated"}
        ),
        "updatedFileCount": sum(
            1 for row in normalized_files if row.get("classification") in {"updated", "new_updated"}
        ),
        "noChangeFileCount": sum(
            1 for row in normalized_files if row.get("classification") == "no_changes"
        ),
        "failedFileCount": len(failed),
        "createdCount": sum(int_value(row.get("createdCount")) for row in changed),
        "updatedCount": sum(int_value(row.get("updatedCount")) for row in changed),
        "reactivatedCount": sum(int_value(row.get("reactivatedCount")) for row in changed),
        "newPieceQty": sum(int_value(row.get("newPieceQty")) for row in changed),
        "updatedPieceQty": sum(int_value(row.get("updatedPieceQty")) for row in changed),
        "addedPieceQty": sum(int_value(row.get("addedPieceQty")) for row in changed),
        "changedPieceQty": sum(int_value(row.get("changedPieceQty")) for row in changed),
        "removedLineCount": sum(int_value(row.get("removedLineCount")) for row in changed),
        "removedPieceQty": sum(int_value(row.get("removedPieceQty")) for row in changed),
        "duplicateManualLineCount": sum(
            int_value(row.get("duplicateManualLineCount")) for row in changed
        ),
        "duplicateManualPieceQty": sum(
            int_value(row.get("duplicateManualPieceQty")) for row in changed
        ),
        "importedDates": sorted(
            {str(row.get("deliveryDate") or "") for row in successful if row.get("deliveryDate")}
        ),
        "changedDates": sorted(
            {str(row.get("deliveryDate") or "") for row in changed if row.get("deliveryDate")}
        ),
        "failedDates": sorted(
            {str(row.get("deliveryDate") or "") for row in failed if row.get("deliveryDate")}
        ),
        "recoveredFileCount": len(recovered_dates),
        "recoveredDates": sorted(recovered_dates),
        "files": normalized_files,
    }


def write_result(path_text: str, payload: dict[str, Any]) -> None:
    """Atomically write the normalized result when the runner requested a file."""
    if not path_text:
        return
    path = Path(path_text).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def current_list_ids(store: Any) -> set[str]:
    """Return current scanner delivery-list ids through the maintained store API."""
    getter = getattr(store, "get_delivery_lists", None)
    if not callable(getter):
        return set()
    rows = getter() or []
    result: set[str] = set()
    for row in rows:
        if isinstance(row, dict):
            value = row.get("id")
        else:
            try:
                value = row["id"]
            except (KeyError, TypeError, IndexError):
                value = ""
        clean = str(value or "").strip()
        if clean:
            result.add(clean)
    return result


def normalized_source_tuple(values: Any) -> tuple[Any, ...]:
    """Return the source-owned business fields used by import reconciliation."""
    def value(name: str, default: Any = "") -> Any:
        if isinstance(values, dict):
            return values.get(name, default)
        try:
            return values[name]
        except (KeyError, TypeError, IndexError):
            return default

    return (
        str(value("order_no") or "").strip(),
        str(value("item_no") or "").strip().zfill(3),
        int_value(value("qty", 0)),
        str(value("dimensions") or "").strip(),
        str(value("customer") or "").strip(),
        str(value("route") or "").strip(),
        str(value("source_route") or "").strip(),
        str(value("job") or "").strip(),
        str(value("product") or "").strip(),
        str(value("queue_state") or "").strip(),
    )


def scanner_stage_drift(
    store: Any,
    delivery_date: str,
    expected_definitions: list[Any],
    allow_source_removals: bool = True,
    verified_excluded_order_items: set[tuple[str, str]] | None = None,
) -> tuple[bool, list[str]]:
    """Compare workbook source rows with active source-owned scanner rows.

    Manual-only rows remain excluded when they are unique operator-owned work.
    A manual row that duplicates an incoming A+W order/item is drift and must be
    reconciled away. The source comparison is a multiset so duplicate business
    rows remain detectable.
    """
    verified_excluded_order_items = verified_excluded_order_items or set()
    expected_by_list: dict[str, list[tuple[Any, ...]]] = {}
    expected_order_items_by_list: dict[str, set[tuple[str, str]]] = {}
    for definition in expected_definitions:
        list_id = str(definition[0]).strip()
        items = list(definition[4] or [])
        normalized: list[tuple[Any, ...]] = []
        order_items: set[tuple[str, str]] = set()
        for index, item in enumerate(items, start=1):
            cloned = store.clone_item_for_list(item, list_id, index)
            normalized_row = normalized_source_tuple(cloned)
            normalized.append(normalized_row)
            order_items.add((str(normalized_row[0]), str(normalized_row[1])))
        expected_by_list[list_id] = sorted(normalized)
        expected_order_items_by_list[list_id] = order_items

    expected_ids = set(expected_by_list)
    mismatched: set[str] = set()
    with store.connect() as connection:
        active_rows = connection.execute(
            """
            SELECT id
            FROM delivery_lists
            WHERE delivery_date = ? AND status = 'active'
            """,
            (delivery_date,),
        ).fetchall()
        active_ids = {
            str(row["id"] if not isinstance(row, dict) else row.get("id") or "").strip()
            for row in active_rows
        }

        for list_id, expected_rows in expected_by_list.items():
            if list_id not in active_ids:
                mismatched.add(list_id)
                continue
            current_rows = connection.execute(
                """
                SELECT order_no, item_no, qty, dimensions, customer, route,
                       source_route, job, product, queue_state,
                       COALESCE(manual_only, 0) AS manual_only,
                       COALESCE(manual_source, '') AS manual_source,
                       COALESCE(protect_from_aw_import, 0) AS protect_from_aw_import
                FROM line_items
                WHERE list_id = ?
                  AND COALESCE(is_deleted, 0) = 0
                """,
                (list_id,),
            ).fetchall()
            source_rows: list[tuple[Any, ...]] = []
            duplicate_manual_found = False
            expected_order_items = expected_order_items_by_list.get(list_id, set())
            for row in current_rows:
                normalized_row = normalized_source_tuple(row)
                is_manual = bool(int(row["manual_only"] or 0)) or bool(str(row["manual_source"] or "").strip())
                protected_manual = is_manual and bool(int(row["protect_from_aw_import"] or 0))
                if is_manual:
                    if not protected_manual and (str(normalized_row[0]), str(normalized_row[1])) in expected_order_items:
                        duplicate_manual_found = True
                    continue
                source_rows.append(normalized_row)
            current = sorted(source_rows)
            verified_exclusion_present = any(
                (str(row[0]), str(row[1])) in verified_excluded_order_items
                for row in source_rows
            )
            if allow_source_removals:
                source_mismatch = current != expected_rows
            else:
                # During the schedule-membership investigation, workbook rows must
                # exist in the scanner but extra source-owned rows are preserved.
                # This still detects missing/additional workbook rows and changed
                # quantities/details without repeatedly trying to retire uncertain
                # rows that disappeared from the raw delivery-date query.
                current_counts = Counter(current)
                expected_counts = Counter(expected_rows)
                source_mismatch = any(
                    current_counts[row] < expected_count
                    for row, expected_count in expected_counts.items()
                )
            if source_mismatch or duplicate_manual_found or verified_exclusion_present:
                mismatched.add(list_id)

        # Optional/custom route stages that disappeared from A+W are drift only
        # when source removals are authoritative. While removals are paused, only
        # an exact Crystal-verified exclusion may force cleanup of an extra stage.
        for list_id in active_ids.difference(expected_ids):
            source_rows = connection.execute(
                """
                SELECT order_no, item_no
                FROM line_items
                WHERE list_id = ?
                  AND COALESCE(is_deleted, 0) = 0
                  AND COALESCE(manual_only, 0) = 0
                  AND COALESCE(manual_source, '') = ''
                """,
                (list_id,),
            ).fetchall()
            if allow_source_removals and source_rows:
                mismatched.add(list_id)
                continue
            if any(
                (str(row["order_no"] or ""), str(row["item_no"] or "").zfill(3))
                in verified_excluded_order_items
                for row in source_rows
            ):
                mismatched.add(list_id)

    return bool(mismatched), sorted(mismatched)


def active_list_summary_map(store: Any) -> dict[str, dict[str, Any]]:
    """Return live active-stage totals and retained preview counters by list ID.

    Automation history is an audit record, not the source of truth for current
    quantities. Reading the maintained list catalog after each reconciliation
    keeps No Changes results, management totals, and manual-row diagnostics tied
    to the same active rows that the Scan page receives.
    """
    getter = getattr(store, "get_delivery_lists", None)
    if not callable(getter):
        return {}
    try:
        rows = list(getter() or [])
    except TypeError:
        rows = list(getter(None) or [])
    except Exception:
        return {}
    return {
        str(row.get("id") or "").strip(): dict(row)
        for row in rows
        if isinstance(row, dict) and str(row.get("id") or "").strip()
    }


def active_stage_summaries(
    store: Any,
    expected_definitions: list[Any],
) -> list[dict[str, Any]]:
    """Build zero-change stage rows from current scanner catalog totals."""
    active_by_id = active_list_summary_map(store)
    summaries: list[dict[str, Any]] = []
    for definition in expected_definitions:
        if not definition:
            continue
        list_id = str(definition[0] or "").strip()
        if not list_id:
            continue
        live = active_by_id.get(list_id, {})
        latest_preview_count = (
            int_value(live.get("newItemCount"))
            + int_value(live.get("updatedItemCount"))
            + int_value(live.get("removedItemCount"))
        )
        summaries.append(
            {
                "listId": list_id,
                "label": str(definition[1] or live.get("label") or ""),
                "stage": str(definition[2] or live.get("stage") or ""),
                "stageProfile": str(definition[3] or live.get("scanner") or ""),
                "scanner": str(definition[3] or live.get("scanner") or ""),
                "totalQty": int_value(live.get("totalQty")),
                "itemCount": int_value(live.get("itemCount")),
                "sourceTotalQty": int_value(live.get("sourceTotalQty")),
                "manualPieceQty": int_value(live.get("manualPieceQty")),
                "manualLineCount": int_value(live.get("manualLineCount")),
                "protectedManualPieceQty": int_value(live.get("protectedManualPieceQty")),
                "protectedManualLineCount": int_value(live.get("protectedManualLineCount")),
                "latestPreviewCount": latest_preview_count,
                "latestPreviewNewCount": int_value(live.get("newItemCount")),
                "latestPreviewUpdatedCount": int_value(live.get("updatedItemCount")),
                "latestPreviewRemovedCount": int_value(live.get("removedItemCount")),
                "latestPreviewRemovedPieceQty": int_value(live.get("removedPieceQty")),
                "latestPreviewAt": str(live.get("latestUpdateAt") or ""),
                "changedLineCount": 0,
                "changedPieceQty": 0,
                "addedPieceQty": 0,
                "removedLineCount": 0,
                "removedPieceQty": 0,
                "created": False,
                "reactivated": False,
            }
        )
    return summaries


def merge_live_stage_totals(
    store: Any,
    stage_summaries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Attach current active/manual quantities to changed import summaries."""
    active_by_id = active_list_summary_map(store)
    merged: list[dict[str, Any]] = []
    for raw_summary in stage_summaries:
        summary = dict(raw_summary)
        live = active_by_id.get(str(summary.get("listId") or ""), {})
        if live:
            summary.update(
                {
                    "totalQty": int_value(live.get("totalQty")),
                    "itemCount": int_value(live.get("itemCount")),
                    "sourceTotalQty": int_value(live.get("sourceTotalQty")),
                    "manualPieceQty": int_value(live.get("manualPieceQty")),
                    "manualLineCount": int_value(live.get("manualLineCount")),
                    "protectedManualPieceQty": int_value(live.get("protectedManualPieceQty")),
                    "protectedManualLineCount": int_value(live.get("protectedManualLineCount")),
                    "latestPreviewCount": (
                        int_value(live.get("newItemCount"))
                        + int_value(live.get("updatedItemCount"))
                        + int_value(live.get("removedItemCount"))
                    ),
                    "latestPreviewNewCount": int_value(live.get("newItemCount")),
                    "latestPreviewUpdatedCount": int_value(live.get("updatedItemCount")),
                    "latestPreviewRemovedCount": int_value(live.get("removedItemCount")),
                    "latestPreviewRemovedPieceQty": int_value(live.get("removedPieceQty")),
                    "latestPreviewAt": str(live.get("latestUpdateAt") or ""),
                }
            )
        merged.append(summary)
    return merged


def routed_payload_for_stage_expectations(store: Any, payload: dict[str, Any]) -> dict[str, Any]:
    """Apply the scanner's customer-route rules before calculating stage IDs.

    The maintained importer performs this transformation inside
    ``import_delivery_list``. Selective SQL verification must use the same
    routed payload or an all-CPU/DTC/Greenville date can incorrectly appear to
    be missing the default Indian Trail stage after a successful import.
    """
    resolver = getattr(store, "apply_customer_route_rules_to_payload", None)
    if not callable(resolver):
        return payload
    routed = resolver(payload)
    if not isinstance(routed, dict):
        raise TypeError("Scanner customer-route resolution returned an invalid payload.")
    return routed


def delivery_workbooks_by_date(
    folder: Path,
    target_dates: set[str],
    date_reader: Any,
    prefer_canonical: bool = False,
) -> dict[str, Path]:
    """Locate one deterministic authoritative workbook for each requested date.

    A manually copied workbook can sit beside the canonical SQL-generated file.
    Importing the whole folder would process both and let filename order decide
    the final scanner state. Select the newest source for each delivery date;
    the canonical ``Delivery List ...`` filename wins only when timestamps tie.
    """
    supported = {".xlsx", ".xlsm", ".csv", ".json"}
    matches: dict[str, tuple[tuple[float, int, str], Path]] = {}
    if not folder.is_dir():
        return {}

    for path in sorted(folder.iterdir(), key=lambda item: item.name.lower()):
        if not path.is_file() or path.suffix.lower() not in supported:
            continue
        try:
            delivery_date = str(date_reader(path) or "").strip()
        except Exception:
            delivery_date = delivery_date_from_name(path.name)
        if delivery_date not in target_dates:
            continue
        try:
            modified_at = float(path.stat().st_mtime)
        except OSError:
            modified_at = 0.0
        canonical_name = 1 if re.match(r"^delivery\s+list\b", path.stem, flags=re.IGNORECASE) else 0
        score = (canonical_name, modified_at, path.name.lower()) if prefer_canonical else (modified_at, canonical_name, path.name.lower())
        current = matches.get(delivery_date)
        if current is None or score > current[0]:
            matches[delivery_date] = (score, path)

    return {delivery_date: record[1] for delivery_date, record in matches.items()}


def import_selected_workbook(
    store: Any,
    path: Path,
    payload: dict[str, Any],
    user: str,
    import_kind: str,
    source_hash_reader: Any,
    allow_source_removals: bool = True,
    verified_excluded_order_items: list[dict[str, Any]] | None = None,
    run_id: str = "",
    run_started_at: str = "",
) -> dict[str, Any]:
    """Import exactly one selected workbook through maintained store rules."""
    preview = store.preview_import(payload)
    if not bool(preview.get("valid")):
        errors = [str(value) for value in (preview.get("errors") or []) if str(value).strip()]
        raise ValueError("; ".join(errors) or f"{path.name} did not pass import validation.")

    result = store.import_delivery_list(
        {
            "payload": payload,
            "fileName": path.name,
            "sourcePath": str(path.resolve()),
            "sourceHash": str(source_hash_reader(path) or ""),
            "importKind": import_kind,
            "allowSourceRemovals": bool(allow_source_removals),
            "verifiedExcludedOrderItems": list(verified_excluded_order_items or []),
            "runId": str(run_id or ""),
            "runStartedAt": str(run_started_at or ""),
            "user": user,
        }
    )
    changed_list_ids = [
        str(value)
        for value in (result.get("changedListIds") or result.get("listIds") or [])
        if str(value).strip()
    ]
    stage_summaries = merge_live_stage_totals(
        store,
        [
            dict(value)
            for value in (result.get("stageSummaries") or [])
            if isinstance(value, dict)
        ],
    )
    duplicate_manual_line_count = sum(
        int_value(value.get("duplicateManualLineCount")) for value in stage_summaries
    )
    duplicate_manual_piece_qty = sum(
        int_value(value.get("duplicateManualPieceQty")) for value in stage_summaries
    )
    return file_result(
        {
            "fileName": path.name,
            "deliveryDate": str(payload.get("deliveryDate") or ""),
            "rowCount": int_value(preview.get("rowCount")),
            "totalQty": int_value(preview.get("totalQty")),
            "createdCount": int_value(result.get("createdCount")),
            "updatedCount": int_value(result.get("updatedCount")),
            "reactivatedCount": int_value(result.get("reactivatedCount")),
            "newPieceQty": int_value(result.get("newPieceQty")),
            "updatedPieceQty": int_value(result.get("updatedPieceQty")),
            "addedPieceQty": int_value(result.get("addedPieceQty")),
            "changedPieceQty": int_value(result.get("changedPieceQty")),
            "removedLineCount": int_value(result.get("removedLineCount")),
            "removedPieceQty": int_value(result.get("removedPieceQty")),
            "duplicateManualLineCount": duplicate_manual_line_count,
            "duplicateManualPieceQty": duplicate_manual_piece_qty,
            "changedListIds": changed_list_ids,
            "reactivatedListIds": result.get("reactivatedListIds") or [],
            "stageSummaries": stage_summaries,
        },
        "updated",
    )


def read_sync_request(path_text: str) -> dict[str, Any]:
    """Read and validate the optional targeted SQL synchronization request."""
    if not path_text:
        return {}
    path = Path(path_text).expanduser()
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("SQL synchronization request must be a JSON object")
    return payload


def selective_sql_sync(
    store: Any,
    folder: Path,
    target_dates: list[str],
    force_import_dates: set[str],
    user: str,
    date_reader: Any,
    payload_loader: Any,
    list_builder: Any,
    source_hash_reader: Any,
    allow_source_removals: bool = True,
    verified_excluded_order_items: list[dict[str, Any]] | None = None,
    run_id: str = "",
    run_started_at: str = "",
) -> dict[str, Any]:
    """Audit unchanged dates and import only scanner dates that have drifted.

    A byte-identical workbook is skipped only when all expected active stages and
    source-owned rows match the scanner. This catches scanner-only additions,
    quantity/detail edits, entire missing stages, and A+W removals without writing
    redundant import records for genuinely synchronized dates.
    """
    clean_dates = sorted({str(value or "").strip() for value in target_dates if str(value or "").strip()})
    if not clean_dates:
        return summary_from_files([], folder, "", "")

    target_set = set(clean_dates)
    verified_excluded_order_items = verified_excluded_order_items or []
    workbooks = delivery_workbooks_by_date(
        folder,
        target_set,
        date_reader,
        prefer_canonical=True,
    )
    existing_ids = current_list_ids(store)
    files: list[dict[str, Any]] = []
    recovered_dates: set[str] = set()
    active_list_id = ""

    for delivery_date in clean_dates:
        path = workbooks.get(delivery_date)
        if path is None:
            files.append(
                file_result(
                    {
                        "fileName": f"Delivery List {delivery_date}.xlsx",
                        "deliveryDate": delivery_date,
                        "errors": ["The expected generated workbook was not found in the Temp Delivery Lists folder."],
                    },
                    "failed",
                )
            )
            continue

        try:
            payload = payload_loader(path)
            routed_payload = routed_payload_for_stage_expectations(store, payload)
            expected_definitions = list_builder(routed_payload)
            expected_ids = {
                str(row[0]).strip()
                for row in expected_definitions
                if row and str(row[0]).strip()
            }
            missing_before = expected_ids.difference(existing_ids)
            date_verified_entries = [
                dict(entry)
                for entry in verified_excluded_order_items
                if isinstance(entry, dict)
                and str(entry.get("deliveryDate") or "").strip() == delivery_date
            ]
            date_verified_keys = {
                (
                    str(entry.get("orderNumber") or "").strip(),
                    str(entry.get("itemNumber") or "").strip().zfill(3),
                )
                for entry in date_verified_entries
                if str(entry.get("orderNumber") or "").strip()
                and str(entry.get("itemNumber") or "").strip()
            }
            source_data_drift, drift_list_ids = scanner_stage_drift(
                store,
                delivery_date,
                expected_definitions,
                allow_source_removals=allow_source_removals,
                verified_excluded_order_items=date_verified_keys,
            )
            manually_forced = delivery_date in force_import_dates
            must_import = manually_forced or bool(missing_before) or source_data_drift

            if must_import:
                imported_file = run_with_database_retry(
                    lambda: import_selected_workbook(
                        store,
                        path,
                        payload,
                        user,
                        "sql_authoritative_sync",
                        source_hash_reader,
                        allow_source_removals=allow_source_removals,
                        verified_excluded_order_items=date_verified_entries,
                        run_id=run_id,
                        run_started_at=run_started_at,
                    ),
                    f"importing delivery date {delivery_date}",
                )
                date_files = [imported_file]
                existing_ids = current_list_ids(store)
                missing_after = expected_ids.difference(existing_ids)
                if missing_after:
                    raise RuntimeError(
                        f"Scanner import did not recreate {len(missing_after)} expected stage list(s) "
                        f"for {delivery_date}: {', '.join(sorted(missing_after))}"
                    )

                # A successful stage creation is not enough: verify every A+W
                # source row expected for this date is now represented in the
                # scanner. This prevents a delta-only/partial import from being
                # reported as successful while Print / Export and the Scan page
                # expose only the newly changed orders. Extra retained source rows
                # remain allowed while unverified removals are paused.
                post_import_drift, post_import_drift_ids = scanner_stage_drift(
                    store,
                    delivery_date,
                    expected_definitions,
                    allow_source_removals=allow_source_removals,
                    verified_excluded_order_items=date_verified_keys,
                )
                if post_import_drift:
                    raise RuntimeError(
                        "Scanner reconciliation completed but source-row coverage is still incomplete or mismatched "
                        f"for {delivery_date}: {', '.join(post_import_drift_ids)}. "
                        "The run is marked failed so a partial delivery list cannot be silently published to operators."
                    )

                imported_file["sourceCoverageVerified"] = True
                files.extend(date_files)
                if missing_before:
                    recovered_dates.add(delivery_date)
                for row in date_files:
                    if row.get("classification") == "failed":
                        continue
                    reasons: list[str] = []
                    if manually_forced:
                        reasons.append("Manual update forced authoritative A+W reconciliation.")
                    if missing_before:
                        reasons.append("Recovered missing scanner stage list(s).")
                    if source_data_drift:
                        reasons.append(
                            "Reconciled scanner source-row drift in: "
                            + ", ".join(drift_list_ids)
                            + "."
                        )
                    if not allow_source_removals:
                        reasons.append(
                            "Unverified source-row removals remained paused; only exact Crystal-verified exclusions could be retired."
                        )
                    if reasons:
                        row["reason"] = " ".join(reasons)
            else:
                items = [item for item in (payload.get("items") or []) if isinstance(item, dict)]
                live_stage_summaries = active_stage_summaries(store, expected_definitions)
                files.append(
                    file_result(
                        {
                            "fileName": path.name,
                            "deliveryDate": delivery_date,
                            "rowCount": len(items),
                            "totalQty": sum(int_value(item.get("qty")) for item in items),
                            "listIds": [
                                str(summary.get("listId") or "")
                                for summary in live_stage_summaries
                                if str(summary.get("listId") or "")
                            ],
                            "stageSummaries": live_stage_summaries,
                            "reason": (
                                "A+W data, generated stages, and all active source-owned scanner rows match."
                            ),
                        },
                        "skipped",
                    )
                )
        except Exception as exc:
            files.append(
                file_result(
                    {
                        "fileName": path.name,
                        "deliveryDate": delivery_date,
                        "errors": [str(exc)],
                    },
                    "failed",
                )
            )

    return summary_from_files(
        files,
        folder,
        clean_dates[0],
        clean_dates[-1],
        active_list_id=active_list_id,
        recovered_dates=recovered_dates,
    )


def main() -> int:
    """Load the maintained scanner configuration/store and run the requested import."""
    args = parse_args()
    project_root = Path(args.project_root).expanduser().resolve()
    if not project_root.is_dir():
        raise FileNotFoundError(f"Project root not found: {project_root}")

    sys.path.insert(0, str(project_root))

    from backend.config import load_config
    from delivery_import_safety import install_safe_delivery_import
    import backend.store as backend_store_module
    from backend.store import (
        build_delivery_lists,
        create_store,
        delivery_date_from_source_header,
        load_delivery_source_payload,
        source_file_hash,
    )

    config = load_config(project_root)
    store = create_store(config)
    if args.initialize_store == "true":
        store.initialize()
    install_safe_delivery_import(store)
    schema_repair_applied = bool(
        getattr(store, "_dls_notice_schema_repaired", False)
        or getattr(store, "_dls_manual_protection_schema_repaired", False)
    )

    folder = Path(args.folder).expanduser()
    sync_request = read_sync_request(args.sync_request_path)
    if sync_request:
        target_dates = [str(value) for value in (sync_request.get("targetDates") or [])]
        force_dates = {
            str(value).strip()
            for value in (sync_request.get("forceImportDates") or [])
            if str(value).strip()
        }
        allow_source_removals = bool(sync_request.get("allowSourceRemovals", True))
        verified_excluded_order_items = [
            dict(value)
            for value in (sync_request.get("verifiedExcludedOrderItems") or [])
            if isinstance(value, dict)
        ]
        superseded_order_candidates = [
            dict(value)
            for value in (sync_request.get("supersededOrderCandidates") or [])
            if isinstance(value, dict)
        ]
        summary = selective_sql_sync(
            store=store,
            folder=folder,
            target_dates=target_dates,
            force_import_dates=force_dates,
            user=args.user,
            date_reader=delivery_date_from_source_header,
            payload_loader=load_delivery_source_payload,
            list_builder=build_delivery_lists,
            source_hash_reader=source_file_hash,
            allow_source_removals=allow_source_removals,
            verified_excluded_order_items=verified_excluded_order_items,
            run_id=args.run_id,
            run_started_at=args.run_started_at,
        )
        try:
            sync_candidate_reviews = getattr(store, "sync_superseded_order_candidates", None)
            if not callable(sync_candidate_reviews):
                loaded_store_path = str(getattr(backend_store_module, "__file__", "unknown backend/store.py"))
                raise RuntimeError(
                    "The installed backend/store.py does not provide "
                    "sync_superseded_order_candidates. The automation ProjectRoot may point at an older "
                    "scanner copy. Restart the v0.257 web app so it can repair ProjectRoot, then rerun the date. "
                    f"Loaded store module: {loaded_store_path}"
                )
            candidate_sync = run_with_database_retry(
                lambda: sync_candidate_reviews(
                    superseded_order_candidates,
                    verified_excluded_order_items,
                    args.user,
                ),
                "saving superseded-order review candidates",
            )
            summary["supersededOrderReview"] = candidate_sync
            summary["pendingSupersededOrderReviews"] = int_value(
                candidate_sync.get("pendingSupersededOrderReviews")
            )
        except Exception as exc:
            # Candidate review is advisory. A queue-persistence failure must never
            # roll back or hide otherwise successful delivery-list imports. Preserve
            # the full diagnostic in the result so the runner can report it clearly.
            warning = f"{type(exc).__name__}: {exc}"
            candidate_sync = {
                "ok": False,
                "candidateCount": len(superseded_order_candidates),
                "insertedCount": 0,
                "updatedCount": 0,
                "resetToPendingCount": 0,
                "systemApprovedCount": 0,
                "pendingSupersededOrderReviews": 0,
                "errors": [warning],
                "traceback": traceback.format_exc(),
            }
            summary["supersededOrderReview"] = candidate_sync
            summary["pendingSupersededOrderReviews"] = 0
            summary["supersededOrderReviewWarning"] = warning
    else:
        start_date = date.fromisoformat(args.date_from) if args.date_from else date.today() - timedelta(days=7)
        end_date = date.fromisoformat(args.date_to) if args.date_to else start_date
        target_dates: list[str] = []
        cursor = start_date
        while cursor <= end_date:
            target_dates.append(cursor.isoformat())
            cursor += timedelta(days=1)

        selected = delivery_workbooks_by_date(
            folder,
            set(target_dates),
            delivery_date_from_source_header,
        )
        files: list[dict[str, Any]] = []
        active_list_id = ""
        for delivery_date in target_dates:
            selected_path = selected.get(delivery_date)
            if selected_path is None:
                continue
            try:
                selected_payload = load_delivery_source_payload(selected_path)
                imported_file = run_with_database_retry(
                    lambda path=selected_path, payload=selected_payload: import_selected_workbook(
                        store,
                        path,
                        payload,
                        args.user,
                        "folder_authoritative_sync",
                        source_file_hash,
                        run_id=args.run_id,
                        run_started_at=args.run_started_at,
                    ),
                    f"importing delivery date {delivery_date}",
                )
                files.append(imported_file)
            except Exception as exc:
                files.append(
                    file_result(
                        {
                            "fileName": selected_path.name,
                            "deliveryDate": delivery_date,
                            "errors": [str(exc)],
                        },
                        "failed",
                    )
                )
        summary = summary_from_files(
            files,
            folder,
            args.date_from,
            args.date_to,
            active_list_id=active_list_id,
        )
        summary.setdefault("recoveredFileCount", 0)
        summary.setdefault("recoveredDates", [])

    # Persist one stable run identity on every per-file result, including
    # unchanged and failed files. The notification/browser can then group the
    # complete run without guessing from delivery dates or timestamps.
    summary["runId"] = str(args.run_id or "")
    summary["runStartedAt"] = str(args.run_started_at or "")
    for row in summary.get("files") or []:
        if not isinstance(row, dict):
            continue
        row.setdefault("runId", str(args.run_id or ""))
        row.setdefault("runStartedAt", str(args.run_started_at or ""))

    summary["schemaRepairApplied"] = schema_repair_applied
    write_result(args.result_path, summary)

    failed_details = []
    for row in summary.get("files") or []:
        if not isinstance(row, dict) or row.get("classification") != "failed":
            continue
        errors = [str(value) for value in (row.get("errors") or []) if str(value).strip()]
        failed_details.append({
            "deliveryDate": str(row.get("deliveryDate") or ""),
            "fileName": str(row.get("fileName") or ""),
            "error": errors[0] if errors else str(row.get("reason") or "No detailed error was returned."),
        })

    console_summary = {
        "ok": summary["ok"],
        "checkedFiles": summary["checkedFiles"],
        "newFileCount": summary["newFileCount"],
        "updatedFileCount": summary["updatedFileCount"],
        "removedLineCount": summary.get("removedLineCount", 0),
        "removedPieceQty": summary.get("removedPieceQty", 0),
        "duplicateManualLineCount": summary.get("duplicateManualLineCount", 0),
        "duplicateManualPieceQty": summary.get("duplicateManualPieceQty", 0),
        "noChangeFileCount": summary["noChangeFileCount"],
        "failedFileCount": summary["failedFileCount"],
        "failedFiles": failed_details,
        "recoveredFileCount": summary.get("recoveredFileCount", 0),
        "recoveredDates": summary.get("recoveredDates", []),
        "importedDates": summary["importedDates"],
        "failedDates": summary["failedDates"],
        "schemaRepairApplied": schema_repair_applied,
        "supersededOrderReviewWarning": str(summary.get("supersededOrderReviewWarning") or ""),
        "resultPath": args.result_path,
    }
    print(json.dumps(console_summary, separators=(",", ":"), sort_keys=True))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
