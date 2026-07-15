# Delivery List Scanner v062 Test Report

Date: 2026-07-15

## Result

**45 automated tests passed. No tests were skipped.**

SQLite remained the active/default database for all application integration and HTTP testing. The Azure SQL compatibility code was tested locally with `pyodbc 5.2.0`, `sqlglot 27.20.0`, fake ODBC cursors/connections, schema parity checks, and SQL translation tests. No claim is made that a live Azure SQL resource was deployed from this environment.

## Validation environment

- Python 3.13.5
- Node.js 22.16.0
- Chromium 144.0.7559.96
- pytest 9.0.2
- pyodbc 5.2.0
- sqlglot 27.20.0

## Executable coverage

Core Python statement coverage: **54%** across 6,326 executable statements.

| Module | Coverage |
|---|---:|
| `delivery_store.py` | 63% |
| `scanner_config.py` | 89% |
| `azure_sql_compat.py` | 49% |
| `migrate_sqlite_to_azure_sql.py` | 26% |
| `server.py` | 12% |

The low direct statement percentage in `server.py` reflects its large set of thin HTTP branches and printable HTML templates. Coverage is supplemented by a real HTTP end-to-end test, static verification of all frontend API references, verification that every `STORE.method()` call resolves to an implemented SQLite store method, and duplicate route-check detection.

## Functional areas tested

### Configuration, startup, and database lifecycle

- Fresh SQLite initialization.
- v060-created SQLite database upgrade and v062 startup.
- Packaged Windows BAT/PowerShell launcher presence and safety checks.
- Browser launch occurs only after a successful `/api/health` response.
- Durable startup traceback creation and launcher/server log paths.
- Python 3.10+ runtime validation in the launcher.
- SQLite connection and busy timeouts match the configured startup timeout.
- Existing-database schema upgrade behavior.
- SQLite remains the default unless Azure SQL is explicitly enabled.
- Repeated startup skips the expensive route-stage repair when rule/signature state is unchanged.
- Context-managed SQLite transactions close their underlying connections after commit/rollback.
- Health endpoint reports SQLite mode.
- Azure SQL dependency loading, SQL translation, row adapters, cursors, transactions, and connection-error behavior.
- Migration identifier quoting, SQLite/Azure column discovery, CLI flags, and dependency-safe table order.

### Imports and route authority

- JSON, CSV, XLSX, folder import, update, skip, preview, and hash behavior.
- CSV delivery dates from supported in-file headings.
- Customer Route Rules override conflicting source routes.
- Exact/longest customer rule matching.
- CPU-Air/Air-CPU Job Nr. override.
- CPU-IT/CPU-INT remains Indian Trail.
- Standard Indian Trail, Greenville, CPU, and DTC destination stage creation.
- Source route preservation.
- Route-rule changes and deletions reconcile existing active stage copies.
- Stage membership repair remains idempotent.

### Authentication and administration

- Login, logout, sessions, permissions, roles, users, activation/deactivation, deletion, password updates, and password reset.
- Station add/rename/remove.
- Customer route rule add/remove.
- Manual edit lookup values.
- Audit and admin summaries.
- Unauthorized HTTP access after logout.

### Main scanning workflow

- Valid scans, malformed barcodes, duplicate/over-quantity errors, exception creation, stage reset, and recent history.
- Outbound safety behavior after Staging.
- Undo and Redo quantity restoration.
- Redo events are recorded as `redo`, not new `scan` events.
- Manual/override paths exercised through store integration tests.
- Active scan data survives the shared workflow paths used by Rush acknowledgment.

### Racks and Outbound

- Rack assignment during Staging.
- Rack completion/uncompletion, departure, return, and Not On Way behavior.
- Outbound rack barcode response, destination, full rack quantity, and In Transit status.
- Rack sets, rack creation/edit/delete, item movement/clear, summary, and packing-list data.

### Indian Trail bays

- Layout loading/updating, group/bay positioning, create/delete, status changes, and assignment controls.
- Receive, manual assignment, move, clear, restore, scan-out, and Bay Check workflows.
- Restoring a cleared assignment respects non-null schema fields.
- Remembered manual-input and barcode rules.
- Auto-assignment settings.
- Stale-bay results and snooze handling.
- SDI Rush/Remake marking and removal.

### Rush/Remake and notifications

- Route-specific propagation through Staging, Outbound, and the correct destination stage.
- Priority delivery date and direct-to-truck persistence.
- Exact-item Rush printing.
- Multi-user notification creation and independent acknowledgment.
- Reimport preservation.

### Reports, print, and exports

- Summary/report data.
- CSV export.
- Single-list XLSX export.
- Multi-stage package XLSX export.
- Delivery-list print packages.
- Rack packing-list and barcode rendering helpers.
- Code 39 SVG and pagination helpers.
- Azure-compatible SQL schema table coverage.

### Real HTTP server test

A temporary real server process was started against a temporary SQLite database. The test exercised:

- `/api/health`
- session and login/logout
- customer route rule creation
- delivery-list import and detail loading
- scanning
- stations, racks, bays, layout, reports, admin, audit, and global search
- CSV, XLSX, and print-package responses
- authorization rejection after logout

The test process and its stdout/stderr handles are closed cleanly after completion.

## Static and duplicate-code checks

- Python AST parsing for every maintained module.
- Node JavaScript syntax validation.
- CSS parsing with no parser errors.
- No duplicate HTML IDs.
- No duplicate Python methods within a class.
- No duplicate top-level JavaScript function names.
- Every named Python function/method has an inline docstring.
- Every named JavaScript function has a nearby Purpose JSDoc note.
- Every frontend literal `/api/...` reference exists in `server.py`.
- Every `STORE.method()` HTTP delegation resolves to an implemented store method.
- Exact/prefix server route checks are unique within their HTTP method.
- v062 cache references are present.
- Windows launcher files are packaged and reference the correct PS1/server/log paths.
- The launcher checks health before opening the browser.
- The BAT preserves nonzero PowerShell failures instead of closing immediately.
- SQLite-default configuration is protected by regression test.

## Browser-rendered visual and interaction sweep

The visual test loaded the real `index.html`, injected the real `styles.css` and `app.js`, and supplied controlled backend responses through a mocked `fetch`. This avoids the environment restriction that blocks Chromium navigation to local HTTP addresses while still executing the actual browser code and layout cascade.

Validated at **1600×1000** and **1366×768**:

- Home page initializes without JavaScript page errors.
- Header height and layout remain usable.
- The full visible profile summary, including its right edge, opens the Sign out dropdown.
- Scan-page stage title and progress row do not overlap.
- Undo/Redo do not overlap the barcode input.
- Scanner buttons expose transitions/hover feedback.
- Chart title/subtitle do not overlap chart controls.
- Interactive chart SVG renders with usable canvas height.
- Bay Map opens with Outbound → In Transit → Received summary visible.
- Bay Map scanner has no internal vertical scrollbar.
- Physical bay sections render.
- Last Bay location renders as the primary readable value.

## Defects found during the v061 audit

1. CSV imports ignored an embedded delivery-date column.
2. Redo history was mislabeled as a new scan.
3. Restoring a cleared bay assignment wrote `NULL` into non-null cleared fields.
4. SQLite context-managed connections committed/rolled back but remained open.
5. The HTTP test process left stdout/stderr handles open after shutdown.

All five were corrected and protected by tests.


## v062 startup investigation

The reported production-PC crash was not reproducible with a fresh SQLite database or a database initialized by v060. The application process remained healthy in both cases. The investigation did identify a release/launcher reliability gap: v061 omitted the Windows launcher files, and the supplied external launcher opened the browser before health and discarded Python tracebacks when its console closed.

v062 therefore adds a supported launcher and durable diagnostics rather than claiming an unobserved database defect was fixed. A remaining machine-specific problem will now be captured in `logs/server-stderr.log` and `logs/startup-error.log` with the Python executable and database path.

## Documentation result

- 549 maintained Python functions/methods inventoried across core source, tests, and tools.
- 665 named JavaScript functions inventoried.
- 104 API route checks inventoried.
- 31 Azure SQL tables documented.
- 273 stable HTML IDs mapped to interface regions.
- 11 CSS ownership sections documented.

See `CODE_REFERENCE_v062.md` for the function-by-function map and `TESTING_v062.md` for release and floor-validation steps.

## Honest limitations

This sweep is comprehensive, but no finite automated suite proves every possible production data combination. The following still require controlled deployment validation:

- Real scanner hardware timing and focus behavior on the production Windows floor PC/Zebra devices.
- Real printers, print drivers, paper margins, and browser print-preview behavior.
- A live Azure SQL managed-identity connection and real SQLite-to-Azure cutover.
- Real SMTP delivery and customer mailbox behavior.
- Production shared-drive permissions, latency, and concurrent-user load.
- Visual review on every possible monitor scaling setting and browser build.

The included manual floor checklist should be completed before replacing the current production ZIP.
