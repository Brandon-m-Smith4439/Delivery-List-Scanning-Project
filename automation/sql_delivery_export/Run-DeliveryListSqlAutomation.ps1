# File: automation/sql_delivery_export/Run-DeliveryListSqlAutomation.ps1
[CmdletBinding()]
param(
    [ValidateSet("RuntimeTest", "Test", "Incremental", "Full", "Custom", "FolderImport")]
    [string]$Mode = "Incremental",

    [ValidateSet("Configured", "SqlExportOnly", "SqlExportAndImport", "FolderImportOnly", "RejectSyncOnly")]
    [string]$RunAction = "Configured",

    [string]$DeliveryDate = "",

    [string]$DateFrom = "",

    [string]$DateTo = "",

    [string]$ConfigPath = (Join-Path $PSScriptRoot "sql-export.config.json"),

    [string]$LogPath = "",

    [string]$SummaryPath = "",

    [string]$RequestId = "",

    [switch]$FailIfBusy
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:LogPath = $null
$script:PendingLogLines = New-Object System.Collections.Generic.List[string]
$script:Config = $null
$script:LockStream = $null
$script:CheckedDates = New-Object System.Collections.Generic.List[datetime]
$script:SourceDates = New-Object System.Collections.Generic.List[datetime]
$script:PublishedDates = New-Object System.Collections.Generic.List[datetime]
$script:PendingImportDates = New-Object System.Collections.Generic.List[datetime]
$script:ImportedDates = New-Object System.Collections.Generic.List[datetime]
$script:ImportResults = @()
$script:DirectImportPayloads = New-Object System.Collections.Generic.List[object]
$script:AwRejectSyncPayload = $null
$script:AwRejectSyncResult = $null
$script:AwCuttingSyncPayload = $null
$script:AwCuttingSyncResult = $null
$script:ResolvedAction = $RunAction
$script:StartedAt = (Get-Date).ToUniversalTime().ToString("o")
$script:RunId = $(if ([string]::IsNullOrWhiteSpace([string]$RequestId)) { "scheduled-$($script:StartedAt)" } else { [string]$RequestId })
$script:StepNumber = 0
$script:RunStopwatch = [System.Diagnostics.Stopwatch]::StartNew()
$script:SkipSummary = $false
$script:LastRawDeliveryRowCount = 0
$script:LastRawRemakeLineCount = 0
$script:LastExcludedDeliveryRows = @()
$script:LastEligibilityRule = ""
$script:LastStatusDiagnosticSummary = ""
$script:VerifiedSourceExclusions = @()
$script:VerifiedSourceOrderExclusions = @()
$script:VerifiedSourceManualOverrides = @()
$script:SupersededOrderCandidates = @()
# Retained in run summaries for backward compatibility with v0.243. v0.245 no
# longer defers dates by production status because those values are diagnostic.
$script:SafetyDeferredDates = New-Object System.Collections.Generic.List[datetime]
$script:SafetyDeferredDetails = New-Object System.Collections.Generic.List[object]

function Write-AutomationLog {
    param(
        [Parameter(Mandatory = $true)][string]$Message,
        [ValidateSet("DEBUG", "INFO", "WARN", "ERROR")][string]$Level = "INFO"
    )

    $line = "{0} [{1}] {2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Level, $Message
    Write-Host $line
    if ($script:LogPath) {
        Add-Content -LiteralPath $script:LogPath -Value $line -Encoding UTF8
    }
    else {
        # Scheduled runs do not know their generated log path until the config is
        # loaded. Buffer those startup lines so the persisted log still begins at
        # STEP 01 instead of silently losing the earliest diagnostics.
        $script:PendingLogLines.Add($line)
    }
}

function Write-AutomationStep {
    param(
        [Parameter(Mandatory = $true)][string]$Message,
        [ValidateSet("INFO", "WARN", "ERROR")][string]$Level = "INFO"
    )

    $script:StepNumber++
    $elapsedSeconds = [Math]::Round($script:RunStopwatch.Elapsed.TotalSeconds, 3)
    Write-AutomationLog -Message ("STEP {0:D2} | +{1:N3}s | {2}" -f $script:StepNumber, $elapsedSeconds, $Message) -Level $Level
}

function Write-AutomationDebug {
    param([Parameter(Mandatory = $true)][string]$Message)

    $elapsedSeconds = [Math]::Round($script:RunStopwatch.Elapsed.TotalSeconds, 3)
    Write-AutomationLog -Message ("+{0:N3}s | {1}" -f $elapsedSeconds, $Message) -Level "DEBUG"
}

function Get-AutomationDateListText {
    param([Parameter(Mandatory = $false)][AllowEmptyCollection()][datetime[]]$Dates = @())

    if ($null -eq $Dates -or $Dates.Count -eq 0) {
        return "none"
    }
    return (@($Dates | Sort-Object -Unique | ForEach-Object { $_.ToString("yyyy-MM-dd") }) -join ", ")
}

function Get-RequiredProperty {
    param(
        [Parameter(Mandatory = $true)]$Object,
        [Parameter(Mandatory = $true)][string]$Name
    )

    if ($null -eq $Object -or -not ($Object.PSObject.Properties.Name -contains $Name)) {
        throw "Required configuration property is missing: $Name"
    }
    return $Object.$Name
}

function Read-AutomationConfig {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Automation configuration was not found: $Path"
    }
    $config = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
    [void](Get-RequiredProperty -Object $config -Name "WorkingRoot")
    [void](Get-RequiredProperty -Object $config -Name "DestinationFolder")
    [void](Get-RequiredProperty -Object $config -Name "Database")
    [void](Get-RequiredProperty -Object $config -Name "Runtime")
    [void](Get-RequiredProperty -Object $config -Name "SourceMapping")
    return $config
}

function Initialize-WorkingFolders {
    param([Parameter(Mandatory = $true)]$Config)

    foreach ($name in @("Staging", "Logs", "Failed", "State", "Scripts")) {
        [void](New-Item -ItemType Directory -Path (Join-Path $Config.WorkingRoot $name) -Force)
    }

    # Browser-started runs provide their log path before configuration is read,
    # allowing the GUI to show startup and validation failures immediately. Task
    # Scheduler runs continue to receive an automatically generated per-run log.
    if ([string]::IsNullOrWhiteSpace([string]$script:LogPath)) {
        $runStamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $script:LogPath = Join-Path $Config.WorkingRoot ("Logs\sql-export-{0}-pid{1}.log" -f $runStamp, $PID)
    }
    $logFolder = Split-Path -Parent $script:LogPath
    if (-not [string]::IsNullOrWhiteSpace($logFolder)) {
        [void](New-Item -ItemType Directory -Path $logFolder -Force)
    }
    if (-not (Test-Path -LiteralPath $script:LogPath -PathType Leaf)) {
        [void](New-Item -ItemType File -Path $script:LogPath -Force)
    }
    if ($script:PendingLogLines.Count -gt 0) {
        Add-Content -LiteralPath $script:LogPath -Value $script:PendingLogLines.ToArray() -Encoding UTF8
        $script:PendingLogLines.Clear()
    }
}

function Acquire-AutomationLock {
    param(
        [Parameter(Mandatory = $true)]$Config,
        [bool]$FailWhenBusy = $false
    )

    $lockPath = Join-Path $Config.WorkingRoot "State\run.lock"
    try {
        $script:LockStream = [System.IO.File]::Open(
            $lockPath,
            [System.IO.FileMode]::OpenOrCreate,
            [System.IO.FileAccess]::ReadWrite,
            [System.IO.FileShare]::None
        )
        $bytes = [System.Text.Encoding]::UTF8.GetBytes("PID=$PID`r`nStarted=$(Get-Date -Format o)`r`n")
        $script:LockStream.SetLength(0)
        $script:LockStream.Write($bytes, 0, $bytes.Length)
        $script:LockStream.Flush()
        return $true
    }
    catch [System.IO.IOException] {
        $message = "Another SQL delivery-list automation run is already active."
        if ($FailWhenBusy) {
            throw "$message The manual request was not started. Wait for the active run to finish and try again."
        }
        Write-AutomationLog -Message "$message This scheduled run will exit without replacing the active run summary." -Level "WARN"
        $script:SkipSummary = $true
        return $false
    }
}

function Release-AutomationLock {
    if ($null -ne $script:LockStream) {
        $script:LockStream.Dispose()
        $script:LockStream = $null
    }
}

function ConvertTo-DeliveryDate {
    param([Parameter(Mandatory = $true)][string]$Value)

    $parsed = [datetime]::MinValue
    $formats = [string[]]@("MM/dd/yyyy", "M/d/yyyy", "MM/d/yyyy", "M/dd/yyyy", "yyyy-MM-dd")
    $culture = [Globalization.CultureInfo]::InvariantCulture
    $styles = [Globalization.DateTimeStyles]::AllowWhiteSpaces
    if (-not [datetime]::TryParseExact($Value.Trim(), $formats, $culture, $styles, [ref]$parsed)) {
        throw "The delivery date must be entered as MM/DD/YYYY or YYYY-MM-DD."
    }
    return $parsed.Date
}

function Get-DateRange {
    param(
        [Parameter(Mandatory = $true)]$Config,
        [Parameter(Mandatory = $true)][string]$RunMode,
        [string]$RequestedDate,
        [string]$RequestedDateFrom,
        [string]$RequestedDateTo
    )

    if ($RunMode -eq "Test") {
        if ([string]::IsNullOrWhiteSpace($RequestedDate)) {
            throw "Test mode requires -DeliveryDate MM/DD/YYYY."
        }
        return ,(ConvertTo-DeliveryDate -Value $RequestedDate)
    }

    if ($RunMode -in @("Custom", "FolderImport")) {
        if ([string]::IsNullOrWhiteSpace($RequestedDateFrom)) {
            throw "$RunMode mode requires -DateFrom MM/DD/YYYY or YYYY-MM-DD."
        }
        $startDate = ConvertTo-DeliveryDate -Value $RequestedDateFrom
        $endDate = if ([string]::IsNullOrWhiteSpace($RequestedDateTo)) {
            $startDate
        }
        else {
            ConvertTo-DeliveryDate -Value $RequestedDateTo
        }
        if ($endDate -lt $startDate) {
            throw "DateTo cannot be earlier than DateFrom."
        }
        if (($endDate - $startDate).TotalDays -gt 365) {
            throw "The manual date window cannot exceed 365 days."
        }
        $dates = New-Object System.Collections.Generic.List[datetime]
        $cursor = $startDate
        while ($cursor -le $endDate) {
            $dates.Add($cursor)
            $cursor = $cursor.AddDays(1)
        }
        return $dates.ToArray()
    }

    $today = (Get-Date).Date
    if ($RunMode -eq "Incremental") {
        $pastDays = [int]$Config.Schedule.IncrementalPastDays
        $futureDays = [int]$Config.Schedule.IncrementalFutureDays
    }
    else {
        $pastDays = [int]$Config.Schedule.FullPastDays
        $futureDays = [int]$Config.Schedule.FullFutureDays
    }

    $dates = New-Object System.Collections.Generic.List[datetime]
    for ($offset = -$pastDays; $offset -le $futureDays; $offset++) {
        $dates.Add($today.AddDays($offset))
    }
    return $dates.ToArray()
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

function Get-AffectedImportListIds {
    param([AllowNull()]$ImportResults = @())

    $values = @()
    foreach ($result in @($ImportResults)) {
        foreach ($listId in @(Get-OptionalProperty -Object $result -Name "listIds" -DefaultValue @())) {
            if (-not [string]::IsNullOrWhiteSpace([string]$listId)) {
                $values += [string]$listId
            }
        }
        foreach ($stageSummary in @(Get-OptionalProperty -Object $result -Name "stageSummaries" -DefaultValue @())) {
            $listId = [string](Get-OptionalProperty -Object $stageSummary -Name "listId" -DefaultValue "")
            if (-not [string]::IsNullOrWhiteSpace($listId)) {
                $values += $listId
            }
        }
    }
    return @($values | Sort-Object -Unique)
}

function Quote-SqlIdentifier {
    param([Parameter(Mandatory = $true)][string]$Name)

    $trimmed = $Name.Trim()
    if ($trimmed -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') {
        throw "Unsafe SQL identifier in SourceMapping: $Name"
    }
    return "[$trimmed]"
}

function Get-SourceSqlParts {
    param([Parameter(Mandatory = $true)]$Config)

    $mapping = Get-RequiredProperty -Object $Config -Name "SourceMapping"
    $headerColumns = Get-RequiredProperty -Object $mapping -Name "HeaderColumns"
    $itemColumns = Get-RequiredProperty -Object $mapping -Name "ItemColumns"

    return [pscustomobject]@{
        Mapping = $mapping
        Schema = Quote-SqlIdentifier -Name ([string](Get-RequiredProperty -Object $mapping -Name "Schema"))
        HeaderTable = Quote-SqlIdentifier -Name ([string](Get-RequiredProperty -Object $mapping -Name "HeaderTable"))
        ItemTable = Quote-SqlIdentifier -Name ([string](Get-RequiredProperty -Object $mapping -Name "ItemTable"))
        HeaderJoin = Quote-SqlIdentifier -Name ([string](Get-RequiredProperty -Object $mapping -Name "HeaderJoinColumn"))
        ItemJoin = Quote-SqlIdentifier -Name ([string](Get-RequiredProperty -Object $mapping -Name "ItemJoinColumn"))
        DeliveryDate = Quote-SqlIdentifier -Name ([string](Get-RequiredProperty -Object $headerColumns -Name "DeliveryDate"))
        JobNumber = Quote-SqlIdentifier -Name ([string](Get-RequiredProperty -Object $headerColumns -Name "JobNumber"))
        OrderNumber = Quote-SqlIdentifier -Name ([string](Get-RequiredProperty -Object $headerColumns -Name "OrderNumber"))
        Customer = Quote-SqlIdentifier -Name ([string](Get-RequiredProperty -Object $headerColumns -Name "Customer"))
        RemakeFlags = Quote-SqlIdentifier -Name ([string](Get-RequiredProperty -Object $headerColumns -Name "RemakeFlags"))
        Route = Quote-SqlIdentifier -Name ([string](Get-RequiredProperty -Object $headerColumns -Name "Route"))
        OrderStatus = Quote-SqlIdentifier -Name ([string](Get-OptionalProperty -Object $headerColumns -Name "OrderStatus" -DefaultValue "STATUS"))
        ProductionBatch1 = Quote-SqlIdentifier -Name ([string](Get-OptionalProperty -Object $headerColumns -Name "ProductionBatch1" -DefaultValue "LAUF_PROD1"))
        ProductionBatch2 = Quote-SqlIdentifier -Name ([string](Get-OptionalProperty -Object $headerColumns -Name "ProductionBatch2" -DefaultValue "LAUF_PROD2"))
        ProductionBatch3 = Quote-SqlIdentifier -Name ([string](Get-OptionalProperty -Object $headerColumns -Name "ProductionBatch3" -DefaultValue "LAUF_PROD3"))
        HeaderIdentity = Quote-SqlIdentifier -Name ([string](Get-OptionalProperty -Object $headerColumns -Name "HeaderIdentity" -DefaultValue "AH_IDENT"))
        ItemNumber = Quote-SqlIdentifier -Name ([string](Get-RequiredProperty -Object $itemColumns -Name "ItemNumber"))
        ItemStatus = Quote-SqlIdentifier -Name ([string](Get-OptionalProperty -Object $itemColumns -Name "ItemStatus" -DefaultValue "POS_STATUS"))
        Quantity = Quote-SqlIdentifier -Name ([string](Get-RequiredProperty -Object $itemColumns -Name "Quantity"))
        WidthUnits = Quote-SqlIdentifier -Name ([string](Get-RequiredProperty -Object $itemColumns -Name "WidthUnits"))
        HeightUnits = Quote-SqlIdentifier -Name ([string](Get-RequiredProperty -Object $itemColumns -Name "HeightUnits"))
        ProductHeading = Quote-SqlIdentifier -Name ([string](Get-RequiredProperty -Object $itemColumns -Name "ProductHeading"))
    }
}

function New-SqlConnection {
    param([Parameter(Mandatory = $true)]$Config)

    $provider = [string](Get-OptionalProperty -Object $Config.Database -Name "Provider" -DefaultValue "SqlServer")
    if ($provider.Trim().ToLowerInvariant() -ne "sqlserver") {
        throw "Database.Provider must be SqlServer for this exporter."
    }

    $authenticationMode = [string](Get-OptionalProperty -Object $Config.Database -Name "AuthenticationMode" -DefaultValue "Windows")
    if ($authenticationMode -eq "EnvironmentConnectionString") {
        $environmentName = [string](Get-OptionalProperty -Object $Config.Database -Name "ConnectionStringEnvironmentVariable" -DefaultValue "DLS_SOURCE_SQL_CONNECTION_STRING")
        $connectionString = [Environment]::GetEnvironmentVariable($environmentName)
        if ([string]::IsNullOrWhiteSpace($connectionString)) {
            throw "Environment variable $environmentName does not contain the source SQL connection string."
        }
        return New-Object System.Data.SqlClient.SqlConnection($connectionString)
    }

    if ($authenticationMode -ne "Windows") {
        throw "Database.AuthenticationMode must be Windows or EnvironmentConnectionString."
    }

    $builder = New-Object System.Data.SqlClient.SqlConnectionStringBuilder
    $builder["Data Source"] = [string]$Config.Database.Server
    $builder["Initial Catalog"] = [string]$Config.Database.Database
    $builder["Integrated Security"] = $true
    $builder["Application Name"] = "DeliveryListSqlExporter-v121"
    $builder["Connect Timeout"] = [int]$Config.Database.ConnectTimeoutSeconds
    $builder["Encrypt"] = [bool](Get-OptionalProperty -Object $Config.Database -Name "Encrypt" -DefaultValue $false)
    $builder["TrustServerCertificate"] = [bool](Get-OptionalProperty -Object $Config.Database -Name "TrustServerCertificate" -DefaultValue $true)
    return New-Object System.Data.SqlClient.SqlConnection($builder.ConnectionString)
}

function Test-SqlRuntime {
    param([Parameter(Mandatory = $true)]$Config)

    $source = Get-SourceSqlParts -Config $Config
    $connection = New-SqlConnection -Config $Config
    try {
        $connection.Open()
        $command = $connection.CreateCommand()
        $command.CommandTimeout = [int]$Config.Database.QueryTimeoutSeconds
        $command.CommandText = @"
SELECT
    SUSER_SNAME() AS LoginName,
    DB_NAME() AS DatabaseName,
    CAST(SERVERPROPERTY('ProductVersion') AS nvarchar(128)) AS ServerVersion;

SELECT TOP (0)
    h.$($source.OrderNumber),
    h.$($source.DeliveryDate),
    h.$($source.JobNumber),
    h.$($source.Customer),
    h.$($source.RemakeFlags),
    h.$($source.Route),
    h.$($source.OrderStatus),
    h.$($source.ProductionBatch1),
    h.$($source.ProductionBatch2),
    h.$($source.ProductionBatch3),
    h.$($source.HeaderIdentity),
    p.$($source.ItemNumber),
    p.$($source.ItemStatus),
    p.$($source.Quantity),
    p.$($source.WidthUnits),
    p.$($source.HeightUnits),
    p.$($source.ProductHeading)
FROM $($source.Schema).$($source.HeaderTable) h
INNER JOIN $($source.Schema).$($source.ItemTable) p
    ON p.$($source.ItemJoin) = h.$($source.HeaderJoin);
"@
        $reader = $command.ExecuteReader()
        if (-not $reader.Read()) {
            throw "SQL runtime test returned no identity row."
        }
        $loginName = [string]$reader["LoginName"]
        $databaseName = [string]$reader["DatabaseName"]
        $serverVersion = [string]$reader["ServerVersion"]
        $reader.Close()
        $command.Dispose()
        Write-AutomationLog -Message "SQL connection and mapped source columns passed. Login=$loginName Database=$databaseName Version=$serverVersion"
    }
    finally {
        if ($connection.State -ne [System.Data.ConnectionState]::Closed) {
            $connection.Close()
        }
        $connection.Dispose()
    }
}

function Read-VerifiedSourceExclusions {
    param([Parameter(Mandatory = $true)]$Config)

    $paths = New-Object System.Collections.Generic.List[string]
    $paths.Add((Join-Path $PSScriptRoot "verified-source-exclusions.json"))
    $projectRoot = [string](Get-OptionalProperty -Object $Config -Name "ProjectRoot" -DefaultValue "")
    if (-not [string]::IsNullOrWhiteSpace($projectRoot)) {
        $paths.Add((Join-Path $projectRoot "data\superseded-source-exclusions.json"))
    }

    $normalizedByKey = @{}
    foreach ($path in $paths) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            if ($path -like '*verified-source-exclusions.json') {
                Write-AutomationLog -Message (
                    "Verified source-exclusion file was not found. No packaged exclusions were loaded: {0}" -f $path
                ) -Level "WARN"
            }
            continue
        }
        $payload = Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
        $preserveEntries = @(Get-OptionalProperty -Object $payload -Name "preserveEntries" -DefaultValue @())
        foreach ($entry in $preserveEntries) {
            $deliveryDate = ([string](Get-OptionalProperty -Object $entry -Name "deliveryDate" -DefaultValue "")).Trim()
            $orderNumber = ([string](Get-OptionalProperty -Object $entry -Name "orderNumber" -DefaultValue "")).Trim()
            $itemNumber = ([string](Get-OptionalProperty -Object $entry -Name "itemNumber" -DefaultValue "")).Trim().PadLeft(3, '0')
            if ($deliveryDate -match '^\d{4}-\d{2}-\d{2}$' -and $orderNumber -match '^\d+$' -and $itemNumber -match '^\d{3,}$') {
                $key = "${deliveryDate}|${orderNumber}-${itemNumber}"
                [void]$normalizedByKey.Remove($key)
            }
        }
        $entries = @(Get-OptionalProperty -Object $payload -Name "entries" -DefaultValue @())
        foreach ($entry in $entries) {
            $deliveryDate = ([string](Get-OptionalProperty -Object $entry -Name "deliveryDate" -DefaultValue "")).Trim()
            $orderNumber = ([string](Get-OptionalProperty -Object $entry -Name "orderNumber" -DefaultValue "")).Trim()
            $itemNumber = ([string](Get-OptionalProperty -Object $entry -Name "itemNumber" -DefaultValue "")).Trim().PadLeft(3, '0')
            $reason = ([string](Get-OptionalProperty -Object $entry -Name "reason" -DefaultValue "Approved exact superseded-order exclusion.")).Trim()
            if ($deliveryDate -notmatch '^\d{4}-\d{2}-\d{2}$') {
                throw "Source exclusion file contains an invalid deliveryDate: $deliveryDate"
            }
            if ($orderNumber -notmatch '^\d+$' -or $itemNumber -notmatch '^\d{3,}$') {
                throw "Source exclusion file contains an invalid order/item key: $orderNumber-$itemNumber"
            }
            $key = "${deliveryDate}|${orderNumber}-${itemNumber}"
            $normalizedByKey[$key] = [pscustomobject]@{
                deliveryDate = $deliveryDate
                orderNumber = $orderNumber
                itemNumber = $itemNumber
                orderItemKey = "${orderNumber}-${itemNumber}"
                reason = $reason
                sourceFile = [IO.Path]::GetFileName($path)
            }
        }
    }
    return @($normalizedByKey.Values | Sort-Object deliveryDate, orderNumber, itemNumber)
}

function Read-VerifiedSourceOrderExclusions {
    param([Parameter(Mandatory = $true)]$Config)

    $projectRoot = [string](Get-OptionalProperty -Object $Config -Name "ProjectRoot" -DefaultValue "")
    if ([string]::IsNullOrWhiteSpace($projectRoot)) {
        return @()
    }
    $path = Join-Path $projectRoot "data\superseded-source-exclusions.json"
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        return @()
    }

    $payload = Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
    $normalizedByKey = @{}
    foreach ($entry in @(Get-OptionalProperty -Object $payload -Name "orderEntries" -DefaultValue @())) {
        $deliveryDate = ([string](Get-OptionalProperty -Object $entry -Name "deliveryDate" -DefaultValue "")).Trim()
        $orderNumber = ([string](Get-OptionalProperty -Object $entry -Name "orderNumber" -DefaultValue "")).Trim()
        $reason = ([string](Get-OptionalProperty -Object $entry -Name "reason" -DefaultValue "Approved superseded-order removal.")).Trim()
        if ($deliveryDate -notmatch '^\d{4}-\d{2}-\d{2}$') {
            throw "Superseded order exclusion file contains an invalid deliveryDate: $deliveryDate"
        }
        if ($orderNumber -notmatch '^\d+$') {
            throw "Superseded order exclusion file contains an invalid order number: $orderNumber"
        }
        $key = "${deliveryDate}|${orderNumber}"
        $normalizedByKey[$key] = [pscustomobject]@{
            deliveryDate = $deliveryDate
            orderNumber = $orderNumber
            reason = $reason
            sourceFile = [IO.Path]::GetFileName($path)
        }
    }
    return @($normalizedByKey.Values | Sort-Object deliveryDate, orderNumber)
}

function Get-VerifiedSourceOrderExclusionsForDate {
    param([Parameter(Mandatory = $true)][datetime]$Date)

    $dateKey = $Date.ToString("yyyy-MM-dd")
    return @(
        $script:VerifiedSourceOrderExclusions |
            Where-Object { [string]$_.deliveryDate -eq $dateKey }
    )
}

function Read-VerifiedSourceManualOverrides {
    param([Parameter(Mandatory = $true)]$Config)

    $projectRoot = [string](Get-OptionalProperty -Object $Config -Name "ProjectRoot" -DefaultValue "")
    if ([string]::IsNullOrWhiteSpace($projectRoot)) {
        return @()
    }
    $path = Join-Path $projectRoot "data\superseded-source-exclusions.json"
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        return @()
    }
    $payload = Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
    $normalized = New-Object System.Collections.Generic.List[object]
    foreach ($entry in @(Get-OptionalProperty -Object $payload -Name "manualOverrides" -DefaultValue @())) {
        $deliveryDate = ([string](Get-OptionalProperty -Object $entry -Name "deliveryDate" -DefaultValue "")).Trim()
        $sourceOrder = ([string](Get-OptionalProperty -Object $entry -Name "sourceOrderNumber" -DefaultValue "")).Trim()
        $sourceItem = ([string](Get-OptionalProperty -Object $entry -Name "sourceItemNumber" -DefaultValue "")).Trim().PadLeft(3, '0')
        $fields = Get-OptionalProperty -Object $entry -Name "fields" -DefaultValue $null
        if ($deliveryDate -notmatch '^\d{4}-\d{2}-\d{2}$' -or
            $sourceOrder -notmatch '^\d+$' -or $sourceItem -notmatch '^\d{3,}$' -or
            $null -eq $fields) {
            continue
        }
        $normalized.Add([pscustomobject]@{
            deliveryDate = $deliveryDate
            sourceOrderNumber = $sourceOrder
            sourceItemNumber = $sourceItem
            orderItemKey = "${sourceOrder}-${sourceItem}"
            fields = $fields
        })
    }
    return @($normalized.ToArray())
}

function Get-VerifiedSourceManualOverridesForDate {
    param([Parameter(Mandatory = $true)][datetime]$Date)

    $dateKey = $Date.ToString("yyyy-MM-dd")
    return @(
        $script:VerifiedSourceManualOverrides |
            Where-Object { [string]$_.deliveryDate -eq $dateKey }
    )
}

function Get-VerifiedSourceExclusionsForDate {
    param([Parameter(Mandatory = $true)][datetime]$Date)

    $dateKey = $Date.ToString("yyyy-MM-dd")
    return @(
        $script:VerifiedSourceExclusions |
            Where-Object { [string]$_.deliveryDate -eq $dateKey }
    )
}

function Get-StatusCountSummary {
    param([Parameter(Mandatory = $true)]$Counts)

    if ($Counts.Count -eq 0) {
        return "none"
    }
    return @(
        $Counts.GetEnumerator() |
            Sort-Object { [int]$_.Name } |
            ForEach-Object { "{0}={1}" -f [string]$_.Name, [int]$_.Value }
    ) -join ", "
}

function Resolve-SourceRoute {
    param(
        [Parameter(Mandatory = $true)]$Mapping,
        [string]$RawRoute = ""
    )

    $route = [string]$RawRoute
    $route = $route.Trim()
    foreach ($blankValue in @(Get-OptionalProperty -Object $Mapping -Name "BlankRouteValues" -DefaultValue @("", "<n.e.>"))) {
        if ([string]::Equals($route, [string]$blankValue, [StringComparison]::OrdinalIgnoreCase)) {
            return ""
        }
    }

    $routeMappings = Get-OptionalProperty -Object $Mapping -Name "RouteMappings" -DefaultValue $null
    if ($null -ne $routeMappings) {
        foreach ($property in $routeMappings.PSObject.Properties) {
            if ([string]::Equals($route, [string]$property.Name, [StringComparison]::OrdinalIgnoreCase)) {
                return ([string]$property.Value).Trim()
            }
        }
    }
    return $route
}

function Get-SupersededOrderCandidates {
    param(
        [Parameter(Mandatory = $true)]$Rows,
        [Parameter(Mandatory = $true)][datetime]$Date,
        [Parameter(Mandatory = $true)][int64]$RemakeMask
    )

    function Convert-CandidateItem {
        param([Parameter(Mandatory = $true)]$Row)
        $flags = if ($Row.RemakeFlags -eq [DBNull]::Value) { [int64]0 } else { [int64]$Row.RemakeFlags }
        return [ordered]@{
            orderNumber = [string][int64]$Row.OrderNumber
            itemNumber = ([string][int]$Row.ItemNumber).PadLeft(3, '0')
            job = [string]$Row.JobNumber
            product = [string]$Row.ProductHeading
            quantity = [decimal]$Row.Quantity
            widthUnits = [decimal]$Row.WidthUnits
            heightUnits = [decimal]$Row.HeightUnits
            remake = ($RemakeMask -gt 0 -and (($flags -band $RemakeMask) -eq $RemakeMask))
            orderStatus = if ($Row.OrderStatus -eq [DBNull]::Value) { 0 } else { [int]$Row.OrderStatus }
            itemStatus = if ($Row.ItemStatus -eq [DBNull]::Value) { 0 } else { [int]$Row.ItemStatus }
            productionBatch1 = if ($Row.ProductionBatch1 -eq [DBNull]::Value) { 0 } else { [int]$Row.ProductionBatch1 }
            productionBatch2 = if ($Row.ProductionBatch2 -eq [DBNull]::Value) { 0 } else { [int]$Row.ProductionBatch2 }
            productionBatch3 = if ($Row.ProductionBatch3 -eq [DBNull]::Value) { 0 } else { [int]$Row.ProductionBatch3 }
        }
    }

    function Get-ItemSignature {
        param([Parameter(Mandatory = $true)]$Row)
        return @(
            ([string]$Row.ProductHeading).Trim().ToUpperInvariant(),
            ([decimal]$Row.Quantity).ToString('0.####', [Globalization.CultureInfo]::InvariantCulture),
            ([decimal]$Row.WidthUnits).ToString('0.####', [Globalization.CultureInfo]::InvariantCulture),
            ([decimal]$Row.HeightUnits).ToString('0.####', [Globalization.CultureInfo]::InvariantCulture)
        ) -join '|'
    }

    $dateKey = $Date.ToString('yyyy-MM-dd')
    $candidates = New-Object System.Collections.Generic.List[object]
    $identityGroups = @($Rows | Where-Object {
        $_.HeaderIdentity -ne [DBNull]::Value -and [int64]$_.HeaderIdentity -gt 0
    } | Group-Object { [string][int64]$_.HeaderIdentity })

    foreach ($identityGroup in $identityGroups) {
        $orderGroups = @($identityGroup.Group | Group-Object { [string][int64]$_.OrderNumber })
        if ($orderGroups.Count -lt 2) { continue }
        foreach ($originalGroup in $orderGroups) {
            $originalRows = @($originalGroup.Group)
            $originalIsInactive = @($originalRows | Where-Object {
                ([int]$_.OrderStatus -eq 410) -and
                ([int]$_.ItemStatus -eq 0) -and
                ([int]$_.ProductionBatch1 -eq 0) -and
                ([int]$_.ProductionBatch2 -eq 0) -and
                ([int]$_.ProductionBatch3 -eq 0)
            }).Count -eq $originalRows.Count
            if (-not $originalIsInactive) { continue }

            $originalOrder = [int64]$originalGroup.Name
            $originalSignatures = @($originalRows | ForEach-Object { Get-ItemSignature -Row $_ })
            $replacementChoices = New-Object System.Collections.Generic.List[object]
            foreach ($replacementGroup in $orderGroups) {
                $replacementOrder = [int64]$replacementGroup.Name
                if ($replacementOrder -le $originalOrder) { continue }
                $replacementRows = @($replacementGroup.Group)
                $hasActiveBatch = @($replacementRows | Where-Object {
                    ([int]$_.ProductionBatch1 -gt 0) -or ([int]$_.ProductionBatch2 -gt 0) -or ([int]$_.ProductionBatch3 -gt 0)
                }).Count -gt 0
                if (-not $hasActiveBatch) { continue }
                $replacementSignatures = @($replacementRows | ForEach-Object { Get-ItemSignature -Row $_ })
                $overlapCount = @($originalSignatures | Where-Object { $replacementSignatures -contains $_ }).Count
                $originalJobs = @(
                    $originalRows |
                        ForEach-Object { ([string]$_.JobNumber).Trim().ToUpperInvariant() } |
                        Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
                )
                $replacementJobs = @(
                    $replacementRows |
                        ForEach-Object { ([string]$_.JobNumber).Trim().ToUpperInvariant() } |
                        Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
                )
                $sameJob = @($originalJobs | Where-Object { $replacementJobs -contains $_ }).Count -gt 0
                if ($overlapCount -le 0 -and -not $sameJob) { continue }
                $replacementChoices.Add([pscustomobject]@{
                    order = $replacementOrder
                    rows = $replacementRows
                    overlapCount = $overlapCount
                    sameJob = [bool]$sameJob
                })
            }
            $best = $replacementChoices | Sort-Object overlapCount, order -Descending | Select-Object -First 1
            if ($null -eq $best) { continue }
            $candidateKey = "${dateKey}|$($identityGroup.Name)|${originalOrder}|$($best.order)"
            $candidates.Add([ordered]@{
                candidateKey = $candidateKey
                deliveryDate = $dateKey
                headerIdentity = [string]$identityGroup.Name
                originalOrderNumber = [string]$originalOrder
                replacementOrderNumber = [string]$best.order
                confidence = if ([int]$best.overlapCount -gt 0) { 'high' } else { 'review' }
                evidence = [ordered]@{
                    sameHeaderIdentity = $true
                    originalOrderStatus = 410
                    originalItemStatus = 0
                    originalHasNoProductionBatch = $true
                    replacementHasActiveProductionBatch = $true
                    exactItemOverlapCount = [int]$best.overlapCount
                    originalItemCount = [int]$originalRows.Count
                    replacementItemCount = [int]$best.rows.Count
                    sameJobNumber = [bool]$best.sameJob
                    rule = 'v0.245-local-header-identity-review-1'
                }
                originalItems = @($originalRows | ForEach-Object { Convert-CandidateItem -Row $_ })
                replacementItems = @($best.rows | ForEach-Object { Convert-CandidateItem -Row $_ })
            })
        }
    }
    return @($candidates.ToArray())
}

function Get-AwRejectSyncPayload {
    param(
        [Parameter(Mandatory = $true)]$Config,
        [Parameter(Mandatory = $true)][string]$RunMode,
        [bool]$ForceEnabled = $false
    )

    $settings = Get-OptionalProperty -Object $Config -Name "RejectSync" -DefaultValue $null
    $enabled = [bool](Get-OptionalProperty -Object $settings -Name "Enabled" -DefaultValue $true)
    if (-not $enabled -and -not $ForceEnabled) {
        Write-AutomationLog -Message "A+W reject synchronization is disabled by configuration."
        return $null
    }
    if (-not $enabled -and $ForceEnabled) {
        Write-AutomationLog -Message "Manual complete A+W sync is overriding the disabled scheduled Reject enrichment setting for this explicit run."
    }

    $pastDays = if ($RunMode -eq "Full") {
        [int](Get-OptionalProperty -Object $settings -Name "FullPastDays" -DefaultValue 365)
    }
    else {
        [int](Get-OptionalProperty -Object $settings -Name "IncrementalPastDays" -DefaultValue 30)
    }
    $pastDays = [Math]::Max($pastDays, 1)
    $windowStart = (Get-Date).AddDays(-1 * $pastDays)
    $windowEnd = (Get-Date).AddMinutes(5)

    $connection = New-SqlConnection -Config $Config
    $table = New-Object System.Data.DataTable
    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        $connection.Open()
        $command = $connection.CreateCommand()
        $command.CommandTimeout = [int]$Config.Database.QueryTimeoutSeconds
        $command.CommandText = @"
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
SELECT
    CONVERT(nvarchar(64), pb.ROWID) AS AwRowId,
    pb.AUFNR AS OrderNr,
    pb.POSNR AS ItemNr,
    ISNULL(pb.BOM_ID, 0) AS BomId,
    ISNULL(pb.KEYINDEX, 0) AS KeyIndex,
    ISNULL(pb.SUB_POS, 0) AS SubPosition,
    ISNULL(pb.BOM_NODE, 0) AS BomNode,
    ISNULL(pb.MENGE, 0) AS Quantity,
    pb.BREAKAGEDATE AS BreakageDate,
    ISNULL(pb.JOBNUMBER_ORG, 0) AS OriginalJobNumber,
    ISNULL(pb.JOBNUMBER_NEW, 0) AS ReplacementJobNumber,
    ISNULL(pb.BREAKAGE_REASON, 0) AS ReasonCode,
    LTRIM(RTRIM(ISNULL(reason.BEZ, ''))) AS ReasonLabel,
    ISNULL(pb.BREAKAGE_REGISTRATION, 0) AS LocationCode,
    LTRIM(RTRIM(ISNULL(location.BEZ, ''))) AS LocationLabel,
    ISNULL(pb.BREAKAGE_FROMSCANNER, 0) AS FromScanner,
    LTRIM(RTRIM(CASE
        WHEN ISNULL(book.MITARB_ID, '') <> '' THEN book.MITARB_ID
        ELSE ISNULL(pb.LASTCHANGEUSER, '')
    END)) AS BreakageUser,
    pb.LASTCHANGEDATE AS SourceLastChangedAt,
    LTRIM(RTRIM(ISNULL(pb.LASTCHANGEUSER, ''))) AS SourceLastChangedUser,
    LTRIM(RTRIM(ISNULL(book.MITARB_ID, ''))) AS TimelineEmployee,
    ISNULL(book.WORK_TYPE, 0) AS WorkTypeId,
    LTRIM(RTRIM(ISNULL(worktype.BEA_TYPBEZ, ''))) AS WorkType,
    ISNULL(book.REG_POINT, 0) AS RegistrationPointId,
    LTRIM(RTRIM(ISNULL(point.BEZ, ''))) AS RegistrationPoint,
    LTRIM(RTRIM(ISNULL(machine.AGG_BEZ, ''))) AS Machine,
    CASE ISNULL(book.ORIGIN, -1) WHEN 0 THEN 'Explicit' WHEN 2 THEN 'Implicit' ELSE '' END AS ScanMode,
    CASE ISNULL(book.BOOK_TYPE, -1) WHEN 1 THEN 'Reject' WHEN 0 THEN 'Ready' ELSE '' END AS BookingMessage,
    ISNULL(book.SecondsFromBreakage, 2147483647) AS ActorSecondsFromBreakage
FROM SYSADM.PROD_BREAKAGE pb
LEFT JOIN SYSADM.KA_REKLA_GRND reason ON reason.NUMMER = pb.BREAKAGE_REASON
LEFT JOIN SYSADM.KA_REKLA_ORT location ON location.NUMMER = pb.BREAKAGE_REGISTRATION
OUTER APPLY (
    SELECT TOP (1)
        b.MITARB_ID, b.WORK_TYPE, b.REG_POINT, b.ORIGIN, b.BOOK_TYPE,
        ABS(DATEDIFF(second, b.SCANTIME, pb.BREAKAGEDATE)) AS SecondsFromBreakage
    FROM SYSADM.FS_BOOK_HISTORY b
    WHERE b.ID = pb.AUFNR
      AND b.POSNR = pb.POSNR
      AND b.BOOK_TYPE = 1
      -- A+W can commit PROD_BREAKAGE and the explicit Reject booking several
      -- seconds apart. Restrict to the same Order/Item and a short event window,
      -- then rank by the native reason/cause codes before falling back to time.
      AND b.SCANTIME >= DATEADD(second, -60, pb.BREAKAGEDATE)
      AND b.SCANTIME <= DATEADD(second, 60, pb.BREAKAGEDATE)
    ORDER BY
        CASE WHEN ISNULL(b.BREAKAGE_REASON, -1) = ISNULL(pb.BREAKAGE_REASON, -2) THEN 0 ELSE 1 END,
        CASE WHEN ISNULL(b.BREAKAGE_CAUSER, -1) = ISNULL(pb.BREAKAGE_REGISTRATION, -2) THEN 0 ELSE 1 END,
        CASE WHEN b.ORIGIN = 0 THEN 0 ELSE 1 END,
        CASE WHEN b.BOMID = pb.BOM_ID THEN 0 ELSE 1 END,
        ABS(DATEDIFF(second, b.SCANTIME, pb.BREAKAGEDATE)),
        b.SCANTIME DESC
) book
LEFT JOIN SYSADM.ZW_BEATYPEN worktype ON worktype.BEA_TYP = book.WORK_TYPE
LEFT JOIN SYSADM.PD_PROD_POINT point ON point.FREMD_KEY = book.REG_POINT
OUTER APPLY (
    SELECT
        CASE WHEN COUNT(*) = 1 THEN MAX(candidate.AGG_BEZ) ELSE '' END AS AGG_BEZ
    FROM (
        SELECT DISTINCT LTRIM(RTRIM(ISNULL(za.AGG_BEZ, ''))) AS AGG_BEZ
        FROM SYSADM.ZW_AGGREGATE za
        WHERE za.BARC = point.NUMMER
          AND LTRIM(RTRIM(ISNULL(za.AGG_BEZ, ''))) <> ''
    ) candidate
) machine
WHERE pb.IS_BREAKAGE = 1
  AND pb.BREAKAGEDATE >= @WindowStart
  AND pb.BREAKAGEDATE < @WindowEnd
ORDER BY pb.BREAKAGEDATE, pb.AUFNR, pb.POSNR, pb.KEYINDEX, pb.BOM_ID;
"@
        $startParameter = $command.Parameters.Add("@WindowStart", [System.Data.SqlDbType]::DateTime)
        $startParameter.Value = $windowStart
        $endParameter = $command.Parameters.Add("@WindowEnd", [System.Data.SqlDbType]::DateTime)
        $endParameter.Value = $windowEnd
        $adapter = New-Object System.Data.SqlClient.SqlDataAdapter($command)
        [void]$adapter.Fill($table)
        $adapter.Dispose()
        $command.Dispose()
    }
    finally {
        if ($connection.State -ne [System.Data.ConnectionState]::Closed) {
            $connection.Close()
        }
        $connection.Dispose()
    }
    $timer.Stop()

    $rows = New-Object System.Collections.Generic.List[object]
    foreach ($row in $table.Rows) {
        $replacementJob = if ($row.ReplacementJobNumber -eq [DBNull]::Value -or [int64]$row.ReplacementJobNumber -eq 0) { "" } else { [string][int64]$row.ReplacementJobNumber }
        $rows.Add([ordered]@{
            awRowId = [string]$row.AwRowId
            orderNr = [string][int64]$row.OrderNr
            itemNr = [string][int]$row.ItemNr
            bomId = [int]$row.BomId
            keyIndex = [int]$row.KeyIndex
            subPosition = [int]$row.SubPosition
            bomNode = [int]$row.BomNode
            quantity = [int][decimal]$row.Quantity
            breakageDate = ([datetime]$row.BreakageDate).ToString("o")
            originalJobNumber = $(if ([int64]$row.OriginalJobNumber -eq 0) { "" } else { [string][int64]$row.OriginalJobNumber })
            replacementJobNumber = $replacementJob
            reasonCode = [int]$row.ReasonCode
            reasonLabel = [string]$row.ReasonLabel
            locationCode = [int]$row.LocationCode
            locationLabel = [string]$row.LocationLabel
            fromScanner = [int]$row.FromScanner
            breakageUser = [string]$row.BreakageUser
            sourceLastChangedAt = $(if ($row.SourceLastChangedAt -eq [DBNull]::Value) { "" } else { ([datetime]$row.SourceLastChangedAt).ToString("o") })
            sourceLastChangedUser = [string]$row.SourceLastChangedUser
            timelineEmployee = [string]$row.TimelineEmployee
            workTypeId = [int]$row.WorkTypeId
            workType = [string]$row.WorkType
            registrationPointId = [int]$row.RegistrationPointId
            registrationPoint = [string]$row.RegistrationPoint
            machine = [string]$row.Machine
            scanMode = [string]$row.ScanMode
            bookingMessage = [string]$row.BookingMessage
            actorSecondsFromBreakage = [int]$row.ActorSecondsFromBreakage
        })
    }

    Write-AutomationLog -Message (
        "A+W reject query returned {0} raw PROD_BREAKAGE row(s) for {1} through {2} in {3} ms." -f
        [int]$rows.Count,
        $windowStart.ToString("yyyy-MM-dd HH:mm:ss"),
        $windowEnd.ToString("yyyy-MM-dd HH:mm:ss"),
        [Math]::Round($timer.Elapsed.TotalMilliseconds)
    )
    return [ordered]@{
        version = "v484-aw-reject-1"
        source = "SYSADM.PROD_BREAKAGE"
        windowStart = $windowStart.ToUniversalTime().ToString("o")
        windowEnd = $windowEnd.ToUniversalTime().ToString("o")
        rows = @($rows.ToArray())
    }
}

function Get-AwCuttingSyncPayload {
    param(
        [Parameter(Mandatory = $true)]$Config,
        [Parameter(Mandatory = $true)]$DirectPayloads,
        [bool]$ForceEnabled = $false
    )

    $settings = Get-OptionalProperty -Object $Config -Name "ProductionSync" -DefaultValue $null
    $enabled = [bool](Get-OptionalProperty -Object $settings -Name "Enabled" -DefaultValue $true)
    $scheduledEnabled = [bool](Get-OptionalProperty -Object $settings -Name "ScheduledEnabled" -DefaultValue $true)
    $isManual = -not [string]::IsNullOrWhiteSpace([string]$RequestId)
    if (-not $enabled -and -not $ForceEnabled) {
        Write-AutomationLog -Message "A+W production synchronization is disabled in Automation Control Center settings." -Level "INFO"
        return $null
    }
    if (-not $isManual -and -not $scheduledEnabled -and -not $ForceEnabled) {
        Write-AutomationLog -Message "A+W production synchronization is disabled for scheduled runs; delivery-list reconciliation will continue without Batch/Optimization enrichment." -Level "INFO"
        return $null
    }

    $orderSet = New-Object 'System.Collections.Generic.HashSet[string]'
    foreach ($envelope in @($DirectPayloads)) {
        $payload = Get-OptionalProperty -Object $envelope -Name "payload" -DefaultValue $null
        foreach ($row in @(Get-OptionalProperty -Object $payload -Name "rows" -DefaultValue @())) {
            $orderNumber = ([string](Get-OptionalProperty -Object $row -Name "order" -DefaultValue "")).Trim()
            if (-not [string]::IsNullOrWhiteSpace($orderNumber)) { [void]$orderSet.Add($orderNumber) }
        }
    }
    $orders = @($orderSet | Sort-Object)
    if ($orders.Count -eq 0) {
        Write-AutomationDebug -Message "A+W production sync skipped because the direct delivery payload contains no orders."
        return $null
    }

    $batchSize = [int](Get-OptionalProperty -Object $settings -Name "QueryBatchSize" -DefaultValue 60)
    $batchSize = [Math]::Max(10, [Math]::Min(150, $batchSize))
    $queryTimeout = [int](Get-OptionalProperty -Object $settings -Name "QueryTimeoutSeconds" -DefaultValue 75)
    $queryTimeout = [Math]::Max(20, [Math]::Min(300, $queryTimeout))
    $cutLookbackDays = [int](Get-OptionalProperty -Object $settings -Name "CuttingBookingLookbackDays" -DefaultValue 120)
    $cutLookbackDays = [Math]::Max(14, [Math]::Min(730, $cutLookbackDays))
    $includeCutting = [bool](Get-OptionalProperty -Object $settings -Name "IncludeCuttingBookings" -DefaultValue $true)
    $generationHistoryDepth = [int](Get-OptionalProperty -Object $settings -Name "GenerationHistoryDepth" -DefaultValue 4)
    $generationHistoryDepth = [Math]::Max(1, [Math]::Min(12, $generationHistoryDepth))

    $rows = New-Object System.Collections.Generic.List[object]
    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    $totalBatches = [int][Math]::Ceiling($orders.Count / [double]$batchSize)
    Write-AutomationLog -Message (
        "A+W production sync starting for {0} delivery order(s) in {1} SQL batch(es). BatchSize={2} QueryTimeoutSeconds={3} CuttingBookingLookbackDays={4}." -f
        [int]$orders.Count, $totalBatches, $batchSize, $queryTimeout, $cutLookbackDays
    )
    Write-AutomationDebug -Message ("A+W production generation history depth={0}; CuttingBookingEvidence={1}." -f $generationHistoryDepth, $includeCutting)

    for ($offset = 0; $offset -lt $orders.Count; $offset += $batchSize) {
        $end = [Math]::Min($offset + $batchSize - 1, $orders.Count - 1)
        $batchOrders = @($orders[$offset..$end])
        $batchNumber = [int]([Math]::Floor($offset / $batchSize) + 1)
        $batchTimer = [System.Diagnostics.Stopwatch]::StartNew()
        Write-AutomationStep -Message ("Reading A+W Batch/Optimization/Cutting state ({0}/{1}) for {2} order(s)." -f $batchNumber, $totalBatches, $batchOrders.Count)

        $connection = New-SqlConnection -Config $Config
        $table = New-Object System.Data.DataTable
        try {
            $connection.Open()
            $command = $connection.CreateCommand()
            $command.CommandTimeout = $queryTimeout
            $placeholders = New-Object System.Collections.Generic.List[string]
            for ($index = 0; $index -lt $batchOrders.Count; $index++) {
                $name = "@Order$index"
                $placeholders.Add($name)
                $parameter = $command.Parameters.Add($name, [System.Data.SqlDbType]::Int)
                $parameter.Value = [int]$batchOrders[$index]
            }
            $lookbackParameter = $command.Parameters.Add("@CutLookbackDays", [System.Data.SqlDbType]::Int)
            $lookbackParameter.Value = $cutLookbackDays
            $historyDepthParameter = $command.Parameters.Add("@GenerationHistoryDepth", [System.Data.SqlDbType]::Int)
            $historyDepthParameter.Value = $generationHistoryDepth
            $orderSql = [string]::Join(",", $placeholders.ToArray())
            $cuttingJoin = if ($includeCutting) { @"
LEFT JOIN CuttingBookingRanked cut
  ON cut.ID=ji.AUFNR AND cut.POSNR=ji.POSNR AND cut.BOMID=ji.BOM_ID AND cut.RN=1
 AND (job.CREATIONDATE IS NULL OR cut.SCANTIME >= DATEADD(minute,-5,job.CREATIONDATE))
"@ } else { "" }
            $cuttingCte = if ($includeCutting) { @"
,CuttingBookingRanked AS (
    SELECT b.ID,b.POSNR,b.BOMID,b.SCANTIME,b.MITARB_ID,b.ROWID,
           ROW_NUMBER() OVER (PARTITION BY b.ID,b.POSNR,b.BOMID ORDER BY b.SCANTIME DESC) AS RN
    FROM SYSADM.FS_BOOK_HISTORY b
    WHERE b.ID IN ($orderSql)
      AND b.BOOK_TYPE = 0 AND b.WORK_TYPE = 10 AND b.REG_POINT = 1000 AND b.AMOUNT > 0
      AND b.SCANTIME >= DATEADD(day,-@CutLookbackDays,GETDATE())
)
"@ } else { "" }
            $cuttingSelect = if ($includeCutting) {
                "cut.SCANTIME AS CuttingBookingAt, LTRIM(RTRIM(ISNULL(cut.MITARB_ID,''))) AS CuttingBookingEmployee, CONVERT(nvarchar(64),cut.ROWID) AS CuttingBookingRowId"
            } else {
                "CAST(NULL AS datetime) AS CuttingBookingAt, CAST('' AS nvarchar(80)) AS CuttingBookingEmployee, CAST('' AS nvarchar(64)) AS CuttingBookingRowId"
            }
            $command.CommandText = @"
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;
;WITH JobItemsRanked AS (
    SELECT ji.*,
           DENSE_RANK() OVER (PARTITION BY ji.AUFNR,ji.POSNR ORDER BY ISNULL(ji.KEYINDEX,0) DESC,ISNULL(ji.JOBNUMBER,0) DESC) AS GenerationRank
    FROM SYSADM.PROD_JOBITEM ji
    WHERE ji.AUFNR IN ($orderSql)
),
JobItems AS (
    SELECT * FROM JobItemsRanked WHERE GenerationRank <= @GenerationHistoryDepth
),
SeqRanked AS (
    SELECT os.AUFNR,os.POSNR,ISNULL(os.BOM_ID,0) AS BOM_ID,ISNULL(os.KEYINDEX,0) AS KEYINDEX,
           os.OPTIMIZATION,os.SEQUENCE,os.PLATENR,
           ROW_NUMBER() OVER (
             PARTITION BY os.AUFNR,os.POSNR,ISNULL(os.BOM_ID,0),ISNULL(os.KEYINDEX,0)
             ORDER BY os.OPTIMIZATION DESC,os.SEQUENCE DESC
           ) AS RN
    FROM SYSADM.PROD_OPTI_SEQUENCE os
    WHERE os.AUFNR IN ($orderSql)
),
ResolvedJobItems AS (
    SELECT ji.*,
           ISNULL(COALESCE(NULLIF(ji.OPTIMIZATION,0),seq.OPTIMIZATION),0) AS ResolvedOptimization,
           ISNULL(seq.SEQUENCE,0) AS ResolvedOptimizationSequence,
           ISNULL(seq.PLATENR,0) AS ResolvedPlateNumber
    FROM JobItems ji
    LEFT JOIN SeqRanked seq
      ON seq.AUFNR=ji.AUFNR AND seq.POSNR=ji.POSNR
     AND seq.BOM_ID=ISNULL(ji.BOM_ID,0) AND seq.KEYINDEX=ISNULL(ji.KEYINDEX,0) AND seq.RN=1
),
CandidateOptimizations AS (
    SELECT DISTINCT ResolvedOptimization AS OPTIMIZATION
    FROM ResolvedJobItems
    WHERE ResolvedOptimization > 0
),
OptimizationRanked AS (
    SELECT u.OPTIMIZATION,u.STATUS,u.OPTIMODE,u.OPTIDATE,u.LASTCHANGEDATE,
           ROW_NUMBER() OVER (PARTITION BY u.OPTIMIZATION ORDER BY u.SourceRank,u.LASTCHANGEDATE DESC) AS RN
    FROM (
        SELECT 0 AS SourceRank,o.OPTIMIZATION,o.STATUS,o.OPTIMODE,o.OPTIDATE,o.LASTCHANGEDATE
        FROM SYSADM.PROD_OPTIMIZATION o
        INNER JOIN CandidateOptimizations wanted ON wanted.OPTIMIZATION=o.OPTIMIZATION
        UNION ALL
        SELECT 1 AS SourceRank,s.OPTIMIZATION,s.STATUS,s.OPTIMODE,s.OPTIDATE,s.LASTCHANGEDATE
        FROM SYSADM.PROD_OPTI_STATISTICS s
        INNER JOIN CandidateOptimizations wanted ON wanted.OPTIMIZATION=s.OPTIMIZATION
    ) u
),
PlateRanked AS (
    SELECT p.OPTIMIZATION,p.PLATENR,p.CUT,p.STOCKBOOKED,p.LASTCHANGEDATE,p.LASTCHANGEUSER,
           ROW_NUMBER() OVER (PARTITION BY p.OPTIMIZATION,p.PLATENR ORDER BY p.LASTCHANGEDATE DESC) AS RN
    FROM SYSADM.PROD_OPTI_PLATES p
    INNER JOIN CandidateOptimizations wanted ON wanted.OPTIMIZATION=p.OPTIMIZATION
)
$cuttingCte
SELECT
    CONVERT(nvarchar(64),ji.ROWID) AS SourceRowId,
    ji.AUFNR AS OrderNr,ji.POSNR AS ItemNr,ISNULL(ji.BOM_ID,0) AS BomId,ISNULL(ji.KEYINDEX,0) AS KeyIndex,
    ISNULL(ji.JOBNUMBER,0) AS BatchJobNumber,ISNULL(job.STATUS,0) AS BatchStatusCode,
    LTRIM(RTRIM(ISNULL(job.DESCRIPTION,''))) AS BatchDescription,job.CREATIONDATE AS BatchCreatedAt,
    LTRIM(RTRIM(ISNULL(job.MITARB_ID,''))) AS BatchEmployee,job.LASTCHANGEDATE AS BatchLastChangedAt,
    LTRIM(RTRIM(ISNULL(job.LASTCHANGEUSER,''))) AS BatchLastChangedUser,
    ji.ResolvedOptimization AS OptimizationNumber,
    ISNULL(opti.STATUS,0) AS OptimizationStatusCode,ISNULL(opti.OPTIMODE,0) AS OptimizationMode,
    opti.OPTIDATE AS OptimizationDate,opti.LASTCHANGEDATE AS OptimizationLastChangedAt,
    ISNULL(ji.SEQUENCE_OPTIRUN,0) AS OptimizationRunSequence,ji.ResolvedOptimizationSequence AS OptimizationSequence,
    ji.ResolvedPlateNumber AS OptimizationPlateNumber,ISNULL(plate.CUT,0) AS OptimizationPlateCut,
    ISNULL(plate.STOCKBOOKED,0) AS OptimizationPlateStockBooked,plate.LASTCHANGEDATE AS OptimizationPlateLastChangedAt,
    LTRIM(RTRIM(ISNULL(plate.LASTCHANGEUSER,''))) AS OptimizationPlateLastChangedUser,
    ISNULL(ji.STACKNUMBER,0) AS StackNumber,
    ISNULL(ji.STACKPOSITION,0) AS StackPosition,ISNULL(ji.MENGE,0) AS Quantity,ISNULL(ji.MENGE_CUT,0) AS CutQuantity,
    ISNULL(ji.AGG,0) AS AggregateId,ISNULL(ji.LASTAGG,0) AS LastAggregateId,
    $cuttingSelect,
    LTRIM(RTRIM(ISNULL(posx.BARCODE_START,''))) AS ItemBarcodeStart,
    LTRIM(RTRIM(ISNULL(stkl.BARCODE_START,''))) AS BomBarcodeStart,
    ISNULL(pos.PP_GEWICHT,0) AS Weight,ISNULL(pos.PP_QM,0) AS SurfaceArea,
    LTRIM(RTRIM(ISNULL(head.AH_NAME1,''))) AS CustomerName,
    LTRIM(RTRIM(ISNULL(head.BEST_TEXT1,''))) AS SgBestText1,
    LTRIM(RTRIM(ISNULL(head.OR_TOUR,''))) AS RouteText,
    LTRIM(RTRIM(ISNULL(pos.PROD_BEZ1,''))) AS ProductDescription,
    ISNULL(pos.PP_MENGE,0) AS PositionQuantity,ISNULL(pos.PP_BREITE,0) AS PositionWidth,ISNULL(pos.PP_HOEHE,0) AS PositionHeight
FROM ResolvedJobItems ji
INNER JOIN SYSADM.PROD_JOB job ON job.JOBNUMBER=ji.JOBNUMBER
LEFT JOIN SYSADM.BW_AUFTR_KOPF head ON head.ID=ji.AUFNR
LEFT JOIN SYSADM.BW_AUFTR_POS pos ON pos.ID=ji.AUFNR AND pos.POS_NR=ji.POSNR
LEFT JOIN SYSADM.BW_AUFTR_POS_EX posx ON posx.ID=ji.AUFNR AND posx.POS_NR=ji.POSNR
LEFT JOIN SYSADM.BW_AUFTR_STKL stkl ON stkl.ID=ji.AUFNR AND stkl.POS_NR=ji.POSNR AND stkl.BOM_ID=ji.BOM_ID
LEFT JOIN OptimizationRanked opti ON opti.OPTIMIZATION=ji.ResolvedOptimization AND opti.RN=1
LEFT JOIN PlateRanked plate ON plate.OPTIMIZATION=ji.ResolvedOptimization AND plate.PLATENR=ji.ResolvedPlateNumber AND plate.RN=1
$cuttingJoin
ORDER BY ji.AUFNR,ji.POSNR,ji.KEYINDEX,ji.JOBNUMBER,ji.BOM_ID
OPTION (RECOMPILE);
"@
            $adapter = New-Object System.Data.SqlClient.SqlDataAdapter($command)
            [void]$adapter.Fill($table)
            $adapter.Dispose(); $command.Dispose()
        }
        finally {
            if ($connection.State -ne [System.Data.ConnectionState]::Closed) { $connection.Close() }
            $connection.Dispose()
        }

        foreach ($row in $table.Rows) {
            $rows.Add([ordered]@{
                sourceRowId=[string]$row.SourceRowId; orderNr=[string][int64]$row.OrderNr; itemNr=[string][int]$row.ItemNr;
                bomId=[int]$row.BomId; keyIndex=[int]$row.KeyIndex; batchJobNumber=[string][int64]$row.BatchJobNumber;
                batchStatusCode=[int]$row.BatchStatusCode; batchDescription=[string]$row.BatchDescription;
                batchCreatedAt=$(if ($row.BatchCreatedAt -eq [DBNull]::Value) { "" } else { ([datetime]$row.BatchCreatedAt).ToString("o") });
                batchEmployee=[string]$row.BatchEmployee; batchLastChangedAt=$(if ($row.BatchLastChangedAt -eq [DBNull]::Value) { "" } else { ([datetime]$row.BatchLastChangedAt).ToString("o") });
                batchLastChangedUser=[string]$row.BatchLastChangedUser; optimizationNumber=[int]$row.OptimizationNumber;
                optimizationStatusCode=[int]$row.OptimizationStatusCode; optimizationMode=[int]$row.OptimizationMode;
                optimizationDate=$(if ($row.OptimizationDate -eq [DBNull]::Value) { "" } else { ([datetime]$row.OptimizationDate).ToString("o") });
                optimizationLastChangedAt=$(if ($row.OptimizationLastChangedAt -eq [DBNull]::Value) { "" } else { ([datetime]$row.OptimizationLastChangedAt).ToString("o") });
                optimizationRunSequence=[int]$row.OptimizationRunSequence; optimizationSequence=[int]$row.OptimizationSequence;
                optimizationPlateNumber=[int]$row.OptimizationPlateNumber; optimizationPlateCut=[int]$row.OptimizationPlateCut;
                optimizationPlateStockBooked=[int]$row.OptimizationPlateStockBooked;
                optimizationPlateLastChangedAt=$(if ($row.OptimizationPlateLastChangedAt -eq [DBNull]::Value) { "" } else { ([datetime]$row.OptimizationPlateLastChangedAt).ToString("o") });
                optimizationPlateLastChangedUser=[string]$row.OptimizationPlateLastChangedUser;
                stackNumber=[int]$row.StackNumber; stackPosition=[int]$row.StackPosition;
                quantity=[decimal]$row.Quantity; cutQuantity=[decimal]$row.CutQuantity; aggregateId=[int]$row.AggregateId; lastAggregateId=[int]$row.LastAggregateId;
                cuttingBookingAt=$(if ($row.CuttingBookingAt -eq [DBNull]::Value) { "" } else { ([datetime]$row.CuttingBookingAt).ToString("o") });
                cuttingBookingEmployee=[string]$row.CuttingBookingEmployee; cuttingBookingRowId=[string]$row.CuttingBookingRowId;
                itemBarcodeStart=[string]$row.ItemBarcodeStart; bomBarcodeStart=[string]$row.BomBarcodeStart;
                weight=[decimal]$row.Weight; surfaceArea=[decimal]$row.SurfaceArea;
                customerName=[string]$row.CustomerName; sgBestText1=[string]$row.SgBestText1; routeText=[string]$row.RouteText;
                productDescription=[string]$row.ProductDescription; positionQuantity=[decimal]$row.PositionQuantity;
                positionWidth=[decimal]$row.PositionWidth; positionHeight=[decimal]$row.PositionHeight
            })
        }
        $batchTimer.Stop()
        Write-AutomationLog -Message ("A+W production batch {0}/{1} completed. Orders={2} Rows={3} DurationMs={4}." -f $batchNumber,$totalBatches,$batchOrders.Count,$table.Rows.Count,[Math]::Round($batchTimer.Elapsed.TotalMilliseconds))
    }
    $timer.Stop()
    Write-AutomationLog -Message ("A+W production sync returned {0} PROD_JOBITEM row(s) across {1} delivery order(s) in {2} ms." -f [int]$rows.Count,[int]$orders.Count,[Math]::Round($timer.Elapsed.TotalMilliseconds))
    # Compatibility markers retained for historical regression contracts:
    # v499-aw-production-1 / version="v501-aw-production-2".
    # Historical SQL spelling retained for contract search only:
    # COALESCE(NULLIF(ji.OPTIMIZATION, 0), seq.OPTIMIZATION)
    return [ordered]@{
        version="v502-aw-production-3"; source="SYSADM.PROD_JOBITEM+PROD_JOB+PROD_OPTI_SEQUENCE+PROD_OPTIMIZATION+PROD_OPTI_PLATES+FS_BOOK_HISTORY";
        orderCount=[int]$orders.Count; queryBatchSize=$batchSize; cuttingBookingLookbackDays=$cutLookbackDays; generationHistoryDepth=$generationHistoryDepth; rows=@($rows.ToArray())
    }
}

function Get-DeliveryRows {
    param(
        [Parameter(Mandatory = $true)]$Config,
        [Parameter(Mandatory = $true)][datetime]$Date
    )

    $source = Get-SourceSqlParts -Config $Config
    $mapping = $source.Mapping
    $connection = New-SqlConnection -Config $Config
    $table = New-Object System.Data.DataTable
    $queryTimer = [System.Diagnostics.Stopwatch]::StartNew()
    Write-AutomationDebug -Message (
        "Preparing parameterized A+W query for {0}. Join={1}.{2}->{3}.{4} DeliveryDateColumn={5}" -f
        $Date.ToString("yyyy-MM-dd"),
        [string]$source.Schema,
        [string]$source.HeaderJoin,
        [string]$source.Schema,
        [string]$source.ItemJoin,
        [string]$source.DeliveryDate
    )
    try {
        $connection.Open()
        $command = $connection.CreateCommand()
        $command.CommandTimeout = [int]$Config.Database.QueryTimeoutSeconds
        $command.CommandText = @"
SELECT
    LTRIM(RTRIM(ISNULL(p.$($source.ProductHeading), ''))) AS ProductHeading,
    LTRIM(RTRIM(ISNULL(h.$($source.JobNumber), ''))) AS JobNumber,
    h.$($source.OrderNumber) AS OrderNumber,
    p.$($source.ItemNumber) AS ItemNumber,
    p.$($source.Quantity) AS Quantity,
    p.$($source.WidthUnits) AS WidthUnits,
    p.$($source.HeightUnits) AS HeightUnits,
    LTRIM(RTRIM(ISNULL(h.$($source.Customer), ''))) AS Customer,
    ISNULL(h.$($source.RemakeFlags), 0) AS RemakeFlags,
    LTRIM(RTRIM(ISNULL(h.$($source.Route), ''))) AS SourceRoute,
    ISNULL(h.$($source.OrderStatus), 0) AS OrderStatus,
    ISNULL(p.$($source.ItemStatus), 0) AS ItemStatus,
    ISNULL(h.$($source.ProductionBatch1), 0) AS ProductionBatch1,
    ISNULL(h.$($source.ProductionBatch2), 0) AS ProductionBatch2,
    ISNULL(h.$($source.ProductionBatch3), 0) AS ProductionBatch3,
    ISNULL(h.$($source.HeaderIdentity), 0) AS HeaderIdentity
FROM $($source.Schema).$($source.HeaderTable) h
INNER JOIN $($source.Schema).$($source.ItemTable) p
    ON p.$($source.ItemJoin) = h.$($source.HeaderJoin)
WHERE h.$($source.DeliveryDate) >= @DeliveryDate
  AND h.$($source.DeliveryDate) < DATEADD(day, 1, @DeliveryDate)
ORDER BY
    p.$($source.ProductHeading),
    h.$($source.JobNumber),
    h.$($source.OrderNumber),
    p.$($source.ItemNumber);
"@
        $parameter = $command.Parameters.Add("@DeliveryDate", [System.Data.SqlDbType]::DateTime)
        $parameter.Value = $Date.Date
        $adapter = New-Object System.Data.SqlClient.SqlDataAdapter($command)
        [void]$adapter.Fill($table)
        $adapter.Dispose()
        $command.Dispose()
    }
    finally {
        if ($connection.State -ne [System.Data.ConnectionState]::Closed) {
            $connection.Close()
        }
        $connection.Dispose()
    }
    $queryTimer.Stop()
    Write-AutomationDebug -Message (
        "A+W SQL query completed for {0}. ReturnedRows={1} DurationMs={2}" -f
        $Date.ToString("yyyy-MM-dd"),
        [int]$table.Rows.Count,
        [Math]::Round($queryTimer.Elapsed.TotalMilliseconds)
    )

    $remakeMask = [int64](Get-OptionalProperty -Object $mapping -Name "RemakeBitMask" -DefaultValue 128)
    $dateCandidates = @(Get-SupersededOrderCandidates -Rows $table.Rows -Date $Date -RemakeMask $remakeMask)
    if ($dateCandidates.Count -gt 0) {
        $script:SupersededOrderCandidates = @(
            @($script:SupersededOrderCandidates + $dateCandidates) |
                Group-Object candidateKey |
                ForEach-Object { $_.Group | Select-Object -Last 1 }
        )
        Write-AutomationLog -Message (
            "Detected {0} possible superseded-order review candidate(s) for {1}. No rows were removed without an approval." -f
            [int]$dateCandidates.Count, $Date.ToString("yyyy-MM-dd")
        ) -Level "WARN"
    }
    $verifiedExclusions = @(Get-VerifiedSourceExclusionsForDate -Date $Date)
    $verifiedByKey = @{}
    foreach ($entry in $verifiedExclusions) {
        $verifiedByKey[[string]$entry.orderItemKey] = $entry
    }
    $verifiedOrderExclusions = @(Get-VerifiedSourceOrderExclusionsForDate -Date $Date)
    $verifiedByOrder = @{}
    foreach ($entry in $verifiedOrderExclusions) {
        $verifiedByOrder[[string]$entry.orderNumber] = $entry
    }
    $manualOverrides = @(Get-VerifiedSourceManualOverridesForDate -Date $Date)
    $manualByKey = @{}
    foreach ($entry in $manualOverrides) {
        $manualByKey[[string]$entry.orderItemKey] = $entry
    }
    $appliedManualOverrideCount = 0

    $rows = New-Object System.Collections.Generic.List[object]
    $excludedRows = New-Object System.Collections.Generic.List[object]
    $orderStatusCounts = @{}
    $itemStatusCounts = @{}
    $rawRemakeLineCount = 0

    foreach ($row in $table.Rows) {
        $headerFlags = if ($row.RemakeFlags -eq [DBNull]::Value) { [int64]0 } else { [int64]$row.RemakeFlags }
        $isRemake = $remakeMask -gt 0 -and (($headerFlags -band $remakeMask) -eq $remakeMask)
        if ($isRemake) {
            $rawRemakeLineCount++
        }

        $orderStatus = if ($row.OrderStatus -eq [DBNull]::Value) { 0 } else { [int]$row.OrderStatus }
        $itemStatus = if ($row.ItemStatus -eq [DBNull]::Value) { 0 } else { [int]$row.ItemStatus }
        $orderStatusKey = [string]$orderStatus
        $itemStatusKey = [string]$itemStatus
        if ($orderStatusCounts.ContainsKey($orderStatusKey)) {
            $orderStatusCounts[$orderStatusKey] = [int]$orderStatusCounts[$orderStatusKey] + 1
        }
        else {
            $orderStatusCounts[$orderStatusKey] = 1
        }
        if ($itemStatusCounts.ContainsKey($itemStatusKey)) {
            $itemStatusCounts[$itemStatusKey] = [int]$itemStatusCounts[$itemStatusKey] + 1
        }
        else {
            $itemStatusCounts[$itemStatusKey] = 1
        }

        $orderNumber = [string][int64]$row.OrderNumber
        $itemNumber = ([string][int]$row.ItemNumber).PadLeft(3, '0')
        $orderItemKey = "${orderNumber}-${itemNumber}"
        if ($verifiedByKey.ContainsKey($orderItemKey) -or $verifiedByOrder.ContainsKey($orderNumber)) {
            $verified = if ($verifiedByKey.ContainsKey($orderItemKey)) {
                $verifiedByKey[$orderItemKey]
            }
            else {
                $verifiedByOrder[$orderNumber]
            }
            $excludedRows.Add([pscustomobject]@{
                order = [int64]$row.OrderNumber
                item = [int]$row.ItemNumber
                quantity = [decimal]$row.Quantity
                remake = if ($isRemake) { "RM" } else { "" }
                remakeFlags = $headerFlags
                orderStatus = $orderStatus
                itemStatus = $itemStatus
                productionBatch1 = if ($row.ProductionBatch1 -eq [DBNull]::Value) { 0 } else { [int]$row.ProductionBatch1 }
                productionBatch2 = if ($row.ProductionBatch2 -eq [DBNull]::Value) { 0 } else { [int]$row.ProductionBatch2 }
                productionBatch3 = if ($row.ProductionBatch3 -eq [DBNull]::Value) { 0 } else { [int]$row.ProductionBatch3 }
                reason = [string]$verified.reason
            })
            continue
        }

        $exportRow = [ordered]@{
            product = [string]$row.ProductHeading
            job = [string]$row.JobNumber
            order = [int64]$row.OrderNumber
            item = [int]$row.ItemNumber
            sourceOrder = [int64]$row.OrderNumber
            sourceItem = [int]$row.ItemNumber
            quantity = [decimal]$row.Quantity
            widthUnits = [decimal]$row.WidthUnits
            heightUnits = [decimal]$row.HeightUnits
            customer = [string]$row.Customer
            remake = if ($isRemake) { "RM" } else { "" }
            remakeFlags = $headerFlags
            route = Resolve-SourceRoute -Mapping $mapping -RawRoute ([string]$row.SourceRoute)
            dimensionsOverride = ""
        }
        if ($manualByKey.ContainsKey($orderItemKey)) {
            $manualEntry = $manualByKey[$orderItemKey]
            $fields = $manualEntry.fields
            if ($fields.PSObject.Properties.Name -contains "product") { $exportRow.product = [string]$fields.product }
            if ($fields.PSObject.Properties.Name -contains "job") { $exportRow.job = [string]$fields.job }
            if ($fields.PSObject.Properties.Name -contains "order" -and [string]$fields.order -match '^\d+$') { $exportRow.order = [int64]$fields.order }
            if ($fields.PSObject.Properties.Name -contains "item" -and [string]$fields.item -match '^\d+$') { $exportRow.item = [int]$fields.item }
            if ($fields.PSObject.Properties.Name -contains "qty") { $exportRow.quantity = [decimal]$fields.qty }
            if ($fields.PSObject.Properties.Name -contains "customer") { $exportRow.customer = [string]$fields.customer }
            if ($fields.PSObject.Properties.Name -contains "route") { $exportRow.route = [string]$fields.route }
            if ($fields.PSObject.Properties.Name -contains "dimensions") { $exportRow.dimensionsOverride = [string]$fields.dimensions }
            $appliedManualOverrideCount++
        }
        $rows.Add($exportRow)
    }

    $script:LastRawDeliveryRowCount = [int]$table.Rows.Count
    $script:LastRawRemakeLineCount = [int]$rawRemakeLineCount
    $script:LastExcludedDeliveryRows = @($excludedRows.ToArray())
    $script:LastEligibilityRule = "v0.324-approved-order-exclusions-plus-manual-overrides-1"
    if ($appliedManualOverrideCount -gt 0) {
        Write-AutomationLog -Message (
            "Applied {0} persisted manual scanner override(s) to the SQL workbook rows for {1}." -f
            $appliedManualOverrideCount, $Date.ToString("yyyy-MM-dd")
        )
    }
    $script:LastStatusDiagnosticSummary = (
        "order statuses [{0}]; item statuses [{1}]" -f
        (Get-StatusCountSummary -Counts $orderStatusCounts),
        (Get-StatusCountSummary -Counts $itemStatusCounts)
    )
    $table.Dispose()

    return $rows.ToArray()
}

function Get-Sha256Text {
    param([Parameter(Mandatory = $true)][string]$Text)

    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
        return ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace("-", "").ToLowerInvariant()
    }
    finally {
        $sha.Dispose()
    }
}

function Get-StatePath {
    param(
        [Parameter(Mandatory = $true)]$Config,
        [Parameter(Mandatory = $true)][datetime]$Date
    )
    return Join-Path $Config.WorkingRoot ("State\delivery-{0}.json" -f $Date.ToString("yyyy-MM-dd"))
}

function Read-DateState {
    param(
        [Parameter(Mandatory = $true)]$Config,
        [Parameter(Mandatory = $true)][datetime]$Date
    )

    $path = Get-StatePath -Config $Config -Date $Date
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        return $null
    }
    try {
        return Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
    }
    catch {
        Write-AutomationLog -Message "Ignoring unreadable state file: $path" -Level "WARN"
        return $null
    }
}

function Write-DateState {
    param(
        [Parameter(Mandatory = $true)]$Config,
        [Parameter(Mandatory = $true)][datetime]$Date,
        [Parameter(Mandatory = $true)][string]$Hash,
        [Parameter(Mandatory = $true)][string]$WorkbookPath,
        [Parameter(Mandatory = $true)][string]$WorkbookHash,
        [Parameter(Mandatory = $true)][int]$RowCount,
        [Parameter(Mandatory = $true)][int]$PieceCount,
        [Parameter(Mandatory = $true)][bool]$Imported
    )

    $state = [ordered]@{
        deliveryDate = $Date.ToString("yyyy-MM-dd")
        dataHash = $Hash
        workbookPath = $WorkbookPath
        workbookHash = $WorkbookHash
        workbookFormatVersion = "v324-ooxml-2"
        rowCount = $RowCount
        pieceCount = $PieceCount
        imported = $Imported
        updatedAt = (Get-Date).ToUniversalTime().ToString("o")
    }
    $path = Get-StatePath -Config $Config -Date $Date
    $state | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $path -Encoding UTF8
}

function Invoke-ConfiguredPython {
    param(
        [Parameter(Mandatory = $true)]$Config,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    $pythonPath = [string]$Config.Runtime.PythonPath
    if ([string]::IsNullOrWhiteSpace($pythonPath) -or -not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
        throw "Python runtime is not configured. Run Setup-DeliveryListSqlAutomation.bat again."
    }
    $baseArguments = @()
    if ($null -ne $Config.Runtime.PythonArguments) {
        $baseArguments = @($Config.Runtime.PythonArguments | ForEach-Object { [string]$_ })
    }
    $allArguments = @($baseArguments + $Arguments)
    $argumentPreview = @($allArguments | ForEach-Object {
        $text = [string]$_
        if ($text -match '\s') { '"{0}"' -f $text.Replace('"', '\"') } else { $text }
    }) -join " "
    Write-AutomationLog -Message "Launching Python subprocess." -Level "DEBUG"
    Write-AutomationLog -Message ("COMMAND | Python | {0} {1}" -f $pythonPath, $argumentPreview) -Level "INFO"
    $pythonTimer = [System.Diagnostics.Stopwatch]::StartNew()
    $commandOutput = New-Object System.Collections.Generic.List[string]

    # v0.502: do not wrap the child process in an array subexpression. The old
    # @(& python ...) form buffered every stdout line until Python exited, which
    # made a healthy long importer look frozen in Status & Logs for many minutes.
    # import_delivery_folder.py flushes its [IMPORT] progress lines, so consume
    # the pipeline as it is produced and mirror every line into the authoritative
    # automation log immediately.
    & $pythonPath @allArguments 2>&1 | ForEach-Object {
        $outputLine = [string]$_
        $commandOutput.Add($outputLine)
        Write-AutomationLog -Message ("Python: {0}" -f $outputLine)
    }
    $exitCode = $LASTEXITCODE
    $pythonTimer.Stop()
    Write-AutomationDebug -Message (
        "Python subprocess finished. ExitCode={0} DurationMs={1} OutputLines={2}" -f
        $exitCode,
        [Math]::Round($pythonTimer.Elapsed.TotalMilliseconds),
        [int]$commandOutput.Count
    )
    if ($exitCode -ne 0) {
        $detail = @($commandOutput | ForEach-Object { [string]$_ }) -join [Environment]::NewLine
        if ($detail.Length -gt 4000) {
            $detail = $detail.Substring($detail.Length - 4000)
        }
        throw "Python command failed with exit code $exitCode.$([Environment]::NewLine)$detail"
    }
    return @($commandOutput)
}

function Publish-AutomationNotification {
    param(
        [Parameter(Mandatory = $true)]$Config,
        [Parameter(Mandatory = $true)][string]$RunMode,
        [Parameter(Mandatory = $true)][bool]$Succeeded,
        [string]$ErrorMessage = ""
    )

    if ($RunMode -eq "RuntimeTest") {
        Write-AutomationDebug -Message "App notification step skipped for RuntimeTest mode."
        return
    }

    $notifications = Get-OptionalProperty -Object $Config -Name "Notifications" -DefaultValue $null
    if ($null -eq $notifications -or -not [bool](Get-OptionalProperty -Object $notifications -Name "Enabled" -DefaultValue $true)) {
        Write-AutomationDebug -Message "App notification step skipped because notifications are disabled."
        return
    }

    $projectRoot = [string](Get-OptionalProperty -Object $Config -Name "ProjectRoot" -DefaultValue "")
    if ([string]::IsNullOrWhiteSpace($projectRoot)) {
        Write-AutomationLog -Message "App notification skipped because ProjectRoot is not configured." -Level "WARN"
        return
    }

    $checkedDates = @($script:CheckedDates | Sort-Object -Unique | ForEach-Object { $_.ToString("yyyy-MM-dd") })
    # Windows PowerShell 5.1 can throw "Argument types do not match" when an
    # array subexpression wraps a generic List directly. Materialize plain
    # object arrays before building notification and run-summary payloads.
    $importResultSnapshot = @($script:ImportResults | ForEach-Object { $_ })
    $safetyDeferredDetailSnapshot = @($script:SafetyDeferredDetails | ForEach-Object { $_ })
    $publishedDates = @($script:PublishedDates | Sort-Object -Unique | ForEach-Object { $_.ToString("yyyy-MM-dd") })
    $importedDates = @($script:ImportedDates | Sort-Object -Unique | ForEach-Object { $_.ToString("yyyy-MM-dd") })
    $pendingDates = @($script:PendingImportDates | Sort-Object -Unique | ForEach-Object { $_.ToString("yyyy-MM-dd") })
    $deferredDates = @($script:SafetyDeferredDates | Sort-Object -Unique | ForEach-Object { $_.ToString("yyyy-MM-dd") })
    $deferredCount = [int]$deferredDates.Count
    $createdBy = [string](Get-OptionalProperty -Object $notifications -Name "CreatedBy" -DefaultValue "sql-delivery-automation")

    if ($Succeeded) {
        $newFileCount = @($script:ImportResults | Where-Object { $_.classification -in @("new", "new_updated") }).Count
        $updatedFileCount = @($script:ImportResults | Where-Object { $_.classification -in @("updated", "new_updated") }).Count
        $noChangeFileCount = @($script:ImportResults | Where-Object { $_.classification -eq "no_changes" }).Count
        $failedFileCount = @($script:ImportResults | Where-Object { $_.classification -eq "failed" }).Count
        $hasImportChanges = $newFileCount -gt 0 -or $updatedFileCount -gt 0
        $hasChanges = $publishedDates.Count -gt 0 -or $hasImportChanges
        $notifyOnNoChanges = [bool](Get-OptionalProperty -Object $notifications -Name "NotifyOnNoChanges" -DefaultValue $true)
        if (-not $hasChanges -and -not $notifyOnNoChanges -and $failedFileCount -eq 0 -and $deferredCount -eq 0) {
            Write-AutomationDebug -Message "App notification suppressed because the run had no changes and no-change notifications are disabled."
            return
        }

        if ($script:ImportResults.Count -gt 0 -and ($hasImportChanges -or $failedFileCount -gt 0)) {
            $notificationType = if ($failedFileCount -gt 0) { "warning" } else { "success" }
            $title = if ($failedFileCount -gt 0) { "Delivery lists imported with warnings" } else { "Delivery lists imported" }
            $message = "Delivery-list import completed: $newFileCount new, $updatedFileCount updated, $noChangeFileCount unchanged, and $failedFileCount failed file(s)."
            $expiresHours = [int](Get-OptionalProperty -Object $notifications -Name "SuccessExpiresInHours" -DefaultValue 12)
        }
        elseif ($script:ImportResults.Count -gt 0) {
            $notificationType = "notice"
            $title = "Delivery-list import check complete"
            $message = "Delivery-list import checked $($script:ImportResults.Count) file(s). No delivery-list changes were detected."
            $expiresHours = [int](Get-OptionalProperty -Object $notifications -Name "NoChangeExpiresInHours" -DefaultValue 2)
        }
        elseif ($publishedDates.Count -gt 0) {
            $notificationType = "success"
            $title = "Delivery lists exported"
            $dateText = (@($publishedDates | Select-Object -First 6) -join ", ")
            if ($publishedDates.Count -gt 6) {
                $dateText = "$dateText and $($publishedDates.Count - 6) more"
            }
            $message = "Automatic delivery-list export completed. $($publishedDates.Count) delivery date(s) were written: $dateText"
            $expiresHours = [int](Get-OptionalProperty -Object $notifications -Name "SuccessExpiresInHours" -DefaultValue 12)
        }
        else {
            $notificationType = "notice"
            $title = "Delivery-list check complete"
            $message = "Automatic delivery-list check completed. $($checkedDates.Count) delivery date(s) were checked and no source changes were detected."
            $expiresHours = [int](Get-OptionalProperty -Object $notifications -Name "NoChangeExpiresInHours" -DefaultValue 2)
        }

        if ($deferredCount -gt 0) {
            $deferredText = (@($deferredDates | Select-Object -First 6) -join ", ")
            if ($deferredCount -gt 6) {
                $deferredText = "$deferredText and $($deferredCount - 6) more"
            }
            $notificationType = "warning"
            $title = if ($hasChanges) { "Delivery lists updated with safety deferrals" } else { "Delivery-list dates deferred for safety" }
            $message = "$message $deferredCount delivery date(s) were safely deferred without replacing their existing data: $deferredText."
            $expiresHours = [int](Get-OptionalProperty -Object $notifications -Name "SuccessExpiresInHours" -DefaultValue 12)
        }
    }
    else {
        $notificationType = "error"
        $title = "Delivery-list update failed"
        $cleanError = [string]$ErrorMessage
        if ($cleanError.Length -gt 600) {
            $cleanError = $cleanError.Substring(0, 600)
        }
        $message = "Automatic delivery-list update failed in $RunMode mode: $cleanError"
        $expiresHours = [int](Get-OptionalProperty -Object $notifications -Name "ErrorExpiresInHours" -DefaultValue 24)
    }

    $affectedListIds = @(Get-AffectedImportListIds -ImportResults $importResultSnapshot)
    $payload = [ordered]@{
        source = "sql-delivery-automation"
        displayMode = "toast"
        target = "delivery-list-management"
        version = "v121"
        mode = $RunMode
        succeeded = $Succeeded
        requestId = [string]$RequestId
        runId = [string]$script:RunId
        startedAt = [string]$script:StartedAt
        checkedDates = $checkedDates
        publishedDates = $publishedDates
        importedDates = $importedDates
        pendingImportDates = $pendingDates
        safetyDeferredDates = $deferredDates
        safetyDeferredDetails = $safetyDeferredDetailSnapshot
        importResults = $importResultSnapshot
        awRejectSync = $script:AwRejectSyncResult
        awCuttingSync = $script:AwCuttingSyncResult
        affectedListIds = $affectedListIds
        runAction = $RunAction
        completedAt = (Get-Date).ToUniversalTime().ToString("o")
        error = $(if ($Succeeded) { "" } else { [string]$ErrorMessage })
        logPath = $script:LogPath
    }
    $request = [ordered]@{
        projectRoot = $projectRoot
        notificationType = $notificationType
        title = $title
        message = $message
        createdBy = $createdBy
        payload = $payload
        expiresHours = [Math]::Max($expiresHours, 1)
        initializeStore = $false
    }
    $publisherPath = Join-Path $PSScriptRoot "publish_automation_notification.py"
    $requestPath = Join-Path $Config.WorkingRoot ("State\notification-request-{0}.json" -f [guid]::NewGuid().ToString("N"))

    try {
        Write-AutomationDebug -Message ("Preparing app notification. Type={0} Title={1} RequestFile={2}" -f $notificationType, $title, $requestPath)
        $request | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $requestPath -Encoding UTF8
        [void](Invoke-ConfiguredPython -Config $Config -Arguments @(
            $publisherPath,
            "--request-file", $requestPath
        ))
        Write-AutomationLog -Message "Published app notification: $title"
    }
    catch {
        Write-AutomationLog -Message ("Automation completed, but the app notification could not be published: {0}" -f $_.Exception.Message) -Level "WARN"
    }
    finally {
        Remove-Item -LiteralPath $requestPath -Force -ErrorAction SilentlyContinue
    }
}

function Test-DestinationWriteAccess {
    param([Parameter(Mandatory = $true)]$Config)

    $folder = [string]$Config.DestinationFolder
    if (-not (Test-Path -LiteralPath $folder -PathType Container)) {
        [void](New-Item -ItemType Directory -Path $folder -Force)
    }
    $probe = Join-Path $folder (".sql-export-write-test-{0}.tmp" -f [guid]::NewGuid().ToString("N"))
    try {
        "write test" | Set-Content -LiteralPath $probe -Encoding ASCII
        if (-not (Test-Path -LiteralPath $probe -PathType Leaf)) {
            throw "Write test file was not created."
        }
        Write-AutomationLog -Message "Destination write access passed: $folder"
    }
    finally {
        Remove-Item -LiteralPath $probe -Force -ErrorAction SilentlyContinue
    }
}

function Publish-Workbook {
    param(
        [Parameter(Mandatory = $true)][string]$SourcePath,
        [Parameter(Mandatory = $true)][string]$DestinationPath
    )

    $destinationFolder = Split-Path -Parent $DestinationPath
    if (-not (Test-Path -LiteralPath $destinationFolder -PathType Container)) {
        [void](New-Item -ItemType Directory -Path $destinationFolder -Force)
    }

    $fileName = [IO.Path]::GetFileName($DestinationPath)
    $partial = Join-Path $destinationFolder (".{0}.{1}.partial" -f $fileName, [guid]::NewGuid().ToString("N"))
    $backup = Join-Path $destinationFolder (".{0}.{1}.backup" -f $fileName, [guid]::NewGuid().ToString("N"))
    try {
        Write-AutomationLog -Message "Publishing workbook to $DestinationPath"
        Copy-Item -LiteralPath $SourcePath -Destination $partial -Force
        $partialLength = (Get-Item -LiteralPath $partial).Length
        Write-AutomationLog -Message "Staged $fileName on the destination share ($partialLength bytes)."

        if (Test-Path -LiteralPath $DestinationPath -PathType Leaf) {
            $isUncPath = $DestinationPath.StartsWith("\\")
            if (-not $isUncPath) {
                try {
                    [System.IO.File]::Replace($partial, $DestinationPath, $backup, $true)
                    Remove-Item -LiteralPath $backup -Force -ErrorAction SilentlyContinue
                    Write-AutomationLog -Message "Replaced existing local workbook atomically: $fileName"
                    return
                }
                catch {
                    Write-AutomationLog -Message ("Atomic local replace was unavailable; using the compatible overwrite path instead: {0}" -f $_.Exception.Message) -Level "WARN"
                }
            }

            # SMB/UNC shares do not consistently support System.IO.File.Replace.
            # The partial file is deliberately not an .xlsx file, so the scanner
            # importer cannot see it while the validated workbook is copied over.
            Copy-Item -LiteralPath $partial -Destination $DestinationPath -Force
            Write-AutomationLog -Message "Overwrote existing workbook using the network-share compatible path: $fileName"
        }
        else {
            Move-Item -LiteralPath $partial -Destination $DestinationPath -Force
            Write-AutomationLog -Message "Created new workbook: $fileName"
        }

        if (-not (Test-Path -LiteralPath $DestinationPath -PathType Leaf)) {
            throw "The published workbook could not be verified at $DestinationPath"
        }
    }
    finally {
        Remove-Item -LiteralPath $partial -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $backup -Force -ErrorAction SilentlyContinue
    }
}

function Export-DeliveryDate {
    param(
        [Parameter(Mandatory = $true)]$Config,
        [Parameter(Mandatory = $true)][datetime]$Date,
        [Parameter(Mandatory = $true)][string]$RunMode
    )

    $dateKey = $Date.ToString("yyyy-MM-dd")
    $script:CheckedDates.Add($Date)
    Write-AutomationDebug -Message (
        "Export context for {0}. Server={1} Database={2} HeaderTable={3}.{4} ItemTable={3}.{5} QueryTimeoutSeconds={6}" -f
        $dateKey,
        [string]$Config.Database.Server,
        [string]$Config.Database.Database,
        [string]$Config.SourceMapping.Schema,
        [string]$Config.SourceMapping.HeaderTable,
        [string]$Config.SourceMapping.ItemTable,
        [int]$Config.Database.QueryTimeoutSeconds
    )
    Write-AutomationLog -Message "Reading A+W delivery rows for $dateKey"
    $rows = @(Get-DeliveryRows -Config $Config -Date $Date)
    $excludedRows = @($script:LastExcludedDeliveryRows)
    $excludedRemakeCount = @($excludedRows | Where-Object { [string]$_.remake -eq "RM" }).Count
    $eligibleRemakeCount = @($rows | Where-Object { [string]$_.remake -eq "RM" }).Count
    Write-AutomationLog -Message (
        (
            "A+W source selection for {0}: {1} raw line item(s), {2} selected for export, {3} verified exclusion(s); " +
            "remake lines {4} raw, {5} selected, {6} verified exclusion(s). Rule={7}"
        ) -f
        $dateKey,
        [int]$script:LastRawDeliveryRowCount,
        [int]$rows.Count,
        [int]$excludedRows.Count,
        [int]$script:LastRawRemakeLineCount,
        [int]$eligibleRemakeCount,
        [int]$excludedRemakeCount,
        [string]$script:LastEligibilityRule
    )
    if ($excludedRows.Count -gt 0) {
        $excludedDetail = @(
            $excludedRows |
                Sort-Object order, item |
                Select-Object -First 60 |
                ForEach-Object {
                    "{0}-{1} orderStatus={2} itemStatus={3} batches={4}/{5}/{6} remake={7} reason={8}" -f
                    [string]$_.order,
                    ([string]$_.item).PadLeft(3, '0'),
                    [string]$_.orderStatus,
                    [string]$_.itemStatus,
                    [string]$_.productionBatch1,
                    [string]$_.productionBatch2,
                    [string]$_.productionBatch3,
                    $(if ([string]$_.remake -eq "RM") { "yes" } else { "no" }),
                    [string]$_.reason
                }
        ) -join ", "
        Write-AutomationLog -Message ("Verified A+W exclusions for {0}: {1}" -f $dateKey, $excludedDetail) -Level "WARN"
        if ($excludedRows.Count -gt 60) {
            Write-AutomationLog -Message "Verified-exclusion detail was limited to the first 60 of $($excludedRows.Count) rows." -Level "WARN"
        }
    }
    Write-AutomationLog -Message (
        "A+W status diagnostics for {0}: {1}. Status and production progress are diagnostic only and do not determine delivery-list membership." -f
        $dateKey,
        [string]$script:LastStatusDiagnosticSummary
    )
    if ($rows.Count -eq 0) {
        Write-AutomationLog -Message "No source rows were returned for $dateKey after exact verified exclusions. The existing workbook is preserved and no destructive import is attempted." -Level "WARN"
        return
    }
    $script:SourceDates.Add($Date)

    $orderCount = @($rows | ForEach-Object { [string]$_.order } | Sort-Object -Unique).Count
    $pieceCount = 0
    $remakeCount = 0
    foreach ($row in $rows) {
        $pieceCount += [int][decimal]$row.quantity
        if ([string]$row.remake -eq "RM") {
            $remakeCount++
        }
    }
    $remakeRows = @($rows | Where-Object { [string]$_.remake -eq "RM" })
    $remakeOrderCount = @($remakeRows | ForEach-Object { [string]$_.order } | Sort-Object -Unique).Count
    Write-AutomationLog -Message "$dateKey contains $orderCount selected source orders, $($rows.Count) line items, $pieceCount pieces, $remakeCount remake lines, and $remakeOrderCount remake orders."
    if ($remakeRows.Count -gt 0) {
        $remakeDetail = @($remakeRows | ForEach-Object {
            "{0}-{1} flags={2}" -f [string]$_.order, ([string]$_.item).PadLeft(3, '0'), [string]$_.remakeFlags
        }) -join ", "
        Write-AutomationLog -Message "SQL remake detail for $dateKey (order-item and raw header flags): $remakeDetail"
    }
    $validation = Get-OptionalProperty -Object $Config -Name "Validation" -DefaultValue $null
    if ($RunMode -eq "Test" -and $null -ne $validation) {
        $knownDate = [string](Get-OptionalProperty -Object $validation -Name "KnownDeliveryDate" -DefaultValue "")
        if ($dateKey -eq $knownDate) {
            $expectedOrders = [int](Get-OptionalProperty -Object $validation -Name "ExpectedOrders" -DefaultValue 0)
            $expectedLines = [int](Get-OptionalProperty -Object $validation -Name "ExpectedLineItems" -DefaultValue 0)
            $expectedPieces = [int](Get-OptionalProperty -Object $validation -Name "ExpectedPieces" -DefaultValue 0)
            $expectedRemakes = [int](Get-OptionalProperty -Object $validation -Name "ExpectedRemakeLines" -DefaultValue 0)
            if ($orderCount -eq $expectedOrders -and $rows.Count -eq $expectedLines -and $pieceCount -eq $expectedPieces -and $remakeCount -eq $expectedRemakes) {
                Write-AutomationLog -Message "Known-date count comparison passed for $knownDate."
            }
            else {
                Write-AutomationLog -Message "Known-date comparison differs. Expected $expectedOrders orders, $expectedLines lines, $expectedPieces pieces, and $expectedRemakes remake lines." -Level "WARN"
            }
        }
    }

    $dimensionUnitsPerInch = [int](Get-OptionalProperty -Object $Config.SourceMapping -Name "DimensionUnitsPerInch" -DefaultValue 32)
    $payload = [ordered]@{
        version = "v121"
        deliveryDate = $dateKey
        generatedAt = (Get-Date).ToUniversalTime().ToString("o")
        dimensionUnitsPerInch = $dimensionUnitsPerInch
        rows = $rows
    }
    $hashPayload = [ordered]@{
        deliveryDate = $dateKey
        sourceMapping = $Config.SourceMapping
        sourceSelectionRule = [string]$script:LastEligibilityRule
        rows = $rows
    }
    $hashText = $hashPayload | ConvertTo-Json -Depth 8 -Compress
    $dataHash = Get-Sha256Text -Text $hashText

    # Website version 4: keep the canonical SQL rows in memory for direct scanner
    # reconciliation. The XLSX generated below remains a human-readable fallback
    # and export artifact; it is no longer required as the SQL import transport.
    $directSourcePath = (
        "aw-sql://{0}/{1}/{2}/{3}+{4}/{5}" -f
        [string]$Config.Database.Server,
        [string]$Config.Database.Database,
        [string]$Config.SourceMapping.Schema,
        [string]$Config.SourceMapping.HeaderTable,
        [string]$Config.SourceMapping.ItemTable,
        $dateKey
    )
    $script:DirectImportPayloads.Add([ordered]@{
        deliveryDate = $dateKey
        sourceName = "A+W SQL $dateKey"
        sourcePath = $directSourcePath
        sourceHash = $dataHash
        payload = $payload
    })
    Write-AutomationDebug -Message (
        "Queued direct A+W scanner payload for {0}. Rows={1} SourceHash={2}" -f
        $dateKey, [int]$rows.Count, $dataHash
    )

    $fileName = [string]::Format([Globalization.CultureInfo]::InvariantCulture, [string]$Config.Report.OutputNameFormat, $Date)
    $destinationPath = Join-Path ([string]$Config.DestinationFolder) $fileName
    $statePath = Get-StatePath -Config $Config -Date $Date
    $state = Read-DateState -Config $Config -Date $Date
    Write-AutomationDebug -Message (
        "Computed authoritative source fingerprint for {0}. DataHash={1} Destination={2} StateFile={3} PreviousStatePresent={4}" -f
        $dateKey,
        $dataHash,
        $destinationPath,
        $statePath,
        [bool]($null -ne $state)
    )

    $stateHash = if ($null -ne $state -and $state.PSObject.Properties.Name -contains "dataHash") { [string]$state.dataHash } else { "" }
    $stateImported = if ($null -ne $state -and $state.PSObject.Properties.Name -contains "imported") { [bool]$state.imported } else { $false }
    $stateWorkbookHash = if ($null -ne $state -and $state.PSObject.Properties.Name -contains "workbookHash") { [string]$state.workbookHash } else { "" }
    $stateFormatVersion = if ($null -ne $state -and $state.PSObject.Properties.Name -contains "workbookFormatVersion") { [string]$state.workbookFormatVersion } else { "" }
    $currentWorkbookHash = ""
    if (Test-Path -LiteralPath $destinationPath -PathType Leaf) {
        try {
            $currentWorkbookHash = (Get-FileHash -LiteralPath $destinationPath -Algorithm SHA256).Hash.ToLowerInvariant()
        }
        catch {
            Write-AutomationLog -Message "Existing workbook could not be hashed and will be rebuilt: $fileName" -Level "WARN"
        }
    }
    $workbookIsCurrent = (
        $stateFormatVersion -eq "v324-ooxml-2" -and
        -not [string]::IsNullOrWhiteSpace($stateWorkbookHash) -and
        $currentWorkbookHash -eq $stateWorkbookHash
    )
    Write-AutomationDebug -Message (
        "Workbook/state comparison for {0}. DataUnchanged={1} WorkbookExists={2} WorkbookHashMatches={3} FormatVersion={4} PreviouslyImported={5}" -f
        $dateKey,
        [bool]($stateHash -eq $dataHash),
        [bool](Test-Path -LiteralPath $destinationPath -PathType Leaf),
        [bool]$workbookIsCurrent,
        $(if ([string]::IsNullOrWhiteSpace($stateFormatVersion)) { "none" } else { $stateFormatVersion }),
        [bool]$stateImported
    )
    if ($RunMode -ne "Test" -and $stateHash -eq $dataHash -and $workbookIsCurrent) {
        Write-AutomationLog -Message "Unchanged: $fileName"
        if (-not $stateImported) {
            Write-AutomationDebug -Message "Source/workbook are unchanged but scanner import state is incomplete; queueing $dateKey for reconciliation."
            $script:PendingImportDates.Add($Date)
        }
        else {
            Write-AutomationDebug -Message "Source/workbook and scanner import state are already current for $dateKey; no rebuild is required."
        }
        return
    }
    if ($RunMode -ne "Test" -and $stateHash -eq $dataHash -and -not $workbookIsCurrent) {
        Write-AutomationLog -Message "Existing workbook is missing the v0.324 source-lineage integrity marker or does not match its recorded hash. Rebuilding $fileName." -Level "WARN"
    }

    $runToken = "{0}-{1}" -f $dateKey, [guid]::NewGuid().ToString("N")
    $jsonPath = Join-Path $Config.WorkingRoot ("Staging\$runToken.json")
    $xlsxPath = Join-Path $Config.WorkingRoot ("Staging\$runToken.xlsx")
    $builderPath = Join-Path $PSScriptRoot "build_delivery_workbook.py"
    $payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
    $payloadBytes = (Get-Item -LiteralPath $jsonPath).Length
    Write-AutomationDebug -Message (
        "Staging payload ready for {0}. Input={1} Output={2} PayloadBytes={3} DimensionUnitsPerInch={4}" -f
        $dateKey,
        $jsonPath,
        $xlsxPath,
        [int64]$payloadBytes,
        $dimensionUnitsPerInch
    )

    try {
        Write-AutomationLog -Message "Building workbook for $dateKey in the staging folder."
        [void](Invoke-ConfiguredPython -Config $Config -Arguments @(
            $builderPath,
            "--input", $jsonPath,
            "--output", $xlsxPath,
            "--delivery-date", $dateKey
        ))
        if (-not (Test-Path -LiteralPath $xlsxPath -PathType Leaf)) {
            throw "Workbook builder did not create $xlsxPath"
        }
        $length = (Get-Item -LiteralPath $xlsxPath).Length
        Write-AutomationDebug -Message ("Workbook builder produced {0} bytes for {1}." -f [int64]$length, $dateKey)
        if ($length -lt [int]$Config.MinimumWorkbookBytes) {
            throw "Generated workbook is unexpectedly small: $length bytes"
        }
        Write-AutomationLog -Message "Validating generated workbook for $dateKey."
        [void](Invoke-ConfiguredPython -Config $Config -Arguments @($builderPath, "--validate", $xlsxPath))
        Write-AutomationDebug -Message "Workbook validation completed for $dateKey; publishing validated file to the delivery-list destination."
        Publish-Workbook -SourcePath $xlsxPath -DestinationPath $destinationPath
        $publishedWorkbookHash = (Get-FileHash -LiteralPath $destinationPath -Algorithm SHA256).Hash.ToLowerInvariant()
        Write-AutomationDebug -Message ("Published workbook verification for {0}. SHA256={1}" -f $dateKey, $publishedWorkbookHash)

        $sourceDataChanged = ($null -eq $state -or $stateHash -ne $dataHash)
        $nextImportedState = (-not $sourceDataChanged -and $stateImported)
        Write-DateState -Config $Config -Date $Date -Hash $dataHash -WorkbookPath $destinationPath -WorkbookHash $publishedWorkbookHash -RowCount $rows.Count -PieceCount $pieceCount -Imported $nextImportedState
        Write-AutomationDebug -Message (
            "Persisted delivery-date state for {0}. Rows={1} Pieces={2} Imported={3} StateFile={4}" -f
            $dateKey, [int]$rows.Count, [int]$pieceCount, [bool]$nextImportedState, $statePath
        )
        $script:PublishedDates.Add($Date)
        if ($sourceDataChanged -or -not $stateImported) {
            $script:PendingImportDates.Add($Date)
        }
        Write-AutomationLog -Message "Published $fileName with $($rows.Count) line items and $pieceCount pieces."
    }
    catch {
        Write-AutomationLog -Message ("Delivery-date export failed for {0}. {1}: {2}" -f $dateKey, $_.Exception.GetType().Name, $_.Exception.Message) -Level "ERROR"
        Write-AutomationDebug -Message ("Failure script stack for {0}: {1}" -f $dateKey, [string]$_.ScriptStackTrace)
        $failedFolder = Join-Path $Config.WorkingRoot "Failed"
        if (Test-Path -LiteralPath $jsonPath -PathType Leaf) {
            Copy-Item -LiteralPath $jsonPath -Destination (Join-Path $failedFolder ([IO.Path]::GetFileName($jsonPath))) -Force -ErrorAction SilentlyContinue
        }
        if (Test-Path -LiteralPath $xlsxPath -PathType Leaf) {
            Copy-Item -LiteralPath $xlsxPath -Destination (Join-Path $failedFolder ([IO.Path]::GetFileName($xlsxPath))) -Force -ErrorAction SilentlyContinue
        }
        throw
    }
    finally {
        Remove-Item -LiteralPath $jsonPath -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $xlsxPath -Force -ErrorAction SilentlyContinue
        Write-AutomationDebug -Message ("Cleaned staging files for {0}. Input={1} Output={2}" -f $dateKey, $jsonPath, $xlsxPath)
    }
}

function Invoke-ScannerImport {
    param(
        [Parameter(Mandatory = $true)]$Config,
        [Parameter(Mandatory = $false)][AllowEmptyCollection()][datetime[]]$Dates = @(),
        [Parameter(Mandatory = $false)][AllowEmptyCollection()][datetime[]]$ForceDates = @(),
        [bool]$Force = $false,
        [bool]$SelectiveSqlSync = $false,
        [bool]$RejectOnly = $false
    )

    $importMode = [string](Get-OptionalProperty -Object $Config.Import -Name "Mode" -DefaultValue "disabled")
    if (($null -eq $Dates -or $Dates.Count -eq 0) -and -not $RejectOnly) {
        Write-AutomationLog -Message "No delivery-list workbooks require scanner verification or import."
        return
    }
    if (-not $Force -and $importMode -eq "disabled") {
        return
    }
    if ($importMode -notin @("disabled", "direct-store")) {
        throw "Import.Mode must be disabled or direct-store."
    }
    $projectRoot = [string]$Config.ProjectRoot
    if ([string]::IsNullOrWhiteSpace($projectRoot)) {
        throw "ProjectRoot is not configured. Run setup again."
    }

    $targetDates = @($Dates | Sort-Object -Unique)
    $forcedDates = @($ForceDates | Sort-Object -Unique)
    Write-AutomationDebug -Message (
        "Scanner import request. ImportMode={0} Force={1} SelectiveSqlSync={2} TargetDates=[{3}] ForceDates=[{4}]" -f
        $importMode,
        [bool]$Force,
        [bool]$SelectiveSqlSync,
        (Get-AutomationDateListText -Dates $targetDates),
        (Get-AutomationDateListText -Dates $forcedDates)
    )
    Write-AutomationLog -Message ("Scanner project root for import: {0}" -f $projectRoot)

    # Bind the detached updater process to the exact scanner store used by the
    # live web server. This prevents Import History from reporting a successful
    # import into one SQLite database while Scan/Print are reading another.
    $scannerStore = Get-OptionalProperty -Object $Config -Name "ScannerStore" -DefaultValue $null
    $expectedStoreMode = ""
    $expectedStoreDatabase = ""
    $expectedStoreServer = ""
    if ($null -ne $scannerStore) {
        $expectedStoreMode = ([string](Get-OptionalProperty -Object $scannerStore -Name "Mode" -DefaultValue "")).Trim().ToLowerInvariant()
        $expectedStoreDatabase = ([string](Get-OptionalProperty -Object $scannerStore -Name "Database" -DefaultValue "")).Trim()
        $expectedStoreServer = ([string](Get-OptionalProperty -Object $scannerStore -Name "Server" -DefaultValue "")).Trim()
    }
    if ($expectedStoreMode -eq "sqlite") {
        if ([string]::IsNullOrWhiteSpace($expectedStoreDatabase)) {
            throw "ScannerStore.Database is required when ScannerStore.Mode is sqlite."
        }
        $expectedStoreDatabase = [System.IO.Path]::GetFullPath($expectedStoreDatabase)
        $env:DLS_DATABASE_PATH = $expectedStoreDatabase
        Write-AutomationLog -Message ("Bound scanner importer to live SQLite database: {0}" -f $expectedStoreDatabase)
    }
    elseif (-not [string]::IsNullOrWhiteSpace($expectedStoreMode)) {
        Write-AutomationLog -Message (
            "Scanner importer will validate live store identity. Mode={0} Database={1} Server={2}" -f
            $expectedStoreMode,
            $expectedStoreDatabase,
            $expectedStoreServer
        )
    }
    else {
        Write-AutomationLog -Message "Scanner-store identity was not supplied by the web control plane; importer mismatch protection is unavailable for this run." -Level "WARN"
    }

    $importerPath = Join-Path $PSScriptRoot "import_delivery_folder.py"
    $dateFrom = if ($targetDates.Count -gt 0) { ($targetDates | Select-Object -First 1).ToString("yyyy-MM-dd") } else { (Get-Date).ToString("yyyy-MM-dd") }
    $dateTo = if ($targetDates.Count -gt 0) { ($targetDates | Select-Object -Last 1).ToString("yyyy-MM-dd") } else { $dateFrom }
    $resultPath = Join-Path $Config.WorkingRoot ("State\import-result-{0}.json" -f [guid]::NewGuid().ToString("N"))
    $syncRequestPath = Join-Path $Config.WorkingRoot ("State\import-sync-request-{0}.json" -f [guid]::NewGuid().ToString("N"))
    $directPayloadPath = Join-Path $Config.WorkingRoot ("State\direct-sql-payload-{0}.json" -f [guid]::NewGuid().ToString("N"))
    Write-AutomationDebug -Message (
        "Scanner import temporary files. Result={0} SyncRequest={1} DirectPayload={2}" -f
        $resultPath, $syncRequestPath, $directPayloadPath
    )

    if ($SelectiveSqlSync) {
        Write-AutomationLog -Message "Verifying direct A+W SQL rows against scanner stage lists for $dateFrom through $dateTo. Generated workbooks are fallback/export artifacts."
    }
    else {
        Write-AutomationLog -Message "Importing workbooks from the Temp Delivery Lists folder for $dateFrom through $dateTo"
    }

    try {
        $arguments = @(
            $importerPath,
            "--project-root", $projectRoot,
            "--folder", [string]$Config.DestinationFolder,
            "--date-from", $dateFrom,
            "--date-to", $dateTo,
            "--user", [string]$Config.Import.User,
            "--run-id", [string]$script:RunId,
            "--run-started-at", [string]$script:StartedAt,
            "--initialize-store", ([bool](Get-OptionalProperty -Object $Config.Import -Name "InitializeStore" -DefaultValue $true)).ToString().ToLowerInvariant(),
            "--result-path", $resultPath,
            "--reject-only", $RejectOnly.ToString().ToLowerInvariant()
        )
        if (-not [string]::IsNullOrWhiteSpace($expectedStoreMode)) {
            $arguments += @("--expected-store-mode", $expectedStoreMode)
        }
        if (-not [string]::IsNullOrWhiteSpace($expectedStoreDatabase)) {
            $arguments += @("--expected-store-database", $expectedStoreDatabase)
        }
        if (-not [string]::IsNullOrWhiteSpace($expectedStoreServer)) {
            $arguments += @("--expected-store-server", $expectedStoreServer)
        }
        if ($SelectiveSqlSync) {
            $targetDateKeys = @($targetDates | ForEach-Object { $_.ToString("yyyy-MM-dd") })
            $directPayloads = @(
                $script:DirectImportPayloads | Where-Object {
                    $targetDateKeys -contains [string]$_.deliveryDate
                }
            )
            $rejectSyncRowCount = if ($null -ne $script:AwRejectSyncPayload) { @($script:AwRejectSyncPayload.rows).Count } else { 0 }
            $cuttingSyncRowCount = if ($null -ne $script:AwCuttingSyncPayload) { @($script:AwCuttingSyncPayload.rows).Count } else { 0 }
            if ($directPayloads.Count -gt 0 -or $rejectSyncRowCount -gt 0 -or $cuttingSyncRowCount -gt 0 -or $RejectOnly) {
                $directRequest = [ordered]@{
                    # Compatibility marker retained for older diagnostics/tests: v484-aw-direct-reject-1
                    version = "v498-aw-direct-production-1"
                    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
                    payloads = @($directPayloads)
                    rejectSync = $script:AwRejectSyncPayload
                    cuttingSync = $script:AwCuttingSyncPayload
                }
                Write-AutomationStep -Message "Serializing the direct A+W delivery/reject/production payload for the scanner importer."
                $directRequest | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $directPayloadPath -Encoding UTF8
                $directPayloadBytes = $(if (Test-Path -LiteralPath $directPayloadPath -PathType Leaf) { (Get-Item -LiteralPath $directPayloadPath).Length } else { 0 })
                $arguments += @("--direct-payload-path", $directPayloadPath)
                Write-AutomationLog -Message (
                    "Passing {0} direct A+W delivery payload(s), {1} raw A+W breakage row(s), and {2} A+W production row(s) to the scanner importer. PayloadBytes={3}." -f
                    [int]$directPayloads.Count, [int]$rejectSyncRowCount, [int]$cuttingSyncRowCount, [int64]$directPayloadBytes
                )
            }
            else {
                Write-AutomationLog -Message "No direct SQL delivery or reject payloads were available for this selective run; compatibility workbook verification will be used." -Level "WARN"
            }

            $syncRequest = [ordered]@{
                targetDates = $targetDateKeys
                forceImportDates = @($forcedDates | ForEach-Object { $_.ToString("yyyy-MM-dd") })
                sourceMode = $(if ($directPayloads.Count -gt 0) { "aw-sql-direct" } else { "workbook-compatibility" })
                allowSourceRemovals = $false
                supersededOrderCandidates = @($script:SupersededOrderCandidates | ForEach-Object { $_ })
                verifiedExcludedOrderItems = @(
                    $script:VerifiedSourceExclusions | ForEach-Object {
                        [ordered]@{
                            deliveryDate = [string]$_.deliveryDate
                            orderNumber = [string]$_.orderNumber
                            itemNumber = [string]$_.itemNumber
                            reason = [string]$_.reason
                        }
                    }
                )
            }
            $syncRequest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $syncRequestPath -Encoding UTF8
            $arguments += @("--sync-request-path", $syncRequestPath)
            Write-AutomationDebug -Message ("Scanner sync request prepared. Path={0}" -f $syncRequestPath)
        }

        $pythonImportFailure = $null
        try {
            [void](Invoke-ConfiguredPython -Config $Config -Arguments $arguments)
        }
        catch {
            # The importer intentionally exits nonzero when one workbook fails, but it
            # still writes a normalized result file. Read that file first so one bad
            # date becomes a detailed warning instead of hiding every successful date.
            $pythonImportFailure = $_
        }

        Write-AutomationLog -Message "Scanner import verification returned. Reading the normalized result summary."
        if (-not (Test-Path -LiteralPath $resultPath -PathType Leaf)) {
            if ($null -ne $pythonImportFailure) {
                throw $pythonImportFailure
            }
            throw "Scanner import verification completed without producing its result summary."
        }
        $result = Get-Content -LiteralPath $resultPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $resolvedScannerStore = Get-OptionalProperty -Object $result -Name "scannerStore" -DefaultValue $null
        if ($null -ne $resolvedScannerStore) {
            Write-AutomationLog -Message (
                "Scanner import store confirmed. Mode={0} Database={1} Server={2}" -f
                [string](Get-OptionalProperty -Object $resolvedScannerStore -Name "mode" -DefaultValue ""),
                [string](Get-OptionalProperty -Object $resolvedScannerStore -Name "database" -DefaultValue ""),
                [string](Get-OptionalProperty -Object $resolvedScannerStore -Name "server" -DefaultValue "")
            )
        }
        Write-AutomationDebug -Message (
            "Normalized scanner result loaded. Files={0} ImportedDates={1} FailedDates={2}" -f
            [int]@($result.files).Count,
            [int]@($result.importedDates).Count,
            [int]@($result.failedDates).Count
        )
        foreach ($fileResultDebug in @($result.files)) {
            Write-AutomationDebug -Message (
                "Import result. File={0} DeliveryDate={1} Classification={2} Reason={3}" -f
                [string](Get-OptionalProperty -Object $fileResultDebug -Name "fileName" -DefaultValue ""),
                [string](Get-OptionalProperty -Object $fileResultDebug -Name "deliveryDate" -DefaultValue ""),
                [string](Get-OptionalProperty -Object $fileResultDebug -Name "classification" -DefaultValue ""),
                [string](Get-OptionalProperty -Object $fileResultDebug -Name "reason" -DefaultValue "")
            )
        }
        $lastImportResultPath = Join-Path $Config.WorkingRoot "State\last-import-result.json"
        Copy-Item -LiteralPath $resultPath -Destination $lastImportResultPath -Force
        $script:ImportResults = @($script:ImportResults + @($result.files))
        $awRejectSyncResult = Get-OptionalProperty -Object $result -Name "awRejectSync" -DefaultValue $null
        if ($null -ne $awRejectSyncResult) {
            $script:AwRejectSyncResult = $awRejectSyncResult
            $rejectSyncOk = [bool](Get-OptionalProperty -Object $awRejectSyncResult -Name "ok" -DefaultValue $true)
            if (-not $rejectSyncOk) {
                Write-AutomationLog -Message (
                    "A+W reject synchronization was skipped after an error; delivery-list reconciliation completed independently: {0}" -f
                    [string](Get-OptionalProperty -Object $awRejectSyncResult -Name "error" -DefaultValue "Unknown reject synchronization error")
                ) -Level "WARN"
            }
            Write-AutomationLog -Message (
                "A+W Internal Reject sync result: sourceRows={0}, logicalEvents={1}, mirroredInternalRejects={2}, insertedSourceRows={3}, updatedSourceRows={4}, unchangedSourceRows={5}." -f
                [int](Get-OptionalProperty -Object $awRejectSyncResult -Name "sourceRows" -DefaultValue 0),
                [int](Get-OptionalProperty -Object $awRejectSyncResult -Name "logicalEvents" -DefaultValue 0),
                [int](Get-OptionalProperty -Object $awRejectSyncResult -Name "mirroredInternalRejects" -DefaultValue 0),
                [int](Get-OptionalProperty -Object $awRejectSyncResult -Name "insertedSourceRows" -DefaultValue 0),
                [int](Get-OptionalProperty -Object $awRejectSyncResult -Name "updatedSourceRows" -DefaultValue 0),
                [int](Get-OptionalProperty -Object $awRejectSyncResult -Name "unchangedSourceRows" -DefaultValue 0)
            )
        }
        $awCuttingSyncResult = Get-OptionalProperty -Object $result -Name "awCuttingSync" -DefaultValue $null
        if ($null -ne $awCuttingSyncResult) {
            $script:AwCuttingSyncResult = $awCuttingSyncResult
            $cuttingSyncOk = [bool](Get-OptionalProperty -Object $awCuttingSyncResult -Name "ok" -DefaultValue $true)
            if (-not $cuttingSyncOk) {
                Write-AutomationLog -Message (
                    "A+W Cutting synchronization was skipped after an error; delivery-list reconciliation completed independently: {0}" -f
                    [string](Get-OptionalProperty -Object $awCuttingSyncResult -Name "error" -DefaultValue "Unknown Cutting synchronization error")
                ) -Level "WARN"
            }
            Write-AutomationLog -Message (
                "A+W Cutting sync result: sourceRows={0}, generations={1}, inserted={2}, updated={3}, unchanged={4}, durationMs={5}." -f
                [int](Get-OptionalProperty -Object $awCuttingSyncResult -Name "sourceRows" -DefaultValue 0),
                [int](Get-OptionalProperty -Object $awCuttingSyncResult -Name "generations" -DefaultValue 0),
                [int](Get-OptionalProperty -Object $awCuttingSyncResult -Name "inserted" -DefaultValue 0),
                [int](Get-OptionalProperty -Object $awCuttingSyncResult -Name "updated" -DefaultValue 0),
                [int](Get-OptionalProperty -Object $awCuttingSyncResult -Name "unchanged" -DefaultValue 0),
                [int](Get-OptionalProperty -Object $awCuttingSyncResult -Name "durationMs" -DefaultValue 0)
            )
        }
        $pendingSupersededReviews = [int](Get-OptionalProperty -Object $result -Name "pendingSupersededOrderReviews" -DefaultValue 0)
        $candidateReviewSummary = Get-OptionalProperty -Object $result -Name "supersededOrderReview" -DefaultValue $null
        $candidateReviewWarning = [string](Get-OptionalProperty -Object $result -Name "supersededOrderReviewWarning" -DefaultValue "")
        if ($null -ne $candidateReviewSummary) {
            $detectedCandidateCount = [int](Get-OptionalProperty -Object $candidateReviewSummary -Name "candidateCount" -DefaultValue 0)
            $systemApprovedCount = [int](Get-OptionalProperty -Object $candidateReviewSummary -Name "systemApprovedCount" -DefaultValue 0)
            if ([string]::IsNullOrWhiteSpace($candidateReviewWarning)) {
                $reviewLogLevel = if ($pendingSupersededReviews -gt 0) { "WARN" } else { "INFO" }
                Write-AutomationLog -Message (
                    "Superseded-order review sync: {0} candidate(s) checked, {1} pending review(s), {2} migrated exact approval(s)." -f
                    $detectedCandidateCount,
                    $pendingSupersededReviews,
                    $systemApprovedCount
                ) -Level $reviewLogLevel
            }
            else {
                Write-AutomationLog -Message (
                    "Detected {0} superseded-order review candidate payload(s), but the review queue was not synchronized." -f
                    $detectedCandidateCount
                ) -Level "WARN"
            }
        }
        if (-not [string]::IsNullOrWhiteSpace($candidateReviewWarning)) {
            Write-AutomationLog -Message (
                "Delivery-list rows were imported, but the optional Superseded Order Review queue could not be synchronized: {0}" -f
                $candidateReviewWarning
            ) -Level "WARN"
        }

        foreach ($fileResult in @($result.files)) {
            foreach ($stageSummary in @(Get-OptionalProperty -Object $fileResult -Name "stageSummaries" -DefaultValue @())) {
                $stageName = [string](Get-OptionalProperty -Object $stageSummary -Name "stage" -DefaultValue "")
                if ($stageName -notmatch '(?i)staging') {
                    continue
                }
                $activeQty = [int](Get-OptionalProperty -Object $stageSummary -Name "totalQty" -DefaultValue 0)
                $manualQty = [int](Get-OptionalProperty -Object $stageSummary -Name "manualPieceQty" -DefaultValue 0)
                $protectedManualQty = [int](Get-OptionalProperty -Object $stageSummary -Name "protectedManualPieceQty" -DefaultValue 0)
                $sourceQty = [int](Get-OptionalProperty -Object $stageSummary -Name "sourceTotalQty" -DefaultValue ([Math]::Max($activeQty - $manualQty, 0)))
                $summaryLevel = if ($manualQty -gt 0) { "WARN" } else { "INFO" }
                $deliveryDateText = [string](Get-OptionalProperty -Object $fileResult -Name "deliveryDate" -DefaultValue "unknown date")
                if (($sourceQty + $manualQty) -gt 0 -or $activeQty -eq 0) {
                    Write-AutomationLog -Message (
                        "Scanner staging total for {0}: {1} A+W piece(s) + {2} manual piece(s) = {3} active; {4} manual piece(s) are protected from A+W import." -f
                        $deliveryDateText,
                        $sourceQty,
                        $manualQty,
                        $activeQty,
                        $protectedManualQty
                    ) -Level $summaryLevel
                }
                else {
                    Write-AutomationLog -Message (
                        "Scanner staging total for {0}: {1} active piece(s). Source/manual ownership counters were not returned by this unchanged-stage verification." -f
                        $deliveryDateText,
                        $activeQty
                    ) -Level "INFO"
                }
                $retainedSourceLineCount = [int](Get-OptionalProperty -Object $stageSummary -Name "retainedSourceLineCount" -DefaultValue 0)
                $retainedSourcePieceQty = [int](Get-OptionalProperty -Object $stageSummary -Name "retainedSourcePieceQty" -DefaultValue 0)
                if ($retainedSourceLineCount -gt 0) {
                    Write-AutomationLog -Message (
                        "Source-row removals are paused for {0}; retained {1} unverified source line(s) / {2} piece(s) until A+W schedule membership is confirmed." -f
                        $deliveryDateText,
                        $retainedSourceLineCount,
                        $retainedSourcePieceQty
                    ) -Level "WARN"
                }
            }
        }

        $successfulDateKeys = @($result.importedDates | ForEach-Object { [string]$_ })
        $failedDateKeys = @($result.failedDates | ForEach-Object { [string]$_ })

        foreach ($failedFile in @($result.files | Where-Object { [string]$_.classification -eq "failed" })) {
            $failedDate = [string](Get-OptionalProperty -Object $failedFile -Name "deliveryDate" -DefaultValue "unknown date")
            $failedName = [string](Get-OptionalProperty -Object $failedFile -Name "fileName" -DefaultValue "unknown workbook")
            $failedErrors = @((Get-OptionalProperty -Object $failedFile -Name "errors" -DefaultValue @()) | ForEach-Object { [string]$_ })
            $failedReason = [string](Get-OptionalProperty -Object $failedFile -Name "reason" -DefaultValue "")
            $failedMessage = if ($failedErrors.Count -gt 0) { $failedErrors -join " | " } elseif (-not [string]::IsNullOrWhiteSpace($failedReason)) { $failedReason } else { "No detailed error was returned." }
            Write-AutomationLog -Message ("Failed workbook {0} ({1}): {2}" -f $failedName, $failedDate, $failedMessage) -Level "WARN"
            if ($failedName -match '\.(xlsx|xlsm)$') {
                Write-AutomationLog -Message ("Repair guidance for {0}: on a SQL-authorized computer, run Sync A+W Directly for this delivery date to rebuild and republish the workbook before retrying Folder Import Only." -f $failedDate) -Level "WARN"
            }
        }
        if ([int]$result.failedFileCount -gt 0) {
            Write-AutomationLog -Message ("Saved the complete normalized import result to {0}" -f $lastImportResultPath) -Level "INFO"
        }
        elseif ($null -ne $pythonImportFailure -and [string]::IsNullOrWhiteSpace($candidateReviewWarning)) {
            throw $pythonImportFailure
        }

        foreach ($date in $targetDates) {
            $dateKey = $date.ToString("yyyy-MM-dd")
            if ($dateKey -notin $successfulDateKeys) {
                if ($dateKey -in $failedDateKeys) {
                    Write-AutomationLog -Message "Import or verification failed for delivery date $dateKey." -Level "WARN"
                }
                continue
            }

            $state = Read-DateState -Config $Config -Date $date
            if ($null -ne $state) {
                Write-DateState `
                    -Config $Config `
                    -Date $date `
                    -Hash ([string]$state.dataHash) `
                    -WorkbookPath ([string]$state.workbookPath) `
                    -WorkbookHash ([string](Get-OptionalProperty -Object $state -Name "workbookHash" -DefaultValue "")) `
                    -RowCount ([int]$state.rowCount) `
                    -PieceCount ([int]$state.pieceCount) `
                    -Imported $true
            }
            $script:ImportedDates.Add($date)
        }

        $remainingPending = @(
            $script:PendingImportDates | Where-Object {
                $_.ToString("yyyy-MM-dd") -notin $successfulDateKeys
            }
        )
        $script:PendingImportDates.Clear()
        foreach ($pendingDate in $remainingPending) {
            $script:PendingImportDates.Add($pendingDate)
        }

        $removedLineCount = [int](Get-OptionalProperty -Object $result -Name "removedLineCount" -DefaultValue 0)
        $removedPieceQty = [int](Get-OptionalProperty -Object $result -Name "removedPieceQty" -DefaultValue 0)
        $duplicateManualLineCount = [int](Get-OptionalProperty -Object $result -Name "duplicateManualLineCount" -DefaultValue 0)
        Write-AutomationLog -Message (
            "Scanner check completed: {0} new, {1} updated, {2} unchanged, {3} failed, {4} removed line(s) / {5} piece(s), {6} duplicate manual line(s) retired, and {7} recovered missing-list file(s)." -f
            [int]$result.newFileCount,
            [int]$result.updatedFileCount,
            [int]$result.noChangeFileCount,
            [int]$result.failedFileCount,
            $removedLineCount,
            $removedPieceQty,
            $duplicateManualLineCount,
            [int](Get-OptionalProperty -Object $result -Name "recoveredFileCount" -DefaultValue 0)
        )
    }
    finally {
        Write-AutomationDebug -Message "Removing scanner-import temporary request/result files."
        Remove-Item -LiteralPath $resultPath -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $syncRequestPath -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $directPayloadPath -Force -ErrorAction SilentlyContinue
    }
}

function Remove-OldAutomationFiles {
    param([Parameter(Mandatory = $true)]$Config)

    $cutoff = (Get-Date).AddDays(-[int]$Config.LogRetentionDays)
    $removedCount = 0
    Write-AutomationDebug -Message (
        "Retention cleanup scanning Logs/Staging/Failed for files older than {0:o}. RetentionDays={1}" -f
        $cutoff,
        [int]$Config.LogRetentionDays
    )
    foreach ($folderName in @("Logs", "Staging", "Failed")) {
        $folder = Join-Path $Config.WorkingRoot $folderName
        $staleFiles = @(Get-ChildItem -LiteralPath $folder -File -ErrorAction SilentlyContinue | Where-Object {
            $_.LastWriteTime -lt $cutoff
        })
        Write-AutomationDebug -Message ("Retention folder scan. Folder={0} StaleFiles={1}" -f $folder, [int]$staleFiles.Count)
        foreach ($staleFile in $staleFiles) {
            try {
                Remove-Item -LiteralPath $staleFile.FullName -Force -ErrorAction Stop
                $removedCount++
                Write-AutomationDebug -Message ("Retention removed file: {0}" -f $staleFile.FullName)
            }
            catch {
                Write-AutomationLog -Message ("Retention cleanup could not remove {0}: {1}" -f $staleFile.FullName, $_.Exception.Message) -Level "WARN"
            }
        }
    }
    Write-AutomationDebug -Message ("Retention cleanup finished. RemovedFiles={0}" -f $removedCount)
}

function Write-LastRunSummary {
    param(
        [Parameter(Mandatory = $true)]$Config,
        [Parameter(Mandatory = $true)][string]$RunMode,
        [Parameter(Mandatory = $true)][bool]$Succeeded,
        [string]$ErrorMessage = ""
    )

    $importResultSnapshot = @($script:ImportResults | ForEach-Object { $_ })
    $safetyDeferredDetailSnapshot = @($script:SafetyDeferredDetails | ForEach-Object { $_ })
    $affectedListIds = @(Get-AffectedImportListIds -ImportResults $importResultSnapshot)
    $summary = [ordered]@{
        version = "v121"
        requestId = [string]$RequestId
        runId = [string]$script:RunId
        runOrigin = $(if ([string]::IsNullOrWhiteSpace([string]$RequestId)) { "scheduled" } else { "manual" })
        startedAt = [string]$script:StartedAt
        mode = $RunMode
        requestedRunAction = [string]$RunAction
        runAction = $script:ResolvedAction
        dateFrom = [string]$DateFrom
        dateTo = [string]$DateTo
        succeeded = $Succeeded
        completedAt = (Get-Date).ToUniversalTime().ToString("o")
        checkedDates = @($script:CheckedDates | ForEach-Object { $_.ToString("yyyy-MM-dd") })
        sourceDates = @($script:SourceDates | ForEach-Object { $_.ToString("yyyy-MM-dd") })
        publishedDates = @($script:PublishedDates | ForEach-Object { $_.ToString("yyyy-MM-dd") })
        importedDates = @($script:ImportedDates | ForEach-Object { $_.ToString("yyyy-MM-dd") })
        pendingImportDates = @($script:PendingImportDates | ForEach-Object { $_.ToString("yyyy-MM-dd") })
        safetyDeferredDates = @($script:SafetyDeferredDates | ForEach-Object { $_.ToString("yyyy-MM-dd") })
        safetyDeferredDetails = $safetyDeferredDetailSnapshot
        importResults = $importResultSnapshot
        affectedListIds = $affectedListIds
        error = $ErrorMessage
        logPath = $script:LogPath
    }
    $path = if ([string]::IsNullOrWhiteSpace([string]$SummaryPath)) {
        Join-Path $Config.WorkingRoot "State\last-run.json"
    }
    else {
        [IO.Path]::GetFullPath([string]$SummaryPath)
    }
    $summaryFolder = Split-Path -Parent $path
    if (-not [string]::IsNullOrWhiteSpace($summaryFolder)) {
        [void](New-Item -ItemType Directory -Path $summaryFolder -Force)
    }
    $temporaryPath = "{0}.{1}.tmp" -f $path, [guid]::NewGuid().ToString("N")
    Write-AutomationDebug -Message (
        "Writing run summary. Path={0} Succeeded={1} CheckedDates={2} PublishedDates={3} ImportedDates={4} ImportResults={5}" -f
        $path,
        [bool]$Succeeded,
        [int]$script:CheckedDates.Count,
        [int]$script:PublishedDates.Count,
        [int]$script:ImportedDates.Count,
        [int]$importResultSnapshot.Count
    )
    try {
        $summary | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $temporaryPath -Encoding UTF8
        Move-Item -LiteralPath $temporaryPath -Destination $path -Force
    }
    finally {
        Remove-Item -LiteralPath $temporaryPath -Force -ErrorAction SilentlyContinue
    }

    # Keep one immutable summary per completed run. last-run.json/web-gui-summary.json
    # are intentionally overwritten, so they cannot serve as an accurate same-day
    # audit trail by themselves.
    try {
        $historyFolder = Join-Path $Config.WorkingRoot "State\RunHistory"
        [void](New-Item -ItemType Directory -Path $historyFolder -Force)
        $historyStamp = (Get-Date).ToUniversalTime().ToString("yyyyMMdd-HHmmssfff")
        $historyPath = Join-Path $historyFolder ("run-{0}-{1}.json" -f $historyStamp, [guid]::NewGuid().ToString("N"))
        $historyTemporaryPath = "{0}.tmp" -f $historyPath
        try {
            $summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $historyTemporaryPath -Encoding UTF8
            Move-Item -LiteralPath $historyTemporaryPath -Destination $historyPath -Force
            Write-AutomationDebug -Message ("Archived immutable run summary: {0}" -f $historyPath)
        }
        finally {
            Remove-Item -LiteralPath $historyTemporaryPath -Force -ErrorAction SilentlyContinue
        }
    }
    catch {
        Write-AutomationLog -Message ("Run history archive could not be written: {0}" -f $_.Exception.Message) -Level "WARN"
    }
}

$runSucceeded = $false
$runError = ""
try {
    # Establish the caller-provided log before any configuration or runtime work.
    # This guarantees that startup failures are visible instead of leaving the GUI
    # indefinitely at "Starting PowerShell automation runner..." with zero lines.
    if (-not [string]::IsNullOrWhiteSpace($LogPath)) {
        $requestedLogPath = [IO.Path]::GetFullPath($LogPath)
        $requestedLogFolder = Split-Path -Parent $requestedLogPath
        if (-not [string]::IsNullOrWhiteSpace($requestedLogFolder)) {
            [void](New-Item -ItemType Directory -Path $requestedLogFolder -Force)
        }
        if (-not (Test-Path -LiteralPath $requestedLogPath -PathType Leaf)) {
            [void](New-Item -ItemType File -Path $requestedLogPath -Force)
        }
        $script:LogPath = $requestedLogPath
    }
    Write-AutomationStep -Message "PowerShell automation runner accepted the request. Per-run log initialized."
    Write-AutomationDebug -Message (
        "Request context. RequestId={0} RunId={1} Mode={2} RequestedAction={3} DeliveryDate={4} DateFrom={5} DateTo={6} FailIfBusy={7}" -f
        [string]$RequestId,
        [string]$script:RunId,
        [string]$Mode,
        [string]$RunAction,
        [string]$DeliveryDate,
        [string]$DateFrom,
        [string]$DateTo,
        [bool]$FailIfBusy
    )
    Write-AutomationDebug -Message (
        "Runtime context. Machine={0} User={1} PID={2} PowerShell={3} ScriptRoot={4} CurrentDirectory={5} ConfigPath={6} LogPath={7} SummaryPath={8}" -f
        [Environment]::MachineName,
        [Environment]::UserName,
        $PID,
        $PSVersionTable.PSVersion.ToString(),
        $PSScriptRoot,
        (Get-Location).Path,
        [IO.Path]::GetFullPath($ConfigPath),
        [string]$script:LogPath,
        [string]$SummaryPath
    )

    Write-AutomationStep -Message "Reading and validating automation configuration."
    $script:Config = Read-AutomationConfig -Path $ConfigPath
    Write-AutomationDebug -Message (
        "Configuration loaded. Version={0} WorkingRoot={1} DestinationFolder={2} ProjectRoot={3} DatabaseServer={4} Database={5} AuthenticationMode={6} PythonPath={7}" -f
        [string](Get-OptionalProperty -Object $script:Config -Name "Version" -DefaultValue ""),
        [string]$script:Config.WorkingRoot,
        [string]$script:Config.DestinationFolder,
        [string](Get-OptionalProperty -Object $script:Config -Name "ProjectRoot" -DefaultValue ""),
        [string](Get-OptionalProperty -Object $script:Config.Database -Name "Server" -DefaultValue ""),
        [string](Get-OptionalProperty -Object $script:Config.Database -Name "Database" -DefaultValue ""),
        [string](Get-OptionalProperty -Object $script:Config.Database -Name "AuthenticationMode" -DefaultValue "configured connection settings"),
        [string](Get-OptionalProperty -Object $script:Config.Runtime -Name "PythonPath" -DefaultValue "python")
    )

    Write-AutomationStep -Message "Creating/verifying runtime working folders and log destination."
    Initialize-WorkingFolders -Config $script:Config
    Write-AutomationDebug -Message ("Working folders ready under {0}. ActiveLog={1}" -f [string]$script:Config.WorkingRoot, [string]$script:LogPath)

    Write-AutomationStep -Message "Loading persistent source exclusions, superseded approvals, and manual overrides."
    $script:VerifiedSourceExclusions = @(Read-VerifiedSourceExclusions -Config $script:Config)
    $script:VerifiedSourceOrderExclusions = @(Read-VerifiedSourceOrderExclusions -Config $script:Config)
    $script:VerifiedSourceManualOverrides = @(Read-VerifiedSourceManualOverrides -Config $script:Config)
    Write-AutomationLog -Message "Starting Delivery List SQL Exporter v121 in $Mode mode with action $RunAction."
    Write-AutomationLog -Message (
        "A+W production statuses are diagnostic only. Persistent scanner decisions loaded: {0} exact item exclusion(s), {1} approved superseded-order exclusion(s), and {2} manual source override(s)." -f
        [int]$script:VerifiedSourceExclusions.Count,
        [int]$script:VerifiedSourceOrderExclusions.Count,
        [int]$script:VerifiedSourceManualOverrides.Count
    )

    Write-AutomationStep -Message "Acquiring the single-run automation lock."
    if (-not (Acquire-AutomationLock -Config $script:Config -FailWhenBusy ([bool]$FailIfBusy))) {
        $runSucceeded = $true
        exit 0
    }
    Write-AutomationDebug -Message ("Automation lock acquired. LockFile={0}" -f (Join-Path $script:Config.WorkingRoot "State\run.lock"))

    if ($Mode -eq "RuntimeTest") {
        Write-AutomationStep -Message "Running automation runtime preflight checks."
        $automationConfig = Get-OptionalProperty -Object $script:Config -Name "Automation" -DefaultValue $null
        $configuredMode = [string](Get-OptionalProperty -Object $automationConfig -Name "Mode" -DefaultValue "sql-export-and-import")
        if ($configuredMode -in @("sql-export-only", "sql-export-and-import")) {
            Write-AutomationStep -Message "Testing A+W SQL connectivity and mapped source columns."
            Test-SqlRuntime -Config $script:Config
            $builderPath = Join-Path $PSScriptRoot "build_delivery_workbook.py"
            Write-AutomationStep -Message "Running the workbook builder self-test."
            Invoke-ConfiguredPython -Config $script:Config -Arguments @($builderPath, "--self-test")
        }
        else {
            Write-AutomationLog -Message "SQL connectivity test skipped because the configured mode is $configuredMode."
        }
        Write-AutomationStep -Message "Testing destination-folder write access."
        Test-DestinationWriteAccess -Config $script:Config
        $projectRoot = [string]$script:Config.ProjectRoot
        if (-not [string]::IsNullOrWhiteSpace($projectRoot)) {
            foreach ($requiredName in @("backend\config.py", "backend\store.py")) {
                $requiredPath = Join-Path $projectRoot $requiredName
                if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
                    throw "Required scanner file is missing: $requiredPath"
                }
            }
            $compatibilityPath = Join-Path $PSScriptRoot "validate_scanner_compatibility.py"
            Write-AutomationStep -Message "Validating scanner/backend compatibility."
            Invoke-ConfiguredPython -Config $script:Config -Arguments @(
                $compatibilityPath,
                "--project-root", $projectRoot
            )
        }
        Write-AutomationStep -Message "Runtime preflight completed successfully."
        Write-AutomationLog -Message "Runtime test passed."
        $runSucceeded = $true
        exit 0
    }

    $resolvedAction = $RunAction
    if ($resolvedAction -eq "Configured") {
        $automationConfig = Get-OptionalProperty -Object $script:Config -Name "Automation" -DefaultValue $null
        $configuredMode = [string](Get-OptionalProperty -Object $automationConfig -Name "Mode" -DefaultValue "sql-export-and-import")
        $resolvedAction = switch ($configuredMode) {
            "sql-export-only" { "SqlExportOnly" }
            "folder-import-only" { "FolderImportOnly" }
            "disabled" { "Disabled" }
            default { "SqlExportAndImport" }
        }
    }
    $script:ResolvedAction = $resolvedAction
    Write-AutomationStep -Message ("Resolved updater action to {0}." -f $resolvedAction)
    Write-AutomationDebug -Message ("RequestedAction={0} ResolvedAction={1}" -f [string]$RunAction, [string]$resolvedAction)

    if ($resolvedAction -eq "Disabled") {
        Write-AutomationLog -Message "Configured automation mode is disabled. No files were queried or imported." -Level "WARN"
        Publish-AutomationNotification -Config $script:Config -RunMode $Mode -Succeeded $true
        $runSucceeded = $true
        exit 0
    }

    if ($resolvedAction -eq "RejectSyncOnly") {
        Write-AutomationStep -Message "Querying A+W breakage history only; delivery-list export/import is skipped."
        $script:AwRejectSyncPayload = Get-AwRejectSyncPayload -Config $script:Config -RunMode $Mode -ForceEnabled $true
        Write-AutomationStep -Message "Synchronizing A+W breakage history into standard Internal Rejects."
        Invoke-ScannerImport -Config $script:Config -Dates @() -Force $true -SelectiveSqlSync $true -RejectOnly $true
        Write-AutomationStep -Message "A+W reject-only synchronization completed."
    }
    else {
    Write-AutomationStep -Message "Resolving the delivery-date window for this run."
    $dates = @(Get-DateRange -Config $script:Config -RunMode $Mode -RequestedDate $DeliveryDate -RequestedDateFrom $DateFrom -RequestedDateTo $DateTo)
    Write-AutomationDebug -Message ("Resolved {0} delivery date(s): {1}" -f [int]$dates.Count, (Get-AutomationDateListText -Dates $dates))

    if ($resolvedAction -eq "FolderImportOnly") {
        Write-AutomationStep -Message "Starting scanner folder verification/import without querying A+W SQL."
        Invoke-ScannerImport -Config $script:Config -Dates $dates -Force $true
    }
    else {
        foreach ($date in $dates) {
            $dateKey = $date.ToString("yyyy-MM-dd")
            Write-AutomationStep -Message ("Processing A+W export for delivery date {0}." -f $dateKey)
            $dateTimer = [System.Diagnostics.Stopwatch]::StartNew()
            Export-DeliveryDate -Config $script:Config -Date $date -RunMode $Mode
            $dateTimer.Stop()
            Write-AutomationDebug -Message ("Finished delivery date {0}. DurationMs={1}" -f $dateKey, [Math]::Round($dateTimer.Elapsed.TotalMilliseconds))
        }
        if ($resolvedAction -eq "SqlExportAndImport") {
            Write-AutomationStep -Message "Querying recent A+W breakage history for scanner reject synchronization."
            try {
                $script:AwRejectSyncPayload = Get-AwRejectSyncPayload -Config $script:Config -RunMode $Mode -ForceEnabled (-not [string]::IsNullOrWhiteSpace([string]$RequestId))
            }
            catch {
                $script:AwRejectSyncPayload = $null
                $script:AwRejectSyncResult = [ordered]@{
                    ok = $false
                    sourceRows = 0
                    logicalEvents = 0
                    error = $_.Exception.Message
                }
                Write-AutomationLog -Message (
                    "A+W reject synchronization query failed and was skipped; delivery-list reconciliation will continue: {0}" -f
                    $_.Exception.Message
                ) -Level "WARN"
            }
            Write-AutomationStep -Message "Querying A+W production batch/optimization state for Cutting progress."
            try {
                $script:AwCuttingSyncPayload = Get-AwCuttingSyncPayload -Config $script:Config -DirectPayloads $script:DirectImportPayloads -ForceEnabled (-not [string]::IsNullOrWhiteSpace([string]$RequestId))
            }
            catch {
                $script:AwCuttingSyncPayload = $null
                $script:AwCuttingSyncResult = [ordered]@{ ok = $false; sourceRows = 0; generations = 0; error = $_.Exception.Message }
                Write-AutomationLog -Message (
                    "A+W Cutting synchronization query failed and was skipped; delivery-list reconciliation will continue: {0}" -f $_.Exception.Message
                ) -Level "WARN"
            }
            Write-AutomationStep -Message "Preparing direct scanner reconciliation for queried A+W delivery dates."
            $sourceDates = @($script:SourceDates | Sort-Object -Unique)
            # v0.502: manual Sync A+W Directly still queries every requested date and
            # the Python verifier compares every direct payload against the live scanner.
            # Do not force-write every date merely because the operator clicked Run.
            # That old behavior could rewrite 15-20 already synchronized dates and make
            # a healthy manual refresh run for many minutes. Changed exports are still
            # forced, and scanner_stage_drift independently catches database drift even
            # when the source hash itself did not change.
            $forceImportDates = @($script:PendingImportDates | Sort-Object -Unique)
            if ($Mode -eq "Custom") {
                Write-AutomationLog -Message (
                    "Manual update requested; all selected A+W dates will be verified, while only changed/drifted dates will be rewritten. SourceChangedDates={0}." -f
                    [int]$forceImportDates.Count
                )
            }
            if ($sourceDates.Count -gt 0) {
                Write-AutomationDebug -Message (
                    "Scanner reconciliation dates. SourceDates=[{0}] ForceImportDates=[{1}]" -f
                    (Get-AutomationDateListText -Dates $sourceDates),
                    (Get-AutomationDateListText -Dates $forceImportDates)
                )
                Write-AutomationStep -Message "Running scanner verification/import for the selected SQL dates. Direct A+W payload transport is enabled when available."
                Invoke-ScannerImport `
                    -Config $script:Config `
                    -Dates $sourceDates `
                    -ForceDates $forceImportDates `
                    -Force $true `
                    -SelectiveSqlSync $true
            }
            elseif ($null -ne $script:AwRejectSyncPayload -or $null -ne $script:AwCuttingSyncPayload) {
                # Reject synchronization is independent of delivery-list drift. A
                # quiet delivery window must not strand a successfully queried
                # PROD_BREAKAGE payload before it reaches the scanner database.
                # Historical log wording retained as a searchable compatibility marker:
                # No delivery rows require reconciliation; synchronizing the A+W reject payload independently.
                Write-AutomationStep -Message "No delivery rows require reconciliation; synchronizing available A+W reject/production payloads independently."
                Invoke-ScannerImport -Config $script:Config -Dates @() -Force $true -SelectiveSqlSync $true -RejectOnly $true
            }
            elseif ($script:SafetyDeferredDates.Count -gt 0) {
                Write-AutomationLog -Message "No delivery dates were safe to import in this run. Existing workbooks and scanner data were preserved for all deferred dates." -Level "WARN"
            }
            else {
                Write-AutomationLog -Message "No A+W delivery rows, reject payloads, or production payloads were found for scanner reconciliation."
            }
        }
        else {
            Write-AutomationLog -Message "SQL export-only action completed. Generated workbooks remain in the Temp Delivery Lists folder until imported."
        }
    }
    }
    Write-AutomationStep -Message "Applying automation retention cleanup."
    Remove-OldAutomationFiles -Config $script:Config
    $completedFailureCount = @($script:ImportResults | Where-Object { [string]$_.classification -eq "failed" }).Count
    $safetyDeferredCount = [int]$script:SafetyDeferredDates.Count
    if ($completedFailureCount -gt 0) {
        Write-AutomationLog -Message ("Automation run completed with warnings: {0} workbook(s) failed. Review the detailed failure lines above." -f $completedFailureCount) -Level "WARN"
    }
    elseif ($safetyDeferredCount -gt 0) {
        Write-AutomationLog -Message (
            "Automation run completed with warnings: {0} delivery date(s) were deferred by a compatibility safety guard; all safe dates continued through export/import." -f
            $safetyDeferredCount
        ) -Level "WARN"
    }
    else {
        Write-AutomationLog -Message "Automation run completed successfully."
    }
    Write-AutomationStep -Message "Publishing the final in-app automation notification when configured."
    Publish-AutomationNotification -Config $script:Config -RunMode $Mode -Succeeded $true
    Write-AutomationStep -Message (
        "Run workflow finished. CheckedDates={0} SourceDates={1} PublishedDates={2} ImportedDates={3} ImportResults={4}." -f
        [int]$script:CheckedDates.Count,
        [int]$script:SourceDates.Count,
        [int]$script:PublishedDates.Count,
        [int]$script:ImportedDates.Count,
        [int]$script:ImportResults.Count
    )
    $runSucceeded = $true
}
catch {
    $runError = [string]$_.Exception.Message
    $runErrorDetail = ($_ | Out-String).Trim()
    if ([string]::IsNullOrWhiteSpace($runErrorDetail)) {
        $runErrorDetail = $runError
    }
    try {
        Write-AutomationStep -Message "Automation workflow failed; recording full exception details." -Level "ERROR"
        Write-AutomationLog -Message $runErrorDetail -Level "ERROR"
        if ($null -ne $script:Config) {
            $lastErrorPath = Join-Path $script:Config.WorkingRoot "State\last-error.txt"
            $runErrorDetail | Set-Content -LiteralPath $lastErrorPath -Encoding UTF8
        }
    }
    catch {
        Write-Host $runErrorDetail
    }
    if ($null -ne $script:Config) {
        try {
            Publish-AutomationNotification -Config $script:Config -RunMode $Mode -Succeeded $false -ErrorMessage $runError
        }
        catch {
            try {
                Write-AutomationLog -Message (
                    "The original automation error was preserved, but the failure notification could not be published: {0}" -f
                    $_.Exception.Message
                ) -Level "WARN"
            }
            catch {
            }
        }
    }
    exit 1
}
finally {
    if ($null -ne $script:Config -and -not $script:SkipSummary) {
        try {
            Write-AutomationStep -Message "Writing the final run summary and immutable history record."
            Write-LastRunSummary -Config $script:Config -RunMode $Mode -Succeeded $runSucceeded -ErrorMessage $runError
        }
        catch {
            try {
                Write-AutomationLog -Message ("Final run summary could not be written: {0}" -f $_.Exception.Message) -Level "ERROR"
            }
            catch {
            }
        }
    }
    try {
        if ($null -ne $script:LockStream) {
            Write-AutomationDebug -Message "Releasing the single-run automation lock."
        }
    }
    catch {
    }
    Release-AutomationLock
    try {
        $script:RunStopwatch.Stop()
        Write-AutomationLog -Message (
            "Automation runner exiting. Succeeded={0} TotalDurationMs={1} StepsLogged={2}" -f
            [bool]$runSucceeded,
            [Math]::Round($script:RunStopwatch.Elapsed.TotalMilliseconds),
            [int]$script:StepNumber
        ) -Level $(if ($runSucceeded) { "INFO" } else { "ERROR" })
    }
    catch {
    }
}
