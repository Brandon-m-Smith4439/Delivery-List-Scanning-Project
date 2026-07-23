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
if ($release -gt 116) {
    throw "The selected project is v$release. This v116 installer will not modify a newer release."
}

$requiredProjectFiles = @("index.html", "app.js", "server.py", "delivery_store.py", "README.md", "README_CHANGELOG.md")
foreach ($name in $requiredProjectFiles) {
    $path = Join-Path $resolvedRoot $name
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required project file is missing: $path"
    }
}

$backupRoot = Join-Path $WorkingRoot ("Backups\v116-project-integration-{0}" -f (Get-Date -Format "yyyyMMdd-HHmmss"))
[void](New-Item -ItemType Directory -Path $backupRoot -Force)
foreach ($name in $requiredProjectFiles) {
    Copy-Item -LiteralPath (Join-Path $resolvedRoot $name) -Destination (Join-Path $backupRoot $name) -Force
}
foreach ($name in @(
    "delivery_automation_control.py",
    "delivery-automation-ui.js",
    "delivery-automation-ui.css",
    "notification-center-ui.js",
    "notification-center-ui.css"
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
$readmePath = Join-Path $resolvedRoot "README.md"
$changelogPath = Join-Path $resolvedRoot "README_CHANGELOG.md"

# Keep the main application assets in place and replace only the isolated v107-v116 add-on references.
$indexText = [IO.File]::ReadAllText($indexPath)
$indexText = [regex]::Replace($indexText, '\s*<link rel="stylesheet" href="delivery-automation-ui\.css\?v=[^"]+">', '')
$indexText = [regex]::Replace($indexText, '\s*<link rel="stylesheet" href="notification-center-ui\.css\?v=[^"]+">', '')
$indexText = [regex]::Replace($indexText, '\s*<script src="delivery-automation-ui\.js\?v=[^"]+"></script>', '')
$indexText = [regex]::Replace($indexText, '\s*<script src="notification-center-ui\.js\?v=[^"]+"></script>', '')
$indexText = [regex]::Replace($indexText, '<link rel="stylesheet" href="styles\.css\?v=[^"]+">', '<link rel="stylesheet" href="styles.css?v=20260723-v116">', 1)
$indexText = [regex]::Replace($indexText, '<script src="app\.js\?v=[^"]+"></script>', '<script src="app.js?v=20260723-v116"></script>', 1)
$indexText = Add-AssetAfterMatch -Text $indexText `
    -Pattern '<link rel="stylesheet" href="styles\.css\?v=20260723-v116">' `
    -Addition ("`r`n    " + '<link rel="stylesheet" href="delivery-automation-ui.css?v=20260723-v116">' + "`r`n    " + '<link rel="stylesheet" href="notification-center-ui.css?v=20260723-v116">') `
    -Label "main stylesheet"
$indexText = Add-AssetAfterMatch -Text $indexText `
    -Pattern '<script src="app\.js\?v=20260723-v116"></script>' `
    -Addition ("`r`n  " + '<script src="delivery-automation-ui.js?v=20260723-v116"></script>' + "`r`n  " + '<script src="notification-center-ui.js?v=20260723-v116"></script>') `
    -Label "main JavaScript"


# Restore the original Delivery List Management overview and move audit history
# into its own modal. The automation GUI now owns folder/date settings, so the
# obsolete inline settings disclosure is removed from the Admin card.
$deliveryManagementHeadingPattern = '(?s)<div class="section-heading">\s*<h2>Delivery List Management</h2>\s*<button class="link-button" type="button" data-admin-modal="deliveryLists">Edit delivery lists</button>\s*</div>'
$deliveryManagementHeading = @'
            <div class="section-heading">
              <h2>Delivery List Management</h2>
              <div class="section-actions">
                <button class="link-button" id="importHistoryBtn" type="button">Import history</button>
                <button class="link-button" type="button" data-admin-modal="deliveryLists">Edit delivery lists</button>
              </div>
            </div>
'@
$deliveryManagementHeading = $deliveryManagementHeading.Replace("`r`n", "`n").TrimEnd("`n")
if ([regex]::IsMatch($indexText, $deliveryManagementHeadingPattern)) {
    $indexText = [regex]::Replace($indexText, $deliveryManagementHeadingPattern, $deliveryManagementHeading, 1)
}
elseif (-not $indexText.Contains('id="importHistoryBtn"')) {
    throw "Could not find the Delivery List Management heading for the v116 Import History button."
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
$appText = $appText.Replace("DLS_AUTOMATION_LIST_REFRESH_BRIDGE_V115", "DLS_AUTOMATION_LIST_REFRESH_BRIDGE_V116")

if (-not $appText.Contains("DLS_AUTOMATION_LIST_REFRESH_BRIDGE_V116")) {
    $appStateAnchor = @'
  lastGlassFilterSignature: "",
};
'@
    $appStateAnchor = $appStateAnchor.Replace("`r`n", "`n")
    $appRefreshBridge = @'
  lastGlassFilterSignature: "",
};

// DLS_AUTOMATION_LIST_REFRESH_BRIDGE_V116
// Update delivery-list metadata and selectors silently. Never dispatch the
// date/stage change events here: the app's normal handlers may navigate to the
// Scan page and can interrupt an operator who is working elsewhere.
function dlsAutomationDateLabel(value) {
  const parsed = new Date(`${value}T12:00:00`);
  return Number.isNaN(parsed.getTime())
    ? value
    : parsed.toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" });
}

function dlsAutomationStageLabel(item) {
  return String(item.label || item.stage || item.scanner || item.id || "Delivery-list stage");
}

function dlsAutomationApplyDeliveryCatalog(refreshedLists) {
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

  document.dispatchEvent(new CustomEvent("dls:delivery-list-catalog-synced", {
    detail: {
      listCount: state.lists.length,
      selectedDate,
      selectedListId: desiredListId,
    },
  }));
}

document.addEventListener("dls:delivery-list-data-refreshed", async (event) => {
  const detail = event.detail && typeof event.detail === "object" ? event.detail : {};
  if (Array.isArray(detail.recentImports)) {
    state.adminRecentImports = detail.recentImports.slice();
  }

  if (Array.isArray(detail.lists)) {
    dlsAutomationApplyDeliveryCatalog(detail.lists);
    return;
  }

  try {
    const response = await fetch("/api/delivery-lists", {
      credentials: "same-origin",
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
    const payload = await response.json();
    if (response.ok && Array.isArray(payload.lists)) {
      dlsAutomationApplyDeliveryCatalog(payload.lists);
    }
  } catch {
    // The next background catalog poll will retry without disrupting scanning.
  }
});
'@
    $appRefreshBridge = $appRefreshBridge.Replace("`r`n", "`n")
    $appText = Replace-RequiredText -Text $appText -Old $appStateAnchor -New $appRefreshBridge -Label "app delivery-list state anchor"
}

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
[IO.File]::WriteAllText($indexPath, $indexText, [Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText($appPath, $appText, [Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText($serverPath, $serverText, [Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText($storePath, $storeText, [Text.UTF8Encoding]::new($false))

$readmeText = [IO.File]::ReadAllText($readmePath)
$readmeText = [regex]::Replace($readmeText, 'Current maintained release:\s*\*\*v\d+\*\*\.', 'Current maintained release: **v116**.', 1)
if (-not $readmeText.Contains('v116 restores the original Delivery List Management overview')) {
    $marker = "Current maintained release: **v116**. SQLite remains the active/default backend.`r`n"
    if (-not $readmeText.Contains($marker)) {
        $marker = "Current maintained release: **v116**. SQLite remains the active/default backend.`n"
    }
    $addition = @'

v116 restores the original Delivery List Management overview and moves Import Audit History into a dedicated searchable modal. History is newest-first, paginated at 20 rows by default, supports 20/50/100 rows per page, and can be filtered by status, delivery date, filename, stage, or user. The obsolete inline import-folder/date settings are removed because those controls now live in the Automation Control Center.
'@
    $readmeText = $readmeText.Replace($marker, $marker + $addition)
}
[IO.File]::WriteAllText($readmePath, $readmeText, [Text.UTF8Encoding]::new($false))

$changelogText = [IO.File]::ReadAllText($changelogPath)
if (-not $changelogText.Contains('## v116')) {
    $entry = @'
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

'@
    $changelogText = $entry + $changelogText
    [IO.File]::WriteAllText($changelogPath, $changelogText, [Text.UTF8Encoding]::new($false))
}

Write-Host "v116 project integration applied successfully." -ForegroundColor Green
Write-Host "Backups: $backupRoot"
Write-Host "Restart the Delivery List Scanner web app before reviewing the control center, notification bell, and dedicated import audit history."
