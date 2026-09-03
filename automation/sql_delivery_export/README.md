## Website version 4 manual reject sync / Control Center recovery (v0.488)

`RejectSyncOnly` is a maintained browser/manual action that runs the configured A+W reject query and persists Internal Reject mirrors without exporting or reconciling delivery lists. The explicit manual action can run even when scheduled reject synchronization is disabled. Normal `SqlExportAndImport` runs also persist the reject payload even when no delivery-list source dates are present. This removes the prior coupling between reject ingestion and delivery-list drift.

Import History and `/latest-import` no longer request the full delivery-list catalog from their audit/status endpoints. Normal unfiltered Control Center browsing is bounded to 1,500 database rows plus 250 supplemental archives, cached where useful, and progressively renders 80 history rows; explicit searches/filters retain the deeper audit scan.

The glass-label probe now follows the observed optimization output into `FS_POOL` families (`STSL*.ASC`, `STSD*.ASC`, `PRODBDAZ.000`) and writes outputs 15-18 for payload/module/object discovery.


## Website version 4 reject reporting / automation performance (v0.487)

A+W logical breakages mirror into the standard scanner `reject_events` timeline and therefore participate in the Rejects page and normal reject Statistics. The timeline keeps break location/cause while machine-breakage reporting prefers the uniquely verified A+W machine enrichment. Repeat reject windows use a no-write fast path when raw A+W ROWIDs/payloads, rollback markers, and Internal Reject mirrors are already current.

Logs & Status now records the exact controller PowerShell command and the runner's exact Python subprocess command. While a browser-started run is active, live output is served from the controller's in-memory stream rather than rereading the entire growing log on every poll. Reject-sync progress includes unchanged row count, fast-path state, and `durationMs`.

The glass-label probe now writes targeted files `08-order-label-controls.csv` through `14-print-pipeline-module-references.csv`. These follow the verified `PROD_JOBITEM.OPTIMIZATION -> PROD_OPTI_SEQUENCE` bridge and inspect label controls, optimization SAVEFILE metadata, plates, AWV label fields, print jobs, pool payloads, and print-related module definitions. A+W remains SELECT-only.

## Website version 4 reject reset / refabrication behavior (v0.486)

A synchronized A+W `PROD_BREAKAGE` event is an operational Internal Reject. The scanner applies its scan/rack/bay rollback once per preserved raw A+W `ROWID`; later source refreshes cannot replay it. If the reject arrives before its delivery order exists, the reset stays pending and the direct importer retries after delivery reconciliation.

Fabrication completion is also reset by the latest Internal Reject. Existing Denver `.egl` and Waterjet `.nce` files that predate the reject remain visible as source/history but do not satisfy fabrication until a newer or overwritten completion file is observed.

For optimization-generated glass-label discovery, run from the project root:

```powershell
powershell.exe -ExecutionPolicy Bypass -File ".\scripts\diagnostics\Probe-AWGlassLabels.ps1"
```

Use an Order/Item that has already been optimized and has labels available in A+W. Return the generated `AW-Glass-Label-Probe-*` folder for schema analysis before the scanner imports label data.
<!-- File: automation/sql_delivery_export/README.md -->
# Delivery List Automation Runtime v132

## Website version 4 unified manual A+W sync / production query controls (v0.499)

The maintained browser workflow exposes one complete manual command: **Sync A+W Directly**. A browser-started direct sync forces delivery reconciliation, A+W Internal Reject synchronization, and Batch/Optimization/Cutting enrichment together. The old `RejectSyncOnly` runner action remains accepted only for compatibility with older installed callers; it is no longer shown as a separate Run Manually card. Scheduled Direct A+W Sync can independently include/exclude Reject and Production enrichment through Automation Control Center settings.

Production enrichment is bounded to order numbers already present in the direct delivery payload and is split into small configurable SQL batches. The query limits historical `PROD_JOBITEM` generations with `DENSE_RANK`, bounds positive Automatic Cutting bookings by a configurable lookback, pre-ranks `PROD_OPTI_SEQUENCE` and optimization state, uses `OPTION (RECOMPILE)`, and emits a live STEP before every SQL batch. A+W remains SELECT-only / `READ UNCOMMITTED`; production enrichment errors do not block delivery-list reconciliation.

The verified Cutting Labels report remains Print Point 846 / `Prodman_CuttingLabel_Optimisation.rpt`. For pixel-accurate reconstruction, export a Screen preview from the Crystal viewer to PDF rather than clicking Execute.


## Website version 4 A+W reject synchronization (v0.485)

Central `SqlExportAndImport` runs query `SYSADM.PROD_BREAKAGE` read-only and mirror each logical A+W breakage into scanner **Internal Reject** history while retaining immutable A+W source rows separately. `PROD_BREAKAGE.ROWID` remains the raw external identity; same-event BOM rows collapse into `aw_reject_events`. `KA_REKLA_GRND` and `KA_REKLA_ORT` are re-read on every sync so new/renamed A+W labels are learned automatically, while optional scanner mappings stay keyed to the stable numeric codes. The reject actor/timeline enrichment comes from the nearest `FS_BOOK_HISTORY` row with `BOOK_TYPE = 1` for the same Order/Item inside a tightly bounded 60-second window, ranked first by matching A+W reason/cause codes, then Explicit origin, BOM identity, and timestamp proximity. This avoids falling back to mutable `PROD_BREAKAGE.LASTCHANGEUSER` when A+W commits the booking a few seconds away from `BREAKAGEDATE`. Machine text is retained only when the registration point maps to one unique A+W machine. The Automated Import **A+W Rejects** tab controls enablement and Normal/Full lookback windows. A+W is never written to, and reject-query/persistence failures remain non-blocking so normal delivery reconciliation continues.

## Website version 4 direct A+W synchronization (v0.478)

The authorized central workflow now keeps the queried A+W SQL rows as the
authoritative scanner input. `Run-DeliveryListSqlAutomation.ps1` passes a
credential-free transient payload to `import_delivery_folder.py`, which converts
those rows into the same scanner item contract and sends them through the
maintained preview/reconciliation path. The dated XLSX is still generated and
published for troubleshooting, floor-computer folder imports, and manual export,
but the central SQL import no longer reparses that workbook.

The direct payload preserves immutable A+W Order/Item identity in each source ID,
so existing manual overrides, approved superseded-order decisions, route rules,
priority intake, scan/rack/bay preservation, import history, and source-removal
safety continue to use the same scanner business rules. Import history records
central direct runs as `aw_sql_direct_sync` and uses an `aw-sql://...` source path
instead of pretending the workbook was the authoritative source.

### A+W BDE / breakage diagnostic

`scripts\diagnostics\Probe-AWBdeBreakage.ps1` remains available for SELECT-only troubleshooting or schema discovery. The live BFSMAIN contract is now verified and production synchronization does **not** depend on the earlier status-455 hypothesis: durable rejects come from `PROD_BREAKAGE.IS_BREAKAGE = 1`, timeline Reject bookings use `FS_BOOK_HISTORY.BOOK_TYPE = 1`, reason text comes from `KA_REKLA_GRND`, and breakage location/cause text comes from `KA_REKLA_ORT`.


## v132 floor-computer folder import setup

Floor computers do not need A+W SQL access. Run
`Setup-DeliveryListSqlAutomation.bat` from this folder. The setup copies the
maintained runtime to `C:\DeliveryListAutomation\Scripts`, preserves existing
configuration with a timestamped backup, creates the command wrappers,
validates scanner compatibility, and installs the scheduled tasks.

The floor scheduler preflight now verifies read access to the Temp Delivery Lists folder and scanner compatibility without querying A+W SQL or requiring permission to write workbooks to the shared folder. The central authorized SQL computer keeps the existing SQL/workbook preflight unchanged.

## v125 safe Task Scheduler command handling

Windows PowerShell can turn text written by `schtasks.exe` to stderr into a terminating `NativeCommandError` while `$ErrorActionPreference` is `Stop`. A missing obsolete task therefore stopped installation even though there was nothing that needed to be deleted.

The maintained installer now queries legacy tasks before deletion and runs every Task Scheduler operation through one wrapper that captures native output and checks the actual process exit code. Missing legacy tasks are ignored; real create, query, delete, or launch failures still include their detailed scheduler output.

## v124 scheduler compatibility fix

The current SQL installer was fixed in v123, but its broad preflight also parsed an older Crystal scheduler script still present in the shared installed Scripts folder. That legacy file contained the same invalid `$incrementalTask:` and `$fullTask:` form. V124 repairs the legacy file and limits current SQL preflight parsing to maintained SQL entry points.

Before creating tasks, the installer now:

1. Parses the maintained SQL automation entry points and fails with exact line/column details on any syntax error.
2. Runs the existing `RuntimeTest` path for SQL connectivity, workbook generation, destination write access, and scanner compatibility.
3. Creates the incremental and full-refresh tasks.
4. Queries both tasks to confirm Windows retained them.
5. Starts the incremental task once as a scheduler launch check.

Historical patch overlays are no longer required by this source tree. Run the
maintained setup to refresh the installed automation runtime; it does not
rewrite the web app or replace the scanner database.

## Verify the real SQL query and scanner import

Run:

`C:\DeliveryListAutomation\Verify-SQL-And-Import.cmd`

Enter a delivery date known to contain A+W orders. The verification performs all of these checks:

- Parses every maintained SQL PowerShell automation entry point.
- Opens the configured A+W SQL connection using the existing read-only query path.
- Runs the configured SQL/workbook/scanner runtime preflight.
- Executes a one-date SQL query and export in Test mode so the workbook is freshly rebuilt and validated.
- Requires the configured known-date expected-count comparison to pass when the selected date matches the validation date.
- Requires the SQL/export summary to include the date in checked, source, and published collections.
- Explicitly invokes the maintained scanner folder importer with the selected date forced through its normal business workflow.
- Requires the normalized importer result to include the date and rejects any failed result.
- Confirms the expected workbook exists.
- Uses the maintained workbook parser and stage builder to compare expected list IDs with the configured scanner store.

A passing result proves the selected date moved through SQL query, workbook generation, workbook validation, the maintained scanner importer, and final stage-list presence. A failed result keeps the detailed automation log under `C:\DeliveryListAutomation\Logs`.

The runtime continues to query A+W read-only and uses the scanner's maintained import workflow.

## Route-aware stage verification fix

The importer and the end-to-end verifier now apply the scanner's active
Customer Route Rules before calculating which receiving-stage lists should
exist. This prevents a successful all-CPU, all-DTC, or all-Greenville delivery
date from being reported as failed merely because no Indian Trail list is
appropriate for that date.

The maintained `import_delivery_folder.py` and `verify_delivery_import.py`
already include this route-aware verification behavior.
