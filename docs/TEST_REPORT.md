## v149 Bay Scanner sticky-fit and input verification

- Verified Add mode retains the latest activity and one recent scan without overlap.
- Verified the sticky panel is 5 px from the top and bottom in normal and fullscreen operation.
- Verified the Bay Map action toolbar remains outside the sticky scanner.
- Verified Check feedback is present in Latest Activity and Recent Bay Scans.
- Verified destination and manual inputs share contained, aligned surfaces without clipping.
- Verified Undo and Redo are icon-only accessible application buttons.
- Verified Manual Submit and Clear use maintained application button classes.
- Verified required IDs remain unique and no database migration is introduced.

# Test Report

## v148 Bay Scanner history and flow verification

- Verified the static Bay Map action toolbar and scanner are adjacent in normal flow.
- Verified only the scanner slot is sticky.
- Verified the title status node is hidden and the `Just now` badge is not visible.
- Verified Remove mode hides Route Pulse percentage labels.
- Verified Recent Bay Scans is permanently open, non-scrollable, and limited to four compact columns.
- Verified Current Bay retains the existing move dropdown.
- Verified structural Bay Map edits are excluded from Bay Scan history while audit records remain available.
- Verified required Bay Scanner IDs remain unique and no schema migration is introduced.

## v147 Bay Scanner route and sticky verification

- Verified the removed header copy and visible Current Mode card are absent from the rendered scanner.
- Verified Route Pulse is nested inside the blue header, uses dark contained surfaces, and suppresses legacy connector pseudo-elements.
- Verified Destination Control is hidden by Remove mode and shown by Add mode.
- Verified the scanner slot alone is sticky at 8 pixels while the Bay Map action toolbar remains static.
- Verified required Bay Scanner IDs remain unique and no database/backend files are changed.

## v146 Bay Scanner workflow verification

- Verified Route Pulse is nested inside the blue Bay Scanner header and cannot exceed the panel width.
- Verified the barcode workflow has no Submit Scan button and still retains the maintained form and input IDs.
- Verified Undo and Redo are children of the scan input surface.
- Verified Manual Scan is one visible row with a larger Order field, compact three-character Item field, and right-side Submit button.
- Verified the removed Remove-mode sentence is absent from index.html and app.js.
- Verified required Bay Scanner IDs remain unique and no database/backend files are changed.

## v145 Bay Scanner layout verification

- Reproduced the v144 failure shape with simulated legacy scanner padding, three-column form ownership, old mode layout, and compressed Bay Map action-button rules.
- Verified the v145 scoped owners keep Scan Command, Remove/Add, Destination Control, barcode entry, Submit, Undo, and Redo in full-width ordered rows despite those simulated conflicts.
- Verified Route Pulse renders before Scan Command and the blue header begins at the panel's outside rounded edge.
- Verified the short-height sticky state positions the panel at 60 pixels and keeps the complete 659-pixel panel inside a 768-pixel viewport when the Bay Map rail is tall enough for sticky travel.
- Verified all maintained Bay Scanner IDs remain present exactly once.
- Verified CSS parsing, balanced braces, responsive rules, and reduced-motion handling.
- No database or backend validation was required because v145 changes presentation only.

## v144 Bay Scanner console validation

- Applied the v144 patch twice against a disposable v143-shaped project to verify repeat-safe markup, documentation, test, and cache-key updates.
- The focused v144 release suite passed **5/5** checks after the first and second patch runs; one historical release-marker check also passed for **6/6** focused checks total.
- Verified every maintained Bay Scanner ID remains unique and present exactly once.
- Verified the scoped stylesheet has balanced braces, reduced-motion handling, responsive rules, and no unscoped body or button ownership.
- Rendered the final console in Chromium at normal and short desktop heights; the panel measured about 744 px at 1050 px viewport height and about 536 px at 768-900 px short-height desktop viewports.
- Confirmed the installer creates timestamped backups and removes the abandoned bottom-docked v144 draft after preserving it in the backup folder.
- Full project validation still must be run after applying the package to the complete local repository because the execution environment could not clone the full GitHub archive.

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
