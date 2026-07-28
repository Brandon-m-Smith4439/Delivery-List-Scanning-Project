# v145 Package Validation

## Baseline

The update was built as a correction over the v144 right-rail Bay Scanner package after a real application screenshot showed four presentation defects:

- Route Pulse appeared below Scan Command.
- The blue header was inset from the panel's rounded outer edge.
- Legacy Bay Scanner grid rules compressed the Scan Command contents into narrow columns.
- The five Bay Map workflow buttons above the scanner were too small and visually inconsistent.

## Automated checks

The v145 installer was applied twice to a disposable v144-shaped project. Both runs completed successfully and created separate timestamped backups.

The installed focused test suite passed 7 of 7 checks:

- v145 cache, README, changelog, and stylesheet markers.
- Route Pulse appears before Scan Command.
- Every maintained Bay Scanner ID is present exactly once.
- Old v144/v137 layout-owner classes are absent from the installed scanner fragment.
- The panel has zero shell padding and the blue header owns the rounded top edge.
- Scan Command is a vertical flex owner rather than an implicit multi-column grid.
- Sticky offsets, action-toolbar ownership, CSS balance, reduced motion, and release notes are present.

The standalone validator also passed and confirmed the old `bay-scanner-v144.css` file is removed after installation.

## Legacy-conflict simulation

A browser test deliberately applied aggressive old rules before the v145 stylesheet, including:

- 12-pixel inherited scanner-panel padding.
- A three-column `.scan-form` grid.
- Automatic grid placement on form children.
- Old `.bay-mode-option` layout assumptions.
- Compressed Bay Map action-button typography.

The v145 console remained correctly ordered. At a 1366 by 768 viewport, the measured command regions were:

- Full Scan Command width: approximately 434 pixels.
- Remove/Add row width: approximately 416 pixels.
- Destination row width: approximately 416 pixels.
- Barcode row width: approximately 416 pixels.

Destination remained below Remove/Add, and Barcode remained below Destination.

## Rendered workstation checks

The presentation was rendered at 1600 by 1050, 1366 by 768, and 1280 by 800.

At 1366 by 768, the compact panel measured approximately 455 by 659 pixels. In a true sticky-state simulation with a tall Bay Map rail, its top settled at approximately 60 pixels and its bottom remained inside the viewport.

The rendered checks confirmed:

- Route Pulse is the first content card below the blue header.
- The header reaches both rounded top corners.
- Remove/Add remains a balanced two-choice row.
- Destination Control, Bay Code, and Clear remain on one stable row.
- Barcode and Submit remain on one stable row.
- Undo and Redo remain directly beneath the barcode row.
- Manual Entry and Recent Bay Scans remain accessible.
- The action toolbar uses five evenly sized professional controls.

## Safety boundary

No database, migration, API, permission, scanner event, bay assignment, undo/redo, transit manifest, or backend file was modified. Production SQLite files are not included in this release package.
