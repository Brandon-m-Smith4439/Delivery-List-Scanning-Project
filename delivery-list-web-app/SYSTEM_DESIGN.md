# Delivery List System Design

Yes, this can become a real delivery-list system as a website/web app. The static prototype proves the operator interface, but production needs a shared data store and a small backend so multiple users can scan at the same time.

## Core Pieces

- Web app: desktop and mobile scanning UI.
- Backend API: validates scans, records scan events, serves current delivery lists.
- Database: stores delivery lists, line items, scan events, users, stations, bay assignments, and audit history.
- Importer: loads new delivery lists from Excel/CSV/SharePoint.
- Sync jobs: optional Power Automate or scheduled workers for SharePoint snapshots, alerts, and reports.

## Current Pilot Architecture

The pilot now has a backend boundary that can survive a database migration:

- `server.py` is the HTTP/API layer.
- `scanner_config.py` loads server-side configuration from environment variables.
- `delivery_store.py` defines the data-access contract and implements `SQLiteDeliveryStore`.
- Future SQL Server/PostgreSQL/Azure SQL support should be added by creating another store adapter with the same methods.
- `index.html`, `app.js`, and `styles.css` provide the desktop/mobile scanner UI, login screen, utility panel, admin dashboard, exception center, global search, and Indian Trail bay map.

Important current store methods include:

- `get_delivery_lists()`
- `get_delivery_list(list_id)`
- `get_line_items(list_id)`
- `record_scan(scan_request)`
- `undo_last_scan(list_id, user, station)`
- `reset_stage(list_id, user, station)`
- `import_delivery_list(payload)`
- `preview_import(payload)`
- `get_scan_events(list_id, only_errors)`
- `get_exceptions(filters)`
- `resolve_exception(data, user)`
- `get_stations()`
- `add_station(name)`
- `export_csv(list_id)`
- `authenticate_user(username, password)`
- `get_user_by_session(token)`
- `create_user(data, created_by)`
- `admin_summary()`
- `global_search(query)`
- `reports_summary()`
- `receive_indian_trail_scan(data, user)`
- `assign_bay(data, user)`
- `clear_bay(data, user)`
- `mark_sdi(data, user)`

This keeps SQL out of the route handler and gives IT a clear place to integrate the company SQL database later.

## Current Phase 2 Coverage

Phase 2 now has a working local foundation:

- Local username/password login with hashed passwords and server-side sessions.
- Seeded Admin, Operator, Supervisor, and Indian Trail roles.
- API permission gates for scans, reset, undo, import, export, reports, stations, users, exceptions, and bay actions.
- Admin dashboard endpoints for summary stats, recent imports, reports, exceptions, global search, users, permissions, and Indian Trail bay status.
- Import preview before committing delivery-list updates.
- Customer Pickup delivery list filtering to CPU orders only.
- Indian Trail receive scan workflow with automatic bay assignment.
- Indian Trail bay map seeded from the workbook layout in `Indian Trail Inventory Manager.xlsm`.
- Repeatable validation scripts for scan workflows and Phase 2 auth/admin/API behavior.

## Database Options

### SharePoint Lists

Best low-friction Microsoft 365 path. Good for permissions and Power Automate, but not ideal for very high scan volume or complex queries.

Recommended when IT will allow Microsoft 365 storage faster than a new server.

### SQLite

Simple local database file hosted with the web app. Fast and cheap for one-site LAN usage, but needs careful backup and one server/computer to host it.

Recommended for a plant-local pilot.

SQLite is a database stored in one local file. In this prototype that file is `data/delivery-scanner-pilot.db`. There is no separate database server to install. The web app's Python backend opens that file, writes scan events, updates quantities, and serves the current list back to every browser using the app.

SQLite is excellent for proving the workflow and running a small local pilot. It is not the final choice if many plants, high scan volume, enterprise backups, centralized permissions, or IT reporting are required.

### PostgreSQL

Professional shared database for long-term use. Strong concurrency, reporting, backups, and audit history.

Recommended for the polished permanent system.

### SQL Server

Very strong fit if the company already supports Microsoft SQL Server. Best enterprise Microsoft path, but depends on IT access.

Recommended if IT will provide a database but not a vendor app.

For IT's existing SQL database, the clean integration is:

- Keep this web UI.
- Replace the current SQLite data layer with a SQL Server data layer.
- Use the same core tables: `delivery_lists`, `line_items`, `scan_events`, `exceptions`, `stations`, `users`, `roles`, `role_permissions`, `sessions`, `imports`, `bays`, `bay_assignments`, `bay_events`, and `audit_events`.
- Store the SQL connection string in a server environment variable, not in browser code.
- Use Windows/Entra authentication if IT supports it; otherwise use a least-privilege SQL login for this app.
- Keep scan validation server-side so two scanners cannot over-count the same item.
- Add scheduled backups and a restore test owned by IT.

The intended SQL Server change is not a rewrite of the app. Add something like `SqlServerDeliveryStore` in `delivery_store.py` or a sibling module, implement the same store methods, then switch with `DLS_DATABASE_TYPE=sqlserver` and `DLS_DATABASE_CONNECTION_STRING=...`.

## Multi-User Scanning

Multiple users can scan at the same time if every scan is recorded as an atomic server-side transaction:

1. Scanner submits barcode, station, user, delivery list, and timestamp.
2. Server canonicalizes or rejects the scan.
3. Server locks/checks the matching line item.
4. Server increments scanned quantity only if remaining quantity exists.
5. Server writes a scan-event row for audit history.
6. Server broadcasts the update to other open screens.

The browser must not be the source of truth for production quantity updates. The backend/database must decide.

## Delivery List Selector

The selector should come from a `delivery_lists` table:

- ID
- delivery date
- source file name
- status: draft, active, archived
- stage/profile
- imported by
- imported at
- revision

Each operator station can default to a stage, but users can switch lists when allowed.

## Indian Trail Bay Sorting

The Indian Trail auto sorting system can be included as a module in the same app:

- Store bay rules in a `bay_rules` table.
- Calculate suggested bay during import and again during scan if needed.
- Allow supervisor override with reason.
- Print/export bay labels or bay lists.
- Show bay counts live on the Indian Trail screen.

Rules can use dimensions, product type, route, customer, rack/bay capacity, and manual overrides.

The pilot already loads the Indian Trail workbook layout, exposes it as a dedicated bay-map page, and can receive an Indian Trail scan into the first available matching bay type. The next step is to refine the bay assignment rules with production labels, capacity rules, and any floor-specific exceptions.

## Power Automate

The system can still use Power Automate, but it should not depend on Power Automate for the critical scan transaction.

Good uses:

- Notify teams when a list is published.
- Save daily reports to SharePoint.
- Email/export exceptions.
- Copy snapshots to SharePoint for visibility.

Avoid:

- Using flows as the only real-time scan processor.
- Depending on flows for high-speed barcode validation.

## Recommended Rollout

1. Keep Excel master as source of truth.
2. Web app reads published JSON snapshots and writes scan events to a queue.
3. Master or a small service processes the queue.
4. Move source of truth to a database once users trust the web UI.
5. Keep Excel export/reporting for people who still need workbook output.

This gives a safe bridge instead of trying to replace everything in one jump.

## Web App vs Desktop Program

For multi-user scanning, the web app is the better long-term fit. A desktop program installed on every computer would still need a shared database, update deployment, user access management, and conflict handling. A web app puts those pieces in one place: one backend, one database, and one UI that works on desktops, tablets, and phones.

A desktop wrapper can still be useful later if operators need a kiosk-style shortcut, label-printer integration, or barcode-scanner hardware settings. In that case the wrapper should open the same web app rather than becoming a separate source of truth.

## Utility Panel Coverage

The web app should absorb the master workbook utility panel in stages:

- Import/update delivery lists from Excel-exported JSON or CSV.
- Refresh the active list from the database.
- Print the current filtered list.
- Export list and scan history to CSV.
- Reset or undo scans with audit records.
- Add/manage stations.
- Manage stages, route filters, bay rules, and scanner defaults.
- Publish snapshots to SharePoint or SQL views for reporting.
