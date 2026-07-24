# Delivery List Automation Runtime v132

This folder is installed to `C:\DeliveryListAutomation\Scripts` by either the central SQL setup or the v132 floor-folder setup. The setup does not replace the scanner database or generated delivery-list workbooks.

## v132 floor-computer folder import setup

Floor computers do not need A+W SQL access. Run `Setup-Floor-Folder-Import-Automation.bat` from the current scanner project folder. The setup copies the maintained runtime to `C:\DeliveryListAutomation\Scripts`, preserves any existing configuration with a timestamped backup, forces `folder-import-only` mode, sets the interval to 60 minutes, creates the command wrappers, validates scanner compatibility, and installs the scheduled tasks.

The floor scheduler preflight now verifies read access to the Temp Delivery Lists folder and scanner compatibility without querying A+W SQL or requiring permission to write workbooks to the shared folder. The central authorized SQL computer keeps the existing SQL/workbook preflight unchanged.

## v125 safe Task Scheduler command handling

Windows PowerShell can turn text written by `schtasks.exe` to stderr into a terminating `NativeCommandError` while `$ErrorActionPreference` is `Stop`. A missing obsolete task therefore stopped installation even though there was nothing that needed to be deleted.

The maintained installer now queries legacy tasks before deletion and runs every Task Scheduler operation through one wrapper that captures native output and checks the actual process exit code. Missing legacy tasks are ignored; real create, query, delete, or launch failures still include their detailed scheduler output.

## v124 scheduler compatibility fix

The current SQL installer was fixed in v123, but its broad preflight also parsed an older Crystal scheduler script still present in the shared installed Scripts folder. That legacy file contained the same invalid `$incrementalTask:` and `$fullTask:` form. V124 repairs the legacy file and limits current SQL preflight parsing to maintained SQL entry points.

Before creating tasks, the installer now:

1. Parses the maintained SQL automation entry points and fails with exact line/column details on any syntax error.
2. Runs the existing `RuntimeTest` path for SQL connectivity, workbook generation, destination write access, and scanner compatibility.
3. Creates the incremental and full-refresh tasks.
4. Queries both tasks to confirm Windows retained them.
5. Starts the incremental task once as a scheduler launch check.

## Apply the patch to an existing installation

1. Extract the v125 changed-files ZIP into the scanner project folder.
2. Run `Apply-v125-AutomationPatch.bat`.
3. The patch backs up the current installed scripts under `C:\DeliveryListAutomation\Backups`.
4. Retry **Save & Install Schedule** in the Admin automation control center.

The patch does not edit `sql-export.config.json`, the production database, or generated delivery-list workbooks.

## Verify the real SQL query and scanner import

Run:

`C:\DeliveryListAutomation\Verify-SQL-And-Import.cmd`

Enter a delivery date known to contain A+W orders. The verification performs all of these checks:

- Parses every maintained SQL PowerShell automation entry point.
- Opens the configured A+W SQL connection using the existing read-only query path.
- Runs the configured SQL/workbook/scanner runtime preflight.
- Executes a one-date SQL query and export in Test mode so the workbook is freshly rebuilt and validated.
- Requires the configured known-date expected-count comparison to pass when the selected date matches the validation date.
- Requires the SQL/export summary to include the date in checked, source, and published collections.
- Explicitly invokes the maintained scanner folder importer with the selected date forced through its normal business workflow.
- Requires the normalized importer result to include the date and rejects any failed result.
- Confirms the expected workbook exists.
- Uses the maintained workbook parser and stage builder to compare expected list IDs with the configured scanner store.

A passing result proves the selected date moved through SQL query, workbook generation, workbook validation, the maintained scanner importer, and final stage-list presence. A failed result keeps the detailed automation log under `C:\DeliveryListAutomation\Logs`.

The runtime continues to query A+W read-only and uses the scanner's maintained import workflow.

## Route-aware stage verification fix

The importer and the end-to-end verifier now apply the scanner's active
Customer Route Rules before calculating which receiving-stage lists should
exist. This prevents a successful all-CPU, all-DTC, or all-Greenville delivery
date from being reported as failed merely because no Indian Trail list is
appropriate for that date.

For an existing central SQL automation installation, run
`Apply-ImportRouteVerificationFix.bat` from the scanner project folder. The
patch creates a timestamped backup and replaces only
`import_delivery_folder.py` and `verify_delivery_import.py` under
`C:\DeliveryListAutomation\Scripts`.
