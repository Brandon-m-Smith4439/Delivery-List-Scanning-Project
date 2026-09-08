# Delivery List Scanner: Safe Future-Chat Change Guide

Use this guide when asking ChatGPT or another coding assistant to modify the Delivery List Scanner. The goal is to keep changes reviewable, preserve live scanner data, and make installation a predictable folder overlay.

## Copy-Paste Request Header

Paste this block at the beginning of every future change request:

```text
Work from the current Delivery List Scanner source exactly as provided. Inspect the repository, git status, current application version, schema version, README, and README_CHANGELOG before editing.

Safety rules:
- Preserve existing user changes. Do not reset, recreate, replace, seed, or package the production SQLite database.
- Preserve data/, logs/, local configuration, credentials, certificates, environment files, and operator-created exports.
- Keep desktop, tablet, TC22/mobile, and print layouts working. Do not solve one breakpoint by changing another without testing both.
- Keep frontend code database-agnostic and database-specific behavior in the database/backend layer.
- Reuse current components and APIs. Do not add duplicate schema definitions, database layers, legacy compatibility copies, versioned CSS/JS source files, or renamed replacement files.
- Keep hot paths lightweight. Avoid full-catalog reloads, repeated network-share scans, unbounded DOM rendering, synchronous media loading, and duplicate polling.
- Any database change must use the existing numbered migration system, make a verified backup, preserve all rows, remain idempotent, and pass integrity/foreign-key checks.
- Do not leave the local test server or hidden PowerShell/Python processes running after validation.

Release rules:
- Increment APPLICATION_VERSION by exactly 1, displayed as a .001 release step (for example 508 means v0.508, then 509 means v0.509).
- Do not increment CURRENT_SCHEMA_VERSION unless the database schema actually changes.
- Add a new entry at the top of README_CHANGELOG.md and update the current release/install section in README.md.
- Advance browser cache keys for every changed CSS/JS asset so floor computers do not run stale files.
- Return the edited files in one ZIP named Delivery_List_Scanner_v0.###_Changed_Files.zip.
- The ZIP must preserve project-root-relative paths, such as static/css/mobile.css and backend/store.py. Do not flatten files and do not add an extra parent folder inside the ZIP.
- Include every runtime dependency changed by the update, but exclude data/, *.db, *.db-wal, *.db-shm, logs/, backups/, .git/, .vs/, __pycache__/, _verification/, credentials, secrets, and generated exports.
- The ZIP must be safe to extract directly into the existing project folder with overwrite/replace enabled.

Validation rules:
- Run JavaScript syntax checks and Python compile/import checks without creating bytecode churn.
- Run focused tests for the changed workflow, then the complete maintained test suite.
- For database work, run integrity_check, foreign_key_check, migration-version validation, and a data-preservation upgrade test on a copy.
- Visually inspect every affected page and dialog at desktop, vertical monitor/tablet, common phone widths, and Zebra TC22 portrait and landscape sizes.
- On the TC22 profile, walk the complete operator route: sign in, Home, Statistics, Scan, All Scans, order details, filters/search, Print/Export, Racks, rack details/history, Bay Map, bay tools, Rejects, Settings, help/tutorial, notifications, user menu, and sign out. Use an isolated test database for any write action.
- Open and visually verify every affected GUI, popup, drawer, tab, tutorial step, success/notice/error state, and empty/loading state. Confirm each shared X closes its own GUI and that the background page cannot scroll while a modal is open.
- Test keyboard, mouse, touch-sized controls, scrolling, predictive search, scan/undo/redo, modal close/scroll lock, loading/error/empty states, permissions, and browser console errors.
- Report exact files changed, exact tests run and results, any unverified operator-only behavior, and any remaining risks.
```

## Safe Installation

1. Back up the entire current project folder and confirm the server is stopped.
2. Preserve the live `data` folder separately. A changed-files ZIP should never contain a database.
3. Inspect the ZIP before extraction. Its first level should contain paths such as `static`, `backend`, `database`, `docs`, or root runtime files, not another project folder.
4. Extract the ZIP into the existing Delivery List Scanner project folder and choose **Replace the files in the destination**.
5. Start the app using the maintained launcher, hard-refresh the browser with `Ctrl+F5`, and confirm the displayed version.
6. Run a controlled scan, undo/redo, list lookup, print preview, rack/bay operation, and sign-out/sign-in check before floor use.

## Versioning Model

- Application release `508` is displayed and documented as `v0.508`.
- Every shipped change advances exactly one step: `v0.508` to `v0.509`.
- SQLite schema numbering is independent. A CSS-only or JavaScript-only release must not create a database migration.
- Historical changelog entries are immutable. Add a new entry above them instead of rewriting previous release history.

## Packaging Checklist

- ZIP paths are relative to the project root and retain their directories.
- Runtime files referenced by edited HTML/Python are included.
- New assets are included and cache-busted where applicable.
- No live database, WAL/SHM sidecars, secrets, logs, backups, verification screenshots, or Git metadata are included.
- README and changelog match the displayed application version.
- The assistant provides a plain-text changed-file list and validation report in addition to the ZIP.
