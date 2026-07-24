# v135 Operations Workflows

This guide covers the operational workflows introduced in Delivery List Scanner v135. It is written for floor testing and Admin verification on the local SQLite deployment.

## Installation

1. Close the scanner server window so `server.py`, `delivery_store.py`, and the SQLite database are not actively being changed.
2. Extract `Delivery_List_Scanner_v135_Changed_Files.zip` into the current v134 project folder and replace the included files.
3. Run `Apply-v135-OperationsPatch.bat` from the project root.
4. Confirm the patch reports success. It creates timestamped copies of the original `server.py` and `delivery_store.py` under `backups\v135-operations-patch`.
5. Start the web app normally. The maintained store applies migration 004 automatically. A verified SQLite backup is created before the schema upgrade.
6. Hard-refresh the browser once so the `20260724-v135` asset cache keys take effect.

The patch may be run more than once. After a successful installation it detects its markers and exits without duplicating routes or import-preservation code.

## Personalized New and Updated review

New/Updated state is not a global line label. It is a set of persistent notice records with a separate receipt for each user.

1. An automatic or manual import creates New or Updated notices for affected list lines.
2. The notification appears as a bottom toast and remains in the bell history.
3. When a user selects an affected list, the list payload and that user's notice flags load in parallel.
4. A compact prompt reports the number of unseen lines.
5. **Review updates** applies the Updated filter and records only that the current notice set has been displayed in this browser session.
6. **Mark reviewed** sends the exact displayed notice IDs to the server.
7. The server verifies that every ID belongs to the selected list, writes receipts for the current user, and returns the remaining pending flags.

A second user is unaffected. A stale or incomplete notice set is rejected so a newer import cannot be silently acknowledged by an older browser view. A no-change import does not clear pending notices.

## Import-run history

Delivery List Management now treats each automation completion time as a selectable run.

- Tabs show run time, status, and the number of affected dates.
- New/Updated, No Changes, Failed, and Running states use distinct status treatments.
- Selecting a bell notification pins the exact results carried by that notification.
- The normal 10-second catalog heartbeat may continue updating list totals, but it does not replace the pinned run.
- Full Import History remains searchable and paginated. Date/time result groups start collapsed to make long histories easier to scan.

## First Scan-page selection

After authentication, the client searches the active list catalog for today's delivery date and a Staging stage. It preloads that list without forcing the user away from Home. The first time Scan is opened, today's Staging list is already selected when available.

## Manual delivery-list orders

Manual entry is available inside **Admin -> Delivery List Management -> Edit Delivery Lists**.

Required values:

- Selected delivery list/date
- Order number and item number
- Quantity
- Route
- Customer
- Glass/product
- Dimensions

The service checks the configured full automation window before insertion. The same order/item cannot already exist on any active list in that window. The selected route determines the destination stage, while Staging and Outbound copies are also created for the same delivery date.

### Manual scanning only

Select **Manual scanning only** when the item cannot produce a normal production barcode. The line receives a `MANUAL-<order>-<item>` identity, a visible manual-only marker, and must be handled through an authorized manual workflow.

Manual entries remain through later automated refreshes. Once a source workbook contains the same order/item, the source version replaces the manual copy and becomes authoritative.

## Internal Reject Tracking

Internal rejects are broken or rejected pieces discovered inside the plant. They are separate from external RM/remake lines imported from delivery lists.

### Log a reject

1. Open **Rejects** from the left navigation.
2. Select **Log Internal Reject**.
3. Enter the order and item. The modal verifies matching active delivery dates.
4. Choose quantity, reason, and break location; add notes when helpful.
5. Submit the reject.

For each active stage copy of the selected order/item, the service:

- reduces scanned quantity by the rejected quantity without going below zero;
- writes an immutable `reject_reset` scan event;
- increments the line's internal reject count and latest reason/location/time;
- reduces or removes matching active rack quantities;
- reduces or clears matching active bay assignments;
- writes an immutable reject history row and an Admin audit event.

The Scan page shows a red INTERNAL REJECT ribbon containing the latest reason, location, and time.

### Reject reasons and locations

Admins manage these values under **Admin -> Reject Tracking Setup**. Removing a value deactivates it for new entries; historical reject records retain their original text.

## Rack details and packing-list history

Rack Overview no longer keeps a selected-rack panel on the right. Clicking a rack opens a modal that preserves all current actions while displaying compact order/item-first rows.

Immediately before a rack packing list opens, v135 records an immutable snapshot containing:

- rack code, name, type, and status;
- delivery date or mixed-date state;
- print time and user;
- line and piece totals;
- every printed order/item row and quantity.

Open **Packing List History** to search and reprint a prior snapshot. A later rack clear, move, return, or reuse does not alter that historical copy.

## Button and Bay Map styling

The v135 stylesheet owns a shared control system for normal, primary, secondary, success, danger, icon-only, hover, active, focus, and disabled states. Feature-specific CSS should reuse these primitives and update the existing owning selector rather than adding a new bottom-of-file override.

The Bay Map scan panel uses the same control system with cleaner spacing, hierarchy, status feedback, and responsive behavior. Existing scanner capabilities remain available.

## Permissions

- View personalized flags/history: `view_lists`
- Log an internal reject: any of `scan`, `manual_adjust`, or `resolve_exceptions`
- Maintain reject catalogs: `view_admin`
- Add manual delivery-list orders: `edit_delivery_lists`
- View/record packing-list history: any of `view_racks` or `export_reports`

Normal list/stage access checks still apply to personalized line notices.

## Verification checklist

1. Sign in as two different users and import a changed list.
2. Confirm both users see the update independently.
3. Review and acknowledge with user A; confirm user B still sees it.
4. Click an older bell notification and wait at least 15 seconds; confirm the selected import run does not change.
5. Open Scan and confirm today's Staging list is selected.
6. Add a manual-only test order, confirm its three workflow copies/route destination, then run a no-change folder import and confirm it remains.
7. Log a one-piece reject on a partially scanned item and verify scan, rack, and bay quantities decrease correctly.
8. Print a rack packing list, modify the rack, and confirm the history snapshot still shows the original print.
9. Check desktop and narrow browser widths for Rack Details, Reject Tracking, Bay Map scanner, and import-run tabs.

## Rollback

- Stop the scanner server.
- Restore `server.py` and `delivery_store.py` from the same timestamp in `backups\v135-operations-patch`.
- Restore the verified pre-migration database backup only when rolling the database itself back. Do not combine an older database with partially retained v135 application files.
- Keep the failed/current database copy and logs until the cause is understood.

Migration 004 is additive. It does not delete pre-v135 business tables or scan history.
