# Delivery List Scanner

Current maintained release: **v089**. SQLite remains the active/default backend.

v089 adds the Builders FirstSource identity directly beneath the existing Barefoot & Company mark in one combined brand lockup. The combined logo is used on the sign-in screen, expanded desktop sidebar, and mobile navigation drawer, while the compact desktop rail keeps the existing Barefoot-only mark for readability. The v088 scan sounds, two-row history, search styling, and temporary sound-test controls remain unchanged.

## Start the local web app

1. Keep `Start-DeliveryScannerWebApp.bat` and `Start-DeliveryScannerWebApp.ps1` beside `server.py`.
2. Keep the existing `data` folder in the project folder. A separate `assets` folder is not required for this maintained release package.
3. Double-click `Start-DeliveryScannerWebApp.bat`.
4. Keep the single launcher window open while the local server is running. The scanner no longer starts a second Python console.

SQLite remains the active/default database. The production database is:

`data\delivery-scanner-pilot.db`

Back up that file before installing a new version.


## Microsoft Graph email

Version 70 introduced Microsoft Graph delivery for customer manifests, ready notices, and Admin test messages; v089 retains that implementation unchanged. The configured sender is `BarefootNC.Glass@bldr.com`, and the default controlled test recipient is `brandon.m.smith@bldr.com`.

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

## Important local folders

- `data` — required SQLite database and local scanner data. Keep it and back it up.
- `logs` — generated diagnostics. Safe to clear while the app is stopped.

A terminal whose prompt points to another project folder, such as `Showers Programmer`, is being opened by that project or its updater; the scanner launcher fixes its Python working directory to this project folder.

The release ZIP contains no database or demo delivery list. When upgrading, keep your existing `data` folder. Current startup logic will not seed sample lists into a nonempty database, but older demo rows are not deleted automatically.

Do not run the SQLite and Azure SQL versions as simultaneous writable production systems during the future cutover.
