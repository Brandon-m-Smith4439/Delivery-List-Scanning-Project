Attribute VB_Name = "modQueueCommon"
Option Explicit

'==============================================================================
' Module: modQueueCommon
' Workbook: Intake_Scanning_Test.xlsm / Intake scanner workbook
'
' What this module does:
'   Shared queue helpers for request IDs, legacy queue workbook access,
'   receive override flags, and compact result messages.
'
' Why this module exists:
'   Both buffering and queue-status display need consistent request IDs and
'   consistent override/result message handling.
'
' Commenting standard used in this rewrite:
'   Comments explain both what each procedure/section does and why it
'   matters to the scanning, SharePoint, Power Automate, buffering, and
'   operator-safety workflow. The code behavior and public procedure names
'   are intentionally kept stable so existing buttons/forms/timers keep working.
'==============================================================================


'modQueueCommon'

Public Const QUEUE_WORKBOOK_PATH As String = "I:\BAREFOOT-INSTALL\Glass Production\Brandon\Scan Queue\ScanQueue_Test.xlsx"
Public Const QUEUE_SHEET_NAME As String = "ScanQueue"
Public Const ACTIVE_LIST_SHEET_NAME As String = "ActiveDeliveryLists"
Public Const QUEUE_RECV_OVERRIDE_FLAG As String = "__OVERRIDE_RECV_OUTBOUND__"
Public Const QUEUE_RECV_OVERRIDE_AVAILABLE_FLAG As String = "OVERRIDE_AVAILABLE|"

Public Const QUEUE_SEND_OVERRIDE_FLAG As String = "__OVERRIDE_SEND_STAGING__"
Public Const QUEUE_SEND_OVERRIDE_AVAILABLE_FLAG As String = "SEND_OVERRIDE_AVAILABLE|"


Private mQuietDepth As Long
Private mPrevScreenUpdating As Boolean
Private mPrevDisplayAlerts As Boolean
Private mPrevEnableEvents As Boolean
Private mPrevAskToUpdateLinks As Boolean
Private mPrevStatusBar As Variant

'------------------------------------------------------------------------------
' Procedure: BeginQuietQueueUi
' Scope: Private Sub
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   BeginQuietQueueUi.
'
' Why it exists:
'   Scans move through local buffer, SharePoint ScanQueue, master processing,
'   and final intake confirmation; this state must stay traceable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub BeginQuietQueueUi(Optional ByVal statusText As String = vbNullString)
    mQuietDepth = mQuietDepth + 1
    If mQuietDepth > 1 Then Exit Sub

    mPrevScreenUpdating = Application.ScreenUpdating
    mPrevDisplayAlerts = Application.DisplayAlerts
    mPrevEnableEvents = Application.EnableEvents
    mPrevAskToUpdateLinks = Application.AskToUpdateLinks
    mPrevStatusBar = Application.StatusBar

    Application.ScreenUpdating = False
    Application.DisplayAlerts = False
    Application.EnableEvents = False
    Application.AskToUpdateLinks = False

    If Len(statusText) > 0 Then
        Application.StatusBar = statusText
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: EndQuietQueueUi
' Scope: Private Sub
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   EndQuietQueueUi.
'
' Why it exists:
'   Scans move through local buffer, SharePoint ScanQueue, master processing,
'   and final intake confirmation; this state must stay traceable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub EndQuietQueueUi()
    If mQuietDepth <= 0 Then Exit Sub

    mQuietDepth = mQuietDepth - 1
    If mQuietDepth > 0 Then Exit Sub

    On Error Resume Next
    Application.ScreenUpdating = mPrevScreenUpdating
    Application.DisplayAlerts = mPrevDisplayAlerts
    Application.EnableEvents = mPrevEnableEvents
    Application.AskToUpdateLinks = mPrevAskToUpdateLinks
    Application.StatusBar = mPrevStatusBar
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: OpenQueueWorkbook
' Scope: Public Function
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   OpenQueueWorkbook.
'
' Why it exists:
'   Scans move through local buffer, SharePoint ScanQueue, master processing,
'   and final intake confirmation; this state must stay traceable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function OpenQueueWorkbook(Optional ByVal readOnly As Boolean = True) As Workbook
    Dim fullPath As String
    Dim wb As Workbook

    fullPath = QUEUE_WORKBOOK_PATH

    If Len(Dir$(fullPath, vbNormal)) = 0 Then
        fullPath = ThisWorkbook.Path & Application.PathSeparator & "ScanQueue_Test.xlsx"
    End If

    If Len(Dir$(fullPath, vbNormal)) = 0 Then
        MsgBox "Could not find the scan queue workbook." & vbCrLf & vbCrLf & _
               "Tried:" & vbCrLf & _
               QUEUE_WORKBOOK_PATH & vbCrLf & _
               ThisWorkbook.Path & Application.PathSeparator & "ScanQueue_Test.xlsx", _
               vbExclamation, "Scan Queue"
        Exit Function
    End If

    BeginQuietQueueUi "Opening scan queue..."
    On Error GoTo FailOpen

    Set wb = Workbooks.Open( _
        Filename:=fullPath, _
        UpdateLinks:=0, _
        readOnly:=readOnly, _
        AddToMru:=False, _
        IgnoreReadOnlyRecommended:=True, _
        Notify:=False)

    If wb.Windows.Count > 0 Then
        wb.Windows(1).Visible = False
    End If

    Set OpenQueueWorkbook = wb

CleanExit:
    EndQuietQueueUi
    Exit Function

FailOpen:
    EndQuietQueueUi
    MsgBox "Could not open the scan queue workbook:" & vbCrLf & _
           fullPath & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbExclamation, "Scan Queue"
End Function

'------------------------------------------------------------------------------
' Procedure: SaveAndCloseQueueWorkbook
' Scope: Public Sub
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   SaveAndCloseQueueWorkbook.
'
' Why it exists:
'   Scans move through local buffer, SharePoint ScanQueue, master processing,
'   and final intake confirmation; this state must stay traceable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub SaveAndCloseQueueWorkbook(ByRef qWb As Workbook, Optional ByVal saveFirst As Boolean = False)
    On Error GoTo CleanUp

    If qWb Is Nothing Then Exit Sub

    BeginQuietQueueUi IIf(saveFirst, "Saving scan queue...", "Closing scan queue...")

    If saveFirst Then
        qWb.Save
    End If

    qWb.Close SaveChanges:=False

CleanUp:
    Set qWb = Nothing
    EndQuietQueueUi
End Sub

'------------------------------------------------------------------------------
' Procedure: BuildRequestId
' Scope: Public Function
'
' What it does:
'   Creates a unique request ID using timestamp, timer ticks,
'   station/workbook/machine text, and a random suffix.
'
' Why it exists:
'   Every local scan needs a stable ID so the buffer, audit sheet, SharePoint
'   ScanQueue, and final status lookup can all match the same request.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function BuildRequestId(ByVal stationName As String) As String
    Dim workbookPart As String
    Dim machinePart As String
    Dim stationPart As String
    Dim tickPart As String
    Dim randomPart As String

    Randomize Timer

    stationPart = CleanRequestIdPart(stationName)
    workbookPart = CleanRequestIdPart(ThisWorkbook.Name)
    machinePart = CleanRequestIdPart(Environ$("COMPUTERNAME"))

    If Len(stationPart) = 0 Then stationPart = "Station"
    If Len(workbookPart) = 0 Then workbookPart = "Workbook"
    If Len(machinePart) = 0 Then machinePart = "Machine"

    workbookPart = Left$(workbookPart, 35)
    machinePart = Left$(machinePart, 25)

    tickPart = Format$(CLng(Timer * 1000), "00000000")
    randomPart = Format$(CLng(Rnd() * 999999), "000000")

    BuildRequestId = Format$(Now, "yyyymmdd_hhnnss") & "_" & _
                     tickPart & "_" & _
                     stationPart & "_" & _
                     workbookPart & "_" & _
                     machinePart & "_" & _
                     randomPart
End Function

'------------------------------------------------------------------------------
' Procedure: CleanRequestIdPart
' Scope: Private Function
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   CleanRequestIdPart.
'
' Why it exists:
'   Scans move through local buffer, SharePoint ScanQueue, master processing,
'   and final intake confirmation; this state must stay traceable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function CleanRequestIdPart(ByVal valueText As String) As String
    Dim s As String

    s = Trim$(CStr(valueText))

    s = Replace$(s, " ", "_")
    s = Replace$(s, ".", "_")
    s = Replace$(s, "-", "_")
    s = Replace$(s, "/", "_")
    s = Replace$(s, "\", "_")
    s = Replace$(s, ":", "_")
    s = Replace$(s, "*", "_")
    s = Replace$(s, "?", "_")
    s = Replace$(s, """", "_")
    s = Replace$(s, "<", "_")
    s = Replace$(s, ">", "_")
    s = Replace$(s, "|", "_")

    Do While InStr(1, s, "__", vbBinaryCompare) > 0
        s = Replace$(s, "__", "_")
    Loop

    CleanRequestIdPart = s
End Function

'------------------------------------------------------------------------------
' Procedure: NextQueueRow
' Scope: Public Function
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   NextQueueRow.
'
' Why it exists:
'   Scans move through local buffer, SharePoint ScanQueue, master processing,
'   and final intake confirmation; this state must stay traceable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function NextQueueRow(ByVal ws As Worksheet) As Long
    Dim lastRow As Long
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row
    If lastRow < 4 Then lastRow = 3
    NextQueueRow = lastRow + 1
End Function

'------------------------------------------------------------------------------
' Procedure: FindRequestRow
' Scope: Public Function
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   FindRequestRow.
'
' Why it exists:
'   Scans move through local buffer, SharePoint ScanQueue, master processing,
'   and final intake confirmation; this state must stay traceable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function FindRequestRow(ByVal ws As Worksheet, ByVal requestId As String) As Long
    Dim lastRow As Long
    Dim r As Long
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row
    For r = 4 To lastRow
        If StrComp(Trim$(CStr(ws.Cells(r, 1).Value)), Trim$(requestId), vbTextCompare) = 0 Then
            FindRequestRow = r
            Exit Function
        End If
    Next r
End Function


'------------------------------------------------------------------------------
' Procedure: IsReceiveOverrideRequestComment
' Scope: Public Function
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   IsReceiveOverrideRequestComment.
'
' Why it exists:
'   Scans move through local buffer, SharePoint ScanQueue, master processing,
'   and final intake confirmation; this state must stay traceable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function IsReceiveOverrideRequestComment(ByVal requestComment As String) As Boolean
    IsReceiveOverrideRequestComment = _
        (InStr(1, UCase$(CStr(requestComment)), UCase$(QUEUE_RECV_OVERRIDE_FLAG), vbTextCompare) > 0)
End Function

'------------------------------------------------------------------------------
' Procedure: StripReceiveOverrideFlag
' Scope: Public Function
'
' What it does:
'   Tracks or submits receive-override state for StripReceiveOverrideFlag.
'
' Why it exists:
'   Receiving overrides are exceptions to normal outbound-before-inbound
'   rules, so they need deliberate tracking and operator approval.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function StripReceiveOverrideFlag(ByVal requestComment As String) As String
    Dim s As String

    s = CStr(requestComment)
    s = Replace$(s, QUEUE_RECV_OVERRIDE_FLAG, vbNullString, 1, -1, vbTextCompare)
    s = Replace$(s, "||", "|")

    Do While Left$(Trim$(s), 1) = "|"
        s = Mid$(Trim$(s), 2)
    Loop

    StripReceiveOverrideFlag = Trim$(s)
End Function

'------------------------------------------------------------------------------
' Procedure: IsSendOverrideRequestComment
'
' Returns True when a queue request was intentionally approved to send outbound
' even though staging quantity is behind.
'------------------------------------------------------------------------------
Public Function IsSendOverrideRequestComment(ByVal requestComment As String) As Boolean
    IsSendOverrideRequestComment = _
        (InStr(1, UCase$(CStr(requestComment)), UCase$(QUEUE_SEND_OVERRIDE_FLAG), vbTextCompare) > 0)
End Function

'------------------------------------------------------------------------------
' Procedure: StripSendOverrideFlag
'
' Removes the outbound/staging override marker from request comments before
' operator-facing comments are written to the sheet.
'------------------------------------------------------------------------------
Public Function StripSendOverrideFlag(ByVal requestComment As String) As String
    Dim s As String

    s = CStr(requestComment)
    s = Replace$(s, QUEUE_SEND_OVERRIDE_FLAG, vbNullString, 1, -1, vbTextCompare)

    Do While InStr(1, s, "||", vbBinaryCompare) > 0
        s = Replace$(s, "||", "|")
    Loop

    Do While Left$(Trim$(s), 1) = "|"
        s = Mid$(Trim$(s), 2)
    Loop

    StripSendOverrideFlag = Trim$(s)
End Function

'------------------------------------------------------------------------------
' Procedure: StripQueueOverrideFlags
'
' Removes all hidden queue override markers from a request comment.
'------------------------------------------------------------------------------
Public Function StripQueueOverrideFlags(ByVal requestComment As String) As String
    Dim s As String

    s = CStr(requestComment)
    s = StripReceiveOverrideFlag(s)
    s = StripSendOverrideFlag(s)

    Do While InStr(1, s, "||", vbBinaryCompare) > 0
        s = Replace$(s, "||", "|")
    Loop

    Do While Left$(Trim$(s), 1) = "|"
        s = Mid$(Trim$(s), 2)
    Loop

    StripQueueOverrideFlags = Trim$(s)
End Function

'------------------------------------------------------------------------------
' Procedure: QueueResultAllowsReceiveOverride
' Scope: Public Function
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   QueueResultAllowsReceiveOverride.
'
' Why it exists:
'   Scans move through local buffer, SharePoint ScanQueue, master processing,
'   and final intake confirmation; this state must stay traceable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function QueueResultAllowsReceiveOverride(ByVal resultMessage As String) As Boolean
    Dim s As String

    s = UCase$(CStr(resultMessage))

    QueueResultAllowsReceiveOverride = _
        (InStr(1, s, UCase$(QUEUE_RECV_OVERRIDE_AVAILABLE_FLAG), vbTextCompare) > 0) Or _
        (InStr(1, s, "NO OUTBOUND", vbTextCompare) > 0) Or _
        (InStr(1, s, "EXCEED OUTBOUND", vbTextCompare) > 0) Or _
        (InStr(1, s, "EXCEED AIRPORT", vbTextCompare) > 0)
End Function

'------------------------------------------------------------------------------
' Procedure: QueueResultAllowsSendOverride
'
' Returns True when the master rejected an outbound scan only because staging
' quantity is behind and the intake station should offer an override button.
'------------------------------------------------------------------------------
Public Function QueueResultAllowsSendOverride(ByVal resultMessage As String) As Boolean
    Dim s As String

    s = UCase$(CStr(resultMessage))

    QueueResultAllowsSendOverride = _
        (InStr(1, s, UCase$(QUEUE_SEND_OVERRIDE_AVAILABLE_FLAG), vbTextCompare) > 0) Or _
        (InStr(1, s, "OUTBOUND WOULD EXCEED STAGED", vbTextCompare) > 0) Or _
        (InStr(1, s, "NOT BEEN FULLY STAGED", vbTextCompare) > 0) Or _
        (InStr(1, s, "STAGING MISMATCH", vbTextCompare) > 0)
End Function

'------------------------------------------------------------------------------
' Procedure: CompactQueueResultMessage
' Scope: Public Function
'
' What it does:
'   Removes hidden routing markers and long boilerplate from queue result
'   messages, then shortens the text for display.
'
' Why it exists:
'   The panel and imported row helper columns need clear operator-readable
'   messages, not full internal queue diagnostics.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function CompactQueueResultMessage(ByVal resultMessage As String) As String
    Dim s As String
    Dim p As Long

    s = Trim$(CStr(resultMessage))

    s = Replace$(s, QUEUE_RECV_OVERRIDE_AVAILABLE_FLAG, vbNullString, 1, -1, vbTextCompare)
    s = Replace$(s, QUEUE_SEND_OVERRIDE_AVAILABLE_FLAG, vbNullString, 1, -1, vbTextCompare)
    s = Replace$(s, "[MASTER FINAL]", vbNullString, 1, -1, vbTextCompare)
    s = Replace$(s, "This was sent back to the intake form for review.", vbNullString, 1, -1, vbTextCompare)
    s = Replace$(s, "This applies to all inbound locations, including Indian Trail, Greenville, and Customer Pickup.", vbNullString, 1, -1, vbTextCompare)
    s = Replace$(s, "This requires review on the intake form.", vbNullString, 1, -1, vbTextCompare)

    s = Replace$(s, vbCrLf & vbCrLf, vbCrLf)
    s = Replace$(s, vbCrLf & vbCrLf, vbCrLf)
    s = Trim$(s)

    If InStr(1, s, "Processor step failed", vbTextCompare) > 0 Then
        p = InStr(1, s, "Error ", vbTextCompare)
        If p > 0 Then s = Mid$(s, p)
    End If

    If Len(s) > 220 Then
        s = Left$(s, 217) & "..."
    End If

    CompactQueueResultMessage = s
End Function



