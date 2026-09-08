# File: automation/sql_delivery_export/Verify-DeliveryListSqlAutomation.ps1
[CmdletBinding()]
param(
    [string]$ConfigPath = "C:\DeliveryListAutomation\Scripts\sql-export.config.json",
    [string]$DeliveryDate = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function ConvertTo-VerificationDate {
    param([Parameter(Mandatory = $true)][string]$Value)

    $parsed = [datetime]::MinValue
    $formats = [string[]]@("MM/dd/yyyy", "M/d/yyyy", "MM/d/yyyy", "M/dd/yyyy", "yyyy-MM-dd")
    $culture = [Globalization.CultureInfo]::InvariantCulture
    $styles = [Globalization.DateTimeStyles]::AllowWhiteSpaces
    if (-not [datetime]::TryParseExact($Value.Trim(), $formats, $culture, $styles, [ref]$parsed)) {
        throw "The verification date must be entered as MM/DD/YYYY or YYYY-MM-DD."
    }
    return $parsed.Date
}

function Assert-PowerShellSyntax {
    param([Parameter(Mandatory = $true)][string]$Folder)

    $paths = @(
        Get-ChildItem -LiteralPath $Folder -Filter "*.ps1" -File -ErrorAction Stop |
            Select-Object -ExpandProperty FullName
    )
    foreach ($path in $paths) {
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
    Write-Host "PowerShell syntax check passed for $($paths.Count) scripts." -ForegroundColor Green
}

function Require-DateInCollection {
    param(
        [Parameter(Mandatory = $true)]$Values,
        [Parameter(Mandatory = $true)][string]$DateKey,
        [Parameter(Mandatory = $true)][string]$Label
    )

    $cleanValues = @($Values | ForEach-Object { [string]$_ })
    if ($DateKey -notin $cleanValues) {
        throw "$Label did not include $DateKey. The end-to-end verification is incomplete."
    }
}

if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
    throw "Automation configuration was not found: $ConfigPath"
}
$config = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
$scriptRoot = Split-Path -Parent $ConfigPath
$runner = Join-Path $scriptRoot "Run-DeliveryListSqlAutomation.ps1"
$importer = Join-Path $scriptRoot "import_delivery_folder.py"
$validator = Join-Path $scriptRoot "verify_delivery_import.py"
foreach ($requiredPath in @($runner, $importer, $validator)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        throw "Required verification file is missing: $requiredPath"
    }
}

Assert-PowerShellSyntax -Folder $scriptRoot

$powerShellPath = [string]$config.Runtime.PowerShellPath
if ([string]::IsNullOrWhiteSpace($powerShellPath)) {
    $powerShellPath = Join-Path $env:WINDIR "System32\WindowsPowerShell\v1.0\powershell.exe"
}
if (-not (Test-Path -LiteralPath $powerShellPath -PathType Leaf)) {
    throw "Windows PowerShell was not found: $powerShellPath"
}

$pythonPath = [string]$config.Runtime.PythonPath
$pythonArguments = @($config.Runtime.PythonArguments | ForEach-Object { [string]$_ })
if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw "Configured Python runtime was not found: $pythonPath"
}

if ([string]::IsNullOrWhiteSpace($DeliveryDate)) {
    $DeliveryDate = Read-Host "Enter a known delivery date to query, export, import, and verify (MM/DD/YYYY)"
}
$verificationDate = ConvertTo-VerificationDate -Value $DeliveryDate
$dateKey = $verificationDate.ToString("yyyy-MM-dd")

Write-Host ""
Write-Host "Step 1 of 4: Running SQL/runtime preflight..." -ForegroundColor Cyan
& $powerShellPath `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File $runner `
    -Mode RuntimeTest `
    -RunAction SqlExportAndImport `
    -ConfigPath $ConfigPath
if ($LASTEXITCODE -ne 0) {
    throw "Runtime preflight failed. Review $($config.WorkingRoot)\Logs."
}

Write-Host ""
Write-Host "Step 2 of 4: Querying A+W SQL and rebuilding the workbook for $dateKey..." -ForegroundColor Cyan
& $powerShellPath `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File $runner `
    -Mode Test `
    -RunAction SqlExportOnly `
    -DeliveryDate $dateKey `
    -ConfigPath $ConfigPath
if ($LASTEXITCODE -ne 0) {
    throw "The SQL query/export test failed. Review $($config.WorkingRoot)\Logs."
}

$lastRunPath = Join-Path $config.WorkingRoot "State\last-run.json"
if (-not (Test-Path -LiteralPath $lastRunPath -PathType Leaf)) {
    throw "The runner did not create its final summary: $lastRunPath"
}
$summary = Get-Content -LiteralPath $lastRunPath -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not [bool]$summary.succeeded) {
    throw "The final SQL/export summary reports failure: $([string]$summary.error)"
}
if ([string]$summary.runAction -ne "SqlExportOnly") {
    throw "The verification did not execute the required SqlExportOnly action."
}

$runLogPath = [string]$summary.logPath
if (-not [string]::IsNullOrWhiteSpace($runLogPath) -and (Test-Path -LiteralPath $runLogPath -PathType Leaf)) {
    $runLogText = Get-Content -LiteralPath $runLogPath -Raw -Encoding UTF8
    if ($runLogText -match "Known-date comparison differs") {
        throw "The known-date SQL count comparison failed. Review $runLogPath before enabling the schedule."
    }
    if ($config.PSObject.Properties.Name -contains "Validation") {
        $knownDate = [string]$config.Validation.KnownDeliveryDate
        if (-not [string]::IsNullOrWhiteSpace($knownDate)) {
            $knownDateKey = (ConvertTo-VerificationDate -Value $knownDate).ToString("yyyy-MM-dd")
            if ($knownDateKey -eq $dateKey -and $runLogText -notmatch "Known-date count comparison passed") {
                throw "The selected known date did not record a passing expected-count comparison. Review $runLogPath."
            }
        }
    }
}

Require-DateInCollection -Values @($summary.checkedDates) -DateKey $dateKey -Label "Checked dates"
Require-DateInCollection -Values @($summary.sourceDates) -DateKey $dateKey -Label "SQL source dates"
Require-DateInCollection -Values @($summary.publishedDates) -DateKey $dateKey -Label "Published workbook dates"

$outputNameFormat = [string]$config.Report.OutputNameFormat
$fileName = [string]::Format(
    [Globalization.CultureInfo]::InvariantCulture,
    $outputNameFormat,
    $verificationDate
)
$workbookPath = Join-Path ([string]$config.DestinationFolder) $fileName
if (-not (Test-Path -LiteralPath $workbookPath -PathType Leaf)) {
    throw "The expected validated workbook was not published: $workbookPath"
}

$stateRoot = Join-Path $config.WorkingRoot "State"
[void](New-Item -ItemType Directory -Path $stateRoot -Force)
$token = [guid]::NewGuid().ToString("N")
$syncRequestPath = Join-Path $stateRoot "verification-sync-$token.json"
$importResultPath = Join-Path $stateRoot "verification-import-$token.json"

try {
    Write-Host ""
    Write-Host "Step 3 of 4: Forcing the maintained scanner importer to verify/import $dateKey..." -ForegroundColor Cyan
    $syncRequest = [ordered]@{
        targetDates = @($dateKey)
        forceImportDates = @($dateKey)
    }
    $syncRequest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $syncRequestPath -Encoding UTF8

    & $pythonPath @pythonArguments $importer `
        --project-root ([string]$config.ProjectRoot) `
        --folder ([string]$config.DestinationFolder) `
        --date-from $dateKey `
        --date-to $dateKey `
        --user "sql-automation-verification" `
        --initialize-store "true" `
        --result-path $importResultPath `
        --sync-request-path $syncRequestPath
    if ($LASTEXITCODE -ne 0) {
        throw "The maintained scanner importer failed for $dateKey."
    }
    if (-not (Test-Path -LiteralPath $importResultPath -PathType Leaf)) {
        throw "The scanner importer did not create its normalized verification result."
    }

    $importResult = Get-Content -LiteralPath $importResultPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not [bool]$importResult.ok) {
        throw "The normalized scanner import result reports failure for $dateKey."
    }
    Require-DateInCollection -Values @($importResult.importedDates) -DateKey $dateKey -Label "Scanner verified/imported dates"

    $matchingResults = @($importResult.files | Where-Object {
        [string]$_.deliveryDate -eq $dateKey
    })
    if ($matchingResults.Count -eq 0) {
        throw "No normalized scanner import result was recorded for $dateKey."
    }
    $failedResults = @($matchingResults | Where-Object {
        [string]$_.classification -eq "failed"
    })
    if ($failedResults.Count -gt 0) {
        $messages = @($failedResults | ForEach-Object {
            @($_.errors | ForEach-Object { [string]$_ }) -join " | "
        }) -join [Environment]::NewLine
        throw "The scanner import result contains a failed workbook for $dateKey.`n$messages"
    }

    Write-Host ""
    Write-Host "Step 4 of 4: Comparing workbook stage definitions with the scanner store..." -ForegroundColor Cyan
    & $pythonPath @pythonArguments $validator `
        --project-root ([string]$config.ProjectRoot) `
        --workbook $workbookPath `
        --delivery-date $dateKey
    if ($LASTEXITCODE -ne 0) {
        throw "The workbook-to-scanner stage comparison failed."
    }
}
finally {
    Remove-Item -LiteralPath $syncRequestPath -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $importResultPath -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "End-to-end delivery-list automation verification passed." -ForegroundColor Green
Write-Host "- A+W SQL returned delivery rows for $dateKey"
Write-Host "- The workbook was rebuilt, validated, and published: $workbookPath"
Write-Host "- The maintained scanner importer was explicitly invoked for the selected date"
Write-Host "- The normalized import result contained no failed workbook"
Write-Host "- Every expected workbook stage list exists in the scanner store"
Write-Host "- SQL/export run summary: $lastRunPath"
