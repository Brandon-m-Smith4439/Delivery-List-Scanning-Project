Attribute VB_Name = "modScanAudit"
Option Explicit

'==============================================================================
' Module: modScanAudit
' Workbook: Intake_Scanning_Test.xlsm / Intake scanner workbook
'
' What this module does:
'   Hidden audit log for intake scans. It records buffered scan details, send
'   status, queue status, result code/message, processed time, and last-seen
'   time.
'
' Why this module exists:
'   The audit sheet gives a troubleshooting trail when an operator says a scan
'   was made but the final queue result is unclear.
'
' Commenting standard used in this rewrite:
'   Comments explain both what each procedure/section does and why it
'   matters to the scanning, SharePoint, Power Automate, buffering, and
'   operator-safety workflow. The code behavior and public procedure names
'   are intentionally kept stable so existing buttons/forms/timers keep working.
'==============================================================================


'modScanAudit'

Public Const SCAN_AUDIT_SHEET_NAME As String = "__SCAN_AUDIT__"
Private Const SCAN_AUDIT_RETENTION_DAYS As Long = 3

'------------------------------------------------------------------------------
' Procedure: AuditSheet
' Scope: Private Function
'
' What it does:
'   Reads, creates, updates, or cleans audit/log information for AuditSheet.
'
' Why it exists:
'   The audit sheet is the troubleshooting trail that connects what the
'   operator scanned locally with what SharePoint/master later reported.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function AuditSheet() As Worksheet
    EnsureScanAuditSheet
    Set AuditSheet = ThisWorkbook.Worksheets(SCAN_AUDIT_SHEET_NAME)
End Function

'------------------------------------------------------------------------------
' Procedure: EnsureScanAuditSheet
' Scope: Public Sub
'
' What it does:
'   Creates or repairs the hidden scan audit sheet and its column headers.
'
' Why it exists:
'   Every local scan should have an audit trail even before the queue request
'   reaches SharePoint.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub EnsureScanAuditSheet()
    Dim ws As Worksheet

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(SCAN_AUDIT_SHEET_NAME)
    On Error GoTo 0

    If ws Is Nothing Then
        Set ws = ThisWorkbook.Worksheets.Add(After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
        ws.Name = SCAN_AUDIT_SHEET_NAME
    End If

    If Len(Trim$(CStr(ws.Cells(1, 1).Value))) = 0 Then
        ws.Cells(1, 1).Value = "LoggedAt"
        ws.Cells(1, 2).Value = "RequestId"
        ws.Cells(1, 3).Value = "DeliveryListKey"
        ws.Cells(1, 4).Value = "DeliveryListDisplay"
        ws.Cells(1, 5).Value = "RequestType"
        ws.Cells(1, 6).Value = "BarcodeText"
        ws.Cells(1, 7).Value = "Mode"
        ws.Cells(1, 8).Value = "OrderNum"
        ws.Cells(1, 9).Value = "ItemNum"
        ws.Cells(1, 10).Value = "Qty"
        ws.Cells(1, 11).Value = "SourceStage"
        ws.Cells(1, 12).Value = "StationName"
        ws.Cells(1, 13).Value = "RequestComment"
        ws.Cells(1, 14).Value = "BufferedAt"
        ws.Cells(1, 15).Value = "BufferStatus"
        ws.Cells(1, 16).Value = "SentAt"
        ws.Cells(1, 17).Value = "QueueStatus"
        ws.Cells(1, 18).Value = "ResultCode"
        ws.Cells(1, 19).Value = "ResultMessage"
        ws.Cells(1, 20).Value = "ProcessedAt"
        ws.Cells(1, 21).Value = "LastSeenAt"

        ws.Rows(1).Font.Bold = True
    End If

    ws.Visible = xlSheetVeryHidden
End Sub

'------------------------------------------------------------------------------
' Procedure: NextAuditRow
' Scope: Private Function
'
' What it does:
'   Reads, creates, updates, or cleans audit/log information for NextAuditRow.
'
' Why it exists:
'   The audit sheet is the troubleshooting trail that connects what the
'   operator scanned locally with what SharePoint/master later reported.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function NextAuditRow(ByVal ws As Worksheet) As Long
    Dim lastRow As Long

    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row
    If lastRow < 2 Then
        NextAuditRow = 2
    Else
        NextAuditRow = lastRow + 1
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: FindAuditRowByRequestId
' Scope: Private Function
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   FindAuditRowByRequestId.
'
' Why it exists:
'   The audit sheet is the troubleshooting trail that connects what the
'   operator scanned locally with what SharePoint/master later reported.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function FindAuditRowByRequestId(ByVal ws As Worksheet, ByVal requestId As String) As Long
    Dim lastRow As Long
    Dim r As Long

    If ws Is Nothing Then Exit Function
    If Len(Trim$(requestId)) = 0 Then Exit Function

    lastRow = ws.Cells(ws.Rows.Count, 2).End(xlUp).Row

    For r = 2 To lastRow
        If StrComp(Trim$(CStr(ws.Cells(r, 2).Value)), Trim$(requestId), vbTextCompare) = 0 Then
            FindAuditRowByRequestId = r
            Exit Function
        End If
    Next r
End Function

'------------------------------------------------------------------------------
' Procedure: LogBufferedScan
' Scope: Public Sub
'
' What it does:
'   Creates or updates an audit row when a barcode/manual request is buffered
'   locally.
'
' Why it exists:
'   This proves the intake workbook captured the scan even if the later Power
'   Automate send fails.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub LogBufferedScan(ByVal requestId As String, _
                           ByVal deliveryListKey As String, _
                           ByVal requestType As String, _
                           ByVal barcodeText As String, _
                           ByVal modeText As String, _
                           ByVal ord As Long, _
                           ByVal itm As Long, _
                           ByVal qty As Long, _
                           ByVal sourceStage As String, _
                           ByVal stationName As String, _
                           ByVal requestComment As String)

    Dim ws As Worksheet
    Dim rowNum As Long

    Set ws = AuditSheet()
    rowNum = FindAuditRowByRequestId(ws, requestId)

    If rowNum = 0 Then rowNum = NextAuditRow(ws)

    ws.Cells(rowNum, 1).Value = Now
    ws.Cells(rowNum, 2).Value = requestId
    ws.Cells(rowNum, 3).Value = deliveryListKey
    ws.Cells(rowNum, 4).Value = GetSelectedDeliveryDisplay()
    ws.Cells(rowNum, 5).Value = requestType
    ws.Cells(rowNum, 6).Value = barcodeText
    ws.Cells(rowNum, 7).Value = modeText
    ws.Cells(rowNum, 8).Value = ord
    ws.Cells(rowNum, 9).Value = itm
    ws.Cells(rowNum, 10).Value = qty
    ws.Cells(rowNum, 11).Value = sourceStage
    ws.Cells(rowNum, 12).Value = stationName
    ws.Cells(rowNum, 13).Value = requestComment
    ws.Cells(rowNum, 14).Value = Now
    ws.Cells(rowNum, 15).Value = "Buffered"
    ws.Cells(rowNum, 21).Value = Now
End Sub

'------------------------------------------------------------------------------
' Procedure: UpdateAuditAfterBufferSend
' Scope: Public Sub
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   UpdateAuditAfterBufferSend.
'
' Why it exists:
'   The audit sheet is the troubleshooting trail that connects what the
'   operator scanned locally with what SharePoint/master later reported.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub UpdateAuditAfterBufferSend(ByVal requestId As String, ByVal bufferStatus As String, Optional ByVal sentAt As Variant)
    Dim ws As Worksheet
    Dim rowNum As Long

    Set ws = AuditSheet()
    rowNum = FindAuditRowByRequestId(ws, requestId)
    If rowNum = 0 Then Exit Sub

    ws.Cells(rowNum, 15).Value = bufferStatus

    If Not IsMissing(sentAt) Then
        If IsDate(sentAt) Then ws.Cells(rowNum, 16).Value = CDate(sentAt)
    End If

    ws.Cells(rowNum, 21).Value = Now
End Sub

'------------------------------------------------------------------------------
' Procedure: UpdateAuditFromRequestItem
' Scope: Public Sub
'
' What it does:
'   Updates the audit row with SharePoint queue status, result code/message,
'   and processed time.
'
' Why it exists:
'   The audit log should show the full lifecycle from local buffer to master
'   result.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub UpdateAuditFromRequestItem(ByVal item As Object)
    Dim ws As Worksheet
    Dim rowNum As Long
    Dim requestId As String
    Dim processedAtVal As Variant

    Set ws = AuditSheet()

    requestId = Trim$(PA_DictText(item, "requestId"))
    If Len(requestId) = 0 Then requestId = Trim$(PA_DictText(item, "title"))
    If Len(requestId) = 0 Then Exit Sub

    rowNum = FindAuditRowByRequestId(ws, requestId)
    If rowNum = 0 Then Exit Sub

    ws.Cells(rowNum, 17).Value = PA_DictText(item, "status")
    ws.Cells(rowNum, 18).Value = PA_DictText(item, "resultCode")
    ws.Cells(rowNum, 19).Value = PA_DictText(item, "resultMessage")

    processedAtVal = PA_ParseIsoDate(PA_DictText(item, "processedAt"))
    If IsDate(processedAtVal) Then
        ws.Cells(rowNum, 20).Value = processedAtVal
    End If

    ws.Cells(rowNum, 21).Value = Now
End Sub

'------------------------------------------------------------------------------
' Procedure: CleanupOldScanAuditRows
' Scope: Public Sub
'
' What it does:
'   Deletes old audit rows beyond the retention window.
'
' Why it exists:
'   The hidden audit sheet is for recent troubleshooting; uncontrolled growth
'   would bloat the intake workbook.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub CleanupOldScanAuditRows()
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim r As Long
    Dim cutoff As Date
    Dim loggedAtVal As Variant
    Dim bufferedAtVal As Variant
    Dim keepDate As Date

    Set ws = AuditSheet()
    cutoff = Now - SCAN_AUDIT_RETENTION_DAYS
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row

    For r = lastRow To 2 Step -1
        keepDate = 0

        loggedAtVal = ws.Cells(r, 1).Value
        bufferedAtVal = ws.Cells(r, 14).Value

        If IsDate(bufferedAtVal) Then
            keepDate = CDate(bufferedAtVal)
        ElseIf IsDate(loggedAtVal) Then
            keepDate = CDate(loggedAtVal)
        End If

        If keepDate > 0 Then
            If keepDate < cutoff Then
                ws.Rows(r).Delete
            End If
        End If
    Next r

    ws.Visible = xlSheetVeryHidden
End Sub

'------------------------------------------------------------------------------
' Procedure: ShowScanAuditSheet
' Scope: Public Sub
'
' What it does:
'   Reads, creates, updates, or cleans audit/log information for
'   ShowScanAuditSheet.
'
' Why it exists:
'   The audit sheet is the troubleshooting trail that connects what the
'   operator scanned locally with what SharePoint/master later reported.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub ShowScanAuditSheet()
    Dim ws As Worksheet
    Set ws = AuditSheet()

    ws.Visible = xlSheetVisible
    ws.Activate
End Sub



