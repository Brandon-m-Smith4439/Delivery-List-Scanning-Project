Attribute VB_Name = "modImportDebug"
Option Explicit

'==============================================================================
' Module: modImportDebug
' Workbook: Intake_Staging_Test.xlsm
'
' Purpose:
'   Provides optional troubleshooting logs for the intake snapshot/import process.
'   Also provides small worksheet-inspection helpers used by modStageSnapshot.
'
' Normal production behavior:
'   IMPORT_DEBUG_ENABLED is False, so ImportDebugReset and ImportDebugLog exit
'   immediately. No debug sheet is created and no logging is written.
'
' Debug behavior:
'   Set IMPORT_DEBUG_ENABLED to True only while troubleshooting import problems.
'   When enabled, this module creates a VeryHidden "__IMPORT_DEBUG__" worksheet
'   and records each import step, procedure name, and details.
'
' Keep/remove decision:
'   This module is currently still referenced by modStageSnapshot and
'   modIntakeStation. Do not delete it unless those references are also removed
'   or replaced.
'==============================================================================

Public Const IMPORT_DEBUG_ENABLED As Boolean = False

Private Const IMPORT_DEBUG_SHEET As String = "__IMPORT_DEBUG__"
Private Const IMPORT_DEBUG_HEADER_ROW As Long = 1
Private Const IMPORT_DEBUG_FIRST_DATA_ROW As Long = 2

Private Const IMPORT_DEBUG_TITLE_SEARCH_RANGE As String = "A1:AG8"
Private Const IMPORT_DEBUG_HEADER_SEARCH_FIRST_ROW As Long = 1
Private Const IMPORT_DEBUG_HEADER_SEARCH_LAST_ROW As Long = 40

Private Const IMPORT_DEBUG_ORDER_HEADER_COL As Long = 5      'Column E
Private Const IMPORT_DEBUG_ITEM_HEADER_COL As Long = 6       'Column F
Private Const IMPORT_DEBUG_ORDER_HEADER_TEXT As String = "Order Nr."
Private Const IMPORT_DEBUG_ITEM_HEADER_TEXT As String = "Item Nr."


'==============================================================================
' Debug sheet reset
'
' Clears and rebuilds the hidden import-debug sheet.
'
' This only runs when IMPORT_DEBUG_ENABLED = True.
' In normal production mode, this procedure exits immediately.
'==============================================================================
Public Sub ImportDebugReset()
    Dim ws As Worksheet

    If Not IMPORT_DEBUG_ENABLED Then Exit Sub

    Set ws = ImportDebugGetSheet(True)
    If ws Is Nothing Then Exit Sub

    ws.Cells.Clear

    ws.Range("A1:F1").Value = Array( _
        "LoggedAt", _
        "Procedure", _
        "Step", _
        "Detail1", _
        "Detail2", _
        "Detail3" _
    )

    ws.Rows(IMPORT_DEBUG_HEADER_ROW).Font.Bold = True
    ws.Visible = xlSheetVeryHidden
End Sub


'==============================================================================
' Debug log writer
'
' Appends one row to the hidden import-debug sheet.
'
' Arguments:
'   procName  - procedure that is writing the log entry
'   stepName  - checkpoint/action name inside the procedure
'   detail1   - optional extra detail
'   detail2   - optional extra detail
'   detail3   - optional extra detail
'
' This only runs when IMPORT_DEBUG_ENABLED = True.
' In normal production mode, this procedure exits immediately.
'==============================================================================
Public Sub ImportDebugLog(ByVal procName As String, _
                          ByVal stepName As String, _
                          Optional ByVal detail1 As String = vbNullString, _
                          Optional ByVal detail2 As String = vbNullString, _
                          Optional ByVal detail3 As String = vbNullString)

    Dim ws As Worksheet
    Dim nextRow As Long
    Dim loggedAt As Date

    If Not IMPORT_DEBUG_ENABLED Then Exit Sub

    loggedAt = Now

    Set ws = ImportDebugGetSheet(True)
    If ws Is Nothing Then Exit Sub

    nextRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row + 1
    If nextRow < IMPORT_DEBUG_FIRST_DATA_ROW Then nextRow = IMPORT_DEBUG_FIRST_DATA_ROW

    ws.Cells(nextRow, 1).Value = loggedAt
    ws.Cells(nextRow, 2).Value = procName
    ws.Cells(nextRow, 3).Value = stepName
    ws.Cells(nextRow, 4).Value = detail1
    ws.Cells(nextRow, 5).Value = detail2
    ws.Cells(nextRow, 6).Value = detail3

    Debug.Print Format$(loggedAt, "yyyy-mm-dd hh:nn:ss"), _
                procName, _
                stepName, _
                detail1, _
                detail2, _
                detail3
End Sub


'==============================================================================
' Delivery title finder
'
' Searches the top-left section of a worksheet for the delivery-list title.
'
' Used by:
'   modStageSnapshot.LoadSelectedStageSnapshot
'
' This is used to confirm that the source sheet and pasted intake sheet appear
' to contain the same delivery list after the import copy/paste operation.
'==============================================================================
Public Function ImportDebugFindDeliveryTitle(ByVal ws As Worksheet) As String
    Dim c As Range
    Dim txt As String

    If ws Is Nothing Then Exit Function

    For Each c In ws.Range(IMPORT_DEBUG_TITLE_SEARCH_RANGE).Cells
        txt = ImportDebugCellValueText(c)

        If Len(txt) > 0 Then
            If InStr(1, UCase$(txt), "DELIVERY LIST FOR", vbTextCompare) > 0 Then
                ImportDebugFindDeliveryTitle = txt
                Exit Function
            End If
        End If
    Next c
End Function


'==============================================================================
' Snapshot summary builder
'
' Returns a compact text summary of a stage/import worksheet.
'
' Used by:
'   modStageSnapshot.LoadSelectedStageSnapshot
'
' This is mainly for troubleshooting. It records the detected title, top scan
' status cells, detected header row, and last data row.
'==============================================================================
Public Function ImportDebugSummary(ByVal ws As Worksheet) As String
    If ws Is Nothing Then
        ImportDebugSummary = "Worksheet=<nothing>"
        Exit Function
    End If

    ImportDebugSummary = _
        "Title=" & ImportDebugFindDeliveryTitle(ws) & _
        " | O2=" & ImportDebugRangeDisplayText(ws, "O2") & _
        " | X2=" & ImportDebugRangeDisplayText(ws, "X2") & _
        " | AO2=" & ImportDebugRangeDisplayText(ws, "AO2") & _
        " | HeaderRow=" & CStr(ImportDebugHeaderRow(ws)) & _
        " | LastDataRow=" & CStr(ImportDebugLastDataRow(ws))
End Function


'==============================================================================
' Debug sheet viewer
'
' Shows the hidden debug sheet so it can be inspected manually.
'
' This is intended to be run manually from the VBA editor or Macro dialog after
' enabling IMPORT_DEBUG_ENABLED and reproducing an import issue.
'==============================================================================
Public Sub ImportDebugShowSheet()
    Dim ws As Worksheet

    Set ws = ImportDebugGetSheet(False)

    If ws Is Nothing Then
        MsgBox "No import debug sheet exists yet." & vbCrLf & vbCrLf & _
               "To create one, set IMPORT_DEBUG_ENABLED to True and run the import/refresh again.", _
               vbInformation, _
               "Import Debug"
        Exit Sub
    End If

    ws.Visible = xlSheetVisible
    ws.Activate
End Sub


'==============================================================================
' Debug sheet getter/creator
'
' Returns the "__IMPORT_DEBUG__" sheet.
'
' If createIfMissing = True:
'   Creates the sheet if it does not already exist.
'
' If createIfMissing = False:
'   Returns Nothing when the sheet does not exist.
'==============================================================================
Private Function ImportDebugGetSheet(ByVal createIfMissing As Boolean) As Worksheet
    Dim ws As Worksheet

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(IMPORT_DEBUG_SHEET)
    On Error GoTo 0

    If ws Is Nothing And createIfMissing Then
        On Error GoTo CreateFailed

        Set ws = ThisWorkbook.Worksheets.Add(After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
        ws.Name = IMPORT_DEBUG_SHEET
        ws.Visible = xlSheetVeryHidden

        On Error GoTo 0
    End If

    Set ImportDebugGetSheet = ws
    Exit Function

CreateFailed:
    Set ImportDebugGetSheet = Nothing
End Function


'==============================================================================
' Header row finder
'
' Looks for the main imported delivery-list header row.
'
' Expected header structure:
'   Column E = "Order Nr."
'   Column F = "Item Nr."
'
' This is private because no other module needs to call it directly. Other
' modules should call ImportDebugSummary instead.
'==============================================================================
Private Function ImportDebugHeaderRow(ByVal ws As Worksheet) As Long
    Dim r As Long

    If ws Is Nothing Then Exit Function

    For r = IMPORT_DEBUG_HEADER_SEARCH_FIRST_ROW To IMPORT_DEBUG_HEADER_SEARCH_LAST_ROW
        If StrComp(ImportDebugCellValueText(ws.Cells(r, IMPORT_DEBUG_ORDER_HEADER_COL)), _
                   IMPORT_DEBUG_ORDER_HEADER_TEXT, _
                   vbTextCompare) = 0 And _
           StrComp(ImportDebugCellValueText(ws.Cells(r, IMPORT_DEBUG_ITEM_HEADER_COL)), _
                   IMPORT_DEBUG_ITEM_HEADER_TEXT, _
                   vbTextCompare) = 0 Then

            ImportDebugHeaderRow = r
            Exit Function
        End If
    Next r
End Function


'==============================================================================
' Last data row finder
'
' Returns the last used row in the imported delivery-list Order Nr. column.
'
' This is private because no other module needs to call it directly. Other
' modules should call ImportDebugSummary instead.
'==============================================================================
Private Function ImportDebugLastDataRow(ByVal ws As Worksheet) As Long
    If ws Is Nothing Then Exit Function

    ImportDebugLastDataRow = ws.Cells(ws.Rows.Count, IMPORT_DEBUG_ORDER_HEADER_COL).End(xlUp).Row
End Function


'==============================================================================
' Safe cell value reader
'
' Converts a single cell value to trimmed text.
'
' This avoids Type Mismatch errors if the worksheet contains an Excel error value
' such as #N/A, #VALUE!, or #REF!.
'==============================================================================
Private Function ImportDebugCellValueText(ByVal c As Range) As String
    If c Is Nothing Then Exit Function
    If IsError(c.Value) Then Exit Function

    ImportDebugCellValueText = Trim$(CStr(c.Value))
End Function


'==============================================================================
' Safe range display-text reader
'
' Reads the displayed text of a cell address, such as O2 or AO2.
'
' This is used in ImportDebugSummary so the debug summary reflects what the user
' would visually see in the worksheet.
'==============================================================================
Private Function ImportDebugRangeDisplayText(ByVal ws As Worksheet, ByVal addressText As String) As String
    If ws Is Nothing Then Exit Function
    If Len(addressText) = 0 Then Exit Function

    On Error Resume Next
    ImportDebugRangeDisplayText = CStr(ws.Range(addressText).Text)
    On Error GoTo 0
End Function

