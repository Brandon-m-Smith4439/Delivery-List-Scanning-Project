# Barefoot Delivery Scanner Audio Language Pack

Custom, consistent industrial UI sounds for the Delivery List Scanner.

Technical format: 44.1 kHz, 16-bit PCM, mono WAV. Every cue is mastered to a -1 dBFS peak with restrained compression and limiting.

## Cue map

| Cue | Use | Design |
|---|---|---|
| `scan_success` | Successful item scan | A crisp scanner response followed by a confident rising three-note success phrase. |
| `collapse_open` | Section expanded | A short upward whoosh for Scan and Bay Map sections. |
| `collapse_close` | Section collapsed | A short downward whoosh for Scan and Bay Map sections. |
| `scan_duplicate` | Duplicate/already scanned | A gentle repeated confirmation that says the scan was heard but no state changed. |
| `scan_warning` | Warning or override required | A controlled descending caution phrase that is distinct without sounding like failure. |
| `scan_error` | Rejected or invalid scan | A low two-part industrial rejection cue that remains clear without becoming a buzzer. |
| `scan_rush` | Successful Rush scan | The signature success sound with a high-priority sparkle that can be recognized instantly. |
| `scan_remake` | Successful remake scan | A bright success cue with a restrained glass-like shimmer for remake identification. |
| `task_complete` | 100% progress or major task completion | A confident four-note ascending completion phrase with a polished final resonance. |
| `rack_item_added` | Item added or assigned to rack | A short mechanical latch followed by a clean confirmation. |
| `rack_complete` | Rack completed | A satisfying three-stage industrial lock-in sound. |
| `rack_reopened` | Rack reopened / Not On The Way | A reverse-release sweep followed by an open-state confirmation. |
| `rack_returned` | Rack returned and cleared | A contained release-and-settle cue for rack reuse. |
| `bay_assigned` | Item assigned or scanned into a bay | A precise placement click with a clean glass-like confirmation. |
| `bay_removed` | Item scanned out or released from a bay | A short release cue that moves downward and away. |
| `bay_moved` | Item moved between bays | A directional slide followed by a placement confirmation. |
| `undo` | Undo completed | A reverse sweep with a soft descending endpoint. |
| `redo` | Redo completed | A forward sweep with a clear ascending endpoint. |
| `import_start` | Delivery-list import started | A compact rising pulse that signals work is underway. |
| `import_complete` | Import completed successfully | A three-note completion phrase that is shorter than a full-truck celebration. |
| `save` | Settings or record saved | A compact, confident save confirmation. |
| `print_ready` | Print job opened or prepared | A subtle feed/click sequence with a ready confirmation. |
| `email_sent` | Email sent | An outgoing sweep followed by a concise delivered confirmation. |
| `login` | Successful sign-in | A warm, restrained welcome phrase. |
| `logout` | Sign-out | A quiet descending close that does not resemble an error. |
| `notification` | New application notification | A light two-part ping designed to be informative rather than urgent. |
| `permission_denied` | Permission denied | A firm low refusal cue reserved for access-control failures. |
| `machine_scan` | Future machine-generated scan accepted | A compact electromechanical pulse distinct from handheld scanning. |
| `machine_fault` | Future machine fault | A controlled industrial fault signal that is forceful without becoming a piercing alarm. |

The app should use semantic cue names rather than referring directly to filenames. This keeps business events and audio assets easy to change independently.
