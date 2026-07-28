# v147 Bay Scanner Containment and Sticky Refinement

## Purpose

v147 corrects the remaining Bay Scanner presentation issues found during floor review of v146. It keeps the maintained scan workflow and control IDs while tightening header content, Route Pulse containment, mode-specific destination controls, and sticky positioning.

## Header and Route Pulse

- Bay Scanner and Route Pulse remain inside one continuous blue header.
- Removed the visible `Indian Trail receiving` eyebrow.
- Removed `Choose the action, confirm the bay, and scan the piece.`
- Removed the visible Current Mode card. A hidden compatibility node retains the existing `bayScannerModeSummary` ID so current JavaScript remains safe.
- Route metrics use restrained dark-blue surfaces instead of bright white cards.
- Legacy transit-line pseudo-elements, arrow graphics, and inherited white pill styling are explicitly suppressed.
- Route Pulse and route metrics use width, overflow, layout, and paint containment so nothing can draw outside the rounded panel.

## Mode-specific destination workflow

Destination Control remains fully available for Add mode. When Remove is selected, CSS hides the complete Destination Control section because the maintained scan workflow locates the piece's current bay automatically.

## Sticky ownership

The five Bay Map action buttons remain in normal document flow and are not sticky. Only `bay-scanner-sticky-slot-v147` uses sticky positioning. Its desktop top offset is 8 pixels so the panel moves near the top of the page after the action buttons scroll away. Tablet and mobile behavior remains non-sticky.

## Preserved behavior

The following workflows are unchanged:

- Add and Remove scanning
- Barcode submission through scanner input or Enter
- Undo and Redo
- Manual Order / Item / Submit
- Indian Trail transit manifest
- Latest activity and All Scans
- Recent Bay Scans
- Change Location
- Permissions, APIs, database rules, and backend processing

## Installation

Install over v146, run `Apply-v147-BayScannerContainmentRefinement.bat`, restart the scanner, and hard-refresh once with `Ctrl+F5`.

No database migration or backend patch is required. No PNG previews are generated or packaged.
