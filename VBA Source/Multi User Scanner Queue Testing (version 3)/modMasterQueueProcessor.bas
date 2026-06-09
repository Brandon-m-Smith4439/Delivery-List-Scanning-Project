Attribute VB_Name = "modMasterQueueProcessor"
Option Explicit

'==============================================================================
' Module: modMasterQueueProcessor
' Workbook: Multi User Scanner Queue Testing.xlsm / Master Delivery List
'
' What this module does:
'   Controls the master queue processor lifecycle: startup, pause/resume,
'   polling, heartbeat, duplicate-master checks, and processing ScanQueue
'   requests.
'
' Why this module exists:
'   Only the active master should process shared queue rows; this module is
'   the guardrail that keeps SharePoint queue activity coordinated.
'
' Commenting standard used in this rewrite:
'   Procedure comments explain both what the code does and why that
'   behavior matters in the scanning / SharePoint / Power Automate workflow.
'   The code logic and public signatures are intentionally kept stable; this
'   pass is primarily a readability, maintainability, and safety pass.
'==============================================================================



'===================
'modMasterQueueProcessor
'===================
Public Const POLL_SECONDS As Long = 10
Public Const HEARTBEAT_SECONDS As Long = 30

Public Const MAX_QUEUE_ROWS_PER_CYCLE As Long = 25
Public Const STALE_PROCESSING_MINUTES As Long = 2

Private Const QUEUE_UPDATE_RETRY_ATTEMPTS As Long = 3
Private Const QUEUE_UPDATE_RETRY_DELAY_SECONDS As Double = 1
Private Const QUEUE_UPDATE_MAX_FAILED_CYCLES As Long = 3

Private mQueueUpdateFailureCounts As Object

Private Const REVISION_TOKEN_NAME As String = "_DeliveryListRevisionToken"
Private Const REVISION_UPDATED_NAME As String = "_DeliveryListRevisionUpdatedAt"
Private Const MASTER_QUEUE_POPUPS_ENABLED As Boolean = False

Private Const COMMENT_SET_PREFIX As String = "__COMMENT_SET__|"

Private mDeliveryListKey As String
Private mDeliveryListDisplay As String
Private mNextProcessorRun As Date
Private mProcessorScheduled As Boolean
Private mHeartbeatNextRun As Date
Private mHeartbeatScheduled As Boolean
Private mProcessorRunning As Boolean
Private mQueuePaused As Boolean
Private mQueuePauseReason As String
Private mQuietDepth As Long
Private mPrevScreenUpdating As Boolean
Private mPrevDisplayAlerts As Boolean
Private mPrevEnableEvents As Boolean
Private mPrevAskToUpdateLinks As Boolean
Private mPrevStatusBar As Variant
Private mPrevQueueScreenUpdating As Boolean
Private mPrevQueueEnableEvents As Boolean
Private mPrevQueueDisplayStatusBar As Boolean
Private mPrevQueueStatusBar As Variant
Private mManualScanFormPausedQueue As Boolean

Private Const ACTIVE_LIST_HEARTBEAT_STALE_MINUTES As Long = 3

Private mMasterSessionId As String
Private mDuplicateMasterWarningShown As Boolean

Public SuppressProcessScanPopups As Boolean
Public SuppressManualScanPopups As Boolean

'------------------------------------------------------------------------------
' Procedure: MasterQueueNotice
' Scope: Private Sub
'
' What it does:
'   Builds or displays the operator-facing notice/message used by
'   MasterQueueNotice.
'
' Why it exists:
'   The scanner/master workflow must tell operators when processing is paused,
'   blocked, failed, or waiting so they do not keep scanning into an unsafe
'   state.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub MasterQueueNotice(ByVal titleText As String, ByVal messageText As String, Optional ByVal style As VbMsgBoxStyle = vbInformation)
    Dim statusText As String

    statusText = titleText & ": " & Replace(Replace(messageText, vbCrLf, " | "), vbLf, " | ")

    On Error Resume Next
    Application.DisplayStatusBar = True
    Application.StatusBar = statusText
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: QueueUpdateStatusWithRetry
' Scope: Private Function
'
' What it does:
'   Retries a fragile operation and records the final success/failure state
'   for QueueUpdateStatusWithRetry.
'
' Why it exists:
'   SharePoint and Power Automate calls can temporarily fail; retrying avoids
'   losing scans because of one short network or service hiccup.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function QueueUpdateStatusWithRetry(ByVal itemId As Long, _
                                            ByVal statusText As String, _
                                            ByVal resultCode As String, _
                                            ByVal resultMessage As String, _
                                            Optional ByVal maxAttempts As Long = QUEUE_UPDATE_RETRY_ATTEMPTS) As Boolean
    Dim attempt As Long
    Dim ok As Boolean
    Dim waitUntil As Date
    Dim lastErrNum As Long
    Dim lastErrDesc As String

    If itemId <= 0 Then Exit Function
    If maxAttempts < 1 Then maxAttempts = 1

    For attempt = 1 To maxAttempts
        Err.Clear

        On Error Resume Next
        ok = PA_QueueUpdateStatus(itemId, statusText, resultCode, resultMessage)
        lastErrNum = Err.Number
        lastErrDesc = Err.Description
        On Error GoTo 0

        If ok Then
            QueueUpdateStatusWithRetry = True
            Exit Function
        End If

        If attempt < maxAttempts Then
            Application.StatusBar = "Retrying ScanQueue update " & attempt & "/" & maxAttempts & _
                                    " for item " & itemId & "..."

            waitUntil = Now + ((QUEUE_UPDATE_RETRY_DELAY_SECONDS * attempt) / 86400#)

            Do While Now < waitUntil
                DoEvents
            Loop
        End If
    Next attempt

    MasterQueueNotice _
        "Queue Update Failed", _
        "Could not update ScanQueue item " & itemId & _
        " after " & maxAttempts & " attempt(s)." & vbCrLf & _
        "Attempted Status: " & statusText & vbCrLf & _
        IIf(lastErrNum <> 0, "Error " & lastErrNum & ": " & lastErrDesc, "Power Automate returned False."), _
        vbExclamation
End Function

'------------------------------------------------------------------------------
' Procedure: QueueUpdateFailureCounts
' Scope: Private Function
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   QueueUpdateFailureCounts.
'
' Why it exists:
'   Delivery timing, queue timestamps, and scan timestamps drive status
'   messages such as Early, On-Time, Late, Processing, and Done.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function QueueUpdateFailureCounts() As Object
    If mQueueUpdateFailureCounts Is Nothing Then
        Set mQueueUpdateFailureCounts = CreateObject("Scripting.Dictionary")
    End If

    Set QueueUpdateFailureCounts = mQueueUpdateFailureCounts
End Function

'------------------------------------------------------------------------------
' Procedure: IncrementQueueUpdateFailureCycle
' Scope: Private Function
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   IncrementQueueUpdateFailureCycle.
'
' Why it exists:
'   Delivery timing, queue timestamps, and scan timestamps drive status
'   messages such as Early, On-Time, Late, Processing, and Done.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function IncrementQueueUpdateFailureCycle(ByVal itemId As Long) As Long
    Dim d As Object
    Dim k As String

    If itemId <= 0 Then Exit Function

    Set d = QueueUpdateFailureCounts()
    k = CStr(itemId)

    If Not d.Exists(k) Then
        d(k) = 0
    End If

    d(k) = CLng(d(k)) + 1
    IncrementQueueUpdateFailureCycle = CLng(d(k))
End Function

'------------------------------------------------------------------------------
' Procedure: ResetQueueUpdateFailureCycle
' Scope: Private Sub
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   ResetQueueUpdateFailureCycle.
'
' Why it exists:
'   Delivery timing, queue timestamps, and scan timestamps drive status
'   messages such as Early, On-Time, Late, Processing, and Done.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ResetQueueUpdateFailureCycle(ByVal itemId As Long)
    Dim d As Object
    Dim k As String

    If itemId <= 0 Then Exit Sub

    Set d = QueueUpdateFailureCounts()
    k = CStr(itemId)

    If d.Exists(k) Then
        d.Remove k
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: PauseQueueBecauseQueueStatusCannotBeWritten
' Scope: Private Sub
'
' What it does:
'   Handles queue/request state used by the shared ScanQueue workflow for
'   PauseQueueBecauseQueueStatusCannotBeWritten.
'
' Why it exists:
'   Queue state must be tracked carefully so buffered intake scans, master
'   processing, retries, and final results stay aligned.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub PauseQueueBecauseQueueStatusCannotBeWritten(ByVal itemId As Long, ByVal requestId As String, ByVal detailText As String)
    On Error Resume Next

    CancelExternalQueueSchedules

    mQueuePaused = True
    mQueuePauseReason = "ScanQueue status update failed for item " & itemId
    mProcessorRunning = False

    UpdateMasterHeartbeatStatus "Paused"

    MasterQueueNotice _
        "Queue Processor Paused", _
        "The master stopped queue processing because it could not write status updates back to ScanQueue." & vbCrLf & vbCrLf & _
        "ItemId: " & itemId & vbCrLf & _
        "RequestId: " & requestId & vbCrLf & vbCrLf & _
        detailText & vbCrLf & vbCrLf & _
        "This prevents infinite retrying or duplicate processing. Resume the queue after Power Automate is working again.", _
        vbExclamation

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: FailQueueItemAfterRepeatedStatusFailures
' Scope: Private Function
'
' What it does:
'   Handles queue/request state used by the shared ScanQueue workflow for
'   FailQueueItemAfterRepeatedStatusFailures.
'
' Why it exists:
'   Queue state must be tracked carefully so buffered intake scans, master
'   processing, retries, and final results stay aligned.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function FailQueueItemAfterRepeatedStatusFailures(ByVal itemId As Long, ByVal requestId As String, ByVal failedCycleCount As Long) As Boolean
    Dim failMessage As String

    failMessage = "Queue status update failed after " & failedCycleCount & _
                  " master queue cycle(s). Scan was not applied. Please retry this scan after Power Automate is available."

    If QueueUpdateStatusWithRetry(itemId, "Error", "QUEUE_UPDATE_FAILED", failMessage, 5) Then
        ResetQueueUpdateFailureCycle itemId
        FailQueueItemAfterRepeatedStatusFailures = True
    Else
        PauseQueueBecauseQueueStatusCannotBeWritten _
            itemId, _
            requestId, _
            "The master also failed to write the final Error status back to SharePoint."
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: BeginMasterQueueUiFreeze
' Scope: Private Sub
'
' What it does:
'   Controls the active sheet/window view, freeze panes, navigation, or
'   selected cell for BeginMasterQueueUiFreeze.
'
' Why it exists:
'   The workbook is used by scanners/operators, so opening the right view and
'   scan area reduces missed scans and operator confusion.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub BeginMasterQueueUiFreeze(Optional ByVal statusText As String = "Processing queued scans...")
    On Error Resume Next
    mPrevQueueScreenUpdating = Application.ScreenUpdating
    mPrevQueueEnableEvents = Application.EnableEvents
    mPrevQueueDisplayStatusBar = Application.DisplayStatusBar
    mPrevQueueStatusBar = Application.StatusBar

    Application.ScreenUpdating = False
    Application.EnableEvents = False
    Application.DisplayStatusBar = True
    Application.StatusBar = statusText
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: EndMasterQueueUiFreeze
' Scope: Private Sub
'
' What it does:
'   Controls the active sheet/window view, freeze panes, navigation, or
'   selected cell for EndMasterQueueUiFreeze.
'
' Why it exists:
'   The workbook is used by scanners/operators, so opening the right view and
'   scan area reduces missed scans and operator confusion.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub EndMasterQueueUiFreeze()
    On Error Resume Next
    Application.ScreenUpdating = mPrevQueueScreenUpdating
    Application.EnableEvents = mPrevQueueEnableEvents
    Application.DisplayStatusBar = mPrevQueueDisplayStatusBar
    Application.StatusBar = mPrevQueueStatusBar
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: BeginQuietQueueUi
' Scope: Private Sub
'
' What it does:
'   Handles queue/request state used by the shared ScanQueue workflow for
'   BeginQuietQueueUi.
'
' Why it exists:
'   Queue state must be tracked carefully so buffered intake scans, master
'   processing, retries, and final results stay aligned.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
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
'   Handles queue/request state used by the shared ScanQueue workflow for
'   EndQuietQueueUi.
'
' Why it exists:
'   Queue state must be tracked carefully so buffered intake scans, master
'   processing, retries, and final results stay aligned.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
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
' Procedure: ResolveDeliveryListDate
' Scope: Private Function
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   ResolveDeliveryListDate.
'
' Why it exists:
'   Delivery timing, queue timestamps, and scan timestamps drive status
'   messages such as Early, On-Time, Late, Processing, and Done.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function ResolveDeliveryListDate() As Date
    On Error Resume Next
    ResolveDeliveryListDate = GetDeliveryListDateForFileName(ThisWorkbook.Worksheets("Delivery List"))
    On Error GoTo 0
End Function

'------------------------------------------------------------------------------
' Procedure: GetCurrentDeliveryListKey
' Scope: Public Function
'
' What it does:
'   Returns a workbook object, setting, status value, parsed value, or
'   calculated result used by other procedures (GetCurrentDeliveryListKey).
'
' Why it exists:
'   Using one getter keeps callers from duplicating lookup logic and protects
'   them from missing sheets, missing names, or blank values.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function GetCurrentDeliveryListKey() As String
    Dim dt As Date
    Dim resolvedKey As String

    dt = ResolveDeliveryListDate()

    If dt > 0 Then
        resolvedKey = "DL_" & Format$(dt, "yyyy_mm_dd")
    Else
        resolvedKey = "DL_UNKNOWN"
    End If

    'Do not let DL_UNKNOWN get permanently cached.
    'If the workbook was still opening or the date was not readable during startup,
    'the queue processor must be allowed to recover on the next poll.
    If Len(mDeliveryListKey) = 0 Or _
       UCase$(mDeliveryListKey) = "DL_UNKNOWN" Or _
       UCase$(resolvedKey) <> "DL_UNKNOWN" Then
        mDeliveryListKey = resolvedKey
    End If

    GetCurrentDeliveryListKey = mDeliveryListKey
End Function

'------------------------------------------------------------------------------
' Procedure: GetCurrentDeliveryListDisplay
' Scope: Public Function
'
' What it does:
'   Returns a workbook object, setting, status value, parsed value, or
'   calculated result used by other procedures
'   (GetCurrentDeliveryListDisplay).
'
' Why it exists:
'   Using one getter keeps callers from duplicating lookup logic and protects
'   them from missing sheets, missing names, or blank values.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function GetCurrentDeliveryListDisplay() As String
    Dim dt As Date

    If Len(mDeliveryListDisplay) > 0 Then
        GetCurrentDeliveryListDisplay = mDeliveryListDisplay
        Exit Function
    End If

    dt = ResolveDeliveryListDate()

    If dt > 0 Then
        mDeliveryListDisplay = "Delivery List For " & Format$(dt, "m/d/yyyy")
    Else
        mDeliveryListDisplay = "Delivery List"
    End If

    GetCurrentDeliveryListDisplay = mDeliveryListDisplay
End Function

'------------------------------------------------------------------------------
' Procedure: RefreshCurrentDeliveryListIdentity
' Scope: Public Sub
'
' What it does:
'   Refreshes calculated display/state based on the latest workbook data for
'   RefreshCurrentDeliveryListIdentity.
'
' Why it exists:
'   Operators depend on the visible sheets matching the real scan/queue state
'   after edits, imports, and queue processing.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub RefreshCurrentDeliveryListIdentity()
    mDeliveryListKey = vbNullString
    mDeliveryListDisplay = vbNullString

    Call GetCurrentDeliveryListKey
    Call GetCurrentDeliveryListDisplay
End Sub

'------------------------------------------------------------------------------
' Procedure: GetMasterSessionId
' Scope: Private Function
'
' What it does:
'   Returns a workbook object, setting, status value, parsed value, or
'   calculated result used by other procedures (GetMasterSessionId).
'
' Why it exists:
'   Using one getter keeps callers from duplicating lookup logic and protects
'   them from missing sheets, missing names, or blank values.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetMasterSessionId() As String
    If Len(mMasterSessionId) = 0 Then
        Randomize
        mMasterSessionId = Format$(Now, "yyyymmdd_hhnnss") & "_" & _
                           Format$(CLng(Timer * 1000), "000000") & "_" & _
                           Format$(CLng(Rnd() * 100000), "00000")
    End If

    GetMasterSessionId = mMasterSessionId
End Function

'------------------------------------------------------------------------------
' Procedure: GetMachineNameText
' Scope: Private Function
'
' What it does:
'   Returns a workbook object, setting, status value, parsed value, or
'   calculated result used by other procedures (GetMachineNameText).
'
' Why it exists:
'   Using one getter keeps callers from duplicating lookup logic and protects
'   them from missing sheets, missing names, or blank values.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetMachineNameText() As String
    GetMachineNameText = Trim$(Environ$("COMPUTERNAME"))
    If Len(GetMachineNameText) = 0 Then GetMachineNameText = "UNKNOWN-PC"
End Function

'------------------------------------------------------------------------------
' Procedure: BuildDuplicateMasterMessage
' Scope: Private Function
'
' What it does:
'   Maintains or checks active-master registration state for
'   BuildDuplicateMasterMessage.
'
' Why it exists:
'   The master must refuse to process a delivery list if another live master
'   already owns that same list. This prevents duplicate queue processing.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BuildDuplicateMasterMessage(ByVal duplicateInfo As Object) As String
    Dim hbText As String

    hbText = PA_DictText(duplicateInfo, "lastHeartbeat")

    BuildDuplicateMasterMessage = _
        "Another live master appears to already be open for this same delivery list." & vbCrLf & vbCrLf & _
        "Delivery List Key: " & GetCurrentDeliveryListKey() & vbCrLf & _
        "Other Workbook: " & PA_DictText(duplicateInfo, "processorWorkbook") & vbCrLf & _
        "Other Machine: " & PA_DictText(duplicateInfo, "machineName") & vbCrLf & _
        "Other Status: " & UCase$(PA_DictText(duplicateInfo, "processorStatus")) & vbCrLf & _
        "Last Heartbeat: " & hbText & vbCrLf & vbCrLf & _
        "Queue processing will stay stopped in this workbook. Use only one master for the same date/list."
End Function

Private Function DuplicateMasterStatusLooksLive(ByVal statusText As String) As Boolean
    Select Case UCase$(Trim$(statusText))
        Case "ONLINE", "OPEN", "ACTIVE", "PAUSED"
            DuplicateMasterStatusLooksLive = True
    End Select
End Function

Private Function DuplicateMasterHeartbeatIsFresh(ByVal heartbeatText As String) As Boolean
    Dim heartbeatAt As Date

    heartbeatAt = PA_ParseIsoDate(heartbeatText)
    If heartbeatAt <= 0 Then Exit Function

    DuplicateMasterHeartbeatIsFresh = _
        (DateDiff("n", heartbeatAt, Now) < ACTIVE_LIST_HEARTBEAT_STALE_MINUTES)
End Function

Private Function DuplicateMasterInfoLooksFresh(ByVal duplicateInfo As Object) As Boolean
    If duplicateInfo Is Nothing Then Exit Function
    If Not DuplicateMasterStatusLooksLive(PA_DictText(duplicateInfo, "processorStatus")) Then Exit Function

    DuplicateMasterInfoLooksFresh = _
        DuplicateMasterHeartbeatIsFresh(PA_DictText(duplicateInfo, "lastHeartbeat"))
End Function

'------------------------------------------------------------------------------
' Procedure: BlockingDuplicateMasterExists
' Scope: Private Function
'
' What it does:
'   Checks the ActiveDeliveryLists SharePoint state and returns True when this
'   workbook must not process queue rows.
'
' Why it exists:
'   A warning is not enough in a multi-user queue. If the duplicate check finds
'   another live master, or if the duplicate check itself fails, the safe action
'   is to stop processing until the operator resolves it.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BlockingDuplicateMasterExists(ByRef blockMessage As String) As Boolean
    Dim dupes As Collection
    Dim d As Object

    On Error GoTo ErrHandler

    Set dupes = PA_ActiveCheckDuplicate(GetCurrentDeliveryListKey(), GetMasterSessionId())
    If dupes Is Nothing Then Exit Function
    If dupes.Count = 0 Then Exit Function

    For Each d In dupes
        If DuplicateMasterInfoLooksFresh(d) Then
            blockMessage = BuildDuplicateMasterMessage(d)
            BlockingDuplicateMasterExists = True
            Exit Function
        End If
    Next d

    Exit Function

ErrHandler:
    blockMessage = _
        "The master could not verify whether another active master is already processing this delivery list." & vbCrLf & vbCrLf & _
        "Delivery List Key: " & GetCurrentDeliveryListKey() & vbCrLf & _
        "Error " & Err.Number & ": " & Err.Description & vbCrLf & vbCrLf & _
        "Queue processing will stay stopped until the duplicate-master check can run successfully."
    BlockingDuplicateMasterExists = True
End Function

'------------------------------------------------------------------------------
' Procedure: WarnIfDuplicateMasterExists
' Scope: Private Sub
'
' What it does:
'   Displays the duplicate-master block message once.
'
' Why it exists:
'   Some older buttons/debug procedures call the warning path directly. Keeping
'   this wrapper preserves that surface while the real safety check now blocks.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub WarnIfDuplicateMasterExists()
    Dim warningText As String

    If mDuplicateMasterWarningShown Then Exit Sub
    If Not BlockingDuplicateMasterExists(warningText) Then Exit Sub

    mDuplicateMasterWarningShown = True
    MsgBox warningText, vbExclamation, "Duplicate Master Warning"
End Sub

'------------------------------------------------------------------------------
' Procedure: GetWorkbookNameText
' Scope: Private Function
'
' What it does:
'   Returns a workbook object, setting, status value, parsed value, or
'   calculated result used by other procedures (GetWorkbookNameText).
'
' Why it exists:
'   Using one getter keeps callers from duplicating lookup logic and protects
'   them from missing sheets, missing names, or blank values.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetWorkbookNameText(ByVal nameText As String) As String
    On Error Resume Next
    GetWorkbookNameText = CStr(Evaluate(ThisWorkbook.names(nameText).RefersTo))
    On Error GoTo 0
End Function

'------------------------------------------------------------------------------
' Procedure: SetWorkbookNameText
' Scope: Private Sub
'
' What it does:
'   Performs the workbook-specific step named SetWorkbookNameText inside
'   modMasterQueueProcessor.
'
' Why it exists:
'   Only the active master should process shared queue rows; this module is
'   the guardrail that keeps SharePoint queue activity coordinated.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub SetWorkbookNameText(ByVal nameText As String, ByVal valueText As String)
    On Error Resume Next
    ThisWorkbook.names(nameText).Delete
    On Error GoTo 0

    ThisWorkbook.names.Add Name:=nameText, RefersTo:="=""" & Replace(valueText, """", """""") & """"
End Sub

'------------------------------------------------------------------------------
' Procedure: EnsureCurrentRevisionInitialized
' Scope: Private Sub
'
' What it does:
'   Verifies that required workbook objects, sheets, layout, names, or
'   settings exist for EnsureCurrentRevisionInitialized.
'
' Why it exists:
'   Many operations assume these supporting objects already exist; ensuring
'   them first prevents runtime failures after imports or workbook copies.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub EnsureCurrentRevisionInitialized()
    If Len(GetWorkbookNameText(REVISION_TOKEN_NAME)) = 0 Then
        BumpCurrentDeliveryListRevision
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: GetCurrentDeliveryListRevisionToken
' Scope: Public Function
'
' What it does:
'   Returns a workbook object, setting, status value, parsed value, or
'   calculated result used by other procedures
'   (GetCurrentDeliveryListRevisionToken).
'
' Why it exists:
'   Using one getter keeps callers from duplicating lookup logic and protects
'   them from missing sheets, missing names, or blank values.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function GetCurrentDeliveryListRevisionToken() As String
    EnsureCurrentRevisionInitialized
    GetCurrentDeliveryListRevisionToken = GetWorkbookNameText(REVISION_TOKEN_NAME)
End Function

'------------------------------------------------------------------------------
' Procedure: GetCurrentDeliveryListRevisionUpdatedAt
' Scope: Public Function
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   GetCurrentDeliveryListRevisionUpdatedAt.
'
' Why it exists:
'   Delivery timing, queue timestamps, and scan timestamps drive status
'   messages such as Early, On-Time, Late, Processing, and Done.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function GetCurrentDeliveryListRevisionUpdatedAt() As String
    EnsureCurrentRevisionInitialized
    GetCurrentDeliveryListRevisionUpdatedAt = GetWorkbookNameText(REVISION_UPDATED_NAME)
End Function

'------------------------------------------------------------------------------
' Procedure: BumpCurrentDeliveryListRevision
' Scope: Public Sub
'
' What it does:
'   Performs the workbook-specific step named BumpCurrentDeliveryListRevision
'   inside modMasterQueueProcessor.
'
' Why it exists:
'   Only the active master should process shared queue rows; this module is
'   the guardrail that keeps SharePoint queue activity coordinated.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub BumpCurrentDeliveryListRevision()
    Dim tokenText As String

    tokenText = Format$(Now, "yyyymmdd_hhnnss") & "_" & Format$(CLng((Timer - Int(Timer / 86400#) * 86400#) * 1000), "000000")

    SetWorkbookNameText REVISION_TOKEN_NAME, tokenText
    SetWorkbookNameText REVISION_UPDATED_NAME, Format$(Now, "m/d/yyyy h:mm:ss AM/PM")
End Sub

'------------------------------------------------------------------------------
' Procedure: RegisterThisMasterDeliveryList
' Scope: Public Sub
'
' What it does:
'   Writes/refreshes this master workbook heartbeat and metadata in the
'   ActiveDeliveryLists SharePoint list.
'
' Why it exists:
'   Intake stations use that registration to know which delivery lists are
'   online and which workbook is responsible for processing their scans.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub RegisterThisMasterDeliveryList()
    Dim listDt As Date

    listDt = ResolveDeliveryListDate()

    Call PA_ActiveUpsertHeartbeat( _
            GetCurrentDeliveryListKey(), _
            GetCurrentDeliveryListDisplay(), _
            listDt, _
            "Online", _
            ThisWorkbook.Name, _
            GetMasterSessionId(), _
            GetMachineNameText(), _
            GetCurrentDeliveryListRevisionToken(), _
            GetCurrentDeliveryListRevisionUpdatedAt())
End Sub

'------------------------------------------------------------------------------
' Procedure: StartExternalQueueProcessor
' Scope: Public Sub
'
' What it does:
'   Starts full master-processing mode by clearing pause state, checking for
'   duplicate active masters, registering this workbook, scheduling queue
'   polling, and scheduling heartbeat updates.
'
' Why it exists:
'   The master must explicitly opt into processing because only one workbook
'   should be allowed to modify shared ScanQueue rows and heartbeat state at a
'   time.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'
' Extra note:
'   This is intentionally blocked when the workbook is read-only so accidental
'   SharePoint opens cannot process scans.
'------------------------------------------------------------------------------
Public Sub StartExternalQueueProcessor()
    Dim duplicateMessage As String

    If ThisWorkbook.ReadOnly Then
        mQueuePaused = True
        mQueuePauseReason = "Read-only safe mode"

        MasterQueueNotice _
            "Read-Only Safe Mode", _
            "This master workbook is open read-only." & vbCrLf & vbCrLf & _
            "The external ScanQueue processor, heartbeat, and SharePoint update macros will not start.", _
            vbInformation

        Exit Sub
    End If

    mQueuePaused = False
    mQueuePauseReason = vbNullString

    RefreshCurrentDeliveryListIdentity

    If BlockingDuplicateMasterExists(duplicateMessage) Then
        CancelExternalQueueSchedules

        mQueuePaused = True
        mQueuePauseReason = "Duplicate master blocked"
        mProcessorRunning = False
        mDuplicateMasterWarningShown = True

        MasterQueueNotice _
            "Duplicate Master Blocked", _
            Replace(duplicateMessage, vbCrLf & vbCrLf, vbCrLf), _
            vbExclamation

        MsgBox duplicateMessage, vbCritical, "Duplicate Master Blocked"
        Exit Sub
    End If

    RegisterThisMasterDeliveryList

    Application.StatusBar = "Publishing initial intake snapshots..."
    PublishAllStageSnapshots False, False

    ScheduleExternalQueueProcessor
    ScheduleHeartbeat
    ScheduleAutoSnapshotPublish
    UpdateMasterHeartbeatStatus "Online"

    Application.StatusBar = "Master queue processor running."

    'Run one immediate queue check on open instead of waiting for the first timer.
    ProcessExternalQueuedScans
End Sub

Public Sub InitializeExternalQueuePausedOnOpen()
    On Error Resume Next
    CancelExternalQueueSchedules
    CancelAutoSnapshotPublish
    On Error GoTo 0

    mQueuePaused = True
    mQueuePauseReason = "Paused on open"
    mProcessorRunning = False

    On Error Resume Next
    UpdateMasterHeartbeatStatus "Paused"
    CreateOrRefreshHomeMenu
    On Error GoTo 0

    Application.StatusBar = "Queue and snapshots are paused. Click QUEUE PAUSED to start processing."
End Sub

'------------------------------------------------------------------------------
' Procedure: StopExternalQueueProcessor
' Scope: Public Sub
'
' What it does:
'   Stops scheduled queue polling and heartbeat callbacks and marks the master
'   as offline/paused where possible.
'
' Why it exists:
'   This gives the operator a clean way to shut down the processor without
'   leaving stale OnTime tasks or misleading online status.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub StopExternalQueueProcessor()
    On Error Resume Next

    If mProcessorScheduled Then
        Application.OnTime EarliestTime:=mNextProcessorRun, Procedure:="'" & ThisWorkbook.Name & "'!ExternalQueueProcessorBridge", Schedule:=False
    End If

    If mHeartbeatScheduled Then
        Application.OnTime EarliestTime:=mHeartbeatNextRun, Procedure:="'" & ThisWorkbook.Name & "'!MasterHeartbeatBridge", Schedule:=False
    End If

    On Error GoTo 0

    mProcessorScheduled = False
    mHeartbeatScheduled = False
    mProcessorRunning = False
    mQueuePaused = True
    mQueuePauseReason = "Stopped"
    CancelAutoSnapshotPublish
    UpdateMasterHeartbeatStatus "Offline"
End Sub

'------------------------------------------------------------------------------
' Procedure: ScheduleExternalQueueProcessor
' Scope: Public Sub
'
' What it does:
'   Schedules the next queue-processing pass with Application.OnTime.
'
' Why it exists:
'   OnTime keeps the master responsive and avoids running the processor
'   continuously in a tight loop.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub ScheduleExternalQueueProcessor()
    If mQueuePaused Then Exit Sub
    If mProcessorScheduled Then Exit Sub

    mNextProcessorRun = Now + TimeSerial(0, 0, POLL_SECONDS)
    mProcessorScheduled = True

    Application.OnTime EarliestTime:=mNextProcessorRun, Procedure:="'" & ThisWorkbook.Name & "'!ExternalQueueProcessorBridge", Schedule:=True
End Sub

'------------------------------------------------------------------------------
' Procedure: ExternalQueueProcessorBridge
' Scope: Public Sub
'
' What it does:
'   Entry point called by Application.OnTime to run one queue-processing cycle
'   safely.
'
' Why it exists:
'   OnTime requires a public no-argument procedure, so this bridge wraps the
'   real processor logic and handles rescheduling.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub ExternalQueueProcessorBridge()
    On Error GoTo SafeExit

    mProcessorScheduled = False

    If mQueuePaused Then Exit Sub
    If mProcessorRunning Then Exit Sub

    mProcessorRunning = True
    ProcessExternalQueuedScans

SafeExit:
    mProcessorRunning = False

    If Not mQueuePaused Then
        ScheduleExternalQueueProcessor
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: ScheduleHeartbeat
' Scope: Public Sub
'
' What it does:
'   Maintains or checks active-master registration state for
'   ScheduleHeartbeat.
'
' Why it exists:
'   The system needs to know which master workbook is online so intake
'   stations do not depend on the wrong processor.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub ScheduleHeartbeat()
    If mQueuePaused Then Exit Sub
    If mHeartbeatScheduled Then Exit Sub

    mHeartbeatNextRun = Now + TimeSerial(0, 0, HEARTBEAT_SECONDS)
    mHeartbeatScheduled = True

    Application.OnTime EarliestTime:=mHeartbeatNextRun, Procedure:="'" & ThisWorkbook.Name & "'!MasterHeartbeatBridge", Schedule:=True
End Sub

'------------------------------------------------------------------------------
' Procedure: MasterHeartbeatBridge
' Scope: Public Sub
'
' What it does:
'   Maintains or checks active-master registration state for
'   MasterHeartbeatBridge.
'
' Why it exists:
'   The system needs to know which master workbook is online so intake
'   stations do not depend on the wrong processor.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub MasterHeartbeatBridge()
    mHeartbeatScheduled = False

    If mQueuePaused Then Exit Sub

    UpdateMasterHeartbeatStatus "Online"
    ScheduleHeartbeat
End Sub

'------------------------------------------------------------------------------
' Procedure: IsExternalQueuePaused
' Scope: Public Function
'
' What it does:
'   Handles queue/request state used by the shared ScanQueue workflow for
'   IsExternalQueuePaused.
'
' Why it exists:
'   Queue state must be tracked carefully so buffered intake scans, master
'   processing, retries, and final results stay aligned.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function IsExternalQueuePaused() As Boolean
    IsExternalQueuePaused = mQueuePaused
End Function

'------------------------------------------------------------------------------
' Procedure: IsExternalQueueBusy
' Scope: Public Function
'
' What it does:
'   Handles queue/request state used by the shared ScanQueue workflow for
'   IsExternalQueueBusy.
'
' Why it exists:
'   Queue state must be tracked carefully so buffered intake scans, master
'   processing, retries, and final results stay aligned.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function IsExternalQueueBusy() As Boolean
    IsExternalQueueBusy = mProcessorRunning
End Function

'------------------------------------------------------------------------------
' Procedure: GetExternalQueuePauseReason
' Scope: Public Function
'
' What it does:
'   Handles queue/request state used by the shared ScanQueue workflow for
'   GetExternalQueuePauseReason.
'
' Why it exists:
'   Queue state must be tracked carefully so buffered intake scans, master
'   processing, retries, and final results stay aligned.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function GetExternalQueuePauseReason() As String
    GetExternalQueuePauseReason = mQueuePauseReason
End Function

'------------------------------------------------------------------------------
' Procedure: WaitForExternalQueueIdle
' Scope: Public Function
'
' What it does:
'   Handles queue/request state used by the shared ScanQueue workflow for
'   WaitForExternalQueueIdle.
'
' Why it exists:
'   Queue state must be tracked carefully so buffered intake scans, master
'   processing, retries, and final results stay aligned.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function WaitForExternalQueueIdle(Optional ByVal timeoutSeconds As Double = 20) As Boolean
    Dim t0 As Double

    t0 = Timer

    Do While mProcessorRunning
        DoEvents

        If Timer < t0 Then
            t0 = t0 - 86400#
        End If

        If (Timer - t0) >= timeoutSeconds Then Exit Function
    Loop

    WaitForExternalQueueIdle = True
End Function

'------------------------------------------------------------------------------
' Procedure: CancelExternalQueueSchedules
' Scope: Private Sub
'
' What it does:
'   Handles queue/request state used by the shared ScanQueue workflow for
'   CancelExternalQueueSchedules.
'
' Why it exists:
'   Queue state must be tracked carefully so buffered intake scans, master
'   processing, retries, and final results stay aligned.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub CancelExternalQueueSchedules()
    On Error Resume Next

    If mProcessorScheduled Then
        Application.OnTime EarliestTime:=mNextProcessorRun, Procedure:="'" & ThisWorkbook.Name & "'!ExternalQueueProcessorBridge", Schedule:=False
    End If

    If mHeartbeatScheduled Then
        Application.OnTime EarliestTime:=mHeartbeatNextRun, Procedure:="'" & ThisWorkbook.Name & "'!MasterHeartbeatBridge", Schedule:=False
    End If

    On Error GoTo 0

    mProcessorScheduled = False
    mHeartbeatScheduled = False
End Sub

'------------------------------------------------------------------------------
' Procedure: PauseExternalQueue
' Scope: Public Function
'
' What it does:
'   Handles queue/request state used by the shared ScanQueue workflow for
'   PauseExternalQueue.
'
' Why it exists:
'   Queue state must be tracked carefully so buffered intake scans, master
'   processing, retries, and final results stay aligned.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function PauseExternalQueue(Optional ByVal reasonText As String = "Manual maintenance") As Boolean
        
    If mQueuePaused Then Exit Function

    Application.StatusBar = "Waiting for scan processing to finish..."

    If Not WaitForExternalQueueIdle(20) Then
        Application.StatusBar = False
        MsgBox "The queue processor is still busy." & vbCrLf & _
               "Please wait a few seconds and try again.", _
               vbExclamation, "Queue Busy"
        Exit Function
    End If

    CancelExternalQueueSchedules
    CancelAutoSnapshotPublish

    mQueuePaused = True
    mQueuePauseReason = reasonText
    mProcessorRunning = False

    'Manual maintenance pause should be visible to the queue workbook
    UpdateMasterHeartbeatStatus "Paused"

    Application.StatusBar = False
    PauseExternalQueue = True
End Function

'------------------------------------------------------------------------------
' Procedure: ResumeExternalQueue
' Scope: Public Sub
'
' What it does:
'   Handles queue/request state used by the shared ScanQueue workflow for
'   ResumeExternalQueue.
'
' Why it exists:
'   Queue state must be tracked carefully so buffered intake scans, master
'   processing, retries, and final results stay aligned.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub ResumeExternalQueue()
    mQueuePaused = False
    mQueuePauseReason = vbNullString

    'Manual resume should be visible to the queue workbook
    RegisterThisMasterDeliveryList
    UpdateMasterHeartbeatStatus "Online"

    ScheduleExternalQueueProcessor
    ScheduleHeartbeat
    ScheduleAutoSnapshotPublish
    PublishAllStageSnapshots False, False

    Application.StatusBar = False
End Sub

'------------------------------------------------------------------------------
' Procedure: ForceExternalQueuePausedForManualEdit
'
' Keeps the queue in a true paused state and refreshes the Utility Panel button
' without resuming processing.
'
' This is needed for Delivery List manual edit mode because edit mode is not a
' temporary action like Import/Update. The queue should remain paused until the
' user intentionally clicks QUEUE PAUSED to resume.
'------------------------------------------------------------------------------
Public Sub ForceExternalQueuePausedForManualEdit(Optional ByVal reasonText As String = "Delivery List manual edit mode")
    On Error Resume Next
    CancelExternalQueueSchedules
    On Error GoTo 0

    mQueuePaused = True
    mQueuePauseReason = reasonText
    mProcessorRunning = False

    On Error Resume Next
    UpdateMasterHeartbeatStatus "Paused"
    On Error GoTo 0

    Application.StatusBar = "Queue paused for Delivery List manual edits. Click QUEUE PAUSED to resume scan processing."

    'Refresh the Utility Panel button, but preserve the active Delivery List sheet.
    On Error Resume Next
    RefreshHomeMenuPreserveActiveSheet "Delivery List"

    If Err.Number <> 0 Then
        Err.Clear
        CreateOrRefreshHomeMenu
    End If

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: DeliveryListEditModeIsActive
'
' Checks whether OpenDeliveryListForEditing actually entered edit mode.
' This prevents the queue from staying paused if the user clicks No on the
' confirmation prompt.
'------------------------------------------------------------------------------
Private Function DeliveryListEditModeIsActive() As Boolean
    Dim nm As Name

    On Error Resume Next
    Set nm = ThisWorkbook.names("_DeliveryEditMode")
    DeliveryListEditModeIsActive = Not nm Is Nothing
    On Error GoTo 0
End Function

'------------------------------------------------------------------------------
' Procedure: SuspendQueueForAction
' Scope: Private Function
'
' What it does:
'   Handles queue/request state used by the shared ScanQueue workflow for
'   SuspendQueueForAction.
'
' Why it exists:
'   Queue state must be tracked carefully so buffered intake scans, master
'   processing, retries, and final results stay aligned.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SuspendQueueForAction(ByVal actionName As String, ByRef resumeWhenDone As Boolean) As Boolean
    resumeWhenDone = False

    'If user already manually paused the queue, do not touch queue state
    If mQueuePaused Then
        SuspendQueueForAction = True
        Exit Function
    End If

    Application.StatusBar = "Waiting for scan processing to finish..."

    If Not WaitForExternalQueueIdle(20) Then
        Application.StatusBar = False
        MsgBox "The queue processor is still busy." & vbCrLf & _
               "Please wait a few seconds and try again.", _
               vbExclamation, "Queue Busy"
        Exit Function
    End If

    'Temporarily stop scheduled processing and mark the master paused so intake
    'stations can block new scans while the delivery list or snapshots change.
    CancelExternalQueueSchedules

    mQueuePaused = True
    mQueuePauseReason = actionName
    mProcessorRunning = False

    On Error Resume Next
    UpdateMasterHeartbeatStatus "Paused"
    On Error GoTo 0

    Application.StatusBar = False
    resumeWhenDone = True
    SuspendQueueForAction = True
End Function

'------------------------------------------------------------------------------
' Procedure: ResumeQueueAfterAction
' Scope: Private Sub
'
' What it does:
'   Handles queue/request state used by the shared ScanQueue workflow for
'   ResumeQueueAfterAction.
'
' Why it exists:
'   Queue state must be tracked carefully so buffered intake scans, master
'   processing, retries, and final results stay aligned.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ResumeQueueAfterAction(ByVal resumeWhenDone As Boolean)
    Application.StatusBar = False

    If Not resumeWhenDone Then Exit Sub

    'Resume quietly after normal button actions
    mQueuePaused = False
    mQueuePauseReason = vbNullString

    On Error Resume Next
    RegisterThisMasterDeliveryList
    On Error GoTo 0

    ScheduleExternalQueueProcessor
    ScheduleHeartbeat
    ScheduleAutoSnapshotPublish

    'Refresh the Utility Panel so the queue button goes back to running state
    On Error Resume Next
    CreateOrRefreshHomeMenu
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: BeginQueueSafeAction
' Scope: Private Function
'
' What it does:
'   Handles queue/request state used by the shared ScanQueue workflow for
'   BeginQueueSafeAction.
'
' Why it exists:
'   Queue state must be tracked carefully so buffered intake scans, master
'   processing, retries, and final results stay aligned.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BeginQueueSafeAction(ByVal actionName As String, ByRef resumeWhenDone As Boolean) As Boolean
    BeginQueueSafeAction = SuspendQueueForAction(actionName, resumeWhenDone)
End Function

'------------------------------------------------------------------------------
' Procedure: EndQueueSafeAction
' Scope: Private Sub
'
' What it does:
'   Handles queue/request state used by the shared ScanQueue workflow for
'   EndQueueSafeAction.
'
' Why it exists:
'   Queue state must be tracked carefully so buffered intake scans, master
'   processing, retries, and final results stay aligned.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub EndQueueSafeAction(ByVal resumeWhenDone As Boolean)
    ResumeQueueAfterAction resumeWhenDone
End Sub

'------------------------------------------------------------------------------
' Procedure: RunImportNewDeliveryListSafe
' Scope: Public Sub
'
' What it does:
'   Performs the workbook-specific step named RunImportNewDeliveryListSafe
'   inside modMasterQueueProcessor.
'
' Why it exists:
'   Only the active master should process shared queue rows; this module is
'   the guardrail that keeps SharePoint queue activity coordinated.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub RunImportNewDeliveryListSafe()
    Dim resumeWhenDone As Boolean

    On Error GoTo ErrHandler
    If Not BeginQueueSafeAction("Importing delivery list", resumeWhenDone) Then Exit Sub

    ImportNewDeliveryList

SafeExit:
    EndQueueSafeAction resumeWhenDone
    Exit Sub

ErrHandler:
    MsgBox "Import failed." & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbExclamation, "Import Error"
    Resume SafeExit
End Sub

'------------------------------------------------------------------------------
' Procedure: RunUpdateExistingDeliveryListSafe
' Scope: Public Sub
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   RunUpdateExistingDeliveryListSafe.
'
' Why it exists:
'   Delivery timing, queue timestamps, and scan timestamps drive status
'   messages such as Early, On-Time, Late, Processing, and Done.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub RunUpdateExistingDeliveryListSafe()
    Dim resumeWhenDone As Boolean

    On Error GoTo ErrHandler
    If Not BeginQueueSafeAction("Updating delivery list", resumeWhenDone) Then Exit Sub

    UpdateExistingDeliveryList

SafeExit:
    EndQueueSafeAction resumeWhenDone
    Exit Sub

ErrHandler:
    MsgBox "Update failed." & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbExclamation, "Update Error"
    Resume SafeExit
End Sub

'------------------------------------------------------------------------------
' Procedure: RunPrintDeliveryListBySectionSafe
' Scope: Public Sub
'
' What it does:
'   Performs the workbook-specific step named
'   RunPrintDeliveryListBySectionSafe inside modMasterQueueProcessor.
'
' Why it exists:
'   Only the active master should process shared queue rows; this module is
'   the guardrail that keeps SharePoint queue activity coordinated.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub RunPrintDeliveryListBySectionSafe()
    Dim resumeWhenDone As Boolean

    On Error GoTo ErrHandler
    If Not BeginQueueSafeAction("Printing delivery lists", resumeWhenDone) Then Exit Sub

    PrintDeliveryListBySection

SafeExit:
    EndQueueSafeAction resumeWhenDone
    Exit Sub

ErrHandler:
    MsgBox "Print failed." & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbExclamation, "Print Error"
    Resume SafeExit
End Sub

'------------------------------------------------------------------------------
' Procedure: RunExportListsFromUtilityPanelSafe
' Scope: Public Sub
'
' What it does:
'   Builds, formats, deletes, or wires workbook UI shapes/buttons/panels for
'   RunExportListsFromUtilityPanelSafe.
'
' Why it exists:
'   Buttons and utility panels are the operator-facing control surface, so
'   they must be rebuilt consistently after imports or sheet refreshes.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub RunExportListsFromUtilityPanelSafe()
    Dim resumeWhenDone As Boolean

    On Error GoTo ErrHandler
    If Not BeginQueueSafeAction("Exporting lists", resumeWhenDone) Then Exit Sub

    ExportListsFromUtilityPanel

SafeExit:
    EndQueueSafeAction resumeWhenDone
    Exit Sub

ErrHandler:
    MsgBox "Export failed." & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbExclamation, "Export Error"
    Resume SafeExit
End Sub

'------------------------------------------------------------------------------
' Procedure: RunManualPublishAllStageSnapshotsSafe
' Scope: Public Sub
'
' What it does:
'   Handles part of the master-to-intake snapshot workflow for
'   RunManualPublishAllStageSnapshotsSafe.
'
' Why it exists:
'   Snapshots let intake workbooks display and scan against current delivery
'   data without opening or editing the master workbook.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub RunManualPublishAllStageSnapshotsSafe()
    Dim resumeWhenDone As Boolean

    On Error GoTo ErrHandler

    If IsExternalQueuePaused() Then
        MsgBox "Snapshot publishing is paused with the queue." & vbCrLf & vbCrLf & _
               "Click QUEUE PAUSED to start queue processing and snapshot publishing.", _
               vbInformation, "Snapshots Paused"
        Exit Sub
    End If

    If Not BeginQueueSafeAction("Publishing intake snapshots", resumeWhenDone) Then Exit Sub

    ManualPublishAllStageSnapshots

SafeExit:
    EndQueueSafeAction resumeWhenDone
    Exit Sub

ErrHandler:
    MsgBox "Publish snapshots failed." & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbExclamation, "Publish Snapshots"

    Resume SafeExit
End Sub

'------------------------------------------------------------------------------
' Procedure: RunSaveCopyForSharePointSafe
' Scope: Public Sub
'
' What it does:
'   Performs the workbook-specific step named RunSaveCopyForSharePointSafe
'   inside modMasterQueueProcessor.
'
' Why it exists:
'   Only the active master should process shared queue rows; this module is
'   the guardrail that keeps SharePoint queue activity coordinated.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub RunSaveCopyForSharePointSafe()
    Dim resumeWhenDone As Boolean

    On Error GoTo ErrHandler
    If Not BeginQueueSafeAction("Saving SharePoint copy", resumeWhenDone) Then Exit Sub

    SaveCopyForSharePoint

SafeExit:
    EndQueueSafeAction resumeWhenDone
    Exit Sub

ErrHandler:
    MsgBox "Save SharePoint copy failed." & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbExclamation, "Save Error"
    Resume SafeExit
End Sub

'------------------------------------------------------------------------------
' Procedure: RunSyncDeliveryListToScannerSheetsSafe
' Scope: Public Sub
'
' What it does:
'   Finds, creates, deletes, rebuilds, protects, or synchronizes worksheets
'   for RunSyncDeliveryListToScannerSheetsSafe.
'
' Why it exists:
'   The master workbook creates multiple operational views from one delivery
'   list; worksheet helpers keep those views from drifting apart.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub RunSyncDeliveryListToScannerSheetsSafe()
    Dim resumeWhenDone As Boolean

    On Error GoTo ErrHandler
    If Not BeginQueueSafeAction("Refreshing scanner sheets", resumeWhenDone) Then Exit Sub

    SyncDeliveryListToScannerSheets True, False

SafeExit:
    EndQueueSafeAction resumeWhenDone
    Exit Sub

ErrHandler:
    MsgBox "Refresh scanner sheets failed." & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbExclamation, "Sync Error"
    Resume SafeExit
End Sub

'------------------------------------------------------------------------------
' Procedure: RunManualScanFromUtilityPanelSafe
' Scope: Public Sub
'
' What it does:
'   Builds, formats, deletes, or wires workbook UI shapes/buttons/panels for
'   RunManualScanFromUtilityPanelSafe.
'
' Why it exists:
'   Buttons and utility panels are the operator-facing control surface, so
'   they must be rebuilt consistently after imports or sheet refreshes.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub RunManualScanFromUtilityPanelSafe()
    Dim resumeWhenDone As Boolean

    On Error GoTo ErrHandler

    If Not BeginQueueSafeAction("Manual scan entry", resumeWhenDone) Then Exit Sub

    mManualScanFormPausedQueue = resumeWhenDone
    ManualScanFromUtilityPanel
    Exit Sub

ErrHandler:
    MsgBox "Manual scan failed." & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbExclamation, "Manual Scan Error"

    If mManualScanFormPausedQueue Then
        ResumeExternalQueue
        RefreshHomeMenuPreserveActiveSheet "Delivery List"
        mManualScanFormPausedQueue = False
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: ResumeQueueAfterManualScanForm
' Scope: Public Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   ResumeQueueAfterManualScanForm.
'
' Why it exists:
'   Remakes need separate visual and print/export handling so replacement
'   glass is not confused with regular delivery-list work.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub ResumeQueueAfterManualScanForm()
    If mManualScanFormPausedQueue Then
        ResumeExternalQueue
        RefreshHomeMenuPreserveActiveSheet "Delivery List"
        mManualScanFormPausedQueue = False
    End If
End Sub
'------------------------------------------------------------------------------
' Procedure: RunOpenDeliveryListForEditingSafe
'
' Opens Delivery List manual edit mode and keeps queue state honest.
'
' Important:
'   Manual edit mode is not treated like Import/Update.
'   Import/Update pauses temporarily and then resumes.
'   Manual edit mode pauses and stays paused until the user manually resumes.
'------------------------------------------------------------------------------
Public Sub RunOpenDeliveryListForEditingSafe()
    Dim alreadyPaused As Boolean

    On Error GoTo ErrHandler

    alreadyPaused = mQueuePaused

    If Not alreadyPaused Then
        If Not PauseExternalQueue("Delivery List edit mode") Then Exit Sub
    End If

    OpenDeliveryListForEditing

    'If the user clicked No on the edit confirmation, OpenDeliveryListForEditing
    'does not create _DeliveryEditMode. In that case, undo the pause we created.
    If Not DeliveryListEditModeIsActive() Then
        If Not alreadyPaused Then
            ResumeExternalQueue
            RefreshHomeMenuPreserveActiveSheet "Delivery List"
        End If

        Application.StatusBar = False
        Exit Sub
    End If

    'Keep the queue visibly paused while the user edits.
    ForceExternalQueuePausedForManualEdit "Delivery List edit mode"

    Application.StatusBar = "Queue paused for Delivery List edit mode. Finish edits, then click QUEUE PAUSED to resume scan processing."

    Exit Sub

ErrHandler:
    If Not alreadyPaused Then
        On Error Resume Next
        ResumeExternalQueue
        RefreshHomeMenuPreserveActiveSheet "Delivery List"
        On Error GoTo 0
    End If

    MsgBox "Could not open edit mode." & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbExclamation, "Edit Mode Error"
End Sub

'------------------------------------------------------------------------------
' Procedure: IsQueueActuallyRunning
' Scope: Private Function
'
' What it does:
'   Handles queue/request state used by the shared ScanQueue workflow for
'   IsQueueActuallyRunning.
'
' Why it exists:
'   Queue state must be tracked carefully so buffered intake scans, master
'   processing, retries, and final results stay aligned.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function IsQueueActuallyRunning() As Boolean
    IsQueueActuallyRunning = ((mProcessorScheduled Or mHeartbeatScheduled Or mProcessorRunning) And Not mQueuePaused)
End Function

'------------------------------------------------------------------------------
' Procedure: ToggleQueueMaintenanceMode
' Scope: Public Sub
'
' What it does:
'   Handles queue/request state used by the shared ScanQueue workflow for
'   ToggleQueueMaintenanceMode.
'
' Why it exists:
'   Queue state must be tracked carefully so buffered intake scans, master
'   processing, retries, and final results stay aligned.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub ToggleQueueMaintenanceMode()
    On Error GoTo ErrHandler

    If IsQueueActuallyRunning() Then
        If PauseExternalQueue("Manual maintenance") Then
            CreateOrRefreshHomeMenu
            Application.StatusBar = "Queue processing paused. Intake stations can keep queueing scans."
        End If
    Else
        ResumeExternalQueue
        CreateOrRefreshHomeMenu
        Application.StatusBar = "Queue processing resumed."
    End If

    Exit Sub

ErrHandler:
    MsgBox "Queue toggle failed." & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbExclamation, "Queue Error"
End Sub

'------------------------------------------------------------------------------
' Procedure: UpdateMasterHeartbeatStatus
' Scope: Private Sub
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   UpdateMasterHeartbeatStatus.
'
' Why it exists:
'   Delivery timing, queue timestamps, and scan timestamps drive status
'   messages such as Early, On-Time, Late, Processing, and Done.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub UpdateMasterHeartbeatStatus(ByVal statusText As String)
    Dim listDt As Date

    listDt = ResolveDeliveryListDate()

    Call PA_ActiveUpsertHeartbeat( _
            GetCurrentDeliveryListKey(), _
            GetCurrentDeliveryListDisplay(), _
            listDt, _
            statusText, _
            ThisWorkbook.Name, _
            GetMasterSessionId(), _
            GetMachineNameText(), _
            GetCurrentDeliveryListRevisionToken(), _
            GetCurrentDeliveryListRevisionUpdatedAt())
End Sub

'------------------------------------------------------------------------------
' Procedure: ExternalQueueItemLooksProcessable
' Scope: Private Function
'
' What it does:
'   Handles queue/request state used by the shared ScanQueue workflow for
'   ExternalQueueItemLooksProcessable.
'
' Why it exists:
'   Queue state must be tracked carefully so buffered intake scans, master
'   processing, retries, and final results stay aligned.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function ExternalQueueItemLooksProcessable(ByVal item As Object) As Boolean
    Dim reqType As String
    Dim modeText As String
    Dim targetSheet As String

    reqType = UCase$(Trim$(PA_DictText(item, "requestType")))
    modeText = UCase$(Trim$(PA_DictText(item, "mode")))
    targetSheet = Trim$(PA_DictText(item, "targetSheet"))

    If Len(reqType) = 0 Then Exit Function

    Select Case reqType
        Case "BARCODE", "MANUAL", "COMMENT"
            If Len(modeText) = 0 Then Exit Function
            If modeText <> "SEND" And modeText <> "RECV" And modeText <> "STAGING" Then Exit Function
            ExternalQueueItemLooksProcessable = True

        Case "SNAPSHOT"
            If Len(modeText) = 0 Then Exit Function
            If modeText <> "SEND" And modeText <> "RECV" And modeText <> "STAGING" Then Exit Function
            If Len(targetSheet) = 0 Then Exit Function
            ExternalQueueItemLooksProcessable = True

        Case Else
            ExternalQueueItemLooksProcessable = False
    End Select
End Function

'------------------------------------------------------------------------------
' Procedure: ExternalQueueItemIsStale
' Scope: Private Function
'
' What it does:
'   Handles queue/request state used by the shared ScanQueue workflow for
'   ExternalQueueItemIsStale.
'
' Why it exists:
'   Queue state must be tracked carefully so buffered intake scans, master
'   processing, retries, and final results stay aligned.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function ExternalQueueItemIsStale(ByVal item As Object) As Boolean
    Dim statusText As String
    Dim stampText As String
    Dim stampVal As Date

    statusText = UCase$(Trim$(PA_DictText(item, "status")))
    If statusText <> "PROCESSING" Then Exit Function

    stampText = PA_DictText(item, "processedAt")
    If Len(stampText) = 0 Then
        ExternalQueueItemIsStale = True
        Exit Function
    End If

    stampVal = PA_ParseIsoDate(stampText)
    If stampVal <= 0 Then
        ExternalQueueItemIsStale = True
        Exit Function
    End If

    If DateDiff("n", stampVal, Now) >= STALE_PROCESSING_MINUTES Then
        ExternalQueueItemIsStale = True
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: ProcessExternalQueuedScans
' Scope: Public Sub
'
' What it does:
'   Handles queue/request state used by the shared ScanQueue workflow for
'   ProcessExternalQueuedScans.
'
' Why it exists:
'   Queue state must be tracked carefully so buffered intake scans, master
'   processing, retries, and final results stay aligned.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub ProcessExternalQueuedScans()
    Dim items As Collection
    Dim item As Object
    Dim processedAny As Boolean
    Dim rowsHandled As Long
    Dim statusText As String
    Dim uiFreezeReleased As Boolean
    Dim duplicateMessage As String

    Dim stepText As String
    Dim currentItemId As Long
    Dim currentRequestId As String
    Dim errNum As Long
    Dim errDesc As String

    Dim markedProcessing As Boolean
    Dim failedCycleCount As Long

    On Error GoTo ErrHandler

    If mQueuePaused Then Exit Sub

    If BlockingDuplicateMasterExists(duplicateMessage) Then
        CancelExternalQueueSchedules

        mQueuePaused = True
        mQueuePauseReason = "Duplicate master blocked"
        mProcessorRunning = False
        mDuplicateMasterWarningShown = True

        On Error Resume Next
        UpdateMasterHeartbeatStatus "Paused"
        On Error GoTo ErrHandler

        MasterQueueNotice _
            "Duplicate Master Blocked", _
            Replace(duplicateMessage, vbCrLf & vbCrLf, vbCrLf), _
            vbExclamation

        Exit Sub
    End If

    stepText = "BeginMasterQueueUiFreeze"
    BeginMasterQueueUiFreeze "Processing queued scans..."

    stepText = "PA_QueueGetPending"
    Set items = PA_QueueGetPending(GetCurrentDeliveryListKey(), MAX_QUEUE_ROWS_PER_CYCLE)

    For Each item In items
        currentItemId = 0
        currentRequestId = vbNullString
        markedProcessing = False

        On Error Resume Next
        currentItemId = CLng(item("id"))
        currentRequestId = PA_DictText(item, "requestId")
        On Error GoTo ErrHandler

        statusText = UCase$(Trim$(PA_DictText(item, "status")))

        If statusText = "QUEUED" Or ExternalQueueItemIsStale(item) Then
            If Not ExternalQueueItemLooksProcessable(item) Then
                stepText = "QueueUpdate malformed item " & currentItemId

                If Not QueueUpdateStatusWithRetry( _
                        currentItemId, _
                        "Error", _
                        "ERROR", _
                        "Malformed queue row for this delivery list.", _
                        QUEUE_UPDATE_RETRY_ATTEMPTS) Then

                    failedCycleCount = IncrementQueueUpdateFailureCycle(currentItemId)

                    If failedCycleCount >= QUEUE_UPDATE_MAX_FAILED_CYCLES Then
                        If Not FailQueueItemAfterRepeatedStatusFailures(currentItemId, currentRequestId, failedCycleCount) Then
                            GoTo SafeExit
                        End If
                    End If
                Else
                    ResetQueueUpdateFailureCycle currentItemId
                End If

            Else
                If statusText = "PROCESSING" Then
                    stepText = "QueueUpdate stale item " & currentItemId

                    markedProcessing = QueueUpdateStatusWithRetry( _
                                            currentItemId, _
                                            "Processing", _
                                            "PROCESSING", _
                                            "Reprocessing stale row", _
                                            QUEUE_UPDATE_RETRY_ATTEMPTS)
                Else
                    stepText = "QueueUpdate processing item " & currentItemId

                    markedProcessing = QueueUpdateStatusWithRetry( _
                                            currentItemId, _
                                            "Processing", _
                                            "PROCESSING", _
                                            "Processing", _
                                            QUEUE_UPDATE_RETRY_ATTEMPTS)
                End If

                If Not markedProcessing Then
                    failedCycleCount = IncrementQueueUpdateFailureCycle(currentItemId)

                    If failedCycleCount >= QUEUE_UPDATE_MAX_FAILED_CYCLES Then
                        If Not FailQueueItemAfterRepeatedStatusFailures(currentItemId, currentRequestId, failedCycleCount) Then
                            GoTo SafeExit
                        End If
                    Else
                        MasterQueueNotice _
                            "Queue Item Skipped", _
                            "ScanQueue item " & currentItemId & " could not be marked Processing." & vbCrLf & _
                            "Failure cycle " & failedCycleCount & " of " & QUEUE_UPDATE_MAX_FAILED_CYCLES & "." & vbCrLf & _
                            "It will be retried on the next queue cycle.", _
                            vbExclamation
                    End If

                Else
                    ResetQueueUpdateFailureCycle currentItemId

                    stepText = "ProcessOneExternalQueueItem " & currentItemId
                    ProcessOneExternalQueueItem item

                    processedAny = True
                    rowsHandled = rowsHandled + 1

                    If rowsHandled >= MAX_QUEUE_ROWS_PER_CYCLE Then Exit For
                End If
            End If
        End If

        If mQueuePaused Then GoTo SafeExit
    Next item

    If processedAny Then
    EndMasterQueueUiFreeze
    uiFreezeReleased = True

    stepText = "SyncDeliveryListToScannerSheets"

    On Error Resume Next
    SyncDeliveryListToScannerSheets False, True

    If Err.Number <> 0 Then
        MasterQueueNotice "Scanner Sheet Refresh Error", _
            "Queued scans were processed, but scanner-sheet refresh failed." & vbCrLf & vbCrLf & _
            "Error " & Err.Number & ": " & Err.Description, _
            vbExclamation
        Err.Clear
    End If

    stepText = "PublishAllStageSnapshots"

    PublishAllStageSnapshots False, False

    If Err.Number <> 0 Then
        MasterQueueNotice "Snapshot Publish Error", _
            "Queued scans were processed, but intake snapshot publishing failed." & vbCrLf & vbCrLf & _
            "Error " & Err.Number & ": " & Err.Description, _
            vbExclamation
        Err.Clear
    End If

    On Error GoTo ErrHandler
End If

SafeExit:
    If Not uiFreezeReleased Then
        EndMasterQueueUiFreeze
    End If

    Exit Sub

ErrHandler:
    errNum = Err.Number
    errDesc = Err.Description

    If Not uiFreezeReleased Then
        EndMasterQueueUiFreeze
    End If

    If currentItemId > 0 Then
        If Not QueueUpdateStatusWithRetry( _
                currentItemId, _
                "Error", _
                "ERROR", _
                "Queue processor failed at step [" & stepText & "] - Error " & errNum & ": " & errDesc, _
                5) Then

            PauseQueueBecauseQueueStatusCannotBeWritten _
                currentItemId, _
                currentRequestId, _
                "The master hit an error and could not write the Error result back to ScanQueue." & vbCrLf & _
                "Step: " & stepText & vbCrLf & _
                "Error " & errNum & ": " & errDesc
        End If
    End If

    MasterQueueNotice "Queue Processor Error", _
        "Power Automate queue processing failed." & vbCrLf & vbCrLf & _
        "Step: " & stepText & vbCrLf & _
        "ItemId: " & currentItemId & vbCrLf & _
        "RequestId: " & currentRequestId & vbCrLf & vbCrLf & _
        "Error " & errNum & ": " & errDesc, _
        vbExclamation

    Resume SafeExit
End Sub

'------------------------------------------------------------------------------
' Procedure: ProcessOneExternalQueueItem
' Scope: Private Sub
'
' What it does:
'   Handles queue/request state used by the shared ScanQueue workflow for
'   ProcessOneExternalQueueItem.
'
' Why it exists:
'   Queue state must be tracked carefully so buffered intake scans, master
'   processing, retries, and final results stay aligned.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ProcessOneExternalQueueItem(ByVal item As Object)
    Dim reqType As String
    Dim modeText As String
    Dim barcodeText As String
    Dim ord As Long
    Dim itm As Long
    Dim qty As Long
    Dim itemId As Long
    Dim dataWs As Worksheet
    Dim ok As Boolean
    Dim resultCode As String
    Dim resultMessage As String
    Dim requestComment As String
    Dim stationName As String
    Dim oldSuppressProcessPopups As Boolean
    Dim oldSuppressManualPopups As Boolean
    Dim stepText As String
    Dim errNum As Long
    Dim errDesc As String
    Dim sourceScanTime As Date

    On Error GoTo ErrHandler

    Set dataWs = ThisWorkbook.Worksheets("Delivery List")

    itemId = CLng(item("id"))
    reqType = UCase$(Trim$(PA_DictText(item, "requestType")))
    modeText = UCase$(Trim$(PA_DictText(item, "mode")))
    stationName = Trim$(PA_DictText(item, "stationName"))
    requestComment = GetQueueItemRequestComment(item)
    sourceScanTime = QueueItemScanDateTime(item)

    oldSuppressProcessPopups = SuppressProcessScanPopups
    oldSuppressManualPopups = SuppressManualScanPopups

    SuppressProcessScanPopups = True
    SuppressManualScanPopups = True

    stepText = "Start"

    If reqType = "BARCODE" Then
    stepText = "Read barcode"
    barcodeText = Trim$(PA_DictText(item, "barcode"))

    If Len(barcodeText) = 0 Then
        resultCode = "ERROR"
        resultMessage = "Queue barcode was blank after master parsing. " & _
                        "OrderNumber=" & PA_DictText(item, "orderNumber") & _
                        ", ItemNumber=" & PA_DictText(item, "itemNumber") & _
                        ", RequestId=" & PA_DictText(item, "requestId") & "."
        GoTo FinalQueueUpdate
    End If

    stepText = "Detect queue override"
    ScannerValidation.AllowQueuedReceiveOverride = IsReceiveOverrideRequestComment(requestComment)
    ScannerValidation.QueuedReceiveOverrideReason = IIf(ScannerValidation.AllowQueuedReceiveOverride, _
                                                        "Receive override approved from intake station " & stationName, _
                                                        vbNullString)

    ScannerValidation.AllowQueuedSendOverride = IsSendOverrideRequestComment(requestComment)
    ScannerValidation.QueuedSendOverrideReason = IIf(ScannerValidation.AllowQueuedSendOverride, _
                                                     "Outbound staging override approved from intake station " & stationName, _
                                                     vbNullString)

    requestComment = StripQueueOverrideFlags(requestComment)

    stepText = "ScannerValidation.ProcessScan"
    ScannerValidation.ProcessScan dataWs, barcodeText, modeText, sourceScanTime
    ok = ScannerValidation.LastScanSuccess

    ScannerValidation.AllowQueuedReceiveOverride = False
    ScannerValidation.QueuedReceiveOverrideReason = vbNullString
    ScannerValidation.AllowQueuedSendOverride = False
    ScannerValidation.QueuedSendOverrideReason = vbNullString
    

    If ok Then
        resultCode = "OK"
        resultMessage = ScannerValidation.LastScanStatus
        
                stepText = "Indian Trail bay assignment barcode"
        Call IndianTrailHandleBayAssignmentForQueueItem( _
                dataWs, _
                modeText, _
                PA_DictText(item, "targetSheet"), _
                ScannerValidation.LastScanOrder, _
                ScannerValidation.LastScanItem, _
                barcodeText, _
                stationName, _
                resultMessage)

        If Len(requestComment) > 0 Then
            stepText = "AppendExternalScanComment barcode"
            AppendExternalScanComment dataWs, modeText, ScannerValidation.LastScanOrder, ScannerValidation.LastScanItem, requestComment, stationName
        End If
    Else
        resultCode = "ERROR"
        resultMessage = IIf(Len(ScannerValidation.LastScanStatus) > 0, ScannerValidation.LastScanStatus, "Processor rejected scan.")
    End If

    ElseIf reqType = "MANUAL" Then
    stepText = "Read manual payload"

    ord = CLng(Val(PA_DictText(item, "orderNumber")))
    itm = CLng(Val(PA_DictText(item, "itemNumber")))
    qty = CLng(Val(PA_DictText(item, "quantity")))

    If qty < 1 Then qty = 1

    stepText = "Validate manual request"

    If Not ValidateManualQueueRequestBeforeApply(dataWs, modeText, ord, itm, qty, resultMessage) Then
        resultCode = "ERROR"
        GoTo FinalQueueUpdate
    End If

    stepText = "ApplyManualScanEntryTemplate"
    ok = ApplyManualScanEntryTemplate(modeText, ord, itm, qty, True, sourceScanTime)

    If ok Then
        resultCode = "OK"
        resultMessage = "Manual scan complete."

        stepText = "Indian Trail bay assignment manual"
        Call IndianTrailHandleBayAssignmentForQueueItem( _
                dataWs, _
                modeText, _
                PA_DictText(item, "targetSheet"), _
                ord, _
                itm, _
                vbNullString, _
                stationName, _
                resultMessage)

        Dim manualUserComment As String

manualUserComment = BuildManualExternalComment(requestComment)

If Len(manualUserComment) > 0 Then
    stepText = "AppendExternalScanComment manual"
    AppendExternalScanComment dataWs, modeText, ord, itm, manualUserComment, stationName, False
End If
    Else
        resultCode = "ERROR"
        resultMessage = "Manual scan could not be applied. The master rejected the manual request, but did not return a detailed reason. Check the order/item quantity columns on the master."
    End If
    ElseIf reqType = "COMMENT" Then
    stepText = "Read comment payload"
    ord = CLng(Val(PA_DictText(item, "orderNumber")))
    itm = CLng(Val(PA_DictText(item, "itemNumber")))
    requestComment = CStr(PA_DictText(item, "requestComment"))

    ScannerValidation.AllowQueuedReceiveOverride = IsReceiveOverrideRequestComment(requestComment)
    ScannerValidation.QueuedReceiveOverrideReason = IIf(ScannerValidation.AllowQueuedReceiveOverride, _
                                                "Override approved from intake station " & stationName, _
                                                vbNullString)

    requestComment = StripReceiveOverrideFlag(requestComment)

    If ord < 1 Or itm < 1 Then
        resultCode = "ERROR"
        resultMessage = "Comment sync missing order/item."

    ElseIf InStr(1, requestComment, COMMENT_SET_PREFIX, vbTextCompare) = 1 Then
        stepText = "SetExternalScanCommentExact"

        If SetExternalScanCommentExact( _
                dataWs, _
                modeText, _
                ord, _
                itm, _
                Mid$(requestComment, Len(COMMENT_SET_PREFIX) + 1)) Then

            resultCode = "OK"

            If Len(Trim$(Mid$(requestComment, Len(COMMENT_SET_PREFIX) + 1))) = 0 Then
                resultMessage = "Comment cleared."
            Else
                resultMessage = "Comment saved."
            End If
        Else
            resultCode = "ERROR"
            resultMessage = "Comment sync could not find the order/item row."
        End If

    ElseIf Len(Trim$(requestComment)) = 0 Then
        resultCode = "ERROR"
        resultMessage = "Comment sync text was blank."

    Else
        'Legacy fallback for any old COMMENT rows that were already queued
        'before the exact-set comment system was added.
        stepText = "AppendExternalScanComment comment"
        AppendExternalScanComment dataWs, modeText, ord, itm, CleanExternalQueueCommentText(requestComment), stationName, False
        resultCode = "OK"
        resultMessage = "Comment synced."
        End If
    
    ElseIf reqType = "SNAPSHOT" Then
    Dim requestedStageProfile As String
    Dim requestedStageKey As String
    Dim expectedStageKey As String
    Dim publishReason As String

    stepText = "Read snapshot request"

    requestedStageProfile = Trim$(PA_DictText(item, "targetSheet"))
    requestedStageKey = Trim$(PA_DictText(item, "requestComment"))
    expectedStageKey = SnapshotStageKeyFromProfilePublic(requestedStageProfile)

    If Len(requestedStageProfile) = 0 Then
        resultCode = "ERROR"
        resultMessage = "Snapshot request missing target sheet/stage."

    ElseIf Len(expectedStageKey) = 0 Then
        resultCode = "ERROR"
        resultMessage = "Unsupported snapshot stage requested: " & requestedStageProfile

    ElseIf Len(requestedStageKey) > 0 And StrComp(requestedStageKey, expectedStageKey, vbTextCompare) <> 0 Then
        resultCode = "ERROR"
        resultMessage = "Snapshot request stage mismatch. TargetSheet=" & requestedStageProfile & _
                        ", RequestComment stageKey=" & requestedStageKey & _
                        ", Expected stageKey=" & expectedStageKey & "."

    Else
        stepText = "Publish requested stage snapshot"

        If PublishStageSnapshot(requestedStageProfile, False, publishReason) Then
            resultCode = "OK"
            resultMessage = "Snapshot published for " & requestedStageProfile & _
                            ". Revision: " & GetCurrentDeliveryListRevisionToken()
        Else
            resultCode = "ERROR"

            If Len(Trim$(publishReason)) > 0 Then
                resultMessage = publishReason
            Else
                resultMessage = "Master could not publish snapshot for " & requestedStageProfile & "."
            End If
        End If
    End If
    
    Else
        resultCode = "ERROR"
        resultMessage = "Unknown request type: " & reqType
    End If

FinalQueueUpdate:
    stepText = "PA_QueueUpdateStatus final"
    If QueueUpdateStatusWithRetry(itemId, IIf(resultCode = "OK", "Done", "Error"), resultCode, resultMessage, 5) Then
    ResetQueueUpdateFailureCycle itemId
Else
    PauseQueueBecauseQueueStatusCannotBeWritten _
        itemId, _
        PA_DictText(item, "requestId"), _
        "The master processed this scan but could not write the final status back to ScanQueue." & vbCrLf & _
        "Result was: " & IIf(resultCode = "OK", "Done", "Error") & " / " & resultCode & vbCrLf & _
        "The queue was paused to prevent duplicate processing."
End If

SafeExit:
    SuppressProcessScanPopups = oldSuppressProcessPopups
    SuppressManualScanPopups = oldSuppressManualPopups
    ScannerValidation.AllowQueuedReceiveOverride = False
    ScannerValidation.QueuedReceiveOverrideReason = vbNullString
    ScannerValidation.AllowQueuedSendOverride = False
    ScannerValidation.QueuedSendOverrideReason = vbNullString
    Exit Sub

ErrHandler:
    errNum = Err.Number
    errDesc = Err.Description
    
    ScannerValidation.AllowQueuedReceiveOverride = False
    ScannerValidation.QueuedReceiveOverrideReason = vbNullString
    ScannerValidation.AllowQueuedSendOverride = False
    ScannerValidation.QueuedSendOverrideReason = vbNullString
    
    SuppressProcessScanPopups = oldSuppressProcessPopups
    SuppressManualScanPopups = oldSuppressManualPopups

On Error Resume Next

If Not QueueUpdateStatusWithRetry( _
        itemId, _
        "Error", _
        "ERROR", _
        "Processor step failed [" & stepText & "] - Error " & errNum & ": " & errDesc, _
        5) Then

    PauseQueueBecauseQueueStatusCannotBeWritten _
        itemId, _
        PA_DictText(item, "requestId"), _
        "The master could not write the processor error back to ScanQueue." & vbCrLf & _
        "Step: " & stepText & vbCrLf & _
        "Error " & errNum & ": " & errDesc
End If

On Error GoTo 0

    Resume SafeExit
End Sub

Private Function SetExternalScanCommentExact(ByVal dataWs As Worksheet, _
                                             ByVal mode As String, _
                                             ByVal ord As Long, _
                                             ByVal itm As Long, _
                                             ByVal fullCommentText As String) As Boolean
    Const SEND_COMMENTS_COL As Long = 23      'W
    Const RECV_COMMENTS_COL As Long = 32      'AF
    Const STAGING_COMMENTS_COL As Long = 48   'AV

    Dim rowNum As Long
    Dim commentCol As Long
    Dim cleanedComment As String

    If dataWs Is Nothing Then Exit Function
    If ord < 1 Or itm < 1 Then Exit Function

    rowNum = FindExternalQueueMatchRow(dataWs, ord, itm)
    If rowNum = 0 Then Exit Function

    Select Case UCase$(Trim$(mode))
        Case "SEND"
            commentCol = SEND_COMMENTS_COL

        Case "RECV"
            commentCol = RECV_COMMENTS_COL

        Case "STAGING"
            commentCol = STAGING_COMMENTS_COL

        Case Else
            Exit Function
    End Select

    cleanedComment = CleanExternalQueueCommentText(fullCommentText)

    With dataWs.Cells(rowNum, commentCol)
        If Len(cleanedComment) = 0 Then
            .ClearContents
        Else
            .Value = cleanedComment
        End If

        .WrapText = False
        .ShrinkToFit = False
        .VerticalAlignment = xlCenter
    End With

    On Error Resume Next
    dataWs.Columns(commentCol).AutoFit
    If dataWs.Columns(commentCol).ColumnWidth < 18 Then dataWs.Columns(commentCol).ColumnWidth = 18
    If dataWs.Columns(commentCol).ColumnWidth > 80 Then dataWs.Columns(commentCol).ColumnWidth = 80
    On Error GoTo 0

    SetExternalScanCommentExact = True
End Function

'------------------------------------------------------------------------------
' Procedure: CleanExternalQueueCommentText
' Scope: Private Function
'
' What it does:
'   Handles queue/request state used by the shared ScanQueue workflow for
'   CleanExternalQueueCommentText.
'
' Why it exists:
'   Queue state must be tracked carefully so buffered intake scans, master
'   processing, retries, and final results stay aligned.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function CleanExternalQueueCommentText(ByVal commentText As String) As String
    commentText = Trim$(CStr(commentText))

    commentText = Replace$(commentText, vbCrLf, " ")
    commentText = Replace$(commentText, vbCr, " ")
    commentText = Replace$(commentText, vbLf, " ")
    commentText = Replace$(commentText, vbTab, " ")

    Do While InStr(1, commentText, "  ", vbBinaryCompare) > 0
        commentText = Replace$(commentText, "  ", " ")
    Loop

    CleanExternalQueueCommentText = Trim$(commentText)
End Function

'------------------------------------------------------------------------------
' Procedure: GetQueueItemRequestComment
' Scope: Private Function
'
' What it does:
'   Handles queue/request state used by the shared ScanQueue workflow for
'   GetQueueItemRequestComment.
'
' Why it exists:
'   Queue state must be tracked carefully so buffered intake scans, master
'   processing, retries, and final results stay aligned.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetQueueItemRequestComment(ByVal item As Object) As String
    Dim requestComment As String
    Dim requestId As String
    Dim statusItem As Object

    If item Is Nothing Then Exit Function

    requestComment = Trim$(PA_DictText(item, "requestComment"))

    If Len(requestComment) > 0 Then
        GetQueueItemRequestComment = requestComment
        Exit Function
    End If

    requestId = Trim$(PA_DictText(item, "requestId"))
    If Len(requestId) = 0 Then Exit Function

    On Error Resume Next
    Set statusItem = PA_QueueGetRequestStatus(requestId)
    On Error GoTo 0

    If Not statusItem Is Nothing Then
        requestComment = Trim$(PA_DictText(statusItem, "requestComment"))
    End If

    GetQueueItemRequestComment = requestComment
End Function

'------------------------------------------------------------------------------
' Procedure: BuildManualExternalComment
' Scope: Private Function
'
' What it does:
'   Builds a derived value, key, JSON block, layout, collection, or workbook
'   object used later by the workflow (BuildManualExternalComment).
'
' Why it exists:
'   The project uses generated keys/layouts to keep repeated logic consistent
'   instead of hand-building values in multiple places.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BuildManualExternalComment(ByVal requestComment As String) As String
    requestComment = Trim$(CStr(requestComment))

    requestComment = Replace$(requestComment, vbCrLf, " ")
    requestComment = Replace$(requestComment, vbCr, " ")
    requestComment = Replace$(requestComment, vbLf, " ")
    requestComment = Replace$(requestComment, vbTab, " ")

    Do While InStr(1, requestComment, "  ", vbBinaryCompare) > 0
        requestComment = Replace$(requestComment, "  ", " ")
    Loop

    requestComment = Trim$(requestComment)

    'No user-entered comment means do not add anything extra.
    If Len(requestComment) = 0 Then Exit Function

    'Do not add generic system/manual words into the comments column.
    If UCase$(requestComment) = "MANUAL" Then Exit Function
    If UCase$(requestComment) = "MANUAL SCAN" Then Exit Function
    If UCase$(requestComment) = "MANUAL SCAN ENTERED" Then Exit Function

    'Cleanup for older queued rows that used the old wording.
    If InStr(1, requestComment, "Manual scan entered from Scanning Panel |", vbTextCompare) = 1 Then
        requestComment = Replace$(requestComment, "Manual scan entered from Scanning Panel |", vbNullString, 1, 1, vbTextCompare)
        requestComment = Trim$(requestComment)

    ElseIf InStr(1, requestComment, "Manual scan entered from Scanning Panel", vbTextCompare) = 1 Then
        requestComment = Replace$(requestComment, "Manual scan entered from Scanning Panel", vbNullString, 1, 1, vbTextCompare)
        requestComment = Trim$(requestComment)
    End If

    If Len(requestComment) = 0 Then Exit Function
    If UCase$(requestComment) = "MANUAL" Then Exit Function

    'If user already typed "Manual: ...", keep it.
    If InStr(1, requestComment, "Manual:", vbTextCompare) = 1 Then
        BuildManualExternalComment = requestComment
    Else
        BuildManualExternalComment = "Manual: " & requestComment
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: AppendExternalScanComment
' Scope: Private Sub
'
' What it does:
'   Appends text or state to an existing cell/message for
'   AppendExternalScanComment.
'
' Why it exists:
'   Append helpers preserve prior context while adding audit or override
'   information for the operator.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub AppendExternalScanComment(ByVal dataWs As Worksheet, _
                                      ByVal mode As String, _
                                      ByVal ord As Long, _
                                      ByVal itm As Long, _
                                      ByVal commentText As String, _
                                      ByVal stationName As String, _
                                      Optional ByVal addPrefix As Boolean = True)
    Const SEND_COMMENTS_COL As Long = 23
    Const RECV_COMMENTS_COL As Long = 32
    Const STAGING_COMMENTS_COL As Long = 48

    Dim rowNum As Long
    Dim commentCol As Long
    Dim prefixText As String
    Dim finalComment As String

    commentText = Trim$(CStr(commentText))
    If Len(commentText) = 0 Then Exit Sub

    rowNum = FindExternalQueueMatchRow(dataWs, ord, itm)
    If rowNum = 0 Then Exit Sub

    Select Case UCase$(Trim$(mode))
        Case "SEND"
            commentCol = SEND_COMMENTS_COL

        Case "RECV"
            commentCol = RECV_COMMENTS_COL

        Case "STAGING"
            commentCol = STAGING_COMMENTS_COL

        Case Else
            Exit Sub
    End Select

    If addPrefix Then
        prefixText = Format$(Now, "m/d/yyyy h:mm AM/PM")

        If Len(Trim$(stationName)) > 0 Then
            prefixText = prefixText & " - " & Trim$(stationName)
        End If

        prefixText = prefixText & ": "
        finalComment = prefixText & commentText
    Else
        finalComment = commentText
    End If

    With dataWs.Cells(rowNum, commentCol)
        If Len(Trim$(CStr(.Value))) > 0 Then
            If InStr(1, CStr(.Value), finalComment, vbTextCompare) = 0 Then
                .Value = CStr(.Value) & " | " & finalComment
            End If
        Else
            .Value = finalComment
        End If

        .WrapText = False
        .ShrinkToFit = False
        .VerticalAlignment = xlCenter
    End With

    AutoFitMasterExternalCommentColumn dataWs, commentCol
End Sub

'------------------------------------------------------------------------------
' Procedure: AutoFitMasterExternalCommentColumn
' Scope: Private Sub
'
' What it does:
'   Finds, sizes, hides, formats, or uses worksheet columns for
'   AutoFitMasterExternalCommentColumn.
'
' Why it exists:
'   The system depends on fixed scan blocks and discovered delivery-list
'   columns, so column handling must be centralized and predictable.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub AutoFitMasterExternalCommentColumn(ByVal ws As Worksheet, ByVal commentCol As Long)
    Const MIN_WIDTH As Double = 18
    Const MAX_WIDTH As Double = 120

    Dim oldWidth As Double
    Dim newWidth As Double

    If ws Is Nothing Then Exit Sub
    If commentCol <= 0 Then Exit Sub

    On Error Resume Next

    oldWidth = ws.Columns(commentCol).ColumnWidth

    With ws.Columns(commentCol)
        .WrapText = False
        .ShrinkToFit = False
        .AutoFit
    End With

    newWidth = ws.Columns(commentCol).ColumnWidth

    If newWidth < MIN_WIDTH Then newWidth = MIN_WIDTH
    If newWidth > MAX_WIDTH Then newWidth = MAX_WIDTH
    If newWidth < oldWidth Then newWidth = oldWidth

    ws.Columns(commentCol).ColumnWidth = newWidth

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: FindExternalQueueMatchRow
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   FindExternalQueueMatchRow.
'
' Why it exists:
'   Rows may represent real orders, section headers, remakes, Greenville work,
'   Customer Pickup work, or updated rows; each type needs different handling.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function FindExternalQueueMatchRow(ByVal dataWs As Worksheet, ByVal ord As Long, ByVal itm As Long) As Long
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim hdrRow As Long
    Dim orderCol As Long
    Dim itemCol As Long
    Dim firstRow As Long
    Dim lastRow As Long

    Set orderHdr = FindExternalHeaderCellInCols(dataWs, Array("Order Nr."), "A:N", 250)
    Set itemHdr = FindExternalHeaderCellInCols(dataWs, Array("Item Nr.", "Item"), "A:N", 250)

    If orderHdr Is Nothing Or itemHdr Is Nothing Then Exit Function

    hdrRow = orderHdr.Row
    orderCol = orderHdr.Column
    itemCol = itemHdr.Column

    firstRow = hdrRow + 1
    lastRow = dataWs.Cells(dataWs.rows.Count, orderCol).End(xlUp).Row

    If lastRow < firstRow Then Exit Function

    FindExternalQueueMatchRow = FindExternalRowByOrderItem(dataWs, ord, itm, orderCol, itemCol, firstRow, lastRow)
End Function
Private Function ValidateManualQueueRequestBeforeApply(ByVal dataWs As Worksheet, _
                                                       ByVal modeText As String, _
                                                       ByVal ord As Long, _
                                                       ByVal itm As Long, _
                                                       ByVal qtyToAdd As Long, _
                                                       ByRef resultMessage As String) As Boolean
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim qtyHdr As Range
    Dim sendQtyHdr As Range
    Dim recvQtyHdr As Range
    Dim stagingQtyHdr As Range

    Dim orderCol As Long
    Dim itemCol As Long
    Dim firstRow As Long
    Dim lastRow As Long
    Dim rowNum As Long

    Dim requiredQty As Long
    Dim stagingQty As Long
    Dim sendQty As Long
    Dim recvQty As Long
    Dim nextSendQty As Long
    Dim nextRecvQty As Long
    Dim orderItemText As String

    ValidateManualQueueRequestBeforeApply = False
    resultMessage = vbNullString

    If dataWs Is Nothing Then
        resultMessage = "Manual scan blocked." & vbCrLf & _
                        "Master Delivery List sheet was not available."
        Exit Function
    End If

    modeText = UCase$(Trim$(CStr(modeText)))

    If ord <= 0 Or itm <= 0 Then
        resultMessage = "Manual scan blocked." & vbCrLf & _
                        "Missing order or item number."
        Exit Function
    End If

    If qtyToAdd < 1 Then qtyToAdd = 1

    orderItemText = "Order: " & ord & vbCrLf & _
                    "Item: " & Format$(itm, "000")

    Set orderHdr = FindExternalHeaderCellInCols(dataWs, Array("Order Nr."), "A:N", 250)
    Set itemHdr = FindExternalHeaderCellInCols(dataWs, Array("Item Nr.", "Item"), "A:N", 250)

    If orderHdr Is Nothing Or itemHdr Is Nothing Then
        resultMessage = "Manual scan blocked." & vbCrLf & _
                        "Master could not find Order/Item headers."
        Exit Function
    End If

    orderCol = orderHdr.Column
    itemCol = itemHdr.Column
    firstRow = orderHdr.Row + 1
    lastRow = dataWs.Cells(dataWs.rows.Count, orderCol).End(xlUp).Row

    rowNum = FindExternalRowByOrderItem(dataWs, ord, itm, orderCol, itemCol, firstRow, lastRow)

    If rowNum = 0 Then
        resultMessage = "Manual scan blocked." & vbCrLf & _
                        "Item not found on this delivery list." & vbCrLf & vbCrLf & _
                        orderItemText
        Exit Function
    End If

    requiredQty = 1

    Set qtyHdr = FindExternalHeaderCellInCols(dataWs, Array("Qty.", "Qty", "Quantity"), "A:N", 250)

    If Not qtyHdr Is Nothing Then
        If IsNumeric(dataWs.Cells(rowNum, qtyHdr.Column).Value) Then
            requiredQty = CLng(dataWs.Cells(rowNum, qtyHdr.Column).Value)
            If requiredQty < 1 Then requiredQty = 1
        End If
    End If

    Set sendQtyHdr = FindExternalHeaderCellInCols(dataWs, Array("Qty Scanned"), "P:W", 60)
    Set recvQtyHdr = FindExternalHeaderCellInCols(dataWs, Array("Qty Scanned"), "Y:AG", 60)
    Set stagingQtyHdr = FindExternalHeaderCellInCols(dataWs, Array("Qty Scanned"), "AP:AV", 60)

    If Not stagingQtyHdr Is Nothing Then stagingQty = CLng(Val(dataWs.Cells(rowNum, stagingQtyHdr.Column).Value))
    If Not sendQtyHdr Is Nothing Then sendQty = CLng(Val(dataWs.Cells(rowNum, sendQtyHdr.Column).Value))
    If Not recvQtyHdr Is Nothing Then recvQty = CLng(Val(dataWs.Cells(rowNum, recvQtyHdr.Column).Value))

    Select Case modeText
        Case "STAGING"
            If stagingQty >= requiredQty Then
                resultMessage = "Manual staging scan blocked." & vbCrLf & _
                                orderItemText & vbCrLf & _
                                "Already staged: " & stagingQty & "/" & requiredQty
                Exit Function
            End If

        Case "SEND"
            nextSendQty = sendQty + qtyToAdd

            If sendQty >= requiredQty Then
                resultMessage = "Manual outbound scan blocked." & vbCrLf & _
                                orderItemText & vbCrLf & _
                                "Already outbound: " & sendQty & "/" & requiredQty
                Exit Function
            End If

            If stagingQty < nextSendQty Then
                resultMessage = "Manual outbound scan blocked." & vbCrLf & _
                                orderItemText & vbCrLf & _
                                "Stage first." & vbCrLf & _
                                "Staged: " & stagingQty & "/" & requiredQty & vbCrLf & _
                                "Outbound: " & sendQty & "/" & requiredQty & vbCrLf & _
                                "Requested: " & qtyToAdd
                Exit Function
            End If

        Case "RECV"
            nextRecvQty = recvQty + qtyToAdd

            If sendQty <= 0 Then
                resultMessage = "Manual inbound scan blocked." & vbCrLf & _
                                orderItemText & vbCrLf & _
                                "Outbound has not been scanned yet." & vbCrLf & _
                                "Outbound: " & sendQty & "/" & requiredQty & vbCrLf & _
                                "Inbound: " & recvQty & "/" & requiredQty
                Exit Function
            End If

            If nextRecvQty > sendQty Then
                resultMessage = "Manual inbound scan blocked." & vbCrLf & _
                                orderItemText & vbCrLf & _
                                "Inbound would exceed outbound." & vbCrLf & _
                                "Outbound: " & sendQty & vbCrLf & _
                                "Inbound: " & recvQty & vbCrLf & _
                                "Requested: " & qtyToAdd
                Exit Function
            End If

        Case Else
            resultMessage = "Manual scan blocked." & vbCrLf & _
                            "Unsupported mode: " & modeText
            Exit Function
    End Select

    ValidateManualQueueRequestBeforeApply = True
End Function
'------------------------------------------------------------------------------
' Procedure: FindExternalHeaderCellInCols
' Scope: Private Function
'
' What it does:
'   Finds, writes, validates, or uses worksheet header cells for
'   FindExternalHeaderCellInCols.
'
' Why it exists:
'   Header locations can move during import/rebuild, so the code uses header
'   discovery to target the correct columns instead of guessing.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function FindExternalHeaderCellInCols(ByVal ws As Worksheet, ByVal headerNames As Variant, ByVal colRange As String, ByVal maxRows As Long) As Range
    Dim searchRange As Range
    Dim f As Range
    Dim nm As Variant

    Set searchRange = Intersect(ws.Range(colRange), ws.rows("1:" & maxRows))
    If searchRange Is Nothing Then Exit Function

    For Each nm In headerNames
        Set f = searchRange.Find(What:=CStr(nm), LookIn:=xlValues, LookAt:=xlWhole, MatchCase:=False)
        If Not f Is Nothing Then
            Set FindExternalHeaderCellInCols = f
            Exit Function
        End If
    Next nm
End Function

'------------------------------------------------------------------------------
' Procedure: FindExternalRowByOrderItem
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   FindExternalRowByOrderItem.
'
' Why it exists:
'   Rows may represent real orders, section headers, remakes, Greenville work,
'   Customer Pickup work, or updated rows; each type needs different handling.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function FindExternalRowByOrderItem(ByVal ws As Worksheet, ByVal orderNum As Long, ByVal itemNum As Long, ByVal orderCol As Long, ByVal itemCol As Long, ByVal firstRow As Long, ByVal lastRow As Long) As Long
    Dim rng As Range
    Dim f As Range
    Dim firstAddr As String

    Set rng = ws.Range(ws.Cells(firstRow, orderCol), ws.Cells(lastRow, orderCol))
    Set f = rng.Find(What:=CStr(orderNum), LookIn:=xlValues, LookAt:=xlWhole)

    If Not f Is Nothing Then
        firstAddr = f.Address
        Do
            If IsNumeric(ws.Cells(f.Row, itemCol).Value) Then
                If CLng(ws.Cells(f.Row, itemCol).Value) = itemNum Then
                    FindExternalRowByOrderItem = f.Row
                    Exit Function
                End If
            End If
            Set f = rng.FindNext(f)
        Loop While Not f Is Nothing And f.Address <> firstAddr
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: GetMasterDeliveryListDateText
' Scope: Public Function
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   GetMasterDeliveryListDateText.
'
' Why it exists:
'   Delivery timing, queue timestamps, and scan timestamps drive status
'   messages such as Early, On-Time, Late, Processing, and Done.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function GetMasterDeliveryListDateText() As String
    On Error Resume Next
    GetMasterDeliveryListDateText = Format$(GetDeliveryListDateForFileName(ThisWorkbook.Worksheets("Delivery List")), "m/d/yyyy")
    If Len(GetMasterDeliveryListDateText) = 0 Then GetMasterDeliveryListDateText = "Unknown"
    On Error GoTo 0
End Function

'------------------------------------------------------------------------------
' Procedure: RefreshHomeMenuPreserveActiveSheet
' Scope: Private Sub
'
' What it does:
'   Builds, formats, deletes, or wires workbook UI shapes/buttons/panels for
'   RefreshHomeMenuPreserveActiveSheet.
'
' Why it exists:
'   Buttons and utility panels are the operator-facing control surface, so
'   they must be rebuilt consistently after imports or sheet refreshes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub RefreshHomeMenuPreserveActiveSheet(Optional ByVal preferredSheetName As String = vbNullString)
    Dim restoreWs As Worksheet
    Dim restoreCell As Range

    On Error Resume Next

    If Len(preferredSheetName) > 0 Then
        Set restoreWs = ThisWorkbook.Worksheets(preferredSheetName)
    End If

    If restoreWs Is Nothing Then
        Set restoreWs = ActiveSheet
    End If

    If Not restoreWs Is Nothing Then
        Set restoreCell = restoreWs.Range("A1")
    End If

    CreateOrRefreshHomeMenu

    If Not restoreWs Is Nothing Then
        restoreWs.Activate
        If Not restoreCell Is Nothing Then
            Application.GoTo restoreCell, False
        End If
    End If

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: Test_QueueUpdateStatus_Processing
' Scope: Public Sub
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   Test_QueueUpdateStatus_Processing.
'
' Why it exists:
'   Delivery timing, queue timestamps, and scan timestamps drive status
'   messages such as Early, On-Time, Late, Processing, and Done.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub Test_QueueUpdateStatus_Processing()
    Dim ok As Boolean

    On Error GoTo ErrHandler

    ok = PA_QueueUpdateStatus(3, "Processing", "PROCESSING", "Processing")
    MsgBox "Processing update returned: " & CStr(ok), vbInformation, "Test"
    Exit Sub

ErrHandler:
    MsgBox "Processing update failed:" & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, vbExclamation, "Test"
End Sub

'------------------------------------------------------------------------------
' Procedure: Test_ShowMasterPendingQueueRows
' Scope: Public Sub
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   Test_ShowMasterPendingQueueRows.
'
' Why it exists:
'   Rows may represent real orders, section headers, remakes, Greenville work,
'   Customer Pickup work, or updated rows; each type needs different handling.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub Test_ShowMasterPendingQueueRows()
    Dim items As Collection
    Dim item As Object
    Dim msg As String
    Dim n As Long

    On Error GoTo ErrHandler

    msg = "Master Queue Debug" & vbCrLf & vbCrLf & _
          "Current Master DeliveryListKey: " & GetCurrentDeliveryListKey() & vbCrLf & _
          "Queue Paused: " & CStr(IsExternalQueuePaused()) & vbCrLf & _
          "Queue Busy: " & CStr(IsExternalQueueBusy()) & vbCrLf & _
          "Pause Reason: " & GetExternalQueuePauseReason() & vbCrLf & vbCrLf

    Set items = PA_QueueGetPending(GetCurrentDeliveryListKey(), 100)

    msg = msg & "Rows returned by PA_QueueGetPending: " & CStr(items.Count) & vbCrLf & vbCrLf

    For Each item In items
        n = n + 1

        msg = msg & "#" & n & vbCrLf & _
              "Id: " & PA_DictText(item, "id") & vbCrLf & _
              "RequestId: " & PA_DictText(item, "requestId") & vbCrLf & _
              "DeliveryListKey: " & PA_DictText(item, "deliveryListKey") & vbCrLf & _
              "RequestType: " & PA_DictText(item, "requestType") & vbCrLf & _
              "Mode: " & PA_DictText(item, "mode") & vbCrLf & _
              "TargetSheet: " & PA_DictText(item, "targetSheet") & vbCrLf & _
              "RequestComment: " & PA_DictText(item, "requestComment") & vbCrLf & _
              "Status: " & PA_DictText(item, "status") & vbCrLf & vbCrLf

        If Len(msg) > 3000 Then
            msg = msg & "...message shortened..."
            Exit For
        End If
    Next item

    MsgBox msg, vbInformation, "Master Queue Debug"
    Exit Sub

ErrHandler:
    MsgBox "Queue debug failed." & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbExclamation, "Master Queue Debug"
End Sub

'------------------------------------------------------------------------------
' Procedure: Test_RunMasterQueueCycleNow
' Scope: Public Sub
'
' What it does:
'   Handles queue/request state used by the shared ScanQueue workflow for
'   Test_RunMasterQueueCycleNow.
'
' Why it exists:
'   Queue state must be tracked carefully so buffered intake scans, master
'   processing, retries, and final results stay aligned.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub Test_RunMasterQueueCycleNow()
    On Error GoTo ErrHandler

    If IsExternalQueuePaused() Then
        MsgBox "The master queue is paused." & vbCrLf & vbCrLf & _
               "Pause Reason: " & GetExternalQueuePauseReason() & vbCrLf & vbCrLf & _
               "Click the queue button to resume, or run ResumeExternalQueue first.", _
               vbExclamation, "Master Queue Paused"
        Exit Sub
    End If

    ProcessExternalQueuedScans

    MsgBox "Master queue cycle finished." & vbCrLf & vbCrLf & _
           "Check the SharePoint ScanQueue row status now.", _
           vbInformation, "Master Queue Debug"
    Exit Sub

ErrHandler:
    MsgBox "Manual queue cycle failed." & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbExclamation, "Master Queue Debug"
End Sub

'------------------------------------------------------------------------------
' Procedure: QueueItemScanDateTime
' Scope: Private Function
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   QueueItemScanDateTime.
'
' Why it exists:
'   Delivery timing, queue timestamps, and scan timestamps drive status
'   messages such as Early, On-Time, Late, Processing, and Done.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function QueueItemScanDateTime(ByVal item As Object) As Date
    Dim rawText As String
    Dim parsedDate As Date

    If item Is Nothing Then
        QueueItemScanDateTime = Now
        Exit Function
    End If

    'This is the time the intake scan hit the SharePoint queue.
    rawText = Trim$(PA_DictText(item, "queuedAt"))

    'Fallbacks for safety.
    If Len(rawText) = 0 Then rawText = Trim$(PA_DictText(item, "QueuedAt"))
    If Len(rawText) = 0 Then rawText = Trim$(PA_DictText(item, "scannedAt"))
    If Len(rawText) = 0 Then rawText = Trim$(PA_DictText(item, "ScannedAt"))

    parsedDate = QueueTimestampToLocalDate(rawText)

    If parsedDate <= 0 Then parsedDate = Now

    QueueItemScanDateTime = parsedDate
End Function

'------------------------------------------------------------------------------
' Procedure: QueueTimestampToLocalDate
' Scope: Private Function
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   QueueTimestampToLocalDate.
'
' Why it exists:
'   Delivery timing, queue timestamps, and scan timestamps drive status
'   messages such as Early, On-Time, Late, Processing, and Done.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function QueueTimestampToLocalDate(ByVal rawText As String) As Date
    Dim s As String
    Dim isIsoLike As Boolean
    Dim dt As Date

    s = Trim$(CStr(rawText))
    If Len(s) = 0 Then Exit Function
    If LCase$(s) = "null" Then Exit Function

    s = Replace$(s, """", vbNullString)

    isIsoLike = (InStr(1, s, "T", vbBinaryCompare) > 0 Or _
                 Right$(UCase$(s), 1) = "Z" Or _
                 InStr(1, s, "+00:00", vbTextCompare) > 0)

    If isIsoLike Then
        dt = QueueIsoTimestampToLocalDate(s)
        If dt > 0 Then
            QueueTimestampToLocalDate = dt
            Exit Function
        End If
    End If

    'If SharePoint/Power Automate already returned a normal local datetime string,
    'do not convert it again.
    On Error Resume Next
    If IsDate(s) Then QueueTimestampToLocalDate = CDate(s)
    On Error GoTo 0
End Function

'------------------------------------------------------------------------------
' Procedure: QueueIsoTimestampToLocalDate
' Scope: Private Function
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   QueueIsoTimestampToLocalDate.
'
' Why it exists:
'   Delivery timing, queue timestamps, and scan timestamps drive status
'   messages such as Early, On-Time, Late, Processing, and Done.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function QueueIsoTimestampToLocalDate(ByVal isoText As String) As Date
    Dim s As String
    Dim baseText As String
    Dim baseDate As Date
    Dim utcDate As Date
    Dim localOffsetMinutes As Long
    Dim sourceOffsetMinutes As Long
    Dim hasExplicitOffset As Boolean
    Dim tailText As String
    Dim signText As String
    Dim offsetHours As Long
    Dim offsetMinutes As Long
    Dim dotPos As Long

    s = Trim$(CStr(isoText))
    If Len(s) = 0 Then Exit Function

    s = Replace$(s, """", vbNullString)
    s = Replace$(s, "T", " ")

    'Remove fractional seconds before timezone handling:
    '2026-05-15 18:45:12.123Z -> 2026-05-15 18:45:12Z
    dotPos = InStr(1, s, ".", vbBinaryCompare)
    If dotPos > 0 Then
        s = Left$(s, dotPos - 1) & Mid$(s, Len(s), 1)
    End If

    'Handle timezone offset endings like +00:00 or -04:00.
    If Len(s) >= 6 Then
        tailText = Right$(s, 6)
        signText = Left$(tailText, 1)

        If (signText = "+" Or signText = "-") And Mid$(tailText, 4, 1) = ":" Then
            hasExplicitOffset = True
            offsetHours = CLng(Val(Mid$(tailText, 2, 2)))
            offsetMinutes = CLng(Val(Mid$(tailText, 5, 2)))

            sourceOffsetMinutes = (offsetHours * 60) + offsetMinutes
            If signText = "-" Then sourceOffsetMinutes = -sourceOffsetMinutes

            s = Left$(s, Len(s) - 6)
        End If
    End If

    If Right$(UCase$(s), 1) = "Z" Then
        hasExplicitOffset = True
        sourceOffsetMinutes = 0
        s = Left$(s, Len(s) - 1)
    End If

    baseText = Trim$(s)
    If Len(baseText) >= 19 Then baseText = Left$(baseText, 19)

    On Error Resume Next
    baseDate = CDate(baseText)
    On Error GoTo 0

    If baseDate <= 0 Then Exit Function

    'If timestamp was explicit UTC/offset, first convert source time to UTC.
    'If it was ISO-like but no offset was included, treat it as UTC because
    'SharePoint/Power Automate DateTime values commonly come back that way.
    If hasExplicitOffset Then
        utcDate = DateAdd("n", -sourceOffsetMinutes, baseDate)
    Else
        utcDate = baseDate
    End If

    localOffsetMinutes = GetWindowsLocalUtcOffsetMinutes()

    QueueIsoTimestampToLocalDate = DateAdd("n", localOffsetMinutes, utcDate)
End Function

'------------------------------------------------------------------------------
' Procedure: GetWindowsLocalUtcOffsetMinutes
' Scope: Private Function
'
' What it does:
'   Controls the active sheet/window view, freeze panes, navigation, or
'   selected cell for GetWindowsLocalUtcOffsetMinutes.
'
' Why it exists:
'   The workbook is used by scanners/operators, so opening the right view and
'   scan area reduces missed scans and operator confusion.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetWindowsLocalUtcOffsetMinutes() As Long
    Dim svc As Object
    Dim items As Object
    Dim itm As Object

    On Error Resume Next

    Set svc = GetObject("winmgmts:\\.\root\cimv2")
    Set items = svc.ExecQuery("SELECT CurrentTimeZone FROM Win32_ComputerSystem")

    For Each itm In items
        GetWindowsLocalUtcOffsetMinutes = CLng(itm.CurrentTimeZone)
        Exit Function
    Next itm

    On Error GoTo 0
End Function

'------------------------------------------------------------------------------
' Procedure: DebugMasterQueuePullNow
' Scope: Public Sub
'
' What it does:
'   Handles queue/request state used by the shared ScanQueue workflow for
'   DebugMasterQueuePullNow.
'
' Why it exists:
'   Queue state must be tracked carefully so buffered intake scans, master
'   processing, retries, and final results stay aligned.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub DebugMasterQueuePullNow()
    Dim ws As Worksheet
    Dim nextRow As Long
    Dim items As Collection
    Dim item As Object
    Dim keyText As String
    Dim i As Long

    On Error GoTo ErrHandler

    RefreshCurrentDeliveryListIdentity
    keyText = GetCurrentDeliveryListKey()

    Set items = PA_QueueGetPending(keyText, MAX_QUEUE_ROWS_PER_CYCLE)

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets("__MASTER_QUEUE_PULL_DEBUG")
    On Error GoTo ErrHandler

    If ws Is Nothing Then
        Set ws = ThisWorkbook.Worksheets.Add(After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
        ws.Name = "__MASTER_QUEUE_PULL_DEBUG"
        ws.Range("A1:O1").Value = Array( _
    "CheckedAt", _
    "MasterDeliveryListKey", _
    "ItemCount", _
    "ItemIndex", _
    "Id", _
    "RequestId", _
    "DeliveryListKey", _
    "RequestType", _
    "Barcode", _
    "OrderNumber", _
    "ItemNumber", _
    "Mode", _
    "TargetSheet", _
    "Status", _
    "RequestComment")
        ws.rows(1).Font.Bold = True
        ws.Columns("A:L").ColumnWidth = 24
    End If

    nextRow = ws.Cells(ws.rows.Count, 1).End(xlUp).Row + 1

    ws.Cells(nextRow, 1).Value = Now
    ws.Cells(nextRow, 2).Value = keyText
    ws.Cells(nextRow, 3).Value = items.Count

    If items.Count = 0 Then
        MsgBox "Queue pull returned 0 rows." & vbCrLf & vbCrLf & _
               "Master key used:" & vbCrLf & keyText & vbCrLf & vbCrLf & _
               "Open __MASTER_QUEUE_PULL_DEBUG and compare this key to the queued ScanQueue row.", _
               vbExclamation, "Master Queue Pull Debug"
        Exit Sub
    End If

    For Each item In items
        i = i + 1

        If i > 1 Then
            nextRow = ws.Cells(ws.rows.Count, 1).End(xlUp).Row + 1
            ws.Cells(nextRow, 1).Value = Now
            ws.Cells(nextRow, 2).Value = keyText
            ws.Cells(nextRow, 3).Value = items.Count
        End If

        ws.Cells(nextRow, 4).Value = i
        ws.Cells(nextRow, 5).Value = PA_DictText(item, "id")
        ws.Cells(nextRow, 6).Value = PA_DictText(item, "requestId")
        ws.Cells(nextRow, 7).Value = PA_DictText(item, "deliveryListKey")
        ws.Cells(nextRow, 8).Value = PA_DictText(item, "requestType")
ws.Cells(nextRow, 9).Value = PA_DictText(item, "barcode")
ws.Cells(nextRow, 10).Value = PA_DictText(item, "orderNumber")
ws.Cells(nextRow, 11).Value = PA_DictText(item, "itemNumber")
ws.Cells(nextRow, 12).Value = PA_DictText(item, "mode")
ws.Cells(nextRow, 13).Value = PA_DictText(item, "targetSheet")
ws.Cells(nextRow, 14).Value = PA_DictText(item, "status")
ws.Cells(nextRow, 15).Value = PA_DictText(item, "requestComment")
    Next item

    MsgBox "Queue pull returned " & items.Count & " row(s)." & vbCrLf & vbCrLf & _
           "Master key used:" & vbCrLf & keyText & vbCrLf & vbCrLf & _
           "Open __MASTER_QUEUE_PULL_DEBUG to inspect what the master sees.", _
           vbInformation, "Master Queue Pull Debug"

    Exit Sub

ErrHandler:
    MsgBox "DebugMasterQueuePullNow failed." & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbExclamation, "Master Queue Pull Debug"
End Sub


