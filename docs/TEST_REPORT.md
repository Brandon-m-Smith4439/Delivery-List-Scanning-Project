# Test Report

## v100 audio and manual-editor verification

- The complete unittest suite passed **21/21** tests.
- Verified restored sound allowlisting, silent printing, first-gesture audio unlock, immediate fallback playback before background WAV loading, and the redesigned five-note Scan Success cue.
- Verified Manual Delivery List Edit source contracts for collapsed rows, 20-row batches, Load More, predictive input, Job Nr. matching, and sidebar-safe filter stacking.
- Exercised the SQLite editor query with 45 real line items and verified pages of 20, 20, and 5 with no duplicate IDs.
- Verified exact Job Nr. and partial order-number searches against SQLite.
- Validated every enabled packaged sound as a readable, nonempty WAV file.
- Python compilation and `git diff --check` passed after the change.

## v099 responsiveness and scanning verification

- The complete unittest suite passed **17/17** tests: the existing 10 database/migration tests plus 7 focused Scan UI source-contract tests.
- Verified that Manual Delivery List Edit save no longer reloads the delivery-list catalog or reruns the modal search.
- Verified that live sound playback does not fetch/decode WAV files and that routine UI actions are excluded from the operational sound allowlist.
- Verified removal of whole-document custom-select polling, viewport-specific Scan rendering, the compact filter drawer, active chips, timed outcomes, rack correction control, and v099 cache keys.
- Python compilation passed for `server.py` and the database/migration tools.
- A disposable SQLite database server smoke test returned HTTP 200 for `/`, `app.js`, and `styles.css`; the served assets contained the v099 filter and scan-result implementations.
- The daily importer remained alive on Windows without `tzdata` and reported that it was using the Windows local timezone fallback.
- A rendered browser screenshot pass could not be completed because the managed environment blocked Edge child-process/profile sandbox access. This does not affect normal operator machines, but visual interaction should still receive a short floor smoke test.

## v097 database verification

- Python compile passed for the database layer, migration runner, integrity and maintenance tools, Azure migration utility, package builder, and database tests.
- The database-focused unittest suite passed **10/10** tests.
- A copy of the production-shaped SQLite database upgraded from the v096 baseline through migration 002 while preserving 208 delivery lists, 13,694 line items, 818 scan events, 21 rack items, and 46 bay assignments. Startup added one expected audit record for its idempotent repair/configuration pass; no prior audit history was removed.
- `PRAGMA integrity_check` returned `ok` and `PRAGMA foreign_key_check` returned no violations after upgrade.
- Migration checksums, idempotent startup, pre-upgrade backup creation, quantity constraints, append-only history, and production no-demo behavior were verified.
- The integrity tool passed on the upgraded copy; duplicate source identifiers were reported as a nonfatal business-key warning.
- Azure migration dry-run preflight passed for all 35 canonical tables and 28,615 rows and produced deterministic checksums without writing to Azure.
- The v097 ZIP was inspected to confirm it contains required source, docs, and tools and no SQLite database files.

## Validation boundary

No live Azure SQL instance was available in this workspace. Azure DDL and migration behavior were statically and locally tested, but the final cutover must still be rehearsed against a nonproduction Azure SQL database before production use.
