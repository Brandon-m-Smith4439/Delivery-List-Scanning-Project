# Delivery List Scanner v063 Testing and Maintenance

## Supported operating mode

SQLite remains the active and default database. Azure SQL files are cutover-readiness assets only and are not activated unless `DLS_DATABASE_TYPE=azure-sql` is explicitly configured.


## Supported Windows startup

Keep these files together in the extracted project folder:

- `Start-DeliveryScannerWebApp.bat`
- `Start-DeliveryScannerWebApp.ps1`
- `server.py`
- The remaining project files

Start the application by double-clicking the BAT. The launcher waits for `/api/health` before opening the browser. If Python or SQLite fails, the window remains readable and details are written to `logs/launcher.log`, `logs/server-stderr.log`, and `logs/startup-error.log`.

Do not reuse the older launcher that opens the browser before running Python. Replace both the BAT and PS1 with the v063 copies.


## Existing production database recovery

Do **not** delete `data\delivery-scanner-pilot.db` for the v063 startup fix. Replace the application files with the v063 release while preserving the existing `data` folder. Demo data now seeds only into an empty database, so an old `data\sample-delivery-list.json` may remain without being synchronized into live lists at startup.

The included BAT also unblocks the PowerShell launcher automatically. Start with `Start-DeliveryScannerWebApp.bat`; no Run once prompt should be required.

## Required validation before a release

Run:

```bash
python tools/run_full_validation.py
```

That command checks Python and JavaScript syntax, the full pytest suite, browser-rendered visual smoke tests, code-reference generation, and release hygiene.

## Manual floor check before replacing production

1. Sign in as an Operator, Indian Trail user, Supervisor, and Admin account.
2. Import one representative delivery list containing Indian Trail, Greenville, CPU, DTC, Rush, Remake, and updated items.
3. Confirm the expected Staging, Outbound, and route-specific receiving lists exist.
4. Scan a normal label, a duplicate label, a blocked Outbound label, a rack barcode, and an Indian Trail receive.
5. Confirm Undo/Redo, recent scans, All Scans colors, rack selection, bay assignment, Rush alerts, and print/export output.
6. Restart the server twice with the included BAT and confirm the second startup does not run route reconciliation again.
7. Temporarily occupy port 8765 with another program and confirm the launcher selects the next open port.
8. Review the `logs` folder and confirm launcher/stdout logs are created.
9. Keep the previous ZIP and database backup until the floor has completed one full shift on the new version.

## Maintenance rules

- Update an existing workflow instead of adding a parallel function, popup, event listener, or CSS override.
- Put business rules in `delivery_store.py`, HTTP translation in `server.py`, browser behavior in `app.js`, and visual rules in the documented section of `styles.css`.
- Preserve `source_id` across stage copies.
- Add schema changes as idempotent migrations that open existing SQLite databases safely.
- Regenerate `CODE_REFERENCE_v063.md` after structural edits.
