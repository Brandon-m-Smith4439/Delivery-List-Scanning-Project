# File: automation/sql_delivery_export/Run-DeliveryListSqlAutomation.ps1
[CmdletBinding()]
param(
    [ValidateSet("RuntimeTest", "Test", "Incremental", "Full", "Custom", "FolderImport")]
    [string]$Mode = "Incremental",

    [ValidateSet("Configured", "SqlExportOnly", "SqlExportAndImport", "FolderImportOnly")]
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
$script:Config = $null
$script:LockStream = $null
$script:CheckedDates = New-Object System.Collections.Generic.List[datetime]
$script:SourceDates = New-Object System.Collections.Generic.List[datetime]
$script:PublishedDates = New-Object System.Collections.Generic.List[datetime]
$script:PendingImportDates = New-Object System.Collections.Generic.List[datetime]
$script:ImportedDates = New-Object System.Collections.Generic.List[datetime]
$script:ImportResults = @()
$script:ResolvedAction = $RunAction
$script:StartedAt = (Get-Date).ToUniversalTime().ToString("o")
$script:SkipSummary = $false
$script:LastRawDeliveryRowCount = 0
$script:LastRawRemakeLineCount = 0
$script:LastExcludedDeliveryRows = @()
$script:LastEligibilityRule = ""
$script:LastStatusDiagnosticSummary = ""
$script:VerifiedSourceExclusions = @()
$script:SupersededOrderCandidates = @()
# Retained in run summaries for backward compatibility with v0.243. v0.245 no
# longer defers dates by production status because those values are diagnostic.
$script:SafetyDeferredDates = New-Object System.Collections.Generic.List[datetime]
$script:SafetyDeferredDetails = New-Object System.Collections.Generic.List[object]

function Write-AutomationLog {
    param(
        [Parameter(Mandatory = $true)][string]$Message,
        [ValidateSet("INFO", "WARN", "ERROR")][string]$Level = "INFO"
    )

    $line = "{0} [{1}] {2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Level, $Message
    Write-Host $line
    if ($script:LogPath) {
        Add-Content -LiteralPath $script:LogPath -Value $line -Encoding UTF8
    }
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

function Get-DeliveryRows {
    param(
        [Parameter(Mandatory = $true)]$Config,
        [Parameter(Mandatory = $true)][datetime]$Date
    )

    $source = Get-SourceSqlParts -Config $Config
    $mapping = $source.Mapping
    $connection = New-SqlConnection -Config $Config
    $table = New-Object System.Data.DataTable
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
        if ($verifiedByKey.ContainsKey($orderItemKey)) {
            $verified = $verifiedByKey[$orderItemKey]
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

        $rows.Add([ordered]@{
            product = [string]$row.ProductHeading
            job = [string]$row.JobNumber
            order = [int64]$row.OrderNumber
            item = [int]$row.ItemNumber
            quantity = [decimal]$row.Quantity
            widthUnits = [decimal]$row.WidthUnits
            heightUnits = [decimal]$row.HeightUnits
            customer = [string]$row.Customer
            remake = if ($isRemake) { "RM" } else { "" }
            remakeFlags = $headerFlags
            route = Resolve-SourceRoute -Mapping $mapping -RawRoute ([string]$row.SourceRoute)
        })
    }

    $script:LastRawDeliveryRowCount = [int]$table.Rows.Count
    $script:LastRawRemakeLineCount = [int]$rawRemakeLineCount
    $script:LastExcludedDeliveryRows = @($excludedRows.ToArray())
    $script:LastEligibilityRule = "v0.245-raw-date-plus-approved-exclusions-1"
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
        workbookFormatVersion = "v115-ooxml-1"
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
    $commandOutput = @(& $pythonPath @allArguments 2>&1)
    $exitCode = $LASTEXITCODE
    foreach ($outputLine in $commandOutput) {
        Write-AutomationLog -Message ("Python: {0}" -f [string]$outputLine)
    }
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
        return
    }

    $notifications = Get-OptionalProperty -Object $Config -Name "Notifications" -DefaultValue $null
    if ($null -eq $notifications -or -not [bool](Get-OptionalProperty -Object $notifications -Name "Enabled" -DefaultValue $true)) {
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
        startedAt = [string]$script:StartedAt
        checkedDates = $checkedDates
        publishedDates = $publishedDates
        importedDates = $importedDates
        pendingImportDates = $pendingDates
        safetyDeferredDates = $deferredDates
        safetyDeferredDetails = $safetyDeferredDetailSnapshot
        importResults = $importResultSnapshot
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
    $fileName = [string]::Format([Globalization.CultureInfo]::InvariantCulture, [string]$Config.Report.OutputNameFormat, $Date)
    $destinationPath = Join-Path ([string]$Config.DestinationFolder) $fileName
    $state = Read-DateState -Config $Config -Date $Date

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
        $stateFormatVersion -eq "v115-ooxml-1" -and
        -not [string]::IsNullOrWhiteSpace($stateWorkbookHash) -and
        $currentWorkbookHash -eq $stateWorkbookHash
    )
    if ($RunMode -ne "Test" -and $stateHash -eq $dataHash -and $workbookIsCurrent) {
        Write-AutomationLog -Message "Unchanged: $fileName"
        if (-not $stateImported) {
            $script:PendingImportDates.Add($Date)
        }
        return
    }
    if ($RunMode -ne "Test" -and $stateHash -eq $dataHash -and -not $workbookIsCurrent) {
        Write-AutomationLog -Message "Existing workbook is missing the v115 integrity marker or does not match its recorded hash. Rebuilding $fileName." -Level "WARN"
    }

    $runToken = "{0}-{1}" -f $dateKey, [guid]::NewGuid().ToString("N")
    $jsonPath = Join-Path $Config.WorkingRoot ("Staging\$runToken.json")
    $xlsxPath = Join-Path $Config.WorkingRoot ("Staging\$runToken.xlsx")
    $builderPath = Join-Path $PSScriptRoot "build_delivery_workbook.py"
    $payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

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
        if ($length -lt [int]$Config.MinimumWorkbookBytes) {
            throw "Generated workbook is unexpectedly small: $length bytes"
        }
        Write-AutomationLog -Message "Validating generated workbook for $dateKey."
        [void](Invoke-ConfiguredPython -Config $Config -Arguments @($builderPath, "--validate", $xlsxPath))
        Publish-Workbook -SourcePath $xlsxPath -DestinationPath $destinationPath
        $publishedWorkbookHash = (Get-FileHash -LiteralPath $destinationPath -Algorithm SHA256).Hash.ToLowerInvariant()

        $sourceDataChanged = ($null -eq $state -or $stateHash -ne $dataHash)
        $nextImportedState = (-not $sourceDataChanged -and $stateImported)
        Write-DateState -Config $Config -Date $Date -Hash $dataHash -WorkbookPath $destinationPath -WorkbookHash $publishedWorkbookHash -RowCount $rows.Count -PieceCount $pieceCount -Imported $nextImportedState
        $script:PublishedDates.Add($Date)
        if ($sourceDataChanged -or -not $stateImported) {
            $script:PendingImportDates.Add($Date)
        }
        Write-AutomationLog -Message "Published $fileName with $($rows.Count) line items and $pieceCount pieces."
    }
    catch {
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
    }
}

function Invoke-ScannerImport {
    param(
        [Parameter(Mandatory = $true)]$Config,
        [Parameter(Mandatory = $false)][AllowEmptyCollection()][datetime[]]$Dates = @(),
        [Parameter(Mandatory = $false)][AllowEmptyCollection()][datetime[]]$ForceDates = @(),
        [bool]$Force = $false,
        [bool]$SelectiveSqlSync = $false
    )

    $importMode = [string](Get-OptionalProperty -Object $Config.Import -Name "Mode" -DefaultValue "disabled")
    if ($null -eq $Dates -or $Dates.Count -eq 0) {
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
    $importerPath = Join-Path $PSScriptRoot "import_delivery_folder.py"
    $dateFrom = ($targetDates | Select-Object -First 1).ToString("yyyy-MM-dd")
    $dateTo = ($targetDates | Select-Object -Last 1).ToString("yyyy-MM-dd")
    $resultPath = Join-Path $Config.WorkingRoot ("State\import-result-{0}.json" -f [guid]::NewGuid().ToString("N"))
    $syncRequestPath = Join-Path $Config.WorkingRoot ("State\import-sync-request-{0}.json" -f [guid]::NewGuid().ToString("N"))

    if ($SelectiveSqlSync) {
        Write-AutomationLog -Message "Verifying generated workbooks and scanner stage lists for $dateFrom through $dateTo"
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
            "--run-id", $(if ([string]::IsNullOrWhiteSpace([string]$RequestId)) { "scheduled-$($script:StartedAt)" } else { [string]$RequestId }),
            "--run-started-at", [string]$script:StartedAt,
            "--initialize-store", ([bool](Get-OptionalProperty -Object $Config.Import -Name "InitializeStore" -DefaultValue $true)).ToString().ToLowerInvariant(),
            "--result-path", $resultPath
        )
        if ($SelectiveSqlSync) {
            $syncRequest = [ordered]@{
                targetDates = @($targetDates | ForEach-Object { $_.ToString("yyyy-MM-dd") })
                forceImportDates = @($forcedDates | ForEach-Object { $_.ToString("yyyy-MM-dd") })
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
        $lastImportResultPath = Join-Path $Config.WorkingRoot "State\last-import-result.json"
        Copy-Item -LiteralPath $resultPath -Destination $lastImportResultPath -Force
        $script:ImportResults = @($script:ImportResults + @($result.files))
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
                Write-AutomationLog -Message ("Repair guidance for {0}: on a SQL-authorized computer, run Query SQL, Export & Import for this delivery date to rebuild and republish the workbook before retrying Folder Import Only." -f $failedDate) -Level "WARN"
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
        Remove-Item -LiteralPath $resultPath -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $syncRequestPath -Force -ErrorAction SilentlyContinue
    }
}

function Remove-OldAutomationFiles {
    param([Parameter(Mandatory = $true)]$Config)

    $cutoff = (Get-Date).AddDays(-[int]$Config.LogRetentionDays)
    foreach ($folderName in @("Logs", "Staging", "Failed")) {
        $folder = Join-Path $Config.WorkingRoot $folderName
        Get-ChildItem -LiteralPath $folder -File -ErrorAction SilentlyContinue | Where-Object {
            $_.LastWriteTime -lt $cutoff
        } | Remove-Item -Force -ErrorAction SilentlyContinue
    }
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
    try {
        $summary | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $temporaryPath -Encoding UTF8
        Move-Item -LiteralPath $temporaryPath -Destination $path -Force
    }
    finally {
        Remove-Item -LiteralPath $temporaryPath -Force -ErrorAction SilentlyContinue
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
        [void](New-Item -ItemType File -Path $requestedLogPath -Force)
        $script:LogPath = $requestedLogPath
    }
    Write-AutomationLog -Message "PowerShell automation runner accepted the request."

    $script:Config = Read-AutomationConfig -Path $ConfigPath
    Initialize-WorkingFolders -Config $script:Config
    $script:VerifiedSourceExclusions = @(Read-VerifiedSourceExclusions -Config $script:Config)
    Write-AutomationLog -Message "Starting Delivery List SQL Exporter v121 in $Mode mode with action $RunAction."
    Write-AutomationLog -Message (
        "A+W production statuses are diagnostic only. Automatic source-row removal is paused except for {0} exact Crystal-verified order/item exclusion(s)." -f
        [int]$script:VerifiedSourceExclusions.Count
    )

    if (-not (Acquire-AutomationLock -Config $script:Config -FailWhenBusy ([bool]$FailIfBusy))) {
        $runSucceeded = $true
        exit 0
    }

    if ($Mode -eq "RuntimeTest") {
        $automationConfig = Get-OptionalProperty -Object $script:Config -Name "Automation" -DefaultValue $null
        $configuredMode = [string](Get-OptionalProperty -Object $automationConfig -Name "Mode" -DefaultValue "sql-export-and-import")
        if ($configuredMode -in @("sql-export-only", "sql-export-and-import")) {
            Test-SqlRuntime -Config $script:Config
            $builderPath = Join-Path $PSScriptRoot "build_delivery_workbook.py"
            Invoke-ConfiguredPython -Config $script:Config -Arguments @($builderPath, "--self-test")
        }
        else {
            Write-AutomationLog -Message "SQL connectivity test skipped because the configured mode is $configuredMode."
        }
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
            Invoke-ConfiguredPython -Config $script:Config -Arguments @(
                $compatibilityPath,
                "--project-root", $projectRoot
            )
        }
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

    if ($resolvedAction -eq "Disabled") {
        Write-AutomationLog -Message "Configured automation mode is disabled. No files were queried or imported." -Level "WARN"
        Publish-AutomationNotification -Config $script:Config -RunMode $Mode -Succeeded $true
        $runSucceeded = $true
        exit 0
    }

    $dates = @(Get-DateRange -Config $script:Config -RunMode $Mode -RequestedDate $DeliveryDate -RequestedDateFrom $DateFrom -RequestedDateTo $DateTo)

    if ($resolvedAction -eq "FolderImportOnly") {
        Invoke-ScannerImport -Config $script:Config -Dates $dates -Force $true
    }
    else {
        foreach ($date in $dates) {
            Export-DeliveryDate -Config $script:Config -Date $date -RunMode $Mode
        }
        if ($resolvedAction -eq "SqlExportAndImport") {
            $sourceDates = @($script:SourceDates | Sort-Object -Unique)
            # A browser-started Custom run is an explicit operator request to reconcile
            # the scanner with A+W, even when the exported workbook hash is unchanged.
            # Scheduled runs may retain their incremental optimization because the Python
            # verifier also compares current scanner source rows with the workbook.
            if ($Mode -eq "Custom") {
                $forceImportDates = @($sourceDates)
                Write-AutomationLog -Message "Manual update requested; forcing authoritative scanner reconciliation for every selected delivery date."
            }
            else {
                $forceImportDates = @($script:PendingImportDates | Sort-Object -Unique)
            }
            if ($sourceDates.Count -gt 0) {
                Invoke-ScannerImport `
                    -Config $script:Config `
                    -Dates $sourceDates `
                    -ForceDates $forceImportDates `
                    -Force $true `
                    -SelectiveSqlSync $true
            }
            elseif ($script:SafetyDeferredDates.Count -gt 0) {
                Write-AutomationLog -Message "No delivery dates were safe to import in this run. Existing workbooks and scanner data were preserved for all deferred dates." -Level "WARN"
            }
            else {
                Write-AutomationLog -Message "No A+W delivery rows were found, so there are no generated workbooks to verify or import."
            }
        }
        else {
            Write-AutomationLog -Message "SQL export-only action completed. Generated workbooks remain in the Temp Delivery Lists folder until imported."
        }
    }
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
    Publish-AutomationNotification -Config $script:Config -RunMode $Mode -Succeeded $true
    $runSucceeded = $true
}
catch {
    $runError = [string]$_.Exception.Message
    $runErrorDetail = ($_ | Out-String).Trim()
    if ([string]::IsNullOrWhiteSpace($runErrorDetail)) {
        $runErrorDetail = $runError
    }
    try {
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
            Write-LastRunSummary -Config $script:Config -RunMode $Mode -Succeeded $runSucceeded -ErrorMessage $runError
        }
        catch {
        }
    }
    Release-AutomationLock
}
