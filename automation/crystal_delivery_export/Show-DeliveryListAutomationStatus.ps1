[CmdletBinding()]
param([string]$WorkingRoot = "C:\DeliveryListAutomation")

$statusPath = Join-Path $WorkingRoot "State\last-run.json"
if (Test-Path -LiteralPath $statusPath -PathType Leaf) {
    Write-Host "Last automation result" -ForegroundColor Cyan
    Get-Content -LiteralPath $statusPath -Raw -Encoding UTF8
}
else {
    Write-Host "No completed automation run has written a status file yet." -ForegroundColor Yellow
}
Write-Host ""
foreach ($task in @("BFS Delivery List Incremental Export", "BFS Delivery List Full Export")) {
    & schtasks.exe /Query /TN $task /V /FO LIST 2>$null
}
Write-Host ""
Write-Host "Logs: $WorkingRoot\Logs"
