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
