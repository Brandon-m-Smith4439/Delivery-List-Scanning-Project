Attribute VB_Name = "modProcessingNotice"
Option Explicit

'==============================================================================
' Module: modProcessingNotice
' Workbook: Intake_Staging_Test.xlsm
'
' Purpose:
'   Controls the modeless "processing / please wait" notice used by the intake
'   scanning workflow.
'
' Used when:
'   - buffered scans are being flushed to SharePoint / Power Automate
'   - queue status is being refreshed
'   - the intake form is checking whether the master delivery list changed
'   - a user tries to scan while scanning is temporarily blocked
'
' Important behavior:
'   This module does not process scans. It only shows, updates, and hides the
'   frmProcessingNotice UserForm so operators know scanning is paused.
'
' Dependency:
'   The intake workbook must contain a UserForm named frmProcessingNotice.
'==============================================================================

Public mProcessingNoticeVisible As Boolean

Private Const DEFAULT_PROCESSING_NOTICE_TEXT As String = _
    "Scans are temporarily paused. Please wait."

Private Const BLOCKED_SCAN_WARNING_TEXT As String = _
    "Scans are temporarily paused while buffered scans are being sent. Please wait a moment and scan again."

Private Const PROCESSING_NOTICE_CAPTION As String = "Processing"


'==============================================================================
' Show/update processing notice
'
' Shows frmProcessingNotice modeless so Excel can continue running VBA while the
' notice is visible.
'
' If the notice is already visible, this updates the message text instead of
' loading a second copy of the form.
'==============================================================================
Public Sub ShowProcessingNotice(Optional ByVal detailText As String = DEFAULT_PROCESSING_NOTICE_TEXT)
    On Error GoTo SafeExit

    detailText = Trim$(CStr(detailText))
    If Len(detailText) = 0 Then detailText = DEFAULT_PROCESSING_NOTICE_TEXT

    If mProcessingNoticeVisible Then
        UpdateProcessingNoticeText detailText
        DoEvents
        Exit Sub
    End If

    Load frmProcessingNotice
    UpdateProcessingNoticeText detailText
    frmProcessingNotice.Show vbModeless

    mProcessingNoticeVisible = True
    DoEvents

SafeExit:
End Sub


'==============================================================================
' Hide processing notice
'
' Unloads frmProcessingNotice and resets the visible-state flag.
' Safe to call even if the form is not currently loaded.
'==============================================================================
Public Sub HideProcessingNotice()
    On Error Resume Next
    Unload frmProcessingNotice
    mProcessingNoticeVisible = False
    On Error GoTo 0
End Sub


'==============================================================================
' Processing notice state
'
' Returns True when this module believes frmProcessingNotice is currently shown.
' Use this function instead of reading mProcessingNoticeVisible directly.
'==============================================================================
Public Function IsProcessingNoticeVisible() As Boolean
    IsProcessingNoticeVisible = mProcessingNoticeVisible
End Function


'==============================================================================
' Blocked scan warning
'
' Runs when the operator scans while intake is temporarily busy.
' Beeps once, then shows the processing notice with a specific warning message.
'==============================================================================
Public Sub ShowBlockedScanWarning()
    Beep
    ShowProcessingNotice BLOCKED_SCAN_WARNING_TEXT
End Sub


'==============================================================================
' Processing notice text updater
'
' Updates common label/control names if they exist on frmProcessingNotice.
' This keeps the module safe even if the form only has a caption or if the label
' was named differently during design.
'
' Supported label/control names:
'   lblDetail
'   lblMessage
'   lblStatus
'   lblProcessingMessage
'   txtDetail
'   txtMessage
'==============================================================================
Private Sub UpdateProcessingNoticeText(ByVal detailText As String)
    On Error Resume Next

    frmProcessingNotice.Caption = PROCESSING_NOTICE_CAPTION

    SetFormControlCaption frmProcessingNotice, "lblDetail", detailText
    SetFormControlCaption frmProcessingNotice, "lblMessage", detailText
    SetFormControlCaption frmProcessingNotice, "lblStatus", detailText
    SetFormControlCaption frmProcessingNotice, "lblProcessingMessage", detailText

    SetFormControlValue frmProcessingNotice, "txtDetail", detailText
    SetFormControlValue frmProcessingNotice, "txtMessage", detailText

    On Error GoTo 0
End Sub


'==============================================================================
' Safe label caption setter
'
' Attempts to set a UserForm control's Caption property.
' If the control does not exist, the error is ignored.
'==============================================================================
Private Sub SetFormControlCaption(ByVal targetForm As Object, ByVal controlName As String, ByVal captionText As String)
    On Error Resume Next
    targetForm.Controls(controlName).Caption = captionText
    On Error GoTo 0
End Sub


'==============================================================================
' Safe textbox value setter
'
' Attempts to set a UserForm control's Value property.
' If the control does not exist, the error is ignored.
'==============================================================================
Private Sub SetFormControlValue(ByVal targetForm As Object, ByVal controlName As String, ByVal valueText As String)
    On Error Resume Next
    targetForm.Controls(controlName).Value = valueText
    On Error GoTo 0
End Sub

