## v117 - Live Delivery Management Refresh and Stable Import History

- Fixed Delivery List Management so the original scanner overview rerenders immediately when the live delivery-list catalog changes.
- Preserved the current page, selected delivery date, selected stage, and active scan workflow while updating list metadata.
- Refreshes the original Admin or Home list renderer only when the catalog signature changes; no synthetic Date or Stage change events are fired.
- Removed the 15-second Import Audit History auto-refresh that was resetting scroll position and expanded/collapsed state.
- Import Audit History now refreshes only when opened, manually refreshed, searched, filtered, paged, page size is changed, or safely synchronized after closing.
- All Import Audit History entries now start collapsed.
- Marks the Refresh button when a new automation result arrives while the history window is open instead of replacing the user's current view.
- Added exact failed-workbook names, dates, and error messages to the command log.
- Saves the complete normalized result to `C:\DeliveryListAutomation\State\last-import-result.json` whenever failures occur.
- Adds repair guidance for failed XLSX/XLSM files: rebuild them with Query SQL, Export & Import on a SQL-authorized computer before retrying Folder Import Only.
- Preserved the dedicated paginated Import Audit History GUI, notification bell, scheduled automation, scan-preservation logic, and database-busy retry behavior.
