# File: scripts/diagnostics/Probe-AWBdeBreakage.ps1
# Website version 4 diagnostic: discover A+W BDE/breakage booking storage safely.
[CmdletBinding()]
param(
    [string]$ConfigPath = "",
    [int]$StatusCode = 455,
    [string]$OrderNumber = "",
    [string]$ItemNumber = "",
    [string]$OutputFolder = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Resolve the project root after parameter binding. Windows PowerShell 5.1 can
# expose an empty $PSScriptRoot while default parameter expressions are being
# evaluated, so the probe deliberately avoids using it inside param(...).
if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
    $scriptFile = ""
    if (-not [string]::IsNullOrWhiteSpace($PSCommandPath)) {
        $scriptFile = $PSCommandPath
    }
    elseif ($null -ne $MyInvocation.MyCommand -and -not [string]::IsNullOrWhiteSpace([string]$MyInvocation.MyCommand.Path)) {
        $scriptFile = [string]$MyInvocation.MyCommand.Path
    }

    if (-not [string]::IsNullOrWhiteSpace($scriptFile)) {
        $scriptDirectory = Split-Path -Parent $scriptFile
        $projectRoot = Split-Path -Parent (Split-Path -Parent $scriptDirectory)
    }
    elseif (-not [string]::IsNullOrWhiteSpace($PSScriptRoot)) {
        $projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
    }
    else {
        # Final fallback for unusual hosts: the documented launch command runs
        # from the project root, so use the current location when no script path
        # metadata is available.
        $projectRoot = (Get-Location).Path
    }

    $ConfigPath = Join-Path $projectRoot "automation\sql_delivery_export\sql-export.config.json"
}

function Get-OptionalProperty {
    param(
        [Parameter(Mandatory = $true)]$Object,
        [Parameter(Mandatory = $true)][string]$Name,
        $DefaultValue = $null
    )
    if ($null -eq $Object -or -not ($Object.PSObject.Properties.Name -contains $Name)) {
        return $DefaultValue
    }
    return $Object.$Name
}

function Quote-SqlIdentifier {
    param([Parameter(Mandatory = $true)][string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) {
        throw "SQL identifier cannot be blank."
    }
    return "[" + $Value.Replace("]", "]]" ) + "]"
}

function New-ProbeConnection {
    param([Parameter(Mandatory = $true)]$Config)

    $database = $Config.Database
    $envName = [string](Get-OptionalProperty -Object $database -Name "ConnectionStringEnvironmentVariable" -DefaultValue "")
    if (-not [string]::IsNullOrWhiteSpace($envName)) {
        $configuredConnectionString = [Environment]::GetEnvironmentVariable($envName)
        if (-not [string]::IsNullOrWhiteSpace($configuredConnectionString)) {
            $builder = New-Object System.Data.SqlClient.SqlConnectionStringBuilder($configuredConnectionString)
            $builder["Application Name"] = "DeliveryScanner-AWBdeProbe-v483"
            return New-Object System.Data.SqlClient.SqlConnection($builder.ConnectionString)
        }
    }

    $builder = New-Object System.Data.SqlClient.SqlConnectionStringBuilder
    $builder["Data Source"] = [string]$database.Server
    $builder["Initial Catalog"] = [string]$database.Database
    $builder["Integrated Security"] = $true
    $builder["Connect Timeout"] = [int](Get-OptionalProperty -Object $database -Name "ConnectTimeoutSeconds" -DefaultValue 15)
    $builder["Encrypt"] = [bool](Get-OptionalProperty -Object $database -Name "Encrypt" -DefaultValue $false)
    $builder["TrustServerCertificate"] = [bool](Get-OptionalProperty -Object $database -Name "TrustServerCertificate" -DefaultValue $true)
    $builder["Application Name"] = "DeliveryScanner-AWBdeProbe-v483"
    return New-Object System.Data.SqlClient.SqlConnection($builder.ConnectionString)
}

function Invoke-ProbeQuery {
    param(
        [Parameter(Mandatory = $true)]$Connection,
        [Parameter(Mandatory = $true)][string]$Query,
        [hashtable]$Parameters = @{}
    )

    $command = $Connection.CreateCommand()
    $command.CommandTimeout = 120
    $command.CommandText = "SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;`r`n" + $Query
    foreach ($entry in $Parameters.GetEnumerator()) {
        $parameter = $command.Parameters.Add("@" + [string]$entry.Key, [System.Data.SqlDbType]::NVarChar, 256)
        $parameter.Value = [string]$entry.Value
    }
    $adapter = New-Object System.Data.SqlClient.SqlDataAdapter($command)
    $table = New-Object System.Data.DataTable
    try {
        [void]$adapter.Fill($table)
        # A DataTable is enumerable in Windows PowerShell. Without the unary
        # comma, function output is flattened into DataRow objects and callers
        # lose DataTable members such as .Rows. Return it as one pipeline object.
        return ,$table
    }
    finally {
        $adapter.Dispose()
        $command.Dispose()
    }
}

function Export-ProbeTable {
    param(
        [Parameter(Mandatory = $true)]$Table,
        [Parameter(Mandatory = $true)][string]$Path
    )
    if ($Table.Rows.Count -gt 0) {
        $Table | Export-Csv -LiteralPath $Path -NoTypeInformation -Encoding UTF8
    }
    else {
        "No rows returned." | Set-Content -LiteralPath $Path -Encoding UTF8
    }
}

function Get-CandidateScore {
    param(
        [Parameter(Mandatory = $true)][string]$ObjectName,
        [Parameter(Mandatory = $true)][string[]]$Columns
    )
    $objectUpper = $ObjectName.ToUpperInvariant()
    $columnText = ($Columns -join "|").ToUpperInvariant()
    $score = 0
    if ($objectUpper -match 'BDE|BUCH|BOOK|HIST|MELD|BRUCH|BREAK|REJECT|FEHL|ZUSTAND|STATUS') { $score += 8 }
    if ($columnText -match 'ZUSTAND|STATUS|BDE') { $score += 5 }
    if ($columnText -match 'AUFT|ORDER') { $score += 4 }
    if ($columnText -match 'POS|ITEM') { $score += 3 }
    if ($columnText -match 'GRUND|REASON|URSACH|CAUSE|FEHL|BRUCH|REJECT') { $score += 5 }
    if ($columnText -match 'DATUM|DATE|ZEIT|TIME|STAMP') { $score += 2 }
    if ($columnText -match 'PERSON|MITARB|USER|BEDIEN|EMPLOYEE') { $score += 2 }
    if ($columnText -match 'MASCH|MACHINE|STATION|ANLAGE|REG') { $score += 2 }
    if ($columnText -match 'ESNR|BARCODE|(^|_)BC($|_)|TEIL') { $score += 2 }
    return $score
}

function Select-OrderColumn {
    param([Parameter(Mandatory = $true)][string[]]$Columns)
    $patterns = @('^AUFNR$', '^AUFTNR$', '^AUFTR_NR$', '^AUFTRAG', '^ORDER_NO$', '^ORDERNR$', '^ORDER_', 'AUFNR', 'AUFT', 'ORDER')
    foreach ($pattern in $patterns) {
        $match = $Columns | Where-Object { $_ -match $pattern } | Select-Object -First 1
        if ($match) { return [string]$match }
    }
    return ""
}

function Select-ItemColumn {
    param([Parameter(Mandatory = $true)][string[]]$Columns)
    $patterns = @('^POS_NR$', '^POSNR$', '^ITEM_NO$', '^ITEMNR$', '^POSITION$', 'POS', 'ITEM')
    foreach ($pattern in $patterns) {
        $match = $Columns | Where-Object { $_ -match $pattern } | Select-Object -First 1
        if ($match) { return [string]$match }
    }
    return ""
}

function Select-StatusColumn {
    param([Parameter(Mandatory = $true)][string[]]$Columns)
    $patterns = @('^ZUSTANDNR$', '^ZUSTAND_NR$', '^STATUSNR$', '^STATUS_NR$', '^STATUS$', '^BOOK_TYPE$', 'ZUSTAND', 'STATUS', 'BDE', 'BOOK_TYPE')
    foreach ($pattern in $patterns) {
        $match = $Columns | Where-Object { $_ -match $pattern } | Select-Object -First 1
        if ($match) { return [string]$match }
    }
    return ""
}

if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
    throw "SQL automation configuration was not found: $ConfigPath"
}
$config = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
$schema = [string](Get-OptionalProperty -Object $config.SourceMapping -Name "Schema" -DefaultValue "SYSADM")
if ([string]::IsNullOrWhiteSpace($schema)) { $schema = "SYSADM" }

if ([string]::IsNullOrWhiteSpace($OrderNumber)) {
    $OrderNumber = (Read-Host "Known rejected A+W Order Nr. (optional; press Enter for metadata only)").Trim()
}
if (-not [string]::IsNullOrWhiteSpace($OrderNumber) -and [string]::IsNullOrWhiteSpace($ItemNumber)) {
    $ItemNumber = (Read-Host "Known rejected Item Nr. (optional; press Enter to search the whole order)").Trim()
}

if ([string]::IsNullOrWhiteSpace($OutputFolder)) {
    $desktop = [Environment]::GetFolderPath("Desktop")
    $OutputFolder = Join-Path $desktop ("AW-BDE-Breakage-Probe-{0}" -f (Get-Date -Format "yyyyMMdd-HHmmss"))
}
[void](New-Item -ItemType Directory -Path $OutputFolder -Force)

$connection = New-ProbeConnection -Config $config
$statusTable = $null
try {
    Write-Host "" 
    Write-Host "Opening SELECT-only A+W SQL diagnostic connection..." -ForegroundColor Cyan
    $connection.Open()
    Write-Host "Connected to $($connection.DataSource) / $($connection.Database)." -ForegroundColor Green

    $environmentTable = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT
    @@SERVERNAME AS ServerName,
    DB_NAME() AS DatabaseName,
    SUSER_SNAME() AS LoginName,
    GETDATE() AS DatabaseLocalTime,
    GETUTCDATE() AS DatabaseUtcTime;
"@
    Export-ProbeTable -Table $environmentTable -Path (Join-Path $OutputFolder "01-environment.csv")

    $statusMetadata = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT
    s.name AS SchemaName,
    o.name AS ObjectName,
    o.type_desc AS ObjectType,
    c.column_id AS ColumnOrder,
    c.name AS ColumnName,
    t.name AS DataType,
    c.max_length AS MaxLength,
    c.is_nullable AS IsNullable
FROM sys.objects o
INNER JOIN sys.schemas s ON s.schema_id = o.schema_id
INNER JOIN sys.columns c ON c.object_id = o.object_id
INNER JOIN sys.types t ON t.user_type_id = c.user_type_id
WHERE s.name = @SchemaName
  AND o.name = 'AWBAR_ZUSTAND'
ORDER BY c.column_id;
"@ -Parameters @{ SchemaName = $schema }
    Export-ProbeTable -Table $statusMetadata -Path (Join-Path $OutputFolder "02-awbar-zustand-columns.csv")

    if ($statusMetadata.Rows.Count -gt 0) {
        $statusColumns = @($statusMetadata.Rows | ForEach-Object { [string]$_.ColumnName })
        $statusCodeColumn = $statusColumns | Where-Object { $_ -ieq "Zustandnr" } | Select-Object -First 1
        if ($statusCodeColumn) {
            $statusObject = "{0}.{1}" -f (Quote-SqlIdentifier -Value $schema), (Quote-SqlIdentifier -Value "AWBAR_ZUSTAND")
            $quotedStatusColumn = Quote-SqlIdentifier -Value ([string]$statusCodeColumn)
            $statusTable = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT TOP (20) *
FROM $statusObject
WHERE LTRIM(RTRIM(CONVERT(nvarchar(128), $quotedStatusColumn))) = @StatusCode;
"@ -Parameters @{ StatusCode = [string]$StatusCode }
            Export-ProbeTable -Table $statusTable -Path (Join-Path $OutputFolder "03-status-$StatusCode.csv")
        }
        else {
            "AWBAR_ZUSTAND exists, but the documented Zustandnr column was not found. Review 02-awbar-zustand-columns.csv before extending the probe." |
                Set-Content -LiteralPath (Join-Path $OutputFolder "03-status-$StatusCode.csv") -Encoding UTF8
        }
    }
    else {
        "$schema.AWBAR_ZUSTAND was not found in this database/schema." |
            Set-Content -LiteralPath (Join-Path $OutputFolder "03-status-$StatusCode.csv") -Encoding UTF8
    }

    $metadata = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT
    s.name AS SchemaName,
    o.name AS ObjectName,
    o.type_desc AS ObjectType,
    c.column_id AS ColumnOrder,
    c.name AS ColumnName,
    t.name AS DataType,
    c.max_length AS MaxLength,
    c.is_nullable AS IsNullable
FROM sys.objects o
INNER JOIN sys.schemas s ON s.schema_id = o.schema_id
INNER JOIN sys.columns c ON c.object_id = o.object_id
INNER JOIN sys.types t ON t.user_type_id = c.user_type_id
WHERE s.name = @SchemaName
  AND o.type IN ('U', 'V')
  AND (
       UPPER(o.name) LIKE '%BDE%'
    OR UPPER(o.name) LIKE '%BUCH%'
    OR UPPER(o.name) LIKE '%BOOK%'
    OR UPPER(o.name) LIKE '%HIST%'
    OR UPPER(o.name) LIKE '%MELD%'
    OR UPPER(o.name) LIKE '%BRUCH%'
    OR UPPER(o.name) LIKE '%BREAK%'
    OR UPPER(o.name) LIKE '%REJECT%'
    OR UPPER(o.name) LIKE '%FEHL%'
    OR UPPER(o.name) LIKE '%ZUSTAND%'
    OR EXISTS (
        SELECT 1
        FROM sys.columns candidate_column
        WHERE candidate_column.object_id = o.object_id
          AND (
               UPPER(candidate_column.name) LIKE '%ZUSTAND%'
            OR UPPER(candidate_column.name) LIKE '%BDE%'
            OR UPPER(candidate_column.name) LIKE '%BUCH%'
            OR UPPER(candidate_column.name) LIKE '%MELD%'
            OR UPPER(candidate_column.name) LIKE '%BRUCH%'
            OR UPPER(candidate_column.name) LIKE '%REJECT%'
            OR UPPER(candidate_column.name) LIKE '%FEHL%'
            OR UPPER(candidate_column.name) LIKE '%GRUND%'
            OR UPPER(candidate_column.name) LIKE '%REASON%'
            OR UPPER(candidate_column.name) LIKE '%URSACH%'
          )
    )
  )
ORDER BY s.name, o.name, c.column_id;
"@ -Parameters @{ SchemaName = $schema }
    Export-ProbeTable -Table $metadata -Path (Join-Path $OutputFolder "04-bde-candidate-columns.csv")

    $candidateRows = New-Object System.Collections.Generic.List[object]
    $candidateGroups = @($metadata.Rows | Group-Object { "{0}.{1}" -f [string]$_.SchemaName, [string]$_.ObjectName })
    foreach ($group in $candidateGroups) {
        $first = $group.Group | Select-Object -First 1
        $columns = @($group.Group | Sort-Object ColumnOrder | ForEach-Object { [string]$_.ColumnName })
        $score = Get-CandidateScore -ObjectName ([string]$first.ObjectName) -Columns $columns
        if ($score -lt 8) { continue }
        $candidateRows.Add([pscustomobject]@{
            SchemaName = [string]$first.SchemaName
            ObjectName = [string]$first.ObjectName
            ObjectType = [string]$first.ObjectType
            Score = $score
            OrderColumn = Select-OrderColumn -Columns $columns
            ItemColumn = Select-ItemColumn -Columns $columns
            StatusColumn = Select-StatusColumn -Columns $columns
            Columns = ($columns -join ", ")
        })
    }
    $rankedCandidates = @($candidateRows | Sort-Object Score, ObjectName -Descending)
    if ($rankedCandidates.Count -gt 0) {
        $rankedCandidates | Export-Csv -LiteralPath (Join-Path $OutputFolder "05-ranked-bde-candidates.csv") -NoTypeInformation -Encoding UTF8
    }
    else {
        "No high-confidence BDE booking candidates were found by the metadata heuristic." |
            Set-Content -LiteralPath (Join-Path $OutputFolder "05-ranked-bde-candidates.csv") -Encoding UTF8
    }

    $sampleIndex = New-Object System.Collections.Generic.List[object]
    if (-not [string]::IsNullOrWhiteSpace($OrderNumber)) {
        $sampleNumber = 0
        foreach ($candidate in @($rankedCandidates | Select-Object -First 20)) {
            $orderColumn = [string]$candidate.OrderColumn
            if ([string]::IsNullOrWhiteSpace($orderColumn)) { continue }
            $sampleNumber++
            $schemaSql = Quote-SqlIdentifier -Value ([string]$candidate.SchemaName)
            $objectSql = Quote-SqlIdentifier -Value ([string]$candidate.ObjectName)
            $orderSql = Quote-SqlIdentifier -Value $orderColumn
            $itemColumn = [string]$candidate.ItemColumn
            $statusColumn = [string]$candidate.StatusColumn
            $itemClause = ""
            $statusClause = ""
            $parameters = @{ OrderNumber = $OrderNumber }
            if (-not [string]::IsNullOrWhiteSpace($ItemNumber) -and -not [string]::IsNullOrWhiteSpace($itemColumn)) {
                $itemSql = Quote-SqlIdentifier -Value $itemColumn
                $itemClause = "`r`n  AND LTRIM(RTRIM(CONVERT(nvarchar(128), $itemSql))) = @ItemNumber"
                $parameters.ItemNumber = $ItemNumber
            }
            if (-not [string]::IsNullOrWhiteSpace($statusColumn)) {
                $statusSql = Quote-SqlIdentifier -Value $statusColumn
                $statusClause = "`r`n  AND LTRIM(RTRIM(CONVERT(nvarchar(128), $statusSql))) = @StatusCode"
                $parameters.StatusCode = [string]$StatusCode
            }
            $safeObjectName = ([string]$candidate.ObjectName -replace '[^A-Za-z0-9_.-]+', '_')
            $fileName = "06-sample-{0:D2}-{1}.csv" -f $sampleNumber, $safeObjectName
            try {
                $sample = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT TOP (100) *
FROM $schemaSql.$objectSql
WHERE LTRIM(RTRIM(CONVERT(nvarchar(128), $orderSql))) = @OrderNumber$itemClause$statusClause
ORDER BY 1;
"@ -Parameters $parameters
                Export-ProbeTable -Table $sample -Path (Join-Path $OutputFolder $fileName)
                $sampleIndex.Add([pscustomobject]@{
                    ObjectName = "$($candidate.SchemaName).$($candidate.ObjectName)"
                    Score = [int]$candidate.Score
                    OrderColumn = $orderColumn
                    ItemColumn = $itemColumn
                    StatusColumn = $statusColumn
                    RowsReturned = [int]$sample.Rows.Count
                    OutputFile = $fileName
                    Error = ""
                })
                $sample.Dispose()
            }
            catch {
                $sampleIndex.Add([pscustomobject]@{
                    ObjectName = "$($candidate.SchemaName).$($candidate.ObjectName)"
                    Score = [int]$candidate.Score
                    OrderColumn = $orderColumn
                    ItemColumn = $itemColumn
                    StatusColumn = $statusColumn
                    RowsReturned = 0
                    OutputFile = $fileName
                    Error = $_.Exception.Message
                })
            }
        }
    }
    if ($sampleIndex.Count -gt 0) {
        $sampleIndex | Export-Csv -LiteralPath (Join-Path $OutputFolder "06-sample-index.csv") -NoTypeInformation -Encoding UTF8
    }
    else {
        "No known Order Nr. was supplied, or no candidate exposed a recognizable order column. Metadata discovery only." |
            Set-Content -LiteralPath (Join-Path $OutputFolder "06-sample-index.csv") -Encoding UTF8
    }

    # v0.483: live validation proved PROD_BREAKAGE and UV_BOOK_HISTORY_EX are the
    # reliable order/item reject sources for this BFSMAIN installation. Keep the
    # older objects visible for comparison, but never join FS_BOOK_HISTORY by BOM/
    # item alone: those identifiers are reused historically and caused false 2017
    # matches for a 2026 reject. Any booking-history correlation is time-bounded.
    if (-not [string]::IsNullOrWhiteSpace($OrderNumber)) {
        $schemaSql = Quote-SqlIdentifier -Value $schema
        $verifiedQueries = @(
            [pscustomobject]@{
                FileName = "07-fs-bruch-order-item.csv"
                Query = @"
SELECT TOP (200) *
FROM $schemaSql.[FS_BRUCH]
WHERE LTRIM(RTRIM(CONVERT(nvarchar(128), [AUFNR]))) = @OrderNumber
  AND (@ItemNumber = '' OR LTRIM(RTRIM(CONVERT(nvarchar(128), [POSNR]))) = @ItemNumber)
ORDER BY [DATUM], [POSNR], [BOMID];
"@
                Parameters = @{ OrderNumber = $OrderNumber; ItemNumber = $ItemNumber }
            },
            [pscustomobject]@{
                FileName = "08-prod-breakage-order-item.csv"
                Query = @"
SELECT TOP (200) *
FROM $schemaSql.[PROD_BREAKAGE]
WHERE LTRIM(RTRIM(CONVERT(nvarchar(128), [AUFNR]))) = @OrderNumber
  AND (@ItemNumber = '' OR LTRIM(RTRIM(CONVERT(nvarchar(128), [POSNR]))) = @ItemNumber)
ORDER BY [BREAKAGEDATE], [POSNR], [BOM_ID];
"@
                Parameters = @{ OrderNumber = $OrderNumber; ItemNumber = $ItemNumber }
            },
            [pscustomobject]@{
                FileName = "09-book-history-near-prod-breakage.csv"
                Query = @"
SELECT TOP (400)
    pb.[AUFNR] AS OrderNr,
    pb.[POSNR] AS ItemNr,
    pb.[BOM_ID] AS BomId,
    pb.[BREAKAGEDATE] AS BreakageDate,
    pb.[BREAKAGE_REASON] AS ProductionBreakageReason,
    pb.[BREAKAGE_REGISTRATION] AS ProductionBreakageRegistration,
    pb.[BREAKAGE_FROMSCANNER] AS BreakageFromScanner,
    bh.[ID] AS BookHistoryId,
    bh.[SUBPOS] AS BookSubPosition,
    bh.[MITARB_ID] AS EmployeeId,
    bh.[REG_POINT] AS RegistrationPoint,
    pp.[BEZ] AS RegistrationPointName,
    pp.[FREMD_KEY] AS RegistrationPointExternalKey,
    pp.[BDE_TYP] AS RegistrationPointBdeType,
    bh.[WORK_TYPE] AS WorkType,
    bh.[SCANTIME] AS ScanTime,
    DATEDIFF(second, pb.[BREAKAGEDATE], bh.[SCANTIME]) AS SecondsFromBreakage,
    bh.[AMOUNT] AS BookedAmount,
    bh.[ORIGIN] AS BookingOrigin,
    bh.[BOOK_TYPE] AS BookType,
    bh.[BREAKAGE_REASON] AS BookHistoryBreakageReason,
    bh.[BREAKAGE_CAUSER] AS BreakageCauser,
    bh.[BARCODE] AS Barcode,
    bh.[RACK] AS Rack
FROM $schemaSql.[PROD_BREAKAGE] pb
INNER JOIN $schemaSql.[FS_BOOK_HISTORY] bh
    ON bh.[BOMID] = pb.[BOM_ID]
   AND bh.[POSNR] = pb.[POSNR]
   AND bh.[SCANTIME] >= DATEADD(second, -10, pb.[BREAKAGEDATE])
   AND bh.[SCANTIME] <= DATEADD(second, 10, pb.[BREAKAGEDATE])
LEFT JOIN $schemaSql.[PD_PROD_POINT] pp
    ON pp.[NUMMER] = bh.[REG_POINT]
WHERE LTRIM(RTRIM(CONVERT(nvarchar(128), pb.[AUFNR]))) = @OrderNumber
  AND (@ItemNumber = '' OR LTRIM(RTRIM(CONVERT(nvarchar(128), pb.[POSNR]))) = @ItemNumber)
ORDER BY pb.[BREAKAGEDATE], bh.[SCANTIME], pb.[BOM_ID];
"@
                Parameters = @{ OrderNumber = $OrderNumber; ItemNumber = $ItemNumber }
            },
            [pscustomobject]@{
                FileName = "10-book-history-code-$StatusCode-near-prod-breakage.csv"
                Query = @"
SELECT TOP (400)
    pb.[AUFNR] AS OrderNr,
    pb.[POSNR] AS ItemNr,
    pb.[BOM_ID] AS BomId,
    pb.[BREAKAGEDATE] AS BreakageDate,
    bh.[ID] AS BookHistoryId,
    bh.[MITARB_ID] AS EmployeeId,
    bh.[REG_POINT] AS RegistrationPoint,
    pp.[BEZ] AS RegistrationPointName,
    bh.[WORK_TYPE] AS WorkType,
    bh.[SCANTIME] AS ScanTime,
    DATEDIFF(second, pb.[BREAKAGEDATE], bh.[SCANTIME]) AS SecondsFromBreakage,
    bh.[BOOK_TYPE] AS BookType,
    bh.[BREAKAGE_REASON] AS BreakageReason,
    bh.[BREAKAGE_CAUSER] AS BreakageCauser,
    bh.[BARCODE] AS Barcode,
    bh.[RACK] AS Rack
FROM $schemaSql.[PROD_BREAKAGE] pb
INNER JOIN $schemaSql.[FS_BOOK_HISTORY] bh
    ON bh.[BOMID] = pb.[BOM_ID]
   AND bh.[POSNR] = pb.[POSNR]
   AND bh.[SCANTIME] >= DATEADD(second, -10, pb.[BREAKAGEDATE])
   AND bh.[SCANTIME] <= DATEADD(second, 10, pb.[BREAKAGEDATE])
LEFT JOIN $schemaSql.[PD_PROD_POINT] pp
    ON pp.[NUMMER] = bh.[REG_POINT]
WHERE LTRIM(RTRIM(CONVERT(nvarchar(128), pb.[AUFNR]))) = @OrderNumber
  AND (@ItemNumber = '' OR LTRIM(RTRIM(CONVERT(nvarchar(128), pb.[POSNR]))) = @ItemNumber)
  AND LTRIM(RTRIM(CONVERT(nvarchar(128), bh.[BOOK_TYPE]))) = @StatusCode
ORDER BY bh.[SCANTIME], pb.[BOM_ID];
"@
                Parameters = @{ OrderNumber = $OrderNumber; ItemNumber = $ItemNumber; StatusCode = [string]$StatusCode }
            },
            [pscustomobject]@{
                FileName = "11-ka-prod-bruch-reason-for-order-item.csv"
                Query = @"
SELECT DISTINCT
    pb.[BREAKAGE_REASON] AS BreakageReasonCode,
    kb.[STATUS_ID] AS StatusId,
    kb.[REKLA_GRND] AS ReasonText,
    kb.[REKLA_ORT] AS LocationText,
    kb.[KZ_KOSTENLOS] AS NoChargeFlag,
    kb.[KZ_LOGISTIC] AS LogisticFlag,
    kb.[ROWID] AS ConfigRowId
FROM $schemaSql.[PROD_BREAKAGE] pb
LEFT JOIN $schemaSql.[KA_PROD_BRUCH] kb
    ON kb.[STATUS_ID] = pb.[BREAKAGE_REASON]
WHERE LTRIM(RTRIM(CONVERT(nvarchar(128), pb.[AUFNR]))) = @OrderNumber
  AND (@ItemNumber = '' OR LTRIM(RTRIM(CONVERT(nvarchar(128), pb.[POSNR]))) = @ItemNumber)
ORDER BY pb.[BREAKAGE_REASON], kb.[REKLA_GRND], kb.[REKLA_ORT];
"@
                Parameters = @{ OrderNumber = $OrderNumber; ItemNumber = $ItemNumber }
            },
            [pscustomobject]@{
                FileName = "12-uv-book-history-ex-order-item.csv"
                Query = @"
SELECT TOP (500) *
FROM $schemaSql.[UV_BOOK_HISTORY_EX]
WHERE LTRIM(RTRIM(CONVERT(nvarchar(128), [PEDIDO]))) = @OrderNumber
  AND (@ItemNumber = '' OR LTRIM(RTRIM(CONVERT(nvarchar(128), [POSICION]))) = @ItemNumber)
ORDER BY [FECHA_HORA_ESCANEO], [POSICION], [PARTE];
"@
                Parameters = @{ OrderNumber = $OrderNumber; ItemNumber = $ItemNumber }
            },
            [pscustomobject]@{
                FileName = "14-verified-reject-evidence.csv"
                Query = @"
SELECT DISTINCT TOP (200)
    pb.[ROWID] AS AandWBreakageRowId,
    pb.[AUFNR] AS OrderNr,
    pb.[POSNR] AS ItemNr,
    pb.[BOM_ID] AS BomId,
    pb.[MENGE] AS BreakageQuantity,
    pb.[BREAKAGEDATE] AS BreakageDate,
    pb.[JOBNUMBER_ORG] AS OriginalJobNumber,
    pb.[JOBNUMBER_NEW] AS ReplacementJobNumber,
    pb.[BREAKAGE_REASON] AS BreakageReasonCode,
    kb.[REKLA_GRND] AS BreakageReasonText,
    kb.[REKLA_ORT] AS BreakageLocationText,
    pb.[BREAKAGE_REGISTRATION] AS BreakageRegistrationCode,
    pb.[BREAKAGE_FROMSCANNER] AS BreakageFromScanner,
    pb.[LASTCHANGEUSER] AS BreakageUser,
    uv.[EMPLEADO] AS TimelineEmployee,
    uv.[ID_TIPO_TRABAJO] AS WorkTypeId,
    uv.[TIPO_TRABAJO] AS WorkType,
    uv.[ID_PUNTO_REG] AS RegistrationPointId,
    uv.[PUNTO_REGISTRO] AS RegistrationPoint,
    uv.[MAQUINA] AS Machine,
    uv.[ESCANEO] AS ScanMode,
    uv.[MENSAJE] AS BookingMessage,
    uv.[PARTE] AS PartNo,
    uv.[VIDRIO_PROCESADO] AS ProcessedGlass,
    uv.[PRODUCTO_PROCESO] AS ProcessProduct,
    uv.[PRODUCTO_FINAL] AS FinalProduct
FROM $schemaSql.[PROD_BREAKAGE] pb
LEFT JOIN $schemaSql.[KA_PROD_BRUCH] kb
    ON kb.[STATUS_ID] = pb.[BREAKAGE_REASON]
OUTER APPLY (
    SELECT TOP (1) uvx.*
    FROM $schemaSql.[UV_BOOK_HISTORY_EX] uvx
    WHERE uvx.[PEDIDO] = pb.[AUFNR]
      AND uvx.[POSICION] = pb.[POSNR]
      AND uvx.[MENSAJE] = 'Reject'
      AND uvx.[FECHA_HORA_ESCANEO] >= DATEADD(second, -1, pb.[BREAKAGEDATE])
      AND uvx.[FECHA_HORA_ESCANEO] <= DATEADD(second, 1, pb.[BREAKAGEDATE])
    ORDER BY
        CASE WHEN uvx.[PARTE] = pb.[BOM_ID] THEN 0 ELSE 1 END,
        CASE WHEN uvx.[ESCANEO] = 'Explicit' THEN 0 ELSE 1 END,
        uvx.[FECHA_HORA_ESCANEO],
        uvx.[MAQUINA]
) uv
WHERE LTRIM(RTRIM(CONVERT(nvarchar(128), pb.[AUFNR]))) = @OrderNumber
  AND (@ItemNumber = '' OR LTRIM(RTRIM(CONVERT(nvarchar(128), pb.[POSNR]))) = @ItemNumber)
  AND pb.[IS_BREAKAGE] = 1
ORDER BY pb.[BREAKAGEDATE], pb.[BOM_ID];
"@
                Parameters = @{ OrderNumber = $OrderNumber; ItemNumber = $ItemNumber }
            },
            [pscustomobject]@{
                FileName = "15-prod-breakage-code-summary.csv"
                Query = @"
SELECT TOP (200)
    [BREAKAGE_REASON] AS BreakageReasonCode,
    [BREAKAGE_REGISTRATION] AS BreakageRegistrationCode,
    [BREAKAGE_FROMSCANNER] AS BreakageFromScanner,
    COUNT(*) AS BreakageRows,
    MIN([BREAKAGEDATE]) AS FirstBreakageDate,
    MAX([BREAKAGEDATE]) AS LastBreakageDate
FROM $schemaSql.[PROD_BREAKAGE]
WHERE [IS_BREAKAGE] = 1
  AND [BREAKAGEDATE] >= DATEADD(day, -180, GETDATE())
GROUP BY [BREAKAGE_REASON], [BREAKAGE_REGISTRATION], [BREAKAGE_FROMSCANNER]
ORDER BY COUNT(*) DESC, [BREAKAGE_REASON], [BREAKAGE_REGISTRATION];
"@
                Parameters = @{}
            },
            [pscustomobject]@{
                FileName = "16-breakage-module-references.csv"
                Query = @"
SELECT TOP (200)
    s.[name] AS SchemaName,
    o.[name] AS ObjectName,
    o.[type_desc] AS ObjectType,
    CASE WHEN UPPER(m.[definition]) LIKE '%PROD_BREAKAGE%' THEN 1 ELSE 0 END AS ReferencesProdBreakage,
    CASE WHEN UPPER(m.[definition]) LIKE '%BREAKAGE_REASON%' THEN 1 ELSE 0 END AS ReferencesBreakageReason,
    CASE WHEN UPPER(m.[definition]) LIKE '%BREAKAGE_CAUSER%' THEN 1 ELSE 0 END AS ReferencesBreakageCauser,
    CASE WHEN UPPER(m.[definition]) LIKE '%BREAKAGE_REGISTRATION%' THEN 1 ELSE 0 END AS ReferencesBreakageRegistration,
    CASE WHEN UPPER(m.[definition]) LIKE '%FS_BOOK_HISTORY%' THEN 1 ELSE 0 END AS ReferencesBookHistory,
    CASE WHEN UPPER(m.[definition]) LIKE '%FS_BRUCH%' THEN 1 ELSE 0 END AS ReferencesFsBruch,
    LEFT(m.[definition], 8000) AS DefinitionPreview
FROM sys.sql_modules m
INNER JOIN sys.objects o ON o.[object_id] = m.[object_id]
INNER JOIN sys.schemas s ON s.[schema_id] = o.[schema_id]
WHERE UPPER(m.[definition]) LIKE '%PROD_BREAKAGE%'
   OR UPPER(m.[definition]) LIKE '%BREAKAGE_REASON%'
   OR UPPER(m.[definition]) LIKE '%BREAKAGE_CAUSER%'
   OR UPPER(m.[definition]) LIKE '%BREAKAGE_REGISTRATION%'
   OR UPPER(m.[definition]) LIKE '%FS_BOOK_HISTORY%'
   OR UPPER(m.[definition]) LIKE '%FS_BRUCH%'
ORDER BY s.[name], o.[name];
"@
                Parameters = @{}
            },
            [pscustomobject]@{
                FileName = "17-breakage-lookup-candidate-columns.csv"
                Query = @"
SELECT TOP (120)
    s.[name] AS SchemaName,
    o.[name] AS ObjectName,
    o.[type_desc] AS ObjectType,
    c.[name] AS CodeColumn,
    t.[name] AS CodeDataType,
    (
        SELECT COUNT(*)
        FROM sys.columns tc
        INNER JOIN sys.types tt ON tt.[user_type_id] = tc.[user_type_id]
        WHERE tc.[object_id] = o.[object_id]
          AND tt.[name] IN ('varchar','nvarchar','char','nchar')
          AND (
               UPPER(tc.[name]) LIKE '%BEZ%'
            OR UPPER(tc.[name]) LIKE '%NAME%'
            OR UPPER(tc.[name]) LIKE '%TEXT%'
            OR UPPER(tc.[name]) LIKE '%BESCH%'
            OR UPPER(tc.[name]) LIKE '%DESC%'
            OR UPPER(tc.[name]) LIKE '%GRUND%'
            OR UPPER(tc.[name]) LIKE '%REASON%'
            OR UPPER(tc.[name]) LIKE '%URSACH%'
            OR UPPER(tc.[name]) LIKE '%CAUSE%'
            OR UPPER(tc.[name]) LIKE '%ORT%'
          )
    ) AS LikelyTextColumnCount,
    CASE
        WHEN UPPER(o.[name]) LIKE '%BRUCH%' OR UPPER(o.[name]) LIKE '%BREAK%' THEN 20
        WHEN UPPER(o.[name]) LIKE '%REKL%' OR UPPER(o.[name]) LIKE '%REJECT%' THEN 15
        WHEN UPPER(o.[name]) LIKE '%GRUND%' OR UPPER(o.[name]) LIKE '%REASON%' OR UPPER(o.[name]) LIKE '%URSACH%' OR UPPER(o.[name]) LIKE '%CAUSE%' THEN 15
        ELSE 0
    END
    + CASE
        WHEN UPPER(c.[name]) LIKE '%BREAKAGE%' OR UPPER(c.[name]) LIKE '%BRUCH%' THEN 10
        WHEN UPPER(c.[name]) LIKE '%GRUND%' OR UPPER(c.[name]) LIKE '%REASON%' OR UPPER(c.[name]) LIKE '%URSACH%' OR UPPER(c.[name]) LIKE '%CAUSE%' THEN 8
        WHEN UPPER(c.[name]) LIKE '%REGISTR%' OR UPPER(c.[name]) LIKE '%STATUS%' THEN 5
        WHEN UPPER(c.[name]) IN ('ID','NUMMER','NR','CODE') THEN 2
        ELSE 0
      END AS CandidateScore
FROM sys.objects o
INNER JOIN sys.schemas s ON s.[schema_id] = o.[schema_id]
INNER JOIN sys.columns c ON c.[object_id] = o.[object_id]
INNER JOIN sys.types t ON t.[user_type_id] = c.[user_type_id]
WHERE o.[type] IN ('U','V')
  AND t.[name] IN ('int','smallint','tinyint','bigint')
  AND (
       UPPER(o.[name]) LIKE '%BRUCH%'
    OR UPPER(o.[name]) LIKE '%BREAK%'
    OR UPPER(o.[name]) LIKE '%REKL%'
    OR UPPER(o.[name]) LIKE '%REJECT%'
    OR UPPER(o.[name]) LIKE '%GRUND%'
    OR UPPER(o.[name]) LIKE '%REASON%'
    OR UPPER(o.[name]) LIKE '%URSACH%'
    OR UPPER(o.[name]) LIKE '%CAUSE%'
    OR UPPER(c.[name]) LIKE '%BREAKAGE%'
    OR UPPER(c.[name]) LIKE '%BRUCH%'
    OR UPPER(c.[name]) LIKE '%GRUND%'
    OR UPPER(c.[name]) LIKE '%REASON%'
    OR UPPER(c.[name]) LIKE '%URSACH%'
    OR UPPER(c.[name]) LIKE '%CAUSE%'
    OR UPPER(c.[name]) LIKE '%REGISTR%'
  )
ORDER BY CandidateScore DESC, LikelyTextColumnCount DESC, s.[name], o.[name], c.[column_id];
"@
                Parameters = @{}
            },
            [pscustomobject]@{
                FileName = "19-reject-actor-candidates.csv"
                Query = @"
SELECT TOP (1200)
    pb.[ROWID] AS AandWBreakageRowId,
    pb.[AUFNR] AS OrderNr,
    pb.[POSNR] AS ItemNr,
    pb.[BOM_ID] AS BreakageBomId,
    pb.[BREAKAGEDATE] AS BreakageDate,
    pb.[BREAKAGE_REASON] AS ProductionReasonCode,
    pb.[BREAKAGE_REGISTRATION] AS ProductionLocationCode,
    pb.[LASTCHANGEUSER] AS SourceLastChangedUser,
    bh.[MITARB_ID] AS RejectBookingEmployee,
    bh.[BOMID] AS BookingBomId,
    bh.[WORK_TYPE] AS WorkType,
    bh.[REG_POINT] AS RegistrationPoint,
    bh.[SCANTIME] AS RejectBookingTime,
    DATEDIFF(second, pb.[BREAKAGEDATE], bh.[SCANTIME]) AS SecondsFromBreakage,
    bh.[ORIGIN] AS BookingOrigin,
    CASE WHEN bh.[ORIGIN] = 0 THEN 'Explicit' WHEN bh.[ORIGIN] = 2 THEN 'Implicit' ELSE '<INDF>' END AS ScanMode,
    bh.[BREAKAGE_REASON] AS BookingReasonCode,
    bh.[BREAKAGE_CAUSER] AS BookingLocationCode,
    CASE WHEN ISNULL(bh.[BREAKAGE_REASON], -1) = ISNULL(pb.[BREAKAGE_REASON], -2) THEN 1 ELSE 0 END AS ReasonCodeMatches,
    CASE WHEN ISNULL(bh.[BREAKAGE_CAUSER], -1) = ISNULL(pb.[BREAKAGE_REGISTRATION], -2) THEN 1 ELSE 0 END AS LocationCodeMatches,
    CASE WHEN bh.[BOMID] = pb.[BOM_ID] THEN 1 ELSE 0 END AS BomMatches
FROM $schemaSql.[PROD_BREAKAGE] pb
INNER JOIN $schemaSql.[FS_BOOK_HISTORY] bh
    ON bh.[ID] = pb.[AUFNR]
   AND bh.[POSNR] = pb.[POSNR]
   AND bh.[BOOK_TYPE] = 1
   AND bh.[SCANTIME] >= DATEADD(second, -60, pb.[BREAKAGEDATE])
   AND bh.[SCANTIME] <= DATEADD(second, 60, pb.[BREAKAGEDATE])
WHERE LTRIM(RTRIM(CONVERT(nvarchar(128), pb.[AUFNR]))) = @OrderNumber
  AND (@ItemNumber = '' OR LTRIM(RTRIM(CONVERT(nvarchar(128), pb.[POSNR]))) = @ItemNumber)
  AND pb.[IS_BREAKAGE] = 1
ORDER BY
    pb.[BREAKAGEDATE], pb.[BOM_ID],
    CASE WHEN ISNULL(bh.[BREAKAGE_REASON], -1) = ISNULL(pb.[BREAKAGE_REASON], -2) THEN 0 ELSE 1 END,
    CASE WHEN ISNULL(bh.[BREAKAGE_CAUSER], -1) = ISNULL(pb.[BREAKAGE_REGISTRATION], -2) THEN 0 ELSE 1 END,
    CASE WHEN bh.[ORIGIN] = 0 THEN 0 ELSE 1 END,
    CASE WHEN bh.[BOMID] = pb.[BOM_ID] THEN 0 ELSE 1 END,
    ABS(DATEDIFF(second, pb.[BREAKAGEDATE], bh.[SCANTIME])),
    bh.[SCANTIME] DESC;
"@
                Parameters = @{ OrderNumber = $OrderNumber; ItemNumber = $ItemNumber }
            }

        )

        $verifiedIndex = New-Object System.Collections.Generic.List[object]
        foreach ($verified in $verifiedQueries) {
            try {
                $verifiedTable = Invoke-ProbeQuery -Connection $connection -Query ([string]$verified.Query) -Parameters $verified.Parameters
                Export-ProbeTable -Table $verifiedTable -Path (Join-Path $OutputFolder ([string]$verified.FileName))
                $verifiedIndex.Add([pscustomobject]@{
                    OutputFile = [string]$verified.FileName
                    RowsReturned = [int]$verifiedTable.Rows.Count
                    Error = ""
                })
                $verifiedTable.Dispose()
            }
            catch {
                $verifiedIndex.Add([pscustomobject]@{
                    OutputFile = [string]$verified.FileName
                    RowsReturned = 0
                    Error = $_.Exception.Message
                })
                ("Query failed: {0}" -f $_.Exception.Message) |
                    Set-Content -LiteralPath (Join-Path $OutputFolder ([string]$verified.FileName)) -Encoding UTF8
            }
        }
        $verifiedIndex | Export-Csv -LiteralPath (Join-Path $OutputFolder "13-verified-breakage-index.csv") -NoTypeInformation -Encoding UTF8

        # Probe candidate master/lookup tables for the two live codes observed on
        # the verified reject. This intentionally scans only metadata-ranked
        # breakage/reason/causer objects and remains SELECT-only.
        $lookupCandidateTable = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT TOP (120)
    s.[name] AS SchemaName,
    o.[name] AS ObjectName,
    c.[name] AS CodeColumn,
    t.[name] AS CodeDataType,
    CASE
        WHEN UPPER(o.[name]) LIKE '%BRUCH%' OR UPPER(o.[name]) LIKE '%BREAK%' THEN 20
        WHEN UPPER(o.[name]) LIKE '%REKL%' OR UPPER(o.[name]) LIKE '%REJECT%' THEN 15
        WHEN UPPER(o.[name]) LIKE '%GRUND%' OR UPPER(o.[name]) LIKE '%REASON%' OR UPPER(o.[name]) LIKE '%URSACH%' OR UPPER(o.[name]) LIKE '%CAUSE%' THEN 15
        ELSE 0
    END
    + CASE
        WHEN UPPER(c.[name]) LIKE '%BREAKAGE%' OR UPPER(c.[name]) LIKE '%BRUCH%' THEN 10
        WHEN UPPER(c.[name]) LIKE '%GRUND%' OR UPPER(c.[name]) LIKE '%REASON%' OR UPPER(c.[name]) LIKE '%URSACH%' OR UPPER(c.[name]) LIKE '%CAUSE%' THEN 8
        WHEN UPPER(c.[name]) LIKE '%REGISTR%' OR UPPER(c.[name]) LIKE '%STATUS%' THEN 5
        WHEN UPPER(c.[name]) IN ('ID','NUMMER','NR','CODE') THEN 2
        ELSE 0
      END AS CandidateScore
FROM sys.objects o
INNER JOIN sys.schemas s ON s.[schema_id] = o.[schema_id]
INNER JOIN sys.columns c ON c.[object_id] = o.[object_id]
INNER JOIN sys.types t ON t.[user_type_id] = c.[user_type_id]
WHERE o.[type] IN ('U','V')
  AND t.[name] IN ('int','smallint','tinyint','bigint')
  AND (
       UPPER(o.[name]) LIKE '%BRUCH%'
    OR UPPER(o.[name]) LIKE '%BREAK%'
    OR UPPER(o.[name]) LIKE '%REKL%'
    OR UPPER(o.[name]) LIKE '%REJECT%'
    OR UPPER(o.[name]) LIKE '%GRUND%'
    OR UPPER(o.[name]) LIKE '%REASON%'
    OR UPPER(o.[name]) LIKE '%URSACH%'
    OR UPPER(o.[name]) LIKE '%CAUSE%'
    OR UPPER(c.[name]) LIKE '%BREAKAGE%'
    OR UPPER(c.[name]) LIKE '%BRUCH%'
    OR UPPER(c.[name]) LIKE '%GRUND%'
    OR UPPER(c.[name]) LIKE '%REASON%'
    OR UPPER(c.[name]) LIKE '%URSACH%'
    OR UPPER(c.[name]) LIKE '%CAUSE%'
    OR UPPER(c.[name]) LIKE '%REGISTR%'
  )
ORDER BY CandidateScore DESC, s.[name], o.[name], c.[column_id];
"@
        $lookupHits = New-Object System.Collections.Generic.List[object]
        $seenLookupCandidates = @{}
        foreach ($candidateRow in $lookupCandidateTable.Rows) {
            $candidateKey = "{0}.{1}.{2}" -f $candidateRow.SchemaName, $candidateRow.ObjectName, $candidateRow.CodeColumn
            if ($seenLookupCandidates.ContainsKey($candidateKey)) { continue }
            $seenLookupCandidates[$candidateKey] = $true
            if ($seenLookupCandidates.Count -gt 60) { break }

            $candidateSchemaSql = Quote-SqlIdentifier -Value ([string]$candidateRow.SchemaName)
            $candidateObjectSql = Quote-SqlIdentifier -Value ([string]$candidateRow.ObjectName)
            $candidateCodeName = [string]$candidateRow.CodeColumn
            $candidateCodeSql = Quote-SqlIdentifier -Value $candidateCodeName
            try {
                $candidateHits = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT TOP (20) *
FROM $candidateSchemaSql.$candidateObjectSql
WHERE $candidateCodeSql IN (137, 5)
ORDER BY $candidateCodeSql;
"@
                foreach ($hitRow in $candidateHits.Rows) {
                    $parts = New-Object System.Collections.Generic.List[string]
                    foreach ($column in $candidateHits.Columns) {
                        $value = $hitRow[$column.ColumnName]
                        if ($value -eq [DBNull]::Value) { continue }
                        $text = ([string]$value).Trim()
                        if ([string]::IsNullOrWhiteSpace($text)) { continue }
                        $parts.Add(("{0}={1}" -f $column.ColumnName, $text))
                        if ($parts.Count -ge 30) { break }
                    }
                    $evidence = ($parts -join '; ')
                    if ($evidence.Length -gt 3000) { $evidence = $evidence.Substring(0, 3000) }
                    $lookupHits.Add([pscustomobject]@{
                        SchemaName = [string]$candidateRow.SchemaName
                        ObjectName = [string]$candidateRow.ObjectName
                        CodeColumn = $candidateCodeName
                        CandidateScore = [int]$candidateRow.CandidateScore
                        CodeValue = [string]$hitRow[$candidateCodeName]
                        RowEvidence = $evidence
                    })
                }
                $candidateHits.Dispose()
            }
            catch {
                $lookupHits.Add([pscustomobject]@{
                    SchemaName = [string]$candidateRow.SchemaName
                    ObjectName = [string]$candidateRow.ObjectName
                    CodeColumn = $candidateCodeName
                    CandidateScore = [int]$candidateRow.CandidateScore
                    CodeValue = ''
                    RowEvidence = 'Query failed: ' + $_.Exception.Message
                })
            }
        }
        $lookupCandidateTable.Dispose()
        if ($lookupHits.Count -gt 0) {
            $lookupHits | Export-Csv -LiteralPath (Join-Path $OutputFolder "18-breakage-code-lookup-hits.csv") -NoTypeInformation -Encoding UTF8
        }
        else {
            "No candidate lookup rows matched code 137 or code 5." | Set-Content -LiteralPath (Join-Path $OutputFolder "18-breakage-code-lookup-hits.csv") -Encoding UTF8
        }
    }

    $summary = @"
A+W BDE / Breakage Discovery Probe
Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Server: $($connection.DataSource)
Database: $($connection.Database)
Schema: $schema
Status code checked: $StatusCode
Known Order Nr.: $(if ([string]::IsNullOrWhiteSpace($OrderNumber)) { "not supplied" } else { $OrderNumber })
Known Item Nr.: $(if ([string]::IsNullOrWhiteSpace($ItemNumber)) { "not supplied" } else { $ItemNumber })
Ranked candidate objects: $($rankedCandidates.Count)

Purpose:
- Preserve the original status-$StatusCode checks as historical evidence, but do not treat that code as the reject identity when the live installation returns no matching rows.
- Treat PROD_BREAKAGE.IS_BREAKAGE = 1 as the verified persisted breakage signal and UV_BOOK_HISTORY_EX.MENSAJE = Reject as the verified production-timeline signal.
- Treat KA_PROD_BRUCH as a disproven reason lookup for this installation when STATUS_ID does not match the live reason code.
- Search SQL module definitions and metadata-ranked lookup/master objects for the human-readable meaning of live reason code 137 and causer/registration code 5.
- Correlate FS_BOOK_HISTORY only inside a tight time window around BREAKAGEDATE; BOM/item alone is not a safe historical key.

Safety:
- Every database operation in this script is SELECT-only.
- READ UNCOMMITTED is used to avoid taking production read locks where SQL Server permits it.
- The script creates files only in this output folder and never writes to A+W.

Next step:
For actor-attribution problems, review 19-reject-actor-candidates.csv first; it shows every BOOK_TYPE=1 booking within +/-60 seconds and the reason/location/explicit/BOM match signals used by production ranking. Review 14-verified-reject-evidence.csv next to confirm one best timeline row per BOM-level source record. Then review 16-breakage-module-references.csv, 17-breakage-lookup-candidate-columns.csv, and 18-breakage-code-lookup-hits.csv to resolve live reason code 137 and causer/registration code 5. The production integration should continue to key raw A+W breakage persistence from PROD_BREAKAGE.ROWID while grouping same-order/item/time BOM rows into one logical operator-facing reject event.
"@
    $summary | Set-Content -LiteralPath (Join-Path $OutputFolder "README.txt") -Encoding UTF8

    $environmentTable.Dispose()
    $statusMetadata.Dispose()
    if ($null -ne $statusTable) { $statusTable.Dispose() }
    $metadata.Dispose()

    Write-Host "" 
    Write-Host "BDE discovery probe completed." -ForegroundColor Green
    Write-Host "Results folder:" -ForegroundColor Cyan
    Write-Host $OutputFolder
}
catch {
    $errorPath = Join-Path $OutputFolder "PROBE-ERROR.txt"
    $_.Exception.ToString() | Set-Content -LiteralPath $errorPath -Encoding UTF8
    Write-Host "" 
    Write-Host "BDE PROBE FAILED" -ForegroundColor Red
    Write-Host $_.Exception.Message
    Write-Host "Details: $errorPath"
    exit 1
}
finally {
    if ($null -ne $connection) {
        if ($connection.State -ne [System.Data.ConnectionState]::Closed) {
            $connection.Close()
        }
        $connection.Dispose()
    }
}
