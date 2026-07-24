# v136 Interface Stability Verification

v136 is a frontend-only correction over the v135 operations release. It does not add a database migration and does not require rerunning the v135 operations patch.

## Floor verification

1. Open **Rack Overview** and select multiple rack cards. Each card should open the compact rack-details GUI, and Complete, Uncomplete, Print, move, clear, return, and Not On The Way controls should remain clickable when their workflow state allows them.
2. Open **Reject Tracking**. The page should show a loading message, then history or a clear empty state. Disconnecting the server should produce a visible retry message instead of a blank page. Open **Log Internal Reject**, enter an order/item, and confirm the active-match preview appears before submission.
3. Open **Bay Map** at normal desktop width and fullscreen. The complete Bay Scanner must remain inside the right rail. Step controls must not extend past the card, and the recent-scan table should scroll inside its own area when needed.
4. Open each Admin editor GUI. Confirm the shared header, close button, spacing, form controls, and scroll region are consistent while each editor's existing functionality remains available.
5. In **Delivery List Management**, select older import-run tabs. The selected tab should remain visible and readable after the ten-second live refresh.
6. Confirm Global Search, Print / Export, blue Admin edit controls, primary actions, and destructive actions use the flatter v136 button treatment. Navigation tabs and selectable cards should not receive the raised action-button styling.

## Rollback

v136 changes only browser assets and documentation. Restore the v135 versions of `app.js`, `styles.css`, and `index.html` to roll back the interface changes. The v135 database and operations services do not need to be changed.
