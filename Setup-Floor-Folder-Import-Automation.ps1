[CmdletBinding()]
param(
    [string]$ProjectRoot = "",
    [string]$WorkingRoot = "C:\DeliveryListAutomation",
    [string]$DestinationFolder = "",
    [ValidateRange(5, 1440)][int]$IntervalMinutes = 60,
    [ValidatePattern('^(?:[01]\d|2[0-3]):[0-5]\d$')][string]$FullRefreshTime = "17:00",
    [switch]$SkipTaskInstall
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$script:SetupScriptRoot = Split-Path -Parent $PSCommandPath

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

function Get-OptionalProperty {
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
    $candidates.Add($script:SetupScriptRoot)
    $candidates.Add((Get-Location).Path)

    foreach ($candidate in $candidates) {
        try {
            $resolved = (Resolve-Path -LiteralPath $candidate -ErrorAction Stop).Path
        }
        catch {
            continue
        }

        $required = @("server.py", "scanner_config.py", "delivery_store.py")
        $missing = @($required | Where-Object {
            -not (Test-Path -LiteralPath (Join-Path $resolved $_) -PathType Leaf)
        })
        if ($missing.Count -eq 0) {
            return $resolved
        }
    }

    throw "The Delivery List Scanner project folder could not be found. Run this setup from the current scanner project folder."
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
    $candidate = Test-PythonCandidate -Path $venvPython
    if ($null -ne $candidate) {
        return $candidate
    }

    $pyCommand = Get-Command py.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $pyCommand) {
        $candidate = Test-PythonCandidate -Path $pyCommand.Source -Arguments @("-3")
        if ($null -ne $candidate) {
            return $candidate
        }
    }

    $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $pythonCommand) {
        $candidate = Test-PythonCandidate -Path $pythonCommand.Source
        if ($null -ne $candidate) {
            return $candidate
        }
    }

    throw "Python 3.10 or newer was not found. Start the web app once, then retry this setup from the same Windows account."
}

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

Write-Host ""
Write-Host "Delivery List Scanner - Floor Folder Import Setup v132" -ForegroundColor Cyan
Write-Host "This computer will import existing workbooks from the Temp Delivery Lists folder." -ForegroundColor DarkGray
Write-Host "It will not query A+W SQL or create delivery-list workbooks." -ForegroundColor DarkGray
Write-Host ""

$resolvedProjectRoot = Resolve-ScannerProjectRoot -RequestedRoot $ProjectRoot
$sourceRoot = Join-Path $resolvedProjectRoot "automation\sql_delivery_export"
$defaultConfigPath = Join-Path $sourceRoot "sql-export.config.json"

$requiredSourceFiles = @(
    "Run-DeliveryListSqlAutomation.ps1",
    "Initialize-DeliveryListSqlAutomation.ps1",
    "Install-DeliveryListSqlAutomationTasks.ps1",
    "Remove-DeliveryListSqlAutomationTasks.ps1",
    "Show-DeliveryListSqlAutomationStatus.ps1",
    "Verify-DeliveryListSqlAutomation.ps1",
    "import_delivery_folder.py",
    "publish_automation_notification.py",
    "validate_scanner_compatibility.py",
    "delivery_import_safety.py",
    "sql-export.config.json"
)
foreach ($name in $requiredSourceFiles) {
    $path = Join-Path $sourceRoot $name
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "The floor automation source package is incomplete. Missing: $path"
    }
}

foreach ($folder in @("Staging", "Logs", "Failed", "State", "Scripts", "Backups")) {
    [void](New-Item -ItemType Directory -Path (Join-Path $WorkingRoot $folder) -Force)
}
$scriptRoot = Join-Path $WorkingRoot "Scripts"
$backupRoot = Join-Path $WorkingRoot ("Backups\v132-floor-folder-import-{0}" -f (Get-Date -Format "yyyyMMdd-HHmmss"))
[void](New-Item -ItemType Directory -Path $backupRoot -Force)

$configPath = Join-Path $scriptRoot "sql-export.config.json"
if (Test-Path -LiteralPath $configPath -PathType Leaf) {
    Copy-Item -LiteralPath $configPath -Destination (Join-Path $backupRoot "sql-export.config.json") -Force
}
foreach ($name in $requiredSourceFiles) {
    if ($name -eq "sql-export.config.json") {
        continue
    }
    $installedPath = Join-Path $scriptRoot $name
    if (Test-Path -LiteralPath $installedPath -PathType Leaf) {
        Copy-Item -LiteralPath $installedPath -Destination (Join-Path $backupRoot $name) -Force
    }
}

Get-ChildItem -LiteralPath $sourceRoot -File | Where-Object {
    $_.Name -ne "sql-export.config.json" -and
    $_.Extension -in @(".ps1", ".py", ".bat", ".md", ".txt", ".js", ".css")
} | Copy-Item -Destination $scriptRoot -Force
Get-ChildItem -LiteralPath $scriptRoot -File -ErrorAction SilentlyContinue |
    Unblock-File -ErrorAction SilentlyContinue

$defaults = Get-Content -LiteralPath $defaultConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
if (Test-Path -LiteralPath $configPath -PathType Leaf) {
    $config = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Merge-MissingJsonProperties -Target $config -Defaults $defaults
}
else {
    $config = $defaults
}

$python = Find-PythonRuntime -Root $resolvedProjectRoot
$powerShellPath = Join-Path $env:WINDIR "System32\WindowsPowerShell\v1.0\powershell.exe"
if (-not (Test-Path -LiteralPath $powerShellPath -PathType Leaf)) {
    throw "Windows PowerShell 5.1 was not found: $powerShellPath"
}

$resolvedDestination = $DestinationFolder.Trim()
if ([string]::IsNullOrWhiteSpace($resolvedDestination)) {
    $resolvedDestination = [string](Get-OptionalProperty -Object $config -Name "DestinationFolder" -DefaultValue "")
}
if ([string]::IsNullOrWhiteSpace($resolvedDestination)) {
    $resolvedDestination = [string]$defaults.DestinationFolder
}
if ([string]::IsNullOrWhiteSpace($resolvedDestination)) {
    throw "The Temp Delivery Lists folder is not configured."
}

Set-JsonProperty -Object $config -Name "Version" -Value "v132"
Set-JsonProperty -Object $config -Name "ProjectRoot" -Value $resolvedProjectRoot
Set-JsonProperty -Object $config -Name "WorkingRoot" -Value $WorkingRoot
Set-JsonProperty -Object $config -Name "DestinationFolder" -Value $resolvedDestination

if (-not ($config.PSObject.Properties.Name -contains "Automation") -or $null -eq $config.Automation) {
    Set-JsonProperty -Object $config -Name "Automation" -Value ([pscustomobject]@{})
}
Set-JsonProperty -Object $config.Automation -Name "Mode" -Value "folder-import-only"
Set-JsonProperty -Object $config.Automation -Name "ScheduleEnabled" -Value $false
Set-JsonProperty -Object $config.Automation -Name "AllowWebGuiControl" -Value $true

if (-not ($config.PSObject.Properties.Name -contains "Schedule") -or $null -eq $config.Schedule) {
    Set-JsonProperty -Object $config -Name "Schedule" -Value ([pscustomobject]@{})
}
Set-JsonProperty -Object $config.Schedule -Name "IncrementalIntervalMinutes" -Value $IntervalMinutes
Set-JsonProperty -Object $config.Schedule -Name "FullRefreshTime" -Value $FullRefreshTime
if (-not ($config.Schedule.PSObject.Properties.Name -contains "IncrementalPastDays")) {
    Set-JsonProperty -Object $config.Schedule -Name "IncrementalPastDays" -Value 2
}
if (-not ($config.Schedule.PSObject.Properties.Name -contains "IncrementalFutureDays")) {
    Set-JsonProperty -Object $config.Schedule -Name "IncrementalFutureDays" -Value 14
}
if (-not ($config.Schedule.PSObject.Properties.Name -contains "FullPastDays")) {
    Set-JsonProperty -Object $config.Schedule -Name "FullPastDays" -Value 7
}
if (-not ($config.Schedule.PSObject.Properties.Name -contains "FullFutureDays")) {
    Set-JsonProperty -Object $config.Schedule -Name "FullFutureDays" -Value 90
}

if (-not ($config.PSObject.Properties.Name -contains "Import") -or $null -eq $config.Import) {
    Set-JsonProperty -Object $config -Name "Import" -Value ([pscustomobject]@{})
}
Set-JsonProperty -Object $config.Import -Name "Mode" -Value "direct-store"
Set-JsonProperty -Object $config.Import -Name "User" -Value "floor-folder-auto-import"
Set-JsonProperty -Object $config.Import -Name "InitializeStore" -Value $true
Set-JsonProperty -Object $config.Import -Name "DisableBuiltInDailyImporter" -Value $true

if (-not ($config.PSObject.Properties.Name -contains "Runtime") -or $null -eq $config.Runtime) {
    Set-JsonProperty -Object $config -Name "Runtime" -Value ([pscustomobject]@{})
}
Set-JsonProperty -Object $config.Runtime -Name "PowerShellPath" -Value $powerShellPath
Set-JsonProperty -Object $config.Runtime -Name "PythonPath" -Value $python.Path
Set-JsonProperty -Object $config.Runtime -Name "PythonArguments" -Value @($python.Arguments)

if (-not ($config.PSObject.Properties.Name -contains "Notifications") -or $null -eq $config.Notifications) {
    Set-JsonProperty -Object $config -Name "Notifications" -Value ([pscustomobject]@{})
}
Set-JsonProperty -Object $config.Notifications -Name "CreatedBy" -Value "floor-folder-auto-import"

$config | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $configPath -Encoding UTF8
[Environment]::SetEnvironmentVariable("DLS_DAILY_IMPORT_ENABLED", "0", "User")
$env:DLS_DAILY_IMPORT_ENABLED = "0"

$runner = Join-Path $scriptRoot "Run-DeliveryListSqlAutomation.ps1"
$incrementalCmd = Join-Path $WorkingRoot "Run-Incremental.cmd"
$fullCmd = Join-Path $WorkingRoot "Run-Full.cmd"
$runNowCmd = Join-Path $WorkingRoot "Run-Now.cmd"
$statusCmd = Join-Path $WorkingRoot "Show-Status.cmd"
$statusScript = Join-Path $scriptRoot "Show-DeliveryListSqlAutomationStatus.ps1"


$incrementalContent = @"
@echo off
"$powerShellPath" -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "$runner" -Mode Incremental -RunAction FolderImportOnly -ConfigPath "$configPath"
exit /b %errorlevel%
"@
$incrementalContent | Set-Content -LiteralPath $incrementalCmd -Encoding ASCII

$fullContent = @"
@echo off
"$powerShellPath" -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "$runner" -Mode Full -RunAction FolderImportOnly -ConfigPath "$configPath"
exit /b %errorlevel%
"@
$fullContent | Set-Content -LiteralPath $fullCmd -Encoding ASCII

$runNowContent = @"
@echo off
"$powerShellPath" -NoProfile -ExecutionPolicy Bypass -File "$runner" -Mode Incremental -RunAction FolderImportOnly -ConfigPath "$configPath"
set EXIT_CODE=%errorlevel%
echo.
if not "%EXIT_CODE%"=="0" echo Folder import failed. Review $WorkingRoot\Logs.
if "%EXIT_CODE%"=="0" echo Folder import completed successfully.
pause
exit /b %EXIT_CODE%
"@
$runNowContent | Set-Content -LiteralPath $runNowCmd -Encoding ASCII

$statusContent = @"
@echo off
"$powerShellPath" -NoProfile -ExecutionPolicy Bypass -File "$statusScript" -ConfigPath "$configPath"
pause
"@
$statusContent | Set-Content -LiteralPath $statusCmd -Encoding ASCII

Assert-PowerShellSyntax -Paths @(
    (Join-Path $scriptRoot "Run-DeliveryListSqlAutomation.ps1"),
    (Join-Path $scriptRoot "Install-DeliveryListSqlAutomationTasks.ps1"),
    (Join-Path $scriptRoot "Remove-DeliveryListSqlAutomationTasks.ps1"),
    (Join-Path $scriptRoot "Show-DeliveryListSqlAutomationStatus.ps1")
)

Write-Host "Project root: $resolvedProjectRoot"
Write-Host "Temp Delivery Lists folder: $resolvedDestination"
Write-Host "Working root: $WorkingRoot"
Write-Host "Python: $($python.Path) $($python.Arguments -join ' ')"
Write-Host "Import interval: every $IntervalMinutes minutes"
Write-Host ""

if (-not (Test-Path -LiteralPath $resolvedDestination -PathType Container)) {
    throw "The Temp Delivery Lists folder cannot be reached from this floor computer: $resolvedDestination"
}

$compatibilityScript = Join-Path $scriptRoot "validate_scanner_compatibility.py"
$compatibilityArguments = @($python.Arguments + @(
    $compatibilityScript,
    "--project-root", $resolvedProjectRoot
))
& $python.Path @compatibilityArguments
if ($LASTEXITCODE -ne 0) {
    throw "Scanner compatibility validation failed."
}

if (-not $SkipTaskInstall) {
    $installer = Join-Path $scriptRoot "Install-DeliveryListSqlAutomationTasks.ps1"
    & $powerShellPath `
        -NoProfile `
        -ExecutionPolicy Bypass `
        -File $installer `
        -ConfigPath $configPath
    if ($LASTEXITCODE -ne 0) {
        throw "The floor folder-import runtime was installed, but Windows scheduled-task installation failed."
    }
}

Write-Host ""
Write-Host "Floor folder-import automation is ready." -ForegroundColor Green
Write-Host "- A+W SQL querying is disabled on this computer."
Write-Host "- Existing workbooks are imported from the Temp Delivery Lists folder every $IntervalMinutes minutes."
Write-Host "- The normal daily full-window safety refresh remains scheduled at $FullRefreshTime."
Write-Host "- The older built-in 5 PM importer is disabled for this Windows user to prevent duplicate runs."
Write-Host "- Backup folder: $backupRoot"
Write-Host ""
Write-Host "Restart the scanner web app, then confirm the Admin automation mode shows Folder Import Only."
