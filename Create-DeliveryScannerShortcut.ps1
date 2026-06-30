$ErrorActionPreference = "Stop"

$appRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "Glass Delivery Scanner.lnk"
$launcherExe = Join-Path $appRoot "publish\Delivery List Scanner.exe"
$batPath = Join-Path $appRoot "Start Delivery Scanner Web App.bat"
$iconPath = Join-Path $appRoot "assets\delivery-list-scanner-icon.ico"

if (Test-Path -LiteralPath $launcherExe) {
    $targetPath = $launcherExe
    $arguments = ""
} else {
    $targetPath = $batPath
    $arguments = ""
}

if (-not (Test-Path -LiteralPath $targetPath)) {
    throw "Could not find the Delivery List Scanner starter in $appRoot"
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $targetPath
$shortcut.Arguments = $arguments
$shortcut.WorkingDirectory = $appRoot
if (Test-Path -LiteralPath $iconPath) {
    $shortcut.IconLocation = "$iconPath,0"
}
$shortcut.Description = "Start the Glass Delivery Scanner web app"
$shortcut.Save()

Write-Host "Created shortcut:"
Write-Host $shortcutPath
