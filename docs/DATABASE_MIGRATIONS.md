# Database Migrations

## Installed versions

| Version | Name | Purpose |
|---:|---|---|
| 001 | `v096_baseline` | Canonical baseline for existing v096 databases and new installations |
| 002 | `v097_production_database` | Constraints, UTC audit fields, history protection, machine tables, relationships, and indexes |

Migration definitions and checksums live in `database_migrations.py`. The application records each installed migration in `schema_migrations` and refuses to continue if an installed checksum changes.

## Existing v096 database upgrade

1. Startup detects an application database without the latest migration.
2. The legacy schema is checked for required v096 tables and columns.
3. SQLite's online backup API creates `data/backups/<database>-before-v097-<UTC>.db`.
4. The backup must pass `integrity_check` and `foreign_key_check`.
5. Migration 001 is recorded as an automatic baseline without recreating any v096 table.
6. Migration 002 runs in numerical order inside a guarded upgrade transaction.
7. Foreign keys are re-enabled and checked immediately after the schema transaction.
8. The verified backup remains on disk whether the upgrade succeeds or fails.

The application never deletes, recreates, or automatically restores a production database. A failed migration stops startup and reports the preserved backup path.

## New installations

An empty database applies migrations 001 and 002 in order. Production mode does not seed sample delivery lists. Idempotent system configuration such as permissions, default stations, route rules, racks, and bays remains supported.

## Adding migration 003 or later

1. Add one immutable `Migration` descriptor in `database_migrations.py`.
2. Add one database-layer migration method to `SQLiteDeliveryStore`.
3. Update `database_contract.py` and `azure_sql_schema.sql` in the same change.
4. Add upgrade, new-install, idempotency, data-preservation, and checksum tests.
5. Never edit an already released migration. Add a new numbered migration instead.
6. Run the integrity tool against a copied production database before release.

## Recovery

If startup reports a migration failure:

1. Stop the scanner server.
2. Preserve the failed database and all `-wal`/`-shm` sidecars.
3. Run `tools/database_integrity_check.py` against both the failed database and verified backup.
4. Restore only through an approved maintenance action after confirming the backup timestamp and row counts.

