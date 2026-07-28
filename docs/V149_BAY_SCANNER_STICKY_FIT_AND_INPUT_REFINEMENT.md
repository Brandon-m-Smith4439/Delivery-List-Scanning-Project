# v149 Bay Scanner Sticky Fit and Input Refinement

## Purpose

v149 keeps the compact Bay Scanner usable in Add and Remove modes without covering Latest Activity. It makes the scanner occupy the available sticky viewport, restores immediate scan-result feedback, and consolidates controls that were visually clipping or using mismatched surfaces.

## Interface changes

- Recent Bay Scans always displays at most one physical bay movement.
- Latest Activity and Recent Bay Scans each include a Check field.
- Check feedback uses Success, Check, Failed, or neutral states derived from the physical event type and reason.
- The sticky slot uses a 5 px top offset and a `100dvh - 10px` height, leaving 5 px below the panel.
- Fullscreen uses the same five-pixel top and bottom fit.
- The Bay Map action toolbar remains outside the sticky slot and in normal document flow.
- Add destination is one contained Target Bay row with a Clear action.
- Remove mode continues to hide destination controls.
- Manual Scan uses one condensed row: label, wider Order field, three-digit Item field, and Submit.
- Undo and Redo are icon-only buttons with accessible names.
- Clear and Manual Submit use shared application button classes.

## Behavior retained

- Add and Remove scan APIs are unchanged.
- Enter still submits the barcode scan field.
- Manual Scan retains its existing request path.
- Undo, Redo, All Scans, Current Bay movement, permissions, and route progress are unchanged.
- The v148 structural-history filter remains the source of truth; layout edits do not enter Bay Scan history.
- No database migration or backend patch is required.
