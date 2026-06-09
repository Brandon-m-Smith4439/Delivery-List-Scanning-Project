Attribute VB_Name = "frmManualScanEntry"
Attribute VB_Base = "0{4AA88821-5AC4-408C-9192-403CB0F08365}{DA5F76FC-82CA-4EBB-9BA7-BEFFB9D985C9}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = False
Option Explicit

Public WasCancelled As Boolean
Public SelectedMode As String
Public SelectedOrderNumber As Long
Public SelectedItemNumber As Long
Public SelectedQuantity As Long
Public SelectedReason As String

Private Sub UserForm_Initialize()
    StyleForm
    SetDefaults
    LoadIntakeModeDefaults
    ShowImportedStageForManualScan
End Sub

Public Sub LoadDefaults()
    WasCancelled = True
    SelectedMode = vbNullString
    SelectedOrderNumber = 0
    SelectedItemNumber = 0
    SelectedQuantity = 0
    SelectedReason = vbNullString

    StyleForm
    SetDefaults
    LoadIntakeModeDefaults
End Sub

Private Sub StyleForm()
    Me.BackColor = RGB(245, 247, 250)

    lblTitle.Font.Bold = True
    lblTitle.Font.Size = 28

    lblSubtitle.Font.Size = 10
    lblSubtitle.ForeColor = RGB(80, 80, 80)

    cmdApply.Default = True
    cmdCancel.Cancel = True

    cmdApply.BackColor = RGB(47, 75, 117)
    cmdApply.ForeColor = RGB(255, 255, 255)

    cmdCancel.BackColor = RGB(230, 230, 230)
    cmdCancel.ForeColor = RGB(0, 0, 0)
End Sub

Private Sub SetDefaults()
    optStaging.Value = False
    optOutbound.Value = False
    optInbound.Value = False

    txtOrder.Value = vbNullString
    txtItem.Value = vbNullString
    txtQty.Value = "1"

    On Error Resume Next
    txtReason.Value = vbNullString
    On Error GoTo 0
End Sub

Private Sub LoadIntakeModeDefaults()
    Dim currentMode As String

    currentMode = UCase$(Trim$(ModeFromStageProfile(GetSelectedStageProfile())))
    SelectedMode = currentMode

    Select Case currentMode
        Case "STAGING"
            optStaging.Value = True

        Case "SEND"
            optOutbound.Value = True

        Case "RECV"
            optInbound.Value = True

        Case Else
            optStaging.Value = True
            SelectedMode = "STAGING"
    End Select

    'Lock the mode choice so the intake form always matches the selected stage.
    optStaging.enabled = False
    optOutbound.enabled = False
    optInbound.enabled = False
End Sub

Private Function BuildMode() As String
    If optStaging.Value Then
        BuildMode = "STAGING"
    ElseIf optOutbound.Value Then
        BuildMode = "SEND"
    ElseIf optInbound.Value Then
        BuildMode = "RECV"
    End If
End Function

Private Function ParseWholeNumber(ByVal rawText As String, ByVal minValue As Long, ByVal maxValue As Long, ByRef outValue As Long) As Boolean
    rawText = Trim$(rawText)

    If Len(rawText) = 0 Then Exit Function
    If Not IsNumeric(rawText) Then Exit Function

    outValue = CLng(Val(rawText))

    If outValue < minValue Or outValue > maxValue Then Exit Function

    ParseWholeNumber = True
End Function

Private Function CleanReasonText(ByVal rawText As String) As String
    rawText = Trim$(CStr(rawText))

    rawText = Replace$(rawText, vbCrLf, " ")
    rawText = Replace$(rawText, vbCr, " ")
    rawText = Replace$(rawText, vbLf, " ")
    rawText = Replace$(rawText, vbTab, " ")

    Do While InStr(1, rawText, "  ", vbBinaryCompare) > 0
        rawText = Replace$(rawText, "  ", " ")
    Loop

    CleanReasonText = Trim$(rawText)
End Function

Private Function ValidateAndStoreSelections() As Boolean
    Dim ord As Long
    Dim itm As Long
    Dim qty As Long
    Dim reasonText As String

    SelectedMode = BuildMode()

    If Len(SelectedMode) = 0 Then
        MsgBox "Please choose a scan type.", vbExclamation, "Manual Scan Entry"
        Exit Function
    End If

    If Not ParseWholeNumber(txtOrder.Text, 1, 999999, ord) Then
        MsgBox "Please enter a valid order number between 1 and 999999.", vbExclamation, "Manual Scan Entry"
        txtOrder.SetFocus
        Exit Function
    End If

    If Not ParseWholeNumber(txtItem.Text, 1, 999, itm) Then
        MsgBox "Please enter a valid item number between 1 and 999.", vbExclamation, "Manual Scan Entry"
        txtItem.SetFocus
        Exit Function
    End If

    If Not ParseWholeNumber(txtQty.Text, 1, 9999, qty) Then
        MsgBox "Please enter a valid quantity between 1 and 9999.", vbExclamation, "Manual Scan Entry"
        txtQty.SetFocus
        Exit Function
    End If

    reasonText = vbNullString

    On Error Resume Next
    reasonText = CleanReasonText(txtReason.Text)
    On Error GoTo 0

    If Len(reasonText) > 150 Then
        MsgBox "Please shorten the reason to 150 characters or less.", vbExclamation, "Manual Scan Entry"
        txtReason.SetFocus
        Exit Function
    End If

    SelectedOrderNumber = ord
    SelectedItemNumber = itm
    SelectedQuantity = qty
    SelectedReason = reasonText

    ValidateAndStoreSelections = True
End Function

Private Sub cmdApply_Click()
    If Not ValidateAndStoreSelections() Then Exit Sub

    WasCancelled = False

    SubmitQueuedManualFromSharedFormData _
        SelectedOrderNumber, _
        SelectedItemNumber, _
        SelectedQuantity, _
        SelectedReason

    ShowImportedStageForManualScan
    Unload Me
End Sub

Private Sub cmdCancel_Click()
    WasCancelled = True
    Unload Me
End Sub

Private Sub UserForm_QueryClose(Cancel As Integer, CloseMode As Integer)
    If CloseMode = vbFormControlMenu Then
        WasCancelled = True
    End If
End Sub

