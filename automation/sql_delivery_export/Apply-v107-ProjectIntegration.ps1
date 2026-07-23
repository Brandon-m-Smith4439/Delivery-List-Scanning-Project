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

$resolvedRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$release = Get-ProjectRelease -Root $resolvedRoot
if ($release -lt 105) {
    throw "This integration requires scanner v105 or newer. Selected project is v$release."
}
if ($release -gt 107) {
    throw "The selected project is v$release. This v107 installer will not modify a newer release."
}

$requiredProjectFiles = @("index.html", "server.py", "README.md", "README_CHANGELOG.md")
foreach ($name in $requiredProjectFiles) {
    $path = Join-Path $resolvedRoot $name
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required project file is missing: $path"
    }
}

$backupRoot = Join-Path $WorkingRoot ("Backups\v107-project-integration-{0}" -f (Get-Date -Format "yyyyMMdd-HHmmss"))
[void](New-Item -ItemType Directory -Path $backupRoot -Force)
foreach ($name in $requiredProjectFiles) {
    Copy-Item -LiteralPath (Join-Path $resolvedRoot $name) -Destination (Join-Path $backupRoot $name) -Force
}
foreach ($name in @("delivery_automation_control.py", "delivery-automation-ui.js", "delivery-automation-ui.css")) {
    $existing = Join-Path $resolvedRoot $name
    if (Test-Path -LiteralPath $existing -PathType Leaf) {
        Copy-Item -LiteralPath $existing -Destination (Join-Path $backupRoot $name) -Force
    }
}

$indexPath = Join-Path $resolvedRoot "index.html"
$serverPath = Join-Path $resolvedRoot "server.py"
$readmePath = Join-Path $resolvedRoot "README.md"
$changelogPath = Join-Path $resolvedRoot "README_CHANGELOG.md"

$indexText = [IO.File]::ReadAllText($indexPath)
if (-not $indexText.Contains('delivery-automation-ui.js')) {
    $indexText = [regex]::Replace(
        $indexText,
        '<link rel="stylesheet" href="styles\.css\?v=[^"]+">',
        '<link rel="stylesheet" href="styles.css?v=20260722-v107">' + "`r`n    " + '<link rel="stylesheet" href="delivery-automation-ui.css?v=20260722-v107">',
        1
    )
    $indexText = [regex]::Replace(
        $indexText,
        '<script src="app\.js\?v=[^"]+"></script>',
        '<script src="app.js?v=20260722-v107"></script>' + "`r`n  " + '<script src="delivery-automation-ui.js?v=20260722-v107"></script>',
        1
    )
    if (-not $indexText.Contains('delivery-automation-ui.js')) {
        throw "Could not add the v107 automation UI bootstrap to index.html."
    }
}

$serverText = [IO.File]::ReadAllText($serverPath).Replace("`r`n", "`n")
if (-not $serverText.Contains('from delivery_automation_control import DeliveryAutomationController')) {
    $serverText = Replace-RequiredText -Text $serverText `
        -Old "from scanner_config import load_config" `
        -New "from scanner_config import load_config`nfrom delivery_automation_control import DeliveryAutomationController" `
        -Label "server import"
}
if (-not $serverText.Contains('DELIVERY_AUTOMATION = DeliveryAutomationController')) {
    $serverText = Replace-RequiredText -Text $serverText `
        -Old "ROOT = Path(__file__).resolve().parent`nCONFIG = load_config(ROOT)`nSTORE = create_store(CONFIG)" `
        -New "ROOT = Path(__file__).resolve().parent`nCONFIG = load_config(ROOT)`nSTORE = create_store(CONFIG)`nDELIVERY_AUTOMATION = DeliveryAutomationController(ROOT, CONFIG)" `
        -Label "server startup"
}

if (-not $serverText.Contains('/api/admin/delivery-automation"')) {
    $getAnchor = @'
        if parsed.path == "/api/notifications/pending":
            user = self.current_user()
            if not user:
                self.send_json({"error": "Authentication required"}, HTTPStatus.UNAUTHORIZED)
                return
            self.send_json({"notifications": STORE.get_pending_notifications(user["username"])})
            return
'@
    $getAnchor = $getAnchor.Replace("`r`n", "`n")
    $getBlock = $getAnchor + @'

        if parsed.path == "/api/admin/delivery-automation":
            user = self.require_permission("import_delivery_lists")
            if not user:
                return
            self.send_json(DELIVERY_AUTOMATION.get_dashboard())
            return
'@
    $getBlock = $getBlock.Replace("`r`n", "`n")
    $serverText = Replace-RequiredText -Text $serverText -Old $getAnchor -New $getBlock -Label "automation GET route"
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

Copy-Item -LiteralPath (Join-Path $PSScriptRoot "delivery_automation_control.py") -Destination (Join-Path $resolvedRoot "delivery_automation_control.py") -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "delivery-automation-ui.js") -Destination (Join-Path $resolvedRoot "delivery-automation-ui.js") -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "delivery-automation-ui.css") -Destination (Join-Path $resolvedRoot "delivery-automation-ui.css") -Force
[IO.File]::WriteAllText($indexPath, $indexText, [Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText($serverPath, $serverText, [Text.UTF8Encoding]::new($false))

$readmeText = [IO.File]::ReadAllText($readmePath)
$readmeText = [regex]::Replace($readmeText, 'Current maintained release:\s*\*\*v\d+\*\*\.', 'Current maintained release: **v107**.', 1)
if (-not $readmeText.Contains('v107 adds the Delivery List Automation Control Center')) {
    $marker = "Current maintained release: **v107**. SQLite remains the active/default backend.`r`n"
    if (-not $readmeText.Contains($marker)) {
        $marker = "Current maintained release: **v107**. SQLite remains the active/default backend.`n"
    }
    $addition = @'

v107 adds the Delivery List Automation Control Center to the existing **Import / Update Delivery List** command. Admin users can now import only from the Temp Delivery Lists folder, query A+W SQL and export workbooks without importing, or query/export/import in one controlled run. The same GUI manages the automatic mode, date windows, interval, full refresh time, notifications, and scheduled tasks. This lets authorized central systems use SQL while temporary floor copies use folder-only importing without A+W access.
'@
    $readmeText = $readmeText.Replace($marker, $marker + $addition)
}
[IO.File]::WriteAllText($readmePath, $readmeText, [Text.UTF8Encoding]::new($false))

$changelogText = [IO.File]::ReadAllText($changelogPath)
if (-not $changelogText.Contains('## v107')) {
    $entry = @'
## v107 - Delivery List Automation Control Center

- Changed **Import / Update Delivery List** into a GUI control center instead of immediately running the folder importer.
- Added three safe manual commands: **Import Temp Folder Only**, **Query SQL & Export Only**, and **Query SQL, Export & Import**.
- Added one-date, custom-range, normal incremental-window, and full-refresh-window controls.
- Added configurable automatic modes so temporary floor installations can use folder-only importing while the authorized central installation can query A+W SQL.
- Added GUI controls for interval, past/future date windows, daily full refresh time, destination folder, popup notifications, task installation, and task removal.
- Reused the existing scanner notification queue for success, no-change, and failure popups.
- Added a server-side allowlisted control module; the browser never receives SQL credentials and cannot execute arbitrary commands.
- Preserved all v105 Old Bay, Bay Scanner, audio, database, route, rack, and scanning behavior.

'@
    $changelogText = $entry + $changelogText
    [IO.File]::WriteAllText($changelogPath, $changelogText, [Text.UTF8Encoding]::new($false))
}

Write-Host "v107 project integration applied successfully." -ForegroundColor Green
Write-Host "Backups: $backupRoot"
Write-Host "Restart the Delivery List Scanner web app before opening the new GUI."
