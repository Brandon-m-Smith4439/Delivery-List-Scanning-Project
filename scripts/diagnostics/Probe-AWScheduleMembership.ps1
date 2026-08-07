[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$server = "SQLAWGLASS"
$database = "BFSMAIN"
$defaultOrderNumbers = "236879,236880,236881,236882,236883,236884,236885,236886"

$dateText = (
    Read-Host "Enter the Crystal delivery-list date to compare (MM/DD/YYYY)"
).Trim()
$orderText = (
    Read-Host "Enter comma-separated A+W order numbers, or press Enter for the known 8/3 comparison set [$defaultOrderNumbers]"
).Trim()
if ([string]::IsNullOrWhiteSpace($orderText)) {
    $orderText = $defaultOrderNumbers
}

$formats = [string[]]@(
    "MM/dd/yyyy",
    "M/d/yyyy",
    "MM/d/yyyy",
    "M/dd/yyyy",
    "yyyy-MM-dd"
)

try {
    $deliveryDate = [datetime]::ParseExact(
        $dateText,
        $formats,
        [Globalization.CultureInfo]::InvariantCulture,
        [Globalization.DateTimeStyles]::AllowWhiteSpaces
    )
}
catch {
    throw "The date must be entered as MM/DD/YYYY or YYYY-MM-DD."
}

$orderNumbers = @(
    $orderText -split ',' |
        ForEach-Object { $_.Trim() } |
        Where-Object { $_ -match '^\d+$' } |
        Sort-Object -Unique
)
if ($orderNumbers.Count -eq 0) {
    throw "Enter at least one numeric order number."
}
$orderSql = $orderNumbers -join ","

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$desktop = [Environment]::GetFolderPath("Desktop")
$outputFolder = Join-Path $desktop "AW-Schedule-Membership-Probe-$timestamp"
New-Item -ItemType Directory -Path $outputFolder -Force | Out-Null

$connectionString = @"
Server=$server;
Database=$database;
Integrated Security=True;
Application Name=DeliveryListScheduleMembershipProbe;
Connect Timeout=15;
Encrypt=False;
TrustServerCertificate=True;
"@

$connection = New-Object System.Data.SqlClient.SqlConnection($connectionString)

function Export-Query {
    param(
        [Parameter(Mandatory = $true)][string]$FileName,
        [Parameter(Mandatory = $true)][string]$Query,
        [switch]$UseDeliveryDate
    )

    $outputPath = Join-Path $outputFolder $FileName
    $errorPath = "$outputPath.error.txt"
    $command = $connection.CreateCommand()
    $command.CommandText = $Query
    $command.CommandTimeout = 120

    if ($UseDeliveryDate) {
        $parameter = $command.Parameters.Add("@DeliveryDate", [System.Data.SqlDbType]::Date)
        $parameter.Value = $deliveryDate.Date
    }

    $adapter = New-Object System.Data.SqlClient.SqlDataAdapter($command)
    $table = New-Object System.Data.DataTable
    try {
        [void]$adapter.Fill($table)
        if ($table.Rows.Count -gt 0) {
            $table |
                Export-Csv -LiteralPath $outputPath -NoTypeInformation -Encoding UTF8
        }
        else {
            "No rows returned." |
                Set-Content -LiteralPath $outputPath -Encoding UTF8
        }
        Write-Host ("Created {0} - {1} rows" -f $FileName, $table.Rows.Count) -ForegroundColor Green
    }
    catch {
        $_.Exception.ToString() |
            Set-Content -LiteralPath $errorPath -Encoding UTF8
        Write-Host ("Query failed for {0}. See {1}" -f $FileName, $errorPath) -ForegroundColor Yellow
    }
    finally {
        $table.Dispose()
        $adapter.Dispose()
        $command.Dispose()
    }
}

try {
    Write-Host ""
    Write-Host "Opening read-only A+W SQL connection..." -ForegroundColor Cyan
    $connection.Open()
    Write-Host "Connected successfully." -ForegroundColor Green
    Write-Host "Delivery date: $($deliveryDate.ToString('yyyy-MM-dd'))"
    Write-Host "Orders: $($orderNumbers -join ', ')"
    Write-Host ""

    Export-Query `
        -FileName "01-membership-object-columns.csv" `
        -Query @"
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
INNER JOIN sys.schemas s
    ON s.schema_id = o.schema_id
INNER JOIN sys.columns c
    ON c.object_id = o.object_id
INNER JOIN sys.types t
    ON t.user_type_id = c.user_type_id
WHERE s.name = 'SYSADM'
  AND o.name IN (
        'POOL_TEILE',
        'BW_LADELISTE',
        'TEMP_DELIV',
        'BW_AUFTR_KOPF',
        'BW_AUFTR_POS'
  )
ORDER BY
    o.name,
    c.column_id;
"@

    Export-Query `
        -FileName "02-target-order-status-and-ladeliste.csv" `
        -Query @"
SELECT
    h.ID AS OrderNumber,
    p.POS_NR AS ItemNumber,
    h.DATUM_LIEFER_PLAN AS PlannedDeliveryDate,
    h.STATUS AS OrderStatus,
    p.POS_STATUS AS ItemStatus,
    h.LADELISTE AS HeaderDeliveryListNumber,
    h.LAUF_PROD1 AS ProductionBatch1,
    h.LAUF_PROD2 AS ProductionBatch2,
    h.LAUF_PROD3 AS ProductionBatch3,
    h.BIT AS HeaderBit,
    h.BEST_TEXT1 AS JobNumber,
    p.PP_MENGE AS Quantity,
    p.PP_BREITE AS Width32nds,
    p.PP_HOEHE AS Height32nds,
    p.PROD_BEZ1 AS ProductDescription
FROM SYSADM.BW_AUFTR_KOPF h
INNER JOIN SYSADM.BW_AUFTR_POS p
    ON p.ID = h.ID
WHERE h.ID IN ($orderSql)
ORDER BY
    h.ID,
    p.POS_NR;
"@

    Export-Query `
        -FileName "03-target-pool-teile-membership.csv" `
        -Query @"
SELECT
    pt.LAUF AS ScheduleRun,
    pt.AUFTNR AS OrderNumber,
    pt.POS AS ItemNumber,
    pt.TEILE_NR AS PartNumber
FROM SYSADM.POOL_TEILE pt
WHERE pt.AUFTNR IN ($orderSql)
ORDER BY
    pt.AUFTNR,
    pt.POS,
    pt.LAUF,
    pt.TEILE_NR;
"@

    Export-Query `
        -FileName "04-target-zero-part-schedule-membership.csv" `
        -Query @"
SELECT DISTINCT
    pt.LAUF AS ScheduleRun,
    pt.AUFTNR AS OrderNumber,
    pt.POS AS ItemNumber,
    pt.TEILE_NR AS PartNumber,
    h.DATUM_LIEFER_PLAN AS PlannedDeliveryDate,
    h.LADELISTE AS HeaderDeliveryListNumber,
    h.STATUS AS OrderStatus,
    p.POS_STATUS AS ItemStatus,
    h.LAUF_PROD1 AS ProductionBatch1,
    h.LAUF_PROD2 AS ProductionBatch2,
    h.LAUF_PROD3 AS ProductionBatch3
FROM SYSADM.POOL_TEILE pt
INNER JOIN SYSADM.BW_AUFTR_KOPF h
    ON h.ID = pt.AUFTNR
INNER JOIN SYSADM.BW_AUFTR_POS p
    ON p.ID = pt.AUFTNR
   AND p.POS_NR = pt.POS
WHERE pt.AUFTNR IN ($orderSql)
  AND pt.TEILE_NR = 0
ORDER BY
    pt.AUFTNR,
    pt.POS,
    pt.LAUF;
"@

    Export-Query `
        -FileName "05-date-zero-part-schedule-membership.csv" `
        -UseDeliveryDate `
        -Query @"
SELECT DISTINCT
    pt.LAUF AS ScheduleRun,
    pt.AUFTNR AS OrderNumber,
    pt.POS AS ItemNumber,
    pt.TEILE_NR AS PartNumber,
    h.DATUM_LIEFER_PLAN AS PlannedDeliveryDate,
    h.LADELISTE AS HeaderDeliveryListNumber,
    h.STATUS AS OrderStatus,
    p.POS_STATUS AS ItemStatus,
    h.BIT AS HeaderBit,
    h.BEST_TEXT1 AS JobNumber
FROM SYSADM.POOL_TEILE pt
INNER JOIN SYSADM.BW_AUFTR_KOPF h
    ON h.ID = pt.AUFTNR
INNER JOIN SYSADM.BW_AUFTR_POS p
    ON p.ID = pt.AUFTNR
   AND p.POS_NR = pt.POS
WHERE h.DATUM_LIEFER_PLAN = @DeliveryDate
  AND pt.TEILE_NR = 0
ORDER BY
    pt.LAUF,
    pt.AUFTNR,
    pt.POS;
"@

    Export-Query `
        -FileName "06-bw-ladeliste-sample.csv" `
        -Query @"
SELECT TOP (500)
    *
FROM SYSADM.BW_LADELISTE;
"@

    Export-Query `
        -FileName "07-temp-deliv-sample.csv" `
        -Query @"
SELECT TOP (500)
    *
FROM SYSADM.TEMP_DELIV;
"@

    $summary = @"
A+W schedule-membership probe
Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Delivery date: $($deliveryDate.ToString("yyyy-MM-dd"))
Orders: $($orderNumbers -join ", ")
SQL login: $([System.Security.Principal.WindowsIdentity]::GetCurrent().Name)

Purpose:
Compare raw order status with actual schedule/run membership. Production status
must not be used as delivery-list membership. The most important outputs are
03-target-pool-teile-membership.csv and 04-target-zero-part-schedule-membership.csv.

All queries were SELECT-only.
No A+W data or database objects were modified.
"@
    $summary |
        Set-Content -LiteralPath (Join-Path $outputFolder "README.txt") -Encoding UTF8

    Write-Host ""
    Write-Host "Probe completed." -ForegroundColor Green
    Write-Host "Results folder:"
    Write-Host $outputFolder -ForegroundColor Cyan
}
catch {
    Write-Host ""
    Write-Host "PROBE FAILED" -ForegroundColor Red
    Write-Host $_.Exception.Message
}
finally {
    if ($null -ne $connection) {
        if ($connection.State -ne [System.Data.ConnectionState]::Closed) {
            $connection.Close()
        }
        $connection.Dispose()
    }
}

Write-Host ""
Read-Host "Press Enter to close"
