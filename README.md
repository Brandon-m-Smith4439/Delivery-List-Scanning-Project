# Delivery List Scanner 

Current maintained release: **v0.205**. SQLite remains the active/default backend.

v0.205 standardizes the Print / Export header controls, replaces the calendar with a dedicated Date From / Date To range picker, loads the complete known glass-type catalog in the preset builder, and restores each user's active preset whenever they reopen Print / Export.

## Install v0.205

1. Close the Delivery List Scanner server.
2. Extract the v0.205 changed-files ZIP directly into the current project folder.
3. Preserve the existing `data` folder and SQLite database.
4. Restart the scanner and hard-refresh the browser with `Ctrl+F5`.

No database migration or separate setup script is required. v0.205 keeps schema version 5.

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
- v0.194 application contract: **194**.
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
