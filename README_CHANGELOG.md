# README Changelog

## v105
- Completely rebuilt the Old Bay Review modal as an Old Bay Control Center with a stronger header, compact operational summary, local search, age filters, sorting, and a dedicated printable-investigation action.
- Added clear old-bay age severity treatments, bay and order/item identity, concise job/size/delivery/last-scan details, and a cleaner per-row snooze control.
- Added explicit row selection, Select Visible/Clear Visible behavior, a live selected count, and safe bulk snoozing that affects only checked rows instead of silently snoozing every old-bay assignment.
- Preserved individual snoozing, empty-state handling, daily automatic alert behavior, print support, and backend stale-bay APIs.
- Completely reorganized the Bay Map scanning panel into a polished three-step workflow: choose Add/Remove, confirm the target bay, then scan the piece.
- Added live mode and target guidance, a larger primary scan surface, an explicit Submit Scan button, and nearby Undo/Redo correction tools.
- Moved Manual Entry into an accessible disclosure so the primary barcode workflow stays concise while order/item entry remains fully available.
- Reworked Bay Scan History with a clearer latest-location card, readable status treatment, retained location correction, All Scans access, and a collapsible recent-scan table.
- Preserved Indian Trail route progress, in-transit manifest access, barcode scans, selected-bay targeting, manual scans, undo/redo, recent history, and location changes.
- Consolidated the latest Old Bay and Bay Scanner CSS ownership blocks instead of adding another duplicate override layer.
- Added Spanish translations for the new Old Bay and Bay Scanner labels and advanced browser/sound cache keys to v105.

## v104
- Reduced the normal-stage timed scan popup from a wide three-card layout to one concise result card with a compact header, readable order/item identity, customer, quantity, dimensions, glass/job, route, location, and optional rack correction.
- Raised popup rack/bay custom-select menus above the timed card so expanded dropdowns no longer render behind it.
- Kept the popup countdown paused for the complete dropdown interaction and while a rack correction request is being saved, even when the select temporarily loses focus or becomes disabled.
- Removed the page-navigation sound entirely while retaining the restrained normal accepted-scan confirmation.
- Added `rack_barcode.wav` as the dedicated accepted rack-barcode cue instead of reusing the print sound.
- Added `rack_outbound.wav`, a rising airy departure swoosh and success chime, for racks successfully released from Outbound and marked on the way.
- Moved `print_ready.wav` to actual print completion: opening a print preview is silent, and the cue plays only after the browser reports the print workflow completed.
- Added `destructive_action.wav`, a restrained downward wipe-and-settle confirmation for successful rack/bay clears, scan resets, Rush/Remake clears, list/date/item/user/rack/bay deletions, and maintained rule/contact removals.
- Stabilized Rush and Remake filter button geometry by reserving the indicator space in clear, alert, selected, and unselected states.
- Reworked active Scan filter pills with compact category-specific status, attention, route, and glass treatments plus clearer remove controls.
- Updated the audio manifest, audio guide, browser preview, README release summary, and browser/sound cache keys to v104.

## v103
- Reconciled the checked-in v102 browser/sound-cache baseline with the maintained release metadata and advanced the edited package to v103; missing historical v101/v102 changelog entries were not reconstructed or guessed.
- Added a distinct accepted-rack-barcode cue by mapping `RACK...` scans to the existing `print_ready.wav` identity instead of the normal item-scan sound.
- Changed normal accepted item scans to use the former page-navigation/notification cue and retained `sounds/scan_success.wav` in the pack without mapping it, leaving it available for a future purpose.
- Rebuilt `collapse_open.wav` and `collapse_close.wav` as shorter, quieter, wind-like swooshes for Scan-page and Bay Map expand/collapse actions.
- Redesigned the timed normal-stage scan result popup with a clearer status header, prominent order/item identity, customer information, piece details, workflow/location details, and a cleaner Admin/Supervisor rack correction control.
- Paused the scan-result countdown while the pointer is over the popup, while any popup control has focus, and while the native rack dropdown is open or being used.
- Redesigned the Scan filter drawer with clearer filter-group explanations, more readable sections, polished active-state controls, and a visible click-outside-to-close instruction.
- Added click-outside closing for the Scan and Bay Map filter drawers.
- Added true multi-select glass-type filtering, including one removable active-filter chip for each selected glass type.
- Updated global search so a selected line item opens the delivery-list stage containing its latest accepted scan; items without an accepted scan open at Staging.
- Kept the Scan-page delivery-list search text when switching stages on the same delivery date and cleared it only when the delivery date changes.
- Updated `sounds/audio_manifest.json`, the audio-pack guide and browser preview, the README release summary, and browser/sound cache keys for v103.

## v100
- Restored the v098 operational and interface sound set for login/logout, saves, email, navigation, undo/redo, imports, racks, bays, permissions, notifications, and machine events; printing remains intentionally silent.
- Unlocks Web Audio during the first pointer or keyboard gesture so asynchronous actions no longer lose browser audio permission.
- Plays an immediate synthesized cue on first use while each distinct packaged WAV loads in the background for later actions, preventing delayed sounds from arriving after the related operation.
- Rebuilt Scan Success as a bright five-note rising major chord with a stable low confirmation tone and high finishing sparkle.
- Reset the sound-volume storage key to restore a 100% default for operators whose earlier test setting may have remained muted.
- Added server-backed Manual Delivery List Edit pagination with 20 rows per request, accurate total counts, and offset-based Load More behavior.
- Made manual-edit rows collapsed by default while keeping Order, Item, Job Nr., customer, stage, and quantity visible in each summary ribbon.
- Added predictive 180 ms search for every typed Order or Job Nr. character and retained unsaved-edit confirmation before replacing displayed rows.
- Lowered the Scan filter drawer below the expanded sidebar stacking layer.
- Advanced browser cache keys to v100.

## v099
- Restored Scan-page responsiveness by removing the 300 ms whole-document custom-select polling loop and relying on the existing mutation/change synchronization.
- Stopped rendering both desktop rows and mobile cards during every Scan-page refresh; only the active viewport layout is now built.
- Coalesced search and filter paints with `requestAnimationFrame` and avoided rebuilding unchanged glass-type controls.
- Changed Manual Delivery List Edit saves to update the affected in-memory list and row in place instead of reloading the complete delivery-list catalog and modal.
- Replaced delayed WAV fetch/decode playback with short immediate synthesized operational cues.
- Limited sounds to scans, important completion events, bay assignment/removal, and machine faults; navigation, login/logout, save, print, email, undo/redo, and routine button actions are silent.
- Added one timed, nonblocking scan-result card for normal stages with success, notice, and error treatments plus the same item details shown by Last Scan.
- Added Admin/Supervisor rack or truck correction to successful staging scan cards while retaining existing backend permissions.
- Replaced the wide Scan-page filter rows with one organized multi-filter drawer, removable active-filter chips, and a combined remake/Rush attention marker.
- Added a Windows local-time fallback for the daily importer when the optional IANA timezone package is unavailable.
- Advanced browser cache keys to v099.

## v098
- Added the complete Barefoot Delivery Scanner Audio Language with 27 distinct mastered mono WAV cues.
- Replaced the four generic operational files with semantic cues for success, duplicate, warning, error, Rush, remake, completion, racks, bays, undo/redo, import, save, print, email, authentication, notifications, permissions, and future machine events.
- Updated the shared Web Audio loader to resolve semantic cue names, cache decoded buffers, retain the shared compressor/volume chain, and fall back safely when a WAV cannot load.
- Added context-aware scan selection so Rush and remake pieces have recognizable success sounds, duplicate scans differ from warnings, and rack/bay workflows use their own audio identities.
- Added audio feedback for rack completion/reopen/return, bay assign/remove/move, undo/redo, import start/complete, settings saves, print preview, sent email, sign-in/sign-out, notifications, and permission denial.
- Added `sounds/audio_manifest.json`, `sounds/README_AUDIO_PACK.md`, and `sounds/preview_audio_pack.html` for maintenance and browser-based auditioning.
- Preserved the v097 numbered SQLite migrations, database safeguards, and Azure SQL preparation without changing migration 001 or 002.
- Advanced browser and sound cache keys to v098.
- Packaged the release as `Delivery_List_Scanner_v098.zip` without live databases, WAL/SHM files, logs, caches, or verification artifacts.

## v097
- Added numbered, checksummed SQLite migrations with automatic legacy v096 baselining.
- Added verified pre-upgrade backups using SQLite's online backup API; failed upgrades preserve the backup and never recreate production data.
- Centralized the canonical logical database contract and documented SQLite-to-SQL Server type mappings.
- Added quantity, boolean, relationship, JSON, timestamp, and migration-history integrity validation.
- Added UTC audit and soft-delete fields to core mutable entities.
- Made scan, audit, and machine event histories append-only in SQLite and Azure SQL.
- Added production-ready machines, scanners, and machine-events tables without changing the UI.
- Added query-driven parity indexes and documented their purpose.
- Added explicit SQLite optimize, WAL checkpoint, and backup-before-VACUUM maintenance commands.
- Rebuilt the SQLite-to-Azure utility with preflight checks, dry-run-by-default behavior, transactional copy, reports, row-count checks, and deterministic checksums.
- Prevented production demo delivery-list seeding while preserving idempotent configuration seeds.
- Added database migration, preservation, integrity, and Azure contract tests.
- Matched the sign-in logo frame to the expanded desktop sidebar logo and removed the oversized login-only glow.
- Added the first editable four-cue WAV implementation used as the foundation for v098.

## v096
- Matched the sign-in page logo to the expanded desktop sidebar logo.
- Reduced the sign-in logo frame from 188 x 188 to 108 x 108.
- Kept the sign-in logo square, proportional, and filled with the same sampled dark-blue background color used by the expanded sidebar logo.
- Kept collapsed-sidebar and mobile-logo sizes unchanged.
- Advanced browser cache keys to v096.

## v095
- Reduced only the expanded desktop sidebar logo and its outline by 10%, from 120 x 120 to 108 x 108.
- Kept the collapsed sidebar logo and mobile logo sizes unchanged.
- Matched the inside of every logo outline to the logo image's sampled dark-blue background color: RGB 4, 43, 84.
- Preserved the square frame, proportional image rendering, and existing sidebar alignment.
- Advanced browser cache keys to v095.

## v094
- Corrected the combined Barefoot and Builders FirstSource logo frames so every displayed version is a true square.
- Set the sign-in logo frame to 188 x 188.
- Kept the collapsed sidebar logo frame at 48 x 48.
- Set the expanded desktop sidebar logo frame to 120 x 120.
- Set the mobile sidebar logo frame to 158 x 158.
- Kept `object-fit: contain` so the supplied logo remains proportional inside each square frame.
- Advanced browser cache keys to v094.

## v093
- Removed the `object-fit: cover` logo rule that was stretching the combined logo into the outline.
- Restored proportional `object-fit: contain` rendering for the sign-in, collapsed-sidebar, expanded-sidebar, and mobile logos.
- Kept the existing displayed logo heights while allowing each image width to follow its natural aspect ratio.
- Adjusted the subtle border, outline, and shadow to follow the actual rendered image rectangle rather than a wider forced frame.
- Preserved the v092 sound volume controls and scan-sound behavior unchanged.
- Advanced browser cache keys to v093.

## v092
- Tight-cropped the supplied combined Barefoot + Builders FirstSource logo so the rounded frame hugs the visible branding instead of surrounding large internal margins.
- Kept the rounded corners, subtle outline, and soft shadow for collapsed, expanded, mobile, and sign-in logo presentations.
- Added a persistent scanner-sound volume slider to the temporary Scan and Bay Map sound-test panels.
- Added a 0-400% floor-volume range with a 200% default for louder production-floor feedback.
- Added a shared Web Audio master-gain and compressor chain so success, notice, error, and 100% completion sounds all follow one volume setting.
- Synchronized every visible volume slider and stored the selected setting in browser local storage.
- Advanced browser cache keys to v092.

## v091
- Added rounded corners to the supplied Barefoot + Builders FirstSource logo in the sign-in screen and sidebar.
- Added a subtle light outline and soft shadow so the logo stands out slightly against the dark navigation background.
- Replaced the collapsed Barefoot-only sidebar image with the same combined Barefoot + Builders FirstSource logo used in the expanded sidebar.
- Kept the existing collapsed/expanded dimensions and sidebar navigation alignment unchanged.
- Advanced browser cache keys to v091.

## v090
- Replaced the existing combined Barefoot and Builders FirstSource brand image with the newly supplied logo.
- Kept the existing webapp asset filename so the sign-in screen, expanded desktop sidebar, and mobile drawer all use the new logo without duplicating brand logic.
- Preserved the collapsed sidebar's compact Barefoot icon so navigation remains readable at rail width.
- Advanced browser cache keys to v090.

## v089
- Combined the existing Barefoot & Company logo with the attached Builders FirstSource logo in a new stacked brand asset.
- Preserved the supplied Builders FirstSource red side lines, red square/white 1 mark, and dark blue text.
- Added `barefoot-builders-firstsource-logo.png` as the maintained combined logo asset.
- Updated the sign-in panel to use the combined Barefoot and Builders FirstSource logo.
- Updated the expanded desktop sidebar to crossfade from the compact Barefoot-only mark to the combined logo without changing the fixed sidebar brand-row height or moving the page selectors.
- Updated the mobile navigation drawer to use the combined logo.
- Kept the collapsed desktop sidebar on the smaller Barefoot-only mark because the Builders FirstSource text is not readable at icon size.
- Advanced browser cache keys to v089.

## v088
- Increased the normal Scan-page Recent Scans history from one row to two rows while retaining five rows in fullscreen.
- Restyled the global search input as a defined rectangular box with rounded corners, a visible border, and a subtle shadow while keeping the outer search wrapper removed.
- Added one shared Web Audio sound engine with synthesized cues so the project does not require packaged sound files.
- Added a bright ascending success cue for accepted scans.
- Added a distinct lower error cue for blocked or failed scans.
- Added a separate notice cue for duplicate, override, and other non-error scan outcomes.
- Added a fun completion arpeggio when the Scan-page stage progress transitions to 100%.
- Added the same completion cue when the Indian Trail Bay Map / In-Transit route progress transitions to fully Outbound and fully Received.
- Prevented initial loading of an already completed list from falsely triggering the completion sound by tracking progress per active list.
- Added temporary shared sound-test controls to the Scan and Bay Map scanner panels, plus an In-Transit 100% test button. These controls are intentionally marked for later removal after floor approval.
- Added static and browser-rendered tests for the two-row history, rounded search field, sound engine, completion wiring, and temporary test controls.
- Advanced browser cache keys to v088.

## v087
- Increased the expanded desktop sidebar logo by approximately 25%, from 74 x 74 to 93 x 93.
- Kept the collapsed sidebar logo at 48 x 48.
- Added `--app-sidebar-logo-expanded-size` as the single documented CSS setting for future logo-size adjustments.
- Updated both the base and final desktop ownership rules to use the shared logo-size variable, preventing later CSS overrides from using a different size.
- Preserved the fixed 126px brand section so page selector buttons and icons remain aligned between collapsed and expanded states.
- Advanced browser cache keys to v087.

## v086
- Reduced the expanded Barefoot sidebar logo by 65%, from 210 x 210 to 74 x 74.
- Kept the collapsed sidebar logo at 48 x 48.
- Reduced the fixed desktop sidebar brand section from 280px to 126px.
- Moved Home, Scan, Racks, Bay Map, and Admin upward in both collapsed and expanded states.
- Kept one identical fixed brand-section height in both states so every selector and icon remains vertically aligned during hover expansion.
- Advanced browser cache keys to v086.

## v085
- Fixed the expanded Barefoot logo being reduced by a later responsive sidebar rule.
- Added a final sidebar-specific logo ownership block so the expanded desktop logo renders up to 210 x 210.
- Kept the collapsed sidebar logo at 48 x 48.
- Made the top sidebar brand section a fixed 280px height in both collapsed and expanded states.
- Removed the hover-only brand-section height change that pushed Home, Scan, Racks, Bay Map, and Admin downward during expansion.
- Kept every page selector and icon at the same vertical position before, during, and after sidebar hover expansion.
- Added an explicit large-logo rule for the responsive mobile drawer as well.
- Advanced browser cache keys to v085.

## v084
- Reverted the collapsed sidebar Barefoot logo back to the smaller size so the rail stays clean when not hovered.
- Reduced the collapsed sidebar logo from 72 x 72 back to 48 x 48.
- Kept the large hover-only expanded brand presentation for the sidebar.
- Tuned the expanded sidebar logo to 210 x 210 so it fills about 75% of the expanded top brand section.
- Set the expanded sidebar top brand section height to 280px so the larger logo sits centered and proportionate.
- Advanced browser cache keys to v084.

## v083
- Removed the outer global-search container chrome so the centered search bar and Search button sit cleanly in the header without the larger wrapper box.
- Reduced the header global-search width from 640px to 560px for a cleaner centered layout.
- Increased the sidebar Barefoot logo by 50% in both collapsed and expanded states.
- Increased the collapsed sidebar logo size from 48 x 48 to 72 x 72.
- Increased the expanded sidebar logo size from 176 x 176 to 264 x 264.
- Added a hover-only larger sidebar logo area so the expanded logo stays centered without wasting space when collapsed.
- Advanced browser cache keys to v083.

## v082
- Restored the operations sidebar on the Scan page.
- Kept the sidebar collapsed by default and hover-expandable, matching Home, Racks, Bay Map, and Admin.
- Preserved the sign-in-screen behavior that hides the entire application shell until authentication succeeds.
- Retained the centered smaller global search bar and simplified Today’s Delivery Progress design from v081.
- Advanced browser cache keys to v082.
- Updated static and browser-rendered checks so the Scan page is protected as a sidebar-enabled workspace.

## v081
- Removed the operations sidebar from the Scan page so scanning uses the full available workstation width.
- Hid the entire application shell while the sign-in screen is active, preventing the sidebar from appearing behind the login interface.
- Centered the global search area in the utility header and reduced its desktop width to a maximum of 640 pixels.
- Added a narrower 430-pixel search treatment for medium desktop widths while preserving the responsive compact layout.
- Rebuilt Today's Delivery Progress with the date as the large upper-left focal point.
- Removed the extra Daily Operations label, explanatory sentence, Completion label, remaining-piece copy, and Open List text.
- Kept each stage card focused on the full stage name, scanned/total piece count, progress bar, and completion percentage.
- Allowed long stage names such as Outbound and Delivery to Customer to wrap without truncation or ellipsis.
- Advanced browser cache keys to v081.
- Added static and browser-rendered regression checks for login-shell hiding, Scan-page sidebar removal, centered search geometry, large date treatment, and fully visible stage labels.

## v080
- Increased the sidebar Barefoot logo size by roughly 30% for improved visibility.
- Enlarged the collapsed sidebar logo from 48 x 48 to 62 x 62.
- Enlarged the expanded sidebar logo from 136 x 136 to 176 x 176.
- Increased the sidebar logo area height so the larger brand mark stays centered cleanly.
- Advanced browser cache keys to v080.

## v079
- Cropped the Barefoot sidebar logo by 1 pixel on every edge, changing it from 200 x 200 to 198 x 198.
- Added `barefoot-logo-sidebar.png` as the new cropped sidebar logo file.
- Updated the sidebar brand image to use the new 198 x 198 cropped logo.
- Kept the login logo unchanged.
- Advanced browser cache keys to v079.

## v078
- Centered the provided Barefoot logo within the expanded sidebar.
- Kept the sidebar brand area at one fixed height in both collapsed and expanded states.
- Removed the vertical navigation shift that occurred when hovering over a collapsed page icon.
- Preserved identical button height, spacing, and vertical coordinates while labels reveal beside the icons.
- Removed the small horizontal button translation on hover so the active pointer target stays stable.
- Advanced browser cache keys to v078.

## v077
- Restored the Barefoot logo using the provided logo image and replaced the sidebar/login synthetic SVG mark.
- Reverted the favicon reference back to the original website icon path (`assets/delivery-list-scanner-icon.ico`).
- Forced the desktop sidebar to remain collapsed by default on every page and expand only while hovered.
- Ensured the expanded sidebar overlays the page instead of shifting the workspace.
- Centered collapsed navigation icons vertically within each page selector.
- Simplified the collapsed profile area so only the avatar shows in the bottom-left; full profile content appears only while expanded.
- Added automatic profile-menu close behavior when the pointer leaves the desktop sidebar.

# Delivery List Scanner - Ongoing Changelog

This is the single maintained changelog for the project. New versions are added at the top. The retained history available in the current project begins with the v037-v039 work and continues through the current release. Earlier version details were not present in the supplied project history and are not reconstructed or guessed here.

---

# Delivery List Scanner - v076 Sidebar Interaction Polish

Date: 2026-07-16

## Hover interaction refinement

- Added a short delayed collapse so the sidebar does not snap closed when the pointer briefly leaves the rail.
- Smoothed desktop expansion with a coordinated width, padding, shadow, and edge-highlight transition.
- Kept the main header and workspace fixed while the expanded sidebar floats above them.
- Added a restrained illuminated edge and deeper overlay shadow only while the sidebar is expanded.

## Logo, labels, and profile motion

- Refined the collapsed Barefoot mark to emphasize the building icon instead of shrinking the full wordmark into an unreadable thumbnail.
- Animated the full Barefoot wordmark and company line into view after the sidebar begins expanding.
- Replaced abrupt navigation-label display changes with opacity, width, and position transitions.
- Applied the same progressive reveal to the bottom-left profile name, role/station copy, chevron, and backend status.
- Kept the profile flyout usable while the sidebar or its descendants have focus.

## Fullscreen and mobile safeguards

- Verified the hover-preview rail expands while the application is in actual browser fullscreen mode.
- Added explicit mobile overrides so hover rules cannot narrow the responsive drawer on pointer-capable tablets.
- Preserved full logo, navigation labels, profile details, close control, and backdrop behavior in the mobile drawer.

## Validation and packaging

- Advanced browser cache keys to v076.
- Updated static shell contracts and the maintained browser visual smoke test for hover-overlay behavior.
- Passed 21 static-integrity checks and the browser-rendered visual smoke test.
- Returned the complete release without an `assets` folder, active database, secrets, caches, compiled files, diffs, or backups.

## Files edited

- `index.html`
- `styles.css`
- `README.md`
- `README_CHANGELOG.md`
- `docs/TESTING.md`
- `docs/TEST_REPORT.md`
- `docs/CODE_REFERENCE.md`
- `tests/test_static_integrity.py`
- `tests/test_visual_smoke.py`

---

# Delivery List Scanner - v075 Hover Preview Sidebar and Transparent Branding

Date: 2026-07-16

## Desktop sidebar behavior

- Changed the desktop navigation from a manually expanded/collapsed sidebar to a professional hover-preview rail.
- The sidebar now stays collapsed by default on desktop workstations and expands automatically only while hovered or focused.
- Kept the page content fixed so the expanded sidebar floats over the interface instead of pushing the header or main workspace sideways.
- Preserved the profile section at the bottom-left of the navigation rail and kept its detail flyout available from the sidebar.
- Simplified the desktop sidebar state so fullscreen and normal desktop mode share the same compact default behavior.

## Fullscreen and mobile behavior

- Reworked the shell synchronization helpers so fullscreen no longer blocks access to the sidebar; operators can hover the left rail and expand it while fullscreen is active.
- Kept the responsive under-960px mobile drawer workflow with the existing menu button, scrim dismissal, and close control.
- Limited the inner sidebar close button to mobile usage so desktop navigation stays clean and hover-driven.

## Barefoot logo refresh

- Replaced the packaged external Barefoot logo image dependency with a self-contained inline SVG brand mark.
- Removed the white logo tile treatment so the branding now renders on a transparent background in both the login panel and the sidebar.
- Embedded a matching SVG favicon so the release remains self-contained without an `assets` folder.

## Packaging and code maintenance

- Advanced browser cache keys to v075.
- Kept the release free of an `assets` folder while preserving the existing workflows, data, and Microsoft Graph email behavior.
- Updated the maintained README summary to document the hover-preview shell behavior and transparent branding approach.

## Files edited

- `index.html`
- `app.js`
- `styles.css`
- `README.md`
- `README_CHANGELOG.md`

---

# Delivery List Scanner - v074 Collapsible Operations Sidebar

Date: 2026-07-16

## Application navigation shell

- Moved Home, Scan, Racks, Bay Map, and Admin out of the crowded header and into one fixed left operations sidebar.
- Preserved the existing `data-page-target` navigation workflow and permission visibility rules instead of creating a second routing system.
- Added a clear active-page treatment, larger page icons/text, stable vertical spacing, and browser tooltips while the sidebar is compact.
- Reduced the utility header to the global search plus Print/Export, language, refresh, and fullscreen actions.
- Kept the global search wide and retained the established 16-pixel input and 15-pixel Search-button text.

## Collapsed, fullscreen, and responsive behavior

- Added expanded and collapsed desktop states using one maintained application-shell owner.
- Added page-aware first-run defaults: Bay Map uses the compact rail by default, while Home, Scan, Racks, and Admin remain expanded.
- Once an operator explicitly expands or collapses the sidebar, that preference is saved in browser storage and reused across pages and restarts.
- Fullscreen automatically uses the compact rail without overwriting the saved desktop preference.
- Added a mobile/tablet overlay drawer below 960 pixels with a menu button, backdrop dismissal, Escape-key dismissal, and automatic closure after page navigation.
- Preserved the prior sidebar state when leaving mobile layout or exiting fullscreen.

## Profile and account controls

- Moved the signed-in profile from the upper-right header to the bottom-left of the sidebar.
- Kept display name, role, assigned station, account identity, and Sign out in the existing shared account workflow.
- Added a compact avatar-only profile state when the desktop sidebar is collapsed.
- Positioned the account details panel beside the desktop sidebar and above the profile control inside the mobile drawer.
- Scoped legacy account-menu resets so older header-specific CSS cannot make the sidebar identity unreadable.

## Code maintenance and validation

- Removed the superseded repeated header ownership block while introducing the single v074 application-shell section.
- Added documented sidebar state helpers for responsive detection, default resolution, persistence, desktop toggling, and mobile drawer toggling.
- Advanced browser cache keys to v074.
- Added static contracts and browser-rendered checks for profile placement, sidebar collapse/expand, Bay Map compact default, responsive drawer behavior, Spanish labels, and non-overlapping utility controls.
- Kept scanning, filtering, rack, bay, SDI/Rush/Remake, printing, database, authentication, and Microsoft Graph business logic unchanged.

## Files edited

- `index.html`
- `app.js`
- `styles.css`
- `README.md`
- `README_CHANGELOG.md`
- `docs/TESTING.md`
- `docs/TEST_REPORT.md`
- `docs/CODE_REFERENCE.md`
- `tests/test_static_integrity.py`
- `tests/test_visual_smoke.py`

---

# Delivery List Scanner - v073 Priority Queue and Dashboard Repair

Date: 2026-07-16

## Rush / Remake Current Priority Work

- Traced the unreadable priority queue to a stale v072 shell/cache-key package mismatch: the release contained newer JavaScript and CSS while `index.html` still referenced v071 browser assets and omitted several v072 markup anchors.
- Advanced both browser asset cache keys to v073 so the browser is forced to load the maintained JavaScript and CSS together.
- Restored the missing Bay recent-scan count label, user-account identity field, and multi-filter help markup expected by the maintained v072 code.
- Strengthened the SDI priority-card ownership selectors so older generic modal/button rules cannot collapse the job cards into separator lines.
- Preserved real collapsed-group behavior by explicitly keeping hidden item panels hidden.
- Verified a 30-job priority queue renders readable job, customer, Rush/Remake, date, item-count, and expand/collapse information.

## Header search and scrollbar

- Increased the global search surface beyond the previous 760-pixel legacy cap.
- Increased the global search input text to 16 pixels and restored the Search button text to 15 pixels.
- Increased the maintained vertical scrollbar from 11 pixels to 15 pixels with a larger minimum thumb.

## Today's Delivery Progress

- Rebuilt the Today progress panel with a clearer operations heading, date badge, stronger surface treatment, and stage-specific accent colors.
- Reworked each stage card to show scanned/total pieces, completion percentage, progress, remaining pieces, and a persistent Open List action.
- Added keyboard activation for the focusable Today stage cards.

## Packaging and validation

- Advanced the complete release to v073.
- Kept the release free of an `assets` folder, active database, Graph secrets, caches, compiled files, diffs, and backups.
- Updated maintained tests to protect the v073 cache keys, restored markup anchors, wider search, larger scrollbar, Today progress components, and SDI priority-card geometry.
- Updated the maintained validation runner to exit each isolated pytest process immediately after pytest returns, preventing passing modules from lingering during interpreter shutdown.

## Files edited

- `index.html`
- `app.js`
- `styles.css`
- `README.md`
- `README_CHANGELOG.md`
- `docs/FOLDER_CLEANUP_GUIDE.md`
- `docs/TEST_REPORT.md`
- `docs/CODE_REFERENCE.md`
- `tests/test_static_integrity.py`
- `tests/test_visual_smoke.py`
- `tools/run_full_validation.py`

---

# Delivery List Scanner - v072 Scan Workflow and Interface Polish

Date: 2026-07-16

## Scan-page filters

- Replaced the single-active-filter behavior with one maintained multi-filter workflow.
- Filters now use OR logic within the same category and AND logic between Status, Attention, and Route categories.
- `All` clears every active filter, while desktop and mobile filter controls stay synchronized through shared state and `aria-pressed` values.
- Existing text search and glass-type filtering continue to apply after the selected status/attention/route filters.

## Compact scan history

- Reduced the normal Scan-page Recent Scans list from two rows to one row.
- Reduced the normal Bay Map scanner Recent Scans list from two rows to one row.
- Preserved the denser fullscreen history: five rows on the main Scan page and two rows in the Bay Map scanner.
- Updated the visible count labels so normal mode reports `Latest 1` and fullscreen mode reports the expanded count.

## SDI Rush / Remake priority workspace

- Rebuilt the Current Priority Work cards for stronger contrast, clearer job/customer/date/count hierarchy, and readable item-level actions.
- Current groups now sort by earliest required priority date first; undated work remains visible after dated work.
- The first group opens when fresh workspace data loads, but users can now collapse it without the interface immediately reopening it.
- Stale expanded-group state is removed safely when the workspace changes.
- Added behavioral coverage confirming earlier Rush/Remake dates appear ahead of later priority work.

## Header and application polish

- Increased the header page-selector font size and button footprint while retaining responsive reductions at narrower widths.
- Enlarged the global search field and search button.
- Expanded and restyled the top-right profile card with a larger avatar, assigned station, role, and account identity in the dropdown.
- Added a maintained custom vertical scrollbar treatment for the app shell and major scrollable panels.
- Removed the Bay scanner Add/Remove selector jump by neutralizing the inherited label transform and using a simple border/background/shadow hover.

## Packaging and version maintenance

- Advanced the release and browser cache keys from v071 to v072.
- Confirmed the returned release ZIP does not require or include an `assets` folder, per the maintained deployment decision.
- Continued excluding the active `data` folder, protected Graph secrets, caches, compiled files, diffs, and temporary test artifacts.

## Validation

- JavaScript syntax passed.
- Python compilation passed.
- CSS parsing passed with no syntax errors.
- Targeted source/backend tests passed.
- Browser-rendered interaction and visual smoke coverage passed, including multi-filter logic, compact histories, profile layout, SDI expansion, and stable Bay selector hover.
- Verified **65 passed and 1 optional Azure SQL translation test skipped** across isolated maintained test-module runs.
- Updated the validation runner to isolate test modules and retry one environment timeout without masking real assertion failures.

## Files edited

- `index.html`
- `app.js`
- `styles.css`
- `delivery_store.py`
- `README.md`
- `README_CHANGELOG.md`
- `docs/PROJECT_REVIEW.md`
- `docs/TESTING.md`
- `docs/TEST_REPORT.md`
- `docs/AZURE_DEPLOYMENT.md`
- `docs/FOLDER_CLEANUP_GUIDE.md`
- `docs/CODE_REFERENCE.md`
- `tests/test_static_integrity.py`
- `tests/test_extended_workflows.py`
- `tests/test_visual_smoke.py`
- `tools/run_full_validation.py`

---

# Delivery List Scanner - v071 Project Review and Maintained Baseline

Date: 2026-07-16

## Review scope

- Reviewed the complete supplied v070 project before beginning additional feature work.
- Confirmed the browser, HTTP, business-rule, SQLite, Azure-readiness, startup, printing, and Microsoft Graph ownership boundaries.
- Added `docs/PROJECT_REVIEW.md` as the maintained architecture, risk, duplication, packaging, and future-editing baseline.
- No scan, import, rack, bay, SDI, Rush/Remake, print/export, authentication, report, database, or email behavior was intentionally changed.

## Code integrity and duplication review

- Confirmed no duplicate Python class methods, top-level JavaScript functions, HTTP route checks, or HTML IDs.
- Confirmed frontend API paths resolve to maintained server routes.
- Documented the large/high-risk store and server functions that require targeted regression tests before refactoring.
- Identified CSS override accumulation as the main current duplication concern: repeated selectors include both intentional revision layers and a small set of exact duplicate declarations.
- Deferred broad CSS consolidation because the current interface is working and source-order changes could cause visual regressions.

## Microsoft Graph review

- Confirmed Graph uses the existing email outbox and automatic manifest/ready-notice workflows rather than a parallel queue.
- Confirmed client-secret and managed-identity authentication, in-memory token caching, one 401 refresh retry, Sent Items support, SMTP fallback, and Draft mode remain intact.
- Confirmed browser-facing settings expose readiness booleans without returning the client secret.
- No live BLDR email was sent because tenant credentials and administrator authorization were not available in the review environment.

## Version and packaging maintenance

- Advanced the maintained release and browser asset cache keys from v070 to v071.
- Updated current README, testing, test-report, Azure deployment, and cleanup documentation.
- Preserved the supplied release structure without adding a database, protected Graph configuration, missing visual assets, caches, compiled files, diffs, or backup files.

## Validation

- JavaScript syntax passed.
- Python compilation passed.
- CSS parsing and HTML ID integrity passed.
- Browser-rendered visual smoke coverage passed.
- Full pytest result in this environment: **63 passed, 1 skipped**.
- The skipped test requires the optional Azure SQL translation dependency `sqlglot`, which is listed in `requirements.txt` and is not required for local SQLite operation.

## Files added or edited

- `index.html`
- `README.md`
- `README_CHANGELOG.md`
- `docs/PROJECT_REVIEW.md`
- `docs/TESTING.md`
- `docs/TEST_REPORT.md`
- `docs/AZURE_DEPLOYMENT.md`
- `docs/FOLDER_CLEANUP_GUIDE.md`
- `docs/CODE_REFERENCE.md`
- `tests/test_static_integrity.py`

---

# Delivery List Scanner - v070 Microsoft Graph Email Integration

Date: 2026-07-16

## Microsoft Graph transport

- Added app-only Microsoft Graph email delivery to the existing customer-email outbox and automatic manifest/ready-notice workflow.
- Sends as `BarefootNC.Glass@bldr.com` through the Graph `/users/{sender}/sendMail` endpoint.
- Preserves SMTP as an optional fallback and Draft mode when no transport is configured.
- Added in-memory token caching, one authorization refresh retry, Sent Items support, and sanitized Graph error reporting.
- Added local client-secret authentication and Azure App Service managed-identity authentication without adding a second email queue or API.

## Secure local Windows setup

- Added `Configure-MicrosoftGraphEmail.bat` and `Configure-MicrosoftGraphEmail.ps1`.
- The setup utility defaults the sender to `BarefootNC.Glass@bldr.com` and the test recipient to `brandon.m.smith@bldr.com`.
- The app-registration client secret is protected with Windows DPAPI and stored under `data\secrets`; it is never written in plain text.
- The normal launcher decrypts the secret only in memory for the current Windows account and passes it to the Python child process.

## Admin email interface

- Reworked the existing SMTP-only readiness panel into one Email Delivery panel.
- Displays Microsoft Graph/SMTP/Draft status, sender, authentication mode, client-ID readiness, and Sent Items behavior without exposing credentials.
- Prepopulates the controlled test recipient and reports which transport sent the test.
- Retains the existing customer rules, global CC rules, outbox, manifest drafts, and ready-notice automation.

## Azure readiness

- Added managed-identity Graph configuration to `.env.azure.example`.
- Added a maintained Microsoft Graph setup and Exchange Online RBAC guide.
- Azure App Service can use its system-assigned identity with no client secret after the future cutover.

## Database and deployment status

- SQLite remains the active/default backend.
- No schema migration is required.
- No live email was sent during packaging because the BLDR tenant ID, client ID, secret, and administrator consent were not available in the build environment.

## Files added or edited

- `delivery_store.py`
- `app.js`
- `index.html`
- `Start-DeliveryScannerWebApp.ps1`
- `Configure-MicrosoftGraphEmail.bat`
- `Configure-MicrosoftGraphEmail.ps1`
- `.env.azure.example`
- `.dockerignore`
- `README.md`
- `README_CHANGELOG.md`
- `docs/MICROSOFT_GRAPH_EMAIL.md`
- `docs/AZURE_DEPLOYMENT.md`
- `docs/FOLDER_CLEANUP_GUIDE.md`
- `docs/TESTING.md`
- `docs/TEST_REPORT.md`
- `tests/test_graph_email.py`
- `tests/test_static_integrity.py`

---

# Delivery List Scanner - v069 Header, SDI, Bay Scanner, Transit, and Page Polish

Date: 2026-07-16

## Header and profile redesign

- Removed the redundant **Glass Delivery Scanner / Plant Operations** copy from the application header; the Barefoot logo now owns the brand area.
- Enlarged the five page-selection buttons and labels and aligned the navigation workspace farther left.
- Expanded the profile summary into a fuller identity card with larger initials, name, role, and a clear dropdown indicator.
- Added one explicit profile-menu toggle handler so the entire painted profile card reliably opens and closes the existing Sign out menu.
- Preserved Print/Export directly before the language control in both English and Spanish.
- Added Spanish translations for the rebuilt Bay scanner and Rush/Remake workspace labels.

## Scan-page progress layout

- Moved the quantity/percentage text beneath the progress bar.
- Expanded the progress track across the complete scanner-header width.
- Kept the stage title centered and preserved the existing contained shimmer and completion animation.
- Standardized the same geometry across Staging, Outbound, Indian Trail, Greenville, CPU, and DTC.

## Bay scanner command consolidation

- Moved the sticky Bay scanner slightly closer to the Bay Map controls.
- Combined Add/Remove direction and Target Bay into one compact command surface.
- Kept the target field, Clear action, scanner input, Undo/Redo, manual scan, and history on the existing workflow.
- Reduced unnecessary vertical spacing without hiding operational controls or adding internal scrolling.

## Rush / Remake SDI workspace rebuild

- Reorganized the modal into a three-step workflow: find the job/piece, choose exact glass items, then configure handling.
- Placed exact item selection and Rush/Remake options side by side on workstation screens.
- Added a live selected-item/missing-item summary and disabled unsafe actions until the required selections are valid.
- Corrected inherited label/grid rules that caused oversized checkboxes, striped empty areas, overlapping controls, and misplaced action fields.
- Preserved predictive Job Nr./SO/Order lookup, Bay Code filtering, exact-item Remake handling, individual clearing, priority dates, and direct-to-truck rules.

## Pieces on the Way physical rack rules

- The In-Transit Manifest and Bay Map rack list now include only racks/trucks whose barcode was actually scanned Outbound.
- A transportation method must be active, have **In Transit** status, and have a departure timestamp before its pieces or rack appear on the way.
- Merely assigning glass to a rack no longer makes it appear in transit.
- Duplicate active rack assignments for the same physical item/rack use the largest assigned quantity rather than inflating totals.

## Today’s Outbound quantity correction

- Replaced the single-Indian-Trail-list assumption with aggregation across every active Indian Trail list for the requested delivery date.
- Physical items are deduplicated by normalized Order Nr./Item Nr. across updated or split list copies.
- Outbound counts now use the highest scan quantity across every active Outbound copy, departed rack quantity, and the downstream Indian Trail received quantity.
- Received items therefore cannot disappear from Outbound totals, including the reported six-piece production case.
- The frontend now prioritizes the date-specific backend summary instead of a potentially incomplete first list in the client list array.

## Scan, Racks, and Admin page polish

- Applied the same layered background, framed page headings, rounded operational cards, borders, and soft shadows used by the Home and Bay Map pages.
- Preserved all existing table, scanner, rack, import, user, route-rule, and administration workflows.

## Database and deployment status

- SQLite remains the active/default backend.
- No schema migration or new API endpoint is required.
- Azure SQL remains opt-in and inherits the date-wide physical-item aggregation.

## Validation

- Full maintained validation: **58 tests passed with no skips**.
- Browser-rendered checks verify the complete profile click target, larger navigation, full-width progress track, compact Bay target command, rebuilt SDI modal, Spanish header containment, and polished page surfaces.
- SQLite regressions verify that a merely assigned rack is excluded from Pieces on the Way, an Outbound-scanned rack appears correctly, and six received pieces in a second active Indian Trail list increase both Received and Outbound totals.

## Files edited

- `app.js`
- `styles.css`
- `delivery_store.py`
- `server.py`
- `index.html`
- `README.md`
- `README_CHANGELOG.md`
- `docs/AZURE_DEPLOYMENT.md`
- `docs/CODE_REFERENCE.md`
- `docs/TESTING.md`
- `docs/TEST_REPORT.md`
- `tests/test_static_integrity.py`
- `tests/test_store_workflows.py`
- `tests/test_visual_smoke.py`

---

# Delivery List Scanner - v068 Header Redesign, Contained Progress Motion, and Outbound Reconciliation

Date: 2026-07-16

## Scan-page progress cleanup

- Removed the temporary administrator progress-animation test button and its JavaScript/CSS state.
- Recentered the stage title across the full scanner header.
- Clipped the idle shimmer, moving gradient, and completion sparkle to the progress-track boundary.
- Removed the header-wide completion pulse that could make the entire scanning panel appear to shimmer.
- Preserved smooth quantity changes, idle motion, completion feedback, consistent sizing, and reduced-motion support.

## Shared Bay Map route progress

- Reused the existing mirrored Outbound/Received progress component inside the large In-Transit center card.
- The compact Bay scanner and the main route card now calculate and display the same independent percentages.
- Both meters fill toward the center and use the same one-time completion celebration.
- The existing truck animation, pieces-in-transit quantity, rack summary, and manifest button remain intact.

## Indian Trail Outbound quantity reconciliation

- Replaced the single-Outbound-list assumption with aggregation across every active Outbound list for the active Indian Trail delivery date.
- Matching continues to prefer the shared source ID and falls back to normalized Order Nr./Item Nr. for legacy rows.
- Duplicate stage copies use the maximum scanned quantity per physical item instead of being summed.
- A quantity already received at Indian Trail is treated as physically sent, so the Outbound side can never display behind the Received side.
- This corrects the production case where received pieces were visible at Indian Trail but six of them were absent from the Bay Map Outbound count.

## Complete application-header redesign

- Rebuilt the header as three owned zones: brand, navigation/search workspace, and command center.
- Added a polished grouped navigation rail with clearer active, hover, and keyboard-focus states.
- Added a framed global-search workspace with a dedicated Search action.
- Grouped Print/Export, language, refresh, fullscreen, and profile into one consistent command area.
- Print/Export remains immediately left of the language control.
- English and Spanish use the same geometry; translated labels no longer trigger separate ad-hoc header layouts.
- Wide screens use one row, common workstations use a deliberate command row plus navigation/search row, and narrow screens stack predictably.
- Preserved the full profile click target and existing Sign out dropdown behavior.

## Database and deployment status

- SQLite remains the active/default backend.
- No schema migration or new API endpoint is required.
- Azure SQL remains opt-in and inherits the shared Outbound reconciliation logic.

## Validation

- Full maintained validation: **55 tests passed with no skips**.
- Browser-rendered checks verify the redesigned English/Spanish header, centered scanner title, track-confined shimmer, removal of the debug control, and both mirrored route meters.
- SQLite regression testing verifies split active Outbound lists are aggregated and that Indian Trail Received quantities cannot exceed the displayed Outbound quantity.

## Files edited

- `app.js`
- `styles.css`
- `delivery_store.py`
- `index.html`
- `README.md`
- `README_CHANGELOG.md`
- `docs/AZURE_DEPLOYMENT.md`
- `docs/CODE_REFERENCE.md`
- `docs/TESTING.md`
- `docs/TEST_REPORT.md`
- `tests/test_static_integrity.py`
- `tests/test_store_workflows.py`
- `tests/test_visual_smoke.py`

---

# Delivery List Scanner - v067 Animated Progress, Live Bay Counts, and Header Alignment

Date: 2026-07-16

## Scan-page progress experience

- Standardized the progress summary across every stage as `Qty: scanned/total · percentage`.
- Removed the stage-specific verb from the quantity row; the stage name remains in the larger scanner title.
- Fixed the label area and progress track dimensions so changing between Staging, Outbound, Indian Trail, Greenville, CPU, and DTC does not resize the meter.
- Added a smooth eased fill, continuously moving color gradient, and subtle idle light sweep so the scanning workflow feels responsive even between scans.
- Added a short sparkle/header celebration when a stage newly reaches 100 percent.
- Added reduced-motion support for users who disable animation at the operating-system/browser level.
- Added a temporary administrator-only **Test** button in the scanner title that previews the complete animation without changing scan data.

## Mirrored Bay Map route meter

- Added one dual-sided progress meter to the existing Bay Map scanner route summary.
- Outbound fills from the left toward the center; Received fills from the right toward the center.
- Both sides retain their own quantities and percentages.
- When both stages newly reach 100 percent, the fills meet in the center and trigger a brief celebration.
- Completion animation state is tracked so the 12-second refresh does not replay the celebration repeatedly.
- The existing pieces-in-transit pill remains clickable and continues opening the existing In-Transit Manifest.

## Bay Map Outbound count correction

- Replaced the fragile Order Nr./Item Nr.-only Outbound summary join with shared `source_id` matching and a legacy fallback.
- Sent quantities are capped to the corresponding Indian Trail destination quantity, preventing duplicate rows from inflating the route count.
- Updated the in-transit matching path to prefer the same shared source identity.
- Extended the existing polling loop so Bay Map route counts refresh every 12 seconds while visible, allowing Outbound scans from another workstation to appear without manually reopening the page.

## English and Spanish header alignment

- Moved Print/Export immediately left of the language button in both languages.
- Anchored Print/Export, language, refresh, fullscreen, and profile controls as one deliberate upper-right action cluster.
- Wide screens match the supplied reference layout; narrower workstations use a controlled second row rather than translated labels pushing controls out of place.
- Preserved the five-button navigation row and responsive two-column mobile navigation.

## Database and deployment status

- SQLite remains the active/default backend.
- No schema migration or new API endpoint is required.
- Azure SQL remains opt-in and inherits the shared source-identity summary behavior.

## Validation

- Full maintained validation: **54 tests passed with no skips**.
- Browser-rendered checks verify consistent `Qty:` text, active/idle progress animation, temporary debug completion, mirrored Bay progress, Spanish header containment, Print/Export ordering, and right-corner alignment.
- SQLite integration verifies a departed two-piece Indian Trail rack updates the Bay Map Outbound quantity and that receiving one piece changes only the Received side.

## Files edited

- `app.js`
- `styles.css`
- `delivery_store.py`
- `index.html`
- `README.md`
- `README_CHANGELOG.md`
- `docs/AZURE_DEPLOYMENT.md`
- `docs/CODE_REFERENCE.md`
- `docs/TESTING.md`
- `docs/TEST_REPORT.md`
- `tests/test_static_integrity.py`
- `tests/test_store_workflows.py`
- `tests/test_visual_smoke.py`

---

# Delivery List Scanner - v066 Expanded Print Filters, Interactive Scan Confirmations, Permission Help, and Guided Lookups

Date: 2026-07-15

## Print / Export glass-type ribbons

- Glass-type category ribbons now start expanded whenever the Print / Export GUI opens for the first time.
- Users can still collapse individual categories, and their open/collapsed choices remain preserved during same-session re-renders.
- The existing glass-type category renderer and selection logic are reused; no second print filter component was added.

## Timed Outbound and Indian Trail scan confirmations

- The shared timed scan-confirmation lifecycle now pauses both the numeric countdown and progress-bar animation while the mouse is over the popup.
- The timer resumes when the pointer leaves the popup.
- Clicking the Outbound rack confirmation opens the existing stage **All Scans** GUI.
- Clicking the Indian Trail receiving/bay confirmation opens the existing **All Bay Scans** GUI.
- Buttons, bay selectors, and move controls remain independently clickable and do not accidentally open history.
- Keyboard users can focus the confirmation and press Enter or Space to open the appropriate history GUI.
- A newly completed scan still takes priority: the shared mount function removes any older timed confirmation before showing the new result.
- Added a short visible hint explaining that the popup can be clicked to open scan history.

## Permission descriptions

- Added one maintained short description for every backend permission.
- Each permission card now shows a clear label plus a smaller explanation of exactly what the permission allows the role to access or change.
- The descriptions remain grouped under the existing Scanning, Delivery Lists, Exceptions, Admin, Stations, Indian Trail/Bays, and Racks sections.
- English labels and descriptions are included in the existing Spanish translation system.

## Lookup Manager redesign

- Replaced the three competing lookup columns with one focused workspace.
- Added large Product, Route, and Process State type tabs with live counts.
- Added a guided editor that explains the saved value, display label, route-only category, and route match-term fields.
- Added a live preview showing what users will see and which value is actually stored.
- Route-only fields remain hidden for Product and Process State entries.
- Added one searchable active library instead of showing all lookup types at once.
- Existing lookup rows now show their source, saved value, label, category, and match terms.
- **Use / edit** loads an existing value back into the same editor; saving uses the existing backend upsert endpoint.
- Added a Clear Form action and preserved the shared save-success confirmation.
- No new database table, schema migration, or parallel lookup API was added.

## Spanish and accessibility coverage

- Added Spanish translations for the redesigned Lookup Manager, permission names, permission descriptions, search instructions, and popup history hint.
- Timed confirmations now expose a keyboard-focusable action target and an All Scans accessibility label.
- Lookup and permission layouts include narrow-screen rules so the additional explanation text remains readable.

## Database and deployment status

- SQLite remains the active/default backend.
- Azure SQL remains opt-in and uses the same shared permissions and lookup workflows.
- No database schema migration is required for v066.

## Validation

- Full maintained validation: **53 tests passed with no skips**.
- Browser-rendered checks confirm Print / Export groups open expanded, permission descriptions render, the guided Lookup Manager can load and filter values, and timed confirmations pause/resume, yield immediately to newer scans, and open All Scans correctly.
- Static checks confirm every backend permission has exactly one maintained description and the popup priority behavior continues to use one shared timed-confirmation mount path.

## Files edited

- `app.js`
- `styles.css`
- `index.html`
- `README.md`
- `README_CHANGELOG.md`
- `docs/AZURE_DEPLOYMENT.md`
- `docs/CODE_REFERENCE.md`
- `docs/TESTING.md`
- `docs/TEST_REPORT.md`
- `tests/test_static_integrity.py`
- `tests/test_visual_smoke.py`

---

# Delivery List Scanner - v065 Bay Scanner Transit Control and Item-Aware SDI

Date: 2026-07-15

## Bay Map scanner header and in-transit control

- Increased the Bay Map scanner title to a clearer 15-pixel compact size.
- Fullscreen raises the same title to 21 pixels without changing the main Scan-page title.
- Replaced the center Outbound-to-Received route content with one focused **pieces in transit** pill.
- The pill shows only the live piece quantity and opens the existing In-Transit Manifest when clicked.
- The existing manifest, API, modal lifecycle, permissions, and close behavior are reused; no parallel transit GUI was added.

## Adaptive current-bay location

- The large current-location value now supports multi-word bay names such as `Manual Overflow`.
- The label starts at the preferred large size and automatically reduces one pixel at a time only when required to fit.
- Multi-word names can wrap and balance across lines, remain centered, and retain a 15-pixel minimum.
- Fitting reruns after render, resize, fullscreen changes, and language changes so translated bay labels remain readable.

## Predictive SDI lookup and bay selector

- The Job Nr. / SO / Order field now uses a predictive dropdown backed by live Indian Trail destination rows.
- Suggestions include job/order, customer, missing-item count, total item count, and associated bay codes.
- Added a real Bay Code dropdown populated from active non-spacer bays.
- Selecting a bay narrows the workspace to that bay's job context while still including unassigned missing pieces for the selected job.
- The existing custom-select component is reused for the Bay Code and Rush/Remake selectors.

## Missing-item-aware Rush selection

- The SDI workspace now calculates physical fulfillment from active Indian Trail bay assignments.
- `PreAssigned` glass is treated as reserved but still missing; only physically assigned/received quantities count as present.
- Job-level Rush/Remake actions automatically select only items with a missing quantity.
- A fully occupied `1/1` item is skipped by a job-level Rush and cannot be selected while the action type is Rush.
- The item list clearly shows quantity in bay, missing quantity, product, dimensions, and current bay.

## Exact broken-piece Remakes

- Users can select an exact Order Nr. and Item Nr. from the predictive workspace.
- A completed in-bay item remains selectable when the action type is Remake.
- Marking that exact item as a Remake clears only its active physical bay assignment, records the removal event/audit, and makes the item missing.
- The Remake state and priority date continue to propagate through Staging, Outbound, and the applicable destination-stage copies using the existing `source_id` workflow.
- Other items on the job remain in their bays and keep their own Rush/Remake state.

## Current marks and individual clearing

- Current Rush/Remake work is grouped by Job Nr. inside the SDI GUI.
- Clicking a group expands its exact items with product, bay, and mark type.
- Each item has its own **Clear item** action so one Rush/Remake can be cleared without clearing the rest of the job.
- Clearing a Remake does not restore broken glass to a bay.
- Clearing a Rush removes only a bay preassignment created by the Rush workflow itself; normal Outbound preassignments are preserved.

## Spanish and documentation coverage

- Added Spanish translations for the predictive lookup, exact-item instructions, bay selector, missing/fulfilled descriptions, current marks, and dynamic pieces-in-transit text.
- New JavaScript functions and Python helpers include purpose/effects/flow notes for future maintenance.
- `docs/CODE_REFERENCE.md` is regenerated during release validation.

## Database and deployment status

- SQLite remains the active/default backend.
- No database schema migration is required for v065.
- The future Azure SQL adapter uses the same shared store methods and remains opt-in.

## Validation

- Full maintained validation: **52 tests passed with no skips**.
- Browser-rendered checks confirm the clickable transit pill, existing manifest opening, compact title size, adaptive `Manual Overflow` fitting, predictive SDI layout, safe default item selection, Rush disabling completed pieces, Remake enabling exact pieces, and individual clear controls.
- SQLite integration checks confirm job-level Rush skips fulfilled `1/1` pieces, exact Remake removes only the broken item, stage propagation remains intact, and clearing one item preserves another item's mark.
- The new SDI workspace endpoint is exercised through the real local HTTP server.

## Files edited

- `app.js`
- `styles.css`
- `delivery_store.py`
- `server.py`
- `index.html`
- `README.md`
- `README_CHANGELOG.md`
- `docs/AZURE_DEPLOYMENT.md`
- `docs/CODE_REFERENCE.md`
- `docs/TESTING.md`
- `docs/TEST_REPORT.md`
- `tests/test_extended_workflows.py`
- `tests/test_server_http.py`
- `tests/test_static_integrity.py`
- `tests/test_visual_smoke.py`

---

# Delivery List Scanner - v064 Print Route Cleanup, Stable Language Layout, Save Confirmations, and Clean Launcher

Date: 2026-07-15

## Print/export route display

- Standard Indian Trail route values such as `IT`, `INT`, and `Indian Trail` remain stored internally for routing but now display as blank on delivery-list printouts and supported exports.
- CPU, DTC, GNV, and custom route codes remain visible so exception destinations stand out clearly.
- Rack packing lists and saved customer manifest print pages use the same public route-label helper rather than maintaining separate route-display rules.
- Blank Indian Trail cells remain truly blank instead of displaying a fallback dash.

## Fullscreen Scan-page history

- The main Scan page now shows five previous scans while fullscreen is active.
- Normal-window Scan history remains at two rows.
- Bay Map scan history remains unchanged.

## Spanish layout stability

- The language system now writes the active language to `body[data-language]` so CSS can reserve the correct space before translated controls reflow.
- The five primary page buttons use one predictable grid instead of wrapping unpredictably.
- Spanish navigation receives dedicated spacing and a controlled second utility row on narrower workstations.
- Mobile navigation uses a clean two-column grid so longer Spanish labels remain aligned and readable.
- At common 1366-pixel workstation width, the Spanish header uses a compact logo treatment so the translated navigation remains neat without an oversized first row.

## Shared save confirmation

- Added one `showSaveConfirmation()` helper that reuses the existing polished action-feedback dialog.
- Explicit save/create workflows now confirm success for stations, racks, rack sets, Bay Map groups/bays/layout, role permissions, bay scanner rules, customer email settings, customer route rules, users, passwords, user settings, and manual line-item edits.
- Scans, notification acknowledgments, background refreshes, and destructive actions do not use this save popup.
- Repaired the Lookup Manager form, whose existing submit handler referenced a missing `saveManualEditLookup()` function; lookup values now save correctly and use the same confirmation popup.

## Windows launcher and terminal behavior

- Python now starts with PowerShell `-NoNewWindow`, preventing the scanner launcher from creating a second visible terminal that can later steal focus.
- The supported release contains one launcher BAT: `Start-DeliveryScannerWebApp.bat`.
- If a separate terminal still opens with a working directory under another project, such as Showers Programmer, that terminal is being started by that other program or updater rather than this scanner launcher.

## Demo-data behavior

- Existing production databases are not seeded or refreshed from `sample-delivery-list.json`.
- Demo rows that may already have been inserted by an older release are not automatically deleted because the current database must be reviewed before any data can be classified safely as demo-only.

## Folder cleanup and documentation

- Added `README.md` as the concise local startup guide.
- Added `docs/FOLDER_CLEANUP_GUIDE.md` with exact keep/remove guidance.
- Consolidated current maintenance documents under `docs/` with stable filenames instead of adding another set of version-suffixed files.
- This `README_CHANGELOG.md` is now the one ongoing changelog; future releases should prepend their changes here.

## Database and deployment status

- SQLite remains the active/default backend.
- No schema migration was added in v064.
- Azure SQL remains opt-in and retains the same route-display, save, and startup behavior where applicable.

## Validation

- Full maintained validation: **50 tests passed with no skips**.
- Browser-rendered checks passed at 1600×1000 and 1366×768, including Spanish navigation geometry and five fullscreen recent-scan rows.
- Print helper tests confirm Indian Trail stays blank while CPU, DTC, and GNV remain visible.
- Windows launcher behavior is statically validated; one live floor-PC launch remains required because this environment is not Windows.

## Files edited

- `app.js`
- `styles.css`
- `server.py`
- `delivery_store.py`
- `index.html`
- `Start-DeliveryScannerWebApp.ps1`
- `README.md`
- `README_CHANGELOG.md`
- `docs/FOLDER_CLEANUP_GUIDE.md`
- `docs/AZURE_DEPLOYMENT.md`
- `docs/CODE_REFERENCE.md`
- `docs/TESTING.md`
- `docs/TEST_REPORT.md`
- `tests/test_static_integrity.py`
- `tests/test_core_helpers.py`
- `tests/test_azure_adapter_and_rendering.py`
- `tests/test_visual_smoke.py`
- `tools/generate_code_reference.py`
- `tools/run_full_validation.py`

---

# Delivery List Scanner - v063 Production Database Startup Collision Fix

Date: 2026-07-15

## Exact crash cause

The production traceback identified a real startup defect in `seed_demo_data()`:

- The existing project folder still contained `data/sample-delivery-list.json`.
- Startup treated that file as data that should be synchronized on every launch.
- Route/stage repair had previously moved one deterministic sample-derived line-item ID to another delivery-list stage.
- Demo reseeding saw a line-count mismatch, rebuilt the original list, and attempted to insert the same globally unique `line_items.id` again.
- SQLite correctly stopped startup with `UNIQUE constraint failed: line_items.id`.

The production database does not need to be deleted or replaced.

## Startup repair

- Demo/sample delivery-list data is now seeded only when the database contains no delivery lists.
- Once a database has real or previously imported lists, an old sample JSON file can no longer rewrite, refresh, or collide with those rows during startup.
- Required stations continue to seed normally even when demo delivery lists are skipped.
- This also removes unnecessary sample-list comparison work from normal production startup.

## Import and refresh collision guard

- Added one shared `available_line_item_id()` guard to the existing insertion workflow.
- Normal deterministic IDs remain unchanged when available.
- If an older stage move already owns that ID in another delivery list, the refreshed row receives a stable collision-safe suffix.
- A duplicate ID inside the same delivery list still raises an error rather than silently creating a duplicate line.
- The guard protects normal delivery-list refreshes as well as the startup condition that exposed the issue.

## Windows security warning

- The packaged BAT now removes the downloaded-file security marker from `Start-DeliveryScannerWebApp.ps1` before invoking it.
- This prevents the recurring `Run only scripts that you trust` / `Run once` prompt after extracting a downloaded ZIP.
- The existing execution-policy bypass, health wait, logging, and startup-error display remain in place.

## Validation

- Recreated the exact cross-list deterministic-ID collision in a temporary SQLite database.
- Confirmed repeated store initialization no longer attempts demo reseeding.
- Confirmed a deliberate refresh creates one collision-safe row without altering the older moved row.
- Started the real HTTP server against the collision database and received a healthy SQLite response.
- Full maintained validation: **47 tests passed with no skips**.

## Database and deployment status

- SQLite remains the active/default backend.
- No production data deletion is required.
- No schema migration was added in v063.
- Azure SQL remains opt-in and inherits the same collision-safe insertion and empty-database demo-seeding rules.

## Files edited

- `delivery_store.py`
- `Start-DeliveryScannerWebApp.bat`
- `index.html`
- `tests/test_store_workflows.py`
- `tests/test_static_integrity.py`
- `tools/generate_code_reference.py`
- `tools/run_full_validation.py`
- `AZURE_DEPLOYMENT.md`
- `README_CHANGELOG.md`
- `CODE_REFERENCE_v063.md`
- `TESTING_v063.md`
- `TEST_REPORT_v063.md`

---

# Delivery List Scanner - v062 Startup Crash Diagnostics and Windows Launcher Repair

Date: 2026-07-15

## Scope

- Used v061 as the baseline after the reported immediate Windows startup failure.
- SQLite remains the active/default backend. Azure SQL remains opt-in.
- No scanning, routing, rack, bay, Rush, printing, chart, or browser workflow was duplicated or replaced.

## What was found

- The v061 application server starts successfully in this environment with both a fresh SQLite database and a database initialized by v060, so the machine-specific exception could not be reproduced without the production database/runtime.
- The release ZIP did not include the BAT or PowerShell launcher used on the floor PC.
- The supplied launcher opened the browser before the server passed a health check.
- A Python startup exception caused the PowerShell window to close without preserving the traceback for the operator.
- The launcher preferred a machine-specific Codex runtime before the normal Windows Python launcher, which could select a stale or incomplete runtime on another computer.
- The existing health check expected text that the current `/api/health` response does not contain, so it could fail to recognize an already-running scanner instance.

## Windows startup repair

- Added `Start-DeliveryScannerWebApp.bat` to the release package.
- Added a documented `Start-DeliveryScannerWebApp.ps1` beside it.
- The launcher now validates that `server.py` is present before starting.
- Python selection now prefers:
  1. A project `.venv` runtime.
  2. The Windows `py -3` launcher.
  3. A normal `python` command.
  4. The Codex runtime only as the final fallback.
- Python must be version 3.10 or newer.
- The browser opens only after `/api/health` reports a healthy application.
- If the requested port belongs to an already-running Delivery List Scanner, the launcher opens that instance instead of starting another server.
- If another program owns the port, the launcher advances to the next available port.
- The launcher keeps the console attached to the Python process and reports an unexpected later shutdown.
- BAT-level failures preserve the window with `pause` instead of disappearing immediately.

## Durable startup diagnostics

The release now creates a `logs` folder at runtime containing:

- `launcher.log` — launcher decisions, runtime selection, port selection, and health status.
- `server-stdout.log` — database initialization and server startup milestones.
- `server-stderr.log` — Python errors and HTTP server diagnostics.
- `startup-error.log` — full Python traceback, Python executable/version, application root, database type, and database path.
- `delivery-scanner.pid` — current local server process ID while the launcher-managed server is running.

`server.py` now logs uncaught startup failures itself, so diagnostics remain available even when the failure occurs during database initialization or port binding.

## SQLite startup tolerance

- SQLite connections now use the configured database timeout during `sqlite3.connect()`.
- `PRAGMA busy_timeout` uses the same timeout value.
- A short-lived database lock from antivirus, backup software, or a recently stopped process waits for release instead of failing immediately.
- The existing WAL, foreign-key, connection-closing, schema-upgrade, and route-repair behavior remains unchanged.

## Startup visibility

`server.py` now emits flushed milestones for:

1. Beginning database initialization.
2. Completing database initialization.
3. Binding the configured host and port.
4. Confirming the running URL and active database mode.

These messages make it clear whether a failure occurred in SQLite initialization or HTTP port binding.

## Documentation and tests

- Updated the maintained code reference to v062.
- Added the six documented PowerShell launcher functions to the code reference.
- Added regression checks for packaged launcher files, health-before-browser ordering, durable logs, Python-version validation, SQLite busy timeout, v062 cache keys, and startup failure tracebacks.
- The complete suite now reports **45 passing tests with no skips**.
- Fresh SQLite startup and v060-to-v062 database upgrade startup both passed.

## Files added

- `Start-DeliveryScannerWebApp.bat`
- `Start-DeliveryScannerWebApp.ps1`

## Files edited

- `server.py`
- `delivery_store.py`
- `index.html`
- `tests/test_core_helpers.py`
- `tests/test_static_integrity.py`
- `tools/generate_code_reference.py`
- `tools/run_full_validation.py`
- `CODE_REFERENCE_v062.md`
- `TESTING_v062.md`
- `TEST_REPORT_v062.md`
- `AZURE_DEPLOYMENT.md`
- `README_CHANGELOG.md`

## Important operator note

Use the BAT included in v062 from the same folder as `server.py`. If startup still fails on the production PC, do not close the error window before reading it. The exact cause will also remain in the package's `logs` folder, especially `server-stderr.log` and `startup-error.log`.

---

# Delivery List Scanner - v061 Full Code Audit and Maintainer Documentation

Date: 2026-07-15

## Scope

- Completed a whole-project architecture, duplicate-code, persistence, route, scanner, rack, bay, print/export, notification, and browser-layout sweep using v060 as the baseline.
- SQLite remains the active/default backend. Azure SQL remains an explicit future cutover option.
- No parallel scanner, popup, chart, route, rack, bay, or database workflow was added.

## Function-by-function documentation

- Added `Purpose`, `Effects`, and `Flow` notes to every named Python function/method in the maintained source and regression suite.
- Added matching JSDoc notes to every named JavaScript function, including local workflow helpers.
- Added explicit ownership comments to the HTML page/modal sections, CSS feature sections, Azure SQL tables, container files, environment template, requirements, and test configuration.
- Added `CODE_REFERENCE_v061.md`, a generated maintenance reference containing the architecture, startup flow, Python functions, JavaScript functions, API routes, database tables, HTML anchors, CSS sections, callers, and safe-edit rules.
- Added `tools/generate_code_reference.py` so future coders can regenerate the reference after structural edits.

## Permanent regression suite

- Added a maintained pytest suite covering route authority, CSV/XLSX imports, authentication, sessions, roles, permissions, password reset, scans, duplicate/error handling, Undo/Redo, racks, rack transit, bays, layout editing, manual/remembered bay rules, Rush/Remake propagation, notifications, customer email settings, reports, print rendering, CSV/XLSX exports, SQLite-to-Azure SQL compatibility, and HTTP API behavior.
- Added browser-rendered visual and interaction checks using the real `index.html`, `styles.css`, and `app.js` with controlled API fixtures.
- Visual checks cover the header/profile click target, Scan panel title/progress clearance, Undo/Redo stacking, chart header/control spacing, chart SVG rendering, Bay Map route summary, last-bay readability, and internal-scroll prevention at 1600×1000 and 1366×768.
- Added static checks for Python/JavaScript syntax, duplicate HTML IDs, CSS parser errors, duplicate class methods, duplicate top-level JavaScript functions, frontend API path coverage, function-documentation coverage, v061 asset versions, and the SQLite-default setting.
- Added `tools/run_full_validation.py`, `tests/README.md`, and `TESTING_v061.md` as the maintained release-validation entry points.

## Defects found and corrected during the sweep

### CSV delivery date preservation

- CSV imports now honor an in-file delivery-date column before using the filename/current-date fallback.
- Supported headings include `deliveryDate`, `Delivery Date`, `Delivery Date:`, `delivery_date`, `Date`, and `date`.

### Undo/Redo history accuracy

- Redone scans are now recorded with event type `redo` rather than being mislabeled as new `scan` events.
- Later Undo and Redo operations correctly recognize both original scans and redone scans.

### Bay assignment restoration

- Restoring a previously cleared bay assignment now writes the schema-compatible empty-string cleared fields instead of `NULL` values that violated the existing non-null constraints.

### SQLite connection lifecycle

- Added one shared `ClosingSQLiteConnection` implementation.
- Every existing `with self.connect()` transaction now commits or rolls back and then closes the underlying SQLite connection.
- This prevents file-handle and connection buildup during long scanner shifts without rewriting individual store workflows.

### Test server resource cleanup

- The HTTP integration test now closes its subprocess stdout/stderr handles after shutdown, preventing validation-time descriptor warnings.

## Startup and database safeguards

- Added a regression test proving an unchanged second SQLite startup skips the full route-stage reconciliation.
- Preserved v060 Customer Route Rule authority and CPU-Air Job Nr. override behavior.
- Preserved `source_route`, `system_metadata`, idempotent repairs, and Azure SQL schema parity.
- No Azure SQL setting is enabled automatically.

## Files added

- `CODE_REFERENCE_v061.md`
- `TESTING_v061.md`
- `pytest.ini`
- `tests/README.md`
- `tests/conftest.py`
- `tests/test_core_helpers.py`
- `tests/test_store_workflows.py`
- `tests/test_extended_workflows.py`
- `tests/test_file_imports_and_sql_compat.py`
- `tests/test_azure_adapter_and_rendering.py`
- `tests/test_visual_smoke.py`
- `tests/test_server_http.py`
- `tests/test_static_integrity.py`
- `tests/test_visual_smoke.py`
- `tools/generate_code_reference.py`
- `tools/run_full_validation.py`

## Existing files reviewed and documented

- `app.js`
- `delivery_store.py`
- `server.py`
- `scanner_config.py`
- `azure_sql_compat.py`
- `migrate_sqlite_to_azure_sql.py`
- `azure_sql_schema.sql`
- `index.html`
- `styles.css`
- `Dockerfile`
- `.dockerignore`
- `.env.azure.example`
- `requirements.txt`
- `AZURE_DEPLOYMENT.md`
- `README_CHANGELOG.md`

## Validation result

- 42 pytest cases passed with no skips after loading the pinned `pyodbc` and `sqlglot` dependencies.
- Azure SQL translation and adapter tests passed locally; a live Azure SQL resource was not available and is not claimed.
- Python backend coverage measured 54% by executable statements across the core modules; the suite additionally performs static coverage of every named function, every browser function’s documentation, all frontend API path references, the schema, and critical rendered layouts.
- JavaScript syntax, Python compilation, CSS parsing, HTML ID uniqueness, duplicate-definition audits, real local HTTP API testing, SQLite integration workflows, browser-rendered visual smoke testing, asset-version checks, and release ZIP integrity all passed.
- This is a comprehensive automated and structural sweep, not a claim that every possible production data combination or live Azure environment has been exercised.

---

# Delivery List Scanner - v060 Customer Route Authority and Fast Startup

Date: 2026-07-15

## v060 Changes

### Customer Route Rules are now the primary source of truth

- Route resolution now happens only after the active database Customer Route Rules are loaded.
- The import parser no longer pre-resolves a route and accidentally makes that value look explicit before the database rules can run.
- Customer matching uses the customer-name field only.
- When multiple rules match, an exact normalized customer match wins; otherwise the most specific/longest matching pattern wins.
- Active customer rules override conflicting imported ROUTE values for CPU, DTC, Greenville, Indian Trail, and custom routes.
- The original imported ROUTE value is retained separately as `source_route`, allowing later rule changes or removals to reroute existing items safely.

### Job Nr. override is limited to CPU-Air routing

- Any capitalization or separator variation of CPU-Air or Air-CPU in Job Nr. routes the item to **Customer Pickup**.
- CPU-IT and CPU-INT continue to explicitly remain on **Indian Trail**.
- DTC and Greenville are no longer inferred from Job Nr.; those destinations come from Customer Route Rules, with the imported ROUTE field retained only as a fallback when no rule matches.
- Generic CPU text such as `CPUITEM` remains excluded by strict token matching.

### Missing destination stages repair automatically

- Existing items are reconciled against the active customer rules during the one required v060 upgrade pass.
- Missing Customer Pickup, BFS Greenville, DTC, or Indian Trail receiving copies are created or moved using the existing shared membership workflow.
- Staging and Outbound copies, scanned quantities, scan history, rack references, bay assignments, and audit references remain preserved.
- Saving or deleting a Customer Route Rule immediately reconciles existing active items so scanning and Print / Export use the updated destination without waiting for a reimport.

### Startup performance

- Removed the full route-stage repair from every application launch.
- Added one `system_metadata` signature containing the route-repair version and active customer rules.
- The repair runs only when that signature changes, such as after upgrading this version or editing route rules.
- The repair now loads active line items once, groups them in memory, and performs follow-up SQL only for items that actually need a route or stage change.
- A 5,000-item repeated-startup test completed in approximately 0.003 seconds after the initial signature was stored; a one-time 1,000-item legacy Greenville repair completed in approximately 0.4 seconds in the test environment.

### SQLite and Azure SQL readiness

- SQLite remains the active default backend.
- Added `line_items.source_route` and `system_metadata` to both the SQLite and Azure SQL schemas.
- Added `system_metadata` to the SQLite-to-Azure migration order.
- Azure SQL remains inactive unless `DLS_DATABASE_TYPE=azure-sql` is deliberately configured.

## Files Edited

- `delivery_store.py`
- `app.js`
- `azure_sql_schema.sql`
- `migrate_sqlite_to_azure_sql.py`
- `index.html`
- `AZURE_DEPLOYMENT.md`
- `README_CHANGELOG.md`

## Validation Performed

- Python compilation and JavaScript syntax validation.
- Fresh SQLite initialization and existing-v059 database upgrade testing.
- Customer-rule precedence tests with conflicting imported ROUTE values.
- CPU-Air Job Nr. override tests against a conflicting Greenville customer rule.
- Exact and longest customer-pattern selection tests.
- Immediate existing-item rerouting after adding and removing a customer rule.
- Original imported route restoration through the new `source_route` field.
- Standard CPU, Greenville, DTC, Indian Trail, and custom destination-stage creation tests.
- Print package, CSV export, and XLSX export tests for corrected destination lists.
- 5,000-item unchanged startup benchmark and 1,000-item legacy-route repair benchmark.
- Duplicate JavaScript function, Python method, and HTML ID audits.
- SQLite remains the reported active database mode.

---

# Delivery List Scanner - v059 Scanner Title, Outbound Rack Focus, and Transit Confirmation

Date: 2026-07-15

## v059 Changes

### Scan-page stage title no longer clips descenders

- Adjusted the existing combined scanner header instead of adding another title or progress block.
- Increased the title line height slightly and added a small amount of bottom breathing room so the `g` in **Staging** no longer clips into or behind the progress row.
- Preserved the compact title-above-progress layout introduced in v055.

### Outbound rack selector follows the scanned rack

- The Outbound rack-barcode response already identified the scanned rack, but the frontend did not apply that value to the existing Transportation Status selector.
- The Scan page now sets `selectedOutboundRackCode` from the successful rack response before the scanner panel renders.
- The rack list is refreshed after the Outbound scan so the selected rack immediately displays its updated **In Transit** status and piece count.
- No second rack selector or status workflow was added.

### Timed Outbound transit confirmation

- Reused the existing Indian Trail timed scan-confirmation presentation for Outbound rack releases.
- Extracted one shared mount, countdown, close, language, and custom-select lifecycle used by both the Indian Trail placement notice and the new Outbound notice.
- After a rack barcode is accepted at Outbound, a blue truck-themed timed notice confirms:
  - the rack code
  - the actual normalized destination
  - that the rack is in transit
  - the total number of pieces currently on the rack
- Indian Trail racks display **Rack [code] is on the way to Indian Trail**. Greenville, CPU, and DTC racks use their actual destination instead of showing an incorrect Indian Trail message.
- The older generic floating scan notice is suppressed for this rack-release event so the operator sees one clear confirmation rather than two overlapping notices.

### Outbound response details

- Extended the existing rack-scan response with `rackDestination`, `rackPieceCount`, and `outboundScannedQty`.
- These are response-only fields. No database schema, migration, or new API endpoint was added.
- SQLite remains the active default backend and Azure SQL remains opt-in.

## Files Edited

- `app.js`
- `delivery_store.py`
- `styles.css`
- `index.html`
- `README_CHANGELOG.md`

## Validation Performed

- JavaScript syntax validation with `node --check app.js`.
- Python compilation for the server, SQLite/Azure store layers, migration utility, and configuration.
- Temporary SQLite Outbound rack integration test verifying:
  - the rack changes from Closed to In Transit
  - the response returns the scanned rack code
  - the response returns the normalized Indian Trail destination
  - the response returns the total three-piece rack quantity
  - the response returns the three newly scanned Outbound pieces
- Static frontend checks confirming the scanned rack response updates the existing Outbound selector before rendering and invokes the shared timed confirmation.
- CSS parsing, balanced-brace validation, duplicate JavaScript function, Python method, and HTML ID audits.
- Updated cache-busting asset references to v059.

---

# Delivery List Scanner - v058 All Scans Event Colors and Route Stage Repair

Date: 2026-07-15

## v058 Changes

### All Scans import and update rows use their own colors

- Kept the existing All Scans event renderer and event classes; no second history table or event-style system was added.
- Import rows now use the existing import blue across the row divider, left event line, event badge, and completion indicator.
- Update rows now use the existing update purple across the row divider, left event line, event badge, and completion indicator.
- Import and update rows no longer inherit the generic successful-scan green presentation.
- Normal scans, manual scans, errors, undo, redo, and notices retain their existing colors.

### CPU, DTC, Greenville, and Indian Trail designations resolve consistently

- Reworked the shared route resolver used by imports, list generation, scanning filters, manual route rules, rack destinations, and print/export selection.
- `GRVLLE`, `GRVlle`, `GRVille`, `GRVle`, `GVlle`, `GNV`, `GRN`, and `Greenville` now resolve to the standard **BFS Greenville** stage.
- DTC designations such as `DTC`, `DTC - Air`, and Job Nr. suffixes containing a separated `DTC` token now resolve to **DTC - Deliver to Customer**.
- `CPU-Air`, `CPU - Air`, reversed `Air-CPU`, and equivalent separator/case variations resolve to **Customer Pickup**.
- `CPU-IT`, `CPU - IT`, `CPU-INT`, reversed forms, and equivalent separator/case variations resolve to **Inbound - Indian Trail**, not Customer Pickup.
- Strict token boundaries remain in place so unrelated text such as `CPUITEM` is not silently treated as a route designation.
- The browser route filters and the Python backend now use matching designation behavior.

### Existing SQLite data repairs itself on startup

- Added one idempotent route-stage reconciliation workflow to the existing store layer.
- On startup, the app canonicalizes legacy route values and verifies that each physical item has Staging, Outbound, and exactly one correct receiving-stage copy.
- Existing items previously placed in hidden custom stages such as `GRVLLE` or `DTC - AIR` are moved into the standard Greenville or DTC list.
- Existing generated `IT` fallbacks are corrected when the preserved Job Nr. contains a strong DTC, Greenville, or CPU-Air designation.
- Scanned quantities, scan events, rack references, bay assignments, and audit references are retained when the receiving-stage row moves.
- Empty legacy custom lists are naturally excluded by the existing list query because they no longer contain line items.
- New imports use the corrected resolver immediately, so the repair path is only active when existing data actually needs correction.

### Scan and print/export availability restored

- Standard destination list IDs and stage names are generated again for CPU, DTC, Greenville, and Indian Trail items.
- Operator stage-access checks now see the standard scanner names instead of inaccessible custom route names.
- Destination stages therefore appear in the Scan page, Print / Export GUI, CSV export, Excel export, and multi-stage print packages.
- Staging and Outbound continue to contain every route, while the receiving copy appears only in its resolved destination stage.

### Database and code-quality status

- SQLite remains the active and default database backend.
- Azure SQL remains opt-in; the shared reconciliation workflow is compatible with the existing Azure SQL adapter but no Azure activation setting changed.
- No database schema or API endpoint was added.
- The route repair uses the existing receiving-list movement implementation rather than creating a second item-copy or print workflow.
- Updated cache-busting asset versions to v058.

## Files Edited

- `app.js`
- `delivery_store.py`
- `styles.css`
- `index.html`
- `README_CHANGELOG.md`

## Validation Performed

- JavaScript syntax validation with `node --check app.js`.
- Python compilation for the server, SQLite/Azure store layers, migration utility, and configuration.
- Backend and frontend route matrices covering CPU-Air, CPU-IT/INT, DTC variants, Greenville/GRVlle variants, capitalization, separators, reversed CPU tokens, and false-positive protection.
- Temporary SQLite import test proving all six standard stages are generated and visible for a mixed-route delivery date.
- Print-package, CSV export, and XLSX export tests for Staging, Outbound, Indian Trail, Greenville, Customer Pickup, and DTC.
- Legacy-database repair test moving hidden Greenville and DTC custom-stage rows into their standard destination lists while preserving all stage copies.
- All Scans CSS precedence review confirming import blue and update purple override the generic successful-scan green row style.
- Duplicate named JavaScript function, Python method, HTML ID, and cache-reference audits.
- Local SQLite server health and frontend-asset smoke testing.
- ZIP content and integrity validation.

---

# Delivery List Scanner - v057 Expanded Charts, Compact Bay Scanner, and Reactive Controls

Date: 2026-07-15

## v057 Changes

### Expanded interactive Chart GUI

- Extended the existing SVG chart renderer and selection workflow rather than adding a second chart system.
- Added a **Date range** selector directly inside the Chart GUI with Today, Last week, Last 30 days, Last 90 days, Full year, and All lists options.
- The Chart GUI range and the dashboard range now use the same `overviewRange` state and report endpoint, preventing separate or conflicting date-filter implementations.
- Added **Delivery completion by list**, showing the completion percentage and scanned/open quantities for each delivery-list stage.
- Added **Open pieces by delivery list**, showing only lists that still have work remaining.
- Added **On-time completion by list**, using the existing on-time and late piece metrics.
- Added **Stage workload**, showing total, completed, and open piece volume by workflow stage.
- Kept the existing glass mix, stage completion, scanned/open work, operator activity, system activity, and remake charts.
- Percentage-based charts automatically use the bar view because a donut chart would incorrectly present percentages as parts of one total.
- Added a six-card summary strip with delivery percentage, pieces completed, open pieces, completed lists, on-time completion, and scan quality.
- Expanded the home dashboard range selector with Today and Last 90 days so the dashboard and Chart GUI expose the same supported ranges.
- Added Spanish translations and dynamic translation patterns for the new chart controls, summaries, and data details.

### Intentionally compact Bay Map scanner

- Added one fixed Bay Map-only compact presentation instead of restoring the removed viewport-measurement and balanced/compact/tight JavaScript system.
- Reduced vertical padding, gaps, route-card height, add/remove controls, target-bay row height, barcode row height, manual-scan height, last-scan card height, and recent-history row spacing.
- All Bay Map scanner controls and the Outbound → In Transit → Received route summary remain visible at all times.
- The compact presentation is stable on initial load and after scans; it does not change size based on content measurements.
- The main Scan-page scanner remains full-size.

### Scan-page Undo/Redo visibility and scanner feedback

- Removed the older negative label offset from the main Scan-page barcode heading so Undo and Redo no longer sit behind the barcode outline at certain display scales.
- Raised the existing Undo/Redo action row above the scan field with an explicit stacking order.
- Added polished hover, pressed, disabled, and keyboard-focus feedback to the existing Undo/Redo buttons.
- Added consistent movement, shadow, border, and focus feedback to scanner-panel buttons, barcode wrappers, Bay Map add/remove choices, and last-scan cards.
- Reused the existing buttons, barcode wrappers, and scanner forms; no duplicate controls or event handlers were added.

### Database and code-quality status

- SQLite remains the active and default database backend.
- Azure SQL remains available only for a deliberate future cutover.
- No database schema, API endpoint, migration, or server business logic changed in v057.
- Removed an existing duplicate assignment of `state.homeChartSelectedLabel` found during the chart review.
- Integrated the expanded chart grid into the existing current chart CSS block instead of adding another duplicate top-level chart-modal override.
- Updated cache-busting asset versions to v057.

## Files Edited

- `app.js`
- `styles.css`
- `index.html`
- `README_CHANGELOG.md`

## Validation Performed

- JavaScript syntax validation with `node --check app.js`.
- Python compilation for the server, SQLite/Azure database layers, migration utility, and configuration.
- Chart dataset and interaction unit tests for delivery completion, remaining work, on-time completion, stage workload, KPI calculations, selection details, sorting, and display limits.
- CSS parser validation with `tinycss2`.
- Duplicate named JavaScript function and HTML ID audits, plus a targeted audit confirming every new Spanish chart translation key is defined once.
- Static selector review confirming the new Bay Map compact rules are scoped to one new Bay Map class and do not reintroduce the removed JavaScript density system.
- Local server smoke testing confirming `/api/health` remains in `sqlite` mode and v057 frontend assets load.
- Headless Chromium visual testing was attempted, but the environment displayed an organization policy block for local URLs; no screenshot-based visual validation is claimed.
- ZIP content and integrity validation.

---

# Delivery List Scanner - v056 Rush Stage Propagation, Safe Acknowledgment, and Priority Placement

Date: 2026-07-15

## v056 Changes

### Rush printing now reflects the submitted change

- The existing Rush print workflow now opens a package containing only the physical items changed by the current Rush submission rather than every older Rush on one stage.
- Rush sheets are generated for every applicable stage copy of the item: Staging, Outbound, and the route-specific destination stage.
- The new priority delivery date is used in each Rush-sheet title while the original delivery-list date remains visible in the subtitle for reference.
- Direct-to-truck Indian Trail Rush sheets clearly state **Send straight to installer truck / skip bay**.
- Standard Indian Trail Rush sheets state **Receive into the indicated priority Rush bay**, while Staging, Outbound, Greenville, CPU, and DTC sheets state that the work must be expedited through that stage.
- The print URL uses the existing print-package endpoint with exact source-item filtering; no second print renderer or Rush-only endpoint was added.

### Acknowledge Rush opens the correct filtered delivery list safely

- Reworked the existing Scan-page Rush alert so **Acknowledge Rush & View** selects an affected delivery list that the current user can access and applies the existing **Rushes** filter immediately.
- The current affected list is retained when possible; otherwise the app selects the matching stage category, then Staging, then the first accessible affected stage.
- Every active scan request is now tracked through the existing `processScan()` path. Acknowledgment waits for active scans to finish before changing delivery lists.
- A barcode already typed into the Scan-page field but not yet submitted is processed before the redirect.
- The alert is not silently dismissed by Escape or backdrop clicks, so the per-user notification remains pending until acknowledgment succeeds.
- Scan-safety and Indian Trail placement dialogs remain above the Rush alert, allowing a scan that needs operator input to complete before redirecting.

### Rush status follows the correct route through production

- Marking an item as Rush now expands the selected physical item by its shared `source_id` and updates only its active stage copies.
- Indian Trail work is marked on Staging, Outbound, and Inbound - Indian Trail.
- Greenville work is marked on Staging, Outbound, and BFS Greenville.
- CPU work is marked on Staging, Outbound, and Customer Pickup.
- DTC work is marked on Staging, Outbound, and DTC - Deliver to Customer.
- Clearing Rush / Remake now clears the status, priority delivery date, and direct-to-truck instruction from all applicable stage copies.
- Rush/Remake markers, priority dates, and direct-to-truck instructions are preserved when an updated delivery-list file refreshes the same physical item.

### Indian Trail Rush receiving and placement

- Added one persisted item-level `priority_direct_to_truck` flag to the existing `line_items` table. Existing SQLite databases add the column automatically at startup, and the Azure SQL readiness schema contains the matching column.
- The direct-to-truck flag is accepted only when the affected route includes Indian Trail; Greenville, CPU, and DTC Rushes cannot accidentally inherit an Indian Trail truck instruction.
- The existing Indian Trail receive response now identifies whether the scanned item is Rush, its priority delivery date, and whether it must bypass bays.
- Direct-to-truck Rush items are received without a bay assignment and display a high-visibility instruction to send the glass straight to the installer truck.
- Only the affected direct-to-truck Rush item's active bay assignment is cleared; other pieces sharing the same Job Nr. remain in their bays.
- Non-direct Rush items display a distinct orange priority-placement popup with the required Rush bay and retain the existing bay-override control.
- Rush receives now create explicit Rush audit actions and scan-history messages for direct-to-truck and priority-bay handling.

### Database and code-quality status

- SQLite remains the active and default database backend. Azure SQL remains opt-in for a deliberate future cutover.
- Reused the existing Rush notification table, per-user acknowledgment receipts, print-package renderer, scan function, Rush filter, delivery-list activation, Indian Trail receive endpoint, and placement popup.
- Added one shared cross-stage item expansion helper and one shared affected-list context helper instead of duplicating stage-specific Rush implementations.
- Removed the now-unused `closeRushAlert()` helper after the alert became acknowledgment-only.
- Updated cache-busting asset versions to v056.

## Files Edited

- `app.js`
- `styles.css`
- `delivery_store.py`
- `server.py`
- `azure_sql_schema.sql`
- `index.html`
- `README_CHANGELOG.md`

## Validation Performed

- JavaScript syntax validation with `node --check app.js`.
- Python compilation for the server, SQLite/Azure database layers, migration utility, and configuration.
- Temporary SQLite integration tests for Indian Trail, Greenville, CPU, and DTC Rush stage propagation.
- Exact-source Rush print-package tests across Staging, Outbound, and destination sheets.
- Rush print HTML checks for new/original delivery dates, direct-to-truck handling, priority-bay handling, and exclusion of unrelated Rush items.
- Indian Trail receive tests for direct-to-truck and priority-bay Rush items.
- Bay-assignment scope test confirming a direct-to-truck scan does not clear a non-Rush sibling item sharing the same job.
- Reimport preservation tests for Rush markers and priority dates across all applicable stages.
- Existing SQLite schema-upgrade test for the new `priority_direct_to_truck` column.
- Duplicate named JavaScript function, Python class-method, and HTML ID audits.
- CSS parser validation, local SQLite server health testing, frontend asset checks, and ZIP integrity validation.

---

# Delivery List Scanner - v055 Combined Scanner Header and Full-Size Panels

Date: 2026-07-15

## v055 Changes

### Combined Scan-page title, quantity, and progress

- Moved the active stage title into the existing navy scanner header instead of leaving it in a separate row below the progress section.
- The title now appears first, with the stage quantity and progress bar sharing one compact row directly beneath it.
- Reused the existing `stageHeading`, `progressText`, and `progressFill` elements and rendering functions; no second title or progress component was added.
- Reduced the scanner panel's normal vertical footprint while keeping the stage name, exact scanned quantity, completion percentage, and progress bar clearly visible.
- Added a narrow-screen fallback that stacks only the quantity and progress bar when horizontal space is genuinely limited.

### Removed automatic scanner-panel condensation

- Removed the JavaScript viewport-height measurement, animation-frame scheduler, delayed settling timer, and balanced/compact/tight class workflow.
- Removed the corresponding height-density CSS rules for both the Scan-page and Bay Map scanner panels.
- Scanner panels now keep their full-size controls and information on initial load, after list changes, after scans, during fullscreen changes, and when the header wraps.
- The page remains the only vertical scroll surface. The scanner panels do not create internal scrollbars and no operational sections are hidden based on viewport height.
- The Bay Map's Outbound → In Transit → Received route summary remains permanently available because there is no longer a tight mode that can alter or hide it.
- Kept the existing live sticky-header offset calculation so both scanner panels still remain below the application header in normal and fullscreen modes.

### Database and code-quality status

- SQLite remains the active and default database backend.
- Azure SQL remains available only through a deliberate future environment change.
- No database schema, API endpoint, migration, or business workflow changed in v055.
- Removed the obsolete density state fields, helper functions, lifecycle calls, and CSS selectors rather than leaving unused duplicate sizing code behind.
- Removed an older duplicate Scan-page header CSS override and retained one current header implementation.

## Files Edited

- `app.js`
- `styles.css`
- `index.html`
- `README_CHANGELOG.md`

## Validation Performed

- JavaScript syntax validation with `node --check app.js`.
- Python compilation for the server, SQLite/Azure database layers, migration utility, and configuration.
- CSS balanced-brace validation.
- Duplicate named JavaScript function and HTML ID audits.
- Static checks confirming all density state, functions, class names, and lifecycle calls were removed.
- Static DOM-order check confirming the stage title appears above the quantity and progress bar inside one scanner header.
- Local server smoke testing confirming `/api/health` remains in `sqlite` mode and the v055 frontend assets load.

---

# Delivery List Scanner - v054 Initial Scanner Sizing and Bay Route Visibility

Date: 2026-07-15

## v054 Changes

### Bay Map route summary now appears on initial load

- Traced the missing Outbound → In Transit → Received summary to the existing height-density workflow rather than adding another Bay Map header component.
- The previous measurement could immediately apply balanced, compact, and tight classes during the same initial pass. Tight mode then hid the route details until a later scan caused the panel to be measured again.
- Reworked the existing density calculation to measure the full panel once and apply cumulative modes from defined overflow ranges instead of repeatedly shrinking and remeasuring against a two-pixel threshold.
- The Bay Map route summary now remains visible in normal, balanced, compact, and tight layouts.
- Tight mode uses smaller route cards and text rather than removing the operational Outbound, in-transit, and Received information.

### Full-size scanner initialization and list switching

- Added one shared density scheduler for the Scan page and Bay Map scanner panels.
- Page changes, delivery-list changes, and fullscreen changes now immediately clear prior density classes so the newly displayed scanner starts at its full width and height.
- Density is recalculated after two animation frames, allowing the visible page, list-specific controls, fonts, and current scanner content to finish laying out before the panel is measured.
- Added one delayed settling measurement for asynchronous list and Bay Map content so a stale initial measurement cannot remain after data finishes rendering.
- The existing header `ResizeObserver` now also remeasures scanner density after the sticky header wraps or changes height, keeping the available-height calculation aligned with the actual header.
- The Scan page now avoids its previous duplicate render when `activateList()` navigates to the page; `showPage()` performs the single final render with the full-size reset.
- Resizing still expands or condenses the panels automatically, but the page can tolerate a modest amount of vertical continuation before stronger compact modes are used. This keeps the scanner larger while preserving the existing no-internal-scroll behavior.

### Database and duplicate-code status

- SQLite remains the active and default database backend.
- Azure SQL remains opt-in and ready for a later deliberate cutover.
- No database schema, API endpoint, or migration changed in v054.
- Reused the existing Bay Map route component, scanner panels, page lifecycle, list activation workflow, and density classes.
- Added one density scheduler and removed the duplicate Scan-page render during navigation instead of adding page-specific sizing systems.
- Removed three older duplicate Spanish translation keys (`Truck`, `Rack Sets`, and `Selected Rack`) while preserving the accented/final translations that already won at runtime.

## Files Edited

- `app.js`
- `styles.css`
- `index.html`
- `README_CHANGELOG.md`

## Validation Performed

- JavaScript syntax validation with `node --check app.js`.
- Python compilation for the server, SQLite/Azure database layers, migration utility, and configuration.
- CSS balanced-brace validation.
- Duplicate JavaScript function, Python method, HTML ID, and translation-key audits.
- Scanner-density unit checks covering full, balanced, compact, and tight overflow ranges.
- Static CSS check confirming tight mode no longer hides `#bayPanelRouteMini`.
- Static lifecycle checks confirming Scan-page list changes and Bay Map page entry reset density before settled measurement.
- Local server smoke testing confirming `/api/health` remains in `sqlite` mode and the v054 frontend assets load.
- Headless Chromium visual testing was attempted, but this execution environment blocks browser navigation to local URLs; no screenshot-based validation is claimed.

---

# Delivery List Scanner - v053 Bay History Location Editing and Scanner Input Polish

Date: 2026-07-15

## v053 Changes

### Change Bay Map locations from scan history

- Kept the existing `/api/indian-trail/move` endpoint, Bay Map assignment mover, confirmation popup, permission checks, and history refresh path; no second move workflow was added.
- Made the existing location-changing control clearly available from the Bay Map scanner's large last-scan card.
- Added the same current-location control to both recent Bay Map scan rows.
- Expanded **All Bay Scans** so active items can be moved directly from the full Indian Trail history GUI.
- The full history table now separates the bay recorded by the historical event from the item's current active location.
- After a move, the Bay Map, last scan, recent scans, and open All Bay Scans GUI refresh through the existing shared Bay Map refresh workflow.
- Items that are no longer assigned to a bay show a read-only status instead of an unusable location selector.
- Users without `move_bay` or `indian_trail_receive` permission see the current location as read-only.
- Updated the existing Spanish translation map for the new current-location labels without adding a second translation system.

### Professional scanner barcode fields

- Updated the existing shared `.scan-input-wrap` styling used by the Scan page and Bay Map scanner instead of adding separate input components.
- Removed native input borders, focus rings, background rectangles, margins, and corner radii that could paint white edges outside the blue scanner outline.
- The rounded wrapper now owns the complete background, clipping, border, and focus state.
- Kept the barcode icon, text entry, Bay Map undo/redo buttons, scanner sizing, and keyboard focus behavior unchanged.

### Database and duplicate-code status

- SQLite remains the active and default database backend.
- Azure SQL remains opt-in and ready for a later deliberate cutover.
- No database schema or migration changed in v053.
- Reused one Bay Map move endpoint, one document-level location-change listener, one confirmation popup, one Bay Map refresh workflow, and one shared scanner-input component.
- Removed 56 redundant Spanish translation entries while preserving the same final translations that were already winning at runtime.

## Files Edited

- `app.js`
- `index.html`
- `styles.css`
- `README_CHANGELOG.md`

## Validation Performed

- JavaScript syntax validation with `node --check app.js`.
- Python compilation for the server, SQLite/Azure database layers, migration utility, and configuration.
- CSS balanced-brace validation.
- Duplicate JavaScript function, Python method, HTML ID, and translation-key audits.
- Static checks confirming the last-scan card, recent-scan rows, and All Bay Scans GUI all use the same `data-bay-event-move` workflow.
- Static checks confirming All Bay Scans displays both historical scanned bay and current active location.
- Static checks confirming both scanner text inputs are borderless, transparent, and clipped inside the shared wrapper.
- Local server smoke testing in SQLite mode.
- ZIP integrity and package-content validation.

---

# Delivery List Scanner - v052 Chart Colors, Scanner Fit, and Bay History Readability

Date: 2026-07-15

## v052 Changes

### Colored full Statistics Chart GUI

- Kept the existing interactive SVG chart renderer and corrected its shared color scope instead of adding another chart implementation.
- Extended the existing chart palette from 8 to 10 distinct colors for bars, donut slices, and legend markers.
- Applied the same palette to both the dashboard glass-mix chart and the full Chart GUI.
- Fixed the full Chart GUI header layout so the eyebrow, title, subtitle, filters, result text, and chart canvas each receive their own grid row.
- Removed the inherited fixed 58-pixel modal header row that caused the text at the top of the Chart GUI to overlap.
- Kept the chart canvas as the only scrollable area inside the modal when a large data set requires additional room.

### Larger scanner-panel fit before compact mode

- Kept the existing shared scanner-density workflow and added one gentle `is-height-balanced` stage before compact and tight modes.
- The normal Scan-page and Bay Map panels now retain larger progress bands, history cards, inputs, and summary cards on marginal screen heights.
- Strong compact spacing is only applied when the balanced layout still does not fit below the live header.
- Preserved the no-internal-scroll behavior for both scanner panels.
- Increased the usable bottom allowance by four pixels while retaining the existing sticky-header measurement.

### Bay Map last-scan redesign

- Reworked the existing Bay Map last-scan card instead of adding another history component.
- Promoted the bay location into a large, high-contrast primary field that is readable at a glance.
- Kept action, order, time, status, and Move controls in the same card as secondary details.
- Added a hover title for long bay names so the complete location remains available when the visible label is truncated.
- Added balanced, compact, tight, and narrow-screen layouts so the larger location remains usable without reintroducing panel scrolling.
- Added the Spanish translation for `Last bay location` through the existing translation system.

### Database and duplicate-code status

- SQLite remains the active and default backend; no database configuration or schema was changed in v052.
- Azure SQL remains available only for a deliberate future cutover.
- Reused the existing chart modal, SVG renderer, scanner-density helper, Bay Map history renderer, custom Move select, and translation observer.
- Added no duplicate JavaScript function declarations, Python methods, HTML IDs, or translation keys.

## Files Edited

- `app.js`
- `index.html`
- `styles.css`
- `README_CHANGELOG.md`

## Validation Performed

- JavaScript syntax validation with `node --check app.js`.
- Python compilation for the server, SQLite/Azure database layers, migration utility, and configuration.
- CSS parsing and balanced-brace validation.
- Duplicate JavaScript function, HTML ID, and translation-key audits.
- Static checks confirming the full chart has 10 scoped colors and a four-row modal layout.
- Static checks confirming the scanner density order is normal, balanced, compact, then tight.
- Static checks confirming the Bay Map last card keeps one set of the existing history element IDs.
- Local server smoke test confirming `/api/health` remains in `sqlite` mode and the v052 frontend assets load.
- ZIP integrity and package-content validation.
- Chromium visual automation was attempted, but Chromium could not complete local rendering in this execution environment; no screenshot-based validation is claimed.

---

# Delivery List Scanner - v051 Profile Hitbox, Scan-Page Rush Alerts, and Priority Delivery Dates

Date: 2026-07-15

## v051 Changes

### Reliable profile-menu click area

- Kept the existing native `details` / `summary` profile dropdown instead of adding another menu toggle implementation.
- Made the full visible profile control the click target, including the avatar, display name, role text, and dropdown chevron.
- Disabled pointer interception on the decorative child elements so clicks consistently reach the existing summary control.
- Preserved the existing click-away close behavior and the single Sign out action.

### Rush alerts for every active user on the Scan page

- Kept the existing Rush notification tables, polling endpoint, receipt tracking, queue, and Rush popup; no second notification system was added.
- Rush notifications are now left pending for every active user, including the user who marked the Rush.
- Alerts are only presented while the user is on the Scan page, matching the production scanning workflow.
- Users already on the Scan page receive the alert through the existing polling cycle.
- Users on another page keep the alert pending and receive it immediately when they open the Scan page.
- Each user acknowledges the notification independently, so one user's acknowledgment does not hide it for anyone else.
- The Rush popup now includes the Job Nr., order, affected item numbers, customer, route, new delivery date, previous delivery date when changed, product/size summary, reason, priority-item count, and submitting user.
- Expanded the existing Rush popup layout to handle the additional details without clipping long values.

### Rush / Remake delivery-date control

- Added a date field to the existing SDI Rush/Remake GUI.
- Opening the GUI for a selected bay assignment prefills the item's current effective delivery date.
- The user can keep the current date or select a new priority delivery date before marking Rush or Remake.
- Added the item-level `priority_delivery_date` field rather than changing an entire delivery list's date.
- The original delivery-list date remains intact, while the Rush/Remake item can carry an earlier or corrected priority date.
- The new date is shown in the success confirmation, the current Rush/Remake list, and the Rush alert sent to users.
- Removing the Rush/Remake mark clears the item-level priority-date override and returns the item to its original delivery-list date.
- Priority delivery dates are preserved when an existing delivery list is refreshed or re-imported.

### SQLite and Azure SQL readiness

- SQLite remains the default and active database backend.
- Added the new column through the existing idempotent SQLite migration path, so an existing local database upgrades automatically at startup.
- Added the matching Azure SQL schema column and kept the shared schema-migration path ready for a future Azure cutover.
- No environment setting was changed to activate Azure SQL.

### Duplicate-code prevention

- Reused the existing native profile dropdown, Rush popup, notification polling, database notification receipts, SDI form, action-feedback popup, schema migration, and import-refresh workflows.
- Added no duplicate JavaScript function declarations, top-level declarations, Python class methods, or HTML IDs.
- Added no new duplicate translation keys compared with v050.

## Files Edited

- `app.js`
- `delivery_store.py`
- `index.html`
- `styles.css`
- `azure_sql_schema.sql`
- `README_CHANGELOG.md`

## Validation Performed

- JavaScript syntax validation with `node --check app.js`.
- Python compilation for the server, SQLite/Azure database layers, migration utility, and configuration.
- CSS parsing with no syntax errors.
- Duplicate JavaScript function, top-level declaration, Python class-method, and HTML ID audits.
- Comparison against v050 confirming no new duplicate translation keys were introduced.
- SQLite schema-upgrade test confirming an existing database receives `priority_delivery_date` automatically.
- Multi-user Rush notification test confirming both the submitter and another active user receive the same notification and acknowledge it independently.
- Rush payload test covering the new date, previous date, item numbers, product/size details, reason, route, and submitting user.
- Rush removal test confirming the priority-date override is cleared.
- Delivery-list refresh test confirming the priority date survives a replace/update import.
- Local server smoke test confirming `/api/health` reports `mode: sqlite` and the frontend assets load.
- A visual browser test was not available in this execution environment; no screenshot-based validation is claimed.

---

# Delivery List Scanner - v050 Interactive Charts, No-Scroll Scanner Panels, and Insertable Bay Map Layout

Date: 2026-07-15

## v050 Changes

### SQLite remains active by default

- Kept `DLS_DATABASE_TYPE` defaulted to `sqlite`; this release does not automatically enable Azure SQL.
- The existing local SQLite database remains the active source of truth until the Azure deployment is deliberately configured with `DLS_DATABASE_TYPE=azure-sql`.
- Updated the Azure deployment guide to clearly separate current SQLite operation from the future Azure SQL cutover.
- Kept the existing Azure SQL adapter, schema, migration utility, container, and deployment files ready for the later transition.

### Real interactive Statistics Chart GUI

- Replaced the simulated CSS bar and donut displays in the full Chart GUI with real responsive SVG charts.
- Added chart axes, grid lines, scaled bars, true donut slices, hover titles, keyboard focus, and accessible labels.
- Bars, donut slices, and legend rows can now be selected to show the category value, percentage of the displayed total, and detail text.
- Preserved the existing metric, chart style, sort, display-limit, and label-filter controls so the chart can be manipulated without adding a second chart workflow.
- Added Spanish translations for the new chart controls, selected-category panel, chart descriptions, and dynamic result text.

### Scanner panels without internal scrolling

- Removed the remaining Scan-page and Bay Map scanner-panel max-height/vertical-scroll rules, including older overridden sizing rules.
- The scanner cards now use the page as the only vertical scroll surface instead of creating a nested scrollbar.
- Added one shared viewport-density helper for both scanner cards. It measures the live header and available screen height, then applies compact or tight spacing only when required.
- Condensed progress bands, scan inputs, manual controls, scan-history cards, recent rows, and summary cards without hiding the operational controls.
- Kept the scanner cards below the live sticky header in normal and fullscreen modes.

### Fullscreen-only Scan-page history increase

- The main Scan page still shows the latest 2 prior scans in normal windowed mode.
- The main Scan page now shows the latest 4 prior scans while fullscreen is active.
- The Bay Map scanner remains at the latest 2 bay actions.
- Entering or exiting fullscreen rerenders the recent-scan table and recalculates panel density immediately.

### Redesigned Edit Map ordering

- Replaced the expanded live bay-group cards in Edit Map with compact layout cards containing bay, occupancy, piece, and order counts.
- Added visible insertion zones at the top, between every group, and at the bottom of each map column.
- Dragging a group to an insertion zone now shifts neighboring groups and preserves their order instead of displacing an occupied position into Holding.
- Added up, down, left, and right buttons for precise one-step movement.
- Corrected same-column insertion indexing so moving a group downward or between nearby groups lands in the intended position.
- No-op movements no longer create redundant undo-history entries.
- Kept the temporary Holding Area and the existing Save, Cancel, Undo, and Redo workflow.

### Duplicate-code prevention and cleanup

- Reused the existing chart modal, translation observer, fullscreen listener, bay layout draft, undo/redo stacks, and scanner render paths.
- Added one chart renderer, one scanner-density helper, and one bay-group insertion helper rather than page-specific duplicates.
- Removed obsolete scanner max-height variables and older nested-scroll overrides that were superseded by the shared density system.
- Removed the obsolete `moveBayGroup()` and `swapBayGroups()` functions from the previous Edit Map workflow, and renamed the remaining Holding helper to match its single responsibility.
- Removed a duplicated Bay Map source comment and avoided duplicate JavaScript function declarations or HTML IDs.

## Files Edited

- `app.js`
- `styles.css`
- `index.html`
- `AZURE_DEPLOYMENT.md`
- `README_CHANGELOG.md`

## Validation Performed

- JavaScript syntax validation with `node --check app.js`.
- Python compilation for the server, SQLite/Azure database layers, migration utility, and configuration.
- CSS parsing with no syntax errors.
- Duplicate JavaScript function declaration and duplicate HTML ID audits.
- Confirmed the configuration still starts in SQLite mode by default.
- Local server smoke test confirming `/api/health` reports `mode: sqlite` and the v050 frontend assets load.
- Interactive SVG bar and donut chart markup tests.
- Edit Map regression tests for insertion above, below, and between groups; same-column downward movement; arrow movement; and no-op undo suppression.
- Static check confirming the Bay Map recent history remains limited to two actions.
- Browser visual automation was attempted, but the execution environment blocks Chromium from loading local and file URLs; no visual-browser validation is claimed.

---

# Delivery List Scanner - v049 Fullscreen Consolidation and Azure SQL Integration

Date: 2026-07-14

## v049 Changes

### Removed the duplicate fullscreen-resume popup

- Confirmed that the project already had the polished `showActionFeedback()` fullscreen recovery popup used after printing.
- Removed the v048 refresh-specific `confirmWebAppAction()` fullscreen prompt and its duplicate Resume/Continue labels.
- Added one `showFullscreenRecoveryPrompt()` helper that uses the existing action-feedback popup.
- Both print recovery and refresh recovery now call the same helper and the same popup component.
- Automatic fullscreen restoration is still attempted first. The popup only appears when the browser requires a new click.
- Kept one fullscreen refresh session-storage flag and one fullscreen recovery UI path.

### Azure SQL database integration

- Implemented `AzureSqlDeliveryStore` as a real selectable database backend.
- `DLS_DATABASE_TYPE=azure-sql` now selects Azure SQL instead of raising `NotImplementedError`.
- Preserved one copy of all scan, import, rack, bay, user, reporting, and notification business rules.
- Removed 11 older customer-email method copies that were byte-for-byte equivalent in `BaseDeliveryStore` and `SQLiteDeliveryStore`; SQLite and Azure SQL now inherit the single shared implementation.
- Added `azure_sql_compat.py`, a pyodbc-backed connection adapter that translates the limited SQLite dialect used by the existing business layer into T-SQL.
- Added support for SQLite-style `LIMIT`, `INSERT OR IGNORE`, `ON CONFLICT`, row mappings, identity values, transactions, and qmark parameters on Azure SQL.
- Added an idempotent `azure_sql_schema.sql` containing the full application schema and indexes.
- Added `DLS_DATABASE_AUTO_SCHEMA` so the app can create/update the schema during the first deployment and run with reduced database permissions afterward.
- Added Azure SQL health output showing the active Azure database and server.
- Replaced the remaining runtime `sqlite3.Row` type check in rack destination routing with one shared row accessor that supports SQLite rows, Azure SQL rows, and dictionaries.

### Azure hosting and migration files

- Added a production container `Dockerfile` with Microsoft ODBC Driver 18 for SQL Server.
- Added `requirements.txt` for `pyodbc` and `sqlglot`.
- Added `.env.azure.example` with managed-identity Azure SQL settings.
- Added coordinated `PORT=8000` and `WEBSITES_PORT=8000` settings for the application process and App Service container routing.
- Added `.dockerignore` to keep local databases, caches, secrets, and ZIP files out of the image.
- Added `migrate_sqlite_to_azure_sql.py` to initialize the Azure schema and copy the current SQLite data while preserving identity IDs.
- Added `AZURE_DEPLOYMENT.md` with the full deployment, managed identity, migration, Azure Files, staging-slot, backup, and rollout process.
- Updated frontend cache versions to v049.

### Cross-database SQL cleanup

- Replaced the SQLite-only `GROUP_CONCAT(DISTINCT ...)` list query with a shared distinct glass-type query.
- Corrected aggregate `GROUP BY` and `HAVING` clauses so they are valid in both SQLite and Azure SQL.
- Reworked bay capacity selection and in-transit rack selection to avoid SQLite-only aggregate behavior.
- Replaced the remaining SQLite `date('now')` report filters with an explicit UTC date parameter shared by both database engines.
- Kept the local SQLite backend as the default for local development and offline testing.

## Files Added

- `azure_sql_compat.py`
- `azure_sql_schema.sql`
- `migrate_sqlite_to_azure_sql.py`
- `requirements.txt`
- `Dockerfile`
- `.dockerignore`
- `.env.azure.example`
- `AZURE_DEPLOYMENT.md`

## Files Edited

- `app.js`
- `delivery_store.py`
- `scanner_config.py`
- `server.py`
- `index.html`
- `README_CHANGELOG.md`

## Validation Performed

- JavaScript syntax validation with `node --check app.js`.
- Python compilation for the server, configuration, SQLite/Azure stores, compatibility adapter, and migration utility.
- Duplicate JavaScript function and top-level variable declaration audit.
- Python duplicate-definition audit plus an exact-body comparison between the base and SQLite stores, confirming the 11 redundant methods were removed.
- Fullscreen audit confirming one recovery helper and removal of the refresh-specific confirmation popup.
- SQLite initialization and flexible CPU route regression checks.
- Local HTTP server smoke test for `/`, `/api/health`, and static assets.
- Static translation of all literal database statements in `delivery_store.py`, including all upsert statements.
- Parameter-order regression test for SQLite `LIMIT ?` conversion to Azure SQL `TOP`.
- Azure MERGE generation checks for delivery lists, bays, racks, rack items, settings, notifications, and security seed data.
- Azure SQL schema/table/column coverage checks, including every base SQLite column across all 30 tables.
- Azure SQL row-compatibility regression check for shared rack destination routing.
- A live Azure SQL connection was not executed because Azure credentials and a target database were not provided in this chat.

---

# Delivery List Scanner - v048 Flexible CPU Input, Fullscreen Refresh Recovery, Spanish Coverage, and No Rack

Date: 2026-07-14

## v048 Changes

### Flexible CPU-Air and CPU-IT Job Nr. matching

- CPU route hints in Job Nr. are now case-insensitive and tolerate common human spacing or separator variations.
- Customer Pickup examples now recognized include `cpu-air`, `CPU - AIR`, `cpu_air`, `CPU/AIR`, `CPU.AIR`, long-dash variations, and the reversed `AIR - CPU` form.
- Indian Trail examples now recognized include `cpu-it`, `CPU - IT`, `cpu_int`, `CPU / INT`, and reversed `IT - CPU` or `INT - CPU` forms.
- Token boundaries prevent unrelated values such as `CPUITEM` or `CPUAIRPORT` from being misclassified.
- The explicit ROUTE column remains authoritative, preserving the routing order established in v047.
- The browser and backend now use matching route-resolution behavior.

### Refresh button with fullscreen recovery

- Added a dedicated Refresh button beside the language and fullscreen controls.
- Refreshing while fullscreen records a one-time fullscreen-resume request for the newly loaded page.
- The app first attempts to restore fullscreen automatically.
- When the browser requires a new user gesture, the app opens its native styled confirmation popup asking whether to resume fullscreen.
- Declining the prompt continues in normal windowed mode without repeatedly prompting.
- English and Spanish labels are included for the refresh control and fullscreen recovery popup.

### Expanded Spanish coverage for operational names

- Added exact Spanish labels for all standard delivery-list stages, including Staging, Outbound, Indian Trail Inbound, BFS Greenville, Customer Pickup, and DTC.
- Added dynamic translation for date-prefixed stage headings and stage-status summaries.
- Standard rack display names now translate dynamically, including names such as `Rack 1 Steel`, wood/aluminum/coral variants, and `Truck / No Rack`.
- Standard bay display names and gray category subtitles now translate, including spaced, dashed, and underscored names such as `Standard-01`, `Tall 02`, `BFS Mirrors_3`, and `Showers-12`.
- Added translations for common bay statuses and operational labels such as Spacer, Mixed, Hold, Scan Blocked, and Manual.
- The existing centralized translation observer remains the only translation path; no duplicate page-specific translation system was added.

### No Rack scanning option

- Added `No Rack - Leave location blank` to the main Staging transportation selector.
- Selecting No Rack sends an intentionally blank rack assignment instead of a fake rack code.
- The scan still increments the Staging scanned quantity, but no `rack_items` record is created.
- The line's Location value remains blank.
- Rack completion and packing-list actions are disabled while No Rack is selected.
- A clear status message explains the blank-location behavior in English or Spanish.
- Rack-page selection state remains independent from the main scanner selection so the new option does not interfere with rack management.

## Exact Code Locations in v048

### `app.js`

- Operational Spanish translations: `SPANISH_OPERATIONAL_TEXT` near line 1590.
- Shared bay-name translation mapping: `SPANISH_BAY_CATEGORY_LABELS` near line 1672.
- Refresh and fullscreen-resume workflow: `refreshPage()` and `resumeFullscreenAfterRefresh()` near lines 2007-2027.
- Client-side flexible CPU route matching: `inferredRoute()` near line 2925.
- Shared rack options and No Rack sentinel conversion: `groupedRackOptionsHtml()` and `rackCodeForScan()` near lines 3729-3762.
- Main scanner No Rack presentation and action state: `renderScanRackTools()` near line 5175.
- Blank rack assignment sent with scans: `processScan()` near line 6578.
- Refresh and Staging rack event wiring: `wireEvents()` near lines 14912 and 15219.

### `delivery_store.py`

- Backend flexible CPU route matching: `job_number_route_hint()` near line 411.
- Blank-rack scan handling uses the existing `record_scan()` workflow near line 5456.

### `styles.css`

- No Rack scanner state: near line 8227.
- Refresh control icon: near line 27129.

### `index.html`

- Refresh header control: near line 115.
- Cache references updated to v048.

## Validation Performed

- `node --check app.js`
- `python3 -m py_compile delivery_store.py server.py scanner_config.py`
- Backend route matrix covering capitalization, spaces, hyphens, underscores, slashes, periods, long dashes, reversed token order, and false-positive prevention.
- Frontend route matrix using the same supported CPU-Air and CPU-IT variations.
- Explicit ROUTE precedence checks proving Job Nr. hints do not override ROUTE.
- Temporary SQLite import and Staging scan proving No Rack increments scanned quantity, leaves Location blank, and creates zero rack-item records.
- Bay translation pattern checks for spaced, dashed, underscored, singular, and plural standard bay names.
- Duplicate-definition audit confirming each new helper, state path, and renderer exists only once.
- Local server smoke test confirming `/api/health`, the refreshed HTML, and v048 cache references load successfully.

---

# Delivery List Scanner - v047 Manual Edit and CPU Route Resolution Fix

Date: 2026-07-14

## v047 Changes

### Manual line edits now persist correctly

- Saving a manual edit now updates the matching copies of that item across the same delivery date instead of changing only one isolated stage row.
- Shared business fields now remain consistent across Staging, Outbound, and the applicable receiving stage:
  - Order Nr. and Item Nr.
  - barcode
  - quantity
  - dimensions
  - customer
  - route
  - Job Nr.
  - product
  - process and queue states
- Stage-specific scanned quantity remains stage-specific and is not copied to the other stages.
- Location edits now use the newly saved line-item values instead of validating against the stale pre-edit row.
- The app refreshes the delivery-list collection after saving and displays a polished success notice.

### Route changes move the item to the correct receiving list

- Changing a line from CPU to Indian Trail now stores an explicit `IT` route so a customer-route fallback cannot silently change it back to CPU.
- The matching receiving-stage record is moved between Customer Pickup, Indian Trail, Greenville, DTC, or a custom route list while retaining its scan, rack, bay, and audit references.
- Staging and Outbound copies remain available because those stages contain all destinations.
- Quantity reductions are blocked when another stage has already scanned more pieces than the proposed new quantity.

### Revised CPU routing order

1. An explicit ROUTE value is authoritative.
2. Any ROUTE value containing `CPU` is treated as CPU, regardless of Job Nr. wording.
3. When ROUTE is blank, Job Nr. `CPU-IT` or `CPU-INT` routes to Indian Trail.
4. When ROUTE is blank, Job Nr. `CPU-Air` routes to Customer Pickup.
5. A matching customer-route database rule is used for other blank-route CPU jobs.
6. A generic CPU mention in Job Nr. defaults to Indian Trail when no route rule resolves it.

This keeps Job Nr. detection available without allowing generic CPU text to override the ROUTE column or customer routing database.

## Exact Code Locations in v047

### `app.js`

- Client-side route interpretation: `inferredRoute()` near line 2760.
- Manual route selector values: `manualEditRouteOptions()` near line 14310.
- Manual-edit save, full list refresh, and success notice: `saveManualLineItem()` near line 14542.

### `delivery_store.py`

- ROUTE-column normalization: `normalize_route_column()` near line 390.
- Job Nr. CPU pattern handling: `job_number_route_hint()` near line 411.
- Shared route-category resolution: `inferred_route()` near line 422.
- Customer-route database application during imports: `apply_customer_route_rules_to_payload()` near line 4789.
- Matching stage-copy lookup: `manual_edit_sibling_rows()` near line 6547.
- Receiving-list movement after route edits: `sync_manual_route_membership()` near line 6650.
- Manual line-item save and stage synchronization: `update_line_item()` near line 6716.

### Cache references

- `styles.css?v=20260714-v047`
- `app.js?v=20260714-v047`

## Validation Performed

- `node --check app.js`
- `python3 -m py_compile delivery_store.py server.py scanner_config.py`
- Server store creation/import check
- Route-rule matrix covering explicit CPU, CPU-IT, CPU-INT, CPU-Air, generic CPU, and explicit Indian Trail
- Customer-route database test showing generic CPU follows a matched customer rule
- Temporary SQLite manual-edit test proving shared fields update across stages
- Temporary SQLite route-movement test proving CPU to Indian Trail and Indian Trail back to CPU both move the receiving record correctly

---

# Delivery List Scanner - v046 Rack Outbound, Destination Override, and Route Fixes

Date: 2026-07-14

## v046 Changes

### Rack-barcode Outbound scans

- Rack barcode scans now match the Outbound line by delivery date, Order Nr., and Item Nr. even when a source identifier differs between list stages.
- A successful rack barcode scan now consistently updates every dependent Outbound workflow:
  - Outbound scanned quantity
  - scan history and audit history
  - Indian Trail bay preassignment
  - In-Transit counts and manifest status
  - Indian Trail missing-Outbound safety checks
  - rack status and the rack-level Outbound scan timestamp
- Duplicate rack scans preserve the original departure time instead of replacing it with a later duplicate-scan time.

### Rack-level date and time

- Removed the individual piece timestamp column from the In-Transit Manifest.
- Each rack or truck group now shows one **Scanned outbound** date and time from the rack barcode scan.
- The Racks Overview card and selected-rack detail panel now show the same rack-level Outbound timestamp.
- Removed the old per-piece timestamp query and styling to keep the manifest faster and easier to read.

### Indian Trail missing-Outbound popup

- The missing-Outbound warning now opens the custom override popup immediately, before the Scan page refreshes Last Scan and Recent Scans.
- This is used by both scanner-entered barcodes and required Order Nr. / Item Nr. manual scans.
- Selecting Yes opens the custom bay selector; selecting No cancels without changing received quantity or bay assignment.

### Wrong rack destination override

- Scanning an item onto a rack assigned to a different destination now opens a custom popup showing:
  - rack code
  - rack destination
  - item destination
  - order/item and customer
- The operator can cancel or explicitly override the destination check.
- An accepted override records the rack's physical destination on that rack item so the rack remains internally consistent and can still be completed.
- The same override is supported by the main Staging scanner and the Rack-page scanner.

### CPU and destination routing

- CPU, DTC, Greenville, and custom routing now use the imported **ROUTE** column first.
- When ROUTE is blank, the customer-route database is used against the Customer field only.
- Job Nr. text is no longer used to infer CPU. A Job Nr. containing `CPU` can therefore remain on the Indian Trail route when the ROUTE column/customer rule says Indian Trail.
- Scan-page route filters and counts now use the same corrected route logic.

## Exact Code Locations in v046

### `app.js`

- Route interpretation: `inferredRoute()` near line 2760.
- Rack Overview Outbound timestamps: `renderRackBoardCard()` and `renderSelectedRackDetails()` near lines 3927-4080.
- Wrong-destination custom popup: `showRackDestinationOverrideDialog()` near line 4166.
- Rack-page destination override retry: `submitRackScan()` near line 4190.
- Scan-page Indian Trail popup and destination override handling: `processScan()` near line 6372.
- In-Transit rack-level timestamp rendering: `transitManifestRackGroups()` and `transitManifestHtml()` near lines 7191-7310.

### `delivery_store.py`

- Customer-only fallback route matching: `default_customer_route()` and `inferred_route()` near lines 341-420.
- Customer route database application: `route_from_customer_rules()` near line 4748.
- Main Staging destination-override response and persistence: `record_scan()` near line 5396.
- Rack-page destination-override response and persistence: `scan_item_to_rack()` near line 7526.
- Rack destination override calculation: `rack_destinations_from_items()` near line 7727.
- Rack barcode Outbound processing and departure timestamp: `scan_rack_outbound()` near line 8156.
- In-Transit rack timestamp and robust Outbound matching: `_indian_trail_in_transit_payload()` near line 8276.

### `styles.css`

- Rack-level timestamp polish: v046 block near line 28727.

### Cache references

- `styles.css?v=20260714-v046`
- `app.js?v=20260714-v046`

## Validation Performed

- `node --check app.js`
- `python3 -m py_compile delivery_store.py server.py scanner_config.py`
- Temporary SQLite rack-barcode test with intentionally mismatched source IDs
- Outbound quantity, departure timestamp, In-Transit, and Indian Trail safety-gate test
- Main Scan-page and Rack-page destination mismatch/override tests
- ROUTE-column and customer-route database classification test proving Job Nr. `CPU` text does not force Customer Pickup
- Native popup audit confirming no `alert()`, `confirm()`, or `prompt()` calls

---

# Delivery List Scanner - v045 Transit Timestamps, Rush Dates, and Stage Memory

Date: 2026-07-14

## v045 Changes

### In-Transit piece timestamps

- Added an **Outbound Scanned** column to the Indian Trail In-Transit Manifest.
- Each individual in-transit quantity now shows its own outbound scan date and time.
- Multi-quantity line items display `Piece 1`, `Piece 2`, and so on with separate timestamps.
- Items that reached transportation without a recorded Outbound scan clearly display `Outbound scan not recorded` instead of inventing a time.

### Rush delivery date

- Rush broadcast popups now include the delivery date in the alert message and the details grid.
- The backend stores the delivery date in the persistent Rush notification payload so every user sees the same date.
- The immediate Rush result also returns `matchedDeliveryDate` for future confirmation-popup use.

### Indian Trail missing-Outbound workflow

- Hardened the Scan page and Bay Map safety workflow into two custom steps.
- Step 1 clearly states that the item has not been scanned Outbound and asks whether to override.
- Selecting **No** cancels the scan without changing received quantity or bay assignment.
- Selecting **Yes** opens a second custom popup asking which bay should receive the item.
- The same two-step flow is used by regular and manual scans on both Indian Trail scanning surfaces.

### Preserve the current stage when changing dates

- Changing the delivery date on the Scan page now keeps the operator in the same stage whenever that stage exists on the selected date.
- The scanner profile is used as a fallback match before the app falls back to the first available stage.
- Changing dates no longer automatically returns the operator to Staging.

## Exact Code Locations in v045

### `app.js`

- Indian Trail two-step Outbound override: `showIndianTrailOutboundReceiveOverride()` near line 6168.
- Rush popup delivery-date display: `showRushAlert()` near line 6671.
- In-Transit timestamp rendering: `transitManifestRowHtml()` near line 7062.
- Delivery-date stage preservation: `deliveryDateSelect` change handler near line 14873.

### `delivery_store.py`

- Per-piece outbound scan timestamps: `_indian_trail_in_transit_payload()` near line 8178.
- Rush notification delivery date: `mark_sdi()` near line 9811.

### `styles.css`

- In-Transit timestamp styling: v045 block near line 28727.

### Cache references

- `styles.css?v=20260714-v045`
- `app.js?v=20260714-v045`

---

# Delivery List Scanner - v044 Bay Scan Workflow and Custom Dialogs

Date: 2026-07-14

## v044 Changes

### Custom webapp dialogs everywhere

- Removed the remaining native JavaScript `alert()`, `confirm()`, and `prompt()` calls so the browser no longer displays messages such as `IP address says:`.
- Added reusable custom confirmation and text-entry dialogs that match the webapp styling.
- Added a custom confirmation and polished success popup when marking a rack returned.
- Added custom confirmation and success feedback for clearing an individual rack and clearing a complete rack set.
- Converted destructive Admin, route, user, delivery-list, rack, and Bay Map actions to custom dialogs.
- Removed the browser-native unsaved-changes prompt. Print-page lifecycle listeners remain, but they do not display a browser confirmation.

### Required manual-scan fields

- Manual scans now require both Order Nr. and Item Nr. on the main Scan page.
- Bay Map manual scans also require both Order Nr. and Item Nr.
- Manual scans use the same processing paths, validation, bay assignment, history, and undo/redo behavior as scanner-entered barcodes.
- Manual events remain clearly marked as manual in scan and Bay Map history.

### Indian Trail Outbound safety override

- Indian Trail scans now check that the item was scanned Outbound before receiving it.
- When Outbound is missing, a custom safety dialog identifies the item and asks whether to override the requirement.
- Confirming the override requires choosing the destination bay.
- Canceling stops the scan without changing received quantity or bay assignments.
- The same safety workflow is used by the Scan page and Bay Map Add To Bay mode.

### Timed placement guidance

- Successful Indian Trail receives show a 12-second placement popup with the suggested or preassigned bay.
- The operator can override the destination from the popup before it closes.
- Oversize glass attempts to suggest an oversize bay and clearly tells the operator to verify placement.
- The popup distinguishes a normal receive from an already-received item being returned to a bay.

### Bay Map scanner repair and manual scanning

- Reworked the Bay Map scanner around one shared scan function for regular and manual scans.
- `Add to bay` receives or returns the item to the selected bay.
- `Remove from bay` scans the item out of whichever bay currently holds it; a stale Add target no longer blocks a valid scan-out.
- Add To Bay can return an already-received item to a bay without increasing Indian Trail received quantity.
- Bay Map manual scanning now uses required Order Nr. and Item Nr. fields rather than the former Manual Assign workflow.
- Undo and redo are retained for both Add and Remove actions.
- Bay scanning permissions allow Indian Trail receiving users to move, clear, restore, and scan items out without requiring a separate Bay Map management permission.

### Move previously scanned items

- Added a bay-move selector to Last Scan.
- Added a Move column to Recent Bay Scans.
- Added a Move column to All Bay Scans.
- Moving an item uses a custom confirmation and updates the live Bay Map and history.
- All Bay Scans now loads up to 250 recent bay events and includes action, order/item, bay, customer, reason, user, timestamp, and movement controls without horizontal scrolling.

### Bay movement timestamps and job details

- Scan-in and scan-out actions now create dated Bay Map events.
- Manual scan-in and scan-out actions are distinguishable in the event history.
- Selected-bay Job details show when each present item was scanned into the bay.
- The Job summary shows the most recent scan-in time for that Job Nr.
- Scan-out records preserve the source bay, user, date, time, order, item, and reason.

### Sticky scanner-panel fit

- Reduced the normal and fullscreen gap below the application header so the Scan and Bay Map panels sit slightly higher.
- Kept a small safety gap and bottom clearance so the full scanner panel fits between the header and bottom of the viewport.

## Exact Code Locations in v044

Line numbers below refer to the files in this package. Search by the function or element name if later edits shift the lines.

### `app.js`

- Sticky Scan/Bay Map panel position: `syncFullscreenStickyPanelOffset()` near line 1853.
- Rack return custom confirmation and success: `returnRack()` near line 4239.
- Rack reset confirmations: `clearRack()` and `clearRackSet()` near lines 4307-4357.
- Indian Trail missing-Outbound override: `showIndianTrailOutboundReceiveOverride()` near line 6160.
- Timed placement and bay override popup: `showIndianTrailPlacementPrompt()` near line 6235.
- Main Scan-page barcode flow: `processScan()` near line 6302.
- Reusable polished edit/success popup: `showActionFeedback()` near line 6547.
- Selected-bay item timestamps: `selectedBayJobItemsHtml()` near line 7674.
- Bay Map Last Scan and Recent Scan movement controls: `renderBayLastScanCard()` and `renderBayRecentActions()` near lines 8428 and 8463.
- Shared Bay Map Add/Remove scan workflow: `runBayScan()` near line 8594.
- Bay Map required manual scan: `submitManualBayScan()` near line 8676.
- All Bay Scans history GUI: `openBayAllScansModal()` near line 9174.
- Reusable custom confirmation dialog: `confirmWebAppAction()` near line 12542.
- Reusable custom text prompt: `promptWebAppAction()` near line 12643.

### `index.html`

- Main Scan-page manual Order/Item fields: lines 426-441.
- Bay Map Add/Remove selector, target bay, barcode box, and manual scan: lines 680-738.
- Bay Map Last Scan and Recent Scan movement controls: lines 740-772.

### `delivery_store.py`

- Selected-bay Job fulfillment and scan-in timestamps: concrete `get_bay_job_details()` implementation near line 7058.
- Dated Bay Map event/history records and active assignment data: concrete `get_bay_events()` implementation near line 7195.
- Indian Trail receive, Outbound safety, returned-item override, and bay assignment: concrete `receive_indian_trail_scan()` implementation near line 8700.
- Bay scan-out and timestamp logging: concrete `scan_out_bay_item()` implementation near line 9299.

### `server.py`

- Multi-permission helper used by Bay Map scan actions: `require_any_permission()` near line 842.
- Indian Trail receive endpoint: near line 1536.
- Move, clear-assignment, restore-assignment, and scan-out endpoints: approximately lines 1560-1601.

### `styles.css`

- v044 custom dialogs, timed placement popup, movement selectors, Bay history layout, timestamps, and scanner-panel fit: block beginning near line 28306.

## Validation

- `node --check app.js`
- `python3 -m py_compile delivery_store.py server.py scanner_config.py`
- HTML audit: all 268 element IDs are unique and all required manual/Bay Map scan controls are present.
- CSS parse audit completed with zero parse errors.
- Native browser dialog audit found zero `alert()`, `confirm()`, or `prompt()` calls in the webapp source.
- Temporary SQLite workflow testing verified:
  - missing-Outbound scans return the override requirement
  - confirmed override receives into the selected bay
  - scan-out records the bay and timestamp
  - an already-received item can be returned to another bay without increasing received quantity
  - manual scan-in and scan-out events remain distinct
  - Job fulfillment and scan-in timestamps update correctly
  - moving an assignment updates the current bay and event history
- Automated visual browser navigation could not run because this execution environment blocks localhost browser navigation. Static validation and direct backend lifecycle tests passed.

### Cache references

- `styles.css?v=20260714-v044`
- `app.js?v=20260714-v044`

---

# Delivery List Scanner - v043 Wrong-List Guidance and Rush Broadcast Alerts

## v043 Changes

### Wrong delivery-list scan guidance

- Wrong-list errors now identify the matching **delivery-list date only** instead of listing every matching stage on that date.
- Last Scan and Recent Scans now use the concise instruction `Check delivery list date <date>`.
- All Scans normalizes both new and previously saved wrong-list errors so older stage-heavy messages also display only the relevant date.
- Indian Trail receiving now returns the same date-focused guidance in its immediate scan error.

### Check-column alignment

- Rebuilt the success, notice, and error symbols as centered pseudo-icons inside their colored circles.
- Centered the entire Check column in Recent Scans, All Scans, and Bay Map scan history.

### One-time Rush alerts

- Added persistent Rush notifications stored in SQLite.
- Every active user receives one polished production-priority popup for each newly submitted Rush.
- The submitting user keeps the existing Rush success confirmation and is not interrupted by a duplicate alert.
- Other users receive the alert within the normal seven-second notification poll, even when viewing Home, Racks, Bay Map, Scan, or Admin.
- Alerts include Job Nr., order, customer, priority-item count, and submitting user when available.
- Each user acknowledges each alert once; acknowledgment is shared across that user's sessions.
- Rush alerts expire after 24 hours so users returning much later are not shown stale priorities.
- Remakes do not create Rush broadcasts.

### Cache references

- `styles.css?v=20260714-v043`
- `app.js?v=20260714-v043`


## v042 Changes

### Bay Map in-transit rack summary

- The `Racks:` line now includes every transportation rack currently carrying Indian Trail pieces, including `T`, `T2`, and other truck-type racks.
- Removed the five-rack display limit and allowed the rack list to wrap so every active in-transit rack remains visible.
- The quantities are based on pieces still in transit, so fully received racks are removed from the Bay Map transit summary.

### Received item locations

- Added cross-stage receipt detection for Indian Trail, Customer Pickup/CPU, DTC, and Greenville.
- Once an item has been scanned at one of those receiving stages, its Location column displays `Received` instead of its former rack, truck, or bay location on every matching scan list.
- Global item search now also reports the current location as `Received` after one of those receiving scans.
- Added a dedicated green Received location badge.

### Rack received and returned lifecycle

- Racks that remain marked `In Transit` but whose complete contents have been scanned at their destination now display `Received`.
- Received racks remain visually grayed out and unavailable for reuse until they are explicitly marked returned.
- Added a `Received` rack-status filter.
- The Outbound transportation-status selector now distinguishes `Received - awaiting return` from `On the way`.
- Added a visible `Mark Returned` button directly on received rack cards in the Racks overview, while preserving the existing selected-rack return action.
- Marking a rack returned clears its active rack contents and resets it for staging reuse.

### Cache references

- `styles.css?v=20260714-v042`
- `app.js?v=20260714-v042`

## Validation

- `node --check app.js`
- `python3 -m py_compile delivery_store.py server.py scanner_config.py`
- Temporary SQLite lifecycle test verified:
  - truck and standard racks both appear in the Indian Trail in-transit summary
  - a fully received rack derives the `Received` state while its stored lifecycle remains `In Transit`
  - matching staging items receive the cross-stage `received` flag
  - marking the rack returned resets it to `Open` with zero active rack contents

---

# Delivery List Scanner - v041 Scanner History, Outbound Status, and Bay Fulfillment

## v041 Changes

### Scan-panel controls

- Condensed the Indian Trail Bay Assignment control to the same compact footprint as the Staging Transportation Method control.
- Added a compact Outbound Transportation Status selector that is view-only and does not assign pieces to racks.
- The Outbound selector groups racks by rack set and shows whether each rack is still being built, complete and waiting for Outbound, or already scanned Outbound.

### Scan errors and history

- Replaced the confusing `BAD SCAN format - No unique delivery-list match` result with a clear wrong-list message.
- When possible, the detailed error identifies the other delivery date or stage where the item appears.
- Kept Last Scan and Recent Scans concise while giving the All Scans GUI the complete message, reason, raw barcode, resolved barcode, user, station, and time.
- Enlarged the All Scans GUI and removed horizontal scrolling by using a fixed, wrapping table layout.
- Separated delivery-list imports from updates with different event badges and row accents.
- Import and update events now show their source file/details and a successful check mark when completed.

### Bay Map job fulfillment

- Replaced the selected-bay Filled Percentage summary with Job completion and Fulfillment counts.
- Jobs in a selected bay can now be expanded to show every order/item required for that Job Nr.
- Each order item shows the quantity currently in the bay and exactly how many pieces are still missing.
- Job details load only when a bay is selected, keeping the main Bay Map refresh lightweight.

### Spanish coverage

- Added Spanish translations and dynamic quantity translations for the new scanner, scan-history, Outbound status, and Bay fulfillment interface.

### Cache references

- `styles.css?v=20260714-v041`
- `app.js?v=20260714-v041`

## Validation

- `node --check app.js`
- `python3 -m py_compile delivery_store.py server.py scanner_config.py`
- Temporary SQLite wrong-list test verified the new friendly error and other-list hint.
- Temporary SQLite import/update test verified distinct successful event types.
- Temporary SQLite Bay Map test verified Job fulfillment `1/3` and missing item quantity `2` after receiving one piece.
- HTML ID and required-control checks.

---

# Delivery List Scanner - v040 Scanner Header and Sticky Clearance Polish

## v040 Changes

- Added a little more breathing room below the sticky application header for both the Scan page and Bay Map scanner panels in normal and fullscreen modes.
- Reused the live measured header height for normal sticky positioning instead of relying only on older fixed offsets.
- Fixed the Bay Map `Indian Trail Route` header band so it fills the scanner card from the left edge through the right edge.
- Removed the width cap that caused the navy route header to stop short on the right side.
- Balanced the Outbound, in-transit, and Received columns inside the compact route header.
- Corrected the compact in-transit wording for a single piece.
- Cleaned the Bay Map scanner HTML indentation around the route header.
- Updated cache references to `styles.css?v=20260714-v040` and `app.js?v=20260714-v040`.

## Validation

- `node --check app.js`
- `python3 -m py_compile delivery_store.py server.py scanner_config.py`
- HTML parsing and required Bay Map scanner element checks
- CSS checks for the live normal/fullscreen sticky offsets and full-width route band

---

# Delivery List Scanner - v039 Fullscreen Scanner Panel Clearance

## v038 Changes

- Preserved the existing fullscreen-return prompt after printing is completed or cancelled.
- Added parent-window monitoring for the temporary print window. Closing the print page with its window close button is now detected even when the browser does not fire `afterprint`.
- Added `pagehide` and `beforeunload` completion signals to every server-generated print page and the Statistics print page.
- When a print page closes, the main webapp is focused and automatic fullscreen restoration is attempted. If the browser blocks automatic fullscreen, the existing polished one-click `Return to fullscreen` popup appears.
- Prevented duplicate fullscreen prompts when more than one print lifecycle event fires.
- Updated cache references to `styles.css?v=20260714-v038` and `app.js?v=20260714-v038`.

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

## v039 Changes

- Fixed the Scan-page scanning panel overlapping the sticky application header while fullscreen is active.
- Fixed the Bay Map scanning panel overlapping the header while fullscreen is active.
- Added live header-height measurement so the scanner offset adjusts when header controls wrap or the fullscreen viewport changes size.
- Kept the existing non-fullscreen sticky-panel positions unchanged.
- Updated cache references to `styles.css?v=20260714-v039` and `app.js?v=20260714-v039`.
