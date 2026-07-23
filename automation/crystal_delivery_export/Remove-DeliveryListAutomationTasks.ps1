$ErrorActionPreference = "Stop"
$tasks = @(
    "BFS Delivery List Incremental Export",
    "BFS Delivery List Full Export"
)
foreach ($task in $tasks) {
    & schtasks.exe /Delete /TN $task /F 2>$null
}
Write-Host "Delivery-list automation tasks removed. Local files and encrypted credentials were not deleted."
