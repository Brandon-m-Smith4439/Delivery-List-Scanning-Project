# Delivery List Scanner - v033 Moving Truck Transit Animation

Date: 2026-07-13

## Summary

This package builds on v028 and focuses only on the Indian Trail Bay Map transit workflow section. The Outbound, In Transit, and Received areas now read as one consistent professional control group, with clearer click affordances and improved readability.

## Changed Files

- `app.js`
- `styles.css`
- `index.html`
- `README_CHANGELOG.md`
- `delivery_store.py` unchanged
- `server.py` unchanged
- `scanner_config.py` unchanged

## Changes

### Outbound and Received cards

- Rebuilt both side cards into a consistent layout with:
  - clear section label
  - large scanned/total quantity
  - delivery-list stage label
  - visible `Open list` action row
- Added professional hover and keyboard-focus effects so users can clearly tell the cards are clickable.
- Added subtle Outbound yellow and Received green accent treatments.
- Added disabled/unavailable presentation when a matching delivery list does not exist.

### In-transit workflow card

- Tightened spacing and improved visual hierarchy.
- Corrected singular/plural wording such as `1 piece on the way`.
- Replaced the compressed summary sentence with separate compact summary chips for jobs, truck pieces, and rack pieces.
- Integrated the rack-in-transit summary into the center card instead of leaving it as a detached footer line.
- Added a clearer `Open manifest` action with hover movement.
- Preserved the existing animated flow line and received-progress calculation.

### Overall layout

- Made all three cards use matching borders, radius, shadows, spacing, and hover behavior.
- Added responsive adjustments for narrower screens.
- No business logic, scan logic, manifest data, or routing behavior was changed.

### Cache version update

- `styles.css?v=20260713-v029`
- `app.js?v=20260713-v029`

## Validation

Passed:

- `python3 -m py_compile delivery_store.py server.py scanner_config.py`
- `node --check app.js`


## v030 Changes

- Centered the selected text inside the Statistics range selector dropdown so values like `Last 30 days` sit visually centered in the pill.
- Simplified the Bay Map in-transit center card so it is easier to scan and read.
- Increased the main in-transit text size and reduced the number of separate info rows in the middle section.
- Replaced the three small transit summary chips with one concise summary sentence.
- Kept the animated lane, received progress bar, rack summary, and Open manifest action.
- Updated cache references to `styles.css?v=20260713-v030` and `app.js?v=20260713-v030`.


## v031 Changes

- Changed Outbound and Inbound card totals to a compact ratio format such as `0/104`.
- Removed the center sentence showing jobs, rack pieces, and truck pieces in transit.
- Restored the in-transit animation and progress-bar dimensions used before v030.
- Recentered the pieces-on-the-way count, animation, and progress bar lower in the middle card.
- Kept the rack summary and Open manifest action.
- Updated cache references to `styles.css?v=20260713-v031` and `app.js?v=20260713-v031`.


## v032 Changes

- Restored the Bay Map in-transit animation lane to span the full width of the center card.
- Kept the existing animation speed, progress bar, pieces-on-the-way count, rack summary, and manifest behavior.
- Rebuilt the Home delivery-date expand icon as a true east-pointing SVG-style arrow instead of a rotated border corner.
- Centered the arrow inside its circular background.
- The arrow now rotates cleanly from east to south when a delivery date is expanded.
- Updated cache references to `styles.css?v=20260713-v032` and `app.js?v=20260713-v032`.


## v033 Changes

- Replaced the Bay Map moving light bar with a full-width Moving Truck animation.
- Added a professional blue delivery truck rendered directly in the web UI with inline SVG and CSS.
- The truck travels from the Outbound side to the Indian Trail side across the entire center lane.
- Added yellow origin and green destination markers with a blue-to-green dashed route.
- Preserved the pieces-on-the-way count, received progress bar, rack summary, and Open manifest action.
- Preserved the v032 Home delivery-list arrow redesign: a true centered east-pointing arrow that rotates south when expanded.
- Added reduced-motion support so the truck remains centered without animation when the operating system requests reduced motion.
- Updated cache references to `styles.css?v=20260713-v033` and `app.js?v=20260713-v033`.
