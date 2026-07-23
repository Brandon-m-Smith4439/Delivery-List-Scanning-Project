[CmdletBinding()]
param(
    [string]$ConfigPath = "C:\DeliveryListAutomation\Scripts\sql-export.config.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "Delivery List Automation v121 Status" -ForegroundColor Cyan
Write-Host ""

foreach ($task in @("BFS Delivery List Automation Incremental", "BFS Delivery List Automation Full Refresh")) {
    Write-Host $task -ForegroundColor White
    & schtasks.exe /Query /TN $task /FO LIST /V 2>$null | Select-String -Pattern "TaskName|Status|Last Run Time|Last Result|Next Run Time|Run As User"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Task is not installed." -ForegroundColor Yellow
    }
    Write-Host ""
}

if (Test-Path -LiteralPath $ConfigPath -PathType Leaf) {
    $config = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $lastRunPath = Join-Path $config.WorkingRoot "State\last-run.json"
    Write-Host "Configuration: $ConfigPath"
    Write-Host "Destination:   $($config.DestinationFolder)"
    Write-Host "Logs:          $($config.WorkingRoot)\Logs"
    if (Test-Path -LiteralPath $lastRunPath -PathType Leaf) {
        Write-Host ""
        Write-Host "Last automation result:" -ForegroundColor White
        $lastRun = Get-Content -LiteralPath $lastRunPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $lastRun | ConvertTo-Json -Depth 8
        $logPath = [string]$lastRun.logPath
        if (-not [string]::IsNullOrWhiteSpace($logPath) -and (Test-Path -LiteralPath $logPath -PathType Leaf)) {
            Write-Host ""
            Write-Host "Complete run log: $logPath" -ForegroundColor White
            Write-Host "------------------------------------------------------------" -ForegroundColor DarkGray
            Get-Content -LiteralPath $logPath -Raw -Encoding UTF8
        }
    }
    else {
        Write-Host "No completed run has been recorded yet." -ForegroundColor Yellow
    }
}
else {
    Write-Host "Configuration is missing. Run setup first: $ConfigPath" -ForegroundColor Yellow
}
