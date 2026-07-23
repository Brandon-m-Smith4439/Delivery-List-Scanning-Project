## v114 - Immediate Import History Refresh and Correct New-Stage Classification

- Fixed the SQL automation refreshing the hidden legacy `importHistory` element instead of the visible `adminDeliveryLists` Recent Delivery List Imports section.
- Changed the visible Admin section to use the authoritative result returned by the just-completed maintained folder import.
- Added per-stage result rows with New Stage, Updated, New + Updated, No Changes, and Failed presentation.
- Added accurate added-piece, updated-piece, changed-piece, and changed-line details for each stage.
- Preserved stage summaries and reactivated-stage identifiers through the Python import wrapper, PowerShell run summary, recent-import API, and browser renderer.
- Added a browser-state synchronization bridge that refreshes `state.lists`, the Scan page delivery-date selector, and the stage selector immediately after an external automation import.
- Fixed deleted or inactive delivery-list stages being restored successfully but classified as No Changes.
- Updated the maintained importer to distinguish active existing stages from inactive stages and count a restored stage as New while recording `reactivatedCount` and `reactivatedListIds`.
- Prevented an older imports-table row for the same workbook and delivery date from replacing the newest run's New or Updated result.
- Retained the Excel-compatible workbook generation, OOXML validation, UNC publishing, live logs, notification center, and automatic missing-list recovery added in earlier automation versions.
- Preserved existing scan quantities, routing, racks, bays, audit history, automation configuration, and scheduled-task selection.
