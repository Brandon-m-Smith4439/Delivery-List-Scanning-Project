# File: automation/sql_delivery_export/Initialize-DeliveryListSqlAutomation.ps1
[CmdletBinding()]
param(
    [string]$WorkingRoot = "C:\DeliveryListAutomation",
    [string]$ProjectRoot = "",
    [switch]$SkipProjectDocumentation
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Set-JsonProperty {
    param(
        [Parameter(Mandatory = $true)]$Object,
        [Parameter(Mandatory = $true)][string]$Name,
        $Value
    )

    if ($Object.PSObject.Properties.Name -contains $Name) {
        $Object.$Name = $Value
    }
    else {
        $Object | Add-Member -NotePropertyName $Name -NotePropertyValue $Value
    }
}

function Get-OptionalSetupProperty {
    param(
        $Object,
        [Parameter(Mandatory = $true)][string]$Name,
        $DefaultValue = $null
    )

    if ($null -eq $Object -or -not ($Object.PSObject.Properties.Name -contains $Name)) {
        return $DefaultValue
    }
    return $Object.$Name
}

function Merge-MissingJsonProperties {
    param(
        [Parameter(Mandatory = $true)]$Target,
        [Parameter(Mandatory = $true)]$Defaults
    )

    foreach ($property in $Defaults.PSObject.Properties) {
        if (-not ($Target.PSObject.Properties.Name -contains $property.Name)) {
            $copy = $property.Value | ConvertTo-Json -Depth 20 | ConvertFrom-Json
            $Target | Add-Member -NotePropertyName $property.Name -NotePropertyValue $copy
            continue
        }
        $targetValue = $Target.($property.Name)
        $defaultValue = $property.Value
        if ($null -ne $targetValue -and $null -ne $defaultValue -and
            $targetValue -is [pscustomobject] -and $defaultValue -is [pscustomobject]) {
            Merge-MissingJsonProperties -Target $targetValue -Defaults $defaultValue
        }
    }
}

function Resolve-ScannerProjectRoot {
    param([string]$RequestedRoot)

    $candidates = New-Object System.Collections.Generic.List[string]
    if (-not [string]::IsNullOrWhiteSpace($RequestedRoot)) {
        $candidates.Add($RequestedRoot)
    }
    $candidates.Add((Join-Path $PSScriptRoot "..\.."))
    $candidates.Add((Get-Location).Path)
    $candidates.Add("C:\Users\brandon.m.smith\My Projects\Delivery List Scanning Project")

    foreach ($candidate in $candidates) {
        try {
            $resolved = (Resolve-Path -LiteralPath $candidate -ErrorAction Stop).Path
        }
        catch {
            continue
        }
        if ((Test-Path -LiteralPath (Join-Path $resolved "server.py") -PathType Leaf) -and
            (Test-Path -LiteralPath (Join-Path $resolved "backend\config.py") -PathType Leaf) -and
            (Test-Path -LiteralPath (Join-Path $resolved "backend\store.py") -PathType Leaf)) {
            return $resolved
        }
    }

    $manual = Read-Host "Enter the full Delivery List Scanning Project folder path"
    $resolvedManual = (Resolve-Path -LiteralPath $manual -ErrorAction Stop).Path
    foreach ($requiredName in @("server.py", "backend\config.py", "backend\store.py")) {
        if (-not (Test-Path -LiteralPath (Join-Path $resolvedManual $requiredName) -PathType Leaf)) {
            throw "The selected project folder is missing $requiredName"
        }
    }
    return $resolvedManual
}

function Get-ProjectRelease {
    param([Parameter(Mandatory = $true)][string]$Root)

    $readmePath = Join-Path $Root "README.md"
    if (-not (Test-Path -LiteralPath $readmePath -PathType Leaf)) {
        throw "README.md was not found in the selected scanner project."
    }
    $text = [IO.File]::ReadAllText($readmePath)
    $match = [regex]::Match($text, 'Current maintained release:\s*\*\*v(?<version>\d+)\*\*')
    if (-not $match.Success) {
        throw "The scanner README does not expose its maintained version."
    }
    return [int]$match.Groups["version"].Value
}

function Test-PythonCandidate {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [string[]]$Arguments = @()
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $null
    }
    try {
        $versionText = & $Path @Arguments -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>$null
        if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace([string]$versionText)) {
            return $null
        }
        $version = [version]([string]$versionText).Trim()
        if ($version -lt [version]"3.10") {
            return $null
        }
        return [pscustomobject]@{
            Path = $Path
            Arguments = @($Arguments)
            Version = $version.ToString()
        }
    }
    catch {
        return $null
    }
}

function Find-PythonRuntime {
    param([Parameter(Mandatory = $true)][string]$Root)

    $venvPython = Join-Path $Root ".venv\Scripts\python.exe"
    $result = Test-PythonCandidate -Path $venvPython
    if ($null -ne $result) {
        return $result
    }

    $pyCommand = Get-Command py.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $pyCommand) {
        $result = Test-PythonCandidate -Path $pyCommand.Source -Arguments @("-3")
        if ($null -ne $result) {
            return $result
        }
    }

    $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $pythonCommand) {
        $result = Test-PythonCandidate -Path $pythonCommand.Source
        if ($null -ne $result) {
            return $result
        }
    }

    throw "Python 3.10 or newer was not found."
}

Write-Host ""
Write-Host "BFS Delivery List Automation v121 Setup" -ForegroundColor Cyan
Write-Host "The exporter is isolated from the scanner application and stores no SQL password." -ForegroundColor DarkGray
Write-Host ""

$resolvedProjectRoot = Resolve-ScannerProjectRoot -RequestedRoot $ProjectRoot
$projectRelease = Get-ProjectRelease -Root $resolvedProjectRoot
if ($projectRelease -lt 105) {
    throw "The selected scanner is v$projectRelease. Update it to v105 or newer before installing this exporter."
}
if ($projectRelease -gt 121) {
    throw "The selected scanner is v$projectRelease. This v121 installer will not modify a newer release."
}

foreach ($folder in @("Staging", "Logs", "Failed", "State", "Scripts", "Backups")) {
    [void](New-Item -ItemType Directory -Path (Join-Path $WorkingRoot $folder) -Force)
}
$scriptRoot = Join-Path $WorkingRoot "Scripts"

Get-ChildItem -LiteralPath $PSScriptRoot -File | Where-Object {
    $_.Name -ne "sql-export.config.json" -and $_.Extension -in @(".ps1", ".py", ".bat", ".md", ".txt", ".js", ".css")
} | Copy-Item -Destination $scriptRoot -Force
Get-ChildItem -LiteralPath $scriptRoot -Recurse -File -ErrorAction SilentlyContinue |
    Unblock-File -ErrorAction SilentlyContinue

$defaultConfigPath = Join-Path $PSScriptRoot "sql-export.config.json"
$configPath = Join-Path $scriptRoot "sql-export.config.json"
$defaults = Get-Content -LiteralPath $defaultConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
if (Test-Path -LiteralPath $configPath -PathType Leaf) {
    $backupPath = Join-Path $WorkingRoot ("Backups\sql-export.config-{0}.json" -f (Get-Date -Format "yyyyMMdd-HHmmss"))
    Copy-Item -LiteralPath $configPath -Destination $backupPath -Force
    $config = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Merge-MissingJsonProperties -Target $config -Defaults $defaults
}
else {
    $config = $defaults
}

Set-JsonProperty -Object $config -Name "Version" -Value "v121"
Set-JsonProperty -Object $config -Name "ProjectRoot" -Value $resolvedProjectRoot
Set-JsonProperty -Object $config -Name "WorkingRoot" -Value $WorkingRoot

# Upgrade the v101 import flag without discarding the user's choice.
if ($config.Import.PSObject.Properties.Name -contains "Enabled") {
    $legacyEnabled = [bool]$config.Import.Enabled
    Set-JsonProperty -Object $config.Import -Name "Mode" -Value $(if ($legacyEnabled) { "direct-store" } else { "disabled" })
    $config.Import.PSObject.Properties.Remove("Enabled")
}

if (-not ($config.PSObject.Properties.Name -contains "Automation")) {
    $config | Add-Member -NotePropertyName "Automation" -NotePropertyValue ([pscustomobject]@{})
}
$currentMode = [string](Get-OptionalSetupProperty -Object $config.Automation -Name "Mode" -DefaultValue "sql-export-and-import")
$defaultChoice = switch ($currentMode) {
    "folder-import-only" { "2" }
    "sql-export-only" { "3" }
    "disabled" { "4" }
    default { "1" }
}
Write-Host "Choose what this computer should do automatically:" -ForegroundColor Cyan
Write-Host "1. Query A+W SQL, export workbooks, and import them (central/authorized computer)"
Write-Host "2. Import existing workbooks from the Temp Delivery Lists folder only (floor computer)"
Write-Host "3. Query A+W SQL and export workbooks only"
Write-Host "4. Disable automatic runs; keep manual GUI commands"
$modeChoice = Read-Host "Selection [$defaultChoice]"
if ([string]::IsNullOrWhiteSpace($modeChoice)) {
    $modeChoice = $defaultChoice
}
$selectedMode = switch ($modeChoice.Trim()) {
    "2" { "folder-import-only" }
    "3" { "sql-export-only" }
    "4" { "disabled" }
    default { "sql-export-and-import" }
}
$currentScheduleEnabled = [bool](Get-OptionalSetupProperty -Object $config.Automation -Name "ScheduleEnabled" -DefaultValue $false)
Set-JsonProperty -Object $config.Automation -Name "Mode" -Value $selectedMode
Set-JsonProperty -Object $config.Automation -Name "ScheduleEnabled" -Value $currentScheduleEnabled
Set-JsonProperty -Object $config.Automation -Name "AllowWebGuiControl" -Value $true
Set-JsonProperty -Object $config.Import -Name "Mode" -Value "direct-store"

$python = Find-PythonRuntime -Root $resolvedProjectRoot
$config.Runtime.PythonPath = $python.Path
$config.Runtime.PythonArguments = @($python.Arguments)
$powerShellPath = Join-Path $env:WINDIR "System32\WindowsPowerShell\v1.0\powershell.exe"
if (-not (Test-Path -LiteralPath $powerShellPath -PathType Leaf)) {
    throw "Windows PowerShell 5.1 was not found at $powerShellPath"
}
$config.Runtime.PowerShellPath = $powerShellPath
$config | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $configPath -Encoding UTF8

$disableBuiltInImporter = [bool](Get-OptionalSetupProperty -Object $config.Import -Name "DisableBuiltInDailyImporter" -DefaultValue $true)
if ([string]$config.Import.Mode -eq "direct-store" -and $disableBuiltInImporter) {
    [Environment]::SetEnvironmentVariable("DLS_DAILY_IMPORT_ENABLED", "0", "User")
    $env:DLS_DAILY_IMPORT_ENABLED = "0"
}

Write-Host "Scanner release: v$projectRelease"
Write-Host "Project root: $resolvedProjectRoot"
Write-Host "Working root: $WorkingRoot"
Write-Host "Python: $($python.Path) $($python.Arguments -join ' ') (version $($python.Version))"
Write-Host "Destination: $($config.DestinationFolder)"
if ([string]$config.Import.Mode -eq "direct-store" -and $disableBuiltInImporter) {
    Write-Host "Built-in 5 PM importer: disabled for the current Windows user"
    Write-Host "Restart the scanner web app after setup so it receives this setting." -ForegroundColor Yellow
}
Write-Host ""

$runner = Join-Path $scriptRoot "Run-DeliveryListSqlAutomation.ps1"
& $powerShellPath -NoProfile -ExecutionPolicy Bypass -File $runner -Mode RuntimeTest -ConfigPath $configPath
if ($LASTEXITCODE -ne 0) {
    throw "Runtime validation failed. Review $WorkingRoot\Logs for details."
}

$incrementalCmd = Join-Path $WorkingRoot "Run-Incremental.cmd"
$fullCmd = Join-Path $WorkingRoot "Run-Full.cmd"
$testCmd = Join-Path $WorkingRoot "Run-Test.cmd"
$runNowCmd = Join-Path $WorkingRoot "Run-Now.cmd"
$runFullNowCmd = Join-Path $WorkingRoot "Run-Full-Now.cmd"
$runOneDateCmd = Join-Path $WorkingRoot "Run-One-Date.cmd"
$statusCmd = Join-Path $WorkingRoot "Show-Status.cmd"

$incrementalContent = @"
@echo off
"$powerShellPath" -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "$runner" -Mode Incremental -ConfigPath "$configPath"
exit /b %errorlevel%
"@
$incrementalContent | Set-Content -LiteralPath $incrementalCmd -Encoding ASCII

$fullContent = @"
@echo off
"$powerShellPath" -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "$runner" -Mode Full -ConfigPath "$configPath"
exit /b %errorlevel%
"@
$fullContent | Set-Content -LiteralPath $fullCmd -Encoding ASCII

$testContent = @"
@echo off
set /p DELIVERY_DATE=Enter a known delivery date (MM/DD/YYYY): 
"$powerShellPath" -NoProfile -ExecutionPolicy Bypass -File "$runner" -Mode Test -DeliveryDate "%DELIVERY_DATE%" -ConfigPath "$configPath"
set EXIT_CODE=%errorlevel%
echo.
if not "%EXIT_CODE%"=="0" echo Test failed. Review $WorkingRoot\Logs.
if "%EXIT_CODE%"=="0" echo Test completed successfully.
pause
exit /b %EXIT_CODE%
"@
$testContent | Set-Content -LiteralPath $testCmd -Encoding ASCII

$runNowContent = @"
@echo off
"$powerShellPath" -NoProfile -ExecutionPolicy Bypass -File "$runner" -Mode Incremental -ConfigPath "$configPath"
set EXIT_CODE=%errorlevel%
echo.
if not "%EXIT_CODE%"=="0" echo Manual update failed. Review $WorkingRoot\Logs.
if "%EXIT_CODE%"=="0" echo Manual update completed successfully.
pause
exit /b %EXIT_CODE%
"@
$runNowContent | Set-Content -LiteralPath $runNowCmd -Encoding ASCII

$runFullNowContent = @"
@echo off
"$powerShellPath" -NoProfile -ExecutionPolicy Bypass -File "$runner" -Mode Full -ConfigPath "$configPath"
set EXIT_CODE=%errorlevel%
echo.
if not "%EXIT_CODE%"=="0" echo Full manual refresh failed. Review $WorkingRoot\Logs.
if "%EXIT_CODE%"=="0" echo Full manual refresh completed successfully.
pause
exit /b %EXIT_CODE%
"@
$runFullNowContent | Set-Content -LiteralPath $runFullNowCmd -Encoding ASCII

$runOneDateContent = @"
@echo off
set /p DELIVERY_DATE=Enter a delivery date to export and import (MM/DD/YYYY): 
"$powerShellPath" -NoProfile -ExecutionPolicy Bypass -File "$runner" -Mode Test -DeliveryDate "%DELIVERY_DATE%" -ConfigPath "$configPath"
set EXIT_CODE=%errorlevel%
echo.
if not "%EXIT_CODE%"=="0" echo One-date update failed. Review $WorkingRoot\Logs.
if "%EXIT_CODE%"=="0" echo One-date update completed successfully.
pause
exit /b %EXIT_CODE%
"@
$runOneDateContent | Set-Content -LiteralPath $runOneDateCmd -Encoding ASCII

$statusScript = Join-Path $scriptRoot "Show-DeliveryListSqlAutomationStatus.ps1"
$statusContent = @"
@echo off
"$powerShellPath" -NoProfile -ExecutionPolicy Bypass -File "$statusScript" -ConfigPath "$configPath"
pause
"@
$statusContent | Set-Content -LiteralPath $statusCmd -Encoding ASCII

Write-Host ""
Write-Host "Setup completed successfully." -ForegroundColor Green
Write-Host "Automation was configured without changing web-app source files or the production database."
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Restart the scanner web app if setup disabled its built-in 5 PM importer."
Write-Host "2. Double-click $testCmd"
Write-Host "3. Enter 07/15/2026 for the first known-data comparison."
Write-Host "4. Confirm the generated workbook, scanner import, and in-app notification."
Write-Host "5. Open the web app Admin page and use Import / Update Delivery List to install or adjust the schedule, or run Install-DeliveryListSqlAutomationTasks.bat from $scriptRoot"
Write-Host ""
Write-Host "Manual commands created:"
Write-Host "- $runNowCmd"
Write-Host "- $runFullNowCmd"
Write-Host "- $runOneDateCmd"
Write-Host "- $statusCmd"
Write-Host ""
