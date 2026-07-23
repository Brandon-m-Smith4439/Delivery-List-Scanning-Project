## v113 - Workbook Integrity, Current Import Audit, and Deleted-List Recovery

- Fixed SQL-generated XLSX files prompting Microsoft Excel to repair the workbook and then opening with an empty worksheet.
- Moved worksheet properties into the SpreadsheetML sequence required by Excel and changed Order, Item, and Qty to native numeric cells.
- Added ZIP integrity, required-part, XML, relationship, style-count, worksheet-order, and scanner-column validation before a workbook can be published.
- Added a workbook format marker and published-file SHA-256 hash so older, damaged, replaced, or repaired workbooks rebuild automatically even when A+W rows are unchanged.
- Changed SQL export-and-import runs to audit every A+W source date and report current No Changes results without repeatedly reimporting complete unchanged dates.
- Added `Last checked` to Recent Delivery List Imports and refreshes the Admin page `Last updated` time after automation checks.
- Fixed skipped maintained-import results that omitted `deliveryDate` by deriving the date from the delivery-list filename.
- Added deleted-stage recovery: missing expected scanner lists trigger the maintained exact-date folder-import workflow, preserving all scanner business rules and avoiding direct table edits.
- Preserved scan quantities, routing, racks, bays, notifications, complete live logs, UNC publishing, and existing automation settings.
