Attribute VB_Name = "modStageSnapshot"
Option Explicit

'==============================================================================
' Module: modStageSnapshot
' Workbook: Intake_Scanning_Test.xlsm / Intake scanner workbook
'
' What this module does:
'   Loads and manages the imported stage snapshot shown to the intake
'   operator. It reconstructs sheets from SharePoint snapshot JSON, applies
'   local scan changes, tracks queue state, and protects editable cells.
'
' Why this module exists:
'   Intake stations should not open or edit the master workbook directly. This
'   module lets them scan against a published snapshot while keeping local UI
'   state clear and recoverable.
'
' Commenting standard used in this rewrite:
'   Comments explain both what each procedure/section does and why it
'   matters to the scanning, SharePoint, Power Automate, buffering, and
'   operator-safety workflow. The code behavior and public procedure names
'   are intentionally kept stable so existing buttons/forms/timers keep working.
'==============================================================================


'modStageSnapshot'

Private Const COMMENT_BASELINE_COL As Long = 50   'AX stores original comment snapshot

Private Const COMMENT_SET_PREFIX As String = "__COMMENT_SET__|"

Private Const STAGE_COMMENT_SAVE_BUTTON_NAME As String = "btnStageSaveComments"

Private mLastHighlightRow As Long
Private mLastHighlightMode As String
Private mStageProgrammaticUpdate As Boolean
Private Const LOCAL_PROCESS_STATE_COL As Long = 13   'M
Private Const LOCAL_COMMENT_MIN_WIDTH As Double = 18
Private Const LOCAL_COMMENT_MAX_WIDTH As Double = 200
Private Const LOCAL_QUEUE_STATE_COL As Long = 14      'N visible on intake sheet
Private Const LOCAL_QUEUE_REQUEST_COL As Long = 53    'BA hidden helper
Private Const LOCAL_QUEUE_RESULT_COL As Long = 54     'BB hidden helper
Private Const LOCAL_QUEUE_MAX_CHECKS_PER_PASS As Long = 4
Private mImportedFinalAppliedRequests As Object

'------------------------------------------------------------------------------
' Procedure: ImportedFinalAppliedStore
' Scope: Private Function
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   ImportedFinalAppliedStore.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function ImportedFinalAppliedStore() As Object
    If mImportedFinalAppliedRequests Is Nothing Then
        Set mImportedFinalAppliedRequests = CreateObject("Scripting.Dictionary")
    End If

    Set ImportedFinalAppliedStore = mImportedFinalAppliedRequests
End Function

'------------------------------------------------------------------------------
' Procedure: ImportedFinalAppliedMarker
' Scope: Private Function
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   ImportedFinalAppliedMarker.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function ImportedFinalAppliedMarker(ByVal requestId As String) As String
    ImportedFinalAppliedMarker = "[FINAL APPLIED:" & Trim$(CStr(requestId)) & "]"
End Function

'------------------------------------------------------------------------------
' Procedure: ImportedFinalRequestAlreadyApplied
' Scope: Private Function
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   ImportedFinalRequestAlreadyApplied.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function ImportedFinalRequestAlreadyApplied(ByVal ws As Worksheet, ByVal dataRow As Long, ByVal requestId As String) As Boolean
    Dim d As Object
    Dim keyText As String
    Dim markerText As String
    Dim existingResultText As String

    requestId = Trim$(CStr(requestId))
    If Len(requestId) = 0 Then Exit Function

    Set d = ImportedFinalAppliedStore()
    keyText = UCase$(requestId)

    If d.Exists(keyText) Then
        ImportedFinalRequestAlreadyApplied = True
        Exit Function
    End If

    If Not ws Is Nothing And dataRow > 0 Then
        markerText = ImportedFinalAppliedMarker(requestId)
        existingResultText = CStr(ws.Cells(dataRow, LOCAL_QUEUE_RESULT_COL).Value)

        If InStr(1, existingResultText, markerText, vbTextCompare) > 0 Then
            d(keyText) = True
            ImportedFinalRequestAlreadyApplied = True
            Exit Function
        End If
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: MarkImportedFinalRequestApplied
' Scope: Private Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   MarkImportedFinalRequestApplied.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub MarkImportedFinalRequestApplied(ByVal ws As Worksheet, ByVal dataRow As Long, ByVal requestId As String, ByVal statusText As String, ByVal resultMessage As String)
    Dim d As Object
    Dim keyText As String
    Dim markerText As String

    requestId = Trim$(CStr(requestId))
    If Len(requestId) = 0 Then Exit Sub

    Set d = ImportedFinalAppliedStore()
    keyText = UCase$(requestId)
    d(keyText) = True

    If ws Is Nothing Then Exit Sub
    If dataRow <= 0 Then Exit Sub

    markerText = ImportedFinalAppliedMarker(requestId)

    ws.Cells(dataRow, LOCAL_QUEUE_RESULT_COL).Value = _
        markerText & " " & Trim$(statusText) & " - " & CompactQueueResultMessage(resultMessage)
End Sub

'------------------------------------------------------------------------------
' Procedure: AppendTextToCellOnce
' Scope: Private Sub
'
' What it does:
'   Appends text safely to an existing cell/message for AppendTextToCellOnce.
'
' Why it exists:
'   Append helpers preserve prior operator/master context while adding new
'   details without duplicating the same message.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub AppendTextToCellOnce(ByVal targetCell As Range, ByVal messageText As String)
    Dim existingText As String

    messageText = Trim$(CStr(messageText))
    If Len(messageText) = 0 Then Exit Sub
    If targetCell Is Nothing Then Exit Sub

    existingText = CStr(targetCell.Value)

    If InStr(1, existingText, messageText, vbTextCompare) > 0 Then
        Exit Sub
    End If

    If Len(Trim$(existingText)) > 0 Then
        targetCell.Value = existingText & " | " & messageText
    Else
        targetCell.Value = messageText
    End If

    targetCell.WrapText = False
    targetCell.ShrinkToFit = False
    targetCell.VerticalAlignment = xlCenter

    AutoFitLocalCommentPresentation targetCell.Worksheet, targetCell.Row
End Sub

'------------------------------------------------------------------------------
' Procedure: AutoFitActiveStageCommentColumn
' Scope: Public Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   AutoFitActiveStageCommentColumn.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub AutoFitActiveStageCommentColumn()
    Dim ws As Worksheet

    Set ws = StageViewSheet()
    If ws Is Nothing Then Exit Sub

    AutoFitAllLocalComments ws
End Sub

'------------------------------------------------------------------------------
' Procedure: IsImportedStageLoaded
' Scope: Public Function
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   IsImportedStageLoaded.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function IsImportedStageLoaded() As Boolean
    Dim ws As Worksheet
    Dim headerRow As Long

    Set ws = StageViewSheet()
    If ws Is Nothing Then Exit Function

    headerRow = GetImportedMainHeaderRow(ws)
    IsImportedStageLoaded = (headerRow > 0)
End Function

'------------------------------------------------------------------------------
' Procedure: IsStageProgrammaticUpdate
' Scope: Public Function
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   IsStageProgrammaticUpdate.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function IsStageProgrammaticUpdate() As Boolean
    IsStageProgrammaticUpdate = mStageProgrammaticUpdate
End Function

'------------------------------------------------------------------------------
' Procedure: BeginStageProgrammaticUpdate
' Scope: Private Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   BeginStageProgrammaticUpdate.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub BeginStageProgrammaticUpdate()
    mStageProgrammaticUpdate = True
End Sub

'------------------------------------------------------------------------------
' Procedure: EndStageProgrammaticUpdate
' Scope: Private Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   EndStageProgrammaticUpdate.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub EndStageProgrammaticUpdate()
    mStageProgrammaticUpdate = False
End Sub

'------------------------------------------------------------------------------
' Procedure: LoadSelectedStageSnapshot
' Scope: Public Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   LoadSelectedStageSnapshot.
'
' Why it exists:
'   The intake workbook reconstructs a working Excel sheet from published
'   snapshot JSON, so data and formatting must be applied in a predictable
'   order.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub LoadSelectedStageSnapshot(Optional ByVal suppressMessage As Boolean = False)
    If Not LoadSelectedStageSnapshotFromSharePoint(suppressMessage) Then
        'Do not silently open the old master workbook.
        'Legacy fallback remains available through LoadSelectedStageSnapshot_LegacyWorkbookImport.
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: LoadSelectedStageSnapshotFromSharePoint
' Scope: Public Function
'
' What it does:
'   Fetches the selected delivery/stage snapshot from SharePoint, rebuilds the
'   intake stage sheet from JSON, applies formatting/filters/protection, seeds
'   queue state, and focuses the scan box.
'
' Why it exists:
'   This is the main replacement for opening the master workbook directly. It
'   gives the scanner a current read-only working view without creating
'   workbook merge conflicts.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function LoadSelectedStageSnapshotFromSharePoint(Optional ByVal suppressMessage As Boolean = False) As Boolean
    Dim wsStage As Worksheet
    Dim snapshotItem As Object
    Dim snapshotJson As String

    Dim selectedKey As String
    Dim selectedProfile As String
    Dim stageKey As String
    Dim stageSheetName As String
    Dim modeText As String

    Dim revisionToken As String
    Dim updatedAtText As String
    Dim headerRow As Long
    Dim rowCount As Long

    Dim oldScreenUpdating As Boolean
    Dim oldEnableEvents As Boolean
    Dim oldDisplayAlerts As Boolean

    On Error GoTo FailLoad

    If IMPORT_DEBUG_ENABLED Then ImportDebugReset

    selectedKey = GetSelectedDeliveryKey()
    selectedProfile = GetSelectedStageProfile()
    stageKey = SnapshotImportStageKeyFromProfile(selectedProfile)
    stageSheetName = StageSheetFromProfile(selectedProfile)
    modeText = ModeFromStageProfile(selectedProfile)

    ImportDebugLog "LoadSelectedStageSnapshotFromSharePoint", "START", _
               "SelectedKey=" & selectedKey & _
               " | SelectedDisplay=" & GetSelectedDeliveryDisplay() & _
               " | StageProfile=" & selectedProfile & _
               " | StageKey=" & stageKey
               
    Set wsStage = StageViewSheet()
    If wsStage Is Nothing Then
        ImportDebugLog "LoadSelectedStageSnapshotFromSharePoint", "NO_STAGE_VIEW"
        Exit Function
    End If

    If Len(selectedKey) = 0 Then
        ImportDebugLog "LoadSelectedStageSnapshotFromSharePoint", "NO_SELECTED_KEY"

        If Not suppressMessage Then
            MsgBox "Select a delivery list first.", vbExclamation, "Scanning Panel"
        End If

        Exit Function
    End If

    If Len(stageKey) = 0 Or Len(stageSheetName) = 0 Or Len(modeText) = 0 Then
        ImportDebugLog "LoadSelectedStageSnapshotFromSharePoint", "NO_STAGE_PROFILE_MATCH"

        If Not suppressMessage Then
            MsgBox "Select a supported stage first.", vbExclamation, "Scanning Panel"
        End If

        Exit Function
    End If

    Set snapshotItem = PA_SnapshotGet(selectedKey, stageKey)

    If snapshotItem Is Nothing Then
        ImportDebugLog "LoadSelectedStageSnapshotFromSharePoint", "SNAPSHOT_GET_NOTHING"

        If Not suppressMessage Then
            MsgBox "Snapshot lookup failed. Power Automate did not return a usable response.", _
                   vbExclamation, "Scanning Panel"
        End If

        Exit Function
    End If

    If UCase$(PA_DictText(snapshotItem, "found")) <> "TRUE" Then
        ImportDebugLog "LoadSelectedStageSnapshotFromSharePoint", "SNAPSHOT_NOT_FOUND", _
               "StageKey=" & stageKey & _
               " | Message=" & PA_DictText(snapshotItem, "message")
               
        If Not suppressMessage Then
            MsgBox "No SharePoint snapshot was found for this delivery list/stage." & vbCrLf & vbCrLf & _
                   "Delivery List Key: " & selectedKey & vbCrLf & _
                   "Stage: " & selectedProfile & vbCrLf & _
                   "Stage Key: " & stageKey & vbCrLf & vbCrLf & _
                   "Make sure the master has published snapshots.", _
                   vbExclamation, "Scanning Panel"
        End If

        Exit Function
    End If

    snapshotJson = PA_DictText(snapshotItem, "snapshotJson")
    If Len(Trim$(snapshotJson)) = 0 Then
        ImportDebugLog "LoadSelectedStageSnapshotFromSharePoint", "SNAPSHOT_JSON_BLANK"

        If Not suppressMessage Then
            MsgBox "The SharePoint snapshot was found, but SnapshotJson was blank.", _
                   vbExclamation, "Scanning Panel"
        End If

        Exit Function
    End If

    revisionToken = PA_DictText(snapshotItem, "revisionToken")
    updatedAtText = PA_DictText(snapshotItem, "updatedAtText")

    If Len(revisionToken) = 0 Then
        revisionToken = PA_JsonGetStringValue(snapshotJson, "revisionToken")
    End If

    If Len(updatedAtText) = 0 Then
        updatedAtText = PA_JsonGetStringValue(snapshotJson, "updatedAt")
    End If

    headerRow = CLng(Val(PA_JsonGetNumberValue(snapshotJson, "headerRow")))
    If headerRow <= 0 Then headerRow = 5

    rowCount = CLng(Val(PA_DictText(snapshotItem, "rowCount")))
    If rowCount <= 0 Then
        rowCount = CLng(Val(PA_JsonGetNumberValue(snapshotJson, "rowCount")))
    End If

    oldScreenUpdating = Application.ScreenUpdating
    oldEnableEvents = Application.EnableEvents
    oldDisplayAlerts = Application.DisplayAlerts

    Application.ScreenUpdating = False
    Application.EnableEvents = False
    Application.DisplayAlerts = False

    If wsStage.ProtectContents Or wsStage.ProtectDrawingObjects Or wsStage.ProtectScenarios Then
        wsStage.Unprotect
    End If

    ClearImportedStageArea wsStage

ApplySnapshotImportSheetLayout wsStage, selectedProfile, stageSheetName, modeText, headerRow, snapshotJson
WriteSnapshotTopRowsToStageSheet wsStage, snapshotJson, headerRow
WriteSnapshotJsonToStageSheet wsStage, snapshotJson, headerRow, modeText
ApplySnapshotPublishedFormat wsStage, snapshotJson, headerRow
ApplyIntakeOnlySnapshotFormatting wsStage, headerRow, modeText

SetConfigValue CFG_LOADED_STAGE_SHEET, stageSheetName
SetConfigValue CFG_LOADED_STAGE_AT, Format$(Now, "m/d/yyyy h:mm:ss AM/PM")
SetConfigValue CFG_LOADED_REVISION_TOKEN, revisionToken
SetConfigValue CFG_LOADED_REVISION_UPDATED_AT, updatedAtText

ApplyStageViewTabAppearance stageSheetName, selectedProfile

mLastHighlightRow = 0
mLastHighlightMode = vbNullString

InitializeStageCommentBaseline wsStage
InitializeLocalQueueStateColumn wsStage
SeedImportedQueueStateFromMaster wsStage

'Do not recalculate the top summary during import.
'The master-published snapshot already brought over the exact summary text/formatting.
RefreshAllLocalStageVisualState wsStage
AutoFitAllLocalComments wsStage

ApplyStageRowVisibilityFilter wsStage, selectedProfile

ApplySnapshotPublishedTopSummaryFormat wsStage, snapshotJson
EnsureMostRecentScanRowsUsable wsStage
ApplyIntakeOnlySnapshotFormatting wsStage, headerRow, modeText

ApplyScanningSideAlignmentAndNumberFormats wsStage

EnsureStageQueueRefreshButton wsStage

ProtectImportedStageForScanning wsStage
FormatImportedStageArea wsStage
ApplyHeaderMostRecentHighlight wsStage

ApplyScanningSideAlignmentAndNumberFormats wsStage
EnsureStageQueueRefreshButton wsStage
EnsureStageAutoQueueToggleButton wsStage
EnsureStageCommentSaveButton wsStage

    ImportDebugLog "LoadSelectedStageSnapshotFromSharePoint", "END_OK", _
               "StageSheet=" & stageSheetName & _
               " | StageKey=" & stageKey & _
               " | RevisionToken=" & revisionToken & _
               " | UpdatedAt=" & updatedAtText & _
               " | RowCount=" & rowCount
               
    LoadSelectedStageSnapshotFromSharePoint = True

CleanExit:
    On Error Resume Next

    Application.DisplayAlerts = oldDisplayAlerts
    Application.EnableEvents = oldEnableEvents
    Application.ScreenUpdating = oldScreenUpdating

    If Not wsStage Is Nothing Then
        wsStage.Activate
        EnsureStageWindowLayout wsStage, True
        FocusStageScanBox
    End If

    On Error GoTo 0
    Exit Function

FailLoad:
    ImportDebugLog "LoadSelectedStageSnapshotFromSharePoint", "FAIL", _
               "Err=" & Err.Number & " | " & Err.Description

    If Not suppressMessage Then
        MsgBox "SharePoint snapshot import failed." & vbCrLf & vbCrLf & _
               "Error " & Err.Number & ": " & Err.Description & vbCrLf & vbCrLf & _
               "Run ImportDebugShowSheet to inspect the import log.", _
               vbExclamation, "Scanning Panel"
    End If

    Resume CleanExit
End Function

'------------------------------------------------------------------------------
' Procedure: RebuildStageQueueButtons
' Scope: Public Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   RebuildStageQueueButtons.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub RebuildStageQueueButtons()
    EnsureStageQueueRefreshButton StageViewSheet()
    EnsureStageAutoQueueToggleButton StageViewSheet()
    EnsureStageCommentSaveButton StageViewSheet()
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplySnapshotPublishedTopSummaryFormat
' Scope: Private Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   ApplySnapshotPublishedTopSummaryFormat.
'
' Why it exists:
'   The intake workbook reconstructs a working Excel sheet from published
'   snapshot JSON, so data and formatting must be applied in a predictable
'   order.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ApplySnapshotPublishedTopSummaryFormat(ByVal ws As Worksheet, ByVal snapshotJson As String)
    Dim formatJson As String
    Dim mergesJson As String
    Dim cellsJson As String
    Dim rowsJson As String
    Dim didApplyPublished As Boolean

    If ws Is Nothing Then Exit Sub
    If Len(Trim$(snapshotJson)) = 0 Then Exit Sub

    formatJson = PA_JsonValueForKey(snapshotJson, "format")

    If Len(Trim$(formatJson)) = 0 Then
        ApplyImportedSummaryPanelFallbackStyle ws
        EnsureMostRecentScanRowsUsable ws
        Exit Sub
    End If

    mergesJson = PA_JsonValueForKey(formatJson, "merges")
    cellsJson = PA_JsonValueForKey(formatJson, "cells")
    rowsJson = PA_JsonValueForKey(formatJson, "rows")

    On Error Resume Next

    ws.Range("A1:AV5").UnMerge

    If Len(Trim$(rowsJson)) > 0 Then
        ApplySnapshotTopRowHeights ws, rowsJson
        didApplyPublished = True
    End If

    If Len(Trim$(mergesJson)) > 0 Then
        ApplySnapshotTopMerges ws, mergesJson
        didApplyPublished = True
    End If

    If Len(Trim$(cellsJson)) > 0 Then
        ApplySnapshotTopCellFormats ws, cellsJson
        didApplyPublished = True
    End If

    On Error GoTo 0

    If Not didApplyPublished Then
        ApplyImportedSummaryPanelFallbackStyle ws
    End If

    'Regardless of published formatting, the intake scan row must stay usable.
    EnsureMostRecentScanRowsUsable ws
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplySnapshotTopRowHeights
' Scope: Private Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   ApplySnapshotTopRowHeights.
'
' Why it exists:
'   The intake workbook reconstructs a working Excel sheet from published
'   snapshot JSON, so data and formatting must be applied in a predictable
'   order.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ApplySnapshotTopRowHeights(ByVal ws As Worksheet, ByVal rowsJson As String)
    Dim objects As Collection
    Dim obj As Variant
    Dim rowNum As Long
    Dim rowHeight As Double

    If ws Is Nothing Then Exit Sub
    If Len(Trim$(rowsJson)) = 0 Then Exit Sub

    Set objects = PA_JsonSplitObjects(rowsJson)

    For Each obj In objects
        rowNum = CLng(Val(PA_JsonGetNumberValue(CStr(obj), "r")))
        rowHeight = CDbl(Val(PA_JsonGetNumberValue(CStr(obj), "h")))

        If rowNum >= 1 And rowNum <= 5 Then
            If rowHeight > 0 Then ws.Rows(rowNum).rowHeight = rowHeight
        End If
    Next obj
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplySnapshotTopMerges
' Scope: Private Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   ApplySnapshotTopMerges.
'
' Why it exists:
'   The intake workbook reconstructs a working Excel sheet from published
'   snapshot JSON, so data and formatting must be applied in a predictable
'   order.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ApplySnapshotTopMerges(ByVal ws As Worksheet, ByVal mergesJson As String)
    Dim objects As Collection
    Dim obj As Variant
    Dim addr As String
    Dim rng As Range

    If ws Is Nothing Then Exit Sub
    If Len(Trim$(mergesJson)) = 0 Then Exit Sub

    Set objects = PA_JsonSplitObjects(mergesJson)

    For Each obj In objects
        addr = PA_JsonGetStringValue(CStr(obj), "addr")

        If Len(addr) > 0 Then
            Set rng = Nothing

            On Error Resume Next
            Set rng = ws.Range(addr)
            On Error GoTo 0

            If Not rng Is Nothing Then
                If Not Intersect(rng, ws.Range("A1:AV5")) Is Nothing Then
                    On Error Resume Next
                    rng.Merge
                    On Error GoTo 0
                End If
            End If
        End If
    Next obj
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplySnapshotTopCellFormats
' Scope: Private Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   ApplySnapshotTopCellFormats.
'
' Why it exists:
'   The intake workbook reconstructs a working Excel sheet from published
'   snapshot JSON, so data and formatting must be applied in a predictable
'   order.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ApplySnapshotTopCellFormats(ByVal ws As Worksheet, ByVal cellsJson As String)
    Dim objects As Collection
    Dim obj As Variant
    Dim addr As String
    Dim cell As Range

    If ws Is Nothing Then Exit Sub
    If Len(Trim$(cellsJson)) = 0 Then Exit Sub

    Set objects = PA_JsonSplitObjects(cellsJson)

    For Each obj In objects
        addr = PA_JsonGetStringValue(CStr(obj), "a")

        If Len(addr) > 0 Then
            Set cell = Nothing

            On Error Resume Next
            Set cell = ws.Range(addr)
            On Error GoTo 0

            If Not cell Is Nothing Then
                If Not Intersect(cell, ws.Range("A1:AV5")) Is Nothing Then
                    ApplySnapshotOneCellFormat cell, CStr(obj)
                End If
            End If
        End If
    Next obj
End Sub

'------------------------------------------------------------------------------
' Procedure: LoadSelectedStageSnapshot_LegacyWorkbookImport
' Scope: Public Sub
'
' What it does:
'   Legacy fallback that opens the master workbook read-only and copies the
'   selected stage sheet into the intake workbook.
'
' Why it exists:
'   Kept for troubleshooting/backward compatibility, but the SharePoint
'   snapshot path is preferred because it avoids direct master workbook
'   access.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub LoadSelectedStageSnapshot_LegacyWorkbookImport(Optional ByVal suppressMessage As Boolean = False)
    Dim wsStage As Worksheet
    Dim wbMaster As Workbook
    Dim wsSource As Worksheet
    Dim masterPath As String
    Dim stageSheetName As String
    Dim srcLastRow As Long
    Dim srcLastCol As Long
    Dim srcRange As Range
    Dim destRange As Range
    Dim i As Long
    Dim wb As Workbook
    Dim masterWasAlreadyOpen As Boolean
    Dim beforeClearSummary As String
    Dim afterClearSummary As String
    Dim sourceSummary As String
    Dim destSummary As String

    On Error GoTo FailLoad

    If IMPORT_DEBUG_ENABLED Then ImportDebugReset
    ImportDebugLog "LoadSelectedStageSnapshot", "START", _
                   "SelectedKey=" & GetSelectedDeliveryKey(), _
                   "SelectedDisplay=" & GetSelectedDeliveryDisplay(), _
                   "StageProfile=" & GetSelectedStageProfile()

    Set wsStage = StageViewSheet()
    If wsStage Is Nothing Then
        ImportDebugLog "LoadSelectedStageSnapshot", "NO_STAGE_VIEW"
        Exit Sub
    End If

    If Len(GetSelectedDeliveryKey()) = 0 Then
        ImportDebugLog "LoadSelectedStageSnapshot", "NO_SELECTED_KEY"
        If Not suppressMessage Then MsgBox "Select a delivery list first.", vbExclamation, "Scanning Panel"
        Exit Sub
    End If

    stageSheetName = StageSheetFromProfile(GetSelectedStageProfile())
    ImportDebugLog "LoadSelectedStageSnapshot", "STAGE_SHEET_NAME", stageSheetName

    If Len(stageSheetName) = 0 Then
        ImportDebugLog "LoadSelectedStageSnapshot", "NO_STAGE_PROFILE_MATCH"
        If Not suppressMessage Then MsgBox "Select a supported stage first.", vbExclamation, "Scanning Panel"
        Exit Sub
    End If

    masterPath = ResolveMasterWorkbookPath()
    ImportDebugLog "LoadSelectedStageSnapshot", "MASTER_PATH", masterPath

    If Len(masterPath) = 0 Then Exit Sub

    Application.ScreenUpdating = False
    Application.EnableEvents = False
    Application.DisplayAlerts = False

    If wsStage.ProtectContents Or wsStage.ProtectDrawingObjects Or wsStage.ProtectScenarios Then
        wsStage.Unprotect
        ImportDebugLog "LoadSelectedStageSnapshot", "DEST_UNPROTECTED"
    End If

    beforeClearSummary = ImportDebugSummary(wsStage)
    ImportDebugLog "LoadSelectedStageSnapshot", "DEST_BEFORE_CLEAR", beforeClearSummary

    For Each wb In Application.Workbooks
        If Len(wb.FullName) > 0 Then
            If StrComp(wb.FullName, masterPath, vbTextCompare) = 0 Then
                Set wbMaster = wb
                masterWasAlreadyOpen = True
                Exit For
            End If
        End If
    Next wb

    If wbMaster Is Nothing Then
        Set wbMaster = Workbooks.Open(Filename:=masterPath, readOnly:=True, UpdateLinks:=False)
        ImportDebugLog "LoadSelectedStageSnapshot", "MASTER_OPENED", wbMaster.Name, wbMaster.FullName
    Else
        ImportDebugLog "LoadSelectedStageSnapshot", "MASTER_ALREADY_OPEN", wbMaster.Name, wbMaster.FullName
    End If

    Set wsSource = Nothing
    On Error Resume Next
    Set wsSource = wbMaster.Worksheets(stageSheetName)
    On Error GoTo FailLoad

    If wsSource Is Nothing Then
        ImportDebugLog "LoadSelectedStageSnapshot", "SOURCE_SHEET_NOT_FOUND", stageSheetName
        Err.Raise vbObjectError + 1000, "LoadSelectedStageSnapshot", _
                  "Could not find stage sheet '" & stageSheetName & "' in the master workbook."
    End If

    sourceSummary = ImportDebugSummary(wsSource)
    ImportDebugLog "LoadSelectedStageSnapshot", "SOURCE_FOUND", wsSource.Name, sourceSummary

    srcLastRow = FindLastUsedRow(wsSource)
    srcLastCol = FindLastUsedCol(wsSource)
    If srcLastCol < IMPORT_MAX_COL Then srcLastCol = IMPORT_MAX_COL

    ImportDebugLog "LoadSelectedStageSnapshot", "SOURCE_DIMENSIONS", _
                   "Rows=" & srcLastRow, "Cols=" & srcLastCol

    ClearImportedStageArea wsStage

    afterClearSummary = ImportDebugSummary(wsStage)
    ImportDebugLog "LoadSelectedStageSnapshot", "DEST_AFTER_CLEAR", afterClearSummary

    Set srcRange = wsSource.Range(wsSource.Cells(1, 1), wsSource.Cells(srcLastRow, srcLastCol))
    Set destRange = wsStage.Range(wsStage.Cells(1, 1), wsStage.Cells(srcLastRow, srcLastCol))

    srcRange.Copy
    destRange.PasteSpecial xlPasteAll
    Application.CutCopyMode = False

    destRange.Value = destRange.Value

    For i = 1 To srcLastCol
        wsStage.Columns(i).ColumnWidth = wsSource.Columns(i).ColumnWidth
    Next i

    For i = 1 To srcLastRow
    wsStage.Rows(i).rowHeight = wsSource.Rows(i).rowHeight
Next i

CopyDeliveryListLogoToSheetTemplate wsSource, wsStage

destSummary = ImportDebugSummary(wsStage)
ImportDebugLog "LoadSelectedStageSnapshot", "DEST_AFTER_PASTE", destSummary
    
    If IMPORT_DEBUG_ENABLED Then
    If StrComp(ImportDebugFindDeliveryTitle(wsSource), ImportDebugFindDeliveryTitle(wsStage), vbTextCompare) <> 0 Then
        ImportDebugLog "LoadSelectedStageSnapshot", "TITLE_MISMATCH", _
                       "Source=" & ImportDebugFindDeliveryTitle(wsSource), _
                       "Dest=" & ImportDebugFindDeliveryTitle(wsStage)
        MsgBox "DEBUG: Source and destination delivery titles do not match after paste." & vbCrLf & vbCrLf & _
               "Source: " & ImportDebugFindDeliveryTitle(wsSource) & vbCrLf & _
               "Dest: " & ImportDebugFindDeliveryTitle(wsStage) & vbCrLf & vbCrLf & _
               "Run ImportDebugShowSheet for the full log.", _
               vbExclamation, "Import Debug"
    End If
End If

    SetConfigValue CFG_LOADED_STAGE_SHEET, stageSheetName
    SetConfigValue CFG_LOADED_STAGE_AT, Format$(Now, "m/d/yyyy h:mm:ss AM/PM")
    StoreLoadedRevisionForSelectedDeliveryList

    ImportDebugLog "LoadSelectedStageSnapshot", "REVISION_STORED", _
                   "LoadedToken=" & GetLoadedRevisionToken(), _
                   "LoadedUpdatedAt=" & GetLoadedRevisionUpdatedAt()

    ApplyStageViewTabAppearance stageSheetName, GetSelectedStageProfile()

    mLastHighlightRow = 0
    mLastHighlightMode = vbNullString

    InitializeStageCommentBaseline wsStage
    InitializeLocalQueueStateColumn wsStage
    SeedImportedQueueStateFromMaster wsStage
    RefreshImportedTopSummaryPanels wsStage
    RefreshAllLocalStageVisualState wsStage
    AutoFitAllLocalComments wsStage
    ProtectImportedStageForScanning wsStage
    FormatImportedStageArea wsStage
    ApplyHeaderMostRecentHighlight wsStage

    ImportDebugLog "LoadSelectedStageSnapshot", "END_OK", ImportDebugSummary(wsStage)

    If IMPORT_DEBUG_ENABLED And Not suppressMessage Then
        MsgBox "Import debug summary:" & vbCrLf & vbCrLf & _
               "Master path: " & masterPath & vbCrLf & _
               "Source sheet: " & wsSource.Name & vbCrLf & _
               "Source title: " & ImportDebugFindDeliveryTitle(wsSource) & vbCrLf & _
               "Dest title: " & ImportDebugFindDeliveryTitle(wsStage), _
               vbInformation, "Import Debug"
    ElseIf Not suppressMessage Then
        MsgBox "Stage snapshot loaded to '" & stageSheetName & "' for " & _
               GetSelectedDeliveryDisplay() & " - " & stageSheetName, _
               vbInformation, "Scanning Panel"
    End If

CancelStationPoll
ScheduleStationPoll REVISION_BACKGROUND_CHECK_SECONDS

CleanExit:
    On Error Resume Next

    If Not wbMaster Is Nothing Then
        If Not masterWasAlreadyOpen Then
            wbMaster.Close SaveChanges:=False
        End If
    End If

    Application.CutCopyMode = False
    Application.DisplayAlerts = True
    Application.EnableEvents = True
    Application.ScreenUpdating = True
    On Error GoTo 0

    If Not wsStage Is Nothing Then
        wsStage.Activate
        EnsureStageWindowLayout wsStage, True
        FocusStageScanBox
    End If
    Exit Sub

FailLoad:
    ImportDebugLog "LoadSelectedStageSnapshot", "FAIL", _
                   "Err=" & Err.Number, Err.Description

    On Error Resume Next
    If Not wsStage Is Nothing Then
        ProtectImportedStageForScanning wsStage
    End If
    On Error GoTo 0

    MsgBox "Stage import failed." & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description & vbCrLf & vbCrLf & _
           "Run ImportDebugShowSheet to inspect the import log.", _
           vbExclamation, "Scanning Panel"

    Resume CleanExit
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplySnapshotImportSheetLayout
' Scope: Private Sub
'
' What it does:
'   Applies baseline row heights, column widths, titles, scan block headers,
'   and number formats before snapshot rows are written.
'
' Why it exists:
'   Snapshot JSON provides data, but the intake view still needs a predictable
'   Excel layout for scan boxes, summaries, and operator readability.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ApplySnapshotImportSheetLayout(ByVal ws As Worksheet, _
                                           ByVal stageProfile As String, _
                                           ByVal stageSheetName As String, _
                                           ByVal modeText As String, _
                                           ByVal headerRow As Long, _
                                           ByVal snapshotJson As String)
    Dim titleText As String

    If ws Is Nothing Then Exit Sub
    If headerRow <= 0 Then headerRow = 5

    titleText = PA_JsonGetStringValue(snapshotJson, "title")
    If Len(titleText) = 0 Then
        titleText = GetSelectedDeliveryDisplay()
    End If

    On Error Resume Next

    ws.Rows(1).rowHeight = 30
    ws.Rows(2).rowHeight = 24
    ws.Rows(3).rowHeight = 24
    ws.Rows(4).rowHeight = 22
    ws.Rows(headerRow).rowHeight = 20

    ws.Columns("A:D").ColumnWidth = 12
    ws.Columns("E").ColumnWidth = 14
    ws.Columns("F").ColumnWidth = 10
    ws.Columns("G").ColumnWidth = 10
    ws.Columns("H:M").ColumnWidth = 16
    ws.Columns("N").ColumnWidth = 12

    ws.Columns("O").ColumnWidth = 18
    ws.Columns("P").ColumnWidth = 20
    ws.Columns("Q").ColumnWidth = 12
    ws.Columns("R").ColumnWidth = 10
    ws.Columns("S").ColumnWidth = 12
    ws.Columns("T").ColumnWidth = 22
    ws.Columns("U").ColumnWidth = 15
    ws.Columns("V").ColumnWidth = 15
    ws.Columns("W").ColumnWidth = 20

    ws.Columns("X").ColumnWidth = 18
    ws.Columns("Y").ColumnWidth = 20
    ws.Columns("Z").ColumnWidth = 12
    ws.Columns("AA").ColumnWidth = 10
    ws.Columns("AB").ColumnWidth = 12
    ws.Columns("AC").ColumnWidth = 22
    ws.Columns("AD").ColumnWidth = 15
    ws.Columns("AE").ColumnWidth = 0.01
    ws.Columns("AF").ColumnWidth = 25
    ws.Columns("AG").ColumnWidth = 15
    ws.Columns("AE").Hidden = True

    ws.Columns("AO").ColumnWidth = 18
    ws.Columns("AP").ColumnWidth = 20
    ws.Columns("AQ").ColumnWidth = 12
    ws.Columns("AR").ColumnWidth = 10
    ws.Columns("AS").ColumnWidth = 12
    ws.Columns("AT").ColumnWidth = 22
    ws.Columns("AU").ColumnWidth = 15
    ws.Columns("AV").ColumnWidth = 25

    ws.Range("A1:N1").Merge
    ws.Range("A1").Value = titleText
    ws.Range("A1").HorizontalAlignment = xlCenter
    ws.Range("A1").VerticalAlignment = xlCenter
    ws.Range("A1").Font.Bold = True
    ws.Range("A1").Font.Size = 18

    ws.Range("O3:W3").Merge
    ws.Range("O3").Value = "Outbound - Airport Rd"

    ws.Range("X3:AG3").Merge
    ws.Range("X3").Value = IIf(UCase$(modeText) = "RECV", stageSheetName, "Inbound")

    ws.Range("AO3:AV3").Merge
    ws.Range("AO3").Value = "Staging - Airport Rd"

    ws.Range("O3:W3").HorizontalAlignment = xlCenter
    ws.Range("X3:AG3").HorizontalAlignment = xlCenter
    ws.Range("AO3:AV3").HorizontalAlignment = xlCenter

    ws.Range("O3:W3").Font.Bold = True
    ws.Range("X3:AG3").Font.Bold = True
    ws.Range("AO3:AV3").Font.Bold = True

    ws.Range("O4").Value = "Most Recent Scan:"
    ws.Range("X4").Value = "Most Recent Scan:"
    ws.Range("AO4").Value = "Most Recent Scan:"
    ws.Range("O4,X4,AO4").Font.Bold = True

    ws.Range("F:F").NumberFormat = "000"
    ws.Range("R:R").NumberFormat = "000"
    ws.Range("AA:AA").NumberFormat = "000"
    ws.Range("AR:AR").NumberFormat = "000"

    ws.Range("T:T").NumberFormat = "m/d/yyyy h:mm AM/PM"
    ws.Range("AC:AC").NumberFormat = "m/d/yyyy h:mm AM/PM"
    ws.Range("AT:AT").NumberFormat = "m/d/yyyy h:mm AM/PM"

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: WriteSnapshotJsonToStageSheet
' Scope: Private Sub
'
' What it does:
'   Writes published header arrays and row objects from the snapshot JSON into
'   the intake stage worksheet.
'
' Why it exists:
'   The intake sheet must visually match the master-published stage while
'   preserving the exact scan-side values included in the snapshot.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub WriteSnapshotJsonToStageSheet(ByVal ws As Worksheet, ByVal snapshotJson As String, ByVal headerRow As Long, ByVal modeText As String)
    Dim rowsText As String
    Dim rowObjects As Collection
    Dim rowObj As Variant
    Dim destRow As Long
    Dim rowIndex As Long

    If ws Is Nothing Then Exit Sub
    If Len(snapshotJson) = 0 Then Exit Sub
    If headerRow <= 0 Then headerRow = 5

    WriteSnapshotJsonArrayToRow ws, headerRow, 1, 14, PA_JsonValueForKey(snapshotJson, "leftHeaders")
    WriteSnapshotJsonArrayToRow ws, headerRow, 16, 23, PA_JsonValueForKey(snapshotJson, "sendHeaders")
    WriteSnapshotJsonArrayToRow ws, headerRow, 25, 33, PA_JsonValueForKey(snapshotJson, "recvHeaders")
    WriteSnapshotJsonArrayToRow ws, headerRow, 42, 48, PA_JsonValueForKey(snapshotJson, "stagingHeaders")

    'Make sure the critical intake headers are always where the existing intake logic expects them.
    ws.Cells(headerRow, 5).Value = "Order Nr."
    ws.Cells(headerRow, 6).Value = "Item Nr."

    If Len(Trim$(CStr(ws.Cells(headerRow, 7).Value))) = 0 Then
        ws.Cells(headerRow, 7).Value = "Qty."
    End If

    With ws.Range(ws.Cells(headerRow, 1), ws.Cells(headerRow, 54))
        .Font.Bold = True
        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
    End With

    rowsText = PA_JsonValueForKey(snapshotJson, "rows")
    Set rowObjects = PA_JsonSplitObjects(rowsText)

    rowIndex = 0

    For Each rowObj In rowObjects
        rowIndex = rowIndex + 1
        destRow = headerRow + rowIndex

        WriteSnapshotRowObjectToSheet ws, CStr(rowObj), destRow, modeText
    Next rowObj
End Sub

'------------------------------------------------------------------------------
' Procedure: WriteSnapshotRowObjectToSheet
' Scope: Private Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   WriteSnapshotRowObjectToSheet.
'
' Why it exists:
'   The intake workbook reconstructs a working Excel sheet from published
'   snapshot JSON, so data and formatting must be applied in a predictable
'   order.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub WriteSnapshotRowObjectToSheet(ByVal ws As Worksheet, ByVal rowJson As String, ByVal destRow As Long, ByVal modeText As String)
    Dim rowType As String

    Dim ord As Long
    Dim itm As Long
    Dim requiredQty As Long
    Dim customerText As String

    If ws Is Nothing Then Exit Sub
    If Len(rowJson) = 0 Then Exit Sub
    If destRow <= 0 Then Exit Sub

    rowType = UCase$(Trim$(PA_JsonGetStringValue(rowJson, "rowType")))
    If Len(rowType) = 0 Then rowType = "LINE"

    'Write exactly what the master published.
    'If the master scanner-side cells are blank, these stay blank.
    'If the master scanner-side cells contain existing scans, those scans come over.
    WriteSnapshotJsonArrayToRow ws, destRow, 1, 14, PA_JsonValueForKey(rowJson, "leftValues")
    WriteSnapshotJsonArrayToRow ws, destRow, 16, 23, PA_JsonValueForKey(rowJson, "sendValues")
    WriteSnapshotJsonArrayToRow ws, destRow, 25, 33, PA_JsonValueForKey(rowJson, "recvValues")
    WriteSnapshotJsonArrayToRow ws, destRow, 42, 48, PA_JsonValueForKey(rowJson, "stagingValues")

    'Section headers like "3/8 CLEAR TEMPERED" should not get forced order/item/qty values.
    If rowType = "SECTION" Then
        Exit Sub
    End If

    'Only force the main delivery-list identity columns A:N side.
    'Do NOT touch the scanner-side order/item/qty columns.
    ord = CLng(Val(PA_JsonGetNumberValue(rowJson, "orderNumber")))
    itm = CLng(Val(PA_JsonGetNumberValue(rowJson, "itemNumber")))
    requiredQty = CLng(Val(PA_JsonGetNumberValue(rowJson, "quantityRequired")))
    customerText = PA_JsonGetStringValue(rowJson, "customer")

    If requiredQty <= 0 Then requiredQty = 1

    ws.Cells(destRow, 5).Value = ord
    ws.Cells(destRow, 6).Value = itm
    ws.Cells(destRow, 7).Value = requiredQty

    If Len(Trim$(CStr(ws.Cells(destRow, 8).Value))) = 0 Then
        ws.Cells(destRow, 8).Value = customerText
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: WriteSnapshotJsonArrayToRow
' Scope: Private Sub
'
' What it does:
'   Parses, decodes, builds, or extracts JSON text used by the Power Automate
'   bridge (WriteSnapshotJsonArrayToRow).
'
' Why it exists:
'   The intake workbook reconstructs a working Excel sheet from published
'   snapshot JSON, so data and formatting must be applied in a predictable
'   order.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub WriteSnapshotJsonArrayToRow(ByVal ws As Worksheet, ByVal rowNum As Long, ByVal firstCol As Long, ByVal lastCol As Long, ByVal arrayText As String)
    Dim values As Collection
    Dim idx As Long
    Dim c As Long
    Dim rawValue As String
    Dim decodedValue As String

    If ws Is Nothing Then Exit Sub
    If rowNum <= 0 Then Exit Sub
    If firstCol <= 0 Or lastCol < firstCol Then Exit Sub

    Set values = SnapshotImportSplitTopLevelValues(arrayText)

    idx = 1

    For c = firstCol To lastCol
        If idx <= values.Count Then
            rawValue = CStr(values(idx))
            decodedValue = PA_JsonDecodeLiteral(rawValue)
            ws.Cells(rowNum, c).Value = decodedValue
        Else
            ws.Cells(rowNum, c).ClearContents
        End If

        idx = idx + 1
    Next c
End Sub

'------------------------------------------------------------------------------
' Procedure: SnapshotImportSplitTopLevelValues
' Scope: Private Function
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   SnapshotImportSplitTopLevelValues.
'
' Why it exists:
'   The intake workbook reconstructs a working Excel sheet from published
'   snapshot JSON, so data and formatting must be applied in a predictable
'   order.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function SnapshotImportSplitTopLevelValues(ByVal arrayText As String) As Collection
    Dim out As New Collection
    Dim s As String
    Dim i As Long
    Dim c As String
    Dim startPos As Long
    Dim depth As Long
    Dim inString As Boolean
    Dim escaped As Boolean

    s = Trim$(CStr(arrayText))

    If Len(s) = 0 Then
        Set SnapshotImportSplitTopLevelValues = out
        Exit Function
    End If

    If Left$(s, 1) = "[" And Right$(s, 1) = "]" Then
        s = Mid$(s, 2, Len(s) - 2)
    End If

    s = Trim$(s)

    If Len(s) = 0 Then
        Set SnapshotImportSplitTopLevelValues = out
        Exit Function
    End If

    startPos = 1
    depth = 0
    inString = False
    escaped = False

    For i = 1 To Len(s)
        c = Mid$(s, i, 1)

        If inString Then
            If escaped Then
                escaped = False
            ElseIf c = "\" Then
                escaped = True
            ElseIf c = """" Then
                inString = False
            End If
        Else
            Select Case c
                Case """"
                    inString = True

                Case "{", "["
                    depth = depth + 1

                Case "}", "]"
                    depth = depth - 1

                Case ","
                    If depth = 0 Then
                        out.Add Trim$(Mid$(s, startPos, i - startPos))
                        startPos = i + 1
                    End If
            End Select
        End If
    Next i

    If startPos <= Len(s) Then
        out.Add Trim$(Mid$(s, startPos))
    End If

    Set SnapshotImportSplitTopLevelValues = out
End Function

'------------------------------------------------------------------------------
' Procedure: SnapshotImportStageKeyFromProfile
' Scope: Private Function
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   SnapshotImportStageKeyFromProfile.
'
' Why it exists:
'   The intake workbook reconstructs a working Excel sheet from published
'   snapshot JSON, so data and formatting must be applied in a predictable
'   order.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function SnapshotImportStageKeyFromProfile(ByVal stageProfile As String) As String
    Select Case UCase$(Trim$(stageProfile))
        Case "STAGING - AIRPORT RD"
            SnapshotImportStageKeyFromProfile = "STAGING_AIRPORT_RD"

        Case "OUTBOUND - AIRPORT RD"
            SnapshotImportStageKeyFromProfile = "OUTBOUND_AIRPORT_RD"

        Case "INBOUND - INDIAN TRAIL"
            SnapshotImportStageKeyFromProfile = "INBOUND_INDIAN_TRAIL"

        Case "INBOUND - GREENVILLE"
            SnapshotImportStageKeyFromProfile = "INBOUND_GREENVILLE"

        Case "CUSTOMER PICKUP"
            SnapshotImportStageKeyFromProfile = "CUSTOMER_PICKUP"
    End Select
End Function

'------------------------------------------------------------------------------
' Procedure: ResolveMasterWorkbookPath
' Scope: Public Function
'
' What it does:
'   Checks or stores master delivery-list identity/revision/processor state
'   for ResolveMasterWorkbookPath.
'
' Why it exists:
'   The intake snapshot must match the current master revision; otherwise
'   scans could be applied to stale rows.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function ResolveMasterWorkbookPath() As String
    Dim savedPath As String
    Dim candidatePath As String
    Dim processorName As String
    Dim chosenPath As Variant
    Dim wb As Workbook

    processorName = GetProcessorWorkbookNameForSelectedList()

    If Len(processorName) > 0 Then
        For Each wb In Application.Workbooks
            If StrComp(wb.Name, processorName, vbTextCompare) = 0 Then
                SetConfigValue CFG_MASTER_WORKBOOK_PATH, wb.FullName
                ResolveMasterWorkbookPath = wb.FullName
                Exit Function
            End If
        Next wb

        candidatePath = ThisWorkbook.Path & Application.PathSeparator & processorName
        If Len(Dir$(candidatePath, vbNormal)) > 0 Then
            SetConfigValue CFG_MASTER_WORKBOOK_PATH, candidatePath
            ResolveMasterWorkbookPath = candidatePath
            Exit Function
        End If
    End If

    savedPath = Trim$(GetConfigValue(CFG_MASTER_WORKBOOK_PATH, vbNullString))
    If Len(savedPath) > 0 Then
        If Len(Dir$(savedPath, vbNormal)) > 0 Then
            ResolveMasterWorkbookPath = savedPath
            Exit Function
        End If
    End If

    chosenPath = Application.GetOpenFilename("Excel Macro-Enabled Workbook (*.xlsm),*.xlsm", , "Locate the Master Delivery List Workbook")
    If chosenPath <> False Then
        SetConfigValue CFG_MASTER_WORKBOOK_PATH, CStr(chosenPath)
        ResolveMasterWorkbookPath = CStr(chosenPath)
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: GetProcessorWorkbookNameForSelectedList
' Scope: Private Function
'
' What it does:
'   Checks or stores master delivery-list identity/revision/processor state
'   for GetProcessorWorkbookNameForSelectedList.
'
' Why it exists:
'   The intake snapshot must match the current master revision; otherwise
'   scans could be applied to stale rows.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function GetProcessorWorkbookNameForSelectedList() As String
    Dim item As Object
    Dim selectedKey As String

    selectedKey = GetSelectedDeliveryKey()
    If Len(selectedKey) = 0 Then Exit Function

    Set item = PA_FindActiveDeliveryListInfo(selectedKey, True)
    If item Is Nothing Then Exit Function

    GetProcessorWorkbookNameForSelectedList = PA_DictText(item, "processorWorkbook")
End Function

'------------------------------------------------------------------------------
' Procedure: ClearImportedStageArea
' Scope: Private Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   ClearImportedStageArea.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ClearImportedStageArea(ByVal ws As Worksheet)
    If ws Is Nothing Then Exit Sub

    On Error Resume Next
    If ws.ProtectContents Or ws.ProtectDrawingObjects Or ws.ProtectScenarios Then
        ws.Unprotect
    End If
    On Error GoTo 0

    ws.Cells.UnMerge
    ws.Cells.Clear
    ws.Cells.Locked = False
    ws.Columns("AX:AZ").Hidden = False
End Sub

'------------------------------------------------------------------------------
' Procedure: FormatImportedStageArea
' Scope: Private Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   FormatImportedStageArea.
'
' Why it exists:
'   The intake workbook reconstructs a working Excel sheet from published
'   snapshot JSON, so data and formatting must be applied in a predictable
'   order.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub FormatImportedStageArea(ByVal ws As Worksheet)
    'Do not change freeze panes or view at runtime.
    'Use the saved sheet view instead.
End Sub

'------------------------------------------------------------------------------
' Procedure: EnsureStageWindowLayout
' Scope: Private Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   EnsureStageWindowLayout.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub EnsureStageWindowLayout(ByVal ws As Worksheet, Optional ByVal forceReset As Boolean = False)
    If ws Is Nothing Then Exit Sub

    ws.Activate

    On Error Resume Next

    If Not forceReset Then
        If Not ActiveWindow Is Nothing Then
            If ActiveWindow.FreezePanes = True _
               And ActiveWindow.SplitRow = 5 _
               And ActiveWindow.SplitColumn = 0 Then
                Exit Sub
            End If
        End If
    End If

    With ActiveWindow
        .FreezePanes = False
        .SplitRow = 0
        .SplitColumn = 0
    End With

    'Freeze rows 1:5 only. Do not freeze columns A:N.
    ws.Range("A6").Select

    With ActiveWindow
        .SplitRow = 5
        .SplitColumn = 0
        .FreezePanes = True
        .ScrollRow = 1
        .ScrollColumn = 1
    End With

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: FindLastUsedRow
' Scope: Private Function
'
' What it does:
'   Finds, classifies, updates, hides, shows, highlights, or formats worksheet
'   rows for FindLastUsedRow.
'
' Why it exists:
'   Rows can be section headers, real delivery lines, hidden filtered rows,
'   active queue rows, or recently scanned rows; each state affects operator
'   behavior.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function FindLastUsedRow(ByVal ws As Worksheet) As Long
    Dim f As Range

    Set f = ws.Cells.Find(What:="*", After:=ws.Cells(1, 1), LookIn:=xlFormulas, SearchOrder:=xlByRows, SearchDirection:=xlPrevious)
    If f Is Nothing Then
        FindLastUsedRow = 1
    Else
        FindLastUsedRow = f.Row
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: FindLastUsedCol
' Scope: Private Function
'
' What it does:
'   Finds, sizes, hides, or formats worksheet columns for FindLastUsedCol.
'
' Why it exists:
'   The intake workflow depends on fixed scan blocks and hidden helper
'   columns, so column handling must stay predictable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function FindLastUsedCol(ByVal ws As Worksheet) As Long
    Dim f As Range

    Set f = ws.Cells.Find(What:="*", After:=ws.Cells(1, 1), LookIn:=xlFormulas, SearchOrder:=xlByColumns, SearchDirection:=xlPrevious)
    If f Is Nothing Then
        FindLastUsedCol = 1
    Else
        FindLastUsedCol = f.Column
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: GetImportedMainHeaderRow
' Scope: Private Function
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   GetImportedMainHeaderRow.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function GetImportedMainHeaderRow(ByVal ws As Worksheet) As Long
    Dim r As Long

    For r = 1 To 40
        If StrComp(Trim$(CStr(ws.Cells(r, 5).Value)), "Order Nr.", vbTextCompare) = 0 And _
           StrComp(Trim$(CStr(ws.Cells(r, 6).Value)), "Item Nr.", vbTextCompare) = 0 Then
            GetImportedMainHeaderRow = r
            Exit Function
        End If
    Next r
End Function

'------------------------------------------------------------------------------
' Procedure: GetStageScanBoxCell
' Scope: Public Function
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   GetStageScanBoxCell.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function GetStageScanBoxCell() As Range
    Dim barcodeCol As Long
    Dim orderCol As Long
    Dim itemCol As Long
    Dim qtyCol As Long
    Dim timeCol As Long
    Dim checkCol As Long
    Dim commentCol As Long
    Dim recentValueCell As Range

    If Not GetModeBlockColumns(ModeFromStageProfile(GetSelectedStageProfile()), barcodeCol, orderCol, itemCol, qtyCol, timeCol, checkCol, commentCol, recentValueCell) Then Exit Function
    Set GetStageScanBoxCell = recentValueCell
End Function

'------------------------------------------------------------------------------
' Procedure: FocusStageScanBox
' Scope: Public Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   FocusStageScanBox.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub FocusStageScanBox()
    FocusScanBoxAndCenterRow 0
End Sub

'------------------------------------------------------------------------------
' Procedure: FocusScanBoxAndCenterRow
' Scope: Public Sub
'
' What it does:
'   Cleans, validates, decodes, applies, focuses, or displays scan/barcode
'   data for FocusScanBoxAndCenterRow.
'
' Why it exists:
'   The scanner acts like a keyboard, so the workbook must turn entered text
'   into safe order/item updates without duplicate submissions.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub FocusScanBoxAndCenterRow(Optional ByVal targetRow As Long = 0)
    Dim ws As Worksheet
    Dim scanCell As Range
    Dim oldEvents As Boolean
    Dim visibleRows As Long
    Dim topRow As Long

    Set ws = StageViewSheet()
    If ws Is Nothing Then Exit Sub

    Set scanCell = GetStageScanBoxCell()
    If scanCell Is Nothing Then Exit Sub

    oldEvents = Application.EnableEvents

    On Error GoTo CleanExit
    Application.EnableEvents = False

    ws.Activate

    'Keep the actual active/selected cell as the scan box
    scanCell.Select

    If Not ActiveWindow Is Nothing Then
        With ActiveWindow
            'This keeps the left delivery-list side visible.
            .ScrollColumn = 1

            'If a scanned row was provided, center that row vertically.
            If targetRow > 0 Then
                visibleRows = .VisibleRange.Rows.Count

                If visibleRows <= 0 Then
                    visibleRows = 20
                End If

                topRow = targetRow - (visibleRows \ 2)

                If topRow < 1 Then
                    topRow = 1
                End If

                .ScrollRow = topRow
            End If
        End With
    End If

CleanExit:
    Application.EnableEvents = oldEvents
End Sub

'------------------------------------------------------------------------------
' Procedure: MarkImportedRowPendingMaster
' Scope: Public Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   MarkImportedRowPendingMaster.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub MarkImportedRowPendingMaster(ByVal targetRow As Long, ByVal requestId As String, Optional ByVal queueStatus As String = "Buffered locally")
    Dim ws As Worksheet

    Set ws = StageViewSheet()
    If ws Is Nothing Then Exit Sub
    If targetRow <= 0 Then Exit Sub
    If Len(Trim$(requestId)) = 0 Then Exit Sub

    ws.Cells(targetRow, LOCAL_QUEUE_REQUEST_COL).Value = requestId
    ws.Cells(targetRow, LOCAL_QUEUE_STATE_COL).Value = ShortQueueStateText(queueStatus)
    ws.Cells(targetRow, LOCAL_QUEUE_RESULT_COL).Value = "Waiting for master confirmation..."

    FormatLocalQueueStateCell ws.Cells(targetRow, LOCAL_QUEUE_STATE_COL), queueStatus
End Sub

'------------------------------------------------------------------------------
' Procedure: IsMasterFinalQueueResult
' Scope: Private Function
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   IsMasterFinalQueueResult.
'
' Why it exists:
'   Scans move through local buffer, SharePoint ScanQueue, master processing,
'   and final intake confirmation; this state must stay traceable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function IsMasterFinalQueueResult(ByVal resultText As String) As Boolean
    IsMasterFinalQueueResult = (Left$(UCase$(Trim$(CStr(resultText))), 14) = "[MASTER FINAL]")
End Function

'------------------------------------------------------------------------------
' Procedure: MasterFinalQueueResultText
' Scope: Private Function
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   MasterFinalQueueResultText.
'
' Why it exists:
'   Scans move through local buffer, SharePoint ScanQueue, master processing,
'   and final intake confirmation; this state must stay traceable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function MasterFinalQueueResultText(ByVal resultMessage As String, ByVal statusText As String) As String
    Dim cleanMessage As String

    cleanMessage = Trim$(CStr(resultMessage))

    If Len(cleanMessage) = 0 Then
        cleanMessage = "Master returned status: " & statusText
    End If

    If IsMasterFinalQueueResult(cleanMessage) Then
        MasterFinalQueueResultText = cleanMessage
    Else
        MasterFinalQueueResultText = "[MASTER FINAL] " & cleanMessage
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: IsStageScanBox
' Scope: Public Function
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for IsStageScanBox.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function IsStageScanBox(ByVal Target As Range) As Boolean
    Dim scanCell As Range

    If Target Is Nothing Then Exit Function
    If Target.CountLarge <> 1 Then Exit Function

    Set scanCell = GetStageScanBoxCell()
    If scanCell Is Nothing Then Exit Function

    IsStageScanBox = (Target.Worksheet.Name = scanCell.Worksheet.Name And Target.Address = scanCell.Address)
End Function

'------------------------------------------------------------------------------
' Procedure: IsStageCommentCell
' Scope: Public Function
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   IsStageCommentCell.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function IsStageCommentCell(ByVal Target As Range) As Boolean
    Dim ws As Worksheet
    Dim headerRow As Long
    Dim lastRow As Long
    Dim barcodeCol As Long
    Dim orderCol As Long
    Dim itemCol As Long
    Dim qtyCol As Long
    Dim timeCol As Long
    Dim checkCol As Long
    Dim commentCol As Long
    Dim recentValueCell As Range

    If Target Is Nothing Then Exit Function
    If Target.CountLarge <> 1 Then Exit Function

    Set ws = StageViewSheet()
    If ws Is Nothing Then Exit Function
    If Target.Worksheet.Name <> ws.Name Then Exit Function

    headerRow = GetImportedMainHeaderRow(ws)
    If headerRow = 0 Then Exit Function

    If Not GetModeBlockColumns(ModeFromStageProfile(GetSelectedStageProfile()), barcodeCol, orderCol, itemCol, qtyCol, timeCol, checkCol, commentCol, recentValueCell) Then Exit Function

    lastRow = ws.Cells(ws.Rows.Count, 5).End(xlUp).Row

    If Target.Column = commentCol And Target.Row > headerRow And Target.Row <= lastRow Then
        IsStageCommentCell = True
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: IsStageEditableCell
' Scope: Public Function
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   IsStageEditableCell.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function IsStageEditableCell(ByVal Target As Range) As Boolean
    IsStageEditableCell = (IsStageScanBox(Target) Or IsStageCommentCell(Target))
End Function

'------------------------------------------------------------------------------
' Procedure: ProtectImportedStageForScanning
' Scope: Public Sub
'
' What it does:
'   Locks the imported snapshot except for the active scan box and allowed
'   comment cells, then protects the sheet with UserInterfaceOnly behavior.
'
' Why it exists:
'   Operators should scan and comment, not accidentally edit imported delivery
'   data or scan/result columns.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub ProtectImportedStageForScanning(ByVal ws As Worksheet)
    Dim headerRow As Long
    Dim lastRow As Long
    Dim r As Long
    Dim barcodeCol As Long
    Dim orderCol As Long
    Dim itemCol As Long
    Dim qtyCol As Long
    Dim timeCol As Long
    Dim checkCol As Long
    Dim commentCol As Long
    Dim recentValueCell As Range

    headerRow = GetImportedMainHeaderRow(ws)
    If headerRow = 0 Then Exit Sub

    If Not GetModeBlockColumns(ModeFromStageProfile(GetSelectedStageProfile()), barcodeCol, orderCol, itemCol, qtyCol, timeCol, checkCol, commentCol, recentValueCell) Then Exit Sub

    lastRow = ws.Cells(ws.Rows.Count, 5).End(xlUp).Row

    On Error Resume Next
    ws.Unprotect
    On Error GoTo 0

    ws.Cells.Locked = True

    If Not recentValueCell Is Nothing Then
        recentValueCell.Locked = False
    End If

    For r = headerRow + 1 To lastRow
        ws.Cells(r, commentCol).Locked = False
    Next r

    ws.Columns("AX:BB").Hidden = True
    ws.EnableSelection = xlUnlockedCells
    ws.Protect DrawingObjects:=True, Contents:=True, Scenarios:=True, UserInterfaceOnly:=True, AllowFiltering:=True, AllowSorting:=True
End Sub

'------------------------------------------------------------------------------
' Procedure: ReprotectImportedStageForScanning
' Scope: Public Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   ReprotectImportedStageForScanning.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub ReprotectImportedStageForScanning()
    Dim ws As Worksheet

    Set ws = StageViewSheet()
    If ws Is Nothing Then Exit Sub

    ProtectImportedStageForScanning ws
End Sub

'------------------------------------------------------------------------------
' Procedure: InitializeStageCommentBaseline
' Scope: Private Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   InitializeStageCommentBaseline.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub InitializeStageCommentBaseline(ByVal ws As Worksheet)
    Dim headerRow As Long
    Dim lastRow As Long
    Dim r As Long
    Dim barcodeCol As Long
    Dim orderCol As Long
    Dim itemCol As Long
    Dim qtyCol As Long
    Dim timeCol As Long
    Dim checkCol As Long
    Dim commentCol As Long
    Dim recentValueCell As Range

    headerRow = GetImportedMainHeaderRow(ws)
    If headerRow = 0 Then Exit Sub

    If Not GetModeBlockColumns(ModeFromStageProfile(GetSelectedStageProfile()), barcodeCol, orderCol, itemCol, qtyCol, timeCol, checkCol, commentCol, recentValueCell) Then Exit Sub

    lastRow = ws.Cells(ws.Rows.Count, 5).End(xlUp).Row

    ws.Columns(COMMENT_BASELINE_COL).Hidden = False
    ws.Cells(1, COMMENT_BASELINE_COL).Value = "OriginalComments"
    ws.Cells(1, COMMENT_BASELINE_COL + 1).Value = "LoadedMode"
    ws.Cells(1, COMMENT_BASELINE_COL + 2).Value = "LoadedKey"
    ws.Cells(2, COMMENT_BASELINE_COL + 1).Value = GetSelectedStageProfile()
    ws.Cells(2, COMMENT_BASELINE_COL + 2).Value = GetSelectedDeliveryKey()

    For r = headerRow + 1 To lastRow
        ws.Cells(r, COMMENT_BASELINE_COL).Value = CStr(ws.Cells(r, commentCol).Value)
    Next r
    
    UpdateStageCommentSaveButton ws
    ws.Columns("AX:BB").Hidden = True
End Sub

'------------------------------------------------------------------------------
' Procedure: RefreshImportedTopSummaryPanels
' Scope: Private Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   RefreshImportedTopSummaryPanels.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub RefreshImportedTopSummaryPanels(ByVal ws As Worksheet)
    Dim headerRow As Long
    Dim lastRow As Long
    Dim r As Long

    Dim totalQty As Long
    Dim outboundQty As Long
    Dim inboundQty As Long
    Dim stagedQty As Long

    Dim stageProfile As String

    Dim outboundLabel As String
    Dim inboundLabel As String
    Dim stagedLabel As String

    If ws Is Nothing Then Exit Sub

    stageProfile = GetSelectedStageProfile()

    headerRow = GetImportedMainHeaderRow(ws)
    If headerRow = 0 Then Exit Sub

    lastRow = ws.Cells(ws.Rows.Count, 5).End(xlUp).Row

    For r = headerRow + 1 To lastRow
        If Not ws.Rows(r).Hidden Then
            If SummaryRowShouldCountForStage(ws, r, stageProfile) Then
                If IsNumeric(ws.Cells(r, 7).Value) Then totalQty = totalQty + CLng(Val(ws.Cells(r, 7).Value))
                If IsNumeric(ws.Cells(r, 19).Value) Then outboundQty = outboundQty + CLng(Val(ws.Cells(r, 19).Value))
                If IsNumeric(ws.Cells(r, 28).Value) Then inboundQty = inboundQty + CLng(Val(ws.Cells(r, 28).Value))
                If IsNumeric(ws.Cells(r, 45).Value) Then stagedQty = stagedQty + CLng(Val(ws.Cells(r, 45).Value))
            End If
        End If
    Next r

    outboundLabel = SummaryLabelFromExistingCell(ws.Range("O2").Value, "Outbound Qty")
    inboundLabel = SummaryLabelFromExistingCell(ws.Range("X2").Value, "Inbound Qty")
    stagedLabel = SummaryLabelFromExistingCell(ws.Range("AO2").Value, "Staged Qty")

    'Values only. Do not touch formats, merges, row 3, or row 4.
    ws.Range("O2").Value = BuildSummaryText(outboundLabel, outboundQty, totalQty, "On Time")
    ws.Range("X2").Value = BuildSummaryText(inboundLabel, inboundQty, totalQty, "Complete")
    ws.Range("AO2").Value = BuildSummaryText(stagedLabel, stagedQty, totalQty, "Complete")

    EnsureMostRecentScanRowsUsable ws
End Sub

'------------------------------------------------------------------------------
' Procedure: EnsureMostRecentScanRowsUsable
' Scope: Private Sub
'
' What it does:
'   Cleans, validates, decodes, applies, focuses, or displays scan/barcode
'   data for EnsureMostRecentScanRowsUsable.
'
' Why it exists:
'   The scanner acts like a keyboard, so the workbook must turn entered text
'   into safe order/item updates without duplicate submissions.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub EnsureMostRecentScanRowsUsable(ByVal ws As Worksheet)
    If ws Is Nothing Then Exit Sub

    On Error Resume Next

    'Row 4 is used by the intake scan/most-recent values.
    'These ranges must never be merged or barcode/manual scans can hang/fail.
    ws.Range("O4:W4").UnMerge
    ws.Range("X4:AG4").UnMerge
    ws.Range("AO4:AV4").UnMerge

    ws.Range("O4:W4").WrapText = False
    ws.Range("X4:AG4").WrapText = False
    ws.Range("AO4:AV4").WrapText = False

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: SummaryRowShouldCountForStage
' Scope: Private Function
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   SummaryRowShouldCountForStage.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function SummaryRowShouldCountForStage(ByVal ws As Worksheet, ByVal rowNum As Long, ByVal stageProfile As String) As Boolean
    If ws Is Nothing Then Exit Function
    If rowNum <= 0 Then Exit Function

    'Only real order/item rows count. Section headers like "3/8 CLEAR TEMPERED" do not.
    If Not SummaryRowIsDeliveryLine(ws, rowNum) Then Exit Function

    Select Case UCase$(Trim$(stageProfile))
        Case "CUSTOMER PICKUP"
            SummaryRowShouldCountForStage = SummaryRowIsCPU(ws, rowNum)

        Case "INBOUND - GREENVILLE"
            SummaryRowShouldCountForStage = SummaryRowIsGreenville(ws, rowNum)

        Case "INBOUND - INDIAN TRAIL"
            'Indian Trail should exclude Greenville and Customer Pickup.
            SummaryRowShouldCountForStage = _
                (Not SummaryRowIsCPU(ws, rowNum)) And _
                (Not SummaryRowIsGreenville(ws, rowNum))

        Case Else
            'Outbound and staging use the whole list.
            SummaryRowShouldCountForStage = True
    End Select
End Function

'------------------------------------------------------------------------------
' Procedure: SummaryRowIsDeliveryLine
' Scope: Private Function
'
' What it does:
'   Finds, classifies, updates, hides, shows, highlights, or formats worksheet
'   rows for SummaryRowIsDeliveryLine.
'
' Why it exists:
'   Rows can be section headers, real delivery lines, hidden filtered rows,
'   active queue rows, or recently scanned rows; each state affects operator
'   behavior.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function SummaryRowIsDeliveryLine(ByVal ws As Worksheet, ByVal rowNum As Long) As Boolean
    Dim orderText As String
    Dim itemText As String

    If ws Is Nothing Then Exit Function

    orderText = Trim$(CStr(ws.Cells(rowNum, 5).Value)) 'E = Order Nr.
    itemText = Trim$(CStr(ws.Cells(rowNum, 6).Value))  'F = Item Nr.

    SummaryRowIsDeliveryLine = (Len(orderText) > 0 Or Len(itemText) > 0)
End Function

'------------------------------------------------------------------------------
' Procedure: SummaryRowIsCPU
' Scope: Private Function
'
' What it does:
'   Finds, classifies, updates, hides, shows, highlights, or formats worksheet
'   rows for SummaryRowIsCPU.
'
' Why it exists:
'   Rows can be section headers, real delivery lines, hidden filtered rows,
'   active queue rows, or recently scanned rows; each state affects operator
'   behavior.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function SummaryRowIsCPU(ByVal ws As Worksheet, ByVal rowNum As Long) As Boolean
    Dim routeText As String

    If ws Is Nothing Then Exit Function

    routeText = SummaryCleanText(ws.Cells(rowNum, 12).Value) 'L = Route
    SummaryRowIsCPU = (UCase$(routeText) = "CPU")
End Function

'------------------------------------------------------------------------------
' Procedure: SummaryRowIsGreenville
' Scope: Private Function
'
' What it does:
'   Finds, classifies, updates, hides, shows, highlights, or formats worksheet
'   rows for SummaryRowIsGreenville.
'
' Why it exists:
'   Rows can be section headers, real delivery lines, hidden filtered rows,
'   active queue rows, or recently scanned rows; each state affects operator
'   behavior.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function SummaryRowIsGreenville(ByVal ws As Worksheet, ByVal rowNum As Long) As Boolean
    Dim customerText As String

    If ws Is Nothing Then Exit Function

    customerText = SummaryCustomerText(ws, rowNum)

    SummaryRowIsGreenville = _
        (UCase$(customerText) = UCase$("BFS East Greenville SC MW"))
End Function

'------------------------------------------------------------------------------
' Procedure: SummaryCustomerText
' Scope: Private Function
'
' What it does:
'   Performs the intake-workbook step named SummaryCustomerText inside
'   modStageSnapshot.
'
' Why it exists:
'   Intake stations should not open or edit the master workbook directly. This
'   module lets them scan against a published snapshot while keeping local UI
'   state clear and recoverable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function SummaryCustomerText(ByVal ws As Worksheet, ByVal rowNum As Long) As String
    Dim a As String
    Dim b As String

    If ws Is Nothing Then Exit Function

    'Customer is normally in the merged I:J area.
    a = SummaryCleanText(ws.Cells(rowNum, 9).Value)   'I
    b = SummaryCleanText(ws.Cells(rowNum, 10).Value)  'J

    If Len(a) > 0 And Len(b) > 0 Then
        If StrComp(a, b, vbTextCompare) = 0 Then
            SummaryCustomerText = a
        Else
            SummaryCustomerText = a & " " & b
        End If
    ElseIf Len(a) > 0 Then
        SummaryCustomerText = a
    Else
        SummaryCustomerText = b
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: SummaryCleanText
' Scope: Private Function
'
' What it does:
'   Performs the intake-workbook step named SummaryCleanText inside
'   modStageSnapshot.
'
' Why it exists:
'   Intake stations should not open or edit the master workbook directly. This
'   module lets them scan against a published snapshot while keeping local UI
'   state clear and recoverable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function SummaryCleanText(ByVal valueIn As Variant) As String
    Dim s As String

    s = CStr(valueIn)
    s = Replace$(s, Chr$(160), " ")

    On Error Resume Next
    s = Application.WorksheetFunction.Clean(s)
    s = Application.WorksheetFunction.Trim(s)
    On Error GoTo 0

    SummaryCleanText = Trim$(s)
End Function

'------------------------------------------------------------------------------
' Procedure: SummaryLabelFromExistingCell
' Scope: Private Function
'
' What it does:
'   Performs the intake-workbook step named SummaryLabelFromExistingCell
'   inside modStageSnapshot.
'
' Why it exists:
'   Intake stations should not open or edit the master workbook directly. This
'   module lets them scan against a published snapshot while keeping local UI
'   state clear and recoverable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function SummaryLabelFromExistingCell(ByVal existingValue As Variant, ByVal fallbackLabel As String) As String
    Dim s As String
    Dim p As Long

    s = Trim$(CStr(existingValue))
    p = InStr(1, s, ":", vbTextCompare)

    If p > 1 Then
        SummaryLabelFromExistingCell = Trim$(Left$(s, p - 1))
    Else
        SummaryLabelFromExistingCell = fallbackLabel
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: BuildSummaryText
' Scope: Private Function
'
' What it does:
'   Builds a display string, request key, message, JSON value, or derived
'   object for BuildSummaryText.
'
' Why it exists:
'   Generated values should be built one consistent way so the buffer, audit,
'   panel, and SharePoint queue can match each other.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function BuildSummaryText(ByVal labelText As String, ByVal doneQty As Long, ByVal totalQty As Long, ByVal suffixText As String) As String
    Dim pct As Double

    If totalQty > 0 Then
        pct = doneQty / totalQty
    Else
        pct = 0
    End If

    BuildSummaryText = labelText & ": " & doneQty & "/" & totalQty & " • " & Format$(pct * 100, "0.0") & "% " & suffixText
End Function

'------------------------------------------------------------------------------
' Procedure: FormatLocalGreenStatus
' Scope: Private Sub
'
' What it does:
'   Calculates, stores, formats, or displays status/result state for
'   FormatLocalGreenStatus.
'
' Why it exists:
'   The intake workbook reconstructs a working Excel sheet from published
'   snapshot JSON, so data and formatting must be applied in a predictable
'   order.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub FormatLocalGreenStatus(ByVal c As Range)
    With c
        .Interior.Color = RGB(198, 239, 206)
        .Font.Color = RGB(0, 97, 0)
        .Font.Bold = True
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: ClearLocalStatusFormat
' Scope: Private Sub
'
' What it does:
'   Calculates, stores, formats, or displays status/result state for
'   ClearLocalStatusFormat.
'
' Why it exists:
'   The intake workbook reconstructs a working Excel sheet from published
'   snapshot JSON, so data and formatting must be applied in a predictable
'   order.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ClearLocalStatusFormat(ByVal c As Range)
    With c
        .Interior.Pattern = xlNone
        .Font.ColorIndex = xlAutomatic
        .Font.Bold = False
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: FormatLocalYellowPartial
' Scope: Private Sub
'
' What it does:
'   Applies or clears visual formatting for FormatLocalYellowPartial.
'
' Why it exists:
'   The intake workbook reconstructs a working Excel sheet from published
'   snapshot JSON, so data and formatting must be applied in a predictable
'   order.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub FormatLocalYellowPartial(ByVal c As Range)
    With c
        .Interior.Color = RGB(255, 242, 204)
        .Font.Color = RGB(156, 101, 0)
        .Font.Bold = True
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: FormatLocalMismatchStatus
' Scope: Private Sub
'
' What it does:
'   Calculates, stores, formats, or displays status/result state for
'   FormatLocalMismatchStatus.
'
' Why it exists:
'   The intake workbook reconstructs a working Excel sheet from published
'   snapshot JSON, so data and formatting must be applied in a predictable
'   order.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub FormatLocalMismatchStatus(ByVal c As Range)
    With c
        .Interior.Color = RGB(255, 199, 206)
        .Font.Color = RGB(156, 0, 6)
        .Font.Bold = True
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: FormatLocalStatusCellByValue
' Scope: Private Sub
'
' What it does:
'   Calculates, stores, formats, or displays status/result state for
'   FormatLocalStatusCellByValue.
'
' Why it exists:
'   The intake workbook reconstructs a working Excel sheet from published
'   snapshot JSON, so data and formatting must be applied in a predictable
'   order.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub FormatLocalStatusCellByValue(ByVal c As Range, ByVal statusText As String)
    Dim statusUpper As String

    statusText = Trim$(statusText)
    statusUpper = UCase$(statusText)

    If statusUpper = "MISMATCH" Or statusUpper = "MASTER ERROR" Then
        FormatLocalMismatchStatus c

    ElseIf statusUpper = "RECEIVED" Or statusUpper = "OK" Then
        FormatLocalGreenStatus c

    ElseIf Left$(statusUpper, 7) = "PARTIAL" Then
        FormatLocalYellowPartial c

    Else
        ClearLocalStatusFormat c
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: FormatLocalDeliveryTiming
' Scope: Private Sub
'
' What it does:
'   Applies or clears visual formatting for FormatLocalDeliveryTiming.
'
' Why it exists:
'   The intake workbook reconstructs a working Excel sheet from published
'   snapshot JSON, so data and formatting must be applied in a predictable
'   order.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub FormatLocalDeliveryTiming(ByVal c As Range, ByVal timing As String)
    With c
        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
        .Font.Bold = True

        Select Case Trim$(timing)
            Case "Late"
                .Interior.Color = RGB(255, 199, 206)
                .Font.Color = RGB(156, 0, 6)
            Case "Early"
                .Interior.Color = RGB(221, 235, 247)
                .Font.Color = RGB(0, 32, 96)
            Case "On-Time"
                .Interior.Color = RGB(198, 239, 206)
                .Font.Color = RGB(0, 97, 0)
            Case Else
                .Interior.Pattern = xlNone
                .Font.ColorIndex = xlAutomatic
                .Font.Bold = False
        End Select
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: FormatLocalQtyMismatchRed
' Scope: Private Sub
'
' What it does:
'   Applies or clears visual formatting for FormatLocalQtyMismatchRed.
'
' Why it exists:
'   The intake workbook reconstructs a working Excel sheet from published
'   snapshot JSON, so data and formatting must be applied in a predictable
'   order.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub FormatLocalQtyMismatchRed(ByVal c As Range)
    With c
        .Interior.Color = RGB(255, 199, 206)
        .Font.Color = RGB(156, 0, 6)
        .Font.Bold = True
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: ClearLocalQtyMismatchRed
' Scope: Private Sub
'
' What it does:
'   Reads, validates, compares, or formats quantity values for
'   ClearLocalQtyMismatchRed.
'
' Why it exists:
'   Quantity rules prevent over-scans and keep staged/outbound/received
'   progress aligned with the delivery-list requirement.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ClearLocalQtyMismatchRed(ByVal c As Range)
    With c
        .Interior.Pattern = xlNone
        .Font.ColorIndex = xlAutomatic
        .Font.Bold = False
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: FormatLocalProcessStateCell
' Scope: Private Sub
'
' What it does:
'   Calculates, stores, formats, or displays status/result state for
'   FormatLocalProcessStateCell.
'
' Why it exists:
'   The intake workbook reconstructs a working Excel sheet from published
'   snapshot JSON, so data and formatting must be applied in a predictable
'   order.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub FormatLocalProcessStateCell(ByVal c As Range, ByVal stateText As String)
    With c
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
        .Borders.lineStyle = xlNone

        Select Case UCase$(Trim$(stateText))
            Case "STAGED"
                .Value = "Staged"
                .Interior.Pattern = xlSolid
                .Interior.Color = RGB(217, 217, 217)
                .Font.Color = RGB(64, 64, 64)

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
                .Borders.lineStyle = xlNone
        End Select
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: GetLocalDeliveryProcessStateText
' Scope: Private Function
'
' What it does:
'   Calculates, stores, formats, or displays status/result state for
'   GetLocalDeliveryProcessStateText.
'
' Why it exists:
'   The operator needs to know whether a scan is local, queued, processing,
'   done, errored, or waiting for master confirmation.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function GetLocalDeliveryProcessStateText(ByVal ws As Worksheet, ByVal rowNum As Long) As String
    Dim stagingQty As Long
    Dim sendQty As Long
    Dim recvQty As Long
    Dim recvStatus As String

    stagingQty = CLng(Val(ws.Cells(rowNum, 45).Value))   'AS
    sendQty = CLng(Val(ws.Cells(rowNum, 19).Value))      'S
    recvQty = CLng(Val(ws.Cells(rowNum, 28).Value))      'AB
    recvStatus = UCase$(Trim$(CStr(ws.Cells(rowNum, 30).Value))) 'AD

    If recvQty > 0 Or Len(recvStatus) > 0 Then
        GetLocalDeliveryProcessStateText = "RECEIVED"
    ElseIf sendQty > 0 Then
        GetLocalDeliveryProcessStateText = "OUTBOUND"
    ElseIf stagingQty > 0 Then
        GetLocalDeliveryProcessStateText = "STAGED"
    Else
        GetLocalDeliveryProcessStateText = vbNullString
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: UpdateLocalDeliveryProcessStateForRow
' Scope: Private Sub
'
' What it does:
'   Finds, classifies, updates, hides, shows, highlights, or formats worksheet
'   rows for UpdateLocalDeliveryProcessStateForRow.
'
' Why it exists:
'   Rows can be section headers, real delivery lines, hidden filtered rows,
'   active queue rows, or recently scanned rows; each state affects operator
'   behavior.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub UpdateLocalDeliveryProcessStateForRow(ByVal ws As Worksheet, ByVal rowNum As Long)
    Dim stateText As String

    stateText = GetLocalDeliveryProcessStateText(ws, rowNum)
    FormatLocalProcessStateCell ws.Cells(rowNum, LOCAL_PROCESS_STATE_COL), stateText
End Sub

'------------------------------------------------------------------------------
' Procedure: GetLocalDeliveryDate
' Scope: Private Function
'
' What it does:
'   Parses, selects, calculates, or formats date/time values for
'   GetLocalDeliveryDate.
'
' Why it exists:
'   Queue times, processed times, delivery timing, and scan timestamps must be
'   readable and consistent for operators.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function GetLocalDeliveryDate(ByVal ws As Worksheet) As Date
    Dim c As Range
    Dim txt As String
    Dim tailTxt As String
    Dim i As Long
    Dim ch As String

    For Each c In ws.Range("A1:AG5").Cells
        txt = Trim$(CStr(c.Value))
        If Len(txt) > 0 Then
            If InStr(1, UCase$(txt), "DELIVERY LIST FOR", vbTextCompare) > 0 Then
                tailTxt = Trim$(Replace$(UCase$(txt), "DELIVERY LIST FOR", "", 1, 1, vbTextCompare))

                If Len(tailTxt) > 0 Then
                    If IsDate(tailTxt) Then
                        GetLocalDeliveryDate = DateValue(CDate(tailTxt))
                        Exit Function
                    End If
                End If

                tailTxt = ""
                For i = 1 To Len(txt)
                    ch = Mid$(txt, i, 1)
                    If (ch >= "0" And ch <= "9") Or ch = "/" Or ch = "-" Then
                        tailTxt = tailTxt & ch
                    End If
                Next i

                If Len(tailTxt) > 0 Then
                    If IsDate(tailTxt) Then
                        GetLocalDeliveryDate = DateValue(CDate(tailTxt))
                        Exit Function
                    End If
                End If
            End If
        End If
    Next c
End Function

'------------------------------------------------------------------------------
' Procedure: LocalDeliveryTimingText
' Scope: Private Function
'
' What it does:
'   Parses, selects, calculates, or formats date/time values for
'   LocalDeliveryTimingText.
'
' Why it exists:
'   Queue times, processed times, delivery timing, and scan timestamps must be
'   readable and consistent for operators.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function LocalDeliveryTimingText(ByVal deliveryDate As Date, ByVal scanDateTime As Date) As String
    If deliveryDate = 0 Then Exit Function

    If DateValue(scanDateTime) < deliveryDate Then
        LocalDeliveryTimingText = "Early"
    ElseIf DateValue(scanDateTime) > deliveryDate Then
        LocalDeliveryTimingText = "Late"
    Else
        LocalDeliveryTimingText = "On-Time"
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: RefreshLocalRowVisualState
' Scope: Private Sub
'
' What it does:
'   Finds, classifies, updates, hides, shows, highlights, or formats worksheet
'   rows for RefreshLocalRowVisualState.
'
' Why it exists:
'   Rows can be section headers, real delivery lines, hidden filtered rows,
'   active queue rows, or recently scanned rows; each state affects operator
'   behavior.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub RefreshLocalRowVisualState(ByVal ws As Worksheet, ByVal rowNum As Long)
    Dim sendQty As Long
    Dim recvQty As Long
    Dim requiredQty As Long
    Dim timingText As String
    Dim deliveryDate As Date

    sendQty = CLng(Val(ws.Cells(rowNum, 19).Value))      'S
    recvQty = CLng(Val(ws.Cells(rowNum, 28).Value))      'AB
    requiredQty = CLng(Val(ws.Cells(rowNum, 7).Value))   'G

    'Format all three check columns so whichever stage is active stays correct
    FormatLocalStatusCellByValue ws.Cells(rowNum, 21), Trim$(CStr(ws.Cells(rowNum, 21).Value)) 'U - outbound check
    FormatLocalStatusCellByValue ws.Cells(rowNum, 30), Trim$(CStr(ws.Cells(rowNum, 30).Value)) 'AD - inbound check
    FormatLocalStatusCellByValue ws.Cells(rowNum, 47), Trim$(CStr(ws.Cells(rowNum, 47).Value)) 'AU - staging check

    If recvQty > sendQty And sendQty > 0 Then
        FormatLocalQtyMismatchRed ws.Cells(rowNum, 19)
    Else
        ClearLocalQtyMismatchRed ws.Cells(rowNum, 19)
    End If

    deliveryDate = GetLocalDeliveryDate(ws)
    If IsDate(ws.Cells(rowNum, 20).Value) Then
        timingText = LocalDeliveryTimingText(deliveryDate, CDate(ws.Cells(rowNum, 20).Value))
        ws.Cells(rowNum, 22).Value = timingText
        FormatLocalDeliveryTiming ws.Cells(rowNum, 22), timingText
    Else
        ws.Cells(rowNum, 22).ClearContents
        FormatLocalDeliveryTiming ws.Cells(rowNum, 22), vbNullString
    End If

    UpdateLocalDeliveryProcessStateForRow ws, rowNum
End Sub

'------------------------------------------------------------------------------
' Procedure: RefreshAllLocalStageVisualState
' Scope: Public Sub
'
' What it does:
'   Recalculates the visible local formatting/state for every delivery row on
'   the imported snapshot.
'
' Why it exists:
'   After import, queue updates, or local scans, colors/process-state cells
'   must match the current quantities and statuses.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub RefreshAllLocalStageVisualState(Optional ByVal ws As Worksheet = Nothing)
    Dim workWs As Worksheet
    Dim headerRow As Long
    Dim lastRow As Long
    Dim r As Long

    If ws Is Nothing Then
        Set workWs = StageViewSheet()
    Else
        Set workWs = ws
    End If

    If workWs Is Nothing Then Exit Sub

    headerRow = GetImportedMainHeaderRow(workWs)
    If headerRow = 0 Then Exit Sub

    lastRow = workWs.Cells(workWs.Rows.Count, 5).End(xlUp).Row

    For r = headerRow + 1 To lastRow
        If IsNumeric(workWs.Cells(r, 5).Value) And IsNumeric(workWs.Cells(r, 6).Value) Then
            RefreshLocalRowVisualState workWs, r
        End If
    Next r
End Sub

'------------------------------------------------------------------------------
' Procedure: AutoFitLocalCommentPresentation
' Scope: Private Sub
'
' What it does:
'   Finds, compares, syncs, appends, or formats local comment text for
'   AutoFitLocalCommentPresentation.
'
' Why it exists:
'   Comments added at the intake station need to be preserved and sent back to
'   the master before refresh/settings changes.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub AutoFitLocalCommentPresentation(ByVal ws As Worksheet, ByVal rowNum As Long)
    Dim barcodeCol As Long
    Dim orderCol As Long
    Dim itemCol As Long
    Dim qtyCol As Long
    Dim timeCol As Long
    Dim checkCol As Long
    Dim commentCol As Long
    Dim recentValueCell As Range
    Dim newWidth As Double

    If ws Is Nothing Then Exit Sub
    If rowNum < 1 Then Exit Sub

    If Not GetModeBlockColumns(ModeFromStageProfile(GetSelectedStageProfile()), _
                               barcodeCol, orderCol, itemCol, qtyCol, timeCol, checkCol, commentCol, recentValueCell) Then Exit Sub

    On Error Resume Next

    With ws.Columns(commentCol)
        .WrapText = False
        .ShrinkToFit = False
    End With

    With ws.Cells(rowNum, commentCol)
        .WrapText = False
        .ShrinkToFit = False
        .VerticalAlignment = xlCenter
    End With

    If Not ActiveCommentColumnHasVisibleComments(ws, commentCol) Then
        ws.Columns(commentCol).ColumnWidth = LOCAL_COMMENT_MIN_WIDTH
        On Error GoTo 0
        Exit Sub
    End If

    ws.Columns(commentCol).AutoFit

    newWidth = ws.Columns(commentCol).ColumnWidth

    If newWidth < LOCAL_COMMENT_MIN_WIDTH Then
        newWidth = LOCAL_COMMENT_MIN_WIDTH
    End If

    If newWidth > LOCAL_COMMENT_MAX_WIDTH Then
        newWidth = LOCAL_COMMENT_MAX_WIDTH
    End If

    ws.Columns(commentCol).ColumnWidth = newWidth

    'Do not AutoFit row height. Comments stay one-line.
    ws.Rows(rowNum).WrapText = False

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: AutoFitAllLocalComments
' Scope: Public Sub
'
' What it does:
'   Finds, compares, syncs, appends, or formats local comment text for
'   AutoFitAllLocalComments.
'
' Why it exists:
'   Comments added at the intake station need to be preserved and sent back to
'   the master before refresh/settings changes.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub AutoFitAllLocalComments(Optional ByVal ws As Worksheet = Nothing)
    Dim workWs As Worksheet
    Dim headerRow As Long
    Dim lastRow As Long
    Dim r As Long

    Dim barcodeCol As Long
    Dim orderCol As Long
    Dim itemCol As Long
    Dim qtyCol As Long
    Dim timeCol As Long
    Dim checkCol As Long
    Dim commentCol As Long
    Dim recentValueCell As Range

    Dim newWidth As Double
    Dim hasComments As Boolean

    If ws Is Nothing Then
        Set workWs = StageViewSheet()
    Else
        Set workWs = ws
    End If

    If workWs Is Nothing Then Exit Sub

    headerRow = GetImportedMainHeaderRow(workWs)
    If headerRow = 0 Then Exit Sub

    If Not GetModeBlockColumns(ModeFromStageProfile(GetSelectedStageProfile()), _
                               barcodeCol, orderCol, itemCol, qtyCol, timeCol, checkCol, commentCol, recentValueCell) Then Exit Sub

    lastRow = workWs.Cells(workWs.Rows.Count, 5).End(xlUp).Row

    On Error Resume Next

    With workWs.Columns(commentCol)
        .WrapText = False
        .ShrinkToFit = False
    End With

    For r = headerRow + 1 To lastRow
        If Not workWs.Rows(r).Hidden Then
            workWs.Cells(r, commentCol).WrapText = False
            workWs.Cells(r, commentCol).ShrinkToFit = False
            workWs.Cells(r, commentCol).VerticalAlignment = xlCenter
        End If
    Next r

    hasComments = ActiveCommentColumnHasVisibleComments(workWs, commentCol)

    If Not hasComments Then
        workWs.Columns(commentCol).ColumnWidth = LOCAL_COMMENT_MIN_WIDTH
        On Error GoTo 0
        Exit Sub
    End If

    workWs.Columns(commentCol).AutoFit

    newWidth = workWs.Columns(commentCol).ColumnWidth

    If newWidth < LOCAL_COMMENT_MIN_WIDTH Then
        newWidth = LOCAL_COMMENT_MIN_WIDTH
    End If

    If newWidth > LOCAL_COMMENT_MAX_WIDTH Then
        newWidth = LOCAL_COMMENT_MAX_WIDTH
    End If

    workWs.Columns(commentCol).ColumnWidth = newWidth

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: UpdateMostRecentScanHeader
' Scope: Private Sub
'
' What it does:
'   Cleans, validates, decodes, applies, focuses, or displays scan/barcode
'   data for UpdateMostRecentScanHeader.
'
' Why it exists:
'   The scanner acts like a keyboard, so the workbook must turn entered text
'   into safe order/item updates without duplicate submissions.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub UpdateMostRecentScanHeader(ByVal ws As Worksheet, _
                                       ByVal modeText As String, _
                                       ByVal barcodeText As String, _
                                       ByVal ord As Long, _
                                       ByVal itm As Long, _
                                       ByVal qtyVal As Long, _
                                       ByVal scanTime As Variant, _
                                       ByVal checkText As String)
    Dim startCol As Long
    Dim prevEvents As Boolean

    Select Case UCase$(Trim$(modeText))
        Case "SEND"
            startCol = 16      'P

        Case "RECV"
            startCol = 25      'Y

        Case "STAGING"
            startCol = 42      'AP

        Case Else
            Exit Sub
    End Select

    prevEvents = Application.EnableEvents
    BeginStageProgrammaticUpdate
    Application.EnableEvents = False

    'IMPORTANT:
    'The first cell in the row-4 most-recent block is also the scan input cell.
    'Do not leave barcode/manual text here or it can be submitted again by accident.
    ws.Cells(4, startCol).ClearContents

    'Keep the useful most-recent values, but leave the scan box blank.
    ws.Cells(4, startCol + 1).Value = ord
    ws.Cells(4, startCol + 2).Value = itm
    ws.Cells(4, startCol + 3).Value = qtyVal
    ws.Cells(4, startCol + 4).Value = scanTime
    ws.Cells(4, startCol + 5).Value = checkText

    ws.Cells(4, startCol + 2).NumberFormat = "0"
    ws.Cells(4, startCol + 4).NumberFormat = "m/d/yyyy h:mm AM/PM"

    FormatLocalStatusCellByValue ws.Cells(4, startCol + 5), checkText

SafeExit:
    Application.EnableEvents = prevEvents
    EndStageProgrammaticUpdate
End Sub

'------------------------------------------------------------------------------
' Procedure: ClearHeaderMostRecentFills
' Scope: Private Sub
'
' What it does:
'   Applies or clears visual formatting for ClearHeaderMostRecentFills.
'
' Why it exists:
'   In this workbook, colors and formatting are operational signals that tell
'   users what is complete, partial, mismatched, blocked, or editable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ClearHeaderMostRecentFills(ByVal ws As Worksheet)
    'Most Recent Scan row keeps original formatting
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplyHeaderMostRecentHighlight
' Scope: Private Sub
'
' What it does:
'   Applies a visual state, setting, filter, tab name/color, protection rule,
'   or workflow state for ApplyHeaderMostRecentHighlight.
'
' Why it exists:
'   Apply helpers make refresh/rebuild operations repeatable and help prevent
'   half-updated sheets.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ApplyHeaderMostRecentHighlight(ByVal ws As Worksheet)
    'Do not highlight the Most Recent Scan row
End Sub

'------------------------------------------------------------------------------
' Procedure: LocalPrevalidateAndApplyBarcode
' Scope: Public Function
'
' What it does:
'   Cleans, validates, decodes, applies, focuses, or displays scan/barcode
'   data for LocalPrevalidateAndApplyBarcode.
'
' Why it exists:
'   The scanner acts like a keyboard, so the workbook must turn entered text
'   into safe order/item updates without duplicate submissions.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function LocalPrevalidateAndApplyBarcode(ByVal barcodeText As String, ByRef checkText As String, ByRef resultMessage As String) As Boolean
    Dim ord As Long
    Dim itm As Long

    ord = DecodeBarcodeOrder(barcodeText)
    itm = DecodeBarcodeItem(barcodeText)

    LocalPrevalidateAndApplyBarcode = LocalApplyToImportedStage(ord, itm, 1, barcodeText, vbNullString, False, checkText, resultMessage)
End Function

'------------------------------------------------------------------------------
' Procedure: LocalPrevalidateAndApplyManual
' Scope: Public Function
'
' What it does:
'   Handles manual scan entry or manual scan state for
'   LocalPrevalidateAndApplyManual.
'
' Why it exists:
'   Manual entry is necessary when a label cannot be scanned, but it must
'   still follow the same validation, buffering, and audit path.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function LocalPrevalidateAndApplyManual(ByVal ord As Long, ByVal itm As Long, ByVal qty As Long, ByVal commentText As String, ByRef checkText As String, ByRef resultMessage As String) As Boolean
    LocalPrevalidateAndApplyManual = LocalApplyToImportedStage(ord, itm, qty, "MANUAL", commentText, True, checkText, resultMessage)
End Function

'------------------------------------------------------------------------------
' Procedure: FindImportedHeaderCol
' Scope: Private Function
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   FindImportedHeaderCol.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function FindImportedHeaderCol(ByVal ws As Worksheet, ByVal headerNames As Variant, Optional ByVal topRows As Long = 40) As Long
    Dim nm As Variant
    Dim searchRange As Range
    Dim f As Range

    Set searchRange = Intersect(ws.Rows("1:" & topRows), ws.Range("A:N"))
    If searchRange Is Nothing Then Exit Function

    For Each nm In headerNames
        Set f = searchRange.Find(What:=CStr(nm), LookIn:=xlValues, LookAt:=xlWhole, MatchCase:=False)
        If Not f Is Nothing Then
            FindImportedHeaderCol = f.Column
            Exit Function
        End If
    Next nm

    For Each nm In headerNames
        Set f = searchRange.Find(What:=CStr(nm), LookIn:=xlValues, LookAt:=xlPart, MatchCase:=False)
        If Not f Is Nothing Then
            FindImportedHeaderCol = f.Column
            Exit Function
        End If
    Next nm
End Function

'------------------------------------------------------------------------------
' Procedure: GetImportedProcessStepText
' Scope: Private Function
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   GetImportedProcessStepText.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function GetImportedProcessStepText(ByVal ws As Worksheet, ByVal rowNum As Long) As String
    Dim processStepCol As Long

    processStepCol = FindImportedHeaderCol(ws, Array("Process Step", "ProcessStep", "Step"))
    If processStepCol > 0 Then
        GetImportedProcessStepText = Trim$(CStr(ws.Cells(rowNum, processStepCol).Value))
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: BuildLocalRecvStatus
' Scope: Private Function
'
' What it does:
'   Calculates, stores, formats, or displays status/result state for
'   BuildLocalRecvStatus.
'
' Why it exists:
'   The operator needs to know whether a scan is local, queued, processing,
'   done, errored, or waiting for master confirmation.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function BuildLocalRecvStatus(ByVal recvQty As Long, ByVal sentQty As Long, ByVal requiredQty As Long) As String
    If recvQty > sentQty Then
        BuildLocalRecvStatus = "Mismatch"
    ElseIf recvQty >= requiredQty Then
        BuildLocalRecvStatus = "Received"
    Else
        BuildLocalRecvStatus = "Partial " & recvQty & "/" & requiredQty
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: LocalApplyToImportedStage
' Scope: Private Function
'
' What it does:
'   Applies a barcode/manual scan locally to the imported snapshot, enforcing
'   quantity rules, writing scan values, comments, status text, and most-
'   recent scan display.
'
' Why it exists:
'   Local application gives immediate feedback and prevents obviously bad
'   scans before anything is buffered to SharePoint.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function LocalApplyToImportedStage(ByVal ord As Long, ByVal itm As Long, ByVal qtyToAdd As Long, ByVal barcodeText As String, ByVal commentText As String, ByVal isManual As Boolean, ByRef checkText As String, ByRef resultMessage As String) As Boolean
    Dim ws As Worksheet
    Dim dataRow As Long
    Dim requiredQty As Long
    Dim currentQty As Long
    Dim newQty As Long
    Dim barcodeCol As Long
    Dim orderCol As Long
    Dim itemCol As Long
    Dim qtyCol As Long
    Dim timeCol As Long
    Dim checkCol As Long
    Dim commentCol As Long
    Dim recentValueCell As Range
    Dim modeText As String
    Dim wasProtected As Boolean
    Dim oldEnableEvents As Boolean

    On Error GoTo FailApply

    oldEnableEvents = Application.EnableEvents

    Set ws = StageViewSheet()
    If ws Is Nothing Then Exit Function

    BeginStageProgrammaticUpdate
    Application.EnableEvents = False

    wasProtected = (ws.ProtectContents Or ws.ProtectDrawingObjects Or ws.ProtectScenarios)
    If wasProtected Then ws.Unprotect

    modeText = ModeFromStageProfile(GetSelectedStageProfile())
    dataRow = FindImportedDataRow(ws, ord, itm)

    If dataRow = 0 Then
        resultMessage = "This order/item was not found on the imported stage snapshot."
        GoTo CleanExit
    End If

    If ws.Rows(dataRow).Hidden Then
        resultMessage = "This order/item is not visible on the selected intake stage."
        GoTo CleanExit
    End If

    If Not GetModeBlockColumns(modeText, barcodeCol, orderCol, itemCol, qtyCol, timeCol, checkCol, commentCol, recentValueCell) Then
        resultMessage = "Unsupported stage mode."
        GoTo CleanExit
    End If

    If Not IsNumeric(ws.Cells(dataRow, 7).Value) Then
        resultMessage = "The line does not have a valid required quantity."
        GoTo CleanExit
    End If

    requiredQty = CLng(Val(ws.Cells(dataRow, 7).Value))
    currentQty = CLng(Val(ws.Cells(dataRow, qtyCol).Value))

    If qtyToAdd < 1 Then
        resultMessage = "Scan quantity must be greater than 0."
        GoTo CleanExit
    End If

    If currentQty + qtyToAdd > requiredQty Then
        resultMessage = "This scan would exceed the required quantity for that line."
        GoTo CleanExit
    End If

    newQty = currentQty + qtyToAdd

    If newQty >= requiredQty Then
        checkText = "OK"
    Else
        checkText = "Partial " & newQty & "/" & requiredQty
    End If

    'The scan / most-recent row must never be merged.
    EnsureMostRecentScanRowsUsable ws

    ws.Cells(dataRow, barcodeCol).Value = barcodeText
    ws.Cells(dataRow, orderCol).Value = ord
    ws.Cells(dataRow, itemCol).Value = itm
    ws.Cells(dataRow, qtyCol).Value = newQty
    ws.Cells(dataRow, timeCol).Value = Now
    ws.Cells(dataRow, checkCol).Value = checkText

    If isManual Then
        AppendTextToCell ws.Cells(dataRow, commentCol), BuildLocalManualComment(commentText)
    ElseIf Len(Trim$(commentText)) > 0 Then
        AppendTextToCell ws.Cells(dataRow, commentCol), commentText
    End If

    FormatLocalStatusCellByValue ws.Cells(dataRow, checkCol), checkText
    UpdateLocalDeliveryProcessStateForRow ws, dataRow

    If isManual Then
        UpdateMostRecentScanHeader ws, modeText, "MANUAL", ord, itm, qtyToAdd, Now, checkText
    Else
        UpdateMostRecentScanHeader ws, modeText, barcodeText, ord, itm, qtyToAdd, Now, checkText
    End If

RefreshImportedTopSummaryPanels ws
RefreshLocalRowVisualState ws, dataRow
AutoFitLocalCommentPresentation ws, dataRow

ApplyScanningSideAlignmentAndNumberFormats ws

HighlightImportedRow ws, dataRow, modeText
ScrollImportedRowIntoView ws, dataRow

    resultMessage = checkText
    LocalApplyToImportedStage = True

CleanExit:
    On Error Resume Next

    If wasProtected Then
        ReprotectImportedStageForScanning
    End If

    Application.EnableEvents = oldEnableEvents
    EndStageProgrammaticUpdate

    On Error GoTo 0
    Exit Function

FailApply:
    resultMessage = "Local apply error " & Err.Number & ": " & Err.Description
    Resume CleanExit
End Function

'------------------------------------------------------------------------------
' Procedure: BuildLocalManualComment
' Scope: Private Function
'
' What it does:
'   Handles manual scan entry or manual scan state for
'   BuildLocalManualComment.
'
' Why it exists:
'   Manual entry is necessary when a label cannot be scanned, but it must
'   still follow the same validation, buffering, and audit path.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function BuildLocalManualComment(ByVal commentText As String) As String
    commentText = Trim$(CStr(commentText))

    If Len(commentText) > 0 Then
        BuildLocalManualComment = "Manual: " & commentText
    Else
        BuildLocalManualComment = "Manual"
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: AppendTextToCell
' Scope: Private Sub
'
' What it does:
'   Appends text safely to an existing cell/message for AppendTextToCell.
'
' Why it exists:
'   Append helpers preserve prior operator/master context while adding new
'   details without duplicating the same message.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub AppendTextToCell(ByVal targetCell As Range, ByVal appendText As String)
    appendText = Trim$(appendText)
    If Len(appendText) = 0 Then Exit Sub
    If targetCell Is Nothing Then Exit Sub

    If Len(Trim$(CStr(targetCell.Value))) > 0 Then
        targetCell.Value = CStr(targetCell.Value) & " | " & appendText
    Else
        targetCell.Value = appendText
    End If

    targetCell.WrapText = False
    targetCell.ShrinkToFit = False
    targetCell.VerticalAlignment = xlCenter

    AutoFitLocalCommentPresentation targetCell.Worksheet, targetCell.Row
End Sub

'------------------------------------------------------------------------------
' Procedure: RecentScanHighlightColor
' Scope: Private Function
'
' What it does:
'   Cleans, validates, decodes, applies, focuses, or displays scan/barcode
'   data for RecentScanHighlightColor.
'
' Why it exists:
'   The scanner acts like a keyboard, so the workbook must turn entered text
'   into safe order/item updates without duplicate submissions.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function RecentScanHighlightColor() As Long
    RecentScanHighlightColor = RGB(255, 255, 153)
End Function

'------------------------------------------------------------------------------
' Procedure: CellHasRecentScanHighlight
' Scope: Private Function
'
' What it does:
'   Cleans, validates, decodes, applies, focuses, or displays scan/barcode
'   data for CellHasRecentScanHighlight.
'
' Why it exists:
'   The scanner acts like a keyboard, so the workbook must turn entered text
'   into safe order/item updates without duplicate submissions.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function CellHasRecentScanHighlight(ByVal c As Range) As Boolean
    On Error GoTo SafeExit

    If c Is Nothing Then Exit Function
    If c.Interior.Pattern = xlNone Then Exit Function

    CellHasRecentScanHighlight = (CLng(c.Interior.Color) = RecentScanHighlightColor())

SafeExit:
End Function

'------------------------------------------------------------------------------
' Procedure: ClearRecentScanHighlightRange
' Scope: Private Sub
'
' What it does:
'   Cleans, validates, decodes, applies, focuses, or displays scan/barcode
'   data for ClearRecentScanHighlightRange.
'
' Why it exists:
'   The scanner acts like a keyboard, so the workbook must turn entered text
'   into safe order/item updates without duplicate submissions.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ClearRecentScanHighlightRange(ByVal rng As Range)
    Dim c As Range

    If rng Is Nothing Then Exit Sub

    On Error Resume Next

    For Each c In rng.Cells
        If CellHasRecentScanHighlight(c) Then
            c.Interior.Pattern = xlNone
        End If
    Next c

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplyRecentScanHighlightRange
' Scope: Private Sub
'
' What it does:
'   Cleans, validates, decodes, applies, focuses, or displays scan/barcode
'   data for ApplyRecentScanHighlightRange.
'
' Why it exists:
'   The scanner acts like a keyboard, so the workbook must turn entered text
'   into safe order/item updates without duplicate submissions.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ApplyRecentScanHighlightRange(ByVal rng As Range)
    If rng Is Nothing Then Exit Sub

    On Error Resume Next

    With rng.Interior
        .Pattern = xlSolid
        .Color = RecentScanHighlightColor()
    End With

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: ClearAllRecentScanHighlights
' Scope: Private Sub
'
' What it does:
'   Cleans, validates, decodes, applies, focuses, or displays scan/barcode
'   data for ClearAllRecentScanHighlights.
'
' Why it exists:
'   The scanner acts like a keyboard, so the workbook must turn entered text
'   into safe order/item updates without duplicate submissions.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ClearAllRecentScanHighlights(ByVal ws As Worksheet)
    Dim headerRow As Long
    Dim lastRow As Long
    Dim r As Long

    If ws Is Nothing Then Exit Sub

    headerRow = GetImportedMainHeaderRow(ws)
    If headerRow = 0 Then Exit Sub

    lastRow = ws.Cells(ws.Rows.Count, 5).End(xlUp).Row
    If lastRow <= headerRow Then Exit Sub

    On Error Resume Next

    For r = headerRow + 1 To lastRow
        'Only real order/item rows.
        If IsNumeric(ws.Cells(r, 5).Value) And IsNumeric(ws.Cells(r, 6).Value) Then
            'Delivery-list side highlight area.
            ClearRecentScanHighlightRange ws.Range(ws.Cells(r, 1), ws.Cells(r, 10))

            'Outbound scan-side highlight area: Barcode through Date/Time.
            ClearRecentScanHighlightRange ws.Range(ws.Cells(r, 16), ws.Cells(r, 20))

            'Inbound scan-side highlight area: Barcode through Date/Time.
            ClearRecentScanHighlightRange ws.Range(ws.Cells(r, 25), ws.Cells(r, 29))

            'Staging scan-side highlight area: Barcode through Date/Time.
            ClearRecentScanHighlightRange ws.Range(ws.Cells(r, 42), ws.Cells(r, 46))
        End If
    Next r

    mLastHighlightRow = 0
    mLastHighlightMode = vbNullString

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: ClearPreviousHighlight
' Scope: Private Sub
'
' What it does:
'   Clears temporary values, old state, helper data, formatting, or scan-box
'   contents for ClearPreviousHighlight.
'
' Why it exists:
'   Stale values can trigger duplicate scans or mislead the operator after a
'   refresh, alert, or settings change.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ClearPreviousHighlight(ByVal ws As Worksheet)
    'Do not rely only on mLastHighlightRow.
    'If a prior highlight was orphaned by refresh/polling/reset, sweep all recent-scan yellow highlights.
    ClearAllRecentScanHighlights ws
End Sub

'------------------------------------------------------------------------------
' Procedure: HighlightImportedRow
' Scope: Private Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   HighlightImportedRow.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub HighlightImportedRow(ByVal ws As Worksheet, ByVal rowNum As Long, ByVal modeText As String)
    Dim barcodeCol As Long
    Dim orderCol As Long
    Dim itemCol As Long
    Dim qtyCol As Long
    Dim timeCol As Long
    Dim checkCol As Long
    Dim commentCol As Long
    Dim recentValueCell As Range

    If ws Is Nothing Then Exit Sub
    If rowNum <= 0 Then Exit Sub

    'Clear every old recent-scan highlight first.
    ClearAllRecentScanHighlights ws

    If Not GetModeBlockColumns(modeText, barcodeCol, orderCol, itemCol, qtyCol, timeCol, checkCol, commentCol, recentValueCell) Then Exit Sub

    On Error Resume Next

    'Left delivery-list side: Job Nr. through Customer.
    ApplyRecentScanHighlightRange ws.Range(ws.Cells(rowNum, 1), ws.Cells(rowNum, 10))

    'Active scanning side only: Barcode through Date/Time Scanned.
    ApplyRecentScanHighlightRange ws.Range(ws.Cells(rowNum, barcodeCol), ws.Cells(rowNum, timeCol))

    mLastHighlightRow = rowNum
    mLastHighlightMode = modeText

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: ClearRecentScanHighlightsNow
' Scope: Public Sub
'
' What it does:
'   Cleans, validates, decodes, applies, focuses, or displays scan/barcode
'   data for ClearRecentScanHighlightsNow.
'
' Why it exists:
'   The scanner acts like a keyboard, so the workbook must turn entered text
'   into safe order/item updates without duplicate submissions.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub ClearRecentScanHighlightsNow()
    Dim ws As Worksheet

    Set ws = StageViewSheet()
    If ws Is Nothing Then Exit Sub

    ClearAllRecentScanHighlights ws
    FocusStageScanBox
End Sub

'------------------------------------------------------------------------------
' Procedure: ScrollImportedRowIntoView
' Scope: Private Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   ScrollImportedRowIntoView.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ScrollImportedRowIntoView(ByVal ws As Worksheet, ByVal rowNum As Long)
    Dim visibleRows As Long
    Dim targetScrollRow As Long
    Dim desiredRowPosition As Long

    If ws Is Nothing Then Exit Sub
    If rowNum < 1 Then Exit Sub

    On Error Resume Next

    EnsureStageWindowLayout ws, False
    ws.Activate

    If ActiveWindow.Panes.Count < 4 Then Exit Sub

    visibleRows = ActiveWindow.Panes(3).VisibleRange.Rows.Count
    If visibleRows < 8 Then visibleRows = 20

    'Lower-middle of the visible pane
    desiredRowPosition = CLng(visibleRows * 0.7)
    If desiredRowPosition < 1 Then desiredRowPosition = 1

    targetScrollRow = rowNum - desiredRowPosition + 1
    If targetScrollRow < 1 Then targetScrollRow = 1

    ActiveWindow.Panes(3).ScrollRow = targetScrollRow
    ActiveWindow.Panes(4).ScrollRow = targetScrollRow

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: FindImportedDataRow
' Scope: Public Function
'
' What it does:
'   Locates the imported snapshot row matching an order/item pair.
'
' Why it exists:
'   Most scan, queue, and comment operations start from order/item identity
'   and need the matching visible row.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function FindImportedDataRow(ByVal ws As Worksheet, ByVal ord As Long, ByVal itm As Long) As Long
    Dim headerRow As Long
    Dim lastRow As Long
    Dim r As Long

    If ws Is Nothing Then Exit Function

    headerRow = GetImportedMainHeaderRow(ws)
    If headerRow = 0 Then Exit Function

    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row

    For r = headerRow + 1 To lastRow
        If Not ws.Rows(r).Hidden Then
            If IsNumeric(ws.Cells(r, 5).Value) And IsNumeric(ws.Cells(r, 6).Value) Then
                If CLng(Val(ws.Cells(r, 5).Value)) = ord And _
                   CLng(Val(ws.Cells(r, 6).Value)) = itm Then

                    FindImportedDataRow = r
                    Exit Function
                End If
            End If
        End If
    Next r
End Function

'------------------------------------------------------------------------------
' Procedure: GetModeBlockColumns
' Scope: Public Function
'
' What it does:
'   Returns the scan block columns for the active stage mode: staging,
'   outbound/send, or inbound/receive.
'
' Why it exists:
'   One imported sheet contains multiple scan blocks, so each operation must
'   write to the correct block for the selected stage.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function GetModeBlockColumns(ByVal modeText As String, ByRef barcodeCol As Long, ByRef orderCol As Long, ByRef itemCol As Long, ByRef qtyCol As Long, ByRef timeCol As Long, ByRef checkCol As Long, ByRef commentCol As Long, ByRef recentValueCell As Range) As Boolean
    Dim ws As Worksheet
    Set ws = StageViewSheet()
    If ws Is Nothing Then Exit Function

    Select Case UCase$(Trim$(modeText))
        Case "SEND"
            barcodeCol = 16
            orderCol = 17
            itemCol = 18
            qtyCol = 19
            timeCol = 20
            checkCol = 21
            commentCol = 23
            Set recentValueCell = ws.Cells(4, 16)

        Case "RECV"
            barcodeCol = 25
            orderCol = 26
            itemCol = 27
            qtyCol = 28
            timeCol = 29
            checkCol = 30
            commentCol = 32
            Set recentValueCell = ws.Cells(4, 25)

        Case "STAGING"
            barcodeCol = 42
            orderCol = 43
            itemCol = 44
            qtyCol = 45
            timeCol = 46
            checkCol = 47
            commentCol = 48
            Set recentValueCell = ws.Cells(4, 42)

        Case Else
            Exit Function
    End Select

    GetModeBlockColumns = True
End Function

'------------------------------------------------------------------------------
' Procedure: SyncPendingStageComments
' Scope: Public Function
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   SyncPendingStageComments.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function SyncPendingStageComments() As Long
    Dim syncedCount As Long
    Dim errorMessage As String

    If Not SyncPendingStageCommentsToMaster(60, syncedCount, errorMessage) Then
        Err.Raise vbObjectError + 9101, "SyncPendingStageComments", errorMessage
    End If

    SyncPendingStageComments = syncedCount
End Function

'------------------------------------------------------------------------------
' Procedure: SyncPendingStageCommentsToMaster
' Scope: Public Function
'
' What it does:
'   Finds local comment changes on the imported stage and queues/sends them to
'   the master queue workflow.
'
' Why it exists:
'   Comments typed at intake need to reach the master; otherwise they are lost
'   when the snapshot refreshes or the user changes stages.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function SyncPendingStageCommentsToMaster(Optional ByVal waitSecondsPerComment As Long = 60, _
                                                 Optional ByRef syncedCount As Long = 0, _
                                                 Optional ByRef errorMessage As String = vbNullString) As Boolean
    Dim ws As Worksheet
    Dim headerRow As Long
    Dim lastRow As Long
    Dim r As Long

    Dim barcodeCol As Long
    Dim orderCol As Long
    Dim itemCol As Long
    Dim qtyCol As Long
    Dim timeCol As Long
    Dim checkCol As Long
    Dim commentCol As Long
    Dim recentValueCell As Range

    Dim modeText As String
    Dim targetSheet As String
    Dim stationName As String
    Dim deliveryKey As String

    Dim ord As Long
    Dim itm As Long
    Dim currentComment As String
    Dim originalComment As String
    Dim commentPayload As String
    Dim requestId As String

    On Error GoTo FailSync

    syncedCount = 0
    errorMessage = vbNullString

    Set ws = StageViewSheet()
    If ws Is Nothing Then
        SyncPendingStageCommentsToMaster = True
        Exit Function
    End If

    If Not IsImportedStageLoaded() Then
        SyncPendingStageCommentsToMaster = True
        Exit Function
    End If

    deliveryKey = GetSelectedDeliveryKey()
    stationName = GetStationName()
    modeText = ModeFromStageProfile(GetSelectedStageProfile())
    targetSheet = StageSheetFromProfile(GetSelectedStageProfile())

    If Len(deliveryKey) = 0 Then
        errorMessage = "Cannot sync comments because no delivery list is selected."
        Exit Function
    End If

    If Len(modeText) = 0 Then
        errorMessage = "Cannot sync comments because the selected stage mode is blank."
        Exit Function
    End If

    If Len(targetSheet) = 0 Then
        errorMessage = "Cannot sync comments because the selected target sheet is blank."
        Exit Function
    End If

    If Not GetModeBlockColumns(modeText, barcodeCol, orderCol, itemCol, qtyCol, timeCol, checkCol, commentCol, recentValueCell) Then
        errorMessage = "Cannot sync comments because the selected stage comments column could not be determined."
        Exit Function
    End If

    headerRow = GetImportedMainHeaderRow(ws)
    If headerRow = 0 Then
        SyncPendingStageCommentsToMaster = True
        Exit Function
    End If

    lastRow = ws.Cells(ws.Rows.Count, 5).End(xlUp).Row

    For r = headerRow + 1 To lastRow
        If Not ws.Rows(r).Hidden Then
            If IsNumeric(ws.Cells(r, 5).Value) And IsNumeric(ws.Cells(r, 6).Value) Then
                ord = CLng(Val(ws.Cells(r, 5).Value))
                itm = CLng(Val(ws.Cells(r, 6).Value))

                currentComment = CleanStageSyncCommentText(ws.Cells(r, commentCol).Value)
                originalComment = CleanStageSyncCommentText(ws.Cells(r, COMMENT_BASELINE_COL).Value)

                If StrComp(currentComment, originalComment, vbTextCompare) <> 0 Then
    requestId = BuildRequestId(stationName)

    'Send the FULL desired comments-cell value, not only an appended delta.
    'This allows edits and deletes to update the master correctly.
    commentPayload = COMMENT_SET_PREFIX & currentComment

    If Not PA_QueueAddRequest( _
            requestId, _
            deliveryKey, _
            "COMMENT", _
            modeText, _
            vbNullString, _
            ord, _
            itm, _
            0, _
            targetSheet, _
            stationName, _
            commentPayload) Then

        errorMessage = "Power Automate did not accept comment sync for Order " & ord & _
                       " / Item " & Format$(itm, "000") & "."
        Exit Function
    End If

    If Not WaitForCommentSyncRequestDone(requestId, waitSecondsPerComment, errorMessage) Then
        If Len(errorMessage) = 0 Then
            errorMessage = "Timed out syncing comment for Order " & ord & _
                           " / Item " & Format$(itm, "000") & "."
        End If

        Exit Function
    End If

    'The master accepted this exact comment value. Mark it as the new baseline.
    ws.Cells(r, COMMENT_BASELINE_COL).Value = currentComment
    syncedCount = syncedCount + 1
End If
            End If
        End If
    Next r

    SyncPendingStageCommentsToMaster = True
    Exit Function

FailSync:
    errorMessage = "Comment sync failed. Error " & Err.Number & ": " & Err.Description
End Function

'------------------------------------------------------------------------------
' Procedure: WaitForCommentSyncRequestDone
' Scope: Private Function
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   WaitForCommentSyncRequestDone.
'
' Why it exists:
'   Scans move through local buffer, SharePoint ScanQueue, master processing,
'   and final intake confirmation; this state must stay traceable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function WaitForCommentSyncRequestDone(ByVal requestId As String, _
                                               ByVal timeoutSeconds As Long, _
                                               ByRef errorMessage As String) As Boolean
    Dim startedAt As Date
    Dim item As Object
    Dim statusText As String
    Dim resultCode As String
    Dim resultMessage As String

    requestId = Trim$(CStr(requestId))
    If Len(requestId) = 0 Then
        errorMessage = "Comment sync request ID was blank."
        Exit Function
    End If

    If timeoutSeconds < 10 Then timeoutSeconds = 10

    startedAt = Now

    Do
        DoEvents

        Set item = PA_QueueGetRequestStatus(requestId)

        If Not item Is Nothing Then
            statusText = Trim$(PA_DictText(item, "status"))
            resultCode = Trim$(PA_DictText(item, "resultCode"))
            resultMessage = Trim$(PA_DictText(item, "resultMessage"))

            If StrComp(statusText, "Done", vbTextCompare) = 0 Then
                WaitForCommentSyncRequestDone = True
                Exit Function
            End If

            If StrComp(statusText, "Error", vbTextCompare) = 0 Then
                If Len(resultMessage) > 0 Then
                    errorMessage = resultMessage
                ElseIf Len(resultCode) > 0 Then
                    errorMessage = resultCode
                Else
                    errorMessage = "The master returned Error for comment sync request " & requestId & "."
                End If

                Exit Function
            End If
        End If

        If DateDiff("s", startedAt, Now) >= timeoutSeconds Then
            errorMessage = "Timed out waiting for the master to save comment sync request " & requestId & "."
            Exit Function
        End If

        Application.Wait Now + TimeSerial(0, 0, 2)
    Loop
End Function

'------------------------------------------------------------------------------
' Procedure: CleanStageSyncCommentText
' Scope: Private Function
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   CleanStageSyncCommentText.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function CleanStageSyncCommentText(ByVal valueIn As Variant) As String
    Dim s As String

    s = Trim$(CStr(valueIn))

    s = Replace$(s, vbCrLf, " | ")
    s = Replace$(s, vbCr, " | ")
    s = Replace$(s, vbLf, " | ")
    s = Replace$(s, vbTab, " ")

    Do While InStr(1, s, "  ", vbBinaryCompare) > 0
        s = Replace$(s, "  ", " ")
    Loop

    Do While InStr(1, s, "| |", vbBinaryCompare) > 0
        s = Replace$(s, "| |", "|")
    Loop

    CleanStageSyncCommentText = Trim$(s)
End Function

'------------------------------------------------------------------------------
' Procedure: QueueStageCommentRow
' Scope: Private Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   QueueStageCommentRow.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub QueueStageCommentRow(ByVal qWs As Worksheet, ByVal ord As Long, ByVal itm As Long, ByVal commentText As String)
    Dim rowNum As Long
    Dim requestId As String

    rowNum = NextQueueRow(qWs)
    requestId = BuildRequestId(GetStationName())

    qWs.Cells(rowNum, 1).Value = requestId
    qWs.Cells(rowNum, 2).Value = GetSelectedDeliveryKey()
    qWs.Cells(rowNum, 3).Value = "COMMENT"
    qWs.Cells(rowNum, 5).Value = ModeFromStageProfile(GetSelectedStageProfile())
    qWs.Cells(rowNum, 6).Value = ord
    qWs.Cells(rowNum, 7).Value = itm
    qWs.Cells(rowNum, 9).Value = GetSelectedStageProfile()
    qWs.Cells(rowNum, 10).Value = GetStationName()
    qWs.Cells(rowNum, 11).Value = Now
    qWs.Cells(rowNum, 12).Value = "Queued"
    qWs.Cells(rowNum, 16).Value = commentText
End Sub

'------------------------------------------------------------------------------
' Procedure: GetAppendedCommentDelta
' Scope: Private Function
'
' What it does:
'   Finds, compares, syncs, appends, or formats local comment text for
'   GetAppendedCommentDelta.
'
' Why it exists:
'   Comments added at the intake station need to be preserved and sent back to
'   the master before refresh/settings changes.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function GetAppendedCommentDelta(ByVal originalText As String, ByVal currentText As String) As String
    Dim deltaText As String

    originalText = Trim$(originalText)
    currentText = Trim$(currentText)

    If Len(currentText) = 0 Then Exit Function
    If StrComp(currentText, originalText, vbTextCompare) = 0 Then Exit Function

    If Len(originalText) > 0 Then
        If Left$(currentText, Len(originalText)) = originalText Then
            deltaText = Mid$(currentText, Len(originalText) + 1)
            deltaText = Replace$(deltaText, vbCrLf, vbLf)
            Do While Left$(deltaText, 1) = vbLf
                deltaText = Mid$(deltaText, 2)
            Loop
            deltaText = Trim$(deltaText)
            GetAppendedCommentDelta = deltaText
            Exit Function
        End If
    End If

    GetAppendedCommentDelta = currentText
End Function

'------------------------------------------------------------------------------
' Procedure: UpdateImportedRowFromMasterResult
' Scope: Public Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   UpdateImportedRowFromMasterResult.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub UpdateImportedRowFromMasterResult(ByVal qWs As Worksheet, ByVal rowNum As Long)
    Dim reqType As String
    Dim barcodeText As String
    Dim ord As Long
    Dim itm As Long
    Dim qty As Long
    Dim statusText As String
    Dim resultCode As String
    Dim resultMessage As String
    Dim requestComment As String
    Dim ws As Worksheet
    Dim dataRow As Long
    Dim barcodeCol As Long
    Dim orderCol As Long
    Dim itemCol As Long
    Dim qtyCol As Long
    Dim timeCol As Long
    Dim checkCol As Long
    Dim commentCol As Long
    Dim recentValueCell As Range
    Dim modeText As String

    Set ws = StageViewSheet()
    If ws Is Nothing Then Exit Sub

    modeText = ModeFromStageProfile(GetSelectedStageProfile())

    reqType = UCase$(Trim$(CStr(qWs.Cells(rowNum, 3).Value)))
    barcodeText = Trim$(CStr(qWs.Cells(rowNum, 4).Value))
    ord = CLng(Val(qWs.Cells(rowNum, 6).Value))
    itm = CLng(Val(qWs.Cells(rowNum, 7).Value))
    qty = CLng(Val(qWs.Cells(rowNum, 8).Value))
    statusText = Trim$(CStr(qWs.Cells(rowNum, 12).Value))
    resultCode = Trim$(CStr(qWs.Cells(rowNum, 14).Value))
    resultMessage = Trim$(CStr(qWs.Cells(rowNum, 15).Value))
    requestComment = Trim$(CStr(qWs.Cells(rowNum, 16).Value))

    If reqType = "BARCODE" Then
        If ord = 0 Then ord = DecodeBarcodeOrder(barcodeText)
        If itm = 0 Then itm = DecodeBarcodeItem(barcodeText)
        If qty = 0 Then qty = 1
    End If

    dataRow = FindImportedDataRow(ws, ord, itm)
    If dataRow = 0 Then Exit Sub

    If Not GetModeBlockColumns(modeText, barcodeCol, orderCol, itemCol, qtyCol, timeCol, checkCol, commentCol, recentValueCell) Then Exit Sub

    If IsDate(qWs.Cells(rowNum, 13).Value) Then
        ws.Cells(dataRow, timeCol).Value = qWs.Cells(rowNum, 13).Value
    End If

    If StrComp(statusText, "Done", vbTextCompare) = 0 Then
        Select Case reqType
            Case "COMMENT"
                ws.Cells(dataRow, COMMENT_BASELINE_COL).Value = CStr(ws.Cells(dataRow, commentCol).Value)

            Case Else
                If Len(resultMessage) > 0 Then
                    ws.Cells(dataRow, checkCol).Value = resultMessage
                ElseIf Len(resultCode) > 0 Then
                    ws.Cells(dataRow, checkCol).Value = resultCode
                Else
                    ws.Cells(dataRow, checkCol).Value = "Done"
                End If

                                UpdateMostRecentScanHeader ws, modeText, barcodeText, ord, itm, qty, ws.Cells(dataRow, timeCol).Value, ws.Cells(dataRow, checkCol).Value
                                RefreshImportedTopSummaryPanels ws
                                RefreshLocalRowVisualState ws, dataRow
                                AutoFitLocalCommentPresentation ws, dataRow
                                HighlightImportedRow ws, dataRow, modeText
        End Select

    ElseIf StrComp(statusText, "Error", vbTextCompare) = 0 Then
        ws.Cells(dataRow, checkCol).Value = "MASTER ERROR"
        AppendTextToCell ws.Cells(dataRow, commentCol), resultMessage
        RefreshLocalRowVisualState ws, dataRow
        AutoFitLocalCommentPresentation ws, dataRow
        HighlightImportedRow ws, dataRow, modeText
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: ShortQueueStateText
' Scope: Public Function
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   ShortQueueStateText.
'
' Why it exists:
'   Scans move through local buffer, SharePoint ScanQueue, master processing,
'   and final intake confirmation; this state must stay traceable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function ShortQueueStateText(ByVal statusText As String) As String
    Select Case UCase$(Trim$(CStr(statusText)))
        Case "BUFFERED LOCALLY", "LOCAL", "BUFFERED"
            ShortQueueStateText = "Local"

        Case "QUEUED"
            ShortQueueStateText = "Queued"

        Case "PROCESSING", "WORKING"
            ShortQueueStateText = "Working"

        Case "DONE", "OK"
            ShortQueueStateText = "Done"

        Case "ERROR", "FAILED", "MASTER ERROR"
            ShortQueueStateText = "Error"

        Case "MISSING", "NOT FOUND", "NOTFOUND"
            ShortQueueStateText = "Missing"

        Case "PA FAIL", "PA_FAILED", "FLOW ERROR"
            ShortQueueStateText = "PA Fail"

        Case Else
            If Len(Trim$(CStr(statusText))) = 0 Then
                ShortQueueStateText = vbNullString
            Else
                ShortQueueStateText = Left$(Trim$(CStr(statusText)), 12)
            End If
    End Select
End Function

'------------------------------------------------------------------------------
' Procedure: FormatLocalQueueStateCell
' Scope: Private Sub
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   FormatLocalQueueStateCell.
'
' Why it exists:
'   The intake workbook reconstructs a working Excel sheet from published
'   snapshot JSON, so data and formatting must be applied in a predictable
'   order.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub FormatLocalQueueStateCell(ByVal c As Range, ByVal stateText As String)
    Dim stateUpper As String

    stateUpper = UCase$(Trim$(CStr(stateText)))

    With c
        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
        .WrapText = False
        .ShrinkToFit = True
        .Font.Bold = True

        Select Case stateUpper
            Case "LOCAL", "BUFFERED", "BUFFERED LOCALLY", "QUEUED"
                .Interior.Color = RGB(255, 242, 204)
                .Font.Color = RGB(156, 101, 0)

            Case "PROCESSING", "WORKING"
                .Interior.Color = RGB(221, 235, 247)
                .Font.Color = RGB(0, 32, 96)

            Case "DONE", "OK"
                .Interior.Color = RGB(198, 239, 206)
                .Font.Color = RGB(0, 97, 0)

            Case "ERROR", "FAILED", "MASTER ERROR", "PA FAIL", "PA_FAILED", "FLOW ERROR"
                .Interior.Color = RGB(255, 199, 206)
                .Font.Color = RGB(156, 0, 6)

            Case "MISSING", "NOT FOUND", "NOTFOUND"
                .Interior.Color = RGB(217, 217, 217)
                .Font.Color = RGB(64, 64, 64)

            Case Else
                .Interior.Pattern = xlNone
                .Font.ColorIndex = xlAutomatic
                .Font.Bold = False
        End Select
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: InitializeLocalQueueStateColumn
' Scope: Private Sub
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   InitializeLocalQueueStateColumn.
'
' Why it exists:
'   Scans move through local buffer, SharePoint ScanQueue, master processing,
'   and final intake confirmation; this state must stay traceable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub InitializeLocalQueueStateColumn(ByVal ws As Worksheet)
    Dim headerRow As Long
    Dim lastRow As Long

    headerRow = GetImportedMainHeaderRow(ws)
    If headerRow = 0 Then Exit Sub

    lastRow = ws.Cells(ws.Rows.Count, 5).End(xlUp).Row

    ws.Cells(headerRow, LOCAL_QUEUE_STATE_COL).Value = "Queue State"
    ws.Cells(headerRow, LOCAL_QUEUE_STATE_COL).Font.Bold = True
    ws.Cells(headerRow, LOCAL_QUEUE_STATE_COL).HorizontalAlignment = xlCenter
    ws.Columns(LOCAL_QUEUE_STATE_COL).ColumnWidth = 12

    If lastRow > headerRow Then
        ws.Range(ws.Cells(headerRow + 1, LOCAL_QUEUE_STATE_COL), ws.Cells(lastRow, LOCAL_QUEUE_STATE_COL)).ClearContents
    End If

    ws.Cells(1, LOCAL_QUEUE_REQUEST_COL).Value = "QueueRequestId"
    ws.Cells(1, LOCAL_QUEUE_RESULT_COL).Value = "QueueResultMessage"
    ws.Columns("BA:BB").Hidden = True
End Sub

'------------------------------------------------------------------------------
' Procedure: SeedImportedQueueStateFromMaster
' Scope: Public Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   SeedImportedQueueStateFromMaster.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub SeedImportedQueueStateFromMaster(ByVal ws As Worksheet)
    Dim headerRow As Long
    Dim lastRow As Long
    Dim r As Long
    Dim queueState As String

    headerRow = GetImportedMainHeaderRow(ws)
    If headerRow = 0 Then Exit Sub

    lastRow = ws.Cells(ws.Rows.Count, 5).End(xlUp).Row

    For r = headerRow + 1 To lastRow
        If IsNumeric(ws.Cells(r, 5).Value) And IsNumeric(ws.Cells(r, 6).Value) Then
            queueState = GetImportedQueueStateFromMasterRow(ws, r)

            ws.Cells(r, LOCAL_QUEUE_STATE_COL).Value = queueState
            ws.Cells(r, LOCAL_QUEUE_REQUEST_COL).Value = vbNullString
            ws.Cells(r, LOCAL_QUEUE_RESULT_COL).Value = vbNullString

            If Len(queueState) > 0 Then
                FormatLocalQueueStateCell ws.Cells(r, LOCAL_QUEUE_STATE_COL), queueState
            Else
                FormatLocalQueueStateCell ws.Cells(r, LOCAL_QUEUE_STATE_COL), vbNullString
            End If
        End If
    Next r
End Sub

'------------------------------------------------------------------------------
' Procedure: SetImportedRowQueueState
' Scope: Public Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   SetImportedRowQueueState.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub SetImportedRowQueueState(ByVal ord As Long, ByVal itm As Long, ByVal requestId As String, ByVal statusText As String, Optional ByVal resultMessage As String = vbNullString)
    Dim ws As Worksheet
    Dim dataRow As Long

    Set ws = StageViewSheet()
    If ws Is Nothing Then Exit Sub

    dataRow = FindImportedDataRow(ws, ord, itm)
    If dataRow = 0 Then Exit Sub

    ws.Cells(dataRow, LOCAL_QUEUE_STATE_COL).Value = ShortQueueStateText(statusText)
    ws.Cells(dataRow, LOCAL_QUEUE_REQUEST_COL).Value = requestId
    ws.Cells(dataRow, LOCAL_QUEUE_RESULT_COL).Value = resultMessage

    FormatLocalQueueStateCell ws.Cells(dataRow, LOCAL_QUEUE_STATE_COL), statusText
End Sub

'------------------------------------------------------------------------------
' Procedure: BuildQueueStateDisplay
' Scope: Private Function
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   BuildQueueStateDisplay.
'
' Why it exists:
'   Scans move through local buffer, SharePoint ScanQueue, master processing,
'   and final intake confirmation; this state must stay traceable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function BuildQueueStateDisplay(ByVal statusText As String, ByVal resultMessage As String) As String
    Dim s As String
    Dim msg As String

    s = Trim$(CStr(statusText))
    msg = Trim$(CStr(resultMessage))

    If Len(s) = 0 Then
        s = "Queued"
    End If

    If Left$(UCase$(msg), 14) = "[MASTER FINAL]" Then
        msg = Trim$(Mid$(msg, 15))
    End If

    If Len(msg) = 0 Then
        BuildQueueStateDisplay = s
    Else
        BuildQueueStateDisplay = s & " - " & Left$(msg, 60)
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: RefreshPendingImportedQueueStates
' Scope: Public Sub
'
' What it does:
'   Checks active request IDs stored on imported rows and updates those rows
'   from the latest SharePoint queue status.
'
' Why it exists:
'   Rows can have multiple pending local scans, so the sheet needs row-level
'   queue watching in addition to the last-request panel.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub RefreshPendingImportedQueueStates(Optional ByVal fullSweep As Boolean = False)

    If IsScanAlertActive() Then Exit Sub

    Dim ws As Worksheet
    Dim headerRow As Long
    Dim lastRow As Long
    Dim r As Long

    Dim requestId As String
    Dim item As Object

    Dim localState As String
    Dim localResultText As String
    Dim statusText As String
    Dim resultCode As String
    Dim resultMessage As String

    Dim anyActive As Boolean
    Dim checkedThisPass As Long
    Dim maxChecksThisPass As Long
    Dim isTerminalFromMaster As Boolean
    
    

    Set ws = StageViewSheet()
    If ws Is Nothing Then Exit Sub
    If Not IsImportedStageLoaded() Then Exit Sub

    headerRow = GetImportedMainHeaderRow(ws)
    If headerRow = 0 Then Exit Sub

    lastRow = ws.Cells(ws.Rows.Count, 5).End(xlUp).Row

    If fullSweep Then
        maxChecksThisPass = 12
    Else
        maxChecksThisPass = 2
    End If

    For r = lastRow To headerRow + 1 Step -1
        requestId = Trim$(CStr(ws.Cells(r, LOCAL_QUEUE_REQUEST_COL).Value))

        If Len(requestId) > 0 Then
            localState = UCase$(Trim$(CStr(ws.Cells(r, LOCAL_QUEUE_STATE_COL).Value)))
            localResultText = Trim$(CStr(ws.Cells(r, LOCAL_QUEUE_RESULT_COL).Value))

            isTerminalFromMaster = False

            If localState = "DONE" Or localState = "ERROR" Then
                If IsMasterFinalQueueResult(localResultText) Then
                    isTerminalFromMaster = True
                End If
            End If

            If Not isTerminalFromMaster Then
                anyActive = True

                If checkedThisPass < maxChecksThisPass Then
                    checkedThisPass = checkedThisPass + 1

                    Set item = PA_QueueGetRequestStatus(requestId)

                    If item Is Nothing Then
                        ws.Cells(r, LOCAL_QUEUE_STATE_COL).Value = ShortQueueStateText("Queued")
                        ws.Cells(r, LOCAL_QUEUE_RESULT_COL).Value = "No status returned from SharePoint yet."
                        FormatLocalQueueStateCell ws.Cells(r, LOCAL_QUEUE_STATE_COL), "Queued"

                    Else
                        statusText = Trim$(PA_DictText(item, "status"))
                        resultCode = Trim$(PA_DictText(item, "resultCode"))
                        resultMessage = Trim$(PA_DictText(item, "resultMessage"))

                        If Len(statusText) = 0 Then statusText = "Queued"

                        If StrComp(statusText, "Done", vbTextCompare) = 0 Or _
                           StrComp(statusText, "Error", vbTextCompare) = 0 Then

                            ws.Cells(r, LOCAL_QUEUE_STATE_COL).Value = ShortQueueStateText(statusText)
                            ws.Cells(r, LOCAL_QUEUE_RESULT_COL).Value = MasterFinalQueueResultText(resultMessage, statusText)
                            FormatLocalQueueStateCell ws.Cells(r, LOCAL_QUEUE_STATE_COL), statusText

                            UpdateAuditFromRequestItem item
                            UpdateImportedRowFromRequestItem item
                            HandleCompletedRequest requestId, statusText, resultCode, resultMessage

                        Else
                            If Len(resultMessage) = 0 Then
                                resultMessage = "Waiting for master queue result..."
                            End If

                            ws.Cells(r, LOCAL_QUEUE_STATE_COL).Value = ShortQueueStateText(statusText)
                            ws.Cells(r, LOCAL_QUEUE_RESULT_COL).Value = resultMessage
                            FormatLocalQueueStateCell ws.Cells(r, LOCAL_QUEUE_STATE_COL), statusText

                            UpdateAuditFromRequestItem item
                        End If
                    End If
                End If
            End If
        End If
    Next r

    ws.Columns(LOCAL_QUEUE_STATE_COL).ColumnWidth = 12

    If Not fullSweep Then
        If anyActive Then
            ScheduleStationPoll
        End If
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: GetImportedQueueStateFromMasterRow
' Scope: Private Function
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   GetImportedQueueStateFromMasterRow.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function GetImportedQueueStateFromMasterRow(ByVal ws As Worksheet, ByVal rowNum As Long) As String
    Dim barcodeCol As Long
    Dim orderCol As Long
    Dim itemCol As Long
    Dim qtyCol As Long
    Dim timeCol As Long
    Dim checkCol As Long
    Dim commentCol As Long
    Dim recentValueCell As Range
    Dim modeText As String
    Dim qtyVal As Long
    Dim checkText As String
    Dim timeVal As Variant

    modeText = ModeFromStageProfile(GetSelectedStageProfile())
    If Not GetModeBlockColumns(modeText, barcodeCol, orderCol, itemCol, qtyCol, timeCol, checkCol, commentCol, recentValueCell) Then Exit Function

    qtyVal = CLng(Val(ws.Cells(rowNum, qtyCol).Value))
    checkText = Trim$(CStr(ws.Cells(rowNum, checkCol).Value))
    timeVal = ws.Cells(rowNum, timeCol).Value

    If qtyVal > 0 Then
        GetImportedQueueStateFromMasterRow = "Done"
        Exit Function
    End If

    If Len(checkText) > 0 Then
        GetImportedQueueStateFromMasterRow = "Done"
        Exit Function
    End If

    If IsDate(timeVal) Then
        GetImportedQueueStateFromMasterRow = "Done"
        Exit Function
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: FindImportedRowForOrderItem
' Scope: Public Function
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   FindImportedRowForOrderItem.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function FindImportedRowForOrderItem(ByVal ord As Long, ByVal itm As Long) As Long
    Dim ws As Worksheet
    Dim headerRow As Long
    Dim lastRow As Long
    Dim r As Long

    Dim barcodeCol As Long
    Dim orderCol As Long
    Dim itemCol As Long
    Dim qtyCol As Long
    Dim timeCol As Long
    Dim checkCol As Long
    Dim commentCol As Long
    Dim recentValueCell As Range

    Set ws = StageViewSheet()
    If ws Is Nothing Then Exit Function

    headerRow = GetImportedMainHeaderRow(ws)
    If headerRow = 0 Then Exit Function

    lastRow = ws.Cells(ws.Rows.Count, 5).End(xlUp).Row

    If GetModeBlockColumns(ModeFromStageProfile(GetSelectedStageProfile()), _
                           barcodeCol, orderCol, itemCol, qtyCol, timeCol, checkCol, commentCol, recentValueCell) Then

        For r = headerRow + 1 To lastRow
            If Not ws.Rows(r).Hidden Then
                If CLng(Val(Replace$(CStr(ws.Cells(r, orderCol).Value), ",", vbNullString))) = ord Then
                    If CLng(Val(ws.Cells(r, itemCol).Value)) = itm Then
                        FindImportedRowForOrderItem = r
                        Exit Function
                    End If
                End If
            End If
        Next r
    End If

    'Fallback to the main delivery-list side.
    For r = headerRow + 1 To lastRow
        If Not ws.Rows(r).Hidden Then
            If CLng(Val(Replace$(CStr(ws.Cells(r, 5).Value), ",", vbNullString))) = ord Then
                If CLng(Val(ws.Cells(r, 6).Value)) = itm Then
                    FindImportedRowForOrderItem = r
                    Exit Function
                End If
            End If
        End If
    Next r
End Function

'------------------------------------------------------------------------------
' Procedure: HasImportedActiveQueueRequests
' Scope: Public Function
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   HasImportedActiveQueueRequests.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function HasImportedActiveQueueRequests() As Boolean
    Dim ws As Worksheet
    Dim headerRow As Long
    Dim lastRow As Long
    Dim r As Long
    Dim requestId As String
    Dim stateText As String
    Dim resultText As String

    Set ws = StageViewSheet()
    If ws Is Nothing Then Exit Function
    If Not IsImportedStageLoaded() Then Exit Function

    headerRow = GetImportedMainHeaderRow(ws)
    If headerRow = 0 Then Exit Function

    lastRow = ws.Cells(ws.Rows.Count, 5).End(xlUp).Row

    For r = headerRow + 1 To lastRow
        requestId = Trim$(CStr(ws.Cells(r, LOCAL_QUEUE_REQUEST_COL).Value))

        If Len(requestId) > 0 Then
            stateText = UCase$(Trim$(CStr(ws.Cells(r, LOCAL_QUEUE_STATE_COL).Value)))
            resultText = UCase$(Trim$(CStr(ws.Cells(r, LOCAL_QUEUE_RESULT_COL).Value)))

            If stateText = "DONE" Or stateText = "ERROR" Then
                If Left$(resultText, 14) = "[MASTER FINAL]" Or _
                   Left$(resultText, 15) = "[FINAL APPLIED:" Then
                    'This request is finished. Do not count it as active.
                Else
                    HasImportedActiveQueueRequests = True
                    Exit Function
                End If
            Else
                HasImportedActiveQueueRequests = True
                Exit Function
            End If
        End If
    Next r
End Function

'------------------------------------------------------------------------------
' Procedure: UpdateImportedRowFromRequestItem
' Scope: Public Sub
'
' What it does:
'   Applies a completed queue item result back to the imported row, including
'   final quantity/status adjustments and result text.
'
' Why it exists:
'   The local snapshot should eventually agree with the master’s final
'   decision, even if the local prevalidation result changed after master
'   processing.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub UpdateImportedRowFromRequestItem(ByVal item As Object)
    Dim requestId As String
    Dim reqType As String
    Dim barcodeText As String
    Dim ord As Long
    Dim itm As Long
    Dim qty As Long
    Dim statusText As String
    Dim resultCode As String
    Dim resultMessage As String
    Dim compactMessage As String
    Dim requestComment As String
    Dim ws As Worksheet
    Dim dataRow As Long

    Dim barcodeCol As Long
    Dim orderCol As Long
    Dim itemCol As Long
    Dim qtyCol As Long
    Dim timeCol As Long
    Dim checkCol As Long
    Dim commentCol As Long
    Dim recentValueCell As Range

    Dim modeText As String
    Dim processedAt As Date

    If item Is Nothing Then Exit Sub

    Set ws = StageViewSheet()
    If ws Is Nothing Then Exit Sub

    modeText = ModeFromStageProfile(GetSelectedStageProfile())

    requestId = Trim$(PA_DictText(item, "requestId"))
    reqType = UCase$(Trim$(PA_DictText(item, "requestType")))
    barcodeText = Trim$(PA_DictText(item, "barcode"))
    ord = CLng(Val(PA_DictText(item, "orderNumber")))
    itm = CLng(Val(PA_DictText(item, "itemNumber")))
    qty = CLng(Val(PA_DictText(item, "quantity")))
    statusText = Trim$(PA_DictText(item, "status"))
    resultCode = Trim$(PA_DictText(item, "resultCode"))
    resultMessage = Trim$(PA_DictText(item, "resultMessage"))
    compactMessage = CompactQueueResultMessage(resultMessage)
    requestComment = Trim$(PA_DictText(item, "requestComment"))
    processedAt = PA_ParseIsoDate(PA_DictText(item, "processedAt"))

    If reqType = "BARCODE" Then
        If ord = 0 Then ord = DecodeBarcodeOrder(barcodeText)
        If itm = 0 Then itm = DecodeBarcodeItem(barcodeText)
        If qty = 0 Then qty = 1
    End If

    If qty <= 0 Then qty = 1

    dataRow = FindImportedDataRow(ws, ord, itm)
    If dataRow = 0 Then Exit Sub

    If Not GetModeBlockColumns(modeText, barcodeCol, orderCol, itemCol, qtyCol, timeCol, checkCol, commentCol, recentValueCell) Then Exit Sub

    If StrComp(statusText, "Done", vbTextCompare) = 0 Or _
       StrComp(statusText, "Error", vbTextCompare) = 0 Then

        If ImportedFinalRequestAlreadyApplied(ws, dataRow, requestId) Then
            Exit Sub
        End If
    End If

    If StrComp(statusText, "Done", vbTextCompare) = 0 Then
        If processedAt > 0 Then
            ws.Cells(dataRow, timeCol).Value = processedAt
        End If

        Select Case reqType
            Case "COMMENT"
                ws.Cells(dataRow, COMMENT_BASELINE_COL).Value = CStr(ws.Cells(dataRow, commentCol).Value)

            Case Else
                ws.Cells(dataRow, checkCol).Value = BuildFinalCheckTextForCompletedRequest(reqType, resultCode, compactMessage)

                FormatLocalStatusCellByValue ws.Cells(dataRow, checkCol), ws.Cells(dataRow, checkCol).Value
                UpdateLocalDeliveryProcessStateForRow ws, dataRow

                UpdateMostRecentScanHeader ws, modeText, barcodeText, ord, itm, qty, ws.Cells(dataRow, timeCol).Value, ws.Cells(dataRow, checkCol).Value
                RefreshImportedTopSummaryPanels ws
                RefreshLocalRowVisualState ws, dataRow
                AutoFitLocalCommentPresentation ws, dataRow
                HighlightImportedRow ws, dataRow, modeText
        End Select

        MarkImportedFinalRequestApplied ws, dataRow, requestId, statusText, compactMessage

    ElseIf StrComp(statusText, "Error", vbTextCompare) = 0 Then
        DecreaseImportedQuantityForErroredRequest item

        ws.Cells(dataRow, checkCol).Value = "MASTER ERROR"

        If Len(compactMessage) > 0 Then
            AppendTextToCellOnce ws.Cells(dataRow, commentCol), compactMessage
        End If

        FormatLocalStatusCellByValue ws.Cells(dataRow, checkCol), ws.Cells(dataRow, checkCol).Value
        UpdateLocalDeliveryProcessStateForRow ws, dataRow
        RefreshImportedTopSummaryPanels ws
        RefreshLocalRowVisualState ws, dataRow
        AutoFitLocalCommentPresentation ws, dataRow
        HighlightImportedRow ws, dataRow, modeText

        MarkImportedFinalRequestApplied ws, dataRow, requestId, statusText, compactMessage
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: BuildFinalCheckTextForCompletedRequest
' Scope: Private Function
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   BuildFinalCheckTextForCompletedRequest.
'
' Why it exists:
'   Scans move through local buffer, SharePoint ScanQueue, master processing,
'   and final intake confirmation; this state must stay traceable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function BuildFinalCheckTextForCompletedRequest(ByVal reqType As String, _
                                                        ByVal resultCode As String, _
                                                        ByVal resultMessage As String) As String
    Dim msgUpper As String
    Dim codeUpper As String

    reqType = UCase$(Trim$(CStr(reqType)))
    resultCode = Trim$(CStr(resultCode))
    resultMessage = Trim$(CStr(resultMessage))

    msgUpper = UCase$(resultMessage)
    codeUpper = UCase$(resultCode)

    'Keep partial text because it is useful in the Check column.
    If Left$(msgUpper, 7) = "PARTIAL" Then
        BuildFinalCheckTextForCompletedRequest = resultMessage
        Exit Function
    End If

    'Successful manual scans should show OK, not "Manual scan complete".
    If reqType = "MANUAL" Then
        If codeUpper = "OK" Or codeUpper = "DONE" Or Len(codeUpper) = 0 Then
            BuildFinalCheckTextForCompletedRequest = "OK"
            Exit Function
        End If
    End If

    'Successful barcode/staging/receive scans should also stay compact.
    If codeUpper = "OK" Or codeUpper = "DONE" Then
        BuildFinalCheckTextForCompletedRequest = "OK"
        Exit Function
    End If

    If Len(resultMessage) > 0 Then
        BuildFinalCheckTextForCompletedRequest = resultMessage
    ElseIf Len(resultCode) > 0 Then
        BuildFinalCheckTextForCompletedRequest = resultCode
    Else
        BuildFinalCheckTextForCompletedRequest = "OK"
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: DecreaseImportedQuantityForErroredRequest
' Scope: Private Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   DecreaseImportedQuantityForErroredRequest.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub DecreaseImportedQuantityForErroredRequest(ByVal item As Object)
    Dim ws As Worksheet
    Dim reqType As String
    Dim barcodeText As String
    Dim ord As Long
    Dim itm As Long
    Dim dataRow As Long
    Dim currentQty As Long
    Dim newQty As Long

    Dim barcodeCol As Long
    Dim orderCol As Long
    Dim itemCol As Long
    Dim qtyCol As Long
    Dim timeCol As Long
    Dim checkCol As Long
    Dim commentCol As Long
    Dim recentValueCell As Range
    Dim modeText As String

    Set ws = StageViewSheet()
    If ws Is Nothing Then Exit Sub

    modeText = ModeFromStageProfile(GetSelectedStageProfile())

    reqType = UCase$(Trim$(PA_DictText(item, "requestType")))
    barcodeText = Trim$(PA_DictText(item, "barcode"))

    ord = CLng(Val(PA_DictText(item, "orderNumber")))
    itm = CLng(Val(PA_DictText(item, "itemNumber")))

    If reqType = "BARCODE" Then
        If ord = 0 Then ord = DecodeBarcodeOrder(barcodeText)
        If itm = 0 Then itm = DecodeBarcodeItem(barcodeText)
    End If

    dataRow = FindImportedDataRow(ws, ord, itm)
    If dataRow = 0 Then Exit Sub

    If Not GetModeBlockColumns(modeText, barcodeCol, orderCol, itemCol, qtyCol, timeCol, checkCol, commentCol, recentValueCell) Then Exit Sub

    currentQty = CLng(Val(ws.Cells(dataRow, qtyCol).Value))
    newQty = currentQty - 1

    If newQty < 0 Then newQty = 0

    ws.Cells(dataRow, qtyCol).Value = newQty
End Sub

'------------------------------------------------------------------------------
' Procedure: WriteSnapshotTopRowsToStageSheet
' Scope: Private Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   WriteSnapshotTopRowsToStageSheet.
'
' Why it exists:
'   The intake workbook reconstructs a working Excel sheet from published
'   snapshot JSON, so data and formatting must be applied in a predictable
'   order.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub WriteSnapshotTopRowsToStageSheet(ByVal ws As Worksheet, ByVal snapshotJson As String, ByVal headerRow As Long)
    Dim topRowsText As String
    Dim rowArrays As Collection
    Dim rowArray As Variant
    Dim r As Long

    If ws Is Nothing Then Exit Sub
    If Len(snapshotJson) = 0 Then Exit Sub
    If headerRow <= 1 Then Exit Sub

    topRowsText = PA_JsonValueForKey(snapshotJson, "topRows")
    If Len(Trim$(topRowsText)) = 0 Then Exit Sub

    Set rowArrays = SnapshotImportSplitTopLevelArrays(topRowsText)

    r = 1

    For Each rowArray In rowArrays
        If r >= headerRow Then Exit For
        WriteSnapshotJsonArrayToRow ws, r, 1, 48, CStr(rowArray)
        r = r + 1
    Next rowArray
End Sub

'------------------------------------------------------------------------------
' Procedure: SnapshotImportSplitTopLevelArrays
' Scope: Private Function
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   SnapshotImportSplitTopLevelArrays.
'
' Why it exists:
'   The intake workbook reconstructs a working Excel sheet from published
'   snapshot JSON, so data and formatting must be applied in a predictable
'   order.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function SnapshotImportSplitTopLevelArrays(ByVal arrayText As String) As Collection
    Dim out As New Collection
    Dim s As String
    Dim i As Long
    Dim c As String
    Dim startPos As Long
    Dim depth As Long
    Dim inString As Boolean
    Dim escaped As Boolean

    s = Trim$(CStr(arrayText))

    If Len(s) = 0 Then
        Set SnapshotImportSplitTopLevelArrays = out
        Exit Function
    End If

    If Left$(s, 1) = "[" And Right$(s, 1) = "]" Then
        s = Mid$(s, 2, Len(s) - 2)
    End If

    s = Trim$(s)
    If Len(s) = 0 Then
        Set SnapshotImportSplitTopLevelArrays = out
        Exit Function
    End If

    startPos = 0
    depth = 0
    inString = False
    escaped = False

    For i = 1 To Len(s)
        c = Mid$(s, i, 1)

        If inString Then
            If escaped Then
                escaped = False
            ElseIf c = "\" Then
                escaped = True
            ElseIf c = """" Then
                inString = False
            End If
        Else
            Select Case c
                Case """"
                    inString = True

                Case "["
                    If depth = 0 Then startPos = i
                    depth = depth + 1

                Case "]"
                    depth = depth - 1

                    If depth = 0 And startPos > 0 Then
                        out.Add Mid$(s, startPos, i - startPos + 1)
                        startPos = 0
                    End If
            End Select
        End If
    Next i

    Set SnapshotImportSplitTopLevelArrays = out
End Function

'------------------------------------------------------------------------------
' Procedure: ApplySnapshotPublishedFormat
' Scope: Private Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   ApplySnapshotPublishedFormat.
'
' Why it exists:
'   The intake workbook reconstructs a working Excel sheet from published
'   snapshot JSON, so data and formatting must be applied in a predictable
'   order.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ApplySnapshotPublishedFormat(ByVal ws As Worksheet, ByVal snapshotJson As String, ByVal headerRow As Long)
    Dim formatJson As String

    If ws Is Nothing Then Exit Sub
    If Len(snapshotJson) = 0 Then Exit Sub

    formatJson = PA_JsonValueForKey(snapshotJson, "format")
    If Len(Trim$(formatJson)) = 0 Then Exit Sub

    On Error Resume Next

    ApplySnapshotColumnFormats ws, PA_JsonValueForKey(formatJson, "columns")
    ApplySnapshotRowFormats ws, PA_JsonValueForKey(formatJson, "rows")

    'Important: values are already written before this.
    'Unmerge then re-merge exactly as master published.
    ws.Range("A1:AV" & Application.Max(headerRow + 1, ws.Cells(ws.Rows.Count, 5).End(xlUp).Row)).UnMerge

    ApplySnapshotMerges ws, PA_JsonValueForKey(formatJson, "merges")
    ApplySnapshotCellFormats ws, PA_JsonValueForKey(formatJson, "cells")

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplySnapshotColumnFormats
' Scope: Private Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   ApplySnapshotColumnFormats.
'
' Why it exists:
'   The intake workbook reconstructs a working Excel sheet from published
'   snapshot JSON, so data and formatting must be applied in a predictable
'   order.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ApplySnapshotColumnFormats(ByVal ws As Worksheet, ByVal columnsJson As String)
    Dim objects As Collection
    Dim obj As Variant
    Dim colNum As Long
    Dim colWidth As Double
    Dim hiddenText As String

    Set objects = PA_JsonSplitObjects(columnsJson)

    For Each obj In objects
        colNum = CLng(Val(PA_JsonGetNumberValue(CStr(obj), "c")))
        colWidth = CDbl(Val(PA_JsonGetNumberValue(CStr(obj), "w")))
        hiddenText = UCase$(PA_JsonValueForKey(CStr(obj), "hidden"))

        If colNum > 0 Then
            If colWidth > 0 Then ws.Columns(colNum).ColumnWidth = colWidth
            ws.Columns(colNum).Hidden = (hiddenText = "TRUE")
        End If
    Next obj
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplySnapshotRowFormats
' Scope: Private Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   ApplySnapshotRowFormats.
'
' Why it exists:
'   The intake workbook reconstructs a working Excel sheet from published
'   snapshot JSON, so data and formatting must be applied in a predictable
'   order.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ApplySnapshotRowFormats(ByVal ws As Worksheet, ByVal rowsJson As String)
    Dim objects As Collection
    Dim obj As Variant
    Dim rowNum As Long
    Dim rowHeight As Double
    Dim hiddenText As String

    Set objects = PA_JsonSplitObjects(rowsJson)

    For Each obj In objects
        rowNum = CLng(Val(PA_JsonGetNumberValue(CStr(obj), "r")))
        rowHeight = CDbl(Val(PA_JsonGetNumberValue(CStr(obj), "h")))
        hiddenText = UCase$(PA_JsonValueForKey(CStr(obj), "hidden"))

        If rowNum > 0 Then
            If rowHeight > 0 Then ws.Rows(rowNum).rowHeight = rowHeight
            ws.Rows(rowNum).Hidden = (hiddenText = "TRUE")
        End If
    Next obj
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplySnapshotMerges
' Scope: Private Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   ApplySnapshotMerges.
'
' Why it exists:
'   The intake workbook reconstructs a working Excel sheet from published
'   snapshot JSON, so data and formatting must be applied in a predictable
'   order.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ApplySnapshotMerges(ByVal ws As Worksheet, ByVal mergesJson As String)
    Dim objects As Collection
    Dim obj As Variant
    Dim addr As String

    Set objects = PA_JsonSplitObjects(mergesJson)

    For Each obj In objects
        addr = PA_JsonGetStringValue(CStr(obj), "addr")

        If Len(addr) > 0 Then
            On Error Resume Next
            ws.Range(addr).Merge
            On Error GoTo 0
        End If
    Next obj
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplySnapshotCellFormats
' Scope: Private Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   ApplySnapshotCellFormats.
'
' Why it exists:
'   The intake workbook reconstructs a working Excel sheet from published
'   snapshot JSON, so data and formatting must be applied in a predictable
'   order.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ApplySnapshotCellFormats(ByVal ws As Worksheet, ByVal cellsJson As String)
    Dim objects As Collection
    Dim obj As Variant
    Dim addr As String
    Dim cell As Range

    Set objects = PA_JsonSplitObjects(cellsJson)

    For Each obj In objects
        addr = PA_JsonGetStringValue(CStr(obj), "a")

        If Len(addr) > 0 Then
            On Error Resume Next
            Set cell = ws.Range(addr)
            On Error GoTo 0

            If Not cell Is Nothing Then
                ApplySnapshotOneCellFormat cell, CStr(obj)
            End If
        End If
    Next obj
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplySnapshotOneCellFormat
' Scope: Private Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   ApplySnapshotOneCellFormat.
'
' Why it exists:
'   The intake workbook reconstructs a working Excel sheet from published
'   snapshot JSON, so data and formatting must be applied in a predictable
'   order.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ApplySnapshotOneCellFormat(ByVal cell As Range, ByVal cellJson As String)
    Dim borderJson As String

    If cell Is Nothing Then Exit Sub

    On Error Resume Next

    cell.NumberFormat = PA_JsonGetStringValue(cellJson, "nf")
    cell.Font.Name = PA_JsonGetStringValue(cellJson, "font")
    cell.Font.Size = CDbl(Val(PA_JsonGetNumberValue(cellJson, "fs")))
    cell.Font.Bold = SnapshotJsonBool(PA_JsonValueForKey(cellJson, "bold"))
    cell.Font.Italic = SnapshotJsonBool(PA_JsonValueForKey(cellJson, "italic"))
    cell.Font.Underline = CLng(Val(PA_JsonGetNumberValue(cellJson, "underline")))

    ApplySnapshotColorValue cell.Font, "Color", PA_JsonValueForKey(cellJson, "fontColor")

    cell.Interior.Pattern = CLng(Val(PA_JsonGetNumberValue(cellJson, "fillPattern")))

    If cell.Interior.Pattern <> xlNone Then
        cell.Interior.Color = CLng(Val(PA_JsonGetNumberValue(cellJson, "fillColor")))
    End If

    cell.HorizontalAlignment = CLng(Val(PA_JsonGetNumberValue(cellJson, "hAlign")))
    cell.VerticalAlignment = CLng(Val(PA_JsonGetNumberValue(cellJson, "vAlign")))
    cell.WrapText = SnapshotJsonBool(PA_JsonValueForKey(cellJson, "wrap"))

    borderJson = PA_JsonValueForKey(cellJson, "border")
    If Len(borderJson) > 0 Then
        ApplySnapshotBorders cell, borderJson
    End If

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplyImportedSummaryPanelFallbackStyle
' Scope: Private Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   ApplyImportedSummaryPanelFallbackStyle.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ApplyImportedSummaryPanelFallbackStyle(ByVal ws As Worksheet)
    If ws Is Nothing Then Exit Sub

    On Error Resume Next

    'Summary value rows.
    ApplySummaryPanelCellStyle ws.Range("O2:W2")
    ApplySummaryPanelCellStyle ws.Range("X2:AG2")
    ApplySummaryPanelCellStyle ws.Range("AO2:AV2")

    'Panel title rows.
    ApplySummaryPanelTitleStyle ws.Range("O3:W3")
    ApplySummaryPanelTitleStyle ws.Range("X3:AG3")
    ApplySummaryPanelTitleStyle ws.Range("AO3:AV3")

    'Most recent scan row must stay unmerged.
    EnsureMostRecentScanRowsUsable ws
    ApplyMostRecentScanRowFallbackStyle ws.Range("O4:W4")
    ApplyMostRecentScanRowFallbackStyle ws.Range("X4:AG4")
    ApplyMostRecentScanRowFallbackStyle ws.Range("AO4:AV4")

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplyMostRecentScanRowFallbackStyle
' Scope: Private Sub
'
' What it does:
'   Cleans, validates, decodes, applies, focuses, or displays scan/barcode
'   data for ApplyMostRecentScanRowFallbackStyle.
'
' Why it exists:
'   The scanner acts like a keyboard, so the workbook must turn entered text
'   into safe order/item updates without duplicate submissions.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ApplyMostRecentScanRowFallbackStyle(ByVal rng As Range)
    If rng Is Nothing Then Exit Sub

    With rng
        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
        .WrapText = False
        .Font.Name = "Calibri"
        .Font.Size = 10
        .Font.Bold = True
        .Font.Color = RGB(0, 0, 0)
        .Interior.Color = RGB(242, 242, 242)

        With .Borders
            .lineStyle = xlContinuous
            .Weight = xlThin
            .Color = RGB(191, 191, 191)
        End With
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplySummaryPanelCellStyle
' Scope: Private Sub
'
' What it does:
'   Builds, formats, or updates the intake operator panel/buttons for
'   ApplySummaryPanelCellStyle.
'
' Why it exists:
'   The panel is the operator-facing part of the workbook; consistent buttons
'   and status cells reduce scanning mistakes.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ApplySummaryPanelCellStyle(ByVal rng As Range)
    If rng Is Nothing Then Exit Sub

    With rng
        If .MergeCells = False Then .Merge

        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
        .WrapText = True
        .Font.Name = "Calibri"
        .Font.Size = 12
        .Font.Bold = True
        .Font.Color = RGB(0, 0, 0)
        .Interior.Color = RGB(221, 235, 247)

        With .Borders
            .lineStyle = xlContinuous
            .Weight = xlThin
            .Color = RGB(91, 155, 213)
        End With
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplySummaryPanelTitleStyle
' Scope: Private Sub
'
' What it does:
'   Builds, formats, or updates the intake operator panel/buttons for
'   ApplySummaryPanelTitleStyle.
'
' Why it exists:
'   The panel is the operator-facing part of the workbook; consistent buttons
'   and status cells reduce scanning mistakes.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ApplySummaryPanelTitleStyle(ByVal rng As Range)
    If rng Is Nothing Then Exit Sub

    With rng
        If .MergeCells = False Then .Merge

        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
        .WrapText = True
        .Font.Name = "Calibri"
        .Font.Size = 11
        .Font.Bold = True
        .Font.Color = RGB(255, 255, 255)
        .Interior.Color = RGB(31, 78, 121)

        With .Borders
            .lineStyle = xlContinuous
            .Weight = xlThin
            .Color = RGB(31, 78, 121)
        End With
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplySummaryPanelLabelStyle
' Scope: Private Sub
'
' What it does:
'   Builds, formats, or updates the intake operator panel/buttons for
'   ApplySummaryPanelLabelStyle.
'
' Why it exists:
'   The panel is the operator-facing part of the workbook; consistent buttons
'   and status cells reduce scanning mistakes.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ApplySummaryPanelLabelStyle(ByVal rng As Range)
    If rng Is Nothing Then Exit Sub

    With rng
        If .MergeCells = False Then .Merge

        .HorizontalAlignment = xlLeft
        .VerticalAlignment = xlCenter
        .WrapText = True
        .Font.Name = "Calibri"
        .Font.Size = 10
        .Font.Bold = True
        .Font.Color = RGB(0, 0, 0)
        .Interior.Color = RGB(242, 242, 242)

        With .Borders
            .lineStyle = xlContinuous
            .Weight = xlThin
            .Color = RGB(191, 191, 191)
        End With
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplySnapshotBorders
' Scope: Private Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   ApplySnapshotBorders.
'
' Why it exists:
'   The intake workbook reconstructs a working Excel sheet from published
'   snapshot JSON, so data and formatting must be applied in a predictable
'   order.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ApplySnapshotBorders(ByVal cell As Range, ByVal borderJson As String)
    If cell Is Nothing Then Exit Sub

    ApplySnapshotOneBorder cell.Borders(xlEdgeLeft), PA_JsonValueForKey(borderJson, "l")
    ApplySnapshotOneBorder cell.Borders(xlEdgeTop), PA_JsonValueForKey(borderJson, "t")
    ApplySnapshotOneBorder cell.Borders(xlEdgeRight), PA_JsonValueForKey(borderJson, "r")
    ApplySnapshotOneBorder cell.Borders(xlEdgeBottom), PA_JsonValueForKey(borderJson, "b")
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplySnapshotOneBorder
' Scope: Private Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   ApplySnapshotOneBorder.
'
' Why it exists:
'   The intake workbook reconstructs a working Excel sheet from published
'   snapshot JSON, so data and formatting must be applied in a predictable
'   order.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ApplySnapshotOneBorder(ByVal b As Border, ByVal borderSideJson As String)
    Dim lineStyle As Long

    If Len(Trim$(borderSideJson)) = 0 Then Exit Sub

    On Error Resume Next

    lineStyle = CLng(Val(PA_JsonGetNumberValue(borderSideJson, "ls")))
    b.lineStyle = lineStyle

    If lineStyle <> xlNone Then
        b.Weight = CLng(Val(PA_JsonGetNumberValue(borderSideJson, "w")))
        b.Color = CLng(Val(PA_JsonGetNumberValue(borderSideJson, "c")))
    End If

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: SnapshotJsonBool
' Scope: Private Function
'
' What it does:
'   Parses, decodes, builds, or extracts JSON text used by the Power Automate
'   bridge (SnapshotJsonBool).
'
' Why it exists:
'   The intake workbook reconstructs a working Excel sheet from published
'   snapshot JSON, so data and formatting must be applied in a predictable
'   order.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function SnapshotJsonBool(ByVal rawValue As String) As Boolean
    rawValue = UCase$(Trim$(CStr(rawValue)))

    SnapshotJsonBool = _
        (rawValue = "TRUE" Or rawValue = "1" Or rawValue = "YES")
End Function

'------------------------------------------------------------------------------
' Procedure: ApplySnapshotColorValue
' Scope: Private Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   ApplySnapshotColorValue.
'
' Why it exists:
'   The intake workbook reconstructs a working Excel sheet from published
'   snapshot JSON, so data and formatting must be applied in a predictable
'   order.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ApplySnapshotColorValue(ByVal targetObj As Object, ByVal propertyName As String, ByVal rawValue As String)
    rawValue = Trim$(CStr(rawValue))

    If Len(rawValue) = 0 Then Exit Sub
    If LCase$(rawValue) = "null" Then Exit Sub

    On Error Resume Next
    CallByName targetObj, propertyName, VbLet, CLng(Val(rawValue))
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplyIntakeOnlySnapshotFormatting
' Scope: Private Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   ApplyIntakeOnlySnapshotFormatting.
'
' Why it exists:
'   The intake workbook reconstructs a working Excel sheet from published
'   snapshot JSON, so data and formatting must be applied in a predictable
'   order.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ApplyIntakeOnlySnapshotFormatting(ByVal ws As Worksheet, ByVal headerRow As Long, ByVal modeText As String)
    If ws Is Nothing Then Exit Sub
    If headerRow <= 0 Then headerRow = 5

    On Error Resume Next

    'Keep queue/status display compact.
    ws.Columns(LOCAL_QUEUE_STATE_COL).ColumnWidth = 12

    'Hidden helper columns stay hidden.
    ws.Columns(LOCAL_QUEUE_REQUEST_COL).Hidden = True
    ws.Columns(LOCAL_QUEUE_RESULT_COL).Hidden = True

    'Keep item columns as 000.
    ws.Columns("F").NumberFormat = "000"
    ws.Columns("R").NumberFormat = "000"
    ws.Columns("AA").NumberFormat = "000"
    ws.Columns("AR").NumberFormat = "000"

    'Keep scan time formats.
    ws.Columns("T").NumberFormat = "m/d/yyyy h:mm AM/PM"
    ws.Columns("AC").NumberFormat = "m/d/yyyy h:mm AM/PM"
    ws.Columns("AT").NumberFormat = "m/d/yyyy h:mm AM/PM"

    'Keep comments readable.
    ws.Columns("W").WrapText = True
    ws.Columns("AF").WrapText = True
    ws.Columns("AV").WrapText = True

    'Keep unused inbound helper column hidden.
    ws.Columns("AE").Hidden = True
    ws.Columns("AE").ColumnWidth = 0.1

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplyStageRowVisibilityFilter
' Scope: Private Sub
'
' What it does:
'   Hides or shows rows on the imported snapshot based on the selected stage
'   profile such as Indian Trail, Greenville, or Customer Pickup.
'
' Why it exists:
'   Inbound stages should show only the rows that physically belong to that
'   station so operators are not distracted by unrelated work.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ApplyStageRowVisibilityFilter(ByVal ws As Worksheet, ByVal stageProfile As String)
    Dim headerRow As Long
    Dim lastRow As Long
    Dim r As Long

    If ws Is Nothing Then Exit Sub

    headerRow = GetImportedMainHeaderRow(ws)
    If headerRow = 0 Then Exit Sub

    lastRow = ws.Cells(ws.Rows.Count, 5).End(xlUp).Row
    If lastRow <= headerRow Then Exit Sub

    On Error Resume Next
    ws.Rows(CStr(headerRow + 1) & ":" & CStr(lastRow)).Hidden = False
    On Error GoTo 0

    If Not StageProfileNeedsDeliveryListFilter(stageProfile) Then Exit Sub

    For r = headerRow + 1 To lastRow
        If StageFilterRowIsSectionHeader(ws, r) Then
            ws.Rows(r).Hidden = Not StageFilterSectionHasVisibleLines(ws, r, lastRow, stageProfile)

        ElseIf SummaryRowIsDeliveryLine(ws, r) Then
            ws.Rows(r).Hidden = Not SummaryRowShouldCountForStage(ws, r, stageProfile)

        Else
            ws.Rows(r).Hidden = True
        End If
    Next r
End Sub

'------------------------------------------------------------------------------
' Procedure: StageProfileNeedsDeliveryListFilter
' Scope: Private Function
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   StageProfileNeedsDeliveryListFilter.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function StageProfileNeedsDeliveryListFilter(ByVal stageProfile As String) As Boolean
    Select Case UCase$(Trim$(stageProfile))
        Case "CUSTOMER PICKUP", _
             "INBOUND - GREENVILLE", _
             "INBOUND - INDIAN TRAIL"

            StageProfileNeedsDeliveryListFilter = True
    End Select
End Function

'------------------------------------------------------------------------------
' Procedure: StageFilterRowIsSectionHeader
' Scope: Private Function
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   StageFilterRowIsSectionHeader.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function StageFilterRowIsSectionHeader(ByVal ws As Worksheet, ByVal rowNum As Long) As Boolean
    Dim leftText As String

    If ws Is Nothing Then Exit Function
    If rowNum <= 0 Then Exit Function

    If SummaryRowIsDeliveryLine(ws, rowNum) Then Exit Function

    leftText = Trim$(CStr(ws.Cells(rowNum, 1).Value))

    StageFilterRowIsSectionHeader = (Len(leftText) > 0)
End Function

'------------------------------------------------------------------------------
' Procedure: StageFilterSectionHasVisibleLines
' Scope: Private Function
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   StageFilterSectionHasVisibleLines.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function StageFilterSectionHasVisibleLines(ByVal ws As Worksheet, _
                                                   ByVal sectionRow As Long, _
                                                   ByVal lastRow As Long, _
                                                   ByVal stageProfile As String) As Boolean
    Dim r As Long

    If ws Is Nothing Then Exit Function
    If sectionRow <= 0 Then Exit Function

    For r = sectionRow + 1 To lastRow
        If StageFilterRowIsSectionHeader(ws, r) Then
            Exit Function
        End If

        If SummaryRowIsDeliveryLine(ws, r) Then
            If SummaryRowShouldCountForStage(ws, r, stageProfile) Then
                StageFilterSectionHasVisibleLines = True
                Exit Function
            End If
        End If
    Next r
End Function

'------------------------------------------------------------------------------
' Procedure: ActiveCommentColumnHasVisibleComments
' Scope: Private Function
'
' What it does:
'   Finds, compares, syncs, appends, or formats local comment text for
'   ActiveCommentColumnHasVisibleComments.
'
' Why it exists:
'   Comments added at the intake station need to be preserved and sent back to
'   the master before refresh/settings changes.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function ActiveCommentColumnHasVisibleComments(ByVal ws As Worksheet, ByVal commentCol As Long) As Boolean
    Dim headerRow As Long
    Dim lastRow As Long
    Dim r As Long

    If ws Is Nothing Then Exit Function
    If commentCol <= 0 Then Exit Function

    headerRow = GetImportedMainHeaderRow(ws)
    If headerRow = 0 Then Exit Function

    lastRow = ws.Cells(ws.Rows.Count, 5).End(xlUp).Row
    If lastRow <= headerRow Then Exit Function

    For r = headerRow + 1 To lastRow
        If Not ws.Rows(r).Hidden Then
            If Len(Trim$(CStr(ws.Cells(r, commentCol).Value))) > 0 Then
                ActiveCommentColumnHasVisibleComments = True
                Exit Function
            End If
        End If
    Next r
End Function

'------------------------------------------------------------------------------
' Procedure: ApplyScanningSideAlignmentAndNumberFormats
' Scope: Private Sub
'
' What it does:
'   Cleans, validates, decodes, applies, focuses, or displays scan/barcode
'   data for ApplyScanningSideAlignmentAndNumberFormats.
'
' Why it exists:
'   The intake workbook reconstructs a working Excel sheet from published
'   snapshot JSON, so data and formatting must be applied in a predictable
'   order.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub ApplyScanningSideAlignmentAndNumberFormats(ByVal ws As Worksheet)
    Dim scanRng As Range
    Dim wasProtected As Boolean

    If ws Is Nothing Then Exit Sub

    On Error Resume Next

    wasProtected = (ws.ProtectContents Or ws.ProtectDrawingObjects Or ws.ProtectScenarios)
    If wasProtected Then ws.Unprotect

    'Only scanning-side panels.
    'Do not touch A:N because that is the delivery-list side.
    Set scanRng = Union( _
        ws.Range("O:W"), _
        ws.Range("X:AG"), _
        ws.Range("AO:AV") _
    )

    With scanRng
        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
    End With

    'Item number columns on the scanning side.
    'Outbound item = R
    'Inbound item = AA
    'Staging item = AR
    '
    'This removes the 001 / 002 display and shows 1 / 2 instead.
    ws.Columns("R").NumberFormat = "0"
    ws.Columns("AA").NumberFormat = "0"
    ws.Columns("AR").NumberFormat = "0"

    'Optional but helpful: keep scan-side order/qty columns as normal numbers too.
    ws.Columns("Q").NumberFormat = "0"
    ws.Columns("Z").NumberFormat = "0"
    ws.Columns("AQ").NumberFormat = "0"

    ws.Columns("S").NumberFormat = "0"
    ws.Columns("AB").NumberFormat = "0"
    ws.Columns("AS").NumberFormat = "0"

    'Keep comments one-line.
    ws.Columns("W").WrapText = False
    ws.Columns("AF").WrapText = False
    ws.Columns("AV").WrapText = False

    If wasProtected Then ProtectImportedStageForScanning ws

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: EnsureStageQueueRefreshButton
' Scope: Public Sub
'
' What it does:
'   Handles part of the imported stage/snapshot workflow for
'   EnsureStageQueueRefreshButton.
'
' Why it exists:
'   Intake stations scan from a local snapshot of the master data, so snapshot
'   state, formatting, and row matching must stay reliable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub EnsureStageQueueRefreshButton(Optional ByVal ws As Worksheet = Nothing)
    Dim workWs As Worksheet
    Dim targetCell As Range
    Dim shp As Shape
    Dim btnName As String
    Dim macroName As String
    Dim wasProtected As Boolean

    btnName = "btnStageQueueRefresh"
    macroName = "'" & ThisWorkbook.Name & "'!RefreshQueueStatusNow"

    If ws Is Nothing Then
        Set workWs = StageViewSheet()
    Else
        Set workWs = ws
    End If

    If workWs Is Nothing Then Exit Sub

    Set targetCell = workWs.Range("N4")

    On Error Resume Next

    wasProtected = (workWs.ProtectContents Or workWs.ProtectDrawingObjects Or workWs.ProtectScenarios)
    If wasProtected Then workWs.Unprotect

    workWs.Shapes(btnName).Delete

    Set shp = workWs.Shapes.AddShape( _
        Type:=msoShapeRoundedRectangle, _
        Left:=targetCell.Left + 2, _
        Top:=targetCell.Top + 2, _
        Width:=targetCell.Width - 4, _
        Height:=targetCell.Height - 4)

    With shp
        .Name = btnName
        .OnAction = macroName
        .Placement = xlMoveAndSize
        .Locked = False

        .Fill.ForeColor.RGB = RGB(47, 75, 117)
        .Line.ForeColor.RGB = RGB(31, 54, 88)

        With .TextFrame2
            .TextRange.Text = "Refresh"
            .VerticalAnchor = msoAnchorMiddle
            .TextRange.ParagraphFormat.Alignment = msoAlignCenter
            .TextRange.Font.Size = 9
            .TextRange.Font.Bold = msoTrue
            .TextRange.Font.Fill.ForeColor.RGB = RGB(255, 255, 255)
        End With
    End With

    targetCell.Value = vbNullString

    If wasProtected Then ProtectImportedStageForScanning workWs

    On Error GoTo 0
End Sub

Public Sub EnsureStageCommentSaveButton(Optional ByVal ws As Worksheet = Nothing)
    Dim workWs As Worksheet
    Dim targetCell As Range
    Dim shp As Shape
    Dim macroName As String
    Dim wasProtected As Boolean

    Dim barcodeCol As Long
    Dim orderCol As Long
    Dim itemCol As Long
    Dim qtyCol As Long
    Dim timeCol As Long
    Dim checkCol As Long
    Dim commentCol As Long
    Dim recentValueCell As Range
    Dim modeText As String

    macroName = "'" & ThisWorkbook.Name & "'!SaveStageCommentsToMasterFromButton"

    If ws Is Nothing Then
        Set workWs = StageViewSheet()
    Else
        Set workWs = ws
    End If

    If workWs Is Nothing Then Exit Sub

    modeText = ModeFromStageProfile(GetSelectedStageProfile())

    If Not GetModeBlockColumns( _
            modeText, _
            barcodeCol, _
            orderCol, _
            itemCol, _
            qtyCol, _
            timeCol, _
            checkCol, _
            commentCol, _
            recentValueCell) Then
        Exit Sub
    End If

    'Place the button on row 4 directly above the active stage comments column:
    'SEND = W4, RECV = AF4, STAGING = AV4.
    Set targetCell = workWs.Cells(4, commentCol)

    On Error Resume Next

    wasProtected = (workWs.ProtectContents Or workWs.ProtectDrawingObjects Or workWs.ProtectScenarios)
    If wasProtected Then workWs.Unprotect Password:=""

    workWs.Shapes(STAGE_COMMENT_SAVE_BUTTON_NAME).Delete

    Set shp = workWs.Shapes.AddShape( _
        Type:=msoShapeRoundedRectangle, _
        Left:=targetCell.Left + 2, _
        Top:=targetCell.Top + 2, _
        Width:=targetCell.Width - 4, _
        Height:=targetCell.Height - 4)

    With shp
        .Name = STAGE_COMMENT_SAVE_BUTTON_NAME
        .OnAction = macroName
        .Placement = xlMoveAndSize
        .Locked = False

        With .TextFrame2
            .VerticalAnchor = msoAnchorMiddle
            .TextRange.ParagraphFormat.Alignment = msoAlignCenter
            .TextRange.Font.Size = 9
            .TextRange.Font.Bold = msoTrue
        End With
    End With

    targetCell.Value = vbNullString

    UpdateStageCommentSaveButton workWs

    If wasProtected Then ProtectImportedStageForScanning workWs

    On Error GoTo 0
End Sub

Public Sub UpdateStageCommentSaveButton(Optional ByVal ws As Worksheet = Nothing)
    Dim workWs As Worksheet
    Dim shp As Shape

    If ws Is Nothing Then
        Set workWs = StageViewSheet()
    Else
        Set workWs = ws
    End If

    If workWs Is Nothing Then Exit Sub

    On Error Resume Next
    Set shp = workWs.Shapes(STAGE_COMMENT_SAVE_BUTTON_NAME)
    On Error GoTo 0

    If shp Is Nothing Then Exit Sub

    If StageCommentsHaveUnsavedChanges() Then
        shp.TextFrame2.TextRange.Text = "Not Saved"
        shp.Fill.ForeColor.RGB = RGB(255, 199, 206)
        shp.Line.ForeColor.RGB = RGB(156, 0, 6)
        shp.TextFrame2.TextRange.Font.Fill.ForeColor.RGB = RGB(156, 0, 6)
    Else
        shp.TextFrame2.TextRange.Text = "Saved"
        shp.Fill.ForeColor.RGB = RGB(198, 239, 206)
        shp.Line.ForeColor.RGB = RGB(0, 97, 0)
        shp.TextFrame2.TextRange.Font.Fill.ForeColor.RGB = RGB(0, 97, 0)
    End If
End Sub

Public Sub MarkStageCommentsDirtyFromEdit()
    UpdateStageCommentSaveButton StageViewSheet()
End Sub

Public Function StageCommentsHaveUnsavedChanges() As Boolean
    StageCommentsHaveUnsavedChanges = (CountUnsavedStageCommentRows() > 0)
End Function

Private Function CountUnsavedStageCommentRows() As Long
    Dim ws As Worksheet
    Dim headerRow As Long
    Dim lastRow As Long
    Dim r As Long

    Dim barcodeCol As Long
    Dim orderCol As Long
    Dim itemCol As Long
    Dim qtyCol As Long
    Dim timeCol As Long
    Dim checkCol As Long
    Dim commentCol As Long
    Dim recentValueCell As Range

    Dim currentComment As String
    Dim originalComment As String

    Set ws = StageViewSheet()
    If ws Is Nothing Then Exit Function
    If Not IsImportedStageLoaded() Then Exit Function

    If Not GetModeBlockColumns( _
            ModeFromStageProfile(GetSelectedStageProfile()), _
            barcodeCol, _
            orderCol, _
            itemCol, _
            qtyCol, _
            timeCol, _
            checkCol, _
            commentCol, _
            recentValueCell) Then
        Exit Function
    End If

    headerRow = GetImportedMainHeaderRow(ws)
    If headerRow = 0 Then Exit Function

    lastRow = ws.Cells(ws.Rows.Count, 5).End(xlUp).Row

    For r = headerRow + 1 To lastRow
        If IsNumeric(ws.Cells(r, 5).Value) And IsNumeric(ws.Cells(r, 6).Value) Then
            currentComment = CleanStageSyncCommentText(ws.Cells(r, commentCol).Value)
            originalComment = CleanStageSyncCommentText(ws.Cells(r, COMMENT_BASELINE_COL).Value)

            If StrComp(currentComment, originalComment, vbTextCompare) <> 0 Then
                CountUnsavedStageCommentRows = CountUnsavedStageCommentRows + 1
            End If
        End If
    Next r
End Function

Public Sub SaveStageCommentsToMasterFromButton()
    Dim queuedCount As Long
    Dim errorMessage As String
    Dim ws As Worksheet

    Set ws = StageViewSheet()

    If ws Is Nothing Then Exit Sub

    If Not IsImportedStageLoaded() Then
        MsgBox "There is no loaded intake sheet to save comments from.", _
               vbExclamation, "Save Comments"
        Exit Sub
    End If

    If Not StageCommentsHaveUnsavedChanges() Then
        UpdateStageCommentSaveButton ws
        FocusStageScanBox
        Exit Sub
    End If

    ShowProcessingNotice "Sending comment updates to the master queue. Please wait."
    DoEvents

    If Not QueuePendingStageCommentsToMasterNoWait(queuedCount, errorMessage) Then
        HideProcessingNotice

        MsgBox "Comments were not queued." & vbCrLf & vbCrLf & _
               errorMessage, _
               vbExclamation, "Save Comments"

        UpdateStageCommentSaveButton ws
        FocusStageScanBox
        Exit Sub
    End If

    HideProcessingNotice

    'The comments have been accepted into ScanQueue.
    'Do not wait for the master to process them.
    UpdateStageCommentSaveButton ws
    ProtectImportedStageForScanning ws

    On Error Resume Next

With StationSheet()
    .Range(CELL_LAST_QUEUE_STATUS).Value = "Comments queued"
    .Range(CELL_LAST_RESULT_CODE).Value = vbNullString
    .Range(CELL_LAST_SCAN_RESULT).Value = "Saved"
    .Range(CELL_LAST_RESULT_MESSAGE).Value = _
        "Comment update(s) were sent to the master queue. Rows queued: " & queuedCount
End With

On Error GoTo 0

    FocusStageScanBox
End Sub

Public Function ConfirmDiscardUnsavedStageComments(ByVal actionName As String) As Boolean
    Dim unsavedCount As Long

    unsavedCount = CountUnsavedStageCommentRows()

    If unsavedCount <= 0 Then
        ConfirmDiscardUnsavedStageComments = True
        Exit Function
    End If

    ConfirmDiscardUnsavedStageComments = _
        (MsgBox("You have unsaved comments." & vbCrLf & vbCrLf & _
                "Unsaved comment row(s): " & unsavedCount & vbCrLf & vbCrLf & _
                "If you continue, these local comments will be deleted when the intake sheet reloads." & vbCrLf & vbCrLf & _
                "Click Yes to continue without saving." & vbCrLf & _
                "Click No to cancel and use Save Comments first.", _
                vbYesNo + vbExclamation, actionName) = vbYes)
End Function

Public Function QueuePendingStageCommentsToMasterNoWait(ByRef queuedCount As Long, _
                                                        Optional ByRef errorMessage As String = vbNullString) As Boolean
    Dim ws As Worksheet
    Dim headerRow As Long
    Dim lastRow As Long
    Dim r As Long

    Dim barcodeCol As Long
    Dim orderCol As Long
    Dim itemCol As Long
    Dim qtyCol As Long
    Dim timeCol As Long
    Dim checkCol As Long
    Dim commentCol As Long
    Dim recentValueCell As Range

    Dim deliveryKey As String
    Dim modeText As String
    Dim targetSheet As String
    Dim stationName As String
    Dim requestId As String

    Dim ord As Long
    Dim itm As Long

    Dim currentComment As String
    Dim originalComment As String
    Dim commentPayload As String

    queuedCount = 0
    errorMessage = vbNullString
    QueuePendingStageCommentsToMasterNoWait = False

    Set ws = StageViewSheet()
    If ws Is Nothing Then
        errorMessage = "There is no loaded intake sheet."
        Exit Function
    End If

    If Not IsImportedStageLoaded() Then
        errorMessage = "There is no loaded intake sheet."
        Exit Function
    End If

    deliveryKey = GetSelectedDeliveryKey()
    modeText = ModeFromStageProfile(GetSelectedStageProfile())
    targetSheet = StageSheetFromProfile(GetSelectedStageProfile())
    stationName = GetStationName()

    If Len(deliveryKey) = 0 Or Len(modeText) = 0 Or Len(targetSheet) = 0 Then
        errorMessage = "Delivery list or stage settings are missing."
        Exit Function
    End If

    If Not GetModeBlockColumns( _
            modeText, _
            barcodeCol, _
            orderCol, _
            itemCol, _
            qtyCol, _
            timeCol, _
            checkCol, _
            commentCol, _
            recentValueCell) Then

        errorMessage = "Could not find the comments column for the selected stage."
        Exit Function
    End If

    headerRow = GetImportedMainHeaderRow(ws)

    If headerRow = 0 Then
        errorMessage = "Could not find the imported delivery-list header row."
        Exit Function
    End If

    lastRow = ws.Cells(ws.Rows.Count, 5).End(xlUp).Row

    For r = headerRow + 1 To lastRow
        If IsNumeric(ws.Cells(r, 5).Value) And IsNumeric(ws.Cells(r, 6).Value) Then
            ord = CLng(Val(ws.Cells(r, 5).Value))
            itm = CLng(Val(ws.Cells(r, 6).Value))

            If ord > 0 And itm > 0 Then
                currentComment = CleanStageSyncCommentText(ws.Cells(r, commentCol).Value)
                originalComment = CleanStageSyncCommentText(ws.Cells(r, COMMENT_BASELINE_COL).Value)

                If StrComp(currentComment, originalComment, vbTextCompare) <> 0 Then
                    requestId = BuildRequestId(stationName)

                    'Send the full current comment value.
                    'This supports add, edit, and delete/clear.
                    commentPayload = COMMENT_SET_PREFIX & currentComment

                    If Not PA_QueueAddRequest( _
                            requestId, _
                            deliveryKey, _
                            "COMMENT", _
                            modeText, _
                            vbNullString, _
                            ord, _
                            itm, _
                            0, _
                            targetSheet, _
                            stationName, _
                            commentPayload) Then

                        errorMessage = "Could not queue comment update for Order " & ord & _
                                       " / Item " & Format$(itm, "000") & "."
                        Exit Function
                    End If

                    'Do not wait for the master.
                    'Once SharePoint accepts the COMMENT row, treat this local comment as saved/queued.
                    ws.Cells(r, COMMENT_BASELINE_COL).Value = currentComment
                    queuedCount = queuedCount + 1
                End If
            End If
        End If
    Next r

    QueuePendingStageCommentsToMasterNoWait = True
End Function
