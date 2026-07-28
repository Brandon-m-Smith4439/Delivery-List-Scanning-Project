# v144 Bay Scanner Operations Console Redesign

## Purpose

The v143 Bay Map scanner keeps every required workflow available, but its three large step cards make the right rail taller and visually heavier than the main Scan-page scanner. v144 replaces that presentation with one compact, scan-first operations console while preserving the maintained scanner behavior.

## Final workflow

1. Choose **Remove** or **Add** in the segmented mode control.
2. In Add mode, click a bay on the map or enter its code in the destination strip.
3. Scan the barcode or type it into the primary scan field.
4. Press Enter or use **Submit Scan**.
5. Use Undo or Redo immediately below the scan command when a correction is required.

Manual order/item entry remains available as a collapsed fallback. Route progress and the latest scan remain visible without competing with the barcode command. The longer recent-scan table stays collapsed until it is needed.

## Design ownership

- `bay-scanner-panel-v144` owns the complete Bay Map scanner surface.
- `bay-scanner-command-v144` owns the compact mode, target, barcode, Submit, Undo, and Redo workflow.
- `bay-route-status-v144` owns the compressed Indian Trail Outbound / In Transit / Received pulse.
- `bay-scan-history-v144` owns latest activity, location correction, All Scans, and the recent-history disclosure.
- `bay-scanner-v144.css` is intentionally scoped to the Bay Map scanner instead of adding broad late overrides to `styles.css`.

The v105 and v137 compatibility classes remain in the markup because older shared styles and existing browser code may still reference them. The final presentation is owned by the v144 classes loaded after the shared stylesheets.

## Motion language

At desktop widths with a viewport height of 900 pixels or less, the console switches to a compact-height state. It removes secondary helper copy, tightens the route pulse, and places latest-activity controls on one row so the complete scanner remains visible at common 1366x768 floor-computer resolutions.

The redesign uses small, restrained effects rather than continuous decorative motion:

- A short panel entrance on page activation.
- A slow, subtle header sheen.
- A small live-status pulse.
- Selected-mode elevation and semantic Add/Remove colors.
- Input focus lift and glow.
- Submit-button sheen only on hover.
- Smooth route-progress width changes.
- Short disclosure transitions for Manual Entry and Recent Scans.

`prefers-reduced-motion: reduce` disables the decorative motion without changing layout, feedback, or scanner functionality.

## Preserved contracts

The redesign preserves these maintained IDs exactly once:

- Add/Remove: `bayScanRemoveMode`, `bayScanModeToggle`, `bayScannerModeSummary`
- Target bay: `bayScannerTargetState`, `bayScanBayInput`, `bayTargetClearBtn`
- Barcode and corrections: `bayScanOutForm`, `bayScanOutInput`, `bayUndoBtn`, `bayRedoBtn`
- Manual fallback: `bayManualOrderInput`, `bayManualItemInput`, `bayManualQtyInput`, `bayManualSubmitBtn`
- Route progress: `bayPanelRouteMini`
- Activity: `bayScanOutStatus`, `bayAllScansBtn`, `bayLastCard`, `bayLastBay`, `bayLastTitle`, `bayLastAction`, `bayLastOrder`, `bayLastTime`, `bayLastMoveSelect`, `bayRecentScanCountLabel`, `bayScanOutRecent`

No API routes, database schema, scan logic, permissions, event handlers, rack behavior, bay assignment rules, or undo/redo rules were changed.

## Required floor verification

1. Open Bay Map at the normal floor-computer resolution, including 1366x768 when available, and confirm the complete panel is visible without horizontal overflow.
2. Remove a known piece from a bay and confirm the current bay is found automatically.
3. Select Add, click a bay on the map, and confirm the target code appears in the destination field.
4. Add a known piece to the selected bay.
5. Test Enter submission and the Submit Scan button.
6. Test Undo and Redo.
7. Expand Manual Entry and submit a known order/item.
8. Open the in-transit manifest through the center route control.
9. Confirm the latest activity card and location-change selector update after a scan.
10. Expand Recent Bay Scans and open All Scans.
11. Test normal desktop, fullscreen, compact desktop, tablet, and mobile widths.
12. Enable reduced motion at the operating-system or browser level and confirm the workflow remains unchanged.

## Rollback

The installer creates timestamped backups under `backups/v144-bay-scanner/<UTC timestamp>`. Restore `index.html`, `README.md`, and `README_CHANGELOG.md` from that folder, remove `bay-scanner-v144.css`, and restore the prior v144 draft note only if it is still needed. No database rollback is required.
