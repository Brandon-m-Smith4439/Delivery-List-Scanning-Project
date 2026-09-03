# File: scripts/diagnostics/Probe-AWGlassLabels.ps1
# Website version 4 diagnostic: discover optimization-generated A+W glass-label storage safely.
[CmdletBinding()]
param(
    [string]$ConfigPath = "",
    [string]$OrderNumber = "",
    [string]$ItemNumber = "",
    [string]$OptimizationNumber = "",
    [switch]$CaptureCuttingLabels,
    [switch]$CaptureCuttingLabelsScreen,
    [switch]$LocateCrystalReport,
    [string]$OutputFolder = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

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
        $projectRoot = (Get-Location).Path
    }
    $ConfigPath = Join-Path $projectRoot "automation\sql_delivery_export\sql-export.config.json"
}

function Get-OptionalProperty {
    param([Parameter(Mandatory = $true)]$Object, [Parameter(Mandatory = $true)][string]$Name, $DefaultValue = $null)
    if ($null -eq $Object -or -not ($Object.PSObject.Properties.Name -contains $Name)) { return $DefaultValue }
    return $Object.$Name
}

function Quote-SqlIdentifier {
    param([Parameter(Mandatory = $true)][string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) { throw "SQL identifier cannot be blank." }
    return "[" + $Value.Replace("]", "]]" ) + "]"
}

function New-ProbeConnection {
    param([Parameter(Mandatory = $true)]$Config)
    $database = $Config.Database
    $envName = [string](Get-OptionalProperty -Object $database -Name "ConnectionStringEnvironmentVariable" -DefaultValue "")
    if (-not [string]::IsNullOrWhiteSpace($envName)) {
        $configured = [Environment]::GetEnvironmentVariable($envName)
        if (-not [string]::IsNullOrWhiteSpace($configured)) {
            $builder = New-Object System.Data.SqlClient.SqlConnectionStringBuilder($configured)
            $builder["Application Name"] = "DeliveryScanner-AWGlassLabelProbe-v498"
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
    $builder["Application Name"] = "DeliveryScanner-AWGlassLabelProbe-v498"
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
        return ,$table
    }
    finally {
        $adapter.Dispose()
        $command.Dispose()
    }
}

function Export-ProbeTable {
    param([Parameter(Mandatory = $true)]$Table, [Parameter(Mandatory = $true)][string]$Path)
    if ($Table.Rows.Count -gt 0) { $Table | Export-Csv -LiteralPath $Path -NoTypeInformation -Encoding UTF8 }
    else { "No rows returned." | Set-Content -LiteralPath $Path -Encoding UTF8 }
}

function Export-ProbeObjects {
    param([object[]]$Rows, [Parameter(Mandatory = $true)][string]$Path)
    $materialized = @($Rows)
    if ($materialized.Count -gt 0) { $materialized | Export-Csv -LiteralPath $Path -NoTypeInformation -Encoding UTF8 }
    else { "No rows returned." | Set-Content -LiteralPath $Path -Encoding UTF8 }
}

function Get-LiveObjectColumnSet {
    param(
        [Parameter(Mandatory = $true)]$Connection,
        [Parameter(Mandatory = $true)][string]$SchemaName,
        [Parameter(Mandatory = $true)][string]$ObjectName
    )
    $table = Invoke-ProbeQuery -Connection $Connection -Query @"
SELECT c.name AS ColumnName
FROM sys.objects o
JOIN sys.schemas s ON s.schema_id=o.schema_id
JOIN sys.columns c ON c.object_id=o.object_id
WHERE s.name=@SchemaName AND o.name=@ObjectName
ORDER BY c.column_id;
"@ -Parameters @{ SchemaName=$SchemaName; ObjectName=$ObjectName }
    $set = @{}
    foreach ($row in $table.Rows) {
        $columnName = ([string]$row.ColumnName).ToUpperInvariant()
        $set[$columnName] = $true
    }
    return $set
}

function Get-OptionalColumnSelectSql {
    param(
        [Parameter(Mandatory = $true)][hashtable]$ColumnSet,
        [Parameter(Mandatory = $true)][string]$TableAlias,
        [Parameter(Mandatory = $true)][string]$ColumnName,
        [Parameter(Mandatory = $true)][string]$OutputAlias,
        [string]$FallbackSql = 'CAST(NULL AS nvarchar(4000))'
    )
    if ($ColumnSet.ContainsKey($ColumnName.ToUpperInvariant())) {
        return ("{0}.{1} AS {2}" -f $TableAlias, (Quote-SqlIdentifier $ColumnName), (Quote-SqlIdentifier $OutputAlias))
    }
    return ("{0} AS {1}" -f $FallbackSql, (Quote-SqlIdentifier $OutputAlias))
}

function Get-CuttingLabelPreviewTempFiles {
    param([Parameter(Mandatory = $true)][datetime]$Since)
    $roots = New-Object System.Collections.Generic.List[string]
    foreach ($candidate in @($env:TEMP, $(if ($env:LOCALAPPDATA) { Join-Path $env:LOCALAPPDATA 'Temp' } else { '' }))) {
        if (-not [string]::IsNullOrWhiteSpace([string]$candidate) -and (Test-Path -LiteralPath $candidate)) {
            if (-not $roots.Contains([string]$candidate)) { $roots.Add([string]$candidate) }
        }
    }
    $rows = New-Object System.Collections.Generic.List[object]
    foreach ($root in $roots) {
        try {
            $recent = Get-ChildItem -LiteralPath $root -File -Recurse -ErrorAction SilentlyContinue |
                Where-Object { $_.LastWriteTime -ge $Since.AddSeconds(-2) } |
                Sort-Object LastWriteTime -Descending |
                Select-Object -First 500
            foreach ($file in $recent) {
                $rows.Add([pscustomobject]@{
                    Root = $root
                    FullName = $file.FullName
                    Extension = $file.Extension
                    Length = $file.Length
                    CreationTime = $file.CreationTime
                    LastWriteTime = $file.LastWriteTime
                })
            }
        }
        catch {
            $rows.Add([pscustomobject]@{
                Root = $root
                FullName = '<scan-error>'
                Extension = ''
                Length = 0
                CreationTime = $null
                LastWriteTime = $null
            })
        }
    }
    return $rows.ToArray()
}

function Get-AwBusinessProProcesses {
    $rows = New-Object System.Collections.Generic.List[object]
    foreach ($process in (Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like '*A+W*' -or $_.ProcessName -match 'A.?W|Albat' })) {
        $path = ''
        $startTime = $null
        try { $path = [string]$process.Path } catch { $path = '' }
        try { $startTime = $process.StartTime } catch { $startTime = $null }
        $rows.Add([pscustomobject]@{
            Id = $process.Id
            ProcessName = $process.ProcessName
            MainWindowTitle = $process.MainWindowTitle
            Path = $path
            StartTime = $startTime
        })
    }
    return $rows.ToArray()
}

function Select-OrderColumn {
    param([Parameter(Mandatory = $true)][string[]]$Columns)
    $patterns = @('^AUFNR$', '^AUFTNR$', '^AUFTR_NR$', '^AUFTRAG$', '^ORDER_NO$', '^ORDERNR$', '^ORDER_REF$', '^PEDIDO$', '^ID$')
    foreach ($pattern in $patterns) {
        $match = $Columns | Where-Object { $_ -match $pattern } | Select-Object -First 1
        if ($match) { return [string]$match }
    }
    $match = $Columns | Where-Object { $_ -match 'AUFNR|AUFT|ORDER|PEDIDO' } | Select-Object -First 1
    return $(if ($match) { [string]$match } else { "" })
}

function Select-ItemColumn {
    param([Parameter(Mandatory = $true)][string[]]$Columns)
    $patterns = @('^POSNR$', '^POS_NR$', '^ITEM_NO$', '^ITEMNR$', '^POSITION$', '^POSICION$')
    foreach ($pattern in $patterns) {
        $match = $Columns | Where-Object { $_ -match $pattern } | Select-Object -First 1
        if ($match) { return [string]$match }
    }
    $match = $Columns | Where-Object { $_ -match 'POSNR|POS_NR|ITEM|POSITION|POSICION' } | Select-Object -First 1
    return $(if ($match) { [string]$match } else { "" })
}

function Get-LabelCandidateScore {
    param([string]$ObjectName, [string[]]$Columns)
    $objectUpper = $ObjectName.ToUpperInvariant()
    $columnText = ($Columns -join '|').ToUpperInvariant()
    $score = 0
    if ($objectUpper -match 'ETIK|LABEL|BARCODE') { $score += 14 }
    if ($objectUpper -match 'OPTI|OPTIM|BATCH|LOS|POOL|JOB|PROD') { $score += 7 }
    if ($columnText -match 'ETIK|LABEL') { $score += 12 }
    if ($columnText -match 'BARCODE|BCODE|EAN|CODE128') { $score += 9 }
    if ($columnText -match 'OPTI|OPTIM|BATCH|LOS|LAUF|POOL') { $score += 7 }
    if ($columnText -match 'AUFNR|AUFT|ORDER|PEDIDO') { $score += 4 }
    if ($columnText -match 'POSNR|POS_NR|ITEM|POSITION|POSICION') { $score += 4 }
    if ($columnText -match 'TEXT|BEZ|DESC|NAME|ZPL|XML|DATA|PATH|FILE|DATEI|DRUCK|PRINT') { $score += 5 }
    if ($columnText -match 'BREITE|HOEHE|WIDTH|HEIGHT|GLAS|GLASS|PROD') { $score += 2 }
    return $score
}


function Find-ProbeTextHits {
    param(
        [Parameter(Mandatory = $true)]$Connection,
        [Parameter(Mandatory = $true)][string]$SchemaName,
        [Parameter(Mandatory = $true)][string]$ObjectName,
        [Parameter(Mandatory = $true)][string[]]$Needles
    )

    $columns = Invoke-ProbeQuery -Connection $Connection -Query @"
SELECT c.name AS ColumnName, t.name AS DataType
FROM sys.objects o
JOIN sys.schemas s ON s.schema_id=o.schema_id
JOIN sys.columns c ON c.object_id=o.object_id
JOIN sys.types t ON t.user_type_id=c.user_type_id
WHERE s.name=@SchemaName AND o.name=@ObjectName AND o.type IN ('U','V')
  AND t.name IN ('varchar','nvarchar','char','nchar','text','ntext','xml');
"@ -Parameters @{ SchemaName=$SchemaName; ObjectName=$ObjectName }
    if ($columns.Rows.Count -eq 0) { return @() }

    $parameters = @{}
    $predicates = New-Object System.Collections.Generic.List[string]
    $needleIndex = 0
    foreach ($needle in $Needles) {
        if ([string]::IsNullOrWhiteSpace($needle)) { continue }
        $needleIndex++
        $parameterName = "Needle$needleIndex"
        $parameters[$parameterName] = "%$needle%"
        foreach ($column in $columns.Rows) {
            $columnName = [string]$column.ColumnName
            $predicates.Add("CONVERT(nvarchar(max), " + (Quote-SqlIdentifier $columnName) + ") LIKE @" + $parameterName)
        }
    }
    if ($predicates.Count -eq 0) { return @() }

    $query = "SELECT TOP (100) * FROM " + (Quote-SqlIdentifier $SchemaName) + "." + (Quote-SqlIdentifier $ObjectName) + " WHERE " + ($predicates -join " OR ") + ";"
    $rows = Invoke-ProbeQuery -Connection $Connection -Query $query -Parameters $parameters
    $hits = New-Object System.Collections.Generic.List[object]
    foreach ($row in $rows.Rows) {
        foreach ($column in $columns.Rows) {
            $columnName = [string]$column.ColumnName
            $value = [string]$row[$columnName]
            if ([string]::IsNullOrWhiteSpace($value)) { continue }
            foreach ($needle in $Needles) {
                if ([string]::IsNullOrWhiteSpace($needle)) { continue }
                if ($value.IndexOf($needle, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) {
                    $preview = $value
                    if ($preview.Length -gt 2000) { $preview = $preview.Substring(0,2000) }
                    $hits.Add([pscustomobject]@{
                        SchemaName=$SchemaName
                        ObjectName=$ObjectName
                        ColumnName=$columnName
                        MatchedText=$needle
                        ValuePreview=$preview
                    })
                }
            }
        }
    }
    return $hits.ToArray()
}

if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) { throw "SQL automation configuration was not found: $ConfigPath" }
$config = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
$schema = [string](Get-OptionalProperty -Object $config.SourceMapping -Name "Schema" -DefaultValue "SYSADM")
if ([string]::IsNullOrWhiteSpace($schema)) { $schema = "SYSADM" }

if ([string]::IsNullOrWhiteSpace($OrderNumber) -and [string]::IsNullOrWhiteSpace($OptimizationNumber)) {
    $OrderNumber = (Read-Host "Known optimized A+W Order Nr. (optional when Optimization Nr. is known)").Trim()
}
if (-not [string]::IsNullOrWhiteSpace($OrderNumber) -and [string]::IsNullOrWhiteSpace($ItemNumber)) {
    $ItemNumber = (Read-Host "Known optimized Item Nr. (optional; press Enter for the whole order)").Trim()
}
if ([string]::IsNullOrWhiteSpace($OptimizationNumber)) {
    $OptimizationNumber = (Read-Host "Optimization Nr. from Production Manager > Optimization Overview (recommended; e.g. 8359)").Trim()
}
if ([string]::IsNullOrWhiteSpace($OutputFolder)) {
    $desktop = [Environment]::GetFolderPath("Desktop")
    $OutputFolder = Join-Path $desktop ("AW-Glass-Label-Probe-{0}" -f (Get-Date -Format "yyyyMMdd-HHmmss"))
}
[void](New-Item -ItemType Directory -Path $OutputFolder -Force)

$connection = New-ProbeConnection -Config $config
try {
    Write-Host ""
    Write-Host "Opening SELECT-only A+W glass-label diagnostic connection..." -ForegroundColor Cyan
    $connection.Open()
    Write-Host "Connected to $($connection.DataSource) / $($connection.Database)." -ForegroundColor Green

    $environment = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT @@SERVERNAME AS ServerName, DB_NAME() AS DatabaseName, SUSER_SNAME() AS LoginName,
       GETDATE() AS DatabaseLocalTime, GETUTCDATE() AS DatabaseUtcTime;
"@
    Export-ProbeTable -Table $environment -Path (Join-Path $OutputFolder "01-environment.csv")

    $metadata = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT s.name AS SchemaName, o.name AS ObjectName, o.type_desc AS ObjectType,
       c.column_id AS ColumnOrder, c.name AS ColumnName, t.name AS DataType, c.max_length AS MaxLength
FROM sys.objects o
JOIN sys.schemas s ON s.schema_id=o.schema_id
JOIN sys.columns c ON c.object_id=o.object_id
JOIN sys.types t ON t.user_type_id=c.user_type_id
WHERE s.name=@Schema
  AND o.type IN ('U','V')
  AND (
       UPPER(o.name) LIKE '%ETIK%' OR UPPER(o.name) LIKE '%LABEL%' OR UPPER(o.name) LIKE '%BARCODE%'
       OR UPPER(o.name) LIKE '%OPTI%' OR UPPER(o.name) LIKE '%POOL%' OR UPPER(o.name) LIKE '%JOB%'
       OR UPPER(c.name) LIKE '%ETIK%' OR UPPER(c.name) LIKE '%LABEL%' OR UPPER(c.name) LIKE '%BARCODE%'
       OR UPPER(c.name) LIKE '%OPTI%' OR UPPER(c.name) LIKE '%BATCH%' OR UPPER(c.name) LIKE '%LOS%'
       OR UPPER(c.name) LIKE '%DRUCK%' OR UPPER(c.name) LIKE '%PRINT%' OR UPPER(c.name) LIKE '%ZPL%'
  )
ORDER BY s.name, o.name, c.column_id;
"@ -Parameters @{ Schema = $schema }
    Export-ProbeTable -Table $metadata -Path (Join-Path $OutputFolder "02-label-candidate-columns.csv")

    $groups = @{}
    foreach ($row in $metadata.Rows) {
        $key = "{0}.{1}" -f [string]$row.SchemaName, [string]$row.ObjectName
        if (-not $groups.ContainsKey($key)) {
            $groups[$key] = [ordered]@{ SchemaName=[string]$row.SchemaName; ObjectName=[string]$row.ObjectName; ObjectType=[string]$row.ObjectType; Columns=New-Object System.Collections.Generic.List[string] }
        }
        $groups[$key].Columns.Add([string]$row.ColumnName)
    }
    $ranked = New-Object System.Collections.Generic.List[object]
    foreach ($entry in $groups.Values) {
        $columns = @($entry.Columns.ToArray())
        $ranked.Add([pscustomobject]@{
            SchemaName=$entry.SchemaName
            ObjectName=$entry.ObjectName
            ObjectType=$entry.ObjectType
            Score=(Get-LabelCandidateScore -ObjectName $entry.ObjectName -Columns $columns)
            OrderColumn=(Select-OrderColumn -Columns $columns)
            ItemColumn=(Select-ItemColumn -Columns $columns)
            Columns=($columns -join ', ')
        })
    }
    $rankedRows = @($ranked | Sort-Object @{Expression='Score';Descending=$true}, ObjectName)
    $rankedRows | Export-Csv -LiteralPath (Join-Path $OutputFolder "03-ranked-label-candidates.csv") -NoTypeInformation -Encoding UTF8

    $modules = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT TOP (200) s.name AS SchemaName, o.name AS ObjectName, o.type_desc AS ObjectType,
       CASE WHEN UPPER(m.definition) LIKE '%ETIK%' THEN 1 ELSE 0 END AS ReferencesEtik,
       CASE WHEN UPPER(m.definition) LIKE '%LABEL%' THEN 1 ELSE 0 END AS ReferencesLabel,
       CASE WHEN UPPER(m.definition) LIKE '%BARCODE%' THEN 1 ELSE 0 END AS ReferencesBarcode,
       CASE WHEN UPPER(m.definition) LIKE '%OPTI%' THEN 1 ELSE 0 END AS ReferencesOptimization,
       CASE WHEN UPPER(m.definition) LIKE '%PROD_JOBITEM%' THEN 1 ELSE 0 END AS ReferencesProdJobItem,
       CASE WHEN UPPER(m.definition) LIKE '%POOL_TEILE%' THEN 1 ELSE 0 END AS ReferencesPoolTeile,
       LEFT(REPLACE(REPLACE(m.definition, CHAR(13), ' '), CHAR(10), ' '), 8000) AS DefinitionPreview
FROM sys.sql_modules m
JOIN sys.objects o ON o.object_id=m.object_id
JOIN sys.schemas s ON s.schema_id=o.schema_id
WHERE s.name=@Schema AND (
    UPPER(m.definition) LIKE '%ETIK%' OR UPPER(m.definition) LIKE '%LABEL%'
    OR UPPER(m.definition) LIKE '%BARCODE%' OR UPPER(m.definition) LIKE '%OPTI%'
)
ORDER BY o.type_desc, o.name;
"@ -Parameters @{ Schema = $schema }
    Export-ProbeTable -Table $modules -Path (Join-Path $OutputFolder "04-label-module-references.csv")

    $sampleIndex = New-Object System.Collections.Generic.List[object]
    if (-not [string]::IsNullOrWhiteSpace($OrderNumber)) {
        $sampleNumber = 0
        foreach ($candidate in ($rankedRows | Where-Object { $_.OrderColumn -and $_.Score -ge 8 } | Select-Object -First 20)) {
            $sampleNumber++
            $schemaName = [string]$candidate.SchemaName
            $objectName = [string]$candidate.ObjectName
            $orderColumn = [string]$candidate.OrderColumn
            $itemColumn = [string]$candidate.ItemColumn
            $where = "CONVERT(nvarchar(256), " + (Quote-SqlIdentifier $orderColumn) + ") = @OrderNumber"
            $parameters = @{ OrderNumber = $OrderNumber }
            if (-not [string]::IsNullOrWhiteSpace($ItemNumber) -and -not [string]::IsNullOrWhiteSpace($itemColumn)) {
                $where += " AND CONVERT(nvarchar(256), " + (Quote-SqlIdentifier $itemColumn) + ") = @ItemNumber"
                $parameters.ItemNumber = $ItemNumber
            }
            $query = "SELECT TOP (150) * FROM " + (Quote-SqlIdentifier $schemaName) + "." + (Quote-SqlIdentifier $objectName) + " WHERE " + $where + ";"
            $safeName = ($objectName -replace '[^A-Za-z0-9_.-]', '_')
            $fileName = "05-sample-{0:D2}-{1}.csv" -f $sampleNumber, $safeName
            $errorText = ""
            $rowCount = 0
            try {
                $sample = Invoke-ProbeQuery -Connection $connection -Query $query -Parameters $parameters
                $rowCount = $sample.Rows.Count
                Export-ProbeTable -Table $sample -Path (Join-Path $OutputFolder $fileName)
            }
            catch {
                $errorText = $_.Exception.Message
                "Probe query failed: $errorText" | Set-Content -LiteralPath (Join-Path $OutputFolder $fileName) -Encoding UTF8
            }
            $sampleIndex.Add([pscustomobject]@{ ObjectName=("{0}.{1}" -f $schemaName,$objectName); Score=[int]$candidate.Score; OrderColumn=$orderColumn; ItemColumn=$itemColumn; RowsReturned=$rowCount; OutputFile=$fileName; Error=$errorText })
        }
    }
    if ($sampleIndex.Count -gt 0) { $sampleIndex | Export-Csv -LiteralPath (Join-Path $OutputFolder "06-sample-index.csv") -NoTypeInformation -Encoding UTF8 }
    else { "No order-specific samples were requested or no candidate exposed an order column." | Set-Content -LiteralPath (Join-Path $OutputFolder "06-sample-index.csv") -Encoding UTF8 }

    $coreMetadata = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT s.name AS SchemaName, o.name AS ObjectName, o.type_desc AS ObjectType,
       c.column_id AS ColumnOrder, c.name AS ColumnName, t.name AS DataType, c.max_length AS MaxLength
FROM sys.objects o
JOIN sys.schemas s ON s.schema_id=o.schema_id
JOIN sys.columns c ON c.object_id=o.object_id
JOIN sys.types t ON t.user_type_id=c.user_type_id
WHERE s.name=@Schema AND o.name IN ('PROD_JOBITEM','POOL_TEILE','BW_AUFTR_POS','ZW_AUFTR_ZEIT','PD_PROD_POINT')
ORDER BY o.name, c.column_id;
"@ -Parameters @{ Schema = $schema }
    Export-ProbeTable -Table $coreMetadata -Path (Join-Path $OutputFolder "07-core-production-columns.csv")

    if (-not [string]::IsNullOrWhiteSpace($OrderNumber)) {
        $targetParams = @{ OrderNumber = $OrderNumber; ItemNumber = $ItemNumber }

        $labelControls = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT TOP (50)
       k.ID AS AUFNR, p.POS_NR AS POSNR,
       k.ETIKETTEN_TYP, k.ETIK_LAYOUT, k.PRINTGUID1, k.PRINTGUID2, k.PRINTGUID3,
       k.PRINTSEQ1, k.PRINTSEQ2, k.PRINTSEQ3,
       p.ETIK_STEUERUNG, p.PROD_ID, p.PROD_BEZ1, p.PP_MENGE, p.PP_BREITE, p.PP_HOEHE,
       ji.JOBNUMBER, ji.BOM_ID, ji.KEYINDEX, ji.OPTIMIZATION, ji.STACKNUMBER, ji.STACKPOSITION,
       ji.LOGICALRACK, ji.RACK, ji.NV_SORTID, ji.NV_NAME
FROM SYSADM.BW_AUFTR_KOPF k
JOIN SYSADM.BW_AUFTR_POS p ON p.ID=k.ID
LEFT JOIN SYSADM.PROD_JOBITEM ji ON ji.AUFNR=p.ID AND ji.POSNR=p.POS_NR
WHERE CONVERT(nvarchar(64), k.ID)=@OrderNumber
  AND (@ItemNumber='' OR CONVERT(nvarchar(64), p.POS_NR)=@ItemNumber)
ORDER BY p.POS_NR, ji.KEYINDEX, ji.BOM_ID;
"@ -Parameters $targetParams
        Export-ProbeTable -Table $labelControls -Path (Join-Path $OutputFolder "08-order-label-controls.csv")

        $optimization = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT DISTINCT TOP (50)
       ji.AUFNR, ji.POSNR, ji.JOBNUMBER, ji.OPTIMIZATION, ji.SEQUENCE_OPTIRUN, ji.NV_NAME,
       o.PRODUKT, o.PRODUKT_BEZ, o.AGG, o.OPTIDATE, o.OPTIMODE, o.STATUS,
       o.SHEETCOUNT, o.RESULT, o.RESULTWITHTRIM, o.LASTCHANGEDATE, o.LASTCHANGEUSER,
       DATALENGTH(o.SAVEFILE) AS SaveFileBytes,
       CASE WHEN o.SAVEFILE IS NULL THEN '' ELSE CONVERT(varchar(128), SUBSTRING(o.SAVEFILE,1,64), 2) END AS SaveFilePrefixHex
FROM SYSADM.PROD_JOBITEM ji
LEFT JOIN SYSADM.PROD_OPTIMIZATION o ON o.OPTIMIZATION=ji.OPTIMIZATION
WHERE CONVERT(nvarchar(64), ji.AUFNR)=@OrderNumber
  AND (@ItemNumber='' OR CONVERT(nvarchar(64), ji.POSNR)=@ItemNumber)
ORDER BY ji.OPTIMIZATION, ji.JOBNUMBER;
"@ -Parameters $targetParams
        Export-ProbeTable -Table $optimization -Path (Join-Path $OutputFolder "09-optimization-record.csv")

        $sequence = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT TOP (200)
       s.OPTIMIZATION, s.SEQUENCE, s.AUFNR, s.POSNR, s.BOM_ID, s.BOM_NODE, s.KEYINDEX, s.PLATENR,
       p.PATTERNNR, p.LAGERORT_ID, p.SLOT, p.LENGTH, p.HEIGHT, p.CUT, p.PM_AUFLEGER_CODE,
       p.STOCKBOOKED, p.SUPPLIER_INFO, p.LASTCHANGEDATE AS PlateLastChangeDate,
       p.LASTCHANGEUSER AS PlateLastChangeUser
FROM SYSADM.PROD_OPTI_SEQUENCE s
LEFT JOIN SYSADM.PROD_OPTI_PLATES p ON p.OPTIMIZATION=s.OPTIMIZATION AND p.PLATENR=s.PLATENR
WHERE CONVERT(nvarchar(64), s.AUFNR)=@OrderNumber
  AND (@ItemNumber='' OR CONVERT(nvarchar(64), s.POSNR)=@ItemNumber)
ORDER BY s.OPTIMIZATION, s.PLATENR, s.SEQUENCE, s.BOM_ID;
"@ -Parameters $targetParams
        Export-ProbeTable -Table $sequence -Path (Join-Path $OutputFolder "10-optimization-sequence-plates.csv")

        $awViews = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT TOP (50)
       i.ID AS AUFNR, i.ITEM_NO AS POSNR, i.LABEL_CONTROL, i.PROD_PRODBATCHNO,
       i.PROD_ID, i.PROD_DESC1, i.PROD_DESC2, i.PI_WIDTH, i.PI_HEIGHT, i.PI_ITEMQTY,
       h.LABEL_LAYOUT, h.LABEL_TYPE, h.BATCH_PRODNOIG, h.BATCH_PRODNOLSG, h.BATCH_PRODNOTSG
FROM SYSADM.AWV_TD_ORDER_ITEM i
LEFT JOIN SYSADM.AWV_TD_ORDER_HEADER h ON h.ID=i.ID
WHERE CONVERT(nvarchar(64), i.ID)=@OrderNumber
  AND (@ItemNumber='' OR CONVERT(nvarchar(64), i.ITEM_NO)=@ItemNumber)
ORDER BY i.ITEM_NO;
"@ -Parameters $targetParams
        Export-ProbeTable -Table $awViews -Path (Join-Path $OutputFolder "11-aw-order-label-view.csv")

        $printJobs = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT TOP (250) pj.*
FROM SYSADM.BW_PRINT_JOBS pj
WHERE pj.DATE BETWEEN DATEADD(day,-2, (SELECT MIN(CAST(o.OPTIDATE AS date))
                                      FROM SYSADM.PROD_JOBITEM ji
                                      JOIN SYSADM.PROD_OPTIMIZATION o ON o.OPTIMIZATION=ji.OPTIMIZATION
                                      WHERE CONVERT(nvarchar(64), ji.AUFNR)=@OrderNumber
                                        AND (@ItemNumber='' OR CONVERT(nvarchar(64), ji.POSNR)=@ItemNumber)))
                  AND DATEADD(day,2, (SELECT MAX(CAST(o.OPTIDATE AS date))
                                     FROM SYSADM.PROD_JOBITEM ji
                                     JOIN SYSADM.PROD_OPTIMIZATION o ON o.OPTIMIZATION=ji.OPTIMIZATION
                                     WHERE CONVERT(nvarchar(64), ji.AUFNR)=@OrderNumber
                                       AND (@ItemNumber='' OR CONVERT(nvarchar(64), ji.POSNR)=@ItemNumber)))
ORDER BY pj.JOB_ID DESC;
"@ -Parameters $targetParams
        Export-ProbeTable -Table $printJobs -Path (Join-Path $OutputFolder "12-print-jobs-near-optimization.csv")

        $poolPayloads = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT TOP (200)
       h.ID, h.DATEI_NAME, h.TYP, h.DATUM_ERSTELLT, h.DATUM_IMPORTIERT, h.DATUM_VERARBEITET,
       h.STATUS, h.BENUTZER, h.MITARB, p.SEQUENZ_NR, p.STATUS AS PoolStatus, p.INDEXFELD1,
       LEFT(p.DATENSATZ, 4000) AS DataPreview
FROM SYSADM.FS_POOL_KOPF h
JOIN SYSADM.FS_POOL p ON p.ID=h.ID
WHERE (p.DATENSATZ LIKE '%' + @OrderNumber + '%'
       OR p.INDEXFELD1 LIKE '%' + @OrderNumber + '%'
       OR p.DATENSATZ LIKE '%OPTIMIZATION%'
       OR UPPER(h.DATEI_NAME) LIKE '%ETIK%'
       OR UPPER(h.DATEI_NAME) LIKE '%LABEL%')
ORDER BY h.DATUM_ERSTELLT DESC, h.ID DESC, p.SEQUENZ_NR;
"@ -Parameters $targetParams
        Export-ProbeTable -Table $poolPayloads -Path (Join-Path $OutputFolder "13-pool-label-payload-candidates.csv")

        $printModules = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT TOP (250) s.name AS SchemaName, o.name AS ObjectName, o.type_desc AS ObjectType,
       CASE WHEN UPPER(m.definition) LIKE '%BW_PRINT_JOBS%' THEN 1 ELSE 0 END AS ReferencesPrintJobs,
       CASE WHEN UPPER(m.definition) LIKE '%ETIK_STEUERUNG%' THEN 1 ELSE 0 END AS ReferencesLabelControl,
       CASE WHEN UPPER(m.definition) LIKE '%ETIK_LAYOUT%' THEN 1 ELSE 0 END AS ReferencesLabelLayout,
       CASE WHEN UPPER(m.definition) LIKE '%PROD_OPTI_SEQUENCE%' THEN 1 ELSE 0 END AS ReferencesOptiSequence,
       CASE WHEN UPPER(m.definition) LIKE '%PROD_OPTIMIZATION%' THEN 1 ELSE 0 END AS ReferencesOptimization,
       CASE WHEN UPPER(m.definition) LIKE '%SAVEFILE%' THEN 1 ELSE 0 END AS ReferencesSaveFile,
       LEFT(REPLACE(REPLACE(m.definition, CHAR(13), ' '), CHAR(10), ' '), 12000) AS DefinitionPreview
FROM sys.sql_modules m
JOIN sys.objects o ON o.object_id=m.object_id
JOIN sys.schemas s ON s.schema_id=o.schema_id
WHERE s.name=@Schema AND (
       UPPER(m.definition) LIKE '%BW_PRINT_JOBS%'
       OR UPPER(m.definition) LIKE '%ETIK_STEUERUNG%'
       OR UPPER(m.definition) LIKE '%ETIK_LAYOUT%'
       OR UPPER(m.definition) LIKE '%PROD_OPTI_SEQUENCE%'
       OR UPPER(m.definition) LIKE '%PROD_OPTIMIZATION%'
       OR UPPER(m.definition) LIKE '%SAVEFILE%'
)
ORDER BY o.type_desc, o.name;
"@ -Parameters @{ Schema = $schema }
        Export-ProbeTable -Table $printModules -Path (Join-Path $OutputFolder "14-print-pipeline-module-references.csv")


        # v0.488: the verified sample generated STSL/STSD/PRODBDAZ pool files
        # at optimization time. Pull those exact job/order-linked records with a
        # larger text preview so we can determine whether they contain the pane
        # label payload or only a production-interface envelope.
        $poolJobFiles = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT TOP (300)
       h.ID, h.DATEI_NAME, h.TYP, h.DATUM_ERSTELLT, h.DATUM_IMPORTIERT, h.DATUM_VERARBEITET,
       h.STATUS, h.BENUTZER, h.MITARB, p.SEQUENZ_NR, p.STATUS AS PoolStatus, p.INDEXFELD1,
       LEN(p.DATENSATZ) AS DataLength, LEFT(p.DATENSATZ, 12000) AS DataPreview
FROM SYSADM.FS_POOL_KOPF h
JOIN SYSADM.FS_POOL p ON p.ID=h.ID
WHERE p.INDEXFELD1 LIKE '%' + @OrderNumber + '%'
   OR p.DATENSATZ LIKE '%' + @OrderNumber + '%'
   OR EXISTS (
       SELECT 1 FROM SYSADM.PROD_JOBITEM ji
       WHERE CONVERT(nvarchar(64), ji.AUFNR)=@OrderNumber
         AND (@ItemNumber='' OR CONVERT(nvarchar(64), ji.POSNR)=@ItemNumber)
         AND UPPER(h.DATEI_NAME) LIKE '%' + CONVERT(nvarchar(32), ji.JOBNUMBER) + '%'
   )
ORDER BY h.DATUM_ERSTELLT DESC, h.ID DESC, p.SEQUENZ_NR;
"@ -Parameters $targetParams
        Export-ProbeTable -Table $poolJobFiles -Path (Join-Path $OutputFolder "15-pool-job-file-records.csv")

        $poolFamilyContext = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT TOP (500)
       h.ID, h.DATEI_NAME, h.TYP, h.DATUM_ERSTELLT, h.DATUM_IMPORTIERT, h.DATUM_VERARBEITET,
       h.STATUS, h.BENUTZER, h.MITARB, p.SEQUENZ_NR, p.STATUS AS PoolStatus, p.INDEXFELD1,
       LEN(p.DATENSATZ) AS DataLength, LEFT(p.DATENSATZ, 4000) AS DataPreview
FROM SYSADM.FS_POOL_KOPF h
JOIN SYSADM.FS_POOL p ON p.ID=h.ID
WHERE (UPPER(h.DATEI_NAME) LIKE 'STSL%.ASC'
       OR UPPER(h.DATEI_NAME) LIKE 'STSD%.ASC'
       OR UPPER(h.DATEI_NAME) = 'PRODBDAZ.000')
  AND h.DATUM_ERSTELLT BETWEEN DATEADD(day,-1, (SELECT MIN(o.OPTIDATE)
      FROM SYSADM.PROD_JOBITEM ji JOIN SYSADM.PROD_OPTIMIZATION o ON o.OPTIMIZATION=ji.OPTIMIZATION
      WHERE CONVERT(nvarchar(64), ji.AUFNR)=@OrderNumber
        AND (@ItemNumber='' OR CONVERT(nvarchar(64), ji.POSNR)=@ItemNumber)))
      AND DATEADD(day,2, (SELECT MAX(o.OPTIDATE)
      FROM SYSADM.PROD_JOBITEM ji JOIN SYSADM.PROD_OPTIMIZATION o ON o.OPTIMIZATION=ji.OPTIMIZATION
      WHERE CONVERT(nvarchar(64), ji.AUFNR)=@OrderNumber
        AND (@ItemNumber='' OR CONVERT(nvarchar(64), ji.POSNR)=@ItemNumber)))
ORDER BY h.DATUM_ERSTELLT DESC, h.ID DESC, p.SEQUENZ_NR;
"@ -Parameters $targetParams
        Export-ProbeTable -Table $poolFamilyContext -Path (Join-Path $OutputFolder "16-pool-output-family-context.csv")

        $poolModules = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT TOP (300) s.name AS SchemaName, o.name AS ObjectName, o.type_desc AS ObjectType,
       CASE WHEN UPPER(m.definition) LIKE '%STSL%' THEN 1 ELSE 0 END AS ReferencesSTSL,
       CASE WHEN UPPER(m.definition) LIKE '%STSD%' THEN 1 ELSE 0 END AS ReferencesSTSD,
       CASE WHEN UPPER(m.definition) LIKE '%PRODBDAZ%' THEN 1 ELSE 0 END AS ReferencesPRODBDAZ,
       CASE WHEN UPPER(m.definition) LIKE '%FS_POOL%' THEN 1 ELSE 0 END AS ReferencesFsPool,
       CASE WHEN UPPER(m.definition) LIKE '%ETIK%' THEN 1 ELSE 0 END AS ReferencesEtik,
       CASE WHEN UPPER(m.definition) LIKE '%BARCODE%' THEN 1 ELSE 0 END AS ReferencesBarcode,
       LEFT(REPLACE(REPLACE(m.definition, CHAR(13), ' '), CHAR(10), ' '), 16000) AS DefinitionPreview
FROM sys.sql_modules m
JOIN sys.objects o ON o.object_id=m.object_id
JOIN sys.schemas s ON s.schema_id=o.schema_id
WHERE s.name=@Schema AND (
       UPPER(m.definition) LIKE '%STSL%'
       OR UPPER(m.definition) LIKE '%STSD%'
       OR UPPER(m.definition) LIKE '%PRODBDAZ%'
       OR UPPER(m.definition) LIKE '%FS_POOL%'
)
ORDER BY o.type_desc, o.name;
"@ -Parameters @{ Schema = $schema }
        Export-ProbeTable -Table $poolModules -Path (Join-Path $OutputFolder "17-pool-output-module-references.csv")

        $labelOrderColumns = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT s.name AS SchemaName, o.name AS ObjectName, o.type_desc AS ObjectType,
       c.column_id AS ColumnOrder, c.name AS ColumnName, t.name AS DataType, c.max_length AS MaxLength
FROM sys.objects o
JOIN sys.schemas s ON s.schema_id=o.schema_id
JOIN sys.columns c ON c.object_id=o.object_id
JOIN sys.types t ON t.user_type_id=c.user_type_id
WHERE s.name=@Schema AND o.type IN ('U','V')
  AND EXISTS (SELECT 1 FROM sys.columns c1 WHERE c1.object_id=o.object_id AND UPPER(c1.name) IN ('AUFNR','ID','ORDER_NO','ORDERNR','PEDIDO'))
  AND EXISTS (SELECT 1 FROM sys.columns c2 WHERE c2.object_id=o.object_id AND UPPER(c2.name) IN ('POSNR','POS_NR','ITEM_NO','ITEMNR','POSICION'))
  AND EXISTS (SELECT 1 FROM sys.columns c3 WHERE c3.object_id=o.object_id AND (UPPER(c3.name) LIKE '%ETIK%' OR UPPER(c3.name) LIKE '%LABEL%' OR UPPER(c3.name) LIKE '%BARCODE%'))
ORDER BY o.type_desc, o.name, c.column_id;
"@ -Parameters @{ Schema = $schema }
        Export-ProbeTable -Table $labelOrderColumns -Path (Join-Path $OutputFolder "18-order-item-label-objects.csv")
    }


    # v0.490+: mirror the operator's actual A+W Business Pro path:
    # Production Manager -> Optimization Overview -> Output -> Cutting Labels.
    # These queries look for the report definition and can optionally capture
    # the SQL/temp-file deltas created when the operator opens the Screen preview.
    $optimizationParams = @{ OptimizationNumber = $OptimizationNumber; OrderNumber = $OrderNumber; ItemNumber = $ItemNumber }
    $selectedOptimization = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT TOP (1000)
       o.OPTIMIZATION, o.PRODUKT, o.PRODUKT_BEZ, o.AGG, o.OPTIDATE, o.OPTIMODE, o.STATUS,
       o.SHEETCOUNT, o.RESULT, o.RESULTWITHTRIM, o.LASTCHANGEDATE, o.LASTCHANGEUSER,
       DATALENGTH(o.SAVEFILE) AS SaveFileBytes,
       ji.AUFNR, ji.POSNR, ji.BOM_ID, ji.KEYINDEX, ji.JOBNUMBER, ji.SEQUENCE_OPTIRUN,
       ji.STACKNUMBER, ji.STACKPOSITION, ji.LOGICALRACK, ji.RACK, ji.NV_NAME,
       seq.SEQUENCE AS OptimizationSequence, seq.PLATENR
FROM SYSADM.PROD_OPTIMIZATION o
LEFT JOIN SYSADM.PROD_JOBITEM ji ON ji.OPTIMIZATION=o.OPTIMIZATION
LEFT JOIN SYSADM.PROD_OPTI_SEQUENCE seq
  ON seq.OPTIMIZATION=o.OPTIMIZATION AND seq.AUFNR=ji.AUFNR AND seq.POSNR=ji.POSNR
 AND seq.BOM_ID=ji.BOM_ID AND seq.KEYINDEX=ji.KEYINDEX
WHERE (@OptimizationNumber<>'' AND CONVERT(nvarchar(64), o.OPTIMIZATION)=@OptimizationNumber)
   OR (@OptimizationNumber='' AND @OrderNumber<>'' AND CONVERT(nvarchar(64), ji.AUFNR)=@OrderNumber
       AND (@ItemNumber='' OR CONVERT(nvarchar(64), ji.POSNR)=@ItemNumber))
ORDER BY o.OPTIMIZATION, ji.JOBNUMBER, ji.AUFNR, ji.POSNR, ji.BOM_ID, seq.SEQUENCE;
"@ -Parameters $optimizationParams
    Export-ProbeTable -Table $selectedOptimization -Path (Join-Path $OutputFolder "19-selected-optimization-output-context.csv")

    $reportMetadata = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT s.name AS SchemaName, o.name AS ObjectName, o.type_desc AS ObjectType,
       c.column_id AS ColumnOrder, c.name AS ColumnName, t.name AS DataType, c.max_length AS MaxLength
FROM sys.objects o
JOIN sys.schemas s ON s.schema_id=o.schema_id
JOIN sys.columns c ON c.object_id=o.object_id
JOIN sys.types t ON t.user_type_id=c.user_type_id
WHERE s.name=@Schema AND o.type IN ('U','V')
  AND (
       UPPER(o.name) LIKE '%FORM%' OR UPPER(o.name) LIKE '%REPORT%' OR UPPER(o.name) LIKE '%PRINT%'
       OR UPPER(o.name) LIKE '%DRUCK%' OR UPPER(o.name) LIKE '%AUSGAB%' OR UPPER(o.name) LIKE '%OUTPUT%'
       OR UPPER(c.name) LIKE '%FORM%' OR UPPER(c.name) LIKE '%REPORT%' OR UPPER(c.name) LIKE '%PRINT%'
       OR UPPER(c.name) LIKE '%DRUCK%' OR UPPER(c.name) LIKE '%ETIK%' OR UPPER(c.name) LIKE '%LABEL%'
  )
ORDER BY o.type_desc, o.name, c.column_id;
"@ -Parameters @{ Schema=$schema }
    Export-ProbeTable -Table $reportMetadata -Path (Join-Path $OutputFolder "20-output-report-definition-columns.csv")

    $uiNeedles = @(
        'Cutting Labels',
        'Cutting Label',
        'Residue Plate Labels',
        'Optimization Result',
        'Optimization List',
        'Rack Loading List',
        'Cutting Plans',
        'optimized stock plates',
        'Series from quantity',
        'Brother HL-L6400DW'
    )
    $reportObjects = @(
        'KA_FORMULARE', 'KA_PRINT_DETAIL', 'KU_KUNDEN_FORM', 'LI_LIEF_FORM',
        'BW_PRINT_JOBS', 'RR_JOBHEAD', 'KA_TEXTE', 'KA_FIRMA', 'KA_FIRMA_MITARB',
        'FS_POOL_KOPF', 'FS_POOL_LOG'
    )
    $uiHits = New-Object System.Collections.Generic.List[object]
    foreach ($objectName in $reportObjects) {
        try {
            foreach ($hit in (Find-ProbeTextHits -Connection $connection -SchemaName $schema -ObjectName $objectName -Needles $uiNeedles)) {
                $uiHits.Add($hit)
            }
        }
        catch {
            $uiHits.Add([pscustomobject]@{ SchemaName=$schema; ObjectName=$objectName; ColumnName='<probe-error>'; MatchedText=''; ValuePreview=$_.Exception.Message })
        }
    }
    if ($uiHits.Count -gt 0) { $uiHits | Export-Csv -LiteralPath (Join-Path $OutputFolder "21-cutting-label-ui-text-hits.csv") -NoTypeInformation -Encoding UTF8 }
    else { "No configured report text matched the Cutting Labels / Output-screen phrases." | Set-Content -LiteralPath (Join-Path $OutputFolder "21-cutting-label-ui-text-hits.csv") -Encoding UTF8 }

    foreach ($reportTable in @('KA_FORMULARE','KA_PRINT_DETAIL')) {
        $fileName = $(if ($reportTable -eq 'KA_FORMULARE') { '22-ka-formulare-report-catalog.csv' } else { '23-ka-print-detail-report-catalog.csv' })
        try {
            $catalog = Invoke-ProbeQuery -Connection $connection -Query ("SELECT TOP (1000) * FROM " + (Quote-SqlIdentifier $schema) + "." + (Quote-SqlIdentifier $reportTable) + ";")
            Export-ProbeTable -Table $catalog -Path (Join-Path $OutputFolder $fileName)
        }
        catch {
            ("Probe query failed: " + $_.Exception.Message) | Set-Content -LiteralPath (Join-Path $OutputFolder $fileName) -Encoding UTF8
        }
    }

    $reportModules = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT TOP (400) s.name AS SchemaName, o.name AS ObjectName, o.type_desc AS ObjectType,
       CASE WHEN UPPER(m.definition) LIKE '%KA_FORMULARE%' THEN 1 ELSE 0 END AS ReferencesKaFormulare,
       CASE WHEN UPPER(m.definition) LIKE '%KA_PRINT_DETAIL%' THEN 1 ELSE 0 END AS ReferencesKaPrintDetail,
       CASE WHEN UPPER(m.definition) LIKE '%BW_PRINT_JOBS%' THEN 1 ELSE 0 END AS ReferencesPrintJobs,
       CASE WHEN UPPER(m.definition) LIKE '%REPORT_GRUPPE%' THEN 1 ELSE 0 END AS ReferencesReportGroup,
       CASE WHEN UPPER(m.definition) LIKE '%DRUCK_STRING%' THEN 1 ELSE 0 END AS ReferencesPrintString,
       CASE WHEN UPPER(m.definition) LIKE '%PRINT_DEF%' THEN 1 ELSE 0 END AS ReferencesPrintDefinition,
       CASE WHEN UPPER(m.definition) LIKE '%CUTTING LABEL%' THEN 1 ELSE 0 END AS ReferencesCuttingLabelText,
       LEFT(REPLACE(REPLACE(m.definition, CHAR(13), ' '), CHAR(10), ' '), 16000) AS DefinitionPreview
FROM sys.sql_modules m
JOIN sys.objects o ON o.object_id=m.object_id
JOIN sys.schemas s ON s.schema_id=o.schema_id
WHERE s.name=@Schema AND (
       UPPER(m.definition) LIKE '%KA_FORMULARE%'
       OR UPPER(m.definition) LIKE '%KA_PRINT_DETAIL%'
       OR UPPER(m.definition) LIKE '%BW_PRINT_JOBS%'
       OR UPPER(m.definition) LIKE '%REPORT_GRUPPE%'
       OR UPPER(m.definition) LIKE '%DRUCK_STRING%'
       OR UPPER(m.definition) LIKE '%PRINT_DEF%'
       OR UPPER(m.definition) LIKE '%CUTTING LABEL%'
)
ORDER BY o.type_desc, o.name;
"@ -Parameters @{ Schema=$schema }
    Export-ProbeTable -Table $reportModules -Path (Join-Path $OutputFolder "24-output-report-module-references.csv")

    # v0.493: the operator-provided Cutting Labels preview proves the report is
    # rendered by Crystal Reports inside the remote Citrix A+W session. Instead
    # of watching the local workstation for report files, inspect A+W's report
    # catalog/configuration and the exact data behind the selected optimization.
    $crystalMetadata = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT s.name AS SchemaName, o.name AS ObjectName, o.type_desc AS ObjectType,
       c.column_id AS ColumnOrder, c.name AS ColumnName, t.name AS DataType, c.max_length AS MaxLength
FROM sys.objects o
JOIN sys.schemas s ON s.schema_id=o.schema_id
JOIN sys.columns c ON c.object_id=o.object_id
JOIN sys.types t ON t.user_type_id=c.user_type_id
WHERE s.name=@Schema AND o.type IN ('U','V')
  AND (
       UPPER(o.name) LIKE '%FORM%' OR UPPER(o.name) LIKE '%REPORT%' OR UPPER(o.name) LIKE '%PRINT%'
       OR UPPER(o.name) LIKE '%DRUCK%' OR UPPER(o.name) LIKE '%CRYSTAL%' OR UPPER(o.name) LIKE '%RPT%'
       OR UPPER(c.name) LIKE '%FORM%' OR UPPER(c.name) LIKE '%REPORT%' OR UPPER(c.name) LIKE '%PRINT%'
       OR UPPER(c.name) LIKE '%DRUCK%' OR UPPER(c.name) LIKE '%CRYSTAL%' OR UPPER(c.name) LIKE '%RPT%'
       OR UPPER(c.name) LIKE '%PATH%' OR UPPER(c.name) LIKE '%DATEI%' OR UPPER(c.name) LIKE '%FILE%'
       OR UPPER(c.name) LIKE '%TEMPLATE%' OR UPPER(c.name) LIKE '%VORLAGE%' OR UPPER(c.name) LIKE '%LAYOUT%'
  )
ORDER BY o.type_desc, o.name, c.column_id;
"@ -Parameters @{ Schema=$schema }
    Export-ProbeTable -Table $crystalMetadata -Path (Join-Path $OutputFolder "31-crystal-report-candidate-columns.csv")

    $crystalNeedles = @(
        'Cutting Labels', 'Cutting Label', 'Crystal', '.rpt', 'RPT',
        'Etik', 'Etikett', 'Label', 'Schneid', 'Zuschnitt',
        'Residue Plate Labels', 'Optimization Result', 'Optimization List',
        'Rack Loading List', 'Cutting Plans'
    )
    # Keep value scanning intentionally narrow. Metadata discovery can list many
    # order/file tables; only report-like object names plus the known A+W report
    # catalogs are value-scanned so this diagnostic does not become an expensive
    # production-database sweep.
    $crystalObjectNames = @(
        (
            @(
                $crystalMetadata.Rows |
                ForEach-Object { [string]$_.ObjectName } |
                Where-Object { $_ -match '(?i)CRYSTAL|RPT|REPORT' }
            ) + @(
                'KA_FORMULARE', 'KA_PRINT_DETAIL', 'KU_KUNDEN_FORM', 'LI_LIEF_FORM',
                'BW_PRINT_JOBS', 'KA_FIRMA', 'KA_FIRMA_MITARB'
            )
        ) |
        Sort-Object -Unique |
        Select-Object -First 40
    )
    $crystalHits = New-Object System.Collections.Generic.List[object]
    foreach ($objectName in $crystalObjectNames) {
        try {
            foreach ($hit in (Find-ProbeTextHits -Connection $connection -SchemaName $schema -ObjectName $objectName -Needles $crystalNeedles)) {
                $crystalHits.Add($hit)
            }
        }
        catch {
            $crystalHits.Add([pscustomobject]@{
                SchemaName=$schema
                ObjectName=$objectName
                ColumnName='<probe-error>'
                MatchedText=''
                ValuePreview=$_.Exception.Message
            })
        }
    }
    Export-ProbeObjects -Rows $crystalHits.ToArray() -Path (Join-Path $OutputFolder "32-crystal-report-text-hits.csv")

    $crystalModules = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT TOP (500) s.name AS SchemaName, o.name AS ObjectName, o.type_desc AS ObjectType,
       CASE WHEN UPPER(m.definition) LIKE '%CRYSTAL%' THEN 1 ELSE 0 END AS ReferencesCrystal,
       CASE WHEN UPPER(m.definition) LIKE '%.RPT%' THEN 1 ELSE 0 END AS ReferencesRpt,
       CASE WHEN UPPER(m.definition) LIKE '%CUTTING LABEL%' THEN 1 ELSE 0 END AS ReferencesCuttingLabels,
       CASE WHEN UPPER(m.definition) LIKE '%ETIK%' THEN 1 ELSE 0 END AS ReferencesEtik,
       CASE WHEN UPPER(m.definition) LIKE '%SCHNEID%' OR UPPER(m.definition) LIKE '%ZUSCHNITT%' THEN 1 ELSE 0 END AS ReferencesCuttingGerman,
       CASE WHEN UPPER(m.definition) LIKE '%KA_FORMULARE%' THEN 1 ELSE 0 END AS ReferencesKaFormulare,
       CASE WHEN UPPER(m.definition) LIKE '%KA_PRINT_DETAIL%' THEN 1 ELSE 0 END AS ReferencesKaPrintDetail,
       LEFT(REPLACE(REPLACE(m.definition, CHAR(13), ' '), CHAR(10), ' '), 20000) AS DefinitionPreview
FROM sys.sql_modules m
JOIN sys.objects o ON o.object_id=m.object_id
JOIN sys.schemas s ON s.schema_id=o.schema_id
WHERE s.name=@Schema AND (
       UPPER(m.definition) LIKE '%CRYSTAL%'
       OR UPPER(m.definition) LIKE '%.RPT%'
       OR UPPER(m.definition) LIKE '%CUTTING LABEL%'
       OR UPPER(m.definition) LIKE '%ETIK%'
       OR UPPER(m.definition) LIKE '%SCHNEID%'
       OR UPPER(m.definition) LIKE '%ZUSCHNITT%'
       OR UPPER(m.definition) LIKE '%KA_FORMULARE%'
       OR UPPER(m.definition) LIKE '%KA_PRINT_DETAIL%'
)
ORDER BY o.type_desc, o.name;
"@ -Parameters @{ Schema=$schema }
    Export-ProbeTable -Table $crystalModules -Path (Join-Path $OutputFolder "33-crystal-report-module-references.csv")

    if (-not [string]::IsNullOrWhiteSpace($OptimizationNumber)) {
        # Match the visible Crystal label anchors: customer, A+W Order/Item,
        # production batch/job, optimization/plate/sequence, product, size and
        # customer/order references. A+W installations can expose different
        # generations of the English AWV reporting views, so optional view
        # columns are projected only when sys.columns proves they exist.
        $headerColumns = Get-LiveObjectColumnSet -Connection $connection -SchemaName 'SYSADM' -ObjectName 'AWV_TD_ORDER_HEADER'
        $itemColumns = Get-LiveObjectColumnSet -Connection $connection -SchemaName 'SYSADM' -ObjectName 'AWV_TD_ORDER_ITEM'
        $headerSelect = @(
            (Get-OptionalColumnSelectSql -ColumnSet $headerColumns -TableAlias 'h' -ColumnName 'CUST_NAME1' -OutputAlias 'CustomerName'),
            (Get-OptionalColumnSelectSql -ColumnSet $headerColumns -TableAlias 'h' -ColumnName 'PO_TEXT1' -OutputAlias 'PurchaseOrderText1'),
            (Get-OptionalColumnSelectSql -ColumnSet $headerColumns -TableAlias 'h' -ColumnName 'PO_TEXT2' -OutputAlias 'PurchaseOrderText2'),
            (Get-OptionalColumnSelectSql -ColumnSet $headerColumns -TableAlias 'h' -ColumnName 'LABEL_LAYOUT' -OutputAlias 'HeaderLabelLayout'),
            (Get-OptionalColumnSelectSql -ColumnSet $headerColumns -TableAlias 'h' -ColumnName 'LABEL_TYPE' -OutputAlias 'HeaderLabelType')
        ) -join ",`r`n       "
        $itemSelect = @(
            (Get-OptionalColumnSelectSql -ColumnSet $itemColumns -TableAlias 'i' -ColumnName 'LABEL_CONTROL' -OutputAlias 'ItemLabelControl'),
            (Get-OptionalColumnSelectSql -ColumnSet $itemColumns -TableAlias 'i' -ColumnName 'ITEM_CUSTREF' -OutputAlias 'CustomerReference'),
            (Get-OptionalColumnSelectSql -ColumnSet $itemColumns -TableAlias 'i' -ColumnName 'ITEM_CUSTITEMNO' -OutputAlias 'CustomerItemNumber'),
            (Get-OptionalColumnSelectSql -ColumnSet $itemColumns -TableAlias 'i' -ColumnName 'ITEM_TEXT' -OutputAlias 'ItemText'),
            (Get-OptionalColumnSelectSql -ColumnSet $itemColumns -TableAlias 'i' -ColumnName 'ITEM_TEXT1' -OutputAlias 'ItemText1'),
            (Get-OptionalColumnSelectSql -ColumnSet $itemColumns -TableAlias 'i' -ColumnName 'ITEM_TEXT2' -OutputAlias 'ItemText2'),
            (Get-OptionalColumnSelectSql -ColumnSet $itemColumns -TableAlias 'i' -ColumnName 'ITEM_TEXT3' -OutputAlias 'ItemText3'),
            (Get-OptionalColumnSelectSql -ColumnSet $itemColumns -TableAlias 'i' -ColumnName 'ITEM_TEXT4' -OutputAlias 'ItemText4'),
            (Get-OptionalColumnSelectSql -ColumnSet $itemColumns -TableAlias 'i' -ColumnName 'ITEM_TEXT5' -OutputAlias 'ItemText5'),
            (Get-OptionalColumnSelectSql -ColumnSet $itemColumns -TableAlias 'i' -ColumnName 'PROD_ID' -OutputAlias 'ProductId'),
            (Get-OptionalColumnSelectSql -ColumnSet $itemColumns -TableAlias 'i' -ColumnName 'PROD_DESC1' -OutputAlias 'ProductDescription1'),
            (Get-OptionalColumnSelectSql -ColumnSet $itemColumns -TableAlias 'i' -ColumnName 'PROD_DESC2' -OutputAlias 'ProductDescription2'),
            (Get-OptionalColumnSelectSql -ColumnSet $itemColumns -TableAlias 'i' -ColumnName 'PROD_SHORTDESC' -OutputAlias 'ProductShortDescription'),
            (Get-OptionalColumnSelectSql -ColumnSet $itemColumns -TableAlias 'i' -ColumnName 'PI_WIDTH' -OutputAlias 'Width' -FallbackSql 'bp.PP_BREITE'),
            (Get-OptionalColumnSelectSql -ColumnSet $itemColumns -TableAlias 'i' -ColumnName 'PI_HEIGHT' -OutputAlias 'Height' -FallbackSql 'bp.PP_HOEHE'),
            (Get-OptionalColumnSelectSql -ColumnSet $itemColumns -TableAlias 'i' -ColumnName 'PI_THICKNESS' -OutputAlias 'Thickness' -FallbackSql 'bp.PP_DICKE'),
            (Get-OptionalColumnSelectSql -ColumnSet $itemColumns -TableAlias 'i' -ColumnName 'PI_ITEMQTY' -OutputAlias 'ItemQuantity' -FallbackSql 'bp.PP_MENGE'),
            (Get-OptionalColumnSelectSql -ColumnSet $itemColumns -TableAlias 'i' -ColumnName 'PI_WEIGHTPERPIECE' -OutputAlias 'WeightPerPiece' -FallbackSql 'bp.PP_GEWICHT'),
            (Get-OptionalColumnSelectSql -ColumnSet $itemColumns -TableAlias 'i' -ColumnName 'PI_SURFACEPERPIECE' -OutputAlias 'SurfacePerPiece' -FallbackSql 'bp.PP_QM'),
            (Get-OptionalColumnSelectSql -ColumnSet $itemColumns -TableAlias 'i' -ColumnName 'PI_SURFACEPERQTY' -OutputAlias 'SurfacePerQuantity' -FallbackSql 'bp.PP_QM'),
            (Get-OptionalColumnSelectSql -ColumnSet $itemColumns -TableAlias 'i' -ColumnName 'DATELASTMOD' -OutputAlias 'ItemLastModified' -FallbackSql 'bp.DATUM'),
            (Get-OptionalColumnSelectSql -ColumnSet $itemColumns -TableAlias 'i' -ColumnName 'COMP_REASON' -OutputAlias 'ComplaintReason' -FallbackSql 'bp.REKLA_GRUND'),
            (Get-OptionalColumnSelectSql -ColumnSet $itemColumns -TableAlias 'i' -ColumnName 'COMP_CAUSE' -OutputAlias 'ComplaintCause' -FallbackSql 'bp.REKLA_ORT'),
            (Get-OptionalColumnSelectSql -ColumnSet $itemColumns -TableAlias 'i' -ColumnName 'REF_DELORDERNO' -OutputAlias 'ReferencedDeliveryOrder'),
            (Get-OptionalColumnSelectSql -ColumnSet $itemColumns -TableAlias 'i' -ColumnName 'REF_DELITEMNO' -OutputAlias 'ReferencedDeliveryItem'),
            (Get-OptionalColumnSelectSql -ColumnSet $itemColumns -TableAlias 'i' -ColumnName 'REF_PONO' -OutputAlias 'ReferencedPurchaseOrder'),
            (Get-OptionalColumnSelectSql -ColumnSet $itemColumns -TableAlias 'i' -ColumnName 'REF_ITEMNO' -OutputAlias 'ReferencedItem')
        ) -join ",`r`n       "
        $labelDataQuery = @"
SELECT TOP (2000)
       seq.OPTIMIZATION AS Optimization,
       seq.SEQUENCE AS OptimizationSequence,
       seq.PLATENR AS PlateNumber,
       ji.JOBNUMBER AS BatchJobNumber,
       ji.OPTIMIZATION AS JobItemOptimization,
       seq.AUFNR AS OrderNr,
       seq.POSNR AS ItemNr,
       seq.BOM_ID AS BomId,
       seq.KEYINDEX AS KeyIndex,
       ji.STACKNUMBER AS StackNumber,
       ji.STACKPOSITION AS StackPosition,
       $headerSelect,
       $itemSelect,
       bp.PP_GEWICHT AS RawOrderWeight,
       bp.PP_QM AS RawOrderSurfaceArea
FROM SYSADM.PROD_OPTI_SEQUENCE seq
OUTER APPLY (
    SELECT TOP (1) candidate.*
    FROM SYSADM.PROD_JOBITEM candidate
    WHERE candidate.AUFNR=seq.AUFNR AND candidate.POSNR=seq.POSNR
    ORDER BY
      CASE WHEN candidate.BOM_ID=seq.BOM_ID AND candidate.KEYINDEX=seq.KEYINDEX THEN 0
           WHEN candidate.BOM_ID=seq.BOM_ID THEN 1 ELSE 2 END,
      CASE WHEN candidate.OPTIMIZATION=seq.OPTIMIZATION THEN 0 ELSE 1 END,
      candidate.JOBNUMBER DESC, candidate.BOM_ID
) ji
LEFT JOIN SYSADM.AWV_TD_ORDER_HEADER h ON h.ID=seq.AUFNR
LEFT JOIN SYSADM.AWV_TD_ORDER_ITEM i ON i.ID=seq.AUFNR AND i.ITEM_NO=seq.POSNR
LEFT JOIN SYSADM.BW_AUFTR_POS bp ON bp.ID=seq.AUFNR AND bp.POS_NR=seq.POSNR
WHERE CONVERT(nvarchar(64), seq.OPTIMIZATION)=@OptimizationNumber
  AND (@OrderNumber='' OR CONVERT(nvarchar(64), seq.AUFNR)=@OrderNumber)
  AND (@ItemNumber='' OR CONVERT(nvarchar(64), seq.POSNR)=@ItemNumber)
ORDER BY seq.SEQUENCE, seq.AUFNR, seq.POSNR, seq.BOM_ID;
"@
        $labelData = Invoke-ProbeQuery -Connection $connection -Query $labelDataQuery -Parameters $optimizationParams
        Export-ProbeTable -Table $labelData -Path (Join-Path $OutputFolder "34-selected-optimization-label-data.csv")

        $routeData = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT TOP (4000)
       z.AUFNR AS OrderNr,
       z.POSNR AS ItemNr,
       z.BOM_ID AS BomId,
       z.BOM_NODE AS BomNode,
       z.ARBART AS WorkTypeId,
       z.AGG AS AggregateId,
       z.ARBFOLGE AS WorkSequence,
       z.DATUM_PROD AS ProductionDate,
       z.STUECK AS PlannedPieces,
       z.FERTIG AS CompletedPieces,
       z.KZ_SELECTED AS IsSelected,
       z.KZ_NOP AS IsNoOperation,
       z.BMENGE AS BomQuantity,
       z.KANTEN AS EdgeData,
       z.POOL_POS AS PoolPosition,
       z.ROWID AS SourceRowId
FROM SYSADM.ZW_AUFTR_ZEIT z
WHERE EXISTS (
    SELECT 1
    FROM SYSADM.PROD_OPTI_SEQUENCE seq
    WHERE CONVERT(nvarchar(64), seq.OPTIMIZATION)=@OptimizationNumber
      AND seq.AUFNR=z.AUFNR AND seq.POSNR=z.POSNR
)
  AND (@OrderNumber='' OR CONVERT(nvarchar(64), z.AUFNR)=@OrderNumber)
  AND (@ItemNumber='' OR CONVERT(nvarchar(64), z.POSNR)=@ItemNumber)
ORDER BY z.AUFNR, z.POSNR, z.BOM_ID, z.ARBFOLGE, z.ARBART, z.AGG;
"@ -Parameters $optimizationParams
        Export-ProbeTable -Table $routeData -Path (Join-Path $OutputFolder "35-selected-optimization-production-route.csv")

        $barcodeMetadata = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT s.name AS SchemaName, o.name AS ObjectName, o.type_desc AS ObjectType,
       c.column_id AS ColumnOrder, c.name AS ColumnName, t.name AS DataType, c.max_length AS MaxLength
FROM sys.objects o
JOIN sys.schemas s ON s.schema_id=o.schema_id
JOIN sys.columns c ON c.object_id=o.object_id
JOIN sys.types t ON t.user_type_id=c.user_type_id
WHERE s.name=@Schema AND o.type IN ('U','V')
  AND (UPPER(c.name) LIKE '%BARCODE%' OR UPPER(c.name) LIKE '%EAN%' OR UPPER(c.name) LIKE '%CODE128%'
       OR UPPER(c.name) LIKE '%ETIK_NR%' OR UPPER(c.name) LIKE '%LABEL%')
ORDER BY o.type_desc, o.name, c.column_id;
"@ -Parameters @{ Schema=$schema }
        Export-ProbeTable -Table $barcodeMetadata -Path (Join-Path $OutputFolder "36-barcode-label-candidate-columns.csv")

        # v0.495: the Crystal catalog scan identified the exact Optimization
        # Overview Cutting Labels report. Resolve its report ID/print point and
        # adjacent routing configuration before attempting any application import.
        $cuttingLabelReportFile = 'Prodman_CuttingLabel_Optimisation.rpt'
        $reportRecord = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT r.ID AS ReportId, r.PUNKTE_ID AS PrintPointId, p.NAME AS PrintPointName,
       p.STATUS_ID AS PrintPointStatusId, p.TYP AS PrintPointType,
       r.NAME1 AS ReportFile, r.BEZ AS ReportDescription, r.STANDARD AS IsStandard,
       r.PROT_KZ AS ProtocolFlag, r.ROWID AS ReportRowId
FROM SYSADM.DR_REPORTE r
LEFT JOIN SYSADM.DR_DRUCKPUNKTE p ON p.ID=r.PUNKTE_ID
WHERE UPPER(r.NAME1)=UPPER(@ReportFile)
   OR UPPER(r.BEZ) LIKE '%CUTTING LABEL%'
ORDER BY r.PUNKTE_ID, r.ID;
"@ -Parameters @{ ReportFile=$cuttingLabelReportFile }
        Export-ProbeTable -Table $reportRecord -Path (Join-Path $OutputFolder "37-cutting-label-report-record.csv")

        $reportSiblings = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT r.ID AS ReportId, r.PUNKTE_ID AS PrintPointId, p.NAME AS PrintPointName,
       r.NAME1 AS ReportFile, r.BEZ AS ReportDescription, r.STANDARD AS IsStandard,
       r.PROT_KZ AS ProtocolFlag, r.ROWID AS ReportRowId
FROM SYSADM.DR_REPORTE r
LEFT JOIN SYSADM.DR_DRUCKPUNKTE p ON p.ID=r.PUNKTE_ID
WHERE r.PUNKTE_ID IN (
    SELECT PUNKTE_ID FROM SYSADM.DR_REPORTE WHERE UPPER(NAME1)=UPPER(@ReportFile)
)
ORDER BY r.PUNKTE_ID, r.ID;
"@ -Parameters @{ ReportFile=$cuttingLabelReportFile }
        Export-ProbeTable -Table $reportSiblings -Path (Join-Path $OutputFolder "38-cutting-label-output-report-siblings.csv")

        $drPrintConfig = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT d.ID AS PrintConfigId, d.PUNKTE_ID AS PrintPointId, p.NAME AS PrintPointName,
       d.MITARB_ID AS EmployeeId, d.REP_ID1 AS ReportId, r.NAME1 AS ReportFile,
       r.BEZ AS ReportDescription, d.FORMULAR1 AS FormId, d.DEVICE1 AS Device,
       d.DRIVER1 AS Driver, d.PORT1 AS Port, d.ROWID AS PrintConfigRowId
FROM SYSADM.DR_DRUCK d
LEFT JOIN SYSADM.DR_DRUCKPUNKTE p ON p.ID=d.PUNKTE_ID
LEFT JOIN SYSADM.DR_REPORTE r ON r.ID=d.REP_ID1
WHERE d.REP_ID1 IN (SELECT ID FROM SYSADM.DR_REPORTE WHERE UPPER(NAME1)=UPPER(@ReportFile))
   OR d.PUNKTE_ID IN (SELECT PUNKTE_ID FROM SYSADM.DR_REPORTE WHERE UPPER(NAME1)=UPPER(@ReportFile))
ORDER BY d.PUNKTE_ID, d.MITARB_ID, d.ID;
"@ -Parameters @{ ReportFile=$cuttingLabelReportFile }
        Export-ProbeTable -Table $drPrintConfig -Path (Join-Path $OutputFolder "39-cutting-label-dr-druck-config.csv")

        $kaPrintConfig = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT d.ID AS PrintDefinitionId, def.BEZ AS PrintDefinitionDescription, d.SEQ_NR AS SequenceNr,
       d.DEVICE AS Device, d.DRIVER AS Driver, d.PORT AS Port, d.OPTIONS AS Options,
       d.FORMULAR AS FormOrReportId, d.MANDANT AS ClientNo, d.AV_BEREICH AS ProductionArea,
       d.ASK_FOR_DATE AS AskForDate, d.ASK_FOR_ARCHIVE AS AskForArchive, d.ROWID AS DetailRowId
FROM SYSADM.KA_PRINT_DETAIL d
LEFT JOIN SYSADM.KA_PRINT_DEF def ON def.ID=d.ID
WHERE d.FORMULAR IN (SELECT ID FROM SYSADM.DR_REPORTE WHERE UPPER(NAME1)=UPPER(@ReportFile))
   OR UPPER(ISNULL(d.OPTIONS,'')) LIKE '%CUTTING%LABEL%'
   OR UPPER(ISNULL(d.OPTIONS,'')) LIKE '%OPTIM%LABEL%'
ORDER BY d.ID, d.SEQ_NR;
"@ -Parameters @{ ReportFile=$cuttingLabelReportFile }
        Export-ProbeTable -Table $kaPrintConfig -Path (Join-Path $OutputFolder "40-cutting-label-ka-print-config.csv")

        $reportPathSettings = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT 'PROD_PT_PARAMETER' AS SourceObject, 'SERVERVOLUMEPATH' AS SettingName, CONVERT(nvarchar(4000), SERVERVOLUMEPATH) AS SettingValue
FROM SYSADM.PROD_PT_PARAMETER WHERE SERVERVOLUMEPATH IS NOT NULL
UNION ALL
SELECT 'PROD_PT_PARAMETER', 'SERVERUPDATEPATH', CONVERT(nvarchar(4000), SERVERUPDATEPATH)
FROM SYSADM.PROD_PT_PARAMETER WHERE SERVERUPDATEPATH IS NOT NULL
UNION ALL
SELECT 'KA_FIRMA', 'PRINTSERVER', CONVERT(nvarchar(4000), PRINTSERVER)
FROM SYSADM.KA_FIRMA WHERE PRINTSERVER IS NOT NULL
UNION ALL
SELECT 'RR_SITE', 'PATH', CONVERT(nvarchar(4000), PATH)
FROM SYSADM.RR_SITE WHERE PATH IS NOT NULL;
"@
        Export-ProbeTable -Table $reportPathSettings -Path (Join-Path $OutputFolder "41-cutting-label-report-path-settings.csv")

        if ($LocateCrystalReport) {
            $locationRows = New-Object System.Collections.Generic.List[object]
            foreach ($settingRow in $reportPathSettings.Rows) {
                $root = [string]$settingRow.SettingValue
                if ([string]::IsNullOrWhiteSpace($root) -or -not $root.StartsWith("\\")) { continue }
                $candidateFolders = New-Object System.Collections.Generic.List[string]
                $candidateFolders.Add($root)
                foreach ($name in @("Reports", "Report", "Crystal", "Forms", "Form", "Prodman", "Production")) {
                    $candidateFolders.Add((Join-Path $root $name))
                }
                try {
                    foreach ($child in @(Get-ChildItem -LiteralPath $root -Directory -ErrorAction SilentlyContinue | Select-Object -First 40)) {
                        $candidateFolders.Add($child.FullName)
                    }
                }
                catch { }
                foreach ($folder in @($candidateFolders.ToArray() | Select-Object -Unique)) {
                    $candidate = Join-Path $folder $cuttingLabelReportFile
                    $exists = $false
                    try { $exists = Test-Path -LiteralPath $candidate -PathType Leaf } catch { $exists = $false }
                    $locationRows.Add([pscustomobject]@{
                        Root = $root
                        CandidatePath = $candidate
                        Exists = [bool]$exists
                        AccessibleFolder = $(try { Test-Path -LiteralPath $folder -PathType Container } catch { $false })
                    })
                }
            }
            Export-ProbeObjects -Rows $locationRows.ToArray() -Path (Join-Path $OutputFolder "54-cutting-label-crystal-file-locations.csv")
        }

        # The prior query incorrectly required PROD_JOBITEM.OPTIMIZATION to be
        # populated. The authoritative optimization membership is PROD_OPTI_SEQUENCE;
        # enumerate all same-order/item job rows and show which keys actually match.
        $optimizationSourceRows = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT TOP (4000)
       seq.OPTIMIZATION AS Optimization, seq.SEQUENCE AS OptimizationSequence, seq.PLATENR AS PlateNumber,
       seq.AUFNR AS OrderNr, seq.POSNR AS ItemNr, seq.BOM_ID AS SequenceBomId, seq.KEYINDEX AS SequenceKeyIndex,
       ji.JOBNUMBER AS BatchJobNumber, ji.BOM_ID AS JobBomId, ji.KEYINDEX AS JobKeyIndex,
       ji.BOM_NODE AS BomNode, ji.BOM_PRODUKT AS BomProduct, ji.PRODUKTART AS ProductType,
       ji.AGG AS AggregateId, ji.LASTAGG AS LastAggregateId, ji.OPTIMIZATION AS JobItemOptimization,
       ji.SEQUENCE_OPTIRUN AS OptimizationRunSequence, ji.STACKNUMBER AS StackNumber, ji.STACKPOSITION AS StackPosition,
       ji.LOGICALRACK AS LogicalRack, ji.RACK AS Rack, ji.NV_SORTID AS SortId, ji.NV_NAME AS SortName,
       CASE WHEN ji.BOM_ID=seq.BOM_ID THEN 1 ELSE 0 END AS BomMatches,
       CASE WHEN ji.KEYINDEX=seq.KEYINDEX THEN 1 ELSE 0 END AS KeyIndexMatches,
       CASE WHEN ji.OPTIMIZATION=seq.OPTIMIZATION THEN 1 ELSE 0 END AS JobOptimizationMatches
FROM SYSADM.PROD_OPTI_SEQUENCE seq
LEFT JOIN SYSADM.PROD_JOBITEM ji ON ji.AUFNR=seq.AUFNR AND ji.POSNR=seq.POSNR
WHERE CONVERT(nvarchar(64), seq.OPTIMIZATION)=@OptimizationNumber
  AND (@OrderNumber='' OR CONVERT(nvarchar(64), seq.AUFNR)=@OrderNumber)
  AND (@ItemNumber='' OR CONVERT(nvarchar(64), seq.POSNR)=@ItemNumber)
ORDER BY seq.SEQUENCE, seq.AUFNR, seq.POSNR, BomMatches DESC, KeyIndexMatches DESC, JobOptimizationMatches DESC, ji.JOBNUMBER DESC, ji.BOM_ID;
"@ -Parameters $optimizationParams
        Export-ProbeTable -Table $optimizationSourceRows -Path (Join-Path $OutputFolder "42-selected-optimization-source-rows.csv")

        if (-not [string]::IsNullOrWhiteSpace($OrderNumber)) {
            $barcodeEvidence = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT 'BW_AUFTR_POS_EX' AS SourceObject, x.ID AS OrderNr, x.POS_NR AS ItemNr, CAST(NULL AS int) AS BomId,
       x.BARCODE_START AS BarcodeValue, x.BARCODE_TYPE AS BarcodeType, x.EAN AS EanValue,
       CAST(NULL AS decimal(18,4)) AS LabelNumberFrom, CAST(NULL AS decimal(18,4)) AS LabelNumberTo, CAST(NULL AS datetime) AS EventTime
FROM SYSADM.BW_AUFTR_POS_EX x WHERE CONVERT(nvarchar(64),x.ID)=@OrderNumber AND (@ItemNumber='' OR CONVERT(nvarchar(64),x.POS_NR)=@ItemNumber)
UNION ALL
SELECT 'BW_AUFTR_STKL', s.ID, s.POS_NR, s.BOM_ID, s.BARCODE_START, s.BARCODE_TYPE, s.EAN, NULL, NULL, NULL
FROM SYSADM.BW_AUFTR_STKL s WHERE CONVERT(nvarchar(64),s.ID)=@OrderNumber AND (@ItemNumber='' OR CONVERT(nvarchar(64),s.POS_NR)=@ItemNumber)
UNION ALL
SELECT 'FS_POS', f.ID, f.POS_NR, NULL, f.BARCODE_START, f.BARCODE_TYPE, NULL, NULL, NULL, NULL
FROM SYSADM.FS_POS f WHERE CONVERT(nvarchar(64),f.ID)=@OrderNumber AND (@ItemNumber='' OR CONVERT(nvarchar(64),f.POS_NR)=@ItemNumber)
UNION ALL
SELECT 'FS_BOOK_HISTORY', b.ID, b.POSNR, b.BOMID, b.BARCODE, NULL, NULL, NULL, NULL, b.SCANTIME
FROM SYSADM.FS_BOOK_HISTORY b WHERE CONVERT(nvarchar(64),b.ID)=@OrderNumber AND (@ItemNumber='' OR CONVERT(nvarchar(64),b.POSNR)=@ItemNumber) AND NULLIF(LTRIM(RTRIM(ISNULL(b.BARCODE,''))),'') IS NOT NULL
UNION ALL
SELECT 'BW_ALCIM_RECEIVE', a.HAUPT_AUFTR, a.HAUPT_POS, a.BOM_ID, NULL, NULL, NULL, a.ETIK_NR_VON, a.ETIK_NR_BIS, CAST(a.PROD_DATUM AS datetime)
FROM SYSADM.BW_ALCIM_RECEIVE a WHERE CONVERT(nvarchar(64),a.HAUPT_AUFTR)=@OrderNumber AND (@ItemNumber='' OR CONVERT(nvarchar(64),a.HAUPT_POS)=@ItemNumber)
ORDER BY SourceObject, BomId, EventTime;
"@ -Parameters @{ OrderNumber=$OrderNumber; ItemNumber=$ItemNumber }
            Export-ProbeTable -Table $barcodeEvidence -Path (Join-Path $OutputFolder "43-selected-order-barcode-evidence.csv")
        }

        $productionCandidates = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT TOP (4000)
       seq.OPTIMIZATION AS Optimization, seq.SEQUENCE AS OptimizationSequence, seq.AUFNR AS OrderNr, seq.POSNR AS ItemNr,
       jps.JOBNUMBER AS BatchJobNumber, jps.LOTTYPE AS LotType, jps.PRODUCTIONSEQUENCE AS ProductionSequence,
       jps.BOM_ID AS BomId, jps.MENGE AS Quantity, jps.KEYINDEX AS KeyIndex, jps.ROWID AS SourceRowId
FROM SYSADM.PROD_OPTI_SEQUENCE seq
JOIN SYSADM.PROD_JOBPRODSEQ jps ON jps.AUFNR=seq.AUFNR AND jps.POSNR=seq.POSNR
WHERE CONVERT(nvarchar(64), seq.OPTIMIZATION)=@OptimizationNumber
  AND (@OrderNumber='' OR CONVERT(nvarchar(64), seq.AUFNR)=@OrderNumber)
  AND (@ItemNumber='' OR CONVERT(nvarchar(64), seq.POSNR)=@ItemNumber)
ORDER BY seq.SEQUENCE, jps.JOBNUMBER, jps.PRODUCTIONSEQUENCE, jps.BOM_ID;
"@ -Parameters $optimizationParams
        Export-ProbeTable -Table $productionCandidates -Path (Join-Path $OutputFolder "44-selected-optimization-production-candidates.csv")

        # v0.496: Optimization lifecycle discovery. Do not translate STATUS codes
        # into user-facing words until the live A+W installation proves the mapping.
        # Compare the live optimization row with the statistics/archive table because
        # A+W may retain booked/completed runs there after they leave the active set.
        $optimizationLifecycle = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT 'PROD_OPTIMIZATION' AS SourceObject,
       o.OPTIMIZATION AS Optimization,
       CAST(NULL AS int) AS StatisticsId,
       CAST(NULL AS int) AS OptimizationNumber,
       o.PRODUKT AS ProductId,
       o.PRODUKT_BEZ AS ProductDescription,
       o.AGG AS AggregateId,
       o.OPTIDATE AS OptimizationDate,
       o.OPTIMODE AS OptimizationMode,
       o.STATUS AS StatusCode,
       o.SHEETCOUNT AS SheetCount,
       o.RESULT AS Result,
       o.RESULTWITHTRIM AS ResultWithTrim,
       DATALENGTH(o.SAVEFILE) AS SaveFileBytes,
       o.LASTCHANGEDATE AS LastChangeDate,
       o.LASTCHANGEUSER AS LastChangeUser,
       o.ROWID AS SourceRowId
FROM SYSADM.PROD_OPTIMIZATION o
WHERE CONVERT(nvarchar(64),o.OPTIMIZATION)=@OptimizationNumber
UNION ALL
SELECT 'PROD_OPTI_STATISTICS',
       s.OPTIMIZATION,
       s.ID,
       s.OPTIMIZATION_NUMBER,
       s.PRODUKT,
       s.PRODUKT_BEZ,
       s.AGG,
       s.OPTIDATE,
       s.OPTIMODE,
       s.STATUS,
       s.SHEETCOUNT,
       s.RESULT,
       s.RESULTWITHTRIM,
       DATALENGTH(s.SAVEFILE),
       s.LASTCHANGEDATE,
       s.LASTCHANGEUSER,
       s.ROWID
FROM SYSADM.PROD_OPTI_STATISTICS s
WHERE CONVERT(nvarchar(64),s.OPTIMIZATION)=@OptimizationNumber
   OR CONVERT(nvarchar(64),s.OPTIMIZATION_NUMBER)=@OptimizationNumber
ORDER BY SourceObject, LastChangeDate, StatisticsId;
"@ -Parameters @{ OptimizationNumber=$OptimizationNumber }
        Export-ProbeTable -Table $optimizationLifecycle -Path (Join-Path $OutputFolder "45-selected-optimization-lifecycle.csv")

        $optimizationStatusSummary = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT q.SourceObject, q.StatusCode, q.OptimizationMode, q.AggregateId,
       COUNT(*) AS [RowCount],
       MIN(q.OptimizationDate) AS FirstOptimizationDate,
       MAX(q.OptimizationDate) AS LastOptimizationDate,
       MAX(q.LastChangeDate) AS LatestChangeDate,
       MIN(q.OptimizationId) AS SampleOptimizationMin,
       MAX(q.OptimizationId) AS SampleOptimizationMax
FROM (
    SELECT 'PROD_OPTIMIZATION' AS SourceObject,
           o.STATUS AS StatusCode,
           o.OPTIMODE AS OptimizationMode,
           o.AGG AS AggregateId,
           o.OPTIDATE AS OptimizationDate,
           o.LASTCHANGEDATE AS LastChangeDate,
           o.OPTIMIZATION AS OptimizationId
    FROM SYSADM.PROD_OPTIMIZATION o
    WHERE COALESCE(o.LASTCHANGEDATE,o.OPTIDATE) >= DATEADD(day,-120,GETDATE())
    UNION ALL
    SELECT 'PROD_OPTI_STATISTICS',
           s.STATUS,
           s.OPTIMODE,
           s.AGG,
           s.OPTIDATE,
           s.LASTCHANGEDATE,
           COALESCE(s.OPTIMIZATION,s.OPTIMIZATION_NUMBER)
    FROM SYSADM.PROD_OPTI_STATISTICS s
    WHERE COALESCE(s.LASTCHANGEDATE,s.OPTIDATE) >= DATEADD(day,-120,GETDATE())
) AS q
GROUP BY q.SourceObject, q.StatusCode, q.OptimizationMode, q.AggregateId
ORDER BY q.SourceObject, q.StatusCode, q.OptimizationMode, q.AggregateId;
"@
        Export-ProbeTable -Table $optimizationStatusSummary -Path (Join-Path $OutputFolder "46-recent-optimization-status-summary.csv")

        $optimizationStatusColumns = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT s.name AS SchemaName, o.name AS ObjectName, o.type_desc AS ObjectType,
       c.column_id AS ColumnOrder, c.name AS ColumnName, t.name AS DataType, c.max_length AS MaxLength
FROM sys.objects o
JOIN sys.schemas s ON s.schema_id=o.schema_id
JOIN sys.columns c ON c.object_id=o.object_id
JOIN sys.types t ON t.user_type_id=c.user_type_id
WHERE s.name=@Schema AND o.type IN ('U','V')
  AND (UPPER(o.name) LIKE '%OPTI%' OR UPPER(o.name) LIKE '%PROD_JOB%' OR UPPER(o.name)='PROD_LISTSTATE')
  AND (UPPER(c.name) LIKE '%STATUS%' OR UPPER(c.name) LIKE '%STATE%' OR UPPER(c.name) LIKE '%BOOK%'
       OR UPPER(c.name) LIKE '%RELEASE%' OR UPPER(c.name) LIKE '%FREI%' OR UPPER(c.name) LIKE '%BUCH%'
       OR UPPER(c.name) LIKE '%DATE%' OR UPPER(c.name) LIKE '%CHANGE%')
ORDER BY o.name, c.column_id;
"@ -Parameters @{ Schema=$schema }
        Export-ProbeTable -Table $optimizationStatusColumns -Path (Join-Path $OutputFolder "47-optimization-status-candidate-columns.csv")

        $statusTextHits = New-Object System.Collections.Generic.List[object]
        $statusTextObjects = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT DISTINCT s.name AS SchemaName, o.name AS ObjectName
FROM sys.objects o
JOIN sys.schemas s ON s.schema_id=o.schema_id
JOIN sys.columns c ON c.object_id=o.object_id
JOIN sys.types t ON t.user_type_id=c.user_type_id
WHERE s.name=@Schema AND o.type IN ('U','V')
  AND (UPPER(o.name) LIKE 'PROD_OPTI%' OR UPPER(o.name) IN ('PROD_LISTSTATE','PROD_JOB','PROD_REPORT_TEXT'))
  AND t.name IN ('varchar','nvarchar','char','nchar','text','ntext','xml')
ORDER BY o.name;
"@ -Parameters @{ Schema=$schema }
        foreach ($candidate in $statusTextObjects.Rows) {
            $hits = Find-ProbeTextHits -Connection $connection -SchemaName ([string]$candidate.SchemaName) -ObjectName ([string]$candidate.ObjectName) -Needles @('Optimized','Optimised','Released','Booked','Release','Book','Freigegeben','Gebucht','Optimiert')
            foreach ($hit in $hits) { $statusTextHits.Add($hit) }
        }
        Export-ProbeObjects -Rows $statusTextHits.ToArray() -Path (Join-Path $OutputFolder "48-optimization-status-text-hits.csv")

        # Keep the three core identity paths separate. This makes it obvious whether
        # a missing join is caused by sequence retention, job-item retention, or the
        # optional optimization number copied onto PROD_JOBITEM.
        $optimizationSequenceRaw = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT TOP (4000) seq.OPTIMIZATION AS Optimization, seq.SEQUENCE AS OptimizationSequence,
       seq.AUFNR AS OrderNr, seq.POSNR AS ItemNr, seq.BOM_ID AS BomId,
       seq.BOM_NODE AS BomNode, seq.KEYINDEX AS KeyIndex, seq.PLATENR AS PlateNumber,
       seq.ROWID AS SourceRowId
FROM SYSADM.PROD_OPTI_SEQUENCE seq
WHERE CONVERT(nvarchar(64),seq.OPTIMIZATION)=@OptimizationNumber
ORDER BY seq.SEQUENCE, seq.AUFNR, seq.POSNR, seq.BOM_ID, seq.KEYINDEX;
"@ -Parameters @{ OptimizationNumber=$OptimizationNumber }
        Export-ProbeTable -Table $optimizationSequenceRaw -Path (Join-Path $OutputFolder "49-selected-optimization-sequence-raw.csv")

        if (-not [string]::IsNullOrWhiteSpace($OrderNumber)) {
            $orderJobItemsRaw = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT TOP (4000) ji.AUFNR AS OrderNr, ji.POSNR AS ItemNr, ji.BOM_ID AS BomId,
       ji.KEYINDEX AS KeyIndex, ji.BOM_NODE AS BomNode, ji.JOBNUMBER AS BatchJobNumber,
       j.STATUS AS BatchStatusCode, j.DESCRIPTION AS BatchDescription,
       j.CREATIONDATE AS BatchCreationDate, j.MITARB_ID AS BatchEmployee,
       j.LASTCHANGEDATE AS BatchLastChangeDate, j.LASTCHANGEUSER AS BatchLastChangeUser,
       ji.OPTIMIZATION AS JobItemOptimization, ji.SEQUENCE_OPTIRUN AS OptimizationRunSequence,
       ji.STACKNUMBER AS StackNumber, ji.STACKPOSITION AS StackPosition,
       ji.MENGE AS Quantity, ji.MENGE_CUT AS CutQuantity, ji.AGG AS AggregateId,
       ji.LASTAGG AS LastAggregateId, ji.ROWID AS JobItemRowId
FROM SYSADM.PROD_JOBITEM ji
LEFT JOIN SYSADM.PROD_JOB j ON j.JOBNUMBER=ji.JOBNUMBER
WHERE CONVERT(nvarchar(64),ji.AUFNR)=@OrderNumber
  AND (@ItemNumber='' OR CONVERT(nvarchar(64),ji.POSNR)=@ItemNumber)
ORDER BY ji.JOBNUMBER DESC, ji.BOM_ID, ji.KEYINDEX;
"@ -Parameters @{ OrderNumber=$OrderNumber; ItemNumber=$ItemNumber }
            Export-ProbeTable -Table $orderJobItemsRaw -Path (Join-Path $OutputFolder "50-selected-order-jobitems-raw.csv")

            $batchStatus = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT DISTINCT j.JOBNUMBER AS BatchJobNumber, j.DESCRIPTION AS BatchDescription,
       j.STATUS AS BatchStatusCode, j.PARTIALDELIVERED AS PartialDelivered,
       j.CREATIONDATE AS BatchCreationDate, j.MITARB_ID AS BatchEmployee,
       j.LASTCHANGEDATE AS BatchLastChangeDate, j.LASTCHANGEUSER AS BatchLastChangeUser,
       ji.OPTIMIZATION AS JobItemOptimization, ji.SEQUENCE_OPTIRUN AS OptimizationRunSequence,
       ji.NV_SORTID AS SortId, ji.NV_NAME AS SortName
FROM SYSADM.PROD_JOBITEM ji
JOIN SYSADM.PROD_JOB j ON j.JOBNUMBER=ji.JOBNUMBER
WHERE CONVERT(nvarchar(64),ji.AUFNR)=@OrderNumber
  AND (@ItemNumber='' OR CONVERT(nvarchar(64),ji.POSNR)=@ItemNumber)
ORDER BY j.JOBNUMBER DESC, ji.OPTIMIZATION, ji.SEQUENCE_OPTIRUN;
"@ -Parameters @{ OrderNumber=$OrderNumber; ItemNumber=$ItemNumber }
            Export-ProbeTable -Table $batchStatus -Path (Join-Path $OutputFolder "51-selected-order-batch-status.csv")

            $cuttingBookings = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT TOP (1000) b.ID AS OrderNr, b.POSNR AS ItemNr, b.BOMID AS BomId,
       b.SCANTIME AS BookingTime, b.BOOK_TYPE AS BookType, b.ORIGIN AS BookingOrigin,
       b.AMOUNT AS BookedAmount, b.MITARB_ID AS EmployeeId, b.REG_POINT AS RegistrationPointId,
       pp.BEZ AS RegistrationPoint, b.WORK_TYPE AS WorkTypeId, wt.BEA_TYPBEZ AS WorkType,
       b.BREAKAGE_REASON AS BreakageReason, b.BREAKAGE_CAUSER AS BreakageCauser,
       b.BARCODE AS Barcode, b.ROWID AS BookingRowId
FROM SYSADM.FS_BOOK_HISTORY b
LEFT JOIN SYSADM.PD_PROD_POINT pp ON CONVERT(nvarchar(64),pp.FREMD_KEY)=CONVERT(nvarchar(64),b.REG_POINT)
LEFT JOIN SYSADM.ZW_BEATYPEN wt ON wt.BEA_TYP=b.WORK_TYPE
WHERE CONVERT(nvarchar(64),b.ID)=@OrderNumber
  AND (@ItemNumber='' OR CONVERT(nvarchar(64),b.POSNR)=@ItemNumber)
ORDER BY b.SCANTIME, b.BOMID, b.WORK_TYPE, b.REG_POINT;
"@ -Parameters @{ OrderNumber=$OrderNumber; ItemNumber=$ItemNumber }
            Export-ProbeTable -Table $cuttingBookings -Path (Join-Path $OutputFolder "52-selected-order-production-bookings.csv")
        }

        $optimizationStatusModules = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT TOP (300) s.name AS SchemaName, o.name AS ObjectName, o.type_desc AS ObjectType,
       CASE WHEN UPPER(m.definition) LIKE '%PROD_OPTIMIZATION%' THEN 1 ELSE 0 END AS ReferencesOptimization,
       CASE WHEN UPPER(m.definition) LIKE '%PROD_OPTI_STATISTICS%' THEN 1 ELSE 0 END AS ReferencesOptimizationStatistics,
       CASE WHEN UPPER(m.definition) LIKE '%STATUS%' THEN 1 ELSE 0 END AS ReferencesStatus,
       CASE WHEN UPPER(m.definition) LIKE '%RELEASE%' OR UPPER(m.definition) LIKE '%FREIG%' THEN 1 ELSE 0 END AS ReferencesRelease,
       CASE WHEN UPPER(m.definition) LIKE '%BOOK%' OR UPPER(m.definition) LIKE '%BUCH%' THEN 1 ELSE 0 END AS ReferencesBook,
       LEFT(REPLACE(REPLACE(m.definition,CHAR(13),' '),CHAR(10),' '),12000) AS DefinitionPreview
FROM sys.sql_modules m
JOIN sys.objects o ON o.object_id=m.object_id
JOIN sys.schemas s ON s.schema_id=o.schema_id
WHERE s.name=@Schema
  AND (UPPER(m.definition) LIKE '%PROD_OPTIMIZATION%' OR UPPER(m.definition) LIKE '%PROD_OPTI_STATISTICS%')
ORDER BY o.type_desc, o.name;
"@ -Parameters @{ Schema=$schema }
        Export-ProbeTable -Table $optimizationStatusModules -Path (Join-Path $OutputFolder "53-optimization-status-module-references.csv")
    }

    $captureScreen = [bool]($CaptureCuttingLabelsScreen -or $CaptureCuttingLabels)
    if ($captureScreen) {
        Write-Host ""
        Write-Host "Interactive Cutting Labels SCREEN capture" -ForegroundColor Cyan
        Write-Host "In A+W Business Pro: Production Manager -> Optimization Overview -> select optimization -> Output." -ForegroundColor Gray
        Write-Host "Uncheck every report except Cutting Labels. Do NOT click Execute." -ForegroundColor Yellow
        Write-Host "This capture uses the Screen preview only and does not intentionally advance cutting/production." -ForegroundColor Yellow
        [void](Read-Host "Press Enter here when the Output tab is prepared")

        $captureBaseline = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT GETDATE() AS CaptureStart,
       (SELECT ISNULL(MAX(JOB_ID),0) FROM SYSADM.BW_PRINT_JOBS) AS MaxPrintJobId,
       (SELECT ISNULL(MAX(ID),0) FROM SYSADM.FS_POOL_KOPF) AS MaxPoolId;
"@
        Export-ProbeTable -Table $captureBaseline -Path (Join-Path $OutputFolder "25-cutting-label-capture-baseline.csv")
        $captureStartValue = [datetime]$captureBaseline.Rows[0].CaptureStart
        $captureStart = $captureStartValue.ToString("yyyy-MM-ddTHH:mm:ss.fff")
        $maxPrintJobId = [string]$captureBaseline.Rows[0].MaxPrintJobId
        $maxPoolId = [string]$captureBaseline.Rows[0].MaxPoolId
        Export-ProbeObjects -Rows (Get-AwBusinessProProcesses) -Path (Join-Path $OutputFolder "30-aw-business-pro-processes.csv")

        Write-Host "Baseline captured. Click SCREEN in A+W now with only Cutting Labels selected." -ForegroundColor Green
        Write-Host "Wait for the Cutting Labels preview window to finish opening. Do not click Execute." -ForegroundColor Yellow
        [void](Read-Host "Press Enter after the Cutting Labels screen preview is open")

        $captureParams = @{ MaxPrintJobId=$maxPrintJobId; MaxPoolId=$maxPoolId; CaptureStart=$captureStart }
        $newPrintJobs = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT * FROM SYSADM.BW_PRINT_JOBS
WHERE JOB_ID > @MaxPrintJobId
ORDER BY JOB_ID;
"@ -Parameters $captureParams
        Export-ProbeTable -Table $newPrintJobs -Path (Join-Path $OutputFolder "26-cutting-label-new-print-jobs.csv")

        $newPool = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT h.ID, h.DATEI_NAME, h.TYP, h.DATUM_ERSTELLT, h.DATUM_IMPORTIERT, h.DATUM_VERARBEITET,
       h.STATUS, h.BENUTZER, h.MITARB, p.SEQUENZ_NR, p.STATUS AS PoolStatus, p.INDEXFELD1,
       LEN(p.DATENSATZ) AS DataLength, LEFT(p.DATENSATZ,12000) AS DataPreview
FROM SYSADM.FS_POOL_KOPF h
LEFT JOIN SYSADM.FS_POOL p ON p.ID=h.ID
WHERE h.ID > @MaxPoolId
ORDER BY h.ID, p.SEQUENZ_NR;
"@ -Parameters $captureParams
        Export-ProbeTable -Table $newPool -Path (Join-Path $OutputFolder "27-cutting-label-new-pool-rows.csv")

        $newPoolLog = Invoke-ProbeQuery -Connection $connection -Query @"
SELECT TOP (1000) * FROM SYSADM.FS_POOL_LOG
WHERE ID > @MaxPoolId OR ZEITSTEMPEL >= CONVERT(datetime, @CaptureStart, 126)
ORDER BY ZEITSTEMPEL, ID, SEQUENZ_NR;
"@ -Parameters $captureParams
        Export-ProbeTable -Table $newPoolLog -Path (Join-Path $OutputFolder "28-cutting-label-new-pool-log.csv")

        # Screen preview may be rendered entirely by the A+W client without a SQL
        # queue record. Capture recently-created/modified temp files as metadata
        # only so we can identify the preview/report format safely on the next pass.
        Export-ProbeObjects -Rows (Get-CuttingLabelPreviewTempFiles -Since $captureStartValue) -Path (Join-Path $OutputFolder "29-cutting-label-screen-temp-files.csv")
    }

    @(
        "A+W Glass Label / Optimization Discovery Probe",
        "Server: $($connection.DataSource)",
        "Database: $($connection.Database)",
        "Schema: $schema",
        "Known optimized order: $OrderNumber",
        "Known optimized item: $ItemNumber",
        "Optimization number: $OptimizationNumber",
        "Capture Cutting Labels Screen action: $captureScreen",
        "Locate Crystal report on configured UNC roots: $LocateCrystalReport",
        "Safety: SELECT-only; READ UNCOMMITTED; no A+W writes.",
        "Best next evidence: 45-selected-optimization-lifecycle.csv through 53-optimization-status-module-references.csv. These outputs prove optimization/batch lifecycle before any scanner Cutting progress state is implemented; the exact Cutting Labels Crystal report remains Prodman_CuttingLabel_Optimisation.rpt (DR_REPORTE ID 846 / print point 846)."
    ) | Set-Content -LiteralPath (Join-Path $OutputFolder "README.txt") -Encoding UTF8

    Write-Host ""
    Write-Host "Glass label discovery probe completed." -ForegroundColor Green
    Write-Host "Results folder: $OutputFolder" -ForegroundColor Cyan
}
catch {
    $errorPath = Join-Path $OutputFolder "PROBE-ERROR.txt"
    @("GLASS LABEL PROBE FAILED", $_.Exception.Message, $_.ScriptStackTrace) | Set-Content -LiteralPath $errorPath -Encoding UTF8
    Write-Host ""
    Write-Host "GLASS LABEL PROBE FAILED" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host "Details: $errorPath" -ForegroundColor Yellow
    exit 1
}
finally {
    if ($null -ne $connection) {
        if ($connection.State -ne [System.Data.ConnectionState]::Closed) { $connection.Close() }
        $connection.Dispose()
    }
}
