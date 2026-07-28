# v145 Bay Scanner Layout Correction

## Purpose

v145 corrects the first v144 Bay Scanner console after real floor rendering exposed conflicts with older Bay Scanner layout rules. The v144 controls were all present, but legacy grid ownership could compress Scan Command into narrow columns, leave padding around the blue header, and make the five Bay Map action buttons look too small.

## Corrected panel order

The maintained right-rail order is now:

1. Blue Bay Scanner header and current mode.
2. Indian Trail Route Pulse.
3. Scan Command.
4. Collapsed Manual Entry.
5. Latest Bay Scan Activity and Recent Bay Scans.

The route summary is intentionally above the scanning workflow so the operator sees current Outbound, In Transit, and Received state before scanning.

## Layout isolation

The v145 fragment retains every operational ID used by `app.js`, but replaces the old v105/v137 layout classes with dedicated v145 owners. The new stylesheet explicitly resets the panel, form, command, mode, target, barcode, and activity grids so older compatibility rules cannot place them into narrow implicit columns.

The panel header now touches the outside border and follows the panel's rounded top corners. The panel itself has zero internal shell padding; spacing belongs to the sections below the header.

## Sticky behavior

At normal desktop height, the right-rail scanner sticks at 68 pixels from the viewport top. At common short floor-computer heights it sticks at 60 pixels, moving it slightly closer to the application header while keeping it below the header. The initial unscrolled position is unchanged because the `top` value applies only after sticky positioning engages.

Fullscreen uses a 10-pixel sticky offset. Tablet and mobile layouts return the scanner to normal document flow.

## Bay Map action toolbar

Old Bays, Rush / Remake, Manage Items, Edit Bays, and Edit Map now use one balanced five-button toolbar with readable labels, consistent icon sizing, subtle depth, and restrained hover/focus motion. Smaller layouts change to three or two columns rather than shrinking the controls into unreadable cells.

## Safety

No API routes, database schema, permissions, scan logic, undo/redo behavior, bay-assignment behavior, transit manifest behavior, or event handlers were changed. The update is limited to Bay Map markup, the v145 scoped stylesheet, release documentation, and focused release checks.

## Floor verification

1. Hard-refresh the browser after installation.
2. Confirm Route Pulse appears directly below the blue header.
3. Confirm the blue header reaches both rounded top corners with no gray inset.
4. Confirm Remove and Add remain side by side and readable.
5. Confirm Target Bay, Bay Code, Clear, barcode input, Submit Scan, Undo, and Redo remain in separate horizontal rows without overlap.
6. Scroll the Bay Map and confirm the scanner sticks slightly higher without overlapping the application header.
7. Confirm all five Bay Map action buttons above the scanner are readable and evenly sized.
8. Test Add, Remove, Manual Entry, All Scans, Recent Bay Scans, Undo, Redo, and Change Location.
