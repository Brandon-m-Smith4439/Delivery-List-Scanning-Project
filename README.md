# Delivery List Scanner

## Start the local web app

1. Keep `Start-DeliveryScannerWebApp.bat` and `Start-DeliveryScannerWebApp.ps1` beside `server.py`.
2. Keep the existing `assets` and `data` folders in the project folder.
3. Double-click `Start-DeliveryScannerWebApp.bat`.
4. Keep the single launcher window open while the local server is running. The scanner no longer starts a second Python console.

SQLite remains the active/default database. The production database is:

`data\delivery-scanner-pilot.db`

Back up that file before installing a new version.

## Project documentation

- Ongoing version history: `README_CHANGELOG.md`
- Folder cleanup and required-file guide: `docs/FOLDER_CLEANUP_GUIDE.md`
- Function and ownership map: `docs/CODE_REFERENCE.md`
- Maintained test instructions: `docs/TESTING.md`
- Latest validation report: `docs/TEST_REPORT.md`
- Future Azure deployment: `docs/AZURE_DEPLOYMENT.md`

## Important local folders

- `assets` — required logos/icons and visual files. Keep it.
- `data` — required SQLite database and local scanner data. Keep it and back it up.
- `logs` — generated diagnostics. Safe to clear while the app is stopped.

A terminal whose prompt points to another project folder, such as `Showers Programmer`, is being opened by that project or its updater; the scanner launcher fixes its Python working directory to this project folder.

The release ZIP contains no database or demo delivery list. When upgrading, keep your existing `data` folder. Current startup logic will not seed sample lists into a nonempty database, but older demo rows are not deleted automatically.

Do not run the SQLite and Azure SQL versions as simultaneous writable production systems during the future cutover.
