# v148 Package Validation

The v148 changed-files release is a code-only package with one guarded store-layer history filter and no schema migration.

## Validation performed

- Installer, validator, builder, and release tests compile successfully.
- Installer applies over a v147-shaped project and is repeat-safe.
- Standalone validation passes after first and repeated installation.
- The available focused and historical release suite passes: **31 passed**.
- Required Bay Scanner IDs remain unique.
- The Bay Map right rail is top-aligned so the static toolbar and scanner are adjacent.
- Only the scanner slot owns sticky positioning.
- The visible live-time badge is removed.
- Remove mode suppresses Route Pulse percentage labels.
- Recent Bay Scans is permanently open and has no horizontal or vertical scrolling.
- Recent rows use Order Nr., Job Nr., Action, and editable Current Bay.
- The app renderer uses the existing `bayEventMoveControlHtml()` workflow.
- A SQLite behavioral test verified structural events are not inserted, item movement events remain, Job Nr. is returned, and Current Bay resolves correctly.
- `delivery_store.py` filters older structural events and prevents new structural layout events from entering Bay Scan history.
- Administrative audit records are not removed.
- CSS parses without errors, has balanced braces, and has zero exact duplicate qualified rules.
- No database, WAL/SHM, secrets, logs, backups, caches, compiled files, or PNG previews are included.
