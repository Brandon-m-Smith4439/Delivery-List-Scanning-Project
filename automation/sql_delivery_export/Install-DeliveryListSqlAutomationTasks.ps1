[CmdletBinding()]
param(
    [string]$ConfigPath = "C:\DeliveryListAutomation\Scripts\sql-export.config.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert-PowerShellSyntax {
    param([Parameter(Mandatory = $true)][string[]]$Paths)

    foreach ($path in $Paths) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Required automation script is missing: $path"
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


function Invoke-ScheduledTasksCommand {
    param(
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    $schtasksPath = Join-Path $env:WINDIR "System32\schtasks.exe"
    if (-not (Test-Path -LiteralPath $schtasksPath -PathType Leaf)) {
        throw "Windows Task Scheduler command was not found: $schtasksPath"
    }

    # Windows PowerShell can promote text written by native programs to stderr
    # into a terminating NativeCommandError when ErrorActionPreference is Stop.
    # Capture both streams under Continue, then use the real process exit code.
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $commandOutput = @(& $schtasksPath @Arguments 2>&1)
        $exitCode = [int]$LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    $message = @(
        $commandOutput | ForEach-Object { $_.ToString().TrimEnd() }
    ) -join [Environment]::NewLine

    return [pscustomobject]@{
        ExitCode = $exitCode
        Output = $message.Trim()
    }
}

function Assert-ScheduledTasksCommandSucceeded {
    param(
        [Parameter(Mandatory = $true)]$Result,
        [Parameter(Mandatory = $true)][string]$FailureMessage
    )

    if ([int]$Result.ExitCode -eq 0) {
        return
    }

    $details = [string]$Result.Output
    if ([string]::IsNullOrWhiteSpace($details)) {
        throw $FailureMessage
    }
    throw "$FailureMessage`n$details"
}

if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
    throw "Automation configuration was not found: $ConfigPath. Run Setup-Floor-Folder-Import-Automation.bat on a floor computer or the SQL automation setup on the authorized central computer."
}

$config = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
$incrementalCmd = Join-Path $config.WorkingRoot "Run-Incremental.cmd"
$fullCmd = Join-Path $config.WorkingRoot "Run-Full.cmd"
if (-not (Test-Path -LiteralPath $incrementalCmd -PathType Leaf) -or
    -not (Test-Path -LiteralPath $fullCmd -PathType Leaf)) {
    throw "Automation command files are missing. Run Setup-Floor-Folder-Import-Automation.bat again on a floor computer, or rerun the central SQL automation setup."
}

$scriptRoot = Split-Path -Parent $ConfigPath
$runner = Join-Path $scriptRoot "Run-DeliveryListSqlAutomation.ps1"
$powerShellPath = [string]$config.Runtime.PowerShellPath
if ([string]::IsNullOrWhiteSpace($powerShellPath)) {
    $powerShellPath = Join-Path $env:WINDIR "System32\WindowsPowerShell\v1.0\powershell.exe"
}
if (-not (Test-Path -LiteralPath $powerShellPath -PathType Leaf)) {
    throw "Windows PowerShell was not found: $powerShellPath"
}

# Validate only the maintained SQL automation entry points used by setup,
# scheduling, status, removal, verification, and actual runs. Older Crystal
# scripts can remain in the shared runtime folder after an upgrade, but they are
# not part of the current SQL task workflow and must not block task installation.
$syntaxFileNames = @(
    "Run-DeliveryListSqlAutomation.ps1",
    "Initialize-DeliveryListSqlAutomation.ps1",
    "Install-DeliveryListSqlAutomationTasks.ps1",
    "Remove-DeliveryListSqlAutomationTasks.ps1",
    "Show-DeliveryListSqlAutomationStatus.ps1",
    "Verify-DeliveryListSqlAutomation.ps1"
)
$syntaxTargets = @(
    $syntaxFileNames | ForEach-Object { Join-Path $scriptRoot $_ }
)
Assert-PowerShellSyntax -Paths $syntaxTargets

Write-Host "PowerShell syntax check passed for $($syntaxTargets.Count) maintained automation scripts." -ForegroundColor Green
$automationMode = [string]$config.Automation.Mode
if ($automationMode -eq "folder-import-only") {
    Write-Host "Running the floor folder-access and scanner compatibility preflight..."
    $destinationFolder = [string]$config.DestinationFolder
    if ([string]::IsNullOrWhiteSpace($destinationFolder) -or
        -not (Test-Path -LiteralPath $destinationFolder -PathType Container)) {
        throw "The Temp Delivery Lists folder cannot be reached: $destinationFolder"
    }

    try {
        [void](Get-ChildItem -LiteralPath $destinationFolder -File -ErrorAction Stop | Select-Object -First 1)
    }
    catch {
        throw "The Temp Delivery Lists folder cannot be read by this Windows account: $destinationFolder"
    }

    $projectRoot = [string]$config.ProjectRoot
    foreach ($requiredName in @("server.py", "scanner_config.py", "delivery_store.py")) {
        $requiredPath = Join-Path $projectRoot $requiredName
        if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
            throw "Required scanner file is missing: $requiredPath"
        }
    }

    $pythonPath = [string]$config.Runtime.PythonPath
    if ([string]::IsNullOrWhiteSpace($pythonPath) -or
        -not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
        throw "Python runtime is not configured for floor folder imports. Run Setup-Floor-Folder-Import-Automation.bat again."
    }
    $pythonArguments = @()
    if ($null -ne $config.Runtime.PythonArguments) {
        $pythonArguments = @($config.Runtime.PythonArguments | ForEach-Object { [string]$_ })
    }
    $compatibilityPath = Join-Path $scriptRoot "validate_scanner_compatibility.py"
    if (-not (Test-Path -LiteralPath $compatibilityPath -PathType Leaf)) {
        throw "Scanner compatibility validator is missing: $compatibilityPath"
    }
    & $pythonPath @pythonArguments $compatibilityPath --project-root $projectRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Scanner compatibility validation failed for the floor folder-import runtime."
    }
    Write-Host "Floor folder-import preflight passed without querying A+W SQL." -ForegroundColor Green
}
else {
    Write-Host "Running the SQL, workbook, destination, and scanner compatibility preflight..."
    & $powerShellPath `
        -NoProfile `
        -ExecutionPolicy Bypass `
        -File $runner `
        -Mode RuntimeTest `
        -RunAction Configured `
        -ConfigPath $ConfigPath
    if ($LASTEXITCODE -ne 0) {
        throw "Automation preflight failed. Review the latest file in $($config.WorkingRoot)\Logs before installing scheduled tasks."
    }
}

$interval = [int]$config.Schedule.IncrementalIntervalMinutes
if ($interval -lt 5) {
    throw "IncrementalIntervalMinutes must be at least 5."
}
$fullTime = [string]$config.Schedule.FullRefreshTime
$taskUser = "$env:USERDOMAIN\$env:USERNAME"
$legacyTasks = @("BFS Delivery List SQL Incremental Export", "BFS Delivery List SQL Full Export")
foreach ($legacyTask in $legacyTasks) {
    $legacyQuery = Invoke-ScheduledTasksCommand -Arguments @("/Query", "/TN", $legacyTask)
    if ($legacyQuery.ExitCode -eq 0) {
        $legacyDelete = Invoke-ScheduledTasksCommand -Arguments @("/Delete", "/TN", $legacyTask, "/F")
        Assert-ScheduledTasksCommandSucceeded `
            -Result $legacyDelete `
            -FailureMessage "Windows Task Scheduler could not remove the obsolete task: $legacyTask"
        Write-Host "Removed obsolete scheduled task: $legacyTask"
    }
}
$incrementalTask = "BFS Delivery List Automation Incremental"
$fullTask = "BFS Delivery List Automation Full Refresh"

$incrementalAction = '"' + $incrementalCmd + '"'
$fullAction = '"' + $fullCmd + '"'

$incrementalCreate = Invoke-ScheduledTasksCommand -Arguments @(
    "/Create", "/TN", $incrementalTask, "/TR", $incrementalAction,
    "/SC", "MINUTE", "/MO", [string]$interval, "/RU", $taskUser, "/IT", "/F"
)
Assert-ScheduledTasksCommandSucceeded `
    -Result $incrementalCreate `
    -FailureMessage "Windows Task Scheduler could not create the incremental task."

$fullCreate = Invoke-ScheduledTasksCommand -Arguments @(
    "/Create", "/TN", $fullTask, "/TR", $fullAction,
    "/SC", "DAILY", "/ST", $fullTime, "/RU", $taskUser, "/IT", "/F"
)
Assert-ScheduledTasksCommandSucceeded `
    -Result $fullCreate `
    -FailureMessage "Windows Task Scheduler could not create the full-refresh task."

foreach ($taskName in @($incrementalTask, $fullTask)) {
    $taskQuery = Invoke-ScheduledTasksCommand -Arguments @("/Query", "/TN", $taskName)
    Assert-ScheduledTasksCommandSucceeded `
        -Result $taskQuery `
        -FailureMessage "Windows Task Scheduler did not retain the task after creation: $taskName"
}

Write-Host "Created scheduled tasks for mode ${automationMode}:" -ForegroundColor Green
Write-Host "- ${incrementalTask}: every $interval minutes while $taskUser is logged on"
Write-Host "- ${fullTask}: daily at $fullTime while $taskUser is logged on"
Write-Host ""
Write-Host "The computer must be on, connected to the BFS network, and signed in as $taskUser."
Write-Host "Running the incremental task now for a final scheduler launch check..."
$incrementalRun = Invoke-ScheduledTasksCommand -Arguments @("/Run", "/TN", $incrementalTask)
Assert-ScheduledTasksCommandSucceeded `
    -Result $incrementalRun `
    -FailureMessage "The scheduled task was created but Windows could not start it."

$config.Automation.ScheduleEnabled = $true
$config | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $ConfigPath -Encoding UTF8
