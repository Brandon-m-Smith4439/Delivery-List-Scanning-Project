# File: automation/crystal_delivery_export/Run-DeliveryListAutomation.ps1
[CmdletBinding()]
param(
    [ValidateSet("RuntimeTest", "Test", "Incremental", "Full")]
    [string]$Mode = "Incremental",

    [datetime]$DeliveryDate,

    [string]$ConfigPath = (Join-Path $PSScriptRoot "crystal-export.config.json")
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-AutomationLog {
    param(
        [Parameter(Mandatory = $true)][string]$Message,
        [ValidateSet("INFO", "WARN", "ERROR")][string]$Level = "INFO"
    )

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$timestamp] [$Level] $Message"
    Write-Host $line
    if ($script:LogPath) {
        Add-Content -LiteralPath $script:LogPath -Value $line -Encoding UTF8
    }
}

function Read-AutomationConfig {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Automation configuration was not found: $Path"
    }
    return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Get-CrystalAssemblyPaths {
    param([Parameter(Mandatory = $true)]$Config)

    $requiredNames = @(
        "CrystalDecisions.Shared.dll",
        "CrystalDecisions.ReportSource.dll",
        "CrystalDecisions.CrystalReports.Engine.dll"
    )
    $configured = @($Config.Runtime.AssemblyPaths | Where-Object { $_ })
    $resolved = New-Object System.Collections.Generic.List[string]

    foreach ($requiredName in $requiredNames) {
        $match = $configured | Where-Object { [IO.Path]::GetFileName($_) -ieq $requiredName } | Select-Object -First 1
        if ($match -and (Test-Path -LiteralPath $match -PathType Leaf)) {
            $resolved.Add((Resolve-Path -LiteralPath $match).Path)
            continue
        }

        $searchRoots = @(
            (Join-Path $env:WINDIR "Microsoft.NET\assembly\GAC_MSIL"),
            (Join-Path $env:WINDIR "assembly\GAC_MSIL"),
            (Join-Path $env:ProgramFiles "SAP BusinessObjects"),
            (Join-Path $env:ProgramFiles "Business Objects")
        )
        if (${env:ProgramFiles(x86)}) {
            $searchRoots += (Join-Path ${env:ProgramFiles(x86)} "SAP BusinessObjects")
            $searchRoots += (Join-Path ${env:ProgramFiles(x86)} "Business Objects")
        }

        $candidate = $null
        foreach ($root in $searchRoots | Select-Object -Unique) {
            if (-not $root -or -not (Test-Path -LiteralPath $root -PathType Container)) {
                continue
            }
            $candidate = Get-ChildItem -LiteralPath $root -Filter $requiredName -File -Recurse -ErrorAction SilentlyContinue |
                Sort-Object { try { [version]$_.VersionInfo.FileVersion } catch { [version]'0.0.0.0' } } -Descending |
                Select-Object -First 1
            if ($candidate) {
                break
            }
        }

        if (-not $candidate) {
            throw "Required SAP Crystal Reports .NET assembly was not found: $requiredName"
        }
        $resolved.Add($candidate.FullName)
    }

    return $resolved.ToArray()
}

function Import-CrystalRuntime {
    param([Parameter(Mandatory = $true)]$Config)

    $assemblyPaths = Get-CrystalAssemblyPaths -Config $Config
    foreach ($assemblyPath in $assemblyPaths) {
        [void][Reflection.Assembly]::LoadFrom($assemblyPath)
    }

    $testDocument = New-Object CrystalDecisions.CrystalReports.Engine.ReportDocument
    $testDocument.Close()
    $testDocument.Dispose()

    $detection = [ordered]@{
        PowerShellPath = (Get-Process -Id $PID).Path
        Is64BitProcess = [Environment]::Is64BitProcess
        AssemblyPaths = $assemblyPaths
        DetectedAt = (Get-Date).ToString("o")
    }
    $detectionPath = Join-Path $Config.WorkingRoot "State\runtime-detection.json"
    $detection | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $detectionPath -Encoding UTF8
    return $assemblyPaths
}

function Get-SecureDatabasePassword {
    param([Parameter(Mandatory = $true)]$Config)

    $credentialFile = [string]$Config.Database.CredentialFile
    if (-not (Test-Path -LiteralPath $credentialFile -PathType Leaf)) {
        throw "The encrypted SQL credential file was not found. Run Setup-DeliveryListAutomation.bat first."
    }
    $securePassword = Get-Content -LiteralPath $credentialFile -Raw -Encoding UTF8 | ConvertTo-SecureString
    $credential = New-Object System.Management.Automation.PSCredential($Config.Database.User, $securePassword)
    return $credential.GetNetworkCredential().Password
}

function Set-DocumentDatabaseLogin {
    param(
        [Parameter(Mandatory = $true)]$Document,
        [Parameter(Mandatory = $true)]$Config,
        [Parameter(Mandatory = $true)][string]$Password
    )

    $server = [string]$Config.Database.Server
    $database = [string]$Config.Database.Database
    $user = [string]$Config.Database.User

    try {
        $Document.SetDatabaseLogon($user, $Password, $server, $database)
    }
    catch {
        Write-AutomationLog -Level WARN -Message "Report-level database login returned: $($_.Exception.Message)"
    }

    foreach ($table in @($Document.Database.Tables)) {
        $logonInfo = $table.LogOnInfo
        $connectionInfo = $logonInfo.ConnectionInfo
        $connectionInfo.ServerName = $server
        $connectionInfo.DatabaseName = $database
        $connectionInfo.UserID = $user
        $connectionInfo.Password = $Password
        if ($connectionInfo.PSObject.Properties.Name -contains "IntegratedSecurity") {
            $connectionInfo.IntegratedSecurity = $false
        }
        $logonInfo.ConnectionInfo = $connectionInfo
        $table.ApplyLogOnInfo($logonInfo)
    }
}

function Set-AllDatabaseLogins {
    param(
        [Parameter(Mandatory = $true)]$Report,
        [Parameter(Mandatory = $true)]$Config,
        [Parameter(Mandatory = $true)][string]$Password
    )

    Set-DocumentDatabaseLogin -Document $Report -Config $Config -Password $Password
    foreach ($subreport in @($Report.Subreports)) {
        Set-DocumentDatabaseLogin -Document $subreport -Config $Config -Password $Password
    }
}

function Get-ParameterValueForDate {
    param(
        [Parameter(Mandatory = $true)]$Report,
        [Parameter(Mandatory = $true)]$Config,
        [Parameter(Mandatory = $true)][datetime]$Date
    )

    $parameterName = [string]$Config.Report.ParameterName
    $parameterField = @($Report.DataDefinition.ParameterFields) |
        Where-Object { $_.Name -ieq $parameterName } |
        Select-Object -First 1
    if (-not $parameterField) {
        throw "Crystal parameter '$parameterName' was not found in the report."
    }

    $kind = [string]$parameterField.ParameterValueKind
    if ($kind -match "String") {
        return $Date.ToString([string]$Config.Report.StringDateFormat, [Globalization.CultureInfo]::InvariantCulture)
    }
    return $Date.Date
}

function Test-XlsxFile {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][int64]$MinimumBytes
    )

    $file = Get-Item -LiteralPath $Path -ErrorAction Stop
    if ($file.Length -lt $MinimumBytes) {
        throw "Exported workbook is unexpectedly small: $($file.Length) bytes."
    }
    $stream = [IO.File]::OpenRead($Path)
    try {
        $first = $stream.ReadByte()
        $second = $stream.ReadByte()
    }
    finally {
        $stream.Dispose()
    }
    if ($first -ne 0x50 -or $second -ne 0x4B) {
        throw "Exported file is not a valid XLSX/ZIP workbook."
    }
}

function Publish-Workbook {
    param(
        [Parameter(Mandatory = $true)][string]$LocalPath,
        [Parameter(Mandatory = $true)][string]$DestinationFolder,
        [Parameter(Mandatory = $true)][string]$FileName
    )

    if (-not (Test-Path -LiteralPath $DestinationFolder -PathType Container)) {
        throw "Destination folder is unavailable: $DestinationFolder"
    }

    $finalPath = Join-Path $DestinationFolder $FileName
    $partialPath = Join-Path $DestinationFolder ($FileName + ".partial")
    if (Test-Path -LiteralPath $partialPath) {
        Remove-Item -LiteralPath $partialPath -Force
    }

    $newHash = (Get-FileHash -LiteralPath $LocalPath -Algorithm SHA256).Hash
    if (Test-Path -LiteralPath $finalPath -PathType Leaf) {
        $existingHash = (Get-FileHash -LiteralPath $finalPath -Algorithm SHA256).Hash
        if ($existingHash -eq $newHash) {
            return [ordered]@{ Path = $finalPath; Published = $false; Reason = "unchanged"; Sha256 = $newHash }
        }
    }

    Copy-Item -LiteralPath $LocalPath -Destination $partialPath -Force
    Test-XlsxFile -Path $partialPath -MinimumBytes 2048
    Move-Item -LiteralPath $partialPath -Destination $finalPath -Force
    return [ordered]@{ Path = $finalPath; Published = $true; Reason = "updated"; Sha256 = $newHash }
}

function Export-DeliveryDate {
    param(
        [Parameter(Mandatory = $true)]$Config,
        [Parameter(Mandatory = $true)][string]$Password,
        [Parameter(Mandatory = $true)][datetime]$Date
    )

    $reportPath = [string]$Config.Report.LocalPath
    if (-not (Test-Path -LiteralPath $reportPath -PathType Leaf)) {
        throw "Local Crystal report was not found: $reportPath"
    }

    $fileName = [string]::Format([Globalization.CultureInfo]::InvariantCulture, [string]$Config.Report.OutputNameFormat, $Date)
    $stagingPath = Join-Path $Config.WorkingRoot ("Staging\" + $fileName)
    $report = New-Object CrystalDecisions.CrystalReports.Engine.ReportDocument

    try {
        $report.Load($reportPath)
        Set-AllDatabaseLogins -Report $report -Config $Config -Password $Password
        $parameterValue = Get-ParameterValueForDate -Report $report -Config $Config -Date $Date
        $report.SetParameterValue([string]$Config.Report.ParameterName, $parameterValue)
        $report.Refresh()

        if (-not $report.HasRecords) {
            Write-AutomationLog -Message "$($Date.ToString('yyyy-MM-dd')): no report records; no workbook published."
            return [ordered]@{ Date = $Date.ToString("yyyy-MM-dd"); Status = "no-records"; Published = $false }
        }

        if (Test-Path -LiteralPath $stagingPath) {
            Remove-Item -LiteralPath $stagingPath -Force
        }
        $exportFormat = [Enum]::Parse([CrystalDecisions.Shared.ExportFormatType], [string]$Config.Report.ExportFormat, $true)
        $report.ExportToDisk($exportFormat, $stagingPath)
        Test-XlsxFile -Path $stagingPath -MinimumBytes ([int64]$Config.MinimumWorkbookBytes)
        $publication = Publish-Workbook -LocalPath $stagingPath -DestinationFolder $Config.DestinationFolder -FileName $fileName
        Write-AutomationLog -Message "$($Date.ToString('yyyy-MM-dd')): $($publication.Reason) - $($publication.Path)"
        return [ordered]@{
            Date = $Date.ToString("yyyy-MM-dd")
            Status = $publication.Reason
            Published = [bool]$publication.Published
            Path = $publication.Path
            Sha256 = $publication.Sha256
        }
    }
    finally {
        try { $report.Close() } catch { }
        try { $report.Dispose() } catch { }
        if (Test-Path -LiteralPath $stagingPath) {
            Remove-Item -LiteralPath $stagingPath -Force -ErrorAction SilentlyContinue
        }
    }
}

function Get-DateSequence {
    param(
        [Parameter(Mandatory = $true)][datetime]$StartDate,
        [Parameter(Mandatory = $true)][datetime]$EndDate
    )

    $dates = New-Object System.Collections.Generic.List[datetime]
    for ($current = $StartDate.Date; $current -le $EndDate.Date; $current = $current.AddDays(1)) {
        $dates.Add($current)
    }
    return $dates.ToArray()
}

function Get-RequestedDates {
    param(
        [Parameter(Mandatory = $true)]$Config,
        [Parameter(Mandatory = $true)][string]$RequestedMode,
        [datetime]$RequestedDate
    )

    if ($RequestedMode -eq "Test") {
        if (-not $PSBoundParameters.ContainsKey("RequestedDate") -or $RequestedDate -eq [datetime]::MinValue) {
            throw "Test mode requires -DeliveryDate."
        }
        return @($RequestedDate.Date)
    }

    $today = (Get-Date).Date
    if ($RequestedMode -eq "Full") {
        $start = $today.AddDays(-[int]$Config.Schedule.FullPastDays)
        $end = $today.AddDays([int]$Config.Schedule.FullFutureDays)
    }
    else {
        $start = $today.AddDays(-[int]$Config.Schedule.IncrementalPastDays)
        $end = $today.AddDays([int]$Config.Schedule.IncrementalFutureDays)
    }
    return Get-DateSequence -StartDate $start -EndDate $end
}

function Invoke-ScannerImport {
    param(
        [Parameter(Mandatory = $true)]$Config,
        [Parameter(Mandatory = $true)][datetime]$OldestDate
    )

    if (-not [bool]$Config.Import.Enabled) {
        Write-AutomationLog -Message "Scanner import is disabled in the configuration."
        return
    }

    $importScript = Join-Path $PSScriptRoot "import_delivery_folder.py"
    if (-not (Test-Path -LiteralPath $importScript -PathType Leaf)) {
        throw "Scanner import wrapper was not found: $importScript"
    }

    $arguments = New-Object System.Collections.Generic.List[string]
    foreach ($argument in @($Config.Import.PythonLauncherArguments)) {
        $arguments.Add([string]$argument)
    }
    $arguments.Add($importScript)
    $arguments.Add("--project-root")
    $arguments.Add([string]$Config.ProjectRoot)
    $arguments.Add("--folder")
    $arguments.Add([string]$Config.DestinationFolder)
    $arguments.Add("--date-from")
    $arguments.Add($OldestDate.ToString("yyyy-MM-dd"))
    $arguments.Add("--user")
    $arguments.Add("crystal-auto-import")

    Write-AutomationLog -Message "Starting Delivery List Scanner folder import."
    $output = & ([string]$Config.Import.PythonLauncher) $arguments.ToArray() 2>&1
    $exitCode = $LASTEXITCODE
    foreach ($line in @($output)) {
        Write-AutomationLog -Message "Importer: $line"
    }
    if ($exitCode -ne 0) {
        throw "Delivery List Scanner import exited with code $exitCode."
    }
    Write-AutomationLog -Message "Delivery List Scanner folder import completed."
}

$config = Read-AutomationConfig -Path $ConfigPath
$workingRoot = [string]$config.WorkingRoot
$requiredFolders = @("Reports", "Staging", "Logs", "Failed", "Secrets", "State")
foreach ($folder in $requiredFolders) {
    [void](New-Item -ItemType Directory -Path (Join-Path $workingRoot $folder) -Force)
}
$script:LogPath = Join-Path $workingRoot ("Logs\delivery-list-export-" + (Get-Date -Format "yyyy-MM-dd") + ".log")

$mutex = New-Object Threading.Mutex($false, "Local\BFSDeliveryListAutomation")
$hasMutex = $false
try {
    $hasMutex = $mutex.WaitOne(0)
    if (-not $hasMutex) {
        Write-AutomationLog -Level WARN -Message "Another delivery-list automation run is still active; this run is skipped."
        exit 0
    }

    Write-AutomationLog -Message "Automation started in $Mode mode."
    $assemblyPaths = Import-CrystalRuntime -Config $config
    Write-AutomationLog -Message "Loaded SAP Crystal runtime: $($assemblyPaths -join '; ')"

    if ($Mode -eq "RuntimeTest") {
        Write-AutomationLog -Message "SAP Crystal runtime test passed in this PowerShell process."
        exit 0
    }

    $password = Get-SecureDatabasePassword -Config $config
    $dates = @(Get-RequestedDates -Config $config -RequestedMode $Mode -RequestedDate $DeliveryDate)
    if ($dates.Count -eq 0) {
        throw "No delivery dates were selected."
    }

    $results = New-Object System.Collections.Generic.List[object]
    $failures = New-Object System.Collections.Generic.List[object]
    foreach ($date in $dates) {
        try {
            $results.Add((Export-DeliveryDate -Config $config -Password $password -Date $date))
        }
        catch {
            $failure = [ordered]@{ Date = $date.ToString("yyyy-MM-dd"); Error = $_.Exception.Message }
            $failures.Add($failure)
            Write-AutomationLog -Level ERROR -Message "$($failure.Date): $($failure.Error)"
        }
    }

    if ($Mode -ne "RuntimeTest") {
        Invoke-ScannerImport -Config $config -OldestDate (($dates | Sort-Object | Select-Object -First 1).Date)
    }

    $status = [ordered]@{
        Mode = $Mode
        CompletedAt = (Get-Date).ToString("o")
        DateCount = $dates.Count
        PublishedCount = @($results | Where-Object { $_.Published }).Count
        NoRecordCount = @($results | Where-Object { $_.Status -eq "no-records" }).Count
        FailureCount = $failures.Count
        Results = $results
        Failures = $failures
    }
    $statusPath = Join-Path $workingRoot "State\last-run.json"
    $status | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $statusPath -Encoding UTF8

    if ($failures.Count -gt 0) {
        throw "$($failures.Count) delivery-date export(s) failed. Review $script:LogPath"
    }
    Write-AutomationLog -Message "Automation completed successfully."
}
catch {
    Write-AutomationLog -Level ERROR -Message $_.Exception.Message
    exit 1
}
finally {
    if ($hasMutex) {
        try { $mutex.ReleaseMutex() } catch { }
    }
    $mutex.Dispose()
}
