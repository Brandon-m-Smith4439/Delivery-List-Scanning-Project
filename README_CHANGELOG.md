# Delivery List Scanner - Ongoing Changelog

This is the single maintained changelog for the project. New versions are added at the top. The retained history available in the current project begins with the v037-v039 work and continues through the current release. Earlier version details were not present in the supplied project history and are not reconstructed or guessed here.

---

# Delivery List Scanner - v064 Print Route Cleanup, Stable Language Layout, Save Confirmations, and Clean Launcher

Date: 2026-07-15

## Print/export route display

- Standard Indian Trail route values such as `IT`, `INT`, and `Indian Trail` remain stored internally for routing but now display as blank on delivery-list printouts and supported exports.
- CPU, DTC, GNV, and custom route codes remain visible so exception destinations stand out clearly.
- Rack packing lists and saved customer manifest print pages use the same public route-label helper rather than maintaining separate route-display rules.
- Blank Indian Trail cells remain truly blank instead of displaying a fallback dash.

## Fullscreen Scan-page history

- The main Scan page now shows five previous scans while fullscreen is active.
- Normal-window Scan history remains at two rows.
- Bay Map scan history remains unchanged.

## Spanish layout stability

- The language system now writes the active language to `body[data-language]` so CSS can reserve the correct space before translated controls reflow.
- The five primary page buttons use one predictable grid instead of wrapping unpredictably.
- Spanish navigation receives dedicated spacing and a controlled second utility row on narrower workstations.
- Mobile navigation uses a clean two-column grid so longer Spanish labels remain aligned and readable.
- At common 1366-pixel workstation width, the Spanish header uses a compact logo treatment so the translated navigation remains neat without an oversized first row.

## Shared save confirmation

- Added one `showSaveConfirmation()` helper that reuses the existing polished action-feedback dialog.
- Explicit save/create workflows now confirm success for stations, racks, rack sets, Bay Map groups/bays/layout, role permissions, bay scanner rules, customer email settings, customer route rules, users, passwords, user settings, and manual line-item edits.
- Scans, notification acknowledgments, background refreshes, and destructive actions do not use this save popup.
- Repaired the Lookup Manager form, whose existing submit handler referenced a missing `saveManualEditLookup()` function; lookup values now save correctly and use the same confirmation popup.

## Windows launcher and terminal behavior

- Python now starts with PowerShell `-NoNewWindow`, preventing the scanner launcher from creating a second visible terminal that can later steal focus.
- The supported release contains one launcher BAT: `Start-DeliveryScannerWebApp.bat`.
- If a separate terminal still opens with a working directory under another project, such as Showers Programmer, that terminal is being started by that other program or updater rather than this scanner launcher.

## Demo-data behavior

- Existing production databases are not seeded or refreshed from `sample-delivery-list.json`.
- Demo rows that may already have been inserted by an older release are not automatically deleted because the current database must be reviewed before any data can be classified safely as demo-only.

## Folder cleanup and documentation

- Added `README.md` as the concise local startup guide.
- Added `docs/FOLDER_CLEANUP_GUIDE.md` with exact keep/remove guidance.
- Consolidated current maintenance documents under `docs/` with stable filenames instead of adding another set of version-suffixed files.
- This `README_CHANGELOG.md` is now the one ongoing changelog; future releases should prepend their changes here.

## Database and deployment status

- SQLite remains the active/default backend.
- No schema migration was added in v064.
- Azure SQL remains opt-in and retains the same route-display, save, and startup behavior where applicable.

## Validation

- Full maintained validation: **50 tests passed with no skips**.
- Browser-rendered checks passed at 1600×1000 and 1366×768, including Spanish navigation geometry and five fullscreen recent-scan rows.
- Print helper tests confirm Indian Trail stays blank while CPU, DTC, and GNV remain visible.
- Windows launcher behavior is statically validated; one live floor-PC launch remains required because this environment is not Windows.

## Files edited

- `app.js`
- `styles.css`
- `server.py`
- `delivery_store.py`
- `index.html`
- `Start-DeliveryScannerWebApp.ps1`
- `README.md`
- `README_CHANGELOG.md`
- `docs/FOLDER_CLEANUP_GUIDE.md`
- `docs/AZURE_DEPLOYMENT.md`
- `docs/CODE_REFERENCE.md`
- `docs/TESTING.md`
- `docs/TEST_REPORT.md`
- `tests/test_static_integrity.py`
- `tests/test_core_helpers.py`
- `tests/test_azure_adapter_and_rendering.py`
- `tests/test_visual_smoke.py`
- `tools/generate_code_reference.py`
- `tools/run_full_validation.py`

---

# Delivery List Scanner - v063 Production Database Startup Collision Fix

Date: 2026-07-15

## Exact crash cause

The production traceback identified a real startup defect in `seed_demo_data()`:

- The existing project folder still contained `data/sample-delivery-list.json`.
- Startup treated that file as data that should be synchronized on every launch.
- Route/stage repair had previously moved one deterministic sample-derived line-item ID to another delivery-list stage.
- Demo reseeding saw a line-count mismatch, rebuilt the original list, and attempted to insert the same globally unique `line_items.id` again.
- SQLite correctly stopped startup with `UNIQUE constraint failed: line_items.id`.

The production database does not need to be deleted or replaced.

## Startup repair

- Demo/sample delivery-list data is now seeded only when the database contains no delivery lists.
- Once a database has real or previously imported lists, an old sample JSON file can no longer rewrite, refresh, or collide with those rows during startup.
- Required stations continue to seed normally even when demo delivery lists are skipped.
- This also removes unnecessary sample-list comparison work from normal production startup.

## Import and refresh collision guard

- Added one shared `available_line_item_id()` guard to the existing insertion workflow.
- Normal deterministic IDs remain unchanged when available.
- If an older stage move already owns that ID in another delivery list, the refreshed row receives a stable collision-safe suffix.
- A duplicate ID inside the same delivery list still raises an error rather than silently creating a duplicate line.
- The guard protects normal delivery-list refreshes as well as the startup condition that exposed the issue.

## Windows security warning

- The packaged BAT now removes the downloaded-file security marker from `Start-DeliveryScannerWebApp.ps1` before invoking it.
- This prevents the recurring `Run only scripts that you trust` / `Run once` prompt after extracting a downloaded ZIP.
- The existing execution-policy bypass, health wait, logging, and startup-error display remain in place.

## Validation

- Recreated the exact cross-list deterministic-ID collision in a temporary SQLite database.
- Confirmed repeated store initialization no longer attempts demo reseeding.
- Confirmed a deliberate refresh creates one collision-safe row without altering the older moved row.
- Started the real HTTP server against the collision database and received a healthy SQLite response.
- Full maintained validation: **47 tests passed with no skips**.

## Database and deployment status

- SQLite remains the active/default backend.
- No production data deletion is required.
- No schema migration was added in v063.
- Azure SQL remains opt-in and inherits the same collision-safe insertion and empty-database demo-seeding rules.

## Files edited

- `delivery_store.py`
- `Start-DeliveryScannerWebApp.bat`
- `index.html`
- `tests/test_store_workflows.py`
- `tests/test_static_integrity.py`
- `tools/generate_code_reference.py`
- `tools/run_full_validation.py`
- `AZURE_DEPLOYMENT.md`
- `README_CHANGELOG.md`
- `CODE_REFERENCE_v063.md`
- `TESTING_v063.md`
- `TEST_REPORT_v063.md`

---

# Delivery List Scanner - v062 Startup Crash Diagnostics and Windows Launcher Repair

Date: 2026-07-15

## Scope

- Used v061 as the baseline after the reported immediate Windows startup failure.
- SQLite remains the active/default backend. Azure SQL remains opt-in.
- No scanning, routing, rack, bay, Rush, printing, chart, or browser workflow was duplicated or replaced.

## What was found

- The v061 application server starts successfully in this environment with both a fresh SQLite database and a database initialized by v060, so the machine-specific exception could not be reproduced without the production database/runtime.
- The release ZIP did not include the BAT or PowerShell launcher used on the floor PC.
- The supplied launcher opened the browser before the server passed a health check.
- A Python startup exception caused the PowerShell window to close without preserving the traceback for the operator.
- The launcher preferred a machine-specific Codex runtime before the normal Windows Python launcher, which could select a stale or incomplete runtime on another computer.
- The existing health check expected text that the current `/api/health` response does not contain, so it could fail to recognize an already-running scanner instance.

## Windows startup repair

- Added `Start-DeliveryScannerWebApp.bat` to the release package.
- Added a documented `Start-DeliveryScannerWebApp.ps1` beside it.
- The launcher now validates that `server.py` is present before starting.
- Python selection now prefers:
  1. A project `.venv` runtime.
  2. The Windows `py -3` launcher.
  3. A normal `python` command.
  4. The Codex runtime only as the final fallback.
- Python must be version 3.10 or newer.
- The browser opens only after `/api/health` reports a healthy application.
- If the requested port belongs to an already-running Delivery List Scanner, the launcher opens that instance instead of starting another server.
- If another program owns the port, the launcher advances to the next available port.
- The launcher keeps the console attached to the Python process and reports an unexpected later shutdown.
- BAT-level failures preserve the window with `pause` instead of disappearing immediately.

## Durable startup diagnostics

The release now creates a `logs` folder at runtime containing:

- `launcher.log` — launcher decisions, runtime selection, port selection, and health status.
- `server-stdout.log` — database initialization and server startup milestones.
- `server-stderr.log` — Python errors and HTTP server diagnostics.
- `startup-error.log` — full Python traceback, Python executable/version, application root, database type, and database path.
- `delivery-scanner.pid` — current local server process ID while the launcher-managed server is running.

`server.py` now logs uncaught startup failures itself, so diagnostics remain available even when the failure occurs during database initialization or port binding.

## SQLite startup tolerance

- SQLite connections now use the configured database timeout during `sqlite3.connect()`.
- `PRAGMA busy_timeout` uses the same timeout value.
- A short-lived database lock from antivirus, backup software, or a recently stopped process waits for release instead of failing immediately.
- The existing WAL, foreign-key, connection-closing, schema-upgrade, and route-repair behavior remains unchanged.

## Startup visibility

`server.py` now emits flushed milestones for:

1. Beginning database initialization.
2. Completing database initialization.
3. Binding the configured host and port.
4. Confirming the running URL and active database mode.

These messages make it clear whether a failure occurred in SQLite initialization or HTTP port binding.

## Documentation and tests

- Updated the maintained code reference to v062.
- Added the six documented PowerShell launcher functions to the code reference.
- Added regression checks for packaged launcher files, health-before-browser ordering, durable logs, Python-version validation, SQLite busy timeout, v062 cache keys, and startup failure tracebacks.
- The complete suite now reports **45 passing tests with no skips**.
- Fresh SQLite startup and v060-to-v062 database upgrade startup both passed.

## Files added

- `Start-DeliveryScannerWebApp.bat`
- `Start-DeliveryScannerWebApp.ps1`

## Files edited

- `server.py`
- `delivery_store.py`
- `index.html`
- `tests/test_core_helpers.py`
- `tests/test_static_integrity.py`
- `tools/generate_code_reference.py`
- `tools/run_full_validation.py`
- `CODE_REFERENCE_v062.md`
- `TESTING_v062.md`
- `TEST_REPORT_v062.md`
- `AZURE_DEPLOYMENT.md`
- `README_CHANGELOG.md`

## Important operator note

Use the BAT included in v062 from the same folder as `server.py`. If startup still fails on the production PC, do not close the error window before reading it. The exact cause will also remain in the package's `logs` folder, especially `server-stderr.log` and `startup-error.log`.

---

# Delivery List Scanner - v061 Full Code Audit and Maintainer Documentation

Date: 2026-07-15

## Scope

- Completed a whole-project architecture, duplicate-code, persistence, route, scanner, rack, bay, print/export, notification, and browser-layout sweep using v060 as the baseline.
- SQLite remains the active/default backend. Azure SQL remains an explicit future cutover option.
- No parallel scanner, popup, chart, route, rack, bay, or database workflow was added.

## Function-by-function documentation

- Added `Purpose`, `Effects`, and `Flow` notes to every named Python function/method in the maintained source and regression suite.
- Added matching JSDoc notes to every named JavaScript function, including local workflow helpers.
- Added explicit ownership comments to the HTML page/modal sections, CSS feature sections, Azure SQL tables, container files, environment template, requirements, and test configuration.
- Added `CODE_REFERENCE_v061.md`, a generated maintenance reference containing the architecture, startup flow, Python functions, JavaScript functions, API routes, database tables, HTML anchors, CSS sections, callers, and safe-edit rules.
- Added `tools/generate_code_reference.py` so future coders can regenerate the reference after structural edits.

## Permanent regression suite

- Added a maintained pytest suite covering route authority, CSV/XLSX imports, authentication, sessions, roles, permissions, password reset, scans, duplicate/error handling, Undo/Redo, racks, rack transit, bays, layout editing, manual/remembered bay rules, Rush/Remake propagation, notifications, customer email settings, reports, print rendering, CSV/XLSX exports, SQLite-to-Azure SQL compatibility, and HTTP API behavior.
- Added browser-rendered visual and interaction checks using the real `index.html`, `styles.css`, and `app.js` with controlled API fixtures.
- Visual checks cover the header/profile click target, Scan panel title/progress clearance, Undo/Redo stacking, chart header/control spacing, chart SVG rendering, Bay Map route summary, last-bay readability, and internal-scroll prevention at 1600×1000 and 1366×768.
- Added static checks for Python/JavaScript syntax, duplicate HTML IDs, CSS parser errors, duplicate class methods, duplicate top-level JavaScript functions, frontend API path coverage, function-documentation coverage, v061 asset versions, and the SQLite-default setting.
- Added `tools/run_full_validation.py`, `tests/README.md`, and `TESTING_v061.md` as the maintained release-validation entry points.

## Defects found and corrected during the sweep

### CSV delivery date preservation

- CSV imports now honor an in-file delivery-date column before using the filename/current-date fallback.
- Supported headings include `deliveryDate`, `Delivery Date`, `Delivery Date:`, `delivery_date`, `Date`, and `date`.

### Undo/Redo history accuracy

- Redone scans are now recorded with event type `redo` rather than being mislabeled as new `scan` events.
- Later Undo and Redo operations correctly recognize both original scans and redone scans.

### Bay assignment restoration

- Restoring a previously cleared bay assignment now writes the schema-compatible empty-string cleared fields instead of `NULL` values that violated the existing non-null constraints.

### SQLite connection lifecycle

- Added one shared `ClosingSQLiteConnection` implementation.
- Every existing `with self.connect()` transaction now commits or rolls back and then closes the underlying SQLite connection.
- This prevents file-handle and connection buildup during long scanner shifts without rewriting individual store workflows.

### Test server resource cleanup

- The HTTP integration test now closes its subprocess stdout/stderr handles after shutdown, preventing validation-time descriptor warnings.

## Startup and database safeguards

- Added a regression test proving an unchanged second SQLite startup skips the full route-stage reconciliation.
- Preserved v060 Customer Route Rule authority and CPU-Air Job Nr. override behavior.
- Preserved `source_route`, `system_metadata`, idempotent repairs, and Azure SQL schema parity.
- No Azure SQL setting is enabled automatically.

## Files added

- `CODE_REFERENCE_v061.md`
- `TESTING_v061.md`
- `pytest.ini`
- `tests/README.md`
- `tests/conftest.py`
- `tests/test_core_helpers.py`
- `tests/test_store_workflows.py`
- `tests/test_extended_workflows.py`
- `tests/test_file_imports_and_sql_compat.py`
- `tests/test_azure_adapter_and_rendering.py`
- `tests/test_visual_smoke.py`
- `tests/test_server_http.py`
- `tests/test_static_integrity.py`
- `tests/test_visual_smoke.py`
- `tools/generate_code_reference.py`
- `tools/run_full_validation.py`

## Existing files reviewed and documented

- `app.js`
- `delivery_store.py`
- `server.py`
- `scanner_config.py`
- `azure_sql_compat.py`
- `migrate_sqlite_to_azure_sql.py`
- `azure_sql_schema.sql`
- `index.html`
- `styles.css`
- `Dockerfile`
- `.dockerignore`
- `.env.azure.example`
- `requirements.txt`
- `AZURE_DEPLOYMENT.md`
- `README_CHANGELOG.md`

## Validation result

- 42 pytest cases passed with no skips after loading the pinned `pyodbc` and `sqlglot` dependencies.
- Azure SQL translation and adapter tests passed locally; a live Azure SQL resource was not available and is not claimed.
- Python backend coverage measured 54% by executable statements across the core modules; the suite additionally performs static coverage of every named function, every browser function’s documentation, all frontend API path references, the schema, and critical rendered layouts.
- JavaScript syntax, Python compilation, CSS parsing, HTML ID uniqueness, duplicate-definition audits, real local HTTP API testing, SQLite integration workflows, browser-rendered visual smoke testing, asset-version checks, and release ZIP integrity all passed.
- This is a comprehensive automated and structural sweep, not a claim that every possible production data combination or live Azure environment has been exercised.

---

# Delivery List Scanner - v060 Customer Route Authority and Fast Startup

Date: 2026-07-15

## v060 Changes

### Customer Route Rules are now the primary source of truth

- Route resolution now happens only after the active database Customer Route Rules are loaded.
- The import parser no longer pre-resolves a route and accidentally makes that value look explicit before the database rules can run.
- Customer matching uses the customer-name field only.
- When multiple rules match, an exact normalized customer match wins; otherwise the most specific/longest matching pattern wins.
- Active customer rules override conflicting imported ROUTE values for CPU, DTC, Greenville, Indian Trail, and custom routes.
- The original imported ROUTE value is retained separately as `source_route`, allowing later rule changes or removals to reroute existing items safely.

### Job Nr. override is limited to CPU-Air routing

- Any capitalization or separator variation of CPU-Air or Air-CPU in Job Nr. routes the item to **Customer Pickup**.
- CPU-IT and CPU-INT continue to explicitly remain on **Indian Trail**.
- DTC and Greenville are no longer inferred from Job Nr.; those destinations come from Customer Route Rules, with the imported ROUTE field retained only as a fallback when no rule matches.
- Generic CPU text such as `CPUITEM` remains excluded by strict token matching.

### Missing destination stages repair automatically

- Existing items are reconciled against the active customer rules during the one required v060 upgrade pass.
- Missing Customer Pickup, BFS Greenville, DTC, or Indian Trail receiving copies are created or moved using the existing shared membership workflow.
- Staging and Outbound copies, scanned quantities, scan history, rack references, bay assignments, and audit references remain preserved.
- Saving or deleting a Customer Route Rule immediately reconciles existing active items so scanning and Print / Export use the updated destination without waiting for a reimport.

### Startup performance

- Removed the full route-stage repair from every application launch.
- Added one `system_metadata` signature containing the route-repair version and active customer rules.
- The repair runs only when that signature changes, such as after upgrading this version or editing route rules.
- The repair now loads active line items once, groups them in memory, and performs follow-up SQL only for items that actually need a route or stage change.
- A 5,000-item repeated-startup test completed in approximately 0.003 seconds after the initial signature was stored; a one-time 1,000-item legacy Greenville repair completed in approximately 0.4 seconds in the test environment.

### SQLite and Azure SQL readiness

- SQLite remains the active default backend.
- Added `line_items.source_route` and `system_metadata` to both the SQLite and Azure SQL schemas.
- Added `system_metadata` to the SQLite-to-Azure migration order.
- Azure SQL remains inactive unless `DLS_DATABASE_TYPE=azure-sql` is deliberately configured.

## Files Edited

- `delivery_store.py`
- `app.js`
- `azure_sql_schema.sql`
- `migrate_sqlite_to_azure_sql.py`
- `index.html`
- `AZURE_DEPLOYMENT.md`
- `README_CHANGELOG.md`

## Validation Performed

- Python compilation and JavaScript syntax validation.
- Fresh SQLite initialization and existing-v059 database upgrade testing.
- Customer-rule precedence tests with conflicting imported ROUTE values.
- CPU-Air Job Nr. override tests against a conflicting Greenville customer rule.
- Exact and longest customer-pattern selection tests.
- Immediate existing-item rerouting after adding and removing a customer rule.
- Original imported route restoration through the new `source_route` field.
- Standard CPU, Greenville, DTC, Indian Trail, and custom destination-stage creation tests.
- Print package, CSV export, and XLSX export tests for corrected destination lists.
- 5,000-item unchanged startup benchmark and 1,000-item legacy-route repair benchmark.
- Duplicate JavaScript function, Python method, and HTML ID audits.
- SQLite remains the reported active database mode.

---

# Delivery List Scanner - v059 Scanner Title, Outbound Rack Focus, and Transit Confirmation

Date: 2026-07-15

## v059 Changes

### Scan-page stage title no longer clips descenders

- Adjusted the existing combined scanner header instead of adding another title or progress block.
- Increased the title line height slightly and added a small amount of bottom breathing room so the `g` in **Staging** no longer clips into or behind the progress row.
- Preserved the compact title-above-progress layout introduced in v055.

### Outbound rack selector follows the scanned rack

- The Outbound rack-barcode response already identified the scanned rack, but the frontend did not apply that value to the existing Transportation Status selector.
- The Scan page now sets `selectedOutboundRackCode` from the successful rack response before the scanner panel renders.
- The rack list is refreshed after the Outbound scan so the selected rack immediately displays its updated **In Transit** status and piece count.
- No second rack selector or status workflow was added.

### Timed Outbound transit confirmation

- Reused the existing Indian Trail timed scan-confirmation presentation for Outbound rack releases.
- Extracted one shared mount, countdown, close, language, and custom-select lifecycle used by both the Indian Trail placement notice and the new Outbound notice.
- After a rack barcode is accepted at Outbound, a blue truck-themed timed notice confirms:
  - the rack code
  - the actual normalized destination
  - that the rack is in transit
  - the total number of pieces currently on the rack
- Indian Trail racks display **Rack [code] is on the way to Indian Trail**. Greenville, CPU, and DTC racks use their actual destination instead of showing an incorrect Indian Trail message.
- The older generic floating scan notice is suppressed for this rack-release event so the operator sees one clear confirmation rather than two overlapping notices.

### Outbound response details

- Extended the existing rack-scan response with `rackDestination`, `rackPieceCount`, and `outboundScannedQty`.
- These are response-only fields. No database schema, migration, or new API endpoint was added.
- SQLite remains the active default backend and Azure SQL remains opt-in.

## Files Edited

- `app.js`
- `delivery_store.py`
- `styles.css`
- `index.html`
- `README_CHANGELOG.md`

## Validation Performed

- JavaScript syntax validation with `node --check app.js`.
- Python compilation for the server, SQLite/Azure store layers, migration utility, and configuration.
- Temporary SQLite Outbound rack integration test verifying:
  - the rack changes from Closed to In Transit
  - the response returns the scanned rack code
  - the response returns the normalized Indian Trail destination
  - the response returns the total three-piece rack quantity
  - the response returns the three newly scanned Outbound pieces
- Static frontend checks confirming the scanned rack response updates the existing Outbound selector before rendering and invokes the shared timed confirmation.
- CSS parsing, balanced-brace validation, duplicate JavaScript function, Python method, and HTML ID audits.
- Updated cache-busting asset references to v059.

---

# Delivery List Scanner - v058 All Scans Event Colors and Route Stage Repair

Date: 2026-07-15

## v058 Changes

### All Scans import and update rows use their own colors

- Kept the existing All Scans event renderer and event classes; no second history table or event-style system was added.
- Import rows now use the existing import blue across the row divider, left event line, event badge, and completion indicator.
- Update rows now use the existing update purple across the row divider, left event line, event badge, and completion indicator.
- Import and update rows no longer inherit the generic successful-scan green presentation.
- Normal scans, manual scans, errors, undo, redo, and notices retain their existing colors.

### CPU, DTC, Greenville, and Indian Trail designations resolve consistently

- Reworked the shared route resolver used by imports, list generation, scanning filters, manual route rules, rack destinations, and print/export selection.
- `GRVLLE`, `GRVlle`, `GRVille`, `GRVle`, `GVlle`, `GNV`, `GRN`, and `Greenville` now resolve to the standard **BFS Greenville** stage.
- DTC designations such as `DTC`, `DTC - Air`, and Job Nr. suffixes containing a separated `DTC` token now resolve to **DTC - Deliver to Customer**.
- `CPU-Air`, `CPU - Air`, reversed `Air-CPU`, and equivalent separator/case variations resolve to **Customer Pickup**.
- `CPU-IT`, `CPU - IT`, `CPU-INT`, reversed forms, and equivalent separator/case variations resolve to **Inbound - Indian Trail**, not Customer Pickup.
- Strict token boundaries remain in place so unrelated text such as `CPUITEM` is not silently treated as a route designation.
- The browser route filters and the Python backend now use matching designation behavior.

### Existing SQLite data repairs itself on startup

- Added one idempotent route-stage reconciliation workflow to the existing store layer.
- On startup, the app canonicalizes legacy route values and verifies that each physical item has Staging, Outbound, and exactly one correct receiving-stage copy.
- Existing items previously placed in hidden custom stages such as `GRVLLE` or `DTC - AIR` are moved into the standard Greenville or DTC list.
- Existing generated `IT` fallbacks are corrected when the preserved Job Nr. contains a strong DTC, Greenville, or CPU-Air designation.
- Scanned quantities, scan events, rack references, bay assignments, and audit references are retained when the receiving-stage row moves.
- Empty legacy custom lists are naturally excluded by the existing list query because they no longer contain line items.
- New imports use the corrected resolver immediately, so the repair path is only active when existing data actually needs correction.

### Scan and print/export availability restored

- Standard destination list IDs and stage names are generated again for CPU, DTC, Greenville, and Indian Trail items.
- Operator stage-access checks now see the standard scanner names instead of inaccessible custom route names.
- Destination stages therefore appear in the Scan page, Print / Export GUI, CSV export, Excel export, and multi-stage print packages.
- Staging and Outbound continue to contain every route, while the receiving copy appears only in its resolved destination stage.

### Database and code-quality status

- SQLite remains the active and default database backend.
- Azure SQL remains opt-in; the shared reconciliation workflow is compatible with the existing Azure SQL adapter but no Azure activation setting changed.
- No database schema or API endpoint was added.
- The route repair uses the existing receiving-list movement implementation rather than creating a second item-copy or print workflow.
- Updated cache-busting asset versions to v058.

## Files Edited

- `app.js`
- `delivery_store.py`
- `styles.css`
- `index.html`
- `README_CHANGELOG.md`

## Validation Performed

- JavaScript syntax validation with `node --check app.js`.
- Python compilation for the server, SQLite/Azure store layers, migration utility, and configuration.
- Backend and frontend route matrices covering CPU-Air, CPU-IT/INT, DTC variants, Greenville/GRVlle variants, capitalization, separators, reversed CPU tokens, and false-positive protection.
- Temporary SQLite import test proving all six standard stages are generated and visible for a mixed-route delivery date.
- Print-package, CSV export, and XLSX export tests for Staging, Outbound, Indian Trail, Greenville, Customer Pickup, and DTC.
- Legacy-database repair test moving hidden Greenville and DTC custom-stage rows into their standard destination lists while preserving all stage copies.
- All Scans CSS precedence review confirming import blue and update purple override the generic successful-scan green row style.
- Duplicate named JavaScript function, Python method, HTML ID, and cache-reference audits.
- Local SQLite server health and frontend-asset smoke testing.
- ZIP content and integrity validation.

---

# Delivery List Scanner - v057 Expanded Charts, Compact Bay Scanner, and Reactive Controls

Date: 2026-07-15

## v057 Changes

### Expanded interactive Chart GUI

- Extended the existing SVG chart renderer and selection workflow rather than adding a second chart system.
- Added a **Date range** selector directly inside the Chart GUI with Today, Last week, Last 30 days, Last 90 days, Full year, and All lists options.
- The Chart GUI range and the dashboard range now use the same `overviewRange` state and report endpoint, preventing separate or conflicting date-filter implementations.
- Added **Delivery completion by list**, showing the completion percentage and scanned/open quantities for each delivery-list stage.
- Added **Open pieces by delivery list**, showing only lists that still have work remaining.
- Added **On-time completion by list**, using the existing on-time and late piece metrics.
- Added **Stage workload**, showing total, completed, and open piece volume by workflow stage.
- Kept the existing glass mix, stage completion, scanned/open work, operator activity, system activity, and remake charts.
- Percentage-based charts automatically use the bar view because a donut chart would incorrectly present percentages as parts of one total.
- Added a six-card summary strip with delivery percentage, pieces completed, open pieces, completed lists, on-time completion, and scan quality.
- Expanded the home dashboard range selector with Today and Last 90 days so the dashboard and Chart GUI expose the same supported ranges.
- Added Spanish translations and dynamic translation patterns for the new chart controls, summaries, and data details.

### Intentionally compact Bay Map scanner

- Added one fixed Bay Map-only compact presentation instead of restoring the removed viewport-measurement and balanced/compact/tight JavaScript system.
- Reduced vertical padding, gaps, route-card height, add/remove controls, target-bay row height, barcode row height, manual-scan height, last-scan card height, and recent-history row spacing.
- All Bay Map scanner controls and the Outbound → In Transit → Received route summary remain visible at all times.
- The compact presentation is stable on initial load and after scans; it does not change size based on content measurements.
- The main Scan-page scanner remains full-size.

### Scan-page Undo/Redo visibility and scanner feedback

- Removed the older negative label offset from the main Scan-page barcode heading so Undo and Redo no longer sit behind the barcode outline at certain display scales.
- Raised the existing Undo/Redo action row above the scan field with an explicit stacking order.
- Added polished hover, pressed, disabled, and keyboard-focus feedback to the existing Undo/Redo buttons.
- Added consistent movement, shadow, border, and focus feedback to scanner-panel buttons, barcode wrappers, Bay Map add/remove choices, and last-scan cards.
- Reused the existing buttons, barcode wrappers, and scanner forms; no duplicate controls or event handlers were added.

### Database and code-quality status

- SQLite remains the active and default database backend.
- Azure SQL remains available only for a deliberate future cutover.
- No database schema, API endpoint, migration, or server business logic changed in v057.
- Removed an existing duplicate assignment of `state.homeChartSelectedLabel` found during the chart review.
- Integrated the expanded chart grid into the existing current chart CSS block instead of adding another duplicate top-level chart-modal override.
- Updated cache-busting asset versions to v057.

## Files Edited

- `app.js`
- `styles.css`
- `index.html`
- `README_CHANGELOG.md`

## Validation Performed

- JavaScript syntax validation with `node --check app.js`.
- Python compilation for the server, SQLite/Azure database layers, migration utility, and configuration.
- Chart dataset and interaction unit tests for delivery completion, remaining work, on-time completion, stage workload, KPI calculations, selection details, sorting, and display limits.
- CSS parser validation with `tinycss2`.
- Duplicate named JavaScript function and HTML ID audits, plus a targeted audit confirming every new Spanish chart translation key is defined once.
- Static selector review confirming the new Bay Map compact rules are scoped to one new Bay Map class and do not reintroduce the removed JavaScript density system.
- Local server smoke testing confirming `/api/health` remains in `sqlite` mode and v057 frontend assets load.
- Headless Chromium visual testing was attempted, but the environment displayed an organization policy block for local URLs; no screenshot-based visual validation is claimed.
- ZIP content and integrity validation.

---

# Delivery List Scanner - v056 Rush Stage Propagation, Safe Acknowledgment, and Priority Placement

Date: 2026-07-15

## v056 Changes

### Rush printing now reflects the submitted change

- The existing Rush print workflow now opens a package containing only the physical items changed by the current Rush submission rather than every older Rush on one stage.
- Rush sheets are generated for every applicable stage copy of the item: Staging, Outbound, and the route-specific destination stage.
- The new priority delivery date is used in each Rush-sheet title while the original delivery-list date remains visible in the subtitle for reference.
- Direct-to-truck Indian Trail Rush sheets clearly state **Send straight to installer truck / skip bay**.
- Standard Indian Trail Rush sheets state **Receive into the indicated priority Rush bay**, while Staging, Outbound, Greenville, CPU, and DTC sheets state that the work must be expedited through that stage.
- The print URL uses the existing print-package endpoint with exact source-item filtering; no second print renderer or Rush-only endpoint was added.

### Acknowledge Rush opens the correct filtered delivery list safely

- Reworked the existing Scan-page Rush alert so **Acknowledge Rush & View** selects an affected delivery list that the current user can access and applies the existing **Rushes** filter immediately.
- The current affected list is retained when possible; otherwise the app selects the matching stage category, then Staging, then the first accessible affected stage.
- Every active scan request is now tracked through the existing `processScan()` path. Acknowledgment waits for active scans to finish before changing delivery lists.
- A barcode already typed into the Scan-page field but not yet submitted is processed before the redirect.
- The alert is not silently dismissed by Escape or backdrop clicks, so the per-user notification remains pending until acknowledgment succeeds.
- Scan-safety and Indian Trail placement dialogs remain above the Rush alert, allowing a scan that needs operator input to complete before redirecting.

### Rush status follows the correct route through production

- Marking an item as Rush now expands the selected physical item by its shared `source_id` and updates only its active stage copies.
- Indian Trail work is marked on Staging, Outbound, and Inbound - Indian Trail.
- Greenville work is marked on Staging, Outbound, and BFS Greenville.
- CPU work is marked on Staging, Outbound, and Customer Pickup.
- DTC work is marked on Staging, Outbound, and DTC - Deliver to Customer.
- Clearing Rush / Remake now clears the status, priority delivery date, and direct-to-truck instruction from all applicable stage copies.
- Rush/Remake markers, priority dates, and direct-to-truck instructions are preserved when an updated delivery-list file refreshes the same physical item.

### Indian Trail Rush receiving and placement

- Added one persisted item-level `priority_direct_to_truck` flag to the existing `line_items` table. Existing SQLite databases add the column automatically at startup, and the Azure SQL readiness schema contains the matching column.
- The direct-to-truck flag is accepted only when the affected route includes Indian Trail; Greenville, CPU, and DTC Rushes cannot accidentally inherit an Indian Trail truck instruction.
- The existing Indian Trail receive response now identifies whether the scanned item is Rush, its priority delivery date, and whether it must bypass bays.
- Direct-to-truck Rush items are received without a bay assignment and display a high-visibility instruction to send the glass straight to the installer truck.
- Only the affected direct-to-truck Rush item's active bay assignment is cleared; other pieces sharing the same Job Nr. remain in their bays.
- Non-direct Rush items display a distinct orange priority-placement popup with the required Rush bay and retain the existing bay-override control.
- Rush receives now create explicit Rush audit actions and scan-history messages for direct-to-truck and priority-bay handling.

### Database and code-quality status

- SQLite remains the active and default database backend. Azure SQL remains opt-in for a deliberate future cutover.
- Reused the existing Rush notification table, per-user acknowledgment receipts, print-package renderer, scan function, Rush filter, delivery-list activation, Indian Trail receive endpoint, and placement popup.
- Added one shared cross-stage item expansion helper and one shared affected-list context helper instead of duplicating stage-specific Rush implementations.
- Removed the now-unused `closeRushAlert()` helper after the alert became acknowledgment-only.
- Updated cache-busting asset versions to v056.

## Files Edited

- `app.js`
- `styles.css`
- `delivery_store.py`
- `server.py`
- `azure_sql_schema.sql`
- `index.html`
- `README_CHANGELOG.md`

## Validation Performed

- JavaScript syntax validation with `node --check app.js`.
- Python compilation for the server, SQLite/Azure database layers, migration utility, and configuration.
- Temporary SQLite integration tests for Indian Trail, Greenville, CPU, and DTC Rush stage propagation.
- Exact-source Rush print-package tests across Staging, Outbound, and destination sheets.
- Rush print HTML checks for new/original delivery dates, direct-to-truck handling, priority-bay handling, and exclusion of unrelated Rush items.
- Indian Trail receive tests for direct-to-truck and priority-bay Rush items.
- Bay-assignment scope test confirming a direct-to-truck scan does not clear a non-Rush sibling item sharing the same job.
- Reimport preservation tests for Rush markers and priority dates across all applicable stages.
- Existing SQLite schema-upgrade test for the new `priority_direct_to_truck` column.
- Duplicate named JavaScript function, Python class-method, and HTML ID audits.
- CSS parser validation, local SQLite server health testing, frontend asset checks, and ZIP integrity validation.

---

# Delivery List Scanner - v055 Combined Scanner Header and Full-Size Panels

Date: 2026-07-15

## v055 Changes

### Combined Scan-page title, quantity, and progress

- Moved the active stage title into the existing navy scanner header instead of leaving it in a separate row below the progress section.
- The title now appears first, with the stage quantity and progress bar sharing one compact row directly beneath it.
- Reused the existing `stageHeading`, `progressText`, and `progressFill` elements and rendering functions; no second title or progress component was added.
- Reduced the scanner panel's normal vertical footprint while keeping the stage name, exact scanned quantity, completion percentage, and progress bar clearly visible.
- Added a narrow-screen fallback that stacks only the quantity and progress bar when horizontal space is genuinely limited.

### Removed automatic scanner-panel condensation

- Removed the JavaScript viewport-height measurement, animation-frame scheduler, delayed settling timer, and balanced/compact/tight class workflow.
- Removed the corresponding height-density CSS rules for both the Scan-page and Bay Map scanner panels.
- Scanner panels now keep their full-size controls and information on initial load, after list changes, after scans, during fullscreen changes, and when the header wraps.
- The page remains the only vertical scroll surface. The scanner panels do not create internal scrollbars and no operational sections are hidden based on viewport height.
- The Bay Map's Outbound → In Transit → Received route summary remains permanently available because there is no longer a tight mode that can alter or hide it.
- Kept the existing live sticky-header offset calculation so both scanner panels still remain below the application header in normal and fullscreen modes.

### Database and code-quality status

- SQLite remains the active and default database backend.
- Azure SQL remains available only through a deliberate future environment change.
- No database schema, API endpoint, migration, or business workflow changed in v055.
- Removed the obsolete density state fields, helper functions, lifecycle calls, and CSS selectors rather than leaving unused duplicate sizing code behind.
- Removed an older duplicate Scan-page header CSS override and retained one current header implementation.

## Files Edited

- `app.js`
- `styles.css`
- `index.html`
- `README_CHANGELOG.md`

## Validation Performed

- JavaScript syntax validation with `node --check app.js`.
- Python compilation for the server, SQLite/Azure database layers, migration utility, and configuration.
- CSS balanced-brace validation.
- Duplicate named JavaScript function and HTML ID audits.
- Static checks confirming all density state, functions, class names, and lifecycle calls were removed.
- Static DOM-order check confirming the stage title appears above the quantity and progress bar inside one scanner header.
- Local server smoke testing confirming `/api/health` remains in `sqlite` mode and the v055 frontend assets load.

---

# Delivery List Scanner - v054 Initial Scanner Sizing and Bay Route Visibility

Date: 2026-07-15

## v054 Changes

### Bay Map route summary now appears on initial load

- Traced the missing Outbound → In Transit → Received summary to the existing height-density workflow rather than adding another Bay Map header component.
- The previous measurement could immediately apply balanced, compact, and tight classes during the same initial pass. Tight mode then hid the route details until a later scan caused the panel to be measured again.
- Reworked the existing density calculation to measure the full panel once and apply cumulative modes from defined overflow ranges instead of repeatedly shrinking and remeasuring against a two-pixel threshold.
- The Bay Map route summary now remains visible in normal, balanced, compact, and tight layouts.
- Tight mode uses smaller route cards and text rather than removing the operational Outbound, in-transit, and Received information.

### Full-size scanner initialization and list switching

- Added one shared density scheduler for the Scan page and Bay Map scanner panels.
- Page changes, delivery-list changes, and fullscreen changes now immediately clear prior density classes so the newly displayed scanner starts at its full width and height.
- Density is recalculated after two animation frames, allowing the visible page, list-specific controls, fonts, and current scanner content to finish laying out before the panel is measured.
- Added one delayed settling measurement for asynchronous list and Bay Map content so a stale initial measurement cannot remain after data finishes rendering.
- The existing header `ResizeObserver` now also remeasures scanner density after the sticky header wraps or changes height, keeping the available-height calculation aligned with the actual header.
- The Scan page now avoids its previous duplicate render when `activateList()` navigates to the page; `showPage()` performs the single final render with the full-size reset.
- Resizing still expands or condenses the panels automatically, but the page can tolerate a modest amount of vertical continuation before stronger compact modes are used. This keeps the scanner larger while preserving the existing no-internal-scroll behavior.

### Database and duplicate-code status

- SQLite remains the active and default database backend.
- Azure SQL remains opt-in and ready for a later deliberate cutover.
- No database schema, API endpoint, or migration changed in v054.
- Reused the existing Bay Map route component, scanner panels, page lifecycle, list activation workflow, and density classes.
- Added one density scheduler and removed the duplicate Scan-page render during navigation instead of adding page-specific sizing systems.
- Removed three older duplicate Spanish translation keys (`Truck`, `Rack Sets`, and `Selected Rack`) while preserving the accented/final translations that already won at runtime.

## Files Edited

- `app.js`
- `styles.css`
- `index.html`
- `README_CHANGELOG.md`

## Validation Performed

- JavaScript syntax validation with `node --check app.js`.
- Python compilation for the server, SQLite/Azure database layers, migration utility, and configuration.
- CSS balanced-brace validation.
- Duplicate JavaScript function, Python method, HTML ID, and translation-key audits.
- Scanner-density unit checks covering full, balanced, compact, and tight overflow ranges.
- Static CSS check confirming tight mode no longer hides `#bayPanelRouteMini`.
- Static lifecycle checks confirming Scan-page list changes and Bay Map page entry reset density before settled measurement.
- Local server smoke testing confirming `/api/health` remains in `sqlite` mode and the v054 frontend assets load.
- Headless Chromium visual testing was attempted, but this execution environment blocks browser navigation to local URLs; no screenshot-based validation is claimed.

---

# Delivery List Scanner - v053 Bay History Location Editing and Scanner Input Polish

Date: 2026-07-15

## v053 Changes

### Change Bay Map locations from scan history

- Kept the existing `/api/indian-trail/move` endpoint, Bay Map assignment mover, confirmation popup, permission checks, and history refresh path; no second move workflow was added.
- Made the existing location-changing control clearly available from the Bay Map scanner's large last-scan card.
- Added the same current-location control to both recent Bay Map scan rows.
- Expanded **All Bay Scans** so active items can be moved directly from the full Indian Trail history GUI.
- The full history table now separates the bay recorded by the historical event from the item's current active location.
- After a move, the Bay Map, last scan, recent scans, and open All Bay Scans GUI refresh through the existing shared Bay Map refresh workflow.
- Items that are no longer assigned to a bay show a read-only status instead of an unusable location selector.
- Users without `move_bay` or `indian_trail_receive` permission see the current location as read-only.
- Updated the existing Spanish translation map for the new current-location labels without adding a second translation system.

### Professional scanner barcode fields

- Updated the existing shared `.scan-input-wrap` styling used by the Scan page and Bay Map scanner instead of adding separate input components.
- Removed native input borders, focus rings, background rectangles, margins, and corner radii that could paint white edges outside the blue scanner outline.
- The rounded wrapper now owns the complete background, clipping, border, and focus state.
- Kept the barcode icon, text entry, Bay Map undo/redo buttons, scanner sizing, and keyboard focus behavior unchanged.

### Database and duplicate-code status

- SQLite remains the active and default database backend.
- Azure SQL remains opt-in and ready for a later deliberate cutover.
- No database schema or migration changed in v053.
- Reused one Bay Map move endpoint, one document-level location-change listener, one confirmation popup, one Bay Map refresh workflow, and one shared scanner-input component.
- Removed 56 redundant Spanish translation entries while preserving the same final translations that were already winning at runtime.

## Files Edited

- `app.js`
- `index.html`
- `styles.css`
- `README_CHANGELOG.md`

## Validation Performed

- JavaScript syntax validation with `node --check app.js`.
- Python compilation for the server, SQLite/Azure database layers, migration utility, and configuration.
- CSS balanced-brace validation.
- Duplicate JavaScript function, Python method, HTML ID, and translation-key audits.
- Static checks confirming the last-scan card, recent-scan rows, and All Bay Scans GUI all use the same `data-bay-event-move` workflow.
- Static checks confirming All Bay Scans displays both historical scanned bay and current active location.
- Static checks confirming both scanner text inputs are borderless, transparent, and clipped inside the shared wrapper.
- Local server smoke testing in SQLite mode.
- ZIP integrity and package-content validation.

---

# Delivery List Scanner - v052 Chart Colors, Scanner Fit, and Bay History Readability

Date: 2026-07-15

## v052 Changes

### Colored full Statistics Chart GUI

- Kept the existing interactive SVG chart renderer and corrected its shared color scope instead of adding another chart implementation.
- Extended the existing chart palette from 8 to 10 distinct colors for bars, donut slices, and legend markers.
- Applied the same palette to both the dashboard glass-mix chart and the full Chart GUI.
- Fixed the full Chart GUI header layout so the eyebrow, title, subtitle, filters, result text, and chart canvas each receive their own grid row.
- Removed the inherited fixed 58-pixel modal header row that caused the text at the top of the Chart GUI to overlap.
- Kept the chart canvas as the only scrollable area inside the modal when a large data set requires additional room.

### Larger scanner-panel fit before compact mode

- Kept the existing shared scanner-density workflow and added one gentle `is-height-balanced` stage before compact and tight modes.
- The normal Scan-page and Bay Map panels now retain larger progress bands, history cards, inputs, and summary cards on marginal screen heights.
- Strong compact spacing is only applied when the balanced layout still does not fit below the live header.
- Preserved the no-internal-scroll behavior for both scanner panels.
- Increased the usable bottom allowance by four pixels while retaining the existing sticky-header measurement.

### Bay Map last-scan redesign

- Reworked the existing Bay Map last-scan card instead of adding another history component.
- Promoted the bay location into a large, high-contrast primary field that is readable at a glance.
- Kept action, order, time, status, and Move controls in the same card as secondary details.
- Added a hover title for long bay names so the complete location remains available when the visible label is truncated.
- Added balanced, compact, tight, and narrow-screen layouts so the larger location remains usable without reintroducing panel scrolling.
- Added the Spanish translation for `Last bay location` through the existing translation system.

### Database and duplicate-code status

- SQLite remains the active and default backend; no database configuration or schema was changed in v052.
- Azure SQL remains available only for a deliberate future cutover.
- Reused the existing chart modal, SVG renderer, scanner-density helper, Bay Map history renderer, custom Move select, and translation observer.
- Added no duplicate JavaScript function declarations, Python methods, HTML IDs, or translation keys.

## Files Edited

- `app.js`
- `index.html`
- `styles.css`
- `README_CHANGELOG.md`

## Validation Performed

- JavaScript syntax validation with `node --check app.js`.
- Python compilation for the server, SQLite/Azure database layers, migration utility, and configuration.
- CSS parsing and balanced-brace validation.
- Duplicate JavaScript function, HTML ID, and translation-key audits.
- Static checks confirming the full chart has 10 scoped colors and a four-row modal layout.
- Static checks confirming the scanner density order is normal, balanced, compact, then tight.
- Static checks confirming the Bay Map last card keeps one set of the existing history element IDs.
- Local server smoke test confirming `/api/health` remains in `sqlite` mode and the v052 frontend assets load.
- ZIP integrity and package-content validation.
- Chromium visual automation was attempted, but Chromium could not complete local rendering in this execution environment; no screenshot-based validation is claimed.

---

# Delivery List Scanner - v051 Profile Hitbox, Scan-Page Rush Alerts, and Priority Delivery Dates

Date: 2026-07-15

## v051 Changes

### Reliable profile-menu click area

- Kept the existing native `details` / `summary` profile dropdown instead of adding another menu toggle implementation.
- Made the full visible profile control the click target, including the avatar, display name, role text, and dropdown chevron.
- Disabled pointer interception on the decorative child elements so clicks consistently reach the existing summary control.
- Preserved the existing click-away close behavior and the single Sign out action.

### Rush alerts for every active user on the Scan page

- Kept the existing Rush notification tables, polling endpoint, receipt tracking, queue, and Rush popup; no second notification system was added.
- Rush notifications are now left pending for every active user, including the user who marked the Rush.
- Alerts are only presented while the user is on the Scan page, matching the production scanning workflow.
- Users already on the Scan page receive the alert through the existing polling cycle.
- Users on another page keep the alert pending and receive it immediately when they open the Scan page.
- Each user acknowledges the notification independently, so one user's acknowledgment does not hide it for anyone else.
- The Rush popup now includes the Job Nr., order, affected item numbers, customer, route, new delivery date, previous delivery date when changed, product/size summary, reason, priority-item count, and submitting user.
- Expanded the existing Rush popup layout to handle the additional details without clipping long values.

### Rush / Remake delivery-date control

- Added a date field to the existing SDI Rush/Remake GUI.
- Opening the GUI for a selected bay assignment prefills the item's current effective delivery date.
- The user can keep the current date or select a new priority delivery date before marking Rush or Remake.
- Added the item-level `priority_delivery_date` field rather than changing an entire delivery list's date.
- The original delivery-list date remains intact, while the Rush/Remake item can carry an earlier or corrected priority date.
- The new date is shown in the success confirmation, the current Rush/Remake list, and the Rush alert sent to users.
- Removing the Rush/Remake mark clears the item-level priority-date override and returns the item to its original delivery-list date.
- Priority delivery dates are preserved when an existing delivery list is refreshed or re-imported.

### SQLite and Azure SQL readiness

- SQLite remains the default and active database backend.
- Added the new column through the existing idempotent SQLite migration path, so an existing local database upgrades automatically at startup.
- Added the matching Azure SQL schema column and kept the shared schema-migration path ready for a future Azure cutover.
- No environment setting was changed to activate Azure SQL.

### Duplicate-code prevention

- Reused the existing native profile dropdown, Rush popup, notification polling, database notification receipts, SDI form, action-feedback popup, schema migration, and import-refresh workflows.
- Added no duplicate JavaScript function declarations, top-level declarations, Python class methods, or HTML IDs.
- Added no new duplicate translation keys compared with v050.

## Files Edited

- `app.js`
- `delivery_store.py`
- `index.html`
- `styles.css`
- `azure_sql_schema.sql`
- `README_CHANGELOG.md`

## Validation Performed

- JavaScript syntax validation with `node --check app.js`.
- Python compilation for the server, SQLite/Azure database layers, migration utility, and configuration.
- CSS parsing with no syntax errors.
- Duplicate JavaScript function, top-level declaration, Python class-method, and HTML ID audits.
- Comparison against v050 confirming no new duplicate translation keys were introduced.
- SQLite schema-upgrade test confirming an existing database receives `priority_delivery_date` automatically.
- Multi-user Rush notification test confirming both the submitter and another active user receive the same notification and acknowledge it independently.
- Rush payload test covering the new date, previous date, item numbers, product/size details, reason, route, and submitting user.
- Rush removal test confirming the priority-date override is cleared.
- Delivery-list refresh test confirming the priority date survives a replace/update import.
- Local server smoke test confirming `/api/health` reports `mode: sqlite` and the frontend assets load.
- A visual browser test was not available in this execution environment; no screenshot-based validation is claimed.

---

# Delivery List Scanner - v050 Interactive Charts, No-Scroll Scanner Panels, and Insertable Bay Map Layout

Date: 2026-07-15

## v050 Changes

### SQLite remains active by default

- Kept `DLS_DATABASE_TYPE` defaulted to `sqlite`; this release does not automatically enable Azure SQL.
- The existing local SQLite database remains the active source of truth until the Azure deployment is deliberately configured with `DLS_DATABASE_TYPE=azure-sql`.
- Updated the Azure deployment guide to clearly separate current SQLite operation from the future Azure SQL cutover.
- Kept the existing Azure SQL adapter, schema, migration utility, container, and deployment files ready for the later transition.

### Real interactive Statistics Chart GUI

- Replaced the simulated CSS bar and donut displays in the full Chart GUI with real responsive SVG charts.
- Added chart axes, grid lines, scaled bars, true donut slices, hover titles, keyboard focus, and accessible labels.
- Bars, donut slices, and legend rows can now be selected to show the category value, percentage of the displayed total, and detail text.
- Preserved the existing metric, chart style, sort, display-limit, and label-filter controls so the chart can be manipulated without adding a second chart workflow.
- Added Spanish translations for the new chart controls, selected-category panel, chart descriptions, and dynamic result text.

### Scanner panels without internal scrolling

- Removed the remaining Scan-page and Bay Map scanner-panel max-height/vertical-scroll rules, including older overridden sizing rules.
- The scanner cards now use the page as the only vertical scroll surface instead of creating a nested scrollbar.
- Added one shared viewport-density helper for both scanner cards. It measures the live header and available screen height, then applies compact or tight spacing only when required.
- Condensed progress bands, scan inputs, manual controls, scan-history cards, recent rows, and summary cards without hiding the operational controls.
- Kept the scanner cards below the live sticky header in normal and fullscreen modes.

### Fullscreen-only Scan-page history increase

- The main Scan page still shows the latest 2 prior scans in normal windowed mode.
- The main Scan page now shows the latest 4 prior scans while fullscreen is active.
- The Bay Map scanner remains at the latest 2 bay actions.
- Entering or exiting fullscreen rerenders the recent-scan table and recalculates panel density immediately.

### Redesigned Edit Map ordering

- Replaced the expanded live bay-group cards in Edit Map with compact layout cards containing bay, occupancy, piece, and order counts.
- Added visible insertion zones at the top, between every group, and at the bottom of each map column.
- Dragging a group to an insertion zone now shifts neighboring groups and preserves their order instead of displacing an occupied position into Holding.
- Added up, down, left, and right buttons for precise one-step movement.
- Corrected same-column insertion indexing so moving a group downward or between nearby groups lands in the intended position.
- No-op movements no longer create redundant undo-history entries.
- Kept the temporary Holding Area and the existing Save, Cancel, Undo, and Redo workflow.

### Duplicate-code prevention and cleanup

- Reused the existing chart modal, translation observer, fullscreen listener, bay layout draft, undo/redo stacks, and scanner render paths.
- Added one chart renderer, one scanner-density helper, and one bay-group insertion helper rather than page-specific duplicates.
- Removed obsolete scanner max-height variables and older nested-scroll overrides that were superseded by the shared density system.
- Removed the obsolete `moveBayGroup()` and `swapBayGroups()` functions from the previous Edit Map workflow, and renamed the remaining Holding helper to match its single responsibility.
- Removed a duplicated Bay Map source comment and avoided duplicate JavaScript function declarations or HTML IDs.

## Files Edited

- `app.js`
- `styles.css`
- `index.html`
- `AZURE_DEPLOYMENT.md`
- `README_CHANGELOG.md`

## Validation Performed

- JavaScript syntax validation with `node --check app.js`.
- Python compilation for the server, SQLite/Azure database layers, migration utility, and configuration.
- CSS parsing with no syntax errors.
- Duplicate JavaScript function declaration and duplicate HTML ID audits.
- Confirmed the configuration still starts in SQLite mode by default.
- Local server smoke test confirming `/api/health` reports `mode: sqlite` and the v050 frontend assets load.
- Interactive SVG bar and donut chart markup tests.
- Edit Map regression tests for insertion above, below, and between groups; same-column downward movement; arrow movement; and no-op undo suppression.
- Static check confirming the Bay Map recent history remains limited to two actions.
- Browser visual automation was attempted, but the execution environment blocks Chromium from loading local and file URLs; no visual-browser validation is claimed.

---

# Delivery List Scanner - v049 Fullscreen Consolidation and Azure SQL Integration

Date: 2026-07-14

## v049 Changes

### Removed the duplicate fullscreen-resume popup

- Confirmed that the project already had the polished `showActionFeedback()` fullscreen recovery popup used after printing.
- Removed the v048 refresh-specific `confirmWebAppAction()` fullscreen prompt and its duplicate Resume/Continue labels.
- Added one `showFullscreenRecoveryPrompt()` helper that uses the existing action-feedback popup.
- Both print recovery and refresh recovery now call the same helper and the same popup component.
- Automatic fullscreen restoration is still attempted first. The popup only appears when the browser requires a new click.
- Kept one fullscreen refresh session-storage flag and one fullscreen recovery UI path.

### Azure SQL database integration

- Implemented `AzureSqlDeliveryStore` as a real selectable database backend.
- `DLS_DATABASE_TYPE=azure-sql` now selects Azure SQL instead of raising `NotImplementedError`.
- Preserved one copy of all scan, import, rack, bay, user, reporting, and notification business rules.
- Removed 11 older customer-email method copies that were byte-for-byte equivalent in `BaseDeliveryStore` and `SQLiteDeliveryStore`; SQLite and Azure SQL now inherit the single shared implementation.
- Added `azure_sql_compat.py`, a pyodbc-backed connection adapter that translates the limited SQLite dialect used by the existing business layer into T-SQL.
- Added support for SQLite-style `LIMIT`, `INSERT OR IGNORE`, `ON CONFLICT`, row mappings, identity values, transactions, and qmark parameters on Azure SQL.
- Added an idempotent `azure_sql_schema.sql` containing the full application schema and indexes.
- Added `DLS_DATABASE_AUTO_SCHEMA` so the app can create/update the schema during the first deployment and run with reduced database permissions afterward.
- Added Azure SQL health output showing the active Azure database and server.
- Replaced the remaining runtime `sqlite3.Row` type check in rack destination routing with one shared row accessor that supports SQLite rows, Azure SQL rows, and dictionaries.

### Azure hosting and migration files

- Added a production container `Dockerfile` with Microsoft ODBC Driver 18 for SQL Server.
- Added `requirements.txt` for `pyodbc` and `sqlglot`.
- Added `.env.azure.example` with managed-identity Azure SQL settings.
- Added coordinated `PORT=8000` and `WEBSITES_PORT=8000` settings for the application process and App Service container routing.
- Added `.dockerignore` to keep local databases, caches, secrets, and ZIP files out of the image.
- Added `migrate_sqlite_to_azure_sql.py` to initialize the Azure schema and copy the current SQLite data while preserving identity IDs.
- Added `AZURE_DEPLOYMENT.md` with the full deployment, managed identity, migration, Azure Files, staging-slot, backup, and rollout process.
- Updated frontend cache versions to v049.

### Cross-database SQL cleanup

- Replaced the SQLite-only `GROUP_CONCAT(DISTINCT ...)` list query with a shared distinct glass-type query.
- Corrected aggregate `GROUP BY` and `HAVING` clauses so they are valid in both SQLite and Azure SQL.
- Reworked bay capacity selection and in-transit rack selection to avoid SQLite-only aggregate behavior.
- Replaced the remaining SQLite `date('now')` report filters with an explicit UTC date parameter shared by both database engines.
- Kept the local SQLite backend as the default for local development and offline testing.

## Files Added

- `azure_sql_compat.py`
- `azure_sql_schema.sql`
- `migrate_sqlite_to_azure_sql.py`
- `requirements.txt`
- `Dockerfile`
- `.dockerignore`
- `.env.azure.example`
- `AZURE_DEPLOYMENT.md`

## Files Edited

- `app.js`
- `delivery_store.py`
- `scanner_config.py`
- `server.py`
- `index.html`
- `README_CHANGELOG.md`

## Validation Performed

- JavaScript syntax validation with `node --check app.js`.
- Python compilation for the server, configuration, SQLite/Azure stores, compatibility adapter, and migration utility.
- Duplicate JavaScript function and top-level variable declaration audit.
- Python duplicate-definition audit plus an exact-body comparison between the base and SQLite stores, confirming the 11 redundant methods were removed.
- Fullscreen audit confirming one recovery helper and removal of the refresh-specific confirmation popup.
- SQLite initialization and flexible CPU route regression checks.
- Local HTTP server smoke test for `/`, `/api/health`, and static assets.
- Static translation of all literal database statements in `delivery_store.py`, including all upsert statements.
- Parameter-order regression test for SQLite `LIMIT ?` conversion to Azure SQL `TOP`.
- Azure MERGE generation checks for delivery lists, bays, racks, rack items, settings, notifications, and security seed data.
- Azure SQL schema/table/column coverage checks, including every base SQLite column across all 30 tables.
- Azure SQL row-compatibility regression check for shared rack destination routing.
- A live Azure SQL connection was not executed because Azure credentials and a target database were not provided in this chat.

---

# Delivery List Scanner - v048 Flexible CPU Input, Fullscreen Refresh Recovery, Spanish Coverage, and No Rack

Date: 2026-07-14

## v048 Changes

### Flexible CPU-Air and CPU-IT Job Nr. matching

- CPU route hints in Job Nr. are now case-insensitive and tolerate common human spacing or separator variations.
- Customer Pickup examples now recognized include `cpu-air`, `CPU - AIR`, `cpu_air`, `CPU/AIR`, `CPU.AIR`, long-dash variations, and the reversed `AIR - CPU` form.
- Indian Trail examples now recognized include `cpu-it`, `CPU - IT`, `cpu_int`, `CPU / INT`, and reversed `IT - CPU` or `INT - CPU` forms.
- Token boundaries prevent unrelated values such as `CPUITEM` or `CPUAIRPORT` from being misclassified.
- The explicit ROUTE column remains authoritative, preserving the routing order established in v047.
- The browser and backend now use matching route-resolution behavior.

### Refresh button with fullscreen recovery

- Added a dedicated Refresh button beside the language and fullscreen controls.
- Refreshing while fullscreen records a one-time fullscreen-resume request for the newly loaded page.
- The app first attempts to restore fullscreen automatically.
- When the browser requires a new user gesture, the app opens its native styled confirmation popup asking whether to resume fullscreen.
- Declining the prompt continues in normal windowed mode without repeatedly prompting.
- English and Spanish labels are included for the refresh control and fullscreen recovery popup.

### Expanded Spanish coverage for operational names

- Added exact Spanish labels for all standard delivery-list stages, including Staging, Outbound, Indian Trail Inbound, BFS Greenville, Customer Pickup, and DTC.
- Added dynamic translation for date-prefixed stage headings and stage-status summaries.
- Standard rack display names now translate dynamically, including names such as `Rack 1 Steel`, wood/aluminum/coral variants, and `Truck / No Rack`.
- Standard bay display names and gray category subtitles now translate, including spaced, dashed, and underscored names such as `Standard-01`, `Tall 02`, `BFS Mirrors_3`, and `Showers-12`.
- Added translations for common bay statuses and operational labels such as Spacer, Mixed, Hold, Scan Blocked, and Manual.
- The existing centralized translation observer remains the only translation path; no duplicate page-specific translation system was added.

### No Rack scanning option

- Added `No Rack - Leave location blank` to the main Staging transportation selector.
- Selecting No Rack sends an intentionally blank rack assignment instead of a fake rack code.
- The scan still increments the Staging scanned quantity, but no `rack_items` record is created.
- The line's Location value remains blank.
- Rack completion and packing-list actions are disabled while No Rack is selected.
- A clear status message explains the blank-location behavior in English or Spanish.
- Rack-page selection state remains independent from the main scanner selection so the new option does not interfere with rack management.

## Exact Code Locations in v048

### `app.js`

- Operational Spanish translations: `SPANISH_OPERATIONAL_TEXT` near line 1590.
- Shared bay-name translation mapping: `SPANISH_BAY_CATEGORY_LABELS` near line 1672.
- Refresh and fullscreen-resume workflow: `refreshPage()` and `resumeFullscreenAfterRefresh()` near lines 2007-2027.
- Client-side flexible CPU route matching: `inferredRoute()` near line 2925.
- Shared rack options and No Rack sentinel conversion: `groupedRackOptionsHtml()` and `rackCodeForScan()` near lines 3729-3762.
- Main scanner No Rack presentation and action state: `renderScanRackTools()` near line 5175.
- Blank rack assignment sent with scans: `processScan()` near line 6578.
- Refresh and Staging rack event wiring: `wireEvents()` near lines 14912 and 15219.

### `delivery_store.py`

- Backend flexible CPU route matching: `job_number_route_hint()` near line 411.
- Blank-rack scan handling uses the existing `record_scan()` workflow near line 5456.

### `styles.css`

- No Rack scanner state: near line 8227.
- Refresh control icon: near line 27129.

### `index.html`

- Refresh header control: near line 115.
- Cache references updated to v048.

## Validation Performed

- `node --check app.js`
- `python3 -m py_compile delivery_store.py server.py scanner_config.py`
- Backend route matrix covering capitalization, spaces, hyphens, underscores, slashes, periods, long dashes, reversed token order, and false-positive prevention.
- Frontend route matrix using the same supported CPU-Air and CPU-IT variations.
- Explicit ROUTE precedence checks proving Job Nr. hints do not override ROUTE.
- Temporary SQLite import and Staging scan proving No Rack increments scanned quantity, leaves Location blank, and creates zero rack-item records.
- Bay translation pattern checks for spaced, dashed, underscored, singular, and plural standard bay names.
- Duplicate-definition audit confirming each new helper, state path, and renderer exists only once.
- Local server smoke test confirming `/api/health`, the refreshed HTML, and v048 cache references load successfully.

---

# Delivery List Scanner - v047 Manual Edit and CPU Route Resolution Fix

Date: 2026-07-14

## v047 Changes

### Manual line edits now persist correctly

- Saving a manual edit now updates the matching copies of that item across the same delivery date instead of changing only one isolated stage row.
- Shared business fields now remain consistent across Staging, Outbound, and the applicable receiving stage:
  - Order Nr. and Item Nr.
  - barcode
  - quantity
  - dimensions
  - customer
  - route
  - Job Nr.
  - product
  - process and queue states
- Stage-specific scanned quantity remains stage-specific and is not copied to the other stages.
- Location edits now use the newly saved line-item values instead of validating against the stale pre-edit row.
- The app refreshes the delivery-list collection after saving and displays a polished success notice.

### Route changes move the item to the correct receiving list

- Changing a line from CPU to Indian Trail now stores an explicit `IT` route so a customer-route fallback cannot silently change it back to CPU.
- The matching receiving-stage record is moved between Customer Pickup, Indian Trail, Greenville, DTC, or a custom route list while retaining its scan, rack, bay, and audit references.
- Staging and Outbound copies remain available because those stages contain all destinations.
- Quantity reductions are blocked when another stage has already scanned more pieces than the proposed new quantity.

### Revised CPU routing order

1. An explicit ROUTE value is authoritative.
2. Any ROUTE value containing `CPU` is treated as CPU, regardless of Job Nr. wording.
3. When ROUTE is blank, Job Nr. `CPU-IT` or `CPU-INT` routes to Indian Trail.
4. When ROUTE is blank, Job Nr. `CPU-Air` routes to Customer Pickup.
5. A matching customer-route database rule is used for other blank-route CPU jobs.
6. A generic CPU mention in Job Nr. defaults to Indian Trail when no route rule resolves it.

This keeps Job Nr. detection available without allowing generic CPU text to override the ROUTE column or customer routing database.

## Exact Code Locations in v047

### `app.js`

- Client-side route interpretation: `inferredRoute()` near line 2760.
- Manual route selector values: `manualEditRouteOptions()` near line 14310.
- Manual-edit save, full list refresh, and success notice: `saveManualLineItem()` near line 14542.

### `delivery_store.py`

- ROUTE-column normalization: `normalize_route_column()` near line 390.
- Job Nr. CPU pattern handling: `job_number_route_hint()` near line 411.
- Shared route-category resolution: `inferred_route()` near line 422.
- Customer-route database application during imports: `apply_customer_route_rules_to_payload()` near line 4789.
- Matching stage-copy lookup: `manual_edit_sibling_rows()` near line 6547.
- Receiving-list movement after route edits: `sync_manual_route_membership()` near line 6650.
- Manual line-item save and stage synchronization: `update_line_item()` near line 6716.

### Cache references

- `styles.css?v=20260714-v047`
- `app.js?v=20260714-v047`

## Validation Performed

- `node --check app.js`
- `python3 -m py_compile delivery_store.py server.py scanner_config.py`
- Server store creation/import check
- Route-rule matrix covering explicit CPU, CPU-IT, CPU-INT, CPU-Air, generic CPU, and explicit Indian Trail
- Customer-route database test showing generic CPU follows a matched customer rule
- Temporary SQLite manual-edit test proving shared fields update across stages
- Temporary SQLite route-movement test proving CPU to Indian Trail and Indian Trail back to CPU both move the receiving record correctly

---

# Delivery List Scanner - v046 Rack Outbound, Destination Override, and Route Fixes

Date: 2026-07-14

## v046 Changes

### Rack-barcode Outbound scans

- Rack barcode scans now match the Outbound line by delivery date, Order Nr., and Item Nr. even when a source identifier differs between list stages.
- A successful rack barcode scan now consistently updates every dependent Outbound workflow:
  - Outbound scanned quantity
  - scan history and audit history
  - Indian Trail bay preassignment
  - In-Transit counts and manifest status
  - Indian Trail missing-Outbound safety checks
  - rack status and the rack-level Outbound scan timestamp
- Duplicate rack scans preserve the original departure time instead of replacing it with a later duplicate-scan time.

### Rack-level date and time

- Removed the individual piece timestamp column from the In-Transit Manifest.
- Each rack or truck group now shows one **Scanned outbound** date and time from the rack barcode scan.
- The Racks Overview card and selected-rack detail panel now show the same rack-level Outbound timestamp.
- Removed the old per-piece timestamp query and styling to keep the manifest faster and easier to read.

### Indian Trail missing-Outbound popup

- The missing-Outbound warning now opens the custom override popup immediately, before the Scan page refreshes Last Scan and Recent Scans.
- This is used by both scanner-entered barcodes and required Order Nr. / Item Nr. manual scans.
- Selecting Yes opens the custom bay selector; selecting No cancels without changing received quantity or bay assignment.

### Wrong rack destination override

- Scanning an item onto a rack assigned to a different destination now opens a custom popup showing:
  - rack code
  - rack destination
  - item destination
  - order/item and customer
- The operator can cancel or explicitly override the destination check.
- An accepted override records the rack's physical destination on that rack item so the rack remains internally consistent and can still be completed.
- The same override is supported by the main Staging scanner and the Rack-page scanner.

### CPU and destination routing

- CPU, DTC, Greenville, and custom routing now use the imported **ROUTE** column first.
- When ROUTE is blank, the customer-route database is used against the Customer field only.
- Job Nr. text is no longer used to infer CPU. A Job Nr. containing `CPU` can therefore remain on the Indian Trail route when the ROUTE column/customer rule says Indian Trail.
- Scan-page route filters and counts now use the same corrected route logic.

## Exact Code Locations in v046

### `app.js`

- Route interpretation: `inferredRoute()` near line 2760.
- Rack Overview Outbound timestamps: `renderRackBoardCard()` and `renderSelectedRackDetails()` near lines 3927-4080.
- Wrong-destination custom popup: `showRackDestinationOverrideDialog()` near line 4166.
- Rack-page destination override retry: `submitRackScan()` near line 4190.
- Scan-page Indian Trail popup and destination override handling: `processScan()` near line 6372.
- In-Transit rack-level timestamp rendering: `transitManifestRackGroups()` and `transitManifestHtml()` near lines 7191-7310.

### `delivery_store.py`

- Customer-only fallback route matching: `default_customer_route()` and `inferred_route()` near lines 341-420.
- Customer route database application: `route_from_customer_rules()` near line 4748.
- Main Staging destination-override response and persistence: `record_scan()` near line 5396.
- Rack-page destination-override response and persistence: `scan_item_to_rack()` near line 7526.
- Rack destination override calculation: `rack_destinations_from_items()` near line 7727.
- Rack barcode Outbound processing and departure timestamp: `scan_rack_outbound()` near line 8156.
- In-Transit rack timestamp and robust Outbound matching: `_indian_trail_in_transit_payload()` near line 8276.

### `styles.css`

- Rack-level timestamp polish: v046 block near line 28727.

### Cache references

- `styles.css?v=20260714-v046`
- `app.js?v=20260714-v046`

## Validation Performed

- `node --check app.js`
- `python3 -m py_compile delivery_store.py server.py scanner_config.py`
- Temporary SQLite rack-barcode test with intentionally mismatched source IDs
- Outbound quantity, departure timestamp, In-Transit, and Indian Trail safety-gate test
- Main Scan-page and Rack-page destination mismatch/override tests
- ROUTE-column and customer-route database classification test proving Job Nr. `CPU` text does not force Customer Pickup
- Native popup audit confirming no `alert()`, `confirm()`, or `prompt()` calls

---

# Delivery List Scanner - v045 Transit Timestamps, Rush Dates, and Stage Memory

Date: 2026-07-14

## v045 Changes

### In-Transit piece timestamps

- Added an **Outbound Scanned** column to the Indian Trail In-Transit Manifest.
- Each individual in-transit quantity now shows its own outbound scan date and time.
- Multi-quantity line items display `Piece 1`, `Piece 2`, and so on with separate timestamps.
- Items that reached transportation without a recorded Outbound scan clearly display `Outbound scan not recorded` instead of inventing a time.

### Rush delivery date

- Rush broadcast popups now include the delivery date in the alert message and the details grid.
- The backend stores the delivery date in the persistent Rush notification payload so every user sees the same date.
- The immediate Rush result also returns `matchedDeliveryDate` for future confirmation-popup use.

### Indian Trail missing-Outbound workflow

- Hardened the Scan page and Bay Map safety workflow into two custom steps.
- Step 1 clearly states that the item has not been scanned Outbound and asks whether to override.
- Selecting **No** cancels the scan without changing received quantity or bay assignment.
- Selecting **Yes** opens a second custom popup asking which bay should receive the item.
- The same two-step flow is used by regular and manual scans on both Indian Trail scanning surfaces.

### Preserve the current stage when changing dates

- Changing the delivery date on the Scan page now keeps the operator in the same stage whenever that stage exists on the selected date.
- The scanner profile is used as a fallback match before the app falls back to the first available stage.
- Changing dates no longer automatically returns the operator to Staging.

## Exact Code Locations in v045

### `app.js`

- Indian Trail two-step Outbound override: `showIndianTrailOutboundReceiveOverride()` near line 6168.
- Rush popup delivery-date display: `showRushAlert()` near line 6671.
- In-Transit timestamp rendering: `transitManifestRowHtml()` near line 7062.
- Delivery-date stage preservation: `deliveryDateSelect` change handler near line 14873.

### `delivery_store.py`

- Per-piece outbound scan timestamps: `_indian_trail_in_transit_payload()` near line 8178.
- Rush notification delivery date: `mark_sdi()` near line 9811.

### `styles.css`

- In-Transit timestamp styling: v045 block near line 28727.

### Cache references

- `styles.css?v=20260714-v045`
- `app.js?v=20260714-v045`

---

# Delivery List Scanner - v044 Bay Scan Workflow and Custom Dialogs

Date: 2026-07-14

## v044 Changes

### Custom webapp dialogs everywhere

- Removed the remaining native JavaScript `alert()`, `confirm()`, and `prompt()` calls so the browser no longer displays messages such as `IP address says:`.
- Added reusable custom confirmation and text-entry dialogs that match the webapp styling.
- Added a custom confirmation and polished success popup when marking a rack returned.
- Added custom confirmation and success feedback for clearing an individual rack and clearing a complete rack set.
- Converted destructive Admin, route, user, delivery-list, rack, and Bay Map actions to custom dialogs.
- Removed the browser-native unsaved-changes prompt. Print-page lifecycle listeners remain, but they do not display a browser confirmation.

### Required manual-scan fields

- Manual scans now require both Order Nr. and Item Nr. on the main Scan page.
- Bay Map manual scans also require both Order Nr. and Item Nr.
- Manual scans use the same processing paths, validation, bay assignment, history, and undo/redo behavior as scanner-entered barcodes.
- Manual events remain clearly marked as manual in scan and Bay Map history.

### Indian Trail Outbound safety override

- Indian Trail scans now check that the item was scanned Outbound before receiving it.
- When Outbound is missing, a custom safety dialog identifies the item and asks whether to override the requirement.
- Confirming the override requires choosing the destination bay.
- Canceling stops the scan without changing received quantity or bay assignments.
- The same safety workflow is used by the Scan page and Bay Map Add To Bay mode.

### Timed placement guidance

- Successful Indian Trail receives show a 12-second placement popup with the suggested or preassigned bay.
- The operator can override the destination from the popup before it closes.
- Oversize glass attempts to suggest an oversize bay and clearly tells the operator to verify placement.
- The popup distinguishes a normal receive from an already-received item being returned to a bay.

### Bay Map scanner repair and manual scanning

- Reworked the Bay Map scanner around one shared scan function for regular and manual scans.
- `Add to bay` receives or returns the item to the selected bay.
- `Remove from bay` scans the item out of whichever bay currently holds it; a stale Add target no longer blocks a valid scan-out.
- Add To Bay can return an already-received item to a bay without increasing Indian Trail received quantity.
- Bay Map manual scanning now uses required Order Nr. and Item Nr. fields rather than the former Manual Assign workflow.
- Undo and redo are retained for both Add and Remove actions.
- Bay scanning permissions allow Indian Trail receiving users to move, clear, restore, and scan items out without requiring a separate Bay Map management permission.

### Move previously scanned items

- Added a bay-move selector to Last Scan.
- Added a Move column to Recent Bay Scans.
- Added a Move column to All Bay Scans.
- Moving an item uses a custom confirmation and updates the live Bay Map and history.
- All Bay Scans now loads up to 250 recent bay events and includes action, order/item, bay, customer, reason, user, timestamp, and movement controls without horizontal scrolling.

### Bay movement timestamps and job details

- Scan-in and scan-out actions now create dated Bay Map events.
- Manual scan-in and scan-out actions are distinguishable in the event history.
- Selected-bay Job details show when each present item was scanned into the bay.
- The Job summary shows the most recent scan-in time for that Job Nr.
- Scan-out records preserve the source bay, user, date, time, order, item, and reason.

### Sticky scanner-panel fit

- Reduced the normal and fullscreen gap below the application header so the Scan and Bay Map panels sit slightly higher.
- Kept a small safety gap and bottom clearance so the full scanner panel fits between the header and bottom of the viewport.

## Exact Code Locations in v044

Line numbers below refer to the files in this package. Search by the function or element name if later edits shift the lines.

### `app.js`

- Sticky Scan/Bay Map panel position: `syncFullscreenStickyPanelOffset()` near line 1853.
- Rack return custom confirmation and success: `returnRack()` near line 4239.
- Rack reset confirmations: `clearRack()` and `clearRackSet()` near lines 4307-4357.
- Indian Trail missing-Outbound override: `showIndianTrailOutboundReceiveOverride()` near line 6160.
- Timed placement and bay override popup: `showIndianTrailPlacementPrompt()` near line 6235.
- Main Scan-page barcode flow: `processScan()` near line 6302.
- Reusable polished edit/success popup: `showActionFeedback()` near line 6547.
- Selected-bay item timestamps: `selectedBayJobItemsHtml()` near line 7674.
- Bay Map Last Scan and Recent Scan movement controls: `renderBayLastScanCard()` and `renderBayRecentActions()` near lines 8428 and 8463.
- Shared Bay Map Add/Remove scan workflow: `runBayScan()` near line 8594.
- Bay Map required manual scan: `submitManualBayScan()` near line 8676.
- All Bay Scans history GUI: `openBayAllScansModal()` near line 9174.
- Reusable custom confirmation dialog: `confirmWebAppAction()` near line 12542.
- Reusable custom text prompt: `promptWebAppAction()` near line 12643.

### `index.html`

- Main Scan-page manual Order/Item fields: lines 426-441.
- Bay Map Add/Remove selector, target bay, barcode box, and manual scan: lines 680-738.
- Bay Map Last Scan and Recent Scan movement controls: lines 740-772.

### `delivery_store.py`

- Selected-bay Job fulfillment and scan-in timestamps: concrete `get_bay_job_details()` implementation near line 7058.
- Dated Bay Map event/history records and active assignment data: concrete `get_bay_events()` implementation near line 7195.
- Indian Trail receive, Outbound safety, returned-item override, and bay assignment: concrete `receive_indian_trail_scan()` implementation near line 8700.
- Bay scan-out and timestamp logging: concrete `scan_out_bay_item()` implementation near line 9299.

### `server.py`

- Multi-permission helper used by Bay Map scan actions: `require_any_permission()` near line 842.
- Indian Trail receive endpoint: near line 1536.
- Move, clear-assignment, restore-assignment, and scan-out endpoints: approximately lines 1560-1601.

### `styles.css`

- v044 custom dialogs, timed placement popup, movement selectors, Bay history layout, timestamps, and scanner-panel fit: block beginning near line 28306.

## Validation

- `node --check app.js`
- `python3 -m py_compile delivery_store.py server.py scanner_config.py`
- HTML audit: all 268 element IDs are unique and all required manual/Bay Map scan controls are present.
- CSS parse audit completed with zero parse errors.
- Native browser dialog audit found zero `alert()`, `confirm()`, or `prompt()` calls in the webapp source.
- Temporary SQLite workflow testing verified:
  - missing-Outbound scans return the override requirement
  - confirmed override receives into the selected bay
  - scan-out records the bay and timestamp
  - an already-received item can be returned to another bay without increasing received quantity
  - manual scan-in and scan-out events remain distinct
  - Job fulfillment and scan-in timestamps update correctly
  - moving an assignment updates the current bay and event history
- Automated visual browser navigation could not run because this execution environment blocks localhost browser navigation. Static validation and direct backend lifecycle tests passed.

### Cache references

- `styles.css?v=20260714-v044`
- `app.js?v=20260714-v044`

---

# Delivery List Scanner - v043 Wrong-List Guidance and Rush Broadcast Alerts

## v043 Changes

### Wrong delivery-list scan guidance

- Wrong-list errors now identify the matching **delivery-list date only** instead of listing every matching stage on that date.
- Last Scan and Recent Scans now use the concise instruction `Check delivery list date <date>`.
- All Scans normalizes both new and previously saved wrong-list errors so older stage-heavy messages also display only the relevant date.
- Indian Trail receiving now returns the same date-focused guidance in its immediate scan error.

### Check-column alignment

- Rebuilt the success, notice, and error symbols as centered pseudo-icons inside their colored circles.
- Centered the entire Check column in Recent Scans, All Scans, and Bay Map scan history.

### One-time Rush alerts

- Added persistent Rush notifications stored in SQLite.
- Every active user receives one polished production-priority popup for each newly submitted Rush.
- The submitting user keeps the existing Rush success confirmation and is not interrupted by a duplicate alert.
- Other users receive the alert within the normal seven-second notification poll, even when viewing Home, Racks, Bay Map, Scan, or Admin.
- Alerts include Job Nr., order, customer, priority-item count, and submitting user when available.
- Each user acknowledges each alert once; acknowledgment is shared across that user's sessions.
- Rush alerts expire after 24 hours so users returning much later are not shown stale priorities.
- Remakes do not create Rush broadcasts.

### Cache references

- `styles.css?v=20260714-v043`
- `app.js?v=20260714-v043`


## v042 Changes

### Bay Map in-transit rack summary

- The `Racks:` line now includes every transportation rack currently carrying Indian Trail pieces, including `T`, `T2`, and other truck-type racks.
- Removed the five-rack display limit and allowed the rack list to wrap so every active in-transit rack remains visible.
- The quantities are based on pieces still in transit, so fully received racks are removed from the Bay Map transit summary.

### Received item locations

- Added cross-stage receipt detection for Indian Trail, Customer Pickup/CPU, DTC, and Greenville.
- Once an item has been scanned at one of those receiving stages, its Location column displays `Received` instead of its former rack, truck, or bay location on every matching scan list.
- Global item search now also reports the current location as `Received` after one of those receiving scans.
- Added a dedicated green Received location badge.

### Rack received and returned lifecycle

- Racks that remain marked `In Transit` but whose complete contents have been scanned at their destination now display `Received`.
- Received racks remain visually grayed out and unavailable for reuse until they are explicitly marked returned.
- Added a `Received` rack-status filter.
- The Outbound transportation-status selector now distinguishes `Received - awaiting return` from `On the way`.
- Added a visible `Mark Returned` button directly on received rack cards in the Racks overview, while preserving the existing selected-rack return action.
- Marking a rack returned clears its active rack contents and resets it for staging reuse.

### Cache references

- `styles.css?v=20260714-v042`
- `app.js?v=20260714-v042`

## Validation

- `node --check app.js`
- `python3 -m py_compile delivery_store.py server.py scanner_config.py`
- Temporary SQLite lifecycle test verified:
  - truck and standard racks both appear in the Indian Trail in-transit summary
  - a fully received rack derives the `Received` state while its stored lifecycle remains `In Transit`
  - matching staging items receive the cross-stage `received` flag
  - marking the rack returned resets it to `Open` with zero active rack contents

---

# Delivery List Scanner - v041 Scanner History, Outbound Status, and Bay Fulfillment

## v041 Changes

### Scan-panel controls

- Condensed the Indian Trail Bay Assignment control to the same compact footprint as the Staging Transportation Method control.
- Added a compact Outbound Transportation Status selector that is view-only and does not assign pieces to racks.
- The Outbound selector groups racks by rack set and shows whether each rack is still being built, complete and waiting for Outbound, or already scanned Outbound.

### Scan errors and history

- Replaced the confusing `BAD SCAN format - No unique delivery-list match` result with a clear wrong-list message.
- When possible, the detailed error identifies the other delivery date or stage where the item appears.
- Kept Last Scan and Recent Scans concise while giving the All Scans GUI the complete message, reason, raw barcode, resolved barcode, user, station, and time.
- Enlarged the All Scans GUI and removed horizontal scrolling by using a fixed, wrapping table layout.
- Separated delivery-list imports from updates with different event badges and row accents.
- Import and update events now show their source file/details and a successful check mark when completed.

### Bay Map job fulfillment

- Replaced the selected-bay Filled Percentage summary with Job completion and Fulfillment counts.
- Jobs in a selected bay can now be expanded to show every order/item required for that Job Nr.
- Each order item shows the quantity currently in the bay and exactly how many pieces are still missing.
- Job details load only when a bay is selected, keeping the main Bay Map refresh lightweight.

### Spanish coverage

- Added Spanish translations and dynamic quantity translations for the new scanner, scan-history, Outbound status, and Bay fulfillment interface.

### Cache references

- `styles.css?v=20260714-v041`
- `app.js?v=20260714-v041`

## Validation

- `node --check app.js`
- `python3 -m py_compile delivery_store.py server.py scanner_config.py`
- Temporary SQLite wrong-list test verified the new friendly error and other-list hint.
- Temporary SQLite import/update test verified distinct successful event types.
- Temporary SQLite Bay Map test verified Job fulfillment `1/3` and missing item quantity `2` after receiving one piece.
- HTML ID and required-control checks.

---

# Delivery List Scanner - v040 Scanner Header and Sticky Clearance Polish

## v040 Changes

- Added a little more breathing room below the sticky application header for both the Scan page and Bay Map scanner panels in normal and fullscreen modes.
- Reused the live measured header height for normal sticky positioning instead of relying only on older fixed offsets.
- Fixed the Bay Map `Indian Trail Route` header band so it fills the scanner card from the left edge through the right edge.
- Removed the width cap that caused the navy route header to stop short on the right side.
- Balanced the Outbound, in-transit, and Received columns inside the compact route header.
- Corrected the compact in-transit wording for a single piece.
- Cleaned the Bay Map scanner HTML indentation around the route header.
- Updated cache references to `styles.css?v=20260714-v040` and `app.js?v=20260714-v040`.

## Validation

- `node --check app.js`
- `python3 -m py_compile delivery_store.py server.py scanner_config.py`
- HTML parsing and required Bay Map scanner element checks
- CSS checks for the live normal/fullscreen sticky offsets and full-width route band

---

# Delivery List Scanner - v039 Fullscreen Scanner Panel Clearance

## v038 Changes

- Preserved the existing fullscreen-return prompt after printing is completed or cancelled.
- Added parent-window monitoring for the temporary print window. Closing the print page with its window close button is now detected even when the browser does not fire `afterprint`.
- Added `pagehide` and `beforeunload` completion signals to every server-generated print page and the Statistics print page.
- When a print page closes, the main webapp is focused and automatic fullscreen restoration is attempted. If the browser blocks automatic fullscreen, the existing polished one-click `Return to fullscreen` popup appears.
- Prevented duplicate fullscreen prompts when more than one print lifecycle event fires.
- Updated cache references to `styles.css?v=20260714-v038` and `app.js?v=20260714-v038`.

Date: 2026-07-13

## Summary

This package builds on v036. It fixes the Bay Map Rush / Remake GUI so users can paste a complete Job Nr. label, adds a reusable polished success popup, and improves printing from fullscreen mode.

## Changed Files

- `app.js`
- `delivery_store.py`
- `server.py`
- `styles.css`
- `index.html`
- `README_CHANGELOG.md`

## Changes

### SDI Job Nr. lookup

- The SDI field now accepts a full Job Nr. such as `88418245M LOGAN FARMS 51`.
- It also accepts an SO number, order number, or barcode.
- Spacing and punctuation differences are normalized when matching a Job Nr.
- When a Job Nr. is matched, every line item belonging to that job on the selected active delivery list is updated together.
- Existing Bay Map assignments for those items are updated to the Rush / Remake override state so the change is visible throughout the Bay Map.
- Clearing by Job Nr. removes the special process state and restores matching bay assignments.
- Replacing the prefilled SDI value with a different Job Nr. now searches for the pasted value instead of silently applying the change to the previously selected assignment.
- The SDI input label, placeholder, and helper text now explain all accepted input formats.

### Polished success popup

- Replaced the native Rush / Remake print confirmation with a custom webapp-styled success popup.
- The popup shows the matched Job Nr. or order, customer, and number of items updated.
- Rush and Remake results provide the correct print action directly in the popup.
- The popup component is reusable for other important edits in future versions.
- Added matching Spanish translations for the new interface text.

### Printing and fullscreen

- Print pages opened by the app now use a managed print window.
- After print preview is closed or cancelled, the temporary print window closes automatically.
- The main webapp is focused again after printing.
- When the app was fullscreen before printing, it attempts to return to fullscreen automatically.
- Browsers that block automatic fullscreen restoration show a polished one-click `Return to fullscreen` popup instead.
- Applied the managed workflow to delivery-list packages, Rush/Remake sheets, rack packing lists, stale-bay reports, customer manifests, and the Statistics PDF report.

## Validation

- `node --check app.js`
- `python3 -m py_compile delivery_store.py server.py scanner_config.py`
- Temporary SQLite test: pasted full Job Nr. marked two matching items as Rush, updated both Bay Map assignments, and cleared both successfully.
- Printable HTML render test verified the after-print notification and automatic print-window close workflow.

## Cache References

- `styles.css?v=20260713-v037`
- `app.js?v=20260713-v037`

## v039 Changes

- Fixed the Scan-page scanning panel overlapping the sticky application header while fullscreen is active.
- Fixed the Bay Map scanning panel overlapping the header while fullscreen is active.
- Added live header-height measurement so the scanner offset adjusts when header controls wrap or the fullscreen viewport changes size.
- Kept the existing non-fullscreen sticky-panel positions unchanged.
- Updated cache references to `styles.css?v=20260714-v039` and `app.js?v=20260714-v039`.
