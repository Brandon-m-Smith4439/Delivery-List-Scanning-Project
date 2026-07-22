# Barefoot Delivery Scanner Audio Language Pack

Custom, consistent industrial UI sounds for the Delivery List Scanner.

Technical format: 44.1 kHz, 16-bit PCM, mono WAV. Primary operational cues are mastered for production-floor use. The expand/collapse and destructive-action cues are intentionally quieter than scan, outbound, and fault cues so routine operation stays clear without becoming noisy.

## Cue map

| Cue | File | Use | Design |
|---|---|---|---|
| `scan_success` | `notification.wav` | Normal accepted item scan | A light two-part confirmation. Page navigation is intentionally silent. |
| Reserved | `scan_success.wav` | Future use | The previous success composition remains packaged but is intentionally not mapped in v104. |
| `rack_barcode` | `rack_barcode.wav` | Accepted `RACK...` barcode | A compact mechanical barcode snap and rack-specific confirmation. |
| `rack_outbound` | `rack_outbound.wav` | Rack released from Outbound | A rising airy departure swoosh followed by a success chime. |
| `destructive_action` | `destructive_action.wav` | Clear, reset, remove, or delete completed | A restrained downward wipe and settle cue that plays only after the action succeeds. |
| `collapse_open` | `collapse_open.wav` | Section expanded | A short, quiet upward windy swoosh for Scan and Bay Map sections. |
| `collapse_close` | `collapse_close.wav` | Section collapsed | A short, quiet downward windy swoosh for Scan and Bay Map sections. |
| `scan_duplicate` | `scan_duplicate.wav` | Duplicate/already scanned | A gentle repeated confirmation that says the scan was heard but no state changed. |
| `scan_warning` | `scan_warning.wav` | Warning or override required | A controlled descending caution phrase that is distinct without sounding like failure. |
| `scan_error` | `scan_error.wav` | Rejected or invalid scan | A low two-part industrial rejection cue that remains clear without becoming a buzzer. |
| `scan_rush` | `scan_rush.wav` | Successful Rush scan | A priority success sound that can be recognized instantly. |
| `scan_remake` | `scan_remake.wav` | Successful remake scan | A bright success cue with a restrained glass-like shimmer. |
| `task_complete` | `task_complete.wav` | 100% progress or major completion | A confident ascending completion phrase. |
| `rack_item_added` | `rack_item_added.wav` | Item added or assigned to rack | A short mechanical latch followed by a clean confirmation. |
| `rack_complete` | `rack_complete.wav` | Rack completed | A satisfying industrial lock-in sound. |
| `rack_reopened` | `rack_reopened.wav` | Rack reopened / Not On The Way | A reverse-release sweep followed by an open-state confirmation. |
| `rack_returned` | `rack_returned.wav` | Rack returned and cleared | A contained release-and-settle cue for rack reuse. |
| `bay_assigned` | `bay_assigned.wav` | Item assigned or scanned into a bay | A precise placement click with a glass-like confirmation. |
| `bay_removed` | `bay_removed.wav` | Item scanned out or released from a bay | A short release cue that moves downward and away. |
| `bay_moved` | `bay_moved.wav` | Item moved between bays | A directional slide followed by placement confirmation. |
| `undo` | `undo.wav` | Undo completed | A reverse sweep with a soft descending endpoint. |
| `redo` | `redo.wav` | Redo completed | A forward sweep with a clear ascending endpoint. |
| `import_start` | `import_start.wav` | Delivery-list import started | A compact rising pulse that signals work is underway. |
| `import_complete` | `import_complete.wav` | Import completed successfully | A short completion phrase. |
| `save` | `save.wav` | Settings or record saved | A compact save confirmation. |
| `print_ready` | `print_ready.wav` | Print completed | Plays after the browser reports that the print workflow completed, not when the preview opens. |
| `email_sent` | `email_sent.wav` | Email sent | An outgoing sweep followed by a delivered confirmation. |
| `login` | `login.wav` | Successful sign-in | A warm, restrained welcome phrase. |
| `logout` | `logout.wav` | Sign-out | A quiet descending close. |
| `notification` | `notification.wav` | Informational notification and normal accepted scan | A light two-part ping. Page navigation does not play a sound. |
| `permission_denied` | `permission_denied.wav` | Permission denied | A firm low refusal cue. |
| `machine_scan` | `machine_scan.wav` | Future machine-generated scan accepted | A compact electromechanical pulse. |
| `machine_fault` | `machine_fault.wav` | Future machine fault | A controlled industrial fault signal. |

The app uses semantic cue names rather than filenames. This keeps business events and audio assets easy to change independently.
