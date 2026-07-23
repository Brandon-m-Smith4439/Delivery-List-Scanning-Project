## v111 - Import Completion and Live Log Performance Fix

- Fixed the Status & Logs page appearing frozen after the scanner database import had already completed.
- Stopped printing the complete per-file import result JSON to PowerShell stdout; the full normalized result remains stored in the private result file used by Recent Delivery List Imports.
- Changed importer console output to one concise summary line containing counts, imported dates, failed dates, and the result-file path.
- Throttled live-status persistence so the complete growing command log is no longer rewritten to disk after every individual output line.
- Kept the in-memory browser status current while persisting recovery status at controlled intervals and once again at completion.
- Added a clear log step after the scanner importer returns and before its normalized result is processed.
- Preserved v110 UNC/SMB publishing, complete per-run logs, notification reliability, and v109 accurate New/Updated/No Changes/Failed history.
- Preserved all scanning, rack, bay, route, stage, audio, notification, and database behavior.
