# v139 Dropdown, Internal Reject, and Import History Update

## Scan filters and delivery dates

- Every maintained single-value selector uses the shared custom dropdown and the existing subtle collapse/open swoosh cues.
- The Scan delivery-date selector shows an alert icon beside dates containing New/Updated notices that remain unreviewed for the signed-in user.
- Internal Rejects are available as a Status filter, use a red `IR` flag in line rows, and have a dedicated `IR` counter in the Filters summary.
- The unlabeled fourth Filters counter was removed.

## Internal reject history and notification

- Reject history date filters now apply to the date the reject was logged, not the delivery date.
- History is grouped by reject/logged date. Each row still shows the affected delivery date, reason, break location, user, notes, quantity, and exact logged time.
- Creating an internal reject publishes a persistent bell notification and a nonintrusive bottom-right alert. The alert remains visible for 30 seconds unless acknowledged sooner.

## Delivery-list import runs

- Delivery List Management loads all automation notifications from the current local day and presents five runs per page.
- The current-day view resets when the browser date changes. Older results remain available in Automation Control Center history.
- Automation history is presented as nested collapsible groups: day, run time, then individual delivery-list results.

## Maintenance

- The new behavior reuses the existing custom-select, notification, line-flag, import-notification, and details/toggle systems.
- No new database migration is required. Existing v135 operations tables and routes remain the maintained backend.
