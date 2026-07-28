Delivery List Scanner v148
Bay Scanner History and Flow Refinement

INSTALL OVER v147

1. Close the Delivery List Scanner server.
2. Back up the project folder and the data folder.
3. Extract this ZIP directly into the current v147 project folder.
4. Replace files when Windows asks.
5. Run Apply-v148-BayScannerHistoryAndFlowRefinement.bat.
6. Restart the scanner normally.
7. Press Ctrl+F5 once in the browser.
8. Run Run-v148-BayScanner-Validation.bat.

WHAT CHANGED

- Removed the large gap between the static Bay Map action toolbar and scanner.
- Kept only the scanner sticky; action buttons scroll normally.
- Removed the visible Just now / waiting badge beside Bay Scanner.
- Hid Route Pulse percentage labels in Remove mode.
- Kept Recent Bay Scans permanently open.
- Reduced recent history to Order Nr., Job Nr., Action, and editable Current Bay.
- Removed horizontal and vertical scrolling from recent history.
- Excluded Bay Map layout-edit events from Recent Bay Scans and All Scans.
- Preserved administrative audit records.

DATABASE

No database schema migration is required. delivery_store.py receives a guarded history-filter update only. The installer creates timestamped backups under:

backups\v148-bay-scanner\<UTC timestamp>

PACKAGE CONTENT

This is a changed-files installer, not a production database package. It does not include a database, WAL/SHM files, logs, secrets, backups, caches, or PNG previews.

To create a complete clean source ZIP from the installed local project, run:

Build-v148-Full-Project-Package.bat
