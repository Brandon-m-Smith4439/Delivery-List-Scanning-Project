# v146 Bay Scanner Workflow Refinement

## Purpose

v146 applies the next floor-review corrections to the Bay Map scanner without changing its APIs, database, permissions, scan rules, or event wiring.

## Combined header and Route Pulse

The Bay Scanner title, current mode, live state, and Indian Trail Route Pulse now share one continuous blue header. The route metrics use zero-minimum grid columns, fixed internal padding, `max-width: 100%`, and clipped overflow so Outbound, In Transit, Received, and the dual progress control cannot extend beyond the rounded scanner shell.

## Scan workflow

- Remove now reads **Finds the piece's current bay**.
- The redundant Remove-mode destination sentence was removed from both static markup and the maintained JavaScript text path.
- The barcode **Submit Scan** button was removed. Hardware scans and typed barcodes continue to submit through the existing form when Enter is received.
- Undo and Redo now sit halfway across the barcode field's upper-right border. The input reserves space on the right so barcode text cannot run under the correction controls.

## Manual scan

Manual Scan is no longer hidden inside a disclosure. It is directly below the barcode field as one horizontal row:

1. A flexible Order Number field.
2. A compact Item field limited to three numeric characters.
3. A right-aligned Submit button.

The existing manual quantity remains fixed at one and the maintained `bayManualSubmitBtn` event path is unchanged.

## Retained functionality

- Add and Remove modes.
- Target-bay selection and Clear.
- Indian Trail transit-manifest access.
- Route progress and completion animation.
- Latest activity, All Scans, recent history, and Change Location.
- Sticky desktop position and non-sticky tablet/mobile behavior.
- Reduced-motion support.

## Deployment boundary

No API route, database schema, database migration, role permission, backend service, scan rule, or notification workflow was changed. This is a browser-interface release over v145.
