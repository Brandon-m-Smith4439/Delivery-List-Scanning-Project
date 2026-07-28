## v151 - Project Structure Organization

- Consolidated maintained browser behavior into `static\js\app.js`.
- Organized application services under `backend` and database ownership under
  `database` while retaining `server.py` as the root launcher.
- Moved optional Docker and Azure App Service templates under `deployment`.
- Added the missing container dependency manifest for the Azure SQL adapter.
- Retained `.dockerignore`, `pytest.ini`, and the paired Windows launchers at
  the root because Docker, pytest, and the BAT launcher discover them there.
- Updated automation integration paths and project-structure validation.

## v151 - Bay Scanner Target and Manual Control Alignment

### Bay Map scanner

- Rebuilt Target Bay as a dedicated label row followed by one aligned input-and-Clear control row, preventing overlap with the Add/Remove selector.
- Increased separation beneath the mode selector so the Add destination remains visually distinct at normal and compact workstation heights.
- Rebuilt Manual Scan with a section heading above one aligned Order Number, Item Number, and Submit row.
- Increased the Manual Scan section height, widened the Item Number field, and enlarged Submit while preserving the wider Order Number field.
- Removed Bay Scanner Route Pulse percentage labels in both Add and Remove modes while retaining Outbound, In Transit, and Received quantities.
- Advanced only the changed Bay Scanner CSS and app JavaScript cache keys to v151.

### Compatibility

- Preserved existing Bay Scanner IDs, Add/Remove behavior, target selection, manual scan submission, route quantities, APIs, permissions, and database schema.
- Limited this merge-friendly package to the four files changed for the correction.
- No database migration, installer, BAT file, or backend patch is required.

## v150 - Bay Scanner Control Alignment and Status Refinement

### Bay Map scanner

- Moved Target Bay onto a clean row beneath the Add/Remove selector and aligned its input with Clear.
- Rebuilt Manual Scan with labels above aligned Order and Item fields.
- Increased the Item field and Submit action while preserving the wider Order field.
- Increased Manual Scan height slightly to prevent clipping.
- Removed Route Pulse percentage labels in Add and Remove modes.
- Replaced status text with compact semantic icons in Latest Activity and Recent Bay Scans.
- Applied matching green, amber, red, and neutral background tones to scan-result surfaces.
- Advanced browser cache keys to v150.

### Compatibility

- Preserved the single recent movement, sticky viewport fit, Bay Scan APIs, assignments, All Scans, permissions, and database schema.
- No database migration or backend patch is required.
- No PNG previews were generated or packaged.

## v149 - Bay Scanner Sticky Fit and Input Refinement

### Bay Map scanner

- Limited Recent Bay Scans to one compact physical movement so the latest-scan card remains visible in Add mode.
- Restored Check feedback to Latest Activity and Recent Bay Scans with Success, Check, Failed, and neutral states.
- Sized the sticky scanner from 5 px below the viewport top to 5 px above its bottom.
- Preserved the same five-pixel sticky fit in fullscreen.
- Closed the remaining Bay Map rail spacing while keeping action buttons in normal, non-sticky flow.
- Rebuilt Add destination as one contained Target Bay input and Clear action.
- Condensed Manual Scan into one aligned row with consistent input heights and surfaces.
- Converted Undo and Redo to icon-only controls with accessible labels.
- Applied maintained application button classes to Manual Submit and Clear.
- Advanced browser cache keys to v149.

### Compatibility

- Preserved v148 structural-event filtering, Bay Scan APIs, assignment movement, All Scans, permissions, and database schema.
- No database migration or backend patch is required.
- No PNG previews were generated or packaged.

### Validation

- Added v149 checks for a one-row history limit, Check feedback, five-pixel sticky viewport fit, fullscreen fit, toolbar separation, simplified destination/manual controls, icon-only correction buttons, shared action styles, unique IDs, and code-only release hygiene.

## v148 - Bay Scanner History and Flow Refinement

### Bay Map scanner

- Removed the normal-flow gap between the non-sticky Bay Map action toolbar and the scanner panel.
- Kept the action toolbar static while preserving the scanner-only sticky behavior.
- Removed the visible live-time badge beside the Bay Scanner title and retained its ID as a hidden compatibility node.
- Hid Route Pulse percentage labels in Remove mode while keeping quantity totals visible.
- Replaced Recent Bay Scans' collapsible disclosure with a permanently open compact table.
- Limited recent rows to Order Nr., Job Nr., Action, and editable Current Bay.
- Removed horizontal and vertical scrolling from the recent history surface.
- Advanced browser cache keys to v148.

### History safety

- Bay event history now returns only item-linked physical bay events.
- Structural events such as layout updates, bay creation, and bay deletion are no longer inserted into Bay Scan history.
- Existing historical structural events are filtered from Recent Bay Scans and All Scans.
- Administrative audit records remain intact for accountability.
- No database schema migration is required.

### Validation

- Added v148 checks for static-toolbar adjacency, scanner-only stickiness, hidden live badge, Remove-mode percentage suppression, permanently open non-scrollable history, four-column rendering, editable Current Bay, unique IDs, JavaScript ownership, and backend history filtering.

## v147 - Bay Scanner Route and Sticky Refinement

### Bay Map scanner

- Removed the redundant receiving eyebrow, workflow sentence, and visible Current Mode summary from the blue header.
- Kept the Bay Scanner title, live scan status, and Route Pulse in one continuous header surface.
- Replaced bright Route Pulse surfaces with contained dark-blue metric cards.
- Suppressed the legacy dotted transit connector, arrow, and inherited white transit pill styling.
- Added paint containment to prevent Route Pulse elements from drawing outside the panel.
- Hid Destination Control in Remove mode while preserving it for Add mode.
- Changed only the scanner slot to `position: sticky` with an 8-pixel top offset; the Bay Map action toolbar remains in normal flow.
- Advanced browser cache keys to v147.

### Safety and validation

- No API route, database schema, permission, scan rule, or backend workflow was changed.
- Added v147 release checks for removed header copy, hidden mode summary, route pseudo-element suppression, dark route surfaces, mode-controlled Destination Control, sticky ownership, unique IDs, cache markers, and CSS integrity.

## v146 - Bay Scanner Workflow Refinement

### Bay Map scanner

- Merged the title and Route Pulse into one continuous blue header with all route metrics contained inside the panel.
- Updated Remove copy from `Find the piece's current bay` to `Finds the piece's current bay`.
- Removed the redundant `Current bay is found automatically in Remove mode.` guidance.
- Removed the main barcode Submit Scan button; scanner input and Enter continue to use the maintained form workflow.
- Moved Undo and Redo onto the scan field's upper-right border for faster correction access.
- Replaced collapsible Manual Entry with one Order / Item / Submit row directly below the barcode input.
- Made the Order field flexible and larger, while Item is compact and limited to three numeric characters.
- Preserved route-manifest access, latest activity, recent history, All Scans, and Change Location.
- Advanced browser cache keys to v146.

### Safety and validation

- No API route, database schema, permission, scan rule, or backend workflow was changed.
- Added v146 release checks for header nesting, route containment, removed copy, no barcode submit button, overlay correction controls, manual-row geometry, unique IDs, cache markers, and CSS integrity.

## v145 - Bay Scanner Layout Correction

### Bay Map scanning panel

- Corrected the first v144 console after real floor rendering showed older Bay Scanner grid rules still influencing the new markup.
- Moved Indian Trail Route Pulse above Scan Command so route state is visible before the operator begins a bay scan.
- Removed inherited panel padding and made the blue header meet the outside border and both rounded top corners.
- Replaced the remaining v105/v137 layout-owner classes with dedicated v145 markup while preserving every operational element ID.
- Explicitly reset the scanner form, command, mode, destination, barcode, manual-entry, and activity grids so they cannot collapse into implicit narrow columns.
- Kept Remove/Add, Target Bay, Bay Code, Clear, barcode input, Submit Scan, Undo, and Redo in stable readable rows.
- Raised the sticky desktop offset to 68 pixels normally and 60 pixels on short floor-computer displays; the initial unscrolled position remains unchanged.
- Rebuilt the five Bay Map workflow buttons as an evenly sized toolbar with readable labels, consistent icon sizing, and restrained interaction feedback.
- Kept Recent Bay Scans visible in the short-height sticky layout while maintaining complete-panel visibility.
- Preserved Manual Entry, All Scans, route manifest access, latest result, location correction, and all existing scanner workflows.

### Safety and validation

- No API, database, permission, scan, bay-assignment, transit, undo/redo, or event-handler behavior changed.
- Replaced the v144 scoped stylesheet with the v145 owner instead of loading another override layer.
- Added focused checks for route-before-command ordering, flush header ownership, sticky offsets, professional action-toolbar ownership, stable command rows, unique IDs, cache keys, and release documentation.
- Rendered the corrected panel at normal and 1366x768 sticky workstation sizes and verified it remains stable even when aggressive legacy grid rules are simulated.
- Advanced browser cache keys to v145.

## v144 - Bay Scanner Operations Console Redesign

### Bay Map scanning panel

- Completely rebuilt the Indian Trail Bay Scanner presentation as a compact scan-first operations console.
- Replaced the vertically stacked three-step cards with a single command surface that keeps action, target bay, barcode, Submit, Undo, and Redo together.
- Made the barcode field and primary Submit Scan button the strongest visual controls.
- Reworked Add and Remove into a professional segmented mode selector with clear semantic states.
- Combined target-bay instructions and entry into a compact destination strip that remains understandable in Remove mode.
- Condensed route progress into a small Outbound / In Transit / Received pulse without removing the manifest shortcut or dual progress behavior.
- Kept Manual Entry and Recent Bay Scans available as compact disclosures instead of permanent tall sections.
- Redesigned latest activity to keep current bay, result, order, time, and location correction readable in the right rail.
- Added restrained panel entrance, live-status pulse, header sheen, progress motion, focus feedback, disclosure transitions, and submit-button polish.
- Added a compact-height desktop state that reduces helper copy and reorganizes latest activity while preserving every operational control.
- Added `prefers-reduced-motion` handling so all decorative motion can be disabled without affecting workflow.

### Safety and validation

- Preserved every maintained Bay Scanner HTML ID used by `app.js`.
- Did not change API routes, database schema, permissions, scan logic, undo/redo behavior, or event handlers.
- Added a scoped `bay-scanner-v144.css` owner instead of adding more broad rules to the already layered global stylesheet.
- Added patch validation for unique HTML IDs, required controls, cache keys, release markers, CSS balance, scoped ownership, and reduced-motion support.
- Replaced the unused bottom-docked v144 draft note with the finalized right-rail console documentation.
- Advanced browser cache keys to v144.

## v143 - Internal Reject Timeline Redesign

### Internal Reject Tracking

- Rebuilt the page to match the approved timeline concept with one polished quality-recovery workspace.
- Added a strong IR page identity, primary Log Internal Reject action, and compact Refresh/Clear controls.
- Rebalanced search, incident-range, From, Through, and Location controls into one readable toolbar.
- Added a live filtered summary for total reject events, unique machines/locations, users, and rejected quantity.
- Changed reject history into collapsible date groups with a vertical incident timeline.
- Added expandable event cards that keep the normal view concise while exposing customer, job, product, and notes on demand.
- Kept grouping based on the rejected/logged date and kept delivery date visible on every incident card.
- Hid the routine success status line after data loads while preserving loading, warning, and failure feedback.
- Advanced browser cache keys to v143.

### Safety and validation

- Preserved the existing reject logging API, process-reset behavior, search, date filters, and catalog controls.
- Added release checks for timeline structure, summary metrics, location filtering, version markers, unique HTML IDs, JavaScript syntax, and CSS balance.

## v142 - Custom Roles and Interface Refinements

### Roles and users

- Added a guided **Create a new role** workflow to Roles & Permissions.
- Administrators can enter a role name and description, then explicitly select or omit every available permission.
- Added Select all and Clear all permission actions while keeping zero-permission roles possible after confirmation.
- Added a guarded `/api/admin/roles` create endpoint through an idempotent backend patch that preserves current `server.py` and `delivery_store.py` changes.
- Rejects case-insensitive duplicate role names and unknown permissions.
- Records role creation in the existing audit history.
- Newly created roles automatically appear in Create User, existing-user role selectors, and the User Directory role filter.
- Rebalanced Create User into Account Details and Starting Access panels so the form uses the full modal width and remains readable at smaller sizes.

### Internal rejects and Scan presentation

- Simplified Reject Tracking into one professional workspace with a single title, primary action, filter toolbar, status line, and history area.
- Removed duplicated page headings and workflow-tag clutter.
- Changed the `IR` row flag to white text on a dark, restrained pulsing red background.
- Added a full-width incident strip below rejected Scan rows showing reject reason, break location/machine, rejected date/time, and event count.
- Preserved the normal line-item columns and flags instead of squeezing long incident details into the Job Nr. cell.

### Filters and navigation

- Changed glass-type filters from equal-width truncated cells to content-aware wrapping buttons that show the complete glass description.
- Corrected sidebar navigation line height and lower padding so letter descenders are no longer clipped.
- Advanced browser cache keys to v142.

### Safety and validation

- Added timestamped backend backups and automatic syntax validation to `Apply-v142-RoleManagementPatch`.
- The backend patch is repeat-safe and restores the original files if final validation fails.
- Added v142 release checks for custom-role wiring, dynamic role options, Reject page ownership, full-width reject details, adaptive glass filters, sidebar text containment, version markers, and unique HTML IDs.

## v141 - User Access Management Redesign

- Replaced the Edit Users modal's wide eight-column table with a responsive, expandable user-card directory.
- Added a polished user-management overview showing total, active, signed-in, and inactive account counts.
- Added local search plus Status and Role filters for faster account lookup.
- Added an expandable, guided Create User form with clearer labels, field help, and responsive layout.
- Organized each user into Access & Profile, Password Reset, and Account Status sections.
- Preserved every existing backend workflow for email, role, multi-station assignment, password generation/reset, activation, deactivation, and deletion.
- Replaced icon-only account actions with labeled, accessible buttons while retaining the existing icon library.
- Preserved user-directory filters after saving or refreshing an account.
- Added desktop, compact desktop, tablet, and mobile layouts without horizontal scrolling.
- Added v141 regression checks for markup ownership, event wiring, version markers, CSS structure, and responsive containment.

## v140 - Attention Filters, Reject Controls, and Import Run Deduplication

- Moved **Internal Rejects** from the Status filter group into **Attention** beside Remakes and Rushes.
- Applied the shared priority-button alert/clear presentation to Internal Rejects.
- Made the Filters `IR` counter neutral gray at zero and red only when rejected pieces exist.
- Stabilized the Scan page delivery-date selector width when an unreviewed-update indicator is present.
- Removed the redundant checkmark from the selected delivery-date menu row; the selected highlight remains.
- Limited date-level New/Updated markers to one canonical workflow stage per date so duplicate stage notices do not keep an icon visible after review.
- Immediately clears the reviewed date marker, then verifies the result against the server-side per-user receipts.
- Removed Reject Tracking's Reject events, Rejected pieces, Rejected today, and Affected orders statistic cards.
- Rebuilt the Reject search field with one clean outline instead of nested rounded borders.
- Enlarged and modernized the Reject From/Through date controls.
- Preserved original import-result timestamps and run IDs when building notification history entries.
- Added content-and-time deduplication so the latest import snapshot and its notification copy cannot appear as two runs a few seconds apart.
- Added v140 tests for filter placement, conditional IR styling, date-selector geometry/review cleanup, Reject page cleanup, and near-time import-run deduplication.

## v139 - Dropdown Audio, Internal Reject Awareness, and Import Run History

### Dropdowns and Scan filters

- Added the existing subtle open/close swoosh to maintained dropdown opening and selection.
- Added per-user New/Updated indicators to Scan delivery-date options.
- Added Internal Rejects to the Status filters, a red `IR` row flag, and a labeled `IR` Filters counter.
- Removed the unidentified trailing Filters count.

### Internal rejects

- Reject date filters now use the reject/logged timestamp.
- Reject history groups by logged date while each record displays its delivery date and complete reject details.
- Internal rejects create persistent bell notifications and a nonintrusive 30-second alert with View and Acknowledge actions.

### Import run organization

- Delivery List Management loads the current local day’s automation runs, displays five per page, and resets the current-day view after the date changes.
- Automation Control Center history is nested into collapsible day groups, run-time groups, and individual delivery-list results.

### Validation

- Added v139 regression coverage for selector audio, date indicators, Internal Reject filtering/notification behavior, current-day run pagination, nested automation history, IDs, syntax, and CSS integrity.

## v138 - Internal Reject Page and Entry Workflow

### Reject Tracking page

- Rebuilt the page header into a focused quality-recovery command area with a standard primary **Log Internal Reject** action.
- Replaced generic mini-stat blocks with professional reject-event, rejected-piece, today, and affected-order summary cards.
- Redesigned the history filter into a labeled delivery-date workflow with All Dates, Today, Last 7 Days, Last 30 Days, and Custom Range presets.
- Added From/Through range validation, linked date input limits, a dedicated Clear Filters action, and clearer active-filter status text.
- Redesigned date groups and reject records so order/item, quantity, reason, break location, logged time, user, and notes remain readable without oversized rows.
- Added polished loading, empty, retry, warning, and error states.

### Log Internal Reject GUI

- Added a direct click owner for the static Reject-page button instead of relying only on document-level delegation.
- Opens the reject window immediately, even while reasons and locations are still loading, preventing a slow catalog request from making the action appear broken.
- Added an explicit **Verify Item** button and Enter-key verification for order/item fields.
- Invalidates an old match whenever the order or item changes, preventing submission against stale verification data.
- Shows the verified delivery date, quantity, and affected stages before submission.
- Added clear catalog loading/failure guidance, a workflow-impact notice, Cancel action, and a responsive submit bar.
- Added a modal ownership marker so reject-specific sizing and layout do not affect rack/history dialogs.

### Maintenance and validation

- Removed superseded v137 reject-modal selectors and stale responsive reject overrides instead of adding another duplicate override layer.
- Advanced browser cache keys and per-user notification storage namespace to v138.
- Added v138 release tests for repeatable button ownership, immediate modal opening, date presets, validation, explicit verification, responsive layout, unique IDs, JavaScript syntax, and CSS duplicate detection.

## v137 - Bay Scanner Readability, Packing Lists, and Review Workflow

### Bay Scanner redesign

- Reworked the Bay Map scanner into a contained, readable three-step workflow with larger operational text and shorter instructions.
- Compacted route progress into one horizontal Outbound / In Transit / Received summary with readable percentages.
- Kept target selection, barcode entry, Submit, Undo, Redo, manual entry, latest result, and recent history within the right rail at desktop and responsive widths.
- Added final high-specificity ownership rules so older Bay Scanner compatibility layers cannot restore the broken two-column layout on narrower screens.

### Rack packing-list correction

- Stopped rack-detail and Truck packing-list printing from silently inheriting the currently selected Scan-page delivery date.
- Rack/Truck detail printing now includes all active pieces currently assigned to the selected rack.
- Explicit date-specific print buttons still pass a delivery date when the user deliberately chooses one.
- Packing-list history snapshots use the same corrected selection scope.

### Internal rejects and destructive icons

- Rebuilt the Log Internal Reject GUI into clear Identify and Describe steps with a verification preview and a single deliberate submit action.
- Replaced the one-time static button binding with a guarded delegated trigger so the Log Internal Reject button can be used repeatedly after closing the modal.
- Added visible loading protection while reject catalogs are being requested.
- Changed trash icon buttons to white surfaces with visible red icons at rest; hover/focus intentionally reverses them to white on red.

### New/Updated review and Scan filters

- Removed the duplicate personalized New/Updated banner previously injected below the Scan filters.
- Kept and polished the bottom-right personalized review prompt.
- Added Review Updates and Mark Reviewed controls beside Filters; Mark Reviewed appears only while the New/Updated filter is displaying the exact pending notice set.
- Added compact Remake, Rush, and New/Updated count badges directly in the Filters summary.
- Made the glass-type selector a responsive, vertically scrollable grid so large glass catalogs do not overlap.
- Advanced browser asset cache keys to v137.

## v136 - Interface Stability and Professional Control Polish

### Rack Overview and Reject Tracking

- Fixed rack cards failing to open the rack-details GUI because the modal called helper functions that existed only inside the rack-page renderer.
- Removed the duplicate local rack status wrappers and reused the maintained global rack status helpers.
- Added visible Reject Tracking loading, success, warning, empty, retry, and server-error states.
- Reject history and reject reason/location catalogs now load independently, so a catalog failure no longer blanks otherwise valid history.
- Reject logging verifies an active order/item match, prevents duplicate submissions while saving, and explains when Admin catalog setup is incomplete.
- Replaced the blank reject navigation square with a masked shield/reject icon that works with the current sidebar icon system.

### Bay Scanner and shared controls

- Rebuilt the final Bay Scanner ownership rules so the right rail, sticky slot, panel, workflow steps, inputs, utilities, and history stay within the available width.
- Wide recent-scan tables now scroll inside the scanner card rather than forcing the page wider.
- Changed workflow cards to a stable step-number/content layout that remains readable in the normal right rail and on smaller screens.
- Replaced the broad glossy every-button override with a scoped action-control system.
- Navigation cards, filter tabs, import tabs, route lanes, and other selectable surfaces retain their component-specific appearance.
- Global Search, Print / Export, Admin edit commands, rack actions, reject actions, and Bay Scanner submit controls use the same flatter professional hover/press/focus language.

### Admin GUI and import-run history

- Added a shared polished frame, header, scrolling body, form surface, and close-button treatment for Admin editor GUIs without replacing each editor's internal layout.
- Made import-run tabs proper accessible tabs with persistent selected state, readable active colors, and stable horizontal scroll position.
- Removed the duplicate render path used when selecting an import run, preventing selected tabs from disappearing or being immediately replaced.
- Advanced browser asset cache keys to v136.
- Added focused v136 release tests for rack modal helper ownership, reject resilience, tab accessibility, button scope, sidebar icon rendering, and Bay Scanner width containment.

## v135 - Personalized Update Review and Operations Workflows

### Personalized New/Updated review

- Replaced browser-only New/Updated clearing with persistent per-user line flags and exact notice receipts.
- Loads the selected delivery list and its personalized update flags in parallel so the review prompt no longer delays normal list selection.
- Shows a compact prompt when the selected list contains unseen New or Updated lines for the signed-in user.
- **Review updates** activates the Updated filter first; **Mark reviewed** is enabled only after the same notice set has been displayed.
- Sends the exact notice IDs to the server and clears only that user's receipts for that list. Other users retain their own unseen state.
- Invalid or stale notice sets are rejected instead of accidentally clearing newer changes.
- Clears the client flag cache when a new automation notification/catalog update arrives so unchanged cached results cannot hide a newly imported change.
- Keeps legacy `New Line` / `Updated Line` process text from acting as the authoritative per-user state.

### Import-run navigation and automation history

- Bell notifications now open and pin the exact saved import result that produced the notification.
- Stops the older automation listener from replacing that pinned result with the newest run on the next 10-second heartbeat.
- Added time-based import-run tabs to Delivery List Management with New / Updated, No Changes, Failed, and Running states.
- Keeps a user-selected run active while normal catalog refreshes continue in the background.
- Groups automation audit history by date and time, keeps result details collapsed initially, and preserves searchable/paginated history controls.
- Renamed the Admin command to **Delivery Automation Control Center** to match its actual scheduling, manual-run, status, and history responsibilities.

### Scan page and Bay Map usability

- Preselects today's Staging delivery list during authenticated startup when one exists, so the first visit to Scan begins on today's Staging stage.
- Displays the line's plain quantity in the Scan-page QTY column; scanned progress remains available through row status and hover details.
- Refined the Bay Map scanning panel into a clearer workflow with stronger spacing, hierarchy, status feedback, and responsive behavior.
- Added a shared professional button system with consistent radius, typography, depth, focus, hover, active, disabled, primary, secondary, success, and danger treatments. Existing button sizes and semantic colors remain available.
- Added a v135 CSS ownership note requiring existing selectors and primitives to be reused before new override blocks are introduced.
- Verified the stylesheet has balanced braces and no exact duplicate qualified rules after the release changes.

### Rack workflow and packing-list history

- Removed the permanent selected-rack details column from Rack Overview.
- Clicking a rack now opens a responsive rack-details modal with compact order/item-first rows, quantity, customer, job/glass, dimensions, delivery date, scan time, and existing management actions.
- Corrected long rack scan timestamps so they wrap inside the rack card instead of pushing Reset Rack out of the card.
- Added **Packing List History** to Rack Overview.
- Records an immutable snapshot immediately before a rack packing list is printed, including rack identity, user, print time, delivery date, quantities, and the exact item rows.
- Historical snapshots remain viewable and printable even after the active rack contents later change.

### Manual delivery-list entries

- Added a manual-order form to the Edit Delivery Lists window.
- Requires order, item, quantity, customer, glass/product, dimensions, and an explicit route before insertion.
- Checks the order/item against every active delivery list inside the configured full automation window and blocks duplicates.
- Inserts the line into Staging, Outbound, and the matching destination stage for the selected delivery date.
- Supports a **manual scanning only** declaration with a visible marker and non-scannable `MANUAL-...` identity.
- Adds per-user New notices for every inserted stage copy.
- Patches the maintained delivery-list refresh so manual entries survive automatic imports until the source workbook supplies the same order/item, at which point the source data takes ownership.

### Internal Reject Tracking

- Added a Rejects page to the left navigation with searchable, date-grouped internal reject history.
- Added a guided reject-entry modal for order, item, quantity, reason, break location, delivery date, and notes.
- Added Admin-managed Reject Reasons and Break Locations with safe deactivate/reactivate behavior.
- Logging a reject records an immutable reject event and audit entry, reduces scanned quantity for the rejected piece across active stage copies, adds `reject_reset` scan events, and reduces/removes matching active rack and bay quantities.
- Tracks cumulative reject count and latest reason/location/time on each affected line.
- Shows a red **INTERNAL REJECT** ribbon on Scan-page rows without conflating internal rejects with imported external RM/remake lines.

### Database, safety, and release packaging

- Added numbered/checksummed SQLite migration 004 for reject catalogs/events, packing-list snapshots, manual-entry audit rows, and per-line manual/reject fields.
- Preserved migration 001-003 checksums and the existing verified pre-upgrade backup path.
- Added `operations_features.py` to keep new operational business rules isolated from the large legacy store while reusing its maintained connections, line insertion, access, audit, rack, bay, and import behavior.
- Added `Apply-v135-OperationsPatch.bat` / `.py` to patch the current full `server.py` and `delivery_store.py` safely from a changed-files-only release. Both generated files are compiled before replacement, timestamped backups are retained, and a failed replacement restores both originals.
- Added focused backend, migration, frontend wiring, HTML-ID, CSS-duplicate, patch-idempotence, and checksum regression tests.
- Added `docs/V135_OPERATIONS_WORKFLOWS.md` with installation, permission, review, reject, manual-order, rack-history, testing, and rollback guidance.
- Advanced browser asset cache keys to v135.

## v134 - Floor Scheduler PowerShell Interpolation Fix

- Fixed `Install-DeliveryListSqlAutomationTasks.ps1` failing syntax validation at line 227 before Task Scheduler installation began.
- Delimited the automation-mode variable as `${automationMode}:` so PowerShell does not interpret the literal colon as part of the variable name.
- Preserved the existing `${incrementalTask}:` and `${fullTask}:` task-summary fixes.
- The floor setup still copies the runtime into `C:\DeliveryListAutomation\Scripts`, validates the installed PowerShell files, verifies scanner compatibility, and only then creates the hourly folder-import tasks.
- Existing scanner data, imported delivery lists, automation configuration backups, and SQL isolation remain unchanged.
- Advanced floor-setup and browser release markers to v134.

## v133 - Safe Windows Batch Launchers for Parenthesized Project Paths

- Fixed `Setup-Floor-Folder-Import-Automation.bat` opening briefly and closing before the PowerShell installer started when the project folder contained parentheses, such as `Delivery-List-Scanning-Project-main (5)`.
- Fixed the same CMD parser failure in `Create Desktop Shortcut.bat`.
- Rebuilt both launchers with label-based control flow instead of parenthesized command blocks that expanded project paths during CMD parsing.
- Quotes every project-derived path and keeps delayed expansion disabled so spaces, parentheses, ampersands, and common OneDrive folder names do not alter the command structure.
- Both launchers now always reach a visible success/failure screen and wait for a keypress before closing.
- Added `logs\floor-folder-import-setup-launch.log` and `logs\desktop-shortcut-launch.log` with the selected project/script paths and PowerShell exit code.
- Added `logs\floor-folder-import-setup-error.log` for unhandled PowerShell setup failures.
- Preserved the v132 folder-import-only runtime installation, hourly schedule, SQL isolation, scanner database, existing import configuration backups, and desktop-shortcut behavior.
- Advanced browser asset cache keys to v133.

## v132 - Floor Computer Hourly Folder-Import Setup

- Added `Setup-Floor-Folder-Import-Automation.bat` as a dedicated one-click installer for floor computers that only consume workbooks from the shared Temp Delivery Lists folder.
- Copies the maintained automation runtime into `C:\DeliveryListAutomation\Scripts`, fixing the missing `Install-DeliveryListSqlAutomationTasks.ps1` failure without requiring A+W SQL access.
- Preserves any existing installed automation configuration and runtime scripts in a timestamped `C:\DeliveryListAutomation\Backups\v132-floor-folder-import-*` folder before replacement.
- Forces `folder-import-only` mode, sets the incremental interval to 60 minutes, keeps the broader daily full-window safety refresh, and records the floor-specific audit user.
- Creates `Run-Incremental.cmd`, `Run-Full.cmd`, `Run-Now.cmd`, and `Show-Status.cmd` in the maintained working root.
- Updated Task Scheduler preflight so floor mode verifies shared-folder read access and scanner compatibility without querying A+W SQL or requiring workbook write permission.
- Kept the existing SQL connectivity, workbook generation, destination-write, and scanner preflight unchanged for authorized central SQL modes.
- Disables the older built-in 5 PM importer for the current floor Windows user to prevent overlapping duplicate imports.
- Added `docs/FLOOR_FOLDER_IMPORT_AUTOMATION.md` with setup, verification, task names, runtime paths, backup behavior, and troubleshooting guidance.
- Preserved the production scanner database, scan history, quantities, racks, bays, Rush/Remake state, import history, and per-user review data.
- Advanced browser asset cache keys to v132.

## v131 - Audited Route-Consolidation Preservation Validation

- Fixed floor database transfer validation stopping after a successful migration because `line_items` decreased from 15,096 to 15,068.
- Recognizes the maintained startup repair that merges obsolete duplicate receiving-stage route copies into one current destination row.
- Allows a lower raw `line_items` count only when every removed row is a receiving-stage row and has an explicit `merge_line_item_reference` audit record.
- Verifies an equivalent logical line item still exists for the same delivery date and barcode/source identity.
- Verifies the retained row has at least the same required quantity and scanned progress as every consolidated row.
- Continues to reject any missing Staging or Outbound row, unaudited deletion, missing logical item, reduced quantity, reduced scan progress, missing table, integrity error, or foreign-key violation.
- Records the number of safely consolidated rows and the semantic validation result in `transfer-report.json`.
- Preserves verified backups, failed-copy retention, and automatic restoration of the previous current-project database on any real validation failure.
- Advanced browser asset cache keys to v131.

## v130 - Complete Legacy v096 Schema Before Migration

- Fixed floor database upgrades reaching the current schema version and then failing during startup with `no such table: system_metadata`.
- Replays the canonical v096 schema creation method before migration 002 whenever the database has not yet reached v097.
- Uses the existing idempotent `CREATE TABLE IF NOT EXISTS` and missing-column helpers, so support tables and fields are added without recreating or replacing existing operational rows.
- Covers both unversioned legacy databases and databases that already contain a v096 baseline record but were created before all v096 support tables existed.
- Does not change any historical migration checksum or schema version.
- Preserves verified source/target backups, integrity checks, foreign-key validation, row-count checks, failed-copy preservation, and automatic target rollback.
- Corrected maintained release documentation that had remained labeled v128 after the v129 migration patch.
- Advanced browser asset cache keys to v130.

## v129 - Late-v096 Column Compatibility Repair

- Fixed the v097 migration failing with `no such column: priority_delivery_date` on older floor databases.
- Runs the maintained v096 compatibility preparation before migration 002 so `source_route`, `priority_delivery_date`, and `priority_direct_to_truck` exist before `line_items` is rebuilt.
- Supports both unversioned legacy databases and databases already marked with the v096 baseline.
- Preserved migration checksums, existing operational data, verified backups, validation, and rollback behavior.

## v128 - Windows Project-Root Quoting Fix

- Fixed the floor database transfer failing before the source prompt with a malformed current-project value ending in `" --interactive`.
- Normalizes the BAT project root to a full path without a trailing backslash before passing it as a quoted Python argument.
- Updated all launcher-relative paths to insert their own directory separator instead of depending on the trailing separator from `%~dp0`.
- Added a defensive Python compatibility repair for the exact malformed argument generated by already-extracted v127 launchers.
- Added regression coverage for the Windows quoting failure while preserving interactive path entry, verified backups, migrations, validation, and rollback behavior.

## v127 - Reliable Floor Database Transfer Launcher

- Moved the old-project/database path prompt from the BAT command parser into the Python transfer tool so pasted paths containing spaces, ampersands, parentheses, quotes, and other CMD-sensitive characters cannot terminate the launcher.
- Rebuilt the BAT as explicit non-nested execution labels for the project virtual environment, bundled Python, Windows Python launcher, and PATH Python fallback.
- Kept the transfer window open after success and every handled failure with a final keypress prompt.
- Added `logs\floor-database-transfer-launch.log` with the project root, selected Python runtime, and transfer-process exit code.
- Preserved drag-and-drop support through an environment handoff without embedding the pasted path in the Python command line.
- Added an interactive-path regression test using a folder name containing an ampersand while preserving the v126 backup, migration, validation, and rollback protections.

## v126 - Floor Database Transfer and Upgrade

- Added `Transfer-Floor-Database-To-Current-Version.bat` for moving an existing floor SQLite database into the newest scanner project while preserving operational data.
- Accepts the old project folder, old data folder, or direct `delivery-scanner-pilot.db` path, including drag-and-drop onto the BAT file.
- Uses SQLite's online backup API instead of raw file copying so committed WAL data is included safely.
- Creates verified backups of both the selected old floor database and the database already present in the current project.
- Replaces the current project's database with a verified snapshot of the old floor data, then invokes the current `delivery_store.py` initialization and numbered migrations.
- Validates SQLite integrity, foreign keys, expected schema version, required scanner tables, and before/after row counts for every pre-existing application table.
- Writes a detailed JSON transfer report under `data\backups\floor-database-transfer-<timestamp>`.
- Preserves a failed upgraded copy when possible and automatically restores the prior current-project database if migration or validation fails.
- Refuses unsupported Azure SQL targets, same-file source/target selections, incomplete pre-v096 schemas, damaged databases, and open target files rather than risking silent data loss.
- Added `docs/FLOOR_DATABASE_TRANSFER.md` and targeted success, rollback, and invalid-source tests.
- Advanced browser asset cache keys to v126.

## v125 - Safe Task Scheduler Native Command Handling

- Fixed schedule installation failing when `schtasks.exe /Delete` reported that an obsolete legacy task did not exist.
- Added one maintained Task Scheduler command wrapper that captures native stdout/stderr without allowing Windows PowerShell's `ErrorActionPreference = Stop` to convert expected `schtasks.exe` messages into terminating `NativeCommandError` records.
- Queries each obsolete task before attempting deletion, so a missing legacy task is treated as normal and schedule installation continues.
- Routes task deletion, creation, post-create verification, and the final launch test through the same exit-code-based command wrapper.
- Preserves detailed native command output when an actual task creation, verification, deletion, or launch error occurs.
- Added `Apply-v125-AutomationPatch.bat`, which backs up and replaces only the installed SQL task installer without touching configuration, scanner data, existing tasks, or generated workbooks.
- Kept the v123-v124 SQL/export/import verification, parser checks, timestamp fixes, and legacy-script compatibility repairs intact.
- Advanced browser asset cache keys to v125.

## v124 - Legacy Scheduler Parser Hotfix

- Fixed the remaining schedule-installation failure coming from the older `Install-DeliveryListAutomationTasks.ps1` file left in the shared installed automation Scripts folder.
- Delimited `${incrementalTask}:` and `${fullTask}:` in the legacy Crystal task installer so the file is valid Windows PowerShell.
- Narrowed the maintained SQL scheduler preflight from every `.ps1` file in the shared folder to the six current SQL automation entry points actually used for initialization, runs, installation, removal, status, and verification.
- Prevented retired or unrelated upgrade scripts from blocking installation of the current SQL scheduled tasks.
- Added `Apply-v124-AutomationPatch.bat`, which backs up and replaces both affected installed scheduler scripts without changing configuration, tasks, scanner data, or generated workbooks.
- Kept the v123 end-to-end SQL/export/import verifier and unchanged-list timestamp fixes intact.
- Advanced browser asset cache keys to v124.

## v123 - Schedule Installer Fix, Timestamp Persistence, and End-to-End Verification

- Fixed the PowerShell parser failure in `Install-DeliveryListSqlAutomationTasks.ps1` by delimiting task-name variables before literal colons.
- Added a complete PowerShell syntax scan across the installed automation scripts before Windows scheduled tasks are created.
- Runs the existing SQL connectivity, workbook builder, destination-write, and scanner compatibility preflight before schedule installation.
- Verifies that both scheduled tasks remain queryable after creation before reporting installation success.
- Added `Apply-v123-AutomationPatch.bat`, which backs up and replaces only the affected installed runtime scripts without touching the automation configuration, scanner database, or delivery-list data.
- Added `Verify-SQL-And-Import.cmd` and maintained PowerShell/Python helpers for a real one-date end-to-end test on the authorized workstation.
- The verification forces the maintained folder importer for the selected date after a fresh read-only SQL query and validated workbook export, then requires a successful normalized result and every expected stage list in the configured scanner store.
- Preserved newest-run No Changes timestamps when the Admin summary refreshes by merging database-backed history into the current automation snapshot instead of replacing it.
- Fixed unchanged delivery dates reverting to `Updated at: --` after the latest-run event had already supplied a valid completion timestamp.
- Added explicit CSS maintenance rules requiring existing selectors, shared components, and design tokens to be reused before new declarations or override layers are introduced.
- Advanced browser asset cache keys to v123.

## v122 - CSS Ownership Map and No-Change Import Timestamps

- Reorganized `styles.css` with a maintained table of contents and clearly labeled sections for global tokens, authentication, shell/header/sidebar, Home, Admin, Scan, shared components, Racks, Bay Map, compatibility layers, and current-release ownership.
- Preserved CSS source order so historical compatibility layers keep the same cascade and visual behavior.
- Removed eight verified exact duplicate qualified rules while leaving similar selectors with different values untouched.
- Fixed Delivery List Management result hydration so date-level **No Changes** results inherit every active stage for that delivery date instead of being filtered out for having no changed-stage rows.
- Carries the completed manual or automatic import timestamp into every hydrated stage row, keeping each Delivery List Management date group current even when the maintained importer performs no database rewrite.
- Reviewed the v106-v121 automation architecture, append-only import reconciliation, notification/review flow, and mirrored runtime/package assets.
- Corrected stale README references from the superseded Crystal export folder to the maintained `automation/sql_delivery_export` control center and setup entry point.
- Advanced browser asset cache keys to v122.
- Confirmed the root and `automation/sql_delivery_export` automation assets are intentional deployment mirrors rather than competing runtime implementations.

## v121 - Notification Timing and Review Reliability

- Moved the delivery-list import toast to the bottom center of the page and extended it to 20 seconds.
- Opening the bell notification menu now marks all currently displayed notifications read for that user.
- Removed the Mark all read control and the per-item Mark read wording from the notification menu.
- Stamps every delivery-list result from the newest run with the run completion time, including No Changes results and their stage details.
- Sends the exact reviewed notice IDs when Mark reviewed is selected and verifies that no unseen notices remain.
- Reloads the selected delivery list from the authenticated API after review and immediately removes New Line / Updated Line labels from the current user's visible rows.
- Preserved per-user isolation, current/future-date limits, append-only scan history, scanning quantities, racks, bays, and import audit history.
## v120 - Per-User Delivery-List Update Review

- Removed SQL delivery-list automation notices from the Rush/priority popup queue.
- Added a compact, nonblocking toast that appears for only a few seconds after a new automation result arrives.
- Made bell notification clicks open Admin Delivery List Management and render that notification's complete New/Updated/No Changes/Failed import result.
- Added numbered SQLite migration 003 with backup protection for per-user line-update notices and review receipts.
- Tracks new and updated lines independently for each signed-in user on today and future delivery dates only.
- Keeps unseen changes through repeated no-change imports and clears them only when that user explicitly chooses Mark reviewed for the selected list.
- Reapplies New Line and Updated Line labels per user when list data is read, so one user's review never clears another user's notices.
- Added an unobtrusive Scan-page review banner that requires Review updates before Mark reviewed is enabled, plus unseen counts in stage selectors.
- Excludes removed or retired rows from the New/Updated review queue while preserving their immutable operational history.
- Preserved append-only scan history, existing scan quantities, racks, bays, Rush/Remake state, import history, schedules, and the authoritative latest-import result.
## v118 - Unified Import Center and Append-Only History-Safe Updates

- Moved Import Audit History into the Import / Update Delivery List control center as a fourth tab.
- Removed the separate Import history button and standalone history modal from Delivery List Management.
- Preserved history search, status/date filters, 20/50/100 row paging, newest-first ordering, manual refresh, and collapsed entries.
- Kept history user-driven: it loads when the History tab opens and does not reset the user's scroll position during automatic updates.
- Reduced the notification bell and inherited the same header utility-button styling used by the language, refresh, and fullscreen controls.
- Fixed `scan_events is append-only` import failures with an isolated SQLite reconciliation layer that updates matched line items in place instead of deleting and recreating their identities.
- Preserved scan-event links, scan quantities, rack assignments, bay assignments, Rush/Remake state, and active list metadata during imports.
- Inserts genuinely new source lines, safely retires source-removed history-linked lines, and deletes only unreferenced removed lines.
- Leaves non-SQLite/Azure SQL stores on their native import implementation.
- Preserved live Delivery List Management rerendering, browser catalog sync, detailed logs, schedules, notifications, and workbook integrity validation.
## v117 - Live Delivery Management Refresh and Stable Import History

- Fixed Delivery List Management so the original scanner overview rerenders immediately when the live delivery-list catalog changes.
- Preserved the current page, selected date, selected stage, and active scan workflow; no synthetic selector change events are fired.
- Removed the 15-second Import Audit History auto-refresh that reset scroll position and expanded/collapsed state.
- Import Audit History now refreshes only on open, manual refresh, search/filter/page controls, and a safe hidden synchronization after close.
- All Import Audit History entries now start collapsed.
- Marks the Refresh button when new results arrive while the history window is open instead of replacing the current view.
- Added exact failed-workbook names, dates, and error messages to the command log.
- Preserves the complete normalized failed-import result at `C:\DeliveryListAutomation\State\last-import-result.json`.
- Added repair guidance for damaged XLSX/XLSM files that require Query SQL, Export & Import on a SQL-authorized computer.
- Preserved dedicated history search/pagination, notifications, schedules, scan quantities, route logic, rack and bay assignments, and database-busy retry behavior.
## v116 - Dedicated Import Audit History

- Restored the original Delivery List Management overview instead of replacing it with recent import results.
- Added a separate Import History button and full-screen modal on the Admin page.
- Shows the newest imports first with 20 results per page by default.
- Added selectable page sizes of 20, 50, and 100 results.
- Added search across delivery date, workbook filename, stage/list, user, classification, and error text.
- Added status filters for New, Updated, New + Updated, No Changes, and Failed.
- Added delivery-date range filters, result totals, page numbers, Previous/Next controls, and manual refresh.
- Preserved stage-level audit detail including new/restored stages, added pieces, updated pieces, changed pieces, and changed lines.
- Removed the obsolete inline Temp Delivery Lists folder and date-settings disclosure from Delivery List Management because those settings now live in the Automation Control Center.
- Kept non-disruptive 10-second catalog synchronization so new dates and stages appear without refreshing or navigating users away from their current page.
- Preserved scan quantities, route logic, rack and bay assignments, notifications, automation settings, and scheduled tasks.
## v115 - Non-Disruptive Live Delivery-List Synchronization

- Fixed the Admin page immediately redirecting to Scan when the v114 import-history refresh ran.
- Removed artificial Date and Stage change events from background catalog refreshes.
- Replaced the installed v114 bridge during upgrade so the redirecting code is not left behind.
- Added a silent delivery-list catalog refresh every 10 seconds for every signed-in browser and immediately after import completion.
- New dates and stages now appear without a browser reload while preserving the current page, selection, and active scanner input.
- Kept Recent Delivery List Imports connected to the latest maintained importer result and its New, Updated, New + Updated, No Changes, Failed, restored-stage, and piece-change details.
- Added bounded retry and backoff for transient SQLite/Azure SQL lock or busy conditions so active scanner writes are favored.
- Confirmed that SQL querying, workbook generation, validation, and network publishing do not write to the scanner database; only the final maintained import phase uses short transactions.
- Preserved scan quantities, routes, racks, bays, audit history, notifications, configuration, and scheduled tasks.
## v114 - Immediate Import History Refresh and Correct New-Stage Classification

- Fixed the automation refreshing the hidden legacy import-history element instead of the visible Recent Delivery List Imports section.
- Made the just-completed maintained folder-import result authoritative for New, Updated, New + Updated, No Changes, and Failed labels.
- Added per-stage result rows with added-piece, updated-piece, changed-piece, and changed-line details.
- Preserved stage summaries, reactivated counts, and restored-stage IDs through the import wrapper, run summary, recent-import API, and browser renderer.
- Added a browser-state bridge that refreshes delivery-list state and the Scan page date/stage selectors without a page reload.
- Fixed inactive or deleted stages being restored successfully but classified as No Changes; restored stages are now New.
- Prevented older imports-table rows for the same workbook/date from overwriting the latest run result.
- Retained Excel-compatible workbooks, integrity validation, missing-list recovery, complete logs, notifications, and UNC publishing.
- Preserved scans, routes, racks, bays, audits, configuration, and scheduled tasks.
## v113 - Workbook Integrity, Import Audit, and Deleted-List Recovery

- Fixed SQL-generated workbooks prompting Excel to repair the file and then opening without worksheet data.
- Moved worksheet properties into the SpreadsheetML order required by Microsoft Excel and added full OOXML ZIP, XML, relationship, style-count, and worksheet-order validation.
- Changed order, item, and quantity cells to native numeric cells while preserving the scanner-compatible A/F/G/J/L/N/V/X layout.
- Added a workbook format marker and published-file SHA-256 hash to each date state. Older, damaged, replaced, or repaired files are rebuilt automatically even when A+W data is unchanged.
- Changed SQL export-and-import mode to audit every source date while importing only changed, pending, or missing-list dates, allowing current No Changes results to appear without unnecessary reimports.
- Added a visible `Last checked` timestamp to Recent Delivery List Imports so a successful no-change automation run is distinguishable from a stale page.
- Preserved authoritative New, Updated, and New + Updated classifications from the scanner imports table while retaining newer No Changes and Failed runtime results.
- Added deleted-stage recovery: when one or more expected scanner lists are missing, the wrapper routes that exact date through the maintained `import_delivery_folder` business workflow without direct table edits.
- Preserved scan quantities, route/stage rules, rack and bay behavior, notifications, live logs, UNC publishing, and existing automation settings.
## v112 - Successful No-Change Automation Runs

- Fixed unchanged SQL checks failing with `Cannot bind argument to parameter 'Dates' because it is an empty array.`
- Changed scanner-import date binding to safely accept an empty collection as a defensive fallback.
- Added an explicit pre-import guard so SQL export-and-import mode skips the scanner importer when no changed or pending workbooks exist.
- Added a clear `No changed or pending delivery-list workbooks require scanner import.` log line.
- No-change runs now complete successfully and publish the normal no-change notification instead of a failure notification.
- Preserved changed-workbook imports, pending-import retries, authoritative Recent Delivery List Imports history, complete live logs, UNC publishing, and all scanner data.
## v111 - Import Completion and Live Log Performance Fix

- Fixed the Status & Logs page appearing frozen after the scanner database import had already completed.
- Stopped printing the complete per-file import result JSON to PowerShell stdout; the full normalized result remains stored for Recent Delivery List Imports.
- Changed importer console output to one concise summary line with counts, imported dates, failed dates, and the private result-file path.
- Throttled live-status persistence so the complete growing command log is not rewritten to disk after every individual output line.
- Limited normalized import results to the delivery-date window requested by the automation run so unrelated files cannot be marked imported or flood the status output.
- Added a clear transition log after the scanner importer returns and before its normalized result is processed.
- Preserved v110 UNC/SMB publishing, complete per-run logs, notification reliability, and v109 accurate New/Updated/No Changes/Failed history.
- Preserved all scanner workflows, scan quantities, rack/bay assignments, routes, audio, notification history, and the production database.
## v110 - Live Automation Logs and Network Share Publishing Fix

- Fixed SQL workbook publishing to the shared Temp Delivery Lists UNC folder by avoiding `System.IO.File.Replace` on SMB/network paths, which caused `The path is not of a legal form.`
- Added a network-share-compatible validated overwrite path while retaining atomic replacement for supported local filesystems.
- Changed automation logging to one complete log file per run so manual and scheduled results are not mixed together.
- Rebuilt the **Status & Logs** page to stream the active command output while the automation runs instead of showing only the final 40 lines.
- Added full-log line counts, the exact log-file path, automatic follow-to-latest behavior, and a **Copy Full Log** button for troubleshooting.
- Updated scheduled-run status loading so the complete saved run log remains available after the browser or web app restarts.
- Changed app-notification publishing to use a temporary JSON request file, avoiding Windows command-line quoting and payload-length failures.
- Added clearer progress messages for workbook building, validation, destination staging, overwrite/create actions, scanner importing, and notification publishing.
- Preserved v109 authoritative **Recent Delivery List Imports** classification and retry behavior for New, Updated, New + Updated, No Changes, and Failed files.
- Preserved all scanner workflows, scan quantities, rack/bay assignments, routes, audio, notification history, and the production database.
## v109 - Accurate Automated Import History

- Connected automated SQL/folder imports to the scanner's authoritative `imports` table instead of relying on an isolated automation status summary.
- Updated the Admin **Recent Delivery List Imports** section immediately after manual or scheduled automation completes.
- Added accurate result labels for **New**, **Updated**, **New + Updated**, **No Changes**, and **Failed** imports.
- Corrected the importer wrapper to read `importedFiles`, `updatedFiles`, `skippedFiles`, and `failedFiles` from the maintained folder importer.
- Stopped requested dates from being marked imported unless the maintained scanner importer actually processed them successfully.
- Preserved pending dates when a file fails or is not processed so a later run can retry it.
- Merged authoritative `last-run.json` results into the web control center so completed runs retain import counts and date details.
- Added a protected recent-import API endpoint and automatic Admin history refresh after automation notifications.
- Preserved the v108 Control Center, notification bell, scanner workflows, scan quantities, rack/bay assignments, routes, audio, and production database.
## v107 - Delivery List Automation Control Center

- Changed **Import / Update Delivery List** into a GUI control center instead of immediately running the folder importer.
- Added three safe manual commands: **Import Temp Folder Only**, **Query SQL & Export Only**, and **Query SQL, Export & Import**.
- Added one-date, custom-range, normal incremental-window, and full-refresh-window controls.
- Added configurable automatic modes so temporary floor installations can use folder-only importing while the authorized central installation can query A+W SQL.
- Added GUI controls for interval, past/future date windows, daily full refresh time, destination folder, popup notifications, task installation, and task removal.
- Reused the existing scanner notification queue for success, no-change, and failure popups.
- Added a server-side allowlisted control module; the browser never receives SQL credentials and cannot execute arbitrary commands.
- Preserved all v105 Old Bay, Bay Scanner, audio, database, route, rack, and scanning behavior.
# README Changelog

## v106
- Added `automation/crystal_delivery_export`, a local Crystal Reports automation package that uses the existing SAP Crystal .NET runtime instead of a third-party report scheduler or mouse automation.
- Added automatic `DeliveryDate` parameter injection for `DeliveryList.rpt`, SQL Server login application for report and subreport tables, and XLSX export through `ExportFormatType.ExcelWorkbook`.
- Added Windows DPAPI credential storage so the A+W SQL password is entered only on the local workstation and is never stored in the repository or plain-text task commands.
- Added automatic Crystal runtime discovery, 64-bit/32-bit Windows PowerShell testing, one-date validation, detailed logs, status JSON, and removable Windows Task Scheduler tasks.
- Added hourly incremental refreshes for two days back through fourteen days forward and a daily 5:15 PM reconciliation for seven days back through ninety days forward; both horizons remain configurable.
- Added safe local staging, XLSX signature/size validation, SHA-256 comparison, `.partial` network publishing, overlap prevention, and no-record protection so failed or empty runs do not replace the previous valid workbook.
- Added `import_delivery_folder.py`, which reuses `scanner_config.py` and `delivery_store.py` to import or update the scanner immediately after each automated export run without duplicating import rules.
- Added static tests for the automation file set, known A+W report/database paths, secure credential workflow, safe publishing behavior, and reuse of the maintained scanner business layer.
- Updated the maintained release summary and project documentation links to v106 without changing the v105 Bay Map interface or the v097 database migration contract.

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
