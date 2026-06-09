Attribute VB_Name = "modIntakeStation"
Option Explicit

'==============================================================================
' Module: modIntakeStation
' Workbook: Intake_Scanning_Test.xlsm / Intake scanner workbook
'
' What this module does:
'   Main intake-station controller. It owns scanner settings, panel status,
'   scan submission, queue polling, revision checks, alerts, and stage/profile
'   configuration.
'
' Why this module exists:
'   The intake workbook acts like a scanner front end; this module coordinates
'   the operator UI with local validation, buffering, SharePoint queue status,
'   and master snapshot freshness.
'
' Commenting standard used in this rewrite:
'   Comments explain both what each procedure/section does and why it
'   matters to the scanning, SharePoint, Power Automate, buffering, and
'   operator-safety workflow. The code behavior and public procedure names
'   are intentionally kept stable so existing buttons/forms/timers keep working.
'==============================================================================


'modIntakeStation'

Private mNextPollTime As Date
Private mPollingScheduled As Boolean
Private mLastPopupRequestId As String

Private mCachedCurrentRevisionToken As String
Private mCachedCurrentRevisionUpdatedAt As String
Private mLastRevisionCheckAt As Date

Public Const SHARED_MANUAL_SCAN_FORM_NAME As String = "frmManualScanEntry"

Private Const REVISION_CHECK_CACHE_SECONDS As Long = 3

Public Const SCANNER_PANEL_SHEET_NAME As String = "Scanning Panel"
Public Const CONFIG_SHEET_NAME As String = "Config"
Public Const IMPORT_SHEET_NAME As String = "Staging"

Public Const CELL_SELECTED_DISPLAY_TOP As String = "J5"
Public Const CELL_PROCESSOR_STATUS As String = "L5"
Public Const CELL_LAST_QUEUE_STATUS As String = "N5"
Public Const CELL_SELECTED_KEY As String = "J6"
Public Const CELL_LAST_REQUEST As String = "L6"
Public Const CELL_LAST_RESULT_CODE As String = "N6"

Public Const CELL_SELECTED_DISPLAY_MAIN As String = "I9"
Public Const CELL_MODE As String = "I10"
Public Const CELL_LAST_SCAN_RESULT As String = "L9"
Public Const CELL_LAST_RESULT_MESSAGE As String = "L10"

Public Const CELL_SCAN_BOX As String = "I12"
Public Const CELL_PREVIEW_ORDER As String = "J12"
Public Const CELL_PREVIEW_ITEM As String = "K12"
Public Const CELL_PREVIEW_QTY As String = "L12"
Public Const CELL_PREVIEW_TIME As String = "M12"
Public Const CELL_PREVIEW_CHECK As String = "N12"
Public Const CELL_PREVIEW_COMMENT As String = "O12"

Public Const IMPORT_TOP_ROW As Long = 20
Public Const IMPORT_LEFT_COL As Long = 1
Public Const IMPORT_MAX_COL As Long = 48   'AV
Public Const IMPORT_CLEAR_LAST_ROW As Long = 3000


Public Const CFG_DEFAULT_MODE As String = "DefaultMode"
Public Const CFG_STATION_NAME As String = "StationName"
Public Const CFG_TARGET_SHEET As String = "TargetSheet"
Public Const CFG_SELECTED_KEY As String = "SelectedDeliveryListKey"
Public Const CFG_SELECTED_DISPLAY As String = "SelectedDeliveryListDisplay"
Public Const CFG_SELECTED_PROFILE As String = "SelectedStationProfile"
Public Const CFG_MASTER_WORKBOOK_PATH As String = "MasterWorkbookPath"
Public Const CFG_LOADED_STAGE_SHEET As String = "LoadedStageSheet"
Public Const CFG_LOADED_STAGE_AT As String = "LoadedStageLoadedAt"
Public Const CFG_LOADED_REVISION_TOKEN As String = "LoadedRevisionToken"
Public Const CFG_LOADED_REVISION_UPDATED_AT As String = "LoadedRevisionUpdatedAt"
Public Const CFG_AUTO_QUEUE_POLL_ENABLED As String = "AutoQueuePollEnabled"

Public Const STATION_POLL_DELAY_AFTER_SCAN_SECONDS As Long = 30
Private Const STATION_POLL_REPEAT_SECONDS As Long = 30
Private Const STATION_LISTINFO_REFRESH_SECONDS As Long = 30

Private Const QUEUE_FAST_POLL_MAX_ATTEMPTS As Long = 12
Private Const QUEUE_SLOW_FALLBACK_SECONDS As Long = 600

Private mQueueFastPollAttemptCount As Long
Private mQueueSlowFallbackActive As Boolean

Private mLastSelectedDeliveryStatusRefreshAt As Date
Private mLastRevisionPopupToken As String
Private mLastBackgroundRevisionCheckAt As Date

Public Const REVISION_BACKGROUND_CHECK_SECONDS As Long = 1800
Private mMasterCheckBusy As Boolean
Private mQueueStatusBusy As Boolean
Private mLastStatusMissingRequestId As String
Private mLastStatusMissingCount As Long
Private mOverrideRequestIds As Object
Private mScanAlertActive As Boolean
Private mPendingOverrideItem As Object

'------------------------------------------------------------------------------
' Procedure: OverrideRequestIdStore
' Scope: Private Function
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   OverrideRequestIdStore.
'
' Why it exists:
'   The intake station must keep local buffer state, SharePoint queue state,
'   and master final results synchronized without blocking scanning.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function OverrideRequestIdStore() As Object
    If mOverrideRequestIds Is Nothing Then
        Set mOverrideRequestIds = CreateObject("Scripting.Dictionary")
    End If

    Set OverrideRequestIdStore = mOverrideRequestIds
End Function

'------------------------------------------------------------------------------
' Procedure: MarkOverrideRequestId
' Scope: Private Sub
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   MarkOverrideRequestId.
'
' Why it exists:
'   The intake station must keep local buffer state, SharePoint queue state,
'   and master final results synchronized without blocking scanning.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub MarkOverrideRequestId(ByVal requestId As String)
    requestId = Trim$(CStr(requestId))
    If Len(requestId) = 0 Then Exit Sub

    OverrideRequestIdStore()(UCase$(requestId)) = True
End Sub

'------------------------------------------------------------------------------
' Procedure: IsKnownOverrideRequestId
' Scope: Private Function
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   IsKnownOverrideRequestId.
'
' Why it exists:
'   The intake station must keep local buffer state, SharePoint queue state,
'   and master final results synchronized without blocking scanning.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function IsKnownOverrideRequestId(ByVal requestId As String) As Boolean
    requestId = Trim$(CStr(requestId))
    If Len(requestId) = 0 Then Exit Function

    IsKnownOverrideRequestId = OverrideRequestIdStore().Exists(UCase$(requestId))
End Function

'------------------------------------------------------------------------------
' Procedure: IsScanAlertActive
' Scope: Public Function
'
' What it does:
'   Displays, updates, or clears an operator-facing alert/message for
'   IsScanAlertActive.
'
' Why it exists:
'   Operators need clear blocking messages when scanning is paused, unsafe,
'   outdated, or requires review so they do not continue blindly.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function IsScanAlertActive() As Boolean
    IsScanAlertActive = mScanAlertActive
End Function

'------------------------------------------------------------------------------
' Procedure: ShowScanSafeAlert
' Scope: Private Sub
'
' What it does:
'   Displays a modeless alert that pauses scan/queue activity and traps focus
'   when a scan result requires operator attention.
'
' Why it exists:
'   Some errors must stop the operator immediately so they cannot keep
'   scanning while the workbook is in a bad or review-required state.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ShowScanSafeAlert(ByVal titleText As String, _
                              ByVal messageText As String, _
                              Optional ByVal codeText As String = vbNullString)
    mScanAlertActive = True
    Set mPendingOverrideItem = Nothing

    'Hard-pause queue polling while an alert is active.
    CancelStationPoll
    HideProcessingNotice
    mQueueStatusBusy = False
    ClearStageScanBoxSilently

    On Error Resume Next

    SetPanelCell StationSheet(), CELL_LAST_QUEUE_STATUS, "Alert active"
    SetPanelCell StationSheet(), CELL_LAST_RESULT_CODE, codeText
    SetPanelCell StationSheet(), CELL_LAST_SCAN_RESULT, "Stopped"
    SetPanelCell StationSheet(), CELL_LAST_RESULT_MESSAGE, messageText

    Load frmScanAlert
    frmScanAlert.LoadAlert titleText, messageText, codeText, False
    frmScanAlert.Show vbModeless
    frmScanAlert.txtScanTrap.SetFocus

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: ShowScanSafeOverrideAlert
' Scope: Private Sub
'
' What it does:
'   Displays the special receive-override alert and stores the request item
'   that can be approved.
'
' Why it exists:
'   Inbound overrides must be deliberate because they can allow receiving
'   without/outside outbound quantity rules.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ShowScanSafeOverrideAlert(ByVal titleText As String, _
                                      ByVal messageText As String, _
                                      ByVal item As Object)
    mScanAlertActive = True
    Set mPendingOverrideItem = item

    'Hard-pause queue polling while an alert is active.
    CancelStationPoll
    HideProcessingNotice
    mQueueStatusBusy = False
    ClearStageScanBoxSilently

    On Error Resume Next

    SetPanelCell StationSheet(), CELL_LAST_QUEUE_STATUS, "Override available"
    SetPanelCell StationSheet(), CELL_LAST_RESULT_CODE, "OVERRIDE_AVAILABLE"
    SetPanelCell StationSheet(), CELL_LAST_SCAN_RESULT, "Stopped"
    SetPanelCell StationSheet(), CELL_LAST_RESULT_MESSAGE, messageText

    Load frmScanAlert
    frmScanAlert.LoadAlert titleText, messageText, "OVERRIDE_AVAILABLE", True
    frmScanAlert.Show vbModeless
    frmScanAlert.txtScanTrap.SetFocus

    On Error GoTo 0
End Sub
Private Sub ShowImmediateIndianTrailBayPopupFromAssignmentList(ByVal orderNumber As Long, _
                                                               ByVal itemNumber As Long)
    Dim stageProfile As String
    Dim modeText As String
    Dim targetSheet As String
    Dim bayInfo As Object
    Dim bayDisplayName As String
    Dim bayKey As String
    Dim assignmentStatus As String
    Dim glassHeader As String
    Dim popupMessage As String
    Dim codeText As String
    Dim bayLine As String
    Dim lookupOk As String
    Dim lookupFound As String
    Dim lookupMessage As String

    stageProfile = GetSelectedStageProfile()
    modeText = UCase$(Trim$(ModeFromStageProfile(stageProfile)))
    targetSheet = StageSheetFromProfile(stageProfile)

    'Only Indian Trail receiving needs the immediate placement popup.
    If modeText <> "RECV" Then Exit Sub
    If StrComp(targetSheet, "Inbound - Indian Trail", vbTextCompare) <> 0 Then Exit Sub
    If orderNumber <= 0 Then Exit Sub

    Set bayInfo = PA_IndianTrailBayLookup(GetSelectedDeliveryKey(), orderNumber, itemNumber)
    If bayInfo Is Nothing Then Exit Sub

    lookupOk = UCase$(PA_DictText(bayInfo, "ok"))
    lookupFound = UCase$(PA_DictText(bayInfo, "found"))
    lookupMessage = Trim$(PA_DictText(bayInfo, "message"))

    If lookupOk <> "TRUE" Then
        popupMessage = "Order: " & orderNumber & vbCrLf & _
                       "Item: " & Format$(itemNumber, "000") & vbCrLf & vbCrLf & _
                       "Bay lookup failed." & vbCrLf & _
                       "Set this order aside for review."

        If Len(lookupMessage) > 0 Then
            popupMessage = popupMessage & vbCrLf & vbCrLf & lookupMessage
        End If

        ShowImmediateIndianTrailBayAlert _
            "Bay Lookup Failed", _
            popupMessage, _
            "BAY_LOOKUP_FAILED"

        Exit Sub
    End If

    bayDisplayName = Trim$(PA_DictText(bayInfo, "bayDisplayName"))
    bayKey = Trim$(PA_DictText(bayInfo, "bayKey"))
    assignmentStatus = Trim$(PA_DictText(bayInfo, "assignmentStatus"))
    glassHeader = Trim$(PA_DictText(bayInfo, "glassHeader"))

    If StrComp(assignmentStatus, "SDIOverride", vbTextCompare) = 0 Then
        popupMessage = "Order: " & orderNumber & vbCrLf & _
                       "Item: " & Format$(itemNumber, "000") & vbCrLf & vbCrLf & _
                       "This order is marked SAME DAY INSTALL (SDI)." & vbCrLf & _
                       "Set it aside for the SDI process."

        If Len(bayDisplayName) > 0 Then
            popupMessage = popupMessage & vbCrLf & vbCrLf & "Current bay: " & bayDisplayName
        End If

        If Len(glassHeader) > 0 Then
            popupMessage = popupMessage & vbCrLf & "Glass: " & glassHeader
        End If

        ShowImmediateIndianTrailBayAlert _
            "Same Day Install (SDI)", _
            popupMessage, _
            "INDIAN_TRAIL_SDI"

        Exit Sub
    End If

    If lookupFound = "TRUE" And Len(bayDisplayName) > 0 Then
        bayLine = bayDisplayName

        If InStr(1, UCase$(bayLine), "BAY", vbTextCompare) = 0 Then
            bayLine = "Bay " & bayLine
        End If

        popupMessage = "Order: " & orderNumber & vbCrLf & _
                       "Item: " & Format$(itemNumber, "000") & vbCrLf

        If Len(glassHeader) > 0 Then
            popupMessage = popupMessage & "Glass: " & glassHeader & vbCrLf
        End If

        popupMessage = popupMessage & vbCrLf & _
                       "Put this order in:" & vbCrLf & _
                       bayLine

        codeText = "INDIAN_TRAIL_BAY"

        ShowImmediateIndianTrailBayAlert _
            "Indian Trail Bay Assignment", _
            popupMessage, _
            codeText

    Else
        popupMessage = "Order: " & orderNumber & vbCrLf & _
                       "Item: " & Format$(itemNumber, "000") & vbCrLf & vbCrLf & _
                       "No Indian Trail bay assignment was found." & vbCrLf & _
                       "Set this order aside for review."

        ShowImmediateIndianTrailBayAlert _
            "Bay Assignment Missing", _
            popupMessage, _
            "BAY_NOT_FOUND"
    End If
End Sub

Private Sub ShowImmediateIndianTrailBayAlert(ByVal titleText As String, _
                                             ByVal messageText As String, _
                                             ByVal codeText As String)
    mScanAlertActive = True
    Set mPendingOverrideItem = Nothing

    CancelStationPoll
    HideProcessingNotice
    mQueueStatusBusy = False
    ClearStageScanBoxSilently

    On Error Resume Next

    SetPanelCell StationSheet(), CELL_LAST_QUEUE_STATUS, "Bay assignment"
    SetPanelCell StationSheet(), CELL_LAST_RESULT_CODE, codeText
    SetPanelCell StationSheet(), CELL_LAST_SCAN_RESULT, "Bay Assigned"
    SetPanelCell StationSheet(), CELL_LAST_RESULT_MESSAGE, messageText

    Load frmScanAlert
    frmScanAlert.LoadAlert titleText, messageText, codeText, False
    frmScanAlert.Show vbModeless
    frmScanAlert.txtScanTrap.SetFocus

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: DismissScanAlert
' Scope: Public Sub
'
' What it does:
'   Clears the active scan alert, resumes polling if needed, and returns focus
'   to the scan box.
'
' Why it exists:
'   After the operator acknowledges an issue, the station should either
'   continue watching active requests or return to ready state.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub DismissScanAlert()
    On Error Resume Next

    mScanAlertActive = False
    Set mPendingOverrideItem = Nothing

    Unload frmScanAlert
    HideProcessingNotice

    If HasActiveQueueWatchRequests() Then
        SetPanelCell StationSheet(), CELL_LAST_QUEUE_STATUS, "Queued"
        SetPanelCell StationSheet(), CELL_LAST_RESULT_MESSAGE, _
            "Alert cleared. Queue status checking will resume."

        ResetQueuePollFallbackForNewWork
        ScheduleStationPoll STATION_POLL_DELAY_AFTER_SCAN_SECONDS
    Else
        SetPanelCell StationSheet(), CELL_LAST_QUEUE_STATUS, "Ready to scan"
    End If

    FocusStageScanBox

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: ApprovePendingReceiveOverride
' Scope: Public Sub
'
' What it does:
'   Approves the currently pending receive override request and submits a
'   corrected override request back through the queue path.
'
' Why it exists:
'   Override approval must still go through the controlled queue system so the
'   master applies the exception consistently.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub ApprovePendingReceiveOverride()
    Dim item As Object

    If mPendingOverrideItem Is Nothing Then
        DismissScanAlert
        Exit Sub
    End If

    Set item = mPendingOverrideItem

    mScanAlertActive = False
    Set mPendingOverrideItem = Nothing

    On Error Resume Next
    Unload frmScanAlert
    On Error GoTo 0

    SubmitOverrideReceiveFromRequestItem item
End Sub

'------------------------------------------------------------------------------
' Procedure: ClearStageScanBoxSilently
' Scope: Private Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   ClearStageScanBoxSilently.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ClearStageScanBoxSilently()
    Dim scanCell As Range
    Dim oldEvents As Boolean

    On Error Resume Next

    Set scanCell = GetStageScanBoxCell()
    If scanCell Is Nothing Then Exit Sub

    oldEvents = Application.EnableEvents
    Application.EnableEvents = False

    scanCell.ClearContents

    Application.EnableEvents = oldEvents

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: IsQueueStatusBusy
' Scope: Public Function
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   IsQueueStatusBusy.
'
' Why it exists:
'   The intake station must keep local buffer state, SharePoint queue state,
'   and master final results synchronized without blocking scanning.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function IsQueueStatusBusy() As Boolean
    IsQueueStatusBusy = mQueueStatusBusy
End Function

'------------------------------------------------------------------------------
' Procedure: IsMasterCheckBusy
' Scope: Public Function
'
' What it does:
'   Checks or stores master delivery-list identity/revision/processor state
'   for IsMasterCheckBusy.
'
' Why it exists:
'   The intake snapshot must match the current master revision; otherwise
'   scans could be applied to stale rows.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function IsMasterCheckBusy() As Boolean
    IsMasterCheckBusy = mMasterCheckBusy
End Function

'------------------------------------------------------------------------------
' Procedure: StationSheet
' Scope: Public Function
'
' What it does:
'   Reads, writes, validates, or applies scanner station settings for
'   StationSheet.
'
' Why it exists:
'   The intake station needs to know which delivery list and stage it is
'   scanning before accepting any input.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function StationSheet() As Worksheet
    Set StationSheet = ThisWorkbook.Worksheets(SCANNER_PANEL_SHEET_NAME)
End Function

'------------------------------------------------------------------------------
' Procedure: StageViewSheet
' Scope: Public Function
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for StageViewSheet.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function StageViewSheet() As Worksheet
    Dim stageName As String
    Dim candidateNames As Variant
    Dim candidateName As Variant

    On Error Resume Next
    Set StageViewSheet = ThisWorkbook.Worksheets(IMPORT_SHEET_NAME)
    On Error GoTo 0

    If Not StageViewSheet Is Nothing Then Exit Function

    stageName = StageSheetFromProfile(GetSelectedStageProfile())
    If Len(stageName) > 0 Then
        On Error Resume Next
        Set StageViewSheet = ThisWorkbook.Worksheets(stageName)
        On Error GoTo 0

        If Not StageViewSheet Is Nothing Then Exit Function
    End If

    candidateNames = Array( _
        "Staging - Airport Rd", _
        "Outbound - Airport Rd", _
        "Inbound - Indian Trail", _
        "Inbound - Greenville", _
        "Customer Pickup" _
    )

    For Each candidateName In candidateNames
        On Error Resume Next
        Set StageViewSheet = ThisWorkbook.Worksheets(CStr(candidateName))
        On Error GoTo 0

        If Not StageViewSheet Is Nothing Then Exit Function
    Next candidateName

    On Error Resume Next
    Set StageViewSheet = ThisWorkbook.Worksheets("Sheet1")
    If Not StageViewSheet Is Nothing Then
        StageViewSheet.Name = IMPORT_SHEET_NAME
    End If
    On Error GoTo 0

    If StageViewSheet Is Nothing Then
        Set StageViewSheet = ThisWorkbook.Worksheets.Add(After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
        StageViewSheet.Name = IMPORT_SHEET_NAME
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: IsStageViewWorksheet
' Scope: Public Function
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   IsStageViewWorksheet.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function IsStageViewWorksheet(ByVal Sh As Object) As Boolean
    Dim sheetName As String

    If Sh Is Nothing Then Exit Function

    sheetName = UCase$(Trim$(CStr(Sh.Name)))

    Select Case sheetName
        Case UCase$(IMPORT_SHEET_NAME), _
             UCase$("Staging - Airport Rd"), _
             UCase$("Outbound - Airport Rd"), _
             UCase$("Inbound - Indian Trail"), _
             UCase$("Inbound - Greenville"), _
             UCase$("Customer Pickup")

            IsStageViewWorksheet = True
    End Select
End Function

'------------------------------------------------------------------------------
' Procedure: ConfigSheet
' Scope: Public Function
'
' What it does:
'   Reads, writes, validates, or applies scanner station settings for
'   ConfigSheet.
'
' Why it exists:
'   The intake station needs to know which delivery list and stage it is
'   scanning before accepting any input.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function ConfigSheet() As Worksheet
    Set ConfigSheet = ThisWorkbook.Worksheets(CONFIG_SHEET_NAME)
End Function

'------------------------------------------------------------------------------
' Procedure: InitializeScannerPanel
' Scope: Public Sub
'
' What it does:
'   Cleans, validates, decodes, applies, focuses, or displays scan/barcode
'   data for InitializeScannerPanel.
'
' Why it exists:
'   The scanner acts like a keyboard, so the workbook must turn entered text
'   into safe order/item updates without duplicate submissions.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub InitializeScannerPanel()
    EnsureScannerConfigDefaults
    EnsureLocalQueueBufferSheet
    FormatScanningPanelLayout
    BuildScanningPanelButtons
    LoadSavedScannerSettingsToPanel
    RefreshScannerPanelOverview
End Sub

'------------------------------------------------------------------------------
' Procedure: FormatScanningPanelLayout
' Scope: Private Sub
'
' What it does:
'   Cleans, validates, decodes, applies, focuses, or displays scan/barcode
'   data for FormatScanningPanelLayout.
'
' Why it exists:
'   The scanner acts like a keyboard, so the workbook must turn entered text
'   into safe order/item updates without duplicate submissions.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub FormatScanningPanelLayout()
    Dim ws As Worksheet

    Set ws = StationSheet()

    On Error Resume Next
    ws.Unprotect
    On Error GoTo 0

    ws.Columns("A:G").ColumnWidth = 1

    ws.Columns("H").ColumnWidth = 30
    ws.Columns("I").ColumnWidth = 30
    ws.Columns("J").ColumnWidth = 25
    ws.Columns("K").ColumnWidth = 25
    ws.Columns("L").ColumnWidth = 50
    ws.Columns("M").ColumnWidth = 25
    ws.Columns("N").ColumnWidth = 25
    ws.Columns("O").ColumnWidth = 25

    ws.Rows("11:14").rowHeight = 20
    ws.Rows("21:30").rowHeight = 20

    ws.Range("I11:O13").ClearContents

    ws.Cells.Locked = True
    ws.Protect DrawingObjects:=True, Contents:=True, Scenarios:=True, UserInterfaceOnly:=True
End Sub

'------------------------------------------------------------------------------
' Procedure: StartupScannerSession
' Scope: Public Sub
'
' What it does:
'   Initializes the intake scanner workbook: disables screen/events during
'   setup, ensures hidden support sheets, cleans audit rows, formats the
'   panel, builds buttons, and resets session state.
'
' Why it exists:
'   A scanner station must start from a known clean state so old delivery
'   selections, stale queue timers, and stale scan values do not affect the
'   next scan session.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'
' Extra note:
'   This is the main startup procedure called by ThisWorkbook.Workbook_Open.
'------------------------------------------------------------------------------
Public Sub StartupScannerSession()
    On Error GoTo CleanFail

    Application.EnableEvents = False
    Application.ScreenUpdating = False

    CancelStationPoll
    EnsureScannerConfigDefaults
    EnsureLocalQueueBufferSheet
    EnsureScanAuditSheet
    CleanupOldScanAuditRows
    FormatScanningPanelLayout

    On Error Resume Next
    BuildScanningPanelButtons
    If Err.Number <> 0 Then
        MsgBox "Button build warning " & Err.Number & ": " & Err.Description, vbExclamation, "Scanning Panel"
        Err.Clear
    End If
    On Error GoTo CleanFail

    ResetScannerSessionState

CleanExit:
    Application.EnableEvents = True
    Application.ScreenUpdating = True
    ChangeScannerSettings
    Exit Sub

CleanFail:
    Application.EnableEvents = True
    Application.ScreenUpdating = True
    MsgBox "Startup error " & Err.Number & ": " & Err.Description, vbExclamation, "Scanning Panel"
    ChangeScannerSettings
End Sub

'------------------------------------------------------------------------------
' Procedure: ResetScannerSessionState
' Scope: Public Sub
'
' What it does:
'   Clears selected delivery/stage settings, panel values, loaded snapshot
'   state, and old stage tabs while preserving required support sheets.
'
' Why it exists:
'   The intake workbook is reused across deliveries and stages; resetting
'   prevents an operator from accidentally scanning against yesterdayÃ¢â‚¬â„¢s or the
'   wrong stageÃ¢â‚¬â„¢s snapshot.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub ResetScannerSessionState()
    Dim wsPanel As Worksheet
    Dim wsStage As Worksheet
    Dim ws As Worksheet
    Dim keepNames As Object

    Set wsPanel = StationSheet()
    Set wsStage = StageViewSheet()
    Set keepNames = CreateObject("Scripting.Dictionary")

    keepNames(UCase$(SCAN_AUDIT_SHEET_NAME)) = True
    keepNames(UCase$(SCANNER_PANEL_SHEET_NAME)) = True
    keepNames(UCase$(CONFIG_SHEET_NAME)) = True
    keepNames(UCase$(IMPORT_SHEET_NAME)) = True
    keepNames(UCase$(BUFFER_SHEET_NAME)) = True
    keepNames(UCase$("__REMAKE_PRINT_TEMPLATE__")) = True

    SetConfigValue CFG_DEFAULT_MODE, vbNullString
    SetConfigValue CFG_STATION_NAME, vbNullString
    SetConfigValue CFG_TARGET_SHEET, vbNullString
    SetConfigValue CFG_SELECTED_KEY, vbNullString
    SetConfigValue CFG_SELECTED_DISPLAY, vbNullString
    SetConfigValue CFG_SELECTED_PROFILE, vbNullString
    SetConfigValue CFG_LOADED_STAGE_SHEET, vbNullString
    SetConfigValue CFG_LOADED_STAGE_AT, vbNullString
    SetConfigValue CFG_LOADED_REVISION_TOKEN, vbNullString
    SetConfigValue CFG_LOADED_REVISION_UPDATED_AT, vbNullString
    
    mLastRevisionPopupToken = vbNullString
    mLastBackgroundRevisionCheckAt = 0

    On Error Resume Next
    Application.EnableEvents = False
    Application.DisplayAlerts = False

    wsPanel.Range(CELL_SELECTED_DISPLAY_TOP).ClearContents
    wsPanel.Range(CELL_PROCESSOR_STATUS).Value = "Select settings"
    wsPanel.Range(CELL_LAST_QUEUE_STATUS).Value = "Select settings"
    wsPanel.Range(CELL_SELECTED_KEY).ClearContents
    wsPanel.Range(CELL_LAST_REQUEST).ClearContents
    wsPanel.Range(CELL_LAST_RESULT_CODE).ClearContents

    wsPanel.Range(CELL_SELECTED_DISPLAY_MAIN).ClearContents
    wsPanel.Range(CELL_MODE).ClearContents
    wsPanel.Range(CELL_LAST_SCAN_RESULT).ClearContents
    wsPanel.Range(CELL_LAST_RESULT_MESSAGE).ClearContents

    wsPanel.Range(CELL_SCAN_BOX).ClearContents
    wsPanel.Range(CELL_PREVIEW_ORDER).ClearContents
    wsPanel.Range(CELL_PREVIEW_ITEM).ClearContents
    wsPanel.Range(CELL_PREVIEW_QTY).ClearContents
    wsPanel.Range(CELL_PREVIEW_TIME).ClearContents
    wsPanel.Range(CELL_PREVIEW_CHECK).ClearContents
    wsPanel.Range(CELL_PREVIEW_COMMENT).ClearContents

    If Not wsStage Is Nothing Then
        wsStage.Unprotect
        wsStage.Cells.UnMerge
        wsStage.Cells.Clear
        wsStage.Name = IMPORT_SHEET_NAME
        wsStage.Tab.ColorIndex = xlColorIndexNone
    End If

    'Delete any leftover old stage tabs from prior versions/runs
    For Each ws In ThisWorkbook.Worksheets
        If Not keepNames.Exists(UCase$(ws.Name)) Then
            Select Case UCase$(ws.Name)
                Case UCase$("Staging - Airport Rd"), _
                     UCase$("Outbound - Airport Rd"), _
                     UCase$("Inbound - Indian Trail"), _
                     UCase$("Inbound - Greenville"), _
                     UCase$("Customer Pickup")
                    ws.Delete
            End Select
        End If
    Next ws

    Application.DisplayAlerts = True
    Application.EnableEvents = True
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: ResetQueuePollFallbackForNewWork
' Scope: Public Sub
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   ResetQueuePollFallbackForNewWork.
'
' Why it exists:
'   The intake station must keep local buffer state, SharePoint queue state,
'   and master final results synchronized without blocking scanning.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub ResetQueuePollFallbackForNewWork()
    mQueueFastPollAttemptCount = 0
    mQueueSlowFallbackActive = False
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplyQueueSlowFallbackUi
' Scope: Private Sub
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   ApplyQueueSlowFallbackUi.
'
' Why it exists:
'   The intake station must keep local buffer state, SharePoint queue state,
'   and master final results synchronized without blocking scanning.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ApplyQueueSlowFallbackUi()
    Dim ws As Worksheet

    Set ws = StationSheet()
    If ws Is Nothing Then Exit Sub

    On Error Resume Next

    SetPanelCell ws, CELL_LAST_QUEUE_STATUS, "Waiting master"
    SetPanelCell ws, CELL_LAST_RESULT_CODE, "MASTER_WAITING"
    SetPanelCell ws, CELL_LAST_RESULT_MESSAGE, _
        "The master has not returned Done/Error yet. The intake will now check every 10 minutes. Click Refresh Queue Status to retry fast checking."
    SetPanelCell ws, CELL_LAST_SCAN_RESULT, "Waiting"

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: ScheduleNextQueueStatusPollAfterCheck
' Scope: Private Sub
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   ScheduleNextQueueStatusPollAfterCheck.
'
' Why it exists:
'   The intake station must keep local buffer state, SharePoint queue state,
'   and master final results synchronized without blocking scanning.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ScheduleNextQueueStatusPollAfterCheck()
    If IsScanAlertActive() Then
        CancelStationPoll
        HideProcessingNotice
        Exit Sub
    End If
    
    If HasActiveQueueWatchRequests() Then
        If mQueueSlowFallbackActive Then
            ApplyQueueSlowFallbackUi
            ScheduleStationPoll QUEUE_SLOW_FALLBACK_SECONDS
            Exit Sub
        End If

        mQueueFastPollAttemptCount = mQueueFastPollAttemptCount + 1

        If mQueueFastPollAttemptCount >= QUEUE_FAST_POLL_MAX_ATTEMPTS Then
            mQueueSlowFallbackActive = True
            ApplyQueueSlowFallbackUi
            ScheduleStationPoll QUEUE_SLOW_FALLBACK_SECONDS
        Else
            ScheduleStationPoll STATION_POLL_REPEAT_SECONDS
        End If
    Else
        ResetQueuePollFallbackForNewWork
        CancelStationPoll

        On Error Resume Next
        SetPanelCell StationSheet(), CELL_LAST_QUEUE_STATUS, "Ready to scan"
        On Error GoTo 0
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: CancelStationPoll
' Scope: Public Sub
'
' What it does:
'   Cancels the scheduled intake polling callback if one exists.
'
' Why it exists:
'   Polling must be cancelled during alerts, workbook close, settings changes,
'   and reset operations to avoid stale callbacks hitting the wrong stage.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub CancelStationPoll()
    On Error Resume Next

    If mPollingScheduled Then
        Application.OnTime EarliestTime:=mNextPollTime, _
                           Procedure:="'" & ThisWorkbook.Name & "'!StationPollBridge", _
                           Schedule:=False
    End If

    mPollingScheduled = False
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplyPanelFormats
' Scope: Private Sub
'
' What it does:
'   Builds, formats, or updates the intake operator panel/buttons for
'   ApplyPanelFormats.
'
' Why it exists:
'   The panel is the operator-facing part of the workbook; consistent buttons
'   and status cells reduce scanning mistakes.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ApplyPanelFormats()
    With StationSheet()
        .Range(CELL_PREVIEW_ITEM).NumberFormat = "0"
        .Range(CELL_PREVIEW_TIME).NumberFormat = "m/d/yyyy h:mm AM/PM"
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: EnsureScannerConfigDefaults
' Scope: Private Sub
'
' What it does:
'   Cleans, validates, decodes, applies, focuses, or displays scan/barcode
'   data for EnsureScannerConfigDefaults.
'
' Why it exists:
'   The scanner acts like a keyboard, so the workbook must turn entered text
'   into safe order/item updates without duplicate submissions.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub EnsureScannerConfigDefaults()
    EnsureConfigKey CFG_DEFAULT_MODE, "STAGING"
    EnsureConfigKey CFG_STATION_NAME, "Staging - Airport Rd"
    EnsureConfigKey CFG_TARGET_SHEET, "Staging - Airport Rd"
    EnsureConfigKey CFG_SELECTED_PROFILE, "Staging - Airport Rd"
    EnsureConfigKey CFG_SELECTED_KEY, vbNullString
    EnsureConfigKey CFG_SELECTED_DISPLAY, vbNullString
    EnsureConfigKey CFG_MASTER_WORKBOOK_PATH, vbNullString
    EnsureConfigKey CFG_LOADED_STAGE_SHEET, vbNullString
    EnsureConfigKey CFG_LOADED_STAGE_AT, vbNullString
    EnsureConfigKey CFG_LOADED_REVISION_TOKEN, vbNullString
    EnsureConfigKey CFG_LOADED_REVISION_UPDATED_AT, vbNullString
    EnsureConfigKey CFG_AUTO_QUEUE_POLL_ENABLED, "TRUE"
End Sub

'------------------------------------------------------------------------------
' Procedure: FocusScanBox
' Scope: Public Sub
'
' What it does:
'   Cleans, validates, decodes, applies, focuses, or displays scan/barcode
'   data for FocusScanBox.
'
' Why it exists:
'   The scanner acts like a keyboard, so the workbook must turn entered text
'   into safe order/item updates without duplicate submissions.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub FocusScanBox()
    FocusStageScanBox
End Sub

'------------------------------------------------------------------------------
' Procedure: ChangeScannerSettings
' Scope: Public Sub
'
' What it does:
'   Cleans, validates, decodes, applies, focuses, or displays scan/barcode
'   data for ChangeScannerSettings.
'
' Why it exists:
'   The scanner acts like a keyboard, so the workbook must turn entered text
'   into safe order/item updates without duplicate submissions.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub ChangeScannerSettings()
    Unload frmScannerSettings
    frmScannerSettings.Show vbModeless
End Sub

'------------------------------------------------------------------------------
' Procedure: ShowSharedManualScanFormOrPrompt
' Scope: Public Sub
'
' What it does:
'   Cleans, validates, decodes, applies, focuses, or displays scan/barcode
'   data for ShowSharedManualScanFormOrPrompt.
'
' Why it exists:
'   The scanner acts like a keyboard, so the workbook must turn entered text
'   into safe order/item updates without duplicate submissions.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub ShowSharedManualScanFormOrPrompt()
    On Error GoTo FallbackPrompt

    ShowImportedStageForManualScan
    VBA.UserForms.Add(SHARED_MANUAL_SCAN_FORM_NAME).Show vbModeless
    Exit Sub

FallbackPrompt:
    SubmitQueuedManualFromPrompt
End Sub

'------------------------------------------------------------------------------
' Procedure: RefreshScannerPanelOverview
' Scope: Public Sub
'
' What it does:
'   Cleans, validates, decodes, applies, focuses, or displays scan/barcode
'   data for RefreshScannerPanelOverview.
'
' Why it exists:
'   The scanner acts like a keyboard, so the workbook must turn entered text
'   into safe order/item updates without duplicate submissions.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub RefreshScannerPanelOverview()
    LoadSavedScannerSettingsToPanel
    RefreshSelectedDeliveryStatus
    RefreshLastRequestStatus
End Sub

'------------------------------------------------------------------------------
' Procedure: LoadSavedScannerSettingsToPanel
' Scope: Private Sub
'
' What it does:
'   Cleans, validates, decodes, applies, focuses, or displays scan/barcode
'   data for LoadSavedScannerSettingsToPanel.
'
' Why it exists:
'   The scanner acts like a keyboard, so the workbook must turn entered text
'   into safe order/item updates without duplicate submissions.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub LoadSavedScannerSettingsToPanel()
    Dim ws As Worksheet
    Dim selectedDisplay As String
    Dim selectedKey As String
    Dim modeText As String

    Set ws = StationSheet()

    selectedDisplay = Trim$(GetConfigValue(CFG_SELECTED_DISPLAY, vbNullString))
    selectedKey = Trim$(GetConfigValue(CFG_SELECTED_KEY, vbNullString))
    modeText = Trim$(GetConfigValue(CFG_SELECTED_PROFILE, GetConfigValue(CFG_STATION_NAME, vbNullString)))

    ws.Range(CELL_SELECTED_DISPLAY_TOP).Value = selectedDisplay
    ws.Range(CELL_SELECTED_DISPLAY_MAIN).Value = selectedDisplay
    ws.Range(CELL_SELECTED_KEY).Value = selectedKey
    ws.Range(CELL_MODE).Value = modeText

    If Len(Trim$(CStr(ws.Range(CELL_LAST_QUEUE_STATUS).Value))) = 0 Then
        ws.Range(CELL_LAST_QUEUE_STATUS).Value = "Idle"
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: SaveScannerSettings
' Scope: Public Sub
'
' What it does:
'   Cleans, validates, decodes, applies, focuses, or displays scan/barcode
'   data for SaveScannerSettings.
'
' Why it exists:
'   The scanner acts like a keyboard, so the workbook must turn entered text
'   into safe order/item updates without duplicate submissions.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub SaveScannerSettings(ByVal deliveryKey As String, ByVal deliveryDisplay As String, ByVal stageProfile As String)
    SetConfigValue CFG_SELECTED_KEY, Trim$(deliveryKey)
    SetConfigValue CFG_SELECTED_DISPLAY, Trim$(deliveryDisplay)
    SetConfigValue CFG_SELECTED_PROFILE, Trim$(stageProfile)
    SetConfigValue CFG_STATION_NAME, Trim$(stageProfile)
    SetConfigValue CFG_TARGET_SHEET, Trim$(stageProfile)
    SetConfigValue CFG_DEFAULT_MODE, ModeFromStageProfile(stageProfile)

    LoadSavedScannerSettingsToPanel
End Sub

'------------------------------------------------------------------------------
' Procedure: LoadLatestPublishedSnapshotForSettings
' Scope: Public Function
'
' What it does:
'   Loads the newest published SharePoint snapshot for the selected delivery
'   list and stage, validates that it actually loaded, updates panel status,
'   and starts background revision checking.
'
' Why it exists:
'   Changing settings should always land the operator on the latest snapshot
'   so new scans are not applied to stale delivery data.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function LoadLatestPublishedSnapshotForSettings(Optional ByVal suppressMessage As Boolean = False) As Boolean
    Dim ws As Worksheet
    Dim expectedStageSheet As String
    Dim loadedStageSheet As String
    Dim loadedRevisionToken As String
    Dim loadedUpdatedAt As String

    Set ws = StationSheet()

    expectedStageSheet = StageSheetFromProfile(GetSelectedStageProfile())

    ImportDebugLog "LoadLatestPublishedSnapshotForSettings", "START", _
               "SelectedKey=" & GetSelectedDeliveryKey(), _
               "SelectedDisplay=" & GetSelectedDeliveryDisplay(), _
               "StageProfile=" & GetSelectedStageProfile() & _
               " | ExpectedStage=" & expectedStageSheet

    If Len(GetSelectedDeliveryKey()) = 0 Then
        If Not suppressMessage Then
            MsgBox "Select a delivery list first.", vbExclamation, "Load Snapshot"
        End If
        Exit Function
    End If

    If Len(GetSelectedStageProfile()) = 0 Or Len(expectedStageSheet) = 0 Then
        If Not suppressMessage Then
            MsgBox "Select a supported stage first.", vbExclamation, "Load Snapshot"
        End If
        Exit Function
    End If

    CancelStationPoll
    ResetRequestTrackingAfterRefresh

    SetPanelCell ws, CELL_LAST_QUEUE_STATUS, "Loading snapshot"
    ClearPanelCell ws, CELL_LAST_RESULT_CODE
    SetPanelCell ws, CELL_LAST_SCAN_RESULT, "Loading"
    SetPanelCell ws, CELL_LAST_RESULT_MESSAGE, _
        "Loading latest published snapshot from SharePoint."

    ShowProcessingNotice "Loading latest published snapshot from SharePoint. Please wait."
    DoEvents

    If Not LoadSelectedStageSnapshotFromSharePoint(True) Then
        HideProcessingNotice

        SetPanelCell ws, CELL_LAST_QUEUE_STATUS, "Load failed"
        SetPanelCell ws, CELL_LAST_RESULT_CODE, "SNAPSHOT_GET_FAILED"
        SetPanelCell ws, CELL_LAST_SCAN_RESULT, "Error"
        SetPanelCell ws, CELL_LAST_RESULT_MESSAGE, _
            "Could not load the latest published snapshot from DeliveryListSnapshots."

        If Not suppressMessage Then
            MsgBox "Snapshot load failed." & vbCrLf & vbCrLf & _
                   "No usable published snapshot was loaded from DeliveryListSnapshots." & vbCrLf & vbCrLf & _
                   "Make sure the master has published at least one snapshot for this delivery list and stage.", _
                   vbExclamation, "Load Snapshot"
        End If

        FocusStageScanBox
        Exit Function
    End If

    HideProcessingNotice

    loadedStageSheet = GetConfigValue(CFG_LOADED_STAGE_SHEET, vbNullString)

    If Not IsImportedStageLoaded() Then
        SetPanelCell ws, CELL_LAST_QUEUE_STATUS, "Load failed"
        SetPanelCell ws, CELL_LAST_RESULT_CODE, "SNAPSHOT_LOAD_FAILED"
        SetPanelCell ws, CELL_LAST_SCAN_RESULT, "Error"
        SetPanelCell ws, CELL_LAST_RESULT_MESSAGE, "The snapshot did not load into the intake sheet."

        FocusStageScanBox
        Exit Function
    End If

    If StrComp(loadedStageSheet, expectedStageSheet, vbTextCompare) <> 0 Then
        SetPanelCell ws, CELL_LAST_QUEUE_STATUS, "Load failed"
        SetPanelCell ws, CELL_LAST_RESULT_CODE, "SNAPSHOT_STAGE_MISMATCH"
        SetPanelCell ws, CELL_LAST_SCAN_RESULT, "Error"
        SetPanelCell ws, CELL_LAST_RESULT_MESSAGE, _
            "The loaded snapshot did not match the selected stage."

        FocusStageScanBox
        Exit Function
    End If

    loadedRevisionToken = GetLoadedRevisionToken()
    loadedUpdatedAt = GetLoadedRevisionUpdatedAt()

    RefreshScannerPanelHeaderOnly
ClearSnapshotRefreshQueueWatch
ClearStageOutOfDateMarker
ResetSnapshotOutOfDateAlertState

    mLastRevisionPopupToken = vbNullString
    mLastBackgroundRevisionCheckAt = 0

    SetPanelCell ws, CELL_LAST_QUEUE_STATUS, "Snapshot loaded"
    ClearPanelCell ws, CELL_LAST_RESULT_CODE
    SetPanelCell ws, CELL_LAST_SCAN_RESULT, "Ready"

    If Len(loadedUpdatedAt) > 0 Then
        SetPanelCell ws, CELL_LAST_RESULT_MESSAGE, _
            "Latest published snapshot loaded from SharePoint. Snapshot updated: " & loadedUpdatedAt
    ElseIf Len(loadedRevisionToken) > 0 Then
        SetPanelCell ws, CELL_LAST_RESULT_MESSAGE, _
            "Latest published snapshot loaded from SharePoint. Revision: " & loadedRevisionToken
    Else
        SetPanelCell ws, CELL_LAST_RESULT_MESSAGE, _
            "Latest published snapshot loaded from SharePoint."
    End If

    ApplySelectedMasterStatusWarning ws

    ImportDebugLog "LoadLatestPublishedSnapshotForSettings", "END_OK", _
                   "LoadedStage=" & loadedStageSheet, _
                   "LoadedRevision=" & loadedRevisionToken, _
                   "LoadedUpdatedAt=" & loadedUpdatedAt

    CancelStationPoll
    ScheduleStationPoll REVISION_BACKGROUND_CHECK_SECONDS

    FocusStageScanBox

    LoadLatestPublishedSnapshotForSettings = True
End Function

'------------------------------------------------------------------------------
' Procedure: ApplyScannerSettingsAndRequestFreshSnapshot
' Scope: Public Function
'
' What it does:
'   Validates the selected delivery/stage, prepares the current stage safely,
'   saves the new settings, and requests a fresh snapshot load.
'
' Why it exists:
'   Settings changes are dangerous if buffered scans or comments are still
'   pending, so this procedure coordinates a safe handoff before switching
'   stages.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function ApplyScannerSettingsAndRequestFreshSnapshot(ByVal deliveryKey As String, _
                                                            ByVal deliveryDisplay As String, _
                                                            ByVal stageProfile As String) As Boolean
    Dim ws As Worksheet
    Dim prepError As String
    Dim expectedStageSheet As String

    Set ws = StationSheet()

    deliveryKey = Trim$(CStr(deliveryKey))
    deliveryDisplay = Trim$(CStr(deliveryDisplay))
    stageProfile = Trim$(CStr(stageProfile))

    If Len(deliveryKey) = 0 Then
        MsgBox "Choose a delivery list before applying settings.", vbExclamation, "Scanner Settings"
        Exit Function
    End If

    If Len(stageProfile) = 0 Then
        MsgBox "Choose a stage before applying settings.", vbExclamation, "Scanner Settings"
        Exit Function
    End If

    If Len(ModeFromStageProfile(stageProfile)) = 0 Then
        MsgBox "Unsupported stage profile: " & stageProfile, vbExclamation, "Scanner Settings"
        Exit Function
    End If

    If IsScanAlertActive() Then
        MsgBox "Clear the active scanning alert before changing settings.", vbExclamation, "Scanner Settings"
        Exit Function
    End If

    If Not PrepareCurrentStageBeforeSettingsChange(prepError) Then
        If Len(prepError) = 0 Then prepError = "The current stage could not be prepared for settings change."

        MsgBox "Settings were not changed." & vbCrLf & vbCrLf & _
               prepError, _
               vbExclamation, "Scanner Settings"

        FocusStageScanBox
        Exit Function
    End If

    CancelStationPoll

    SaveScannerSettings deliveryKey, deliveryDisplay, stageProfile

    expectedStageSheet = StageSheetFromProfile(stageProfile)

    SetPanelCell ws, CELL_LAST_QUEUE_STATUS, "Changing settings"
    ClearPanelCell ws, CELL_LAST_RESULT_CODE
    SetPanelCell ws, CELL_LAST_SCAN_RESULT, "Loading"
    SetPanelCell ws, CELL_LAST_RESULT_MESSAGE, _
        "Loading latest published snapshot for " & expectedStageSheet & "."

    LoadLatestPublishedSnapshotForSettings True

    ApplyScannerSettingsAndRequestFreshSnapshot = _
        (IsImportedStageLoaded() And _
         StrComp(GetConfigValue(CFG_LOADED_STAGE_SHEET, vbNullString), expectedStageSheet, vbTextCompare) = 0)
End Function

'------------------------------------------------------------------------------
' Procedure: PrepareCurrentStageBeforeSettingsChange
' Scope: Private Function
'
' What it does:
'   Flushes local buffered scans, syncs comments, and waits for active queue
'   work before allowing the operator to change delivery/stage settings.
'
' Why it exists:
'   This prevents lost scans or unsaved comments when a user switches away
'   from the current imported stage.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function PrepareCurrentStageBeforeSettingsChange(ByRef errorMessage As String) As Boolean
    errorMessage = vbNullString

    On Error GoTo FailPrep

    If IsBufferFlushBusy() Then
        errorMessage = "Buffered scans are currently being sent. Wait for that to finish, then change settings again."
        Exit Function
    End If

    If HasPendingQueueRows() Then
        ShowProcessingNotice "Sending buffered scans before changing settings. Please wait."
        DoEvents

        FlushPendingQueueRows 500

        HideProcessingNotice

        If HasPendingQueueRows() Or IsBufferFlushBusy() Then
            errorMessage = "Buffered scans are still waiting to send. Settings change was stopped so scans are not lost."
            Exit Function
        End If
    End If

    If IsImportedStageLoaded() Then
        If Not ConfirmDiscardUnsavedStageComments("Change Settings") Then
            errorMessage = "Settings were not changed because comments have not been saved."
            Exit Function
        End If
    End If

    If HasActiveQueueWatchRequests() Then
        ShowProcessingNotice "Checking queued scan status before changing settings. Please wait."
        DoEvents

        RefreshLastRequestStatus
        RefreshPendingImportedQueueStates True

        HideProcessingNotice

        If HasActiveQueueWatchRequests() Then
            If Not ConfirmSettingsChangeWithActiveQueueRequests() Then
                errorMessage = "Settings were not changed because scans are still waiting for master results."
                Exit Function
            End If

            CancelStationPoll
        End If
    End If

    PrepareCurrentStageBeforeSettingsChange = True
    Exit Function

FailPrep:
    HideProcessingNotice
    errorMessage = "Settings-change prep failed. Error " & Err.Number & ": " & Err.Description
End Function

'------------------------------------------------------------------------------
' Procedure: ConfirmSettingsChangeWithActiveQueueRequests
' Scope: Private Function
'
' What it does:
'   Confirms whether the operator wants to switch delivery/stage settings while
'   sent queue requests are still waiting on a final master result.
'
' Why it exists:
'   Buffered local scans must still be flushed before switching, but requests
'   already accepted by SharePoint should not trap an intake station on an old
'   list when the master is offline or closed.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function ConfirmSettingsChangeWithActiveQueueRequests() As Boolean
    ConfirmSettingsChangeWithActiveQueueRequests = _
        (MsgBox( _
            "There are scans already sent to SharePoint that are still waiting for a final result from the master." & vbCrLf & vbCrLf & _
            "You can change settings now. Those scan requests will stay in SharePoint and the master can process them when it is online, but this intake workbook may stop showing final Done/Error results for the previous list or stage after the switch." & vbCrLf & vbCrLf & _
            "Continue changing settings?", _
            vbYesNo + vbExclamation, _
            "Queued Scans Still Waiting") = vbYes)
End Function

'------------------------------------------------------------------------------
' Procedure: WaitForActiveQueueRequestsToFinishForSettingsChange
' Scope: Private Function
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   WaitForActiveQueueRequestsToFinishForSettingsChange.
'
' Why it exists:
'   The intake station must keep local buffer state, SharePoint queue state,
'   and master final results synchronized without blocking scanning.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function WaitForActiveQueueRequestsToFinishForSettingsChange(ByVal timeoutSeconds As Long, _
                                                                     ByRef errorMessage As String) As Boolean
    Dim startedAt As Date

    errorMessage = vbNullString

    If timeoutSeconds < 10 Then timeoutSeconds = 10

    startedAt = Now

    Do
        If Not HasActiveQueueWatchRequests() Then
            WaitForActiveQueueRequestsToFinishForSettingsChange = True
            Exit Function
        End If

        If IsScanAlertActive() Then
            errorMessage = "A scan alert is active. Clear the alert before changing settings."
            Exit Function
        End If

        ShowProcessingNotice "Waiting for the current queue requests to finish before changing settings. Please wait."
        DoEvents

        RefreshLastRequestStatus
        RefreshPendingImportedQueueStates True

        If Not HasActiveQueueWatchRequests() Then
            HideProcessingNotice
            WaitForActiveQueueRequestsToFinishForSettingsChange = True
            Exit Function
        End If

        If DateDiff("s", startedAt, Now) >= timeoutSeconds Then
            HideProcessingNotice
            errorMessage = "There are still scans waiting for the master to finish. Wait for them to show Done/Error, then change settings again."
            Exit Function
        End If

        Application.Wait Now + TimeSerial(0, 0, 2)
    Loop
End Function

'------------------------------------------------------------------------------
' Procedure: ModeFromStageProfile
' Scope: Public Function
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   ModeFromStageProfile.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function ModeFromStageProfile(ByVal stageProfile As String) As String
    Select Case UCase$(Trim$(stageProfile))
        Case "STAGING - AIRPORT RD"
            ModeFromStageProfile = "STAGING"

        Case "OUTBOUND - AIRPORT RD"
            ModeFromStageProfile = "SEND"

        Case "INBOUND - INDIAN TRAIL", _
             "INBOUND - GREENVILLE", _
             "CUSTOMER PICKUP"
            ModeFromStageProfile = "RECV"

        Case Else
            ModeFromStageProfile = vbNullString
    End Select
End Function

'------------------------------------------------------------------------------
' Procedure: StageSheetFromProfile
' Scope: Public Function
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   StageSheetFromProfile.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function StageSheetFromProfile(ByVal stageProfile As String) As String
    Select Case UCase$(Trim$(stageProfile))
        Case "STAGING - AIRPORT RD"
            StageSheetFromProfile = "Staging - Airport Rd"

        Case "OUTBOUND - AIRPORT RD"
            StageSheetFromProfile = "Outbound - Airport Rd"

        Case "INBOUND - INDIAN TRAIL"
            StageSheetFromProfile = "Inbound - Indian Trail"

        Case "INBOUND - GREENVILLE"
            StageSheetFromProfile = "Inbound - Greenville"

        Case "CUSTOMER PICKUP"
            StageSheetFromProfile = "Customer Pickup"

        Case Else
            StageSheetFromProfile = vbNullString
    End Select
End Function

'------------------------------------------------------------------------------
' Procedure: GetSelectedStageProfile
' Scope: Public Function
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   GetSelectedStageProfile.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function GetSelectedStageProfile() As String
    GetSelectedStageProfile = Trim$(GetConfigValue(CFG_SELECTED_PROFILE, vbNullString))
End Function

'------------------------------------------------------------------------------
' Procedure: StageTabColorFromProfile
' Scope: Private Function
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   StageTabColorFromProfile.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function StageTabColorFromProfile(ByVal stageProfile As String) As Long
    Select Case UCase$(Trim$(stageProfile))
        Case "STAGING - AIRPORT RD"
            StageTabColorFromProfile = RGB(127, 127, 127)     'gray

        Case "OUTBOUND - AIRPORT RD"
            StageTabColorFromProfile = RGB(47, 75, 117)       'blue

        Case "INBOUND - INDIAN TRAIL"
            StageTabColorFromProfile = RGB(70, 140, 95)       'green

        Case "INBOUND - GREENVILLE"
            StageTabColorFromProfile = RGB(64, 181, 173)      'turquoise

        Case "CUSTOMER PICKUP"
            StageTabColorFromProfile = RGB(230, 145, 56)      'orange

        Case Else
            StageTabColorFromProfile = RGB(127, 127, 127)
    End Select
End Function

'------------------------------------------------------------------------------
' Procedure: ApplyStageViewTabAppearance
' Scope: Public Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   ApplyStageViewTabAppearance.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub ApplyStageViewTabAppearance(ByVal stageSheetName As String, ByVal stageProfile As String)
    Dim ws As Worksheet
    Dim targetName As String
    Dim conflictWs As Worksheet
    Dim oldDisplayAlerts As Boolean

    Set ws = StageViewSheet()
    If ws Is Nothing Then Exit Sub

    targetName = Trim$(stageSheetName)

    If Len(targetName) = 0 Then
        targetName = StageSheetFromProfile(stageProfile)
    End If

    If Len(targetName) = 0 Then
        targetName = IMPORT_SHEET_NAME
    End If

    On Error Resume Next
    Set conflictWs = ThisWorkbook.Worksheets(targetName)
    On Error GoTo 0

    If Not conflictWs Is Nothing Then
        If StrComp(conflictWs.Name, ws.Name, vbTextCompare) <> 0 Then
            oldDisplayAlerts = Application.DisplayAlerts
            Application.DisplayAlerts = False
            On Error Resume Next
            conflictWs.Delete
            On Error GoTo 0
            Application.DisplayAlerts = oldDisplayAlerts
        End If
    End If

    On Error Resume Next

    If StrComp(ws.Name, targetName, vbTextCompare) <> 0 Then
        ws.Name = targetName
    End If

    ws.Tab.Color = StageTabColorFromProfile(stageProfile)

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: ShowImportedStageForManualScan
' Scope: Public Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   ShowImportedStageForManualScan.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub ShowImportedStageForManualScan()
    Dim ws As Worksheet

    Set ws = StageViewSheet()
    If ws Is Nothing Then Exit Sub

    On Error Resume Next
    ws.Activate

    If Not ActiveWindow Is Nothing Then
        ActiveWindow.ScrollRow = 1
        ActiveWindow.ScrollColumn = 1
    End If
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: GetStationName
' Scope: Public Function
'
' What it does:
'   Reads, writes, validates, or applies scanner station settings for
'   GetStationName.
'
' Why it exists:
'   The intake station needs to know which delivery list and stage it is
'   scanning before accepting any input.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function GetStationName() As String
    GetStationName = Trim$(GetConfigValue(CFG_STATION_NAME, vbNullString))
End Function

'------------------------------------------------------------------------------
' Procedure: GetSelectedDeliveryKey
' Scope: Public Function
'
' What it does:
'   Returns a workbook object, setting, parsed value, range, or calculated
'   value used by calling code (GetSelectedDeliveryKey).
'
' Why it exists:
'   Getters centralize lookup logic so other modules do not duplicate
'   sheet/range/config handling.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function GetSelectedDeliveryKey() As String
    GetSelectedDeliveryKey = Trim$(GetConfigValue(CFG_SELECTED_KEY, vbNullString))
End Function

'------------------------------------------------------------------------------
' Procedure: GetSelectedDeliveryDisplay
' Scope: Public Function
'
' What it does:
'   Returns a workbook object, setting, parsed value, range, or calculated
'   value used by calling code (GetSelectedDeliveryDisplay).
'
' Why it exists:
'   Getters centralize lookup logic so other modules do not duplicate
'   sheet/range/config handling.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function GetSelectedDeliveryDisplay() As String
    GetSelectedDeliveryDisplay = Trim$(GetConfigValue(CFG_SELECTED_DISPLAY, vbNullString))
End Function

'------------------------------------------------------------------------------
' Procedure: GetLoadedRevisionToken
' Scope: Public Function
'
' What it does:
'   Checks or stores master delivery-list identity/revision/processor state
'   for GetLoadedRevisionToken.
'
' Why it exists:
'   The intake snapshot must match the current master revision; otherwise
'   scans could be applied to stale rows.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function GetLoadedRevisionToken() As String
    GetLoadedRevisionToken = Trim$(GetConfigValue(CFG_LOADED_REVISION_TOKEN, vbNullString))
End Function

'------------------------------------------------------------------------------
' Procedure: GetLoadedRevisionUpdatedAt
' Scope: Public Function
'
' What it does:
'   Checks or stores master delivery-list identity/revision/processor state
'   for GetLoadedRevisionUpdatedAt.
'
' Why it exists:
'   The intake snapshot must match the current master revision; otherwise
'   scans could be applied to stale rows.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function GetLoadedRevisionUpdatedAt() As String
    GetLoadedRevisionUpdatedAt = Trim$(GetConfigValue(CFG_LOADED_REVISION_UPDATED_AT, vbNullString))
End Function

'------------------------------------------------------------------------------
' Procedure: GetCurrentSelectedDeliveryListRevisionToken
' Scope: Private Function
'
' What it does:
'   Checks or stores master delivery-list identity/revision/processor state
'   for GetCurrentSelectedDeliveryListRevisionToken.
'
' Why it exists:
'   The intake snapshot must match the current master revision; otherwise
'   scans could be applied to stale rows.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function GetCurrentSelectedDeliveryListRevisionToken(Optional ByRef revisionUpdatedAtText As String = vbNullString, Optional ByVal forceRefresh As Boolean = False) As String
    Dim selectedKey As String
    Dim useCache As Boolean
    Dim item As Object

    selectedKey = GetSelectedDeliveryKey()
    If Len(selectedKey) = 0 Then Exit Function

    useCache = False

    If Not forceRefresh Then
        If mLastRevisionCheckAt > 0 Then
            If DateDiff("s", mLastRevisionCheckAt, Now) < REVISION_CHECK_CACHE_SECONDS Then
                useCache = True
            End If
        End If
    End If

    If useCache Then
        revisionUpdatedAtText = mCachedCurrentRevisionUpdatedAt
        GetCurrentSelectedDeliveryListRevisionToken = mCachedCurrentRevisionToken
        Exit Function
    End If

    Set item = PA_FindActiveDeliveryListInfo(selectedKey, True)
    If item Is Nothing Then
        revisionUpdatedAtText = mCachedCurrentRevisionUpdatedAt
        GetCurrentSelectedDeliveryListRevisionToken = mCachedCurrentRevisionToken
        Exit Function
    End If

    mCachedCurrentRevisionToken = PA_DictText(item, "revisionToken")
    mCachedCurrentRevisionUpdatedAt = PA_DictText(item, "revisionUpdatedAt")
    mLastRevisionCheckAt = Now

    revisionUpdatedAtText = mCachedCurrentRevisionUpdatedAt
    GetCurrentSelectedDeliveryListRevisionToken = mCachedCurrentRevisionToken
End Function

'------------------------------------------------------------------------------
' Procedure: RefreshSelectedDeliveryStatus
' Scope: Public Sub
'
' What it does:
'   Calculates, stores, formats, or displays status/result state for
'   RefreshSelectedDeliveryStatus.
'
' Why it exists:
'   The operator needs to know whether a scan is local, queued, processing,
'   done, errored, or waiting for master confirmation.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub RefreshSelectedDeliveryStatus()
    Dim ws As Worksheet
    Dim selectedKey As String
    Dim item As Object
    Dim displayText As String
    Dim processorStatus As String

    Set ws = StationSheet()
    selectedKey = GetSelectedDeliveryKey()

    If Len(selectedKey) = 0 Then
        ws.Range(CELL_SELECTED_DISPLAY_TOP).Value = vbNullString
        ws.Range(CELL_SELECTED_DISPLAY_MAIN).Value = vbNullString
        ws.Range(CELL_PROCESSOR_STATUS).Value = "No delivery list selected"
        Exit Sub
    End If

    Set item = PA_FindActiveDeliveryListInfo(selectedKey, True)

    If item Is Nothing Then
        ws.Range(CELL_PROCESSOR_STATUS).Value = "Not registered"
        ApplySelectedMasterStatusWarning ws
        Exit Sub
    End If

    displayText = PA_DictText(item, "displayName")
    processorStatus = PA_DictText(item, "processorStatus")

    ws.Range(CELL_SELECTED_DISPLAY_TOP).Value = displayText
    ws.Range(CELL_SELECTED_DISPLAY_MAIN).Value = displayText
    ws.Range(CELL_SELECTED_KEY).Value = selectedKey
    ws.Range(CELL_PROCESSOR_STATUS).Value = processorStatus

    SetConfigValue CFG_SELECTED_DISPLAY, displayText

    ApplySelectedMasterStatusWarning ws
End Sub

'------------------------------------------------------------------------------
' Procedure: StoreLoadedRevisionForSelectedDeliveryList
' Scope: Public Sub
'
' What it does:
'   Checks or stores master delivery-list identity/revision/processor state
'   for StoreLoadedRevisionForSelectedDeliveryList.
'
' Why it exists:
'   The intake snapshot must match the current master revision; otherwise
'   scans could be applied to stale rows.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub StoreLoadedRevisionForSelectedDeliveryList()
    Dim revisionToken As String
    Dim revisionUpdatedAtText As String

    revisionToken = GetCurrentSelectedDeliveryListRevisionToken(revisionUpdatedAtText, True)

    SetConfigValue CFG_LOADED_REVISION_TOKEN, revisionToken
    SetConfigValue CFG_LOADED_REVISION_UPDATED_AT, revisionUpdatedAtText

    mCachedCurrentRevisionToken = revisionToken
    mCachedCurrentRevisionUpdatedAt = revisionUpdatedAtText
    mLastRevisionCheckAt = Now
End Sub

'------------------------------------------------------------------------------
' Procedure: BuildOrderItemErrorText
' Scope: Private Function
'
' What it does:
'   Builds a display string, request key, message, JSON value, or derived
'   object for BuildOrderItemErrorText.
'
' Why it exists:
'   Generated values should be built one consistent way so the buffer, audit,
'   panel, and SharePoint queue can match each other.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function BuildOrderItemErrorText(ByVal ord As Long, ByVal itm As Long, ByVal messageText As String) As String
    If ord > 0 Or itm > 0 Then
        BuildOrderItemErrorText = "Order " & ord & " / Item " & Format$(itm, "000") & vbCrLf & vbCrLf & messageText
    Else
        BuildOrderItemErrorText = messageText
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: ValidateLoadedRevision
' Scope: Private Function
'
' What it does:
'   Compares the loaded snapshot revision with the current active master
'   revision and blocks scanning if the intake copy is outdated.
'
' Why it exists:
'   The master can update after the intake loaded a snapshot; this check
'   prevents scans from being applied to old row data.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function ValidateLoadedRevision(ByVal ws As Worksheet) As Boolean
    Dim currentToken As String
    Dim currentUpdatedAt As String
    Dim loadedToken As String
    Dim popupKey As String

    'Out-of-date snapshots are now warning-only.
    'Scanning must stay allowed.
    ValidateLoadedRevision = True

    If HasLoadedRevisionMismatch(currentToken, currentUpdatedAt) Then
        ApplyRefreshRequiredUi ws, currentUpdatedAt

        loadedToken = GetLoadedRevisionToken()

        If Len(loadedToken) = 0 Then
            popupKey = "NO_LOADED_TOKEN"
        Else
            popupKey = loadedToken
        End If

        'Show only once for the currently loaded stale snapshot.
        'Do not show again until the user refreshes and this state is reset.
        If StrComp(mLastRevisionPopupToken, popupKey, vbTextCompare) <> 0 Then
            mLastRevisionPopupToken = popupKey
            ShowSnapshotOutOfDateScanAlert currentUpdatedAt
        End If
    End If
End Function
'------------------------------------------------------------------------------
' Procedure: GetConfigValue
' Scope: Public Function
'
' What it does:
'   Reads, writes, validates, or applies scanner station settings for
'   GetConfigValue.
'
' Why it exists:
'   The intake station needs to know which delivery list and stage it is
'   scanning before accepting any input.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function GetConfigValue(ByVal configKey As String, Optional ByVal defaultValue As String = vbNullString) As String
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim r As Long

    Set ws = ConfigSheet()
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row

    For r = 2 To lastRow
        If StrComp(Trim$(CStr(ws.Cells(r, 1).Value)), Trim$(configKey), vbTextCompare) = 0 Then
            GetConfigValue = Trim$(CStr(ws.Cells(r, 2).Value))
            Exit Function
        End If
    Next r

    GetConfigValue = defaultValue
End Function

'------------------------------------------------------------------------------
' Procedure: SetConfigValue
' Scope: Public Sub
'
' What it does:
'   Reads, writes, validates, or applies scanner station settings for
'   SetConfigValue.
'
' Why it exists:
'   The intake station needs to know which delivery list and stage it is
'   scanning before accepting any input.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub SetConfigValue(ByVal configKey As String, ByVal configValue As String)
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim r As Long
    Dim writeRow As Long

    Set ws = ConfigSheet()
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row
    writeRow = 0

    For r = 2 To lastRow
        If StrComp(Trim$(CStr(ws.Cells(r, 1).Value)), Trim$(configKey), vbTextCompare) = 0 Then
            writeRow = r
            Exit For
        End If
    Next r

    If writeRow = 0 Then
        If lastRow < 2 Then lastRow = 1
        writeRow = lastRow + 1
        ws.Cells(writeRow, 1).Value = configKey
    End If

    ws.Cells(writeRow, 2).Value = configValue
End Sub

'------------------------------------------------------------------------------
' Procedure: EnsureConfigKey
' Scope: Private Sub
'
' What it does:
'   Reads, writes, validates, or applies scanner station settings for
'   EnsureConfigKey.
'
' Why it exists:
'   The intake station needs to know which delivery list and stage it is
'   scanning before accepting any input.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub EnsureConfigKey(ByVal configKey As String, ByVal defaultValue As String)
    If Len(GetConfigValue(configKey, vbNullString)) = 0 Then
        SetConfigValue configKey, defaultValue
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: ProcessorStatusAllowsScanning
' Scope: Private Function
'
' What it does:
'   Uses the selected delivery list's cached master status to decide whether
'   this station should show a master-status warning.
'
' Why it exists:
'   The master marks itself Paused while importing/updating delivery lists or
'   when duplicate-master protection blocks processing. Scanner stations should
'   warn operators about that state, while still allowing local buffered scans
'   to continue.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function ProcessorStatusAllowsScanning(ByVal ws As Worksheet) As Boolean
    Dim statusText As String
    Dim normalizedStatus As String
    Dim warningMessage As String

    statusText = Trim$(CStr(ws.Range(CELL_PROCESSOR_STATUS).Value))
    normalizedStatus = UCase$(statusText)

    If Len(normalizedStatus) = 0 Or normalizedStatus = "ONLINE" Then
        ClearMasterStatusWarningState ws
        ProcessorStatusAllowsScanning = True
        Exit Function
    End If

    Select Case normalizedStatus
        Case "PAUSED"
            warningMessage = "The master is paused. You may keep scanning, but updates will not process until the master is back online. Refresh Snapshot after the master resumes."

        Case "OFFLINE"
            warningMessage = "The master is offline. You may keep scanning, but updates will not process until the master is back online. Refresh Snapshot after the master returns."

        Case "NOT REGISTERED"
            warningMessage = "This delivery list is not registered by an active master. You may keep scanning if this is the correct list, but updates will wait until the master is online."

        Case "NO DELIVERY LIST SELECTED", "SELECT SETTINGS"
            warningMessage = "Choose an online delivery list before scanning."
            SetPanelCell ws, CELL_LAST_QUEUE_STATUS, "Master not ready"
            SetPanelCell ws, CELL_LAST_RESULT_CODE, "MASTER_NOT_READY"
            SetPanelCell ws, CELL_LAST_RESULT_MESSAGE, warningMessage
            SetPanelCell ws, CELL_LAST_SCAN_RESULT, "Selection required"
            Exit Function

        Case Else
            If InStr(1, normalizedStatus, "PAUSED", vbTextCompare) > 0 Or _
               InStr(1, normalizedStatus, "OFFLINE", vbTextCompare) > 0 Or _
               InStr(1, normalizedStatus, "NOT REGISTERED", vbTextCompare) > 0 Then

                warningMessage = "The master is not online. You may keep scanning, but updates will not process until the master is back online. Current master status: " & statusText
            Else
                ClearMasterStatusWarningState ws
                ProcessorStatusAllowsScanning = True
                Exit Function
            End If
    End Select

    SetPanelCell ws, CELL_LAST_QUEUE_STATUS, "Master " & statusText
    SetPanelCell ws, CELL_LAST_RESULT_CODE, "MASTER_NOT_ONLINE_WARNING"
    SetPanelCell ws, CELL_LAST_RESULT_MESSAGE, warningMessage
    SetPanelCell ws, CELL_LAST_SCAN_RESULT, "Scan allowed"

    ApplyStageMasterStatusMarker normalizedStatus

    ProcessorStatusAllowsScanning = True
End Function

Private Sub ApplySelectedMasterStatusWarning(ByVal ws As Worksheet)
    If ws Is Nothing Then Exit Sub
    If Not IsImportedStageLoaded() Then Exit Sub

    ProcessorStatusAllowsScanning ws
End Sub

Private Sub ClearMasterStatusWarningState(ByVal ws As Worksheet)
    ClearStageMasterStatusMarker

    If ws Is Nothing Then Exit Sub
    If StrComp(Trim$(CStr(ws.Range(CELL_LAST_RESULT_CODE).Value)), _
               "MASTER_NOT_ONLINE_WARNING", vbTextCompare) <> 0 Then
        Exit Sub
    End If

    SetPanelCell ws, CELL_LAST_QUEUE_STATUS, "Ready to scan"
    ClearPanelCell ws, CELL_LAST_RESULT_CODE
    SetPanelCell ws, CELL_LAST_SCAN_RESULT, "Ready"
    ClearPanelCell ws, CELL_LAST_RESULT_MESSAGE
End Sub

'------------------------------------------------------------------------------
' Procedure: ValidatePanelReady
' Scope: Private Function
'
' What it does:
'   Checks whether the intake workbook is safe to accept a scan right now:
'   selection exists, snapshot is loaded, revision is current, buffer is not
'   busy, queue poll is not busy, and no alert is active.
'
' Why it exists:
'   This is the main guardrail before scans are accepted. It blocks scans for
'   true local safety issues, while stale snapshots and paused/offline masters
'   stay warning-only so operators can keep scanning into the local buffer.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function ValidatePanelReady(ByVal ws As Worksheet) As Boolean

    If IsScanAlertActive() Then
        SetPanelCell ws, CELL_LAST_QUEUE_STATUS, "Alert active"
        SetPanelCell ws, CELL_LAST_RESULT_CODE, "ALERT_ACTIVE"
        SetPanelCell ws, CELL_LAST_RESULT_MESSAGE, "Clear the active alert before scanning again."
        SetPanelCell ws, CELL_LAST_SCAN_RESULT, "Stopped"

        ClearStageScanBoxSilently
        Exit Function
    End If
    
    If Len(GetSelectedDeliveryKey()) = 0 Then
        ws.Range(CELL_LAST_QUEUE_STATUS).Value = "Selection required"
        ws.Range(CELL_LAST_RESULT_CODE).Value = "NO_LIST"
        ws.Range(CELL_LAST_RESULT_MESSAGE).Value = "Click Change Settings and choose an online delivery list."
        ws.Range(CELL_LAST_SCAN_RESULT).Value = "Selection required"
        Exit Function
    End If

    If Len(ModeFromStageProfile(GetSelectedStageProfile())) = 0 Then
        ws.Range(CELL_LAST_QUEUE_STATUS).Value = "Selection required"
        ws.Range(CELL_LAST_RESULT_CODE).Value = "NO_MODE"
        ws.Range(CELL_LAST_RESULT_MESSAGE).Value = "Click Change Settings and choose a stage."
        ws.Range(CELL_LAST_SCAN_RESULT).Value = "Selection required"
        Exit Function
    End If

    If Len(GetStationName()) = 0 Then
        ws.Range(CELL_LAST_QUEUE_STATUS).Value = "Selection required"
        ws.Range(CELL_LAST_RESULT_CODE).Value = "NO_STATION"
        ws.Range(CELL_LAST_RESULT_MESSAGE).Value = "Scanner station profile is blank."
        ws.Range(CELL_LAST_SCAN_RESULT).Value = "Selection required"
        Exit Function
    End If

    If Not IsImportedStageLoaded Then
        ws.Range(CELL_LAST_QUEUE_STATUS).Value = "Stage not loaded"
        ws.Range(CELL_LAST_RESULT_CODE).Value = "NO_STAGE"
        ws.Range(CELL_LAST_RESULT_MESSAGE).Value = "Click Change Settings and load a stage snapshot first."
        ws.Range(CELL_LAST_SCAN_RESULT).Value = "Stage not loaded"
        Exit Function
    End If

    If IsMasterCheckBusy() Then
    SetPanelCell ws, CELL_LAST_QUEUE_STATUS, "Update check running"
    SetPanelCell ws, CELL_LAST_RESULT_CODE, "MASTER_CHECK_RUNNING"
    SetPanelCell ws, CELL_LAST_RESULT_MESSAGE, _
        "Checking for master updates in the background. Scanning is still allowed."
    SetPanelCell ws, CELL_LAST_SCAN_RESULT, "Scan allowed"

    'Do not exit. Scanning must continue even while the revision check is running.
End If

    If Not ValidateLoadedRevision(ws) Then Exit Function
    If Not ProcessorStatusAllowsScanning(ws) Then Exit Function

    If IsBufferFlushBusy() Then
        ws.Range(CELL_LAST_QUEUE_STATUS).Value = "Please wait"
        ws.Range(CELL_LAST_RESULT_CODE).Value = "BUFFER_BUSY"
        ws.Range(CELL_LAST_RESULT_MESSAGE).Value = "Buffered scans are currently being sent to the master. Wait for the send to finish."
        ws.Range(CELL_LAST_SCAN_RESULT).Value = "Busy"

        ShowBlockedScanWarning
        Exit Function
    End If

    If IsQueueStatusBusy() Then
        ws.Range(CELL_LAST_QUEUE_STATUS).Value = "Please wait"
        ws.Range(CELL_LAST_RESULT_CODE).Value = "QUEUE_STATUS_BUSY"
        ws.Range(CELL_LAST_RESULT_MESSAGE).Value = "Queue status is being checked. Please wait until the processing screen closes."
        ws.Range(CELL_LAST_SCAN_RESULT).Value = "Busy"

        ShowProcessingNotice "Checking queue status. Please wait."
        Exit Function
    End If

    ValidatePanelReady = True
End Function

'------------------------------------------------------------------------------
' Procedure: SubmitQueuedScanFromBox
' Scope: Public Sub
'
' What it does:
'   Reads the barcode from the active stage scan box, validates it locally,
'   applies the scan to the imported snapshot, buffers the request, marks the
'   row as waiting for master confirmation, and clears/refocuses the scan box.
'
' Why it exists:
'   Operators need immediate feedback even though the master processes the
'   final SharePoint queue request later. Local application plus buffering
'   keeps scanning fast and traceable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub SubmitQueuedScanFromBox()
    Dim ws As Worksheet
    Dim scanCell As Range
    Dim barcodeText As String
    Dim requestId As String
    Dim ord As Long
    Dim itm As Long
    Dim checkText As String
    Dim localMessage As String
    Dim importedRow As Long
    Dim recoveryMessage As String

    Set ws = StationSheet()

    If Not ValidatePanelReady(ws) Then
        ClearStageScanBoxSilently
        Exit Sub
    End If

    Set scanCell = GetStageScanBoxCell()
    If scanCell Is Nothing Then
        UpdatePanelForLocalError "NO_SCAN_BOX", "Could not determine the stage scan box."
        ClearStageScanBoxSilently
        Exit Sub
    End If

    barcodeText = CleanBarcodeText(CStr(scanCell.Value))

    If Len(barcodeText) = 0 Then
        ws.Range(CELL_LAST_QUEUE_STATUS).Value = "No scan entered"
        ClearStageScanBoxSilently
        Exit Sub
    End If

    If Not TryRecoverBarcodeForCurrentSnapshot(barcodeText, barcodeText, ord, itm, recoveryMessage) Then
        UpdatePanelForLocalError "BAD_FORMAT", _
            "Scan could not be read. Expected T200 + 12 digits, or enough order/item digits to match the loaded delivery list."
        ClearStageScanBoxSilently
        Exit Sub
    End If

    If Not LocalPrevalidateAndApplyBarcode(barcodeText, checkText, localMessage) Then
        UpdatePanelForLocalError "LOCAL_ERROR", BuildOrderItemErrorText(ord, itm, localMessage)
        ClearStageScanBoxSilently
        Exit Sub
    End If

    If Len(recoveryMessage) > 0 Then
        If Len(localMessage) > 0 Then
            localMessage = recoveryMessage & " " & localMessage
        Else
            localMessage = recoveryMessage
        End If
    End If

    'Show local success immediately.
    UpdatePreviewFromBarcode barcodeText, ord, itm, 1, Now, checkText, localMessage

    requestId = BuildRequestId(GetStationName())

    On Error GoTo BufferErr

    'Only buffer here.
    'Do NOT flush, poll, or show the processing screen from this scan procedure.
    BufferBarcodeRequest requestId, barcodeText, ord, itm

    importedRow = FindImportedRowForOrderItem(ord, itm)

    MarkImportedRowPendingMaster importedRow, requestId, "Buffered locally"

    ws.Range(CELL_LAST_REQUEST).Value = requestId
    ws.Range(CELL_LAST_QUEUE_STATUS).Value = "Buffered locally"
    ws.Range(CELL_LAST_RESULT_CODE).Value = vbNullString
    ws.Range(CELL_LAST_RESULT_MESSAGE).Value = "Scan is buffered locally and waiting to be sent to the shared ScanQueue."
    ws.Range(CELL_LAST_SCAN_RESULT).Value = checkText

'Clear the scan input so the same barcode cannot be submitted again by Enter/double-click.
ClearStageScanBoxSilently

'For Indian Trail receiving, show the bay from SharePoint immediately.
'Do not wait for the master final queue response.
ShowImmediateIndianTrailBayPopupFromAssignmentList ord, itm

If Not IsScanAlertActive() Then
    FocusScanBoxAndCenterRow importedRow
End If

Exit Sub

BufferErr:
    ClearStageScanBoxSilently
    UpdatePanelForLocalError "BUFFER_ERROR", "Buffer write failed: " & Err.Description
End Sub

'------------------------------------------------------------------------------
' Procedure: SubmitQueuedManualFromPrompt
' Scope: Public Sub
'
' What it does:
'   Collects manual order/item/quantity/comment input with Excel prompts,
'   validates it, applies it locally, and buffers it to the queue.
'
' Why it exists:
'   Manual entry is the fallback for missed/damaged labels, so it follows the
'   same queue/audit path as barcode scans instead of bypassing the system.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub SubmitQueuedManualFromPrompt()
    Dim ws As Worksheet
    Dim ord As Variant
    Dim itm As Variant
    Dim qty As Variant
    Dim commentText As String
    Dim requestId As String
    Dim checkText As String
    Dim localMessage As String

    Set ws = StationSheet()

    If Not ValidatePanelReady(ws) Then Exit Sub

    ord = Application.InputBox("Order Number", "Manual Scan Entry", Type:=1)
    If VarType(ord) = vbBoolean Then Exit Sub

    itm = Application.InputBox("Item Number", "Manual Scan Entry", Type:=1)
    If VarType(itm) = vbBoolean Then Exit Sub

    qty = Application.InputBox("Quantity", "Manual Scan Entry", 1, Type:=1)
    If VarType(qty) = vbBoolean Then Exit Sub

    commentText = Trim$(InputBox("Optional comment for this manual scan:", "Manual Scan Comment"))

    If CLng(ord) < 1 Or CLng(itm) < 1 Or CLng(qty) < 1 Then
        UpdatePanelForLocalError "BAD_INPUT", "Order, item, and qty must all be greater than 0."
        Exit Sub
    End If

    If Not LocalPrevalidateAndApplyManual(CLng(ord), CLng(itm), CLng(qty), commentText, checkText, localMessage) Then
    UpdatePanelForLocalError "LOCAL_ERROR", BuildOrderItemErrorText(CLng(ord), CLng(itm), localMessage)
    Exit Sub
End If

    requestId = BuildRequestId(GetStationName())

    BufferManualRequest requestId, CLng(ord), CLng(itm), CLng(qty), BuildQueuedManualComment(commentText)
    
    SetImportedRowQueueState CLng(ord), CLng(itm), requestId, "Queued"

    ws.Range(CELL_LAST_REQUEST).Value = requestId
    ws.Range(CELL_LAST_QUEUE_STATUS).Value = "Buffered locally"
    ws.Range(CELL_LAST_RESULT_CODE).Value = vbNullString
    ws.Range(CELL_LAST_RESULT_MESSAGE).Value = "Manual scan applied locally and queued for background flush."
    ws.Range(CELL_LAST_SCAN_RESULT).Value = checkText
End Sub

'------------------------------------------------------------------------------
' Procedure: SubmitQueuedManualFromSharedFormData
' Scope: Public Sub
'
' What it does:
'   Receives manual scan values from the shared UserForm, validates/applies
'   them locally, and buffers the manual request.
'
' Why it exists:
'   This keeps the modern manual scan form using the same business rules as
'   the simpler prompt-based fallback.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub SubmitQueuedManualFromSharedFormData(ByVal ord As Long, ByVal itm As Long, ByVal qty As Long, Optional ByVal commentText As String = vbNullString)
    Dim ws As Worksheet
    Dim requestId As String
    Dim checkText As String
    Dim localMessage As String

    Set ws = StationSheet()

    If Not ValidatePanelReady(ws) Then Exit Sub

    If ord < 1 Or itm < 1 Or qty < 1 Then
        UpdatePanelForLocalError "BAD_INPUT", "Order, item, and qty must all be greater than 0."
        Exit Sub
    End If

    If Not LocalPrevalidateAndApplyManual(ord, itm, qty, commentText, checkText, localMessage) Then
        UpdatePanelForLocalError "LOCAL_ERROR", BuildOrderItemErrorText(ord, itm, localMessage)
        Exit Sub
    End If

    requestId = BuildRequestId(GetStationName())

    BufferManualRequest requestId, ord, itm, qty, BuildQueuedManualComment(commentText)
    
    SetImportedRowQueueState ord, itm, requestId, "Queued"

    ws.Range(CELL_LAST_REQUEST).Value = requestId
    ws.Range(CELL_LAST_QUEUE_STATUS).Value = "Buffered locally"
    ws.Range(CELL_LAST_RESULT_CODE).Value = vbNullString
    ws.Range(CELL_LAST_RESULT_MESSAGE).Value = "Manual scan applied locally and queued for background flush."
    ws.Range(CELL_LAST_SCAN_RESULT).Value = checkText
End Sub

'------------------------------------------------------------------------------
' Procedure: BuildQueuedManualComment
' Scope: Private Function
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   BuildQueuedManualComment.
'
' Why it exists:
'   The intake station must keep local buffer state, SharePoint queue state,
'   and master final results synchronized without blocking scanning.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function BuildQueuedManualComment(ByVal commentText As String) As String
    commentText = Trim$(CStr(commentText))

    If Len(commentText) > 0 Then
        BuildQueuedManualComment = "Manual: " & commentText
    Else
        BuildQueuedManualComment = "Manual"
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: IncrementMissingStatusCount
' Scope: Private Function
'
' What it does:
'   Calculates, stores, formats, or displays status/result state for
'   IncrementMissingStatusCount.
'
' Why it exists:
'   The operator needs to know whether a scan is local, queued, processing,
'   done, errored, or waiting for master confirmation.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function IncrementMissingStatusCount(ByVal requestId As String) As Long
    requestId = Trim$(CStr(requestId))

    If StrComp(mLastStatusMissingRequestId, requestId, vbTextCompare) <> 0 Then
        mLastStatusMissingRequestId = requestId
        mLastStatusMissingCount = 0
    End If

    mLastStatusMissingCount = mLastStatusMissingCount + 1
    IncrementMissingStatusCount = mLastStatusMissingCount
End Function

'------------------------------------------------------------------------------
' Procedure: ResetMissingStatusCount
' Scope: Private Sub
'
' What it does:
'   Calculates, stores, formats, or displays status/result state for
'   ResetMissingStatusCount.
'
' Why it exists:
'   The operator needs to know whether a scan is local, queued, processing,
'   done, errored, or waiting for master confirmation.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ResetMissingStatusCount(ByVal requestId As String)
    If StrComp(mLastStatusMissingRequestId, Trim$(CStr(requestId)), vbTextCompare) = 0 Then
        mLastStatusMissingCount = 0
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: RefreshLastRequestStatus
' Scope: Public Sub
'
' What it does:
'   Looks up the latest SharePoint status for the most recent request ID,
'   updates the panel, updates the imported row queue state, and handles final
'   Done/Error results.
'
' Why it exists:
'   The intake station needs to know when the master has accepted, rejected,
'   or requires override review for scans that were already buffered locally.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub RefreshLastRequestStatus()
    Dim ws As Worksheet
    Dim requestId As String
    Dim item As Object

    Dim statusText As String
    Dim resultCode As String
    Dim resultMessage As String
    Dim compactMessage As String

    Dim ord As Long
    Dim itm As Long
    
    If IsScanAlertActive() Then
        CancelStationPoll
        HideProcessingNotice
        Exit Sub
    End If
    
    Set ws = StationSheet()
    If ws Is Nothing Then Exit Sub

    requestId = Trim$(CStr(ws.Range(CELL_LAST_REQUEST).Value))
    If Len(requestId) = 0 Then Exit Sub

    Set item = PA_QueueGetRequestStatus(requestId)

    If item Is Nothing Then
        If HasPendingQueueRows() Then
            ws.Range(CELL_LAST_QUEUE_STATUS).Value = "Local"
            ws.Range(CELL_LAST_RESULT_MESSAGE).Value = "Scan is still local and has not been sent to SharePoint yet."
            ScheduleStationPoll STATION_POLL_REPEAT_SECONDS
            Exit Sub
        End If

        If IncrementMissingStatusCount(requestId) >= 4 Then
            ws.Range(CELL_LAST_QUEUE_STATUS).Value = "Missing"
            ws.Range(CELL_LAST_RESULT_CODE).Value = "QUEUE_LOOKUP_MISSING"
            ws.Range(CELL_LAST_RESULT_MESSAGE).Value = _
                "[MASTER FINAL] SharePoint status lookup could not find this request ID."

            MsgBox "The intake sent this scan, but the SharePoint status lookup cannot find it." & vbCrLf & vbCrLf & _
                   "RequestId:" & vbCrLf & requestId, _
                   vbExclamation, "Queue Status Missing"

            Exit Sub
        End If

        ws.Range(CELL_LAST_QUEUE_STATUS).Value = "Queued"
        ws.Range(CELL_LAST_RESULT_MESSAGE).Value = "Waiting for SharePoint queue status."

        ScheduleStationPoll STATION_POLL_REPEAT_SECONDS
        Exit Sub
    End If

    ResetMissingStatusCount requestId

    statusText = Trim$(PA_DictText(item, "status"))
    resultCode = Trim$(PA_DictText(item, "resultCode"))
    resultMessage = Trim$(PA_DictText(item, "resultMessage"))
    compactMessage = CompactQueueResultMessage(resultMessage)

    If Len(statusText) = 0 Then statusText = "Queued"

    ord = CLng(Val(PA_DictText(item, "orderNumber")))
    itm = CLng(Val(PA_DictText(item, "itemNumber")))

    If ord > 0 And itm > 0 Then
        SetImportedRowQueueState ord, itm, requestId, statusText, compactMessage
    End If

    If StrComp(statusText, "Done", vbTextCompare) = 0 Or _
       StrComp(statusText, "Error", vbTextCompare) = 0 Then

        If Len(compactMessage) = 0 Then
            compactMessage = "Master returned status: " & statusText
        End If

        UpdateImportedRowFromRequestItem item
        UpdatePanelFromRequestItem item
        HandleCompletedRequestFromItem item

        Exit Sub
    End If

    UpdatePanelFromRequestItem item
    ScheduleStationPoll STATION_POLL_REPEAT_SECONDS
End Sub

'------------------------------------------------------------------------------
' Procedure: UpdatePanelFromRequestRow
' Scope: Private Sub
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   UpdatePanelFromRequestRow.
'
' Why it exists:
'   The intake station must keep local buffer state, SharePoint queue state,
'   and master final results synchronized without blocking scanning.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub UpdatePanelFromRequestRow(ByVal qWs As Worksheet, ByVal rowNum As Long)
    Dim ws As Worksheet
    Dim reqType As String
    Dim barcodeText As String
    Dim ord As Long
    Dim itm As Long
    Dim qty As Long
    Dim queuedAt As Variant
    Dim processedAt As Variant
    Dim statusText As String
    Dim resultCode As String
    Dim resultMessage As String
    Dim requestComment As String

    Set ws = StationSheet()

    reqType = UCase$(Trim$(CStr(qWs.Cells(rowNum, 3).Value)))
    barcodeText = Trim$(CStr(qWs.Cells(rowNum, 4).Value))
    ord = CLng(Val(qWs.Cells(rowNum, 6).Value))
    itm = CLng(Val(qWs.Cells(rowNum, 7).Value))
    qty = CLng(Val(qWs.Cells(rowNum, 8).Value))
    queuedAt = qWs.Cells(rowNum, 11).Value
    processedAt = qWs.Cells(rowNum, 13).Value
    statusText = Trim$(CStr(qWs.Cells(rowNum, 12).Value))
    resultCode = Trim$(CStr(qWs.Cells(rowNum, 14).Value))
    resultMessage = Trim$(CStr(qWs.Cells(rowNum, 15).Value))
    requestComment = Trim$(CStr(qWs.Cells(rowNum, 16).Value))

    If reqType = "BARCODE" Then
        If ord = 0 Then ord = DecodeBarcodeOrder(barcodeText)
        If itm = 0 Then itm = DecodeBarcodeItem(barcodeText)
        If qty = 0 Then qty = 1

        UpdatePreviewFromBarcode _
            barcodeText, ord, itm, qty, _
            PickBestScanTime(queuedAt, processedAt), _
            DeriveCheckDisplay(statusText, resultCode, resultMessage), _
            BuildPanelCommentText(reqType, requestComment, resultMessage, statusText)

    ElseIf reqType = "MANUAL" Then
        If qty = 0 Then qty = 1

        UpdatePreviewFromManual _
            ord, itm, qty, _
            PickBestScanTime(queuedAt, processedAt), _
            DeriveCheckDisplay(statusText, resultCode, resultMessage), _
            BuildPanelCommentText(reqType, requestComment, resultMessage, statusText)
    End If

    ws.Range(CELL_LAST_QUEUE_STATUS).Value = statusText
    ws.Range(CELL_LAST_RESULT_CODE).Value = resultCode
    ws.Range(CELL_LAST_SCAN_RESULT).Value = DeriveLastScanResult(statusText, resultCode, resultMessage)
    ws.Range(CELL_LAST_RESULT_MESSAGE).Value = resultMessage
End Sub

'------------------------------------------------------------------------------
' Procedure: PickBestScanTime
' Scope: Private Function
'
' What it does:
'   Cleans, validates, decodes, applies, focuses, or displays scan/barcode
'   data for PickBestScanTime.
'
' Why it exists:
'   The scanner acts like a keyboard, so the workbook must turn entered text
'   into safe order/item updates without duplicate submissions.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function PickBestScanTime(ByVal queuedAt As Variant, ByVal processedAt As Variant) As Variant
    If IsDate(processedAt) Then
        PickBestScanTime = processedAt
    ElseIf IsDate(queuedAt) Then
        PickBestScanTime = queuedAt
    Else
        PickBestScanTime = Now
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: DeriveLastScanResult
' Scope: Private Function
'
' What it does:
'   Cleans, validates, decodes, applies, focuses, or displays scan/barcode
'   data for DeriveLastScanResult.
'
' Why it exists:
'   The scanner acts like a keyboard, so the workbook must turn entered text
'   into safe order/item updates without duplicate submissions.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function DeriveLastScanResult(ByVal statusText As String, ByVal resultCode As String, ByVal resultMessage As String) As String
    If StrComp(statusText, "Queued", vbTextCompare) = 0 Or StrComp(statusText, "Processing", vbTextCompare) = 0 Then
        DeriveLastScanResult = statusText
    ElseIf Len(Trim$(resultMessage)) > 0 Then
        DeriveLastScanResult = resultMessage
    ElseIf Len(Trim$(resultCode)) > 0 Then
        DeriveLastScanResult = resultCode
    Else
        DeriveLastScanResult = statusText
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: DeriveCheckDisplay
' Scope: Private Function
'
' What it does:
'   Performs the intake-workbook step named DeriveCheckDisplay inside
'   modIntakeStation.
'
' Why it exists:
'   The intake workbook acts like a scanner front end; this module coordinates
'   the operator UI with local validation, buffering, SharePoint queue status,
'   and master snapshot freshness.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function DeriveCheckDisplay(ByVal statusText As String, ByVal resultCode As String, ByVal resultMessage As String) As String
    Dim msgUpper As String

    msgUpper = UCase$(Trim$(resultMessage))

    If StrComp(statusText, "Queued", vbTextCompare) = 0 Or StrComp(statusText, "Processing", vbTextCompare) = 0 Then
        DeriveCheckDisplay = statusText
    ElseIf Left$(msgUpper, 7) = "PARTIAL" Then
        DeriveCheckDisplay = resultMessage
    ElseIf Len(Trim$(resultCode)) > 0 Then
        DeriveCheckDisplay = resultCode
    ElseIf Len(Trim$(resultMessage)) > 0 Then
        DeriveCheckDisplay = resultMessage
    Else
        DeriveCheckDisplay = statusText
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: BuildPanelCommentText
' Scope: Private Function
'
' What it does:
'   Builds, formats, or updates the intake operator panel/buttons for
'   BuildPanelCommentText.
'
' Why it exists:
'   The panel is the operator-facing part of the workbook; consistent buttons
'   and status cells reduce scanning mistakes.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function BuildPanelCommentText(ByVal reqType As String, ByVal requestComment As String, ByVal resultMessage As String, ByVal statusText As String) As String
    requestComment = Trim$(requestComment)
    resultMessage = Trim$(resultMessage)

    If UCase$(reqType) = "MANUAL" Then
        If Len(requestComment) > 0 Then
            BuildPanelCommentText = requestComment
        Else
            BuildPanelCommentText = "Manual scan entered from Scanning Panel"
        End If
    ElseIf Len(requestComment) > 0 Then
        BuildPanelCommentText = requestComment
    ElseIf StrComp(statusText, "Error", vbTextCompare) = 0 Then
        BuildPanelCommentText = resultMessage
    Else
        BuildPanelCommentText = vbNullString
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: UpdatePreviewFromBarcode
' Scope: Private Sub
'
' What it does:
'   Cleans, validates, decodes, applies, focuses, or displays scan/barcode
'   data for UpdatePreviewFromBarcode.
'
' Why it exists:
'   The scanner acts like a keyboard, so the workbook must turn entered text
'   into safe order/item updates without duplicate submissions.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub UpdatePreviewFromBarcode(ByVal barcodeText As String, ByVal ord As Long, ByVal itm As Long, ByVal qty As Long, ByVal scanTime As Variant, ByVal checkText As String, ByVal commentText As String)
    ClearPanelPreviewRow

    With StationSheet()
        .Range(CELL_LAST_SCAN_RESULT).Value = checkText
        .Range(CELL_LAST_RESULT_MESSAGE).Value = commentText
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: UpdatePreviewFromManual
' Scope: Private Sub
'
' What it does:
'   Handles manual scan entry or manual scan state for
'   UpdatePreviewFromManual.
'
' Why it exists:
'   Manual entry is necessary when a label cannot be scanned, but it must
'   still follow the same validation, buffering, and audit path.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub UpdatePreviewFromManual(ByVal ord As Long, ByVal itm As Long, ByVal qty As Long, ByVal scanTime As Variant, ByVal checkText As String, ByVal commentText As String)
    ClearPanelPreviewRow

    With StationSheet()
        .Range(CELL_LAST_SCAN_RESULT).Value = checkText
        .Range(CELL_LAST_RESULT_MESSAGE).Value = commentText
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: UpdatePanelForLocalError
' Scope: Public Sub
'
' What it does:
'   Builds, formats, or updates the intake operator panel/buttons for
'   UpdatePanelForLocalError.
'
' Why it exists:
'   The panel is the operator-facing part of the workbook; consistent buttons
'   and status cells reduce scanning mistakes.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub UpdatePanelForLocalError(ByVal codeText As String, ByVal messageText As String)
    ClearPanelPreviewRow

    With StationSheet()
        .Range(CELL_LAST_QUEUE_STATUS).Value = "Local validation failed"
        .Range(CELL_LAST_RESULT_CODE).Value = codeText
        .Range(CELL_LAST_RESULT_MESSAGE).Value = messageText
        .Range(CELL_LAST_SCAN_RESULT).Value = "Error"
    End With

    ShowScanSafeAlert "Scanning Error", messageText, codeText
End Sub

'------------------------------------------------------------------------------
' Procedure: HandleCompletedRequest
' Scope: Public Sub
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   HandleCompletedRequest.
'
' Why it exists:
'   The intake station must keep local buffer state, SharePoint queue state,
'   and master final results synchronized without blocking scanning.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub HandleCompletedRequest(ByVal requestId As String, _
                                  ByVal statusText As String, _
                                  ByVal resultCode As String, _
                                  ByVal resultMessage As String)
    Dim compactMessage As String

    If StrComp(mLastPopupRequestId, requestId, vbTextCompare) = 0 Then Exit Sub

    compactMessage = CompactQueueResultMessage(resultMessage)

    If StrComp(statusText, "Error", vbTextCompare) = 0 Or _
       (Len(resultCode) > 0 And StrComp(resultCode, "OK", vbTextCompare) <> 0 And UCase$(Left$(compactMessage, 7)) <> "PARTIAL") Then

        ShowScanSafeAlert _
            "Master Scan Error", _
            compactMessage, _
            resultCode
    End If

    mLastPopupRequestId = requestId
End Sub

'------------------------------------------------------------------------------
' Procedure: ClearStationStatus
' Scope: Public Sub
'
' What it does:
'   Reads, writes, validates, or applies scanner station settings for
'   ClearStationStatus.
'
' Why it exists:
'   The intake station needs to know which delivery list and stage it is
'   scanning before accepting any input.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub ClearStationStatus()
    Dim ws As Worksheet
    Set ws = StationSheet()

    On Error GoTo SafeExit
    Application.EnableEvents = False

    ws.Range(CELL_LAST_REQUEST).ClearContents
    ws.Range(CELL_LAST_RESULT_CODE).ClearContents
    ws.Range(CELL_LAST_QUEUE_STATUS).Value = "Idle"
    ws.Range(CELL_LAST_SCAN_RESULT).ClearContents
    ws.Range(CELL_LAST_RESULT_MESSAGE).ClearContents

    ws.Range(CELL_SCAN_BOX).ClearContents
    ws.Range(CELL_PREVIEW_ORDER).ClearContents
    ws.Range(CELL_PREVIEW_ITEM).ClearContents
    ws.Range(CELL_PREVIEW_QTY).ClearContents
    ws.Range(CELL_PREVIEW_TIME).ClearContents
    ws.Range(CELL_PREVIEW_CHECK).ClearContents
    ws.Range(CELL_PREVIEW_COMMENT).ClearContents

SafeExit:
    Application.EnableEvents = True
    FocusScanBox
End Sub

'------------------------------------------------------------------------------
' Procedure: ScheduleStationPoll
' Scope: Public Sub
'
' What it does:
'   Schedules the next intake polling pass with Application.OnTime.
'
' Why it exists:
'   Polling lets the workbook check queue results and revision changes without
'   blocking scanning continuously.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub ScheduleStationPoll(Optional ByVal delaySeconds As Long = -1)
    Dim procName As String

    If Not IsAutoQueuePollEnabled() Then
        CancelStationPoll
        Exit Sub
    End If

    On Error Resume Next

    If delaySeconds < 0 Then
        delaySeconds = STATION_POLL_REPEAT_SECONDS
    End If

    procName = "'" & ThisWorkbook.Name & "'!StationPollBridge"

    If mPollingScheduled Then
        Application.OnTime EarliestTime:=mNextPollTime, _
                           Procedure:=procName, _
                           Schedule:=False
        mPollingScheduled = False
    End If

    mNextPollTime = Now + (delaySeconds / 86400#)
    mPollingScheduled = True

    Application.OnTime EarliestTime:=mNextPollTime, _
                       Procedure:=procName, _
                       Schedule:=True

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: StationPollBridge
' Scope: Public Sub
'
' What it does:
'   Public no-argument OnTime entry point that runs the intake station polling
'   work.
'
' Why it exists:
'   Application.OnTime cannot call procedures with arguments, so this bridge
'   safely connects the timer to the real polling logic.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub StationPollBridge()
    On Error GoTo ErrHandler

    'This scheduled run has now fired.
    mPollingScheduled = False

    'If a scanner-safe alert is active, queue polling must stop completely.
    'Do not show the processing form and do not update queue status.
    If IsScanAlertActive() Then
        CancelStationPoll
        HideProcessingNotice
        mQueueStatusBusy = False
        Exit Sub
    End If

    'Do not let SharePoint queue polling interrupt rapid scanning.
    If RapidScanBufferShouldDeferQueuePolling() Then
        CancelStationPoll
        HideProcessingNotice

        On Error Resume Next
        SetPanelCell StationSheet(), CELL_LAST_QUEUE_STATUS, "Buffered locally"
        SetPanelCell StationSheet(), CELL_LAST_RESULT_MESSAGE, _
            CStr(GetPendingQueueRowCount()) & " scan(s) waiting to send."
        On Error GoTo ErrHandler

        FocusStageScanBox
        Exit Sub
    End If

    'Prevent overlapping queue-status checks.
    If mQueueStatusBusy Then
        If HasActiveQueueWatchRequests() And Not IsScanAlertActive() Then
            ScheduleStationPoll STATION_POLL_REPEAT_SECONDS
        Else
            ResetQueuePollFallbackForNewWork
            CancelStationPoll
        End If

        Exit Sub
    End If

    'If there is nothing waiting for a master result, stop queue polling.
    If Not HasActiveQueueWatchRequests() Then
        ResetQueuePollFallbackForNewWork
        CancelStationPoll
        HideProcessingNotice

        On Error Resume Next
        SetPanelCell StationSheet(), CELL_LAST_QUEUE_STATUS, "Ready to scan"
        On Error GoTo ErrHandler

        FocusStageScanBox
        Exit Sub
    End If

    mQueueStatusBusy = True

    'Check again before showing the processing form.
    If IsScanAlertActive() Then GoTo SafeExitAlert

    ShowProcessingNotice "Checking queue status. Please wait."
    DoEvents

    If IsScanAlertActive() Then GoTo SafeExitAlert

    If HasPendingQueueRows() Then
        FlushPendingQueueRows 25

        If RapidScanBufferShouldDeferQueuePolling() Or IsScanAlertActive() Then
            GoTo SafeExitNoReschedule
        End If
    End If

    RefreshLastRequestStatus

    If IsScanAlertActive() Then GoTo SafeExitAlert

    RefreshPendingImportedQueueStates False

SafeExit:
    HideProcessingNotice
    mQueueStatusBusy = False
    FocusStageScanBox

    If IsScanAlertActive() Then
        CancelStationPoll
    Else
        ScheduleNextQueueStatusPollAfterCheck
    End If

    Exit Sub

SafeExitAlert:
    HideProcessingNotice
    mQueueStatusBusy = False
    CancelStationPoll
    Exit Sub

SafeExitNoReschedule:
    HideProcessingNotice
    mQueueStatusBusy = False
    FocusStageScanBox

    CancelStationPoll
    RefreshBufferedCountUi

    Exit Sub

ErrHandler:
    On Error Resume Next
    StationSheet.Range(CELL_LAST_QUEUE_STATUS).Value = "PA Fail"
    StationSheet.Range(CELL_LAST_RESULT_CODE).Value = "POLL_ERROR"
    StationSheet.Range(CELL_LAST_RESULT_MESSAGE).Value = "Queue poll failed: " & Err.Description
    On Error GoTo 0

    Resume SafeExit
End Sub

'------------------------------------------------------------------------------
' Procedure: HasActiveQueueWatchRequests
' Scope: Private Function
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   HasActiveQueueWatchRequests.
'
' Why it exists:
'   The intake station must keep local buffer state, SharePoint queue state,
'   and master final results synchronized without blocking scanning.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function HasActiveQueueWatchRequests() As Boolean
    Dim ws As Worksheet
    Dim requestId As String
    Dim localStatus As String
    Dim localMessage As String

    Set ws = StationSheet()
    If ws Is Nothing Then Exit Function

    requestId = Trim$(CStr(ws.Range(CELL_LAST_REQUEST).Value))
    localStatus = UCase$(Trim$(CStr(ws.Range(CELL_LAST_QUEUE_STATUS).Value)))
    localMessage = UCase$(Trim$(CStr(ws.Range(CELL_LAST_RESULT_MESSAGE).Value)))

    If Len(requestId) > 0 Then
        If Not ((localStatus = "DONE" Or localStatus = "ERROR") And Left$(localMessage, 14) = "[MASTER FINAL]") Then
            HasActiveQueueWatchRequests = True
            Exit Function
        End If
    End If

    HasActiveQueueWatchRequests = HasImportedActiveQueueRequests()
End Function

'------------------------------------------------------------------------------
' Procedure: CleanBarcodeText
' Scope: Public Function
'
' What it does:
'   Cleans, validates, decodes, applies, focuses, or displays scan/barcode
'   data for CleanBarcodeText.
'
' Why it exists:
'   The scanner acts like a keyboard, so the workbook must turn entered text
'   into safe order/item updates without duplicate submissions.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function CleanBarcodeText(ByVal rawText As String) As String
    rawText = Replace$(rawText, vbCr, vbNullString)
    rawText = Replace$(rawText, vbLf, vbNullString)
    rawText = Replace$(rawText, vbTab, vbNullString)
    rawText = Replace$(rawText, " ", vbNullString)
    CleanBarcodeText = UCase$(Trim$(rawText))
End Function

'------------------------------------------------------------------------------
' Procedure: IsValidBarcode
' Scope: Public Function
'
' What it does:
'   Cleans, validates, decodes, applies, focuses, or displays scan/barcode
'   data for IsValidBarcode.
'
' Why it exists:
'   The scanner acts like a keyboard, so the workbook must turn entered text
'   into safe order/item updates without duplicate submissions.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function IsValidBarcode(ByVal barcodeText As String) As Boolean
    Dim ord As Long
    Dim itm As Long
    Dim canonicalBarcode As String

    IsValidBarcode = TryDecodeBarcodeText(barcodeText, ord, itm, canonicalBarcode)
End Function

'------------------------------------------------------------------------------
' Procedure: DecodeBarcodeOrder
' Scope: Public Function
'
' What it does:
'   Cleans, validates, decodes, applies, focuses, or displays scan/barcode
'   data for DecodeBarcodeOrder.
'
' Why it exists:
'   The scanner acts like a keyboard, so the workbook must turn entered text
'   into safe order/item updates without duplicate submissions.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function DecodeBarcodeOrder(ByVal barcodeText As String) As Long
    Dim itm As Long
    Dim canonicalBarcode As String

    Call TryDecodeBarcodeText(barcodeText, DecodeBarcodeOrder, itm, canonicalBarcode)
End Function

'------------------------------------------------------------------------------
' Procedure: DecodeBarcodeItem
' Scope: Public Function
'
' What it does:
'   Cleans, validates, decodes, applies, focuses, or displays scan/barcode
'   data for DecodeBarcodeItem.
'
' Why it exists:
'   The scanner acts like a keyboard, so the workbook must turn entered text
'   into safe order/item updates without duplicate submissions.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function DecodeBarcodeItem(ByVal barcodeText As String) As Long
    Dim ord As Long
    Dim canonicalBarcode As String

    Call TryDecodeBarcodeText(barcodeText, ord, DecodeBarcodeItem, canonicalBarcode)
End Function

Private Function TryRecoverBarcodeForCurrentSnapshot(ByVal rawBarcode As String, _
                                                     ByRef canonicalBarcode As String, _
                                                     ByRef orderNumber As Long, _
                                                     ByRef itemNumber As Long, _
                                                     ByRef recoveryMessage As String) As Boolean
    Dim cleanText As String
    Dim digitsOnly As String
    Dim i As Long
    Dim candidateText As String
    Dim candidateOrder As Long
    Dim candidateItem As Long
    Dim inferredOrder As Long

    cleanText = CleanBarcodeText(rawBarcode)
    recoveryMessage = vbNullString

    If TryDecodeBarcodeText(cleanText, orderNumber, itemNumber, canonicalBarcode) Then
        TryRecoverBarcodeForCurrentSnapshot = True
        Exit Function
    End If

    digitsOnly = BarcodeDigitsOnly(cleanText)

    For i = 1 To Len(digitsOnly) - 11
        candidateText = Mid$(digitsOnly, i, 12)
        candidateOrder = CLng(Val(Left$(candidateText, 6)))
        candidateItem = CLng(Val(Mid$(candidateText, 7, 3)))

        If candidateOrder > 0 And candidateItem > 0 Then
            If FindImportedRowForOrderItem(candidateOrder, candidateItem) > 0 Then
                orderNumber = candidateOrder
                itemNumber = candidateItem
                canonicalBarcode = CanonicalBarcodeText(orderNumber, itemNumber)
                recoveryMessage = "Recovered damaged label as Order " & orderNumber & " / Item " & Format$(itemNumber, "000") & "."
                TryRecoverBarcodeForCurrentSnapshot = True
                Exit Function
            End If
        End If
    Next i

    For i = 1 To Len(digitsOnly) - 8
        candidateText = Mid$(digitsOnly, i, 9)
        candidateItem = CLng(Val(Mid$(candidateText, 4, 3)))

        If candidateItem > 0 Then
            If TryFindImportedOrderBySuffixItem(Left$(candidateText, 3), candidateItem, inferredOrder) Then
                orderNumber = inferredOrder
                itemNumber = candidateItem
                canonicalBarcode = CanonicalBarcodeText(orderNumber, itemNumber)
                recoveryMessage = "Recovered damaged label as Order " & orderNumber & " / Item " & Format$(itemNumber, "000") & " from matching delivery-list data."
                TryRecoverBarcodeForCurrentSnapshot = True
                Exit Function
            End If
        End If
    Next i
End Function

Private Function TryDecodeBarcodeText(ByVal barcodeText As String, _
                                      ByRef orderNumber As Long, _
                                      ByRef itemNumber As Long, _
                                      ByRef canonicalBarcode As String) As Boolean
    Dim cleanText As String
    Dim digitsOnly As String
    Dim i As Long
    Dim candidateText As String

    cleanText = CleanBarcodeText(barcodeText)

    If Len(cleanText) = 16 And cleanText Like "T200############" Then
        orderNumber = CLng(Mid$(cleanText, 5, 6))
        itemNumber = CLng(Mid$(cleanText, 11, 3))
        canonicalBarcode = cleanText
        TryDecodeBarcodeText = (orderNumber > 0 And itemNumber > 0)
        Exit Function
    End If

    digitsOnly = BarcodeDigitsOnly(cleanText)

    For i = 1 To Len(digitsOnly) - 11
        candidateText = Mid$(digitsOnly, i, 12)
        orderNumber = CLng(Val(Left$(candidateText, 6)))
        itemNumber = CLng(Val(Mid$(candidateText, 7, 3)))

        If orderNumber > 0 And itemNumber > 0 Then
            canonicalBarcode = CanonicalBarcodeText(orderNumber, itemNumber)
            TryDecodeBarcodeText = True
            Exit Function
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

Private Function TryFindImportedOrderBySuffixItem(ByVal orderSuffix As String, _
                                                  ByVal itemNumber As Long, _
                                                  ByRef orderNumber As Long) As Boolean
    Dim ws As Worksheet
    Dim headerRow As Long
    Dim lastRow As Long
    Dim barcodeCol As Long
    Dim orderCol As Long
    Dim itemCol As Long
    Dim qtyCol As Long
    Dim timeCol As Long
    Dim checkCol As Long
    Dim commentCol As Long
    Dim recentValueCell As Range
    Dim foundCount As Long

    Set ws = StageViewSheet()
    If ws Is Nothing Then Exit Function

    headerRow = GetImportedMainHeaderRow(ws)
    If headerRow = 0 Then Exit Function

    lastRow = ws.Cells(ws.Rows.Count, 5).End(xlUp).Row
    If lastRow <= headerRow Then Exit Function

    If GetModeBlockColumns(ModeFromStageProfile(GetSelectedStageProfile()), _
                           barcodeCol, orderCol, itemCol, qtyCol, timeCol, checkCol, commentCol, recentValueCell) Then
        ScanImportedOrderSuffixBlock ws, headerRow + 1, lastRow, orderCol, itemCol, orderSuffix, itemNumber, orderNumber, foundCount
    End If

    ScanImportedOrderSuffixBlock ws, headerRow + 1, lastRow, 5, 6, orderSuffix, itemNumber, orderNumber, foundCount

    TryFindImportedOrderBySuffixItem = (foundCount = 1 And orderNumber > 0)
End Function

Private Sub ScanImportedOrderSuffixBlock(ByVal ws As Worksheet, _
                                         ByVal firstRow As Long, _
                                         ByVal lastRow As Long, _
                                         ByVal orderCol As Long, _
                                         ByVal itemCol As Long, _
                                         ByVal orderSuffix As String, _
                                         ByVal itemNumber As Long, _
                                         ByRef orderNumber As Long, _
                                         ByRef foundCount As Long)
    Dim r As Long
    Dim rowOrder As Long
    Dim rowItem As Long

    If orderCol <= 0 Or itemCol <= 0 Then Exit Sub

    For r = firstRow To lastRow
        If Not ws.Rows(r).Hidden Then
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
    Next r
End Sub

'------------------------------------------------------------------------------
' Procedure: UpdatePanelFromRequestItem
' Scope: Private Sub
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   UpdatePanelFromRequestItem.
'
' Why it exists:
'   The intake station must keep local buffer state, SharePoint queue state,
'   and master final results synchronized without blocking scanning.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub UpdatePanelFromRequestItem(ByVal item As Object)
    Dim ws As Worksheet
    Dim reqType As String
    Dim barcodeText As String
    Dim ord As Long
    Dim itm As Long
    Dim qty As Long
    Dim queuedAt As Variant
    Dim processedAt As Variant
    Dim statusText As String
    Dim resultCode As String
    Dim resultMessage As String
    Dim requestComment As String
    Dim displayStatus As String
    Dim displayMessage As String

    Set ws = StationSheet()

    reqType = UCase$(Trim$(PA_DictText(item, "requestType")))
    barcodeText = Trim$(PA_DictText(item, "barcode"))
    ord = CLng(Val(PA_DictText(item, "orderNumber")))
    itm = CLng(Val(PA_DictText(item, "itemNumber")))
    qty = CLng(Val(PA_DictText(item, "quantity")))
    queuedAt = PA_ParseIsoDate(PA_DictText(item, "queuedAt"))
    processedAt = PA_ParseIsoDate(PA_DictText(item, "processedAt"))
    statusText = Trim$(PA_DictText(item, "status"))
    resultCode = Trim$(PA_DictText(item, "resultCode"))
    resultMessage = Trim$(PA_DictText(item, "resultMessage"))
    requestComment = Trim$(PA_DictText(item, "requestComment"))

    If Len(statusText) = 0 Then statusText = "Queued"
    If qty = 0 Then qty = 1

    displayStatus = ShortQueueStateText(statusText)
    displayMessage = CompactQueueResultMessage(resultMessage)

    If reqType = "BARCODE" Then
        If ord = 0 Then ord = DecodeBarcodeOrder(barcodeText)
        If itm = 0 Then itm = DecodeBarcodeItem(barcodeText)

        UpdatePreviewFromBarcode _
            barcodeText, ord, itm, qty, _
            PickBestScanTime(queuedAt, processedAt), _
            DeriveCheckDisplay(statusText, resultCode, displayMessage), _
            BuildPanelCommentText(reqType, requestComment, displayMessage, statusText)

    ElseIf reqType = "MANUAL" Then
        UpdatePreviewFromManual _
            ord, itm, qty, _
            PickBestScanTime(queuedAt, processedAt), _
            DeriveCheckDisplay(statusText, resultCode, displayMessage), _
            BuildPanelCommentText(reqType, requestComment, displayMessage, statusText)
    End If

    ws.Range(CELL_LAST_QUEUE_STATUS).Value = displayStatus
    ws.Range(CELL_LAST_RESULT_CODE).Value = resultCode
    ws.Range(CELL_LAST_SCAN_RESULT).Value = DeriveLastScanResult(statusText, resultCode, displayMessage)

    If StrComp(statusText, "Done", vbTextCompare) = 0 Or _
       StrComp(statusText, "Error", vbTextCompare) = 0 Then
        ws.Range(CELL_LAST_RESULT_MESSAGE).Value = "[MASTER FINAL] " & displayMessage
    Else
        ws.Range(CELL_LAST_RESULT_MESSAGE).Value = displayMessage
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: ClearPanelPreviewRow
' Scope: Private Sub
'
' What it does:
'   Builds, formats, or updates the intake operator panel/buttons for
'   ClearPanelPreviewRow.
'
' Why it exists:
'   The panel is the operator-facing part of the workbook; consistent buttons
'   and status cells reduce scanning mistakes.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ClearPanelPreviewRow()
    Dim ws As Worksheet
    Dim wasProtected As Boolean

    Set ws = StationSheet()
    If ws Is Nothing Then Exit Sub

    wasProtected = ws.ProtectContents

    If wasProtected Then
        On Error Resume Next
        ws.Unprotect Password:=""
        On Error GoTo 0
    End If

    ws.Range(CELL_PREVIEW_ORDER).ClearContents
    ws.Range(CELL_PREVIEW_ITEM).ClearContents
    ws.Range(CELL_PREVIEW_QTY).ClearContents
    ws.Range(CELL_PREVIEW_TIME).ClearContents
    ws.Range(CELL_PREVIEW_CHECK).ClearContents
    ws.Range(CELL_PREVIEW_COMMENT).ClearContents

    If wasProtected Then
        On Error Resume Next
        ws.Protect Password:="", UserInterfaceOnly:=True, DrawingObjects:=False, Contents:=True, Scenarios:=True
        On Error GoTo 0
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: RefreshCurrentIntakeSnapshot
' Scope: Public Sub
'
' What it does:
'   Requests/loads a refreshed published snapshot for the currently selected
'   delivery and stage.
'
' Why it exists:
'   Operators need a manual refresh option when the master changes or when
'   automatic revision checks indicate the loaded snapshot is stale.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub RefreshCurrentIntakeSnapshot()
Dim ws As Worksheet
Dim expectedStageSheet As String
Dim loadedStageSheet As String
Dim currentRevisionToken As String
Dim currentRevisionUpdatedAt As String

    Set ws = StationSheet()

    ImportDebugLog "RefreshCurrentIntakeSnapshot", "START", _
                   "SelectedKey=" & GetSelectedDeliveryKey(), _
                   "SelectedDisplay=" & GetSelectedDeliveryDisplay(), _
                   "StageProfile=" & GetSelectedStageProfile()

    If Len(GetSelectedDeliveryKey()) = 0 Then
        ImportDebugLog "RefreshCurrentIntakeSnapshot", "NO_SELECTED_KEY"
        MsgBox "Select a delivery list first.", vbExclamation, "Refresh Snapshot"
        Exit Sub
    End If

    If Len(GetSelectedStageProfile()) = 0 Then
        ImportDebugLog "RefreshCurrentIntakeSnapshot", "NO_STAGE_PROFILE"
        MsgBox "Select a stage first.", vbExclamation, "Refresh Snapshot"
        Exit Sub
    End If
    
    expectedStageSheet = StageSheetFromProfile(GetSelectedStageProfile())
    loadedStageSheet = GetConfigValue(CFG_LOADED_STAGE_SHEET, vbNullString)
    
    If IsBufferFlushBusy() Then
        ImportDebugLog "RefreshCurrentIntakeSnapshot", "BUFFER_BUSY"
        MsgBox "Buffered scans are currently being sent." & vbCrLf & vbCrLf & _
               "Please wait for sending to finish, then click Refresh Snapshot again.", _
               vbExclamation, "Refresh Snapshot"
        Exit Sub
    End If

    If HasPendingQueueRows() Then
        ImportDebugLog "RefreshCurrentIntakeSnapshot", "HAS_PENDING_ROWS"
        If MsgBox("There are still buffered scans waiting to send." & vbCrLf & vbCrLf & _
                  "Do you want to send them now before refreshing?", _
                  vbYesNo + vbQuestion, "Refresh Snapshot") <> vbYes Then
            ImportDebugLog "RefreshCurrentIntakeSnapshot", "USER_ABORTED_PENDING_SEND"
            Exit Sub
        End If

        FlushPendingQueueRows 500

        If HasPendingQueueRows() Or IsBufferFlushBusy() Then
            ImportDebugLog "RefreshCurrentIntakeSnapshot", "PENDING_ROWS_STILL_EXIST"
            MsgBox "Refresh stopped because buffered scans are still not fully sent yet." & vbCrLf & vbCrLf & _
                   "Wait a moment, then click Refresh Snapshot again.", _
                   vbExclamation, "Refresh Snapshot"
            Exit Sub
        End If
    End If
    
        If IsImportedStageLoaded() And StrComp(loadedStageSheet, expectedStageSheet, vbTextCompare) = 0 Then
    If Not ConfirmDiscardUnsavedStageComments("Refresh Snapshot") Then
        ImportDebugLog "RefreshCurrentIntakeSnapshot", "USER_ABORTED_UNSAVED_COMMENTS"
        SetPanelCell ws, CELL_LAST_QUEUE_STATUS, "Refresh cancelled"
        SetPanelCell ws, CELL_LAST_RESULT_CODE, "UNSAVED_COMMENTS"
        SetPanelCell ws, CELL_LAST_SCAN_RESULT, "Cancelled"
        SetPanelCell ws, CELL_LAST_RESULT_MESSAGE, "Refresh was cancelled because comments have not been saved."
        FocusStageScanBox
        Exit Sub
    End If
End If
    
    CancelStationPoll
    ResetRequestTrackingAfterRefresh
    ImportDebugLog "RefreshCurrentIntakeSnapshot", "TRACKING_RESET"

    SetPanelCell ws, CELL_LAST_QUEUE_STATUS, "Refreshing snapshot"
    ClearPanelCell ws, CELL_LAST_RESULT_CODE
    SetPanelCell ws, CELL_LAST_SCAN_RESULT, "Refreshing"
    SetPanelCell ws, CELL_LAST_RESULT_MESSAGE, "Requesting the selected stage snapshot from the master."


    ImportDebugLog "RefreshCurrentIntakeSnapshot", "EXPECTED_STAGE", expectedStageSheet

ShowProcessingNotice "Requesting fresh snapshot from master. Please wait."
DoEvents

If Not RequestMasterSnapshotAndWait(GetSelectedDeliveryKey(), GetSelectedStageProfile(), 300) Then
    HideProcessingNotice
    SetPanelCell ws, CELL_LAST_QUEUE_STATUS, "Refresh failed"

    If Len(Trim$(CStr(ws.Range(CELL_LAST_RESULT_CODE).Value))) = 0 Then
        SetPanelCell ws, CELL_LAST_RESULT_CODE, "SNAPSHOT_REQUEST_FAILED"
    End If

    SetPanelCell ws, CELL_LAST_SCAN_RESULT, "Error"

    If Len(Trim$(CStr(ws.Range(CELL_LAST_RESULT_MESSAGE).Value))) = 0 Or _
       StrComp(Trim$(CStr(ws.Range(CELL_LAST_RESULT_MESSAGE).Value)), "Requesting fresh snapshot from master...", vbTextCompare) = 0 Then
        SetPanelCell ws, CELL_LAST_RESULT_MESSAGE, "The master did not publish the requested snapshot."
    End If

    Exit Sub
End If

SetPanelCell ws, CELL_LAST_RESULT_MESSAGE, "Loading the published snapshot from SharePoint."

LoadSelectedStageSnapshotFromSharePoint True

HideProcessingNotice

    ImportDebugLog "RefreshCurrentIntakeSnapshot", "POST_LOAD", _
                   "IsImportedStageLoaded=" & CStr(IsImportedStageLoaded()), _
                   "LoadedStage=" & GetConfigValue(CFG_LOADED_STAGE_SHEET, vbNullString), _
                   "LoadedToken=" & GetLoadedRevisionToken()

    If Not IsImportedStageLoaded() Then
        ImportDebugLog "RefreshCurrentIntakeSnapshot", "FAIL_NOT_LOADED"
        SetPanelCell ws, CELL_LAST_QUEUE_STATUS, "Refresh failed"
        SetPanelCell ws, CELL_LAST_RESULT_CODE, "REFRESH_FAILED"
        SetPanelCell ws, CELL_LAST_SCAN_RESULT, "Error"
        SetPanelCell ws, CELL_LAST_RESULT_MESSAGE, "Snapshot reload did not complete."
        Exit Sub
    End If

    If StrComp(GetConfigValue(CFG_LOADED_STAGE_SHEET, vbNullString), expectedStageSheet, vbTextCompare) <> 0 Then
        ImportDebugLog "RefreshCurrentIntakeSnapshot", "FAIL_STAGE_MISMATCH", _
                       GetConfigValue(CFG_LOADED_STAGE_SHEET, vbNullString), expectedStageSheet
        SetPanelCell ws, CELL_LAST_QUEUE_STATUS, "Refresh failed"
        SetPanelCell ws, CELL_LAST_RESULT_CODE, "REFRESH_STAGE_MISMATCH"
        SetPanelCell ws, CELL_LAST_SCAN_RESULT, "Error"
        SetPanelCell ws, CELL_LAST_RESULT_MESSAGE, "The reloaded stage did not match the selected stage."
        Exit Sub
    End If

    currentRevisionToken = GetCurrentSelectedDeliveryListRevisionToken(currentRevisionUpdatedAt, True)
    ImportDebugLog "RefreshCurrentIntakeSnapshot", "REVISION_COMPARE", _
                   "Loaded=" & GetLoadedRevisionToken(), _
                   "Current=" & currentRevisionToken, _
                   "UpdatedAt=" & currentRevisionUpdatedAt

    If Len(currentRevisionToken) > 0 Then
        If StrComp(GetLoadedRevisionToken(), currentRevisionToken, vbTextCompare) <> 0 Then
            ImportDebugLog "RefreshCurrentIntakeSnapshot", "FAIL_REVISION_MISMATCH"
            SetPanelCell ws, CELL_LAST_QUEUE_STATUS, "Refresh incomplete"
            SetPanelCell ws, CELL_LAST_RESULT_CODE, "REFRESH_REVISION_MISMATCH"
            SetPanelCell ws, CELL_LAST_SCAN_RESULT, "Error"
            SetPanelCell ws, CELL_LAST_RESULT_MESSAGE, "The snapshot reloaded, but the revision still does not match the master."
            Exit Sub
        End If
    End If

    RefreshScannerPanelHeaderOnly

    mLastRevisionPopupToken = vbNullString
    mLastBackgroundRevisionCheckAt = 0

    ClearSnapshotRefreshQueueWatch
    ClearStageOutOfDateMarker
    ResetSnapshotOutOfDateAlertState

SetPanelCell ws, CELL_LAST_QUEUE_STATUS, "Snapshot refreshed"
ClearPanelCell ws, CELL_LAST_RESULT_CODE
SetPanelCell ws, CELL_LAST_SCAN_RESULT, "Ready"
SetPanelCell ws, CELL_LAST_RESULT_MESSAGE, "Selected stage snapshot was loaded from SharePoint."

ImportDebugLog "RefreshCurrentIntakeSnapshot", "END_OK"

CancelStationPoll
ScheduleStationPoll REVISION_BACKGROUND_CHECK_SECONDS

FocusStageScanBox

    If IMPORT_DEBUG_ENABLED Then
        MsgBox "Refresh finished. Run ImportDebugShowSheet to inspect the detailed import log.", _
               vbInformation, "Refresh Debug"
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: ClearPanelCell
' Scope: Private Sub
'
' What it does:
'   Builds, formats, or updates the intake operator panel/buttons for
'   ClearPanelCell.
'
' Why it exists:
'   The panel is the operator-facing part of the workbook; consistent buttons
'   and status cells reduce scanning mistakes.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ClearPanelCell(ByVal ws As Worksheet, ByVal addr As String)
    With ws.Range(addr)
        If .MergeCells Then
            .MergeArea.Cells(1, 1).Value = vbNullString
        Else
            .Value = vbNullString
        End If
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: SetPanelCell
' Scope: Private Sub
'
' What it does:
'   Builds, formats, or updates the intake operator panel/buttons for
'   SetPanelCell.
'
' Why it exists:
'   The panel is the operator-facing part of the workbook; consistent buttons
'   and status cells reduce scanning mistakes.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub SetPanelCell(ByVal ws As Worksheet, ByVal addr As String, ByVal valueText As Variant)
    With ws.Range(addr)
        If .MergeCells Then
            .MergeArea.Cells(1, 1).Value = valueText
        Else
            .Value = valueText
        End If
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: HasLoadedRevisionMismatch
' Scope: Private Function
'
' What it does:
'   Checks or stores master delivery-list identity/revision/processor state
'   for HasLoadedRevisionMismatch.
'
' Why it exists:
'   The intake snapshot must match the current master revision; otherwise
'   scans could be applied to stale rows.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function HasLoadedRevisionMismatch(ByRef currentToken As String, ByRef currentUpdatedAt As String) As Boolean
    Dim loadedToken As String

    loadedToken = GetLoadedRevisionToken()
    currentToken = GetCurrentSelectedDeliveryListRevisionToken(currentUpdatedAt, False)

    'If the master has no revision token yet, do not block scanning
    If Len(currentToken) = 0 Then Exit Function

    If StrComp(loadedToken, currentToken, vbTextCompare) <> 0 Then
        HasLoadedRevisionMismatch = True
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: ApplyRefreshRequiredUi
' Scope: Private Sub
'
' What it does:
'   Applies a visual state, setting, filter, tab name/color, protection rule,
'   or workflow state for ApplyRefreshRequiredUi.
'
' Why it exists:
'   Apply helpers make refresh/rebuild operations repeatable and help prevent
'   half-updated sheets.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ApplyRefreshRequiredUi(ByVal ws As Worksheet, ByVal currentUpdatedAt As String)
    Dim msg As String

    msg = "The master delivery list has changed."

    If Len(Trim$(currentUpdatedAt)) > 0 Then
        msg = msg & " Master updated: " & currentUpdatedAt & "."
    End If

    msg = msg & " You may keep scanning, but this intake view is out of date. Click Refresh Snapshot as soon as possible."

    SetPanelCell ws, CELL_LAST_QUEUE_STATUS, "Snapshot out of date"
    SetPanelCell ws, CELL_LAST_RESULT_CODE, "SNAPSHOT_OUT_OF_DATE"
    SetPanelCell ws, CELL_LAST_RESULT_MESSAGE, msg
    SetPanelCell ws, CELL_LAST_SCAN_RESULT, "Scan allowed"

    ApplyStageOutOfDateMarker msg
End Sub

Private Sub ShowSnapshotOutOfDateScanAlert(ByVal currentUpdatedAt As String)
    Dim msg As String

    msg = "The master delivery list has changed."

    If Len(Trim$(currentUpdatedAt)) > 0 Then
        msg = msg & vbCrLf & vbCrLf & _
              "Master updated: " & currentUpdatedAt
    End If

    msg = msg & vbCrLf & vbCrLf & _
          "Your intake view is now out of date." & vbCrLf & vbCrLf & _
          "You may keep scanning. Scans will still be queued to the master." & vbCrLf & vbCrLf & _
          "Click Refresh Snapshot as soon as possible so the visible delivery list catches up."

    On Error Resume Next

    Unload frmScanAlert

    frmScanAlert.LoadAlert _
        "Snapshot Out of Date", _
        msg, _
        "SNAPSHOT_OUT_OF_DATE", _
        False

    frmScanAlert.Show vbModeless

    On Error GoTo 0
End Sub

Private Sub ResetSnapshotOutOfDateAlertState()
    mLastRevisionPopupToken = vbNullString
End Sub

Private Sub ApplyStageOutOfDateMarker(ByVal messageText As String)
    Dim ws As Worksheet
    Dim rng As Range

    On Error GoTo SafeExit

    Set ws = StageViewSheet()
    If ws Is Nothing Then Exit Sub

    ws.Unprotect Password:=""

    Set rng = ws.Range("A1:N1")

    If ws.Range("A1").MergeCells Then ws.Range("A1").MergeArea.UnMerge
    rng.ClearContents
    rng.Merge

    With rng
        .Cells(1, 1).Value = "SNAPSHOT OUT OF DATE - Keep scanning if needed. Click Refresh Snapshot ASAP."
        .Interior.Color = RGB(255, 242, 204)
        .Font.Color = RGB(156, 101, 0)
        .Font.Bold = True
        .Font.Size = 14
        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
        .WrapText = False
        .ShrinkToFit = True
        .Borders.lineStyle = xlContinuous
        .Borders.Weight = xlMedium
    End With

    ws.Rows(1).rowHeight = 40

SafeExit:
    On Error Resume Next
    ReprotectStageViewSheetForScanning ws
    On Error GoTo 0
End Sub

Private Sub ApplyStageMasterStatusMarker(ByVal normalizedStatus As String)
    Dim ws As Worksheet
    Dim rng As Range
    Dim bannerText As String

    On Error GoTo SafeExit

    Set ws = StageViewSheet()
    If ws Is Nothing Then Exit Sub

    Select Case UCase$(Trim$(normalizedStatus))
        Case "PAUSED"
            bannerText = "MASTER PAUSED - Keep scanning if needed. Updates will process when the master resumes."

        Case "OFFLINE"
            bannerText = "MASTER OFFLINE - Keep scanning if needed. Updates will process when the master is back online."

        Case Else
            bannerText = "MASTER NOT ONLINE - Keep scanning if needed. Updates will process when the master is back online."
    End Select

    ws.Unprotect Password:=""

    Set rng = ws.Range("A1:N1")

    If ws.Range("A1").MergeCells Then ws.Range("A1").MergeArea.UnMerge
    rng.ClearContents
    rng.Merge

    With rng
        .Cells(1, 1).Value = bannerText
        .Interior.Color = RGB(255, 242, 204)
        .Font.Color = RGB(156, 101, 0)
        .Font.Bold = True
        .Font.Size = 14
        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
        .WrapText = False
        .ShrinkToFit = True
        .Borders.lineStyle = xlContinuous
        .Borders.Weight = xlMedium
    End With

    ws.Rows(1).rowHeight = 40

SafeExit:
    On Error Resume Next
    ReprotectStageViewSheetForScanning ws
    On Error GoTo 0
End Sub

Private Sub ClearStageOutOfDateMarker()
    Dim ws As Worksheet
    Dim rng As Range
    Dim curText As String

    On Error GoTo SafeExit

    Set ws = StageViewSheet()
    If ws Is Nothing Then Exit Sub

    Set rng = ws.Range("A1:N1")
    curText = CStr(ws.Range("A1").Value)

    If InStr(1, curText, "SNAPSHOT OUT OF DATE", vbTextCompare) = 0 Then GoTo SafeExit

    ws.Unprotect Password:=""

    If ws.Range("A1").MergeCells Then ws.Range("A1").MergeArea.UnMerge

    With rng
        .ClearContents
        .Interior.Pattern = xlNone
        .Font.ColorIndex = xlAutomatic
        .Font.Bold = False
        .Font.Size = 11
        .Borders.lineStyle = xlNone
        .ShrinkToFit = False
    End With

SafeExit:
    On Error Resume Next
    ReprotectStageViewSheetForScanning ws
    On Error GoTo 0
End Sub

Private Sub ClearStageMasterStatusMarker()
    Dim ws As Worksheet
    Dim rng As Range
    Dim curText As String

    On Error GoTo SafeExit

    Set ws = StageViewSheet()
    If ws Is Nothing Then Exit Sub

    Set rng = ws.Range("A1:N1")
    curText = UCase$(Trim$(CStr(ws.Range("A1").Value)))

    If Left$(curText, 7) <> "MASTER " Then GoTo SafeExit

    ws.Unprotect Password:=""

    If ws.Range("A1").MergeCells Then ws.Range("A1").MergeArea.UnMerge

    With rng
        .ClearContents
        .Interior.Pattern = xlNone
        .Font.ColorIndex = xlAutomatic
        .Font.Bold = False
        .Font.Size = 11
        .Borders.lineStyle = xlNone
        .ShrinkToFit = False
    End With

SafeExit:
    On Error Resume Next
    ReprotectStageViewSheetForScanning ws
    On Error GoTo 0
End Sub

Private Sub ReprotectStageViewSheetForScanning(ByVal ws As Worksheet)
    If ws Is Nothing Then Exit Sub

    On Error Resume Next

    ws.EnableSelection = xlUnlockedCells

    ws.Protect Password:="", _
               UserInterfaceOnly:=True, _
               DrawingObjects:=False, _
               Contents:=True, _
               Scenarios:=True

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: CheckForMasterRevisionUpdate
' Scope: Private Sub
'
' What it does:
'   Checks or stores master delivery-list identity/revision/processor state
'   for CheckForMasterRevisionUpdate.
'
' Why it exists:
'   The intake snapshot must match the current master revision; otherwise
'   scans could be applied to stale rows.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub CheckForMasterRevisionUpdate()
    Dim ws As Worksheet
    Dim currentToken As String
    Dim currentUpdatedAt As String
    Dim priorQueueStatus As String
    Dim priorResultMessage As String

    Set ws = StationSheet()

    If Len(GetSelectedDeliveryKey()) = 0 Then Exit Sub
    If Not IsImportedStageLoaded() Then Exit Sub

    If mLastBackgroundRevisionCheckAt > 0 Then
        If DateDiff("s", mLastBackgroundRevisionCheckAt, Now) < REVISION_BACKGROUND_CHECK_SECONDS Then
            Exit Sub
        End If
    End If

    mLastBackgroundRevisionCheckAt = Now

    priorQueueStatus = CStr(ws.Range(CELL_LAST_QUEUE_STATUS).Value)
    priorResultMessage = CStr(ws.Range(CELL_LAST_RESULT_MESSAGE).Value)

mMasterCheckBusy = True
SetPanelCell ws, CELL_LAST_QUEUE_STATUS, "Checking master updates"
SetPanelCell ws, CELL_LAST_RESULT_MESSAGE, _
    "Checking for master updates in the background. Scanning is still allowed."
DoEvents

    On Error GoTo SafeExit

    If HasLoadedRevisionMismatch(currentToken, currentUpdatedAt) Then
    ApplyRefreshRequiredUi ws, currentUpdatedAt

    If StrComp(mLastRevisionPopupToken, GetLoadedRevisionToken(), vbTextCompare) <> 0 Then
        mLastRevisionPopupToken = GetLoadedRevisionToken()
        ShowSnapshotOutOfDateScanAlert currentUpdatedAt
    End If
Else
    ws.Range(CELL_LAST_QUEUE_STATUS).Value = priorQueueStatus
    ws.Range(CELL_LAST_RESULT_MESSAGE).Value = priorResultMessage
End If

SafeExit:
    HideProcessingNotice
    mMasterCheckBusy = False
End Sub

'------------------------------------------------------------------------------
' Procedure: ResetRequestTrackingAfterRefresh
' Scope: Private Sub
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   ResetRequestTrackingAfterRefresh.
'
' Why it exists:
'   The intake station must keep local buffer state, SharePoint queue state,
'   and master final results synchronized without blocking scanning.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ResetRequestTrackingAfterRefresh()
    Dim ws As Worksheet
    Set ws = StationSheet()

    ClearPanelCell ws, CELL_LAST_REQUEST
    ClearPanelCell ws, CELL_LAST_RESULT_CODE
    SetPanelCell ws, CELL_LAST_QUEUE_STATUS, "Idle"
    ClearPanelCell ws, CELL_LAST_SCAN_RESULT
    ClearPanelCell ws, CELL_LAST_RESULT_MESSAGE

    mLastPopupRequestId = vbNullString
End Sub

'------------------------------------------------------------------------------
' Procedure: ClearSnapshotRefreshQueueWatch
' Scope: Private Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   ClearSnapshotRefreshQueueWatch.
'
' Why it exists:
'   The intake station must keep local buffer state, SharePoint queue state,
'   and master final results synchronized without blocking scanning.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ClearSnapshotRefreshQueueWatch()
    Dim ws As Worksheet

    Set ws = StationSheet()
    If ws Is Nothing Then Exit Sub

    ClearPanelCell ws, CELL_LAST_REQUEST

    mLastStatusMissingRequestId = vbNullString
    mLastStatusMissingCount = 0
End Sub

'------------------------------------------------------------------------------
' Procedure: RefreshScannerPanelHeaderOnly
' Scope: Private Sub
'
' What it does:
'   Cleans, validates, decodes, applies, focuses, or displays scan/barcode
'   data for RefreshScannerPanelHeaderOnly.
'
' Why it exists:
'   The scanner acts like a keyboard, so the workbook must turn entered text
'   into safe order/item updates without duplicate submissions.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub RefreshScannerPanelHeaderOnly()
    LoadSavedScannerSettingsToPanel
    RefreshSelectedDeliveryStatus
End Sub

'------------------------------------------------------------------------------
' Procedure: RefreshQueueStatusNow
' Scope: Public Sub
'
' What it does:
'   Manually triggers fast queue-status checking for the currently loaded
'   stage and active requests.
'
' Why it exists:
'   This gives the operator a way to retry status updates instead of waiting
'   for slow fallback polling.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub RefreshQueueStatusNow()
    Dim ws As Worksheet

    Set ws = StationSheet()

    If Len(GetSelectedDeliveryKey()) = 0 Then
        MsgBox "Select a delivery list first.", vbExclamation, "Refresh Queue Status"
        Exit Sub
    End If

    If Not IsImportedStageLoaded() Then
        MsgBox "Load a stage snapshot first.", vbExclamation, "Refresh Queue Status"
        Exit Sub
    End If

    If mQueueStatusBusy Then
        ShowProcessingNotice "Queue status is already being checked. Please wait."
        Exit Sub
    End If

    On Error GoTo ErrHandler

    'Manual button restarts the fast checking window.
    ResetQueuePollFallbackForNewWork
    CancelStationPoll

    mQueueStatusBusy = True
    ShowProcessingNotice "Checking queue status. Please wait."

    ws.Range(CELL_LAST_QUEUE_STATUS).Value = "Working"
    ws.Range(CELL_LAST_RESULT_CODE).Value = vbNullString
    ws.Range(CELL_LAST_RESULT_MESSAGE).Value = "Checking SharePoint queue status."

    If HasPendingQueueRows() Then
        FlushPendingQueueRows 100
    End If

    RefreshLastRequestStatus
    RefreshPendingImportedQueueStates True

SafeExit:
    HideProcessingNotice
    mQueueStatusBusy = False
    FocusStageScanBox

If HasActiveQueueWatchRequests() Then
    If IsAutoQueuePollEnabled() Then
        ScheduleStationPoll STATION_POLL_REPEAT_SECONDS
    Else
        CancelStationPoll
        SetPanelCell ws, CELL_LAST_QUEUE_STATUS, "Auto queue off"
        SetPanelCell ws, CELL_LAST_RESULT_MESSAGE, _
            "Manual refresh completed. Automatic queue checking is off."
    End If
Else
    ResetQueuePollFallbackForNewWork
    CancelStationPoll
End If

    Exit Sub

ErrHandler:
    ws.Range(CELL_LAST_QUEUE_STATUS).Value = "PA Fail"
    ws.Range(CELL_LAST_RESULT_CODE).Value = "QUEUE_REFRESH_FAILED"
    ws.Range(CELL_LAST_RESULT_MESSAGE).Value = "Error " & Err.Number & ": " & Err.Description

    MsgBox "Queue status refresh failed." & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbExclamation, "Refresh Queue Status"

    Resume SafeExit
End Sub

'------------------------------------------------------------------------------
' Procedure: DebugLastRequestStatusNow
' Scope: Public Sub
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   DebugLastRequestStatusNow.
'
' Why it exists:
'   The intake station must keep local buffer state, SharePoint queue state,
'   and master final results synchronized without blocking scanning.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub DebugLastRequestStatusNow()
    Dim ws As Worksheet
    Dim requestId As String
    Dim item As Object
    Dim msg As String

    Set ws = StationSheet()
    requestId = Trim$(CStr(ws.Range(CELL_LAST_REQUEST).Value))

    If Len(requestId) = 0 Then
        MsgBox "No last request ID is stored in " & CELL_LAST_REQUEST & ".", vbExclamation, "Debug Queue Status"
        Exit Sub
    End If

    Set item = PA_QueueGetRequestStatus(requestId)

    If item Is Nothing Then
        MsgBox "No item was returned for this request ID." & vbCrLf & vbCrLf & _
               "RequestId:" & vbCrLf & requestId & vbCrLf & vbCrLf & _
               "Open the __PA_Status_Debug sheet and check the latest Step column.", _
               vbExclamation, "Debug Queue Status"
        Exit Sub
    End If

    msg = "RequestId: " & PA_DictText(item, "requestId") & vbCrLf & _
          "Status: " & PA_DictText(item, "status") & vbCrLf & _
          "ResultCode: " & PA_DictText(item, "resultCode") & vbCrLf & _
          "ResultMessage: " & PA_DictText(item, "resultMessage") & vbCrLf & _
          "Order: " & PA_DictText(item, "orderNumber") & vbCrLf & _
          "Item: " & PA_DictText(item, "itemNumber")

    MsgBox msg, vbInformation, "Debug Queue Status"
End Sub

'------------------------------------------------------------------------------
' Procedure: HandleCompletedRequestFromItem
' Scope: Public Sub
'
' What it does:
'   Handles a final SharePoint queue item result, including alerts, override
'   flow, panel updates, and row-state cleanup.
'
' Why it exists:
'   Done/Error status is the masterÃ¢â‚¬â„¢s final answer; the intake workbook must
'   translate that into clear operator feedback.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub HandleCompletedRequestFromItem(ByVal item As Object)
    Dim requestId As String
    Dim statusText As String
    Dim resultCode As String
    Dim resultMessage As String
    Dim compactMessage As String
    Dim isOverrideRequest As Boolean

    If item Is Nothing Then Exit Sub

    requestId = Trim$(PA_DictText(item, "requestId"))
    statusText = Trim$(PA_DictText(item, "status"))
    resultCode = Trim$(PA_DictText(item, "resultCode"))
    resultMessage = Trim$(PA_DictText(item, "resultMessage"))
    compactMessage = CompactQueueResultMessage(resultMessage)

    If Len(requestId) = 0 Then Exit Sub
    If StrComp(mLastPopupRequestId, requestId, vbTextCompare) = 0 Then Exit Sub

    isOverrideRequest = IsKnownOverrideRequestId(requestId) Or _
                        IsReceiveOverrideRequestComment(PA_DictText(item, "requestComment")) Or _
                        IsSendOverrideRequestComment(PA_DictText(item, "requestComment"))

    If StrComp(statusText, "Error", vbTextCompare) = 0 Or _
       (Len(resultCode) > 0 And StrComp(resultCode, "OK", vbTextCompare) <> 0 And UCase$(Left$(compactMessage, 7)) <> "PARTIAL") Then

        If QueueResultAllowsSendOverride(resultMessage) And Not isOverrideRequest Then
            ShowScanSafeOverrideAlert _
                "Override Outbound Scan?", _
                "Outbound scan was blocked:" & vbCrLf & vbCrLf & _
                compactMessage & vbCrLf & vbCrLf & _
                "Scanning is paused. Click Override to send this item outbound anyway, or Clear Alert to stop.", _
                item

        ElseIf QueueResultAllowsReceiveOverride(resultMessage) And Not isOverrideRequest Then
            ShowScanSafeOverrideAlert _
                "Override Inbound Scan?", _
                "Inbound scan was blocked:" & vbCrLf & vbCrLf & _
                compactMessage & vbCrLf & vbCrLf & _
                "Scanning is paused. Click Override to receive this item anyway, or Clear Alert to stop.", _
                item
        Else
            ShowScanSafeAlert _
                "Master Scan Error", _
                compactMessage, _
                resultCode
        End If
    End If

    mLastPopupRequestId = requestId
End Sub



'------------------------------------------------------------------------------
' Procedure: SubmitOverrideReceiveFromRequestItem
' Scope: Private Sub
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   SubmitOverrideReceiveFromRequestItem.
'
' Why it exists:
'   The intake station must keep local buffer state, SharePoint queue state,
'   and master final results synchronized without blocking scanning.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub SubmitOverrideReceiveFromRequestItem(ByVal item As Object)
    Dim ws As Worksheet
    Dim requestId As String
    Dim oldRequestId As String
    Dim reqType As String
    Dim barcodeText As String
    Dim modeText As String
    Dim ord As Long
    Dim itm As Long
    Dim qty As Long
    Dim checkText As String
    Dim localMessage As String
    Dim importedRow As Long
    Dim ok As Boolean
    Dim overrideFlag As String
    Dim localOverrideComment As String
    Dim localApplyOk As Boolean

    Set ws = StationSheet()

    If item Is Nothing Then Exit Sub

    oldRequestId = Trim$(PA_DictText(item, "requestId"))
    reqType = UCase$(Trim$(PA_DictText(item, "requestType")))
    barcodeText = Trim$(PA_DictText(item, "barcode"))
    modeText = Trim$(PA_DictText(item, "mode"))

    If Len(modeText) = 0 Then
        modeText = ModeFromStageProfile(GetSelectedStageProfile())
    End If

    modeText = UCase$(Trim$(modeText))

    ord = CLng(Val(PA_DictText(item, "orderNumber")))
    itm = CLng(Val(PA_DictText(item, "itemNumber")))
    qty = CLng(Val(PA_DictText(item, "quantity")))

    If qty <= 0 Then qty = 1

    Select Case modeText
        Case "RECV"
            overrideFlag = QUEUE_RECV_OVERRIDE_FLAG
            localOverrideComment = "Override approved from intake form."

        Case "SEND"
            overrideFlag = QUEUE_SEND_OVERRIDE_FLAG
            localOverrideComment = "Override approved from intake form - outbound before staging."

        Case Else
            MsgBox "Override is only available for inbound receiving or outbound scans.", _
                   vbExclamation, "Override Not Available"
            Exit Sub
    End Select

    requestId = BuildRequestId(GetStationName())

    On Error GoTo FailOverride

    ShowProcessingNotice "Sending override to master. Please wait."
    mQueueStatusBusy = True
    DoEvents

    If reqType = "BARCODE" Then
        If Len(barcodeText) = 0 Then
            MsgBox "Cannot override because the original barcode was blank.", vbExclamation, "Override Failed"
            GoTo SafeExit
        End If

        localApplyOk = LocalPrevalidateAndApplyBarcode(barcodeText, checkText, localMessage)

        If Not localApplyOk Then
            'The original scan may already be applied locally before the master
            'returned the override alert. Do not block the override just because
            'the local snapshot says the quantity is already applied.
            If InStr(1, localMessage, "exceed the required quantity", vbTextCompare) = 0 And _
               InStr(1, localMessage, "already", vbTextCompare) = 0 Then

                MsgBox "Override could not be applied locally:" & vbCrLf & vbCrLf & _
                       CompactQueueResultMessage(localMessage), _
                       vbExclamation, "Override Failed"
                GoTo SafeExit
            End If

            If Len(checkText) = 0 Then checkText = "Override queued"
        End If

        ok = PA_QueueAddRequest( _
                requestId, _
                GetSelectedDeliveryKey(), _
                "BARCODE", _
                modeText, _
                barcodeText, _
                ord, _
                itm, _
                qty, _
                StageSheetFromProfile(GetSelectedStageProfile()), _
                GetStationName(), _
                overrideFlag)

    ElseIf reqType = "MANUAL" Then
        localApplyOk = LocalPrevalidateAndApplyManual(ord, itm, qty, localOverrideComment, checkText, localMessage)

        If Not localApplyOk Then
            If InStr(1, localMessage, "exceed the required quantity", vbTextCompare) = 0 And _
               InStr(1, localMessage, "already", vbTextCompare) = 0 Then

                MsgBox "Override could not be applied locally:" & vbCrLf & vbCrLf & _
                       CompactQueueResultMessage(localMessage), _
                       vbExclamation, "Override Failed"
                GoTo SafeExit
            End If

            If Len(checkText) = 0 Then checkText = "Override queued"
        End If

        ok = PA_QueueAddRequest( _
                requestId, _
                GetSelectedDeliveryKey(), _
                "MANUAL", _
                modeText, _
                vbNullString, _
                ord, _
                itm, _
                qty, _
                StageSheetFromProfile(GetSelectedStageProfile()), _
                GetStationName(), _
                overrideFlag)
    Else
        MsgBox "Override is not available for request type: " & reqType, vbExclamation, "Override Failed"
        GoTo SafeExit
    End If

    If Not ok Then
        MsgBox "Power Automate did not accept the override request.", vbExclamation, "Override Failed"
        GoTo SafeExit
    End If

    MarkOverrideRequestId requestId
    importedRow = FindImportedRowForOrderItem(ord, itm)
    MarkImportedRowPendingMaster importedRow, requestId, "Queued"

    ws.Range(CELL_LAST_REQUEST).Value = requestId
    ws.Range(CELL_LAST_QUEUE_STATUS).Value = "Queued"
    ws.Range(CELL_LAST_RESULT_CODE).Value = vbNullString

    If modeText = "SEND" Then
        ws.Range(CELL_LAST_RESULT_MESSAGE).Value = "Outbound override sent to master."
    Else
        ws.Range(CELL_LAST_RESULT_MESSAGE).Value = "Inbound override sent to master."
    End If

    ws.Range(CELL_LAST_SCAN_RESULT).Value = checkText

    mLastPopupRequestId = oldRequestId

    FocusScanBoxAndCenterRow importedRow
    ResetQueuePollFallbackForNewWork
    ScheduleStationPoll STATION_POLL_DELAY_AFTER_SCAN_SECONDS

SafeExit:
    HideProcessingNotice
    mQueueStatusBusy = False
    FocusStageScanBox
    Exit Sub

FailOverride:
    HideProcessingNotice
    mQueueStatusBusy = False

    MsgBox "Override failed." & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbExclamation, "Override Failed"

    FocusStageScanBox
End Sub

'------------------------------------------------------------------------------
' Procedure: SnapshotStageKeyFromProfileIntake
' Scope: Private Function
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   SnapshotStageKeyFromProfileIntake.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function SnapshotStageKeyFromProfileIntake(ByVal stageProfile As String) As String
    Select Case UCase$(Trim$(stageProfile))
        Case "STAGING - AIRPORT RD"
            SnapshotStageKeyFromProfileIntake = "STAGING_AIRPORT_RD"

        Case "OUTBOUND - AIRPORT RD"
            SnapshotStageKeyFromProfileIntake = "OUTBOUND_AIRPORT_RD"

        Case "INBOUND - INDIAN TRAIL"
            SnapshotStageKeyFromProfileIntake = "INBOUND_INDIAN_TRAIL"

        Case "INBOUND - GREENVILLE"
            SnapshotStageKeyFromProfileIntake = "INBOUND_GREENVILLE"

        Case "CUSTOMER PICKUP"
            SnapshotStageKeyFromProfileIntake = "CUSTOMER_PICKUP"
    End Select
End Function

'------------------------------------------------------------------------------
' Procedure: RequestMasterSnapshotAndWait
' Scope: Private Function
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   RequestMasterSnapshotAndWait.
'
' Why it exists:
'   The intake station must keep local buffer state, SharePoint queue state,
'   and master final results synchronized without blocking scanning.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function RequestMasterSnapshotAndWait(ByVal deliveryListKey As String, _
                                              ByVal stageProfile As String, _
                                              ByVal timeoutSeconds As Long) As Boolean
    Dim requestId As String
    Dim stageKey As String
    Dim modeText As String
    Dim startedAt As Date
    Dim item As Object
    Dim statusText As String
    Dim resultCode As String
    Dim resultMessage As String

    stageKey = SnapshotStageKeyFromProfileIntake(stageProfile)
    modeText = ModeFromStageProfile(stageProfile)

    If Len(deliveryListKey) = 0 Then Exit Function
    If Len(stageKey) = 0 Then Exit Function
    If Len(modeText) = 0 Then Exit Function

    requestId = BuildRequestId(GetStationName())

    StationSheet.Range(CELL_LAST_REQUEST).Value = requestId
    StationSheet.Range(CELL_LAST_QUEUE_STATUS).Value = "Queued"
    StationSheet.Range(CELL_LAST_RESULT_CODE).Value = vbNullString
    StationSheet.Range(CELL_LAST_RESULT_MESSAGE).Value = "Requesting fresh snapshot from master..."
    StationSheet.Range(CELL_LAST_SCAN_RESULT).Value = "Snapshot"

    If Not PA_QueueAddRequest( _
            requestId, _
            deliveryListKey, _
            "SNAPSHOT", _
            modeText, _
            vbNullString, _
            0, _
            0, _
            0, _
            stageProfile, _
            GetStationName(), _
            stageKey) Then

        StationSheet.Range(CELL_LAST_QUEUE_STATUS).Value = "Error"
        StationSheet.Range(CELL_LAST_RESULT_CODE).Value = "SNAPSHOT_REQUEST_FAILED"
        StationSheet.Range(CELL_LAST_RESULT_MESSAGE).Value = "Power Automate did not accept the snapshot request."
        Exit Function
    End If

    startedAt = Now

    Do
        DoEvents

        Set item = PA_QueueGetRequestStatus(requestId)

        If Not item Is Nothing Then
            statusText = Trim$(PA_DictText(item, "status"))
            resultCode = Trim$(PA_DictText(item, "resultCode"))
            resultMessage = Trim$(PA_DictText(item, "resultMessage"))

            StationSheet.Range(CELL_LAST_QUEUE_STATUS).Value = ShortQueueStateText(statusText)
            StationSheet.Range(CELL_LAST_RESULT_CODE).Value = resultCode
            StationSheet.Range(CELL_LAST_RESULT_MESSAGE).Value = resultMessage

            If StrComp(statusText, "Done", vbTextCompare) = 0 Then
                RequestMasterSnapshotAndWait = True
                Exit Function
            End If

            If StrComp(statusText, "Error", vbTextCompare) = 0 Then
                MsgBox "Master could not publish the requested snapshot." & vbCrLf & vbCrLf & _
                       resultMessage, _
                       vbExclamation, "Refresh Snapshot"
                Exit Function
            End If
        End If

        If DateDiff("s", startedAt, Now) >= timeoutSeconds Then
            StationSheet.Range(CELL_LAST_QUEUE_STATUS).Value = "Timeout"
            StationSheet.Range(CELL_LAST_RESULT_CODE).Value = "SNAPSHOT_TIMEOUT"
            StationSheet.Range(CELL_LAST_RESULT_MESSAGE).Value = "Timed out waiting for master snapshot."
            Exit Function
        End If

        Application.Wait Now + TimeSerial(0, 0, 2)
    Loop
End Function

'------------------------------------------------------------------------------
' Procedure: IsAutoQueuePollEnabled
' Scope: Public Function
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   IsAutoQueuePollEnabled.
'
' Why it exists:
'   The intake station must keep local buffer state, SharePoint queue state,
'   and master final results synchronized without blocking scanning.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function IsAutoQueuePollEnabled() As Boolean
    Dim s As String

    s = UCase$(Trim$(GetConfigValue(CFG_AUTO_QUEUE_POLL_ENABLED, "TRUE")))

    IsAutoQueuePollEnabled = _
        (s = "TRUE" Or s = "YES" Or s = "ON" Or s = "1")
End Function

'------------------------------------------------------------------------------
' Procedure: SetAutoQueuePollEnabled
' Scope: Public Sub
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   SetAutoQueuePollEnabled.
'
' Why it exists:
'   The intake station must keep local buffer state, SharePoint queue state,
'   and master final results synchronized without blocking scanning.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub SetAutoQueuePollEnabled(ByVal enabled As Boolean)
    If enabled Then
        SetConfigValue CFG_AUTO_QUEUE_POLL_ENABLED, "TRUE"
    Else
        SetConfigValue CFG_AUTO_QUEUE_POLL_ENABLED, "FALSE"
        CancelStationPoll
    End If

    UpdateAutoQueuePollButton StageViewSheet()
End Sub

'------------------------------------------------------------------------------
' Procedure: ToggleAutoQueuePoll
' Scope: Public Sub
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   ToggleAutoQueuePoll.
'
' Why it exists:
'   The intake station must keep local buffer state, SharePoint queue state,
'   and master final results synchronized without blocking scanning.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub ToggleAutoQueuePoll()
    SetAutoQueuePollEnabled Not IsAutoQueuePollEnabled()

    If IsAutoQueuePollEnabled() Then
        SetPanelCell StationSheet(), CELL_LAST_QUEUE_STATUS, "Auto queue on"

        If HasActiveQueueWatchRequests() Then
            ResetQueuePollFallbackForNewWork
            ScheduleStationPoll STATION_POLL_DELAY_AFTER_SCAN_SECONDS
        End If
    Else
        SetPanelCell StationSheet(), CELL_LAST_QUEUE_STATUS, "Auto queue off"
        SetPanelCell StationSheet(), CELL_LAST_RESULT_MESSAGE, _
            "Automatic queue status checking is off. Use Refresh Queue Status to check manually."
    End If

    FocusStageScanBox
End Sub

'------------------------------------------------------------------------------
' Procedure: UpdateAutoQueuePollButton
' Scope: Public Sub
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   UpdateAutoQueuePollButton.
'
' Why it exists:
'   The intake station must keep local buffer state, SharePoint queue state,
'   and master final results synchronized without blocking scanning.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub UpdateAutoQueuePollButton(Optional ByVal ws As Worksheet = Nothing)
    Dim workWs As Worksheet
    Dim shp As Shape
    Dim btnName As String
    Dim captionText As String

    btnName = "btnStageAutoQueueToggle"

    If ws Is Nothing Then
        Set workWs = StageViewSheet()
    Else
        Set workWs = ws
    End If

    If workWs Is Nothing Then Exit Sub

    On Error Resume Next
    Set shp = workWs.Shapes(btnName)
    On Error GoTo 0

    If shp Is Nothing Then Exit Sub

    If IsAutoQueuePollEnabled() Then
        captionText = "Auto ON"
        shp.Fill.ForeColor.RGB = RGB(198, 239, 206)
        shp.Line.ForeColor.RGB = RGB(0, 97, 0)
        shp.TextFrame2.TextRange.Font.Fill.ForeColor.RGB = RGB(0, 97, 0)
    Else
        captionText = "Auto OFF"
        shp.Fill.ForeColor.RGB = RGB(255, 199, 206)
        shp.Line.ForeColor.RGB = RGB(156, 0, 6)
        shp.TextFrame2.TextRange.Font.Fill.ForeColor.RGB = RGB(156, 0, 6)
    End If

    shp.TextFrame2.TextRange.Text = captionText
End Sub

'------------------------------------------------------------------------------
' Procedure: EnsureStageAutoQueueToggleButton
' Scope: Public Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   EnsureStageAutoQueueToggleButton.
'
' Why it exists:
'   The intake station must keep local buffer state, SharePoint queue state,
'   and master final results synchronized without blocking scanning.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub EnsureStageAutoQueueToggleButton(Optional ByVal ws As Worksheet = Nothing)
    Dim workWs As Worksheet
    Dim targetCell As Range
    Dim shp As Shape
    Dim btnName As String
    Dim macroName As String
    Dim wasProtected As Boolean

    btnName = "btnStageAutoQueueToggle"
    macroName = "'" & ThisWorkbook.Name & "'!ToggleAutoQueuePoll"

    If ws Is Nothing Then
        Set workWs = StageViewSheet()
    Else
        Set workWs = ws
    End If

    If workWs Is Nothing Then Exit Sub

    'Put it right above/near the Queue State column.
    'N4 can be Refresh, M4 can be Auto ON/OFF.
    Set targetCell = workWs.Range("M4")

    On Error Resume Next

    wasProtected = (workWs.ProtectContents Or workWs.ProtectDrawingObjects Or workWs.ProtectScenarios)
    If wasProtected Then workWs.Unprotect

    workWs.Shapes(btnName).Delete

    Set shp = workWs.Shapes.AddShape( _
        Type:=msoShapeRoundedRectangle, _
        Left:=targetCell.Left + 2, _
        Top:=targetCell.Top + 2, _
        Width:=targetCell.Width - 4, _
        Height:=targetCell.Height - 4)

    With shp
        .Name = btnName
        .OnAction = macroName
        .Placement = xlMoveAndSize
        .Locked = False

        With .TextFrame2
            .VerticalAnchor = msoAnchorMiddle
            .TextRange.ParagraphFormat.Alignment = msoAlignCenter
            .TextRange.Font.Size = 9
            .TextRange.Font.Bold = msoTrue
        End With
    End With

    targetCell.Value = vbNullString

    UpdateAutoQueuePollButton workWs

    If wasProtected Then ProtectImportedStageForScanning workWs

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: DebugLoadLatestSnapshotOnly
' Scope: Public Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   DebugLoadLatestSnapshotOnly.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub DebugLoadLatestSnapshotOnly()
    On Error GoTo ErrHandler

    SetAutoQueuePollEnabled False
    CancelStationPoll
    CancelPendingQueueFlush
    HideProcessingNotice

    Application.EnableEvents = True
    Application.ScreenUpdating = True
    Application.DisplayAlerts = True
    Application.StatusBar = False

    If Len(GetSelectedDeliveryKey()) = 0 Then
        MsgBox "No delivery list is selected.", vbExclamation, "Debug Snapshot Load"
        Exit Sub
    End If

    If Len(GetSelectedStageProfile()) = 0 Then
        MsgBox "No stage profile is selected.", vbExclamation, "Debug Snapshot Load"
        Exit Sub
    End If

    If LoadLatestPublishedSnapshotForSettings(False) Then
        MsgBox "Direct snapshot load succeeded.", vbInformation, "Debug Snapshot Load"
    Else
        MsgBox "Direct snapshot load failed. Open the __PA_SnapshotGet_Debug sheet and check the latest rows.", _
               vbExclamation, "Debug Snapshot Load"
    End If

    Exit Sub

ErrHandler:
    MsgBox "DebugLoadLatestSnapshotOnly failed." & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbExclamation, "Debug Snapshot Load"
End Sub
