# README Changelog

## v0.357 - Move Rack Layering, Five-Week Packing History, and Shared Page Headers

- Fixed the shared Move Rack destination selector rendering behind the Operations GUI. The body-mounted menu now receives a dedicated `is-rack-transfer-menu-v357` class and explicit top-level stack while preserving the exact Scan-page rack option presentation and automatic above/below placement.
- Reworked Rack History packing-list pagination from 25 individual print days to **5 grouped business weeks per page**. Search filtering is applied before week grouping/paging, and the page summary now reports the visible week range rather than misleading print-day ranges.
- Added `app-page-header-v357` as a shared geometry contract for Home, Statistics, Scan, Racks, Rejects, Bay Map, and Admin. Header height, padding, radius, H1 scale, description spacing, and eyebrow scale are normalized while each page keeps its existing color identity, icons, metadata, and actions.
- Added lightweight page-eyebrow labels to Home, Scan, Racks, and Admin to align their information hierarchy with the existing Statistics, Rejects, and Bay Map header designs.
- Added v0.357 regression coverage for Move Rack menu stacking, true five-week Rack History paging, seven-page header normalization, version/cache references, and schema continuity.
- Advanced application/cache references and `APPLICATION_VERSION` to v0.357. SQLite schema remains version 11; no migration or reset is included.

## v0.356 - Missing Glass Item Selector, Old Bay Investigation Print, Shared Move Rack Selector, and Manage Items Readability

- Threw out the v0.355 generated Missing Glass line ledger and rebuilt the exact-item selector as self-labelled cards. Each imported line now keeps Order/Item, Job Nr., Glass/Size, Physical Bay, Expected, Accounted, Missing, and Rush/Missing/Accounted status together, eliminating layout drift from variable-length content while preserving the exact `data-sdi-line-item-id` contract.
- Completely rebuilt the Old Bays **Print Investigation List** around the same Physical Bay → Order → Glass hierarchy as the browser GUI. Printed orders carry age-derived severity or purple snooze state, snooze time-left/start information, Job Nr./Order/customer identity, aligned physical glass counts/status, Last Physical Scan, order totals, a verification checkbox, and an investigation-notes line. Current Status/Search/Age/Sort filters remain authoritative before rendering.
- Replaced the Move Rack dialog's private nested combobox with the maintained shared custom-select system. Transfer destinations now use `groupedRackOptionsHtml()` and therefore display the same route pills, rack lifecycle cues, rack-set color metadata, and full rack summary as Scan Transportation Method. Because the shared menu is mounted to `document.body`, viewport-aware positioning can open above the dialog instead of clipping below it.
- Normalized Bay Map **Manage Items** typography across headings, search/filter controls, Job Nr. groups, exact glass lines, status badges, selection summaries, destination controls, actions, and status messaging. The GUI dimensions and functional IDs/hooks are unchanged.
- Added v0.356 regression coverage for the new Missing Glass cards, grouped Old Bay print report, shared Move Rack selector, Manage Items typography, version/cache references, and schema continuity.
- Advanced application/cache references and `APPLICATION_VERSION` to v0.356. SQLite schema remains version 11; no migration or reset is included.

## v0.355 - Missing Glass Rebuild, Old Bay State Ribbon, Last Scan Rack Color, and Manage Items Redesign

- Replaced the previous Missing Glass visual implementation with a clean isolated `missing-glass-workflow-v355` workspace. The form no longer carries the legacy `sdi-form` layout class, preventing old Rush/SDI grid ownership from displacing controls or creating the large empty regions seen in the prior GUI.
- Reorganized Missing Glass into a focused main work area and compact handling rail: job/order search, Physical Bay filter, Select Missing action, loaded-job summary, shortage ledger, delivery date, reason, responsible person, direct-to-installer option, collapsible communication settings, and final actions now use one maintained v0.355 layout. Existing control IDs, exact line-item selection, backend requests, email modes, direct-to-truck behavior, and audit behavior are preserved.
- Added a dedicated Old Bays order-state ribbon. Every old order exposes its age in days at the upper left; snoozed orders switch to the maintained purple state and show a live snooze countdown plus the exact snoozed-at date/time. When snooze expires, the order returns to its age-derived orange-to-red severity automatically.
- Extended Last Scan rack presentation with `--last-scan-location-accent`, using the same resolved rack-set color as the rack/location interfaces. Current completed racks still take the maintained green completion color, while historical locations remain visually muted.
- Completely rebuilt Bay Map **Manage Items** into a purpose-specific operator workspace with a search/filter command row, grouped Job Nr. inventory cards, aligned exact-line rows, a current-selection summary, destination/reason controls, and compact move/clear/open-scanner/open-SDI actions. Existing `data-manage-*` selection hooks and move/clear controls are retained.
- Added responsive ownership for both rebuilt workspaces so the Missing Glass and Manage Items layouts collapse cleanly on narrower displays without falling back into older generic grid rules.
- Advanced application/cache references and `APPLICATION_VERSION` to v0.355. SQLite schema remains version 11; no migration or reset is included.

## v0.354 - Normalized All Scans, Smooth GUIs, Visible Rack Errors, Live Rack Color, and Workflow Repair

- Replaced the All Scans Location-only width override with an explicit ten-column table contract. Event, source, item, quantity, customer, Location, Details, user, time, and Check now retain stable proportions; Location still sizes from the longest rendered location label and the history viewport gains horizontal overflow only when necessary.
- Removed the remaining high-cost modal rendering effects: GUI-open state no longer blurs the live application header, backdrops, modal panels, or body-portaled custom-select menus. Modal scroll owners are paint-contained and GUI hover/interaction transitions are shortened to keep pointer feedback synchronized with the cursor.
- Paused Scan/Bay polling, pending-notification polling, delivery-catalog heartbeat refreshes, and focus-triggered catalog detail refresh while a GUI is open. Background work resumes after the modal closes instead of repainting hidden content underneath an active workspace.
- Kept the optimized observer model: English does not keep the translation observer connected, custom-select discovery only inspects nodes that can contain a select, Import History observation moves from one-time discovery to its own result container, and modal observation only reacts to actual modal-state changes.
- Ensured inline Location assignment failures produce the shared in-app error popup in addition to the Scan System notice. Rejected moves to completed racks, incompatible destinations, and other backend assignment blocks now give the operator a direct explanation.
- Refreshes the Scan table immediately after rack lifecycle changes and forces a fresh rack-state read after scans whose response omits the rack catalog, so rack-set Location colors and the green Complete state update without requiring another row click.
- Corrected Old Bays item presentation: only the main order card carries the age/snooze rail, zero-missing values are neutral, actual missing quantities receive limited warning emphasis, and non-missing item status is restored to `ACCOUNTED`.
- Re-aligned Missing Glass by giving the ledger header and every line item one shared eight-column definition, restoring consistent 38px operator controls and preserving all existing field IDs, request APIs, line selection, email modes, and direct-to-truck behavior.
- Advanced application/cache references and `APPLICATION_VERSION` to v0.354. SQLite schema remains version 11; no migration or reset is included.

## v0.353 - Accurate Rack Moves, Faster GUIs, Reliable Rack Actions, Old Bay Aging, and Compact Missing Glass

- Corrected rack-move chronology by resolving the current rack from the newest active `rack_items` assignment rather than rack sort order. Moving `Steel 1` to `Steel 9` now records `Moved from Steel 1 to Steel 9` even when older active/history rows exist.
- Made rack transition writes share one timestamp and changed event-time rack/bay history to treat removal/clear timestamps as exclusive boundaries. `rack_move` events also expose their parsed source/destination so All Scans displays the explicit destination instead of reconstructing move direction from a timestamp tie.
- Reduced the All Scans **Location** column to intrinsic content width so it only occupies the space required by the largest visible location label.
- Removed the largest GUI-open performance hot path: modal state detection no longer calls `getComputedStyle()` / `getClientRects()` for every mutation, the modal observer reacts only to actual modal-state additions/removals/visibility attributes, English no longer translates every inserted DOM node, and custom selects no longer observe unrelated class mutations. Hidden Admin/Bay Action History payloads are lazy-loaded when their history tab is opened.
- Added transient-layer cleanup for body-portaled custom-select menus and strengthened Rack Overview heading action hit targets so **Racks History** and **Edit Racks** do not lose their upper click area after modal/dropdown activity.
- Added an application-wide unexpected-error boundary for uncaught runtime errors and unhandled async failures. These failures now surface through the maintained in-app Action Feedback dialog with a simple operator-readable message/context instead of silently stopping an action.
- Made completed racks override their set accent with the maintained green completion treatment in the Scan **Location** column.
- Completely reformatted Old Bays again around compact identity and aligned item rows: Job Nr. now precedes Order and sits directly beside it; each glass row inherits an orange-to-red age accent that becomes dark red at 30+ days; status reads `MISSING` or `OLD BY X DAYS`; snoozed orders temporarily switch to the maintained purple snooze treatment.
- Matched per-order snooze actions to the bulk snooze button styling, added live **Time Left** on the left and **Snoozed At** date/time on the right, and removed the redundant “active order physically assigned” sentence. Expired snoozes automatically return to their age-derived color.
- Rebuilt Missing Glass into a denser floor workflow with a single search/filter/selection command row, compact physical-shortage ledger, one-line priority fields, collapsible communication settings, and smaller final actions. Existing element IDs, exact line selection, email behavior, direct-to-truck handling, clear behavior, and backend contracts remain unchanged.
- Advanced application/cache references and `APPLICATION_VERSION` to v0.353. SQLite schema remains version 11; no migration or reset is included.

## v0.352 - Rack Route Selection, Historical Locations, Stable Row Selection, Old Bay Normalization, and Missing Glass Rework

- Rebuilt the closed operational rack selection so **Transportation Method** uses the same visual language as the opened dropdown: the route is a leading colored pill and the remaining selected text is `Display Name | PCs | Status`. Route text is no longer duplicated at the end of the selected label.
- Standardized Scan Location rack labels to uppercase across both passive and selected/editable rows while retaining the exact same 12px/850-weight typography.
- Added **Location** to All Scans. Backend event retrieval now resolves the rack or bay active at the event timestamp using existing rack/bay assignment history, preserving historical movement context instead of showing only the current location.
- Added explicit `rack_move` scanner-history events for manual Scan Location changes, including previous and new rack labels, station, user, and audit payload details. No schema change is required because the existing scan-event and assignment history tables are reused.
- Fixed delivery-list row selection drift by preserving the operator-selected line ID across background payload refreshes whenever that row still exists. The latest scan is used only when there is no longer a valid selected row.
- Completely reformatted Old Bays into a normalized Bay → Order → Glass review ledger with quieter bay summaries, one-line order identity/status/age, aligned glass rows, compact physical totals, prominent missing quantities, restrained snooze controls, and collapsible context for other active orders sharing the bay.
- Completely rebuilt Missing Glass configuration around **Find Work → Verify & Select → Rush Handling**. The new item ledger shows Order/Item, Glass/Size, Bay, Expected, Accounted, Missing, and Status in aligned columns; production handling and communication settings are separated into clear cards with one final action bar. Existing line IDs, email modes, direct-to-truck handling, clear behavior, and audit/API contracts remain intact.
- Advanced application/cache references and `APPLICATION_VERSION` to v0.352. SQLite schema remains version 11; no migration or reset is included.

## v0.351 - Rack Color Continuity, Transportation Route Detail, Old Bay Ledger, and Missing Glass Workflow

- Locked Scan Location rack typography to the same 12px, 850-weight treatment in passive and editable states so selecting a row no longer changes the apparent Location font size.
- Added a shared resolved rack-set display color that matches the Racks page exactly, including deterministic hue fallbacks for sets without an explicit saved color. Scan Location cells and rack-option metadata now use that same accent.
- Strengthened the Location rack-cell tint/border treatment so the selected Steel, Wood, Truck, or custom rack set is immediately recognizable while preserving the normal table-cell presentation during inline reassignment.
- Increased the v0.350 compact rack dropdown dimensions by 13% (0.70 → 0.791 of the former menu geometry) and proportionally relaxed opened search/option sizing without returning to the old oversized menu.
- Added the resolved rack route to the closed operational selection text used by **Transportation Method**, while keeping open option labels focused on `Display Name | PCs | Status` and retaining route pills in the opened menu. Inline Location remains compact display-name-only.
- Completely rebuilt Old Bays content as a physical verification ledger: bay headers now show old-order/piece/missing/selected metrics, order cards expose review state and age clearly, item rows use aligned Item/Glass/Physical Count/Status columns, and other active orders sharing the bay are isolated as physical context. Existing filtering, selection, snooze, printing, and history behavior is unchanged.
- Completely rebuilt Missing Glass inside New Request as a guided **Find → Select → Prioritize** workflow. Predictive matches show missing context, loaded jobs expose missing/accounted/Rush/selected metrics, exact lines display physical bay counts and protection status, and priority/email controls are grouped into a cleaner action card. Existing APIs, exact line-item IDs, email modes, direct-to-truck behavior, clearing, and audit history remain intact.
- Advanced application/cache references and `APPLICATION_VERSION` to v0.351. SQLite schema remains version 11; no migration or reset is included.

## v0.350 - Rack Name Correction, Compact Rack Menus, Stable Location Editing, and Unified Request Type

- Corrected the shared rack display formatter so legacy persisted names such as `Rack 1 Steel` and `Rack 1 Wood` render everywhere as `Steel 1` and `Wood 1`. The correction is presentation-only and does not rewrite rack records or codes.
- Preserved the shared operational rack option format as `Display Name | PCs | Status`; zero-piece racks continue to omit the `0PC` segment and show only the display name plus lifecycle status.
- Reduced opened rack dropdown geometry by 30% from the prior presentation, including a 70%-sized menu width/available-height limit and tighter opened option rows. Closed Transportation Method and other operational rack selectors keep their full selected rack information.
- Rebuilt Scan Location rack reassignment so the normal rack-colored Location badge remains visible before, during, and after editing. The custom select now overlays that badge transparently instead of visually replacing the cell when a line is selected.
- Reworked **New Request** into one three-choice request selector: **Rush**, **Remake**, and **Missing Glass**. Missing Glass switches the same New Request workspace to the existing already-imported glass workflow rather than appearing as a separate mode/tab.
- Renamed the modal heading to **Priority Work** while preserving Work Center, Action History, email behavior, intake APIs, Missing Glass item handling, and audit behavior.
- Advanced application/cache references and `APPLICATION_VERSION` to v0.350. SQLite schema remains version 11; no migration or reset is included.

## v0.349 - Rack Selector Clarity, Rack-Color Locations, Unified New Request, and Old Bay Polish

- Standardized every shared rack dropdown label around the operator display name: `Display Name | PCs | Status`. Route text is no longer duplicated in the label because the existing route pill remains visible in opened menus.
- Suppressed zero-piece text for empty racks. Empty choices now read like `Wood 1 | Empty` instead of `Wood 1 | 0PCs | Empty`.
- Corrected the shared selected-label behavior so only explicitly compact selectors collapse to the rack display name. **Transportation Method** and other operational selectors retain full rack information after selection; the Scan-table Location selector remains display-name-only while closed.
- Added rack-set color metadata to shared rack options and reused the same saved Rack Overview color inside Scan Location rack cells. No parallel hard-coded rack color map was introduced.
- Reworked inline Scan Location rack editing so the control reads as part of the normal table cell, uses the rack-set accent, and only reveals stronger editing affordance on hover/focus.
- Reorganized the Old Bay command bar with Search on the left and Status/Age/Sort directly beside **Print Investigation List** on the right. **Select All** now sits immediately left of **Clear Selected**, followed by the selected count and bulk snooze controls.
- Polished Old Bay Bay → Order → Item presentation with stronger physical-bay headers, cleaner selected-order treatment, bordered summary facts, denser item rows, and clearer missing-glass emphasis while retaining the existing grouping, snooze, print, and physical-neighbor data.
- Removed the standalone **Missing Glass Rush** top tab and integrated it into **New Request**. New Request now contains a two-mode workflow: Rush/Remake pre-registration for work not yet imported, and Missing Glass Rush for exact already-imported glass.
- Editing a queued Rush/Remake request returns to the Rush/Remake half of New Request; editing existing Missing Glass priority work returns directly to the Missing Glass half. Existing backend APIs, audit events, email modes, and Work Center behavior are unchanged.
- Advanced application/cache references and `APPLICATION_VERSION` to v0.349. SQLite schema remains version 11; no migration or reset is included.

## v0.348 - Unified Priority Work, Display-Name Racks, and Grouped Old Bay Orders

- Removed the Rush/Remake pre-registration explanation block and merged Requests with Priority Work into a single searchable **Work Center**. Existing requests can be edited without deleting their audit history, and matched requests expose current order/item/customer/route/stage/date/process information.
- Added durable `priority_intake_updated` audit handling and server routing so Rush/Remake request edits update the existing request instead of creating duplicates.
- Kept Priority Work content at a 12px minimum and simplified section copy. Missing Glass Rush remains editable/clearable in the same Work Center.
- Switched operator-facing rack identity to display names across Scan Location, shared rack selectors, rack transfers, Rack Overview, and individual Rack details. Rack codes remain secondary technical identifiers.
- Standardized rack option text as `Route Display Name | PCs | Status`, kept rack-set grouping and route/lifecycle cues, and standardized opened rack menus around 430px.
- Presented legacy truck codes as `RT1`/`RT2` in operator-facing code labels and made newly created truck defaults use the `RT#` convention while retaining legacy database compatibility.
- Removed rack editing from Scan All Scans and removed Bay Map All Scans location editing; both histories are read-only.
- Rebuilt Old Bay content around Bay → Order → Items, including last-scan timing, missing item quantities, physical bay order counts, and compact visibility into other active orders sharing the same bay.
- Widened Old Bay Age/Sort filters, reduced Search width, and aligned Clear Selected/selected totals immediately before the bulk snooze controls.
- Advanced application/cache references to v0.348. SQLite schema remains version 11 with no migration.

## v0.347 - Remake Accountability, Missing Glass Rush, and Rack Selector Cleanup

- Corrected Smart Glazier Remake matching so ordinary numeric suffixes such as `.2`, `.3`, and `.4` are normal work. Remake intake now requires a terminal `.<number>R` generation such as `.2R`, `.3R`, or `.4R`, or an explicit A+W `RM` / `Remake` marker.
- Added reusable Reason and Responsible Person libraries seeded from the supplied historical Remake tracking data. Custom values saved through Rush/Remake or Missing Glass Rush are recovered from the existing audit ledger and become reusable without a schema migration.
- Added recipient selection from active scanner users with saved email addresses. Draft mode opens the user's default mail application with a prepared subject/body and optional recipients; system mode uses the maintained scanner transport; No email remains available.
- Renamed and rebuilt Imported Rush Tools as **Missing Glass Rush** for already-imported jobs. Operators select exact missing pieces, reason, responsible person, optional priority date/direct-to-truck handling, and the same email workflow before applying Rush.
- Rebuilt Current Priority Work as a categorized **Priority Work Center** covering Rush intake, Remake intake, and existing-order Missing Glass Rush with search and category filters.
- Kept Old Bay Print Investigation List on the primary Search/Status/Age/Sort row and aligned it at the far right while preserving v0.346 filter-aware print behavior.
- Removed route text duplication from rack option labels because the opened rack menus already render dedicated route pills. Rack labels now focus on rack code, piece count, and lifecycle state.
- Added compact closed labels for inline rack assignment: the Scan-table selector shows only the rack code while its opened menu expands to the same broad grouped rack view used by operational scanning.
- Polished rack-transfer destination selection with the same rack-set grouping/lifecycle-route cues, compact selected rack code, shared blue Continue action, icons, and maintained hover treatment.
- Kept Transportation Method neutral gray across Complete/Incomplete/On-the-Way rack states and removed the redundant No Rack location explanation from the Scan panel.
- Reduced retained Recent Scans rows from 2 to 1 in the normal Scan panel and from 5 to 4 in full screen.
- Advanced application/cache references to v0.347 while preserving SQLite schema version 11. No migration or reset is included.
- Added v0.347 regression coverage for remake matching, reusable intake choices, recipient/draft behavior, Missing Glass Rush/priority-work UI, compact rack selector labels, and Scan recent-row limits.

## v0.346 - Filtered Old Bay Print and Rush / Remake Intake

- Replaced the Old Bay Live stale / Snoozed workspace tabs with a compact **Status** selector immediately before Age, reduced Search width slightly, and widened the bulk Snooze control.
- Made **Print Investigation List** honor the current Old Bay Status, Search, Age, and Sort state. The server applies the same queue filtering/sorting before rendering the printable physical-review sheet.
- Rebuilt Rush / Remake around a pre-import Order Entry queue. A request records Priority Type, Job Nr., reason, responsible person, creator, timestamps, email choice, and recipients before the new A+W order exists.
- Added durable priority-intake state on the existing append-only `audit_events` ledger rather than introducing a mutable schema table. Requests can remain Pending, become Matched when A+W imports the expected work, or be Cancelled while preserving history.
- Rush intake matches the requested Job Nr. when it arrives. Remake intake follows the Job root and recognizes common Smart Glazier/A+W remake forms including `.2`, `.2R`, and RM/Remake source markers.
- Applied priority-intake decisions inside the maintained import pipeline before route/stage generation. Matching source rows inherit Rush/Remake state, matched requests retain source/order/date details, and repeat imports continue to associate the same matched source identity.
- Added automatic import attention: newly matched Rush requests publish the maintained Rush popup notification; Remake matches publish an in-app Remake notification with Job, orders, reason, responsible person, and affected-list context.
- Added three communication modes to each request: **Send from system**, **Create draft in my email app**, and **No email**. System sends use the maintained email transport/outbox; user-draft mode prepares the message and opens the browser `mailto:` handoff using the logged-in user's saved BFS email as account context.
- Added a polished searchable **Requests** tab while preserving Imported Rush Tools, Current Priority Work, and Action History for already-imported work and existing lifecycle management.
- Extended Rush Action History to include priority-intake creation, email, match, and cancellation events with purpose-specific history details/icons.
- Added external Remake accountability to Statistics reporting: matched intake requests aggregate request count, piece quantity, reason, and responsible person alongside the existing external-remake line/piece metrics.
- Advanced application/cache references to v0.346 while preserving SQLite schema version 11. No database migration or reset is included.
- Added v0.346 regression coverage for Old Bay print-state filtering, Rush/Remake intake UI/routes, import matching/notification ownership, email modes, and external-remake accountability.

## v0.345 - Old Bay Tab Rail and Unified Rack Selector Menus

- Moved All old bays, Live stale, and Snoozed into the Old Bay modal's top tab rail beside Action History. Selecting any queue tab returns the modal to the workspace while Action History cleanly clears the queue-tab active state.
- Reorganized Old Bay tools into a two-row workflow: Search, Age, Sort, and Print Investigation List on the first row; Select All, Clear Selected, selected row/piece totals, Days, and Snooze/Extend on the second row. The Days field remains immediately left of the snooze action, which sits directly below Print.
- Added one shared rack-set grouping helper for operator rack selectors. Scan, All Scans, outbound override/status, and rack-transfer destinations now group racks by set/type and sort rack codes naturally inside each group.
- Added explicit lifecycle dots and route pills to the open custom-select rack options so lifecycle/route colors remain obvious inside the dropdown menu.
- Updated rack-transfer menus to use the same set headings, rack-code labels, lifecycle colors, and route colors as the Scan selector.
- Locked the Scan Complete/Uncomplete and Print/Not On The Way controls to stable desktop widths so state-label changes do not resize the scanning panel.
- Applied a Rack History-only 7px upward SVG correction to its Action History rows, leaving the shared icon alignment unchanged in every other maintained Action History GUI.
- Advanced application/cache references to v0.345. SQLite schema remains version 11 with no migration.
- Added v0.345 regression coverage for Old Bay tab placement/layout, grouped and color-cued rack menus, stable Scan lifecycle button sizing, and the Rack History-only icon correction.

## v0.344 - Persistent Snoozed Bays and Color-Coded Rack Selectors

- Fixed the Old Bays disappearance regression caused by the Bay Map alert refresh replacing the open workspace with an unsnoozed-only result set. Background alert claims now preserve the open all-row workspace, and snoozing from Live stale returns the view to All so the row remains visibly present as snoozed.
- Reorganized the Old Bay command center so Select All, Clear Selected, and selected row/piece totals sit above Search; Age and Sort sit directly beside Search; snooze days sit directly left of the right-aligned Snooze action; and Print Investigation List sits beneath the snooze action.
- Updated the bulk Snooze button to show `Extend Snooze` for fully snoozed selections and `Snooze / Extend` for mixed live/snoozed selections.
- Reversed the snooze ribbon emphasis so remaining time appears first and elapsed `Snoozed ... ago` time appears second.
- Changed operator rack selectors from display names to rack codes while preserving shared compact quantity/route/status labels.
- Added shared rack-selector lifecycle/route color cues to custom selects and the rack-transfer destination combobox. Lifecycle state owns the left color edge; route owns the right color edge.
- Advanced application/cache references to v0.344. SQLite schema remains version 11 with no migration.
- Added v0.344 regression coverage for snoozed-row persistence, Old Bay command hierarchy, adaptive bulk snooze wording, reversed snooze timing, rack-code labels, and rack selector color metadata.

## v0.343 - Old Bay Single-Row Controls, Rack Selector Labels, and History Icon Alignment

- Removed the Old Bay `Physical verification queue / Review and resolve old bay assignments` instructional header and merged Search, selected row/piece totals, Select All, Clear Selected, bulk snooze days, Snooze Selected, Age, Sort, and Print Investigation List into one compact desktop command row beneath the queue tabs.
- Standardized the shared rack selector/transfer label format to operator-facing values such as `Coral 1 (Empty)`, `Coral 1 DTC 2pcs Incomplete`, and `Coral 1 IT 1pc Complete`; the same builder now feeds Staging Scan and rack-transfer choices.
- Removed the completed-rack helper sentence while preserving completed-rack selection for the Uncomplete lifecycle action.
- Aligned Complete/Uncomplete and Print/Not On The Way directly beside the Transportation selector on the Scan page at desktop widths.
- Applied the requested 7px downward optical offset to the shared Action History SVG owner so every maintained Action History GUI receives the same correction.
- Advanced application/cache references to v0.343. SQLite schema remains version 11 with no migration.
- Added v0.343 regression coverage for the unified Old Bay row, shared rack labels, completed-rack helper removal, Scan rack-action alignment, and global history-icon offset.

# Delivery List Scanner Changelog

## v0.342 - Action History Icons, Completed Rack Lifecycle Access, and Old Bay Header Redesign

- Added purpose-specific colored SVG icons to every maintained Action History event row, including shared Admin/Bay/Rack/Reject history views and the all-racks activity list. Event visuals now distinguish scan, move/assignment, print, complete/review, rollback, edit, snooze, removal/warning, create, security, bay, rack, and generic history actions.
- Kept completed racks selectable from the Staging Scan rack selector so operators can reopen them without leaving the Scan page. Completed racks remain blocked from receiving new scans until **Uncomplete** is used.
- Fixed the Staging rack lifecycle controls so dynamic rerenders preserve their icons for Complete, Uncomplete, Mark Returned, Print Packing List, and Not On The Way instead of replacing SVG markup with text-only labels.
- Added the same icon continuity to legacy rack-card Complete, Uncomplete, and Print Packing List actions.
- Fixed the Scan update-review renderer so **Review Updates / Review Changes / Review Open** and **Mark Reviewed** keep their requested icons after label/state updates.
- Removed the redundant Old Bay metric-card strip for Live stale rows, Snoozed, Bays affected, and Oldest row; queue counts remain in the All / Live stale / Snoozed tabs.
- Reworked the Old Bay search/control header into one polished physical-verification command center with a branded workflow intro, stronger queue tabs, prominent Search, grouped selection/snooze actions, and a clean Age/Sort/Print utility row.
- Added v0.342 regression coverage for Action History event icons, completed-rack Staging selection/uncomplete behavior, dynamic Scan action icons, Scan review icons, Old Bay metric removal, and the redesigned command-center hierarchy.
- SQLite schema remains version 11; no migration or database reset is required.

## v0.341 - Rack Action Icons and Old Bay Selection Command Center

- Locked the individual-rack **Uncomplete Rack** and **Not On The Way** rollback actions to their dedicated lifecycle palettes across normal, hover, focus, and nested icon/text states so later shared button rules cannot turn them blue with unreadable text.
- Added purpose-specific SVG icons to every individual-rack lifecycle action: Complete Rack, Mark On The Way, Uncomplete Rack, Mark Returned, Not On The Way, and Print Packing Slip. Existing move/clear controls remain icon-only.
- Added direct action icons to Rack Overview **Racks History** and **Edit Racks**.
- Added compact icons to the Scan page's primary actions and semantic marker dots to its filter tabs while preserving click-to-sort column headers and existing Undo/Redo icon controls.
- Added a magnifier/search SVG to Bay Map **Find Match**.
- Reworked Old Bay queue tabs with distinct blue **All**, orange **Live stale**, and purple **Snoozed** identities plus stronger active states and matching tab icons.
- Rebuilt the Old Bay command center so tabs remain above Search and Search shares the main row with a selected-row/piece summary, explicit **Select All**, **Clear Selected**, bulk snooze days, and the existing purple **Snooze Selected** action.
- Changed bulk selection behavior so **Select All** always selects every row matching the current tab/search/filter and **Clear Selected** is a separate action. The summary now reports both selected rows and selected pieces.
- Removed the verbose review-selection instructions and the redundant Old Bay Done button; Age, Sort, and Print Investigation List remain in a compact secondary tools row.
- Added v0.341 regression coverage for lifecycle hover ownership, Rack/Scan/Bay button icons, colored Old Bay tabs, explicit selection controls, selected-piece totals, and the command-center hierarchy.
- Advanced `APPLICATION_VERSION` to 341 while preserving SQLite schema version 11. No database migration or reset is included.

## v0.340 - Unified Old Bay Command Center and Rack Lifecycle Action Polish

- Moved the Packing List History intro document glyph an additional 3px downward while preserving its existing rightward optical correction.
- Replaced the shared-blue **Uncomplete Rack** and **Not On The Way** buttons in the individual Rack GUI with distinct polished lifecycle rollback styles and purpose-specific SVG icons.
- Rebuilt Old Bay controls as one unified command center: All / Live stale / Snoozed tabs sit above Search, while Search/Age/Sort, Investigation List printing, selection state, bulk snooze, and Done are grouped into a clearer hierarchy rather than equal-sized tiles.
- Reused the same polished purple Zz action treatment for both per-row Snooze / Extend and the bulk **Snooze selected** action.
- Simplified active snooze ribbons to show `Snoozed … ago` on the left and remaining time on the right; removed the redundant total-window line.
- Reduced timer noise by showing seconds only while the elapsed/remaining duration is below one hour.
- Added v0.340 regression coverage for the unified Old Bay control hierarchy, concise snooze timing, shared snooze-action styling, Packing History icon offset, and distinct rack rollback actions.
- Advanced `APPLICATION_VERSION` to 340 while preserving SQLite schema version 11. No database migration or reset is included.

## v0.339 - Old Bay Queue Tabs, Reliable Snooze Extensions, and Rack UI Consistency

- Nudged the Packing List History intro document glyph an additional 2px downward while keeping the existing rightward optical correction.
- Converted individual-rack **Not On The Way** to the shared blue primary-button treatment and removed the old rack-specific amber hover override.
- Rebuilt the Old Bay action strip into evenly sized control tiles with All old bays / Live stale / Snoozed queue tabs, cleaner selection copy, and a direct SVG printer icon for Investigation List.
- Added second-level snooze timing and replaced the previous full-list timer rerender with targeted countdown text updates so open search fields and duration selects remain stable.
- Fixed snooze extension at the backend: extending an active snooze now adds the requested days to its current future expiration instead of resetting it from the current time. Bulk actions preserve the same extension semantics per assignment.
- Moved Bay identity to the far left of each stale-order header, followed by Order Nr., Item Nr., and days old.
- Polished the per-row Snooze / Extend control and clarified its wording so active rows explicitly extend by the selected duration.
- Moved the Bay Map in-transit `Racks:` summary directly below the **Pieces on the way** status pill.
- Added v0.339 regression coverage for queue tabs, second-level countdowns, extension semantics, bay-first order headers, shared Not On The Way styling, and in-transit rack-summary placement.
- Advanced `APPLICATION_VERSION` to 339 while preserving SQLite schema version 11. No database migration or reset is included.

## v0.338 - Manual Rack Departure and Old Bay Control Center Polish

- Corrected the remaining optical alignment of the **Previously printed packing lists** heading icon by moving only the white document glyph slightly right and down inside its existing blue badge.
- Added a confirmed **Mark On The Way** action to completed racks in the individual Rack GUI. The backend validates that the rack is complete and every active rack item has a matching active Outbound line before applying remaining quantities, Indian Trail preassignment, rack-scoped scan events, departure metadata, and `In Transit` status.
- Added `/api/racks/on-way` as the maintained manual-departure endpoint; the existing **Not On The Way** reversal continues to recognize the same `RACK-<code>` scan events so a manual departure can be safely reopened.
- Replaced the five Bay Map launcher pseudo-icons (**Old Bays, Rush, Manage Items, Edit Bays, Edit Map**) with direct SVG artwork for clearer and more consistent visual language.
- Moved Old Bay review/bulk controls out of the bottom footer and into a polished action strip directly below Search/Age/Sort.
- Old Bay Control Center now loads active snoozes as part of the review set, keeps them sorted below live or expired stale work, and shows a purple Zzz ribbon with elapsed snooze time, remaining time, and total snooze window. Existing snoozes use `bay_stale_snoozes.updated_at` as their start timestamp.
- Kept the Old Bays attention badge and six-hour notification limited to unsnoozed work that actually needs review now.
- Rebuilt the printable Old Bay Investigation List with the maintained Barefoot / Builders FirstSource print logo, landscape document framing, summary metrics, readable local timestamps, live/snoozed review-state styling, physical check boxes, and an investigation-notes column.
- Advanced `APPLICATION_VERSION` to 338 while preserving SQLite schema version 11. No database migration or reset is included.

## v0.337 - Notification-Only Multi-Quantity and Rack Hit-Target Stabilization

- Removed persistent multi-quantity controls from **All Scans**. The current scanned/total quantity remains visible, while **Add Qty** and **Scan Remaining** are available only in the immediate successful scan notification.
- Removed the All Scans green-dot **Live audit data** header status pill.
- Consolidated the Packing List History heading artwork to one explicitly sized inline SVG, centered inside the blue badge and shifted slightly left as a complete icon/background unit. Existing per-snapshot paper-icon spacing remains intact.
- Reworked the recurring Rack Overview **Racks History / Edit Racks** partial hit-target failure. The client now checks the real button/header geometry and browser hit test after rack refreshes, modal unlock, page entry, resize, and focus. If only the top portion has slipped under the sticky header, it repairs the retained scroll position before the dead band persists.
- Removed the superseded Rack heading click-forwarding-era CSS ownership and replaced it with one v0.337 hit-target owner using only each button's visible rectangle.
- `APPLICATION_VERSION` is now `337`; SQLite schema remains `11`.

## v0.336 - All Scans Quantity Completion and UI Consistency Fixes

- Removed multi-piece quantity controls from the Last Scan card. The existing successful scan confirmation can still offer immediate quantity completion, while persistent follow-up now lives in All Scans.
- Added compact Add Qty / Scan Remaining controls to the newest eligible All Scans row for each line item. Eligibility requires a successful scan/manual-scan event, remaining unsatisfied quantity, and a delivery date that has not passed.
- Refreshes an open All Scans GUI immediately after a quantity completion action so current scanned totals and remaining-action availability stay accurate.
- Fixed the Edit Racks split-view regression introduced by the v0.335 Action History grid rule: the history panel now becomes a grid only when it is not hidden, and a final hidden-state guard keeps it completely out of Rack Manager layout.
- Replaced the Packing List History intro badge pseudo-element with a real inline SVG document/history icon so affected browsers cannot render the heading as an empty blue block.
- Left-aligned the Print / Export date selector text while preserving the dropdown affordance at the right edge.
- Standardized formatted Excel rows 1–4 by removing the isolated title/metric outline borders; the branded header is now consistently borderless before the structured table begins.
- Advanced `APPLICATION_VERSION` to 336 while preserving SQLite schema version 11. No migration or database reset is included.

## v0.335 - Pinned Action History, Reliable Flag Sorting, and Polished Excel Export

- Changed **Edit Racks → Action History** back to the intended split layout: the heading and search/filter toolbar remain at the top while only the history-result list owns vertical scrolling. This matches Rack History Action History and prevents controls from disappearing during long reviews.
- Fixed Scan-page Flag sorting by replacing the undefined `isInternalRejectItem()` call with the same `internalRejectCount > 0` condition used by the visible Internal Reject flag. The first ascending Flag click now reliably groups flagged rows above rows with no flags.
- Fixed the individual-rack Route status color on initial open by passing the already-resolved `rackRouteClass` through `openOperationsModal(...)`. IT/CPU/DTC/GNV no longer begin gray and then correct themselves only after Complete/Incomplete refreshes.
- Preserved deliberate detailed Print / Export selections. Selecting every route/status/attention/glass detail no longer auto-replaces those choices with Airport, All Status, All Attention, or All Glass. The Create Preset builder uses the same non-collapsing behavior.
- Rebuilt the formatted Excel workbook header so A:B are dedicated to the Barefoot / Builders FirstSource logo while C:H carry a branded title/date/metrics/filter-summary presentation. Increased useful column widths and row heights for a cleaner production document.
- Replaced the Excel logo's fixed two-cell stretch with an aspect-ratio-preserving one-cell anchor bounded to a professional logo area, preventing the source artwork from appearing squished.
- Added worksheet horizontal centering, repeatable table headings, hidden gridlines, page numbering/footer branding, and v0.335 document metadata while preserving the scanner's offline built-in OOXML writer.
- Updated maintained web/print-logo cache references and added v0.335 regression coverage for Action History scroll ownership, Flag sorting dependencies, initial rack-route class forwarding, detailed-filter persistence, and the polished Excel structure.
- Advanced `APPLICATION_VERSION` to 335 while preserving SQLite schema version 11. No migration or database reset is included.

## v0.334 - Packing History Icons, Flag Sorting, and Action History Scrolling

- Replaced the Packing List History heading badge's mask-only artwork with a direct white SVG document/history icon so the heading no longer appears as an empty blue block on affected browsers.
- Shifted the per-snapshot paper icon slightly left and increased its grid spacing so the icon no longer crowds the rack/snapshot text.
- Reworked Scan-page Flag sorting around the markers actually rendered in the Flag column: Remake, Rush, Internal Reject, and Manual scan only. The first Flag-header click groups flagged rows at the top and a second click reverses the grouping.
- Removed process-state and queue-state text from Flag sorting so ordinary unflagged rows are no longer accidentally treated as flagged.
- Fixed Edit Racks Action History scrolling by making the complete history tab the single vertical scroll owner and returning the result list to normal document flow. Wheel/touch input over rows now scrolls the tab and the search/filter controls travel with the history content.
- Narrowed the v0.326 action-history overscroll rule so only actual Operations-modal history lists retain direct containment; Admin Action History relies on its parent tab scroller.
- Updated maintained cache and print-logo references to the v0.334 release key.
- Added v0.334 regression coverage for the robust Packing History icon, snapshot icon spacing, visible-flag sorting semantics, and Admin Action History scroll ownership.
- Advanced `APPLICATION_VERSION` to 334 while preserving SQLite schema version 11. No migration or database reset is included.

## v0.333 - Rack Set Editing and Searchable Packing History

- Fixed existing grouped rack-set edits so each save request includes the rack's current `oldRackCode`. The backend therefore updates the existing rack definition instead of rejecting its unchanged code as a duplicate such as `R1M already exists`.
- Added reusable focus/caret preservation for search/text controls whose history toolbar markup is rebuilt after asynchronous filtering. Rack History and shared Action History searches now keep accepting keystrokes while results refresh.
- Removed the older duplicate `filterPackingHistoryRows()` function that had been overriding the grouped search renderer and only hiding snapshot rows while leaving empty print-date/week groups visible.
- Reworked Packing List History filtering to search snapshots first and then rebuild week/day groups, so dates with no matches disappear completely and matching weeks auto-open while a query is active.
- Expanded Packing List History search indexing to rack code/name, print time/date, delivery date, printed-by user, Order Nr., Job Nr., and delivery dates stored inside each immutable snapshot.
- Added safe `order_numbers`, `job_numbers`, counts, and normalized `search_text` fields to the packing-history API without exposing raw `snapshot_json` to the browser.
- Added common date-format tokens so operators can search equivalent dates using ISO, slash, dash, abbreviated-month, or full-month forms.
- Polished Packing List History content with document icons, snapshot numbers, order/job counts, stronger week/day hierarchy, cleaner metadata columns, query context, and improved card hover/readability styling.
- Updated maintained print-logo cache references to the v0.333 release key.
- Added v0.333 regression coverage for existing rack-set update identity, single-owner packing-history filtering, Order/Job search indexing, focus restoration hooks, and the new history presentation.
- Advanced `APPLICATION_VERSION` to 333 while preserving SQLite schema version 11. No migration or database reset is included.

## v0.332 - Rack Set Workspace Identity and Packing List Polish

- Added a selected-rack-set accent pipeline to the Rack Overview center panel. The saved grouped-set icon color now creates a subtle gradient behind the individual rack cards while each card keeps its own lifecycle status colors.
- Restored `overflow: hidden` on the Rack Overview heading so the decorative top-right circle remains inside the rounded title section. The newer global header hit-testing fix remains responsible for button interaction, so the older overflow workaround is no longer needed.
- Removed the duplicated route suffix from the individual-rack modal description; the header description now reports only the rack piece count because Route has its own dedicated status cell.
- Added `rackResolvedDestination(...)` so the individual-rack Route cell uses the rack's explicit destination when present, otherwise derives one stable route from its contents, and treats populated legacy/no-destination racks as Indian Trail. Mixed-route racks remain neutral instead of being mislabeled.
- Made the IT/CPU/GNV/DTC route palette the final CSS owner so rack-set/material colors cannot override the Route cell after modal refreshes.
- Normalized historical packing-list `printedAt` values to a local `M/D/YYYY h:mm AM/PM` display instead of exposing raw ISO timestamps.
- Rebuilt historical packing-list preview/print HTML with the maintained Barefoot/Builders FirstSource print logo, rack metadata cards, route summary, alternating rows, check boxes, and a print-safe landscape layout.
- Polished the live rack packing-list document with the same maintained print logo, branded accent bar, cleaner metadata/barcode treatment, and a stronger table layout.
- Added v0.332 regression coverage for selected-set gradient ownership, route resolution/final colors, title-card clipping, duplicate-route removal, timestamp normalization, and branded live/history packing-list output.
- Advanced `APPLICATION_VERSION` to 332 while preserving SQLite schema version 11. No migration or database reset is included.

## v0.331 - Scan Page Render and Route Status Color Fix

- Restored the `sortScanItems()` helper that v0.329 accidentally removed together with the retired Scan column-filter popup implementation. `getPagedItems()` continued calling that helper, so the Scan page threw during render, appeared blank, and could flash the date-switch loading state without painting rows.
- Preserved the simplified Scan header interaction: headers remain click-to-sort ascending/descending and the removed funnel buttons/filter popup stay removed.
- Changed the individual-rack **Route** cell to use the same destination palette as Rack Overview instead of inheriting the rack set/material accent: **IT** green, **CPU** purple, **DTC** pink, and **GNV** teal. An unset route uses a neutral gray treatment.
- Added v0.331 regression coverage for the Scan sorting dependency and route-derived rack header classes/colors.
- Advanced `APPLICATION_VERSION` to 331 while preserving SQLite schema version 11. No migration or database reset is included.

## v0.330 - Scan Startup Regression Fix

- Removed the stale `closeScanColumnFilterMenu()` Escape, resize, and scroll listeners that remained after v0.329 intentionally removed the Scan column-filter popup. Those dangling references raised a `ReferenceError` during UI event binding and prevented the Delivery List from loading.
- Removed the empty pointerdown handler left behind by the same retired column-filter implementation.
- Preserved v0.329 behavior: Scan column headers remain click-to-sort controls with no per-column filter buttons or popup menu.
- Added a static regression check that `app.js` contains no `closeScanColumnFilterMenu`, `openScanColumnFilterMenu`, or `scanColumnFilters` references.
- Advanced `APPLICATION_VERSION` to 330 while preserving SQLite schema version 11. No migration or database reset is included.

## v0.329 - Simplified Scan Sorting and Rack Visual Fidelity

- Removed the Scan table's per-column funnel buttons, custom column-filter popup, column-filter state, and column-filter chips. Column headers remain directly clickable and toggle ascending/descending table-wide sorting.
- Preserved the existing status, route, glass-type, free-text filters, active sort chip, paging, and grouped/flat table behavior.
- Fixed individual-rack lifecycle text contrast with explicit lifecycle foreground colors so the status cannot inherit low-contrast heading typography.
- Added a compact **Route** cell immediately to the right of **Rack Status** in the individual-rack GUI header, using the existing shortened rack destination labels.
- Applied the shared blue `app-primary-button` style to the multi-quantity **Add Qty** action in successful scan notifications and Last Scan.
- Completed grouped rack-set icon parity: Glass Cart, Pallet, Dolly, Crate, and Warehouse now render the selected icon on Rack Overview cards and individual-rack GUIs instead of falling back to the generic rack symbol.
- Made the saved rack-set hex color the canonical post-creation visual accent for selected/hovered set cards and rack details, while keeping subtle tinting for backgrounds.
- Advanced `APPLICATION_VERSION` to 329 while preserving SQLite schema version 11. No migration or database reset is included.

## v0.328 - Scan Column Tools, Multi-Quantity Scanning, and Rack Visual Identity

- Added sortable controls to every maintained Scan-page table column. Numeric columns support smallest/largest ordering while text columns support A/Z ordering, and an explicit sort is applied across the entire filtered table rather than inside individual glass-type groups.
- Added custom per-column filters with text operators (**Contains**, **Equals**, **Starts with**, **Does not contain**) and numeric operators (**Equals**, **Not equal**, **Greater than**, **Greater than or equal**, **Less than**, **Less than or equal**).
- Integrated column filters with existing Scan filters, glass-type filters, search, filter chips, paging, and Clear Filters behavior.
- Added an operator Qty field beside Manual Scan Item Nr.; it defaults to 1, validates 1–999, and resets after a successful manual scan.
- Added **Add Qty** and **Scan Remaining** controls to successful timed scan notifications and Last Scan when an item has Qty > 1 with unscanned pieces remaining.
- Added `scanQty` handling to normal and Indian Trail scan APIs. The backend caps the accepted delta at the line's remaining quantity and carries that exact delta through line progress, Staging rack quantity, Outbound auto-stage quantity, Indian Trail receiving, scan events, and audit payloads.
- Fixed the recurring top-half hover/click dead zone on the Rack Overview heading controls by removing pointer hit-testing from the sticky header's background layer while opting actual header controls back in. Removed the prior Rack-only geometry stabilization and click-forwarding workaround.
- Applied each rack set's configured color to the individual-rack GUI; built-in material groups fall back to stable maintained hues, making wood, steel, aluminum, mirror, truck, and custom rack workspaces visually distinct at a glance.
- Enlarged and structured the individual-rack lifecycle cell and added a matching lifecycle-colored edge across the rack header. Lifecycle colors remain identical to Rack Overview for **Incomplete**, **Complete**, **On the Way**, **Received**, and **Empty**.
- Advanced `APPLICATION_VERSION` to 328 while preserving SQLite schema version 11. No migration or database reset is included.

## v0.327 - Rack Status Polish and Natural Page Scrolling

- Restyled the individual-rack header lifecycle cell with the exact Rack Overview lifecycle colors for **Incomplete**, **Complete**, **On the Way**, **Received**, and **Empty**.
- Added a matching lifecycle dot, adaptive content sizing, improved padding/shadow, and responsive title-row wrapping so the status stays visually balanced and its text remains readable next to different rack names.
- Removed the v0.326 `body * { overscroll-behavior: contain; }` rule that could prevent normal document scrolling whenever the pointer was over ordinary non-scrollable content.
- Restricted modal overscroll containment to the actual Admin/Operations body scrollers and action-history list instead of static modal shells or generic history/results class names.
- Removed the broad Scan-page overscroll selectors from non-scrollable scanner/bay panels; true overflow drawers/options continue to keep their existing local containment.
- Advanced `APPLICATION_VERSION` to 327 while preserving SQLite schema version 11. No migration or database reset is included.

## v0.326 - Global Search, Scroll Containment, and Rack Interaction Polish

- Moved Global Search's latest scan date/time onto the same resolved status/location row and aligned it to the right, while adding a contained vertical scrollbar to Smart Results.
- Added scroll-boundary containment across nested GUI/results scrollers and expanded the central modal body-lock detector to every visible shared modal plus rack-transfer dialogs, preventing continued wheel/touch input from moving the page behind a GUI.
- Changed nested rack-transfer close handling to recalculate the shared modal lock instead of blindly unlocking the document while the parent rack workspace is still open.
- Kept the Scan Date/Stage body-mounted custom-select menus positioned during window scrolling and lowered the sticky main scanner panel beneath the sticky application header.
- Added a colored individual-rack lifecycle cell immediately beside the rack name and removed the duplicate rack health-dot presentation plus the body-level Rack Status banner.
- Corrected **Not On The Way** hover/focus styling with a dedicated readable warning palette.
- Disabled-looking move and clear controls now remain hoverable/clickable for explanation when an **On the Way** rack is lifecycle-locked. A shared blocked-action popup explains the required recovery action.
- Added backend lifecycle guards for single rack-item moves, individual rack-item clears, and whole-rack clears so direct/stale requests cannot bypass the existing move-all **On the Way** protection.
- Added a preflight block before clearing an entire rack set when any member rack is On the Way, preventing partial destructive processing.
- Added explanatory blocked-state behavior to rack/rack-set deletion prerequisites and changed non-Scan errors to the shared action-feedback popup instead of forcing an unrelated Scan-page render.
- Removed the duplicate **Clear selected rack set** reset control beside the Status/Sort filters.
- Advanced `APPLICATION_VERSION` to 326 while preserving SQLite schema version 11. No migration or database reset is included.

## v0.325 - Compact Bay Labels and Stage-Aware Location History

- Added one operator-facing bay formatter that collapses canonical internal codes such as `T-BAY12-01` and repeated labels such as `BAY T-BAY12-01` to **Bay 12-01** without mutating the persisted bay code.
- Changed the Scan-page Location column so only Indian Trail receiving shows bay locations; Staging and Outbound remain rack/truck-oriented.
- Added latest bay-assignment history to delivery-list payloads and scan-event payloads. After a bay is cleared or cancelled, the former bay remains visible in a muted gray **prior** state instead of disappearing.
- Replaced the generic **Received** location treatment on Staging/Outbound with the actual rack/truck. After downstream receipt, that transport location is shown in gray as history and is no longer offered as an editable staging rack assignment.
- Updated Last Scan and Recent Scans to use the same stage-aware Location logic and compact bay labels.
- Shortened rack destination display values to **IT**, **CPU**, **DTC**, and **GNV** while keeping the existing persisted destination values and route-class behavior intact.
- Advanced `APPLICATION_VERSION` to 325 while preserving SQLite schema version 11. No migration or database reset is included.

## v0.324 - Persistent Manual Overrides and Superseded Order Enforcement

- Made approved superseded-order decisions durable at the original A+W source-order level instead of resetting an approval when the candidate fingerprint gains or changes items on the same selected removal target.
- Changed immediate superseded-order cleanup to find every active source-owned row by original `source_id` lineage, so a manually changed visible Order Nr./Item Nr. cannot hide an old source row from removal.
- Replaced hard deletion of approved superseded rows with soft retirement plus active rack/bay cancellation, preserving immutable scan, machine, rack, bay, and audit history while removing the old order from live workflows.
- Added order-level entries to `data/superseded-source-exclusions.json`; the SQL exporter now excludes the entire approved source order when rebuilding the shared Excel delivery list.
- Added audit-backed source-owned manual import overrides keyed to the original A+W Order/Item. Only explicitly edited fields remain authoritative; untouched fields can continue following later SQL updates.
- Raised explicit manual route edits above Job Nr. hints and Customer Route Rules so a saved IT→CPU/other route change cannot be re-imported into its old receiving stage.
- Publishes supported manual order/item/qty/dimensions/customer/route/job/product overrides to the shared persistent-decision file and applies them to regenerated SQL workbook rows.
- Adds hidden Source Order/Source Item lineage cells to SQL-generated workbooks so a visible manual Order Nr./Item Nr. edit can survive workbook round-trips without becoming a second source identity.
- Advanced the workbook integrity marker to `v324-ooxml-2`, so older generated workbooks are rebuilt once into the lineage-aware format instead of being accepted as current from prior state hashes.
- Updated the workbook builder to honor a persisted dimensions override without changing the underlying source-unit conversion for normal SQL rows.
- Updated automated folder-import drift calculation and end-to-end verification to use the same `prepare_import_payload(...)` path as the actual importer.
- Advanced `APPLICATION_VERSION` to 324 while preserving SQLite schema version 11. No migration or database reset is included.

## v0.323 - Self-Healing Automated Import Schedule Runtime

- Fixed **Save & Install Schedule** on local/network-folder scanner installations where `C:\DeliveryListAutomation\Scripts\Install-DeliveryListSqlAutomationTasks.ps1` had never been deployed.
- Expanded runtime synchronization to include the maintained scheduler installer/remover/status/verification scripts, workbook/import helpers, notification publisher, compatibility validator, and verified-source exclusions.
- Added schedule-runtime preparation that writes the current saved settings to the stable installed config path and creates `Run-Incremental.cmd` / `Run-Full.cmd` before invoking Task Scheduler.
- Preserved existing automation settings and database/state files; the runtime refresh does not replace the operator's selected network folder, mode, schedule window, or notification settings with defaults.
- Uses the scanner's active Python interpreter when a floor-folder configuration has not yet recorded a Python path, allowing the no-SQL compatibility preflight to complete.
- Keeps the saved `ScheduleEnabled` flag aligned with the actual Windows task state when installation fails, then marks it enabled only after a successful installer return.
- Preserved the folder-import-only scheduler preflight so floor computers verify shared-folder read access and scanner compatibility without querying A+W SQL.
- Advanced `APPLICATION_VERSION` to 323 while preserving SQLite schema version 11. No migration or database reset is included.

## v0.322 - Automated DL Import Tab Scrolling

- Restored contained vertical scrolling to the Automated DL Import **Run Now**, **Schedule**, and **Status** workspaces so longer tab content and bottom actions remain reachable.
- Kept the Automation Control Center frame fixed to the viewport and avoided reintroducing a second outer modal scrollbar.
- Preserved Import History's dedicated results-only scrollbar so its filter/header/footer controls remain stable while history rows scroll.
- Replaced the blanket active-tab `overflow: hidden` behavior with explicit non-History scrolling ownership.
- Advanced `APPLICATION_VERSION` to 322 while preserving SQLite schema version 11. No migration or database reset is included.

## v0.321 - Rack Cards, Persistent Bays, and Indian Trail Scan Safety

- Reworked Rack Overview lifecycle badges so **Incomplete**, **Complete**, **On the Way**, and other statuses size to their text instead of consuming a flexible card grid row.
- Anchored the Rack Overview reset action to the lower-right of each card so lifecycle text, outbound timestamps, and destination pills cannot push the control around.
- Changed bay-layout startup seeding to bootstrap-only behavior for existing rows. Saved names, grouped-set names, bay policy/status, capacity, active state, category, source cell, and layout coordinates now remain database-authoritative after restart.
- Made the old synthetic-bay cleanup a one-time migration-style repair and changed built-in role permissions to bootstrap-only defaults, so later Admin visibility/role edits are not silently restored by a server restart.
- Added a large **PLACE THIS ORDER IN / BAY ##** destination block to successful Indian Trail receive notifications, including Order Nr. and Job Nr. context.
- Added a prominent Current Bay destination to Last Scan, added explicit Job Nr. labeling, and added Bay information to Recent Scans.
- Made Manual Bay a one-scan override on the Indian Trail Scan page; a successful manual receive clears the selected manual bay and returns the scanner to Auto.
- Added latest scan date/time beneath Global Search's resolved current stage/location for scanned items.
- Removed occupied/preassigned bays from new manual-bay choices while preserving the already assigned bay in the post-scan correction selector.
- Added transaction-level one-order-per-bay validation to manual assignment, receiving, outbound preassignment, location editing, bay moves/restores, and Rush preassignment.
- Changed Indian Trail auto/preassignment grouping from Job Nr. to Order Nr. so different orders that share a Job Nr. can never be automatically placed in the same physical bay.
- Expanded scan-event payloads with current bay identity so Last Scan and Recent Scans remain accurate after refresh.
- Advanced `APPLICATION_VERSION` to 321 while preserving SQLite schema version 11. No migration or database reset is included.

## v0.320 - Truck Rack Consistency and Manage Items Scrolling

- Standardized Truck 1/Truck 2 operator-facing identity across staging, rack management, location displays, Global Search, scan confirmations, and Indian Trail in-transit data while retaining the historical `T` database code for Truck 1 compatibility.
- Removed the old `Truck / No Rack` presentation. The dedicated No Rack selector is now the only maintained blank-location choice, and legacy `NORACK` input no longer aliases Truck 1.
- Changed the Staging rack selector to default to No Rack, disable Complete/On-the-Way destinations, and automatically clear a stale selection when its rack lifecycle changes.
- Added backend lifecycle validation before Staging scan quantities/rack assignments can change, closing the path that allowed a stale On-the-Way truck selection to receive another piece.
- Reused the same open-rack rule for direct rack scans, item/rack moves, manual rack-location recovery, and outbound transportation overrides so failed moves leave the original rack assignment untouched.
- Added a contained vertical scrollbar to the Manage Bay Items left order/item workspace so long lists scroll instead of compressing their cards.
- Added/updated regression assertions for Truck 1 labeling, No Rack separation, locked-rack safeguards, Manage Items scrolling, cache keys, and application versioning.
- Advanced `APPLICATION_VERSION` to 320 while preserving SQLite schema version 11. No migration or database reset is included.

## v0.319 - Manage Items Readability and Bay Scanner Footer Boundary

- Rebalanced the Manage Bay Items workspace to give the left-side job/order list more room and prevent exact-item details from becoming tiny or clipped.
- Reflowed exact-item rows into a two-line card layout that preserves complete item identity, glass/product/size, grouped bay location, and status information.
- Made the custom fixed Bay Map scanner footer-aware so it moves upward with the page boundary and stops before the desktop footer instead of overlapping it.
- Changed the Bay Scanner in-transit piece count to full white text for better operational contrast.
- Verified the shared action-history renderer already surfaces Job Nr., Order Nr., and Item Nr. for the requested Old Bays, Rush, Edit Bays, and Manage Items actions when those values exist in the audit payload; no redundant history path was added.
- Advanced `APPLICATION_VERSION` to 319 while preserving SQLite schema version 11. No migration or database reset is included.

## v0.318 - Bay Operations, Exact-Item Management, and Priority Work Clarity

- Added the restrained outline-circle visual treatment to the Old Bay Control Center and Bay Map scanner-panel headers.
- Made Old Bays order cards selectable from their full non-interactive surface while preserving normal controls and checkbox behavior.
- Reworked Current Priority Work to keep expanded Rush details above surrounding outlines and expose original/new delivery dates, marked time/user, bay, item, product/size, direct-to-truck handling, and reason.
- Added grouped bay-set names to Manage Bay Items locations and introduced whole-job/exact-item multi-selection with Select All and Clear Selection.
- Changed Manage Bay Items move/clear actions to operate on exact selected assignment IDs so sibling items may be manually split across different bays.
- Expanded Selected Bay job details to show each sibling item's actual current bay/group, including items located outside the selected bay.
- Enriched bay assignment, bay-policy, Old Bays, Rush, and layout audit payloads and action-history summaries with specific job/order/item/location/date context.
- Chunked Priority Work audit metadata lookups to remain safe on large delivery days.
- Advanced `APPLICATION_VERSION` to 318 while preserving SQLite schema version 11. No migration or database reset is included.

## v0.317 - All-Date Transit Count and Bay Selection Polish

- Changed the Bay Map **Pieces On The Way** figure to use the same all-date physical in-transit manifest as the In-Transit GUI, so a departed Indian Trail rack contributes even when its delivery date is not today.
- Preserved today's Outbound sent, Indian Trail received, and route progress totals as date-specific values; added explicit date-specific in-transit fields for diagnostics without exposing them as the all-date headline count.
- Replaced the Edit Bays Select All checkbox with compact **Select All** and **Clear All** buttons and made each bay row's non-form surface toggle selection for faster multi-bay editing.
- Kept per-bay checkboxes synchronized with row selection, selected counts, and the Apply To Selected action.
- Merged Location Corrections guidance into a compact top line and forced the All Bay Scans content grid to size rows to their content, preventing the guidance block from ballooning when scan history is sparse.
- Advanced `APPLICATION_VERSION` to 317 while preserving SQLite schema version 11. No migration or database reset is included.

## v0.316 - Physical In-Transit Counts, Bay Bulk Editing, and Scan Archive Compaction

- Rebased Indian Trail in-transit totals on active physical rack assignments once a rack has departed, so pieces remain counted even if the staging/source delivery-list copy is later superseded, made inactive, or soft-deleted by a delivery-list update.
- Deduplicated equivalent Order Nr./Item Nr./rack assignments by keeping the largest live quantity for one physical rack, then subtracts Indian Trail received quantity once per physical item before allocating the remainder across departed racks.
- Added Select All and per-bay selection to Edit Bays with bulk Category, Capacity, and Assign Behavior updates for any subset of bays in the selected grouped set. Bulk changes reuse the existing progress/busy feedback while each selected bay is saved.
- Promoted **Physical bay scan history** to the actual All Bay Scans modal title with **Indian Trail activity archive** and the explanatory copy in the shared modal heading rather than a second oversized hero inside the body.
- Replaced the duplicate history hero with a compact Retained / Total scans / Page strip and reduced Location Corrections guidance to a single compact row.
- Advanced `APPLICATION_VERSION` to 316 while preserving SQLite schema version 11. No migration or database reset is included.

## v0.315 - In-Transit Rack Icon and Numeric Date Repair

- Restored real rack-set artwork in the Indian Trail In-Transit Manifest by reusing the maintained rack icon library instead of a generic circular marker.
- Carries saved rack-set icon colors into In-Transit rack headers, including custom A-frame glass cart and other administrator-selected rack visuals.
- Changed In-Transit delivery-date cells from full weekday/month wording to compact `M/D/YYYY` formatting such as `8/14/2026`.
- Applied the same compact delivery-date formatting to individual Rack content rows for consistent rack presentation.
- Advanced `APPLICATION_VERSION` to 315 while preserving SQLite schema version 11. No migration or database reset is included.

## v0.314 - Rack Hitbox, All-Date In-Transit, and Bay Editor Feedback

- Hardened Rack History/Edit Racks after page navigation by rechecking heading geometry after the asynchronous rack refresh and forwarding clicks that fall inside the visible action rectangles even when a stale transparent shell layer wins browser hit testing.
- Disabled scroll anchoring on the Rack Overview heading/content so later DOM refreshes cannot pull the top of those actions back under the sticky application shell.
- Changed the Indian Trail In-Transit Manifest to include every active departed Indian Trail rack across delivery dates instead of silently limiting the manifest to the dashboard/today date.
- Kept Bay Map Outbound, Received, in-transit counts, and the route progress bar date-specific; future/past in-transit pieces appear in the manifest without inflating today's progress.
- Added Delivery Date to mixed-date in-transit item rows, removed the temporary Test 100% sound button, and polished the manifest header with the shared outlined-circle treatment.
- Applied the shared blue primary-button format to maintained Edit Bays save/create actions.
- Added live bay-by-bay progress feedback and busy-state protection while grouped bay-set changes are written sequentially.
- Advanced `APPLICATION_VERSION` to 314 while preserving SQLite schema version 11. No migration or database reset is included.

## v0.313 - Rack Action Hitbox and Compact Delivery Update Preview

- Fixed the Rack Overview page-transition hitbox regression by resetting application scroll owners after page visibility changes, preventing the sticky header from retaining an overlap over the top of Rack History and Edit Racks.
- Removed the expanded pseudo-element click surface from Rack History/Edit Racks and returned both actions to a smaller 36-pixel true button rectangle.
- Narrowed the Delivery List Update Preview control center from the previous wide desktop footprint and reduced surrounding padding/vertical spacing.
- Removed the preview filter buttons, search field, result counter, and four redundant top metric cards; the preview now focuses on date totals, route dropdowns, orders, and changed items.
- Condensed route and order presentation while preserving exact glass colors from Lookup Manager, item glass type/size/QTY, change badges, and before/after values for updated fields.
- Advanced `APPLICATION_VERSION` to 313 while preserving SQLite schema version 11. No migration or database reset is included.

## v0.312 - Compact Bay Capacity and Managed Glass Color Palette

- Condensed grouped Physical Bay utilization to a compact `occupied/total` fraction that remains inside the small group header while retaining color emphasis on the current occupied count.
- Restored Rack Overview route/destination badges to the upper-right corner.
- Added a Glass Colors library to Lookup Manager using the existing `admin_lookup_values` table, keeping SQLite schema version 11 unchanged.
- Populated Glass Colors from the maintained known-glass vocabulary and active/discovered glass products.
- Added administrator-editable exact hex colors with stable automatic defaults for glass types that have not been customized.
- Replaced Delivery List Update Preview's page-local generated hues with the shared Lookup Manager palette, including reusable CSS variables for future glass-aware interfaces.
- Advanced maintained application/cache references to v0.312.

## v0.311 - Rack Transfer, History, Preview, and Bay Persistence

- Fixed whole-rack content moves failing after the transfer because the source-rack reset still referenced obsolete `completed_by`, `departed_by`, and `returned_by` columns that are not part of the maintained rack schema.
- Made both Packing List History and All Racks History own a bounded vertical scroll region inside the Rack History control center so expanded weeks and long action logs remain reachable.
- Moved Rack Overview route/destination badges to the upper-left and hardened the full Rack History/Edit Racks button surfaces against decorative header hitbox interference.
- Shifted one percentage point from the Scan Route column to Progress and kept compact progress pills such as `Outbound 0/1` on one row.
- Removed the Glass Type dropdown level from Delivery List Update Preview; routes remain the only dropdowns and each route now contains polished static Order cards with flat item rows.
- Added exact glass type and glass size to every preview item and assigned stable per-product hues so each clear thickness, mirror, and antique-mirror product has its own visual identity.
- Preserved operator-edited bay display names during startup layout seeding so server restarts no longer restore the bootstrap JSON name over the database value.
- Replaced grouped-bay `3/30 used` fractions with a compact occupied/total summary and utilization meter that transitions green to orange to red as capacity fills.
- Advanced `APPLICATION_VERSION` to 311 while preserving SQLite schema version 11. No migration or database reset is included.

## v0.310 - Physical Bay Policy and Attention Clarity

- Restored the compact `AUTO` / `MAN` grouped-bay policy indicator in the upper-left of Physical Bay Map group headers, with `MIX` and `BLK` fallbacks for mixed or fully blocked sets.
- Split grouped utilization text so the occupied value in labels such as `3/32 used` is visually emphasized while `/32 used` remains neutral supporting text.
- Kept the occupied value utilization-aware, moving from green through orange to red as a bay group approaches full capacity.
- Added a small `!` indicator to every individual bay that contributes to the grouped attention count and attached the specific attention reasons to its tooltip/accessibility label.
- Centralized bay attention classification so group counts and individual indicators use the same error, stale-bay, and Picking/SDI rules.
- Advanced `APPLICATION_VERSION` to 310 while preserving SQLite schema version 11. No migration or database reset is included.

## v0.309 - Rack Creation Compatibility, Sticky Stage, and Bay Group Status Polish

- Centralized new rack insertion through a compatibility-safe helper that explicitly supplies rack lifecycle values and neutral defaults for legacy SQLite `NOT NULL` columns without defaults, preventing `racks.completed_at` creation failures.
- Raised Racks History and Edit Racks actions above decorative Rack Overview heading layers so the top portion of each visible button remains clickable.
- Kept Scan Date/Stage context menus attached to their sticky controls during document scrolling and gave Stage explicit pointer/z-index ownership so the Stage dropdown remains selectable after scrolling down the Scan page.
- Removed the legacy CSS-generated second `used` suffix from Physical Bay group utilization text.
- Added utilization-aware Bay group count coloring that transitions from green through orange to red as occupied bays approach the group total.
- Replaced the wide Bay group `N attention` strip with a small unobtrusive exclamation/count badge while preserving a descriptive tooltip and accessible label.
- Advanced `APPLICATION_VERSION` to 309 while preserving SQLite schema version 11. No migration or database reset is included.

## v0.308 - Rack Creation, Review Scope, History Scroll, and Preview Workflow Repair

- Made Staging/Outbound Mark Reviewed acknowledge every currently existing update notice across active stages for that delivery date for the signed-in user only; Indian Trail, Greenville, CPU, and DTC direct review remains stage-specific.
- Fixed Add Rack Set failing on strict `racks.completed_at` schemas by using explicit empty-string lifecycle values for new and reactivated racks instead of `NULL`/implicit defaults.
- Added existing-rack visibility to Add Individual Rack for the selected rack set, including code, display name, and lifecycle state; duplicate rack code/name protections remain enforced.
- Repaired the Racks History modal grid so the records tabs and body have dedicated rows, the body scrolls vertically, expanded weeks remain reachable, and the `print days · snapshots` summary stays compact.
- Added a prominent lifecycle banner to individual Rack details so Complete, Incomplete, On the way, Received, and Empty state is obvious above the displayed orders.
- Forced Edit Racks groups into independent full-width collapsible rows so expanding Wood, Coral, or another set cannot push Truck or a neighboring set downward through shared grid-row sizing.
- Updated Delivery List Update Preview so selected non-Airport routes open automatically, whole-list/Airport previews keep routes collapsed, order sections are no longer dropdowns, and route headers show two concise metrics such as `23 New Lines | 26 New QTY`.
- Removed redundant Physical Bay Map group policy/open indicators while retaining `used`, blocked, and attention information where useful.
- Raised the sticky Scan panel above overlapping list content so Stage/Date controls remain clickable while scrolled and removed residual pseudo/overflow styling that could render a black dot beside the RM flag.
- Advanced `APPLICATION_VERSION` to 308 while preserving SQLite schema version 11. No migration or database reset is included.

## v0.307 - Rack Review Synchronization and Rack Manager Reliability

- Made Staging/Outbound Mark Reviewed propagate by the durable automatic-import source fingerprint instead of requiring identical notice timestamps across stage copies; review receipts remain isolated to the signed-in user and affected Stage markers clear immediately before the authoritative refresh.
- Kept manual-entry review propagation isolated by its change token and retained a legacy timestamp fallback only for notices without a source fingerprint.
- Prevented duplicate active individual rack codes and duplicate rack display names with both live form validation and backend transaction checks.
- Added live rack-set validation for duplicate set names and generated rack-code collisions before Create Rack Set can submit, with matching backend validation and form-local error text instead of relying on a generic red flash.
- Synchronized backend rack-set visual support with the UI icon library, including A-frame glass cart, pallet, dolly, crate, and warehouse icons.
- Stopped the Packing List History page summary from stretching to fill unused modal height; the print-day/snapshot line now stays compact at the top of its content flow.
- Changed Edit Racks to one full-width collapsible set per row and pins Truck first so expanding Wood, Coral, or another set cannot stretch a neighboring grid row.
- Renamed loaded Open rack status to Incomplete in the Rack Overview and added a prominent status indicator for Incomplete, Complete, On the way, Received, and Empty states.
- Advanced `APPLICATION_VERSION` to 307 while preserving SQLite schema version 11. No migration or database reset is included.

## v0.306 - Mobile Scan Workflow and Dialog Repair

- Removed the compact Scan bottom navigation and now present scanner controls, summary, filters, paging, and delivery-list cards in one continuous handheld workflow.
- Added Job Nr., explicit scanned/total quantity, and complete/partial/not-scanned states to mobile delivery-list cards.
- Reworked Scan and Bay Map All Scans tables into labeled mobile audit cards while retaining the desktop tables.
- Corrected blank header icons and constrained the combined Barefoot logo to the mobile navigation drawer.
- Repaired compact Print/Export, preset, admin, bay, and operations dialogs so each owns its scrolling area and remains closable on a phone.
- Constrained Home progress tracks to their card width and allowed expanded Bay Map groups and bay cards to grow to their complete content.

## v0.305 - Unified Mobile Workflow and TC22 Visual Polish

- Added a final `static/css/mobile.css` ownership layer loaded after every page stylesheet, eliminating compact-layout drift from older revision media queries without changing desktop rendering.
- Reworked compact navigation into focused Scan, List, Summary, and Review views; Menu now opens the full application drawer instead of switching to an empty legacy view.
- Prioritized station/date/stage context, transportation or bay destination, barcode entry, manual entry, and scan feedback for one-handed floor operation.
- Reflowed Home, Statistics, Racks, Bay Map, Reject Tracking, Admin, Print / Export, login, and shared dialogs for 760px-and-below screens with a dedicated 430px and short-landscape pass.
- Added safe-area-aware framing, consistent 44px-or-larger controls, contained search and filter overlays, full-screen mobile modal workspaces, and predictable mobile overflow behavior.
- Advanced `APPLICATION_VERSION` to 305 while preserving SQLite schema version 11. No migration or database reset is included.

## v0.304 - TC22 Mobile Workspace and Rush Notification Isolation

- Restricted the full-screen `New Rush Submitted` production-priority alert to genuine `rush` notifications instead of treating every pending application notice as a Rush.
- Kept automated import results, Superseded Order Review, and other administrative notifications in the normal notification center; they no longer enter the Scan-page Rush popup queue.
- Tagged operator-created Rush notifications with `source: operator-priority-work` and added backend/browser automation-identity guards for defense in depth.
- Prevented A+W/source imports from creating operator Rush state by stripping imported `Rush` / standalone `SDI` tokens while preserving audited operator Rush state and source-authoritative Remake markers.
- Added a TC22-first responsive ownership layer for compact widths only. Zebra TC22-class handheld layouts now use a compact two-row header, safe-area-aware bottom navigation, touch-sized controls, and reduced navigation/logo overhead.
- Reworked Home, Scan, Statistics, Racks, Bay Map, Reject Tracking, Admin, and Print / Export at 760px and below, plus an extra-narrow 430px pass for phone-class CSS viewports.
- Made compact Scan controls prioritize barcode entry and one-handed use: Station/Date/Stage reflow cleanly, barcode input is larger, rack/bay/manual controls stack predictably, and update/Rush dialogs stay fully visible above mobile navigation.
- Converted compact control centers and data-heavy pages to single-column or horizontally contained layouts so tables and modal content do not clip outside a handheld viewport.
- Advanced `APPLICATION_VERSION` to 304 while preserving SQLite schema version 11. No migration or database reset is included.

## v0.303 - Delivery Date Recovery and Accurate Import Quantities

- Prevented stale deleted-list metadata from blanking the Scan delivery-date selector after imports, restores, and catalog refreshes.
- Refreshes the newly selected active-list detail whenever an import replaces an inactive or unavailable list.
- Normalized current and historical import summaries against the canonical Staging copy, with Outbound as the fallback, so one physical piece is counted once.
- Separated changed-row labels from piece totals in Delivery List Update Preview and import-history actions.
- Added durable new-date classification so restored lists and new route stages are reported as updates while truly new delivery dates remain New.
- Added isolated SQLite regression tests for Indian Trail-only routing, update quantities, restored stages, foreign keys, integrity checks, and historical stage-copy normalization.
- Advanced `APPLICATION_VERSION` to 303 while preserving SQLite schema version 11.

## v0.302 - Main and Website 2 Integration, Exact Removal History, and Import Review

- Restored five-run pagination in Today's Import Activity while retaining every loaded same-day run across the pager.
- Added separate positive and red negative quantity pills so management totals read like `121 +12 -1 132`, with the no-removal form remaining `121 +12 133`.
- Added durable per-item import snapshots for new, updated, quantity-decreased, and removed A+W-owned rows, including removal notices after the live row is gone.
- Made removed-piece totals flow through stage summaries, import history, selected-run metrics, and preview records instead of being inferred from current rows.
- Based import-level added/removed totals on the canonical full-list stage instead of summing replicated operational stage copies, preventing logical pieces from being double- or triple-counted.
- Reworked Delivery List Update Preview to Route → Glass Type → Order dropdowns with header counts on the right and flat item rows inside each expanded order.
- Removed item-level dropdowns; order-level customer, job, route, and glass/product details are shown once above item number, size, quantity, and before/after changes.
- Kept preview content on the main modal scrollbar rather than route-level vertical scroll areas.
- Added explicit Admin selection of either superseded candidate as the removal target; the original candidate remains a suggestion only.
- Persisted the selected superseded removal order in SQLite migration 11 and mirrored the compatibility column in the Azure schema definition.
- Approved superseded removals now create their own import-history record so red removal totals remain auditable in Today's Import Activity.
- Updated maintained application references and cache keys to v0.302. SQLite schema is now version 11.

## v0.301 - Complete Same-Day Import History and Hierarchical Update Preview

- Canonicalized one automation execution by its shared run start timestamp so the same run no longer appears twice a few seconds apart when database and completion-notification timestamps differ.
- Prevented one notification file result from being reused to identify multiple database imports, preserving distinct same-day runs.
- Removed the five-run browser page from Today's Import Activity and now exposes every loaded run for the current day in the existing horizontal run strip.
- Added immutable `State\RunHistory` JSON summaries for every completed PowerShell run and included those archives in the Automation Control Center history source, preventing later runs from overwriting the only runtime copy.
- Added an explicit shared PowerShell `runId` to scheduled summaries and notifications so future database, runtime, archive, and notification records use the same identity.
- Rebuilt Delivery List Update Preview hierarchy as route → glass type → order → item, with all dropdowns collapsed initially and filter/search-aware path expansion.
- Removed the small route-content vertical scrollbar so the preview uses the main GUI/modal scrollbar as expanded groups grow.
- Updated maintained application references and cache keys to v0.301. SQLite schema remains version 10.

## v0.300 - Import Integrity, Full-List Reconciliation, and Superseded Review Alerts

- Fixed stale automation `ProjectRoot` configuration. The running web app now repairs the installed automation config to its own project root so scheduled/manual SQL imports write to the same scanner database used by the browser.
- Added post-import source coverage verification. Automation can no longer report success when only changed/new rows were imported; every expected A+W row must be present after reconciliation.
- Changed Delivery List Management quantity presentation to arithmetic totals such as `111 +9 120`, using the import event's saved post-import total rather than a potentially unrelated live route total.
- Detail-only item updates no longer inflate the middle quantity cell. The middle value is the signed net piece change.
- Added in-app notification creation for newly pending superseded-order reviews. Source rows remain active until an exact Admin approval is made.
- Strengthened the existing Superseded Order Review red badge and refresh it after new automation results are received.
- Updated maintained application references and cache keys to v0.300. SQLite schema remains version 10.

## v0.299 - Stable Manual Delivery List Expansion

- Removed automatic opening of changed delivery-date groups in Delivery List Management.
- Restored manual expand/collapse control while retaining the complete stage view introduced in v0.298.
- Added stable delivery-group keys and preserved each user's open/closed choices across recent-import and automation-status refreshes.
- Avoided replacing the Delivery List Management DOM when the normalized data markup has not changed, preventing repeated background checks from flashing the section.
- Removed the animated max-height/opacity replay from Delivery List Management stage tables and returned them to native details visibility.
- Preserved Airport Road consolidation, route-accurate preview filtering, historical preview recovery, and existing print/export behavior.
- Updated maintained application references and cache keys to v0.299. SQLite schema remains version 10.

## v0.298 - Complete Stage View, Route-Accurate Preview, and Historical Recovery

- Restored every Delivery List Management stage row for the selected import/date instead of showing changed routes only.
- Collapsed only the duplicate Staging and Outbound rows into one Airport Road row; Indian Trail, Greenville, CPU, DTC, and custom stages remain individually visible with original, change, current, and status information.
- Kept changed delivery dates automatically expanded while unchanged stage rows remain visible as `No Updates`.
- Changed preview classification to use each order snapshot's actual route before using stage/scanner fallback, preventing Greenville orders from appearing in the Airport Road preview group.
- Routed standard route preview buttons through the authoritative Airport Outbound list and applied an exact route-group filter in the browser, eliminating stale CPU stage IDs and duplicate cross-stage snapshots.
- Added historical list metadata fallback so retired or missing stage records can still return their saved change snapshots instead of `Delivery list was not found`.
- Supplemented newly-created stage previews from the current item catalog when older notice batches retained fewer snapshots than the recorded changed-line count.
- Preserved the delivery-date header preview as the all-route view and preserved exact Print / Export route selection.
- Updated maintained application references and cache keys to v0.298. SQLite schema remains version 10.

## v0.297 - Route-First Delivery Management and Exact Route Printing

- Replaced Staging and Outbound rows in Delivery List Management with one Airport Road route row and retained Indian Trail, Greenville, CPU, and DTC as the remaining route rows.
- Limited each changed delivery-date expansion to routes actually changed by that import and automatically opened delivery dates that contain changes.
- Reserved New management status for a newly-created delivery list or route; existing routes remain Updated even when they contain newly-added orders.
- Classified every retained order in a newly-created route as New in Delivery List Update Preview while preserving explicit Removed order snapshots.
- Removed nested stage wrappers from the preview so route dropdowns open directly to changed orders, item details, and before/after values.
- Chose one representative preview stage per route, with Outbound preferred for Airport Road, preventing duplicate Staging/Outbound order cards.
- Routed all management print actions through the Airport Outbound source list and preselected the exact Airport Road, Indian Trail, Greenville, CPU, or DTC filter in Print / Export.
- Kept the delivery-date header print action on Airport Road, representing the complete outbound delivery list across all routes.
- Corrected preview eye buttons to the same 34-by-34 square footprint as print buttons.
- Updated maintained application references and cache keys to v0.297. SQLite schema remains version 10.

## v0.296 - Cross-Stage Preview Access and Durable Daily Import History

- Fixed Delivery List Update Preview returning `Permission denied for this delivery-list stage` to Admin/Supervisor and fully authorized Delivery List Management users when the changed run included stages outside their ordinary scanner assignment.
- Preserved every already-loaded same-day import while the newest manual or automated run is refreshed from durable history.
- Changed live import snapshots from replace behavior to stable-key merge behavior and immediately refreshes complete current-day audit history after each run.
- Prevented identical-result imports with different stable run IDs from being collapsed as duplicates merely because they occurred close together.
- Reorganized the update-preview GUI into initially collapsed Airport, Indian Trail, Greenville, CPU, and DTC workflow groups.
- Added exact stage sections, location-level New/Updated/Removed badges, compact totals, and filter-aware expansion while retaining detailed order, item, customer, job, product, dimensions, route, and before/after values.
- Updated maintained application references and cache keys to v0.296. SQLite schema remains version 10.

## v0.295 - Targeted SQL Import Scope Repair

- Fixed the automated importer failure `name 'args' is not defined` that occurred only when a delivery date required an authoritative scanner import.
- Added explicit `run_id` and `run_started_at` parameters to `selective_sql_sync` and passed them from `main()` into the maintained import call.
- Preserved stable run identity in durable import history and notifications without referencing `main()` local variables from a module-level helper.
- Confirmed unchanged dates continue to skip redundant writes while changed/new dates can import normally.
- Updated maintained application references and cache keys to v0.295. SQLite schema remains version 10.

## v0.294 - Import History Dates, Preview Reliability, and Change Totals

- Corrected the Delivery List Management Selected Run layout so its summary and metrics remain compact and aligned instead of stacking into a tall empty panel.
- Changed the stage Changes cell to show updated pieces and removed pieces independently, including both values when a run contains additions/updates and removals.
- Limited update-preview buttons to stages with current new, updated, or removed rows.
- Fixed the legacy update-preview fallback's undefined row helper and added explicit API error responses, eliminating the opaque `Failed to fetch` failure.
- Made multi-stage previews tolerant of one failed stage while preserving the successfully loaded stage details.
- Rebuilt Automation Control Center import-history grouping around raw timestamps and stable run IDs, preventing shortened timestamps from being interpreted as year 2001.
- Added full-year visible timestamps and polished day, run, metric, status, and file-result cards in Automation Control Center.
- Preserved new-piece and updated-piece totals through import normalization, durable change summaries, API history, and browser signatures.
- Updated maintained application references and cache keys to v0.294. SQLite schema remains version 10.

## v0.293 - Complete Daily Import History and Item-Level Change Preview

- Added stable run IDs across the automation runner, importer, import audit records, notifications, and browser so one automation run has one identity everywhere.
- Stopped Delivery List Management from collapsing repeated same-day imports by delivery date/source name and from duplicating the newest runtime result beside its durable database record.
- Loads every available current-day result across the paginated audit history, retains every run, and paginates the Recent Imports tabs without a 100-run cutoff.
- Removed the second per-run date-only de-duplication layer so every legitimate file result in the selected run remains visible.
- Added a polished daily activity heading, run/file totals, selected-run metrics, clearer tabs, and improved responsive presentation.
- Rebuilt Delivery List Update Preview with concise copy, All/New/Updated/Removed filters, order/item search, prominent order details, and compact item cards.
- Added durable previous-value snapshots and changed-field lists so updated rows can show exact before/after values in the preview.
- Updated maintained application references and cache keys to v0.293. SQLite schema remains version 10.

## v0.292 - Review Queue Installation Repair and Simplified Active Totals

- Reissued the complete Superseded Order Review implementation, including `backend/store.py`, API routes, schema support, browser assets, and automation files, so partial overlays cannot leave the importer without `sync_superseded_order_candidates`.
- Added a precise runtime diagnostic with the loaded store-module path when an incomplete installation is detected.
- Corrected automation logging so a failed advisory review sync is not also reported as a successful sync.
- Simplified Delivery List Management quantity cells and date summaries to one active value such as `129 pcs`; removed duplicate `A+W pcs` and `active total` wording.
- Replaced misleading ownership-breakdown logging with a single active total when unchanged-stage verification does not return source/manual counters.
- Preserved successful scanner imports, exact-key approvals, Keep Both, Review Later, manual protection, and SQLite schema version 10.
- Updated maintained application references and cache keys to v0.292.

## v0.291 - Automatic Import Result and Notification Recovery

- Fixed the Windows PowerShell 5.1 `Argument types do not match` failure caused by serializing generic list objects directly in notification and last-run payloads.
- The runner now reads a normalized import result even when Python returns a nonzero exit for one failed workbook, allowing successful dates to remain successful and failed dates to be reported individually.
- Superseded Order Review queue persistence is now advisory and cannot abort delivery-list imports; failures are retained as warnings with a traceback in the result file.
- Failure notifications can no longer mask the original automation exception. Full error details are also written to `State\last-error.txt`.
- Increased the selective-sync request JSON depth so complete candidate item evidence is preserved.
- Updated maintained application references and cache keys to v0.291. SQLite schema remains version 10.

## v0.290 - Local Superseded Order Review and Exact-Key Approval

- Removed production status as an automatic delivery-list membership decision. Status values are evidence only.
- Added local candidate detection using shared A+W Header Identity (`AH_IDENT`), older order status 410/item status 0/no production batch, a newer active-batch order, and matching job/item evidence.
- Added the Delivery List Management **Superseded Order Review** workspace with side-by-side item comparison, live scanner impact, and explicit Approve / Keep Both / Review Later actions.
- Added SQLite migration 10 and Azure SQL compatibility for durable candidate evidence, decisions, fingerprints, and audit metadata.
- Approval removes only exact A+W-owned delivery-date/order/item keys, preserves protected manual entries, creates removed-line preview snapshots, updates stage revisions, and records audit/history entries.
- Added `data/superseded-source-exclusions.json`, generated atomically from approved reviews and merged into the SQL exporter with the existing historical exact exclusions. Non-approved review decisions publish preservation overrides so Keep Both, Review Later, or changed evidence can restore an older bootstrap-excluded row.
- Candidate decisions remain stable while evidence is unchanged; materially changed evidence returns the candidate to pending review.
- Updated maintained application references and cache keys to v0.290.

## v0.289 - Raw Date Restore and Schedule-Membership Investigation

- Removed the unsafe universal `460` order/item status and production-batch eligibility filter that was excluding valid future, internal-reject, and not-yet-cut delivery-list rows.
- Restored every raw A+W row matching the planned delivery date, with production statuses retained only as diagnostics.
- Added a maintained exact-exclusion file for the eight 8/3/2026 order/item rows directly verified absent from Crystal, avoiding job-number or dimensional duplicate guesses.
- Paused unverified automatic source-row removals while continuing additions, updates, remake changes, route changes, and unprotected manual-duplicate retirement.
- Allowed exact Crystal-verified exclusions to retire known obsolete rows while the general removal pause is active.
- Updated selective SQL drift checks so retained unverified source rows do not trigger endless re-import loops.
- Added a SELECT-only A+W schedule-membership probe covering `POOL_TEILE`, header `LADELISTE`, `BW_LADELISTE`, and `TEMP_DELIV`.
- Added the verified-exclusion file to startup/runtime synchronization under `C:\DeliveryListAutomation\Scripts`.
- Preserved protected manual orders and SQLite schema version 9; no database migration is required.
- Updated maintained application references and cache keys to v0.289.

## v0.288 - Date-Scoped Eligibility Safety Deferral

- Fixed a future/incomplete delivery date exceeding `MaxExcludedPercent` aborting the entire automatic Incremental or Full window before already-safe dates could be imported.
- Changed the A+W eligibility safety guard to defer only the suspicious delivery date, preserving its existing workbook and scanner rows without publishing a partial source set.
- Continues processing and importing every safe delivery date in the same run.
- Added `safetyDeferredDates` and detailed raw/eligible/excluded percentage diagnostics to the persisted run summary and app-notification payload.
- Added warning completion and notification wording so a protected deferral is visible without being reported as a total automation failure.
- Preserved the verified status/item/batch eligibility rule, protected manual orders, retained change previews, and SQLite schema version 9.
- Updated maintained application references and cache keys to v0.288.

## v0.287 - Live Active Totals, Manual-Row Diagnostics, and Retained Change Preview

- Fixed Delivery List Management so current quantities come from the live active scanner stages rather than stale automation-history summaries.
- Added A+W-owned, manual, protected-manual, and total-active quantity breakdowns to list summaries, stage results, and the automation log.
- Kept no-change result list IDs separate from changed list IDs so a verification run remains correctly classified.
- Kept the eye preview available after a later No Changes run by using retained notice/import-history snapshots independently of the selected run classification.
- Forced the selected Scan page to reload when catalog totals, revisions, matching import results, browser focus, or visibility indicate stale detail.
- Added live item/remake totals to delivery-list detail responses so the browser can verify rendered Scan rows against the database response.
- Updated the Remakes badge to distinguish A+W remake pieces from preserved manual remake pieces when both are present.
- Preserved SQLite schema version 9; no database migration is required.

## v0.286 - Active Scan Refresh and Complete Change Preview

- Fixed the Scan page retaining stale pre-import line items after an external SQL import updated the database and Delivery List Management catalog.
- Added delivery-list revision awareness to browser catalog caching and automatic active-list detail reloads when revision, item count, or total quantity changes.
- Added durable per-stage `changeItems` snapshots for New, Updated, and Removed rows inside import history without changing the database schema.
- Updated the Delivery List Update Preview endpoint to merge normal notice snapshots with import-history snapshots and report the expected changed-line count.
- Added a visible legacy-history warning when an older import summary contains more changed lines than available item snapshots and clarified that a no-change rerun cannot reconstruct missing historical rows.
- Replaced numeric preview-button badges with a guaranteed inline eye icon while preserving detailed accessible labels and tooltips.
- Fixed the A+W eligibility summary log format so raw, eligible, excluded, and remake counts replace all PowerShell placeholders.
- Updated maintained application references and cache keys to v0.286. SQLite schema version 9 is unchanged.

## v0.285 - PowerShell Eligibility Log Parser Repair

- Fixed the SQL automation runner failing at parse time before any A+W query because a colon immediately followed `$dateKey` inside a double-quoted PowerShell string.
- Replaced the unsafe interpolation with the PowerShell format operator so excluded-row diagnostics remain readable without being parsed as a scoped variable reference.
- Added a regression assertion preventing direct `$variable:` interpolation from returning to the maintained runner.
- Retained manual/scheduled run isolation, A+W report-eligibility filtering, protected manual orders, and SQLite schema version 9.
- Updated maintained application references and cache keys to v0.285.

## v0.284 - Manual and Scheduled Automation Run Isolation

- Fixed a one-date browser request appearing as `Incremental` / `Configured` and showing a multi-day scheduled-task log when the two runs overlapped.
- Added a dedicated browser-run summary file and request ID so the web controller never reads a scheduled run's shared `last-run.json` as the manual result.
- Added a pre-launch shared-lock check with a clear message when Task Scheduler is already running the delivery-list automation.
- Added a PowerShell `FailIfBusy` path to close the race where a scheduled task starts after the browser's lock check.
- Prevented a skipped overlapping scheduled task from overwriting the active run summary.
- Refreshes maintained automation runtime files when the web app starts, ensuring scheduled tasks use the current exporter and A+W eligibility rules after an update.
- Expanded Status & Logs to distinguish manual requests from scheduled tasks and display the actual date/range mode.
- Retained A+W report eligibility, protected manual orders, and SQLite schema version 9.
- Updated maintained application references and cache keys to v0.284.

## v0.283 - SQLite Migration Registry Startup Repair

- Fixed scanner startup failing with `Database did not reach the expected schema version` when the application contract expected schema 9 but the deployed changed-files overlay did not include the migration-9 registry.
- Added the complete maintained `database/migrations.py` to the repair package so schema contract and numbered migration definitions are deployed together.
- Added a preflight check requiring a continuous migration definition set from version 1 through `CURRENT_SCHEMA_VERSION` before any migration work begins.
- Made the final schema check report installed, defined, missing, unexpected, and expected versions instead of a generic mismatch.
- Confirmed migration 9 remains idempotent when `protect_from_aw_import` columns already exist but the migration ledger is still at version 8.
- Retained the v0.282 A+W report-eligibility query and removal behavior without changing SQLite schema version 9.
- Updated maintained application references and cache keys to v0.283.

## v0.282 - A+W Report Eligibility and Removed Scheduling Rows

- Confirmed the 8/3/2026 remake mismatch originates before scanner import: the raw delivery-date SQL set retained eight old remake item rows after their orders were removed from active scheduling.
- Added source eligibility checks for A+W order status, item status, and header production-batch membership before workbook creation.
- Uses verified defaults of order status `460`, item status `460`, and at least one active `LAUF_PROD1` / `LAUF_PROD2` / `LAUF_PROD3` value; these settings remain overrideable through `SourceMapping.DeliveryEligibility`.
- Excludes the verified obsolete pattern (`STATUS=410`, `POS_STATUS=0`, no production batch) without comparing or collapsing different order numbers that happen to share the same job, dimensions, customer, or product.
- Added raw-versus-eligible line and remake totals plus per-row exclusion diagnostics to the SQL automation log.
- Added a configurable maximum excluded-row percentage so a suspicious source-status change fails closed instead of publishing a mass-removal workbook.
- Added the eligibility-rule signature to the source hash, forcing the first v0.282 run to rebuild and import the corrected workbook even when the underlying A+W rows are unchanged.
- Retained protected manual-order behavior, authoritative order/item reconciliation, and history-safe removed-line handling.
- Updated maintained version references and cache keys to v0.282. SQLite schema version 9 is unchanged.

## v0.281 - Protected Manual Orders and Remake Source Diagnostics

- Added an operator-controlled **Protect from A+W import** option to manual-order creation; it is enabled by default for safer manual workflow entries.
- Added the same protection toggle to the manual line-item editor so authorized users can change the protection state across all workflow-stage copies.
- Added SQLite migration 9 and Azure SQL compatibility columns for `protect_from_aw_import` on line items and manual-entry audit records.
- Authoritative reconciliation now keeps protected manual rows independent even when A+W later publishes the same order/item. Unprotected duplicates continue to be retired.
- SQL drift checks ignore intentional protected manual duplicates while continuing to detect unprotected duplicates.
- Fixed authoritative imports preserving stale source-provided `Remake`/`RM` labels after A+W removed the remake flag.
- Preserved only operator-managed Rush/Remake Priority Work labels whose latest audit action is still active.
- Expanded SQL exporter remake diagnostics to log separate remake line and unique-order counts plus the exact order/item rows and raw A+W header flag values classified as remakes. This makes Crystal-vs-SQL differences directly auditable.
- Updated maintained version references and cache keys to v0.281.

## v0.280 - Authoritative Manual Duplicate Retirement

- Fixed authoritative A+W reconciliation leaving a manual/test duplicate active when the same order and item already existed as a source-owned A+W line.
- Preserves manual-only work only when its order/item is absent from the incoming A+W stage; colliding manual copies are now retired as removed lines.
- Added duplicate-manual line and piece counters to stage summaries, normalized automation results, Delivery List Management history data, and live completion logs.
- Updated scheduled scanner drift detection so a manual row that duplicates an expected A+W order/item forces reconciliation instead of being ignored.
- Added a regression test covering one authoritative source row, one duplicate manual row, and one unrelated manual-only row.
- Updated the visible application version, cache keys, documentation, application contract, and focused tests to v0.280. SQLite schema version 8 is unchanged.

## v0.279 - Runtime Import Schema Guard and Single-Source Reconciliation

- Added an import-time SQLite schema guard that repairs `line_update_notices` before any new, updated, or removed preview notice is written, including automation configurations where `Import.InitializeStore` is disabled.
- Preserves existing notice IDs and `line_update_receipts` while rebuilding the canonical `snapshot_json` and `removed`-change schema.
- Added SQLite schema migration 8 so normal scanner startup records and verifies the same canonical notice-table repair.
- Changed SQL authoritative reconciliation to import the one selected canonical generated workbook directly instead of invoking a whole-folder import that could process both `8.3.26.xlsx` and `Delivery List 08-03-2026.xlsx`.
- Changed Folder Import Only to select and import one deterministic workbook per delivery date from the standalone automation importer.
- Added `schemaRepairApplied` to normalized results and console summaries for direct troubleshooting.
- Updated the visible application version, cache keys, documentation, contract, migration history, and focused tests to v0.279 / SQLite schema version 8.

## v0.278 - Import Notice Schema Recovery

- Added SQLite schema migration 7 to repair databases that recorded the v0.275 migration while still retaining the older `line_update_notices` table without `snapshot_json` or `removed` notice support.
- Rebuilds delivery-list update notices and receipts transactionally while preserving existing notice IDs, review receipts, source hashes, timestamps, and valid snapshots.
- Changed folder-import results to fail whenever any candidate workbook fails instead of returning `ok: true` because unrelated files were skipped.
- Added one-source-per-delivery-date protection for Folder Import Only. When duplicate workbooks exist for the same date, the newest modified workbook is imported and the older duplicate is reported as ignored instead of being applied afterward.
- Updated the SQL automation result normalizer so failed workbook rows cannot be surfaced as a successful import.
- Updated the visible application version, cache keys, documentation, application contract, migration history, and focused tests to v0.278 / SQLite schema version 7.

## v0.277 - Manual Automation Startup and Live Log Repair

- Reverted browser-started automation to the installed `C:\DeliveryListAutomation\Scripts` runtime directory so the PowerShell runner and all adjacent helper scripts execute from one consistent location.
- Added an explicit, atomic runtime synchronization step for `Run-DeliveryListSqlAutomation.ps1`, `import_delivery_folder.py`, and `delivery_import_safety.py` before each manual GUI run.
- Added a caller-supplied per-run PowerShell log path and initialized it before configuration loading, preventing startup failures from leaving Status & Logs at zero lines with no recorded log.
- Added an immediate `PowerShell automation runner accepted the request.` startup record, plus `-NoLogo` and `-NonInteractive` process flags.
- Added runner-path and synchronized-file diagnostics to the live automation status while retaining complete-log polling and v0.276 authoritative A+W reconciliation.
- Updated the visible application version, cache keys, documentation, application contract, and focused tests to v0.277. SQLite schema version 6 is unchanged.

## v0.276 - Authoritative SQL Reconciliation Repair

- Fixed browser-started Custom SQL Export & Import runs so every selected A+W delivery date is force-reconciled even when the generated workbook and exporter state hash are unchanged.
- Changed the automation controller to prefer the maintained project PowerShell runner for manual GUI runs, preventing an older installed runtime copy from bypassing newly deployed reconciliation fixes.
- Added read-only source-row drift detection to scheduled SQL synchronization, comparing every generated stage and source-owned business row instead of treating existing stage IDs as proof of synchronization.
- Added detection for scanner-only rows, removed A+W rows, quantity/detail differences, missing expected stages, and obsolete optional/custom route stages.
- Reconciled fully removed optional/custom route stages against an empty source set so their removed lines appear in import history and update preview before the stage is retired.
- Preserved manual-only rows when a source stage disappears; a stage remains active when manual work is still present.
- Retained historical Delivery List Update Preview snapshots for 365 days while keeping current/future-only unseen-update indicators on the scanning workflow.
- Updated the visible application version, cache keys, documentation, application contract, and focused tests to v0.276. SQLite schema version 6 is unchanged.

## v0.275 - Authoritative A+W Removals and Update Preview

- Made the newest A+W delivery list authoritative for source-owned rows in every imported stage, including imports where the only change is one or more removed items.
- Added history-safe removal handling: unreferenced rows are deleted, while rows referenced by immutable scan, machine, rack, or bay history are soft-deleted and excluded from all active delivery-list workflows.
- Retired active rack assignments as `Removed` and active bay assignments as `Cancelled` when their source line disappears, preserving the historical assignment records and preventing ghost work from remaining active.
- Preserved manually created delivery-list rows unless an incoming source row takes ownership of the same order/item.
- Added schema migration 6 to allow `removed` line-update notices and retain a JSON display snapshot after the active line item has been deleted.
- Added removed line and piece totals to import results, normalized SQL automation results, Delivery List Management summaries, stage summaries, and removal-only update classification.
- Changed Delivery List Management quantity presentation to show removal-only updates as `-N pcs` and mixed updates as distinct added and removed quantities.
- Added a Preview Changes button to every changed stage row, immediately before Print / Export, while retaining the delivery-date-level Preview Changes button.
- Rebuilt Delivery List Update Preview with New, Updated, and Removed groups, stage/date metrics, retained-snapshot guidance, and responsive polished item cards.
- Applied the maintained safe reconciliation wrapper to both SQL and Crystal automatic importer entry points.
- Excluded soft-deleted source rows from active list totals, scanning and cross-date matching, global/admin search, reports, reject matching, rack/bay and Indian Trail workflows, print packages, edit lookups, and administration counts.
- Advanced the application contract, visible version, browser cache keys, documentation, database contract, migration history, and focused structure tests to v0.275 / schema version 6.

## v0.274 - Compact Polished Create Preset Workspace

- Reduced the desktop Create Preset control center from a near-full-screen window to a centered 1240 × 780 maximum while retaining safe responsive sizing at 1024px and mobile widths.
- Increased the typography for preset labels, descriptions, input values, filter choices, selection totals, live summary values, and action buttons.
- Added final v0.274 modal ownership so the smaller centered geometry does not conflict with the v0.228 viewport repair or older modal transforms.
- Reused the maintained Print / Export route, status, attention, All-choice, Mirror, Tempered, and Annealed gradient palettes inside Create Preset.
- Added card accent rails, layered panel gradients, polished controls, and a subtle workspace grid so Create Preset and Print / Export read as one product.
- Preserved internal scrolling, responsive stacking, Lookup Manager glass types, live summary, personal-default selection, and all existing save/apply behavior.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.274. Schema version 5 is unchanged.

## v0.273 - Packing Snapshot Layout and Bay Edit Shortcut

- Replaced the tall Packing List History page summary with a single compact status line that reports the visible print-day range and snapshot count without pushing weekly groups down the modal.
- Kept Preview and Print Snapshot side-by-side on each historical packing-list row, including protection against shared button rules that would otherwise stretch them vertically.
- Raised the in-app snapshot preview above the Operations/Packing List History GUI with an explicit top-level stacking layer.
- Removed the redundant footer Close button from Snapshot Preview; the top-right X, Escape key, and backdrop continue to close the preview.
- Changed the existing Glass Cart rack-set visual to an A-frame glass cart silhouette without changing the persisted icon key.
- Reintroduced a deliberately tiny physical Bay Map group pencil in the top-right. It opens the exact group in the maintained Edit Bays GUI and leaves Edit Bays as the single editing workflow.
- Advanced application revision to 273 while retaining database schema version 5; no migration is included.

## v0.272 - Rack Manager Collapse and Packing Snapshot History

- Anchors shared standalone-popup X controls in the top-right, including rack delete/confirmation dialogs.
- Makes every Edit Racks rack set initially collapsed with a clear View racks / Hide racks affordance while preserving expansion state during the open manager session.
- Keeps rack-set visual-identity icons fully contained inside their tiles and adds Glass cart, Pallet, Dolly, Crate, and Warehouse icon choices.
- Rebuilds Packing List History into initially collapsed Monday-Friday business-week groups.
- Limits Packing List History to 25 distinct print days per page and keeps the Operations modal body as the single vertical scroll owner so historical content is not clipped inside nested panes.
- Adds Preview and Print Snapshot actions for every historical packing-list record; Preview displays the exact saved packing-list HTML without triggering the browser print dialog.
- Keeps database schema version 5; this release does not add a migration.

## v0.271 - Rack Visual Selection and Delete Reliability

- Reworked Add Rack Set visual identity controls so icon tiles use neutral white surfaces and the selected rack-set color is applied to the icon itself instead of hiding every icon inside a blue button.
- Added a quick color-swatch palette plus the native custom color picker; choosing either updates the icon library and live set preview immediately.
- Applied the maintained shared blue `app-primary-button` format to Cancel in both Add Rack Set and Add Individual Rack workflows.
- Removed the redundant Rack Configuration hero/subsection from both rack creation workflows; the modal title, numbered sections, and live preview now carry the hierarchy without repeating the same introduction.
- Made empty-rack deletion predictable: a deleted/reused rack code can be created cleanly, stale zero-quantity rack-item rows no longer block deletion, and the rack form returns to Edit Racks after a successful delete.
- Made rack-set deletion all-or-nothing from the UI: the set trash action is enabled only when every rack in that set is empty, then removes the full set and its orphaned visual metadata while preserving rack/audit history.
- Prevented Add Rack Set from silently overwriting active rack codes. Conflicting generated codes now produce a clear error so a supposedly new set cannot accidentally adopt an existing rack's contents/lifecycle.
- Removed the internal vertical scrollbar from grouped rack sets in Edit Racks; all racks in each group are laid out and the main Admin modal owns scrolling.
- Removed the grouped-set pencil from the physical Bay Map. Bay editing remains available through the maintained Edit Bays workflow.
- Application revision is 271. Database schema remains version 5; no migration was added.

## v0.270 - Guided Rack Creation Workspaces

- Rebuilt the **Add Individual Rack** GUI into a polished Rack Manager form with clearly grouped rack identity and rack-set fields, helper copy, and a live visual preview.
- Rebuilt the **Add Rack Set** GUI into Set Identity, Numbering, and Visual Identity sections with a live preview of generated rack codes and rack count.
- Preserved the existing rack-set icon/color library and reused it in the new creation preview rather than creating a second visual system.
- Individual-rack creation now lists the rack sets that actually exist in the maintained Rack Manager, including custom sets.
- Added a top **Edit Racks** return control and footer **Cancel** button to both creation screens. Both return to the Rack Manager without closing the Admin workspace.
- Saving an individual rack or creating a rack set now returns to **Edit Racks** automatically so users can immediately see and continue managing the result.
- Kept all rack APIs and persistence behavior unchanged.
- Advanced `APPLICATION_VERSION` to 270 while preserving `CURRENT_SCHEMA_VERSION = 5`; no migration, database reset, or schema change is included.

## v0.269 - Scan Update Clarity, Rack Transport History, and Rack Set Visuals

- Reworded Scan-page review messaging so it says **New stage** when a stage is newly introduced and **Delivery list updated** / **new orders** when an existing list receives added orders. Removed the misleading "updated orders" phrasing from the Scan review prompt/header and changed the Scan attention label to **New Orders**.
- Made the Scan review header bar harder to overlook with a stronger accent, visible REVIEW / NEW STAGE / NEW ORDERS badge, and concise review copy.
- Increased the Scan review notification duration to exactly 10 seconds and synchronized its countdown/progress animation to the same duration.
- Preserved the most recent rack assignment after rack contents are cleared or scanned out. Scan-table Location now shows that former rack in a muted gray prior-history style unless a current rack, bay, or received state supersedes it.
- Standardized the shared blue primary-button component to a 13px font and a 38px minimum height, and applied it to the Manual Scan Submit button.
- Added a rack-set visual library with selectable icons and color input for new/existing rack sets. Rack-set visuals are persisted in existing `system_metadata` and reused on Rack Overview and Rack Manager group headers.
- Added a 20-second Old Bay review notification countdown/progress timer.
- Preserved `CURRENT_SCHEMA_VERSION = 5` and advanced only `APPLICATION_VERSION` to 269. No migration or database reset is included.

## v0.268 - Compact Stage Selector and Bay Edit Icon Polish

- Reduced the Scan-panel Stage selector and popup from the oversized v0.267 footprint while preserving full Indian Trail readability.
- Reserved explicit right-side space for the Stage review marker and arrow instead of letting them overlap the selected stage text.
- Locked selected and menu-row New/Updated `!` markers to a true 18px circle so shared dropdown sizing cannot stretch them into an oval.
- Preserved the wider Delivery Date menu used for complete business-week range headers.
- Reduced the grouped Bay Map edit-pencil artwork by roughly 25% without reducing the existing click target or changing its top-right placement.
- Preserved `CURRENT_SCHEMA_VERSION = 5` and advanced only `APPLICATION_VERSION` to 268. No migration or database change is included.

## v0.267 - Scan Selector Alignment and Delivery Week Readability

- Fixed the Stage dropdown selected-row layout so the checkmark, optional update `!`, and stage label stay on one horizontal row.
- Increased the selected Stage footprint and stopped the update marker from consuming extra text padding, preventing marked stages from looking compressed.
- Kept Stage popup width equal to its trigger while allowing the Delivery Date popup to open slightly wider for complete business-week headers.
- Changed business-week range copy to the explicit `M/D/YYYY - M/D/YYYY` format requested for This Week, Last Week, Next Week, and older week groups.
- Preserved `CURRENT_SCHEMA_VERSION = 5` and advanced only `APPLICATION_VERSION` to 267. No migration or database change is included.

## v0.266 - Update Review Synchronization and Scan Selector Polish

- Changed per-user New/Updated flags to use only the newest update batch for each delivery-list stage, preventing superseded historical notices from disagreeing with the rows that are actually New/Updated now.
- Made Staging and Outbound authoritative review scopes: marking either stage reviewed acknowledges that same current update batch across all active route/stage copies for the delivery date.
- Kept Indian Trail, CPU, DTC, and Greenville review isolated to the selected stage so route-specific review never clears unrelated routes.
- Preserved occurrence-bound safety so a newer update that arrives while a user is reviewing cannot be cleared by the earlier review action.
- Reduced the New/Updated review prompt from 15 seconds to 7.5 seconds, including the visible countdown/progress timing.
- Constrained Scan Date/Stage custom-select popup menus to their trigger width so review indicators cannot create oversized Stage dropdowns.
- Increased Station, Stage, and Delivery Date value typography slightly and expanded their selector footprint so Indian Trail and marked dates remain fully legible.
- Advanced `APPLICATION_VERSION` to 266 while preserving `CURRENT_SCHEMA_VERSION = 5`; no migration, database reset, or schema-contract change is included.

## v0.265 - Scan Stage Review Scope and Bay Group Header Polish

- Expanded the Scan panel context selector layout so the full Indian Trail stage label remains visible and delivery dates retain readable text when a review `!` marker is present.
- Positioned update indicators independently from selected-value text and the dropdown arrow so the indicator no longer consumes label width or creates clipping inside the compact scanner header.
- Added the same per-user `!` review indicator to Stage options that already exists on delivery dates.
- Changed delivery-date marker aggregation to de-duplicate the same delivery-date/order/item across stage copies while retaining exact per-stage pending counts for the Stage selector.
- Added order-aware Airport Rd review propagation: marking Staging or Outbound updates reviewed acknowledges the exact reviewed change-token/order/item notices across every active stage copy of those items for that user.
- Kept Indian Trail, CPU, DTC, and Greenville reviews stage-specific so reviewing one route cannot clear pending updates on another route.
- Preserved per-user review ownership through `line_update_receipts`; one user's review does not clear another user's date or stage indicators.
- Invalidated all affected client-side update caches after an Airport Rd review so downstream Stage selector markers refresh immediately from the authoritative backend state.
- Moved the Bay Map grouped-set Edit icon from the bottom-right to the top-right of each physical bay group header while preserving the existing Edit Bays workflow and permissions.
- Advanced `APPLICATION_VERSION` to 265 while preserving `CURRENT_SCHEMA_VERSION = 5`; no migration, database reset, or schema-contract change is included.

## v0.264 - Statistics Chart Visibility and Scan Review Polish

- Removed the internal vertical scrollbar from the main Statistics table so the default Top 10 view stays in normal page flow; wide accountability tables retain horizontal scrolling only when required.
- Reduced table spacing slightly without shrinking the restored v0.263 typography.
- Updated bar-chart geometry to reserve left-side space from the longest visible category and render the full category label instead of truncating it.
- Added adaptive donut-center sizing so long totals and currency values remain fully inside the center and do not overlap the ring.
- Expanded usable text space in the Scan panel date/stage selectors while preserving the compact centered header layout and right-side dropdown arrow.
- Replaced the Review Updates full-panel jump with a controlled maximum 120px downward nudge that keeps the Mark Reviewed control visible while exposing highlighted rows.
- Advanced `APPLICATION_VERSION` to 264 while keeping `CURRENT_SCHEMA_VERSION = 5`; no database migration, reset, or schema-contract change is included.

## v0.263 - Statistics Readability and Breakage Table Hierarchy

- Restored chart/control/table typography that had been reduced too aggressively during the dense Statistics pass.
- Returned main chart titles, filter inputs, axis/category labels, donut values, legends, KPI text, table text, and selected-row details to a normal readable scale.
- Kept compact chart geometry where useful while increasing legend/table breathing room to prevent the larger text from feeling crowded.
- Reorganized machine and glass breakage tables around six clear columns instead of nine narrow columns.
- Added a grouped Breakage totals block showing Pieces, SQFT, Cost, and Rejects together for each machine/glass row.
- Replaced compressed inline glass/machine/reason summaries with stacked readable detail rows and explicit additional-detail indicators.
- Added clear Complete / unpriced / missing-dimension coverage pills.
- Reworked Reject reasons by machine so frequency is visually prominent and separate from material-impact totals.
- Added a contextual breakage-table heading that explains the view and current chart-ranking unit.
- Preserved custom dates, external-remake logic, chart unit switching, drilldowns, PDF output, Top 10 / Show more data, and all existing breakage calculations.
- Kept `CURRENT_SCHEMA_VERSION = 5` unchanged and advanced only `APPLICATION_VERSION` to 263. No database migration is included.

## v0.262 - Combined Breakage Accountability and Custom Statistics Range

- Combined machine breakage piece, SQFT, and cost datasets into one machine accountability view with a live Chart Unit selector.
- Combined glass-type breakage piece, SQFT, and cost datasets into one glass accountability view while retaining all three measures in table and selection details.
- Added reject-reason aggregation by machine, including occurrence count, rejected pieces, rejected SQFT, estimated material cost, and affected glass types.
- Added machine drilldowns for reject reasons and glass types, plus glass-type drilldowns for machines and reject reasons.
- Added a Statistics custom date-range picker using the maintained Print / Export two-month calendar classes and range-selection interaction.
- Made the custom Statistics range authoritative for both delivery-list filtering and the `/api/reports/summary` request until the user selects a preset range.
- Restricted and restyled the External remakes control so it appears only for breakage comparisons where external remake inclusion changes the result.
- Expanded combined breakage table layouts and kept the main chart single-measure so SQFT, pieces, cost, glass, machines, and reasons remain readable instead of competing on one visual scale.
- Updated the Statistics PDF breakage tables with reject counts, glass context, and top reject reasons.
- Kept `CURRENT_SCHEMA_VERSION = 5` unchanged and advanced only `APPLICATION_VERSION` to 262. No database migration is included.

## v0.261 - Admin-Managed Glass Material Costs

- Added **Glass costs** as a dedicated Lookup Manager library alongside Products, Routes, and Process states.
- Exposed every default per-SQFT glass rate in the admin UI and made existing rates editable without touching application code.
- Added discovered, currently unpriced product types to the Glass Costs library so administrators can price newly introduced glass as soon as it appears in imported data.
- Persisted glass-cost overrides in the existing `admin_lookup_values` table using the `glass_cost` lookup type, keeping schema version 5 unchanged.
- Updated Statistics breakage-cost calculations and PDF inputs to consume the effective default-plus-admin pricing map.
- Kept built-in rates as safe fallbacks, while manual overrides take precedence immediately after save.
- Added glass-cost validation, audit payloads, source/coverage messaging, and English/Spanish Lookup Manager copy.
- Updated Admin overview copy and v0.261 cache/version references.
- Added focused regression coverage for the new lookup bucket, glass-cost editor, persisted override path, effective Statistics pricing, and unchanged database schema contract.

## v0.260 - Compact Glass-First Statistics and Breakage Analytics

- Reduced the main Statistics chart/table presentation by roughly 35% through tighter row geometry, smaller chart canvases, compact legends, and denser table typography while preserving interactive selection and accessibility.
- Changed the initial Statistics presentation to **Glass type quantity** in the donut/circle view and changed the default display limit to 10.
- Added a bottom **Show more data** action that advances the display limit through larger result sets so long datasets do not overwhelm the first view.
- Shortened Statistics workflow labels to Staging, Outbound, Inbound, CPU, Greenville, and DTC so stage names remain fully visible inside the main chart.
- Added reporting calculations for internal rejects by machine/location and by glass type, including rejected pieces, rejected SQFT, and estimated material cost.
- Expanded breakage table view to show pieces, SQFT, estimated cost, coverage gaps, and source in one compact row for each machine/location or glass type.
- Added the supplied per-SQFT material pricing for six standard glass products and six Antique Mirror products; unpriced glass and missing dimensions are surfaced as coverage gaps rather than assigned guessed values.
- Added piece-based and SQFT-based breakage percentages using estimated total produced glass. Internal rejects are included by default, with an explicit Statistics toggle to include/exclude external remake production.
- Kept external remakes out of individual machine accountability; when included in machine comparisons they appear only as an explicit **External remakes** comparison bucket.
- Reworked the Statistics PDF report to include only delivery progress, breakage KPIs, workflow progress, machine breakage, glass-type breakage, and calculation coverage notes.
- Added Spanish mappings for the new breakage controls, datasets, and progressive **Show more data** action so the existing language toggle remains complete.
- Added regression coverage for the glass-first defaults, progressive display limit, short stage labels, reject datasets, pricing reference, produced totals, updated PDF content, v0.260 cache keys, and unchanged schema version 5.
- Advanced `APPLICATION_VERSION` to 260 while preserving `CURRENT_SCHEMA_VERSION = 5`; no database migration, reset, or schema-contract change is included.

## v0.259 - Dense Statistics Workspace and Stable Range Control

- Reduced the visual footprint of the main Statistics chart workspace so more live categories and supporting information remain visible without scrolling.
- Tightened chart header spacing, view controls, filter controls, KPI cards, result messaging, chart canvas padding, table rows, legends, and selected-category details.
- Reduced bar-chart row geometry from 54px to 42px, compacted the line chart from 500px to 420px high, and reduced the donut canvas from 480px to 400px while preserving the same data and interactions.
- Replaced the Statistics side-navigation pseudo-element graphic with an explicit masked chart icon so the icon renders consistently with the other main navigation entries.
- Changed the Statistics reporting-range selector to an intentionally native control and added a stable navy background, white chevron, and scoped hover/focus styling to prevent the transient white state seen during live rerenders.
- Added regression coverage for the Statistics navigation icon, native date-range ownership, compact chart geometry, v0.259 cache keys, and unchanged schema contract.
- Advanced the application revision to 259 while preserving `CURRENT_SCHEMA_VERSION = 5`; no database migration or data change is included.

## v0.258 - Inline Live Statistics Analytics Workspace

- Removed the separate chart explorer modal and promoted the full analytics experience into the Statistics page.
- Added live bar, line, donut, and table views with immediate updates for range, dataset, sort, limit, and category-search changes.
- Expanded the dataset library with delivery completion, open pieces, on-time results, incomplete lists, stage workload, stage open work, scanned/open stage work, glass mix, four delivery-date views, operator scans, scan issues, operational actions, and remakes.
- Kept only four priority metrics above the main chart and removed duplicate workflow and operational-attention cards.
- Added chart-specific KPI cards, selected-category details, accessible chart/table selection, source-order sorting, and top 10/20/50/all display limits.
- Added compact supporting charts for stage completion, open work, and operational activity, each linked back to the main analytics workspace.
- Added icons to Statistics headings, filters, buttons, KPI cards, chart types, data rows, selections, and supporting panels.
- Applied the shared `app-primary-button` component to every blue Statistics action, including Refresh, PDF report, Reset, active view, and Analyze buttons.
- Consolidated all new Statistics chart and table ownership in `static/css/statistics.css` without adding another competing Home-page override layer.
- Advanced the application revision to 258 while preserving `CURRENT_SCHEMA_VERSION = 5`; no database migration or data change is included.

## v0.257 - Dedicated Statistics Workspace

- Added Statistics as its own main navigation page between Home and Scan.
- Removed the statistics dashboard from Home and expanded delivery-list discovery to the full page width.
- Built a polished Statistics command header using the same navy, white-card, restrained-accent, and rounded-control language as the rest of the web app.
- Kept the four priority metrics at the top and enlarged them for faster scanning without adding duplicate totals.
- Promoted glass mix and the full chart explorer into a larger production-mix card.
- Moved stage completion into a dedicated workflow card and retained concise progress, open-piece, and list-count details.
- Kept operational attention limited to scan issues, manual handling, and bay/rack actions.
- Preserved all existing chart datasets, date ranges, PDF reporting, filtering, sorting, display limits, bar/donut views, and chart selection behavior.
- Added `static/css/statistics.css` as the maintained page owner and removed the current statistics ownership block from `home.css`.
- Advanced the application revision to 257 while preserving `CURRENT_SCHEMA_VERSION = 5`; no database migration or data change is included.

## v0.256 - Calm Statistics Dashboard and Progressive Chart Explorer

- Reworked the Home statistics dashboard to match the web app’s established white-card, navy-accent, compact-control visual language.
- Reduced first-view information density to four priority metrics, one glass-mix chart, concise workflow progress, and three operational-health summaries.
- Removed the chart’s repeated largest-quantity and average-per-type summary tiles; the dashboard now shows one actionable largest-share insight.
- Replaced large stage metric cards with compact progress rows showing completion, open pieces, and list count.
- Consolidated scan exceptions, manual scans, bay overrides, manual edits, rack activity, and bay activity into three readable operational summaries.
- Rebuilt the full chart explorer with a dark application header, left setup sidebar, dedicated chart workspace, and progressively disclosed advanced filters.
- Preserved every existing chart metric, date range, sorting option, display limit, search filter, bar/donut view, PDF report, and chart selection behavior.
- Advanced the application revision to 256 while keeping `CURRENT_SCHEMA_VERSION = 5`; no database migration or data change is included.
- Strengthened static regression coverage so the application contract must remain aligned with the maintained migration registry before a release is accepted.

## v0.255 - Five-Migration Contract Startup Recovery

- Fixed the second startup failure caused by applying the v0.254 schema-10 contract to the maintained project checkout whose `database/migrations.py` registry defines migrations 1 through 5.
- Restored `CURRENT_SCHEMA_VERSION` to 5 while advancing `APPLICATION_VERSION` to 255; application revisions and database schema versions are intentionally independent.
- Preserved the verified backup created during the failed startup and made no database reset, replacement, deletion, or manual schema edit.
- Added a contract maintenance comment that frontend-only releases must not change the expected schema version.
- Replaced the incorrect schema-10 regression with a registry parser that validates the actual migration definition sequence `[1, 2, 3, 4, 5]` when the full project is present.
- Preserved the v0.253 Statistics Dashboard redesign and all v0.252 Bay Map/shared-button improvements.
- Advanced the visible version, cache keys, documentation, and tests to v0.255.

## v0.254 - Database Contract Registry Alignment Hotfix

- Fixed the startup-blocking contract mismatch introduced by the v0.253 changed-files package: `database/contract.py` expected only migrations 1 through 5 while the maintained migration registry defines migrations 1 through 10.
- Restored `CURRENT_SCHEMA_VERSION` to 10 so `validate_migration_registry()` accepts the complete maintained registry and database initialization can continue.
- Added an inline maintenance note requiring the contract version to remain synchronized with the highest definition in `database/migrations.py`.
- Added focused regression coverage for application version 254, schema version 10, and the maintained migration range.
- Preserved all v0.253 Statistics Dashboard and chart-explorer changes; this hotfix does not alter, reset, replace, or migrate the existing SQLite database.
- Advanced the application contract, visible version, cache keys, documentation, and tests to v0.254.

## v0.253 - Statistics Dashboard Hierarchy and Chart Explorer Polish

- Rebuilt the Home statistics dashboard around four priority metrics so delivery completion, open pieces, on-time completion, and remake volume appear first.
- Removed the duplicated snapshot/remake statistic containers and consolidated operational exceptions and audited actions into one health section.
- Reworked stage cards to show completion, scanned quantity, open quantity, and list count without repeating top-level KPI values.
- Polished the embedded glass-mix chart with a stronger header, clearer donut presentation, improved legend rows, useful chart context, responsive layout, and a professional empty state.
- Modernized the full statistics explorer with a dark command header, structured filter toolbar, cleaner canvas, and chart-specific summary cards instead of repeated dashboard KPIs.
- Integrated the chart explorer header with the shared dark-header close-button variant so the close control remains consistent and legible.
- Removed the second redundant `renderHomeStatistics` call from the Home render workflow, reducing unnecessary DOM work.
- Added focused structure coverage for the new dashboard ownership, removed duplicate containers, contextual explorer summaries, and single-render behavior.
- Advanced the application contract, visible version, cache keys, documentation, and tests to v0.253. No new migration was intended; v0.255 restores the maintained schema-5 contract for the current project checkout.

## v0.252 - Uniform Bay Map Actions and Sidebar-Aligned Primary Buttons

- Fixed the Bay Map action toolbar root cause by explicitly resetting each launcher's grid column and row in the maintained owner; the older odd-last-child rule can no longer stretch Edit Map across the toolbar.
- Kept all five Bay Map actions at the same 54-pixel height and equal-width five-column layout, including narrow-screen horizontal scrolling.
- Retuned the reusable `app-primary-button` component from the brighter blue palette to the deeper navy family used by the application sidebar.
- Centralized the revised normal, hover, focus, active, border, edge, and shadow colors in `static/css/shared-ui.css` so pages continue sharing one professional button system.
- Added focused structure coverage for the explicit Bay Map grid reset and sidebar-aligned shared palette.
- Advanced the application contract, visible version, cache keys, documentation, and tests to v0.252. Schema version 5 is unchanged.

## v0.251 - Flat Bay Actions and Compact Centered Scan Selectors

- Removed the v0.250 category-gradient override from Print / Export so its filters return to the established pre-gradient visual system.
- Rebuilt the five Bay Map launcher buttons as one equal-height row with flat, restrained category surfaces; narrow layouts scroll horizontally instead of wrapping Edit Map beneath the other actions.
- Reduced the Scan panel Date and Stage selectors to matching 120-pixel controls and centered them around the station title.
- Positioned each custom-select arrow independently from the selected value so the date and stage text remain optically centered.
- Increased selector line height and vertical room enough to prevent descenders, including the “g” in Staging, from clipping.
- Advanced the application contract, visible version, cache keys, documentation, and tests to v0.251. Schema version 5 is unchanged.

## v0.250 - Numeric Week Dates, Centered Scan Identity, and Bay Status Clarity

- Restored compact M/D/YYYY delivery-date labels in maintained date selectors and Print / Export while retaining Monday-Friday business-week separators.
- Added reusable business-week grouping to the Home delivery-list catalog with This Week, Next Week, Last Week, and dated week headings.
- Centered the Scan panel station title and placed equally prominent Date and Stage controls immediately beside it with centered selection text.
- Applied the shared primary-button treatment to Sign In and password-reset primary actions and darkened the reusable blue beveled palette across the webapp.
- Standardized the five Bay Map launcher buttons to equal dimensions with restrained dark-blue-to-category gradients.
- Added matching category-gradient treatment to Print / Export filter buttons and header actions while preserving clear selected-state outlines.
- Changed grouped bay totals to occupied/total with the available count, moved Auto/Man policy indicators to the upper-left, and strengthened individual bay Available, Occupied, Preassigned, and Picking states.
- Advanced the application contract, visible version, cache keys, documentation, and tests to v0.250. Schema version 5 is unchanged.

## v0.249 - Guided Rack Editing, Scan Header Clarity, and Business-Week Date Menus

- Kept Edit Bays and a smaller Edit Map action adjacent at the right side of the Bay Map action row.
- Reduced Delivery List Management Previous/Next controls and centered them as a tighter pager pair.
- Reworked Edit Racks into a guided workspace with icon-led Add Rack Set and Add Individual Rack actions inside the content area, clearer set summaries, and group icons.
- Removed generic green-dot status pills from static modal headers. Live status remains available for changing workspaces such as individual rack state, active sessions, manual edits, current delivery data, and the Automation Control Center.
- Swapped Date and Stage in the Scan panel, enlarged the station name as the panel title, removed the visible Assigned station label, and standardized Scan stage names to Staging, Outbound, Indian Trail, CPU, DTC, and Greenville.
- Added Monday-Friday business-week optgroup separators to maintained delivery-date dropdowns outside Print / Export.
- Reduced shared full-GUI close buttons by approximately 15%, from 58px to 49px, while preserving one centered-X component.
- Advanced the application contract, visible version, cache keys, documentation, and tests to v0.249. Schema version 5 is unchanged.

## v0.248 - Bay Map Streamlining, Rack Set Icons, and Timed Update Review

- Removed the Bay Map Physical Floor View helper strip and its duplicate Open Manage Items action while preserving the maintained Manage Items control in the right-side action panel.
- Hid the physical-bay summary bar when no filters are active, eliminating the persistent “Showing all physical bays” and compact-filter guidance text.
- Reduced Bay Map Undo/Redo controls through page-owned shared-component variables and reduced the compact Submit action by approximately twenty percent.
- Reorganized the Admin import-run pager so Previous and Next sit together in the center with smaller dimensions.
- Reworked rack-set icons so the set-specific symbol occupies the main icon tile and the secondary corner badge is removed; individual rack GUI icons remain unchanged.
- Moved new/updated review presentation out of the global stylesheet and into `static/css/scan.css`, moved the notice below the filter toolbar, polished the notice, and applied the shared primary-button treatment to Mark Reviewed.
- Added a visible 15-second countdown and automatic dismissal to the delivery-list update popup.
- Advanced the application contract, visible version, cache keys, documentation, and tests to v0.248. Schema version 5 is unchanged.

## v0.247 - CSS Ownership Cleanup and Stable Shared Controls

- Reorganized recent UI work so reusable blue actions and close buttons live only in `static/css/shared-ui.css`, Print / Export and Create Preset rules live in `static/css/print.css`, and rack icons/modal polish live in `static/css/racks.css`.
- Removed duplicate `.gui-close-button` and recent shared-primary ownership from `static/css/styles.css` instead of adding another release override.
- Removed Admin, Bay, Rack, and Reject close-button shape/color rules, retaining only page-specific placement while the shared component owns geometry and interaction.
- Fixed the resting X by giving its SVG mask an explicit color independent of the hidden legacy text glyph.
- Separated keyboard focus from destructive hover styling so the Automated Control Center no longer opens with a false red-hover state.
- Strengthened shared component specificity with reusable anchors so older page IDs cannot resize, flatten, or recolor only one copy of a common control.
- Restored white Search text and icon states and applied the shared beveled style to the Scan page Print Packing Slip button.
- Advanced the application contract, visible version, cache keys, documentation, and tests to v0.247. Schema version 5 is unchanged.

## v0.246 - Unified Square Close Buttons and Distinct Rack Set Icons

- Standardized every full-GUI close button to one truly square shared control with the X locked to the visual center, eliminating the stretched and off-center variants.
- Hardened the shared close-button ownership rule so older modal and header selectors cannot reintroduce the prior automation-center close-button overlap or legacy glyph sizing.
- Removed inherited rack-set icon classes that were leaking the old legacy corner icons into the new rack visuals.
- Expanded rack-set and individual rack icon mapping so Coral, LR, RR, Showers, Mirrors, BFS Mirrors, Framed Mirrors, CRL, and Spacers each render with their own icon family and matching set color treatment.
- Advanced the application contract, visible version, cache keys, documentation, and tests to v0.246. Schema version 5 is unchanged.

## v0.244 - Beveled Actions and Rack GUI Visual Identity

- Enlarged the reusable `.gui-close-button` to a 58-pixel rounded square and replaced browser-dependent X glyph positioning with one generated, consistently centered X.
- Preserved the maintained white-X/red-background hover and keyboard-focus treatment while adding a pressed state and beveled resting surface.
- Kept transient toast and banner dismissals compact so the larger modal-close geometry applies only to full GUI controls.
- Added a deeper reusable bevel to `.app-primary-button`, including raised, hover, pressed, focus, and disabled states.
- Migrated Global Search, Bay Map Find Match, Racks History, Print/Export, and Scan-page Complete controls to the shared blue action class.
- Repaired the Racks History button's pointer and hover surface so the complete button remains selectable and never flashes white over only part of its content.
- Added deterministic rack-set hues and icon families that are shared by rack-set selectors and each individual rack detail GUI.
- Added rack-set-colored headers, rack-set icons, hollow top-right header rings, themed list accents, and restrained row hover polish to individual rack GUIs.
- Added a polished audited-records header, history icon, and hollow top-right header ring to the Racks History GUI.
- Advanced the application contract, visible version, cache keys, documentation, and tests to v0.244. Schema version 5 is unchanged.

## v0.243 - Formatted Excel Export and Shared Webapp Controls

- Replaced the plain server-generated XLSX handoff with a browser-built workbook based on the exact printable preview selection.
- Added one formatted worksheet per normal, Rush, or remake delivery sheet with the supplied company logo, route-first title, full delivery date, row/order/QTY totals, filter summary, Checked By line, glass-type section bands, alternating rows, and print-ready page setup.
- Added workbook print areas, repeated column headings, frozen headings, Letter orientation support, hidden gridlines, and maintained column widths so Excel output remains useful on screen and on paper.
- Kept CSV output deliberately raw and unformatted with one record per selected item and explicit identifiers, date, quantity, status, attention, glass, dimensions, and route fields.
- Added `.app-primary-button` as the reusable polished blue action style and made existing maintained primary selectors compatibility aliases for consistent webapp behavior.
- Standardized `.gui-close-button` as a centered 34-pixel rounded square with the existing white-X/red-background hover and focus behavior, including remaining dynamic dismiss controls.
- Restored the supplied print logo to the changed-files package because both browser printing and formatted XLSX export depend on the same maintained asset.
- Advanced the application contract, visible version, cache keys, documentation, and tests to v0.243. Schema version 5 is unchanged.

## v0.242 - Preset Dialog and Adaptive Glass Layout Polish

- Replaced the browser-native print-preset deletion confirmation with the existing shared `confirmWebAppAction` dialog.
- Added the shared success feedback dialog and application save sound after successful preset deletion, including Default fallback details when applicable.
- Removed fixed-height stretching from Annealed, Tempered, and Mirror panels so each family sizes to its actual product list and grows naturally when new glass types are discovered.
- Increased exact glass-product font size, enabled full multi-line wrapping, added comfortable cell indentation, and preserved a fixed-width check indicator.
- Removed the browser-native Copies spinner so the maintained minus/plus stepper is the only visible increment control.
- Replaced the Save Preset card's temporary lightning symbol with the standard save icon.
- Advanced the application contract, visible version, cache keys, documentation, and tests to v0.242. Schema version 5 is unchanged.

## v0.241 - Preset Management and Shared GUI Close Controls

- Added a trash-can action beside every user-created Print / Export preset while protecting the built-in preset from deletion.
- Renamed the visible built-in preset from `System Default` to `Default` and retained compatibility with the former reserved name.
- Added deletion cleanup for active and personal-default presets so deleting one safely falls back to Default.
- Added one reusable `gui-close-button` class for all maintained top-right GUI X controls, with corrected glyph centering and consistent white-on-red hover/focus feedback.
- Moved the Create Preset Glass Types row title to the top of the expanded section.
- Changed Annealed, Tempered, and Mirror product lists to one vertical column per family.
- Added fixed-width glass selection indicators so check marks remain aligned regardless of product-name length.
- Advanced the application contract, visible version, cache keys, documentation, and tests to v0.241. Schema version 5 is unchanged.

## v0.240 - Consistent Header Rings and Compact Preset Workspace

- Removed the remaining filled radial circle from the Print / Export header.
- Added the maintained hollow outline-ring decoration to both Print / Export and Create Preset using one consistent size, weight, and placement.
- Increased the practical Create Preset desktop height and compacted card spacing, filter rows, choices, and the grouped glass library so routine desktop use no longer needs vertical scrolling.
- Preserved safe internal scrolling for narrow stacked layouts and unusually short browser windows so no controls become unreachable.
- Added explicit hover feedback to the Create Preset Attention choices without moving or highlighting the surrounding section.
- Removed parent-level focus outlines from the Preset Name label and Smart Search container while keeping accessible focus feedback on the actual input, choice, or switch.
- Advanced the application contract, visible version, cache keys, documentation, and tests to v0.240. Schema version 5 is unchanged.

## v0.239 - Stable Workspace Surfaces and Business-Week Labels

- Removed hover movement, border changes, and elevation from Print / Export filter sections, preview surfaces, and Create Preset cards; hover feedback remains on actual controls and buttons.
- Removed the large outline circle from the Print / Export header and both outline circles from the Create Preset header.
- Removed the `Ready to create a reusable print setup.` empty-state sentence from the bottom of Create Preset.
- Changed Delivery Date group ranges from Monday-Sunday to Monday-Friday so a week beginning August 3 displays as `Aug 3–7` rather than `Aug 3–9`.
- Advanced the application contract, visible version, cache keys, documentation, and tests to v0.239. Schema version 5 is unchanged.

## v0.238 - Print Workspace Interaction Polish

- Added the maintained hollow outline-circle motif to the top-right of both Print / Export and Create Preset.
- Added restrained hover and focus elevation to filter sections, preview controls, preset cards, header controls, and primary actions.
- Added clearer hover feedback to modal close buttons and a quiet inner highlight to selected controls.
- Added consistent keyboard focus rings across buttons, inputs, selects, and checkbox-backed controls.
- Added `prefers-reduced-motion` handling so the polish does not force movement on motion-sensitive users.
- Kept the entire visual pass CSS-only, adding no timers, API calls, or JavaScript work during normal interaction.
- Advanced the application contract, visible version, cache keys, documentation, and tests to v0.238. Schema version 5 is unchanged.

## v0.237 - Persistent Smart Search and Dynamic Glass-Family Presets

- Fixed Smart Search closing after Add Item or Add Order by stopping the result click before the rerendered button can be treated as an outside click.
- Added composed-path protection to the document outside-click handler so the Smart Search panel remains open during continuous order/item selection.
- Increased Add Item and Add Order action size and typography while preserving the detail-first result layout.
- Added Annealed set, Tempered set, and Mirror set selectors to Create Preset alongside exact product choices.
- Stored selected glass families as semantic preset rules so future imported products in those Lookup Manager families are included automatically.
- Reapplied semantic family and exact-product rules after every date or route change, including dates where a selected family temporarily has no matching rows.
- Preserved existing exact-glass presets through backward-compatible `glassTypes` handling and added optional `glassFamilies` data without a database migration.
- Advanced the application contract, visible version, cache keys, documentation, and tests to v0.237. Schema version 5 is unchanged.

## v0.236 - Print Filter Cleanup and Persistent Smart Search

- Removed the main Print / Export Glass Type search bar and its obsolete client-side filtering implementation.
- Removed the requested explanatory text beneath Route, Glass Type, Status, and Attention.
- Rebuilt Smart Search result cards around one clear set of order, item, customer, job, glass, quantity, and delivery-date fields.
- Increased result-information typography while reducing Add Item and Add Order to compact actions.
- Preserved the active query and kept Smart Search open after Add Item or Add Order so users can continue selecting without reopening the panel.
- Removed search-only empty-state markup, event wiring, reset logic, element registration, and dedicated CSS to avoid dead code.
- Advanced the application contract, visible version, cache keys, documentation, and tests to v0.236. Schema version 5 is unchanged.

## v0.235 - Startup-Safe Create Preset Event Wiring

- Removed the stale `renderPrintPresetLiveSummary` listener that caused a `ReferenceError` during application startup after the Preset Summary feature was removed.
- Consolidated Create Preset listeners into `wirePrintPresetEvents()` so the feature has one maintained event-wiring owner.
- Added `wireOptionalStartupFeature()` to isolate optional Create Preset initialization failures from the core application startup path.
- Added `addOptionalUiEventListener()` so absent optional controls or handlers are skipped safely instead of throwing.
- Preserved all v0.234 Create Preset behavior, output settings, saved presets, and personal-default handling.
- Added focused regression checks for deleted helper references and startup isolation.
- Advanced the application contract, visible version, cache keys, documentation, and tests to v0.235. Schema version 5 is unchanged.

## v0.234 - Create Preset Simplification and Theme Alignment

- Removed the requested helper text from Preset Details, filter groups, Save Preset, and the bottom information footer.
- Removed the Glass Types search control and its event/search implementation.
- Removed the complete Preset Summary card and its live-rendering code.
- Moved Print Options and Save Preset upward into the right column.
- Rebalanced the modal into a wider filter workspace and a compact output/action column.
- Updated the modal shell, cards, buttons, fields, backdrop, and selected states to match the webapp's maintained navy, blue, gray, and white palette.
- Preserved route and glass-family accents as restrained category cues.
- Preserved the v0.233 single-scroll-owner behavior and schema version 5.
- Advanced the application contract, visible version, cache keys, documentation, and focused tests to v0.234.

## v0.233 - Create Preset Scroll and Bottom Containment Repair

- Restored one reliable internal vertical scrollbar to the complete Create Preset workspace at all supported viewport heights.
- Kept the branded modal header fixed while every editable section and the bottom Save Preset/help area scrolls together inside the dialog.
- Replaced stretch-owned workspace rows with content-sized rows so expanded glass categories cannot push Summary, Print Options, Actions, status, or help content beyond the modal boundary.
- Removed the right-column auto spacer that could leave Save Preset outside the reachable content flow.
- Added stable scrollbar gutter spacing, touch momentum scrolling, scroll padding, and comfortable bottom containment without introducing nested scroll regions or background work.
- Preserved the v0.232 visual palette, grouped glass library, route accents, responsive layout, personal preset behavior, and schema version 5.
- Advanced the application contract, visible version, cache keys, documentation, and focused tests to v0.233.

## v0.232 - Expanded Preset Workspace and Restrained Category Colors

- Removed the Create Preset Description field and simplified Preset Details to Preset Name plus the personal-default toggle.
- Increased the desktop workspace height from 760 to 860 pixels so standard desktop displays can show the complete modal without routine vertical scrolling.
- Kept one safe internal scrollbar for shorter desktop, tablet, and mobile viewports.
- Expanded Glass Types into three side-by-side desktop panels ordered Annealed, Tempered, and Mirror.
- Restored restrained route-specific tints for Airport, Indian Trail, Greenville, CPU, and DTC.
- Restored restrained glass-family colors: blue for Annealed, green for Tempered, and purple for Mirror.
- Kept Status and Attention choices neutral to prevent the color system from becoming visually overwhelming.
- Consolidated final Create Preset styling into the v0.232 ownership block rather than stacking another duplicate override layer.
- Advanced the application contract, visible version, cache keys, documentation, and focused tests to v0.232. Schema version 5 is unchanged.

## v0.231 - Neutral Preset Selection and Grouped Glass Library

- Organized Create Preset glass choices into Annealed, Tempered, and Mirror sections without changing their exact stored or Lookup Manager values.
- Updated glass search so empty category sections hide automatically while matching categories remain grouped.
- Replaced route-, status-, attention-, and glass-specific preset button colors with one neutral unselected style and one clearly defined selected style.
- Strengthened selection visibility with a two-pixel border, shared soft background, circular check badge, and selected-count pills.
- Moved Print Options below Preset Summary and anchored Save Preset actions at the bottom-right of the desktop workspace.
- Simplified headings, descriptions, placeholders, and the preset information footer to reduce visual and reading load.
- Consolidated the former v0.230 flow-repair ownership block into the v0.231 layer instead of adding another duplicate CSS override section.
- Preserved responsive stacking, personal defaults, live summary, Save/Apply behavior, and schema version 5.
- Advanced the application contract, visible version, cache keys, documentation, and focused tests to v0.231.

## v0.230 - Create Preset Flow Repair and Subtle Control Palette

- Replaced the fixed first workspace row with content-sized grid rows so the main column can no longer overflow underneath the status and information rows.
- Assigned explicit desktop, tablet, and mobile grid placement for the main column, summary/actions column, status message, and information footer.
- Retained a compact centered modal while allowing one maintained internal scrollbar when content exceeds the available browser height.
- Replaced saturated selected route, status, attention, and glass fills with soft category tints, defined borders, dark readable labels, and preserved check marks.
- Softened action buttons, orientation controls, card accent rails, shadows, workspace patterning, and the modal backdrop.
- Added v0.230 ownership classes so the repair cleanly overrides v0.227-v0.229 presentation rules without changing preset behavior.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.230. Schema version 5 is unchanged.

## v0.229 - Compact Polished Create Preset Workspace

- Reduced the desktop Create Preset control center from a near-full-screen window to a centered 1240 × 780 maximum while retaining safe responsive sizing at 1024px and mobile widths.
- Increased the typography for preset labels, descriptions, input values, filter choices, selection totals, live summary values, and action buttons.
- Added final v0.229 modal ownership so the smaller centered geometry does not conflict with the v0.228 viewport repair or older modal transforms.
- Reused the maintained Print / Export route, status, attention, All-choice, Mirror, Tempered, and Annealed gradient palettes inside Create Preset.
- Added card accent rails, layered panel gradients, polished controls, and a subtle workspace grid so Create Preset and Print / Export read as one product.
- Preserved internal scrolling, responsive stacking, Lookup Manager glass types, live summary, personal-default selection, and all existing save/apply behavior.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.229. Schema version 5 is unchanged.

## v0.228 - Create Preset Viewport Positioning Repair

- Fixed the v0.227 Create Preset control center being shifted far beyond the top-left of the browser by inherited `top: 50%`, `left: 50%`, and `translate(-50%, -50%)` rules from the legacy compact modal.
- Added a final v0.228 positioning layer that neutralizes the inherited legacy transform while retaining historical class compatibility.
- Added dedicated v0.228 fixed-position ownership with safe desktop and mobile viewport insets.
- Kept the modal workspace internally scrollable and added compact-height tuning for shorter screens.
- Reset the workspace scroll position whenever Create Preset opens and focused the name field without causing viewport movement.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.228. Schema version 5 is unchanged.

## v0.227 - Health-State Attention Filters and Preset Control Center

- Changed Remakes, Rushes, and Internal Rejects so the entire filter button follows its live health state: red gradient with an exclamation when matching work exists, green gradient with a check when clear.
- Rebuilt Create Preset around the supplied control-center reference with Preset Details, Default Filters, Print Options, Preset Summary, and Actions.
- Removed the Visibility and Preview sections from the new preset workspace.
- Added an optional preset description and a personal-default toggle while retaining the immutable System Default fallback for users who do not choose a custom default.
- Added separate Save Preset and Save & Apply actions, live right-column summary updates, copy stepper controls, and responsive layout behavior.
- Preserved the Lookup Manager product library, automatic All-choice collapse rules, grouped newest-first date history, and schema version 5.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.227.

## v0.226 - Automatic All Selections and Newest-First Delivery Dates

- Automatically replaces every available detailed Route selection with Airport, the maintained all-routes choice.
- Automatically replaces complete Glass, Status, and Attention detail selections with their corresponding All choice in both Print / Export and Create Preset.
- Reordered grouped Delivery Date weeks and individual dates from newest/future to oldest so later weeks appear above This Week and historical weeks.
- Restored the v0.224 step-guided Create Preset layout while retaining the v0.225 grouped-date history and in-memory load-more behavior.
- Increased glass-category count typography, changed Tempered section/chip styling from orange to green, and lengthened the borderless Checked By write-in line.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.226. Schema version 5 is unchanged.

## v0.225 - Grouped Delivery Date History and Unified Preset Workspace

- Reduced Landscape continuation-page pagination from 29 to 28 logical rows while retaining 27 logical rows on the first Landscape page and the existing Portrait limits.
- Reworked Create Preset into one continuous workspace with the preset name, compact Route/Status/Attention cards, full Lookup Manager glass library, and output settings visible without step navigation.
- Removed the Step 1 / Step 2 framing and retained immediate current-selection loading, overwrite guidance, per-user storage, and System Default protection.
- Grouped Delivery Date options by Monday-Sunday week with clear This Week, Last Week, Next Week, and dated week headings.
- Limited the initial historical date list to the rolling previous two weeks while continuing to show every available future delivery date.
- Added in-memory two-week history expansion when the user reaches the bottom of the date menu, plus an explicit load-more row for pointer and keyboard access.
- Kept custom date ranges and selected older dates available even when they fall outside the initial history window.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.225. Schema version 5 is unchanged.

## v0.224 - Unavailable Filter States and Aligned Print Signoff

- Grayed out and disabled zero-count Route, Status, New/Updated, and Errors choices in Print / Export so unavailable filters are visually and functionally distinct.
- Kept Remakes, Rushes, and Internal Rejects enabled at zero so their Scan-page-style green-clear and red-alert indicators remain useful.
- Added safe fallback selection behavior when a previously selected route or standard filter no longer contains rows after a date/scope change.
- Increased the filter-chip count font for faster quantity scanning without increasing chip height.
- Removed the border and background around Checked By, enlarged its text, and aligned it with the first-page Filters line at the right side of the title header.
- Increased Rows, Orders, and QTY typography on first and continuation pages while retaining the more compact Filters treatment.
- Preserved v0.223 pagination, table widths, shared preview/print styling, and schema version 5.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.224.

## v0.223 - Table-Adjacent Signoff and Fuller Delivery Pages

- Moved the first-page `Checked By` field out of the branded title block and placed it directly above the delivery-list column headings.
- Kept the signoff right aligned in a compact print-safe row shared by preview and popup printing.
- Increased safe pagination by two logical lines on first pages and three logical lines on continuation pages.
- Set Portrait limits to 26/28 and Landscape limits to 27/29 logical rows for first/continuation pages; glass headings continue to count toward the limit.
- Centered Order, Item, and QTY headings and values in preview and print output.
- Narrowed Dimensions by less than one percentage point and gave that width to QTY so all three letters remain visible.
- Preserved Letter geometry, Default margins, enlarged branded headers, repeating Filters, alternating row bands, fixed Printed at footer, and Rush/remake frames.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.223. Schema version 5 is unchanged.

## v0.222 - Enlarged Branded Delivery-Sheet Headers

- Enlarged the complete first-page title area by approximately 30%, including the supplied print logo, route heading, full weekday date, totals, Filters line, badge, and Checked By signoff.
- Enlarged continuation-page branding by approximately 10% while keeping it visibly subordinate to the first-page header.
- Added fit-aware first-page and continuation-page sizes for medium and long multi-route titles so headings remain on one line.
- Applied all sizing through the shared delivery-sheet stylesheet, keeping preview and popup printing visually identical.
- Adjusted safe pagination to 24/25 logical rows in Portrait and 25/26 in Landscape for first/continuation pages so enlarged headers do not clip table rows or the repeating footer.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.222. Schema version 5 is unchanged.

## v0.221 - Idle Route and Print Row State Recovery

- Fixed the intermittent Print / Export failure that appeared after leaving the browser tab or another app page idle while Airport still looked selected.
- Changed background delivery-list catalog updates to merge lightweight summaries with already loaded item detail instead of replacing `state.lists` and silently discarding print rows.
- Preserves cached item detail only while the delivery-list revision is unchanged; changed lists are invalidated and reloaded on demand.
- Reasserts committed route controls on window focus, `pageshow`, tab visibility recovery, and catalog-sync events.
- Added a single-flight recovery guard so simultaneous focus/catalog events cannot issue duplicate detail requests.
- Keeps recovery event-driven with no new timer, polling loop, or recurring network work. Schema version 5 is unchanged.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.221.

## v0.220 - Print Filter Visual Hierarchy and Compact Signoff

- Removed the Date write-in field from the printed signoff block and kept one right-aligned Checked By line, giving route titles and filter metadata more horizontal room.
- Repeated the compact active Filters line on every delivery-list page, including continuation pages.
- Reduced continuation-page pagination by one logical row in Portrait and Landscape to keep the new repeating metadata inside Default Letter margins.
- Added route-specific gradients for Airport, Indian Trail, Greenville, CPU, and DTC choices in Print / Export.
- Grouped current glass choices beneath compact Mirror, Tempered, and Annealed separator headers with category-specific colors while preserving exact maintained product values.
- Added distinct gradient treatments for Status and Attention choices.
- Added Scan-page-style red exclamation circles when Remakes, Rushes, or Internal Rejects are present and green check circles when those categories are clear.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.220. Schema version 5 is unchanged.

## v0.219 - Shared Preview and Print Styling

- Lowered the first-page Checked By and Date signoff fields within the branded header and kept each field on one uninterrupted line.
- Forced the full weekday delivery date to remain on one line in both Portrait and Landscape layouts.
- Removed the duplicated popup sheet-design CSS and made the generated print window load the same versioned `static/css/styles.css` used by the on-screen preview.
- Retained only Letter page size, 0.4-inch browser margin, page-break, and print-safe frame overrides inside the popup document.
- Added print startup readiness checks for the shared stylesheet, fonts, and supplied logo before invoking the browser print dialog.
- Changed the default Portrait preview zoom to 90%, including when switching back from Landscape.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.219. Schema version 5 is unchanged.

## v0.218 - Reliable Print Logo and Tightened Branded Header

- Restored `static/images/barefoot-company-builders-firstsource-print-logo.png` to the release package so both the Letter preview and popup print document show the supplied artwork instead of fallback alt text.
- Resolves the print logo from the active application URL with a v0.218 cache key, avoiding relative-path ambiguity inside the generated popup document.
- Removed the continuation-sheet sentence beneath the title; page progression remains available in the top-right `List page X of Y` label.
- Prevented route-first titles from wrapping into an indented second line and added automatic medium/long title scaling for multi-route output.
- Increased the full weekday date size so it is nearly as prominent as the delivery-list title while remaining visually secondary.
- Reduced spacing between the totals line and active Filters line in preview and actual print CSS.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.218. Schema version 5 is unchanged.

## v0.217 - Full Weekday Dates and Route-First Delivery Titles

- Standardized delivery-date display text to the full weekday format, such as `Tuesday, August 4, 2026`, across the browser application including Home and Delivery List views.
- Rebuilt the preview and printed header so the selected destination routes form the primary uppercase title, such as `INDIAN TRAIL DELIVERY LIST`.
- Uses vertical separators for multi-route headings, such as `GREENVILLE | CPU | DTC DELIVERY LIST`, while retaining Airport as the safe default destination.
- Places the full weekday date immediately beneath the route title on first and continuation pages.
- Expanded the adaptive Print / Export date selector width for full weekday labels and custom date ranges.
- Preserved the supplied monochrome print logo, totals, filters, signoff fields, page numbering, pagination, gray bands, alternating rows, and footer behavior.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.217. Schema version 5 is unchanged.

## v0.216 - Supplied Print Logo and Cleaner Header Metadata

- Added the user-supplied stacked Barefoot Company and Builders FirstSource logo to `static/images` and switched the delivery-list preview and print package to that dedicated asset.
- Cropped only the broad unused white canvas around the supplied image so the artwork renders larger and cleaner without changing the logo design.
- Removed the extra sheet-header divider immediately above the column headings on normal, continuation, Rush, and remake pages.
- Kept the maintained black divider between the column header row and glass-type subheaders.
- Moved the active Filters summary onto its own line directly beneath `Rows | Orders | QTY` so the metadata order is consistent and easier to scan.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.216. Schema version 5 is unchanged.

## v0.215 - Date-First Branded Print Header and Alternating Rows

- Rebuilt the delivery-list title so the delivery date is the dominant top-left heading in compact `M/D/YY` form, with `Delivery list for <destination>` directly beneath it.
- Derives the printed destination title from the committed Print / Export Route selection, including maintained multi-route labels when more than one destination is selected.
- Reuses the existing sidebar Barefoot/Builders FirstSource logo in the preview and generated print document, applying grayscale and contrast treatment so it remains clear on black-and-white paper.
- Added a solid black divider beneath the column headings and above every glass-type subheader to create a clearer visual break between table structure and grouped products.
- Added alternating white and light-gray order rows with exact print-color adjustment for improved scanability in preview, color printing, and monochrome printing.
- Preserved v0.214 pagination, Route centering, first-page signoff fields, compact continuation headers, gray heading bands, remake/rush frames, and repeating Printed at footer.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.215. Schema version 5 is unchanged.

## v0.214 - Fuller Page Capacity and Repeating Print Footer

- Increased Portrait pagination from 23/25 to 25/27 logical rows while continuing to count glass-type headings so bottom rows remain inside Default Letter margins.
- Increased Landscape pagination from 16/18 to 26/28 logical rows to use the wider page more effectively without allowing rows to enter the footer area.
- Limited Checked By, Date, and the active filter summary to the first page of each delivery-list section; continuation pages use a compact title and totals header.
- Moved `Printed at` into a fixed bottom-left footer on every preview and printed page.
- Center aligned Route in Portrait and Landscape preview/print tables.
- Strengthened column-header and glass-type subheader gray fills and enabled exact print-color adjustment so those bands appear on paper.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.214. Schema version 5 is unchanged.

## v0.213 - Denser Delivery Sheets and Stable Remake Frames

- Removed the Notes section from every delivery-list page and used the recovered vertical space for additional printable order rows.
- Increased safe pagination to 23/25 logical rows for Portrait and 16/18 for Landscape while continuing to count glass group headings, preventing bottom-row clipping.
- Left aligned Route in both the on-screen Letter preview and generated print document.
- Raised the Check heading and checkbox cells to the same type scale as the other table columns in Portrait and Landscape.
- Rebuilt the remake dashed frame with a contained printable inset and hidden overflow so no portion can appear on the previous sheet.
- Added a narrow remake-only content gutter in preview and print output so the dashed frame remains visible without overlapping list content.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.213. Schema version 5 is unchanged.

## v0.212 - Adaptive Print Metadata, Stable Route State, and Table Fit

- Removed Route from the printed filter summary and changed the line to show only unique, active restrictions; completely unfiltered output now reads `Filters: All items`.
- Shortened delivery-list totals to `Rows | Orders | QTY` so the print header uses less vertical and horizontal space.
- Made Airport route state authoritative across date changes, panel reopen, preset application, and Portrait/Landscape switching instead of rereading stale visual checkbox markup.
- Automatically fits Landscape Letter sheets to the available preview width when orientation changes while retaining manual zoom controls.
- Renamed the compact table headings to `Order`, `Item`, and `QTY`; widened Dimensions, narrowed Customer, widened Route and Check, and restored Route text to the same readable size as the other columns.
- Moved the remake dashed outline into the physical page-margin area so it surrounds the sheet without overlapping delivery-list content or being clipped by Default print margins.
- Made the Delivery Date selector width respond to the active label: compact for one date and wider for a custom range.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.212. Schema version 5 is unchanged.

## v0.211 - Letter Preview Parity and Printed Filter Summary

- Rebuilt the Delivery List Preview around physical US Letter dimensions so Portrait uses 8.5 x 11 inches and Landscape uses 11 x 8.5 inches.
- Matched preview and generated print output to the same 0.4-inch Chrome/Edge Default-margin model instead of using unrelated screen-only sheet padding.
- Synchronized preview and print title sizes, metadata text, table measurements, column widths, notes boxes, Rush borders, remake borders, and landscape geometry.
- Added a compact gray `Filters` sentence beneath the totals and above `Printed at` on normal, Rush, remake, and continuation pages.
- The printed summary records Route, Glass, Status, Attention, exact order/item selection count, and Updated-only mode while compressing large multi-select groups into counts.
- Kept the remake outline at a consistent printer-safe physical inset from all four Letter-page edges in both preview and print output.
- Preserved the v0.210 deterministic Airport initialization, exact preview/output rows, system default preset, and schema version 5.
- Advanced the application contract, visible version, asset cache keys, documentation, and focused structure tests to v0.211.

## v0.210 - Deterministic Initial Airport Route

- Fixed the intermittent state where Airport looked selected when Print / Export opened but was not yet committed for preview, print, or export.
- Commits the System Default Airport route synchronously before the GUI is exposed or any asynchronous delivery-list detail request begins.
- Added maintained route normalization so an empty, invalid, or conflicting route set resolves to the complete Airport outbound selection.
- Prevents initial filter rendering from reading stale route markup left behind by a previous Print / Export session.
- Replaced the redundant startup reset plus System Default reapplication with one initialization transaction, removing overlapping filter renders.
- Tracks the active Print / Export open session so a late response from an older or closed session cannot replace current filter state.
- Makes Print and Export await any in-progress workspace initialization before validating rows and creating output.
- Preserved the v0.209 preset redesign, system default, landscape printing, print totals, inset remake border, and schema version 5.
- Advanced the application contract, visible version, asset cache keys, documentation, and focused structure tests to v0.210.

## v0.209 - System Default Preset, Landscape Sheets, and Print Totals

- Moved the Delivery Date selector into the left Filters heading cluster so the active date sits immediately beside the section name instead of floating with the action buttons.
- Increased Delivery Date, Create Preset, Saved Presets, and Clear Filters typography to a centered 12.5-pixel control style while preserving compact sizing.
- Completely redesigned Create Preset as a guided two-column workspace with a dedicated name step, system-default explanation, usage guidance, balanced filter cards, and a responsive output-settings area.
- Added an immutable `System Default` preset available to every user without duplicating it into per-user browser storage.
- Applies System Default automatically on initial Print / Export open and after Clear Filters: Airport/all outbound items, All Glass, All Status, All Attention, PDF, one copy, and Portrait.
- Kept user-created presets user-scoped, displayed them after System Default, and blocked users from replacing the reserved system preset name.
- Added orientation-aware pagination so landscape sheets use their own page-height limits instead of reusing portrait pagination.
- Designed a true landscape delivery-list sheet with a wider Customer and Dimensions layout, compact row spacing, landscape header geometry, and a reduced notes area.
- Added Total printable rows, Total orders, and Total QTY metadata above the Printed at timestamp on normal, Rush, remake, and continuation sheets.
- Replaced the remake sheet's outer dashed border with a printer-safe inset outline in both preview and print output so all four corners remain visible.
- Kept the v0.208 exact glass-type filtering unchanged after confirming the reported zero-row case was caused by an intentionally selected Remakes attention filter.
- Advanced the application contract, visible version, asset cache keys, documentation, and focused structure tests to v0.209 while retaining schema version 5.

## v0.208 - Exact Glass Preview State and Centered Header Controls

- Fixed exact glass-type choices showing nonzero chip counts while the Delivery List Preview incorrectly rendered zero printable rows.
- Made committed route and exact-glass application state authoritative for preview filtering instead of rereading transient controls during asynchronous filter rerenders.
- Added one maintained glass-type comparison key that normalizes Unicode, common inch/quote marks, repeated whitespace, surrounding whitespace, and letter case while preserving original product labels for display, presets, and output.
- Captures Airport and exact glass selections before loading placeholders replace the filter controls, preventing a valid route from being lost during a glass selection refresh.
- Reconciles retained and saved glass selections against the currently loaded product catalog by normalized identity so small formatting differences do not invalidate a selection.
- Centered the Delivery Date and Saved Presets select labels across their full controls and kept Create Preset and Clear Filters content centered at the same vertical level.
- Preserved the v0.207 custom-range calendar, Lookup Manager product library, responsive preset layout, exact order/item selection, PDF/XLSX/CSV behavior, and schema version 5.
- Advanced the application contract, visible version, cache keys, documentation, and focused structure tests to v0.208.

## v0.207 - Custom Range Completion, Stable Initial Filters, and Lookup Glass Library

- Removed repeated leading wording from individual delivery-date and applied date-range selector labels.
- Changed Custom Range to begin a fresh two-click draft when opened from a single date, preserving an existing range only when editing one.
- Fixed calendar day clicks closing the picker after the grid rerender by using the original composed event path for outside-click detection.
- Renamed the guarded calendar action to Apply Dates and continued to require both Date From and Date To.
- Increased Delivery Date, Create Preset, Saved Presets, and Clear Filters typography to match the 10.5-pixel filter-chip content.
- Added stable route and glass selection snapshots so the initial Airport / All Glass state survives asynchronous choice rendering and exact glass filters work on first selection.
- Removed active-preset coupling from live glass selection state; applying a preset remains explicit while later manual filter changes remain authoritative.
- Reorganized Create Preset into complete desktop, medium, and mobile grid areas with Attention, Glass Types, and Output Settings using all available space.
- Added a lightweight Lookup Manager product-library prefetch and immediate modal enrichment without restoring historical delivery-list requests.
- Uses every Lookup Manager product value as an exact glass option while displaying its maintained friendly product-name label and searching both value and label.
- Centralized adoption of Lookup Manager payloads so Print / Export and Manual Delivery List Edit share the same normalized library state.
- Preserved schema version 5 and advanced the application contract, visible version, cache keys, documentation, and structure tests to v0.207.

## v0.206 - Compact Print Controls, Instant Preset Builder, and Calendar Repair

- Reduced Delivery Date, Create Preset, Saved Presets, and Clear Filters from oversized equal-width controls to compact, purpose-sized controls on one aligned desktop row.
- Added controlled wrapping and two-column mobile behavior without allowing the four controls to expand unnecessarily.
- Rebuilt the Create Preset GUI with a polished header, guided preset-name card, clearer filter sections, improved output settings, and responsive footer actions.
- Added searchable glass-type choices inside the preset builder.
- Removed historical glass-type quantity totals from preset creation; presets now display and store glass-type labels only.
- Eliminated the preset modal's full-catalog network wait by collecting glass types from the active workspace, already-loaded list detail, and existing user presets.
- Fixed Custom Date Range immediately closing when selected from the detached enhanced dropdown menu.
- Preserved user-specific preset persistence, exact print sessions, PDF/XLSX/CSV output, live preview behavior, and schema version 5.
- Advanced the application contract, visible version, and Styles/JavaScript cache keys to v0.206.

## v0.205 - Consistent Header Controls, Range Calendar, and User Presets

- Standardized Delivery Date, Create Preset, Saved Presets, and Clear Filters to the same height, border, radius, typography, and hover treatment.
- Rebuilt Custom Date Range as a dedicated two-month Date From / Date To picker; removed the unused single-date calendar mode.
- Added working range restart, previous/next month navigation, today highlighting, outbound-date markers, and guarded Apply Range behavior.
- Kept one-click individual delivery dates in the header dropdown with Custom Date Range as its first option.
- Expanded preset creation to preload every glass type currently known across the active delivery-list catalog.
- Namespaced saved presets and active-preset state by signed-in user, with migration from the earlier browser-wide preset store.
- Reapplies the active user preset whenever Print / Export opens and keeps it selected until the user chooses another preset or clears filters.
- Preserved the v0.204 live preview repair, visual polish, exact item/order selection, direct PDF printing, copies, orientation, XLSX, and CSV behavior.
- Preserved schema version 5 and advanced the application contract and cache keys to v0.205.

## v0.204 - Print / Export Visual Polish and Preview Geometry Repair

- Fixed the delivery-list preview container expanding to an extreme off-screen width because a shrink-to-fit page stack contained percentage-width sheets.
- Replaced the competing parent-and-sheet preview transforms with one layout-aware zoom owner.
- Keeps portrait and landscape sheets centered, visible, and vertically scrollable inside the preview pane.
- Preserved the same sheet markup, grouping, pagination, and data used by the working Print List popup.
- Rebalanced the desktop Print / Export workspace to provide useful width to both filters and the document preview.
- Standardized filter cards, headings, helper text, chip sizes, selected colors, and long-label wrapping.
- Refined Delivery Date, preset, and Clear Filters controls to avoid overlap and cut-off labels.
- Polished the preview toolbar, document canvas, sheet framing, table readability, and output footer.
- Added safe wrapping for Copies, Layout, File Type, and the primary output action on narrower displays.
- Updated the visible footer version, application contract, cache keys, documentation, and structure tests to v0.204.
- Preserved SQLite schema version 5; no database migration is required.

## v0.203 - Print Layout Completion and Direct Preview Printing

- Moved Delivery Date into the Filters header with one-date choices and Custom date range as the first dropdown option.
- Kept the calendar GUI for custom ranges, including highlighted today, month navigation, and date-range selection.
- Rebuilt filter order as Route / Glass Type, Status / Attention, then exact order and item search at the bottom.
- Replaced Copies with a bounded increment control and Layout with exclusive Portrait and Landscape buttons.
- Added the same output controls to Create Preset and kept preset application synchronized with the main output controls.
- Removed asynchronous PDF preparation from the print click path so the print popup opens reliably under browser popup rules.
- Generates the PDF/print window directly from the exact loaded rows shown in the live preview.
- Added shared sheet pagination and markup for preview and printing: 21-row first pages, 23-row continuation pages, glass group headers, normal/Rush/remake sheets, notes, and checked-by fields.
- Applies `@page` portrait or landscape sizing to the real browser print dialog.
- Removed the Not found preview-reconciliation message while retaining exact authenticated sessions for XLSX and CSV exports.
- Improved exact search readiness by ensuring selected delivery-list detail is loaded before suggestions are generated.
- Preserved schema version 5 and advanced the application contract and cache keys to v0.203.

## v0.202 - Exact Print Sessions, Item Selection, and Output Presets

- Replaced the Print / Export preview reconciliation request with an authenticated POST contract that carries exact line-item IDs and list/order/item fallback keys.
- Added short-lived, same-user print sessions so Print, PDF, XLSX, and CSV consume the exact package validated by the live preview.
- Fixed valid browser previews failing to print because the older query-string reconciliation returned zero rows.
- Added smart item-level search results with separate Add Item and Add Order actions for order, item, customer, and Job Nr. matches.
- Added exact selected-item cards with individual removal while retaining whole-order selection and Clear All.
- Removed Date Range and exact order/customer choices from the Create Preset builder.
- Added file type, copy count, and portrait/landscape output settings to presets.
- Moved the compact preset controls into the Filters header immediately before Clear Filters.
- Added maintained copies and orientation selectors beside File Type.
- Replaced the page-number selector with a vertically scrollable stack containing every preview page.
- Added portrait and landscape page geometry to both the browser preview and the generated print document.
- Preserved schema version 5; no database migration is required.
- Advanced the application contract and global Styles/JavaScript cache keys to v0.202.

## v0.201 - Print Calendar, All Glass Semantics, and Preview Stability

- Reworked All Glass into a true unrestricted choice that deselects every exact glass type.
- Exact glass-type selections now clear All Glass, while clearing all exact choices restores All Glass.
- Fixed the live-preview gate that treated All Glass as zero selected glass types.
- Preserved a valid browser-built preview whenever backend reconciliation returns an empty or zero-piece package.
- Resized All Status and All Attention to match their neighboring filter buttons and kept them in the first grid position.
- Replaced the visible quick-date and start/end fields with a top-of-workspace calendar selector.
- Added Single Date and Custom Range calendar modes, month navigation, highlighted today, range highlighting, and outbound-list date markers.
- Kept the selected dates connected to presets, preview, print, PDF, XLSX, and CSV output.
- Advanced the application contract and Styles/JavaScript cache keys to v0.201 without changing schema version 5.

## v0.200 - Live Preview Repair, Preset Builder, and Unified Output Selector

- Fixed the Print / Export paper preview flashing valid rows and then reverting to zero printable rows.
- Preserved a valid local preview when a stale or mismatched backend reconciliation response returns no rows.
- Stopped sending exact Glass Type filters when every available glass type is selected.
- Added All Status and All Attention controls and selected them by default.
- Defined All Attention as unrestricted so ordinary rows without attention flags remain included.
- Removed the footer Reset Filters action and enlarged the top-right Clear Filters button.
- Replaced Save Preset with Create Preset.
- Added an editable preset builder for dates, routes, status, attention, glass types, and exact selected orders.
- Automatically applies a newly created preset after saving it.
- Replaced the split Export PDF control with the maintained custom output selector.
- Added PDF, Excel Workbook, and CSV options.
- Kept PDF paired with Print List and changed the primary action to Export List for XLSX and CSV.
- Added filtered package CSV export using the same backend package contract as print and XLSX.
- Advanced the application contract and Styles/JavaScript cache keys to v0.200 without changing schema version 5.

## v0.199 - Multi-Order Selection, Preset GUI, and Live Paper Preview

- Made selected Print / Export chips use white labels and counts for readable contrast.
- Replaced single free-text output filtering with a smart multi-order picker that searches order numbers, customer names, and Job Nr. values.
- Added a Selected Orders workspace with exact order metadata, individual removal, Clear All, and unavailable-order guidance after date or route changes.
- Added exact `ordersExact` filtering to live preview, print, PDF, and XLSX requests.
- Added a dedicated Save Current Filters GUI with preset summary, validation, and overwrite guidance.
- Moved Route choices into a vertical right-side rail inside the filter pane.
- Narrowed the preview panel and changed the paper preview to mirror the maintained printed delivery-list structure: glass group rows, Job Nr., Order Nr., Item Nr., Qty., Dimensions, Customer, Route, Check, and Notes.
- Added an immediate local live preview on every filter change, followed by exact backend reconciliation through `/api/print/package-preview`.
- Preserved the live paper if backend reconciliation fails, eliminating the blank preview state.
- Increased preview pagination to 18 printable rows and included Job Nr. in backend preview rows.
- Advanced the application contract and Styles/JavaScript cache keys to v0.199.
- No database migration is required; schema version 5 remains active.

## v0.198 - Route-First Print Filters, Quick Date, and Smart Search

- Removed the Stage section from the Print / Export control center and made Route the primary source selector.
- Added fixed Airport, Indian Trail, Greenville, CPU, and DTC route choices.
- Defined Airport as the complete selected Airport Outbound workload and destination routes as focused subsets of those outbound rows.
- Fixed the blank Route, Status, Attention, and Glass Type sections by replacing the undefined `printItemsForCountList` call with the maintained loaded item collection.
- Added explicit loading and error states so filter failures cannot appear as unexplained empty sections.
- Added a Quick Date selector that sets both ends of the date range to one available outbound delivery date.
- Made glass-type options recalculate from the current date and route scope.
- Added live smart order suggestions for partial customer names, partial or complete order numbers, and Job Nr. values.
- Added Job Nr., product, and source-ID matching to the shared backend search filter.
- Removed the second decorative header ring while retaining one subtle background accent.
- Preserved schema version 5; no database migration is required.
- Advanced the application contract and global Styles/JavaScript cache keys to v0.198.

## v0.197 - Print / Export Document Preview Control Center

- Rebuilt the Print / Export Delivery Lists modal to match the approved full-screen filters-and-document-preview layout.
- Added left-side Search, Date Range, Stage, Route, Status, Attention, and exact Glass Type controls.
- Added a live paged paper preview with page selection, zoom controls, and full-screen viewing.
- Added preview rows for order, item, customer, delivery date, pieces, glass type, dimensions, scan status, attention state, and route.
- Added shared backend filters for exact routes, scan statuses, attention states, and customer/order search.
- Added browser-local named filter presets plus Reset Filters and Clear All actions.
- Added the reference-style Export PDF split control while retaining XLSX as a selectable export format, with both outputs aligned to the exact live preview contract.
- Preserved schema version 5; no database migration is required.
- Advanced the application contract and changed global Styles/JavaScript cache keys to v0.197.

## v0.196 - Scanner Panel Date, Station, and Stage Header

- Moved the active Stage and Delivery Date selectors from the Scan page heading into the scanner panel header.
- Replaced the combined stage/date scanner title with a three-column context row: Stage selector, assigned station, and Delivery Date selector.
- Reduced Stage selector option text to the stage name only because the assigned station is now displayed separately in the center.
- Styled both selectors with transparent header surfaces that retain the existing accessible custom-dropdown behavior and delivery-date update marker.
- Preserved cross-date switching, list activation, stage permissions, hidden station selection, scan request metadata, and audit history.
- Added a responsive two-row layout for narrow scanner panels.
- Advanced the application contract and changed Scan/JavaScript cache keys to v0.196.
- No database migration is required; schema version 5 remains current.

### Changed files

- `README.md`
- `README_CHANGELOG.md`
- `index.html`
- `database/contract.py`
- `static/js/app.js`
- `static/css/scan.css`
- `tests/test_static_structure.py`

## v0.195 - Print / Export Filter Workspace and Exact Preview

- Removed the visible Station status from the Scan page heading and right-aligned the Delivery Date and Stage selectors.
- Preserved the hidden station selector and station profile elements so scan requests, permissions, station assignment, and audit history continue using the signed-in station.
- Rebuilt the Print / Export modal around dedicated stage, exact-glass, customer, order, and content filter cards.
- Added stage progress cards, glass search and mirror presets, whole-category glass selection, customer and order search, and Select all/Clear actions.
- Added exact JSON-backed glass, customer, and order selection filters so checkbox choices do not broaden into substring matches or break on commas in customer names.
- Removed the duplicate Selection Summary and retained one detailed Selection Preview.
- Added `/api/print/package-preview`, which summarizes the exact `get_print_package` output used by both print preview and XLSX export.
- Made Estimated Glass Pieces, printable rows, order/customer totals, normal/remake/Rush mix, and stage/glass/customer/order breakdowns reflect the final generated package.
- Added a red zero-result preview with `Selected filters yield 0 results.` and disabled output while no printable rows match.
- Keeps output disabled while the exact preview is calculating or unavailable so an earlier preview cannot authorize a newer filter combination.
- Advanced the application contract and changed Styles/Scan/JavaScript cache keys to v0.195.
- No database migration is required; schema version 5 remains current.

### Changed files

- `README.md`
- `README_CHANGELOG.md`
- `index.html`
- `server.py`
- `backend/store.py`
- `database/contract.py`
- `static/js/app.js`
- `static/css/styles.css`
- `static/css/scan.css`
- `tests/test_static_structure.py`

## v0.194 - Exact Manual Scans and Result Feedback Repair

- Required manual scans to match the complete six-digit order and item instead of falling through to three-digit suffix recovery.
- Applied exact manual matching to current-list scans, cross-date candidates, date hints, local mode, and Indian Trail receiving.
- Preserved tolerant suffix recovery for physical barcode scans.
- Restored green success and red failure backgrounds on the Last Scan card after page-specific CSS had overridden the shared status colors.
- Mapped successful delivery-date switches to the packaged positive `scan_success.wav` cue while keeping normal scans on `notification.wav`.
- Kept cross-date selection prompts on the warning cue until a scan succeeds.
- Removed the Action History tab and history loading from the All Scans GUI.
- Advanced the application contract and changed Scan/JavaScript cache keys to v0.194.
- No database migration is required; schema version 5 remains current.

## v0.193 - Guarded Cross-Delivery-Date Scanning

- Added cross-delivery-date matching to the maintained main Scan and Indian Trail receiving workflows without creating a second scanner implementation.
- Checks the selected list first, then searches only active, accessible lists in the same operational stage and configured date window.
- Automatically switches and scans one unique safe match while retaining the matched delivery date as the active selection.
- Added an operator selection window for multiple matches, Ask mode, completed lines, manual bay choices, and rack/outbound/destination safeguards.
- Shows candidate delivery date, stage, order/item, quantity progress, route, customer, current location, and safety guidance before a manual choice.
- Preserves existing duplicate, stage-access, outbound, transportation, Indian Trail, rack, bay, supervisor-override, undo/redo, and audit behavior.
- Clears an unavailable, closed, or destination-incompatible selected rack before applying a confirmed cross-date scan and explains why it was not preserved.
- Added Admin settings for Disabled, Ask before switching, and Automatically switch unique matches, plus configurable past/future search limits defaulting to 7 and 30 days.
- Added immutable audit records for match discovery, settings changes, and cross-date switches.
- Added a dedicated visual date-change notice and semantic `delivery_date_changed` cue using the existing `scan_warning.wav` asset.
- Advanced the application contract and changed Scan/Admin/JavaScript cache keys to v0.193.

### Changed files

- `README.md`
- `README_CHANGELOG.md`
- `index.html`
- `server.py`
- `backend/store.py`
- `database/contract.py`
- `static/js/app.js`
- `static/css/scan.css`
- `static/css/admin.css`
- `tests/test_static_structure.py`

### Database

- No database migration is required.
- Existing schema version 5 remains current.
- Shared settings use the existing `system_metadata` table.

## v0.192 - Unified Rack Transfers and Paged Action History

- Replaced the native rack-transfer destination selector with a high-layer custom chooser so the destination list cannot open behind the Individual Rack GUI.
- Reused the same rack-transfer GUI for whole-rack, delivery-date, and individual-item moves on both the Racks page and Individual Rack modal.
- Added a small visual gap between each delivery-date heading and its first order line in the Individual Rack workspace.
- Changed every Action History tab to server-side pagination with a hard maximum of 50 events per page.
- Added Previous and Next page controls while preserving search, user, action, and date filters.
- Added paged All Racks History with server-side rack-group and rack-range filtering.
- Applied the richer All Racks History event-card design to every GUI Action History tab.
- Restricted Edit Racks Action History to rack creation, rack editing, rack-set creation, and rack deletion events. Operational rack scanning and transportation actions remain in Racks History.
- Added SQLite migration 005 with immutable `audit_events_archive` storage and timestamp indexes. Events older than 30 days are copied into the logical archive and removed from active GUI history without weakening the append-only primary audit log.
- Updated the database contract to schema version 5 and application contract version 192.
- Advanced the application display and changed browser asset cache keys to v0.192.

### Changed files

- `index.html`
- `README_CHANGELOG.md`
- `server.py`
- `backend/store.py`
- `database/contract.py`
- `database/migrations.py`
- `static/js/app.js`
- `static/css/shell.css`

### Database

- Migration required: **005 - v192_action_history_archive**.
- The normal verified pre-upgrade backup process runs before applying the migration.

## v0.191 - Rack-Scoped Action History and Combined Racks History

### Individual Rack Action History

- Limited the Individual Rack Action History tab to the currently opened rack instead of showing actions from every rack.
- Rack-scoped matching now includes direct rack actions, item clears, scans, packing-list prints, rack transfers where the rack was the source or destination, and compatible outbound-override transportation events.
- Added the source rack, destination rack, order, item, and moved quantity to new individual-item transfer audit records so future investigations remain accurate from both sides of a move.
- Reloads the selected rack's history whenever its Action History tab is opened.
- Preserved the shared user, action, date, and text investigation filters from v0.190 and labeled the tab clearly as history for the selected rack only.

### Racks History control center

- Renamed the Rack Overview action from `Packing List History` to `Racks History`.
- Rebuilt that window with two maintained section tabs: `Packing List History` and `All Racks History`.
- Preserved immutable packing-list snapshots and the existing Open Snapshot workflow in the Packing List History tab.
- Added an All Racks History timeline covering rack scans, status changes, transfers, clears, recovery actions, rack setup changes, and packing-list print records.
- Added All Racks History filters for text search, user, action, rack group, inclusive rack-from / rack-through range, and inclusive date range.
- Rack-group options combine the live rack catalog with group names retained in historical audit records; rack ranges use natural rack-code order and include transfer events when either the source or destination rack matches.
- Added result counts, rack and rack-group badges, a one-click Clear Filters action, and Spanish translations for the new history controls.

### Compatibility

- SQLite remains the active/default backend.
- No database migration is required.
- No images, installers, launchers, database files, or unrelated project files are included.

## v0.190 - Action History Investigation Filters and Move Icon Hover

### Action History filters

- Added a shared investigation toolbar to every GUI that exposes an Action History tab, including Admin editors, Internal Rejects, Individual Racks, Old Bays, Rush Orders, Manage Bay Items, and Edit Bays.
- Added free-text search across action names, event details, users, entity identifiers, reasons, and displayed timestamps.
- Added exact User and Action dropdown filters populated from the loaded event history.
- Added inclusive From Date and Through Date filters using the operator's local displayed date.
- Added a live `shown / loaded` event count and one-click Clear Filters control.
- Increased each Action History load from the small recent-event sample to as many as 500 relevant audit events so the filters are useful for investigations.
- Preserved the latest-change summary and the full unfiltered count on each Action History tab.
- Added Spanish translations for the new filter controls and empty-result messaging.

### Individual Rack move control

- Replaced the whole-rack move icon's solid-blue hover state with a light-blue hover surface and dark directional glyph so the icon remains clearly visible.
- Applied the same readable hover treatment to delivery-date rack move controls.

### Compatibility

- SQLite remains the active/default backend.
- No database migration is required.
- No images, installers, launchers, database files, or unrelated project files are included.

## v0.189 - Individual Rack Grid Ownership and Tab-Bar Actions

### Individual Rack control center

- Corrected a cross-stylesheet grid conflict that placed the Workspace tabs and rack contents into separate implicit columns.
- Forced the Rack Overview header, tab/action bar, Workspace, and Action History into one full-width modal column.
- Moved Complete / Uncomplete Rack, Print Packing Slip, return controls, and the whole-rack move icon onto the far-right side of the Workspace / Action History tab bar.
- Restored the Rack Overview header to a clean full-width presentation with the status and close controls only.
- Added final shell-level ownership so later Racks and Bay stylesheet rules can no longer reset the rack workspace to row 2 or suppress its vertical overflow.
- Made the complete Workspace canvas the deliberate vertical scroll owner while allowing expanded delivery-date groups and order cards to grow naturally.
- Preserved a separate full-height scrollbar for Action History when its event list exceeds the available height.

### Compatibility

- SQLite remains the active/default backend.
- No database migration or backend replacement is required.
- No images, installers, launchers, database files, or unrelated project files are included.

## v0.188 - Individual Rack Tabs, Header Actions, and Scroll Restoration

### Individual Rack control center

- Moved Action History into a separate Workspace / Action History tab system matching the maintained administration GUIs.
- Kept the rack contents and Action History as peer workspaces so history no longer consumes space above the assigned-piece list.
- Restored one reliable full-height vertical scrollbar for the Individual Rack workspace, allowing every expanded delivery-date group and order to remain reachable.
- Added the same full-height scrolling behavior to the Action History tab when the recorded event list exceeds the available screen height.
- Moved Complete / Uncomplete, Print Packing Slip, return controls, and the whole-rack move icon into the right side of the shared Rack Overview header.
- Increased and rebalanced the header height so the status and close controls remain on the top row while rack actions sit directly underneath.
- Kept delivery-date move icons and individual-piece controls inside the rack contents workspace.

### Compatibility

- SQLite remains the active/default backend.
- No database migration or backend replacement is required.
- No images, installers, launchers, database files, or unrelated project files are included.

## v0.187 - Individual Rack Scroll and Header Consolidation

### Individual Rack details

- Restored a visible vertical scrollbar for the complete Individual Rack workspace.
- Delivery-date groups and every assigned order now expand to their full natural height inside that scrolling workspace.
- Removed the nested order-list viewport that could prevent expanded rack contents from becoming visible.
- Merged the duplicate inner rack/truck identity panel into the shared Rack Overview header so rack type, rack name, counts, status, and destination remain visible without consuming a second section.
- Removed the visible `Orders on this truck` / `Orders on this rack` heading without removing any grouped date or order data.
- Kept whole-rack and delivery-date move icons, packing actions, status controls, and Action History.

### Compatibility

- SQLite remains the active/default backend.
- No database migration or backend replacement is required.
- No images, installers, launchers, database files, or unrelated project files are included.

## v0.186 - Rack Date Group Expansion and Header Cleanup

### Individual Rack details

- Repaired the delivery-date accordion layout after the v0.185 transfer-panel removal left the rack workspace with an obsolete extra grid row.
- Expanded delivery-date groups now render every order and line item instead of clipping the group after the first visible order.
- Kept the Orders list as the only scrolling region so long racks remain usable without hiding date-group contents.
- Preserved the compact whole-rack and delivery-date move icons introduced in v0.185.

### Rack Overview

- Removed the Rack Pieces, Truck Pieces, and Active Racks statistic bubbles from the upper-right page heading.
- Kept Packing List History and Edit Racks as the only Rack Overview heading actions.

### Compatibility

- SQLite remains the active/default backend.
- No database migration or backend replacement is required.
- No images, installers, launchers, database files, or unrelated project files are included.

## v0.185 - Update Preview Placement, Permission Selection, User Layout, and Rack Move Icons

### Delivery List Management and Manual Edit

- Removed the New / Updated preview action from the Edit Delivery Lists window.
- Added the preview action to each changed delivery-date row in the main Delivery List Management card, directly to the left of Print / Export.
- The preview now combines every changed stage for that delivery date into one read-only review window.
- Manual Edit now displays `Remake` as the effective Process value when imported `RM` or `REMAKE` markers identify the piece, even when the stored process text is blank, Normal, or Standard.

### Roles and users

- Replaced the broken Create Role permission dropdown categories with always-visible grouped permission cards and working checkboxes.
- Kept Select All, Clear All, category counts, role validation, and existing-role permission editing intact.
- Expanded Add New User across the full available modal width.
- Removed the nested Existing Users scroll window so the complete User Access Management GUI uses one normal vertical scrollbar.

### Racks and packing history

- Removed the large whole-rack and delivery-date transfer sections from Individual Rack.
- Added one move icon beside the rack identity for moving all contents and one move icon beside each delivery-date group.
- Move icons open a compact destination selector and retain the guarded transactional transfer logic from v0.184.
- Removed Action History from Packing List Print History while leaving Action History available for other operational GUIs.

### Compatibility

- SQLite remains the active/default backend.
- No database migration or backend replacement is required.
- No images, installers, launchers, database files, or unrelated project files are included.

## v0.184 - Permissions, Rack Transfers, Update Preview, and GUI Repair Pass

### Print / Export and operational GUIs

- Corrected the Exact Glass Types accordion so category headers, selection controls, counts, and exact glass choices stay aligned without the large empty or malformed card layout.
- Refined the Internal Reject Control Center header, tabs, piece summary, quantity entry, reject fields, and fixed submission footer so its title and subtitle remain fully visible.
- Applied the maintained control-center polish to Individual Rack, Packing List Print History, and the Indian Trail In-Transit manifest.
- Prevented white hover flashes on Sign In and Packing List History actions.
- Centered the profile initials inside both sidebar profile circles.
- Constrained Rush missing-item cards to consistent operational heights and centered the Rush launcher icon.
- Removed the clipped Scan Flags marker animation that appeared as a tiny black dot at the right edge of the Flags column.

### Delivery-list update review

- Added a New / Updated preview action to Delivery List Management when the latest import batch contains changed lines.
- The preview groups exact new and updated items and shows order, item, job, customer, size, quantity, glass type, route, and workflow state.
- Added maintained backend lookup support for the newest delivery-list notice batch without changing the database schema.

### Rack transfers

- Added guarded whole-rack transfer from the Individual Rack Control Center.
- Added delivery-date group transfer so every active piece for one grouped date can be moved together.
- Validates every destination rule before any assignment moves, limits targets to open racks, safely merges an existing target line when necessary, and writes piece/line totals to audit history.

### Roles, users, lookups, and permissions

- Rebuilt the permission catalog around current delivery-list, Bay Map, rack, reject, reporting, automation, and administration responsibilities.
- Migrates legacy permission names to canonical maintained permissions while preserving compatibility for older frontend checks.
- Added functional role creation and repaired permission category expansion and selection.
- Repaired and polished Add New User validation, save status, error handling, and refresh behavior; the server now enforces a valid role and an eight-character minimum temporary password.
- Refined Lookup Manager icons and catalog cards and polished Reject Reasons and Break Locations content.

### Automation, filters, and language

- Corrected automation timestamps and delivery dates so two-digit or display-formatted values cannot be interpreted as year 2001.
- Expanded the Automation Control Center to use the available desktop viewport; only Import History results scroll inside that window.
- Repaired Manual Edit Remakes filtering to recognize both `REMAKE` and standalone imported `RM` markers while preserving the other maintained filters.
- Expanded Spanish translations for the current Print / Export, rack, packing-history, reject, role, user, lookup, automation, update-preview, and Rush workflows.

### Compatibility

- SQLite remains the active/default backend.
- Existing databases are preserved and no database migration is required.
- No images, installers, launchers, database files, or unrelated project files are included in the changed-files package.

## v0.183 - Compact Print, Rush Frame, and Reject Detail Refinement

- Refit Print / Export into a shorter desktop workspace that stays inside the available screen without main-column vertical scrolling.
- Reduced the header, command row, stage controls, glass-type categories, filters, summary rows, and final action area while preserving exact individual glass-type selection.
- Changed Exact Glass Types to a single-open-category accordion so the full document workspace remains visible and operators can still select precise glass types.
- Removed the inherited Rush panel padding that created the visible white outer frame around the colored header.
- Removed main Rush workspace scrolling on normal desktop displays and confined overflow to the missing-item results only when a loaded order contains more rows than fit.
- Shortened and rebalanced the Rush search, item-selection, and handling sections so the complete three-step workflow fits inside the modal.
- Removed Internal Reject Step 4 and kept the irreversible-action warning in the compact submission footer.
- Reused the maintained Administration-style section tabs for Add Reject and Action History.
- Moved Quantity Rejected beside Order Number and Item Number in the Identify Piece row and constrains it to the verified available quantity.
- Expanded Matched Piece Summary with piece dimensions, glass type, route, available quantity, scan progress, current/suggested bay, delivery date, customer, job, and active stages.
- Enriched the existing reject-match response with display-only piece details from the verified active delivery-list rows; no schema or migration change is required.

## v0.182 - Modal Geometry Repair and Internal Reject Control Center

- Rebuilt the Print / Export window into a contained two-column document workspace with exact-stage controls, exact glass-type categories, optional customer/order filters, a live selection summary, and a useful output preview instead of a large empty region.
- Corrected the Print / Export grid ownership that squeezed the configuration column and pushed the action area into an oversized blank panel.
- Corrected Rush, Manage Bay Items, and Edit Bays modal row ownership so the hero header, section tabs, and workspace each receive their own grid row.
- Removed the nested-frame appearance from Rush and kept all three Bay workflow windows inside one consistent rounded modal shell.
- Increased usable modal height, protected headers and tabs from clipping, and confined scrolling to the intended list/workspace regions.
- Refined Manage Bay Items into a wider job list plus a balanced selected-job workspace with contained actions and readable full job information.
- Refined Edit Bays into a wider non-horizontal-scrolling group editor with a stable Add New Bay Group command and contained individual-bay rows.
- Rebuilt Add Internal Reject as a four-step control center: Identify Piece, Matched Piece Summary, Reject Details, and Impact / Review.
- Kept delivery-date resolution automatic and retained the existing verified match, catalog, submission, reset, audit, and permission behavior.
- Added a live Print / Export selection summary without changing the existing print/export API contract.
- No database migration or backend replacement is required.

# File: README_CHANGELOG.md

## v0.181 - Bay Workflow Control Centers, Rush Priority, Reject Entry, Print Selection, and Statistics Polish

### Bay Map control centers

- Rebuilt the Old Bay Control Center with a larger working canvas, larger typography, clearer review cards, and a more readable filter and snooze workflow.
- Added Workspace and Action History tabs to Old Bays, Manage Items, and Edit Bays.
- Added Add Rush, Current Priority Work, and Action History tabs to the Rush window.
- Expanded Manage Items, added a status filter, increased the order-information area, and allowed the left results list to show complete order details without clipping.
- Expanded Edit Bays, removed normal horizontal scrolling, and changed new-group creation to an explicit Add New Bay Group action that opens the creation workspace only when requested.
- Polished the In-Transit Manifest with a stronger receiving header, clearer summary cards, refined rack and glass-type groups, and a larger contained table workspace.
- Removed Bay Availability, Assigned / Occupied, and Needs Attention summary cards from the Bay Map heading and extended the Bay Map title treatment across the reclaimed width.

### Rush-only priority management

- Renamed the Bay Map Rush / Remake launcher and workflow to Rush.
- Removed the Rush / Remake type selector; new work created from this window is always Rush work.
- Changed Current Priority Work to include only intentionally marked Rush items.
- Imported RM / Remake markers continue to work in remake filters and printing but no longer inflate the operator-managed priority-work count.
- Rush clearing now removes only Rush / SDI state and preserves an existing RM / Remake marker on the same item.

### Action history

- Added Bay-workflow action-history contexts for Old Bay snoozes and review actions, Rush changes, managed bay-item moves and clears, and bay/group configuration changes.
- Extended action-history access to the existing Bay Map operational permissions instead of requiring an Administration-only permission.

### Internal rejects

- Simplified Add Internal Reject to require Order Number and Item Number for lookup instead of manually entering a delivery date.
- Resolves the active delivery date and affected stages automatically.
- Shows a compact date choice only when the same order/item has more than one active delivery-date match.
- Polished the identify, verify, incident-detail, impact, and submit sections while preserving reject rollback and audit behavior.

### Print / Export and Home statistics

- Rebuilt Print / Export as a larger document workspace with clearer stage, exact-glass, optional-filter, and output controls.
- Glass categories now organize the list only; each exact glass type is selected independently, such as 1/4 Clear Annealed without automatically including 3/8 Clear Annealed.
- Retained an explicit All Glass Types control for full-list output.
- Applied a stronger visual hierarchy to the Home Statistics dashboard, including its header, range tools, KPI cards, remake summary, glass chart, stage breakdown, and scan-health cards.

### Compatibility

- Preserved normal remake flags and remake printing, Bay Scanner behavior, Old Bay timing, scan history, delivery-list data, reject history, permissions, and the production SQLite database.
- No database migration is required.

## v0.180 - Main and Rejects Integration with Manual Edit Glass Type Filters

- Added a Glass Type section to the Manual Delivery List Edit filter drawer.
- Populates glass choices from the product/glass types that actually exist in the selected delivery-list stage.
- Displays the current piece quantity for each glass type.
- Supports selecting multiple glass types with OR logic inside the group and AND logic with progress, route, location, attention, and text-search filters.
- Keeps the stage's glass choices available when other filters return zero matching rows.
- Refreshes glass choices whenever the selected delivery-list stage changes.
- Integrated the Rejects feature line back into main while preserving main's
  Bay Scanner, Old Bay attention, Current Priority Work, footer, and timed scan
  feedback changes.
- Resolved the two branches' independent release numbering into one sequential
  `0.###` history without replacing the production database.
- No database migration is required.

## v0.179 - Manual Edit Exact Row Capture Repair

- Changed Manual Edit Save to use the exact expanded card containing the clicked Save button instead of querying the entire document by line-item ID.
- Added an original-value snapshot to every editable card and compares it with the current visible controls before saving.
- Captures the current Route, Location, Process, Product, order, item, customer, quantity, dimensions, and job values synchronously before the request.
- Sends the browser-detected changed fields with the save request for verification.
- Prevents a server no-change response from rerendering the result list and erasing the operator's unsaved values.
- Keeps the row open and reports a clear error when a detected edit is not confirmed by the server.

## v0.178 - Manual Route Save and New Order Workspace Repair

- Fixed manual-edit choice fields using a stale hidden mirror instead of the value currently displayed in the dropdown.
- Route saves now send an explicit override and store Indian Trail as `INDIAN TRAIL`, preventing CPU inference from undoing the operator's choice.
- Normalized route comparisons across sibling stage copies and exposed the applied route in the save response.
- Rebuilt the Manual Edit layout so Create New Order has a dedicated non-shrinking row and loaded results scroll independently.
- Added bounded scrolling to the expanded New Order card on shorter screens.

## v0.177 - Manual Route Corrections and Functional Admin GUI Tabs

- Fixed manual CPU-to-Indian Trail route changes being normalized back to the legacy inferred `IT` fallback.
- Stores explicit Indian Trail manual routing, synchronizes workflow copies, moves the receiving record, and returns the verified updated row.
- Keeps a just-saved row visible and expanded when it no longer matches active filters.
- Added green scanned-row styling and clear Scanned / Not scanned status badges.
- Moved the Manual Edit filter drawer to a viewport-level overlay so it remains fully visible with empty or short result sets.
- Replaced the pink Administration palette with navy and blue surfaces.
- Restored meaningful Workspace and Action History tabs to every Admin editor, including Edit Racks.

## v0.176 - Verified Manual Editing, GUI Action History, and Timed Rack Overrides

- Corrected Manual Delivery List Edit so one logical item is reported as one update even when its workflow-stage copies are synchronized.
- Saves now reload and verify every affected delivery-list stage before showing success.
- Added Scan-style filters for progress, route, location, remakes, rushes, updates, internal rejects, and manual entries.
- Added a persistent Create New Order toolbar action that remains available after loading more rows.
- Added real expandable Action History to each maintained Admin and Rack/Operations GUI.
- Added a configurable 1-120 minute mixed-destination rack override window under Bay Scanner Rules, defaulting to 15 minutes.
- Once one rack-destination mismatch is approved, additional destination combinations can be scanned into that rack until the window expires.

## v0.175 - Simplified GUI Headers and Automation Action

### Shared editor headers

- Removed the decorative selected workspace tab, Live scanner data tab, and Changes are audited tab from regular Administration editors.
- Removed the matching decorative context rail from Individual Rack and Packing List History Operations windows.
- Converted both shared modal systems to a simpler two-row layout: polished hero header plus scrollable editor canvas.
- Left the Delivery Automation Control Center's functional Run Manually, Automatic Schedule, Status & Logs, and Import History tabs unchanged.

### Delivery List Management action

- Moved the automation launcher into the Delivery List Management heading actions, immediately left of Edit delivery lists.
- Renamed it to Edit automated DL import and changed it to the maintained blue text-button treatment.
- Preserved the existing permission check and Automation Control Center open behavior.

### Compatibility

- Preserved all editor forms, event handlers, API requests, permissions, automation settings, and database behavior.
- No database migration or backend update is required.

## v0.174 - Modal Hidden State and Close Repair

### Startup and close behavior

- Fixed the shared Admin Control Center window being visible immediately when the web app loaded.
- Restored the X button and backdrop close behavior by ensuring the modal-specific grid rules cannot override the native `hidden` attribute.
- Applied the same hidden-state protection to the Operations window used by Individual Rack and Packing List History.
- Cleared stale modal content after closing so a previously opened editor cannot remain painted or replace a supposedly closed permanent window.
- Removed the Operations Control Center presentation class on close and synchronized `aria-hidden` state for both panels and backdrops.

### Compatibility

- Preserved every editor workflow, permission check, API request, unsaved manual-edit confirmation, rack operation, and database behavior.
- No database migration or backend update is required.

## v0.173 - Scan Typography and Control Center Layering Repair

### Scan-row readability

- Unified the Scanned pill label, date, time, separators, and station on one centered baseline with one readable font size.
- Increased Flags, Route, Location, and Progress text from the overly compact v0.169 sizes while preserving the maintained column widths.
- Corrected the missing semicolon in the Location width declaration so the browser consistently honors the complete fixed-width table contract.

### GUI layering and contrast

- Made the Administration Control Center header, context rail, and editor canvas explicit protected grid rows.
- Applied the same layer ownership to Individual Rack and Packing List History Operations windows.
- Prevented generic modal header rules from squeezing the status pill and close button into a narrow column.
- Increased and protected the close controls, constrained long status labels, and forced readable high-contrast hero text.
- Kept editor content beneath the header and context rail instead of allowing it to visually cover either surface.

### Compatibility

- Preserved every existing editor layout, event handler, permission check, API request, rack action, and scan record.
- No database migration, backend update, or JavaScript replacement is required.

## v0.172 - Scan Timestamp, Rack Status, and Rack Control Centers

### Scan-page presentation

- Condensed last-scan dates to month/day and times to a compact lowercase format such as `4:30pm` while preserving the full timestamp in hover text.
- Reserved the in-row scan-pill space only in the Job Nr. cell so Order and Item remain vertically aligned with QTY, Dimensions, Customer, Flags, Route, Location, and Progress.
- Added the active delivery-list date to the Scan panel title beside the stage name.

### Rack status integrity

- Removed the generic selected class from individual rack cards.
- Kept selection state available through `aria-current` while preserving Open, Complete, On the Way, Received, and Empty visual formatting.

### Rack GUI Control Centers

- Added the Administration-style Control Center hero, live-status pill, context rail, guided canvas, and section-card treatment to Individual Rack and Packing List History windows.
- Added dynamic rack context and status labels to the Individual Rack header.
- Strengthened Edit Racks, Rack, and Rack Set Admin editor surfaces without changing their existing forms or event handlers.

### Compatibility

- Preserved existing API calls, permission checks, rack actions, packing-list snapshots, scan data, and database behavior.
- No database migration or backend update is required.

## v0.171 - Administration Control Center GUI System

### Shared Admin window format

- Rebuilt the shared Administration modal around the same structural design language as the Delivery Automation Control Center.
- Added a descriptive navy hero, task-specific eyebrow, explanatory copy, live-status pill, and a workspace context rail.
- Added maintained profiles for Delivery Lists, Delivery List Actions, Manual Edit, Users, Roles, Sessions, Stations, Customer Routes, Customer Emails, Lookups, Reject Settings, Bay Scanner Rules, Bay Auto Assigner, Racks, Rack Sets, and All Scans.

### Editor consistency

- Standardized the working canvas, section cards, headers, tables, search controls, forms, list rows, empty states, and command/footer areas.
- Expanded data-heavy Admin editors while preserving responsive full-screen behavior on narrow displays.
- Kept all existing editor-specific layouts and workflows instead of replacing them with one generic form.

### Compatibility

- Preserved all existing IDs, delegated event handlers, API calls, permission checks, unsaved-change protection, editor refreshes, and database behavior.
- No database migration or backend update is required.


## v0.170 - Admin Editors, Scan Panel, and Automation Compatibility

### Page alignment and Scan panel

- Moved the Home Delivery List Overview text away from the decorative header accent.
- Aligned the Admin header, KPI cards, and dashboard sections to the same full-width grid edge.
- Restored the main Scan panel's navy progress header after the v0.169 surface rule incorrectly treated it as a white content card.
- Re-established distinct bordered cards for transportation, bay override, barcode entry, manual scan, manual assignment, and scan history.

### Administration editor polish

- Added a consistent purple Admin modal header, larger working canvas, refined backdrop surface, and stronger form/table hierarchy.
- Applied the shared editor treatment to Delivery List Management, Manual Delivery List Edit, Roles & Permissions, User Access Management, Customer Routes, Customer Email Rules, Lookup Manager, Reject Reasons & Locations, Bay Scanner Rules, and Bay Auto Assigner.
- Preserved all existing HTML IDs, event handlers, API requests, permissions, and editor workflows.

### Automation compatibility

- Added thin root-level `scanner_config.py` and `delivery_store.py` compatibility bridges for installed automation created before the v151 backend organization.
- Both bridges re-export the maintained `backend.config` and `backend.store` implementations; no database or business rules are duplicated.
- This resolves legacy scanner-root checks that reported the organized project was missing the old root module filenames.
- No database migration is required.

## v0.169 - Core Page Visual Polish and Scan Table Refinement

### Scan table geometry

- Reduced the in-row Last Scan pill so it ends at the Item column.
- Condensed Flags, Route, and Location to smaller production-safe widths while keeping markers, route labels, and rack controls contained.
- Reallocated the recovered width to Job Nr., Dimensions, and Customer.
- Replaced the two-pixel table clearance workaround with an exact 100% column contract.
- Removed the exposed white strip after Progress and removed the final cell's right border so the table meets the panel edge cleanly.

### Cross-page visual polish

- Added a shared professional hero treatment to Home, Scan, Racks, and Admin using each page's own accent color.
- Refined page backgrounds, panel hierarchy, borders, radii, shadows, typography, section headings, controls, and hover/focus feedback.
- Polished Home delivery progress, finder controls, list cards, and statistics surfaces.
- Polished the Scan command area, filter/table surfaces, row groups, compact operational columns, and scanner cards.
- Polished Rack set navigation, rack cards, detail panels, statuses, and management controls.
- Polished Admin KPI cards, management panels, tables, forms, lists, and last-updated status.

### Compatibility

- No JavaScript, backend, API, database, permission, reject-management, scanning, rack, or bay behavior changed.
- Advanced only the five changed stylesheet cache keys to `20260729-v158`; the unchanged JavaScript bundle remains on v157.

## v0.168 - In-Row Scan Pill and Progress Column

### Scan-page line presentation

- Replaced the separate Last Scan ribbon with a small scan-information pill inside the normal line-item row.
- Anchored the pill to the Job Nr. cell and allowed it to paint across Order, Item, QTY, Dimensions, and Customer without creating or resizing table columns.
- Kept date, time, and station on one compact line with ellipsis protection for long station names.
- Preserved QTY as a plain centered whole number.

### Headers and width containment

- Renamed the Scan table headers from Item Nr. to Item and Process State to Progress.
- Rebalanced the fixed table contract to give Progress more room.
- Reserved two physical pixels and one percentage point inside the table so the final Progress edge is not clipped by the list panel.
- Kept Internal Reject and future supplemental ribbons contained within the maintained table width.
- No backend, API, permission, database, reject-management, scan-history, rack, or bay behavior changed.
- Advanced only the Scan stylesheet and application JavaScript cache keys to v157.

## v0.167 - Scan Time Ribbon and Plain Quantity

### Scan-page line presentation

- Replaced the QTY pill with a plain centered integer while preserving scanned-versus-total information in the cell tooltip.
- Removed the long `Scanned: date/time - station` line from the Job Nr. column.
- Added a compact blue Last Scan ribbon above each scanned line item.
- Displays the date, time, and station in one readable line rather than multiple narrow information cells.
- Keeps the scan ribbon inside the same Job Nr.-through-Customer six-column span used by Internal Rejects.

### Width safety and compatibility

- Added one reusable detail-ribbon containment contract for scan-time, Internal Reject, and future warning/audit ribbons.
- Supplemental ribbons cannot create new table columns, minimum widths, or horizontal overflow.
- Preserved the v0.166 fixed percentage-based table contract, location containment, process wrapping, and flag containment.
- No API, database, permission, reject-management, scanning, rack, or bay behavior changed.
- Advanced only the Scan stylesheet and application JavaScript cache keys to v156.

## v0.166 - Reject Ribbon Simplification and Scan Table Containment

### Internal-reject ribbon

- Removed Delivery Date from the Scan-page reject ribbon.
- Removed the trailing event-count and investigation-note capsules.
- Increased the remaining Reason, Machine / Location, Qty, Rejected By, and Incident typography.
- Kept the ribbon limited to Job Nr. through Customer and allowed it to wrap responsively at narrower widths.

### Scan table width safety

- Replaced automatic table sizing with a maintained 100% percentage-based column contract.
- Removed the hard 118-pixel minimum from the Location column.
- Constrained long scan timestamps, process labels, flags, location selectors, badges, and ribbon content to their assigned columns.
- Prevented current and future row-detail ribbons from enlarging the delivery-list panel and producing horizontal page scroll.

### Compatibility

- No backend, API, permission, database, or reject-history behavior changed.
- Advanced only the Scan stylesheet and application JavaScript cache keys to v155.

## v0.165 - Admin Reject Management and Scan Ribbon Polish

### Admin-only reject management

- Added Edit and Delete actions to each Reject Timeline incident for the built-in Admin role only.
- Enforced the Admin role independently on the server for `/api/rejects/update` and `/api/rejects/delete`; UI visibility is not treated as authorization.
- Edit Reject updates reason, machine/location, rejected quantity, incident date/time, and investigation notes while keeping the affected order/item identity and original creator immutable.
- Delete Reject removes the selected reject event and recalculates cumulative line-item reject flags from remaining events.
- Editing or deleting a reject intentionally does not replay, restore, or reverse the original scan, rack, bay, or process rollback.
- Added append-only audit records for both edits and deletions, including the prior reject data and recalculated line summary.

### Scan-page reject awareness

- Rebuilt the internal-reject ribbon as a compact polished strip above the affected line item.
- Limited the ribbon to the Job Nr. through Customer columns so Flags, Route, Location, and Process State retain their normal table alignment.
- Added reason, machine/location, rejected quantity, rejected user, incident time, delivery date, event count, and investigation-note status.
- Expanded the line-flags response with current reject event details and separated cumulative rejected-piece quantity from reject-event count.

### Compatibility

- No database migration is required.
- Existing reject creation, scan reduction, rack removal, bay clearing, notifications, catalog management, and Reject Timeline filtering remain unchanged.
- Advanced only the changed Rejects, Scan, and application JavaScript cache keys to v154.

## v0.164 - Old Bay Attention and Priority Work Management

### Old Bay attention

- Replaced the automatic Old Bay modal opening with a timed orange notice shown when a user enters Bay Map.
- The notice reports the number of unique old orders needing review and provides a Review action that opens the existing Old Bay Control Center.
- Limited the notice to once every six hours per signed-in username using the existing server-side system metadata, so the timing follows the user across browser sessions and workstations.
- Added an orange attention-count badge to the top-right of the Old Bays button.
- Preserved existing search, age filters, selection, printing, and individual/bulk snoozing inside the Old Bay GUI.

### Current priority work

- Reorganized Current Priority Work into collapsible priority-date ribbons with nested job/order ribbons.
- Added search and Rush/Remake type filters with a live visible-item count.
- Added Edit and Remove actions for individual marked items.
- Added Edit Order and Remove Order actions for each grouped job/order.
- Added a guarded Clear All action for all current Rush/Remake work.
- Editing reuses the maintained Rush/Remake form and loads the existing type, priority date, truck handling, bay, and available reason details.

### Compatibility

- Preserved Old Bay aging and snooze rules, Rush/Remake endpoints, permissions, bay assignments, delivery lists, scan history, and database schema.
- Extended the existing stale-bay response with an atomic per-user six-hour alert claim; no new table or column is required.
- Extended the existing SDI workspace payload with current priority handling details and removed the former 100-group display cap so Clear All covers every current priority group.
- No migration, installer, BAT file, image, or database replacement is required.
- Advanced the changed Bay Map CSS and application JavaScript cache keys to v0.164.

## v0.163 - Footer Bug Reporting and Version Display

### Global footer

- Removed the Home and Settings actions from the desktop footer.
- Added a right-aligned **Report Bugs** action that opens a pre-addressed email to the maintained project contact with a structured bug-report template.
- Added a compact application-version badge showing **0.163** beside the bug-report action.
- Standardized maintained release numbering to the `0.xxx` format; the previous release is therefore identified as **0.162**.
- Preserved the application identity, active-scanner indicator, corrected footer grid placement, dark background, and responsive behavior.

### Compatibility

- No page-navigation, scanning, Bay Map, backend, database, permission, or API behavior changed.
- No migration, installer, BAT file, JavaScript change, image, or database replacement is required.
- Advanced only the shared shell stylesheet cache key to v0.163.

## v0.162 - Footer Grid Placement Correction

### Global footer

- Fixed the polished desktop footer being auto-placed into the collapsed sidebar grid column, which squeezed its content vertically and allowed the sidebar to cover it.
- Added an explicit third application-shell row and placed the footer in the main content column beneath the page.
- Preserved the dark operations background, application identity, active-scanner indicator, Home and Settings actions, and mobile behavior.
- Added responsive placement so the footer uses the single content column after the desktop sidebar becomes the mobile drawer.

### Compatibility

- No scanning, Bay Map, backend, database, permission, or API behavior changed.
- No migration, installer, BAT file, image, or database replacement is required.
- Advanced only the footer stylesheet cache key to v162.

## v0.161 - Footer Ownership, Bay Barcode Recovery, and Timed Scan Errors

### Global footer

- Moved the desktop footer into a dedicated last-loaded shell stylesheet so page-specific CSS can no longer clear, fade, mask, or replace its dark operations background.
- Preserved the application identity, active-scanner surface, Home and Settings actions, and mobile footer behavior.

### Bay Scanner matching

- Fixed Bay Map Add mode searching only the newest Indian Trail delivery list when no list was explicitly selected.
- Bay Map now searches every active Indian Trail destination list and binds a successful scan to the uniquely matched delivery date and line item.
- Expanded alternate labels such as `43273429.5` and `43273429.30` to match the stored order number as well as barcode, source identity, Job Nr., and item number.
- Preserved ambiguity protection so the scanner reports a clear correction instead of moving the wrong piece.
- Kept the combined manual Order + Item formats from v0.160 and routed them through the corrected cross-date Bay matching path.

### Timed scan failures

- Added one shared timed top-of-screen error card for Bay Scanner barcode entry, Bay manual entry, Scan-page barcode entry, and Scan-page manual entry.
- The timed card shows the entered value and exact validation or backend error so operators can correct a scan without relying on a brief inline message.
- Changed missing manual scan fields and missing Indian Trail bay selection into surfaced scanner errors instead of silent returns or short floating notices.

### Compatibility

- Preserved Bay Add/Remove behavior, outbound safety overrides, assignment history, recent scans, All Scans pagination, seven-day Bay activity retention, permissions, and database schema.
- No migration, installer, BAT file, database replacement, or server-route change is required.
- Added `static/css/shell.css` as the final shared-shell owner and advanced only changed asset cache keys to v161.

## v0.160 - Global Footer, Flexible Bay Entry, External Barcode Support, and Selected Bay Polish

### Global application footer

- Rebuilt the non-page-specific desktop footer as a solid operations bar so the bottom of the web app no longer appears faded.
- Added a compact application identity, active-scanner status surface, and polished Home and Settings actions while preserving the existing scanner name and navigation behavior.

### Bay Scanner manual entry

- Replaced the separate Order Number and Item Number controls with one aligned Order + Item field and Submit action.
- Accepts compact and separated formats including `236505001`, `236505 1`, `236505.1`, and `236505/1`.
- Added Enter-key submission and strict validation that rejects ambiguous values instead of guessing.

### Alternate product barcodes

- Added Bay Map Add and Remove matching for alternate product labels such as `43273429.30`.
- Matches exact stored barcode, source identity, or Job Nr. values and can resolve a dotted job/item label against the item number.
- Uses unique highest-confidence matching and reports ambiguous labels rather than moving the wrong piece.

### Selected Bay GUI

- Added a polished Indian Trail header, stronger modal framing, improved content spacing, and clearer card depth to the individual Selected Bay window.
- Preserved all existing fulfillment details, scanner targeting, bay status actions, job expansion, item movement, and close behavior.

### Compatibility

- Preserved Add/Remove workflows, recent-scan limits, sticky scanner behavior, seven-day Bay activity retention, All Scans pagination, permissions, and database schema.
- No migration, server-route change, installer, BAT file, image, or database replacement is required.
- Advanced only the changed global stylesheet, Bay stylesheet, and application JavaScript cache keys to v160.

## v0.159 - Bay Map Edit Header Cleanup and All Scans Visual Polish

### Edit Physical Bay Map

- Removed the unused Close button from the top-right of the Edit Physical Bay Map header.
- Kept Cancel as the intentional way to leave edit mode without saving and Save Layout as the deliberate commit action.
- Removed the obsolete JavaScript element binding, click listener, and button-specific stylesheet rule instead of leaving dead ownership behind.

### All Bay Scans

- Rebuilt the paginated All Bay Scans window with the same restrained operations-console polish used by the Bay Map action workflows.
- Added a dark Indian Trail activity header, seven-day retention summary, total-scan and current-page metrics, and clearer location-correction guidance.
- Improved sticky table headers, alternating rows, status accents, action/current-bay/user pills, hover readability, and the Change Location control.
- Polished the 25-row pager, empty state, loading state, and retryable failure state without changing server-side pagination or retention behavior.
- Prevented the All Scans custom modal style marker from leaking into subsequently opened Admin windows.

### Compatibility

- Preserved Bay Scanner follow behavior, recent-scan limits, seven-day Bay activity cleanup, 25-row server pagination, location correction permissions, APIs, and database schema.
- No backend, migration, installer, BAT, image, or database change is required.
- Advanced only the Bay Map stylesheet and application JavaScript cache keys to v159.

## v0.158 - Expanded Fullscreen Bay History and Operations UI Polish

### Bay Scanner history

- Increased fullscreen Recent Bay Scans by two rows for both workflows.
- Fullscreen Add to Bay now shows up to five recent movements, and fullscreen Remove from Bay shows up to six.
- Preserved the normal-window limits of one Add movement and two Remove movements.
- Increased the initial Bay Map event request to six retained movements so every fullscreen row is available without another request.

### Bay Map workflow presentation

- Reworked the Old Bays through Edit Map launcher into five consistent operational cards with distinct restrained accents, stronger icons, clearer depth, and improved hover/focus feedback.
- Polished the Rush / Remake window with a priority-colored header, stronger step cards, clearer form hierarchy, and more deliberate primary/destructive actions.
- Polished Manage Items with a clearer split workspace, stronger selected-item summary, improved assignment rows, focused fields, and semantic Move, Clear, Scanner, and Rush actions.
- Polished Edit Bays with a stronger editor header, clearer group navigation, refined forms and bay cards, and improved focus/selection states.
- Polished Edit Physical Bay Map with a dedicated map-edit header, organized tool strip, clearer Save/Cancel actions, and refined drag columns, group cards, and drop zones.

### Compatibility

- Preserved Bay Scanner follow behavior, Add/Remove logic, All Scans pagination, seven-day Bay activity retention, assignment rules, APIs, permissions, and database schema.
- No backend, migration, installer, BAT, or database change is required.
- Advanced only the Bay Map stylesheet and application JavaScript cache keys to v158.

## v0.157 - Adaptive Bay History Loading and Preassignment Move Safety

### Bay Map scanner

- Fixed Recent Bay Scans remaining at one row because the normal Bay Map refresh requested only one retained event from the paged history endpoint.
- The compact scanner now loads the newest four retained movements once, then applies the existing mode-aware limits locally: Remove shows two and Add shows one in a normal window; fullscreen Remove shows four and fullscreen Add shows three.
- Preserved immediate recent-history rerendering when the scan mode or fullscreen state changes.

### Bay assignment correctness

- Fixed moving a PreAssigned item to another bay changing its assignment status to Moved.
- A PreAssigned destination correction now remains PreAssigned, so a missing piece is not falsely counted as physically scanned into the destination bay.
- Physical Assigned/Moved rows continue to become Moved and remain counted as present.
- Added the previous and resulting assignment status to the maintained move audit payload.

### Compatibility

- Preserved the v0.155 seven-day Bay Map activity retention, 25-row All Scans pagination, read-only Latest Activity, scanner follow behavior, permissions, and database schema.
- No migration, server-route change, CSS change, installer, or BAT file is required.
- Advanced only the application JavaScript cache key to v157.

## v0.156 - Bay Scanner Fixed-Width Follow and Adaptive Recent History

### Bay Map scanner

- Corrected the fixed-follow controller so the Bay Scanner keeps the exact measured right-rail width instead of inheriting a viewport-wide `width: 100%` rule after it becomes fixed.
- Added explicit fixed left/width CSS variables, viewport-edge clamping, border-box sizing, and automatic width recalculation on resize and fullscreen changes.
- Preserved the non-sticky Bay Map action toolbar, five-pixel viewport spacing, internal overflow, and normal-flow anchor height.
- Made Recent Bay Scans adapt to the active workflow: Remove shows up to two rows normally and Add shows one.
- In fullscreen, Remove shows up to four recent rows and Add shows up to three.
- Refreshes recent history immediately when Add/Remove mode or fullscreen state changes.

### Compatibility

- Preserved the v0.155 seven-day Bay Map activity retention, 25-row All Scans pagination, Latest Activity summary, location correction, scan workflows, permissions, and database schema.
- Advanced only the changed Bay Map CSS and application JavaScript cache keys to v156.

## v0.155 - Bay Scanner Sticky Follow, Latest Activity, and Paged History

### Bay Map scanner

- Replaced the unreliable nested CSS sticky behavior with one measured Bay Scanner follow controller.
- Keeps the Bay Map action toolbar in normal flow while fixing only the scanner after it reaches the usable viewport below the application header.
- Preserves the scanner's rail width, a five-pixel viewport margin, fullscreen behavior, and internal scrolling when its content is taller than the available screen.
- Rebuilt Latest Activity as a professional read-only summary with scan result, time, current bay, action, order, item, Job Nr., customer, user, and result details.
- Removed bay-location editing from Latest Activity and Recent Bay Scans; location correction now exists only in All Bay Scans.
- Kept Recent Bay Scans at one compact read-only physical movement.

### All Bay Scans performance and retention

- Changed All Bay Scans to open immediately with a loading state and request one server-side page at a time.
- Limited every page to a maximum of 25 events and added Previous, Next, and numbered page controls with total-result information.
- Added a seven-day Bay Map event retention window. Expired `bay_events` rows are deleted at startup and during throttled Bay Map history reads.
- The cleanup affects only Bay Map movement activity; delivery-list scan history, audit history, rack history, reject history, packing history, and import history remain unchanged.
- Kept active-item location correction in All Bay Scans through the maintained Bay Map move workflow.

### Compatibility

- Preserved Bay Scanner Add/Remove behavior, barcode and manual scanning, route progress, Undo/Redo, permissions, and existing Bay Map assignment APIs.
- No database schema migration is required.
- Advanced the changed Bay Map CSS and application JavaScript cache keys to v155.

## v0.154 - Bay Scanner Sticky Containing Block and Manual Row Alignment

### Bay Map scanner

- Restored sticky scrolling by making the Bay Map right rail stretch to the full map-row height while keeping the action toolbar in normal, non-sticky flow.
- Kept scanner stickiness active through compact workstation widths and disables it only for the true mobile layout.
- Kept the scanner directly beneath Edit Map with the maintained four-pixel normal-flow gap and a five-pixel sticky viewport offset.
- Added scoped overflow ownership to the Bay Map shell and right rail so an inherited overflow rule cannot disable sticky positioning.
- Replaced the Manual Scan label wrappers with direct Order Number, Item Number, and Submit grid children.
- Aligned all three Manual Scan controls on one 34-pixel row and reduced the section's vertical height.
- Left-aligned Item Number content while retaining its three-digit limit.
- Moved the Target Bay and Scan Barcode titles closer to their corresponding inputs.
- Advanced the Bay Map stylesheet cache key to v154.

### Compatibility

- Preserved Bay Scanner IDs, Add/Remove behavior, target selection, manual submission, Undo/Redo, route progress, history, APIs, permissions, and database schema.
- Changed only `index.html`, `static\css\bays.css`, and `README_CHANGELOG.md`.
- No JavaScript, backend, database migration, installer, BAT file, or global stylesheet change is required.

## v0.153 - Bay Scanner Sticky Ownership and Manual Row Correction

### Bay Map scanner

- Removed the extra Bay Scanner sticky wrapper and made the scanner panel itself the sticky element.
- Kept Old Bays, Rush / Remake, Manage Items, Edit Bays, and Edit Map in normal non-sticky document flow.
- Forced the scanner to follow Edit Map with only the maintained four-pixel right-rail gap in normal and sticky workflows.
- Eliminated the wrapper height and inherited grid-row behavior that repeatedly left a large blank area above Bay Scanner.
- Replaced the older v150/v151 Manual Scan layout selectors with an isolated v0.153 one-row owner.
- Kept Order Number and Item Number as in-field placeholders with hidden accessible labels.
- Aligned Order Number, Item Number, and Submit on one 36-pixel control row and reduced the Manual Scan section height.
- Advanced the Bay Map stylesheet cache key to v153.

### Compatibility

- Preserved Bay Scanner control IDs, Add/Remove behavior, manual submission, route progress, history, APIs, permissions, and database schema.
- Changed only `index.html`, `static\css\bays.css`, and `README_CHANGELOG.md`.
- No JavaScript, backend, database migration, installer, BAT file, or global stylesheet change is required.

## v0.152 - Bay Scanner Manual Alignment and Content Fit

### Bay Map scanner

- Moved the Manual Scan Order Number and Item Number labels into their respective input fields as placeholders while retaining accessible hidden labels.
- Aligned Order Number, Item Number, and Submit on one consistent 42-pixel control row.
- Increased the Item Number field and Submit button widths while preserving the wider flexible Order Number field.
- Removed the forced full-viewport scanner height so the panel ends directly after Recent Bay Scans when its content fits.
- Preserved the sticky viewport height limit and internal scrolling when the scanner content exceeds the available screen height.
- Advanced the Bay Map stylesheet cache key to v152.

### Compatibility

- Preserved existing Bay Scanner IDs, manual submission behavior, Add/Remove workflow, target selection, recent activity, APIs, permissions, and database schema.
- Limited the release package to the files changed for this correction.
- No database migration, backend patch, installer, BAT file, or JavaScript change is required.

## v0.151 - Project Structure Organization and Bay Scanner Target Alignment

- Consolidated maintained browser behavior into `static\js\app.js`.
- Moved Rejects page, reject workflow, timeline, and internal-reject
  presentation rules from the global stylesheet into `static\css\rejects.css`.
- Organized application services under `backend` and database ownership under
  `database` while retaining `server.py` as the root launcher.
- Moved optional Docker and Azure App Service templates under `deployment`.
- Added the missing container dependency manifest for the Azure SQL adapter.
- Retained `.dockerignore`, `pytest.ini`, and the paired Windows launchers at
  the root because Docker, pytest, and the BAT launcher discover them there.
- Updated automation integration paths and project-structure validation.

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

## v0.150 - Bay Scanner Control Alignment and Status Refinement

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

## v0.149 - Bay Scanner Sticky Fit and Input Refinement

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

## v0.148 - Bay Scanner History and Flow Refinement

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

## v0.147 - Bay Scanner Route and Sticky Refinement

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

## v0.146 - Bay Scanner Workflow Refinement

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

## v0.145 - Bay Scanner Layout Correction

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

## v0.144 - Bay Scanner Operations Console Redesign

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

## v0.143 - Internal Reject Timeline Redesign

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

## v0.142 - Custom Roles and Interface Refinements

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

## v0.141 - User Access Management Redesign

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

## v0.140 - Attention Filters, Reject Controls, and Import Run Deduplication

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

## v0.139 - Dropdown Audio, Internal Reject Awareness, and Import Run History

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

## v0.138 - Internal Reject Page and Entry Workflow

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

## v0.137 - Bay Scanner Readability, Packing Lists, and Review Workflow

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

## v0.136 - Interface Stability and Professional Control Polish

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

## v0.135 - Personalized Update Review and Operations Workflows

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

## v0.134 - Floor Scheduler PowerShell Interpolation Fix

- Fixed `Install-DeliveryListSqlAutomationTasks.ps1` failing syntax validation at line 227 before Task Scheduler installation began.
- Delimited the automation-mode variable as `${automationMode}:` so PowerShell does not interpret the literal colon as part of the variable name.
- Preserved the existing `${incrementalTask}:` and `${fullTask}:` task-summary fixes.
- The floor setup still copies the runtime into `C:\DeliveryListAutomation\Scripts`, validates the installed PowerShell files, verifies scanner compatibility, and only then creates the hourly folder-import tasks.
- Existing scanner data, imported delivery lists, automation configuration backups, and SQL isolation remain unchanged.
- Advanced floor-setup and browser release markers to v134.

## v0.133 - Safe Windows Batch Launchers for Parenthesized Project Paths

- Fixed `Setup-Floor-Folder-Import-Automation.bat` opening briefly and closing before the PowerShell installer started when the project folder contained parentheses, such as `Delivery-List-Scanning-Project-main (5)`.
- Fixed the same CMD parser failure in `Create Desktop Shortcut.bat`.
- Rebuilt both launchers with label-based control flow instead of parenthesized command blocks that expanded project paths during CMD parsing.
- Quotes every project-derived path and keeps delayed expansion disabled so spaces, parentheses, ampersands, and common OneDrive folder names do not alter the command structure.
- Both launchers now always reach a visible success/failure screen and wait for a keypress before closing.
- Added `logs\floor-folder-import-setup-launch.log` and `logs\desktop-shortcut-launch.log` with the selected project/script paths and PowerShell exit code.
- Added `logs\floor-folder-import-setup-error.log` for unhandled PowerShell setup failures.
- Preserved the v132 folder-import-only runtime installation, hourly schedule, SQL isolation, scanner database, existing import configuration backups, and desktop-shortcut behavior.
- Advanced browser asset cache keys to v133.

## v0.132 - Floor Computer Hourly Folder-Import Setup

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

## v0.131 - Audited Route-Consolidation Preservation Validation

- Fixed floor database transfer validation stopping after a successful migration because `line_items` decreased from 15,096 to 15,068.
- Recognizes the maintained startup repair that merges obsolete duplicate receiving-stage route copies into one current destination row.
- Allows a lower raw `line_items` count only when every removed row is a receiving-stage row and has an explicit `merge_line_item_reference` audit record.
- Verifies an equivalent logical line item still exists for the same delivery date and barcode/source identity.
- Verifies the retained row has at least the same required quantity and scanned progress as every consolidated row.
- Continues to reject any missing Staging or Outbound row, unaudited deletion, missing logical item, reduced quantity, reduced scan progress, missing table, integrity error, or foreign-key violation.
- Records the number of safely consolidated rows and the semantic validation result in `transfer-report.json`.
- Preserves verified backups, failed-copy retention, and automatic restoration of the previous current-project database on any real validation failure.
- Advanced browser asset cache keys to v131.

## v0.130 - Complete Legacy v096 Schema Before Migration

- Fixed floor database upgrades reaching the current schema version and then failing during startup with `no such table: system_metadata`.
- Replays the canonical v096 schema creation method before migration 002 whenever the database has not yet reached v097.
- Uses the existing idempotent `CREATE TABLE IF NOT EXISTS` and missing-column helpers, so support tables and fields are added without recreating or replacing existing operational rows.
- Covers both unversioned legacy databases and databases that already contain a v096 baseline record but were created before all v096 support tables existed.
- Does not change any historical migration checksum or schema version.
- Preserves verified source/target backups, integrity checks, foreign-key validation, row-count checks, failed-copy preservation, and automatic target rollback.
- Corrected maintained release documentation that had remained labeled v128 after the v129 migration patch.
- Advanced browser asset cache keys to v130.

## v0.129 - Late-v096 Column Compatibility Repair

- Fixed the v097 migration failing with `no such column: priority_delivery_date` on older floor databases.
- Runs the maintained v096 compatibility preparation before migration 002 so `source_route`, `priority_delivery_date`, and `priority_direct_to_truck` exist before `line_items` is rebuilt.
- Supports both unversioned legacy databases and databases already marked with the v096 baseline.
- Preserved migration checksums, existing operational data, verified backups, validation, and rollback behavior.

## v0.128 - Windows Project-Root Quoting Fix

- Fixed the floor database transfer failing before the source prompt with a malformed current-project value ending in `" --interactive`.
- Normalizes the BAT project root to a full path without a trailing backslash before passing it as a quoted Python argument.
- Updated all launcher-relative paths to insert their own directory separator instead of depending on the trailing separator from `%~dp0`.
- Added a defensive Python compatibility repair for the exact malformed argument generated by already-extracted v127 launchers.
- Added regression coverage for the Windows quoting failure while preserving interactive path entry, verified backups, migrations, validation, and rollback behavior.

## v0.127 - Reliable Floor Database Transfer Launcher

- Moved the old-project/database path prompt from the BAT command parser into the Python transfer tool so pasted paths containing spaces, ampersands, parentheses, quotes, and other CMD-sensitive characters cannot terminate the launcher.
- Rebuilt the BAT as explicit non-nested execution labels for the project virtual environment, bundled Python, Windows Python launcher, and PATH Python fallback.
- Kept the transfer window open after success and every handled failure with a final keypress prompt.
- Added `logs\floor-database-transfer-launch.log` with the project root, selected Python runtime, and transfer-process exit code.
- Preserved drag-and-drop support through an environment handoff without embedding the pasted path in the Python command line.
- Added an interactive-path regression test using a folder name containing an ampersand while preserving the v126 backup, migration, validation, and rollback protections.

## v0.126 - Floor Database Transfer and Upgrade

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

## v0.125 - Safe Task Scheduler Native Command Handling

- Fixed schedule installation failing when `schtasks.exe /Delete` reported that an obsolete legacy task did not exist.
- Added one maintained Task Scheduler command wrapper that captures native stdout/stderr without allowing Windows PowerShell's `ErrorActionPreference = Stop` to convert expected `schtasks.exe` messages into terminating `NativeCommandError` records.
- Queries each obsolete task before attempting deletion, so a missing legacy task is treated as normal and schedule installation continues.
- Routes task deletion, creation, post-create verification, and the final launch test through the same exit-code-based command wrapper.
- Preserves detailed native command output when an actual task creation, verification, deletion, or launch error occurs.
- Added `Apply-v125-AutomationPatch.bat`, which backs up and replaces only the installed SQL task installer without touching configuration, scanner data, existing tasks, or generated workbooks.
- Kept the v123-v124 SQL/export/import verification, parser checks, timestamp fixes, and legacy-script compatibility repairs intact.
- Advanced browser asset cache keys to v125.

## v0.124 - Legacy Scheduler Parser Hotfix

- Fixed the remaining schedule-installation failure coming from the older `Install-DeliveryListAutomationTasks.ps1` file left in the shared installed automation Scripts folder.
- Delimited `${incrementalTask}:` and `${fullTask}:` in the legacy Crystal task installer so the file is valid Windows PowerShell.
- Narrowed the maintained SQL scheduler preflight from every `.ps1` file in the shared folder to the six current SQL automation entry points actually used for initialization, runs, installation, removal, status, and verification.
- Prevented retired or unrelated upgrade scripts from blocking installation of the current SQL scheduled tasks.
- Added `Apply-v124-AutomationPatch.bat`, which backs up and replaces both affected installed scheduler scripts without changing configuration, tasks, scanner data, or generated workbooks.
- Kept the v123 end-to-end SQL/export/import verifier and unchanged-list timestamp fixes intact.
- Advanced browser asset cache keys to v124.

## v0.123 - Schedule Installer Fix, Timestamp Persistence, and End-to-End Verification

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

## v0.122 - CSS Ownership Map and No-Change Import Timestamps

- Reorganized `styles.css` with a maintained table of contents and clearly labeled sections for global tokens, authentication, shell/header/sidebar, Home, Admin, Scan, shared components, Racks, Bay Map, compatibility layers, and current-release ownership.
- Preserved CSS source order so historical compatibility layers keep the same cascade and visual behavior.
- Removed eight verified exact duplicate qualified rules while leaving similar selectors with different values untouched.
- Fixed Delivery List Management result hydration so date-level **No Changes** results inherit every active stage for that delivery date instead of being filtered out for having no changed-stage rows.
- Carries the completed manual or automatic import timestamp into every hydrated stage row, keeping each Delivery List Management date group current even when the maintained importer performs no database rewrite.
- Reviewed the v106-v121 automation architecture, append-only import reconciliation, notification/review flow, and mirrored runtime/package assets.
- Corrected stale README references from the superseded Crystal export folder to the maintained `automation/sql_delivery_export` control center and setup entry point.
- Advanced browser asset cache keys to v122.
- Confirmed the root and `automation/sql_delivery_export` automation assets are intentional deployment mirrors rather than competing runtime implementations.

## v0.121 - Notification Timing and Review Reliability

- Moved the delivery-list import toast to the bottom center of the page and extended it to 20 seconds.
- Opening the bell notification menu now marks all currently displayed notifications read for that user.
- Removed the Mark all read control and the per-item Mark read wording from the notification menu.
- Stamps every delivery-list result from the newest run with the run completion time, including No Changes results and their stage details.
- Sends the exact reviewed notice IDs when Mark reviewed is selected and verifies that no unseen notices remain.
- Reloads the selected delivery list from the authenticated API after review and immediately removes New Line / Updated Line labels from the current user's visible rows.
- Preserved per-user isolation, current/future-date limits, append-only scan history, scanning quantities, racks, bays, and import audit history.
## v0.120 - Per-User Delivery-List Update Review

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
## v0.118 - Unified Import Center and Append-Only History-Safe Updates

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
## v0.117 - Live Delivery Management Refresh and Stable Import History

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
## v0.116 - Dedicated Import Audit History

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
## v0.115 - Non-Disruptive Live Delivery-List Synchronization

- Fixed the Admin page immediately redirecting to Scan when the v114 import-history refresh ran.
- Removed artificial Date and Stage change events from background catalog refreshes.
- Replaced the installed v114 bridge during upgrade so the redirecting code is not left behind.
- Added a silent delivery-list catalog refresh every 10 seconds for every signed-in browser and immediately after import completion.
- New dates and stages now appear without a browser reload while preserving the current page, selection, and active scanner input.
- Kept Recent Delivery List Imports connected to the latest maintained importer result and its New, Updated, New + Updated, No Changes, Failed, restored-stage, and piece-change details.
- Added bounded retry and backoff for transient SQLite/Azure SQL lock or busy conditions so active scanner writes are favored.
- Confirmed that SQL querying, workbook generation, validation, and network publishing do not write to the scanner database; only the final maintained import phase uses short transactions.
- Preserved scan quantities, routes, racks, bays, audit history, notifications, configuration, and scheduled tasks.
## v0.114 - Immediate Import History Refresh and Correct New-Stage Classification

- Fixed the automation refreshing the hidden legacy import-history element instead of the visible Recent Delivery List Imports section.
- Made the just-completed maintained folder-import result authoritative for New, Updated, New + Updated, No Changes, and Failed labels.
- Added per-stage result rows with added-piece, updated-piece, changed-piece, and changed-line details.
- Preserved stage summaries, reactivated counts, and restored-stage IDs through the import wrapper, run summary, recent-import API, and browser renderer.
- Added a browser-state bridge that refreshes delivery-list state and the Scan page date/stage selectors without a page reload.
- Fixed inactive or deleted stages being restored successfully but classified as No Changes; restored stages are now New.
- Prevented older imports-table rows for the same workbook/date from overwriting the latest run result.
- Retained Excel-compatible workbooks, integrity validation, missing-list recovery, complete logs, notifications, and UNC publishing.
- Preserved scans, routes, racks, bays, audits, configuration, and scheduled tasks.
## v0.113 - Workbook Integrity, Import Audit, and Deleted-List Recovery

- Fixed SQL-generated workbooks prompting Excel to repair the file and then opening without worksheet data.
- Moved worksheet properties into the SpreadsheetML order required by Microsoft Excel and added full OOXML ZIP, XML, relationship, style-count, and worksheet-order validation.
- Changed order, item, and quantity cells to native numeric cells while preserving the scanner-compatible A/F/G/J/L/N/V/X layout.
- Added a workbook format marker and published-file SHA-256 hash to each date state. Older, damaged, replaced, or repaired files are rebuilt automatically even when A+W data is unchanged.
- Changed SQL export-and-import mode to audit every source date while importing only changed, pending, or missing-list dates, allowing current No Changes results to appear without unnecessary reimports.
- Added a visible `Last checked` timestamp to Recent Delivery List Imports so a successful no-change automation run is distinguishable from a stale page.
- Preserved authoritative New, Updated, and New + Updated classifications from the scanner imports table while retaining newer No Changes and Failed runtime results.
- Added deleted-stage recovery: when one or more expected scanner lists are missing, the wrapper routes that exact date through the maintained `import_delivery_folder` business workflow without direct table edits.
- Preserved scan quantities, route/stage rules, rack and bay behavior, notifications, live logs, UNC publishing, and existing automation settings.
## v0.112 - Successful No-Change Automation Runs

- Fixed unchanged SQL checks failing with `Cannot bind argument to parameter 'Dates' because it is an empty array.`
- Changed scanner-import date binding to safely accept an empty collection as a defensive fallback.
- Added an explicit pre-import guard so SQL export-and-import mode skips the scanner importer when no changed or pending workbooks exist.
- Added a clear `No changed or pending delivery-list workbooks require scanner import.` log line.
- No-change runs now complete successfully and publish the normal no-change notification instead of a failure notification.
- Preserved changed-workbook imports, pending-import retries, authoritative Recent Delivery List Imports history, complete live logs, UNC publishing, and all scanner data.
## v0.111 - Import Completion and Live Log Performance Fix

- Fixed the Status & Logs page appearing frozen after the scanner database import had already completed.
- Stopped printing the complete per-file import result JSON to PowerShell stdout; the full normalized result remains stored for Recent Delivery List Imports.
- Changed importer console output to one concise summary line with counts, imported dates, failed dates, and the private result-file path.
- Throttled live-status persistence so the complete growing command log is not rewritten to disk after every individual output line.
- Limited normalized import results to the delivery-date window requested by the automation run so unrelated files cannot be marked imported or flood the status output.
- Added a clear transition log after the scanner importer returns and before its normalized result is processed.
- Preserved v110 UNC/SMB publishing, complete per-run logs, notification reliability, and v109 accurate New/Updated/No Changes/Failed history.
- Preserved all scanner workflows, scan quantities, rack/bay assignments, routes, audio, notification history, and the production database.
## v0.110 - Live Automation Logs and Network Share Publishing Fix

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
## v0.109 - Accurate Automated Import History

- Connected automated SQL/folder imports to the scanner's authoritative `imports` table instead of relying on an isolated automation status summary.
- Updated the Admin **Recent Delivery List Imports** section immediately after manual or scheduled automation completes.
- Added accurate result labels for **New**, **Updated**, **New + Updated**, **No Changes**, and **Failed** imports.
- Corrected the importer wrapper to read `importedFiles`, `updatedFiles`, `skippedFiles`, and `failedFiles` from the maintained folder importer.
- Stopped requested dates from being marked imported unless the maintained scanner importer actually processed them successfully.
- Preserved pending dates when a file fails or is not processed so a later run can retry it.
- Merged authoritative `last-run.json` results into the web control center so completed runs retain import counts and date details.
- Added a protected recent-import API endpoint and automatic Admin history refresh after automation notifications.
- Preserved the v108 Control Center, notification bell, scanner workflows, scan quantities, rack/bay assignments, routes, audio, and production database.
## v0.107 - Delivery List Automation Control Center

- Changed **Import / Update Delivery List** into a GUI control center instead of immediately running the folder importer.
- Added three safe manual commands: **Import Temp Folder Only**, **Query SQL & Export Only**, and **Query SQL, Export & Import**.
- Added one-date, custom-range, normal incremental-window, and full-refresh-window controls.
- Added configurable automatic modes so temporary floor installations can use folder-only importing while the authorized central installation can query A+W SQL.
- Added GUI controls for interval, past/future date windows, daily full refresh time, destination folder, popup notifications, task installation, and task removal.
- Reused the existing scanner notification queue for success, no-change, and failure popups.
- Added a server-side allowlisted control module; the browser never receives SQL credentials and cannot execute arbitrary commands.
- Preserved all v105 Old Bay, Bay Scanner, audio, database, route, rack, and scanning behavior.
# README Changelog

## v0.106
- Added `automation/crystal_delivery_export`, a local Crystal Reports automation package that uses the existing SAP Crystal .NET runtime instead of a third-party report scheduler or mouse automation.
- Added automatic `DeliveryDate` parameter injection for `DeliveryList.rpt`, SQL Server login application for report and subreport tables, and XLSX export through `ExportFormatType.ExcelWorkbook`.
- Added Windows DPAPI credential storage so the A+W SQL password is entered only on the local workstation and is never stored in the repository or plain-text task commands.
- Added automatic Crystal runtime discovery, 64-bit/32-bit Windows PowerShell testing, one-date validation, detailed logs, status JSON, and removable Windows Task Scheduler tasks.
- Added hourly incremental refreshes for two days back through fourteen days forward and a daily 5:15 PM reconciliation for seven days back through ninety days forward; both horizons remain configurable.
- Added safe local staging, XLSX signature/size validation, SHA-256 comparison, `.partial` network publishing, overlap prevention, and no-record protection so failed or empty runs do not replace the previous valid workbook.
- Added `import_delivery_folder.py`, which reuses `scanner_config.py` and `delivery_store.py` to import or update the scanner immediately after each automated export run without duplicating import rules.
- Added static tests for the automation file set, known A+W report/database paths, secure credential workflow, safe publishing behavior, and reuse of the maintained scanner business layer.
- Updated the maintained release summary and project documentation links to v106 without changing the v105 Bay Map interface or the v097 database migration contract.

## v0.105
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

## v0.104
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

## v0.103
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

## v0.100
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

## v0.099
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

## v0.098
- Added the complete Barefoot Delivery Scanner Audio Language with 27 distinct mastered mono WAV cues.
- Replaced the four generic operational files with semantic cues for success, duplicate, warning, error, Rush, remake, completion, racks, bays, undo/redo, import, save, print, email, authentication, notifications, permissions, and future machine events.
- Updated the shared Web Audio loader to resolve semantic cue names, cache decoded buffers, retain the shared compressor/volume chain, and fall back safely when a WAV cannot load.
- Added context-aware scan selection so Rush and remake pieces have recognizable success sounds, duplicate scans differ from warnings, and rack/bay workflows use their own audio identities.
- Added audio feedback for rack completion/reopen/return, bay assign/remove/move, undo/redo, import start/complete, settings saves, print preview, sent email, sign-in/sign-out, notifications, and permission denial.
- Added `sounds/audio_manifest.json`, `sounds/README_AUDIO_PACK.md`, and `sounds/preview_audio_pack.html` for maintenance and browser-based auditioning.
- Preserved the v097 numbered SQLite migrations, database safeguards, and Azure SQL preparation without changing migration 001 or 002.
- Advanced browser and sound cache keys to v098.
- Packaged the release as `Delivery_List_Scanner_v098.zip` without live databases, WAL/SHM files, logs, caches, or verification artifacts.

## v0.097
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

## v0.096
- Matched the sign-in page logo to the expanded desktop sidebar logo.
- Reduced the sign-in logo frame from 188 x 188 to 108 x 108.
- Kept the sign-in logo square, proportional, and filled with the same sampled dark-blue background color used by the expanded sidebar logo.
- Kept collapsed-sidebar and mobile-logo sizes unchanged.
- Advanced browser cache keys to v096.

## v0.095
- Reduced only the expanded desktop sidebar logo and its outline by 10%, from 120 x 120 to 108 x 108.
- Kept the collapsed sidebar logo and mobile logo sizes unchanged.
- Matched the inside of every logo outline to the logo image's sampled dark-blue background color: RGB 4, 43, 84.
- Preserved the square frame, proportional image rendering, and existing sidebar alignment.
- Advanced browser cache keys to v095.

## v0.094
- Corrected the combined Barefoot and Builders FirstSource logo frames so every displayed version is a true square.
- Set the sign-in logo frame to 188 x 188.
- Kept the collapsed sidebar logo frame at 48 x 48.
- Set the expanded desktop sidebar logo frame to 120 x 120.
- Set the mobile sidebar logo frame to 158 x 158.
- Kept `object-fit: contain` so the supplied logo remains proportional inside each square frame.
- Advanced browser cache keys to v094.

## v0.093
- Removed the `object-fit: cover` logo rule that was stretching the combined logo into the outline.
- Restored proportional `object-fit: contain` rendering for the sign-in, collapsed-sidebar, expanded-sidebar, and mobile logos.
- Kept the existing displayed logo heights while allowing each image width to follow its natural aspect ratio.
- Adjusted the subtle border, outline, and shadow to follow the actual rendered image rectangle rather than a wider forced frame.
- Preserved the v092 sound volume controls and scan-sound behavior unchanged.
- Advanced browser cache keys to v093.

## v0.092
- Tight-cropped the supplied combined Barefoot + Builders FirstSource logo so the rounded frame hugs the visible branding instead of surrounding large internal margins.
- Kept the rounded corners, subtle outline, and soft shadow for collapsed, expanded, mobile, and sign-in logo presentations.
- Added a persistent scanner-sound volume slider to the temporary Scan and Bay Map sound-test panels.
- Added a 0-400% floor-volume range with a 200% default for louder production-floor feedback.
- Added a shared Web Audio master-gain and compressor chain so success, notice, error, and 100% completion sounds all follow one volume setting.
- Synchronized every visible volume slider and stored the selected setting in browser local storage.
- Advanced browser cache keys to v092.

## v0.091
- Added rounded corners to the supplied Barefoot + Builders FirstSource logo in the sign-in screen and sidebar.
- Added a subtle light outline and soft shadow so the logo stands out slightly against the dark navigation background.
- Replaced the collapsed Barefoot-only sidebar image with the same combined Barefoot + Builders FirstSource logo used in the expanded sidebar.
- Kept the existing collapsed/expanded dimensions and sidebar navigation alignment unchanged.
- Advanced browser cache keys to v091.

## v0.090
- Replaced the existing combined Barefoot and Builders FirstSource brand image with the newly supplied logo.
- Kept the existing webapp asset filename so the sign-in screen, expanded desktop sidebar, and mobile drawer all use the new logo without duplicating brand logic.
- Preserved the collapsed sidebar's compact Barefoot icon so navigation remains readable at rail width.
- Advanced browser cache keys to v090.

## v0.089
- Combined the existing Barefoot & Company logo with the attached Builders FirstSource logo in a new stacked brand asset.
- Preserved the supplied Builders FirstSource red side lines, red square/white 1 mark, and dark blue text.
- Added `barefoot-builders-firstsource-logo.png` as the maintained combined logo asset.
- Updated the sign-in panel to use the combined Barefoot and Builders FirstSource logo.
- Updated the expanded desktop sidebar to crossfade from the compact Barefoot-only mark to the combined logo without changing the fixed sidebar brand-row height or moving the page selectors.
- Updated the mobile navigation drawer to use the combined logo.
- Kept the collapsed desktop sidebar on the smaller Barefoot-only mark because the Builders FirstSource text is not readable at icon size.
- Advanced browser cache keys to v089.

## v0.088
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

## v0.087
- Increased the expanded desktop sidebar logo by approximately 25%, from 74 x 74 to 93 x 93.
- Kept the collapsed sidebar logo at 48 x 48.
- Added `--app-sidebar-logo-expanded-size` as the single documented CSS setting for future logo-size adjustments.
- Updated both the base and final desktop ownership rules to use the shared logo-size variable, preventing later CSS overrides from using a different size.
- Preserved the fixed 126px brand section so page selector buttons and icons remain aligned between collapsed and expanded states.
- Advanced browser cache keys to v087.

## v0.086
- Reduced the expanded Barefoot sidebar logo by 65%, from 210 x 210 to 74 x 74.
- Kept the collapsed sidebar logo at 48 x 48.
- Reduced the fixed desktop sidebar brand section from 280px to 126px.
- Moved Home, Scan, Racks, Bay Map, and Admin upward in both collapsed and expanded states.
- Kept one identical fixed brand-section height in both states so every selector and icon remains vertically aligned during hover expansion.
- Advanced browser cache keys to v086.

## v0.085
- Fixed the expanded Barefoot logo being reduced by a later responsive sidebar rule.
- Added a final sidebar-specific logo ownership block so the expanded desktop logo renders up to 210 x 210.
- Kept the collapsed sidebar logo at 48 x 48.
- Made the top sidebar brand section a fixed 280px height in both collapsed and expanded states.
- Removed the hover-only brand-section height change that pushed Home, Scan, Racks, Bay Map, and Admin downward during expansion.
- Kept every page selector and icon at the same vertical position before, during, and after sidebar hover expansion.
- Added an explicit large-logo rule for the responsive mobile drawer as well.
- Advanced browser cache keys to v085.

## v0.084
- Reverted the collapsed sidebar Barefoot logo back to the smaller size so the rail stays clean when not hovered.
- Reduced the collapsed sidebar logo from 72 x 72 back to 48 x 48.
- Kept the large hover-only expanded brand presentation for the sidebar.
- Tuned the expanded sidebar logo to 210 x 210 so it fills about 75% of the expanded top brand section.
- Set the expanded sidebar top brand section height to 280px so the larger logo sits centered and proportionate.
- Advanced browser cache keys to v084.

## v0.083
- Removed the outer global-search container chrome so the centered search bar and Search button sit cleanly in the header without the larger wrapper box.
- Reduced the header global-search width from 640px to 560px for a cleaner centered layout.
- Increased the sidebar Barefoot logo by 50% in both collapsed and expanded states.
- Increased the collapsed sidebar logo size from 48 x 48 to 72 x 72.
- Increased the expanded sidebar logo size from 176 x 176 to 264 x 264.
- Added a hover-only larger sidebar logo area so the expanded logo stays centered without wasting space when collapsed.
- Advanced browser cache keys to v083.

## v0.082
- Restored the operations sidebar on the Scan page.
- Kept the sidebar collapsed by default and hover-expandable, matching Home, Racks, Bay Map, and Admin.
- Preserved the sign-in-screen behavior that hides the entire application shell until authentication succeeds.
- Retained the centered smaller global search bar and simplified Today’s Delivery Progress design from v081.
- Advanced browser cache keys to v082.
- Updated static and browser-rendered checks so the Scan page is protected as a sidebar-enabled workspace.
