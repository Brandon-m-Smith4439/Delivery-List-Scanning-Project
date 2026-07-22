# Delivery List Scanner Database Schema

Version: v097  
Canonical logical contract: `database_contract.py`  
SQLite schema ownership: numbered methods registered by `database_migrations.py`  
Azure SQL schema ownership: `azure_sql_schema.sql`

## Design rules

- SQLite remains the default local database.
- Order numbers, item numbers, barcodes, rack codes, bay codes, machine codes, and scanner codes are text.
- Business workflows live in `delivery_store.py`; browser and API code remain database agnostic.
- `scan_events`, `audit_events`, and `machine_events` are append-only history.
- Timestamps created by v097 use UTC ISO-8601 text in SQLite and `datetime2(0)` in Azure SQL.
- JSON is limited to optional metadata, message recipients, and rendered payloads. Searchable business fields are normal columns.
- Soft-delete/audit fields are present on core mutable entities. Existing behavior continues to use active/status fields until a workflow explicitly adopts soft deletion.

## Tables

| Table | Responsibility | Important relationships |
|---|---|---|
| `schema_migrations` | Installed migration number, name, checksum, timing, and app version | Independent system history |
| `delivery_lists` | One date/stage delivery list | Parent of line items, scans, exceptions, and assignments |
| `line_items` | Searchable glass/order rows and stage quantities | FK to delivery list; identifiers remain text |
| `scan_events` | Immutable scan, duplicate, notice, undo, and redo history | FK to list; nullable FK to line item |
| `stations` | Configured scanning stations | Station names are copied into immutable history |
| `customer_route_rules` | Import routing rules | Independent configuration |
| `system_metadata` | Idempotent repair/configuration markers | Independent configuration |
| `admin_lookup_values` | Product, route, and process lookup values | Independent configuration |
| `imports` | Import batches, source hashes, and change summaries | Delivery date is a searchable normal column |
| `exceptions` | Resolvable scan/workflow issues | FK to delivery list and optional scan event |
| `audit_events` | Immutable administrative history | Entity references are durable text snapshots |
| `users` | Local identities | Parent of sessions, roles, acknowledgements, and audit-user fields |
| `roles` | Authorization roles | Parent of role-permission and user-role rows |
| `permissions` | Named authorization capabilities | Parent of role-permission rows |
| `role_permissions` | Role-to-permission mapping | FKs to roles and permissions |
| `user_roles` | User-to-role mapping | FKs to users and roles |
| `sessions` | Authentication sessions | FK to users |
| `password_reset_tokens` | Expiring reset challenges | FK to users |
| `bays` | Indian Trail bay definitions and map positions | Parent of assignments/events |
| `bay_assignments` | Current and historical bay occupancy | FK to list and bay; line-item ID retained as historical text |
| `bay_events` | Historical bay actions | Bay IDs are relational; line-item ID remains a durable text snapshot |
| `racks` | Rack/truck definitions and lifecycle | Parent of rack items |
| `rack_items` | Quantity of a line item on one rack | FKs to rack and line item; unique rack/item pair |
| `bay_stale_snoozes` | Stale-alert snooze state | FK to bay assignment |
| `bay_manual_input_rules` | Remembered manual bay input rules | Independent configuration |
| `bay_scan_barcode_rules` | Remembered barcode bay rules | Independent configuration |
| `bay_auto_assign_settings` | Auto-assignment thresholds | Independent key/value configuration |
| `customer_email_contacts` | Customer manifest recipients | Independent configuration |
| `customer_email_cc` | Global CC recipients | Independent configuration |
| `email_outbox` | Queued/sent/failed messages | JSON only for recipients and optional rendered payload |
| `app_notifications` | Multi-user application notices | Parent of acknowledgement rows |
| `app_notification_receipts` | Per-user notice acknowledgement | FKs to notification and user |
| `machines` | Future production machine registry | Parent of scanners and machine events |
| `scanners` | Physical scanner/device registry | Optional FK to machine |
| `machine_events` | Future immutable machine/scanner event stream | Optional FKs to machine, scanner, and line item |

## Constraints

- `line_items.qty >= 0`
- `0 <= line_items.scanned_qty <= line_items.qty`
- `rack_items.qty > 0`
- `bay_assignments.assigned_qty >= 0`
- v097 boolean fields are limited to `0/1` in SQLite and use `bit` in Azure SQL.
- Machine metadata must be valid JSON.
- Foreign keys are enabled for every SQLite connection and checked after migration.

Some v096 bay history references line-item IDs that were legitimately replaced during route synchronization. Those event and assignment reference strings are preserved rather than discarded. The database enforces every relationship that can be enforced without destroying that history.

## Indexes

`database_contract.INDEX_DESCRIPTIONS` is the canonical index inventory. Indexes cover delivery-date list selection, list/order rendering, barcode/source lookup, recent scan/audit history, active sessions, exception filters, bay/rack contents, and future machine timelines. The integrity tool reports any missing documented index.

