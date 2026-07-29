<!-- File: README.md -->
# Delivery List Scanner

Current maintained release: **v163**. SQLite remains the active/default backend.

v163 fixes the Control Center modals being permanently visible at startup. The Admin and Operations panels now obey their native hidden state, close normally, clear stale editor content, and reopen with the requested GUI only.

## Install v163 over v162

1. Close the Delivery List Scanner server.
2. Extract `Delivery_List_Scanner_v163_Modal_Hidden_State_And_Close_Repair_Changed_Files.zip` into the current project folder and replace the included files.
3. Restart the scanner and hard-refresh the browser with `Ctrl+F5`.

No database migration or backend update is required. Existing Admin, rack, scan, automation, permission, and API behavior remains unchanged.

## v163 highlights

- Restored native hidden-state ownership for the shared Admin Control Center modal and backdrop.
- Applied the same protection to Individual Rack and Packing List History Operations modals.
- Prevented `display: grid !important` from forcing either modal visible during startup or after closing.
- Added defensive ARIA state updates, stale-content cleanup, and Operations Control Center class cleanup when windows close.
- Advanced Admin, Racks, and JavaScript cache keys to v163.

## v162 highlights

- Restored one vertically centered font system across the complete in-row Scanned pill, including label, date, time, separators, and station.
- Increased Flags, Route, Location, and Progress text to a consistent readable production-floor size.
- Corrected the missing Location width delimiter so the maintained 100% Scan-table geometry is parsed reliably.
- Made the Admin Control Center hero, context rail, and editor canvas explicit non-overlapping grid rows.
- Made the Operations/Rack Control Center hero, context rail, and editor canvas use the same protected layering.
- Increased and protected the close buttons, constrained long status pills, and restored high-contrast hero text in every touched GUI.
- Advanced the Scan, Racks, and Admin stylesheet cache keys to v162.

## v161 highlights

- Condensed in-row scan dates to month/day and times to compact lowercase forms such as `4:30pm`.
- Reserved scan-pill space only in Job Nr., keeping Order and Item vertically aligned with the remaining line-item columns.
- Added the active delivery-list date to the Scan panel title.
- Removed the generic selected color from individual rack cards so Open, Complete, On the Way, Received, and Empty formatting remains visible.
- Added Control Center headers, context rails, status pills, guided canvases, and polished content cards to Individual Rack and Packing List History windows.
- Strengthened the existing Edit Racks, Rack, and Rack Set Admin editors with matching rack-specific Control Center surfaces.

## v160 highlights

- Rebuilt the shared Admin modal header to match the Delivery Automation Control Center format.
- Added a contextual eyebrow, task-specific description, live status pill, and workspace rail to every Admin GUI.
- Added specific descriptions and context labels for delivery lists, manual editing, users, roles, sessions, stations, routes, emails, lookups, rejects, bay rules, auto-assignment, racks, and scan history.
- Standardized section cards, tables, forms, search bars, list rows, empty states, and command/footer areas.
- Preserved all IDs, event delegation, API requests, permissions, editor state, and save behavior.

v159 corrected the v158 page-polish alignment regressions, restored the main Scan panel hierarchy, extended the polished Admin design to the maintained editor windows, and added thin compatibility bridges for installed automation that still imports the pre-v151 root module names.

v158 tightens the Scan table and brings the Home, Scan, Racks, and Admin workspaces up to the same polished visual standard as Internal Rejects. The last-scan pill now ends at Item, compact operational columns use a complete 100% width contract, and the Progress column reaches the panel edge without the white strip introduced by the earlier clearance workaround.

## Install v158 over v157

1. Close the Delivery List Scanner server.
2. Extract `Delivery_List_Scanner_v158_Core_Page_Visual_Polish_And_Scan_Table_Refinement_Changed_Files.zip` into the current project folder and replace the included files.
3. Restart the scanner normally.
4. Hard-refresh the browser once with `Ctrl+F5` so the `20260729-v158` stylesheet cache keys take effect.

No database migration, backend patch, or JavaScript replacement is required. Reject management, scanning behavior, rack/bay workflows, permissions, and APIs remain unchanged.

## v158 highlights

- Limited the in-row last-scan pill to Job Nr. through Item.
- Condensed Flags, Route, and Location while preserving wrapping and selector usability.
- Rebuilt the Scan table as an exact 100% column contract and removed the right-side white strip after Progress.
- Added Rejects-quality hero headings, layered surfaces, hierarchy, spacing, borders, and interaction polish to Home, Scan, Racks, and Admin.
- Kept all existing IDs, controls, workflows, responsive behavior, and page ownership boundaries.

## v157 highlights

- Replaced the separate Last Scan ribbon with a compact in-row pill.
- Anchored the pill inside Job Nr. while allowing it to visually extend through Customer.
- Kept the pill absolutely positioned so its date, time, and station cannot affect table width.
- Preserved the plain whole-number QTY presentation.
- Renamed Item Nr. to Item and Process State to Progress.
- Increased the Progress column and reserved right-edge clearance so its full border and content stay visible.
- Preserved Internal Reject ribbon containment and every v155 width-safety rule.

## v156 highlights

- Replaced the QTY progress-style pill with a plain centered whole number.
- Removed the full scan timestamp and station from the Job Nr. cell.
- Added a compact blue Last Scan ribbon above every scanned line item.
- Displays the last scan date, time, and station in one readable contained sentence.
- Uses the same six-column ribbon span and four-column alignment tail as Internal Rejects.
- Added a reusable detail-ribbon containment contract for future warning, timing, and audit ribbons.
- Preserved the fixed percentage-based table layout and all v155 overflow protections.

## v155 highlights

- Removed Delivery Date from the Scan-page internal-reject ribbon.
- Removed the trailing event-count and investigation-note mini-cells from the ribbon.
- Increased the remaining ribbon label and value sizes while preserving the slim presentation.
- Added a fixed 100% percentage-based Scan-table column contract.
- Removed the hard 118-pixel Location-column minimum that could force the table wider than its panel.
- Contained long scan timestamps, process states, flags, location controls, badges, and future detail ribbons within their assigned columns.
- Added responsive ribbon wrapping without changing the underlying line-item or reject data.
- Preserved Admin reject editing/deletion, reject filtering, line flags, scanner behavior, and all backend APIs.

## v154 highlights

- Added Edit and Delete controls to Reject Timeline rows for users whose assigned role is exactly **Admin**.
- Added server-side Admin-role enforcement for both reject mutation endpoints.
- Edit Reject supports reason, machine/location, quantity, incident date/time, and investigation notes while keeping order, item, job, product, delivery date, and original creator locked.
- Delete Reject removes the reject record and recalculates line-item reject flags without restoring historical scans, rack quantities, bay assignments, or process state.
- Every edit and deletion writes an audit event containing the prior record and the resulting reject summary.
- Expanded line flags with the latest reject quantity, user, notes, delivery date, event count, and event ID.
- Rebuilt the Scan-page internal-reject ribbon as a slim polished strip spanning Job Nr. through Customer.
- The ribbon shows reason, machine/location, rejected quantity, rejected by, incident time, delivery date, event count, and whether investigation notes exist.
- Preserved all existing reject creation, process restart, notification, filter, and timeline behavior.

## v150 highlights

- Moved Target Bay below the Add/Remove selector with reliable spacing and aligned Clear action.
- Rebuilt Manual Scan with labels above the Order and Item fields.
- Kept Order wide, increased the Item field, enlarged Submit, and increased the section height slightly.
- Removed Route Pulse percentage labels in both Add and Remove modes.
- Replaced status words with check, warning, X, or neutral icons.
- Applied matching green, amber, red, or neutral tones to Latest Activity and Recent Bay Scan surfaces.
- Preserved one recent scan, sticky viewport fit, and all existing Bay Scanner workflows.
- No PNG previews were generated or packaged.

## v149 highlights

- Reduced Recent Bay Scans to one compact row so Add mode cannot cover the latest-scan card.
- Restored a Check field to both Latest Activity and Recent Bay Scans.
- Added clear Success, Check, Failed, and neutral feedback badges.
- Sized the sticky panel to `100dvh - 10px` with 5 px top and bottom viewport spacing.
- Applied the same sticky fit in browser fullscreen.
- Closed the rail-layout gap while keeping the Bay Map action buttons outside the sticky slot.
- Rebuilt Add destination as one contained Target Bay row.
- Condensed Manual Scan into one aligned row with matching input surfaces.
- Changed Undo and Redo to icon-only application buttons with accessible labels.
- Applied the shared application button treatment to Manual Submit and Clear.
- No PNG previews were generated or packaged.

## v148 highlights

- Eliminated the large normal-flow gap between the static Bay Map action buttons and Bay Scanner.
- Kept the action buttons non-sticky; only the scanner panel sticks after reaching the top.
- Removed the `Just now` / waiting badge beside the Bay Scanner title while preserving its compatibility ID as a hidden status node.
- Hid the percentage labels under Route Pulse while Remove mode is selected.
- Replaced the collapsible Recent Bay Scans disclosure with a permanently open compact table.
- Reduced recent history to Order Nr., Job Nr., Action, and Current Bay.
- Kept Current Bay editable through the existing location-change dropdown.
- Removed horizontal and vertical scrolling from the recent history section.
- Excluded structural layout edits from both Recent Bay Scans and All Scans history while retaining administrative audit records.
- No PNG previews were generated or packaged.

## v147 highlights

- Removed `Indian Trail receiving`, the header workflow sentence, and the visible Current Mode card.
- Kept the Bay Scanner title and Route Pulse inside one continuous blue header.
- Recolored Route Pulse metrics with restrained dark-blue surfaces instead of bright white controls.
- Removed the inherited dotted connector and arrow that crossed the Route Pulse section.
- Added strict paint and width containment so Route Pulse remains inside the rounded panel.
- Hid Destination Control whenever Remove is selected and restored it immediately for Add mode.
- Moved only the sticky scanner panel to an 8-pixel top offset; Bay Map action buttons remain non-sticky.
- Preserved barcode scanning, Undo/Redo, Manual Scan, All Scans, recent history, location correction, permissions, API calls, and scan behavior.
- No PNG previews were generated or packaged.

## v146 highlights

- Merged the Bay Scanner title and Indian Trail Route Pulse into one blue header surface.
- Contained every Route Pulse metric, transit control, and progress element within the panel width.
- Changed Remove guidance to `Finds the piece's current bay`.
- Removed the redundant Remove-mode sentence beneath Destination Control.
- Removed the barcode Submit Scan button; barcode entry continues to submit through Enter and scanner input.
- Positioned Undo and Redo halfway across the scan field's upper-right border.
- Replaced the collapsible Manual Entry card with one always-visible horizontal row.
- Made Manual Order wider than Item and limited Item to three numeric characters.
- Kept the Manual Submit button on the right side of the same row.
- Preserved All Scans, recent history, location correction, permissions, API calls, and scan behavior.
- Added responsive and reduced-motion handling without generating or packaging preview images.

## v145 highlights

- Moved Indian Trail Route Pulse directly below the blue Bay Scanner header.
- Removed the gray inset around the header so the blue surface reaches both rounded top corners.
- Rebuilt Scan Command with dedicated v145 layout classes so older grid rules cannot compress it into narrow columns.
- Kept Remove/Add, Destination Control, Bay Code, Clear, barcode entry, Submit Scan, Undo, and Redo in clear horizontal workflow rows.
- Moved the sticky desktop position slightly higher without changing the panel's initial unscrolled location.
- Rebuilt Old Bays, Rush / Remake, Manage Items, Edit Bays, and Edit Map as a balanced professional action toolbar.
- Preserved Manual Entry, Latest Activity, Recent Bay Scans, All Scans, and Change Location.
- Added responsive and reduced-motion handling without changing scanner behavior.
- Preserved all Bay Scanner IDs, permissions, API calls, scan logic, and event handlers.

## v144 highlights

- Replaced the tall three-card Bay Scanner workflow with one compact scan command console.
- Made the barcode field and Submit Scan action the visual priority for production-floor use.
- Rebuilt Add/Remove as a clear segmented mode control with semantic state styling.
- Combined target-bay guidance and bay-code entry into one compact destination strip.
- Kept Undo and Redo immediately below the barcode command without consuming a full workflow card.
- Condensed Indian Trail Outbound / In Transit / Received progress into a small live route pulse.
- Kept Manual Entry and Recent Bay Scans collapsed until needed.
- Reworked the latest-scan card so bay, action, order, time, and location correction stay readable.
- Added restrained entrance, status-pulse, focus, progress, disclosure, and button animations.
- Added a dedicated short-height desktop layout so the complete panel remains visible at common 1366x768 floor-computer resolutions.
- Added a complete reduced-motion fallback for accessibility and floor devices that disable animation.
- Preserved all existing Bay Scanner IDs, permissions, API calls, scan logic, and event handlers.

## v143 highlights

- Internal Reject Tracking now matches the approved timeline-based design direction.
- Added a polished quality-recovery header with the primary Log Internal Reject action and compact Refresh/Clear controls.
- Added search, incident range, From, Through, and live Location filters in one balanced toolbar.
- Added a filtered summary strip for reject events, machines/locations, users, and rejected quantity.
- Reject history is grouped by incident date and rendered as a vertical timeline with readable compact cards.
- Each reject card shows order/item, quantity, delivery date, reason, machine/location, user, and time at a glance.
- Details expand in place to show customer, job, product, and investigation notes.
- Loading and error feedback remains visible, while successful loads no longer consume permanent vertical space.


## v142 highlights

- Create custom roles with a name, description, and explicit permission checklist.
- Select all or clear all permissions while building a new role.
- Existing roles remain expandable and independently editable.
- Custom roles immediately appear throughout user management.
- Create User uses a balanced two-panel layout with full-width email/password fields.
- Reject Tracking uses one header, one filter toolbar, and one history workspace.
- Internal Reject flags use white text on a dark pulsing red background.
- Each rejected line displays a full-width incident strip containing reason, process location/machine, and rejected time.
- Glass-type filter buttons grow or wrap to show the complete label instead of truncating it.
- Sidebar navigation labels use safe line height and padding so characters such as `y`, `g`, and `p` are not clipped.

v138 rebuilt the Internal Reject Tracking page, date filters, repeatable reject-entry window, and explicit item verification workflow.

v137 improved the Bay Scanner, rack/truck packing-list scope, personalized update review, filter counts, glass-type layout, and the first reject-entry redesign.

v136 stabilized rack-card modal opening, Reject Tracking error states, Admin import-run tabs, button ownership, Admin editor framing, and Bay Scanner width containment.

v134 fixes the floor folder-import scheduler installer failing PowerShell syntax validation at `Install-DeliveryListSqlAutomationTasks.ps1:227`. The task mode variable is explicitly delimited before the literal colon, so the hourly folder-import tasks can be created normally. The floor setup continues to validate the installed PowerShell files before touching Task Scheduler.

v133 fixes Windows batch launchers closing immediately when the scanner project path contains parentheses or other CMD-sensitive characters, such as `Delivery-List-Scanning-Project-main (5)`. The floor folder-import setup and desktop-shortcut launchers now use label-based control flow instead of parenthesized command blocks, quote every project-derived path, always pause at a visible result screen, and write launcher/error logs under the project `logs` folder.

v132 adds a dedicated one-click floor-computer setup for hourly imports from the shared Temp Delivery Lists folder. It installs the missing runtime scripts under `C:\DeliveryListAutomation\Scripts`, preserves existing automation configuration with timestamped backups, forces folder-import-only mode, sets the interval to 60 minutes, creates and verifies the scheduled tasks, and skips A+W SQL and workbook-write preflight checks on floor computers while keeping the central SQL workflow unchanged.

v131 fixes the floor transfer false-positive that treated the maintained route-membership repair as lost data. When startup merges duplicate receiving-stage copies of the same logical order item, the transfer now allows the lower raw `line_items` count only after verifying every removed row has the maintained merge audit, remains represented by an equivalent receiving row, and retains at least the same quantity and scanned progress. Staging, outbound, unaudited, or quantity-reducing removals still fail and roll back.

v130 completes the canonical v096 schema before running the v097 production migration on older floor databases. This safely creates missing support tables such as `system_metadata` and adds any missing late-v096 columns without replacing existing rows, fixing the transfer failure that occurred after the main migrations when startup tried to read a table absent from early development databases.

v129 added pre-v097 compatibility-column repair so older floor databases receive `source_route`, `priority_delivery_date`, and `priority_direct_to_truck` before the v097 `line_items` rebuild.

v128 fixes the Windows project-root quoting failure in the floor database transfer launcher. The BAT now removes its trailing directory separator before passing the current project path to Python, and the Python tool defensively repairs the malformed `project-main" --interactive` argument produced by already-extracted v127 launchers.

v127 fixes the floor database transfer BAT closing immediately after a pasted path. The source-path prompt now runs inside Python instead of CMD, preventing spaces, ampersands, parentheses, quotes, and other Windows path characters from breaking batch parsing. The launcher always reaches a visible success/failure screen, waits for a keypress before closing, supports drag-and-drop through an environment handoff, and writes `logs\floor-database-transfer-launch.log` for startup diagnostics.

v126 adds a guarded floor-database transfer utility for moving an existing SQLite scanner database into the newest project copy without losing operational data. The BAT creates verified source and target backups, uses SQLite online backup so WAL data is included, runs the current maintained migrations, validates integrity and foreign keys, compares every pre-existing table count, writes a JSON report, and automatically restores the prior target database if the upgrade fails.

v125 fixes Windows PowerShell treating harmless `schtasks.exe` error output as a terminating `NativeCommandError` when an obsolete scheduled task is not installed. The scheduler now queries before deleting legacy tasks, captures native command output under a non-terminating preference, and evaluates the real exit code for delete, create, query, and launch operations.

v124 fixes the remaining schedule-installation parser failure caused by an older Crystal automation script that was still present in the shared installed Scripts folder. The maintained SQL scheduler now syntax-checks only the current SQL automation entry points it actually uses, while the legacy Crystal task installer is also repaired so its task-name labels are valid PowerShell.

v123 fixes the Windows Task Scheduler installer parser error, validates every installed PowerShell automation script before tasks are created, and runs the existing SQL/workbook/scanner runtime preflight before schedule installation. It also adds a one-click end-to-end verification command that queries A+W SQL for a known date, rebuilds and validates the workbook, explicitly invokes the maintained scanner importer for that date, checks the known-date expected counts, and confirms every expected stage list exists in the scanner store. Delivery List Management now preserves newest-run No Changes timestamps when the normal Admin summary refreshes, preventing unchanged dates from falling back to `Updated at: --`. The CSS maintenance header explicitly requires reusing maintained selectors, components, and tokens before adding new rules.

v122 organizes the main stylesheet into a documented page-and-component ownership map without changing the intentional source order of compatibility rules. It also removes a small set of verified exact CSS duplicates and fixes Delivery List Management so every stage for a manually or automatically checked delivery date receives the completed-run timestamp even when the result is **No Changes**.

v121 centers delivery-list update toasts at the bottom of the page for 20 seconds, marks bell notifications read when the notification menu opens, removes the manual read control, stamps every latest-run result including No Changes with the actual check completion time, and makes per-user Mark reviewed clear the visible New/Updated rows immediately while verifying the exact notice receipts on the server.
v120 separates delivery-list automation notices from Rush alerts, adds a small nonblocking update toast, opens Delivery List Management from bell notifications, and adds persistent per-user current/future line-update review state. New and updated lines remain highlighted for each user until that user explicitly marks the selected list reviewed; repeated no-change imports do not erase unseen updates.
v118 moves Import Audit History into the Import / Update Delivery List control center, aligns the smaller notification bell with the other header utility buttons, and installs a non-destructive SQLite import reconciler so lists with append-only scan history can update without deleting their line-item identities.
v117 fixes live Delivery List Management rerendering so new, restored, updated, and removed dates appear in the scanner's original Admin/Home layout without a browser refresh. Import Audit History no longer auto-refreshes while open, every entry starts collapsed, and failed workbook logs now include the exact file/error plus a retained normalized result for troubleshooting.
v116 restores the original Delivery List Management overview and moves Import Audit History into a dedicated searchable modal. History is newest-first, paginated at 20 rows by default, supports 20/50/100 rows per page, and can be filtered by status, delivery date, filename, stage, or user. The obsolete inline import-folder/date settings are removed because those controls now live in the Automation Control Center.
v115 adds non-disruptive live delivery-list synchronization for every signed-in browser. New delivery dates and stages appear without a page refresh, while the current page, selected list, and scanner workflow remain untouched. The v114 Admin-to-Scan redirect is removed, and transient scanner database contention now makes the importer wait and retry instead of failing immediately.
v114 refreshes the visible Recent Delivery List Imports section immediately after automated folder imports, preserves the maintained importer's per-stage New/Updated piece counts, and updates the Scan page delivery-list selectors without a browser reload. Inactive stages restored by reimport are now classified as New instead of No Changes. Excel-compatible workbook generation, integrity validation, and missing-list recovery remain enabled.
v113 repairs Excel-compatible SQL workbooks and restores deleted scanner lists. Generated XLSX files now follow Excel's required SpreadsheetML element order, carry recorded integrity hashes, and rebuild automatically when an older or damaged workbook is detected. SQL export-and-import runs audit every A+W source date, report current No Changes results without reimporting complete unchanged dates, and route missing stage lists through the maintained exact-date folder importer.
v112 fixes false failures when an incremental check has no workbooks to import. Unchanged runs now skip the scanner importer cleanly, complete successfully, and publish the normal no-change notification. Changed-workbook imports, pending retries, v111 live-log performance, v110 UNC publishing, v109 authoritative import history, and all scanner workflows remain preserved.
v111 fixes the completed-import log stall and reduces live-status write overhead. The importer now keeps its complete per-file result in the normalized result file while printing only one concise console summary, the browser controller throttles recovery-status persistence instead of rewriting the entire growing log after every line, and requested date windows exclude unrelated folder results. v110 UNC publishing, complete logs, v109 authoritative import history, and all scanner workflows remain preserved.
v110 fixes UNC workbook publishing and adds complete live automation logs. SQL-generated workbooks now use a network-share-compatible staged overwrite instead of `System.IO.File.Replace`, the **Status & Logs** page streams every active output line and retains the complete per-run log, and notification publishing uses a JSON request file for reliable Windows argument handling. v109 authoritative recent-import classifications and all scanner workflows remain preserved.
v109 corrects automated delivery-list import history so SQL and folder automation use the scanner's maintained import records, refresh the Admin **Recent Delivery List Imports** section immediately, and accurately label each result as **New**, **Updated**, **New + Updated**, **No Changes**, or **Failed**. Existing scan preservation, routing, stages, racks, bays, notifications, and v108 automation controls remain unchanged.
v107 adds the Delivery List Automation Control Center to the existing **Import / Update Delivery List** command. Admin users can now import only from the Temp Delivery Lists folder, query A+W SQL and export workbooks without importing, or query/export/import in one controlled run. The same GUI manages the automatic mode, date windows, interval, full refresh time, notifications, and scheduled tasks. This lets authorized central systems use SQL while temporary floor copies use folder-only importing without A+W access.
v106 adds a local, no-third-party-scheduler automation package for the A+W Crystal Reports delivery-list workflow. It supplies the `DeliveryDate` parameter to `DeliveryList.rpt`, uses locally encrypted SQL credentials, exports validated XLSX files through the production UNC folder, and invokes the scanner's existing import logic immediately after each scheduled run.

The package includes one-date testing, Crystal runtime and architecture detection, hourly incremental refreshes, daily full reconciliation, atomic `.partial` publishing, duplicate-file checks, logs, status reporting, and removable Windows Task Scheduler tasks. It does not bundle SAP runtime files, SQL credentials, databases, or generated delivery lists.

The v097 numbered/checksummed SQLite migrations, verified backups, constraints, append-only event history, integrity tooling, and Azure SQL migration preparation remain unchanged.

## Start the local web app

1. Keep `Start-DeliveryScannerWebApp.bat` and `Start-DeliveryScannerWebApp.ps1` beside `server.py`.
2. Keep the existing `data`, `assets`, `sounds`, and `static` folders in the project folder.
3. Double-click `Start-DeliveryScannerWebApp.bat`.
4. Keep the single launcher window open while the local server is running. The scanner no longer starts a second Python console.

SQLite remains the active/default database. The production database is:

`data\delivery-scanner-pilot.db`

Keep this file and its `-wal`/`-shm` companions together whenever the app is running. Before any numbered schema upgrade, startup creates and verifies a version-labeled backup under `data\backups`. Production databases are never deleted or recreated automatically.

## Database preservation

The `data` folder is production state, not application source. Never replace or
delete it during a code-only update. Stop the server and copy the complete
folder, including SQLite `-wal` and `-shm` companions, before transferring a
floor database to another checkout.

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

See `automation\sql_delivery_export\README.md` for the installed runtime and
troubleshooting steps.

## Database operations

- Azure migration dry run: `py -3 -m database.migrate_sqlite_to_azure_sql --sqlite-path data\delivery-scanner-pilot.db`
- SQLite migrations are owned by `database\migrations.py`.
- The logical cross-database contract is owned by `database\contract.py`.

## Optional container deployment

Docker and Azure App Service support files are organized under `deployment`.
They are not required for normal Windows floor operation.

- Container definition: `deployment\docker\Dockerfile`
- Container-only dependencies: `deployment\docker\requirements.txt`
- Azure App Service setting template:
  `deployment\azure\app-service.env.example`

Run the Docker build from the project root so the root `.dockerignore` protects
local databases, secrets, logs, backups, and verification output:

```powershell
docker build -f deployment/docker/Dockerfile -t delivery-list-scanner .
```

## Audio language

The maintained sound pack is stored under `sounds\` as 44.1 kHz, 16-bit PCM mono WAV files. Open `sounds\preview_audio_pack.html` in a browser to audition the packaged cues without installing audio software. The web app loads semantic cue names from `static\js\app.js`, uses the existing shared volume/compressor chain, and falls back to synthesized tones only if a WAV file cannot be loaded.

The existing sound-volume slider remains available for floor testing. At 100%, the main operational files are mastered for production-floor use; the subtle expand/collapse and destructive-action cues are intentionally quieter and shorter so routine interface actions are less distracting.

## Microsoft Graph email

Version 70 introduced Microsoft Graph delivery for customer manifests, ready notices, and Admin test messages; v132 retains that implementation unchanged. The configured sender is `BarefootNC.Glass@bldr.com`, and the default controlled test recipient is `brandon.m.smith@bldr.com`.

After BLDR IT provides the Entra tenant ID, application/client ID, and a client-secret value, run `Configure-MicrosoftGraphEmail.bat` once. The secret is encrypted for the current Windows account and loaded only in memory by the normal scanner launcher.

## Project documentation

- Ongoing version history: `README_CHANGELOG.md`
- Current folder ownership and cleanup guide: `docs/PROJECT_STRUCTURE.md`
- Automated SQL export/import runtime: `automation/sql_delivery_export/README.md`

## Important local folders

- `static` - maintained browser CSS, JavaScript, and image source.
- `assets` - favicon and print-page assets referenced by the server.
- `sounds` - maintained browser audio cues.
- `data` - required SQLite database and local scanner state. Keep it and back it up.
- `automation` - scheduled delivery-list import/export source and setup scripts.
- `scripts` - optional Windows setup and diagnostic utilities.
- `resources` - source material retained for A+W integration work.
- `logs` - generated diagnostics. Safe to clear while the app is stopped.
- `backups` - retained recovery copies. Review dates before removing anything.
- `C:\DeliveryListAutomation` - installed automation runtime, staging, logs, and task state.

A terminal whose prompt points to another project folder, such as `Showers Programmer`, is being opened by that project or its updater; the scanner launcher fixes its Python working directory to this project folder.

The release ZIP contains no database, SQL credential, SAP runtime, or demo delivery list. When upgrading, keep your existing `data` folder. Production startup never seeds demo delivery lists; existing data is preserved and upgraded in place only after a verified backup succeeds.

Do not run the SQLite and Azure SQL versions as simultaneous writable production systems during the future cutover.
