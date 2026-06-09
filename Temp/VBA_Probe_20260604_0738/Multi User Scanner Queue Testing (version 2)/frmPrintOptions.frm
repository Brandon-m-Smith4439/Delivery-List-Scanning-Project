Attribute VB_Name = "frmPrintOptions"
Attribute VB_Base = "0{A8A6634D-D9D1-4ADF-A88D-56C842FDDCA7}{3A9E4A54-B96E-47C8-82BC-4517AB5AD0D1}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = False
Option Explicit

Private mWs As Worksheet
Private mFirstDataRow As Long
Private mLastRealRow As Long
Private mOrderCol As Long
Private mItemCol As Long
Private mIsRefreshing As Boolean

Public WasCancelled As Boolean
Public SelectedPrintKind As String
Public SelectedDestinationMode As String
Public selectedGlassKeys As String
Public selectedAction As String
Public selectedCopies As Long

Private Sub UserForm_Initialize()
    StyleForm
End Sub

Public Sub LoadOptions(ByVal ws As Worksheet, _
                       ByVal firstDataRow As Long, _
                       ByVal lastRealRow As Long, _
                       ByVal orderCol As Long, _
                       ByVal itemCol As Long)

    Set mWs = ws
    mFirstDataRow = firstDataRow
    mLastRealRow = lastRealRow
    mOrderCol = orderCol
    mItemCol = itemCol

    WasCancelled = True
    SelectedPrintKind = vbNullString
    SelectedDestinationMode = vbNullString
    selectedGlassKeys = vbNullString
    selectedAction = vbNullString
    selectedCopies = 1

    StyleForm
    SetDefaults
    RefreshAvailableOptions
End Sub

Private Sub StyleForm()
    Me.backColor = RGB(245, 247, 250)

    lblTitle.Font.Bold = True
    lblTitle.Font.Size = 28

    lblSubtitle.Font.Size = 10
    lblSubtitle.foreColor = RGB(80, 80, 80)

    fraDestination.Font.Bold = True
    fraPrintFilter.Font.Bold = True
    fraGlassTypes.Font.Bold = True

    lblGlassHint.Font.Size = 10
    lblGlassHint.foreColor = RGB(90, 90, 90)

    lstGlassTypes.MultiSelect = fmMultiSelectMulti
    lstGlassTypes.ColumnCount = 2
    lstGlassTypes.ColumnWidths = "180 pt;0 pt"
    lstGlassTypes.IntegralHeight = False

    cmdPreview.Default = True
    cmdCancel.Cancel = True

    cmdPreview.backColor = RGB(47, 75, 117)
    cmdPreview.foreColor = RGB(255, 255, 255)

    cmdPrint.backColor = RGB(70, 140, 95)
    cmdPrint.foreColor = RGB(255, 255, 255)

    cmdCancel.backColor = RGB(230, 230, 230)
    cmdCancel.foreColor = RGB(0, 0, 0)
End Sub

Private Sub SetDefaults()
    chkAllDestinations.Value = False
    chkIndianTrail.Value = True
    chkGreenville.Value = False
    chkCustomerPickup.Value = False

    chkAllGlassTypes.Value = False
    ClearGlassSelections

    optOrders.Value = True

    ToggleDestinationControls
    ToggleGlassControls
End Sub

Private Sub chkAllDestinations_Click()
    If mIsRefreshing Then Exit Sub
    ToggleDestinationControls
    RefreshAvailableOptions
End Sub

Private Sub chkIndianTrail_Click()
    If mIsRefreshing Then Exit Sub
    SyncAllDestinationCheck
    RefreshAvailableOptions
End Sub

Private Sub chkGreenville_Click()
    If mIsRefreshing Then Exit Sub
    SyncAllDestinationCheck
    RefreshAvailableOptions
End Sub

Private Sub chkCustomerPickup_Click()
    If mIsRefreshing Then Exit Sub
    SyncAllDestinationCheck
    RefreshAvailableOptions
End Sub

Private Sub chkAllGlassTypes_Click()
    If mIsRefreshing Then Exit Sub
    ToggleGlassControls
End Sub

Private Sub optOrders_Click()
    If mIsRefreshing Then Exit Sub
    RefreshAvailableOptions
End Sub

Private Sub optRemakes_Click()
    If mIsRefreshing Then Exit Sub
    RefreshAvailableOptions
End Sub

Private Sub optUpdatedOrders_Click()
    If mIsRefreshing Then Exit Sub
    RefreshAvailableOptions
End Sub

Private Sub optUpdatedRemakes_Click()
    If mIsRefreshing Then Exit Sub
    RefreshAvailableOptions
End Sub

Private Sub optUpdatedAll_Click()
    If mIsRefreshing Then Exit Sub
    RefreshAvailableOptions
End Sub

Private Sub optAllOrders_Click()
    If mIsRefreshing Then Exit Sub
    RefreshAvailableOptions
End Sub
Private Sub RefreshAvailableOptions()
    Dim hasStandard As Boolean
    Dim hasGreenville As Boolean
    Dim hasCPU As Boolean

    Dim hasUpdatedOrders As Boolean
    Dim hasUpdatedRemakes As Boolean
    Dim hasUpdatedAll As Boolean

    Dim currentPrintKind As String
    Dim destinationMode As String
    Dim sections As Collection
    Dim i As Long
    Dim sectionInfo As Variant
    Dim rowIndex As Long

    If mWs Is Nothing Then Exit Sub

    mIsRefreshing = True

    'Destination availability based on ALL rows / ALL print kinds
    hasStandard = HasPrintableRowsForTemplate(mWs, mFirstDataRow, mLastRealRow, mOrderCol, mItemCol, "STANDARD", "ALL")
    hasGreenville = HasPrintableRowsForTemplate(mWs, mFirstDataRow, mLastRealRow, mOrderCol, mItemCol, "GREENVILLE", "ALL")
    hasCPU = HasPrintableRowsForTemplate(mWs, mFirstDataRow, mLastRealRow, mOrderCol, mItemCol, "CPU", "ALL")

    'Keep them visible, store availability in Tag
    chkIndianTrail.Visible = True
    chkGreenville.Visible = True
    chkCustomerPickup.Visible = True

    chkIndianTrail.Tag = IIf(hasStandard, "1", "0")
    chkGreenville.Tag = IIf(hasGreenville, "1", "0")
    chkCustomerPickup.Tag = IIf(hasCPU, "1", "0")

    If Not hasStandard Then chkIndianTrail.Value = False
    If Not hasGreenville Then chkGreenville.Value = False
    If Not hasCPU Then chkCustomerPickup.Value = False

    'If none selected and not All Destinations, pick first available one
    If Not chkAllDestinations.Value Then
        If Not (chkIndianTrail.Value Or chkGreenville.Value Or chkCustomerPickup.Value) Then
            If hasStandard Then
                chkIndianTrail.Value = True
            ElseIf hasGreenville Then
                chkGreenville.Value = True
            ElseIf hasCPU Then
                chkCustomerPickup.Value = True
            Else
                chkAllDestinations.Value = True
            End If
        End If
    End If

    ToggleDestinationControls

    destinationMode = BuildDestinationModeForAvailability()

    'Updated filter availability based on currently selected destination(s)
    hasUpdatedOrders = HasPrintableRowsForTemplate(mWs, mFirstDataRow, mLastRealRow, mOrderCol, mItemCol, destinationMode, "UPDATED_ORDERS")
    hasUpdatedRemakes = HasPrintableRowsForTemplate(mWs, mFirstDataRow, mLastRealRow, mOrderCol, mItemCol, destinationMode, "UPDATED_REMAKES")
    hasUpdatedAll = HasPrintableRowsForTemplate(mWs, mFirstDataRow, mLastRealRow, mOrderCol, mItemCol, destinationMode, "UPDATED_ALL")

    'Keep them visible, just disable when unavailable
    optUpdatedOrders.Visible = True
    optUpdatedRemakes.Visible = True
    optUpdatedAll.Visible = True

    optUpdatedOrders.Enabled = hasUpdatedOrders
    optUpdatedRemakes.Enabled = hasUpdatedRemakes
    optUpdatedAll.Enabled = hasUpdatedAll

    currentPrintKind = BuildPrintKind()

    If currentPrintKind = "UPDATED_ORDERS" And Not hasUpdatedOrders Then optOrders.Value = True
    If currentPrintKind = "UPDATED_REMAKES" And Not hasUpdatedRemakes Then optOrders.Value = True
    If currentPrintKind = "UPDATED_ALL" And Not hasUpdatedAll Then optOrders.Value = True

    currentPrintKind = BuildPrintKind()

    Set sections = GetDeliveryListSectionsForPrintKind(mWs, mFirstDataRow, mLastRealRow, mOrderCol, mItemCol, destinationMode, currentPrintKind)

    lstGlassTypes.Clear
    If Not sections Is Nothing Then
        For i = 1 To sections.Count
            sectionInfo = sections(i)
            If Len(Trim$(CStr(sectionInfo(0)))) > 0 Then
                lstGlassTypes.AddItem CStr(sectionInfo(0))
                rowIndex = lstGlassTypes.ListCount - 1
                lstGlassTypes.List(rowIndex, 1) = UCase$(Trim$(CStr(sectionInfo(0))))
            End If
        Next i
    End If

    If lstGlassTypes.ListCount = 0 Then
        chkAllGlassTypes.Value = False
        chkAllGlassTypes.Enabled = False
    Else
        chkAllGlassTypes.Enabled = True
    End If

    ToggleGlassControls

    mIsRefreshing = False
End Sub
Private Function BuildDestinationModeForAvailability() As String
    If chkAllDestinations.Value Then
        BuildDestinationModeForAvailability = "ALL"
    Else
        BuildDestinationModeForAvailability = GetSafeVisibleDestinationModeTemplate( _
            chkIndianTrail.Value And chkIndianTrail.Tag = "1", _
            chkGreenville.Value And chkGreenville.Tag = "1", _
            chkCustomerPickup.Value And chkCustomerPickup.Tag = "1")
    End If

    If Len(BuildDestinationModeForAvailability) = 0 Then
        BuildDestinationModeForAvailability = "ALL"
    End If
End Function

Private Sub SyncAllDestinationCheck()
    If chkIndianTrail.Value Or chkGreenville.Value Or chkCustomerPickup.Value Then
        chkAllDestinations.Value = False
    End If
End Sub
Private Sub ToggleDestinationControls()
    Dim enabledState As Boolean

    enabledState = Not chkAllDestinations.Value

    chkIndianTrail.Enabled = enabledState And (chkIndianTrail.Tag = "1")
    chkGreenville.Enabled = enabledState And (chkGreenville.Tag = "1")
    chkCustomerPickup.Enabled = enabledState And (chkCustomerPickup.Tag = "1")

    If chkAllDestinations.Value Then
        chkIndianTrail.Value = False
        chkGreenville.Value = False
        chkCustomerPickup.Value = False
    End If
End Sub

Private Sub ToggleGlassControls()
    lstGlassTypes.Enabled = Not chkAllGlassTypes.Value
    lblGlassHint.Enabled = Not chkAllGlassTypes.Value

    If chkAllGlassTypes.Value Then
        ClearGlassSelections
    End If
End Sub

Private Sub ClearGlassSelections()
    Dim i As Long

    For i = 0 To lstGlassTypes.ListCount - 1
        lstGlassTypes.Selected(i) = False
    Next i
End Sub

Private Sub AddToken(ByRef tokenList As String, ByVal token As String)
    If Len(token) = 0 Then Exit Sub

    token = UCase$(Trim$(token))

    If Not TokenListContains(tokenList, token) Then
        If Len(tokenList) > 0 Then tokenList = tokenList & "|"
        tokenList = tokenList & token
    End If
End Sub

Private Function TokenListContains(ByVal tokenList As String, ByVal token As String) As Boolean
    Dim parts() As String
    Dim i As Long

    token = UCase$(Trim$(token))
    tokenList = UCase$(Trim$(tokenList))

    If tokenList = "ALL" Then
        TokenListContains = True
        Exit Function
    End If

    If Len(tokenList) = 0 Then Exit Function

    parts = Split(tokenList, "|")
    For i = LBound(parts) To UBound(parts)
        If Trim$(parts(i)) = token Then
            TokenListContains = True
            Exit Function
        End If
    Next i
End Function
Private Function BuildDestinationMode() As String
    Dim outText As String

    If chkAllDestinations.Value Then
        BuildDestinationMode = "ALL"
        Exit Function
    End If

    If chkIndianTrail.Value And chkIndianTrail.Tag = "1" Then AddToken outText, "STANDARD"
    If chkGreenville.Value And chkGreenville.Tag = "1" Then AddToken outText, "GREENVILLE"
    If chkCustomerPickup.Value And chkCustomerPickup.Tag = "1" Then AddToken outText, "CPU"

    BuildDestinationMode = outText
End Function

Private Function BuildPrintKind() As String
    If optOrders.Value Then
        BuildPrintKind = "ORDERS"
    ElseIf optRemakes.Value Then
        BuildPrintKind = "REMAKES"
    ElseIf optUpdatedOrders.Value Then
        BuildPrintKind = "UPDATED_ORDERS"
    ElseIf optUpdatedRemakes.Value Then
        BuildPrintKind = "UPDATED_REMAKES"
    ElseIf optUpdatedAll.Value Then
        BuildPrintKind = "UPDATED_ALL"
    ElseIf optAllOrders.Value Then
        BuildPrintKind = "ALL"
    End If
End Function

Private Function BuildGlassKeys() As String
    Dim outText As String
    Dim i As Long

    If chkAllGlassTypes.Value Then
        BuildGlassKeys = "ALL"
        Exit Function
    End If

    For i = 0 To lstGlassTypes.ListCount - 1
        If lstGlassTypes.Selected(i) Then
            AddToken outText, CStr(lstGlassTypes.List(i, 1))
        End If
    Next i

    BuildGlassKeys = outText
End Function

Private Function ValidateAndStoreSelections() As Boolean
    SelectedDestinationMode = BuildDestinationMode()
    SelectedPrintKind = BuildPrintKind()
    selectedGlassKeys = BuildGlassKeys()

    If Len(SelectedDestinationMode) = 0 Then
        MsgBox "Please choose at least one destination.", vbExclamation, "Print Delivery List"
        Exit Function
    End If

    If Len(SelectedPrintKind) = 0 Then
        MsgBox "Please choose a print filter.", vbExclamation, "Print Delivery List"
        Exit Function
    End If

    If Len(selectedGlassKeys) = 0 Then
        MsgBox "Please choose at least one glass type, or select All glass types.", vbExclamation, "Print Delivery List"
        Exit Function
    End If

    ValidateAndStoreSelections = True
End Function

Private Sub cmdPreview_Click()
    If Not ValidateAndStoreSelections() Then Exit Sub

    selectedAction = "PREVIEW"
    WasCancelled = False
    Me.Hide
End Sub
Private Sub cmdPrint_Click()
    Dim copiesToPrint As Long

    If Not ValidateAndStoreSelections() Then Exit Sub

    copiesToPrint = PromptForCopyCount()
    If copiesToPrint < 1 Then Exit Sub

    selectedCopies = copiesToPrint
    selectedAction = "PRINT"
    WasCancelled = False
    Me.Hide
End Sub

Private Sub cmdCancel_Click()
    WasCancelled = True
    selectedAction = vbNullString
    Me.Hide
End Sub

Private Sub UserForm_QueryClose(Cancel As Integer, CloseMode As Integer)
    If CloseMode = vbFormControlMenu Then
        WasCancelled = True
        selectedAction = vbNullString
    End If
End Sub
Private Function PromptForCopyCount() As Long
    Dim v As Variant
    Dim n As Long

    v = Application.InputBox( _
            Prompt:="How many copies would you like to print?", _
            Title:="Print Copies", _
            Default:=1, _
            Type:=1)

    If VarType(v) = vbBoolean Then
        PromptForCopyCount = 0
        Exit Function
    End If

    n = CLng(Val(v))
    If n < 1 Then
        MsgBox "Please enter a whole number greater than 0.", vbExclamation, "Print Copies"
        PromptForCopyCount = 0
        Exit Function
    End If

    PromptForCopyCount = n
End Function
