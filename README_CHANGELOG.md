# Delivery List Scanner - v037 Job Nr. SDI and Managed Print Workflow

Date: 2026-07-13

## Summary

This package builds on v036. It fixes the Bay Map Rush / Remake GUI so users can paste a complete Job Nr. label, adds a reusable polished success popup, and improves printing from fullscreen mode.

## Changed Files

- `app.js`
- `delivery_store.py`
- `server.py`
- `styles.css`
- `index.html`
- `README_CHANGELOG.md`

## Changes

### SDI Job Nr. lookup

- The SDI field now accepts a full Job Nr. such as `88418245M LOGAN FARMS 51`.
- It also accepts an SO number, order number, or barcode.
- Spacing and punctuation differences are normalized when matching a Job Nr.
- When a Job Nr. is matched, every line item belonging to that job on the selected active delivery list is updated together.
- Existing Bay Map assignments for those items are updated to the Rush / Remake override state so the change is visible throughout the Bay Map.
- Clearing by Job Nr. removes the special process state and restores matching bay assignments.
- Replacing the prefilled SDI value with a different Job Nr. now searches for the pasted value instead of silently applying the change to the previously selected assignment.
- The SDI input label, placeholder, and helper text now explain all accepted input formats.

### Polished success popup

- Replaced the native Rush / Remake print confirmation with a custom webapp-styled success popup.
- The popup shows the matched Job Nr. or order, customer, and number of items updated.
- Rush and Remake results provide the correct print action directly in the popup.
- The popup component is reusable for other important edits in future versions.
- Added matching Spanish translations for the new interface text.

### Printing and fullscreen

- Print pages opened by the app now use a managed print window.
- After print preview is closed or cancelled, the temporary print window closes automatically.
- The main webapp is focused again after printing.
- When the app was fullscreen before printing, it attempts to return to fullscreen automatically.
- Browsers that block automatic fullscreen restoration show a polished one-click `Return to fullscreen` popup instead.
- Applied the managed workflow to delivery-list packages, Rush/Remake sheets, rack packing lists, stale-bay reports, customer manifests, and the Statistics PDF report.

## Validation

- `node --check app.js`
- `python3 -m py_compile delivery_store.py server.py scanner_config.py`
- Temporary SQLite test: pasted full Job Nr. marked two matching items as Rush, updated both Bay Map assignments, and cleared both successfully.
- Printable HTML render test verified the after-print notification and automatic print-window close workflow.

## Cache References

- `styles.css?v=20260713-v037`
- `app.js?v=20260713-v037`
