# File: database/migrations.py
"""Numbered SQLite migrations and verified pre-upgrade backup support."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from typing import Any, Callable

from database.contract import APPLICATION_VERSION, CURRENT_SCHEMA_VERSION
from database.time_utils import (
    normalize_aw_plant_timestamp,
    normalize_utc_timestamp,
    reinterpret_legacy_aw_utc_clock_as_plant,
)


class MigrationError(RuntimeError):
    """Raised when migration history or an upgrade is unsafe."""


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    checksum_material: str
    method_name: str

    @property
    def checksum(self) -> str:
        """Handle checksum for the maintained Delivery List Scanner workflow."""
        value = f"{self.version}\n{self.name}\n{self.checksum_material}".encode("utf-8")
        return hashlib.sha256(value).hexdigest()


MIGRATIONS = (
    Migration(1, "v096_baseline", "Delivery List Scanner v096 canonical SQLite schema", "_migration_001_v096_baseline"),
    Migration(
        2,
        "v097_production_database",
        "UTC audit fields, relational constraints, immutable history, machine scanning tables, query indexes, and atomic FK validation; final-v097-r1",
        "_migration_002_v097_production_database",
    ),
    Migration(
        3,
        "v120_user_line_updates",
        "Per-user current-and-future delivery-list line update notices and explicit review acknowledgements; v120-r1",
        "_migration_003_v120_user_line_updates",
    ),
    Migration(
        4,
        "v135_operations_workflows",
        "Internal reject tracking, manual delivery entries, per-line operational flags, and immutable packing-list print snapshots; v135-r1",
        "_migration_004_v135_operations_workflows",
    ),
    Migration(
        5,
        "v192_action_history_archive",
        "Thirty-day active action-history retention with immutable logical archive storage and timestamp indexes; v192-r1",
        "_migration_005_v192_action_history_archive",
    ),
    Migration(
        6,
        "v230_removed_import_lines",
        "Authoritative A+W removals with snapshot-backed new, updated, and removed delivery-list preview notices; v230-r1",
        "_migration_006_v230_removed_import_lines",
    ),
    Migration(
        7,
        "v233_repair_removed_import_notice_schema",
        "Repair databases whose v230 migration ledger exists without the snapshot-backed removed-line notice columns; v233-r1",
        "_migration_007_v233_repair_removed_import_notice_schema",
    ),
    Migration(
        8,
        "v234_authoritative_import_schema_guard",
        "Revalidate and rebuild snapshot-backed removed-line notices before authoritative automation imports; v234-r1",
        "_migration_008_v234_authoritative_import_schema_guard",
    ),
    Migration(
        9,
        "v236_protected_manual_orders",
        "Explicit per-line and manual-entry protection from authoritative A+W replacement or retirement; v236-r1",
        "_migration_009_v236_protected_manual_orders",
    ),
    Migration(
        10,
        "v245_superseded_order_review",
        "Locally detected A+W superseded-order candidates, explicit admin decisions, exact-key exclusions, and durable evidence snapshots; v245-r1",
        "_migration_010_v245_superseded_order_review",
    ),
    Migration(
        11,
        "v257_superseded_remove_choice",
        "Persist the exact candidate order selected for removal while preserving legacy original-order approvals; v257-r1",
        "_migration_011_v257_superseded_remove_choice",
    ),
    Migration(
        12,
        "v484_aw_reject_sync",
        "Persist raw A+W PROD_BREAKAGE rows by external ROWID and de-duplicate BOM-level source rows into logical A+W reject events; v484-r1",
        "_migration_012_v484_aw_reject_sync",
    ),
    Migration(
        13,
        "v485_internalize_aw_rejects",
        "Mirror A+W breakage into Internal Reject history without replaying floor rollback, add stable reason/location display mappings, and preserve source linkage; v485-r1",
        "_migration_013_v485_internalize_aw_rejects",
    ),
    Migration(
        14,
        "v486_aw_reject_operational_reset",
        "Apply A+W Internal Reject scan/rack/bay rollback exactly once per preserved PROD_BREAKAGE source row and retain the rollback marker across source refreshes; v486-r1",
        "_migration_014_v486_aw_reject_operational_reset",
    ),
    Migration(
        15,
        "v487_reject_reporting_performance",
        "Add index-friendly Internal Reject timeline/statistics access paths after A+W history synchronization; v487-r1",
        "_migration_015_v487_reject_reporting_performance",
    ),
    Migration(
        16,
        "v498_aw_cutting_progress",
        "Persist A+W production batch/optimization generations for reject-aware Cutting progress and label context; v498-r1",
        "_migration_016_v498_aw_cutting_progress",
    ),
    Migration(
        17,
        "v507_runtime_read_indexes",
        "Targeted active Order/Item, catalog heartbeat, scan history, line-update, and A+W Cutting read indexes; v507-r1",
        "_migration_017_v507_runtime_read_indexes",
    ),
    Migration(
        18,
        "v507_normalize_external_timestamps",
        "Normalize legacy SQL Server and A+W timestamps to aware second-precision UTC text without changing event identities; v507-r1",
        "_migration_018_v507_normalize_external_timestamps",
    ),
    Migration(
        19,
        "v516_aw_eastern_timestamp_contract",
        "Interpret offset-free A+W SQL datetime values as America/New_York plant time, repair legacy A+W reject/cutting evidence, and preserve stable event identities; v516-r1",
        "_migration_019_v516_aw_eastern_timestamp_contract",
    ),
)


def validate_migration_registry() -> None:
    """Require one maintained migration definition for every schema version.

    Changed-files deployments can otherwise update ``database.contract`` without
    replacing ``database.migrations``. That leaves the application expecting a
    schema version that the installed migration registry cannot reach. Fail
    before opening a migration transaction and report the exact missing entries.
    """
    defined_versions = [migration.version for migration in MIGRATIONS]
    expected_versions = list(range(1, CURRENT_SCHEMA_VERSION + 1))
    duplicate_versions = sorted(
        {version for version in defined_versions if defined_versions.count(version) > 1}
    )
    missing_versions = sorted(set(expected_versions) - set(defined_versions))
    unexpected_versions = sorted(
        version for version in set(defined_versions) if version > CURRENT_SCHEMA_VERSION
    )
    if duplicate_versions or missing_versions or unexpected_versions:
        raise MigrationError(
            "SQLite migration registry does not match the application contract. "
            f"Expected definitions={expected_versions}; defined={defined_versions}; "
            f"missing={missing_versions}; duplicates={duplicate_versions}; "
            f"unexpected={unexpected_versions}. Reapply the complete maintained "
            "changed-files package before starting the scanner."
        )


def utc_now() -> str:
    """Handle utc now for the maintained Delivery List Scanner workflow."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def migration_by_version(version: int) -> Migration:
    """Handle migration by version for the maintained Delivery List Scanner workflow."""
    for migration in MIGRATIONS:
        if migration.version == version:
            return migration
    raise KeyError(version)


def ensure_migration_table(connection: Any) -> None:
    """Handle ensure migration table for the maintained Delivery List Scanner workflow."""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER NOT NULL PRIMARY KEY,
            name TEXT NOT NULL,
            checksum TEXT NOT NULL,
            applied_at_utc TEXT NOT NULL,
            execution_ms INTEGER NOT NULL DEFAULT 0 CHECK (execution_ms >= 0),
            app_version TEXT NOT NULL DEFAULT ''
        )
        """
    )
    connection.commit()


def installed_migrations(connection: Any) -> dict[int, dict[str, Any]]:
    """Handle installed migrations for the maintained Delivery List Scanner workflow."""
    ensure_migration_table(connection)
    rows = connection.execute(
        "SELECT version, name, checksum, applied_at_utc, execution_ms, app_version FROM schema_migrations ORDER BY version"
    ).fetchall()
    return {
        int(row["version"]): {
            "version": int(row["version"]),
            "name": str(row["name"]),
            "checksum": str(row["checksum"]),
            "applied_at_utc": str(row["applied_at_utc"]),
            "execution_ms": int(row["execution_ms"]),
            "app_version": str(row["app_version"]),
        }
        for row in rows
    }


def validate_installed_checksums(connection: Any) -> None:
    """Handle validate installed checksums for the maintained Delivery List Scanner workflow."""
    installed = installed_migrations(connection)
    for version, row in installed.items():
        try:
            expected = migration_by_version(version)
        except KeyError as exc:
            raise MigrationError(f"Database contains unknown migration version {version}") from exc
        if row["checksum"] != expected.checksum:
            raise MigrationError(
                f"Migration {version:03d} checksum mismatch. The installed schema history must not be edited."
            )


def has_application_tables(connection: Any) -> bool:
    """Handle has application tables for the maintained Delivery List Scanner workflow."""
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'delivery_lists'"
    ).fetchone()
    return bool(row)


def baseline_legacy_v096(connection: Any, owner: Any) -> bool:
    """Handle baseline legacy v096 for the maintained Delivery List Scanner workflow."""
    installed = installed_migrations(connection)
    if installed or not has_application_tables(connection):
        return False
    owner._verify_v096_baseline(connection)
    migration = migration_by_version(1)
    connection.execute(
        "INSERT INTO schema_migrations (version, name, checksum, applied_at_utc, execution_ms, app_version) VALUES (?, ?, ?, ?, 0, ?)",
        (migration.version, migration.name, migration.checksum, utc_now(), "096-baseline"),
    )
    connection.commit()
    return True


def prepare_v096_compatibility_schema(connection: Any, owner: Any, installed: dict[int, dict[str, Any]]) -> None:
    """Complete the canonical v096 schema before the v097 table rebuild.

    Some floor databases were created during development before every v096
    support table and additive column existed. Merely recording the v096
    baseline is not enough for those databases: later startup work expects
    auxiliary tables such as ``system_metadata``, and the v097 rebuild expects
    fields such as ``priority_delivery_date``.

    Re-run the canonical v096 schema method here because it is deliberately
    idempotent: ``CREATE TABLE IF NOT EXISTS`` adds missing support tables, and
    the maintained compatibility helper adds only absent columns. Existing
    rows are not recreated or replaced. This also repairs a database that
    already carries the v096 baseline record but was created before the schema
    was complete.
    """
    if 2 in installed:
        return
    baseline = migration_by_version(1)
    initializer = getattr(owner, baseline.method_name, None)
    if not callable(initializer):
        raise MigrationError(
            "The database requires v096 schema completion, but the current store does not provide it."
        )
    initializer(connection)
    connection.commit()


def _ensure_column(connection: Any, table: str, column: str, definition: str) -> None:
    """Add one compatibility column only when it is absent."""
    columns = {str(row["name"]) for row in connection.execute(f"PRAGMA table_info([{table}])").fetchall()}
    if column not in columns:
        connection.execute(f"ALTER TABLE [{table}] ADD COLUMN [{column}] {definition}")


def _migration_004_v135_operations_workflows(connection: Any) -> None:
    """Add internal rejects, manual orders, packing history, and per-line flags."""
    _ensure_column(connection, "line_items", "manual_only", "INTEGER NOT NULL DEFAULT 0 CHECK (manual_only IN (0, 1))")
    _ensure_column(connection, "line_items", "manual_source", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(connection, "line_items", "internal_reject_count", "INTEGER NOT NULL DEFAULT 0 CHECK (internal_reject_count >= 0)")
    _ensure_column(connection, "line_items", "last_reject_reason", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(connection, "line_items", "last_reject_location", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(connection, "line_items", "last_rejected_at", "TEXT NOT NULL DEFAULT ''")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS reject_reasons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT NOT NULL UNIQUE,
            active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_by TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS reject_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT NOT NULL UNIQUE,
            active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_by TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS reject_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            delivery_date TEXT NOT NULL,
            order_no TEXT NOT NULL,
            item_no TEXT NOT NULL,
            qty INTEGER NOT NULL DEFAULT 1 CHECK (qty > 0),
            customer TEXT NOT NULL DEFAULT '',
            job TEXT NOT NULL DEFAULT '',
            product TEXT NOT NULL DEFAULT '',
            reason_label TEXT NOT NULL,
            location_label TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            rejected_at TEXT NOT NULL,
            rejected_by TEXT NOT NULL DEFAULT '',
            source_list_id TEXT NOT NULL DEFAULT '',
            source_line_item_id TEXT NOT NULL DEFAULT '',
            affected_list_ids_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(affected_list_ids_json)),
            scan_qty_reduced INTEGER NOT NULL DEFAULT 0 CHECK (scan_qty_reduced >= 0)
        );
        CREATE TABLE IF NOT EXISTS packing_list_prints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rack_code TEXT NOT NULL,
            rack_name TEXT NOT NULL DEFAULT '',
            delivery_date TEXT NOT NULL DEFAULT '',
            printed_at TEXT NOT NULL,
            printed_by TEXT NOT NULL DEFAULT '',
            piece_qty INTEGER NOT NULL DEFAULT 0 CHECK (piece_qty >= 0),
            line_count INTEGER NOT NULL DEFAULT 0 CHECK (line_count >= 0),
            snapshot_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(snapshot_json))
        );
        CREATE TABLE IF NOT EXISTS manual_delivery_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            delivery_date TEXT NOT NULL,
            order_no TEXT NOT NULL,
            item_no TEXT NOT NULL,
            qty INTEGER NOT NULL CHECK (qty > 0),
            route TEXT NOT NULL,
            customer TEXT NOT NULL DEFAULT '',
            job TEXT NOT NULL DEFAULT '',
            product TEXT NOT NULL DEFAULT '',
            dimensions TEXT NOT NULL DEFAULT '',
            manual_only INTEGER NOT NULL DEFAULT 0 CHECK (manual_only IN (0, 1)),
            created_by TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            target_list_ids_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(target_list_ids_json))
        );
        CREATE INDEX IF NOT EXISTS idx_reject_events_date_time
            ON reject_events(delivery_date, rejected_at DESC, id DESC);
        CREATE INDEX IF NOT EXISTS idx_reject_events_order_item
            ON reject_events(order_no, item_no, rejected_at DESC);
        CREATE INDEX IF NOT EXISTS idx_packing_list_prints_time
            ON packing_list_prints(printed_at DESC, id DESC);
        CREATE INDEX IF NOT EXISTS idx_manual_delivery_entries_date
            ON manual_delivery_entries(delivery_date, created_at DESC, id DESC);
        """
    )
    created = utc_now()
    reason_defaults = ("Damaged / broken", "Edge chip", "Scratch / surface defect", "Incorrect size", "Other")
    location_defaults = ("Cutting", "Polisher", "Washer", "Tempering", "Wrapper", "Staging", "Rack / transport", "Other")
    for sort_order, label in enumerate(reason_defaults, start=1):
        connection.execute(
            "INSERT OR IGNORE INTO reject_reasons (label, active, sort_order, created_by, created_at, updated_at) VALUES (?, 1, ?, 'system', ?, ?)",
            (label, sort_order, created, created),
        )
    for sort_order, label in enumerate(location_defaults, start=1):
        connection.execute(
            "INSERT OR IGNORE INTO reject_locations (label, active, sort_order, created_by, created_at, updated_at) VALUES (?, 1, ?, 'system', ?, ?)",
            (label, sort_order, created, created),
        )


def _migration_005_v192_action_history_archive(connection: Any) -> None:
    """Add immutable logical archive storage for action history older than 30 days."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS audit_events_archive (
            source_event_id INTEGER PRIMARY KEY,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            action TEXT NOT NULL,
            user_name TEXT NOT NULL DEFAULT '',
            station TEXT NOT NULL DEFAULT '',
            reason TEXT NOT NULL DEFAULT '',
            payload_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(payload_json)),
            created_at TEXT NOT NULL,
            archived_at_utc TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_audit_events_created_time
            ON audit_events(created_at DESC, id DESC);
        CREATE INDEX IF NOT EXISTS idx_audit_events_archive_created_time
            ON audit_events_archive(created_at DESC, source_event_id DESC);
        CREATE TRIGGER IF NOT EXISTS trg_audit_events_archive_immutable_update
            BEFORE UPDATE ON audit_events_archive
            BEGIN SELECT RAISE(ABORT, 'audit_events_archive is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS trg_audit_events_archive_immutable_delete
            BEFORE DELETE ON audit_events_archive
            BEGIN SELECT RAISE(ABORT, 'audit_events_archive is append-only'); END;
        """
    )


def _migration_006_v230_removed_import_lines(connection: Any) -> None:
    """Allow removed-line notices and preserve their display snapshot after deletion."""
    connection.executescript(
        """
        CREATE TABLE line_update_notices_v230 (
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
        );

        INSERT INTO line_update_notices_v230 (
            id, line_item_id, list_id, delivery_date, change_type,
            change_token, source_hash, snapshot_json, created_at
        )
        SELECT id, line_item_id, list_id, delivery_date, change_type,
               change_token, source_hash, '{}', created_at
        FROM line_update_notices;

        CREATE TABLE line_update_receipts_v230 (
            notice_id INTEGER NOT NULL REFERENCES line_update_notices_v230(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            seen_at TEXT NOT NULL,
            PRIMARY KEY (notice_id, user_id)
        );

        INSERT INTO line_update_receipts_v230 (notice_id, user_id, seen_at)
        SELECT notice_id, user_id, seen_at
        FROM line_update_receipts;

        DROP TABLE line_update_receipts;
        DROP TABLE line_update_notices;
        ALTER TABLE line_update_notices_v230 RENAME TO line_update_notices;
        ALTER TABLE line_update_receipts_v230 RENAME TO line_update_receipts;

        CREATE INDEX idx_line_update_notices_list_date
            ON line_update_notices(list_id, delivery_date, created_at DESC, id DESC);
        CREATE INDEX idx_line_update_receipts_user
            ON line_update_receipts(user_id, notice_id);
        """
    )



def _migration_007_v233_repair_removed_import_notice_schema(connection: Any) -> None:
    """Repair an incomplete v230 notice schema without losing review history.

    A small number of deployed databases recorded migration 6 while retaining
    the older v120 ``line_update_notices`` table.  The importer then attempted
    to write ``snapshot_json`` and failed before any A+W reconciliation could
    complete.  Migration 7 deliberately rebuilds the two notice tables from
    their current contents, so it repairs both the missing JSON column and the
    older change-type constraint that rejected ``removed`` notices.
    """
    _ensure_column(
        connection,
        "line_update_notices",
        "snapshot_json",
        "TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(snapshot_json))",
    )

    connection.executescript(
        """
        DROP TABLE IF EXISTS line_update_receipts_v233;
        DROP TABLE IF EXISTS line_update_notices_v233;

        CREATE TABLE line_update_notices_v233 (
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
        );

        INSERT INTO line_update_notices_v233 (
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
            COALESCE(source_hash, ''),
            CASE WHEN json_valid(snapshot_json) THEN snapshot_json ELSE '{}' END,
            created_at
        FROM line_update_notices;

        CREATE TABLE line_update_receipts_v233 (
            notice_id INTEGER NOT NULL REFERENCES line_update_notices_v233(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            seen_at TEXT NOT NULL,
            PRIMARY KEY (notice_id, user_id)
        );

        INSERT INTO line_update_receipts_v233 (notice_id, user_id, seen_at)
        SELECT receipt.notice_id, receipt.user_id, receipt.seen_at
        FROM line_update_receipts receipt
        JOIN line_update_notices_v233 notice ON notice.id = receipt.notice_id;

        DROP TABLE line_update_receipts;
        DROP TABLE line_update_notices;
        ALTER TABLE line_update_notices_v233 RENAME TO line_update_notices;
        ALTER TABLE line_update_receipts_v233 RENAME TO line_update_receipts;

        CREATE INDEX idx_line_update_notices_list_date
            ON line_update_notices(list_id, delivery_date, created_at DESC, id DESC);
        CREATE INDEX idx_line_update_receipts_user
            ON line_update_receipts(user_id, notice_id);
        """
    )


def _migration_008_v234_authoritative_import_schema_guard(connection: Any) -> None:
    """Reapply the canonical notice-table shape as an idempotent schema guard.

    Runtime automation now repairs this schema even when store initialization is
    disabled. This numbered migration provides the same guarantee during normal
    application startup and advances the verified schema ledger to version 8.
    """
    _migration_007_v233_repair_removed_import_notice_schema(connection)

def _migration_009_v236_protected_manual_orders(connection: Any) -> None:
    """Add an explicit operator-controlled A+W import protection flag.

    The flag is copied to each workflow-stage line for a manual order. A protected
    manual line is never consumed as the matching A+W source row and is never
    retired as a duplicate during authoritative reconciliation.
    """
    _ensure_column(
        connection,
        "line_items",
        "protect_from_aw_import",
        "INTEGER NOT NULL DEFAULT 0 CHECK (protect_from_aw_import IN (0, 1))",
    )
    _ensure_column(
        connection,
        "manual_delivery_entries",
        "protect_from_aw_import",
        "INTEGER NOT NULL DEFAULT 0 CHECK (protect_from_aw_import IN (0, 1))",
    )


def _migration_010_v245_superseded_order_review(connection: Any) -> None:
    """Create the local-only superseded-order review queue.

    Detection is advisory. Only an explicit Admin decision can activate exact
    A+W order/item exclusions, so production statuses never become a broad
    deletion rule.
    """
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS superseded_order_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_key TEXT NOT NULL UNIQUE,
            delivery_date TEXT NOT NULL,
            header_identity TEXT NOT NULL DEFAULT '',
            original_order_no TEXT NOT NULL,
            replacement_order_no TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'approved', 'keep_both', 'review_later')),
            confidence TEXT NOT NULL DEFAULT 'high',
            evidence_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(evidence_json)),
            original_items_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(original_items_json)),
            replacement_items_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(replacement_items_json)),
            source_fingerprint TEXT NOT NULL DEFAULT '',
            detected_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            decided_at TEXT NOT NULL DEFAULT '',
            decided_by TEXT NOT NULL DEFAULT '',
            decision_reason TEXT NOT NULL DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
            created_at_utc TEXT NOT NULL DEFAULT '',
            updated_at_utc TEXT NOT NULL DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_superseded_order_reviews_status_date
            ON superseded_order_reviews(status, active, delivery_date DESC, last_seen_at DESC, id DESC);
        CREATE INDEX IF NOT EXISTS idx_superseded_order_reviews_orders
            ON superseded_order_reviews(delivery_date, original_order_no, replacement_order_no);
        """
    )


def _migration_011_v257_superseded_remove_choice(connection: Any) -> None:
    """Persist which candidate order an Admin explicitly chose to remove.

    Existing v0.245-v0.256 approvals left this value blank. Runtime logic treats
    those legacy approvals as original-order removals, preserving their exact
    historical behavior while all new approvals record the selected candidate.
    """
    _ensure_column(
        connection,
        "superseded_order_reviews",
        "approved_remove_order_no",
        "TEXT NOT NULL DEFAULT ''",
    )


def _migration_012_v484_aw_reject_sync(connection: Any) -> None:
    """Persist A+W breakage source rows separately from scanner Internal Rejects.

    ``PROD_BREAKAGE.ROWID`` is the immutable external row identity. Multiple
    BOM rows that share the same order/item/breakage timestamp and A+W
    ``KEYINDEX`` are grouped into one logical event so UI and metrics do not
    multiply one operator reject by the number of production BOM nodes.
    """
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS aw_reject_events (
            event_key TEXT PRIMARY KEY,
            order_no TEXT NOT NULL,
            item_no TEXT NOT NULL,
            breakage_date TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity >= 0),
            original_job_number TEXT NOT NULL DEFAULT '',
            replacement_job_number TEXT NOT NULL DEFAULT '',
            reason_code INTEGER NOT NULL DEFAULT 0,
            reason_label TEXT NOT NULL DEFAULT '',
            location_code INTEGER NOT NULL DEFAULT 0,
            location_label TEXT NOT NULL DEFAULT '',
            from_scanner INTEGER NOT NULL DEFAULT 0 CHECK (from_scanner IN (0, 1)),
            breakage_user TEXT NOT NULL DEFAULT '',
            timeline_employee TEXT NOT NULL DEFAULT '',
            work_type_id INTEGER NOT NULL DEFAULT 0,
            work_type TEXT NOT NULL DEFAULT '',
            registration_point_id INTEGER NOT NULL DEFAULT 0,
            registration_point TEXT NOT NULL DEFAULT '',
            machine TEXT NOT NULL DEFAULT '',
            scan_mode TEXT NOT NULL DEFAULT '',
            booking_message TEXT NOT NULL DEFAULT '',
            source_row_count INTEGER NOT NULL DEFAULT 0 CHECK (source_row_count >= 0),
            source_last_changed_at TEXT NOT NULL DEFAULT '',
            source_last_changed_user TEXT NOT NULL DEFAULT '',
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            source_payload_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(source_payload_json))
        );

        CREATE TABLE IF NOT EXISTS aw_reject_source_rows (
            aw_row_id TEXT PRIMARY KEY,
            event_key TEXT NOT NULL REFERENCES aw_reject_events(event_key) ON DELETE CASCADE,
            order_no TEXT NOT NULL,
            item_no TEXT NOT NULL,
            bom_id INTEGER NOT NULL DEFAULT 0,
            key_index INTEGER NOT NULL DEFAULT 0,
            sub_position INTEGER NOT NULL DEFAULT 0,
            bom_node INTEGER NOT NULL DEFAULT 0,
            quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
            breakage_date TEXT NOT NULL,
            original_job_number TEXT NOT NULL DEFAULT '',
            replacement_job_number TEXT NOT NULL DEFAULT '',
            is_breakage INTEGER NOT NULL DEFAULT 1 CHECK (is_breakage IN (0, 1)),
            reason_code INTEGER NOT NULL DEFAULT 0,
            location_code INTEGER NOT NULL DEFAULT 0,
            from_scanner INTEGER NOT NULL DEFAULT 0 CHECK (from_scanner IN (0, 1)),
            last_changed_at TEXT NOT NULL DEFAULT '',
            last_changed_user TEXT NOT NULL DEFAULT '',
            synced_at TEXT NOT NULL,
            source_payload_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(source_payload_json))
        );

        CREATE INDEX IF NOT EXISTS idx_aw_reject_events_order_item_time
            ON aw_reject_events(order_no, item_no, breakage_date DESC);
        CREATE INDEX IF NOT EXISTS idx_aw_reject_events_time
            ON aw_reject_events(breakage_date DESC);
        CREATE INDEX IF NOT EXISTS idx_aw_reject_source_rows_event
            ON aw_reject_source_rows(event_key, bom_id, key_index);
        CREATE INDEX IF NOT EXISTS idx_aw_reject_source_rows_time
            ON aw_reject_source_rows(breakage_date DESC);
        """
    )



def _migration_013_v485_internalize_aw_rejects(connection: Any) -> None:
    """Unify A+W breakage with Internal Reject reporting without mutating A+W.

    Scanner-created reject rows keep their existing rollback semantics. Imported
    A+W breakage rows are mirrored into ``reject_events`` as source_type ``aw``
    records and never replay scan/rack/bay rollback. Stable numeric A+W codes are
    mapped separately so admins can rename historical and future display values
    in one operation while retaining raw A+W labels in ``aw_reject_events``.
    """
    _ensure_column(connection, "reject_events", "source_type", "TEXT NOT NULL DEFAULT 'scanner'")
    _ensure_column(connection, "reject_events", "source_external_key", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(connection, "reject_events", "source_reason_code", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "reject_events", "source_location_code", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "reject_events", "manual_override_json", "TEXT NOT NULL DEFAULT '{}'")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS reject_value_mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_system TEXT NOT NULL DEFAULT 'aw',
            kind TEXT NOT NULL CHECK (kind IN ('reason', 'location')),
            source_code INTEGER NOT NULL,
            source_label TEXT NOT NULL DEFAULT '',
            mapped_label TEXT NOT NULL DEFAULT '',
            updated_by TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(source_system, kind, source_code)
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_reject_events_source_external
            ON reject_events(source_type, source_external_key)
            WHERE source_external_key <> '';
        CREATE INDEX IF NOT EXISTS idx_reject_events_source_codes
            ON reject_events(source_type, source_reason_code, source_location_code, rejected_at DESC);
        CREATE INDEX IF NOT EXISTS idx_reject_value_mappings_kind_code
            ON reject_value_mappings(source_system, kind, source_code);
        """
    )


def _migration_014_v486_aw_reject_operational_reset(connection: Any) -> None:
    """Track the one-time floor rollback attached to imported A+W rejects.

    A+W source ROWIDs are immutable enough for reconciliation even when the
    logical event timestamp/job metadata is later corrected. Keeping the marker
    on every raw source row prevents a corrected logical key from replaying the
    scan/rack/bay rollback. Existing v0.485 rows intentionally start blank so
    startup reconciliation can apply the new behavior once after upgrade.
    """
    _ensure_column(connection, "aw_reject_source_rows", "rollback_applied_at", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(connection, "aw_reject_source_rows", "rollback_scan_qty_reduced", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(connection, "reject_events", "operational_rollback_applied_at", "TEXT NOT NULL DEFAULT ''")
    connection.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_aw_reject_source_rows_rollback_pending_v486
            ON aw_reject_source_rows(event_key, rollback_applied_at);
        """
    )


def _migration_015_v487_reject_reporting_performance(connection: Any) -> None:
    """Keep unified Internal Reject reads responsive after large A+W backfills."""
    connection.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_reject_events_rejected_at_v487
            ON reject_events(rejected_at DESC, id DESC);
        CREATE INDEX IF NOT EXISTS idx_reject_events_source_time_v487
            ON reject_events(source_type, rejected_at DESC, id DESC);
        CREATE INDEX IF NOT EXISTS idx_aw_reject_source_rows_row_event_v487
            ON aw_reject_source_rows(aw_row_id, event_key, rollback_applied_at);
        """
    )


def _migration_016_v498_aw_cutting_progress(connection: Any) -> None:
    """Persist A+W cutting generations without collapsing remake history.

    ``PROD_JOBITEM.KEYINDEX`` separates replacement generations while the
    production batch/job number identifies the concrete A+W batch.  Keeping
    each generation lets Order Details select the newest physical replacement
    after an Internal Reject without losing the previous batch/optimization.
    """
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS aw_cutting_generations (
            order_no TEXT NOT NULL,
            item_no TEXT NOT NULL,
            key_index INTEGER NOT NULL DEFAULT 0,
            batch_job_number TEXT NOT NULL,
            batch_status_code INTEGER NOT NULL DEFAULT 0,
            batch_description TEXT NOT NULL DEFAULT '',
            batch_creation_at TEXT NOT NULL DEFAULT '',
            batch_employee TEXT NOT NULL DEFAULT '',
            batch_last_changed_at TEXT NOT NULL DEFAULT '',
            batch_last_changed_user TEXT NOT NULL DEFAULT '',
            optimization_number INTEGER NOT NULL DEFAULT 0,
            optimization_status_code INTEGER NOT NULL DEFAULT 0,
            optimization_mode INTEGER NOT NULL DEFAULT 0,
            optimization_date TEXT NOT NULL DEFAULT '',
            optimization_last_changed_at TEXT NOT NULL DEFAULT '',
            cutting_booking_at TEXT NOT NULL DEFAULT '',
            cutting_booking_employee TEXT NOT NULL DEFAULT '',
            cutting_booking_row_id TEXT NOT NULL DEFAULT '',
            item_barcode_start TEXT NOT NULL DEFAULT '',
            cutting_barcode_start TEXT NOT NULL DEFAULT '',
            weight REAL NOT NULL DEFAULT 0,
            surface_area REAL NOT NULL DEFAULT 0,
            source_row_count INTEGER NOT NULL DEFAULT 0 CHECK (source_row_count >= 0),
            source_payload_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(source_payload_json)),
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            synced_at TEXT NOT NULL,
            PRIMARY KEY(order_no, item_no, key_index, batch_job_number)
        );
        CREATE INDEX IF NOT EXISTS idx_aw_cutting_order_item_generation_v498
            ON aw_cutting_generations(order_no, item_no, key_index DESC, batch_creation_at DESC);
        CREATE INDEX IF NOT EXISTS idx_aw_cutting_batch_v498
            ON aw_cutting_generations(batch_job_number, optimization_number);
        """
    )


def _migration_017_v507_runtime_read_indexes(connection: Any) -> None:
    """Add focused indexes for the high-frequency interactive read paths.

    These indexes deliberately avoid broad duplicate coverage.  They target the
    exact predicates used by Order Details, the compact catalog heartbeat, scan
    history, and per-list update checks so large synchronized stage catalogs do
    not force table scans during normal browser interaction.
    """
    connection.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_line_items_active_order_item_v507
            ON line_items(order_no, item_no, list_id)
            WHERE COALESCE(is_deleted, 0) = 0;
        CREATE INDEX IF NOT EXISTS idx_delivery_lists_active_date_revision_v507
            ON delivery_lists(status, delivery_date DESC, revision, id);
        CREATE INDEX IF NOT EXISTS idx_scan_events_list_recent_v507
            ON scan_events(list_id, created_at DESC, id DESC);
        CREATE INDEX IF NOT EXISTS idx_line_update_notices_list_recent_v507
            ON line_update_notices(list_id, id DESC, change_token, change_type);
        CREATE INDEX IF NOT EXISTS idx_aw_cutting_order_item_recent_v507
            ON aw_cutting_generations(order_no, item_no, key_index DESC, batch_creation_at DESC, batch_job_number DESC);
        """
    )


def _migration_018_v507_normalize_external_timestamps(connection: Any) -> None:
    """Repair external SQL timestamps while preserving immutable event keys."""
    timestamp_columns = (
        ("line_items", "last_rejected_at"),
        ("reject_events", "rejected_at"),
        ("aw_reject_events", "breakage_date"),
        ("aw_reject_events", "source_last_changed_at"),
        ("aw_reject_source_rows", "breakage_date"),
        ("aw_reject_source_rows", "last_changed_at"),
    )
    for table, column in timestamp_columns:
        columns = {str(row[1]) for row in connection.execute(f"PRAGMA table_info([{table}])").fetchall()}
        if column not in columns:
            continue
        rows = connection.execute(
            f"SELECT rowid, [{column}] FROM [{table}] WHERE TRIM(COALESCE([{column}], '')) <> ''"
        ).fetchall()
        for row in rows:
            value = str(row[1] or "").strip()
            try:
                normalized = normalize_utc_timestamp(value)
            except (TypeError, ValueError):
                # Leave malformed evidence intact so the integrity tool can
                # identify it rather than silently discarding source history.
                continue
            if normalized != value:
                connection.execute(
                    f"UPDATE [{table}] SET [{column}] = ? WHERE rowid = ?",
                    (normalized, row[0]),
                )


def _migration_019_v516_aw_eastern_timestamp_contract(connection: Any) -> None:
    """Repair A+W plant-local timestamps and establish the Eastern-time contract.

    A+W SQL ``datetime`` values are Monroe/Charlotte wall-clock times. Migration
    18 correctly made scanner timestamps aware, but it had no source-specific
    timezone contract and therefore tagged offset-free A+W reject clocks as UTC.
    This migration repairs those persisted A+W rows without changing immutable
    event keys, and normalizes legacy Cutting generation clocks that were still
    stored without offsets.
    """

    tables = {
        str(row[0])
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }

    # Cutting generations were intentionally left as source text in schema 18.
    # Offset-free values are safe to localize directly; already-aware values are
    # absolute and ``normalize_aw_plant_timestamp`` preserves their instant.
    if "aw_cutting_generations" in tables:
        cutting_columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info([aw_cutting_generations])").fetchall()
        }
        timestamp_columns = [
            column
            for column in (
                "batch_creation_at",
                "batch_last_changed_at",
                "optimization_date",
                "optimization_last_changed_at",
                "cutting_booking_at",
            )
            if column in cutting_columns
        ]
        payload_available = "source_payload_json" in cutting_columns
        select_columns = ", ".join(f"[{column}]" for column in timestamp_columns)
        if payload_available:
            select_columns = f"{select_columns}, [source_payload_json]" if select_columns else "[source_payload_json]"
        if select_columns:
            rows = connection.execute(
                f"SELECT rowid, {select_columns} FROM [aw_cutting_generations]"
            ).fetchall()
            for row in rows:
                rowid = row[0]
                values = list(row[1:1 + len(timestamp_columns)])
                updates: dict[str, str] = {}
                for column, value in zip(timestamp_columns, values):
                    text = str(value or "").strip()
                    if not text:
                        continue
                    try:
                        normalized = normalize_aw_plant_timestamp(text)
                    except (TypeError, ValueError):
                        continue
                    if normalized != text:
                        updates[column] = normalized

                payload_index = 1 + len(timestamp_columns)
                raw_payload = row[payload_index] if payload_available else ""
                payload_text = str(raw_payload or "")
                payload_changed = False
                payload: dict[str, Any] = {}
                if payload_text:
                    try:
                        parsed = json.loads(payload_text)
                        if isinstance(parsed, dict):
                            payload = parsed
                    except (TypeError, ValueError, json.JSONDecodeError):
                        payload = {}
                cut_evidence = payload.get("cutEvidence") if isinstance(payload.get("cutEvidence"), dict) else None
                if cut_evidence is not None:
                    plate_changed = str(cut_evidence.get("plateLastChangedAt") or "").strip()
                    if plate_changed:
                        try:
                            normalized_plate = normalize_aw_plant_timestamp(plate_changed)
                            if normalized_plate != plate_changed:
                                cut_evidence["plateLastChangedAt"] = normalized_plate
                                payload_changed = True
                        except (TypeError, ValueError):
                            pass
                    assignments = cut_evidence.get("sequenceAssignments")
                    if isinstance(assignments, list):
                        for assignment in assignments:
                            if not isinstance(assignment, dict):
                                continue
                            value = str(assignment.get("plateLastChangedAt") or "").strip()
                            if not value:
                                continue
                            try:
                                normalized = normalize_aw_plant_timestamp(value)
                            except (TypeError, ValueError):
                                continue
                            if normalized != value:
                                assignment["plateLastChangedAt"] = normalized
                                payload_changed = True
                if payload_changed:
                    updates["source_payload_json"] = json.dumps(payload, sort_keys=True, separators=(",", ":"))

                if updates:
                    assignments = ", ".join(f"[{column}] = ?" for column in updates)
                    connection.execute(
                        f"UPDATE [aw_cutting_generations] SET {assignments} WHERE rowid = ?",
                        (*updates.values(), rowid),
                    )

    # A+W reject source rows retain the original source payload. Prefer those raw
    # clock values because migration 18 may already have tagged the persisted
    # column as +00:00. When an old payload is unavailable, reinterpret only these
    # known A+W columns' clock components as Eastern exactly once.
    if "aw_reject_source_rows" in tables:
        columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info([aw_reject_source_rows])").fetchall()
        }
        rows = connection.execute(
            "SELECT rowid, event_key, breakage_date, last_changed_at, source_payload_json "
            "FROM aw_reject_source_rows"
        ).fetchall() if {"event_key", "breakage_date", "last_changed_at", "source_payload_json"}.issubset(columns) else []
        for rowid, _event_key, stored_breakage, stored_changed, payload_text in rows:
            source_payload: dict[str, Any] = {}
            try:
                parsed = json.loads(str(payload_text or "{}"))
                if isinstance(parsed, dict):
                    source_payload = parsed
            except (TypeError, ValueError, json.JSONDecodeError):
                source_payload = {}
            raw_breakage = str(source_payload.get("breakageDate") or "").strip()
            raw_changed = str(source_payload.get("sourceLastChangedAt") or "").strip()
            try:
                breakage = (
                    normalize_aw_plant_timestamp(raw_breakage)
                    if raw_breakage
                    else reinterpret_legacy_aw_utc_clock_as_plant(stored_breakage)
                )
            except (TypeError, ValueError):
                breakage = str(stored_breakage or "")
            try:
                changed = (
                    normalize_aw_plant_timestamp(raw_changed)
                    if raw_changed
                    else reinterpret_legacy_aw_utc_clock_as_plant(stored_changed)
                )
            except (TypeError, ValueError):
                changed = str(stored_changed or "")
            if breakage != str(stored_breakage or "") or changed != str(stored_changed or ""):
                connection.execute(
                    "UPDATE aw_reject_source_rows SET breakage_date=?, last_changed_at=? WHERE rowid=?",
                    (breakage, changed, rowid),
                )

    # Logical A+W events derive their timestamps from the repaired raw source
    # rows. BOM rows for one logical event share breakage time; the latest source
    # maintenance clock remains the event's source-last-changed value.
    if "aw_reject_events" in tables and "aw_reject_source_rows" in tables:
        connection.execute(
            """
            UPDATE aw_reject_events
            SET breakage_date = COALESCE((
                    SELECT MIN(src.breakage_date)
                    FROM aw_reject_source_rows src
                    WHERE src.event_key = aw_reject_events.event_key
                      AND TRIM(COALESCE(src.breakage_date, '')) <> ''
                ), breakage_date),
                source_last_changed_at = COALESCE((
                    SELECT MAX(src.last_changed_at)
                    FROM aw_reject_source_rows src
                    WHERE src.event_key = aw_reject_events.event_key
                      AND TRIM(COALESCE(src.last_changed_at, '')) <> ''
                ), source_last_changed_at)
            """
        )

    # Keep the mirrored Internal Reject timestamp aligned with its authoritative
    # A+W event unless an operator explicitly overrode ``rejectedAt``.
    if "reject_events" in tables and "aw_reject_events" in tables:
        rows = connection.execute(
            """
            SELECT re.rowid, re.source_external_key, re.rejected_at, re.manual_override_json,
                   aw.breakage_date
            FROM reject_events re
            JOIN aw_reject_events aw ON aw.event_key = re.source_external_key
            WHERE re.source_type = 'aw' AND TRIM(COALESCE(re.source_external_key, '')) <> ''
            """
        ).fetchall()
        for rowid, _event_key, rejected_at, override_text, aw_breakage in rows:
            overrides: dict[str, Any] = {}
            try:
                parsed = json.loads(str(override_text or "{}"))
                if isinstance(parsed, dict):
                    overrides = parsed
            except (TypeError, ValueError, json.JSONDecodeError):
                overrides = {}
            if str(overrides.get("rejectedAt") or "").strip():
                continue
            corrected = str(aw_breakage or "").strip()
            if corrected and corrected != str(rejected_at or ""):
                connection.execute(
                    "UPDATE reject_events SET rejected_at=? WHERE rowid=?",
                    (corrected, rowid),
                )

    # ``line_items.last_rejected_at`` is a materialized summary. Recompute only
    # identities that have reject history so current fabrication/recut cutoffs use
    # the same corrected instant as Rejects and Order Details.
    if "line_items" in tables and "reject_events" in tables and "delivery_lists" in tables:
        connection.execute(
            """
            UPDATE line_items
            SET last_rejected_at = COALESCE((
                SELECT MAX(re.rejected_at)
                FROM reject_events re
                JOIN delivery_lists dl ON dl.id = line_items.list_id
                WHERE re.delivery_date = dl.delivery_date
                  AND re.order_no = line_items.order_no
                  AND re.item_no = line_items.item_no
            ), last_rejected_at)
            WHERE EXISTS (
                SELECT 1
                FROM reject_events re
                JOIN delivery_lists dl ON dl.id = line_items.list_id
                WHERE re.delivery_date = dl.delivery_date
                  AND re.order_no = line_items.order_no
                  AND re.item_no = line_items.item_no
            )
            """
        )


def run_sqlite_migrations(connection: Any, owner: Any) -> list[int]:
    """Handle run sqlite migrations for the maintained Delivery List Scanner workflow."""
    validate_migration_registry()
    ensure_migration_table(connection)
    baseline_legacy_v096(connection, owner)
    validate_installed_checksums(connection)
    installed = installed_migrations(connection)
    prepare_v096_compatibility_schema(connection, owner, installed)
    installed = installed_migrations(connection)
    applied: list[int] = []
    for migration in MIGRATIONS:
        if migration.version > CURRENT_SCHEMA_VERSION or migration.version in installed:
            continue
        started = time.monotonic()
        method: Callable[[Any], None] | None = globals().get(migration.method_name)
        if not callable(method):
            method = getattr(owner, migration.method_name)
        foreign_keys_disabled = migration.version >= 2
        try:
            if foreign_keys_disabled:
                connection.commit()
                connection.execute("PRAGMA foreign_keys = OFF")
                connection.execute("BEGIN IMMEDIATE")
            method(connection)
            elapsed_ms = max(int((time.monotonic() - started) * 1000), 0)
            connection.execute(
                "INSERT INTO schema_migrations (version, name, checksum, applied_at_utc, execution_ms, app_version) VALUES (?, ?, ?, ?, ?, ?)",
                (migration.version, migration.name, migration.checksum, utc_now(), elapsed_ms, APPLICATION_VERSION),
            )
            if foreign_keys_disabled:
                violations = connection.execute("PRAGMA foreign_key_check").fetchall()
                if violations:
                    raise MigrationError(
                        f"Migration {migration.version:03d} left {len(violations)} foreign-key violation(s)"
                    )
            connection.commit()
            if foreign_keys_disabled:
                connection.execute("PRAGMA foreign_keys = ON")
        except Exception:
            connection.rollback()
            if foreign_keys_disabled:
                connection.execute("PRAGMA foreign_keys = ON")
            raise
        applied.append(migration.version)
        installed[migration.version] = {"checksum": migration.checksum}
    validate_installed_checksums(connection)
    final_installed = installed_migrations(connection)
    installed_versions = sorted(final_installed)
    expected_versions = list(range(1, CURRENT_SCHEMA_VERSION + 1))
    missing_versions = sorted(set(expected_versions) - set(installed_versions))
    unexpected_versions = sorted(set(installed_versions) - set(expected_versions))
    if missing_versions or unexpected_versions:
        defined_versions = [migration.version for migration in MIGRATIONS]
        raise MigrationError(
            "Database did not reach the expected schema version. "
            f"Expected={CURRENT_SCHEMA_VERSION}; installed={installed_versions}; "
            f"defined={defined_versions}; missing={missing_versions}; "
            f"unexpected={unexpected_versions}."
        )
    return applied


def database_needs_upgrade(path: Path) -> bool:
    """Handle database needs upgrade for the maintained Delivery List Scanner workflow."""
    if not path.exists() or path.stat().st_size == 0:
        return False
    connection = sqlite3.connect(path)
    try:
        if not has_application_tables(connection):
            return False
        table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'schema_migrations'"
        ).fetchone()
        if not table:
            return True
        row = connection.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migrations").fetchone()
        return int(row[0] or 0) < CURRENT_SCHEMA_VERSION
    finally:
        connection.close()


def create_verified_backup(database_path: Path, backup_dir: Path | None = None) -> Path:
    """Create and verify an online SQLite backup without modifying the source."""
    database_path = database_path.resolve()
    if not database_path.exists():
        raise FileNotFoundError(database_path)
    target_dir = (backup_dir or database_path.parent / "backups").resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = target_dir / f"{database_path.stem}-before-v{APPLICATION_VERSION}-{stamp}.db"
    source = sqlite3.connect(database_path, timeout=60)
    destination = sqlite3.connect(target)
    try:
        source.backup(destination)
        destination.commit()
        result = destination.execute("PRAGMA integrity_check").fetchone()
        if not result or str(result[0]).lower() != "ok":
            raise MigrationError(f"Backup integrity check failed: {result[0] if result else 'no result'}")
        foreign_keys = destination.execute("PRAGMA foreign_key_check").fetchall()
        if foreign_keys:
            raise MigrationError(f"Backup contains {len(foreign_keys)} foreign-key violation(s)")
    except Exception:
        destination.close()
        source.close()
        if target.exists():
            target.unlink()
        raise
    destination.close()
    source.close()
    return target
