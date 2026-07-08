Scanning Project UI Polish v3 - 2026-07-08

Replacement files included:
- server.py
- delivery_store.py
- index.html
- app.js
- styles.css

Changes in this pass:
- Replaced the Admin top-page selector icon with a cleaner cog icon.
- Replaced the Scan top-page selector icon with a sharper barcode icon.
- Polished the top-right signed-in user menu with initials, role/station details, and a cleaner dropdown.
- Re-centered the save/delete icons in the Customer Route Rules editor.
- Reworked Active/Inactive and Signed in/Logged out user pills so they sit side by side, centered in their status area.
- Updated the delete-user icon to read as a user-delete action instead of a generic trash icon.
- Removed Create Rack and Create Rack Set from the main Rack page header; those actions remain inside Edit Racks.
- Added a Quick rack edit form inside Edit Racks so rack name/type can be edited without opening a separate rack form.
- Added full-card gradient status coloring to rack cards: green for complete, gold for open/loaded, soft gray for empty.
- Made Complete Rack and Print Packing List action buttons consistent and slightly smaller.
- Enlarged the rack selector in the staging scan panel.
- Moved All scans to the top-right of the scan history heading.
- Tightened the scan history card to better handle long customer names and avoid the scanning panel's own vertical scrollbar.
- Added additional polish to the Edit Lookups UI for readability.

Validation performed:
- app.js passed node --check.
- server.py and delivery_store.py passed Python compile checks.

Install:
1. Back up your current project folder.
2. Replace the matching files in your project with these files.
3. Restart the local server.
4. Hard refresh the browser if the old CSS is cached.
