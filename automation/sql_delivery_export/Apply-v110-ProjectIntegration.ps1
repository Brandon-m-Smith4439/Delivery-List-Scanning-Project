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
if ($release -gt 110) {
    throw "The selected project is v$release. This v110 installer will not modify a newer release."
}

$requiredProjectFiles = @("index.html", "server.py", "delivery_store.py", "README.md", "README_CHANGELOG.md")
foreach ($name in $requiredProjectFiles) {
    $path = Join-Path $resolvedRoot $name
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required project file is missing: $path"
    }
}

$backupRoot = Join-Path $WorkingRoot ("Backups\v110-project-integration-{0}" -f (Get-Date -Format "yyyyMMdd-HHmmss"))
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
$serverPath = Join-Path $resolvedRoot "server.py"
$storePath = Join-Path $resolvedRoot "delivery_store.py"
$readmePath = Join-Path $resolvedRoot "README.md"
$changelogPath = Join-Path $resolvedRoot "README_CHANGELOG.md"

# Keep the main application assets in place and replace only the isolated v107-v110 add-on references.
$indexText = [IO.File]::ReadAllText($indexPath)
$indexText = [regex]::Replace($indexText, '\s*<link rel="stylesheet" href="delivery-automation-ui\.css\?v=[^"]+">', '')
$indexText = [regex]::Replace($indexText, '\s*<link rel="stylesheet" href="notification-center-ui\.css\?v=[^"]+">', '')
$indexText = [regex]::Replace($indexText, '\s*<script src="delivery-automation-ui\.js\?v=[^"]+"></script>', '')
$indexText = [regex]::Replace($indexText, '\s*<script src="notification-center-ui\.js\?v=[^"]+"></script>', '')
$indexText = [regex]::Replace($indexText, '<link rel="stylesheet" href="styles\.css\?v=[^"]+">', '<link rel="stylesheet" href="styles.css?v=20260722-v110">', 1)
$indexText = [regex]::Replace($indexText, '<script src="app\.js\?v=[^"]+"></script>', '<script src="app.js?v=20260722-v110"></script>', 1)
$indexText = Add-AssetAfterMatch -Text $indexText `
    -Pattern '<link rel="stylesheet" href="styles\.css\?v=20260722-v110">' `
    -Addition ("`r`n    " + '<link rel="stylesheet" href="delivery-automation-ui.css?v=20260722-v110">' + "`r`n    " + '<link rel="stylesheet" href="notification-center-ui.css?v=20260722-v110">') `
    -Label "main stylesheet"
$indexText = Add-AssetAfterMatch -Text $indexText `
    -Pattern '<script src="app\.js\?v=20260722-v110"></script>' `
    -Addition ("`r`n  " + '<script src="delivery-automation-ui.js?v=20260722-v110"></script>' + "`r`n  " + '<script src="notification-center-ui.js?v=20260722-v110"></script>') `
    -Label "main JavaScript"

$serverText = [IO.File]::ReadAllText($serverPath).Replace("`r`n", "`n")
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
            limit = parse_qs(parsed.query).get("limit", ["20"])[0]
            self.send_json(DELIVERY_AUTOMATION.get_recent_imports(int(limit or 20)))
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
[IO.File]::WriteAllText($serverPath, $serverText, [Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText($storePath, $storeText, [Text.UTF8Encoding]::new($false))

$readmeText = [IO.File]::ReadAllText($readmePath)
$readmeText = [regex]::Replace($readmeText, 'Current maintained release:\s*\*\*v\d+\*\*\.', 'Current maintained release: **v110**.', 1)
if (-not $readmeText.Contains('v110 fixes UNC workbook publishing and adds complete live automation logs')) {
    $marker = "Current maintained release: **v110**. SQLite remains the active/default backend.`r`n"
    if (-not $readmeText.Contains($marker)) {
        $marker = "Current maintained release: **v110**. SQLite remains the active/default backend.`n"
    }
    $addition = @'

v110 fixes UNC workbook publishing and adds complete live automation logs. SQL-generated workbooks now use a network-share-compatible staged overwrite instead of `System.IO.File.Replace`, the **Status & Logs** page streams every active output line and retains the complete per-run log, and notification publishing uses a JSON request file for reliable Windows argument handling. v109 authoritative recent-import classifications and all scanner workflows remain preserved.
'@
    $readmeText = $readmeText.Replace($marker, $marker + $addition)
}
[IO.File]::WriteAllText($readmePath, $readmeText, [Text.UTF8Encoding]::new($false))

$changelogText = [IO.File]::ReadAllText($changelogPath)
if (-not $changelogText.Contains('## v110')) {
    $entry = @'
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

'@
    $changelogText = $entry + $changelogText
    [IO.File]::WriteAllText($changelogPath, $changelogText, [Text.UTF8Encoding]::new($false))
}

Write-Host "v110 project integration applied successfully." -ForegroundColor Green
Write-Host "Backups: $backupRoot"
Write-Host "Restart the Delivery List Scanner web app before reviewing the control center, notification bell, and corrected recent import history."
