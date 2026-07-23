[CmdletBinding()]
param(
    [string]$WorkingRoot = "C:\DeliveryListAutomation"
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

Write-Host ""
Write-Host "BFS Delivery List Crystal Export Setup" -ForegroundColor Cyan
Write-Host "The SQL password is encrypted for this Windows user and is never written to the repository." -ForegroundColor DarkGray
Write-Host ""

$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path
$sourceConfig = Join-Path $PSScriptRoot "crystal-export.config.json"
$scriptRoot = Join-Path $WorkingRoot "Scripts"
$folders = @("Reports", "Staging", "Logs", "Failed", "Secrets", "State", "Scripts")
foreach ($folder in $folders) {
    [void](New-Item -ItemType Directory -Path (Join-Path $WorkingRoot $folder) -Force)
}

Get-ChildItem -LiteralPath $PSScriptRoot -File | Where-Object {
    $_.Extension -in @(".ps1", ".py", ".json", ".bat", ".md")
} | Copy-Item -Destination $scriptRoot -Force

$configPath = Join-Path $scriptRoot "crystal-export.config.json"
$config = Get-Content -LiteralPath $sourceConfig -Raw -Encoding UTF8 | ConvertFrom-Json
Set-JsonProperty -Object $config -Name "ProjectRoot" -Value $projectRoot
Set-JsonProperty -Object $config -Name "WorkingRoot" -Value $WorkingRoot
$config.Report.LocalPath = Join-Path $WorkingRoot "Reports\DeliveryList.rpt"
$config.Database.CredentialFile = Join-Path $WorkingRoot "Secrets\aw-sql-password.txt"
$config | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $configPath -Encoding UTF8

$repoReport = Join-Path $projectRoot "DeliveryList.rpt"
$reportSource = if (Test-Path -LiteralPath $repoReport -PathType Leaf) {
    $repoReport
}
else {
    [string]$config.Report.SourcePath
}
if (-not (Test-Path -LiteralPath $reportSource -PathType Leaf)) {
    throw "DeliveryList.rpt was not found in the project or at $($config.Report.SourcePath)"
}
Copy-Item -LiteralPath $reportSource -Destination $config.Report.LocalPath -Force
Write-Host "Copied report to $($config.Report.LocalPath)"

$securePassword = Read-Host "Enter the SQL password for $($config.Database.User) on $($config.Database.Server)" -AsSecureString
$securePassword | ConvertFrom-SecureString | Set-Content -LiteralPath $config.Database.CredentialFile -Encoding UTF8

$identity = "$env:USERDOMAIN\$env:USERNAME"
try {
    & icacls.exe (Join-Path $WorkingRoot "Secrets") /inheritance:r /grant:r "${identity}:(OI)(CI)F" /T | Out-Null
}
catch {
    Write-Warning "The Secrets folder ACL could not be tightened automatically: $($_.Exception.Message)"
}

$runner = Join-Path $scriptRoot "Run-DeliveryListAutomation.ps1"
$powerShellCandidates = New-Object System.Collections.Generic.List[string]
$powerShellCandidates.Add((Join-Path $env:WINDIR "System32\WindowsPowerShell\v1.0\powershell.exe"))
if ([Environment]::Is64BitOperatingSystem) {
    $powerShellCandidates.Add((Join-Path $env:WINDIR "SysWOW64\WindowsPowerShell\v1.0\powershell.exe"))
}

$selectedPowerShell = $null
foreach ($candidate in $powerShellCandidates | Select-Object -Unique) {
    if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
        continue
    }
    Write-Host "Testing Crystal runtime with $candidate"
    & $candidate -NoProfile -ExecutionPolicy Bypass -File $runner -Mode RuntimeTest -ConfigPath $configPath
    if ($LASTEXITCODE -eq 0) {
        $selectedPowerShell = $candidate
        break
    }
}
if (-not $selectedPowerShell) {
    throw @"
The installed SAP Crystal Reports .NET runtime could not be loaded in either 64-bit or 32-bit Windows PowerShell.
This package does not bundle SAP runtime files. Ask IT to install the matching SAP Crystal Reports .NET runtime used by A+W, then run setup again.
Review logs under $WorkingRoot\Logs for the exact missing assembly or architecture error.
"@
}

$detectionPath = Join-Path $WorkingRoot "State\runtime-detection.json"
$detection = Get-Content -LiteralPath $detectionPath -Raw -Encoding UTF8 | ConvertFrom-Json
$config = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
$config.Runtime.PowerShellPath = $selectedPowerShell
$config.Runtime.AssemblyPaths = @($detection.AssemblyPaths)
$config | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $configPath -Encoding UTF8

$incrementalCmd = Join-Path $WorkingRoot "Run-Incremental.cmd"
$fullCmd = Join-Path $WorkingRoot "Run-Full.cmd"
$testCmd = Join-Path $WorkingRoot "Run-Test.cmd"
@"
@echo off
"$selectedPowerShell" -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "$runner" -Mode Incremental -ConfigPath "$configPath"
exit /b %errorlevel%
"@ | Set-Content -LiteralPath $incrementalCmd -Encoding ASCII
@"
@echo off
"$selectedPowerShell" -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "$runner" -Mode Full -ConfigPath "$configPath"
exit /b %errorlevel%
"@ | Set-Content -LiteralPath $fullCmd -Encoding ASCII
@"
@echo off
set /p DELIVERY_DATE=Enter a known delivery date (MM/DD/YYYY): 
"$selectedPowerShell" -NoProfile -ExecutionPolicy Bypass -File "$runner" -Mode Test -DeliveryDate "%DELIVERY_DATE%" -ConfigPath "$configPath"
pause
"@ | Set-Content -LiteralPath $testCmd -Encoding ASCII

Write-Host ""
Write-Host "Setup completed." -ForegroundColor Green
Write-Host "1. Double-click $testCmd and test a date that you know contains delivery-list rows."
Write-Host "2. Confirm the workbook appears in $($config.DestinationFolder)."
Write-Host "3. Run Install-DeliveryListAutomationTasks.bat from $scriptRoot."
Write-Host ""
