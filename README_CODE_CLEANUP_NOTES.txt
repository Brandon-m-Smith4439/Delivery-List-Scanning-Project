Delivery List Scanner - v44 Code Cleanup Notes

This package keeps the v43 behavior intact and focuses on maintainability:

1. Added code-map comments to server.py, delivery_store.py, app.js, styles.css, and index.html.
2. Removed trailing whitespace and collapsed extra blank lines.
3. Removed safe exact-duplicate CSS rule blocks where the same selector/body appeared again with no same-selector override between them.
4. Kept dated CSS override blocks in place when they may affect current UI behavior. The webapp has many iterative polish layers, so aggressive CSS reordering was intentionally avoided.

Future cleanup recommendation:
- When making a visual change, search styles.css for the selector first and update that rule instead of adding a new override at the bottom.
- Keep scanner, rack, bay, email, and print business rules in delivery_store.py; keep server.py focused on routing and printable HTML rendering.
- When editing app.js, prefer updating the current renderer/helper over adding duplicate helper functions.
