# Delivery List Scanner

Current maintained release: **v0.254**. SQLite remains the active/default backend.

v0.254 restores stable manual expansion in Delivery List Management. Delivery-date groups stay collapsed until the user opens them, preserve that choice during background import checks, and no longer replay the flashing expansion animation.

## Install v0.254

1. Stop the scanner server and wait for any delivery-list automation run to finish.
2. Extract the v0.254 changed-files ZIP directly into the current project folder, preserving the included folder structure.
3. Keep the existing `data` folder, scanner database, configuration, logs, and backups.
4. Restart the scanner server.
5. Refresh the browser with `Ctrl+F5`.
6. Open Delivery List Management and manually expand/collapse several delivery dates while a history check runs. The selected groups should remain stable without flashing.

## v0.254 highlights

- Removes automatic opening of changed delivery dates in Delivery List Management.
- Restores manual expand/collapse behavior for each delivery-date group while keeping every stage visible inside the group.
- Preserves the user's open/closed choices when recent-import data refreshes in the background.
- Skips replacing identical Delivery List Management markup during repeated automation checks, preventing unnecessary redraws.
- Removes the stage-table opening animation from Delivery List Management while retaining the existing visual treatment and route/stage information.
- Keeps the v0.253 Airport Road consolidation, route-accurate previews, historical preview recovery, and exact print filters.
- SQLite schema remains version 10; no migration is required.

## v0.253 highlights

- Restores the full Delivery List Management dropdown so unchanged and changed stages remain visible together.
- Combines only Staging and Outbound into one Airport Road row while preserving Indian Trail, Greenville, CPU, DTC, and custom route stages.
- Uses the outbound all-orders list as the authoritative preview source, then filters route-level previews by each order's actual route.
- Prevents Greenville, CPU, and DTC orders from being grouped under Airport Road merely because their source stage is Outbound.
- Recovers preview metadata and retained snapshots for historical or retired stage IDs instead of returning `Delivery list was not found`.
- Expands newly-created stage previews with every current order so the preview does not report many recorded changes while showing only one retained snapshot.
- Keeps preview and print eye/icon actions square and keeps exact route filters for Indian Trail, Greenville, CPU, and DTC.
- SQLite schema remains version 10; no migration is required.

## v0.252 highlights

- Replaces Staging and Outbound rows in Delivery List Management with one Airport Road route row, alongside Indian Trail, Greenville, CPU, and DTC.
- Shows only routes changed by the selected import and automatically expands delivery dates containing changes.
- Keeps New reserved for a newly-created delivery list or route in the management view.
- Marks every retained order inside a newly-created route as New in the item preview while preserving explicit Removed order snapshots.
- Removes nested stage sections from the preview so each collapsed route opens directly to its changed orders and item details.
- Uses one representative stage per route, preventing Staging/Outbound duplicate orders in the combined preview.
- Opens route-level Print / Export actions with the exact route filter already selected.
- Opens the delivery-date print action with Airport Road selected, which represents the complete Airport Road outbound delivery list across all routes.
- Uses the Airport Outbound list as the print source so destination filters do not duplicate rows across scanner stages.
- Makes every preview eye button a perfect square matching the print icon.
- SQLite schema remains version 10; no migration is required.

## v0.251 highlights

- Allows Admin, Supervisor, and fully authorized Delivery List Management users to preview changes across every stage without being blocked by their ordinary scanner-stage assignment.
- Keeps earlier automated and manual import runs visible while the newest run is loading, then merges the full durable day history instead of replacing it.
- Uses stable run identity before timestamp/signature fallback so identical results from separate manual and automated runs remain distinct.
- Rebuilds Delivery List Update Preview into collapsed Airport Road, Indian Trail, Greenville, CPU, and DTC route groups.
- Automatically opens matching route groups only when the user searches or applies a change-type filter; the initial preview remains fully collapsed.
- SQLite schema remains version 10; no migration is required.

## v0.250 highlights

- Fixes `name 'args' is not defined` during authoritative scanner reconciliation of changed or newly created delivery dates.
- Passes `run_id` and `run_started_at` into `selective_sql_sync` as explicit parameters rather than relying on `main()` local state.
- Preserves the stable automation-run identity on imported file history, notifications, and Recent Imports grouping.
- Leaves successfully published workbooks untouched; only the failed scanner-import step needs to be rerun.
- Preserves all v0.249 import-history, preview, change-total, superseded-order review, and manual-protection behavior.
- SQLite schema remains version 10; no migration is required.

## v0.249 highlights

- Reflows the Selected Run summary into a compact two-column header with file, updated-piece, removed-piece, and status metrics instead of a tall vertical stack.
- Shows positive changes and removed quantities independently in the Delivery List Management **Changes** column, including mixed updates such as `Updated 12 pcs` and `Removed 3 pcs`.
- Displays update-preview buttons only on stages that currently contain saved new, updated, or removed rows.
- Fixes the update-preview API fallback that called an undefined row helper, and returns readable JSON errors instead of an opaque browser `Failed to fetch` message.
- Lets multi-stage previews load every successful stage even when one stage fails, while showing the failed stage as a concise warning.
- Groups Automation Control Center history by raw run ID and raw timestamp instead of reparsing shortened display text, preventing year `2001` and duplicate/mis-grouped runs.
- Adds the full year to visible run timestamps and polishes the history day, run, status, and result cards.
- Preserves separate new-piece and updated-piece totals through scanner import normalization and durable import history.
- Retains complete same-day import history, exact-key review approvals, manual protections, and SQLite schema version 10.

## v0.248 highlights

- Uses a stable automation run ID across the PowerShell runner, Python importer, database audit row, app notification, and browser grouping.
- Keeps all same-day import runs, including repeated imports of the same delivery-date workbook, instead of collapsing them by date and file name.
- Treats durable database history as the audit source and uses runtime/notification results only as matched run context or a fallback, preventing the newest run from appearing twice.
- Loads every available current-day result across the paginated audit history and paginates the run tabs without an artificial 100-run display cutoff.
- Shows polished daily run totals, selected-run metrics, complete file results, and clearer status treatment in the Recent Imports section.
- Rebuilds Delivery List Update Preview with All/New/Updated/Removed filters, order/item search, prominent customer and stage context, and compact order details.
- Records and displays exact before/after values for changed quantity, dimensions, customer, job, product, route, queue state, source ID, and barcode when those snapshots are available.
- Preserves the v0.247 Superseded Order Review, exact-key approvals, simplified active totals, manual protections, and SQLite schema version 10.

## v0.247 highlights

- Reissues the complete v0.245-v0.246 Superseded Order Review file set so the runtime store always includes `sync_superseded_order_candidates`.
- Adds a precise importer diagnostic showing the loaded `backend/store.py` path when an incomplete overlay is detected.
- Stops the automation log from describing a failed review-queue sync as a successful sync.
- Keeps successful workbook/scanner imports successful when only the optional review queue has a problem.
- Shows a single active quantity in Delivery List Management, such as **129 pcs**, without duplicate A+W/active-total wording.
- Avoids misleading `0 A+W + 0 manual = 121 active` logging when an unchanged-stage result does not return ownership counters.
- Keeps all exact-key approval, Keep Both, Review Later, manual protection, raw date selection, and notification recovery behavior from v0.245-v0.246.

- Uses A+W `AH_IDENT`/Header Identity as the primary relationship signal between an older order and a newer replacement candidate.
- Requires the older candidate to be status 410 with item status 0 and no production batch, while the newer order must have an active production batch. These conditions only create a review; they never delete automatically.
- Shows original and replacement items side by side with dimensions, quantities, statuses, batches, exact overlap evidence, and current scanner impact.
- Supports **Approve old order removal**, **Keep both**, and **Review later**.
- Approval removes only the exact A+W-owned order/item rows, preserves protected manual rows, records update-preview snapshots, increments affected stage revisions, and writes an audit event.
- Approved exact keys are written to `data/superseded-source-exclusions.json` and merged with the eight historical Crystal-verified 8/3 exclusions on every SQL run. Keep Both, Review Later, and changed-evidence states publish preservation overrides so those bootstrap exclusions can be reversed locally.
- A changed candidate fingerprint automatically returns the review to pending so an old decision cannot silently expand to new item keys.
- Adds SQLite schema migration 10 and the matching Azure SQL compatibility table.

## v0.244 highlights

- Removes order-status `460`, item-status `460`, and production-batch requirements from delivery-list membership decisions.
- Restores status `50`, `450`, `455`, internal-reject, not-yet-cut, and other raw date-matched rows instead of assuming they were removed from Crystal.
- Keeps status and production-batch distributions in the automation log as diagnostics only.
- Uses `verified-source-exclusions.json` for the eight exact 8/3/2026 order/item rows already confirmed absent from Crystal; no job/customer/dimension similarity rule is used.
- Pauses all other automatic A+W source-row removals while still importing new rows, changed quantities/details, route changes, remake changes, and unprotected manual duplicates.
- Allows exact Crystal-verified exclusions to be retired even while general removals are paused.
- Prevents repeated drift imports by treating extra unverified source rows as retained rather than as an error.
- Adds a focused SELECT-only `POOL_TEILE`, `LADELISTE`, `BW_LADELISTE`, and `TEMP_DELIV` schedule-membership probe.
- Preserves protected manual orders and SQLite schema version 9; no database migration is required.

## Install v0.237

> **Historical only:** v0.237 production-status filtering is superseded by v0.244 and must not be used as the current delivery-list membership rule.

1. Start from the maintained v0.236 project.
2. Stop the scanner server and wait for any active automation run to finish.
3. Extract the v0.237 changed-files ZIP directly into the current project folder, preserving the included folder structure.
4. Preserve the existing `data` folder, automation configuration, and database files.
5. Restart the scanner server and refresh the browser with `Ctrl+F5`.
6. Run Query SQL, Export & Import for the affected delivery date. The browser controller automatically refreshes the updated PowerShell runner under `C:\DeliveryListAutomation\Scripts`.
7. Confirm the automation log reports raw, report-eligible, and excluded line/remake counts before the workbook is rebuilt and imported.

## v0.237 highlights

- Reads A+W header status, item status, and all three header production-run fields alongside the delivery rows.
- Uses verified report-eligibility defaults: order status `460`, item status `460`, and at least one active production batch.
- Excludes removed scheduling records such as the eight 8/3/2026 duplicate remake lines whose old orders were status `410`, item status `0`, and no longer assigned to a production batch.
- Keeps different order numbers independent; no deletion decision is based on matching job text, customer, dimensions, product, or quantity.
- Logs every excluded order/item with status, production batches, remake flag, and the exact exclusion reason.
- Adds a configurable mass-removal safety limit before an eligibility-filtered workbook can be published.
- Includes the eligibility-rule version in the exporter hash so the first v0.237 run rebuilds and imports the corrected workbook even when A+W source records themselves have not changed.
- Retains v0.236 protected manual orders and remake-source cleanup behavior.
- Advances the application to v0.237 while SQLite schema version 9 remains unchanged.

The verified defaults work with the current `SYSADM.BW_AUFTR_KOPF` / `BW_AUFTR_POS` mapping. They can be overridden later without another code change by adding this optional block under `SourceMapping` in the installed automation configuration:

```json
"DeliveryEligibility": {
  "AllowedOrderStatuses": [460],
  "AllowedItemStatuses": [460],
  "RequireProductionBatch": true,
  "MaxExcludedPercent": 50
}
```

## Install v0.236

1. Start from the maintained v0.235 project.
2. Stop the scanner server and wait for any active automation run to finish.
3. Extract the v0.236 changed-files ZIP directly into the current project folder, preserving the included folder structure.
4. Preserve the existing `data` folder, automation configuration, and database files.
5. Restart the scanner server so SQLite migration 9 can add the manual-order protection columns.
6. Refresh the browser with `Ctrl+F5`.
7. Run Query SQL, Export & Import for the affected delivery date. The browser controller automatically refreshes the updated runtime importer, safety helper, and PowerShell runner under `C:\DeliveryListAutomation\Scripts`.

## v0.236 highlights

- Adds **Protect from A+W import** to manual-order creation and enables it by default.
- Adds the same protection toggle to the manual line-item editor for existing manual rows.
- Keeps protected manual rows separate even when A+W later publishes the same order/item.
- Continues retiring unprotected manual duplicates so A+W remains authoritative by default when protection is not selected.
- Adds SQLite migration 9 plus Azure SQL compatibility columns for the new protection state.
- Stops carrying stale source-provided `Remake`/`RM` labels forward after A+W no longer marks the row.
- Preserves Rush/Remake labels created through the operator Priority Work workflow by checking their latest audit action.
- Logs both SQL-classified remake line count and unique remake order count.
- Logs each remake order/item and the raw A+W header flag used by the bitmask test.
- Advances the application to v0.236 and SQLite schema version 9.

## Install v0.234

1. Start from the maintained v0.233 project.
2. Stop the scanner server and wait for any active automation run to finish.
3. Extract the v0.234 changed-files ZIP directly into the current project folder, preserving the included folder structure.
4. Preserve the existing `data` folder, automation configuration, and database files.
5. Restart the scanner server and refresh the browser with `Ctrl+F5`.
6. Run Query SQL, Export & Import again for the requested date. The browser controller automatically refreshes the updated importer and safety helper under `C:\DeliveryListAutomation\Scripts`.

## v0.234 highlights

- Repairs `line_update_notices` immediately inside the import-safety runtime, so `snapshot_json` and Removed notice support no longer depend on `Import.InitializeStore` or a migration having run first.
- Preserves existing notice IDs and per-user review receipts while rebuilding only the affected notice tables.
- Makes SQL Export & Import process the selected canonical `Delivery List ...` workbook directly instead of calling a whole-folder import that can process duplicate files for the same date.
- Makes Folder Import Only select and import one deterministic workbook per date.
- Reports `schemaRepairApplied: true` in the normalized import result when the runtime repair was needed.
- Advances the application to v0.234 and SQLite schema version 8.

## Install v0.233

1. Start from the maintained v0.232 project.
2. Stop the scanner server and wait for any active automation run to finish.
3. Extract the v0.233 changed-files ZIP directly into the current project folder, preserving the included folder structure.
4. Preserve the existing `data` folder, automation configuration, and database files.
5. Restart the scanner server. Startup creates a verified backup when needed and advances SQLite schema version 6 to 7.
6. Refresh the browser with `Ctrl+F5`.
7. Re-run Folder Import Only or Query SQL, Export & Import for the requested delivery date.

## v0.233 highlights

- Repairs `line_update_notices` when `snapshot_json` is missing even if the database migration ledger already says schema version 6 was installed.
- Preserves existing line-update notices and per-user review receipts while rebuilding the table with New, Updated, and Removed change support.
- Returns a failed automation status whenever any selected workbook fails instead of allowing skipped files to make the run appear successful.
- Imports only the newest modified workbook when more than one source file resolves to the same delivery date, avoiding sequential overwrite behavior.
- Retains v0.232 live-log startup repair and v0.231 authoritative A+W reconciliation.
- Advances the application contract, visible version, cache keys, documentation, migration history, and focused tests to v0.233 / schema version 7.

## Install v0.232

1. Start from the maintained v0.231 project.
2. Stop the scanner server. A running browser-started automation process should be ended before replacing files.
3. Extract the v0.232 changed-files ZIP directly into the current project folder, preserving the included folder structure.
4. Preserve the existing `data` folder, automation configuration, and database files.
5. Restart the scanner server and refresh the browser with `Ctrl+F5`.
6. Start one manual Query SQL, Export & Import run. The server now atomically refreshes the maintained runtime runner/import helpers under `C:\DeliveryListAutomation\Scripts` before launching PowerShell.
7. Confirm the Status & Logs panel immediately shows a concrete log path and the line `PowerShell automation runner accepted the request.`

## v0.232 highlights

- Restores one installed PowerShell runtime directory for browser and scheduled automation instead of executing the project runner beside a different working/helper directory.
- Atomically synchronizes the maintained runner, SQL importer, and import-safety helper before each browser-started run.
- Supplies a known per-run log path before PowerShell reads configuration, so startup, parser, configuration, and permission failures are visible immediately.
- Adds non-interactive PowerShell startup flags and records the exact runner path and synchronized runtime files in the live status payload.
- Retains v0.231 authoritative manual reconciliation and scheduled scanner-row drift detection.
- Advances the application contract, visible version, cache keys, documentation, and focused tests to v0.232. Schema version 6 is unchanged.

## Install v0.231

1. Start from the maintained v0.230 project.
2. Stop the scanner server and automated delivery-list tasks.
3. Extract the v0.231 changed-files ZIP directly into the current project folder, preserving the included folder structure.
4. Preserve the existing `data` folder and database files.
5. Restart the scanner server. No database migration is required; schema version 6 is unchanged.
6. Re-run `automation/sql_delivery_export/Setup-DeliveryListSqlAutomation.bat` or copy the updated `Run-DeliveryListSqlAutomation.ps1` into `C:\DeliveryListAutomation\Scripts` so scheduled Windows tasks use the v0.231 runner.
7. Restart the automation tasks and refresh the browser with `Ctrl+F5`.

## v0.231 highlights

- Forces every date selected in a browser-started Custom SQL Export & Import run through authoritative A+W reconciliation, even when the workbook hash is unchanged.
- Makes the browser automation controller use the maintained project runner, preventing manual GUI runs from silently executing an older installed PowerShell copy.
- Adds a source-row drift preflight for scheduled SQL synchronization. The verifier now compares active source-owned scanner rows with every generated stage instead of checking stage IDs only.
- Detects removed lines, scanner-only rows, quantity/detail differences, missing stages, and obsolete optional/custom route stages before deciding that a workbook has no changes.
- Reconciles an optional/custom route stage against an empty source set when the entire stage disappears from A+W, while preserving manual-only rows.
- Retains Delivery List Update Preview snapshots for historical dates for one year; past-date previews no longer disappear immediately after the delivery date.
- Advances the application contract, visible version, cache keys, documentation, and focused tests to v0.231. Schema version 6 is unchanged.

## Install v0.230

1. Start from the maintained v0.229 project.
2. Stop the scanner server and automated delivery-list import tasks.
3. Extract the v0.230 changed-files ZIP directly into the current project folder, preserving the included folder structure.
4. Preserve the existing `data` folder and database files.
5. Restart the scanner server. Startup upgrades SQLite schema version 5 to 6 and creates the maintained verified pre-upgrade backup before applying the migration.
6. Restart the automation tasks and refresh the browser with `Ctrl+F5`.

## v0.230 highlights

- Reconciles every imported A+W stage against its current active source rows, including imports that contain only removals.
- Deletes unreferenced removed lines and safely soft-deletes history-linked lines so removed work is no longer active or scannable without damaging scan, rack, bay, or machine history.
- Retires active rack and bay assignments for source-removed lines while retaining their audit records.
- Records removed-line snapshots in the import-update notice history so a physically deleted source row can still be reviewed later.
- Shows removal-only quantities as `-N pcs` and mixed updates as separate `+N pcs` and `-N pcs` values in Delivery List Management.
- Adds a Preview Changes action to every changed stage row while retaining the delivery-date-level preview action.
- Adds New, Updated, and Removed sections and stronger visual hierarchy to Delivery List Update Preview.
- Applies the same safe reconciliation wrapper to the maintained SQL and Crystal automatic import entry points.
- Advances the application contract to v0.230 and SQLite schema version to 6.

## Install v0.228

1. Start from the maintained v0.227 project.
2. Extract the v0.228 changed-files ZIP directly into the current project folder.
3. Preserve the existing `data` folder and database files.
4. Restart the scanner server and refresh the browser with `Ctrl+F5`.

No database migration or separate setup script is required. v0.228 keeps schema version 5.

## v0.228 highlights

- Removes the legacy centered-modal transform that shifted the full-screen preset workspace beyond the top-left edge.
- Gives the v0.228 modal and backdrop final fixed-position ownership so legacy preset classes cannot move the workspace.
- Keeps a consistent 12px desktop viewport inset and a 5px mobile inset.
- Preserves the complete v0.227 preset-control-center design while making its workspace internally scrollable.
- Resets the preset workspace to the top whenever it opens and focuses the name field without moving the page.
- Adds compact-height adjustments for shorter desktop displays.
- Preserves schema version 5 and all v0.227 preset behavior.

## Install v0.227

1. Start from the maintained v0.226 project.
2. Extract the v0.227 changed-files ZIP directly into the current project folder.
3. Preserve the existing `data` folder and database files.
4. Restart the scanner server and refresh the browser with `Ctrl+F5`.

No database migration or separate setup script is required. v0.227 keeps schema version 5.

## v0.227 highlights

- Uses a complete red gradient and exclamation indicator when Remakes, Rushes, or Internal Rejects contain matching work.
- Uses a complete green gradient and check indicator when each of those attention categories is clear.
- Replaces the step-based Create Preset screen with a full preset control center modeled on the supplied reference.
- Adds Preset Details with name, description, and an optional personal-default toggle.
- Keeps Default Filters, Print Options, Preset Summary, and Actions visible in one organized workspace.
- Removes Visibility and Preview from Create Preset as requested.
- Supports Save Preset and Save & Apply as separate actions.
- Preserves Lookup Manager glass types, automatic All-choice collapsing, grouped newest-first delivery dates, and schema version 5.

## Install v0.226

1. Start from the maintained v0.225 project.
2. Extract the v0.226 changed-files ZIP directly into the current project folder.
3. Preserve the existing `data` folder and database files.
4. Restart the scanner server and refresh the browser with `Ctrl+F5`.

No database migration or separate setup script is required. v0.226 keeps schema version 5.

## v0.226 highlights

- Automatically collapses every available Route selection back to Airport, the maintained all-routes choice.
- Automatically collapses complete Glass, Status, and Attention detail selections back to All Glass, All Status, or All Attention.
- Applies the same collapse behavior inside Create Preset.
- Orders grouped delivery-date weeks and their dates from newest/future to oldest.
- Restores the v0.224 two-column, step-guided Create Preset layout while preserving Lookup Manager glass values and fast loading.
- Enlarges glass-category quantity totals, changes Tempered styling from orange to green, and lengthens the Checked By write-in line.
- Preserves incremental two-week date-history loading, custom ranges, print geometry, and schema version 5.

## Install v0.225

1. Start from the maintained v0.224 project.
2. Extract the v0.225 changed-files ZIP directly into the current project folder.
3. Preserve the existing `data` folder and database files.
4. Restart the scanner server and refresh the browser with `Ctrl+F5`.

No database migration or separate setup script is required. v0.225 keeps schema version 5.

## v0.225 highlights

- Reduces Landscape continuation pages from 29 to 28 logical rows while leaving the first Landscape page at 27.
- Replaces the step-based Create Preset layout with one continuous name, filter, glass-library, and output workspace.
- Groups Delivery Date choices under visual Monday-Sunday week headings.
- Initially renders the rolling previous two weeks together with every currently available future delivery date.
- Loads two additional historical weeks whenever the user reaches the bottom of the date menu, with an explicit Load 2 older weeks control as a keyboard/mouse fallback.
- Performs the date-history expansion entirely in memory, without additional list-detail requests or recurring work.
- Preserves custom date ranges, system/user presets, shared preview/print styling, idle-state recovery, and schema version 5.

## Install v0.224

1. Start from the maintained v0.223 project.
2. Extract the v0.224 changed-files ZIP directly into the current project folder.
3. Preserve the existing `data` folder and database files.
4. Restart the scanner server and refresh the browser with `Ctrl+F5`.

No database migration or separate setup script is required. v0.224 keeps schema version 5.

## v0.224 highlights

- Grays out and disables zero-count Route, Status, New/Updated, and Errors choices so unavailable filters cannot be mistaken for usable filters.
- Keeps Remakes, Rushes, and Internal Rejects active at zero so their maintained green-clear or red-alert indicators remain visible.
- Automatically falls back to a route/status/attention selection that still has content after a date or route scope changes.
- Enlarges the numeric counts on every Print / Export filter chip without increasing the control height.
- Removes the surrounding Checked By box and moves the larger signoff text into the first-page title header, aligned with the Filters line on the right.
- Enlarges `Rows | Orders | QTY` on first and continuation pages while keeping Filters visually secondary.
- Preserves v0.223 page capacity, centered Order/Item/QTY columns, shared preview/print styling, and schema version 5.

## Install v0.223

1. Start from the maintained v0.222 project.
2. Extract the v0.223 changed-files ZIP directly into the current project folder.
3. Preserve the existing `data` folder and database files.
4. Restart the scanner server and refresh the browser with `Ctrl+F5`.

No database migration or separate setup script is required. v0.223 keeps schema version 5.

## v0.223 highlights

- Moves the first-page `Checked By` field out of the branded title area and places it immediately above the delivery-list column headings.
- Keeps the signoff right aligned and compact so the title remains clean without wasting printable height.
- Adds two logical delivery-list lines to each first page.
- Adds three logical delivery-list lines to every continuation page.
- Uses 26/28 logical rows in Portrait and 27/29 in Landscape for first/continuation pages; glass-type separator rows continue to count toward the limit.
- Centers the Order, Item, and QTY columns and transfers a small amount of width from Dimensions to QTY so the complete `QTY` heading remains visible.
- Applies the same structure and sizing to the on-screen preview and popup print document through the shared stylesheet.
- Preserves the enlarged v0.222 branding, repeating filters, alternating rows, fixed footer, Rush/remake frames, and idle-state recovery.

## Install v0.222

1. Start from the maintained v0.221 project.
2. Extract the v0.222 changed-files ZIP directly into the current project folder.
3. Preserve the existing `data` folder and database files.
4. Restart the scanner server and refresh the browser with `Ctrl+F5`.

No database migration or separate setup script is required. v0.222 keeps schema version 5.

## v0.222 highlights

- Enlarges the complete first-page branded title block by approximately 30%, including the supplied logo, route title, full date, totals, filters, badge, and Checked By field.
- Enlarges continuation-page branding by approximately 10% while preserving a more compact hierarchy than page one.
- Uses fit-aware medium and long route-title sizes so multi-route headings remain on one line beside the Checked By field.
- Applies the same sizing to the on-screen Letter preview and popup print document through the shared stylesheet.
- Reserves safe vertical space by adjusting logical row limits to 24/25 in Portrait and 25/26 in Landscape for first/continuation pages.
- Preserves Default Letter margins, repeating filters and footer, glass headings, alternating rows, Rush/remake frames, and the v0.221 idle-state recovery.

## Install v0.221

1. Start from the maintained v0.220 project.
2. Extract the v0.221 changed-files ZIP directly into the current project folder.
3. Preserve the existing `data` folder and database files.
4. Restart the scanner server and refresh the browser with `Ctrl+F5`.

No database migration or separate setup script is required. v0.221 keeps schema version 5.

## v0.221 highlights

- Preserves already loaded delivery-list item detail when the 10-second background catalog heartbeat returns an unchanged lightweight list summary.
- Invalidates cached print rows only when list revision fields actually change, then reloads only the selected lists on demand.
- Reasserts committed route state when the tab regains focus, returns from browser history, or becomes visible again.
- Keeps the recovery event-driven; unchanged heartbeats perform no Print / Export rerender and no extra API request.
- Prevents a long-idle page from showing Airport as selected while preview/print rows have silently been discarded.

## Install v0.220

1. Start from the maintained v0.219 project.
2. Extract the v0.220 changed-files ZIP directly into the current project folder.
3. Preserve the existing `data` folder and database files.
4. Restart the scanner server and refresh the browser with `Ctrl+F5`.

No database migration or separate setup script is required. v0.220 keeps schema version 5.

## v0.220 highlights

- Removes the Date write-in field from delivery-list signoff and keeps one right-aligned `Checked By` line.
- Repeats the compact active Filters summary on first and continuation pages.
- Uses route-specific gradients for Airport, Indian Trail, Greenville, CPU, and DTC choices.
- Groups visible glass types under compact Mirror, Tempered, and Annealed separators with matching category colors.
- Gives All/Not Scanned/Partial/Complete and Attention choices distinct, readable gradients.
- Adds Scan-page-style red exclamation circles when Remakes, Rushes, or Internal Rejects exist and green check circles when each category is clear.
- Reduces continuation-page row limits by one logical row to reserve safe space for the repeating filter line.
- Preserves the shared preview/print stylesheet, 90% Portrait preview zoom, Letter geometry, print logo, pagination, gray bands, alternating rows, and repeating Printed at footer.

## v0.219 highlights

- Moves the first-page Checked By and Date signoff box slightly lower so it aligns more naturally with the branded title block.
- Forces both signoff labels and the full delivery date to remain on one line.
- Makes the popup print document load the same maintained `static/css/styles.css` used by the preview instead of carrying a second duplicated formatting definition.
- Waits for the shared stylesheet, fonts, and logo image before opening the browser print dialog.
- Keeps only physical Letter-page and printer-margin overrides inside the popup, preventing future preview/print formatting drift.
- Sets Portrait preview to 90% by default, including after returning from Landscape mode.
- Preserves Letter dimensions, default 0.4-inch margins, pagination, table geometry, gray bands, alternating rows, remake/rush frames, and footer placement.

## v0.218 highlights

- Restores the supplied Barefoot Company / Builders FirstSource logo asset to the changed-files package so preview and popup print documents render the actual artwork rather than fallback alt text.
- Resolves the logo through an absolute application URL with a v0.218 cache key, keeping popup printing reliable after upgrades.
- Removes the continuation-sheet sentence beneath the title while retaining the top-right page number.
- Keeps route-driven delivery-list titles on one continuous line and automatically scales unusually long multi-route titles instead of wrapping them into an indented second line.
- Enlarges the full weekday date to sit just below the title in the same visual hierarchy.
- Tightens the vertical gap between `Rows | Orders | QTY` and the active Filters line.
- Preserves pagination, gray bands, alternating rows, first-page signoff fields, remake/rush borders, and repeating Printed at footers.

## v0.217 highlights

- Displays delivery dates in the readable `Tuesday, August 4, 2026` format across the browser application, including the Home page and Delivery List views.
- Replaces the print header's compact numeric date-first wording with a route-first title such as `INDIAN TRAIL DELIVERY LIST`.
- Joins multiple selected routes with vertical separators, such as `GREENVILLE | CPU | DTC DELIVERY LIST`.
- Places the full weekday date directly beneath the route title in preview and actual paper output.
- Expands the adaptive Print / Export date control so full weekday dates and custom ranges remain readable.
- Preserves the supplied print logo, page totals, filters, signoff fields, pagination, gray bands, alternating rows, and repeating footer.

## v0.216 highlights

- Adds the supplied stacked Barefoot Company and Builders FirstSource logo as a dedicated print asset and uses it in preview and generated print pages.
- Crops only the unused outer canvas around the supplied logo, retaining the artwork itself and a clean white print margin.
- Removes the extra title/header divider above the table on normal, Rush, remake, and continuation pages while preserving the black divider between column headings and glass-type groups.
- Places the active Filters line on its own line directly beneath `Rows | Orders | QTY`.
- Preserves v0.215 date-first titles, dynamic destinations, alternating rows, gray table bands, pagination, remake/rush frames, and repeating footer.

## v0.215 highlights

- Makes the delivery date the dominant top-left heading in compact `M/D/YY` format.
- Places `Delivery list for <destination>` beneath the date and derives the destination from the committed Route selection.
- Reuses the existing sidebar Barefoot/Builders FirstSource logo beside the title with grayscale and contrast treatment for black-and-white printing.
- Adds a strong black divider between the column headings and every glass-type subheader.
- Alternates printable order rows between white and light gray while preserving exact print colors in Chrome and Edge.
- Preserves v0.214 page capacities, first-page signoff details, compact continuation headers, gray heading bands, and repeating footer.

## v0.214 highlights

- Raises Portrait pagination to 25 logical rows on first pages and 27 on continuation pages.
- Raises Landscape pagination to 26 logical rows on first pages and 28 on continuation pages, with glass headings still counted toward the page limit.
- Keeps Checked By, Date, and active Filters only on the first page of each delivery-list section; continuation pages retain the title, page identification, and totals.
- Moves `Printed at` into the bottom-left footer of every page.
- Centers Route in both preview and actual print output.
- Forces gray column-header and glass-type subheader backgrounds to print in Chrome and Edge.

## v0.210 highlights

- Commits Airport to maintained Print / Export state before the GUI becomes visible, rather than relying on the route chip's checked appearance.
- Replaces the redundant reset-then-reapply startup sequence with one awaited initialization transaction.
- Prevents stale route controls from a previous GUI session from overwriting the new session's Airport default.
- Shows loading filter content and disables empty output until the current delivery-list details are ready.
- Makes an immediate Print or Export click wait for initialization and then revalidates the committed Airport route.
- Invalidates late asynchronous work when Print / Export closes or reopens, preventing an older session from replacing the active one.
- Preserves the v0.209 system default preset, landscape sheets, print totals, preset redesign, and schema version 5.

## v0.209 highlights

- Moves Delivery Date directly beside the Filters section title while keeping Create Preset, Saved Presets, and Clear Filters grouped on the right.
- Raises all four header controls to the same larger 12.5-pixel type size with centered labels and icons.
- Rebuilds Create Preset as a guided two-step workspace with a clear naming panel, system-default explanation, usage guide, balanced filter cards, and responsive output controls.
- Adds an immutable **System Default · All Items** preset for every user and applies it automatically when Print / Export first opens.
- Defines the system default as Airport/all outbound items, All Glass, All Status, All Attention, PDF, one copy, and Portrait.
- Preserves user-created presets separately and prevents the reserved System Default name from being overwritten.
- Adds a true landscape delivery-list layout with orientation-specific pagination, tighter row geometry, wider Dimensions and Customer columns, and a shorter notes area.
- Shows Total printable rows, Total orders, and Total QTY above Printed at on every delivery-list sheet and continuation page.
- Replaces the remake sheet's edge border with an inset dashed outline so all four corners remain inside the printer-safe area.
- Preserves v0.208 exact glass matching, the custom range calendar, Lookup Manager glass library, exact order/item selection, PDF/XLSX/CSV output, and schema version 5.

## v0.208 highlights

- Fixes exact glass-type selections showing valid counts while the document preview incorrectly displayed zero rows.
- Stores route and exact glass selections in stable application state before filter controls are replaced or rerendered.
- Filters imported products with normalized Unicode, inch/quote marks, whitespace, and case comparison while retaining the original maintained product label for presets and output.
- Preserves Airport as the complete outbound route without requiring users to click Airport again after choosing a glass type.
- Restores saved glass-type presets against normalized product identities so minor formatting differences do not invalidate a known selection.
- Centers Delivery Date, Create Preset, Saved Presets, and Clear Filters text and icons within their compact header controls.
- Preserves the v0.207 custom-range calendar, Lookup Manager glass library, user-scoped presets, exact print rows, exports, and schema version 5.

## v0.207 highlights

- Removes repeated Delivery Date / Date Range prefixes so the selector displays clean dates and ranges.
- Keeps Custom Range open after the first date, requires a second date, and closes only after Apply Dates or an explicit cancel/outside click.
- Increases Delivery Date, Create Preset, Saved Presets, and Clear Filters text to the same 10.5-pixel size used by filter-chip content.
- Preserves Airport, All Glass, and exact glass selections through initial asynchronous filter rendering so first-use glass filtering no longer produces a false zero-row preview.
- Reflows Create Preset into filled three-column and responsive two-/one-column layouts with no blank section beside Attention.
- Loads every maintained Lookup Manager product value for the Glass Types preset library and displays its friendly product-name label.
- Keeps Create Preset immediate by prefetching the small lookup library and enriching the open modal without loading historical delivery lists.
- Preserves user-scoped presets, exact preview/print rows, PDF/XLSX/CSV output, and schema version 5.

## v0.206 highlights

- Reduced Delivery Date, Create Preset, Saved Presets, and Clear Filters to compact 34-pixel controls.
- Keeps all four Print / Export header controls aligned on one desktop row, with controlled wrapping on narrower screens.
- Rebuilt the Create Preset modal with a clearer name section, polished category cards, improved output controls, and responsive layout.
- Opens Create Preset immediately from already-loaded data instead of fetching every historical delivery list.
- Removed lifetime glass-type quantity totals from preset creation; the builder now stores and displays glass-type names only.
- Added a glass-type search field inside Create Preset for faster selection.
- Fixed Custom Date Range closing immediately when chosen from the enhanced Delivery Date dropdown.
- Preserved user-scoped preset storage, active-preset restoration, exact preview/print behavior, and schema version 5.

## v0.205 highlights

- Gives Delivery Date, Create Preset, Saved Presets, and Clear Filters one consistent 40-pixel control system.
- Keeps Custom Date Range as the first date-selector option while individual delivery dates remain one-click choices.
- Replaces the old mixed single/range calendar with a two-month Date From / Date To range picker.
- Highlights today, marks known outbound dates, and requires both range endpoints before Apply Range is enabled.
- Loads glass types from every currently known delivery list before opening the preset builder.
- Stores presets and the active preset under the signed-in user instead of sharing one browser-wide active choice.
- Automatically reapplies the user's active preset whenever Print / Export is reopened, until that user selects another preset or clears filters.
- Preserves the working v0.204 preview, visual polish, exact item/order selection, and direct-print workflow.

## v0.204 highlights

- Repairs the preview page container that expanded to an extreme off-screen width and left the visible preview pane blank.
- Keeps every preview page centered inside a normal-width, vertically scrollable document stack.
- Uses layout-aware preview zoom instead of applying competing transforms to both the page stack and each sheet.
- Preserves the exact delivery-list sheet markup shared by the preview and the working print popup.
- Rebalances the control center so the filter workspace and document preview fit normal floor-monitor widths cleanly.
- Gives Route, Glass Type, Status, Attention, order search, and selected items consistent card spacing and typography.
- Allows long filter labels to wrap instead of clipping or overlapping their quantity values.
- Refines the Filters header so Delivery Date, Create Preset, Saved Presets, and Clear Filters remain aligned without crowding.
- Polishes the preview toolbar, paper background, page shadow, status badge, zoom controls, and output footer.
- Makes Copies, Layout, File Type, and Print/Export controls wrap safely on narrower panes rather than overlapping.
- Updates the visible footer version and browser cache keys to v0.204.

## v0.203 highlights

- Moves the delivery-date selector into the right side of the Filters heading.
- Lists individual delivery dates in the maintained dropdown and keeps Custom date range as the first choice.
- Opens the existing calendar for custom ranges with today's date highlighted.
- Reorders the filter workspace to Route and Glass Type on top, Status and Attention below, and exact orders/items at the bottom.
- Replaces the Copies dropdown with a one-to-ten increment control.
- Replaces the Layout dropdown with exclusive Portrait and Landscape buttons.
- Prints synchronously from the exact browser preview so popup blockers do not suppress the print window after an asynchronous request.
- Uses CSS `@page` portrait or landscape sizing so the browser print dialog reflects the selected layout.
- Makes the preview and printed document share the same sheet titles, glass grouping, continuation pages, row limits, columns, notes box, Rush styling, and remake styling.
- Removes the failed preview-reconciliation warning and keeps spreadsheet exports on the authenticated exact-row session path.
- Reinforces smart searching by loading current list detail before matching order, item, customer, glass, or Job Nr. text.

## v0.202 highlights

- Replaced GET-only print reconciliation with an authenticated POST selection contract carrying the exact visible row IDs.
- Creates a short-lived same-user output token so Print, PDF, XLSX, and CSV use the same locked selection as the preview.
- Fixed Print List failing after a valid live preview reported that server reconciliation returned no rows.
- Searches order number, item number, customer, and Job Nr. values while typing.
- Lets operators add either one exact item or the complete order to Selected Orders & Items.
- Supports removing exact items and whole orders independently or clearing the complete selection.
- Removes dates and exact customer/order choices from saved presets.
- Adds file type, copy count, and portrait/landscape layout to the Create Preset GUI.
- Moves the compact Create Preset and Saved Presets controls beside Clear Filters.
- Shows every delivery-list preview page in one vertically scrollable document instead of using a page-number selector.
- Adds copy count and portrait/landscape selectors beside the maintained file-type selector.
- Keeps PDF paired with Print List; XLSX and CSV remain paired with Export List.

## v0.201 highlights

- Selecting **All Glass** deselects every exact glass type and represents a true unrestricted glass selection.
- Selecting any exact glass type clears All Glass; clearing every exact type restores All Glass.
- Repaired the live preview gate so All Glass no longer appears as zero selected glass types.
- Keeps All Status and All Attention the same size as the other filter buttons and positions each in the top-left of its section.
- Moves Date Selection to the top of the Print / Export filter workspace.
- Adds one calendar GUI with Single Date and Custom Range modes.
- Highlights today's date and marks dates that have outbound delivery lists.

## v0.199 highlights

- Forces white text and quantity counts on every selected Print / Export filter.
- Converts customer, Job Nr., and order searching into an explicit multi-order picker.
- Keeps selected orders in a removable list with individual and Clear All controls.
- Stores selected exact orders in browser presets and sends them to preview, print, PDF, and XLSX output.
- Replaces the browser prompt with a dedicated Save Preset GUI and overwrite guidance.
- Places Route choices in a vertical rail on the right side of the filter workspace.
- Narrows the preview pane and renders a letter-shaped delivery-list page using the real print columns and glass grouping.
- Draws a live preview immediately from loaded rows, then reconciles it with the exact backend print package.
- Keeps the live preview visible as a fallback if exact preview reconciliation fails instead of leaving a blank page.

## v0.198 highlights

- Removed the Stage filter from Print / Export and made Route the primary list selector.
- Added the maintained Route choices: Airport, Indian Trail, Greenville, CPU, and DTC.
- Airport includes every item on the selected Airport Outbound delivery lists; destination routes filter those outbound items to the selected destinations.
- Repaired the missing Route, Status, Attention, and Glass Type sections by removing a call to a nonexistent browser helper.
- Added a Quick Date selector that sets the start and end dates to one available delivery date while preserving the full date-range controls.
- Rebuilds Glass Type choices from the glass types that actually exist in the selected date range and route selection.
- Added smart Search suggestions that surface matching orders while typing a customer, complete or partial order number, or Job Nr.
- Extended backend search matching to Job Nr., product, and source identifiers so preview, print, and XLSX remain aligned.
- Removed the extra decorative circle from the Print / Export header.
- Preserved the exact backend preview, output safeguards, presets, PDF/XLSX controls, and scanner-panel header.

## Start the local web app

1. Keep `Start-DeliveryScannerWebApp.bat` and `Start-DeliveryScannerWebApp.ps1` beside `server.py`.
2. Keep the existing `data`, `assets`, `sounds`, and `static` folders in the project folder.
3. Double-click `Start-DeliveryScannerWebApp.bat`.
4. Keep the launcher window open while the local server is running.

SQLite remains the active/default database. The production database is:

`data\delivery-scanner-pilot.db`

Keep this file and its `-wal`/`-shm` companions together whenever the app is running. Before any numbered schema upgrade, startup creates and verifies a version-labeled backup under `data\backups`. Production databases are never deleted or recreated automatically.

## Database preservation

The `data` folder is production state, not application source. Never replace or delete it during a code-only update. Stop the server and copy the complete folder, including SQLite `-wal` and `-shm` companions, before transferring a floor database to another checkout.

## Cross-delivery-date scanning

The settings are available under **Admin > Cross-Date Scanning**:

- **Disabled** — scans remain limited to the selected delivery list.
- **Ask before switching** — every valid cross-date match requires operator confirmation.
- **Automatically switch unique matches** — one safe match switches and scans automatically; ambiguous or guarded matches require confirmation.

The default search window is:

- Past delivery dates: **7 days**
- Future delivery dates: **30 days**

The backend always checks the selected list first. Cross-date searching begins only when the barcode cannot be uniquely resolved on that list. Candidate lists must be active, inside the configured date window, accessible to the signed-in user, and in the same operational stage category.

The existing safety rules remain authoritative. Cross-date scanning does not bypass:

- completed quantity checks;
- duplicate handling;
- user stage access;
- outbound staging and transportation requirements;
- Indian Trail outbound requirements;
- rack status and destination compatibility;
- manual bay selection;
- supervisor override workflows; or
- undo/redo and immutable scan history.

## Automated delivery-list imports

The maintained automation package is under `automation\sql_delivery_export`.

### Floor computers: import the shared folder every hour

1. Extract the newest changed-files package into the current scanner project folder.
2. Close the scanner web app/server window.
3. Run `automation\sql_delivery_export\Setup-DeliveryListSqlAutomation.bat` once.
4. Restart the scanner web app and confirm **Admin > Delivery Automation Control Center** shows **Import Temp Folder Only** with the schedule installed.
5. Run `C:\DeliveryListAutomation\Run-Now.cmd` for a visible manual verification.

The floor setup copies the maintained runtime to `C:\DeliveryListAutomation\Scripts`, uses the existing shared Temp Delivery Lists folder, creates a 60-minute incremental task plus the normal daily full-window safety task, and disables the older built-in 5 PM importer for that Windows user. It does not query A+W SQL or replace the scanner database.

### Central authorized computer: query SQL, export, and import

Use the normal SQL automation setup and the Admin control center. Run `C:\DeliveryListAutomation\Verify-SQL-And-Import.cmd` with a known delivery date to verify the read-only SQL query, workbook generation, publication, maintained scanner import, and expected stage lists.

See `automation\sql_delivery_export\README.md` for the installed runtime and troubleshooting steps.

## Database operations

- Azure migration dry run: `py -3 -m database.migrate_sqlite_to_azure_sql --sqlite-path data\delivery-scanner-pilot.db`
- SQLite migrations are owned by `database\migrations.py`.
- The logical cross-database contract is owned by `database\contract.py`.
- v0.218 application contract: **218**.
- Current SQLite schema contract: **5**.

## Optional container deployment

Docker and Azure App Service support files are organized under `deployment`. They are not required for normal Windows floor operation.

- Container definition: `deployment\docker\Dockerfile`
- Container-only dependencies: `deployment\docker\requirements.txt`
- Azure App Service setting template: `deployment\azure\app-service.env.example`

Run the Docker build from the project root so the root `.dockerignore` protects local databases, secrets, logs, backups, and verification output:

```powershell
docker build -f deployment/docker/Dockerfile -t delivery-list-scanner .
```

## Audio language

The maintained sound pack is stored under `sounds\` as 44.1 kHz, 16-bit PCM mono WAV files. Open `sounds\preview_audio_pack.html` in a browser to audition the packaged cues without installing audio software. The web app loads semantic cue names from `static\js\app.js`, uses the existing shared volume/compressor chain, and falls back to synthesized tones only if a WAV file cannot be loaded.

v0.194 maps `delivery_date_changed` to the already packaged `sounds\scan_success.wav` cue. Normal accepted scans continue using `sounds\notification.wav`, so no binary sound asset is included in this changed-files release.

## Microsoft Graph email

Microsoft Graph delivery supports customer manifests, ready notices, and Admin test messages. The configured sender is `BarefootNC.Glass@bldr.com`, and the default controlled test recipient is `brandon.m.smith@bldr.com`.

After BLDR IT provides the Entra tenant ID, application/client ID, and client-secret value, run `Configure-MicrosoftGraphEmail.bat` once. The secret is encrypted for the current Windows account and loaded only in memory by the normal scanner launcher.

## Project documentation

- Ongoing version history: `README_CHANGELOG.md`
- Current folder ownership and cleanup guide: `docs/PROJECT_STRUCTURE.md`
- Automated SQL export/import runtime: `automation/sql_delivery_export/README.md`

## Important local folders

- `static` — maintained browser CSS, JavaScript, and image source.
- `assets` — favicon and print-page assets referenced by the server.
- `sounds` — maintained browser audio cues.
- `data` — required SQLite database and local scanner state. Keep it and back it up.
- `automation` — scheduled delivery-list import/export source and setup scripts.
- `scripts` — optional Windows setup and diagnostic utilities.
- `resources` — source material retained for A+W integration work.
- `logs` — generated diagnostics. Safe to clear while the app is stopped.
- `backups` — retained recovery copies. Review dates before removing anything.
- `C:\DeliveryListAutomation` — installed automation runtime, staging, logs, and task state.

The release ZIP contains no database, SQL credential, SAP runtime, demo delivery list, or new audio binary. When upgrading, keep the existing `data` folder. Production startup never seeds demo delivery lists; existing data is preserved and upgraded in place only after a verified backup succeeds.

Do not run the SQLite and Azure SQL versions as simultaneous writable production systems during a future cutover.


## v0.236 Manual-order protection

Manual orders can be marked **Protect from A+W import** when created or edited. Protected rows remain separate and active if A+W later publishes the same order/item. Unprotected manual duplicates may be retired by authoritative reconciliation. Source-provided remake markers now clear when A+W removes the flag, while operator-marked Priority Work remakes remain protected by their audit history. SQL automation logs include the exact remake order/items and raw header flags used for classification.
