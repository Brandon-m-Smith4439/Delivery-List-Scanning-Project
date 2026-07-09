Scanning Project v36 - Bay scanner history and email draft modal polish

Updated files:
- server.py
- delivery_store.py
- index.html
- app.js
- styles.css

Changes in this pass:
- Reworked the Bay Map scan history section to use the same latest compact Scan History styling as the main Scan page scanning panel.
- Changed Bay Map recent scan/action rows into a vertical compact table instead of side-by-side cards.
- Tightened the Bay Map scanner panel spacing around Target Bay, scan input, and mode controls.
- Kept Target Bay near the top of the bay scan workflow above the scan textbox.
- Fixed Email Draft preview layering so it opens above the Customer Emails edit GUI.
- Rebuilt Email Draft preview sizing, padding, and layout so the content has proper white space and does not overlap or hide behind the modal edges.

Validation performed:
- app.js passed node --check.
- server.py and delivery_store.py passed Python compile checks.

Install note:
- Stop the local server, back up the current project folder, replace these files, then restart the server.
