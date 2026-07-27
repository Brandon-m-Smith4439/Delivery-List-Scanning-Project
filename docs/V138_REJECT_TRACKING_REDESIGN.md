# v138 Reject Tracking Redesign

v138 is a browser/UI correction over the existing v135 reject database and API implementation. It does not add a database migration or require rerunning the v135 operations patch.

## Page workflow

1. Use the summary cards for a quick view of reject activity.
2. Search by order, item, customer, reason, or location.
3. Choose a delivery-date preset or a custom From/Through range.
4. Expand a delivery date to review the individual reject records.
5. Use Clear Filters to return to the complete history.

The date range filters the delivery date attached to each reject record. The logged timestamp remains visible on every record and is used for the Today and Last 30 Days summary calculations.

## Logging workflow

1. Select Log Internal Reject. The window opens immediately.
2. Enter the order and item, then choose Verify Item.
3. Confirm the matched delivery date, quantity, and stages.
4. Choose a reject reason and break location.
5. Add optional investigation notes.
6. Record the reject and restart the affected piece.

The form cannot reuse a stale verification after the order or item changes. Catalog loading errors remain visible inside the open window rather than silently preventing the window from opening.
