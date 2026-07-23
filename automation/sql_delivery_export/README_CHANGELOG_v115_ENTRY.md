## v115 - Non-Disruptive Live Delivery-List Synchronization

- Fixed the Admin page immediately redirecting to the Scan page after the v114 recent-import refresh ran.
- Removed the synthetic delivery-date and stage `change` events that caused normal Scan-page navigation handlers to run while the user was on another page.
- Replaced the v114 refresh bridge during setup so upgrading an already-installed v114 project removes the redirecting code instead of leaving both bridges in place.
- Added a silent delivery-list catalog refresh for every signed-in browser every 10 seconds and immediately after an import completes.
- New delivery dates and stage lists now appear in the Scan selectors without a browser refresh while preserving the user's current page, selected list, and active scan workflow.
- Kept the visible Recent Delivery List Imports section connected to the authoritative result of the latest maintained folder import.
- Preserved New, Updated, New + Updated, No Changes, Failed, restored-stage, added-piece, updated-piece, changed-piece, and changed-line details.
- Added database-busy retry and backoff to the external importer so active scanner writes are favored instead of turning a temporary SQLite/Azure SQL lock into a failed automated update.
- Confirmed that A+W querying, workbook generation, validation, and UNC publishing do not write to the scanner database; only the final maintained import phase briefly performs scanner database transactions.
- Preserved scan quantities, rack and bay assignments, routing, audit history, automation configuration, notifications, and scheduled-task selection.
