Attribute VB_Name = "frmManualScanEntry"
Attribute VB_Base = "0{F4CFFFFA-D7CA-4E44-8445-D958C662881B}{A95B9CE8-ACFD-46C3-A1E5-23ABAE3543E0}"
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

Private Sub UserForm_Initialize()
    StyleForm
    SetDefaults
End Sub

Public Sub LoadDefaults()
    WasCancelled = True
    SelectedMode = vbNullString
    SelectedOrderNumber = 0
    SelectedItemNumber = 0
    SelectedQuantity = 0

    StyleForm
    SetDefaults
End Sub

Private Sub StyleForm()
    Me.backColor = RGB(245, 247, 250)

    lblTitle.Font.Bold = True
    lblTitle.Font.Size = 28

    lblSubtitle.Font.Size = 10
    lblSubtitle.foreColor = RGB(80, 80, 80)

    cmdApply.Default = True
    cmdCancel.Cancel = True

    cmdApply.backColor = RGB(47, 75, 117)
    cmdApply.foreColor = RGB(255, 255, 255)

    cmdCancel.backColor = RGB(230, 230, 230)
    cmdCancel.foreColor = RGB(0, 0, 0)
End Sub

Private Sub SetDefaults()
    optStaging.Value = True
    txtOrder.Value = vbNullString
    txtItem.Value = vbNullString
    txtQty.Value = "1"
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

Private Function ValidateAndStoreSelections() As Boolean
    Dim ord As Long
    Dim itm As Long
    Dim qty As Long

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

    SelectedOrderNumber = ord
    SelectedItemNumber = itm
    SelectedQuantity = qty

    ValidateAndStoreSelections = True
End Function
Private Sub cmdApply_Click()
    If Not ValidateAndStoreSelections() Then Exit Sub

    If ApplyManualScanEntryTemplate(SelectedMode, SelectedOrderNumber, SelectedItemNumber, SelectedQuantity) Then
        Me.Hide

        On Error Resume Next
        ThisWorkbook.Worksheets("Delivery List").Activate
        Application.GoTo ThisWorkbook.Worksheets("Delivery List").Range("A1"), False
        ResumeQueueAfterManualScanForm
        On Error GoTo 0

        Unload Me
    End If
End Sub
Private Sub cmdCancel_Click()
    WasCancelled = True

    On Error Resume Next
    ThisWorkbook.Worksheets("Delivery List").Activate
    Application.GoTo ThisWorkbook.Worksheets("Delivery List").Range("A1"), False
    ResumeQueueAfterManualScanForm
    On Error GoTo 0

    Unload Me
End Sub
Private Sub UserForm_QueryClose(Cancel As Integer, CloseMode As Integer)
    If CloseMode = vbFormControlMenu Then
        WasCancelled = True

        On Error Resume Next
        ThisWorkbook.Worksheets("Delivery List").Activate
        Application.GoTo ThisWorkbook.Worksheets("Delivery List").Range("A1"), False
        ResumeQueueAfterManualScanForm
        On Error GoTo 0
    End If
End Sub
