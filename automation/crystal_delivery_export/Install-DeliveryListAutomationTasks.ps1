[CmdletBinding()]
param(
    [string]$ConfigPath = "C:\DeliveryListAutomation\Scripts\crystal-export.config.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
    throw "Run Setup-DeliveryListAutomation.bat first. Configuration was not found: $ConfigPath"
}
$config = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
$incrementalCmd = Join-Path $config.WorkingRoot "Run-Incremental.cmd"
$fullCmd = Join-Path $config.WorkingRoot "Run-Full.cmd"
if (-not (Test-Path -LiteralPath $incrementalCmd -PathType Leaf) -or -not (Test-Path -LiteralPath $fullCmd -PathType Leaf)) {
    throw "Automation command files are missing. Run setup again."
}

$interval = [int]$config.Schedule.IncrementalIntervalMinutes
if ($interval -lt 5) {
    throw "IncrementalIntervalMinutes must be at least 5."
}
$fullTime = [string]$config.Schedule.FullRefreshTime
$taskUser = "$env:USERDOMAIN\$env:USERNAME"
$incrementalTask = "BFS Delivery List Incremental Export"
$fullTask = "BFS Delivery List Full Export"

& schtasks.exe /Create /TN $incrementalTask /TR ('"' + $incrementalCmd + '"') /SC MINUTE /MO $interval /RU $taskUser /IT /F
if ($LASTEXITCODE -ne 0) {
    throw "Windows Task Scheduler could not create the incremental task."
}
& schtasks.exe /Create /TN $fullTask /TR ('"' + $fullCmd + '"') /SC DAILY /ST $fullTime /RU $taskUser /IT /F
if ($LASTEXITCODE -ne 0) {
    throw "Windows Task Scheduler could not create the full-refresh task."
}

Write-Host "Created scheduled tasks:" -ForegroundColor Green
Write-Host "- $incrementalTask: every $interval minutes while $taskUser is logged on"
Write-Host "- $fullTask: daily at $fullTime while $taskUser is logged on"
Write-Host ""
Write-Host "Running the incremental task now for a final check..."
& schtasks.exe /Run /TN $incrementalTask
