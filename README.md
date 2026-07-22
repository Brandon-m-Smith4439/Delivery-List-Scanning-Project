# Delivery List Scanner

Current maintained release: **v105**. SQLite remains the active/default backend.

v105 completely rebuilds the **Old Bay Control Center** and the Indian Trail **Bay Scanner** without removing any existing bay-map capabilities. Old Bay review now includes local search, age filtering, sorting, clear age/urgency treatments, row selection, safe bulk snoozing, individual snoozing, summary counts, and the existing printable investigation list.

The Bay Scanner now presents Add/Remove as a clear three-step workflow, makes target-bay requirements obvious, provides a larger primary scan command, keeps Undo/Redo close to the scan action, moves manual entry into an accessible disclosure, and reorganizes current/recent history into a cleaner operational card. Route progress, barcode scanning, manual scans, location correction, and All Scans remain available.

The v097 numbered/checksummed SQLite migrations, verified backups, constraints, append-only event history, integrity tooling, and Azure SQL migration preparation remain unchanged.

## Start the local web app

1. Keep `Start-DeliveryScannerWebApp.bat` and `Start-DeliveryScannerWebApp.ps1` beside `server.py`.
2. Keep the existing `data` folder in the project folder. A separate `assets` folder is not required for this maintained release package.
3. Double-click `Start-DeliveryScannerWebApp.bat`.
4. Keep the single launcher window open while the local server is running. The scanner no longer starts a second Python console.

SQLite remains the active/default database. The production database is:

`data\delivery-scanner-pilot.db`

Keep this file and its `-wal`/`-shm` companions together whenever the app is running. Before the first v097 schema upgrade, startup creates and verifies a backup under `data\backups`. Production databases are never deleted or recreated automatically.

## Database operations

- Health check: `py -3 tools\database_integrity_check.py data\delivery-scanner-pilot.db`
- Maintenance while stopped: `py -3 tools\database_maintenance.py data\delivery-scanner-pilot.db --optimize --checkpoint`
- Azure dry run: `py -3 migrate_sqlite_to_azure_sql.py --sqlite-path data\delivery-scanner-pilot.db`

See `docs\DATABASE_MIGRATIONS.md` before restoring or troubleshooting an upgrade.

## Audio language

The maintained sound pack is stored under `sounds\` as 44.1 kHz, 16-bit PCM mono WAV files. Open `sounds\preview_audio_pack.html` in a browser to audition the packaged cues without installing audio software. The web app loads semantic cue names from `app.js`, uses the existing shared volume/compressor chain, and falls back to synthesized tones only if a WAV file cannot be loaded.

The existing sound-volume slider remains available for floor testing. At 100%, the main operational files are mastered for production-floor use; the subtle expand/collapse and destructive-action cues are intentionally quieter and shorter so routine interface actions are less distracting.

## Microsoft Graph email

Version 70 introduced Microsoft Graph delivery for customer manifests, ready notices, and Admin test messages; v104 retains that implementation unchanged. The configured sender is `BarefootNC.Glass@bldr.com`, and the default controlled test recipient is `brandon.m.smith@bldr.com`.

After BLDR IT provides the Entra tenant ID, application/client ID, and a client-secret value, run `Configure-MicrosoftGraphEmail.bat` once. The secret is encrypted for the current Windows account and loaded only in memory by the normal scanner launcher. See `docs/MICROSOFT_GRAPH_EMAIL.md` for the IT and testing steps.

## Project documentation

- Ongoing version history: `README_CHANGELOG.md`
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

A terminal whose prompt points to another project folder, such as `Showers Programmer`, is being opened by that project or its updater; the scanner launcher fixes its Python working directory to this project folder.

The release ZIP contains no database or demo delivery list. When upgrading, keep your existing `data` folder. Production startup never seeds demo delivery lists; existing data is preserved and upgraded in place only after a verified backup succeeds.

Do not run the SQLite and Azure SQL versions as simultaneous writable production systems during the future cutover.
