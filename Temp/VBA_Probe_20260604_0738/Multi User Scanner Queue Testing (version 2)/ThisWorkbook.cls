Attribute VB_Name = "ThisWorkbook"
Attribute VB_Base = "0{00020819-0000-0000-C000-000000000046}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = True
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = True
Option Explicit

'==============================================================================
' Module: ThisWorkbook_Master
' Workbook: Multi User Scanner Queue Testing.xlsm / Master Delivery List
'
' What this module does:
'   Workbook event and workbook-level orchestration code for the Master
'   Delivery List workbook.
'
' Why this module exists:
'   Excel events are the only place to intercept open/close, sheet changes,
'   selection changes, and edit-mode transitions reliably.
'
' Commenting standard used in this rewrite:
'   Procedure comments explain both what the code does and why that
'   behavior matters in the scanning / SharePoint / Power Automate workflow.
'   The code logic and public signatures are intentionally kept stable; this
'   pass is primarily a readability, maintainability, and safety pass.
'==============================================================================



'========================
'ThisWorkbook (Code)
'========================
' SHEET NAMES
'========================
Private Const DATA_SHEET_NAME As String = "Delivery List"
Private Const STAGING_SHEET_NAME As String = "Staging - Airport Rd"
Private Const SEND_SHEET_NAME As String = "Outbound - Airport Rd"
Private Const GREENVILLE_RECV_SHEET_NAME As String = "Inbound - Greenville"
Private Const GREENVILLE_CUSTOMER_TEXT As String = "BFS East Greenville SC MW"
Private Const CPU_SHEET_NAME As String = "Customer Pickup"
Private Const CPU_ROUTE_TEXT As String = "CPU"
Private Const HEADER_ROW_FIXED As Long = 5
Private Const FIRST_DATA_ROW_FIXED As Long = 6

'Delivery list headers (main list only)
Private Const HDR_ORDER As String = "Order Nr."
Private Const HDR_ITEM As String = "Item Nr."

'Highlight only A:N
Private Const SEND_COMMENTS_COL As Long = 23      'W
Private Const RECV_COMMENTS_COL As Long = 32      'AF
Private Const RECV_BAY_COL As Long = 33           'AG
Private Const STAGING_COMMENTS_COL As Long = 48   'AV
Private Const FIRST_DATA_ROW As Long = 6

Private lastSelectedSheetName As String
Private lastSelectedCellAddress As String
Private lastSelectedCellValue As Variant

Private mFirstViewResetDone As Object
Private mIsShowingScannedRow As Boolean

Private currentChangeNoticeShown As Boolean
Private lastManualChangeKey As String
Private shownScanInstructionsPopup As Boolean
Private Const REMAKE_MARKER_COL_FIXED As Long = 11
Private Const ROUTE_COL_FIXED As Long = 12
Private Const PROCESS_STATE_COL_FIXED As Long = 13
Private Const LIST_LAST_COL As Long = 13             'M
Private Const SCAN_HIGHLIGHT_LAST_COL As Long = 10   'L
Private mManualEditsPending As Boolean
Private mHandlingEditExit As Boolean
Private mEditStartKeys As Object
Private mEditSnapshot As Object
Private mEditStartRowState As Object

Private Const SCAN_QUEUE_SHEET_NAME As String = "__SCAN_QUEUE__"
Private mScanQueueProcessorScheduled As Boolean
Private mScanQueueProcessorRunning As Boolean
Private mNextScanQueueRun As Date
Private mPrevMoveAfterReturn As Boolean
Private mPrevMoveAfterReturnDirection As Long
'========================
' MANUAL EDIT PERSISTENCE
'========================
Private Const MANUAL_EDIT_STATE_SHEET As String = "__MANUAL_EDIT_STATE__"
Private Const MANUAL_EDIT_PINK As Long = 6684927   'RGB(255, 0, 102)

'------------------------------------------------------------------------------
' Procedure: HasSavedManualEditRecords
' Scope: Private Function
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   HasSavedManualEditRecords.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function HasSavedManualEditRecords() As Boolean
    Dim ws As Worksheet
    Dim lastRow As Long

    Set ws = GetOrCreateManualEditStateSheet()
    lastRow = ws.Cells(ws.rows.Count, 1).End(xlUp).Row

    HasSavedManualEditRecords = (lastRow >= 2)
End Function

'------------------------------------------------------------------------------
' Procedure: ClearManualEditMarksEverywhere
' Scope: Private Sub
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   ClearManualEditMarksEverywhere.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ClearManualEditMarksEverywhere(Optional ByVal clearStateRecords As Boolean = True)
    Dim ws As Worksheet

    If clearStateRecords Then
        ClearManualEditStateSheetRecords
    End If

    ClearManualEditMarksForSheet ThisWorkbook.Worksheets(DATA_SHEET_NAME)

    Set ws = GetSheetIfExists(STAGING_SHEET_NAME)
    If Not ws Is Nothing Then ClearManualEditMarksForSheet ws

    Set ws = GetSheetIfExists(SEND_SHEET_NAME)
    If Not ws Is Nothing Then ClearManualEditMarksForSheet ws

    Set ws = CurrentRecvSheet()
    If Not ws Is Nothing Then ClearManualEditMarksForSheet ws

    Set ws = GetSheetIfExists(GREENVILLE_RECV_SHEET_NAME)
    If Not ws Is Nothing Then ClearManualEditMarksForSheet ws

    Set ws = GetSheetIfExists(CPU_SHEET_NAME)
    If Not ws Is Nothing Then ClearManualEditMarksForSheet ws
End Sub

'------------------------------------------------------------------------------
' Procedure: GetOrCreateManualEditStateSheet
' Scope: Private Function
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   GetOrCreateManualEditStateSheet.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetOrCreateManualEditStateSheet() As Worksheet
    Dim ws As Worksheet

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(MANUAL_EDIT_STATE_SHEET)
    On Error GoTo 0

    If ws Is Nothing Then
        Set ws = ThisWorkbook.Worksheets.Add(After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
        ws.Name = MANUAL_EDIT_STATE_SHEET
    End If

    On Error Resume Next
    ws.Visible = xlSheetVisible
    ws.Unprotect Password:=""
    On Error GoTo 0

    If Len(CStr(ws.Range("A1").Value)) = 0 Then
        ws.Range("A1:E1").Value = Array("RowKey", "ColStart", "ColEnd", "Stamp", "Token")
    End If

    ws.Visible = xlSheetVeryHidden
    Set GetOrCreateManualEditStateSheet = ws
End Function

'------------------------------------------------------------------------------
' Procedure: GetSheetIfExists
' Scope: Private Function
'
' What it does:
'   Finds, creates, deletes, rebuilds, protects, or synchronizes worksheets
'   for GetSheetIfExists.
'
' Why it exists:
'   The master workbook creates multiple operational views from one delivery
'   list; worksheet helpers keep those views from drifting apart.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetSheetIfExists(ByVal sheetName As String) As Worksheet
    On Error Resume Next
    Set GetSheetIfExists = ThisWorkbook.Worksheets(sheetName)
    On Error GoTo 0
End Function

'------------------------------------------------------------------------------
' Procedure: FindHeaderCellLocal
' Scope: Private Function
'
' What it does:
'   Finds, writes, validates, or uses worksheet header cells for
'   FindHeaderCellLocal.
'
' Why it exists:
'   Header locations can move during import/rebuild, so the code uses header
'   discovery to target the correct columns instead of guessing.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function FindHeaderCellLocal(ByVal ws As Worksheet, ByVal headerNames As Variant) As Range
    Set FindHeaderCellLocal = FindHeaderCellInCols(ws, headerNames, "A:N", 250)
End Function

'------------------------------------------------------------------------------
' Procedure: IsSectionHeaderRowLocal
' Scope: Private Function
'
' What it does:
'   Finds, writes, validates, or uses worksheet header cells for
'   IsSectionHeaderRowLocal.
'
' Why it exists:
'   Header locations can move during import/rebuild, so the code uses header
'   discovery to target the correct columns instead of guessing.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function IsSectionHeaderRowLocal(ByVal ws As Worksheet, ByVal rowNum As Long, _
                                         ByVal orderCol As Long, ByVal itemCol As Long) As Boolean
    Dim leftText As String
    Dim ordTxt As String
    Dim itemTxt As String

    leftText = Trim$(CStr(ws.Cells(rowNum, 1).Value))
    ordTxt = Trim$(CStr(ws.Cells(rowNum, orderCol).Value))
    itemTxt = Trim$(CStr(ws.Cells(rowNum, itemCol).Value))

    IsSectionHeaderRowLocal = (Len(leftText) > 0 And Len(ordTxt) = 0 And Len(itemTxt) = 0)
End Function

'------------------------------------------------------------------------------
' Procedure: IsRealDeliveryLineLocal
' Scope: Private Function
'
' What it does:
'   Returns a True/False decision used by higher-level workflow code
'   (IsRealDeliveryLineLocal).
'
' Why it exists:
'   Boolean helpers make business rules readable and keep condition checks
'   consistent across modules.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function IsRealDeliveryLineLocal(ByVal ws As Worksheet, ByVal rowNum As Long, _
                                         ByVal orderCol As Long, ByVal itemCol As Long) As Boolean
    IsRealDeliveryLineLocal = _
        (Len(Trim$(CStr(ws.Cells(rowNum, orderCol).Value))) > 0 Or _
         Len(Trim$(CStr(ws.Cells(rowNum, itemCol).Value))) > 0)
End Function

'------------------------------------------------------------------------------
' Procedure: NormalizeSectionKeyLocal
' Scope: Private Function
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   NormalizeSectionKeyLocal.
'
' Why it exists:
'   Remakes need separate visual and print/export handling so replacement
'   glass is not confused with regular delivery-list work.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function NormalizeSectionKeyLocal(ByVal s As String) As String
    NormalizeSectionKeyLocal = UCase$(Trim$(s))
End Function

'------------------------------------------------------------------------------
' Procedure: BuildDeliveryLineKeyLocal
' Scope: Private Function
'
' What it does:
'   Builds a derived value, key, JSON block, layout, collection, or workbook
'   object used later by the workflow (BuildDeliveryLineKeyLocal).
'
' Why it exists:
'   The project uses generated keys/layouts to keep repeated logic consistent
'   instead of hand-building values in multiple places.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BuildDeliveryLineKeyLocal(ByVal ws As Worksheet, ByVal rowNum As Long, _
                                           ByVal sectionKey As String, _
                                           ByVal orderCol As Long, ByVal itemCol As Long) As String
    Dim ordTxt As String
    Dim itemTxt As String

    ordTxt = Trim$(CStr(ws.Cells(rowNum, orderCol).Value))

    If IsNumeric(ws.Cells(rowNum, itemCol).Value) Then
        itemTxt = Format$(CLng(Val(ws.Cells(rowNum, itemCol).Value)), "000")
    Else
        itemTxt = Trim$(CStr(ws.Cells(rowNum, itemCol).Value))
    End If

    BuildDeliveryLineKeyLocal = NormalizeSectionKeyLocal(sectionKey) & "|" & ordTxt & "|" & itemTxt
End Function

'------------------------------------------------------------------------------
' Procedure: GetRowKeyForManualEdit
' Scope: Private Function
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   GetRowKeyForManualEdit.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetRowKeyForManualEdit(ByVal ws As Worksheet, ByVal rowNum As Long) As String
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim orderCol As Long
    Dim itemCol As Long
    Dim firstDataRow As Long
    Dim r As Long
    Dim currentSectionKey As String

    Set orderHdr = FindHeaderCellLocal(ws, Array(HDR_ORDER))
    Set itemHdr = FindHeaderCellLocal(ws, Array(HDR_ITEM, "Item"))

    If orderHdr Is Nothing Or itemHdr Is Nothing Then Exit Function

    orderCol = orderHdr.Column
    itemCol = itemHdr.Column
    firstDataRow = orderHdr.Row + 1

    If rowNum < firstDataRow Then Exit Function
    If Not IsRealDeliveryLineLocal(ws, rowNum, orderCol, itemCol) Then Exit Function

    currentSectionKey = "__UNSECTIONED__"

    For r = firstDataRow To rowNum
        If IsSectionHeaderRowLocal(ws, r, orderCol, itemCol) Then
            currentSectionKey = NormalizeSectionKeyLocal(CStr(ws.Cells(r, 1).Value))
            If Len(currentSectionKey) = 0 Then currentSectionKey = "__UNSECTIONED__"
        End If
    Next r

    GetRowKeyForManualEdit = BuildDeliveryLineKeyLocal(ws, rowNum, currentSectionKey, orderCol, itemCol)
End Function

'------------------------------------------------------------------------------
' Procedure: BuildCurrentDeliveryKeySetForEdit
' Scope: Private Function
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   BuildCurrentDeliveryKeySetForEdit.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BuildCurrentDeliveryKeySetForEdit() As Object
    Dim dict As Object
    Dim ws As Worksheet
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim orderCol As Long
    Dim itemCol As Long
    Dim firstDataRow As Long
    Dim lastRow As Long
    Dim r As Long
    Dim currentSectionKey As String
    Dim rowKey As String

    Set dict = CreateObject("Scripting.Dictionary")
    Set ws = ThisWorkbook.Worksheets(DATA_SHEET_NAME)

    Set orderHdr = FindHeaderCellLocal(ws, Array(HDR_ORDER))
    Set itemHdr = FindHeaderCellLocal(ws, Array(HDR_ITEM, "Item"))
    If orderHdr Is Nothing Or itemHdr Is Nothing Then
        Set BuildCurrentDeliveryKeySetForEdit = dict
        Exit Function
    End If

    orderCol = orderHdr.Column
    itemCol = itemHdr.Column
    firstDataRow = orderHdr.Row + 1
    lastRow = ws.Cells(ws.rows.Count, orderCol).End(xlUp).Row
    currentSectionKey = "__UNSECTIONED__"

    For r = firstDataRow To lastRow
        If IsSectionHeaderRowLocal(ws, r, orderCol, itemCol) Then
            currentSectionKey = NormalizeSectionKeyLocal(CStr(ws.Cells(r, 1).Value))
            If Len(currentSectionKey) = 0 Then currentSectionKey = "__UNSECTIONED__"

        ElseIf IsRealDeliveryLineLocal(ws, r, orderCol, itemCol) Then
            rowKey = BuildDeliveryLineKeyLocal(ws, r, currentSectionKey, orderCol, itemCol)
            If Len(rowKey) > 0 Then
                If Not dict.Exists(rowKey) Then dict.Add rowKey, True
            End If
        End If
    Next r

    Set BuildCurrentDeliveryKeySetForEdit = dict
End Function

'------------------------------------------------------------------------------
' Procedure: BuildManualEditStartStateKey
' Scope: Private Function
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   BuildManualEditStartStateKey.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BuildManualEditStartStateKey(ByVal rowKey As String, ByVal occurrenceIndex As Long) As String
    BuildManualEditStartStateKey = rowKey & "|" & CStr(occurrenceIndex)
End Function

'------------------------------------------------------------------------------
' Procedure: BuildCurrentDeliveryRowStateMapForEdit
' Scope: Private Function
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   BuildCurrentDeliveryRowStateMapForEdit.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BuildCurrentDeliveryRowStateMapForEdit() As Object
    Dim dict As Object
    Dim counts As Object
    Dim ws As Worksheet
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim orderCol As Long
    Dim itemCol As Long
    Dim firstDataRow As Long
    Dim lastRow As Long
    Dim r As Long
    Dim currentSectionKey As String
    Dim rowKey As String
    Dim occ As Long

    Set dict = CreateObject("Scripting.Dictionary")
    Set counts = CreateObject("Scripting.Dictionary")
    Set ws = ThisWorkbook.Worksheets(DATA_SHEET_NAME)

    Set orderHdr = FindHeaderCellLocal(ws, Array(HDR_ORDER))
    Set itemHdr = FindHeaderCellLocal(ws, Array(HDR_ITEM, "Item"))
    If orderHdr Is Nothing Or itemHdr Is Nothing Then
        Set BuildCurrentDeliveryRowStateMapForEdit = dict
        Exit Function
    End If

    orderCol = orderHdr.Column
    itemCol = itemHdr.Column
    firstDataRow = orderHdr.Row + 1
    lastRow = ws.Cells(ws.rows.Count, orderCol).End(xlUp).Row
    currentSectionKey = "__UNSECTIONED__"

    For r = firstDataRow To lastRow
        If IsSectionHeaderRowLocal(ws, r, orderCol, itemCol) Then
            currentSectionKey = NormalizeSectionKeyLocal(CStr(ws.Cells(r, 1).Value))
            If Len(currentSectionKey) = 0 Then currentSectionKey = "__UNSECTIONED__"

        ElseIf IsRealDeliveryLineLocal(ws, r, orderCol, itemCol) Then
            rowKey = BuildDeliveryLineKeyLocal(ws, r, currentSectionKey, orderCol, itemCol)

            If Len(rowKey) > 0 Then
                If counts.Exists(rowKey) Then
                    occ = CLng(counts(rowKey)) + 1
                    counts(rowKey) = occ
                Else
                    occ = 1
                    counts.Add rowKey, occ
                End If

                dict(BuildManualEditStartStateKey(rowKey, occ)) = GetRowSnapshotValue(ws, r)
            End If
        End If
    Next r

    Set BuildCurrentDeliveryRowStateMapForEdit = dict
End Function

'------------------------------------------------------------------------------
' Procedure: GetRowOccurrenceIndexForManualEdit
' Scope: Private Function
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   GetRowOccurrenceIndexForManualEdit.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetRowOccurrenceIndexForManualEdit(ByVal ws As Worksheet, ByVal rowNum As Long, _
                                                    ByVal firstDataRow As Long, ByVal orderCol As Long, _
                                                    ByVal itemCol As Long, ByVal targetRowKey As String) As Long
    Dim r As Long
    Dim currentSectionKey As String
    Dim rowKey As String
    Dim occ As Long

    currentSectionKey = "__UNSECTIONED__"

    For r = firstDataRow To rowNum
        If IsSectionHeaderRowLocal(ws, r, orderCol, itemCol) Then
            currentSectionKey = NormalizeSectionKeyLocal(CStr(ws.Cells(r, 1).Value))
            If Len(currentSectionKey) = 0 Then currentSectionKey = "__UNSECTIONED__"

        ElseIf IsRealDeliveryLineLocal(ws, r, orderCol, itemCol) Then
            rowKey = BuildDeliveryLineKeyLocal(ws, r, currentSectionKey, orderCol, itemCol)

            If StrComp(rowKey, targetRowKey, vbBinaryCompare) = 0 Then
                occ = occ + 1
            End If
        End If
    Next r

    GetRowOccurrenceIndexForManualEdit = occ
End Function

'------------------------------------------------------------------------------
' Procedure: GetManualEditStateKeyForRow
' Scope: Private Function
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   GetManualEditStateKeyForRow.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetManualEditStateKeyForRow(ByVal ws As Worksheet, ByVal rowNum As Long) As String
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim orderCol As Long
    Dim itemCol As Long
    Dim firstDataRow As Long
    Dim rowKey As String
    Dim occ As Long

    If ws Is Nothing Then Exit Function
    If rowNum < 1 Then Exit Function

    Set orderHdr = FindHeaderCellLocal(ws, Array(HDR_ORDER))
    Set itemHdr = FindHeaderCellLocal(ws, Array(HDR_ITEM, "Item"))
    If orderHdr Is Nothing Or itemHdr Is Nothing Then Exit Function

    orderCol = orderHdr.Column
    itemCol = itemHdr.Column
    firstDataRow = orderHdr.Row + 1

    rowKey = GetRowKeyForManualEdit(ws, rowNum)
    If Len(rowKey) = 0 Then Exit Function

    occ = GetRowOccurrenceIndexForManualEdit(ws, rowNum, firstDataRow, orderCol, itemCol, rowKey)
    If occ <= 0 Then Exit Function

    GetManualEditStateKeyForRow = BuildManualEditStartStateKey(rowKey, occ)
End Function

'------------------------------------------------------------------------------
' Procedure: RebuildManualEditStateFromDeliveryList
' Scope: Private Sub
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   RebuildManualEditStateFromDeliveryList.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub RebuildManualEditStateFromDeliveryList()
    Dim ws As Worksheet
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim orderCol As Long
    Dim itemCol As Long
    Dim firstDataRow As Long
    Dim lastRow As Long
    Dim r As Long
    Dim stateKey As String
    Dim rowBand As Range

    Set ws = ThisWorkbook.Worksheets(DATA_SHEET_NAME)

    ClearManualEditStateSheetRecords

    Set orderHdr = FindHeaderCellLocal(ws, Array(HDR_ORDER))
    Set itemHdr = FindHeaderCellLocal(ws, Array(HDR_ITEM, "Item"))
    If orderHdr Is Nothing Or itemHdr Is Nothing Then Exit Sub

    orderCol = orderHdr.Column
    itemCol = itemHdr.Column
    firstDataRow = orderHdr.Row + 1
    lastRow = ws.Cells(ws.rows.Count, orderCol).End(xlUp).Row

    For r = firstDataRow To lastRow
        If Not IsSectionHeaderRowLocal(ws, r, orderCol, itemCol) Then
            If IsRealDeliveryLineLocal(ws, r, orderCol, itemCol) Then
                Set rowBand = GetManualEditBandForRow(ws, r)

                If Not rowBand Is Nothing Then
                    If HasManualEditOutline(rowBand) Then
                        stateKey = GetManualEditStateKeyForRow(ws, r)
                        If Len(stateKey) > 0 Then
                            SaveManualEditRecord stateKey, 1, 10
                        End If
                    End If
                End If
            End If
        End If
    Next r
End Sub

'------------------------------------------------------------------------------
' Procedure: ClearManualEditStateSheetRecords
' Scope: Private Sub
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   ClearManualEditStateSheetRecords.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ClearManualEditStateSheetRecords()
    Dim ws As Worksheet
    Dim lastRow As Long

    Set ws = GetOrCreateManualEditStateSheet()

    lastRow = ws.Cells(ws.rows.Count, 1).End(xlUp).Row
    If lastRow >= 2 Then
        ws.Range("A2:E" & lastRow).ClearContents
    End If

    ws.Visible = xlSheetVeryHidden
End Sub

'------------------------------------------------------------------------------
' Procedure: ClearManualEditBorderIfPink
' Scope: Private Sub
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   ClearManualEditBorderIfPink.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ClearManualEditBorderIfPink(ByVal b As Border)
    On Error Resume Next
    If b.LineStyle <> xlNone Then
        If b.Color = MANUAL_EDIT_PINK Then
            b.LineStyle = xlNone
        End If
    End If
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: ClearManualEditOutlineIfPink
' Scope: Private Sub
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   ClearManualEditOutlineIfPink.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ClearManualEditOutlineIfPink(ByVal rng As Range)
    Dim c As Range

    If rng Is Nothing Then Exit Sub

    For Each c In rng.Cells
        ClearManualEditBorderIfPink c.Borders(xlEdgeLeft)
        ClearManualEditBorderIfPink c.Borders(xlEdgeTop)
        ClearManualEditBorderIfPink c.Borders(xlEdgeBottom)
        ClearManualEditBorderIfPink c.Borders(xlEdgeRight)
    Next c
End Sub

'------------------------------------------------------------------------------
' Procedure: ClearManualEditMarksForSheet
' Scope: Private Sub
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   ClearManualEditMarksForSheet.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ClearManualEditMarksForSheet(ByVal ws As Worksheet)
    Dim lastRow As Long
    Dim firstRow As Long

    If ws Is Nothing Then Exit Sub

    lastRow = GetLastUsedRow(ws)
    If lastRow < 1 Then Exit Sub

    firstRow = FIRST_DATA_ROW_FIXED
    If lastRow < firstRow Then Exit Sub

    ClearManualEditOutlineIfPink ws.Range("A" & firstRow & ":M" & lastRow)
End Sub

'------------------------------------------------------------------------------
' Procedure: ResetManualEditSessionState
' Scope: Private Sub
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   ResetManualEditSessionState.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ResetManualEditSessionState()
    'Legacy helper:
    'only clear saved pink manual-edit markers.
    'Do NOT rebuild sheet formatting or refresh scanner sheets here.
    ClearManualEditMarksEverywhere True
End Sub

'------------------------------------------------------------------------------
' Procedure: BeginDeliveryListEditSession
' Scope: Public Sub
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   BeginDeliveryListEditSession.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub BeginDeliveryListEditSession()
    Dim resp As VbMsgBoxResult

    'Do NOT rebuild or refresh anything here.
    'We only decide whether to keep or clear prior pink manual-edit marks.
    If HasSavedManualEditRecords() Then
        resp = MsgBox( _
            "Previous manual edit highlights were found." & vbCrLf & vbCrLf & _
            "Do you want to remove the previous manual edits?" & vbCrLf & vbCrLf & _
            "Yes = clear previous pink manual edit outlines" & vbCrLf & _
            "No = keep previous pink manual edit outlines" & vbCrLf & _
            "Cancel = do not enter edit mode", _
            vbYesNoCancel + vbQuestion + vbDefaultButton2, _
            "Manual Edit Highlights")

        If resp = vbCancel Then Exit Sub

        If resp = vbYes Then
            ClearManualEditMarksEverywhere True
        End If
    End If

    Set mEditStartKeys = BuildCurrentDeliveryKeySetForEdit()
    Set mEditStartRowState = BuildCurrentDeliveryRowStateMapForEdit()
    mManualEditsPending = False
    Set mEditSnapshot = CreateObject("Scripting.Dictionary")
End Sub

'------------------------------------------------------------------------------
' Procedure: IsKnownPreEditRowKey
' Scope: Private Function
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   IsKnownPreEditRowKey.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function IsKnownPreEditRowKey(ByVal rowKey As String) As Boolean
    On Error Resume Next
    IsKnownPreEditRowKey = (Not mEditStartKeys Is Nothing) And mEditStartKeys.Exists(rowKey)
    On Error GoTo 0
End Function

'------------------------------------------------------------------------------
' Procedure: GetManualEditRange
' Scope: Private Function
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   GetManualEditRange.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetManualEditRange(ByVal c As Range) As Range
    Dim rng As Range

    If c.MergeCells Then
        Set rng = c.MergeArea
    Else
        Set rng = c
    End If

    Set GetManualEditRange = Intersect(rng, c.Worksheet.Range("A:J"))
End Function

'------------------------------------------------------------------------------
' Procedure: GetManualEditBandForRow
' Scope: Private Function
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   GetManualEditBandForRow.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetManualEditBandForRow(ByVal ws As Worksheet, ByVal rowNum As Long) As Range
    If ws Is Nothing Then Exit Function
    If rowNum < 1 Then Exit Function

    Set GetManualEditBandForRow = ws.Range("A" & rowNum & ":J" & rowNum)
End Function

'------------------------------------------------------------------------------
' Procedure: GetRowSnapshotKey
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   GetRowSnapshotKey.
'
' Why it exists:
'   Rows may represent real orders, section headers, remakes, Greenville work,
'   Customer Pickup work, or updated rows; each type needs different handling.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetRowSnapshotKey(ByVal ws As Worksheet, ByVal rowNum As Long) As String
    GetRowSnapshotKey = UCase$(ws.Name) & "|ROW|" & CStr(rowNum)
End Function

'------------------------------------------------------------------------------
' Procedure: GetCellContentSignature
' Scope: Private Function
'
' What it does:
'   Returns a workbook object, setting, status value, parsed value, or
'   calculated result used by other procedures (GetCellContentSignature).
'
' Why it exists:
'   Using one getter keeps callers from duplicating lookup logic and protects
'   them from missing sheets, missing names, or blank values.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetCellContentSignature(ByVal c As Range) As String
    If c Is Nothing Then Exit Function

    On Error Resume Next

    If c.HasFormula Then
        GetCellContentSignature = "F:" & CStr(c.Formula2)
    Else
        GetCellContentSignature = "V:" & CStr(c.Value2)
    End If

    On Error GoTo 0
End Function

'------------------------------------------------------------------------------
' Procedure: GetRowSnapshotValue
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   GetRowSnapshotValue.
'
' Why it exists:
'   Rows may represent real orders, section headers, remakes, Greenville work,
'   Customer Pickup work, or updated rows; each type needs different handling.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetRowSnapshotValue(ByVal ws As Worksheet, ByVal rowNum As Long) As String
    Dim band As Range
    Dim c As Range
    Dim s As String

    Set band = GetManualEditBandForRow(ws, rowNum)
    If band Is Nothing Then Exit Function

    For Each c In band.Cells
        s = s & "|" & GetCellContentSignature(c)
    Next c

    GetRowSnapshotValue = s
End Function

'------------------------------------------------------------------------------
' Procedure: CaptureEditSnapshotForRow
' Scope: Private Sub
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   CaptureEditSnapshotForRow.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub CaptureEditSnapshotForRow(ByVal ws As Worksheet, ByVal rowNum As Long)
    Dim key As String

    If ws Is Nothing Then Exit Sub
    If rowNum < 1 Then Exit Sub

    EnsureEditSnapshotStore

    key = GetRowSnapshotKey(ws, rowNum)
    mEditSnapshot(key) = GetRowSnapshotValue(ws, rowNum)
End Sub

'------------------------------------------------------------------------------
' Procedure: DidRowActuallyChange
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   DidRowActuallyChange.
'
' Why it exists:
'   Rows may represent real orders, section headers, remakes, Greenville work,
'   Customer Pickup work, or updated rows; each type needs different handling.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function DidRowActuallyChange(ByVal ws As Worksheet, ByVal rowNum As Long) As Boolean
    Dim key As String
    Dim oldValue As String
    Dim newValue As String

    If ws Is Nothing Then Exit Function
    If rowNum < 1 Then Exit Function

    EnsureEditSnapshotStore

    key = GetRowSnapshotKey(ws, rowNum)
    newValue = GetRowSnapshotValue(ws, rowNum)

    If Not mEditSnapshot.Exists(key) Then
        DidRowActuallyChange = True
        Exit Function
    End If

    oldValue = CStr(mEditSnapshot(key))
    DidRowActuallyChange = (StrComp(oldValue, newValue, vbBinaryCompare) <> 0)
End Function

'------------------------------------------------------------------------------
' Procedure: EnsureEditSnapshotStore
' Scope: Private Sub
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   EnsureEditSnapshotStore.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub EnsureEditSnapshotStore()
    If mEditSnapshot Is Nothing Then
        Set mEditSnapshot = CreateObject("Scripting.Dictionary")
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: GetSnapshotKey
' Scope: Private Function
'
' What it does:
'   Handles part of the master-to-intake snapshot workflow for GetSnapshotKey.
'
' Why it exists:
'   Snapshots let intake workbooks display and scan against current delivery
'   data without opening or editing the master workbook.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetSnapshotKey(ByVal ws As Worksheet, ByVal rng As Range) As String
    GetSnapshotKey = UCase$(ws.Name) & "|" & rng.Address(False, False)
End Function

'------------------------------------------------------------------------------
' Procedure: GetRangeSnapshotValue
' Scope: Private Function
'
' What it does:
'   Handles part of the master-to-intake snapshot workflow for
'   GetRangeSnapshotValue.
'
' Why it exists:
'   Snapshots let intake workbooks display and scan against current delivery
'   data without opening or editing the master workbook.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetRangeSnapshotValue(ByVal rng As Range) As String
    Dim c As Range
    Dim s As String

    If rng Is Nothing Then Exit Function

    If rng.MergeCells Then
        Set rng = rng.MergeArea
    End If

    For Each c In rng.Cells
        s = s & "|" & GetCellContentSignature(c)
    Next c

    GetRangeSnapshotValue = s
End Function

'------------------------------------------------------------------------------
' Procedure: CaptureEditSnapshotForRange
' Scope: Private Sub
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   CaptureEditSnapshotForRange.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub CaptureEditSnapshotForRange(ByVal ws As Worksheet, ByVal rng As Range)
    Dim key As String

    If ws Is Nothing Then Exit Sub
    If rng Is Nothing Then Exit Sub

    EnsureEditSnapshotStore

    key = GetSnapshotKey(ws, rng)
    mEditSnapshot(key) = GetRangeSnapshotValue(rng)
End Sub

'------------------------------------------------------------------------------
' Procedure: DidEditRangeActuallyChange
' Scope: Private Function
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   DidEditRangeActuallyChange.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function DidEditRangeActuallyChange(ByVal ws As Worksheet, ByVal rng As Range) As Boolean
    Dim key As String
    Dim oldValue As String
    Dim newValue As String

    If ws Is Nothing Then Exit Function
    If rng Is Nothing Then Exit Function

    EnsureEditSnapshotStore

    key = GetSnapshotKey(ws, rng)
    newValue = GetRangeSnapshotValue(rng)

    If Not mEditSnapshot.Exists(key) Then
        'No prior snapshot means treat it as changed
        DidEditRangeActuallyChange = True
        Exit Function
    End If

    oldValue = CStr(mEditSnapshot(key))
    DidEditRangeActuallyChange = (StrComp(oldValue, newValue, vbBinaryCompare) <> 0)
End Function

'------------------------------------------------------------------------------
' Procedure: CaptureEditSnapshotForTarget
' Scope: Private Sub
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   CaptureEditSnapshotForTarget.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub CaptureEditSnapshotForTarget(ByVal ws As Worksheet, ByVal target As Range)
    Dim c As Range
    Dim rng As Range
    Dim seen As Object
    Dim addrKey As String

    If ws Is Nothing Then Exit Sub
    If target Is Nothing Then Exit Sub

    Set seen = CreateObject("Scripting.Dictionary")

    For Each c In target.Cells
        Set rng = GetManualEditRange(c)
        If Not rng Is Nothing Then
            addrKey = rng.Address(False, False)
            If Not seen.Exists(addrKey) Then
                seen.Add addrKey, True
                CaptureEditSnapshotForRange ws, rng
            End If
        End If
    Next c
End Sub

'------------------------------------------------------------------------------
' Procedure: Workbook_SheetSelectionChange
' Scope: Private Sub
'
' What it does:
'   Captures selection context and edit snapshots before a user changes cells.
'
' Why it exists:
'   Manual edit detection needs a before-value snapshot so the workbook can
'   tell whether a row really changed.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub Workbook_SheetSelectionChange(ByVal Sh As Object, ByVal target As Range)
    On Error GoTo SafeExit

    Dim rng As Range
    Dim rw As Range
    Dim seen As Object

    If Sh Is Nothing Then Exit Sub
    If target Is Nothing Then Exit Sub
    If target.CountLarge < 1 Then Exit Sub

    lastSelectedSheetName = Sh.Name
    lastSelectedCellAddress = target.Cells(1, 1).Address(False, False)
    lastSelectedCellValue = target.Cells(1, 1).Value

    If Sh.Name = DATA_SHEET_NAME And IsDeliveryEditModeOn() Then
        Set rng = Intersect(target, Sh.Range("A:J"))
        If Not rng Is Nothing Then
            Set seen = CreateObject("Scripting.Dictionary")

            For Each rw In rng.rows
                If Not seen.Exists(CStr(rw.Row)) Then
                    seen.Add CStr(rw.Row), True
                    CaptureEditSnapshotForRow Sh, rw.Row
                End If
            Next rw
        End If
    End If

SafeExit:
End Sub

'------------------------------------------------------------------------------
' Procedure: HasManualEditOutline
' Scope: Private Function
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   HasManualEditOutline.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function HasManualEditOutline(ByVal rng As Range) As Boolean
    If rng Is Nothing Then Exit Function

    On Error Resume Next

    'Only count this as a true manual-edit row if the row band itself
    'has BOTH the left and right pink edges.
    'This avoids falsely picking up the row above, which can inherit a
    'shared top/bottom border visually from Excel.
    HasManualEditOutline = _
        (rng.Borders(xlEdgeLeft).LineStyle <> xlNone And rng.Borders(xlEdgeLeft).Color = MANUAL_EDIT_PINK) And _
        (rng.Borders(xlEdgeRight).LineStyle <> xlNone And rng.Borders(xlEdgeRight).Color = MANUAL_EDIT_PINK)

    On Error GoTo 0
End Function

'------------------------------------------------------------------------------
' Procedure: ApplyManualEditOutline
' Scope: Private Sub
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   ApplyManualEditOutline.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ApplyManualEditOutline(ByVal rng As Range)
    If rng Is Nothing Then Exit Sub

    'Only clear old pink outline, not all borders
    ClearManualEditOutlineIfPink rng

    With rng.Borders(xlEdgeLeft)
        .LineStyle = xlContinuous
        .Weight = xlMedium
        .Color = MANUAL_EDIT_PINK
    End With
    With rng.Borders(xlEdgeTop)
        .LineStyle = xlContinuous
        .Weight = xlMedium
        .Color = MANUAL_EDIT_PINK
    End With
    With rng.Borders(xlEdgeBottom)
        .LineStyle = xlContinuous
        .Weight = xlMedium
        .Color = MANUAL_EDIT_PINK
    End With
    With rng.Borders(xlEdgeRight)
        .LineStyle = xlContinuous
        .Weight = xlMedium
        .Color = MANUAL_EDIT_PINK
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: ClearManualEditOutline
' Scope: Private Sub
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   ClearManualEditOutline.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ClearManualEditOutline(ByVal rng As Range)
    If rng Is Nothing Then Exit Sub
    ClearManualEditOutlineIfPink rng
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplyManualEditMark
' Scope: Private Sub
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   ApplyManualEditMark.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ApplyManualEditMark(ByVal rng As Range)
    If rng Is Nothing Then Exit Sub
    ApplyManualEditOutline rng
End Sub

'------------------------------------------------------------------------------
' Procedure: ClearManualEditMark
' Scope: Private Sub
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   ClearManualEditMark.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ClearManualEditMark(ByVal rng As Range)
    If rng Is Nothing Then Exit Sub
    ClearManualEditOutline rng
End Sub

'------------------------------------------------------------------------------
' Procedure: SaveManualEditRecord
' Scope: Private Sub
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   SaveManualEditRecord.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub SaveManualEditRecord(ByVal rowKey As String, ByVal colStart As Long, ByVal colEnd As Long)
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim r As Long
    Dim token As String

    If Len(rowKey) = 0 Then Exit Sub

    Set ws = GetOrCreateManualEditStateSheet()
    token = rowKey & "|" & CStr(colStart) & "|" & CStr(colEnd)

    lastRow = ws.Cells(ws.rows.Count, 1).End(xlUp).Row
    If lastRow < 2 Then lastRow = 1

    For r = 2 To lastRow
        If StrComp(CStr(ws.Cells(r, 5).Value), token, vbTextCompare) = 0 Then Exit Sub
    Next r

    ws.Cells(lastRow + 1, 1).Value = rowKey
    ws.Cells(lastRow + 1, 2).Value = colStart
    ws.Cells(lastRow + 1, 3).Value = colEnd
    ws.Cells(lastRow + 1, 4).Value = Format$(Now, "m/d/yyyy h:mm AM/PM")
    ws.Cells(lastRow + 1, 5).Value = token
    ws.Visible = xlSheetVeryHidden
End Sub

'------------------------------------------------------------------------------
' Procedure: PersistManualEditMarkersForRow
' Scope: Private Sub
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   PersistManualEditMarkersForRow.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub PersistManualEditMarkersForRow(ByVal ws As Worksheet, ByVal rowNum As Long)
    Dim stateKey As String

    stateKey = GetManualEditStateKeyForRow(ws, rowNum)
    If Len(stateKey) = 0 Then Exit Sub

    'Persist the whole A:M band for the edited row occurrence
    SaveManualEditRecord stateKey, 1, 10
End Sub

'------------------------------------------------------------------------------
' Procedure: BuildRowKeyMapForSheet
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   BuildRowKeyMapForSheet.
'
' Why it exists:
'   Rows may represent real orders, section headers, remakes, Greenville work,
'   Customer Pickup work, or updated rows; each type needs different handling.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BuildRowKeyMapForSheet(ByVal ws As Worksheet) As Object
    Dim dict As Object
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim orderCol As Long
    Dim itemCol As Long
    Dim firstDataRow As Long
    Dim lastRow As Long
    Dim r As Long
    Dim currentSectionKey As String
    Dim rowKey As String

    Set dict = CreateObject("Scripting.Dictionary")

    Set orderHdr = FindHeaderCellLocal(ws, Array(HDR_ORDER))
    Set itemHdr = FindHeaderCellLocal(ws, Array(HDR_ITEM, "Item"))
    If orderHdr Is Nothing Or itemHdr Is Nothing Then
        Set BuildRowKeyMapForSheet = dict
        Exit Function
    End If

    orderCol = orderHdr.Column
    itemCol = itemHdr.Column
    firstDataRow = orderHdr.Row + 1
    lastRow = ws.Cells(ws.rows.Count, orderCol).End(xlUp).Row
    currentSectionKey = "__UNSECTIONED__"

    For r = firstDataRow To lastRow
        If IsSectionHeaderRowLocal(ws, r, orderCol, itemCol) Then
            currentSectionKey = NormalizeSectionKeyLocal(CStr(ws.Cells(r, 1).Value))
            If Len(currentSectionKey) = 0 Then currentSectionKey = "__UNSECTIONED__"

        ElseIf IsRealDeliveryLineLocal(ws, r, orderCol, itemCol) Then
            rowKey = BuildDeliveryLineKeyLocal(ws, r, currentSectionKey, orderCol, itemCol)
            If Len(rowKey) > 0 Then
                If Not dict.Exists(rowKey) Then dict.Add rowKey, r
            End If
        End If
    Next r

    Set BuildRowKeyMapForSheet = dict
End Function

'------------------------------------------------------------------------------
' Procedure: BuildRowStateKeyMapForSheet
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   BuildRowStateKeyMapForSheet.
'
' Why it exists:
'   Rows may represent real orders, section headers, remakes, Greenville work,
'   Customer Pickup work, or updated rows; each type needs different handling.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BuildRowStateKeyMapForSheet(ByVal ws As Worksheet) As Object
    Dim dict As Object
    Dim counts As Object
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim orderCol As Long
    Dim itemCol As Long
    Dim firstDataRow As Long
    Dim lastRow As Long
    Dim r As Long
    Dim currentSectionKey As String
    Dim rowKey As String
    Dim stateKey As String
    Dim occ As Long

    Set dict = CreateObject("Scripting.Dictionary")
    Set counts = CreateObject("Scripting.Dictionary")

    Set orderHdr = FindHeaderCellLocal(ws, Array(HDR_ORDER))
    Set itemHdr = FindHeaderCellLocal(ws, Array(HDR_ITEM, "Item"))
    If orderHdr Is Nothing Or itemHdr Is Nothing Then
        Set BuildRowStateKeyMapForSheet = dict
        Exit Function
    End If

    orderCol = orderHdr.Column
    itemCol = itemHdr.Column
    firstDataRow = orderHdr.Row + 1
    lastRow = ws.Cells(ws.rows.Count, orderCol).End(xlUp).Row
    currentSectionKey = "__UNSECTIONED__"

    For r = firstDataRow To lastRow
        If IsSectionHeaderRowLocal(ws, r, orderCol, itemCol) Then
            currentSectionKey = NormalizeSectionKeyLocal(CStr(ws.Cells(r, 1).Value))
            If Len(currentSectionKey) = 0 Then currentSectionKey = "__UNSECTIONED__"

        ElseIf IsRealDeliveryLineLocal(ws, r, orderCol, itemCol) Then
            rowKey = BuildDeliveryLineKeyLocal(ws, r, currentSectionKey, orderCol, itemCol)

            If Len(rowKey) > 0 Then
                If counts.Exists(rowKey) Then
                    occ = CLng(counts(rowKey)) + 1
                    counts(rowKey) = occ
                Else
                    occ = 1
                    counts.Add rowKey, occ
                End If

                stateKey = BuildManualEditStartStateKey(rowKey, occ)
                dict(stateKey) = r
            End If
        End If
    Next r

    Set BuildRowStateKeyMapForSheet = dict
End Function

'------------------------------------------------------------------------------
' Procedure: ReapplyManualEditMarksForSheet
' Scope: Private Sub
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   ReapplyManualEditMarksForSheet.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ReapplyManualEditMarksForSheet(ByVal ws As Worksheet)
    Dim stateWs As Worksheet
    Dim keyMap As Object
    Dim lastRow As Long
    Dim r As Long
    Dim stateKey As String
    Dim rowNum As Long
    Dim colStart As Long
    Dim colEnd As Long
    Dim rng As Range

    If ws Is Nothing Then Exit Sub

    On Error Resume Next
    Set stateWs = ThisWorkbook.Worksheets(MANUAL_EDIT_STATE_SHEET)
    On Error GoTo 0
    If stateWs Is Nothing Then Exit Sub

    Set keyMap = BuildRowStateKeyMapForSheet(ws)

    lastRow = stateWs.Cells(stateWs.rows.Count, 1).End(xlUp).Row
    If lastRow < 2 Then Exit Sub

    For r = 2 To lastRow
        stateKey = CStr(stateWs.Cells(r, 1).Value)

        If keyMap.Exists(stateKey) Then
            rowNum = CLng(keyMap(stateKey))
            colStart = CLng(Val(stateWs.Cells(r, 2).Value))
            colEnd = CLng(Val(stateWs.Cells(r, 3).Value))

            If colStart > 0 And colEnd >= colStart Then
                Set rng = ws.Range(ws.Cells(rowNum, colStart), ws.Cells(rowNum, colEnd))
                ApplyManualEditOutline rng
            End If
        End If
    Next r
End Sub

'------------------------------------------------------------------------------
' Procedure: ReapplyAllManualEditMarks
' Scope: Private Sub
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   ReapplyAllManualEditMarks.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ReapplyAllManualEditMarks()
    Dim ws As Worksheet

    ReapplyManualEditMarksForSheet ThisWorkbook.Worksheets(DATA_SHEET_NAME)

    Set ws = GetSheetIfExists(STAGING_SHEET_NAME)
    If Not ws Is Nothing Then ReapplyManualEditMarksForSheet ws

    Set ws = GetSheetIfExists(SEND_SHEET_NAME)
    If Not ws Is Nothing Then ReapplyManualEditMarksForSheet ws

    Set ws = CurrentRecvSheet()
    If Not ws Is Nothing Then ReapplyManualEditMarksForSheet ws

    Set ws = GetSheetIfExists(GREENVILLE_RECV_SHEET_NAME)
    If Not ws Is Nothing Then ReapplyManualEditMarksForSheet ws

    Set ws = GetSheetIfExists("Customer Pickup")
    If Not ws Is Nothing Then ReapplyManualEditMarksForSheet ws
End Sub

'------------------------------------------------------------------------------
' Procedure: ClearStoredHighlightOnSheetForRow
' Scope: Private Sub
'
' What it does:
'   Applies, stores, restores, or clears scan/manual highlight state for
'   ClearStoredHighlightOnSheetForRow.
'
' Why it exists:
'   Highlights help the operator find the affected row after scanning or
'   editing, but stale highlights must be cleared so they do not mislead
'   anyone.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ClearStoredHighlightOnSheetForRow(ByVal ws As Worksheet, ByVal rowNum As Long)
    If ws Is Nothing Then Exit Sub

    If GetStoredHighlightRow(ws) = rowNum Then
        SaveStoredHighlightRow ws, 0
    End If

    If rowNum > 0 Then
        With ws.Range(ws.Cells(rowNum, 1), ws.Cells(rowNum, SCAN_HIGHLIGHT_LAST_COL))
            If .Cells(1, 1).Interior.Color = RGB(255, 255, 153) Then
                .Interior.Pattern = xlNone
            End If
        End With
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: ClearStoredHighlightEverywhereForRow
' Scope: Private Sub
'
' What it does:
'   Applies, stores, restores, or clears scan/manual highlight state for
'   ClearStoredHighlightEverywhereForRow.
'
' Why it exists:
'   Highlights help the operator find the affected row after scanning or
'   editing, but stale highlights must be cleared so they do not mislead
'   anyone.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ClearStoredHighlightEverywhereForRow(ByVal rowNum As Long)
    Dim ws As Worksheet

    ClearStoredHighlightOnSheetForRow ThisWorkbook.Worksheets(DATA_SHEET_NAME), rowNum

    Set ws = GetSheetIfExists(STAGING_SHEET_NAME)
    If Not ws Is Nothing Then ClearStoredHighlightOnSheetForRow ws, rowNum

    Set ws = GetSheetIfExists(SEND_SHEET_NAME)
    If Not ws Is Nothing Then ClearStoredHighlightOnSheetForRow ws, rowNum

    Set ws = CurrentRecvSheet()
    If Not ws Is Nothing Then ClearStoredHighlightOnSheetForRow ws, rowNum

    Set ws = GetSheetIfExists(GREENVILLE_RECV_SHEET_NAME)
    If Not ws Is Nothing Then ClearStoredHighlightOnSheetForRow ws, rowNum

    Set ws = GetSheetIfExists(CPU_SHEET_NAME)
    If Not ws Is Nothing Then ClearStoredHighlightOnSheetForRow ws, rowNum
End Sub

'------------------------------------------------------------------------------
' Procedure: ResetCurrentManualEditHighlights
' Scope: Private Sub
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   ResetCurrentManualEditHighlights.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ResetCurrentManualEditHighlights()
    Dim ws As Worksheet

    ClearManualEditStateSheetRecords

    ClearManualEditMarksForSheet ThisWorkbook.Worksheets(DATA_SHEET_NAME)

    Set ws = GetSheetIfExists(STAGING_SHEET_NAME)
    If Not ws Is Nothing Then ClearManualEditMarksForSheet ws

    Set ws = GetSheetIfExists(SEND_SHEET_NAME)
    If Not ws Is Nothing Then ClearManualEditMarksForSheet ws

    Set ws = CurrentRecvSheet()
    If Not ws Is Nothing Then ClearManualEditMarksForSheet ws

    Set ws = GetSheetIfExists(GREENVILLE_RECV_SHEET_NAME)
    If Not ws Is Nothing Then ClearManualEditMarksForSheet ws

    Set ws = GetSheetIfExists(CPU_SHEET_NAME)
    If Not ws Is Nothing Then ClearManualEditMarksForSheet ws
End Sub

'------------------------------------------------------------------------------
' Procedure: HandleDeliveryListEditExit
' Scope: Private Function
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   HandleDeliveryListEditExit.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function HandleDeliveryListEditExit(ByVal targetSheetName As String) As Boolean
    Dim dataWs As Worksheet
    Dim resp As VbMsgBoxResult

    Set dataWs = ThisWorkbook.Worksheets(DATA_SHEET_NAME)

    If Not IsDeliveryEditModeOn() Then
        HandleDeliveryListEditExit = True
        Exit Function
    End If

    If mHandlingEditExit Then
        HandleDeliveryListEditExit = True
        Exit Function
    End If

    mHandlingEditExit = True
    On Error GoTo FailExit

    If mManualEditsPending Then
        resp = MsgBox( _
            "You have finished making manual edits?" & vbCrLf & vbCrLf & _
            "Click Yes to finish editing and update the Delivery List and all scanner sheets now." & vbCrLf & _
            "Click No to keep editing on the Delivery List.", _
            vbYesNo + vbQuestion + vbDefaultButton1, _
            "Finish Delivery List Editing")

        If resp = vbYes Then
            FinishDeliveryListEditing targetSheetName
            HandleDeliveryListEditExit = True
        Else
            Application.EnableEvents = False
            dataWs.Activate
            Application.EnableEvents = True
            HandleDeliveryListEditExit = False
        End If
    Else
        DisableDeliveryListEditMode dataWs
        HandleDeliveryListEditExit = True
    End If

CleanExit:
    mHandlingEditExit = False
    Exit Function

FailExit:
    Application.EnableEvents = True
    MsgBox "Could not exit Delivery List edit mode." & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbExclamation, "Edit Mode"
    HandleDeliveryListEditExit = False
    Resume CleanExit
End Function

'------------------------------------------------------------------------------
' Procedure: MarkDeliveryListEdit
' Scope: Private Sub
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   MarkDeliveryListEdit.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub MarkDeliveryListEdit(ByVal target As Range)
    Dim ws As Worksheet
    Dim rng As Range
    Dim rw As Range
    Dim rowBand As Range
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim firstDataRow As Long
    Dim orderCol As Long
    Dim itemCol As Long
    Dim rowKey As String
    Dim stateKey As String
    Dim currentSig As String
    Dim startSig As String
    Dim occurrenceIndex As Long
    Dim shouldMark As Boolean
    Dim seen As Object

    Set ws = target.Worksheet
    Set rng = Intersect(target, ws.Range("A:J"))
    If rng Is Nothing Then Exit Sub

    Set orderHdr = FindHeaderCellLocal(ws, Array(HDR_ORDER))
    Set itemHdr = FindHeaderCellLocal(ws, Array(HDR_ITEM, "Item"))
    If orderHdr Is Nothing Or itemHdr Is Nothing Then Exit Sub

    orderCol = orderHdr.Column
    itemCol = itemHdr.Column
    firstDataRow = orderHdr.Row + 1

    Set seen = CreateObject("Scripting.Dictionary")

    For Each rw In rng.rows
        If seen.Exists(CStr(rw.Row)) Then GoTo nextRow
        seen.Add CStr(rw.Row), True

        Set rowBand = GetManualEditBandForRow(ws, rw.Row)
        If rowBand Is Nothing Then GoTo SnapshotAndNext

        If rw.Row < firstDataRow Then GoTo SnapshotAndNext

        If IsSectionHeaderRowLocal(ws, rw.Row, orderCol, itemCol) Then
            ClearManualEditMark rowBand
            GoTo SnapshotAndNext
        End If

        If Not IsRealDeliveryLineLocal(ws, rw.Row, orderCol, itemCol) Then
            ClearManualEditMark rowBand
            GoTo SnapshotAndNext
        End If

        rowKey = GetRowKeyForManualEdit(ws, rw.Row)
        If Len(rowKey) = 0 Then
            ClearManualEditMark rowBand
            GoTo SnapshotAndNext
        End If

        occurrenceIndex = GetRowOccurrenceIndexForManualEdit(ws, rw.Row, firstDataRow, orderCol, itemCol, rowKey)
        stateKey = BuildManualEditStartStateKey(rowKey, occurrenceIndex)
        currentSig = GetRowSnapshotValue(ws, rw.Row)

        shouldMark = True

        If Not mEditStartRowState Is Nothing Then
            If mEditStartRowState.Exists(stateKey) Then
                startSig = CStr(mEditStartRowState(stateKey))
                shouldMark = (StrComp(startSig, currentSig, vbBinaryCompare) <> 0)
            End If
        End If

        If shouldMark Then
            ClearStoredHighlightEverywhereForRow rw.Row
            ApplyManualEditMark rowBand
        Else
            ClearManualEditMark rowBand
        End If

SnapshotAndNext:
        CaptureEditSnapshotForRow ws, rw.Row

nextRow:
    Next rw

    RebuildManualEditStateFromDeliveryList
    RegisterManualChange
End Sub

'------------------------------------------------------------------------------
' Procedure: RefreshAllScannerSheetsAfterEdit
' Scope: Private Sub
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   RefreshAllScannerSheetsAfterEdit.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub RefreshAllScannerSheetsAfterEdit(ByVal dataWs As Worksheet)
    Dim ws As Worksheet

    'Do NOT restyle the master Delivery List here.
    'That wipes the preserved purple updated-row formatting.
    RefreshScannerSheet dataWs, ThisWorkbook.Worksheets(STAGING_SHEET_NAME), "STAGING"
    RefreshScannerSheet dataWs, ThisWorkbook.Worksheets(SEND_SHEET_NAME), "SEND"

    Set ws = CurrentRecvSheet()
    If Not ws Is Nothing Then RefreshScannerSheet dataWs, ws, "RECV"

    Set ws = GetSheetIfExists(GREENVILLE_RECV_SHEET_NAME)
    If Not ws Is Nothing Then RefreshScannerSheet dataWs, ws, "RECV"

    Set ws = GetSheetIfExists("Customer Pickup")
    If Not ws Is Nothing Then RefreshScannerSheet dataWs, ws, "RECV"

    'Reapply persistent manual-edit outlines after scanner sheets refresh
    ReapplyAllManualEditMarks
End Sub

'------------------------------------------------------------------------------
' Procedure: FinishDeliveryListEditing
' Scope: Public Sub
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   FinishDeliveryListEditing.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub FinishDeliveryListEditing(Optional ByVal activateSheetName As String = "")
    Dim dataWs As Worksheet
    Dim targetWs As Worksheet
    Dim oldEvents As Boolean
    Dim oldScreen As Boolean
    Dim oldAlerts As Boolean
    Dim finishedCleanly As Boolean

    On Error GoTo ErrHandler

    Set dataWs = ThisWorkbook.Worksheets(DATA_SHEET_NAME)

    If Len(activateSheetName) > 0 Then
        Set targetWs = GetSheetIfExists(activateSheetName)
    End If

    oldEvents = Application.EnableEvents
    oldScreen = Application.ScreenUpdating
    oldAlerts = Application.DisplayAlerts

    Application.EnableEvents = False
    Application.ScreenUpdating = False
    Application.DisplayAlerts = False

    On Error Resume Next
    dataWs.Unprotect Password:=""
    On Error GoTo ErrHandler

    RefreshAllScannerSheetsAfterEdit dataWs
    ReboldDeliveryListHeaders dataWs
    HideStagingOnDeliveryList dataWs
    SetDeliverySummaryVisibility dataWs, True
    ProtectViewOnlySheet dataWs

    DisableDeliveryListEditMode dataWs
    mManualEditsPending = False
    Set mEditStartKeys = Nothing
    Set mEditStartRowState = Nothing

    If Not targetWs Is Nothing Then
        targetWs.Activate
    Else
        dataWs.Activate
    End If

    finishedCleanly = True

SafeExit:
    Application.DisplayAlerts = oldAlerts
    Application.ScreenUpdating = oldScreen
    Application.EnableEvents = oldEvents

    'Manual edits should leave queue paused until the user manually resumes.
    'This also refreshes the Utility Panel button so it shows QUEUE PAUSED red.
    On Error Resume Next
    ForceExternalQueuePausedForManualEdit "Delivery List manual edits complete - awaiting manual resume"
    On Error GoTo 0

    If finishedCleanly Then
        Application.StatusBar = "Manual edits finished. Queue is still paused. Click QUEUE PAUSED to resume scan processing."
    End If

    Exit Sub

ErrHandler:
    Application.DisplayAlerts = oldAlerts
    Application.ScreenUpdating = oldScreen
    Application.EnableEvents = oldEvents

    On Error Resume Next
    ForceExternalQueuePausedForManualEdit "Delivery List manual edit error - queue left paused"
    On Error GoTo 0

    MsgBox "FinishDeliveryListEditing error " & Err.Number & ":" & vbCrLf & Err.Description, _
           vbCritical, "Edit Mode Error"
End Sub

'------------------------------------------------------------------------------
' Procedure: CPUSheetExists
' Scope: Private Function
'
' What it does:
'   Identifies, filters, formats, or routes Customer Pickup rows for
'   CPUSheetExists.
'
' Why it exists:
'   Customer Pickup orders follow a separate operational path, so they cannot
'   be mixed into normal inbound/Greenville handling by accident.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function CPUSheetExists() As Boolean
    Dim ws As Worksheet

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(CPU_SHEET_NAME)
    On Error GoTo 0

    CPUSheetExists = Not ws Is Nothing
End Function

'------------------------------------------------------------------------------
' Procedure: GetRouteColumn
' Scope: Private Function
'
' What it does:
'   Finds, sizes, hides, formats, or uses worksheet columns for
'   GetRouteColumn.
'
' Why it exists:
'   The system depends on fixed scan blocks and discovered delivery-list
'   columns, so column handling must be centralized and predictable.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetRouteColumn(ByVal ws As Worksheet) As Long
    GetRouteColumn = ROUTE_COL_FIXED
End Function

'------------------------------------------------------------------------------
' Procedure: IsCPURow
' Scope: Private Function
'
' What it does:
'   Identifies, filters, formats, or routes Customer Pickup rows for IsCPURow.
'
' Why it exists:
'   Customer Pickup orders follow a separate operational path, so they cannot
'   be mixed into normal inbound/Greenville handling by accident.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function IsCPURow(ByVal ws As Worksheet, ByVal rowNum As Long, Optional ByVal routeCol As Long = 0) As Boolean
    Dim routeText As String

    If routeCol = 0 Then routeCol = GetRouteColumn(ws)
    If routeCol = 0 Then Exit Function
    If rowNum < FIRST_DATA_ROW_FIXED Then Exit Function

    routeText = CStr(ws.Cells(rowNum, routeCol).Value)
    routeText = Replace$(routeText, Chr$(160), " ")

    On Error Resume Next
    routeText = Application.WorksheetFunction.Clean(routeText)
    routeText = Application.WorksheetFunction.Trim(routeText)
    On Error GoTo 0

    routeText = UCase$(Trim$(routeText))

    IsCPURow = (routeText = UCase$(CPU_ROUTE_TEXT))
End Function

'------------------------------------------------------------------------------
' Procedure: HasCPUOrders
' Scope: Private Function
'
' What it does:
'   Identifies, filters, formats, or routes Customer Pickup rows for
'   HasCPUOrders.
'
' Why it exists:
'   Customer Pickup orders follow a separate operational path, so they cannot
'   be mixed into normal inbound/Greenville handling by accident.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function HasCPUOrders(ByVal ws As Worksheet) As Boolean
    Dim lastRow As Long
    Dim r As Long

    lastRow = ws.Cells(ws.rows.Count, ROUTE_COL_FIXED).End(xlUp).Row
    If lastRow < FIRST_DATA_ROW_FIXED Then Exit Function

    For r = FIRST_DATA_ROW_FIXED To lastRow
        If IsCPURow(ws, r) Then
            HasCPUOrders = True
            Exit Function
        End If
    Next r
End Function

'------------------------------------------------------------------------------
' Procedure: RefreshAllOperationalSheets
' Scope: Public Sub
'
' What it does:
'   Finds, creates, deletes, rebuilds, protects, or synchronizes worksheets
'   for RefreshAllOperationalSheets.
'
' Why it exists:
'   The master workbook creates multiple operational views from one delivery
'   list; worksheet helpers keep those views from drifting apart.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub RefreshAllOperationalSheets(ByVal dataWs As Worksheet)
    EnsureScannerSheetsExist dataWs

    RefreshScannerSheet dataWs, ThisWorkbook.Worksheets(STAGING_SHEET_NAME), "STAGING"
    RefreshScannerSheet dataWs, ThisWorkbook.Worksheets(SEND_SHEET_NAME), "SEND"
    RefreshScannerSheet dataWs, CurrentRecvSheet(), "RECV"

    If HasGreenvilleOrders(dataWs) And GreenvilleSheetExists() Then
        RefreshScannerSheet dataWs, ThisWorkbook.Worksheets(GREENVILLE_RECV_SHEET_NAME), "RECV"
    ElseIf GreenvilleSheetExists() Then
        On Error Resume Next
        Application.DisplayAlerts = False
        ThisWorkbook.Worksheets(GREENVILLE_RECV_SHEET_NAME).Delete
        Application.DisplayAlerts = True
        On Error GoTo 0
    End If

    If HasCPUOrders(dataWs) And CPUSheetExists() Then
        RefreshScannerSheet dataWs, ThisWorkbook.Worksheets(CPU_SHEET_NAME), "RECV"
    ElseIf CPUSheetExists() Then
        On Error Resume Next
        Application.DisplayAlerts = False
        ThisWorkbook.Worksheets(CPU_SHEET_NAME).Delete
        Application.DisplayAlerts = True
        On Error GoTo 0
    End If
    'Final receive-sheet summary correction after all refresh work is done
    FinalizeReceiveLocationSummaries
End Sub

'------------------------------------------------------------------------------
' Procedure: CurrentRecvSheetName
' Scope: Private Function
'
' What it does:
'   Finds, creates, deletes, rebuilds, protects, or synchronizes worksheets
'   for CurrentRecvSheetName.
'
' Why it exists:
'   The master workbook creates multiple operational views from one delivery
'   list; worksheet helpers keep those views from drifting apart.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function CurrentRecvSheetName() As String
    CurrentRecvSheetName = GetReceiveSheetName()
End Function

'------------------------------------------------------------------------------
' Procedure: CurrentRecvSheet
' Scope: Private Function
'
' What it does:
'   Finds, creates, deletes, rebuilds, protects, or synchronizes worksheets
'   for CurrentRecvSheet.
'
' Why it exists:
'   The master workbook creates multiple operational views from one delivery
'   list; worksheet helpers keep those views from drifting apart.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function CurrentRecvSheet() As Worksheet
    Set CurrentRecvSheet = GetReceiveSheet()
End Function

'------------------------------------------------------------------------------
' Procedure: HasSeparateGreenvilleInbound
' Scope: Private Function
'
' What it does:
'   Identifies, filters, formats, or routes Greenville-specific delivery rows
'   for HasSeparateGreenvilleInbound.
'
' Why it exists:
'   Greenville orders are separated from standard Indian Trail inbound work,
'   so those rows need consistent classification across sheets, print/export,
'   and snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function HasSeparateGreenvilleInbound() As Boolean
    HasSeparateGreenvilleInbound = (UCase$(CurrentRecvSheetName()) <> UCase$(GREENVILLE_RECV_SHEET_NAME))
End Function

'------------------------------------------------------------------------------
' Procedure: IsReceiveSheetName
' Scope: Private Function
'
' What it does:
'   Finds, creates, deletes, rebuilds, protects, or synchronizes worksheets
'   for IsReceiveSheetName.
'
' Why it exists:
'   The master workbook creates multiple operational views from one delivery
'   list; worksheet helpers keep those views from drifting apart.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function IsReceiveSheetName(ByVal sheetName As String) As Boolean
    IsReceiveSheetName = (UCase$(sheetName) = UCase$(CurrentRecvSheetName()) Or _
                          UCase$(sheetName) = UCase$(GREENVILLE_RECV_SHEET_NAME) Or _
                          UCase$(sheetName) = UCase$(CPU_SHEET_NAME))
End Function

'------------------------------------------------------------------------------
' Procedure: GetCustomerColumn
' Scope: Private Function
'
' What it does:
'   Finds, sizes, hides, formats, or uses worksheet columns for
'   GetCustomerColumn.
'
' Why it exists:
'   The system depends on fixed scan blocks and discovered delivery-list
'   columns, so column handling must be centralized and predictable.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetCustomerColumn(ByVal ws As Worksheet) As Long
    Dim custHdr As Range
    Set custHdr = FindHeaderCellInCols(ws, Array("Customer"), "A:N", 250)
    If Not custHdr Is Nothing Then GetCustomerColumn = custHdr.Column
End Function

'------------------------------------------------------------------------------
' Procedure: IsGreenvilleRow
' Scope: Private Function
'
' What it does:
'   Identifies, filters, formats, or routes Greenville-specific delivery rows
'   for IsGreenvilleRow.
'
' Why it exists:
'   Greenville orders are separated from standard Indian Trail inbound work,
'   so those rows need consistent classification across sheets, print/export,
'   and snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function IsGreenvilleRow(ByVal ws As Worksheet, ByVal rowNum As Long, Optional ByVal customerCol As Long = 0) As Boolean
    Dim customerText As String

    If customerCol = 0 Then customerCol = GetCustomerColumn(ws)
    If customerCol = 0 Then Exit Function
    If rowNum < FIRST_DATA_ROW_FIXED Then Exit Function

    customerText = CStr(ws.Cells(rowNum, customerCol).Value)
    customerText = Replace$(customerText, Chr$(160), " ")

    On Error Resume Next
    customerText = Application.WorksheetFunction.Clean(customerText)
    customerText = Application.WorksheetFunction.Trim(customerText)
    On Error GoTo 0

    customerText = UCase$(Trim$(customerText))

    IsGreenvilleRow = (customerText = UCase$(GREENVILLE_CUSTOMER_TEXT))
End Function

'------------------------------------------------------------------------------
' Procedure: HasGreenvilleOrders
' Scope: Private Function
'
' What it does:
'   Identifies, filters, formats, or routes Greenville-specific delivery rows
'   for HasGreenvilleOrders.
'
' Why it exists:
'   Greenville orders are separated from standard Indian Trail inbound work,
'   so those rows need consistent classification across sheets, print/export,
'   and snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function HasGreenvilleOrders(ByVal ws As Worksheet) As Boolean
    Dim custCol As Long
    Dim orderHdr As Range
    Dim firstRow As Long, lastRow As Long
    Dim r As Long

    custCol = GetCustomerColumn(ws)
    Set orderHdr = FindHeaderCellInCols(ws, Array(HDR_ORDER), "A:N", 250)

    If custCol = 0 Or orderHdr Is Nothing Then Exit Function

    firstRow = orderHdr.Row + 1
    lastRow = ws.Cells(ws.rows.Count, orderHdr.Column).End(xlUp).Row

    For r = firstRow To lastRow
        If IsGreenvilleRow(ws, r, custCol) Then
            HasGreenvilleOrders = True
            Exit Function
        End If
    Next r
End Function

'------------------------------------------------------------------------------
' Procedure: GreenvilleSheetExists
' Scope: Private Function
'
' What it does:
'   Identifies, filters, formats, or routes Greenville-specific delivery rows
'   for GreenvilleSheetExists.
'
' Why it exists:
'   Greenville orders are separated from standard Indian Trail inbound work,
'   so those rows need consistent classification across sheets, print/export,
'   and snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GreenvilleSheetExists() As Boolean
    Dim ws As Worksheet

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(GREENVILLE_RECV_SHEET_NAME)
    On Error GoTo 0

    GreenvilleSheetExists = Not ws Is Nothing
End Function

'------------------------------------------------------------------------------
' Procedure: HasDeliverySummaryTable
' Scope: Private Function
'
' What it does:
'   Calculates or updates summary/banner information shown at the top of
'   delivery/scanner sheets for HasDeliverySummaryTable.
'
' Why it exists:
'   Operators use those summary panels to quickly see staged, outbound,
'   inbound, and completion progress without manually counting rows.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function HasDeliverySummaryTable(ByVal ws As Worksheet) As Boolean
    Dim lo As ListObject
    Dim nm As String

    For Each lo In ws.ListObjects
        nm = UCase$(lo.Name & " " & lo.displayName)
        If InStr(1, nm, "DELIVERYSUMMARY", vbTextCompare) > 0 Then
            HasDeliverySummaryTable = True
            Exit Function
        End If
    Next lo
End Function

'------------------------------------------------------------------------------
' Procedure: HasUpdatedRowPurpleBorder
' Scope: Private Function
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   HasUpdatedRowPurpleBorder.
'
' Why it exists:
'   Delivery timing, queue timestamps, and scan timestamps drive status
'   messages such as Early, On-Time, Late, Processing, and Done.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function HasUpdatedRowPurpleBorder(ByVal rng As Range) As Boolean
    If rng Is Nothing Then Exit Function

    On Error Resume Next

    'IMPORTANT:
    'Only treat a row as an "updated purple row" when the row-band itself
    'has BOTH the left and right purple outer borders.
    '
    'Why:
    'The row above a true updated row can inherit a shared top/bottom edge
    'from Excel's border rendering. If we look for ANY purple edge, the
    'purple border "walks" upward one row at a time after each scan.
    '
    'Using left + right outer borders avoids that false match.
    HasUpdatedRowPurpleBorder = _
        (rng.Borders(xlEdgeLeft).LineStyle <> xlNone And rng.Borders(xlEdgeLeft).Color = RGB(112, 48, 160)) And _
        (rng.Borders(xlEdgeRight).LineStyle <> xlNone And rng.Borders(xlEdgeRight).Color = RGB(112, 48, 160))

    On Error GoTo 0
End Function

'------------------------------------------------------------------------------
' Procedure: ReapplyUpdatedRowStyle
' Scope: Private Sub
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   ReapplyUpdatedRowStyle.
'
' Why it exists:
'   Delivery timing, queue timestamps, and scan timestamps drive status
'   messages such as Early, On-Time, Late, Processing, and Done.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ReapplyUpdatedRowStyle(ByVal ws As Worksheet, ByVal rowNum As Long, ByVal isGreenville As Boolean)
    Dim bandAJ As Range

    Set bandAJ = ws.Range("A" & rowNum & ":J" & rowNum)

    With bandAJ
        If isGreenville Then
            .Interior.Color = RGB(221, 235, 247)
            .Font.Color = RGB(31, 78, 121)
        Else
            .Interior.Color = RGB(221, 217, 238)
            .Font.Color = RGB(64, 0, 96)
        End If

        .Font.Bold = True
    End With

    ReapplyUpdatedRowPurpleBorder bandAJ
End Sub

'------------------------------------------------------------------------------
' Procedure: ReapplyUpdatedRowPurpleBorder
' Scope: Private Sub
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   ReapplyUpdatedRowPurpleBorder.
'
' Why it exists:
'   Delivery timing, queue timestamps, and scan timestamps drive status
'   messages such as Early, On-Time, Late, Processing, and Done.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ReapplyUpdatedRowPurpleBorder(ByVal rng As Range)
    If rng Is Nothing Then Exit Sub

    With rng.Borders(xlEdgeLeft)
        .LineStyle = xlContinuous
        .Weight = xlThin
        .Color = RGB(112, 48, 160)
    End With
    With rng.Borders(xlEdgeTop)
        .LineStyle = xlContinuous
        .Weight = xlThin
        .Color = RGB(112, 48, 160)
    End With
    With rng.Borders(xlEdgeBottom)
        .LineStyle = xlContinuous
        .Weight = xlThin
        .Color = RGB(112, 48, 160)
    End With
    With rng.Borders(xlEdgeRight)
        .LineStyle = xlContinuous
        .Weight = xlThin
        .Color = RGB(112, 48, 160)
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: HighlightGreenvilleRows
' Scope: Private Sub
'
' What it does:
'   Applies, stores, restores, or clears scan/manual highlight state for
'   HighlightGreenvilleRows.
'
' Why it exists:
'   Highlights help the operator find the affected row after scanning or
'   editing, but stale highlights must be cleared so they do not mislead
'   anyone.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub HighlightGreenvilleRows(ByVal ws As Worksheet)
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim firstRow As Long
    Dim lastRow As Long
    Dim r As Long
    Dim orderCol As Long
    Dim itemCol As Long
    Dim bandAJ As Range
    Dim routeCell As Range
    Dim rmCell As Range
    Dim isCPU As Boolean
    Dim isGreenville As Boolean
    Dim isRemake As Boolean
    Dim hasProgressFill As Boolean
    Dim hasUpdatedBorder As Boolean

    Set orderHdr = FindHeaderCellInCols(ws, Array(HDR_ORDER), "A:N", 250)
    Set itemHdr = FindHeaderCellInCols(ws, Array(HDR_ITEM), "A:N", 250)

    If orderHdr Is Nothing Or itemHdr Is Nothing Then Exit Sub

    orderCol = orderHdr.Column
    itemCol = itemHdr.Column
    firstRow = orderHdr.Row + 1
    lastRow = ws.Cells(ws.rows.Count, orderHdr.Column).End(xlUp).Row

    For r = firstRow To lastRow
        If IsSectionHeaderRowLocal(ws, r, orderCol, itemCol) Then GoTo nextRow
        If Not IsRealDeliveryLineLocal(ws, r, orderCol, itemCol) Then GoTo nextRow

        Set bandAJ = ws.Range("A" & r & ":J" & r)
        Set routeCell = ws.Cells(r, ROUTE_COL_FIXED)
        Set rmCell = ws.Cells(r, REMAKE_MARKER_COL_FIXED)

        isCPU = IsCPURow(ws, r)
        isGreenville = IsGreenvilleRow(ws, r)
        isRemake = (UCase$(Trim$(CStr(rmCell.Value))) = "RM")
        hasProgressFill = HasDeliveryProgressFill(bandAJ)
        hasUpdatedBorder = HasUpdatedRowPurpleBorder(bandAJ)

        'Only clear A:J when this is NOT one of the update-marked rows
        If Not hasUpdatedBorder Then
            With bandAJ
                .Interior.Pattern = xlNone
                .Font.ColorIndex = xlAutomatic
                .Font.Bold = False
                .Borders.LineStyle = xlNone
            End With
        End If

        'L = CPU cell gets rebuilt fresh each pass
        With routeCell
            .Interior.Pattern = xlNone
            .Font.ColorIndex = xlAutomatic
            .Font.Bold = False
            .Borders.LineStyle = xlNone
        End With

        'K = RM cell gets rebuilt fresh each pass
        With rmCell
            .Interior.Pattern = xlNone
            .Font.ColorIndex = xlAutomatic
            .Font.Bold = False
            .Borders.LineStyle = xlNone
        End With

        'If this row was marked as a newly added update row,
        'keep its purple border even after scans/process refreshes.
        If hasUpdatedBorder Then
    ReapplyUpdatedRowStyle ws, r, isGreenville

ElseIf Not hasProgressFill Then
    If isGreenville Then
        With bandAJ
            .Interior.Color = RGB(221, 235, 247)
            .Font.Color = RGB(31, 78, 121)
            .Font.Bold = True
        End With
    End If
End If

        'K = RM only
        If isRemake Then
            With rmCell
                .Value = "RM"
                .HorizontalAlignment = xlCenter
                .VerticalAlignment = xlCenter
                .Font.Bold = True
                .Font.Color = RGB(255, 255, 255)
                .Interior.Color = RGB(192, 0, 0)

                With .Borders(xlEdgeLeft)
                    .LineStyle = xlContinuous
                    .Weight = xlThin
                    .Color = RGB(128, 0, 0)
                End With
                With .Borders(xlEdgeTop)
                    .LineStyle = xlContinuous
                    .Weight = xlThin
                    .Color = RGB(128, 0, 0)
                End With
                With .Borders(xlEdgeBottom)
                    .LineStyle = xlContinuous
                    .Weight = xlThin
                    .Color = RGB(128, 0, 0)
                End With
                With .Borders(xlEdgeRight)
                    .LineStyle = xlContinuous
                    .Weight = xlThin
                    .Color = RGB(128, 0, 0)
                End With
            End With
        End If

        'L = CPU only
        If isCPU Then
            With routeCell
                .Interior.Color = RGB(248, 214, 170)
                .Font.Color = RGB(125, 68, 28)
                .Font.Bold = True
                With .Borders
                    .LineStyle = xlContinuous
                    .Weight = xlThin
                    .Color = RGB(191, 144, 0)
                End With
            End With
        End If

nextRow:
    Next r
End Sub

'------------------------------------------------------------------------------
' Procedure: HasDeliveryProgressFill
' Scope: Private Function
'
' What it does:
'   Returns a True/False decision used by higher-level workflow code
'   (HasDeliveryProgressFill).
'
' Why it exists:
'   Boolean helpers make business rules readable and keep condition checks
'   consistent across modules.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function HasDeliveryProgressFill(ByVal rowBand As Range) As Boolean
    Dim clr As Long

    clr = rowBand.Cells(1, 1).Interior.Color

    HasDeliveryProgressFill = _
        (clr = RGB(235, 247, 228)) Or _
        (clr = RGB(255, 249, 230)) Or _
        (clr = RGB(255, 235, 235))
End Function

'------------------------------------------------------------------------------
' Procedure: ApplyGreenvilleReceiveFilter
' Scope: Private Sub
'
' What it does:
'   Identifies, filters, formats, or routes Greenville-specific delivery rows
'   for ApplyGreenvilleReceiveFilter.
'
' Why it exists:
'   Greenville orders are separated from standard Indian Trail inbound work,
'   so those rows need consistent classification across sheets, print/export,
'   and snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ApplyGreenvilleReceiveFilter(ByVal ws As Worksheet)
    Dim orderHdr As Range
    Dim custCol As Long
    Dim routeCol As Long
    Dim firstRow As Long
    Dim lastRow As Long
    Dim r As Long
    Dim isGreenville As Boolean
    Dim isCPU As Boolean

    If Not IsReceiveSheetName(ws.Name) Then Exit Sub

    custCol = GetCustomerColumn(ws)
    routeCol = GetRouteColumn(ws)
    Set orderHdr = FindHeaderCellInCols(ws, Array(HDR_ORDER), "A:N", 250)

    If orderHdr Is Nothing Then Exit Sub

    firstRow = orderHdr.Row + 1
    lastRow = ws.Cells(ws.rows.Count, orderHdr.Column).End(xlUp).Row

    ws.rows("1:" & orderHdr.Row).Hidden = False

    On Error Resume Next
    With ws.Range("X3:AG3")
        If .MergeCells Then .MergeArea.UnMerge
        .Merge

        If UCase$(ws.Name) = UCase$(GREENVILLE_RECV_SHEET_NAME) Then
            .Value = GREENVILLE_RECV_SHEET_NAME
        ElseIf UCase$(ws.Name) = UCase$(CurrentRecvSheetName()) Then
            .Value = CurrentRecvSheetName()
        ElseIf UCase$(ws.Name) = UCase$(CPU_SHEET_NAME) Then
            .Value = CPU_SHEET_NAME
        End If

        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
        .Font.Bold = True
        .Font.Size = 18
    End With
    On Error GoTo 0

    For r = firstRow To lastRow
        isCPU = IsCPURow(ws, r, routeCol)
        isGreenville = IsGreenvilleRow(ws, r, custCol)

        Select Case UCase$(ws.Name)
            Case UCase$(CPU_SHEET_NAME)
                ws.rows(r).Hidden = Not isCPU

            Case UCase$(GREENVILLE_RECV_SHEET_NAME)
                ws.rows(r).Hidden = (Not isGreenville) Or isCPU

            Case UCase$(CurrentRecvSheetName())
                ws.rows(r).Hidden = isGreenville Or isCPU

            Case Else
                ws.rows(r).Hidden = False
        End Select
    Next r

    RefreshReceiveLocationSummary ws
End Sub

'------------------------------------------------------------------------------
' Procedure: VisibleSummaryPctText
' Scope: Private Function
'
' What it does:
'   Calculates or updates summary/banner information shown at the top of
'   delivery/scanner sheets for VisibleSummaryPctText.
'
' Why it exists:
'   Operators use those summary panels to quickly see staged, outbound,
'   inbound, and completion progress without manually counting rows.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function VisibleSummaryPctText(ByVal partVal As Long, ByVal totalVal As Long) As String
    If totalVal <= 0 Then
        VisibleSummaryPctText = "0.0%"
    Else
        VisibleSummaryPctText = Format$(partVal / totalVal, "0.0%")
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: ReceiveSummaryRowMatchesSheet
' Scope: Private Function
'
' What it does:
'   Calculates or updates summary/banner information shown at the top of
'   delivery/scanner sheets for ReceiveSummaryRowMatchesSheet.
'
' Why it exists:
'   Operators use those summary panels to quickly see staged, outbound,
'   inbound, and completion progress without manually counting rows.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function ReceiveSummaryRowMatchesSheet(ByVal ws As Worksheet, _
                                               ByVal rowNum As Long, _
                                               ByVal orderCol As Long, _
                                               ByVal itemCol As Long, _
                                               Optional ByVal customerCol As Long = 0, _
                                               Optional ByVal routeCol As Long = 0) As Boolean
    Dim isGreenville As Boolean
    Dim isCPU As Boolean
    Dim sheetNm As String

    If ws Is Nothing Then Exit Function
    If rowNum < 1 Then Exit Function
    If Not IsRealDeliveryLine(ws, rowNum, orderCol, itemCol) Then Exit Function

    If customerCol = 0 Then customerCol = GetCustomerColumn(ws)
    If routeCol = 0 Then routeCol = GetRouteColumn(ws)

    If routeCol > 0 Then
        isCPU = IsCPURow(ws, rowNum, routeCol)
    Else
        isCPU = False
    End If

    If customerCol > 0 Then
        isGreenville = IsGreenvilleRow(ws, rowNum, customerCol)
    Else
        isGreenville = False
    End If

    sheetNm = UCase$(Trim$(ws.Name))

    Select Case sheetNm
        Case UCase$(CPU_SHEET_NAME)
            ReceiveSummaryRowMatchesSheet = isCPU

        Case UCase$(GREENVILLE_RECV_SHEET_NAME)
            ReceiveSummaryRowMatchesSheet = isGreenville And (Not isCPU)

        Case UCase$(CurrentRecvSheetName())
            ReceiveSummaryRowMatchesSheet = (Not isGreenville) And (Not isCPU)

        Case Else
            ReceiveSummaryRowMatchesSheet = True
    End Select
End Function

'------------------------------------------------------------------------------
' Procedure: RefreshReceiveLocationSummary
' Scope: Public Sub
'
' What it does:
'   Calculates or updates summary/banner information shown at the top of
'   delivery/scanner sheets for RefreshReceiveLocationSummary.
'
' Why it exists:
'   Operators use those summary panels to quickly see staged, outbound,
'   inbound, and completion progress without manually counting rows.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub RefreshReceiveLocationSummary(ByVal ws As Worksheet)
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim qtyHdr As Range
    Dim sendQtyHdr As Range
    Dim sendCheckHdr As Range
    Dim recvQtyHdr As Range
    Dim recvCheckHdr As Range
    Dim stagingQtyHdr As Range

    Dim firstDataRow As Long
    Dim lastRow As Long
    Dim r As Long

    Dim totalQty As Long
    Dim stagedQty As Long
    Dim outboundQty As Long
    Dim inboundQty As Long
    Dim outboundOnTimeQty As Long

    Dim req As Long
    Dim sendStatus As String
    Dim sendTiming As String
    Dim customerCol As Long
    Dim routeCol As Long

    If ws Is Nothing Then Exit Sub
    If Not IsReceiveSheetName(ws.Name) Then Exit Sub

    Set orderHdr = FindHeaderCellInCols(ws, Array(HDR_ORDER), "A:N", 250)
    Set itemHdr = FindHeaderCellInCols(ws, Array(HDR_ITEM), "A:N", 250)
    Set qtyHdr = FindHeaderCellInCols(ws, Array("Qty.", "Qty", "Quantity"), "A:N", 250)

    Set sendQtyHdr = FindHeaderCellInCols(ws, Array("Qty Scanned"), "P:W", 60)
    Set sendCheckHdr = FindHeaderCellInCols(ws, Array("Check"), "P:W", 60)

    Set recvQtyHdr = FindHeaderCellInCols(ws, Array("Qty Scanned"), "Y:AG", 60)
    Set recvCheckHdr = FindHeaderCellInCols(ws, Array("Check"), "Y:AG", 60)

    Set stagingQtyHdr = FindHeaderCellInCols(ws, Array("Qty Scanned"), "AP:AV", 60)

    If orderHdr Is Nothing Then Exit Sub
    If itemHdr Is Nothing Then Exit Sub
    If qtyHdr Is Nothing Then Exit Sub
    If sendQtyHdr Is Nothing Or sendCheckHdr Is Nothing Then Exit Sub
    If recvQtyHdr Is Nothing Or recvCheckHdr Is Nothing Then Exit Sub
    If stagingQtyHdr Is Nothing Then Exit Sub

    customerCol = GetCustomerColumn(ws)
    routeCol = GetRouteColumn(ws)

    firstDataRow = orderHdr.Row + 1
    lastRow = ws.Cells(ws.rows.Count, orderHdr.Column).End(xlUp).Row
    If lastRow < firstDataRow Then Exit Sub

    totalQty = 0
    stagedQty = 0
    outboundQty = 0
    inboundQty = 0
    outboundOnTimeQty = 0

    For r = firstDataRow To lastRow
        If ReceiveSummaryRowMatchesSheet(ws, r, orderHdr.Column, itemHdr.Column, customerCol, routeCol) Then
            req = 1
            If IsNumeric(ws.Cells(r, qtyHdr.Column).Value) Then
                req = CLng(Val(ws.Cells(r, qtyHdr.Column).Value))
                If req < 1 Then req = 1
            End If

            totalQty = totalQty + req
            stagedQty = stagedQty + VisibleSummaryClampQty(ws.Cells(r, stagingQtyHdr.Column).Value, req)
            outboundQty = outboundQty + VisibleSummaryClampQty(ws.Cells(r, sendQtyHdr.Column).Value, req)
            inboundQty = inboundQty + VisibleSummaryClampQty(ws.Cells(r, recvQtyHdr.Column).Value, req)

            sendStatus = UCase$(Trim$(CStr(ws.Cells(r, sendCheckHdr.Column).Value)))
            sendTiming = UCase$(Trim$(CStr(ws.Cells(r, sendCheckHdr.Column + 1).Value)))

            If sendStatus = "OK" Then
                If sendTiming = "ON-TIME" Or sendTiming = "EARLY" Then
                    outboundOnTimeQty = outboundOnTimeQty + req
                End If
            End If
        End If
    Next r

    ws.Range("O2").Value = "Outbound Qty: " & outboundQty & "/" & totalQty & _
                           " â€¢ " & VisibleSummaryPctText(outboundOnTimeQty, totalQty) & " On Time"

    ws.Range("X2").Value = "Inbound Qty: " & inboundQty & "/" & totalQty & _
                           " â€¢ " & VisibleSummaryPctText(inboundQty, totalQty) & " Complete"

    ws.Range("AO2").Value = "Staged Qty: " & stagedQty & "/" & totalQty & _
                            " â€¢ " & VisibleSummaryPctText(stagedQty, totalQty) & " Complete"
End Sub

'------------------------------------------------------------------------------
' Procedure: VisibleSummaryClampQty
' Scope: Private Function
'
' What it does:
'   Calculates or updates summary/banner information shown at the top of
'   delivery/scanner sheets for VisibleSummaryClampQty.
'
' Why it exists:
'   Operators use those summary panels to quickly see staged, outbound,
'   inbound, and completion progress without manually counting rows.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function VisibleSummaryClampQty(ByVal rawVal As Variant, ByVal reqQty As Long) As Long
    Dim q As Long

    q = CLng(Val(rawVal))
    If q < 0 Then q = 0
    If q > reqQty Then q = reqQty

    VisibleSummaryClampQty = q
End Function

'------------------------------------------------------------------------------
' Procedure: IsVisibleReceiveSummaryLine
' Scope: Private Function
'
' What it does:
'   Calculates or updates summary/banner information shown at the top of
'   delivery/scanner sheets for IsVisibleReceiveSummaryLine.
'
' Why it exists:
'   Operators use those summary panels to quickly see staged, outbound,
'   inbound, and completion progress without manually counting rows.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function IsVisibleReceiveSummaryLine(ByVal ws As Worksheet, ByVal rowNum As Long, ByVal orderCol As Long, ByVal itemCol As Long) As Boolean
    If ws.rows(rowNum).Hidden Then Exit Function

    IsVisibleReceiveSummaryLine = IsRealDeliveryLine(ws, rowNum, orderCol, itemCol)
End Function

'------------------------------------------------------------------------------
' Procedure: ReceiveSummaryLineBelongsToSheet
' Scope: Private Function
'
' What it does:
'   Calculates or updates summary/banner information shown at the top of
'   delivery/scanner sheets for ReceiveSummaryLineBelongsToSheet.
'
' Why it exists:
'   Operators use those summary panels to quickly see staged, outbound,
'   inbound, and completion progress without manually counting rows.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function ReceiveSummaryLineBelongsToSheet(ByVal ws As Worksheet, _
                                                  ByVal rowNum As Long, _
                                                  ByVal orderCol As Long, _
                                                  ByVal itemCol As Long, _
                                                  Optional ByVal customerCol As Long = 0, _
                                                  Optional ByVal routeCol As Long = 0) As Boolean
    Dim isGreenville As Boolean
    Dim isCPU As Boolean
    Dim sheetNm As String

    If ws Is Nothing Then Exit Function
    If rowNum < 1 Then Exit Function
    If ws.rows(rowNum).Hidden Then Exit Function
    If Not IsRealDeliveryLine(ws, rowNum, orderCol, itemCol) Then Exit Function

    If customerCol = 0 Then customerCol = GetCustomerColumn(ws)
    If routeCol = 0 Then routeCol = GetRouteColumn(ws)

    isCPU = IsCPURow(ws, rowNum, routeCol)
    isGreenville = IsGreenvilleRow(ws, rowNum, customerCol)
    sheetNm = UCase$(Trim$(ws.Name))

    Select Case sheetNm
        Case UCase$(CPU_SHEET_NAME)
            ReceiveSummaryLineBelongsToSheet = isCPU

        Case UCase$(GREENVILLE_RECV_SHEET_NAME)
            ReceiveSummaryLineBelongsToSheet = isGreenville And (Not isCPU)

        Case UCase$(CurrentRecvSheetName())
            ReceiveSummaryLineBelongsToSheet = (Not isGreenville) And (Not isCPU)

        Case Else
            ReceiveSummaryLineBelongsToSheet = True
    End Select
End Function

'------------------------------------------------------------------------------
' Procedure: FinalizeReceiveLocationSummaries
' Scope: Public Sub
'
' What it does:
'   Performs the workbook-specific step named FinalizeReceiveLocationSummaries
'   inside ThisWorkbook_Master.
'
' Why it exists:
'   Excel events are the only place to intercept open/close, sheet changes,
'   selection changes, and edit-mode transitions reliably.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub FinalizeReceiveLocationSummaries()
    Dim ws As Worksheet

    On Error Resume Next

    Set ws = CurrentRecvSheet()
    If Not ws Is Nothing Then RefreshReceiveLocationSummary ws

    Set ws = GetSheetIfExists(GREENVILLE_RECV_SHEET_NAME)
    If Not ws Is Nothing Then RefreshReceiveLocationSummary ws

    Set ws = GetSheetIfExists(CPU_SHEET_NAME)
    If Not ws Is Nothing Then RefreshReceiveLocationSummary ws

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: HideStagingOnDeliveryList
' Scope: Private Sub
'
' What it does:
'   Hides a sheet, panel, notice, or helper object for
'   HideStagingOnDeliveryList.
'
' Why it exists:
'   Helper objects should stay out of the operatorâ€™s way unless they are
'   needed for troubleshooting.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub HideStagingOnDeliveryList(ByVal ws As Worksheet)
    Dim wasProtected As Boolean

    wasProtected = ws.ProtectContents

    On Error Resume Next
    ws.Unprotect Password:=""
    ws.Columns("AO:AV").EntireColumn.Hidden = False
    On Error GoTo 0

    If wasProtected And Not IsDeliveryEditModeOn() Then
        ProtectViewOnlySheet ws
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: MasterOpenIsAllowedForFullProcessing
' Scope: Private Function
'
' What it does:
'   Performs the workbook-specific step named
'   MasterOpenIsAllowedForFullProcessing inside ThisWorkbook_Master.
'
' Why it exists:
'   Excel events are the only place to intercept open/close, sheet changes,
'   selection changes, and edit-mode transitions reliably.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function MasterOpenIsAllowedForFullProcessing() As Boolean
    'Excel's built-in Read-only Recommended prompt is now used instead.
    'If the workbook opens read-only, do not run master queue/heartbeat/startup processing.
    MasterOpenIsAllowedForFullProcessing = Not ThisWorkbook.ReadOnly
End Function

'------------------------------------------------------------------------------
' Procedure: SwitchMasterWorkbookToReadOnlySafeMode
' Scope: Private Function
'
' What it does:
'   Controls worksheet/workbook protection or read-only safety behavior for
'   SwitchMasterWorkbookToReadOnlySafeMode.
'
' Why it exists:
'   Protection keeps operators from accidentally editing formula/layout areas
'   while still allowing the intended scan or comment cells to work.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SwitchMasterWorkbookToReadOnlySafeMode() As Boolean
    'Legacy safe-mode function no longer used.
    'Excel's built-in Read-only Recommended prompt handles this now.
    SwitchMasterWorkbookToReadOnlySafeMode = ThisWorkbook.ReadOnly
End Function

'------------------------------------------------------------------------------
' Procedure: Workbook_Open
' Scope: Private Sub
'
' What it does:
'   Runs the master workbook startup sequence, applies safety checks,
'   initializes sheet layout/state, and starts processor scheduling only when
'   allowed.
'
' Why it exists:
'   Opening a macro workbook is the point where accidental processing can
'   happen, so startup must be guarded and predictable.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub Workbook_Open()
    Dim openErrText As String
    Dim fullStartupAllowed As Boolean

    On Error GoTo ErrHandler

    fullStartupAllowed = MasterOpenIsAllowedForFullProcessing()

    If Not fullStartupAllowed Then
        On Error Resume Next
        Application.EnableEvents = True
        On Error GoTo 0
        Exit Sub
    End If

    Application.EnableEvents = False
    mPrevMoveAfterReturn = Application.MoveAfterReturn

    On Error Resume Next
    mPrevMoveAfterReturnDirection = Application.MoveAfterReturnDirection
    On Error GoTo ErrHandler

    Application.MoveAfterReturn = False
    UnprotectAllOperationalSheets

    Set mFirstViewResetDone = CreateObject("Scripting.Dictionary")

    SetDeliveryEditMode False
    shownScanInstructionsPopup = False
    currentChangeNoticeShown = False
    lastManualChangeKey = ""
    EnsureChangeAuditSheet
    ResetScanQueueSheet
    mScanQueueProcessorScheduled = False
    mScanQueueProcessorRunning = False

    If LCase$(Right$(ThisWorkbook.Name, 5)) = ".xltm" Then
        ResetManualChangeNotice
    End If

    ShowManualChangeNoticeIfNeeded

    Dim dataWs As Worksheet
    Set dataWs = GetOrRenameDataSheet()

    If dataWs Is Nothing Then
        MsgBox "Could not find or create the Delivery List sheet.", vbCritical, "Open Error"
        GoTo FinalizeOpen
    End If

    'IMPORTANT: unprotect before layout changes
    On Error Resume Next
    dataWs.Unprotect Password:=""
    On Error GoTo ErrHandler

    'DO NOT rebuild the delivery-list import layout on open.
    'That routine is for imports/updates and clears O:AV scan data.
    ScannerValidation.EnsureScanLayout dataWs

    If HasDeliverySummaryTable(dataWs) Then
        CreateOrUpdateTopSummaryPanels dataWs
    End If

    AutoFitCommentColumns dataWs

    EnsureScannerSheetsExist dataWs
    HighlightGreenvilleRows dataWs
    RefreshAllOperationalSheets dataWs
    FinalizeReceiveLocationSummaries
    ForceRow3HeightAll
    CreateOrRefreshActionButtons

    ReapplyAllStoredHighlights dataWs
    RefreshAllDeliveryListProcessStates dataWs
    ApplyFreezePanesToOperationalSheets
    RemoveActionButtonsFromScannerSheets

    HideStagingOnDeliveryList dataWs
    SetDeliverySummaryVisibility dataWs, True
    ProtectViewOnlySheet dataWs

    If ActiveSheet.Name = "Utility Panel" Then
        ActiveWindow.DisplayGridlines = False
    Else
        ActiveWindow.DisplayGridlines = True
    End If

    If ActiveSheet.Name = DATA_SHEET_NAME Or _
        ActiveSheet.Name = STAGING_SHEET_NAME Or _
        ActiveSheet.Name = SEND_SHEET_NAME Or _
        ActiveSheet.Name = CurrentRecvSheetName() Or _
        ActiveSheet.Name = GREENVILLE_RECV_SHEET_NAME Or _
        ActiveSheet.Name = CPU_SHEET_NAME Then

        ShowScanInstructionsOnce
    End If

FinalizeOpen:
    On Error Resume Next

    If fullStartupAllowed Then
        StartExternalQueueProcessor

        If Err.Number <> 0 Then
            If Len(openErrText) > 0 Then openErrText = openErrText & vbCrLf & vbCrLf
            openErrText = openErrText & "Queue startup error " & Err.Number & ":" & vbCrLf & Err.Description
            Err.Clear
        End If
    End If

    On Error GoTo 0

    Application.EnableEvents = True

    If Len(openErrText) > 0 Then
        MsgBox openErrText, vbCritical, "Open Error"
    End If

    Exit Sub

ErrHandler:
    openErrText = "Workbook_Open error " & Err.Number & ":" & vbCrLf & Err.Description
    Resume FinalizeOpen
End Sub

'------------------------------------------------------------------------------
' Procedure: FocusScannerCell
' Scope: Private Sub
'
' What it does:
'   Performs the workbook-specific step named FocusScannerCell inside
'   ThisWorkbook_Master.
'
' Why it exists:
'   Excel events are the only place to intercept open/close, sheet changes,
'   selection changes, and edit-mode transitions reliably.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub FocusScannerCell(ByVal Sh As Object)
    Dim scanAddr As String

    If Sh Is Nothing Then Exit Sub

    Select Case UCase$(Sh.Name)
        Case UCase$(STAGING_SHEET_NAME)
            scanAddr = ScannerValidation.SCAN_CELL_STAGING

        Case UCase$(SEND_SHEET_NAME)
            scanAddr = ScannerValidation.SCAN_CELL_SEND

        Case UCase$(CurrentRecvSheetName()), _
             UCase$(GREENVILLE_RECV_SHEET_NAME), _
             UCase$(CPU_SHEET_NAME)
            scanAddr = ScannerValidation.SCAN_CELL_RECV

        Case Else
            Exit Sub
    End Select

    On Error Resume Next
    Application.MoveAfterReturn = False
    Sh.Activate
    Sh.Range(scanAddr).Select
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: StabilizeOperationalSheetOnActivate
' Scope: Private Sub
'
' What it does:
'   Controls the active sheet/window view, freeze panes, navigation, or
'   selected cell for StabilizeOperationalSheetOnActivate.
'
' Why it exists:
'   The workbook is used by scanners/operators, so opening the right view and
'   scan area reduces missed scans and operator confusion.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub StabilizeOperationalSheetOnActivate(ByVal Sh As Object)
    Dim doFirstViewReset As Boolean

    If Sh Is Nothing Then Exit Sub

    doFirstViewReset = ShouldRunFirstViewReset(Sh.Name)

    On Error GoTo SafeExit

    Application.EnableEvents = False
    Application.ScreenUpdating = False

    If Sh.Name = DATA_SHEET_NAME Then
        SetDeliverySummaryVisibility ThisWorkbook.Worksheets(DATA_SHEET_NAME), True

        If Not IsDeliveryEditModeOn() Then
            ProtectViewOnlySheet ThisWorkbook.Worksheets(DATA_SHEET_NAME)
        End If

        If doFirstViewReset Then
            If Not ActiveWindow Is Nothing Then
                ActiveWindow.ScrollRow = 1
                ActiveWindow.ScrollColumn = 1
            End If
            Application.GoTo Sh.Range("A6"), False
        End If

    ElseIf Sh.Name = STAGING_SHEET_NAME Or Sh.Name = SEND_SHEET_NAME Then
        On Error Resume Next
        Sh.Unprotect Password:=""
        On Error GoTo SafeExit

        If doFirstViewReset Then
            ApplyOperationalFreezePane Sh
            DoEvents

            If Not ActiveWindow Is Nothing Then
                ActiveWindow.ScrollRow = 1
                ActiveWindow.ScrollColumn = 1
            End If

            FocusScannerCell Sh
        End If

        'IMPORTANT: always re-protect scanner sheets after activation work
        ProtectLockColumnsAtoN Sh

    ElseIf IsReceiveSheetName(Sh.Name) Then
        On Error Resume Next
        Sh.Unprotect Password:=""
        On Error GoTo SafeExit

        
               ApplyGreenvilleReceiveFilter Sh
        ForceRow3Height Sh

        If doFirstViewReset Then
            ApplyOperationalFreezePane Sh
            DoEvents

            Sh.Calculate
            DoEvents

            'Refresh receive-location summary again on first activation,
            'after the filter and calculation have settled
            RefreshReceiveLocationSummary Sh

            If Not ActiveWindow Is Nothing Then
                ActiveWindow.ScrollRow = 1
                ActiveWindow.ScrollColumn = 1
            End If

            FocusScannerCell Sh
        Else
            Sh.Calculate
            DoEvents
        End If
        
         'Keep receive-location summary correct on later activations too
            RefreshReceiveLocationSummary Sh

        'IMPORTANT: always re-protect scanner sheets after activation work
        ProtectLockColumnsAtoN Sh
    End If

SafeExit:
    Application.ScreenUpdating = True
    Application.EnableEvents = True
End Sub

'------------------------------------------------------------------------------
' Procedure: RefreshCPUSheetOnActivate
' Scope: Private Sub
'
' What it does:
'   Identifies, filters, formats, or routes Customer Pickup rows for
'   RefreshCPUSheetOnActivate.
'
' Why it exists:
'   Customer Pickup orders follow a separate operational path, so they cannot
'   be mixed into normal inbound/Greenville handling by accident.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub RefreshCPUSheetOnActivate(ByVal Sh As Object)
    If Sh Is Nothing Then Exit Sub
    If UCase$(Sh.Name) <> UCase$(CPU_SHEET_NAME) Then Exit Sub

    On Error Resume Next
    Application.EnableEvents = False
    Sh.Unprotect Password:=""

    ApplyGreenvilleReceiveFilter Sh
    Sh.Calculate
    DoEvents

    On Error GoTo 0
    Application.EnableEvents = True
End Sub

'------------------------------------------------------------------------------
' Procedure: UnprotectAllOperationalSheets
' Scope: Private Sub
'
' What it does:
'   Controls worksheet/workbook protection or read-only safety behavior for
'   UnprotectAllOperationalSheets.
'
' Why it exists:
'   Protection keeps operators from accidentally editing formula/layout areas
'   while still allowing the intended scan or comment cells to work.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub UnprotectAllOperationalSheets()
    On Error Resume Next

    ThisWorkbook.Worksheets(DATA_SHEET_NAME).Unprotect Password:=""
    ThisWorkbook.Worksheets(STAGING_SHEET_NAME).Unprotect Password:=""
    ThisWorkbook.Worksheets(SEND_SHEET_NAME).Unprotect Password:=""

    If Not CurrentRecvSheet() Is Nothing Then
        CurrentRecvSheet().Unprotect Password:=""
    End If

    If GreenvilleSheetExists() Then
        ThisWorkbook.Worksheets(GREENVILLE_RECV_SHEET_NAME).Unprotect Password:=""
    End If

    If CPUSheetExists() Then
        ThisWorkbook.Worksheets(CPU_SHEET_NAME).Unprotect Password:=""
    End If

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: IsLiveScanCaptureCell
' Scope: Private Function
'
' What it does:
'   Returns a True/False decision used by higher-level workflow code
'   (IsLiveScanCaptureCell).
'
' Why it exists:
'   Boolean helpers make business rules readable and keep condition checks
'   consistent across modules.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function IsLiveScanCaptureCell(ByVal target As Range) As Boolean
    If target Is Nothing Then Exit Function
    If target.CountLarge <> 1 Then Exit Function

    IsLiveScanCaptureCell = (target.Column = 16 And target.Row >= 4 And target.Row <= 6)
End Function

'------------------------------------------------------------------------------
' Procedure: Workbook_SheetChange
' Scope: Private Sub
'
' What it does:
'   Handles user edits or scan box changes at the workbook level and routes
'   them to the correct scanner/edit logic.
'
' Why it exists:
'   Workbook events let the project react immediately when the operator
'   changes a protected operational sheet.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub Workbook_SheetChange(ByVal Sh As Object, ByVal target As Range)
    On Error GoTo ErrHandler

    Dim uiWs As Worksheet
    Dim uiScan As Range
    Dim mode As String
    Dim uiScanAddr As String
    Dim rawText As String
    Dim norm As String
    Dim scanQueue As Collection
    Dim i As Long

    '========================
    ' DELIVERY LIST CHANGES
    '========================
    If Sh.Name = DATA_SHEET_NAME Then
        If IsDeliveryEditModeOn() Then
            Application.EnableEvents = False

            MarkDeliveryListEdit target
            SetPendingDeliveryListEdits True

            Application.EnableEvents = True
        End If
        Exit Sub
    End If

    If target Is Nothing Then Exit Sub
    If target.CountLarge <> 1 Then Exit Sub

    rawText = CStr(target.Value)
    norm = NormalizeScan(rawText)


    '========================
    ' COMMENT COLUMN HANDLING
    '========================
    If IsCommentEditCell(Sh, target) Then
        'If a scan/barcode lands in the comments column, block it and warn the user.
        If IsBarcodeLikeScan(norm) Or InStr(1, rawText, "T200", vbTextCompare) > 0 Then
            Application.EnableEvents = False
            SafeClearContents target
            Application.EnableEvents = True

            Beep
            MsgBox "Scans are not allowed in the comments column." & vbCrLf & vbCrLf & _
                "Please scan in the scanner input box for this sheet.", _
                vbExclamation, "Wrong Column"

            FocusScannerCell Sh
            Exit Sub
        End If

        'Normal typed comment edit
        Application.EnableEvents = False
        SyncCommentEdit Sh, target
        AutoFitCommentColumns Sh
        Application.EnableEvents = True
        Exit Sub
    End If

    '========================
    ' DETERMINE MODE / SCAN CELL
    '========================
    If Sh.Name = STAGING_SHEET_NAME Then
        mode = "STAGING"
        uiScanAddr = ScannerValidation.SCAN_CELL_STAGING

    ElseIf Sh.Name = SEND_SHEET_NAME Then
        mode = "SEND"
        uiScanAddr = ScannerValidation.SCAN_CELL_SEND

    ElseIf IsReceiveSheetName(Sh.Name) Then
        mode = "RECV"
        uiScanAddr = ScannerValidation.SCAN_CELL_RECV

    Else
        Exit Sub
    End If

    'If it does not look barcode-like at all, ignore it.
    If Not IsBarcodeLikeScan(norm) And InStr(1, rawText, "T200", vbTextCompare) = 0 Then Exit Sub

    Application.EnableEvents = False
    Application.MoveAfterReturn = False

    Set uiWs = Sh
    Set uiScan = uiWs.Range(uiScanAddr)
    Set scanQueue = New Collection

    'Always snap focus back to the real scan cell
    FocusScannerCell uiWs

    'Queue from the actual changed cell first.
    'This keeps scan-anywhere working.
    EnqueueBarcodesFromRawText rawText, scanQueue

    If scanQueue.Count = 0 Then
        If IsBarcodeLikeScan(norm) Then
            scanQueue.Add norm
        Else
            GoTo SafeExit
        End If
    End If

    For i = 1 To scanQueue.Count
        EnqueueScanRecord uiWs.Name, mode, CStr(scanQueue(i))
    Next i

    'Clear the changed cell that received the scan text
    SafeClearContents target

    'Also harvest any spill that already landed in the live scan zone (rows 4:6 only)
    HarvestThreeCellLiveScanZoneToQueue uiWs, uiScanAddr, mode

    'Pin focus back again before leaving the event
    FocusScannerCell uiWs

    ScheduleQueuedScanProcessor

SafeExit:
    On Error Resume Next
    If Not uiWs Is Nothing Then
        Application.MoveAfterReturn = False
        FocusScannerCell uiWs
    End If
    On Error GoTo 0

    Application.EnableEvents = True
    Exit Sub

ErrHandler:
    Application.EnableEvents = True
    MsgBox "Workbook_SheetChange error " & Err.Number & ":" & vbCrLf & Err.Description, vbCritical, "VBA Error"
End Sub

'------------------------------------------------------------------------------
' Procedure: IsCommentEditCell
' Scope: Private Function
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   IsCommentEditCell.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function IsCommentEditCell(ByVal ws As Worksheet, ByVal target As Range) As Boolean
    If target Is Nothing Then Exit Function
    If target.CountLarge <> 1 Then Exit Function
    If target.Row < FIRST_DATA_ROW Then Exit Function

    Select Case UCase$(ws.Name)
        Case UCase$(STAGING_SHEET_NAME)
            IsCommentEditCell = (target.Column = STAGING_COMMENTS_COL)

        Case UCase$(SEND_SHEET_NAME)
            IsCommentEditCell = (target.Column = SEND_COMMENTS_COL)

        Case UCase$(CurrentRecvSheetName()), _
             UCase$(GREENVILLE_RECV_SHEET_NAME), _
             UCase$(CPU_SHEET_NAME)
            IsCommentEditCell = (target.Column = RECV_COMMENTS_COL)
    End Select
End Function

'------------------------------------------------------------------------------
' Procedure: SyncCommentEdit
' Scope: Private Sub
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   SyncCommentEdit.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub SyncCommentEdit(ByVal srcWs As Worksheet, ByVal target As Range)
    Dim dataWs As Worksheet

    Set dataWs = ThisWorkbook.Worksheets(DATA_SHEET_NAME)

    On Error Resume Next
    dataWs.Unprotect Password:=""
    ThisWorkbook.Worksheets(STAGING_SHEET_NAME).Unprotect Password:=""
    ThisWorkbook.Worksheets(SEND_SHEET_NAME).Unprotect Password:=""
    CurrentRecvSheet().Unprotect Password:=""
    srcWs.Unprotect Password:=""
    If GreenvilleSheetExists() Then
        ThisWorkbook.Worksheets(GREENVILLE_RECV_SHEET_NAME).Unprotect Password:=""
    End If
    If CPUSheetExists() Then
        ThisWorkbook.Worksheets(CPU_SHEET_NAME).Unprotect Password:=""
    End If
    On Error GoTo 0

    'write the comment back to the Delivery List
    dataWs.Cells(target.Row, target.Column).Value = target.Value

    'refresh all sheets so the comment stays everywhere
    HighlightGreenvilleRows dataWs
    RefreshAllOperationalSheets dataWs

    AutoFitCommentColumns dataWs
    AutoFitCommentColumns ThisWorkbook.Worksheets(STAGING_SHEET_NAME)
    AutoFitCommentColumns ThisWorkbook.Worksheets(SEND_SHEET_NAME)
    AutoFitCommentColumns CurrentRecvSheet()

    If GreenvilleSheetExists() Then
        AutoFitCommentColumns ThisWorkbook.Worksheets(GREENVILLE_RECV_SHEET_NAME)
    End If

    If CPUSheetExists() Then
        AutoFitCommentColumns ThisWorkbook.Worksheets(CPU_SHEET_NAME)
    End If

    HideStagingOnDeliveryList dataWs
    SetDeliverySummaryVisibility dataWs, True
    ProtectViewOnlySheet dataWs
End Sub

'------------------------------------------------------------------------------
' Procedure: ShowMostRecentScannedRow
' Scope: Private Sub
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   ShowMostRecentScannedRow.
'
' Why it exists:
'   Rows may represent real orders, section headers, remakes, Greenville work,
'   Customer Pickup work, or updated rows; each type needs different handling.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ShowMostRecentScannedRow(ByVal ws As Worksheet, ByVal scanCell As Range, ByVal rowNum As Long, ByVal mode As String)
    Dim targetScrollRow As Long
    Dim visibleRows As Long
    Dim targetScrollCol As Long
    Dim targetCell As Range

    If ws Is Nothing Then Exit Sub
    If scanCell Is Nothing Then Exit Sub
    If rowNum < 1 Then Exit Sub

    On Error GoTo SafeExit

    mIsShowingScannedRow = True

    Application.ScreenUpdating = True
    ws.Activate
    DoEvents

    Set targetCell = ws.Cells(rowNum, 1)

    On Error Resume Next
    visibleRows = ActiveWindow.VisibleRange.rows.Count
    On Error GoTo SafeExit

    If visibleRows < 10 Then visibleRows = 20

    targetScrollRow = rowNum - Int(visibleRows * 0.5)
    If targetScrollRow < 1 Then targetScrollRow = 1

    Select Case UCase$(mode)
        Case "SEND", "RECV", "STAGING"
            targetScrollCol = 1
        Case Else
            targetScrollCol = 1
    End Select

    'Move the window to the matched row first
    Application.GoTo targetCell, False
    DoEvents

    If Not ActiveWindow Is Nothing Then
        ActiveWindow.ScrollColumn = targetScrollCol
        ActiveWindow.ScrollRow = targetScrollRow
    End If

    DoEvents

    'Then put the selection back on the real scan cell without changing scroll
    scanCell.Select
    DoEvents

    If Not ActiveWindow Is Nothing Then
        ActiveWindow.ScrollColumn = targetScrollCol
        ActiveWindow.ScrollRow = targetScrollRow
    End If

SafeExit:
    mIsShowingScannedRow = False
End Sub

'------------------------------------------------------------------------------
' Procedure: EnsureScannerSheetsExist
' Scope: Private Sub
'
' What it does:
'   Finds, creates, deletes, rebuilds, protects, or synchronizes worksheets
'   for EnsureScannerSheetsExist.
'
' Why it exists:
'   The master workbook creates multiple operational views from one delivery
'   list; worksheet helpers keep those views from drifting apart.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub EnsureScannerSheetsExist(ByVal dataWs As Worksheet)
    EnsureScannerSheetFromTemplate dataWs, STAGING_SHEET_NAME
    EnsureScannerSheetFromTemplate dataWs, SEND_SHEET_NAME
    EnsureScannerSheetFromTemplate dataWs, CurrentRecvSheetName()

    If HasGreenvilleOrders(dataWs) Then
        EnsureScannerSheetFromTemplate dataWs, GREENVILLE_RECV_SHEET_NAME
    ElseIf GreenvilleSheetExists() Then
        On Error Resume Next
        Application.DisplayAlerts = False
        ThisWorkbook.Worksheets(GREENVILLE_RECV_SHEET_NAME).Delete
        Application.DisplayAlerts = True
        On Error GoTo 0
    End If

    If HasCPUOrders(dataWs) Then
        EnsureScannerSheetFromTemplate dataWs, CPU_SHEET_NAME
    ElseIf CPUSheetExists() Then
        On Error Resume Next
        Application.DisplayAlerts = False
        ThisWorkbook.Worksheets(CPU_SHEET_NAME).Delete
        Application.DisplayAlerts = True
        On Error GoTo 0
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: EnsureScannerSheetFromTemplate
' Scope: Private Sub
'
' What it does:
'   Finds, creates, deletes, rebuilds, protects, or synchronizes worksheets
'   for EnsureScannerSheetFromTemplate.
'
' Why it exists:
'   The master workbook creates multiple operational views from one delivery
'   list; worksheet helpers keep those views from drifting apart.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub EnsureScannerSheetFromTemplate(ByVal dataWs As Worksheet, ByVal sheetName As String)
    Dim ws As Worksheet

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(sheetName)
    On Error GoTo 0

    If ws Is Nothing Then
        Application.DisplayAlerts = False
        dataWs.Copy After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count)
        Application.DisplayAlerts = True

        Set ws = ActiveSheet
        ws.Name = sheetName
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: RefreshScannerSheet
' Scope: Private Sub
'
' What it does:
'   Finds, creates, deletes, rebuilds, protects, or synchronizes worksheets
'   for RefreshScannerSheet.
'
' Why it exists:
'   The master workbook creates multiple operational views from one delivery
'   list; worksheet helpers keep those views from drifting apart.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub RefreshScannerSheet(ByVal dataWs As Worksheet, ByVal ws As Worksheet, ByVal mode As String)
    On Error Resume Next
    ws.Unprotect Password:=""
    On Error GoTo 0

    SyncScannerFromMain dataWs, ws
    ForceRow3Height ws
    AutoFitCommentColumns ws
    HideOtherPanel ws, mode

    If IsReceiveSheetName(ws.Name) Then
        ApplyGreenvilleReceiveFilter ws
    End If

    'Keep the Delivery List logo on the scanner sheet after refreshes
    CopyDeliveryListLogoToSheetTemplate dataWs, ws

    'IMPORTANT:
    'Receive sheets must NOT use the generic full-list banner builder.
    'They need their own marker-based summary only.
    If IsReceiveSheetName(ws.Name) Then
        RefreshReceiveLocationSummary ws
    Else
        CreateOrUpdateTopSummaryPanels ws
    End If

    ws.Calculate
    DoEvents

    SetDeliverySummaryVisibility ws, False
    ProtectLockColumnsAtoN ws

    'Allow the next user activation to behave like a first open again
    ResetFirstViewResetFlag ws.Name
End Sub

'------------------------------------------------------------------------------
' Procedure: RefreshAllTopSummaryPanels
' Scope: Private Sub
'
' What it does:
'   Calculates or updates summary/banner information shown at the top of
'   delivery/scanner sheets for RefreshAllTopSummaryPanels.
'
' Why it exists:
'   Operators use those summary panels to quickly see staged, outbound,
'   inbound, and completion progress without manually counting rows.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub RefreshAllTopSummaryPanels()
    Dim ws As Worksheet

    On Error Resume Next

    Set ws = ThisWorkbook.Worksheets(DATA_SHEET_NAME)
    If Not ws Is Nothing Then
        CreateOrUpdateTopSummaryPanels ws
        ws.Calculate
    End If

    Set ws = ThisWorkbook.Worksheets(STAGING_SHEET_NAME)
    If Not ws Is Nothing Then
        CreateOrUpdateTopSummaryPanels ws
        ws.Calculate
    End If

    Set ws = ThisWorkbook.Worksheets(SEND_SHEET_NAME)
    If Not ws Is Nothing Then
        CreateOrUpdateTopSummaryPanels ws
        ws.Calculate
    End If

    Set ws = CurrentRecvSheet()
    If Not ws Is Nothing Then
        RefreshReceiveLocationSummary ws
        ws.Calculate
    End If

    If GreenvilleSheetExists() Then
        Set ws = ThisWorkbook.Worksheets(GREENVILLE_RECV_SHEET_NAME)
        RefreshReceiveLocationSummary ws
        ws.Calculate
    End If

    If CPUSheetExists() Then
        Set ws = ThisWorkbook.Worksheets(CPU_SHEET_NAME)
        RefreshReceiveLocationSummary ws
        ws.Calculate
    End If

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: HideOtherPanel
' Scope: Private Sub
'
' What it does:
'   Builds, formats, deletes, or wires workbook UI shapes/buttons/panels for
'   HideOtherPanel.
'
' Why it exists:
'   Buttons and utility panels are the operator-facing control surface, so
'   they must be rebuilt consistently after imports or sheet refreshes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub HideOtherPanel(ByVal ws As Worksheet, ByVal mode As String)
    On Error Resume Next
    ws.Unprotect Password:=""
    On Error GoTo 0

    ws.Columns("O:AV").Hidden = False

    Select Case UCase$(mode)
        Case "STAGING"
            ws.Columns("O:AN").EntireColumn.Hidden = True

        Case "SEND"
            ws.Columns("X:AV").EntireColumn.Hidden = True

        Case "RECV"
            ws.Columns("O:W").EntireColumn.Hidden = True
            ws.Columns("AO:AV").EntireColumn.Hidden = True
    End Select
End Sub

'------------------------------------------------------------------------------
' Procedure: FindMatchRowInData
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   FindMatchRowInData.
'
' Why it exists:
'   Rows may represent real orders, section headers, remakes, Greenville work,
'   Customer Pickup work, or updated rows; each type needs different handling.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function FindMatchRowInData(ByVal dataWs As Worksheet, ByVal ord As Long, ByVal itm As Long) As Long
    Dim orderHdr As Range, itemHdr As Range

    'IMPORTANT: search only A:N so Airport/Indian panel headers do not collide
    Set orderHdr = FindHeaderCellInCols(dataWs, Array(HDR_ORDER), "A:N", 250)
    Set itemHdr = FindHeaderCellInCols(dataWs, Array(HDR_ITEM), "A:N", 250)

    If orderHdr Is Nothing Or itemHdr Is Nothing Then
        FindMatchRowInData = 0
        Exit Function
    End If

    Dim hdrRow As Long, orderCol As Long, itemCol As Long
    hdrRow = orderHdr.Row
    orderCol = orderHdr.Column
    itemCol = itemHdr.Column

    Dim firstRow As Long, lastRow As Long
    firstRow = hdrRow + 1
    lastRow = dataWs.Cells(dataWs.rows.Count, orderCol).End(xlUp).Row

    If lastRow < firstRow Then
        FindMatchRowInData = 0
        Exit Function
    End If

    FindMatchRowInData = FindRowByOrderItem(dataWs, ord, itm, orderCol, itemCol, firstRow, lastRow)
End Function

'------------------------------------------------------------------------------
' Procedure: ClearScanHighlight
' Scope: Private Sub
'
' What it does:
'   Applies, stores, restores, or clears scan/manual highlight state for
'   ClearScanHighlight.
'
' Why it exists:
'   Highlights help the operator find the affected row after scanning or
'   editing, but stale highlights must be cleared so they do not mislead
'   anyone.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ClearScanHighlight(ByVal ws As Worksheet)
    Dim lastRow As Long
    Dim r As Long

    lastRow = GetLastUsedRow(ws)
    If lastRow < 1 Then Exit Sub

    For r = 1 To lastRow
        If ws.Cells(r, 1).Interior.Color = RGB(255, 255, 153) Then
            ws.Range(ws.Cells(r, 1), ws.Cells(r, SCAN_HIGHLIGHT_LAST_COL)).Interior.Pattern = xlNone
        End If
    Next r
End Sub

'------------------------------------------------------------------------------
' Procedure: GetHighlightStoreName
' Scope: Private Function
'
' What it does:
'   Applies, stores, restores, or clears scan/manual highlight state for
'   GetHighlightStoreName.
'
' Why it exists:
'   Highlights help the operator find the affected row after scanning or
'   editing, but stale highlights must be cleared so they do not mislead
'   anyone.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetHighlightStoreName(ByVal ws As Worksheet) As String
    Dim nm As String

    nm = UCase$(ws.Name)
    nm = Replace$(nm, " ", "_")
    nm = Replace$(nm, "-", "_")
    nm = Replace$(nm, ".", "_")
    nm = Replace$(nm, "&", "_")

    GetHighlightStoreName = "_LastScanHighlight_" & nm
End Function

'------------------------------------------------------------------------------
' Procedure: SaveStoredHighlightRow
' Scope: Private Sub
'
' What it does:
'   Applies, stores, restores, or clears scan/manual highlight state for
'   SaveStoredHighlightRow.
'
' Why it exists:
'   Highlights help the operator find the affected row after scanning or
'   editing, but stale highlights must be cleared so they do not mislead
'   anyone.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub SaveStoredHighlightRow(ByVal ws As Worksheet, ByVal rowNum As Long)
    Dim nm As String

    If ws Is Nothing Then Exit Sub

    nm = GetHighlightStoreName(ws)

    On Error Resume Next
    ThisWorkbook.names(nm).Delete
    On Error GoTo 0

    If rowNum > 0 Then
        ThisWorkbook.names.Add Name:=nm, RefersTo:="=" & CLng(rowNum)
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: GetStoredHighlightRow
' Scope: Private Function
'
' What it does:
'   Applies, stores, restores, or clears scan/manual highlight state for
'   GetStoredHighlightRow.
'
' Why it exists:
'   Highlights help the operator find the affected row after scanning or
'   editing, but stale highlights must be cleared so they do not mislead
'   anyone.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetStoredHighlightRow(ByVal ws As Worksheet) As Long
    Dim nm As String
    Dim s As String

    If ws Is Nothing Then Exit Function

    nm = GetHighlightStoreName(ws)

    On Error Resume Next
    s = ThisWorkbook.names(nm).RefersTo
    On Error GoTo 0

    s = Replace$(s, "=", "")
    s = Trim$(s)

    If IsNumeric(s) Then
        GetStoredHighlightRow = CLng(s)
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: HighlightMostRecent
' Scope: Private Sub
'
' What it does:
'   Applies, stores, restores, or clears scan/manual highlight state for
'   HighlightMostRecent.
'
' Why it exists:
'   Highlights help the operator find the affected row after scanning or
'   editing, but stale highlights must be cleared so they do not mislead
'   anyone.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub HighlightMostRecent(ByVal ws As Worksheet, ByVal newRow As Long)
    ws.Range(ws.Cells(newRow, 1), ws.Cells(newRow, SCAN_HIGHLIGHT_LAST_COL)).Interior.Color = RGB(255, 255, 153)
End Sub

'------------------------------------------------------------------------------
' Procedure: ReapplyStoredHighlight
' Scope: Private Sub
'
' What it does:
'   Applies, stores, restores, or clears scan/manual highlight state for
'   ReapplyStoredHighlight.
'
' Why it exists:
'   Highlights help the operator find the affected row after scanning or
'   editing, but stale highlights must be cleared so they do not mislead
'   anyone.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ReapplyStoredHighlight(ByVal ws As Worksheet)
    Dim rowNum As Long
    Dim lastRow As Long

    If ws Is Nothing Then Exit Sub

    ClearScanHighlight ws

    rowNum = GetStoredHighlightRow(ws)
    lastRow = GetLastUsedRow(ws)

    If rowNum > 0 And rowNum <= lastRow Then
        HighlightMostRecent ws, rowNum
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: ReapplyAllStoredHighlights
' Scope: Private Sub
'
' What it does:
'   Applies, stores, restores, or clears scan/manual highlight state for
'   ReapplyAllStoredHighlights.
'
' Why it exists:
'   Highlights help the operator find the affected row after scanning or
'   editing, but stale highlights must be cleared so they do not mislead
'   anyone.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ReapplyAllStoredHighlights(ByVal dataWs As Worksheet)
    Dim recvWs As Worksheet

    ReapplyStoredHighlight dataWs
    ReapplyStoredHighlight ThisWorkbook.Worksheets(STAGING_SHEET_NAME)
    ReapplyStoredHighlight ThisWorkbook.Worksheets(SEND_SHEET_NAME)

    On Error Resume Next
    Set recvWs = CurrentRecvSheet()
    On Error GoTo 0

    If Not recvWs Is Nothing Then
        ReapplyStoredHighlight recvWs
    End If

    If GreenvilleSheetExists() Then
        ReapplyStoredHighlight ThisWorkbook.Worksheets(GREENVILLE_RECV_SHEET_NAME)
    End If

    If CPUSheetExists() Then
        ReapplyStoredHighlight ThisWorkbook.Worksheets(CPU_SHEET_NAME)
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: FormatProcessStateCell
' Scope: Private Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   FormatProcessStateCell.
'
' Why it exists:
'   Remakes need separate visual and print/export handling so replacement
'   glass is not confused with regular delivery-list work.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub FormatProcessStateCell(ByVal c As Range, ByVal stateText As String)
    With c
        'Process State formatting should always win on the Process State column
        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
        .WrapText = False
        .NumberFormat = "@"

        .Font.Bold = True
        .Font.Italic = False
        .Font.Underline = xlUnderlineStyleNone
        .Font.Strikethrough = False
        .Font.ColorIndex = xlAutomatic

        .Interior.PatternColorIndex = xlAutomatic
        .Interior.TintAndShade = 0
        .Borders.LineStyle = xlNone

        Select Case UCase$(Trim$(stateText))

            Case "STAGED"
                .Value = "Staged"
                .Interior.Pattern = xlSolid
                .Interior.Color = RGB(217, 217, 217)   'lighter, cleaner gray
                .Font.Color = RGB(64, 64, 64)          'darker text for readability

            Case "OUTBOUND"
                .Value = "Outbound"
                .Interior.Pattern = xlSolid
                .Interior.Color = RGB(189, 215, 238)
                .Font.Color = RGB(0, 112, 192)

            Case "RECEIVED"
                .Value = "Received"
                .Interior.Pattern = xlSolid
                .Interior.Color = RGB(198, 239, 206)
                .Font.Color = RGB(0, 128, 0)

            Case Else
                .ClearContents
                .Interior.Pattern = xlNone
                .Font.Bold = False
                .Font.ColorIndex = xlAutomatic
                .Borders.LineStyle = xlNone
        End Select
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: GetDeliveryProcessStateText
' Scope: Private Function
'
' What it does:
'   Returns a workbook object, setting, status value, parsed value, or
'   calculated result used by other procedures (GetDeliveryProcessStateText).
'
' Why it exists:
'   Using one getter keeps callers from duplicating lookup logic and protects
'   them from missing sheets, missing names, or blank values.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetDeliveryProcessStateText(ByVal ws As Worksheet, ByVal rowNum As Long) As String
    Dim stagingQty As Long
    Dim sendQty As Long
    Dim recvQty As Long
    Dim recvStatus As String

    stagingQty = CLng(Val(ws.Range("AS" & rowNum).Value))
    sendQty = CLng(Val(ws.Range("S" & rowNum).Value))
    recvQty = CLng(Val(ws.Range("AB" & rowNum).Value))
    recvStatus = UCase$(Trim$(CStr(ws.Range("AD" & rowNum).Value)))

    If recvQty > 0 Or Len(recvStatus) > 0 Then
        GetDeliveryProcessStateText = "RECEIVED"
    ElseIf sendQty > 0 Then
        GetDeliveryProcessStateText = "OUTBOUND"
    ElseIf stagingQty > 0 Then
        GetDeliveryProcessStateText = "STAGED"
    Else
        GetDeliveryProcessStateText = vbNullString
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: UpdateDeliveryProcessStateForRow
' Scope: Private Sub
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   UpdateDeliveryProcessStateForRow.
'
' Why it exists:
'   Delivery timing, queue timestamps, and scan timestamps drive status
'   messages such as Early, On-Time, Late, Processing, and Done.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub UpdateDeliveryProcessStateForRow(ByVal ws As Worksheet, ByVal rowNum As Long)
    Dim stateText As String
    stateText = GetDeliveryProcessStateText(ws, rowNum)
    FormatProcessStateCell ws.Cells(rowNum, PROCESS_STATE_COL_FIXED), stateText
End Sub

'------------------------------------------------------------------------------
' Procedure: RefreshAllDeliveryListProcessStates
' Scope: Public Sub
'
' What it does:
'   Refreshes calculated display/state based on the latest workbook data for
'   RefreshAllDeliveryListProcessStates.
'
' Why it exists:
'   Operators depend on the visible sheets matching the real scan/queue state
'   after edits, imports, and queue processing.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub RefreshAllDeliveryListProcessStates(Optional ByVal ws As Worksheet = Nothing)
    Dim dataWs As Worksheet
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim orderCol As Long
    Dim itemCol As Long
    Dim firstRow As Long
    Dim lastRow As Long
    Dim r As Long

    If ws Is Nothing Then
        Set dataWs = ThisWorkbook.Worksheets(DATA_SHEET_NAME)
    Else
        Set dataWs = ws
    End If

    Set orderHdr = FindHeaderCellInCols(dataWs, Array(HDR_ORDER), "A:N", 250)
    Set itemHdr = FindHeaderCellInCols(dataWs, Array(HDR_ITEM), "A:N", 250)

    If orderHdr Is Nothing Or itemHdr Is Nothing Then Exit Sub

    orderCol = orderHdr.Column
    itemCol = itemHdr.Column
    firstRow = orderHdr.Row + 1
    lastRow = GetLastUsedRow(dataWs)

    If lastRow < firstRow Then Exit Sub

    For r = firstRow To lastRow
        If IsRealDeliveryLine(dataWs, r, orderCol, itemCol) Then
            UpdateDeliveryProcessStateForRow dataWs, r
        End If
    Next r
End Sub

'------------------------------------------------------------------------------
' Procedure: GetDeliveryListProgressStatus
' Scope: Private Function
'
' What it does:
'   Returns a workbook object, setting, status value, parsed value, or
'   calculated result used by other procedures
'   (GetDeliveryListProgressStatus).
'
' Why it exists:
'   Using one getter keeps callers from duplicating lookup logic and protects
'   them from missing sheets, missing names, or blank values.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetDeliveryListProgressStatus(ByVal ws As Worksheet, ByVal rowNum As Long) As String
    Dim recvStatus As String
    Dim sendStatus As String
    Dim stagingStatus As String

    recvStatus = Trim$(CStr(ws.Range("AD" & rowNum).Value))
    sendStatus = Trim$(CStr(ws.Range("U" & rowNum).Value))
    stagingStatus = Trim$(CStr(ws.Range("AU" & rowNum).Value))

    If Len(recvStatus) > 0 Then
        GetDeliveryListProgressStatus = recvStatus
    ElseIf Len(sendStatus) > 0 Then
        GetDeliveryListProgressStatus = sendStatus
    ElseIf Len(stagingStatus) > 0 Then
        GetDeliveryListProgressStatus = stagingStatus
    Else
        GetDeliveryListProgressStatus = vbNullString
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: ApplyDeliveryListProgressRowStyle
' Scope: Private Sub
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   ApplyDeliveryListProgressRowStyle.
'
' Why it exists:
'   Rows may represent real orders, section headers, remakes, Greenville work,
'   Customer Pickup work, or updated rows; each type needs different handling.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ApplyDeliveryListProgressRowStyle(ByVal ws As Worksheet, ByVal rowNum As Long, ByVal statusText As String)
    Dim rowBand As Range
    Set rowBand = ws.Range("A" & rowNum & ":J" & rowNum)

    Select Case True
        Case statusText = "OK" Or statusText = "Received"
            With rowBand
                .Interior.Color = RGB(235, 247, 228)
                .Font.Color = RGB(0, 97, 0)
                .Font.Bold = False
            End With

        Case Left$(statusText, 7) = "Partial "
            With rowBand
                .Interior.Color = RGB(255, 249, 230)
                .Font.Color = RGB(156, 101, 0)
                .Font.Bold = False
            End With

        Case statusText = "Mismatch"
            With rowBand
                .Interior.Color = RGB(255, 235, 235)
                .Font.Color = RGB(156, 0, 6)
                .Font.Bold = False
            End With
    End Select
End Sub

'------------------------------------------------------------------------------
' Procedure: ReapplyDeliveryListProgressRows
' Scope: Private Sub
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   ReapplyDeliveryListProgressRows.
'
' Why it exists:
'   Rows may represent real orders, section headers, remakes, Greenville work,
'   Customer Pickup work, or updated rows; each type needs different handling.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ReapplyDeliveryListProgressRows(ByVal ws As Worksheet)
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim orderCol As Long
    Dim itemCol As Long
    Dim firstRow As Long
    Dim lastRow As Long
    Dim currentHighlightRow As Long
    Dim r As Long
    Dim statusText As String

    Set orderHdr = FindHeaderCellInCols(ws, Array(HDR_ORDER), "A:N", 250)
    Set itemHdr = FindHeaderCellInCols(ws, Array(HDR_ITEM), "A:N", 250)

    If orderHdr Is Nothing Or itemHdr Is Nothing Then Exit Sub

    orderCol = orderHdr.Column
    itemCol = itemHdr.Column
    firstRow = orderHdr.Row + 1
    lastRow = GetLastUsedRow(ws)
    currentHighlightRow = GetStoredHighlightRow(ws)

    If lastRow < firstRow Then Exit Sub

    For r = firstRow To lastRow
        If IsRealDeliveryLine(ws, r, orderCol, itemCol) Then
            If r <> currentHighlightRow Then
                statusText = GetDeliveryListProgressStatus(ws, r)

                If Len(statusText) > 0 Then
                    ApplyDeliveryListProgressRowStyle ws, r, statusText
                End If
            End If
        End If
    Next r
End Sub

'------------------------------------------------------------------------------
' Procedure: FindHeaderCellInCols
' Scope: Private Function
'
' What it does:
'   Finds, writes, validates, or uses worksheet header cells for
'   FindHeaderCellInCols.
'
' Why it exists:
'   Header locations can move during import/rebuild, so the code uses header
'   discovery to target the correct columns instead of guessing.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function FindHeaderCellInCols(ByVal ws As Worksheet, ByVal names As Variant, ByVal colAddress As String, Optional ByVal topRows As Long = 200) As Range
    Dim searchRange As Range, nm As Variant, f As Range
    Set searchRange = Intersect(ws.Range("1:" & topRows), ws.Columns(colAddress))
    If searchRange Is Nothing Then
        Set FindHeaderCellInCols = Nothing
        Exit Function
    End If

    For Each nm In names
        Set f = searchRange.Find(What:=CStr(nm), LookIn:=xlValues, LookAt:=xlWhole)
        If Not f Is Nothing Then
            Set FindHeaderCellInCols = f
            Exit Function
        End If
    Next nm

    For Each nm In names
        Set f = searchRange.Find(What:=CStr(nm), LookIn:=xlValues, LookAt:=xlPart)
        If Not f Is Nothing Then
            Set FindHeaderCellInCols = f
            Exit Function
        End If
    Next nm

    Set FindHeaderCellInCols = Nothing
End Function

'------------------------------------------------------------------------------
' Procedure: FindRowByOrderItem
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   FindRowByOrderItem.
'
' Why it exists:
'   Rows may represent real orders, section headers, remakes, Greenville work,
'   Customer Pickup work, or updated rows; each type needs different handling.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function FindRowByOrderItem(ByVal ws As Worksheet, ByVal orderNum As Long, ByVal itemNum As Long, _
                                    ByVal orderCol As Long, ByVal itemCol As Long, _
                                    ByVal firstRow As Long, ByVal lastRow As Long) As Long
    Dim rng As Range, f As Range, firstAddr As String
    Set rng = ws.Range(ws.Cells(firstRow, orderCol), ws.Cells(lastRow, orderCol))

    Set f = rng.Find(What:=CStr(orderNum), LookIn:=xlValues, LookAt:=xlWhole)
    If Not f Is Nothing Then
        firstAddr = f.Address
        Do
            If IsNumeric(ws.Cells(f.Row, itemCol).Value) Then
                If CLng(ws.Cells(f.Row, itemCol).Value) = itemNum Then
                    FindRowByOrderItem = f.Row
                    Exit Function
                End If
            End If
            Set f = rng.FindNext(f)
        Loop While Not f Is Nothing And f.Address <> firstAddr
    End If

    FindRowByOrderItem = 0
End Function

'------------------------------------------------------------------------------
' Procedure: IsRealDeliveryLine
' Scope: Private Function
'
' What it does:
'   Returns a True/False decision used by higher-level workflow code
'   (IsRealDeliveryLine).
'
' Why it exists:
'   Boolean helpers make business rules readable and keep condition checks
'   consistent across modules.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function IsRealDeliveryLine(ByVal ws As Worksheet, ByVal rowNum As Long, ByVal orderCol As Long, ByVal itemCol As Long) As Boolean
    Dim vOrder As Variant
    Dim vItem As Variant

    vOrder = ws.Cells(rowNum, orderCol).Value
    vItem = ws.Cells(rowNum, itemCol).Value

    IsRealDeliveryLine = False

    If IsNumeric(vOrder) And IsNumeric(vItem) Then
        If CLng(Val(vOrder)) > 0 Then
            IsRealDeliveryLine = True
        End If
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: GetOrRenameDataSheet
' Scope: Private Function
'
' What it does:
'   Finds, creates, deletes, rebuilds, protects, or synchronizes worksheets
'   for GetOrRenameDataSheet.
'
' Why it exists:
'   The master workbook creates multiple operational views from one delivery
'   list; worksheet helpers keep those views from drifting apart.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetOrRenameDataSheet() As Worksheet
    Dim ws As Worksheet
    Dim candidate As Worksheet

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(DATA_SHEET_NAME)
    On Error GoTo 0

    If Not ws Is Nothing Then
        Set GetOrRenameDataSheet = ws
        Exit Function
    End If

    'Try to find a sheet that looks like the delivery list
    For Each candidate In ThisWorkbook.Worksheets
        If candidate.Name <> STAGING_SHEET_NAME _
            And candidate.Name <> SEND_SHEET_NAME _
            And candidate.Name <> CurrentRecvSheetName() _
            And candidate.Name <> "Utility Panel" _
            And candidate.Name <> "__ChangeAudit" Then

            If Not FindHeaderCellInCols(candidate, Array(HDR_ORDER), "A:N", 250) Is Nothing Then
                If Not FindHeaderCellInCols(candidate, Array(HDR_ITEM), "A:N", 250) Is Nothing Then
                    On Error Resume Next
                    candidate.Name = DATA_SHEET_NAME
                    On Error GoTo 0

                    If candidate.Name = DATA_SHEET_NAME Then
                        Set GetOrRenameDataSheet = candidate
                        Exit Function
                    End If
                End If
            End If
        End If
    Next candidate

    'Fallback: only rename first sheet if it is not one of the special tabs
    If ThisWorkbook.Worksheets.Count >= 1 Then
        Set ws = ThisWorkbook.Worksheets(1)

        If ws.Name <> STAGING_SHEET_NAME _
            And ws.Name <> SEND_SHEET_NAME _
            And ws.Name <> CurrentRecvSheetName() _
            And ws.Name <> "Utility Panel" _
            And ws.Name <> "__ChangeAudit" Then

            On Error Resume Next
            ws.Name = DATA_SHEET_NAME
            On Error GoTo 0

            If ws.Name = DATA_SHEET_NAME Then
                Set GetOrRenameDataSheet = ws
                Exit Function
            End If
        End If
    End If

    Set GetOrRenameDataSheet = Nothing
End Function

'------------------------------------------------------------------------------
' Procedure: NormalizeScan
' Scope: Private Function
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   NormalizeScan.
'
' Why it exists:
'   Remakes need separate visual and print/export handling so replacement
'   glass is not confused with regular delivery-list work.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function NormalizeScan(ByVal s As String) As String
    Dim i As Long, ch As String, out As String

    s = Replace(s, "*", "")
    s = Replace(s, vbCr, "")
    s = Replace(s, vbLf, "")
    s = Trim$(s)

    For i = 1 To Len(s)
        ch = Mid$(s, i, 1)
        If ch Like "[0-9A-Za-z]" Then out = out & ch
    Next i

    NormalizeScan = UCase$(out)
End Function

'------------------------------------------------------------------------------
' Procedure: SafeClearContents
' Scope: Private Sub
'
' What it does:
'   Performs the workbook-specific step named SafeClearContents inside
'   ThisWorkbook_Master.
'
' Why it exists:
'   Excel events are the only place to intercept open/close, sheet changes,
'   selection changes, and edit-mode transitions reliably.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub SafeClearContents(ByVal rng As Range)
    On Error Resume Next
    If rng Is Nothing Then Exit Sub

    If rng.MergeCells Then
        rng.MergeArea.Cells(1, 1).ClearContents
    Else
        rng.ClearContents
    End If

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: GetOrCreateScanQueueSheet
' Scope: Private Function
'
' What it does:
'   Finds, creates, deletes, rebuilds, protects, or synchronizes worksheets
'   for GetOrCreateScanQueueSheet.
'
' Why it exists:
'   The master workbook creates multiple operational views from one delivery
'   list; worksheet helpers keep those views from drifting apart.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetOrCreateScanQueueSheet() As Worksheet
    Dim ws As Worksheet

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(SCAN_QUEUE_SHEET_NAME)
    On Error GoTo 0

    If ws Is Nothing Then
        Set ws = ThisWorkbook.Worksheets.Add(After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
        ws.Name = SCAN_QUEUE_SHEET_NAME

        ws.Range("A1").Value = "Seq"
        ws.Range("B1").Value = "SourceSheet"
        ws.Range("C1").Value = "Mode"
        ws.Range("D1").Value = "Barcode"
        ws.Range("E1").Value = "QueuedAt"

        ws.Visible = xlSheetVeryHidden
    End If

    Set GetOrCreateScanQueueSheet = ws
End Function

'------------------------------------------------------------------------------
' Procedure: ResetScanQueueSheet
' Scope: Private Sub
'
' What it does:
'   Finds, creates, deletes, rebuilds, protects, or synchronizes worksheets
'   for ResetScanQueueSheet.
'
' Why it exists:
'   The master workbook creates multiple operational views from one delivery
'   list; worksheet helpers keep those views from drifting apart.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ResetScanQueueSheet()
    Dim ws As Worksheet
    Dim lastRow As Long

    Set ws = GetOrCreateScanQueueSheet()
    lastRow = ws.Cells(ws.rows.Count, 1).End(xlUp).Row

    If lastRow >= 2 Then
        ws.Range("A2:E" & lastRow).ClearContents
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: EnqueueScanRecord
' Scope: Private Sub
'
' What it does:
'   Handles queue/request state used by the shared ScanQueue workflow for
'   EnqueueScanRecord.
'
' Why it exists:
'   Queue state must be tracked carefully so buffered intake scans, master
'   processing, retries, and final results stay aligned.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub EnqueueScanRecord(ByVal sourceSheetName As String, ByVal mode As String, ByVal barcodeText As String)
    Dim deliveryListKey As String
    Dim dt As Date
    Dim ok As Boolean
    Dim sourceWs As Worksheet
    Dim canonicalBarcode As String
    Dim ord As Long
    Dim itm As Long

    If Len(barcodeText) = 0 Then Exit Sub

    Set sourceWs = GetSheetIfExists(sourceSheetName)
    If sourceWs Is Nothing Then Set sourceWs = GetSheetIfExists(DATA_SHEET_NAME)

    If Not TryCanonicalizeQueuedScan(sourceWs, barcodeText, canonicalBarcode, ord, itm) Then Exit Sub
    barcodeText = canonicalBarcode

    deliveryListKey = "DL_UNKNOWN"

    On Error Resume Next
    dt = GetDeliveryListDateForFileName(ThisWorkbook.Worksheets("Delivery List"))
    On Error GoTo 0

    If dt > 0 Then
        deliveryListKey = "DL_" & Format$(dt, "yyyy_mm_dd")
    End If

    ok = PA_QueueAddBarcodeRequest( _
            deliveryListKey, _
            UCase$(mode), _
            UCase$(barcodeText), _
            sourceSheetName, _
            ThisWorkbook.Name, _
            vbNullString)

    If Not ok Then
        MsgBox "Could not write the scan to the Power Automate queue.", vbExclamation, "Queue Write Error"
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: HarvestThreeCellLiveScanZoneToQueue
' Scope: Private Sub
'
' What it does:
'   Handles queue/request state used by the shared ScanQueue workflow for
'   HarvestThreeCellLiveScanZoneToQueue.
'
' Why it exists:
'   Queue state must be tracked carefully so buffered intake scans, master
'   processing, retries, and final results stay aligned.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub HarvestThreeCellLiveScanZoneToQueue(ByVal ws As Worksheet, ByVal scanAddr As String, ByVal mode As String)
    Dim scanCell As Range
    Dim c As Range
    Dim found As Collection
    Dim v As Variant
    Dim rawText As String

    If ws Is Nothing Then Exit Sub
    If Len(scanAddr) = 0 Then Exit Sub

    Set scanCell = ws.Range(scanAddr)

    'IMPORTANT:
    'Do NOT harvest row 4, because ScannerValidation writes the last successful scan
    'back into the real scan cell (P4 / Y4 / AP4) as a display value.
    '
    'Only harvest spill rows below the scan cell:
    'row 5 = possible overwrite of the header
    'row 6 = possible second spill row
    For Each c In ws.Range(ws.Cells(scanCell.Row + 1, scanCell.Column), ws.Cells(scanCell.Row + 2, scanCell.Column)).Cells
        rawText = CStr(c.Value)

        If Len(rawText) > 0 Then
            Set found = ExtractBarcodeMatchesFromRawText(rawText)

            If found.Count > 0 Then
                For Each v In found
                    EnqueueScanRecord ws.Name, mode, CStr(v)
                Next v

                SafeClearContents c
            End If
        End If
    Next c
End Sub

'------------------------------------------------------------------------------
' Procedure: HarvestAllLiveScanZonesToQueueSheet
' Scope: Private Sub
'
' What it does:
'   Finds, creates, deletes, rebuilds, protects, or synchronizes worksheets
'   for HarvestAllLiveScanZonesToQueueSheet.
'
' Why it exists:
'   The master workbook creates multiple operational views from one delivery
'   list; worksheet helpers keep those views from drifting apart.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub HarvestAllLiveScanZonesToQueueSheet()
    Dim ws As Worksheet

    On Error Resume Next

    Set ws = GetSheetIfExists(STAGING_SHEET_NAME)
    If Not ws Is Nothing Then
        HarvestThreeCellLiveScanZoneToQueue ws, ScannerValidation.SCAN_CELL_STAGING, "STAGING"
    End If

    Set ws = GetSheetIfExists(SEND_SHEET_NAME)
    If Not ws Is Nothing Then
        HarvestThreeCellLiveScanZoneToQueue ws, ScannerValidation.SCAN_CELL_SEND, "SEND"
    End If

    Set ws = CurrentRecvSheet()
    If Not ws Is Nothing Then
        HarvestThreeCellLiveScanZoneToQueue ws, ScannerValidation.SCAN_CELL_RECV, "RECV"
    End If

    Set ws = GetSheetIfExists(GREENVILLE_RECV_SHEET_NAME)
    If Not ws Is Nothing Then
        HarvestThreeCellLiveScanZoneToQueue ws, ScannerValidation.SCAN_CELL_RECV, "RECV"
    End If

    Set ws = GetSheetIfExists(CPU_SHEET_NAME)
    If Not ws Is Nothing Then
        HarvestThreeCellLiveScanZoneToQueue ws, ScannerValidation.SCAN_CELL_RECV, "RECV"
    End If

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: AddQueuedScanItem
' Scope: Private Sub
'
' What it does:
'   Handles queue/request state used by the shared ScanQueue workflow for
'   AddQueuedScanItem.
'
' Why it exists:
'   Queue state must be tracked carefully so buffered intake scans, master
'   processing, retries, and final results stay aligned.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub AddQueuedScanItem(ByRef items As Collection, ByVal sourceSheetName As String, ByVal mode As String, ByVal barcodeText As String)
    If Len(barcodeText) = 0 Then Exit Sub
    If Not IsBarcodeLikeScan(barcodeText) Then Exit Sub

    items.Add Array(CStr(sourceSheetName), UCase$(mode), UCase$(NormalizeScan(barcodeText)))
End Sub

'------------------------------------------------------------------------------
' Procedure: HarvestBarcodesFromCellToItems
' Scope: Private Sub
'
' What it does:
'   Cleans, decodes, validates, writes, or displays barcode data for
'   HarvestBarcodesFromCellToItems.
'
' Why it exists:
'   The barcode is the link between the physical glass label and the
'   order/item row, so the project must parse and validate it consistently.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub HarvestBarcodesFromCellToItems(ByVal ws As Worksheet, ByVal c As Range, ByVal mode As String, ByRef items As Collection)
    Dim found As Collection
    Dim v As Variant
    Dim rawText As String

    If ws Is Nothing Then Exit Sub
    If c Is Nothing Then Exit Sub

    rawText = CStr(c.Value)
    If Len(rawText) = 0 Then Exit Sub

    Set found = ExtractBarcodeMatchesFromRawText(rawText)

    If found.Count > 0 Then
        For Each v In found
            AddQueuedScanItem items, ws.Name, mode, CStr(v)
        Next v

        SafeClearContents c
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: HarvestScanCaptureZoneToItems
' Scope: Private Sub
'
' What it does:
'   Performs the workbook-specific step named HarvestScanCaptureZoneToItems
'   inside ThisWorkbook_Master.
'
' Why it exists:
'   Excel events are the only place to intercept open/close, sheet changes,
'   selection changes, and edit-mode transitions reliably.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub HarvestScanCaptureZoneToItems(ByVal ws As Worksheet, ByVal scanAddr As String, ByVal mode As String, ByRef items As Collection)
    Dim scanCell As Range
    Dim r As Long
    Dim rowStart As Long
    Dim rowEnd As Long
    Dim scanCol As Long

    If ws Is Nothing Then Exit Sub
    If Len(scanAddr) = 0 Then Exit Sub

    Set scanCell = ws.Range(scanAddr)
    scanCol = scanCell.Column

    'Sweep the scan cell and a few rows below/above it
    rowStart = scanCell.Row - 1
    If rowStart < 1 Then rowStart = 1

    rowEnd = scanCell.Row + 6

    For r = rowStart To rowEnd
        HarvestBarcodesFromCellToItems ws, ws.Cells(r, scanCol), mode, items
    Next r
End Sub

'------------------------------------------------------------------------------
' Procedure: HarvestAllScannerCaptureZonesToQueueSheet
' Scope: Private Sub
'
' What it does:
'   Finds, creates, deletes, rebuilds, protects, or synchronizes worksheets
'   for HarvestAllScannerCaptureZonesToQueueSheet.
'
' Why it exists:
'   The master workbook creates multiple operational views from one delivery
'   list; worksheet helpers keep those views from drifting apart.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub HarvestAllScannerCaptureZonesToQueueSheet()
    Dim items As Collection
    Dim i As Long
    Dim oneItem As Variant
    Dim ws As Worksheet

    Set items = New Collection

    On Error Resume Next

    Set ws = GetSheetIfExists(STAGING_SHEET_NAME)
    If Not ws Is Nothing Then
        HarvestScanCaptureZoneToItems ws, ScannerValidation.SCAN_CELL_STAGING, "STAGING", items
    End If

    Set ws = GetSheetIfExists(SEND_SHEET_NAME)
    If Not ws Is Nothing Then
        HarvestScanCaptureZoneToItems ws, ScannerValidation.SCAN_CELL_SEND, "SEND", items
    End If

    Set ws = CurrentRecvSheet()
    If Not ws Is Nothing Then
        HarvestScanCaptureZoneToItems ws, ScannerValidation.SCAN_CELL_RECV, "RECV", items
    End If

    Set ws = GetSheetIfExists(GREENVILLE_RECV_SHEET_NAME)
    If Not ws Is Nothing Then
        HarvestScanCaptureZoneToItems ws, ScannerValidation.SCAN_CELL_RECV, "RECV", items
    End If

    Set ws = GetSheetIfExists(CPU_SHEET_NAME)
    If Not ws Is Nothing Then
        HarvestScanCaptureZoneToItems ws, ScannerValidation.SCAN_CELL_RECV, "RECV", items
    End If

    On Error GoTo 0

    For i = 1 To items.Count
        oneItem = items(i)
        EnqueueScanRecord CStr(oneItem(0)), CStr(oneItem(1)), CStr(oneItem(2))
    Next i
End Sub

'------------------------------------------------------------------------------
' Procedure: GetNextQueuedScanRow
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   GetNextQueuedScanRow.
'
' Why it exists:
'   Rows may represent real orders, section headers, remakes, Greenville work,
'   Customer Pickup work, or updated rows; each type needs different handling.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetNextQueuedScanRow(ByVal qWs As Worksheet) As Long
    Dim lastRow As Long
    Dim r As Long

    If qWs Is Nothing Then Exit Function

    lastRow = qWs.Cells(qWs.rows.Count, 4).End(xlUp).Row
    If lastRow < 2 Then Exit Function

    For r = 2 To lastRow
        If Len(Trim$(CStr(qWs.Cells(r, 4).Value))) > 0 Then
            GetNextQueuedScanRow = r
            Exit Function
        End If
    Next r
End Function

'------------------------------------------------------------------------------
' Procedure: GetScanCellAddressForMode
' Scope: Private Function
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   GetScanCellAddressForMode.
'
' Why it exists:
'   Remakes need separate visual and print/export handling so replacement
'   glass is not confused with regular delivery-list work.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetScanCellAddressForMode(ByVal mode As String) As String
    Select Case UCase$(mode)
        Case "STAGING"
            GetScanCellAddressForMode = ScannerValidation.SCAN_CELL_STAGING
        Case "SEND"
            GetScanCellAddressForMode = ScannerValidation.SCAN_CELL_SEND
        Case "RECV"
            GetScanCellAddressForMode = ScannerValidation.SCAN_CELL_RECV
    End Select
End Function

'------------------------------------------------------------------------------
' Procedure: IsInScannerCaptureZone
' Scope: Private Function
'
' What it does:
'   Returns a True/False decision used by higher-level workflow code
'   (IsInScannerCaptureZone).
'
' Why it exists:
'   Boolean helpers make business rules readable and keep condition checks
'   consistent across modules.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function IsInScannerCaptureZone(ByVal ws As Worksheet, ByVal target As Range, ByVal scanAddr As String) As Boolean
    Dim scanCell As Range

    If ws Is Nothing Then Exit Function
    If target Is Nothing Then Exit Function
    If Len(scanAddr) = 0 Then Exit Function
    If target.CountLarge <> 1 Then Exit Function

    Set scanCell = ws.Range(scanAddr)

    'Only accept scans from the scan cell itself, one row above, or up to four rows below.
    'This catches Enter-spill during rapid scans without touching the historic barcode column.
    IsInScannerCaptureZone = _
        (target.Column = scanCell.Column) And _
        (target.Row >= scanCell.Row - 1) And _
        (target.Row <= scanCell.Row + 4)
End Function

'------------------------------------------------------------------------------
' Procedure: ScheduleQueuedScanProcessor
' Scope: Private Sub
'
' What it does:
'   Handles queue/request state used by the shared ScanQueue workflow for
'   ScheduleQueuedScanProcessor.
'
' Why it exists:
'   Queue state must be tracked carefully so buffered intake scans, master
'   processing, retries, and final results stay aligned.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ScheduleQueuedScanProcessor()
    'No local queue processor in scanner-only workbooks.
    'Scans are posted straight to Power Automate in EnqueueScanRecord.
End Sub

'------------------------------------------------------------------------------
' Procedure: ProcessQueuedScansInternal
' Scope: Public Sub
'
' What it does:
'   Handles queue/request state used by the shared ScanQueue workflow for
'   ProcessQueuedScansInternal.
'
' Why it exists:
'   Queue state must be tracked carefully so buffered intake scans, master
'   processing, retries, and final results stay aligned.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub ProcessQueuedScansInternal()
    Dim qWs As Worksheet
    Dim dataWs As Worksheet
    Dim uiWs As Worksheet
    Dim uiScan As Range
    Dim uiScanAddr As String
    Dim sourceSheetName As String
    Dim mode As String
    Dim barcodeText As String
    Dim queueRow As Long
    Dim lastMatchRow As Long
    Dim lastMode As String
    Dim lastMatchedSheet As Worksheet

    Dim oldEvents As Boolean
    Dim oldScreen As Boolean
    Dim oldAlerts As Boolean

    If mScanQueueProcessorRunning Then Exit Sub

    mScanQueueProcessorRunning = True
    mScanQueueProcessorScheduled = False

    oldEvents = Application.EnableEvents
    oldScreen = Application.ScreenUpdating
    oldAlerts = Application.DisplayAlerts

    Application.EnableEvents = False
    Application.ScreenUpdating = False
    Application.DisplayAlerts = False
    Application.MoveAfterReturn = False
    Application.StatusBar = "Processing queued scans..."

    Set dataWs = ThisWorkbook.Worksheets(DATA_SHEET_NAME)
    Set qWs = GetOrCreateScanQueueSheet()

    UnprotectAllOperationalSheets
    ScannerValidation.EnsureScanLayout dataWs
    HarvestAllLiveScanZonesToQueueSheet

    lastMatchRow = 0
    lastMode = vbNullString

    Do
        'Sweep any spillover scans back into the queue first
        HarvestAllLiveScanZonesToQueueSheet

        queueRow = GetNextQueuedScanRow(qWs)
        If queueRow = 0 Then Exit Do

        sourceSheetName = Trim$(CStr(qWs.Cells(queueRow, 2).Value))
        mode = UCase$(Trim$(CStr(qWs.Cells(queueRow, 3).Value)))
        barcodeText = NormalizeScan(CStr(qWs.Cells(queueRow, 4).Value))

        qWs.Range("A" & queueRow & ":E" & queueRow).ClearContents

        If IsBarcodeLikeScan(barcodeText) Then
            Set uiWs = Nothing

            On Error Resume Next
            Set uiWs = ThisWorkbook.Worksheets(sourceSheetName)
            On Error GoTo 0

            If uiWs Is Nothing Then
                Select Case mode
                    Case "STAGING"
                        Set uiWs = GetSheetIfExists(STAGING_SHEET_NAME)
                    Case "SEND"
                        Set uiWs = GetSheetIfExists(SEND_SHEET_NAME)
                    Case "RECV"
                        Set uiWs = CurrentRecvSheet()
                End Select
            End If

            If Not uiWs Is Nothing Then
                uiScanAddr = GetScanCellAddressForMode(mode)

                If Len(uiScanAddr) > 0 Then
                    Set uiScan = uiWs.Range(uiScanAddr)

                    FocusScannerCell uiWs
                    Application.StatusBar = "Processing queued scan: " & barcodeText

                    If ProcessOneQueuedBarcode(dataWs, uiWs, uiScan, barcodeText, mode, lastMatchRow) Then
                        Set lastMatchedSheet = uiWs
                        lastMode = mode
                    End If

                    'Sweep again after each scan in case more scans spilled during processing
                    HarvestAllLiveScanZonesToQueueSheet
                    FocusScannerCell uiWs
                End If
            End If
        End If

        DoEvents
        HarvestAllLiveScanZonesToQueueSheet
    Loop

    ResetScanQueueSheet

    'One final batch refresh after all queued scans are done
RefreshAllDeliveryListProcessStates dataWs

'Do NOT restyle the master Delivery List here.
'That can wipe manual pink outlines and other preserved master formatting.
RefreshAllOperationalSheets dataWs
ForceRow3HeightAll

RefreshAllTopSummaryPanels

HideStagingOnDeliveryList dataWs
SetDeliverySummaryVisibility dataWs, True

ReapplyAllStoredHighlights dataWs

'VERY IMPORTANT:
'the scanner sheets were just rebuilt/refreshed from the master,
'so reapply persistent manual-edit outlines now.
ReapplyAllManualEditMarks

RefreshAllDeliveryListProcessStates dataWs

ProtectViewOnlySheet dataWs

    'Turn repaint back on BEFORE we try to visibly jump to the scanned row
Application.ScreenUpdating = True
DoEvents

If lastMatchRow > 0 Then
    If Not lastMatchedSheet Is Nothing Then
        ShowMostRecentScannedRow lastMatchedSheet, _
                                 lastMatchedSheet.Range(GetScanCellAddressForMode(lastMode)), _
                                 lastMatchRow, _
                                 lastMode
    End If
ElseIf Not lastMatchedSheet Is Nothing Then
    FocusScannerCell lastMatchedSheet
End If

SafeExit:
    Application.StatusBar = False
    Application.DisplayAlerts = oldAlerts
    Application.ScreenUpdating = oldScreen
    Application.EnableEvents = oldEvents
    Application.MoveAfterReturn = False
    mScanQueueProcessorRunning = False
    Exit Sub
End Sub

'------------------------------------------------------------------------------
' Procedure: ExtractBarcodeMatchesFromRawText
' Scope: Private Function
'
' What it does:
'   Cleans, decodes, validates, writes, or displays barcode data for
'   ExtractBarcodeMatchesFromRawText.
'
' Why it exists:
'   The barcode is the link between the physical glass label and the
'   order/item row, so the project must parse and validate it consistently.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function ExtractBarcodeMatchesFromRawText(ByVal rawText As String) As Collection
    Dim re As Object
    Dim matches As Object
    Dim m As Object
    Dim out As Collection

    Set out = New Collection

    rawText = UCase$(CStr(rawText))
    If Len(rawText) = 0 Then
        Set ExtractBarcodeMatchesFromRawText = out
        Exit Function
    End If

    Set re = CreateObject("VBScript.RegExp")
    re.Global = True
    re.IgnoreCase = True
    re.Pattern = "T200\d{12}"

    If re.Test(rawText) Then
        Set matches = re.Execute(rawText)
        For Each m In matches
            out.Add UCase$(CStr(m.Value))
        Next m
    End If

    Set ExtractBarcodeMatchesFromRawText = out
End Function

'------------------------------------------------------------------------------
' Procedure: EnqueueBarcodesFromRawText
' Scope: Private Sub
'
' What it does:
'   Cleans, decodes, validates, writes, or displays barcode data for
'   EnqueueBarcodesFromRawText.
'
' Why it exists:
'   The barcode is the link between the physical glass label and the
'   order/item row, so the project must parse and validate it consistently.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub EnqueueBarcodesFromRawText(ByVal rawText As String, ByRef scanQueue As Collection)
    Dim found As Collection
    Dim v As Variant
    Dim normalizedSingle As String

    Set found = ExtractBarcodeMatchesFromRawText(rawText)

    If found.Count > 0 Then
        For Each v In found
            scanQueue.Add CStr(v)
        Next v
    Else
        normalizedSingle = NormalizeScan(CStr(rawText))
        If IsBarcodeLikeScan(normalizedSingle) Then
            scanQueue.Add normalizedSingle
        End If
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: QueueAdditionalBarcodesFromRange
' Scope: Private Sub
'
' What it does:
'   Cleans, decodes, validates, writes, or displays barcode data for
'   QueueAdditionalBarcodesFromRange.
'
' Why it exists:
'   The barcode is the link between the physical glass label and the
'   order/item row, so the project must parse and validate it consistently.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub QueueAdditionalBarcodesFromRange(ByVal rng As Range, ByVal currentBarcode As String, ByRef scanQueue As Collection)
    Dim found As Collection
    Dim v As Variant
    Dim skipCurrentOnce As Boolean
    Dim normalizedSingle As String

    If rng Is Nothing Then Exit Sub

    Set found = ExtractBarcodeMatchesFromRawText(CStr(rng.Value))

    If found.Count > 0 Then
        skipCurrentOnce = False

        For Each v In found
            If UCase$(CStr(v)) = UCase$(currentBarcode) And Not skipCurrentOnce Then
                skipCurrentOnce = True
            Else
                scanQueue.Add UCase$(CStr(v))
            End If
        Next v

    Else
        normalizedSingle = NormalizeScan(CStr(rng.Value))
        If IsBarcodeLikeScan(normalizedSingle) Then
            If UCase$(normalizedSingle) <> UCase$(currentBarcode) Then
                scanQueue.Add normalizedSingle
            End If
        End If
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: ProcessOneQueuedBarcode
' Scope: Private Function
'
' What it does:
'   Cleans, decodes, validates, writes, or displays barcode data for
'   ProcessOneQueuedBarcode.
'
' Why it exists:
'   The barcode is the link between the physical glass label and the
'   order/item row, so the project must parse and validate it consistently.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function ProcessOneQueuedBarcode(ByVal dataWs As Worksheet, _
                                         ByVal uiWs As Worksheet, _
                                         ByVal uiScan As Range, _
                                         ByVal barcodeText As String, _
                                         ByVal mode As String, _
                                         ByRef outMatchRow As Long) As Boolean
    Dim dataScan As Range
    Dim ord As Long
    Dim itm As Long
    Dim matchRow As Long
    Dim rowIsGreenville As Boolean
    Dim rowIsCPU As Boolean
    Dim redirectSheet As String

    If Len(barcodeText) = 0 Then Exit Function
    If Not TryCanonicalizeQueuedScan(dataWs, barcodeText, barcodeText, ord, itm) Then Exit Function

    matchRow = FindMatchRowInData(dataWs, ord, itm)

    If mode = "RECV" And matchRow > 0 Then
        rowIsGreenville = IsGreenvilleRow(dataWs, matchRow)
        rowIsCPU = IsCPURow(dataWs, matchRow)

        If rowIsCPU Then
            If UCase$(uiWs.Name) <> UCase$(CPU_SHEET_NAME) Then
                SafeClearContents uiScan
                Beep
                MsgBox "Inbound mismatch." & vbCrLf & vbCrLf & _
                       "This CPU / customer pickup order must be scanned on '" & CPU_SHEET_NAME & "'." & vbCrLf & _
                       "It cannot be received on '" & uiWs.Name & "'.", _
                       vbExclamation, "Wrong Inbound Sheet"
                Exit Function
            End If

        ElseIf UCase$(uiWs.Name) = UCase$(CPU_SHEET_NAME) Then
            If rowIsGreenville Then
                redirectSheet = GREENVILLE_RECV_SHEET_NAME
            Else
                redirectSheet = CurrentRecvSheetName()
            End If

            SafeClearContents uiScan
            Beep
            MsgBox "Inbound mismatch." & vbCrLf & vbCrLf & _
                   "This order is not a CPU / customer pickup order." & vbCrLf & _
                   "Please scan it on '" & redirectSheet & "'.", _
                   vbExclamation, "Wrong Inbound Sheet"
            Exit Function

        ElseIf rowIsGreenville And UCase$(uiWs.Name) = UCase$(CurrentRecvSheetName()) Then
            SafeClearContents uiScan
            Beep
            MsgBox "Inbound mismatch." & vbCrLf & vbCrLf & _
                   "This Greenville order must be scanned on '" & GREENVILLE_RECV_SHEET_NAME & "'." & vbCrLf & _
                   "It cannot be received on '" & CurrentRecvSheetName() & "'.", _
                   vbExclamation, "Wrong Inbound Sheet"
            Exit Function

        ElseIf (Not rowIsGreenville) And UCase$(uiWs.Name) = UCase$(GREENVILLE_RECV_SHEET_NAME) Then
            SafeClearContents uiScan
            Beep
            MsgBox "Inbound mismatch." & vbCrLf & vbCrLf & _
                   "This order is not a Greenville order." & vbCrLf & _
                   "Please scan it on '" & CurrentRecvSheetName() & "'.", _
                   vbExclamation, "Wrong Inbound Sheet"
            Exit Function
        End If
    End If

    uiScan.Value = barcodeText

    Select Case mode
        Case "STAGING"
            Set dataScan = dataWs.Range(ScannerValidation.SCAN_CELL_STAGING)
        Case "SEND"
            Set dataScan = dataWs.Range(ScannerValidation.SCAN_CELL_SEND)
        Case "RECV"
            Set dataScan = dataWs.Range(ScannerValidation.SCAN_CELL_RECV)
        Case Else
            Exit Function
    End Select

    RemoveActionButtonsFromScannerSheets

    dataScan.Value = barcodeText
    ScannerValidation.ProcessScan dataWs, barcodeText, mode

    matchRow = FindMatchRowInData(dataWs, ord, itm)

    If matchRow > 0 Then
        SaveStoredHighlightRow dataWs, matchRow
        SaveStoredHighlightRow uiWs, matchRow
        UpdateDeliveryProcessStateForRow dataWs, matchRow
        outMatchRow = matchRow
    End If

    ProcessOneQueuedBarcode = True
End Function

'------------------------------------------------------------------------------
' Procedure: PullNextRapidScanCandidate
' Scope: Private Function
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   PullNextRapidScanCandidate.
'
' Why it exists:
'   Delivery timing, queue timestamps, and scan timestamps drive status
'   messages such as Early, On-Time, Late, Processing, and Done.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function PullNextRapidScanCandidate(ByVal primaryCell As Range, _
                                            ByVal scanCell As Range, _
                                            ByVal currentScan As String) As String
    Dim candidate As String

    On Error Resume Next

    If Not scanCell Is Nothing Then
        candidate = NormalizeScan(CStr(scanCell.Value))
        If Len(candidate) > 0 Then
            If IsBarcodeLikeScan(candidate) Then
                If UCase$(candidate) <> UCase$(currentScan) Then
                    SafeClearContents scanCell
                    PullNextRapidScanCandidate = candidate
                    Exit Function
                End If
            End If
        End If
    End If

    If Not primaryCell Is Nothing Then
        candidate = NormalizeScan(CStr(primaryCell.Value))
        If Len(candidate) > 0 Then
            If IsBarcodeLikeScan(candidate) Then
                If UCase$(candidate) <> UCase$(currentScan) Then
                    SafeClearContents primaryCell
                    PullNextRapidScanCandidate = candidate
                    Exit Function
                End If
            End If
        End If
    End If

    On Error GoTo 0
End Function

'------------------------------------------------------------------------------
' Procedure: IsBarcode
' Scope: Private Function
'
' What it does:
'   Cleans, decodes, validates, writes, or displays barcode data for
'   IsBarcode.
'
' Why it exists:
'   The barcode is the link between the physical glass label and the
'   order/item row, so the project must parse and validate it consistently.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function IsBarcode(ByVal s As String) As Boolean
    IsBarcode = (Len(s) = 16 And s Like "T200############")
End Function

Private Function IsBarcodeLikeScan(ByVal s As String) As Boolean
    Dim normalizedText As String
    Dim digitsOnly As String

    normalizedText = NormalizeScan(s)

    If IsBarcode(normalizedText) Then
        IsBarcodeLikeScan = True
        Exit Function
    End If

    If Left$(normalizedText, 1) <> "T" Then Exit Function

    digitsOnly = ScanDigitsOnly(normalizedText)
    IsBarcodeLikeScan = (Len(digitsOnly) >= 9)
End Function

Private Function TryCanonicalizeQueuedScan(ByVal ws As Worksheet, _
                                           ByVal rawScan As String, _
                                           ByRef canonicalBarcode As String, _
                                           ByRef orderNumber As Long, _
                                           ByRef itemNumber As Long) As Boolean
    Dim normalizedText As String
    Dim recoveryMessage As String

    normalizedText = NormalizeScan(rawScan)

    If Not ws Is Nothing Then
        If ScannerValidation.TryCanonicalizeScanForSheet(ws, normalizedText, canonicalBarcode, orderNumber, itemNumber, recoveryMessage) Then
            TryCanonicalizeQueuedScan = True
            Exit Function
        End If
    End If

    If IsBarcode(normalizedText) Then
        canonicalBarcode = normalizedText
        orderNumber = CLng(Mid$(normalizedText, 5, 6))
        itemNumber = CLng(Mid$(normalizedText, 11, 3))
        TryCanonicalizeQueuedScan = (orderNumber > 0 And itemNumber > 0)
    End If
End Function

Private Function ScanDigitsOnly(ByVal valueText As String) As String
    Dim i As Long
    Dim ch As String

    For i = 1 To Len(valueText)
        ch = Mid$(valueText, i, 1)
        If ch Like "[0-9]" Then ScanDigitsOnly = ScanDigitsOnly & ch
    Next i
End Function

'------------------------------------------------------------------------------
' Procedure: SyncScannerFromMain
' Scope: Private Sub
'
' What it does:
'   Performs the workbook-specific step named SyncScannerFromMain inside
'   ThisWorkbook_Master.
'
' Why it exists:
'   Excel events are the only place to intercept open/close, sheet changes,
'   selection changes, and edit-mode transitions reliably.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub SyncScannerFromMain(ByVal dataWs As Worksheet, ByVal uiWs As Worksheet)
    Dim lastRow As Long
    Dim oldLastRow As Long
    Dim firstSyncRow As Long
    Dim clearStartRow As Long

    lastRow = GetLastUsedRow(dataWs)
    oldLastRow = GetLastUsedRow(uiWs)

    'Preserve the local banner/title area on scanner sheets.
    'Row 2 = top summaries
    'Row 3 = scanner sheet title/location banner
    If UCase$(uiWs.Name) = UCase$(DATA_SHEET_NAME) Then
        firstSyncRow = 1
    Else
        firstSyncRow = 4
    End If

    clearStartRow = firstSyncRow
    If clearStartRow < 1 Then clearStartRow = 1

    If oldLastRow >= clearStartRow Then
        If oldLastRow > lastRow And lastRow >= clearStartRow Then
            uiWs.Range("A" & (lastRow + 1) & ":AV" & oldLastRow).Clear
        ElseIf lastRow < clearStartRow Then
            uiWs.Range("A" & clearStartRow & ":AV" & oldLastRow).Clear
        End If
    End If

    If lastRow < firstSyncRow Then Exit Sub

    dataWs.Range("A" & firstSyncRow & ":AV" & lastRow).Copy
    uiWs.Range("A" & firstSyncRow).PasteSpecial xlPasteAll
    Application.CutCopyMode = False
End Sub

'------------------------------------------------------------------------------
' Procedure: GetLastUsedRow
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   GetLastUsedRow.
'
' Why it exists:
'   Rows may represent real orders, section headers, remakes, Greenville work,
'   Customer Pickup work, or updated rows; each type needs different handling.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetLastUsedRow(ByVal ws As Worksheet) As Long
    Dim f As Range
    Set f = ws.Cells.Find(What:="*", LookIn:=xlFormulas, SearchOrder:=xlByRows, SearchDirection:=xlPrevious)

    If f Is Nothing Then
        GetLastUsedRow = 0
    Else
        GetLastUsedRow = f.Row
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: ProtectLockColumnsAtoN
' Scope: Private Sub
'
' What it does:
'   Controls worksheet/workbook protection or read-only safety behavior for
'   ProtectLockColumnsAtoN.
'
' Why it exists:
'   Protection keeps operators from accidentally editing formula/layout areas
'   while still allowing the intended scan or comment cells to work.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ProtectLockColumnsAtoN(ByVal ws As Worksheet)
    Dim lastRow As Long
    Dim unlockRng As Range
    Dim lockRng As Range

    On Error Resume Next
    ws.Unprotect Password:=""
    On Error GoTo 0

    lastRow = GetLastUsedRow(ws)
    If lastRow < 1 Then lastRow = 1

    Set unlockRng = ws.UsedRange
    Set lockRng = ws.Range("A1:N" & lastRow)

    On Error Resume Next
    If Not unlockRng Is Nothing Then unlockRng.Locked = False
    If Not lockRng Is Nothing Then lockRng.Locked = True
    ws.rows("1:2").Locked = True
    On Error GoTo 0

    If ws.Name = DATA_SHEET_NAME Then
        ws.EnableSelection = xlNoSelection
    Else
        ws.EnableSelection = xlUnlockedCells
    End If

    ApplyOperationalFreezePane ws

    ws.Protect Password:="", UserInterfaceOnly:=True, DrawingObjects:=False, Contents:=True, Scenarios:=True
End Sub

'------------------------------------------------------------------------------
' Procedure: ProtectViewOnlySheet
' Scope: Private Sub
'
' What it does:
'   Controls worksheet/workbook protection or read-only safety behavior for
'   ProtectViewOnlySheet.
'
' Why it exists:
'   Protection keeps operators from accidentally editing formula/layout areas
'   while still allowing the intended scan or comment cells to work.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ProtectViewOnlySheet(ByVal ws As Worksheet)
    On Error Resume Next
    ws.Unprotect Password:=""
    On Error GoTo 0

    On Error Resume Next
    ws.UsedRange.Locked = True
    On Error GoTo 0

    If ws.Name = DATA_SHEET_NAME Then
        ws.EnableSelection = xlNoSelection
        ApplyOperationalFreezePane ws
    Else
        ws.EnableSelection = xlUnlockedCells
    End If

    ws.Protect Password:="", UserInterfaceOnly:=True, DrawingObjects:=False, Contents:=True, Scenarios:=True
End Sub

'------------------------------------------------------------------------------
' Procedure: ForceRow3Height
' Scope: Private Sub
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   ForceRow3Height.
'
' Why it exists:
'   Rows may represent real orders, section headers, remakes, Greenville work,
'   Customer Pickup work, or updated rows; each type needs different handling.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ForceRow3Height(ByVal ws As Worksheet)
    If ws Is Nothing Then Exit Sub

    On Error Resume Next
    ws.rows(3).RowHeight = 55
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: ForceRow3HeightAll
' Scope: Private Sub
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   ForceRow3HeightAll.
'
' Why it exists:
'   Rows may represent real orders, section headers, remakes, Greenville work,
'   Customer Pickup work, or updated rows; each type needs different handling.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ForceRow3HeightAll()
    ForceRow3Height ThisWorkbook.Worksheets(DATA_SHEET_NAME)
    ForceRow3Height ThisWorkbook.Worksheets(STAGING_SHEET_NAME)
    ForceRow3Height ThisWorkbook.Worksheets(SEND_SHEET_NAME)

    If Not CurrentRecvSheet() Is Nothing Then
        ForceRow3Height CurrentRecvSheet()
    End If

    If GreenvilleSheetExists() Then
        ForceRow3Height ThisWorkbook.Worksheets(GREENVILLE_RECV_SHEET_NAME)
    End If

    If CPUSheetExists() Then
        ForceRow3Height ThisWorkbook.Worksheets(CPU_SHEET_NAME)
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: ResetActivatedSheetView
' Scope: Private Sub
'
' What it does:
'   Controls the active sheet/window view, freeze panes, navigation, or
'   selected cell for ResetActivatedSheetView.
'
' Why it exists:
'   The workbook is used by scanners/operators, so opening the right view and
'   scan area reduces missed scans and operator confusion.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ResetActivatedSheetView(ByVal Sh As Object)
    If Sh Is Nothing Then Exit Sub

    On Error Resume Next

    If Not ActiveWindow Is Nothing Then
        ActiveWindow.ScrollRow = 1
        ActiveWindow.ScrollColumn = 1
    End If

    Select Case UCase$(Sh.Name)
        Case UCase$("Utility Panel")
            Application.GoTo Sh.Range("A1"), False

        Case UCase$(DATA_SHEET_NAME)
            Application.GoTo Sh.Range("A6"), False

        Case UCase$(STAGING_SHEET_NAME), _
             UCase$(SEND_SHEET_NAME), _
             UCase$(CurrentRecvSheetName()), _
             UCase$(GREENVILLE_RECV_SHEET_NAME), _
             UCase$(CPU_SHEET_NAME)

            FocusScannerCell Sh
    End Select

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: ShouldRunFirstViewReset
' Scope: Private Function
'
' What it does:
'   Controls the active sheet/window view, freeze panes, navigation, or
'   selected cell for ShouldRunFirstViewReset.
'
' Why it exists:
'   The workbook is used by scanners/operators, so opening the right view and
'   scan area reduces missed scans and operator confusion.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function ShouldRunFirstViewReset(ByVal sheetName As String) As Boolean
    Dim key As String

    key = UCase$(Trim$(sheetName))

    If mFirstViewResetDone Is Nothing Then
        Set mFirstViewResetDone = CreateObject("Scripting.Dictionary")
    End If

    If Not mFirstViewResetDone.Exists(key) Then
        mFirstViewResetDone.Add key, True
        ShouldRunFirstViewReset = True
    Else
        ShouldRunFirstViewReset = False
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: ResetFirstViewResetFlag
' Scope: Private Sub
'
' What it does:
'   Controls the active sheet/window view, freeze panes, navigation, or
'   selected cell for ResetFirstViewResetFlag.
'
' Why it exists:
'   The workbook is used by scanners/operators, so opening the right view and
'   scan area reduces missed scans and operator confusion.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ResetFirstViewResetFlag(ByVal sheetName As String)
    Dim key As String

    key = UCase$(Trim$(sheetName))

    If mFirstViewResetDone Is Nothing Then
        Set mFirstViewResetDone = CreateObject("Scripting.Dictionary")
    End If

    If mFirstViewResetDone.Exists(key) Then
        mFirstViewResetDone.Remove key
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: Workbook_SheetActivate
' Scope: Private Sub
'
' What it does:
'   Runs sheet-specific view, protection, and instruction logic whenever the
'   operator switches tabs.
'
' Why it exists:
'   Different operational sheets need different gridline/freeze/protection
'   behavior, and this centralizes that tab-switch behavior.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub Workbook_SheetActivate(ByVal Sh As Object)
    On Error GoTo SafeExit

    If mIsShowingScannedRow Then Exit Sub

    If Sh.Name <> DATA_SHEET_NAME Then
        If Not HandleDeliveryListEditExit(Sh.Name) Then Exit Sub
    End If

    If Sh.Name = "Utility Panel" Then
        If Not ActiveWindow Is Nothing Then
            ActiveWindow.DisplayGridlines = False
        End If

        If ShouldRunFirstViewReset(Sh.Name) Then
            If Not ActiveWindow Is Nothing Then
                ActiveWindow.ScrollRow = 1
                ActiveWindow.ScrollColumn = 1
            End If
            Application.GoTo Sh.Range("A1"), False
        End If

    ElseIf Sh.Name = DATA_SHEET_NAME Or _
            Sh.Name = STAGING_SHEET_NAME Or _
            Sh.Name = SEND_SHEET_NAME Or _
            Sh.Name = CurrentRecvSheetName() Or _
            Sh.Name = GREENVILLE_RECV_SHEET_NAME Or _
            Sh.Name = CPU_SHEET_NAME Then

        If Not ActiveWindow Is Nothing Then
            ActiveWindow.DisplayGridlines = True
        End If

        StabilizeOperationalSheetOnActivate Sh
        ShowScanInstructionsOnce
    End If

SafeExit:
End Sub

'------------------------------------------------------------------------------
' Procedure: AutoFitCommentColumns
' Scope: Private Sub
'
' What it does:
'   Finds, sizes, hides, formats, or uses worksheet columns for
'   AutoFitCommentColumns.
'
' Why it exists:
'   The system depends on fixed scan blocks and discovered delivery-list
'   columns, so column handling must be centralized and predictable.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub AutoFitCommentColumns(ByVal ws As Worksheet)
    Const STAGING_COMMENT_COL As String = "AV"
    Const SEND_COMMENT_COL As String = "W"
    Const RECV_COMMENT_COL As String = "AF"
    Const MIN_WIDTH As Double = 20
    Const MAX_WIDTH As Double = 80

    Dim stagingWasHidden As Boolean
    Dim sendWasHidden As Boolean
    Dim recvWasHidden As Boolean

    On Error Resume Next

    stagingWasHidden = ws.Columns(STAGING_COMMENT_COL).Hidden
    sendWasHidden = ws.Columns(SEND_COMMENT_COL).Hidden
    recvWasHidden = ws.Columns(RECV_COMMENT_COL).Hidden

    ws.Columns(STAGING_COMMENT_COL).Hidden = False
    ws.Columns(SEND_COMMENT_COL).Hidden = False
    ws.Columns(RECV_COMMENT_COL).Hidden = False

    ws.Columns(STAGING_COMMENT_COL).AutoFit
    If ws.Columns(STAGING_COMMENT_COL).ColumnWidth < MIN_WIDTH Then ws.Columns(STAGING_COMMENT_COL).ColumnWidth = MIN_WIDTH
    If ws.Columns(STAGING_COMMENT_COL).ColumnWidth > MAX_WIDTH Then ws.Columns(STAGING_COMMENT_COL).ColumnWidth = MAX_WIDTH

    ws.Columns(SEND_COMMENT_COL).AutoFit
    If ws.Columns(SEND_COMMENT_COL).ColumnWidth < MIN_WIDTH Then ws.Columns(SEND_COMMENT_COL).ColumnWidth = MIN_WIDTH
    If ws.Columns(SEND_COMMENT_COL).ColumnWidth > MAX_WIDTH Then ws.Columns(SEND_COMMENT_COL).ColumnWidth = MAX_WIDTH

    ws.Columns(RECV_COMMENT_COL).AutoFit
    If ws.Columns(RECV_COMMENT_COL).ColumnWidth < MIN_WIDTH Then ws.Columns(RECV_COMMENT_COL).ColumnWidth = MIN_WIDTH
    If ws.Columns(RECV_COMMENT_COL).ColumnWidth > MAX_WIDTH Then ws.Columns(RECV_COMMENT_COL).ColumnWidth = MAX_WIDTH

    ws.Columns(STAGING_COMMENT_COL).Hidden = stagingWasHidden
    ws.Columns(SEND_COMMENT_COL).Hidden = sendWasHidden
    ws.Columns(RECV_COMMENT_COL).Hidden = recvWasHidden

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: SetDeliverySummaryVisibility
' Scope: Private Sub
'
' What it does:
'   Calculates or updates summary/banner information shown at the top of
'   delivery/scanner sheets for SetDeliverySummaryVisibility.
'
' Why it exists:
'   Operators use those summary panels to quickly see staged, outbound,
'   inbound, and completion progress without manually counting rows.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub SetDeliverySummaryVisibility(ByVal ws As Worksheet, ByVal showIt As Boolean)
    Dim lo As ListObject
    Dim nm As String
    Dim foundOne As Boolean
    Dim wasProtected As Boolean

    wasProtected = ws.ProtectContents

    On Error Resume Next
    ws.Unprotect Password:=""
    On Error GoTo 0

    If ws.Name = DATA_SHEET_NAME Then showIt = True

    For Each lo In ws.ListObjects
        nm = UCase$(lo.Name & " " & lo.displayName)

        If InStr(1, nm, "DELIVERYSUMMARY", vbTextCompare) > 0 Then
            lo.Range.EntireRow.Hidden = Not showIt
            foundOne = True
        End If
    Next lo

    If ws.Name = DATA_SHEET_NAME And Not foundOne Then
        ws.rows.Hidden = False
    End If

    If ws.Name = DATA_SHEET_NAME And wasProtected And Not IsDeliveryEditModeOn() Then
        ProtectViewOnlySheet ws
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: EnableDeliveryListEditMode
' Scope: Private Sub
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   EnableDeliveryListEditMode.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub EnableDeliveryListEditMode(ByVal ws As Worksheet)
    On Error Resume Next
    ws.Unprotect Password:=""
    On Error GoTo 0

    ws.Tab.Color = RGB(255, 192, 0)
    SetDeliveryEditMode True
End Sub

'------------------------------------------------------------------------------
' Procedure: DisableDeliveryListEditMode
' Scope: Private Sub
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   DisableDeliveryListEditMode.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub DisableDeliveryListEditMode(ByVal ws As Worksheet)
    ProtectViewOnlySheet ws
    ws.Tab.ColorIndex = xlColorIndexNone
    SetDeliveryEditMode False
End Sub

'------------------------------------------------------------------------------
' Procedure: GetChangeAuditSheet
' Scope: Private Function
'
' What it does:
'   Finds, creates, deletes, rebuilds, protects, or synchronizes worksheets
'   for GetChangeAuditSheet.
'
' Why it exists:
'   The master workbook creates multiple operational views from one delivery
'   list; worksheet helpers keep those views from drifting apart.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetChangeAuditSheet() As Worksheet
    Dim ws As Worksheet

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets("__ChangeAudit")
    On Error GoTo 0

    If ws Is Nothing Then
        Set ws = ThisWorkbook.Worksheets.Add(After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
        ws.Name = "__ChangeAudit"

        ws.Range("A1").Value = "CurrentChangeKey"
        ws.Range("B1").Value = "ChangedBy"
        ws.Range("C1").Value = "ChangedAt"

        ws.Range("A5").Value = "User"
        ws.Range("B5").Value = "SeenChangeKey"

        ws.Visible = xlSheetVeryHidden
    End If

    Set GetChangeAuditSheet = ws
End Function

'------------------------------------------------------------------------------
' Procedure: EnsureChangeAuditSheet
' Scope: Private Sub
'
' What it does:
'   Finds, creates, deletes, rebuilds, protects, or synchronizes worksheets
'   for EnsureChangeAuditSheet.
'
' Why it exists:
'   The master workbook creates multiple operational views from one delivery
'   list; worksheet helpers keep those views from drifting apart.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub EnsureChangeAuditSheet()
    Dim ws As Worksheet
    Set ws = GetChangeAuditSheet()
End Sub

'------------------------------------------------------------------------------
' Procedure: GetCurrentUserName
' Scope: Private Function
'
' What it does:
'   Returns a workbook object, setting, status value, parsed value, or
'   calculated result used by other procedures (GetCurrentUserName).
'
' Why it exists:
'   Using one getter keeps callers from duplicating lookup logic and protects
'   them from missing sheets, missing names, or blank values.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetCurrentUserName() As String
    GetCurrentUserName = Trim$(Environ$("Username"))
    If Len(GetCurrentUserName) = 0 Then
        GetCurrentUserName = Trim$(Application.userName)
    End If
    If Len(GetCurrentUserName) = 0 Then
        GetCurrentUserName = "Unknown User"
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: RegisterManualChange
' Scope: Private Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   RegisterManualChange.
'
' Why it exists:
'   Remakes need separate visual and print/export handling so replacement
'   glass is not confused with regular delivery-list work.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub RegisterManualChange()
    Dim ws As Worksheet
    Dim changeKey As String

    Set ws = GetChangeAuditSheet()

    changeKey = Format$(Now, "yyyymmdd_hhnnss")

    ws.Range("A2").Value = changeKey
    ws.Range("B2").Value = GetCurrentUserName()
    ws.Range("C2").Value = Format$(Now, "m/d/yyyy h:mm AM/PM")

    lastManualChangeKey = changeKey
End Sub

'------------------------------------------------------------------------------
' Procedure: ShowManualChangeNoticeIfNeeded
' Scope: Private Sub
'
' What it does:
'   Builds or displays the operator-facing notice/message used by
'   ShowManualChangeNoticeIfNeeded.
'
' Why it exists:
'   The scanner/master workflow must tell operators when processing is paused,
'   blocked, failed, or waiting so they do not keep scanning into an unsafe
'   state.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ShowManualChangeNoticeIfNeeded()
    Dim ws As Worksheet
    Dim changeKey As String
    Dim changedBy As String
    Dim changedAt As String

    If currentChangeNoticeShown Then Exit Sub

    Set ws = GetChangeAuditSheet()

    changeKey = Trim$(CStr(ws.Range("A2").Value))
    changedBy = Trim$(CStr(ws.Range("B2").Value))
    changedAt = Trim$(CStr(ws.Range("C2").Value))

    If Len(changeKey) = 0 Then Exit Sub
    If HasUserAlreadySeenChange(changeKey) Then Exit Sub

    currentChangeNoticeShown = True
    lastManualChangeKey = changeKey

    MsgBox "Manual changes have been made to the Delivery List." & vbCrLf & vbCrLf & _
       "Changed by: " & changedBy & vbCrLf & _
       "Changed at: " & changedAt & vbCrLf & vbCrLf & _
       "Manual edits will appear outlined in pink.", _
       vbExclamation, "Change Notice"

    MarkUserAsHavingSeenChange changeKey
End Sub

'------------------------------------------------------------------------------
' Procedure: HasUserAlreadySeenChange
' Scope: Private Function
'
' What it does:
'   Returns a True/False decision used by higher-level workflow code
'   (HasUserAlreadySeenChange).
'
' Why it exists:
'   Boolean helpers make business rules readable and keep condition checks
'   consistent across modules.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function HasUserAlreadySeenChange(ByVal changeKey As String) As Boolean
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim r As Long
    Dim userName As String

    Set ws = GetChangeAuditSheet()
    userName = GetCurrentUserName()

    lastRow = ws.Cells(ws.rows.Count, 1).End(xlUp).Row
    If lastRow < 6 Then Exit Function

    For r = 6 To lastRow
        If StrComp(CStr(ws.Cells(r, 1).Value), userName, vbTextCompare) = 0 Then
            If StrComp(CStr(ws.Cells(r, 2).Value), changeKey, vbTextCompare) = 0 Then
                HasUserAlreadySeenChange = True
                Exit Function
            End If
        End If
    Next r
End Function

'------------------------------------------------------------------------------
' Procedure: MarkUserAsHavingSeenChange
' Scope: Private Sub
'
' What it does:
'   Performs the workbook-specific step named MarkUserAsHavingSeenChange
'   inside ThisWorkbook_Master.
'
' Why it exists:
'   Excel events are the only place to intercept open/close, sheet changes,
'   selection changes, and edit-mode transitions reliably.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub MarkUserAsHavingSeenChange(ByVal changeKey As String)
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim r As Long
    Dim userName As String

    Set ws = GetChangeAuditSheet()
    userName = GetCurrentUserName()

    lastRow = ws.Cells(ws.rows.Count, 1).End(xlUp).Row
    If lastRow < 6 Then lastRow = 5

    For r = 6 To lastRow
        If StrComp(CStr(ws.Cells(r, 1).Value), userName, vbTextCompare) = 0 Then
            ws.Cells(r, 2).Value = changeKey
            Exit Sub
        End If
    Next r

    ws.Cells(lastRow + 1, 1).Value = userName
    ws.Cells(lastRow + 1, 2).Value = changeKey
End Sub

'------------------------------------------------------------------------------
' Procedure: RemoveActionButtonsFromScannerSheets
' Scope: Private Sub
'
' What it does:
'   Builds, formats, deletes, or wires workbook UI shapes/buttons/panels for
'   RemoveActionButtonsFromScannerSheets.
'
' Why it exists:
'   Buttons and utility panels are the operator-facing control surface, so
'   they must be rebuilt consistently after imports or sheet refreshes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub RemoveActionButtonsFromScannerSheets()
    RemoveActionButtonsFromSheet ThisWorkbook.Worksheets(STAGING_SHEET_NAME)
    RemoveActionButtonsFromSheet ThisWorkbook.Worksheets(SEND_SHEET_NAME)
    RemoveActionButtonsFromSheet CurrentRecvSheet()

    If GreenvilleSheetExists() Then
        RemoveActionButtonsFromSheet ThisWorkbook.Worksheets(GREENVILLE_RECV_SHEET_NAME)
    End If

    If CPUSheetExists() Then
        RemoveActionButtonsFromSheet ThisWorkbook.Worksheets(CPU_SHEET_NAME)
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: RemoveActionButtonsFromSheet
' Scope: Private Sub
'
' What it does:
'   Builds, formats, deletes, or wires workbook UI shapes/buttons/panels for
'   RemoveActionButtonsFromSheet.
'
' Why it exists:
'   Buttons and utility panels are the operator-facing control surface, so
'   they must be rebuilt consistently after imports or sheet refreshes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub RemoveActionButtonsFromSheet(ByVal ws As Worksheet)
    On Error Resume Next
    ws.Shapes("btnImportDeliveryList").Delete
    ws.Shapes("btnSaveForSharePoint").Delete
    ws.Shapes("btnSyncScannerSheets").Delete
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: IsDeliveryEditModeOn
' Scope: Private Function
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   IsDeliveryEditModeOn.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function IsDeliveryEditModeOn() As Boolean
    Dim s As String

    On Error Resume Next
    s = CStr(ThisWorkbook.names("_DeliveryEditMode").RefersTo)
    On Error GoTo 0

    s = Replace$(s, "=", "")
    s = UCase$(Trim$(s))

    IsDeliveryEditModeOn = (s = "TRUE")
End Function

'------------------------------------------------------------------------------
' Procedure: SetDeliveryEditMode
' Scope: Private Sub
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   SetDeliveryEditMode.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub SetDeliveryEditMode(ByVal isOn As Boolean)
    On Error Resume Next
    ThisWorkbook.names("_DeliveryEditMode").Delete
    On Error GoTo 0

    If isOn Then
        ThisWorkbook.names.Add Name:="_DeliveryEditMode", RefersTo:="=TRUE"
        mManualEditsPending = False
    Else
        ThisWorkbook.names.Add Name:="_DeliveryEditMode", RefersTo:="=FALSE"
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: ShowScanInstructionsOnce
' Scope: Private Sub
'
' What it does:
'   Shows an operator message, form, panel, or selected sheet for
'   ShowScanInstructionsOnce.
'
' Why it exists:
'   The workflow uses visible prompts/forms to prevent silent failures and
'   guide the operator during scanning and master processing.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ShowScanInstructionsOnce()
    'Scanner instruction popup disabled.
    'Users already know the workflow, and popups can interrupt scanning.
    shownScanInstructionsPopup = True
End Sub

'------------------------------------------------------------------------------
' Procedure: ResetManualChangeNotice
' Scope: Private Sub
'
' What it does:
'   Builds or displays the operator-facing notice/message used by
'   ResetManualChangeNotice.
'
' Why it exists:
'   The scanner/master workflow must tell operators when processing is paused,
'   blocked, failed, or waiting so they do not keep scanning into an unsafe
'   state.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ResetManualChangeNotice()
    Dim ws As Worksheet

    Set ws = GetChangeAuditSheet()

    ws.Range("A2:C2").ClearContents
End Sub

'------------------------------------------------------------------------------
' Procedure: HasPendingDeliveryListEdits
' Scope: Private Function
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   HasPendingDeliveryListEdits.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function HasPendingDeliveryListEdits() As Boolean
    HasPendingDeliveryListEdits = mManualEditsPending
End Function

'------------------------------------------------------------------------------
' Procedure: SetPendingDeliveryListEdits
' Scope: Private Sub
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   SetPendingDeliveryListEdits.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub SetPendingDeliveryListEdits(ByVal isPending As Boolean)
    mManualEditsPending = isPending
End Sub

'------------------------------------------------------------------------------
' Procedure: ReboldDeliveryListHeaders
' Scope: Private Sub
'
' What it does:
'   Finds, writes, validates, or uses worksheet header cells for
'   ReboldDeliveryListHeaders.
'
' Why it exists:
'   Header locations can move during import/rebuild, so the code uses header
'   discovery to target the correct columns instead of guessing.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ReboldDeliveryListHeaders(ByVal ws As Worksheet)
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim hdrRow As Long
    Dim orderCol As Long
    Dim itemCol As Long
    Dim firstRow As Long
    Dim lastRow As Long
    Dim r As Long

    Set orderHdr = FindHeaderCellInCols(ws, Array(HDR_ORDER), "A:N", 250)
    Set itemHdr = FindHeaderCellInCols(ws, Array(HDR_ITEM), "A:N", 250)

    If orderHdr Is Nothing Or itemHdr Is Nothing Then Exit Sub

    hdrRow = orderHdr.Row
    orderCol = orderHdr.Column
    itemCol = itemHdr.Column
    firstRow = hdrRow + 1
    lastRow = ws.Cells(ws.rows.Count, orderCol).End(xlUp).Row

    With ws.Range("A" & hdrRow & ":N" & hdrRow)
        .Font.Bold = True
    End With

    For r = firstRow To lastRow
        If IsSectionHeaderRowLocal(ws, r, orderCol, itemCol) Then
            ws.Range("A" & r & ":J" & r).Font.Bold = True
        End If
    Next r
End Sub

'------------------------------------------------------------------------------
' Procedure: Workbook_BeforeClose
' Scope: Private Sub
'
' What it does:
'   Cleans up scheduled tasks and workbook-level state before Excel closes the
'   master workbook.
'
' Why it exists:
'   Without cleanup, Application.OnTime callbacks and stale heartbeat state
'   can remain after the operator thinks the master is closed.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub Workbook_BeforeClose(Cancel As Boolean)
    On Error Resume Next
    Application.MoveAfterReturn = mPrevMoveAfterReturn
    Application.MoveAfterReturnDirection = mPrevMoveAfterReturnDirection
    StopExternalQueueProcessor
    On Error GoTo 0
End Sub



