Attribute VB_Name = "frmScanAlert"
Attribute VB_Base = "0{7045F4BF-4D59-442E-A527-0EC7C132D0C1}{59584274-5E00-44FE-87DD-B8394985BF1D}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = False
Option Explicit
Public Sub LoadAlert(ByVal titleText As String, _
                     ByVal messageText As String, _
                     ByVal codeText As String, _
                     Optional ByVal allowOverride As Boolean = False)

    Dim showOverride As Boolean

    On Error GoTo ErrHandler

    Me.Caption = "Scanning Alert"

    showOverride = allowOverride

    'Outbound/staging manual errors are not override-ready yet.
    If InStr(1, messageText, "Manual outbound scan blocked", vbTextCompare) > 0 Then showOverride = False
    If InStr(1, messageText, "Stage first", vbTextCompare) > 0 Then showOverride = False
    If InStr(1, messageText, "Not enough staged", vbTextCompare) > 0 Then showOverride = False

    'Only set text. Do not change size, font, position, width, height, alignment, etc.
    lblTitle.Caption = titleText
    lblMessage.Caption = messageText
    lblCode.Caption = codeText

    ApplyScanAlertTitleColor titleText, codeText, messageText

    cmdOverride.Visible = showOverride

    txtScanTrap.Text = vbNullString

    Exit Sub

ErrHandler:
    MsgBox "Could not load scan alert form." & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbExclamation, "Scan Alert"
End Sub
Private Sub ApplyScanAlertTitleColor(ByVal titleText As String, _
                                     ByVal codeText As String, _
                                     ByVal messageText As String)
    Dim keyText As String

    keyText = UCase$(Trim$(titleText & " " & codeText & " " & messageText))

    Select Case True
Case InStr(1, keyText, "ERROR", vbTextCompare) > 0 Or _
     InStr(1, keyText, "BLOCKED", vbTextCompare) > 0 Or _
     InStr(1, keyText, "FAILED", vbTextCompare) > 0 Or _
     InStr(1, keyText, "MISSING", vbTextCompare) > 0 Or _
     InStr(1, keyText, "NOT_FOUND", vbTextCompare) > 0 Or _
     InStr(1, keyText, "NOT FOUND", vbTextCompare) > 0
            lblTitle.ForeColor = RGB(192, 0, 0)       'red

        Case InStr(1, keyText, "OVERRIDE", vbTextCompare) > 0
            lblTitle.ForeColor = RGB(191, 95, 0)      'orange

        Case InStr(1, keyText, "SNAPSHOT", vbTextCompare) > 0 Or _
             InStr(1, keyText, "OUT OF DATE", vbTextCompare) > 0
            lblTitle.ForeColor = RGB(156, 101, 0)     'yellow/brown

        Case InStr(1, keyText, "INDIAN_TRAIL_SDI", vbTextCompare) > 0 Or _
             InStr(1, keyText, "SAME DAY INSTALL", vbTextCompare) > 0
            lblTitle.ForeColor = RGB(0, 92, 112)      'teal

        Case InStr(1, keyText, "INDIAN_TRAIL_BAY", vbTextCompare) > 0 Or _
             InStr(1, keyText, "BAY ASSIGNMENT", vbTextCompare) > 0 Or _
             InStr(1, keyText, "BAY ASSIGNED", vbTextCompare) > 0
            lblTitle.ForeColor = RGB(0, 97, 0)        'green

        Case InStr(1, keyText, "OK", vbTextCompare) > 0 Or _
             InStr(1, keyText, "SAVED", vbTextCompare) > 0
            lblTitle.ForeColor = RGB(0, 97, 0)        'green

        Case Else
            lblTitle.ForeColor = RGB(0, 0, 0)         'black/default
    End Select
End Sub

Private Sub UserForm_Initialize()
    Me.Caption = "Scanning Alert"

    txtScanTrap.Left = 2
    txtScanTrap.Top = 2
    txtScanTrap.Width = 1
    txtScanTrap.Height = 1
    txtScanTrap.BorderStyle = fmBorderStyleNone
    txtScanTrap.BackColor = Me.BackColor
    txtScanTrap.ForeColor = Me.BackColor

    cmdClear.Default = False
    cmdClear.Cancel = False

    cmdOverride.Default = False
    cmdOverride.Cancel = False
End Sub

Private Sub UserForm_Activate()
    On Error Resume Next
    txtScanTrap.Text = vbNullString
    txtScanTrap.SetFocus
    On Error GoTo 0
End Sub

Private Sub txtScanTrap_KeyDown(ByVal KeyCode As MSForms.ReturnInteger, ByVal Shift As Integer)
    'Swallow scanner Enter and barcode keystrokes.
    KeyCode = 0
End Sub

Private Sub txtScanTrap_KeyPress(ByVal KeyAscii As MSForms.ReturnInteger)
    'Swallow scanner characters.
    KeyAscii = 0
End Sub

Private Sub txtScanTrap_Change()
    'Keep the trap empty even if scanner text gets through.
    txtScanTrap.Text = vbNullString
End Sub

Private Sub cmdClear_Click()
    DismissScanAlert
End Sub

Private Sub cmdOverride_Click()
    ApprovePendingReceiveOverride
End Sub

Private Sub UserForm_QueryClose(Cancel As Integer, CloseMode As Integer)
    'Do not let accidental keyboard input close this alert.
    If CloseMode = vbFormControlMenu Then
        Cancel = True
    End If
End Sub
