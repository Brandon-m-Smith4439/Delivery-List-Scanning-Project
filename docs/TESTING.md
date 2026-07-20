# Delivery List Scanner v074 Testing and Maintenance

## Supported operating mode

SQLite remains the active and default database. Azure SQL files are cutover-readiness assets only and are not activated unless `DLS_DATABASE_TYPE=azure-sql` is explicitly configured.


## Supported Windows startup

Keep these files together in the extracted project folder:

- `Start-DeliveryScannerWebApp.bat`
- `Start-DeliveryScannerWebApp.ps1`
- `server.py`
- The remaining project files

Start the application by double-clicking the BAT. The launcher waits for `/api/health` before opening the browser. If Python or SQLite fails, the window remains readable and details are written to `logs/launcher.log`, `logs/server-stderr.log`, and `logs/startup-error.log`.

Do not reuse the older launcher that opens the browser before running Python. Replace both the BAT and PS1 with the v074 copies.


## Existing production database recovery

Do **not** delete `data\delivery-scanner-pilot.db` for the maintained startup fix. Replace the application files with the v074 release while preserving the existing `data` folder. Demo data now seeds only into an empty database, so an old `data\sample-delivery-list.json` may remain without being synchronized into live lists at startup.

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
9. Open the Bay Map scanner in normal and fullscreen modes; confirm the larger title, pieces-in-transit pill, existing manifest, and long bay names such as `Manual Overflow`.
10. In Rush / Remake Order, type part of a Job Nr. or Order Nr.; confirm predictive results and the Bay Code dropdown appear.
11. Use a job with one occupied `1/1` item and one missing item; confirm job-level Rush selects only the missing item.
12. Select an exact occupied Order/Item as Remake; confirm only that item leaves its bay and becomes missing.
13. Expand Current Rush / Remake Orders and clear one item; confirm other marked items on the job remain unchanged.
14. Open Print / Export and confirm every glass-type category ribbon starts expanded.
15. Trigger an Outbound rack confirmation, hover it for several seconds, and confirm the timer pauses; click the body and confirm All Scans opens.
16. Trigger an Indian Trail receive confirmation and repeat the pause/click check for All Bay Scans; perform another scan while hovering and confirm the new popup replaces the old one.
17. Open Edit Role Permissions and confirm every permission includes a short readable description.
18. Open Lookup Manager, switch among Product/Route/Process tabs, load an existing value with Use / edit, search the active library, and save one representative value.
19. Keep the previous ZIP and database backup until the floor has completed one full shift on the new version.

## Maintenance rules

- Update an existing workflow instead of adding a parallel function, popup, event listener, or CSS override.
- Put business rules in `delivery_store.py`, HTTP translation in `server.py`, browser behavior in `app.js`, and visual rules in the documented section of `styles.css`.
- Preserve `source_id` across stage copies.
- Add schema changes as idempotent migrations that open existing SQLite databases safely.
- Regenerate `docs/CODE_REFERENCE.md` after structural edits.


## v074 sidebar and application-shell floor check

1. Open Home at a normal workstation width and confirm the full sidebar shows Home, Scan, Racks, Bay Map, Admin, and the signed-in profile at the bottom-left.
2. Confirm the upper header contains only global search, Search, Print/Export, language, refresh, and fullscreen controls; the profile must not appear in the upper-right.
3. Collapse the sidebar and confirm it becomes an icon rail without covering the page. Hover each icon and confirm the browser tooltip identifies the page.
4. Reload the browser and confirm the explicitly selected expanded/collapsed preference is retained.
5. Clear the saved sidebar preference in browser storage or use a fresh browser profile, then open Bay Map and confirm it defaults to the compact rail while the other pages default to expanded navigation.
6. Open the bottom-left profile in expanded and collapsed states. Confirm display name, role, station, account identity, and Sign out remain readable and clickable.
7. Enter fullscreen from Scan and Bay Map. Confirm the sidebar uses the compact rail and exiting fullscreen restores the prior desktop choice.
8. Resize below 960 pixels. Confirm the sidebar becomes a hidden drawer, the menu button opens it, the backdrop and Escape close it, and selecting a page closes it automatically.
9. Switch to Spanish at workstation and compact widths. Confirm navigation labels and utility controls remain within their surfaces without overlap.
10. Recheck Scan and Bay Map sticky scanner panels after the shorter header; confirm they do not hide beneath the utility bar.

## v068 retained progress, route-summary, and header regression check

1. Open each standard Scan-page stage and confirm the stage title is centered with no Test button beside it.
2. Leave the page idle and confirm the light sweep stays inside the progress bar instead of crossing the navy scanner header or panel.
3. Scan one piece and confirm the fill glides forward. Complete a small test list and confirm the sparkle remains inside the progress track.
4. Open Bay Map and verify the compact scanner and large In-Transit card both show mirrored Outbound and Received meters filling toward the center.
5. Compare the Bay Map Outbound quantity with the active Outbound list, including items already received at Indian Trail. Received must never be greater than Outbound.
6. Keep Bay Map open while another user sends an Indian Trail rack Outbound. Confirm the quantity refreshes within approximately 12 seconds.
7. Check English and Spanish at the workstation resolution. Confirm the command row, profile, navigation, and search do not overlap and Print/Export remains immediately left of the language control.
8. Confirm the profile summary is clickable across its full visible width and Sign out still opens in the existing dropdown.


## v069 header, Bay scanner, SDI, and transit floor check

1. Confirm the header shows only the Barefoot logo, larger page buttons, Print/Export before the language control, and a full clickable profile card.
2. Open the Scan page and confirm the progress bar spans the scanner header with `Qty:` beneath it.
3. Open Bay Map and confirm Add/Remove plus Target Bay share one compact command card.
4. Open Rush / Remake, search a known job, verify item rows are compact, and test Rush, Remake, and individual clear behavior.
5. Assign glass to a rack without scanning the rack Outbound; confirm it is absent from Pieces on the Way. Then complete and scan the rack Outbound and confirm it appears.
6. Compare today’s Outbound and Received route quantities to the relevant delivery-list rows, including items from updated/split lists.


## v071 reviewed-baseline check

1. Confirm the project starts with the existing preserved `assets` and `data` folders.
2. Confirm the browser loads `styles.css?v=20260716-v071` and `app.js?v=20260716-v071`.
3. Run `python tools/run_full_validation.py`.
4. Review `docs/PROJECT_REVIEW.md` before structural changes to the large store, server, JavaScript, or CSS workflows.
5. Treat the v070 Microsoft Graph floor check below as still required before any live BLDR email rollout.

## v070 Microsoft Graph email floor check

1. Obtain the BLDR tenant ID, app-registration client ID, and client-secret value from the authorized Microsoft 365 administrator.
2. Run `Configure-MicrosoftGraphEmail.bat` as the same Windows account that starts the scanner.
3. Start the scanner and confirm the launcher logs `Microsoft Graph email configuration loaded for BarefootNC.Glass@bldr.com`.
4. Open Admin > Customer Emails and confirm the transport says Microsoft Graph and Ready to send.
5. Confirm the sender is `BarefootNC.Glass@bldr.com` and the test recipient is `brandon.m.smith@bldr.com`.
6. Send the test and confirm the outbox status becomes Sent.
7. Confirm the message arrives at the test recipient and appears in the Barefoot mailbox Sent Items.
8. Temporarily use an invalid recipient and confirm a readable failed outbox row is created without exposing a token or secret.
9. Restart the scanner and confirm the encrypted configuration loads without asking for the secret again.
10. Confirm automatic import manifest and Staging-ready messages continue to use the same outbox and customer/CC rules.

