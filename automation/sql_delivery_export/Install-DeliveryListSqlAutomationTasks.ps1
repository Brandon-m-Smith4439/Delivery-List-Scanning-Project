[CmdletBinding()]
param(
    [string]$ConfigPath = "C:\DeliveryListAutomation\Scripts\sql-export.config.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
    throw "Run Setup-DeliveryListSqlAutomation.bat first. Configuration was not found: $ConfigPath"
}
$config = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
$incrementalCmd = Join-Path $config.WorkingRoot "Run-Incremental.cmd"
$fullCmd = Join-Path $config.WorkingRoot "Run-Full.cmd"
if (-not (Test-Path -LiteralPath $incrementalCmd -PathType Leaf) -or
    -not (Test-Path -LiteralPath $fullCmd -PathType Leaf)) {
    throw "Automation command files are missing. Run setup again."
}

$interval = [int]$config.Schedule.IncrementalIntervalMinutes
if ($interval -lt 5) {
    throw "IncrementalIntervalMinutes must be at least 5."
}
$fullTime = [string]$config.Schedule.FullRefreshTime
$taskUser = "$env:USERDOMAIN\$env:USERNAME"
$legacyTasks = @("BFS Delivery List SQL Incremental Export", "BFS Delivery List SQL Full Export")
foreach ($legacyTask in $legacyTasks) {
    & schtasks.exe /Delete /TN $legacyTask /F 2>$null | Out-Null
}
$incrementalTask = "BFS Delivery List Automation Incremental"
$fullTask = "BFS Delivery List Automation Full Refresh"

$incrementalAction = '"' + $incrementalCmd + '"'
$fullAction = '"' + $fullCmd + '"'

& schtasks.exe /Create /TN $incrementalTask /TR $incrementalAction /SC MINUTE /MO $interval /RU $taskUser /IT /F
if ($LASTEXITCODE -ne 0) {
    throw "Windows Task Scheduler could not create the incremental task."
}
& schtasks.exe /Create /TN $fullTask /TR $fullAction /SC DAILY /ST $fullTime /RU $taskUser /IT /F
if ($LASTEXITCODE -ne 0) {
    throw "Windows Task Scheduler could not create the full-refresh task."
}

Write-Host "Created scheduled tasks:" -ForegroundColor Green
Write-Host "- $incrementalTask: every $interval minutes while $taskUser is logged on"
Write-Host "- $fullTask: daily at $fullTime while $taskUser is logged on"
Write-Host ""
Write-Host "The computer must be on, connected to the BFS network, and signed in as $taskUser."
Write-Host "Running the incremental task now for a final scheduler check..."
& schtasks.exe /Run /TN $incrementalTask
if ($LASTEXITCODE -ne 0) {
    throw "The scheduled task was created but Windows could not start it."
}

$config.Automation.ScheduleEnabled = $true
$config | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $ConfigPath -Encoding UTF8
