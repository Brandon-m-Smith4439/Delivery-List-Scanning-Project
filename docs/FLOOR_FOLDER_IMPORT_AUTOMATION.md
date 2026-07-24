# Floor Computer Folder-Import Automation

Floor computers should import existing workbooks from the shared **Temp Delivery Lists** folder. They should not query A+W SQL or generate workbooks.

## One-time setup

1. Extract the v133 changed-files package into the current scanner project folder.
2. Close the scanner web app/server window.
3. Run `Setup-Floor-Folder-Import-Automation.bat` from the project folder.
4. The setup uses the configured Temp Delivery Lists folder, sets the automatic mode to `folder-import-only`, and sets the incremental interval to 60 minutes.
5. Restart the scanner web app.
6. Open **Admin > Import / Update Delivery List** and confirm the mode is **Import Temp Folder Only** and the schedule is installed.

The setup creates these scheduled tasks for the signed-in Windows user:

- `BFS Delivery List Automation Incremental` — runs every 60 minutes.
- `BFS Delivery List Automation Full Refresh` — runs daily at the configured full-refresh time and checks the larger date window.

The computer must be on, connected to the BFS network, and signed in for `/IT` tasks to run.

## What the setup installs

The maintained runtime is copied to:

`C:\DeliveryListAutomation\Scripts`

The setup also creates:

- `C:\DeliveryListAutomation\Run-Incremental.cmd`
- `C:\DeliveryListAutomation\Run-Full.cmd`
- `C:\DeliveryListAutomation\Run-Now.cmd`
- `C:\DeliveryListAutomation\Show-Status.cmd`

Existing runtime scripts and `sql-export.config.json` are backed up under:

`C:\DeliveryListAutomation\Backups\v133-floor-folder-import-<timestamp>`

The scanner database is not copied, replaced, or reset by this setup.

## Folder-only safety behavior

For floor mode, schedule installation:

- Verifies the Temp Delivery Lists folder exists and can be read.
- Verifies the current scanner project contains the required server, configuration, and data-store files.
- Runs the maintained scanner compatibility validator.
- Does not test or query A+W SQL.
- Does not require workbook write access to the shared folder.
- Uses the maintained folder importer, preserving scan history, quantities, racks, bays, Rush/Remake state, import history, and per-user update review data.

The older built-in 5 PM importer is disabled for the current Windows user to avoid duplicate automated imports.

## Manual verification

Run:

`C:\DeliveryListAutomation\Run-Now.cmd`

Then review:

- The command result shown in the window.
- The newest file under `C:\DeliveryListAutomation\Logs`.
- Delivery List Management in the Admin page.
- Import Audit History in the automation control center.

## Troubleshooting

### Setup BAT opens briefly and closes

V133 removes the parenthesized CMD blocks that were broken by project folders such as `Delivery-List-Scanning-Project-main (5)`. Replace both root launchers from the v133 package before retrying. The setup launcher now remains open after every handled result. Diagnostic files are written to:

- `logs\floor-folder-import-setup-launch.log`
- `logs\floor-folder-import-setup-error.log`

The desktop shortcut launcher uses the same safe path handling and writes `logs\desktop-shortcut-launch.log`.

### Missing scheduled-task script

If the web app reports that this file is missing:

`C:\DeliveryListAutomation\Scripts\Install-DeliveryListSqlAutomationTasks.ps1`

run `Setup-Floor-Folder-Import-Automation.bat` again. The source package is copied into the installed runtime before task creation.

### Shared folder cannot be reached

Confirm the floor computer is connected to the BFS network and can open the configured Temp Delivery Lists folder in File Explorer while signed in as the same Windows user running the scheduled task.

### Schedule exists but does not run

Open Windows Task Scheduler and inspect the two `BFS Delivery List Automation` tasks. The setup creates interactive tasks for the current Windows account, so the account must remain signed in.
