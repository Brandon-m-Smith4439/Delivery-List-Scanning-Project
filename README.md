# Delivery List Scanner

Current maintained release: **v0.180**. SQLite remains the active/default backend.

v0.180 integrates the Rejects feature branch into main while preserving the
newest Bay Map work. It also adds data-driven Glass Type filters to Manual
Delivery List Edit and keeps the production SQLite database in place.

## Install v0.180

1. Close the Delivery List Scanner server.
2. Update the existing project folder from the merged `main` branch.
3. Preserve the existing `data` folder and its SQLite database.
4. Restart the scanner and hard-refresh the browser with `Ctrl+F5`.

No database migration or separate setup script is required. Keep the existing `data` folder and database in place.

## v0.180 highlights

- Merged Rejects workflows and administration improvements into main.
- Preserved main's Bay Scanner, Old Bay attention, Current Priority Work, and
  timed scan feedback changes.
- Added a Glass Type section to the Manual Delivery List Edit Filters window.
- Shows only glass types present in the selected delivery-list stage.
- Displays the current piece quantity beside each glass type.
- Supports selecting one or multiple glass types at the same time.
- Uses OR logic within Glass Type and AND logic with the other filter groups.
- Keeps glass-type choices available even when another active filter returns no rows.
- Refreshes the available glass types when the selected delivery-list stage changes.
- Preserves the v0.179 exact-row Save repair and every existing manual-edit workflow.

## v0.179 highlights

- Saves the exact expanded Manual Edit card associated with the clicked Save button.
- Captures all visible text, quantity, location, route, process, and product controls before asynchronous work begins.
- Stores each card's original values so the browser can identify the precise fields the operator changed.
- Sends the detected changed-field list with the update request for verification and diagnostics.
- Prevents a false no-change response from rerendering the card and erasing the operator's entered values.
- Keeps the edited card open and displays an error if the server does not confirm the update.
- Preserves the v0.178 explicit route override and New Order workspace layout.

## v0.178 highlights

- Reads Route, Location, Process, and Product directly from the visible manual-edit controls during save.
- Sends an explicit `routeOverride` so CPU-to-Indian Trail changes cannot be lost to legacy route inference.
- Uses `INDIAN TRAIL` as the maintained edit value instead of the legacy `IT` fallback.
- Keeps the Create New Order form in a dedicated non-shrinking row above the independently scrolling results.
- Makes the expanded New Order form scroll within its own bounded card on shorter displays.
- Returns the route actually applied by the backend for verification.

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
