Attribute VB_Name = "modIntakePrintHelpers"
Option Explicit

'==============================================================================
' Module: modIntakePrintHelpers
' Workbook: Intake_Staging_Test.xlsm
'
' Purpose:
'   Shared print/export engine for the intake workbook.
'
' What remains in this cleaned version:
'   - Destination filtering: Indian Trail / Greenville / Customer Pickup
'   - Print-kind filtering: orders, remakes, updated orders, updated remakes,
'     updated all, and all rows
'   - Glass-section filtering
'   - Delivery-list print preview/print builder
'   - Remake print preview/print builder
'   - Delivery-list .xlsx export builder
'   - Remake .xlsx export builder
'   - UserForm support functions used by frmPrintOptions and frmExportOptions
'
' What was intentionally removed:
'   Master-workbook-only import/update/menu/sync/navigation procedures were
'   removed from this intake helper module. The intake workbook should not carry
'   master Delivery List import/update logic in the print/export helper layer.
'==============================================================================

Private Const GREENVILLE_CUSTOMER_TEXT As String = "BFS East Greenville SC MW"
Private Const CPU_ROUTE_TEXT As String = "CPU"

Private Const PRINT_HELPER_SECTION_COL As Long = 40   'AN - hidden helper section name for page-break logic
Private Const PRINT_HELPER_ROWTYPE_COL As Long = 41   'AO - hidden helper row type for page-break logic
Private Const FIRST_DATA_ROW_FIXED As Long = 6

Private Const REMAKE_MARKER_TEXT As String = "RM"
Private Const REMAKE_PRINT_TEMPLATE_SHEET As String = "__REMAKE_PRINT_TEMPLATE__"
Private Const REMAKE_PRINT_PREVIEW_SHEET As String = "__REMAKE_PRINT_PREVIEW__"
Private Const REMAKE_TITLE_PREFIX As String = "                 REMAKES DUE: "

Private Const REMAKE_MARKER_COL_FIXED As Long = 11   'Column K
Private Const ROUTE_COL_FIXED As Long = 12           'Column L



'==============================================================================
' Destination and row classification helpers
'==============================================================================


'------------------------------------------------------------------------------
' Returns True when a delivery row is marked as Customer Pickup/CPU.
'------------------------------------------------------------------------------

Private Function IsCPURowTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, Optional ByVal RouteCol As Long = 0) As Boolean
    Dim routeText As String

    If rowNum < FIRST_DATA_ROW_FIXED Then Exit Function

    routeText = CStr(ws.Cells(rowNum, ROUTE_COL_FIXED).Value)
    routeText = Replace$(routeText, Chr$(160), " ")
    routeText = Application.WorksheetFunction.Clean(routeText)
    routeText = Application.WorksheetFunction.Trim(routeText)
    routeText = UCase$(routeText)

    IsCPURowTemplate = (routeText = UCase$(CPU_ROUTE_TEXT))
End Function


'------------------------------------------------------------------------------
' Finds the Customer column so Greenville rows can be detected.
'------------------------------------------------------------------------------

Private Function GetCustomerColumnTemplate(ByVal ws As Worksheet) As Long
    Dim hdr As Range

    If ws Is Nothing Then Exit Function

    Set hdr = FindHeaderCellTemplate(ws, Array("Customer"))

    If Not hdr Is Nothing Then
        GetCustomerColumnTemplate = hdr.Column
    End If
End Function


'------------------------------------------------------------------------------
' Returns True when a delivery row belongs to the Greenville customer.
'------------------------------------------------------------------------------

Private Function IsGreenvilleRowTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, Optional ByVal customerCol As Long = 0) As Boolean
    If customerCol = 0 Then customerCol = GetCustomerColumnTemplate(ws)
    If customerCol = 0 Then Exit Function

    IsGreenvilleRowTemplate = (UCase$(Trim$(CStr(ws.Cells(rowNum, customerCol).Value))) = UCase$(GREENVILLE_CUSTOMER_TEXT))
End Function


'------------------------------------------------------------------------------
' Normalizes remake marker values and detects RM/remake rows.
'------------------------------------------------------------------------------

Private Function IsRemakeMarkerValueTemplate(ByVal v As Variant) As Boolean
    Dim s As String

    s = UCase$(Trim$(CStr(v)))

    IsRemakeMarkerValueTemplate = _
        (s = UCase$(REMAKE_MARKER_TEXT)) Or _
        (s = "RM")
End Function


'------------------------------------------------------------------------------
' Returns True when a row is marked as a remake.
'------------------------------------------------------------------------------

Private Function IsRemakeRowTemplate(ByVal ws As Worksheet, ByVal rowNum As Long) As Boolean
    IsRemakeRowTemplate = IsRemakeMarkerValueTemplate(ws.Cells(rowNum, REMAKE_MARKER_COL_FIXED).Value)
End Function


'------------------------------------------------------------------------------
' Detects updated rows by their purple outside border style.
'------------------------------------------------------------------------------

Private Function HasUpdatedPurpleOuterBorderTemplate(ByVal ws As Worksheet, ByVal rowNum As Long) As Boolean
    Dim rng As Range

    Set rng = ws.Range("A" & rowNum & ":J" & rowNum)

    On Error Resume Next
    HasUpdatedPurpleOuterBorderTemplate = _
        (rng.Borders(xlEdgeLeft).lineStyle <> xlNone And rng.Borders(xlEdgeLeft).Color = RGB(112, 48, 160)) And _
        (rng.Borders(xlEdgeRight).lineStyle <> xlNone And rng.Borders(xlEdgeRight).Color = RGB(112, 48, 160))
    On Error GoTo 0
End Function


'------------------------------------------------------------------------------
' Applies destination + print/export kind filtering to a row.
'------------------------------------------------------------------------------

Private Function DoesPrintModeMatchRowTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, _
                                               ByVal destinationMode As String, ByVal printKind As String) As Boolean
    Dim isRemake As Boolean
    Dim isUpdated As Boolean

    If Not DoesDestinationMatchRowTemplate(ws, rowNum, destinationMode) Then Exit Function

    isRemake = IsRemakeRowTemplate(ws, rowNum)
    isUpdated = IsUpdatedPrintRowTemplate(ws, rowNum)

    Select Case UCase$(printKind)
        Case "ORDERS"
            DoesPrintModeMatchRowTemplate = (Not isRemake) And (Not isUpdated)

        Case "REMAKES"
            DoesPrintModeMatchRowTemplate = isRemake

        Case "UPDATED_ORDERS"
            DoesPrintModeMatchRowTemplate = isUpdated And (Not isRemake)

        Case "UPDATED_REMAKES"
            DoesPrintModeMatchRowTemplate = isUpdated And isRemake

        Case "UPDATED_ALL"
            DoesPrintModeMatchRowTemplate = isUpdated

        Case "ALL"
            DoesPrintModeMatchRowTemplate = True

        Case Else
            DoesPrintModeMatchRowTemplate = False
    End Select
End Function


'------------------------------------------------------------------------------
' Returns True when a row should count as updated.
'------------------------------------------------------------------------------

Private Function IsUpdatedPrintRowTemplate(ByVal ws As Worksheet, ByVal rowNum As Long) As Boolean
    If ws Is Nothing Then Exit Function
    If rowNum < FIRST_DATA_ROW_FIXED Then Exit Function

    IsUpdatedPrintRowTemplate = HasUpdatedPurpleOuterBorderTemplate(ws, rowNum)
End Function


'------------------------------------------------------------------------------
' Builds the destination label used in print/export titles.
'------------------------------------------------------------------------------

Private Function GetSingleDestinationTitleLabelTemplate(ByVal destinationMode As String) As String
    Dim hitCount As Long
    Dim labelText As String

    destinationMode = UCase$(Trim$(destinationMode))
    If destinationMode = "ALL" Then Exit Function

    If TokenListContainsTemplate(destinationMode, "STANDARD") Then
        hitCount = hitCount + 1
        labelText = "INDIAN TRAIL"
    End If

    If TokenListContainsTemplate(destinationMode, "GREENVILLE") Then
        hitCount = hitCount + 1
        labelText = "GREENVILLE"
    End If

    If TokenListContainsTemplate(destinationMode, "CPU") Then
        hitCount = hitCount + 1
        labelText = "CUSTOMER PICKUP"
    End If

    If hitCount = 1 Then
        GetSingleDestinationTitleLabelTemplate = labelText
    Else
        GetSingleDestinationTitleLabelTemplate = vbNullString
    End If
End Function


'------------------------------------------------------------------------------
' Writes the print/export title for the selected destination.
'------------------------------------------------------------------------------

Private Sub ApplyDestinationAwareDeliveryTitleTemplate(ByVal ws As Worksheet, _
                                                       ByVal srcWs As Worksheet, _
                                                       ByVal destinationMode As String)
    Dim singleDestLabel As String
    Dim dateText As String
    Dim listDate As Date
    Dim line1Text As String
    Dim line2Text As String
    Dim fullText As String
    Dim line2Start As Long

    If ws Is Nothing Or srcWs Is Nothing Then Exit Sub

    singleDestLabel = GetSingleDestinationTitleLabelTemplate(destinationMode)
    listDate = GetDeliveryListDateForFileName(srcWs)

    If listDate > 0 Then
        dateText = Format$(listDate, "m/d/yyyy")
    Else
        dateText = vbNullString
    End If

    line1Text = "DELIVERY LIST FOR:"

    If Len(singleDestLabel) > 0 Then
        If Len(dateText) > 0 Then
            line2Text = singleDestLabel & " " & dateText
        Else
            line2Text = singleDestLabel
        End If
    Else
        If Len(dateText) > 0 Then
            line2Text = dateText
        Else
            line2Text = vbNullString
        End If
    End If

    If Len(line2Text) > 0 Then
        fullText = line1Text & vbLf & line2Text
    Else
        fullText = line1Text
    End If

    On Error Resume Next
    ws.Unprotect Password:=""
    ws.Range("A2:N3").UnMerge
    On Error GoTo 0

    'Start the title band a little to the right so it clears the logo better
    With ws.Range("A2:N3")
        .Merge
        .Value = fullText
        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
        .WrapText = True
        .Font.Name = "Calibri"
        .Font.Bold = True
        .Font.Italic = False
        .Font.Size = 20
        .Font.Color = RGB(0, 0, 0)
    End With

    'Italicize only the second line
    If Len(line2Text) > 0 Then
        line2Start = Len(line1Text) + 2   'vbLf counts as 1 char, next line starts after it
        With ws.Range("A2").Characters(line2Start, Len(line2Text)).Font
            .Bold = True
            .Italic = True
            .Underline = True
            .Size = 20
            .Color = RGB(0, 0, 0)
        End With
    End If
End Sub


'------------------------------------------------------------------------------
' Keeps copied logos inside the header area without overlapping headers.
'------------------------------------------------------------------------------

Private Sub RepositionPrintPreviewLogoTemplate(ByVal ws As Worksheet)
    Dim shp As Shape
    Dim safeBottom As Double
    Dim actualBottom As Double
    Dim extra As Double
    Dim bump As Double

    If ws Is Nothing Then Exit Sub

    On Error Resume Next

    For Each shp In ws.Shapes
        If LCase$(Left$(shp.Name, 13)) = "dlsharedlogo_" Then
            shp.LockAspectRatio = msoTrue

            'Keep the logo in the top-left corner at full size
            shp.Left = ws.Range("A1").Left + 3
            shp.Top = ws.Range("A1").Top + 3

            'Do not let it overlap the row-5 headers
            safeBottom = ws.Rows(5).Top - 3
            actualBottom = shp.Top + shp.Height

            If actualBottom > safeBottom Then
                extra = actualBottom - safeBottom
                bump = (extra / 4) + 1

                ws.Rows(1).rowHeight = ws.Rows(1).rowHeight + bump
                ws.Rows(2).rowHeight = ws.Rows(2).rowHeight + bump
                ws.Rows(3).rowHeight = ws.Rows(3).rowHeight + bump
                ws.Rows(4).rowHeight = ws.Rows(4).rowHeight + bump

                'Reset top after row-height change
                shp.Left = ws.Range("A1").Left + 3
                shp.Top = ws.Range("A1").Top + 3
            End If

            Exit For
        End If
    Next shp

    On Error GoTo 0
End Sub


'==============================================================================
' Glass section filtering
'==============================================================================


'------------------------------------------------------------------------------
' Returns only glass sections containing rows matching the selected filters.
'------------------------------------------------------------------------------

Public Function GetDeliveryListSectionsForPrintKind(ByVal ws As Worksheet, ByVal firstDataRow As Long, ByVal lastRealRow As Long, _
                                                     ByVal orderCol As Long, ByVal itemCol As Long, _
                                                     ByVal destinationMode As String, ByVal printKind As String) As Collection
    Dim sections As Collection
    Dim currentTitle As String
    Dim currentStart As Long
    Dim r As Long

    Set sections = New Collection
    currentTitle = vbNullString
    currentStart = 0

    For r = firstDataRow To lastRealRow
        If IsSectionHeaderRowTemplate(ws, r, orderCol, itemCol) Then
            If currentStart > 0 Then
                If SectionContainsPrintableRowsTemplate(ws, currentStart, r - 1, orderCol, itemCol, destinationMode, printKind) Then
                    sections.Add Array(currentTitle, currentStart, r - 1)
                End If
            End If

            currentTitle = Trim$(CStr(ws.Cells(r, 1).Value))
            currentStart = r
        End If
    Next r

    If currentStart > 0 Then
        If SectionContainsPrintableRowsTemplate(ws, currentStart, lastRealRow, orderCol, itemCol, destinationMode, printKind) Then
            sections.Add Array(currentTitle, currentStart, lastRealRow)
        End If
    End If

    Set GetDeliveryListSectionsForPrintKind = sections
End Function


'------------------------------------------------------------------------------
' Checks whether a glass section has at least one matching delivery line.
'------------------------------------------------------------------------------

Private Function SectionContainsPrintableRowsTemplate(ByVal ws As Worksheet, ByVal startRow As Long, ByVal endRow As Long, _
                                                      ByVal orderCol As Long, ByVal itemCol As Long, _
                                                      ByVal destinationMode As String, ByVal printKind As String) As Boolean
    Dim r As Long

    For r = startRow To endRow
        If IsRealDeliveryLineTemplate(ws, r, orderCol, itemCol) Then
            If DoesPrintModeMatchRowTemplate(ws, r, destinationMode, printKind) Then
                SectionContainsPrintableRowsTemplate = True
                Exit Function
            End If
        End If
    Next r
End Function


'------------------------------------------------------------------------------
' Checks whether a section is included by the selected glass filter.
'------------------------------------------------------------------------------

Private Function IsGlassSectionSelectedTemplate(ByVal sectionTitle As String, ByVal selectedGlassKeys As String) As Boolean
    If UCase$(Trim$(selectedGlassKeys)) = "ALL" Then
        IsGlassSectionSelectedTemplate = True
    Else
        IsGlassSectionSelectedTemplate = TokenListContainsTemplate(selectedGlassKeys, NormalizeSectionKey(sectionTitle))
    End If
End Function


'------------------------------------------------------------------------------
' Builds the Job Nr. display text used on remake print/export rows.
'------------------------------------------------------------------------------

Private Function GetRemakeJobDisplayTextTemplate(ByVal ws As Worksheet, ByVal rowNum As Long) As String
    Dim c As Long
    Dim part As String
    Dim txt As String

    For c = 1 To 4
        part = Trim$(CStr(ws.Cells(rowNum, c).Value))
        If Len(part) > 0 Then
            If Len(txt) > 0 Then txt = txt & " "
            txt = txt & part
        End If
    Next c

    GetRemakeJobDisplayTextTemplate = txt
End Function


'------------------------------------------------------------------------------
' Copies formatting from a remake template row to an output row.
'------------------------------------------------------------------------------

Private Sub ApplyRemakeTemplateRowFormat(ByVal ws As Worksheet, ByVal templateRow As Long, ByVal destRow As Long)
    ws.Rows(templateRow).Copy
    ws.Rows(destRow).PasteSpecial xlPasteFormats
    Application.CutCopyMode = False
    ws.Rows(destRow).rowHeight = ws.Rows(templateRow).rowHeight
    ws.Range("A" & destRow & ":M" & destRow).ClearContents
End Sub


'------------------------------------------------------------------------------
' Writes a remake section header into the preview/export sheet.
'------------------------------------------------------------------------------

Private Sub WriteRemakeSectionHeaderTemplate(ByVal ws As Worksheet, ByVal destRow As Long, ByVal sectionTitle As String)
    ApplyRemakeTemplateRowFormat ws, GetRemakePrintSectionTemplateRowTemplate(ws), destRow
    ws.Cells(destRow, 1).Value = sectionTitle
End Sub


'------------------------------------------------------------------------------
' Writes a remake spacer row into the preview/export sheet.
'------------------------------------------------------------------------------

Private Sub WriteRemakeBlankSpacerTemplate(ByVal ws As Worksheet, ByVal destRow As Long)
    ApplyRemakeTemplateRowFormat ws, GetRemakePrintSpacerTemplateRowTemplate(ws), destRow
End Sub


'------------------------------------------------------------------------------
' Maps one source delivery row into the remake print/export layout.
'------------------------------------------------------------------------------

Private Sub WriteRemakeLineTemplate(ByVal srcWs As Worksheet, ByVal srcRow As Long, ByVal destWs As Worksheet, _
                                    ByVal destRow As Long, ByVal orderCol As Long, ByVal itemCol As Long, _
                                    ByVal qtyCol As Long, ByVal dimCol As Long)

    ApplyRemakeTemplateRowFormat destWs, GetRemakePrintLineTemplateRowTemplate(destWs), destRow

    On Error Resume Next
    destWs.Range("A" & destRow & ":M" & destRow).UnMerge
    On Error GoTo 0

    destWs.Range("A" & destRow & ":M" & destRow).ClearContents

    'Reference remake layout:
    'A = Job Nr.
    'C = Order
    'E = Item
    'G = Qty.
    'I = Dimensions
    'K = Check Off

    destWs.Cells(destRow, 1).Value = GetRemakeJobDisplayTextTemplate(srcWs, srcRow)
    destWs.Cells(destRow, 3).Value = srcWs.Cells(srcRow, orderCol).Value

    If IsNumeric(srcWs.Cells(srcRow, itemCol).Value) Then
        destWs.Cells(destRow, 5).Value = Format$(CLng(Val(srcWs.Cells(srcRow, itemCol).Value)), "000")
    Else
        destWs.Cells(destRow, 5).Value = srcWs.Cells(srcRow, itemCol).Value
    End If

    destWs.Cells(destRow, 7).Value = srcWs.Cells(srcRow, qtyCol).Value
    destWs.Cells(destRow, 9).Value = srcWs.Cells(srcRow, dimCol).Value

    'No customer text on remake print
    destWs.Cells(destRow, 11).Value = ChrW(&H25A1)   'empty check box
    destWs.Cells(destRow, 11).HorizontalAlignment = xlCenter
    destWs.Cells(destRow, 11).VerticalAlignment = xlCenter
    destWs.Cells(destRow, 11).Font.Name = "Segoe UI Symbol"
    destWs.Cells(destRow, 11).Font.Size = 20
    destWs.Cells(destRow, 11).Font.Bold = False

    destWs.Cells(destRow, 1).HorizontalAlignment = xlLeft
    destWs.Cells(destRow, 1).VerticalAlignment = xlCenter

    destWs.Cells(destRow, 3).HorizontalAlignment = xlCenter
    destWs.Cells(destRow, 3).VerticalAlignment = xlCenter

    destWs.Cells(destRow, 5).HorizontalAlignment = xlCenter
    destWs.Cells(destRow, 5).VerticalAlignment = xlCenter

    destWs.Cells(destRow, 7).HorizontalAlignment = xlCenter
    destWs.Cells(destRow, 7).VerticalAlignment = xlCenter

    destWs.Cells(destRow, 9).HorizontalAlignment = xlCenter
    destWs.Cells(destRow, 9).VerticalAlignment = xlCenter
End Sub


'------------------------------------------------------------------------------
' Applies page setup for remake print/export sheets.
'------------------------------------------------------------------------------

Private Sub ConfigureRemakePrintPageTemplate(ByVal ws As Worksheet, ByVal lastPrintRow As Long)
    With ws.PageSetup
        .PrintArea = ws.Range("A1:K" & lastPrintRow).Address
        .Orientation = xlLandscape
        .PaperSize = xlPaperLetter
        .Zoom = False
        .FitToPagesWide = 1
        .FitToPagesTall = False
        .CenterHorizontally = True
        .CenterVertically = False
        .LeftMargin = Application.InchesToPoints(0.35)
        .RightMargin = Application.InchesToPoints(0.35)
        .TopMargin = Application.InchesToPoints(0.4)
        .BottomMargin = Application.InchesToPoints(0.4)
        .HeaderMargin = Application.InchesToPoints(0.2)
        .FooterMargin = Application.InchesToPoints(0.2)
        .CenterFooter = "Page &P of &N"
    End With
End Sub


'==============================================================================
' Remake print/preview builder
'==============================================================================


'------------------------------------------------------------------------------
' Builds the temporary remake preview sheet, then previews or prints it.
'------------------------------------------------------------------------------
Public Sub BuildAndPreviewRemakePrintFromTemplate(ByVal srcWs As Worksheet, _
                                                   ByVal sectionStartRow As Long, ByVal sectionEndRow As Long, _
                                                   ByVal firstDataRow As Long, ByVal lastRealRow As Long, _
                                                   ByVal orderCol As Long, ByVal itemCol As Long, _
                                                   ByVal destinationMode As String, _
                                                   ByVal selectedGlassKeys As String, _
                                                   Optional ByVal printKind As String = "REMAKES", _
                                                   Optional ByVal selectedAction As String = "PREVIEW", _
                                                   Optional ByVal selectedCopies As Long = 1)
    Dim templateWs As Worksheet
    Dim previewWs As Worksheet
    Dim prevSheet As Worksheet
    Dim qtyHdr As Range
    Dim dimHdr As Range
    Dim qtyCol As Long
    Dim dimCol As Long
    Dim scanStart As Long
    Dim scanEnd As Long
    Dim destRow As Long
    Dim r As Long
    Dim listDate As Date
    Dim currentSectionTitle As String
    Dim printedAnyInSection As Boolean
    Dim printedAnyRows As Boolean
    Dim oldDisplayAlerts As Boolean
    Dim oldScreenUpdating As Boolean
    Dim bodyLastRow As Long
    Dim bodyStartRow As Long

    On Error GoTo ErrHandler

    oldDisplayAlerts = Application.DisplayAlerts
    oldScreenUpdating = Application.ScreenUpdating

    If srcWs Is Nothing Then Exit Sub

    Set qtyHdr = FindHeaderCellTemplate(srcWs, Array("Qty.", "Qty"))
    Set dimHdr = FindHeaderCellTemplate(srcWs, Array("Dimensions"))

    If qtyHdr Is Nothing Or dimHdr Is Nothing Then
        MsgBox "Could not find Qty. / Dimensions headers needed for remake printing.", vbExclamation, "Print Remakes"
        Exit Sub
    End If

    qtyCol = qtyHdr.Column
    dimCol = dimHdr.Column

    Application.DisplayAlerts = False
    Application.ScreenUpdating = False

    Set prevSheet = ActiveSheet
    Set templateWs = ThisWorkbook.Worksheets(REMAKE_PRINT_TEMPLATE_SHEET)

    DeleteSheetIfExists ThisWorkbook, REMAKE_PRINT_PREVIEW_SHEET

    templateWs.Visible = xlSheetVisible
    templateWs.Copy After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count)
    Set previewWs = ActiveSheet
    previewWs.Name = REMAKE_PRINT_PREVIEW_SHEET
    templateWs.Visible = xlSheetVeryHidden

    On Error Resume Next
    previewWs.Unprotect Password:=""
    On Error GoTo ErrHandler

    listDate = GetDeliveryListDateForFileName(srcWs)
    If listDate > 0 Then
        previewWs.Range("A2").Value = REMAKE_TITLE_PREFIX & Format$(listDate, "m/d/yyyy")
    End If

    ApplyRemakePrintColumnHeadersTemplate previewWs

    bodyStartRow = GetRemakePrintBodyStartRowTemplate(previewWs)
    bodyLastRow = GetLastUsedRowTemplate(previewWs)
    If bodyLastRow < bodyStartRow Then bodyLastRow = bodyStartRow

    previewWs.Range("A" & bodyStartRow & ":M" & bodyLastRow).ClearContents

    If sectionStartRow > 0 And sectionEndRow > 0 Then
        scanStart = sectionStartRow
        scanEnd = sectionEndRow
    Else
        scanStart = firstDataRow
        scanEnd = lastRealRow
    End If

    destRow = bodyStartRow
    currentSectionTitle = vbNullString
    printedAnyInSection = False
    printedAnyRows = False

    For r = scanStart To scanEnd
        If IsSectionHeaderRowTemplate(srcWs, r, orderCol, itemCol) Then
            currentSectionTitle = Trim$(CStr(srcWs.Cells(r, 1).Value))
            printedAnyInSection = False

        ElseIf IsRealDeliveryLineTemplate(srcWs, r, orderCol, itemCol) Then
            If DoesPrintModeMatchRowTemplate(srcWs, r, destinationMode, printKind) And _
               IsGlassSectionSelectedTemplate(currentSectionTitle, selectedGlassKeys) Then

                If Not printedAnyInSection And Len(currentSectionTitle) > 0 Then
                    WriteRemakeSectionHeaderTemplate previewWs, destRow, currentSectionTitle
                    WriteRemakeBlankSpacerTemplate previewWs, destRow + 1
                    destRow = destRow + 2
                    printedAnyInSection = True
                End If

                WriteRemakeLineTemplate srcWs, r, previewWs, destRow, orderCol, itemCol, qtyCol, dimCol
                destRow = destRow + 1
                printedAnyRows = True
            End If
        End If
    Next r

    If Not printedAnyRows Then
        MsgBox "There are no remake rows to preview for " & GetDestinationLabel(destinationMode) & ".", _
               vbInformation, "Print Remakes"
        GoTo SafeExit
    End If

    ConfigureRemakePrintPageTemplate previewWs, destRow - 1

    previewWs.Activate
    previewWs.Range("A1").Select

    If UCase$(selectedAction) = "PRINT" Then
        If selectedCopies < 1 Then selectedCopies = 1
        previewWs.PrintOut Copies:=selectedCopies
    Else
        previewWs.PrintPreview
    End If

SafeExit:
    On Error Resume Next
    If Not prevSheet Is Nothing Then prevSheet.Activate
    If Not previewWs Is Nothing Then previewWs.Delete
    If Not templateWs Is Nothing Then templateWs.Visible = xlSheetVeryHidden
    Application.DisplayAlerts = oldDisplayAlerts
    Application.ScreenUpdating = oldScreenUpdating
    On Error GoTo 0
    Exit Sub

ErrHandler:
    MsgBox "BuildAndPreviewRemakePrintFromTemplate error " & Err.Number & ":" & vbCrLf & Err.Description, _
           vbCritical, "Print Remakes Error"
    Resume SafeExit
End Sub
'==============================================================================
' Shared text/key utilities
'==============================================================================


'------------------------------------------------------------------------------
' Normalizes worksheet text by removing nonbreaking spaces and extra whitespace.
'------------------------------------------------------------------------------

Private Function CleanLayoutTextTemplate(ByVal v As Variant) As String
    Dim s As String

    If IsError(v) Then Exit Function

    s = CStr(v)
    s = Replace$(s, Chr$(160), " ")
    s = Application.WorksheetFunction.Clean(s)
    s = Application.WorksheetFunction.Trim(s)

    CleanLayoutTextTemplate = Trim$(s)
End Function


'------------------------------------------------------------------------------
' Normalizes glass section names for dictionary/token comparisons.
'------------------------------------------------------------------------------

Private Function NormalizeSectionKey(ByVal s As String) As String
    NormalizeSectionKey = UCase$(Trim$(s))
End Function


'------------------------------------------------------------------------------
' Detects glass section header rows in the imported delivery list.
'------------------------------------------------------------------------------

Private Function IsSectionHeaderRowTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, ByVal orderCol As Long, ByVal itemCol As Long) As Boolean
    Dim leftText As String
    Dim ordTxt As String
    Dim itemTxt As String

    leftText = CleanLayoutTextTemplate(ws.Cells(rowNum, 1).Value)
    ordTxt = CleanLayoutTextTemplate(ws.Cells(rowNum, orderCol).Value)
    itemTxt = CleanLayoutTextTemplate(ws.Cells(rowNum, itemCol).Value)

    IsSectionHeaderRowTemplate = (Len(leftText) > 0 And Len(ordTxt) = 0 And Len(itemTxt) = 0)
End Function


'------------------------------------------------------------------------------
' Safely deletes a temporary sheet if it exists.
'------------------------------------------------------------------------------

Private Sub DeleteSheetIfExists(ByVal wb As Workbook, ByVal sheetName As String)
    Dim ws As Worksheet
    Dim safeWs As Worksheet
    Dim oldAlerts As Boolean
    Dim oldEvents As Boolean
    Dim oldScreen As Boolean

    On Error Resume Next
    Set ws = wb.Worksheets(sheetName)
    On Error GoTo 0

    If ws Is Nothing Then Exit Sub
    If wb.Worksheets.Count <= 1 Then Exit Sub

    oldAlerts = Application.DisplayAlerts
    oldEvents = Application.EnableEvents
    oldScreen = Application.ScreenUpdating

    Application.DisplayAlerts = False
    Application.EnableEvents = False
    Application.ScreenUpdating = False

    On Error Resume Next

    'Make sure a different visible sheet is active before deleting
    For Each safeWs In wb.Worksheets
        If safeWs.Name <> ws.Name Then
            safeWs.Visible = xlSheetVisible
            safeWs.Activate
            Exit For
        End If
    Next safeWs

    ws.Unprotect Password:=""
    ws.Visible = xlSheetVisible
    ws.Delete

    Application.DisplayAlerts = oldAlerts
    Application.EnableEvents = oldEvents
    Application.ScreenUpdating = oldScreen
    On Error GoTo 0
End Sub


'------------------------------------------------------------------------------
' Returns the last used row on a worksheet.
'------------------------------------------------------------------------------

Private Function GetLastUsedRowTemplate(ByVal ws As Worksheet) As Long
    Dim f As Range
    Set f = ws.Cells.Find(What:="*", LookIn:=xlFormulas, SearchOrder:=xlByRows, SearchDirection:=xlPrevious)

    If f Is Nothing Then
        GetLastUsedRowTemplate = 0
    Else
        GetLastUsedRowTemplate = f.Row
    End If
End Function


'------------------------------------------------------------------------------
' Adds a unique token to a pipe-delimited token list.
'------------------------------------------------------------------------------

Private Sub AddTokenTemplate(ByRef tokenList As String, ByVal token As String)
    If Len(token) = 0 Then Exit Sub

    If Not TokenListContainsTemplate(tokenList, token) Then
        If Len(tokenList) > 0 Then
            tokenList = tokenList & "|"
        End If
        tokenList = tokenList & UCase$(token)
    End If
End Sub


'------------------------------------------------------------------------------
' Checks whether a pipe-delimited token list contains a token.
'------------------------------------------------------------------------------

Private Function TokenListContainsTemplate(ByVal tokenList As String, ByVal token As String) As Boolean
    Dim parts() As String
    Dim i As Long

    token = UCase$(Trim$(token))
    tokenList = UCase$(Trim$(tokenList))

    If tokenList = "ALL" Then
        TokenListContainsTemplate = True
        Exit Function
    End If

    If Len(tokenList) = 0 Then Exit Function

    parts = Split(tokenList, "|")
    For i = LBound(parts) To UBound(parts)
        If Trim$(parts(i)) = token Then
            TokenListContainsTemplate = True
            Exit Function
        End If
    Next i
End Function


'==============================================================================
' Delivery-list print/preview builder
'==============================================================================


'------------------------------------------------------------------------------
' Determines whether route columns should stay visible for printing.
'------------------------------------------------------------------------------

Private Function DestinationNeedsRouteColumnTemplate(ByVal destinationMode As String) As Boolean
    DestinationNeedsRouteColumnTemplate = _
        TokenListContainsTemplate(destinationMode, "ALL") Or _
        TokenListContainsTemplate(destinationMode, "CPU")
End Function


'------------------------------------------------------------------------------
' Builds a readable destination label for messages.
'------------------------------------------------------------------------------

Private Function GetDestinationLabel(ByVal destinationMode As String) As String
    Dim txt As String

    If UCase$(Trim$(destinationMode)) = "ALL" Then
        GetDestinationLabel = "all destinations"
        Exit Function
    End If

    If TokenListContainsTemplate(destinationMode, "STANDARD") Then
        txt = "Indian Trail"
    End If

    If TokenListContainsTemplate(destinationMode, "GREENVILLE") Then
        If Len(txt) > 0 Then txt = txt & ", "
        txt = txt & "Greenville"
    End If

    If TokenListContainsTemplate(destinationMode, "CPU") Then
        If Len(txt) > 0 Then txt = txt & ", "
        txt = txt & "Customer Pickup"
    End If

    If Len(txt) = 0 Then txt = "selected destination(s)"
    GetDestinationLabel = txt
End Function


'------------------------------------------------------------------------------
' Applies destination filtering to one row.
'------------------------------------------------------------------------------

Private Function DoesDestinationMatchRowTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, ByVal destinationMode As String) As Boolean
    If UCase$(Trim$(destinationMode)) = "ALL" Then
        DoesDestinationMatchRowTemplate = True
        Exit Function
    End If

    If TokenListContainsTemplate(destinationMode, "STANDARD") Then
        If (Not IsGreenvilleRowTemplate(ws, rowNum) And Not IsCPURowTemplate(ws, rowNum)) Then
            DoesDestinationMatchRowTemplate = True
            Exit Function
        End If
    End If

    If TokenListContainsTemplate(destinationMode, "GREENVILLE") Then
        If IsGreenvilleRowTemplate(ws, rowNum) Then
            DoesDestinationMatchRowTemplate = True
            Exit Function
        End If
    End If

    If TokenListContainsTemplate(destinationMode, "CPU") Then
        If IsCPURowTemplate(ws, rowNum) Then
            DoesDestinationMatchRowTemplate = True
            Exit Function
        End If
    End If

    DoesDestinationMatchRowTemplate = False
End Function


'------------------------------------------------------------------------------
' Builds the temporary delivery-list preview sheet, then previews or prints it.
'------------------------------------------------------------------------------
Public Sub BuildAndPreviewDeliveryListPrint(ByVal srcWs As Worksheet, _
                                             ByVal sectionStartRow As Long, ByVal sectionEndRow As Long, _
                                             ByVal firstDataRow As Long, ByVal lastRealRow As Long, _
                                             ByVal orderCol As Long, ByVal itemCol As Long, _
                                             ByVal destinationMode As String, _
                                             ByVal selectedGlassKeys As String, _
                                             Optional ByVal printKind As String = "ORDERS", _
                                             Optional ByVal selectedAction As String = "PREVIEW", _
                                             Optional ByVal selectedCopies As Long = 1)
    Dim baseWs As Worksheet
    Dim previewWs As Worksheet
    Dim prevSheet As Worksheet
    Dim oldDisplayAlerts As Boolean
    Dim oldScreenUpdating As Boolean
    Dim destRow As Long
    Dim r As Long
    Dim scanStart As Long
    Dim scanEnd As Long
    Dim currentSectionTitle As String
    Dim currentHeaderRow As Long
    Dim printedAnyInSection As Boolean
    Dim printedAnyRows As Boolean
    Dim baseLastRow As Long
    Dim previewLastRow As Long
    Dim breakRows As Collection
    Dim i As Long
    Dim buildLastCol As String
    Dim printLastCol As String

    On Error GoTo ErrHandler

    oldDisplayAlerts = Application.DisplayAlerts
    oldScreenUpdating = Application.ScreenUpdating

    If srcWs Is Nothing Then Exit Sub

    Application.DisplayAlerts = False
    Application.ScreenUpdating = False

    Set prevSheet = ActiveSheet

    buildLastCol = GetPrintLastColForDestination(destinationMode)
    printLastCol = buildLastCol

    If Not DestinationNeedsRouteColumnTemplate(destinationMode) Then
        printLastCol = "J"
    End If

    DeleteSheetIfExists ThisWorkbook, "__PRINT_BASE__"
    DeleteSheetIfExists ThisWorkbook, "__PRINT_PREVIEW__"

    Set baseWs = ThisWorkbook.Worksheets.Add(After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
    baseWs.Name = "__PRINT_BASE__"

    srcWs.Range("A:" & buildLastCol).Copy
    baseWs.Range("A1").PasteSpecial xlPasteColumnWidths
    Application.CutCopyMode = False

    srcWs.Range("A1:" & buildLastCol & "5").Copy
    baseWs.Range("A1").PasteSpecial xlPasteAll
    Application.CutCopyMode = False

    For i = 1 To 5
        baseWs.Rows(i).rowHeight = srcWs.Rows(i).rowHeight
    Next i

    ApplyDestinationAwareDeliveryTitleTemplate baseWs, srcWs, destinationMode
    CopyDeliveryListLogoToSheetTemplate srcWs, baseWs
    RepositionPrintPreviewLogoTemplate baseWs

    If sectionStartRow > 0 And sectionEndRow > 0 Then
        scanStart = sectionStartRow
        scanEnd = sectionEndRow
    Else
        scanStart = firstDataRow
        scanEnd = lastRealRow
    End If

    destRow = 6
    currentSectionTitle = vbNullString
    currentHeaderRow = 0
    printedAnyInSection = False
    printedAnyRows = False

    For r = scanStart To scanEnd
        If IsSectionHeaderRowTemplate(srcWs, r, orderCol, itemCol) Then
            currentSectionTitle = Trim$(CStr(srcWs.Cells(r, 1).Value))
            currentHeaderRow = r
            printedAnyInSection = False

        ElseIf IsRealDeliveryLineTemplate(srcWs, r, orderCol, itemCol) Then
            If DoesPrintModeMatchRowTemplate(srcWs, r, destinationMode, printKind) And _
               IsGlassSectionSelectedTemplate(currentSectionTitle, selectedGlassKeys) Then

                If Not printedAnyInSection And currentHeaderRow > 0 Then
                    CopyPrintableRowForPrint srcWs, currentHeaderRow, baseWs, destRow, currentSectionTitle, "HEADER", buildLastCol, destinationMode
                    destRow = destRow + 1
                    printedAnyInSection = True
                End If

                CopyPrintableRowForPrint srcWs, r, baseWs, destRow, currentSectionTitle, "LINE", buildLastCol, destinationMode
                destRow = destRow + 1
                printedAnyRows = True
            End If
        End If
    Next r

    If Not printedAnyRows Then
        MsgBox "There are no rows to preview for " & GetDestinationLabel(destinationMode) & ".", _
               vbInformation, "Print Delivery List"
        GoTo SafeExit
    End If

    baseLastRow = destRow - 1
    ConfigureDeliveryListPrintPage baseWs, baseLastRow, printLastCol

    Set breakRows = GetPrintBreakRows(baseWs)

    Set previewWs = ThisWorkbook.Worksheets.Add(After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
    previewWs.Name = "__PRINT_PREVIEW__"

    baseWs.Range("A:" & buildLastCol).Copy
    previewWs.Range("A1").PasteSpecial xlPasteColumnWidths
    Application.CutCopyMode = False

    baseWs.Range("A1:" & buildLastCol & baseLastRow).Copy
    previewWs.Range("A1").PasteSpecial xlPasteAll
    Application.CutCopyMode = False

    ApplyDestinationAwareDeliveryTitleTemplate previewWs, srcWs, destinationMode
    CopyDeliveryListLogoToSheetTemplate srcWs, previewWs
    RepositionPrintPreviewLogoTemplate previewWs

    previewLastRow = baseLastRow
    ApplyContinuationHeadersFromBaseBreaks baseWs, previewWs, breakRows, previewLastRow, baseLastRow
    ConfigureDeliveryListPrintPage previewWs, previewLastRow, printLastCol

    On Error Resume Next
    baseWs.Columns(PRINT_HELPER_SECTION_COL).Hidden = True
    baseWs.Columns(PRINT_HELPER_ROWTYPE_COL).Hidden = True
    previewWs.Columns(PRINT_HELPER_SECTION_COL).Hidden = True
    previewWs.Columns(PRINT_HELPER_ROWTYPE_COL).Hidden = True
    On Error GoTo ErrHandler

    previewWs.Activate
    previewWs.Range("A1").Select

    If UCase$(selectedAction) = "PRINT" Then
        If selectedCopies < 1 Then selectedCopies = 1
        previewWs.PrintOut Copies:=selectedCopies
    Else
        previewWs.PrintPreview
    End If

SafeExit:
    On Error Resume Next
    If Not prevSheet Is Nothing Then prevSheet.Activate
    If Not previewWs Is Nothing Then previewWs.Delete
    If Not baseWs Is Nothing Then baseWs.Delete
    Application.DisplayAlerts = oldDisplayAlerts
    Application.ScreenUpdating = oldScreenUpdating
    On Error GoTo 0
    Exit Sub

ErrHandler:
    MsgBox "BuildAndPreviewDeliveryListPrint error " & Err.Number & ":" & vbCrLf & Err.Description, _
           vbCritical, "Print Delivery List Error"
    Resume SafeExit
End Sub
'------------------------------------------------------------------------------
' Collects Excel-calculated horizontal page break rows.
'------------------------------------------------------------------------------

Private Function GetPrintBreakRows(ByVal ws As Worksheet) As Collection
    Dim breaks As New Collection
    Dim i As Long

    If ws Is Nothing Then
        Set GetPrintBreakRows = breaks
        Exit Function
    End If

    ws.Activate
    DoEvents

    On Error Resume Next
    ws.DisplayPageBreaks = True
    On Error GoTo 0

    For i = 1 To ws.HPageBreaks.Count
        breaks.Add ws.HPageBreaks(i).Location.Row
    Next i

    On Error Resume Next
    ws.DisplayPageBreaks = False
    On Error GoTo 0

    Set GetPrintBreakRows = breaks
End Function


'------------------------------------------------------------------------------
' Adds repeated glass-section continuation headers after page breaks.
'------------------------------------------------------------------------------

Private Sub ApplyContinuationHeadersFromBaseBreaks(ByVal baseWs As Worksheet, ByVal previewWs As Worksheet, _
                                                   ByVal breakRows As Collection, ByRef previewLastRow As Long, _
                                                   ByVal baseLastRow As Long)
    Dim i As Long
    Dim breakRow As Long
    Dim targetRow As Long
    Dim sectionTitle As String
    Dim templateHeaderRow As Long

    If baseWs Is Nothing Or previewWs Is Nothing Then Exit Sub
    If breakRows Is Nothing Then Exit Sub
    If breakRows.Count = 0 Then Exit Sub

    On Error Resume Next
    previewWs.ResetAllPageBreaks
    On Error GoTo 0

    For i = breakRows.Count To 1 Step -1
        breakRow = CLng(breakRows(i))

        If breakRow > 6 And breakRow <= baseLastRow Then
            targetRow = FindFirstHelperLineAtOrBelow(baseWs, breakRow, baseLastRow)

            If targetRow > 0 Then
                sectionTitle = Trim$(CStr(baseWs.Cells(targetRow, PRINT_HELPER_SECTION_COL).Value))

                If Len(sectionTitle) > 0 Then
                    templateHeaderRow = FindPrintHeaderTemplateAbove(baseWs, targetRow - 1, sectionTitle)

                    If templateHeaderRow > 0 Then
                        previewWs.Rows(targetRow).Insert Shift:=xlDown, CopyOrigin:=xlFormatFromLeftOrAbove

                        baseWs.Range("A" & templateHeaderRow & ":O" & templateHeaderRow).Copy
                        previewWs.Range("A" & targetRow).PasteSpecial xlPasteAll
                        Application.CutCopyMode = False

                        previewWs.Rows(targetRow).rowHeight = baseWs.Rows(templateHeaderRow).rowHeight
                        previewWs.Cells(targetRow, 1).Value = BuildContinuationHeaderText(sectionTitle)
                        previewWs.Cells(targetRow, PRINT_HELPER_SECTION_COL).Value = sectionTitle
                        previewWs.Cells(targetRow, PRINT_HELPER_ROWTYPE_COL).Value = "CONT"

                        On Error Resume Next
                        previewWs.HPageBreaks.Add Before:=previewWs.Rows(targetRow)
                        On Error GoTo 0

                        previewLastRow = previewLastRow + 1
                    End If
                End If
            End If
        End If
    Next i
End Sub


'------------------------------------------------------------------------------
' Copies and cleans one row into a print/export sheet.
'------------------------------------------------------------------------------

Private Sub CopyPrintableRowForPrint(ByVal srcWs As Worksheet, ByVal srcRow As Long, ByVal destWs As Worksheet, _
                                     ByVal destRow As Long, ByVal sectionTitle As String, _
                                     ByVal rowType As String, ByVal visibleLastCol As String, _
                                     ByVal destinationMode As String)

    srcWs.Range("A" & srcRow & ":" & visibleLastCol & srcRow).Copy
    destWs.Range("A" & destRow).PasteSpecial xlPasteAll
    Application.CutCopyMode = False

    destWs.Rows(destRow).rowHeight = srcWs.Rows(srcRow).rowHeight
    destWs.Cells(destRow, PRINT_HELPER_SECTION_COL).Value = sectionTitle
    destWs.Cells(destRow, PRINT_HELPER_ROWTYPE_COL).Value = UCase$(rowType)

    'Plain print copy only: remove fills, font colors, and borders
    With destWs.Range("A" & destRow & ":" & visibleLastCol & destRow)
        .Interior.Pattern = xlNone
        .Font.ColorIndex = xlAutomatic
        .Font.Italic = False
        .Font.Underline = xlUnderlineStyleNone
        .Borders.lineStyle = xlNone
    End With

    'Keep section headers readable
    If UCase$(rowType) = "HEADER" Or UCase$(rowType) = "CONT" Then
        destWs.Range("A" & destRow & ":" & visibleLastCol & destRow).Font.Bold = True
    Else
        destWs.Range("A" & destRow & ":" & visibleLastCol & destRow).Font.Bold = False
    End If
End Sub


'------------------------------------------------------------------------------
' Applies page setup for normal delivery-list printing.
'------------------------------------------------------------------------------

Private Sub ConfigureDeliveryListPrintPage(ByVal ws As Worksheet, ByVal lastPrintRow As Long, ByVal lastPrintCol As String)
    With ws.PageSetup
        .PrintArea = ws.Range("A1:" & lastPrintCol & lastPrintRow).Address
        .Orientation = xlPortrait
        .PaperSize = xlPaperLetter
        .Zoom = False
        .FitToPagesWide = 1
        .FitToPagesTall = False
        .CenterHorizontally = True
        .CenterVertically = False
        .LeftMargin = Application.InchesToPoints(0.2)
        .RightMargin = Application.InchesToPoints(0.2)
        .TopMargin = Application.InchesToPoints(0.35)
        .BottomMargin = Application.InchesToPoints(0.35)
        .HeaderMargin = Application.InchesToPoints(0.15)
        .FooterMargin = Application.InchesToPoints(0.15)
        .PrintTitleRows = ""
        .CenterFooter = "Page &P of &N"
    End With
End Sub


'------------------------------------------------------------------------------
' Returns the last delivery-list column to include in print/export output.
'------------------------------------------------------------------------------

Private Function GetPrintLastColForDestination(ByVal destinationMode As String) As String
    GetPrintLastColForDestination = "L"
End Function


'------------------------------------------------------------------------------
' Finds the nearest section header above a row in the print base sheet.
'------------------------------------------------------------------------------

Private Function FindPrintHeaderTemplateAbove(ByVal ws As Worksheet, ByVal startRow As Long, ByVal sectionTitle As String) As Long
    Dim r As Long
    Dim rowType As String
    Dim rowSection As String

    For r = startRow To 6 Step -1
        rowType = UCase$(Trim$(CStr(ws.Cells(r, PRINT_HELPER_ROWTYPE_COL).Value)))
        rowSection = Trim$(CStr(ws.Cells(r, PRINT_HELPER_SECTION_COL).Value))

        If (rowType = "HEADER" Or rowType = "CONT") And _
           StrComp(rowSection, sectionTitle, vbTextCompare) = 0 Then
            FindPrintHeaderTemplateAbove = r
            Exit Function
        End If
    Next r
End Function


'------------------------------------------------------------------------------
' Adds the (cont.) suffix to continued section headers.
'------------------------------------------------------------------------------

Private Function BuildContinuationHeaderText(ByVal headerText As String) As String
    headerText = Trim$(headerText)

    If Len(headerText) = 0 Then
        BuildContinuationHeaderText = "(cont.)"
    ElseIf InStr(1, headerText, "(cont.)", vbTextCompare) > 0 Then
        BuildContinuationHeaderText = headerText
    Else
        BuildContinuationHeaderText = headerText & " (cont.)"
    End If
End Function


'------------------------------------------------------------------------------
' Finds the first real printed line at or below a page break.
'------------------------------------------------------------------------------

Private Function FindFirstHelperLineAtOrBelow(ByVal ws As Worksheet, ByVal startRow As Long, ByVal lastRow As Long) As Long
    Dim r As Long
    Dim rowType As String

    For r = startRow To lastRow
        rowType = UCase$(Trim$(CStr(ws.Cells(r, PRINT_HELPER_ROWTYPE_COL).Value)))
        If rowType = "LINE" Then
            FindFirstHelperLineAtOrBelow = r
            Exit Function
        End If
    Next r
End Function


'==============================================================================
' Export workbook helpers
'==============================================================================


'------------------------------------------------------------------------------
' Normalizes the user-selected .xlsx export file path.
'------------------------------------------------------------------------------

Private Function NormalizeXlsxSavePathTemplate(ByVal rawPath As String) As String
    rawPath = Trim$(rawPath)

    If Len(rawPath) = 0 Then Exit Function
    If UCase$(rawPath) = "FALSE" Then Exit Function

    If LCase$(Right$(rawPath, 5)) <> ".xlsx" Then
        rawPath = rawPath & ".xlsx"
    End If

    NormalizeXlsxSavePathTemplate = rawPath
End Function


'------------------------------------------------------------------------------
' Shows the Save As dialog for exported .xlsx workbooks.
'------------------------------------------------------------------------------

Private Function PromptForXlsxSavePathTemplate(ByVal suggestedName As String, _
                                               ByVal dialogTitle As String) As String
    Dim pickedPath As Variant

    On Error Resume Next
    Application.DisplayAlerts = True
    Application.ScreenUpdating = True
    ThisWorkbook.Activate
    AppActivate Application.Caption
    On Error GoTo 0

    DoEvents

    pickedPath = Application.GetSaveAsFilename( _
        InitialFileName:=suggestedName & ".xlsx", _
        FileFilter:="Excel Workbook (*.xlsx), *.xlsx", _
        Title:=dialogTitle)

    If VarType(pickedPath) = vbBoolean Then Exit Function

    PromptForXlsxSavePathTemplate = NormalizeXlsxSavePathTemplate(CStr(pickedPath))
End Function


'------------------------------------------------------------------------------
' Builds a default export workbook file name.
'------------------------------------------------------------------------------

Private Function BuildSuggestedExportFileNameTemplate(ByVal exportType As String, ByVal srcWs As Worksheet) As String
    Dim listDate As Date
    Dim dtText As String
    Dim baseName As String

    Select Case UCase$(exportType)
        Case "REMAKES"
            baseName = "RemakeList"
        Case Else
            baseName = "DeliveryList"
    End Select

    If Not srcWs Is Nothing Then
        listDate = GetDeliveryListDateForFileName(srcWs)
    End If

    If listDate > 0 Then
        dtText = Format$(listDate, "m.d.yy")
    Else
        dtText = vbNullString
    End If

    BuildSuggestedExportFileNameTemplate = CleanFileName(baseName & dtText)
End Function


'------------------------------------------------------------------------------
' Checks whether a worksheet name already exists in an export workbook.
'------------------------------------------------------------------------------

Private Function SheetExistsInWorkbookTemplate(ByVal wb As Workbook, ByVal sheetName As String) As Boolean
    Dim ws As Worksheet

    On Error Resume Next
    Set ws = wb.Worksheets(sheetName)
    On Error GoTo 0

    SheetExistsInWorkbookTemplate = Not ws Is Nothing
End Function


'------------------------------------------------------------------------------
' Converts section-name fractions into decimal text for safer sheet names.
'------------------------------------------------------------------------------

Private Function FractionTextToDecimalTemplate(ByVal s As String) As String
    Dim parts() As String
    Dim n As Double
    Dim d As Double

    s = Trim$(s)
    If InStr(1, s, "/", vbTextCompare) = 0 Then
        FractionTextToDecimalTemplate = s
        Exit Function
    End If

    parts = Split(s, "/")
    If UBound(parts) <> 1 Then
        FractionTextToDecimalTemplate = s
        Exit Function
    End If

    If Not IsNumeric(parts(0)) Or Not IsNumeric(parts(1)) Then
        FractionTextToDecimalTemplate = s
        Exit Function
    End If

    n = CDbl(parts(0))
    d = CDbl(parts(1))
    If d = 0 Then
        FractionTextToDecimalTemplate = s
        Exit Function
    End If

    FractionTextToDecimalTemplate = Trim$(Format$(n / d, "0.###"))
End Function


'------------------------------------------------------------------------------
' Converts fractions and quotes in export worksheet names.
'------------------------------------------------------------------------------

Private Function ConvertFractionsInExportSheetNameTemplate(ByVal rawName As String) As String
    Dim re As Object
    Dim matches As Object
    Dim m As Object
    Dim resultText As String
    Dim fractionText As String
    Dim decimalText As String

    resultText = rawName

    Set re = CreateObject("VBScript.RegExp")
    re.Global = True
    re.IgnoreCase = True
    re.Pattern = "(\d+/\d+)"

    If re.Test(resultText) Then
        Set matches = re.Execute(resultText)

        For Each m In matches
            fractionText = CStr(m.Value)
            decimalText = FractionTextToDecimalTemplate(fractionText)
            resultText = Replace$(resultText, fractionText, decimalText)
        Next m
    End If

    'Optional cleanup so tabs look cleaner
    resultText = Replace$(resultText, """", "")
    resultText = Replace$(resultText, "'", "")

    ConvertFractionsInExportSheetNameTemplate = resultText
End Function


'------------------------------------------------------------------------------
' Creates a valid, unique worksheet name for an exported glass section.
'------------------------------------------------------------------------------

Private Function BuildUniqueExportSheetNameTemplate(ByVal wb As Workbook, ByVal rawName As String) As String
    Dim baseName As String
    Dim tryName As String
    Dim suffix As String
    Dim i As Long

    baseName = ConvertFractionsInExportSheetNameTemplate(rawName)
    baseName = CleanSheetTabName(baseName)

    If Len(baseName) = 0 Then baseName = "Section"

    tryName = baseName
    i = 1

    Do While SheetExistsInWorkbookTemplate(wb, tryName)
        i = i + 1
        suffix = " (" & CStr(i) & ")"

        If Len(baseName) + Len(suffix) > 31 Then
            tryName = Left$(baseName, 31 - Len(suffix)) & suffix
        Else
            tryName = baseName & suffix
        End If
    Loop

    BuildUniqueExportSheetNameTemplate = tryName
End Function


'------------------------------------------------------------------------------
' Removes invalid Excel sheet-tab characters.
'------------------------------------------------------------------------------

Private Function CleanSheetTabName(ByVal s As String) As String
    s = Trim$(s)
    s = Replace$(s, "/", "-")
    s = Replace$(s, "\", "-")
    s = Replace$(s, ":", "-")
    s = Replace$(s, "*", "")
    s = Replace$(s, "?", "")
    s = Replace$(s, "[", "(")
    s = Replace$(s, "]", ")")

    If Len(s) > 31 Then s = Left$(s, 31)
    CleanSheetTabName = Trim$(s)
End Function


'------------------------------------------------------------------------------
' Applies the same row filtering used by print to export rows.
'------------------------------------------------------------------------------

Private Function RowMatchesDeliveryExportTemplate(ByVal ws As Worksheet, _
                                                  ByVal rowNum As Long, _
                                                  ByVal destinationMode As String, _
                                                  Optional ByVal exportKind As String = "ORDERS") As Boolean
    RowMatchesDeliveryExportTemplate = DoesPrintModeMatchRowTemplate(ws, rowNum, destinationMode, exportKind)
End Function


'------------------------------------------------------------------------------
' Copies top title/header formatting into a delivery export sheet.
'------------------------------------------------------------------------------

Private Sub PrepareDeliveryExportSheetTemplate(ByVal srcWs As Worksheet, _
                                               ByVal destWs As Worksheet, _
                                               ByVal visibleLastCol As String, _
                                               Optional ByVal destinationMode As String = "ALL")
    Dim i As Long

    srcWs.Range("A:" & visibleLastCol).Copy
    destWs.Range("A1").PasteSpecial xlPasteColumnWidths
    Application.CutCopyMode = False

    srcWs.Range("A1:" & visibleLastCol & "5").Copy
    destWs.Range("A1").PasteSpecial xlPasteAll
    Application.CutCopyMode = False

    For i = 1 To 5
        destWs.Rows(i).rowHeight = srcWs.Rows(i).rowHeight
    Next i

    CopyDeliveryListLogoToSheetTemplate srcWs, destWs
    ApplyDestinationAwareDeliveryTitleTemplate destWs, srcWs, destinationMode
End Sub


'------------------------------------------------------------------------------
' Finds the logo shape in the source sheet header.
'------------------------------------------------------------------------------

Private Function FindDeliveryListLogoShapeTemplate(ByVal ws As Worksheet) As Shape
    Dim shp As Shape
    Dim bestShp As Shape
    Dim topLimit As Double
    Dim leftLimit As Double
    Dim bestScore As Double
    Dim score As Double
    Dim nm As String

    If ws Is Nothing Then Exit Function

    topLimit = ws.Rows(6).Top
    leftLimit = ws.Columns("N").Left
    bestScore = 10 ^ 30

    For Each shp In ws.Shapes
        nm = LCase$(shp.Name)

        'Prefer any top-of-sheet shape explicitly named like a logo
        If InStr(1, nm, "logo", vbTextCompare) > 0 Then
            If shp.Top < topLimit Then
                Set FindDeliveryListLogoShapeTemplate = shp
                Exit Function
            End If
        End If

        'Fallback: first picture/group in the top-left header area
        Select Case shp.Type
            Case msoPicture, msoLinkedPicture, msoGroup
                If shp.Top < topLimit And shp.Left < leftLimit Then
                    score = shp.Top + shp.Left
                    If bestShp Is Nothing Or score < bestScore Then
                        Set bestShp = shp
                        bestScore = score
                    End If
                End If
        End Select
    Next shp

    If Not bestShp Is Nothing Then
        Set FindDeliveryListLogoShapeTemplate = bestShp
    End If
End Function


'------------------------------------------------------------------------------
' Removes previously copied logo shapes from a destination sheet.
'------------------------------------------------------------------------------

Private Sub RemoveCopiedDeliveryListLogoTemplate(ByVal ws As Worksheet)
    Dim shp As Shape

    If ws Is Nothing Then Exit Sub

    On Error Resume Next
    For Each shp In ws.Shapes
        If LCase$(Left$(shp.Name, 13)) = "dlsharedlogo_" Then
            shp.Delete
        End If
    Next shp
    On Error GoTo 0
End Sub


'------------------------------------------------------------------------------
' Copies the delivery-list logo from the source sheet to an output sheet.
'------------------------------------------------------------------------------

Public Sub CopyDeliveryListLogoToSheetTemplate(ByVal srcWs As Worksheet, ByVal destWs As Worksheet)
    Dim srcLogo As Shape
    Dim newShp As Shape
    Dim safeName As String

    If srcWs Is Nothing Or destWs Is Nothing Then Exit Sub
    If UCase$(srcWs.Name) = UCase$(destWs.Name) Then Exit Sub

    Set srcLogo = FindDeliveryListLogoShapeTemplate(srcWs)

    RemoveCopiedDeliveryListLogoTemplate destWs

    If srcLogo Is Nothing Then Exit Sub

    On Error Resume Next
    srcLogo.Copy
    destWs.Paste
    Set newShp = destWs.Shapes(destWs.Shapes.Count)
    On Error GoTo 0

    If newShp Is Nothing Then Exit Sub

    safeName = Replace$(destWs.Name, " ", "_")
    safeName = Replace$(safeName, "-", "_")

    With newShp
        .Name = "dlSharedLogo_" & safeName
        .Left = srcLogo.Left
        .Top = srcLogo.Top
        .Width = srcLogo.Width
        .Height = srcLogo.Height
        .Placement = xlFreeFloating
        .Locked = True
    End With
End Sub


'------------------------------------------------------------------------------
' Removes Excel's default blank sheet after export sheets are created.
'------------------------------------------------------------------------------

Private Sub DeleteDefaultFirstSheetIfNeededTemplate(ByVal wb As Workbook)
    Dim ws As Worksheet

    If wb Is Nothing Then Exit Sub
    If wb.Worksheets.Count <= 1 Then Exit Sub

    Set ws = wb.Worksheets(1)

    If LCase$(Left$(ws.Name, 5)) = "sheet" Then
        Application.DisplayAlerts = False
        ws.Delete
        Application.DisplayAlerts = True
    End If
End Sub


'------------------------------------------------------------------------------
' Creates one delivery export worksheet for one glass section.
'------------------------------------------------------------------------------

Private Function CreateDeliveryExportSectionSheetTemplate(ByVal srcWs As Worksheet, _
                                                          ByVal newWb As Workbook, _
                                                          ByVal sectionTitle As String, _
                                                          ByVal headerRow As Long, _
                                                          ByVal startRow As Long, _
                                                          ByVal endRow As Long, _
                                                          ByVal orderCol As Long, _
                                                          ByVal itemCol As Long, _
                                                          ByVal destinationMode As String, _
                                                          ByVal selectedGlassKeys As String, _
                                                          ByVal visibleLastCol As String, _
                                                          Optional ByVal exportKind As String = "ORDERS") As Boolean
    Dim destWs As Worksheet
    Dim destRow As Long
    Dim r As Long
    Dim hasAny As Boolean

    If headerRow <= 0 Then Exit Function
    If startRow > endRow Then Exit Function
    If Not IsGlassSectionSelectedTemplate(sectionTitle, selectedGlassKeys) Then Exit Function

    For r = startRow To endRow
        If IsRealDeliveryLineTemplate(srcWs, r, orderCol, itemCol) Then
            If RowMatchesDeliveryExportTemplate(srcWs, r, destinationMode, exportKind) Then
                hasAny = True
                Exit For
            End If
        End If
    Next r

    If Not hasAny Then Exit Function

    Set destWs = newWb.Worksheets.Add(After:=newWb.Worksheets(newWb.Worksheets.Count))
    destWs.Name = BuildUniqueExportSheetNameTemplate(newWb, sectionTitle)

    PrepareDeliveryExportSheetTemplate srcWs, destWs, visibleLastCol, destinationMode

    destRow = 6
    CopyPrintableRowForPrint srcWs, headerRow, destWs, destRow, sectionTitle, "HEADER", visibleLastCol, destinationMode
    destRow = destRow + 1

    For r = startRow To endRow
        If IsRealDeliveryLineTemplate(srcWs, r, orderCol, itemCol) Then
            If RowMatchesDeliveryExportTemplate(srcWs, r, destinationMode, exportKind) Then
                CopyPrintableRowForPrint srcWs, r, destWs, destRow, sectionTitle, "LINE", visibleLastCol, destinationMode
                destRow = destRow + 1
            End If
        End If
    Next r

    CreateDeliveryExportSectionSheetTemplate = True
End Function


'------------------------------------------------------------------------------
' Creates one remake export worksheet for one glass section.
'------------------------------------------------------------------------------

Private Function CreateRemakeExportSectionSheetTemplate(ByVal srcWs As Worksheet, _
                                                        ByVal newWb As Workbook, _
                                                        ByVal templateWs As Worksheet, _
                                                        ByVal sectionTitle As String, _
                                                        ByVal startRow As Long, _
                                                        ByVal endRow As Long, _
                                                        ByVal orderCol As Long, _
                                                        ByVal itemCol As Long, _
                                                        ByVal qtyCol As Long, _
                                                        ByVal dimCol As Long, _
                                                        ByVal destinationMode As String, _
                                                        ByVal selectedGlassKeys As String, _
                                                        ByVal listDate As Date, _
                                                        Optional ByVal exportKind As String = "REMAKES") As Boolean
    Dim destWs As Worksheet
    Dim bodyLastRow As Long
    Dim bodyStartRow As Long
    Dim destRow As Long
    Dim r As Long
    Dim hasAny As Boolean

    If startRow > endRow Then Exit Function
    If Not IsGlassSectionSelectedTemplate(sectionTitle, selectedGlassKeys) Then Exit Function

    For r = startRow To endRow
        If IsRealDeliveryLineTemplate(srcWs, r, orderCol, itemCol) Then
            If DoesPrintModeMatchRowTemplate(srcWs, r, destinationMode, exportKind) Then
                hasAny = True
                Exit For
            End If
        End If
    Next r

    If Not hasAny Then Exit Function

    templateWs.Visible = xlSheetVisible
    templateWs.Copy After:=newWb.Worksheets(newWb.Worksheets.Count)
    Set destWs = newWb.Worksheets(newWb.Worksheets.Count)
    templateWs.Visible = xlSheetVeryHidden

    destWs.Name = BuildUniqueExportSheetNameTemplate(newWb, sectionTitle)

    On Error Resume Next
    destWs.Unprotect Password:=""
    On Error GoTo 0

    If listDate > 0 Then
        destWs.Range("A2").Value = REMAKE_TITLE_PREFIX & Format$(listDate, "m/d/yyyy")
    End If

    ApplyRemakePrintColumnHeadersTemplate destWs

    bodyLastRow = GetLastUsedRowTemplate(destWs)
    bodyStartRow = GetRemakePrintBodyStartRowTemplate(destWs)

    If bodyLastRow < bodyStartRow Then bodyLastRow = bodyStartRow
    destWs.Range("A" & bodyStartRow & ":M" & bodyLastRow).ClearContents

    destRow = bodyStartRow
    WriteRemakeSectionHeaderTemplate destWs, destRow, sectionTitle
    WriteRemakeBlankSpacerTemplate destWs, destRow + 1
    destRow = destRow + 2

    For r = startRow To endRow
        If IsRealDeliveryLineTemplate(srcWs, r, orderCol, itemCol) Then
            If DoesPrintModeMatchRowTemplate(srcWs, r, destinationMode, exportKind) Then
                WriteRemakeLineTemplate srcWs, r, destWs, destRow, orderCol, itemCol, qtyCol, dimCol
                destRow = destRow + 1
            End If
        End If
    Next r

    ConfigureRemakePrintPageTemplate destWs, destRow - 1
    CreateRemakeExportSectionSheetTemplate = True
End Function


'==============================================================================
' Public export entry points
'==============================================================================


'------------------------------------------------------------------------------
' Public entry point that exports delivery-list sheets to a new workbook.
'------------------------------------------------------------------------------

Public Sub ExportDeliveryListWorkbookTemplate(ByVal srcWs As Worksheet, _
                                               ByVal destinationMode As String, _
                                               ByVal selectedGlassKeys As String, _
                                               Optional ByVal exportKind As String = "ORDERS")
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim firstDataRow As Long
    Dim lastRealRow As Long
    Dim orderCol As Long
    Dim itemCol As Long

    On Error GoTo ErrHandler

    Set orderHdr = FindHeaderCellTemplate(srcWs, Array("Order Nr."))
    Set itemHdr = FindHeaderCellTemplate(srcWs, Array("Item Nr.", "Item"))

    If orderHdr Is Nothing Or itemHdr Is Nothing Then
        MsgBox "Could not find Order Nr. / Item headers for delivery export.", vbExclamation, "Export Delivery List"
        Exit Sub
    End If

    firstDataRow = orderHdr.Row + 1
    orderCol = orderHdr.Column
    itemCol = itemHdr.Column
    lastRealRow = FindLastRealDeliveryRowTemplate(srcWs, orderCol, itemCol, firstDataRow)

    If lastRealRow < firstDataRow Then
        MsgBox "No delivery rows were found to export.", vbInformation, "Export Delivery List"
        Exit Sub
    End If

    ExportDeliveryListWorkbookFromPrintTemplate srcWs, 0, 0, firstDataRow, lastRealRow, _
                                                orderCol, itemCol, destinationMode, selectedGlassKeys, exportKind
    Exit Sub

ErrHandler:
    MsgBox "ExportDeliveryListWorkbookTemplate error " & Err.Number & ":" & vbCrLf & Err.Description, vbCritical, "Export Error"
End Sub


'------------------------------------------------------------------------------
' Creates the delivery-list export workbook and saves it as .xlsx.
'------------------------------------------------------------------------------

Private Sub ExportDeliveryListWorkbookFromPrintTemplate(ByVal srcWs As Worksheet, _
                                                        ByVal sectionStartRow As Long, ByVal sectionEndRow As Long, _
                                                        ByVal firstDataRow As Long, ByVal lastRealRow As Long, _
                                                        ByVal orderCol As Long, ByVal itemCol As Long, _
                                                        ByVal destinationMode As String, _
                                                        ByVal selectedGlassKeys As String, _
                                                        Optional ByVal exportKind As String = "ORDERS")
    Dim newWb As Workbook
    Dim visibleLastCol As String
    Dim scanStart As Long
    Dim scanEnd As Long
    Dim r As Long
    Dim currentSectionTitle As String
    Dim currentHeaderRow As Long
    Dim currentSectionStart As Long
    Dim madeAnySheets As Boolean
    Dim savePath As Variant
    Dim suggestedName As String
    Dim oldDisplayAlerts As Boolean
    Dim oldScreenUpdating As Boolean

    On Error GoTo ErrHandler

    oldDisplayAlerts = Application.DisplayAlerts
    oldScreenUpdating = Application.ScreenUpdating
    Application.DisplayAlerts = False
    Application.ScreenUpdating = False

    visibleLastCol = GetPrintLastColForDestination(destinationMode)

    If sectionStartRow > 0 And sectionEndRow > 0 Then
        scanStart = sectionStartRow
        scanEnd = sectionEndRow
    Else
        scanStart = firstDataRow
        scanEnd = lastRealRow
    End If

    Set newWb = Workbooks.Add(xlWBATWorksheet)

    currentSectionTitle = vbNullString
    currentHeaderRow = 0
    currentSectionStart = 0
    madeAnySheets = False

    For r = scanStart To scanEnd
        If IsSectionHeaderRowTemplate(srcWs, r, orderCol, itemCol) Then
            If currentHeaderRow > 0 Then
                If CreateDeliveryExportSectionSheetTemplate(srcWs, newWb, currentSectionTitle, currentHeaderRow, _
                                                            currentSectionStart, r - 1, orderCol, itemCol, _
                                                            destinationMode, selectedGlassKeys, visibleLastCol, exportKind) Then
                    madeAnySheets = True
                End If
            End If

            currentSectionTitle = Trim$(CStr(srcWs.Cells(r, 1).Value))
            currentHeaderRow = r
            currentSectionStart = r + 1
        End If
    Next r

    If currentHeaderRow > 0 Then
        If CreateDeliveryExportSectionSheetTemplate(srcWs, newWb, currentSectionTitle, currentHeaderRow, _
                                                    currentSectionStart, scanEnd, orderCol, itemCol, _
                                                    destinationMode, selectedGlassKeys, visibleLastCol, exportKind) Then
            madeAnySheets = True
        End If
    End If

    If Not madeAnySheets Then
        MsgBox "There were no delivery rows to export for the selected glass section(s).", _
               vbInformation, "Export Delivery List"
        GoTo SafeExit
    End If

    DeleteDefaultFirstSheetIfNeededTemplate newWb

    Select Case UCase$(exportKind)
        Case "UPDATED_ORDERS"
            suggestedName = BuildSuggestedExportFileNameTemplate("DELIVERY", srcWs) & "_Updated"
        Case "UPDATED_ALL"
            suggestedName = BuildSuggestedExportFileNameTemplate("DELIVERY", srcWs) & "_Updated"
        Case "ALL"
            suggestedName = BuildSuggestedExportFileNameTemplate("DELIVERY", srcWs) & ""
        Case Else
            suggestedName = BuildSuggestedExportFileNameTemplate("DELIVERY", srcWs)
    End Select

    newWb.Activate
    DoEvents

    savePath = PromptForXlsxSavePathTemplate(suggestedName, "Export Delivery List")
    If Len(CStr(savePath)) = 0 Then GoTo SafeExit

    newWb.SaveAs Filename:=CStr(savePath), FileFormat:=xlOpenXMLWorkbook
    MsgBox "Delivery export created successfully.", vbInformation, "Export Delivery List"

SafeExit:
    On Error Resume Next
    Application.DisplayAlerts = False
    If Not newWb Is Nothing Then newWb.Close SaveChanges:=False
    Application.DisplayAlerts = oldDisplayAlerts
    Application.ScreenUpdating = oldScreenUpdating
    On Error GoTo 0
    Exit Sub

ErrHandler:
    Application.DisplayAlerts = False
    On Error Resume Next
    If Not newWb Is Nothing Then newWb.Close SaveChanges:=False
    Application.DisplayAlerts = oldDisplayAlerts
    Application.ScreenUpdating = oldScreenUpdating
    MsgBox "ExportDeliveryListWorkbookFromPrintTemplate error " & Err.Number & ":" & vbCrLf & Err.Description, _
           vbCritical, "Export Error"
End Sub


'------------------------------------------------------------------------------
' Public entry point that exports remake sheets to a new workbook.
'------------------------------------------------------------------------------

Public Sub ExportRemakeListWorkbookTemplate(ByVal srcWs As Worksheet, _
                                             ByVal destinationMode As String, _
                                             ByVal selectedGlassKeys As String, _
                                             Optional ByVal exportKind As String = "REMAKES")
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim orderCol As Long
    Dim itemCol As Long
    Dim firstDataRow As Long
    Dim lastRealRow As Long

    On Error GoTo ErrHandler

    Set orderHdr = FindHeaderCellTemplateInCols(srcWs, Array("Order Nr."), "A:N", 250)
    Set itemHdr = FindHeaderCellTemplateInCols(srcWs, Array("Item Nr.", "Item"), "A:N", 250)

    If orderHdr Is Nothing Or itemHdr Is Nothing Then
        MsgBox "Could not find the Delivery List headers needed for remake export.", vbExclamation, "Export Remake List"
        Exit Sub
    End If

    orderCol = orderHdr.Column
    itemCol = itemHdr.Column
    firstDataRow = orderHdr.Row + 1
    lastRealRow = FindLastRealDeliveryRowTemplate(srcWs, orderCol, itemCol, firstDataRow)

    If lastRealRow < firstDataRow Then
        MsgBox "There are no remake rows to export.", vbInformation, "Export Remake List"
        Exit Sub
    End If

    ExportRemakeListWorkbookFromTemplate srcWs, 0, 0, firstDataRow, lastRealRow, _
                                         orderCol, itemCol, destinationMode, selectedGlassKeys, exportKind
    Exit Sub

ErrHandler:
    MsgBox "ExportRemakeListWorkbookTemplate error " & Err.Number & ":" & vbCrLf & Err.Description, vbCritical, "Export Error"
End Sub


'------------------------------------------------------------------------------
' Creates the remake export workbook and saves it as .xlsx.
'------------------------------------------------------------------------------

Private Sub ExportRemakeListWorkbookFromTemplate(ByVal srcWs As Worksheet, _
                                                 ByVal sectionStartRow As Long, ByVal sectionEndRow As Long, _
                                                 ByVal firstDataRow As Long, ByVal lastRealRow As Long, _
                                                 ByVal orderCol As Long, ByVal itemCol As Long, _
                                                 ByVal destinationMode As String, _
                                                 ByVal selectedGlassKeys As String, _
                                                 Optional ByVal exportKind As String = "REMAKES")
    Dim newWb As Workbook
    Dim templateWs As Worksheet
    Dim qtyHdr As Range
    Dim dimHdr As Range
    Dim qtyCol As Long
    Dim dimCol As Long
    Dim listDate As Date
    Dim savePath As Variant
    Dim suggestedName As String
    Dim oldDisplayAlerts As Boolean
    Dim oldScreenUpdating As Boolean
    Dim scanStart As Long
    Dim scanEnd As Long
    Dim r As Long
    Dim currentSectionTitle As String
    Dim currentSectionStart As Long
    Dim madeAnySheets As Boolean

    On Error GoTo ErrHandler

    Set qtyHdr = FindHeaderCellTemplate(srcWs, Array("Qty.", "Qty"))
    Set dimHdr = FindHeaderCellTemplate(srcWs, Array("Dimensions"))

    If qtyHdr Is Nothing Or dimHdr Is Nothing Then
        MsgBox "Could not find Qty. / Dimensions headers needed for remake export.", _
               vbExclamation, "Export Remake List"
        Exit Sub
    End If

    qtyCol = qtyHdr.Column
    dimCol = dimHdr.Column
    listDate = GetDeliveryListDateForFileName(srcWs)

    oldDisplayAlerts = Application.DisplayAlerts
    oldScreenUpdating = Application.ScreenUpdating
    Application.DisplayAlerts = False
    Application.ScreenUpdating = False

    Set templateWs = ThisWorkbook.Worksheets(REMAKE_PRINT_TEMPLATE_SHEET)
    Set newWb = Workbooks.Add(xlWBATWorksheet)

    If sectionStartRow > 0 And sectionEndRow > 0 Then
        scanStart = sectionStartRow
        scanEnd = sectionEndRow
    Else
        scanStart = firstDataRow
        scanEnd = lastRealRow
    End If

    currentSectionTitle = vbNullString
    currentSectionStart = 0
    madeAnySheets = False

    For r = scanStart To scanEnd
        If IsSectionHeaderRowTemplate(srcWs, r, orderCol, itemCol) Then
            If currentSectionStart > 0 Then
                If CreateRemakeExportSectionSheetTemplate(srcWs, newWb, templateWs, currentSectionTitle, _
                                                          currentSectionStart, r - 1, orderCol, itemCol, _
                                                          qtyCol, dimCol, destinationMode, selectedGlassKeys, _
                                                          listDate, exportKind) Then
                    madeAnySheets = True
                End If
            End If

            currentSectionTitle = Trim$(CStr(srcWs.Cells(r, 1).Value))
            currentSectionStart = r + 1
        End If
    Next r

    If currentSectionStart > 0 Then
        If CreateRemakeExportSectionSheetTemplate(srcWs, newWb, templateWs, currentSectionTitle, _
                                                  currentSectionStart, scanEnd, orderCol, itemCol, _
                                                  qtyCol, dimCol, destinationMode, selectedGlassKeys, _
                                                  listDate, exportKind) Then
            madeAnySheets = True
        End If
    End If

    If Not madeAnySheets Then
        MsgBox "There were no remake rows to export for the selected glass section(s).", _
               vbInformation, "Export Remake List"
        GoTo SafeExit
    End If

    DeleteDefaultFirstSheetIfNeededTemplate newWb

    If UCase$(exportKind) = "UPDATED_REMAKES" Then
        suggestedName = BuildSuggestedExportFileNameTemplate("REMAKES", srcWs) & "_Updated"
    Else
        suggestedName = BuildSuggestedExportFileNameTemplate("REMAKES", srcWs)
    End If

    newWb.Activate
    DoEvents

    savePath = PromptForXlsxSavePathTemplate(suggestedName, "Export Remake List")
    If Len(CStr(savePath)) = 0 Then GoTo SafeExit

    newWb.SaveAs Filename:=CStr(savePath), FileFormat:=xlOpenXMLWorkbook
    MsgBox "Remake export created successfully.", vbInformation, "Export Remake List"

SafeExit:
    On Error Resume Next
    Application.DisplayAlerts = False
    If Not newWb Is Nothing Then newWb.Close SaveChanges:=False
    If Not templateWs Is Nothing Then templateWs.Visible = xlSheetVeryHidden
    Application.DisplayAlerts = oldDisplayAlerts
    Application.ScreenUpdating = oldScreenUpdating
    On Error GoTo 0
    Exit Sub

ErrHandler:
    Application.DisplayAlerts = False
    On Error Resume Next
    If Not newWb Is Nothing Then newWb.Close SaveChanges:=False
    If Not templateWs Is Nothing Then templateWs.Visible = xlSheetVeryHidden
    Application.DisplayAlerts = oldDisplayAlerts
    Application.ScreenUpdating = oldScreenUpdating
    MsgBox "ExportRemakeListWorkbookFromTemplate error " & Err.Number & ":" & vbCrLf & Err.Description, _
           vbCritical, "Export Error"
End Sub


'==============================================================================
' Delivery-list date and header helpers
'==============================================================================


'------------------------------------------------------------------------------
' Extracts a date from delivery-list title text.
'------------------------------------------------------------------------------

Private Function TryParseDateFromTitleTextTemplate(ByVal s As String) As Date
    Dim p As Long
    Dim candidate As String

    s = Trim$(CStr(s))
    p = InStr(1, UCase$(s), "DELIVERY LIST FOR", vbTextCompare)

    If p > 0 Then
        candidate = Trim$(Mid$(s, p + Len("DELIVERY LIST FOR")))
        On Error Resume Next
        TryParseDateFromTitleTextTemplate = DateValue(candidate)
        On Error GoTo 0
    End If
End Function


'------------------------------------------------------------------------------
' Returns the delivery-list date used in titles and file names.
'------------------------------------------------------------------------------

Public Function GetDeliveryListDateForFileName(ByVal ws As Worksheet) As Date
    Dim hdr As Range
    Dim r As Range
    Dim c As Range
    Dim dt As Date

    Set r = ws.Range("A1:AG5")
    Set hdr = r.Find(What:="DELIVERY LIST FOR", LookIn:=xlValues, LookAt:=xlPart)

    If Not hdr Is Nothing Then
        'First: old behavior - look for a standalone date cell on the same row
        For Each c In ws.Range(ws.Cells(hdr.Row, hdr.Column), ws.Cells(hdr.Row, ws.Columns.Count)).Cells
            If IsDate(c.Value) Then
                GetDeliveryListDateForFileName = DateValue(c.Value)
                Exit Function
            End If
        Next c

        'Second: new behavior - parse the date from the title text itself
        dt = TryParseDateFromTitleTextTemplate(CStr(hdr.Value))
        If dt > 0 Then
            GetDeliveryListDateForFileName = dt
            Exit Function
        End If
    End If

    'Fallback: any standalone date in the top area
    For Each c In ws.Range("A1:AG3").Cells
        If IsDate(c.Value) Then
            GetDeliveryListDateForFileName = DateValue(c.Value)
            Exit Function
        End If
    Next c

    GetDeliveryListDateForFileName = 0
End Function


'------------------------------------------------------------------------------
' Removes invalid file-name characters.
'------------------------------------------------------------------------------

Private Function CleanFileName(ByVal s As String) As String
    s = Trim$(s)
    s = Replace$(s, "\", "-")
    s = Replace$(s, "/", "-")
    s = Replace$(s, ":", "-")
    s = Replace$(s, "*", "")
    s = Replace$(s, "?", "")
    s = Replace$(s, """", "")
    s = Replace$(s, "<", "")
    s = Replace$(s, ">", "")
    s = Replace$(s, "|", "-")
    s = Replace$(s, vbCr, " ")
    s = Replace$(s, vbLf, " ")

    Do While InStr(s, "  ") > 0
        s = Replace$(s, "  ", " ")
    Loop

    CleanFileName = Trim$(s)
End Function


'------------------------------------------------------------------------------
' Finds a header in a specific column band.
'------------------------------------------------------------------------------

Private Function FindHeaderCellTemplateInCols(ByVal ws As Worksheet, ByVal names As Variant, ByVal colAddress As String, Optional ByVal topRows As Long = 250) As Range
    Dim searchRange As Range
    Dim nm As Variant
    Dim f As Range

    Set searchRange = Intersect(ws.Range("1:" & topRows), ws.Columns(colAddress))
    If searchRange Is Nothing Then
        Set FindHeaderCellTemplateInCols = Nothing
        Exit Function
    End If

    For Each nm In names
        Set f = searchRange.Find(What:=CStr(nm), LookIn:=xlValues, LookAt:=xlWhole)
        If Not f Is Nothing Then
            Set FindHeaderCellTemplateInCols = f
            Exit Function
        End If
    Next nm

    For Each nm In names
        Set f = searchRange.Find(What:=CStr(nm), LookIn:=xlValues, LookAt:=xlPart)
        If Not f Is Nothing Then
            Set FindHeaderCellTemplateInCols = f
            Exit Function
        End If
    Next nm

    Set FindHeaderCellTemplateInCols = Nothing
End Function


'------------------------------------------------------------------------------
' Finds a header anywhere in the top rows.
'------------------------------------------------------------------------------

Private Function FindHeaderCellTemplate(ByVal ws As Worksheet, ByVal names As Variant, Optional ByVal topRows As Long = 250) As Range
    Dim searchRange As Range
    Dim nm As Variant
    Dim f As Range

    Set searchRange = ws.Range(ws.Cells(1, 1), ws.Cells(topRows, ws.Columns.Count))

    For Each nm In names
        Set f = searchRange.Find(What:=CStr(nm), LookIn:=xlValues, LookAt:=xlWhole)
        If Not f Is Nothing Then
            Set FindHeaderCellTemplate = f
            Exit Function
        End If
    Next nm

    For Each nm In names
        Set f = searchRange.Find(What:=CStr(nm), LookIn:=xlValues, LookAt:=xlPart)
        If Not f Is Nothing Then
            Set FindHeaderCellTemplate = f
            Exit Function
        End If
    Next nm

    Set FindHeaderCellTemplate = Nothing
End Function


'------------------------------------------------------------------------------
' Finds the last real delivery line.
'------------------------------------------------------------------------------

Private Function FindLastRealDeliveryRowTemplate(ByVal ws As Worksheet, ByVal orderCol As Long, ByVal itemCol As Long, ByVal firstDataRow As Long) As Long
    Dim lastUsedRow As Long
    Dim r As Long

    lastUsedRow = GetLastUsedRowTemplate(ws)

    For r = lastUsedRow To firstDataRow Step -1
        If IsRealDeliveryLineTemplate(ws, r, orderCol, itemCol) Then
            FindLastRealDeliveryRowTemplate = r
            Exit Function
        End If
    Next r

    FindLastRealDeliveryRowTemplate = 0
End Function


'------------------------------------------------------------------------------
' Returns True for rows with an order or item value.
'------------------------------------------------------------------------------

Private Function IsRealDeliveryLineTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, ByVal orderCol As Long, ByVal itemCol As Long) As Boolean
    IsRealDeliveryLineTemplate = _
        (Len(Trim$(CStr(ws.Cells(rowNum, orderCol).Value))) > 0 Or _
         Len(Trim$(CStr(ws.Cells(rowNum, itemCol).Value))) > 0)
End Function


'------------------------------------------------------------------------------
' Writes remake print/export column headers.
'------------------------------------------------------------------------------

Private Sub ApplyRemakePrintColumnHeadersTemplate(ByVal ws As Worksheet)
    Dim hdrRow As Long

    hdrRow = GetRemakePrintHeaderRowTemplate(ws)

    On Error Resume Next
    ws.Range("A" & hdrRow & ":K" & hdrRow).UnMerge
    On Error GoTo 0

    ws.Range("A" & hdrRow & ":K" & hdrRow).ClearContents

    ws.Range("A" & hdrRow).Value = "Job Nr."
    ws.Range("C" & hdrRow).Value = "Order"
    ws.Range("E" & hdrRow).Value = "Item"
    ws.Range("G" & hdrRow).Value = "Qty."
    ws.Range("I" & hdrRow).Value = "Dimensions"
    ws.Range("K" & hdrRow).Value = "Check Off"

    With ws.Range("A" & hdrRow & ":K" & hdrRow)
        .Font.Bold = True
        .Font.Underline = xlUnderlineStyleNone
        .VerticalAlignment = xlCenter
    End With

    ws.Range("A" & hdrRow).HorizontalAlignment = xlLeft
    ws.Range("C" & hdrRow).HorizontalAlignment = xlCenter
    ws.Range("E" & hdrRow).HorizontalAlignment = xlCenter
    ws.Range("G" & hdrRow).HorizontalAlignment = xlCenter
    ws.Range("I" & hdrRow).HorizontalAlignment = xlLeft
    ws.Range("K" & hdrRow).HorizontalAlignment = xlCenter
End Sub


'------------------------------------------------------------------------------
' Finds the remake template header row.
'------------------------------------------------------------------------------

Private Function GetRemakePrintHeaderRowTemplate(ByVal ws As Worksheet) As Long
    Dim f As Range

    On Error Resume Next
    Set f = ws.Cells.Find(What:="Job Nr.", LookIn:=xlValues, LookAt:=xlWhole, _
                          SearchOrder:=xlByRows, SearchDirection:=xlNext, MatchCase:=False)
    On Error GoTo 0

    If Not f Is Nothing Then
        GetRemakePrintHeaderRowTemplate = f.Row
    Else
        'Fallback to old layout if header not found
        GetRemakePrintHeaderRowTemplate = 5
    End If
End Function


'------------------------------------------------------------------------------
' Finds the first remake body/output row.
'------------------------------------------------------------------------------

Private Function GetRemakePrintBodyStartRowTemplate(ByVal ws As Worksheet) As Long
    'Old layout:
    'header row = 5
    'section template row = 7
    'so body starts header + 2
    GetRemakePrintBodyStartRowTemplate = GetRemakePrintHeaderRowTemplate(ws) + 2
End Function


'------------------------------------------------------------------------------
' Returns the remake template section-header row.
'------------------------------------------------------------------------------

Private Function GetRemakePrintSectionTemplateRowTemplate(ByVal ws As Worksheet) As Long
    GetRemakePrintSectionTemplateRowTemplate = GetRemakePrintHeaderRowTemplate(ws) + 2
End Function


'------------------------------------------------------------------------------
' Returns the remake template spacer row.
'------------------------------------------------------------------------------

Private Function GetRemakePrintSpacerTemplateRowTemplate(ByVal ws As Worksheet) As Long
    GetRemakePrintSpacerTemplateRowTemplate = GetRemakePrintHeaderRowTemplate(ws) + 3
End Function


'------------------------------------------------------------------------------
' Returns the remake template detail-line row.
'------------------------------------------------------------------------------

Private Function GetRemakePrintLineTemplateRowTemplate(ByVal ws As Worksheet) As Long
    GetRemakePrintLineTemplateRowTemplate = GetRemakePrintHeaderRowTemplate(ws) + 4
End Function


'==============================================================================
' UserForm support functions
'==============================================================================


'------------------------------------------------------------------------------
' Builds the destination token list from visible/available checkbox states.
'------------------------------------------------------------------------------

Public Function GetSafeVisibleDestinationModeTemplate(ByVal indianTrailOn As Boolean, _
                                                       ByVal greenvilleOn As Boolean, _
                                                       ByVal cpuOn As Boolean) As String
    Dim outText As String

    If indianTrailOn Then AddTokenTemplate outText, "STANDARD"
    If greenvilleOn Then AddTokenTemplate outText, "GREENVILLE"
    If cpuOn Then AddTokenTemplate outText, "CPU"

    GetSafeVisibleDestinationModeTemplate = outText
End Function


'------------------------------------------------------------------------------
' Returns True when at least one row matches the selected destination and print/export type.
'------------------------------------------------------------------------------

Public Function HasPrintableRowsForTemplate(ByVal ws As Worksheet, _
                                            ByVal firstDataRow As Long, _
                                            ByVal lastRealRow As Long, _
                                            ByVal orderCol As Long, _
                                            ByVal itemCol As Long, _
                                            ByVal destinationMode As String, _
                                            ByVal printKind As String) As Boolean
    Dim r As Long

    For r = firstDataRow To lastRealRow
        If IsRealDeliveryLineTemplate(ws, r, orderCol, itemCol) Then
            If DoesPrintModeMatchRowTemplate(ws, r, destinationMode, printKind) Then
                HasPrintableRowsForTemplate = True
                Exit Function
            End If
        End If
    Next r
End Function


'==============================================================================
' Legacy intake button compatibility wrappers
'
' These keep older worksheet buttons from breaking if they still point to the
' master-style macro names. New intake buttons should use the safe wrappers in
' modIntakePrintExport instead:
'   RunIntakePrintDeliveryListSafe
'   RunIntakeExportListsSafe
'==============================================================================
Public Sub PrintDeliveryListBySection()
    RunIntakePrintDeliveryListSafe
End Sub

Public Sub ExportListsFromUtilityPanel()
    RunIntakeExportListsSafe
End Sub


