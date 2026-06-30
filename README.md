# Delivery List Web App Prototype

This is a static prototype for a future independent delivery-list scanning system. It uses the Version 3 master workbook data exported to `data/sample-delivery-list.json` and runs without Excel.

## Run With The SQLite Backend

Double-click:

```text
Start Delivery Scanner Web App.bat
```

Or from PowerShell:

```powershell
.\Start-DeliveryScannerWebApp.ps1
```

The launcher uses the bundled Codex Python on this machine when available, picks the next open local port starting at `8765`, opens the browser, and stores scan state in:

```text
data/delivery-scanner-pilot.db
```

Manual run from this folder:

```powershell
$env:PORT = "8765"
py -3 .\server.py
```

Open:

```text
http://127.0.0.1:8765/
```

Default local login:

```text
Username: admin
Password: Admin123!
```

Seeded test accounts:

```text
operator / Operator123!
supervisor / Supervisor123!
itoperator / Trail123!
itlead / TrailLead123!
itmanager / TrailManager123!
```

Change the default admin values before a real pilot by setting `DLS_DEFAULT_ADMIN_USERNAME` and `DLS_DEFAULT_ADMIN_PASSWORD` before the first database is created.

## Architecture

The backend is split into a small HTTP layer, server-side config, and a data-access layer:

- `server.py`: serves the web app and exposes `/api/...` routes.
- `scanner_config.py`: reads environment/config values.
- `delivery_store.py`: contains the database contract and current SQLite implementation.
- `tests/validate_workflows.py`: repeatable validation for scan rules and critical workflows.
- `tests/validate_phase2.py`: repeatable validation for login, roles, admin routes, import preview, reports, search, and Indian Trail bay APIs.

The browser uses relative API paths such as `/api/scans`; database paths, ports, auth mode, and future SQL connection strings stay on the server.

## Configuration

Optional environment variables:

```powershell
$env:DLS_DATABASE_TYPE = "sqlite"
$env:DLS_DATABASE_PATH = ".\data\delivery-scanner-pilot.db"
$env:DLS_HOST = "127.0.0.1"
$env:DLS_PORT = "8765"
$env:DLS_BASE_URL = "http://127.0.0.1:8765/"
$env:DLS_AUTH_MODE = "local-dev"
$env:DLS_SESSION_SECRET = "change-this-before-production"
$env:DLS_DEFAULT_ADMIN_USERNAME = "admin"
$env:DLS_DEFAULT_ADMIN_PASSWORD = "Admin123!"
$env:DLS_ENVIRONMENT = "development"
```

`DLS_DATABASE_TYPE` is intentionally abstracted now. SQLite works today. SQL Server/PostgreSQL/Azure SQL should be added as a new store adapter that implements the same methods as `SQLiteDeliveryStore`.

## Validation

Run the workflow checks from this folder:

```powershell
py -3 .\tests\validate_workflows.py
py -3 .\tests\validate_phase2.py
```

`validate_workflows.py` validates:

- delivery-list seeding
- Customer Pickup CPU filtering
- exact scan
- outbound scan auto-staging when the matching staging scan is missing
- damaged-label recovery
- duplicate/over-quantity rejection
- bad scan rejection
- ambiguous damaged scan rejection
- undo
- station add
- exception logging
- CSV export
- import/update

`validate_phase2.py` validates:

- default admin creation and hashed password storage
- role permissions for Admin and Operator
- unauthenticated and forbidden API responses
- login/session cookie behavior
- admin summary, reports, global search, and import preview
- seeded bay map and Indian Trail receive-to-bay assignment
- Indian Trail recent bay action feed
- operator scan/export access without admin access
- stage-filtered delivery lists for Airport Road, Customer Pickup, and Indian Trail accounts

## Static Demo Mode

From this folder:

```powershell
python -m http.server 8765 --bind 127.0.0.1
```

Open:

```text
http://127.0.0.1:8765/
```

Demo damaged scan URL:

```text
http://127.0.0.1:8765/?reset=1&demoScan=TDEXRTY887001000
```

## What Works

- Desktop scanner/table layout based on the provided mockup.
- Mobile scan-first layout with bottom navigation.
- Home overview section for the current/latest delivery date with stage progress cards.
- Delivery-list/stage selector with separate demo scan state per list.
- Stage-aware filtering; Customer Pickup shows CPU orders only.
- Station selector with add-station support.
- Search and status filters.
- Exact barcode scans.
- Manual scan entry by order number and item number.
- Damaged-label recovery when the delivery list has one safe match.
- Unknown/ambiguous scans reject instead of guessing.
- Outbound scans automatically stage the matching item when staging was missed, with a non-blocking notice.
- Highlighted quantity status, progress, last scan, recent scans, and summary counts.
- Indian Trail bay map based on a generated snapshot of `Indian Trail Inventory Manager.xlsm`; regenerate the JSON layout after workbook layout changes.
- Indian Trail route flow, legend, search-to-bay scroll, and recent bay action feed.
- SQLite-backed scan state, audit events, undo, import/update JSON, print, and CSV export when launched with `server.py`.
- Login/session support with role-based permissions.
- Admin dashboard data for users, imports, exceptions, reports, global search, and bay status.
- Import preview validation before committing a delivery-list update.
- Exception center with review action.
- Indian Trail receive scans with automatic bay assignment, clear-bay actions, and SDI review marking.
- Local browser storage for static demo scan state.

See `SYSTEM_DESIGN.md` for the production database, multi-user scanning, Power Automate, and rollout design.

## Production Paths

### 1. Local/LAN Web App

Use a small web server with SQLite or PostgreSQL. Operators open the app from phones, tablets, or PCs on the plant network. This is the most independent path if a local machine or internal server can host it.

Best when:
- You want ownership without waiting on a vendor database.
- IT can allow one internal web app or server folder.
- You need fast scanning and audit history.

### 2. SharePoint-Backed Web App

Keep SharePoint Lists as the database and use a custom web front end. This avoids a new database purchase and fits the current Power Automate direction.

Best when:
- IT is more comfortable with Microsoft 365 tools.
- Authentication and permissions should stay in company accounts.
- You want less server maintenance.

### 3. Excel Bridge During Migration

Keep the current master workbook as the source of truth while the web app reads published JSON snapshots and writes scan events to a queue.

Best when:
- Operators need a better UI quickly.
- The workbook cannot be replaced all at once.
- You want a safe rollout with rollback.

## Production Requirements

- Replace the default admin password and set a real session secret.
- Add a production SQL Server/PostgreSQL/Azure SQL store adapter if IT wants a central database.
- Durable scan queue with retry.
- Audit log for every scan/edit.
- Offline-tolerant mobile queue.
- Expanded admin tools for routes, stages, bay rules, and scanner defaults.
- Backups and restore testing.
- Barcode recovery rules shared between server and client.
