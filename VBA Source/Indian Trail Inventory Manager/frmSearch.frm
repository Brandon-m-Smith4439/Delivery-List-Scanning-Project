Attribute VB_Name = "frmSearch"
Attribute VB_Base = "0{1FBEDBD4-1589-4A6A-816D-06C99E851780}{5B7ED57D-3DD7-41D1-8C33-01F3486788E8}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = False
Option Explicit

Private mMode As String
Private mSeed As String
Private mSelectedBay As String
Private mDefaultDeliveryKey As String

Private mLblTitle As Object
Private mLblStatus As Object
Private mTxtSearch As Object
Private mTxtDeliveryKey As Object
Private mTxtOrder As Object
Private mTxtBay As Object
Private mTxtNewBay As Object
Private mTxtGlassHeader As Object
Private mTxtNotes As Object
Private mCboAction As Object
Private mCboCategory As Object
Private WithEvents mCmdSubmit As CommandButton
Attribute mCmdSubmit.VB_VarHelpID = -1
Private WithEvents mCmdCancel As CommandButton
Attribute mCmdCancel.VB_VarHelpID = -1

Private Const DYNAMIC_TAG As String = "ITIM_DYNAMIC"

Public Sub Configure(ByVal modeText As String, _
                     Optional ByVal seedText As String = vbNullString, _
                     Optional ByVal selectedBayText As String = vbNullString, _
                     Optional ByVal defaultDeliveryKey As String = vbNullString)
    mMode = UCase$(Trim$(modeText))
    mSeed = seedText
    mSelectedBay = selectedBayText
    mDefaultDeliveryKey = defaultDeliveryKey

    BuildLayout
End Sub

Private Sub UserForm_Initialize()
    Me.Caption = "Indian Trail Bay Manager"
    Me.BackColor = RGB(245, 247, 250)
End Sub

Private Sub UserForm_Activate()
    If Len(mMode) = 0 Then
        Configure "SEARCH"
    End If
End Sub

Private Sub BuildLayout()
    Dim y As Single
    Dim titleText As String

    ResetRuntimeControls

    Me.Caption = "Indian Trail Bay Manager"
    Me.BackColor = RGB(245, 247, 250)
    Me.Width = 430
    Me.Height = 365

    Select Case mMode
        Case "BAY"
            titleText = "Bay Actions"
        Case "MANUAL"
            titleText = "Manual Bay Entry"
        Case "SDI"
            titleText = "Same Day Install"
        Case Else
            titleText = "Search"
            mMode = "SEARCH"
    End Select

    Set mLblTitle = AddLabel("lblTitle", titleText, 18, 12, 380, 24, True)
    mLblTitle.Font.Size = 16
    mLblTitle.ForeColor = RGB(47, 75, 117)

    y = 48

    Select Case mMode
        Case "SEARCH"
            AddSearchFields y
        Case "BAY"
            AddBayActionFields y
        Case "MANUAL"
            AddManualEntryFields y
        Case "SDI"
            AddSdiFields y
    End Select

    Set mLblStatus = AddLabel("lblStatus", vbNullString, 18, 276, 380, 18, False)
    mLblStatus.ForeColor = RGB(90, 100, 115)

    Set mCmdSubmit = Me.Controls.Add("Forms.CommandButton.1", DynamicName("cmdSubmit"), True)
    With mCmdSubmit
        .Tag = DYNAMIC_TAG
        .Caption = SubmitCaption()
        .Left = 220
        .Top = 302
        .Width = 84
        .Height = 28
        .BackColor = RGB(47, 75, 117)
        .ForeColor = RGB(255, 255, 255)
        .Font.Bold = True
    End With

    Set mCmdCancel = Me.Controls.Add("Forms.CommandButton.1", DynamicName("cmdCancel"), True)
    With mCmdCancel
        .Tag = DYNAMIC_TAG
        .Caption = "Cancel"
        .Left = 314
        .Top = 302
        .Width = 84
        .Height = 28
    End With
End Sub

Private Sub ResetRuntimeControls()
    Dim i As Long
    Dim ctl As Object
    Dim tagText As String

    Set mLblTitle = Nothing
    Set mLblStatus = Nothing
    Set mTxtSearch = Nothing
    Set mTxtDeliveryKey = Nothing
    Set mTxtOrder = Nothing
    Set mTxtBay = Nothing
    Set mTxtNewBay = Nothing
    Set mTxtGlassHeader = Nothing
    Set mTxtNotes = Nothing
    Set mCboAction = Nothing
    Set mCboCategory = Nothing
    Set mCmdSubmit = Nothing
    Set mCmdCancel = Nothing

    For i = Me.Controls.Count - 1 To 0 Step -1
        Set ctl = Me.Controls(i)

        tagText = vbNullString
        On Error Resume Next
        tagText = CStr(ctl.Tag)
        On Error GoTo 0

        If tagText = DYNAMIC_TAG Then
            On Error Resume Next
            Me.Controls.Remove ctl.Name
            On Error GoTo 0
        Else
            On Error Resume Next
            ctl.Visible = False
            On Error GoTo 0
        End If
    Next i
End Sub

Private Function DynamicName(ByVal baseName As String) As String
    DynamicName = "itimDyn_" & baseName
End Function

Private Sub AddSearchFields(ByRef y As Single)
    AddLabel "lblSearch", "Order, bay, or mirror", 18, y, 150, 18, False
    Set mTxtSearch = AddTextBox("txtSearch", 170, y - 2, 220, 22, IIf(Len(mSeed) > 0, mSeed, mSelectedBay))
    y = y + 34

    AddLabel "lblSearchHint", "Search checks the map first, then loaded bay assignments.", 18, y, 372, 36, False
End Sub

Private Sub AddBayActionFields(ByRef y As Single)
    AddLabel "lblAction", "Action", 18, y, 120, 18, False
    Set mCboAction = AddCombo("cboAction", 170, y - 2, 220, 22)
    mCboAction.AddItem "Clear Bay"
    mCboAction.AddItem "Scan Out of Bay"
    mCboAction.AddItem "Move Order"
    mCboAction.AddItem "Manual Exception"
    Select Case UCase$(mSeed)
        Case "CLEAR": mCboAction.Value = "Clear Bay"
        Case "SCANOUT", "SCAN OUT", "SCAN OUT OF BAY": mCboAction.Value = "Scan Out of Bay"
        Case "MOVE": mCboAction.Value = "Move Order"
        Case "EXCEPTION": mCboAction.Value = "Manual Exception"
        Case Else: mCboAction.Value = "Clear Bay"
    End Select
    y = y + 30

    AddLabel "lblOrder", "Order number", 18, y, 120, 18, False
    Set mTxtOrder = AddTextBox("txtOrder", 170, y - 2, 220, 22, vbNullString)
    y = y + 30

    AddLabel "lblBay", "Current bay", 18, y, 120, 18, False
    Set mTxtBay = AddTextBox("txtBay", 170, y - 2, 220, 22, mSelectedBay)
    y = y + 30

    AddLabel "lblNewBay", "New bay", 18, y, 120, 18, False
    Set mTxtNewBay = AddTextBox("txtNewBay", 170, y - 2, 220, 22, vbNullString)
    y = y + 30

    AddLabel "lblNotes", "Notes", 18, y, 120, 18, False
    Set mTxtNotes = AddTextBox("txtNotes", 170, y - 2, 220, 58, vbNullString)
    mTxtNotes.Multiline = True
End Sub

Private Sub AddManualEntryFields(ByRef y As Single)
    AddLabel "lblDelivery", "Delivery key", 18, y, 120, 18, False
    Set mTxtDeliveryKey = AddTextBox("txtDeliveryKey", 170, y - 2, 220, 22, mDefaultDeliveryKey)
    y = y + 30

    AddLabel "lblOrder", "Order number", 18, y, 120, 18, False
    Set mTxtOrder = AddTextBox("txtOrder", 170, y - 2, 220, 22, vbNullString)
    y = y + 30

    AddLabel "lblBay", "Bay", 18, y, 120, 18, False
    Set mTxtBay = AddTextBox("txtBay", 170, y - 2, 220, 22, mSelectedBay)
    y = y + 30

    AddLabel "lblCategory", "Glass category", 18, y, 120, 18, False
    Set mCboCategory = AddCombo("cboCategory", 170, y - 2, 220, 22)
    mCboCategory.AddItem "Tempered"
    mCboCategory.AddItem "MirrorAnnealed"
    mCboCategory.AddItem "ManualOversized"
    mCboCategory.AddItem "ManualException"
    mCboCategory.Value = "ManualException"
    y = y + 30

    AddLabel "lblHeader", "Glass header", 18, y, 120, 18, False
    Set mTxtGlassHeader = AddTextBox("txtGlassHeader", 170, y - 2, 220, 22, vbNullString)
    y = y + 30

    AddLabel "lblNotes", "Notes", 18, y, 120, 18, False
    Set mTxtNotes = AddTextBox("txtNotes", 170, y - 2, 220, 44, vbNullString)
    mTxtNotes.Multiline = True
End Sub

Private Sub AddSdiFields(ByRef y As Single)
    AddLabel "lblAction", "Action", 18, y, 120, 18, False
    Set mCboAction = AddCombo("cboAction", 170, y - 2, 220, 22)
    mCboAction.AddItem "Mark SDI"
    mCboAction.AddItem "Remove SDI"
    mCboAction.AddItem "Print SDI List"
    Select Case UCase$(mSeed)
        Case "REMOVE": mCboAction.Value = "Remove SDI"
        Case "PRINT", "PRINT SDI", "PRINT SDI LIST": mCboAction.Value = "Print SDI List"
        Case Else: mCboAction.Value = "Mark SDI"
    End Select
    y = y + 30

    AddLabel "lblDelivery", "Delivery key", 18, y, 120, 18, False
    Set mTxtDeliveryKey = AddTextBox("txtDeliveryKey", 170, y - 2, 220, 22, mDefaultDeliveryKey)
    y = y + 30

    AddLabel "lblOrder", "Order number", 18, y, 120, 18, False
    Set mTxtOrder = AddTextBox("txtOrder", 170, y - 2, 220, 22, vbNullString)
    y = y + 30

    AddLabel "lblNotes", "Notes", 18, y, 120, 18, False
    Set mTxtNotes = AddTextBox("txtNotes", 170, y - 2, 220, 70, vbNullString)
    mTxtNotes.Multiline = True
End Sub

Private Function AddLabel(ByVal controlName As String, ByVal captionText As String, _
                          ByVal leftPos As Single, ByVal topPos As Single, _
                          ByVal widthVal As Single, ByVal heightVal As Single, _
                          ByVal boldText As Boolean) As Object
    Set AddLabel = Me.Controls.Add("Forms.Label.1", DynamicName(controlName), True)
    With AddLabel
        .Tag = DYNAMIC_TAG
        .Caption = captionText
        .Left = leftPos
        .Top = topPos
        .Width = widthVal
        .Height = heightVal
        .BackStyle = fmBackStyleTransparent
        .Font.Name = "Aptos"
        .Font.Size = 10
        .Font.Bold = boldText
    End With
End Function

Private Function AddTextBox(ByVal controlName As String, ByVal leftPos As Single, _
                            ByVal topPos As Single, ByVal widthVal As Single, _
                            ByVal heightVal As Single, ByVal valueText As String) As Object
    Set AddTextBox = Me.Controls.Add("Forms.TextBox.1", DynamicName(controlName), True)
    With AddTextBox
        .Tag = DYNAMIC_TAG
        .Left = leftPos
        .Top = topPos
        .Width = widthVal
        .Height = heightVal
        .Text = valueText
        .Font.Name = "Aptos"
        .Font.Size = 10
    End With
End Function

Private Function AddCombo(ByVal controlName As String, ByVal leftPos As Single, _
                          ByVal topPos As Single, ByVal widthVal As Single, _
                          ByVal heightVal As Single) As Object
    Set AddCombo = Me.Controls.Add("Forms.ComboBox.1", DynamicName(controlName), True)
    With AddCombo
        .Tag = DYNAMIC_TAG
        .Left = leftPos
        .Top = topPos
        .Width = widthVal
        .Height = heightVal
        .Style = fmStyleDropDownList
        .Font.Name = "Aptos"
        .Font.Size = 10
    End With
End Function

Private Function SubmitCaption() As String
    Select Case mMode
        Case "SEARCH": SubmitCaption = "Search"
        Case "BAY": SubmitCaption = "Apply"
        Case "MANUAL": SubmitCaption = "Save"
        Case "SDI": SubmitCaption = "Apply"
        Case Else: SubmitCaption = "OK"
    End Select
End Function

Private Sub mCmdSubmit_Click()
    If Not ValidateForm Then Exit Sub

    ITIM_FormSubmit _
        mMode, _
        ComboValue(mCboAction), _
        TextValue(mTxtSearch), _
        TextValue(mTxtDeliveryKey), _
        TextValue(mTxtOrder), _
        TextValue(mTxtBay), _
        TextValue(mTxtNewBay), _
        ComboValue(mCboCategory), _
        TextValue(mTxtGlassHeader), _
        TextValue(mTxtNotes)

    Unload Me
End Sub

Private Sub mCmdCancel_Click()
    Unload Me
End Sub

Private Function ValidateForm() As Boolean
    ValidateForm = True

    Select Case mMode
        Case "SEARCH"
            If Len(TextValue(mTxtSearch)) = 0 Then
                ShowValidation "Enter an order, bay, or mirror number."
                ValidateForm = False
            End If

        Case "BAY"
            If Len(ComboValue(mCboAction)) = 0 Then
                ShowValidation "Choose an action."
                ValidateForm = False
            End If

        Case "MANUAL"
            If Len(TextValue(mTxtOrder)) = 0 Or Len(TextValue(mTxtBay)) = 0 Then
                ShowValidation "Order number and bay are required."
                ValidateForm = False
            End If

        Case "SDI"
            If Len(ComboValue(mCboAction)) = 0 Then
                ShowValidation "Choose an action."
                ValidateForm = False
            ElseIf UCase$(ComboValue(mCboAction)) <> "PRINT SDI LIST" And Len(TextValue(mTxtOrder)) = 0 Then
                ShowValidation "Order number is required."
                ValidateForm = False
            End If
    End Select
End Function

Private Sub ShowValidation(ByVal messageText As String)
    mLblStatus.Caption = messageText
    mLblStatus.ForeColor = RGB(156, 0, 6)
End Sub

Private Function TextValue(ByVal tb As Object) As String
    If tb Is Nothing Then
        TextValue = vbNullString
    Else
        TextValue = Trim$(tb.Text)
    End If
End Function

Private Function ComboValue(ByVal cb As Object) As String
    If cb Is Nothing Then
        ComboValue = vbNullString
    Else
        ComboValue = Trim$(cb.Value)
    End If
End Function

