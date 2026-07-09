Delivery List Scanner - v62

Edited files:
- app.js
- delivery_store.py
- index.html

Changes:
- Fixed Print/Export Glass Type = Mirror so intentionally selecting mirror glass now includes regular mirror rows instead of only remake mirrors.
- Kept the default mirror exclusion behavior for normal/updated delivery-list printing when mirrors are not selected.
- Added backend handling so mirror remakes can still print with remake/update print packages even when regular mirrors are excluded by default.
- Kept updated-list printing filtered to updated rows while still allowing selected mirror rows when Mirror is intentionally checked in Glass Types.
- Updated cache-busting references to v62.

Notes:
- No __pycache__ folders included.
- No diff files included.
