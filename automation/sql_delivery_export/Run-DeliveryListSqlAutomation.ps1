[CmdletBinding()]
param(
    [ValidateSet("RuntimeTest", "Test", "Incremental", "Full", "Custom", "FolderImport")]
    [string]$Mode = "Incremental",

    [ValidateSet("Configured", "SqlExportOnly", "SqlExportAndImport", "FolderImportOnly")]
    [string]$RunAction = "Configured",

    [string]$DeliveryDate = "",

    [string]$DateFrom = "",

    [string]$DateTo = "",

    [string]$ConfigPath = (Join-Path $PSScriptRoot "sql-export.config.json")
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

    # Use one log per run so the Status & Logs page can display the complete
    # command without mixing it with earlier scheduled or manual runs.
    $runStamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $script:LogPath = Join-Path $Config.WorkingRoot ("Logs\sql-export-{0}-pid{1}.log" -f $runStamp, $PID)
    [void](New-Item -ItemType File -Path $script:LogPath -Force)
}

function Acquire-AutomationLock {
    param([Parameter(Mandatory = $true)]$Config)

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
        Write-AutomationLog -Message "Another SQL delivery-list automation run is already active. This run will exit." -Level "WARN"
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
    param([object[]]$ImportResults = @())

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
        ItemNumber = Quote-SqlIdentifier -Name ([string](Get-RequiredProperty -Object $itemColumns -Name "ItemNumber"))
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
    p.$($source.ItemNumber),
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
    LTRIM(RTRIM(ISNULL(h.$($source.Route), ''))) AS SourceRoute
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
    $rows = New-Object System.Collections.Generic.List[object]
    foreach ($row in $table.Rows) {
        $headerFlags = if ($row.RemakeFlags -eq [DBNull]::Value) { [int64]0 } else { [int64]$row.RemakeFlags }
        $isRemake = $remakeMask -gt 0 -and (($headerFlags -band $remakeMask) -eq $remakeMask)
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
            route = Resolve-SourceRoute -Mapping $mapping -RawRoute ([string]$row.SourceRoute)
        })
    }
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
    $publishedDates = @($script:PublishedDates | Sort-Object -Unique | ForEach-Object { $_.ToString("yyyy-MM-dd") })
    $importedDates = @($script:ImportedDates | Sort-Object -Unique | ForEach-Object { $_.ToString("yyyy-MM-dd") })
    $pendingDates = @($script:PendingImportDates | Sort-Object -Unique | ForEach-Object { $_.ToString("yyyy-MM-dd") })
    $createdBy = [string](Get-OptionalProperty -Object $notifications -Name "CreatedBy" -DefaultValue "sql-delivery-automation")

    if ($Succeeded) {
        $newFileCount = @($script:ImportResults | Where-Object { $_.classification -in @("new", "new_updated") }).Count
        $updatedFileCount = @($script:ImportResults | Where-Object { $_.classification -in @("updated", "new_updated") }).Count
        $noChangeFileCount = @($script:ImportResults | Where-Object { $_.classification -eq "no_changes" }).Count
        $failedFileCount = @($script:ImportResults | Where-Object { $_.classification -eq "failed" }).Count
        $hasImportChanges = $newFileCount -gt 0 -or $updatedFileCount -gt 0
        $hasChanges = $publishedDates.Count -gt 0 -or $hasImportChanges
        $notifyOnNoChanges = [bool](Get-OptionalProperty -Object $notifications -Name "NotifyOnNoChanges" -DefaultValue $true)
        if (-not $hasChanges -and -not $notifyOnNoChanges -and $failedFileCount -eq 0) {
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

    $affectedListIds = @(Get-AffectedImportListIds -ImportResults @($script:ImportResults))
    $payload = [ordered]@{
        source = "sql-delivery-automation"
        displayMode = "toast"
        target = "delivery-list-management"
        version = "v121"
        mode = $RunMode
        succeeded = $Succeeded
        checkedDates = $checkedDates
        publishedDates = $publishedDates
        importedDates = $importedDates
        pendingImportDates = $pendingDates
        importResults = @($script:ImportResults)
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
    if ($rows.Count -eq 0) {
        Write-AutomationLog -Message "No rows were returned for $dateKey. Any existing workbook is preserved." -Level "WARN"
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
    Write-AutomationLog -Message "$dateKey contains $orderCount orders, $($rows.Count) line items, $pieceCount pieces, and $remakeCount remake lines."
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
            "--initialize-store", ([bool](Get-OptionalProperty -Object $Config.Import -Name "InitializeStore" -DefaultValue $true)).ToString().ToLowerInvariant(),
            "--result-path", $resultPath
        )
        if ($SelectiveSqlSync) {
            $syncRequest = [ordered]@{
                targetDates = @($targetDates | ForEach-Object { $_.ToString("yyyy-MM-dd") })
                forceImportDates = @($forcedDates | ForEach-Object { $_.ToString("yyyy-MM-dd") })
            }
            $syncRequest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $syncRequestPath -Encoding UTF8
            $arguments += @("--sync-request-path", $syncRequestPath)
        }

        [void](Invoke-ConfiguredPython -Config $Config -Arguments $arguments)

        Write-AutomationLog -Message "Scanner import verification returned. Reading the normalized result summary."
        if (-not (Test-Path -LiteralPath $resultPath -PathType Leaf)) {
            throw "Scanner import verification completed without producing its result summary."
        }
        $result = Get-Content -LiteralPath $resultPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $lastImportResultPath = Join-Path $Config.WorkingRoot "State\last-import-result.json"
        Copy-Item -LiteralPath $resultPath -Destination $lastImportResultPath -Force
        $script:ImportResults = @($script:ImportResults + @($result.files))
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

        Write-AutomationLog -Message (
            "Scanner check completed: {0} new, {1} updated, {2} unchanged, {3} failed, {4} recovered missing-list file(s)." -f
            [int]$result.newFileCount,
            [int]$result.updatedFileCount,
            [int]$result.noChangeFileCount,
            [int]$result.failedFileCount,
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

    $affectedListIds = @(Get-AffectedImportListIds -ImportResults @($script:ImportResults))
    $summary = [ordered]@{
        version = "v121"
        mode = $RunMode
        runAction = $script:ResolvedAction
        succeeded = $Succeeded
        completedAt = (Get-Date).ToUniversalTime().ToString("o")
        checkedDates = @($script:CheckedDates | ForEach-Object { $_.ToString("yyyy-MM-dd") })
        sourceDates = @($script:SourceDates | ForEach-Object { $_.ToString("yyyy-MM-dd") })
        publishedDates = @($script:PublishedDates | ForEach-Object { $_.ToString("yyyy-MM-dd") })
        importedDates = @($script:ImportedDates | ForEach-Object { $_.ToString("yyyy-MM-dd") })
        pendingImportDates = @($script:PendingImportDates | ForEach-Object { $_.ToString("yyyy-MM-dd") })
        importResults = @($script:ImportResults)
        affectedListIds = $affectedListIds
        error = $ErrorMessage
        logPath = $script:LogPath
    }
    $path = Join-Path $Config.WorkingRoot "State\last-run.json"
    $summary | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $path -Encoding UTF8
}

$runSucceeded = $false
$runError = ""
try {
    $script:Config = Read-AutomationConfig -Path $ConfigPath
    Initialize-WorkingFolders -Config $script:Config
    Write-AutomationLog -Message "Starting Delivery List SQL Exporter v121 in $Mode mode with action $RunAction."

    if (-not (Acquire-AutomationLock -Config $script:Config)) {
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
            foreach ($requiredName in @("scanner_config.py", "delivery_store.py")) {
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
            $forceImportDates = @($script:PendingImportDates | Sort-Object -Unique)
            if ($sourceDates.Count -gt 0) {
                Invoke-ScannerImport `
                    -Config $script:Config `
                    -Dates $sourceDates `
                    -ForceDates $forceImportDates `
                    -Force $true `
                    -SelectiveSqlSync $true
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
    if ($completedFailureCount -gt 0) {
        Write-AutomationLog -Message ("Automation run completed with warnings: {0} workbook(s) failed. Review the detailed failure lines above." -f $completedFailureCount) -Level "WARN"
    }
    else {
        Write-AutomationLog -Message "Automation run completed successfully."
    }
    Publish-AutomationNotification -Config $script:Config -RunMode $Mode -Succeeded $true
    $runSucceeded = $true
}
catch {
    $runError = $_.Exception.Message
    try {
        Write-AutomationLog -Message $runError -Level "ERROR"
    }
    catch {
        Write-Host $runError
    }
    if ($null -ne $script:Config) {
        Publish-AutomationNotification -Config $script:Config -RunMode $Mode -Succeeded $false -ErrorMessage $runError
    }
    exit 1
}
finally {
    if ($null -ne $script:Config) {
        try {
            Write-LastRunSummary -Config $script:Config -RunMode $Mode -Succeeded $runSucceeded -ErrorMessage $runError
        }
        catch {
        }
    }
    Release-AutomationLock
}
