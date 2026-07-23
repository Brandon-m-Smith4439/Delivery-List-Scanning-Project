## v120 - Per-User Delivery-List Update Review

- Removed SQL delivery-list automation notices from the Rush/priority popup queue while retaining them in the bell inbox and notification history.
- Added a compact nonblocking toast for new automation results, with a View action and short automatic dismissal.
- Made automation bell notifications open Delivery List Management and show the complete import result carried by that notification.
- Added numbered SQLite migration 003 with backup protection for persistent line-update notices and per-user review receipts.
- Tracks New and Updated lines independently for each signed-in user on today and future delivery dates.
- Keeps unseen changes through repeated no-change imports and clears them only when that user explicitly selects Mark reviewed for the selected list.
- Creates a new notice when a line materially changes again after an earlier version was reviewed.
- Excludes removed/retired lines from the New/Updated review queue.
- Added a Scan-page update banner with Review updates and Mark reviewed actions plus unseen counts in list metadata.
- Preserved append-only scan history, scanned quantities, racks, bays, Rush/Remake state, import history, schedules, and authoritative latest-import results.
