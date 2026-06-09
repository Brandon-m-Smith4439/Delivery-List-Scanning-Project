Attribute VB_Name = "modIndianTrailBayAssignment"
Option Explicit

'==============================================================================
' Module: modIndianTrailBayAssignment
' Workbook: Multi User Scanner Queue Testing.xlsm / Master Delivery List
'
' What this module does:
'   Handles Indian Trail bay assignment/display logic for inbound receiving,
'   including row classification and calls to the bay assignment flow.
'
' Why this module exists:
'   Indian Trail needs persistent bay information so receiving can keep track
'   of where glass is physically staged after scans are processed.
'
' Commenting standard used in this rewrite:
'   Procedure comments explain both what the code does and why that
'   behavior matters in the scanning / SharePoint / Power Automate workflow.
'   The code logic and public signatures are intentionally kept stable; this
'   pass is primarily a readability, maintainability, and safety pass.
'==============================================================================



'=========================================================
' modIndianTrailBayAssignment
' Phase 3: assign/get Indian Trail bay from SharePoint after successful scans.
'
' Enabled immediately because this is a safe testing environment.
' SDI is still Phase 4.
' Manual bay clearing is later.
'=========================================================

Private Const ITBA_DATA_SHEET_NAME As String = "Delivery List"
Private Const ITBA_SEND_SHEET_NAME As String = "Outbound - Airport Rd"
Private Const ITBA_INDIAN_TRAIL_SHEET_NAME As String = "Inbound - Indian Trail"
Private Const ITBA_GREENVILLE_SHEET_NAME As String = "Inbound - Greenville"
Private Const ITBA_CPU_SHEET_NAME As String = "Customer Pickup"

Private Const ITBA_GREENVILLE_CUSTOMER_TEXT As String = "BFS East Greenville SC MW"
Private Const ITBA_CPU_ROUTE_TEXT As String = "CPU"

Private Const ITBA_ENABLE_BAY_ASSIGNMENT As Boolean = True

Private Const ITBA_OVERSIZED_MAX_LENGTH_REFERENCE As Double = 105#
Private Const ITBA_OVERSIZED_MAX_WIDTH_REFERENCE As Double = 56#
Private Const ITBA_BLOCK_POSSIBLE_OVERSIZED As Boolean = False

'------------------------------------------------------------------------------
' Procedure: IndianTrailHandleBayAssignmentForQueueItem
' Scope: Public Function
'
' What it does:
'   Handles queue/request state used by the shared ScanQueue workflow for
'   IndianTrailHandleBayAssignmentForQueueItem.
'
' Why it exists:
'   Indian Trail receiving depends on bay visibility so operators can
'   physically locate glass after it is scanned in.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function IndianTrailHandleBayAssignmentForQueueItem(ByVal dataWs As Worksheet, _
                                                           ByVal modeText As String, _
                                                           ByVal targetSheetName As String, _
                                                           ByVal orderNumber As Long, _
                                                           ByVal itemNumber As Long, _
                                                           ByVal barcodeText As String, _
                                                           ByVal stationName As String, _
                                                           ByRef resultMessage As String) As Boolean
    Dim scanStage As String
    Dim rowNum As Long
    Dim headerText As String
    Dim headerRow As Long
    Dim glassCategory As String
    Dim bayCategory As String
    Dim routingWarning As String
    Dim dimensionsText As String
    Dim widthInches As Double
    Dim heightInches As Double
    Dim maxDimensionInches As Double
    Dim possibleOversized As Boolean
    Dim notesText As String
    Dim response As Object
    Dim bayDisplayName As String
    Dim flowMessage As String
    Dim deliveryListKey As String

    On Error GoTo FailSoft

    IndianTrailHandleBayAssignmentForQueueItem = False

    If Not ITBA_ENABLE_BAY_ASSIGNMENT Then Exit Function
    If dataWs Is Nothing Then Exit Function
    If orderNumber <= 0 Then Exit Function

    modeText = UCase$(Trim$(CStr(modeText)))
    targetSheetName = Trim$(CStr(targetSheetName))

    If Not ITBA_ShouldHandleScan(dataWs, modeText, targetSheetName, orderNumber, itemNumber) Then Exit Function

    If modeText = "SEND" Then
        scanStage = "OUTBOUND_PREASSIGN"
    ElseIf modeText = "RECV" Then
        scanStage = "INDIAN_TRAIL_RECEIVE"
    Else
        Exit Function
    End If

    rowNum = ITBA_FindRowByOrderItem(dataWs, orderNumber, itemNumber)
    If rowNum = 0 Then Exit Function

    ITBA_GetHeaderForDeliveryRow dataWs, rowNum, headerText, headerRow
    ITBA_ClassifyGlassHeader headerText, glassCategory, bayCategory, routingWarning

    dimensionsText = ITBA_GetDimensionsForRow(dataWs, rowNum)

    If ITBA_ParseDimensionsInches(dimensionsText, widthInches, heightInches, maxDimensionInches) Then
        possibleOversized = ITBA_PossibleOversized(widthInches, heightInches)
    End If

    notesText = vbNullString

    If Len(routingWarning) > 0 Then notesText = routingWarning

    If possibleOversized Then
        If Len(notesText) > 0 Then notesText = notesText & " | "
        notesText = notesText & "Possible oversized by reference dimensions; receiving must decide manually."

        If ITBA_BLOCK_POSSIBLE_OVERSIZED Then
            glassCategory = "ManualException"
            bayCategory = "ManualException"
        End If
    End If

    deliveryListKey = "DL_UNKNOWN"
    On Error Resume Next
    deliveryListKey = GetCurrentDeliveryListKey()
    On Error GoTo FailSoft

    If Len(Trim$(deliveryListKey)) = 0 Then deliveryListKey = "DL_UNKNOWN"

    Set response = PA_IndianTrailBayAssignOrGet( _
                    deliveryListKey, _
                    orderNumber, _
                    CStr(orderNumber), _
                    itemNumber, _
                    headerText, _
                    glassCategory, _
                    bayCategory, _
                    scanStage, _
                    targetSheetName, _
                    stationName, _
                    ThisWorkbook.Name, _
                    barcodeText, _
                    notesText)

    If response Is Nothing Then Exit Function

    bayDisplayName = PA_DictText(response, "bayDisplayName")
    flowMessage = PA_DictText(response, "message")

    If Len(bayDisplayName) > 0 Then
        ITBA_WriteBayDisplayNameForOrder dataWs, orderNumber, bayDisplayName
    End If

    If Len(flowMessage) > 0 Then
        If Len(resultMessage) > 0 Then
            resultMessage = resultMessage & " | " & flowMessage
        Else
            resultMessage = flowMessage
        End If
    ElseIf Len(bayDisplayName) > 0 Then
        If Len(resultMessage) > 0 Then
            If modeText = "RECV" Then
                resultMessage = resultMessage & " | Indian Trail Bay: " & bayDisplayName
            Else
                resultMessage = resultMessage & " | Preassigned Indian Trail Bay: " & bayDisplayName
            End If
        Else
            resultMessage = "Indian Trail Bay: " & bayDisplayName
        End If
    End If

    If response.Exists("ok") Then
        IndianTrailHandleBayAssignmentForQueueItem = CBool(response("ok"))
    End If

    Exit Function

FailSoft:
    If Len(resultMessage) > 0 Then
        resultMessage = resultMessage & " | Indian Trail bay assignment warning: " & Err.Description
    Else
        resultMessage = "Indian Trail bay assignment warning: " & Err.Description
    End If

    Err.Clear
End Function

'------------------------------------------------------------------------------
' Procedure: ITBA_ShouldHandleScan
' Scope: Private Function
'
' What it does:
'   Performs the workbook-specific step named ITBA_ShouldHandleScan inside
'   modIndianTrailBayAssignment.
'
' Why it exists:
'   Indian Trail needs persistent bay information so receiving can keep track
'   of where glass is physically staged after scans are processed.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function ITBA_ShouldHandleScan(ByVal dataWs As Worksheet, _
                                       ByVal modeText As String, _
                                       ByVal targetSheetName As String, _
                                       ByVal orderNumber As Long, _
                                       ByVal itemNumber As Long) As Boolean
    Dim rowNum As Long
    Dim targetUpper As String

    ITBA_ShouldHandleScan = False

    If dataWs Is Nothing Then Exit Function
    If orderNumber <= 0 Then Exit Function

    modeText = UCase$(Trim$(CStr(modeText)))
    targetSheetName = Trim$(CStr(targetSheetName))
    targetUpper = UCase$(targetSheetName)

    Select Case modeText
        Case "SEND"
            If targetUpper <> UCase$(ITBA_SEND_SHEET_NAME) Then Exit Function

            rowNum = ITBA_FindRowByOrderItem(dataWs, orderNumber, itemNumber)
            If rowNum = 0 Then Exit Function

            If ITBA_RowIsGreenville(dataWs, rowNum) Then Exit Function
            If ITBA_RowIsCPU(dataWs, rowNum) Then Exit Function

            ITBA_ShouldHandleScan = True

        Case "RECV"
            If targetUpper <> UCase$(ITBA_INDIAN_TRAIL_SHEET_NAME) Then Exit Function

            rowNum = ITBA_FindRowByOrderItem(dataWs, orderNumber, itemNumber)
            If rowNum = 0 Then Exit Function

            If ITBA_RowIsGreenville(dataWs, rowNum) Then Exit Function
            If ITBA_RowIsCPU(dataWs, rowNum) Then Exit Function

            ITBA_ShouldHandleScan = True
    End Select
End Function

'------------------------------------------------------------------------------
' Procedure: ITBA_RowIsGreenville
' Scope: Private Function
'
' What it does:
'   Identifies, filters, formats, or routes Greenville-specific delivery rows
'   for ITBA_RowIsGreenville.
'
' Why it exists:
'   Greenville orders are separated from standard Indian Trail inbound work,
'   so those rows need consistent classification across sheets, print/export,
'   and snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function ITBA_RowIsGreenville(ByVal ws As Worksheet, ByVal rowNum As Long) As Boolean
    Dim customerCol As Long
    Dim customerText As String

    customerCol = ITBA_FindHeaderCol(ws, Array("Customer"), "A:N", 250)
    If customerCol <= 0 Then Exit Function

    customerText = UCase$(Trim$(CStr(ws.Cells(rowNum, customerCol).Value)))
    ITBA_RowIsGreenville = (InStr(1, customerText, UCase$(ITBA_GREENVILLE_CUSTOMER_TEXT), vbTextCompare) > 0)
End Function

'------------------------------------------------------------------------------
' Procedure: ITBA_RowIsCPU
' Scope: Private Function
'
' What it does:
'   Identifies, filters, formats, or routes Customer Pickup rows for
'   ITBA_RowIsCPU.
'
' Why it exists:
'   Customer Pickup orders follow a separate operational path, so they cannot
'   be mixed into normal inbound/Greenville handling by accident.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function ITBA_RowIsCPU(ByVal ws As Worksheet, ByVal rowNum As Long) As Boolean
    Dim routeCol As Long
    Dim routeText As String

    routeCol = ITBA_FindHeaderCol(ws, Array("Route", "Rt", "Route Code"), "A:N", 250)
    If routeCol <= 0 Then routeCol = 12

    routeText = UCase$(Trim$(CStr(ws.Cells(rowNum, routeCol).Value)))
    ITBA_RowIsCPU = (routeText = UCase$(ITBA_CPU_ROUTE_TEXT))
End Function

'------------------------------------------------------------------------------
' Procedure: ITBA_FindRowByOrderItem
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   ITBA_FindRowByOrderItem.
'
' Why it exists:
'   Rows may represent real orders, section headers, remakes, Greenville work,
'   Customer Pickup work, or updated rows; each type needs different handling.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function ITBA_FindRowByOrderItem(ByVal ws As Worksheet, ByVal orderNumber As Long, ByVal itemNumber As Long) As Long
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim orderCol As Long
    Dim itemCol As Long
    Dim firstRow As Long
    Dim lastRow As Long
    Dim rng As Range
    Dim f As Range
    Dim firstAddr As String

    Set orderHdr = ITBA_FindHeaderCell(ws, Array("Order Nr."), "A:N", 250)
    Set itemHdr = ITBA_FindHeaderCell(ws, Array("Item Nr.", "Item"), "A:N", 250)

    If orderHdr Is Nothing Or itemHdr Is Nothing Then Exit Function

    orderCol = orderHdr.Column
    itemCol = itemHdr.Column
    firstRow = orderHdr.Row + 1
    lastRow = ws.Cells(ws.rows.Count, orderCol).End(xlUp).Row

    If lastRow < firstRow Then Exit Function

    Set rng = ws.Range(ws.Cells(firstRow, orderCol), ws.Cells(lastRow, orderCol))
    Set f = rng.Find(What:=CStr(orderNumber), LookIn:=xlValues, LookAt:=xlWhole)

    If Not f Is Nothing Then
        firstAddr = f.Address

        Do
            If IsNumeric(ws.Cells(f.Row, itemCol).Value) Then
                If CLng(ws.Cells(f.Row, itemCol).Value) = itemNumber Then
                    ITBA_FindRowByOrderItem = f.Row
                    Exit Function
                End If
            End If

            Set f = rng.FindNext(f)
        Loop While Not f Is Nothing And f.Address <> firstAddr
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: ITBA_GetHeaderForDeliveryRow
' Scope: Private Sub
'
' What it does:
'   Finds, writes, validates, or uses worksheet header cells for
'   ITBA_GetHeaderForDeliveryRow.
'
' Why it exists:
'   Header locations can move during import/rebuild, so the code uses header
'   discovery to target the correct columns instead of guessing.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ITBA_GetHeaderForDeliveryRow(ByVal ws As Worksheet, _
                                         ByVal rowNum As Long, _
                                         ByRef headerText As String, _
                                         ByRef headerRow As Long)
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim orderCol As Long
    Dim itemCol As Long
    Dim r As Long

    headerText = vbNullString
    headerRow = 0

    Set orderHdr = ITBA_FindHeaderCell(ws, Array("Order Nr."), "A:N", 250)
    Set itemHdr = ITBA_FindHeaderCell(ws, Array("Item Nr.", "Item"), "A:N", 250)

    If orderHdr Is Nothing Or itemHdr Is Nothing Then Exit Sub

    orderCol = orderHdr.Column
    itemCol = itemHdr.Column

    For r = rowNum - 1 To orderHdr.Row + 1 Step -1
        If ITBA_RowIsGlassHeader(ws, r, orderCol, itemCol) Then
            headerText = Trim$(CStr(ws.Cells(r, 1).Value))
            headerRow = r
            Exit Sub
        End If
    Next r
End Sub

'------------------------------------------------------------------------------
' Procedure: ITBA_RowIsGlassHeader
' Scope: Private Function
'
' What it does:
'   Finds, writes, validates, or uses worksheet header cells for
'   ITBA_RowIsGlassHeader.
'
' Why it exists:
'   Header locations can move during import/rebuild, so the code uses header
'   discovery to target the correct columns instead of guessing.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function ITBA_RowIsGlassHeader(ByVal ws As Worksheet, ByVal rowNum As Long, ByVal orderCol As Long, ByVal itemCol As Long) As Boolean
    Dim titleText As String
    Dim titleUpper As String

    titleText = Trim$(CStr(ws.Cells(rowNum, 1).Value))
    If Len(titleText) = 0 Then Exit Function

    If Len(Trim$(CStr(ws.Cells(rowNum, orderCol).Value))) > 0 Then Exit Function
    If Len(Trim$(CStr(ws.Cells(rowNum, itemCol).Value))) > 0 Then Exit Function

    titleUpper = UCase$(titleText)

    ITBA_RowIsGlassHeader = _
        (InStr(1, titleUpper, "TEMPER", vbTextCompare) > 0) Or _
        (InStr(1, titleUpper, "ANNEAL", vbTextCompare) > 0) Or _
        (InStr(1, titleUpper, "MIRROR", vbTextCompare) > 0) Or _
        (InStr(1, titleUpper, "BFS", vbTextCompare) > 0) Or _
        (InStr(1, titleUpper, "CORAL", vbTextCompare) > 0)
End Function

'------------------------------------------------------------------------------
' Procedure: ITBA_ClassifyGlassHeader
' Scope: Private Sub
'
' What it does:
'   Finds, writes, validates, or uses worksheet header cells for
'   ITBA_ClassifyGlassHeader.
'
' Why it exists:
'   Header locations can move during import/rebuild, so the code uses header
'   discovery to target the correct columns instead of guessing.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ITBA_ClassifyGlassHeader(ByVal headerText As String, _
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
        routingWarning = "Coral header - not auto-assigned by Indian Trail bay logic"

    Else
        routingWarning = "Unknown glass header - manual bay routing required"
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: ITBA_GetDimensionsForRow
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   ITBA_GetDimensionsForRow.
'
' Why it exists:
'   Rows may represent real orders, section headers, remakes, Greenville work,
'   Customer Pickup work, or updated rows; each type needs different handling.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function ITBA_GetDimensionsForRow(ByVal ws As Worksheet, ByVal rowNum As Long) As String
    Dim dimCol As Long

    dimCol = ITBA_FindHeaderCol(ws, Array("Dimensions", "Dimension", "Dim", "Size"), "A:N", 250)
    If dimCol > 0 Then ITBA_GetDimensionsForRow = Trim$(CStr(ws.Cells(rowNum, dimCol).Value))
End Function

'------------------------------------------------------------------------------
' Procedure: ITBA_ParseDimensionsInches
' Scope: Private Function
'
' What it does:
'   Performs the workbook-specific step named ITBA_ParseDimensionsInches
'   inside modIndianTrailBayAssignment.
'
' Why it exists:
'   Indian Trail needs persistent bay information so receiving can keep track
'   of where glass is physically staged after scans are processed.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function ITBA_ParseDimensionsInches(ByVal dimensionsText As String, _
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

    widthInches = ITBA_ParseSingleInchValue(CStr(parts(0)))
    heightInches = ITBA_ParseSingleInchValue(CStr(parts(1)))

    If widthInches <= 0 Or heightInches <= 0 Then Exit Function

    If widthInches >= heightInches Then
        maxDimensionInches = widthInches
    Else
        maxDimensionInches = heightInches
    End If

    ITBA_ParseDimensionsInches = True
End Function

'------------------------------------------------------------------------------
' Procedure: ITBA_ParseSingleInchValue
' Scope: Private Function
'
' What it does:
'   Performs the workbook-specific step named ITBA_ParseSingleInchValue inside
'   modIndianTrailBayAssignment.
'
' Why it exists:
'   Indian Trail needs persistent bay information so receiving can keep track
'   of where glass is physically staged after scans are processed.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function ITBA_ParseSingleInchValue(ByVal valueText As String) As Double
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

    ITBA_ParseSingleInchValue = total
End Function

'------------------------------------------------------------------------------
' Procedure: ITBA_PossibleOversized
' Scope: Private Function
'
' What it does:
'   Performs the workbook-specific step named ITBA_PossibleOversized inside
'   modIndianTrailBayAssignment.
'
' Why it exists:
'   Indian Trail needs persistent bay information so receiving can keep track
'   of where glass is physically staged after scans are processed.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function ITBA_PossibleOversized(ByVal widthInches As Double, ByVal heightInches As Double) As Boolean
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

    ITBA_PossibleOversized = (maxDim >= ITBA_OVERSIZED_MAX_LENGTH_REFERENCE Or minDim >= ITBA_OVERSIZED_MAX_WIDTH_REFERENCE)
End Function

'------------------------------------------------------------------------------
' Procedure: ITBA_WriteBayDisplayNameForOrder
' Scope: Private Sub
'
' What it does:
'   Performs the workbook-specific step named ITBA_WriteBayDisplayNameForOrder
'   inside modIndianTrailBayAssignment.
'
' Why it exists:
'   Indian Trail receiving depends on bay visibility so operators can
'   physically locate glass after it is scanned in.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ITBA_WriteBayDisplayNameForOrder(ByVal ws As Worksheet, ByVal orderNumber As Long, ByVal bayDisplayName As String)
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim orderCol As Long
    Dim itemCol As Long
    Dim bayCol As Long
    Dim firstRow As Long
    Dim lastRow As Long
    Dim r As Long

    bayDisplayName = Trim$(CStr(bayDisplayName))
    If Len(bayDisplayName) = 0 Then Exit Sub

    Set orderHdr = ITBA_FindHeaderCell(ws, Array("Order Nr."), "A:N", 250)
    Set itemHdr = ITBA_FindHeaderCell(ws, Array("Item Nr.", "Item"), "A:N", 250)

    If orderHdr Is Nothing Or itemHdr Is Nothing Then Exit Sub

    orderCol = orderHdr.Column
    itemCol = itemHdr.Column

    bayCol = ITBA_FindHeaderCol(ws, Array("Bay Nr.", "Bay No.", "Bay Number", "Bay"), "Y:AG", 250)
    If bayCol <= 0 Then bayCol = 33

    firstRow = orderHdr.Row + 1
    lastRow = ws.Cells(ws.rows.Count, orderCol).End(xlUp).Row

    For r = firstRow To lastRow
        If IsNumeric(ws.Cells(r, orderCol).Value) Then
            If CLng(ws.Cells(r, orderCol).Value) = orderNumber Then
                If Len(Trim$(CStr(ws.Cells(r, itemCol).Value))) > 0 Then
                    ws.Cells(r, bayCol).Value = bayDisplayName
                End If
            End If
        End If
    Next r
End Sub

'------------------------------------------------------------------------------
' Procedure: ITBA_FindHeaderCell
' Scope: Private Function
'
' What it does:
'   Finds, writes, validates, or uses worksheet header cells for
'   ITBA_FindHeaderCell.
'
' Why it exists:
'   Header locations can move during import/rebuild, so the code uses header
'   discovery to target the correct columns instead of guessing.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function ITBA_FindHeaderCell(ByVal ws As Worksheet, ByVal headerNames As Variant, ByVal colAddress As String, ByVal maxRows As Long) As Range
    Dim searchRange As Range
    Dim f As Range
    Dim nm As Variant

    If ws Is Nothing Then Exit Function

    Set searchRange = Intersect(ws.Range("1:" & maxRows), ws.Columns(colAddress))
    If searchRange Is Nothing Then Exit Function

    For Each nm In headerNames
        Set f = searchRange.Find(What:=CStr(nm), LookIn:=xlValues, LookAt:=xlWhole, MatchCase:=False)

        If Not f Is Nothing Then
            Set ITBA_FindHeaderCell = f
            Exit Function
        End If
    Next nm

    For Each nm In headerNames
        Set f = searchRange.Find(What:=CStr(nm), LookIn:=xlValues, LookAt:=xlPart, MatchCase:=False)

        If Not f Is Nothing Then
            Set ITBA_FindHeaderCell = f
            Exit Function
        End If
    Next nm
End Function

'------------------------------------------------------------------------------
' Procedure: ITBA_FindHeaderCol
' Scope: Private Function
'
' What it does:
'   Finds, writes, validates, or uses worksheet header cells for
'   ITBA_FindHeaderCol.
'
' Why it exists:
'   Header locations can move during import/rebuild, so the code uses header
'   discovery to target the correct columns instead of guessing.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function ITBA_FindHeaderCol(ByVal ws As Worksheet, ByVal headerNames As Variant, ByVal colAddress As String, ByVal maxRows As Long) As Long
    Dim f As Range

    Set f = ITBA_FindHeaderCell(ws, headerNames, colAddress, maxRows)
    If Not f Is Nothing Then ITBA_FindHeaderCol = f.Column
End Function


