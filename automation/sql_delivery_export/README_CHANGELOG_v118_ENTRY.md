## v118 - Unified Import Center and Append-Only History-Safe Updates

- Moved Import Audit History into the Import / Update Delivery List control center as a fourth tab.
- Removed the separate Import history button and standalone history modal from Delivery List Management.
- Preserved history search, status/date filters, 20/50/100 row paging, newest-first ordering, manual refresh, and collapsed entries.
- Kept history user-driven: it loads when the History tab opens and does not reset the user's scroll position during automatic updates.
- Reduced the notification bell and inherited the same header utility-button styling used by the language, refresh, and fullscreen controls.
- Fixed `scan_events is append-only` import failures with an isolated SQLite reconciliation layer that updates matched line items in place instead of deleting and recreating their identities.
- Preserved scan-event links, scan quantities, rack assignments, bay assignments, Rush/Remake state, and active list metadata during imports.
- Inserts genuinely new source lines, safely retires source-removed history-linked lines, and deletes only unreferenced removed lines.
- Leaves non-SQLite/Azure SQL stores on their native import implementation.
- Preserved live Delivery List Management rerendering, browser catalog sync, detailed logs, schedules, notifications, and workbook integrity validation.
