Attribute VB_Name = "modSnapshotPublisher"
Option Explicit

'==============================================================================
' Module: modSnapshotPublisher
' Workbook: Multi User Scanner Queue Testing.xlsm / Master Delivery List
'
' What this module does:
'   Publishes master workbook stage snapshots to SharePoint so intake
'   workbooks can load a current read-only copy without opening the master
'   workbook.
'
' Why this module exists:
'   This protects the master from coauthoring conflicts and lets intake
'   stations work from SharePoint/Power Automate instead of direct workbook
'   sharing.
'
' Commenting standard used in this rewrite:
'   Procedure comments explain both what the code does and why that
'   behavior matters in the scanning / SharePoint / Power Automate workflow.
'   The code logic and public signatures are intentionally kept stable; this
'   pass is primarily a readability, maintainability, and safety pass.
'==============================================================================



Private Const SNAPSHOT_LEFT_FIRST_COL As Long = 1      'A
Private Const SNAPSHOT_LEFT_LAST_COL As Long = 14      'N

Private Const SNAPSHOT_SEND_FIRST_COL As Long = 16     'P
Private Const SNAPSHOT_SEND_LAST_COL As Long = 23      'W

Private Const SNAPSHOT_RECV_FIRST_COL As Long = 25     'Y
Private Const SNAPSHOT_RECV_LAST_COL As Long = 33      'AG

Private Const SNAPSHOT_STAGING_FIRST_COL As Long = 42  'AP
Private Const SNAPSHOT_STAGING_LAST_COL As Long = 48   'AV

Private Const SNAPSHOT_AUTO_PUBLISH_SECONDS As Long = 600

Private mNextSnapshotPublishRun As Date
Private mSnapshotPublishScheduled As Boolean
Private mSnapshotPublishRunning As Boolean

'------------------------------------------------------------------------------
' Procedure: ScheduleAutoSnapshotPublish
' Scope: Public Sub
'
' What it does:
'   Handles part of the master-to-intake snapshot workflow for
'   ScheduleAutoSnapshotPublish.
'
' Why it exists:
'   Snapshots let intake workbooks display and scan against current delivery
'   data without opening or editing the master workbook.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub ScheduleAutoSnapshotPublish()
    If IsExternalQueuePaused() Then Exit Sub
    If mSnapshotPublishScheduled Then Exit Sub

    mNextSnapshotPublishRun = Now + TimeSerial(0, 0, SNAPSHOT_AUTO_PUBLISH_SECONDS)
    mSnapshotPublishScheduled = True

    Application.OnTime _
        EarliestTime:=mNextSnapshotPublishRun, _
        Procedure:="'" & ThisWorkbook.Name & "'!AutoSnapshotPublishBridge", _
        Schedule:=True
End Sub

'------------------------------------------------------------------------------
' Procedure: CancelAutoSnapshotPublish
' Scope: Public Sub
'
' What it does:
'   Handles part of the master-to-intake snapshot workflow for
'   CancelAutoSnapshotPublish.
'
' Why it exists:
'   Snapshots let intake workbooks display and scan against current delivery
'   data without opening or editing the master workbook.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub CancelAutoSnapshotPublish()
    On Error Resume Next

    If mSnapshotPublishScheduled Then
        Application.OnTime _
            EarliestTime:=mNextSnapshotPublishRun, _
            Procedure:="'" & ThisWorkbook.Name & "'!AutoSnapshotPublishBridge", _
            Schedule:=False
    End If

    mSnapshotPublishScheduled = False
    mSnapshotPublishRunning = False

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: AutoSnapshotPublishBridge
' Scope: Public Sub
'
' What it does:
'   Handles part of the master-to-intake snapshot workflow for
'   AutoSnapshotPublishBridge.
'
' Why it exists:
'   Snapshots let intake workbooks display and scan against current delivery
'   data without opening or editing the master workbook.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub AutoSnapshotPublishBridge()
    On Error GoTo SafeExit

    mSnapshotPublishScheduled = False

    If IsExternalQueuePaused() Then GoTo SafeExit
    If mSnapshotPublishRunning Then GoTo SafeExit
    mSnapshotPublishRunning = True

    'Do not bump revision on timed snapshot refreshes.
    PublishAllStageSnapshots False, False

SafeExit:
    mSnapshotPublishRunning = False
    If Not IsExternalQueuePaused() Then ScheduleAutoSnapshotPublish
End Sub

'------------------------------------------------------------------------------
' Procedure: Test_PublishSnapshot_IndianTrail
' Scope: Public Sub
'
' What it does:
'   Handles part of the master-to-intake snapshot workflow for
'   Test_PublishSnapshot_IndianTrail.
'
' Why it exists:
'   Snapshots let intake workbooks display and scan against current delivery
'   data without opening or editing the master workbook.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub Test_PublishSnapshot_IndianTrail()
    BumpCurrentDeliveryListRevision

    If PublishStageSnapshot("Inbound - Indian Trail", True) Then
        RegisterThisMasterDeliveryList
        MsgBox "Indian Trail snapshot published successfully.", vbInformation, "Snapshot Publish"
    Else
        MsgBox "Indian Trail snapshot was not published.", vbExclamation, "Snapshot Publish"
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: Test_PublishAllStageSnapshots
' Scope: Public Sub
'
' What it does:
'   Handles part of the master-to-intake snapshot workflow for
'   Test_PublishAllStageSnapshots.
'
' Why it exists:
'   Snapshots let intake workbooks display and scan against current delivery
'   data without opening or editing the master workbook.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub Test_PublishAllStageSnapshots()
    PublishAllStageSnapshots True, True
End Sub

'------------------------------------------------------------------------------
' Procedure: PublishAllStageSnapshots
' Scope: Public Sub
'
' What it does:
'   Publishes every supported operational stage snapshot from the master
'   workbook to SharePoint.
'
' Why it exists:
'   Intake stations load these snapshots instead of opening the master
'   workbook, reducing merge conflicts and making scanning stations
'   independent.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub PublishAllStageSnapshots(Optional ByVal showMessage As Boolean = False, Optional ByVal bumpRevision As Boolean = True)
    Dim profiles As Variant
    Dim profile As Variant
    Dim publishedCount As Long
    Dim skippedCount As Long
    Dim failedCount As Long

    On Error GoTo FailPublish

    If IsExternalQueuePaused() Then
        Application.StatusBar = False
        If showMessage Then
            MsgBox "Snapshot publishing is paused with the queue." & vbCrLf & vbCrLf & _
                   "Click QUEUE PAUSED to start queue processing and snapshot publishing.", _
                   vbInformation, "Snapshots Paused"
        End If
        Exit Sub
    End If

    If bumpRevision Then
        BumpCurrentDeliveryListRevision
    End If

    profiles = Array( _
        "Outbound - Airport Rd", _
        "Inbound - Indian Trail", _
        "Inbound - Greenville", _
        "Customer Pickup", _
        "Staging - Airport Rd")

    Application.StatusBar = "Publishing intake snapshots..."

    For Each profile In profiles
        If PublishStageSnapshot(CStr(profile), False) Then
            publishedCount = publishedCount + 1
        Else
            skippedCount = skippedCount + 1
        End If
    Next profile

    If publishedCount > 0 Then
        RegisterThisMasterDeliveryList
    End If

    Application.StatusBar = False

    If showMessage Then
        MsgBox "Snapshot publish complete." & vbCrLf & vbCrLf & _
               "Published: " & publishedCount & vbCrLf & _
               "Skipped: " & skippedCount & vbCrLf & _
               "Failed: " & failedCount, _
               vbInformation, "Snapshot Publish"
    End If

    Exit Sub

FailPublish:
    Application.StatusBar = False

    If showMessage Then
        MsgBox "Snapshot publish failed." & vbCrLf & vbCrLf & _
               "Error " & Err.Number & ": " & Err.Description, _
               vbExclamation, "Snapshot Publish"
    Else
        Err.Raise Err.Number, Err.Source, Err.Description
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: PublishStageSnapshot
' Scope: Public Function
'
' What it does:
'   Builds and uploads one stage snapshot for a selected profile such as
'   Outbound, Indian Trail, Greenville, Customer Pickup, or Staging.
'
' Why it exists:
'   Publishing one stage at a time lets the master refresh only the affected
'   intake view when needed and gives clear failure messages per stage.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function PublishStageSnapshot(ByVal stageProfile As String, _
                                     Optional ByVal showErrors As Boolean = False, _
                                     Optional ByRef failReason As String = vbNullString) As Boolean
    Dim stageKey As String
    Dim stageSheetName As String
    Dim modeText As String
    Dim ws As Worksheet
    Dim snapshotJson As String
    Dim rowCount As Long
    Dim revisionToken As String
    Dim updatedAtText As String
    Dim deliveryListKey As String

    On Error GoTo FailPublish

    failReason = vbNullString

    stageProfile = Trim$(CStr(stageProfile))
    stageKey = SnapshotStageKeyFromProfile(stageProfile)
    stageSheetName = SnapshotStageSheetFromProfile(stageProfile)
    modeText = SnapshotModeFromStageProfile(stageProfile)

    If Len(stageKey) = 0 Or Len(stageSheetName) = 0 Or Len(modeText) = 0 Then
        failReason = "Unsupported stage profile: " & stageProfile

        If showErrors Then
            MsgBox failReason, vbExclamation, "Snapshot Publish"
        End If

        Exit Function
    End If

    Set ws = Nothing

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(stageSheetName)
    On Error GoTo FailPublish

    If ws Is Nothing Then
        failReason = "Could not find sheet '" & stageSheetName & "' in the master workbook."

        If showErrors Then
            MsgBox failReason, vbExclamation, "Snapshot Publish"
        End If

        Exit Function
    End If

    deliveryListKey = GetCurrentDeliveryListKey()
    revisionToken = GetCurrentDeliveryListRevisionToken()
    updatedAtText = Format$(Now, "m/d/yyyy h:mm:ss AM/PM")

    snapshotJson = BuildStageSnapshotJson(ws, deliveryListKey, stageKey, stageProfile, modeText, stageSheetName, revisionToken, updatedAtText, rowCount)

    If Len(snapshotJson) = 0 Then
        failReason = "Snapshot JSON was blank for " & stageProfile & _
                     ". Check that the sheet has Order Nr. and Item Nr. headers in A:N."

        If showErrors Then
            MsgBox failReason, vbExclamation, "Snapshot Publish"
        End If

        Exit Function
    End If

    If rowCount <= 0 Then
        failReason = "No delivery rows were found for " & stageProfile & "."

        If showErrors Then
            MsgBox failReason, vbExclamation, "Snapshot Publish"
        End If

        Exit Function
    End If

    If Not PA_SnapshotUpsert( _
            deliveryListKey, _
            stageKey, _
            stageProfile, _
            modeText, _
            stageSheetName, _
            revisionToken, _
            updatedAtText, _
            rowCount, _
            snapshotJson) Then

        failReason = "SnapshotUpsert flow returned False for " & stageProfile & _
                     ". DeliveryListKey=" & deliveryListKey & _
                     ", StageKey=" & stageKey & _
                     ", RowCount=" & rowCount & "."

        Exit Function
    End If

    PublishStageSnapshot = True
    Exit Function

FailPublish:
    failReason = "Snapshot publish failed for " & stageProfile & _
                 ". Error " & Err.Number & ": " & Err.Description

    If showErrors Then
        MsgBox failReason, vbExclamation, "Snapshot Publish"
    Else
        Err.Clear
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: Test_BuildIndianTrailHeaderRoutingDebug
' Scope: Public Sub
'
' What it does:
'   Finds, writes, validates, or uses worksheet header cells for
'   Test_BuildIndianTrailHeaderRoutingDebug.
'
' Why it exists:
'   Header locations can move during import/rebuild, so the code uses header
'   discovery to target the correct columns instead of guessing.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub Test_BuildIndianTrailHeaderRoutingDebug()
    Dim ws As Worksheet

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets("Inbound - Indian Trail")
    On Error GoTo 0

    If ws Is Nothing Then
        MsgBox "Could not find sheet 'Inbound - Indian Trail'.", vbExclamation, "Header Routing Debug"
        Exit Sub
    End If

    BuildIndianTrailHeaderRoutingDebugSheet ws
End Sub

'------------------------------------------------------------------------------
' Procedure: BuildStageSnapshotJson
' Scope: Private Function
'
' What it does:
'   Serializes a scanner sheet into JSON, including header metadata, row data,
'   section headers, scan values, routing info, and formatting metadata.
'
' Why it exists:
'   Power Automate stores text fields more reliably than workbook objects, so
'   the intake workbook reconstructs the stage view from this JSON snapshot.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BuildStageSnapshotJson(ByVal ws As Worksheet, _
                                        ByVal deliveryListKey As String, _
                                        ByVal stageKey As String, _
                                        ByVal stageProfile As String, _
                                        ByVal modeText As String, _
                                        ByVal stageSheetName As String, _
                                        ByVal revisionToken As String, _
                                        ByVal updatedAtText As String, _
                                        ByRef rowCount As Long) As String
    Dim headerRow As Long
    Dim orderCol As Long
    Dim itemCol As Long
    Dim qtyCol As Long
    Dim dimensionsCol As Long
    Dim customerCol As Long
    Dim routeCol As Long
    Dim lastRow As Long
    Dim r As Long
    Dim rowsJson As String
    Dim rowJson As String
    Dim titleText As String
    Dim rowType As String
    Dim deliveryLineCount As Long

    Dim currentGlassHeader As String
    Dim currentHeaderRow As Long
    Dim currentGlassCategory As String
    Dim currentBayCategory As String
    Dim currentRoutingWarning As String

    rowCount = 0
    deliveryLineCount = 0

    headerRow = SnapshotFindMainHeaderRow(ws, orderCol, itemCol)
    If headerRow = 0 Then Exit Function

    qtyCol = SnapshotFindHeaderColInRowByNames(ws, headerRow, Array("Qty.", "Qty", "Quantity"))
    dimensionsCol = SnapshotFindHeaderColInRowByNames(ws, headerRow, Array("Dimensions", "Dimension", "Dim", "Size"))
    customerCol = SnapshotFindHeaderColInRowByNames(ws, headerRow, Array("Customer"))
    routeCol = SnapshotFindHeaderColInRowByNames(ws, headerRow, Array("Route", "Rt", "Route Code"))

    If qtyCol = 0 Then qtyCol = 7
    If dimensionsCol = 0 Then dimensionsCol = 8
    If routeCol = 0 Then routeCol = 12

    lastRow = ws.Cells(ws.rows.Count, orderCol).End(xlUp).Row
    titleText = SnapshotFindDeliveryTitle(ws)

    For r = headerRow + 1 To lastRow
        rowType = vbNullString

        If SnapshotRowIsSectionHeader(ws, r, orderCol, itemCol) Then
            rowType = "SECTION"

            currentGlassHeader = SnapshotCellText(ws.Cells(r, 1))
            currentHeaderRow = r
            SnapshotClassifyGlassHeader currentGlassHeader, currentGlassCategory, currentBayCategory, currentRoutingWarning

        ElseIf SnapshotRowIsDeliveryLine(ws, r, orderCol, itemCol) Then
            rowType = "LINE"
            deliveryLineCount = deliveryLineCount + 1

            If Len(Trim$(currentGlassHeader)) = 0 Then
                currentHeaderRow = 0
                SnapshotClassifyGlassHeader currentGlassHeader, currentGlassCategory, currentBayCategory, currentRoutingWarning
            End If
        End If

        If Len(rowType) > 0 Then
            rowCount = rowCount + 1

            rowJson = BuildStageSnapshotRowJson( _
                        ws, _
                        r, _
                        rowCount, _
                        orderCol, _
                        itemCol, _
                        qtyCol, _
                        dimensionsCol, _
                        customerCol, _
                        routeCol, _
                        modeText, _
                        rowType, _
                        currentGlassHeader, _
                        currentHeaderRow, _
                        currentGlassCategory, _
                        currentBayCategory, _
                        "DeliveryListHeader", _
                        currentRoutingWarning)

            If Len(rowsJson) > 0 Then rowsJson = rowsJson & ","
            rowsJson = rowsJson & rowJson
        End If
    Next r

    If rowCount = 0 Then Exit Function

    BuildStageSnapshotJson = "{" & _
        """schemaVersion"":3," & _
        """deliveryListKey"":" & SnapshotJsonString(deliveryListKey) & "," & _
        """stageKey"":" & SnapshotJsonString(stageKey) & "," & _
        """stageProfile"":" & SnapshotJsonString(stageProfile) & "," & _
        """mode"":" & SnapshotJsonString(UCase$(modeText)) & "," & _
        """stageSheetName"":" & SnapshotJsonString(stageSheetName) & "," & _
        """revisionToken"":" & SnapshotJsonString(revisionToken) & "," & _
        """updatedAt"":" & SnapshotJsonString(updatedAtText) & "," & _
        """title"":" & SnapshotJsonString(titleText) & "," & _
        """headerRow"":" & CStr(headerRow) & "," & _
        """routingSource"":" & SnapshotJsonString("DeliveryListHeader") & "," & _
        """rowCount"":" & CStr(rowCount) & "," & _
        """deliveryLineCount"":" & CStr(deliveryLineCount) & "," & _
        """topRows"":" & SnapshotTopRowsJson(ws, headerRow) & "," & _
        """leftHeaders"":" & SnapshotRangeValuesJson(ws, headerRow, SNAPSHOT_LEFT_FIRST_COL, SNAPSHOT_LEFT_LAST_COL) & "," & _
        """sendHeaders"":" & SnapshotRangeValuesJson(ws, headerRow, SNAPSHOT_SEND_FIRST_COL, SNAPSHOT_SEND_LAST_COL) & "," & _
        """recvHeaders"":" & SnapshotRangeValuesJson(ws, headerRow, SNAPSHOT_RECV_FIRST_COL, SNAPSHOT_RECV_LAST_COL) & "," & _
        """stagingHeaders"":" & SnapshotRangeValuesJson(ws, headerRow, SNAPSHOT_STAGING_FIRST_COL, SNAPSHOT_STAGING_LAST_COL) & "," & _
        """rows"": [" & rowsJson & "]," & _
        """format"":" & SnapshotSheetFormatJson(ws, headerRow, lastRow) & _
        "}"
End Function

'------------------------------------------------------------------------------
' Procedure: BuildStageSnapshotRowJson
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   BuildStageSnapshotRowJson.
'
' Why it exists:
'   The intake workbook reconstructs its visible sheet from snapshot JSON, so
'   row data and formatting details must be serialized predictably.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BuildStageSnapshotRowJson(ByVal ws As Worksheet, _
                                           ByVal rowNum As Long, _
                                           ByVal rowIndex As Long, _
                                           ByVal orderCol As Long, _
                                           ByVal itemCol As Long, _
                                           ByVal qtyCol As Long, _
                                           ByVal dimensionsCol As Long, _
                                           ByVal customerCol As Long, _
                                           ByVal routeCol As Long, _
                                           ByVal modeText As String, _
                                           Optional ByVal rowType As String = "LINE", _
                                           Optional ByVal glassHeader As String = vbNullString, _
                                           Optional ByVal headerRowIndex As Long = 0, _
                                           Optional ByVal glassCategory As String = vbNullString, _
                                           Optional ByVal bayCategory As String = vbNullString, _
                                           Optional ByVal routingSource As String = vbNullString, _
                                           Optional ByVal routingWarning As String = vbNullString) As String
    Dim activeBarcodeCol As Long
    Dim activeQtyCol As Long
    Dim activeTimeCol As Long
    Dim activeCheckCol As Long
    Dim activeCommentCol As Long
    Dim activeBayCol As Long

    Dim ord As Long
    Dim itm As Long
    Dim requiredQty As Long
    Dim scanQty As Long
    Dim dimensionsText As String
    Dim customerText As String
    Dim routeText As String
    Dim bayText As String
    Dim barcodeText As String
    Dim scanTimeText As String
    Dim checkStatusText As String
    Dim commentText As String

    Dim widthInches As Double
    Dim heightInches As Double
    Dim maxDimensionInches As Double
    Dim parsedDimensions As Boolean
    Dim possibleOversized As Boolean
    Dim json As String

    rowType = UCase$(Trim$(rowType))
    If Len(rowType) = 0 Then rowType = "LINE"
    If Len(routingSource) = 0 Then routingSource = "DeliveryListHeader"

    SnapshotGetActiveBlockColumns modeText, activeBarcodeCol, activeQtyCol, activeTimeCol, activeCheckCol, activeCommentCol, activeBayCol

    If rowType = "LINE" Then
        ord = SnapshotSafeLong(ws.Cells(rowNum, orderCol).Value)
        itm = SnapshotSafeLong(ws.Cells(rowNum, itemCol).Value)
        requiredQty = SnapshotSafeLong(ws.Cells(rowNum, qtyCol).Value)

        If requiredQty < 1 Then requiredQty = 1

        If dimensionsCol > 0 Then
            dimensionsText = SnapshotCellText(ws.Cells(rowNum, dimensionsCol))
            parsedDimensions = SnapshotParseDimensionsInches(dimensionsText, widthInches, heightInches, maxDimensionInches)
            If parsedDimensions Then
                possibleOversized = SnapshotPossibleOversized(widthInches, heightInches)
                If possibleOversized Then
                    If Len(routingWarning) > 0 Then routingWarning = routingWarning & " | "
                    routingWarning = routingWarning & "Possible oversized - receiving must decide manually"
                End If
            End If
        End If

        If activeQtyCol > 0 Then scanQty = SnapshotSafeLong(ws.Cells(rowNum, activeQtyCol).Value)
        If customerCol > 0 Then customerText = SnapshotCellText(ws.Cells(rowNum, customerCol))
        If routeCol > 0 Then routeText = SnapshotCellText(ws.Cells(rowNum, routeCol))
        If activeBayCol > 0 Then bayText = SnapshotCellText(ws.Cells(rowNum, activeBayCol))
        If activeBarcodeCol > 0 Then barcodeText = SnapshotCellText(ws.Cells(rowNum, activeBarcodeCol))
        If activeTimeCol > 0 Then scanTimeText = SnapshotCellText(ws.Cells(rowNum, activeTimeCol))
        If activeCheckCol > 0 Then checkStatusText = SnapshotCellText(ws.Cells(rowNum, activeCheckCol))
        If activeCommentCol > 0 Then commentText = SnapshotCellText(ws.Cells(rowNum, activeCommentCol))
    End If

    json = "{"
    json = json & """rowType"":" & SnapshotJsonString(rowType) & ","
    json = json & """rowNumber"":" & CStr(rowNum) & ","
    json = json & """rowIndex"":" & CStr(rowIndex) & ","
    json = json & """orderNumber"":" & CStr(ord) & ","
    json = json & """itemNumber"":" & CStr(itm) & ","
    json = json & """quantityRequired"":" & CStr(requiredQty) & ","
    json = json & """dimensions"":" & SnapshotJsonString(dimensionsText) & ","
    json = json & """glassHeader"":" & SnapshotJsonString(glassHeader) & ","
    json = json & """headerRowIndex"":" & CStr(headerRowIndex) & ","
    json = json & """glassCategory"":" & SnapshotJsonString(glassCategory) & ","
    json = json & """bayCategory"":" & SnapshotJsonString(bayCategory) & ","
    json = json & """routingSource"":" & SnapshotJsonString(routingSource) & ","
    json = json & """routingWarning"":" & SnapshotJsonString(routingWarning) & ","
    json = json & """possibleOversized"":" & SnapshotBoolJson(possibleOversized) & ","
    json = json & """widthInches"":" & SnapshotNumberText(widthInches) & ","
    json = json & """heightInches"":" & SnapshotNumberText(heightInches) & ","
    json = json & """maxDimensionInches"":" & SnapshotNumberText(maxDimensionInches) & ","
    json = json & """customer"":" & SnapshotJsonString(customerText) & ","
    json = json & """route"":" & SnapshotJsonString(routeText) & ","
    json = json & """bayNumber"":" & SnapshotJsonString(bayText) & ","
    json = json & """barcode"":" & SnapshotJsonString(barcodeText) & ","
    json = json & """scanQty"":" & CStr(scanQty) & ","
    json = json & """scanTime"":" & SnapshotJsonString(scanTimeText) & ","
    json = json & """checkStatus"":" & SnapshotJsonString(checkStatusText) & ","
    json = json & """comments"":" & SnapshotJsonString(commentText) & ","
    json = json & """queueState"":" & SnapshotJsonString(vbNullString) & ","
    json = json & """queueResult"":" & SnapshotJsonString(vbNullString) & ","
    json = json & """leftValues"":" & SnapshotRangeValuesJson(ws, rowNum, SNAPSHOT_LEFT_FIRST_COL, SNAPSHOT_LEFT_LAST_COL) & ","
    json = json & """sendValues"":" & SnapshotRangeValuesJson(ws, rowNum, SNAPSHOT_SEND_FIRST_COL, SNAPSHOT_SEND_LAST_COL) & ","
    json = json & """recvValues"":" & SnapshotRangeValuesJson(ws, rowNum, SNAPSHOT_RECV_FIRST_COL, SNAPSHOT_RECV_LAST_COL) & ","
    json = json & """stagingValues"":" & SnapshotRangeValuesJson(ws, rowNum, SNAPSHOT_STAGING_FIRST_COL, SNAPSHOT_STAGING_LAST_COL)
    json = json & "}"

    BuildStageSnapshotRowJson = json
End Function

'------------------------------------------------------------------------------
' Procedure: SnapshotClassifyGlassHeader
' Scope: Private Sub
'
' What it does:
'   Finds, writes, validates, or uses worksheet header cells for
'   SnapshotClassifyGlassHeader.
'
' Why it exists:
'   Header locations can move during import/rebuild, so the code uses header
'   discovery to target the correct columns instead of guessing.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub SnapshotClassifyGlassHeader(ByVal headerText As String, _
                                        ByRef glassCategory As String, _
                                        ByRef bayCategory As String, _
                                        ByRef routingWarning As String)
    Dim h As String

    h = UCase$(Trim$(CStr(headerText)))
    glassCategory = "ManualException"
    bayCategory = "ManualException"
    routingWarning = vbNullString

    If Len(h) = 0 Then
        routingWarning = "No delivery-list glass header found above this order"

    ElseIf InStr(1, h, "BFS", vbTextCompare) > 0 And InStr(1, h, "MIRROR", vbTextCompare) > 0 Then
        glassCategory = "MirrorAnnealed"
        bayCategory = "MirrorAnnealed"

    ElseIf InStr(1, h, "MIRROR", vbTextCompare) > 0 Then
        glassCategory = "MirrorAnnealed"
        bayCategory = "MirrorAnnealed"

    ElseIf InStr(1, h, "ANNEAL", vbTextCompare) > 0 Then
        glassCategory = "MirrorAnnealed"
        bayCategory = "MirrorAnnealed"

    ElseIf InStr(1, h, "TEMPER", vbTextCompare) > 0 Then
        glassCategory = "Tempered"
        bayCategory = "Tempered"

    ElseIf InStr(1, h, "CORAL", vbTextCompare) > 0 Then
        glassCategory = "ManualException"
        bayCategory = "ManualException"
        routingWarning = "Coral header - not auto-assigned by Indian Trail bay logic"

    Else
        glassCategory = "ManualException"
        bayCategory = "ManualException"
        routingWarning = "Unknown glass header - manual bay routing required"
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: SnapshotParseDimensionsInches
' Scope: Private Function
'
' What it does:
'   Handles part of the master-to-intake snapshot workflow for
'   SnapshotParseDimensionsInches.
'
' Why it exists:
'   Snapshots let intake workbooks display and scan against current delivery
'   data without opening or editing the master workbook.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SnapshotParseDimensionsInches(ByVal dimensionsText As String, _
                                               ByRef widthInches As Double, _
                                               ByRef heightInches As Double, _
                                               ByRef maxDimensionInches As Double) As Boolean
    Dim s As String
    Dim parts As Variant

    widthInches = 0
    heightInches = 0
    maxDimensionInches = 0

    s = UCase$(Trim$(CStr(dimensionsText)))
    If Len(s) = 0 Then Exit Function

    s = Replace$(s, ChrW$(215), "X")
    s = Replace$(s, ChrW$(8220), "")
    s = Replace$(s, ChrW$(8221), "")
    s = Replace$(s, """", "")
    s = Replace$(s, "'", "")
    s = Replace$(s, "INCHES", "")
    s = Replace$(s, "INCH", "")
    s = Replace$(s, "IN.", "")
    s = Replace$(s, " BY ", "X")
    s = Replace$(s, " x ", "X")
    s = Replace$(s, " X ", "X")
    s = Replace$(s, " X", "X")
    s = Replace$(s, "X ", "X")

    parts = Split(s, "X")
    If UBound(parts) < 1 Then Exit Function

    widthInches = SnapshotParseSingleInchValue(CStr(parts(0)))
    heightInches = SnapshotParseSingleInchValue(CStr(parts(1)))

    If widthInches <= 0 Or heightInches <= 0 Then Exit Function

    If widthInches >= heightInches Then
        maxDimensionInches = widthInches
    Else
        maxDimensionInches = heightInches
    End If

    SnapshotParseDimensionsInches = True
End Function

'------------------------------------------------------------------------------
' Procedure: SnapshotParseSingleInchValue
' Scope: Private Function
'
' What it does:
'   Handles part of the master-to-intake snapshot workflow for
'   SnapshotParseSingleInchValue.
'
' Why it exists:
'   Snapshots let intake workbooks display and scan against current delivery
'   data without opening or editing the master workbook.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SnapshotParseSingleInchValue(ByVal valueText As String) As Double
    Dim cleaned As String
    Dim tokens As Variant
    Dim token As Variant
    Dim fracParts As Variant
    Dim numerator As Double
    Dim denominator As Double
    Dim total As Double

    cleaned = Trim$(CStr(valueText))
    cleaned = Replace$(cleaned, ChrW$(160), " ")
    cleaned = Replace$(cleaned, "-", " ")

    Do While InStr(1, cleaned, "  ", vbBinaryCompare) > 0
        cleaned = Replace$(cleaned, "  ", " ")
    Loop

    If Len(cleaned) = 0 Then Exit Function

    tokens = Split(cleaned, " ")
    For Each token In tokens
        token = Trim$(CStr(token))
        If Len(token) > 0 Then
            If InStr(1, token, "/", vbBinaryCompare) > 0 Then
                fracParts = Split(CStr(token), "/")
                If UBound(fracParts) = 1 Then
                    If IsNumeric(fracParts(0)) And IsNumeric(fracParts(1)) Then
                        numerator = CDbl(fracParts(0))
                        denominator = CDbl(fracParts(1))
                        If denominator <> 0 Then total = total + (numerator / denominator)
                    End If
                End If
            ElseIf IsNumeric(token) Then
                total = total + CDbl(token)
            End If
        End If
    Next token

    SnapshotParseSingleInchValue = total
End Function

'------------------------------------------------------------------------------
' Procedure: SnapshotPossibleOversized
' Scope: Private Function
'
' What it does:
'   Handles part of the master-to-intake snapshot workflow for
'   SnapshotPossibleOversized.
'
' Why it exists:
'   Snapshots let intake workbooks display and scan against current delivery
'   data without opening or editing the master workbook.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SnapshotPossibleOversized(ByVal widthInches As Double, ByVal heightInches As Double) As Boolean
    Dim maxDim As Double
    Dim minDim As Double

    If widthInches <= 0 Or heightInches <= 0 Then Exit Function

    If widthInches >= heightInches Then
        maxDim = widthInches
        minDim = heightInches
    Else
        maxDim = heightInches
        minDim = widthInches
    End If

    'Reference only. Oversized is still a manual receiving decision.
    SnapshotPossibleOversized = (maxDim >= 105# Or minDim >= 56#)
End Function

'------------------------------------------------------------------------------
' Procedure: BuildIndianTrailHeaderRoutingDebugSheet
' Scope: Private Sub
'
' What it does:
'   Finds, writes, validates, or uses worksheet header cells for
'   BuildIndianTrailHeaderRoutingDebugSheet.
'
' Why it exists:
'   Header locations can move during import/rebuild, so the code uses header
'   discovery to target the correct columns instead of guessing.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub BuildIndianTrailHeaderRoutingDebugSheet(ByVal sourceWs As Worksheet)
    Dim debugWs As Worksheet
    Dim headerRow As Long
    Dim orderCol As Long
    Dim itemCol As Long
    Dim qtyCol As Long
    Dim dimensionsCol As Long
    Dim lastRow As Long
    Dim r As Long
    Dim outRow As Long
    Dim currentGlassHeader As String
    Dim currentHeaderRow As Long
    Dim glassCategory As String
    Dim bayCategory As String
    Dim routingWarning As String
    Dim dimensionsText As String
    Dim widthInches As Double
    Dim heightInches As Double
    Dim maxDimensionInches As Double
    Dim parsedDimensions As Boolean
    Dim possibleOversized As Boolean

    If sourceWs Is Nothing Then Exit Sub

    headerRow = SnapshotFindMainHeaderRow(sourceWs, orderCol, itemCol)
    If headerRow = 0 Then
        MsgBox "Could not find Order Nr. and Item Nr. headers on " & sourceWs.Name & ".", vbExclamation, "Header Routing Debug"
        Exit Sub
    End If

    qtyCol = SnapshotFindHeaderColInRowByNames(sourceWs, headerRow, Array("Qty.", "Qty", "Quantity"))
    dimensionsCol = SnapshotFindHeaderColInRowByNames(sourceWs, headerRow, Array("Dimensions", "Dimension", "Dim", "Size"))
    If qtyCol = 0 Then qtyCol = 7
    If dimensionsCol = 0 Then dimensionsCol = 8

    Application.DisplayAlerts = False
    On Error Resume Next
    ThisWorkbook.Worksheets("__HEADER_PARSE_DEBUG__").Delete
    On Error GoTo 0
    Application.DisplayAlerts = True

    Set debugWs = ThisWorkbook.Worksheets.Add(After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
    debugWs.Name = "__HEADER_PARSE_DEBUG__"

    debugWs.Range("A1:M1").Value = Array( _
        "SourceSheet", "SheetRow", "OrderNumber", "ItemNumber", "Qty", "Dimensions", _
        "GlassHeader", "HeaderRowIndex", "GlassCategory", "BayCategory", _
        "PossibleOversized", "MaxDimensionInches", "RoutingWarning")

    outRow = 2
    lastRow = sourceWs.Cells(sourceWs.rows.Count, orderCol).End(xlUp).Row

    For r = headerRow + 1 To lastRow
        If SnapshotRowIsSectionHeader(sourceWs, r, orderCol, itemCol) Then
            currentGlassHeader = SnapshotCellText(sourceWs.Cells(r, 1))
            currentHeaderRow = r
            SnapshotClassifyGlassHeader currentGlassHeader, glassCategory, bayCategory, routingWarning

        ElseIf SnapshotRowIsDeliveryLine(sourceWs, r, orderCol, itemCol) Then
            If Len(Trim$(currentGlassHeader)) = 0 Then
                currentHeaderRow = 0
                SnapshotClassifyGlassHeader currentGlassHeader, glassCategory, bayCategory, routingWarning
            End If

            dimensionsText = SnapshotCellText(sourceWs.Cells(r, dimensionsCol))
            widthInches = 0
            heightInches = 0
            maxDimensionInches = 0
            parsedDimensions = SnapshotParseDimensionsInches(dimensionsText, widthInches, heightInches, maxDimensionInches)
            possibleOversized = False

            If parsedDimensions Then
                possibleOversized = SnapshotPossibleOversized(widthInches, heightInches)
                If possibleOversized Then
                    If Len(routingWarning) > 0 Then routingWarning = routingWarning & " | "
                    routingWarning = routingWarning & "Possible oversized - receiving must decide manually"
                End If
            End If

            debugWs.Cells(outRow, 1).Value = sourceWs.Name
            debugWs.Cells(outRow, 2).Value = r
            debugWs.Cells(outRow, 3).Value = SnapshotSafeLong(sourceWs.Cells(r, orderCol).Value)
            debugWs.Cells(outRow, 4).Value = SnapshotSafeLong(sourceWs.Cells(r, itemCol).Value)
            debugWs.Cells(outRow, 5).Value = SnapshotSafeLong(sourceWs.Cells(r, qtyCol).Value)
            debugWs.Cells(outRow, 6).Value = dimensionsText
            debugWs.Cells(outRow, 7).Value = currentGlassHeader
            debugWs.Cells(outRow, 8).Value = currentHeaderRow
            debugWs.Cells(outRow, 9).Value = glassCategory
            debugWs.Cells(outRow, 10).Value = bayCategory
            debugWs.Cells(outRow, 11).Value = possibleOversized
            debugWs.Cells(outRow, 12).Value = maxDimensionInches
            debugWs.Cells(outRow, 13).Value = routingWarning
            outRow = outRow + 1
        End If
    Next r

    With debugWs.Range("A1:M1")
        .Font.Bold = True
        .Interior.Color = RGB(220, 230, 241)
    End With

    debugWs.Columns("A:M").AutoFit
    debugWs.Activate

    MsgBox "Header routing debug complete." & vbCrLf & _
           "Rows written: " & (outRow - 2), vbInformation, "Header Routing Debug"
End Sub

'------------------------------------------------------------------------------
' Procedure: SnapshotGetActiveBlockColumns
' Scope: Private Sub
'
' What it does:
'   Finds, sizes, hides, formats, or uses worksheet columns for
'   SnapshotGetActiveBlockColumns.
'
' Why it exists:
'   The system depends on fixed scan blocks and discovered delivery-list
'   columns, so column handling must be centralized and predictable.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub SnapshotGetActiveBlockColumns(ByVal modeText As String, _
                                          ByRef barcodeCol As Long, _
                                          ByRef qtyCol As Long, _
                                          ByRef timeCol As Long, _
                                          ByRef checkCol As Long, _
                                          ByRef commentCol As Long, _
                                          ByRef bayCol As Long)
    Select Case UCase$(Trim$(modeText))
        Case "SEND"
            barcodeCol = 16
            qtyCol = 19
            timeCol = 20
            checkCol = 21
            commentCol = 23
            bayCol = 0

        Case "RECV"
            barcodeCol = 25
            qtyCol = 28
            timeCol = 29
            checkCol = 30
            commentCol = 32
            bayCol = 33

        Case "STAGING"
            barcodeCol = 42
            qtyCol = 45
            timeCol = 46
            checkCol = 47
            commentCol = 48
            bayCol = 0
    End Select
End Sub

'------------------------------------------------------------------------------
' Procedure: SnapshotRangeValuesJson
' Scope: Private Function
'
' What it does:
'   Parses, builds, or safely transforms JSON text used by the Power Automate
'   bridge (SnapshotRangeValuesJson).
'
' Why it exists:
'   The intake workbook reconstructs its visible sheet from snapshot JSON, so
'   row data and formatting details must be serialized predictably.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SnapshotRangeValuesJson(ByVal ws As Worksheet, ByVal rowNum As Long, ByVal firstCol As Long, ByVal lastCol As Long) As String
    Dim c As Long
    Dim out As String

    For c = firstCol To lastCol
        If Len(out) > 0 Then out = out & ","
        out = out & SnapshotJsonString(SnapshotCellText(ws.Cells(rowNum, c)))
    Next c

    SnapshotRangeValuesJson = "[" & out & "]"
End Function

'------------------------------------------------------------------------------
' Procedure: SnapshotFindMainHeaderRow
' Scope: Private Function
'
' What it does:
'   Finds, writes, validates, or uses worksheet header cells for
'   SnapshotFindMainHeaderRow.
'
' Why it exists:
'   The intake workbook reconstructs its visible sheet from snapshot JSON, so
'   row data and formatting details must be serialized predictably.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SnapshotFindMainHeaderRow(ByVal ws As Worksheet, ByRef orderCol As Long, ByRef itemCol As Long) As Long
    Dim r As Long
    Dim c As Long
    Dim orderFoundCol As Long
    Dim itemFoundCol As Long

    For r = 1 To 250
        orderFoundCol = 0
        itemFoundCol = 0

        For c = 1 To 14
            If StrComp(Trim$(CStr(ws.Cells(r, c).Value)), "Order Nr.", vbTextCompare) = 0 Then
                orderFoundCol = c
            ElseIf StrComp(Trim$(CStr(ws.Cells(r, c).Value)), "Item Nr.", vbTextCompare) = 0 Or _
                   StrComp(Trim$(CStr(ws.Cells(r, c).Value)), "Item", vbTextCompare) = 0 Then
                itemFoundCol = c
            End If
        Next c

        If orderFoundCol > 0 And itemFoundCol > 0 Then
            orderCol = orderFoundCol
            itemCol = itemFoundCol
            SnapshotFindMainHeaderRow = r
            Exit Function
        End If
    Next r
End Function

'------------------------------------------------------------------------------
' Procedure: SnapshotFindHeaderColInRowByNames
' Scope: Private Function
'
' What it does:
'   Finds, writes, validates, or uses worksheet header cells for
'   SnapshotFindHeaderColInRowByNames.
'
' Why it exists:
'   The intake workbook reconstructs its visible sheet from snapshot JSON, so
'   row data and formatting details must be serialized predictably.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SnapshotFindHeaderColInRowByNames(ByVal ws As Worksheet, ByVal headerRow As Long, ByVal headerNames As Variant) As Long
    Dim nm As Variant
    Dim f As Range

    If headerRow <= 0 Then Exit Function

    For Each nm In headerNames
        Set f = ws.rows(headerRow).Find(What:=CStr(nm), LookIn:=xlValues, LookAt:=xlWhole, MatchCase:=False)
        If Not f Is Nothing Then
            SnapshotFindHeaderColInRowByNames = f.Column
            Exit Function
        End If
    Next nm

    For Each nm In headerNames
        Set f = ws.rows(headerRow).Find(What:=CStr(nm), LookIn:=xlValues, LookAt:=xlPart, MatchCase:=False)
        If Not f Is Nothing Then
            SnapshotFindHeaderColInRowByNames = f.Column
            Exit Function
        End If
    Next nm
End Function

'------------------------------------------------------------------------------
' Procedure: SnapshotRowIsSectionHeader
' Scope: Private Function
'
' What it does:
'   Finds, writes, validates, or uses worksheet header cells for
'   SnapshotRowIsSectionHeader.
'
' Why it exists:
'   The intake workbook reconstructs its visible sheet from snapshot JSON, so
'   row data and formatting details must be serialized predictably.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SnapshotRowIsSectionHeader(ByVal ws As Worksheet, _
                                            ByVal rowNum As Long, _
                                            ByVal orderCol As Long, _
                                            ByVal itemCol As Long) As Boolean
    Dim leftText As String
    Dim orderText As String
    Dim itemText As String

    If ws Is Nothing Then Exit Function
    If rowNum <= 0 Then Exit Function

    leftText = Trim$(CStr(ws.Cells(rowNum, 1).Value))
    orderText = Trim$(CStr(ws.Cells(rowNum, orderCol).Value))
    itemText = Trim$(CStr(ws.Cells(rowNum, itemCol).Value))

    'Section headers are rows like "3/8 CLEAR TEMPERED":
    'text on the left, but no order/item values.
    SnapshotRowIsSectionHeader = _
        (Len(leftText) > 0 And Len(orderText) = 0 And Len(itemText) = 0)
End Function

'------------------------------------------------------------------------------
' Procedure: SnapshotRowIsDeliveryLine
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   SnapshotRowIsDeliveryLine.
'
' Why it exists:
'   The intake workbook reconstructs its visible sheet from snapshot JSON, so
'   row data and formatting details must be serialized predictably.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SnapshotRowIsDeliveryLine(ByVal ws As Worksheet, ByVal rowNum As Long, ByVal orderCol As Long, ByVal itemCol As Long) As Boolean
    Dim ord As Long
    Dim itm As Long

    ord = SnapshotSafeLong(ws.Cells(rowNum, orderCol).Value)
    itm = SnapshotSafeLong(ws.Cells(rowNum, itemCol).Value)

    SnapshotRowIsDeliveryLine = (ord > 0 And itm > 0)
End Function

'------------------------------------------------------------------------------
' Procedure: SnapshotFindDeliveryTitle
' Scope: Private Function
'
' What it does:
'   Handles part of the master-to-intake snapshot workflow for
'   SnapshotFindDeliveryTitle.
'
' Why it exists:
'   Snapshots let intake workbooks display and scan against current delivery
'   data without opening or editing the master workbook.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SnapshotFindDeliveryTitle(ByVal ws As Worksheet) As String
    Dim c As Range
    Dim txt As String

    For Each c In ws.Range("A1:AG5").Cells
        txt = Trim$(CStr(c.Value))
        If InStr(1, txt, "DELIVERY LIST", vbTextCompare) > 0 Then
            SnapshotFindDeliveryTitle = txt
            Exit Function
        End If
    Next c

    SnapshotFindDeliveryTitle = ws.Name
End Function

'------------------------------------------------------------------------------
' Procedure: SnapshotStageKeyFromProfile
' Scope: Private Function
'
' What it does:
'   Handles part of the master-to-intake snapshot workflow for
'   SnapshotStageKeyFromProfile.
'
' Why it exists:
'   Snapshots let intake workbooks display and scan against current delivery
'   data without opening or editing the master workbook.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SnapshotStageKeyFromProfile(ByVal stageProfile As String) As String
    Select Case UCase$(Trim$(stageProfile))
        Case "STAGING - AIRPORT RD"
            SnapshotStageKeyFromProfile = "STAGING_AIRPORT_RD"

        Case "OUTBOUND - AIRPORT RD"
            SnapshotStageKeyFromProfile = "OUTBOUND_AIRPORT_RD"

        Case "INBOUND - INDIAN TRAIL"
            SnapshotStageKeyFromProfile = "INBOUND_INDIAN_TRAIL"

        Case "INBOUND - GREENVILLE"
            SnapshotStageKeyFromProfile = "INBOUND_GREENVILLE"

        Case "CUSTOMER PICKUP"
            SnapshotStageKeyFromProfile = "CUSTOMER_PICKUP"
    End Select
End Function

'------------------------------------------------------------------------------
' Procedure: SnapshotStageSheetFromProfile
' Scope: Private Function
'
' What it does:
'   Finds, creates, deletes, rebuilds, protects, or synchronizes worksheets
'   for SnapshotStageSheetFromProfile.
'
' Why it exists:
'   The master workbook creates multiple operational views from one delivery
'   list; worksheet helpers keep those views from drifting apart.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SnapshotStageSheetFromProfile(ByVal stageProfile As String) As String
    Select Case UCase$(Trim$(stageProfile))
        Case "STAGING - AIRPORT RD"
            SnapshotStageSheetFromProfile = "Staging - Airport Rd"

        Case "OUTBOUND - AIRPORT RD"
            SnapshotStageSheetFromProfile = "Outbound - Airport Rd"

        Case "INBOUND - INDIAN TRAIL"
            SnapshotStageSheetFromProfile = "Inbound - Indian Trail"

        Case "INBOUND - GREENVILLE"
            SnapshotStageSheetFromProfile = "Inbound - Greenville"

        Case "CUSTOMER PICKUP"
            SnapshotStageSheetFromProfile = "Customer Pickup"
    End Select
End Function

'------------------------------------------------------------------------------
' Procedure: SnapshotModeFromStageProfile
' Scope: Private Function
'
' What it does:
'   Handles part of the master-to-intake snapshot workflow for
'   SnapshotModeFromStageProfile.
'
' Why it exists:
'   Snapshots let intake workbooks display and scan against current delivery
'   data without opening or editing the master workbook.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SnapshotModeFromStageProfile(ByVal stageProfile As String) As String
    Select Case UCase$(Trim$(stageProfile))
        Case "STAGING - AIRPORT RD"
            SnapshotModeFromStageProfile = "STAGING"

        Case "OUTBOUND - AIRPORT RD"
            SnapshotModeFromStageProfile = "SEND"

        Case "INBOUND - INDIAN TRAIL", _
             "INBOUND - GREENVILLE", _
             "CUSTOMER PICKUP"
            SnapshotModeFromStageProfile = "RECV"
    End Select
End Function

'------------------------------------------------------------------------------
' Procedure: SnapshotCellText
' Scope: Private Function
'
' What it does:
'   Handles part of the master-to-intake snapshot workflow for
'   SnapshotCellText.
'
' Why it exists:
'   Snapshots let intake workbooks display and scan against current delivery
'   data without opening or editing the master workbook.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SnapshotCellText(ByVal c As Range) As String
    Dim v As Variant
    Dim numberFormatText As String

    If c Is Nothing Then Exit Function

    v = c.Value

    If IsError(v) Then Exit Function
    If IsEmpty(v) Then Exit Function

    numberFormatText = LCase$(CStr(c.NumberFormat))

    If IsDate(v) Then
        If InStr(1, numberFormatText, "m", vbTextCompare) > 0 And _
           InStr(1, numberFormatText, "d", vbTextCompare) > 0 Then
            SnapshotCellText = Format$(CDate(v), "m/d/yyyy h:mm AM/PM")
            Exit Function
        End If
    End If

    SnapshotCellText = CStr(v)
End Function

'------------------------------------------------------------------------------
' Procedure: SnapshotSafeLong
' Scope: Private Function
'
' What it does:
'   Handles part of the master-to-intake snapshot workflow for
'   SnapshotSafeLong.
'
' Why it exists:
'   Snapshots let intake workbooks display and scan against current delivery
'   data without opening or editing the master workbook.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SnapshotSafeLong(ByVal valueIn As Variant) As Long
    Dim s As String

    If IsError(valueIn) Then Exit Function

    s = CStr(valueIn)
    s = Replace$(s, ",", vbNullString)
    s = Trim$(s)

    If Len(s) = 0 Then Exit Function

    SnapshotSafeLong = CLng(Val(s))
End Function

'------------------------------------------------------------------------------
' Procedure: SnapshotJsonString
' Scope: Private Function
'
' What it does:
'   Parses, builds, or safely transforms JSON text used by the Power Automate
'   bridge (SnapshotJsonString).
'
' Why it exists:
'   The intake workbook reconstructs its visible sheet from snapshot JSON, so
'   row data and formatting details must be serialized predictably.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SnapshotJsonString(ByVal valueText As String) As String
    Dim s As String

    s = CStr(valueText)

    s = Replace$(s, "\", "\\")
    s = Replace$(s, """", "\""")
    s = Replace$(s, "/", "\/")
    s = Replace$(s, vbCrLf, "\n")
    s = Replace$(s, vbCr, "\n")
    s = Replace$(s, vbLf, "\n")
    s = Replace$(s, vbTab, "\t")

    SnapshotJsonString = """" & s & """"
End Function

'------------------------------------------------------------------------------
' Procedure: SnapshotStageKeyFromProfilePublic
' Scope: Public Function
'
' What it does:
'   Handles part of the master-to-intake snapshot workflow for
'   SnapshotStageKeyFromProfilePublic.
'
' Why it exists:
'   Snapshots let intake workbooks display and scan against current delivery
'   data without opening or editing the master workbook.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function SnapshotStageKeyFromProfilePublic(ByVal stageProfile As String) As String
    SnapshotStageKeyFromProfilePublic = SnapshotStageKeyFromProfile(stageProfile)
End Function

'------------------------------------------------------------------------------
' Procedure: SnapshotTopRowsJson
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   SnapshotTopRowsJson.
'
' Why it exists:
'   The intake workbook reconstructs its visible sheet from snapshot JSON, so
'   row data and formatting details must be serialized predictably.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SnapshotTopRowsJson(ByVal ws As Worksheet, ByVal headerRow As Long) As String
    Dim r As Long
    Dim out As String

    If ws Is Nothing Then
        SnapshotTopRowsJson = "[]"
        Exit Function
    End If

    If headerRow <= 1 Then
        SnapshotTopRowsJson = "[]"
        Exit Function
    End If

    For r = 1 To headerRow - 1
        If Len(out) > 0 Then out = out & ","
        out = out & SnapshotRangeValuesJson(ws, r, 1, 48) 'A:AV
    Next r

    SnapshotTopRowsJson = "[" & out & "]"
End Function

'------------------------------------------------------------------------------
' Procedure: SnapshotSheetFormatJson
' Scope: Private Function
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   SnapshotSheetFormatJson.
'
' Why it exists:
'   The intake workbook reconstructs its visible sheet from snapshot JSON, so
'   row data and formatting details must be serialized predictably.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SnapshotSheetFormatJson(ByVal ws As Worksheet, ByVal headerRow As Long, ByVal lastRow As Long) As String
    If ws Is Nothing Then
        SnapshotSheetFormatJson = "{}"
        Exit Function
    End If

    If headerRow <= 0 Then headerRow = 5
    If lastRow < headerRow Then lastRow = headerRow

    SnapshotSheetFormatJson = "{" & _
        """columns"":" & SnapshotColumnFormatsJson(ws, 1, 48) & "," & _
        """rows"":" & SnapshotRowFormatsJson(ws, 1, lastRow) & "," & _
        """merges"":" & SnapshotMergeFormatsJson(ws, 1, lastRow, 1, 48) & "," & _
        """cells"":" & SnapshotCellFormatsJson(ws, 1, lastRow, 1, 48) & _
        "}"
End Function

'------------------------------------------------------------------------------
' Procedure: SnapshotColumnFormatsJson
' Scope: Private Function
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   SnapshotColumnFormatsJson.
'
' Why it exists:
'   The intake workbook reconstructs its visible sheet from snapshot JSON, so
'   row data and formatting details must be serialized predictably.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SnapshotColumnFormatsJson(ByVal ws As Worksheet, ByVal firstCol As Long, ByVal lastCol As Long) As String
    Dim c As Long
    Dim out As String

    For c = firstCol To lastCol
        If Len(out) > 0 Then out = out & ","

        out = out & "{" & _
            """c"":" & CStr(c) & "," & _
            """w"":" & SnapshotNumberText(ws.Columns(c).ColumnWidth) & "," & _
            """hidden"":" & SnapshotBoolJson(ws.Columns(c).Hidden) & _
            "}"
    Next c

    SnapshotColumnFormatsJson = "[" & out & "]"
End Function

'------------------------------------------------------------------------------
' Procedure: SnapshotRowFormatsJson
' Scope: Private Function
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   SnapshotRowFormatsJson.
'
' Why it exists:
'   The intake workbook reconstructs its visible sheet from snapshot JSON, so
'   row data and formatting details must be serialized predictably.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SnapshotRowFormatsJson(ByVal ws As Worksheet, ByVal firstRow As Long, ByVal lastRow As Long) As String
    Dim r As Long
    Dim out As String

    For r = firstRow To lastRow
        If Len(out) > 0 Then out = out & ","

        out = out & "{" & _
            """r"":" & CStr(r) & "," & _
            """h"":" & SnapshotNumberText(ws.rows(r).RowHeight) & "," & _
            """hidden"":" & SnapshotBoolJson(ws.rows(r).Hidden) & _
            "}"
    Next r

    SnapshotRowFormatsJson = "[" & out & "]"
End Function

'------------------------------------------------------------------------------
' Procedure: SnapshotMergeFormatsJson
' Scope: Private Function
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   SnapshotMergeFormatsJson.
'
' Why it exists:
'   The intake workbook reconstructs its visible sheet from snapshot JSON, so
'   row data and formatting details must be serialized predictably.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SnapshotMergeFormatsJson(ByVal ws As Worksheet, _
                                          ByVal firstRow As Long, ByVal lastRow As Long, _
                                          ByVal firstCol As Long, ByVal lastCol As Long) As String
    Dim seen As Object
    Dim r As Long
    Dim c As Long
    Dim ma As Range
    Dim key As String
    Dim out As String

    Set seen = CreateObject("Scripting.Dictionary")

    On Error Resume Next

    For r = firstRow To lastRow
        For c = firstCol To lastCol
            If ws.Cells(r, c).MergeCells Then
                Set ma = ws.Cells(r, c).MergeArea
                key = ma.Address(False, False)

                If Not seen.Exists(key) Then
                    seen.Add key, True

                    If Len(out) > 0 Then out = out & ","

                    out = out & "{" & _
                        """addr"":" & SnapshotJsonString(key) & _
                        "}"
                End If
            End If
        Next c
    Next r

    On Error GoTo 0

    SnapshotMergeFormatsJson = "[" & out & "]"
End Function

'------------------------------------------------------------------------------
' Procedure: SnapshotCellFormatsJson
' Scope: Private Function
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   SnapshotCellFormatsJson.
'
' Why it exists:
'   The intake workbook reconstructs its visible sheet from snapshot JSON, so
'   row data and formatting details must be serialized predictably.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SnapshotCellFormatsJson(ByVal ws As Worksheet, _
                                         ByVal firstRow As Long, ByVal lastRow As Long, _
                                         ByVal firstCol As Long, ByVal lastCol As Long) As String
    Dim r As Long
    Dim c As Long
    Dim out As String

    For r = firstRow To lastRow
        For c = firstCol To lastCol
            If SnapshotCellNeedsFormat(ws.Cells(r, c), r, c) Then
                If Len(out) > 0 Then out = out & ","
                out = out & SnapshotCellFormatJson(ws.Cells(r, c))
            End If
        Next c
    Next r

    SnapshotCellFormatsJson = "[" & out & "]"
End Function

'------------------------------------------------------------------------------
' Procedure: SnapshotCellNeedsFormat
' Scope: Private Function
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   SnapshotCellNeedsFormat.
'
' Why it exists:
'   The intake workbook reconstructs its visible sheet from snapshot JSON, so
'   row data and formatting details must be serialized predictably.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SnapshotCellNeedsFormat(ByVal cell As Range, ByVal rowNum As Long, ByVal colNum As Long) As Boolean
    If cell Is Nothing Then Exit Function

    'Always include top/header areas and scanner-panel area.
    If rowNum <= 5 Then
        SnapshotCellNeedsFormat = True
        Exit Function
    End If

    'Always include A:AV cells that contain values.
    If Len(Trim$(CStr(cell.Value))) > 0 Then
        SnapshotCellNeedsFormat = True
        Exit Function
    End If

    'Include cells that visually matter even if blank.
    If cell.MergeCells Then
        SnapshotCellNeedsFormat = True
        Exit Function
    End If

    If cell.Interior.Pattern <> xlNone Then
        SnapshotCellNeedsFormat = True
        Exit Function
    End If

    If SnapshotCellHasBorder(cell) Then
        SnapshotCellNeedsFormat = True
        Exit Function
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: SnapshotCellFormatJson
' Scope: Private Function
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   SnapshotCellFormatJson.
'
' Why it exists:
'   The intake workbook reconstructs its visible sheet from snapshot JSON, so
'   row data and formatting details must be serialized predictably.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SnapshotCellFormatJson(ByVal cell As Range) As String
    SnapshotCellFormatJson = "{" & _
        """a"":" & SnapshotJsonString(cell.Address(False, False)) & "," & _
        """nf"":" & SnapshotJsonString(CStr(cell.NumberFormat)) & "," & _
        """font"":" & SnapshotJsonString(CStr(cell.Font.Name)) & "," & _
        """fs"":" & SnapshotNumberText(cell.Font.Size) & "," & _
        """bold"":" & SnapshotBoolJson(cell.Font.Bold) & "," & _
        """italic"":" & SnapshotBoolJson(cell.Font.Italic) & "," & _
        """underline"":" & CStr(CLng(cell.Font.Underline)) & "," & _
        """fontColor"":" & SnapshotColorJson(cell.Font.Color) & "," & _
        """fillPattern"":" & CStr(CLng(cell.Interior.Pattern)) & "," & _
        """fillColor"":" & SnapshotColorJson(cell.Interior.Color) & "," & _
        """hAlign"":" & CStr(CLng(cell.HorizontalAlignment)) & "," & _
        """vAlign"":" & CStr(CLng(cell.VerticalAlignment)) & "," & _
        """wrap"":" & SnapshotBoolJson(cell.WrapText) & "," & _
        """border"":" & SnapshotBorderJson(cell) & _
        "}"
End Function

'------------------------------------------------------------------------------
' Procedure: SnapshotBorderJson
' Scope: Private Function
'
' What it does:
'   Parses, builds, or safely transforms JSON text used by the Power Automate
'   bridge (SnapshotBorderJson).
'
' Why it exists:
'   The intake workbook reconstructs its visible sheet from snapshot JSON, so
'   row data and formatting details must be serialized predictably.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SnapshotBorderJson(ByVal cell As Range) As String
    SnapshotBorderJson = "{" & _
        """l"":" & SnapshotOneBorderJson(cell.Borders(xlEdgeLeft)) & "," & _
        """t"":" & SnapshotOneBorderJson(cell.Borders(xlEdgeTop)) & "," & _
        """r"":" & SnapshotOneBorderJson(cell.Borders(xlEdgeRight)) & "," & _
        """b"":" & SnapshotOneBorderJson(cell.Borders(xlEdgeBottom)) & _
        "}"
End Function

'------------------------------------------------------------------------------
' Procedure: SnapshotOneBorderJson
' Scope: Private Function
'
' What it does:
'   Parses, builds, or safely transforms JSON text used by the Power Automate
'   bridge (SnapshotOneBorderJson).
'
' Why it exists:
'   The intake workbook reconstructs its visible sheet from snapshot JSON, so
'   row data and formatting details must be serialized predictably.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SnapshotOneBorderJson(ByVal b As Border) As String
    SnapshotOneBorderJson = "{" & _
        """ls"":" & CStr(CLng(b.LineStyle)) & "," & _
        """w"":" & CStr(CLng(b.Weight)) & "," & _
        """c"":" & SnapshotColorJson(b.Color) & _
        "}"
End Function

'------------------------------------------------------------------------------
' Procedure: SnapshotCellHasBorder
' Scope: Private Function
'
' What it does:
'   Handles part of the master-to-intake snapshot workflow for
'   SnapshotCellHasBorder.
'
' Why it exists:
'   Snapshots let intake workbooks display and scan against current delivery
'   data without opening or editing the master workbook.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SnapshotCellHasBorder(ByVal cell As Range) As Boolean
    On Error Resume Next

    SnapshotCellHasBorder = _
        (cell.Borders(xlEdgeLeft).LineStyle <> xlNone) Or _
        (cell.Borders(xlEdgeTop).LineStyle <> xlNone) Or _
        (cell.Borders(xlEdgeRight).LineStyle <> xlNone) Or _
        (cell.Borders(xlEdgeBottom).LineStyle <> xlNone)

    On Error GoTo 0
End Function

'------------------------------------------------------------------------------
' Procedure: SnapshotBoolJson
' Scope: Private Function
'
' What it does:
'   Parses, builds, or safely transforms JSON text used by the Power Automate
'   bridge (SnapshotBoolJson).
'
' Why it exists:
'   The intake workbook reconstructs its visible sheet from snapshot JSON, so
'   row data and formatting details must be serialized predictably.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SnapshotBoolJson(ByVal valueIn As Boolean) As String
    If valueIn Then
        SnapshotBoolJson = "true"
    Else
        SnapshotBoolJson = "false"
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: SnapshotColorJson
' Scope: Private Function
'
' What it does:
'   Finds, sizes, hides, formats, or uses worksheet columns for
'   SnapshotColorJson.
'
' Why it exists:
'   The intake workbook reconstructs its visible sheet from snapshot JSON, so
'   row data and formatting details must be serialized predictably.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SnapshotColorJson(ByVal valueIn As Variant) As String
    On Error GoTo NoColor

    If IsError(valueIn) Then GoTo NoColor

    SnapshotColorJson = CStr(CLng(valueIn))
    Exit Function

NoColor:
    SnapshotColorJson = "null"
End Function

'------------------------------------------------------------------------------
' Procedure: SnapshotNumberText
' Scope: Private Function
'
' What it does:
'   Handles part of the master-to-intake snapshot workflow for
'   SnapshotNumberText.
'
' Why it exists:
'   Snapshots let intake workbooks display and scan against current delivery
'   data without opening or editing the master workbook.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SnapshotNumberText(ByVal valueIn As Variant) As String
    Dim s As String

    s = CStr(valueIn)
    s = Replace$(s, ",", "")
    s = Trim$(s)

    If Len(s) = 0 Or Not IsNumeric(s) Then
        SnapshotNumberText = "0"
    Else
        SnapshotNumberText = s
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: ManualPublishAllStageSnapshots
' Scope: Public Sub
'
' What it does:
'   Handles part of the master-to-intake snapshot workflow for
'   ManualPublishAllStageSnapshots.
'
' Why it exists:
'   Snapshots let intake workbooks display and scan against current delivery
'   data without opening or editing the master workbook.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub ManualPublishAllStageSnapshots()
    Dim profiles As Variant
    Dim profile As Variant
    Dim okCount As Long
    Dim failCount As Long
    Dim failText As String
    Dim failReason As String
    Dim oldStatusBar As Variant

    On Error GoTo ErrHandler

    If ThisWorkbook.ReadOnly Then
        MsgBox "This master workbook is open read-only." & vbCrLf & vbCrLf & _
               "Snapshots cannot be published from a read-only master.", _
               vbExclamation, "Publish Snapshots"
        Exit Sub
    End If

    profiles = Array( _
        "Staging - Airport Rd", _
        "Outbound - Airport Rd", _
        "Inbound - Indian Trail", _
        "Inbound - Greenville", _
        "Customer Pickup" _
    )

    oldStatusBar = Application.StatusBar
    Application.StatusBar = "Publishing stage snapshots to SharePoint..."

    For Each profile In profiles
        failReason = vbNullString

        Application.StatusBar = "Publishing snapshot: " & CStr(profile) & "..."

        If PublishStageSnapshot(CStr(profile), False, failReason) Then
            okCount = okCount + 1
        Else
            failCount = failCount + 1

            If Len(Trim$(failReason)) = 0 Then
                failReason = "Unknown publish failure."
            End If

            failText = failText & "• " & CStr(profile) & ": " & failReason & vbCrLf
        End If

        DoEvents
    Next profile

    Application.StatusBar = oldStatusBar

    If failCount = 0 Then
        MsgBox "Snapshots published successfully." & vbCrLf & vbCrLf & _
               "Published: " & okCount, _
               vbInformation, "Publish Snapshots"
    Else
        MsgBox "Snapshot publish finished with issues." & vbCrLf & vbCrLf & _
               "Published: " & okCount & vbCrLf & _
               "Failed: " & failCount & vbCrLf & vbCrLf & _
               failText, _
               vbExclamation, "Publish Snapshots"
    End If

    Exit Sub

ErrHandler:
    Application.StatusBar = oldStatusBar

    MsgBox "Manual snapshot publish failed." & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbExclamation, "Publish Snapshots"
End Sub

'------------------------------------------------------------------------------
' Procedure: RemoveExtraPublishSnapshotButtons
' Scope: Public Sub
'
' What it does:
'   Builds, formats, deletes, or wires workbook UI shapes/buttons/panels for
'   RemoveExtraPublishSnapshotButtons.
'
' Why it exists:
'   Buttons and utility panels are the operator-facing control surface, so
'   they must be rebuilt consistently after imports or sheet refreshes.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub RemoveExtraPublishSnapshotButtons()
    Dim ws As Worksheet

    For Each ws In ThisWorkbook.Worksheets
        If UCase$(ws.Name) <> UCase$("Utility Panel") _
           And UCase$(ws.Name) <> UCase$("Scanning Panel") Then

            On Error Resume Next
            ws.Shapes("btnManualPublishSnapshots").Delete
            On Error GoTo 0
        End If
    Next ws

    MsgBox "Extra Publish Snapshots buttons were removed from delivery/scanning sheets. The main panel button was left alone.", _
           vbInformation, "Publish Snapshots Button Cleanup"
End Sub
