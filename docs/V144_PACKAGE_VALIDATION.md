# v144 Package Validation Report

## Verified baseline

- Repository: `Brandon-m-Smith4439/Delivery-List-Scanning-Project`
- Verified maintained release: **v143**
- Verified source commit: `940dfd053144a8552f330b3cf3ea7ce8f0418038`
- The repository also contained an unannounced bottom-docked v144 draft document and test while the live page and cache markers remained v143. The finalized release replaces that inactive draft with the approved compact right-rail console.

## Change boundary

v144 is a browser-only interface release. It changes the Bay Scanner markup, installs one scoped stylesheet, advances cache keys, and updates release documentation/tests. No API routes, database schema, scan logic, permissions, event handlers, or backend modules are changed.

## Installer validation

The package installer was run twice against a disposable v143-shaped project to verify repeat safety.

- First install: passed.
- Second install: passed.
- Focused v144 release contract: **5/5 passed** after both installs.
- Historical current-release marker check: passed, for **6/6 focused checks** total.
- The inactive bottom-dock draft was preserved in the timestamped rollback backup and removed from the installed project.
- Existing v143 project files were backed up before replacement.
- Every maintained Bay Scanner ID remained present exactly once.
- All browser cache markers advanced to v144.

## Static validation

- Python patch/test compilation: passed.
- HTML required-ID and duplicate-ID checks: passed.
- CSS brace balance: passed.
- CSS is scoped to the v144 Bay Scanner/right-rail ownership classes.
- No unscoped `body`, generic `button`, or `.app button` owner was introduced.
- Reduced-motion handling is present.
- No database, SQLite WAL/SHM, secret, credential, log, cache, backup, or compiled file is included in the release ZIP.

## Rendered viewport checks

The final console was rendered in Chromium at normal and compact desktop sizes.

| Viewport | Approximate scanner height | Result |
|---|---:|---|
| 1600 x 1050 | 744 px | Entire panel visible with full helper text |
| 1440 x 900 | 537 px | Entire panel visible in compact-height mode |
| 1366 x 768 | 536 px | Entire panel visible on a common floor computer |
| 1280 x 800 | 534 px | Entire panel visible without horizontal overflow |

The short-height media rule intentionally removes secondary helper copy and compacts the latest-activity layout while preserving the barcode command, mode selector, target bay, Submit, Undo/Redo, route progress, Manual Entry access, All Scans, and location correction.

## Full repository boundary

The connected GitHub integration exposed the current source and commit, but the execution environment could not clone the complete repository archive into its local filesystem. For that reason, this delivery contains:

1. A repeat-safe changed-files installer.
2. A pinned Windows full-project builder that downloads the exact verified v143 commit, applies v144, validates it, strips production data and secrets, and creates `Delivery_List_Scanner_v144_Full_Project.zip`.

## Required floor verification

1. Back up the current project and `data` folder.
2. Install v144 and hard-refresh with `Ctrl+F5`.
3. Test Add mode using a selected bay.
4. Test Remove mode and automatic current-bay discovery.
5. Verify Enter and Submit Scan both submit.
6. Verify Undo and Redo.
7. Verify Manual Entry.
8. Open the in-transit manifest from Route Pulse.
9. Open All Scans and change a recent item location.
10. Check the page at the actual floor workstation resolution and browser zoom.
