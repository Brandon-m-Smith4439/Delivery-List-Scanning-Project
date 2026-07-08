Scanning Project UI/Print Polish - 2026-07-08 v5

Files included:
- server.py
- delivery_store.py
- index.html
- app.js
- styles.css

Updates in this pass:
- Squashed the Scan page barcode icon so it is shorter and sharper.
- Refined the Admin top navigation cog icon.
- Polished the signed-in user selector in the top right and added an in-app dropdown action area.
- Kept the import window quick by checking from last week forward, with no upper-date cutoff by default.
- Updated the import history view so active delivery-list dates from yesterday through the newest future list remain visible, while older dates only surface when there are actual changes.
- Reworked print package behavior so remakes are automatically split to their own remake sheet for any selected stage.
- Updated print output headings/badges so sheets clearly show Updated, Remake, Indian Trail, CPU, DTC, Greenville, Outbound, or Staging.
- Updated print logic so updated-list sheets exclude remake rows and regular mirror rows, while remake sheets still include mirror remakes.
- Remake sheets now print two copies, matching the regular delivery-list copy behavior.
- Improved the Edit Racks modal so it fits without horizontal scrolling.
- Added inline rack editing from the pencil icons inside Edit Racks.
- Added a clearer inline edit row for rack name and rack set/type.
- Made Complete Rack and Print Packing List buttons slightly larger and equal sized.

Validation performed:
- app.js passed node --check.
- server.py and delivery_store.py passed Python compile checks.

Before replacing files:
- Back up the current project folder.
- Replace the matching files in the web app folder.
- Restart the local server so Python and static files refresh.
