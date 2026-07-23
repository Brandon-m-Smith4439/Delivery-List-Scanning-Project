# Delivery List SQL Automation Runtime v121

This folder is installed to `C:\DeliveryListAutomation\Scripts` by the v121 setup package.

## v121 changes

- Centers the delivery-list automation toast along the bottom of the page.
- Keeps the toast visible for 20 seconds unless dismissed or opened.
- Marks current bell notifications read when the bell menu opens.
- Removes the manual Mark all read control and Mark read item wording.
- Stamps all newest-run delivery-list results, including No Changes, with the current check completion time.
- Sends exact per-user notice IDs when Mark reviewed is selected.
- Reloads and rerenders the selected list after review so New Line and Updated Line labels disappear immediately for that user.
- Retains Rush separation, notification history, per-user current/future review state, authoritative latest imports, integrated Import History, live catalog synchronization, append-only-safe imports, full logs, and scheduled tasks.

The runtime continues to query A+W read-only and uses the scanner's maintained import workflow.
