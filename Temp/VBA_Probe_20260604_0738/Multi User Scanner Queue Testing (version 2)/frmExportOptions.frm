Attribute VB_Name = "frmExportOptions"
Attribute VB_Base = "0{03157FE4-6F54-40D6-8CEB-9DB1122B9470}{C23BA3C0-B015-4DB1-A021-5DDEE945CA66}"
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
Public SelectedExportKind As String
Public SelectedDestinationMode As String
Public selectedGlassKeys As String
Public selectedAction As String

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
    SelectedExportKind = vbNullString
    SelectedDestinationMode = vbNullString
    selectedGlassKeys = vbNullString
    selectedAction = vbNullString

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

    cmdCancel.Cancel = True

    cmdExport.backColor = RGB(47, 75, 117)
    cmdExport.foreColor = RGB(255, 255, 255)

    cmdCancel.backColor = RGB(230, 230, 230)
    cmdCancel.foreColor = RGB(0, 0, 0)
End Sub

Private Sub SetDefaults()
    chkAllDestinations.Value = False
    chkIndianTrail.Value = True
    chkGreenville.Value = False
    chkCustomerPickup.Value = False

    chkAllGlassTypes.Value = True
    ClearGlassSelections

    optAllOrders.Value = True

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

    Dim currentExportKind As String
    Dim destinationMode As String
    Dim sections As Collection
    Dim i As Long
    Dim sectionInfo As Variant
    Dim rowIndex As Long

    If mWs Is Nothing Then Exit Sub

    mIsRefreshing = True

    hasStandard = HasPrintableRowsForTemplate(mWs, mFirstDataRow, mLastRealRow, mOrderCol, mItemCol, "STANDARD", "ALL")
    hasGreenville = HasPrintableRowsForTemplate(mWs, mFirstDataRow, mLastRealRow, mOrderCol, mItemCol, "GREENVILLE", "ALL")
    hasCPU = HasPrintableRowsForTemplate(mWs, mFirstDataRow, mLastRealRow, mOrderCol, mItemCol, "CPU", "ALL")

    chkIndianTrail.Visible = True
    chkGreenville.Visible = True
    chkCustomerPickup.Visible = True

    chkIndianTrail.Tag = IIf(hasStandard, "1", "0")
    chkGreenville.Tag = IIf(hasGreenville, "1", "0")
    chkCustomerPickup.Tag = IIf(hasCPU, "1", "0")

    If Not hasStandard Then chkIndianTrail.Value = False
    If Not hasGreenville Then chkGreenville.Value = False
    If Not hasCPU Then chkCustomerPickup.Value = False

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

    hasUpdatedOrders = HasPrintableRowsForTemplate(mWs, mFirstDataRow, mLastRealRow, mOrderCol, mItemCol, destinationMode, "UPDATED_ORDERS")
    hasUpdatedRemakes = HasPrintableRowsForTemplate(mWs, mFirstDataRow, mLastRealRow, mOrderCol, mItemCol, destinationMode, "UPDATED_REMAKES")
    hasUpdatedAll = HasPrintableRowsForTemplate(mWs, mFirstDataRow, mLastRealRow, mOrderCol, mItemCol, destinationMode, "UPDATED_ALL")

    optUpdatedOrders.Visible = True
    optUpdatedRemakes.Visible = True
    optUpdatedAll.Visible = True

    optUpdatedOrders.Enabled = hasUpdatedOrders
    optUpdatedRemakes.Enabled = hasUpdatedRemakes
    optUpdatedAll.Enabled = hasUpdatedAll

    currentExportKind = BuildExportKind()

    If currentExportKind = "UPDATED_ORDERS" And Not hasUpdatedOrders Then optOrders.Value = True
    If currentExportKind = "UPDATED_REMAKES" And Not hasUpdatedRemakes Then optOrders.Value = True
    If currentExportKind = "UPDATED_ALL" And Not hasUpdatedAll Then optOrders.Value = True

    currentExportKind = BuildExportKind()

    Set sections = GetDeliveryListSectionsForPrintKind(mWs, mFirstDataRow, mLastRealRow, mOrderCol, mItemCol, destinationMode, currentExportKind)

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
        chkAllGlassTypes.Value = True
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

Private Function BuildExportKind() As String
    If optOrders.Value Then
        BuildExportKind = "ORDERS"
    ElseIf optRemakes.Value Then
        BuildExportKind = "REMAKES"
    ElseIf optUpdatedOrders.Value Then
        BuildExportKind = "UPDATED_ORDERS"
    ElseIf optUpdatedRemakes.Value Then
        BuildExportKind = "UPDATED_REMAKES"
    ElseIf optUpdatedAll.Value Then
        BuildExportKind = "UPDATED_ALL"
    ElseIf optAllOrders.Value Then
        BuildExportKind = "ALL"
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
    SelectedExportKind = BuildExportKind()
    selectedGlassKeys = BuildGlassKeys()

    If Len(SelectedDestinationMode) = 0 Then
        MsgBox "Please choose at least one destination.", vbExclamation, "Export Delivery List"
        Exit Function
    End If

    If Len(SelectedExportKind) = 0 Then
        MsgBox "Please choose an export filter.", vbExclamation, "Export Delivery List"
        Exit Function
    End If

    If Len(selectedGlassKeys) = 0 Then
        MsgBox "Please choose at least one glass type, or select All glass types.", vbExclamation, "Export Delivery List"
        Exit Function
    End If

    ValidateAndStoreSelections = True
End Function

Private Sub cmdExport_Click()
    If Not ValidateAndStoreSelections() Then Exit Sub

    selectedAction = "EXPORT"
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

