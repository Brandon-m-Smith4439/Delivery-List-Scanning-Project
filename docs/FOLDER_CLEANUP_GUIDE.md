# Delivery List Scanner Folder Cleanup Guide

This guide separates files required to run the local SQLite web app from optional development and future-Azure files.

## Required for the local web app

Keep these files in the project root:

- `Start-DeliveryScannerWebApp.bat`
- `Start-DeliveryScannerWebApp.ps1`
- `Configure-MicrosoftGraphEmail.bat` — one-time local Graph setup.
- `Configure-MicrosoftGraphEmail.ps1` — encrypts the Graph client secret for the current Windows account.
- `server.py`
- `delivery_store.py`
- `scanner_config.py`
- `azure_sql_compat.py` — imported by the shared store even while SQLite is active; Azure packages are loaded only if Azure mode is selected.
- `index.html`
- `app.js`
- `styles.css`
- `README.md`
- `README_CHANGELOG.md`

Keep these folders:

- A separate `assets` folder is not required in the maintained release package.
- `data` — contains the active SQLite database. Never delete this folder during an upgrade.
- `data\secrets` — created only after Microsoft Graph setup; contains the DPAPI-encrypted local Graph configuration. Preserve it securely and never include it in a release ZIP.

## Keep for the planned Azure SQL deployment

These files do not affect normal SQLite startup, but they should stay with the maintained project so the later Azure cutover remains ready:

- `azure_sql_schema.sql`
- `migrate_sqlite_to_azure_sql.py`
- `requirements.txt`
- `Dockerfile`
- `.dockerignore`
- `.env.azure.example`
- `docs/AZURE_DEPLOYMENT.md`
- `docs/MICROSOFT_GRAPH_EMAIL.md`

## Optional maintenance and testing files

These are not required for daily floor use, but are useful for future coders and release testing:

- `pytest.ini`
- `tests`
- `tools`
- `docs/CODE_REFERENCE.md`
- `docs/TESTING.md`
- `docs/TEST_REPORT.md`
- `docs/PROJECT_REVIEW.md`
- `docs/FOLDER_CLEANUP_GUIDE.md`

## Files and folders that may be removed

Remove these while the app is stopped:

- `__pycache__`
- `.pytest_cache`
- old `CODE_REFERENCE_v###.md` files
- old `TEST_REPORT_v###.md` files
- old `TESTING_v###.md` files
- old ZIP releases after they are backed up elsewhere
- duplicate launcher BAT files such as `Start Delivery Scanner Web App.bat`
- `Create Desktop Shortcut.bat` and `Create-DeliveryScannerShortcut.ps1` after the shortcut has been created and verified
- old patch, diff, backup, or temporary audit folders

The `logs` folder may be deleted while the app is stopped. It will be recreated automatically. Keep the latest logs when troubleshooting.

## Git files

- `.gitignore` is useful only when using Git.
- `.git` contains the local Git history and is not required to run the app.

Delete `.git` only when you are certain you do not need local source-control history. Removing it does not affect the scanner database or runtime, but it permanently removes that local repository history.

## Demo data

Current startup logic does not seed or refresh demo delivery lists when the SQLite database already contains any delivery lists. It does not automatically delete demo rows that may have been inserted by an older version. Because older demo rows cannot be distinguished safely from real rows without reviewing the actual database, no automatic deletion is performed.
