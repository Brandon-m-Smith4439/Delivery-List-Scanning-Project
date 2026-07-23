## v112 - Successful No-Change Automation Runs

- Fixed unchanged SQL checks failing with `Cannot bind argument to parameter 'Dates' because it is an empty array.`
- Changed scanner-import date binding to safely accept an empty collection as a defensive fallback.
- Added an explicit pre-import guard so SQL export-and-import mode skips the scanner importer when no changed or pending workbooks exist.
- Added a clear `No changed or pending delivery-list workbooks require scanner import.` log line.
- No-change runs now complete successfully and publish the normal no-change notification instead of a failure notification.
- Preserved changed-workbook imports, pending-import retries, authoritative Recent Delivery List Imports history, complete live logs, UNC publishing, and all scanner data.
