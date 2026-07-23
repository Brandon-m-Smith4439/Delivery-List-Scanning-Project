[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ProjectRoot,
    [string]$WorkingRoot = "C:\DeliveryListAutomation"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-ProjectRelease {
    param([Parameter(Mandatory = $true)][string]$Root)
    $readme = Join-Path $Root "README.md"
    if (-not (Test-Path -LiteralPath $readme -PathType Leaf)) {
        throw "README.md was not found in $Root"
    }
    $text = [IO.File]::ReadAllText($readme)
    $match = [regex]::Match($text, 'Current maintained release:\s*\*\*v(?<version>\d+)\*\*')
    if (-not $match.Success) {
        throw "The project README does not expose its maintained release."
    }
    return [int]$match.Groups["version"].Value
}

function Replace-RequiredText {
    param(
        [Parameter(Mandatory = $true)][string]$Text,
        [Parameter(Mandatory = $true)][string]$Old,
        [Parameter(Mandatory = $true)][string]$New,
        [Parameter(Mandatory = $true)][string]$Label
    )
    if (-not $Text.Contains($Old)) {
        throw "Could not find the expected $Label block. No project files were committed."
    }
    return $Text.Replace($Old, $New)
}

function Add-AssetAfterMatch {
    param(
        [Parameter(Mandatory = $true)][string]$Text,
        [Parameter(Mandatory = $true)][string]$Pattern,
        [Parameter(Mandatory = $true)][string]$Addition,
        [Parameter(Mandatory = $true)][string]$Label
    )
    $match = [regex]::Match($Text, $Pattern)
    if (-not $match.Success) {
        throw "Could not find the expected $Label asset anchor."
    }
    return $Text.Insert($match.Index + $match.Length, $Addition)
}

$resolvedRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$release = Get-ProjectRelease -Root $resolvedRoot
if ($release -lt 105) {
    throw "This integration requires scanner v105 or newer. Selected project is v$release."
}
if ($release -gt 121) {
    throw "The selected project is v$release. This v121 installer will not modify a newer release."
}

$requiredProjectFiles = @("index.html", "app.js", "server.py", "delivery_store.py", "database_contract.py", "database_migrations.py", "README.md", "README_CHANGELOG.md")
foreach ($name in $requiredProjectFiles) {
    $path = Join-Path $resolvedRoot $name
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required project file is missing: $path"
    }
}

$backupRoot = Join-Path $WorkingRoot ("Backups\v121-project-integration-{0}" -f (Get-Date -Format "yyyyMMdd-HHmmss"))
[void](New-Item -ItemType Directory -Path $backupRoot -Force)
foreach ($name in $requiredProjectFiles) {
    Copy-Item -LiteralPath (Join-Path $resolvedRoot $name) -Destination (Join-Path $backupRoot $name) -Force
}
foreach ($name in @(
    "delivery_automation_control.py",
    "delivery-automation-ui.js",
    "delivery-automation-ui.css",
    "notification-center-ui.js",
    "notification-center-ui.css",
    "delivery_import_safety.py"
)) {
    $existing = Join-Path $resolvedRoot $name
    if (Test-Path -LiteralPath $existing -PathType Leaf) {
        Copy-Item -LiteralPath $existing -Destination (Join-Path $backupRoot $name) -Force
    }
}

$indexPath = Join-Path $resolvedRoot "index.html"
$appPath = Join-Path $resolvedRoot "app.js"
$serverPath = Join-Path $resolvedRoot "server.py"
$storePath = Join-Path $resolvedRoot "delivery_store.py"
$databaseContractPath = Join-Path $resolvedRoot "database_contract.py"
$databaseMigrationsPath = Join-Path $resolvedRoot "database_migrations.py"
$readmePath = Join-Path $resolvedRoot "README.md"
$changelogPath = Join-Path $resolvedRoot "README_CHANGELOG.md"

$databaseContractText = [IO.File]::ReadAllText($databaseContractPath).Replace("`r`n", "`n")
$databaseMigrationsText = [IO.File]::ReadAllText($databaseMigrationsPath).Replace("`r`n", "`n")

# v121 adds a numbered, backup-protected SQLite migration for per-user line-update
# notices. The migration is additive and never edits existing scan or audit history.
$databaseContractText = [regex]::Replace($databaseContractText, 'APPLICATION_VERSION = "[^"]+"', 'APPLICATION_VERSION = "121"', 1)
$databaseContractText = [regex]::Replace($databaseContractText, 'CURRENT_SCHEMA_VERSION = \d+', 'CURRENT_SCHEMA_VERSION = 3', 1)
if (-not $databaseContractText.Contains('"line_update_notices"')) {
    $contractTableOld = @'
    "app_notification_receipts": "Per-user notification acknowledgements.",
'@
    $contractTableOld = $contractTableOld.Replace("`r`n", "`n").TrimEnd("`n")
    $contractTableNew = @'
    "app_notification_receipts": "Per-user notification acknowledgements.",
    "line_update_notices": "Per-user-visible new and updated delivery-list line events.",
    "line_update_receipts": "Per-user review acknowledgements for line update events.",
'@
    $contractTableNew = $contractTableNew.Replace("`r`n", "`n").TrimEnd("`n")
    $databaseContractText = Replace-RequiredText -Text $databaseContractText -Old $contractTableOld -New $contractTableNew -Label "database contract table inventory"
}
if (-not $databaseContractText.Contains('"line_update_notices": {')) {
    $contractColumnsOld = @'
    "machine_events": {
'@
    $contractColumnsOld = $contractColumnsOld.Replace("`r`n", "`n").TrimEnd("`n")
    $contractColumnsNew = @'
    "line_update_notices": {"id", "line_item_id", "list_id", "delivery_date", "change_type", "change_token", "source_hash", "created_at"},
    "line_update_receipts": {"notice_id", "user_id", "seen_at"},
    "machine_events": {
'@
    $contractColumnsNew = $contractColumnsNew.Replace("`r`n", "`n").TrimEnd("`n")
    $databaseContractText = Replace-RequiredText -Text $databaseContractText -Old $contractColumnsOld -New $contractColumnsNew -Label "database contract required columns"
}
if (-not $databaseContractText.Contains('"idx_line_update_notices_list_date"')) {
    $contractIndexOld = @'
    "idx_machine_events_machine_time": "Machine event timeline.",
'@
    $contractIndexOld = $contractIndexOld.Replace("`r`n", "`n").TrimEnd("`n")
    $contractIndexNew = @'
    "idx_line_update_notices_list_date": "Pending update lines by delivery list and current/future date.",
    "idx_line_update_receipts_user": "Per-user review state for update lines.",
    "idx_machine_events_machine_time": "Machine event timeline.",
'@
    $contractIndexNew = $contractIndexNew.Replace("`r`n", "`n").TrimEnd("`n")
    $databaseContractText = Replace-RequiredText -Text $databaseContractText -Old $contractIndexOld -New $contractIndexNew -Label "database contract index descriptions"
}
if (-not $databaseContractText.Contains('"line_update_notices": {"created_at"}')) {
    $contractTimestampOld = @'
    "machine_events": {"created_at_utc"},
'@
    $contractTimestampOld = $contractTimestampOld.Replace("`r`n", "`n").TrimEnd("`n")
    $contractTimestampNew = @'
    "line_update_notices": {"created_at"},
    "line_update_receipts": {"seen_at"},
    "machine_events": {"created_at_utc"},
'@
    $contractTimestampNew = $contractTimestampNew.Replace("`r`n", "`n").TrimEnd("`n")
    $databaseContractText = Replace-RequiredText -Text $databaseContractText -Old $contractTimestampOld -New $contractTimestampNew -Label "database contract timestamp columns"
}

if (-not $databaseMigrationsText.Contains('"v120_user_line_updates"')) {
    $migrationTupleAnchor = @'
    Migration(
        2,
        "v097_production_database",
        "UTC audit fields, relational constraints, immutable history, machine scanning tables, query indexes, and atomic FK validation; final-v097-r1",
        "_migration_002_v097_production_database",
    ),
)
'@
    $migrationTupleAnchor = $migrationTupleAnchor.Replace("`r`n", "`n")
    $migrationTupleBlock = @'
    Migration(
        2,
        "v097_production_database",
        "UTC audit fields, relational constraints, immutable history, machine scanning tables, query indexes, and atomic FK validation; final-v097-r1",
        "_migration_002_v097_production_database",
    ),
    Migration(
        3,
        "v120_user_line_updates",
        "Per-user current-and-future delivery-list line update notices and explicit review acknowledgements; v120-r1",
        "_migration_003_v120_user_line_updates",
    ),
)
'@
    $migrationTupleBlock = $migrationTupleBlock.Replace("`r`n", "`n")
    $databaseMigrationsText = Replace-RequiredText -Text $databaseMigrationsText -Old $migrationTupleAnchor -New $migrationTupleBlock -Label "v121 migration tuple"
}

# Keep the main application assets in place and replace only the isolated v107-v121 add-on references.
$indexText = [IO.File]::ReadAllText($indexPath)
$indexText = [regex]::Replace($indexText, '\s*<link rel="stylesheet" href="delivery-automation-ui\.css\?v=[^"]+">', '')
$indexText = [regex]::Replace($indexText, '\s*<link rel="stylesheet" href="notification-center-ui\.css\?v=[^"]+">', '')
$indexText = [regex]::Replace($indexText, '\s*<script src="delivery-automation-ui\.js\?v=[^"]+"></script>', '')
$indexText = [regex]::Replace($indexText, '\s*<script src="notification-center-ui\.js\?v=[^"]+"></script>', '')
$indexText = [regex]::Replace($indexText, '<link rel="stylesheet" href="styles\.css\?v=[^"]+">', '<link rel="stylesheet" href="styles.css?v=20260723-v121">', 1)
$indexText = [regex]::Replace($indexText, '<script src="app\.js\?v=[^"]+"></script>', '<script src="app.js?v=20260723-v121"></script>', 1)
$indexText = Add-AssetAfterMatch -Text $indexText `
    -Pattern '<link rel="stylesheet" href="styles\.css\?v=20260723-v121">' `
    -Addition ("`r`n    " + '<link rel="stylesheet" href="delivery-automation-ui.css?v=20260723-v121">' + "`r`n    " + '<link rel="stylesheet" href="notification-center-ui.css?v=20260723-v121">') `
    -Label "main stylesheet"
$indexText = Add-AssetAfterMatch -Text $indexText `
    -Pattern '<script src="app\.js\?v=20260723-v121"></script>' `
    -Addition ("`r`n  " + '<script src="delivery-automation-ui.js?v=20260723-v121"></script>' + "`r`n  " + '<script src="notification-center-ui.js?v=20260723-v121"></script>') `
    -Label "main JavaScript"


# Restore the original Delivery List Management overview. Import history now
# lives inside the Import / Update Delivery List control center, so remove the
# separate Admin-card history link left by v116/v117.
$deliveryManagementHeadingPattern = '(?s)<div class="section-heading">\s*<h2>Delivery List Management</h2>\s*(?:<div class="section-actions">\s*)?(?:<button class="link-button" id="importHistoryBtn" type="button">Import history</button>\s*)?<button class="link-button" type="button" data-admin-modal="deliveryLists">Edit delivery lists</button>\s*(?:</div>\s*)?</div>'
$deliveryManagementHeading = @'
            <div class="section-heading">
              <h2>Delivery List Management</h2>
              <button class="link-button" type="button" data-admin-modal="deliveryLists">Edit delivery lists</button>
            </div>
'@
$deliveryManagementHeading = $deliveryManagementHeading.Replace("`r`n", "`n").TrimEnd("`n")
if ([regex]::IsMatch($indexText, $deliveryManagementHeadingPattern)) {
    $indexText = [regex]::Replace($indexText, $deliveryManagementHeadingPattern, $deliveryManagementHeading, 1)
}
else {
    throw "Could not find the Delivery List Management heading for the v121 control-center integration."
}
$indexText = [regex]::Replace($indexText, '(?s)\s*<details class="admin-import-settings">.*?</details>', '', 1)
$indexText = [regex]::Replace($indexText, '\s*<div id="importHistory" class="compact-list" hidden></div>', '', 1)

# Keep every connected browser's delivery-list catalog current without changing pages,
# forcing dropdown change events, or interrupting an active scan workflow.
$appText = [IO.File]::ReadAllText($appPath).Replace("`r`n", "`n")
$legacyBridgeV114 = @'
  lastGlassFilterSignature: "",
};

// DLS_AUTOMATION_LIST_REFRESH_BRIDGE_V114
// Synchronize the scanner's in-memory delivery-list catalog after the SQL
// automation imports files. This removes the need for a full browser refresh.
document.addEventListener("dls:delivery-list-data-refreshed", async (event) => {
  const detail = event.detail && typeof event.detail === "object" ? event.detail : {};
  let refreshedLists = Array.isArray(detail.lists) ? detail.lists : null;

  if (!refreshedLists) {
    try {
      const response = await fetch("/api/delivery-lists", {
        credentials: "same-origin",
        cache: "no-store",
      });
      const payload = await response.json();
      if (response.ok && Array.isArray(payload.lists)) refreshedLists = payload.lists;
    } catch {
      refreshedLists = null;
    }
  }

  if (Array.isArray(detail.recentImports)) {
    state.adminRecentImports = detail.recentImports.slice();
  }
  if (!Array.isArray(refreshedLists)) return;

  const dateSelect = document.getElementById("deliveryDateSelect");
  const stageSelect = document.getElementById("deliveryStageSelect");
  const previousDate = String(dateSelect?.value || "");
  const previousStage = String(stageSelect?.value || state.activeListId || "");
  state.lists = refreshedLists.slice();

  const deliveryDates = [...new Set(
    state.lists.map((item) => String(item.deliveryDate || "").trim()).filter(Boolean)
  )].sort();
  if (!dateSelect || !stageSelect || !deliveryDates.length) return;

  const today = new Date();
  const todayKey = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
  const selectedDate = deliveryDates.includes(previousDate)
    ? previousDate
    : deliveryDates.find((value) => value >= todayKey) || deliveryDates[deliveryDates.length - 1];

  dateSelect.innerHTML = deliveryDates.map((value) => {
    const parsed = new Date(`${value}T12:00:00`);
    const label = Number.isNaN(parsed.getTime())
      ? value
      : parsed.toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" });
    return `<option value="${value}">${label}</option>`;
  }).join("");
  dateSelect.value = selectedDate;

  const selectedDateLists = state.lists.filter(
    (item) => String(item.deliveryDate || "") === selectedDate
  );
  const desiredListId = selectedDateLists.some((item) => String(item.id || "") === previousStage)
    ? previousStage
    : String(selectedDateLists[0]?.id || "");
  state.activeListId = desiredListId;

  dateSelect.dispatchEvent(new Event("change", { bubbles: true }));
  window.setTimeout(() => {
    if (desiredListId && [...stageSelect.options].some((option) => option.value === desiredListId)) {
      stageSelect.value = desiredListId;
      state.activeListId = desiredListId;
      stageSelect.dispatchEvent(new Event("change", { bubbles: true }));
    }
  }, 0);
});
'@
$legacyBridgeV114 = $legacyBridgeV114.Replace("`r`n", "`n")
if ($appText.Contains($legacyBridgeV114)) {
    $appText = $appText.Replace($legacyBridgeV114, "  lastGlassFilterSignature: `"`",`n};")
}
# Remove the previous v115/v116 delivery-catalog bridge before installing the
# v121 bridge. Merely renaming the marker would preserve the stale behavior.
$automationBridgePattern = '(?s)\n// DLS_AUTOMATION_LIST_REFRESH_BRIDGE_V(?:115|116|117|118|119|120|121)\n.*?\n\}\);\n'
$appText = [regex]::Replace($appText, $automationBridgePattern, "`n", 1)

$appStateAnchor = @'
  lastGlassFilterSignature: "",
};
'@
$appStateAnchor = $appStateAnchor.Replace("`r`n", "`n")
$appRefreshBridge = @'
  lastGlassFilterSignature: "",
};

// DLS_AUTOMATION_LIST_REFRESH_BRIDGE_V121
// Delivery List Management has two independent live inputs: the current list
// catalog and the complete newest import result. Keep both in the app's normal
// state, then call the original Admin renderer so the existing layout remains
// authoritative instead of drawing a second replacement UI.
let dlsAutomationLatestImportCheckedAt = "";

function dlsAutomationDateLabel(value) {
  const parsed = new Date(`${value}T12:00:00`);
  return Number.isNaN(parsed.getTime())
    ? value
    : parsed.toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" });
}

function dlsAutomationStageLabel(item) {
  const base = String(item.label || item.stage || item.scanner || item.id || "Delivery-list stage");
  const unseen = Number(item.unseenUpdateCount || 0);
  return unseen > 0 ? `${base} - ${unseen} update${unseen === 1 ? "" : "s"}` : base;
}

function dlsAutomationTryRenderer(renderer, name) {
  if (typeof renderer !== "function") return false;
  try {
    renderer();
    return true;
  } catch (error) {
    console.warn(`Delivery-list catalog renderer ${name} could not run.`, error);
    return false;
  }
}

function dlsAutomationApplyLastUpdatedTimestamp(value) {
  const text = String(value || dlsAutomationLatestImportCheckedAt || "").trim();
  if (!text) return;
  dlsAutomationLatestImportCheckedAt = text;
  const parsed = new Date(text);
  const label = Number.isNaN(parsed.getTime())
    ? text
    : parsed.toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
  const target = document.getElementById("adminLastUpdated");
  if (target) target.textContent = `Last updated: ${label}`;
}

function dlsAutomationRefreshVisibleListViews(lastCheckedAt = "") {
  const adminPage = document.getElementById("adminPage");
  if (adminPage && !adminPage.hidden) {
    // renderAdmin is the maintained page renderer and preserves the exact
    // Delivery List Management layout. Older add-ons guessed at narrower
    // renderer names and could update the wrong part of the Admin page.
    let rendered = false;
    if (typeof renderAdmin === "function") {
      rendered = dlsAutomationTryRenderer(renderAdmin, "renderAdmin");
    }
    if (!rendered && typeof renderAdminDeliveryLists === "function") {
      rendered = dlsAutomationTryRenderer(renderAdminDeliveryLists, "renderAdminDeliveryLists");
    }
    if (!rendered && typeof renderAdminDeliveryListManagement === "function") {
      rendered = dlsAutomationTryRenderer(renderAdminDeliveryListManagement, "renderAdminDeliveryListManagement");
    }
    if (!rendered && typeof renderAdminDashboard === "function") {
      dlsAutomationTryRenderer(renderAdminDashboard, "renderAdminDashboard");
    }
    window.requestAnimationFrame(() => dlsAutomationApplyLastUpdatedTimestamp(lastCheckedAt));
    return;
  }

  const homePage = document.getElementById("homePage");
  if (homePage && !homePage.hidden) {
    if (typeof renderHome === "function" && dlsAutomationTryRenderer(renderHome, "renderHome")) return;
    if (typeof renderHomeDeliveryLists === "function") {
      dlsAutomationTryRenderer(renderHomeDeliveryLists, "renderHomeDeliveryLists");
    }
  }
}

function dlsAutomationApplyDeliveryCatalog(refreshedLists) {
  if (!Array.isArray(refreshedLists)) return false;

  const dateSelect = document.getElementById("deliveryDateSelect");
  const stageSelect = document.getElementById("deliveryStageSelect");
  const previousDate = String(dateSelect?.value || "");
  const previousStage = String(stageSelect?.value || state.activeListId || "");
  state.lists = refreshedLists.slice();

  const deliveryDates = [...new Set(
    state.lists.map((item) => String(item.deliveryDate || "").trim()).filter(Boolean)
  )].sort();

  if (dateSelect && stageSelect && deliveryDates.length) {
    const today = new Date();
    const todayKey = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
    const selectedDate = deliveryDates.includes(previousDate)
      ? previousDate
      : deliveryDates.find((value) => value >= todayKey) || deliveryDates[deliveryDates.length - 1];

    dateSelect.innerHTML = deliveryDates.map(
      (value) => `<option value="${value}">${dlsAutomationDateLabel(value)}</option>`
    ).join("");
    dateSelect.value = selectedDate;

    const selectedDateLists = state.lists.filter(
      (item) => String(item.deliveryDate || "") === selectedDate
    );
    stageSelect.innerHTML = selectedDateLists.map((item) => {
      const listId = String(item.id || "");
      return `<option value="${listId}">${dlsAutomationStageLabel(item)}</option>`;
    }).join("");

    const desiredListId = selectedDateLists.some((item) => String(item.id || "") === previousStage)
      ? previousStage
      : String(selectedDateLists[0]?.id || "");
    if (desiredListId) stageSelect.value = desiredListId;

    const activeStillExists = state.lists.some(
      (item) => String(item.id || "") === String(state.activeListId || "")
    );
    if (!activeStillExists && desiredListId) state.activeListId = desiredListId;
  }
  return true;
}

function dlsAutomationApplyImportSnapshot(detail = {}) {
  const latestResults = Array.isArray(detail.latestImportResults)
    ? detail.latestImportResults
    : (Array.isArray(detail.recentImports) ? detail.recentImports : null);
  let changed = false;

  if (latestResults) {
    state.adminRecentImports = latestResults.slice();
    changed = true;
  }
  if (Array.isArray(detail.lists)) {
    changed = dlsAutomationApplyDeliveryCatalog(detail.lists) || changed;
  }
  if (detail.lastCheckedAt) {
    dlsAutomationLatestImportCheckedAt = String(detail.lastCheckedAt);
    changed = true;
  }

  if (!changed) return;
  dlsAutomationRefreshVisibleListViews(detail.lastCheckedAt || dlsAutomationLatestImportCheckedAt);
  document.dispatchEvent(new CustomEvent("dls:delivery-list-catalog-synced", {
    detail: {
      listCount: state.lists.length,
      importResultCount: state.adminRecentImports.length,
      lastCheckedAt: dlsAutomationLatestImportCheckedAt,
      selectedDate: String(document.getElementById("deliveryDateSelect")?.value || ""),
      selectedListId: String(document.getElementById("deliveryStageSelect")?.value || state.activeListId || ""),
    },
  }));
}

document.addEventListener("dls:delivery-list-data-refreshed", (event) => {
  const detail = event.detail && typeof event.detail === "object" ? event.detail : {};
  dlsAutomationApplyImportSnapshot(detail);
});
'@
$appRefreshBridge = $appRefreshBridge.Replace("`r`n", "`n")
$appText = Replace-RequiredText -Text $appText -Old $appStateAnchor -New $appRefreshBridge -Label "app delivery-list state anchor"

$serverText = [IO.File]::ReadAllText($serverPath).Replace("`r`n", "`n")
$legacyRecentImportRoute = @'
        if parsed.path == "/api/admin/delivery-automation/recent-imports":
            user = self.require_permission("import_delivery_lists")
            if not user:
                return
            limit = parse_qs(parsed.query).get("limit", ["20"])[0]
            self.send_json(DELIVERY_AUTOMATION.get_recent_imports(int(limit or 20)))
            return
'@
$legacyRecentImportRoute = $legacyRecentImportRoute.Replace("`r`n", "`n")
$paginatedRecentImportRoute = @'
        if parsed.path == "/api/admin/delivery-automation/recent-imports":
            user = self.require_permission("import_delivery_lists")
            if not user:
                return
            params = parse_qs(parsed.query)
            self.send_json(
                DELIVERY_AUTOMATION.get_import_history(
                    page=int(params.get("page", ["1"])[0] or 1),
                    page_size=int(params.get("pageSize", params.get("limit", ["20"]))[0] or 20),
                    query=params.get("q", [""])[0],
                    classification=params.get("classification", [""])[0],
                    date_from=params.get("dateFrom", [""])[0],
                    date_to=params.get("dateTo", [""])[0],
                )
            )
            return
'@
$paginatedRecentImportRoute = $paginatedRecentImportRoute.Replace("`r`n", "`n")
if ($serverText.Contains($legacyRecentImportRoute)) {
    $serverText = $serverText.Replace($legacyRecentImportRoute, $paginatedRecentImportRoute)
}
if (-not $serverText.Contains('from delivery_automation_control import DeliveryAutomationController')) {
    $serverText = Replace-RequiredText -Text $serverText `
        -Old "from scanner_config import load_config" `
        -New "from scanner_config import load_config`nfrom delivery_automation_control import DeliveryAutomationController" `
        -Label "server import"
}

if (-not $serverText.Contains('from delivery_import_safety import install_safe_delivery_import')) {
    $serverText = Replace-RequiredText -Text $serverText `
        -Old "from delivery_automation_control import DeliveryAutomationController" `
        -New "from delivery_automation_control import DeliveryAutomationController`nfrom delivery_import_safety import install_safe_delivery_import" `
        -Label "safe delivery import server import"
}

$controllerPattern = 'DELIVERY_AUTOMATION = DeliveryAutomationController\(ROOT, CONFIG(?:, STORE)?\)'
if ([regex]::IsMatch($serverText, $controllerPattern)) {
    $serverText = [regex]::Replace(
        $serverText,
        $controllerPattern,
        'DELIVERY_AUTOMATION = DeliveryAutomationController(ROOT, CONFIG, STORE)',
        1
    )
}
else {
    $serverText = Replace-RequiredText -Text $serverText `
        -Old "ROOT = Path(__file__).resolve().parent`nCONFIG = load_config(ROOT)`nSTORE = create_store(CONFIG)" `
        -New "ROOT = Path(__file__).resolve().parent`nCONFIG = load_config(ROOT)`nSTORE = create_store(CONFIG)`nDELIVERY_AUTOMATION = DeliveryAutomationController(ROOT, CONFIG, STORE)" `
        -Label "server startup"
}

# Install the SQLite-safe wrapper before the controller begins serving requests.
$serverText = [regex]::Replace(
    $serverText,
    'STORE = create_store\(CONFIG\)\n(?:install_safe_delivery_import\(STORE\)\n)?DELIVERY_AUTOMATION = DeliveryAutomationController\(ROOT, CONFIG, STORE\)',
    "STORE = create_store(CONFIG)`ninstall_safe_delivery_import(STORE)`nDELIVERY_AUTOMATION = DeliveryAutomationController(ROOT, CONFIG, STORE)",
    1
)
if (-not $serverText.Contains('install_safe_delivery_import(STORE)')) {
    throw "Could not install the safe delivery import wrapper before the automation controller."
}

# Make the normal Admin summary endpoint authoritative for the newest complete
# import run. This fixes first-load and full-page-refresh cases even when the
# automation add-on notification was missed while the browser was closed.
$legacyAdminSummaryRoute = @'
        if parsed.path == "/api/admin/summary":
            if not self.require_permission("view_admin"):
                return
            self.send_json(STORE.admin_summary())
            return
'@
$legacyAdminSummaryRoute = $legacyAdminSummaryRoute.Replace("`r`n", "`n")
$latestAdminSummaryRoute = @'
        if parsed.path == "/api/admin/summary":
            if not self.require_permission("view_admin"):
                return
            summary = dict(STORE.admin_summary() or {})
            latest_import = DELIVERY_AUTOMATION.get_latest_import_result()
            latest_results = list(latest_import.get("latestImportResults") or [])
            summary["recentImports"] = latest_results
            summary["latestImportResults"] = latest_results
            summary["lastCheckedAt"] = str(latest_import.get("lastCheckedAt") or "")
            summary["lastImportCheckedAt"] = str(latest_import.get("lastCheckedAt") or "")
            summary["latestImportRun"] = dict(latest_import.get("latestRun") or {})
            self.send_json(summary)
            return
'@
$latestAdminSummaryRoute = $latestAdminSummaryRoute.Replace("`r`n", "`n")
if ($serverText.Contains($legacyAdminSummaryRoute)) {
    $serverText = $serverText.Replace($legacyAdminSummaryRoute, $latestAdminSummaryRoute)
}
elseif (-not $serverText.Contains('latest_import = DELIVERY_AUTOMATION.get_latest_import_result()')) {
    throw "Could not find the Admin summary route for the v121 latest-import integration."
}

$getPendingAnchor = @'
        if parsed.path == "/api/notifications/pending":
            user = self.current_user()
            if not user:
                self.send_json({"error": "Authentication required"}, HTTPStatus.UNAUTHORIZED)
                return
            self.send_json({"notifications": STORE.get_pending_notifications(user["username"])})
            return
'@
$getPendingAnchor = $getPendingAnchor.Replace("`r`n", "`n")

if (-not $serverText.Contains('/api/notifications/history')) {
    $notificationHistoryBlock = $getPendingAnchor + @'

        if parsed.path == "/api/notifications/history":
            user = self.current_user()
            if not user:
                self.send_json({"error": "Authentication required"}, HTTPStatus.UNAUTHORIZED)
                return
            limit = parse_qs(parsed.query).get("limit", ["50"])[0]
            self.send_json({"notifications": STORE.get_notification_history(user["username"], int(limit or 50))})
            return
'@
    $notificationHistoryBlock = $notificationHistoryBlock.Replace("`r`n", "`n")
    $serverText = Replace-RequiredText -Text $serverText -Old $getPendingAnchor -New $notificationHistoryBlock -Label "notification history GET route"
}


if (-not $serverText.Contains('/api/delivery-list-updates')) {
    $notificationHistoryAnchor = @'
        if parsed.path == "/api/notifications/history":
            user = self.current_user()
            if not user:
                self.send_json({"error": "Authentication required"}, HTTPStatus.UNAUTHORIZED)
                return
            limit = parse_qs(parsed.query).get("limit", ["50"])[0]
            self.send_json({"notifications": STORE.get_notification_history(user["username"], int(limit or 50))})
            return
'@
    $notificationHistoryAnchor = $notificationHistoryAnchor.Replace("`r`n", "`n")
    $lineUpdateGetBlock = $notificationHistoryAnchor + @'

        if parsed.path == "/api/delivery-list-updates":
            user = self.require_permission("view_lists")
            if not user:
                return
            list_id = str(parse_qs(parsed.query).get("listId", [""])[0] or "").strip()
            if not list_id:
                self.send_json({"error": "listId is required"}, HTTPStatus.BAD_REQUEST)
                return
            if not STORE.user_can_access_list(user, list_id):
                self.send_json({"error": "Permission denied for this delivery-list stage"}, HTTPStatus.FORBIDDEN)
                return
            self.send_json(STORE.get_user_line_update_summary(user["username"], list_id))
            return
'@
    $lineUpdateGetBlock = $lineUpdateGetBlock.Replace("`r`n", "`n")
    $serverText = Replace-RequiredText -Text $serverText -Old $notificationHistoryAnchor -New $lineUpdateGetBlock -Label "per-user line update GET route"
}

if (-not $serverText.Contains('/api/admin/delivery-automation"')) {
    $automationGetAnchor = @'
        if parsed.path == "/api/notifications/history":
            user = self.current_user()
            if not user:
                self.send_json({"error": "Authentication required"}, HTTPStatus.UNAUTHORIZED)
                return
            limit = parse_qs(parsed.query).get("limit", ["50"])[0]
            self.send_json({"notifications": STORE.get_notification_history(user["username"], int(limit or 50))})
            return
'@
    $automationGetAnchor = $automationGetAnchor.Replace("`r`n", "`n")
    $automationGetBlock = $automationGetAnchor + @'

        if parsed.path == "/api/admin/delivery-automation":
            user = self.require_permission("import_delivery_lists")
            if not user:
                return
            self.send_json(DELIVERY_AUTOMATION.get_dashboard())
            return
'@
    $automationGetBlock = $automationGetBlock.Replace("`r`n", "`n")
    $serverText = Replace-RequiredText -Text $serverText -Old $automationGetAnchor -New $automationGetBlock -Label "automation GET route"
}


if (-not $serverText.Contains('/api/admin/delivery-automation/recent-imports')) {
    $recentImportAnchor = @'
        if parsed.path == "/api/admin/delivery-automation":
            user = self.require_permission("import_delivery_lists")
            if not user:
                return
            self.send_json(DELIVERY_AUTOMATION.get_dashboard())
            return

'@
    $recentImportAnchor = $recentImportAnchor.Replace("`r`n", "`n")
    $recentImportBlock = @'
        if parsed.path == "/api/admin/delivery-automation":
            user = self.require_permission("import_delivery_lists")
            if not user:
                return
            self.send_json(DELIVERY_AUTOMATION.get_dashboard())
            return

        if parsed.path == "/api/admin/delivery-automation/recent-imports":
            user = self.require_permission("import_delivery_lists")
            if not user:
                return
            params = parse_qs(parsed.query)
            self.send_json(
                DELIVERY_AUTOMATION.get_import_history(
                    page=int(params.get("page", ["1"])[0] or 1),
                    page_size=int(params.get("pageSize", params.get("limit", ["20"]))[0] or 20),
                    query=params.get("q", [""])[0],
                    classification=params.get("classification", [""])[0],
                    date_from=params.get("dateFrom", [""])[0],
                    date_to=params.get("dateTo", [""])[0],
                )
            )
            return

'@
    $recentImportBlock = $recentImportBlock.Replace("`r`n", "`n")
    $serverText = Replace-RequiredText -Text $serverText -Old $recentImportAnchor -New $recentImportBlock -Label "automation recent-import GET route"
}

if (-not $serverText.Contains('/api/admin/delivery-automation/latest-import')) {
    $latestImportAnchor = @'
        if parsed.path == "/api/admin/delivery-automation/recent-imports":
            user = self.require_permission("import_delivery_lists")
            if not user:
                return
            params = parse_qs(parsed.query)
            self.send_json(
                DELIVERY_AUTOMATION.get_import_history(
                    page=int(params.get("page", ["1"])[0] or 1),
                    page_size=int(params.get("pageSize", params.get("limit", ["20"]))[0] or 20),
                    query=params.get("q", [""])[0],
                    classification=params.get("classification", [""])[0],
                    date_from=params.get("dateFrom", [""])[0],
                    date_to=params.get("dateTo", [""])[0],
                )
            )
            return
'@
    $latestImportAnchor = $latestImportAnchor.Replace("`r`n", "`n")
    $latestImportBlock = $latestImportAnchor + @'

        if parsed.path == "/api/admin/delivery-automation/latest-import":
            user = self.require_permission("import_delivery_lists")
            if not user:
                return
            self.send_json(DELIVERY_AUTOMATION.get_latest_import_result())
            return
'@
    $latestImportBlock = $latestImportBlock.Replace("`r`n", "`n")
    $serverText = Replace-RequiredText -Text $serverText -Old $latestImportAnchor -New $latestImportBlock -Label "automation latest-import GET route"
}

$ackAnchor = @'
            if parsed.path == "/api/notifications/acknowledge":
                user = self.current_user()
                if not user:
                    self.send_json({"error": "Authentication required"}, HTTPStatus.UNAUTHORIZED)
                    return
                self.send_json(
                    STORE.acknowledge_notification(
                        int(data.get("notificationId") or 0),
                        user["username"],
                    )
                )
                return
'@
$ackAnchor = $ackAnchor.Replace("`r`n", "`n")
if (-not $serverText.Contains('/api/notifications/read-all')) {
    $readAllBlock = $ackAnchor + @'

            if parsed.path == "/api/notifications/read-all":
                user = self.current_user()
                if not user:
                    self.send_json({"error": "Authentication required"}, HTTPStatus.UNAUTHORIZED)
                    return
                self.send_json(STORE.mark_all_notifications_read(user["username"]))
                return
'@
    $readAllBlock = $readAllBlock.Replace("`r`n", "`n")
    $serverText = Replace-RequiredText -Text $serverText -Old $ackAnchor -New $readAllBlock -Label "notification read-all POST route"
}


if (-not $serverText.Contains('/api/delivery-list-updates/acknowledge')) {
    $readAllAnchor = @'
            if parsed.path == "/api/notifications/read-all":
                user = self.current_user()
                if not user:
                    self.send_json({"error": "Authentication required"}, HTTPStatus.UNAUTHORIZED)
                    return
                self.send_json(STORE.mark_all_notifications_read(user["username"]))
                return
'@
    $readAllAnchor = $readAllAnchor.Replace("`r`n", "`n")
    $lineUpdatePostBlock = $readAllAnchor + @'

            if parsed.path == "/api/delivery-list-updates/acknowledge":
                user = self.require_permission("view_lists")
                if not user:
                    return
                list_id = str(data.get("listId") or "").strip()
                if not list_id:
                    self.send_json({"error": "listId is required"}, HTTPStatus.BAD_REQUEST)
                    return
                if not STORE.user_can_access_list(user, list_id):
                    self.send_json({"error": "Permission denied for this delivery-list stage"}, HTTPStatus.FORBIDDEN)
                    return
                notice_ids = data.get("noticeIds") if isinstance(data.get("noticeIds"), list) else None
                self.send_json(STORE.acknowledge_user_line_updates(user["username"], list_id, notice_ids))
                return
'@
    $lineUpdatePostBlock = $lineUpdatePostBlock.Replace("`r`n", "`n")
    $serverText = Replace-RequiredText -Text $serverText -Old $readAllAnchor -New $lineUpdatePostBlock -Label "per-user line update acknowledgement route"
}

if (-not $serverText.Contains('/api/admin/delivery-automation/run')) {
    $postAnchor = @'
            if parsed.path == "/api/import/folder":
                user = self.require_permission("import_delivery_lists")
                if not user:
                    return
                data["user"] = user["username"]
                self.send_json(STORE.import_delivery_folder(data))
                return
'@
    $postAnchor = $postAnchor.Replace("`r`n", "`n")
    $postBlock = $postAnchor + @'

            if parsed.path == "/api/admin/delivery-automation/run":
                user = self.require_permission("import_delivery_lists")
                if not user:
                    return
                self.send_json(
                    DELIVERY_AUTOMATION.start_run(data, user["username"]),
                    HTTPStatus.ACCEPTED,
                )
                return

            if parsed.path == "/api/admin/delivery-automation/config":
                user = self.require_permission("import_delivery_lists")
                if not user:
                    return
                self.send_json(DELIVERY_AUTOMATION.save_settings(data, user["username"]))
                return

            if parsed.path == "/api/admin/delivery-automation/schedule/install":
                if not self.require_permission("import_delivery_lists"):
                    return
                self.send_json(DELIVERY_AUTOMATION.install_schedule())
                return

            if parsed.path == "/api/admin/delivery-automation/schedule/remove":
                if not self.require_permission("import_delivery_lists"):
                    return
                self.send_json(DELIVERY_AUTOMATION.remove_schedule())
                return
'@
    $postBlock = $postBlock.Replace("`r`n", "`n")
    $serverText = Replace-RequiredText -Text $serverText -Old $postAnchor -New $postBlock -Label "automation POST routes"
}

$storeText = [IO.File]::ReadAllText($storePath).Replace("`r`n", "`n")
if (-not $storeText.Contains('def _migration_003_v120_user_line_updates')) {
    $migrationMethod = @'
    def _migration_003_v120_user_line_updates(self, con: sqlite3.Connection) -> None:
        """Add persistent per-user review state for current/future import changes."""
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS line_update_notices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                line_item_id TEXT NOT NULL,
                list_id TEXT NOT NULL,
                delivery_date TEXT NOT NULL,
                change_type TEXT NOT NULL CHECK (change_type IN ('new', 'updated')),
                change_token TEXT NOT NULL,
                source_hash TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                UNIQUE(line_item_id, change_type, change_token)
            );

            CREATE TABLE IF NOT EXISTS line_update_receipts (
                notice_id INTEGER NOT NULL REFERENCES line_update_notices(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                seen_at TEXT NOT NULL,
                PRIMARY KEY (notice_id, user_id)
            );

            CREATE INDEX IF NOT EXISTS idx_line_update_notices_list_date
                ON line_update_notices(list_id, delivery_date, created_at DESC, id DESC);
            CREATE INDEX IF NOT EXISTS idx_line_update_receipts_user
                ON line_update_receipts(user_id, notice_id);
            """
        )

'@
    $migrationMethod = $migrationMethod.Replace("`r`n", "`n")
    $migrationMethodAnchor = "    def clone_item_for_list("
    if (-not $storeText.Contains($migrationMethodAnchor)) {
        throw "Could not find the delivery-store migration insertion anchor."
    }
    $storeText = $storeText.Replace($migrationMethodAnchor, $migrationMethod + $migrationMethodAnchor)
}


# Treat a delivery-list stage restored from inactive/deleted state as New. The
# maintained importer previously reactivated the row correctly but classified
# it as No Changes because the physical database row already existed.
if (-not $storeText.Contains("reactivated_list_ids = {")) {
    $existingListAnchor = @'
            existing_list_ids = {
                row["id"]
                for row in con.execute(
                    "SELECT id FROM delivery_lists WHERE id IN ({})".format(",".join("?" for _ in definitions)),
                    definition_ids,
                ).fetchall()
            }
'@
    $existingListAnchor = $existingListAnchor.Replace("`r`n", "`n")
    $existingListBlock = @'
            existing_list_rows = con.execute(
                "SELECT id, status FROM delivery_lists WHERE id IN ({})".format(",".join("?" for _ in definitions)),
                definition_ids,
            ).fetchall()
            active_existing_list_ids = {
                row["id"]
                for row in existing_list_rows
                if str(row["status"] or "").strip().lower() == "active"
            }
            reactivated_list_ids = {
                row["id"]
                for row in existing_list_rows
                if str(row["status"] or "").strip().lower() != "active"
            }
'@
    $existingListBlock = $existingListBlock.Replace("`r`n", "`n")
    $storeText = Replace-RequiredText -Text $storeText -Old $existingListAnchor -New $existingListBlock -Label "active delivery-list import classification"

    $stageSummaryAnchor = @'
                summary = self.upsert_delivery_list(con, list_id, label, str(payload["deliveryDate"]), stage, scanner, items, replace_items=True)
                stage_summaries.append(summary)
                if summary["created"] or summary["changedLineCount"] or summary["changedPieceQty"]:
                    changed_list_ids.append(list_id)
                    event_type = "import" if summary["created"] else "update"
'@
    $stageSummaryAnchor = $stageSummaryAnchor.Replace("`r`n", "`n")
    $stageSummaryBlock = @'
                summary = self.upsert_delivery_list(con, list_id, label, str(payload["deliveryDate"]), stage, scanner, items, replace_items=True)
                stage_reactivated = list_id in reactivated_list_ids
                summary["reactivated"] = stage_reactivated
                stage_summaries.append(summary)
                if summary["created"] or stage_reactivated or summary["changedLineCount"] or summary["changedPieceQty"]:
                    changed_list_ids.append(list_id)
                    event_type = "import" if summary["created"] or stage_reactivated else "update"
'@
    $stageSummaryBlock = $stageSummaryBlock.Replace("`r`n", "`n")
    $storeText = Replace-RequiredText -Text $storeText -Old $stageSummaryAnchor -New $stageSummaryBlock -Label "reactivated stage summary"

    $changeCountAnchor = @'
                "createdCount": sum(1 for summary in stage_summaries if summary["created"]),
                "updatedCount": sum(1 for summary in stage_summaries if not summary["created"] and (summary["changedLineCount"] or summary["changedPieceQty"])),
'@
    $changeCountAnchor = $changeCountAnchor.Replace("`r`n", "`n")
    $changeCountBlock = @'
                "createdCount": sum(1 for summary in stage_summaries if summary["created"] or summary.get("reactivated")),
                "reactivatedCount": sum(1 for summary in stage_summaries if summary.get("reactivated")),
                "reactivatedListIds": [summary["listId"] for summary in stage_summaries if summary.get("reactivated")],
                "updatedCount": sum(1 for summary in stage_summaries if not summary["created"] and not summary.get("reactivated") and (summary["changedLineCount"] or summary["changedPieceQty"])),
'@
    $changeCountBlock = $changeCountBlock.Replace("`r`n", "`n")
    $storeText = Replace-RequiredText -Text $storeText -Old $changeCountAnchor -New $changeCountBlock -Label "import change summary counts"

    $returnCountAnchor = @'
        created_count = sum(1 for definition in definitions if definition[0] not in existing_list_ids)
        updated_count = sum(1 for summary in stage_summaries if not summary["created"] and (summary["changedLineCount"] or summary["changedPieceQty"]))
'@
    $returnCountAnchor = $returnCountAnchor.Replace("`r`n", "`n")
    $returnCountBlock = @'
        created_count = sum(1 for definition in definitions if definition[0] not in active_existing_list_ids)
        reactivated_count = sum(1 for definition in definitions if definition[0] in reactivated_list_ids)
        updated_count = sum(1 for summary in stage_summaries if not summary["created"] and not summary.get("reactivated") and (summary["changedLineCount"] or summary["changedPieceQty"]))
'@
    $returnCountBlock = $returnCountBlock.Replace("`r`n", "`n")
    $storeText = Replace-RequiredText -Text $storeText -Old $returnCountAnchor -New $returnCountBlock -Label "import return counts"

    $returnPayloadAnchor = @'
            "createdCount": created_count,
            "updatedCount": updated_count,
'@
    $returnPayloadAnchor = $returnPayloadAnchor.Replace("`r`n", "`n")
    $returnPayloadBlock = @'
            "createdCount": created_count,
            "reactivatedCount": reactivated_count,
            "reactivatedListIds": sorted(reactivated_list_ids),
            "updatedCount": updated_count,
'@
    $returnPayloadBlock = $returnPayloadBlock.Replace("`r`n", "`n")
    $storeText = Replace-RequiredText -Text $storeText -Old $returnPayloadAnchor -New $returnPayloadBlock -Label "import return reactivated fields"
}

# Surface safe in-place removed-line counts in the maintained import audit.
if (-not $storeText.Contains('"removedLineCount": sum(int(summary.get("removedLineCount")')) {
    $changePieceAnchor = @'
                "changedPieceQty": sum(int(summary["changedPieceQty"] or 0) for summary in stage_summaries),
                "stages": stage_summaries,
'@
    $changePieceAnchor = $changePieceAnchor.Replace("`r`n", "`n")
    $changePieceBlock = @'
                "changedPieceQty": sum(int(summary["changedPieceQty"] or 0) for summary in stage_summaries),
                "removedLineCount": sum(int(summary.get("removedLineCount") or 0) for summary in stage_summaries),
                "removedPieceQty": sum(int(summary.get("removedPieceQty") or 0) for summary in stage_summaries),
                "stages": stage_summaries,
'@
    $changePieceBlock = $changePieceBlock.Replace("`r`n", "`n")
    $storeText = Replace-RequiredText -Text $storeText -Old $changePieceAnchor -New $changePieceBlock -Label "safe import removed-line audit counts"

    $returnPieceAnchor = @'
            "changedPieceQty": sum(int(summary["changedPieceQty"] or 0) for summary in stage_summaries),
            "printCandidates": self.print_candidates_from_payload(payload, changed_list_ids, source_name, stage_summaries),
'@
    $returnPieceAnchor = $returnPieceAnchor.Replace("`r`n", "`n")
    $returnPieceBlock = @'
            "changedPieceQty": sum(int(summary["changedPieceQty"] or 0) for summary in stage_summaries),
            "removedLineCount": sum(int(summary.get("removedLineCount") or 0) for summary in stage_summaries),
            "removedPieceQty": sum(int(summary.get("removedPieceQty") or 0) for summary in stage_summaries),
            "printCandidates": self.print_candidates_from_payload(payload, changed_list_ids, source_name, stage_summaries),
'@
    $returnPieceBlock = $returnPieceBlock.Replace("`r`n", "`n")
    $storeText = Replace-RequiredText -Text $storeText -Old $returnPieceAnchor -New $returnPieceBlock -Label "safe import removed-line return counts"
}

if (-not $storeText.Contains('"reactivatedCount": result.get("reactivatedCount", 0)')) {
    $folderFileResultAnchor = @'
                    "createdCount": result["createdCount"],
                    "updatedCount": result["updatedCount"],
'@
    $folderFileResultAnchor = $folderFileResultAnchor.Replace("`r`n", "`n")
    $folderFileResultBlock = @'
                    "createdCount": result["createdCount"],
                    "reactivatedCount": result.get("reactivatedCount", 0),
                    "updatedCount": result["updatedCount"],
'@
    $folderFileResultBlock = $folderFileResultBlock.Replace("`r`n", "`n")
    $storeText = Replace-RequiredText -Text $storeText -Old $folderFileResultAnchor -New $folderFileResultBlock -Label "folder import reactivated count"
}

if (-not $storeText.Contains('def get_notification_history(')) {
    $notificationMethods = @'
    def get_notification_history(self, username: str, limit: int = 50) -> list[dict[str, Any]]:
        """Return recent non-scan application notifications for the bell inbox.

        Scan events live in scan_events and are deliberately excluded. Notification
        receipts affect popup delivery only; acknowledged items remain visible here
        until their normal expiration so scanning cannot erase update history.
        """
        clean_username = str(username or "").strip()
        clean_limit = max(1, min(int(limit or 50), 200))
        if not clean_username:
            return []
        with self.connect() as con:
            user = con.execute(
                "SELECT id FROM users WHERE lower(username) = lower(?) AND active = 1",
                (clean_username,),
            ).fetchone()
            if not user:
                return []
            rows = con.execute(
                """
                SELECT n.*,
                       CASE WHEN r.notification_id IS NULL THEN 0 ELSE 1 END AS is_read
                FROM app_notifications n
                LEFT JOIN app_notification_receipts r
                  ON r.notification_id = n.id AND r.user_id = ?
                WHERE n.active = 1
                  AND (COALESCE(n.expires_at, '') = '' OR n.expires_at > ?)
                ORDER BY n.id DESC
                """,
                (user["id"], now_iso()),
            ).fetchall()
        notifications = []
        for row in list(rows)[:clean_limit]:
            try:
                payload = json.loads(row["payload_json"] or "{}")
            except json.JSONDecodeError:
                payload = {}
            notifications.append(
                {
                    "id": row["id"],
                    "type": row["notification_type"],
                    "title": row["title"],
                    "message": row["message"],
                    "details": payload,
                    "createdBy": row["created_by"],
                    "createdAt": row["created_at"],
                    "expiresAt": row["expires_at"],
                    "isRead": bool(row["is_read"]),
                }
            )
        return notifications

    def mark_all_notifications_read(self, username: str) -> dict[str, Any]:
        """Acknowledge all currently visible bell notifications for one user."""
        notifications = self.get_notification_history(username, 200)
        marked = 0
        for notification in notifications:
            if notification.get("isRead"):
                continue
            self.acknowledge_notification(int(notification.get("id") or 0), username)
            marked += 1
        return {"ok": True, "markedRead": marked}

'@
    $notificationMethods = $notificationMethods.Replace("`r`n", "`n")
    $ackMethodAnchor = "    def acknowledge_notification("
    if (-not $storeText.Contains($ackMethodAnchor)) {
        throw "Could not find the notification acknowledgement method in delivery_store.py."
    }
    $storeText = $storeText.Replace($ackMethodAnchor, $notificationMethods + $ackMethodAnchor)
}

Copy-Item -LiteralPath (Join-Path $PSScriptRoot "delivery_automation_control.py") -Destination (Join-Path $resolvedRoot "delivery_automation_control.py") -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "delivery-automation-ui.js") -Destination (Join-Path $resolvedRoot "delivery-automation-ui.js") -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "delivery-automation-ui.css") -Destination (Join-Path $resolvedRoot "delivery-automation-ui.css") -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "notification-center-ui.js") -Destination (Join-Path $resolvedRoot "notification-center-ui.js") -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "notification-center-ui.css") -Destination (Join-Path $resolvedRoot "notification-center-ui.css") -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "delivery_import_safety.py") -Destination (Join-Path $resolvedRoot "delivery_import_safety.py") -Force
[IO.File]::WriteAllText($indexPath, $indexText, [Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText($appPath, $appText, [Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText($serverPath, $serverText, [Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText($storePath, $storeText, [Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText($databaseContractPath, $databaseContractText, [Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText($databaseMigrationsPath, $databaseMigrationsText, [Text.UTF8Encoding]::new($false))

$readmeText = [IO.File]::ReadAllText($readmePath)
$readmeText = [regex]::Replace($readmeText, 'Current maintained release:\s*\*\*v\d+\*\*\.', 'Current maintained release: **v121**.', 1)
if (-not $readmeText.Contains('v121 centers delivery-list update toasts')) {
    $marker = "Current maintained release: **v121**. SQLite remains the active/default backend.`r`n"
    if (-not $readmeText.Contains($marker)) {
        $marker = "Current maintained release: **v121**. SQLite remains the active/default backend.`n"
    }
    $addition = @'

v121 centers delivery-list update toasts at the bottom of the page for 20 seconds, marks bell notifications read when the notification menu opens, removes the manual read control, stamps every latest-run result including No Changes with the actual check completion time, and makes per-user Mark reviewed clear the visible New/Updated rows immediately while verifying the exact notice receipts on the server.
'@
    $readmeText = $readmeText.Replace($marker, $marker + $addition)
}
[IO.File]::WriteAllText($readmePath, $readmeText, [Text.UTF8Encoding]::new($false))

$changelogText = [IO.File]::ReadAllText($changelogPath)
if (-not $changelogText.Contains('## v121')) {
    $entry = @'
## v121 - Notification Timing and Review Reliability

- Moved the delivery-list import toast to the bottom center of the page and extended it to 20 seconds.
- Opening the bell notification menu now marks all currently displayed notifications read for that user.
- Removed the Mark all read control and the per-item Mark read wording from the notification menu.
- Stamps every delivery-list result from the newest run with the run completion time, including No Changes results and their stage details.
- Sends the exact reviewed notice IDs when Mark reviewed is selected and verifies that no unseen notices remain.
- Reloads the selected delivery list from the authenticated API after review and immediately removes New Line / Updated Line labels from the current user's visible rows.
- Preserved per-user isolation, current/future-date limits, append-only scan history, scanning quantities, racks, bays, and import audit history.

'@
    $changelogText = $entry + $changelogText
    [IO.File]::WriteAllText($changelogPath, $changelogText, [Text.UTF8Encoding]::new($false))
}

Write-Host "v121 project integration applied successfully." -ForegroundColor Green
Write-Host "Backups: $backupRoot"
Write-Host "Restart the Delivery List Scanner web app before testing automation toasts, bell navigation, and per-user update review."

