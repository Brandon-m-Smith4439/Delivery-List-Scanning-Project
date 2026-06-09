# Delivery List Scanning Project

Last updated: 2026-05-28

## Current Purpose

This project supports the glass plant delivery-list scanning workflow. Operators scan order/item barcodes from intake station workbooks. Those scans are buffered locally, sent to SharePoint through Power Automate, processed by the active master workbook, verified against the delivery list, and then reflected back into stage snapshots used by scanner stations.

## Active Workbooks

- `Multi User Scanner Queue Testing (version 2).xlsm`
  - Current multi-user master workbook.
  - Owns delivery-list import, queue processing, master validation, snapshot publishing, and Indian Trail bay assignment calls.
- `Intake_Scanning_Test (version 1).xlsm`
  - Current scanner station workbook.
  - Loads a selected delivery-list/stage snapshot, validates scans locally, buffers scan requests, and sends them to the shared queue.
- `Indian Trail Inventory Manager.xlsm`
  - Current Indian Trail bay/inventory manager workbook.
  - Used to view/search bay assignments, manually manage bays, and support SDI handling.

## Folder Map

- `Temp Delivery Lists`
  - Raw A&W delivery-list files before import into the master.
- `Delivery Lists to Export to Sharepoint`
  - Historical/imported delivery list workbooks used for SharePoint publishing/archive.
- `Sharepoint Lists`
  - CSV/schema exports of current SharePoint lists.
- `Power Automate Flows`
  - Zip exports of current Power Automate flows.
- `VBA Source`
  - Extracted editable VBA source for the active workbooks.
- `tools`
  - Local helper scripts for exporting/importing VBA source.
- `Backups`
  - Workbook backups and VBA sync backups.
- `(Legacy)`
  - Older one-user workbook versions and obsolete experiments.

## SharePoint Lists

- `ActiveDeliveryLists`
  - Tracks which delivery lists are online, paused, or offline.
  - Used by intake stations to find available delivery lists and by the master to publish heartbeat/revision state.
- `ScanQueue`
  - Shared queue for barcode, manual, comment, and snapshot requests.
  - Intake stations add rows; the master processes rows and writes final status/result.
- `DeliveryListSnapshots`
  - Stores stage-specific snapshot JSON for scanner workbooks.
  - Lets intake stations load master data without opening the master workbook directly.
- `IndianTrailBays`
  - Bay definitions/capacity/map data for Indian Trail.
- `IndianTrailBayAssignments`
  - Order-to-bay assignments and assignment status.
  - Current statuses include `PreAssigned`, `Occupied`, `Cleared`, `Cancelled`, `SDIOverride`, and `ManualException`.
- `IndianTrailProductRules`
  - Product/glass routing rules for Indian Trail bay assignment.
- `IndianTrailSettings`
  - Config values for Indian Trail bay logic.
- `IndianTrailSpecialOrders`
  - Special order flags such as SDI.

## Power Automate Flows

- `QueueAddRequest`
  - Adds scan/snapshot requests to `ScanQueue`.
- `QueueGetPending`
  - Returns pending/stale queue rows for the master processor.
- `QueueUpdateStatus`
  - Updates final or processing state on `ScanQueue` rows.
- `QueueGetRequestStatus`
  - Lets intake stations poll one request by request id.
- `SnapshotUpsert`
  - Upserts stage snapshots into `DeliveryListSnapshots`.
- `SnapshotGet`
  - Returns the latest active snapshot for a delivery list/stage.
- `ActiveUpsertHeartbeat`
  - Upserts master heartbeat/status/revision data into `ActiveDeliveryLists`.
- `ActiveCheckDuplicate`
  - Detects another active master for the same delivery list.
- `ActiveDeliveryListsGetOnline`
  - Lists online/paused active delivery lists for scanner settings.
- `IndianTrailBayAssignOrGet`
  - Assigns or retrieves Indian Trail bay assignment data.
- `CleanupOldActiveDeliveryLists`
  - Removes or expires stale active-list rows.
- `CleanupOldDeliveryListSnapshots`
  - Removes old snapshot rows.
- `CleanupOldScanQueueRows`
  - Removes old queue rows.

## Operating Rules

- Only one master workbook should process a delivery list at a time.
- Intake stations may keep scanning while the selected master is paused, offline, or temporarily not registered, but the panel must show a top warning banner and mark the scan state as warning-only until the master is online again.
- Scans must carry the delivery-list key and should be processed only against the matching master revision/snapshot.
- Delivery-list import should pause queue processing, publish a new revision, publish fresh snapshots, then resume queue processing.
- Power Automate trigger URLs/signatures are secrets and must not be posted in notes, tickets, or screenshots.

## Current Hardening Pass

Started 2026-05-28.

Completed first-pass changes:

- Convert duplicate-master warning into a hard block before queue processing starts.
- Keep the active master marked `Paused` while import/update actions are running so scanner stations can warn operators that updates will wait.
- Restore snapshot publishing after processed queue scans.
- Add intake-side paused/offline/not-registered warnings that still allow local buffered scanning.
- Add debug-sheet row trimming for high-volume intake Power Automate logs.
- Default the master import picker to `Temp Delivery Lists`.

Completed follow-up changes on 2026-05-29:

- Changed intake master-status handling so `Paused`, `Offline`, and `Not registered` are warning-only states instead of scan blockers.
- Added/confirmed top-of-stage banners for `MASTER PAUSED`, `MASTER OFFLINE`, and `MASTER NOT ONLINE`.
- Hardened the stage warning banner merge/clear logic so switching from paused to offline to online updates or clears the banner cleanly.
- Changed intake settings switching so unsent local buffered scans still block switching, but queue requests already sent to SharePoint can be left waiting after an operator confirmation.
- Applied master-status warnings immediately after delivery-list status refresh and snapshot load, instead of waiting for the next scan.
- Added heartbeat-age handling so stale `Online`/`Paused` active-list rows are treated as offline on intake, and stale duplicate-master records no longer block the live master.
- Updated `frmRushOrders` to match the other light-gray UserForm styling and load `Barefoot Logo.jpg` from the workbook folder at runtime.
- Record the last imported delivery-list source path/title/timestamp in workbook names.

Indian Trail manager changes on 2026-05-29:

- Made `Bay Map` the primary working screen after rebuild, with five top actions: Search, Bay Actions, Manual Entry, Refresh, and SDI.
- Rewired the old manager-panel button macros so they route into the same form/data actions instead of dead placeholder procedures.
- Added `modIndianTrailInventoryData` to load the exported SharePoint CSV lists into hidden local cache sheets and repaint the map from active assignments.
- Added local map status colors: `PreAssigned` yellow, `Occupied` green, `ManualException` red, and `SDIOverride` light blue.
- Updated `frmSearch` into a shared action form that supports Search, Bay Actions, Manual Entry, and SDI modes.
- Added a Power Automate write-back hook for future manager actions through `ITIM_URL_BAY_ADMIN_ACTION`; until that URL is filled in, manager actions update the local workbook/map cache only.
- Added `Power Automate Flows/README_IndianTrailBayAdminAction.md` with the recommended HTTP flow contract for clear/move/manual assign/manual exception/mark SDI/remove SDI actions.
- Refined `Bay Map` into a live operating view instead of a control-panel-first page: the title now reads `Indian Trail Live Bay View`, the right side shows occupied/preassigned/SDI/exception/not-on-map/active counts, and the refresh timestamp is shown on the map.
- Bay note cells now show compact assignment detail such as status/order/category instead of only the order number.
- Double-clicking a bay label or its adjacent assignment cell on `Bay Map` opens the Bay Actions form with that bay prefilled.
- Hid the old `Inventory Manager` panel during rebuild now that the map carries the working buttons.
- Moved the live status table to `Q15:U25`, moved the refresh/status message below it at `Q26:U26`, removed the delivery-list key from the visible live table, and added a legend for `PRE`, `OCC`, `SDI`, `EXC`, and `MAP`.
- Reduced the top map buttons to compact two-row buttons.
- Polished the live table to `Q11:U18`, removed blank rows inside the table, kept the refresh/status message directly below the table at `Q18:U18`, and centered the compact buttons across the `A:U` top band.
- Reapplied top-band formatting so `U5:X6` keeps the button-band fill and `U7:X7` keeps the map background fill after status updates.

Validation:

- Synced changed master modules into `Multi User Scanner Queue Testing (version 2).xlsm`.
- Synced changed intake modules into `Intake_Scanning_Test (version 1).xlsm`.
- Synced Indian Trail manager modules/forms into `Indian Trail Inventory Manager.xlsm`.
- Live smoke check with workbook events disabled returned `DL_2026_04_01` from both master and intake.
- Indian Trail disposable smoke test passed map rebuild, local CSV refresh, and all four shared form modes.
- Indian Trail live rebuild/refresh passed and saved `Bay Map`; button macros resolve to the expected public procedures.
- Indian Trail live no-write form construction smoke test passed for Search, Bay Actions, Manual Entry, and SDI modes.
- Indian Trail live-view smoke test passed with summary counts `Occupied=4`, `Preassigned=9`, `SDI=0`, `Exception=0`, `NotOnMap=0`, `Active=13` from the current exported SharePoint list data.
- Indian Trail layout smoke test passed after moving the live table to `Q:U`, hiding the manager panel, and consolidating status below the table. Button size verified around `180.5 x 32`.
- Indian Trail polish smoke test passed after moving the live table up, removing blank table rows, fixing `U5:X7` formatting, and centering the buttons across `A:U`.
- Backups were created under `Backups\VBA Sync Backups`.
- Latest backups include `Intake_Scanning_Test (version 1)__before_vba_import_20260529_095454.xlsm` and `Multi User Scanner Queue Testing (version 2)__before_vba_import_20260529_131536.xlsm`.
- Latest Indian Trail backup: `Indian Trail Inventory Manager__before_vba_import_20260529_151833.xlsm`.
- Latest Indian Trail live-view backup: `Indian Trail Inventory Manager__before_vba_import_20260529_154353.xlsm`.
- Latest Indian Trail compact live-map backup: `Indian Trail Inventory Manager__before_vba_import_20260601_094231.xlsm`.
- Latest Indian Trail polish backup: `Indian Trail Inventory Manager__before_vba_import_20260601_103321.xlsm`.

## Known Follow-Ups

- Add atomic queue claiming in Power Automate or a server-side processor so two processors cannot claim the same queued row.
- Move Power Automate trigger URLs out of VBA source and into a secure configuration pattern.
- Make Indian Trail glass/header routing table-driven instead of relying only on header text.
- Finish SDI/manual bay override/clear/reassign state transitions in the bay assignment workflow.
- Build and publish the `IndianTrailBayAdminAction` Power Automate flow, then paste its HTTP URL into `ITIM_URL_BAY_ADMIN_ACTION` and reimport `modIndianTrailInventoryData`.
- Add a `NeedsReview`/exception queue for unknown glass headers, missing bay assignment, stale revisions, and malformed scans.
- Build a migration path toward Power Apps plus SharePoint/Dataverse as the source of truth, with Excel becoming an export/reporting tool.
