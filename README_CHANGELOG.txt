Scanning Project Update v43 - Updated Remake Print Fix

Files included:
- server.py
- delivery_store.py
- index.html
- app.js
- styles.css

What changed in this update:
- Fixed updated delivery-list printing so remake sheets only include remakes that were actually new/changed by the latest import/update.
- Existing remakes no longer appear on the updated remake sheet unless that remake row itself was marked New Line / Updated Line / changed by the import.
- Whole-list printing and remake-only printing still include all applicable remakes as before.
- Rush updated printing keeps the same behavior and only prints updated rush rows when Updated Only is selected.

Install:
1. Stop the local server.
2. Back up your current project folder.
3. Replace the included files.
4. Start the server again.

Validation performed:
- server.py Python compile check
- delivery_store.py Python compile check
- app.js node syntax check
