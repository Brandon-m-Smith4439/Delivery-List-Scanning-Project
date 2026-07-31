# Delivery List Scanner

Current maintained release: **v0.193**. SQLite remains the active/default backend.

v0.193 adds guarded cross-delivery-date scanning to the maintained Scan and Indian Trail receiving workflows. When a barcode is not on the selected delivery list, the system can search accessible active lists in the same operational stage, switch a unique safe match automatically, or ask the operator to choose the correct date when review is required.

## Install v0.193

1. Close the Delivery List Scanner server.
2. Extract the v0.193 changed-files ZIP directly into the current project folder.
3. Preserve the existing `data` folder and its SQLite database.
4. Restart the scanner and hard-refresh the browser with `Ctrl+F5`.

No database migration or separate setup script is required. v0.193 stores its shared scan settings in the existing `system_metadata` table and keeps schema version 5.

## v0.193 highlights

- Checks the currently selected delivery date before searching anywhere else.
- Searches only active, accessible delivery lists in the same operational scan stage.
- Automatically switches and scans when one safe match exists and Auto mode is enabled.
- Opens a delivery-date selection window when multiple matches exist, Ask mode is enabled, or a rack, bay, outbound, or destination safeguard requires review.
- Shows delivery date, stage, order/item, progress, route, customer, location, and safety details for every candidate.
- Keeps the matched delivery date selected after a successful switch and refreshes the list, progress, flags, racks, recent scans, and Indian Trail data.
- Blocks completed candidates and respects existing stage access, duplicate, outbound, rack, destination, bay, and supervisor-override rules.
- Preserves a selected rack only when it remains open and destination-compatible. An unavailable, closed, or incompatible rack is cleared with an explanation before the cross-date scan is applied.
- Adds Admin settings for Disabled, Ask before switching, and Automatically switch unique matches.
- Adds configurable search windows with defaults of 7 past days and 30 future days.
- Records immutable audit events for cross-date matches, settings changes, and completed date switches.
- Uses the existing `scan_warning.wav` asset as the distinct delivery-date-change cue; no new sound file is required.

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
- v0.193 application contract: **193**.
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

v0.193 maps the new `delivery_date_changed` semantic cue to the existing `sounds\scan_warning.wav` file, so no binary sound asset is included in the changed-files release.

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
