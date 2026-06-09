Attribute VB_Name = "ThisWorkbook"
Attribute VB_Base = "0{00020819-0000-0000-C000-000000000046}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = True
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = True
Option Explicit

'==============================================================================
' Module: ThisWorkbook_Intake
' Workbook: Intake_Scanning_Test.xlsm / Intake scanner workbook
'
' What this module does:
'   Workbook-level event code for the intake/scanning workbook. It starts the
'   scanner session, captures scan-box changes, and cleans up timers/state
'   when the workbook closes.
'
' Why this module exists:
'   Excel workbook events are the safest place to intercept startup, scan
'   entry, and shutdown because they run automatically around the operator
'   workflow.
'
' Commenting standard used in this rewrite:
'   Comments explain both what each procedure/section does and why it
'   matters to the scanning, SharePoint, Power Automate, buffering, and
'   operator-safety workflow. The code behavior and public procedure names
'   are intentionally kept stable so existing buttons/forms/timers keep working.
'==============================================================================


'ThisWorkbook'

'------------------------------------------------------------------------------
' Procedure: Workbook_Open
' Scope: Private Sub
'
' What it does:
'   Runs the intake workbook startup sequence by calling StartupScannerSession
'   as soon as the workbook opens.
'
' Why it exists:
'   The scanner station needs its hidden sheets, settings, buttons, audit log,
'   and panel layout ready before an operator starts scanning.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'
' Extra note:
'   Workbook_Open is intentionally tiny so the real startup logic stays
'   testable in modIntakeStation.
'------------------------------------------------------------------------------
Private Sub Workbook_Open()
    On Error Resume Next
    StartupScannerSession
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: Workbook_SheetChange
' Scope: Private Sub
'
' What it does:
'   Watches worksheet edits and submits a scan only when the changed cell is
'   the active stage scan box.
'
' Why it exists:
'   Scanner guns type into a worksheet cell like a keyboard. This event turns
'   that cell change into a queued scan while ignoring normal
'   worksheet/programmatic changes.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'
' Extra note:
'   The event disables events while submitting/clearing the scan box to
'   prevent recursive scan submissions.
'------------------------------------------------------------------------------
Private Sub Workbook_SheetChange(ByVal Sh As Object, ByVal Target As Range)
    Dim scanCell As Range
    Dim enteredText As String

    On Error GoTo ErrHandler

    If Target Is Nothing Then Exit Sub
    If Target.CountLarge <> 1 Then Exit Sub
    If Application.EnableEvents = False Then Exit Sub
    If IsStageProgrammaticUpdate() Then Exit Sub
    If Not IsStageViewWorksheet(Sh) Then Exit Sub
    
    If IsStageCommentCell(Target) Then
    MarkStageCommentsDirtyFromEdit
    Exit Sub
End If

    Set scanCell = GetStageScanBoxCell()
    If scanCell Is Nothing Then Exit Sub
    If Target.Address(False, False) <> scanCell.Address(False, False) Then Exit Sub

    enteredText = CleanBarcodeText(CStr(Target.Value))
    If Len(enteredText) = 0 Then Exit Sub

    Application.EnableEvents = False
    SubmitQueuedScanFromBox
    scanCell.ClearContents
    FocusStageScanBox

SafeExit:
    Application.EnableEvents = True
    Exit Sub

ErrHandler:
    On Error Resume Next
    UpdatePanelForLocalError "RUNTIME_ERROR", "Scan runtime error " & Err.Number & ": " & Err.Description
    Resume SafeExit
End Sub

'------------------------------------------------------------------------------
' Procedure: Workbook_BeforeClose
' Scope: Private Sub
'
' What it does:
'   Cancels pending timers, cleans old audit records, and resets scanner
'   session state before the intake workbook closes.
'
' Why it exists:
'   Application.OnTime timers can keep firing after close if not cancelled,
'   and hidden state should not carry into the next operator session
'   unexpectedly.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub Workbook_BeforeClose(Cancel As Boolean)
    On Error Resume Next
    CancelPendingQueueFlush
    CancelStationPoll
    CleanupOldScanAuditRows
    ResetScannerSessionState
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: ResetScannerRuntimeState
' Scope: Public Sub
'
' What it does:
'   Emergency reset macro that restores basic Excel runtime flags such as
'   events, screen updating, alerts, status bar, and Enter-key behavior.
'
' Why it exists:
'   If a macro errors while Excel events or screen updating are disabled, the
'   scanner can feel frozen; this gives the operator/admin a safe recovery
'   button.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub ResetScannerRuntimeState()
    On Error Resume Next

    Application.EnableEvents = True
    Application.ScreenUpdating = True
    Application.DisplayAlerts = True
    Application.DisplayStatusBar = True
    Application.MoveAfterReturn = False
    Application.StatusBar = False

    On Error GoTo 0

    MsgBox "Scanner runtime state reset. Try scanning again.", vbInformation, "Scanner Reset"
End Sub

