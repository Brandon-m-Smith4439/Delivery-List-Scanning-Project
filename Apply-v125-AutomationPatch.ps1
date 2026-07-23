[CmdletBinding()]
param(
    [string]$WorkingRoot = "C:\DeliveryListAutomation"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert-PowerShellSyntax {
    param([Parameter(Mandatory = $true)][string[]]$Paths)

    foreach ($path in $Paths) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Required patch script is missing: $path"
        }
        $tokens = $null
        $parseErrors = $null
        [void][System.Management.Automation.Language.Parser]::ParseFile(
            $path,
            [ref]$tokens,
            [ref]$parseErrors
        )
        if ($parseErrors.Count -gt 0) {
            $details = @($parseErrors | ForEach-Object {
                "{0}:{1} {2}" -f $_.Extent.StartLineNumber, $_.Extent.StartColumnNumber, $_.Message
            }) -join [Environment]::NewLine
            throw "PowerShell syntax validation failed for $path`n$details"
        }
    }
}

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourcePath = Join-Path $projectRoot "automation\sql_delivery_export\Install-DeliveryListSqlAutomationTasks.ps1"
$runtimeRoot = Join-Path $WorkingRoot "Scripts"
$destinationPath = Join-Path $runtimeRoot "Install-DeliveryListSqlAutomationTasks.ps1"
$configPath = Join-Path $runtimeRoot "sql-export.config.json"

if (-not (Test-Path -LiteralPath $runtimeRoot -PathType Container)) {
    throw "The installed automation runtime was not found at $runtimeRoot. Run Setup-DeliveryListSqlAutomation-v121.bat first."
}
if (-not (Test-Path -LiteralPath $configPath -PathType Leaf)) {
    throw "The installed SQL automation configuration was not found: $configPath"
}

Assert-PowerShellSyntax -Paths @($sourcePath)

$backupRoot = Join-Path $WorkingRoot ("Backups\v125-automation-patch-{0}" -f (Get-Date -Format "yyyyMMdd-HHmmss"))
[void](New-Item -ItemType Directory -Path $backupRoot -Force)
if (Test-Path -LiteralPath $destinationPath -PathType Leaf) {
    Copy-Item `
        -LiteralPath $destinationPath `
        -Destination (Join-Path $backupRoot "Install-DeliveryListSqlAutomationTasks.ps1") `
        -Force
}

Copy-Item -LiteralPath $sourcePath -Destination $destinationPath -Force
Unblock-File -LiteralPath $destinationPath -ErrorAction SilentlyContinue
Assert-PowerShellSyntax -Paths @($destinationPath)

Write-Host ""
Write-Host "v125 Task Scheduler command patch installed successfully." -ForegroundColor Green
Write-Host "- Missing obsolete tasks are now treated as an expected condition instead of a fatal error."
Write-Host "- All schtasks.exe output is captured safely and evaluated by its process exit code."
Write-Host "- Existing automation configuration, scanner data, scheduled-task settings, and workbooks were not changed."
Write-Host "- Backup folder: $backupRoot"
Write-Host ""
Write-Host "Next: return to the web app and retry Save & Install Schedule."
