Attribute VB_Name = "modIntakePrintExportTemplates"
Option Explicit

'==============================================================================
' Module: modIntakePrintExportTemplates
' Workbook: Intake_Staging_Test.xlsm
'
' Purpose:
'   Coordinates intake print/export requests after the user clicks Print or Export.
'
' Main responsibilities:
'   1. Validate that the imported stage sheet is available.
'   2. Find the Order Nr. and Item Nr. columns on the imported stage sheet.
'   3. Open the print/export option forms.
'   4. Route the request to the correct builder in modIntakePrintHelpers.
'
' Cleanup/debug notes:
'   The old module contained unused private glass-selection helpers. Those were
'   removed because the userforms already return selectedGlassKeys, and the live
'   row filtering is handled inside modIntakePrintHelpers.
'==============================================================================

Private Const HEADER_SEARCH_TOP_ROWS As Long = 250
Private Const DELIVERY_HEADER_COLS As String = "A:N"


'==============================================================================
' Header finder - anywhere across the top rows
'
' Looks for an exact header match first, then a partial match.
'==============================================================================
Private Function FindHeaderCellTemplate(ByVal ws As Worksheet, _
                                        ByVal names As Variant, _
                                        Optional ByVal topRows As Long = HEADER_SEARCH_TOP_ROWS) As Range
    Dim searchRange As Range
    Dim nm As Variant
    Dim f As Range

    If ws Is Nothing Then Exit Function
    If topRows < 1 Then topRows = HEADER_SEARCH_TOP_ROWS

    Set searchRange = ws.Range(ws.Cells(1, 1), ws.Cells(topRows, ws.Columns.Count))

    For Each nm In names
        Set f = searchRange.Find(What:=CStr(nm), _
                                 After:=searchRange.Cells(searchRange.Cells.Count), _
                                 LookIn:=xlValues, _
                                 LookAt:=xlWhole, _
                                 SearchOrder:=xlByRows, _
                                 SearchDirection:=xlNext, _
                                 MatchCase:=False)
        If Not f Is Nothing Then
            Set FindHeaderCellTemplate = f
            Exit Function
        End If
    Next nm

    For Each nm In names
        Set f = searchRange.Find(What:=CStr(nm), _
                                 After:=searchRange.Cells(searchRange.Cells.Count), _
                                 LookIn:=xlValues, _
                                 LookAt:=xlPart, _
                                 SearchOrder:=xlByRows, _
                                 SearchDirection:=xlNext, _
                                 MatchCase:=False)
        If Not f Is Nothing Then
            Set FindHeaderCellTemplate = f
            Exit Function
        End If
    Next nm
End Function


'==============================================================================
' Header finder - limited to specific columns
'
' Used for the main delivery-list headers, which should be in A:N.
'==============================================================================
Private Function FindHeaderCellTemplateInCols(ByVal ws As Worksheet, _
                                              ByVal names As Variant, _
                                              ByVal colAddress As String, _
                                              Optional ByVal topRows As Long = HEADER_SEARCH_TOP_ROWS) As Range
    Dim searchRange As Range
    Dim nm As Variant
    Dim f As Range

    If ws Is Nothing Then Exit Function
    If Len(Trim$(colAddress)) = 0 Then Exit Function
    If topRows < 1 Then topRows = HEADER_SEARCH_TOP_ROWS

    Set searchRange = Intersect(ws.Range("1:" & topRows), ws.Columns(colAddress))
    If searchRange Is Nothing Then Exit Function

    For Each nm In names
        Set f = searchRange.Find(What:=CStr(nm), _
                                 After:=searchRange.Cells(searchRange.Cells.Count), _
                                 LookIn:=xlValues, _
                                 LookAt:=xlWhole, _
                                 SearchOrder:=xlByRows, _
                                 SearchDirection:=xlNext, _
                                 MatchCase:=False)
        If Not f Is Nothing Then
            Set FindHeaderCellTemplateInCols = f
            Exit Function
        End If
    Next nm

    For Each nm In names
        Set f = searchRange.Find(What:=CStr(nm), _
                                 After:=searchRange.Cells(searchRange.Cells.Count), _
                                 LookIn:=xlValues, _
                                 LookAt:=xlPart, _
                                 SearchOrder:=xlByRows, _
                                 SearchDirection:=xlNext, _
                                 MatchCase:=False)
        If Not f Is Nothing Then
            Set FindHeaderCellTemplateInCols = f
            Exit Function
        End If
    Next nm
End Function


'==============================================================================
' Real delivery-line detector
'
' A row counts as a real line when it has an order or item value.
'==============================================================================
Private Function IsRealDeliveryLineTemplate(ByVal ws As Worksheet, _
                                            ByVal rowNum As Long, _
                                            ByVal orderCol As Long, _
                                            ByVal itemCol As Long) As Boolean
    If ws Is Nothing Then Exit Function
    If rowNum < 1 Or orderCol < 1 Or itemCol < 1 Then Exit Function

    IsRealDeliveryLineTemplate = _
        (Len(Trim$(CStr(ws.Cells(rowNum, orderCol).Value))) > 0 Or _
         Len(Trim$(CStr(ws.Cells(rowNum, itemCol).Value))) > 0)
End Function


'==============================================================================
' Last real delivery row finder
'
' Walks upward from the last used order row until it finds a real delivery line.
'==============================================================================
Private Function FindLastRealDeliveryRowTemplate(ByVal ws As Worksheet, _
                                                 ByVal orderCol As Long, _
                                                 ByVal itemCol As Long, _
                                                 ByVal firstDataRow As Long) As Long
    Dim lastRow As Long
    Dim r As Long

    If ws Is Nothing Then Exit Function
    If firstDataRow < 1 Or orderCol < 1 Or itemCol < 1 Then Exit Function

    lastRow = ws.Cells(ws.Rows.Count, orderCol).End(xlUp).Row
    If lastRow < firstDataRow Then Exit Function

    For r = lastRow To firstDataRow Step -1
        If IsRealDeliveryLineTemplate(ws, r, orderCol, itemCol) Then
            FindLastRealDeliveryRowTemplate = r
            Exit Function
        End If
    Next r
End Function


'==============================================================================
' Print-options form wrapper
'
' Opens frmPrintOptions and returns the selected filters/action/copy count.
'==============================================================================
Private Function PromptForPrintOptionsTemplate(ByVal ws As Worksheet, _
                                               ByVal firstDataRow As Long, _
                                               ByVal lastRealRow As Long, _
                                               ByVal orderCol As Long, _
                                               ByVal itemCol As Long, _
                                               ByRef printKind As String, _
                                               ByRef destinationMode As String, _
                                               ByRef selectedGlassKeys As String, _
                                               ByRef selectedAction As String, _
                                               ByRef selectedCopies As Long) As Boolean
    Dim frm As frmPrintOptions

    Set frm = New frmPrintOptions
    frm.LoadOptions ws, firstDataRow, lastRealRow, orderCol, itemCol
    frm.Show vbModal

    If frm.WasCancelled Then GoTo SafeExit

    printKind = frm.SelectedPrintKind
    destinationMode = frm.SelectedDestinationMode
    selectedGlassKeys = frm.selectedGlassKeys
    selectedAction = frm.selectedAction
    selectedCopies = frm.selectedCopies

    PromptForPrintOptionsTemplate = _
        (Len(printKind) > 0 And _
         Len(destinationMode) > 0 And _
         Len(selectedGlassKeys) > 0 And _
         Len(selectedAction) > 0)

SafeExit:
    On Error Resume Next
    Unload frm
    Set frm = Nothing
    On Error GoTo 0
End Function


'==============================================================================
' Export-options form wrapper
'
' Opens frmExportOptions and returns the selected filters/action.
'==============================================================================
Private Function PromptForExportOptionsTemplate(ByVal ws As Worksheet, _
                                                ByVal firstDataRow As Long, _
                                                ByVal lastRealRow As Long, _
                                                ByVal orderCol As Long, _
                                                ByVal itemCol As Long, _
                                                ByRef exportKind As String, _
                                                ByRef destinationMode As String, _
                                                ByRef selectedGlassKeys As String, _
                                                ByRef selectedAction As String) As Boolean
    Dim frm As frmExportOptions

    Set frm = New frmExportOptions
    frm.LoadOptions ws, firstDataRow, lastRealRow, orderCol, itemCol
    frm.Show vbModal

    If frm.WasCancelled Then GoTo SafeExit

    exportKind = frm.SelectedExportKind
    destinationMode = frm.SelectedDestinationMode
    selectedGlassKeys = frm.selectedGlassKeys
    selectedAction = frm.selectedAction

    PromptForExportOptionsTemplate = _
        (Len(exportKind) > 0 And _
         Len(destinationMode) > 0 And _
         Len(selectedGlassKeys) > 0 And _
         Len(selectedAction) > 0)

SafeExit:
    On Error Resume Next
    Unload frm
    Set frm = Nothing
    On Error GoTo 0
End Function


'==============================================================================
' Intake print entry point
'
' Validates the imported sheet, asks the user for print options, then routes to
' either normal delivery-list print preview/print or remake print preview/print.
'==============================================================================
Public Sub PrintDeliveryListBySection_Intake()
    Dim ws As Worksheet
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim orderCol As Long
    Dim itemCol As Long
    Dim firstDataRow As Long
    Dim lastRealRow As Long
    Dim destinationMode As String
    Dim printKind As String
    Dim selectedGlassKeys As String
    Dim selectedAction As String
    Dim sections As Collection
    Dim selectedCopies As Long

    On Error GoTo ErrHandler

    If Not EnsureIntakePrintExportReady(ws) Then Exit Sub

    Set orderHdr = FindHeaderCellTemplateInCols(ws, Array("Order Nr."), DELIVERY_HEADER_COLS, HEADER_SEARCH_TOP_ROWS)
    Set itemHdr = FindHeaderCellTemplateInCols(ws, Array("Item Nr.", "Item"), DELIVERY_HEADER_COLS, HEADER_SEARCH_TOP_ROWS)

    If orderHdr Is Nothing Or itemHdr Is Nothing Then
        MsgBox "Could not find the Delivery List headers.", vbExclamation, "Print Delivery List"
        Exit Sub
    End If

    orderCol = orderHdr.Column
    itemCol = itemHdr.Column
    firstDataRow = orderHdr.Row + 1
    lastRealRow = FindLastRealDeliveryRowTemplate(ws, orderCol, itemCol, firstDataRow)

    If lastRealRow < firstDataRow Then
        MsgBox "There are no printable delivery lines on the imported delivery list.", vbExclamation, "Print Delivery List"
        Exit Sub
    End If

    If Not PromptForPrintOptionsTemplate(ws, firstDataRow, lastRealRow, orderCol, itemCol, _
                                         printKind, destinationMode, selectedGlassKeys, selectedAction, selectedCopies) Then
        Exit Sub
    End If

    Set sections = GetDeliveryListSectionsForPrintKind(ws, firstDataRow, lastRealRow, orderCol, itemCol, destinationMode, printKind)

    If sections Is Nothing Then
        MsgBox "There are no rows that match the selected destination/filter.", vbInformation, "Print Delivery List"
        Exit Sub
    End If

    If sections.Count = 0 Then
        MsgBox "There are no rows that match the selected destination/filter.", vbInformation, "Print Delivery List"
        Exit Sub
    End If

    Select Case UCase$(printKind)
        Case "REMAKES", "UPDATED_REMAKES"
            If Not RequireIntakeRemakeTemplateSheet() Then Exit Sub

            BuildAndPreviewRemakePrintFromTemplate ws, 0, 0, firstDataRow, lastRealRow, _
                                                   orderCol, itemCol, destinationMode, _
                                                   selectedGlassKeys, printKind, selectedAction, selectedCopies

        Case Else
            BuildAndPreviewDeliveryListPrint ws, 0, 0, firstDataRow, lastRealRow, _
                                             orderCol, itemCol, destinationMode, _
                                             selectedGlassKeys, printKind, selectedAction, selectedCopies
    End Select

    Exit Sub

ErrHandler:
    MsgBox "PrintDeliveryListBySection_Intake error " & Err.Number & ":" & vbCrLf & Err.Description, _
           vbCritical, "Print Error"
End Sub


'==============================================================================
' Intake export entry point
'
' Validates the imported sheet, asks the user for export options, then creates
' either a normal delivery-list export workbook or a remake-list export workbook.
'==============================================================================
Public Sub ExportListsFromIntake()
    Dim srcWs As Worksheet
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim firstDataRow As Long
    Dim lastRealRow As Long
    Dim orderCol As Long
    Dim itemCol As Long
    Dim exportKind As String
    Dim destinationMode As String
    Dim selectedGlassKeys As String
    Dim selectedAction As String
    Dim oldScreenUpdating As Boolean
    Dim oldEnableEvents As Boolean
    Dim oldDisplayAlerts As Boolean

    On Error GoTo ErrHandler

    oldScreenUpdating = Application.ScreenUpdating
    oldEnableEvents = Application.EnableEvents
    oldDisplayAlerts = Application.DisplayAlerts

    If Not EnsureIntakePrintExportReady(srcWs) Then Exit Sub

    Set orderHdr = FindHeaderCellTemplate(srcWs, Array("Order Nr."))
    Set itemHdr = FindHeaderCellTemplate(srcWs, Array("Item Nr.", "Item"))

    If orderHdr Is Nothing Or itemHdr Is Nothing Then
        MsgBox "Could not find Order Nr. / Item headers for export.", vbExclamation, "Export List"
        Exit Sub
    End If

    firstDataRow = orderHdr.Row + 1
    orderCol = orderHdr.Column
    itemCol = itemHdr.Column
    lastRealRow = FindLastRealDeliveryRowTemplate(srcWs, orderCol, itemCol, firstDataRow)

    If lastRealRow < firstDataRow Then
        MsgBox "No delivery rows were found to export.", vbInformation, "Export List"
        Exit Sub
    End If

    If Not PromptForExportOptionsTemplate(srcWs, firstDataRow, lastRealRow, orderCol, itemCol, _
                                          exportKind, destinationMode, selectedGlassKeys, selectedAction) Then
        Exit Sub
    End If

    Application.ScreenUpdating = False
    Application.EnableEvents = False
    Application.DisplayAlerts = True

    Select Case UCase$(exportKind)
        Case "ORDERS", "UPDATED_ORDERS", "UPDATED_ALL", "ALL"
            ExportDeliveryListWorkbookTemplate srcWs, destinationMode, selectedGlassKeys, exportKind

        Case "REMAKES", "UPDATED_REMAKES"
            If Not RequireIntakeRemakeTemplateSheet() Then GoTo SafeExit
            ExportRemakeListWorkbookTemplate srcWs, destinationMode, selectedGlassKeys, exportKind

        Case Else
            MsgBox "Unsupported export type: " & exportKind, vbExclamation, "Export List"
    End Select

SafeExit:
    Application.DisplayAlerts = oldDisplayAlerts
    Application.EnableEvents = oldEnableEvents
    Application.ScreenUpdating = oldScreenUpdating
    Exit Sub

ErrHandler:
    Application.DisplayAlerts = oldDisplayAlerts
    Application.EnableEvents = oldEnableEvents
    Application.ScreenUpdating = oldScreenUpdating

    MsgBox "ExportListsFromIntake error " & Err.Number & ":" & vbCrLf & Err.Description, _
           vbCritical, "Export Error"
End Sub


