# Delivery List Scanner v071 Project Review

Date: 2026-07-16

## Review purpose

This release establishes the supplied v070 project as the reviewed baseline for future changes. No scan, import, rack, bay, printing, authentication, reporting, database, or email workflow was intentionally changed in v071.

The review focused on:

- Runtime architecture and ownership boundaries.
- Microsoft Graph integration and fallback behavior.
- Duplicate definitions, duplicate routes, HTML ID integrity, and CSS accumulation.
- Large/high-risk functions that need extra regression coverage before refactoring.
- Release packaging, documentation, and future editing standards.

## Architecture confirmed

### Browser layer

- `index.html` owns stable page, panel, modal, and control anchors.
- `app.js` owns browser state, API calls, rendering, translations, user interaction, and centralized event wiring.
- `styles.css` owns visual presentation and responsive behavior.

### Server layer

- `server.py` serves static files, translates `/api/...` requests, and renders print/export responses.
- `delivery_store.py` is the business-rule and persistence source of truth.
- `scanner_config.py` owns environment-driven runtime configuration.

### Database layer

- SQLite remains the active/default backend.
- `azure_sql_compat.py`, `azure_sql_schema.sql`, and `migrate_sqlite_to_azure_sql.py` are future-cutover assets.
- The Azure adapter intentionally reuses the SQLite business-rule implementation rather than creating a second workflow copy.

### Startup layer

- `Start-DeliveryScannerWebApp.bat` is the single supported Windows entry point.
- The BAT delegates to `Start-DeliveryScannerWebApp.ps1`.
- The PowerShell launcher validates Python, selects an available port, waits for `/api/health`, loads protected Microsoft Graph settings when present, and preserves startup logs.

## Microsoft Graph review

The Graph implementation is correctly connected to the existing customer-email workflow instead of creating a second queue.

Confirmed design:

1. Automatic manifest, ready-notice, and Admin test messages all use the existing `email_outbox` table.
2. `get_email_transport_config()` resolves Graph, SMTP, Draft, or Disabled mode in one location.
3. Local testing uses app-only client credentials loaded by the Windows launcher.
4. The client secret is stored with Windows DPAPI and is not returned to the browser or stored in SQLite.
5. Azure App Service can later use managed identity without a client secret.
6. Access tokens are cached in memory and refreshed once after a 401 response.
7. Graph sends through `/users/{sender}/sendMail` and defaults to saving a copy in Sent Items.
8. Missing transport configuration produces reviewable drafts instead of silently dropping messages.

A live BLDR email was not sent during this review because tenant credentials, administrator consent, and mailbox-scoped authorization were not available in the review environment.

## Automated validation

The supplied project completed the following checks:

- JavaScript syntax: passed.
- Python syntax/compilation: passed.
- CSS parsing: passed.
- HTML duplicate ID check: passed.
- Frontend API path/server route consistency: passed.
- Duplicate top-level Python method check: passed.
- Duplicate top-level JavaScript function check: passed.
- Duplicate HTTP route check: passed.
- Browser-rendered visual smoke coverage: passed.
- Full pytest result in this environment: **63 passed, 1 skipped**.

The skipped test is the optional Azure SQL translation test because `sqlglot` is not installed in the local review environment. That package is listed in `requirements.txt` and is not required for the active SQLite deployment. Install the Azure requirements and rerun the suite before an Azure SQL cutover.

## Code-size and maintainability observations

Current major source sizes:

- `app.js`: approximately 21,700 lines.
- `styles.css`: approximately 32,000 lines.
- `delivery_store.py`: approximately 13,600 lines.
- `server.py`: approximately 2,000 lines.
- `index.html`: approximately 1,270 lines.

The size reflects a mature feature set, but it raises the cost of broad edits. Future work should continue to modify the owning function or style block rather than append parallel implementations.

### High-risk functions

The following functions are large enough that even small edits need targeted tests and manual floor verification:

- `SQLiteDeliveryStore.receive_indian_trail_scan()`
- `SQLiteDeliveryStore.mark_sdi()`
- `SQLiteDeliveryStore.upsert_delivery_list()`
- `SQLiteDeliveryStore._indian_trail_in_transit_payload()`
- `SQLiteDeliveryStore.global_search()`
- `Handler.do_POST()`
- `Handler.do_GET()`

These are not identified as broken. They are change-risk hotspots because they combine many branches and responsibilities.

## Duplicate-code review

### Confirmed clean

- No duplicate class methods were found in the maintained Python modules.
- No duplicate top-level JavaScript function names were found.
- No duplicate exact/prefix API route checks were found inside the same HTTP method.
- No duplicate HTML IDs were found.
- Frontend API paths resolve to maintained server routes.

### CSS accumulation

A structural CSS parse found:

- 4,535 qualified rules.
- 419 selectors repeated within the same media/root context.
- 10 exact selector-and-declaration duplicates within the same context.

Repeated selectors are not automatically defects; many are intentional later overrides from previous visual revisions. However, the stylesheet has accumulated enough override layers that blind cleanup would be risky. CSS consolidation should be done as a dedicated release, one ownership section at a time, with browser screenshots and interaction tests after each section.

The first safe CSS cleanup targets are exact duplicate declarations that do not depend on source order. Broader selector merging should wait until the affected page is being actively changed.

## Documentation quality

The project already has unusually strong inline documentation coverage:

- Python functions are required by tests to have docstrings.
- Named JavaScript functions are required by tests to have nearby Purpose notes.
- CSS has ownership sections.
- `docs/CODE_REFERENCE.md` maps functions and approximate callers.
- `README_CHANGELOG.md` is the single maintained version history.

Some generated Purpose docstrings are generic. When a function is edited in the future, its note should be improved to explain the real business rule, side effects, and important callers rather than leaving only a template description.

## Packaging assumptions discovered

The supplied v070 ZIP did not contain `assets` or `data` folders.

- The application references `assets/barefoot-logo.jpg` and `assets/delivery-list-scanner-icon.ico`.
- The active SQLite database and protected Graph configuration belong under `data`.
- The upgrade instructions correctly require preserving the existing local `assets` and `data` folders.

This v071 package preserves the supplied release structure and does not invent or package a database, secret, or missing visual asset. A brand-new workstation installation needs the approved asset files and an initialized/preserved data folder.

## Required standards for future edits

1. Review the complete owning workflow before changing a function.
2. Replace or extend the existing function/block; do not add a second implementation below it.
3. Keep business rules in `delivery_store.py`.
4. Keep HTTP parsing and response translation in `server.py`.
5. Keep browser behavior in `app.js` and centralized event wiring in `wireEvents()`.
6. Put CSS changes in the existing ownership section; avoid late emergency overrides.
7. Preserve `source_id` across stage copies.
8. Make schema changes idempotent and safe for existing SQLite databases.
9. Add or update automated tests for every behavior change.
10. Regenerate `docs/CODE_REFERENCE.md` after structural source edits.
11. Update `README_CHANGELOG.md` for every delivered version.
12. Increase the release version and browser asset cache keys with every returned ZIP.
13. Do not include databases, secrets, caches, compiled files, diffs, or backup files in release ZIPs.

## Recommended order for future maintenance

1. Continue feature/fix work against this reviewed v071 baseline.
2. Keep refactors tightly connected to a requested feature instead of performing broad rewrites.
3. Schedule a dedicated CSS consolidation release only after the current interface is considered visually stable.
4. Split the largest server/store functions only with characterization tests that lock down their current behavior first.
5. Complete the controlled Microsoft Graph live test before enabling automatic external delivery for real customers.
