Attribute VB_Name = "modScanningPanelButtons"
Option Explicit

'==============================================================================
' Module: modScanningPanelButtons
' Workbook: Intake_Scanning_Test.xlsm / Intake scanner workbook
'
' What this module does:
'   Builds and styles the button shapes on the Scanning Panel sheet and wires
'   them to the correct intake macros.
'
' Why this module exists:
'   The panel is the operator-facing control surface, so button layout and
'   macro wiring must be repeatable after workbook refreshes or repairs.
'
' Commenting standard used in this rewrite:
'   Comments explain both what each procedure/section does and why it
'   matters to the scanning, SharePoint, Power Automate, buffering, and
'   operator-safety workflow. The code behavior and public procedure names
'   are intentionally kept stable so existing buttons/forms/timers keep working.
'==============================================================================


'modScanningPanelButtons

'========================
' Button fonts
'========================
Private Const FONT_BASE As String = "Aptos"
Private Const FONT_ICON As String = "Segoe MDL2 Assets"

'========================
' Base button palette
'========================
Private Const BTN_PRIMARY_R As Long = 47
Private Const BTN_PRIMARY_G As Long = 75
Private Const BTN_PRIMARY_B As Long = 117

Private Const BTN_TXT_R As Long = 255
Private Const BTN_TXT_G As Long = 255
Private Const BTN_TXT_B As Long = 255

'========================
' Gradient settings
'========================
Private Const BTN_GRADIENT_STYLE As Long = 3   'DiagonalUp
Private Const BTN_ACCENT_BLEND As Double = 0.6
Private Const BTN_GRADIENT_VARIANT As Long = 1


'========================
' Default accent
'========================
Private Const BTN_ACCENT_R As Long = 20
Private Const BTN_ACCENT_G As Long = 255
Private Const BTN_ACCENT_B As Long = 15

'========================
' Glyph codepoints
'========================
Private Const CP_KEYBOARD As Long = &HE765
Private Const CP_SETTINGS As Long = &HE713
Private Const CP_PRINT As Long = &HE749
Private Const CP_UP_ARROW As Long = &HE74A
Private Const CP_REFRESH As Long = &HE72C

Private Type BtnTheme
    Fill As Long
    Font As Long
End Type

'------------------------------------------------------------------------------
' Procedure: GlyphFromCP
' Scope: Private Function
'
' What it does:
'   Builds, formats, or updates the intake operator panel/buttons for
'   GlyphFromCP.
'
' Why it exists:
'   Consistent button shapes and macro assignments make the intake panel
'   repairable and easy for operators to use.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function GlyphFromCP(ByVal cp As Long) As String
    GlyphFromCP = ChrW$(cp)
End Function

'------------------------------------------------------------------------------
' Procedure: Rgb3
' Scope: Private Function
'
' What it does:
'   Performs the intake-workbook step named Rgb3 inside
'   modScanningPanelButtons.
'
' Why it exists:
'   Consistent button shapes and macro assignments make the intake panel
'   repairable and easy for operators to use.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function Rgb3(ByVal r As Long, ByVal g As Long, ByVal b As Long) As Long
    Rgb3 = RGB(r, g, b)
End Function

'------------------------------------------------------------------------------
' Procedure: accentColor
' Scope: Private Function
'
' What it does:
'   Finds, sizes, hides, or formats worksheet columns for accentColor.
'
' Why it exists:
'   Consistent button shapes and macro assignments make the intake panel
'   repairable and easy for operators to use.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function accentColor() As Long
    accentColor = RGB(BTN_ACCENT_R, BTN_ACCENT_G, BTN_ACCENT_B)
End Function

'------------------------------------------------------------------------------
' Procedure: ThemePrimary
' Scope: Private Function
'
' What it does:
'   Builds, formats, or updates the intake operator panel/buttons for
'   ThemePrimary.
'
' Why it exists:
'   Consistent button shapes and macro assignments make the intake panel
'   repairable and easy for operators to use.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function ThemePrimary() As BtnTheme
    Dim t As BtnTheme
    t.Fill = Rgb3(BTN_PRIMARY_R, BTN_PRIMARY_G, BTN_PRIMARY_B)
    t.Font = Rgb3(BTN_TXT_R, BTN_TXT_G, BTN_TXT_B)
    ThemePrimary = t
End Function

'------------------------------------------------------------------------------
' Procedure: BuildScanningPanelButtons
' Scope: Public Sub
'
' What it does:
'   Rebuilds every operator button on the Scanning Panel and wires each shape
'   to its assigned macro.
'
' Why it exists:
'   If shapes are deleted, copied, or broken by workbook edits, rebuilding
'   restores the operator control panel in one step.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub BuildScanningPanelButtons()
    Dim ws As Worksheet
    Dim thm As BtnTheme
    Dim wasProtected As Boolean

    Set ws = StationSheet()
    thm = ThemePrimary()

    On Error Resume Next
    wasProtected = (ws.ProtectContents Or ws.ProtectDrawingObjects Or ws.ProtectScenarios)
    If wasProtected Then ws.Unprotect
    On Error GoTo FailBuild

    DeletePanelButton ws, "btnScannerManual"
    DeletePanelButton ws, "btnScannerManual_ico"
    DeletePanelButton ws, "btnScannerSettings"
    DeletePanelButton ws, "btnScannerSettings_ico"
    DeletePanelButton ws, "btnScannerPrint"
    DeletePanelButton ws, "btnScannerPrint_ico"
    DeletePanelButton ws, "btnScannerExport"
    DeletePanelButton ws, "btnScannerExport_ico"
    DeletePanelButton ws, "btnScannerRefresh"
    DeletePanelButton ws, "btnScannerRefresh_ico"
    DeletePanelButton ws, "btnScannerQueueRefresh"
    DeletePanelButton ws, "btnScannerQueueRefresh_ico"

    AddIconButton ws, "H13:K15", "btnScannerManual", GlyphFromCP(CP_KEYBOARD), _
                  "MANUAL SCAN ENTRY", "Used to manually scan a missed tag", _
                  "ShowSharedManualScanFormOrPrompt", thm, RGB(255, 181, 54)

    AddIconButton ws, "L13:O15", "btnScannerSettings", GlyphFromCP(CP_SETTINGS), _
                  "SETTINGS", "Choose list and stage then load snapshot", _
                  "ChangeScannerSettings", thm, RGB(196, 196, 196)

    AddIconButton ws, "H17:K19", "btnScannerPrint", GlyphFromCP(CP_PRINT), _
                  "PRINT DELIVERY LIST", "Prints the imported delivery list snapshot", _
                  "RunIntakePrintDeliveryListSafe", thm, RGB(196, 196, 196)

    AddIconButton ws, "L17:O19", "btnScannerExport", GlyphFromCP(CP_UP_ARROW), _
                  "EXPORT DELIVERY LIST", "Exports the imported delivery list snapshot", _
                  "RunIntakeExportListsSafe", thm, RGB(15, 255, 179)

    AddIconButton ws, "H21:K23", "btnScannerRefresh", GlyphFromCP(CP_REFRESH), _
              "REFRESH SNAPSHOT", "Ask master for newest snapshot", _
              "RefreshCurrentIntakeSnapshot", thm, RGB(91, 155, 213)

    AddIconButton ws, "L21:O23", "btnScannerQueueRefresh", GlyphFromCP(CP_REFRESH), _
                  "REFRESH QUEUE STATUS", "Manually checks queue results for the imported stage", _
                  "RefreshQueueStatusNow", thm, RGB(112, 173, 71)

SafeExit:
    On Error Resume Next
    If wasProtected Then
        ws.Protect DrawingObjects:=True, Contents:=True, Scenarios:=True, UserInterfaceOnly:=True
    End If
    On Error GoTo 0
    Exit Sub

FailBuild:
    MsgBox "BuildScanningPanelButtons failed." & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbExclamation, "Scanning Panel"
    Resume SafeExit
End Sub

'------------------------------------------------------------------------------
' Procedure: DeletePanelButton
' Scope: Private Sub
'
' What it does:
'   Builds, formats, or updates the intake operator panel/buttons for
'   DeletePanelButton.
'
' Why it exists:
'   Consistent button shapes and macro assignments make the intake panel
'   repairable and easy for operators to use.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub DeletePanelButton(ByVal ws As Worksheet, ByVal shapeName As String)
    On Error Resume Next
    ws.Shapes(shapeName).Delete
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: AddIconButton
' Scope: Private Sub
'
' What it does:
'   Creates a rounded button shape plus a separate icon overlay, applies
'   gradient styling, and assigns the click macro.
'
' Why it exists:
'   Using shapes gives the panel a clean operator-friendly UI while still
'   calling normal VBA macros.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub AddIconButton( _
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
    Dim acc As Long
    Dim labelText As String
    Dim titleLen As Long

    Set r = ws.Range(anchorRangeAddress)

    On Error Resume Next
    ws.Shapes(shapeName).Delete
    ws.Shapes(shapeName & "_ico").Delete
    On Error GoTo FailAdd

    btnW = r.Width - 6
    btnH = r.Height - 4

    If btnW < 120 Then btnW = 120
    If btnW > r.Width Then btnW = r.Width

    If btnH < 36 Then btnH = 36
    If btnH > r.Height Then btnH = r.Height

    leftPos = r.Left + (r.Width - btnW) / 2
    topPos = r.Top + (r.Height - btnH) / 2

    iconPad = 8
    iconW = btnH * 0.5
    textMargin = iconPad + iconW + 8

    If accentRGB = -1 Then
        acc = accentColor()
    Else
        acc = accentRGB
    End If

    labelText = titleText & vbLf & descText
    titleLen = Len(titleText)

    Set btn = ws.Shapes.AddShape(msoShapeRoundedRectangle, leftPos, topPos, btnW, btnH)
    With btn
        .Name = shapeName
        .OnAction = "'" & ThisWorkbook.Name & "'!" & macroName

With .Fill
    .Visible = msoTrue
    .TwoColorGradient BTN_GRADIENT_STYLE, BTN_GRADIENT_VARIANT
    .ForeColor.RGB = theme.Fill
    .BackColor.RGB = BlendColors(theme.Fill, acc, BTN_ACCENT_BLEND)
End With

        With .Line
            .Visible = msoTrue
            .ForeColor.RGB = RGB(255, 255, 255)
            .Transparency = 0.7
            .Weight = 0.9
        End With

        On Error Resume Next
        .Shadow.Visible = msoTrue
        .Shadow.Blur = 4
        .Shadow.OffsetX = 1.5
        .Shadow.OffsetY = 1.5
        .Shadow.Transparency = 0.75
        On Error GoTo FailAdd

        With .TextFrame2
            .VerticalAnchor = msoAnchorMiddle
            .WordWrap = msoTrue
            .MarginLeft = textMargin
            .MarginRight = 8
            .MarginTop = 4
            .MarginBottom = 4
            .TextRange.Text = labelText
            .TextRange.ParagraphFormat.Alignment = msoAlignCenter

            With .TextRange.Font
                .Name = FONT_BASE
                .Fill.ForeColor.RGB = theme.Font
            End With

            With .TextRange.Characters(1, titleLen).Font
                .Size = 10
                .Bold = msoTrue
            End With

            If Len(descText) > 0 Then
                With .TextRange.Characters(titleLen + 2, Len(descText)).Font
                    .Size = 8
                    .Bold = msoFalse
                    .Fill.ForeColor.RGB = RGB(235, 240, 248)
                End With
            End If
        End With
    End With

    Set ico = ws.Shapes.AddTextbox(msoTextOrientationHorizontal, _
                                   leftPos + iconPad, _
                                   topPos + (btnH - iconW) / 2, _
                                   iconW, iconW)

    With ico
        .Name = shapeName & "_ico"
        .OnAction = "'" & ThisWorkbook.Name & "'!" & macroName
        .Line.Visible = msoFalse
        .Fill.Visible = msoFalse

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
                .Size = iconW * 0.8
                .Bold = msoTrue
                .Fill.ForeColor.RGB = theme.Font
            End With
        End With
    End With

    Exit Sub

FailAdd:
    Err.Raise Err.Number, "AddIconButton(" & shapeName & ")", Err.Description
End Sub

'------------------------------------------------------------------------------
' Procedure: BlendColors
' Scope: Private Function
'
' What it does:
'   Finds, sizes, hides, or formats worksheet columns for BlendColors.
'
' Why it exists:
'   Consistent button shapes and macro assignments make the intake panel
'   repairable and easy for operators to use.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function BlendColors(ByVal baseColor As Long, ByVal accentColor As Long, ByVal accentWeight As Double) As Long
    Dim br As Long, bg As Long, bb As Long
    Dim ar As Long, ag As Long, ab As Long
    Dim rr As Long, rg As Long, rb As Long

    If accentWeight < 0 Then accentWeight = 0
    If accentWeight > 1 Then accentWeight = 1

    br = baseColor And &HFF
    bg = (baseColor \ &H100) And &HFF
    bb = (baseColor \ &H10000) And &HFF

    ar = accentColor And &HFF
    ag = (accentColor \ &H100) And &HFF
    ab = (accentColor \ &H10000) And &HFF

    rr = CLng((br * (1 - accentWeight)) + (ar * accentWeight))
    rg = CLng((bg * (1 - accentWeight)) + (ag * accentWeight))
    rb = CLng((bb * (1 - accentWeight)) + (ab * accentWeight))

    BlendColors = RGB(rr, rg, rb)
End Function


