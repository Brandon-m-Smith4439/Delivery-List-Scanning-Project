# Database Maintenance

## Routine integrity check

Run while diagnosing a problem or before an upgrade:

```powershell
py -3 tools\database_integrity_check.py
```

For a machine-readable report:

```powershell
py -3 tools\database_integrity_check.py --json --report logs\database-integrity.json
```

The tool checks SQLite integrity, foreign keys, migration checksums/version, canonical tables and columns, documented indexes, duplicate business keys, timestamps, JSON, and row counts. Potential duplicate import keys are warnings because some source lists legitimately repeat a source identifier.

## SQLite connection settings

Every application connection enables:

- `foreign_keys=ON`
- `journal_mode=WAL`
- configured `busy_timeout`
- `synchronous=NORMAL`
- `temp_store=MEMORY`

## Optimize and WAL checkpoint

Run these when the scanner is quiet:

```powershell
py -3 tools\database_maintenance.py --optimize --checkpoint
```

The checkpoint consolidates WAL content and truncates the WAL file. Do not manually delete `-wal` or `-shm` files.

## VACUUM

VACUUM is optional and should not be part of normal startup. Stop scanning activity first, then run:

```powershell
py -3 tools\database_maintenance.py --vacuum
```

The utility creates and verifies an online backup before VACUUM begins.

## Backup policy

- Keep `data/delivery-scanner-pilot.db`, `-wal`, and `-shm` together while the app is running.
- Use SQLite's backup API instead of copying only the main file during active use.
- Keep pre-upgrade backups through at least one successfully completed production shift.
- Never use a test database as the production source of truth.

