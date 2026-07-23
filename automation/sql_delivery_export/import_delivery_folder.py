#!/usr/bin/env python3
"""Import SQL-generated delivery workbooks through the maintained scanner store.

The wrapper deliberately reuses scanner_config.py and delivery_store.py. It
never reimplements route, stage, scan-preservation, rack, bay, or audit rules.
For SQL synchronization runs it also performs a read-only stage-list preflight:
unchanged workbooks are reported without reimporting, while a deleted scanner
list causes that exact delivery date to be imported through the maintained
folder-import business workflow.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time
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
    changed_list_ids = [
        str(value)
        for value in (row.get("listIds") or row.get("changedListIds") or [])
        if value
    ]

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
    elif updated_count or changed_list_ids:
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
        "addedPieceQty": int_value(row.get("addedPieceQty")),
        "changedPieceQty": int_value(row.get("changedPieceQty")),
        "removedLineCount": int_value(row.get("removedLineCount")),
        "removedPieceQty": int_value(row.get("removedPieceQty")),
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
        "ok": bool(result.get("ok", not failed_rows)),
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
        "addedPieceQty": sum(row["addedPieceQty"] for row in imported_rows + updated_rows),
        "changedPieceQty": sum(row["changedPieceQty"] for row in imported_rows + updated_rows),
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
        "addedPieceQty": sum(int_value(row.get("addedPieceQty")) for row in changed),
        "changedPieceQty": sum(int_value(row.get("changedPieceQty")) for row in changed),
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


def delivery_workbooks_by_date(
    folder: Path,
    target_dates: set[str],
    date_reader: Any,
) -> dict[str, Path]:
    """Locate one supported delivery workbook for each requested source date."""
    supported = {".xlsx", ".xlsm", ".csv", ".json"}
    matches: dict[str, Path] = {}
    if not folder.is_dir():
        return matches
    for path in sorted(folder.iterdir(), key=lambda item: item.name.lower()):
        if not path.is_file() or path.suffix.lower() not in supported:
            continue
        try:
            delivery_date = str(date_reader(path) or "").strip()
        except Exception:
            delivery_date = delivery_date_from_name(path.name)
        if delivery_date in target_dates:
            matches[delivery_date] = path
    return matches


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
) -> dict[str, Any]:
    """Audit unchanged dates and import only changed or missing scanner lists.

    This avoids repeatedly writing scanner import rows or queuing customer
    manifests for byte-identical workbooks. When an expected stage list is
    missing, the exact date is sent through ``import_delivery_folder`` so the
    scanner's maintained business workflow recreates it.
    """
    clean_dates = sorted({str(value or "").strip() for value in target_dates if str(value or "").strip()})
    if not clean_dates:
        return summary_from_files([], folder, "", "")

    target_set = set(clean_dates)
    workbooks = delivery_workbooks_by_date(folder, target_set, date_reader)
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
            expected_definitions = list_builder(payload)
            expected_ids = {
                str(row[0]).strip()
                for row in expected_definitions
                if row and str(row[0]).strip()
            }
            missing_before = expected_ids.difference(existing_ids)
            must_import = delivery_date in force_import_dates or bool(missing_before)

            if must_import:
                raw_result = run_with_database_retry(
                    lambda: store.import_delivery_folder(
                        {
                            "sourceFolder": str(folder),
                            "dateFrom": delivery_date,
                            "dateTo": delivery_date,
                            "user": user,
                        }
                    ),
                    f"importing delivery date {delivery_date}",
                )
                normalized = normalize_result(raw_result or {}, delivery_date, delivery_date)
                date_files = [
                    row
                    for row in normalized.get("files") or []
                    if str(row.get("deliveryDate") or "") == delivery_date
                ]
                if not date_files:
                    raise RuntimeError(
                        f"The maintained scanner importer returned no result for {delivery_date}."
                    )
                files.extend(date_files)
                active_list_id = str(normalized.get("activeListId") or active_list_id)
                existing_ids = current_list_ids(store)
                missing_after = expected_ids.difference(existing_ids)
                if missing_after:
                    raise RuntimeError(
                        f"Scanner import did not recreate {len(missing_after)} expected stage list(s) "
                        f"for {delivery_date}: {', '.join(sorted(missing_after))}"
                    )
                if missing_before:
                    recovered_dates.add(delivery_date)
                    for row in date_files:
                        if row.get("classification") != "failed":
                            row["reason"] = (
                                "Recovered missing scanner stage list(s) through the maintained import workflow."
                            )
            else:
                items = [item for item in (payload.get("items") or []) if isinstance(item, dict)]
                files.append(
                    file_result(
                        {
                            "fileName": path.name,
                            "deliveryDate": delivery_date,
                            "rowCount": len(items),
                            "totalQty": sum(int_value(item.get("qty")) for item in items),
                            "reason": (
                                "A+W data and the published workbook are unchanged; all expected scanner "
                                "stage lists are present."
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

    from scanner_config import load_config
    from delivery_import_safety import install_safe_delivery_import
    from delivery_store import (
        build_delivery_lists,
        create_store,
        delivery_date_from_source_header,
        load_delivery_source_payload,
    )

    config = load_config(project_root)
    store = create_store(config)
    if args.initialize_store == "true":
        store.initialize()
    install_safe_delivery_import(store)

    folder = Path(args.folder).expanduser()
    sync_request = read_sync_request(args.sync_request_path)
    if sync_request:
        target_dates = [str(value) for value in (sync_request.get("targetDates") or [])]
        force_dates = {
            str(value).strip()
            for value in (sync_request.get("forceImportDates") or [])
            if str(value).strip()
        }
        summary = selective_sql_sync(
            store=store,
            folder=folder,
            target_dates=target_dates,
            force_import_dates=force_dates,
            user=args.user,
            date_reader=delivery_date_from_source_header,
            payload_loader=load_delivery_source_payload,
            list_builder=build_delivery_lists,
        )
    else:
        raw_result = run_with_database_retry(
            lambda: store.import_delivery_folder(
                {
                    "sourceFolder": str(folder),
                    "user": args.user,
                    "dateFrom": args.date_from,
                    "dateTo": args.date_to,
                }
            ),
            "importing the Temp Delivery Lists folder",
        )
        summary = normalize_result(raw_result or {}, args.date_from, args.date_to)
        summary.setdefault("recoveredFileCount", 0)
        summary.setdefault("recoveredDates", [])

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
        "noChangeFileCount": summary["noChangeFileCount"],
        "failedFileCount": summary["failedFileCount"],
        "failedFiles": failed_details,
        "recoveredFileCount": summary.get("recoveredFileCount", 0),
        "recoveredDates": summary.get("recoveredDates", []),
        "importedDates": summary["importedDates"],
        "failedDates": summary["failedDates"],
        "resultPath": args.result_path,
    }
    print(json.dumps(console_summary, separators=(",", ":"), sort_keys=True))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
