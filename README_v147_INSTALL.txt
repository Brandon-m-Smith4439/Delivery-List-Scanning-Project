Delivery List Scanner v147 - Bay Scanner Containment Refinement
================================================================

Install over the current v146 project.

1. Close the Delivery List Scanner server.
2. Back up the project folder and the existing data folder.
3. Extract this ZIP directly into the v146 project folder.
4. Replace files when Windows asks.
5. Double-click Apply-v147-BayScannerContainmentRefinement.bat.
6. Restart the scanner normally.
7. Press Ctrl+F5 once in the browser.
8. Run Run-v147-BayScanner-Validation.bat.

What changed
------------
- Removed the visible Indian Trail receiving label, workflow sentence, and Current Mode card.
- Kept Bay Scanner and Route Pulse in one continuous blue header.
- Recolored Route Pulse with contained dark-blue surfaces.
- Removed the inherited dotted connector, arrow, and bright white transit pill.
- Hid Destination Control while Remove is selected; it returns for Add mode.
- Moved only the scanner panel to an 8-pixel sticky offset.
- Kept the Bay Map action buttons outside the sticky scanner slot.

No database migration or backend patch is required.
No PNG preview files are included.

Rollback copies are created under:
  backups\v147-bay-scanner\<UTC timestamp>
