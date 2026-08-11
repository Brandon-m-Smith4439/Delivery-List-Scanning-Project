# Delivery List Scanner

Current maintained release: **v0.302**. SQLite remains the active/default backend.

v0.302 merges the maintained Main workspace with Website Version 2. It keeps Main's statistics, printing, rack, scan, and Bay Map improvements while adding Website 2's authoritative SQL-import reconciliation, complete import history, superseded-order review, and exact-key removal safeguards.

## Install v0.302

1. Stop the Delivery List Scanner if it is running.
2. Extract the v0.302 changed-files ZIP directly into `C:\Users\brandon.m.smith\My Projects\Delivery List Scanning Project` and replace the included files.
3. Preserve the existing `data` folder and database files.
4. Start the scanner normally.
5. Hard-refresh the browser (`Ctrl+F5`) once so the v0.302 CSS/JavaScript cache keys are loaded.

On first start, the numbered migration runner upgrades schema version 5 databases through schema version **11** without deleting operational data. Keep the existing `data` folder in place and retain a verified database backup before replacing program files.

## v0.302 highlights

- Collapsed the oversized Packing List History page-count strip into one compact line such as **1-5 of 5 print days · 6 snapshots**.
- Forced **Preview** and **Print Snapshot** to remain beside each other on each snapshot row.
- Raised the snapshot preview into a dedicated top-level visual layer so it always appears above Packing List History.
- Removed the redundant footer **Close** button from Snapshot Preview while retaining the top-right X and Escape/backdrop close behavior.
- Replaced the generic Glass Cart visual with a recognizable **A-frame glass cart** icon while retaining the existing saved `glasscart` value for compatibility.
- Restored a very small pencil shortcut in the top-right of each physical Bay Map group; clicking it opens that exact group in the maintained Edit Bays GUI.
- Preserved Main's Packing List History, statistics workspace, formatted print/export, rack visuals, scan review, and Bay Map improvements.
- Added authoritative import reconciliation that retires removed source rows logically while keeping their audit history.
- Added complete same-day import history, route-accurate update preview, source exclusions, and exact added/removed piece totals.
- Added administrator review for likely superseded A+W orders, including selectable exact-order removal and durable decision history.
- Advanced `APPLICATION_VERSION` to 302 and `CURRENT_SCHEMA_VERSION` to 11; migrations are additive and do not reset the production database.

## v0.269 highlights

- Reworded Scan update messaging to distinguish a **New stage** from a **Delivery list updated** with **new orders**; Scan attention filtering now says **New Orders** instead of describing orders as updated.
- Strengthened the always-visible Scan review bar with a clearer border, accent, and NEW STAGE / NEW ORDERS label so pending review work is harder to miss.
- Set the Scan new-order/stage review popup to **10 seconds** with matching countdown/progress timing.
- Preserved the most recent rack on a scan line after that rack is cleared/scanned out, displaying the former rack as a muted **prior** location while active rack/bay/received locations still take precedence.
- Standardized shared blue buttons at a consistent **13px** font size and a slightly shorter **38px** minimum height; the Manual Scan Submit button now uses the shared primary-button component.
- Added a rack-set icon library and editable icon color when creating or editing a rack set. Selections persist through existing `system_metadata` and appear on Rack Overview cards and Rack Manager group headers.
- Added a visible **20-second** Old Bay review countdown and matching timeout progress bar.
- Advanced `APPLICATION_VERSION` to 269 while preserving `CURRENT_SCHEMA_VERSION = 5`; no migration or database reset is included.

## v0.266 highlights

- Made New/Updated flags authoritative to the newest update batch for each stage so superseded unreviewed notices no longer keep stale `!` markers or review notifications visible.
- Changed Staging/Outbound review to acknowledge the same current update batch across every active route/stage for that delivery date, while IT, CPU, DTC, and Greenville remain stage-specific and per-user.
- Reduced the New/Updated review notification lifetime from 15 seconds to 7.5 seconds.
- Kept Stage and Delivery Date popup menus aligned to their compact trigger width so `!` indicators do not cause oversized dropdowns.
- Increased Scan panel Station, Stage, and Delivery Date value text slightly while expanding the label budget for Indian Trail and review-marked dates.
- Advanced `APPLICATION_VERSION` to 266 while preserving `CURRENT_SCHEMA_VERSION = 5`; no migration or database reset is included.

## v0.265 highlights

- Expanded the Scan header label budget so Indian Trail and delivery dates with review markers remain fully visible.
- Added per-user `!` review markers to the Stage selector as well as the Delivery Date selector.
- Changed date marker aggregation to de-duplicate the same order/item copied across multiple stages.
- Made Airport Rd review order-aware: reviewing Staging or Outbound marks the exact reviewed update occurrence read across downstream copies of those same order/items for that user.
- Kept Indian Trail, CPU, DTC, and Greenville review independent so reviewing one route does not clear another route.
- Moved each Bay Map grouped-set Edit icon to the top-right corner of the group header.
- Advanced `APPLICATION_VERSION` to 265 while preserving `CURRENT_SCHEMA_VERSION = 5`; no migration or database reset is included.

## v0.263 highlights

- Restored readable Statistics typography after the prior compact pass made labels, controls, table text, legends, and chart details too small.
- Reorganized breakage tables into clearer accountability blocks for machine/glass/reason review.
- Grouped pieces, SQFT, cost, and reject count together instead of spreading them across many narrow columns.
- Improved coverage/status presentation and selected-row drilldowns while preserving custom ranges and breakage controls.
- Advanced `APPLICATION_VERSION` to 263 while preserving `CURRENT_SCHEMA_VERSION = 5`; no database migration or database change is included.

## v0.262 highlights

- Consolidated the previous machine piece/SQFT/cost datasets into one **Machine breakage overview** with a Chart Unit selector for Square feet, Pieces, or Cost.
- Consolidated glass breakage into one **Glass type breakage overview** with the same switchable ranking measure.
- Added **Reject reasons by machine**, showing how many reject events each reason generated for each machine plus pieces, SQFT, cost, and affected glass types.
- Added machine drilldowns for top reject reasons and broken glass types, and glass-type drilldowns for responsible machines and reject reasons.
- Added a polished Statistics custom-date calendar using the established Print / Export two-month range-picker visual language. A custom range overrides the preset range until another preset is selected.
- Limited the **External remakes** switch to breakage reporting and restyled it as a compact web-app toggle. External remakes remain separate from real machine accountability.
- Expanded combined breakage table rows so pieces, SQFT, material cost, reject-event count, related machines/glass, top reasons, and data coverage can be reviewed without changing datasets.
- Updated the Statistics PDF with machine reject counts, broken glass context, and top reject reasons while keeping the report focused on operationally useful information.
- Preserved the default Top 10 / Show more data behavior and the compact v0.260 chart geometry.
- Advanced `APPLICATION_VERSION` to 262 while preserving `CURRENT_SCHEMA_VERSION = 5`; no schema migration, database reset, or migration-registry change is included.

## v0.261 highlights

- Added **Glass costs** as a fourth library inside Admin → Lookup Manager.
- Displays all built-in glass rates plus newly discovered unpriced glass products in one searchable list.
- Administrators can edit an existing rate or add a rate for a new glass type using **Cost per SQFT**.
- Saved rates persist through the existing `admin_lookup_values` table; no schema change or migration is required.
- Statistics breakage calculations use the effective administrator-maintained price map, with the built-in rates retained as fallbacks.
- Lookup Manager identifies default, discovered, and manually maintained pricing sources and highlights glass with no configured cost.
- Preserved `CURRENT_SCHEMA_VERSION = 5`; no migration was introduced.

## v0.260 highlights

- Opens Statistics on **Glass type quantity** in the donut/circle view with a default display limit of 10 categories.
- Adds **Show more data** below the main analytics region; each click increases the display limit before eventually exposing all matching categories.
- Reduces main chart/table geometry and typography by roughly one third so substantially more data fits in the same workspace.
- Uses compact workflow labels in Statistics: Staging, Outbound, Inbound, CPU, Greenville, and DTC.
- Adds internal reject datasets by machine and glass type for piece count, SQFT, and estimated material cost.
- Makes breakage table view show pieces, SQFT, estimated cost, data coverage, and source together so machine accountability can be reviewed without switching measures.
- Calculates piece and SQFT breakage percentages against estimated total produced glass and adds an explicit toggle to include or exclude external remakes.
- Uses the maintained per-SQFT glass pricing supplied for Clear, UltraClear, Mirror, and Antique Mirror products; unknown prices and missing dimensions are reported instead of silently estimated.
- Replaces the prior Statistics PDF clutter with delivery progress, breakage KPIs, workflow progress, machine breakage, glass-type breakage, and calculation coverage notes.
- Keeps external remakes separate from production-machine accountability even when they are included in the overall breakage percentage.
- Preserves `CURRENT_SCHEMA_VERSION = 5`; no migration, database reset, or schema-contract change is part of this release.

## v0.253 highlights

- Replaces the repeated dashboard totals with four priority cards: delivery completion, open pieces, on-time completion, and remake pieces.
- Keeps glass-mix visualization on the dashboard while improving hierarchy, legend readability, summary context, responsive behavior, and empty states.
- Rebuilds stage cards around completion, scanned pieces, open pieces, and list counts without repeating top-level totals.
- Consolidates scan exceptions, manual scans, bay overrides, rack activity, bay activity, manual edits, and top-operator activity into one operational-health section.
- Removes the obsolete duplicate snapshot/remake containers and eliminates the second redundant statistics render pass.
- Modernizes the full chart explorer and replaces its repeated dashboard KPIs with chart-specific category, total, average, and highest-value summaries.
- Preserves all existing chart metrics, filters, sorting, limits, bar/donut views, and PDF reporting. No new migration was intended; v0.255 keeps the maintained schema contract at version 5.

## Install v0.232

1. Start from the maintained v0.231 project.
2. Extract the v0.232 changed-files ZIP directly into the current project folder.
3. Preserve the existing `data` folder and database files.
4. Restart the scanner server and refresh the browser with `Ctrl+F5`.

No database migration or separate setup script is required. v0.232 keeps schema version 5.

## v0.232 highlights

- Removes the Description field from Create Preset and keeps Preset Name beside the personal-default toggle.
- Increases the desktop modal height to 860 pixels while retaining safe scrolling only for shorter or narrower browser windows.
- Expands Glass Types into side-by-side Annealed, Tempered, and Mirror panels on desktop.
- Restores subtle route-specific tints and restrained blue, green, and purple glass-family colors.
- Keeps Status and Attention controls neutral so selected filters remain clear without overwhelming the workspace.
- Preserves Preset Summary, Print Options, bottom-right Save Preset actions, Lookup Manager values, and schema version 5.

## Install v0.231

1. Start from the maintained v0.230 project.
2. Extract the v0.231 changed-files ZIP directly into the current project folder.
3. Preserve the existing `data` folder and database files.
4. Restart the scanner server and refresh the browser with `Ctrl+F5`.

No database migration or separate setup script is required. v0.231 keeps schema version 5.

## v0.231 highlights

- Organizes Create Preset glass types into Annealed, Tempered, and Mirror sections while preserving exact Lookup Manager values.
- Replaces category-specific button colors with one neutral control treatment.
- Makes selected filters obvious through a stronger border, soft shared background, check badge, and selected-count pill.
- Moves Print Options directly below Preset Summary in the right column.
- Anchors Save Preset actions at the bottom-right of the desktop workspace.
- Shortens instructional text and keeps the responsive tablet/mobile stacking behavior.
- Consolidates the final preset CSS ownership layer instead of stacking another duplicate override block.
- Preserves schema version 5.

## Install v0.230

1. Start from the maintained v0.229 project.
2. Extract the v0.230 changed-files ZIP directly into the current project folder.
3. Preserve the existing `data` folder and database files.
4. Restart the scanner server and refresh the browser with `Ctrl+F5`.

No database migration or separate setup script is required. v0.230 keeps schema version 5.

## v0.230 highlights

- Rebuilds the Create Preset workspace rows around content height instead of forcing the main cards into a fixed-height grid row.
- Prevents Print Options, Preset Summary, Actions, status messages, and the information footer from occupying the same vertical space.
- Keeps the compact centered workspace and uses internal scrolling only when the browser is too short to show every card.
- Replaces saturated selected filter fills with soft tinted backgrounds, stronger borders, readable dark text, and retained check marks.
- Softens action, orientation, card-accent, and backdrop colors while preserving clear hierarchy and route/category identity.
- Preserves responsive stacking, Lookup Manager glass types, live summary, personal defaults, and Save/Apply behavior.
- Preserves schema version 5.

## Install v0.229

1. Start from the maintained v0.228 project.
2. Extract the v0.229 changed-files ZIP directly into the current project folder.
3. Preserve the existing `data` folder and database files.
4. Restart the scanner server and refresh the browser with `Ctrl+F5`.

No database migration or separate setup script is required. v0.229 keeps schema version 5.

## v0.229 highlights

- Reduces the desktop Create Preset workspace to a centered maximum of 1240 × 780 pixels while retaining responsive full-screen behavior on smaller displays.
- Increases labels, inputs, filter choices, summaries, and action-button typography without increasing the overall modal footprint.
- Carries the Print / Export route, status, attention, All-choice, Mirror, Tempered, and Annealed gradients into Create Preset.
- Adds stronger card hierarchy, section accent rails, polished shadows, and the maintained Print / Export blue workspace treatment.
- Keeps the v0.228 viewport repair, internal scrolling, Lookup Manager glass library, live summary, personal default, and Save/Apply behavior.
- Preserves schema version 5.

## Install v0.228

1. Start from the maintained v0.227 project.
2. Extract the v0.228 changed-files ZIP directly into the current project folder.
3. Preserve the existing `data` folder and database files.
4. Restart the scanner server and refresh the browser with `Ctrl+F5`.

No database migration or separate setup script is required. v0.228 keeps schema version 5.

## v0.228 highlights

- Removes the legacy centered-modal transform that shifted the full-screen preset workspace beyond the top-left edge.
- Gives the v0.228 modal and backdrop final fixed-position ownership so legacy preset classes cannot move the workspace.
- Keeps a consistent 12px desktop viewport inset and a 5px mobile inset.
- Preserves the complete v0.227 preset-control-center design while making its workspace internally scrollable.
- Resets the preset workspace to the top whenever it opens and focuses the name field without moving the page.
- Adds compact-height adjustments for shorter desktop displays.
- Preserves schema version 5 and all v0.227 preset behavior.

## Install v0.227

1. Start from the maintained v0.226 project.
2. Extract the v0.227 changed-files ZIP directly into the current project folder.
3. Preserve the existing `data` folder and database files.
4. Restart the scanner server and refresh the browser with `Ctrl+F5`.

No database migration or separate setup script is required. v0.227 keeps schema version 5.

## v0.227 highlights

- Uses a complete red gradient and exclamation indicator when Remakes, Rushes, or Internal Rejects contain matching work.
- Uses a complete green gradient and check indicator when each of those attention categories is clear.
- Replaces the step-based Create Preset screen with a full preset control center modeled on the supplied reference.
- Adds Preset Details with name, description, and an optional personal-default toggle.
- Keeps Default Filters, Print Options, Preset Summary, and Actions visible in one organized workspace.
- Removes Visibility and Preview from Create Preset as requested.
- Supports Save Preset and Save & Apply as separate actions.
- Preserves Lookup Manager glass types, automatic All-choice collapsing, grouped newest-first delivery dates, and schema version 5.

## Install v0.226

1. Start from the maintained v0.225 project.
2. Extract the v0.226 changed-files ZIP directly into the current project folder.
3. Preserve the existing `data` folder and database files.
4. Restart the scanner server and refresh the browser with `Ctrl+F5`.

No database migration or separate setup script is required. v0.226 keeps schema version 5.

## v0.226 highlights

- Automatically collapses every available Route selection back to Airport, the maintained all-routes choice.
- Automatically collapses complete Glass, Status, and Attention detail selections back to All Glass, All Status, or All Attention.
- Applies the same collapse behavior inside Create Preset.
- Orders grouped delivery-date weeks and their dates from newest/future to oldest.
- Restores the v0.224 two-column, step-guided Create Preset layout while preserving Lookup Manager glass values and fast loading.
- Enlarges glass-category quantity totals, changes Tempered styling from orange to green, and lengthens the Checked By write-in line.
- Preserves incremental two-week date-history loading, custom ranges, print geometry, and schema version 5.

## Install v0.225

1. Start from the maintained v0.224 project.
2. Extract the v0.225 changed-files ZIP directly into the current project folder.
3. Preserve the existing `data` folder and database files.
4. Restart the scanner server and refresh the browser with `Ctrl+F5`.

No database migration or separate setup script is required. v0.225 keeps schema version 5.

## v0.225 highlights

- Reduces Landscape continuation pages from 29 to 28 logical rows while leaving the first Landscape page at 27.
- Replaces the step-based Create Preset layout with one continuous name, filter, glass-library, and output workspace.
- Groups Delivery Date choices under visual Monday-Sunday week headings.
- Initially renders the rolling previous two weeks together with every currently available future delivery date.
- Loads two additional historical weeks whenever the user reaches the bottom of the date menu, with an explicit Load 2 older weeks control as a keyboard/mouse fallback.
- Performs the date-history expansion entirely in memory, without additional list-detail requests or recurring work.
- Preserves custom date ranges, system/user presets, shared preview/print styling, idle-state recovery, and schema version 5.

## Install v0.224

1. Start from the maintained v0.223 project.
2. Extract the v0.224 changed-files ZIP directly into the current project folder.
3. Preserve the existing `data` folder and database files.
4. Restart the scanner server and refresh the browser with `Ctrl+F5`.

No database migration or separate setup script is required. v0.224 keeps schema version 5.

## v0.224 highlights

- Grays out and disables zero-count Route, Status, New/Updated, and Errors choices so unavailable filters cannot be mistaken for usable filters.
- Keeps Remakes, Rushes, and Internal Rejects active at zero so their maintained green-clear or red-alert indicators remain visible.
- Automatically falls back to a route/status/attention selection that still has content after a date or route scope changes.
- Enlarges the numeric counts on every Print / Export filter chip without increasing the control height.
- Removes the surrounding Checked By box and moves the larger signoff text into the first-page title header, aligned with the Filters line on the right.
- Enlarges `Rows | Orders | QTY` on first and continuation pages while keeping Filters visually secondary.
- Preserves v0.223 page capacity, centered Order/Item/QTY columns, shared preview/print styling, and schema version 5.

## Install v0.223

1. Start from the maintained v0.222 project.
2. Extract the v0.223 changed-files ZIP directly into the current project folder.
3. Preserve the existing `data` folder and database files.
4. Restart the scanner server and refresh the browser with `Ctrl+F5`.

No database migration or separate setup script is required. v0.223 keeps schema version 5.

## v0.223 highlights

- Moves the first-page `Checked By` field out of the branded title area and places it immediately above the delivery-list column headings.
- Keeps the signoff right aligned and compact so the title remains clean without wasting printable height.
- Adds two logical delivery-list lines to each first page.
- Adds three logical delivery-list lines to every continuation page.
- Uses 26/28 logical rows in Portrait and 27/29 in Landscape for first/continuation pages; glass-type separator rows continue to count toward the limit.
- Centers the Order, Item, and QTY columns and transfers a small amount of width from Dimensions to QTY so the complete `QTY` heading remains visible.
- Applies the same structure and sizing to the on-screen preview and popup print document through the shared stylesheet.
- Preserves the enlarged v0.222 branding, repeating filters, alternating rows, fixed footer, Rush/remake frames, and idle-state recovery.

## Install v0.222

1. Start from the maintained v0.221 project.
2. Extract the v0.222 changed-files ZIP directly into the current project folder.
3. Preserve the existing `data` folder and database files.
4. Restart the scanner server and refresh the browser with `Ctrl+F5`.

No database migration or separate setup script is required. v0.222 keeps schema version 5.

## v0.222 highlights

- Enlarges the complete first-page branded title block by approximately 30%, including the supplied logo, route title, full date, totals, filters, badge, and Checked By field.
- Enlarges continuation-page branding by approximately 10% while preserving a more compact hierarchy than page one.
- Uses fit-aware medium and long route-title sizes so multi-route headings remain on one line beside the Checked By field.
- Applies the same sizing to the on-screen Letter preview and popup print document through the shared stylesheet.
- Reserves safe vertical space by adjusting logical row limits to 24/25 in Portrait and 25/26 in Landscape for first/continuation pages.
- Preserves Default Letter margins, repeating filters and footer, glass headings, alternating rows, Rush/remake frames, and the v0.221 idle-state recovery.

## Install v0.221

1. Start from the maintained v0.220 project.
2. Extract the v0.221 changed-files ZIP directly into the current project folder.
3. Preserve the existing `data` folder and database files.
4. Restart the scanner server and refresh the browser with `Ctrl+F5`.

No database migration or separate setup script is required. v0.221 keeps schema version 5.

## v0.221 highlights

- Preserves already loaded delivery-list item detail when the 10-second background catalog heartbeat returns an unchanged lightweight list summary.
- Invalidates cached print rows only when list revision fields actually change, then reloads only the selected lists on demand.
- Reasserts committed route state when the tab regains focus, returns from browser history, or becomes visible again.
- Keeps the recovery event-driven; unchanged heartbeats perform no Print / Export rerender and no extra API request.
- Prevents a long-idle page from showing Airport as selected while preview/print rows have silently been discarded.

## Install v0.220

1. Start from the maintained v0.219 project.
2. Extract the v0.220 changed-files ZIP directly into the current project folder.
3. Preserve the existing `data` folder and database files.
4. Restart the scanner server and refresh the browser with `Ctrl+F5`.

No database migration or separate setup script is required. v0.220 keeps schema version 5.

## v0.220 highlights

- Removes the Date write-in field from delivery-list signoff and keeps one right-aligned `Checked By` line.
- Repeats the compact active Filters summary on first and continuation pages.
- Uses route-specific gradients for Airport, Indian Trail, Greenville, CPU, and DTC choices.
- Groups visible glass types under compact Mirror, Tempered, and Annealed separators with matching category colors.
- Gives All/Not Scanned/Partial/Complete and Attention choices distinct, readable gradients.
- Adds Scan-page-style red exclamation circles when Remakes, Rushes, or Internal Rejects exist and green check circles when each category is clear.
- Reduces continuation-page row limits by one logical row to reserve safe space for the repeating filter line.
- Preserves the shared preview/print stylesheet, 90% Portrait preview zoom, Letter geometry, print logo, pagination, gray bands, alternating rows, and repeating Printed at footer.

## v0.219 highlights

- Moves the first-page Checked By and Date signoff box slightly lower so it aligns more naturally with the branded title block.
- Forces both signoff labels and the full delivery date to remain on one line.
- Makes the popup print document load the same maintained `static/css/styles.css` used by the preview instead of carrying a second duplicated formatting definition.
- Waits for the shared stylesheet, fonts, and logo image before opening the browser print dialog.
- Keeps only physical Letter-page and printer-margin overrides inside the popup, preventing future preview/print formatting drift.
- Sets Portrait preview to 90% by default, including after returning from Landscape mode.
- Preserves Letter dimensions, default 0.4-inch margins, pagination, table geometry, gray bands, alternating rows, remake/rush frames, and footer placement.

## v0.218 highlights

- Restores the supplied Barefoot Company / Builders FirstSource logo asset to the changed-files package so preview and popup print documents render the actual artwork rather than fallback alt text.
- Resolves the logo through an absolute application URL with a v0.218 cache key, keeping popup printing reliable after upgrades.
- Removes the continuation-sheet sentence beneath the title while retaining the top-right page number.
- Keeps route-driven delivery-list titles on one continuous line and automatically scales unusually long multi-route titles instead of wrapping them into an indented second line.
- Enlarges the full weekday date to sit just below the title in the same visual hierarchy.
- Tightens the vertical gap between `Rows | Orders | QTY` and the active Filters line.
- Preserves pagination, gray bands, alternating rows, first-page signoff fields, remake/rush borders, and repeating Printed at footers.

## v0.217 highlights

- Displays delivery dates in the readable `Tuesday, August 4, 2026` format across the browser application, including the Home page and Delivery List views.
- Replaces the print header's compact numeric date-first wording with a route-first title such as `INDIAN TRAIL DELIVERY LIST`.
- Joins multiple selected routes with vertical separators, such as `GREENVILLE | CPU | DTC DELIVERY LIST`.
- Places the full weekday date directly beneath the route title in preview and actual paper output.
- Expands the adaptive Print / Export date control so full weekday dates and custom ranges remain readable.
- Preserves the supplied print logo, page totals, filters, signoff fields, pagination, gray bands, alternating rows, and repeating footer.

## v0.216 highlights

- Adds the supplied stacked Barefoot Company and Builders FirstSource logo as a dedicated print asset and uses it in preview and generated print pages.
- Crops only the unused outer canvas around the supplied logo, retaining the artwork itself and a clean white print margin.
- Removes the extra title/header divider above the table on normal, Rush, remake, and continuation pages while preserving the black divider between column headings and glass-type groups.
- Places the active Filters line on its own line directly beneath `Rows | Orders | QTY`.
- Preserves v0.215 date-first titles, dynamic destinations, alternating rows, gray table bands, pagination, remake/rush frames, and repeating footer.

## v0.215 highlights

- Makes the delivery date the dominant top-left heading in compact `M/D/YY` format.
- Places `Delivery list for <destination>` beneath the date and derives the destination from the committed Route selection.
- Reuses the existing sidebar Barefoot/Builders FirstSource logo beside the title with grayscale and contrast treatment for black-and-white printing.
- Adds a strong black divider between the column headings and every glass-type subheader.
- Alternates printable order rows between white and light gray while preserving exact print colors in Chrome and Edge.
- Preserves v0.214 page capacities, first-page signoff details, compact continuation headers, gray heading bands, and repeating footer.

## v0.214 highlights

- Raises Portrait pagination to 25 logical rows on first pages and 27 on continuation pages.
- Raises Landscape pagination to 26 logical rows on first pages and 28 on continuation pages, with glass headings still counted toward the page limit.
- Keeps Checked By, Date, and active Filters only on the first page of each delivery-list section; continuation pages retain the title, page identification, and totals.
- Moves `Printed at` into the bottom-left footer of every page.
- Centers Route in both preview and actual print output.
- Forces gray column-header and glass-type subheader backgrounds to print in Chrome and Edge.

## v0.210 highlights

- Commits Airport to maintained Print / Export state before the GUI becomes visible, rather than relying on the route chip's checked appearance.
- Replaces the redundant reset-then-reapply startup sequence with one awaited initialization transaction.
- Prevents stale route controls from a previous GUI session from overwriting the new session's Airport default.
- Shows loading filter content and disables empty output until the current delivery-list details are ready.
- Makes an immediate Print or Export click wait for initialization and then revalidates the committed Airport route.
- Invalidates late asynchronous work when Print / Export closes or reopens, preventing an older session from replacing the active one.
- Preserves the v0.209 system default preset, landscape sheets, print totals, preset redesign, and schema version 5.

## v0.209 highlights

- Moves Delivery Date directly beside the Filters section title while keeping Create Preset, Saved Presets, and Clear Filters grouped on the right.
- Raises all four header controls to the same larger 12.5-pixel type size with centered labels and icons.
- Rebuilds Create Preset as a guided two-step workspace with a clear naming panel, system-default explanation, usage guide, balanced filter cards, and responsive output controls.
- Adds an immutable **System Default · All Items** preset for every user and applies it automatically when Print / Export first opens.
- Defines the system default as Airport/all outbound items, All Glass, All Status, All Attention, PDF, one copy, and Portrait.
- Preserves user-created presets separately and prevents the reserved System Default name from being overwritten.
- Adds a true landscape delivery-list layout with orientation-specific pagination, tighter row geometry, wider Dimensions and Customer columns, and a shorter notes area.
- Shows Total printable rows, Total orders, and Total QTY above Printed at on every delivery-list sheet and continuation page.
- Replaces the remake sheet's edge border with an inset dashed outline so all four corners remain inside the printer-safe area.
- Preserves v0.208 exact glass matching, the custom range calendar, Lookup Manager glass library, exact order/item selection, PDF/XLSX/CSV output, and schema version 5.

## v0.208 highlights

- Fixes exact glass-type selections showing valid counts while the document preview incorrectly displayed zero rows.
- Stores route and exact glass selections in stable application state before filter controls are replaced or rerendered.
- Filters imported products with normalized Unicode, inch/quote marks, whitespace, and case comparison while retaining the original maintained product label for presets and output.
- Preserves Airport as the complete outbound route without requiring users to click Airport again after choosing a glass type.
- Restores saved glass-type presets against normalized product identities so minor formatting differences do not invalidate a known selection.
- Centers Delivery Date, Create Preset, Saved Presets, and Clear Filters text and icons within their compact header controls.
- Preserves the v0.207 custom-range calendar, Lookup Manager glass library, user-scoped presets, exact print rows, exports, and schema version 5.

## v0.207 highlights

- Removes repeated Delivery Date / Date Range prefixes so the selector displays clean dates and ranges.
- Keeps Custom Range open after the first date, requires a second date, and closes only after Apply Dates or an explicit cancel/outside click.
- Increases Delivery Date, Create Preset, Saved Presets, and Clear Filters text to the same 10.5-pixel size used by filter-chip content.
- Preserves Airport, All Glass, and exact glass selections through initial asynchronous filter rendering so first-use glass filtering no longer produces a false zero-row preview.
- Reflows Create Preset into filled three-column and responsive two-/one-column layouts with no blank section beside Attention.
- Loads every maintained Lookup Manager product value for the Glass Types preset library and displays its friendly product-name label.
- Keeps Create Preset immediate by prefetching the small lookup library and enriching the open modal without loading historical delivery lists.
- Preserves user-scoped presets, exact preview/print rows, PDF/XLSX/CSV output, and schema version 5.

## v0.206 highlights

- Reduced Delivery Date, Create Preset, Saved Presets, and Clear Filters to compact 34-pixel controls.
- Keeps all four Print / Export header controls aligned on one desktop row, with controlled wrapping on narrower screens.
- Rebuilt the Create Preset modal with a clearer name section, polished category cards, improved output controls, and responsive layout.
- Opens Create Preset immediately from already-loaded data instead of fetching every historical delivery list.
- Removed lifetime glass-type quantity totals from preset creation; the builder now stores and displays glass-type names only.
- Added a glass-type search field inside Create Preset for faster selection.
- Fixed Custom Date Range closing immediately when chosen from the enhanced Delivery Date dropdown.
- Preserved user-scoped preset storage, active-preset restoration, exact preview/print behavior, and schema version 5.

## v0.205 highlights

- Gives Delivery Date, Create Preset, Saved Presets, and Clear Filters one consistent 40-pixel control system.
- Keeps Custom Date Range as the first date-selector option while individual delivery dates remain one-click choices.
- Replaces the old mixed single/range calendar with a two-month Date From / Date To range picker.
- Highlights today, marks known outbound dates, and requires both range endpoints before Apply Range is enabled.
- Loads glass types from every currently known delivery list before opening the preset builder.
- Stores presets and the active preset under the signed-in user instead of sharing one browser-wide active choice.
- Automatically reapplies the user's active preset whenever Print / Export is reopened, until that user selects another preset or clears filters.
- Preserves the working v0.204 preview, visual polish, exact item/order selection, and direct-print workflow.

## v0.204 highlights

- Repairs the preview page container that expanded to an extreme off-screen width and left the visible preview pane blank.
- Keeps every preview page centered inside a normal-width, vertically scrollable document stack.
- Uses layout-aware preview zoom instead of applying competing transforms to both the page stack and each sheet.
- Preserves the exact delivery-list sheet markup shared by the preview and the working print popup.
- Rebalances the control center so the filter workspace and document preview fit normal floor-monitor widths cleanly.
- Gives Route, Glass Type, Status, Attention, order search, and selected items consistent card spacing and typography.
- Allows long filter labels to wrap instead of clipping or overlapping their quantity values.
- Refines the Filters header so Delivery Date, Create Preset, Saved Presets, and Clear Filters remain aligned without crowding.
- Polishes the preview toolbar, paper background, page shadow, status badge, zoom controls, and output footer.
- Makes Copies, Layout, File Type, and Print/Export controls wrap safely on narrower panes rather than overlapping.
- Updates the visible footer version and browser cache keys to v0.204.

## v0.203 highlights

- Moves the delivery-date selector into the right side of the Filters heading.
- Lists individual delivery dates in the maintained dropdown and keeps Custom date range as the first choice.
- Opens the existing calendar for custom ranges with today's date highlighted.
- Reorders the filter workspace to Route and Glass Type on top, Status and Attention below, and exact orders/items at the bottom.
- Replaces the Copies dropdown with a one-to-ten increment control.
- Replaces the Layout dropdown with exclusive Portrait and Landscape buttons.
- Prints synchronously from the exact browser preview so popup blockers do not suppress the print window after an asynchronous request.
- Uses CSS `@page` portrait or landscape sizing so the browser print dialog reflects the selected layout.
- Makes the preview and printed document share the same sheet titles, glass grouping, continuation pages, row limits, columns, notes box, Rush styling, and remake styling.
- Removes the failed preview-reconciliation warning and keeps spreadsheet exports on the authenticated exact-row session path.
- Reinforces smart searching by loading current list detail before matching order, item, customer, glass, or Job Nr. text.

## v0.202 highlights

- Replaced GET-only print reconciliation with an authenticated POST selection contract carrying the exact visible row IDs.
- Creates a short-lived same-user output token so Print, PDF, XLSX, and CSV use the same locked selection as the preview.
- Fixed Print List failing after a valid live preview reported that server reconciliation returned no rows.
- Searches order number, item number, customer, and Job Nr. values while typing.
- Lets operators add either one exact item or the complete order to Selected Orders & Items.
- Supports removing exact items and whole orders independently or clearing the complete selection.
- Removes dates and exact customer/order choices from saved presets.
- Adds file type, copy count, and portrait/landscape layout to the Create Preset GUI.
- Moves the compact Create Preset and Saved Presets controls beside Clear Filters.
- Shows every delivery-list preview page in one vertically scrollable document instead of using a page-number selector.
- Adds copy count and portrait/landscape selectors beside the maintained file-type selector.
- Keeps PDF paired with Print List; XLSX and CSV remain paired with Export List.

## v0.201 highlights

- Selecting **All Glass** deselects every exact glass type and represents a true unrestricted glass selection.
- Selecting any exact glass type clears All Glass; clearing every exact type restores All Glass.
- Repaired the live preview gate so All Glass no longer appears as zero selected glass types.
- Keeps All Status and All Attention the same size as the other filter buttons and positions each in the top-left of its section.
- Moves Date Selection to the top of the Print / Export filter workspace.
- Adds one calendar GUI with Single Date and Custom Range modes.
- Highlights today's date and marks dates that have outbound delivery lists.

## v0.199 highlights

- Forces white text and quantity counts on every selected Print / Export filter.
- Converts customer, Job Nr., and order searching into an explicit multi-order picker.
- Keeps selected orders in a removable list with individual and Clear All controls.
- Stores selected exact orders in browser presets and sends them to preview, print, PDF, and XLSX output.
- Replaces the browser prompt with a dedicated Save Preset GUI and overwrite guidance.
- Places Route choices in a vertical rail on the right side of the filter workspace.
- Narrows the preview pane and renders a letter-shaped delivery-list page using the real print columns and glass grouping.
- Draws a live preview immediately from loaded rows, then reconciles it with the exact backend print package.
- Keeps the live preview visible as a fallback if exact preview reconciliation fails instead of leaving a blank page.

## v0.198 highlights

- Removed the Stage filter from Print / Export and made Route the primary list selector.
- Added the maintained Route choices: Airport, Indian Trail, Greenville, CPU, and DTC.
- Airport includes every item on the selected Airport Outbound delivery lists; destination routes filter those outbound items to the selected destinations.
- Repaired the missing Route, Status, Attention, and Glass Type sections by removing a call to a nonexistent browser helper.
- Added a Quick Date selector that sets the start and end dates to one available delivery date while preserving the full date-range controls.
- Rebuilds Glass Type choices from the glass types that actually exist in the selected date range and route selection.
- Added smart Search suggestions that surface matching orders while typing a customer, complete or partial order number, or Job Nr.
- Extended backend search matching to Job Nr., product, and source identifiers so preview, print, and XLSX remain aligned.
- Removed the extra decorative circle from the Print / Export header.
- Preserved the exact backend preview, output safeguards, presets, PDF/XLSX controls, and scanner-panel header.

## Start the local web app

1. Keep `Start-DeliveryScannerWebApp.bat` and `Start-DeliveryScannerWebApp.ps1` beside `server.py`.
2. Keep the existing `data`, `assets`, `sounds`, and `static` folders in the project folder.
3. Double-click `Start-DeliveryScannerWebApp.bat`.
4. Keep the launcher window open while the local server is running.

SQLite remains the active/default database. The production database is:

`data\delivery-scanner-pilot.db`

Keep this file and its `-wal`/`-shm` companions together whenever the app is running. Before any numbered schema upgrade, startup creates and verifies a version-labeled backup under `data\backups`. Production databases are never deleted or recreated automatically.

## Database preservation

The `data` folder is production state, not application source. Never replace or delete it during a code-only update. Stop the server and copy the complete folder, including SQLite `-wal` and `-shm` companions, before transferring a floor database to another checkout.

## Cross-delivery-date scanning

The settings are available under **Admin > Cross-Date Scanning**:

- **Disabled** — scans remain limited to the selected delivery list.
- **Ask before switching** — every valid cross-date match requires operator confirmation.
- **Automatically switch unique matches** — one safe match switches and scans automatically; ambiguous or guarded matches require confirmation.

The default search window is:

- Past delivery dates: **7 days**
- Future delivery dates: **30 days**

The backend always checks the selected list first. Cross-date searching begins only when the barcode cannot be uniquely resolved on that list. Candidate lists must be active, inside the configured date window, accessible to the signed-in user, and in the same operational stage category.

The existing safety rules remain authoritative. Cross-date scanning does not bypass:

- completed quantity checks;
- duplicate handling;
- user stage access;
- outbound staging and transportation requirements;
- Indian Trail outbound requirements;
- rack status and destination compatibility;
- manual bay selection;
- supervisor override workflows; or
- undo/redo and immutable scan history.

## Automated delivery-list imports

The maintained automation package is under `automation\sql_delivery_export`.

### Floor computers: import the shared folder every hour

1. Extract the newest changed-files package into the current scanner project folder.
2. Close the scanner web app/server window.
3. Run `automation\sql_delivery_export\Setup-DeliveryListSqlAutomation.bat` once.
4. Restart the scanner web app and confirm **Admin > Delivery Automation Control Center** shows **Import Temp Folder Only** with the schedule installed.
5. Run `C:\DeliveryListAutomation\Run-Now.cmd` for a visible manual verification.

The floor setup copies the maintained runtime to `C:\DeliveryListAutomation\Scripts`, uses the existing shared Temp Delivery Lists folder, creates a 60-minute incremental task plus the normal daily full-window safety task, and disables the older built-in 5 PM importer for that Windows user. It does not query A+W SQL or replace the scanner database.

### Central authorized computer: query SQL, export, and import

Use the normal SQL automation setup and the Admin control center. Run `C:\DeliveryListAutomation\Verify-SQL-And-Import.cmd` with a known delivery date to verify the read-only SQL query, workbook generation, publication, maintained scanner import, and expected stage lists.

See `automation\sql_delivery_export\README.md` for the installed runtime and troubleshooting steps.

## Database operations

- Azure migration dry run: `py -3 -m database.migrate_sqlite_to_azure_sql --sqlite-path data\delivery-scanner-pilot.db`
- SQLite migrations are owned by `database\migrations.py`.
- The logical cross-database contract is owned by `database\contract.py`.
- v0.256 application contract: **256**.
- v0.253 application contract: **253**.
- v0.246 application contract: **246**.
- v0.235 application contract: **235**.
- Current SQLite schema contract: **5**.

## Optional container deployment

Docker and Azure App Service support files are organized under `deployment`. They are not required for normal Windows floor operation.

- Container definition: `deployment\docker\Dockerfile`
- Container-only dependencies: `deployment\docker\requirements.txt`
- Azure App Service setting template: `deployment\azure\app-service.env.example`

Run the Docker build from the project root so the root `.dockerignore` protects local databases, secrets, logs, backups, and verification output:

```powershell
docker build -f deployment/docker/Dockerfile -t delivery-list-scanner .
```

## Audio language

The maintained sound pack is stored under `sounds\` as 44.1 kHz, 16-bit PCM mono WAV files. Open `sounds\preview_audio_pack.html` in a browser to audition the packaged cues without installing audio software. The web app loads semantic cue names from `static\js\app.js`, uses the existing shared volume/compressor chain, and falls back to synthesized tones only if a WAV file cannot be loaded.

v0.194 maps `delivery_date_changed` to the already packaged `sounds\scan_success.wav` cue. Normal accepted scans continue using `sounds\notification.wav`, so no binary sound asset is included in this changed-files release.

## Microsoft Graph email

Microsoft Graph delivery supports customer manifests, ready notices, and Admin test messages. The configured sender is `BarefootNC.Glass@bldr.com`, and the default controlled test recipient is `brandon.m.smith@bldr.com`.

After BLDR IT provides the Entra tenant ID, application/client ID, and client-secret value, run `Configure-MicrosoftGraphEmail.bat` once. The secret is encrypted for the current Windows account and loaded only in memory by the normal scanner launcher.

## Project documentation

- Ongoing version history: `README_CHANGELOG.md`
- Current folder ownership and cleanup guide: `docs/PROJECT_STRUCTURE.md`
- Automated SQL export/import runtime: `automation/sql_delivery_export/README.md`

## Important local folders

- `static` — maintained browser CSS, JavaScript, and image source.
- `assets` — favicon and print-page assets referenced by the server.
- `sounds` — maintained browser audio cues.
- `data` — required SQLite database and local scanner state. Keep it and back it up.
- `automation` — scheduled delivery-list import/export source and setup scripts.
- `scripts` — optional Windows setup and diagnostic utilities.
- `resources` — source material retained for A+W integration work.
- `logs` — generated diagnostics. Safe to clear while the app is stopped.
- `backups` — retained recovery copies. Review dates before removing anything.
- `C:\DeliveryListAutomation` — installed automation runtime, staging, logs, and task state.

The release ZIP contains no database, SQL credential, SAP runtime, demo delivery list, or new audio binary. When upgrading, keep the existing `data` folder. Production startup never seeds demo delivery lists; existing data is preserved and upgraded in place only after a verified backup succeeds.

Do not run the SQLite and Azure SQL versions as simultaneous writable production systems during a future cutover.
