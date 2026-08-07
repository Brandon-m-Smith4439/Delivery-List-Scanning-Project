# Delivery List Scanner Changelog

## v0.254 - Stable Manual Delivery List Expansion

- Removed automatic opening of changed delivery-date groups in Delivery List Management.
- Restored manual expand/collapse control while retaining the complete stage view introduced in v0.253.
- Added stable delivery-group keys and preserved each user's open/closed choices across recent-import and automation-status refreshes.
- Avoided replacing the Delivery List Management DOM when the normalized data markup has not changed, preventing repeated background checks from flashing the section.
- Removed the animated max-height/opacity replay from Delivery List Management stage tables and returned them to native details visibility.
- Preserved Airport Road consolidation, route-accurate preview filtering, historical preview recovery, and existing print/export behavior.
- Updated maintained application references and cache keys to v0.254. SQLite schema remains version 10.

## v0.253 - Complete Stage View, Route-Accurate Preview, and Historical Recovery

- Restored every Delivery List Management stage row for the selected import/date instead of showing changed routes only.
- Collapsed only the duplicate Staging and Outbound rows into one Airport Road row; Indian Trail, Greenville, CPU, DTC, and custom stages remain individually visible with original, change, current, and status information.
- Kept changed delivery dates automatically expanded while unchanged stage rows remain visible as `No Updates`.
- Changed preview classification to use each order snapshot's actual route before using stage/scanner fallback, preventing Greenville orders from appearing in the Airport Road preview group.
- Routed standard route preview buttons through the authoritative Airport Outbound list and applied an exact route-group filter in the browser, eliminating stale CPU stage IDs and duplicate cross-stage snapshots.
- Added historical list metadata fallback so retired or missing stage records can still return their saved change snapshots instead of `Delivery list was not found`.
- Supplemented newly-created stage previews from the current item catalog when older notice batches retained fewer snapshots than the recorded changed-line count.
- Preserved the delivery-date header preview as the all-route view and preserved exact Print / Export route selection.
- Updated maintained application references and cache keys to v0.253. SQLite schema remains version 10.

## v0.252 - Route-First Delivery Management and Exact Route Printing

- Replaced Staging and Outbound rows in Delivery List Management with one Airport Road route row and retained Indian Trail, Greenville, CPU, and DTC as the remaining route rows.
- Limited each changed delivery-date expansion to routes actually changed by that import and automatically opened delivery dates that contain changes.
- Reserved New management status for a newly-created delivery list or route; existing routes remain Updated even when they contain newly-added orders.
- Classified every retained order in a newly-created route as New in Delivery List Update Preview while preserving explicit Removed order snapshots.
- Removed nested stage wrappers from the preview so route dropdowns open directly to changed orders, item details, and before/after values.
- Chose one representative preview stage per route, with Outbound preferred for Airport Road, preventing duplicate Staging/Outbound order cards.
- Routed all management print actions through the Airport Outbound source list and preselected the exact Airport Road, Indian Trail, Greenville, CPU, or DTC filter in Print / Export.
- Kept the delivery-date header print action on Airport Road, representing the complete outbound delivery list across all routes.
- Corrected preview eye buttons to the same 34-by-34 square footprint as print buttons.
- Updated maintained application references and cache keys to v0.252. SQLite schema remains version 10.

## v0.251 - Cross-Stage Preview Access and Durable Daily Import History

- Fixed Delivery List Update Preview returning `Permission denied for this delivery-list stage` to Admin/Supervisor and fully authorized Delivery List Management users when the changed run included stages outside their ordinary scanner assignment.
- Preserved every already-loaded same-day import while the newest manual or automated run is refreshed from durable history.
- Changed live import snapshots from replace behavior to stable-key merge behavior and immediately refreshes complete current-day audit history after each run.
- Prevented identical-result imports with different stable run IDs from being collapsed as duplicates merely because they occurred close together.
- Reorganized the update-preview GUI into initially collapsed Airport, Indian Trail, Greenville, CPU, and DTC workflow groups.
- Added exact stage sections, location-level New/Updated/Removed badges, compact totals, and filter-aware expansion while retaining detailed order, item, customer, job, product, dimensions, route, and before/after values.
- Updated maintained application references and cache keys to v0.251. SQLite schema remains version 10.

## v0.250 - Targeted SQL Import Scope Repair

- Fixed the automated importer failure `name 'args' is not defined` that occurred only when a delivery date required an authoritative scanner import.
- Added explicit `run_id` and `run_started_at` parameters to `selective_sql_sync` and passed them from `main()` into the maintained import call.
- Preserved stable run identity in durable import history and notifications without referencing `main()` local variables from a module-level helper.
- Confirmed unchanged dates continue to skip redundant writes while changed/new dates can import normally.
- Updated maintained application references and cache keys to v0.250. SQLite schema remains version 10.

## v0.249 - Import History Dates, Preview Reliability, and Change Totals

- Corrected the Delivery List Management Selected Run layout so its summary and metrics remain compact and aligned instead of stacking into a tall empty panel.
- Changed the stage Changes cell to show updated pieces and removed pieces independently, including both values when a run contains additions/updates and removals.
- Limited update-preview buttons to stages with current new, updated, or removed rows.
- Fixed the legacy update-preview fallback's undefined row helper and added explicit API error responses, eliminating the opaque `Failed to fetch` failure.
- Made multi-stage previews tolerant of one failed stage while preserving the successfully loaded stage details.
- Rebuilt Automation Control Center import-history grouping around raw timestamps and stable run IDs, preventing shortened timestamps from being interpreted as year 2001.
- Added full-year visible timestamps and polished day, run, metric, status, and file-result cards in Automation Control Center.
- Preserved new-piece and updated-piece totals through import normalization, durable change summaries, API history, and browser signatures.
- Updated maintained application references and cache keys to v0.249. SQLite schema remains version 10.

## v0.248 - Complete Daily Import History and Item-Level Change Preview

- Added stable run IDs across the automation runner, importer, import audit records, notifications, and browser so one automation run has one identity everywhere.
- Stopped Delivery List Management from collapsing repeated same-day imports by delivery date/source name and from duplicating the newest runtime result beside its durable database record.
- Loads every available current-day result across the paginated audit history, retains every run, and paginates the Recent Imports tabs without a 100-run cutoff.
- Removed the second per-run date-only de-duplication layer so every legitimate file result in the selected run remains visible.
- Added a polished daily activity heading, run/file totals, selected-run metrics, clearer tabs, and improved responsive presentation.
- Rebuilt Delivery List Update Preview with concise copy, All/New/Updated/Removed filters, order/item search, prominent order details, and compact item cards.
- Added durable previous-value snapshots and changed-field lists so updated rows can show exact before/after values in the preview.
- Updated maintained application references and cache keys to v0.248. SQLite schema remains version 10.

## v0.247 - Review Queue Installation Repair and Simplified Active Totals

- Reissued the complete Superseded Order Review implementation, including `backend/store.py`, API routes, schema support, browser assets, and automation files, so partial overlays cannot leave the importer without `sync_superseded_order_candidates`.
- Added a precise runtime diagnostic with the loaded store-module path when an incomplete installation is detected.
- Corrected automation logging so a failed advisory review sync is not also reported as a successful sync.
- Simplified Delivery List Management quantity cells and date summaries to one active value such as `129 pcs`; removed duplicate `A+W pcs` and `active total` wording.
- Replaced misleading ownership-breakdown logging with a single active total when unchanged-stage verification does not return source/manual counters.
- Preserved successful scanner imports, exact-key approvals, Keep Both, Review Later, manual protection, and SQLite schema version 10.
- Updated maintained application references and cache keys to v0.247.

## v0.246 - Automatic Import Result and Notification Recovery

- Fixed the Windows PowerShell 5.1 `Argument types do not match` failure caused by serializing generic list objects directly in notification and last-run payloads.
- The runner now reads a normalized import result even when Python returns a nonzero exit for one failed workbook, allowing successful dates to remain successful and failed dates to be reported individually.
- Superseded Order Review queue persistence is now advisory and cannot abort delivery-list imports; failures are retained as warnings with a traceback in the result file.
- Failure notifications can no longer mask the original automation exception. Full error details are also written to `State\last-error.txt`.
- Increased the selective-sync request JSON depth so complete candidate item evidence is preserved.
- Updated maintained application references and cache keys to v0.246. SQLite schema remains version 10.

## v0.245 - Local Superseded Order Review and Exact-Key Approval

- Removed production status as an automatic delivery-list membership decision. Status values are evidence only.
- Added local candidate detection using shared A+W Header Identity (`AH_IDENT`), older order status 410/item status 0/no production batch, a newer active-batch order, and matching job/item evidence.
- Added the Delivery List Management **Superseded Order Review** workspace with side-by-side item comparison, live scanner impact, and explicit Approve / Keep Both / Review Later actions.
- Added SQLite migration 10 and Azure SQL compatibility for durable candidate evidence, decisions, fingerprints, and audit metadata.
- Approval removes only exact A+W-owned delivery-date/order/item keys, preserves protected manual entries, creates removed-line preview snapshots, updates stage revisions, and records audit/history entries.
- Added `data/superseded-source-exclusions.json`, generated atomically from approved reviews and merged into the SQL exporter with the existing historical exact exclusions. Non-approved review decisions publish preservation overrides so Keep Both, Review Later, or changed evidence can restore an older bootstrap-excluded row.
- Candidate decisions remain stable while evidence is unchanged; materially changed evidence returns the candidate to pending review.
- Updated maintained application references and cache keys to v0.245.

## v0.244 - Raw Date Restore and Schedule-Membership Investigation

- Removed the unsafe universal `460` order/item status and production-batch eligibility filter that was excluding valid future, internal-reject, and not-yet-cut delivery-list rows.
- Restored every raw A+W row matching the planned delivery date, with production statuses retained only as diagnostics.
- Added a maintained exact-exclusion file for the eight 8/3/2026 order/item rows directly verified absent from Crystal, avoiding job-number or dimensional duplicate guesses.
- Paused unverified automatic source-row removals while continuing additions, updates, remake changes, route changes, and unprotected manual-duplicate retirement.
- Allowed exact Crystal-verified exclusions to retire known obsolete rows while the general removal pause is active.
- Updated selective SQL drift checks so retained unverified source rows do not trigger endless re-import loops.
- Added a SELECT-only A+W schedule-membership probe covering `POOL_TEILE`, header `LADELISTE`, `BW_LADELISTE`, and `TEMP_DELIV`.
- Added the verified-exclusion file to startup/runtime synchronization under `C:\DeliveryListAutomation\Scripts`.
- Preserved protected manual orders and SQLite schema version 9; no database migration is required.
- Updated maintained application references and cache keys to v0.244.

## v0.243 - Date-Scoped Eligibility Safety Deferral

- Fixed a future/incomplete delivery date exceeding `MaxExcludedPercent` aborting the entire automatic Incremental or Full window before already-safe dates could be imported.
- Changed the A+W eligibility safety guard to defer only the suspicious delivery date, preserving its existing workbook and scanner rows without publishing a partial source set.
- Continues processing and importing every safe delivery date in the same run.
- Added `safetyDeferredDates` and detailed raw/eligible/excluded percentage diagnostics to the persisted run summary and app-notification payload.
- Added warning completion and notification wording so a protected deferral is visible without being reported as a total automation failure.
- Preserved the verified status/item/batch eligibility rule, protected manual orders, retained change previews, and SQLite schema version 9.
- Updated maintained application references and cache keys to v0.243.

## v0.242 - Live Active Totals, Manual-Row Diagnostics, and Retained Change Preview

- Fixed Delivery List Management so current quantities come from the live active scanner stages rather than stale automation-history summaries.
- Added A+W-owned, manual, protected-manual, and total-active quantity breakdowns to list summaries, stage results, and the automation log.
- Kept no-change result list IDs separate from changed list IDs so a verification run remains correctly classified.
- Kept the eye preview available after a later No Changes run by using retained notice/import-history snapshots independently of the selected run classification.
- Forced the selected Scan page to reload when catalog totals, revisions, matching import results, browser focus, or visibility indicate stale detail.
- Added live item/remake totals to delivery-list detail responses so the browser can verify rendered Scan rows against the database response.
- Updated the Remakes badge to distinguish A+W remake pieces from preserved manual remake pieces when both are present.
- Preserved SQLite schema version 9; no database migration is required.

## v0.241 - Active Scan Refresh and Complete Change Preview

- Fixed the Scan page retaining stale pre-import line items after an external SQL import updated the database and Delivery List Management catalog.
- Added delivery-list revision awareness to browser catalog caching and automatic active-list detail reloads when revision, item count, or total quantity changes.
- Added durable per-stage `changeItems` snapshots for New, Updated, and Removed rows inside import history without changing the database schema.
- Updated the Delivery List Update Preview endpoint to merge normal notice snapshots with import-history snapshots and report the expected changed-line count.
- Added a visible legacy-history warning when an older import summary contains more changed lines than available item snapshots and clarified that a no-change rerun cannot reconstruct missing historical rows.
- Replaced numeric preview-button badges with a guaranteed inline eye icon while preserving detailed accessible labels and tooltips.
- Fixed the A+W eligibility summary log format so raw, eligible, excluded, and remake counts replace all PowerShell placeholders.
- Updated maintained application references and cache keys to v0.241. SQLite schema version 9 is unchanged.

## v0.240 - PowerShell Eligibility Log Parser Repair

- Fixed the SQL automation runner failing at parse time before any A+W query because a colon immediately followed `$dateKey` inside a double-quoted PowerShell string.
- Replaced the unsafe interpolation with the PowerShell format operator so excluded-row diagnostics remain readable without being parsed as a scoped variable reference.
- Added a regression assertion preventing direct `$variable:` interpolation from returning to the maintained runner.
- Retained manual/scheduled run isolation, A+W report-eligibility filtering, protected manual orders, and SQLite schema version 9.
- Updated maintained application references and cache keys to v0.240.

## v0.239 - Manual and Scheduled Automation Run Isolation

- Fixed a one-date browser request appearing as `Incremental` / `Configured` and showing a multi-day scheduled-task log when the two runs overlapped.
- Added a dedicated browser-run summary file and request ID so the web controller never reads a scheduled run's shared `last-run.json` as the manual result.
- Added a pre-launch shared-lock check with a clear message when Task Scheduler is already running the delivery-list automation.
- Added a PowerShell `FailIfBusy` path to close the race where a scheduled task starts after the browser's lock check.
- Prevented a skipped overlapping scheduled task from overwriting the active run summary.
- Refreshes maintained automation runtime files when the web app starts, ensuring scheduled tasks use the current exporter and A+W eligibility rules after an update.
- Expanded Status & Logs to distinguish manual requests from scheduled tasks and display the actual date/range mode.
- Retained A+W report eligibility, protected manual orders, and SQLite schema version 9.
- Updated maintained application references and cache keys to v0.239.

## v0.238 - SQLite Migration Registry Startup Repair

- Fixed scanner startup failing with `Database did not reach the expected schema version` when the application contract expected schema 9 but the deployed changed-files overlay did not include the migration-9 registry.
- Added the complete maintained `database/migrations.py` to the repair package so schema contract and numbered migration definitions are deployed together.
- Added a preflight check requiring a continuous migration definition set from version 1 through `CURRENT_SCHEMA_VERSION` before any migration work begins.
- Made the final schema check report installed, defined, missing, unexpected, and expected versions instead of a generic mismatch.
- Confirmed migration 9 remains idempotent when `protect_from_aw_import` columns already exist but the migration ledger is still at version 8.
- Retained the v0.237 A+W report-eligibility query and removal behavior without changing SQLite schema version 9.
- Updated maintained application references and cache keys to v0.238.

## v0.237 - A+W Report Eligibility and Removed Scheduling Rows

- Confirmed the 8/3/2026 remake mismatch originates before scanner import: the raw delivery-date SQL set retained eight old remake item rows after their orders were removed from active scheduling.
- Added source eligibility checks for A+W order status, item status, and header production-batch membership before workbook creation.
- Uses verified defaults of order status `460`, item status `460`, and at least one active `LAUF_PROD1` / `LAUF_PROD2` / `LAUF_PROD3` value; these settings remain overrideable through `SourceMapping.DeliveryEligibility`.
- Excludes the verified obsolete pattern (`STATUS=410`, `POS_STATUS=0`, no production batch) without comparing or collapsing different order numbers that happen to share the same job, dimensions, customer, or product.
- Added raw-versus-eligible line and remake totals plus per-row exclusion diagnostics to the SQL automation log.
- Added a configurable maximum excluded-row percentage so a suspicious source-status change fails closed instead of publishing a mass-removal workbook.
- Added the eligibility-rule signature to the source hash, forcing the first v0.237 run to rebuild and import the corrected workbook even when the underlying A+W rows are unchanged.
- Retained protected manual-order behavior, authoritative order/item reconciliation, and history-safe removed-line handling.
- Updated maintained version references and cache keys to v0.237. SQLite schema version 9 is unchanged.

## v0.236 - Protected Manual Orders and Remake Source Diagnostics

- Added an operator-controlled **Protect from A+W import** option to manual-order creation; it is enabled by default for safer manual workflow entries.
- Added the same protection toggle to the manual line-item editor so authorized users can change the protection state across all workflow-stage copies.
- Added SQLite migration 9 and Azure SQL compatibility columns for `protect_from_aw_import` on line items and manual-entry audit records.
- Authoritative reconciliation now keeps protected manual rows independent even when A+W later publishes the same order/item. Unprotected duplicates continue to be retired.
- SQL drift checks ignore intentional protected manual duplicates while continuing to detect unprotected duplicates.
- Fixed authoritative imports preserving stale source-provided `Remake`/`RM` labels after A+W removed the remake flag.
- Preserved only operator-managed Rush/Remake Priority Work labels whose latest audit action is still active.
- Expanded SQL exporter remake diagnostics to log separate remake line and unique-order counts plus the exact order/item rows and raw A+W header flag values classified as remakes. This makes Crystal-vs-SQL differences directly auditable.
- Updated maintained version references and cache keys to v0.236.

## v0.235 - Authoritative Manual Duplicate Retirement

- Fixed authoritative A+W reconciliation leaving a manual/test duplicate active when the same order and item already existed as a source-owned A+W line.
- Preserves manual-only work only when its order/item is absent from the incoming A+W stage; colliding manual copies are now retired as removed lines.
- Added duplicate-manual line and piece counters to stage summaries, normalized automation results, Delivery List Management history data, and live completion logs.
- Updated scheduled scanner drift detection so a manual row that duplicates an expected A+W order/item forces reconciliation instead of being ignored.
- Added a regression test covering one authoritative source row, one duplicate manual row, and one unrelated manual-only row.
- Updated the visible application version, cache keys, documentation, application contract, and focused tests to v0.235. SQLite schema version 8 is unchanged.

## v0.234 - Runtime Import Schema Guard and Single-Source Reconciliation

- Added an import-time SQLite schema guard that repairs `line_update_notices` before any new, updated, or removed preview notice is written, including automation configurations where `Import.InitializeStore` is disabled.
- Preserves existing notice IDs and `line_update_receipts` while rebuilding the canonical `snapshot_json` and `removed`-change schema.
- Added SQLite schema migration 8 so normal scanner startup records and verifies the same canonical notice-table repair.
- Changed SQL authoritative reconciliation to import the one selected canonical generated workbook directly instead of invoking a whole-folder import that could process both `8.3.26.xlsx` and `Delivery List 08-03-2026.xlsx`.
- Changed Folder Import Only to select and import one deterministic workbook per delivery date from the standalone automation importer.
- Added `schemaRepairApplied` to normalized results and console summaries for direct troubleshooting.
- Updated the visible application version, cache keys, documentation, contract, migration history, and focused tests to v0.234 / SQLite schema version 8.

## v0.233 - Import Notice Schema Recovery

- Added SQLite schema migration 7 to repair databases that recorded the v0.230 migration while still retaining the older `line_update_notices` table without `snapshot_json` or `removed` notice support.
- Rebuilds delivery-list update notices and receipts transactionally while preserving existing notice IDs, review receipts, source hashes, timestamps, and valid snapshots.
- Changed folder-import results to fail whenever any candidate workbook fails instead of returning `ok: true` because unrelated files were skipped.
- Added one-source-per-delivery-date protection for Folder Import Only. When duplicate workbooks exist for the same date, the newest modified workbook is imported and the older duplicate is reported as ignored instead of being applied afterward.
- Updated the SQL automation result normalizer so failed workbook rows cannot be surfaced as a successful import.
- Updated the visible application version, cache keys, documentation, application contract, migration history, and focused tests to v0.233 / SQLite schema version 7.

## v0.232 - Manual Automation Startup and Live Log Repair

- Reverted browser-started automation to the installed `C:\DeliveryListAutomation\Scripts` runtime directory so the PowerShell runner and all adjacent helper scripts execute from one consistent location.
- Added an explicit, atomic runtime synchronization step for `Run-DeliveryListSqlAutomation.ps1`, `import_delivery_folder.py`, and `delivery_import_safety.py` before each manual GUI run.
- Added a caller-supplied per-run PowerShell log path and initialized it before configuration loading, preventing startup failures from leaving Status & Logs at zero lines with no recorded log.
- Added an immediate `PowerShell automation runner accepted the request.` startup record, plus `-NoLogo` and `-NonInteractive` process flags.
- Added runner-path and synchronized-file diagnostics to the live automation status while retaining complete-log polling and v0.231 authoritative A+W reconciliation.
- Updated the visible application version, cache keys, documentation, application contract, and focused tests to v0.232. SQLite schema version 6 is unchanged.

## v0.231 - Authoritative SQL Reconciliation Repair

- Fixed browser-started Custom SQL Export & Import runs so every selected A+W delivery date is force-reconciled even when the generated workbook and exporter state hash are unchanged.
- Changed the automation controller to prefer the maintained project PowerShell runner for manual GUI runs, preventing an older installed runtime copy from bypassing newly deployed reconciliation fixes.
- Added read-only source-row drift detection to scheduled SQL synchronization, comparing every generated stage and source-owned business row instead of treating existing stage IDs as proof of synchronization.
- Added detection for scanner-only rows, removed A+W rows, quantity/detail differences, missing expected stages, and obsolete optional/custom route stages.
- Reconciled fully removed optional/custom route stages against an empty source set so their removed lines appear in import history and update preview before the stage is retired.
- Preserved manual-only rows when a source stage disappears; a stage remains active when manual work is still present.
- Retained historical Delivery List Update Preview snapshots for 365 days while keeping current/future-only unseen-update indicators on the scanning workflow.
- Updated the visible application version, cache keys, documentation, application contract, and focused tests to v0.231. SQLite schema version 6 is unchanged.

## v0.230 - Authoritative A+W Removals and Update Preview

- Made the newest A+W delivery list authoritative for source-owned rows in every imported stage, including imports where the only change is one or more removed items.
- Added history-safe removal handling: unreferenced rows are deleted, while rows referenced by immutable scan, machine, rack, or bay history are soft-deleted and excluded from all active delivery-list workflows.
- Retired active rack assignments as `Removed` and active bay assignments as `Cancelled` when their source line disappears, preserving the historical assignment records and preventing ghost work from remaining active.
- Preserved manually created delivery-list rows unless an incoming source row takes ownership of the same order/item.
- Added schema migration 6 to allow `removed` line-update notices and retain a JSON display snapshot after the active line item has been deleted.
- Added removed line and piece totals to import results, normalized SQL automation results, Delivery List Management summaries, stage summaries, and removal-only update classification.
- Changed Delivery List Management quantity presentation to show removal-only updates as `-N pcs` and mixed updates as distinct added and removed quantities.
- Added a Preview Changes button to every changed stage row, immediately before Print / Export, while retaining the delivery-date-level Preview Changes button.
- Rebuilt Delivery List Update Preview with New, Updated, and Removed groups, stage/date metrics, retained-snapshot guidance, and responsive polished item cards.
- Applied the maintained safe reconciliation wrapper to both SQL and Crystal automatic importer entry points.
- Excluded soft-deleted source rows from active list totals, scanning and cross-date matching, global/admin search, reports, reject matching, rack/bay and Indian Trail workflows, print packages, edit lookups, and administration counts.
- Advanced the application contract, visible version, browser cache keys, documentation, database contract, migration history, and focused structure tests to v0.230 / schema version 6.

## v0.229 - Compact Polished Create Preset Workspace

- Reduced the desktop Create Preset control center from a near-full-screen window to a centered 1240 × 780 maximum while retaining safe responsive sizing at 1024px and mobile widths.
- Increased the typography for preset labels, descriptions, input values, filter choices, selection totals, live summary values, and action buttons.
- Added final v0.229 modal ownership so the smaller centered geometry does not conflict with the v0.228 viewport repair or older modal transforms.
- Reused the maintained Print / Export route, status, attention, All-choice, Mirror, Tempered, and Annealed gradient palettes inside Create Preset.
- Added card accent rails, layered panel gradients, polished controls, and a subtle workspace grid so Create Preset and Print / Export read as one product.
- Preserved internal scrolling, responsive stacking, Lookup Manager glass types, live summary, personal-default selection, and all existing save/apply behavior.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.229. Schema version 5 is unchanged.

## v0.228 - Create Preset Viewport Positioning Repair

- Fixed the v0.227 Create Preset control center being shifted far beyond the top-left of the browser by inherited `top: 50%`, `left: 50%`, and `translate(-50%, -50%)` rules from the legacy compact modal.
- Added a final v0.228 positioning layer that neutralizes the inherited legacy transform while retaining historical class compatibility.
- Added dedicated v0.228 fixed-position ownership with safe desktop and mobile viewport insets.
- Kept the modal workspace internally scrollable and added compact-height tuning for shorter screens.
- Reset the workspace scroll position whenever Create Preset opens and focused the name field without causing viewport movement.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.228. Schema version 5 is unchanged.

## v0.227 - Health-State Attention Filters and Preset Control Center

- Changed Remakes, Rushes, and Internal Rejects so the entire filter button follows its live health state: red gradient with an exclamation when matching work exists, green gradient with a check when clear.
- Rebuilt Create Preset around the supplied control-center reference with Preset Details, Default Filters, Print Options, Preset Summary, and Actions.
- Removed the Visibility and Preview sections from the new preset workspace.
- Added an optional preset description and a personal-default toggle while retaining the immutable System Default fallback for users who do not choose a custom default.
- Added separate Save Preset and Save & Apply actions, live right-column summary updates, copy stepper controls, and responsive layout behavior.
- Preserved the Lookup Manager product library, automatic All-choice collapse rules, grouped newest-first date history, and schema version 5.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.227.

## v0.226 - Automatic All Selections and Newest-First Delivery Dates

- Automatically replaces every available detailed Route selection with Airport, the maintained all-routes choice.
- Automatically replaces complete Glass, Status, and Attention detail selections with their corresponding All choice in both Print / Export and Create Preset.
- Reordered grouped Delivery Date weeks and individual dates from newest/future to oldest so later weeks appear above This Week and historical weeks.
- Restored the v0.224 step-guided Create Preset layout while retaining the v0.225 grouped-date history and in-memory load-more behavior.
- Increased glass-category count typography, changed Tempered section/chip styling from orange to green, and lengthened the borderless Checked By write-in line.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.226. Schema version 5 is unchanged.

## v0.225 - Grouped Delivery Date History and Unified Preset Workspace

- Reduced Landscape continuation-page pagination from 29 to 28 logical rows while retaining 27 logical rows on the first Landscape page and the existing Portrait limits.
- Reworked Create Preset into one continuous workspace with the preset name, compact Route/Status/Attention cards, full Lookup Manager glass library, and output settings visible without step navigation.
- Removed the Step 1 / Step 2 framing and retained immediate current-selection loading, overwrite guidance, per-user storage, and System Default protection.
- Grouped Delivery Date options by Monday-Sunday week with clear This Week, Last Week, Next Week, and dated week headings.
- Limited the initial historical date list to the rolling previous two weeks while continuing to show every available future delivery date.
- Added in-memory two-week history expansion when the user reaches the bottom of the date menu, plus an explicit load-more row for pointer and keyboard access.
- Kept custom date ranges and selected older dates available even when they fall outside the initial history window.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.225. Schema version 5 is unchanged.

## v0.224 - Unavailable Filter States and Aligned Print Signoff

- Grayed out and disabled zero-count Route, Status, New/Updated, and Errors choices in Print / Export so unavailable filters are visually and functionally distinct.
- Kept Remakes, Rushes, and Internal Rejects enabled at zero so their Scan-page-style green-clear and red-alert indicators remain useful.
- Added safe fallback selection behavior when a previously selected route or standard filter no longer contains rows after a date/scope change.
- Increased the filter-chip count font for faster quantity scanning without increasing chip height.
- Removed the border and background around Checked By, enlarged its text, and aligned it with the first-page Filters line at the right side of the title header.
- Increased Rows, Orders, and QTY typography on first and continuation pages while retaining the more compact Filters treatment.
- Preserved v0.223 pagination, table widths, shared preview/print styling, and schema version 5.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.224.

## v0.223 - Table-Adjacent Signoff and Fuller Delivery Pages

- Moved the first-page `Checked By` field out of the branded title block and placed it directly above the delivery-list column headings.
- Kept the signoff right aligned in a compact print-safe row shared by preview and popup printing.
- Increased safe pagination by two logical lines on first pages and three logical lines on continuation pages.
- Set Portrait limits to 26/28 and Landscape limits to 27/29 logical rows for first/continuation pages; glass headings continue to count toward the limit.
- Centered Order, Item, and QTY headings and values in preview and print output.
- Narrowed Dimensions by less than one percentage point and gave that width to QTY so all three letters remain visible.
- Preserved Letter geometry, Default margins, enlarged branded headers, repeating Filters, alternating row bands, fixed Printed at footer, and Rush/remake frames.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.223. Schema version 5 is unchanged.

## v0.222 - Enlarged Branded Delivery-Sheet Headers

- Enlarged the complete first-page title area by approximately 30%, including the supplied print logo, route heading, full weekday date, totals, Filters line, badge, and Checked By signoff.
- Enlarged continuation-page branding by approximately 10% while keeping it visibly subordinate to the first-page header.
- Added fit-aware first-page and continuation-page sizes for medium and long multi-route titles so headings remain on one line.
- Applied all sizing through the shared delivery-sheet stylesheet, keeping preview and popup printing visually identical.
- Adjusted safe pagination to 24/25 logical rows in Portrait and 25/26 in Landscape for first/continuation pages so enlarged headers do not clip table rows or the repeating footer.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.222. Schema version 5 is unchanged.

## v0.221 - Idle Route and Print Row State Recovery

- Fixed the intermittent Print / Export failure that appeared after leaving the browser tab or another app page idle while Airport still looked selected.
- Changed background delivery-list catalog updates to merge lightweight summaries with already loaded item detail instead of replacing `state.lists` and silently discarding print rows.
- Preserves cached item detail only while the delivery-list revision is unchanged; changed lists are invalidated and reloaded on demand.
- Reasserts committed route controls on window focus, `pageshow`, tab visibility recovery, and catalog-sync events.
- Added a single-flight recovery guard so simultaneous focus/catalog events cannot issue duplicate detail requests.
- Keeps recovery event-driven with no new timer, polling loop, or recurring network work. Schema version 5 is unchanged.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.221.

## v0.220 - Print Filter Visual Hierarchy and Compact Signoff

- Removed the Date write-in field from the printed signoff block and kept one right-aligned Checked By line, giving route titles and filter metadata more horizontal room.
- Repeated the compact active Filters line on every delivery-list page, including continuation pages.
- Reduced continuation-page pagination by one logical row in Portrait and Landscape to keep the new repeating metadata inside Default Letter margins.
- Added route-specific gradients for Airport, Indian Trail, Greenville, CPU, and DTC choices in Print / Export.
- Grouped current glass choices beneath compact Mirror, Tempered, and Annealed separator headers with category-specific colors while preserving exact maintained product values.
- Added distinct gradient treatments for Status and Attention choices.
- Added Scan-page-style red exclamation circles when Remakes, Rushes, or Internal Rejects are present and green check circles when those categories are clear.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.220. Schema version 5 is unchanged.

## v0.219 - Shared Preview and Print Styling

- Lowered the first-page Checked By and Date signoff fields within the branded header and kept each field on one uninterrupted line.
- Forced the full weekday delivery date to remain on one line in both Portrait and Landscape layouts.
- Removed the duplicated popup sheet-design CSS and made the generated print window load the same versioned `static/css/styles.css` used by the on-screen preview.
- Retained only Letter page size, 0.4-inch browser margin, page-break, and print-safe frame overrides inside the popup document.
- Added print startup readiness checks for the shared stylesheet, fonts, and supplied logo before invoking the browser print dialog.
- Changed the default Portrait preview zoom to 90%, including when switching back from Landscape.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.219. Schema version 5 is unchanged.

## v0.218 - Reliable Print Logo and Tightened Branded Header

- Restored `static/images/barefoot-company-builders-firstsource-print-logo.png` to the release package so both the Letter preview and popup print document show the supplied artwork instead of fallback alt text.
- Resolves the print logo from the active application URL with a v0.218 cache key, avoiding relative-path ambiguity inside the generated popup document.
- Removed the continuation-sheet sentence beneath the title; page progression remains available in the top-right `List page X of Y` label.
- Prevented route-first titles from wrapping into an indented second line and added automatic medium/long title scaling for multi-route output.
- Increased the full weekday date size so it is nearly as prominent as the delivery-list title while remaining visually secondary.
- Reduced spacing between the totals line and active Filters line in preview and actual print CSS.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.218. Schema version 5 is unchanged.

## v0.217 - Full Weekday Dates and Route-First Delivery Titles

- Standardized delivery-date display text to the full weekday format, such as `Tuesday, August 4, 2026`, across the browser application including Home and Delivery List views.
- Rebuilt the preview and printed header so the selected destination routes form the primary uppercase title, such as `INDIAN TRAIL DELIVERY LIST`.
- Uses vertical separators for multi-route headings, such as `GREENVILLE | CPU | DTC DELIVERY LIST`, while retaining Airport as the safe default destination.
- Places the full weekday date immediately beneath the route title on first and continuation pages.
- Expanded the adaptive Print / Export date selector width for full weekday labels and custom date ranges.
- Preserved the supplied monochrome print logo, totals, filters, signoff fields, page numbering, pagination, gray bands, alternating rows, and footer behavior.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.217. Schema version 5 is unchanged.

## v0.216 - Supplied Print Logo and Cleaner Header Metadata

- Added the user-supplied stacked Barefoot Company and Builders FirstSource logo to `static/images` and switched the delivery-list preview and print package to that dedicated asset.
- Cropped only the broad unused white canvas around the supplied image so the artwork renders larger and cleaner without changing the logo design.
- Removed the extra sheet-header divider immediately above the column headings on normal, continuation, Rush, and remake pages.
- Kept the maintained black divider between the column header row and glass-type subheaders.
- Moved the active Filters summary onto its own line directly beneath `Rows | Orders | QTY` so the metadata order is consistent and easier to scan.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.216. Schema version 5 is unchanged.

## v0.215 - Date-First Branded Print Header and Alternating Rows

- Rebuilt the delivery-list title so the delivery date is the dominant top-left heading in compact `M/D/YY` form, with `Delivery list for <destination>` directly beneath it.
- Derives the printed destination title from the committed Print / Export Route selection, including maintained multi-route labels when more than one destination is selected.
- Reuses the existing sidebar Barefoot/Builders FirstSource logo in the preview and generated print document, applying grayscale and contrast treatment so it remains clear on black-and-white paper.
- Added a solid black divider beneath the column headings and above every glass-type subheader to create a clearer visual break between table structure and grouped products.
- Added alternating white and light-gray order rows with exact print-color adjustment for improved scanability in preview, color printing, and monochrome printing.
- Preserved v0.214 pagination, Route centering, first-page signoff fields, compact continuation headers, gray heading bands, remake/rush frames, and repeating Printed at footer.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.215. Schema version 5 is unchanged.

## v0.214 - Fuller Page Capacity and Repeating Print Footer

- Increased Portrait pagination from 23/25 to 25/27 logical rows while continuing to count glass-type headings so bottom rows remain inside Default Letter margins.
- Increased Landscape pagination from 16/18 to 26/28 logical rows to use the wider page more effectively without allowing rows to enter the footer area.
- Limited Checked By, Date, and the active filter summary to the first page of each delivery-list section; continuation pages use a compact title and totals header.
- Moved `Printed at` into a fixed bottom-left footer on every preview and printed page.
- Center aligned Route in Portrait and Landscape preview/print tables.
- Strengthened column-header and glass-type subheader gray fills and enabled exact print-color adjustment so those bands appear on paper.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.214. Schema version 5 is unchanged.

## v0.213 - Denser Delivery Sheets and Stable Remake Frames

- Removed the Notes section from every delivery-list page and used the recovered vertical space for additional printable order rows.
- Increased safe pagination to 23/25 logical rows for Portrait and 16/18 for Landscape while continuing to count glass group headings, preventing bottom-row clipping.
- Left aligned Route in both the on-screen Letter preview and generated print document.
- Raised the Check heading and checkbox cells to the same type scale as the other table columns in Portrait and Landscape.
- Rebuilt the remake dashed frame with a contained printable inset and hidden overflow so no portion can appear on the previous sheet.
- Added a narrow remake-only content gutter in preview and print output so the dashed frame remains visible without overlapping list content.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.213. Schema version 5 is unchanged.

## v0.212 - Adaptive Print Metadata, Stable Route State, and Table Fit

- Removed Route from the printed filter summary and changed the line to show only unique, active restrictions; completely unfiltered output now reads `Filters: All items`.
- Shortened delivery-list totals to `Rows | Orders | QTY` so the print header uses less vertical and horizontal space.
- Made Airport route state authoritative across date changes, panel reopen, preset application, and Portrait/Landscape switching instead of rereading stale visual checkbox markup.
- Automatically fits Landscape Letter sheets to the available preview width when orientation changes while retaining manual zoom controls.
- Renamed the compact table headings to `Order`, `Item`, and `QTY`; widened Dimensions, narrowed Customer, widened Route and Check, and restored Route text to the same readable size as the other columns.
- Moved the remake dashed outline into the physical page-margin area so it surrounds the sheet without overlapping delivery-list content or being clipped by Default print margins.
- Made the Delivery Date selector width respond to the active label: compact for one date and wider for a custom range.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.212. Schema version 5 is unchanged.

## v0.211 - Letter Preview Parity and Printed Filter Summary

- Rebuilt the Delivery List Preview around physical US Letter dimensions so Portrait uses 8.5 x 11 inches and Landscape uses 11 x 8.5 inches.
- Matched preview and generated print output to the same 0.4-inch Chrome/Edge Default-margin model instead of using unrelated screen-only sheet padding.
- Synchronized preview and print title sizes, metadata text, table measurements, column widths, notes boxes, Rush borders, remake borders, and landscape geometry.
- Added a compact gray `Filters` sentence beneath the totals and above `Printed at` on normal, Rush, remake, and continuation pages.
- The printed summary records Route, Glass, Status, Attention, exact order/item selection count, and Updated-only mode while compressing large multi-select groups into counts.
- Kept the remake outline at a consistent printer-safe physical inset from all four Letter-page edges in both preview and print output.
- Preserved the v0.210 deterministic Airport initialization, exact preview/output rows, system default preset, and schema version 5.
- Advanced the application contract, visible version, asset cache keys, documentation, and focused structure tests to v0.211.

## v0.210 - Deterministic Initial Airport Route

- Fixed the intermittent state where Airport looked selected when Print / Export opened but was not yet committed for preview, print, or export.
- Commits the System Default Airport route synchronously before the GUI is exposed or any asynchronous delivery-list detail request begins.
- Added maintained route normalization so an empty, invalid, or conflicting route set resolves to the complete Airport outbound selection.
- Prevents initial filter rendering from reading stale route markup left behind by a previous Print / Export session.
- Replaced the redundant startup reset plus System Default reapplication with one initialization transaction, removing overlapping filter renders.
- Tracks the active Print / Export open session so a late response from an older or closed session cannot replace current filter state.
- Makes Print and Export await any in-progress workspace initialization before validating rows and creating output.
- Preserved the v0.209 preset redesign, system default, landscape printing, print totals, inset remake border, and schema version 5.
- Advanced the application contract, visible version, asset cache keys, documentation, and focused structure tests to v0.210.

## v0.209 - System Default Preset, Landscape Sheets, and Print Totals

- Moved the Delivery Date selector into the left Filters heading cluster so the active date sits immediately beside the section name instead of floating with the action buttons.
- Increased Delivery Date, Create Preset, Saved Presets, and Clear Filters typography to a centered 12.5-pixel control style while preserving compact sizing.
- Completely redesigned Create Preset as a guided two-column workspace with a dedicated name step, system-default explanation, usage guidance, balanced filter cards, and a responsive output-settings area.
- Added an immutable `System Default` preset available to every user without duplicating it into per-user browser storage.
- Applies System Default automatically on initial Print / Export open and after Clear Filters: Airport/all outbound items, All Glass, All Status, All Attention, PDF, one copy, and Portrait.
- Kept user-created presets user-scoped, displayed them after System Default, and blocked users from replacing the reserved system preset name.
- Added orientation-aware pagination so landscape sheets use their own page-height limits instead of reusing portrait pagination.
- Designed a true landscape delivery-list sheet with a wider Customer and Dimensions layout, compact row spacing, landscape header geometry, and a reduced notes area.
- Added Total printable rows, Total orders, and Total QTY metadata above the Printed at timestamp on normal, Rush, remake, and continuation sheets.
- Replaced the remake sheet's outer dashed border with a printer-safe inset outline in both preview and print output so all four corners remain visible.
- Kept the v0.208 exact glass-type filtering unchanged after confirming the reported zero-row case was caused by an intentionally selected Remakes attention filter.
- Advanced the application contract, visible version, asset cache keys, documentation, and focused structure tests to v0.209 while retaining schema version 5.

## v0.208 - Exact Glass Preview State and Centered Header Controls

- Fixed exact glass-type choices showing nonzero chip counts while the Delivery List Preview incorrectly rendered zero printable rows.
- Made committed route and exact-glass application state authoritative for preview filtering instead of rereading transient controls during asynchronous filter rerenders.
- Added one maintained glass-type comparison key that normalizes Unicode, common inch/quote marks, repeated whitespace, surrounding whitespace, and letter case while preserving original product labels for display, presets, and output.
- Captures Airport and exact glass selections before loading placeholders replace the filter controls, preventing a valid route from being lost during a glass selection refresh.
- Reconciles retained and saved glass selections against the currently loaded product catalog by normalized identity so small formatting differences do not invalidate a selection.
- Centered the Delivery Date and Saved Presets select labels across their full controls and kept Create Preset and Clear Filters content centered at the same vertical level.
- Preserved the v0.207 custom-range calendar, Lookup Manager product library, responsive preset layout, exact order/item selection, PDF/XLSX/CSV behavior, and schema version 5.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.208.

## v0.207 - Custom Range Completion, Stable Initial Filters, and Lookup Glass Library

- Removed repeated leading wording from individual delivery-date and applied date-range selector labels.
- Changed Custom Range to begin a fresh two-click draft when opened from a single date, preserving an existing range only when editing one.
- Fixed calendar day clicks closing the picker after the grid rerender by using the original composed event path for outside-click detection.
- Renamed the guarded calendar action to Apply Dates and continued to require both Date From and Date To.
- Increased Delivery Date, Create Preset, Saved Presets, and Clear Filters typography to match the 10.5-pixel filter-chip content.
- Added stable route and glass selection snapshots so the initial Airport / All Glass state survives asynchronous choice rendering and exact glass filters work on first selection.
- Removed active-preset coupling from live glass selection state; applying a preset remains explicit while later manual filter changes remain authoritative.
- Reorganized Create Preset into complete desktop, medium, and mobile grid areas with Attention, Glass Types, and Output Settings using all available space.
- Added a lightweight Lookup Manager product-library prefetch and immediate modal enrichment without restoring historical delivery-list requests.
- Uses every Lookup Manager product value as an exact glass option while displaying its maintained friendly product-name label and searching both value and label.
- Centralized adoption of Lookup Manager payloads so Print / Export and Manual Delivery List Edit share the same normalized library state.
- Preserved schema version 5 and advanced the application contract, visible version, cache keys, documentation, and structure tests to v0.207.

## v0.206 - Compact Print Controls, Instant Preset Builder, and Calendar Repair

- Reduced Delivery Date, Create Preset, Saved Presets, and Clear Filters from oversized equal-width controls to compact, purpose-sized controls on one aligned desktop row.
- Added controlled wrapping and two-column mobile behavior without allowing the four controls to expand unnecessarily.
- Rebuilt the Create Preset GUI with a polished header, guided preset-name card, clearer filter sections, improved output settings, and responsive footer actions.
- Added searchable glass-type choices inside the preset builder.
- Removed historical glass-type quantity totals from preset creation; presets now display and store glass-type labels only.
- Eliminated the preset modal's full-catalog network wait by collecting glass types from the active workspace, already-loaded list detail, and existing user presets.
- Fixed Custom Date Range immediately closing when selected from the detached enhanced dropdown menu.
- Preserved user-specific preset persistence, exact print sessions, PDF/XLSX/CSV output, live preview behavior, and schema version 5.
- Advanced the application contract, visible version, and Styles/JavaScript cache keys to v0.206.

## v0.205 - Consistent Header Controls, Range Calendar, and User Presets

- Standardized Delivery Date, Create Preset, Saved Presets, and Clear Filters to the same height, border, radius, typography, and hover treatment.
- Rebuilt Custom Date Range as a dedicated two-month Date From / Date To picker; removed the unused single-date calendar mode.
- Added working range restart, previous/next month navigation, today highlighting, outbound-date markers, and guarded Apply Range behavior.
- Kept one-click individual delivery dates in the header dropdown with Custom Date Range as its first option.
- Expanded preset creation to preload every glass type currently known across the active delivery-list catalog.
- Namespaced saved presets and active-preset state by signed-in user, with migration from the earlier browser-wide preset store.
- Reapplies the active user preset whenever Print / Export opens and keeps it selected until the user chooses another preset or clears filters.
- Preserved the v0.204 live preview repair, visual polish, exact item/order selection, direct PDF printing, copies, orientation, XLSX, and CSV behavior.
- Preserved schema version 5 and advanced the application contract and cache keys to v0.205.

## v0.204 - Print / Export Visual Polish and Preview Geometry Repair

- Fixed the delivery-list preview container expanding to an extreme off-screen width because a shrink-to-fit page stack contained percentage-width sheets.
- Replaced the competing parent-and-sheet preview transforms with one layout-aware zoom owner.
- Keeps portrait and landscape sheets centered, visible, and vertically scrollable inside the preview pane.
- Preserved the same sheet markup, grouping, pagination, and data used by the working Print List popup.
- Rebalanced the desktop Print / Export workspace to provide useful width to both filters and the document preview.
- Standardized filter cards, headings, helper text, chip sizes, selected colors, and long-label wrapping.
- Refined Delivery Date, preset, and Clear Filters controls to avoid overlap and cut-off labels.
- Polished the preview toolbar, document canvas, sheet framing, table readability, and output footer.
- Added safe wrapping for Copies, Layout, File Type, and the primary output action on narrower displays.
- Updated the visible footer version, application contract, cache keys, documentation, and structure tests to v0.204.
- Preserved SQLite schema version 5; no database migration is required.

## v0.203 - Print Layout Completion and Direct Preview Printing

- Moved Delivery Date into the Filters header with one-date choices and Custom date range as the first dropdown option.
- Kept the calendar GUI for custom ranges, including highlighted today, month navigation, and date-range selection.
- Rebuilt filter order as Route / Glass Type, Status / Attention, then exact order and item search at the bottom.
- Replaced Copies with a bounded increment control and Layout with exclusive Portrait and Landscape buttons.
- Added the same output controls to Create Preset and kept preset application synchronized with the main output controls.
- Removed asynchronous PDF preparation from the print click path so the print popup opens reliably under browser popup rules.
- Generates the PDF/print window directly from the exact loaded rows shown in the live preview.
- Added shared sheet pagination and markup for preview and printing: 21-row first pages, 23-row continuation pages, glass group headers, normal/Rush/remake sheets, notes, and checked-by fields.
- Applies `@page` portrait or landscape sizing to the real browser print dialog.
- Removed the Not found preview-reconciliation message while retaining exact authenticated sessions for XLSX and CSV exports.
- Improved exact search readiness by ensuring selected delivery-list detail is loaded before suggestions are generated.
- Preserved schema version 5 and advanced the application contract and cache keys to v0.203.

## v0.202 - Exact Print Sessions, Item Selection, and Output Presets

- Replaced the Print / Export preview reconciliation request with an authenticated POST contract that carries exact line-item IDs and list/order/item fallback keys.
- Added short-lived, same-user print sessions so Print, PDF, XLSX, and CSV consume the exact package validated by the live preview.
- Fixed valid browser previews failing to print because the older query-string reconciliation returned zero rows.
- Added smart item-level search results with separate Add Item and Add Order actions for order, item, customer, and Job Nr. matches.
- Added exact selected-item cards with individual removal while retaining whole-order selection and Clear All.
- Removed Date Range and exact order/customer choices from the Create Preset builder.
- Added file type, copy count, and portrait/landscape output settings to presets.
- Moved the compact preset controls into the Filters header immediately before Clear Filters.
- Added maintained copies and orientation selectors beside File Type.
- Replaced the page-number selector with a vertically scrollable stack containing every preview page.
- Added portrait and landscape page geometry to both the browser preview and the generated print document.
- Preserved schema version 5; no database migration is required.
- Advanced the application contract and global Styles/JavaScript cache keys to v0.202.

## v0.201 - Print Calendar, All Glass Semantics, and Preview Stability

- Reworked All Glass into a true unrestricted choice that deselects every exact glass type.
- Exact glass-type selections now clear All Glass, while clearing all exact choices restores All Glass.
- Fixed the live-preview gate that treated All Glass as zero selected glass types.
- Preserved a valid browser-built preview whenever backend reconciliation returns an empty or zero-piece package.
- Resized All Status and All Attention to match their neighboring filter buttons and kept them in the first grid position.
- Replaced the visible quick-date and start/end fields with a top-of-workspace calendar selector.
- Added Single Date and Custom Range calendar modes, month navigation, highlighted today, range highlighting, and outbound-list date markers.
- Kept the selected dates connected to presets, preview, print, PDF, XLSX, and CSV output.
- Advanced the application contract and Styles/JavaScript cache keys to v0.201 without changing schema version 5.

## v0.200 - Live Preview Repair, Preset Builder, and Unified Output Selector

- Fixed the Print / Export paper preview flashing valid rows and then reverting to zero printable rows.
- Preserved a valid local preview when a stale or mismatched backend reconciliation response returns no rows.
- Stopped sending exact Glass Type filters when every available glass type is selected.
- Added All Status and All Attention controls and selected them by default.
- Defined All Attention as unrestricted so ordinary rows without attention flags remain included.
- Removed the footer Reset Filters action and enlarged the top-right Clear Filters button.
- Replaced Save Preset with Create Preset.
- Added an editable preset builder for dates, routes, status, attention, glass types, and exact selected orders.
- Automatically applies a newly created preset after saving it.
- Replaced the split Export PDF control with the maintained custom output selector.
- Added PDF, Excel Workbook, and CSV options.
- Kept PDF paired with Print List and changed the primary action to Export List for XLSX and CSV.
- Added filtered package CSV export using the same backend package contract as print and XLSX.
- Advanced the application contract and Styles/JavaScript cache keys to v0.200 without changing schema version 5.

## v0.199 - Multi-Order Selection, Preset GUI, and Live Paper Preview

- Made selected Print / Export chips use white labels and counts for readable contrast.
- Replaced single free-text output filtering with a smart multi-order picker that searches order numbers, customer names, and Job Nr. values.
- Added a Selected Orders workspace with exact order metadata, individual removal, Clear All, and unavailable-order guidance after date or route changes.
- Added exact `ordersExact` filtering to live preview, print, PDF, and XLSX requests.
- Added a dedicated Save Current Filters GUI with preset summary, validation, and overwrite guidance.
- Moved Route choices into a vertical right-side rail inside the filter pane.
- Narrowed the preview panel and changed the paper preview to mirror the maintained printed delivery-list structure: glass group rows, Job Nr., Order Nr., Item Nr., Qty., Dimensions, Customer, Route, Check, and Notes.
- Added an immediate local live preview on every filter change, followed by exact backend reconciliation through `/api/print/package-preview`.
- Preserved the live paper if backend reconciliation fails, eliminating the blank preview state.
- Increased preview pagination to 18 printable rows and included Job Nr. in backend preview rows.
- Advanced the application contract and Styles/JavaScript cache keys to v0.199.
- No database migration is required; schema version 5 remains active.

## v0.198 - Route-First Print Filters, Quick Date, and Smart Search

- Removed the Stage section from the Print / Export control center and made Route the primary source selector.
- Added fixed Airport, Indian Trail, Greenville, CPU, and DTC route choices.
- Defined Airport as the complete selected Airport Outbound workload and destination routes as focused subsets of those outbound rows.
- Fixed the blank Route, Status, Attention, and Glass Type sections by replacing the undefined `printItemsForCountList` call with the maintained loaded item collection.
- Added explicit loading and error states so filter failures cannot appear as unexplained empty sections.
- Added a Quick Date selector that sets both ends of the date range to one available outbound delivery date.
- Made glass-type options recalculate from the current date and route scope.
- Added live smart order suggestions for partial customer names, partial or complete order numbers, and Job Nr. values.
- Added Job Nr., product, and source-ID matching to the shared backend search filter.
- Removed the second decorative header ring while retaining one subtle background accent.
- Preserved schema version 5; no database migration is required.
- Advanced the application contract and global Styles/JavaScript cache keys to v0.198.

## v0.197 - Print / Export Document Preview Control Center

- Rebuilt the Print / Export Delivery Lists modal to match the approved full-screen filters-and-document-preview layout.
- Added left-side Search, Date Range, Stage, Route, Status, Attention, and exact Glass Type controls.
- Added a live paged paper preview with page selection, zoom controls, and full-screen viewing.
- Added preview rows for order, item, customer, delivery date, pieces, glass type, dimensions, scan status, attention state, and route.
- Added shared backend filters for exact routes, scan statuses, attention states, and customer/order search.
- Added browser-local named filter presets plus Reset Filters and Clear All actions.
- Added the reference-style Export PDF split control while retaining XLSX as a selectable export format, with both outputs aligned to the exact live preview contract.
- Preserved schema version 5; no database migration is required.
- Advanced the application contract and changed global Styles/JavaScript cache keys to v0.197.

## v0.196 - Scanner Panel Date, Station, and Stage Header

- Moved the active Stage and Delivery Date selectors from the Scan page heading into the scanner panel header.
- Replaced the combined stage/date scanner title with a three-column context row: Stage selector, assigned station, and Delivery Date selector.
- Reduced Stage selector option text to the stage name only because the assigned station is now displayed separately in the center.
- Styled both selectors with transparent header surfaces that retain the existing accessible custom-dropdown behavior and delivery-date update marker.
- Preserved cross-date switching, list activation, stage permissions, hidden station selection, scan request metadata, and audit history.
- Added a responsive two-row layout for narrow scanner panels.
- Advanced the application contract and changed Scan/JavaScript cache keys to v0.196.
- No database migration is required; schema version 5 remains current.

### Changed files

- `README.md`
- `README_CHANGELOG.md`
- `index.html`
- `database/contract.py`
- `static/js/app.js`
- `static/css/scan.css`
- `tests/test_static_structure.py`

## v0.195 - Print / Export Filter Workspace and Exact Preview

- Removed the visible Station status from the Scan page heading and right-aligned the Delivery Date and Stage selectors.
- Preserved the hidden station selector and station profile elements so scan requests, permissions, station assignment, and audit history continue using the signed-in station.
- Rebuilt the Print / Export modal around dedicated stage, exact-glass, customer, order, and content filter cards.
- Added stage progress cards, glass search and mirror presets, whole-category glass selection, customer and order search, and Select all/Clear actions.
- Added exact JSON-backed glass, customer, and order selection filters so checkbox choices do not broaden into substring matches or break on commas in customer names.
- Removed the duplicate Selection Summary and retained one detailed Selection Preview.
- Added `/api/print/package-preview`, which summarizes the exact `get_print_package` output used by both print preview and XLSX export.
- Made Estimated Glass Pieces, printable rows, order/customer totals, normal/remake/Rush mix, and stage/glass/customer/order breakdowns reflect the final generated package.
- Added a red zero-result preview with `Selected filters yield 0 results.` and disabled output while no printable rows match.
- Keeps output disabled while the exact preview is calculating or unavailable so an earlier preview cannot authorize a newer filter combination.
- Advanced the application contract and changed Styles/Scan/JavaScript cache keys to v0.195.
- No database migration is required; schema version 5 remains current.

### Changed files

- `README.md`
- `README_CHANGELOG.md`
- `index.html`
- `server.py`
- `backend/store.py`
- `database/contract.py`
- `static/js/app.js`
- `static/css/styles.css`
- `static/css/scan.css`
- `tests/test_static_structure.py`

## v0.194 - Exact Manual Scans and Result Feedback Repair

- Required manual scans to match the complete six-digit order and item instead of falling through to three-digit suffix recovery.
- Applied exact manual matching to current-list scans, cross-date candidates, date hints, local mode, and Indian Trail receiving.
- Preserved tolerant suffix recovery for physical barcode scans.
- Restored green success and red failure backgrounds on the Last Scan card after page-specific CSS had overridden the shared status colors.
- Mapped successful delivery-date switches to the packaged positive `scan_success.wav` cue while keeping normal scans on `notification.wav`.
- Kept cross-date selection prompts on the warning cue until a scan succeeds.
- Removed the Action History tab and history loading from the All Scans GUI.
- Advanced the application contract and changed Scan/JavaScript cache keys to v0.194.
- No database migration is required; schema version 5 remains current.

## v0.193 - Guarded Cross-Delivery-Date Scanning

- Added cross-delivery-date matching to the maintained main Scan and Indian Trail receiving workflows without creating a second scanner implementation.
- Checks the selected list first, then searches only active, accessible lists in the same operational stage and configured date window.
- Automatically switches and scans one unique safe match while retaining the matched delivery date as the active selection.
- Added an operator selection window for multiple matches, Ask mode, completed lines, manual bay choices, and rack/outbound/destination safeguards.
- Shows candidate delivery date, stage, order/item, quantity progress, route, customer, current location, and safety guidance before a manual choice.
- Preserves existing duplicate, stage-access, outbound, transportation, Indian Trail, rack, bay, supervisor-override, undo/redo, and audit behavior.
- Clears an unavailable, closed, or destination-incompatible selected rack before applying a confirmed cross-date scan and explains why it was not preserved.
- Added Admin settings for Disabled, Ask before switching, and Automatically switch unique matches, plus configurable past/future search limits defaulting to 7 and 30 days.
- Added immutable audit records for match discovery, settings changes, and cross-date switches.
- Added a dedicated visual date-change notice and semantic `delivery_date_changed` cue using the existing `scan_warning.wav` asset.
- Advanced the application contract and changed Scan/Admin/JavaScript cache keys to v0.193.

### Changed files

- `README.md`
- `README_CHANGELOG.md`
- `index.html`
- `server.py`
- `backend/store.py`
- `database/contract.py`
- `static/js/app.js`
- `static/css/scan.css`
- `static/css/admin.css`
- `tests/test_static_structure.py`

### Database

- No database migration is required.
- Existing schema version 5 remains current.
- Shared settings use the existing `system_metadata` table.

## v0.192 - Unified Rack Transfers and Paged Action History

- Replaced the native rack-transfer destination selector with a high-layer custom chooser so the destination list cannot open behind the Individual Rack GUI.
- Reused the same rack-transfer GUI for whole-rack, delivery-date, and individual-item moves on both the Racks page and Individual Rack modal.
- Added a small visual gap between each delivery-date heading and its first order line in the Individual Rack workspace.
- Changed every Action History tab to server-side pagination with a hard maximum of 50 events per page.
- Added Previous and Next page controls while preserving search, user, action, and date filters.
- Added paged All Racks History with server-side rack-group and rack-range filtering.
- Applied the richer All Racks History event-card design to every GUI Action History tab.
- Restricted Edit Racks Action History to rack creation, rack editing, rack-set creation, and rack deletion events. Operational rack scanning and transportation actions remain in Racks History.
- Added SQLite migration 005 with immutable `audit_events_archive` storage and timestamp indexes. Events older than 30 days are copied into the logical archive and removed from active GUI history without weakening the append-only primary audit log.
- Updated the database contract to schema version 5 and application contract version 192.
- Advanced the application display and changed browser asset cache keys to v0.192.

### Changed files

- `index.html`
- `README_CHANGELOG.md`
- `server.py`
- `backend/store.py`
- `database/contract.py`
- `database/migrations.py`
- `static/js/app.js`
- `static/css/shell.css`

### Database

- Migration required: **005 - v192_action_history_archive**.
- The normal verified pre-upgrade backup process runs before applying the migration.

## v0.191 - Rack-Scoped Action History and Combined Racks History

### Individual Rack Action History

- Limited the Individual Rack Action History tab to the currently opened rack instead of showing actions from every rack.
- Rack-scoped matching now includes direct rack actions, item clears, scans, packing-list prints, rack transfers where the rack was the source or destination, and compatible outbound-override transportation events.
- Added the source rack, destination rack, order, item, and moved quantity to new individual-item transfer audit records so future investigations remain accurate from both sides of a move.
- Reloads the selected rack's history whenever its Action History tab is opened.
- Preserved the shared user, action, date, and text investigation filters from v0.190 and labeled the tab clearly as history for the selected rack only.

### Racks History control center

- Renamed the Rack Overview action from `Packing List History` to `Racks History`.
- Rebuilt that window with two maintained section tabs: `Packing List History` and `All Racks History`.
- Preserved immutable packing-list snapshots and the existing Open Snapshot workflow in the Packing List History tab.
- Added an All Racks History timeline covering rack scans, status changes, transfers, clears, recovery actions, rack setup changes, and packing-list print records.
- Added All Racks History filters for text search, user, action, rack group, inclusive rack-from / rack-through range, and inclusive date range.
- Rack-group options combine the live rack catalog with group names retained in historical audit records; rack ranges use natural rack-code order and include transfer events when either the source or destination rack matches.
- Added result counts, rack and rack-group badges, a one-click Clear Filters action, and Spanish translations for the new history controls.

### Compatibility

- SQLite remains the active/default backend.
- No database migration is required.
- No images, installers, launchers, database files, or unrelated project files are included.

## v0.190 - Action History Investigation Filters and Move Icon Hover

### Action History filters

- Added a shared investigation toolbar to every GUI that exposes an Action History tab, including Admin editors, Internal Rejects, Individual Racks, Old Bays, Rush Orders, Manage Bay Items, and Edit Bays.
- Added free-text search across action names, event details, users, entity identifiers, reasons, and displayed timestamps.
- Added exact User and Action dropdown filters populated from the loaded event history.
- Added inclusive From Date and Through Date filters using the operator's local displayed date.
- Added a live `shown / loaded` event count and one-click Clear Filters control.
- Increased each Action History load from the small recent-event sample to as many as 500 relevant audit events so the filters are useful for investigations.
- Preserved the latest-change summary and the full unfiltered count on each Action History tab.
- Added Spanish translations for the new filter controls and empty-result messaging.

### Individual Rack move control

- Replaced the whole-rack move icon's solid-blue hover state with a light-blue hover surface and dark directional glyph so the icon remains clearly visible.
- Applied the same readable hover treatment to delivery-date rack move controls.

### Compatibility

- SQLite remains the active/default backend.
- No database migration is required.
- No images, installers, launchers, database files, or unrelated project files are included.

## v0.189 - Individual Rack Grid Ownership and Tab-Bar Actions

### Individual Rack control center

- Corrected a cross-stylesheet grid conflict that placed the Workspace tabs and rack contents into separate implicit columns.
- Forced the Rack Overview header, tab/action bar, Workspace, and Action History into one full-width modal column.
- Moved Complete / Uncomplete Rack, Print Packing Slip, return controls, and the whole-rack move icon onto the far-right side of the Workspace / Action History tab bar.
- Restored the Rack Overview header to a clean full-width presentation with the status and close controls only.
- Added final shell-level ownership so later Racks and Bay stylesheet rules can no longer reset the rack workspace to row 2 or suppress its vertical overflow.
- Made the complete Workspace canvas the deliberate vertical scroll owner while allowing expanded delivery-date groups and order cards to grow naturally.
- Preserved a separate full-height scrollbar for Action History when its event list exceeds the available height.

### Compatibility

- SQLite remains the active/default backend.
- No database migration or backend replacement is required.
- No images, installers, launchers, database files, or unrelated project files are included.

## v0.188 - Individual Rack Tabs, Header Actions, and Scroll Restoration

### Individual Rack control center

- Moved Action History into a separate Workspace / Action History tab system matching the maintained administration GUIs.
- Kept the rack contents and Action History as peer workspaces so history no longer consumes space above the assigned-piece list.
- Restored one reliable full-height vertical scrollbar for the Individual Rack workspace, allowing every expanded delivery-date group and order to remain reachable.
- Added the same full-height scrolling behavior to the Action History tab when the recorded event list exceeds the available screen height.
- Moved Complete / Uncomplete, Print Packing Slip, return controls, and the whole-rack move icon into the right side of the shared Rack Overview header.
- Increased and rebalanced the header height so the status and close controls remain on the top row while rack actions sit directly underneath.
- Kept delivery-date move icons and individual-piece controls inside the rack contents workspace.

### Compatibility

- SQLite remains the active/default backend.
- No database migration or backend replacement is required.
- No images, installers, launchers, database files, or unrelated project files are included.

## v0.187 - Individual Rack Scroll and Header Consolidation

### Individual Rack details

- Restored a visible vertical scrollbar for the complete Individual Rack workspace.
- Delivery-date groups and every assigned order now expand to their full natural height inside that scrolling workspace.
- Removed the nested order-list viewport that could prevent expanded rack contents from becoming visible.
- Merged the duplicate inner rack/truck identity panel into the shared Rack Overview header so rack type, rack name, counts, status, and destination remain visible without consuming a second section.
- Removed the visible `Orders on this truck` / `Orders on this rack` heading without removing any grouped date or order data.
- Kept whole-rack and delivery-date move icons, packing actions, status controls, and Action History.

### Compatibility

- SQLite remains the active/default backend.
- No database migration or backend replacement is required.
- No images, installers, launchers, database files, or unrelated project files are included.

## v0.186 - Rack Date Group Expansion and Header Cleanup

### Individual Rack details

- Repaired the delivery-date accordion layout after the v0.185 transfer-panel removal left the rack workspace with an obsolete extra grid row.
- Expanded delivery-date groups now render every order and line item instead of clipping the group after the first visible order.
- Kept the Orders list as the only scrolling region so long racks remain usable without hiding date-group contents.
- Preserved the compact whole-rack and delivery-date move icons introduced in v0.185.

### Rack Overview

- Removed the Rack Pieces, Truck Pieces, and Active Racks statistic bubbles from the upper-right page heading.
- Kept Packing List History and Edit Racks as the only Rack Overview heading actions.

### Compatibility

- SQLite remains the active/default backend.
- No database migration or backend replacement is required.
- No images, installers, launchers, database files, or unrelated project files are included.

## v0.185 - Update Preview Placement, Permission Selection, User Layout, and Rack Move Icons

### Delivery List Management and Manual Edit

- Removed the New / Updated preview action from the Edit Delivery Lists window.
- Added the preview action to each changed delivery-date row in the main Delivery List Management card, directly to the left of Print / Export.
- The preview now combines every changed stage for that delivery date into one read-only review window.
- Manual Edit now displays `Remake` as the effective Process value when imported `RM` or `REMAKE` markers identify the piece, even when the stored process text is blank, Normal, or Standard.

### Roles and users

- Replaced the broken Create Role permission dropdown categories with always-visible grouped permission cards and working checkboxes.
- Kept Select All, Clear All, category counts, role validation, and existing-role permission editing intact.
- Expanded Add New User across the full available modal width.
- Removed the nested Existing Users scroll window so the complete User Access Management GUI uses one normal vertical scrollbar.

### Racks and packing history

- Removed the large whole-rack and delivery-date transfer sections from Individual Rack.
- Added one move icon beside the rack identity for moving all contents and one move icon beside each delivery-date group.
- Move icons open a compact destination selector and retain the guarded transactional transfer logic from v0.184.
- Removed Action History from Packing List Print History while leaving Action History available for other operational GUIs.

### Compatibility

- SQLite remains the active/default backend.
- No database migration or backend replacement is required.
- No images, installers, launchers, database files, or unrelated project files are included.

## v0.184 - Permissions, Rack Transfers, Update Preview, and GUI Repair Pass

### Print / Export and operational GUIs

- Corrected the Exact Glass Types accordion so category headers, selection controls, counts, and exact glass choices stay aligned without the large empty or malformed card layout.
- Refined the Internal Reject Control Center header, tabs, piece summary, quantity entry, reject fields, and fixed submission footer so its title and subtitle remain fully visible.
- Applied the maintained control-center polish to Individual Rack, Packing List Print History, and the Indian Trail In-Transit manifest.
- Prevented white hover flashes on Sign In and Packing List History actions.
- Centered the profile initials inside both sidebar profile circles.
- Constrained Rush missing-item cards to consistent operational heights and centered the Rush launcher icon.
- Removed the clipped Scan Flags marker animation that appeared as a tiny black dot at the right edge of the Flags column.

### Delivery-list update review

- Added a New / Updated preview action to Delivery List Management when the latest import batch contains changed lines.
- The preview groups exact new and updated items and shows order, item, job, customer, size, quantity, glass type, route, and workflow state.
- Added maintained backend lookup support for the newest delivery-list notice batch without changing the database schema.

### Rack transfers

- Added guarded whole-rack transfer from the Individual Rack Control Center.
- Added delivery-date group transfer so every active piece for one grouped date can be moved together.
- Validates every destination rule before any assignment moves, limits targets to open racks, safely merges an existing target line when necessary, and writes piece/line totals to audit history.

### Roles, users, lookups, and permissions

- Rebuilt the permission catalog around current delivery-list, Bay Map, rack, reject, reporting, automation, and administration responsibilities.
- Migrates legacy permission names to canonical maintained permissions while preserving compatibility for older frontend checks.
- Added functional role creation and repaired permission category expansion and selection.
- Repaired and polished Add New User validation, save status, error handling, and refresh behavior; the server now enforces a valid role and an eight-character minimum temporary password.
- Refined Lookup Manager icons and catalog cards and polished Reject Reasons and Break Locations content.

### Automation, filters, and language

- Corrected automation timestamps and delivery dates so two-digit or display-formatted values cannot be interpreted as year 2001.
- Expanded the Automation Control Center to use the available desktop viewport; only Import History results scroll inside that window.
- Repaired Manual Edit Remakes filtering to recognize both `REMAKE` and standalone imported `RM` markers while preserving the other maintained filters.
- Expanded Spanish translations for the current Print / Export, rack, packing-history, reject, role, user, lookup, automation, update-preview, and Rush workflows.

### Compatibility

- SQLite remains the active/default backend.
- Existing databases are preserved and no database migration is required.
- No images, installers, launchers, database files, or unrelated project files are included in the changed-files package.

## v0.183 - Compact Print, Rush Frame, and Reject Detail Refinement

- Refit Print / Export into a shorter desktop workspace that stays inside the available screen without main-column vertical scrolling.
- Reduced the header, command row, stage controls, glass-type categories, filters, summary rows, and final action area while preserving exact individual glass-type selection.
- Changed Exact Glass Types to a single-open-category accordion so the full document workspace remains visible and operators can still select precise glass types.
- Removed the inherited Rush panel padding that created the visible white outer frame around the colored header.
- Removed main Rush workspace scrolling on normal desktop displays and confined overflow to the missing-item results only when a loaded order contains more rows than fit.
- Shortened and rebalanced the Rush search, item-selection, and handling sections so the complete three-step workflow fits inside the modal.
- Removed Internal Reject Step 4 and kept the irreversible-action warning in the compact submission footer.
- Reused the maintained Administration-style section tabs for Add Reject and Action History.
- Moved Quantity Rejected beside Order Number and Item Number in the Identify Piece row and constrains it to the verified available quantity.
- Expanded Matched Piece Summary with piece dimensions, glass type, route, available quantity, scan progress, current/suggested bay, delivery date, customer, job, and active stages.
- Enriched the existing reject-match response with display-only piece details from the verified active delivery-list rows; no schema or migration change is required.

## v0.182 - Modal Geometry Repair and Internal Reject Control Center

- Rebuilt the Print / Export window into a contained two-column document workspace with exact-stage controls, exact glass-type categories, optional customer/order filters, a live selection summary, and a useful output preview instead of a large empty region.
- Corrected the Print / Export grid ownership that squeezed the configuration column and pushed the action area into an oversized blank panel.
- Corrected Rush, Manage Bay Items, and Edit Bays modal row ownership so the hero header, section tabs, and workspace each receive their own grid row.
- Removed the nested-frame appearance from Rush and kept all three Bay workflow windows inside one consistent rounded modal shell.
- Increased usable modal height, protected headers and tabs from clipping, and confined scrolling to the intended list/workspace regions.
- Refined Manage Bay Items into a wider job list plus a balanced selected-job workspace with contained actions and readable full job information.
- Refined Edit Bays into a wider non-horizontal-scrolling group editor with a stable Add New Bay Group command and contained individual-bay rows.
- Rebuilt Add Internal Reject as a four-step control center: Identify Piece, Matched Piece Summary, Reject Details, and Impact / Review.
- Kept delivery-date resolution automatic and retained the existing verified match, catalog, submission, reset, audit, and permission behavior.
- Added a live Print / Export selection summary without changing the existing print/export API contract.
- No database migration or backend replacement is required.

# File: README_CHANGELOG.md

## v0.181 - Bay Workflow Control Centers, Rush Priority, Reject Entry, Print Selection, and Statistics Polish

### Bay Map control centers

- Rebuilt the Old Bay Control Center with a larger working canvas, larger typography, clearer review cards, and a more readable filter and snooze workflow.
- Added Workspace and Action History tabs to Old Bays, Manage Items, and Edit Bays.
- Added Add Rush, Current Priority Work, and Action History tabs to the Rush window.
- Expanded Manage Items, added a status filter, increased the order-information area, and allowed the left results list to show complete order details without clipping.
- Expanded Edit Bays, removed normal horizontal scrolling, and changed new-group creation to an explicit Add New Bay Group action that opens the creation workspace only when requested.
- Polished the In-Transit Manifest with a stronger receiving header, clearer summary cards, refined rack and glass-type groups, and a larger contained table workspace.
- Removed Bay Availability, Assigned / Occupied, and Needs Attention summary cards from the Bay Map heading and extended the Bay Map title treatment across the reclaimed width.

### Rush-only priority management

- Renamed the Bay Map Rush / Remake launcher and workflow to Rush.
- Removed the Rush / Remake type selector; new work created from this window is always Rush work.
- Changed Current Priority Work to include only intentionally marked Rush items.
- Imported RM / Remake markers continue to work in remake filters and printing but no longer inflate the operator-managed priority-work count.
- Rush clearing now removes only Rush / SDI state and preserves an existing RM / Remake marker on the same item.

### Action history

- Added Bay-workflow action-history contexts for Old Bay snoozes and review actions, Rush changes, managed bay-item moves and clears, and bay/group configuration changes.
- Extended action-history access to the existing Bay Map operational permissions instead of requiring an Administration-only permission.

### Internal rejects

- Simplified Add Internal Reject to require Order Number and Item Number for lookup instead of manually entering a delivery date.
- Resolves the active delivery date and affected stages automatically.
- Shows a compact date choice only when the same order/item has more than one active delivery-date match.
- Polished the identify, verify, incident-detail, impact, and submit sections while preserving reject rollback and audit behavior.

### Print / Export and Home statistics

- Rebuilt Print / Export as a larger document workspace with clearer stage, exact-glass, optional-filter, and output controls.
- Glass categories now organize the list only; each exact glass type is selected independently, such as 1/4 Clear Annealed without automatically including 3/8 Clear Annealed.
- Retained an explicit All Glass Types control for full-list output.
- Applied a stronger visual hierarchy to the Home Statistics dashboard, including its header, range tools, KPI cards, remake summary, glass chart, stage breakdown, and scan-health cards.

### Compatibility

- Preserved normal remake flags and remake printing, Bay Scanner behavior, Old Bay timing, scan history, delivery-list data, reject history, permissions, and the production SQLite database.
- No database migration is required.

## v0.180 - Main and Rejects Integration with Manual Edit Glass Type Filters

- Added a Glass Type section to the Manual Delivery List Edit filter drawer.
- Populates glass choices from the product/glass types that actually exist in the selected delivery-list stage.
- Displays the current piece quantity for each glass type.
- Supports selecting multiple glass types with OR logic inside the group and AND logic with progress, route, location, attention, and text-search filters.
- Keeps the stage's glass choices available when other filters return zero matching rows.
- Refreshes glass choices whenever the selected delivery-list stage changes.
- Integrated the Rejects feature line back into main while preserving main's
  Bay Scanner, Old Bay attention, Current Priority Work, footer, and timed scan
  feedback changes.
- Resolved the two branches' independent release numbering into one sequential
  `0.###` history without replacing the production database.
- No database migration is required.

## v0.179 - Manual Edit Exact Row Capture Repair

- Changed Manual Edit Save to use the exact expanded card containing the clicked Save button instead of querying the entire document by line-item ID.
- Added an original-value snapshot to every editable card and compares it with the current visible controls before saving.
- Captures the current Route, Location, Process, Product, order, item, customer, quantity, dimensions, and job values synchronously before the request.
- Sends the browser-detected changed fields with the save request for verification.
- Prevents a server no-change response from rerendering the result list and erasing the operator's unsaved values.
- Keeps the row open and reports a clear error when a detected edit is not confirmed by the server.

## v0.178 - Manual Route Save and New Order Workspace Repair

- Fixed manual-edit choice fields using a stale hidden mirror instead of the value currently displayed in the dropdown.
- Route saves now send an explicit override and store Indian Trail as `INDIAN TRAIL`, preventing CPU inference from undoing the operator's choice.
- Normalized route comparisons across sibling stage copies and exposed the applied route in the save response.
- Rebuilt the Manual Edit layout so Create New Order has a dedicated non-shrinking row and loaded results scroll independently.
- Added bounded scrolling to the expanded New Order card on shorter screens.

## v0.177 - Manual Route Corrections and Functional Admin GUI Tabs

- Fixed manual CPU-to-Indian Trail route changes being normalized back to the legacy inferred `IT` fallback.
- Stores explicit Indian Trail manual routing, synchronizes workflow copies, moves the receiving record, and returns the verified updated row.
- Keeps a just-saved row visible and expanded when it no longer matches active filters.
- Added green scanned-row styling and clear Scanned / Not scanned status badges.
- Moved the Manual Edit filter drawer to a viewport-level overlay so it remains fully visible with empty or short result sets.
- Replaced the pink Administration palette with navy and blue surfaces.
- Restored meaningful Workspace and Action History tabs to every Admin editor, including Edit Racks.

## v0.176 - Verified Manual Editing, GUI Action History, and Timed Rack Overrides

- Corrected Manual Delivery List Edit so one logical item is reported as one update even when its workflow-stage copies are synchronized.
- Saves now reload and verify every affected delivery-list stage before showing success.
- Added Scan-style filters for progress, route, location, remakes, rushes, updates, internal rejects, and manual entries.
- Added a persistent Create New Order toolbar action that remains available after loading more rows.
- Added real expandable Action History to each maintained Admin and Rack/Operations GUI.
- Added a configurable 1-120 minute mixed-destination rack override window under Bay Scanner Rules, defaulting to 15 minutes.
- Once one rack-destination mismatch is approved, additional destination combinations can be scanned into that rack until the window expires.

## v0.175 - Simplified GUI Headers and Automation Action

### Shared editor headers

- Removed the decorative selected workspace tab, Live scanner data tab, and Changes are audited tab from regular Administration editors.
- Removed the matching decorative context rail from Individual Rack and Packing List History Operations windows.
- Converted both shared modal systems to a simpler two-row layout: polished hero header plus scrollable editor canvas.
- Left the Delivery Automation Control Center's functional Run Manually, Automatic Schedule, Status & Logs, and Import History tabs unchanged.

### Delivery List Management action

- Moved the automation launcher into the Delivery List Management heading actions, immediately left of Edit delivery lists.
- Renamed it to Edit automated DL import and changed it to the maintained blue text-button treatment.
- Preserved the existing permission check and Automation Control Center open behavior.

### Compatibility

- Preserved all editor forms, event handlers, API requests, permissions, automation settings, and database behavior.
- No database migration or backend update is required.

## v0.174 - Modal Hidden State and Close Repair

### Startup and close behavior

- Fixed the shared Admin Control Center window being visible immediately when the web app loaded.
- Restored the X button and backdrop close behavior by ensuring the modal-specific grid rules cannot override the native `hidden` attribute.
- Applied the same hidden-state protection to the Operations window used by Individual Rack and Packing List History.
- Cleared stale modal content after closing so a previously opened editor cannot remain painted or replace a supposedly closed permanent window.
- Removed the Operations Control Center presentation class on close and synchronized `aria-hidden` state for both panels and backdrops.

### Compatibility

- Preserved every editor workflow, permission check, API request, unsaved manual-edit confirmation, rack operation, and database behavior.
- No database migration or backend update is required.

## v0.173 - Scan Typography and Control Center Layering Repair

### Scan-row readability

- Unified the Scanned pill label, date, time, separators, and station on one centered baseline with one readable font size.
- Increased Flags, Route, Location, and Progress text from the overly compact v0.169 sizes while preserving the maintained column widths.
- Corrected the missing semicolon in the Location width declaration so the browser consistently honors the complete fixed-width table contract.

### GUI layering and contrast

- Made the Administration Control Center header, context rail, and editor canvas explicit protected grid rows.
- Applied the same layer ownership to Individual Rack and Packing List History Operations windows.
- Prevented generic modal header rules from squeezing the status pill and close button into a narrow column.
- Increased and protected the close controls, constrained long status labels, and forced readable high-contrast hero text.
- Kept editor content beneath the header and context rail instead of allowing it to visually cover either surface.

### Compatibility

- Preserved every existing editor layout, event handler, permission check, API request, rack action, and scan record.
- No database migration, backend update, or JavaScript replacement is required.

## v0.172 - Scan Timestamp, Rack Status, and Rack Control Centers

### Scan-page presentation

- Condensed last-scan dates to month/day and times to a compact lowercase format such as `4:30pm` while preserving the full timestamp in hover text.
- Reserved the in-row scan-pill space only in the Job Nr. cell so Order and Item remain vertically aligned with QTY, Dimensions, Customer, Flags, Route, Location, and Progress.
- Added the active delivery-list date to the Scan panel title beside the stage name.

### Rack status integrity

- Removed the generic selected class from individual rack cards.
- Kept selection state available through `aria-current` while preserving Open, Complete, On the Way, Received, and Empty visual formatting.

### Rack GUI Control Centers

- Added the Administration-style Control Center hero, live-status pill, context rail, guided canvas, and section-card treatment to Individual Rack and Packing List History windows.
- Added dynamic rack context and status labels to the Individual Rack header.
- Strengthened Edit Racks, Rack, and Rack Set Admin editor surfaces without changing their existing forms or event handlers.

### Compatibility

- Preserved existing API calls, permission checks, rack actions, packing-list snapshots, scan data, and database behavior.
- No database migration or backend update is required.

## v0.171 - Administration Control Center GUI System

### Shared Admin window format

- Rebuilt the shared Administration modal around the same structural design language as the Delivery Automation Control Center.
- Added a descriptive navy hero, task-specific eyebrow, explanatory copy, live-status pill, and a workspace context rail.
- Added maintained profiles for Delivery Lists, Delivery List Actions, Manual Edit, Users, Roles, Sessions, Stations, Customer Routes, Customer Emails, Lookups, Reject Settings, Bay Scanner Rules, Bay Auto Assigner, Racks, Rack Sets, and All Scans.

### Editor consistency

- Standardized the working canvas, section cards, headers, tables, search controls, forms, list rows, empty states, and command/footer areas.
- Expanded data-heavy Admin editors while preserving responsive full-screen behavior on narrow displays.
- Kept all existing editor-specific layouts and workflows instead of replacing them with one generic form.

### Compatibility

- Preserved all existing IDs, delegated event handlers, API calls, permission checks, unsaved-change protection, editor refreshes, and database behavior.
- No database migration or backend update is required.


## v0.170 - Admin Editors, Scan Panel, and Automation Compatibility

### Page alignment and Scan panel

- Moved the Home Delivery List Overview text away from the decorative header accent.
- Aligned the Admin header, KPI cards, and dashboard sections to the same full-width grid edge.
- Restored the main Scan panel's navy progress header after the v0.169 surface rule incorrectly treated it as a white content card.
- Re-established distinct bordered cards for transportation, bay override, barcode entry, manual scan, manual assignment, and scan history.

### Administration editor polish

- Added a consistent purple Admin modal header, larger working canvas, refined backdrop surface, and stronger form/table hierarchy.
- Applied the shared editor treatment to Delivery List Management, Manual Delivery List Edit, Roles & Permissions, User Access Management, Customer Routes, Customer Email Rules, Lookup Manager, Reject Reasons & Locations, Bay Scanner Rules, and Bay Auto Assigner.
- Preserved all existing HTML IDs, event handlers, API requests, permissions, and editor workflows.

### Automation compatibility

- Added thin root-level `scanner_config.py` and `delivery_store.py` compatibility bridges for installed automation created before the v151 backend organization.
- Both bridges re-export the maintained `backend.config` and `backend.store` implementations; no database or business rules are duplicated.
- This resolves legacy scanner-root checks that reported the organized project was missing the old root module filenames.
- No database migration is required.

## v0.169 - Core Page Visual Polish and Scan Table Refinement

### Scan table geometry

- Reduced the in-row Last Scan pill so it ends at the Item column.
- Condensed Flags, Route, and Location to smaller production-safe widths while keeping markers, route labels, and rack controls contained.
- Reallocated the recovered width to Job Nr., Dimensions, and Customer.
- Replaced the two-pixel table clearance workaround with an exact 100% column contract.
- Removed the exposed white strip after Progress and removed the final cell's right border so the table meets the panel edge cleanly.

### Cross-page visual polish

- Added a shared professional hero treatment to Home, Scan, Racks, and Admin using each page's own accent color.
- Refined page backgrounds, panel hierarchy, borders, radii, shadows, typography, section headings, controls, and hover/focus feedback.
- Polished Home delivery progress, finder controls, list cards, and statistics surfaces.
- Polished the Scan command area, filter/table surfaces, row groups, compact operational columns, and scanner cards.
- Polished Rack set navigation, rack cards, detail panels, statuses, and management controls.
- Polished Admin KPI cards, management panels, tables, forms, lists, and last-updated status.

### Compatibility

- No JavaScript, backend, API, database, permission, reject-management, scanning, rack, or bay behavior changed.
- Advanced only the five changed stylesheet cache keys to `20260729-v158`; the unchanged JavaScript bundle remains on v157.

## v0.168 - In-Row Scan Pill and Progress Column

### Scan-page line presentation

- Replaced the separate Last Scan ribbon with a small scan-information pill inside the normal line-item row.
- Anchored the pill to the Job Nr. cell and allowed it to paint across Order, Item, QTY, Dimensions, and Customer without creating or resizing table columns.
- Kept date, time, and station on one compact line with ellipsis protection for long station names.
- Preserved QTY as a plain centered whole number.

### Headers and width containment

- Renamed the Scan table headers from Item Nr. to Item and Process State to Progress.
- Rebalanced the fixed table contract to give Progress more room.
- Reserved two physical pixels and one percentage point inside the table so the final Progress edge is not clipped by the list panel.
- Kept Internal Reject and future supplemental ribbons contained within the maintained table width.
- No backend, API, permission, database, reject-management, scan-history, rack, or bay behavior changed.
- Advanced only the Scan stylesheet and application JavaScript cache keys to v157.

## v0.167 - Scan Time Ribbon and Plain Quantity

### Scan-page line presentation

- Replaced the QTY pill with a plain centered integer while preserving scanned-versus-total information in the cell tooltip.
- Removed the long `Scanned: date/time - station` line from the Job Nr. column.
- Added a compact blue Last Scan ribbon above each scanned line item.
- Displays the date, time, and station in one readable line rather than multiple narrow information cells.
- Keeps the scan ribbon inside the same Job Nr.-through-Customer six-column span used by Internal Rejects.

### Width safety and compatibility

- Added one reusable detail-ribbon containment contract for scan-time, Internal Reject, and future warning/audit ribbons.
- Supplemental ribbons cannot create new table columns, minimum widths, or horizontal overflow.
- Preserved the v0.166 fixed percentage-based table contract, location containment, process wrapping, and flag containment.
- No API, database, permission, reject-management, scanning, rack, or bay behavior changed.
- Advanced only the Scan stylesheet and application JavaScript cache keys to v156.

## v0.166 - Reject Ribbon Simplification and Scan Table Containment

### Internal-reject ribbon

- Removed Delivery Date from the Scan-page reject ribbon.
- Removed the trailing event-count and investigation-note capsules.
- Increased the remaining Reason, Machine / Location, Qty, Rejected By, and Incident typography.
- Kept the ribbon limited to Job Nr. through Customer and allowed it to wrap responsively at narrower widths.

### Scan table width safety

- Replaced automatic table sizing with a maintained 100% percentage-based column contract.
- Removed the hard 118-pixel minimum from the Location column.
- Constrained long scan timestamps, process labels, flags, location selectors, badges, and ribbon content to their assigned columns.
- Prevented current and future row-detail ribbons from enlarging the delivery-list panel and producing horizontal page scroll.

### Compatibility

- No backend, API, permission, database, or reject-history behavior changed.
- Advanced only the Scan stylesheet and application JavaScript cache keys to v155.

## v0.165 - Admin Reject Management and Scan Ribbon Polish

### Admin-only reject management

- Added Edit and Delete actions to each Reject Timeline incident for the built-in Admin role only.
- Enforced the Admin role independently on the server for `/api/rejects/update` and `/api/rejects/delete`; UI visibility is not treated as authorization.
- Edit Reject updates reason, machine/location, rejected quantity, incident date/time, and investigation notes while keeping the affected order/item identity and original creator immutable.
- Delete Reject removes the selected reject event and recalculates cumulative line-item reject flags from remaining events.
- Editing or deleting a reject intentionally does not replay, restore, or reverse the original scan, rack, bay, or process rollback.
- Added append-only audit records for both edits and deletions, including the prior reject data and recalculated line summary.

### Scan-page reject awareness

- Rebuilt the internal-reject ribbon as a compact polished strip above the affected line item.
- Limited the ribbon to the Job Nr. through Customer columns so Flags, Route, Location, and Process State retain their normal table alignment.
- Added reason, machine/location, rejected quantity, rejected user, incident time, delivery date, event count, and investigation-note status.
- Expanded the line-flags response with current reject event details and separated cumulative rejected-piece quantity from reject-event count.

### Compatibility

- No database migration is required.
- Existing reject creation, scan reduction, rack removal, bay clearing, notifications, catalog management, and Reject Timeline filtering remain unchanged.
- Advanced only the changed Rejects, Scan, and application JavaScript cache keys to v154.

## v0.164 - Old Bay Attention and Priority Work Management

### Old Bay attention

- Replaced the automatic Old Bay modal opening with a timed orange notice shown when a user enters Bay Map.
- The notice reports the number of unique old orders needing review and provides a Review action that opens the existing Old Bay Control Center.
- Limited the notice to once every six hours per signed-in username using the existing server-side system metadata, so the timing follows the user across browser sessions and workstations.
- Added an orange attention-count badge to the top-right of the Old Bays button.
- Preserved existing search, age filters, selection, printing, and individual/bulk snoozing inside the Old Bay GUI.

### Current priority work

- Reorganized Current Priority Work into collapsible priority-date ribbons with nested job/order ribbons.
- Added search and Rush/Remake type filters with a live visible-item count.
- Added Edit and Remove actions for individual marked items.
- Added Edit Order and Remove Order actions for each grouped job/order.
- Added a guarded Clear All action for all current Rush/Remake work.
- Editing reuses the maintained Rush/Remake form and loads the existing type, priority date, truck handling, bay, and available reason details.

### Compatibility

- Preserved Old Bay aging and snooze rules, Rush/Remake endpoints, permissions, bay assignments, delivery lists, scan history, and database schema.
- Extended the existing stale-bay response with an atomic per-user six-hour alert claim; no new table or column is required.
- Extended the existing SDI workspace payload with current priority handling details and removed the former 100-group display cap so Clear All covers every current priority group.
- No migration, installer, BAT file, image, or database replacement is required.
- Advanced the changed Bay Map CSS and application JavaScript cache keys to v0.164.

## v0.163 - Footer Bug Reporting and Version Display

### Global footer

- Removed the Home and Settings actions from the desktop footer.
- Added a right-aligned **Report Bugs** action that opens a pre-addressed email to the maintained project contact with a structured bug-report template.
- Added a compact application-version badge showing **0.163** beside the bug-report action.
- Standardized maintained release numbering to the `0.xxx` format; the previous release is therefore identified as **0.162**.
- Preserved the application identity, active-scanner indicator, corrected footer grid placement, dark background, and responsive behavior.

### Compatibility

- No page-navigation, scanning, Bay Map, backend, database, permission, or API behavior changed.
- No migration, installer, BAT file, JavaScript change, image, or database replacement is required.
- Advanced only the shared shell stylesheet cache key to v0.163.

## v0.162 - Footer Grid Placement Correction

### Global footer

- Fixed the polished desktop footer being auto-placed into the collapsed sidebar grid column, which squeezed its content vertically and allowed the sidebar to cover it.
- Added an explicit third application-shell row and placed the footer in the main content column beneath the page.
- Preserved the dark operations background, application identity, active-scanner indicator, Home and Settings actions, and mobile behavior.
- Added responsive placement so the footer uses the single content column after the desktop sidebar becomes the mobile drawer.

### Compatibility

- No scanning, Bay Map, backend, database, permission, or API behavior changed.
- No migration, installer, BAT file, image, or database replacement is required.
- Advanced only the footer stylesheet cache key to v162.

## v0.161 - Footer Ownership, Bay Barcode Recovery, and Timed Scan Errors

### Global footer

- Moved the desktop footer into a dedicated last-loaded shell stylesheet so page-specific CSS can no longer clear, fade, mask, or replace its dark operations background.
- Preserved the application identity, active-scanner surface, Home and Settings actions, and mobile footer behavior.

### Bay Scanner matching

- Fixed Bay Map Add mode searching only the newest Indian Trail delivery list when no list was explicitly selected.
- Bay Map now searches every active Indian Trail destination list and binds a successful scan to the uniquely matched delivery date and line item.
- Expanded alternate labels such as `43273429.5` and `43273429.30` to match the stored order number as well as barcode, source identity, Job Nr., and item number.
- Preserved ambiguity protection so the scanner reports a clear correction instead of moving the wrong piece.
- Kept the combined manual Order + Item formats from v0.160 and routed them through the corrected cross-date Bay matching path.

### Timed scan failures

- Added one shared timed top-of-screen error card for Bay Scanner barcode entry, Bay manual entry, Scan-page barcode entry, and Scan-page manual entry.
- The timed card shows the entered value and exact validation or backend error so operators can correct a scan without relying on a brief inline message.
- Changed missing manual scan fields and missing Indian Trail bay selection into surfaced scanner errors instead of silent returns or short floating notices.

### Compatibility

- Preserved Bay Add/Remove behavior, outbound safety overrides, assignment history, recent scans, All Scans pagination, seven-day Bay activity retention, permissions, and database schema.
- No migration, installer, BAT file, database replacement, or server-route change is required.
- Added `static/css/shell.css` as the final shared-shell owner and advanced only changed asset cache keys to v161.

## v0.160 - Global Footer, Flexible Bay Entry, External Barcode Support, and Selected Bay Polish

### Global application footer

- Rebuilt the non-page-specific desktop footer as a solid operations bar so the bottom of the web app no longer appears faded.
- Added a compact application identity, active-scanner status surface, and polished Home and Settings actions while preserving the existing scanner name and navigation behavior.

### Bay Scanner manual entry

- Replaced the separate Order Number and Item Number controls with one aligned Order + Item field and Submit action.
- Accepts compact and separated formats including `236505001`, `236505 1`, `236505.1`, and `236505/1`.
- Added Enter-key submission and strict validation that rejects ambiguous values instead of guessing.

### Alternate product barcodes

- Added Bay Map Add and Remove matching for alternate product labels such as `43273429.30`.
- Matches exact stored barcode, source identity, or Job Nr. values and can resolve a dotted job/item label against the item number.
- Uses unique highest-confidence matching and reports ambiguous labels rather than moving the wrong piece.

### Selected Bay GUI

- Added a polished Indian Trail header, stronger modal framing, improved content spacing, and clearer card depth to the individual Selected Bay window.
- Preserved all existing fulfillment details, scanner targeting, bay status actions, job expansion, item movement, and close behavior.

### Compatibility

- Preserved Add/Remove workflows, recent-scan limits, sticky scanner behavior, seven-day Bay activity retention, All Scans pagination, permissions, and database schema.
- No migration, server-route change, installer, BAT file, image, or database replacement is required.
- Advanced only the changed global stylesheet, Bay stylesheet, and application JavaScript cache keys to v160.

## v0.159 - Bay Map Edit Header Cleanup and All Scans Visual Polish

### Edit Physical Bay Map

- Removed the unused Close button from the top-right of the Edit Physical Bay Map header.
- Kept Cancel as the intentional way to leave edit mode without saving and Save Layout as the deliberate commit action.
- Removed the obsolete JavaScript element binding, click listener, and button-specific stylesheet rule instead of leaving dead ownership behind.

### All Bay Scans

- Rebuilt the paginated All Bay Scans window with the same restrained operations-console polish used by the Bay Map action workflows.
- Added a dark Indian Trail activity header, seven-day retention summary, total-scan and current-page metrics, and clearer location-correction guidance.
- Improved sticky table headers, alternating rows, status accents, action/current-bay/user pills, hover readability, and the Change Location control.
- Polished the 25-row pager, empty state, loading state, and retryable failure state without changing server-side pagination or retention behavior.
- Prevented the All Scans custom modal style marker from leaking into subsequently opened Admin windows.

### Compatibility

- Preserved Bay Scanner follow behavior, recent-scan limits, seven-day Bay activity cleanup, 25-row server pagination, location correction permissions, APIs, and database schema.
- No backend, migration, installer, BAT, image, or database change is required.
- Advanced only the Bay Map stylesheet and application JavaScript cache keys to v159.

## v0.158 - Expanded Fullscreen Bay History and Operations UI Polish

### Bay Scanner history

- Increased fullscreen Recent Bay Scans by two rows for both workflows.
- Fullscreen Add to Bay now shows up to five recent movements, and fullscreen Remove from Bay shows up to six.
- Preserved the normal-window limits of one Add movement and two Remove movements.
- Increased the initial Bay Map event request to six retained movements so every fullscreen row is available without another request.

### Bay Map workflow presentation

- Reworked the Old Bays through Edit Map launcher into five consistent operational cards with distinct restrained accents, stronger icons, clearer depth, and improved hover/focus feedback.
- Polished the Rush / Remake window with a priority-colored header, stronger step cards, clearer form hierarchy, and more deliberate primary/destructive actions.
- Polished Manage Items with a clearer split workspace, stronger selected-item summary, improved assignment rows, focused fields, and semantic Move, Clear, Scanner, and Rush actions.
- Polished Edit Bays with a stronger editor header, clearer group navigation, refined forms and bay cards, and improved focus/selection states.
- Polished Edit Physical Bay Map with a dedicated map-edit header, organized tool strip, clearer Save/Cancel actions, and refined drag columns, group cards, and drop zones.

### Compatibility

- Preserved Bay Scanner follow behavior, Add/Remove logic, All Scans pagination, seven-day Bay activity retention, assignment rules, APIs, permissions, and database schema.
- No backend, migration, installer, BAT, or database change is required.
- Advanced only the Bay Map stylesheet and application JavaScript cache keys to v158.

## v0.157 - Adaptive Bay History Loading and Preassignment Move Safety

### Bay Map scanner

- Fixed Recent Bay Scans remaining at one row because the normal Bay Map refresh requested only one retained event from the paged history endpoint.
- The compact scanner now loads the newest four retained movements once, then applies the existing mode-aware limits locally: Remove shows two and Add shows one in a normal window; fullscreen Remove shows four and fullscreen Add shows three.
- Preserved immediate recent-history rerendering when the scan mode or fullscreen state changes.

### Bay assignment correctness

- Fixed moving a PreAssigned item to another bay changing its assignment status to Moved.
- A PreAssigned destination correction now remains PreAssigned, so a missing piece is not falsely counted as physically scanned into the destination bay.
- Physical Assigned/Moved rows continue to become Moved and remain counted as present.
- Added the previous and resulting assignment status to the maintained move audit payload.

### Compatibility

- Preserved the v0.155 seven-day Bay Map activity retention, 25-row All Scans pagination, read-only Latest Activity, scanner follow behavior, permissions, and database schema.
- No migration, server-route change, CSS change, installer, or BAT file is required.
- Advanced only the application JavaScript cache key to v157.

## v0.156 - Bay Scanner Fixed-Width Follow and Adaptive Recent History

### Bay Map scanner

- Corrected the fixed-follow controller so the Bay Scanner keeps the exact measured right-rail width instead of inheriting a viewport-wide `width: 100%` rule after it becomes fixed.
- Added explicit fixed left/width CSS variables, viewport-edge clamping, border-box sizing, and automatic width recalculation on resize and fullscreen changes.
- Preserved the non-sticky Bay Map action toolbar, five-pixel viewport spacing, internal overflow, and normal-flow anchor height.
- Made Recent Bay Scans adapt to the active workflow: Remove shows up to two rows normally and Add shows one.
- In fullscreen, Remove shows up to four recent rows and Add shows up to three.
- Refreshes recent history immediately when Add/Remove mode or fullscreen state changes.

### Compatibility

- Preserved the v0.155 seven-day Bay Map activity retention, 25-row All Scans pagination, Latest Activity summary, location correction, scan workflows, permissions, and database schema.
- Advanced only the changed Bay Map CSS and application JavaScript cache keys to v156.

## v0.155 - Bay Scanner Sticky Follow, Latest Activity, and Paged History

### Bay Map scanner

- Replaced the unreliable nested CSS sticky behavior with one measured Bay Scanner follow controller.
- Keeps the Bay Map action toolbar in normal flow while fixing only the scanner after it reaches the usable viewport below the application header.
- Preserves the scanner's rail width, a five-pixel viewport margin, fullscreen behavior, and internal scrolling when its content is taller than the available screen.
- Rebuilt Latest Activity as a professional read-only summary with scan result, time, current bay, action, order, item, Job Nr., customer, user, and result details.
- Removed bay-location editing from Latest Activity and Recent Bay Scans; location correction now exists only in All Bay Scans.
- Kept Recent Bay Scans at one compact read-only physical movement.

### All Bay Scans performance and retention

- Changed All Bay Scans to open immediately with a loading state and request one server-side page at a time.
- Limited every page to a maximum of 25 events and added Previous, Next, and numbered page controls with total-result information.
- Added a seven-day Bay Map event retention window. Expired `bay_events` rows are deleted at startup and during throttled Bay Map history reads.
- The cleanup affects only Bay Map movement activity; delivery-list scan history, audit history, rack history, reject history, packing history, and import history remain unchanged.
- Kept active-item location correction in All Bay Scans through the maintained Bay Map move workflow.

### Compatibility

- Preserved Bay Scanner Add/Remove behavior, barcode and manual scanning, route progress, Undo/Redo, permissions, and existing Bay Map assignment APIs.
- No database schema migration is required.
- Advanced the changed Bay Map CSS and application JavaScript cache keys to v155.

## v0.154 - Bay Scanner Sticky Containing Block and Manual Row Alignment

### Bay Map scanner

- Restored sticky scrolling by making the Bay Map right rail stretch to the full map-row height while keeping the action toolbar in normal, non-sticky flow.
- Kept scanner stickiness active through compact workstation widths and disables it only for the true mobile layout.
- Kept the scanner directly beneath Edit Map with the maintained four-pixel normal-flow gap and a five-pixel sticky viewport offset.
- Added scoped overflow ownership to the Bay Map shell and right rail so an inherited overflow rule cannot disable sticky positioning.
- Replaced the Manual Scan label wrappers with direct Order Number, Item Number, and Submit grid children.
- Aligned all three Manual Scan controls on one 34-pixel row and reduced the section's vertical height.
- Left-aligned Item Number content while retaining its three-digit limit.
- Moved the Target Bay and Scan Barcode titles closer to their corresponding inputs.
- Advanced the Bay Map stylesheet cache key to v154.

### Compatibility

- Preserved Bay Scanner IDs, Add/Remove behavior, target selection, manual submission, Undo/Redo, route progress, history, APIs, permissions, and database schema.
- Changed only `index.html`, `static\css\bays.css`, and `README_CHANGELOG.md`.
- No JavaScript, backend, database migration, installer, BAT file, or global stylesheet change is required.

## v0.153 - Bay Scanner Sticky Ownership and Manual Row Correction

### Bay Map scanner

- Removed the extra Bay Scanner sticky wrapper and made the scanner panel itself the sticky element.
- Kept Old Bays, Rush / Remake, Manage Items, Edit Bays, and Edit Map in normal non-sticky document flow.
- Forced the scanner to follow Edit Map with only the maintained four-pixel right-rail gap in normal and sticky workflows.
- Eliminated the wrapper height and inherited grid-row behavior that repeatedly left a large blank area above Bay Scanner.
- Replaced the older v150/v151 Manual Scan layout selectors with an isolated v0.153 one-row owner.
- Kept Order Number and Item Number as in-field placeholders with hidden accessible labels.
- Aligned Order Number, Item Number, and Submit on one 36-pixel control row and reduced the Manual Scan section height.
- Advanced the Bay Map stylesheet cache key to v153.

### Compatibility

- Preserved Bay Scanner control IDs, Add/Remove behavior, manual submission, route progress, history, APIs, permissions, and database schema.
- Changed only `index.html`, `static\css\bays.css`, and `README_CHANGELOG.md`.
- No JavaScript, backend, database migration, installer, BAT file, or global stylesheet change is required.

## v0.152 - Bay Scanner Manual Alignment and Content Fit

### Bay Map scanner

- Moved the Manual Scan Order Number and Item Number labels into their respective input fields as placeholders while retaining accessible hidden labels.
- Aligned Order Number, Item Number, and Submit on one consistent 42-pixel control row.
- Increased the Item Number field and Submit button widths while preserving the wider flexible Order Number field.
- Removed the forced full-viewport scanner height so the panel ends directly after Recent Bay Scans when its content fits.
- Preserved the sticky viewport height limit and internal scrolling when the scanner content exceeds the available screen height.
- Advanced the Bay Map stylesheet cache key to v152.

### Compatibility

- Preserved existing Bay Scanner IDs, manual submission behavior, Add/Remove workflow, target selection, recent activity, APIs, permissions, and database schema.
- Limited the release package to the files changed for this correction.
- No database migration, backend patch, installer, BAT file, or JavaScript change is required.

## v0.151 - Project Structure Organization and Bay Scanner Target Alignment

- Consolidated maintained browser behavior into `static\js\app.js`.
- Moved Rejects page, reject workflow, timeline, and internal-reject
  presentation rules from the global stylesheet into `static\css\rejects.css`.
- Organized application services under `backend` and database ownership under
  `database` while retaining `server.py` as the root launcher.
- Moved optional Docker and Azure App Service templates under `deployment`.
- Added the missing container dependency manifest for the Azure SQL adapter.
- Retained `.dockerignore`, `pytest.ini`, and the paired Windows launchers at
  the root because Docker, pytest, and the BAT launcher discover them there.
- Updated automation integration paths and project-structure validation.

### Bay Map scanner

- Rebuilt Target Bay as a dedicated label row followed by one aligned input-and-Clear control row, preventing overlap with the Add/Remove selector.
- Increased separation beneath the mode selector so the Add destination remains visually distinct at normal and compact workstation heights.
- Rebuilt Manual Scan with a section heading above one aligned Order Number, Item Number, and Submit row.
- Increased the Manual Scan section height, widened the Item Number field, and enlarged Submit while preserving the wider Order Number field.
- Removed Bay Scanner Route Pulse percentage labels in both Add and Remove modes while retaining Outbound, In Transit, and Received quantities.
- Advanced only the changed Bay Scanner CSS and app JavaScript cache keys to v151.

### Compatibility

- Preserved existing Bay Scanner IDs, Add/Remove behavior, target selection, manual scan submission, route quantities, APIs, permissions, and database schema.
- Limited this merge-friendly package to the four files changed for the correction.
- No database migration, installer, BAT file, or backend patch is required.

## v0.150 - Bay Scanner Control Alignment and Status Refinement

### Bay Map scanner

- Moved Target Bay onto a clean row beneath the Add/Remove selector and aligned its input with Clear.
- Rebuilt Manual Scan with labels above aligned Order and Item fields.
- Increased the Item field and Submit action while preserving the wider Order field.
- Increased Manual Scan height slightly to prevent clipping.
- Removed Route Pulse percentage labels in Add and Remove modes.
- Replaced status text with compact semantic icons in Latest Activity and Recent Bay Scans.
- Applied matching green, amber, red, and neutral background tones to scan-result surfaces.
- Advanced browser cache keys to v150.

### Compatibility

- Preserved the single recent movement, sticky viewport fit, Bay Scan APIs, assignments, All Scans, permissions, and database schema.
- No database migration or backend patch is required.
- No PNG previews were generated or packaged.

## v0.149 - Bay Scanner Sticky Fit and Input Refinement

### Bay Map scanner

- Limited Recent Bay Scans to one compact physical movement so the latest-scan card remains visible in Add mode.
- Restored Check feedback to Latest Activity and Recent Bay Scans with Success, Check, Failed, and neutral states.
- Sized the sticky scanner from 5 px below the viewport top to 5 px above its bottom.
- Preserved the same five-pixel sticky fit in fullscreen.
- Closed the remaining Bay Map rail spacing while keeping action buttons in normal, non-sticky flow.
- Rebuilt Add destination as one contained Target Bay input and Clear action.
- Condensed Manual Scan into one aligned row with consistent input heights and surfaces.
- Converted Undo and Redo to icon-only controls with accessible labels.
- Applied maintained application button classes to Manual Submit and Clear.
- Advanced browser cache keys to v149.

### Compatibility

- Preserved v148 structural-event filtering, Bay Scan APIs, assignment movement, All Scans, permissions, and database schema.
- No database migration or backend patch is required.
- No PNG previews were generated or packaged.

### Validation

- Added v149 checks for a one-row history limit, Check feedback, five-pixel sticky viewport fit, fullscreen fit, toolbar separation, simplified destination/manual controls, icon-only correction buttons, shared action styles, unique IDs, and code-only release hygiene.

## v0.148 - Bay Scanner History and Flow Refinement

### Bay Map scanner

- Removed the normal-flow gap between the non-sticky Bay Map action toolbar and the scanner panel.
- Kept the action toolbar static while preserving the scanner-only sticky behavior.
- Removed the visible live-time badge beside the Bay Scanner title and retained its ID as a hidden compatibility node.
- Hid Route Pulse percentage labels in Remove mode while keeping quantity totals visible.
- Replaced Recent Bay Scans' collapsible disclosure with a permanently open compact table.
- Limited recent rows to Order Nr., Job Nr., Action, and editable Current Bay.
- Removed horizontal and vertical scrolling from the recent history surface.
- Advanced browser cache keys to v148.

### History safety

- Bay event history now returns only item-linked physical bay events.
- Structural events such as layout updates, bay creation, and bay deletion are no longer inserted into Bay Scan history.
- Existing historical structural events are filtered from Recent Bay Scans and All Scans.
- Administrative audit records remain intact for accountability.
- No database schema migration is required.

### Validation

- Added v148 checks for static-toolbar adjacency, scanner-only stickiness, hidden live badge, Remove-mode percentage suppression, permanently open non-scrollable history, four-column rendering, editable Current Bay, unique IDs, JavaScript ownership, and backend history filtering.

## v0.147 - Bay Scanner Route and Sticky Refinement

### Bay Map scanner

- Removed the redundant receiving eyebrow, workflow sentence, and visible Current Mode summary from the blue header.
- Kept the Bay Scanner title, live scan status, and Route Pulse in one continuous header surface.
- Replaced bright Route Pulse surfaces with contained dark-blue metric cards.
- Suppressed the legacy dotted transit connector, arrow, and inherited white transit pill styling.
- Added paint containment to prevent Route Pulse elements from drawing outside the panel.
- Hid Destination Control in Remove mode while preserving it for Add mode.
- Changed only the scanner slot to `position: sticky` with an 8-pixel top offset; the Bay Map action toolbar remains in normal flow.
- Advanced browser cache keys to v147.

### Safety and validation

- No API route, database schema, permission, scan rule, or backend workflow was changed.
- Added v147 release checks for removed header copy, hidden mode summary, route pseudo-element suppression, dark route surfaces, mode-controlled Destination Control, sticky ownership, unique IDs, cache markers, and CSS integrity.

## v0.146 - Bay Scanner Workflow Refinement

### Bay Map scanner

- Merged the title and Route Pulse into one continuous blue header with all route metrics contained inside the panel.
- Updated Remove copy from `Find the piece's current bay` to `Finds the piece's current bay`.
- Removed the redundant `Current bay is found automatically in Remove mode.` guidance.
- Removed the main barcode Submit Scan button; scanner input and Enter continue to use the maintained form workflow.
- Moved Undo and Redo onto the scan field's upper-right border for faster correction access.
- Replaced collapsible Manual Entry with one Order / Item / Submit row directly below the barcode input.
- Made the Order field flexible and larger, while Item is compact and limited to three numeric characters.
- Preserved route-manifest access, latest activity, recent history, All Scans, and Change Location.
- Advanced browser cache keys to v146.

### Safety and validation

- No API route, database schema, permission, scan rule, or backend workflow was changed.
- Added v146 release checks for header nesting, route containment, removed copy, no barcode submit button, overlay correction controls, manual-row geometry, unique IDs, cache markers, and CSS integrity.

## v0.145 - Bay Scanner Layout Correction

### Bay Map scanning panel

- Corrected the first v144 console after real floor rendering showed older Bay Scanner grid rules still influencing the new markup.
- Moved Indian Trail Route Pulse above Scan Command so route state is visible before the operator begins a bay scan.
- Removed inherited panel padding and made the blue header meet the outside border and both rounded top corners.
- Replaced the remaining v105/v137 layout-owner classes with dedicated v145 markup while preserving every operational element ID.
- Explicitly reset the scanner form, command, mode, destination, barcode, manual-entry, and activity grids so they cannot collapse into implicit narrow columns.
- Kept Remove/Add, Target Bay, Bay Code, Clear, barcode input, Submit Scan, Undo, and Redo in stable readable rows.
- Raised the sticky desktop offset to 68 pixels normally and 60 pixels on short floor-computer displays; the initial unscrolled position remains unchanged.
- Rebuilt the five Bay Map workflow buttons as an evenly sized toolbar with readable labels, consistent icon sizing, and restrained interaction feedback.
- Kept Recent Bay Scans visible in the short-height sticky layout while maintaining complete-panel visibility.
- Preserved Manual Entry, All Scans, route manifest access, latest result, location correction, and all existing scanner workflows.

### Safety and validation

- No API, database, permission, scan, bay-assignment, transit, undo/redo, or event-handler behavior changed.
- Replaced the v144 scoped stylesheet with the v145 owner instead of loading another override layer.
- Added focused checks for route-before-command ordering, flush header ownership, sticky offsets, professional action-toolbar ownership, stable command rows, unique IDs, cache keys, and release documentation.
- Rendered the corrected panel at normal and 1366x768 sticky workstation sizes and verified it remains stable even when aggressive legacy grid rules are simulated.
- Advanced browser cache keys to v145.

## v0.144 - Bay Scanner Operations Console Redesign

### Bay Map scanning panel

- Completely rebuilt the Indian Trail Bay Scanner presentation as a compact scan-first operations console.
- Replaced the vertically stacked three-step cards with a single command surface that keeps action, target bay, barcode, Submit, Undo, and Redo together.
- Made the barcode field and primary Submit Scan button the strongest visual controls.
- Reworked Add and Remove into a professional segmented mode selector with clear semantic states.
- Combined target-bay instructions and entry into a compact destination strip that remains understandable in Remove mode.
- Condensed route progress into a small Outbound / In Transit / Received pulse without removing the manifest shortcut or dual progress behavior.
- Kept Manual Entry and Recent Bay Scans available as compact disclosures instead of permanent tall sections.
- Redesigned latest activity to keep current bay, result, order, time, and location correction readable in the right rail.
- Added restrained panel entrance, live-status pulse, header sheen, progress motion, focus feedback, disclosure transitions, and submit-button polish.
- Added a compact-height desktop state that reduces helper copy and reorganizes latest activity while preserving every operational control.
- Added `prefers-reduced-motion` handling so all decorative motion can be disabled without affecting workflow.

### Safety and validation

- Preserved every maintained Bay Scanner HTML ID used by `app.js`.
- Did not change API routes, database schema, permissions, scan logic, undo/redo behavior, or event handlers.
- Added a scoped `bay-scanner-v144.css` owner instead of adding more broad rules to the already layered global stylesheet.
- Added patch validation for unique HTML IDs, required controls, cache keys, release markers, CSS balance, scoped ownership, and reduced-motion support.
- Replaced the unused bottom-docked v144 draft note with the finalized right-rail console documentation.
- Advanced browser cache keys to v144.

## v0.143 - Internal Reject Timeline Redesign

### Internal Reject Tracking

- Rebuilt the page to match the approved timeline concept with one polished quality-recovery workspace.
- Added a strong IR page identity, primary Log Internal Reject action, and compact Refresh/Clear controls.
- Rebalanced search, incident-range, From, Through, and Location controls into one readable toolbar.
- Added a live filtered summary for total reject events, unique machines/locations, users, and rejected quantity.
- Changed reject history into collapsible date groups with a vertical incident timeline.
- Added expandable event cards that keep the normal view concise while exposing customer, job, product, and notes on demand.
- Kept grouping based on the rejected/logged date and kept delivery date visible on every incident card.
- Hid the routine success status line after data loads while preserving loading, warning, and failure feedback.
- Advanced browser cache keys to v143.

### Safety and validation

- Preserved the existing reject logging API, process-reset behavior, search, date filters, and catalog controls.
- Added release checks for timeline structure, summary metrics, location filtering, version markers, unique HTML IDs, JavaScript syntax, and CSS balance.

## v0.142 - Custom Roles and Interface Refinements

### Roles and users

- Added a guided **Create a new role** workflow to Roles & Permissions.
- Administrators can enter a role name and description, then explicitly select or omit every available permission.
- Added Select all and Clear all permission actions while keeping zero-permission roles possible after confirmation.
- Added a guarded `/api/admin/roles` create endpoint through an idempotent backend patch that preserves current `server.py` and `delivery_store.py` changes.
- Rejects case-insensitive duplicate role names and unknown permissions.
- Records role creation in the existing audit history.
- Newly created roles automatically appear in Create User, existing-user role selectors, and the User Directory role filter.
- Rebalanced Create User into Account Details and Starting Access panels so the form uses the full modal width and remains readable at smaller sizes.

### Internal rejects and Scan presentation

- Simplified Reject Tracking into one professional workspace with a single title, primary action, filter toolbar, status line, and history area.
- Removed duplicated page headings and workflow-tag clutter.
- Changed the `IR` row flag to white text on a dark, restrained pulsing red background.
- Added a full-width incident strip below rejected Scan rows showing reject reason, break location/machine, rejected date/time, and event count.
- Preserved the normal line-item columns and flags instead of squeezing long incident details into the Job Nr. cell.

### Filters and navigation

- Changed glass-type filters from equal-width truncated cells to content-aware wrapping buttons that show the complete glass description.
- Corrected sidebar navigation line height and lower padding so letter descenders are no longer clipped.
- Advanced browser cache keys to v142.

### Safety and validation

- Added timestamped backend backups and automatic syntax validation to `Apply-v142-RoleManagementPatch`.
- The backend patch is repeat-safe and restores the original files if final validation fails.
- Added v142 release checks for custom-role wiring, dynamic role options, Reject page ownership, full-width reject details, adaptive glass filters, sidebar text containment, version markers, and unique HTML IDs.

## v0.141 - User Access Management Redesign

- Replaced the Edit Users modal's wide eight-column table with a responsive, expandable user-card directory.
- Added a polished user-management overview showing total, active, signed-in, and inactive account counts.
- Added local search plus Status and Role filters for faster account lookup.
- Added an expandable, guided Create User form with clearer labels, field help, and responsive layout.
- Organized each user into Access & Profile, Password Reset, and Account Status sections.
- Preserved every existing backend workflow for email, role, multi-station assignment, password generation/reset, activation, deactivation, and deletion.
- Replaced icon-only account actions with labeled, accessible buttons while retaining the existing icon library.
- Preserved user-directory filters after saving or refreshing an account.
- Added desktop, compact desktop, tablet, and mobile layouts without horizontal scrolling.
- Added v141 regression checks for markup ownership, event wiring, version markers, CSS structure, and responsive containment.

## v0.140 - Attention Filters, Reject Controls, and Import Run Deduplication

- Moved **Internal Rejects** from the Status filter group into **Attention** beside Remakes and Rushes.
- Applied the shared priority-button alert/clear presentation to Internal Rejects.
- Made the Filters `IR` counter neutral gray at zero and red only when rejected pieces exist.
- Stabilized the Scan page delivery-date selector width when an unreviewed-update indicator is present.
- Removed the redundant checkmark from the selected delivery-date menu row; the selected highlight remains.
- Limited date-level New/Updated markers to one canonical workflow stage per date so duplicate stage notices do not keep an icon visible after review.
- Immediately clears the reviewed date marker, then verifies the result against the server-side per-user receipts.
- Removed Reject Tracking's Reject events, Rejected pieces, Rejected today, and Affected orders statistic cards.
- Rebuilt the Reject search field with one clean outline instead of nested rounded borders.
- Enlarged and modernized the Reject From/Through date controls.
- Preserved original import-result timestamps and run IDs when building notification history entries.
- Added content-and-time deduplication so the latest import snapshot and its notification copy cannot appear as two runs a few seconds apart.
- Added v140 tests for filter placement, conditional IR styling, date-selector geometry/review cleanup, Reject page cleanup, and near-time import-run deduplication.

## v0.139 - Dropdown Audio, Internal Reject Awareness, and Import Run History

### Dropdowns and Scan filters

- Added the existing subtle open/close swoosh to maintained dropdown opening and selection.
- Added per-user New/Updated indicators to Scan delivery-date options.
- Added Internal Rejects to the Status filters, a red `IR` row flag, and a labeled `IR` Filters counter.
- Removed the unidentified trailing Filters count.

### Internal rejects

- Reject date filters now use the reject/logged timestamp.
- Reject history groups by logged date while each record displays its delivery date and complete reject details.
- Internal rejects create persistent bell notifications and a nonintrusive 30-second alert with View and Acknowledge actions.

### Import run organization

- Delivery List Management loads the current local day’s automation runs, displays five per page, and resets the current-day view after the date changes.
- Automation Control Center history is nested into collapsible day groups, run-time groups, and individual delivery-list results.

### Validation

- Added v139 regression coverage for selector audio, date indicators, Internal Reject filtering/notification behavior, current-day run pagination, nested automation history, IDs, syntax, and CSS integrity.

## v0.138 - Internal Reject Page and Entry Workflow

### Reject Tracking page

- Rebuilt the page header into a focused quality-recovery command area with a standard primary **Log Internal Reject** action.
- Replaced generic mini-stat blocks with professional reject-event, rejected-piece, today, and affected-order summary cards.
- Redesigned the history filter into a labeled delivery-date workflow with All Dates, Today, Last 7 Days, Last 30 Days, and Custom Range presets.
- Added From/Through range validation, linked date input limits, a dedicated Clear Filters action, and clearer active-filter status text.
- Redesigned date groups and reject records so order/item, quantity, reason, break location, logged time, user, and notes remain readable without oversized rows.
- Added polished loading, empty, retry, warning, and error states.

### Log Internal Reject GUI

- Added a direct click owner for the static Reject-page button instead of relying only on document-level delegation.
- Opens the reject window immediately, even while reasons and locations are still loading, preventing a slow catalog request from making the action appear broken.
- Added an explicit **Verify Item** button and Enter-key verification for order/item fields.
- Invalidates an old match whenever the order or item changes, preventing submission against stale verification data.
- Shows the verified delivery date, quantity, and affected stages before submission.
- Added clear catalog loading/failure guidance, a workflow-impact notice, Cancel action, and a responsive submit bar.
- Added a modal ownership marker so reject-specific sizing and layout do not affect rack/history dialogs.

### Maintenance and validation

- Removed superseded v137 reject-modal selectors and stale responsive reject overrides instead of adding another duplicate override layer.
- Advanced browser cache keys and per-user notification storage namespace to v138.
- Added v138 release tests for repeatable button ownership, immediate modal opening, date presets, validation, explicit verification, responsive layout, unique IDs, JavaScript syntax, and CSS duplicate detection.

## v0.137 - Bay Scanner Readability, Packing Lists, and Review Workflow

### Bay Scanner redesign

- Reworked the Bay Map scanner into a contained, readable three-step workflow with larger operational text and shorter instructions.
- Compacted route progress into one horizontal Outbound / In Transit / Received summary with readable percentages.
- Kept target selection, barcode entry, Submit, Undo, Redo, manual entry, latest result, and recent history within the right rail at desktop and responsive widths.
- Added final high-specificity ownership rules so older Bay Scanner compatibility layers cannot restore the broken two-column layout on narrower screens.

### Rack packing-list correction

- Stopped rack-detail and Truck packing-list printing from silently inheriting the currently selected Scan-page delivery date.
- Rack/Truck detail printing now includes all active pieces currently assigned to the selected rack.
- Explicit date-specific print buttons still pass a delivery date when the user deliberately chooses one.
- Packing-list history snapshots use the same corrected selection scope.

### Internal rejects and destructive icons

- Rebuilt the Log Internal Reject GUI into clear Identify and Describe steps with a verification preview and a single deliberate submit action.
- Replaced the one-time static button binding with a guarded delegated trigger so the Log Internal Reject button can be used repeatedly after closing the modal.
- Added visible loading protection while reject catalogs are being requested.
- Changed trash icon buttons to white surfaces with visible red icons at rest; hover/focus intentionally reverses them to white on red.

### New/Updated review and Scan filters

- Removed the duplicate personalized New/Updated banner previously injected below the Scan filters.
- Kept and polished the bottom-right personalized review prompt.
- Added Review Updates and Mark Reviewed controls beside Filters; Mark Reviewed appears only while the New/Updated filter is displaying the exact pending notice set.
- Added compact Remake, Rush, and New/Updated count badges directly in the Filters summary.
- Made the glass-type selector a responsive, vertically scrollable grid so large glass catalogs do not overlap.
- Advanced browser asset cache keys to v137.

## v0.136 - Interface Stability and Professional Control Polish

### Rack Overview and Reject Tracking

- Fixed rack cards failing to open the rack-details GUI because the modal called helper functions that existed only inside the rack-page renderer.
- Removed the duplicate local rack status wrappers and reused the maintained global rack status helpers.
- Added visible Reject Tracking loading, success, warning, empty, retry, and server-error states.
- Reject history and reject reason/location catalogs now load independently, so a catalog failure no longer blanks otherwise valid history.
- Reject logging verifies an active order/item match, prevents duplicate submissions while saving, and explains when Admin catalog setup is incomplete.
- Replaced the blank reject navigation square with a masked shield/reject icon that works with the current sidebar icon system.

### Bay Scanner and shared controls

- Rebuilt the final Bay Scanner ownership rules so the right rail, sticky slot, panel, workflow steps, inputs, utilities, and history stay within the available width.
- Wide recent-scan tables now scroll inside the scanner card rather than forcing the page wider.
- Changed workflow cards to a stable step-number/content layout that remains readable in the normal right rail and on smaller screens.
- Replaced the broad glossy every-button override with a scoped action-control system.
- Navigation cards, filter tabs, import tabs, route lanes, and other selectable surfaces retain their component-specific appearance.
- Global Search, Print / Export, Admin edit commands, rack actions, reject actions, and Bay Scanner submit controls use the same flatter professional hover/press/focus language.

### Admin GUI and import-run history

- Added a shared polished frame, header, scrolling body, form surface, and close-button treatment for Admin editor GUIs without replacing each editor's internal layout.
- Made import-run tabs proper accessible tabs with persistent selected state, readable active colors, and stable horizontal scroll position.
- Removed the duplicate render path used when selecting an import run, preventing selected tabs from disappearing or being immediately replaced.
- Advanced browser asset cache keys to v136.
- Added focused v136 release tests for rack modal helper ownership, reject resilience, tab accessibility, button scope, sidebar icon rendering, and Bay Scanner width containment.

## v0.135 - Personalized Update Review and Operations Workflows

### Personalized New/Updated review

- Replaced browser-only New/Updated clearing with persistent per-user line flags and exact notice receipts.
- Loads the selected delivery list and its personalized update flags in parallel so the review prompt no longer delays normal list selection.
- Shows a compact prompt when the selected list contains unseen New or Updated lines for the signed-in user.
- **Review updates** activates the Updated filter first; **Mark reviewed** is enabled only after the same notice set has been displayed.
- Sends the exact notice IDs to the server and clears only that user's receipts for that list. Other users retain their own unseen state.
- Invalid or stale notice sets are rejected instead of accidentally clearing newer changes.
- Clears the client flag cache when a new automation notification/catalog update arrives so unchanged cached results cannot hide a newly imported change.
- Keeps legacy `New Line` / `Updated Line` process text from acting as the authoritative per-user state.

### Import-run navigation and automation history

- Bell notifications now open and pin the exact saved import result that produced the notification.
- Stops the older automation listener from replacing that pinned result with the newest run on the next 10-second heartbeat.
- Added time-based import-run tabs to Delivery List Management with New / Updated, No Changes, Failed, and Running states.
- Keeps a user-selected run active while normal catalog refreshes continue in the background.
- Groups automation audit history by date and time, keeps result details collapsed initially, and preserves searchable/paginated history controls.
- Renamed the Admin command to **Delivery Automation Control Center** to match its actual scheduling, manual-run, status, and history responsibilities.

### Scan page and Bay Map usability

- Preselects today's Staging delivery list during authenticated startup when one exists, so the first visit to Scan begins on today's Staging stage.
- Displays the line's plain quantity in the Scan-page QTY column; scanned progress remains available through row status and hover details.
- Refined the Bay Map scanning panel into a clearer workflow with stronger spacing, hierarchy, status feedback, and responsive behavior.
- Added a shared professional button system with consistent radius, typography, depth, focus, hover, active, disabled, primary, secondary, success, and danger treatments. Existing button sizes and semantic colors remain available.
- Added a v135 CSS ownership note requiring existing selectors and primitives to be reused before new override blocks are introduced.
- Verified the stylesheet has balanced braces and no exact duplicate qualified rules after the release changes.

### Rack workflow and packing-list history

- Removed the permanent selected-rack details column from Rack Overview.
- Clicking a rack now opens a responsive rack-details modal with compact order/item-first rows, quantity, customer, job/glass, dimensions, delivery date, scan time, and existing management actions.
- Corrected long rack scan timestamps so they wrap inside the rack card instead of pushing Reset Rack out of the card.
- Added **Packing List History** to Rack Overview.
- Records an immutable snapshot immediately before a rack packing list is printed, including rack identity, user, print time, delivery date, quantities, and the exact item rows.
- Historical snapshots remain viewable and printable even after the active rack contents later change.

### Manual delivery-list entries

- Added a manual-order form to the Edit Delivery Lists window.
- Requires order, item, quantity, customer, glass/product, dimensions, and an explicit route before insertion.
- Checks the order/item against every active delivery list inside the configured full automation window and blocks duplicates.
- Inserts the line into Staging, Outbound, and the matching destination stage for the selected delivery date.
- Supports a **manual scanning only** declaration with a visible marker and non-scannable `MANUAL-...` identity.
- Adds per-user New notices for every inserted stage copy.
- Patches the maintained delivery-list refresh so manual entries survive automatic imports until the source workbook supplies the same order/item, at which point the source data takes ownership.

### Internal Reject Tracking

- Added a Rejects page to the left navigation with searchable, date-grouped internal reject history.
- Added a guided reject-entry modal for order, item, quantity, reason, break location, delivery date, and notes.
- Added Admin-managed Reject Reasons and Break Locations with safe deactivate/reactivate behavior.
- Logging a reject records an immutable reject event and audit entry, reduces scanned quantity for the rejected piece across active stage copies, adds `reject_reset` scan events, and reduces/removes matching active rack and bay quantities.
- Tracks cumulative reject count and latest reason/location/time on each affected line.
- Shows a red **INTERNAL REJECT** ribbon on Scan-page rows without conflating internal rejects with imported external RM/remake lines.

### Database, safety, and release packaging

- Added numbered/checksummed SQLite migration 004 for reject catalogs/events, packing-list snapshots, manual-entry audit rows, and per-line manual/reject fields.
- Preserved migration 001-003 checksums and the existing verified pre-upgrade backup path.
- Added `operations_features.py` to keep new operational business rules isolated from the large legacy store while reusing its maintained connections, line insertion, access, audit, rack, bay, and import behavior.
- Added `Apply-v135-OperationsPatch.bat` / `.py` to patch the current full `server.py` and `delivery_store.py` safely from a changed-files-only release. Both generated files are compiled before replacement, timestamped backups are retained, and a failed replacement restores both originals.
- Added focused backend, migration, frontend wiring, HTML-ID, CSS-duplicate, patch-idempotence, and checksum regression tests.
- Added `docs/V135_OPERATIONS_WORKFLOWS.md` with installation, permission, review, reject, manual-order, rack-history, testing, and rollback guidance.
- Advanced browser asset cache keys to v135.

## v0.134 - Floor Scheduler PowerShell Interpolation Fix

- Fixed `Install-DeliveryListSqlAutomationTasks.ps1` failing syntax validation at line 227 before Task Scheduler installation began.
- Delimited the automation-mode variable as `${automationMode}:` so PowerShell does not interpret the literal colon as part of the variable name.
- Preserved the existing `${incrementalTask}:` and `${fullTask}:` task-summary fixes.
- The floor setup still copies the runtime into `C:\DeliveryListAutomation\Scripts`, validates the installed PowerShell files, verifies scanner compatibility, and only then creates the hourly folder-import tasks.
- Existing scanner data, imported delivery lists, automation configuration backups, and SQL isolation remain unchanged.
- Advanced floor-setup and browser release markers to v134.

## v0.133 - Safe Windows Batch Launchers for Parenthesized Project Paths

- Fixed `Setup-Floor-Folder-Import-Automation.bat` opening briefly and closing before the PowerShell installer started when the project folder contained parentheses, such as `Delivery-List-Scanning-Project-main (5)`.
- Fixed the same CMD parser failure in `Create Desktop Shortcut.bat`.
- Rebuilt both launchers with label-based control flow instead of parenthesized command blocks that expanded project paths during CMD parsing.
- Quotes every project-derived path and keeps delayed expansion disabled so spaces, parentheses, ampersands, and common OneDrive folder names do not alter the command structure.
- Both launchers now always reach a visible success/failure screen and wait for a keypress before closing.
- Added `logs\floor-folder-import-setup-launch.log` and `logs\desktop-shortcut-launch.log` with the selected project/script paths and PowerShell exit code.
- Added `logs\floor-folder-import-setup-error.log` for unhandled PowerShell setup failures.
- Preserved the v132 folder-import-only runtime installation, hourly schedule, SQL isolation, scanner database, existing import configuration backups, and desktop-shortcut behavior.
- Advanced browser asset cache keys to v133.

## v0.132 - Floor Computer Hourly Folder-Import Setup

- Added `Setup-Floor-Folder-Import-Automation.bat` as a dedicated one-click installer for floor computers that only consume workbooks from the shared Temp Delivery Lists folder.
- Copies the maintained automation runtime into `C:\DeliveryListAutomation\Scripts`, fixing the missing `Install-DeliveryListSqlAutomationTasks.ps1` failure without requiring A+W SQL access.
- Preserves any existing installed automation configuration and runtime scripts in a timestamped `C:\DeliveryListAutomation\Backups\v132-floor-folder-import-*` folder before replacement.
- Forces `folder-import-only` mode, sets the incremental interval to 60 minutes, keeps the broader daily full-window safety refresh, and records the floor-specific audit user.
- Creates `Run-Incremental.cmd`, `Run-Full.cmd`, `Run-Now.cmd`, and `Show-Status.cmd` in the maintained working root.
- Updated Task Scheduler preflight so floor mode verifies shared-folder read access and scanner compatibility without querying A+W SQL or requiring workbook write permission.
- Kept the existing SQL connectivity, workbook generation, destination-write, and scanner preflight unchanged for authorized central SQL modes.
- Disables the older built-in 5 PM importer for the current floor Windows user to prevent overlapping duplicate imports.
- Added `docs/FLOOR_FOLDER_IMPORT_AUTOMATION.md` with setup, verification, task names, runtime paths, backup behavior, and troubleshooting guidance.
- Preserved the production scanner database, scan history, quantities, racks, bays, Rush/Remake state, import history, and per-user review data.
- Advanced browser asset cache keys to v132.

## v0.131 - Audited Route-Consolidation Preservation Validation

- Fixed floor database transfer validation stopping after a successful migration because `line_items` decreased from 15,096 to 15,068.
- Recognizes the maintained startup repair that merges obsolete duplicate receiving-stage route copies into one current destination row.
- Allows a lower raw `line_items` count only when every removed row is a receiving-stage row and has an explicit `merge_line_item_reference` audit record.
- Verifies an equivalent logical line item still exists for the same delivery date and barcode/source identity.
- Verifies the retained row has at least the same required quantity and scanned progress as every consolidated row.
- Continues to reject any missing Staging or Outbound row, unaudited deletion, missing logical item, reduced quantity, reduced scan progress, missing table, integrity error, or foreign-key violation.
- Records the number of safely consolidated rows and the semantic validation result in `transfer-report.json`.
- Preserves verified backups, failed-copy retention, and automatic restoration of the previous current-project database on any real validation failure.
- Advanced browser asset cache keys to v131.

## v0.130 - Complete Legacy v096 Schema Before Migration

- Fixed floor database upgrades reaching the current schema version and then failing during startup with `no such table: system_metadata`.
- Replays the canonical v096 schema creation method before migration 002 whenever the database has not yet reached v097.
- Uses the existing idempotent `CREATE TABLE IF NOT EXISTS` and missing-column helpers, so support tables and fields are added without recreating or replacing existing operational rows.
- Covers both unversioned legacy databases and databases that already contain a v096 baseline record but were created before all v096 support tables existed.
- Does not change any historical migration checksum or schema version.
- Preserves verified source/target backups, integrity checks, foreign-key validation, row-count checks, failed-copy preservation, and automatic target rollback.
- Corrected maintained release documentation that had remained labeled v128 after the v129 migration patch.
- Advanced browser asset cache keys to v130.

## v0.129 - Late-v096 Column Compatibility Repair

- Fixed the v097 migration failing with `no such column: priority_delivery_date` on older floor databases.
- Runs the maintained v096 compatibility preparation before migration 002 so `source_route`, `priority_delivery_date`, and `priority_direct_to_truck` exist before `line_items` is rebuilt.
- Supports both unversioned legacy databases and databases already marked with the v096 baseline.
- Preserved migration checksums, existing operational data, verified backups, validation, and rollback behavior.

## v0.128 - Windows Project-Root Quoting Fix

- Fixed the floor database transfer failing before the source prompt with a malformed current-project value ending in `" --interactive`.
- Normalizes the BAT project root to a full path without a trailing backslash before passing it as a quoted Python argument.
- Updated all launcher-relative paths to insert their own directory separator instead of depending on the trailing separator from `%~dp0`.
- Added a defensive Python compatibility repair for the exact malformed argument generated by already-extracted v127 launchers.
- Added regression coverage for the Windows quoting failure while preserving interactive path entry, verified backups, migrations, validation, and rollback behavior.

## v0.127 - Reliable Floor Database Transfer Launcher

- Moved the old-project/database path prompt from the BAT command parser into the Python transfer tool so pasted paths containing spaces, ampersands, parentheses, quotes, and other CMD-sensitive characters cannot terminate the launcher.
- Rebuilt the BAT as explicit non-nested execution labels for the project virtual environment, bundled Python, Windows Python launcher, and PATH Python fallback.
- Kept the transfer window open after success and every handled failure with a final keypress prompt.
- Added `logs\floor-database-transfer-launch.log` with the project root, selected Python runtime, and transfer-process exit code.
- Preserved drag-and-drop support through an environment handoff without embedding the pasted path in the Python command line.
- Added an interactive-path regression test using a folder name containing an ampersand while preserving the v126 backup, migration, validation, and rollback protections.

## v0.126 - Floor Database Transfer and Upgrade

- Added `Transfer-Floor-Database-To-Current-Version.bat` for moving an existing floor SQLite database into the newest scanner project while preserving operational data.
- Accepts the old project folder, old data folder, or direct `delivery-scanner-pilot.db` path, including drag-and-drop onto the BAT file.
- Uses SQLite's online backup API instead of raw file copying so committed WAL data is included safely.
- Creates verified backups of both the selected old floor database and the database already present in the current project.
- Replaces the current project's database with a verified snapshot of the old floor data, then invokes the current `delivery_store.py` initialization and numbered migrations.
- Validates SQLite integrity, foreign keys, expected schema version, required scanner tables, and before/after row counts for every pre-existing application table.
- Writes a detailed JSON transfer report under `data\backups\floor-database-transfer-<timestamp>`.
- Preserves a failed upgraded copy when possible and automatically restores the prior current-project database if migration or validation fails.
- Refuses unsupported Azure SQL targets, same-file source/target selections, incomplete pre-v096 schemas, damaged databases, and open target files rather than risking silent data loss.
- Added `docs/FLOOR_DATABASE_TRANSFER.md` and targeted success, rollback, and invalid-source tests.
- Advanced browser asset cache keys to v126.

## v0.125 - Safe Task Scheduler Native Command Handling

- Fixed schedule installation failing when `schtasks.exe /Delete` reported that an obsolete legacy task did not exist.
- Added one maintained Task Scheduler command wrapper that captures native stdout/stderr without allowing Windows PowerShell's `ErrorActionPreference = Stop` to convert expected `schtasks.exe` messages into terminating `NativeCommandError` records.
- Queries each obsolete task before attempting deletion, so a missing legacy task is treated as normal and schedule installation continues.
- Routes task deletion, creation, post-create verification, and the final launch test through the same exit-code-based command wrapper.
- Preserves detailed native command output when an actual task creation, verification, deletion, or launch error occurs.
- Added `Apply-v125-AutomationPatch.bat`, which backs up and replaces only the installed SQL task installer without touching configuration, scanner data, existing tasks, or generated workbooks.
- Kept the v123-v124 SQL/export/import verification, parser checks, timestamp fixes, and legacy-script compatibility repairs intact.
- Advanced browser asset cache keys to v125.

## v0.124 - Legacy Scheduler Parser Hotfix

- Fixed the remaining schedule-installation failure coming from the older `Install-DeliveryListAutomationTasks.ps1` file left in the shared installed automation Scripts folder.
- Delimited `${incrementalTask}:` and `${fullTask}:` in the legacy Crystal task installer so the file is valid Windows PowerShell.
- Narrowed the maintained SQL scheduler preflight from every `.ps1` file in the shared folder to the six current SQL automation entry points actually used for initialization, runs, installation, removal, status, and verification.
- Prevented retired or unrelated upgrade scripts from blocking installation of the current SQL scheduled tasks.
- Added `Apply-v124-AutomationPatch.bat`, which backs up and replaces both affected installed scheduler scripts without changing configuration, tasks, scanner data, or generated workbooks.
- Kept the v123 end-to-end SQL/export/import verifier and unchanged-list timestamp fixes intact.
- Advanced browser asset cache keys to v124.

## v0.123 - Schedule Installer Fix, Timestamp Persistence, and End-to-End Verification

- Fixed the PowerShell parser failure in `Install-DeliveryListSqlAutomationTasks.ps1` by delimiting task-name variables before literal colons.
- Added a complete PowerShell syntax scan across the installed automation scripts before Windows scheduled tasks are created.
- Runs the existing SQL connectivity, workbook builder, destination-write, and scanner compatibility preflight before schedule installation.
- Verifies that both scheduled tasks remain queryable after creation before reporting installation success.
- Added `Apply-v123-AutomationPatch.bat`, which backs up and replaces only the affected installed runtime scripts without touching the automation configuration, scanner database, or delivery-list data.
- Added `Verify-SQL-And-Import.cmd` and maintained PowerShell/Python helpers for a real one-date end-to-end test on the authorized workstation.
- The verification forces the maintained folder importer for the selected date after a fresh read-only SQL query and validated workbook export, then requires a successful normalized result and every expected stage list in the configured scanner store.
- Preserved newest-run No Changes timestamps when the Admin summary refreshes by merging database-backed history into the current automation snapshot instead of replacing it.
- Fixed unchanged delivery dates reverting to `Updated at: --` after the latest-run event had already supplied a valid completion timestamp.
- Added explicit CSS maintenance rules requiring existing selectors, shared components, and design tokens to be reused before new declarations or override layers are introduced.
- Advanced browser asset cache keys to v123.

## v0.122 - CSS Ownership Map and No-Change Import Timestamps

- Reorganized `styles.css` with a maintained table of contents and clearly labeled sections for global tokens, authentication, shell/header/sidebar, Home, Admin, Scan, shared components, Racks, Bay Map, compatibility layers, and current-release ownership.
- Preserved CSS source order so historical compatibility layers keep the same cascade and visual behavior.
- Removed eight verified exact duplicate qualified rules while leaving similar selectors with different values untouched.
- Fixed Delivery List Management result hydration so date-level **No Changes** results inherit every active stage for that delivery date instead of being filtered out for having no changed-stage rows.
- Carries the completed manual or automatic import timestamp into every hydrated stage row, keeping each Delivery List Management date group current even when the maintained importer performs no database rewrite.
- Reviewed the v106-v121 automation architecture, append-only import reconciliation, notification/review flow, and mirrored runtime/package assets.
- Corrected stale README references from the superseded Crystal export folder to the maintained `automation/sql_delivery_export` control center and setup entry point.
- Advanced browser asset cache keys to v122.
- Confirmed the root and `automation/sql_delivery_export` automation assets are intentional deployment mirrors rather than competing runtime implementations.

## v0.121 - Notification Timing and Review Reliability

- Moved the delivery-list import toast to the bottom center of the page and extended it to 20 seconds.
- Opening the bell notification menu now marks all currently displayed notifications read for that user.
- Removed the Mark all read control and the per-item Mark read wording from the notification menu.
- Stamps every delivery-list result from the newest run with the run completion time, including No Changes results and their stage details.
- Sends the exact reviewed notice IDs when Mark reviewed is selected and verifies that no unseen notices remain.
- Reloads the selected delivery list from the authenticated API after review and immediately removes New Line / Updated Line labels from the current user's visible rows.
- Preserved per-user isolation, current/future-date limits, append-only scan history, scanning quantities, racks, bays, and import audit history.
## v0.120 - Per-User Delivery-List Update Review

- Removed SQL delivery-list automation notices from the Rush/priority popup queue.
- Added a compact, nonblocking toast that appears for only a few seconds after a new automation result arrives.
- Made bell notification clicks open Admin Delivery List Management and render that notification's complete New/Updated/No Changes/Failed import result.
- Added numbered SQLite migration 003 with backup protection for per-user line-update notices and review receipts.
- Tracks new and updated lines independently for each signed-in user on today and future delivery dates only.
- Keeps unseen changes through repeated no-change imports and clears them only when that user explicitly chooses Mark reviewed for the selected list.
- Reapplies New Line and Updated Line labels per user when list data is read, so one user's review never clears another user's notices.
- Added an unobtrusive Scan-page review banner that requires Review updates before Mark reviewed is enabled, plus unseen counts in stage selectors.
- Excludes removed or retired rows from the New/Updated review queue while preserving their immutable operational history.
- Preserved append-only scan history, existing scan quantities, racks, bays, Rush/Remake state, import history, schedules, and the authoritative latest-import result.
## v0.118 - Unified Import Center and Append-Only History-Safe Updates

- Moved Import Audit History into the Import / Update Delivery List control center as a fourth tab.
- Removed the separate Import history button and standalone history modal from Delivery List Management.
- Preserved history search, status/date filters, 20/50/100 row paging, newest-first ordering, manual refresh, and collapsed entries.
- Kept history user-driven: it loads when the History tab opens and does not reset the user's scroll position during automatic updates.
- Reduced the notification bell and inherited the same header utility-button styling used by the language, refresh, and fullscreen controls.
- Fixed `scan_events is append-only` import failures with an isolated SQLite reconciliation layer that updates matched line items in place instead of deleting and recreating their identities.
- Preserved scan-event links, scan quantities, rack assignments, bay assignments, Rush/Remake state, and active list metadata during imports.
- Inserts genuinely new source lines, safely retires source-removed history-linked lines, and deletes only unreferenced removed lines.
- Leaves non-SQLite/Azure SQL stores on their native import implementation.
- Preserved live Delivery List Management rerendering, browser catalog sync, detailed logs, schedules, notifications, and workbook integrity validation.
## v0.117 - Live Delivery Management Refresh and Stable Import History

- Fixed Delivery List Management so the original scanner overview rerenders immediately when the live delivery-list catalog changes.
- Preserved the current page, selected date, selected stage, and active scan workflow; no synthetic selector change events are fired.
- Removed the 15-second Import Audit History auto-refresh that reset scroll position and expanded/collapsed state.
- Import Audit History now refreshes only on open, manual refresh, search/filter/page controls, and a safe hidden synchronization after close.
- All Import Audit History entries now start collapsed.
- Marks the Refresh button when new results arrive while the history window is open instead of replacing the current view.
- Added exact failed-workbook names, dates, and error messages to the command log.
- Preserves the complete normalized failed-import result at `C:\DeliveryListAutomation\State\last-import-result.json`.
- Added repair guidance for damaged XLSX/XLSM files that require Query SQL, Export & Import on a SQL-authorized computer.
- Preserved dedicated history search/pagination, notifications, schedules, scan quantities, route logic, rack and bay assignments, and database-busy retry behavior.
## v0.116 - Dedicated Import Audit History

- Restored the original Delivery List Management overview instead of replacing it with recent import results.
- Added a separate Import History button and full-screen modal on the Admin page.
- Shows the newest imports first with 20 results per page by default.
- Added selectable page sizes of 20, 50, and 100 results.
- Added search across delivery date, workbook filename, stage/list, user, classification, and error text.
- Added status filters for New, Updated, New + Updated, No Changes, and Failed.
- Added delivery-date range filters, result totals, page numbers, Previous/Next controls, and manual refresh.
- Preserved stage-level audit detail including new/restored stages, added pieces, updated pieces, changed pieces, and changed lines.
- Removed the obsolete inline Temp Delivery Lists folder and date-settings disclosure from Delivery List Management because those settings now live in the Automation Control Center.
- Kept non-disruptive 10-second catalog synchronization so new dates and stages appear without refreshing or navigating users away from their current page.
- Preserved scan quantities, route logic, rack and bay assignments, notifications, automation settings, and scheduled tasks.
## v0.115 - Non-Disruptive Live Delivery-List Synchronization

- Fixed the Admin page immediately redirecting to Scan when the v114 import-history refresh ran.
- Removed artificial Date and Stage change events from background catalog refreshes.
- Replaced the installed v114 bridge during upgrade so the redirecting code is not left behind.
- Added a silent delivery-list catalog refresh every 10 seconds for every signed-in browser and immediately after import completion.
- New dates and stages now appear without a browser reload while preserving the current page, selection, and active scanner input.
- Kept Recent Delivery List Imports connected to the latest maintained importer result and its New, Updated, New + Updated, No Changes, Failed, restored-stage, and piece-change details.
- Added bounded retry and backoff for transient SQLite/Azure SQL lock or busy conditions so active scanner writes are favored.
- Confirmed that SQL querying, workbook generation, validation, and network publishing do not write to the scanner database; only the final maintained import phase uses short transactions.
- Preserved scan quantities, routes, racks, bays, audit history, notifications, configuration, and scheduled tasks.
## v0.114 - Immediate Import History Refresh and Correct New-Stage Classification

- Fixed the automation refreshing the hidden legacy import-history element instead of the visible Recent Delivery List Imports section.
- Made the just-completed maintained folder-import result authoritative for New, Updated, New + Updated, No Changes, and Failed labels.
- Added per-stage result rows with added-piece, updated-piece, changed-piece, and changed-line details.
- Preserved stage summaries, reactivated counts, and restored-stage IDs through the import wrapper, run summary, recent-import API, and browser renderer.
- Added a browser-state bridge that refreshes delivery-list state and the Scan page date/stage selectors without a page reload.
- Fixed inactive or deleted stages being restored successfully but classified as No Changes; restored stages are now New.
- Prevented older imports-table rows for the same workbook/date from overwriting the latest run result.
- Retained Excel-compatible workbooks, integrity validation, missing-list recovery, complete logs, notifications, and UNC publishing.
- Preserved scans, routes, racks, bays, audits, configuration, and scheduled tasks.
## v0.113 - Workbook Integrity, Import Audit, and Deleted-List Recovery

- Fixed SQL-generated workbooks prompting Excel to repair the file and then opening without worksheet data.
- Moved worksheet properties into the SpreadsheetML order required by Microsoft Excel and added full OOXML ZIP, XML, relationship, style-count, and worksheet-order validation.
- Changed order, item, and quantity cells to native numeric cells while preserving the scanner-compatible A/F/G/J/L/N/V/X layout.
- Added a workbook format marker and published-file SHA-256 hash to each date state. Older, damaged, replaced, or repaired files are rebuilt automatically even when A+W data is unchanged.
- Changed SQL export-and-import mode to audit every source date while importing only changed, pending, or missing-list dates, allowing current No Changes results to appear without unnecessary reimports.
- Added a visible `Last checked` timestamp to Recent Delivery List Imports so a successful no-change automation run is distinguishable from a stale page.
- Preserved authoritative New, Updated, and New + Updated classifications from the scanner imports table while retaining newer No Changes and Failed runtime results.
- Added deleted-stage recovery: when one or more expected scanner lists are missing, the wrapper routes that exact date through the maintained `import_delivery_folder` business workflow without direct table edits.
- Preserved scan quantities, route/stage rules, rack and bay behavior, notifications, live logs, UNC publishing, and existing automation settings.
## v0.112 - Successful No-Change Automation Runs

- Fixed unchanged SQL checks failing with `Cannot bind argument to parameter 'Dates' because it is an empty array.`
- Changed scanner-import date binding to safely accept an empty collection as a defensive fallback.
- Added an explicit pre-import guard so SQL export-and-import mode skips the scanner importer when no changed or pending workbooks exist.
- Added a clear `No changed or pending delivery-list workbooks require scanner import.` log line.
- No-change runs now complete successfully and publish the normal no-change notification instead of a failure notification.
- Preserved changed-workbook imports, pending-import retries, authoritative Recent Delivery List Imports history, complete live logs, UNC publishing, and all scanner data.
## v0.111 - Import Completion and Live Log Performance Fix

- Fixed the Status & Logs page appearing frozen after the scanner database import had already completed.
- Stopped printing the complete per-file import result JSON to PowerShell stdout; the full normalized result remains stored for Recent Delivery List Imports.
- Changed importer console output to one concise summary line with counts, imported dates, failed dates, and the private result-file path.
- Throttled live-status persistence so the complete growing command log is not rewritten to disk after every individual output line.
- Limited normalized import results to the delivery-date window requested by the automation run so unrelated files cannot be marked imported or flood the status output.
- Added a clear transition log after the scanner importer returns and before its normalized result is processed.
- Preserved v110 UNC/SMB publishing, complete per-run logs, notification reliability, and v109 accurate New/Updated/No Changes/Failed history.
- Preserved all scanner workflows, scan quantities, rack/bay assignments, routes, audio, notification history, and the production database.
## v0.110 - Live Automation Logs and Network Share Publishing Fix

- Fixed SQL workbook publishing to the shared Temp Delivery Lists UNC folder by avoiding `System.IO.File.Replace` on SMB/network paths, which caused `The path is not of a legal form.`
- Added a network-share-compatible validated overwrite path while retaining atomic replacement for supported local filesystems.
- Changed automation logging to one complete log file per run so manual and scheduled results are not mixed together.
- Rebuilt the **Status & Logs** page to stream the active command output while the automation runs instead of showing only the final 40 lines.
- Added full-log line counts, the exact log-file path, automatic follow-to-latest behavior, and a **Copy Full Log** button for troubleshooting.
- Updated scheduled-run status loading so the complete saved run log remains available after the browser or web app restarts.
- Changed app-notification publishing to use a temporary JSON request file, avoiding Windows command-line quoting and payload-length failures.
- Added clearer progress messages for workbook building, validation, destination staging, overwrite/create actions, scanner importing, and notification publishing.
- Preserved v109 authoritative **Recent Delivery List Imports** classification and retry behavior for New, Updated, New + Updated, No Changes, and Failed files.
- Preserved all scanner workflows, scan quantities, rack/bay assignments, routes, audio, notification history, and the production database.
## v0.109 - Accurate Automated Import History

- Connected automated SQL/folder imports to the scanner's authoritative `imports` table instead of relying on an isolated automation status summary.
- Updated the Admin **Recent Delivery List Imports** section immediately after manual or scheduled automation completes.
- Added accurate result labels for **New**, **Updated**, **New + Updated**, **No Changes**, and **Failed** imports.
- Corrected the importer wrapper to read `importedFiles`, `updatedFiles`, `skippedFiles`, and `failedFiles` from the maintained folder importer.
- Stopped requested dates from being marked imported unless the maintained scanner importer actually processed them successfully.
- Preserved pending dates when a file fails or is not processed so a later run can retry it.
- Merged authoritative `last-run.json` results into the web control center so completed runs retain import counts and date details.
- Added a protected recent-import API endpoint and automatic Admin history refresh after automation notifications.
- Preserved the v108 Control Center, notification bell, scanner workflows, scan quantities, rack/bay assignments, routes, audio, and production database.
## v0.107 - Delivery List Automation Control Center

- Changed **Import / Update Delivery List** into a GUI control center instead of immediately running the folder importer.
- Added three safe manual commands: **Import Temp Folder Only**, **Query SQL & Export Only**, and **Query SQL, Export & Import**.
- Added one-date, custom-range, normal incremental-window, and full-refresh-window controls.
- Added configurable automatic modes so temporary floor installations can use folder-only importing while the authorized central installation can query A+W SQL.
- Added GUI controls for interval, past/future date windows, daily full refresh time, destination folder, popup notifications, task installation, and task removal.
- Reused the existing scanner notification queue for success, no-change, and failure popups.
- Added a server-side allowlisted control module; the browser never receives SQL credentials and cannot execute arbitrary commands.
- Preserved all v105 Old Bay, Bay Scanner, audio, database, route, rack, and scanning behavior.
# README Changelog

## v0.106
- Added `automation/crystal_delivery_export`, a local Crystal Reports automation package that uses the existing SAP Crystal .NET runtime instead of a third-party report scheduler or mouse automation.
- Added automatic `DeliveryDate` parameter injection for `DeliveryList.rpt`, SQL Server login application for report and subreport tables, and XLSX export through `ExportFormatType.ExcelWorkbook`.
- Added Windows DPAPI credential storage so the A+W SQL password is entered only on the local workstation and is never stored in the repository or plain-text task commands.
- Added automatic Crystal runtime discovery, 64-bit/32-bit Windows PowerShell testing, one-date validation, detailed logs, status JSON, and removable Windows Task Scheduler tasks.
- Added hourly incremental refreshes for two days back through fourteen days forward and a daily 5:15 PM reconciliation for seven days back through ninety days forward; both horizons remain configurable.
- Added safe local staging, XLSX signature/size validation, SHA-256 comparison, `.partial` network publishing, overlap prevention, and no-record protection so failed or empty runs do not replace the previous valid workbook.
- Added `import_delivery_folder.py`, which reuses `scanner_config.py` and `delivery_store.py` to import or update the scanner immediately after each automated export run without duplicating import rules.
- Added static tests for the automation file set, known A+W report/database paths, secure credential workflow, safe publishing behavior, and reuse of the maintained scanner business layer.
- Updated the maintained release summary and project documentation links to v106 without changing the v105 Bay Map interface or the v097 database migration contract.

## v0.105
- Completely rebuilt the Old Bay Review modal as an Old Bay Control Center with a stronger header, compact operational summary, local search, age filters, sorting, and a dedicated printable-investigation action.
- Added clear old-bay age severity treatments, bay and order/item identity, concise job/size/delivery/last-scan details, and a cleaner per-row snooze control.
- Added explicit row selection, Select Visible/Clear Visible behavior, a live selected count, and safe bulk snoozing that affects only checked rows instead of silently snoozing every old-bay assignment.
- Preserved individual snoozing, empty-state handling, daily automatic alert behavior, print support, and backend stale-bay APIs.
- Completely reorganized the Bay Map scanning panel into a polished three-step workflow: choose Add/Remove, confirm the target bay, then scan the piece.
- Added live mode and target guidance, a larger primary scan surface, an explicit Submit Scan button, and nearby Undo/Redo correction tools.
- Moved Manual Entry into an accessible disclosure so the primary barcode workflow stays concise while order/item entry remains fully available.
- Reworked Bay Scan History with a clearer latest-location card, readable status treatment, retained location correction, All Scans access, and a collapsible recent-scan table.
- Preserved Indian Trail route progress, in-transit manifest access, barcode scans, selected-bay targeting, manual scans, undo/redo, recent history, and location changes.
- Consolidated the latest Old Bay and Bay Scanner CSS ownership blocks instead of adding another duplicate override layer.
- Added Spanish translations for the new Old Bay and Bay Scanner labels and advanced browser/sound cache keys to v105.

## v0.104
- Reduced the normal-stage timed scan popup from a wide three-card layout to one concise result card with a compact header, readable order/item identity, customer, quantity, dimensions, glass/job, route, location, and optional rack correction.
- Raised popup rack/bay custom-select menus above the timed card so expanded dropdowns no longer render behind it.
- Kept the popup countdown paused for the complete dropdown interaction and while a rack correction request is being saved, even when the select temporarily loses focus or becomes disabled.
- Removed the page-navigation sound entirely while retaining the restrained normal accepted-scan confirmation.
- Added `rack_barcode.wav` as the dedicated accepted rack-barcode cue instead of reusing the print sound.
- Added `rack_outbound.wav`, a rising airy departure swoosh and success chime, for racks successfully released from Outbound and marked on the way.
- Moved `print_ready.wav` to actual print completion: opening a print preview is silent, and the cue plays only after the browser reports the print workflow completed.
- Added `destructive_action.wav`, a restrained downward wipe-and-settle confirmation for successful rack/bay clears, scan resets, Rush/Remake clears, list/date/item/user/rack/bay deletions, and maintained rule/contact removals.
- Stabilized Rush and Remake filter button geometry by reserving the indicator space in clear, alert, selected, and unselected states.
- Reworked active Scan filter pills with compact category-specific status, attention, route, and glass treatments plus clearer remove controls.
- Updated the audio manifest, audio guide, browser preview, README release summary, and browser/sound cache keys to v104.

## v0.103
- Reconciled the checked-in v102 browser/sound-cache baseline with the maintained release metadata and advanced the edited package to v103; missing historical v101/v102 changelog entries were not reconstructed or guessed.
- Added a distinct accepted-rack-barcode cue by mapping `RACK...` scans to the existing `print_ready.wav` identity instead of the normal item-scan sound.
- Changed normal accepted item scans to use the former page-navigation/notification cue and retained `sounds/scan_success.wav` in the pack without mapping it, leaving it available for a future purpose.
- Rebuilt `collapse_open.wav` and `collapse_close.wav` as shorter, quieter, wind-like swooshes for Scan-page and Bay Map expand/collapse actions.
- Redesigned the timed normal-stage scan result popup with a clearer status header, prominent order/item identity, customer information, piece details, workflow/location details, and a cleaner Admin/Supervisor rack correction control.
- Paused the scan-result countdown while the pointer is over the popup, while any popup control has focus, and while the native rack dropdown is open or being used.
- Redesigned the Scan filter drawer with clearer filter-group explanations, more readable sections, polished active-state controls, and a visible click-outside-to-close instruction.
- Added click-outside closing for the Scan and Bay Map filter drawers.
- Added true multi-select glass-type filtering, including one removable active-filter chip for each selected glass type.
- Updated global search so a selected line item opens the delivery-list stage containing its latest accepted scan; items without an accepted scan open at Staging.
- Kept the Scan-page delivery-list search text when switching stages on the same delivery date and cleared it only when the delivery date changes.
- Updated `sounds/audio_manifest.json`, the audio-pack guide and browser preview, the README release summary, and browser/sound cache keys for v103.

## v0.100
- Restored the v098 operational and interface sound set for login/logout, saves, email, navigation, undo/redo, imports, racks, bays, permissions, notifications, and machine events; printing remains intentionally silent.
- Unlocks Web Audio during the first pointer or keyboard gesture so asynchronous actions no longer lose browser audio permission.
- Plays an immediate synthesized cue on first use while each distinct packaged WAV loads in the background for later actions, preventing delayed sounds from arriving after the related operation.
- Rebuilt Scan Success as a bright five-note rising major chord with a stable low confirmation tone and high finishing sparkle.
- Reset the sound-volume storage key to restore a 100% default for operators whose earlier test setting may have remained muted.
- Added server-backed Manual Delivery List Edit pagination with 20 rows per request, accurate total counts, and offset-based Load More behavior.
- Made manual-edit rows collapsed by default while keeping Order, Item, Job Nr., customer, stage, and quantity visible in each summary ribbon.
- Added predictive 180 ms search for every typed Order or Job Nr. character and retained unsaved-edit confirmation before replacing displayed rows.
- Lowered the Scan filter drawer below the expanded sidebar stacking layer.
- Advanced browser cache keys to v100.

## v0.099
- Restored Scan-page responsiveness by removing the 300 ms whole-document custom-select polling loop and relying on the existing mutation/change synchronization.
- Stopped rendering both desktop rows and mobile cards during every Scan-page refresh; only the active viewport layout is now built.
- Coalesced search and filter paints with `requestAnimationFrame` and avoided rebuilding unchanged glass-type controls.
- Changed Manual Delivery List Edit saves to update the affected in-memory list and row in place instead of reloading the complete delivery-list catalog and modal.
- Replaced delayed WAV fetch/decode playback with short immediate synthesized operational cues.
- Limited sounds to scans, important completion events, bay assignment/removal, and machine faults; navigation, login/logout, save, print, email, undo/redo, and routine button actions are silent.
- Added one timed, nonblocking scan-result card for normal stages with success, notice, and error treatments plus the same item details shown by Last Scan.
- Added Admin/Supervisor rack or truck correction to successful staging scan cards while retaining existing backend permissions.
- Replaced the wide Scan-page filter rows with one organized multi-filter drawer, removable active-filter chips, and a combined remake/Rush attention marker.
- Added a Windows local-time fallback for the daily importer when the optional IANA timezone package is unavailable.
- Advanced browser cache keys to v099.

## v0.098
- Added the complete Barefoot Delivery Scanner Audio Language with 27 distinct mastered mono WAV cues.
- Replaced the four generic operational files with semantic cues for success, duplicate, warning, error, Rush, remake, completion, racks, bays, undo/redo, import, save, print, email, authentication, notifications, permissions, and future machine events.
- Updated the shared Web Audio loader to resolve semantic cue names, cache decoded buffers, retain the shared compressor/volume chain, and fall back safely when a WAV cannot load.
- Added context-aware scan selection so Rush and remake pieces have recognizable success sounds, duplicate scans differ from warnings, and rack/bay workflows use their own audio identities.
- Added audio feedback for rack completion/reopen/return, bay assign/remove/move, undo/redo, import start/complete, settings saves, print preview, sent email, sign-in/sign-out, notifications, and permission denial.
- Added `sounds/audio_manifest.json`, `sounds/README_AUDIO_PACK.md`, and `sounds/preview_audio_pack.html` for maintenance and browser-based auditioning.
- Preserved the v097 numbered SQLite migrations, database safeguards, and Azure SQL preparation without changing migration 001 or 002.
- Advanced browser and sound cache keys to v098.
- Packaged the release as `Delivery_List_Scanner_v098.zip` without live databases, WAL/SHM files, logs, caches, or verification artifacts.

## v0.097
- Added numbered, checksummed SQLite migrations with automatic legacy v096 baselining.
- Added verified pre-upgrade backups using SQLite's online backup API; failed upgrades preserve the backup and never recreate production data.
- Centralized the canonical logical database contract and documented SQLite-to-SQL Server type mappings.
- Added quantity, boolean, relationship, JSON, timestamp, and migration-history integrity validation.
- Added UTC audit and soft-delete fields to core mutable entities.
- Made scan, audit, and machine event histories append-only in SQLite and Azure SQL.
- Added production-ready machines, scanners, and machine-events tables without changing the UI.
- Added query-driven parity indexes and documented their purpose.
- Added explicit SQLite optimize, WAL checkpoint, and backup-before-VACUUM maintenance commands.
- Rebuilt the SQLite-to-Azure utility with preflight checks, dry-run-by-default behavior, transactional copy, reports, row-count checks, and deterministic checksums.
- Prevented production demo delivery-list seeding while preserving idempotent configuration seeds.
- Added database migration, preservation, integrity, and Azure contract tests.
- Matched the sign-in logo frame to the expanded desktop sidebar logo and removed the oversized login-only glow.
- Added the first editable four-cue WAV implementation used as the foundation for v098.

## v0.096
- Matched the sign-in page logo to the expanded desktop sidebar logo.
- Reduced the sign-in logo frame from 188 x 188 to 108 x 108.
- Kept the sign-in logo square, proportional, and filled with the same sampled dark-blue background color used by the expanded sidebar logo.
- Kept collapsed-sidebar and mobile-logo sizes unchanged.
- Advanced browser cache keys to v096.

## v0.095
- Reduced only the expanded desktop sidebar logo and its outline by 10%, from 120 x 120 to 108 x 108.
- Kept the collapsed sidebar logo and mobile logo sizes unchanged.
- Matched the inside of every logo outline to the logo image's sampled dark-blue background color: RGB 4, 43, 84.
- Preserved the square frame, proportional image rendering, and existing sidebar alignment.
- Advanced browser cache keys to v095.

## v0.094
- Corrected the combined Barefoot and Builders FirstSource logo frames so every displayed version is a true square.
- Set the sign-in logo frame to 188 x 188.
- Kept the collapsed sidebar logo frame at 48 x 48.
- Set the expanded desktop sidebar logo frame to 120 x 120.
- Set the mobile sidebar logo frame to 158 x 158.
- Kept `object-fit: contain` so the supplied logo remains proportional inside each square frame.
- Advanced browser cache keys to v094.

## v0.093
- Removed the `object-fit: cover` logo rule that was stretching the combined logo into the outline.
- Restored proportional `object-fit: contain` rendering for the sign-in, collapsed-sidebar, expanded-sidebar, and mobile logos.
- Kept the existing displayed logo heights while allowing each image width to follow its natural aspect ratio.
- Adjusted the subtle border, outline, and shadow to follow the actual rendered image rectangle rather than a wider forced frame.
- Preserved the v092 sound volume controls and scan-sound behavior unchanged.
- Advanced browser cache keys to v093.

## v0.092
- Tight-cropped the supplied combined Barefoot + Builders FirstSource logo so the rounded frame hugs the visible branding instead of surrounding large internal margins.
- Kept the rounded corners, subtle outline, and soft shadow for collapsed, expanded, mobile, and sign-in logo presentations.
- Added a persistent scanner-sound volume slider to the temporary Scan and Bay Map sound-test panels.
- Added a 0-400% floor-volume range with a 200% default for louder production-floor feedback.
- Added a shared Web Audio master-gain and compressor chain so success, notice, error, and 100% completion sounds all follow one volume setting.
- Synchronized every visible volume slider and stored the selected setting in browser local storage.
- Advanced browser cache keys to v092.

## v0.091
- Added rounded corners to the supplied Barefoot + Builders FirstSource logo in the sign-in screen and sidebar.
- Added a subtle light outline and soft shadow so the logo stands out slightly against the dark navigation background.
- Replaced the collapsed Barefoot-only sidebar image with the same combined Barefoot + Builders FirstSource logo used in the expanded sidebar.
- Kept the existing collapsed/expanded dimensions and sidebar navigation alignment unchanged.
- Advanced browser cache keys to v091.

## v0.090
- Replaced the existing combined Barefoot and Builders FirstSource brand image with the newly supplied logo.
- Kept the existing webapp asset filename so the sign-in screen, expanded desktop sidebar, and mobile drawer all use the new logo without duplicating brand logic.
- Preserved the collapsed sidebar's compact Barefoot icon so navigation remains readable at rail width.
- Advanced browser cache keys to v090.

## v0.089
- Combined the existing Barefoot & Company logo with the attached Builders FirstSource logo in a new stacked brand asset.
- Preserved the supplied Builders FirstSource red side lines, red square/white 1 mark, and dark blue text.
- Added `barefoot-builders-firstsource-logo.png` as the maintained combined logo asset.
- Updated the sign-in panel to use the combined Barefoot and Builders FirstSource logo.
- Updated the expanded desktop sidebar to crossfade from the compact Barefoot-only mark to the combined logo without changing the fixed sidebar brand-row height or moving the page selectors.
- Updated the mobile navigation drawer to use the combined logo.
- Kept the collapsed desktop sidebar on the smaller Barefoot-only mark because the Builders FirstSource text is not readable at icon size.
- Advanced browser cache keys to v089.

## v0.088
- Increased the normal Scan-page Recent Scans history from one row to two rows while retaining five rows in fullscreen.
- Restyled the global search input as a defined rectangular box with rounded corners, a visible border, and a subtle shadow while keeping the outer search wrapper removed.
- Added one shared Web Audio sound engine with synthesized cues so the project does not require packaged sound files.
- Added a bright ascending success cue for accepted scans.
- Added a distinct lower error cue for blocked or failed scans.
- Added a separate notice cue for duplicate, override, and other non-error scan outcomes.
- Added a fun completion arpeggio when the Scan-page stage progress transitions to 100%.
- Added the same completion cue when the Indian Trail Bay Map / In-Transit route progress transitions to fully Outbound and fully Received.
- Prevented initial loading of an already completed list from falsely triggering the completion sound by tracking progress per active list.
- Added temporary shared sound-test controls to the Scan and Bay Map scanner panels, plus an In-Transit 100% test button. These controls are intentionally marked for later removal after floor approval.
- Added static and browser-rendered tests for the two-row history, rounded search field, sound engine, completion wiring, and temporary test controls.
- Advanced browser cache keys to v088.

## v0.087
- Increased the expanded desktop sidebar logo by approximately 25%, from 74 x 74 to 93 x 93.
- Kept the collapsed sidebar logo at 48 x 48.
- Added `--app-sidebar-logo-expanded-size` as the single documented CSS setting for future logo-size adjustments.
- Updated both the base and final desktop ownership rules to use the shared logo-size variable, preventing later CSS overrides from using a different size.
- Preserved the fixed 126px brand section so page selector buttons and icons remain aligned between collapsed and expanded states.
- Advanced browser cache keys to v087.

## v0.086
- Reduced the expanded Barefoot sidebar logo by 65%, from 210 x 210 to 74 x 74.
- Kept the collapsed sidebar logo at 48 x 48.
- Reduced the fixed desktop sidebar brand section from 280px to 126px.
- Moved Home, Scan, Racks, Bay Map, and Admin upward in both collapsed and expanded states.
- Kept one identical fixed brand-section height in both states so every selector and icon remains vertically aligned during hover expansion.
- Advanced browser cache keys to v086.

## v0.085
- Fixed the expanded Barefoot logo being reduced by a later responsive sidebar rule.
- Added a final sidebar-specific logo ownership block so the expanded desktop logo renders up to 210 x 210.
- Kept the collapsed sidebar logo at 48 x 48.
- Made the top sidebar brand section a fixed 280px height in both collapsed and expanded states.
- Removed the hover-only brand-section height change that pushed Home, Scan, Racks, Bay Map, and Admin downward during expansion.
- Kept every page selector and icon at the same vertical position before, during, and after sidebar hover expansion.
- Added an explicit large-logo rule for the responsive mobile drawer as well.
- Advanced browser cache keys to v085.

## v0.084
- Reverted the collapsed sidebar Barefoot logo back to the smaller size so the rail stays clean when not hovered.
- Reduced the collapsed sidebar logo from 72 x 72 back to 48 x 48.
- Kept the large hover-only expanded brand presentation for the sidebar.
- Tuned the expanded sidebar logo to 210 x 210 so it fills about 75% of the expanded top brand section.
- Set the expanded sidebar top brand section height to 280px so the larger logo sits centered and proportionate.
- Advanced browser cache keys to v084.

## v0.083
- Removed the outer global-search container chrome so the centered search bar and Search button sit cleanly in the header without the larger wrapper box.
- Reduced the header global-search width from 640px to 560px for a cleaner centered layout.
- Increased the sidebar Barefoot logo by 50% in both collapsed and expanded states.
- Increased the collapsed sidebar logo size from 48 x 48 to 72 x 72.
- Increased the expanded sidebar logo size from 176 x 176 to 264 x 264.
- Added a hover-only larger sidebar logo area so the expanded logo stays centered without wasting space when collapsed.
- Advanced browser cache keys to v083.

## v0.082
- Restored the operations sidebar on the Scan page.
- Kept the sidebar collapsed by default and hover-expandable, matching Home, Racks, Bay Map, and Admin.
- Preserved the sign-in-screen behavior that hides the entire application shell until authentication succeeds.
- Retained the centered smaller global search bar and simplified Today’s Delivery Progress design from v081.
- Advanced browser cache keys to v082.
- Updated static and browser-rendered checks so the Scan page is protected as a sidebar-enabled workspace.
