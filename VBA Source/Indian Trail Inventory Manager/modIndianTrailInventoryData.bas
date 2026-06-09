Attribute VB_Name = "modIndianTrailInventoryData"
Option Explicit

'Runtime data/actions for the Indian Trail bay map.
'The workbook can refresh from the exported SharePoint CSV files today.
'Live write-back is routed through one optional Power Automate admin flow URL.

Private Const ITIM_PANEL_SHEET As String = "Inventory Manager"
Private Const ITIM_MAP_SHEET As String = "Bay Map"
Private Const ITIM_ASSIGNMENTS_SHEET As String = "ITIM_Assignments"
Private Const ITIM_BAYS_SHEET As String = "ITIM_Bays"
Private Const ITIM_SPECIAL_SHEET As String = "ITIM_SpecialOrders"
Private Const ITIM_SDI_PRINT_SHEET As String = "SDI Print"
Private Const ITIM_STATUS_CELL As String = "M7"
Private Const ITIM_MAP_STATUS_RANGE As String = "Q18:U18"

Private Const ITIM_ASSIGNMENTS_CSV As String = "IndianTrailBayAssignments.csv"
Private Const ITIM_BAYS_CSV As String = "IndianTrailBays.csv"
Private Const ITIM_SPECIAL_CSV As String = "IndianTrailSpecialOrders.csv"

'Paste the manual-admin Power Automate HTTP trigger URL here after creating the flow.
Private Const ITIM_URL_BAY_ADMIN_ACTION As String = "https://default2506d8b9503e40968f98d094e76b67.a5.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/ab6bf49d16c443279941e9817262bab2/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=HyfjC41W6jkRcsitx08Xsud4d5WNfASF3SgTHQ4qhu0"

'Optional direct SharePoint list links for the Open List buttons.
Private Const ITIM_URL_ASSIGNMENTS_LIST As String = ""
Private Const ITIM_URL_BAYS_LIST As String = ""

Public Sub ITIM_ShowSearchForm(Optional ByVal seedText As String = vbNullString)
    Unload frmSearch
    frmSearch.Configure "SEARCH", seedText, ITIM_SelectedBayText(), ITIM_DefaultDeliveryListKey()
    frmSearch.Show vbModeless
End Sub

Public Sub ITIM_ShowManageBayForm(Optional ByVal actionText As String = vbNullString)
    Unload frmSearch
    frmSearch.Configure "BAY", actionText, ITIM_SelectedBayText(), ITIM_DefaultDeliveryListKey()
    frmSearch.Show vbModeless
End Sub

Public Sub ITIM_ShowManualEntryForm()
    Unload frmSearch
    frmSearch.Configure "MANUAL", vbNullString, ITIM_SelectedBayText(), ITIM_DefaultDeliveryListKey()
    frmSearch.Show vbModeless
End Sub

Public Sub ITIM_ShowSdiForm(Optional ByVal actionText As String = vbNullString)
    Unload frmSearch
    frmSearch.Configure "SDI", actionText, ITIM_SelectedBayText(), ITIM_DefaultDeliveryListKey()
    frmSearch.Show vbModeless
End Sub

Public Sub ITIM_FormSubmit(ByVal modeText As String, _
                           ByVal actionText As String, _
                           ByVal searchText As String, _
                           ByVal deliveryListKey As String, _
                           ByVal orderText As String, _
                           ByVal bayText As String, _
                           ByVal newBayText As String, _
                           ByVal glassCategory As String, _
                           ByVal glassHeader As String, _
                           ByVal notesText As String)
    Select Case UCase$(Trim$(modeText))
        Case "SEARCH"
            If Not ITIM_DataSearch(searchText) Then
                ITIM_DataSetStatus "Nothing found for: " & searchText, "WARN"
                MsgBox "No matching order or bay was found.", vbExclamation, "Search"
            End If

        Case "BAY"
            ITIM_DataApplyBayAction actionText, deliveryListKey, orderText, bayText, newBayText, glassCategory, glassHeader, notesText

        Case "MANUAL"
            ITIM_DataApplyBayAction "Manual Assign", deliveryListKey, orderText, bayText, vbNullString, glassCategory, glassHeader, notesText

        Case "SDI"
            If ITIM_IsPrintSdiAction(actionText) Then
                ITIM_PrintSdiList True
            Else
                ITIM_DataApplyBayAction actionText, deliveryListKey, orderText, bayText, vbNullString, "SDI", glassHeader, notesText
            End If
    End Select
End Sub

Public Sub ITIM_DataRefreshAndSync()
    Dim rowsLoaded As Long

    On Error GoTo ErrHandler

    Application.ScreenUpdating = False
    ITIM_DataSetStatus "Refreshing Indian Trail bay data...", "INFO"

    rowsLoaded = rowsLoaded + ITIM_LoadCsvToSheet(ITIM_BAYS_CSV, ITIM_BAYS_SHEET)
    rowsLoaded = rowsLoaded + ITIM_LoadCsvToSheet(ITIM_ASSIGNMENTS_CSV, ITIM_ASSIGNMENTS_SHEET)
    rowsLoaded = rowsLoaded + ITIM_LoadCsvToSheet(ITIM_SPECIAL_CSV, ITIM_SPECIAL_SHEET)

    ITIM_DataSyncMapStatus

    Application.ScreenUpdating = True
    ITIM_DataSetStatus "Refresh complete. " & rowsLoaded & " row(s) loaded.", "INFO"
    Exit Sub

ErrHandler:
    Application.ScreenUpdating = True
    ITIM_DataSetStatus "Refresh failed: " & Err.Description, "ERROR"
    MsgBox "Indian Trail refresh failed." & vbCrLf & vbCrLf & Err.Description, vbExclamation, "Refresh"
End Sub

Public Sub ITIM_PrintSdiList(Optional ByVal showPreview As Boolean = True)
    Dim printWs As Worksheet
    Dim assignmentWs As Worksheet
    Dim specialWs As Worksheet
    Dim seen As Object
    Dim outRow As Long
    Dim lastRow As Long
    Dim r As Long
    Dim orderText As String
    Dim assignmentRow As Long
    Dim activeCount As Long

    On Error GoTo ErrHandler

    Set printWs = ITIM_EnsureDataSheet(ITIM_SDI_PRINT_SHEET)
    Set assignmentWs = ITIM_GetWorksheet(ITIM_ASSIGNMENTS_SHEET)
    Set specialWs = ITIM_GetWorksheet(ITIM_SPECIAL_SHEET)
    Set seen = CreateObject("Scripting.Dictionary")

    printWs.Visible = xlSheetVisible
    printWs.Cells.Clear
    ITIM_PrepareSdiPrintSheet printWs
    outRow = 5

    If Not assignmentWs Is Nothing Then
        lastRow = assignmentWs.Cells(assignmentWs.Rows.Count, 1).End(xlUp).Row
        For r = 2 To lastRow
            If StrComp(ITIM_CellByHeader(assignmentWs, r, "AssignmentStatus"), "SDIOverride", vbTextCompare) = 0 Then
                orderText = ITIM_CellByHeader(assignmentWs, r, "OrderNumber")
                ITIM_AddSdiPrintRow printWs, seen, outRow, orderText, _
                    ITIM_CellByHeader(assignmentWs, r, "BayDisplayName"), _
                    ITIM_CellByHeader(assignmentWs, r, "AssignmentStatus"), _
                    ITIM_CellByHeader(assignmentWs, r, "GlassHeader"), _
                    ITIM_CellByHeader(assignmentWs, r, "Notes")
            End If
        Next r
    End If

    If Not specialWs Is Nothing Then
        lastRow = specialWs.Cells(specialWs.Rows.Count, 1).End(xlUp).Row
        For r = 2 To lastRow
            If StrComp(ITIM_CellByHeader(specialWs, r, "SpecialType"), "SDI", vbTextCompare) = 0 And _
               StrComp(ITIM_CellByHeader(specialWs, r, "SpecialStatus"), "Active", vbTextCompare) = 0 Then
                orderText = ITIM_CellByHeader(specialWs, r, "OrderNumber")
                assignmentRow = 0
                If Not assignmentWs Is Nothing Then assignmentRow = ITIM_FindAssignmentRow(assignmentWs, orderText, vbNullString)

                If assignmentRow > 0 Then
                    ITIM_AddSdiPrintRow printWs, seen, outRow, orderText, _
                        ITIM_CellByHeader(assignmentWs, assignmentRow, "BayDisplayName"), _
                        ITIM_CellByHeader(assignmentWs, assignmentRow, "AssignmentStatus"), _
                        ITIM_CellByHeader(assignmentWs, assignmentRow, "GlassHeader"), _
                        ITIM_CellByHeader(assignmentWs, assignmentRow, "Notes")
                Else
                    ITIM_AddSdiPrintRow printWs, seen, outRow, orderText, vbNullString, _
                        "SDIOverride", vbNullString, ITIM_CellByHeader(specialWs, r, "Notes")
                End If
            End If
        Next r
    End If

    activeCount = outRow - 5
    If activeCount = 0 Then
        printWs.Range("A5:F5").Merge
        printWs.Range("A5").Value = "No active SDI orders were found."
        printWs.Range("A5").Font.Italic = True
        printWs.Range("A5").Font.Color = RGB(90, 100, 115)
        outRow = 6
    End If

    ITIM_FormatSdiPrintSheet printWs, outRow
    printWs.Activate
    ITIM_DataSetStatus "SDI print sheet prepared. " & activeCount & " active order(s).", "INFO"

    If showPreview Then printWs.PrintPreview
    Exit Sub

ErrHandler:
    ITIM_DataSetStatus "SDI print failed: " & Err.Description, "ERROR"
    MsgBox "Could not prepare the SDI print sheet." & vbCrLf & vbCrLf & Err.Description, vbExclamation, "Print SDI List"
End Sub

Public Sub ITIM_DataSyncMapStatus()
    Dim mapWs As Worksheet
    Dim assignmentWs As Worksheet
    Dim lastRow As Long
    Dim r As Long
    Dim bayDisplay As String
    Dim orderText As String
    Dim statusText As String
    Dim categoryText As String
    Dim bayCell As Range
    Dim paintedCount As Long
    Dim preAssignedCount As Long
    Dim occupiedCount As Long
    Dim exceptionCount As Long
    Dim sdiCount As Long
    Dim notOnMapCount As Long

    On Error GoTo ErrHandler

    Set mapWs = ITIM_GetWorksheet(ITIM_MAP_SHEET)
    Set assignmentWs = ITIM_GetWorksheet(ITIM_ASSIGNMENTS_SHEET)

    If assignmentWs Is Nothing Then
        ITIM_LoadCsvToSheet ITIM_ASSIGNMENTS_CSV, ITIM_ASSIGNMENTS_SHEET
        Set assignmentWs = ITIM_GetWorksheet(ITIM_ASSIGNMENTS_SHEET)
    End If

    If mapWs Is Nothing Or assignmentWs Is Nothing Then Exit Sub

    mapWs.Unprotect Password:=""
    ITIM_ClearMapAssignments mapWs

    lastRow = assignmentWs.Cells(assignmentWs.Rows.Count, 1).End(xlUp).Row

    For r = 2 To lastRow
        statusText = ITIM_CellByHeader(assignmentWs, r, "AssignmentStatus")

        If ITIM_IsActiveAssignmentStatus(statusText) Then
            Select Case UCase$(Trim$(statusText))
                Case "OCCUPIED"
                    occupiedCount = occupiedCount + 1
                Case "MANUALEXCEPTION"
                    exceptionCount = exceptionCount + 1
                Case "SDIOVERRIDE"
                    sdiCount = sdiCount + 1
                Case Else
                    preAssignedCount = preAssignedCount + 1
            End Select

            bayDisplay = ITIM_CellByHeader(assignmentWs, r, "BayDisplayName")

            If Len(bayDisplay) > 0 Then
                Set bayCell = ITIM_FindMapCell(mapWs, bayDisplay)

                If Not bayCell Is Nothing Then
                    orderText = ITIM_CellByHeader(assignmentWs, r, "OrderNumber")
                    categoryText = ITIM_CellByHeader(assignmentWs, r, "GlassCategory")
                    ITIM_PaintMapAssignment bayCell, orderText, statusText, categoryText
                    paintedCount = paintedCount + 1
                Else
                    notOnMapCount = notOnMapCount + 1
                End If
            Else
                notOnMapCount = notOnMapCount + 1
            End If
        End If
    Next r

    ITIM_UpdateLiveSummary mapWs, occupiedCount, preAssignedCount, sdiCount, exceptionCount, notOnMapCount, paintedCount

    mapWs.Protect Password:="", DrawingObjects:=False, Contents:=True, Scenarios:=True, UserInterfaceOnly:=True
    ITIM_DataSetStatus "Bay map synced. " & paintedCount & " active bay(s) shown.", "INFO"
    Exit Sub

ErrHandler:
    On Error Resume Next
    If Not mapWs Is Nothing Then mapWs.Protect Password:="", DrawingObjects:=False, Contents:=True, Scenarios:=True, UserInterfaceOnly:=True
    On Error GoTo 0

    ITIM_DataSetStatus "Map sync failed: " & Err.Description, "ERROR"
End Sub

Public Function ITIM_DataSearch(ByVal searchText As String) As Boolean
    Dim mapWs As Worksheet
    Dim assignmentWs As Worksheet
    Dim foundCell As Range
    Dim r As Long
    Dim lastRow As Long
    Dim targetBay As String
    Dim s As String

    s = Trim$(searchText)
    If Len(s) = 0 Then Exit Function

    Set mapWs = ITIM_GetWorksheet(ITIM_MAP_SHEET)
    If mapWs Is Nothing Then Exit Function

    Set foundCell = ITIM_FindMapCell(mapWs, s)
    If Not foundCell Is Nothing Then
        ITIM_HighlightMapCell foundCell, s
        ITIM_DataSearch = True
        Exit Function
    End If

    Set assignmentWs = ITIM_GetWorksheet(ITIM_ASSIGNMENTS_SHEET)
    If assignmentWs Is Nothing Then
        On Error Resume Next
        ITIM_LoadCsvToSheet ITIM_ASSIGNMENTS_CSV, ITIM_ASSIGNMENTS_SHEET
        Set assignmentWs = ITIM_GetWorksheet(ITIM_ASSIGNMENTS_SHEET)
        On Error GoTo 0
    End If

    If assignmentWs Is Nothing Then Exit Function

    lastRow = assignmentWs.Cells(assignmentWs.Rows.Count, 1).End(xlUp).Row

    For r = 2 To lastRow
        If InStr(1, ITIM_CellByHeader(assignmentWs, r, "OrderNumber"), s, vbTextCompare) > 0 Or _
           InStr(1, ITIM_CellByHeader(assignmentWs, r, "NormalizedOrderNumber"), s, vbTextCompare) > 0 Or _
           InStr(1, ITIM_CellByHeader(assignmentWs, r, "BayDisplayName"), s, vbTextCompare) > 0 Or _
           InStr(1, ITIM_CellByHeader(assignmentWs, r, "GlassHeader"), s, vbTextCompare) > 0 Then

            targetBay = ITIM_CellByHeader(assignmentWs, r, "BayDisplayName")
            If Len(targetBay) > 0 Then
                Set foundCell = ITIM_FindMapCell(mapWs, targetBay)
                If Not foundCell Is Nothing Then
                    ITIM_HighlightMapCell foundCell, ITIM_CellByHeader(assignmentWs, r, "OrderNumber") & " -> " & targetBay
                    ITIM_DataSearch = True
                    Exit Function
                End If
            End If
        End If
    Next r
End Function

Public Sub ITIM_DataApplyBayAction(ByVal actionText As String, _
                                   ByVal deliveryListKey As String, _
                                   ByVal orderText As String, _
                                   ByVal bayText As String, _
                                   ByVal newBayText As String, _
                                   ByVal glassCategory As String, _
                                   ByVal glassHeader As String, _
                                   ByVal notesText As String)
    Dim actionKey As String
    Dim assignmentWs As Worksheet
    Dim responseText As String
    Dim flowOk As Boolean
    Dim changedMessage As String
    Dim actionToPost As String

    On Error GoTo ErrHandler

    Set assignmentWs = ITIM_EnsureDataSheet(ITIM_ASSIGNMENTS_SHEET)
    If assignmentWs.Cells(1, 1).Value = vbNullString Then ITIM_EnsureAssignmentHeaders assignmentWs
    ITIM_EnsureAssignmentRuntimeHeaders assignmentWs

    actionKey = UCase$(Trim$(actionText))
    actionToPost = ITIM_AdminFlowActionText(actionText)

    Select Case True
        Case actionKey = "SCAN OUT" Or actionKey = "SCAN OUT OF BAY" Or actionKey = "SCANOUT"
            changedMessage = ITIM_LocalClearBay(assignmentWs, orderText, bayText, notesText)
            changedMessage = "Order scanned out of bay locally."

        Case actionKey = "CLEAR" Or actionKey = "CLEAR BAY"
            changedMessage = ITIM_LocalClearBay(assignmentWs, orderText, bayText, notesText)

        Case actionKey = "MOVE" Or actionKey = "MOVE ORDER"
            changedMessage = ITIM_LocalMoveOrder(assignmentWs, deliveryListKey, orderText, newBayText, notesText)

        Case actionKey = "EXCEPTION" Or actionKey = "MANUAL EXCEPTION"
            changedMessage = ITIM_LocalSetAssignmentStatus(assignmentWs, deliveryListKey, orderText, bayText, "ManualException", glassCategory, glassHeader, notesText)

        Case actionKey = "MARK" Or actionKey = "MARK SDI" Or actionKey = "SDI"
            changedMessage = ITIM_LocalMarkSdi(deliveryListKey, orderText, notesText)

        Case actionKey = "REMOVE" Or actionKey = "REMOVE SDI"
            changedMessage = ITIM_LocalRemoveSdi(deliveryListKey, orderText, notesText)

        Case Else
            changedMessage = ITIM_LocalSetAssignmentStatus(assignmentWs, deliveryListKey, orderText, bayText, "PreAssigned", glassCategory, glassHeader, notesText)
    End Select

    flowOk = ITIM_PostAdminAction(actionToPost, deliveryListKey, orderText, bayText, newBayText, glassCategory, glassHeader, notesText, responseText)

    ITIM_DataSyncMapStatus

    If flowOk Then
        ITIM_DataSetStatus changedMessage & " SharePoint updated.", "INFO"
    Else
        ITIM_DataSetStatus changedMessage & " " & responseText, "WARN"
    End If

    MsgBox changedMessage & vbCrLf & vbCrLf & responseText, vbInformation, "Indian Trail Bay Action"
    Exit Sub

ErrHandler:
    ITIM_DataSetStatus "Bay action failed: " & Err.Description, "ERROR"
    MsgBox "Bay action failed." & vbCrLf & vbCrLf & Err.Description, vbExclamation, "Indian Trail Bay Action"
End Sub

Public Function ITIM_SelectedBayText() As String
    Dim ws As Worksheet

    On Error Resume Next
    Set ws = ActiveSheet
    On Error GoTo 0

    If ws Is Nothing Then Exit Function
    If StrComp(ws.Name, ITIM_MAP_SHEET, vbTextCompare) <> 0 Then Exit Function
    ITIM_SelectedBayText = ITIM_MapBayTextForTarget(ActiveCell)
End Function

Public Function ITIM_HandleMapDoubleClick(ByVal targetCell As Range) As Boolean
    Dim bayText As String
    Dim bayCell As Range

    On Error GoTo SafeExit

    If targetCell Is Nothing Then Exit Function
    If StrComp(targetCell.Worksheet.Name, ITIM_MAP_SHEET, vbTextCompare) <> 0 Then Exit Function
    If Intersect(targetCell, targetCell.Worksheet.Range("A8:AD360")) Is Nothing Then Exit Function

    bayText = ITIM_MapBayTextForTarget(targetCell)
    If Len(bayText) = 0 Then Exit Function

    ITIM_HandleMapDoubleClick = True

    Set bayCell = ITIM_FindMapCell(targetCell.Worksheet, bayText)
    If Not bayCell Is Nothing Then ITIM_HighlightMapCell bayCell, "bay " & bayText

    Unload frmSearch
    frmSearch.Configure "BAY", vbNullString, bayText, ITIM_DefaultDeliveryListKey()
    frmSearch.Show vbModeless

SafeExit:
End Function

Public Function ITIM_DefaultDeliveryListKey() As String
    Dim ws As Worksheet
    Dim c As Long

    Set ws = ITIM_GetWorksheet(ITIM_ASSIGNMENTS_SHEET)
    If ws Is Nothing Then Exit Function

    c = ITIM_HeaderCol(ws, "DeliveryListKey")
    If c > 0 Then ITIM_DefaultDeliveryListKey = Trim$(CStr(ws.Cells(2, c).Value))
End Function

Public Sub ITIM_DataOpenAssignmentsList()
    ITIM_OpenUrlOrLocalCsv ITIM_URL_ASSIGNMENTS_LIST, ITIM_ASSIGNMENTS_CSV
End Sub

Public Sub ITIM_DataOpenBaysList()
    ITIM_OpenUrlOrLocalCsv ITIM_URL_BAYS_LIST, ITIM_BAYS_CSV
End Sub

Public Sub ITIM_DataSetStatus(ByVal statusText As String, Optional ByVal statusKind As String = "INFO")
    Dim mapWs As Worksheet
    Dim fillColor As Long
    Dim fontColor As Long

    Select Case UCase$(statusKind)
        Case "WARN"
            fillColor = RGB(255, 242, 204)
            fontColor = RGB(156, 101, 0)
        Case "ERROR"
            fillColor = RGB(255, 199, 206)
            fontColor = RGB(156, 0, 6)
        Case Else
            fillColor = RGB(198, 239, 206)
            fontColor = RGB(0, 97, 0)
    End Select

    On Error Resume Next

    Set mapWs = ITIM_GetWorksheet(ITIM_MAP_SHEET)
    If Not mapWs Is Nothing Then
        mapWs.Unprotect Password:=""
        mapWs.Range("U5:X7").UnMerge
        mapWs.Range("U5:X7").ClearContents
        mapWs.Range("U5:X6").Interior.Color = RGB(183, 199, 218)
        mapWs.Range("U7:X7").Interior.Color = RGB(226, 235, 245)
        mapWs.Range(ITIM_MAP_STATUS_RANGE).UnMerge
        With mapWs.Range(ITIM_MAP_STATUS_RANGE)
            .Merge
            .Value = statusText
            .Interior.Color = fillColor
            .Font.Color = fontColor
            .Font.Bold = True
            .Font.Size = 9
            .HorizontalAlignment = xlCenter
            .VerticalAlignment = xlCenter
            .WrapText = True
            .Borders.LineStyle = xlContinuous
            .Borders.Color = RGB(197, 210, 226)
        End With
        mapWs.Protect Password:="", DrawingObjects:=False, Contents:=True, Scenarios:=True, UserInterfaceOnly:=True
    End If

    On Error GoTo 0
End Sub

Private Function ITIM_IsPrintSdiAction(ByVal actionText As String) As Boolean
    Dim actionKey As String

    actionKey = UCase$(Trim$(actionText))
    ITIM_IsPrintSdiAction = (actionKey = "PRINT SDI LIST" Or actionKey = "PRINT SDI" Or actionKey = "PRINT")
End Function

Private Sub ITIM_PrepareSdiPrintSheet(ByVal ws As Worksheet)
    With ws
        .Range("A1:F1").Merge
        .Range("A1").Value = "Indian Trail Same Day Install Orders"
        .Range("A1").Interior.Color = RGB(47, 75, 117)
        .Range("A1").Font.Color = RGB(255, 255, 255)
        .Range("A1").Font.Bold = True
        .Range("A1").Font.Size = 18
        .Range("A1").HorizontalAlignment = xlCenter

        .Range("A2:F2").Merge
        .Range("A2").Value = "Active SDI list prepared " & Format$(Now, "m/d/yyyy h:nn AM/PM")
        .Range("A2").Interior.Color = RGB(221, 230, 242)
        .Range("A2").Font.Color = RGB(47, 75, 117)
        .Range("A2").Font.Bold = True
        .Range("A2").HorizontalAlignment = xlCenter

        .Range("A4:F4").Value = Array("Order", "Bay", "Status", "Glass Header", "Notes", "Source")
        With .Range("A4:F4")
            .Interior.Color = RGB(31, 78, 121)
            .Font.Color = RGB(255, 255, 255)
            .Font.Bold = True
            .HorizontalAlignment = xlCenter
        End With
    End With
End Sub

Private Sub ITIM_AddSdiPrintRow(ByVal ws As Worksheet, _
                                ByVal seen As Object, _
                                ByRef outRow As Long, _
                                ByVal orderText As String, _
                                ByVal bayText As String, _
                                ByVal statusText As String, _
                                ByVal glassHeader As String, _
                                ByVal notesText As String)
    Dim keyText As String

    keyText = UCase$(Trim$(orderText))
    If Len(keyText) = 0 Then Exit Sub
    If seen.Exists(keyText) Then Exit Sub

    seen.Add keyText, True

    ws.Cells(outRow, 1).Value = orderText
    ws.Cells(outRow, 2).Value = IIf(Len(Trim$(bayText)) > 0, bayText, "No bay")
    ws.Cells(outRow, 3).Value = statusText
    ws.Cells(outRow, 4).Value = glassHeader
    ws.Cells(outRow, 5).Value = notesText
    ws.Cells(outRow, 6).Value = IIf(Len(Trim$(bayText)) > 0, "Assignment", "Special order")
    outRow = outRow + 1
End Sub

Private Sub ITIM_FormatSdiPrintSheet(ByVal ws As Worksheet, ByVal finalRow As Long)
    Dim lastDataRow As Long

    lastDataRow = finalRow - 1
    If lastDataRow < 4 Then lastDataRow = 4

    With ws.Range("A4:F" & lastDataRow)
        .Borders.LineStyle = xlContinuous
        .Borders.Color = RGB(197, 210, 226)
        .VerticalAlignment = xlCenter
    End With

    ws.Columns("A").ColumnWidth = 18
    ws.Columns("B").ColumnWidth = 16
    ws.Columns("C").ColumnWidth = 18
    ws.Columns("D").ColumnWidth = 26
    ws.Columns("E").ColumnWidth = 46
    ws.Columns("F").ColumnWidth = 18
    ws.Columns("E").WrapText = True
    ws.Rows("1:2").RowHeight = 24
    ws.Rows("4:" & lastDataRow).RowHeight = 22
    ws.Range("A5:F" & lastDataRow).Font.Size = 11

    With ws.PageSetup
        .Orientation = xlLandscape
        .Zoom = False
        .FitToPagesWide = 1
        .FitToPagesTall = False
        .PrintTitleRows = "$4:$4"
        .LeftMargin = Application.InchesToPoints(0.35)
        .RightMargin = Application.InchesToPoints(0.35)
        .TopMargin = Application.InchesToPoints(0.45)
        .BottomMargin = Application.InchesToPoints(0.45)
    End With
End Sub

Private Function ITIM_LoadCsvToSheet(ByVal csvFileName As String, ByVal targetSheetName As String) As Long
    Dim csvPath As String
    Dim ws As Worksheet
    Dim lastRow As Long

    csvPath = ITIM_ProjectRoot() & Application.PathSeparator & "Sharepoint Lists" & Application.PathSeparator & csvFileName
    If Len(Dir$(csvPath, vbNormal)) = 0 Then Err.Raise vbObjectError + 7301, , "CSV not found: " & csvPath

    Set ws = ITIM_EnsureDataSheet(targetSheetName)
    ws.Visible = xlSheetVisible
    ws.Cells.Clear

    With ws.QueryTables.Add(Connection:="TEXT;" & csvPath, Destination:=ws.Range("A1"))
        .TextFileParseType = xlDelimited
        .TextFileCommaDelimiter = True
        .TextFileTextQualifier = xlTextQualifierDoubleQuote
        .Refresh BackgroundQuery:=False
        .Delete
    End With

    If Left$(Trim$(CStr(ws.Range("A1").Value)), 11) = "ListSchema=" Then
        ws.Rows(1).Delete
    End If

    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row
    If lastRow > 1 Then ITIM_LoadCsvToSheet = lastRow - 1

    ws.Visible = xlSheetHidden
End Function

Private Function ITIM_ProjectRoot() As String
    Dim p As String
    Dim i As Long
    Dim slashPos As Long

    p = ThisWorkbook.Path

    For i = 1 To 8
        If Len(Dir$(p & Application.PathSeparator & "Sharepoint Lists", vbDirectory)) > 0 Then
            ITIM_ProjectRoot = p
            Exit Function
        End If

        slashPos = InStrRev(p, Application.PathSeparator)
        If slashPos <= 3 Then Exit For
        p = Left$(p, slashPos - 1)
    Next i

    ITIM_ProjectRoot = ThisWorkbook.Path
End Function

Private Function ITIM_GetWorksheet(ByVal sheetName As String) As Worksheet
    On Error Resume Next
    Set ITIM_GetWorksheet = ThisWorkbook.Worksheets(sheetName)
    On Error GoTo 0
End Function

Private Function ITIM_EnsureDataSheet(ByVal sheetName As String) As Worksheet
    Set ITIM_EnsureDataSheet = ITIM_GetWorksheet(sheetName)

    If ITIM_EnsureDataSheet Is Nothing Then
        Set ITIM_EnsureDataSheet = ThisWorkbook.Worksheets.Add(After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
        ITIM_EnsureDataSheet.Name = sheetName
    End If
End Function

Private Function ITIM_HeaderCol(ByVal ws As Worksheet, ByVal headerText As String) As Long
    Dim lastCol As Long
    Dim c As Long

    If ws Is Nothing Then Exit Function

    lastCol = ws.Cells(1, ws.Columns.Count).End(xlToLeft).Column

    For c = 1 To lastCol
        If StrComp(Trim$(CStr(ws.Cells(1, c).Value)), headerText, vbTextCompare) = 0 Then
            ITIM_HeaderCol = c
            Exit Function
        End If
    Next c
End Function

Private Function ITIM_CellByHeader(ByVal ws As Worksheet, ByVal rowNum As Long, ByVal headerText As String) As String
    Dim c As Long

    c = ITIM_HeaderCol(ws, headerText)
    If c > 0 Then ITIM_CellByHeader = Trim$(CStr(ws.Cells(rowNum, c).Value))
End Function

Private Sub ITIM_SetCellByHeader(ByVal ws As Worksheet, ByVal rowNum As Long, ByVal headerText As String, ByVal valueText As Variant)
    Dim c As Long

    c = ITIM_HeaderCol(ws, headerText)
    If c > 0 Then ws.Cells(rowNum, c).Value = valueText
End Sub

Private Sub ITIM_EnsureAssignmentHeaders(ByVal ws As Worksheet)
    Dim headers As Variant
    Dim i As Long

    headers = Array("OrderNumber", "NormalizedOrderNumber", "DeliveryListKey", "AssignmentGroupId", "BayKey", _
                    "BayDisplayName", "GlassCategory", "GlassHeader", "AssignmentStatus", "PreAssignedAt", _
                    "OccupiedAt", "ClearedAt", "ManualOverride", "LastScanStation", "Notes", _
                    "SdiPreviousStatus", "SdiPreviousBayKey", "SdiPreviousBayDisplayName", _
                    "SdiPreviousGlassCategory", "SdiPreviousGlassHeader")

    For i = LBound(headers) To UBound(headers)
        ws.Cells(1, i + 1).Value = headers(i)
    Next i
End Sub

Private Sub ITIM_EnsureAssignmentRuntimeHeaders(ByVal ws As Worksheet)
    ITIM_EnsureHeader ws, "SdiPreviousStatus"
    ITIM_EnsureHeader ws, "SdiPreviousBayKey"
    ITIM_EnsureHeader ws, "SdiPreviousBayDisplayName"
    ITIM_EnsureHeader ws, "SdiPreviousGlassCategory"
    ITIM_EnsureHeader ws, "SdiPreviousGlassHeader"
End Sub

Private Sub ITIM_EnsureHeader(ByVal ws As Worksheet, ByVal headerText As String)
    Dim nextCol As Long

    If ws Is Nothing Then Exit Sub
    If ITIM_HeaderCol(ws, headerText) > 0 Then Exit Sub

    nextCol = ws.Cells(1, ws.Columns.Count).End(xlToLeft).Column + 1
    If nextCol < 1 Then nextCol = 1
    ws.Cells(1, nextCol).Value = headerText
End Sub

Private Function ITIM_IsActiveAssignmentStatus(ByVal statusText As String) As Boolean
    Select Case UCase$(Trim$(statusText))
        Case "PREASSIGNED", "OCCUPIED", "MANUALEXCEPTION", "SDIOVERRIDE"
            ITIM_IsActiveAssignmentStatus = True
    End Select
End Function

Private Function ITIM_FindMapCell(ByVal mapWs As Worksheet, ByVal searchText As String) As Range
    Dim targetText As String

    targetText = Trim$(searchText)
    If Len(targetText) = 0 Then Exit Function

    On Error Resume Next
    Set ITIM_FindMapCell = mapWs.Range("A1:AD360").Find(What:=targetText, LookIn:=xlValues, LookAt:=xlWhole, MatchCase:=False)
    If ITIM_FindMapCell Is Nothing Then
        Set ITIM_FindMapCell = mapWs.Range("A1:AD360").Find(What:=targetText, LookIn:=xlValues, LookAt:=xlPart, MatchCase:=False)
    End If
    On Error GoTo 0
End Function

Private Function ITIM_LooksLikeBayLabel(ByVal valueText As String) As Boolean
    Dim s As String

    s = UCase$(Trim$(valueText))
    If Len(s) = 0 Then Exit Function

    ITIM_LooksLikeBayLabel = _
        (InStr(1, s, "--", vbTextCompare) > 0 Or _
         Left$(s, 4) = "MIR ")
End Function

Private Function ITIM_MapBayTextForTarget(ByVal targetCell As Range) As String
    Dim valueText As String

    If targetCell Is Nothing Then Exit Function
    If targetCell.Cells.CountLarge > 1 Then Set targetCell = targetCell.Cells(1, 1)

    valueText = Trim$(CStr(targetCell.Value))
    If ITIM_LooksLikeBayLabel(valueText) Then
        ITIM_MapBayTextForTarget = valueText
        Exit Function
    End If

    If targetCell.Column < targetCell.Worksheet.Columns.Count Then
        valueText = Trim$(CStr(targetCell.Offset(0, 1).Value))
        If ITIM_LooksLikeBayLabel(valueText) Then
            ITIM_MapBayTextForTarget = valueText
            Exit Function
        End If
    End If

    If targetCell.Column > 1 Then
        valueText = Trim$(CStr(targetCell.Offset(0, -1).Value))
        If ITIM_LooksLikeBayLabel(valueText) Then ITIM_MapBayTextForTarget = valueText
    End If
End Function

Private Sub ITIM_ClearMapAssignments(ByVal mapWs As Worksheet)
    Dim cell As Range

    For Each cell In mapWs.Range("A8:AD360").Cells
        If cell.Column > 1 Then
            If ITIM_LooksLikeBayLabel(CStr(cell.Value)) Then
                cell.Offset(0, -1).ClearContents
                cell.Offset(0, -1).Interior.Color = RGB(242, 246, 250)
                cell.Offset(0, -1).Font.Color = RGB(47, 75, 117)
                cell.Offset(0, -1).Font.Bold = False

                cell.Interior.Color = RGB(255, 255, 255)
                cell.Font.Bold = True
            End If
        End If
    Next cell
End Sub

Private Sub ITIM_UpdateLiveSummary(ByVal mapWs As Worksheet, _
                                   ByVal occupiedCount As Long, _
                                   ByVal preAssignedCount As Long, _
                                   ByVal sdiCount As Long, _
                                   ByVal exceptionCount As Long, _
                                   ByVal notOnMapCount As Long, _
                                   ByVal paintedCount As Long)
    If mapWs Is Nothing Then Exit Sub

    With mapWs.Range("R12")
        .Value = occupiedCount
        .Interior.Color = ITIM_StatusFillColor("Occupied")
        .Font.Color = ITIM_StatusFontColor("Occupied")
    End With

    With mapWs.Range("R13")
        .Value = preAssignedCount
        .Interior.Color = ITIM_StatusFillColor("PreAssigned")
        .Font.Color = ITIM_StatusFontColor("PreAssigned")
    End With

    With mapWs.Range("R14")
        .Value = sdiCount
        .Interior.Color = ITIM_StatusFillColor("SDIOverride")
        .Font.Color = ITIM_StatusFontColor("SDIOverride")
    End With

    With mapWs.Range("R15")
        .Value = exceptionCount
        .Interior.Color = ITIM_StatusFillColor("ManualException")
        .Font.Color = ITIM_StatusFontColor("ManualException")
    End With

    With mapWs.Range("R16")
        .Value = notOnMapCount
        .Interior.Color = IIf(notOnMapCount > 0, RGB(255, 199, 206), RGB(226, 239, 218))
        .Font.Color = IIf(notOnMapCount > 0, RGB(156, 0, 6), RGB(0, 97, 0))
    End With

    With mapWs.Range("R17")
        .Value = paintedCount
        .Interior.Color = RGB(221, 230, 242)
        .Font.Color = RGB(47, 75, 117)
    End With

    With mapWs.Range("R12:R17")
        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
        .Font.Bold = True
    End With

    On Error Resume Next
    mapWs.Range("Q18:U18").UnMerge
    On Error GoTo 0

    With mapWs.Range("Q18:U18")
        .Merge
        .Value = "Last refresh: " & Format$(Now, "m/d/yyyy h:nn AM/PM")
        .Interior.Color = RGB(221, 230, 242)
        .Font.Color = RGB(47, 75, 117)
        .Font.Bold = True
        .Font.Size = 9
        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
        .WrapText = True
        .Borders.LineStyle = xlContinuous
        .Borders.Color = RGB(197, 210, 226)
    End With
End Sub

Private Sub ITIM_PaintMapAssignment(ByVal bayCell As Range, ByVal orderText As String, ByVal statusText As String, ByVal categoryText As String)
    Dim noteCell As Range
    Dim fillColor As Long
    Dim labelColor As Long
    Dim noteText As String

    If bayCell Is Nothing Then Exit Sub
    If bayCell.Column <= 1 Then Exit Sub

    fillColor = ITIM_StatusFillColor(statusText)
    labelColor = ITIM_StatusFontColor(statusText)

    Set noteCell = bayCell.Offset(0, -1)

    If Len(Trim$(CStr(noteCell.Value))) > 0 Then
        noteText = CStr(noteCell.Value) & vbLf & ITIM_MapAssignmentText(orderText, statusText, categoryText)
    Else
        noteText = ITIM_MapAssignmentText(orderText, statusText, categoryText)
    End If

    With noteCell
        .Value = noteText
        .Interior.Color = fillColor
        .Font.Color = labelColor
        .Font.Bold = True
        .WrapText = True
        .ShrinkToFit = True
        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
    End With

    With bayCell
        .Interior.Color = fillColor
        .Font.Color = labelColor
        .Font.Bold = True
    End With
End Sub

Private Function ITIM_MapAssignmentText(ByVal orderText As String, ByVal statusText As String, ByVal categoryText As String) As String
    Dim s As String

    s = ITIM_StatusShortText(statusText) & ": " & orderText
    If Len(Trim$(categoryText)) > 0 Then s = s & " | " & ITIM_CategoryShortText(categoryText)

    ITIM_MapAssignmentText = s
End Function

Private Function ITIM_StatusShortText(ByVal statusText As String) As String
    Select Case UCase$(Trim$(statusText))
        Case "OCCUPIED"
            ITIM_StatusShortText = "OCC"
        Case "MANUALEXCEPTION"
            ITIM_StatusShortText = "EXC"
        Case "SDIOVERRIDE"
            ITIM_StatusShortText = "SDI"
        Case Else
            ITIM_StatusShortText = "PRE"
    End Select
End Function

Private Function ITIM_CategoryShortText(ByVal categoryText As String) As String
    Dim s As String

    s = Trim$(categoryText)

    Select Case UCase$(s)
        Case "MIRRORANNEALED"
            ITIM_CategoryShortText = "Mirror"
        Case "MANUALOVERSIZED"
            ITIM_CategoryShortText = "Oversize"
        Case "MANUALEXCEPTION"
            ITIM_CategoryShortText = "Manual"
        Case Else
            ITIM_CategoryShortText = s
    End Select
End Function

Private Function ITIM_StatusFillColor(ByVal statusText As String) As Long
    Select Case UCase$(Trim$(statusText))
        Case "OCCUPIED"
            ITIM_StatusFillColor = RGB(198, 239, 206)
        Case "MANUALEXCEPTION"
            ITIM_StatusFillColor = RGB(255, 199, 206)
        Case "SDIOVERRIDE"
            ITIM_StatusFillColor = RGB(218, 238, 243)
        Case Else
            ITIM_StatusFillColor = RGB(255, 242, 204)
    End Select
End Function

Private Function ITIM_StatusFontColor(ByVal statusText As String) As Long
    Select Case UCase$(Trim$(statusText))
        Case "OCCUPIED"
            ITIM_StatusFontColor = RGB(0, 97, 0)
        Case "MANUALEXCEPTION"
            ITIM_StatusFontColor = RGB(156, 0, 6)
        Case "SDIOVERRIDE"
            ITIM_StatusFontColor = RGB(0, 92, 112)
        Case Else
            ITIM_StatusFontColor = RGB(156, 101, 0)
    End Select
End Function

Private Sub ITIM_HighlightMapCell(ByVal foundCell As Range, ByVal statusText As String)
    Dim mapWs As Worksheet
    Dim box As Shape

    If foundCell Is Nothing Then Exit Sub
    Set mapWs = foundCell.Worksheet

    mapWs.Unprotect Password:=""

    On Error Resume Next
    mapWs.Shapes("itimMapHighlight").Delete
    On Error GoTo 0

    Set box = mapWs.Shapes.AddShape(msoShapeRoundedRectangle, foundCell.Left - 2, foundCell.Top - 2, foundCell.Width + 4, foundCell.Height + 4)

    With box
        .Name = "itimMapHighlight"
        .Fill.Visible = msoFalse
        .Line.Visible = msoTrue
        .Line.ForeColor.RGB = RGB(255, 192, 0)
        .Line.Weight = 3
        .Placement = xlMoveAndSize
        .ZOrder msoBringToFront
    End With

    mapWs.Activate
    foundCell.Select
    mapWs.Protect Password:="", DrawingObjects:=False, Contents:=True, Scenarios:=True, UserInterfaceOnly:=True
    ITIM_DataSetStatus "Found " & statusText & ".", "INFO"
End Sub

Private Function ITIM_LocalClearBay(ByVal ws As Worksheet, ByVal orderText As String, ByVal bayText As String, ByVal notesText As String) As String
    Dim rowNum As Long

    rowNum = ITIM_FindAssignmentRow(ws, orderText, bayText)
    If rowNum = 0 Then Err.Raise vbObjectError + 7310, , "No active assignment found for the selected order/bay."

    ITIM_SetCellByHeader ws, rowNum, "AssignmentStatus", "Cleared"
    ITIM_SetCellByHeader ws, rowNum, "ClearedAt", ITIM_NowStamp()
    ITIM_SetCellByHeader ws, rowNum, "ManualOverride", True
    ITIM_SetCellByHeader ws, rowNum, "Notes", ITIM_AppendNote(ITIM_CellByHeader(ws, rowNum, "Notes"), notesText)

    ITIM_LocalClearBay = "Bay cleared locally."
End Function

Private Function ITIM_LocalMoveOrder(ByVal ws As Worksheet, ByVal deliveryListKey As String, ByVal orderText As String, ByVal newBayText As String, ByVal notesText As String) As String
    Dim rowNum As Long

    If Len(Trim$(orderText)) = 0 Then Err.Raise vbObjectError + 7311, , "Order number is required."
    If Len(Trim$(newBayText)) = 0 Then Err.Raise vbObjectError + 7312, , "New bay is required."

    rowNum = ITIM_FindAssignmentRow(ws, orderText, vbNullString)
    If rowNum = 0 Then
        rowNum = ITIM_NewAssignmentRow(ws, deliveryListKey, orderText)
    End If

    ITIM_SetCellByHeader ws, rowNum, "BayKey", ITIM_BayKeyForDisplay(newBayText)
    ITIM_SetCellByHeader ws, rowNum, "BayDisplayName", newBayText
    ITIM_SetCellByHeader ws, rowNum, "ManualOverride", True
    ITIM_SetCellByHeader ws, rowNum, "Notes", ITIM_AppendNote(ITIM_CellByHeader(ws, rowNum, "Notes"), notesText)

    ITIM_LocalMoveOrder = "Order moved locally to bay " & newBayText & "."
End Function

Private Function ITIM_LocalSetAssignmentStatus(ByVal ws As Worksheet, _
                                               ByVal deliveryListKey As String, _
                                               ByVal orderText As String, _
                                               ByVal bayText As String, _
                                               ByVal statusText As String, _
                                               ByVal glassCategory As String, _
                                               ByVal glassHeader As String, _
                                               ByVal notesText As String) As String
    Dim rowNum As Long

    If Len(Trim$(orderText)) = 0 Then Err.Raise vbObjectError + 7313, , "Order number is required."
    If Len(Trim$(bayText)) = 0 And UCase$(statusText) <> "MANUALEXCEPTION" Then Err.Raise vbObjectError + 7314, , "Bay is required."

    rowNum = ITIM_FindAssignmentRow(ws, orderText, bayText)
    If rowNum = 0 Then rowNum = ITIM_NewAssignmentRow(ws, deliveryListKey, orderText)

    If Len(Trim$(bayText)) > 0 Then
        ITIM_SetCellByHeader ws, rowNum, "BayKey", ITIM_BayKeyForDisplay(bayText)
        ITIM_SetCellByHeader ws, rowNum, "BayDisplayName", bayText
    End If

    If Len(Trim$(glassCategory)) > 0 Then ITIM_SetCellByHeader ws, rowNum, "GlassCategory", glassCategory
    If Len(Trim$(glassHeader)) > 0 Then ITIM_SetCellByHeader ws, rowNum, "GlassHeader", glassHeader

    ITIM_SetCellByHeader ws, rowNum, "AssignmentStatus", statusText
    ITIM_SetCellByHeader ws, rowNum, "ManualOverride", True
    ITIM_SetCellByHeader ws, rowNum, "LastScanStation", Environ$("COMPUTERNAME")
    ITIM_SetCellByHeader ws, rowNum, "Notes", ITIM_AppendNote(ITIM_CellByHeader(ws, rowNum, "Notes"), notesText)

    If UCase$(statusText) = "PREASSIGNED" Then ITIM_SetCellByHeader ws, rowNum, "PreAssignedAt", ITIM_NowStamp()

    ITIM_LocalSetAssignmentStatus = "Assignment updated locally."
End Function

Private Function ITIM_LocalMarkSdi(ByVal deliveryListKey As String, ByVal orderText As String, ByVal notesText As String) As String
    Dim ws As Worksheet
    Dim rowNum As Long
    Dim wasNew As Boolean
    Dim previousStatus As String

    If Len(Trim$(orderText)) = 0 Then Err.Raise vbObjectError + 7315, , "Order number is required."

    Set ws = ITIM_EnsureDataSheet(ITIM_ASSIGNMENTS_SHEET)
    If ws.Cells(1, 1).Value = vbNullString Then ITIM_EnsureAssignmentHeaders ws
    ITIM_EnsureAssignmentRuntimeHeaders ws

    rowNum = ITIM_FindAssignmentRow(ws, orderText, vbNullString)
    If rowNum = 0 Then
        wasNew = True
        rowNum = ITIM_NewAssignmentRow(ws, deliveryListKey, orderText)
    End If

    previousStatus = ITIM_CellByHeader(ws, rowNum, "AssignmentStatus")
    If StrComp(previousStatus, "SDIOverride", vbTextCompare) <> 0 Then
        If wasNew Or Len(Trim$(previousStatus)) = 0 Then previousStatus = "NoAssignment"
        ITIM_SetCellByHeader ws, rowNum, "SdiPreviousStatus", previousStatus
        ITIM_SetCellByHeader ws, rowNum, "SdiPreviousBayKey", ITIM_CellByHeader(ws, rowNum, "BayKey")
        ITIM_SetCellByHeader ws, rowNum, "SdiPreviousBayDisplayName", ITIM_CellByHeader(ws, rowNum, "BayDisplayName")
        ITIM_SetCellByHeader ws, rowNum, "SdiPreviousGlassCategory", ITIM_CellByHeader(ws, rowNum, "GlassCategory")
        ITIM_SetCellByHeader ws, rowNum, "SdiPreviousGlassHeader", ITIM_CellByHeader(ws, rowNum, "GlassHeader")
    End If

    ITIM_SetCellByHeader ws, rowNum, "AssignmentStatus", "SDIOverride"
    ITIM_SetCellByHeader ws, rowNum, "GlassCategory", "SDI"
    ITIM_SetCellByHeader ws, rowNum, "ManualOverride", True
    ITIM_SetCellByHeader ws, rowNum, "Notes", ITIM_AppendNote(ITIM_CellByHeader(ws, rowNum, "Notes"), notesText)

    ITIM_UpsertSpecialOrder orderText, "SDI", "Active", notesText

    ITIM_LocalMarkSdi = "Order marked SDI locally."
End Function

Private Function ITIM_LocalRemoveSdi(ByVal deliveryListKey As String, ByVal orderText As String, ByVal notesText As String) As String
    Dim ws As Worksheet
    Dim rowNum As Long
    Dim bayText As String
    Dim previousStatus As String

    If Len(Trim$(orderText)) = 0 Then Err.Raise vbObjectError + 7316, , "Order number is required."

    Set ws = ITIM_EnsureDataSheet(ITIM_ASSIGNMENTS_SHEET)
    If ws.Cells(1, 1).Value = vbNullString Then ITIM_EnsureAssignmentHeaders ws
    ITIM_EnsureAssignmentRuntimeHeaders ws

    rowNum = ITIM_FindAssignmentRow(ws, orderText, vbNullString)

    If rowNum > 0 Then
        previousStatus = ITIM_CellByHeader(ws, rowNum, "SdiPreviousStatus")

        Select Case UCase$(Trim$(previousStatus))
            Case "NOASSIGNMENT"
                ITIM_SetCellByHeader ws, rowNum, "AssignmentStatus", "Cleared"
                ITIM_SetCellByHeader ws, rowNum, "BayKey", vbNullString
                ITIM_SetCellByHeader ws, rowNum, "BayDisplayName", vbNullString
                ITIM_SetCellByHeader ws, rowNum, "GlassCategory", vbNullString
                ITIM_SetCellByHeader ws, rowNum, "GlassHeader", vbNullString
                ITIM_SetCellByHeader ws, rowNum, "ClearedAt", ITIM_NowStamp()

            Case "PREASSIGNED", "OCCUPIED", "MANUALEXCEPTION"
                ITIM_SetCellByHeader ws, rowNum, "AssignmentStatus", previousStatus
                ITIM_SetCellByHeader ws, rowNum, "BayKey", ITIM_CellByHeader(ws, rowNum, "SdiPreviousBayKey")
                ITIM_SetCellByHeader ws, rowNum, "BayDisplayName", ITIM_CellByHeader(ws, rowNum, "SdiPreviousBayDisplayName")
                ITIM_SetCellByHeader ws, rowNum, "GlassCategory", ITIM_CellByHeader(ws, rowNum, "SdiPreviousGlassCategory")
                ITIM_SetCellByHeader ws, rowNum, "GlassHeader", ITIM_CellByHeader(ws, rowNum, "SdiPreviousGlassHeader")

            Case Else
                bayText = ITIM_CellByHeader(ws, rowNum, "BayDisplayName")
                If Len(bayText) > 0 Then
                    ITIM_SetCellByHeader ws, rowNum, "AssignmentStatus", "PreAssigned"
                Else
                    ITIM_SetCellByHeader ws, rowNum, "AssignmentStatus", "ManualException"
                End If
        End Select

        ITIM_SetCellByHeader ws, rowNum, "Notes", ITIM_AppendNote(ITIM_CellByHeader(ws, rowNum, "Notes"), notesText)
        ITIM_SetCellByHeader ws, rowNum, "SdiPreviousStatus", vbNullString
        ITIM_SetCellByHeader ws, rowNum, "SdiPreviousBayKey", vbNullString
        ITIM_SetCellByHeader ws, rowNum, "SdiPreviousBayDisplayName", vbNullString
        ITIM_SetCellByHeader ws, rowNum, "SdiPreviousGlassCategory", vbNullString
        ITIM_SetCellByHeader ws, rowNum, "SdiPreviousGlassHeader", vbNullString
    End If

    ITIM_UpsertSpecialOrder orderText, "SDI", "Cleared", notesText

    ITIM_LocalRemoveSdi = "Order SDI flag cleared locally."
End Function

Private Function ITIM_FindAssignmentRow(ByVal ws As Worksheet, ByVal orderText As String, ByVal bayText As String) As Long
    Dim lastRow As Long
    Dim r As Long
    Dim orderNeedle As String
    Dim bayNeedle As String

    orderNeedle = Trim$(orderText)
    bayNeedle = Trim$(bayText)
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row

    For r = 2 To lastRow
        If ITIM_IsActiveAssignmentStatus(ITIM_CellByHeader(ws, r, "AssignmentStatus")) Then
            If Len(orderNeedle) > 0 Then
                If StrComp(ITIM_CellByHeader(ws, r, "OrderNumber"), orderNeedle, vbTextCompare) = 0 Or _
                   StrComp(ITIM_CellByHeader(ws, r, "NormalizedOrderNumber"), orderNeedle, vbTextCompare) = 0 Then
                    ITIM_FindAssignmentRow = r
                    Exit Function
                End If
            End If

            If Len(bayNeedle) > 0 Then
                If StrComp(ITIM_CellByHeader(ws, r, "BayDisplayName"), bayNeedle, vbTextCompare) = 0 Or _
                   StrComp(ITIM_CellByHeader(ws, r, "BayKey"), bayNeedle, vbTextCompare) = 0 Then
                    ITIM_FindAssignmentRow = r
                    Exit Function
                End If
            End If
        End If
    Next r
End Function

Private Function ITIM_NewAssignmentRow(ByVal ws As Worksheet, ByVal deliveryListKey As String, ByVal orderText As String) As Long
    Dim rowNum As Long
    Dim normalizedOrder As String

    normalizedOrder = Trim$(orderText)
    If Len(Trim$(deliveryListKey)) = 0 Then deliveryListKey = ITIM_DefaultDeliveryListKey()
    If Len(Trim$(deliveryListKey)) = 0 Then deliveryListKey = "DL_UNKNOWN"

    rowNum = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row + 1
    If rowNum < 2 Then rowNum = 2

    ITIM_SetCellByHeader ws, rowNum, "OrderNumber", normalizedOrder
    ITIM_SetCellByHeader ws, rowNum, "NormalizedOrderNumber", normalizedOrder
    ITIM_SetCellByHeader ws, rowNum, "DeliveryListKey", deliveryListKey
    ITIM_SetCellByHeader ws, rowNum, "AssignmentGroupId", deliveryListKey & "-" & normalizedOrder
    ITIM_SetCellByHeader ws, rowNum, "PreAssignedAt", ITIM_NowStamp()
    ITIM_SetCellByHeader ws, rowNum, "LastScanStation", Environ$("COMPUTERNAME")

    ITIM_NewAssignmentRow = rowNum
End Function

Private Function ITIM_BayKeyForDisplay(ByVal bayDisplayName As String) As String
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim r As Long

    Set ws = ITIM_GetWorksheet(ITIM_BAYS_SHEET)
    If ws Is Nothing Then
        On Error Resume Next
        ITIM_LoadCsvToSheet ITIM_BAYS_CSV, ITIM_BAYS_SHEET
        Set ws = ITIM_GetWorksheet(ITIM_BAYS_SHEET)
        On Error GoTo 0
    End If

    If ws Is Nothing Then
        ITIM_BayKeyForDisplay = bayDisplayName
        Exit Function
    End If

    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row

    For r = 2 To lastRow
        If StrComp(ITIM_CellByHeader(ws, r, "BayDisplayName"), bayDisplayName, vbTextCompare) = 0 Or _
           StrComp(ITIM_CellByHeader(ws, r, "BayKey"), bayDisplayName, vbTextCompare) = 0 Then
            ITIM_BayKeyForDisplay = ITIM_CellByHeader(ws, r, "BayKey")
            Exit Function
        End If
    Next r

    ITIM_BayKeyForDisplay = bayDisplayName
End Function

Private Sub ITIM_UpsertSpecialOrder(ByVal orderText As String, ByVal specialType As String, ByVal specialStatus As String, ByVal notesText As String)
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim r As Long
    Dim targetRow As Long

    Set ws = ITIM_EnsureDataSheet(ITIM_SPECIAL_SHEET)

    If ws.Cells(1, 1).Value = vbNullString Then
        ws.Range("A1:H1").Value = Array("OrderNumber", "NormalizedOrderNumber", "SpecialType", "EffectiveDate", "SpecialStatus", "EnteredAt", "EnteredBy", "Notes")
    End If

    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row

    For r = 2 To lastRow
        If StrComp(ITIM_CellByHeader(ws, r, "NormalizedOrderNumber"), orderText, vbTextCompare) = 0 And _
           StrComp(ITIM_CellByHeader(ws, r, "SpecialType"), specialType, vbTextCompare) = 0 Then
            targetRow = r
            Exit For
        End If
    Next r

    If targetRow = 0 Then targetRow = lastRow + 1

    ITIM_SetCellByHeader ws, targetRow, "OrderNumber", orderText
    ITIM_SetCellByHeader ws, targetRow, "NormalizedOrderNumber", orderText
    ITIM_SetCellByHeader ws, targetRow, "SpecialType", specialType
    ITIM_SetCellByHeader ws, targetRow, "SpecialStatus", specialStatus
    ITIM_SetCellByHeader ws, targetRow, "EnteredAt", ITIM_NowStamp()
    ITIM_SetCellByHeader ws, targetRow, "EnteredBy", Environ$("USERNAME")
    ITIM_SetCellByHeader ws, targetRow, "Notes", ITIM_AppendNote(ITIM_CellByHeader(ws, targetRow, "Notes"), notesText)
End Sub

Private Function ITIM_PostAdminAction(ByVal actionText As String, _
                                      ByVal deliveryListKey As String, _
                                      ByVal orderText As String, _
                                      ByVal bayText As String, _
                                      ByVal newBayText As String, _
                                      ByVal glassCategory As String, _
                                      ByVal glassHeader As String, _
                                      ByVal notesText As String, _
                                      ByRef responseText As String) As Boolean
    Dim http As Object
    Dim payload As String
    Dim flowActionText As String

    If Len(Trim$(ITIM_URL_BAY_ADMIN_ACTION)) = 0 Then
        responseText = "SharePoint write-back flow is not configured yet. Local workbook/map cache was updated only."
        Exit Function
    End If

    flowActionText = ITIM_AdminFlowActionText(actionText)

    payload = "{" & _
              """action"":" & ITIM_JsonString(flowActionText) & "," & _
              """deliveryListKey"":" & ITIM_JsonString(deliveryListKey) & "," & _
              """orderNumber"":" & ITIM_JsonString(orderText) & "," & _
              """bayDisplayName"":" & ITIM_JsonString(bayText) & "," & _
              """newBayDisplayName"":" & ITIM_JsonString(newBayText) & "," & _
              """glassCategory"":" & ITIM_JsonString(glassCategory) & "," & _
              """glassHeader"":" & ITIM_JsonString(glassHeader) & "," & _
              """notes"":" & ITIM_JsonString(notesText) & "," & _
              """stationName"":" & ITIM_JsonString(Environ$("COMPUTERNAME")) & "," & _
              """sourceWorkbook"":" & ITIM_JsonString(ThisWorkbook.Name) & _
              "}"

    Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")
    http.Open "POST", ITIM_URL_BAY_ADMIN_ACTION, False
    http.setRequestHeader "Content-Type", "application/json"
    http.Send payload

    responseText = ITIM_FriendlyFlowResponse(CStr(http.responseText), CLng(http.Status))
    If http.Status < 200 Or http.Status >= 300 Then
        responseText = ITIM_AdminFlowFallbackMessage(flowActionText, CLng(http.Status), responseText)
    End If
    ITIM_PostAdminAction = (http.Status >= 200 And http.Status < 300)
End Function

Private Function ITIM_AdminFlowActionText(ByVal actionText As String) As String
    Select Case UCase$(Trim$(actionText))
        Case "SCAN OUT", "SCAN OUT OF BAY", "SCANOUT", "CLEAR"
            ITIM_AdminFlowActionText = "Clear Bay"
        Case "MOVE"
            ITIM_AdminFlowActionText = "Move Order"
        Case "EXCEPTION"
            ITIM_AdminFlowActionText = "Manual Exception"
        Case "MARK", "SDI"
            ITIM_AdminFlowActionText = "Mark SDI"
        Case "REMOVE"
            ITIM_AdminFlowActionText = "Remove SDI"
        Case Else
            ITIM_AdminFlowActionText = actionText
    End Select
End Function

Private Function ITIM_FriendlyFlowResponse(ByVal rawResponse As String, ByVal statusCode As Long) As String
    Dim messageText As String
    Dim resultCode As String
    Dim trimmedResponse As String

    trimmedResponse = Trim$(rawResponse)
    messageText = ITIM_ExtractJsonString(trimmedResponse, "message")
    resultCode = ITIM_ExtractJsonString(trimmedResponse, "resultCode")

    If Len(messageText) > 0 Then
        ITIM_FriendlyFlowResponse = messageText
        If Len(resultCode) > 0 Then ITIM_FriendlyFlowResponse = ITIM_FriendlyFlowResponse & " (" & resultCode & ")"
    ElseIf statusCode >= 200 And statusCode < 300 Then
        ITIM_FriendlyFlowResponse = "SharePoint updated."
    ElseIf Len(trimmedResponse) > 0 Then
        ITIM_FriendlyFlowResponse = "Flow HTTP " & statusCode & ": " & Left$(trimmedResponse, 260)
    Else
        ITIM_FriendlyFlowResponse = "Flow HTTP " & statusCode & " did not return a message."
    End If
End Function

Private Function ITIM_AdminFlowFallbackMessage(ByVal actionText As String, ByVal statusCode As Long, ByVal currentMessage As String) As String
    Dim currentText As String

    currentText = Trim$(currentMessage)
    If Len(currentText) > 0 And InStr(1, currentText, "did not return a message", vbTextCompare) = 0 Then
        ITIM_AdminFlowFallbackMessage = currentText
        Exit Function
    End If

    Select Case statusCode
        Case 404
            Select Case UCase$(Trim$(actionText))
                Case "CLEAR BAY"
                    ITIM_AdminFlowFallbackMessage = "No active bay assignment was found to clear. SharePoint was not changed."
                Case "MOVE ORDER", "MANUAL ASSIGN", "MANUAL EXCEPTION", "MARK SDI", "REMOVE SDI"
                    ITIM_AdminFlowFallbackMessage = "No matching active assignment or special-order row was found in SharePoint."
                Case Else
                    ITIM_AdminFlowFallbackMessage = "The admin flow did not find a matching SharePoint record."
            End Select

        Case 400
            ITIM_AdminFlowFallbackMessage = "The admin flow rejected the request. Check the action, order number, bay, and flow expressions."

        Case Else
            ITIM_AdminFlowFallbackMessage = "Flow HTTP " & statusCode & ". SharePoint may not have been updated."
    End Select
End Function

Private Function ITIM_ExtractJsonString(ByVal jsonText As String, ByVal keyText As String) As String
    Dim marker As String
    Dim startPos As Long
    Dim pos As Long
    Dim ch As String
    Dim valueText As String
    Dim escaped As Boolean

    marker = Chr$(34) & keyText & Chr$(34) & ":"
    startPos = InStr(1, jsonText, marker, vbTextCompare)
    If startPos = 0 Then Exit Function

    startPos = startPos + Len(marker)
    Do While startPos <= Len(jsonText) And Mid$(jsonText, startPos, 1) = " "
        startPos = startPos + 1
    Loop

    If startPos > Len(jsonText) Then Exit Function

    If Mid$(jsonText, startPos, 1) <> Chr$(34) Then
        For pos = startPos To Len(jsonText)
            ch = Mid$(jsonText, pos, 1)
            If ch = "," Or ch = "}" Then Exit For
            valueText = valueText & ch
        Next pos
        ITIM_ExtractJsonString = Trim$(valueText)
        Exit Function
    End If

    startPos = startPos + 1
    For pos = startPos To Len(jsonText)
        ch = Mid$(jsonText, pos, 1)
        If escaped Then
            valueText = valueText & ITIM_UnescapeJsonChar(ch)
            escaped = False
        ElseIf ch = "\" Then
            escaped = True
        ElseIf ch = Chr$(34) Then
            Exit For
        Else
            valueText = valueText & ch
        End If
    Next pos

    ITIM_ExtractJsonString = valueText
End Function

Private Function ITIM_UnescapeJsonChar(ByVal ch As String) As String
    Select Case ch
        Case "n"
            ITIM_UnescapeJsonChar = vbCrLf
        Case "r"
            ITIM_UnescapeJsonChar = vbCr
        Case "t"
            ITIM_UnescapeJsonChar = vbTab
        Case Else
            ITIM_UnescapeJsonChar = ch
    End Select
End Function

Private Function ITIM_JsonString(ByVal valueText As String) As String
    Dim s As String

    s = CStr(valueText)
    s = Replace$(s, "\", "\\")
    s = Replace$(s, Chr$(34), "\" & Chr$(34))
    s = Replace$(s, vbCrLf, "\n")
    s = Replace$(s, vbCr, "\n")
    s = Replace$(s, vbLf, "\n")

    ITIM_JsonString = """" & s & """"
End Function

Private Function ITIM_AppendNote(ByVal existingText As String, ByVal newText As String) As String
    Dim cleanNew As String

    cleanNew = Trim$(newText)

    If Len(cleanNew) = 0 Then
        ITIM_AppendNote = existingText
    ElseIf Len(Trim$(existingText)) = 0 Then
        ITIM_AppendNote = ITIM_NowStamp() & " - " & cleanNew
    Else
        ITIM_AppendNote = existingText & vbLf & ITIM_NowStamp() & " - " & cleanNew
    End If
End Function

Private Function ITIM_NowStamp() As String
    ITIM_NowStamp = Format$(Now, "yyyy-mm-dd hh:nn:ss")
End Function

Private Sub ITIM_OpenUrlOrLocalCsv(ByVal urlText As String, ByVal csvName As String)
    Dim csvPath As String

    If Len(Trim$(urlText)) > 0 Then
        ThisWorkbook.FollowHyperlink urlText
        Exit Sub
    End If

    csvPath = ITIM_ProjectRoot() & Application.PathSeparator & "Sharepoint Lists" & Application.PathSeparator & csvName
    If Len(Dir$(csvPath, vbNormal)) > 0 Then
        ThisWorkbook.FollowHyperlink csvPath
    Else
        MsgBox "No SharePoint URL is configured and the local CSV was not found:" & vbCrLf & csvPath, vbExclamation, "Open List"
    End If
End Sub
