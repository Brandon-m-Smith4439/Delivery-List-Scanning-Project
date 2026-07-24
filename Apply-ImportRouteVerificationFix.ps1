[CmdletBinding()]
param(
    [string]$WorkingRoot = "C:\DeliveryListAutomation"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceRoot = Join-Path $projectRoot "automation\sql_delivery_export"
$runtimeRoot = Join-Path $WorkingRoot "Scripts"
$fileNames = @(
    "import_delivery_folder.py",
    "verify_delivery_import.py"
)

if (-not (Test-Path -LiteralPath $runtimeRoot -PathType Container)) {
    throw "The installed delivery-list automation runtime was not found at $runtimeRoot."
}

foreach ($fileName in $fileNames) {
    $sourcePath = Join-Path $sourceRoot $fileName
    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
        throw "Required project helper is missing: $sourcePath"
    }
}

$backupRoot = Join-Path $WorkingRoot (
    "Backups\import-route-verification-{0}" -f (Get-Date -Format "yyyyMMdd-HHmmss")
)
[void](New-Item -ItemType Directory -Path $backupRoot -Force)

foreach ($fileName in $fileNames) {
    $sourcePath = Join-Path $sourceRoot $fileName
    $destinationPath = Join-Path $runtimeRoot $fileName
    if (Test-Path -LiteralPath $destinationPath -PathType Leaf) {
        Copy-Item `
            -LiteralPath $destinationPath `
            -Destination (Join-Path $backupRoot $fileName) `
            -Force
    }
    Copy-Item -LiteralPath $sourcePath -Destination $destinationPath -Force
    Unblock-File -LiteralPath $destinationPath -ErrorAction SilentlyContinue

    $sourceHash = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash
    $destinationHash = (Get-FileHash -LiteralPath $destinationPath -Algorithm SHA256).Hash
    if ($sourceHash -ne $destinationHash) {
        throw "Installed helper verification failed for $fileName."
    }
}

Write-Host ""
Write-Host "Delivery-list route verification fix installed successfully." -ForegroundColor Green
Write-Host "- Customer Route Rules now determine the expected receiving stages."
Write-Host "- All-CPU, all-DTC, and all-Greenville dates no longer falsely require Indian Trail."
Write-Host "- Existing configuration, scanner data, scheduled tasks, and workbooks were not changed."
Write-Host "- Backup folder: $backupRoot"
Write-Host ""
Write-Host "Next: retry the normal automatic import or run C:\DeliveryListAutomation\Run-Now.cmd."

