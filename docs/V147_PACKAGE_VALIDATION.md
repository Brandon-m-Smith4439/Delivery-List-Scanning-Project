# v147 Package Validation

The v147 changed-files release was validated as a code-only package.

## Validation performed

- Python installer, validator, builder, and release test files compile successfully.
- The installer applies to a v146-shaped project and is repeat-safe.
- The standalone validator passes after installation.
- Focused v147 pytest checks pass.
- Required Bay Scanner IDs remain unique.
- The Route Pulse is nested in the blue header and has layout/paint containment.
- Legacy route connector pseudo-elements are explicitly disabled.
- Route metric and transit surfaces are no longer bright white.
- Destination Control is hidden for Remove and shown for Add.
- Only the scanner slot is sticky; the Bay Map action toolbar is explicitly static.
- Old 68-pixel and 60-pixel sticky offsets are absent.
- CSS braces are balanced.
- No database, WAL/SHM, secrets, logs, backups, caches, compiled files, or PNG previews are included.

## Test result

A fresh v146-shaped project passed the installer, standalone validator, repeat-install check, and the complete available test suite: **23 passed**.
