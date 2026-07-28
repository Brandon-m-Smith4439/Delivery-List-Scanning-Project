# v146 Package Validation

The release package was validated as a code-only changed-files update.

## Automated checks

- Python installer and validator compile successfully.
- The installer applies cleanly to a v145-shaped project and is repeat-safe.
- The v146 release tests pass after installation.
- Static HTML IDs remain unique.
- All maintained Bay Scanner IDs are present exactly once.
- Route Pulse is nested inside the blue header.
- Route Pulse and route metrics are constrained to the panel width.
- The barcode Submit Scan button is absent.
- Undo and Redo are inside the barcode scan surface.
- Manual Scan is one visible Order / Item / Submit row.
- Item Number is limited to three numeric characters.
- Removed target guidance is absent from index.html and app.js.
- CSS braces are balanced and reduced-motion rules are present.
- No PNG or other preview image is included.

## Exclusions

The package contains no SQLite database, WAL/SHM companion, credentials, Microsoft Graph secret, logs, backups, caches, compiled Python files, or generated preview images.
