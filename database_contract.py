"""Canonical database contract shared by SQLite and Azure SQL tooling.

Migration DDL remains in the database-specific migration implementations.  This
module owns the logical table inventory, required v097 columns, type mapping,
and documented indexes so validation tools do not need a second schema parser.
"""

from __future__ import annotations


APPLICATION_VERSION = "121"
CURRENT_SCHEMA_VERSION = 3


TABLE_DESCRIPTIONS = {
    "schema_migrations": "Installed numbered database migrations and checksums.",
    "delivery_lists": "One delivery date and processing-stage list.",
    "line_items": "Searchable glass/order line items for a delivery-list stage.",
    "scan_events": "Immutable append-only scanner history.",
    "stations": "Configured application scanning stations.",
    "customer_route_rules": "Customer-to-route import classification rules.",
    "system_metadata": "Small idempotent system configuration markers.",
    "admin_lookup_values": "Admin-managed product, route, and process lookups.",
    "imports": "Delivery-list import batches and source fingerprints.",
    "exceptions": "Resolvable scanning and workflow exceptions.",
    "audit_events": "Immutable append-only administrative history.",
    "users": "Local application identities.",
    "roles": "Named authorization roles.",
    "permissions": "Named application permissions.",
    "role_permissions": "Many-to-many role permission assignments.",
    "user_roles": "Many-to-many user role assignments.",
    "sessions": "Authenticated browser sessions.",
    "password_reset_tokens": "Expiring password-reset challenges.",
    "bays": "Indian Trail physical bay definitions and layout.",
    "bay_assignments": "Current and historical line-item bay assignments.",
    "bay_events": "Append-only Indian Trail bay action history.",
    "racks": "Transportation rack definitions and lifecycle state.",
    "rack_items": "Line-item quantities loaded onto racks or trucks.",
    "bay_stale_snoozes": "Temporary suppression state for stale-bay alerts.",
    "bay_manual_input_rules": "Remembered manual bay matching rules.",
    "bay_scan_barcode_rules": "Remembered barcode-to-bay rules.",
    "bay_auto_assign_settings": "Automatic bay assignment configuration.",
    "customer_email_contacts": "Customer notification recipients.",
    "customer_email_cc": "Global customer-email CC recipients.",
    "email_outbox": "Queued and delivered customer notifications.",
    "app_notifications": "Multi-user in-app notices.",
    "app_notification_receipts": "Per-user notification acknowledgements.",
    "line_update_notices": "Per-user-visible new and updated delivery-list line events.",
    "line_update_receipts": "Per-user review acknowledgements for line update events.",
    "machines": "Production machines available for future scanner integration.",
    "scanners": "Physical scanner devices and optional machine association.",
    "machine_events": "Append-only machine/scanner production events.",
}


REQUIRED_COLUMNS = {
    "schema_migrations": {"version", "name", "checksum", "applied_at_utc", "execution_ms", "app_version"},
    "delivery_lists": {"id", "delivery_date", "stage", "status", "is_deleted", "created_at_utc", "updated_at_utc"},
    "line_items": {
        "id", "list_id", "source_id", "barcode", "order_no", "item_no", "qty", "scanned_qty",
        "is_deleted", "created_at_utc", "updated_at_utc",
    },
    "scan_events": {"id", "list_id", "line_item_id", "barcode", "event_type", "qty_delta", "created_at"},
    "audit_events": {"id", "entity_type", "entity_id", "action", "payload_json", "created_at"},
    "racks": {"id", "rack_code", "status", "active", "is_deleted", "created_at_utc", "updated_at_utc"},
    "rack_items": {"id", "rack_id", "line_item_id", "qty", "status", "is_deleted", "created_at_utc", "updated_at_utc"},
    "bays": {"id", "bay_code", "capacity_qty", "active", "is_deleted", "created_at_utc", "updated_at_utc"},
    "bay_assignments": {"id", "delivery_list_id", "line_item_id", "bay_id", "assigned_qty", "status", "is_deleted"},
    "machines": {"id", "machine_code", "display_name", "machine_type", "active", "metadata_json"},
    "scanners": {"id", "scanner_code", "display_name", "machine_id", "active", "metadata_json"},
    "line_update_notices": {"id", "line_item_id", "list_id", "delivery_date", "change_type", "change_token", "source_hash", "created_at"},
    "line_update_receipts": {"notice_id", "user_id", "seen_at"},
    "machine_events": {
        "id", "machine_id", "scanner_id", "line_item_id", "event_type", "event_status", "qty",
        "barcode", "order_no", "item_no", "metadata_json", "created_at_utc",
    },
}


TEXT_BUSINESS_IDENTIFIERS = {
    "line_items": {"id", "source_id", "barcode", "order_no", "item_no"},
    "racks": {"rack_code"},
    "bays": {"bay_code"},
    "machines": {"machine_code"},
    "scanners": {"scanner_code"},
    "line_update_notices": {"id", "line_item_id", "list_id", "delivery_date", "change_type", "change_token", "source_hash", "created_at"},
    "line_update_receipts": {"notice_id", "user_id", "seen_at"},
    "machine_events": {"barcode", "order_no", "item_no"},
}


SQLITE_TO_SQLSERVER_TYPES = {
    "TEXT_IDENTIFIER": "nvarchar(255)",
    "TEXT_SHORT": "nvarchar(500)",
    "TEXT_LONG": "nvarchar(max)",
    "INTEGER_ID": "bigint",
    "INTEGER": "int",
    "BOOLEAN": "bit",
    "REAL": "decimal(18,4)",
    "UTC_TIMESTAMP": "datetime2(0)",
    "JSON": "nvarchar(max) with ISJSON CHECK",
}


INDEX_DESCRIPTIONS = {
    "idx_delivery_lists_date_status_stage": "Home/list selection by delivery date, active status, and stage.",
    "idx_line_items_list_order_item": "Stage rendering and order/item lookup within a list.",
    "idx_line_items_source": "Cross-stage sibling resolution by stable source identifier.",
    "idx_line_items_barcode": "Scanner barcode lookup.",
    "idx_scan_events_list_time": "Recent scan history for one list.",
    "idx_scan_events_line_time": "Latest scan state for one line item.",
    "idx_imports_date_time": "Recent import batches by delivery date.",
    "idx_exceptions_list_status": "Open exception filters for a list.",
    "idx_audit_events_entity_time": "Administrative history for one entity.",
    "idx_sessions_user_expiry": "Active-session cleanup and user presence.",
    "idx_bay_assignments_line_status": "Current bay location for a line item.",
    "idx_bay_assignments_bay_status": "Current contents and capacity of a bay.",
    "idx_bay_events_bay_time": "Recent actions for a selected bay.",
    "idx_rack_items_rack_status": "Current contents of a rack.",
    "idx_rack_items_line_status": "Current rack location for a line item.",
    "idx_line_update_notices_list_date": "Pending update lines by delivery list and current/future date.",
    "idx_line_update_receipts_user": "Per-user review state for update lines.",
    "idx_machine_events_machine_time": "Machine event timeline.",
    "idx_machine_events_scanner_time": "Scanner event timeline.",
    "idx_machine_events_order_item": "Production lookup by order and item.",
}


JSON_COLUMNS = {
    "audit_events": {"payload_json"},
    "app_notifications": {"payload_json"},
    "email_outbox": {"to_emails", "cc_emails", "payload_json"},
    "machines": {"metadata_json"},
    "scanners": {"metadata_json"},
    "line_update_notices": {"id", "line_item_id", "list_id", "delivery_date", "change_type", "change_token", "source_hash", "created_at"},
    "line_update_receipts": {"notice_id", "user_id", "seen_at"},
    "machine_events": {"metadata_json"},
}


TIMESTAMP_COLUMNS = {
    "schema_migrations": {"applied_at_utc"},
    "delivery_lists": {"created_at", "created_at_utc", "updated_at_utc", "deleted_at_utc"},
    "line_items": {"created_at_utc", "updated_at_utc", "deleted_at_utc"},
    "scan_events": {"created_at"},
    "audit_events": {"created_at"},
    "sessions": {"created_at", "expires_at", "last_seen_at"},
    "racks": {"created_at", "updated_at", "completed_at", "departed_at", "returned_at", "created_at_utc", "updated_at_utc", "deleted_at_utc"},
    "rack_items": {"added_at", "removed_at", "created_at_utc", "updated_at_utc", "deleted_at_utc"},
    "bay_assignments": {"assigned_at", "cleared_at", "created_at_utc", "updated_at_utc", "deleted_at_utc"},
    "line_update_notices": {"id", "line_item_id", "list_id", "delivery_date", "change_type", "change_token", "source_hash", "created_at"},
    "line_update_receipts": {"notice_id", "user_id", "seen_at"},
    "line_update_notices": {"created_at"},
    "line_update_receipts": {"seen_at"},
    "machine_events": {"created_at_utc"},
}

