# v144 Bottom-Docked Indian Trail Bay Scanner

## Purpose

The Indian Trail Bay Map previously reserved a 440-500 pixel right rail for the scanner. That compressed the saved seven-column physical floor layout and made individual bay groups difficult to read. v144 keeps the same scanner controls and saved floor positions while changing only their presentation.

## Layout ownership

- `bay-map-shell-v144` owns the full-width Bay Map page grid.
- `bay-right-rail-v144` now contains only the five Bay Map workflow actions and renders as a horizontal action bar.
- `bay-scanner-dock-slot-v144` owns the sticky bottom docking behavior.
- `bay-scanner-dock-v144` owns the compact horizontal scanner layout.
- The existing `bay-floor-grid-v19` still renders seven saved physical columns. v144 increases the space available to those columns but does not recalculate or reorder them.

## Scanner zones

The dock reuses the existing HTML controls and IDs in four readable zones:

1. Scanner title and current Add/Remove mode.
2. Indian Trail route progress.
3. Three-step action, target-bay, and barcode workflow with manual entry and Undo/Redo.
4. Latest scan, All Scans, recent history, and location correction.

No API, database, scan logic, permissions, or event handlers were changed.

## Responsive behavior

- Wide desktop: one compact horizontal dock.
- Compact desktop: title/route/history share the left side while the scan workflow remains wide.
- Tablet: two-column dock with the barcode step spanning the full width.
- Narrow mobile: single-column non-sticky workflow.

## Future maintenance

Modify the v144 ownership classes rather than appending new rules to the older right-rail scanner sections. The older classes remain because other shared scanner components still use them, but the Bay Map layout should be maintained through the v144 classes.
