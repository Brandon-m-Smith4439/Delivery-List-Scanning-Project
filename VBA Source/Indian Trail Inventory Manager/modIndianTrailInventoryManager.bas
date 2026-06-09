Attribute VB_Name = "modIndianTrailInventoryManager"
Option Explicit

'==============================================================================
' Module: modIndianTrailInventoryManager
' Workbook: Indian Trail Inventory Manager.xlsm
'
' Purpose:
'   Builds the Indian Trail Inventory Manager control panel and a separate
'   physical bay map sheet. The panel is button-only. The map is generated
'   directly in this workbook without importing Inventory.xlsx.
'==============================================================================

Private Const ITIM_PANEL_SHEET As String = "Inventory Manager"
Private Const ITIM_MAP_SHEET As String = "Bay Map"
Private Const ITIM_STATUS_CELL As String = "M7"

'========================
' Fonts
'========================
Private Const FONT_BASE As String = "Aptos"
Private Const FONT_ICON As String = "Segoe MDL2 Assets"

'========================
' Utility-panel button palette
'========================
Private Const BTN_PRIMARY_R As Long = 47
Private Const BTN_PRIMARY_G As Long = 75
Private Const BTN_PRIMARY_B As Long = 117

Private Const BTN_TXT_R As Long = 255
Private Const BTN_TXT_G As Long = 255
Private Const BTN_TXT_B As Long = 255

Private Const BTN_GRADIENT_STYLE As Long = 2       'msoGradientDiagonalUp
Private Const BTN_GRADIENT_LIGHTEN As Double = 0.1
Private Const BTN_ACCENT_POS As Double = 0.99
Private Const BTN_MID_POS As Double = 0.7

Private Const BTN_ACCENT_R As Long = 20
Private Const BTN_ACCENT_G As Long = 255
Private Const BTN_ACCENT_B As Long = 15

'========================
' Segoe MDL2 Assets glyph codepoints
'========================
Private Const CP_REFRESH As Long = &HE72C
Private Const CP_SEARCH As Long = &HE721
Private Const CP_TABLE As Long = &HE80A
Private Const CP_CLEAR As Long = &HE74D
Private Const CP_PIN As Long = &HE718
Private Const CP_MOVE As Long = &HE7C2
Private Const CP_FLAG As Long = &HE7C1
Private Const CP_UNFLAG As Long = &HE7BA
Private Const CP_WARNING As Long = &HE814
Private Const CP_MAP As Long = &HE707
Private Const CP_TARGET As Long = &HE81C
Private Const CP_LINK As Long = &HE71B
Private Const CP_REBUILD As Long = &HE777
Private Const CP_HELP As Long = &HE897

Private Type BtnTheme
    Fill As Long
    Font As Long
End Type

Public Sub BuildIndianTrailInventoryManagerPanel()
    Dim mapWs As Worksheet
    Dim thm As BtnTheme
    Dim oldEvents As Boolean
    Dim oldScreen As Boolean
    Dim oldAlerts As Boolean
    Dim stepText As String

    oldEvents = Application.EnableEvents
    oldScreen = Application.ScreenUpdating
    oldAlerts = Application.DisplayAlerts

    On Error GoTo FailBuild

    Application.EnableEvents = False
    Application.ScreenUpdating = False
    Application.DisplayAlerts = False

    stepText = "Create/find map sheet"
    Set mapWs = EnsureWorksheet(ITIM_MAP_SHEET)

    stepText = "Hide old manager panel"
    HideManagerPanel

    stepText = "Load button theme"
    thm = ThemePrimary()

    stepText = "Unprotect sheets"
    On Error Resume Next
    mapWs.Unprotect Password:=""
    On Error GoTo FailBuild

    stepText = "Clear map sheet"
    ClearMapSheet mapWs

    stepText = "Build physical bay map"
    BuildPhysicalBayMap mapWs

    stepText = "Set status"
    ITIM_DataSetStatus "Ready - live Bay Map loaded.", "INFO"

    stepText = "Protect sheets"
    mapWs.Protect Password:="", DrawingObjects:=False, Contents:=True, Scenarios:=True, UserInterfaceOnly:=True
    mapWs.Activate
    mapWs.Range("A1").Select

CleanExit:
    Application.DisplayAlerts = oldAlerts
    Application.EnableEvents = oldEvents
    Application.ScreenUpdating = oldScreen
    Exit Sub

FailBuild:
    Application.DisplayAlerts = oldAlerts
    Application.EnableEvents = oldEvents
    Application.ScreenUpdating = oldScreen

    MsgBox "Indian Trail Inventory Manager build failed." & vbCrLf & vbCrLf & _
           "Step: " & stepText & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbExclamation, "Indian Trail Inventory Manager"
End Sub

Private Function EnsureWorksheet(ByVal sheetName As String) As Worksheet
    On Error Resume Next
    Set EnsureWorksheet = ThisWorkbook.Worksheets(sheetName)
    On Error GoTo 0

    If EnsureWorksheet Is Nothing Then
        If sheetName = ITIM_PANEL_SHEET Then
            On Error Resume Next
            Set EnsureWorksheet = ThisWorkbook.Worksheets("IT Inventory Manager")
            If Not EnsureWorksheet Is Nothing Then EnsureWorksheet.Name = ITIM_PANEL_SHEET
            On Error GoTo 0
        ElseIf sheetName = ITIM_MAP_SHEET Then
            On Error Resume Next
            Set EnsureWorksheet = ThisWorkbook.Worksheets("Indian Trail Bay Map")
            If Not EnsureWorksheet Is Nothing Then EnsureWorksheet.Name = ITIM_MAP_SHEET
            On Error GoTo 0
        End If
    End If

    If EnsureWorksheet Is Nothing Then
        Set EnsureWorksheet = ThisWorkbook.Worksheets.Add(After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
        EnsureWorksheet.Name = sheetName
    End If
End Function

Private Sub HideManagerPanel()
    Dim ws As Worksheet

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(ITIM_PANEL_SHEET)
    If ws Is Nothing Then Set ws = ThisWorkbook.Worksheets("IT Inventory Manager")

    If Not ws Is Nothing Then
        ws.Unprotect Password:=""
        ws.Visible = xlSheetVeryHidden
    End If
    On Error GoTo 0
End Sub

Private Sub ClearPanelSheet(ByVal ws As Worksheet)
    Dim i As Long

    On Error Resume Next

    For i = ws.Shapes.Count To 1 Step -1
        If Left$(ws.Shapes(i).Name, 4) = "itim" Then ws.Shapes(i).Delete
    Next i

    Do While ws.ListObjects.Count > 0
        ws.ListObjects(1).Delete
    Loop

    ws.Cells.UnMerge
    ws.Cells.Clear
    ws.Cells.Locked = True
    On Error GoTo 0
End Sub

Private Sub FormatPanelSheet(ByVal ws As Worksheet)
    With ws
        .Activate
        ActiveWindow.DisplayGridlines = False

        .Cells.Font.Name = FONT_BASE
        .Cells.Font.Size = 13
        .Cells.Interior.Color = RGB(189, 205, 222)

        .Columns("A").ColumnWidth = 37
        .Columns("B:G").ColumnWidth = 14.5
        .Columns("H").ColumnWidth = 2.5
        .Columns("I:N").ColumnWidth = 14.5
        .Columns("O").ColumnWidth = 3

        .Rows("1:2").RowHeight = 18
        .Rows("3:6").RowHeight = 24
        .Rows("7:44").RowHeight = 25

        .Range("B2:N6").Merge
        With .Range("B2")
            .Value = "Indian Trail Inventory Manager"
            .Interior.Color = RGB(47, 75, 117)
            .Font.Color = RGB(255, 255, 255)
            .Font.Bold = True
            .Font.Size = 36
            .HorizontalAlignment = xlCenter
            .VerticalAlignment = xlCenter
            .WrapText = True
        End With

        .Range("B8:N8").Merge
        With .Range("B8")
            .Value = "ACTIONS"
            .Interior.Color = RGB(47, 75, 117)
            .Font.Color = RGB(255, 255, 255)
            .Font.Bold = True
            .Font.Size = 12
            .HorizontalAlignment = xlCenter
            .VerticalAlignment = xlCenter
        End With

        .Range("H9:H42").Interior.Color = RGB(158, 176, 197)
        .Range("B9:G42").Interior.Color = RGB(183, 199, 218)
        .Range("I9:N42").Interior.Color = RGB(183, 199, 218)

        AddPanelSectionHeader ws, "B10:G10", "Inventory / Bay View"
        AddPanelSectionHeader ws, "I10:N10", "Map / Search"
        AddPanelSectionHeader ws, "B22:G22", "Bay Controls"
        AddPanelSectionHeader ws, "I22:N22", "SDI / Manual Controls"
        AddPanelSectionHeader ws, "B34:G34", "SharePoint Links"
        AddPanelSectionHeader ws, "I34:N34", "Maintenance"

        .Range("B7:L7").Merge
        With .Range("B7")
            .Value = "Use the buttons below. Physical bay details live on the Bay Map sheet."
            .Interior.Color = RGB(221, 230, 242)
            .Font.Color = RGB(47, 75, 117)
            .Font.Bold = True
            .HorizontalAlignment = xlCenter
            .VerticalAlignment = xlCenter
        End With

        .Range(ITIM_STATUS_CELL & ":N7").Merge
        With .Range(ITIM_STATUS_CELL)
            .Value = "Ready"
            .Interior.Color = RGB(198, 239, 206)
            .Font.Color = RGB(0, 97, 0)
            .Font.Bold = True
            .HorizontalAlignment = xlCenter
            .VerticalAlignment = xlCenter
        End With

        .Range("B2:N7").BorderAround LineStyle:=xlContinuous, Weight:=xlThin, Color:=RGB(164, 179, 199)
        .Range("B8:N8").BorderAround LineStyle:=xlContinuous, Weight:=xlThin, Color:=RGB(164, 179, 199)
        .Range("B9:G42").BorderAround LineStyle:=xlContinuous, Weight:=xlThin, Color:=RGB(164, 179, 199)
        .Range("I9:N42").BorderAround LineStyle:=xlContinuous, Weight:=xlThin, Color:=RGB(164, 179, 199)
    End With
End Sub

Private Sub AddPanelSectionHeader(ByVal ws As Worksheet, ByVal addressText As String, ByVal captionText As String)
    ws.Range(addressText).Merge
    With ws.Range(Split(addressText, ":")(0))
        .Value = captionText
        .Interior.Color = RGB(31, 78, 121)
        .Font.Color = RGB(255, 255, 255)
        .Font.Bold = True
        .Font.Size = 10
        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
    End With
End Sub

Private Sub BuildPanelButtons(ByVal ws As Worksheet, ByRef thm As BtnTheme)
    'Left column - Inventory / Bay View
    AddSlimGradientButton ws, "B11:G13", "itimRefreshInventory", GlyphFromCP(CP_REFRESH), _
        "REFRESH INVENTORY", "Reload bay assignments", "ITIM_RefreshInventory", thm, RGB(91, 155, 213)

    AddSlimGradientButton ws, "B14:G16", "itimOpenMap", GlyphFromCP(CP_MAP), _
        "OPEN BAY MAP", "View physical bay layout", "ITIM_OpenBayMap", thm, RGB(15, 255, 179)

    AddSlimGradientButton ws, "B17:G19", "itimSyncMap", GlyphFromCP(CP_TABLE), _
        "SYNC MAP STATUS", "Color bays from inventory", "ITIM_SyncMapStatus", thm, RGB(196, 196, 196)

    'Right column - Map / Search
    AddSlimGradientButton ws, "I11:N13", "itimFindOrder", GlyphFromCP(CP_SEARCH), _
        "FIND ORDER / BAY", "Search map and assignments", "ITIM_FindOrderOrBay", thm, RGB(91, 155, 213)

    AddSlimGradientButton ws, "I14:N16", "itimHighlightBay", GlyphFromCP(CP_TARGET), _
        "HIGHLIGHT BAY", "Jump to a bay on map", "ITIM_HighlightBayOnMap", thm, RGB(15, 255, 179)

    AddSlimGradientButton ws, "I17:N19", "itimOpenSelectedBay", GlyphFromCP(CP_PIN), _
        "SHOW SELECTED BAY", "Highlight selected map value", "ITIM_ShowSelectedBayOnMap", thm, RGB(196, 196, 196)

    'Left column - Bay Controls
    AddSlimGradientButton ws, "B23:G25", "itimClearBay", GlyphFromCP(CP_CLEAR), _
        "CLEAR SELECTED BAY", "Confirm bay is empty", "ITIM_ClearSelectedBay", thm, RGB(255, 181, 54)

    AddSlimGradientButton ws, "B26:G28", "itimManualAssign", GlyphFromCP(CP_PIN), _
        "MANUAL ASSIGN", "Assign order to bay", "ITIM_ManualAssignSelectedOrder", thm, RGB(91, 155, 213)

    AddSlimGradientButton ws, "B29:G31", "itimMoveBay", GlyphFromCP(CP_MOVE), _
        "MOVE BAY", "Move order to another bay", "ITIM_MoveSelectedOrderToBay", thm, RGB(15, 255, 179)

    'Right column - SDI / Manual Controls
    AddSlimGradientButton ws, "I23:N25", "itimMarkSDI", GlyphFromCP(CP_FLAG), _
        "MARK SDI", "Same-day install flag", "ITIM_MarkSelectedOrderSDI", thm, RGB(255, 181, 54)

    AddSlimGradientButton ws, "I26:N28", "itimRemoveSDI", GlyphFromCP(CP_UNFLAG), _
        "REMOVE SDI", "Restore normal bay flow", "ITIM_RemoveSelectedOrderSDI", thm, RGB(196, 196, 196)

    AddSlimGradientButton ws, "I29:N31", "itimManualException", GlyphFromCP(CP_WARNING), _
        "MANUAL EXCEPTION", "Set aside for review", "ITIM_MarkSelectedOrderManualException", thm, RGB(192, 0, 0)

    'Bottom links / maintenance
    AddSlimGradientButton ws, "B35:G37", "itimOpenAssignments", GlyphFromCP(CP_LINK), _
        "OPEN ASSIGNMENTS", "SharePoint assignment list", "ITIM_OpenAssignmentsList", thm, RGB(91, 155, 213)

    AddSlimGradientButton ws, "B38:G40", "itimOpenBays", GlyphFromCP(CP_TABLE), _
        "OPEN BAY LIST", "SharePoint bay definitions", "ITIM_OpenBayDefinitionsList", thm, RGB(15, 255, 179)

    AddSlimGradientButton ws, "I35:N37", "itimRebuildPanel", GlyphFromCP(CP_REBUILD), _
        "REBUILD PANEL", "Refresh layout/buttons", "ITIM_RebuildPanel", thm, RGB(91, 155, 213)

    AddSlimGradientButton ws, "I38:N40", "itimHelp", GlyphFromCP(CP_HELP), _
        "HELP / STEPS", "How to use this sheet", "ITIM_ShowHelp", thm, RGB(255, 181, 54)
End Sub

'==============================================================================
' Physical bay map
'==============================================================================

Private Sub ClearMapSheet(ByVal ws As Worksheet)
    Dim i As Long

    On Error Resume Next

    For i = ws.Shapes.Count To 1 Step -1
        If Left$(ws.Shapes(i).Name, 4) = "itim" Then ws.Shapes(i).Delete
    Next i

    Do While ws.ListObjects.Count > 0
        ws.ListObjects(1).Delete
    Loop

    ws.Cells.UnMerge
    ws.Cells.Clear
    ws.Cells.Locked = True
    On Error GoTo 0
End Sub

Private Sub BuildPhysicalBayMap(ByVal ws As Worksheet)
    Dim mapStep As String

    On Error GoTo FailMap

    mapStep = "Format map sheet"

    With ws
        .Activate
        ActiveWindow.DisplayGridlines = False

        .Cells.Font.Name = FONT_BASE
        .Cells.Font.Size = 9
        .Cells.Interior.Color = RGB(226, 235, 245)

        .Columns("A").ColumnWidth = 20
        .Columns("B").ColumnWidth = 12
        .Columns("C").ColumnWidth = 6
        .Columns("D").ColumnWidth = 20
        .Columns("E").ColumnWidth = 12
        .Columns("F").ColumnWidth = 6
        .Columns("G").ColumnWidth = 20
        .Columns("H").ColumnWidth = 12
        .Columns("I").ColumnWidth = 6
        .Columns("J").ColumnWidth = 20
        .Columns("K").ColumnWidth = 12
        .Columns("L").ColumnWidth = 6
        .Columns("M").ColumnWidth = 20
        .Columns("N").ColumnWidth = 12
        .Columns("O").ColumnWidth = 6
        .Columns("P").ColumnWidth = 6
        .Columns("Q").ColumnWidth = 20
        .Columns("R").ColumnWidth = 12
        .Columns("S").ColumnWidth = 6
        .Columns("T").ColumnWidth = 20
        .Columns("U").ColumnWidth = 12
        .Columns("V").ColumnWidth = 6
        .Columns("W").ColumnWidth = 12
        .Columns("X").ColumnWidth = 12

        .Rows("1:360").RowHeight = 16

        .Range("A1:X2").Merge
        With .Range("A1")
            .Value = "Indian Trail Live Bay View"
            .Interior.Color = RGB(47, 75, 117)
            .Font.Color = RGB(255, 255, 255)
            .Font.Bold = True
            .Font.Size = 18
            .HorizontalAlignment = xlCenter
            .VerticalAlignment = xlCenter
        End With

        .Range("A3:X4").Merge
        With .Range("A3")
            .Value = "Live Indian Trail bay view: outbound scans preassign bays, receiving scans mark orders occupied, and SDI/manual actions keep exceptions visible."
            .Interior.Color = RGB(221, 230, 242)
            .Font.Color = RGB(47, 75, 117)
            .Font.Bold = True
            .Font.Size = 12
            .HorizontalAlignment = xlCenter
            .VerticalAlignment = xlCenter
        End With
        
        .Range("A5:X6").Interior.Color = RGB(183, 199, 218)
        .Range("A7:X7").Interior.Color = RGB(226, 235, 245)
        .Rows("5:6").RowHeight = 18
        .Rows("7").RowHeight = 16
        .Rows("18").RowHeight = 16
        
    End With

    mapStep = "Add map quick buttons"
    BuildMapQuickButtons ws, ThemePrimary()

    mapStep = "Add live status frame"
    BuildMapLiveStatusFrame ws

    mapStep = "Add named manual bays"
    AddNamedBaySection ws, "G8", "H10", "LR", "LR BAYS", 30, RGB(31, 78, 121), RGB(221, 230, 242)
    AddNamedBaySection ws, "J8", "K10", "RR", "RR BAYS", 24, RGB(31, 78, 121), RGB(221, 230, 242)

    mapStep = "Add CRL Laurence bays"
    AddGroupedBaySection ws, "G45", "H47", "CRL", "CRL LAURENCE BAYS", 42, 2, _
                    RGB(143, 143, 17), RGB(255, 242, 204)

    mapStep = "Add framed mirror bays 1-26 under Bay 16"
AddGroupedBaySectionRange ws, "J45", "K47", "FM", "FRAMED MIRROR BAYS 1-25", _
                          1, 25, 6, _
                          RGB(0, 128, 128), RGB(218, 238, 243)

mapStep = "Add framed mirror bays 27-36 parallel with Bay 14"
AddGroupedBaySectionRange ws, "M157", "N159", "FM", "FRAMED MIRROR BAYS 26-36", _
                          26, 36, 6, _
                          RGB(0, 128, 128), RGB(218, 238, 243)

    mapStep = "Add left physical racks"
AddBayStackColumn ws, "A", "B", 8, _
    Array(1, 2, 3, 4, 5, 6), _
    Array(22, 22, 23, 23, 22, 22), _
    "Coral"

mapStep = "Add middle-left racks"
AddBayStackColumn ws, "D", "E", 8, _
    Array(7, 8, 9, 10, 11), _
    Array(33, 23, 22, 22, 23), _
    "Coral"

mapStep = "Add middle-right racks"
AddBayStackColumn ws, "M", "N", 8, _
    Array(12, 13, 14, 15, 16), _
    Array(33, 23, 23, 22, 22), _
    "Showers"

mapStep = "Add right mirror racks"
AddBayStackColumn ws, "Q", "R", 27, _
    Array(17, 18, 19, 20, 21), _
    Array(22, 22, 22, 22, 22), _
    "Mirror Rack"

    mapStep = "Add BFS mirror bays"
    AddBfsMirrorBaySection ws, "T27", "U29", 4, 22, 88

    mapStep = "Finalize map formatting"
    With ws.Range("A1:AD360")
        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
    End With

    ws.Range("A1:AD360").Locked = True
    Exit Sub

FailMap:
    Err.Raise Err.Number, , "BuildPhysicalBayMap failed at: " & mapStep & vbCrLf & Err.Description
End Sub
Private Sub AddGroupedBaySectionRange(ByVal ws As Worksheet, _
                                      ByVal headerCellAddress As String, _
                                      ByVal firstSlotAddress As String, _
                                      ByVal keyPrefix As String, _
                                      ByVal titleText As String, _
                                      ByVal firstBayNumber As Long, _
                                      ByVal lastBayNumber As Long, _
                                      ByVal slotsPerBay As Long, _
                                      ByVal headerColor As Long, _
                                      ByVal subFillColor As Long)
    Dim headerCell As Range
    Dim firstSlot As Range
    Dim bayIndex As Long
    Dim slotIndex As Long
    Dim rowOffset As Long
    Dim bayHeader As Range
    Dim slotCell As Range

    Set headerCell = ws.Range(headerCellAddress)
    Set firstSlot = ws.Range(firstSlotAddress)

    With headerCell.Resize(1, 2)
        .Merge
        .Value = titleText
        .Interior.Color = headerColor
        .Font.Color = RGB(255, 255, 255)
        .Font.Bold = True
        .Font.Size = 10
        .Borders.LineStyle = xlContinuous
        .Borders.Color = RGB(255, 255, 255)
    End With

    With headerCell.Offset(1, 0).Resize(1, 2)
        .Merge
        .Value = "Framed Mirrors"
        .Interior.Color = subFillColor
        .Font.Color = headerColor
        .Font.Bold = True
        .Font.Size = 9
        .Borders.LineStyle = xlContinuous
        .Borders.Color = RGB(164, 179, 199)
    End With

    rowOffset = 0

    For bayIndex = firstBayNumber To lastBayNumber
        Set bayHeader = firstSlot.Offset(rowOffset, -1)

        With bayHeader.Resize(1, 2)
            .Merge
            .Value = keyPrefix & " Bay " & bayIndex
            .Interior.Color = headerColor
            .Font.Color = RGB(255, 255, 255)
            .Font.Bold = True
            .Font.Size = 9
            .Borders.LineStyle = xlContinuous
            .Borders.Color = RGB(255, 255, 255)
        End With

        For slotIndex = 1 To slotsPerBay
            Set slotCell = firstSlot.Offset(rowOffset + slotIndex, 0)

            With slotCell.Offset(0, -1)
                .Value = vbNullString
                .Interior.Color = RGB(242, 246, 250)
                .Borders.LineStyle = xlContinuous
                .Borders.Color = RGB(210, 218, 229)
            End With

            With slotCell
                .Value = keyPrefix & bayIndex & "--" & slotIndex
                .Interior.Color = RGB(255, 255, 255)
                .Font.Color = headerColor
                .Font.Bold = True
                .Borders.LineStyle = xlContinuous
                .Borders.Color = RGB(164, 179, 199)
            End With
        Next slotIndex

        'Bay header + slot rows + one blank separator row.
        rowOffset = rowOffset + slotsPerBay + 2
    Next bayIndex
End Sub
Private Sub AddBayStackColumn(ByVal ws As Worksheet, _
                              ByVal headerColumnLetter As String, _
                              ByVal slotColumnLetter As String, _
                              ByVal firstHeaderRow As Long, _
                              ByVal bayNumbers As Variant, _
                              ByVal slotCounts As Variant, _
                              ByVal categoryText As String)
    Dim i As Long
    Dim currentHeaderRow As Long
    Dim bayNumber As Long
    Dim slotCount As Long
    Dim headerAddress As String
    Dim firstSlotAddress As String

    currentHeaderRow = firstHeaderRow

    For i = LBound(bayNumbers) To UBound(bayNumbers)
        bayNumber = CLng(bayNumbers(i))
        slotCount = CLng(slotCounts(i))

        headerAddress = headerColumnLetter & CStr(currentHeaderRow)
        firstSlotAddress = slotColumnLetter & CStr(currentHeaderRow + 2)

        AddBayStack ws, headerAddress, firstSlotAddress, bayNumber, slotCount, categoryText

        'Header row + subheader row + slot rows + one blank separator row.
        currentHeaderRow = currentHeaderRow + slotCount + 3
    Next i
End Sub
Private Sub AddNamedBaySection(ByVal ws As Worksheet, _
                               ByVal headerCellAddress As String, _
                               ByVal firstSlotAddress As String, _
                               ByVal keyPrefix As String, _
                               ByVal titleText As String, _
                               ByVal slotCount As Long, _
                               ByVal headerColor As Long, _
                               ByVal subFillColor As Long)
    Dim headerCell As Range
    Dim firstSlot As Range
    Dim r As Long
    Dim slotCell As Range

    Set headerCell = ws.Range(headerCellAddress)
    Set firstSlot = ws.Range(firstSlotAddress)

    With headerCell.Resize(1, 2)
        .Merge
        .Value = titleText
        .Interior.Color = headerColor
        .Font.Color = RGB(255, 255, 255)
        .Font.Bold = True
        .Font.Size = 10
        .Borders.LineStyle = xlContinuous
        .Borders.Color = RGB(255, 255, 255)
    End With

    With headerCell.Offset(1, 0).Resize(1, 2)
        .Merge
        .Value = "Manual entry"
        .Interior.Color = subFillColor
        .Font.Color = headerColor
        .Font.Bold = True
        .Font.Size = 9
        .Borders.LineStyle = xlContinuous
        .Borders.Color = RGB(164, 179, 199)
    End With

    For r = 1 To slotCount
        Set slotCell = firstSlot.Offset(r - 1, 0)

        With slotCell.Offset(0, -1)
            .Value = vbNullString
            .Interior.Color = RGB(242, 246, 250)
            .Borders.LineStyle = xlContinuous
            .Borders.Color = RGB(210, 218, 229)
        End With

        With slotCell
            .Value = keyPrefix & "--" & CStr(r)
            .Interior.Color = RGB(255, 255, 255)
            .Font.Color = headerColor
            .Font.Bold = True
            .Borders.LineStyle = xlContinuous
            .Borders.Color = RGB(164, 179, 199)
        End With
    Next r
End Sub
Private Sub AddGroupedBaySection(ByVal ws As Worksheet, _
                                 ByVal headerCellAddress As String, _
                                 ByVal firstSlotAddress As String, _
                                 ByVal keyPrefix As String, _
                                 ByVal titleText As String, _
                                 ByVal bayCount As Long, _
                                 ByVal slotsPerBay As Long, _
                                 ByVal headerColor As Long, _
                                 ByVal subFillColor As Long)
    Dim headerCell As Range
    Dim firstSlot As Range
    Dim bayIndex As Long
    Dim slotIndex As Long
    Dim rowOffset As Long
    Dim bayHeader As Range
    Dim slotCell As Range

    Set headerCell = ws.Range(headerCellAddress)
    Set firstSlot = ws.Range(firstSlotAddress)

    With headerCell.Resize(1, 2)
        .Merge
        .Value = titleText
        .Interior.Color = headerColor
        .Font.Color = RGB(255, 255, 255)
        .Font.Bold = True
        .Font.Size = 10
        .Borders.LineStyle = xlContinuous
        .Borders.Color = RGB(255, 255, 255)
    End With

    With headerCell.Offset(1, 0).Resize(1, 2)
        .Merge
        .Value = "CRL Manual Entry"
        .Interior.Color = subFillColor
        .Font.Color = headerColor
        .Font.Bold = True
        .Font.Size = 9
        .Borders.LineStyle = xlContinuous
        .Borders.Color = RGB(164, 179, 199)
    End With

    rowOffset = 0

    For bayIndex = 1 To bayCount
        Set bayHeader = firstSlot.Offset(rowOffset, -1)

        With bayHeader.Resize(1, 2)
            .Merge
            .Value = keyPrefix & " Bay " & bayIndex
            .Interior.Color = headerColor
            .Font.Color = RGB(255, 255, 255)
            .Font.Bold = True
            .Font.Size = 10
            .Borders.LineStyle = xlContinuous
            .Borders.Color = RGB(255, 255, 255)
        End With

        For slotIndex = 1 To slotsPerBay
            Set slotCell = firstSlot.Offset(rowOffset + slotIndex, 0)

            With slotCell.Offset(0, -1)
                .Value = vbNullString
                .Interior.Color = RGB(242, 246, 250)
                .Borders.LineStyle = xlContinuous
                .Borders.Color = RGB(210, 218, 229)
            End With

            With slotCell
                .Value = keyPrefix & bayIndex & "--" & slotIndex
                .Interior.Color = RGB(255, 255, 255)
                .Font.Color = headerColor
                .Font.Bold = True
                .Borders.LineStyle = xlContinuous
                .Borders.Color = RGB(164, 179, 199)
            End With
        Next slotIndex

        rowOffset = rowOffset + slotsPerBay + 2
    Next bayIndex
End Sub
Private Sub AddBfsMirrorBaySection(ByVal ws As Worksheet, _
                                   ByVal headerCellAddress As String, _
                                   ByVal firstSlotAddress As String, _
                                   ByVal bayCount As Long, _
                                   ByVal slotsPerBay As Long, _
                                   ByVal topMirrorNumber As Long)
    Dim headerCell As Range
    Dim firstSlot As Range
    Dim bayIndex As Long
    Dim slotIndex As Long
    Dim rowOffset As Long
    Dim mirrorNumber As Long
    Dim bayHeader As Range
    Dim slotCell As Range

    Const BFS_HEADER_COLOR As Long = 10498160   'RGB(112, 48, 160)
    Const BFS_SUBFILL_COLOR As Long = 16111850  'RGB(234, 222, 245)

    Set headerCell = ws.Range(headerCellAddress)
    Set firstSlot = ws.Range(firstSlotAddress)

    With headerCell.Resize(1, 2)
        .Merge
        .Value = "BFS MIRROR BAYS"
        .Interior.Color = RGB(112, 48, 160)
        .Font.Color = RGB(255, 255, 255)
        .Font.Bold = True
        .Borders.LineStyle = xlContinuous
        .Borders.Color = RGB(255, 255, 255)
    End With

    With headerCell.Offset(1, 0).Resize(1, 2)
        .Merge
        .Value = bayCount & " bays / " & slotsPerBay & " mirror slots each"
        .Interior.Color = RGB(234, 222, 245)
        .Font.Color = RGB(112, 48, 160)
        .Font.Bold = True
        .Font.Size = 10
        .Borders.LineStyle = xlContinuous
        .Borders.Color = RGB(164, 179, 199)
    End With

    rowOffset = 0
    mirrorNumber = topMirrorNumber

    For bayIndex = 1 To bayCount
        Set bayHeader = firstSlot.Offset(rowOffset, -1)

        With bayHeader.Resize(1, 2)
            .Merge
            .Value = "BFS MIR Bay " & bayIndex
            .Interior.Color = RGB(112, 48, 160)
            .Font.Color = RGB(255, 255, 255)
            .Font.Bold = True
            .Font.Size = 9
            .Borders.LineStyle = xlContinuous
            .Borders.Color = RGB(255, 255, 255)
        End With

        For slotIndex = 1 To slotsPerBay
            If mirrorNumber < 1 Then Exit For

            Set slotCell = firstSlot.Offset(rowOffset + slotIndex, 0)

            With slotCell.Offset(0, -1)
                .Value = vbNullString
                .Interior.Color = RGB(242, 246, 250)
                .Borders.LineStyle = xlContinuous
                .Borders.Color = RGB(210, 218, 229)
            End With

            With slotCell
                .Value = "MIR " & mirrorNumber
                .Interior.Color = RGB(255, 255, 255)
                .Font.Color = RGB(112, 48, 160)
                .Font.Bold = True
                .WrapText = False
                .Borders.LineStyle = xlContinuous
                .Borders.Color = RGB(164, 179, 199)
            End With

            mirrorNumber = mirrorNumber - 1
        Next slotIndex

        rowOffset = rowOffset + slotsPerBay + 2
    Next bayIndex
End Sub
Private Function RackHeaderColor(ByVal categoryText As String) As Long
    Select Case True
        'Mirror racks should be purple.
        Case InStr(1, categoryText, "Mirror", vbTextCompare) > 0
            RackHeaderColor = RGB(112, 48, 160)

        'Bays 1-11 should be tan.
        Case InStr(1, categoryText, "Coral", vbTextCompare) > 0 Or _
             InStr(1, categoryText, "Coral", vbTextCompare) > 0
            RackHeaderColor = RGB(156, 101, 0)

        'Bays 12-16 stay green.
        Case InStr(1, categoryText, "Showers", vbTextCompare) > 0
            RackHeaderColor = RGB(0, 97, 0)

        Case InStr(1, categoryText, "Manual", vbTextCompare) > 0
            RackHeaderColor = RGB(192, 0, 0)

        Case Else
            RackHeaderColor = RGB(47, 75, 117)
    End Select
End Function
Private Function RackSubFillColor(ByVal categoryText As String) As Long
    Select Case True
        'Mirror racks should be purple.
        Case InStr(1, categoryText, "Mirror", vbTextCompare) > 0
            RackSubFillColor = RGB(234, 222, 245)

        'Bays 1-11 should be tan.
        Case InStr(1, categoryText, "Coral", vbTextCompare) > 0 Or _
             InStr(1, categoryText, "Coral", vbTextCompare) > 0
            RackSubFillColor = RGB(255, 242, 204)

        'Bays 12-16 stay green.
        Case InStr(1, categoryText, "Showers", vbTextCompare) > 0
            RackSubFillColor = RGB(226, 239, 218)

        Case InStr(1, categoryText, "Manual", vbTextCompare) > 0
            RackSubFillColor = RGB(255, 199, 206)

        Case Else
            RackSubFillColor = RGB(221, 230, 242)
    End Select
End Function

Private Sub AddMapLabel(ByVal ws As Worksheet, ByVal topLeftAddress As String, ByVal labelText As String)
    With ws.Range(topLeftAddress).Resize(1, 2)
        .Merge
        .Value = labelText
        .Interior.Color = RGB(255, 242, 204)
        .Font.Color = RGB(156, 101, 0)
        .Font.Bold = True
        .Borders.LineStyle = xlContinuous
        .Borders.Color = RGB(156, 101, 0)
    End With
End Sub

Private Sub AddBayStack(ByVal ws As Worksheet, _
                        ByVal headerCellAddress As String, _
                        ByVal firstSlotAddress As String, _
                        ByVal bayNumber As Long, _
                        ByVal slotCount As Long, _
                        ByVal categoryText As String)
    Dim headerCell As Range
    Dim firstSlot As Range
    Dim r As Long
    Dim slotCell As Range
    Dim headerColor As Long
    Dim subFillColor As Long

    Set headerCell = ws.Range(headerCellAddress)
    Set firstSlot = ws.Range(firstSlotAddress)
    headerColor = RackHeaderColor(categoryText)
    subFillColor = RackSubFillColor(categoryText)

    With headerCell.Resize(1, 2)
        .Merge
        .Value = "Bay " & bayNumber
        .Interior.Color = headerColor
        .Font.Color = RGB(255, 255, 255)
        .Font.Bold = True
        .Font.Size = 9
        .Borders.LineStyle = xlContinuous
        .Borders.Color = RGB(255, 255, 255)
    End With

    With headerCell.Offset(1, 0).Resize(1, 2)
        .Merge
        .Value = categoryText
        .Interior.Color = subFillColor
        .Font.Color = headerColor
        .Font.Bold = True
        .Font.Size = 7
        .Borders.LineStyle = xlContinuous
        .Borders.Color = RGB(164, 179, 199)
    End With

    For r = 1 To slotCount
        Set slotCell = firstSlot.Offset(r - 1, 0)

        With slotCell.Offset(0, -1)
            .Value = vbNullString
            .Interior.Color = RGB(242, 246, 250)
            .Borders.LineStyle = xlContinuous
            .Borders.Color = RGB(210, 218, 229)
        End With

        With slotCell
            .Value = CStr(bayNumber) & "--" & CStr(r)
            .Interior.Color = RGB(255, 255, 255)
            .Font.Color = headerColor
            .Font.Bold = True
            .Borders.LineStyle = xlContinuous
            .Borders.Color = RGB(164, 179, 199)
        End With
    Next r
End Sub

Private Sub AddMirrorRack(ByVal ws As Worksheet, _
                          ByVal headerCellAddress As String, _
                          ByVal firstSlotAddress As String, _
                          ByVal topMirrorNumber As Long, _
                          ByVal bottomMirrorNumber As Long)
    Dim headerCell As Range
    Dim firstSlot As Range
    Dim n As Long
    Dim rowOffset As Long
    Dim noteCell As Range
    Dim labelCell As Range

    Set headerCell = ws.Range(headerCellAddress)
    Set firstSlot = ws.Range(firstSlotAddress)

    With headerCell.Resize(1, 2)
        .Merge
        .Value = "BFS MIRROR BAYS"
        .Interior.Color = RGB(156, 101, 0)
        .Font.Color = RGB(255, 255, 255)
        .Font.Bold = True
        .Borders.LineStyle = xlContinuous
        .Borders.Color = RGB(255, 255, 255)
    End With

    With headerCell.Offset(1, 0).Resize(1, 2)
        .Merge
        .Value = "BFS MIR 88-1"
        .Interior.Color = RGB(255, 242, 204)
        .Font.Color = RGB(156, 101, 0)
        .Font.Bold = True
        .Font.Size = 7
        .Borders.LineStyle = xlContinuous
        .Borders.Color = RGB(164, 179, 199)
    End With

    rowOffset = 0
    For n = topMirrorNumber To bottomMirrorNumber Step -1
        Set noteCell = firstSlot.Offset(rowOffset, -1)
        Set labelCell = firstSlot.Offset(rowOffset, 0)

        With noteCell
            .Value = vbNullString
            .Interior.Color = RGB(242, 246, 250)
            .Borders.LineStyle = xlContinuous
            .Borders.Color = RGB(210, 218, 229)
        End With

        With labelCell
            .Value = "BFS MIR " & n
            .Interior.Color = RGB(255, 255, 255)
            .Font.Color = RGB(156, 101, 0)
            .Font.Bold = True
            .Borders.LineStyle = xlContinuous
            .Borders.Color = RGB(164, 179, 199)
        End With

        rowOffset = rowOffset + 1
    Next n
End Sub

Private Sub AddSmallTwoSlotRack(ByVal ws As Worksheet, _
                                ByVal firstHeaderAddress As String, _
                                ByVal firstBayNumber As Long, _
                                ByVal lastBayNumber As Long)
    Dim firstCell As Range
    Dim b As Long
    Dim rowNum As Long

    Set firstCell = ws.Range(firstHeaderAddress)
    rowNum = 0

    With firstCell.Offset(-2, 0).Resize(1, 2)
        .Merge
        .Value = "TWO-SLOT / MANUAL BAYS"
        .Interior.Color = RGB(192, 0, 0)
        .Font.Color = RGB(255, 255, 255)
        .Font.Bold = True
        .Font.Size = 8
        .Borders.LineStyle = xlContinuous
    End With

    For b = firstBayNumber To lastBayNumber
        With firstCell.Offset(rowNum, 0)
            .Value = "Bay " & b
            .Interior.Color = RGB(192, 0, 0)
            .Font.Color = RGB(255, 255, 255)
            .Font.Bold = True
            .Borders.LineStyle = xlContinuous
        End With
        With firstCell.Offset(rowNum, 1)
            .Value = CStr(b) & "--1"
            .Interior.Color = RGB(255, 255, 255)
            .Font.Color = RGB(192, 0, 0)
            .Font.Bold = True
            .Borders.LineStyle = xlContinuous
        End With
        With firstCell.Offset(rowNum + 1, 0)
            .Value = vbNullString
            .Interior.Color = RGB(242, 246, 250)
            .Borders.LineStyle = xlContinuous
        End With
        With firstCell.Offset(rowNum + 1, 1)
            .Value = CStr(b) & "--2"
            .Interior.Color = RGB(255, 255, 255)
            .Font.Color = RGB(192, 0, 0)
            .Font.Bold = True
            .Borders.LineStyle = xlContinuous
        End With
        rowNum = rowNum + 3
    Next b
End Sub

'==============================================================================
' Button actions
'==============================================================================

Public Sub ITIM_RefreshInventory()
    ITIM_DataRefreshAndSync
End Sub

Public Sub ITIM_OpenBayMap()
    Dim ws As Worksheet
    Set ws = EnsureWorksheet(ITIM_MAP_SHEET)
    ws.Activate
    ws.Range("A1").Select
    ITIM_SetStatus "Opened physical bay map.", "INFO", False
End Sub

Public Sub ITIM_SyncMapStatus()
    ITIM_DataSyncMapStatus
End Sub

Public Sub ITIM_FindOrderOrBay()
    ITIM_ShowSearchForm
End Sub

Public Sub ITIM_HighlightBayOnMap()
    Dim bayText As String

    bayText = Trim$(InputBox("Enter bay to highlight, like 17--8, or a BFS mirror number like MIR 82.", "Highlight Bay"))
    If Len(bayText) = 0 Then Exit Sub

    HighlightBayOnMap bayText
End Sub

Public Sub ITIM_ShowSelectedBayOnMap()
    Dim bayText As String

    bayText = Trim$(CStr(ActiveCell.Value))

    If Len(bayText) = 0 Then
        bayText = Trim$(InputBox("Enter a bay key or MIR number to highlight, like 17--8 or MIR 82.", "Show Selected Bay"))
    End If

    If Len(bayText) = 0 Then Exit Sub

    HighlightBayOnMap bayText
End Sub

Private Sub HighlightBayOnMap(ByVal bayText As String)
    Dim ws As Worksheet
    Dim foundCell As Range
    Dim box As Shape

    Set ws = EnsureWorksheet(ITIM_MAP_SHEET)
    ws.Unprotect Password:=""

    ClearMapHighlights ws

    On Error Resume Next
    Set foundCell = ws.Range("A1:AD360").Find(What:=bayText, LookIn:=xlValues, LookAt:=xlWhole, MatchCase:=False)
    If foundCell Is Nothing Then
        Set foundCell = ws.Range("A1:AD360").Find(What:=bayText, LookIn:=xlValues, LookAt:=xlPart, MatchCase:=False)
    End If
    On Error GoTo 0

    If foundCell Is Nothing Then
        ws.Protect Password:="", DrawingObjects:=False, Contents:=True, Scenarios:=True, UserInterfaceOnly:=True
        ITIM_SetStatus "Bay not found on map: " & bayText, "WARN", False
        MsgBox "Bay " & bayText & " was not found on the physical map.", vbExclamation, "Highlight Bay"
        Exit Sub
    End If

    Set box = ws.Shapes.AddShape(msoShapeRoundedRectangle, foundCell.Left - 2, foundCell.Top - 2, foundCell.Width + 4, foundCell.Height + 4)

    With box
        .Name = "itimMapHighlight"
        .Fill.Visible = msoFalse
        .Line.Visible = msoTrue
        .Line.ForeColor.RGB = RGB(255, 192, 0)
        .Line.Weight = 3
        .Placement = xlMoveAndSize
        .ZOrder msoBringToFront
    End With

    ws.Activate
    foundCell.Select
    ws.Protect Password:="", DrawingObjects:=False, Contents:=True, Scenarios:=True, UserInterfaceOnly:=True
    ITIM_SetStatus "Highlighted bay " & bayText & ".", "INFO", False
End Sub

Private Sub ClearMapHighlights(ByVal ws As Worksheet)
    On Error Resume Next
    ws.Shapes("itimMapHighlight").Delete
    On Error GoTo 0
End Sub

Public Sub ITIM_ClearSelectedBay()
    ITIM_ShowManageBayForm "CLEAR"
End Sub

Public Sub ITIM_ManualAssignSelectedOrder()
    ITIM_ShowManualEntryForm
End Sub

Public Sub ITIM_MoveSelectedOrderToBay()
    ITIM_ShowManageBayForm "MOVE"
End Sub

Public Sub ITIM_MarkSelectedOrderSDI()
    ITIM_ShowSdiForm "MARK"
End Sub

Public Sub ITIM_RemoveSelectedOrderSDI()
    ITIM_ShowSdiForm "REMOVE"
End Sub

Public Sub ITIM_MarkSelectedOrderManualException()
    ITIM_ShowManageBayForm "EXCEPTION"
End Sub

Public Sub ITIM_OpenAssignmentsList()
    ITIM_DataOpenAssignmentsList
End Sub

Public Sub ITIM_OpenBayDefinitionsList()
    ITIM_DataOpenBaysList
End Sub

Public Sub ITIM_ShowHelp()
    MsgBox "Indian Trail Inventory Manager" & vbCrLf & vbCrLf & _
           "1. Refresh reloads bay definitions and assignments from the local SharePoint CSV exports, then colors the map." & vbCrLf & _
           "2. Search finds an order, bay, or mirror number and highlights it on the map." & vbCrLf & _
           "3. Bay Actions clears, moves, or flags selected orders for manual review." & vbCrLf & _
           "4. Manual Entry creates or updates a manual bay assignment." & vbCrLf & _
           "5. SDI marks or clears same-day install exceptions." & vbCrLf & vbCrLf & _
           "SharePoint write-back uses the Indian Trail bay admin Power Automate flow when its URL is configured.", _
           vbInformation, "Help / Steps"
End Sub

Public Sub ITIM_RebuildPanel()
    BuildIndianTrailInventoryManagerPanel
End Sub

Private Sub ITIM_SetStatus(ByVal statusText As String, Optional ByVal statusKind As String = "INFO", Optional ByVal protectWhenDone As Boolean = True)
    ITIM_DataSetStatus statusText, statusKind
End Sub

'==============================================================================
' Master-style button builder
'==============================================================================

Private Function GlyphFromCP(ByVal cp As Long) As String
    GlyphFromCP = ChrW$(cp)
End Function

Private Function Rgb3(ByVal r As Long, ByVal g As Long, ByVal b As Long) As Long
    Rgb3 = RGB(r, g, b)
End Function

Private Function AccentColor() As Long
    AccentColor = RGB(BTN_ACCENT_R, BTN_ACCENT_G, BTN_ACCENT_B)
End Function

Private Function ThemePrimary() As BtnTheme
    Dim t As BtnTheme
    t.Fill = Rgb3(BTN_PRIMARY_R, BTN_PRIMARY_G, BTN_PRIMARY_B)
    t.Font = Rgb3(BTN_TXT_R, BTN_TXT_G, BTN_TXT_B)
    ThemePrimary = t
End Function

Private Function FitIn(ByVal slot As Double, ByVal Target As Double, ByVal minV As Double) As Double
    Dim v As Double
    v = Target
    If v > slot Then v = slot
    If v < minV Then v = minV
    FitIn = v
End Function

Private Sub AddSlimGradientButton( _
    ByVal ws As Worksheet, ByVal anchorRangeAddress As String, _
    ByVal shapeName As String, ByVal glyph As String, _
    ByVal titleText As String, ByVal descText As String, _
    ByVal macroName As String, ByRef theme As BtnTheme, _
    Optional ByVal accentRGB As Long = -1)

    Dim r As Range
    Dim btn As Shape
    Dim ico As Shape
    Dim leftPos As Double
    Dim topPos As Double
    Dim btnW As Double
    Dim btnH As Double
    Dim iconPad As Double
    Dim iconW As Double
    Dim textMargin As Double
    Dim label As String
    Dim titleLen As Long
    Dim totalLen As Long
    Dim acc As Long

    Set r = ws.Range(anchorRangeAddress)

    On Error Resume Next
    ws.Shapes(shapeName).Delete
    ws.Shapes(shapeName & "_ico").Delete
    On Error GoTo 0

    btnW = FitIn(r.Width - 4, 420, 130)
    btnH = FitIn(r.Height - 4, 44, 28)

    leftPos = r.Left + (r.Width - btnW) / 2
    topPos = r.Top + (r.Height - btnH) / 2

    iconPad = 7
    iconW = btnH * 0.5
    textMargin = iconPad + iconW + 8
    label = titleText & vbLf & descText

    If accentRGB = -1 Then
        acc = AccentColor()
    Else
        acc = accentRGB
    End If

    Set btn = ws.Shapes.AddShape(msoShapeRoundedRectangle, leftPos, topPos, btnW, btnH)

    With btn
        .Name = shapeName
        .OnAction = "'" & ThisWorkbook.Name & "'!" & macroName
        .Locked = False
        .Placement = xlMoveAndSize

        With .Fill
            .Visible = msoTrue
            .TwoColorGradient BTN_GRADIENT_STYLE, 1
            .ForeColor.RGB = theme.Fill
            .BackColor.RGB = acc
        End With

        With .Line
            .Visible = msoTrue
            .ForeColor.RGB = RGB(255, 255, 255)
            .Transparency = 0.65
            .Weight = 0.8
        End With

        On Error Resume Next
        .Shadow.Visible = msoTrue
        .Shadow.Transparency = 0.6
        .Shadow.Blur = 5
        .Shadow.OffsetX = 1
        .Shadow.OffsetY = 1
        On Error GoTo 0

        With .TextFrame2
            .VerticalAnchor = msoAnchorMiddle
            .WordWrap = msoTrue
            .MarginLeft = textMargin
            .MarginRight = 10
            .MarginTop = 3
            .MarginBottom = 3
            .TextRange.Text = label
            .TextRange.ParagraphFormat.Alignment = msoAlignCenter

            With .TextRange.Font
                .Name = FONT_BASE
                .Size = 9
                .Bold = msoTrue
                .Fill.ForeColor.RGB = theme.Font
            End With
        End With

        titleLen = Len(titleText)
        totalLen = Len(label)

        On Error Resume Next
        If totalLen > titleLen + 1 Then
            With .TextFrame.Characters(titleLen + 2, totalLen - (titleLen + 1)).Font
                .Name = FONT_BASE
                .Size = 7
                .Bold = False
                .Color = RGB(238, 242, 248)
            End With
        End If
        On Error GoTo 0
    End With

    Set ico = ws.Shapes.AddShape(msoShapeRectangle, leftPos + iconPad, topPos + (btnH - iconW) / 2, iconW, iconW)

    With ico
        .Name = shapeName & "_ico"
        .OnAction = "'" & ThisWorkbook.Name & "'!" & macroName
        .Locked = False
        .Placement = xlMoveAndSize
        .Fill.Visible = msoFalse
        .Line.Visible = msoFalse

        With .TextFrame2
            .VerticalAnchor = msoAnchorMiddle
            .WordWrap = msoFalse
            .MarginLeft = 0
            .MarginRight = 0
            .MarginTop = 0
            .MarginBottom = 0
            .TextRange.Text = glyph
            .TextRange.ParagraphFormat.Alignment = msoAlignCenter

            With .TextRange.Font
                .Name = FONT_ICON
                .Size = iconW * 0.82
                .Bold = msoTrue
                .Fill.ForeColor.RGB = theme.Font
            End With
        End With

        On Error Resume Next
        .ZOrder msoBringToFront
        On Error GoTo 0
    End With
End Sub
Private Sub BuildMapQuickButtons(ByVal ws As Worksheet, ByRef thm As BtnTheme)
    AddSlimGradientButton ws, "D5:F6", "itimMapSearch", GlyphFromCP(CP_SEARCH), _
        "SEARCH", "Find order or bay", "ITIM_ShowSearchForm", thm, RGB(91, 155, 213)

    AddSlimGradientButton ws, "G5:I6", "itimMapManageBay", GlyphFromCP(CP_PIN), _
        "BAY ACTIONS", "Clear, move, exception", "ITIM_ShowManageBayForm", thm, RGB(15, 255, 179)

    AddSlimGradientButton ws, "J5:L6", "itimMapManualEntry", GlyphFromCP(CP_TABLE), _
        "MANUAL ENTRY", "Assign order to bay", "ITIM_ShowManualEntryForm", thm, RGB(255, 181, 54)

    AddSlimGradientButton ws, "M5:O6", "itimMapRefresh", GlyphFromCP(CP_REFRESH), _
        "REFRESH", "Reload inventory", "ITIM_RefreshInventory", thm, RGB(91, 155, 213)

    AddSlimGradientButton ws, "P5:R6", "itimMapSdi", GlyphFromCP(CP_FLAG), _
        "SDI", "Mark or clear order", "ITIM_ShowSdiForm", thm, RGB(196, 196, 196)
End Sub

Private Sub BuildMapLiveStatusFrame(ByVal ws As Worksheet)
    With ws.Range("Q11:U18")
        .Clear
        .Interior.Color = RGB(245, 247, 250)
        .Borders.LineStyle = xlContinuous
        .Borders.Color = RGB(197, 210, 226)
        .Font.Name = FONT_BASE
        .Font.Size = 9
    End With

    With ws.Range("Q11:R11")
        .Merge
        .Value = "LIVE STATUS"
        .Interior.Color = RGB(47, 75, 117)
        .Font.Color = RGB(255, 255, 255)
        .Font.Bold = True
        .HorizontalAlignment = xlCenter
    End With

    ws.Range("Q12").Value = "Occupied"
    ws.Range("Q13").Value = "Preassigned"
    ws.Range("Q14").Value = "SDI"
    ws.Range("Q15").Value = "Exception"
    ws.Range("Q16").Value = "Not on map"
    ws.Range("Q17").Value = "Active total"

    With ws.Range("Q12:Q17")
        .Font.Bold = True
        .Font.Color = RGB(47, 75, 117)
    End With

    With ws.Range("R12:R17")
        .HorizontalAlignment = xlCenter
        .Font.Bold = True
    End With

    With ws.Range("S11:U11")
        .Merge
        .Value = "LEGEND"
        .Interior.Color = RGB(47, 75, 117)
        .Font.Color = RGB(255, 255, 255)
        .Font.Bold = True
        .HorizontalAlignment = xlCenter
    End With

    ws.Range("S12").Value = "PRE"
    ws.Range("S13").Value = "OCC"
    ws.Range("S14").Value = "SDI"
    ws.Range("S15").Value = "EXC"
    ws.Range("S16").Value = "MAP"
    ws.Range("S17").Value = "ACT"

    ws.Range("T12:U12").Merge
    ws.Range("T12").Value = "Preassigned"
    ws.Range("T13:U13").Merge
    ws.Range("T13").Value = "Occupied"
    ws.Range("T14:U14").Merge
    ws.Range("T14").Value = "Same Day Install"
    ws.Range("T15:U15").Merge
    ws.Range("T15").Value = "Manual exception"
    ws.Range("T16:U16").Merge
    ws.Range("T16").Value = "Not found on map"
    ws.Range("T17:U17").Merge
    ws.Range("T17").Value = "Active total"

    With ws.Range("S12:S17")
        .Font.Bold = True
        .HorizontalAlignment = xlCenter
        .Interior.Color = RGB(221, 230, 242)
        .Font.Color = RGB(47, 75, 117)
    End With

    With ws.Range("T12:U17")
        .Font.Color = RGB(47, 75, 117)
        .VerticalAlignment = xlCenter
    End With

    With ws.Range("Q18:U18")
        .Merge
        .Value = "Ready"
        .Interior.Color = RGB(221, 230, 242)
        .Font.Color = RGB(47, 75, 117)
        .Font.Bold = True
        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
        .WrapText = True
    End With
End Sub

