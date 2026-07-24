# Delivery List Scanner

Current maintained release: **v129**. SQLite remains the active/default backend.

v129 repairs the Windows desktop-shortcut installer. The BAT now validates Windows PowerShell, keeps success and failure messages visible, and calls the companion script with quoted paths. The PowerShell creator now targets the maintained `Start-DeliveryScannerWebApp.bat` launcher instead of the obsolete spaced filename, resolves redirected/OneDrive Desktop folders, safely handles project paths containing spaces or symbols, uses the packaged scanner icon when available, replaces an existing shortcut, and verifies the saved target, arguments, and working directory before reporting success.

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
2. Keep the existing `data` folder in the project folder. A separate `assets` folder is not required for this maintained release package.
3. Double-click `Start-DeliveryScannerWebApp.bat`.
4. Keep the single launcher window open while the local server is running. The scanner no longer starts a second Python console.

To add a desktop launcher, double-click `Create Desktop Shortcut.bat` from the project folder. It creates or replaces the current user's **Glass Delivery Scanner** shortcut and points it to the maintained `Start-DeliveryScannerWebApp.bat` launcher.

SQLite remains the active/default database. The production database is:

`data\delivery-scanner-pilot.db`

Keep this file and its `-wal`/`-shm` companions together whenever the app is running. Before the first v097 schema upgrade, startup creates and verifies a backup under `data\backups`. Production databases are never deleted or recreated automatically.

## Floor database transfer and upgrade

Use `Transfer-Floor-Database-To-Current-Version.bat` when updating a floor computer to a newer scanner build while keeping its existing SQLite data.

1. Close the old and new Delivery List Scanner server windows.
2. Keep the old project folder unchanged.
3. Extract the newest changed-files package into the newest/current project folder.
4. Double-click `Transfer-Floor-Database-To-Current-Version.bat`.
5. Paste the old project folder, old `data` folder, or old `delivery-scanner-pilot.db` path.
6. Confirm the displayed source and target paths by typing `TRANSFER`.
7. Start the newest web app and verify users, delivery lists, scans, racks, and bays.

The utility does not modify the old database. It backs up both the old source and the current target under `data\backups\floor-database-transfer-<timestamp>`, upgrades the copied database with the current app's numbered migrations, validates SQLite integrity/foreign keys, and confirms that record counts from every old table did not decrease. On failure, it preserves diagnostics and restores the database that was in the current project before the transfer.

This is a replacement-and-upgrade operation, not a merge of two separately active databases. It supports the maintained v096-compatible SQLite schema and later. See `docs/FLOOR_DATABASE_TRANSFER.md`.

## Automated A+W delivery-list imports

The maintained v121+ automation package is under `automation\sql_delivery_export`.

1. For an existing v121-v124 installation, extract the newest changed-files package into the project folder and run `Apply-v125-AutomationPatch.bat` once. This safely backs up and replaces only the installed SQL schedule installer; it does not change configuration, scanner data, existing tasks, or workbooks.
2. Open **Admin > Import / Update Delivery List**, save the settings, and choose **Save & Install Schedule** again. The installer now checks PowerShell syntax and runs the SQL/workbook/scanner preflight before creating tasks.
3. Run `C:\DeliveryListAutomation\Verify-SQL-And-Import.cmd` and enter a known delivery date. This performs a real read-only A+W SQL query, enforces the configured known-date count comparison, rebuilds and validates the workbook, imports it through the maintained scanner workflow, and confirms every expected stage list exists.
4. Continue using the control center for Folder Import Only, SQL Export Only, SQL Export and Import, schedule settings, logs, and notifications.

See `automation\sql_delivery_export\README.md` for the installed runtime, repair steps, and verification details.

## Database operations

- Health check: `py -3 tools\database_integrity_check.py data\delivery-scanner-pilot.db`
- Maintenance while stopped: `py -3 tools\database_maintenance.py data\delivery-scanner-pilot.db --optimize --checkpoint`
- Azure dry run: `py -3 migrate_sqlite_to_azure_sql.py --sqlite-path data\delivery-scanner-pilot.db`

See `docs\DATABASE_MIGRATIONS.md` before restoring or troubleshooting an upgrade.

## Audio language

The maintained sound pack is stored under `sounds\` as 44.1 kHz, 16-bit PCM mono WAV files. Open `sounds\preview_audio_pack.html` in a browser to audition the packaged cues without installing audio software. The web app loads semantic cue names from `app.js`, uses the existing shared volume/compressor chain, and falls back to synthesized tones only if a WAV file cannot be loaded.

The existing sound-volume slider remains available for floor testing. At 100%, the main operational files are mastered for production-floor use; the subtle expand/collapse and destructive-action cues are intentionally quieter and shorter so routine interface actions are less distracting.

## Microsoft Graph email

Version 70 introduced Microsoft Graph delivery for customer manifests, ready notices, and Admin test messages; v129 retains that implementation unchanged. The configured sender is `BarefootNC.Glass@bldr.com`, and the default controlled test recipient is `brandon.m.smith@bldr.com`.

After BLDR IT provides the Entra tenant ID, application/client ID, and a client-secret value, run `Configure-MicrosoftGraphEmail.bat` once. The secret is encrypted for the current Windows account and loaded only in memory by the normal scanner launcher. See `docs/MICROSOFT_GRAPH_EMAIL.md` for the IT and testing steps.

## Project documentation

- Ongoing version history: `README_CHANGELOG.md`
- Automated A+W SQL export/import: `automation/sql_delivery_export/README.md`
- Floor database transfer and recovery: `docs/FLOOR_DATABASE_TRANSFER.md`
- Folder cleanup and required-file guide: `docs/FOLDER_CLEANUP_GUIDE.md`
- Function and ownership map: `docs/CODE_REFERENCE.md`
- Maintained test instructions: `docs/TESTING.md`
- Latest validation report: `docs/TEST_REPORT.md`
- Reviewed architecture and maintenance baseline: `docs/PROJECT_REVIEW.md`
- Microsoft Graph email setup: `docs/MICROSOFT_GRAPH_EMAIL.md`
- Future Azure deployment: `docs/AZURE_DEPLOYMENT.md`
- Canonical database contract: `docs/DATABASE_SCHEMA.md`
- Migration and recovery guide: `docs/DATABASE_MIGRATIONS.md`
- SQLite-to-SQL Server mapping: `docs/SQLITE_TO_SQLSERVER_MAPPING.md`
- Database maintenance: `docs/DATABASE_MAINTENANCE.md`
- Audio language and cue mapping: `docs/AUDIO_LANGUAGE.md`

## Important local folders

- `data` — required SQLite database and local scanner data. Keep it and back it up.
- `logs` — generated diagnostics. Safe to clear while the app is stopped.
- `C:\DeliveryListAutomation` — local SQL automation runtime, staging, logs, state, and scheduled-task files created by the maintained setup.

A terminal whose prompt points to another project folder, such as `Showers Programmer`, is being opened by that project or its updater; the scanner launcher fixes its Python working directory to this project folder.

The release ZIP contains no database, SQL credential, SAP runtime, or demo delivery list. When upgrading, keep your existing `data` folder. Production startup never seeds demo delivery lists; existing data is preserved and upgraded in place only after a verified backup succeeds.

Do not run the SQLite and Azure SQL versions as simultaneous writable production systems during the future cutover.
