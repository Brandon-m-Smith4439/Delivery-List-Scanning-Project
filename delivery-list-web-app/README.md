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
& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" .\server.py
```

Open:

```text
http://127.0.0.1:8765/
```

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
- Delivery-list/stage selector with separate demo scan state per list.
- Stage-aware filtering; Customer Pickup shows CPU orders only.
- Station selector with add-station support.
- Search and status filters.
- Exact barcode scans.
- Damaged-label recovery when the delivery list has one safe match.
- Unknown/ambiguous scans reject instead of guessing.
- Highlighted quantity status, progress, last scan, recent scans, and summary counts.
- Indian Trail bay-sort preview.
- SQLite-backed scan state, audit events, undo, import/update JSON, print, and CSV export when launched with `server.py`.
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

- Login and role permissions.
- Delivery-list import screen.
- Durable scan queue with retry.
- Audit log for every scan/edit.
- Offline-tolerant mobile queue.
- Admin tools for routes, stages, and scanner stations.
- Backups and restore testing.
- Barcode recovery rules shared between server and client.
