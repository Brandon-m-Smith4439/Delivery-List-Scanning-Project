# File: automation/sql_delivery_export/Remove-DeliveryListSqlAutomationTasks.ps1
[CmdletBinding()]
param(
    [string]$ConfigPath = "C:\DeliveryListAutomation\Scripts\sql-export.config.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

$tasks = @(
    "BFS Delivery List Automation Incremental",
    "BFS Delivery List Automation Full Refresh",
    "BFS Delivery List SQL Incremental Export",
    "BFS Delivery List SQL Full Export"
)
foreach ($task in $tasks) {
    & schtasks.exe /Delete /TN $task /F 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Removed: $task" -ForegroundColor Green
    }
}
if (Test-Path -LiteralPath $ConfigPath -PathType Leaf) {
    $config = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($config.PSObject.Properties.Name -contains "Automation") {
        $config.Automation.ScheduleEnabled = $false
        $config | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $ConfigPath -Encoding UTF8
    }
}
Write-Host "Delivery-list automation scheduled tasks are disabled." -ForegroundColor Yellow
