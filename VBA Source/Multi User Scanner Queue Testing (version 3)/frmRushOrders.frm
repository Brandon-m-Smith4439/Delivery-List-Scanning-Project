Attribute VB_Name = "frmRushOrders"
Attribute VB_Base = "0{62EBDADB-7A9C-409B-A3A7-C2C2E041F58A}{EEC5EC1B-9DD3-4595-9F9E-38165E9258BF}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = False
Option Explicit

'==============================================================================
' UserForm: frmRushOrders
'
' This form builds its own controls at runtime.
' Do not manually add controls unless you want to customize the layout later.
'==============================================================================

Private txtOrders As MSForms.TextBox
Private txtNote As MSForms.TextBox
Private txtStatus As MSForms.TextBox
Private lstRush As MSForms.ListBox
Private chkPrintAfterMark As MSForms.CheckBox
Private imgLogo As MSForms.Image

Private WithEvents cmdMark As MSForms.CommandButton
Attribute cmdMark.VB_VarHelpID = -1
Private WithEvents cmdClearTyped As MSForms.CommandButton
Attribute cmdClearTyped.VB_VarHelpID = -1
Private WithEvents cmdRefresh As MSForms.CommandButton
Attribute cmdRefresh.VB_VarHelpID = -1
Private WithEvents cmdPreviewAll As MSForms.CommandButton
Attribute cmdPreviewAll.VB_VarHelpID = -1
Private WithEvents cmdPrintAll As MSForms.CommandButton
Attribute cmdPrintAll.VB_VarHelpID = -1
Private WithEvents cmdPreviewSelected As MSForms.CommandButton
Attribute cmdPreviewSelected.VB_VarHelpID = -1
Private WithEvents cmdPrintSelected As MSForms.CommandButton
Attribute cmdPrintSelected.VB_VarHelpID = -1
Private WithEvents cmdClearSelected As MSForms.CommandButton
Attribute cmdClearSelected.VB_VarHelpID = -1
Private WithEvents cmdClose As MSForms.CommandButton
Attribute cmdClose.VB_VarHelpID = -1

Private Sub UserForm_Initialize()
    BuildFormLayout
    RefreshRushList
End Sub

Private Sub BuildFormLayout()
    Dim lbl As MSForms.label

    Me.Caption = "Rush Orders"
    Me.Width = 790
    Me.Height = 560
    Me.backColor = RGB(245, 247, 250)

    AddCompanyLogo 628, 10, 126, 44

    Set lbl = AddLabel("lblTitle", "RUSH ORDERS", 14, 12, 300, 28)
    lbl.Font.Size = 18
    lbl.Font.Bold = True
    lbl.foreColor = RGB(192, 0, 0)

    Set lbl = AddLabel("lblInstructions", _
        "Enter order numbers, order-item pairs, or barcodes. Examples: 231860, 231860-002, T200231860002000", _
        14, 46, 595, 20)
    lbl.Font.Size = 9

    Set lbl = AddLabel("lblOrders", "Orders / Items to mark or clear:", 14, 78, 230, 18)
    lbl.Font.Bold = True

    Set txtOrders = Me.Controls.Add("Forms.TextBox.1", "txtOrders", True)
    With txtOrders
        .Left = 14
        .Top = 100
        .Width = 350
        .Height = 80
        .Multiline = True
        .EnterKeyBehavior = True
        .ScrollBars = fmScrollBarsVertical
    End With

    Set lbl = AddLabel("lblNote", "Rush note / reason:", 384, 78, 180, 18)
    lbl.Font.Bold = True

    Set txtNote = Me.Controls.Add("Forms.TextBox.1", "txtNote", True)
    With txtNote
        .Left = 384
        .Top = 100
        .Width = 370
        .Height = 80
        .Multiline = True
        .EnterKeyBehavior = True
        .ScrollBars = fmScrollBarsVertical
    End With

    Set chkPrintAfterMark = Me.Controls.Add("Forms.CheckBox.1", "chkPrintAfterMark", True)
    With chkPrintAfterMark
        .Left = 14
        .Top = 190
        .Width = 220
        .Height = 20
        .Caption = "Print after marking rush"
        .Value = False
        .backColor = Me.backColor
    End With

    Set cmdMark = AddButton("cmdMark", "MARK AS RUSH", 14, 220, 130, 32, RGB(192, 0, 0))
    Set cmdClearTyped = AddButton("cmdClearTyped", "CLEAR TYPED", 154, 220, 120, 32, RGB(100, 100, 100))
    Set cmdRefresh = AddButton("cmdRefresh", "REFRESH LIST", 284, 220, 120, 32, RGB(60, 90, 150))

    Set lbl = AddLabel("lblCurrent", "Current rush orders:", 14, 270, 180, 18)
    lbl.Font.Bold = True

    Set lbl = AddLabel("lblListHeader", _
        "Order        Item    Qty      Route        Customer                         Dimensions                      Note", _
        14, 292, 730, 16)
    lbl.Font.Size = 8
    lbl.Font.Bold = True

    Set lstRush = Me.Controls.Add("Forms.ListBox.1", "lstRush", True)
    With lstRush
        .Left = 14
        .Top = 310
        .Width = 740
        .Height = 130
        .ColumnCount = 8
        .ColumnWidths = "0 pt;65 pt;45 pt;45 pt;75 pt;165 pt;135 pt;190 pt"
        .MultiSelect = fmMultiSelectMulti
    End With

    Set cmdPreviewAll = AddButton("cmdPreviewAll", "PREVIEW ALL", 14, 455, 105, 30, RGB(80, 80, 80))
    Set cmdPrintAll = AddButton("cmdPrintAll", "PRINT ALL", 128, 455, 95, 30, RGB(192, 0, 0))
    Set cmdPreviewSelected = AddButton("cmdPreviewSelected", "PREVIEW SELECTED", 238, 455, 135, 30, RGB(80, 80, 80))
    Set cmdPrintSelected = AddButton("cmdPrintSelected", "PRINT SELECTED", 382, 455, 125, 30, RGB(192, 0, 0))
    Set cmdClearSelected = AddButton("cmdClearSelected", "CLEAR SELECTED", 516, 455, 125, 30, RGB(100, 100, 100))
    Set cmdClose = AddButton("cmdClose", "CLOSE", 658, 455, 95, 30, RGB(60, 60, 60))

    Set txtStatus = Me.Controls.Add("Forms.TextBox.1", "txtStatus", True)
    With txtStatus
        .Left = 14
        .Top = 495
        .Width = 740
        .Height = 28
        .Locked = True
        .backColor = RGB(255, 255, 255)
        .BorderStyle = fmBorderStyleSingle
        .Text = "Ready."
    End With
End Sub

Private Sub AddCompanyLogo(ByVal leftPos As Single, _
                           ByVal topPos As Single, _
                           ByVal widthVal As Single, _
                           ByVal heightVal As Single)
    Dim logoPath As String

    If Len(ThisWorkbook.Path) = 0 Then Exit Sub

    logoPath = ThisWorkbook.Path & Application.PathSeparator & "Barefoot Logo.jpg"
    If Len(Dir$(logoPath)) = 0 Then Exit Sub

    On Error GoTo LogoError

    Set imgLogo = Me.Controls.Add("Forms.Image.1", "imgLogo", True)

    With imgLogo
        .Left = leftPos
        .Top = topPos
        .Width = widthVal
        .Height = heightVal
        .Picture = LoadPicture(logoPath)
        .PictureSizeMode = fmPictureSizeModeZoom
        .BorderStyle = fmBorderStyleNone
        .BackStyle = fmBackStyleTransparent
    End With

    Exit Sub

LogoError:
    On Error Resume Next
    If Not imgLogo Is Nothing Then Me.Controls.Remove imgLogo.Name
    Set imgLogo = Nothing
    On Error GoTo 0
End Sub

Private Function AddLabel(ByVal controlName As String, _
                          ByVal captionText As String, _
                          ByVal leftPos As Single, _
                          ByVal topPos As Single, _
                          ByVal widthVal As Single, _
                          ByVal heightVal As Single) As MSForms.label
    Set AddLabel = Me.Controls.Add("Forms.Label.1", controlName, True)

    With AddLabel
        .Caption = captionText
        .Left = leftPos
        .Top = topPos
        .Width = widthVal
        .Height = heightVal
        .backColor = Me.backColor
    End With
End Function

Private Function AddButton(ByVal controlName As String, _
                           ByVal captionText As String, _
                           ByVal leftPos As Single, _
                           ByVal topPos As Single, _
                           ByVal widthVal As Single, _
                           ByVal heightVal As Single, _
                           ByVal backColorValue As Long) As MSForms.CommandButton
    Set AddButton = Me.Controls.Add("Forms.CommandButton.1", controlName, True)

    With AddButton
        .Caption = captionText
        .Left = leftPos
        .Top = topPos
        .Width = widthVal
        .Height = heightVal
        .backColor = backColorValue
        .foreColor = RGB(255, 255, 255)
        .Font.Bold = True
    End With
End Function

Private Sub cmdMark_Click()
    Dim notFoundText As String
    Dim updatedCount As Long
    Dim copiesToPrint As Long

    On Error GoTo ErrHandler

    If Len(Trim$(txtOrders.Text)) = 0 Then
        MsgBox "Enter at least one order number, order/item, or barcode.", vbExclamation, "Rush Orders"
        Exit Sub
    End If

    updatedCount = RushOrders_MarkOrders(txtOrders.Text, txtNote.Text, notFoundText)

    RefreshRushList

    txtStatus.Text = updatedCount & " row(s) marked as RUSH."

    If Len(Trim$(notFoundText)) > 0 Then
        MsgBox "These entries were not found:" & vbCrLf & vbCrLf & notFoundText, _
               vbExclamation, "Rush Orders"
    End If

    If updatedCount > 0 Then
        If chkPrintAfterMark.Value Then
            copiesToPrint = RushOrders_PromptCopies("Rush Print Copies")
            If copiesToPrint > 0 Then RushOrders_PrintAllRush copiesToPrint
        End If
    End If

    Exit Sub

ErrHandler:
    MsgBox "Could not mark rush order(s)." & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbExclamation, "Rush Orders"
End Sub

Private Sub cmdClearTyped_Click()
    Dim notFoundText As String
    Dim clearedCount As Long

    On Error GoTo ErrHandler

    If Len(Trim$(txtOrders.Text)) = 0 Then
        MsgBox "Enter at least one order number, order/item, or barcode to clear.", _
               vbExclamation, "Rush Orders"
        Exit Sub
    End If

    If MsgBox("Clear RUSH from the typed order(s)?", _
              vbYesNo + vbQuestion, "Clear Rush") <> vbYes Then
        Exit Sub
    End If

    clearedCount = RushOrders_ClearOrders(txtOrders.Text, notFoundText)

    RefreshRushList

    txtStatus.Text = clearedCount & " rush row(s) cleared."

    If Len(Trim$(notFoundText)) > 0 Then
        MsgBox "These entries were not found:" & vbCrLf & vbCrLf & notFoundText, _
               vbExclamation, "Rush Orders"
    End If

    Exit Sub

ErrHandler:
    MsgBox "Could not clear typed rush order(s)." & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbExclamation, "Rush Orders"
End Sub

Private Sub cmdRefresh_Click()
    RefreshRushList
End Sub

Private Sub cmdPreviewAll_Click()
    On Error GoTo ErrHandler

    If RushOrders_CountRushRows() = 0 Then
        MsgBox "There are no current rush orders to preview.", vbInformation, "Rush Orders"
        Exit Sub
    End If

    RushOrders_PreviewAllRush
    Exit Sub

ErrHandler:
    MsgBox "Could not preview rush forms." & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbExclamation, "Rush Preview"
End Sub

Private Sub cmdPrintAll_Click()
    Dim copiesToPrint As Long

    On Error GoTo ErrHandler

    If RushOrders_CountRushRows() = 0 Then
        MsgBox "There are no current rush orders to print.", vbInformation, "Rush Orders"
        Exit Sub
    End If

    copiesToPrint = RushOrders_PromptCopies("Rush Print Copies")
    If copiesToPrint < 1 Then Exit Sub

    RushOrders_PrintAllRush copiesToPrint
    Exit Sub

ErrHandler:
    MsgBox "Could not print rush forms." & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbExclamation, "Rush Print"
End Sub

Private Sub cmdPreviewSelected_Click()
    Dim selectedRows As Collection

    On Error GoTo ErrHandler

    Set selectedRows = SelectedRushRows()

    If selectedRows.Count = 0 Then
        MsgBox "Select at least one rush row from the list.", vbExclamation, "Rush Orders"
        Exit Sub
    End If

    RushOrders_PreviewSelectedRush selectedRows
    Exit Sub

ErrHandler:
    MsgBox "Could not preview selected rush forms." & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbExclamation, "Rush Preview"
End Sub

Private Sub cmdPrintSelected_Click()
    Dim selectedRows As Collection
    Dim copiesToPrint As Long

    On Error GoTo ErrHandler

    Set selectedRows = SelectedRushRows()

    If selectedRows.Count = 0 Then
        MsgBox "Select at least one rush row from the list.", vbExclamation, "Rush Orders"
        Exit Sub
    End If

    copiesToPrint = RushOrders_PromptCopies("Rush Print Copies")
    If copiesToPrint < 1 Then Exit Sub

    RushOrders_PrintSelectedRush selectedRows, copiesToPrint
    Exit Sub

ErrHandler:
    MsgBox "Could not print selected rush forms." & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbExclamation, "Rush Print"
End Sub

Private Sub cmdClearSelected_Click()
    Dim selectedRows As Collection
    Dim clearedCount As Long

    On Error GoTo ErrHandler

    Set selectedRows = SelectedRushRows()

    If selectedRows.Count = 0 Then
        MsgBox "Select at least one rush row from the list.", vbExclamation, "Rush Orders"
        Exit Sub
    End If

    If MsgBox("Clear RUSH from the selected row(s)?", _
              vbYesNo + vbQuestion, "Clear Rush") <> vbYes Then
        Exit Sub
    End If

    clearedCount = RushOrders_ClearRowsBySourceRow(selectedRows)

    RefreshRushList

    txtStatus.Text = clearedCount & " selected rush row(s) cleared."

    Exit Sub

ErrHandler:
    MsgBox "Could not clear selected rush row(s)." & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbExclamation, "Rush Orders"
End Sub

Private Sub cmdClose_Click()
    Unload Me
End Sub

Private Sub RefreshRushList()
    Dim rows As Collection
    Dim item As Variant
    Dim idx As Long

    On Error GoTo ErrHandler

    RushOrders_EnsureReady

    Set rows = RushOrders_GetRushRows()

    lstRush.Clear

    For Each item In rows
        lstRush.AddItem CStr(item("row"))
        idx = lstRush.ListCount - 1

        lstRush.List(idx, 1) = CStr(item("order"))
        lstRush.List(idx, 2) = Format$(CLng(Val(CStr(item("item")))), "000")
        lstRush.List(idx, 3) = CStr(item("qty"))
        lstRush.List(idx, 4) = CStr(item("route"))
        lstRush.List(idx, 5) = CStr(item("customer"))
        lstRush.List(idx, 6) = CStr(item("dimensions"))
        lstRush.List(idx, 7) = CStr(item("note"))
    Next item

    txtStatus.Text = rows.Count & " current rush row(s)."

    Exit Sub

ErrHandler:
    txtStatus.Text = "Could not refresh rush list. Error " & Err.Number & ": " & Err.Description
End Sub

Private Function SelectedRushRows() As Collection
    Dim out As New Collection
    Dim i As Long

    If lstRush.ListCount = 0 Then
        Set SelectedRushRows = out
        Exit Function
    End If

    For i = 0 To lstRush.ListCount - 1
        If lstRush.Selected(i) Then
            out.Add CLng(lstRush.List(i, 0))
        End If
    Next i

    Set SelectedRushRows = out
End Function

Private Sub UserForm_QueryClose(Cancel As Integer, CloseMode As Integer)
    'No special handling needed. This keeps the X button normal.
End Sub


