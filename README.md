# Delivery List Scanner

Current maintained release: **v0.472**. SQLite remains the active/default backend.

v0.472 finishes the production-file workflow without putting network-share traversal on scanner or Smart Search request threads. It adds persisted machine/file settings, actual-machine evidence overrides, order-centered Scan review, and whole-order production-file access while preserving the v0.471 Statistics selector fix.

## Install v0.472

1. Stop the Delivery List Scanner server.
2. Copy the v0.472 changed files over the matching paths in your current project.
3. Start the server again so the backend/frontend release are both v0.472.
4. Hard-refresh open browser sessions (`Ctrl+F5`) so the v0.472 cache keys are used.

SQLite schema remains **version 11**. No migration or database reset is required.

## v0.472 highlights

- Moved production-share discovery to a persisted background index. Scanner transactions and Smart Search return from cached metadata instead of recursively walking mapped or UNC shares.
- Added **Machine & Production Files** settings for share roots, machine terms, refresh interval, integration enablement, and the Staging fabrication gate. The new permission is available in Role Manager and Admin remains the non-lockout recovery role.
- Treats Sketch machine assignment and completion evidence separately: a WJ-assigned item with an exact `.egl` reports Denver completion, while a Denver-assigned item found in Completed WJ reports Waterjet completion.
- Keeps unavailable evidence shares fail-safe and nonblocking. A Staging rejection occurs only for an exact, confidently assigned item whose relevant completion share is available and lacks matching evidence.
- Groups Scan table work by Order within the maintained glass-type sections. Each order header shows Job Nr., customer, attention count, and scanned piece progress; double-click opens the existing Order Details workflow.
- Expanded Order Details with whole-order sketch/hardware access while retaining exact item sketches, programs, fabrication status, and synchronized stage progress.
- Fixed stale Smart Search responses so an older network response cannot replace results for the operator's newer query.
- Added focused regressions for cross-machine evidence, settings persistence, nonblocking network indexing, Admin permissions, and the v0.472 UI contract.
- Advanced browser cache references and `APPLICATION_VERSION` to **v0.472** while keeping SQLite schema version **11** unchanged.

## v0.471 highlights

- Fixed the Statistics **Common glass sizes** glass-type selector opening with an empty custom menu when report options arrived after the menu had already been opened.
- Dynamic custom selects now detect option-set changes and rebuild an already-open body-portal menu in place while preserving any active option search.
- Common glass sizes shows **Loading glass types…** while its report query is in flight and **No glass-size data in this range** for a genuinely empty reporting range instead of presenting a blank control.
- Entering Statistics now retries the report query when report-only data is missing; choosing Common glass sizes also triggers that recovery path when needed.
- Verified the maintained report backend against the supplied production database: populated glass-size frequency data is returned for active reporting ranges, and the existing rotated-dimension normalization regression remains green.
- Advanced browser cache references and `APPLICATION_VERSION` to **v0.471** while keeping SQLite schema version **11** unchanged.

## v0.470 highlights

- Corrected the Bay Map shuttle layering/timing: Outbound panes now load **right-to-left**, above the dotted route but behind the truck; Indian Trail panes stay invisible until the truck has arrived and turned for unloading.
- Finished Print / Export **All Glass Types** selected-state contrast by forcing both the label and numeric count to white.
- Standardized Settings/Admin edit, save, and delete controls on the shared pencil/save/trash icon owner and ensured Delivery List Management exposes the shared pencil action immediately before each stage Reset control.
- Reworked Lookup Manager so the library uses the full modal width. **Add New** and row Edit actions open the maintained form as a focused secondary GUI instead of permanently occupying the left side; the foreground editor remains crisp while its library backdrop is subdued.
- Fixed Priority Work print-window handling for Rush, Remake, and Missing Glass sheets and reduced repeated explanatory/detail text in intake and Work Center while preserving the unified v0.469 behavior.
- Added **Common glass sizes** to Statistics. Operators select a glass type and can rank its most frequent dimensions by physical pieces within the active reporting range.
- Rebalanced Scan table widths so Job Nr. receives more space while Order Nr. and Item remain compact but large enough for their headers/normal production values.
- Made completed racks read-only for contents at both browser and backend layers. Move/remove/clear actions require the rack to be marked **Incomplete** first.
- Moved Bay Map secondary actions into clickable cards below In Transit and added a **Hardware** card with order/hardware search.
- Added a Scan-row double-click **Order Details** GUI with grouped order/item/stage information plus matching Hardware Lists, Sketches, Programs, preview/print actions, and Windows program launching.
- Added cached production-share discovery for `Hardware Lists`, `Sketches`, `Programs`, and `Completed WJ`. Sketch text/filenames are used conservatively to identify Denver CNC or Waterjet assignments; `.egl` is exact-item Denver evidence and matching Completed WJ files are Waterjet evidence.
- Added a fail-safe pre-Staging fabrication check. A confidently assigned Denver/Waterjet item is blocked and logged as an Error only when the matching evidence folder is available and exact-item completion evidence is missing. Unavailable shares or ambiguous/image-only sketches remain non-blocking. Fabrication state is also appended to Smart Search stage status.
- Reorganized the compact Scan filter glance to **Err / New / IR / RM / R**, lights Errors red when present, makes ON THE WAY rack locations blue, and enlarges the active Delivery List date title.
- Added regression coverage for exact-item Denver evidence, Waterjet completion, disconnected-share safety, completed-rack content locks, and the maintained unified Priority Work flow.
- Advanced browser cache references and `APPLICATION_VERSION` to **v0.470** while keeping SQLite schema version **11** unchanged. No migration or database reset is required.

## v0.469 highlights

- Rebuilt **Priority Work** around one central New Request workflow. Operators choose **Rush**, **Remake**, or **Rush + Remake** instead of switching between separate request systems.
- The Job Nr. / SO / Order lookup checks active imported delivery lists as the operator types. If the work already exists, the GUI shows the matched customer/order/pieces/stages and can apply Priority Work immediately. If it has not been imported yet, the same request is saved durably and waits for a future authoritative import.
- Existing imported work can keep its current delivery date or receive a new priority delivery date before the Rush/Remake/Both mark is applied across every synchronized stage copy of the same physical Order/Item.
- **Missing Glass Rush is no longer a standalone workflow or flag type.** Missing Glass is a reusable reason under Rush, Remake, or Rush + Remake. Historical existing-order Rush marks continue to read as Rush with their saved reason instead of resurrecting a separate Missing Glass Rush classification.
- Added **Rush**, **Remake**, and **Missing Glass** printout actions directly to the Priority Work GUI. The paperwork can be printed before an order imports (with the request details) or after a match (including the imported order/item/glass/dimensions/quantity rows).
- Work Center now organizes active requests into Rush, Remake, and Rush + Remake sections. Requests with a Missing Glass reason can print the dedicated Missing Glass sheet without becoming a separate priority type.
- Pending priority delivery dates are carried into the matched imported stage copies, and combined requests persist both Remake and Rush state. Existing audit/notification/import reconciliation paths are reused rather than introducing a duplicate priority table.
- Advanced browser cache references and `APPLICATION_VERSION` to **v0.469** while keeping SQLite schema version **11** unchanged. No migration or database reset is required.

## v0.468 highlights

- Added **Whole Delivery List** to the Manual Edit scope selector. It shows each logical Order/Item once for the selected delivery date and saves shared order fields across every synchronized stage copy. Stage-owned **Scanned** progress and physical **Location** remain protected and editable only from a specific stage.
- Whole-list Manual Edit search/filtering is scoped to one delivery date and de-duplicates stage copies by the same durable physical-line identity used by the existing synchronization path. Glass filter counts also count each logical line once instead of multiplying by stage count.
- Fixed the selected **All Glass Types** Print / Export chip so its visible label is white like the other selected All-filter buttons.
- Removed the old decorative empty circle from the compact **Delivery list changes** preview header.
- Consolidated icon-only **Save** and **Delete** buttons into one late-loaded shared visual profile. Save stays navy/blue with white ink on hover; Delete stays white/red and becomes red/white on hover, preventing the Manual Edit save button from flashing white.
- Added regression coverage proving whole-list editing updates shared Customer/Dimensions/Qty across all stage copies while preserving each stage's existing scanned quantity.
- Advanced browser cache references and `APPLICATION_VERSION` to **v0.468** while keeping SQLite schema version **11** unchanged. No migration or database reset is required.

## v0.467 highlights

- Increased Scan filter-count numerals slightly without enlarging the surrounding filter chips; Print / Export filter counts receive the same readability bump.
- Changed the Delivery List row default from **25 to 50** and added **200** as the new maximum Rows option in both the top and bottom pagers. Operators can still choose 25, 50, or 100.
- Rebuilt the positive-load Bay Map shuttle sequence around exact per-pane timing. Glass panes now remain separate, load one at a time into the rear cargo area, travel on a layer behind the truck instead of over the roof/cab, and disappear only after they are fully occluded by the truck body.
- Truck departure is no longer tied to a rough percentage of the animation. It waits until the final visible pane has completely loaded, then holds at Outbound for an additional **2 seconds** before leaving. Inbound unloading is individually sequenced as well, with the truck remaining docked through the complete unload and dwell.
- Preserved the v0.459 load-aware piece count and zero-piece waiting-cloud behavior. The existing 120-pane safety ceiling remains for extreme loads.
- Advanced browser cache references and `APPLICATION_VERSION` to **v0.467** while keeping SQLite schema version **11** unchanged. No migration or database reset is required.

## v0.466 highlights

- Removed parentheses from Scan filter quantities across Status, Attention, Route, and Glass Type. Counts now render as clean numeric badges such as `4` instead of `(4)`; Print / Export already used bare numeric counts and remains consistent.
- Replaced the simple luminance threshold for selected glass filters with a direct contrast-ratio comparison between white and navy ink against the actual color-filled chip. Vivid Mirror/Tempered colors now automatically choose the more readable label color.
- Separated the exact-glass count badge from the glass-colored label ink. Selected Scan and Print / Export glass filters use a pale count pill with dark navy numerals, preventing white-on-white count text on purple/green selections.
- Standardized selected filter count badges so ordinary active filters keep white counts on app blue while exact glass selections keep dark counts on a pale surface.
- Advanced browser cache references and `APPLICATION_VERSION` to **v0.466** while keeping SQLite schema version **11** unchanged. No migration or database reset is required.

## v0.465 highlights

- Corrected Print / Export preview geometry without changing the actual printed delivery list. The preview Letter-paper shell now uses an outline instead of a layout-affecting border, leaving the same exact `.4in` printable margins and `10.2in` / `7.7in` printable heights as the real portrait/landscape print job. This removes the small landscape bottom-edge difference and restores the portrait Check column to the same usable width as paper.
- Exact glass-type selections in both Scan filters and Print / Export now fill the complete choice with that glass type's canonical Lookup Manager color. The former app-blue check badge is removed; selected text automatically switches between dark and white ink based on the saved color's luminance.
- Moved **New Orders / New/Updated** and **Errors** into the **Status** filter group. **Attention** now contains only **Rushes, Remakes, and Internal Rejects** on Scan, Print / Export, and the saved Print Preset editor. Older saved presets are migrated in memory so their Updated/Error selections are preserved.
- Updated Print / Export backend exact-status matching so Status choices remain OR-combined even when New/Updated or Errors are selected, matching the browser filter behavior.
- Expanded the Scan **Route** filter section to the same full drawer width as **Glass Type** for a more balanced filter layout.
- Advanced browser cache references and `APPLICATION_VERSION` to **v0.465** while keeping SQLite schema version **11** unchanged. No migration or database reset is required.

## v0.464 highlights

- Increased the complete Scan glass-type group band from **38px to 43px** after floor review. The inner foreground control is **41px**, preserving the intentional 2px structural allowance without returning to the old 54px table-cell height.
- Preserved the glass-color gradient, static sheen, NEW/UPDATED badge treatment, piece count, and Collapse/Expand controls unchanged.
- Advanced browser cache references and `APPLICATION_VERSION` to **v0.464** while keeping SQLite schema version **11** unchanged. No migration or database reset is required.

## v0.463 highlights

- Fixed the remaining Scan glass-type header height at the actual table-layout source. The shared Delivery List cell rule reserves 54px for normal item rows; v0.462 shortened only the inner header button, so the parent glass-group cell still painted a taller second color layer.
- Glass-group structural rows now explicitly own a compact **38px** row/cell height, with the foreground control held to **36px**. The glass name, NEW badge, piece count, Collapse/Expand control, gradient, and static sheen remain intact without the extra vertical band.
- Advanced browser cache references and `APPLICATION_VERSION` to **v0.463** while keeping SQLite schema version **11** unchanged. No migration or database reset is required.

## v0.462 highlights

- Reduced Scan glass-type group headers from the 42px reference height to a compact 36px control height, with slightly smaller count/toggle pills so the header occupies less vertical space without crowding its text.
- Rebuilt the group-level **New / Updated** badge as a semantic `mark` element. This removes it from the older broad `span/strong/b` white-text selector entirely, while an exact final owner forces dark ink, yellow fill, and dark text fill for reliable contrast.
- Increased the fixed glass-header sheen modestly with a wider, brighter highlight band. The sheen remains completely static and has no animation.
- Advanced browser cache references and `APPLICATION_VERSION` to **v0.462** while keeping SQLite schema version **11** unchanged. No migration or database reset is required.

## v0.461 highlights

- Lookup Manager **Uncombine Glass Types** now reconstructs saved combinations from persisted alias rows instead of depending on the current-session target label. Alias payloads expose a stable normalized target identity, the browser sends durable alias IDs when separating, and the backend can also match older target labels by physical glass-profile identity. This keeps combinations created on older versions reversible after a server restart or later naming normalization.
- The Statistics command header is now a true dark-blue/navy banner with high-contrast white title/copy, readable live-range/status chips, and translucent light actions while retaining the shared non-Home header geometry.
- Fixed the Scan glass header **New/Updated** text at the actual winning CSS specificity. The nested yellow marker now explicitly owns black ink/text-fill even against the older broad white-text group-header rule.
- Rebuilt the Scan glass-header sheen as a static pseudo-element overlay above the canonical glass gradient. This makes the highlight visibly present without animation and without changing the Lookup Manager glass color.
- Added regression coverage for uncombining an alias created under the older `3/8 Clear` target after recreating the store, proving the current `3/8 Clear Annealed` profile can still separate it.
- Advanced browser cache references and `APPLICATION_VERSION` to **v0.461** while keeping SQLite schema version **11** unchanged. No migration or database reset is required.

## v0.460 highlights

- Clear glass now always has an explicit operational heat-treatment identity. Imported/source labels such as **3/8 Clear**, **1/2 Clear**, **1/4 Clear**, **1/8 Clear**, and **3/8 UltraClear** that omit both Tempered and Annealed are treated as the corresponding **Annealed** glass type for grouping, Statistics, print/export summaries, and operator-facing glass labels. Explicit Tempered and Annealed names remain separate. Historical source product text is preserved unchanged.
- Updated the built-in clear-glass cost/reference names to use explicit **Annealed** labels so Lookup Manager and reporting no longer advertise an ambiguous standalone `3/8 Clear` glass type.
- Added a canonical `glassType` field to line-item/event payloads while keeping the original imported `product` field intact, allowing clients to consistently group legacy clear-glass rows without rewriting database history.
- Scan glass-group **New/Updated** badges now use black text even inside white-text glass headers, preventing the inherited header color from washing out the `New` label.
- Added a subtle fixed sheen layer to Scan glass-type headers. The sheen is static (no animation) and preserves the compact v0.459 dark Lookup Manager gradient.
- Added regression coverage proving raw `3/8 Clear` reports as `3/8 Clear Annealed`, explicit `3/8 Clear Tempered` remains Tempered, and Statistics never emits a standalone `3/8 Clear` category.
- Advanced browser cache references and `APPLICATION_VERSION` to **v0.460** while keeping SQLite schema version **11** unchanged. No migration or database reset is required.

## v0.459 highlights

- Bay Map shuttle load visuals now scale much more directly with **pieces on the way**. Normal floor loads render one animated pane per physical piece, with stack spacing compressed as counts rise so the lane remains readable. A generous safety ceiling protects the page from pathological DOM growth without changing the maintained numeric transit count.
- Shuttle timing is recalculated from load size: heavier glass loads receive longer Outbound loading and Indian Trail unloading pauses, while small loads move through a shorter cycle.
- The **0 pieces** state remains physically parked at Outbound, but the waiting thought-cloud has been refined so its three dots read as a clearer left-to-right sequence.
- Statistics glass colors now resolve through one explicit canonical Lookup Manager helper before chart rendering, including combined aliases. If the lightweight glass-color library finishes loading after Statistics first paints, the page immediately rerenders so generated fallback colors cannot remain on screen.
- The Statistics header is one step darker while staying inside the shared pale-blue workspace family.
- Scan glass-type section headers now follow the approved reference more closely without the decorative glass icon: a compact 42px dark glass-colored gradient band, strong white glass name at left, bordered piece-count pill, and a compact Collapse/Expand control at right.
- Advanced browser cache references and `APPLICATION_VERSION` to **v0.459** while keeping SQLite schema version **11** unchanged. No migration or database reset is required.

## v0.458 highlights

- Bay Map shuttle animation now derives its visual load from the live **pieces on the way** count. Small loads show only the matching number of glass panes; larger loads compress the visual stack up to a practical display cap while the exact piece count remains in the maintained transit label.
- Shuttle cycle duration now scales with the in-transit quantity, so larger glass loads spend longer at the Outbound loading pause and Indian Trail unloading pause instead of using one fixed wait for every run.
- When **0 pieces** are in transit, the shuttle no longer drives an empty loop. It waits at the Outbound side with a small thought-cloud whose three dots animate left-to-right, clearly communicating that the truck is waiting for glass to be loaded.
- Statistics **Glass mix by quantity** and **Glass type breakage** entries now carry the canonical Lookup Manager glass color into Bar, Donut, Line-point, and Table-swatch rendering. Combined aliases continue resolving through their canonical target profile, so Statistics matches Scan and other glass-aware interfaces.
- Darkened the shared pale-blue Statistics header slightly while preserving the v0.457 139px geometry, accent rail, circle decoration, and overall application styling.
- Advanced browser cache references and `APPLICATION_VERSION` to **v0.458** while keeping SQLite schema version **11** unchanged. No migration or database reset is required.

## v0.457 highlights

- Edit Users now exposes **Display name** in each expandable account card. Saving Access & profile changes updates display name, email, role, and station assignments through the same audited profile transaction instead of adding a duplicate user endpoint.
- Increased every primary page header except Home by about **20%** (116px → 139px desktop) through the final shared UI layer so Statistics, Scan, Racks, Rejects, Bay Map, and Admin keep one consistent header scale. Home retains its established hero proportions.
- Removed the repeated Statistics analytics subtitle/range sentence, enlarged the **Filter categories** search field, reduced Reset to a compact fixed action, and converted the analytics toolbar to a flexible row that fills the available width cleanly.
- Home Delivery Library expansion no longer removes/re-adds animation classes or forces a layout flush. The native `[open]` state owns one smooth reveal, so the animation replays on every reopen without the visible restart flash.
- Scan glass-type group headers use a softer, darker canonical glass gradient with a subtle framed border and gentler hover surface, keeping Lookup Manager identity without the overly bright stripe effect.
- Indian Trail receive confirmation now shows **Job Nr. before Customer**, adds **Dimensions** and **QTY**, removes the redundant Item metadata pill, and grows about 15% from the v0.456 compact size to make the added verification data readable while keeping the styled Done action.
- Rebuilt Bay Map endpoint motion around a new 16-second shuttle cycle: sequential translucent light-blue panes load from the left into the truck at Outbound, the truck travels and flips at Indian Trail, then panes unload sequentially out to the right before the truck returns. Reduced-motion behavior remains static.
- Advanced browser cache references and `APPLICATION_VERSION` to **v0.457** while keeping SQLite schema version **11** unchanged. No migration or database reset is required.

## v0.456 highlights

- Matched the desktop footer to the same navy/radial gradient owned by the sidebar so the application shell reads as one continuous frame.
- Brought the Statistics header onto the exact shared 116px page-header geometry, added the same open-circle decoration and left accent rail used by the other primary workspaces, and increased color saturation/contrast across analytics cards, KPI surfaces, chart controls, and supporting panels.
- Removed the outer **Priority metrics** section card while keeping the four priority statistic cards as a standalone dashboard row. Their semantic warning/success/open colors are brighter and easier to scan.
- Standardized all Statistics analytics selector bars to the same 42px height. Reporting range labels now use compact numeric `M/D/YYYY` dates while the maintained two-month calendar interaction remains unchanged.
- Home Delivery Library date groups explicitly restart their reveal animation on every collapse/re-expand cycle. The **Open stage** label is forced white when its stage card/button is hovered or focused so it stays readable on the colored action surface.
- Scan glass-type group headers now consume three dark gradient stops precomputed from the canonical Lookup Manager glass color, producing a clear glass-hue-to-navy gradient instead of a flat colored strip.
- Reduced the Indian Trail receive confirmation to a substantially smaller floor-friendly footprint while preserving scanned-order metadata, the BAY destination hero, Bay override controls, and All Scans hint. The **Done** button now has an explicit green primary-action treatment.
- Advanced browser cache references and `APPLICATION_VERSION` to **v0.456** while keeping SQLite schema version **11** unchanged. No migration or database reset is required.

## v0.455 highlights

- Fixed the remaining Scan glass-group header issue at its actual cascade source. v0.454 colored the surrounding table cell, but an older opaque blue `button` background still covered that color. The glass-group button is now transparent and the visible header surface uses the canonical Lookup Manager glass hue darkened into a high-contrast band, with strong white glass name/count/collapse text.
- Repaired the Indian Trail success notification packaging/formatting issue. The v0.453 popup markup lived in `app.js`, while its layout overrides lived in `styles.css`; because the following v0.454 package was incremental and did not include `styles.css`, an installation that skipped the v0.453 full package could run the new markup with the old generic grid rules. v0.455 deliberately includes and strengthens the authoritative `styles.css` layout so scanned-order metadata pills, the large BAY hero, enlarged Override Bay selector, side-by-side Move action, helper hint, and bottom-right Done button remain aligned.
- Removed the v0.454 Table-only date selector and its temporary range-snapshot logic. Statistics now has one **Chart date range** calendar directly in the analytics toolbar, and the same selected Date From / Date To applies consistently to Bar, Line, Donut, and Table views and every Data selection.
- The analytics range control reuses the maintained two-month calendar interaction used elsewhere in the app, displays the active date span directly on the control, preselects the current reporting range when opened, and continues to drive the existing authoritative report query instead of introducing duplicate aggregation logic.
- Preserved the v0.454 Statistics header alignment, removal of Delivery lists / Delivery dates from the Data selector, complete Table rows, and expanding non-scrolling Bar chart.
- Advanced browser cache references and `APPLICATION_VERSION` to **v0.455** while keeping SQLite schema version **11** unchanged.

## v0.454 highlights

- Scan content-group headers now use the exact Lookup Manager glass-type hue as their visual source, darkened into a strong readable header surface. Glass names are high-contrast white instead of faded blue-gray text, while combined glass aliases continue resolving through the canonical profile color added in v0.452.
- Statistics now uses the same pale blue-gray page-header language as the rest of the application instead of a separate dark navy command banner. The reporting date selector and status elements use the same neutral control surfaces as the main workspaces.
- Removed the **Delivery lists** and **Delivery dates** groups from the Statistics Data selector. Workflow stages, production mix, breakage/rejects, and people/activity remain available.
- Table view now exposes a dedicated **Table date** filter. Choosing one delivery date temporarily focuses the existing authoritative Statistics range/report query on that date; leaving Table view or choosing **Use page range** restores the prior reporting range instead of maintaining a second client-only calculation path.
- Table view always expands to every matching row rather than inheriting the chart Top 10/20/etc. limit, making it the complete review surface for the selected date/range.
- Bar charts no longer create an internal vertical scroll area. Their SVG height expands with the visible category count and scales to the available desktop width; small screens retain horizontal overflow only when necessary.
- SQLite schema remains version **11**; no migration or database reset is required.

## v0.453 highlights

- The Bay Map in-transit animation now uses clearer light-blue glass motion at both endpoints: on the Outbound side the panes approach from the left and move into the truck, while on the Indian Trail side the panes move out from the truck toward the right. The artwork remains intentionally simple and reduced-motion behavior stays unchanged.
- Rebuilt the Indian Trail receive success notification into a wider, cleaner layout. The top section now emphasizes the scanned order with structured customer/job metadata pills instead of the older repeated headline copy.
- Kept the large destination hero but removed the redundant Order/Job line beneath the bay name, enlarged the "PLACE THIS ORDER IN" label, enlarged the Override Bay selector, and placed the Move to selected bay action directly beside it for quicker correction.
- Moved the Done action to a clear bottom-right footer position and preserved the All Scans helper link/hint without forcing the notification to grow taller.
- Advanced browser cache references and `APPLICATION_VERSION` to **v0.453** while keeping SQLite schema version **11** unchanged. No migration or database reset is required.

## v0.452 highlights

- Combined Glass Types now load color metadata and alias metadata together for every authenticated operator. A combined source name can retain its old stored color for reversible uncombine, but while combined it always renders with the canonical target profile's configured color. Stable fallback colors are also shared across all aliases in an unconfigured combined family.
- Historical rack locations labeled **PRIOR** now use a neutral gray rack surface/rail instead of the rack set's active color, making completed transportation visually distinct from current rack assignments.
- Indian Trail now validates both **Staging** and **Outbound** prerequisites. If either is missing and a supervisor overrides the receive, both stage copies are reconciled to the received quantity as needed.
- Reconciled prerequisite quantities are stored as explicit `scan_override_it` events with station label **Scan Override IT**. Staging/Outbound line timestamps display **SCAN OVERRIDE IT: <date> at <time>** instead of presenting the synthetic event as a normal ON TIME/LATE Airport scan. Synthetic override events are excluded from delivery timeliness metrics.
- The Bay Map shuttle keeps the v0.451 endpoint-aligned progress meter but replaces rack sprites with three simple light-blue vertical glass panes that slide into the truck at Outbound and out of the truck at Indian Trail during the endpoint pauses.
- Added regression coverage for combined glass alias/color metadata, full prerequisite override history, synthetic timing exclusion, and a legacy mismatch where Outbound is present but Staging is missing.
- SQLite schema remains version **11**; no migration or database reset is required.

## v0.451 highlights

- Priority ribbon rows now explicitly override the shared 54px Delivery List cell height. Rush, Remake, and Missing Glass banners collapse to their own compact height and sit directly on the line item with no inherited white band beneath them.
- Global Search now treats each meaningful term as an **AND** condition across the same order. Queries such as `73 x 64 rush`, `73x64 remake`, or `ALPHA BUILDERS rush` can combine dimensions, flags, customer/job information, route, order/item identifiers, product, stage, delivery date, rack/bay data, and other maintained line metadata.
- Rush, Remake, and Missing Glass Rush are directly searchable as flags. Priority reason/responsible metadata participates in the same search without duplicating the priority classification rules; results continue to use the shared `priority_banner_annotations` resolver.
- Dimension separators (`x` / `×`) are normalized for search, so spacing around the separator does not change the result. Every term must match the same physical order result rather than independently matching unrelated records.
- The Bay Map in-transit dual progress meter now ends beneath the shuttle's actual left/right stopping points instead of stretching edge-to-edge. During the existing endpoint pauses, a small glass rack visibly unloads at Inbound and another rack loads at Outbound before the truck reverses direction. Reduced-motion users keep the static truck without transfer animation.
- Added regression coverage for combined size + flag search, direct flag searches, Missing Glass Rush, compact dimension syntax, customer + flag combinations, and priority reason/responsible searches.
- SQLite schema remains version **11**; no migration or database reset is required.

## v0.450 highlights

- Priority ribbons were shortened and their internal padding reduced as the first density pass for flagged Delivery List work.
- Smart Search priority flags use high-contrast states: **Rush** is bright red, **Remake** is near-black, and **Missing Glass Rush** is bright red-orange. Smart Search reuses the maintained backend priority annotation resolver so these states do not introduce duplicate classification logic.
- The Indian Trail receive success notification keeps the large **PLACE THIS ORDER IN / BAY** destination hero while reducing the supporting icon, selector, helper text, and action buttons to normal interface sizing.
- After an item is scanned out from the Bay Map, Inbound Location keeps its most recent Bay as history and shows the same explicit **PRIOR** lifecycle label used for historical rack locations.
- Added a 20-piece regression that stages ten two-piece orders into one rack, scans the rack Outbound, verifies all Outbound Bay preassignments, receives every piece one by one while confirming the rack clears one piece at a time, scans all pieces out from the Bay Map, and confirms Bay history remains available afterward. Manual Scan is exercised during Staging, Inbound receive, and Bay Map scan-out.
- Added Rush intake, Remake intake, and Missing Glass Rush lifecycle coverage through Smart Search, Staging, Outbound rack scan, Inbound Bay receipt, and Bay Map removal.
- SQLite schema remains version **11**; no migration or database reset is required.

## v0.449 highlights

- An explicit Indian Trail / Inbound prerequisite override now backfills the same physical item on **Staging and Outbound** to the received quantity, with dedicated audit/scan events instead of leaving those stage copies at zero.
- Any active rack assignment for the overridden physical item is removed automatically. The former rack remains historical and is labeled **OVERRIDDEN BY IT** rather than generic PRIOR.
- Inbound receive still promotes the physical Bay to current Location; Bay assignment identity is exposed so a selected Inbound row can change its Bay inline using the same low-friction pattern as rack reassignment. Received Bay moves remain **Received** rather than being downgraded to a generic moved state.
- Legacy stage-sequence progress such as `IT received 1; Outbound 0` is stacked as separate **Received** and **Outbound** lines with the second line indented so the Progress column cannot clip it.
- Strengthens sticky Scan Stage selector pointer/stacking ownership after page scroll.
- Preserves v0.448 rack lifecycle labels, durable Bay refresh, and authoritative ON TIME/LATE metrics.
- SQLite schema remains version **11**; no database reset or migration is required.

## v0.439 highlights

- Smart Search Stage cells now show the **Stage Lookup Manager display name**, not rack/bay/truck location wording.
- Keeps **Stage + Scanned** together as one right-side status group whenever space allows, with the pair wrapping together instead of splitting apart.
- Removes seconds from Smart Search scan timestamps; scan time is shown to the minute only.
- Uses richer workflow accents for Staging, Outbound, Received, CPU, Greenville, and DTC while keeping the full-card stage gradient soft and readable.
- Preserves the v0.438 **795px** search width, compact 36px height, tighter Order/Job/Customer spacing, distinct never-scanned icon, 20-result cap, cached focus recall, and one-click navigation.
- Advances browser cache references and `APPLICATION_VERSION` to v0.439.
- SQLite schema remains version 11; no migration or database reset is required.

## v0.437 highlights

- Reduces the desktop Global Search maximum width from 980px to 690px (about 30%) and aligns the Smart Search dropdown to the same footprint.
- Reduces the desktop search surface from 56px to 36px and the input from 54px to 34px (about 35%) so the header feels substantially lighter.
- Reduces desktop search text modestly to 17px so it remains comfortable within the shorter control.
- Keeps the v0.436 Job Nr. proximity/column allocation, v0.435 stage gradients/icons, semantic cells, 20-result cap, cached focus recall, and navigation behavior unchanged.
- Keeps mobile at a practical 42px control height rather than forcing the 36px desktop height onto touch layouts.
- Advances browser cache references and `APPLICATION_VERSION` to v0.437.
- SQLite schema remains version 11; no migration or database reset is required.

## v0.436 highlights

- Restores the Global Search control to the pre-v0.435 56px surface / 54px input height instead of making the header taller.
- Expands the desktop header center track up to 980px so Global Search and its Smart Search dropdown gain real horizontal room rather than being capped by the older 640px header column.
- Keeps responsive widths intact at 1260px and below so smaller screens retain the existing compact header behavior.
- Tightens the Order/Item-to-Job gap and reduces the Order/Item column share, giving Job Nr. substantially more horizontal room while preserving a useful Customer column.
- Preserves v0.435 stage-at-a-glance card gradients/icons, semantic cells, 20-result cap, cached focus recall, and one-click navigation.
- Advances browser cache references and `APPLICATION_VERSION` to v0.436.
- SQLite schema remains version 11; no migration or database reset is required.

## v0.435 highlights

- Enlarges the Global Search control to 960px maximum width with a taller 60px search surface and larger 19.5px input text.
- Increases Smart Search card, identity, metadata, glass, and status-chip sizing from the very compact v0.434 treatment while using the additional dropdown width to keep information fitting cleanly.
- Gives every genuinely scanned result a soft full-card gradient keyed to its current workflow stage; never-scanned results remain neutral white.
- Replaces the neutral cube tile on scanned results with the designated stage icon for Staging, Outbound, Indian Trail Received, CPU, Greenville, or DTC.
- Keeps stage washes intentionally light so Route, Flags, Glass Type, and Stage cells remain independently readable and semantic.
- Preserves the 20-result cap, cached focus recall, changed delivery dates, scan timestamps, route/glass/flag colors, and one-click navigation.
- Advances browser cache references and `APPLICATION_VERSION` to v0.435.
- SQLite schema remains version 11; no migration or database reset is required.

## v0.434 highlights

- Preserves the v0.433 Smart Search reference-card hierarchy while substantially reducing each result's height and horizontal footprint.
- Shrinks the leading cube tile, card padding/gaps, top-row column spacing, typography, Type chip, DD/Flags/Route/Stage chips, and icon sizes so Job and Customer have more usable width.
- Keeps Order/Item visually strongest while preventing the oversized reference layout from forcing normal status chips onto extra lines.
- Retains the same neutral hover, Lookup Manager glass colors, route/flag/stage semantic colors, changed delivery dates, scan timestamps, 20-result cap, cached focus recall, and one-click navigation.
- Advances browser cache references and `APPLICATION_VERSION` to v0.434.
- SQLite schema remains version 11; no migration or database reset is required.

## v0.433 highlights

- Rebuilds each Smart Search match as a polished reference-style record card with a blue cube icon tile, large Order/Item identity, Job and Customer columns, a thin identity divider, a clean Size/Qty/Type row, and a final semantic chip row.
- Matches the supplied visual hierarchy with larger typography, a white card surface, soft blue-gray dropdown canvas, rounded borders, light neutral shadow, and visible separation between adjacent results.
- Converts DD, Flags, Route, Stage, and Scanned metadata into compact icon chips while keeping Glass Type driven by the Lookup Manager color and Route/Stage driven by their maintained semantic palettes.
- Keeps Flags present for every result, including **None**, and preserves changed-delivery-date text, Rush/Remake states, scanned time, 20-result search, cached reopen-on-focus, and one-click navigation.
- Enlarges and slightly widens the Global Search field to visually align with the supplied reference.
- Keeps hover/focus neutral with no semantic recoloring.
- Advances browser cache references and `APPLICATION_VERSION` to v0.433.
- SQLite schema remains version 11; no migration or database reset is required.

## v0.432 highlights

- Increases Smart Search result text size while preserving the compact four-row layout.
- Makes Route a true bordered/tinted cell with a distinct, lighter route palette, including explicit Indian Trail, CPU, DTC, Greenville, and Airport colors.
- Makes Flags an always-present cell: **None** when no priority applies, **RUSH**, **REMAKE**, or **REMAKE · RUSH** with restrained flag-specific color.
- Restricts the unscanned gray treatment to the Stage cell only; the rest of the result stays neutral white.
- Keeps hover colorless and reduces it to a nearly invisible neutral depth cue.
- Removes the remaining JavaScript animation replay for Home Find Delivery List date groups so each dropdown performs only the single CSS-owned expansion.
- Adds the designated stage icon inside each Forward View STG/OUT/IN/CPU/GNV/DTC counter and slightly enlarges the scanned/total count.
- Enlarges the Home greeting and full date to better use the open hero space.
- Advances browser cache references and `APPLICATION_VERSION` to v0.432.
- SQLite schema remains version 11; no migration or database reset is required.

## v0.431 highlights

- Fixes Smart Search focus recall so clicking back into Global Search keeps the cached results open instead of reopening them for one frame and immediately hiding them.
- Keeps the overall Smart Search result neutral; stage color is confined to the Stage cell, and never-scanned status is rendered in neutral gray.
- Keeps Route, Glass Type, RUSH, and REMAKE as independent semantic cells with their own maintained colors.
- Removes colored Smart Search hover feedback; hover/focus now uses only a subtle neutral border and shadow.
- Removes the Home Delivery Library forced reflow/animation replay that caused date headers to flash before expanding.
- Adds compact Forward View stage counters in workflow order: STG, OUT, IN, CPU, GNV, and DTC, each showing scanned/total pieces for that delivery date.
- Preserves the 20-result Smart Search cap, changed-delivery-date display, one-click navigation, and existing Airport Road staging progress source.
- Advances browser cache references and `APPLICATION_VERSION` to v0.431.
- SQLite schema remains version 11; no migration or database reset is required.

## v0.430 highlights

- Adds a light stage-colored gradient to Smart Search matches that have actually been scanned, while unscanned matches remain neutral.
- Converts each metadata field into a compact cell so Order/Item, Job Nr., Customer, Size, Qty, Type, DD, flags, Route, Stage, and Scanned time are easier to parse at a glance.
- Gives the Route cell a stable route color, Rush/Remake their own priority colors, and Glass Type a Lookup Manager-driven glass-color gradient.
- Uses a small gap and border around each result so adjacent orders are visually distinct without bringing back large-card spacing.
- Reopens the current Smart Search results immediately when the Global Search input regains focus, reusing the last results when the query is unchanged.
- Preserves the four-line hierarchy, changed-delivery-date text, one-click navigation, and 20-result cap.
- Keeps SQLite schema version 11 unchanged; no migration or database reset is required.
- Advances browser cache references and `APPLICATION_VERSION` to v0.430.

## v0.429 highlights

- Refines Smart/Global Search into compact record strips with larger, easier-to-read text while keeping the same four-line operational hierarchy.
- Sections the identity, glass, delivery, and current-stage lines with subtle hairline dividers and consistent aligned spacing instead of adding bulky cards.
- Fixes Delivery Date / priority flag / Route crowding with deliberate inline gaps and preserves real whitespace between multiple priority flags.
- Replaces the Glass Type underline with a small Lookup Manager-colored dot plus strong text for a cleaner visual cue.
- Gives RUSH and REMAKE compact alert tags and current-stage text a small status dot, reserving stronger color only for information that needs attention.
- Keeps Order/Item as the strongest anchor, Customer truncation, changed-delivery-date rendering, scan timestamp, one-click navigation, and the 20-result cap unchanged.
- Keeps SQLite schema version 11 unchanged; no migration or database reset is required.
- Advances browser cache references and `APPLICATION_VERSION` to v0.429.

## v0.428 highlights

- Keeps each Smart/Global Search match condensed to the existing four text rows while standardizing label weight, value typography, spacing, and field separators across the entire result.
- Adds consistent inline **Customer:** and **Scanned:** labels and applies the same muted label treatment to Job Nr., Size, Qty, Type, DD, Route, and Stage.
- Adds restrained visual polish with a subtle left-edge accent, cleaner row separators, a soft neutral result background, and a stronger hover/focus accent without adding card height, pills, or large boxes.
- Keeps the order/item identifier as the strongest text anchor, preserves Lookup Manager glass-color underlining, and retains restrained Rush/Remake and stage status colors.
- Preserves the 20-result cap, changed delivery dates, route, priority flags, scan time, navigation behavior, and the existing backend search payload.
- Keeps SQLite schema version 11 unchanged; no migration or database reset is required.
- Advances browser cache references and `APPLICATION_VERSION` to v0.428.

## v0.426 highlights

- Compresses each Global Search match into four tight text rows with minimal vertical padding and no card-like boxes, gradients, or pill containers.
- Keeps the requested information order: Order/Item + Job Nr. + Customer; Size + Qty + Glass Type; DD + changed date + REMAKE/RUSH + Route; current Stage + scanned date/time.
- Keeps Glass Type color meaning as a subtle colored underline instead of a large tinted field.
- Converts REMAKE, RUSH, Route, and Stage presentation to simple inline text while retaining their useful status colors.
- Removes result-to-result grid gaps and hover lift so the search dropdown reads like a compact operational lookup list.
- Preserves v0.425 priority-date, Rush/Remake aggregation, navigation, and Lookup Manager glass-color data behavior.
- Keeps SQLite schema version 11 unchanged; no migration or database reset is required.
- Advances browser cache references and `APPLICATION_VERSION` to v0.426.

## v0.423 integration baseline

The v0.423 release remains the merged Main + Website Version 3 integration baseline underneath the maintained v0.434 release.

## Website Version 3 integrated highlights

These entries preserve Website Version 3's release order and are renumbered from its branch-local v0.325-v0.362 sequence to v0.386-v0.422.

## v0.422 highlights

- Fixes Combine selection text so English mode stays English after clicking rows; Spanish mode continues to translate the same live states.
- Adds **Uncombine Glass Types** beside Combine Glass Types in the Glass Type Library header.
- Lets administrators select one or more manually combined profiles and restore their underlying source names with one **Uncombine selected** action.
- Makes only genuinely combined profiles selectable during Uncombine mode, reducing accidental operations.
- Uses the existing schema-neutral `glass_alias` records and leaves historical imported line-item text untouched.
- Keeps Uncombine reversible: separated glass types can be combined again later.
- Includes desktop/mobile styling and Spanish coverage for the new workflow.
- Advances the maintained application release to **v0.422** while keeping SQLite schema version **11** unchanged.


## v0.421 highlights

- Moves **Combine Glass Types** to the Glass Type Library header.
- Turns the library into an explicit multi-select surface while combine mode is active.
- Uses the **first selected profile as Keep / canonical**, with every later selected profile marked Merge.
- Combines the selected profiles through the existing reversible `glass_alias` backend without rewriting historical imported glass names or changing schema version 11.
- Updates row selection in place so selecting multiple entries does not rebuild the Lookup Manager or jump the scroll position.
- Keeps same-family combine safety for Annealed, Mirror, and Tempered profiles.
- Removes the Superseded Orders filter repaint flash by updating the filter buttons and review list in place.
- Gives Superseded review filters stable hover/active/focus states instead of flashing white on click.
- Includes mobile layout support and Spanish translations for the new combine workflow.
- Advances the maintained application release to **v0.421** while keeping SQLite schema version **11** unchanged.


## v0.420 highlights

- Adds a **Combine** action to every Glass Type profile. The selected row is the canonical profile to keep; administrators can select other same-family profiles that represent the exact same physical glass.
- Stores combinations as reversible `glass_alias` records in the existing `admin_lookup_values` table, keeping SQLite schema version **11** unchanged and preserving historical imported product text.
- Resolves combined aliases through the shared glass-label path so filters, glass-aware presentation, and other browser surfaces use the canonical profile rather than showing duplicate names.
- Delivers the active alias map through the existing Presentation context, allowing ordinary operator screens to use the canonical glass name without granting Lookup Manager access.
- Applies the same alias map to shared glass-color handling and Statistics material-cost/breakage reporting so combined names group under the selected canonical glass identity.
- Supports **separating aliases again** by reopening Combine for the canonical profile and unchecking a previously combined alias.
- Limits Combine candidates to the same Annealed / Mirror / Tempered family to reduce accidental cross-family merges.
- Keeps the v0.419 Spanish-language guarantee intact by translating the new Combine workflow, instructions, accessibility text, and save feedback.
- Advances the maintained application release to **v0.420** while keeping SQLite schema version **11**. No migration or database reset is required.


## v0.419 highlights

- Expands the maintained Spanish dictionary across the current shell, Home, Statistics, Scan, Racks, Reject Tracking, Bay Map, Admin, Lookup Manager, Customer Email Center, automation, notifications, print/export, dialogs, empty states, validation messages, and other current browser surfaces.
- Extends live translation ownership beyond normal text nodes to `placeholder`, `title`, `aria-label`, image `alt`, and mobile `data-label` attributes, including attributes changed after Spanish mode is already active.
- Localizes user-facing dates, times, month/day names, and chart/report number formatting through the selected `en-US` / `es-US` application locale. Recognizable English dates already on screen are converted during a live language switch.
- Translates backend/API validation and safety messages that can surface directly in browser notifications while preserving technical identifiers, user-entered data, configured company/site names, route codes, and stable workflow keys.
- Localizes the browser-native automation disable confirmation and translates the separate Statistics report and Delivery List print-package documents before their print dialogs open.
- Preserves the v0.418 Presentation-logo sidebar behavior and all v0.416 portability architecture. Spanish translation changes presentation only; no workflow, API, permission, database, or automation behavior changes are included.
- Advances the maintained application release to **v0.419** while keeping SQLite schema version **11**.


## v0.418 highlights

- Makes the selected **Presentation logo the exclusive sidebar brand surface**. When `Use installed logo asset` is enabled, the generated initials, company name, and application title are forcibly hidden from the sidebar on desktop and mobile.
- Preserves the existing portable fallback: disabling the installed logo still shows the configured company/application text and generated company initials.
- Adds no workflow, API, database, permission, or presentation-profile schema changes. SQLite schema remains **11**.
- Advances the maintained application release to **v0.418** and refreshes maintained browser cache/version references.


## v0.417 highlights

- Fully **reverts the v0.356 Lookup Manager visual overhaul**. Lookup Manager desktop/mobile styling, layout, spacing, card treatment, navigation treatment, search presentation, and cosmetic-only JavaScript/CSS changes return to the v0.416 implementation.
- Preserves the complete **v0.416 portability architecture**, including Presentation settings, station display aliases, stage display names, route display labels, configurable branding/support email, receiving-site wording, and stable backend identifiers.
- Makes no workflow, API, database, permission, lookup normalization, or save/remove behavior changes beyond the rollback.
- Advances the maintained application release to **v0.417** while keeping SQLite schema version **11**. No migration or database reset is required.


## v0.416 highlights

- Adds a **Presentation** workspace to Lookup Manager for company/organization name, application name, sign-in product name, support/report email, and installed-logo behavior. These are presentation settings only; workflow identity is not rewritten.
- Adds safe **Station Display Names**. The database/internal station value remains stable for scan attribution, access rules, historical records, and default seeding, while operators can see a location-specific alias such as `Dock 4` or `Receiving Building A`.
- Makes **Stage configuration explicitly two-layered**: the Display Name is operator-facing, while the existing stage key, behavior preset, internal station binding, and route code remain stable engine contracts. The Stage editor now uses the maintained internal station list instead of encouraging free-form station renames.
- Reuses existing **Route lookup labels** as the operator-facing destination names throughout portable route/filter presentation while preserving route codes such as CPU, DTC, and GNV underneath.
- Loads a lightweight, non-sensitive **presentation context before authentication** so the sign-in screen and normal operator pages can use configured company, station, stage, and route wording without loading Admin-only data.
- Extends portable wording into the primary **Receiving/Bay and Auto Assignment** surfaces so a renamed receiving site does not continue showing `Indian Trail` cosmetically while the backend continues using its existing internal workflow key.
- Makes shell branding portable without adding new image files. The current installed Barefoot/BFS logo remains the default; administrators can disable it for another company and the shell automatically falls back to a polished initials/text brand.
- Makes the **Report Bugs** destination configurable and normalizes authentication/user-management copy from company-specific `BFS email` wording to generic `email` wording. Validation and authentication behavior are unchanged.
- Applies cosmetic **receiving-role labels** to the built-in `Indian Trail Operator / Lead / Manager` roles. The stored role names remain unchanged for permission logic, while user/role management can follow the configured receiving-site display name.
- Preserves `APPLICATION_VERSION = 416` with `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is required.


## v0.415 highlights

- Keeps the **Customer Route Rules overview** at the same six-column desktop width as Lookup Manager while allowing the card to grow naturally with its selected route. Internal scrolling begins only after ten standard route rows are present.
- Normalizes every Customer Route overview line item to the same compact **56px row height** used by the correctly sized CPU tab, so DTC, GRN, and custom-route tabs with only a few customers no longer stretch those rows to fill the card.
- Restores normal **Admin-page wheel/trackpad scrolling** when the pointer is over the Customer Route overview. If a route has more than ten entries, its internal list can scroll and then naturally chain back to the page at the list boundary.
- Removes the obsolete Admin KPI strip for **Active Delivery Lists, Scans Today, Line Items, and Active Users**. The existing Admin summary API request remains because its data still feeds import history and superseded-review state.
- Advances `APPLICATION_VERSION` to 415 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.


## v0.414 highlights

- Restores **Customer Route Rules** to the exact compact Admin geometry requested: the same six-column width as Lookup Manager and the same shared row height as Customer Emails. The readable route list scrolls inside the card instead of stretching the dashboard.
- Consolidates the **Glass Type library** by canonical physical-glass identity. Default and discovered aliases now merge into one row even when casing, punctuation, quote marks, heat-treatment abbreviations, or spacing differ (for example `Ultra Clear` versus `UltraClear`). Distinct tempered products and distinct mirror patterns remain separate.
- Uses a neutral **combined** source label when one glass profile is assembled from both default and discovered data, making the source relationship explicit without displaying duplicate glass cards.
- Adds the supplied **static/css/mobile.css** back to the maintained source package and applies the shared readable GUI typography floor to handheld Admin/Operations dialogs while leaving scaled print-document previews alone.
- Clarifies **Stations versus Stages** in Lookup Manager. Stations are physical scan/work areas; Stages are dated workflow steps; behavior presets define what a stage does; route/station fields connect that behavior to operational scope. The existing preset keys and backend contracts remain unchanged for production compatibility.
- No SQLite schema migration or database reset is required; schema version remains **11**.


## v0.413 highlights

- Restores the **Customer Route Rules overview** to the normal four-column Admin dashboard card width while keeping the larger v0.412 text and route-color cues. The card returns to full width only at the existing responsive breakpoint.
- Reframes **Bay Auto Assignment** around its actual live purpose: qualifying Indian Trail orders are classified during Outbound scanning and may reserve the first empty matching bay before receiving. The GUI now explains that flow directly instead of presenting the feature as a generic bay remapper.
- Removes routine **destination remapping** and the irrelevant CPU policy control from the Auto Assignment GUI. Existing stored mapping values are preserved for upgraded installations, while admins only tune the two size thresholds and choose which applicable categories require manual placement.
- Keeps the existing bay safety behavior intact: an existing assignment is reused, one physical bay cannot mix Order Nrs., manual categories stop before automatic reservation, specialized classifications never silently fall back to Standard when their bay family is full, and existing placements are never moved by a settings change.
- Normalizes the **Customer Email Center** to the same readable modal typography scale as the rest of Admin, including forms, search, rules, CC recipients, test-email copy, activity rows, filters, statuses, and retained email detail dialogs.
- Adds a shared **full-GUI typography floor** of 13px for controls/body data and 12px for supporting copy across modal panels, dialogs, print GUIs, automation, notifications, and Admin workspaces so maintained interfaces do not drift back to 8-10px operational text.
- Advances `APPLICATION_VERSION` to 413 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.412 highlights

- Enlarges the **Customer Route Rules overview** to a full-width dashboard card, raises operational overview copy to at least 12px, and adds restrained route-color cues to the overview tabs, customer rows, route pills, and full Customer Routes manager.
- Corrects **Lookup Manager** visual behavior by re-centering the live-preview icon, preserving the Edit Settings pencil on hover, and replacing the Glass Types / Routes / Process States search controls with a clearer labeled search surface and one-click Clear action.
- Restores **distinct Mirror glass profiles** instead of collapsing every mirror alias into one `Mirror` profile. The maintained 1/4 Mirror plus French Antique, Summer Cloud Antique, Dark Cloud Antique, Rainbow Antique, Hollywood Antique, and Woodford Antique defaults are independently available, and additional discovered mirror products remain distinct.
- Rebuilds **Mixed Destination** inside Scan Page Settings as one focused approval-window workspace with a simple scope explanation and the same existing settings contract.
- Repairs **Reject Reasons / Break Locations** so edit/delete icon actions stay side by side and long location text wraps inside its row instead of overlapping neighboring content.
- Rebuilds **Bay Rules & Auto Assignment > Auto Assignment** into a three-step workspace for size thresholds, destination mappings, and manual-placement exceptions while preserving the current backend payload and field identities.
- Repairs **Action History modal scrolling** by explicitly routing wheel/trackpad input to each history panel's owned vertical scroller, including when the pointer is over filters, cards, controls, or row content.
- Advances `APPLICATION_VERSION` to 412 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.411 highlights

- Adds **CPU / DTC / GRN route tabs** to both the Customer Route Rules Admin overview and full manager. The overview shows up to 10 customers for the selected route, then exposes a Show More action that opens the full manager on that same route.
- Normalizes Lookup Manager glass configuration into **Annealed / Mirror / Tempered** families. Generic non-mirror glass aliases collapse into an Annealed profile, explicit Tempered aliases remain separate, and mirror aliases share one Mirror profile while original imported line-item text remains untouched.
- Propagates canonical glass-profile colors across discovered aliases and makes profile removal hide the canonical profile plus its discovered source aliases without rewriting historical delivery-list data.
- Lets administrators edit both **Reject Reasons and Break Locations** using compact side-by-side pencil and trash actions. Historical reject events retain the text recorded when the reject occurred.
- Replaces the separate Cross-Date and mixed-destination configuration paths with **Scan Page Settings**, using permission-aware top tabs for Cross-Date Scanning and Mixed Destination while preserving the existing settings APIs.
- Replaces the separate Scanner Rules and Bay Auto Assigner launchers with **Bay Rules & Auto Assignment**, using shared top tabs for Scanner Rules and Auto Assignment while preserving the existing rule/assignment APIs and Action History routing.
- Advances `APPLICATION_VERSION` to 411 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.410 highlights

- Simplifies **Customer Routes** by keeping color at the route-group level while making editable rule rows neutral; the Admin overview now exposes every route group as an initially collapsed section.
- Adds safe **Delete Draft** support to Customer Email Activity and increases activity typography again.
- Combines **Glass Types + Glass Costs + Glass Colors** into one Lookup Manager Glass Types workspace so one selected glass profile owns its label, cost/SQFT, and exact preview color.
- Uses normalized Lookup Manager color matching in Delivery List Update Preview and changes order navigation to gray outside-the-card dots connected by a vertical guide.
- Rebuilds **User Directory** search/filter controls and adds editable Reject Reason labels without rewriting historical reject records.
- Combines Bay scanner administration into **Bay Scanner Management** with Bay Scanner and Scanner Rules top-level workspaces, preserving the existing scanner-rule APIs.
- Advances `APPLICATION_VERSION` to 410 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.409 highlights

- Standardizes **CPU as the orange route** in route-facing Admin/preview treatments, while preserving existing route codes and backend routing behavior.
- Groups **Customer Route Rules by route** in both the full Customer Routes manager and the Admin dashboard overview. Each group and overview statistic receives a restrained route-color treatment so route ownership is visible without overpowering the form controls.
- Re-centers the Customer Routes section icon by moving the signpost glyph 3px right and 4px down inside its existing tile, and contains the enhanced Route dropdown hover/focus effect so it no longer spills over the colored rule-card background.
- Increases **Email Activity** typography, row spacing, status/action text, and Email Activity detail-dialog text so retained customer communications are readable at normal kiosk/desktop distance.
- Increases **In-Transit / Delivery Manifest** header, summary, rack, glass-ribbon, and table text sizing while preserving the existing manifest layout and columns.
- Slightly increases **Delivery List Update Preview order-card** height and order typography without returning to the earlier oversized layout or changing the compact line-item density.
- Advances `APPLICATION_VERSION` to 409 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.408 highlights

- Replaces Customer Route rule left-edge color strips with a subtle full-card gradient derived from the route color and uses a clearer Route Rules signpost icon.
- Rebuilds the Lookup Manager live-preview treatment and groups Products, Glass Costs, and Glass Colors into Annealed, Mirror, and Tempered families while preserving search.
- Clarifies that **Updated Line** is an A+W import-change marker, while manual Admin changes are durable `manual_edit` audit events surfaced in Manual Edit and Action History.
- Simplifies Cross-Date Scanning to Switch Behavior, Past/Future date windows, and Save while preserving the same backend settings contract.
- Rebuilds Reject Tracking Setup into separate polished Reject Reasons and Break Locations libraries with independent scrolling and purpose-specific controls.
- Advances `APPLICATION_VERSION` to 408 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.407 highlights

- Extends **Create New Role** so the permission library fills the complete workspace between the role identity fields and bottom actions; the permission list remains the single scroll owner.
- Repairs and polishes **Customer Routes** with a materially larger Create New Customer Route launcher, a dedicated Route Rules heading/status strip, isolated non-overlapping rule cards, and purpose-built Save/Delete icons.
- Rebuilds **Lookup Manager iconography and actions** around restrained outline SVGs and lower-saturation icon tiles instead of the older mixed number/icon backgrounds.
- Adds **Stations** directly to Lookup Manager, using the maintained station create/rename/remove APIs while protecting required built-in recovery stations.
- Adds remove controls for **Products, Routes, Process States, Glass Costs, and Glass Colors**. Removed discovered/default values are stored as administrator tombstones so old delivery-list history cannot immediately repopulate them.
- Adds a first-class **Stage Editor**. Administrators can add/remove stage definitions, change stage display names, and assign maintained behavior presets for Airport Staging, Airport Outbound, Indian Trail, Greenville, CPU, DTC, or a custom route. Stable stage keys remain the operational identity while display names can change safely.
- Applies stage presets to current list generation, scan-category detection, route/manual-order targeting, import history source selection, print/export sheet classification, rack staging behavior, route reconciliation, and global-search progress so renamed stages retain their operational logic. Saving a display-name/preset change updates existing list metadata with the same stable stage key; removing a stage stops future generation while retaining historical data for audit safety.
- Completely revamps **Cross-Date Scanning** as a compact command center with clearer mode/window controls, visible safeguards, stronger hierarchy, and the same existing backend settings contract.
- Advances `APPLICATION_VERSION` to 407 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.406 highlights

- Makes **Delivery List Update Preview** denser and easier to scan: glass colors keep their Lookup Manager identity but use a less saturated preview treatment, route headers use the complete route color rather than generic blue, each order gets a route-colored dot, and item/order spacing is reduced so more work fits on screen.
- Expands the **Create New Role** permission workspace to nearly the full available viewport while keeping identity fields and Create/Cancel actions fixed. The permission library remains the single dedicated scroller.
- Moves **Customer Rules, Test Email, and Email Activity** into the existing shared Admin tab rail beside Action History. The duplicate internal email tab strip is removed, the Add/Edit Customer Rule Cancel action is removed, and the rule/Global CC icons receive stronger contrast.
- Polishes **Customer Routes** with a larger Create New Customer Route button and cleaner route-rule cards with route-aware accents, stronger input focus states, and more consistent row actions.
- Completely refocuses **Lookup Manager** around the existing Admin tab rail: Products, Routes, Process States, Glass Costs, Glass Colors, and Action History now share one top-level tab system. The old Lookup Manager hero/KPI block is removed, while the selected library gets a cleaner two-column editor/library workspace with independent scrolling.
- Advances `APPLICATION_VERSION` to 406 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.405 highlights

- Makes the currently opened **Delivery List Update Preview route** visually unmistakable with a stronger active route header and `Viewing` marker, while increasing spacing/border hierarchy between individual orders so adjacent orders cannot visually blend together.
- Fixes the remaining **Create New Role permission clipping** at the category-card level: permission categories now size to their complete option grids while the outer permission library remains the single scroll owner.
- Redesigns the shared **Cancel / Cancel Scan** icon as a lighter crisp X rather than the dense filled circle-X glyph.
- Changes recognized **superseded/duplicate-order candidate processing** so the review candidate is persisted before scanner reconciliation begins. If a candidate exists and the review queue cannot be written, reconciliation fails closed; pending candidates remain in source data until an explicit review decision. Existing exact same Order Nr. + Item Nr. corruption guards remain defensive integrity checks rather than silently choosing which order to remove.
- Simplifies **Customer Emails** to Customer Rules, Test Email, and Email Activity. Removes the large hero/stats/Draft-mode block and the separate Delivery Setup tab, moves Global CC management beside the customer-rule editor, and keeps only a compact transport-readiness message where it is relevant to testing.
- Rebuilds **Email Activity Open** as a dedicated high-layer child dialog with readable recipients/status/message content and PDF/Copy/Open-in-Email-App actions, eliminating the prior blurred/broken nested-modal presentation.
- Removes the verbose **Customer Route Rules** introduction and replaces it with a compact route manager plus a polished **Create New Customer Route** button that opens its own child GUI. Existing route rows remain editable in place.
- Advances `APPLICATION_VERSION` to 405 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.404 highlights

- Makes each **Delivery List Update Preview item row** use the Lookup Manager glass-type color across the whole line instead of allowing the generic New/Updated semantic color to make unrelated glass types look green.
- Repairs **Create New Role permission reachability** by giving the role dialog a definite viewport and a dedicated permission-list scrollbar while keeping role identity and actions visible.
- Adds a shared circle-X icon treatment to Cancel actions across maintained dialogs, confirmations, rack tools, overrides, calendars, reject workflows, and Admin creation forms.
- Rebuilds **Customer Emails** as a tabbed Customer Email Center with Customer Rules, Delivery Setup, Test Email, and Email Activity workspaces; adds search/filtering, clearer transport readiness, recipient/CC management, status counts, and more readable activity actions.
- Hardens duplicate protection around the logical **Order Nr. + Item Nr.** identity. Import payloads containing duplicate logical items now fail before publication; stage insertion has a second defensive duplicate barrier; protected manual rows suppress colliding A+W source copies; manual creation normalizes numeric identity; and manual edits cannot be changed into an existing logical item for the same delivery date.
- Keeps intentional workflow siblings across Staging, Outbound, and route stages. The duplicate guard prevents multiple active copies of the same Order Nr. + Item Nr. **inside a stage/list**, not the required synchronized copies across separate workflow stages.
- Advances `APPLICATION_VERSION` to 404 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.403 highlights

- Pins the detached SQL updater to the **same scanner database as the running web app**, in addition to the existing `ProjectRoot` repair. This addresses the failure mode where Import History could show a newly created date while `/api/delivery-lists`, Scan, and Print / Export could not see it.
- Writes a non-secret `ScannerStore` identity (mode/database/server where applicable) into the maintained automation runtime configuration. SQLite runs also receive the live absolute database path through `DLS_DATABASE_PATH` before Python starts.
- Makes the Python importer validate its resolved scanner-store identity **before initialization or writes**. If the detached process resolves a different store, the run stops instead of recording a false successful import.
- Adds explicit updater log lines for scanner-store binding/validation so database-path drift can be diagnosed directly from Status & Logs without exposing credentials.
- To repair a date that was previously written to the wrong store, install v0.403 and run **Query SQL, Export & Import** for that delivery date once. The maintained selective reconciliation will detect the lists missing from the live store and rebuild them.
- Advances `APPLICATION_VERSION` to 403 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.402 highlights

- Fixes the **role-save logout regression**. Saving role permissions no longer deletes active browser sessions; authorization changes are read from `role_permissions` on every authenticated request and therefore apply immediately without forcing users back to Sign In.
- Keeps **403 permission denials** inside the signed-in application as a normal access-denied popup. A Sign In redirect is reserved for a real **401 expired/missing session**.
- Protects the built-in **Admin** role as the application recovery role. Admin is synchronized to all canonical permissions at startup and cannot be reduced to a partial permission set from Role Manager.
- Removes the duplicate smaller gray `username · email` line from the Admin dashboard user preview while retaining role, permission summary, station, profile, and session state.
- Raises the dedicated **Create New Role** and **Create New User** dialogs above the already-open Admin modal so the focused child GUI can never render behind its parent.
- Restores **Delivery List Management Print / Export** availability for newly updated dates by retaining the authoritative Airport Outbound list ID from import results and hydrating exact print list detail directly when the general catalog has not refreshed yet.
- Advances `APPLICATION_VERSION` to 402 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.401 highlights

- Revamps **All Delivery Lists** with a conventional search control, dedicated clear action, restrained focus/loading feedback, and no sweeping search sheen.
- Marks required **Create New Order** fields with red asterisks while preserving the dedicated order-creation dialog and Airport Staging + Outbound + selected-route workflow contract.
- Moves **Create New Role** into a dedicated polished dialog with role identity fields, categorized permission selection, Select all/Clear all tools, and a primary blue launcher/action.
- Moves **Create New User** into its own polished dialog with account details, temporary password, starting role/station, explicit User → Role → Permission guidance, and a primary blue launcher/action. New-user creation requires both profile-management and user-assignment authority because the operation assigns initial access.
- Expands the Admin dashboard user preview to **10 users** and removes the old incremental “view one more” behavior.
- Completes a permission-model review across browser gates and API routes. The original broad `edit_delivery_lists` authority is split into item editing, manual order creation, item deletion, list/date deletion, superseded-order approval, and cross-date scanning. User profile management, user access/password controls, role/station assignment, and role-definition authority are explicitly separated. Customer email, bay scanner rule, and bay auto-assigner administration also receive dedicated permissions.
- Retires the unused standalone Indian Trail bay-report permission in favor of the maintained general `view_reports` capability, while legacy permission aliases are upgraded in place for existing databases.
- Restricts the shared **Action History** API by GUI context so possessing one Admin-like capability no longer permits querying unrelated GUI audit history by manually changing the request context.
- Keeps existing custom-role behavior through a one-time capability-preserving permission backfill while leaving later Role Manager edits authoritative.
- Advances `APPLICATION_VERSION` to 401 while preserving `CURRENT_SCHEMA_VERSION = 11`.

## v0.400 highlights

- Replaces the Edit Delivery Lists launch-time `loadDeliveryLists()` refresh with a dedicated `/api/admin/delivery-list-catalog` endpoint that selects the requested three-week page first, then aggregates only those visible stage totals. It avoids the richer Home/scanner catalog's glass/update/timing work and per-list timing queries just to open the Admin browser.
- Keeps Edit Delivery Lists search server-backed and paged, including order/item/customer/job/product matches, so older results remain searchable without downloading every active delivery list into the browser.
- Opens Manual Delivery List Edit faster by starting the first 20-row server page and rack/bay/lookup reads in parallel instead of serially, and briefly caches the slower-changing product/route/process lookup library while still refreshing physical rack/bay destinations.
- Restyles Automation Control Center Import History filters with the same labeled search/filter card used by Action History tabs while retaining the existing Import History paging and filter behavior.
- Gives the Create New Order **Cancel** action a finished secondary-button treatment with icon, focus, hover, and pressed feedback.
- Advances `APPLICATION_VERSION` to 400 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.399 highlights

- Moves **Edit Delivery Lists** and Automation Control Center **Import History** paging into the same centered header/footer pattern used by Action History: result context on the left, numbered Previous/page/Next navigation in the middle, and range/status context on the right. The duplicate bottom pagers are removed.
- Gives both affected browsers one explicit content scroll viewport. Search/filter/pager controls stay in opaque rows above the content, and wheel/trackpad input over cards/disclosures is routed to the intended viewport instead of becoming trapped by nested overflow containers.
- Replaces the inline expandable **Create New Order** section with a separate modal dialog that preserves the existing Airport Staging + Airport Outbound + selected-route creation contract.
- Polishes the Create New Order launcher and dialog with a dedicated header, workflow destination summary, grouped fields/options, fixed action footer, Cancel/Close controls, and responsive behavior.
- Advances `APPLICATION_VERSION` to 399 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.398 highlights

- Organizes Automation Control Center **Import History** into the same Monday-Friday operating-week bands used by Home and Edit Delivery Lists, including **Next Week**, **This Week**, **Previous Week**, and older week ranges while retaining collapsed date/category/run/result details.
- Standardizes compact numbered **Previous / page / Next** controls across Import History, Edit Delivery Lists, Manual Edit result pages, every shared Admin Action History tab, and Delivery List Management's daily timed-import browser without changing each section's existing server-side page-size rules.
- Polishes **Create New Order** with an explicit workflow-destination summary, grouped order fields, clearer options, stronger focus/hover feedback, and a primary Create Order action.
- Makes the selected route authoritative for manual order creation and requires every new manual order/item to be created in **Airport Staging + Airport Outbound + the selected route stage** for that delivery date. Missing required workflow stages now stop the operation instead of creating an incomplete set of copies.
- Expands the manual-order audit payload with the actual target list IDs/stages and Airport roles so the fan-out can be reconstructed from Action History.
- Advances `APPLICATION_VERSION` to 398 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.397 highlights

- Changes Automation Control Center **Import History** to use two paging rules: normal browsing shows **Next Week + This Week + Previous Week** together, then moves backward in three-week pages; any active search/status/date filter shows every matching import across up to **25 activity dates per page** before creating another page.
- Adds visible **Page X of Y** context at the top of both Import History and Edit Delivery Lists, while keeping Previous / Next controls at the bottom.
- Simplifies the Edit Delivery Lists top summary to the actual visible delivery-date range instead of concatenating relative week labels.
- Removes the redundant **Live delivery data** health label from Edit Delivery Lists and **Unsaved changes protected** from Manual Delivery List Edit.
- Reapplies Lookup Manager **Glass colors** to Glass Type cells in Delivery List Update Preview using the shared configured color library and automatic fallback palette.
- Advances `APPLICATION_VERSION` to 397 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.396 highlights

- Changes Automation Control Center Import History From/Through filtering to use the same local **import activity date** that drives the business-week history pages. This removes the prior mismatch where the controls filtered workbook delivery dates while the tab itself was organized by updater-run dates.
- Renames the date controls to **Import activity from / through** so their behavior is explicit and keeps the existing normalized range and stale-request protection.
- Changes Edit Delivery Lists to open on **Next Week + This Week + Previous Week**, then move backward through older delivery dates in **three-week pages**. Pagination controls are now simply **Previous / Next**.
- Keeps Edit Delivery Lists week headings/date rows compact (`M/D/YYYY`) and removes the generic green runtime dot from this records-oriented GUI header.
- Restores **Glass Type** directly to the right of Item Nr. in Delivery List Preview item rows while preserving Dimensions and Quantity after it.
- Narrows the Delivery List Preview modal from 1100px to about 780px (roughly 30%) while retaining responsive two-column/stacked behavior on smaller screens.
- Advances `APPLICATION_VERSION` to 396 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.395 highlights

- Replaces the Automation Control Center tab/action icons with cleaner vector-mask icons and adds restrained hover feedback.
- Polishes the Import History Refresh control with a dedicated refresh icon, loading state, hover response, and preserved new-results indicator.
- Makes Import History search route-aware and token-based, so searches such as `Airport 8/14` can match route aliases and dates together. Date filters keep a valid From/Through range and rapid filter changes cannot be overwritten by an older request.
- Reorganizes Edit Delivery Lists into business-week pages with compact numeric dates such as `8/14/2026`, matching the Home/date-selector week language. v0.396 supersedes the one-week paging size with the three-week operating window.
- Changes the Edit Stage selector/current-stage label to `M/D/YYYY - Stage` and removes redundant scanner text from that selector.
- Gives the manual editor Search control the shared primary blue treatment and replaces Load 20 More growth with server-backed Previous/Next pages.
- Advanced `APPLICATION_VERSION` to 395 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset was included.

## v0.394 highlights

- Reworks Automation Control Center **Import History** stage results into the same route language used by Delivery List Management: **Airport Road**, **Indian Trail**, **Greenville**, **CPU**, and **DTC**. Airport Road uses the authoritative Outbound copy so its totals represent all orders without double-counting Staging/Outbound copies.
- Adds compact route-level Before / Changes / After / Status rows inside each import result while preserving the existing business-week pagination and initially-collapsed history hierarchy.
- Makes Edit Delivery Lists open immediately with an explicit loading state while the current catalog refreshes, and shows the same loading feedback while the selected manual-edit stage and lookup data initialize.
- Makes a manual Admin deletion remove the same logical **Order Nr. + Item Nr.** from every stage copy for that delivery date, matching the sibling synchronization already used by manual edits. The audit record stores affected row/list IDs and the deletion count.
- Changes whole-list update previews so a single populated route opens automatically, while previews containing multiple routes start collapsed.
- Redesigns preview order content into one left-to-right identity row (**Order Nr. / Job Nr. / Customer / Flags**) followed by item rows containing only **Item Nr. / Dimensions / Quantity**. Redundant order line/QTY/change cells and per-item NEW/UPDATED pills are removed; change differences remain available where useful.
- Advances `APPLICATION_VERSION` to 394 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.393 highlights

- Replaces the Status & Logs `<details>/<pre>` scrolling structure with a dedicated three-row **Live command log** panel. The log viewport—not the text element—now owns vertical scrolling, so growing/wrapped output cannot expand the Status grid below the visible Automation Control Center.
- Adds an explicit end-of-log clearance marker, stable scrollbar gutter, contained wheel/touch scrolling, keyboard focus, and a **Newest** button. Follow-newest uses a double-layout-frame scroll plus `ResizeObserver`, keeping the final line fully visible as the log wraps or the modal changes size.
- Adds controller-side diagnostics to the same per-run log before PowerShell starts, including the requested action/range, overlap checks, runtime-file synchronization result, runner/summary/log paths, and final process exit code.
- Preserves the earliest startup trace for both browser-started and scheduled updates. Scheduled runs buffer pre-configuration log lines until their generated log file is available, so the persisted log begins at STEP 01.
- Adds structured PowerShell `STEP ##` and `DEBUG` trace lines with elapsed time for configuration, runtime folders, persisted decisions, lock acquisition, runtime preflight, action/date resolution, each delivery-date export, scanner reconciliation, cleanup, notification publication, final summary/history persistence, lock release, and total run duration.
- Adds delivery-date diagnostics for SQL query duration/row counts, source fingerprints, prior state and workbook-hash decisions, staging payload/file sizes, workbook validation/publication hashes, persisted state, temporary-file cleanup, and failure stack context.
- Expands Python importer diagnostics to show project/store initialization, target workbook discovery, per-date drift decisions, authoritative import decisions, post-import source coverage checks, Superseded Order Review synchronization, normalized result persistence, and final importer duration.
- Keeps credentials out of diagnostics: connection-string contents are never logged; only non-secret server/database/runtime context and file paths are recorded.
- Advances `APPLICATION_VERSION` to 393 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.392 highlights

- Corrected the prior Status-tab layout boundary by removing the log container's erroneous full-tab height and changing the final Status grid row to `minmax(0, 1fr)`. v0.393 supersedes the remaining `<details>/<pre>` implementation with a dedicated viewport.
- Replaced the shared Admin launcher's moving sweep sheen with a low-opacity stationary highlight that fades gently on hover/focus.
- Advanced `APPLICATION_VERSION` to 392 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset was included.

## v0.391 highlights

- Converts Superseded Orders **Item evidence** width/height values from the maintained A+W `1/32-inch` source units into normal inch/fraction display text, matching the delivery-list workbook formatter while leaving persisted review fingerprints and decisions untouched.
- Improves **Status & Logs** reachability by scrolling to the newest output after layout settles, keeping wheel gestures owned by the log, and reserving trailing scroll space so the final wrapped line clears the modal edge.
- Gives every Admin-dashboard GUI launcher one shared visual treatment with consistent geometry, icon placement, subtle depth, keyboard focus treatment, and a polished hover/press animation. Pending Superseded Order reviews retain the same shared component with an attention palette.
- Advances `APPLICATION_VERSION` to 391 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.390 highlights

- Makes the **Status & Logs** command log reliably scrollable while live status polling is active. Manually moving away from the newest line automatically disables **Follow newest activity** so the next refresh cannot snap the operator back to the bottom.
- Keeps the log as the Status tab's dedicated contained scroller, with stable vertical scrollbar space and no scroll chaining into the Automation Control Center shell.
- Starts every **Import History** date, category, run, and individual file-result dropdown collapsed so operators choose exactly how much detail to reveal.
- Splits each Import History date into **New / Updated / Exceptions** and **No New / Updated Lists** dropdowns, keeping successful no-change checks out of the way without discarding their audit history.
- Moves **Item evidence** immediately below the Superseded Orders suggested-removal panel and expands it by default so the source comparison is visible before the approval choices.
- Advances `APPLICATION_VERSION` to 390 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.389 highlights

- Reworked **Review Superseded Orders** into a more compact approval workflow with an unmistakable suggested-removal panel, preselected removal choice, inline scanner-impact counts, and collapsible item evidence.
- Routed superseded-order audit events into the shared Admin **Action History** and added readable removed/kept order details so approvals, Keep Both, and Review Later decisions are accurately visible immediately after the action.
- Condensed the Automation Control Center **Incremental schedule** and **Daily full refresh** settings into single horizontal rows while preserving all existing schedule inputs and save/install behavior.
- Reworked **Status & Logs** so the runtime summary uses less vertical space and the live command log owns the remaining workspace with its own contained scrollbar instead of being visually cut off.
- Changed Automation Control Center **Import History** to business-week pagination: one page keeps the entire Monday-Friday week and every run from those days together, preventing a busy day from being split across pages. The row-based import-history API remains available to existing non-Control-Center callers.
- Reduced the Import History heading/filter/status chrome to leave more room for weekly history content.
- Advanced `APPLICATION_VERSION` to 389 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.388 highlights

- Refines the individual-rack header lifecycle cell so **Incomplete**, **Complete**, **On the Way**, **Received**, and **Empty** use the exact same border/background/text palette as their Rack Overview status chips.
- Adds a compact lifecycle dot, adaptive sizing, stronger spacing/shadow, and responsive wrapping so the status remains readable beside long rack names and on narrower screens.
- Removes the v0.387 blanket `overscroll-behavior` rule that accidentally turned ordinary cards, headings, and non-scrollable panels into wheel dead zones.
- Limits scroll-boundary containment to true overflow owners. Normal page scrolling now continues when the pointer is over ordinary page content, while genuine nested scrollers still keep their own boundary behavior.
- Removes the broad Scan-page `[class*="scroll"]` containment selector and the non-scrollable bay-scanner-panel containment that could block document scrolling when hovered.
- Advances `APPLICATION_VERSION` to 388 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.387 highlights

- Places Global Search's latest scanned date/time on the same status row, aligned to the right of the resolved current stage/location, and gives Smart Results a contained vertical scrollbar.
- Prevents wheel/touch scroll chaining from exhausted internal GUI and results scrollers into the page behind them; all visible shared modals now participate in the central body-scroll lock.
- Keeps the Staging/Delivery Stage custom-select menu attached to its trigger during page scrolling and lowers the sticky scanner panel beneath the sticky application header.
- Adds a colored lifecycle cell immediately to the right of the individual rack name for **Incomplete**, **Complete**, **On the Way**, **Received**, and **Empty** states. Removes the duplicate green-dot health indicator and the old body-level Rack Status banner from the rack workspace.
- Repairs the **Not On The Way** button hover/focus palette so it keeps readable high-contrast text instead of inheriting the generic dark-blue hover.
- Grays rack move/clear controls when an **On the Way** rack is lifecycle-locked and shows a centered explanation when the operator clicks a blocked control. The backend now enforces the same lock for single-item moves and rack/item clears, not only move-all.
- Extends explanatory blocked-action behavior to rack/rack-set deletion prerequisites and converts non-Scan backend errors into the shared action-feedback popup instead of re-rendering the Scan page behind another workspace.
- Removes the duplicate **Clear selected rack set** button beside the rack Sort control.
- Advances `APPLICATION_VERSION` to 387 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.386 highlights

- Shortens canonical internal bay identifiers such as `T-BAY12-01` to the operator-facing label **Bay 12-01** without changing the stored bay code used by the backend, scans, or assignments.
- Shows active/current bays in the Scan-page Location column only while viewing the Indian Trail receiving stage.
- Keeps the most recent bay visible in gray after a bay assignment is cleared or cancelled so scanning glass out of a bay does not erase its physical-location history.
- Shows rack/truck locations instead of bay locations on Staging and Outbound. Once the piece has been received downstream, that rack remains visible in gray as prior transportation history rather than changing to a generic **Received** badge.
- Applies the same stage-aware compact Location behavior to Last Scan and Recent Scans.
- Shortens rack destination/route display labels to **IT**, **CPU**, **DTC**, and **GNV** while preserving the existing canonical stored destination values.
- Advances `APPLICATION_VERSION` to 386 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.385 highlights

- Makes the Home **Today's Delivery** stage grid dynamically divide the available width by the live stage count so all active stages remain on one row.
- Rebuilds the successful-scan **Correct rack / truck** selector to use the selected rack's maintained color and compact operator label, matching the Scan Location column while remaining editable.
- Replaces the basic Truck rack glyph with a clearer box-truck silhouette across Rack set cards, Rack configuration previews, In Transit usage, and Rack detail headers.
- Contains cleared/historical rack locations inside the Location cell with a compact **PRIOR** status pill instead of allowing the old suffix to escape the colored rack box.
- Adds orange Rush date-move traceability ribbons: the source date states where the order moved, while the corresponding target-date stage shows a non-counting reference so the order can be found on both delivery dates.
- Keeps Rush move references separate from stage quantities/scanned totals so moving a priority delivery date never double-counts pieces.
- Extends the existing transform-free page transition from 180ms to 230ms for a slightly smoother navigation fade without restoring movement or jitter.
- Preserves all existing Airport Rd Forward View calculations, physical Bay Map colors, rack/bay workflows, permissions, and SQLite schema version 11.
- Advances application/cache references and `APPLICATION_VERSION` to v0.385.

## v0.384 highlights

- Reduces the Home **Forward View** section by approximately 15% through tighter vertical spacing, card height, padding, progress-bar height, and summary-chip sizing while preserving the five-date desktop layout.
- Moves the Airport Rd staging `scanned / total` piece amount from the bottom-right to the **bottom-left** of each date card.
- Keeps the **stage count** anchored in the top-right of every Forward View date card.
- Preserves the existing Airport Rd staging source-of-truth calculation, date click-through behavior, Home artwork, page transitions, and SQLite schema version 11.
- Advances application/cache references and `APPLICATION_VERSION` to v0.384.

## v0.383 highlights

- Removes the Delivery Date field from individual Rack detail lines and gives **Job Nr.** substantially more horizontal room.
- Rebalances the Rack details content area with calmer application-blue surfaces instead of the overly bright white treatment; Lookup Manager glass color remains localized to the **Glass Type** field only.
- Makes selected Print / Export glass-type filters unmistakable with a neutral app-blue selection frame and check badge while keeping each glass hue subtle in the background.
- Keeps **All Glass Types** as a high-contrast white-on-blue selected state in Print / Export.
- Restores the Forward View **stage count** in the top-right of each date card.
- Keeps the Airport Rd staging `scanned / total` piece amount in the bottom-right, but removes the **Airport Rd pieces** text label entirely.
- Preserves v0.382 Scan selection stability, glass-filter clarity, Bay Map stage-card polish, Home artwork, page transitions, physical Bay colors, and SQLite schema version 11.
- Advances application/cache references and `APPLICATION_VERSION` to v0.383.

## v0.381 highlights

- Removes the compact **Open Stage** affordances from Today's Delivery and returns the Home stage cards to their cleaner whole-card navigation presentation.
- Restores the original physical **Bay Map** category/status colors and removes Lookup Manager glass tinting from physical bay slots and selected-bay item details; In Transit and other glass-aware GUIs keep their subtle glass presentation.
- Adds an explicit **Glass Type** field to each individual Rack details line and applies only a faint Lookup Manager tint to the complete line.
- Fixes **Print / Export** glass control contrast, including a deliberate neutral/selected treatment for **All Glass Types**, while keeping exact glass colors subtle.
- Fixes the Scan Filters **All Glass Types** selected count so the quantity remains visible on the dark selected state.
- Normalizes the Job Nr. / Glass Type content box to fill the full first-column width so glass-gradient cells align evenly from row to row.
- Adds a dedicated **Glass Type** column to **All Scans** using the same restrained Lookup Manager glass treatment.
- Allows clicking the currently selected Scan line a second time to clear the selection, including mobile cards, and softens the selected-row outline/background.
- Preserves Airport Rd Forward View math, success-popup rack selection, In Transit styling, packing-list behavior, Home artwork, page transitions, permissions, and SQLite schema version 11.
- Advances application/cache references and `APPLICATION_VERSION` to v0.381.

## v0.380 highlights

- Adds compact **Open Stage** affordances with stage-colored hover feedback to each Today's Delivery stage card while preserving whole-card navigation.
- Rebalances Lookup Manager glass colors into a much softer background language: low-opacity gradients, lighter borders/rings, and no fully saturated active glass chips.
- Overrides legacy hard-coded glass category colors where the new Lookup Manager tone is present, including In Transit and Bay item surfaces, and neutralizes older Print/Export category accent colors so exact saved glass colors remain authoritative.
- Enlarges the Scan Filters drawer to a two-column desktop workspace with larger labels, buttons, glass choices, and spacing for easier reading.
- Fixes the **All Glass Types** active-state contrast and adds targeted contrast corrections for dark hover/active controls that could inherit dark text.
- Adds an explicit Glass Type label to each individual rack line item and tints the complete rack row with the same very subtle saved glass gradient.
- Extends saved glass treatment to populated Bay Map slots while keeping empty bays neutral.
- Preserves Airport Rd Forward View math, success-popup rack selection, packing-list behavior, page transitions, Home artwork, permissions, and SQLite schema version 11.
- Advances application/cache references and `APPLICATION_VERSION` to v0.380.

## v0.379 highlights

- Changes **Forward View** to use the Airport Rd **Staging** list only for workload/completion, showing `scanned / total` Airport Rd pieces instead of summing duplicated pieces across every destination stage.
- Makes the successful Scan confirmation rack/truck selector open on the rack or truck that accepted the scan, while preserving the existing correction workflow for changing the location immediately.
- Rebuilds the Scan **Filters** drawer into a smaller three-column application-styled workspace with tighter controls and removes the inherited duplicate OK/check/warning icons from Rush, Remake, and Internal Reject filters.
- Publishes Lookup Manager glass colors through an authenticated read-only presentation endpoint and uses them for a shared subtle gradient language across Scan filters/list rows, Racks, Bay Map/In Transit, Manage Items, Missing Glass, Old Bays, Rejects, Statistics glass rows, and Print/Export glass controls.
- Revamps the **In Transit** glass/rack presentation with cleaner hierarchy, app-matched surfaces, and Lookup Manager glass gradients.
- Rebuilds rack **Packing List** printing to visually align with the Delivery List print language: cleaner header/meta treatment, light table headers, glass-type grouping rows, check-off fields, and a landscape document layout while keeping the rack scan barcode.
- Preserves Home artwork, opacity-only page transitions, scanning/rack/bay workflows, permissions, and SQLite schema version 11.
- Advances application/cache references and `APPLICATION_VERSION` to v0.379.

## v0.378 highlights

- Removes the redundant **open** piece count from each Forward View delivery-date card.
- Rebuilds each date card around a clearer sequence: weekday/date, polished completion bar, then a compact total-pieces summary below it.
- Moves the completion percentage onto the progress bar, matching the visual language used by expanded Delivery Library stage cards.
- Adds a small piece/cube icon and raised soft-blue treatment around the total piece quantity so workload is easier to recognize at a glance.
- Slightly increases weekday, numeric date, percentage, piece-count, and stage-count typography throughout Forward View without changing the five-date layout.
- Preserves date click-through, Home artwork, opacity-only page transitions, permissions, and SQLite schema version 11.
- Advances application/cache references and `APPLICATION_VERSION` to v0.378.

## v0.377 highlights

- Scales the transparent Home truck/warehouse illustration back from the oversized v0.376 treatment to a more balanced desktop footprint.
- Softens the illustration to roughly half-opacity so it reads as background decoration rather than competing with the greeting or operational stage cards.
- Lowers the artwork slightly and shortens the reserved greeting area so the live stage cards can overlap the bottom edge of the illustration by a small amount while remaining fully readable and clickable above it.
- Retains the transparent v0.375 image asset and the matched Home hero gradient for a seamless blend with no visible rectangular image background.
- Preserves the v0.376 opacity-only page transitions, Bay Map initial transit animation fix, Settings/Admin reveal behavior, and reduced-motion support.
- Preserves all workflow/data behavior and SQLite schema version 11.
- Advances application/cache references and `APPLICATION_VERSION` to v0.377.

## v0.376 highlights

- Replaces the page-entry translate/settle animation with a pure opacity transition so a newly selected page never dips downward before fading into place.
- Prepares the incoming page at 0 opacity **before** it is unhidden, removing the one-frame full-opacity flash that caused the v0.375 navigation jitter.
- Keeps the transition intentionally fast at 180ms and retains `prefers-reduced-motion` handling.
- Fixes the Bay Map in-transit truck on initial page entry by removing the temporary hidden/paused state before restarting the truck animation, then softly revealing the refreshed route panel.
- Ensures the static Settings/Admin header is present in the prepared page state and participates in the first clean fade instead of appearing before the transition begins.
- Makes the transparent Home truck/warehouse artwork substantially larger and wider on desktop, with responsive intermediate sizes while keeping it hidden on narrow mobile layouts.
- Preserves all scanning, delivery-list, rack, bay, reject, statistics, admin, permission, and SQLite schema version 11 behavior.
- Advances application/cache references and `APPLICATION_VERSION` to v0.376.

## v0.375 highlights

- Adds `static/images/home-delivery-header-v0375-transparent.png`, derived from the approved supplied artwork with the generated sky/background removed so the illustration blends into the live Home hero instead of reading as a rectangular image.
- Retunes the Today's Delivery hero gradient to the same pale blue family as the artwork and positions the transparent scene on the upper-right with a restrained shadow for a seamless transition.
- Keeps the stage cards and greeting above the decorative artwork and preserves the mobile hide behavior when the header becomes too narrow.
- Adds a subtle 190ms fade-and-4px settle animation when Home, Statistics, Scan, Racks, Rejects, Bay Map, or Settings is entered, including the initial Home reveal after sign-in.
- Honors `prefers-reduced-motion` so the page-entry animation is disabled for users who request reduced motion.
- Preserves all scanning, delivery-list, rack, bay, reject, statistics, admin, permission, and SQLite schema version 11 behavior.
- Advances application/cache references and `APPLICATION_VERSION` to v0.375.

## v0.374 highlights

- Adds the supplied polished delivery-truck/warehouse artwork as `static/images/home-delivery-header-v0374.png` rather than redrawing the scene in CSS.
- Replaces the v0.373 inline SVG decoration with the real image asset in the upper-right of **Today's Delivery**.
- Sizes and positions the image so its built-in left-side negative space protects the greeting while the truck/warehouse scene remains prominent on the right.
- Keeps the artwork entirely above the live stage cards and disables it on narrow mobile layouts where it would compete with operational content.
- Preserves all Home progress behavior, stage drill-through, Forward View, Delivery Library interactions, permissions, and SQLite schema version 11.
- Advances application/cache references and `APPLICATION_VERSION` to v0.374.

## v0.371 highlights

- Reconfines the Home **Today's Delivery** truck-and-trees illustration to the upper-right hero zone so it no longer appears behind the stage cards.
- Replaces the translucent decoration treatment with solid soft-blue illustration fills for a cleaner, more consistent Home first-view experience.
- Keeps the greeting and live stage grid clearly layered above the artwork so the decoration remains decorative instead of competing with workflow content.
- Adds matching top-right decorative illustrations to the major application page headers, including Statistics, Scan, Racks, Rejects, Bay Map, and Settings.
- Uses page-appropriate illustration motifs to make each header feel polished while preserving the current structure and controls.
- Preserves all Home drill-through behavior, Delivery Library interactions, permissions, and SQLite schema version 11.
- Advances application/cache references and `APPLICATION_VERSION` to v0.371.

## v0.370 highlights

- Increases the entire Home **Today's Delivery** first-view hero by about 30%, including greeting/date hierarchy, stage-card height, icon scale, spacing, and progress controls.
- Replaces the basic truck/tree watermark with a clearer delivery scene using a more detailed box truck, cab/window/wheels, road line, layered trees, and subtle landscape depth while keeping the illustration decorative and right-aligned.
- Replaces the shared truck glyph for Greenville/DTC with distinct destination icons: a facility/warehouse for Greenville and a customer-home delivery icon for DTC.
- Removes false colored progress slivers at 0% by omitting zero-progress header segments and zero-fill stage elements entirely.
- Adds polished hover/focus feedback to Today's stage cards and the Delivery Library **Open Stage** affordance without reintroducing the older janky card-lift motion.
- Normalizes Forward View weekday, date, workload, open, stage-count, and percentage typography; weekday labels now use the Home header blue.
- Preserves all current Home drill-through behavior, Inbound presentation, Delivery Library search/paging, permissions, and SQLite schema version 11.
- Advances application/cache references and `APPLICATION_VERSION` to v0.370.

## v0.369 highlights

- Rebuilds each expanded Delivery Library stage card as a contained two-column layout: stage identity/progress on the left and Open Stage on the right.
- Moves the stage progress bar directly underneath the stage title/support text so it cannot extend beyond the stage card when the card is narrow.
- Keeps the stage icon, Inbound/Outbound presentation, stage color, percentage-on-bar, and `scanned / total` piece count from v0.368.
- Adds responsive containment so the Open Stage action drops below cleanly on smaller widths without changing the progress bar's ownership.
- Preserves Delivery Library search, date grouping, stage drill-through, permissions, and SQLite schema version 11.
- Advances application/cache references and `APPLICATION_VERSION` to v0.369.

## v0.368 highlights

- Enlarges the overall progress bar in each Delivery Library date header so it becomes a clear visual anchor rather than a tiny inherited progress strip.
- Replaces the plain right-side piece quantity with a polished **Total Pieces** summary card and piece icon.
- Rebuilds expanded delivery stages into a stable three-column layout: stage identity, stage-colored progress, and Open Stage action.
- Keeps percentage inside each stage progress bar and the requested `scanned / total` piece count directly beneath it.
- Changes the user-facing **Received** stage label to **Inbound** without changing stored stage values, routes, APIs, or Indian Trail workflow behavior.
- Replaces the Received checkmark with a diagonal down-right Inbound arrow that mirrors the Outbound arrow style on Today's Delivery and Delivery Library cards.
- Preserves all existing Home navigation, delivery search/filtering, business-week paging, permissions, and SQLite schema version 11.
- Advances application/cache references and `APPLICATION_VERSION` to v0.368.

## v0.367 highlights

- Anchors the Today's Delivery truck/tree watermark to the far-right edge so it no longer competes with the greeting.
- Removes the extra Forward View and Quick Destinations explanatory sentences and increases Forward View date-card height by another 20% for better readability.
- Replaces Home lift/translate hover motion with fast border, background, and shadow feedback to eliminate the janky trailing feel.
- Rebuilds expanded Delivery Library stage rows with the same stage icon language as Today's Delivery, a subtle stage-colored gradient, and one polished stage progress control instead of separate Scanned/Open/Pieces counters.
- Shows each expanded stage as a stage-colored progress bar with the completion percentage inside the bar and `scanned / total` directly below it.
- Reformats Delivery Library date headings to show weekday above the numeric date and centralizes the full-date progress track further left.
- Preserves all existing Home click-through behavior, search/filtering, business-week paging, permissions, and SQLite schema version 11.
- Advances application/cache references and `APPLICATION_VERSION` to v0.367.

## v0.366 highlights

- Matches the approved Home screenshot with a pale blue/white first-view hero, subtle delivery-truck watermark, larger greeting/date, and four evenly sized live stage cards.
- Rebuilds stage-card visuals around the existing live markup: colored left accent, stage-specific icon tile, normalized count hierarchy, slim progress track, and right-aligned completion percent.
- Rebalances **Forward View** to the screenshot density with five equal delivery-date cards, a rectangular `View all delivery lists` action, and clearer workload/progress spacing.
- Enlarges the six destination cards to the approved proportions with large colored icon tiles, circular arrow controls, page-specific tinting, and subtle dotted corner texture.
- Softens the Delivery Library into a pale blue discovery surface with an integrated heading and clean white search/stage controls.
- Preserves all existing Home data renderers, drill-through behavior, permissions, delivery-list search/paging, and SQLite schema version 11.
- Advances application/cache references and `APPLICATION_VERSION` to v0.366.

## v0.364 highlights

- Lightens the Home **Today's Delivery** background into the same layered blue family used across the rest of the web app rather than a standalone dark banner.
- Enlarges the local-time greeting/operator text to 30px and the delivery date to 23px on desktop for faster recognition.
- Returns the stage cards to light raised surfaces with navy typography while preserving live progress, click-through behavior, and stage status.
- Increases Forward View card height from 76px to 91px (about 20%) and proportionally restores heading, metric, spacing, and progress-bar size without returning to the older oversized layout.
- Keeps the v0.363 single-theme application model; Dark mode remains removed.
- Advances application/cache references to v0.364 while preserving SQLite schema version 11.

## v0.360 highlights

- Removes the Home `Delivery operations / Operations Hub / Signed in as ...` header block so **Delivery Progress by Stage** moves to the top of the page.
- Adds **Good morning / Good afternoon / Good evening** using each browser's local clock and includes the current operator name.
- Rebalances Delivery Progress with a lighter blue operational surface, higher-contrast date pill, and brighter stage cards.
- Adds a per-user **Appearance** control under the profile menu with Light and Dark choices.
- Stores the appearance preference by signed-in user and restores it automatically at login/session load.
- Adds `static/css/theme.css` as the final shared theme layer so dark mode can cover the whole application without duplicating page-specific styles.
- Advances application/cache references and `APPLICATION_VERSION` to v0.360. SQLite schema remains version 11 with no migration.

## v0.359 highlights

- Removes the Home **Priority Work** and **Print / Export** destination cards plus the v0.358 Floor Command Center, Needs Attention/Action Queue, and Common Workspaces/Navigation sections.
- Moves **Delivery Progress by Stage** directly below the Home header and rebuilds it as the primary live floor-status surface with a sleek dark-navy treatment, compact live-status indicator, and direct stage drill-through.
- Keeps the destination strip focused on six page destinations: **Scan, Racks, Bay Map, Statistics, Rejects, and Settings**. Existing permission gates are retained for restricted pages.
- Renames the user-facing top-level **Admin** page/navigation entry to **Settings Page / Settings** while preserving the existing `admin` page key, Admin APIs, permissions, modal IDs, and internal implementation names.
- Removes the Home side rail entirely so **Forward View / Upcoming Delivery Timeline** spans the normal full content width instead of being constrained by the old Action Queue and Navigation columns.
- Gives **Find a Delivery List / Delivery Library** a stronger navy header, richer blue finder surface, polished week bands, and clearer open-date emphasis while retaining all existing search, stage filters, grouping, paging, and exact-list drill-through.
- Keeps the v0.358 lightweight Home data model: Forward View and stage progress reuse the already-loaded delivery catalog and do not add a new recurring dashboard API.
- Advances application/cache references and `APPLICATION_VERSION` to v0.359. SQLite schema remains version 11 with no migration.

## v0.358 highlights

- Replaced the old Home layout with a polished **Operations Hub** designed as the application's primary launch surface rather than a passive delivery-list browser.
- Added the original six-button **Quick Actions** strip, live Operational Pulse, Needs Attention queue, Upcoming Delivery Timeline, stage progress, and lower Delivery Library. v0.359 intentionally simplifies that design while retaining its Forward View, direct navigation, and delivery-library architecture.
- Added responsive Home ownership for desktop, intermediate, tablet, and phone layouts while preserving the v0.354+ GUI performance safeguards.
- Advanced application/cache references and `APPLICATION_VERSION` to v0.358. SQLite schema remains version 11 with no migration.

## v0.357 highlights

- Raises the body-mounted **Move Rack** selector above the Operations modal stack with an explicit top-level menu class/z-index while retaining the shared Scan-page rack formatting, route pills, lifecycle cues, and viewport-aware above/below positioning.
- Changes **Rack History → Packing List History** from 25-print-day pagination to true **5 business weeks per page**. Pages are built after date/search filtering, so each page contains at most five grouped weeks regardless of how many packing-list print days exist in those weeks.
- Adds a shared top-level page-header geometry contract across Home, Statistics, Scan, Racks, Rejects, Bay Map, and Admin: consistent height, padding, corner radius, heading size, description rhythm, and eyebrow typography while preserving each page's established accent color, icons, and action controls.
- Adds consistent page eyebrows to Home, Scan, Racks, and Admin so the lighter header variants follow the same information hierarchy already used by Statistics, Rejects, and Bay Map.
- Advances application/cache references and `APPLICATION_VERSION` to v0.357. SQLite schema remains version 11 with no migration.

## v0.356 highlights

- Replaces the Missing Glass exact-item ledger with self-contained selectable glass cards. Every card owns Order/Item, Job Nr., Glass/Size, Physical Bay, Expected, Accounted, Missing, and status labels, preventing long values from shifting unrelated columns. Existing `data-sdi-line-item-id` selection and backend behavior are unchanged.
- Completely rebuilds **Print Investigation List** to mirror the current Old Bays Control Center: Physical Bay sections contain whole-order cards, age/snooze state appears at order level, Job Nr. and Order stay together, glass lines show In Bay/Missing/Status, and each order has a physical-verification checkbox and investigation-notes line.
- Removes the private nested Move Rack combobox. Rack transfers now use the same enhanced body-mounted rack selector as Transportation Method on Scan, including route pills, rack lifecycle cues, rack-set color metadata, full `Display Name | PCs | Status` labels, keyboard behavior, and automatic above/below viewport positioning.
- Normalizes all Bay Map **Manage Items** text from the overly compact initial scale to the standard operator-readable size while preserving the v0.355 layout and actions.
- Keeps the v0.354 GUI performance safeguards and the v0.355 Missing Glass/Old Bays/Last Scan/Manage Items architecture intact.
- Advances application/cache references and `APPLICATION_VERSION` to v0.356. SQLite schema remains version 11 with no migration.

## v0.355 highlights

- Throws out the previous Missing Glass presentation and replaces it with an isolated v0.355 workspace that does not inherit the legacy Rush/SDI form grid. Search, bay filtering, missing-line selection, shortage ledger, priority handling, communication options, and final actions now live in a deliberate two-column operator layout with a responsive single-column fallback. Existing IDs, line-item selection, direct-to-truck handling, email modes, APIs, and audit behavior are preserved.
- Reworks Old Bays order state into a dedicated top ribbon. Every order shows its age in days at the upper left; snoozed orders add a clear purple Snoozed state, live snooze time remaining, and the exact snoozed-at date/time. The existing orange-to-red age severity remains on the whole order and resumes automatically after snooze expiry.
- Extends the Scan-panel Last Scan Location card with the same resolved rack-set accent used elsewhere in the application. Steel, Wood, Truck, and custom rack sets now carry their rack color into Last Scan; completed current racks retain the green completion priority and historical locations remain muted.
- Completely rebuilds Bay Map **Manage Items** around a command/search bar, grouped Bay Inventory ledger, explicit current-selection summary, destination/reason controls, and compact move/clear/scanner/SDI actions. Existing selection and move/clear event hooks remain intact.
- Keeps the v0.354 GUI-performance improvements and avoids reintroducing legacy grid/observer ownership into the rebuilt workspaces.
- Advances application/cache references and `APPLICATION_VERSION` to v0.355. SQLite schema remains version 11 with no migration.

## v0.353 highlights

- Shrinks the **All Scans Location** column to content width and makes `rack_move` rows use the explicitly logged destination. Rack-move source detection now chooses the newest active rack assignment instead of rack sort order, preventing reversed `Steel 9 → Steel 1` history when the actual move was `Steel 1 → Steel 9`.
- Uses one transition timestamp for rack assignment/removal writes and treats removal/clear timestamps as exclusive event-history boundaries, eliminating ambiguous source/destination matches at timestamp ties.
- Removes forced layout reads from modal scroll-lock detection, filters modal mutation observation to actual modal-state changes, skips English translation work on DOM mutations, stops observing unrelated class churn in the custom-select enhancer, and lazy-loads hidden Action History content where applicable.
- Cleans orphaned body-mounted dropdown layers when pages/GUI state changes and hardens the Rack page **Racks History** / **Edit Racks** hit targets against stale overlays and sticky-header edge overlap.
- Adds a final application-wide runtime/unhandled-promise error boundary that opens the shared in-app error dialog when an unexpected action fails; existing validation/request errors continue using their specific blocked/error feedback.
- Makes completed rack assignments green in the Scan **Location** column, matching completed Transportation Method status.
- Rebuilds Old Bays with a compact Job Nr. → Order identity row, age-driven orange-to-dark-red line accents, red `MISSING` / `OLD BY X DAYS` status, purple snoozed state, matching per-order snooze controls, live time-left plus snoozed-at timestamps, and removes the redundant physical-order-count sentence.
- Condenses Missing Glass into one search/selection toolbar, one scrollable shortage ledger, a compact handling row, collapsible email options, and a small final action bar while preserving the existing IDs, exact-line selection, email modes, direct-to-truck behavior, and API/audit contracts.
- Advances application/cache references and `APPLICATION_VERSION` to v0.353. SQLite schema remains version 11 with no migration.

## v0.352 highlights

- Makes the closed **Transportation Method** selection mirror the opened rack rows: the resolved route appears as the leading colored route pill, followed by `Display Name | PCs | Status`, without duplicating the route in plain text.
- Normalizes Scan Location rack labels to uppercase in both passive and editable row states while preserving identical typography and rack-set coloring.
- Adds **Location** to All Scans and resolves the rack/bay that was active at each event timestamp, so historical scans retain locations such as `TRUCK 1` even after the same item is later moved to `STEEL 1`. Manual Location-cell rack moves are also recorded as explicit `Rack moved` history events.
- Prevents polling/background refreshes from replacing an operator-selected delivery-list row with the latest/first scan item while the selected row still exists.
- Rebuilds Old Bays into a normalized Bay → Order → Glass ledger with one readable order header, aligned piece rows, compact physical summary, missing-piece emphasis, quiet snooze controls, and collapsible neighboring-order context.
- Rebuilds Missing Glass into three clear work areas—Find Work, Verify & Select, and Rush Handling—with an aligned physical-shortage ledger, loaded-job totals, separated production/communication settings, and a clear final action bar. Existing exact-line selection, email, direct-to-truck, clear, and audit behavior is preserved.
- Advances application/cache references and `APPLICATION_VERSION` to v0.352. SQLite schema remains version 11 with no migration.

## v0.351 highlights

- Locks Scan Location typography to the same 12px/850-weight metrics before and during rack reassignment, eliminating the selected-cell font-size jump.
- Uses the exact resolved Rack Overview set accent—including deterministic fallback hues—for Location cells and shared rack option metadata, so Steel, Wood, Truck, and custom rack sets keep the same recognizable color everywhere.
- Increases the compact opened rack menu by 13% from v0.350 while keeping it substantially smaller than the original oversized selector.
- Keeps open rack labels in `Display Name | PCs | Status` format and makes the closed **Transportation Method** selection include the resolved route. Inline Location remains display-name-only.
- Rebuilds Old Bays content into a physical verification ledger while preserving search/filter/select/snooze/print behavior.
- Rebuilds Missing Glass as a guided workflow while preserving its existing APIs and audit behavior.
- Advances application/cache references and `APPLICATION_VERSION` to v0.351. SQLite schema remains version 11 with no migration.

## v0.350 highlights

- Normalizes legacy stored rack names such as `Rack 1 Steel`, `Rack 2 Steel`, `Rack 1 Wood`, and `Rack 2 Wood` into operator-facing `Steel 1`, `Steel 2`, `Wood 1`, and `Wood 2` without rewriting persisted rack records.
- Keeps rack option text in the requested `Display Name | PCs | Status` format and continues suppressing the piece segment when quantity is zero.
- Reduces the opened shared rack menu to 70% of the previous width/available height and tightens only the opened option list; closed Transportation Method and other operational selectors retain their larger scanning-panel presentation.
- Rebuilds inline Scan Location reassignment so the normal rack-colored Location badge remains visible while editing. The shared selector is now a transparent interaction layer instead of replacing the cell with a visibly different dropdown control.
- Replaces the previous Rush/Remake-versus-Missing-Glass mode buttons with one New Request type selector containing **Rush**, **Remake**, and **Missing Glass**. Missing Glass continues to use the existing exact imported-item workflow and backend behavior.
- Advances application/cache references and `APPLICATION_VERSION` to v0.350. SQLite schema remains version 11 with no migration.

## v0.345 highlights

- Old Bays puts **All old bays / Live stale / Snoozed** in the same top modal tab rail as Action History. Search/Age/Sort/Print occupy the first command row, while Select All/Clear Selected/selected pieces sit beneath Search and bulk snooze sits beneath Print with Days immediately to its left.
- Rack dropdowns share one grouped-by-set organization across Scan, All Scans, outbound override/status, and rack-transfer workflows. Within each set, racks are sorted naturally by rack code.
- Open custom rack dropdowns contain explicit lifecycle dots and route pills in addition to the colored edges, so the color information is visible inside the menu instead of only on the closed selector.
- Move-all / rack-transfer destinations use the same rack-set headings, rack-code labels, lifecycle colors, and route colors as Scan selectors.
- Scan Complete/Uncomplete and Print/Not On The Way controls keep stable desktop widths as their labels change state.
- Rack History Action History receives a local 7px upward correction, cancelling the shared downward optical shift only in that GUI while leaving all other Action History icon alignment unchanged.
- Application/cache version advances to v0.345. SQLite schema remains version 11.

## v0.344 highlights

- Old Bays no longer loses snoozed rows when the Bay Map refreshes its unsnoozed attention badge. Snoozing from the Live stale tab returns the workspace to All so the newly snoozed row remains visibly in the queue.
- Old Bay controls are reorganized into a clearer hierarchy: Select All/Clear Selected/selection total above Search; Age and Sort immediately beside Search; snooze days immediately left of the right-aligned Snooze/Extend action; Print Investigation List sits below that snooze action.
- Bulk snooze wording now becomes **Extend Snooze** when all selected rows are already snoozed and **Snooze / Extend** for mixed selections.
- Snooze ribbons put **time left** first and move **Snoozed ... ago** to the secondary position.
- Rack selectors use rack **codes** rather than display names, e.g. `R1M IT 2pcs Complete`, while retaining the compact `(Empty)` format for empty racks.
- Scan/custom rack dropdowns and rack-transfer choices now expose lifecycle and route color cues at the same time: lifecycle color on the left edge and route color on the right edge.
- SQLite schema remains version 11.

## v0.343 highlights

- Old Bays keeps All / Live stale / Snoozed tabs above a unified command area containing Search, selected rows/pieces, Select All, Clear Selected, snooze days, Snooze Selected, Age, Sort, and Print Investigation List. The retired Physical verification queue instructional header remains removed.
- Rack dropdown labels use one shared compact operator format across Scan and rack transfers.
- Completed racks remain selectable for lifecycle management, with Complete/Uncomplete and Print/Not On The Way aligned directly with Transportation on desktop.
- All maintained Action History rows use the shared action-specific icon renderer with the 7px downward optical adjustment applied globally.
- SQLite schema remains version 11; no migration or database reset is required.

## v0.342 highlights

- Adds purpose-specific colored icons to every maintained Action History event row. Shared Admin/Bay/Rack/Reject action-history views and the all-racks activity list use the same event-category icon language.
- Keeps completed racks selectable from the Staging Scan rack selector for lifecycle management while still blocking new staging scans until reopened.
- Preserves visible SVG icons on dynamic Staging lifecycle/packing-list controls and Scan-page update-review actions.
- Removes the Old Bay four-card metric strip; queue counts remain available directly in the All / Live stale / Snoozed tabs.
- SQLite schema remains version 11; no migration or database reset is required.

## v0.341 highlights

- Locks **Uncomplete Rack** and **Not On The Way** to their dedicated gold/coral lifecycle palettes across normal, hover, focus, and child-text states so shared button rules cannot turn them blue with unreadable text.
- Adds purpose-specific icons to every individual-rack lifecycle action: Complete, Mark On The Way, Uncomplete, Mark Returned, Not On The Way, and Print Packing Slip. Existing move/clear controls retain their icon-only treatment.
- Adds direct SVG icons to Rack Overview **Racks History** and **Edit Racks**.
- Adds a consistent icon language to Scan-page action buttons, plus compact semantic markers on Scan filter tabs without cluttering sortable column headers.
- Adds a search/magnifier icon to the Bay Map **Find Match** button.
- Gives Old Bay **All old bays / Live stale / Snoozed** tabs distinct blue, orange, and purple visual identities with matching active-state treatments.
- Rebuilds the Old Bay command center so tabs remain above Search, while Search shares the main action row with a concise selected-row/piece summary, **Select All**, **Clear Selected**, snooze duration, and the existing purple **Snooze Selected** action.
- Changes the Old Bay selection summary to report both selected rows and total selected pieces, removes the verbose review-selection copy, and removes the redundant Done button.
- **Select All** now always selects every currently matching Old Bay row; **Clear Selected** is a separate explicit action instead of overloading one toggle button.
- SQLite schema remains version 11; no migration or database reset is required.

## v0.340 highlights

- Moves the Packing List History document glyph another 3px down while preserving the existing 1px right optical correction.
- Replaces shared-blue styling on **Uncomplete Rack** and **Not On The Way** with distinct polished lifecycle rollback treatments and matching action icons.
- Merges Old Bay queue tabs, Search/Age/Sort, Investigation List printing, review selection, bulk snooze, and Done into one visually unified command center with the queue tabs above Search.
- Keeps the Investigation List action visually separate as a recognizable printer control while allowing Search to remain the dominant workspace control.
- Makes the bulk **Snooze selected** action share the same purple Zz action language as each row's Snooze / Extend button.
- Simplifies snooze ribbons to `Snoozed … ago` plus `… left`; removes the redundant total snooze-window text.
- Shows snooze seconds only for durations below one hour, reducing visual noise on day/hour-scale snoozes while retaining second-level feedback near expiration.
- SQLite schema remains version 11; no migration or database reset is required.

## v0.339 highlights

- Moves the Packing List History document glyph another 2px down while preserving the existing 1px right optical offset.
- Applies the shared blue `app-primary-button` treatment to **Not On The Way** in the individual Rack GUI and removes the obsolete amber override.
- Rebuilds the Old Bay review-action bar as an evenly proportioned control grid with All / Live stale / Snoozed queue tabs and a direct SVG printer icon.
- Adds second-level elapsed, remaining, and total snooze timing. The countdown updates in place every second instead of rebuilding the entire Old Bay list, so search focus and row duration selections remain stable.
- Fixes **Extend Snooze** semantics: active snoozes now add the requested days after the current expiration instead of resetting to `now + days`, which could previously shorten an existing snooze.
- Moves the Bay identifier to the start of each Old Bay order header, followed by Order Nr., Item Nr., and days old.
- Gives each row's Snooze / Extend control a dedicated polished purple action treatment and explicit `Extend snooze by` wording.
- Moves the Bay Map in-transit `Racks:` summary directly beneath the **Pieces on the way** pill.
- SQLite schema remains version 11; no migration or database reset is required.

## v0.338 highlights

- Moves the Packing List History document glyph a small amount right/down inside its blue badge to correct the remaining optical misalignment shown in the operator screenshot.
- Adds **Mark On The Way** to completed racks in the individual Rack GUI. The action requires an Are-you-sure confirmation, applies only remaining Outbound quantities for every active rack item, performs maintained Indian Trail preassignment, records rack-scoped scan/audit history, and then marks the rack In Transit.
- Upgrades all five Bay Map launcher icons from small CSS primitives to direct SVG artwork while preserving each action's maintained color identity.
- Moves Old Bay bulk controls from the bottom of the GUI to a polished action strip directly below Search/Age/Sort so review actions stay near the operator's filtering controls.
- Keeps active snoozes visible in Old Bay Control Center but sorts them below live/expired stale work. Snoozed rows receive a purple Zzz ribbon showing elapsed snooze time, time remaining, and total snooze window.
- Keeps the Old Bays attention badge limited to work that needs review now; active snoozes do not inflate the alert count.
- Rebuilds the printable Old Bay Investigation List as a branded Barefoot / Builders FirstSource landscape worksheet with live/snoozed summary metrics, professional table hierarchy, review state, physical check boxes, and investigation-notes space.
- SQLite schema remains version 11; no migration or database reset is required.

## v0.337 highlights

- Multi-piece **Add Qty / Scan Remaining** controls exist only in the immediate successful scan notification. All Scans remains a read-only audit view for quantity.
- All Scans no longer shows the green-dot **Live audit data** health/status ornament in its modal header.
- The **Previously printed packing lists** heading uses a direct SVG document icon and the full badge remains offset left for the compact Rack History layout.
- Rack Overview detects and repairs the recurring partial sticky-header overlap after rack refreshes, modal close, resize, focus, and page entry instead of relying on click forwarding or invisible hit areas.
- SQLite schema remains version 11; no migration or database reset is required.

## v0.335 highlights

- Keeps **Edit Racks → Action History** heading/search/filter controls pinned in the tab while the event-result list owns the vertical scrollbar, matching the Rack History Action History interaction.
- Fixes Flag sorting at its data source by using the same visible `internalRejectCount` marker as the Scan table instead of calling a nonexistent `isInternalRejectItem()` helper. Flagged rows now reliably group first on the initial ascending click.
- Forwards `rackRouteClass` during the initial individual-rack modal open, so IT/CPU/DTC/GNV route colors are correct immediately instead of defaulting to gray until a lifecycle action refreshes the modal.
- Stops Print / Export filter controls from collapsing a deliberate selection of every detailed Route, Status, Attention, or Glass option back into Airport/All. The Create Preset builder follows the same rule.
- Reworked the formatted Excel header with dedicated logo space, a branded navy/pale-blue title area, Orders/Rows/QTY metrics, filter summary, prepared/check fields, wider business columns, alternating detail rows, and a cleaner Builders FirstSource footer.
- Preserves the Barefoot / Builders FirstSource logo's natural aspect ratio with a bounded one-cell image anchor instead of stretching it into a fixed rectangle.
- Adds horizontal print centering, repeating column headings, hidden gridlines, page numbering, and current v0.335 workbook metadata while keeping the existing offline OOXML export path.
- Advances `APPLICATION_VERSION` to 335 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.334 highlights

- Replaces the Packing List History heading badge's mask-only artwork with a direct embedded SVG so it cannot degrade into a plain blue square on affected browsers.
- Adds a few pixels of breathing room between each snapshot's paper icon and its rack/snapshot copy without changing the paper icon itself.
- Makes Scan-page **Flag** sorting use the actual visible Flag-column markers (Remake, Rush, Internal Reject, and Manual scan only) instead of process/queue text. The first click places flagged rows above rows with no flags; the second click reverses that grouping.
- Restores one clear scroll owner for Admin/Edit Racks Action History. The complete tab now scrolls, wheel input over history rows reaches that parent scroller, and the search/filter toolbar moves naturally with the history content.
- Removes generic overscroll containment from action-history lists that are not necessarily scroll owners, while retaining containment on actual Operations-modal history lists.
- Advances `APPLICATION_VERSION` to 334 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.333 highlights

- Fixes grouped rack-set editing by sending each rack's existing `oldRackCode` identity when the set editor saves. The backend now recognizes each row as an update instead of treating its unchanged rack code as a duplicate create.
- Adds reusable focus/caret preservation around dynamically rebuilt history search toolbars. Rack History and the shared Action History search controls can update results without forcing the operator to click back into the search box between keystrokes.
- Removes the obsolete duplicate `filterPackingHistoryRows()` implementation that overrode the newer grouped renderer and merely hid matching rows inside still-visible date/week shells.
- Rebuilds Packing List History search results from the filtered snapshot set before date/week grouping, so unmatched dates and weeks disappear completely. Matching weeks auto-expand while a search is active.
- Expands Packing List History indexing to include rack code/name, print date/time, delivery date, printed-by user, every Order Nr., and every Job Nr. stored in the immutable snapshot. Common date formats such as `8/17/2026`, `08/17/2026`, and `08-17-2026` are recognized client-side.
- Enriches packing-history API rows with safe searchable Order/Job summaries without returning the raw snapshot JSON to the browser.
- Polishes Packing List History with document-style snapshot icons, stronger week/day hierarchy, snapshot numbers, order/job counts, cleaner metadata cells, search-result context, and improved hover/readability treatment.
- Advances `APPLICATION_VERSION` to 333 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.332 highlights

- Carries the selected grouped rack set's exact saved accent color into the center rack workspace with a restrained gradient behind the individual rack cards.
- Restores clipping on the Rack Overview title card so its decorative upper-right circle stays inside the rounded heading boundary without changing button hit-testing.
- Removes the redundant route suffix from the individual-rack description (`10 pieces · IT` becomes `10 pieces`) because Route now owns a dedicated header cell.
- Resolves the individual-rack Route cell from the persisted rack destination first, then rack-item routes, with populated legacy/no-destination racks falling back to Indian Trail. This prevents an IT rack from intermittently appearing as neutral gray after refreshes.
- Makes route colors the final CSS owner for IT, CPU, DTC, and GNV so rack-set/material accents cannot override them.
- Normalizes historical packing-list timestamps from raw ISO values such as `2026-08-17T18:47:29+00:00` into a local `M/D/YYYY h:mm AM/PM` display.
- Rebuilds the historical packing-list preview/print as a branded document with the maintained Barefoot/Builders FirstSource print logo, structured rack metadata, improved table hierarchy, and print-safe styling.
- Polishes the current rack packing-list printout to use the same maintained print-logo asset, stronger document hierarchy, cleaner metadata cards, and a more professional table treatment.
- Advances `APPLICATION_VERSION` to 332 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.331 highlights

- Restores `sortScanItems()` after v0.329 accidentally removed it with the old per-column filter-popup helpers while `getPagedItems()` still depended on it. This fixes the blank Scan page and yellow date-switch flash caused by the resulting runtime exception.
- Keeps the intended v0.329 behavior: column headers remain click-to-sort ascending/descending with no per-column filter popup restored.
- Makes the individual-rack **Route** cell derive its color from the rack destination: IT green, CPU purple, DTC pink, and GNV teal. The rack material/set color continues to style the rack GUI itself but no longer controls the Route cell.
- Adds a regression assertion that the Scan sorting helper exists whenever the Scan render path calls it, and that route-color classes are supplied by `rackDestinationClass()`.
- Advances `APPLICATION_VERSION` to 331 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.330 highlights

- Removes the three stale `closeScanColumnFilterMenu()` event-listener references left behind when v0.329 removed the Scan column-filter popup.
- Removes the now-empty document pointer handler that belonged to the removed column-filter behavior.
- Keeps the v0.329 Scan header behavior unchanged: clicking a column header toggles ascending/descending sorting with no funnel/filter popup.
- Adds a regression assertion that the removed column-filter API cannot remain referenced by `app.js`.
- Advances `APPLICATION_VERSION` to 330 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.329 highlights

- Removes the redundant Scan-page per-column filter buttons and popup menus while keeping click-anywhere header sorting with ascending/descending toggling.
- Adds a dedicated shortened Route cell beside Rack Status in the individual-rack header and fixes lifecycle text contrast, including the On the Way state.
- Moves the multi-quantity `Add Qty` action onto the shared blue `app-primary-button` styling.
- Completes overview/modal rendering support for every icon offered by the grouped rack-set creation picker, including glass cart, pallet, dolly, crate, and warehouse icons.
- Uses the exact saved rack-set hex color as the primary visual accent instead of substituting a nearby generated hue.
- Advances `APPLICATION_VERSION` to 329 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.328 highlights

- Adds true table-wide Scan-page sorting from every maintained column header, including A→Z/Z→A text sorting and smallest→largest/largest→smallest numeric sorting.
- Adds per-column custom filters with text and numeric operators. Column filters combine with the existing status, route, glass-type, and free-text filters and appear as removable active-filter chips.
- Adds multi-piece scan controls to successful scan notifications and Last Scan whenever the source Qty is greater than one and pieces remain. Operators can add a chosen quantity or scan all remaining pieces in one action.
- Adds a Qty field immediately to the right of Item Nr. in Manual Scan. It defaults to 1 and sends the requested quantity through the same scanner validation/audit workflow.
- Extends backend scan accounting so normal, Staging, Outbound auto-stage, rack quantity, Indian Trail receive, scan-event quantity delta, and audit records use the accepted multi-piece quantity while never exceeding the line's remaining Qty.
- Fixes the recurring upper-half dead zone on **Racks History** and **Edit Racks** at its source: the sticky application-header background no longer participates in pointer hit-testing, while real header controls remain interactive. Old Rack-specific geometry nudging/click-forwarding workarounds are removed.
- Gives every individual-rack GUI a visual accent derived from its configured rack-set/icon color, or from the maintained material hue for built-in wood, steel, aluminum, mirror, truck, and other sets.
- Makes rack lifecycle status glanceable with a larger two-line status cell plus a lifecycle-colored header edge while preserving exact Rack Overview colors for Incomplete, Complete, On the Way, Received, and Empty.
- Advances `APPLICATION_VERSION` to 328 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.327 highlights

- Refines the individual-rack header lifecycle cell so **Incomplete**, **Complete**, **On the Way**, **Received**, and **Empty** use the exact same border/background/text palette as their Rack Overview status chips.
- Adds a compact lifecycle dot, adaptive sizing, stronger spacing/shadow, and responsive wrapping so the status remains readable beside long rack names and on narrower screens.
- Removes the v0.326 blanket `overscroll-behavior` rule that accidentally turned ordinary cards, headings, and non-scrollable panels into wheel dead zones.
- Limits scroll-boundary containment to true overflow owners. Normal page scrolling now continues when the pointer is over ordinary page content, while genuine nested scrollers still keep their own boundary behavior.
- Removes the broad Scan-page `[class*="scroll"]` containment selector and the non-scrollable bay-scanner-panel containment that could block document scrolling when hovered.
- Advances `APPLICATION_VERSION` to 327 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.326 highlights

- Places Global Search's latest scanned date/time on the same status row, aligned to the right of the resolved current stage/location, and gives Smart Results a contained vertical scrollbar.
- Prevents wheel/touch scroll chaining from exhausted internal GUI and results scrollers into the page behind them; all visible shared modals now participate in the central body-scroll lock.
- Keeps the Staging/Delivery Stage custom-select menu attached to its trigger during page scrolling and lowers the sticky scanner panel beneath the sticky application header.
- Adds a colored lifecycle cell immediately to the right of the individual rack name for **Incomplete**, **Complete**, **On the Way**, **Received**, and **Empty** states. Removes the duplicate green-dot health indicator and the old body-level Rack Status banner from the rack workspace.
- Repairs the **Not On The Way** button hover/focus palette so it keeps readable high-contrast text instead of inheriting the generic dark-blue hover.
- Grays rack move/clear controls when an **On the Way** rack is lifecycle-locked and shows a centered explanation when the operator clicks a blocked control. The backend now enforces the same lock for single-item moves and rack/item clears, not only move-all.
- Extends explanatory blocked-action behavior to rack/rack-set deletion prerequisites and converts non-Scan backend errors into the shared action-feedback popup instead of re-rendering the Scan page behind another workspace.
- Removes the duplicate **Clear selected rack set** button beside the rack Sort control.
- Advances `APPLICATION_VERSION` to 326 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.325 highlights

- Shortens canonical internal bay identifiers such as `T-BAY12-01` to the operator-facing label **Bay 12-01** without changing the stored bay code used by the backend, scans, or assignments.
- Shows active/current bays in the Scan-page Location column only while viewing the Indian Trail receiving stage.
- Keeps the most recent bay visible in gray after a bay assignment is cleared or cancelled so scanning glass out of a bay does not erase its physical-location history.
- Shows rack/truck locations instead of bay locations on Staging and Outbound. Once the piece has been received downstream, that rack remains visible in gray as prior transportation history rather than changing to a generic **Received** badge.
- Applies the same stage-aware compact Location behavior to Last Scan and Recent Scans.
- Shortens rack destination/route display labels to **IT**, **CPU**, **DTC**, and **GNV** while preserving the existing canonical stored destination values.
- Advances `APPLICATION_VERSION` to 325 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.324 highlights

- Treats an Admin-approved superseded-order removal as a durable **source-order** decision. A later SQL fingerprint/item change on that same removed order no longer silently resets the approval to Pending.
- Removes every live source-owned row for the approved A+W order by immutable source lineage, even if an operator previously changed the visible Order Nr. or Item Nr.
- Soft-retires superseded rows from live delivery lists, rack assignments, and bay assignments instead of hard-deleting history-linked records, preserving scan/machine/audit history.
- Publishes order-level superseded exclusions to the SQL exporter so future regenerated Excel workbooks omit the entire approved old order, including newly appearing items on that same source order.
- Persists field-level manual edits for source-owned rows by original A+W Order/Item identity. Later workbook imports update untouched source fields but keep the operator's explicitly edited Order Nr., Item Nr., Qty, dimensions, customer, route, Job Nr., and product.
- Gives a manual route override higher priority than Job Nr. hints and Customer Route Rules, preventing an IT→CPU edit from being re-created in Indian Trail during the next automated import.
- Writes source-owned manual overrides into the shared persistent-decision file and applies them during SQL workbook generation, so regenerated workbooks reflect supported manual edits rather than immediately restoring the raw SQL values.
- Stores the original A+W source Order/Item in hidden workbook columns so visible manual Order Nr./Item Nr. edits still reconcile to the same source row on the next import instead of creating a duplicate identity.
- Advances the SQL workbook integrity marker to `v324-ooxml-2`, forcing maintained automation to rebuild older workbook copies into the source-lineage-aware format before treating them as current.
- Aligns folder-import drift checks and end-to-end workbook verification with the same persistent-decision preparation used by the real importer, avoiding false IT/CPU stage mismatches after manual routing changes.
- Advances `APPLICATION_VERSION` to 324 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.323 highlights

- Expands the browser-controlled runtime synchronization from four run-time reconciliation files to the complete maintained scheduler/runtime dependency set, including the install/remove/status/verification PowerShell scripts and scanner compatibility helpers.
- Self-heals a partially installed local runtime under `C:\DeliveryListAutomation` before installing or removing the Windows schedule.
- Materializes the current saved automation settings to the stable installed `Scripts\sql-export.config.json` path without resetting the selected network folder, automation mode, notification choices, or schedule values.
- Creates or refreshes `Run-Incremental.cmd` and `Run-Full.cmd` automatically so Task Scheduler never fails immediately after the missing installer script is repaired.
- Reuses the Python interpreter running the scanner when a floor-computer config has no Python path yet, allowing the folder-import compatibility preflight to run without requiring A+W SQL access.
- Keeps `ScheduleEnabled` aligned with the real Windows task state if installation fails; it is marked enabled only after the installer returns successfully.
- Preserves the folder-import-only preflight, which validates network-folder read access and scanner compatibility without querying A+W SQL.
- Advances `APPLICATION_VERSION` to 323 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.322 highlights

- Restores vertical scrolling to the Automated DL Import **Run Now**, **Schedule**, and **Status** tabs so long content and bottom controls remain reachable at normal and reduced viewport heights.
- Keeps the automation modal itself contained inside the viewport instead of allowing the whole dialog to spill beyond its frame.
- Preserves the existing **Import History** layout, where only the history results area scrolls and its filters/header/footer remain fixed.
- Uses one owning desktop rule instead of adding a competing bottom-of-file override, reducing future cascade conflicts.
- Advances `APPLICATION_VERSION` to 322 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.321 highlights

- Makes Rack Overview lifecycle pills content-sized instead of grid-sized and pins each reset action to the lower-right so **Incomplete**, **Complete**, and **On the Way** never rearrange the card.
- Stops startup bay seeding from overwriting saved display names, grouped-set names, policies, capacity, visibility, and layout values with the bundled base map.
- Treats legacy synthetic-bay cleanup and built-in role permissions as bootstrap-only startup work so saved Admin visibility and role-permission changes remain authoritative after restart.
- Adds a large **PLACE THIS ORDER IN / BAY ##** destination block to successful Indian Trail scan confirmations.
- Adds a prominent Current Bay block and explicit **Job Nr.** to Last Scan, plus Bay and Job Nr. information in Recent Scans.
- Treats Manual Bay as a one-scan override: after a successful manual receive, the scanner automatically returns to **Auto** bay assignment.
- Shows the latest scan date/time directly below the resolved current stage/location in Global Search.
- Hides occupied bays from new manual bay choices and enforces the same safety rule server-side so one physical bay cannot contain different Order Nr. values.
- Changes Indian Trail bay grouping from Job Nr. to Order Nr. so different orders sharing one job number cannot be automatically combined into one bay.
- Advances `APPLICATION_VERSION` to 321 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.320 highlights

- Presents the historical `T` rack consistently as **Truck 1** and numbered truck racks as **Truck N** in locations, rack selectors, Rack Manager, Global Search, scan confirmations, and in-transit data.
- Separates **No Rack** from Truck 1 completely in maintained input normalization; No Rack remains the explicit blank-location selector and legacy `NORACK` no longer resolves to Truck 1.
- Defaults Staging to the explicit **No Rack** choice instead of Truck 1 and disables Complete/On-the-Way racks as staging destinations. If a selected rack becomes locked, the stale selection is cleared before another scan.
- Adds backend lifecycle validation before Staging scan quantity or rack assignments are mutated, preventing pieces from being loaded or manually moved onto a Complete/On-the-Way rack even when a browser has stale state.
- Applies the same open-rack requirement to rack moves, manual rack recovery, and outbound transportation overrides so the browser and API enforce one rule.
- Gives the Manage Bay Items left order/item workspace a dedicated vertical scrollbar with stationary filters and non-shrinking cards.
- Advances `APPLICATION_VERSION` to 320 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.319 highlights

- Rebalances the Manage Bay Items workspace so the left-side job/order list has substantially more usable width instead of squeezing exact-item information into tiny clipped rows.
- Reflows exact item cards into a readable two-line layout with full Order/Item, glass/product, size, grouped bay location, and status information.
- Makes the fixed Bay Map scanner footer-aware: as the application footer enters the viewport, the scanner stops above it instead of scrolling over the footer.
- Changes the Bay Scanner **pieces in transit** value to full white text for stronger contrast.
- Verified that Old Bays, Rush, Edit Bays, and Manage Items action-history formatting already includes Job Nr./Order Nr./Item Nr. when the recorded audit payload contains that work identity, so no duplicate history implementation was added.
- Advances `APPLICATION_VERSION` to 319 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.318 highlights

- Adds the quiet outline-circle header treatment to Old Bay Control Center and the Bay Map scanner panel.
- Lets Old Bays rows be selected from the whole non-interactive order card surface instead of requiring the small checkbox target.
- Rebuilds Current Priority Work so expanded Rush details stay above their card outline and clearly show original/new delivery dates, marked time, marked-by user, bay, item, glass information, handling, and reason.
- Shows grouped bay-set names with exact bay locations in Manage Bay Items and adds whole-job plus exact-item multi-selection with Select All/Clear Selection controls.
- Makes Move/Clear act on the selected exact assignments, allowing sibling items from one job to be manually split across different bays without a schema change.
- Updates Selected Bay job details to show where sibling items are actually located when one item is in the selected bay and another is in a different grouped set/bay.
- Enriches Old Bays, Rush, Edit Bays, and Manage Items action-history details with job/order/item, old/new bay, policy, priority-date, and related context.
- Advances `APPLICATION_VERSION` to 318 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.317 highlights

- Counts **Pieces On The Way** across every Indian Trail rack currently marked In Transit, even when that rack belongs to a delivery date other than today.
- Keeps today's Outbound sent, Indian Trail received, and dual progress meters date-specific; all-date physical transit no longer changes those daily progress counts.
- Adds compact **Select All** and **Clear All** buttons to Edit Bays and lets users toggle a bay by clicking the non-form surface of the entire bay row instead of having to hit only the checkbox.
- Keeps individual checkboxes available as a precise selection affordance and synchronizes row highlight, checkbox state, selected count, and Apply To Selected availability.
- Moves Location Corrections guidance into a compact top line and prevents the All Bay Scans grid from stretching short content vertically when only a few scan records exist.
- Advances `APPLICATION_VERSION` to 317 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.316 highlights

- Counts Indian Trail pieces on the way from active rack assignments on departed racks, even when the source delivery-list copy has since been superseded or soft-deleted by an update.
- Subtracts Indian Trail receiving scans once per Order Nr./Item Nr. before allocating the remaining physical quantity across racks, preventing received quantities from being subtracted once per rack.
- Adds Select All and per-bay checkboxes to Edit Bays plus bulk Category, Capacity, and Assign Behavior controls with the existing progress feedback while selected bays are updated.
- Makes **Physical bay scan history** the actual All Bay Scans dialog title, with **Indian Trail activity archive** as the eyebrow and the existing explanatory sentence in the modal header.
- Replaces the oversized duplicate history hero with a compact retained/scan/page strip and compresses the Location Corrections guidance into a single low-profile row.
- Advances `APPLICATION_VERSION` to 316 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.315 highlights

- Reuses the maintained rack-set icon library inside the In-Transit Manifest, including custom A-frame glass cart, pallet, dolly, crate, warehouse, material, and truck artwork.
- Carries each rack set's saved icon color into the In-Transit rack marker instead of falling back to a plain blue circular marker.
- Displays delivery dates inside In-Transit glass/order rows as compact `M/D/YYYY` values such as `8/14/2026`.
- Uses the same compact numeric delivery date in individual Rack contents so rack detail and In-Transit presentation stay consistent.
- Advances `APPLICATION_VERSION` to 315 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.314 highlights

- Re-checks Rack Overview heading geometry after asynchronous rack refreshes and forwards clicks that land inside the visible Rack History/Edit Racks button rectangles even if a stale transparent shell layer wins browser hit testing.
- Keeps the In-Transit Manifest all-date so every rack currently marked In Transit for Indian Trail is visible, while Bay Map Outbound/Indian Trail counts and progress remain tied strictly to today's delivery date.
- Removes the temporary Test 100% sound action from In-Transit and adds the same restrained decorative header circle used by the polished control-center dialogs.
- Adds Delivery Date to in-transit rows so mixed-date racks remain understandable.
- Applies the shared blue primary-button treatment to maintained Edit Bays save/create actions.
- Shows live bay-by-bay progress while a grouped bay set rename/policy update is being written instead of silently waiting through sequential updates.
- Advances `APPLICATION_VERSION` to 314 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

## v0.313 highlights

- Resets page scrolling only after the destination page becomes visible, eliminating the navigation-dependent sticky-header overlap that made the upper part of Rack History/Edit Racks unclickable.
- Uses the real 36-pixel Rack History/Edit Racks button surfaces instead of an oversized pseudo-element hit area.
- Narrows Delivery List Update Preview to a maximum 1100-pixel desktop workspace and reduces modal/body/card spacing.
- Removes preview filters, search, result count, and redundant New/Updated/Removed metric cards.
- Keeps Route dropdowns, polished Order headers, Customer/Route context, exact glass colors, glass sizes, QTY, change states, and before/after details.
- Advances `APPLICATION_VERSION` to 313 while preserving SQLite schema version 11.

**## Install v0.312**

1. Stop the Delivery List Scanner if it is running.
2. Extract the v0.312 changed-files ZIP directly into `C:\Users\brandon.m.smith\My Projects\Delivery List Scanning Project\` and replace the included files.
3. Preserve the existing `data` folder and database files.
4. Start the scanner manually with `py -3 server.py`.
5. Hard-refresh the browser (`Ctrl+F5`) once so the v0.312 CSS/JavaScript cache keys are loaded.

No database migration or reset is included. `CURRENT_SCHEMA_VERSION` remains **11**.

## v0.312 highlights

- Replaces the oversized grouped-bay occupied/total/meter block with a compact `3/32` capacity pill that fits the Physical Bay group card and keeps only the live occupied number color-coded.
- Restores Rack Overview route/destination pills to the upper-right corner while retaining the current rack-history scrolling and action-button hitbox fixes.
- Adds a dedicated **Glass colors** library to Admin -> Lookup Manager using the existing generic lookup table, so no schema migration is required.
- Builds the Glass Colors library from the same known glass-type vocabulary used by glass costs and active delivery-list products, including clear thicknesses, mirrors, antique mirrors, and newly discovered products.
- Lets administrators select and save an exact color for each glass type; unconfigured glass types receive stable distinct automatic colors until overridden.
- Centralizes glass-color resolution in shared browser helpers and applies it to Delivery List Update Preview item borders, tinting, and glass indicators so future glass-aware interfaces can reuse the same palette.
- Advances `APPLICATION_VERSION` to 312 while preserving SQLite schema version 11.

## v0.311 highlights

- Fixes whole-rack content transfers by removing references to obsolete rack lifecycle `*_by` columns while preserving timestamp resets and transfer auditing.
- Gives Packing List History and All Racks History their own bounded vertical scroll areas inside the Rack History control center.
- Moves the Rack route/destination pill to the upper-left, enlarges the complete Rack History/Edit Racks click target, and gives Scan Progress one percentage point from Route so compact stage progress stays on one line.
- Simplifies Delivery List Update Preview to Route dropdowns containing polished static Order cards and flat item rows; each item shows exact glass type, glass size, QTY, and change state.
- Assigns a stable distinct visual hue to every exact glass/product label so individual clear thicknesses, mirrors, and antique-mirror products are visually distinguishable.
- Preserves operator-edited Physical Bay display names when the bootstrap JSON layout is re-seeded during server startup.
- Replaces the `3/30 used` group fraction with an occupied/total summary and utilization meter that transitions from green through orange to red as the set fills.
- Advances `APPLICATION_VERSION` to 311 while preserving SQLite schema version 11.

## v0.310 highlights

- Restores a compact **AUTO / MAN / MIX / BLK** policy chip to the upper-left of each Physical Bay grouped set without bringing back the redundant large status block.
- Adds the same small `!` indicator to each individual bay that contributes to the grouped attention count, with a tooltip describing the attention reason.
- Separates the occupied value from the total-capacity text and transitions utilization color from green through orange toward red as a group fills.
- Keeps Rack creation and sticky Scan Stage behavior from v0.309 unchanged.
- Advances `APPLICATION_VERSION` to 310 while preserving SQLite schema version 11.

## v0.309 highlights

- Routes all new rack and rack-set inserts through one compatibility-safe rack creator that explicitly supplies lifecycle values and fills any legacy SQLite `NOT NULL`/no-default rack columns with neutral values.
- Raises the complete Racks History and Edit Racks button surfaces above decorative heading layers so their full visible area is clickable.
- Keeps the sticky Scan Stage custom dropdown interactive after page scrolling by preserving/repositioning Scan context menus instead of closing them on document scroll.
- Removes the duplicated generated `used` suffix from Physical Bay group counts.
- Colors the `used` count continuously from green through orange toward red as a bay group approaches full utilization.
- Replaces the wide Bay group attention message with a small `!` + count badge and tooltip/accessibility label.
- Advances `APPLICATION_VERSION` to 309 while preserving SQLite schema version 11.

## v0.308 highlights

- Marks every currently existing stage-copy update notice for the delivery date reviewed for the signed-in user when Staging or Outbound is reviewed; route-specific review remains isolated.
- Repairs Add Rack Set on databases where rack lifecycle columns such as `completed_at` are `NOT NULL` by writing explicit empty lifecycle values instead of `NULL` or relying on legacy defaults.
- Shows the existing racks, names, and lifecycle states for the selected rack set while adding an individual rack, while keeping duplicate code/name validation.
- Makes Racks History use a dedicated scrollable modal-body row, keeps the page summary compact, and allows expanded weeks to remain fully reachable.
- Adds a prominent Complete / Incomplete / On the way lifecycle banner inside each individual Rack details workspace above its order contents.
- Makes Rack Manager groups independent full-width collapsible rows so expanding Wood or Coral cannot move another rack set to a different grid row.
- Reworks Delivery List Update Preview so a specifically selected route opens automatically, whole-list/Airport previews keep route groups collapsed, orders are static headers rather than dropdowns, and route totals read like `23 New Lines | 26 New QTY`.
- Removes redundant Physical Bay Map group status/open indicators, retaining the concise used count plus blocked/attention only when needed.
- Raises the sticky Scan panel above overlapping page content so Stage remains interactive while scrolled and hardens RM flag styling against the stray black-dot artifact.
- Advances `APPLICATION_VERSION` to 308 while preserving SQLite schema version 11.

## v0.307 highlights

- Staging/Outbound review now clears the matching automatic-import occurrence across downstream active stages for only the signed-in user, immediately clears those Stage markers, and then verifies them from the backend.
- Rack-set creation validates set names and generated rack codes before submit and again in the backend transaction, with the exact error kept visible inside the form instead of only flashing a generic error.
- Individual rack creation prevents duplicate rack codes and duplicate display names.
- Packing List History keeps its `print days · snapshots` summary compact instead of stretching into unused modal height.
- Edit Racks uses one full-width collapsible set per row with Truck pinned first, so opening Wood/Coral no longer distorts a neighboring grid row.
- Rack Overview labels loaded open racks as **Incomplete** and adds a stronger lifecycle indicator for Incomplete, Complete, On the way, Received, and Empty.
- Preserves the v0.306 mobile interface as-is and keeps SQLite schema version 11.

## v0.306 highlights

- Presents scanner controls, recent feedback, summary, filters, paging, and delivery-list cards as one continuous mobile Scan page with no bottom sub-navigation.
- Adds Job Nr., explicit scanned/total quantity, and complete, partial, or not-scanned status to every handheld delivery-list card.
- Converts Scan and Bay Map All Scans histories into labeled audit cards on phones while retaining the desktop tables.
- Repairs compact header icons, sidebar branding, Home progress geometry, expanded physical Bay groups, and maintained mobile dialog shells.
- Reflows Print / Export and preset controls into one internally scrollable, touch-first workspace with an accessible close action.

## v0.305 highlights

- Added a final `static/css/mobile.css` ownership layer loaded after every page stylesheet so compact-device fixes do not change desktop rendering.
- Reworked compact navigation and the main page/dialog layouts for TC22-class handheld use with safe-area handling and touch-sized controls.
- Preserved SQLite schema version 11 with no database migration.

## v0.304 highlights

- Restricts the full-screen New Rush Submitted alert to genuine Rush notifications created by the operator Priority Work workflow; import results and Superseded Order Review remain in the notification center instead of impersonating a Rush.
- Adds defensive backend and browser filtering so automation/system identities cannot enter the Rush popup queue.
- Removes imported `Rush` / standalone `SDI` tokens from source-owned line state; genuine operator Rush state is restored only from the existing Priority Work audit history.
- Adds a TC22-first compact-device layout at 760px and below, with an extra narrow 430px pass for phone-class CSS viewports.
- Reduces compact header/sidebar overhead, adds safe-area-aware bottom navigation, and standardizes touch-friendly controls without changing desktop sizing.
- Reworks Home, Scan, Statistics, Racks, Bay Map, Reject Tracking, Admin, and Print / Export for single-column handheld use, readable typography, horizontal table containment, and full-height mobile control centers.
- Keeps the Scan workflow the highest-density handheld surface with larger barcode input, stacked Station/Date/Stage context, mobile-friendly rack/bay controls, and compact review/Rush dialogs.
- Advanced `APPLICATION_VERSION` to 304 while preserving `CURRENT_SCHEMA_VERSION = 11`; no database migration or reset is included.

**## v0.303 highlights**

\- Kept the selected delivery date synchronized with the active delivery-list catalog so removed or restored lists cannot leave the Scan date selector blank.
\- Refreshes the replacement active list immediately when an import changes which list is active, restoring the correct stages without a page reload.
\- Counts import changes from the canonical physical list copy rather than adding Staging, Outbound, and destination-stage copies together.
\- Distinguishes changed rows from physical piece quantities in import previews and treats restored or newly added route stages as updates rather than brand-new delivery dates.
\- Preserves all route rules; Indian Trail rows remain Indian Trail unless an explicit source route or configured customer route rule says otherwise.
\- Advanced \`APPLICATION\_VERSION\` to 303 while preserving \`CURRENT\_SCHEMA\_VERSION = 11\`; no database migration or reset is included.

**## v0.302 highlights**

\- Collapsed the oversized Packing List History page-count strip into one compact line such as **\*\*1-5 of 5 print days · 6 snapshots\*\***.
\- Forced **\*\*Preview\*\*** and **\*\*Print Snapshot\*\*** to remain beside each other on each snapshot row.
\- Raised the snapshot preview into a dedicated top-level visual layer so it always appears above Packing List History.
\- Removed the redundant footer **\*\*Close\*\*** button from Snapshot Preview while retaining the top-right X and Escape/backdrop close behavior.
\- Replaced the generic Glass Cart visual with a recognizable **\*\*A-frame glass cart\*\*** icon while retaining the existing saved \`glasscart\` value for compatibility.
\- Restored a very small pencil shortcut in the top-right of each physical Bay Map group; clicking it opens that exact group in the maintained Edit Bays GUI.
\- Preserved Main's Packing List History, statistics workspace, formatted print/export, rack visuals, scan review, and Bay Map improvements.
\- Added authoritative import reconciliation that retires removed source rows logically while keeping their audit history.
\- Added complete same-day import history, route-accurate update preview, source exclusions, and exact added/removed piece totals.
\- Added administrator review for likely superseded A+W orders, including selectable exact-order removal and durable decision history.
\- Advanced \`APPLICATION\_VERSION\` to 302 and \`CURRENT\_SCHEMA\_VERSION\` to 11; migrations are additive and do not reset the production database.

**## v0.269 highlights**

\- Reworded Scan update messaging to distinguish a **\*\*New stage\*\*** from a **\*\*Delivery list updated\*\*** with **\*\*new orders\*\***; Scan attention filtering now says **\*\*New Orders\*\*** instead of describing orders as updated.
\- Strengthened the always-visible Scan review bar with a clearer border, accent, and NEW STAGE / NEW ORDERS label so pending review work is harder to miss.
\- Set the Scan new-order/stage review popup to **\*\*10 seconds\*\*** with matching countdown/progress timing.
\- Preserved the most recent rack on a scan line after that rack is cleared/scanned out, displaying the former rack as a muted **\*\*prior\*\*** location while active rack/bay/received locations still take precedence.
\- Standardized shared blue buttons at a consistent **\*\*13px\*\*** font size and a slightly shorter **\*\*38px\*\*** minimum height; the Manual Scan Submit button now uses the shared primary-button component.
\- Added a rack-set icon library and editable icon color when creating or editing a rack set. Selections persist through existing \`system\_metadata\` and appear on Rack Overview cards and Rack Manager group headers.
\- Added a visible **\*\*20-second\*\*** Old Bay review countdown and matching timeout progress bar.
\- Advanced \`APPLICATION\_VERSION\` to 269 while preserving \`CURRENT\_SCHEMA\_VERSION = 5\`; no migration or database reset is included.

**## v0.266 highlights**

\- Made New/Updated flags authoritative to the newest update batch for each stage so superseded unreviewed notices no longer keep stale \`!\` markers or review notifications visible.
\- Changed Staging/Outbound review to acknowledge the same current update batch across every active route/stage for that delivery date, while IT, CPU, DTC, and Greenville remain stage-specific and per-user.
\- Reduced the New/Updated review notification lifetime from 15 seconds to 7.5 seconds.
\- Kept Stage and Delivery Date popup menus aligned to their compact trigger width so \`!\` indicators do not cause oversized dropdowns.
\- Increased Scan panel Station, Stage, and Delivery Date value text slightly while expanding the label budget for Indian Trail and review-marked dates.
\- Advanced \`APPLICATION\_VERSION\` to 266 while preserving \`CURRENT\_SCHEMA\_VERSION = 5\`; no migration or database reset is included.

**## v0.265 highlights**

\- Expanded the Scan header label budget so Indian Trail and delivery dates with review markers remain fully visible.
\- Added per-user \`!\` review markers to the Stage selector as well as the Delivery Date selector.
\- Changed date marker aggregation to de-duplicate the same order/item copied across multiple stages.
\- Made Airport Rd review order-aware: reviewing Staging or Outbound marks the exact reviewed update occurrence read across downstream copies of those same order/items for that user.
\- Kept Indian Trail, CPU, DTC, and Greenville review independent so reviewing one route does not clear another route.
\- Moved each Bay Map grouped-set Edit icon to the top-right corner of the group header.
\- Advanced \`APPLICATION\_VERSION\` to 265 while preserving \`CURRENT\_SCHEMA\_VERSION = 5\`; no migration or database reset is included.

**## v0.263 highlights**

\- Restored readable Statistics typography after the prior compact pass made labels, controls, table text, legends, and chart details too small.
\- Reorganized breakage tables into clearer accountability blocks for machine/glass/reason review.
\- Grouped pieces, SQFT, cost, and reject count together instead of spreading them across many narrow columns.
\- Improved coverage/status presentation and selected-row drilldowns while preserving custom ranges and breakage controls.
\- Advanced \`APPLICATION\_VERSION\` to 263 while preserving \`CURRENT\_SCHEMA\_VERSION = 5\`; no database migration or database change is included.

**## v0.262 highlights**

\- Consolidated the previous machine piece/SQFT/cost datasets into one **\*\*Machine breakage overview\*\*** with a Chart Unit selector for Square feet, Pieces, or Cost.
\- Consolidated glass breakage into one **\*\*Glass type breakage overview\*\*** with the same switchable ranking measure.
\- Added **\*\*Reject reasons by machine\*\***, showing how many reject events each reason generated for each machine plus pieces, SQFT, cost, and affected glass types.
\- Added machine drilldowns for top reject reasons and broken glass types, and glass-type drilldowns for responsible machines and reject reasons.
\- Added a polished Statistics custom-date calendar using the established Print / Export two-month range-picker visual language. A custom range overrides the preset range until another preset is selected.
\- Limited the **\*\*External remakes\*\*** switch to breakage reporting and restyled it as a compact web-app toggle. External remakes remain separate from real machine accountability.
\- Expanded combined breakage table rows so pieces, SQFT, material cost, reject-event count, related machines/glass, top reasons, and data coverage can be reviewed without changing datasets.
\- Updated the Statistics PDF with machine reject counts, broken glass context, and top reject reasons while keeping the report focused on operationally useful information.
\- Preserved the default Top 10 / Show more data behavior and the compact v0.260 chart geometry.
\- Advanced \`APPLICATION\_VERSION\` to 262 while preserving \`CURRENT\_SCHEMA\_VERSION = 5\`; no schema migration, database reset, or migration-registry change is included.

**## v0.261 highlights**

\- Added **\*\*Glass costs\*\*** as a fourth library inside Admin → Lookup Manager.
\- Displays all built-in glass rates plus newly discovered unpriced glass products in one searchable list.
\- Administrators can edit an existing rate or add a rate for a new glass type using **\*\*Cost per SQFT\*\***.
\- Saved rates persist through the existing \`admin\_lookup\_values\` table; no schema change or migration is required.
\- Statistics breakage calculations use the effective administrator-maintained price map, with the built-in rates retained as fallbacks.
\- Lookup Manager identifies default, discovered, and manually maintained pricing sources and highlights glass with no configured cost.
\- Preserved \`CURRENT\_SCHEMA\_VERSION = 5\`; no migration was introduced.

**## v0.260 highlights**

\- Opens Statistics on **\*\*Glass type quantity\*\*** in the donut/circle view with a default display limit of 10 categories.
\- Adds **\*\*Show more data\*\*** below the main analytics region; each click increases the display limit before eventually exposing all matching categories.
\- Reduces main chart/table geometry and typography by roughly one third so substantially more data fits in the same workspace.
\- Uses compact workflow labels in Statistics: Staging, Outbound, Inbound, CPU, Greenville, and DTC.
\- Adds internal reject datasets by machine and glass type for piece count, SQFT, and estimated material cost.
\- Makes breakage table view show pieces, SQFT, estimated cost, data coverage, and source together so machine accountability can be reviewed without switching measures.
\- Calculates piece and SQFT breakage percentages against estimated total produced glass and adds an explicit toggle to include or exclude external remakes.
\- Uses the maintained per-SQFT glass pricing supplied for Clear, UltraClear, Mirror, and Antique Mirror products; unknown prices and missing dimensions are reported instead of silently estimated.
\- Replaces the prior Statistics PDF clutter with delivery progress, breakage KPIs, workflow progress, machine breakage, glass-type breakage, and calculation coverage notes.
\- Keeps external remakes separate from production-machine accountability even when they are included in the overall breakage percentage.
\- Preserves \`CURRENT\_SCHEMA\_VERSION = 5\`; no migration, database reset, or schema-contract change is part of this release.

**## v0.253 highlights**

\- Replaces the repeated dashboard totals with four priority cards: delivery completion, open pieces, on-time completion, and remake pieces.
\- Keeps glass-mix visualization on the dashboard while improving hierarchy, legend readability, summary context, responsive behavior, and empty states.
\- Rebuilds stage cards around completion, scanned pieces, open pieces, and list counts without repeating top-level totals.
\- Consolidates scan exceptions, manual scans, bay overrides, rack activity, bay activity, manual edits, and top-operator activity into one operational-health section.
\- Removes the obsolete duplicate snapshot/remake containers and eliminates the second redundant statistics render pass.
\- Modernizes the full chart explorer and replaces its repeated dashboard KPIs with chart-specific category, total, average, and highest-value summaries.
\- Preserves all existing chart metrics, filters, sorting, limits, bar/donut views, and PDF reporting. No new migration was intended; v0.255 keeps the maintained schema contract at version 5.

**## Install v0.232**

1. Start from the maintained v0.231 project.
2. Extract the v0.232 changed-files ZIP directly into the current project folder.
3. Preserve the existing \`data\` folder and database files.
4. Restart the scanner server and refresh the browser with \`Ctrl+F5\`.

No database migration or separate setup script is required. v0.232 keeps schema version 5.

**## v0.232 highlights**

\- Removes the Description field from Create Preset and keeps Preset Name beside the personal-default toggle.
\- Increases the desktop modal height to 860 pixels while retaining safe scrolling only for shorter or narrower browser windows.
\- Expands Glass Types into side-by-side Annealed, Tempered, and Mirror panels on desktop.
\- Restores subtle route-specific tints and restrained blue, green, and purple glass-family colors.
\- Keeps Status and Attention controls neutral so selected filters remain clear without overwhelming the workspace.
\- Preserves Preset Summary, Print Options, bottom-right Save Preset actions, Lookup Manager values, and schema version 5.

**## Install v0.231**

1. Start from the maintained v0.230 project.
2. Extract the v0.231 changed-files ZIP directly into the current project folder.
3. Preserve the existing \`data\` folder and database files.
4. Restart the scanner server and refresh the browser with \`Ctrl+F5\`.

No database migration or separate setup script is required. v0.231 keeps schema version 5.

**## v0.231 highlights**

\- Organizes Create Preset glass types into Annealed, Tempered, and Mirror sections while preserving exact Lookup Manager values.
\- Replaces category-specific button colors with one neutral control treatment.
\- Makes selected filters obvious through a stronger border, soft shared background, check badge, and selected-count pill.
\- Moves Print Options directly below Preset Summary in the right column.
\- Anchors Save Preset actions at the bottom-right of the desktop workspace.
\- Shortens instructional text and keeps the responsive tablet/mobile stacking behavior.
\- Consolidates the final preset CSS ownership layer instead of stacking another duplicate override block.
\- Preserves schema version 5.

**## Install v0.230**

1. Start from the maintained v0.229 project.
2. Extract the v0.230 changed-files ZIP directly into the current project folder.
3. Preserve the existing \`data\` folder and database files.
4. Restart the scanner server and refresh the browser with \`Ctrl+F5\`.

No database migration or separate setup script is required. v0.230 keeps schema version 5.

**## v0.230 highlights**

\- Rebuilds the Create Preset workspace rows around content height instead of forcing the main cards into a fixed-height grid row.
\- Prevents Print Options, Preset Summary, Actions, status messages, and the information footer from occupying the same vertical space.
\- Keeps the compact centered workspace and uses internal scrolling only when the browser is too short to show every card.
\- Replaces saturated selected filter fills with soft tinted backgrounds, stronger borders, readable dark text, and retained check marks.
\- Softens action, orientation, card-accent, and backdrop colors while preserving clear hierarchy and route/category identity.
\- Preserves responsive stacking, Lookup Manager glass types, live summary, personal defaults, and Save/Apply behavior.
\- Preserves schema version 5.

**## Install v0.229**

1. Start from the maintained v0.228 project.
2. Extract the v0.229 changed-files ZIP directly into the current project folder.
3. Preserve the existing \`data\` folder and database files.
4. Restart the scanner server and refresh the browser with \`Ctrl+F5\`.

No database migration or separate setup script is required. v0.229 keeps schema version 5.

**## v0.229 highlights**

\- Reduces the desktop Create Preset workspace to a centered maximum of 1240 × 780 pixels while retaining responsive full-screen behavior on smaller displays.
\- Increases labels, inputs, filter choices, summaries, and action-button typography without increasing the overall modal footprint.
\- Carries the Print / Export route, status, attention, All-choice, Mirror, Tempered, and Annealed gradients into Create Preset.
\- Adds stronger card hierarchy, section accent rails, polished shadows, and the maintained Print / Export blue workspace treatment.
\- Keeps the v0.228 viewport repair, internal scrolling, Lookup Manager glass library, live summary, personal default, and Save/Apply behavior.
\- Preserves schema version 5.

**## Install v0.228**

1. Start from the maintained v0.227 project.
2. Extract the v0.228 changed-files ZIP directly into the current project folder.
3. Preserve the existing \`data\` folder and database files.
4. Restart the scanner server and refresh the browser with \`Ctrl+F5\`.

No database migration or separate setup script is required. v0.228 keeps schema version 5.

**## v0.228 highlights**

\- Removes the legacy centered-modal transform that shifted the full-screen preset workspace beyond the top-left edge.
\- Gives the v0.228 modal and backdrop final fixed-position ownership so legacy preset classes cannot move the workspace.
\- Keeps a consistent 12px desktop viewport inset and a 5px mobile inset.
\- Preserves the complete v0.227 preset-control-center design while making its workspace internally scrollable.
\- Resets the preset workspace to the top whenever it opens and focuses the name field without moving the page.
\- Adds compact-height adjustments for shorter desktop displays.
\- Preserves schema version 5 and all v0.227 preset behavior.

**## Install v0.227**

1. Start from the maintained v0.226 project.
2. Extract the v0.227 changed-files ZIP directly into the current project folder.
3. Preserve the existing \`data\` folder and database files.
4. Restart the scanner server and refresh the browser with \`Ctrl+F5\`.

No database migration or separate setup script is required. v0.227 keeps schema version 5.

**## v0.227 highlights**

\- Uses a complete red gradient and exclamation indicator when Remakes, Rushes, or Internal Rejects contain matching work.
\- Uses a complete green gradient and check indicator when each of those attention categories is clear.
\- Replaces the step-based Create Preset screen with a full preset control center modeled on the supplied reference.
\- Adds Preset Details with name, description, and an optional personal-default toggle.
\- Keeps Default Filters, Print Options, Preset Summary, and Actions visible in one organized workspace.
\- Removes Visibility and Preview from Create Preset as requested.
\- Supports Save Preset and Save & Apply as separate actions.
\- Preserves Lookup Manager glass types, automatic All-choice collapsing, grouped newest-first delivery dates, and schema version 5.

**## Install v0.226**

1. Start from the maintained v0.225 project.
2. Extract the v0.226 changed-files ZIP directly into the current project folder.
3. Preserve the existing \`data\` folder and database files.
4. Restart the scanner server and refresh the browser with \`Ctrl+F5\`.

No database migration or separate setup script is required. v0.226 keeps schema version 5.

**## v0.226 highlights**

\- Automatically collapses every available Route selection back to Airport, the maintained all-routes choice.
\- Automatically collapses complete Glass, Status, and Attention detail selections back to All Glass, All Status, or All Attention.
\- Applies the same collapse behavior inside Create Preset.
\- Orders grouped delivery-date weeks and their dates from newest/future to oldest.
\- Restores the v0.224 two-column, step-guided Create Preset layout while preserving Lookup Manager glass values and fast loading.
\- Enlarges glass-category quantity totals, changes Tempered styling from orange to green, and lengthens the Checked By write-in line.
\- Preserves incremental two-week date-history loading, custom ranges, print geometry, and schema version 5.

**## Install v0.225**

1. Start from the maintained v0.224 project.
2. Extract the v0.225 changed-files ZIP directly into the current project folder.
3. Preserve the existing \`data\` folder and database files.
4. Restart the scanner server and refresh the browser with \`Ctrl+F5\`.

No database migration or separate setup script is required. v0.225 keeps schema version 5.

**## v0.225 highlights**

\- Reduces Landscape continuation pages from 29 to 28 logical rows while leaving the first Landscape page at 27.
\- Replaces the step-based Create Preset layout with one continuous name, filter, glass-library, and output workspace.
\- Groups Delivery Date choices under visual Monday-Sunday week headings.
\- Initially renders the rolling previous two weeks together with every currently available future delivery date.
\- Loads two additional historical weeks whenever the user reaches the bottom of the date menu, with an explicit Load 2 older weeks control as a keyboard/mouse fallback.
\- Performs the date-history expansion entirely in memory, without additional list-detail requests or recurring work.
\- Preserves custom date ranges, system/user presets, shared preview/print styling, idle-state recovery, and schema version 5.

**## Install v0.224**

1. Start from the maintained v0.223 project.
2. Extract the v0.224 changed-files ZIP directly into the current project folder.
3. Preserve the existing \`data\` folder and database files.
4. Restart the scanner server and refresh the browser with \`Ctrl+F5\`.

No database migration or separate setup script is required. v0.224 keeps schema version 5.

**## v0.224 highlights**

\- Grays out and disables zero-count Route, Status, New/Updated, and Errors choices so unavailable filters cannot be mistaken for usable filters.
\- Keeps Remakes, Rushes, and Internal Rejects active at zero so their maintained green-clear or red-alert indicators remain visible.
\- Automatically falls back to a route/status/attention selection that still has content after a date or route scope changes.
\- Enlarges the numeric counts on every Print / Export filter chip without increasing the control height.
\- Removes the surrounding Checked By box and moves the larger signoff text into the first-page title header, aligned with the Filters line on the right.
\- Enlarges \`Rows | Orders | QTY\` on first and continuation pages while keeping Filters visually secondary.
\- Preserves v0.223 page capacity, centered Order/Item/QTY columns, shared preview/print styling, and schema version 5.

**## Install v0.223**

1. Start from the maintained v0.222 project.
2. Extract the v0.223 changed-files ZIP directly into the current project folder.
3. Preserve the existing \`data\` folder and database files.
4. Restart the scanner server and refresh the browser with \`Ctrl+F5\`.

No database migration or separate setup script is required. v0.223 keeps schema version 5.

**## v0.223 highlights**

\- Moves the first-page \`Checked By\` field out of the branded title area and places it immediately above the delivery-list column headings.
\- Keeps the signoff right aligned and compact so the title remains clean without wasting printable height.
\- Adds two logical delivery-list lines to each first page.
\- Adds three logical delivery-list lines to every continuation page.
\- Uses 26/28 logical rows in Portrait and 27/29 in Landscape for first/continuation pages; glass-type separator rows continue to count toward the limit.
\- Centers the Order, Item, and QTY columns and transfers a small amount of width from Dimensions to QTY so the complete \`QTY\` heading remains visible.
\- Applies the same structure and sizing to the on-screen preview and popup print document through the shared stylesheet.
\- Preserves the enlarged v0.222 branding, repeating filters, alternating rows, fixed footer, Rush/remake frames, and idle-state recovery.

**## Install v0.222**

1. Start from the maintained v0.221 project.
2. Extract the v0.222 changed-files ZIP directly into the current project folder.
3. Preserve the existing \`data\` folder and database files.
4. Restart the scanner server and refresh the browser with \`Ctrl+F5\`.

No database migration or separate setup script is required. v0.222 keeps schema version 5.

**## v0.222 highlights**

\- Enlarges the complete first-page branded title block by approximately 30%, including the supplied logo, route title, full date, totals, filters, badge, and Checked By field.
\- Enlarges continuation-page branding by approximately 10% while preserving a more compact hierarchy than page one.
\- Uses fit-aware medium and long route-title sizes so multi-route headings remain on one line beside the Checked By field.
\- Applies the same sizing to the on-screen Letter preview and popup print document through the shared stylesheet.
\- Reserves safe vertical space by adjusting logical row limits to 24/25 in Portrait and 25/26 in Landscape for first/continuation pages.
\- Preserves Default Letter margins, repeating filters and footer, glass headings, alternating rows, Rush/remake frames, and the v0.221 idle-state recovery.

**## Install v0.221**

1. Start from the maintained v0.220 project.
2. Extract the v0.221 changed-files ZIP directly into the current project folder.
3. Preserve the existing \`data\` folder and database files.
4. Restart the scanner server and refresh the browser with \`Ctrl+F5\`.

No database migration or separate setup script is required. v0.221 keeps schema version 5.

**## v0.221 highlights**

\- Preserves already loaded delivery-list item detail when the 10-second background catalog heartbeat returns an unchanged lightweight list summary.
\- Invalidates cached print rows only when list revision fields actually change, then reloads only the selected lists on demand.
\- Reasserts committed route state when the tab regains focus, returns from browser history, or becomes visible again.
\- Keeps the recovery event-driven; unchanged heartbeats perform no Print / Export rerender and no extra API request.
\- Prevents a long-idle page from showing Airport as selected while preview/print rows have silently been discarded.

**## Install v0.220**

1. Start from the maintained v0.219 project.
2. Extract the v0.220 changed-files ZIP directly into the current project folder.
3. Preserve the existing \`data\` folder and database files.
4. Restart the scanner server and refresh the browser with \`Ctrl+F5\`.

No database migration or separate setup script is required. v0.220 keeps schema version 5.

**## v0.220 highlights**

\- Removes the Date write-in field from delivery-list signoff and keeps one right-aligned \`Checked By\` line.
\- Repeats the compact active Filters summary on first and continuation pages.
\- Uses route-specific gradients for Airport, Indian Trail, Greenville, CPU, and DTC choices.
\- Groups visible glass types under compact Mirror, Tempered, and Annealed separators with matching category colors.
\- Gives All/Not Scanned/Partial/Complete and Attention choices distinct, readable gradients.
\- Adds Scan-page-style red exclamation circles when Remakes, Rushes, or Internal Rejects exist and green check circles when each category is clear.
\- Reduces continuation-page row limits by one logical row to reserve safe space for the repeating filter line.
\- Preserves the shared preview/print stylesheet, 90% Portrait preview zoom, Letter geometry, print logo, pagination, gray bands, alternating rows, and repeating Printed at footer.

**## v0.219 highlights**

\- Moves the first-page Checked By and Date signoff box slightly lower so it aligns more naturally with the branded title block.
\- Forces both signoff labels and the full delivery date to remain on one line.
\- Makes the popup print document load the same maintained \`static/css/styles.css\` used by the preview instead of carrying a second duplicated formatting definition.
\- Waits for the shared stylesheet, fonts, and logo image before opening the browser print dialog.
\- Keeps only physical Letter-page and printer-margin overrides inside the popup, preventing future preview/print formatting drift.
\- Sets Portrait preview to 90% by default, including after returning from Landscape mode.
\- Preserves Letter dimensions, default 0.4-inch margins, pagination, table geometry, gray bands, alternating rows, remake/rush frames, and footer placement.

**## v0.218 highlights**

\- Restores the supplied Barefoot Company / Builders FirstSource logo asset to the changed-files package so preview and popup print documents render the actual artwork rather than fallback alt text.
\- Resolves the logo through an absolute application URL with a v0.218 cache key, keeping popup printing reliable after upgrades.
\- Removes the continuation-sheet sentence beneath the title while retaining the top-right page number.
\- Keeps route-driven delivery-list titles on one continuous line and automatically scales unusually long multi-route titles instead of wrapping them into an indented second line.
\- Enlarges the full weekday date to sit just below the title in the same visual hierarchy.
\- Tightens the vertical gap between \`Rows | Orders | QTY\` and the active Filters line.
\- Preserves pagination, gray bands, alternating rows, first-page signoff fields, remake/rush borders, and repeating Printed at footers.

**## v0.217 highlights**

\- Displays delivery dates in the readable \`Tuesday, August 4, 2026\` format across the browser application, including the Home page and Delivery List views.
\- Replaces the print header's compact numeric date-first wording with a route-first title such as \`INDIAN TRAIL DELIVERY LIST\`.
\- Joins multiple selected routes with vertical separators, such as \`GREENVILLE | CPU | DTC DELIVERY LIST\`.
\- Places the full weekday date directly beneath the route title in preview and actual paper output.
\- Expands the adaptive Print / Export date control so full weekday dates and custom ranges remain readable.
\- Preserves the supplied print logo, page totals, filters, signoff fields, pagination, gray bands, alternating rows, and repeating footer.

**## v0.216 highlights**

\- Adds the supplied stacked Barefoot Company and Builders FirstSource logo as a dedicated print asset and uses it in preview and generated print pages.
\- Crops only the unused outer canvas around the supplied logo, retaining the artwork itself and a clean white print margin.
\- Removes the extra title/header divider above the table on normal, Rush, remake, and continuation pages while preserving the black divider between column headings and glass-type groups.
\- Places the active Filters line on its own line directly beneath \`Rows | Orders | QTY\`.
\- Preserves v0.215 date-first titles, dynamic destinations, alternating rows, gray table bands, pagination, remake/rush frames, and repeating footer.

**## v0.215 highlights**

\- Makes the delivery date the dominant top-left heading in compact \`M/D/YY\` format.
\- Places \`Delivery list for \<destination>\` beneath the date and derives the destination from the committed Route selection.
\- Reuses the existing sidebar Barefoot/Builders FirstSource logo beside the title with grayscale and contrast treatment for black-and-white printing.
\- Adds a strong black divider between the column headings and every glass-type subheader.
\- Alternates printable order rows between white and light gray while preserving exact print colors in Chrome and Edge.
\- Preserves v0.214 page capacities, first-page signoff details, compact continuation headers, gray heading bands, and repeating footer.

**## v0.214 highlights**

\- Raises Portrait pagination to 25 logical rows on first pages and 27 on continuation pages.
\- Raises Landscape pagination to 26 logical rows on first pages and 28 on continuation pages, with glass headings still counted toward the page limit.
\- Keeps Checked By, Date, and active Filters only on the first page of each delivery-list section; continuation pages retain the title, page identification, and totals.
\- Moves \`Printed at\` into the bottom-left footer of every page.
\- Centers Route in both preview and actual print output.
\- Forces gray column-header and glass-type subheader backgrounds to print in Chrome and Edge.

**## v0.210 highlights**

\- Commits Airport to maintained Print / Export state before the GUI becomes visible, rather than relying on the route chip's checked appearance.
\- Replaces the redundant reset-then-reapply startup sequence with one awaited initialization transaction.
\- Prevents stale route controls from a previous GUI session from overwriting the new session's Airport default.
\- Shows loading filter content and disables empty output until the current delivery-list details are ready.
\- Makes an immediate Print or Export click wait for initialization and then revalidates the committed Airport route.
\- Invalidates late asynchronous work when Print / Export closes or reopens, preventing an older session from replacing the active one.
\- Preserves the v0.209 system default preset, landscape sheets, print totals, preset redesign, and schema version 5.

**## v0.209 highlights**

\- Moves Delivery Date directly beside the Filters section title while keeping Create Preset, Saved Presets, and Clear Filters grouped on the right.
\- Raises all four header controls to the same larger 12.5-pixel type size with centered labels and icons.
\- Rebuilds Create Preset as a guided two-step workspace with a clear naming panel, system-default explanation, usage guide, balanced filter cards, and responsive output controls.
\- Adds an immutable **\*\*System Default · All Items\*\*** preset for every user and applies it automatically when Print / Export first opens.
\- Defines the system default as Airport/all outbound items, All Glass, All Status, All Attention, PDF, one copy, and Portrait.
\- Preserves user-created presets separately and prevents the reserved System Default name from being overwritten.
\- Adds a true landscape delivery-list layout with orientation-specific pagination, tighter row geometry, wider Dimensions and Customer columns, and a shorter notes area.
\- Shows Total printable rows, Total orders, and Total QTY above Printed at on every delivery-list sheet and continuation page.
\- Replaces the remake sheet's edge border with an inset dashed outline so all four corners remain inside the printer-safe area.
\- Preserves v0.208 exact glass matching, the custom range calendar, Lookup Manager glass library, exact order/item selection, PDF/XLSX/CSV output, and schema version 5.

**## v0.208 highlights**

\- Fixes exact glass-type selections showing valid counts while the document preview incorrectly displayed zero rows.
\- Stores route and exact glass selections in stable application state before filter controls are replaced or rerendered.
\- Filters imported products with normalized Unicode, inch/quote marks, whitespace, and case comparison while retaining the original maintained product label for presets and output.
\- Preserves Airport as the complete outbound route without requiring users to click Airport again after choosing a glass type.
\- Restores saved glass-type presets against normalized product identities so minor formatting differences do not invalidate a known selection.
\- Centers Delivery Date, Create Preset, Saved Presets, and Clear Filters text and icons within their compact header controls.
\- Preserves the v0.207 custom-range calendar, Lookup Manager glass library, user-scoped presets, exact print rows, exports, and schema version 5.

**## v0.207 highlights**

\- Removes repeated Delivery Date / Date Range prefixes so the selector displays clean dates and ranges.
\- Keeps Custom Range open after the first date, requires a second date, and closes only after Apply Dates or an explicit cancel/outside click.
\- Increases Delivery Date, Create Preset, Saved Presets, and Clear Filters text to the same 10.5-pixel size used by filter-chip content.
\- Preserves Airport, All Glass, and exact glass selections through initial asynchronous filter rendering so first-use glass filtering no longer produces a false zero-row preview.
\- Reflows Create Preset into filled three-column and responsive two-/one-column layouts with no blank section beside Attention.
\- Loads every maintained Lookup Manager product value for the Glass Types preset library and displays its friendly product-name label.
\- Keeps Create Preset immediate by prefetching the small lookup library and enriching the open modal without loading historical delivery lists.
\- Preserves user-scoped presets, exact preview/print rows, PDF/XLSX/CSV output, and schema version 5.

**## v0.206 highlights**

\- Reduced Delivery Date, Create Preset, Saved Presets, and Clear Filters to compact 34-pixel controls.
\- Keeps all four Print / Export header controls aligned on one desktop row, with controlled wrapping on narrower screens.
\- Rebuilt the Create Preset modal with a clearer name section, polished category cards, improved output controls, and responsive layout.
\- Opens Create Preset immediately from already-loaded data instead of fetching every historical delivery list.
\- Removed lifetime glass-type quantity totals from preset creation; the builder now stores and displays glass-type names only.
\- Added a glass-type search field inside Create Preset for faster selection.
\- Fixed Custom Date Range closing immediately when chosen from the enhanced Delivery Date dropdown.
\- Preserved user-scoped preset storage, active-preset restoration, exact preview/print behavior, and schema version 5.

**## v0.205 highlights**

\- Gives Delivery Date, Create Preset, Saved Presets, and Clear Filters one consistent 40-pixel control system.
\- Keeps Custom Date Range as the first date-selector option while individual delivery dates remain one-click choices.
\- Replaces the old mixed single/range calendar with a two-month Date From / Date To range picker.
\- Highlights today, marks known outbound dates, and requires both range endpoints before Apply Range is enabled.
\- Loads glass types from every currently known delivery list before opening the preset builder.
\- Stores presets and the active preset under the signed-in user instead of sharing one browser-wide active choice.
\- Automatically reapplies the user's active preset whenever Print / Export is reopened, until that user selects another preset or clears filters.
\- Preserves the working v0.204 preview, visual polish, exact item/order selection, and direct-print workflow.

**## v0.204 highlights**

\- Repairs the preview page container that expanded to an extreme off-screen width and left the visible preview pane blank.
\- Keeps every preview page centered inside a normal-width, vertically scrollable document stack.
\- Uses layout-aware preview zoom instead of applying competing transforms to both the page stack and each sheet.
\- Preserves the exact delivery-list sheet markup shared by the preview and the working print popup.
\- Rebalances the control center so the filter workspace and document preview fit normal floor-monitor widths cleanly.
\- Gives Route, Glass Type, Status, Attention, order search, and selected items consistent card spacing and typography.
\- Allows long filter labels to wrap instead of clipping or overlapping their quantity values.
\- Refines the Filters header so Delivery Date, Create Preset, Saved Presets, and Clear Filters remain aligned without crowding.
\- Polishes the preview toolbar, paper background, page shadow, status badge, zoom controls, and output footer.
\- Makes Copies, Layout, File Type, and Print/Export controls wrap safely on narrower panes rather than overlapping.
\- Updates the visible footer version and browser cache keys to v0.204.

**## v0.203 highlights**

\- Moves the delivery-date selector into the right side of the Filters heading.
\- Lists individual delivery dates in the maintained dropdown and keeps Custom date range as the first choice.
\- Opens the existing calendar for custom ranges with today's date highlighted.
\- Reorders the filter workspace to Route and Glass Type on top, Status and Attention below, and exact orders/items at the bottom.
\- Replaces the Copies dropdown with a one-to-ten increment control.
\- Replaces the Layout dropdown with exclusive Portrait and Landscape buttons.
\- Prints synchronously from the exact browser preview so popup blockers do not suppress the print window after an asynchronous request.
\- Uses CSS \`@page\` portrait or landscape sizing so the browser print dialog reflects the selected layout.
\- Makes the preview and printed document share the same sheet titles, glass grouping, continuation pages, row limits, columns, notes box, Rush styling, and remake styling.
\- Removes the failed preview-reconciliation warning and keeps spreadsheet exports on the authenticated exact-row session path.
\- Reinforces smart searching by loading current list detail before matching order, item, customer, glass, or Job Nr. text.

**## v0.202 highlights**

\- Replaced GET-only print reconciliation with an authenticated POST selection contract carrying the exact visible row IDs.
\- Creates a short-lived same-user output token so Print, PDF, XLSX, and CSV use the same locked selection as the preview.
\- Fixed Print List failing after a valid live preview reported that server reconciliation returned no rows.
\- Searches order number, item number, customer, and Job Nr. values while typing.
\- Lets operators add either one exact item or the complete order to Selected Orders & Items.
\- Supports removing exact items and whole orders independently or clearing the complete selection.
\- Removes dates and exact customer/order choices from saved presets.
\- Adds file type, copy count, and portrait/landscape layout to the Create Preset GUI.
\- Moves the compact Create Preset and Saved Presets controls beside Clear Filters.
\- Shows every delivery-list preview page in one vertically scrollable document instead of using a page-number selector.
\- Adds copy count and portrait/landscape selectors beside the maintained file-type selector.
\- Keeps PDF paired with Print List; XLSX and CSV remain paired with Export List.

**## v0.201 highlights**

\- Selecting **\*\*All Glass\*\*** deselects every exact glass type and represents a true unrestricted glass selection.
\- Selecting any exact glass type clears All Glass; clearing every exact type restores All Glass.
\- Repaired the live preview gate so All Glass no longer appears as zero selected glass types.
\- Keeps All Status and All Attention the same size as the other filter buttons and positions each in the top-left of its section.
\- Moves Date Selection to the top of the Print / Export filter workspace.
\- Adds one calendar GUI with Single Date and Custom Range modes.
\- Highlights today's date and marks dates that have outbound delivery lists.

**## v0.199 highlights**

\- Forces white text and quantity counts on every selected Print / Export filter.
\- Converts customer, Job Nr., and order searching into an explicit multi-order picker.
\- Keeps selected orders in a removable list with individual and Clear All controls.
\- Stores selected exact orders in browser presets and sends them to preview, print, PDF, and XLSX output.
\- Replaces the browser prompt with a dedicated Save Preset GUI and overwrite guidance.
\- Places Route choices in a vertical rail on the right side of the filter workspace.
\- Narrows the preview pane and renders a letter-shaped delivery-list page using the real print columns and glass grouping.
\- Draws a live preview immediately from loaded rows, then reconciles it with the exact backend print package.
\- Keeps the live preview visible as a fallback if exact preview reconciliation fails instead of leaving a blank page.

**## v0.198 highlights**

\- Removed the Stage filter from Print / Export and made Route the primary list selector.
\- Added the maintained Route choices: Airport, Indian Trail, Greenville, CPU, and DTC.
\- Airport includes every item on the selected Airport Outbound delivery lists; destination routes filter those outbound items to the selected destinations.
\- Repaired the missing Route, Status, Attention, and Glass Type sections by removing a call to a nonexistent browser helper.
\- Added a Quick Date selector that sets the start and end dates to one available delivery date while preserving the full date-range controls.
\- Rebuilds Glass Type choices from the glass types that actually exist in the selected date range and route selection.
\- Added smart Search suggestions that surface matching orders while typing a customer, complete or partial order number, or Job Nr.
\- Extended backend search matching to Job Nr., product, and source identifiers so preview, print, and XLSX remain aligned.
\- Removed the extra decorative circle from the Print / Export header.
\- Preserved the exact backend preview, output safeguards, presets, PDF/XLSX controls, and scanner-panel header.

**## Start the local web app**

1. Keep \`Start-DeliveryScannerWebApp.bat\` and \`Start-DeliveryScannerWebApp.ps1\` beside \`server.py\`.
2. Keep the existing \`data\`, \`assets\`, \`sounds\`, and \`static\` folders in the project folder.
3. Double-click \`Start-DeliveryScannerWebApp.bat\`.
4. Keep the launcher window open while the local server is running.

SQLite remains the active/default database. The production database is:

\`data\delivery-scanner-pilot.db\`

Keep this file and its \`-wal\`/\`-shm\` companions together whenever the app is running. Before any numbered schema upgrade, startup creates and verifies a version-labeled backup under \`data\backups\`. Production databases are never deleted or recreated automatically.

**## Database preservation**

The \`data\` folder is production state, not application source. Never replace or delete it during a code-only update. Stop the server and copy the complete folder, including SQLite \`-wal\` and \`-shm\` companions, before transferring a floor database to another checkout.

**## Cross-delivery-date scanning**

The settings are available under **\*\*Admin > Cross-Date Scanning\*\***:

\- **\*\*Disabled\*\*** — scans remain limited to the selected delivery list.
\- **\*\*Ask before switching\*\*** — every valid cross-date match requires operator confirmation.
\- **\*\*Automatically switch unique matches\*\*** — one safe match switches and scans automatically; ambiguous or guarded matches require confirmation.

The default search window is:

\- Past delivery dates: **\*\*7 days\*\***
\- Future delivery dates: **\*\*30 days\*\***

The backend always checks the selected list first. Cross-date searching begins only when the barcode cannot be uniquely resolved on that list. Candidate lists must be active, inside the configured date window, accessible to the signed-in user, and in the same operational stage category.

The existing safety rules remain authoritative. Cross-date scanning does not bypass:

\- completed quantity checks;
\- duplicate handling;
\- user stage access;
\- outbound staging and transportation requirements;
\- Indian Trail outbound requirements;
\- rack status and destination compatibility;
\- manual bay selection;
\- supervisor override workflows; or
\- undo/redo and immutable scan history.

**## Automated delivery-list imports**

The maintained automation package is under \`automation\sql\_delivery\_export\`.

**### Floor computers: import the shared folder every hour**

1. Extract the newest changed-files package into the current scanner project folder.
2. Close the scanner web app/server window.
3. Run \`automation\sql\_delivery\_export\Setup-DeliveryListSqlAutomation.bat\` once.
4. Restart the scanner web app and confirm **\*\*Admin > Delivery Automation Control Center\*\*** shows **\*\*Import Temp Folder Only\*\*** with the schedule installed.
5. Run \`C:\DeliveryListAutomation\Run-Now\.cmd\` for a visible manual verification.

The floor setup copies the maintained runtime to \`C:\DeliveryListAutomation\Scripts\`, uses the existing shared Temp Delivery Lists folder, creates a 60-minute incremental task plus the normal daily full-window safety task, and disables the older built-in 5 PM importer for that Windows user. It does not query A+W SQL or replace the scanner database.

**### Central authorized computer: query SQL, export, and import**

Use the normal SQL automation setup and the Admin control center. Run \`C:\DeliveryListAutomation\Verify-SQL-And-Import.cmd\` with a known delivery date to verify the read-only SQL query, workbook generation, publication, maintained scanner import, and expected stage lists.

See \`automation\sql\_delivery\_export\README.md\` for the installed runtime and troubleshooting steps.

**## Database operations**

\- Azure migration dry run: \`py -3 -m database.migrate\_sqlite\_to\_azure\_sql --sqlite-path data\delivery-scanner-pilot.db\`
\- SQLite migrations are owned by \`database\migrations.py\`.
\- The logical cross-database contract is owned by \`database\contract.py\`.
\- v0.256 application contract: **\*\*256\*\***.
\- v0.253 application contract: **\*\*253\*\***.
\- v0.246 application contract: **\*\*246\*\***.
\- v0.235 application contract: **\*\*235\*\***.
\- Current SQLite schema contract: **\*\*5\*\***.

**## Optional container deployment**

Docker and Azure App Service support files are organized under \`deployment\`. They are not required for normal Windows floor operation.

\- Container definition: \`deployment\docker\Dockerfile\`
\- Container-only dependencies: \`deployment\docker\requirements.txt\`
\- Azure App Service setting template: \`deployment\azure\app-service.env.example\`

Run the Docker build from the project root so the root \`.dockerignore\` protects local databases, secrets, logs, backups, and verification output:

\`\`\`powershell
docker build -f deployment/docker/Dockerfile -t delivery-list-scanner .
\`\`\`

**## Audio language**

The maintained sound pack is stored under \`sounds\\\` as 44.1 kHz, 16-bit PCM mono WAV files. Open \`sounds\preview\_audio\_pack.html\` in a browser to audition the packaged cues without installing audio software. The web app loads semantic cue names from \`static\js\app.js\`, uses the existing shared volume/compressor chain, and falls back to synthesized tones only if a WAV file cannot be loaded.

v0.194 maps \`delivery\_date\_changed\` to the already packaged \`sounds\scan\_success.wav\` cue. Normal accepted scans continue using \`sounds\notification.wav\`, so no binary sound asset is included in this changed-files release.

**## Microsoft Graph email**

Microsoft Graph delivery supports customer manifests, ready notices, and Admin test messages. The configured sender is \`BarefootNC.Glass\@bldr.com\`, and the default controlled test recipient is \`brandon.m.smith\@bldr.com\`.

After BLDR IT provides the Entra tenant ID, application/client ID, and client-secret value, run \`Configure-MicrosoftGraphEmail.bat\` once. The secret is encrypted for the current Windows account and loaded only in memory by the normal scanner launcher.

**## Project documentation**

\- Ongoing version history: \`README\_CHANGELOG.md\`
\- Current folder ownership and cleanup guide: \`docs/PROJECT\_STRUCTURE.md\`
\- Automated SQL export/import runtime: \`automation/sql\_delivery\_export/README.md\`

**## Important local folders**

\- \`static\` — maintained browser CSS, JavaScript, and image source.
\- \`assets\` — favicon and print-page assets referenced by the server.
\- \`sounds\` — maintained browser audio cues.
\- \`data\` — required SQLite database and local scanner state. Keep it and back it up.
\- \`automation\` — scheduled delivery-list import/export source and setup scripts.
\- \`scripts\` — optional Windows setup and diagnostic utilities.
\- \`resources\` — source material retained for A+W integration work.
\- \`logs\` — generated diagnostics. Safe to clear while the app is stopped.
\- \`backups\` — retained recovery copies. Review dates before removing anything.
\- \`C:\DeliveryListAutomation\` — installed automation runtime, staging, logs, and task state.

The release ZIP contains no database, SQL credential, SAP runtime, demo delivery list, or new audio binary. When upgrading, keep the existing \`data\` folder. Production startup never seeds demo delivery lists; existing data is preserved and upgraded in place only after a verified backup succeeds.

Do not run the SQLite and Azure SQL versions as simultaneous writable production systems during a future cutover.
