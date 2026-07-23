# Floor Database Transfer and Upgrade

Use `Transfer-Floor-Database-To-Current-Version.bat` when installing a newer Delivery List Scanner build on a floor computer while preserving the SQLite data from its older project copy.

## What the transfer does

The transfer is a **database replacement and schema upgrade**, not a merge of two separately active databases.

1. Validates the selected old floor database.
2. Creates a WAL-safe SQLite backup of the old database without modifying it.
3. Creates a verified backup of the database already in the current/new project.
4. Places a snapshot of the old floor database at the current project's configured SQLite path.
5. Runs the current app's maintained `delivery_store.py` initialization and numbered migrations.
6. Runs SQLite integrity and foreign-key checks.
7. Confirms that tables from the old database still exist and that their record counts did not decrease.
8. Writes a JSON report and all backups under `data\backups\floor-database-transfer-<timestamp>`.

The transfer preserves the complete floor database, including delivery lists, line items, scan quantities and history, users, permissions, racks, rack assignments, bays, bay assignments, import history, settings, and audit records that exist in the selected database.

## Required preparation

- Use the newest/current scanner project as the destination.
- Keep the old project folder unchanged until testing is complete.
- Close the Delivery List Scanner server window on both copies before running the transfer.
- Do not open the database in another SQLite program during the transfer.
- This utility supports the local SQLite deployment only. It does not migrate data into Azure SQL.

## Run the transfer

1. Extract the newest changed-files package into the current scanner project.
2. Double-click `Transfer-Floor-Database-To-Current-Version.bat`.
3. Paste either:
   - the old scanner project folder,
   - the old project's `data` folder, or
   - the full path to `delivery-scanner-pilot.db`.
4. Review the source and target paths shown by the utility.
5. Type `TRANSFER` exactly when prompted.
6. Wait for the final success message.
7. Start the current scanner normally.

A database file can also be dragged directly onto the BAT file.

## Verify after transfer

Check these areas before treating the new copy as the floor production copy:

- Existing usernames and passwords work.
- Delivery dates and all stage lists are present.
- Scanned quantities match the old system.
- Recent Scan and All Scans history are present.
- Rack status and rack contents are correct.
- Bay assignments and the Old Bays view are correct.
- Rush, remake, route, and manual-edit state is retained.
- The Admin import history is present.

The transfer report lists before-and-after row counts for every pre-existing application table.

## Automatic recovery behavior

If migration or validation fails after the target was replaced:

- The failed upgraded database is copied into the timestamped backup folder when possible.
- The database that existed in the current project before the transfer is restored automatically.
- The selected old floor database remains untouched.

Do not delete the timestamped backup folder until floor testing has been completed successfully.

## Compatibility boundary

The current migration system can baseline and upgrade the maintained v096-compatible schema and later databases. The transfer stops before changing the target when the selected database is missing required core tables. That is safer than guessing how to translate a much older or incomplete schema. Provide that database for a dedicated converter if this validation occurs.
