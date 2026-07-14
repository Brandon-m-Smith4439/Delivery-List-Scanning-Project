# Delivery List Scanner - v047 Manual Edit and CPU Route Resolution Fix

Date: 2026-07-14

## v047 Changes

### Manual line edits now persist correctly

- Saving a manual edit now updates the matching copies of that item across the same delivery date instead of changing only one isolated stage row.
- Shared business fields now remain consistent across Staging, Outbound, and the applicable receiving stage:
  - Order Nr. and Item Nr.
  - barcode
  - quantity
  - dimensions
  - customer
  - route
  - Job Nr.
  - product
  - process and queue states
- Stage-specific scanned quantity remains stage-specific and is not copied to the other stages.
- Location edits now use the newly saved line-item values instead of validating against the stale pre-edit row.
- The app refreshes the delivery-list collection after saving and displays a polished success notice.

### Route changes move the item to the correct receiving list

- Changing a line from CPU to Indian Trail now stores an explicit `IT` route so a customer-route fallback cannot silently change it back to CPU.
- The matching receiving-stage record is moved between Customer Pickup, Indian Trail, Greenville, DTC, or a custom route list while retaining its scan, rack, bay, and audit references.
- Staging and Outbound copies remain available because those stages contain all destinations.
- Quantity reductions are blocked when another stage has already scanned more pieces than the proposed new quantity.

### Revised CPU routing order

1. An explicit ROUTE value is authoritative.
2. Any ROUTE value containing `CPU` is treated as CPU, regardless of Job Nr. wording.
3. When ROUTE is blank, Job Nr. `CPU-IT` or `CPU-INT` routes to Indian Trail.
4. When ROUTE is blank, Job Nr. `CPU-Air` routes to Customer Pickup.
5. A matching customer-route database rule is used for other blank-route CPU jobs.
6. A generic CPU mention in Job Nr. defaults to Indian Trail when no route rule resolves it.

This keeps Job Nr. detection available without allowing generic CPU text to override the ROUTE column or customer routing database.

## Exact Code Locations in v047

### `app.js`

- Client-side route interpretation: `inferredRoute()` near line 2760.
- Manual route selector values: `manualEditRouteOptions()` near line 14310.
- Manual-edit save, full list refresh, and success notice: `saveManualLineItem()` near line 14542.

### `delivery_store.py`

- ROUTE-column normalization: `normalize_route_column()` near line 390.
- Job Nr. CPU pattern handling: `job_number_route_hint()` near line 411.
- Shared route-category resolution: `inferred_route()` near line 422.
- Customer-route database application during imports: `apply_customer_route_rules_to_payload()` near line 4789.
- Matching stage-copy lookup: `manual_edit_sibling_rows()` near line 6547.
- Receiving-list movement after route edits: `sync_manual_route_membership()` near line 6650.
- Manual line-item save and stage synchronization: `update_line_item()` near line 6716.

### Cache references

- `styles.css?v=20260714-v047`
- `app.js?v=20260714-v047`

## Validation Performed

- `node --check app.js`
- `python3 -m py_compile delivery_store.py server.py scanner_config.py`
- Server store creation/import check
- Route-rule matrix covering explicit CPU, CPU-IT, CPU-INT, CPU-Air, generic CPU, and explicit Indian Trail
- Customer-route database test showing generic CPU follows a matched customer rule
- Temporary SQLite manual-edit test proving shared fields update across stages
- Temporary SQLite route-movement test proving CPU to Indian Trail and Indian Trail back to CPU both move the receiving record correctly

---

# Delivery List Scanner - v046 Rack Outbound, Destination Override, and Route Fixes

Date: 2026-07-14

## v046 Changes

### Rack-barcode Outbound scans

- Rack barcode scans now match the Outbound line by delivery date, Order Nr., and Item Nr. even when a source identifier differs between list stages.
- A successful rack barcode scan now consistently updates every dependent Outbound workflow:
  - Outbound scanned quantity
  - scan history and audit history
  - Indian Trail bay preassignment
  - In-Transit counts and manifest status
  - Indian Trail missing-Outbound safety checks
  - rack status and the rack-level Outbound scan timestamp
- Duplicate rack scans preserve the original departure time instead of replacing it with a later duplicate-scan time.

### Rack-level date and time

- Removed the individual piece timestamp column from the In-Transit Manifest.
- Each rack or truck group now shows one **Scanned outbound** date and time from the rack barcode scan.
- The Racks Overview card and selected-rack detail panel now show the same rack-level Outbound timestamp.
- Removed the old per-piece timestamp query and styling to keep the manifest faster and easier to read.

### Indian Trail missing-Outbound popup

- The missing-Outbound warning now opens the custom override popup immediately, before the Scan page refreshes Last Scan and Recent Scans.
- This is used by both scanner-entered barcodes and required Order Nr. / Item Nr. manual scans.
- Selecting Yes opens the custom bay selector; selecting No cancels without changing received quantity or bay assignment.

### Wrong rack destination override

- Scanning an item onto a rack assigned to a different destination now opens a custom popup showing:
  - rack code
  - rack destination
  - item destination
  - order/item and customer
- The operator can cancel or explicitly override the destination check.
- An accepted override records the rack's physical destination on that rack item so the rack remains internally consistent and can still be completed.
- The same override is supported by the main Staging scanner and the Rack-page scanner.

### CPU and destination routing

- CPU, DTC, Greenville, and custom routing now use the imported **ROUTE** column first.
- When ROUTE is blank, the customer-route database is used against the Customer field only.
- Job Nr. text is no longer used to infer CPU. A Job Nr. containing `CPU` can therefore remain on the Indian Trail route when the ROUTE column/customer rule says Indian Trail.
- Scan-page route filters and counts now use the same corrected route logic.

## Exact Code Locations in v046

### `app.js`

- Route interpretation: `inferredRoute()` near line 2760.
- Rack Overview Outbound timestamps: `renderRackBoardCard()` and `renderSelectedRackDetails()` near lines 3927-4080.
- Wrong-destination custom popup: `showRackDestinationOverrideDialog()` near line 4166.
- Rack-page destination override retry: `submitRackScan()` near line 4190.
- Scan-page Indian Trail popup and destination override handling: `processScan()` near line 6372.
- In-Transit rack-level timestamp rendering: `transitManifestRackGroups()` and `transitManifestHtml()` near lines 7191-7310.

### `delivery_store.py`

- Customer-only fallback route matching: `default_customer_route()` and `inferred_route()` near lines 341-420.
- Customer route database application: `route_from_customer_rules()` near line 4748.
- Main Staging destination-override response and persistence: `record_scan()` near line 5396.
- Rack-page destination-override response and persistence: `scan_item_to_rack()` near line 7526.
- Rack destination override calculation: `rack_destinations_from_items()` near line 7727.
- Rack barcode Outbound processing and departure timestamp: `scan_rack_outbound()` near line 8156.
- In-Transit rack timestamp and robust Outbound matching: `_indian_trail_in_transit_payload()` near line 8276.

### `styles.css`

- Rack-level timestamp polish: v046 block near line 28727.

### Cache references

- `styles.css?v=20260714-v046`
- `app.js?v=20260714-v046`

## Validation Performed

- `node --check app.js`
- `python3 -m py_compile delivery_store.py server.py scanner_config.py`
- Temporary SQLite rack-barcode test with intentionally mismatched source IDs
- Outbound quantity, departure timestamp, In-Transit, and Indian Trail safety-gate test
- Main Scan-page and Rack-page destination mismatch/override tests
- ROUTE-column and customer-route database classification test proving Job Nr. `CPU` text does not force Customer Pickup
- Native popup audit confirming no `alert()`, `confirm()`, or `prompt()` calls

---

# Delivery List Scanner - v045 Transit Timestamps, Rush Dates, and Stage Memory

Date: 2026-07-14

## v045 Changes

### In-Transit piece timestamps

- Added an **Outbound Scanned** column to the Indian Trail In-Transit Manifest.
- Each individual in-transit quantity now shows its own outbound scan date and time.
- Multi-quantity line items display `Piece 1`, `Piece 2`, and so on with separate timestamps.
- Items that reached transportation without a recorded Outbound scan clearly display `Outbound scan not recorded` instead of inventing a time.

### Rush delivery date

- Rush broadcast popups now include the delivery date in the alert message and the details grid.
- The backend stores the delivery date in the persistent Rush notification payload so every user sees the same date.
- The immediate Rush result also returns `matchedDeliveryDate` for future confirmation-popup use.

### Indian Trail missing-Outbound workflow

- Hardened the Scan page and Bay Map safety workflow into two custom steps.
- Step 1 clearly states that the item has not been scanned Outbound and asks whether to override.
- Selecting **No** cancels the scan without changing received quantity or bay assignment.
- Selecting **Yes** opens a second custom popup asking which bay should receive the item.
- The same two-step flow is used by regular and manual scans on both Indian Trail scanning surfaces.

### Preserve the current stage when changing dates

- Changing the delivery date on the Scan page now keeps the operator in the same stage whenever that stage exists on the selected date.
- The scanner profile is used as a fallback match before the app falls back to the first available stage.
- Changing dates no longer automatically returns the operator to Staging.

## Exact Code Locations in v045

### `app.js`

- Indian Trail two-step Outbound override: `showIndianTrailOutboundReceiveOverride()` near line 6168.
- Rush popup delivery-date display: `showRushAlert()` near line 6671.
- In-Transit timestamp rendering: `transitManifestRowHtml()` near line 7062.
- Delivery-date stage preservation: `deliveryDateSelect` change handler near line 14873.

### `delivery_store.py`

- Per-piece outbound scan timestamps: `_indian_trail_in_transit_payload()` near line 8178.
- Rush notification delivery date: `mark_sdi()` near line 9811.

### `styles.css`

- In-Transit timestamp styling: v045 block near line 28727.

### Cache references

- `styles.css?v=20260714-v045`
- `app.js?v=20260714-v045`

---

# Delivery List Scanner - v044 Bay Scan Workflow and Custom Dialogs

Date: 2026-07-14

## v044 Changes

### Custom webapp dialogs everywhere

- Removed the remaining native JavaScript `alert()`, `confirm()`, and `prompt()` calls so the browser no longer displays messages such as `IP address says:`.
- Added reusable custom confirmation and text-entry dialogs that match the webapp styling.
- Added a custom confirmation and polished success popup when marking a rack returned.
- Added custom confirmation and success feedback for clearing an individual rack and clearing a complete rack set.
- Converted destructive Admin, route, user, delivery-list, rack, and Bay Map actions to custom dialogs.
- Removed the browser-native unsaved-changes prompt. Print-page lifecycle listeners remain, but they do not display a browser confirmation.

### Required manual-scan fields

- Manual scans now require both Order Nr. and Item Nr. on the main Scan page.
- Bay Map manual scans also require both Order Nr. and Item Nr.
- Manual scans use the same processing paths, validation, bay assignment, history, and undo/redo behavior as scanner-entered barcodes.
- Manual events remain clearly marked as manual in scan and Bay Map history.

### Indian Trail Outbound safety override

- Indian Trail scans now check that the item was scanned Outbound before receiving it.
- When Outbound is missing, a custom safety dialog identifies the item and asks whether to override the requirement.
- Confirming the override requires choosing the destination bay.
- Canceling stops the scan without changing received quantity or bay assignments.
- The same safety workflow is used by the Scan page and Bay Map Add To Bay mode.

### Timed placement guidance

- Successful Indian Trail receives show a 12-second placement popup with the suggested or preassigned bay.
- The operator can override the destination from the popup before it closes.
- Oversize glass attempts to suggest an oversize bay and clearly tells the operator to verify placement.
- The popup distinguishes a normal receive from an already-received item being returned to a bay.

### Bay Map scanner repair and manual scanning

- Reworked the Bay Map scanner around one shared scan function for regular and manual scans.
- `Add to bay` receives or returns the item to the selected bay.
- `Remove from bay` scans the item out of whichever bay currently holds it; a stale Add target no longer blocks a valid scan-out.
- Add To Bay can return an already-received item to a bay without increasing Indian Trail received quantity.
- Bay Map manual scanning now uses required Order Nr. and Item Nr. fields rather than the former Manual Assign workflow.
- Undo and redo are retained for both Add and Remove actions.
- Bay scanning permissions allow Indian Trail receiving users to move, clear, restore, and scan items out without requiring a separate Bay Map management permission.

### Move previously scanned items

- Added a bay-move selector to Last Scan.
- Added a Move column to Recent Bay Scans.
- Added a Move column to All Bay Scans.
- Moving an item uses a custom confirmation and updates the live Bay Map and history.
- All Bay Scans now loads up to 250 recent bay events and includes action, order/item, bay, customer, reason, user, timestamp, and movement controls without horizontal scrolling.

### Bay movement timestamps and job details

- Scan-in and scan-out actions now create dated Bay Map events.
- Manual scan-in and scan-out actions are distinguishable in the event history.
- Selected-bay Job details show when each present item was scanned into the bay.
- The Job summary shows the most recent scan-in time for that Job Nr.
- Scan-out records preserve the source bay, user, date, time, order, item, and reason.

### Sticky scanner-panel fit

- Reduced the normal and fullscreen gap below the application header so the Scan and Bay Map panels sit slightly higher.
- Kept a small safety gap and bottom clearance so the full scanner panel fits between the header and bottom of the viewport.

## Exact Code Locations in v044

Line numbers below refer to the files in this package. Search by the function or element name if later edits shift the lines.

### `app.js`

- Sticky Scan/Bay Map panel position: `syncFullscreenStickyPanelOffset()` near line 1853.
- Rack return custom confirmation and success: `returnRack()` near line 4239.
- Rack reset confirmations: `clearRack()` and `clearRackSet()` near lines 4307-4357.
- Indian Trail missing-Outbound override: `showIndianTrailOutboundReceiveOverride()` near line 6160.
- Timed placement and bay override popup: `showIndianTrailPlacementPrompt()` near line 6235.
- Main Scan-page barcode flow: `processScan()` near line 6302.
- Reusable polished edit/success popup: `showActionFeedback()` near line 6547.
- Selected-bay item timestamps: `selectedBayJobItemsHtml()` near line 7674.
- Bay Map Last Scan and Recent Scan movement controls: `renderBayLastScanCard()` and `renderBayRecentActions()` near lines 8428 and 8463.
- Shared Bay Map Add/Remove scan workflow: `runBayScan()` near line 8594.
- Bay Map required manual scan: `submitManualBayScan()` near line 8676.
- All Bay Scans history GUI: `openBayAllScansModal()` near line 9174.
- Reusable custom confirmation dialog: `confirmWebAppAction()` near line 12542.
- Reusable custom text prompt: `promptWebAppAction()` near line 12643.

### `index.html`

- Main Scan-page manual Order/Item fields: lines 426-441.
- Bay Map Add/Remove selector, target bay, barcode box, and manual scan: lines 680-738.
- Bay Map Last Scan and Recent Scan movement controls: lines 740-772.

### `delivery_store.py`

- Selected-bay Job fulfillment and scan-in timestamps: concrete `get_bay_job_details()` implementation near line 7058.
- Dated Bay Map event/history records and active assignment data: concrete `get_bay_events()` implementation near line 7195.
- Indian Trail receive, Outbound safety, returned-item override, and bay assignment: concrete `receive_indian_trail_scan()` implementation near line 8700.
- Bay scan-out and timestamp logging: concrete `scan_out_bay_item()` implementation near line 9299.

### `server.py`

- Multi-permission helper used by Bay Map scan actions: `require_any_permission()` near line 842.
- Indian Trail receive endpoint: near line 1536.
- Move, clear-assignment, restore-assignment, and scan-out endpoints: approximately lines 1560-1601.

### `styles.css`

- v044 custom dialogs, timed placement popup, movement selectors, Bay history layout, timestamps, and scanner-panel fit: block beginning near line 28306.

## Validation

- `node --check app.js`
- `python3 -m py_compile delivery_store.py server.py scanner_config.py`
- HTML audit: all 268 element IDs are unique and all required manual/Bay Map scan controls are present.
- CSS parse audit completed with zero parse errors.
- Native browser dialog audit found zero `alert()`, `confirm()`, or `prompt()` calls in the webapp source.
- Temporary SQLite workflow testing verified:
  - missing-Outbound scans return the override requirement
  - confirmed override receives into the selected bay
  - scan-out records the bay and timestamp
  - an already-received item can be returned to another bay without increasing received quantity
  - manual scan-in and scan-out events remain distinct
  - Job fulfillment and scan-in timestamps update correctly
  - moving an assignment updates the current bay and event history
- Automated visual browser navigation could not run because this execution environment blocks localhost browser navigation. Static validation and direct backend lifecycle tests passed.

### Cache references

- `styles.css?v=20260714-v044`
- `app.js?v=20260714-v044`

---

# Delivery List Scanner - v043 Wrong-List Guidance and Rush Broadcast Alerts

## v043 Changes

### Wrong delivery-list scan guidance

- Wrong-list errors now identify the matching **delivery-list date only** instead of listing every matching stage on that date.
- Last Scan and Recent Scans now use the concise instruction `Check delivery list date <date>`.
- All Scans normalizes both new and previously saved wrong-list errors so older stage-heavy messages also display only the relevant date.
- Indian Trail receiving now returns the same date-focused guidance in its immediate scan error.

### Check-column alignment

- Rebuilt the success, notice, and error symbols as centered pseudo-icons inside their colored circles.
- Centered the entire Check column in Recent Scans, All Scans, and Bay Map scan history.

### One-time Rush alerts

- Added persistent Rush notifications stored in SQLite.
- Every active user receives one polished production-priority popup for each newly submitted Rush.
- The submitting user keeps the existing Rush success confirmation and is not interrupted by a duplicate alert.
- Other users receive the alert within the normal seven-second notification poll, even when viewing Home, Racks, Bay Map, Scan, or Admin.
- Alerts include Job Nr., order, customer, priority-item count, and submitting user when available.
- Each user acknowledges each alert once; acknowledgment is shared across that user's sessions.
- Rush alerts expire after 24 hours so users returning much later are not shown stale priorities.
- Remakes do not create Rush broadcasts.

### Cache references

- `styles.css?v=20260714-v043`
- `app.js?v=20260714-v043`


## v042 Changes

### Bay Map in-transit rack summary

- The `Racks:` line now includes every transportation rack currently carrying Indian Trail pieces, including `T`, `T2`, and other truck-type racks.
- Removed the five-rack display limit and allowed the rack list to wrap so every active in-transit rack remains visible.
- The quantities are based on pieces still in transit, so fully received racks are removed from the Bay Map transit summary.

### Received item locations

- Added cross-stage receipt detection for Indian Trail, Customer Pickup/CPU, DTC, and Greenville.
- Once an item has been scanned at one of those receiving stages, its Location column displays `Received` instead of its former rack, truck, or bay location on every matching scan list.
- Global item search now also reports the current location as `Received` after one of those receiving scans.
- Added a dedicated green Received location badge.

### Rack received and returned lifecycle

- Racks that remain marked `In Transit` but whose complete contents have been scanned at their destination now display `Received`.
- Received racks remain visually grayed out and unavailable for reuse until they are explicitly marked returned.
- Added a `Received` rack-status filter.
- The Outbound transportation-status selector now distinguishes `Received - awaiting return` from `On the way`.
- Added a visible `Mark Returned` button directly on received rack cards in the Racks overview, while preserving the existing selected-rack return action.
- Marking a rack returned clears its active rack contents and resets it for staging reuse.

### Cache references

- `styles.css?v=20260714-v042`
- `app.js?v=20260714-v042`

## Validation

- `node --check app.js`
- `python3 -m py_compile delivery_store.py server.py scanner_config.py`
- Temporary SQLite lifecycle test verified:
  - truck and standard racks both appear in the Indian Trail in-transit summary
  - a fully received rack derives the `Received` state while its stored lifecycle remains `In Transit`
  - matching staging items receive the cross-stage `received` flag
  - marking the rack returned resets it to `Open` with zero active rack contents

---

# Delivery List Scanner - v041 Scanner History, Outbound Status, and Bay Fulfillment

## v041 Changes

### Scan-panel controls

- Condensed the Indian Trail Bay Assignment control to the same compact footprint as the Staging Transportation Method control.
- Added a compact Outbound Transportation Status selector that is view-only and does not assign pieces to racks.
- The Outbound selector groups racks by rack set and shows whether each rack is still being built, complete and waiting for Outbound, or already scanned Outbound.

### Scan errors and history

- Replaced the confusing `BAD SCAN format - No unique delivery-list match` result with a clear wrong-list message.
- When possible, the detailed error identifies the other delivery date or stage where the item appears.
- Kept Last Scan and Recent Scans concise while giving the All Scans GUI the complete message, reason, raw barcode, resolved barcode, user, station, and time.
- Enlarged the All Scans GUI and removed horizontal scrolling by using a fixed, wrapping table layout.
- Separated delivery-list imports from updates with different event badges and row accents.
- Import and update events now show their source file/details and a successful check mark when completed.

### Bay Map job fulfillment

- Replaced the selected-bay Filled Percentage summary with Job completion and Fulfillment counts.
- Jobs in a selected bay can now be expanded to show every order/item required for that Job Nr.
- Each order item shows the quantity currently in the bay and exactly how many pieces are still missing.
- Job details load only when a bay is selected, keeping the main Bay Map refresh lightweight.

### Spanish coverage

- Added Spanish translations and dynamic quantity translations for the new scanner, scan-history, Outbound status, and Bay fulfillment interface.

### Cache references

- `styles.css?v=20260714-v041`
- `app.js?v=20260714-v041`

## Validation

- `node --check app.js`
- `python3 -m py_compile delivery_store.py server.py scanner_config.py`
- Temporary SQLite wrong-list test verified the new friendly error and other-list hint.
- Temporary SQLite import/update test verified distinct successful event types.
- Temporary SQLite Bay Map test verified Job fulfillment `1/3` and missing item quantity `2` after receiving one piece.
- HTML ID and required-control checks.

---

# Delivery List Scanner - v040 Scanner Header and Sticky Clearance Polish

## v040 Changes

- Added a little more breathing room below the sticky application header for both the Scan page and Bay Map scanner panels in normal and fullscreen modes.
- Reused the live measured header height for normal sticky positioning instead of relying only on older fixed offsets.
- Fixed the Bay Map `Indian Trail Route` header band so it fills the scanner card from the left edge through the right edge.
- Removed the width cap that caused the navy route header to stop short on the right side.
- Balanced the Outbound, in-transit, and Received columns inside the compact route header.
- Corrected the compact in-transit wording for a single piece.
- Cleaned the Bay Map scanner HTML indentation around the route header.
- Updated cache references to `styles.css?v=20260714-v040` and `app.js?v=20260714-v040`.

## Validation

- `node --check app.js`
- `python3 -m py_compile delivery_store.py server.py scanner_config.py`
- HTML parsing and required Bay Map scanner element checks
- CSS checks for the live normal/fullscreen sticky offsets and full-width route band

---

# Delivery List Scanner - v039 Fullscreen Scanner Panel Clearance

## v038 Changes

- Preserved the existing fullscreen-return prompt after printing is completed or cancelled.
- Added parent-window monitoring for the temporary print window. Closing the print page with its window close button is now detected even when the browser does not fire `afterprint`.
- Added `pagehide` and `beforeunload` completion signals to every server-generated print page and the Statistics print page.
- When a print page closes, the main webapp is focused and automatic fullscreen restoration is attempted. If the browser blocks automatic fullscreen, the existing polished one-click `Return to fullscreen` popup appears.
- Prevented duplicate fullscreen prompts when more than one print lifecycle event fires.
- Updated cache references to `styles.css?v=20260714-v038` and `app.js?v=20260714-v038`.

Date: 2026-07-13

## Summary

This package builds on v036. It fixes the Bay Map Rush / Remake GUI so users can paste a complete Job Nr. label, adds a reusable polished success popup, and improves printing from fullscreen mode.

## Changed Files

- `app.js`
- `delivery_store.py`
- `server.py`
- `styles.css`
- `index.html`
- `README_CHANGELOG.md`

## Changes

### SDI Job Nr. lookup

- The SDI field now accepts a full Job Nr. such as `88418245M LOGAN FARMS 51`.
- It also accepts an SO number, order number, or barcode.
- Spacing and punctuation differences are normalized when matching a Job Nr.
- When a Job Nr. is matched, every line item belonging to that job on the selected active delivery list is updated together.
- Existing Bay Map assignments for those items are updated to the Rush / Remake override state so the change is visible throughout the Bay Map.
- Clearing by Job Nr. removes the special process state and restores matching bay assignments.
- Replacing the prefilled SDI value with a different Job Nr. now searches for the pasted value instead of silently applying the change to the previously selected assignment.
- The SDI input label, placeholder, and helper text now explain all accepted input formats.

### Polished success popup

- Replaced the native Rush / Remake print confirmation with a custom webapp-styled success popup.
- The popup shows the matched Job Nr. or order, customer, and number of items updated.
- Rush and Remake results provide the correct print action directly in the popup.
- The popup component is reusable for other important edits in future versions.
- Added matching Spanish translations for the new interface text.

### Printing and fullscreen

- Print pages opened by the app now use a managed print window.
- After print preview is closed or cancelled, the temporary print window closes automatically.
- The main webapp is focused again after printing.
- When the app was fullscreen before printing, it attempts to return to fullscreen automatically.
- Browsers that block automatic fullscreen restoration show a polished one-click `Return to fullscreen` popup instead.
- Applied the managed workflow to delivery-list packages, Rush/Remake sheets, rack packing lists, stale-bay reports, customer manifests, and the Statistics PDF report.

## Validation

- `node --check app.js`
- `python3 -m py_compile delivery_store.py server.py scanner_config.py`
- Temporary SQLite test: pasted full Job Nr. marked two matching items as Rush, updated both Bay Map assignments, and cleared both successfully.
- Printable HTML render test verified the after-print notification and automatic print-window close workflow.

## Cache References

- `styles.css?v=20260713-v037`
- `app.js?v=20260713-v037`

## v039 Changes

- Fixed the Scan-page scanning panel overlapping the sticky application header while fullscreen is active.
- Fixed the Bay Map scanning panel overlapping the header while fullscreen is active.
- Added live header-height measurement so the scanner offset adjusts when header controls wrap or the fullscreen viewport changes size.
- Kept the existing non-fullscreen sticky-panel positions unchanged.
- Updated cache references to `styles.css?v=20260714-v039` and `app.js?v=20260714-v039`.
