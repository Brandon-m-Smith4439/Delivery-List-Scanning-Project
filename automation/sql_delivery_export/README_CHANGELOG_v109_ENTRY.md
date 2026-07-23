## v109 - Accurate Automated Import History

- Connected automated SQL/folder imports to the scanner's authoritative `imports` table instead of relying on an isolated automation status summary.
- Updated the Admin **Recent Delivery List Imports** section immediately after manual or scheduled automation completes.
- Added accurate result labels for **New**, **Updated**, **New + Updated**, **No Changes**, and **Failed** imports.
- Corrected the importer wrapper to read `importedFiles`, `updatedFiles`, `skippedFiles`, and `failedFiles` from the maintained folder importer.
- Stopped requested dates from being marked imported unless the maintained scanner importer actually processed them successfully.
- Preserved pending dates when a file fails or is not processed so a later run can retry it.
- Merged authoritative `last-run.json` results into the web control center so completed runs retain import counts and date details.
- Added a protected recent-import API endpoint and automatic Admin history refresh after automation notifications, page entry, and periodic visible-page checks.
- Preserved the v108 Control Center, notification bell, scanner workflows, scan quantities, rack/bay assignments, routes, audio, and production database.

