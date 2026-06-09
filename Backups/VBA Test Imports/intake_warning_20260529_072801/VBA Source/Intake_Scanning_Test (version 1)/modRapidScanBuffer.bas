Attribute VB_Name = "modRapidScanBuffer"
Option Explicit

'==============================================================================
' Module: modRapidScanBuffer
' Workbook: Intake_Scanning_Test.xlsm / Intake scanner workbook
'
' What this module does:
'   Local scan-buffer system. It writes rapid scans to a hidden buffer sheet
'   first, then sends them to the shared ScanQueue after the scanner is idle.
'
' Why this module exists:
'   Buffering keeps scanner input responsive and prevents operators from
'   waiting on Power Automate/SharePoint after every barcode.
'
' Commenting standard used in this rewrite:
'   Comments explain both what each procedure/section does and why it
'   matters to the scanning, SharePoint, Power Automate, buffering, and
'   operator-safety workflow. The code behavior and public procedure names
'   are intentionally kept stable so existing buttons/forms/timers keep working.
'==============================================================================


'modRapidScanBuffer'

Public Const BUFFER_SHEET_NAME As String = "LocalQueueBuffer"
Public Const BUFFER_STATUS_PENDING As String = "Pending"
Public Const BUFFER_STATUS_SENT As String = "Sent"
Public Const BUFFER_STATUS_RETRY As String = "Retry"
Public Const BUFFER_STATUS_FAILED As String = "Failed"
Private Const BUFFER_MAX_RETRIES As Long = 3

Private mNextFlushRun As Date
Private mFlushScheduled As Boolean
Private mFlushRunning As Boolean
Private Const BUFFER_FLUSH_IDLE_SECONDS As Long = 4
Private mBufferUiBusy As Boolean

'------------------------------------------------------------------------------
' Procedure: EnsureLocalQueueBufferSheet
' Scope: Public Sub
'
' What it does:
'   Creates or repairs the hidden LocalQueueBuffer sheet and its header row.
'
' Why it exists:
'   Rapid scans are stored locally first, so the buffer sheet must always
'   exist before the scan box accepts input.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub EnsureLocalQueueBufferSheet()
    Dim ws As Worksheet

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(BUFFER_SHEET_NAME)
    On Error GoTo 0

    If ws Is Nothing Then
        Set ws = ThisWorkbook.Worksheets.Add(After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
        ws.Name = BUFFER_SHEET_NAME
    End If

    ws.Cells(1, 1).Value = "RequestId"
    ws.Cells(1, 2).Value = "DeliveryListKey"
    ws.Cells(1, 3).Value = "RequestType"
    ws.Cells(1, 4).Value = "BarcodeText"
    ws.Cells(1, 5).Value = "Mode"
    ws.Cells(1, 6).Value = "OrderNum"
    ws.Cells(1, 7).Value = "ItemNum"
    ws.Cells(1, 8).Value = "Qty"
    ws.Cells(1, 9).Value = "SourceStage"
    ws.Cells(1, 10).Value = "StationName"
    ws.Cells(1, 11).Value = "RequestTime"
    ws.Cells(1, 12).Value = "BufferStatus"
    ws.Cells(1, 13).Value = "RequestComment"
    ws.Cells(1, 14).Value = "SentTime"
    ws.Cells(1, 15).Value = "RetryCount"
    ws.Cells(1, 16).Value = "LastError"
    ws.Cells(1, 17).Value = "LastAttemptAt"

    ws.Visible = xlSheetVeryHidden
End Sub

'------------------------------------------------------------------------------
' Procedure: BufferSheet
' Scope: Private Function
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   BufferSheet.
'
' Why it exists:
'   This keeps scan capture fast while still guaranteeing each scan is
'   eventually sent to the shared queue or marked failed for review.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function BufferSheet() As Worksheet
    EnsureLocalQueueBufferSheet
    Set BufferSheet = ThisWorkbook.Worksheets(BUFFER_SHEET_NAME)
End Function

'------------------------------------------------------------------------------
' Procedure: NextBufferRow
' Scope: Private Function
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   NextBufferRow.
'
' Why it exists:
'   This keeps scan capture fast while still guaranteeing each scan is
'   eventually sent to the shared queue or marked failed for review.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function NextBufferRow(ByVal ws As Worksheet) As Long
    Dim lastRow As Long

    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row
    If lastRow < 2 Then
        NextBufferRow = 2
    Else
        NextBufferRow = lastRow + 1
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: BufferBarcodeRequest
' Scope: Public Sub
'
' What it does:
'   Writes a barcode scan request to the hidden local buffer and logs it in
'   the audit sheet.
'
' Why it exists:
'   The scan is captured immediately even if Power Automate or the network is
'   momentarily slow.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub BufferBarcodeRequest(ByVal requestId As String, ByVal barcodeText As String, ByVal ord As Long, ByVal itm As Long)
    Dim ws As Worksheet
    Dim rowNum As Long

    Set ws = BufferSheet()
    rowNum = NextBufferRow(ws)

    ws.Cells(rowNum, 1).Value = requestId
    ws.Cells(rowNum, 2).Value = GetSelectedDeliveryKey()
    ws.Cells(rowNum, 3).Value = "BARCODE"
    ws.Cells(rowNum, 4).Value = barcodeText
    ws.Cells(rowNum, 5).Value = ModeFromStageProfile(GetSelectedStageProfile())
    ws.Cells(rowNum, 6).Value = ord
    ws.Cells(rowNum, 7).Value = itm
    ws.Cells(rowNum, 8).Value = 1
    ws.Cells(rowNum, 9).Value = GetSelectedStageProfile()
    ws.Cells(rowNum, 10).Value = GetStationName()
    ws.Cells(rowNum, 11).Value = Now
    ws.Cells(rowNum, 12).Value = BUFFER_STATUS_PENDING
    ws.Cells(rowNum, 13).Value = vbNullString
    LogBufferedScan requestId, _
                GetSelectedDeliveryKey(), _
                "BARCODE", _
                barcodeText, _
                ModeFromStageProfile(GetSelectedStageProfile()), _
                ord, _
                itm, _
                1, _
                GetSelectedStageProfile(), _
                GetStationName(), _
                vbNullString
    ws.Cells(rowNum, 14).Value = vbNullString
    ws.Cells(rowNum, 15).Value = 0
    ws.Cells(rowNum, 16).Value = vbNullString
    ws.Cells(rowNum, 17).Value = vbNullString

    SetBufferBusyUi False
    RefreshBufferedCountUi
    SchedulePendingQueueFlush
End Sub

'------------------------------------------------------------------------------
' Procedure: BufferManualRequest
' Scope: Public Sub
'
' What it does:
'   Writes a manual scan request to the hidden local buffer and logs it in the
'   audit sheet.
'
' Why it exists:
'   Manual scans need the same delayed-send, retry, and audit behavior as
'   barcode scans.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub BufferManualRequest(ByVal requestId As String, ByVal ord As Long, ByVal itm As Long, ByVal qty As Long, ByVal commentText As String)
    Dim ws As Worksheet
    Dim rowNum As Long

    Set ws = BufferSheet()
    rowNum = NextBufferRow(ws)

    ws.Cells(rowNum, 1).Value = requestId
    ws.Cells(rowNum, 2).Value = GetSelectedDeliveryKey()
    ws.Cells(rowNum, 3).Value = "MANUAL"
    ws.Cells(rowNum, 4).Value = vbNullString
    ws.Cells(rowNum, 5).Value = ModeFromStageProfile(GetSelectedStageProfile())
    ws.Cells(rowNum, 6).Value = ord
    ws.Cells(rowNum, 7).Value = itm
    ws.Cells(rowNum, 8).Value = qty
    ws.Cells(rowNum, 9).Value = GetSelectedStageProfile()
    ws.Cells(rowNum, 10).Value = GetStationName()
    ws.Cells(rowNum, 11).Value = Now
    ws.Cells(rowNum, 12).Value = BUFFER_STATUS_PENDING
    ws.Cells(rowNum, 13).Value = commentText
    LogBufferedScan requestId, _
                GetSelectedDeliveryKey(), _
                "MANUAL", _
                vbNullString, _
                ModeFromStageProfile(GetSelectedStageProfile()), _
                ord, _
                itm, _
                qty, _
                GetSelectedStageProfile(), _
                GetStationName(), _
                commentText
    ws.Cells(rowNum, 14).Value = vbNullString
    ws.Cells(rowNum, 15).Value = 0
    ws.Cells(rowNum, 16).Value = vbNullString
    ws.Cells(rowNum, 17).Value = vbNullString

    SetBufferBusyUi False
    RefreshBufferedCountUi
    SchedulePendingQueueFlush
End Sub

'------------------------------------------------------------------------------
' Procedure: HasPendingQueueRows
' Scope: Public Function
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   HasPendingQueueRows.
'
' Why it exists:
'   This keeps scan capture fast while still guaranteeing each scan is
'   eventually sent to the shared queue or marked failed for review.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function HasPendingQueueRows() As Boolean
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim r As Long
    Dim statusText As String

    Set ws = BufferSheet()
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row

    For r = 2 To lastRow
        statusText = Trim$(CStr(ws.Cells(r, 12).Value))
        If StrComp(statusText, BUFFER_STATUS_PENDING, vbTextCompare) = 0 Or _
           StrComp(statusText, BUFFER_STATUS_RETRY, vbTextCompare) = 0 Then
            HasPendingQueueRows = True
            Exit Function
        End If
    Next r
End Function

'------------------------------------------------------------------------------
' Procedure: IsBufferFlushBusy
' Scope: Public Function
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   IsBufferFlushBusy.
'
' Why it exists:
'   This keeps scan capture fast while still guaranteeing each scan is
'   eventually sent to the shared queue or marked failed for review.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function IsBufferFlushBusy() As Boolean
    IsBufferFlushBusy = mBufferUiBusy Or mFlushRunning
End Function

'------------------------------------------------------------------------------
' Procedure: GetPendingQueueRowCount
' Scope: Public Function
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   GetPendingQueueRowCount.
'
' Why it exists:
'   This keeps scan capture fast while still guaranteeing each scan is
'   eventually sent to the shared queue or marked failed for review.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function GetPendingQueueRowCount() As Long
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim r As Long
    Dim statusText As String

    Set ws = BufferSheet()
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row

    For r = 2 To lastRow
        statusText = Trim$(CStr(ws.Cells(r, 12).Value))
        If StrComp(statusText, BUFFER_STATUS_PENDING, vbTextCompare) = 0 Or _
           StrComp(statusText, BUFFER_STATUS_RETRY, vbTextCompare) = 0 Then
            GetPendingQueueRowCount = GetPendingQueueRowCount + 1
        End If
    Next r
End Function

'------------------------------------------------------------------------------
' Procedure: GetFailedQueueRowCount
' Scope: Private Function
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   GetFailedQueueRowCount.
'
' Why it exists:
'   This keeps scan capture fast while still guaranteeing each scan is
'   eventually sent to the shared queue or marked failed for review.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function GetFailedQueueRowCount() As Long
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim r As Long
    Dim statusText As String

    Set ws = BufferSheet()
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row

    For r = 2 To lastRow
        statusText = Trim$(CStr(ws.Cells(r, 12).Value))
        If StrComp(statusText, BUFFER_STATUS_FAILED, vbTextCompare) = 0 Then
            GetFailedQueueRowCount = GetFailedQueueRowCount + 1
        End If
    Next r
End Function

'------------------------------------------------------------------------------
' Procedure: GetLatestBufferError
' Scope: Private Function
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   GetLatestBufferError.
'
' Why it exists:
'   This keeps scan capture fast while still guaranteeing each scan is
'   eventually sent to the shared queue or marked failed for review.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function GetLatestBufferError() As String
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim r As Long
    Dim errText As String

    Set ws = BufferSheet()
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row

    For r = lastRow To 2 Step -1
        errText = Trim$(CStr(ws.Cells(r, 16).Value))
        If Len(errText) > 0 Then
            GetLatestBufferError = errText
            Exit Function
        End If
    Next r
End Function

'------------------------------------------------------------------------------
' Procedure: MarkBufferRowSent
' Scope: Private Sub
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   MarkBufferRowSent.
'
' Why it exists:
'   This keeps scan capture fast while still guaranteeing each scan is
'   eventually sent to the shared queue or marked failed for review.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub MarkBufferRowSent(ByVal ws As Worksheet, ByVal rowNum As Long)
    Dim requestId As String

    requestId = Trim$(CStr(ws.Cells(rowNum, 1).Value))

    ws.Cells(rowNum, 12).Value = BUFFER_STATUS_SENT
    ws.Cells(rowNum, 14).Value = Now
    ws.Cells(rowNum, 16).Value = vbNullString
    ws.Cells(rowNum, 17).Value = Now

    UpdateAuditAfterBufferSend requestId, BUFFER_STATUS_SENT, Now
End Sub

'------------------------------------------------------------------------------
' Procedure: MarkBufferRowFailure
' Scope: Private Sub
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   MarkBufferRowFailure.
'
' Why it exists:
'   This keeps scan capture fast while still guaranteeing each scan is
'   eventually sent to the shared queue or marked failed for review.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub MarkBufferRowFailure(ByVal ws As Worksheet, ByVal rowNum As Long, ByVal errText As String)
    Dim retryCount As Long
    Dim requestId As String
    Dim finalStatus As String

    requestId = Trim$(CStr(ws.Cells(rowNum, 1).Value))

    retryCount = CLng(Val(ws.Cells(rowNum, 15).Value)) + 1
    ws.Cells(rowNum, 15).Value = retryCount
    ws.Cells(rowNum, 16).Value = errText
    ws.Cells(rowNum, 17).Value = Now

    If retryCount >= BUFFER_MAX_RETRIES Then
        ws.Cells(rowNum, 12).Value = BUFFER_STATUS_FAILED
        finalStatus = BUFFER_STATUS_FAILED
    Else
        ws.Cells(rowNum, 12).Value = BUFFER_STATUS_RETRY
        finalStatus = BUFFER_STATUS_RETRY
    End If

    UpdateAuditAfterBufferSend requestId, finalStatus
End Sub

'------------------------------------------------------------------------------
' Procedure: RefreshBufferedCountUi
' Scope: Public Sub
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   RefreshBufferedCountUi.
'
' Why it exists:
'   This keeps scan capture fast while still guaranteeing each scan is
'   eventually sent to the shared queue or marked failed for review.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub RefreshBufferedCountUi()
    Dim pendingCount As Long
    Dim failedCount As Long
    Dim lastError As String

    pendingCount = GetPendingQueueRowCount()
    failedCount = GetFailedQueueRowCount()
    lastError = GetLatestBufferError()

    On Error Resume Next

    If IsBufferFlushBusy() Then
        StationSheet.Range(CELL_LAST_QUEUE_STATUS).Value = "Sending buffered scans..."
    ElseIf pendingCount > 0 Then
        StationSheet.Range(CELL_LAST_QUEUE_STATUS).Value = "Buffered locally"
        If Len(lastError) > 0 Then
            StationSheet.Range(CELL_LAST_RESULT_MESSAGE).Value = lastError
        Else
            StationSheet.Range(CELL_LAST_RESULT_MESSAGE).Value = CStr(pendingCount) & " scan(s) waiting to send."
        End If
    ElseIf failedCount > 0 Then
        StationSheet.Range(CELL_LAST_QUEUE_STATUS).Value = "Buffer send failed"
        If Len(lastError) > 0 Then
            StationSheet.Range(CELL_LAST_RESULT_MESSAGE).Value = lastError
        Else
            StationSheet.Range(CELL_LAST_RESULT_MESSAGE).Value = CStr(failedCount) & " buffered scan(s) failed."
        End If
    Else
        If Trim$(CStr(StationSheet.Range(CELL_LAST_QUEUE_STATUS).Value)) = "" Or _
           Trim$(CStr(StationSheet.Range(CELL_LAST_QUEUE_STATUS).Value)) = "Sending buffered scans..." Or _
           Trim$(CStr(StationSheet.Range(CELL_LAST_QUEUE_STATUS).Value)) = "Buffered locally" Or _
           Trim$(CStr(StationSheet.Range(CELL_LAST_QUEUE_STATUS).Value)) = "Buffer send failed" Then
            StationSheet.Range(CELL_LAST_QUEUE_STATUS).Value = "Ready to scan"
        End If
    End If

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: SetBufferBusyUi
' Scope: Private Sub
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   SetBufferBusyUi.
'
' Why it exists:
'   This keeps scan capture fast while still guaranteeing each scan is
'   eventually sent to the shared queue or marked failed for review.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub SetBufferBusyUi(ByVal isBusy As Boolean, Optional ByVal detailText As String = vbNullString)
    mBufferUiBusy = isBusy

    On Error Resume Next

    If isBusy Then
        If Len(detailText) = 0 Then
            detailText = "Scans are temporarily paused while buffered scans are being sent."
        End If

        StationSheet.Range(CELL_LAST_QUEUE_STATUS).Value = "Sending buffered scans."
        StationSheet.Range(CELL_LAST_RESULT_MESSAGE).Value = detailText
        Application.StatusBar = detailText

        ShowProcessingNotice detailText
    Else
        HideProcessingNotice

        If GetPendingQueueRowCount() > 0 Then
            StationSheet.Range(CELL_LAST_QUEUE_STATUS).Value = "Buffered locally"
            StationSheet.Range(CELL_LAST_RESULT_MESSAGE).Value = CStr(GetPendingQueueRowCount()) & " scan(s) waiting to send."
        ElseIf Len(Trim$(CStr(StationSheet.Range(CELL_LAST_QUEUE_STATUS).Value))) = 0 Or _
               Trim$(CStr(StationSheet.Range(CELL_LAST_QUEUE_STATUS).Value)) = "Sending buffered scans." Then
            StationSheet.Range(CELL_LAST_QUEUE_STATUS).Value = "Ready to scan"
            StationSheet.Range(CELL_LAST_RESULT_MESSAGE).Value = "No buffered scans waiting."
        End If

        Application.StatusBar = False
    End If

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: SchedulePendingQueueFlush
' Scope: Public Sub
'
' What it does:
'   Schedules a delayed buffer flush, cancelling/rescheduling any existing
'   pending flush so rapid scans can accumulate.
'
' Why it exists:
'   The idle delay prevents the scanner from pausing after each barcode while
'   still sending rows soon after the operator stops scanning.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub SchedulePendingQueueFlush()
    On Error Resume Next

    If mFlushRunning Then Exit Sub

    'If a flush was already scheduled, cancel it and push it back.
    'This lets rapid scans accumulate into one batch after the operator pauses.
    If mFlushScheduled Then
        Application.OnTime EarliestTime:=mNextFlushRun, _
                           Procedure:="'" & ThisWorkbook.Name & "'!PendingQueueFlushBridge", _
                           Schedule:=False
    End If

    mNextFlushRun = Now + TimeSerial(0, 0, BUFFER_FLUSH_IDLE_SECONDS)
    mFlushScheduled = True

    Application.OnTime EarliestTime:=mNextFlushRun, _
                       Procedure:="'" & ThisWorkbook.Name & "'!PendingQueueFlushBridge", _
                       Schedule:=True

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: CancelPendingQueueFlush
' Scope: Public Sub
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   CancelPendingQueueFlush.
'
' Why it exists:
'   This keeps scan capture fast while still guaranteeing each scan is
'   eventually sent to the shared queue or marked failed for review.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub CancelPendingQueueFlush()
    On Error Resume Next

    If mFlushScheduled Then
        Application.OnTime EarliestTime:=mNextFlushRun, _
                           Procedure:="'" & ThisWorkbook.Name & "'!PendingQueueFlushBridge", _
                           Schedule:=False
    End If

    mFlushScheduled = False
    mFlushRunning = False
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: PendingQueueFlushBridge
' Scope: Public Sub
'
' What it does:
'   Public no-argument OnTime callback that runs one buffer flush and
'   reschedules if pending/retry rows remain.
'
' Why it exists:
'   Application.OnTime needs a public bridge, and the bridge prevents
'   overlapping flushes.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub PendingQueueFlushBridge()
    On Error GoTo ErrHandler

    mFlushScheduled = False
    If mFlushRunning Then Exit Sub

    mFlushRunning = True
    FlushPendingQueueRows 25

SafeExit:
    mFlushRunning = False

    If HasPendingQueueRows() Then
        SchedulePendingQueueFlush
    Else
        SetBufferBusyUi False
        RefreshBufferedCountUi
    End If
    Exit Sub

ErrHandler:
    On Error Resume Next
    mFlushRunning = False
    StationSheet.Range(CELL_LAST_QUEUE_STATUS).Value = "Buffer send failed"
    StationSheet.Range(CELL_LAST_RESULT_MESSAGE).Value = "Buffer flush bridge error " & Err.Number & ": " & Err.Description
    RefreshBufferedCountUi
    On Error GoTo 0
    Resume SafeExit
End Sub

'------------------------------------------------------------------------------
' Procedure: FlushPendingQueueRows
' Scope: Public Sub
'
' What it does:
'   Sends pending/retry buffer rows to Power Automate, updates
'   retry/sent/failed state, updates audit rows, and refreshes the panel/UI
'   notice.
'
' Why it exists:
'   This is the handoff from fast local capture to the shared SharePoint
'   ScanQueue, with retries so scans are not lost on transient failures.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub FlushPendingQueueRows(Optional ByVal maxRows As Long = 25)
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim r As Long
    Dim flushedCount As Long
    Dim pendingTotal As Long
    Dim remainingPending As Long
    Dim statusText As String
    Dim ok As Boolean
    Dim flowError As String

    Dim requestId As String
    Dim deliveryListKey As String
    Dim requestType As String
    Dim barcodeText As String
    Dim modeText As String
    Dim ord As Long
    Dim itm As Long
    Dim qty As Long
    Dim sourceStage As String
    Dim stationName As String
    Dim requestComment As String

    On Error GoTo ErrHandler

    Set ws = BufferSheet()
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row

    If lastRow < 2 Then
        SetBufferBusyUi False
        Exit Sub
    End If

    pendingTotal = GetPendingQueueRowCount()
    If pendingTotal = 0 Then
        SetBufferBusyUi False
        Exit Sub
    End If

    'This notice should only appear once the rapid-scan idle window has ended
    'and we are actually sending buffered rows to SharePoint.
    SetBufferBusyUi True, "Sending buffered scans to queue... 0/" & pendingTotal

    For r = 2 To lastRow
        statusText = Trim$(CStr(ws.Cells(r, 12).Value))

        If StrComp(statusText, BUFFER_STATUS_PENDING, vbTextCompare) = 0 Or _
           StrComp(statusText, BUFFER_STATUS_RETRY, vbTextCompare) = 0 Then

            requestId = Trim$(CStr(ws.Cells(r, 1).Value))
            deliveryListKey = Trim$(CStr(ws.Cells(r, 2).Value))
            requestType = UCase$(Trim$(CStr(ws.Cells(r, 3).Value)))
            barcodeText = UCase$(Trim$(CStr(ws.Cells(r, 4).Value)))
            modeText = UCase$(Trim$(CStr(ws.Cells(r, 5).Value)))
            ord = CLng(Val(ws.Cells(r, 6).Value))
            itm = CLng(Val(ws.Cells(r, 7).Value))
            qty = CLng(Val(ws.Cells(r, 8).Value))
            sourceStage = Trim$(CStr(ws.Cells(r, 9).Value))
            stationName = Trim$(CStr(ws.Cells(r, 10).Value))
            requestComment = Trim$(CStr(ws.Cells(r, 13).Value))

            ok = False
            flowError = vbNullString

            On Error Resume Next
            ok = PA_QueueAddRequest( _
                    requestId, _
                    deliveryListKey, _
                    requestType, _
                    modeText, _
                    barcodeText, _
                    ord, _
                    itm, _
                    qty, _
                    sourceStage, _
                    stationName, _
                    requestComment)

            If Err.Number <> 0 Then
                flowError = "Queue send error " & Err.Number & ": " & Err.Description
                ok = False
                Err.Clear
            End If
            On Error GoTo ErrHandler

            If ok Then
                MarkBufferRowSent ws, r
                flushedCount = flushedCount + 1

                SetBufferBusyUi True, _
                    "Sending buffered scans to queue... " & flushedCount & "/" & pendingTotal
            Else
                If Len(flowError) = 0 Then
                    flowError = "Flow 1 returned ok = false. Check QueueAddRequest flow and SharePoint choice values."
                End If

                MarkBufferRowFailure ws, r, flowError
                StationSheet.Range(CELL_LAST_QUEUE_STATUS).Value = "Buffer send failed"
                StationSheet.Range(CELL_LAST_RESULT_MESSAGE).Value = flowError
            End If

            If flushedCount >= maxRows Then Exit For
        End If
    Next r

    remainingPending = GetPendingQueueRowCount()

    If flushedCount > 0 Then
        If remainingPending > 0 Then
            'Do NOT start queue-status polling yet.
            'There are still local buffered rows waiting to be sent.
            StationSheet.Range(CELL_LAST_QUEUE_STATUS).Value = "Buffered locally"
            StationSheet.Range(CELL_LAST_RESULT_MESSAGE).Value = _
                CStr(flushedCount) & " sent. " & CStr(remainingPending) & " still waiting to send."
        Else
            'Now the buffer is fully flushed. It is safe to start watching SharePoint/master status.
            StationSheet.Range(CELL_LAST_QUEUE_STATUS).Value = "Queued"
            StationSheet.Range(CELL_LAST_RESULT_MESSAGE).Value = _
                CStr(flushedCount) & " buffered scan(s) sent to queue."
                
            ResetQueuePollFallbackForNewWork
            ScheduleStationPoll STATION_POLL_DELAY_AFTER_SCAN_SECONDS
        End If

    ElseIf remainingPending > 0 Then
        StationSheet.Range(CELL_LAST_QUEUE_STATUS).Value = "Buffer waiting for queue"
        StationSheet.Range(CELL_LAST_RESULT_MESSAGE).Value = GetLatestBufferError()

    ElseIf GetFailedQueueRowCount() > 0 Then
        StationSheet.Range(CELL_LAST_QUEUE_STATUS).Value = "Buffer send failed"
        StationSheet.Range(CELL_LAST_RESULT_MESSAGE).Value = GetLatestBufferError()
    End If

SafeExit:
    SetBufferBusyUi False
    RefreshBufferedCountUi
    Exit Sub

ErrHandler:
    On Error Resume Next
    StationSheet.Range(CELL_LAST_QUEUE_STATUS).Value = "Buffer send failed"
    StationSheet.Range(CELL_LAST_RESULT_MESSAGE).Value = _
        "Flush error " & Err.Number & ": " & Err.Description
    On Error GoTo 0
    Resume SafeExit
End Sub

'------------------------------------------------------------------------------
' Procedure: RapidScanBufferShouldDeferQueuePolling
' Scope: Public Function
'
' What it does:
'   Returns whether queue polling should wait because buffer sending is still
'   active or local rows have not been sent yet.
'
' Why it exists:
'   Polling too early can show confusing “missing” statuses for scans that are
'   still only local.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function RapidScanBufferShouldDeferQueuePolling() As Boolean
    RapidScanBufferShouldDeferQueuePolling = _
        mFlushScheduled Or _
        mFlushRunning Or _
        HasPendingQueueRows()
End Function



