Attribute VB_Name = "modIntakePrintExport"
Option Explicit

'==============================================================================
' Module: modIntakePrintExport
' Workbook: Intake_Staging_Test.xlsm
'
' Purpose:
'   Small safety/wrapper layer for intake print and export buttons.
'
' What this module does:
'   1. Confirms a delivery-list snapshot is loaded before print/export starts.
'   2. Returns the currently imported stage worksheet.
'   3. Confirms the remake print template exists before remake print/export.
'   4. Provides safe button-entry procedures that show friendly error messages.
'
' What this module does NOT do:
'   It does not build print previews, create export workbooks, or filter rows.
'   That work is handled by modIntakePrintExportTemplates and
'   modIntakePrintHelpers.
'==============================================================================

Private Const REMAKE_PRINT_TEMPLATE_SHEET As String = "__REMAKE_PRINT_TEMPLATE__"
Private Const MSG_TITLE_PRINT_EXPORT As String = "Print / Export"
Private Const MSG_TITLE_REMAKE_TEMPLATE As String = "Missing Remake Template"


'==============================================================================
' Source sheet resolver
'
' Returns the imported stage worksheet that print/export should use.
'==============================================================================
Public Function GetIntakePrintExportSourceSheet() As Worksheet
    Dim srcWs As Worksheet

    If Not IsImportedStageLoaded() Then
        MsgBox "No delivery list snapshot is currently loaded." & vbCrLf & vbCrLf & _
               "Use Settings and import a delivery list first.", _
               vbExclamation, MSG_TITLE_PRINT_EXPORT
        Exit Function
    End If

    Set srcWs = StageViewSheet()

    If srcWs Is Nothing Then
        MsgBox "The intake workbook says a snapshot is loaded, but the imported stage sheet could not be found." & vbCrLf & vbCrLf & _
               "Use Settings and import the delivery list again.", _
               vbExclamation, MSG_TITLE_PRINT_EXPORT
        Exit Function
    End If

    Set GetIntakePrintExportSourceSheet = srcWs
End Function


'==============================================================================
' Print/export readiness check
'
' Returns True only when the imported stage sheet is available.
' The resolved worksheet is returned through srcWs.
'==============================================================================
Public Function EnsureIntakePrintExportReady(ByRef srcWs As Worksheet) As Boolean
    Set srcWs = GetIntakePrintExportSourceSheet()

    If srcWs Is Nothing Then Exit Function

    EnsureIntakePrintExportReady = True
End Function


'==============================================================================
' Worksheet existence helper
'
' Checks for a sheet by name in this intake workbook.
'==============================================================================
Public Function IntakeSheetExists(ByVal sheetName As String) As Boolean
    Dim ws As Worksheet

    sheetName = Trim$(sheetName)
    If Len(sheetName) = 0 Then Exit Function

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(sheetName)
    On Error GoTo 0

    IntakeSheetExists = Not ws Is Nothing
End Function


'==============================================================================
' Remake template requirement
'
' Remake printing/exporting depends on the hidden remake template sheet.
'==============================================================================
Public Function RequireIntakeRemakeTemplateSheet() As Boolean
    If IntakeSheetExists(REMAKE_PRINT_TEMPLATE_SHEET) Then
        RequireIntakeRemakeTemplateSheet = True
    Else
        MsgBox "The hidden sheet '" & REMAKE_PRINT_TEMPLATE_SHEET & "' is missing from the intake workbook." & vbCrLf & vbCrLf & _
               "Copy that sheet from the master workbook into the intake workbook first.", _
               vbExclamation, MSG_TITLE_REMAKE_TEMPLATE
    End If
End Function


'==============================================================================
' Delivery display text
'
' Returns the selected delivery display name for messages/file labels.
' Falls back to the delivery key, then a generic label.
'==============================================================================
Public Function GetIntakeDeliveryDisplayText() As String
    Dim displayText As String

    displayText = Trim$(GetSelectedDeliveryDisplay())

    If Len(displayText) = 0 Then
        displayText = Trim$(GetSelectedDeliveryKey())
    End If

    If Len(displayText) = 0 Then
        displayText = "Delivery List"
    End If

    GetIntakeDeliveryDisplayText = displayText
End Function


'==============================================================================
' Stage display text
'
' Returns the current imported stage sheet name for labels/messages.
' This intentionally avoids showing a popup when no snapshot is loaded.
'==============================================================================
Public Function GetIntakeStageDisplayText() As String
    Dim ws As Worksheet

    If Not IsImportedStageLoaded() Then Exit Function

    Set ws = StageViewSheet()
    If ws Is Nothing Then Exit Function

    GetIntakeStageDisplayText = Trim$(ws.Name)
End Function


'==============================================================================
' Safe print button entry point
'
' Use this from intake buttons instead of calling PrintDeliveryListBySection_Intake
' directly. This keeps user-facing error handling in one place.
'==============================================================================
Public Sub RunIntakePrintDeliveryListSafe()
    On Error GoTo ErrHandler

    PrintDeliveryListBySection_Intake
    Exit Sub

ErrHandler:
    MsgBox "Print failed." & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbExclamation, "Print Error"
End Sub


'==============================================================================
' Safe export button entry point
'
' Use this from intake buttons instead of calling ExportListsFromIntake directly.
' This keeps user-facing error handling in one place.
'==============================================================================
Public Sub RunIntakeExportListsSafe()
    On Error GoTo ErrHandler

    ExportListsFromIntake
    Exit Sub

ErrHandler:
    MsgBox "Export failed." & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbExclamation, "Export Error"
End Sub


