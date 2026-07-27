# v137 Interface and Workflow Verification

v137 is a browser/interface correction over v136. It does not add a database migration and does not require rerunning the v135 operations patch.

## Required floor checks

1. Open **Bay Map** and confirm the Bay Scanner is fully inside the right rail. Verify Add, Remove, target bay, barcode scan, Submit, Undo, Redo, manual entry, last result, and recent scans.
2. Open **Racks**, select Truck 2, and print its packing list from the rack-details GUI. The preview must include every active Truck 2 piece regardless of the delivery date currently selected on the Scan page.
3. Open **Reject Tracking**, open and close **Log Internal Reject** twice, and confirm the button opens the GUI every time.
4. Verify trash buttons show a red trash symbol on white before hover and white on red during hover/focus.
5. Select a list with unseen line changes. Confirm only the bottom-right personalized prompt appears; no second banner should appear below Filters.
6. Select **Review Updates**, verify the New/Updated filter activates, then use **Mark Reviewed** beside Filters.
7. Confirm the Filters summary shows separate RM, Rush, and New/Updated counts.
8. Open Filters on a list with many glass types and confirm the glass choices wrap into a scrollable grid without overlapping.

## Automated validation

The v137 release tests cover JavaScript syntax, unique HTML IDs, CSS parsing and exact-duplicate detection, explicit-only rack print date filtering, repeatable reject-modal ownership, personalized review controls, filter badges, robust glass-type layout, trash-icon states, and Bay Scanner containment selectors.

## Rollback

Restore the v136 copies of `app.js`, `index.html`, `styles.css`, and `notification-center-v135.js`. No database rollback is required.
