Attribute VB_Name = "modRushOrders"
Option Explicit

'==============================================================================
' Module: modRushOrders
' Workbook: Master Delivery List workbook
'
' Purpose:
'   UserForm-driven Rush Order workflow.
'
' Features:
'   - Mark order(s) or order/item(s) as RUSH.
'   - Clear rush marks.
'   - Shows current rush rows in frmRushOrders.
'   - Prints/previews dedicated rush forms from a temporary workbook.
'   - Avoids risky page breaks/temp print sheets inside the master workbook.
'
' Storage:
'   AX = Rush flag
'   AY = Rush note
'   AZ = Rush added date/time
'   BA = Rush added by
'
' Notes:
'   These helper columns are outside A:N, P:W, Y:AG, and AP:AV, so they should
'   not interfere with your current scan blocks.
'==============================================================================

Public Const RUSH_DATA_SHEET_NAME As String = "Delivery List"

Public Const RUSH_STATUS_COL As Long = 50   'AX
Public Const RUSH_NOTE_COL As Long = 51     'AY
Public Const RUSH_DATE_COL As Long = 52     'AZ
Public Const RUSH_USER_COL As Long = 53     'BA

Public Const RUSH_FLAG_TEXT As String = "RUSH"

Private Const DELIVERY_HEADER_COLS As String = "A:N"
Private Const HEADER_SEARCH_TOP_ROWS As Long = 250

'------------------------------------------------------------------------------
' Utility Panel entry point.
' Keep this macro name because your Utility Panel button points to it.
'------------------------------------------------------------------------------
Public Sub RunRushOrdersFromUtilityPanelSafe()
    On Error GoTo ErrHandler

    RushOrders_EnsureReady
    frmRushOrders.Show

    Exit Sub

ErrHandler:
    MsgBox "Could not open Rush Orders." & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbExclamation, "Rush Orders"
End Sub

'------------------------------------------------------------------------------
' Public initializer used by the form.
'------------------------------------------------------------------------------
Public Sub RushOrders_EnsureReady()
    Dim ws As Worksheet

    Set ws = RushOrders_GetDataSheet()
    RushOrders_EnsureRushColumns ws
    RushOrders_ApplyRushFormatting ws
End Sub

'------------------------------------------------------------------------------
' Mark typed orders/items as rush.
' rawOrders accepts:
'   231860
'   231860-002
'   T200231860002000
'   Multiple values separated by commas, spaces, tabs, or new lines.
'------------------------------------------------------------------------------
Public Function RushOrders_MarkOrders(ByVal rawOrders As String, _
                                      ByVal rushNote As String, _
                                      ByRef notFoundText As String) As Long
    Dim ws As Worksheet
    Dim tokens As Collection
    Dim token As Variant
    Dim orderNumber As Long
    Dim itemNumber As Long
    Dim updatedForToken As Long
    Dim totalUpdated As Long

    Set ws = RushOrders_GetDataSheet()
    RushOrders_EnsureRushColumns ws

    Set tokens = RushOrders_ParseTokens(rawOrders)

    For Each token In tokens
        orderNumber = 0
        itemNumber = 0

        If RushOrders_ParseOneToken(CStr(token), orderNumber, itemNumber) Then
            updatedForToken = RushOrders_UpdateMatchingRows(ws, orderNumber, itemNumber, True, rushNote)
            totalUpdated = totalUpdated + updatedForToken

            If updatedForToken = 0 Then
                notFoundText = notFoundText & CStr(token) & vbCrLf
            End If
        Else
            notFoundText = notFoundText & CStr(token) & "  (could not read)" & vbCrLf
        End If
    Next token

    If totalUpdated > 0 Then
        RushOrders_ApplyRushFormatting ws

        On Error Resume Next
        BumpCurrentDeliveryListRevision
        On Error GoTo 0
    End If

    RushOrders_MarkOrders = totalUpdated
End Function

'------------------------------------------------------------------------------
' Clear rush marks from typed orders/items.
'------------------------------------------------------------------------------
Public Function RushOrders_ClearOrders(ByVal rawOrders As String, _
                                       ByRef notFoundText As String) As Long
    Dim ws As Worksheet
    Dim tokens As Collection
    Dim token As Variant
    Dim orderNumber As Long
    Dim itemNumber As Long
    Dim updatedForToken As Long
    Dim totalUpdated As Long

    Set ws = RushOrders_GetDataSheet()
    RushOrders_EnsureRushColumns ws

    Set tokens = RushOrders_ParseTokens(rawOrders)

    For Each token In tokens
        orderNumber = 0
        itemNumber = 0

        If RushOrders_ParseOneToken(CStr(token), orderNumber, itemNumber) Then
            updatedForToken = RushOrders_UpdateMatchingRows(ws, orderNumber, itemNumber, False, vbNullString)
            totalUpdated = totalUpdated + updatedForToken

            If updatedForToken = 0 Then
                notFoundText = notFoundText & CStr(token) & vbCrLf
            End If
        Else
            notFoundText = notFoundText & CStr(token) & "  (could not read)" & vbCrLf
        End If
    Next token

    If totalUpdated > 0 Then
        RushOrders_ApplyRushFormatting ws

        On Error Resume Next
        BumpCurrentDeliveryListRevision
        On Error GoTo 0
    End If

    RushOrders_ClearOrders = totalUpdated
End Function

'------------------------------------------------------------------------------
' Clear selected rows from the form list.
'------------------------------------------------------------------------------
Public Function RushOrders_ClearRowsBySourceRow(ByVal rowNumbers As Collection) As Long
    Dim ws As Worksheet
    Dim rowNumber As Variant
    Dim clearedCount As Long

    If rowNumbers Is Nothing Then Exit Function
    If rowNumbers.Count = 0 Then Exit Function

    Set ws = RushOrders_GetDataSheet()
    RushOrders_EnsureRushColumns ws

    For Each rowNumber In rowNumbers
        If CLng(rowNumber) > 0 Then
            ws.Range(ws.Cells(CLng(rowNumber), RUSH_STATUS_COL), _
                     ws.Cells(CLng(rowNumber), RUSH_USER_COL)).ClearContents
            clearedCount = clearedCount + 1
        End If
    Next rowNumber

    If clearedCount > 0 Then
        RushOrders_ApplyRushFormatting ws

        On Error Resume Next
        BumpCurrentDeliveryListRevision
        On Error GoTo 0
    End If

    RushOrders_ClearRowsBySourceRow = clearedCount
End Function

'------------------------------------------------------------------------------
' Returns current rush rows for the UserForm list.
' Each item is a late-bound Scripting.Dictionary.
'------------------------------------------------------------------------------
Public Function RushOrders_GetRushRows() As Collection
    Dim ws As Worksheet
    Dim out As New Collection
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim orderCol As Long
    Dim itemCol As Long
    Dim firstDataRow As Long
    Dim lastRow As Long
    Dim r As Long
    Dim d As Object

    Set ws = RushOrders_GetDataSheet()
    RushOrders_EnsureRushColumns ws

    Set orderHdr = RushOrders_FindHeaderCell(ws, Array("Order Nr."), DELIVERY_HEADER_COLS, HEADER_SEARCH_TOP_ROWS)
    Set itemHdr = RushOrders_FindHeaderCell(ws, Array("Item Nr.", "Item"), DELIVERY_HEADER_COLS, HEADER_SEARCH_TOP_ROWS)

    If orderHdr Is Nothing Or itemHdr Is Nothing Then
        Set RushOrders_GetRushRows = out
        Exit Function
    End If

    orderCol = orderHdr.Column
    itemCol = itemHdr.Column
    firstDataRow = orderHdr.Row + 1
    lastRow = ws.Cells(ws.rows.Count, orderCol).End(xlUp).Row

    For r = firstDataRow To lastRow
        If UCase$(Trim$(CStr(ws.Cells(r, RUSH_STATUS_COL).Value))) = RUSH_FLAG_TEXT Then
            Set d = CreateObject("Scripting.Dictionary")

            d("row") = r
            d("order") = RushOrders_CellTextByHeader(ws, r, Array("Order Nr."))
            d("item") = RushOrders_CellTextByHeader(ws, r, Array("Item Nr.", "Item"))
            d("qty") = RushOrders_CellTextByHeader(ws, r, Array("Qty.", "Qty", "Quantity"))
            d("customer") = RushOrders_CellTextByHeader(ws, r, Array("Customer"))
            d("route") = RushOrders_CellTextByHeader(ws, r, Array("Route", "Rt", "Route Code"))
            d("dimensions") = RushOrders_CellTextByHeader(ws, r, Array("Dimensions", "Dimension", "Dim", "Size"))
            d("note") = Trim$(CStr(ws.Cells(r, RUSH_NOTE_COL).Value))
            d("added") = Trim$(CStr(ws.Cells(r, RUSH_DATE_COL).Text))
            d("addedBy") = Trim$(CStr(ws.Cells(r, RUSH_USER_COL).Value))
            d("glass") = RushOrders_FindGlassHeaderAbove(ws, r)

            out.Add d
        End If
    Next r

    Set RushOrders_GetRushRows = out
End Function

'------------------------------------------------------------------------------
' Count current rush rows.
'------------------------------------------------------------------------------
Public Function RushOrders_CountRushRows() As Long
    Dim rows As Collection
    Set rows = RushOrders_GetRushRows()
    RushOrders_CountRushRows = rows.Count
End Function
'------------------------------------------------------------------------------
' Preview all current rush rows using the existing remake print template.
'------------------------------------------------------------------------------
Public Sub RushOrders_PreviewAllRush()
    BuildAndPreviewRushPrintFromTemplate "PREVIEW", 1
End Sub

'------------------------------------------------------------------------------
' Print all current rush rows using the existing remake print template.
'------------------------------------------------------------------------------
Public Sub RushOrders_PrintAllRush(ByVal copiesToPrint As Long)
    BuildAndPreviewRushPrintFromTemplate "PRINT", copiesToPrint
End Sub

'------------------------------------------------------------------------------
' Preview selected rush rows using the existing remake print template.
'------------------------------------------------------------------------------
Public Sub RushOrders_PreviewSelectedRush(ByVal rowNumbers As Collection)
    If rowNumbers Is Nothing Or rowNumbers.Count = 0 Then
        MsgBox "Select at least one rush row from the list.", vbExclamation, "Rush Orders"
        Exit Sub
    End If

    BuildAndPreviewRushSelectedPrintFromTemplate rowNumbers, "PREVIEW", 1
End Sub

'------------------------------------------------------------------------------
' Print selected rush rows using the existing remake print template.
'------------------------------------------------------------------------------
Public Sub RushOrders_PrintSelectedRush(ByVal rowNumbers As Collection, ByVal copiesToPrint As Long)
    If rowNumbers Is Nothing Or rowNumbers.Count = 0 Then
        MsgBox "Select at least one rush row from the list.", vbExclamation, "Rush Orders"
        Exit Sub
    End If

    BuildAndPreviewRushSelectedPrintFromTemplate rowNumbers, "PRINT", copiesToPrint
End Sub

'------------------------------------------------------------------------------
' Shared print/preview worker.
' Builds a temporary workbook. Each rush form is its own worksheet.
' This avoids page-break and temp-sheet 1004 errors inside the master workbook.
'------------------------------------------------------------------------------
Private Sub RushOrders_PrintRowsInternal(ByVal rowNumbers As Collection, _
                                         ByVal selectedAction As String, _
                                         ByVal copiesToPrint As Long)
    Dim srcWs As Worksheet
    Dim printWb As Workbook
    Dim printWs As Worksheet
    Dim rowNumber As Variant
    Dim formNumber As Long
    Dim oldScreenUpdating As Boolean
    Dim oldDisplayAlerts As Boolean
    Dim oldEnableEvents As Boolean

    On Error GoTo ErrHandler

    If rowNumbers Is Nothing Or rowNumbers.Count = 0 Then
        MsgBox "There are no rush orders selected/currently marked.", vbInformation, "Rush Print"
        Exit Sub
    End If

    If copiesToPrint < 1 Then copiesToPrint = 1

    Set srcWs = RushOrders_GetDataSheet()

    oldScreenUpdating = Application.ScreenUpdating
    oldDisplayAlerts = Application.DisplayAlerts
    oldEnableEvents = Application.EnableEvents

    Application.ScreenUpdating = False
    Application.DisplayAlerts = False
    Application.EnableEvents = False

    Set printWb = Workbooks.Add(xlWBATWorksheet)

    formNumber = 0

    For Each rowNumber In rowNumbers
        If CLng(rowNumber) > 0 Then
            formNumber = formNumber + 1

            If formNumber = 1 Then
                Set printWs = printWb.Worksheets(1)
            Else
                Set printWs = printWb.Worksheets.Add(After:=printWb.Worksheets(printWb.Worksheets.Count))
            End If

            printWs.Name = RushOrders_SafeSheetName("Rush_" & _
                          RushOrders_CleanSheetNamePart(RushOrders_CellTextByHeader(srcWs, CLng(rowNumber), Array("Order Nr."))) & "_" & _
                          RushOrders_CleanSheetNamePart(RushOrders_CellTextByHeader(srcWs, CLng(rowNumber), Array("Item Nr.", "Item"))), _
                          printWb)

            RushOrders_BuildOnePrintForm srcWs, printWs, CLng(rowNumber), formNumber
        End If
    Next rowNumber

    If formNumber = 0 Then
        MsgBox "No printable rush rows were found.", vbInformation, "Rush Print"
        GoTo SafeExit
    End If

    Application.ScreenUpdating = True
    Application.DisplayAlerts = True
    Application.EnableEvents = True

    printWb.Activate

    If UCase$(Trim$(selectedAction)) = "PRINT" Then
        MsgBox "Load your unique rush paper now if needed." & vbCrLf & vbCrLf & _
               "The rush form itself also has a large red RUSH ORDER header.", _
               vbInformation, "Rush Print"

        printWb.PrintOut Copies:=copiesToPrint
    Else
        printWb.PrintPreview
    End If

SafeExit:
    On Error Resume Next
    Application.DisplayAlerts = False

    If Not printWb Is Nothing Then
        printWb.Close SaveChanges:=False
    End If

    Application.DisplayAlerts = oldDisplayAlerts
    Application.ScreenUpdating = oldScreenUpdating
    Application.EnableEvents = oldEnableEvents
    On Error GoTo 0

    Exit Sub

ErrHandler:
    MsgBox "Rush Print failed." & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbExclamation, "Rush Print"

    Resume SafeExit
End Sub

'------------------------------------------------------------------------------
' Builds one rush order form on one worksheet.
'------------------------------------------------------------------------------
Private Sub RushOrders_BuildOnePrintForm(ByVal srcWs As Worksheet, _
                                         ByVal printWs As Worksheet, _
                                         ByVal srcRow As Long, _
                                         ByVal formNumber As Long)
    Dim orderNumber As String
    Dim itemNumber As String
    Dim qtyText As String
    Dim dimText As String
    Dim customerText As String
    Dim routeText As String
    Dim rushNote As String
    Dim addedText As String
    Dim addedByText As String
    Dim glassHeader As String

    orderNumber = RushOrders_CellTextByHeader(srcWs, srcRow, Array("Order Nr."))
    itemNumber = RushOrders_CellTextByHeader(srcWs, srcRow, Array("Item Nr.", "Item"))
    qtyText = RushOrders_CellTextByHeader(srcWs, srcRow, Array("Qty.", "Qty", "Quantity"))
    dimText = RushOrders_CellTextByHeader(srcWs, srcRow, Array("Dimensions", "Dimension", "Dim", "Size"))
    customerText = RushOrders_CellTextByHeader(srcWs, srcRow, Array("Customer"))
    routeText = RushOrders_CellTextByHeader(srcWs, srcRow, Array("Route", "Rt", "Route Code"))
    rushNote = Trim$(CStr(srcWs.Cells(srcRow, RUSH_NOTE_COL).Value))
    addedText = Trim$(CStr(srcWs.Cells(srcRow, RUSH_DATE_COL).Text))
    addedByText = Trim$(CStr(srcWs.Cells(srcRow, RUSH_USER_COL).Value))
    glassHeader = RushOrders_FindGlassHeaderAbove(srcWs, srcRow)

    With printWs
        .Cells.Clear

        .Columns("A").ColumnWidth = 14
        .Columns("B").ColumnWidth = 14
        .Columns("C").ColumnWidth = 14
        .Columns("D").ColumnWidth = 14
        .Columns("E").ColumnWidth = 14
        .Columns("F").ColumnWidth = 14
        .Columns("G").ColumnWidth = 14
        .Columns("H").ColumnWidth = 14

        .rows.RowHeight = 21
        .Cells.Font.Name = "Calibri"
        .Cells.Font.Size = 11

        .Range("A1:H2").Merge
        .Range("A1").Value = "RUSH ORDER"
        .Range("A1").HorizontalAlignment = xlCenter
        .Range("A1").VerticalAlignment = xlCenter
        .Range("A1").Font.Bold = True
        .Range("A1").Font.Size = 34
        .Range("A1").Font.Color = RGB(255, 255, 255)
        .Range("A1").Interior.Color = RGB(192, 0, 0)

        .Range("A3:H3").Merge
        .Range("A3").Value = "FORM #" & formNumber & "     PRINTED: " & Format$(Now, "m/d/yyyy h:mm AM/PM")
        .Range("A3").HorizontalAlignment = xlCenter
        .Range("A3").Font.Bold = True
        .Range("A3").Interior.Color = RGB(255, 230, 230)

        RushOrders_WriteLabelValue printWs, 5, "Order Number", orderNumber
        RushOrders_WriteLabelValue printWs, 6, "Item Number", Format$(CLng(Val(itemNumber)), "000")
        RushOrders_WriteLabelValue printWs, 7, "Quantity", qtyText
        RushOrders_WriteLabelValue printWs, 8, "Dimensions", dimText
        RushOrders_WriteLabelValue printWs, 9, "Customer", customerText
        RushOrders_WriteLabelValue printWs, 10, "Route", routeText
        RushOrders_WriteLabelValue printWs, 11, "Glass Type", glassHeader
        RushOrders_WriteLabelValue printWs, 12, "Rush Added", addedText
        RushOrders_WriteLabelValue printWs, 13, "Rush Added By", addedByText

        .Range("A15:H15").Merge
        .Range("A15").Value = "RUSH NOTES"
        .Range("A15").Font.Bold = True
        .Range("A15").Font.Size = 14
        .Range("A15").Font.Color = RGB(255, 255, 255)
        .Range("A15").Interior.Color = RGB(192, 0, 0)

        .Range("A16:H20").Merge
        .Range("A16").Value = rushNote
        .Range("A16").WrapText = True
        .Range("A16").VerticalAlignment = xlTop
        .Range("A16").Interior.Color = RGB(255, 242, 204)

        .Range("A22:H22").Merge
        .Range("A22").Value = "SHOP CHECKOFF"
        .Range("A22").Font.Bold = True
        .Range("A22").Font.Size = 14
        .Range("A22").Font.Color = RGB(255, 255, 255)
        .Range("A22").Interior.Color = RGB(192, 0, 0)

        .Range("A24").Value = "[ ] Pulled"
        .Range("C24").Value = "[ ] Checked"
        .Range("E24").Value = "[ ] Loaded"
        .Range("G24").Value = "[ ] Complete"

        .Range("A26:H27").Merge
        .Range("A26").Value = "Signature / Initials: ___________________________________________"
        .Range("A26").Font.Bold = True

        With .Range("A1:H29")
            .Borders.LineStyle = xlContinuous
            .Borders.Weight = xlThin
        End With

        With .Range("A1:H29").Borders(xlEdgeLeft)
            .LineStyle = xlContinuous
            .Weight = xlThick
            .Color = RGB(192, 0, 0)
        End With

        With .Range("A1:H29").Borders(xlEdgeRight)
            .LineStyle = xlContinuous
            .Weight = xlThick
            .Color = RGB(192, 0, 0)
        End With

        With .Range("A1:H29").Borders(xlEdgeTop)
            .LineStyle = xlContinuous
            .Weight = xlThick
            .Color = RGB(192, 0, 0)
        End With

        With .Range("A1:H29").Borders(xlEdgeBottom)
            .LineStyle = xlContinuous
            .Weight = xlThick
            .Color = RGB(192, 0, 0)
        End With

        RushOrders_SafePageSetup printWs
    End With
End Sub

Private Sub RushOrders_WriteLabelValue(ByVal ws As Worksheet, _
                                       ByVal rowNum As Long, _
                                       ByVal labelText As String, _
                                       ByVal valueText As String)
    With ws
        .Range("A" & rowNum & ":B" & rowNum).Merge
        .Range("C" & rowNum & ":H" & rowNum).Merge

        .Range("A" & rowNum).Value = labelText & ":"
        .Range("A" & rowNum).Font.Bold = True
        .Range("A" & rowNum).Interior.Color = RGB(217, 217, 217)

        .Range("C" & rowNum).Value = valueText
        .Range("C" & rowNum).Font.Bold = True
        .Range("C" & rowNum).WrapText = True
    End With
End Sub

'------------------------------------------------------------------------------
' PageSetup can throw runtime 1004 depending on printer driver availability.
' This makes page setup best-effort instead of fatal.
'------------------------------------------------------------------------------
Private Sub RushOrders_SafePageSetup(ByVal ws As Worksheet)
    On Error Resume Next

    With ws.PageSetup
        .PrintArea = "$A$1:$H$29"
        .Orientation = xlPortrait
        .PaperSize = xlPaperLetter
        .Zoom = False
        .FitToPagesWide = 1
        .FitToPagesTall = 1
        .CenterHorizontally = True
        .CenterVertically = False
        .LeftMargin = Application.InchesToPoints(0.25)
        .RightMargin = Application.InchesToPoints(0.25)
        .TopMargin = Application.InchesToPoints(0.25)
        .BottomMargin = Application.InchesToPoints(0.25)
        .HeaderMargin = Application.InchesToPoints(0.1)
        .FooterMargin = Application.InchesToPoints(0.1)
        .CenterFooter = "RUSH ORDER"
    End With

    On Error GoTo 0
End Sub

Private Function RushOrders_AllCurrentRushSourceRows() As Collection
    Dim rushRows As Collection
    Dim out As New Collection
    Dim item As Variant

    Set rushRows = RushOrders_GetRushRows()

    For Each item In rushRows
        out.Add CLng(item("row"))
    Next item

    Set RushOrders_AllCurrentRushSourceRows = out
End Function

Private Function RushOrders_GetDataSheet() As Worksheet
    On Error Resume Next
    Set RushOrders_GetDataSheet = ThisWorkbook.Worksheets(RUSH_DATA_SHEET_NAME)
    On Error GoTo 0

    If RushOrders_GetDataSheet Is Nothing Then
        Err.Raise vbObjectError + 9300, "RushOrders_GetDataSheet", _
                  "Could not find sheet '" & RUSH_DATA_SHEET_NAME & "'."
    End If
End Function

Private Sub RushOrders_EnsureRushColumns(ByVal ws As Worksheet)
    If ws Is Nothing Then Exit Sub

    On Error Resume Next
    ws.Unprotect Password:=""
    On Error GoTo 0

    ws.Cells(1, RUSH_STATUS_COL).Value = "Rush"
    ws.Cells(1, RUSH_NOTE_COL).Value = "Rush Note"
    ws.Cells(1, RUSH_DATE_COL).Value = "Rush Added At"
    ws.Cells(1, RUSH_USER_COL).Value = "Rush Added By"

    With ws.Range(ws.Cells(1, RUSH_STATUS_COL), ws.Cells(1, RUSH_USER_COL))
        .Font.Bold = True
        .Interior.Color = RGB(192, 0, 0)
        .Font.Color = RGB(255, 255, 255)
    End With

    ws.Columns(RUSH_STATUS_COL).ColumnWidth = 10
    ws.Columns(RUSH_NOTE_COL).ColumnWidth = 28
    ws.Columns(RUSH_DATE_COL).ColumnWidth = 18
    ws.Columns(RUSH_USER_COL).ColumnWidth = 18
End Sub

Private Sub RushOrders_ApplyRushFormatting(ByVal ws As Worksheet)
    Dim orderHdr As Range
    Dim orderCol As Long
    Dim firstDataRow As Long
    Dim lastRow As Long
    Dim rng As Range
    Dim i As Long
    Dim formulaText As String
    Dim existingFormula As String

    If ws Is Nothing Then Exit Sub

    Set orderHdr = RushOrders_FindHeaderCell(ws, Array("Order Nr."), DELIVERY_HEADER_COLS, HEADER_SEARCH_TOP_ROWS)
    If orderHdr Is Nothing Then Exit Sub

    orderCol = orderHdr.Column
    firstDataRow = orderHdr.Row + 1
    lastRow = ws.Cells(ws.rows.Count, orderCol).End(xlUp).Row

    If lastRow < firstDataRow Then Exit Sub

    Set rng = ws.Range("A" & firstDataRow & ":N" & lastRow)
    formulaText = "=$AX" & firstDataRow & "=""" & RUSH_FLAG_TEXT & """"

    On Error Resume Next

    For i = rng.FormatConditions.Count To 1 Step -1
        existingFormula = vbNullString
        existingFormula = rng.FormatConditions(i).Formula1

        If InStr(1, existingFormula, "$AX", vbTextCompare) > 0 _
           And InStr(1, existingFormula, RUSH_FLAG_TEXT, vbTextCompare) > 0 Then
            rng.FormatConditions(i).Delete
        End If
    Next i

    On Error GoTo 0

    With rng.FormatConditions.Add(Type:=xlExpression, Formula1:=formulaText)
        .Interior.Color = RGB(255, 199, 206)
        .Font.Color = RGB(156, 0, 6)
        .Font.Bold = True
        .StopIfTrue = False
    End With
End Sub

Private Function RushOrders_UpdateMatchingRows(ByVal ws As Worksheet, _
                                               ByVal orderNumber As Long, _
                                               ByVal itemNumber As Long, _
                                               ByVal makeRush As Boolean, _
                                               ByVal rushNote As String) As Long
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim orderCol As Long
    Dim itemCol As Long
    Dim firstDataRow As Long
    Dim lastRow As Long
    Dim r As Long
    Dim rowOrder As Long
    Dim rowItem As Long
    Dim updatedCount As Long

    Set orderHdr = RushOrders_FindHeaderCell(ws, Array("Order Nr."), DELIVERY_HEADER_COLS, HEADER_SEARCH_TOP_ROWS)
    Set itemHdr = RushOrders_FindHeaderCell(ws, Array("Item Nr.", "Item"), DELIVERY_HEADER_COLS, HEADER_SEARCH_TOP_ROWS)

    If orderHdr Is Nothing Or itemHdr Is Nothing Then
        Err.Raise vbObjectError + 9301, "RushOrders_UpdateMatchingRows", _
                  "Could not find Order Nr. / Item Nr. headers on Delivery List."
    End If

    orderCol = orderHdr.Column
    itemCol = itemHdr.Column
    firstDataRow = orderHdr.Row + 1
    lastRow = ws.Cells(ws.rows.Count, orderCol).End(xlUp).Row

    For r = firstDataRow To lastRow
        rowOrder = RushOrders_SafeLong(ws.Cells(r, orderCol).Value)
        rowItem = RushOrders_SafeLong(ws.Cells(r, itemCol).Value)

        If rowOrder = orderNumber Then
            If itemNumber = 0 Or rowItem = itemNumber Then
                If makeRush Then
                    ws.Cells(r, RUSH_STATUS_COL).Value = RUSH_FLAG_TEXT
                    ws.Cells(r, RUSH_NOTE_COL).Value = rushNote
                    ws.Cells(r, RUSH_DATE_COL).Value = Now
                    ws.Cells(r, RUSH_DATE_COL).NumberFormat = "m/d/yyyy h:mm AM/PM"
                    ws.Cells(r, RUSH_USER_COL).Value = Application.userName
                Else
                    ws.Range(ws.Cells(r, RUSH_STATUS_COL), ws.Cells(r, RUSH_USER_COL)).ClearContents
                End If

                updatedCount = updatedCount + 1
            End If
        End If
    Next r

    RushOrders_UpdateMatchingRows = updatedCount
End Function

Private Function RushOrders_ParseTokens(ByVal rawText As String) As Collection
    Dim cleaned As String
    Dim parts() As String
    Dim i As Long
    Dim token As String
    Dim out As New Collection

    cleaned = CStr(rawText)
    cleaned = Replace$(cleaned, vbCrLf, ",")
    cleaned = Replace$(cleaned, vbCr, ",")
    cleaned = Replace$(cleaned, vbLf, ",")
    cleaned = Replace$(cleaned, vbTab, ",")
    cleaned = Replace$(cleaned, ";", ",")
    cleaned = Replace$(cleaned, " ", ",")

    Do While InStr(1, cleaned, ",,", vbBinaryCompare) > 0
        cleaned = Replace$(cleaned, ",,", ",")
    Loop

    parts = Split(cleaned, ",")

    For i = LBound(parts) To UBound(parts)
        token = Trim$(parts(i))
        If Len(token) > 0 Then out.Add token
    Next i

    Set RushOrders_ParseTokens = out
End Function

Private Function RushOrders_ParseOneToken(ByVal tokenText As String, _
                                          ByRef orderNumber As Long, _
                                          ByRef itemNumber As Long) As Boolean
    Dim s As String
    Dim parts() As String

    s = UCase$(Trim$(tokenText))
    s = Replace$(s, "*", vbNullString)
    s = Replace$(s, "#", vbNullString)

    orderNumber = 0
    itemNumber = 0

    If Len(s) = 16 And s Like "T200############" Then
        orderNumber = CLng(Mid$(s, 5, 6))
        itemNumber = CLng(Mid$(s, 11, 3))
        RushOrders_ParseOneToken = True
        Exit Function
    End If

    s = Replace$(s, "_", "-")
    s = Replace$(s, "/", "-")
    s = Replace$(s, ".", "-")

    If InStr(1, s, "-", vbBinaryCompare) > 0 Then
        parts = Split(s, "-")
        If UBound(parts) >= 1 Then
            orderNumber = CLng(Val(parts(0)))
            itemNumber = CLng(Val(parts(1)))
        End If
    Else
        orderNumber = CLng(Val(s))
        itemNumber = 0
    End If

    RushOrders_ParseOneToken = (orderNumber > 0)
End Function

Private Function RushOrders_FindHeaderCell(ByVal ws As Worksheet, _
                                           ByVal headerNames As Variant, _
                                           ByVal colAddress As String, _
                                           ByVal maxRows As Long) As Range
    Dim searchRange As Range
    Dim f As Range
    Dim nm As Variant

    If ws Is Nothing Then Exit Function

    Set searchRange = Intersect(ws.Range("1:" & maxRows), ws.Columns(colAddress))
    If searchRange Is Nothing Then Exit Function

    For Each nm In headerNames
        Set f = searchRange.Find(What:=CStr(nm), LookIn:=xlValues, LookAt:=xlWhole, MatchCase:=False)
        If Not f Is Nothing Then
            Set RushOrders_FindHeaderCell = f
            Exit Function
        End If
    Next nm

    For Each nm In headerNames
        Set f = searchRange.Find(What:=CStr(nm), LookIn:=xlValues, LookAt:=xlPart, MatchCase:=False)
        If Not f Is Nothing Then
            Set RushOrders_FindHeaderCell = f
            Exit Function
        End If
    Next nm
End Function

Private Function RushOrders_CellTextByHeader(ByVal ws As Worksheet, _
                                             ByVal rowNum As Long, _
                                             ByVal headerNames As Variant) As String
    Dim hdr As Range

    Set hdr = RushOrders_FindHeaderCell(ws, headerNames, DELIVERY_HEADER_COLS, HEADER_SEARCH_TOP_ROWS)

    If Not hdr Is Nothing Then
        RushOrders_CellTextByHeader = Trim$(CStr(ws.Cells(rowNum, hdr.Column).Text))
    End If
End Function

Private Function RushOrders_FindGlassHeaderAbove(ByVal ws As Worksheet, ByVal rowNum As Long) As String
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim orderCol As Long
    Dim itemCol As Long
    Dim r As Long
    Dim leftText As String

    Set orderHdr = RushOrders_FindHeaderCell(ws, Array("Order Nr."), DELIVERY_HEADER_COLS, HEADER_SEARCH_TOP_ROWS)
    Set itemHdr = RushOrders_FindHeaderCell(ws, Array("Item Nr.", "Item"), DELIVERY_HEADER_COLS, HEADER_SEARCH_TOP_ROWS)

    If orderHdr Is Nothing Or itemHdr Is Nothing Then Exit Function

    orderCol = orderHdr.Column
    itemCol = itemHdr.Column

    For r = rowNum - 1 To orderHdr.Row + 1 Step -1
        leftText = Trim$(CStr(ws.Cells(r, 1).Value))

        If Len(leftText) > 0 _
           And Len(Trim$(CStr(ws.Cells(r, orderCol).Value))) = 0 _
           And Len(Trim$(CStr(ws.Cells(r, itemCol).Value))) = 0 Then
            RushOrders_FindGlassHeaderAbove = leftText
            Exit Function
        End If
    Next r
End Function

Private Function RushOrders_SafeLong(ByVal valueIn As Variant) As Long
    Dim s As String

    If IsError(valueIn) Then Exit Function

    s = CStr(valueIn)
    s = Replace$(s, ",", vbNullString)
    s = Trim$(s)

    If Len(s) = 0 Then Exit Function

    RushOrders_SafeLong = CLng(Val(s))
End Function

Private Function RushOrders_CleanSheetNamePart(ByVal valueText As String) As String
    Dim s As String

    s = Trim$(CStr(valueText))
    s = Replace$(s, ",", vbNullString)
    s = Replace$(s, " ", vbNullString)
    s = Replace$(s, ":", vbNullString)
    s = Replace$(s, "\", vbNullString)
    s = Replace$(s, "/", vbNullString)
    s = Replace$(s, "?", vbNullString)
    s = Replace$(s, "*", vbNullString)
    s = Replace$(s, "[", vbNullString)
    s = Replace$(s, "]", vbNullString)

    If Len(s) = 0 Then s = "Row"

    RushOrders_CleanSheetNamePart = s
End Function

Private Function RushOrders_SafeSheetName(ByVal baseName As String, ByVal wb As Workbook) As String
    Dim s As String
    Dim candidate As String
    Dim n As Long

    s = RushOrders_CleanSheetNamePart(baseName)
    If Len(s) > 25 Then s = Left$(s, 25)

    candidate = s
    n = 1

    Do While RushOrders_SheetExists(candidate, wb)
        n = n + 1
        candidate = Left$(s, 25) & "_" & CStr(n)
        If Len(candidate) > 31 Then candidate = Left$(candidate, 31)
    Loop

    RushOrders_SafeSheetName = candidate
End Function

Private Function RushOrders_SheetExists(ByVal sheetName As String, ByVal wb As Workbook) As Boolean
    Dim ws As Worksheet

    On Error Resume Next
    Set ws = wb.Worksheets(sheetName)
    RushOrders_SheetExists = Not ws Is Nothing
    On Error GoTo 0
End Function

Public Function RushOrders_PromptCopies(Optional ByVal titleText As String = "Rush Print Copies") As Long
    Dim v As Variant
    Dim n As Long

    v = Application.InputBox( _
            Prompt:="How many copies would you like to print?", _
            Title:=titleText, _
            Default:=1, _
            Type:=1)

    If VarType(v) = vbBoolean Then
        RushOrders_PromptCopies = 0
        Exit Function
    End If

    n = CLng(Val(v))

    If n < 1 Then
        MsgBox "Please enter a whole number greater than 0.", vbExclamation, titleText
        RushOrders_PromptCopies = 0
        Exit Function
    End If

    RushOrders_PromptCopies = n
End Function

