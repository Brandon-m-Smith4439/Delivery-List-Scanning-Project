<!-- File: automation/crystal_delivery_export/README.md -->
# Automated A+W Crystal Delivery List Export

This package automates the existing A+W `DeliveryList.rpt` workflow without automating mouse clicks and without installing a third-party report scheduler.

It uses the SAP Crystal Reports .NET runtime already installed on the Windows computer, supplies the `DeliveryDate` parameter, logs into `SQLAWGLASS / BFSMAIN`, exports XLSX workbooks, publishes them through the UNC folder, and then invokes the Delivery List Scanner's existing folder importer.

## Security

Do not put the SQL password in this repository or send it through chat. Setup prompts for it locally and stores it with Windows DPAPI at:

`C:\DeliveryListAutomation\Secrets\aw-sql-password.txt`

That encrypted value can only be decrypted by the same Windows user on the same computer. The scheduled tasks therefore run only while that user is logged on during this local pilot.

## Known report settings

- Report source: `\\bfs-awbppw01\Trans\Reports\BFS\CR\DeliveryList.rpt`
- Crystal parameter: `DeliveryDate`
- Provider shown by A+W: `SQLServer OLEDB`
- SQL server: `SQLAWGLASS`
- Database: `BFSMAIN`
- Initial SQL user: `bsmith`
- Publish folder: `\\bfs.buildersfirstsource.com\Departments\BAREFOOT-INSTALL\Glass Production\Brandon\Temp Delivery Lists`

## Setup

1. Run this package from the active Delivery List Scanner project folder—the folder containing `server.py`, the `backend` package, and the existing `data` folder.
2. Double-click `Setup-DeliveryListAutomation.bat`.
3. Enter the A+W SQL password when prompted. It is not displayed and is not saved as plain text.
4. Setup creates:
   - `C:\DeliveryListAutomation\Reports`
   - `C:\DeliveryListAutomation\Staging`
   - `C:\DeliveryListAutomation\Logs`
   - `C:\DeliveryListAutomation\Failed`
   - `C:\DeliveryListAutomation\Secrets`
   - `C:\DeliveryListAutomation\State`
   - `C:\DeliveryListAutomation\Scripts`
5. Setup tests both 64-bit and 32-bit Windows PowerShell and records the one that can load the installed Crystal runtime.
6. Double-click `C:\DeliveryListAutomation\Run-Test.cmd` and enter a delivery date known to contain report rows.
7. Confirm an XLSX file named like `Delivery List 2026-07-22.xlsx` appears in the UNC destination folder.
8. Confirm the scanner imported or updated the delivery list.
9. Double-click `Install-DeliveryListAutomationTasks.bat` to create the two local scheduled tasks.

## Schedule

The checked-in configuration uses:

- Incremental export every 60 minutes: two days back through fourteen days forward.
- Full reconciliation daily at 5:15 PM: seven days back through ninety days forward.
- Immediate scanner folder import after each non-test export run.

The Crystal report accepts one `DeliveryDate`, so one report execution is required for every date in the selected range. The pilot deliberately starts with a limited hourly horizon to reduce load on the A+W SQL server. Adjust the values in `C:\DeliveryListAutomation\Scripts\crystal-export.config.json` after measuring the runtime and confirming the acceptable date horizon with IT.

## Safe publishing

Each workbook is exported locally first, validated as an XLSX file, copied to the destination with a `.partial` suffix, and renamed only after the copy finishes. The scanner ignores `.partial` files because they are not supported import extensions.

Existing identical workbooks are not replaced. Dates with no report records do not publish an empty workbook. The previous valid workbook therefore remains available if a report execution fails.

## Monitoring

- Double-click `Show-DeliveryListAutomationStatus.bat`.
- Review `C:\DeliveryListAutomation\State\last-run.json`.
- Review daily logs under `C:\DeliveryListAutomation\Logs`.
- Windows Task Scheduler names:
  - `BFS Delivery List Incremental Export`
  - `BFS Delivery List Full Export`

## Runtime limitation

This project does not and should not copy SAP runtime DLLs into the repository. The exporter can only run when the matching SAP Crystal Reports .NET runtime is already installed and registered. Seeing the Crystal report viewer on the computer makes that plausible but does not guarantee that the .NET runtime is available to a custom process.

When setup reports a missing Crystal assembly or architecture error, IT must install the matching SAP Crystal Reports .NET runtime used by A+W. A portable script cannot replace the native Crystal query/export engine.

## Local-pilot limitation

The scheduled tasks use the current user's interactive Windows token so no administrator installation or stored Windows logon password is required. They continue while the workstation is locked, but they do not run after the user logs out or when the computer is powered off. When the scanner moves to a dedicated system, recreate the tasks under a dedicated service account and retest SQL, report, and UNC permissions.
