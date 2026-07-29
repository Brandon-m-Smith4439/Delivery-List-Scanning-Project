# File: scripts/diagnostics/Probe-AWDeliveryList.ps1
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$server = "SQLAWGLASS"
$database = "BFSMAIN"

$dateText = (
    Read-Host "Enter a delivery date that has a known manual Crystal export (MM/DD/YYYY)"
).Trim()

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

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$desktop = [Environment]::GetFolderPath("Desktop")

$outputFolder = Join-Path `
    $desktop `
    "AW-DeliveryList-Probe-$timestamp"

New-Item `
    -ItemType Directory `
    -Path $outputFolder `
    -Force |
    Out-Null

$connectionString = @"
Server=$server;
Database=$database;
Integrated Security=True;
Application Name=DeliveryListFocusedProbe;
Connect Timeout=15;
Encrypt=False;
TrustServerCertificate=True;
"@

$connection = New-Object `
    System.Data.SqlClient.SqlConnection(
        $connectionString
    )

function Export-Query {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FileName,

        [Parameter(Mandatory = $true)]
        [string]$Query,

        [switch]$UseDeliveryDate
    )

    $outputPath = Join-Path $outputFolder $FileName
    $errorPath = "$outputPath.error.txt"

    $command = $connection.CreateCommand()
    $command.CommandText = $Query
    $command.CommandTimeout = 120

    if ($UseDeliveryDate) {
        $parameter = $command.Parameters.Add(
            "@DeliveryDate",
            [System.Data.SqlDbType]::Date
        )

        $parameter.Value = $deliveryDate.Date
    }

    $adapter = New-Object `
        System.Data.SqlClient.SqlDataAdapter(
            $command
        )

    $table = New-Object System.Data.DataTable

    try {
        [void]$adapter.Fill($table)

        if ($table.Rows.Count -gt 0) {
            $table |
                Export-Csv `
                    -LiteralPath $outputPath `
                    -NoTypeInformation `
                    -Encoding UTF8
        }
        else {
            "No rows returned." |
                Set-Content `
                    -LiteralPath $outputPath `
                    -Encoding UTF8
        }

        Write-Host (
    		"Created {0} - {1} rows" -f
    		$FileName,
    		$table.Rows.Count
	) -ForegroundColor Green
    }
    catch {
        $_.Exception.ToString() |
            Set-Content `
                -LiteralPath $errorPath `
                -Encoding UTF8

        Write-Host (
            "Query failed for {0}. See {1}" -f
            $FileName,
            $errorPath
        ) -ForegroundColor Yellow
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
    Write-Host ""

    Export-Query `
        -FileName "01-target-object-columns.csv" `
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
        'TEMP_DELIV',
        'BW_LADELISTE',
        'DR_REPORTE',
        'KA_CRYSTAL',
        'KA_CRYSTAL_GRP',
        'KA_CRYSTAL_MIT',
        'BW_AUFTR_KOPF',
        'BW_AUFTR_POS'
  )
ORDER BY
    o.name,
    c.column_id;
"@

    Export-Query `
        -FileName "02-candidate-delivery-view.csv" `
        -UseDeliveryDate `
        -Query @"
SELECT TOP (1000)
    h.ID AS OrderNumber,
    i.ITEM_NO AS ItemNumber,

    h.DATE_SCHEDDEL AS ScheduledDeliveryDate,
    h.DATE_DEL AS DeliveryDate,
    h.DATE_ACTUALDEL AS ActualDeliveryDate,
    h.DATE_REQDEL AS RequestedDeliveryDate,

    h.CUST_ID AS CustomerNumber,
    h.CUST_MATCHCODE AS CustomerMatchCode,
    h.CUST_NAME1 AS CustomerName1,
    h.CUST_NAME2 AS CustomerName2,

    h.DELADDR_CUSTNAME1 AS DeliveryName1,
    h.DELADDR_CUSTNAME2 AS DeliveryName2,
    h.DELADDR_CUSTCITY AS DeliveryCity,
    h.DELADDR_CUSTSTATE AS DeliveryState,

    h.OR_DELROUTE AS DeliveryRoute,
    h.OR_ALTDELROUTE AS AlternateDeliveryRoute,
    h.OR_CUSTOMSROUTE AS CustomsRoute,

    h.STATUS AS OrderStatus,
    i.ITEM_STATUS AS ItemStatus,

    h.CLAIM_NO AS ClaimNumber,
    h.CLAIM_DOCNO AS ClaimDocumentNumber,

    h.BATCH_PRODNOIG AS HeaderBatchIG,
    h.BATCH_PRODNOLSG AS HeaderBatchLSG,
    h.BATCH_PRODNOTSG AS HeaderBatchTSG,
    i.PROD_PRODBATCHNO AS ItemProductionBatch,
    i.PROD_KOMONO AS ItemProductionReference,

    i.ITEM_CUSTREF AS ItemCustomerReference,
    i.ITEM_CUSTITEMNO AS CustomerItemNumber,
    i.ITEM_TEXT AS ItemText,
    i.ITEM_TEXT1 AS ItemText1,
    i.ITEM_TEXT2 AS ItemText2,
    i.ITEM_TEXT3 AS ItemText3,

    i.PROD_ID AS ProductId,
    i.PROD_SHORTDESC AS ProductShortDescription,
    i.PROD_DESC1 AS ProductDescription1,
    i.PROD_DESC2 AS ProductDescription2,
    i.PROD_DESC3 AS ProductDescription3,

    i.PI_ITEMQTY AS ItemQuantity,
    i.PI_ORIGQTYFORPARTDEL AS OriginalQuantity,
    i.PI_PARTDELIVEREDQTY AS PartDeliveredQuantity,

    i.PI_WIDTH AS Width,
    i.PI_HEIGHT AS Height,
    i.PI_THICKNESS AS Thickness,
    i.PI_WEIGHTPERPIECE AS WeightPerPiece,

    i.PROD_RACKNO AS AWrackNumber,
    i.PROD_RACKNOSHIPCTRL AS RackNoShippingControl,

    i.REF_PONO AS CustomerPONumber,
    i.REF_DELORDERNO AS ReferencedDeliveryOrder,
    i.REF_DELITEMNO AS ReferencedDeliveryItem,

    i.COMP_REASON AS ComplaintReason,
    i.COMP_CAUSE AS ComplaintCause,
    i.DATELASTMOD AS ItemLastModifiedDate
FROM SYSADM.AWV_TD_ORDER_HEADER h
INNER JOIN SYSADM.AWV_TD_ORDER_ITEM i
    ON i.ORDER_REF = h.ID
WHERE
       h.DATE_SCHEDDEL = @DeliveryDate
    OR h.DATE_DEL = @DeliveryDate
ORDER BY
    h.ID,
    i.ITEM_NO;
"@

    Export-Query `
        -FileName "03-temp-deliv.csv" `
        -Query @"
SELECT TOP (500)
    *
FROM SYSADM.TEMP_DELIV;
"@

    Export-Query `
        -FileName "04-bw-ladeliste.csv" `
        -Query @"
SELECT TOP (100)
    *
FROM SYSADM.BW_LADELISTE;
"@

    Export-Query `
        -FileName "05-base-order-headers.csv" `
        -UseDeliveryDate `
        -Query @"
SELECT TOP (500)
    ID AS OrderNumber,
    STATUS AS OrderStatus,
    DATUM_LIEFER_PLAN AS PlannedDeliveryDate,
    DATUM_LIEFER_TAT AS ActualDeliveryDate,
    DATUM_LIEFERWUNSCH AS RequestedDeliveryDate,
    AH_HAUPT_AUFTR AS MainOrderNumber,
    OR_TOUR AS Route,
    OR_AWTOUR AS AWRoute,
    OR_LIEFERBED AS DeliveryCondition,
    KO_OBJEKT_KUNDE AS CustomerObject,
    LAUF_PROD1 AS ProductionBatch1,
    LAUF_PROD2 AS ProductionBatch2,
    LAUF_PROD3 AS ProductionBatch3
FROM SYSADM.BW_AUFTR_KOPF
WHERE DATUM_LIEFER_PLAN = @DeliveryDate
ORDER BY ID;
"@

    Export-Query `
        -FileName "06-base-order-items.csv" `
        -UseDeliveryDate `
        -Query @"
SELECT TOP (1000)
    h.ID AS OrderNumber,
    p.POS_NR AS ItemNumber,
    h.DATUM_LIEFER_PLAN AS PlannedDeliveryDate,
    h.OR_TOUR AS Route,
    h.OR_AWTOUR AS AWRoute,

    p.POS_STATUS AS ItemStatus,
    p.POS_KOMMISSION AS JobOrCommission,
    p.POS_KUNDENPOS AS CustomerItemNumber,
    p.POS_TEXT AS ItemText,
    p.POS_TEXT1 AS ItemText1,
    p.POS_TEXT2 AS ItemText2,
    p.POS_TEXT3 AS ItemText3,

    p.PP_MENGE AS Quantity,
    p.PP_ORIG_MENGE AS OriginalQuantity,
    p.PP_TEILGEL_MENGE AS PartDeliveredQuantity,
    p.PP_BREITE AS Width,
    p.PP_HOEHE AS Height,

    p.FER_LAUF1 AS ProductionBatch
FROM SYSADM.BW_AUFTR_KOPF h
INNER JOIN SYSADM.BW_AUFTR_POS p
    ON p.ID = h.ID
WHERE h.DATUM_LIEFER_PLAN = @DeliveryDate
ORDER BY
    h.ID,
    p.POS_NR;
"@

    Export-Query `
        -FileName "07-report-field-mapping.csv" `
        -Query @"
SELECT
    h.ID AS OrderNumber,
    p.POS_NR AS ItemNumber,

    h.STATUS AS OrderStatus,
    p.POS_STATUS AS ItemStatus,

    h.BEST_TEXT1 AS HeaderOrderText1,
    h.BEST_TEXT2 AS HeaderOrderText2,
    h.FREMD_KEY AS ForeignKey,
    h.AH_MCODE AS CustomerMatchCode,
    h.AH_KOPF AS CustomerHeader,
    h.AH_NAME1 AS CustomerName1,
    h.AH_NAME2 AS CustomerName2,

    h.AL_KOPF AS DeliveryAddressHeader,
    h.AL_NAME1 AS DeliveryAddressName1,
    h.AL_NAME2 AS DeliveryAddressName2,

    h.OR_TOUR AS Route,
    h.OR_AWTOUR AS AWRoute,
    h.OR_LIEFERBED AS DeliveryCondition,

    h.CLAIM AS ClaimFlag,
    h.CLAIM_ORDER AS ClaimOrderFlag,

    h.LAUF_PROD1 AS HeaderProductionBatch,

    p.POS_KOMMISSION AS ItemCommission,
    p.POS_KUNDENPOS AS CustomerItemNumber,

    p.PROD_ID AS ProductId,
    p.PROD_BEZ1 AS ProductDescription1,
    p.PROD_BEZ2 AS ProductDescription2,
    p.PROD_BEZ3 AS ProductDescription3,
    p.PROD_KURZ_BEZ AS ProductShortDescription,

    p.PROD_WGR AS ProductGroup,
    p.PROD_WGR_STAT AS StatisticalProductGroup,
    p.PROD_KMB AS CombinationGroup,
    p.PROD_KMB_STAT AS StatisticalCombinationGroup,
    p.PROD_PRODART AS ProductType,
    p.PROD_PRODGRP AS ProductClass,

    p.PP_MENGE AS Quantity,
    p.PP_BREITE AS Width32nds,
    p.PP_HOEHE AS Height32nds,
    p.PP_DICKE AS Thickness,

    p.REKLA_ORT AS ComplaintLocation,
    p.REKLA_GRUND AS ComplaintReason
FROM SYSADM.BW_AUFTR_KOPF h
INNER JOIN SYSADM.BW_AUFTR_POS p
    ON p.ID = h.ID
WHERE h.ID IN (
    235897,
    235934,
    235941,
    235955,
    235966,
    236067,
    236068,
    236069,
    236073,
    236074
)
ORDER BY
    h.ID,
    p.POS_NR;
"@

    Export-Query `
        -FileName "08-remake-flag-comparison.csv" `
        -Query @"
SELECT
    CASE
        WHEN h.ID IN (
            236067,
            236068,
            236069,
            236073,
            236074
        )
        THEN 'RM in Crystal'
        ELSE 'Not RM in Crystal'
    END AS ExpectedCrystalResult,

    h.ID AS OrderNumber,
    p.POS_NR AS ItemNumber,

    h.BEST_TEXT1 AS JobNumber,
    h.STATUS AS OrderStatus,
    p.POS_STATUS AS ItemStatus,

    h.MOD AS OrderModification,
    h.BIT AS HeaderBit,
    h.CLAIM AS ClaimFlag,
    h.CLAIM_ORDER AS ClaimOrderFlag,
    h.CONTRACT AS ContractFlag,
    h.KATEGORIE AS OrderCategory,
    h.CHANGED AS HeaderChanged,
    h.AH_HAUPT_AUFTR AS MainOrderNumber,
    h.AH_IDENT AS CustomerId,
    h.AH_MCODE AS CustomerMatchCode,
    h.FREMD_KEY AS ForeignKey,

    p.POS_BIT AS PositionBit1,
    p.POS_BIT2 AS PositionBit2,
    p.POS_BIT3 AS PositionBit3,
    p.VERS_BIT AS VersionBit,
    p.RESTERROR AS RestError,
    p.ALTERNATIV AS AlternativeFlag,
    p.POS_BLOCK AS PositionBlocked,
    p.POS_AUFTRINFO AS PositionOrderInfo,

    p.AUFTR_REF AS OrderReference,
    p.POS_REF AS PositionReference,

    p.REF_BEST_ID AS PurchaseOrderReference,
    p.REF_BEST_POS AS PurchaseItemReference,
    p.REF_AUSLIEF_AUFTR_ID AS DeliveryOrderReference,
    p.REF_AUSLIEF_AUFTR_POS AS DeliveryItemReference,
    p.REF_ENDKUNDE_BEST_ID AS EndCustomerOrderReference,
    p.REF_ENDKUNDE_BEST_POS AS EndCustomerItemReference,

    p.POS_TEXT AS PositionText,
    p.POS_TEXT1 AS PositionText1,
    p.POS_TEXT2 AS PositionText2,
    p.POS_TEXT3 AS PositionText3,
    p.POS_TEXT4 AS PositionText4,
    p.POS_TEXT5 AS PositionText5,

    p.REKLA_ORT AS ComplaintLocation,
    p.REKLA_GRUND AS ComplaintReason,

    p.PROD_ID AS ProductId,
    p.PROD_BEZ1 AS ProductDescription,
    p.PP_MENGE AS Quantity
FROM SYSADM.BW_AUFTR_KOPF h
INNER JOIN SYSADM.BW_AUFTR_POS p
    ON p.ID = h.ID
WHERE h.ID IN (
    235897,
    235934,
    235950,
    235955,
    235966,
    236067,
    236068,
    236069,
    236073,
    236074
)
ORDER BY
    h.ID,
    p.POS_NR;
"@

    Export-Query `
        -FileName "09-remake-order-history.csv" `
        -Query @"
SELECT
    CASE
        WHEN REF_ID IN (
            236067,
            236068,
            236069,
            236073,
            236074
        )
        THEN 'RM in Crystal'
        ELSE 'Not RM in Crystal'
    END AS ExpectedCrystalResult,

    REF_ID AS OrderNumber,
    STATUS_ID AS StatusId,
    PUNKT_ID AS StatusPointId,
    BEARBEITER AS UpdatedBy,
    DATUM AS StatusDate,
    BEM AS StatusComment
FROM SYSADM.BW_AUFTR_HIST
WHERE REF_ID IN (
    235897,
    235934,
    235950,
    235955,
    235966,
    236067,
    236068,
    236069,
    236073,
    236074
)
ORDER BY
    REF_ID,
    DATUM;
"@

    $summary = @"
A+W focused delivery-list probe
Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Delivery date: $($deliveryDate.ToString("yyyy-MM-dd"))
SQL login: $([System.Security.Principal.WindowsIdentity]::GetCurrent().Name)

All queries were SELECT-only.
No A+W data or database objects were modified.
"@

    $summary |
        Set-Content `
            -LiteralPath (Join-Path $outputFolder "README.txt") `
            -Encoding UTF8

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