Attribute VB_Name = "frmScannerSettings"
Attribute VB_Base = "0{D452BFCC-DFA2-4C6E-A9A7-777763C796EF}{57F79E6A-914D-45AA-8368-3A0B3F97818D}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = False
Option Explicit

Private Sub UserForm_Initialize()
    Me.Caption = "Scanner Settings"
    LoadStageProfiles
    ReloadDeliveryLists
    LoadCurrentSelections
End Sub
Private Sub ReloadDeliveryLists()
    Dim keepStage As String

    keepStage = Trim$(CStr(cboProcessStage.Value))

    LoadDeliveryLists

    If Len(keepStage) > 0 Then
        cboProcessStage.Value = keepStage
    End If
End Sub

Private Sub RestoreDeliverySelection(ByVal deliveryKey As String)
    Dim i As Long

    If Len(Trim$(deliveryKey)) = 0 Then Exit Sub

    For i = 0 To lstDeliveryLists.ListCount - 1
        If StrComp(lstDeliveryLists.List(i, 1), deliveryKey, vbTextCompare) = 0 Then
            lstDeliveryLists.ListIndex = i
            Exit For
        End If
    Next i
End Sub
Private Sub cmdRefresh_Click()
    Dim currentKey As String

    currentKey = vbNullString
    If lstDeliveryLists.ListIndex >= 0 Then
        currentKey = CStr(lstDeliveryLists.List(lstDeliveryLists.ListIndex, 1))
    End If

    lstDeliveryLists.Clear
    DoEvents
    ReloadDeliveryLists
    RestoreDeliverySelection currentKey

    If lstDeliveryLists.ListCount = 0 Then
        MsgBox "No online delivery lists were found. Make sure the master delivery list is open and then click Refresh again.", vbInformation, "Scanner Settings"
    End If
End Sub
Private Sub LoadDeliveryLists()
    Dim items As Collection
    Dim item As Object
    Dim listDateText As String
    Dim deliveryKey As String
    Dim seenKeys As Object

    Set seenKeys = CreateObject("Scripting.Dictionary")
    seenKeys.CompareMode = vbTextCompare

    lstDeliveryLists.Clear
    lstDeliveryLists.ColumnCount = 4
    lstDeliveryLists.ColumnWidths = "170 pt;120 pt;65 pt;90 pt"

    Set items = PA_ActiveDeliveryListsGetOnline(False)

    For Each item In items
        deliveryKey = Trim$(PA_DictText(item, "deliveryListKey"))

        'Do not show duplicate delivery lists.
        'The ActiveDeliveryListsGetOnline flow can return the same key more than once
        'depending on the flow response/output path, so the form protects itself here.
        If Len(deliveryKey) > 0 Then
            If Not seenKeys.Exists(deliveryKey) Then
                seenKeys.Add deliveryKey, True

                listDateText = vbNullString
                If Len(PA_DictText(item, "listDate")) > 0 Then
                    On Error Resume Next
                    listDateText = Format$(CDate(PA_DictText(item, "listDate")), "m/d/yyyy")
                    On Error GoTo 0
                End If

                lstDeliveryLists.AddItem PA_DictText(item, "displayName")
                lstDeliveryLists.List(lstDeliveryLists.ListCount - 1, 1) = deliveryKey
                lstDeliveryLists.List(lstDeliveryLists.ListCount - 1, 2) = PA_DictText(item, "processorStatus")
                lstDeliveryLists.List(lstDeliveryLists.ListCount - 1, 3) = listDateText
            End If
        End If
    Next item
End Sub
Private Function DeliveryListMatches(ByVal aWs As Worksheet, ByVal rowNum As Long) As Boolean
    Dim statusText As String
    Dim heartbeatVal As Variant

    If Len(Trim$(CStr(aWs.Cells(rowNum, 1).Value))) = 0 Then Exit Function

    statusText = UCase$(Trim$(CStr(aWs.Cells(rowNum, 4).Value)))
    heartbeatVal = aWs.Cells(rowNum, 5).Value

    If statusText <> "ONLINE" And statusText <> "OPEN" And statusText <> "ACTIVE" Then Exit Function
    If Not IsDate(heartbeatVal) Then Exit Function

    'Allow a little cushion for heartbeat timing
    If DateDiff("n", CDate(heartbeatVal), Now) > 5 Then Exit Function

    DeliveryListMatches = True
End Function

Private Sub AddDeliveryListRow(ByVal aWs As Worksheet, ByVal rowNum As Long)
    Dim listDateText As String

    If IsDate(aWs.Cells(rowNum, 3).Value) Then
        listDateText = Format$(CDate(aWs.Cells(rowNum, 3).Value), "m/d/yyyy")
    Else
        listDateText = vbNullString
    End If

    lstDeliveryLists.AddItem CStr(aWs.Cells(rowNum, 2).Value)
    lstDeliveryLists.List(lstDeliveryLists.ListCount - 1, 1) = CStr(aWs.Cells(rowNum, 1).Value)
    lstDeliveryLists.List(lstDeliveryLists.ListCount - 1, 2) = CStr(aWs.Cells(rowNum, 4).Value)
    lstDeliveryLists.List(lstDeliveryLists.ListCount - 1, 3) = listDateText
End Sub
Private Sub LoadStageProfiles()
    With cboProcessStage
        .Clear
        .AddItem "Staging - Airport Rd"
        .AddItem "Outbound - Airport Rd"
        .AddItem "Inbound - Indian Trail"
        .AddItem "Inbound - Greenville"
        .AddItem "Customer Pickup"
    End With
End Sub

Private Sub LoadCurrentSelections()
    Dim currentKey As String
    Dim currentProfile As String
    Dim i As Long

    currentKey = GetSelectedDeliveryKey()
    currentProfile = GetSelectedStageProfile()

    For i = 0 To lstDeliveryLists.ListCount - 1
        If StrComp(lstDeliveryLists.List(i, 1), currentKey, vbTextCompare) = 0 Then
            lstDeliveryLists.ListIndex = i
            Exit For
        End If
    Next i

    For i = 0 To cboProcessStage.ListCount - 1
        If StrComp(cboProcessStage.List(i), currentProfile, vbTextCompare) = 0 Then
            cboProcessStage.ListIndex = i
            Exit For
        End If
    Next i
End Sub
Private Sub cmdApply_Click()
    Dim deliveryKey As String
    Dim deliveryDisplay As String
    Dim stageProfile As String

    If lstDeliveryLists.ListIndex < 0 Then
        MsgBox "Select a delivery list.", vbExclamation, "Scanner Settings"
        Exit Sub
    End If

    stageProfile = Trim$(CStr(cboProcessStage.Value))

    If Len(stageProfile) = 0 Then
        MsgBox "Select a stage.", vbExclamation, "Scanner Settings"
        Exit Sub
    End If

    deliveryKey = CStr(lstDeliveryLists.List(lstDeliveryLists.ListIndex, 1))
    deliveryDisplay = CStr(lstDeliveryLists.List(lstDeliveryLists.ListIndex, 0))

    'Hide this settings form while the intake prepares the old stage,
    'requests a fresh snapshot from the master, and loads the new stage.
    Me.Hide
    DoEvents

    If ApplyScannerSettingsAndRequestFreshSnapshot(deliveryKey, deliveryDisplay, stageProfile) Then
        RefreshScannerPanelOverview
        Unload Me
    Else
        'If the refresh/settings change failed, show settings again
        'so the user can retry or cancel.
        Me.Show vbModeless
    End If
End Sub

Private Sub cmdCancel_Click()
    Unload Me
End Sub

