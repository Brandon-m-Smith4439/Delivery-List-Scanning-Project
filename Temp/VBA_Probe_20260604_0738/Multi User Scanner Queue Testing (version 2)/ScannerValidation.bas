Attribute VB_Name = "ScannerValidation"
Option Explicit

'==============================================================================
' Module: ScannerValidation
' Workbook: Multi User Scanner Queue Testing.xlsm / Master Delivery List
'
' What this module does:
'   Core scanner validation and sheet-update engine for staging, outbound, and
'   inbound/receiving scans.
'
' Why this module exists:
'   This is where barcode rules, quantity checks, status formatting, receive
'   override behavior, and scan layout rules are kept consistent across
'   sheets.
'
' Commenting standard used in this rewrite:
'   Procedure comments explain both what the code does and why that
'   behavior matters in the scanning / SharePoint / Power Automate workflow.
'   The code logic and public signatures are intentionally kept stable; this
'   pass is primarily a readability, maintainability, and safety pass.
'==============================================================================



'=====================
'ScannerValidation (Code)
'=====================

'=== SETTINGS ===
Public Const SCAN_CELL_SEND As String = "P4"
Public Const SCAN_CELL_RECV As String = "Y4"
Public Const SCAN_CELL_STAGING As String = "AP4"

Public Const HEADER_TEXT_ORDER As String = "Order Nr."
Public Const HEADER_TEXT_ITEM As String = "Item Nr."

Public Const HEADER_TEXT_BAR_SEND As String = "Barcode"
Public Const HEADER_TEXT_QTY_SEND As String = "Qty Scanned"
Public Const HEADER_TEXT_TIME_SEND As String = "Date & Time Scanned"
Public Const HEADER_TEXT_CHECK_SEND As String = "Check"

Public Const HEADER_TEXT_BAR_RECV As String = "Barcode"
Public Const HEADER_TEXT_QTY_RECV As String = "Qty Scanned"
Public Const HEADER_TEXT_TIME_RECV As String = "Date & Time"
Public Const HEADER_TEXT_CHECK_RECV As String = "Check"

Public Const HEADER_TEXT_BAR_STAGING As String = "Barcode"
Public Const HEADER_TEXT_QTY_STAGING As String = "Qty Scanned"
Public Const HEADER_TEXT_TIME_STAGING As String = "Date & Time Scanned"
Public Const HEADER_TEXT_CHECK_STAGING As String = "Check"

Private Const SUMMARY_GREENVILLE_SHEET_NAME As String = "Inbound - Greenville"
Private Const SUMMARY_GREENVILLE_CUSTOMER_TEXT As String = "BFS East Greenville SC MW"
Private Const SUMMARY_CPU_SHEET_NAME As String = "Customer Pickup"
Private Const SUMMARY_CPU_ROUTE_TEXT As String = "CPU"
Private Const SUMMARY_ROUTE_COL_FIXED As Long = 12   'L

Public LastScanSuccess As Boolean
Public LastScanOrder As Long
Public LastScanItem As Long
Public LastScanRequiredQty As Long
Public LastScanSentQty As Long
Public LastScanRecvQty As Long
Public LastScanStatus As String
Public LastScanTiming As String
Public LastScanMode As String

Public AllowQueuedReceiveOverride As Boolean
Public QueuedReceiveOverrideReason As String

Public AllowQueuedSendOverride As Boolean
Public QueuedSendOverrideReason As String

'If True, receiving is blocked until it was scanned out first
Public Const REQUIRE_SEND_BEFORE_RECV As Boolean = True

'------------------------------------------------------------------------------
' Procedure: ProcessScanNotice
' Scope: Private Sub
'
' What it does:
'   Builds or displays the operator-facing notice/message used by
'   ProcessScanNotice.
'
' Why it exists:
'   Scan results directly affect staged/outbound/received quantities, so this
'   rule keeps the visible sheet and downstream queue result accurate.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ProcessScanNotice(ByVal messageText As String, Optional ByVal titleText As String = "Scan Error", Optional ByVal style As VbMsgBoxStyle = vbExclamation)
    If Not SuppressProcessScanPopups Then
        MsgBox messageText, style, titleText
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: ManualScanNotice
' Scope: Private Sub
'
' What it does:
'   Builds or displays the operator-facing notice/message used by
'   ManualScanNotice.
'
' Why it exists:
'   Scan results directly affect staged/outbound/received quantities, so this
'   rule keeps the visible sheet and downstream queue result accurate.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ManualScanNotice(ByVal messageText As String, Optional ByVal titleText As String = "Manual Scan", Optional ByVal style As VbMsgBoxStyle = vbExclamation)
    If Not SuppressManualScanPopups Then
        MsgBox messageText, style, titleText
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: ProcessScan
' Scope: Public Sub
'
' What it does:
'   Validates a scanned barcode, finds the matching order/item row, updates
'   the correct scan block, checks quantities, formats statuses, and stores
'   last-scan results.
'
' Why it exists:
'   This is the central scan engine; all scanner sheets must apply the same
'   rules so staging/outbound/inbound counts stay in sync.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub ProcessScan(ByVal ws As Worksheet, _
                       ByVal rawScan As String, _
                       ByVal mode As String, _
                       Optional ByVal sourceScanTime As Variant)
    On Error Resume Next
    ws.Unprotect Password:=""
    On Error GoTo 0

    Dim code As String
    code = UCase$(cleanBarcode(rawScan))
    If Len(code) = 0 Then Exit Sub

    LastScanSuccess = False
    LastScanMode = UCase$(mode)
    LastScanStatus = ""
    LastScanTiming = ""
    LastScanRequiredQty = 0
    LastScanSentQty = 0
    LastScanRecvQty = 0

    '=== Find header cells ===
    'IMPORTANT:
    'Order/Item for the DELIVERY LIST must only be searched in A:N
    Dim orderHdr As Range, itemHdr As Range
    Dim sendBarHdr As Range, sendQtyHdr As Range, sendTimeHdr As Range, sendCheckHdr As Range
    Dim recvBarHdr As Range, recvQtyHdr As Range, recvTimeHdr As Range, recvCheckHdr As Range
    Dim stagingBarHdr As Range, stagingQtyHdr As Range, stagingTimeHdr As Range, stagingCheckHdr As Range

    Set orderHdr = FindHeaderCellInCols(ws, Array(HEADER_TEXT_ORDER), "A:N", 250)
    Set itemHdr = FindHeaderCellInCols(ws, Array(HEADER_TEXT_ITEM), "A:N", 250)

    Set sendBarHdr = FindHeaderCellInCols(ws, Array(HEADER_TEXT_BAR_SEND), "P:W", 60)
    Set sendQtyHdr = FindHeaderCellInCols(ws, Array(HEADER_TEXT_QTY_SEND), "P:W", 60)
    Set sendTimeHdr = FindHeaderCellInCols(ws, Array(HEADER_TEXT_TIME_SEND), "P:W", 60)
    Set sendCheckHdr = FindHeaderCellInCols(ws, Array(HEADER_TEXT_CHECK_SEND), "P:W", 60)

    Set recvBarHdr = FindHeaderCellInCols(ws, Array(HEADER_TEXT_BAR_RECV), "Y:AG", 60)
    Set recvQtyHdr = FindHeaderCellInCols(ws, Array(HEADER_TEXT_QTY_RECV), "Y:AG", 60)
    Set recvTimeHdr = FindHeaderCellInCols(ws, Array(HEADER_TEXT_TIME_RECV), "Y:AG", 60)
    Set recvCheckHdr = FindHeaderCellInCols(ws, Array(HEADER_TEXT_CHECK_RECV), "Y:AG", 60)

    Set stagingBarHdr = FindHeaderCellInCols(ws, Array(HEADER_TEXT_BAR_STAGING), "AP:AV", 60)
    Set stagingQtyHdr = FindHeaderCellInCols(ws, Array(HEADER_TEXT_QTY_STAGING), "AP:AV", 60)
    Set stagingTimeHdr = FindHeaderCellInCols(ws, Array(HEADER_TEXT_TIME_STAGING), "AP:AV", 60)
    Set stagingCheckHdr = FindHeaderCellInCols(ws, Array(HEADER_TEXT_CHECK_STAGING), "AP:AV", 60)

    If orderHdr Is Nothing Or itemHdr Is Nothing Then
    LastScanStatus = "Missing delivery list headers (Order Nr. / Item Nr.) in A:N."
    ProcessScanNotice "Couldn't find delivery list headers (Order Nr. / Item Nr.) in A:N.", "Scan Error", vbCritical
    Exit Sub
End If

    If sendBarHdr Is Nothing Or sendQtyHdr Is Nothing Or sendTimeHdr Is Nothing Or sendCheckHdr Is Nothing Then
    LastScanStatus = "Missing SEND headers (Barcode / Qty Scanned / Date & Time Scanned / Check)."
    ProcessScanNotice "Missing SEND headers (Barcode / Qty Scanned / Date & Time Scanned / Check).", "Scan Error", vbCritical
    Exit Sub
End If

    If recvBarHdr Is Nothing Or recvQtyHdr Is Nothing Or recvTimeHdr Is Nothing Or recvCheckHdr Is Nothing Then
    LastScanStatus = "Missing RECV headers (Barcode Received / Qty Received / Date & Time Received / Received Check)."
    ProcessScanNotice "Missing RECV headers (Barcode Received / Qty Received / Date & Time Received / Received Check).", "Scan Error", vbCritical
    Exit Sub
End If

    If stagingBarHdr Is Nothing Or stagingQtyHdr Is Nothing Or stagingTimeHdr Is Nothing Or stagingCheckHdr Is Nothing Then
    LastScanStatus = "Missing STAGING headers (Barcode / Qty / Date & Time / Check)."
    ProcessScanNotice "Missing STAGING headers (Barcode / Qty / Date & Time / Check).", "Scan Error", vbCritical
    Exit Sub
End If
    
    '=== Use found rows / cols ===
    Dim orderHeaderRow As Long
    Dim orderCol As Long, itemCol As Long

    Dim sendBarCol As Long, sendQtyCol As Long, sendTimeCol As Long, sendCheckCol As Long
    Dim recvBarCol As Long, recvQtyCol As Long, recvTimeCol As Long, recvCheckCol As Long
    Dim stagingBarCol As Long, stagingQtyCol As Long, stagingTimeCol As Long, stagingCheckCol As Long

    orderHeaderRow = orderHdr.Row
    orderCol = orderHdr.Column
    itemCol = itemHdr.Column

    sendBarCol = sendBarHdr.Column
    sendQtyCol = sendQtyHdr.Column
    sendTimeCol = sendTimeHdr.Column
    sendCheckCol = sendCheckHdr.Column

    recvBarCol = recvBarHdr.Column
    recvQtyCol = recvQtyHdr.Column
    recvTimeCol = recvTimeHdr.Column
    recvCheckCol = recvCheckHdr.Column

    stagingBarCol = stagingBarHdr.Column
    stagingQtyCol = stagingQtyHdr.Column
    stagingTimeCol = stagingTimeHdr.Column
    stagingCheckCol = stagingCheckHdr.Column

    '=== Delivery list data range ===
    Dim firstDataRow As Long, lastRow As Long
    firstDataRow = orderHeaderRow + 1
    lastRow = ws.Cells(ws.rows.Count, orderCol).End(xlUp).Row

    If lastRow < firstDataRow Then
    LastScanStatus = "No delivery list rows found under the Order column."
    ProcessScanNotice "No delivery list rows found under the Order column.", "Scan Error", vbExclamation
    Exit Sub
End If

    Dim ord As Long, itm As Long
    Dim recoveryMessage As String

    If Not TryRecoverScanBarcode(code, ws, orderCol, itemCol, firstDataRow, lastRow, ord, itm, code, recoveryMessage) Then
        Beep
        LastScanStatus = "BAD SCAN format: " & rawScan
        ProcessScanNotice "BAD SCAN format:" & vbCrLf & rawScan & vbCrLf & vbCrLf & _
                          "The scan did not contain a recoverable order/item for this delivery list.", _
                          "Scan Error", vbExclamation
        Exit Sub
    End If

    LastScanOrder = ord
    LastScanItem = itm

    Dim itmTxt As String
    itmTxt = Format$(itm, "000")

    'Find matching row in delivery list
    Dim matchRow As Long
    matchRow = FindRowByOrderItem(ws, ord, itm, orderCol, itemCol, firstDataRow, lastRow)

    If matchRow = 0 Then
    Beep
    LastScanStatus = "Scanned item doesn't exist in this list: Order " & ord & " / Item " & Format$(itm, "000")
    ProcessScanNotice "Scanned item doesn't exist in this list:" & vbCrLf & _
                      "Order: " & ord & "   Item: " & Format$(itm, "000") & vbCrLf & _
                      "Scan: " & code, _
                      "Not Found", vbExclamation
    Exit Sub
End If

    'Required Qty comes from the delivery list
    Dim qtyReqCol As Long, requiredQty As Long
    qtyReqCol = FindHeaderColInRowByNames(ws, orderHeaderRow, Array("Qty.", "Qty", "Quantity"))
    requiredQty = 1

    If qtyReqCol > 0 Then
        If IsNumeric(ws.Cells(matchRow, qtyReqCol).Value) Then
            requiredQty = CLng(ws.Cells(matchRow, qtyReqCol).Value)
            If requiredQty < 1 Then requiredQty = 1
        End If
    End If

    Dim writeRow As Long
    writeRow = matchRow

    'Safeguard: if row already has a different barcode recorded, stop
    Dim existingCode As String
    Select Case UCase$(mode)
        Case "STAGING"
            existingCode = UCase$(Trim$(CStr(ws.Cells(writeRow, stagingBarCol).Value)))
        Case "SEND"
            existingCode = UCase$(Trim$(CStr(ws.Cells(writeRow, sendBarCol).Value)))
        Case Else
            existingCode = UCase$(Trim$(CStr(ws.Cells(writeRow, recvBarCol).Value)))
    End Select

    If Len(existingCode) > 0 And existingCode <> code Then
    Beep
    LastScanStatus = "Barcode mismatch for Order " & ord & " / Item " & Format$(itm, "000")
    ProcessScanNotice "This line already has a different barcode recorded:" & vbCrLf & _
                      "Existing: " & existingCode & vbCrLf & _
                      "New:      " & code, _
                      "Barcode Mismatch", vbExclamation
    Exit Sub
End If

    Dim nowT As Date

If IsMissing(sourceScanTime) Then
    nowT = Now
ElseIf IsDate(sourceScanTime) Then
    nowT = CDate(sourceScanTime)
Else
    nowT = Now
End If

    Dim deliveryDate As Date, timing As String
    deliveryDate = GetDeliveryListDate(ws)
    timing = DeliveryTimingText(deliveryDate, nowT)

    '=========================
    ' STAGING (Qty logic)
    '=========================
    If UCase$(mode) = "STAGING" Then
        Dim stagingQty As Long
        Dim stagingCommentsCol As Long
        Dim stagingStatus As String

        stagingQty = CLng(Val(ws.Cells(writeRow, stagingQtyCol).Value))
        stagingCommentsCol = stagingCheckCol + 1

        If stagingQty >= requiredQty Then
    Beep
    LastScanStatus = "Already fully staged (" & stagingQty & " / " & requiredQty & ") for Order " & ord & " / Item " & Format$(itm, "000")
    ProcessScanNotice "This line is already fully STAGED (" & stagingQty & " / " & requiredQty & ").", "Over Quantity", vbExclamation
    Exit Sub
End If

        stagingQty = stagingQty + 1

        ws.Cells(writeRow, stagingBarCol).Value = code
        ws.Cells(writeRow, stagingBarCol + 1).Value = ord
        ws.Cells(writeRow, stagingBarCol + 2).Value = itmTxt
        ws.Cells(writeRow, stagingQtyCol).Value = stagingQty
        With ws.Cells(writeRow, stagingTimeCol)
    .Value = nowT
    .NumberFormat = "m/d/yyyy h:mm AM/PM"
End With

        If stagingQty = requiredQty Then
            stagingStatus = "OK"
            ws.Cells(writeRow, stagingCheckCol).Value = stagingStatus
            FormatGreenStatus ws.Cells(writeRow, stagingCheckCol)
        Else
            stagingStatus = "Partial " & CStr(stagingQty) & "/" & CStr(requiredQty)
            ws.Cells(writeRow, stagingCheckCol).Value = stagingStatus
            FormatYellowPartial ws.Cells(writeRow, stagingCheckCol)
        End If

        With ws.Range(SCAN_CELL_STAGING)
            .Value = code
            .Offset(0, 1).Value = ord
            .Offset(0, 2).Value = itmTxt
            .Offset(0, 3).Value = stagingQty
            .Offset(0, 4).Value = nowT
            .Offset(0, 4).NumberFormat = "m/d/yyyy h:mm AM/PM"
            .Offset(0, 5).Value = stagingStatus
            .Offset(0, 6).Value = ws.Cells(writeRow, stagingCommentsCol).Value
        End With

        FormatStatusCellByValue ws.Range(SCAN_CELL_STAGING).Offset(0, 5), stagingStatus
        
        
        LastScanRequiredQty = requiredQty
        LastScanSentQty = CLng(Val(ws.Cells(writeRow, sendQtyCol).Value))
        LastScanRecvQty = CLng(Val(ws.Cells(writeRow, recvQtyCol).Value))
        LastScanTiming = ""
        LastScanStatus = stagingStatus
        LastScanSuccess = True

    '=========================
    ' SEND (Qty Scanned logic)
    '=========================
    ElseIf UCase$(mode) = "SEND" Then
    Dim sentQty As Long
    sentQty = CLng(Val(ws.Cells(writeRow, sendQtyCol).Value))
    
    Dim currentStagingQty As Long
    currentStagingQty = CLng(Val(ws.Cells(writeRow, stagingQtyCol).Value))

    'First: stop duplicate outbound scans once full quantity is already sent
    If sentQty >= requiredQty Then
    Beep
    LastScanRequiredQty = requiredQty
    LastScanSentQty = sentQty
    LastScanRecvQty = CLng(Val(ws.Cells(writeRow, recvQtyCol).Value))
    LastScanTiming = ""
    LastScanStatus = "Already fully outbound scanned for Order " & ord & " / Item " & Format$(itm, "000")
    LastScanSuccess = False

    ProcessScanNotice "Already scanned on outbound." & vbCrLf & vbCrLf & _
                      "This item is already fully scanned on 'Outbound - Airport Rd'." & vbCrLf & _
                      "Outbound: " & sentQty & " / " & requiredQty & vbCrLf & _
                      "Staged: " & currentStagingQty & " / " & requiredQty, _
                      "Already Scanned on Outbound", vbExclamation
    Exit Sub
End If

        'Second: block outbound if staging is still behind the next outbound quantity.
    'This can now be overridden deliberately, similar to inbound receive override.
    Dim outboundOverrideType As String
    Dim attemptedOutboundQty As Long
    Dim sendOverrideCommentsCol As Long

    outboundOverrideType = vbNullString
    attemptedOutboundQty = sentQty + 1
    sendOverrideCommentsCol = sendCheckCol + 2

    If currentStagingQty < attemptedOutboundQty Then
        If SuppressProcessScanPopups Then
            If AllowQueuedSendOverride Then
                outboundOverrideType = "STAGING"
            Else
                LastScanRequiredQty = requiredQty
                LastScanSentQty = attemptedOutboundQty
                LastScanRecvQty = CLng(Val(ws.Cells(writeRow, recvQtyCol).Value))
                LastScanTiming = ""
                LastScanStatus = QUEUE_SEND_OVERRIDE_AVAILABLE_FLAG & _
                                 "Outbound would exceed staged quantity. " & _
                                 "Staged Qty: " & currentStagingQty & _
                                 "; Current Outbound Qty: " & sentQty & _
                                 "; Attempted Outbound Qty: " & attemptedOutboundQty
                LastScanSuccess = False
                Exit Sub
            End If

        Else
            Beep

            If MsgBox( _
                "Outbound scan blocked." & vbCrLf & vbCrLf & _
                "This item has not been staged enough for the next outbound scan." & vbCrLf & _
                "Staged Qty: " & currentStagingQty & vbCrLf & _
                "Current Outbound Qty: " & sentQty & vbCrLf & _
                "Attempted Outbound Qty: " & attemptedOutboundQty & vbCrLf & vbCrLf & _
                "Override and send outbound anyway?", _
                vbYesNo + vbExclamation, "Override Staging Mismatch?") <> vbYes Then

                LastScanRequiredQty = requiredQty
                LastScanSentQty = sentQty
                LastScanRecvQty = CLng(Val(ws.Cells(writeRow, recvQtyCol).Value))
                LastScanTiming = ""
                LastScanStatus = "Outbound scan cancelled for Order " & ord & _
                                 " / Item " & Format$(itm, "000") & _
                                 ". Staging quantity is behind outbound quantity."
                LastScanSuccess = False

                Exit Sub
            End If

            outboundOverrideType = "STAGING"
        End If
    End If

    If outboundOverrideType = "STAGING" Then
        AppendOverrideComment ws.Cells(writeRow, sendOverrideCommentsCol), _
            "Override: outbound before staged"
        AutoFitCommentsCol ws, sendOverrideCommentsCol, 80
    End If

    sentQty = sentQty + 1

    ws.Cells(writeRow, sendBarCol).Value = code
    ws.Cells(writeRow, sendBarCol + 1).Value = ord
    ws.Cells(writeRow, sendBarCol + 2).Value = itmTxt
    ws.Cells(writeRow, sendQtyCol).Value = sentQty
    With ws.Cells(writeRow, sendTimeCol)
    .Value = nowT
    .NumberFormat = "m/d/yyyy h:mm AM/PM"
End With

    'Delivery Timing (right of Check)
    Dim sendTimingCol As Long
    sendTimingCol = sendCheckCol + 1
    ws.Cells(writeRow, sendTimingCol).Value = timing
    FormatDeliveryTiming ws.Cells(writeRow, sendTimingCol), timing

    'Red-flag if received qty is ahead of sent qty
    Dim curRecvQty As Long
    curRecvQty = CLng(Val(ws.Cells(writeRow, recvQtyCol).Value))
    If curRecvQty > sentQty Then
        FormatQtyMismatchRed ws.Cells(writeRow, sendQtyCol)
    Else
        ClearQtyMismatchRed ws.Cells(writeRow, sendQtyCol)
    End If

    UpdateRecvCheckCell ws, writeRow, recvCheckCol, curRecvQty, sentQty, requiredQty

    Dim sendStatus As String
    If sentQty = requiredQty Then
        sendStatus = "OK"
        ws.Cells(writeRow, sendCheckCol).Value = sendStatus
        FormatGreenStatus ws.Cells(writeRow, sendCheckCol)
    Else
        sendStatus = "Partial " & CStr(sentQty) & "/" & CStr(requiredQty)
        ws.Cells(writeRow, sendCheckCol).Value = sendStatus
        FormatYellowPartial ws.Cells(writeRow, sendCheckCol)
    End If

    'Top tracking cells (P4:V4)
    With ws.Range(SCAN_CELL_SEND)
        .Value = code                       'P4
        .Offset(0, 1).Value = ord           'Q4
        .Offset(0, 2).Value = itmTxt        'R4
        .Offset(0, 3).Value = sentQty       'S4
        .Offset(0, 4).Value = nowT          'T4
        .Offset(0, 4).NumberFormat = "m/d/yyyy h:mm AM/PM"
        .Offset(0, 5).Value = sendStatus    'U4
        .Offset(0, 6).Value = timing        'V4
    End With

    FormatStatusCellByValue ws.Range(SCAN_CELL_SEND).Offset(0, 5), sendStatus
    FormatDeliveryTiming ws.Range(SCAN_CELL_SEND).Offset(0, 6), timing

    LastScanRequiredQty = requiredQty
    LastScanSentQty = sentQty
    LastScanRecvQty = CLng(Val(ws.Cells(writeRow, recvQtyCol).Value))
    LastScanTiming = timing
    LastScanStatus = sendStatus
    LastScanSuccess = True
    
    '============================
    ' RECV (Qty Received logic)
    '============================
    ElseIf UCase$(mode) = "RECV" Then
        Dim sentQtyForLine As Long
        sentQtyForLine = CLng(Val(ws.Cells(writeRow, sendQtyCol).Value))

        Dim recvQty As Long
        recvQty = CLng(Val(ws.Cells(writeRow, recvQtyCol).Value))

        Dim nextRecvQty As Long
        nextRecvQty = recvQty + 1

        Dim recvCommentsCol As Long
        recvCommentsCol = recvCheckCol + 2

        Dim overrideType As String
        overrideType = ""

                'Case 1: no outbound quantity has been scanned yet
        If REQUIRE_SEND_BEFORE_RECV And sentQtyForLine <= 0 Then
            If SuppressProcessScanPopups Then
                If AllowQueuedReceiveOverride Then
                    overrideType = "NO_SENT"
                Else
                    LastScanRequiredQty = requiredQty
                    LastScanSentQty = sentQtyForLine
                    LastScanRecvQty = nextRecvQty
                    LastScanTiming = ""
                    LastScanStatus = QUEUE_RECV_OVERRIDE_AVAILABLE_FLAG & _
                                     "No outbound scan found. Outbound Qty: " & sentQtyForLine & _
                                     "; Current Inbound Qty: " & recvQty & _
                                     "; Attempted Inbound Qty: " & nextRecvQty
                    LastScanSuccess = False
                    Exit Sub
                End If
            Else
                Beep

                If MsgBox( _
                    "No outbound quantity has been scanned for this line." & vbCrLf & _
                    "You are about to receive qty " & nextRecvQty & "." & vbCrLf & vbCrLf & _
                    "Override and receive anyway?", _
                    vbYesNo + vbExclamation, "Override Outbound Scan?") <> vbYes Then

                    LastScanRequiredQty = requiredQty
                    LastScanSentQty = sentQtyForLine
                    LastScanRecvQty = recvQty
                    LastScanTiming = ""
                    LastScanStatus = "Inbound scan cancelled for Order " & ord & " / Item " & Format$(itm, "000") & _
                                     ". No outbound quantity has been scanned yet."
                    LastScanSuccess = False

                    Exit Sub
                End If

                overrideType = "NO_SENT"
            End If

        'Case 2: inbound would exceed outbound quantity
        ElseIf nextRecvQty > sentQtyForLine Then
            If SuppressProcessScanPopups Then
                If AllowQueuedReceiveOverride Then
                    overrideType = "EXCEEDS"
                Else
                    LastScanRequiredQty = requiredQty
                    LastScanSentQty = sentQtyForLine
                    LastScanRecvQty = nextRecvQty
                    LastScanTiming = ""
                    LastScanStatus = QUEUE_RECV_OVERRIDE_AVAILABLE_FLAG & _
                                     "Inbound would exceed outbound. Outbound Qty: " & sentQtyForLine & _
                                     "; Current Inbound Qty: " & recvQty & _
                                     "; Attempted Inbound Qty: " & nextRecvQty
                    LastScanSuccess = False
                    Exit Sub
                End If
            Else
                Beep

                If MsgBox( _
                    "Inbound quantity would exceed outbound quantity." & vbCrLf & _
                    "Outbound Qty: " & sentQtyForLine & vbCrLf & _
                    "Current Inbound Qty: " & recvQty & vbCrLf & _
                    "Attempted Inbound Qty: " & nextRecvQty & vbCrLf & vbCrLf & _
                    "Override and receive anyway? The outbound quantity will be flagged.", _
                    vbYesNo + vbExclamation, "Override Over-Receive?") <> vbYes Then

                    LastScanRequiredQty = requiredQty
                    LastScanSentQty = sentQtyForLine
                    LastScanRecvQty = recvQty
                    LastScanTiming = ""
                    LastScanStatus = "Inbound scan cancelled for Order " & ord & " / Item " & Format$(itm, "000") & _
                                     ". Inbound quantity would exceed outbound quantity." & vbCrLf & _
                                     "Outbound Qty: " & sentQtyForLine & vbCrLf & _
                                     "Current Inbound Qty: " & recvQty & vbCrLf & _
                                     "Attempted Inbound Qty: " & nextRecvQty
                    LastScanSuccess = False

                    Exit Sub
                End If

                overrideType = "EXCEEDS"
            End If
        End If

        If overrideType = "NO_SENT" Then
            AppendOverrideComment ws.Cells(writeRow, recvCommentsCol), "Override: received with no sent scans"
            AutoFitCommentsCol ws, recvCommentsCol, 80
        ElseIf overrideType = "EXCEEDS" Then
            AppendOverrideComment ws.Cells(writeRow, recvCommentsCol), "Override: received exceeds scanned"
            AutoFitCommentsCol ws, recvCommentsCol, 80
        End If

        recvQty = nextRecvQty

        ws.Cells(writeRow, recvBarCol).Value = code
        ws.Cells(writeRow, recvBarCol + 1).Value = ord
        ws.Cells(writeRow, recvBarCol + 2).Value = itmTxt
        ws.Cells(writeRow, recvQtyCol).Value = recvQty
        With ws.Cells(writeRow, recvTimeCol)
    .Value = nowT
    .NumberFormat = "m/d/yyyy h:mm AM/PM"
End With


        'Flag Airport Rd Qty red if received exceeds scanned
        If recvQty > sentQtyForLine Then
            FormatQtyMismatchRed ws.Cells(writeRow, sendQtyCol)
        Else
            ClearQtyMismatchRed ws.Cells(writeRow, sendQtyCol)
        End If

        UpdateRecvCheckCell ws, writeRow, recvCheckCol, recvQty, sentQtyForLine, requiredQty

        Dim recvStatus As String
        recvStatus = CStr(ws.Cells(writeRow, recvCheckCol).Value)

        'Top tracking cells (Y4:AE4)
        With ws.Range(SCAN_CELL_RECV)
            .Value = code
            .Offset(0, 1).Value = ord
            .Offset(0, 2).Value = itmTxt
            .Offset(0, 3).Value = recvQty
            .Offset(0, 4).Value = nowT
            .Offset(0, 4).NumberFormat = "m/d/yyyy h:mm AM/PM"
            .Offset(0, 5).Value = recvStatus
            .Offset(0, 6).ClearContents
        End With

        FormatStatusCellByValue ws.Range(SCAN_CELL_RECV).Offset(0, 5), recvStatus
        
        LastScanRequiredQty = requiredQty
        LastScanSentQty = sentQtyForLine
        LastScanRecvQty = recvQty
        LastScanTiming = ""
        LastScanStatus = CStr(ws.Cells(writeRow, recvCheckCol).Value)
        LastScanSuccess = True

    Else
    LastScanStatus = "Unknown scan mode: " & mode
    ProcessScanNotice "Unknown scan mode: " & mode, "Scan Error", vbCritical
    Exit Sub
End If

    '--- AutoFit Comments columns every scan ---
    Dim sendCommentsCol As Long, recvCommentsCol2 As Long, stagingCommentsCol2 As Long
    sendCommentsCol = sendCheckCol + 2
    recvCommentsCol2 = recvCheckCol + 2
    stagingCommentsCol2 = stagingCheckCol + 1

    AutoFitCommentsCol ws, sendCommentsCol, 80
    AutoFitCommentsCol ws, recvCommentsCol2, 80
    AutoFitCommentsCol ws, stagingCommentsCol2, 80

    EnsureMinColWidth ws, sendCommentsCol, 18
    EnsureMinColWidth ws, recvCommentsCol2, 18
    EnsureMinColWidth ws, stagingCommentsCol2, 18

    'Update sent/received completion summary
    UpdateProgressSummary ws, orderHeaderRow, orderCol, firstDataRow, lastRow, _
        sendBarCol, sendTimeCol, sendCheckCol, _
        recvBarCol, recvTimeCol, recvCheckCol
End Sub

'=== Cleans scanner input ===

'------------------------------------------------------------------------------
' Procedure: cleanBarcode
' Scope: Private Function
'
' What it does:
'   Cleans, decodes, validates, writes, or displays barcode data for
'   cleanBarcode.
'
' Why it exists:
'   The barcode is the link between the physical glass label and the
'   order/item row, so the project must parse and validate it consistently.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function cleanBarcode(ByVal s As String) As String
    Dim i As Long, ch As String, out As String
    s = Replace(s, "*", "")
    s = Replace(s, vbCr, "")
    s = Replace(s, vbLf, "")
    s = Trim$(s)

    For i = 1 To Len(s)
        ch = Mid$(s, i, 1)
        If ch Like "[0-9A-Za-z]" Then out = out & ch
    Next i

    cleanBarcode = out
End Function

Public Function TryCanonicalizeScanForSheet(ByVal ws As Worksheet, _
                                            ByVal rawScan As String, _
                                            ByRef canonicalCode As String, _
                                            ByRef orderNumber As Long, _
                                            ByRef itemNumber As Long, _
                                            Optional ByRef recoveryMessage As String) As Boolean
    On Error GoTo Fail

    Dim code As String
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim orderCol As Long
    Dim itemCol As Long
    Dim firstDataRow As Long
    Dim lastRow As Long

    If ws Is Nothing Then Exit Function

    code = UCase$(cleanBarcode(rawScan))
    If Len(code) = 0 Then Exit Function

    Set orderHdr = FindHeaderCellInCols(ws, Array(HEADER_TEXT_ORDER), "A:N", 250)
    Set itemHdr = FindHeaderCellInCols(ws, Array(HEADER_TEXT_ITEM), "A:N", 250)

    If orderHdr Is Nothing Or itemHdr Is Nothing Then Exit Function

    orderCol = orderHdr.Column
    itemCol = itemHdr.Column
    firstDataRow = orderHdr.Row + 1
    lastRow = ws.Cells(ws.rows.Count, orderCol).End(xlUp).Row

    If lastRow < firstDataRow Then Exit Function

    TryCanonicalizeScanForSheet = TryRecoverScanBarcode(code, ws, orderCol, itemCol, firstDataRow, lastRow, orderNumber, itemNumber, canonicalCode, recoveryMessage)
    Exit Function

Fail:
    TryCanonicalizeScanForSheet = False
End Function

Private Function TryRecoverScanBarcode(ByVal scanText As String, _
                                       ByVal ws As Worksheet, _
                                       ByVal orderCol As Long, _
                                       ByVal itemCol As Long, _
                                       ByVal firstDataRow As Long, _
                                       ByVal lastRow As Long, _
                                       ByRef orderNumber As Long, _
                                       ByRef itemNumber As Long, _
                                       ByRef canonicalCode As String, _
                                       ByRef recoveryMessage As String) As Boolean
    Dim cleanText As String
    Dim digitsOnly As String
    Dim i As Long
    Dim candidateText As String
    Dim candidateOrder As Long
    Dim candidateItem As Long
    Dim inferredOrder As Long

    cleanText = UCase$(cleanBarcode(scanText))
    recoveryMessage = vbNullString

    If Len(cleanText) = 16 And cleanText Like "T200############" Then
        orderNumber = CLng(Mid$(cleanText, 5, 6))
        itemNumber = CLng(Mid$(cleanText, 11, 3))
        canonicalCode = cleanText
        TryRecoverScanBarcode = (orderNumber > 0 And itemNumber > 0)
        Exit Function
    End If

    digitsOnly = BarcodeDigitsOnly(cleanText)

    For i = 1 To Len(digitsOnly) - 11
        candidateText = Mid$(digitsOnly, i, 12)
        candidateOrder = CLng(Val(Left$(candidateText, 6)))
        candidateItem = CLng(Val(Mid$(candidateText, 7, 3)))

        If candidateOrder > 0 And candidateItem > 0 Then
            If FindRowByOrderItem(ws, candidateOrder, candidateItem, orderCol, itemCol, firstDataRow, lastRow) > 0 Then
                orderNumber = candidateOrder
                itemNumber = candidateItem
                canonicalCode = CanonicalBarcodeText(orderNumber, itemNumber)
                recoveryMessage = "Recovered damaged label as Order " & orderNumber & " / Item " & Format$(itemNumber, "000") & "."
                TryRecoverScanBarcode = True
                Exit Function
            End If
        End If
    Next i

    For i = 1 To Len(digitsOnly) - 8
        candidateText = Mid$(digitsOnly, i, 9)
        candidateItem = CLng(Val(Mid$(candidateText, 4, 3)))

        If candidateItem > 0 Then
            If TryFindOrderBySuffixItem(ws, orderCol, itemCol, firstDataRow, lastRow, Left$(candidateText, 3), candidateItem, inferredOrder) Then
                orderNumber = inferredOrder
                itemNumber = candidateItem
                canonicalCode = CanonicalBarcodeText(orderNumber, itemNumber)
                recoveryMessage = "Recovered damaged label as Order " & orderNumber & " / Item " & Format$(itemNumber, "000") & " from matching delivery-list data."
                TryRecoverScanBarcode = True
                Exit Function
            End If
        End If
    Next i
End Function

Private Function BarcodeDigitsOnly(ByVal valueText As String) As String
    Dim i As Long
    Dim ch As String

    For i = 1 To Len(valueText)
        ch = Mid$(valueText, i, 1)
        If ch Like "[0-9]" Then BarcodeDigitsOnly = BarcodeDigitsOnly & ch
    Next i
End Function

Private Function CanonicalBarcodeText(ByVal orderNumber As Long, ByVal itemNumber As Long) As String
    CanonicalBarcodeText = "T200" & Format$(orderNumber, "000000") & Format$(itemNumber, "000") & "000"
End Function

Private Function TryFindOrderBySuffixItem(ByVal ws As Worksheet, _
                                          ByVal orderCol As Long, _
                                          ByVal itemCol As Long, _
                                          ByVal firstDataRow As Long, _
                                          ByVal lastRow As Long, _
                                          ByVal orderSuffix As String, _
                                          ByVal itemNumber As Long, _
                                          ByRef orderNumber As Long) As Boolean
    Dim r As Long
    Dim rowOrder As Long
    Dim rowItem As Long
    Dim foundCount As Long

    If ws Is Nothing Then Exit Function
    If orderCol <= 0 Or itemCol <= 0 Then Exit Function

    For r = firstDataRow To lastRow
        If Not ws.rows(r).Hidden Then
            If IsRealDeliveryLine(ws, r, orderCol, itemCol) Then
                rowOrder = CLng(Val(Replace$(CStr(ws.Cells(r, orderCol).Value), ",", vbNullString)))
                rowItem = CLng(Val(ws.Cells(r, itemCol).Value))

                If rowOrder > 0 And rowItem = itemNumber Then
                    If Right$(Format$(rowOrder, "000000"), Len(orderSuffix)) = orderSuffix Then
                        If orderNumber = 0 Or orderNumber <> rowOrder Then
                            orderNumber = rowOrder
                            foundCount = foundCount + 1
                        End If
                    End If
                End If
            End If
        End If
    Next r

    TryFindOrderBySuffixItem = (foundCount = 1 And orderNumber > 0)
End Function

'=== Finds a header cell anywhere in the top part of the sheet ===

'------------------------------------------------------------------------------
' Procedure: FindHeaderCell
' Scope: Private Function
'
' What it does:
'   Finds, writes, validates, or uses worksheet header cells for
'   FindHeaderCell.
'
' Why it exists:
'   Header locations can move during import/rebuild, so the code uses header
'   discovery to target the correct columns instead of guessing.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function FindHeaderCell(ByVal ws As Worksheet, ByVal names As Variant, Optional ByVal topRows As Long = 60) As Range
    Dim searchRange As Range, nm As Variant, f As Range
    Set searchRange = ws.Range(ws.Cells(1, 1), ws.Cells(topRows, ws.Columns.Count))

    For Each nm In names
        Set f = searchRange.Find(What:=CStr(nm), LookIn:=xlValues, LookAt:=xlWhole)
        If Not f Is Nothing Then
            Set FindHeaderCell = f
            Exit Function
        End If
    Next nm

    For Each nm In names
        Set f = searchRange.Find(What:=CStr(nm), LookIn:=xlValues, LookAt:=xlPart)
        If Not f Is Nothing Then
            Set FindHeaderCell = f
            Exit Function
        End If
    Next nm

    Set FindHeaderCell = Nothing
End Function

'=== Finds a header cell only within specific columns ===

'------------------------------------------------------------------------------
' Procedure: FindHeaderCellInCols
' Scope: Private Function
'
' What it does:
'   Finds, writes, validates, or uses worksheet header cells for
'   FindHeaderCellInCols.
'
' Why it exists:
'   Header locations can move during import/rebuild, so the code uses header
'   discovery to target the correct columns instead of guessing.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function FindHeaderCellInCols(ByVal ws As Worksheet, ByVal names As Variant, ByVal colAddress As String, Optional ByVal topRows As Long = 250) As Range
    Dim searchRange As Range, nm As Variant, f As Range

    Set searchRange = Intersect(ws.Range("1:" & topRows), ws.Columns(colAddress))
    If searchRange Is Nothing Then
        Set FindHeaderCellInCols = Nothing
        Exit Function
    End If

    For Each nm In names
        Set f = searchRange.Find(What:=CStr(nm), LookIn:=xlValues, LookAt:=xlWhole)
        If Not f Is Nothing Then
            Set FindHeaderCellInCols = f
            Exit Function
        End If
    Next nm

    For Each nm In names
        Set f = searchRange.Find(What:=CStr(nm), LookIn:=xlValues, LookAt:=xlPart)
        If Not f Is Nothing Then
            Set FindHeaderCellInCols = f
            Exit Function
        End If
    Next nm

    Set FindHeaderCellInCols = Nothing
End Function

'=== Find a header column within a specific header row ===

'------------------------------------------------------------------------------
' Procedure: FindHeaderColInRowByNames
' Scope: Private Function
'
' What it does:
'   Finds, writes, validates, or uses worksheet header cells for
'   FindHeaderColInRowByNames.
'
' Why it exists:
'   Header locations can move during import/rebuild, so the code uses header
'   discovery to target the correct columns instead of guessing.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function FindHeaderColInRowByNames(ByVal ws As Worksheet, ByVal headerRow As Long, ByVal names As Variant) As Long
    Dim nm As Variant, f As Range
    For Each nm In names
        Set f = ws.rows(headerRow).Find(What:=CStr(nm), LookIn:=xlValues, LookAt:=xlWhole)
        If Not f Is Nothing Then
            FindHeaderColInRowByNames = f.Column
            Exit Function
        End If
    Next nm
    FindHeaderColInRowByNames = 0
End Function

'=== Finds the list row by Order + Item ===

'------------------------------------------------------------------------------
' Procedure: FindRowByOrderItem
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   FindRowByOrderItem.
'
' Why it exists:
'   Rows may represent real orders, section headers, remakes, Greenville work,
'   Customer Pickup work, or updated rows; each type needs different handling.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function FindRowByOrderItem( _
    ByVal ws As Worksheet, _
    ByVal orderNum As Long, _
    ByVal itemNum As Long, _
    ByVal orderCol As Long, _
    ByVal itemCol As Long, _
    ByVal firstRow As Long, _
    ByVal lastRow As Long) As Long

    Dim rng As Range, f As Range, firstAddr As String
    Set rng = ws.Range(ws.Cells(firstRow, orderCol), ws.Cells(lastRow, orderCol))

    Set f = rng.Find(What:=CStr(orderNum), LookIn:=xlValues, LookAt:=xlWhole)
    If Not f Is Nothing Then
        firstAddr = f.Address
        Do
            Dim v As Variant
            v = ws.Cells(f.Row, itemCol).Value
            If IsNumeric(v) Then
                If CLng(v) = itemNum Then
                    FindRowByOrderItem = f.Row
                    Exit Function
                End If
            End If
            Set f = rng.FindNext(f)
        Loop While Not f Is Nothing And f.Address <> firstAddr
    End If

    FindRowByOrderItem = 0
End Function

'------------------------------------------------------------------------------
' Procedure: FormatGreenStatus
' Scope: Private Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   FormatGreenStatus.
'
' Why it exists:
'   Scan results directly affect staged/outbound/received quantities, so this
'   rule keeps the visible sheet and downstream queue result accurate.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub FormatGreenStatus(ByVal c As Range)
    With c
        .Interior.Color = RGB(198, 239, 206)
        .Font.Color = RGB(0, 97, 0)
        .Font.Bold = True
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: ClearStatusFormat
' Scope: Private Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   ClearStatusFormat.
'
' Why it exists:
'   Scan results directly affect staged/outbound/received quantities, so this
'   rule keeps the visible sheet and downstream queue result accurate.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ClearStatusFormat(ByVal c As Range)
    With c
        .Interior.Pattern = xlNone
        .Font.ColorIndex = xlAutomatic
        .Font.Bold = False
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: UpdateProgressSummary
' Scope: Private Sub
'
' What it does:
'   Calculates or updates summary/banner information shown at the top of
'   delivery/scanner sheets for UpdateProgressSummary.
'
' Why it exists:
'   Operators use those summary panels to quickly see staged, outbound,
'   inbound, and completion progress without manually counting rows.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub UpdateProgressSummary( _
    ByVal ws As Worksheet, _
    ByVal orderHeaderRow As Long, _
    ByVal orderCol As Long, _
    ByVal firstDataRow As Long, _
    ByVal lastRow As Long, _
    ByVal sendBarCol As Long, _
    ByVal sendTimeCol As Long, _
    ByVal sendCheckCol As Long, _
    ByVal recvBarCol As Long, _
    ByVal recvTimeCol As Long, _
    ByVal recvCheckCol As Long)

    Dim qtyReqCol As Long
    qtyReqCol = FindHeaderColInRowByNames(ws, orderHeaderRow, Array("Qty.", "Qty", "Quantity"))

    'Find item column from delivery list headers
    Dim itemCol As Long
    itemCol = FindHeaderColInRowByNames(ws, orderHeaderRow, Array(HEADER_TEXT_ITEM))

    If itemCol = 0 Then Exit Sub

    'Qty columns are immediately LEFT of the Date&Time columns
    Dim sendQtyCol As Long, recvQtyCol As Long
    sendQtyCol = sendTimeCol - 1
    recvQtyCol = recvTimeCol - 1

    'Timing columns are immediately RIGHT of the Check columns
    Dim sendTimingCol As Long, recvTimingCol As Long
    sendTimingCol = sendCheckCol + 1
    recvTimingCol = recvCheckCol + 1

    Dim totalPieces As Long
Dim sentPieces As Long, deliveredPieces As Long
Dim sentOnTimePieces As Long

Dim r As Long
Dim customerCol As Long
Dim routeCol As Long

customerCol = SummaryCustomerColumn(ws)
routeCol = SUMMARY_ROUTE_COL_FIXED

For r = firstDataRow To lastRow
    'Only count real delivery rows
    If IsRealDeliveryLine(ws, r, orderCol, itemCol) Then

        If SummaryRowBelongsToActiveSheet(ws, r, customerCol, routeCol) Then

            Dim req As Long
            req = 1
            If qtyReqCol > 0 Then
                If IsNumeric(ws.Cells(r, qtyReqCol).Value) Then
                    req = CLng(ws.Cells(r, qtyReqCol).Value)
                    If req < 1 Then req = 1
                End If
            End If

            Dim sQty As Long, dQty As Long
            sQty = CLng(Val(ws.Cells(r, sendQtyCol).Value))
            dQty = CLng(Val(ws.Cells(r, recvQtyCol).Value))

            If sQty < 0 Then sQty = 0
            If dQty < 0 Then dQty = 0

            If sQty > req Then sQty = req
            If dQty > req Then dQty = req

            totalPieces = totalPieces + req
            sentPieces = sentPieces + sQty
            deliveredPieces = deliveredPieces + dQty

            Dim sTiming As String
            sTiming = Trim$(CStr(ws.Cells(r, sendTimingCol).Value))

            If sTiming = "On-Time" Or sTiming = "Early" Then
                sentOnTimePieces = sentOnTimePieces + sQty
            End If
        End If
    End If
Next r

If totalPieces <= 0 Then Exit Sub

Dim sentOnTimePct As Double, deliveredPct As Double
sentOnTimePct = sentOnTimePieces / totalPieces
deliveredPct = deliveredPieces / totalPieces

    Dim labelRow As Long, valueRow As Long
    labelRow = lastRow + 2
    valueRow = lastRow + 3

    ws.rows(labelRow).RowHeight = 12
    ws.rows(valueRow).RowHeight = 12

    'SEND SIDE
    ws.Cells(labelRow, sendTimeCol).Value = "Sent"
    ws.Cells(labelRow, sendCheckCol).Value = "Sent on Time %"

    With ws.Cells(valueRow, sendTimeCol)
        .NumberFormat = "@"
        .Value = CStr(sentPieces) & " / " & CStr(totalPieces)
    End With
    ws.Cells(valueRow, sendCheckCol).Value = sentOnTimePct
    ws.Cells(valueRow, sendCheckCol).NumberFormat = "0.0%"

    ws.Range(ws.Cells(labelRow, sendTimeCol), ws.Cells(labelRow, sendCheckCol)).Font.Bold = True
    ws.Range(ws.Cells(valueRow, sendTimeCol), ws.Cells(valueRow, sendCheckCol)).Font.Bold = True

        'RECV SIDE
    If UCase$(ws.Name) = UCase$("Outbound - Airport Rd") Then
        ws.Cells(labelRow, recvTimeCol).Value = "Inbound"
        ws.Cells(labelRow, recvCheckCol).Value = "Inbound % Complete"

        With ws.Cells(valueRow, recvTimeCol)
            .NumberFormat = "@"
            .Value = CStr(deliveredPieces) & " / " & CStr(totalPieces)
        End With
        ws.Cells(valueRow, recvCheckCol).Value = deliveredPct
        ws.Cells(valueRow, recvCheckCol).NumberFormat = "0.0%"

        ws.Range(ws.Cells(labelRow, recvTimeCol), ws.Cells(labelRow, recvCheckCol)).Font.Bold = True
        ws.Range(ws.Cells(valueRow, recvTimeCol), ws.Cells(valueRow, recvCheckCol)).Font.Bold = True
    Else
        With ws.Range(ws.Cells(labelRow, recvTimeCol), ws.Cells(valueRow, recvCheckCol))
            .ClearContents
            .Interior.Pattern = xlNone
            .Font.Bold = False
            .Font.ColorIndex = xlAutomatic
            .Borders.LineStyle = xlNone
        End With
    End If

    CreateOrUpdateSummaryTable ws, labelRow, totalPieces, sentPieces, sentOnTimePct, deliveredPieces, deliveredPct
End Sub

'=== Layout builder ===

'------------------------------------------------------------------------------
' Procedure: EnsureScanLayout
' Scope: Public Sub
'
' What it does:
'   Creates or repairs the scan input/status blocks on a delivery/scanner
'   sheet.
'
' Why it exists:
'   Imported or rebuilt sheets can lose layout pieces, so this makes sure the
'   columns needed by ProcessScan exist before scans run.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub EnsureScanLayout(ByVal ws As Worksheet)

    On Error Resume Next
    ws.Unprotect Password:=""
    On Error GoTo 0

    Dim sendScan As Range, recvScan As Range, stagingScan As Range
    Set sendScan = ws.Range(SCAN_CELL_SEND)       'P4
    Set recvScan = ws.Range(SCAN_CELL_RECV)       'Y4
    Set stagingScan = ws.Range(SCAN_CELL_STAGING) 'AP4

    'Layout:
    'Delivery list = A:N
    'Outbound      = O:W   (label O, data P:W)
    'Inbound       = X:AG  (label X, data Y:AG)
    'Staging       = AO:AV (label AO, data AP:AV)

    ws.rows(4).RowHeight = 20
    ws.rows(5).RowHeight = 15

    'Label columns
    ws.Columns("O").ColumnWidth = 18
    ws.Columns("X").ColumnWidth = 18
    ws.Columns("AO").ColumnWidth = 18

    'Outbound
    ws.Columns("P").ColumnWidth = 20
    ws.Columns("Q").ColumnWidth = 12
    ws.Columns("R").ColumnWidth = 10
    ws.Columns("S").ColumnWidth = 16
    ws.Columns("T").ColumnWidth = 25
    ws.Columns("U").ColumnWidth = 15
    ws.Columns("V").ColumnWidth = 15
    ws.Columns("W").ColumnWidth = 20

    'Inbound
    ws.Columns("Y").ColumnWidth = 20
    ws.Columns("Z").ColumnWidth = 12
    ws.Columns("AA").ColumnWidth = 10
    ws.Columns("AB").ColumnWidth = 16
    ws.Columns("AC").ColumnWidth = 25
    ws.Columns("AD").ColumnWidth = 15
    ws.Columns("AE").ColumnWidth = 0.01   'Unused
    ws.Columns("AF").ColumnWidth = 20  'Comments
    ws.Columns("AG").ColumnWidth = 15  'Bay Nr.
    ws.Columns("AE").EntireColumn.Hidden = True

    'Staging
    ws.Columns("AP").ColumnWidth = 20
    ws.Columns("AQ").ColumnWidth = 12
    ws.Columns("AR").ColumnWidth = 10
    ws.Columns("AS").ColumnWidth = 16
    ws.Columns("AT").ColumnWidth = 25
    ws.Columns("AU").ColumnWidth = 15
    ws.Columns("AV").ColumnWidth = 20

    ws.Range("O:W").HorizontalAlignment = xlCenter
    ws.Range("O:W").VerticalAlignment = xlCenter
    ws.Range("X:AG").HorizontalAlignment = xlCenter
    ws.Range("X:AG").VerticalAlignment = xlCenter
    ws.Range("AO:AV").HorizontalAlignment = xlCenter
    ws.Range("AO:AV").VerticalAlignment = xlCenter

    'Titles
    BuildTitle ws, sendScan.Offset(-1, 0), "Outbound - Airport Rd", sendScan.Column - 1, sendScan.Column + 7
    BuildTitle ws, recvScan.Offset(-1, 0), GetReceiveSheetName(), recvScan.Column - 1, recvScan.Column + 8
    BuildTitle ws, stagingScan.Offset(-1, 0), "Staging - Airport Rd", stagingScan.Column - 1, stagingScan.Column + 6

    'Most recent labels
    With ws.Range("O4")
        .Value = "Most Recent Scan:"
        .Font.Bold = True
        .HorizontalAlignment = xlRight
        .VerticalAlignment = xlCenter
    End With

    With ws.Range("X4")
        .Value = "Most Recent Scan:"
        .Font.Bold = True
        .HorizontalAlignment = xlRight
        .VerticalAlignment = xlCenter
    End With

    With ws.Range("AO4")
        .Value = "Most Recent Scan:"
        .Font.Bold = True
        .HorizontalAlignment = xlRight
        .VerticalAlignment = xlCenter
    End With

    'Scan input cells
    FormatScanCell sendScan
    FormatScanCell recvScan
    FormatScanCell stagingScan

    'Top time formats
    ws.Range("T4").NumberFormat = "m/d/yyyy h:mm AM/PM"
    ws.Range("AC4").NumberFormat = "m/d/yyyy h:mm AM/PM"
    ws.Range("AT4").NumberFormat = "m/d/yyyy h:mm AM/PM"

    Dim hdrRow As Long
    hdrRow = 5

    'Outbound headers
    ws.Range("P" & hdrRow).Value = HEADER_TEXT_BAR_SEND
    ws.Range("Q" & hdrRow).Value = "Order Nr."
    ws.Range("R" & hdrRow).Value = "Item Nr."
    ws.Range("S" & hdrRow).Value = HEADER_TEXT_QTY_SEND
    ws.Range("T" & hdrRow).Value = HEADER_TEXT_TIME_SEND
    ws.Range("U" & hdrRow).Value = HEADER_TEXT_CHECK_SEND
    ws.Range("V" & hdrRow).Value = "Delivery Timing"
    ws.Range("W" & hdrRow).Value = "Comments"

    'Inbound headers
    ws.Range("Y" & hdrRow).Value = HEADER_TEXT_BAR_RECV
    ws.Range("Z" & hdrRow).Value = "Order Nr."
    ws.Range("AA" & hdrRow).Value = "Item Nr."
    ws.Range("AB" & hdrRow).Value = HEADER_TEXT_QTY_RECV
    ws.Range("AC" & hdrRow).Value = HEADER_TEXT_TIME_RECV
    ws.Range("AD" & hdrRow).Value = HEADER_TEXT_CHECK_RECV
    ws.Range("AE" & hdrRow).ClearContents
    ws.Range("AF" & hdrRow).Value = "Comments"
    ws.Range("AG" & hdrRow).Value = "Bay Nr."

    'Staging headers
    ws.Range("AP" & hdrRow).Value = HEADER_TEXT_BAR_STAGING
    ws.Range("AQ" & hdrRow).Value = "Order Nr."
    ws.Range("AR" & hdrRow).Value = "Item Nr."
    ws.Range("AS" & hdrRow).Value = HEADER_TEXT_QTY_STAGING
    ws.Range("AT" & hdrRow).Value = HEADER_TEXT_TIME_STAGING
    ws.Range("AU" & hdrRow).Value = HEADER_TEXT_CHECK_STAGING
    ws.Range("AV" & hdrRow).Value = "Comments"

    EnsureMinColWidth ws, ws.Range("W1").Column, 18
    EnsureMinColWidth ws, ws.Range("AF1").Column, 18
    EnsureMinColWidth ws, ws.Range("AV1").Column, 18

    With ws.Range("P" & hdrRow & ":W" & hdrRow)
        .Font.Bold = True
        .Font.Underline = xlUnderlineStyleSingle
        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
    End With

    With ws.Range("Y" & hdrRow & ":AG" & hdrRow)
        .Font.Bold = True
        .Font.Underline = xlUnderlineStyleSingle
        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
    End With

    With ws.Range("AP" & hdrRow & ":AV" & hdrRow)
        .Font.Bold = True
        .Font.Underline = xlUnderlineStyleSingle
        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
    End With

    With ws.Range("O3:W3").Borders(xlEdgeLeft)
        .LineStyle = xlContinuous
        .Weight = xlThick
        .Color = RGB(0, 0, 0)
    End With

    With ws.Range("X3:AG3").Borders(xlEdgeLeft)
        .LineStyle = xlContinuous
        .Weight = xlThick
        .Color = RGB(0, 0, 0)
    End With

    With ws.Range("AO3:AV3").Borders(xlEdgeLeft)
        .LineStyle = xlContinuous
        .Weight = xlThick
        .Color = RGB(0, 0, 0)
    End With

    With ws.Range("O:O").Borders(xlEdgeLeft)
        .LineStyle = xlContinuous
        .Weight = xlThick
        .Color = RGB(0, 0, 0)
    End With

    With ws.Range("X:X").Borders(xlEdgeLeft)
        .LineStyle = xlContinuous
        .Weight = xlThick
        .Color = RGB(0, 0, 0)
    End With

    With ws.Range("AO:AO").Borders(xlEdgeLeft)
        .LineStyle = xlContinuous
        .Weight = xlThick
        .Color = RGB(0, 0, 0)
    End With

    FormatTimeColumns ws
End Sub

'------------------------------------------------------------------------------
' Procedure: BuildTitle
' Scope: Private Sub
'
' What it does:
'   Builds a derived value, key, JSON block, layout, collection, or workbook
'   object used later by the workflow (BuildTitle).
'
' Why it exists:
'   The project uses generated keys/layouts to keep repeated logic consistent
'   instead of hand-building values in multiple places.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub BuildTitle(ByVal ws As Worksheet, ByVal anchor As Range, ByVal txt As String, ByVal colL As Long, ByVal colR As Long)
    Dim r As Range
    Set r = ws.Range(ws.Cells(anchor.Row, colL), ws.Cells(anchor.Row, colR))
    If r.MergeCells Then r.UnMerge
    r.Merge

    With r
        .Value = txt
        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
        .Font.Bold = True
        .Font.Size = 18
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: FormatScanCell
' Scope: Private Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   FormatScanCell.
'
' Why it exists:
'   Scan results directly affect staged/outbound/received quantities, so this
'   rule keeps the visible sheet and downstream queue result accurate.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub FormatScanCell(ByVal c As Range)
    With c
        .Interior.Color = RGB(198, 239, 206)
        .Font.Color = RGB(0, 97, 0)
        .Font.Bold = True
        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
        .Borders.LineStyle = xlContinuous
        .Borders.Weight = xlThin
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: FormatYellowPartial
' Scope: Private Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   FormatYellowPartial.
'
' Why it exists:
'   Remakes need separate visual and print/export handling so replacement
'   glass is not confused with regular delivery-list work.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub FormatYellowPartial(ByVal c As Range)
    With c
        .Interior.Color = RGB(255, 242, 204)
        .Font.Color = RGB(156, 101, 0)
        .Font.Bold = True
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplyDeliveryListRowProgressFill
' Scope: Private Sub
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   ApplyDeliveryListRowProgressFill.
'
' Why it exists:
'   Rows may represent real orders, section headers, remakes, Greenville work,
'   Customer Pickup work, or updated rows; each type needs different handling.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ApplyDeliveryListRowProgressFill(ByVal ws As Worksheet, ByVal rowNum As Long, ByVal statusText As String)
    Dim rowBand As Range

    Set rowBand = ws.Range("A" & rowNum & ":M" & rowNum)

    With rowBand
        Select Case True
            Case statusText = "OK" Or statusText = "Received"
                .Interior.Color = RGB(235, 247, 228)
                .Font.Color = RGB(0, 97, 0)
                .Font.Bold = False

            Case Left$(statusText, 7) = "Partial "
                .Interior.Color = RGB(255, 249, 230)
                .Font.Color = RGB(156, 101, 0)
                .Font.Bold = False

            Case statusText = "Mismatch"
                .Interior.Color = RGB(255, 235, 235)
                .Font.Color = RGB(156, 0, 6)
                .Font.Bold = False
        End Select
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: GetDeliveryListDate
' Scope: Private Function
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   GetDeliveryListDate.
'
' Why it exists:
'   Delivery timing, queue timestamps, and scan timestamps drive status
'   messages such as Early, On-Time, Late, Processing, and Done.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetDeliveryListDate(ByVal ws As Worksheet) As Date
    Dim searchRng As Range
    Dim c As Range
    Dim txt As String
    Dim tailTxt As String
    Dim i As Long
    Dim ch As String

    Set searchRng = ws.Range("A1:AG5")

    '1) First, support the NEW normalized title:
    '   "DELIVERY LIST FOR 4/2/2026" in one merged/text cell.
    For Each c In searchRng.Cells
        txt = Trim$(CStr(c.Value))
        If Len(txt) > 0 Then
            If InStr(1, UCase$(txt), "DELIVERY LIST FOR", vbTextCompare) > 0 Then
                tailTxt = Trim$(Replace$(UCase$(txt), "DELIVERY LIST FOR", "", 1, 1, vbTextCompare))

                If Len(tailTxt) > 0 Then
                    If IsDate(tailTxt) Then
                        GetDeliveryListDate = DateValue(CDate(tailTxt))
                        Exit Function
                    End If
                End If

                'Fallback: pull just date-like characters out of the title text
                tailTxt = ""
                For i = 1 To Len(txt)
                    ch = Mid$(txt, i, 1)
                    If (ch >= "0" And ch <= "9") Or ch = "/" Or ch = "-" Then
                        tailTxt = tailTxt & ch
                    ElseIf Len(tailTxt) > 0 Then
                        'stop once we've started capturing a date and hit other text
                    End If
                Next i

                If Len(tailTxt) > 0 Then
                    If IsDate(tailTxt) Then
                        GetDeliveryListDate = DateValue(CDate(tailTxt))
                        Exit Function
                    End If
                End If
            End If
        End If
    Next c

    '2) Legacy support: find a standalone date on the same row as "DELIVERY LIST FOR"
    Dim hdr As Range
    Set hdr = searchRng.Find(What:="DELIVERY LIST FOR", LookIn:=xlValues, LookAt:=xlPart)

    If Not hdr Is Nothing Then
        For Each c In ws.Range(ws.Cells(hdr.Row, hdr.Column), ws.Cells(hdr.Row, ws.Columns.Count)).Cells
            If IsDate(c.Value) Then
                GetDeliveryListDate = DateValue(c.Value)
                Exit Function
            End If
        Next c
    End If

    '3) Legacy fallback: any standalone date in top area
    For Each c In ws.Range("A1:AG3").Cells
        If IsDate(c.Value) Then
            GetDeliveryListDate = DateValue(c.Value)
            Exit Function
        End If
    Next c

    GetDeliveryListDate = 0
End Function

'------------------------------------------------------------------------------
' Procedure: DeliveryTimingText
' Scope: Private Function
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   DeliveryTimingText.
'
' Why it exists:
'   Delivery timing, queue timestamps, and scan timestamps drive status
'   messages such as Early, On-Time, Late, Processing, and Done.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function DeliveryTimingText(ByVal deliveryDate As Date, ByVal scanDateTime As Date) As String
    If deliveryDate = 0 Then
        DeliveryTimingText = ""
        Exit Function
    End If

    Dim scanD As Date
    scanD = DateValue(scanDateTime)

    If scanD < deliveryDate Then
        DeliveryTimingText = "Early"
    ElseIf scanD > deliveryDate Then
        DeliveryTimingText = "Late"
    Else
        DeliveryTimingText = "On-Time"
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: FormatDeliveryTiming
' Scope: Private Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   FormatDeliveryTiming.
'
' Why it exists:
'   Remakes need separate visual and print/export handling so replacement
'   glass is not confused with regular delivery-list work.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub FormatDeliveryTiming(ByVal c As Range, ByVal timing As String)
    With c
        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
        .Font.Bold = True

        Select Case timing
            Case "Late"
                .Interior.Color = RGB(255, 199, 206)
                .Font.Color = RGB(156, 0, 6)
            Case "Early"
                .Interior.Color = RGB(221, 235, 247)
                .Font.Color = RGB(0, 32, 96)
            Case "On-Time"
                .Interior.Color = RGB(198, 239, 206)
                .Font.Color = RGB(0, 97, 0)
            Case Else
                .Interior.Pattern = xlNone
                .Font.ColorIndex = xlAutomatic
                .Font.Bold = False
        End Select
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: FormatTimeColumns
' Scope: Private Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   FormatTimeColumns.
'
' Why it exists:
'   Remakes need separate visual and print/export handling so replacement
'   glass is not confused with regular delivery-list work.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub FormatTimeColumns(ByVal ws As Worksheet)
    Dim sendTimeHdr As Range, recvTimeHdr As Range
    Set sendTimeHdr = FindHeaderCell(ws, Array(HEADER_TEXT_TIME_SEND, "Date & TimeScanned"))
    Set recvTimeHdr = FindHeaderCell(ws, Array(HEADER_TEXT_TIME_RECV, "Date & TimeReceived"))

    If Not sendTimeHdr Is Nothing Then
        ws.Columns(sendTimeHdr.Column).NumberFormat = "m/d/yyyy h:mm AM/PM"
    End If

    If Not recvTimeHdr Is Nothing Then
        ws.Columns(recvTimeHdr.Column).NumberFormat = "m/d/yyyy h:mm AM/PM"
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: FormatQtyMismatchRed
' Scope: Private Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   FormatQtyMismatchRed.
'
' Why it exists:
'   Scan results directly affect staged/outbound/received quantities, so this
'   rule keeps the visible sheet and downstream queue result accurate.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub FormatQtyMismatchRed(ByVal c As Range)
    With c
        .Interior.Color = RGB(255, 199, 206)
        .Font.Color = RGB(156, 0, 6)
        .Font.Bold = True
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: ClearQtyMismatchRed
' Scope: Private Sub
'
' What it does:
'   Reads, caps, validates, compares, or formats quantity values for
'   ClearQtyMismatchRed.
'
' Why it exists:
'   Scan results directly affect staged/outbound/received quantities, so this
'   rule keeps the visible sheet and downstream queue result accurate.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ClearQtyMismatchRed(ByVal c As Range)
    With c
        .Interior.Pattern = xlNone
        .Font.ColorIndex = xlAutomatic
        .Font.Bold = False
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: AppendOverrideComment
' Scope: Private Sub
'
' What it does:
'   Appends text or state to an existing cell/message for
'   AppendOverrideComment.
'
' Why it exists:
'   Append helpers preserve prior context while adding audit or override
'   information for the operator.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub AppendOverrideComment(ByVal c As Range, ByVal msg As String)
    Dim cur As String
    cur = Trim$(CStr(c.Value))

    If Len(cur) = 0 Then
        c.Value = msg
    ElseIf InStr(1, cur, msg, vbTextCompare) = 0 Then
        c.Value = cur & " | " & msg
    End If

    c.WrapText = False
    c.HorizontalAlignment = xlCenter
    c.VerticalAlignment = xlCenter
End Sub

'------------------------------------------------------------------------------
' Procedure: EnsureMinColWidth
' Scope: Private Sub
'
' What it does:
'   Finds, sizes, hides, formats, or uses worksheet columns for
'   EnsureMinColWidth.
'
' Why it exists:
'   The system depends on fixed scan blocks and discovered delivery-list
'   columns, so column handling must be centralized and predictable.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub EnsureMinColWidth(ByVal ws As Worksheet, ByVal colNum As Long, ByVal minWidth As Double)
    If colNum <= 0 Then Exit Sub
    If ws.Columns(colNum).ColumnWidth < minWidth Then
        ws.Columns(colNum).ColumnWidth = minWidth
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: AutoFitCommentsCol
' Scope: Private Sub
'
' What it does:
'   Finds, sizes, hides, formats, or uses worksheet columns for
'   AutoFitCommentsCol.
'
' Why it exists:
'   The system depends on fixed scan blocks and discovered delivery-list
'   columns, so column handling must be centralized and predictable.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub AutoFitCommentsCol(ByVal ws As Worksheet, ByVal commentsCol As Long, Optional ByVal maxWidth As Double = 80)
    If commentsCol <= 0 Then Exit Sub

    On Error Resume Next
    ws.Columns(commentsCol).AutoFit
    If ws.Columns(commentsCol).ColumnWidth > maxWidth Then
        ws.Columns(commentsCol).ColumnWidth = maxWidth
    End If
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: FormatMismatchStatus
' Scope: Private Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   FormatMismatchStatus.
'
' Why it exists:
'   Scan results directly affect staged/outbound/received quantities, so this
'   rule keeps the visible sheet and downstream queue result accurate.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub FormatMismatchStatus(ByVal c As Range)
    With c
        .Interior.Color = RGB(255, 199, 206)
        .Font.Color = RGB(156, 0, 6)
        .Font.Bold = True
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: FormatStatusCellByValue
' Scope: Private Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   FormatStatusCellByValue.
'
' Why it exists:
'   Scan results directly affect staged/outbound/received quantities, so this
'   rule keeps the visible sheet and downstream queue result accurate.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub FormatStatusCellByValue(ByVal c As Range, ByVal statusText As String)
    If statusText = "Mismatch" Then
        FormatMismatchStatus c
    ElseIf statusText = "Received" Or statusText = "OK" Then
        FormatGreenStatus c
    ElseIf Left$(statusText, 7) = "Partial " Then
        FormatYellowPartial c
    Else
        ClearStatusFormat c
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: UpdateRecvCheckCell
' Scope: Private Sub
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   UpdateRecvCheckCell.
'
' Why it exists:
'   Delivery timing, queue timestamps, and scan timestamps drive status
'   messages such as Early, On-Time, Late, Processing, and Done.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub UpdateRecvCheckCell( _
    ByVal ws As Worksheet, _
    ByVal rowNum As Long, _
    ByVal recvCheckCol As Long, _
    ByVal recvQty As Long, _
    ByVal sentQty As Long, _
    ByVal requiredQty As Long)

    Dim c As Range
    Dim status As String

    Set c = ws.Cells(rowNum, recvCheckCol)

    If recvQty <= 0 Then
        c.ClearContents
        ClearStatusFormat c
        Exit Sub
    End If

    If recvQty > sentQty Then
        status = "Mismatch"
    ElseIf recvQty >= requiredQty Then
        status = "Received"
    Else
        status = "Partial " & CStr(recvQty) & "/" & CStr(requiredQty)
    End If

    c.Value = status
    FormatStatusCellByValue c, status
End Sub

'------------------------------------------------------------------------------
' Procedure: IsSummaryReceiveSheetName
' Scope: Public Function
'
' What it does:
'   Calculates or updates summary/banner information shown at the top of
'   delivery/scanner sheets for IsSummaryReceiveSheetName.
'
' Why it exists:
'   Operators use those summary panels to quickly see staged, outbound,
'   inbound, and completion progress without manually counting rows.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function IsSummaryReceiveSheetName(ByVal sheetName As String) As Boolean
    Dim nm As String

    nm = UCase$(Trim$(sheetName))

    IsSummaryReceiveSheetName = _
        (nm = UCase$(GetReceiveSheetName()) Or _
         nm = UCase$(SUMMARY_GREENVILLE_SHEET_NAME) Or _
         nm = UCase$(SUMMARY_CPU_SHEET_NAME))
End Function

'------------------------------------------------------------------------------
' Procedure: CreateOrUpdateSummaryTable
' Scope: Public Sub
'
' What it does:
'   Calculates or updates summary/banner information shown at the top of
'   delivery/scanner sheets for CreateOrUpdateSummaryTable.
'
' Why it exists:
'   Operators use those summary panels to quickly see staged, outbound,
'   inbound, and completion progress without manually counting rows.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub CreateOrUpdateSummaryTable( _
    ByVal ws As Worksheet, _
    ByVal labelRow As Long, _
    ByVal totalPieces As Long, _
    ByVal sentPieces As Long, _
    ByVal sentOnTimePct As Double, _
    ByVal deliveredPieces As Long, _
    ByVal deliveredPct As Double)

    Dim listDate As Date
    listDate = GetDeliveryListDate(ws)

    'Start to the right of AG so it does not collide with the scanner layout
    Dim startCol As Long
    startCol = ws.Range("AX1").Column

    Dim rng As Range
    Set rng = ws.Range(ws.Cells(labelRow, startCol), ws.Cells(labelRow + 1, startCol + 5))

    'Force the summary area visible
    On Error Resume Next
    ws.Unprotect Password:=""
    rng.EntireRow.Hidden = False
    rng.EntireColumn.Hidden = False
    On Error GoTo 0

    rng.rows(1).Value = Array( _
    "List Date", _
    "Total Pieces", _
    "Sent Pieces", _
    "Sent on Time %", _
    "Inbound Pieces", _
    "Inbound % Complete")

rng.rows(2).Value = Array( _
    IIf(listDate = 0, "", listDate), _
    totalPieces, _
    sentPieces, _
    sentOnTimePct, _
    deliveredPieces, _
    deliveredPct)

    rng.Columns(1).NumberFormat = "m/d/yyyy"
    rng.Columns(4).NumberFormat = "0.0%"
    rng.Columns(6).NumberFormat = "0.0%"

    rng.rows(1).Font.Bold = True

    Dim lo As ListObject

    On Error Resume Next
    Set lo = ws.ListObjects("tblDeliverySummary")
    On Error GoTo 0

    If lo Is Nothing Then
        Set lo = ws.ListObjects.Add(xlSrcRange, rng, , xlYes)
        lo.Name = "tblDeliverySummary"
        lo.TableStyle = "TableStyleLight9"
    Else
        On Error Resume Next
        lo.Resize rng
        If Err.Number <> 0 Then
            Err.Clear
            lo.Delete
            Set lo = ws.ListObjects.Add(xlSrcRange, rng, , xlYes)
            lo.Name = "tblDeliverySummary"
            lo.TableStyle = "TableStyleLight9"
        End If
        On Error GoTo 0
    End If
    
        If IsSummaryReceiveSheetName(ws.Name) Then
        ThisWorkbook.RefreshReceiveLocationSummary ws
    Else
        CreateOrUpdateTopSummaryPanels ws
    End If
    
    'Make absolutely sure the created/resized table is visible
    On Error Resume Next
    lo.Range.EntireRow.Hidden = False
    lo.Range.EntireColumn.Hidden = False
    On Error GoTo 0
    
End Sub

'------------------------------------------------------------------------------
' Procedure: SetTopBanner
' Scope: Private Sub
'
' What it does:
'   Calculates or updates summary/banner information shown at the top of
'   delivery/scanner sheets for SetTopBanner.
'
' Why it exists:
'   Operators use those summary panels to quickly see staged, outbound,
'   inbound, and completion progress without manually counting rows.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub SetTopBanner(ByVal rng As Range, ByVal bannerText As String, ByVal fillColor As Long)
    On Error Resume Next
    rng.MergeArea.UnMerge
    On Error GoTo 0

    rng.Merge

    With rng
        .Cells(1, 1).Value = bannerText
        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
        .Font.Bold = True
        .Font.Size = 12
        .Font.Color = RGB(255, 255, 255)
        .Interior.Color = fillColor
        .Borders.LineStyle = xlContinuous
        .Borders.Weight = xlThin
        .WrapText = False
    End With

    rng.RowHeight = 24
End Sub

'------------------------------------------------------------------------------
' Procedure: BannerPctText
' Scope: Private Function
'
' What it does:
'   Calculates or updates summary/banner information shown at the top of
'   delivery/scanner sheets for BannerPctText.
'
' Why it exists:
'   Operators use those summary panels to quickly see staged, outbound,
'   inbound, and completion progress without manually counting rows.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BannerPctText(ByVal num As Double, ByVal den As Double) As String
    If den <= 0 Then
        BannerPctText = "0.0%"
    Else
        BannerPctText = Format$(num / den, "0.0%")
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: CappedQty
' Scope: Private Function
'
' What it does:
'   Reads, caps, validates, compares, or formats quantity values for
'   CappedQty.
'
' Why it exists:
'   Scan results directly affect staged/outbound/received quantities, so this
'   rule keeps the visible sheet and downstream queue result accurate.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function CappedQty(ByVal v As Variant, ByVal req As Long) As Long
    Dim q As Long

    q = CLng(Val(v))
    If q < 0 Then q = 0
    If q > req Then q = req

    CappedQty = q
End Function

'------------------------------------------------------------------------------
' Procedure: CreateOrUpdateTopSummaryPanels
' Scope: Public Sub
'
' What it does:
'   Calculates or updates summary/banner information shown at the top of
'   delivery/scanner sheets for CreateOrUpdateTopSummaryPanels.
'
' Why it exists:
'   Operators use those summary panels to quickly see staged, outbound,
'   inbound, and completion progress without manually counting rows.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Sub CreateOrUpdateTopSummaryPanels(ByVal ws As Worksheet)
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim qtyHdr As Range

    Dim sendQtyHdr As Range
    Dim sendCheckHdr As Range

    Dim recvQtyHdr As Range
    Dim recvCheckHdr As Range

    Dim stagingQtyHdr As Range

    Dim firstDataRow As Long
    Dim lastRow As Long
    Dim r As Long

    Dim totalQty As Long
    Dim stagedQty As Long
    Dim outboundQty As Long
    Dim inboundQty As Long
    Dim outboundOnTimeQty As Long

    Dim req As Long
    Dim sendTiming As String
    Dim sendStatus As String

    Dim outboundText As String
    Dim inboundText As String
    Dim stagingText As String

    Set orderHdr = FindHeaderCellInCols(ws, Array(HEADER_TEXT_ORDER), "A:N", 250)
    Set itemHdr = FindHeaderCellInCols(ws, Array(HEADER_TEXT_ITEM), "A:N", 250)
    Set qtyHdr = FindHeaderCellInCols(ws, Array("Qty.", "Qty", "Quantity"), "A:N", 250)

    Set sendQtyHdr = FindHeaderCellInCols(ws, Array(HEADER_TEXT_QTY_SEND), "P:W", 60)
    Set sendCheckHdr = FindHeaderCellInCols(ws, Array(HEADER_TEXT_CHECK_SEND), "P:W", 60)

    Set recvQtyHdr = FindHeaderCellInCols(ws, Array(HEADER_TEXT_QTY_RECV), "Y:AG", 60)
    Set recvCheckHdr = FindHeaderCellInCols(ws, Array(HEADER_TEXT_CHECK_RECV), "Y:AG", 60)

    Set stagingQtyHdr = FindHeaderCellInCols(ws, Array(HEADER_TEXT_QTY_STAGING), "AP:AV", 60)

    If orderHdr Is Nothing Then Exit Sub
    If itemHdr Is Nothing Then Exit Sub
    If qtyHdr Is Nothing Then Exit Sub
    If sendQtyHdr Is Nothing Or sendCheckHdr Is Nothing Then Exit Sub
    If recvQtyHdr Is Nothing Or recvCheckHdr Is Nothing Then Exit Sub
    If stagingQtyHdr Is Nothing Then Exit Sub

    firstDataRow = orderHdr.Row + 1
    lastRow = ws.Cells(ws.rows.Count, orderHdr.Column).End(xlUp).Row
    If lastRow < firstDataRow Then lastRow = firstDataRow

    totalQty = 0
    stagedQty = 0
    outboundQty = 0
    inboundQty = 0
    outboundOnTimeQty = 0

    For r = firstDataRow To lastRow
        If IsRealDeliveryLine(ws, r, orderHdr.Column, itemHdr.Column) Then
            req = 1
            If IsNumeric(ws.Cells(r, qtyHdr.Column).Value) Then
                req = CLng(Val(ws.Cells(r, qtyHdr.Column).Value))
                If req < 1 Then req = 1
            End If

            totalQty = totalQty + req
            stagedQty = stagedQty + CappedQty(ws.Cells(r, stagingQtyHdr.Column).Value, req)
            outboundQty = outboundQty + CappedQty(ws.Cells(r, sendQtyHdr.Column).Value, req)
            inboundQty = inboundQty + CappedQty(ws.Cells(r, recvQtyHdr.Column).Value, req)

            sendStatus = UCase$(Trim$(CStr(ws.Cells(r, sendCheckHdr.Column).Value)))
            sendTiming = UCase$(Trim$(CStr(ws.Cells(r, sendCheckHdr.Column + 1).Value)))

            If sendStatus = "OK" Then
                If sendTiming = "ON-TIME" Or sendTiming = "EARLY" Then
                    outboundOnTimeQty = outboundOnTimeQty + req
                End If
            End If
        End If
    Next r

    outboundText = "Outbound Qty: " & outboundQty & "/" & totalQty & _
                   " â€¢ " & BannerPctText(outboundOnTimeQty, totalQty) & " On Time"

    inboundText = "Inbound Qty: " & inboundQty & "/" & totalQty & _
                  " â€¢ " & BannerPctText(inboundQty, totalQty) & " Complete"

    stagingText = "Staged Qty: " & stagedQty & "/" & totalQty & _
                  " â€¢ " & BannerPctText(stagedQty, totalQty) & " Complete"

    SetTopBanner ws.Range("O2:W2"), outboundText, RGB(0, 123, 167)
    SetTopBanner ws.Range("X2:AG2"), inboundText, RGB(40, 167, 69)
    SetTopBanner ws.Range("AO2:AV2"), stagingText, RGB(108, 117, 125)
End Sub

'------------------------------------------------------------------------------
' Procedure: SummaryOrderKeyText
' Scope: Private Function
'
' What it does:
'   Calculates or updates summary/banner information shown at the top of
'   delivery/scanner sheets for SummaryOrderKeyText.
'
' Why it exists:
'   Operators use those summary panels to quickly see staged, outbound,
'   inbound, and completion progress without manually counting rows.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SummaryOrderKeyText(ByVal rawValue As Variant) As String
    Dim s As String

    s = CStr(rawValue)
    s = Replace$(s, Chr$(160), " ")
    On Error Resume Next
    s = Application.WorksheetFunction.Clean(s)
    s = Application.WorksheetFunction.Trim(s)
    On Error GoTo 0

    SummaryOrderKeyText = Trim$(s)
End Function

'------------------------------------------------------------------------------
' Procedure: SummaryCleanCompareText
' Scope: Private Function
'
' What it does:
'   Calculates or updates summary/banner information shown at the top of
'   delivery/scanner sheets for SummaryCleanCompareText.
'
' Why it exists:
'   Operators use those summary panels to quickly see staged, outbound,
'   inbound, and completion progress without manually counting rows.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SummaryCleanCompareText(ByVal rawValue As Variant) As String
    Dim s As String

    s = CStr(rawValue)
    s = Replace$(s, Chr$(160), " ")
    On Error Resume Next
    s = Application.WorksheetFunction.Clean(s)
    s = Application.WorksheetFunction.Trim(s)
    On Error GoTo 0

    SummaryCleanCompareText = UCase$(Trim$(s))
End Function

'------------------------------------------------------------------------------
' Procedure: SummaryOrderColumn
' Scope: Private Function
'
' What it does:
'   Calculates or updates summary/banner information shown at the top of
'   delivery/scanner sheets for SummaryOrderColumn.
'
' Why it exists:
'   Operators use those summary panels to quickly see staged, outbound,
'   inbound, and completion progress without manually counting rows.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SummaryOrderColumn(ByVal ws As Worksheet) As Long
    Dim hdr As Range

    Set hdr = FindHeaderCellInCols(ws, Array(HEADER_TEXT_ORDER), "A:N", 250)
    If Not hdr Is Nothing Then SummaryOrderColumn = hdr.Column
End Function

'------------------------------------------------------------------------------
' Procedure: SummaryItemColumn
' Scope: Private Function
'
' What it does:
'   Calculates or updates summary/banner information shown at the top of
'   delivery/scanner sheets for SummaryItemColumn.
'
' Why it exists:
'   Operators use those summary panels to quickly see staged, outbound,
'   inbound, and completion progress without manually counting rows.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SummaryItemColumn(ByVal ws As Worksheet) As Long
    Dim hdr As Range

    Set hdr = FindHeaderCellInCols(ws, Array(HEADER_TEXT_ITEM), "A:N", 250)
    If Not hdr Is Nothing Then SummaryItemColumn = hdr.Column
End Function

'------------------------------------------------------------------------------
' Procedure: SummaryGetOrderScopeFlags
' Scope: Private Sub
'
' What it does:
'   Calculates or updates summary/banner information shown at the top of
'   delivery/scanner sheets for SummaryGetOrderScopeFlags.
'
' Why it exists:
'   Operators use those summary panels to quickly see staged, outbound,
'   inbound, and completion progress without manually counting rows.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub SummaryGetOrderScopeFlags(ByVal ws As Worksheet, _
                                      ByVal rowNum As Long, _
                                      ByRef isGreenville As Boolean, _
                                      ByRef isCPU As Boolean, _
                                      Optional ByVal orderCol As Long = 0, _
                                      Optional ByVal itemCol As Long = 0, _
                                      Optional ByVal customerCol As Long = 0, _
                                      Optional ByVal routeCol As Long = 0)
    Dim firstDataRow As Long
    Dim lastRow As Long
    Dim r As Long
    Dim orderKey As String
    Dim testOrderKey As String
    Dim orderHdr As Range

    isGreenville = False
    isCPU = False

    If orderCol = 0 Then orderCol = SummaryOrderColumn(ws)
    If itemCol = 0 Then itemCol = SummaryItemColumn(ws)
    If customerCol = 0 Then customerCol = SummaryCustomerColumn(ws)
    If routeCol = 0 Then routeCol = SUMMARY_ROUTE_COL_FIXED

    If orderCol = 0 Or itemCol = 0 Then Exit Sub
    If rowNum < 1 Then Exit Sub
    If Not IsRealDeliveryLine(ws, rowNum, orderCol, itemCol) Then Exit Sub

    orderKey = SummaryOrderKeyText(ws.Cells(rowNum, orderCol).Value)
    If Len(orderKey) = 0 Then Exit Sub

    Set orderHdr = FindHeaderCellInCols(ws, Array(HEADER_TEXT_ORDER), "A:N", 250)
    If orderHdr Is Nothing Then Exit Sub

    firstDataRow = orderHdr.Row + 1
    lastRow = ws.Cells(ws.rows.Count, orderCol).End(xlUp).Row
    If lastRow < firstDataRow Then Exit Sub

    For r = firstDataRow To lastRow
        If IsRealDeliveryLine(ws, r, orderCol, itemCol) Then
            testOrderKey = SummaryOrderKeyText(ws.Cells(r, orderCol).Value)

            If StrComp(testOrderKey, orderKey, vbTextCompare) = 0 Then
                If routeCol > 0 Then
                    If SummaryCleanCompareText(ws.Cells(r, routeCol).Value) = UCase$(SUMMARY_CPU_ROUTE_TEXT) Then
                        isCPU = True
                    End If
                End If

                If customerCol > 0 Then
                    If SummaryCleanCompareText(ws.Cells(r, customerCol).Value) = UCase$(SUMMARY_GREENVILLE_CUSTOMER_TEXT) Then
                        isGreenville = True
                    End If
                End If

                If isCPU And isGreenville Then Exit For
            End If
        End If
    Next r
End Sub

'------------------------------------------------------------------------------
' Procedure: SummaryCleanText
' Scope: Private Function
'
' What it does:
'   Calculates or updates summary/banner information shown at the top of
'   delivery/scanner sheets for SummaryCleanText.
'
' Why it exists:
'   Operators use those summary panels to quickly see staged, outbound,
'   inbound, and completion progress without manually counting rows.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SummaryCleanText(ByVal rawValue As Variant) As String
    Dim s As String

    s = CStr(rawValue)
    s = Replace$(s, Chr$(160), " ")

    On Error Resume Next
    s = Application.WorksheetFunction.Clean(s)
    s = Application.WorksheetFunction.Trim(s)
    On Error GoTo 0

    SummaryCleanText = UCase$(Trim$(s))
End Function

'------------------------------------------------------------------------------
' Procedure: SummaryCustomerColumn
' Scope: Public Function
'
' What it does:
'   Calculates or updates summary/banner information shown at the top of
'   delivery/scanner sheets for SummaryCustomerColumn.
'
' Why it exists:
'   Operators use those summary panels to quickly see staged, outbound,
'   inbound, and completion progress without manually counting rows.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function SummaryCustomerColumn(ByVal ws As Worksheet) As Long
    Dim custHdr As Range

    Set custHdr = FindHeaderCellInCols(ws, Array("Customer"), "A:N", 250)
    If Not custHdr Is Nothing Then SummaryCustomerColumn = custHdr.Column
End Function

'------------------------------------------------------------------------------
' Procedure: SummaryRowIsGreenville
' Scope: Private Function
'
' What it does:
'   Calculates or updates summary/banner information shown at the top of
'   delivery/scanner sheets for SummaryRowIsGreenville.
'
' Why it exists:
'   Operators use those summary panels to quickly see staged, outbound,
'   inbound, and completion progress without manually counting rows.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SummaryRowIsGreenville(ByVal ws As Worksheet, ByVal rowNum As Long, Optional ByVal customerCol As Long = 0) As Boolean
    If customerCol = 0 Then customerCol = SummaryCustomerColumn(ws)
    If customerCol = 0 Then Exit Function
    If rowNum < 1 Then Exit Function

    SummaryRowIsGreenville = _
        (SummaryCleanText(ws.Cells(rowNum, customerCol).Value) = UCase$(SUMMARY_GREENVILLE_CUSTOMER_TEXT))
End Function

'------------------------------------------------------------------------------
' Procedure: SummaryRowIsCPU
' Scope: Private Function
'
' What it does:
'   Calculates or updates summary/banner information shown at the top of
'   delivery/scanner sheets for SummaryRowIsCPU.
'
' Why it exists:
'   Operators use those summary panels to quickly see staged, outbound,
'   inbound, and completion progress without manually counting rows.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SummaryRowIsCPU(ByVal ws As Worksheet, ByVal rowNum As Long, Optional ByVal routeCol As Long = 0) As Boolean
    If routeCol = 0 Then routeCol = SUMMARY_ROUTE_COL_FIXED
    If routeCol = 0 Then Exit Function
    If rowNum < 1 Then Exit Function

    SummaryRowIsCPU = _
        (SummaryCleanText(ws.Cells(rowNum, routeCol).Value) = UCase$(SUMMARY_CPU_ROUTE_TEXT))
End Function

'------------------------------------------------------------------------------
' Procedure: SummaryRowBelongsToActiveSheet
' Scope: Public Function
'
' What it does:
'   Calculates or updates summary/banner information shown at the top of
'   delivery/scanner sheets for SummaryRowBelongsToActiveSheet.
'
' Why it exists:
'   Operators use those summary panels to quickly see staged, outbound,
'   inbound, and completion progress without manually counting rows.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function SummaryRowBelongsToActiveSheet(ByVal ws As Worksheet, ByVal rowNum As Long, _
                                               Optional ByVal customerCol As Long = 0, _
                                               Optional ByVal routeCol As Long = 0) As Boolean
    Dim isGreenville As Boolean
    Dim isCPU As Boolean
    Dim sheetNm As String

    sheetNm = UCase$(Trim$(ws.Name))
    isGreenville = SummaryRowIsGreenville(ws, rowNum, customerCol)
    isCPU = SummaryRowIsCPU(ws, rowNum, routeCol)

    Select Case sheetNm
        Case UCase$(SUMMARY_CPU_SHEET_NAME)
            SummaryRowBelongsToActiveSheet = isCPU

        Case UCase$(SUMMARY_GREENVILLE_SHEET_NAME)
            SummaryRowBelongsToActiveSheet = isGreenville And (Not isCPU)

        Case UCase$(GetReceiveSheetName())
            SummaryRowBelongsToActiveSheet = (Not isGreenville) And (Not isCPU)

        Case Else
            SummaryRowBelongsToActiveSheet = True
    End Select
End Function

'------------------------------------------------------------------------------
' Procedure: IsRealDeliveryLine
' Scope: Private Function
'
' What it does:
'   Returns a True/False decision used by higher-level workflow code
'   (IsRealDeliveryLine).
'
' Why it exists:
'   Boolean helpers make business rules readable and keep condition checks
'   consistent across modules.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function IsRealDeliveryLine(ByVal ws As Worksheet, ByVal rowNum As Long, ByVal orderCol As Long, ByVal itemCol As Long) As Boolean
    Dim vOrder As Variant
    Dim vItem As Variant

    vOrder = ws.Cells(rowNum, orderCol).Value
    vItem = ws.Cells(rowNum, itemCol).Value

    IsRealDeliveryLine = False

    If IsNumeric(vOrder) And IsNumeric(vItem) Then
        If CLng(Val(vOrder)) > 0 Then
            IsRealDeliveryLine = True
        End If
    End If
End Function


