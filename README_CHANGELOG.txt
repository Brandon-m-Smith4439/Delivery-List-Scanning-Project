Scanning Project UI/backend update - v14

Updated in this package:

1. Print / packing list polish
- Enlarged the Date write-in area in the Checked By / Date box on printed delivery lists.
- Kept the larger delivery-list print font and current pagination behavior.
- Added an RM flag column to rack packing lists so remake pieces are obvious on printed packing paperwork.

2. Outbound scan safety
- Outbound piece scans are now blocked when the matching staging row has not been scanned.
- Outbound piece scans are also blocked when the matching staging row has no rack/truck transportation method assigned.
- Added an in-app Outbound Safety Check popup that lets the user override the block and assign a transportation method.
- Override actions are written to the audit trail.
- The old silent auto-stage behavior is no longer used for normal outbound scans; auto-stage only happens as part of an explicit override.

3. Top-right user menu
- Simplified the account control to a less-oval rounded rectangle.
- Simplified the dropdown so it only shows Sign out.
- Added smoother dropdown styling.

4. Old Bay Review popup
- Revamped the old bay popup with clearer summary cards, better order cards, bay pills, and a cleaner sticky footer.
- Changed wording from Old Bay Orders to Old Bay Review.

Validation completed:
- server.py passed Python compile check.
- delivery_store.py passed Python compile check.
- app.js passed node --check.

Install note:
Back up your current project folder first, then replace the matching files with the files in this package.

## v15 - Print wrap / stale bay / user menu polish

- Prevented long Job Nr. and Customer values from wrapping on printed delivery-list rows, which stops those rows from pushing one list page onto an extra physical print page.
- Kept the print page number only at the top-right of each delivery-list page.
- Moved the Old Bay Review days counter into a smaller pill beside the order/customer information.
- Added click-away and Escape-to-close behavior for the top-right user sign-out dropdown.

