Attribute VB_Name = "TemplateImporter"
Option Explicit

'==============================================================================
' Module: TemplateImporter
' Workbook: Multi User Scanner Queue Testing.xlsm / Master Delivery List
'
' What this module does:
'   Large master workbook utility module for importing/updating delivery
'   lists, rebuilding scanner sheets, print/export flows, utility panel
'   buttons, and delivery row formatting.
'
' Why this module exists:
'   The master workbook uses this module to turn a raw delivery list into the
'   operational sheets used by scanning, printing, exports, and intake
'   snapshots.
'
' Commenting standard used in this rewrite:
'   Procedure comments explain both what the code does and why that
'   behavior matters in the scanning / SharePoint / Power Automate workflow.
'   The code logic and public signatures are intentionally kept stable; this
'   pass is primarily a readability, maintainability, and safety pass.
'==============================================================================



'========================
'TemplateImporter (Code)
'========================
Private mPrevCalc As XlCalculation
Private mPrevScreenUpdating As Boolean
Private mPrevEnableEvents As Boolean
Private mPrevDisplayAlerts As Boolean
Private mPrevStatusBar As Variant
Private mPrevCursor As XlMousePointer
Public Const DEFAULT_RECEIVE_DEST As String = "Indian Trail"
Private Const RECEIVE_DEST_NAME As String = "_ReceiveDestination"
Private Const DESTINATION_DROPDOWN_CELL As String = "K25"
Private Const DESTINATION_LIST As String = "Indian Trail"

Private Const DESTINATION_DROPDOWN_NAME As String = "ddlDestinationSelector"
Private Const DESTINATION_SELECTOR_ANCHOR As String = "H25:K25"
Private Const DESTINATION_HELPER_COLS As String = "Z:AA"
Private Const DESTINATION_INDEX_CELL As String = "AA1"
Private Const DESTINATION_SELECTOR_SHELL As String = "shpDestinationSelectorShell"
Private Const UPDATE_COMPLETE_NOTICE_KEY As String = "UPDATE_COMPLETE_NOTICE_V1"

Private Const GREENVILLE_RECV_SHEET_NAME As String = "Inbound - Greenville"
Private Const GREENVILLE_CUSTOMER_TEXT As String = "BFS East Greenville SC MW"
Private Const CPU_SHEET_NAME As String = "Customer Pickup"
Private Const CPU_ROUTE_TEXT As String = "CPU"
Private Const PRINT_HELPER_SECTION_COL As Long = 40   'AN
Private Const PRINT_HELPER_ROWTYPE_COL As Long = 41   'AO
Private Const FIRST_DATA_ROW_FIXED As Long = 6
Private Const REMAKE_MARKER_TEXT As String = "RM"
Private Const REMAKE_PRINT_TEMPLATE_SHEET As String = "__REMAKE_PRINT_TEMPLATE__"
Private Const REMAKE_PRINT_PREVIEW_SHEET As String = "__REMAKE_PRINT_PREVIEW__"
Private Const REMAKE_TITLE_PREFIX As String = "                 REMAKES DUE: "
Private Const REMAKE_MARKER_COL_FIXED As Long = 11   'Column K
Private Const ROUTE_COL_FIXED As Long = 12           'Column L
Private Const PROCESS_STATE_COL_FIXED As Long = 13   'Column M


Private Const LEGACY_ROUTE_COL_FIXED As Long = 13    'Old source Route in M
Private Const LEGACY_REMAKE_MARKER_COL_FIXED As Long = 14   'Old RM marker in N

Private Const KNOWN_SRC_JOB_START_COL As Long = 1      'A
Private Const KNOWN_SRC_JOB_END_COL As Long = 3        'C
Private Const KNOWN_SRC_ORDER_COL As Long = 6          'F
Private Const KNOWN_SRC_ITEM_START_COL As Long = 7     'G
Private Const KNOWN_SRC_ITEM_END_COL As Long = 8       'H
Private Const KNOWN_SRC_QTY_START_COL As Long = 10     'J
Private Const KNOWN_SRC_QTY_END_COL As Long = 11       'K
Private Const KNOWN_SRC_DIM_START_COL As Long = 12     'L
Private Const KNOWN_SRC_DIM_END_COL As Long = 13       'M
Private Const KNOWN_SRC_CUST_START_COL As Long = 14    'N
Private Const KNOWN_SRC_CUST_END_COL As Long = 21      'U
Private Const KNOWN_SRC_REMAKE_COL As Long = 22        'V
Private Const KNOWN_SRC_ROUTE_COL As Long = 24         'X

Private Type SourceLayoutProfile
    headerRow As Long
    firstDataRow As Long
    JobStartCol As Long
    JobEndCol As Long
    orderCol As Long
    ItemStartCol As Long
    ItemEndCol As Long
    QtyStartCol As Long
    QtyEndCol As Long
    DimStartCol As Long
    DimEndCol As Long
    CustStartCol As Long
    CustEndCol As Long
    RemakeCol As Long
    routeCol As Long
    IsValid As Boolean
End Type

Private Const CLR_IMP_GVL_FILL As Long = 16116705    'RGB(221,235,247)
Private Const CLR_IMP_GVL_FONT As Long = 7942893     'RGB(31,78,121)

Private Const CLR_IMP_CPU_FILL As Long = 11195640    'RGB(248,214,170)
Private Const CLR_IMP_CPU_FONT As Long = 1856637     'RGB(125,68,28)

Private Const CLR_IMP_BOTH_FILL As Long = 14808319   'RGB(223,242,241)
Private Const CLR_IMP_BOTH_FONT As Long = 3874874    'RGB(58,93,90)

Private Const CLR_ADD_STD_FILL As Long = 15654365    'RGB(221,217,238)
Private Const CLR_ADD_STD_FONT As Long = 6291520     'RGB(64,0,96)

Private Const CLR_ADD_GVL_FILL As Long = 14277081    'RGB(201,218,248)
Private Const CLR_ADD_GVL_FONT As Long = 6956073     'RGB(41,73,125)

Private Const CLR_ADD_CPU_FILL As Long = 10854484    'RGB(212,190,165)
Private Const CLR_ADD_CPU_FONT As Long = 2047263     'RGB(95,61,31)

Private Const CLR_ADD_BOTH_FILL As Long = 13429727   'RGB(191,230,223)
Private Const CLR_ADD_BOTH_FONT As Long = 3283213    'RGB(45,59,50)

Private Const CLR_ADD_RM_FILL As Long = 14737632     'RGB(224,195,195)
Private Const CLR_ADD_RM_FONT As Long = 3932160      'RGB(96,0,0)

'========================
' SLEEK LIGHT THEME (no images)
'========================
' Font families
Private Const FONT_BASE As String = "Calibri"
Private Const FONT_ICON As String = "Segoe Fluent Icons, Segoe MDL2 Assets"

'Legacy utility-panel aliases used by older button helper code.
Private Const UP_FONT_BASE As String = "Calibri"
Private Const UP_FONT_ICON As String = "Segoe Fluent Icons, Segoe MDL2 Assets"

' Light background (subtle blue-gray, *not* white)
Private Const THEME_BG_R As Long = 190
Private Const THEME_BG_G As Long = 204
Private Const THEME_BG_B As Long = 221

' Card panels (soft)
Private Const CARD_BG_R As Long = 180
Private Const CARD_BG_G As Long = 194
Private Const CARD_BG_B As Long = 211
Private Const CARD_BORDER_R As Long = 160
Private Const CARD_BORDER_G As Long = 174
Private Const CARD_BORDER_B As Long = 191

' Section header strip (dark slate)
Private Const HEADER_BG_R As Long = 59
Private Const HEADER_BG_G As Long = 74
Private Const HEADER_BG_B As Long = 102
Private Const HEADER_TXT_R As Long = 255
Private Const HEADER_TXT_G As Long = 255
Private Const HEADER_TXT_B As Long = 255

' Info bar text color
Private Const INFO_BG_R As Long = 80
Private Const INFO_BG_G As Long = 100
Private Const INFO_BG_B As Long = 138
Private Const INFO_TXT_R As Long = 255
Private Const INFO_TXT_G As Long = 255
Private Const INFO_TXT_B As Long = 255

' One consistent button color (professional steel blue)
Private Const BTN_PRIMARY_R As Long = 47
Private Const BTN_PRIMARY_G As Long = 75
Private Const BTN_PRIMARY_B As Long = 117
Private Const BTN_TXT_R As Long = 255
Private Const BTN_TXT_G As Long = 255
Private Const BTN_TXT_B As Long = 255



'=== MDL2 glyph codepoints (hex without spaces) ===
Private Const CP_IMPORT  As Long = &HE118
Private Const CP_UPDATE  As Long = &HE72C
Private Const CP_PRINT   As Long = &HE749
Private Const CP_EXPORT  As Long = &HE74E
Private Const CP_LIST    As Long = &HE14C
Private Const CP_EDIT    As Long = &HE70F

'=== New glyph choices (hex, no spaces) ===
' Up arrow (nice for Export/Upload)
Private Const CP_UP_ARROW     As Long = &HE74A   ' Up

' Share (clean metaphor for "Save SharePoint Copy")
Private Const CP_SHARE        As Long = &HE72D   ' Share

' Alternative to "refresh" for Update Existing List
Private Const CP_UPDATE_ALT   As Long = &HE777   ' UpdateRestore

' Solid input metaphor for Manual Scan (keyboard)
Private Const CP_KEYBOARD     As Long = &HE765   ' KeyboardClassic
' (Alternative: numeric keypad/dial pad if you prefer)
Private Const CP_DIALPAD      As Long = &HE75F   ' Dialpad





'========================
' Diagonal gradient + in-fill accent (no overlay)
'========================
' Two-color base gradient direction:
' 1=Horizontal, 2=Vertical, 3=DiagonalUp, 4=DiagonalDown (top-left?bottom-right)
Private Const BTN_GRADIENT_STYLE   As Long = 3

' Mid-tone lightening for the diagonal (0..1)
Private Const BTN_GRADIENT_LIGHTEN As Double = 0.16

' Where the accent stop sits in the gradient (0..1) â nearer 1.0 = closer to bottom-right
Private Const BTN_ACCENT_POS       As Double = 0.99
' Where the mid stop sits (0..1)
Private Const BTN_MID_POS          As Double = 0.7

' Bottom-right accent color (kept subtle so we donât go ârainbowâ)
Private Const BTN_ACCENT_R As Long = 20
Private Const BTN_ACCENT_G As Long = 255
Private Const BTN_ACCENT_B As Long = 15



' Small type for theme
Private Type BtnTheme
    Fill As Long
    Font As Long
End Type

'------------------------------------------------------------------------------
' Procedure: LightenColor
' Scope: Private Function
'
' What it does:
'   Finds, sizes, hides, formats, or uses worksheet columns for LightenColor.
'
' Why it exists:
'   The system depends on fixed scan blocks and discovered delivery-list
'   columns, so column handling must be centralized and predictable.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function LightenColor(ByVal rgbColor As Long, ByVal amount As Double) As Long
    Dim r As Long, g As Long, b As Long
    r = (rgbColor And &HFF)
    g = (rgbColor \ &H100) And &HFF
    b = (rgbColor \ &H10000) And &HFF
    r = CLng(r + (255 - r) * amount)
    g = CLng(g + (255 - g) * amount)
    b = CLng(b + (255 - b) * amount)
    LightenColor = RGB(r, g, b)
End Function

'------------------------------------------------------------------------------
' Procedure: AccentColor
' Scope: Private Function
'
' What it does:
'   Finds, sizes, hides, formats, or uses worksheet columns for AccentColor.
'
' Why it exists:
'   The system depends on fixed scan blocks and discovered delivery-list
'   columns, so column handling must be centralized and predictable.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function AccentColor() As Long
    AccentColor = RGB(BTN_ACCENT_R, BTN_ACCENT_G, BTN_ACCENT_B)
End Function


' Convert codepoint to the glyph character at runtime

'------------------------------------------------------------------------------
' Procedure: GlyphFromCP
' Scope: Private Function
'
' What it does:
'   Performs the workbook-specific step named GlyphFromCP inside
'   TemplateImporter.
'
' Why it exists:
'   The master workbook uses this module to turn a raw delivery list into the
'   operational sheets used by scanning, printing, exports, and intake
'   snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GlyphFromCP(ByVal cp As Long) As String
    GlyphFromCP = ChrW$(cp)
End Function

'------------------------------------------------------------------------------
' Procedure: Rgb3
' Scope: Private Function
'
' What it does:
'   Performs the workbook-specific step named Rgb3 inside TemplateImporter.
'
' Why it exists:
'   The master workbook uses this module to turn a raw delivery list into the
'   operational sheets used by scanning, printing, exports, and intake
'   snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function Rgb3(ByVal r As Long, ByVal g As Long, ByVal b As Long) As Long
    Rgb3 = RGB(r, g, b)
End Function

'------------------------------------------------------------------------------
' Procedure: ThemePrimary
' Scope: Private Function
'
' What it does:
'   Performs the workbook-specific step named ThemePrimary inside
'   TemplateImporter.
'
' Why it exists:
'   The master workbook uses this module to turn a raw delivery list into the
'   operational sheets used by scanning, printing, exports, and intake
'   snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function ThemePrimary() As BtnTheme
    Dim t As BtnTheme
    t.Fill = Rgb3(BTN_PRIMARY_R, BTN_PRIMARY_G, BTN_PRIMARY_B)
    t.Font = Rgb3(BTN_TXT_R, BTN_TXT_G, BTN_TXT_B)
    ThemePrimary = t
End Function

'------------------------------------------------------------------------------
' Procedure: FitIn
' Scope: Private Function
'
' What it does:
'   Performs the workbook-specific step named FitIn inside TemplateImporter.
'
' Why it exists:
'   The master workbook uses this module to turn a raw delivery list into the
'   operational sheets used by scanning, printing, exports, and intake
'   snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function FitIn(ByVal slot As Double, ByVal target As Double, ByVal minV As Double) As Double
    Dim v As Double: v = target
    If v > slot Then v = slot
    If v < minV Then v = minV
    FitIn = v
End Function
'========================
' SINGLE BUTTON (centered text) + ICON OVERLAY (left inside)
' with roomier height + tighter margins for two-line label
'========================

'------------------------------------------------------------------------------
' Procedure: AddIconButton
' Scope: Private Sub
'
' What it does:
'   Builds, formats, deletes, or wires workbook UI shapes/buttons/panels for
'   AddIconButton.
'
' Why it exists:
'   Buttons and utility panels are the operator-facing control surface, so
'   they must be rebuilt consistently after imports or sheet refreshes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub AddIconButton( _
    ByVal ws As Worksheet, ByVal anchorRangeAddress As String, _
    ByVal shapeName As String, ByVal glyph As String, _
    ByVal titleText As String, ByVal descText As String, _
    ByVal macroName As String, ByRef theme As BtnTheme, _
    Optional ByVal accentRGB As Long = -1)

    Dim r As Range: Set r = ws.Range(anchorRangeAddress)
    Dim btn As Shape, ico As Shape
    Dim leftPos As Double, topPos As Double, btnW As Double, btnH As Double
    Dim basePad As Double, iconPad As Double, iconW As Double, textMargin As Double
    Dim label As String

    ' Clean any previous shapes with same logical names
   On Error Resume Next
    ws.Shapes(shapeName).Delete
    ws.Shapes(shapeName & "_ico").Delete
    On Error GoTo 0
    
    

    ' Target sizes (slightly larger for 2 lines)
    btnW = FitIn(r.Width, 286, 150)
    btnH = FitIn(r.Height, 64, 44)          ' ? taller than before
    leftPos = r.Left + (r.Width - btnW) / 2
    topPos = r.Top + (r.Height - btnH) / 2

    ' Icon sizing/placement
    basePad = 6
    iconPad = 8
    iconW = btnH * 0.55                      ' a hair smaller than before
    textMargin = iconPad + iconW + 6         ' equal L/R margins so text stays centered

    label = titleText & vbLf & descText

    ' --- Main button shape (centered text) ---
    Set btn = ws.Shapes.AddShape(msoShapeRoundedRectangle, leftPos, topPos, btnW, btnH)
    With btn
        .Name = shapeName
        .OnAction = "'" & ThisWorkbook.Name & "'!" & macroName

        
'========================
' Diagonal gradient with in-fill accent (keeps main color the same; only end color varies)
'========================
Dim f As Object, gs As Object, acc As Long

' Use per-button accent if provided; otherwise fall back to global AccentColor()
If accentRGB = -1 Then acc = AccentColor() Else acc = accentRGB

' 1) Portable two-color gradient (works on every build)
With .Fill
    .Visible = msoTrue
    .TwoColorGradient BTN_GRADIENT_STYLE, 1
    .foreColor.RGB = theme.Fill                                   ' start color (main button color)
    ' If caller provided an accent, use it as the end color even when GradientStops aren't available
    If accentRGB = -1 Then
        .backColor.RGB = LightenColor(theme.Fill, BTN_GRADIENT_LIGHTEN)
    Else
        .backColor.RGB = acc
    End If
End With

' 2) If GradientStops are available, shape a 3-stop gradient ending at our accent color
On Error Resume Next
Set f = btn.Fill
Set gs = CallByName(f, "GradientStops", VbGet)  ' late-bound for compatibility
If Err.Number = 0 And Not gs Is Nothing Then
    CallByName gs, "Clear", VbMethod
    CallByName gs, "Insert", VbMethod, theme.Fill, 0, 0
    CallByName gs, "Insert", VbMethod, LightenColor(theme.Fill, BTN_GRADIENT_LIGHTEN), BTN_MID_POS, 0
    CallByName gs, "Insert", VbMethod, acc, BTN_ACCENT_POS, 0
End If
Err.Clear
On Error GoTo 0

' 3) Border stays the same
.Line.Visible = msoTrue
.Line.foreColor.RGB = RGB(255, 255, 255)
.Line.Transparency = 0.7
.Line.Weight = 0.9         ' <-- Button border thickness (see Section C)

        ' Center the text; equal margins leave room for icon on the left
        With .TextFrame2
            .VerticalAnchor = msoAnchorMiddle
            .WordWrap = msoTrue
            .MarginLeft = textMargin
            .MarginRight = textMargin
            .MarginTop = 3: .MarginBottom = 3
            .TextRange.Text = label
            .TextRange.ParagraphFormat.Alignment = msoAlignCenter
            With .TextRange.Font
                .Name = FONT_BASE
                .Size = 12                    ' title size
                .Bold = msoTrue
                .Fill.foreColor.RGB = theme.Font
            End With
        End With

        ' Make the description smaller & lighter so it fits
        On Error Resume Next
        Dim titleLen As Long: titleLen = Len(titleText)
        Dim totalLen As Long: totalLen = Len(label)
        If totalLen > titleLen + 1 Then
            With .TextFrame.Characters(titleLen + 2, totalLen - (titleLen + 1)).Font
                .Name = FONT_BASE
                .Size = 9                      ' ? slightly smaller than before
                .Bold = False
                .Color = RGB(238, 242, 248)    ' light for readability on blue
            End With
        End If
        On Error GoTo 0
    End With

    ' --- Icon shape: left-inside overlay (no border, no fill) ---
    Dim iconLeft As Double, iconTop As Double
    iconLeft = leftPos + iconPad
    iconTop = topPos + (btnH - iconW) / 2

    Set ico = ws.Shapes.AddShape(msoShapeRectangle, iconLeft, iconTop, iconW, iconW)
    With ico
        .Name = shapeName & "_ico"
        .OnAction = "'" & ThisWorkbook.Name & "'!" & macroName
        .Fill.Visible = msoFalse
        .Line.Visible = msoFalse

        With .TextFrame2
            .VerticalAnchor = msoAnchorMiddle
            .WordWrap = msoFalse
            .MarginLeft = 0: .MarginRight = 0
            .MarginTop = 0: .MarginBottom = 0
            .TextRange.Text = glyph
            .TextRange.ParagraphFormat.Alignment = msoAlignCenter
            With .TextRange.Font
                .Name = FONT_ICON
                .Size = iconW * 0.8
                .Bold = msoTrue
                .Fill.foreColor.RGB = theme.Font   ' white
            End With
        End With

        On Error Resume Next
        .ZOrder msoBringToFront
        On Error GoTo 0
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: CPUSheetExistsTemplate
' Scope: Private Function
'
' What it does:
'   Identifies, filters, formats, or routes Customer Pickup rows for
'   CPUSheetExistsTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function CPUSheetExistsTemplate() As Boolean
    Dim ws As Worksheet

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(CPU_SHEET_NAME)
    On Error GoTo 0

    CPUSheetExistsTemplate = Not ws Is Nothing
End Function

'------------------------------------------------------------------------------
' Procedure: GetRouteColumnTemplate
' Scope: Private Function
'
' What it does:
'   Finds, sizes, hides, formats, or uses worksheet columns for
'   GetRouteColumnTemplate.
'
' Why it exists:
'   The system depends on fixed scan blocks and discovered delivery-list
'   columns, so column handling must be centralized and predictable.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetRouteColumnTemplate(ByVal ws As Worksheet) As Long
    GetRouteColumnTemplate = ROUTE_COL_FIXED
End Function

'------------------------------------------------------------------------------
' Procedure: IsCPURowTemplate
' Scope: Private Function
'
' What it does:
'   Identifies, filters, formats, or routes Customer Pickup rows for
'   IsCPURowTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function IsCPURowTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, Optional ByVal routeCol As Long = 0) As Boolean
    Dim routeText As String

    If rowNum < FIRST_DATA_ROW_FIXED Then Exit Function

    routeText = CStr(ws.Cells(rowNum, ROUTE_COL_FIXED).Value)
    routeText = Replace$(routeText, Chr$(160), " ")
    routeText = Application.WorksheetFunction.Clean(routeText)
    routeText = Application.WorksheetFunction.Trim(routeText)
    routeText = UCase$(routeText)

    IsCPURowTemplate = (routeText = UCase$(CPU_ROUTE_TEXT))
End Function

'------------------------------------------------------------------------------
' Procedure: HasCPUOrdersTemplate
' Scope: Private Function
'
' What it does:
'   Identifies, filters, formats, or routes Customer Pickup rows for
'   HasCPUOrdersTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function HasCPUOrdersTemplate(ByVal ws As Worksheet) As Boolean
    Dim lastRow As Long
    Dim r As Long

    lastRow = ws.Cells(ws.rows.Count, ROUTE_COL_FIXED).End(xlUp).Row
    If lastRow < FIRST_DATA_ROW_FIXED Then Exit Function

    For r = FIRST_DATA_ROW_FIXED To lastRow
        If IsCPURowTemplate(ws, r) Then
            HasCPUOrdersTemplate = True
            Exit Function
        End If
    Next r
End Function

'------------------------------------------------------------------------------
' Procedure: RebuildAllScannerSheetsFromMain
' Scope: Private Sub
'
' What it does:
'   Finds, creates, deletes, rebuilds, protects, or synchronizes worksheets
'   for RebuildAllScannerSheetsFromMain.
'
' Why it exists:
'   The master workbook creates multiple operational views from one delivery
'   list; worksheet helpers keep those views from drifting apart.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub RebuildAllScannerSheetsFromMain(ByVal dataWs As Worksheet)
    RebuildScannerSheetFromMain dataWs, "Staging - Airport Rd", "STAGING"
    CopyDeliveryListLogoToSheetTemplate dataWs, ThisWorkbook.Worksheets("Staging - Airport Rd")

    RebuildScannerSheetFromMain dataWs, "Outbound - Airport Rd", "SEND"
    CopyDeliveryListLogoToSheetTemplate dataWs, ThisWorkbook.Worksheets("Outbound - Airport Rd")

    RebuildScannerSheetFromMain dataWs, GetReceiveSheetName(), "RECV"
    CopyDeliveryListLogoToSheetTemplate dataWs, ThisWorkbook.Worksheets(GetReceiveSheetName())

    If HasGreenvilleOrdersTemplate(dataWs) Then
        RebuildScannerSheetFromMain dataWs, GREENVILLE_RECV_SHEET_NAME, "RECV"
        CopyDeliveryListLogoToSheetTemplate dataWs, ThisWorkbook.Worksheets(GREENVILLE_RECV_SHEET_NAME)
    Else
        DeleteSheetIfExists ThisWorkbook, GREENVILLE_RECV_SHEET_NAME
    End If

    If HasCPUOrdersTemplate(dataWs) Then
        RebuildScannerSheetFromMain dataWs, CPU_SHEET_NAME, "RECV"
        CopyDeliveryListLogoToSheetTemplate dataWs, ThisWorkbook.Worksheets(CPU_SHEET_NAME)
    Else
        DeleteSheetIfExists ThisWorkbook, CPU_SHEET_NAME
    End If

    ApplyOperationalTabColorsTemplate
End Sub

'------------------------------------------------------------------------------
' Procedure: GetHighlightStoreNameTemplate
' Scope: Private Function
'
' What it does:
'   Applies, stores, restores, or clears scan/manual highlight state for
'   GetHighlightStoreNameTemplate.
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
Private Function GetHighlightStoreNameTemplate(ByVal ws As Worksheet) As String
    Dim nm As String

    If ws Is Nothing Then Exit Function

    nm = UCase$(ws.Name)
    nm = Replace$(nm, " ", "_")
    nm = Replace$(nm, "-", "_")
    nm = Replace$(nm, ".", "_")
    nm = Replace$(nm, "&", "_")

    GetHighlightStoreNameTemplate = "_LastScanHighlight_" & nm
End Function

'------------------------------------------------------------------------------
' Procedure: ClearStoredScanHighlightTemplate
' Scope: Private Sub
'
' What it does:
'   Applies, stores, restores, or clears scan/manual highlight state for
'   ClearStoredScanHighlightTemplate.
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
Private Sub ClearStoredScanHighlightTemplate(ByVal ws As Worksheet)
    Dim nm As String
    Dim lastRow As Long
    Dim r As Long

    If ws Is Nothing Then Exit Sub

    nm = GetHighlightStoreNameTemplate(ws)

    On Error Resume Next
    ThisWorkbook.names(nm).Delete
    On Error GoTo 0

    lastRow = ws.Cells(ws.rows.Count, 1).End(xlUp).Row
    If lastRow < 1 Then Exit Sub

    For r = 1 To lastRow
        If ws.Cells(r, 1).Interior.Color = RGB(255, 255, 153) Then
            ws.Range(ws.Cells(r, 1), ws.Cells(r, 10)).Interior.Pattern = xlNone
        End If
    Next r
End Sub

'------------------------------------------------------------------------------
' Procedure: ClearAllStoredScanHighlightsTemplate
' Scope: Private Sub
'
' What it does:
'   Applies, stores, restores, or clears scan/manual highlight state for
'   ClearAllStoredScanHighlightsTemplate.
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
Private Sub ClearAllStoredScanHighlightsTemplate()
    On Error Resume Next

    ClearStoredScanHighlightTemplate ThisWorkbook.Worksheets("Delivery List")
    ClearStoredScanHighlightTemplate ThisWorkbook.Worksheets("Staging - Airport Rd")
    ClearStoredScanHighlightTemplate ThisWorkbook.Worksheets("Outbound - Airport Rd")
    ClearStoredScanHighlightTemplate ThisWorkbook.Worksheets(GetReceiveSheetName())

    If SheetExistsTemplate(GREENVILLE_RECV_SHEET_NAME) Then
        ClearStoredScanHighlightTemplate ThisWorkbook.Worksheets(GREENVILLE_RECV_SHEET_NAME)
    End If

    If SheetExistsTemplate(CPU_SHEET_NAME) Then
        ClearStoredScanHighlightTemplate ThisWorkbook.Worksheets(CPU_SHEET_NAME)
    End If

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: SheetExistsTemplate
' Scope: Private Function
'
' What it does:
'   Finds, creates, deletes, rebuilds, protects, or synchronizes worksheets
'   for SheetExistsTemplate.
'
' Why it exists:
'   The master workbook creates multiple operational views from one delivery
'   list; worksheet helpers keep those views from drifting apart.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SheetExistsTemplate(ByVal sheetName As String) As Boolean
    Dim ws As Worksheet

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(sheetName)
    On Error GoTo 0

    SheetExistsTemplate = Not ws Is Nothing
End Function

'------------------------------------------------------------------------------
' Procedure: SetSheetTabColorTemplate
' Scope: Private Sub
'
' What it does:
'   Finds, sizes, hides, formats, or uses worksheet columns for
'   SetSheetTabColorTemplate.
'
' Why it exists:
'   The system depends on fixed scan blocks and discovered delivery-list
'   columns, so column handling must be centralized and predictable.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub SetSheetTabColorTemplate(ByVal sheetName As String, ByVal tabColor As Long)
    Dim ws As Worksheet

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(sheetName)
    On Error GoTo 0

    If ws Is Nothing Then Exit Sub
    ws.Tab.Color = tabColor
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplyOperationalTabColorsTemplate
' Scope: Private Sub
'
' What it does:
'   Finds, sizes, hides, formats, or uses worksheet columns for
'   ApplyOperationalTabColorsTemplate.
'
' Why it exists:
'   The system depends on fixed scan blocks and discovered delivery-list
'   columns, so column handling must be centralized and predictable.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ApplyOperationalTabColorsTemplate()
    'Staging = gray
    SetSheetTabColorTemplate "Staging - Airport Rd", RGB(127, 127, 127)

    'Outbound = blue
    SetSheetTabColorTemplate "Outbound - Airport Rd", RGB(47, 75, 117)

    'Current main inbound (Indian Trail) = green
    SetSheetTabColorTemplate GetReceiveSheetName(), RGB(70, 140, 95)

    'Greenville = turquoise
    SetSheetTabColorTemplate GREENVILLE_RECV_SHEET_NAME, RGB(64, 181, 173)

    'Customer Pickup = orange
    SetSheetTabColorTemplate CPU_SHEET_NAME, RGB(230, 145, 56)
End Sub

'------------------------------------------------------------------------------
' Procedure: FindDeliveryListLogoShapeTemplate
' Scope: Private Function
'
' What it does:
'   Builds, formats, deletes, or wires workbook UI shapes/buttons/panels for
'   FindDeliveryListLogoShapeTemplate.
'
' Why it exists:
'   Buttons and utility panels are the operator-facing control surface, so
'   they must be rebuilt consistently after imports or sheet refreshes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function FindDeliveryListLogoShapeTemplate(ByVal ws As Worksheet) As Shape
    Dim shp As Shape
    Dim bestShp As Shape
    Dim topLimit As Double
    Dim leftLimit As Double
    Dim bestScore As Double
    Dim score As Double
    Dim nm As String

    If ws Is Nothing Then Exit Function

    topLimit = ws.rows(6).Top
    leftLimit = ws.Columns("N").Left
    bestScore = 10 ^ 30

    For Each shp In ws.Shapes
        nm = LCase$(shp.Name)

        'Prefer any top-of-sheet shape explicitly named like a logo
        If InStr(1, nm, "logo", vbTextCompare) > 0 Then
            If shp.Top < topLimit Then
                Set FindDeliveryListLogoShapeTemplate = shp
                Exit Function
            End If
        End If

        'Fallback: first picture/group in the top-left header area
        Select Case shp.Type
            Case msoPicture, msoLinkedPicture, msoGroup
                If shp.Top < topLimit And shp.Left < leftLimit Then
                    score = shp.Top + shp.Left
                    If bestShp Is Nothing Or score < bestScore Then
                        Set bestShp = shp
                        bestScore = score
                    End If
                End If
        End Select
    Next shp

    If Not bestShp Is Nothing Then
        Set FindDeliveryListLogoShapeTemplate = bestShp
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: RemoveCopiedDeliveryListLogoTemplate
' Scope: Private Sub
'
' What it does:
'   Finds, copies, removes, or positions the delivery-list logo for
'   RemoveCopiedDeliveryListLogoTemplate.
'
' Why it exists:
'   Rebuilt scanner and print-preview sheets should retain the familiar
'   delivery-list branding without duplicating stale logo shapes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub RemoveCopiedDeliveryListLogoTemplate(ByVal ws As Worksheet)
    Dim shp As Shape

    If ws Is Nothing Then Exit Sub

    On Error Resume Next
    For Each shp In ws.Shapes
        If LCase$(Left$(shp.Name, 13)) = "dlsharedlogo_" Then
            shp.Delete
        End If
    Next shp
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: CopyDeliveryListLogoToSheetTemplate
' Scope: Public Sub
'
' What it does:
'   Finds, copies, removes, or positions the delivery-list logo for
'   CopyDeliveryListLogoToSheetTemplate.
'
' Why it exists:
'   Rebuilt scanner and print-preview sheets should retain the familiar
'   delivery-list branding without duplicating stale logo shapes.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub CopyDeliveryListLogoToSheetTemplate(ByVal srcWs As Worksheet, ByVal destWs As Worksheet)
    Dim srcLogo As Shape
    Dim newShp As Shape
    Dim safeName As String

    If srcWs Is Nothing Or destWs Is Nothing Then Exit Sub
    If UCase$(srcWs.Name) = UCase$(destWs.Name) Then Exit Sub

    Set srcLogo = FindDeliveryListLogoShapeTemplate(srcWs)

    RemoveCopiedDeliveryListLogoTemplate destWs

    If srcLogo Is Nothing Then Exit Sub

    On Error Resume Next
    srcLogo.Copy
    destWs.Paste
    Set newShp = destWs.Shapes(destWs.Shapes.Count)
    On Error GoTo 0

    If newShp Is Nothing Then Exit Sub

    safeName = Replace$(destWs.Name, " ", "_")
    safeName = Replace$(safeName, "-", "_")

    With newShp
        .Name = "dlSharedLogo_" & safeName
        .Left = srcLogo.Left
        .Top = srcLogo.Top
        .Width = srcLogo.Width
        .Height = srcLogo.Height
        .Placement = xlFreeFloating
        .Locked = True
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: GreenvilleSheetExistsTemplate
' Scope: Private Function
'
' What it does:
'   Identifies, filters, formats, or routes Greenville-specific delivery rows
'   for GreenvilleSheetExistsTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GreenvilleSheetExistsTemplate() As Boolean
    Dim ws As Worksheet

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets("Inbound - Greenville")
    On Error GoTo 0

    GreenvilleSheetExistsTemplate = Not ws Is Nothing
End Function

'------------------------------------------------------------------------------
' Procedure: EnsureReceiveDestinationName
' Scope: Public Sub
'
' What it does:
'   Verifies that required workbook objects, sheets, layout, names, or
'   settings exist for EnsureReceiveDestinationName.
'
' Why it exists:
'   Many operations assume these supporting objects already exist; ensuring
'   them first prevents runtime failures after imports or workbook copies.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub EnsureReceiveDestinationName()
    If Len(GetReceiveDestinationName()) = 0 Then
        SaveReceiveSheetName DEFAULT_RECEIVE_DEST
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: GetReceiveDestinationName
' Scope: Public Function
'
' What it does:
'   Returns a workbook object, setting, status value, parsed value, or
'   calculated result used by other procedures (GetReceiveDestinationName).
'
' Why it exists:
'   Using one getter keeps callers from duplicating lookup logic and protects
'   them from missing sheets, missing names, or blank values.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function GetReceiveDestinationName() As String
    Dim s As String

    On Error Resume Next
    s = ThisWorkbook.names(RECEIVE_DEST_NAME).RefersTo
    On Error GoTo 0

    s = Replace$(s, "=", "")
    s = Replace$(s, """", "")
    s = Trim$(s)

    If Len(s) = 0 Then s = DEFAULT_RECEIVE_DEST
    GetReceiveDestinationName = s
End Function

'------------------------------------------------------------------------------
' Procedure: GetReceiveSheetName
' Scope: Public Function
'
' What it does:
'   Finds, creates, deletes, rebuilds, protects, or synchronizes worksheets
'   for GetReceiveSheetName.
'
' Why it exists:
'   The master workbook creates multiple operational views from one delivery
'   list; worksheet helpers keep those views from drifting apart.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function GetReceiveSheetName() As String
    GetReceiveSheetName = "Inbound - " & GetReceiveDestinationName()
End Function

'------------------------------------------------------------------------------
' Procedure: GetReceiveSheet
' Scope: Public Function
'
' What it does:
'   Finds, creates, deletes, rebuilds, protects, or synchronizes worksheets
'   for GetReceiveSheet.
'
' Why it exists:
'   The master workbook creates multiple operational views from one delivery
'   list; worksheet helpers keep those views from drifting apart.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function GetReceiveSheet() As Worksheet
    Dim ws As Worksheet
    Dim nm As String

    nm = GetReceiveSheetName()

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(nm)
    On Error GoTo 0

    Set GetReceiveSheet = ws
End Function

'------------------------------------------------------------------------------
' Procedure: SaveReceiveSheetName
' Scope: Private Sub
'
' What it does:
'   Finds, creates, deletes, rebuilds, protects, or synchronizes worksheets
'   for SaveReceiveSheetName.
'
' Why it exists:
'   The master workbook creates multiple operational views from one delivery
'   list; worksheet helpers keep those views from drifting apart.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub SaveReceiveSheetName(ByVal destName As String)
    On Error Resume Next
    ThisWorkbook.names(RECEIVE_DEST_NAME).Delete
    On Error GoTo 0

    ThisWorkbook.names.Add Name:=RECEIVE_DEST_NAME, RefersTo:="=""" & destName & """"
End Sub

'------------------------------------------------------------------------------
' Procedure: CleanSheetTabName
' Scope: Private Function
'
' What it does:
'   Finds, creates, deletes, rebuilds, protects, or synchronizes worksheets
'   for CleanSheetTabName.
'
' Why it exists:
'   The master workbook creates multiple operational views from one delivery
'   list; worksheet helpers keep those views from drifting apart.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function CleanSheetTabName(ByVal s As String) As String
    s = Trim$(s)
    s = Replace$(s, "/", "-")
    s = Replace$(s, "\", "-")
    s = Replace$(s, ":", "-")
    s = Replace$(s, "*", "")
    s = Replace$(s, "?", "")
    s = Replace$(s, "[", "(")
    s = Replace$(s, "]", ")")

    If Len(s) > 31 Then s = Left$(s, 31)
    CleanSheetTabName = Trim$(s)
End Function

'------------------------------------------------------------------------------
' Procedure: GetSelectedDestinationFromSelector
' Scope: Private Function
'
' What it does:
'   Returns a workbook object, setting, status value, parsed value, or
'   calculated result used by other procedures
'   (GetSelectedDestinationFromSelector).
'
' Why it exists:
'   Using one getter keeps callers from duplicating lookup logic and protects
'   them from missing sheets, missing names, or blank values.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetSelectedDestinationFromSelector(ByVal ws As Worksheet) As String
    Dim items As Variant
    Dim idx As Long

    items = Split(DESTINATION_LIST, ",")
    idx = CLng(Val(ws.Range(DESTINATION_INDEX_CELL).Value))

    If idx < 1 Or idx > UBound(items) - LBound(items) + 1 Then
        idx = 1
    End If

    GetSelectedDestinationFromSelector = Trim$(CStr(items(idx - 1 + LBound(items))))
End Function

'------------------------------------------------------------------------------
' Procedure: GetCustomerColumnTemplate
' Scope: Private Function
'
' What it does:
'   Finds, sizes, hides, formats, or uses worksheet columns for
'   GetCustomerColumnTemplate.
'
' Why it exists:
'   The system depends on fixed scan blocks and discovered delivery-list
'   columns, so column handling must be centralized and predictable.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetCustomerColumnTemplate(ByVal ws As Worksheet) As Long
    Dim hdr As Range
    Set hdr = FindHeaderCellTemplate(ws, Array("Customer"))
    If Not hdr Is Nothing Then GetCustomerColumnTemplate = hdr.Column
End Function

'------------------------------------------------------------------------------
' Procedure: IsGreenvilleRowTemplate
' Scope: Private Function
'
' What it does:
'   Identifies, filters, formats, or routes Greenville-specific delivery rows
'   for IsGreenvilleRowTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function IsGreenvilleRowTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, Optional ByVal customerCol As Long = 0) As Boolean
    If customerCol = 0 Then customerCol = GetCustomerColumnTemplate(ws)
    If customerCol = 0 Then Exit Function

    IsGreenvilleRowTemplate = (UCase$(Trim$(CStr(ws.Cells(rowNum, customerCol).Value))) = UCase$(GREENVILLE_CUSTOMER_TEXT))
End Function

'------------------------------------------------------------------------------
' Procedure: HasGreenvilleOrdersTemplate
' Scope: Private Function
'
' What it does:
'   Identifies, filters, formats, or routes Greenville-specific delivery rows
'   for HasGreenvilleOrdersTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function HasGreenvilleOrdersTemplate(ByVal ws As Worksheet) As Boolean
    Dim custCol As Long
    Dim orderHdr As Range
    Dim firstRow As Long, lastRow As Long
    Dim r As Long

    custCol = GetCustomerColumnTemplate(ws)
    Set orderHdr = FindHeaderCellTemplateInCols(ws, Array("Order Nr."), "A:N", 250)

    If custCol = 0 Or orderHdr Is Nothing Then Exit Function

    firstRow = orderHdr.Row + 1
    lastRow = ws.Cells(ws.rows.Count, orderHdr.Column).End(xlUp).Row

    For r = firstRow To lastRow
        If IsGreenvilleRowTemplate(ws, r, custCol) Then
            HasGreenvilleOrdersTemplate = True
            Exit Function
        End If
    Next r
End Function

'------------------------------------------------------------------------------
' Procedure: HasDeliveryProgressFillTemplate
' Scope: Private Function
'
' What it does:
'   Returns a True/False decision used by higher-level workflow code
'   (HasDeliveryProgressFillTemplate).
'
' Why it exists:
'   Boolean helpers make business rules readable and keep condition checks
'   consistent across modules.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function HasDeliveryProgressFillTemplate(ByVal rowBand As Range) As Boolean
    Dim clr As Long

    clr = rowBand.Cells(1, 1).Interior.Color

    HasDeliveryProgressFillTemplate = _
        (clr = RGB(235, 247, 228)) Or _
        (clr = RGB(255, 249, 230)) Or _
        (clr = RGB(255, 235, 235))
End Function

'------------------------------------------------------------------------------
' Procedure: HighlightGreenvilleRowsTemplate
' Scope: Private Sub
'
' What it does:
'   Applies, stores, restores, or clears scan/manual highlight state for
'   HighlightGreenvilleRowsTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub HighlightGreenvilleRowsTemplate(ByVal ws As Worksheet)
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim firstRow As Long
    Dim orderCol As Long
    Dim itemCol As Long
    Dim updatedKeys As Object

    Set orderHdr = FindHeaderCellTemplateInCols(ws, Array("Order Nr."), "A:N", 250)
    Set itemHdr = FindHeaderCellTemplateInCols(ws, Array("Item Nr.", "Item"), "A:N", 250)

    If orderHdr Is Nothing Or itemHdr Is Nothing Then Exit Sub

    firstRow = orderHdr.Row + 1
    orderCol = orderHdr.Column
    itemCol = itemHdr.Column

    'Preserve rows that are already marked as updated/new
    Set updatedKeys = BuildExistingUpdatedRowKeySetTemplate(ws, firstRow, orderCol, itemCol)

    ReapplyDeliveryListRowStylesTemplate ws, firstRow, orderCol, itemCol, Nothing, updatedKeys
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplyGreenvilleReceiveFilterTemplate
' Scope: Private Sub
'
' What it does:
'   Identifies, filters, formats, or routes Greenville-specific delivery rows
'   for ApplyGreenvilleReceiveFilterTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ApplyGreenvilleReceiveFilterTemplate(ByVal ws As Worksheet)
    Dim orderHdr As Range
    Dim custCol As Long
    Dim routeCol As Long
    Dim firstRow As Long, lastRow As Long
    Dim r As Long
    Dim isGreenville As Boolean
    Dim isCPU As Boolean

    If UCase$(ws.Name) <> UCase$(GREENVILLE_RECV_SHEET_NAME) And _
       UCase$(ws.Name) <> UCase$(GetReceiveSheetName()) And _
       UCase$(ws.Name) <> UCase$(CPU_SHEET_NAME) Then Exit Sub

    custCol = GetCustomerColumnTemplate(ws)
    routeCol = GetRouteColumnTemplate(ws)
    Set orderHdr = FindHeaderCellTemplateInCols(ws, Array("Order Nr."), "A:N", 250)

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
        ElseIf UCase$(ws.Name) = UCase$(GetReceiveSheetName()) Then
            .Value = GetReceiveSheetName()
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
        isCPU = IsCPURowTemplate(ws, r, routeCol)
        isGreenville = IsGreenvilleRowTemplate(ws, r, custCol)

        Select Case UCase$(ws.Name)
            Case UCase$(CPU_SHEET_NAME)
                ws.rows(r).Hidden = Not isCPU

            Case UCase$(GREENVILLE_RECV_SHEET_NAME)
                ws.rows(r).Hidden = (Not isGreenville) Or isCPU

            Case UCase$(GetReceiveSheetName())
                ws.rows(r).Hidden = isGreenville Or isCPU

            Case Else
                ws.rows(r).Hidden = False
        End Select
    Next r

    'Immediately refresh the receive-location top summary from the visible rows
    ThisWorkbook.RefreshReceiveLocationSummary ws
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplyDestinationSelection
' Scope: Public Sub
'
' What it does:
'   Applies formatting, filters, protection, selection state, or business-
'   state changes for ApplyDestinationSelection.
'
' Why it exists:
'   Separating apply steps makes it easier to rebuild sheets and then
'   consistently reapply the visual/workflow rules operators rely on.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub ApplyDestinationSelection()
    Dim panelWs As Worksheet
    Dim dataWs As Worksheet
    Dim newDest As String
    Dim oldDest As String
    Dim oldSheetName As String
    Dim newSheetName As String

    On Error GoTo ErrHandler
    Application.ScreenUpdating = False
    Application.EnableEvents = False
    Application.DisplayAlerts = False

    Set panelWs = ThisWorkbook.Worksheets("Utility Panel")
    Set dataWs = ThisWorkbook.Worksheets("Delivery List")

    newDest = CleanSheetTabName(GetSelectedDestinationFromSelector(panelWs))
    oldDest = GetReceiveDestinationName()
    oldSheetName = GetReceiveSheetName()
    newSheetName = "Inbound - " & newDest

    If Len(newDest) = 0 Then
        MsgBox "Please select a destination.", vbExclamation, "Destination Required"
        GoTo SafeExit
    End If

    If UCase$(newDest) = UCase$("Greenville") Then
        MsgBox "Greenville is now handled as its own separate inbound sheet." & vbCrLf & vbCrLf & _
                "Please leave the main inbound destination as Indian Trail for phase 1.", _
                vbExclamation, "Greenville Handled Separately"
        GoTo SafeExit
    End If

    If UCase$(newDest) = UCase$("Delivery List") Or _
       UCase$(newDest) = UCase$("Utility Panel") Then
        MsgBox "That destination name is reserved. Please choose a different name.", vbExclamation, "Invalid Destination"
        GoTo SafeExit
    End If

    If UCase$(newSheetName) <> UCase$(oldSheetName) Then
        If Not SheetNameAvailable(newSheetName) Then
            MsgBox "A different sheet already uses the name '" & newSheetName & "'.", vbExclamation, "Name In Use"
            GoTo SafeExit
        End If
    End If

    SaveReceiveSheetName newDest

    On Error Resume Next
    dataWs.Unprotect Password:=""
    On Error GoTo ErrHandler

    ScannerValidation.EnsureScanLayout dataWs
    AutoFitCommentColumnsTemplate dataWs

    If UCase$(oldSheetName) <> UCase$(newSheetName) Then
        DeleteSheetIfExists ThisWorkbook, oldSheetName
    End If

    HighlightGreenvilleRowsTemplate dataWs

    RebuildAllScannerSheetsFromMain dataWs
    
    ProtectViewOnlyTemplate dataWs
    CreateOrRefreshHomeMenu
    ThisWorkbook.Worksheets("Utility Panel").Activate

    MsgBox "Receiving destination updated to '" & GetReceiveSheetName() & "'.", vbInformation, "Destination Updated"

SafeExit:
    Application.DisplayAlerts = True
    Application.EnableEvents = True
    Application.ScreenUpdating = True
    Exit Sub

ErrHandler:
    Application.DisplayAlerts = True
    Application.EnableEvents = True
    Application.ScreenUpdating = True
    MsgBox "ApplyDestinationSelection error " & Err.Number & ":" & vbCrLf & Err.Description, vbCritical, "Destination Error"
End Sub

'------------------------------------------------------------------------------
' Procedure: SheetNameAvailable
' Scope: Private Function
'
' What it does:
'   Finds, creates, deletes, rebuilds, protects, or synchronizes worksheets
'   for SheetNameAvailable.
'
' Why it exists:
'   The master workbook creates multiple operational views from one delivery
'   list; worksheet helpers keep those views from drifting apart.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SheetNameAvailable(ByVal sheetName As String) As Boolean
    Dim ws As Worksheet

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(sheetName)
    On Error GoTo 0

    SheetNameAvailable = (ws Is Nothing)
End Function

'------------------------------------------------------------------------------
' Procedure: GoToReceiveSheet
' Scope: Public Sub
'
' What it does:
'   Controls the active sheet/window view, freeze panes, navigation, or
'   selected cell for GoToReceiveSheet.
'
' Why it exists:
'   The workbook is used by scanners/operators, so opening the right view and
'   scan area reduces missed scans and operator confusion.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub GoToReceiveSheet()
    Dim ws As Worksheet
    Set ws = GetReceiveSheet()
    If Not ws Is Nothing Then ws.Activate
End Sub

'------------------------------------------------------------------------------
' Procedure: PromptForUpdateImportKindTemplate
' Scope: Private Function
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   PromptForUpdateImportKindTemplate.
'
' Why it exists:
'   Delivery timing, queue timestamps, and scan timestamps drive status
'   messages such as Early, On-Time, Late, Processing, and Done.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function PromptForUpdateImportKindTemplate() As String
    'All updates now come from the same combined delivery list.
    'Default to REGULAR and let row-level RM markers be auto-detected.
    PromptForUpdateImportKindTemplate = "REGULAR"
End Function

'------------------------------------------------------------------------------
' Procedure: PromptForPrintJobTypeTemplate
' Scope: Private Function
'
' What it does:
'   Performs the workbook-specific step named PromptForPrintJobTypeTemplate
'   inside TemplateImporter.
'
' Why it exists:
'   The master workbook uses this module to turn a raw delivery list into the
'   operational sheets used by scanning, printing, exports, and intake
'   snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function PromptForPrintJobTypeTemplate() As String
    Dim choice As Variant

    choice = Application.InputBox( _
        "Select print filter:" & vbCrLf & vbCrLf & _
        "1 = Regular orders" & vbCrLf & _
        "2 = Remakes only" & vbCrLf & _
        "3 = Updated regular orders" & vbCrLf & _
        "4 = Updated remakes" & vbCrLf & _
        "5 = All updated orders" & vbCrLf & _
        "6 = All orders", _
        "Print Selection", Type:=1)

    If VarType(choice) = vbBoolean Then Exit Function

    Select Case CLng(Val(choice))
        Case 1: PromptForPrintJobTypeTemplate = "ORDERS"
        Case 2: PromptForPrintJobTypeTemplate = "REMAKES"
        Case 3: PromptForPrintJobTypeTemplate = "UPDATED_ORDERS"
        Case 4: PromptForPrintJobTypeTemplate = "UPDATED_REMAKES"
        Case 5: PromptForPrintJobTypeTemplate = "UPDATED_ALL"
        Case 6: PromptForPrintJobTypeTemplate = "ALL"
        Case Else
            MsgBox "Please enter 1, 2, 3, 4, 5, or 6.", vbExclamation, "Print Selection"
    End Select
End Function

'------------------------------------------------------------------------------
' Procedure: IsRemakeMarkerValueTemplate
' Scope: Private Function
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   IsRemakeMarkerValueTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function IsRemakeMarkerValueTemplate(ByVal v As Variant) As Boolean
    Dim s As String

    s = UCase$(Trim$(CStr(v)))

    IsRemakeMarkerValueTemplate = _
        (s = UCase$(REMAKE_MARKER_TEXT)) Or _
        (s = "RM")
End Function

'------------------------------------------------------------------------------
' Procedure: GetRowImportKindTemplate
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   GetRowImportKindTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetRowImportKindTemplate(ByVal ws As Worksheet, ByVal rowNum As Long) As String
    If IsRemakeMarkerValueTemplate(ws.Cells(rowNum, REMAKE_MARKER_COL_FIXED).Value) Then
        GetRowImportKindTemplate = "REMAKE"
    Else
        GetRowImportKindTemplate = "REGULAR"
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: IsRemakeRowTemplate
' Scope: Private Function
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   IsRemakeRowTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function IsRemakeRowTemplate(ByVal ws As Worksheet, ByVal rowNum As Long) As Boolean
    IsRemakeRowTemplate = IsRemakeMarkerValueTemplate(ws.Cells(rowNum, REMAKE_MARKER_COL_FIXED).Value)
End Function

'------------------------------------------------------------------------------
' Procedure: BuildDeliveryLineKeyWithKindTemplate
' Scope: Private Function
'
' What it does:
'   Builds a derived value, key, JSON block, layout, collection, or workbook
'   object used later by the workflow (BuildDeliveryLineKeyWithKindTemplate).
'
' Why it exists:
'   The project uses generated keys/layouts to keep repeated logic consistent
'   instead of hand-building values in multiple places.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BuildDeliveryLineKeyWithKindTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, _
                                                      ByVal sectionKey As String, ByVal orderCol As Long, _
                                                      ByVal itemCol As Long, ByVal importKind As String, _
                                                      Optional ByVal routeKey As String = "__NOROUTE__") As String
    Dim ordTxt As String
    Dim itemTxt As String

    ordTxt = Trim$(CStr(ws.Cells(rowNum, orderCol).Value))

    If IsNumeric(ws.Cells(rowNum, itemCol).Value) Then
        itemTxt = Format$(CLng(Val(ws.Cells(rowNum, itemCol).Value)), "000")
    Else
        itemTxt = Trim$(CStr(ws.Cells(rowNum, itemCol).Value))
    End If

    If Len(routeKey) = 0 Then routeKey = "__NOROUTE__"

    BuildDeliveryLineKeyWithKindTemplate = UCase$(Trim$(importKind)) & "|" & _
                                           UCase$(Trim$(routeKey)) & "|" & _
                                           NormalizeSectionKey(sectionKey) & "|" & _
                                           ordTxt & "|" & itemTxt
End Function

'------------------------------------------------------------------------------
' Procedure: BuildExistingDeliveryKeySetWithKindTemplate
' Scope: Private Function
'
' What it does:
'   Builds a derived value, key, JSON block, layout, collection, or workbook
'   object used later by the workflow
'   (BuildExistingDeliveryKeySetWithKindTemplate).
'
' Why it exists:
'   The project uses generated keys/layouts to keep repeated logic consistent
'   instead of hand-building values in multiple places.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BuildExistingDeliveryKeySetWithKindTemplate(ByVal ws As Worksheet, ByVal firstDataRow As Long, _
                                                             ByVal orderCol As Long, ByVal itemCol As Long) As Object
    Dim dict As Object
    Dim lastRealRow As Long
    Dim currentSectionKey As String
    Dim rowKey As String
    Dim rowKind As String
    Dim routeKey As String
    Dim r As Long

    Set dict = CreateObject("Scripting.Dictionary")
    lastRealRow = FindLastRealDeliveryRowTemplate(ws, orderCol, itemCol, firstDataRow)
    currentSectionKey = vbNullString

    For r = firstDataRow To lastRealRow
        If IsSectionHeaderRowTemplate(ws, r, orderCol, itemCol) Then
            currentSectionKey = NormalizeSectionKey(CStr(ws.Cells(r, 1).Value))

        ElseIf IsRealDeliveryLineTemplate(ws, r, orderCol, itemCol) Then
            If Len(currentSectionKey) = 0 Then currentSectionKey = "__UNSECTIONED__"

            rowKind = GetRowImportKindTemplate(ws, r)
            routeKey = NormalizeRouteKeyForUpdateTemplate(ws.Cells(r, ROUTE_COL_FIXED).Value)

            rowKey = BuildDeliveryLineKeyWithKindTemplate(ws, r, currentSectionKey, orderCol, itemCol, rowKind, routeKey)

            If Not dict.Exists(rowKey) Then
                dict.Add rowKey, True
            End If
        End If
    Next r

    Set BuildExistingDeliveryKeySetWithKindTemplate = dict
End Function

'------------------------------------------------------------------------------
' Procedure: ClearRemakeRowBoxBordersTemplate
' Scope: Private Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   ClearRemakeRowBoxBordersTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ClearRemakeRowBoxBordersTemplate(ByVal ws As Worksheet, ByVal rowNum As Long)
    With ws.Cells(rowNum, REMAKE_MARKER_COL_FIXED)
        .Borders(xlEdgeLeft).LineStyle = xlNone
        .Borders(xlEdgeTop).LineStyle = xlNone
        .Borders(xlEdgeBottom).LineStyle = xlNone
        .Borders(xlEdgeRight).LineStyle = xlNone
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: HasUpdatedPurpleOuterBorderTemplate
' Scope: Private Function
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   HasUpdatedPurpleOuterBorderTemplate.
'
' Why it exists:
'   Delivery timing, queue timestamps, and scan timestamps drive status
'   messages such as Early, On-Time, Late, Processing, and Done.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function HasUpdatedPurpleOuterBorderTemplate(ByVal ws As Worksheet, ByVal rowNum As Long) As Boolean
    Dim rng As Range

    Set rng = ws.Range("A" & rowNum & ":J" & rowNum)

    On Error Resume Next
    HasUpdatedPurpleOuterBorderTemplate = _
        (rng.Borders(xlEdgeLeft).LineStyle <> xlNone And rng.Borders(xlEdgeLeft).Color = RGB(112, 48, 160)) And _
        (rng.Borders(xlEdgeRight).LineStyle <> xlNone And rng.Borders(xlEdgeRight).Color = RGB(112, 48, 160))
    On Error GoTo 0
End Function

'------------------------------------------------------------------------------
' Procedure: ReapplyUpdatedPurpleOuterBorderTemplate
' Scope: Private Sub
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   ReapplyUpdatedPurpleOuterBorderTemplate.
'
' Why it exists:
'   Delivery timing, queue timestamps, and scan timestamps drive status
'   messages such as Early, On-Time, Late, Processing, and Done.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ReapplyUpdatedPurpleOuterBorderTemplate(ByVal ws As Worksheet, ByVal rowNum As Long)
    With ws.Range("A" & rowNum & ":J" & rowNum)
        With .Borders(xlEdgeLeft)
            .LineStyle = xlContinuous
            .Weight = xlThin
            .Color = RGB(112, 48, 160)
        End With
        With .Borders(xlEdgeTop)
            .LineStyle = xlContinuous
            .Weight = xlThin
            .Color = RGB(112, 48, 160)
        End With
        With .Borders(xlEdgeBottom)
            .LineStyle = xlContinuous
            .Weight = xlThin
            .Color = RGB(112, 48, 160)
        End With
        With .Borders(xlEdgeRight)
            .LineStyle = xlContinuous
            .Weight = xlThin
            .Color = RGB(112, 48, 160)
        End With
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplyRemakeMarkerTemplate
' Scope: Private Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   ApplyRemakeMarkerTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ApplyRemakeMarkerTemplate(ByVal ws As Worksheet, ByVal rowNum As Long)
    Dim keepUpdatedPurple As Boolean

    keepUpdatedPurple = HasUpdatedPurpleOuterBorderTemplate(ws, rowNum)

    ClearRemakeRowBoxBordersTemplate ws, rowNum

    With ws.Cells(rowNum, REMAKE_MARKER_COL_FIXED)
        .Value = REMAKE_MARKER_TEXT
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

    'If this remake row was also an updated/new purple row,
    'restore the purple OUTER border after the RM cell is rebuilt.
    If keepUpdatedPurple Then
        ReapplyUpdatedPurpleOuterBorderTemplate ws, rowNum
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplyRemakeAdditionMarkTemplate
' Scope: Private Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   ApplyRemakeAdditionMarkTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ApplyRemakeAdditionMarkTemplate(ByVal ws As Worksheet, ByVal rowNum As Long)
    'Do not overwrite CPU / Greenville row fill.
    'RM formatting is the red RM cell plus red borders around each display box.
    ApplyRemakeMarkerTemplate ws, rowNum
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplyImportedRemakeMarkTemplate
' Scope: Private Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   ApplyImportedRemakeMarkTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ApplyImportedRemakeMarkTemplate(ByVal ws As Worksheet, ByVal rowNum As Long)
    'Do not overwrite CPU / Greenville row fill.
    'RM formatting is the red RM cell plus red borders around each display box.
    ApplyRemakeMarkerTemplate ws, rowNum
End Sub

'------------------------------------------------------------------------------
' Procedure: ReapplyImportedRemakeMarkersTemplate
' Scope: Private Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   ReapplyImportedRemakeMarkersTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ReapplyImportedRemakeMarkersTemplate(ByVal ws As Worksheet, ByVal firstDataRow As Long, _
                                                 ByVal orderCol As Long, ByVal itemCol As Long)
    Dim lastRealRow As Long
    Dim r As Long

    lastRealRow = FindLastRealDeliveryRowTemplate(ws, orderCol, itemCol, firstDataRow)
    If lastRealRow < firstDataRow Then Exit Sub

    For r = firstDataRow To lastRealRow
        If IsRealDeliveryLineTemplate(ws, r, orderCol, itemCol) Then
            If IsRemakeRowTemplate(ws, r) Then
                ApplyImportedRemakeMarkTemplate ws, r
            Else
                ClearRemakeRowBoxBordersTemplate ws, r
            End If
        End If
    Next r
End Sub

'------------------------------------------------------------------------------
' Procedure: ReapplyRemakeMarkersTemplate
' Scope: Private Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   ReapplyRemakeMarkersTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ReapplyRemakeMarkersTemplate(ByVal ws As Worksheet, ByVal firstDataRow As Long, _
                                         ByVal orderCol As Long, ByVal itemCol As Long)
    Dim lastRealRow As Long
    Dim r As Long

    lastRealRow = FindLastRealDeliveryRowTemplate(ws, orderCol, itemCol, firstDataRow)
    If lastRealRow < firstDataRow Then Exit Sub

    For r = firstDataRow To lastRealRow
        If IsRealDeliveryLineTemplate(ws, r, orderCol, itemCol) Then
            If IsRemakeRowTemplate(ws, r) Then
                ApplyRemakeMarkerTemplate ws, r
            Else
                ClearRemakeRowBoxBordersTemplate ws, r
            End If
        End If
    Next r
End Sub

'------------------------------------------------------------------------------
' Procedure: ReapplyRemakeMarkersForSheetTemplate
' Scope: Public Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   ReapplyRemakeMarkersForSheetTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub ReapplyRemakeMarkersForSheetTemplate(ByVal ws As Worksheet)
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim firstDataRow As Long
    Dim orderCol As Long
    Dim itemCol As Long

    If ws Is Nothing Then Exit Sub

    Set orderHdr = FindHeaderCellTemplate(ws, Array("Order Nr."))
    Set itemHdr = FindHeaderCellTemplate(ws, Array("Item Nr.", "Item"))

    If orderHdr Is Nothing Or itemHdr Is Nothing Then Exit Sub

    firstDataRow = orderHdr.Row + 1
    orderCol = orderHdr.Column
    itemCol = itemHdr.Column

    ReapplyRemakeMarkersTemplate ws, firstDataRow, orderCol, itemCol
End Sub

'------------------------------------------------------------------------------
' Procedure: ClearBandAJStyleTemplate
' Scope: Private Sub
'
' What it does:
'   Clears temporary data, formatting, cached state, or helper ranges for
'   ClearBandAJStyleTemplate.
'
' Why it exists:
'   Old scan/edit/import state can mislead operators if it survives a refresh,
'   rebuild, or new delivery list import.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ClearBandAJStyleTemplate(ByVal ws As Worksheet, ByVal rowNum As Long)
    With ws.Range("A" & rowNum & ":J" & rowNum)
        .Interior.Pattern = xlNone
        .Font.ColorIndex = xlAutomatic
        .Font.Bold = False
        .Borders.LineStyle = xlNone
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplyBandAJStyleTemplate
' Scope: Private Sub
'
' What it does:
'   Applies formatting, filters, protection, selection state, or business-
'   state changes for ApplyBandAJStyleTemplate.
'
' Why it exists:
'   Separating apply steps makes it easier to rebuild sheets and then
'   consistently reapply the visual/workflow rules operators rely on.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ApplyBandAJStyleTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, _
                                     ByVal fillColor As Long, ByVal fontColor As Long, _
                                     Optional ByVal usePurpleBorder As Boolean = False)
    With ws.Range("A" & rowNum & ":J" & rowNum)
        .Interior.Color = fillColor
        .Font.Color = fontColor
        .Font.Bold = True

        If usePurpleBorder Then
            With .Borders
                .LineStyle = xlContinuous
                .Weight = xlThin
                .Color = RGB(112, 48, 160)
            End With
        Else
            .Borders.LineStyle = xlNone
        End If
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: ClearCPUCellStyleTemplate
' Scope: Private Sub
'
' What it does:
'   Identifies, filters, formats, or routes Customer Pickup rows for
'   ClearCPUCellStyleTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ClearCPUCellStyleTemplate(ByVal ws As Worksheet, ByVal rowNum As Long)
    With ws.Cells(rowNum, ROUTE_COL_FIXED)
        .Interior.Pattern = xlNone
        .Font.ColorIndex = xlAutomatic
        .Font.Bold = False
        .Borders.LineStyle = xlNone
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplyCPUCellStyleTemplate
' Scope: Private Sub
'
' What it does:
'   Identifies, filters, formats, or routes Customer Pickup rows for
'   ApplyCPUCellStyleTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ApplyCPUCellStyleTemplate(ByVal ws As Worksheet, ByVal rowNum As Long)
    With ws.Cells(rowNum, ROUTE_COL_FIXED)
        .Interior.Color = RGB(248, 214, 170)
        .Font.Color = RGB(125, 68, 28)
        .Font.Bold = True

        With .Borders
            .LineStyle = xlContinuous
            .Weight = xlThin
            .Color = RGB(191, 144, 0)
        End With
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: ClearRMCellStyleTemplate
' Scope: Private Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   ClearRMCellStyleTemplate.
'
' Why it exists:
'   Remakes need separate visual and print/export handling so replacement
'   glass is not confused with regular delivery-list work.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ClearRMCellStyleTemplate(ByVal ws As Worksheet, ByVal rowNum As Long)
    ClearRemakeRowBoxBordersTemplate ws, rowNum

    With ws.Cells(rowNum, REMAKE_MARKER_COL_FIXED)
        .Interior.Pattern = xlNone
        .Font.ColorIndex = xlAutomatic
        .Font.Bold = False
        .Borders.LineStyle = xlNone
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: IsAddedRowNumberTemplate
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   IsAddedRowNumberTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function IsAddedRowNumberTemplate(ByVal addedRows As Object, ByVal rowNum As Long) As Boolean
    On Error Resume Next
    IsAddedRowNumberTemplate = (Not addedRows Is Nothing) And addedRows.Exists(CStr(rowNum))
    On Error GoTo 0
End Function

'------------------------------------------------------------------------------
' Procedure: IsAddedRowKeyTemplate
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   IsAddedRowKeyTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function IsAddedRowKeyTemplate(ByVal addedKeys As Object, ByVal rowKey As String) As Boolean
    On Error Resume Next
    IsAddedRowKeyTemplate = (Not addedKeys Is Nothing) And addedKeys.Exists(rowKey)
    On Error GoTo 0
End Function

'------------------------------------------------------------------------------
' Procedure: BuildCurrentDeliveryLineKeyWithKindTemplate
' Scope: Private Function
'
' What it does:
'   Builds a derived value, key, JSON block, layout, collection, or workbook
'   object used later by the workflow
'   (BuildCurrentDeliveryLineKeyWithKindTemplate).
'
' Why it exists:
'   The project uses generated keys/layouts to keep repeated logic consistent
'   instead of hand-building values in multiple places.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BuildCurrentDeliveryLineKeyWithKindTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, _
                                                             ByVal sectionKey As String, ByVal orderCol As Long, _
                                                             ByVal itemCol As Long) As String
    Dim rowKind As String
    Dim routeKey As String

    rowKind = GetRowImportKindTemplate(ws, rowNum)
    routeKey = NormalizeRouteKeyForUpdateTemplate(ws.Cells(rowNum, ROUTE_COL_FIXED).Value)

    BuildCurrentDeliveryLineKeyWithKindTemplate = _
        BuildDeliveryLineKeyWithKindTemplate(ws, rowNum, sectionKey, orderCol, itemCol, rowKind, routeKey)
End Function

'------------------------------------------------------------------------------
' Procedure: ApplyDeliveryListRowStyleTemplate
' Scope: Private Sub
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   ApplyDeliveryListRowStyleTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ApplyDeliveryListRowStyleTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, Optional ByVal isAdded As Boolean = False)
    Dim isGreenville As Boolean
    Dim isCPU As Boolean
    Dim isRemake As Boolean
    Dim hasProgressFill As Boolean

    isGreenville = IsGreenvilleRowTemplate(ws, rowNum)
    isCPU = IsCPURowTemplate(ws, rowNum)
    isRemake = IsRemakeRowTemplate(ws, rowNum)
    hasProgressFill = HasDeliveryProgressFillTemplate(ws.Range("A" & rowNum & ":J" & rowNum))

    ClearBandAJStyleTemplate ws, rowNum
    ClearCPUCellStyleTemplate ws, rowNum
    ClearRMCellStyleTemplate ws, rowNum

    'A:J band rules
    If isAdded Then
        If isGreenville Then
            ApplyBandAJStyleTemplate ws, rowNum, RGB(221, 235, 247), RGB(31, 78, 121), True
        Else
            ApplyBandAJStyleTemplate ws, rowNum, RGB(221, 217, 238), RGB(64, 0, 96), True
        End If
    ElseIf Not hasProgressFill Then
        If isGreenville Then
            ApplyBandAJStyleTemplate ws, rowNum, RGB(221, 235, 247), RGB(31, 78, 121), False
        End If
    End If

    'K = RM only
    If isRemake Then
        ApplyRemakeMarkerTemplate ws, rowNum
    End If

    'L = CPU only
    If isCPU Then
        ApplyCPUCellStyleTemplate ws, rowNum
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: ReapplyDeliveryListRowStylesTemplate
' Scope: Private Sub
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   ReapplyDeliveryListRowStylesTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ReapplyDeliveryListRowStylesTemplate(ByVal ws As Worksheet, ByVal firstDataRow As Long, _
                                                 ByVal orderCol As Long, ByVal itemCol As Long, _
                                                 Optional ByVal addedRows As Object = Nothing, _
                                                 Optional ByVal addedKeys As Object = Nothing)
    Dim lastRealRow As Long
    Dim r As Long
    Dim currentSectionKey As String
    Dim currentRowKey As String
    Dim isAdded As Boolean

    lastRealRow = FindLastRealDeliveryRowTemplate(ws, orderCol, itemCol, firstDataRow)
    If lastRealRow < firstDataRow Then Exit Sub

    currentSectionKey = vbNullString

    For r = firstDataRow To lastRealRow
        If IsSectionHeaderRowTemplate(ws, r, orderCol, itemCol) Then
            currentSectionKey = NormalizeSectionKey(CStr(ws.Cells(r, 1).Value))

        ElseIf IsRealDeliveryLineTemplate(ws, r, orderCol, itemCol) Then
            If Len(currentSectionKey) = 0 Then currentSectionKey = "__UNSECTIONED__"

            currentRowKey = BuildCurrentDeliveryLineKeyWithKindTemplate(ws, r, currentSectionKey, orderCol, itemCol)

            'Use only stable keys here.
            'Do NOT use row numbers during final reapply because inserts shift rows.
            isAdded = IsAddedRowKeyTemplate(addedKeys, currentRowKey)

            ApplyDeliveryListRowStyleTemplate ws, r, isAdded
        End If
    Next r
End Sub

'------------------------------------------------------------------------------
' Procedure: DoesPrintModeMatchRowTemplate
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   DoesPrintModeMatchRowTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function DoesPrintModeMatchRowTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, _
                                               ByVal destinationMode As String, ByVal printKind As String) As Boolean
    Dim isRemake As Boolean
    Dim isUpdated As Boolean

    If Not DoesDestinationMatchRowTemplate(ws, rowNum, destinationMode) Then Exit Function

    isRemake = IsRemakeRowTemplate(ws, rowNum)
    isUpdated = IsUpdatedPrintRowTemplate(ws, rowNum)

    Select Case UCase$(printKind)
        Case "ORDERS"
            DoesPrintModeMatchRowTemplate = (Not isRemake) And (Not isUpdated)

        Case "REMAKES"
            DoesPrintModeMatchRowTemplate = isRemake

        Case "UPDATED_ORDERS"
            DoesPrintModeMatchRowTemplate = isUpdated And (Not isRemake)

        Case "UPDATED_REMAKES"
            DoesPrintModeMatchRowTemplate = isUpdated And isRemake

        Case "UPDATED_ALL"
            DoesPrintModeMatchRowTemplate = isUpdated

        Case "ALL"
            DoesPrintModeMatchRowTemplate = True

        Case Else
            DoesPrintModeMatchRowTemplate = False
    End Select
End Function

'------------------------------------------------------------------------------
' Procedure: IsUpdatedPrintRowTemplate
' Scope: Private Function
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   IsUpdatedPrintRowTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function IsUpdatedPrintRowTemplate(ByVal ws As Worksheet, ByVal rowNum As Long) As Boolean
    If ws Is Nothing Then Exit Function
    If rowNum < FIRST_DATA_ROW_FIXED Then Exit Function

    IsUpdatedPrintRowTemplate = HasUpdatedPurpleOuterBorderTemplate(ws, rowNum)
End Function

'------------------------------------------------------------------------------
' Procedure: GetSingleDestinationTitleLabelTemplate
' Scope: Private Function
'
' What it does:
'   Returns a workbook object, setting, status value, parsed value, or
'   calculated result used by other procedures
'   (GetSingleDestinationTitleLabelTemplate).
'
' Why it exists:
'   Using one getter keeps callers from duplicating lookup logic and protects
'   them from missing sheets, missing names, or blank values.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetSingleDestinationTitleLabelTemplate(ByVal destinationMode As String) As String
    Dim hitCount As Long
    Dim labelText As String

    destinationMode = UCase$(Trim$(destinationMode))
    If destinationMode = "ALL" Then Exit Function

    If TokenListContainsTemplate(destinationMode, "STANDARD") Then
        hitCount = hitCount + 1
        labelText = "INDIAN TRAIL"
    End If

    If TokenListContainsTemplate(destinationMode, "GREENVILLE") Then
        hitCount = hitCount + 1
        labelText = "GREENVILLE"
    End If

    If TokenListContainsTemplate(destinationMode, "CPU") Then
        hitCount = hitCount + 1
        labelText = "CUSTOMER PICKUP"
    End If

    If hitCount = 1 Then
        GetSingleDestinationTitleLabelTemplate = labelText
    Else
        GetSingleDestinationTitleLabelTemplate = vbNullString
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: BuildDeliveryListTitleForDestinationTemplate
' Scope: Private Function
'
' What it does:
'   Builds a derived value, key, JSON block, layout, collection, or workbook
'   object used later by the workflow
'   (BuildDeliveryListTitleForDestinationTemplate).
'
' Why it exists:
'   The project uses generated keys/layouts to keep repeated logic consistent
'   instead of hand-building values in multiple places.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BuildDeliveryListTitleForDestinationTemplate(ByVal srcWs As Worksheet, _
                                                             ByVal destinationMode As String) As String
    Dim listDate As Date
    Dim dateText As String
    Dim singleDestLabel As String

    listDate = GetDeliveryListDateForFileName(srcWs)

    If listDate > 0 Then
        dateText = Format$(listDate, "m/d/yyyy")
    End If

    singleDestLabel = GetSingleDestinationTitleLabelTemplate(destinationMode)

    If Len(singleDestLabel) > 0 Then
        If Len(dateText) > 0 Then
            BuildDeliveryListTitleForDestinationTemplate = "DELIVERY LIST FOR " & singleDestLabel & " " & dateText
        Else
            BuildDeliveryListTitleForDestinationTemplate = "DELIVERY LIST FOR " & singleDestLabel
        End If
    Else
        If Len(dateText) > 0 Then
            BuildDeliveryListTitleForDestinationTemplate = "DELIVERY LIST FOR " & dateText
        Else
            BuildDeliveryListTitleForDestinationTemplate = "DELIVERY LIST"
        End If
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: ApplyDestinationAwareDeliveryTitleTemplate
' Scope: Private Sub
'
' What it does:
'   Applies formatting, filters, protection, selection state, or business-
'   state changes for ApplyDestinationAwareDeliveryTitleTemplate.
'
' Why it exists:
'   Separating apply steps makes it easier to rebuild sheets and then
'   consistently reapply the visual/workflow rules operators rely on.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ApplyDestinationAwareDeliveryTitleTemplate(ByVal ws As Worksheet, _
                                                       ByVal srcWs As Worksheet, _
                                                       ByVal destinationMode As String)
    Dim singleDestLabel As String
    Dim dateText As String
    Dim listDate As Date
    Dim line1Text As String
    Dim line2Text As String
    Dim fullText As String
    Dim line2Start As Long

    If ws Is Nothing Or srcWs Is Nothing Then Exit Sub

    singleDestLabel = GetSingleDestinationTitleLabelTemplate(destinationMode)
    listDate = GetDeliveryListDateForFileName(srcWs)

    If listDate > 0 Then
        dateText = Format$(listDate, "m/d/yyyy")
    Else
        dateText = vbNullString
    End If

    line1Text = "DELIVERY LIST FOR:"

    If Len(singleDestLabel) > 0 Then
        If Len(dateText) > 0 Then
            line2Text = singleDestLabel & " " & dateText
        Else
            line2Text = singleDestLabel
        End If
    Else
        If Len(dateText) > 0 Then
            line2Text = dateText
        Else
            line2Text = vbNullString
        End If
    End If

    If Len(line2Text) > 0 Then
        fullText = line1Text & vbLf & line2Text
    Else
        fullText = line1Text
    End If

    On Error Resume Next
    ws.Unprotect Password:=""
    ws.Range("A2:N3").UnMerge
    On Error GoTo 0

    'Start the title band a little to the right so it clears the logo better
    With ws.Range("A2:N3")
        .Merge
        .Value = fullText
        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
        .WrapText = True
        .Font.Name = "Calibri"
        .Font.Bold = True
        .Font.Italic = False
        .Font.Size = 20
        .Font.Color = RGB(0, 0, 0)
    End With

    'Italicize only the second line
    If Len(line2Text) > 0 Then
        line2Start = Len(line1Text) + 2   'vbLf counts as 1 char, next line starts after it
        With ws.Range("A2").Characters(line2Start, Len(line2Text)).Font
            .Bold = True
            .Italic = True
            .Underline = True
            .Size = 20
            .Color = RGB(0, 0, 0)
        End With
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: RepositionPrintPreviewLogoTemplate
' Scope: Private Sub
'
' What it does:
'   Finds, copies, removes, or positions the delivery-list logo for
'   RepositionPrintPreviewLogoTemplate.
'
' Why it exists:
'   Rebuilt scanner and print-preview sheets should retain the familiar
'   delivery-list branding without duplicating stale logo shapes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub RepositionPrintPreviewLogoTemplate(ByVal ws As Worksheet)
    Dim shp As Shape
    Dim safeBottom As Double
    Dim actualBottom As Double
    Dim extra As Double
    Dim bump As Double

    If ws Is Nothing Then Exit Sub

    On Error Resume Next

    For Each shp In ws.Shapes
        If LCase$(Left$(shp.Name, 13)) = "dlsharedlogo_" Then
            shp.LockAspectRatio = msoTrue

            'Keep the logo in the top-left corner at full size
            shp.Left = ws.Range("A1").Left + 3
            shp.Top = ws.Range("A1").Top + 3

            'Do not let it overlap the row-5 headers
            safeBottom = ws.rows(5).Top - 3
            actualBottom = shp.Top + shp.Height

            If actualBottom > safeBottom Then
                extra = actualBottom - safeBottom
                bump = (extra / 4) + 1

                ws.rows(1).RowHeight = ws.rows(1).RowHeight + bump
                ws.rows(2).RowHeight = ws.rows(2).RowHeight + bump
                ws.rows(3).RowHeight = ws.rows(3).RowHeight + bump
                ws.rows(4).RowHeight = ws.rows(4).RowHeight + bump

                'Reset top after row-height change
                shp.Left = ws.Range("A1").Left + 3
                shp.Top = ws.Range("A1").Top + 3
            End If

            Exit For
        End If
    Next shp

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: GetAllGlassSectionsTemplate
' Scope: Private Function
'
' What it does:
'   Returns a workbook object, setting, status value, parsed value, or
'   calculated result used by other procedures (GetAllGlassSectionsTemplate).
'
' Why it exists:
'   Using one getter keeps callers from duplicating lookup logic and protects
'   them from missing sheets, missing names, or blank values.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetAllGlassSectionsTemplate(ByVal ws As Worksheet, ByVal firstDataRow As Long, ByVal lastRealRow As Long, _
                                             ByVal orderCol As Long, ByVal itemCol As Long) As Collection
    Dim sections As Collection
    Dim seen As Object
    Dim r As Long
    Dim titleText As String
    Dim key As String

    Set sections = New Collection
    Set seen = CreateObject("Scripting.Dictionary")

    For r = firstDataRow To lastRealRow
        If IsSectionHeaderRowTemplate(ws, r, orderCol, itemCol) Then
            titleText = Trim$(CStr(ws.Cells(r, 1).Value))
            key = UCase$(titleText)

            If Len(titleText) > 0 Then
                If Not seen.Exists(key) Then
                    seen.Add key, True
                    sections.Add Array(titleText, r, r)
                End If
            End If
        End If
    Next r

    Set GetAllGlassSectionsTemplate = sections
End Function

'------------------------------------------------------------------------------
' Procedure: GetDeliveryListSectionsForPrintKind
' Scope: Public Function
'
' What it does:
'   Returns a workbook object, setting, status value, parsed value, or
'   calculated result used by other procedures
'   (GetDeliveryListSectionsForPrintKind).
'
' Why it exists:
'   Using one getter keeps callers from duplicating lookup logic and protects
'   them from missing sheets, missing names, or blank values.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function GetDeliveryListSectionsForPrintKind(ByVal ws As Worksheet, ByVal firstDataRow As Long, ByVal lastRealRow As Long, _
                                                     ByVal orderCol As Long, ByVal itemCol As Long, _
                                                     ByVal destinationMode As String, ByVal printKind As String) As Collection
    Dim sections As Collection
    Dim currentTitle As String
    Dim currentStart As Long
    Dim r As Long

    Set sections = New Collection
    currentTitle = vbNullString
    currentStart = 0

    For r = firstDataRow To lastRealRow
        If IsSectionHeaderRowTemplate(ws, r, orderCol, itemCol) Then
            If currentStart > 0 Then
                If SectionContainsPrintableRowsTemplate(ws, currentStart, r - 1, orderCol, itemCol, destinationMode, printKind) Then
                    sections.Add Array(currentTitle, currentStart, r - 1)
                End If
            End If

            currentTitle = Trim$(CStr(ws.Cells(r, 1).Value))
            currentStart = r
        End If
    Next r

    If currentStart > 0 Then
        If SectionContainsPrintableRowsTemplate(ws, currentStart, lastRealRow, orderCol, itemCol, destinationMode, printKind) Then
            sections.Add Array(currentTitle, currentStart, lastRealRow)
        End If
    End If

    Set GetDeliveryListSectionsForPrintKind = sections
End Function

'------------------------------------------------------------------------------
' Procedure: SectionContainsPrintableRowsTemplate
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   SectionContainsPrintableRowsTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SectionContainsPrintableRowsTemplate(ByVal ws As Worksheet, ByVal startRow As Long, ByVal endRow As Long, _
                                                      ByVal orderCol As Long, ByVal itemCol As Long, _
                                                      ByVal destinationMode As String, ByVal printKind As String) As Boolean
    Dim r As Long

    For r = startRow To endRow
        If IsRealDeliveryLineTemplate(ws, r, orderCol, itemCol) Then
            If DoesPrintModeMatchRowTemplate(ws, r, destinationMode, printKind) Then
                SectionContainsPrintableRowsTemplate = True
                Exit Function
            End If
        End If
    Next r
End Function

'------------------------------------------------------------------------------
' Procedure: PromptForGlassSectionChoiceLabelTemplate
' Scope: Private Function
'
' What it does:
'   Performs the workbook-specific step named
'   PromptForGlassSectionChoiceLabelTemplate inside TemplateImporter.
'
' Why it exists:
'   The master workbook uses this module to turn a raw delivery list into the
'   operational sheets used by scanning, printing, exports, and intake
'   snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function PromptForGlassSectionChoiceLabelTemplate(ByVal sections As Collection, ByVal labelText As String) As String
    Dim promptText As String
    Dim raw As String
    Dim i As Long
    Dim sectionInfo As Variant

    If sections Is Nothing Then
        PromptForGlassSectionChoiceLabelTemplate = "ALL"
        Exit Function
    End If

    If sections.Count = 0 Then
        PromptForGlassSectionChoiceLabelTemplate = "ALL"
        Exit Function
    End If

    promptText = "Select glass type(s) for " & labelText & ":" & vbCrLf & vbCrLf & _
                 "0 = All glass types"

    For i = 1 To sections.Count
        sectionInfo = sections(i)
        promptText = promptText & vbCrLf & CStr(i) & " = " & CStr(sectionInfo(0))
    Next i

    promptText = promptText & vbCrLf & vbCrLf & _
                 "You can enter one or more numbers separated by commas." & vbCrLf & _
                 "Example: 1,3,5" & vbCrLf & vbCrLf & _
                 "You can also enter the exact glass name(s)."

    raw = InputBox(promptText, "Select Glass Type(s)")
    raw = Trim$(raw)

    If raw = "" Then Exit Function

    If raw = "0" Then
        PromptForGlassSectionChoiceLabelTemplate = "ALL"
        Exit Function
    End If

    PromptForGlassSectionChoiceLabelTemplate = BuildGlassSectionKeyListTemplate(sections, raw)

    If Len(PromptForGlassSectionChoiceLabelTemplate) = 0 Then
        MsgBox "Invalid glass selection." & vbCrLf & vbCrLf & _
               "Enter 0, a number like 2, a comma list like 1,3,5," & vbCrLf & _
               "or an exact glass name.", _
               vbExclamation, "Print Selection"
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: BuildGlassSectionKeyListTemplate
' Scope: Private Function
'
' What it does:
'   Builds a derived value, key, JSON block, layout, collection, or workbook
'   object used later by the workflow (BuildGlassSectionKeyListTemplate).
'
' Why it exists:
'   The project uses generated keys/layouts to keep repeated logic consistent
'   instead of hand-building values in multiple places.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BuildGlassSectionKeyListTemplate(ByVal sections As Collection, ByVal raw As String) As String
    Dim parts() As String
    Dim partText As String
    Dim i As Long
    Dim j As Long
    Dim idx As Long
    Dim sectionInfo As Variant
    Dim outText As String
    Dim matched As Boolean
    Dim targetKey As String
    Dim sectionKey As String

    If Len(Trim$(raw)) = 0 Then Exit Function
    If sections Is Nothing Then Exit Function
    If sections.Count = 0 Then Exit Function

    raw = Replace$(raw, ";", ",")
    parts = Split(raw, ",")

    For i = LBound(parts) To UBound(parts)
        partText = Trim$(parts(i))

        If Len(partText) = 0 Then
            'ignore blank fragments
        ElseIf IsNumeric(partText) Then
            idx = CLng(Val(partText))

            If idx = 0 Then
                BuildGlassSectionKeyListTemplate = "ALL"
                Exit Function
            End If

            If idx < 1 Or idx > sections.Count Then
                BuildGlassSectionKeyListTemplate = vbNullString
                Exit Function
            End If

            sectionInfo = sections(idx)
            AddTokenTemplate outText, NormalizeSectionKey(CStr(sectionInfo(0)))

        Else
            matched = False
            targetKey = NormalizeSectionKey(partText)

            For j = 1 To sections.Count
                sectionInfo = sections(j)
                sectionKey = NormalizeSectionKey(CStr(sectionInfo(0)))

                If StrComp(sectionKey, targetKey, vbTextCompare) = 0 Then
                    AddTokenTemplate outText, sectionKey
                    matched = True
                    Exit For
                End If
            Next j

            If Not matched Then
                BuildGlassSectionKeyListTemplate = vbNullString
                Exit Function
            End If
        End If
    Next i

    BuildGlassSectionKeyListTemplate = outText
End Function

'------------------------------------------------------------------------------
' Procedure: IsGlassSectionSelectedTemplate
' Scope: Private Function
'
' What it does:
'   Returns a True/False decision used by higher-level workflow code
'   (IsGlassSectionSelectedTemplate).
'
' Why it exists:
'   Boolean helpers make business rules readable and keep condition checks
'   consistent across modules.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function IsGlassSectionSelectedTemplate(ByVal sectionTitle As String, ByVal selectedGlassKeys As String) As Boolean
    If UCase$(Trim$(selectedGlassKeys)) = "ALL" Then
        IsGlassSectionSelectedTemplate = True
    Else
        IsGlassSectionSelectedTemplate = TokenListContainsTemplate(selectedGlassKeys, NormalizeSectionKey(sectionTitle))
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: GetRemakeJobDisplayTextTemplate
' Scope: Private Function
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   GetRemakeJobDisplayTextTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetRemakeJobDisplayTextTemplate(ByVal ws As Worksheet, ByVal rowNum As Long) As String
    Dim c As Long
    Dim part As String
    Dim txt As String

    For c = 1 To 4
        part = Trim$(CStr(ws.Cells(rowNum, c).Value))
        If Len(part) > 0 Then
            If Len(txt) > 0 Then txt = txt & " "
            txt = txt & part
        End If
    Next c

    GetRemakeJobDisplayTextTemplate = txt
End Function

'------------------------------------------------------------------------------
' Procedure: ApplyRemakeTemplateRowFormat
' Scope: Private Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   ApplyRemakeTemplateRowFormat.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ApplyRemakeTemplateRowFormat(ByVal ws As Worksheet, ByVal templateRow As Long, ByVal destRow As Long)
    ws.rows(templateRow).Copy
    ws.rows(destRow).PasteSpecial xlPasteFormats
    Application.CutCopyMode = False
    ws.rows(destRow).RowHeight = ws.rows(templateRow).RowHeight
    ws.Range("A" & destRow & ":M" & destRow).ClearContents
End Sub

'------------------------------------------------------------------------------
' Procedure: WriteRemakeSectionHeaderTemplate
' Scope: Private Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   WriteRemakeSectionHeaderTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub WriteRemakeSectionHeaderTemplate(ByVal ws As Worksheet, ByVal destRow As Long, ByVal sectionTitle As String)
    ApplyRemakeTemplateRowFormat ws, GetRemakePrintSectionTemplateRowTemplate(ws), destRow
    ws.Cells(destRow, 1).Value = sectionTitle
End Sub

'------------------------------------------------------------------------------
' Procedure: WriteRemakeBlankSpacerTemplate
' Scope: Private Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   WriteRemakeBlankSpacerTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub WriteRemakeBlankSpacerTemplate(ByVal ws As Worksheet, ByVal destRow As Long)
    ApplyRemakeTemplateRowFormat ws, GetRemakePrintSpacerTemplateRowTemplate(ws), destRow
End Sub

'------------------------------------------------------------------------------
' Procedure: WriteRemakeLineTemplate
' Scope: Private Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   WriteRemakeLineTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub WriteRemakeLineTemplate(ByVal srcWs As Worksheet, ByVal srcRow As Long, ByVal destWs As Worksheet, _
                                    ByVal destRow As Long, ByVal orderCol As Long, ByVal itemCol As Long, _
                                    ByVal qtyCol As Long, ByVal dimCol As Long)

    ApplyRemakeTemplateRowFormat destWs, GetRemakePrintLineTemplateRowTemplate(destWs), destRow

    On Error Resume Next
    destWs.Range("A" & destRow & ":M" & destRow).UnMerge
    On Error GoTo 0

    destWs.Range("A" & destRow & ":M" & destRow).ClearContents

    'Reference remake layout:
    'A = Job Nr.
    'C = Order
    'E = Item
    'G = Qty.
    'I = Dimensions
    'K = Check Off

    destWs.Cells(destRow, 1).Value = GetRemakeJobDisplayTextTemplate(srcWs, srcRow)
    destWs.Cells(destRow, 3).Value = srcWs.Cells(srcRow, orderCol).Value

    If IsNumeric(srcWs.Cells(srcRow, itemCol).Value) Then
        destWs.Cells(destRow, 5).Value = Format$(CLng(Val(srcWs.Cells(srcRow, itemCol).Value)), "000")
    Else
        destWs.Cells(destRow, 5).Value = srcWs.Cells(srcRow, itemCol).Value
    End If

    destWs.Cells(destRow, 7).Value = srcWs.Cells(srcRow, qtyCol).Value
    destWs.Cells(destRow, 9).Value = srcWs.Cells(srcRow, dimCol).Value

    'No customer text on remake print
    destWs.Cells(destRow, 11).Value = ChrW(&H25A1)   '?
    destWs.Cells(destRow, 11).HorizontalAlignment = xlCenter
    destWs.Cells(destRow, 11).VerticalAlignment = xlCenter
    destWs.Cells(destRow, 11).Font.Name = "Segoe UI Symbol"
    destWs.Cells(destRow, 11).Font.Size = 20
    destWs.Cells(destRow, 11).Font.Bold = False

    destWs.Cells(destRow, 1).HorizontalAlignment = xlLeft
    destWs.Cells(destRow, 1).VerticalAlignment = xlCenter

    destWs.Cells(destRow, 3).HorizontalAlignment = xlCenter
    destWs.Cells(destRow, 3).VerticalAlignment = xlCenter

    destWs.Cells(destRow, 5).HorizontalAlignment = xlCenter
    destWs.Cells(destRow, 5).VerticalAlignment = xlCenter

    destWs.Cells(destRow, 7).HorizontalAlignment = xlCenter
    destWs.Cells(destRow, 7).VerticalAlignment = xlCenter

    destWs.Cells(destRow, 9).HorizontalAlignment = xlCenter
    destWs.Cells(destRow, 9).VerticalAlignment = xlCenter
End Sub

'------------------------------------------------------------------------------
' Procedure: ConfigureRemakePrintPageTemplate
' Scope: Private Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   ConfigureRemakePrintPageTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ConfigureRemakePrintPageTemplate(ByVal ws As Worksheet, ByVal lastPrintRow As Long)
    With ws.PageSetup
        .PrintArea = ws.Range("A1:K" & lastPrintRow).Address
        .Orientation = xlLandscape
        .PaperSize = xlPaperLetter
        .Zoom = False
        .FitToPagesWide = 1
        .FitToPagesTall = False
        .CenterHorizontally = True
        .CenterVertically = False
        .LeftMargin = Application.InchesToPoints(0.35)
        .RightMargin = Application.InchesToPoints(0.35)
        .TopMargin = Application.InchesToPoints(0.4)
        .BottomMargin = Application.InchesToPoints(0.4)
        .HeaderMargin = Application.InchesToPoints(0.2)
        .FooterMargin = Application.InchesToPoints(0.2)
        .CenterFooter = "Page &P of &N"
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: BuildAndPreviewRemakePrintFromTemplate
' Scope: Private Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   BuildAndPreviewRemakePrintFromTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub BuildAndPreviewRemakePrintFromTemplate(ByVal srcWs As Worksheet, _
                                                   ByVal sectionStartRow As Long, ByVal sectionEndRow As Long, _
                                                   ByVal firstDataRow As Long, ByVal lastRealRow As Long, _
                                                   ByVal orderCol As Long, ByVal itemCol As Long, _
                                                   ByVal destinationMode As String, _
                                                   ByVal selectedGlassKeys As String, _
                                                   Optional ByVal printKind As String = "REMAKES", _
                                                   Optional ByVal selectedAction As String = "PREVIEW", _
                                                   Optional ByVal selectedCopies As Long = 1)

    Dim templateWs As Worksheet
    Dim previewWs As Worksheet
    Dim prevSheet As Worksheet
    Dim qtyHdr As Range
    Dim dimHdr As Range
    Dim qtyCol As Long
    Dim dimCol As Long
    Dim scanStart As Long
    Dim scanEnd As Long
    Dim destRow As Long
    Dim r As Long
    Dim listDate As Date
    Dim currentSectionTitle As String
    Dim printedAnyInSection As Boolean
    Dim printedAnyRows As Boolean
    Dim oldDisplayAlerts As Boolean
    Dim oldScreenUpdating As Boolean
    Dim bodyLastRow As Long

    On Error GoTo ErrHandler

    Set qtyHdr = FindHeaderCellTemplate(srcWs, Array("Qty.", "Qty"))
    Set dimHdr = FindHeaderCellTemplate(srcWs, Array("Dimensions"))

    If qtyHdr Is Nothing Or dimHdr Is Nothing Then
        MsgBox "Could not find Qty. / Dimensions headers needed for remake printing.", vbExclamation, "Print Remakes"
        Exit Sub
    End If

    oldDisplayAlerts = Application.DisplayAlerts
    oldScreenUpdating = Application.ScreenUpdating
    Application.DisplayAlerts = False
    Application.ScreenUpdating = False

    Set prevSheet = ActiveSheet

    Set templateWs = ThisWorkbook.Worksheets(REMAKE_PRINT_TEMPLATE_SHEET)

    DeleteSheetIfExists ThisWorkbook, REMAKE_PRINT_PREVIEW_SHEET

    templateWs.Visible = xlSheetVisible
    templateWs.Copy After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count)
    Set previewWs = ActiveSheet
    previewWs.Name = REMAKE_PRINT_PREVIEW_SHEET
    templateWs.Visible = xlSheetVeryHidden

    On Error Resume Next
    previewWs.Unprotect Password:=""
    On Error GoTo ErrHandler

    listDate = GetDeliveryListDateForFileName(srcWs)
    If listDate > 0 Then
        previewWs.Range("A2").Value = REMAKE_TITLE_PREFIX & Format$(listDate, "m/d/yyyy")
    End If

    ApplyRemakePrintColumnHeadersTemplate previewWs

    bodyLastRow = GetLastUsedRowTemplate(previewWs)
    Dim bodyStartRow As Long

    bodyStartRow = GetRemakePrintBodyStartRowTemplate(previewWs)

    If bodyLastRow < bodyStartRow Then bodyLastRow = bodyStartRow

    RushClearTemplateBodyContents previewWs, bodyStartRow, bodyLastRow

    

    qtyCol = qtyHdr.Column
    dimCol = dimHdr.Column

    If sectionStartRow > 0 And sectionEndRow > 0 Then
        scanStart = sectionStartRow
        scanEnd = sectionEndRow
    Else
        scanStart = firstDataRow
        scanEnd = lastRealRow
    End If

    destRow = bodyStartRow
    currentSectionTitle = vbNullString
    printedAnyInSection = False
    printedAnyRows = False

    For r = scanStart To scanEnd
        If IsSectionHeaderRowTemplate(srcWs, r, orderCol, itemCol) Then
            currentSectionTitle = Trim$(CStr(srcWs.Cells(r, 1).Value))
            printedAnyInSection = False

        ElseIf IsRealDeliveryLineTemplate(srcWs, r, orderCol, itemCol) Then
    If DoesPrintModeMatchRowTemplate(srcWs, r, destinationMode, printKind) _
        And IsGlassSectionSelectedTemplate(currentSectionTitle, selectedGlassKeys) Then
        If Not printedAnyInSection And Len(currentSectionTitle) > 0 Then
            WriteRemakeSectionHeaderTemplate previewWs, destRow, currentSectionTitle
            WriteRemakeBlankSpacerTemplate previewWs, destRow + 1
            destRow = destRow + 2
            printedAnyInSection = True
        End If

        WriteRemakeLineTemplate srcWs, r, previewWs, destRow, orderCol, itemCol, qtyCol, dimCol
        destRow = destRow + 1
        printedAnyRows = True
    End If
End If
    Next r

    If Not printedAnyRows Then
        MsgBox "There are no remake rows to preview for " & GetDestinationLabel(destinationMode) & ".", _
               vbInformation, "Print Remakes"
        GoTo SafeExit
    End If

    ConfigureRemakePrintPageTemplate previewWs, destRow - 1

    previewWs.Activate
previewWs.Range("A1").Select

If UCase$(selectedAction) = "PRINT" Then
    If selectedCopies < 1 Then selectedCopies = 1
    previewWs.PrintOut Copies:=selectedCopies
Else
    previewWs.PrintPreview
End If
SafeExit:
    On Error Resume Next
    If Not prevSheet Is Nothing Then prevSheet.Activate
    If Not previewWs Is Nothing Then previewWs.Delete
    If Not templateWs Is Nothing Then templateWs.Visible = xlSheetVeryHidden
    Application.DisplayAlerts = oldDisplayAlerts
    Application.ScreenUpdating = oldScreenUpdating
    On Error GoTo 0
    Exit Sub

ErrHandler:
    MsgBox "BuildAndPreviewRemakePrintFromTemplate error " & Err.Number & ":" & vbCrLf & Err.Description, _
           vbCritical, "Print Remakes Error"
    Resume SafeExit
End Sub

'------------------------------------------------------------------------------
' Procedure: BuildAndPreviewRushPrintFromTemplate
'
' Uses the existing remake print template for rush orders.
' This is intentionally black-and-white friendly.
'
' Title becomes:
'   Rush Order Due m/d/yyyy
'
' It prints rows where AX = RUSH.
'------------------------------------------------------------------------------
Public Sub BuildAndPreviewRushPrintFromTemplate(ByVal selectedAction As String, _
                                                Optional ByVal selectedCopies As Long = 1)
    BuildAndPreviewRushPrintFromTemplateInternal Nothing, False, selectedAction, selectedCopies
End Sub

'------------------------------------------------------------------------------
' Procedure: BuildAndPreviewRushSelectedPrintFromTemplate
'
' Same as BuildAndPreviewRushPrintFromTemplate, but only prints selected
' Delivery List source rows from frmRushOrders.
'------------------------------------------------------------------------------
Public Sub BuildAndPreviewRushSelectedPrintFromTemplate(ByVal selectedRows As Collection, _
                                                        ByVal selectedAction As String, _
                                                        Optional ByVal selectedCopies As Long = 1)
    BuildAndPreviewRushPrintFromTemplateInternal selectedRows, True, selectedAction, selectedCopies
End Sub

'------------------------------------------------------------------------------
' Shared Rush print worker.
'------------------------------------------------------------------------------
Private Sub BuildAndPreviewRushPrintFromTemplateInternal(ByVal selectedRows As Collection, _
                                                         ByVal useSelectedRows As Boolean, _
                                                         ByVal selectedAction As String, _
                                                         ByVal selectedCopies As Long)
    Dim srcWs As Worksheet
    Dim templateWs As Worksheet
    Dim previewWs As Worksheet
    Dim prevSheet As Worksheet

    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim qtyHdr As Range
    Dim dimHdr As Range

    Dim orderCol As Long
    Dim itemCol As Long
    Dim qtyCol As Long
    Dim dimCol As Long

    Dim firstDataRow As Long
    Dim lastRealRow As Long
    Dim bodyStartRow As Long
    Dim bodyLastRow As Long
    Dim destRow As Long
    Dim r As Long

    Dim listDate As Date
    Dim currentSectionTitle As String
    Dim printedAnyInSection As Boolean
    Dim printedAnyRows As Boolean

    Dim oldDisplayAlerts As Boolean
    Dim oldScreenUpdating As Boolean

    On Error GoTo ErrHandler

    Set srcWs = ThisWorkbook.Worksheets("Delivery List")

    Set orderHdr = FindHeaderCellTemplateInCols(srcWs, Array("Order Nr."), "A:N", 250)
    Set itemHdr = FindHeaderCellTemplateInCols(srcWs, Array("Item Nr.", "Item"), "A:N", 250)
    Set qtyHdr = FindHeaderCellTemplate(srcWs, Array("Qty.", "Qty"))
    Set dimHdr = FindHeaderCellTemplate(srcWs, Array("Dimensions"))

    If orderHdr Is Nothing Or itemHdr Is Nothing Then
        MsgBox "Could not find Order Nr. / Item Nr. headers for Rush printing.", vbExclamation, "Rush Print"
        Exit Sub
    End If

    If qtyHdr Is Nothing Or dimHdr Is Nothing Then
        MsgBox "Could not find Qty. / Dimensions headers needed for Rush printing.", vbExclamation, "Rush Print"
        Exit Sub
    End If

    orderCol = orderHdr.Column
    itemCol = itemHdr.Column
    qtyCol = qtyHdr.Column
    dimCol = dimHdr.Column

    firstDataRow = orderHdr.Row + 1
    lastRealRow = FindLastRealDeliveryRowTemplate(srcWs, orderCol, itemCol, firstDataRow)

    If lastRealRow < firstDataRow Then
        MsgBox "No delivery rows were found to print.", vbInformation, "Rush Print"
        Exit Sub
    End If

    If selectedCopies < 1 Then selectedCopies = 1

    oldDisplayAlerts = Application.DisplayAlerts
    oldScreenUpdating = Application.ScreenUpdating

    Application.DisplayAlerts = False
    Application.ScreenUpdating = False

    Set prevSheet = ActiveSheet
    Set templateWs = ThisWorkbook.Worksheets(REMAKE_PRINT_TEMPLATE_SHEET)

    DeleteSheetIfExists ThisWorkbook, REMAKE_PRINT_PREVIEW_SHEET

    templateWs.Visible = xlSheetVisible
    templateWs.Copy After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count)

    Set previewWs = ActiveSheet
    previewWs.Name = REMAKE_PRINT_PREVIEW_SHEET

    templateWs.Visible = xlSheetVeryHidden

    On Error Resume Next
    previewWs.Unprotect Password:=""
    On Error GoTo ErrHandler

    listDate = GetDeliveryListDateForFileName(srcWs)

    'Clear old title cell content from the template area.
    RushClearMergedCellContents previewWs.Range("A2")

    'Write Rush header in a clean area to the right of the logo.
    WriteRushHeaderOnRemakeTemplate previewWs, listDate

    ApplyRemakePrintColumnHeadersTemplate previewWs

    bodyLastRow = GetLastUsedRowTemplate(previewWs)
    bodyStartRow = GetRemakePrintBodyStartRowTemplate(previewWs)

    If bodyLastRow < bodyStartRow Then bodyLastRow = bodyStartRow

    previewWs.Range("A" & bodyStartRow & ":M" & bodyLastRow).ClearContents

    destRow = bodyStartRow
    currentSectionTitle = vbNullString
    printedAnyInSection = False
    printedAnyRows = False

    For r = firstDataRow To lastRealRow
        If IsSectionHeaderRowTemplate(srcWs, r, orderCol, itemCol) Then
            currentSectionTitle = Trim$(CStr(srcWs.Cells(r, 1).Value))
            printedAnyInSection = False

        ElseIf IsRealDeliveryLineTemplate(srcWs, r, orderCol, itemCol) Then
            If RushTemplateShouldPrintRow(srcWs, r, selectedRows, useSelectedRows) Then

                If Not printedAnyInSection Then
                    If Len(Trim$(currentSectionTitle)) > 0 Then
                        WriteRemakeSectionHeaderTemplate previewWs, destRow, currentSectionTitle
                    Else
                        WriteRemakeSectionHeaderTemplate previewWs, destRow, "RUSH ORDERS"
                    End If

                    WriteRemakeBlankSpacerTemplate previewWs, destRow + 1
                    destRow = destRow + 2

                    printedAnyInSection = True
                End If

                WriteRemakeLineTemplate srcWs, r, previewWs, destRow, orderCol, itemCol, qtyCol, dimCol

                'Keep rush row bold, but remove the extra heavy borders.
                previewWs.Range("A" & destRow & ":K" & destRow).Font.Bold = True

                destRow = destRow + 1
                printedAnyRows = True
            End If
        End If
    Next r

    If Not printedAnyRows Then
        MsgBox "There are no Rush orders to print.", vbInformation, "Rush Print"
        GoTo SafeExit
    End If

    ConfigureRemakePrintPageTemplate previewWs, destRow - 1

    Application.DisplayAlerts = oldDisplayAlerts
    Application.ScreenUpdating = True

    previewWs.Activate
    previewWs.Range("A1").Select

    If UCase$(Trim$(selectedAction)) = "PRINT" Then
        previewWs.PrintOut Copies:=selectedCopies
    Else
        previewWs.PrintPreview
    End If

SafeExit:
    On Error Resume Next

    Application.DisplayAlerts = False

    If Not previewWs Is Nothing Then
        previewWs.Delete
    End If

    If Not prevSheet Is Nothing Then
        prevSheet.Activate
    End If

    Application.DisplayAlerts = oldDisplayAlerts
    Application.ScreenUpdating = oldScreenUpdating

    On Error GoTo 0
    Exit Sub

ErrHandler:
    MsgBox "Rush Print failed." & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, _
           vbExclamation, "Rush Print"

    Resume SafeExit
End Sub

'------------------------------------------------------------------------------
' Safely clears a single cell even when it is part of a merged range.
'------------------------------------------------------------------------------
Private Sub RushClearMergedCellContents(ByVal targetCell As Range)
    On Error Resume Next

    If targetCell Is Nothing Then Exit Sub

    If targetCell.MergeCells Then
        targetCell.MergeArea.ClearContents
    Else
        targetCell.ClearContents
    End If

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Safely clears the remake-template body area without triggering merged-cell
' runtime errors.
'
' Important:
'   Do not call Range("A:M").ClearContents on this template because some cells
'   may be merged. Excel can throw:
'       "We can't do that to a merged cell."
'------------------------------------------------------------------------------
Private Sub RushClearTemplateBodyContents(ByVal ws As Worksheet, _
                                          ByVal firstRow As Long, _
                                          ByVal lastRow As Long)
    Dim r As Long
    Dim c As Long
    Dim cell As Range
    Dim mergeKey As String
    Dim clearedMerges As Object

    If ws Is Nothing Then Exit Sub
    If firstRow <= 0 Then Exit Sub
    If lastRow < firstRow Then Exit Sub

    Set clearedMerges = CreateObject("Scripting.Dictionary")

    On Error Resume Next

    For r = firstRow To lastRow
        For c = 1 To 13   'A:M
            Set cell = ws.Cells(r, c)

            If cell.MergeCells Then
                mergeKey = cell.MergeArea.Address(False, False)

                If Not clearedMerges.Exists(mergeKey) Then
                    clearedMerges.Add mergeKey, True
                    cell.MergeArea.ClearContents
                End If
            Else
                cell.ClearContents
            End If
        Next c
    Next r

    On Error GoTo 0
End Sub
Private Sub WriteRushHeaderOnRemakeTemplate(ByVal ws As Worksheet, ByVal listDate As Date)
    Dim shpTitle As Shape
    Dim shpDate As Shape
    Dim dateText As String

    Dim logoRight As Double
    Dim titleAreaLeft As Double
    Dim titleAreaRight As Double
    Dim titleAreaWidth As Double

    Const TITLE_FONT_SIZE As Double = 42   '35% bigger than 24 pt
    Const DATE_FONT_SIZE As Double = 42
    Const TITLE_SHIFT_LEFT_PERCENT As Double = 0.1

    On Error Resume Next
    ws.Shapes("rushHeaderTitle").Delete
    ws.Shapes("rushHeaderDate").Delete
    ws.Shapes("rushHeaderUnderline").Delete
    On Error GoTo 0

    If listDate > 0 Then
        dateText = Format$(listDate, "m/d/yyyy")
    Else
        dateText = vbNullString
    End If

    'Logo is mostly in column A, about 65% across.
    'Start the title area slightly to the right of that logo.
    logoRight = ws.Columns("A").Left + (ws.Columns("A").Width * 0.7)

    titleAreaLeft = logoRight + 12
titleAreaRight = ws.Columns("M").Left + ws.Columns("M").Width
titleAreaWidth = titleAreaRight - titleAreaLeft

If titleAreaWidth < 250 Then
    titleAreaLeft = ws.Columns("B").Left
    titleAreaRight = ws.Columns("M").Left + ws.Columns("M").Width
    titleAreaWidth = titleAreaRight - titleAreaLeft
End If

'Move both title and date about 15% left while keeping them centered together.
titleAreaLeft = titleAreaLeft - (titleAreaWidth * TITLE_SHIFT_LEFT_PERCENT)

    'Main title centered between the logo and the right edge of the page.
    Set shpTitle = ws.Shapes.AddTextbox( _
                Orientation:=msoTextOrientationHorizontal, _
                Left:=titleAreaLeft, _
                Top:=16, _
                Width:=titleAreaWidth, _
                Height:=48)

    With shpTitle
        .Name = "rushHeaderTitle"
        .Line.Visible = msoFalse
        .Fill.Visible = msoFalse
        .Placement = xlMoveAndSize

        .TextFrame.Characters.Text = "RUSH ORDER DUE:"
        .TextFrame.HorizontalAlignment = xlHAlignCenter
        .TextFrame.VerticalAlignment = xlVAlignCenter
        .TextFrame.MarginLeft = 0
        .TextFrame.MarginRight = 0
        .TextFrame.MarginTop = 0
        .TextFrame.MarginBottom = 0

        With .TextFrame.Characters.Font
            .Name = "Bodoni MT Black"
            .Size = TITLE_FONT_SIZE
            .Bold = False
        End With
    End With

    'Date below the title, centered in the same open area.
    Set shpDate = ws.Shapes.AddTextbox( _
                   Orientation:=msoTextOrientationHorizontal, _
                   Left:=titleAreaLeft, _
                   Top:=58, _
                   Width:=titleAreaWidth, _
                   Height:=48)

    With shpDate
        .Name = "rushHeaderDate"
        .Line.Visible = msoFalse
        .Fill.Visible = msoFalse
        .Placement = xlMoveAndSize

        .TextFrame.Characters.Text = dateText
        .TextFrame.HorizontalAlignment = xlHAlignCenter
        .TextFrame.VerticalAlignment = xlVAlignCenter
        .TextFrame.MarginLeft = 0
        .TextFrame.MarginRight = 0
        .TextFrame.MarginTop = 0
        .TextFrame.MarginBottom = 0

        With .TextFrame.Characters.Font
            .Name = "Bodoni MT Black"
            .Size = DATE_FONT_SIZE
            .Bold = True
        End With
    End With
End Sub

'------------------------------------------------------------------------------
' Returns True when the source delivery row should print on the Rush sheet.
'------------------------------------------------------------------------------
Private Function RushTemplateShouldPrintRow(ByVal srcWs As Worksheet, _
                                            ByVal rowNum As Long, _
                                            ByVal selectedRows As Collection, _
                                            ByVal useSelectedRows As Boolean) As Boolean
    If srcWs Is Nothing Then Exit Function
    If rowNum <= 0 Then Exit Function

    If UCase$(Trim$(CStr(srcWs.Cells(rowNum, RUSH_STATUS_COL).Value))) <> RUSH_FLAG_TEXT Then
        Exit Function
    End If

    If useSelectedRows Then
        RushTemplateShouldPrintRow = RushTemplateCollectionContainsRow(selectedRows, rowNum)
    Else
        RushTemplateShouldPrintRow = True
    End If
End Function

'------------------------------------------------------------------------------
' Checks whether a source row is in the selected UserForm rows.
'------------------------------------------------------------------------------
Private Function RushTemplateCollectionContainsRow(ByVal selectedRows As Collection, _
                                                   ByVal rowNum As Long) As Boolean
    Dim v As Variant

    If selectedRows Is Nothing Then Exit Function

    For Each v In selectedRows
        If CLng(v) = rowNum Then
            RushTemplateCollectionContainsRow = True
            Exit Function
        End If
    Next v
End Function

'------------------------------------------------------------------------------
' Procedure: CleanLayoutTextTemplate
' Scope: Private Function
'
' What it does:
'   Cleans or normalizes text so comparisons, keys, and operator messages are
'   stable (CleanLayoutTextTemplate).
'
' Why it exists:
'   The workbook compares text from Excel, barcodes, SharePoint, and Power
'   Automate; normalization prevents small formatting differences from
'   breaking logic.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function CleanLayoutTextTemplate(ByVal v As Variant) As String
    Dim s As String

    s = CStr(v)
    s = Replace$(s, Chr$(160), " ")
    s = Application.WorksheetFunction.Clean(s)
    s = Application.WorksheetFunction.Trim(s)

    CleanLayoutTextTemplate = Trim$(s)
End Function

'------------------------------------------------------------------------------
' Procedure: MaxLongTemplate
' Scope: Private Function
'
' What it does:
'   Performs the workbook-specific step named MaxLongTemplate inside
'   TemplateImporter.
'
' Why it exists:
'   The master workbook uses this module to turn a raw delivery list into the
'   operational sheets used by scanning, printing, exports, and intake
'   snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function MaxLongTemplate(ByVal a As Long, ByVal b As Long) As Long
    If a > b Then
        MaxLongTemplate = a
    Else
        MaxLongTemplate = b
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: LastColOfRangeTemplate
' Scope: Private Function
'
' What it does:
'   Finds, sizes, hides, formats, or uses worksheet columns for
'   LastColOfRangeTemplate.
'
' Why it exists:
'   The system depends on fixed scan blocks and discovered delivery-list
'   columns, so column handling must be centralized and predictable.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function LastColOfRangeTemplate(ByVal rng As Range) As Long
    LastColOfRangeTemplate = rng.Column + rng.Columns.Count - 1
End Function

'------------------------------------------------------------------------------
' Procedure: UnmergeWholeUsedRangeSafeTemplate
' Scope: Private Sub
'
' What it does:
'   Performs the workbook-specific step named
'   UnmergeWholeUsedRangeSafeTemplate inside TemplateImporter.
'
' Why it exists:
'   The master workbook uses this module to turn a raw delivery list into the
'   operational sheets used by scanning, printing, exports, and intake
'   snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub UnmergeWholeUsedRangeSafeTemplate(ByVal ws As Worksheet)
    Dim rng As Range

    Set rng = GetWholeUsedRangeTemplate(ws)
    If rng Is Nothing Then Exit Sub

    UnmergeRangeSafeTemplate rng
End Sub

'------------------------------------------------------------------------------
' Procedure: GetWholeUsedRangeTemplate
' Scope: Private Function
'
' What it does:
'   Returns a workbook object, setting, status value, parsed value, or
'   calculated result used by other procedures (GetWholeUsedRangeTemplate).
'
' Why it exists:
'   Using one getter keeps callers from duplicating lookup logic and protects
'   them from missing sheets, missing names, or blank values.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetWholeUsedRangeTemplate(ByVal ws As Worksheet) As Range
    Dim rng As Range

    On Error Resume Next
    Set rng = ws.UsedRange
    On Error GoTo 0

    If rng Is Nothing Then
        Set rng = ws.Range("A1")
    End If

    Set GetWholeUsedRangeTemplate = rng
End Function

'------------------------------------------------------------------------------
' Procedure: FindHeaderCellAnywhereTemplate
' Scope: Private Function
'
' What it does:
'   Finds, writes, validates, or uses worksheet header cells for
'   FindHeaderCellAnywhereTemplate.
'
' Why it exists:
'   Header locations can move during import/rebuild, so the code uses header
'   discovery to target the correct columns instead of guessing.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function FindHeaderCellAnywhereTemplate(ByVal ws As Worksheet, ByVal names As Variant) As Range
    Dim searchRange As Range
    Dim nm As Variant
    Dim f As Range

    Set searchRange = GetWholeUsedRangeTemplate(ws)

    For Each nm In names
        Set f = searchRange.Find(What:=CStr(nm), After:=searchRange.Cells(searchRange.Cells.Count), _
                                 LookIn:=xlValues, LookAt:=xlWhole, _
                                 SearchOrder:=xlByRows, SearchDirection:=xlNext, _
                                 MatchCase:=False)
        If Not f Is Nothing Then
            Set FindHeaderCellAnywhereTemplate = f
            Exit Function
        End If
    Next nm

    For Each nm In names
        Set f = searchRange.Find(What:=CStr(nm), After:=searchRange.Cells(searchRange.Cells.Count), _
                                 LookIn:=xlValues, LookAt:=xlPart, _
                                 SearchOrder:=xlByRows, SearchDirection:=xlNext, _
                                 MatchCase:=False)
        If Not f Is Nothing Then
            Set FindHeaderCellAnywhereTemplate = f
            Exit Function
        End If
    Next nm

    For Each nm In names
        Set f = searchRange.Find(What:=CStr(nm), After:=searchRange.Cells(searchRange.Cells.Count), _
                                 LookIn:=xlFormulas, LookAt:=xlWhole, _
                                 SearchOrder:=xlByRows, SearchDirection:=xlNext, _
                                 MatchCase:=False)
        If Not f Is Nothing Then
            Set FindHeaderCellAnywhereTemplate = f
            Exit Function
        End If
    Next nm

    For Each nm In names
        Set f = searchRange.Find(What:=CStr(nm), After:=searchRange.Cells(searchRange.Cells.Count), _
                                 LookIn:=xlFormulas, LookAt:=xlPart, _
                                 SearchOrder:=xlByRows, SearchDirection:=xlNext, _
                                 MatchCase:=False)
        If Not f Is Nothing Then
            Set FindHeaderCellAnywhereTemplate = f
            Exit Function
        End If
    Next nm
End Function

'------------------------------------------------------------------------------
' Procedure: LastUsedColTemplate
' Scope: Private Function
'
' What it does:
'   Finds, sizes, hides, formats, or uses worksheet columns for
'   LastUsedColTemplate.
'
' Why it exists:
'   The system depends on fixed scan blocks and discovered delivery-list
'   columns, so column handling must be centralized and predictable.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function LastUsedColTemplate(ByVal ws As Worksheet) As Long
    Dim f As Range
    Set f = ws.Cells.Find(What:="*", LookIn:=xlFormulas, SearchOrder:=xlByColumns, SearchDirection:=xlPrevious)

    If f Is Nothing Then
        LastUsedColTemplate = 1
    Else
        LastUsedColTemplate = f.Column
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: ResolveSourceLayoutProfileTemplate
' Scope: Private Function
'
' What it does:
'   Performs the workbook-specific step named
'   ResolveSourceLayoutProfileTemplate inside TemplateImporter.
'
' Why it exists:
'   The master workbook uses this module to turn a raw delivery list into the
'   operational sheets used by scanning, printing, exports, and intake
'   snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function ResolveSourceLayoutProfileTemplate(ByVal ws As Worksheet) As SourceLayoutProfile
    Dim p As SourceLayoutProfile
    Dim hdrJob As Range
    Dim hdrOrder As Range
    Dim hdrItem As Range
    Dim hdrQty As Range
    Dim hdrDim As Range
    Dim hdrCust As Range
    Dim hdrRemake As Range
    Dim hdrRoute As Range

    Set hdrOrder = FindHeaderCellAnywhereTemplate(ws, Array("Order Nr.", "Order No.", "Order Number"))
    If hdrOrder Is Nothing Then
        ResolveSourceLayoutProfileTemplate = p
        Exit Function
    End If

    p.headerRow = hdrOrder.Row
    p.firstDataRow = p.headerRow + 1

    Set hdrJob = FindHeaderCellAnywhereTemplate(ws, Array("Job Nr.", "Job Number", "Job"))
    Set hdrItem = FindHeaderCellAnywhereTemplate(ws, Array("Item Nr.", "Item"))
    Set hdrQty = FindHeaderCellAnywhereTemplate(ws, Array("Qty.", "Qty", "Quantity"))
    Set hdrDim = FindHeaderCellAnywhereTemplate(ws, Array("Dimensions", "Dimension"))
    Set hdrCust = FindHeaderCellAnywhereTemplate(ws, Array("Customer"))
    Set hdrRemake = FindHeaderCellAnywhereTemplate(ws, Array("Remake", "RM"))
    Set hdrRoute = FindHeaderCellAnywhereTemplate(ws, Array("Route"))

    'Known newer source layout
    If hdrOrder.Column = KNOWN_SRC_ORDER_COL Then
    p.JobStartCol = KNOWN_SRC_JOB_START_COL
    p.JobEndCol = KNOWN_SRC_JOB_END_COL
    p.orderCol = KNOWN_SRC_ORDER_COL
    p.ItemStartCol = KNOWN_SRC_ITEM_START_COL
    p.ItemEndCol = KNOWN_SRC_ITEM_END_COL
    p.QtyStartCol = KNOWN_SRC_QTY_START_COL
    p.QtyEndCol = KNOWN_SRC_QTY_END_COL
    p.DimStartCol = KNOWN_SRC_DIM_START_COL
    p.DimEndCol = KNOWN_SRC_DIM_END_COL
    p.CustStartCol = KNOWN_SRC_CUST_START_COL
    p.CustEndCol = KNOWN_SRC_CUST_END_COL
    p.RemakeCol = KNOWN_SRC_REMAKE_COL

    'Route can now be merged W:X, so use the actual detected header position.
    If Not hdrRoute Is Nothing Then
        If hdrRoute.MergeCells Then
            p.routeCol = hdrRoute.MergeArea.Column
        Else
            p.routeCol = hdrRoute.Column
        End If
    Else
        p.routeCol = KNOWN_SRC_ROUTE_COL   'fallback only
    End If

    p.IsValid = True
    ResolveSourceLayoutProfileTemplate = p
    Exit Function
End If

    If Not hdrJob Is Nothing Then
        If hdrJob.MergeCells Then
            p.JobStartCol = hdrJob.MergeArea.Column
            p.JobEndCol = LastColOfRangeTemplate(hdrJob.MergeArea)
        Else
            p.JobStartCol = hdrJob.Column
            p.JobEndCol = hdrJob.Column
        End If
    Else
        p.JobStartCol = 1
        p.JobEndCol = MaxLongTemplate(1, hdrOrder.Column - 3)
    End If

    p.orderCol = hdrOrder.Column

    If Not hdrItem Is Nothing Then
        If hdrItem.MergeCells Then
            p.ItemStartCol = MaxLongTemplate(1, hdrItem.MergeArea.Column - 1)
            p.ItemEndCol = MaxLongTemplate(p.ItemStartCol, LastColOfRangeTemplate(hdrItem.MergeArea) - 1)
        Else
            p.ItemStartCol = MaxLongTemplate(1, hdrItem.Column - 1)
            p.ItemEndCol = hdrItem.Column
        End If
    End If

    If Not hdrQty Is Nothing Then
        If hdrQty.MergeCells Then
            p.QtyStartCol = hdrQty.MergeArea.Column
            p.QtyEndCol = LastColOfRangeTemplate(hdrQty.MergeArea)
        Else
            p.QtyStartCol = hdrQty.Column
            p.QtyEndCol = hdrQty.Column
        End If
    End If

    If Not hdrDim Is Nothing Then
        If hdrDim.MergeCells Then
            p.DimStartCol = hdrDim.MergeArea.Column
            p.DimEndCol = LastColOfRangeTemplate(hdrDim.MergeArea)
        Else
            p.DimStartCol = hdrDim.Column
            p.DimEndCol = hdrDim.Column
        End If
    End If

    If Not hdrCust Is Nothing Then
        If hdrCust.MergeCells Then
            p.CustStartCol = hdrCust.MergeArea.Column
            p.CustEndCol = LastColOfRangeTemplate(hdrCust.MergeArea)
        Else
            p.CustStartCol = hdrCust.Column
            p.CustEndCol = hdrCust.Column
        End If
    End If

    If Not hdrRemake Is Nothing Then
        If hdrRemake.MergeCells Then
            p.RemakeCol = hdrRemake.MergeArea.Column
        Else
            p.RemakeCol = hdrRemake.Column
        End If
    End If

    If Not hdrRoute Is Nothing Then
        If hdrRoute.MergeCells Then
            p.routeCol = hdrRoute.MergeArea.Column
        Else
            p.routeCol = hdrRoute.Column
        End If
    End If

    p.IsValid = (p.orderCol > 0 And p.ItemEndCol >= p.ItemStartCol)
    ResolveSourceLayoutProfileTemplate = p
End Function

'------------------------------------------------------------------------------
' Procedure: GetFirstNonBlankTextFromColsTemplate
' Scope: Private Function
'
' What it does:
'   Finds, sizes, hides, formats, or uses worksheet columns for
'   GetFirstNonBlankTextFromColsTemplate.
'
' Why it exists:
'   The system depends on fixed scan blocks and discovered delivery-list
'   columns, so column handling must be centralized and predictable.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetFirstNonBlankTextFromColsTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, _
                                                      ByVal firstCol As Long, ByVal lastCol As Long) As String
    Dim c As Long
    Dim s As String

    If firstCol <= 0 Or lastCol < firstCol Then Exit Function

    For c = firstCol To lastCol
        s = CleanLayoutTextTemplate(ws.Cells(rowNum, c).Value)
        If Len(s) > 0 Then
            GetFirstNonBlankTextFromColsTemplate = s
            Exit Function
        End If
    Next c
End Function

'------------------------------------------------------------------------------
' Procedure: JoinUniqueNonBlankTextFromColsTemplate
' Scope: Private Function
'
' What it does:
'   Finds, sizes, hides, formats, or uses worksheet columns for
'   JoinUniqueNonBlankTextFromColsTemplate.
'
' Why it exists:
'   The system depends on fixed scan blocks and discovered delivery-list
'   columns, so column handling must be centralized and predictable.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function JoinUniqueNonBlankTextFromColsTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, _
                                                        ByVal firstCol As Long, ByVal lastCol As Long, _
                                                        Optional ByVal delim As String = " ") As String
    Dim c As Long
    Dim s As String
    Dim outText As String

    If firstCol <= 0 Or lastCol < firstCol Then Exit Function

    For c = firstCol To lastCol
        s = CleanLayoutTextTemplate(ws.Cells(rowNum, c).Value)
        If Len(s) > 0 Then
            If Len(outText) = 0 Then
                outText = s
            ElseIf InStr(1, outText, s, vbTextCompare) = 0 Then
                outText = outText & delim & s
            End If
        End If
    Next c

    JoinUniqueNonBlankTextFromColsTemplate = outText
End Function

'------------------------------------------------------------------------------
' Procedure: GetSourceJobTextByProfileTemplate
' Scope: Private Function
'
' What it does:
'   Returns a workbook object, setting, status value, parsed value, or
'   calculated result used by other procedures
'   (GetSourceJobTextByProfileTemplate).
'
' Why it exists:
'   Using one getter keeps callers from duplicating lookup logic and protects
'   them from missing sheets, missing names, or blank values.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetSourceJobTextByProfileTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, _
                                                   ByRef p As SourceLayoutProfile) As String
    GetSourceJobTextByProfileTemplate = JoinUniqueNonBlankTextFromColsTemplate(ws, rowNum, p.JobStartCol, p.JobEndCol, " ")
End Function

'------------------------------------------------------------------------------
' Procedure: GetSourceOrderTextByProfileTemplate
' Scope: Private Function
'
' What it does:
'   Returns a workbook object, setting, status value, parsed value, or
'   calculated result used by other procedures
'   (GetSourceOrderTextByProfileTemplate).
'
' Why it exists:
'   Using one getter keeps callers from duplicating lookup logic and protects
'   them from missing sheets, missing names, or blank values.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetSourceOrderTextByProfileTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, _
                                                     ByRef p As SourceLayoutProfile) As String
    GetSourceOrderTextByProfileTemplate = CleanLayoutTextTemplate(ws.Cells(rowNum, p.orderCol).Value)
End Function

'------------------------------------------------------------------------------
' Procedure: GetSourceItemTextByProfileTemplate
' Scope: Private Function
'
' What it does:
'   Returns a workbook object, setting, status value, parsed value, or
'   calculated result used by other procedures
'   (GetSourceItemTextByProfileTemplate).
'
' Why it exists:
'   Using one getter keeps callers from duplicating lookup logic and protects
'   them from missing sheets, missing names, or blank values.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetSourceItemTextByProfileTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, _
                                                    ByRef p As SourceLayoutProfile) As String
    Dim c As Long
    Dim s As String
    Dim ordTxt As String

    ordTxt = GetSourceOrderTextByProfileTemplate(ws, rowNum, p)

    'Pass 1: work right-to-left and prefer a value that is NOT the order number
    For c = p.ItemEndCol To p.ItemStartCol Step -1
        s = CleanLayoutTextTemplate(ws.Cells(rowNum, c).Value)
        If Len(s) > 0 Then
            If Len(ordTxt) = 0 Or StrComp(s, ordTxt, vbTextCompare) <> 0 Then
                GetSourceItemTextByProfileTemplate = s
                Exit Function
            End If
        End If
    Next c

    'Pass 2: if every candidate matched order or only one value exists, take the rightmost nonblank
    For c = p.ItemEndCol To p.ItemStartCol Step -1
        s = CleanLayoutTextTemplate(ws.Cells(rowNum, c).Value)
        If Len(s) > 0 Then
            GetSourceItemTextByProfileTemplate = s
            Exit Function
        End If
    Next c
End Function

'------------------------------------------------------------------------------
' Procedure: GetSourceQtyValueByProfileTemplate
' Scope: Private Function
'
' What it does:
'   Reads, caps, validates, compares, or formats quantity values for
'   GetSourceQtyValueByProfileTemplate.
'
' Why it exists:
'   Quantity rules prevent over-scanning and keep staged, outbound, and
'   received counts aligned with the required delivery quantity.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetSourceQtyValueByProfileTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, _
                                                    ByRef p As SourceLayoutProfile) As Variant
    Dim c As Long
    Dim v As Variant

    If p.QtyStartCol <= 0 Or p.QtyEndCol < p.QtyStartCol Then
        GetSourceQtyValueByProfileTemplate = vbNullString
        Exit Function
    End If

    For c = p.QtyStartCol To p.QtyEndCol
        v = ws.Cells(rowNum, c).Value
        If Len(Trim$(CStr(v))) > 0 Then
            GetSourceQtyValueByProfileTemplate = v
            Exit Function
        End If
    Next c

    GetSourceQtyValueByProfileTemplate = vbNullString
End Function

'------------------------------------------------------------------------------
' Procedure: GetSourceDimensionsTextByProfileTemplate
' Scope: Private Function
'
' What it does:
'   Returns a workbook object, setting, status value, parsed value, or
'   calculated result used by other procedures
'   (GetSourceDimensionsTextByProfileTemplate).
'
' Why it exists:
'   Using one getter keeps callers from duplicating lookup logic and protects
'   them from missing sheets, missing names, or blank values.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetSourceDimensionsTextByProfileTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, _
                                                          ByRef p As SourceLayoutProfile) As String
    Dim d1 As String
    Dim d2 As String

    d1 = GetFirstNonBlankTextFromColsTemplate(ws, rowNum, p.DimStartCol, p.DimStartCol)
    d2 = GetFirstNonBlankTextFromColsTemplate(ws, rowNum, p.DimEndCol, p.DimEndCol)

    If Len(d1) > 0 And Len(d2) > 0 Then
        If StrComp(d1, d2, vbTextCompare) = 0 Then
            GetSourceDimensionsTextByProfileTemplate = d1
        Else
            GetSourceDimensionsTextByProfileTemplate = d1 & " x " & d2
        End If
    ElseIf Len(d1) > 0 Then
        GetSourceDimensionsTextByProfileTemplate = d1
    Else
        GetSourceDimensionsTextByProfileTemplate = d2
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: GetSourceCustomerTextByProfileTemplate
' Scope: Private Function
'
' What it does:
'   Returns a workbook object, setting, status value, parsed value, or
'   calculated result used by other procedures
'   (GetSourceCustomerTextByProfileTemplate).
'
' Why it exists:
'   Using one getter keeps callers from duplicating lookup logic and protects
'   them from missing sheets, missing names, or blank values.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetSourceCustomerTextByProfileTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, _
                                                        ByRef p As SourceLayoutProfile) As String
    GetSourceCustomerTextByProfileTemplate = JoinUniqueNonBlankTextFromColsTemplate(ws, rowNum, p.CustStartCol, p.CustEndCol, " ")
End Function

'------------------------------------------------------------------------------
' Procedure: IsSourceSectionHeaderByProfileTemplate
' Scope: Private Function
'
' What it does:
'   Finds, writes, validates, or uses worksheet header cells for
'   IsSourceSectionHeaderByProfileTemplate.
'
' Why it exists:
'   Header locations can move during import/rebuild, so the code uses header
'   discovery to target the correct columns instead of guessing.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function IsSourceSectionHeaderByProfileTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, _
                                                        ByRef p As SourceLayoutProfile) As Boolean
    Dim leftTxt As String
    Dim ordTxt As String
    Dim itemTxt As String

    leftTxt = CleanLayoutTextTemplate(ws.Cells(rowNum, 1).Value)
    ordTxt = GetSourceOrderTextByProfileTemplate(ws, rowNum, p)
    itemTxt = GetSourceItemTextByProfileTemplate(ws, rowNum, p)

    IsSourceSectionHeaderByProfileTemplate = (Len(leftTxt) > 0 And Len(ordTxt) = 0 And Len(itemTxt) = 0)
End Function

'------------------------------------------------------------------------------
' Procedure: IsSourceRealRowByProfileTemplate
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   IsSourceRealRowByProfileTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function IsSourceRealRowByProfileTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, _
                                                  ByRef p As SourceLayoutProfile) As Boolean
    IsSourceRealRowByProfileTemplate = _
        (Len(GetSourceOrderTextByProfileTemplate(ws, rowNum, p)) > 0 Or _
         Len(GetSourceItemTextByProfileTemplate(ws, rowNum, p)) > 0)
End Function

'------------------------------------------------------------------------------
' Procedure: BuildSourceDeliveryLineKeyByProfileTemplate
' Scope: Private Function
'
' What it does:
'   Builds a derived value, key, JSON block, layout, collection, or workbook
'   object used later by the workflow
'   (BuildSourceDeliveryLineKeyByProfileTemplate).
'
' Why it exists:
'   The project uses generated keys/layouts to keep repeated logic consistent
'   instead of hand-building values in multiple places.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BuildSourceDeliveryLineKeyByProfileTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, _
                                                             ByVal sectionKey As String, ByVal importKind As String, _
                                                             ByRef p As SourceLayoutProfile) As String
    Dim ordTxt As String
    Dim itemTxt As String
    Dim routeKey As String

    ordTxt = GetSourceOrderTextByProfileTemplate(ws, rowNum, p)
    itemTxt = GetSourceItemTextByProfileTemplate(ws, rowNum, p)

    If IsNumeric(itemTxt) Then
        itemTxt = Format$(CLng(Val(itemTxt)), "000")
    End If

    routeKey = NormalizeRouteKeyForUpdateTemplate(GetBestSourceRouteByProfileTemplate(ws, rowNum, p))

    If Len(routeKey) = 0 Then routeKey = "__NOROUTE__"

    BuildSourceDeliveryLineKeyByProfileTemplate = UCase$(Trim$(importKind)) & "|" & _
                                                  UCase$(Trim$(routeKey)) & "|" & _
                                                  NormalizeSectionKey(sectionKey) & "|" & _
                                                  ordTxt & "|" & itemTxt
End Function

'------------------------------------------------------------------------------
' Procedure: ResetSystemColumnsForRowTemplate
' Scope: Private Sub
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   ResetSystemColumnsForRowTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ResetSystemColumnsForRowTemplate(ByVal ws As Worksheet, ByVal rowNum As Long)
    UnmergeRangeSafeTemplate ws.Range("K" & rowNum & ":N" & rowNum)

    With ws.Range("K" & rowNum & ":N" & rowNum)
        .ClearContents
        .Interior.Pattern = xlNone
        .Font.Bold = False
        .Font.Italic = False
        .Font.Underline = xlUnderlineStyleNone
        .Font.Strikethrough = False
        .Font.ColorIndex = xlAutomatic
        .Borders.LineStyle = xlNone
        .HorizontalAlignment = xlLeft
        .VerticalAlignment = xlCenter
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: MapSourceRowToDeliveryListByProfileTemplate
' Scope: Private Sub
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   MapSourceRowToDeliveryListByProfileTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub MapSourceRowToDeliveryListByProfileTemplate(ByVal srcWs As Worksheet, ByVal srcRow As Long, _
                                                        ByVal destWs As Worksheet, ByVal destRow As Long, _
                                                        ByRef p As SourceLayoutProfile, _
                                                        Optional ByVal isSectionHeader As Boolean = False)
    Dim jobTxt As String
    Dim ordTxt As String
    Dim itemTxt As String
    Dim qtyVal As Variant
    Dim dimTxt As String
    Dim custTxt As String
    Dim routeTxt As String
    Dim makeRemake As Boolean
    Dim sectionText As String

    sectionText = CleanLayoutTextTemplate(srcWs.Cells(srcRow, 1).Value)
    jobTxt = GetSourceJobTextByProfileTemplate(srcWs, srcRow, p)
    ordTxt = GetSourceOrderTextByProfileTemplate(srcWs, srcRow, p)
    itemTxt = GetSourceItemTextByProfileTemplate(srcWs, srcRow, p)
    qtyVal = GetSourceQtyValueByProfileTemplate(srcWs, srcRow, p)
    dimTxt = GetSourceDimensionsTextByProfileTemplate(srcWs, srcRow, p)
    custTxt = GetSourceCustomerTextByProfileTemplate(srcWs, srcRow, p)

    routeTxt = GetBestSourceRouteByProfileTemplate(srcWs, srcRow, p)

    makeRemake = RowHasImportedRemakeFlagTemplate(srcWs, srcRow, p.RemakeCol)

    UnmergeRangeSafeTemplate destWs.Range("A" & destRow & ":N" & destRow)
    destWs.Range("A" & destRow & ":N" & destRow).ClearContents

    If isSectionHeader Then
        destWs.Cells(destRow, 1).Value = sectionText
    Else
        destWs.Cells(destRow, 1).Value = jobTxt
        destWs.Cells(destRow, 5).Value = ordTxt

        If Len(itemTxt) > 0 Then
            If IsNumeric(itemTxt) Then
                destWs.Cells(destRow, 6).Value = Format$(CLng(Val(itemTxt)), "000")
            Else
                destWs.Cells(destRow, 6).Value = itemTxt
            End If
        End If

        destWs.Cells(destRow, 7).Value = qtyVal
        destWs.Cells(destRow, 8).Value = dimTxt
        destWs.Cells(destRow, 9).Value = custTxt
        destWs.Cells(destRow, 5).HorizontalAlignment = xlCenter   'Order Nr.
        destWs.Cells(destRow, 5).VerticalAlignment = xlCenter

        destWs.Cells(destRow, 6).HorizontalAlignment = xlCenter   'Item Nr.
        destWs.Cells(destRow, 6).VerticalAlignment = xlCenter

        destWs.Cells(destRow, 7).HorizontalAlignment = xlCenter   'Qty.
        destWs.Cells(destRow, 7).VerticalAlignment = xlCenter

        If makeRemake Then
            destWs.Cells(destRow, REMAKE_MARKER_COL_FIXED).Value = REMAKE_MARKER_TEXT
        Else
            destWs.Cells(destRow, REMAKE_MARKER_COL_FIXED).ClearContents
        End If

        destWs.Cells(destRow, ROUTE_COL_FIXED).Value = routeTxt
    End If

    destWs.Cells(destRow, PROCESS_STATE_COL_FIXED).ClearContents
    destWs.Cells(destRow, 14).ClearContents

    NormalizeMergedDisplayColumnsForRowTemplate destWs, destRow
End Sub

'------------------------------------------------------------------------------
' Procedure: GetImportedSourceRemakeColTemplate
' Scope: Private Function
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   GetImportedSourceRemakeColTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetImportedSourceRemakeColTemplate(ByVal ws As Worksheet) As Long
    Dim p As SourceLayoutProfile
    p = ResolveSourceLayoutProfileTemplate(ws)
    GetImportedSourceRemakeColTemplate = p.RemakeCol
End Function

'------------------------------------------------------------------------------
' Procedure: GetImportedSourceRouteColTemplate
' Scope: Private Function
'
' What it does:
'   Finds, sizes, hides, formats, or uses worksheet columns for
'   GetImportedSourceRouteColTemplate.
'
' Why it exists:
'   The system depends on fixed scan blocks and discovered delivery-list
'   columns, so column handling must be centralized and predictable.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetImportedSourceRouteColTemplate(ByVal ws As Worksheet) As Long
    Dim p As SourceLayoutProfile
    p = ResolveSourceLayoutProfileTemplate(ws)
    GetImportedSourceRouteColTemplate = p.routeCol
End Function

'------------------------------------------------------------------------------
' Procedure: CleanRouteCandidateTemplate
' Scope: Private Function
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   CleanRouteCandidateTemplate.
'
' Why it exists:
'   Delivery timing, queue timestamps, and scan timestamps drive status
'   messages such as Early, On-Time, Late, Processing, and Done.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function CleanRouteCandidateTemplate(ByVal v As Variant) As String
    Dim s As String

    s = UCase$(CleanLayoutTextTemplate(v))

    Select Case s
        Case "CPU", _
             "CUSTOMER PICKUP", _
             "CUSTOMER PICK-UP", _
             "CUST PICKUP", _
             "CUST PICK-UP", _
             "CUSTOMERPICKUP"
            CleanRouteCandidateTemplate = CPU_ROUTE_TEXT

        Case Else
            CleanRouteCandidateTemplate = vbNullString
    End Select
End Function

'------------------------------------------------------------------------------
' Procedure: NormalizeRouteKeyForUpdateTemplate
' Scope: Private Function
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   NormalizeRouteKeyForUpdateTemplate.
'
' Why it exists:
'   Remakes need separate visual and print/export handling so replacement
'   glass is not confused with regular delivery-list work.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function NormalizeRouteKeyForUpdateTemplate(ByVal v As Variant) As String
    Dim s As String

    s = CleanRouteCandidateTemplate(v)

    If Len(s) = 0 Then
        NormalizeRouteKeyForUpdateTemplate = "__NOROUTE__"
    Else
        NormalizeRouteKeyForUpdateTemplate = UCase$(Trim$(s))
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: BuildDeliveryIdentityKeyWithKindTemplate
' Scope: Private Function
'
' What it does:
'   Builds a derived value, key, JSON block, layout, collection, or workbook
'   object used later by the workflow
'   (BuildDeliveryIdentityKeyWithKindTemplate).
'
' Why it exists:
'   The project uses generated keys/layouts to keep repeated logic consistent
'   instead of hand-building values in multiple places.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BuildDeliveryIdentityKeyWithKindTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, _
                                                          ByVal sectionKey As String, ByVal orderCol As Long, _
                                                          ByVal itemCol As Long, ByVal importKind As String) As String
    Dim ordTxt As String
    Dim itemTxt As String

    ordTxt = Trim$(CStr(ws.Cells(rowNum, orderCol).Value))

    If IsNumeric(ws.Cells(rowNum, itemCol).Value) Then
        itemTxt = Format$(CLng(Val(ws.Cells(rowNum, itemCol).Value)), "000")
    Else
        itemTxt = Trim$(CStr(ws.Cells(rowNum, itemCol).Value))
    End If

    BuildDeliveryIdentityKeyWithKindTemplate = UCase$(Trim$(importKind)) & "|" & _
                                               NormalizeSectionKey(sectionKey) & "|" & _
                                               ordTxt & "|" & itemTxt
End Function

'------------------------------------------------------------------------------
' Procedure: BuildCurrentDeliveryIdentityKeyWithKindTemplate
' Scope: Private Function
'
' What it does:
'   Builds a derived value, key, JSON block, layout, collection, or workbook
'   object used later by the workflow
'   (BuildCurrentDeliveryIdentityKeyWithKindTemplate).
'
' Why it exists:
'   The project uses generated keys/layouts to keep repeated logic consistent
'   instead of hand-building values in multiple places.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BuildCurrentDeliveryIdentityKeyWithKindTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, _
                                                                 ByVal sectionKey As String, ByVal orderCol As Long, _
                                                                 ByVal itemCol As Long) As String
    Dim rowKind As String

    rowKind = GetRowImportKindTemplate(ws, rowNum)

    BuildCurrentDeliveryIdentityKeyWithKindTemplate = _
        BuildDeliveryIdentityKeyWithKindTemplate(ws, rowNum, sectionKey, orderCol, itemCol, rowKind)
End Function

'------------------------------------------------------------------------------
' Procedure: BuildSourceDeliveryIdentityKeyByProfileTemplate
' Scope: Private Function
'
' What it does:
'   Builds a derived value, key, JSON block, layout, collection, or workbook
'   object used later by the workflow
'   (BuildSourceDeliveryIdentityKeyByProfileTemplate).
'
' Why it exists:
'   The project uses generated keys/layouts to keep repeated logic consistent
'   instead of hand-building values in multiple places.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BuildSourceDeliveryIdentityKeyByProfileTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, _
                                                                 ByVal sectionKey As String, ByVal importKind As String, _
                                                                 ByRef p As SourceLayoutProfile) As String
    Dim ordTxt As String
    Dim itemTxt As String

    ordTxt = GetSourceOrderTextByProfileTemplate(ws, rowNum, p)
    itemTxt = GetSourceItemTextByProfileTemplate(ws, rowNum, p)

    If IsNumeric(itemTxt) Then
        itemTxt = Format$(CLng(Val(itemTxt)), "000")
    End If

    BuildSourceDeliveryIdentityKeyByProfileTemplate = UCase$(Trim$(importKind)) & "|" & _
                                                      NormalizeSectionKey(sectionKey) & "|" & _
                                                      ordTxt & "|" & itemTxt
End Function

'------------------------------------------------------------------------------
' Procedure: BuildExistingDeliveryRowIndexByIdentityWithKindTemplate
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   BuildExistingDeliveryRowIndexByIdentityWithKindTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BuildExistingDeliveryRowIndexByIdentityWithKindTemplate(ByVal ws As Worksheet, ByVal firstDataRow As Long, _
                                                                         ByVal orderCol As Long, ByVal itemCol As Long) As Object
    Dim dict As Object
    Dim lastRealRow As Long
    Dim currentSectionKey As String
    Dim rowKey As String
    Dim r As Long

    Set dict = CreateObject("Scripting.Dictionary")
    lastRealRow = FindLastRealDeliveryRowTemplate(ws, orderCol, itemCol, firstDataRow)
    currentSectionKey = vbNullString

    For r = firstDataRow To lastRealRow
        If IsSectionHeaderRowTemplate(ws, r, orderCol, itemCol) Then
            currentSectionKey = NormalizeSectionKey(CStr(ws.Cells(r, 1).Value))

        ElseIf IsRealDeliveryLineTemplate(ws, r, orderCol, itemCol) Then
            If Len(currentSectionKey) = 0 Then currentSectionKey = "__UNSECTIONED__"

            rowKey = BuildCurrentDeliveryIdentityKeyWithKindTemplate(ws, r, currentSectionKey, orderCol, itemCol)

            If Not dict.Exists(rowKey) Then
                dict.Add rowKey, CLng(r)
            End If
        End If
    Next r

    Set BuildExistingDeliveryRowIndexByIdentityWithKindTemplate = dict
End Function

'------------------------------------------------------------------------------
' Procedure: SyncSourceRowToExistingDeliveryRowTemplate
' Scope: Private Sub
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   SyncSourceRowToExistingDeliveryRowTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub SyncSourceRowToExistingDeliveryRowTemplate(ByVal srcWs As Worksheet, ByVal srcRow As Long, _
                                                       ByVal destWs As Worksheet, ByVal destRow As Long, _
                                                       ByRef p As SourceLayoutProfile, ByVal rowImportKind As String)
    'Existing row: preserve any scans/comments already on the main Delivery List
    CopySourceRowIntoDestination srcWs, srcRow, destWs, destRow, False, True
    NormalizeImportedRowToNewLayoutTemplate destWs, destRow, False, (UCase$(Trim$(rowImportKind)) = "REMAKE")
    ApplyDeliveryListRowStyleTemplate destWs, destRow, False
End Sub

'------------------------------------------------------------------------------
' Procedure: GetCellValueSafeTemplate
' Scope: Private Function
'
' What it does:
'   Returns a workbook object, setting, status value, parsed value, or
'   calculated result used by other procedures (GetCellValueSafeTemplate).
'
' Why it exists:
'   Using one getter keeps callers from duplicating lookup logic and protects
'   them from missing sheets, missing names, or blank values.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetCellValueSafeTemplate(ByVal c As Range) As Variant
    If c Is Nothing Then Exit Function

    On Error Resume Next
    If c.MergeCells Then
        GetCellValueSafeTemplate = c.MergeArea.Cells(1, 1).Value
    Else
        GetCellValueSafeTemplate = c.Value
    End If
    On Error GoTo 0
End Function

'------------------------------------------------------------------------------
' Procedure: FindDynamicRouteForRowTemplate
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   FindDynamicRouteForRowTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function FindDynamicRouteForRowTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, _
                                                Optional ByVal sourceRouteCol As Long = 0) As String
    Dim lastCol As Long
    Dim c As Long
    Dim txt As String
    Dim currentRoute As String
    Dim legacyRoute As String

    If ws Is Nothing Then Exit Function
    If rowNum < 1 Then Exit Function

    If sourceRouteCol = 0 Then sourceRouteCol = GetImportedSourceRouteColTemplate(ws)
    lastCol = LastUsedColTemplate(ws)
    If lastCol < 1 Then lastCol = 1

    'Check the detected route cell first
    If sourceRouteCol > 0 And sourceRouteCol <= lastCol Then
        txt = CleanRouteCandidateTemplate(GetCellValueSafeTemplate(ws.Cells(rowNum, sourceRouteCol)))
        If Len(txt) > 0 Then
            FindDynamicRouteForRowTemplate = txt
            Exit Function
        End If
    End If

    'Then check one column to the LEFT (common for W:X situations)
    If sourceRouteCol > 1 Then
        txt = CleanRouteCandidateTemplate(GetCellValueSafeTemplate(ws.Cells(rowNum, sourceRouteCol - 1)))
        If Len(txt) > 0 Then
            FindDynamicRouteForRowTemplate = txt
            Exit Function
        End If
    End If

    'Then check one column to the RIGHT just in case
    If sourceRouteCol > 0 And sourceRouteCol < lastCol Then
        txt = CleanRouteCandidateTemplate(GetCellValueSafeTemplate(ws.Cells(rowNum, sourceRouteCol + 1)))
        If Len(txt) > 0 Then
            FindDynamicRouteForRowTemplate = txt
            Exit Function
        End If
    End If

    'Small fallback only in the normal remake/route band
    For c = 22 To 26   'V:Z
        If c <= lastCol Then
            txt = CleanRouteCandidateTemplate(GetCellValueSafeTemplate(ws.Cells(rowNum, c)))
            If Len(txt) > 0 Then
                FindDynamicRouteForRowTemplate = txt
                Exit Function
            End If
        End If
    Next c

    'Final fallback to already-normalized/current route cells
    currentRoute = CleanRouteCandidateTemplate(GetCellValueSafeTemplate(ws.Cells(rowNum, ROUTE_COL_FIXED)))
    legacyRoute = CleanRouteCandidateTemplate(GetCellValueSafeTemplate(ws.Cells(rowNum, LEGACY_ROUTE_COL_FIXED)))

    If Len(currentRoute) > 0 Then
        FindDynamicRouteForRowTemplate = currentRoute
    ElseIf Len(legacyRoute) > 0 Then
        FindDynamicRouteForRowTemplate = legacyRoute
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: GetBestSourceRouteByProfileTemplate
' Scope: Private Function
'
' What it does:
'   Returns a workbook object, setting, status value, parsed value, or
'   calculated result used by other procedures
'   (GetBestSourceRouteByProfileTemplate).
'
' Why it exists:
'   Using one getter keeps callers from duplicating lookup logic and protects
'   them from missing sheets, missing names, or blank values.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetBestSourceRouteByProfileTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, _
                                                     ByRef p As SourceLayoutProfile) As String
    'Route must be line-specific only.
    'Do NOT inherit CPU from earlier rows in the same order/job block.
    GetBestSourceRouteByProfileTemplate = FindDynamicRouteForRowTemplate(ws, rowNum, p.routeCol)
End Function

'------------------------------------------------------------------------------
' Procedure: RowHasImportedRemakeFlagTemplate
' Scope: Private Function
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   RowHasImportedRemakeFlagTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function RowHasImportedRemakeFlagTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, _
                                                  Optional ByVal sourceRemakeCol As Long = 0) As Boolean
    If sourceRemakeCol = 0 Then sourceRemakeCol = GetImportedSourceRemakeColTemplate(ws)

    If sourceRemakeCol > 0 Then
        RowHasImportedRemakeFlagTemplate = IsRemakeMarkerValueTemplate(ws.Cells(rowNum, sourceRemakeCol).Value)
    End If

    If Not RowHasImportedRemakeFlagTemplate Then
        RowHasImportedRemakeFlagTemplate = _
            IsRemakeMarkerValueTemplate(ws.Cells(rowNum, REMAKE_MARKER_COL_FIXED).Value) Or _
            IsRemakeMarkerValueTemplate(ws.Cells(rowNum, LEGACY_REMAKE_MARKER_COL_FIXED).Value)
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: GetSourceRowImportKindTemplate
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   GetSourceRowImportKindTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetSourceRowImportKindTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, _
                                                ByVal defaultKind As String, _
                                                Optional ByVal sourceRemakeCol As Long = 0) As String
    If UCase$(Trim$(defaultKind)) = "REMAKE" Then
        GetSourceRowImportKindTemplate = "REMAKE"
    ElseIf RowHasImportedRemakeFlagTemplate(ws, rowNum, sourceRemakeCol) Then
        GetSourceRowImportKindTemplate = "REMAKE"
    Else
        GetSourceRowImportKindTemplate = "REGULAR"
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: GetBestImportedRouteTemplate
' Scope: Private Function
'
' What it does:
'   Returns a workbook object, setting, status value, parsed value, or
'   calculated result used by other procedures (GetBestImportedRouteTemplate).
'
' Why it exists:
'   Using one getter keeps callers from duplicating lookup logic and protects
'   them from missing sheets, missing names, or blank values.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetBestImportedRouteTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, _
                                              Optional ByVal sourceRouteCol As Long = 0) As String
    GetBestImportedRouteTemplate = FindDynamicRouteForRowTemplate(ws, rowNum, sourceRouteCol)
End Function

'------------------------------------------------------------------------------
' Procedure: ApplyDeliveryListSystemHeadersTemplate
' Scope: Private Sub
'
' What it does:
'   Finds, writes, validates, or uses worksheet header cells for
'   ApplyDeliveryListSystemHeadersTemplate.
'
' Why it exists:
'   Header locations can move during import/rebuild, so the code uses header
'   discovery to target the correct columns instead of guessing.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ApplyDeliveryListSystemHeadersTemplate(ByVal ws As Worksheet, ByVal hdrRow As Long)
    UnmergeRangeSafeTemplate ws.Range("A" & hdrRow & ":N" & hdrRow)
    ws.Range("A" & hdrRow & ":N" & hdrRow).ClearContents

    ws.Range("A" & hdrRow & ":D" & hdrRow).Merge
    ws.Range("I" & hdrRow & ":J" & hdrRow).Merge

    ws.Cells(hdrRow, 1).Value = "Job Nr."
    ws.Cells(hdrRow, 5).Value = "Order Nr."
    ws.Cells(hdrRow, 6).Value = "Item Nr."
    ws.Cells(hdrRow, 7).Value = "Qty."
    ws.Cells(hdrRow, 8).Value = "Dimensions"
    ws.Cells(hdrRow, 9).Value = "Customer"
    ws.Cells(hdrRow, 11).Value = "RM"
    ws.Cells(hdrRow, 12).Value = "Route"
    ws.Cells(hdrRow, 13).Value = "Process State"
    ws.Cells(hdrRow, 14).ClearContents

    With ws.Range("A" & hdrRow & ":N" & hdrRow)
        .Font.Bold = True
        .Font.Size = 10
        .Font.Underline = xlUnderlineStyleNone
        .VerticalAlignment = xlCenter
    End With

    ws.Range("A" & hdrRow & ":D" & hdrRow).HorizontalAlignment = xlCenter
    ws.Cells(hdrRow, 5).HorizontalAlignment = xlCenter
    ws.Cells(hdrRow, 6).HorizontalAlignment = xlCenter
    ws.Cells(hdrRow, 7).HorizontalAlignment = xlCenter
    ws.Cells(hdrRow, 8).HorizontalAlignment = xlCenter
    ws.Range("I" & hdrRow & ":J" & hdrRow).HorizontalAlignment = xlCenter
    ws.Cells(hdrRow, 11).HorizontalAlignment = xlCenter
    ws.Cells(hdrRow, 12).HorizontalAlignment = xlCenter
    ws.Cells(hdrRow, 13).HorizontalAlignment = xlCenter

    If ws.Columns("A").ColumnWidth < 12 Then ws.Columns("A:C").ColumnWidth = 12
    ws.Columns("D").ColumnWidth = 7
    If ws.Columns("E").ColumnWidth < 10 Then ws.Columns("E").ColumnWidth = 10
    If ws.Columns("F").ColumnWidth < 8 Then ws.Columns("F").ColumnWidth = 8
    If ws.Columns("G").ColumnWidth < 8 Then ws.Columns("G").ColumnWidth = 8
    If ws.Columns("H").ColumnWidth < 16 Then ws.Columns("H").ColumnWidth = 16
    If ws.Columns("I").ColumnWidth < 16 Then ws.Columns("I:J").ColumnWidth = 16
    If ws.Columns("K").ColumnWidth < 5 Then ws.Columns("K").ColumnWidth = 5
    If ws.Columns("L").ColumnWidth < 8 Then ws.Columns("L").ColumnWidth = 8
    If ws.Columns("M").ColumnWidth < 14 Then ws.Columns("M").ColumnWidth = 14
    If ws.Columns("N").ColumnWidth < 2 Then ws.Columns("N").ColumnWidth = 2
End Sub

'------------------------------------------------------------------------------
' Procedure: UnmergeRangeSafeTemplate
' Scope: Private Sub
'
' What it does:
'   Performs the workbook-specific step named UnmergeRangeSafeTemplate inside
'   TemplateImporter.
'
' Why it exists:
'   The master workbook uses this module to turn a raw delivery list into the
'   operational sheets used by scanning, printing, exports, and intake
'   snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub UnmergeRangeSafeTemplate(ByVal rng As Range)
    Dim c As Range

    On Error Resume Next
    For Each c In rng.Cells
        If c.MergeCells Then
            c.MergeArea.UnMerge
        End If
    Next c
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: GetPreferredMergedValueTemplate
' Scope: Private Function
'
' What it does:
'   Returns a workbook object, setting, status value, parsed value, or
'   calculated result used by other procedures
'   (GetPreferredMergedValueTemplate).
'
' Why it exists:
'   Using one getter keeps callers from duplicating lookup logic and protects
'   them from missing sheets, missing names, or blank values.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetPreferredMergedValueTemplate(ByVal rng As Range, Optional ByVal preferRight As Boolean = False) As Variant
    Dim i As Long
    Dim v As Variant

    If preferRight Then
        For i = rng.Columns.Count To 1 Step -1
            v = rng.Cells(1, i).Value
            If Len(Trim$(CStr(v))) > 0 Then
                GetPreferredMergedValueTemplate = v
                Exit Function
            End If
        Next i
    Else
        For i = 1 To rng.Columns.Count
            v = rng.Cells(1, i).Value
            If Len(Trim$(CStr(v))) > 0 Then
                GetPreferredMergedValueTemplate = v
                Exit Function
            End If
        Next i
    End If

    GetPreferredMergedValueTemplate = vbNullString
End Function

'------------------------------------------------------------------------------
' Procedure: NormalizeMergedDisplayColumnsForRowTemplate
' Scope: Private Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   NormalizeMergedDisplayColumnsForRowTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub NormalizeMergedDisplayColumnsForRowTemplate(ByVal ws As Worksheet, ByVal rowNum As Long)
    Dim valAD As Variant
    Dim valIJ As Variant

    valAD = GetPreferredMergedValueTemplate(ws.Range("A" & rowNum & ":D" & rowNum), False)
    valIJ = GetPreferredMergedValueTemplate(ws.Range("I" & rowNum & ":J" & rowNum), True)

    UnmergeRangeSafeTemplate ws.Range("A" & rowNum & ":D" & rowNum)
    UnmergeRangeSafeTemplate ws.Range("I" & rowNum & ":J" & rowNum)

    ws.Range("A" & rowNum & ":D" & rowNum).ClearContents
    ws.Range("I" & rowNum & ":J" & rowNum).ClearContents

    ws.Cells(rowNum, 1).Value = valAD   'A for merged A:D
    ws.Cells(rowNum, 9).Value = valIJ   'I for merged I:J (preserve J content)

    ws.Range("A" & rowNum & ":D" & rowNum).Merge
    ws.Range("I" & rowNum & ":J" & rowNum).Merge

    ws.Range("A" & rowNum & ":D" & rowNum).HorizontalAlignment = xlLeft
    ws.Range("A" & rowNum & ":D" & rowNum).VerticalAlignment = xlCenter

    ws.Range("I" & rowNum & ":J" & rowNum).HorizontalAlignment = xlLeft
    ws.Range("I" & rowNum & ":J" & rowNum).VerticalAlignment = xlCenter
End Sub

'------------------------------------------------------------------------------
' Procedure: EnsureDeliveryListColumnLayoutTemplate
' Scope: Public Sub
'
' What it does:
'   Finds, sizes, hides, formats, or uses worksheet columns for
'   EnsureDeliveryListColumnLayoutTemplate.
'
' Why it exists:
'   The system depends on fixed scan blocks and discovered delivery-list
'   columns, so column handling must be centralized and predictable.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub EnsureDeliveryListColumnLayoutTemplate(ByVal ws As Worksheet)
    Dim p As SourceLayoutProfile
    Dim r As Long
    Dim lastUsedRow As Long

    p = ResolveSourceLayoutProfileTemplate(ws)
    If Not p.IsValid Then
        MsgBox "Could not detect the imported delivery list layout.", vbCritical, "Import Layout Error"
        Exit Sub
    End If

    ' Preserve title rows above the detected header row
    UnmergeUsedRangeFromRowTemplate ws, p.headerRow

    ApplyDeliveryListSystemHeadersTemplate ws, p.headerRow

    lastUsedRow = GetLastUsedRowTemplate(ws)
    If lastUsedRow < p.firstDataRow Then Exit Sub

    For r = p.firstDataRow To lastUsedRow
        If IsSourceSectionHeaderByProfileTemplate(ws, r, p) Then
            MapSourceRowToDeliveryListByProfileTemplate ws, r, ws, r, p, True

        ElseIf IsSourceRealRowByProfileTemplate(ws, r, p) Then
            MapSourceRowToDeliveryListByProfileTemplate ws, r, ws, r, p, False

        Else
            UnmergeRangeSafeTemplate ws.Range("A" & r & ":N" & r)
            ws.Range("A" & r & ":N" & r).ClearContents
        End If
    Next r

    If lastUsedRow >= p.firstDataRow Then
        ws.Range("O" & p.firstDataRow & ":AV" & lastUsedRow).ClearContents
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: NormalizeImportedRowToNewLayoutTemplate
' Scope: Private Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   NormalizeImportedRowToNewLayoutTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub NormalizeImportedRowToNewLayoutTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, _
                                                    Optional ByVal isSectionHeader As Boolean = False, _
                                                    Optional ByVal isRemake As Boolean = False)
    Dim jobTxt As String
    Dim ordTxt As Variant
    Dim itemTxt As Variant
    Dim qtyVal As Variant
    Dim dimTxt As String
    Dim custTxt As String
    Dim rmTxt As String
    Dim routeTxt As String
    Dim sectionTxt As String

    sectionTxt = JoinUniqueNonBlankTextFromColsTemplate(ws, rowNum, 1, 4, " ")
    jobTxt = sectionTxt
    ordTxt = ws.Cells(rowNum, 5).Value
    itemTxt = ws.Cells(rowNum, 6).Value
    qtyVal = ws.Cells(rowNum, 7).Value
    dimTxt = CleanLayoutTextTemplate(ws.Cells(rowNum, 8).Value)
    custTxt = JoinUniqueNonBlankTextFromColsTemplate(ws, rowNum, 9, 10, " ")
    rmTxt = CleanLayoutTextTemplate(ws.Cells(rowNum, REMAKE_MARKER_COL_FIXED).Value)
    routeTxt = GetBestImportedRouteTemplate(ws, rowNum)

    UnmergeRangeSafeTemplate ws.Range("A" & rowNum & ":N" & rowNum)
    ws.Range("A" & rowNum & ":N" & rowNum).ClearContents

    If isSectionHeader Then
        ws.Cells(rowNum, 1).Value = sectionTxt
    Else
        ws.Cells(rowNum, 1).Value = jobTxt
        ws.Cells(rowNum, 5).Value = ordTxt
        ws.Cells(rowNum, 6).Value = itemTxt
        ws.Cells(rowNum, 7).Value = qtyVal
        ws.Cells(rowNum, 8).Value = dimTxt
        ws.Cells(rowNum, 9).Value = custTxt
        ws.Cells(rowNum, 5).HorizontalAlignment = xlCenter
        ws.Cells(rowNum, 5).VerticalAlignment = xlCenter

        ws.Cells(rowNum, 6).HorizontalAlignment = xlCenter
        ws.Cells(rowNum, 6).VerticalAlignment = xlCenter

        ws.Cells(rowNum, 7).HorizontalAlignment = xlCenter
        ws.Cells(rowNum, 7).VerticalAlignment = xlCenter

        If isRemake Then
            ws.Cells(rowNum, REMAKE_MARKER_COL_FIXED).Value = REMAKE_MARKER_TEXT
        ElseIf IsRemakeMarkerValueTemplate(rmTxt) Then
            ws.Cells(rowNum, REMAKE_MARKER_COL_FIXED).Value = REMAKE_MARKER_TEXT
        End If

        ws.Cells(rowNum, ROUTE_COL_FIXED).Value = routeTxt
    End If

    ws.Cells(rowNum, PROCESS_STATE_COL_FIXED).ClearContents
    ws.Cells(rowNum, 14).ClearContents

    NormalizeMergedDisplayColumnsForRowTemplate ws, rowNum
End Sub

'------------------------------------------------------------------------------
' Procedure: GetBestImportedDeliveryListTitleTextTemplate
' Scope: Private Function
'
' What it does:
'   Returns a workbook object, setting, status value, parsed value, or
'   calculated result used by other procedures
'   (GetBestImportedDeliveryListTitleTextTemplate).
'
' Why it exists:
'   Using one getter keeps callers from duplicating lookup logic and protects
'   them from missing sheets, missing names, or blank values.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetBestImportedDeliveryListTitleTextTemplate(ByVal ws As Worksheet) As String
    Dim lastCol As Long
    Dim r As Long
    Dim c As Long
    Dim txt As String
    Dim dt As Date

    lastCol = LastUsedColTemplate(ws)
    If lastCol < 1 Then lastCol = 14

    For r = 1 To 5
        For c = 1 To lastCol
            txt = CleanLayoutTextTemplate(ws.Cells(r, c).Value)
            If Len(txt) > 0 Then
                If InStr(1, UCase$(txt), "DELIVERY LIST FOR", vbTextCompare) > 0 Then
                    GetBestImportedDeliveryListTitleTextTemplate = txt
                    Exit Function
                End If
            End If
        Next c
    Next r

    dt = GetDeliveryListDateForFileName(ws)
    If dt > 0 Then
        GetBestImportedDeliveryListTitleTextTemplate = "Delivery List For " & Format$(dt, "m/d/yyyy")
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: EnsureImportedDeliveryListTitleTemplate
' Scope: Public Sub
'
' What it does:
'   Verifies that required workbook objects, sheets, layout, names, or
'   settings exist for EnsureImportedDeliveryListTitleTemplate.
'
' Why it exists:
'   Many operations assume these supporting objects already exist; ensuring
'   them first prevents runtime failures after imports or workbook copies.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub EnsureImportedDeliveryListTitleTemplate(ByVal ws As Worksheet)
    Dim dt As Date
    Dim titleText As String

    dt = GetDeliveryListDateForFileName(ws)

    If dt > 0 Then
        titleText = "Delivery List For " & Format$(dt, "m/d/yyyy")
    Else
        titleText = "Delivery List"
    End If

    On Error Resume Next
    ws.Unprotect Password:=""
    On Error GoTo 0

    UnmergeRangeSafeTemplate ws.Range("A1:N4")
    ws.Range("A1:N4").ClearContents

    With ws.Range("A2:N3")
        .Merge
        .Value = titleText
        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
        .Font.Bold = True
        .Font.Size = 16
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: ImportNewDeliveryList
' Scope: Public Sub
'
' What it does:
'   Imports delivery-list data or import-related settings into the master
'   workbook (ImportNewDeliveryList).
'
' Why it exists:
'   The master needs imported source data converted into the stable layout
'   used by scanner sheets and print/export routines.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub ImportNewDeliveryList()
    Dim filePath As Variant
    Dim srcWb As Workbook
    Dim srcWs As Worksheet
    Dim dataWs As Worksheet
    Dim oldDataWs As Worksheet
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim firstDataRow As Long
    Dim orderCol As Long
    Dim itemCol As Long
    Dim importedTitleText As String
    Dim defaultImportFolder As String

    On Error GoTo ErrHandler

    defaultImportFolder = ThisWorkbook.Path & Application.PathSeparator & "Temp Delivery Lists"
    If Len(Dir$(defaultImportFolder, vbDirectory)) > 0 Then
        On Error Resume Next
        ChDir defaultImportFolder
        On Error GoTo ErrHandler
    End If

    filePath = Application.GetOpenFilename( _
        "Excel Files (*.xlsx;*.xlsm), *.xlsx;*.xlsm", _
        , _
        "Select the downloaded delivery list file")

    If VarType(filePath) = vbBoolean Then Exit Sub

    Application.ScreenUpdating = False
    Application.EnableEvents = False
    Application.DisplayAlerts = False
    Application.CutCopyMode = False
    Application.StatusBar = "Importing delivery list..."

    Set srcWb = Workbooks.Open(CStr(filePath), ReadOnly:=True)
    Set srcWs = srcWb.Worksheets(1)

    importedTitleText = GetBestImportedDeliveryListTitleTextTemplate(srcWs)

    'Remove old operational sheets first
    DeleteSheetIfExists ThisWorkbook, "Airport Rd"
    DeleteSheetIfExists ThisWorkbook, "Staging - Airport Rd"
    DeleteSheetIfExists ThisWorkbook, "Outbound - Airport Rd"
    DeleteSheetIfExists ThisWorkbook, GREENVILLE_RECV_SHEET_NAME
    DeleteSheetIfExists ThisWorkbook, CPU_SHEET_NAME
    DeleteSheetIfExists ThisWorkbook, GetReceiveSheetName()
    DeleteSheetIfExists ThisWorkbook, "__OLD_DELIVERY_LIST__"

    On Error Resume Next
    Set oldDataWs = ThisWorkbook.Worksheets("Delivery List")
    On Error GoTo ErrHandler

    If Not oldDataWs Is Nothing Then
        oldDataWs.Unprotect Password:=""
        oldDataWs.Name = "__OLD_DELIVERY_LIST__"
    End If

    'Copy imported sheet into this workbook
    srcWs.Copy Before:=ThisWorkbook.Worksheets(1)
    Set dataWs = ThisWorkbook.Worksheets(1)
    dataWs.Name = "Delivery List"

    'Immediately unprotect the copied sheet before any formatting work
    On Error Resume Next
    dataWs.Unprotect Password:=""
    On Error GoTo ErrHandler

    srcWb.Close SaveChanges:=False
    Set srcWb = Nothing

    'Rebuild the workbook-controlled layout in A:N
    EnsureDeliveryListColumnLayoutTemplate dataWs
    
    NormalizeDeliveryListTitleTemplate dataWs

    'Normalize top display row
    ForceRow3HeightTemplate dataWs

    'Clear old change-audit marker if present
    On Error Resume Next
    ThisWorkbook.Worksheets("__ChangeAudit").Range("A2:C2").ClearContents
    On Error GoTo ErrHandler

    'Delete old delivery list copy now that new one is live
    DeleteSheetIfExists ThisWorkbook, "__OLD_DELIVERY_LIST__"

    'Delete imported blank spacer rows / footer junk first
    RemoveImportedFooterNotes dataWs

    'No hidden rows in imported main list
    dataWs.rows.Hidden = False

    'Normalize any oversized imported row heights
    NormalizeImportedRowHeights dataWs

    'Column widths / font cleanup
    AutoFitImportedDeliveryListColumns dataWs
    StandardizeImportedDetailFontSize dataWs

    'Make sure scan layout exists after import cleanup is finished
    ScannerValidation.EnsureScanLayout dataWs
    ThisWorkbook.RefreshAllDeliveryListProcessStates dataWs

    Set orderHdr = FindHeaderCellTemplate(dataWs, Array("Order Nr."))
    Set itemHdr = FindHeaderCellTemplate(dataWs, Array("Item Nr.", "Item"))

    If Not orderHdr Is Nothing And Not itemHdr Is Nothing Then
        firstDataRow = orderHdr.Row + 1
        orderCol = orderHdr.Column
        itemCol = itemHdr.Column

        ReapplyDeliveryListRowStylesTemplate dataWs, firstDataRow, orderCol, itemCol
    End If

    AutoFitCommentColumnsTemplate dataWs

    'Rebuild all scanner sheets from the cleaned main list
'Rebuild all scanner sheets from the cleaned main list
RebuildAllScannerSheetsFromMain dataWs

'Main Delivery List summary
CreateOrUpdateTopSummaryPanels dataWs
dataWs.Calculate

'Now refresh the scanner sheets through the normal stage-specific refresh path
ThisWorkbook.RefreshAllOperationalSheets dataWs

ClearAllStoredScanHighlightsTemplate

'Delivery list structure changed â publish a new revision
BumpCurrentDeliveryListRevision
RecordDeliveryListImportMetadataTemplate CStr(filePath), importedTitleText
PublishAllStageSnapshots False, False
RegisterThisMasterDeliveryList
CreateOrRefreshActionButtons

'Final safe protection
ProtectViewOnlyTemplate dataWs

dataWs.Activate
If Not ActiveWindow Is Nothing Then
    ActiveWindow.ScrollRow = 1
    ActiveWindow.ScrollColumn = 1
End If
Application.GoTo dataWs.Range("A6"), False

Application.StatusBar = False
Application.DisplayAlerts = True
Application.EnableEvents = True
Application.ScreenUpdating = True

    MsgBox "Import complete." & vbCrLf & _
           "The master revision was updated and fresh intake snapshots were published.", _
           vbInformation, "Delivery List Imported"
    Exit Sub

ErrHandler:
    Dim errNum As Long
    Dim errDesc As String

    errNum = Err.Number
    errDesc = Err.Description

    On Error Resume Next
    If Not srcWb Is Nothing Then srcWb.Close SaveChanges:=False
    Application.StatusBar = False
    Application.CutCopyMode = False
    Application.DisplayAlerts = True
    Application.EnableEvents = True
    Application.ScreenUpdating = True

    MsgBox "ImportNewDeliveryList error " & errNum & ":" & vbCrLf & errDesc, vbCritical, "Import Error"
End Sub

'------------------------------------------------------------------------------
' Procedure: RecordDeliveryListImportMetadataTemplate
' Scope: Private Sub
'
' What it does:
'   Stores the last imported A&W source file, title text, and timestamp in
'   workbook-level names.
'
' Why it exists:
'   Delivery-list imports are operational events. Keeping this metadata with
'   the workbook makes it easier to verify which A&W source file produced the
'   current master revision and snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub RecordDeliveryListImportMetadataTemplate(ByVal sourcePath As String, ByVal titleText As String)
    On Error Resume Next

    ThisWorkbook.names("_LastDeliveryListImportSource").Delete
    ThisWorkbook.names("_LastDeliveryListImportTitle").Delete
    ThisWorkbook.names("_LastDeliveryListImportedAt").Delete

    ThisWorkbook.names.Add Name:="_LastDeliveryListImportSource", RefersTo:="=""" & Replace(sourcePath, """", """""") & """"
    ThisWorkbook.names.Add Name:="_LastDeliveryListImportTitle", RefersTo:="=""" & Replace(titleText, """", """""") & """"
    ThisWorkbook.names.Add Name:="_LastDeliveryListImportedAt", RefersTo:="=""" & Format$(Now, "m/d/yyyy h:mm:ss AM/PM") & """"

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: UpdateExistingDeliveryList
' Scope: Public Sub
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   UpdateExistingDeliveryList.
'
' Why it exists:
'   Delivery timing, queue timestamps, and scan timestamps drive status
'   messages such as Early, On-Time, Late, Processing, and Done.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub UpdateExistingDeliveryList()

    Dim filePath As Variant
    Dim srcWb As Workbook
    Dim srcWs As Worksheet
    Dim dataWs As Worksheet
    Dim destOrderHdr As Range, destItemHdr As Range
    Dim p As SourceLayoutProfile
    Dim destFirstRow As Long
    Dim destOrderCol As Long, destItemCol As Long
    Dim existingKeys As Object
    Dim additionsBySection As Object
    Dim sourceSectionNames As Object
    Dim sourceSectionHeaderRows As Object
    Dim savedScanState As Object
    Dim currentSectionKey As String
    Dim currentSectionDisplay As String
    Dim rowKey As String
    Dim importKind As String
    Dim rowImportKind As String
    Dim lastSrcRealRow As Long
    Dim addedCount As Long
    Dim r As Long
    Dim i As Long
    Dim sectionKey As Variant
    Dim rowsForSection As Collection
    Dim insertRow As Long
    Dim appendRow As Long
    Dim pendingRows As Collection
    Dim addedRows As Object
    Dim addedKeys As Object
    Dim existingIdentityRows As Object
    Dim rowIdentityKey As String
    Dim existingRowNum As Long

    On Error GoTo ErrHandler

    filePath = Application.GetOpenFilename( _
        "Excel Files (*.xlsx;*.xlsm), *.xlsx;*.xlsm", _
        , _
        "Select the newest downloaded delivery list file")
    If VarType(filePath) = vbBoolean Then Exit Sub

    importKind = PromptForUpdateImportKindTemplate()
    If Len(importKind) = 0 Then Exit Sub

    Application.ScreenUpdating = False
    Application.EnableEvents = False
    Application.DisplayAlerts = False

    Set dataWs = ThisWorkbook.Worksheets("Delivery List")
    On Error Resume Next
    dataWs.Unprotect Password:=""
    On Error GoTo ErrHandler

    Set srcWb = Workbooks.Open(CStr(filePath), ReadOnly:=True)
    Set srcWs = srcWb.Worksheets(1)

    p = ResolveSourceLayoutProfileTemplate(srcWs)
    If Not p.IsValid Then
        MsgBox "Could not detect the source delivery list layout in the update file.", vbCritical, "Update Error"
        GoTo SafeExit
    End If

    Set destOrderHdr = FindHeaderCellTemplate(dataWs, Array("Order Nr."))
    Set destItemHdr = FindHeaderCellTemplate(dataWs, Array("Item Nr.", "Item"))
    If destOrderHdr Is Nothing Or destItemHdr Is Nothing Then
        MsgBox "Could not find Order Nr. / Item Nr. headers on the current Delivery List.", vbCritical, "Update Error"
        GoTo SafeExit
    End If

    If Not ValidateMatchingDeliveryListsTemplate(dataWs, srcWs) Then GoTo SafeExit

    destFirstRow = destOrderHdr.Row + 1
    destOrderCol = destOrderHdr.Column
    destItemCol = destItemHdr.Column

    'Preserve existing scans/comments before inserting anything
    Set savedScanState = CaptureScanPanelStateByKeyTemplate(dataWs, destFirstRow, destOrderCol, destItemCol)

    Set existingKeys = BuildExistingDeliveryKeySetWithKindTemplate(dataWs, destFirstRow, destOrderCol, destItemCol)
Set existingIdentityRows = BuildExistingDeliveryRowIndexByIdentityWithKindTemplate(dataWs, destFirstRow, destOrderCol, destItemCol)
Set additionsBySection = CreateObject("Scripting.Dictionary")
Set sourceSectionNames = CreateObject("Scripting.Dictionary")
Set sourceSectionHeaderRows = CreateObject("Scripting.Dictionary")
Set addedRows = CreateObject("Scripting.Dictionary")
Set addedKeys = CreateObject("Scripting.Dictionary")

    lastSrcRealRow = GetLastUsedRowTemplate(srcWs)
    currentSectionKey = vbNullString
    currentSectionDisplay = vbNullString
    addedCount = 0

    For r = p.firstDataRow To lastSrcRealRow
        If IsSourceSectionHeaderByProfileTemplate(srcWs, r, p) Then
            currentSectionDisplay = Trim$(CStr(srcWs.Cells(r, 1).Value))
            currentSectionKey = NormalizeSectionKey(currentSectionDisplay)

            If Len(currentSectionKey) > 0 Then
                If Not sourceSectionNames.Exists(currentSectionKey) Then
                    sourceSectionNames.Add currentSectionKey, currentSectionDisplay
                End If
                If Not sourceSectionHeaderRows.Exists(currentSectionKey) Then
                    sourceSectionHeaderRows.Add currentSectionKey, r
                End If
            End If

        ElseIf IsSourceRealRowByProfileTemplate(srcWs, r, p) Then
            If Len(currentSectionKey) = 0 Then
                currentSectionKey = "__UNSECTIONED__"
                currentSectionDisplay = vbNullString
                If Not sourceSectionNames.Exists(currentSectionKey) Then
                    sourceSectionNames.Add currentSectionKey, currentSectionDisplay
                End If
            End If

            rowImportKind = GetSourceRowImportKindTemplate(srcWs, r, importKind, p.RemakeCol)

'Identity key = same logical line item, regardless of CPU/non-CPU route state
rowIdentityKey = BuildSourceDeliveryIdentityKeyByProfileTemplate(srcWs, r, currentSectionKey, rowImportKind, p)

'Full row key still includes route so new true additions can be tracked/highlighted correctly
rowKey = BuildSourceDeliveryLineKeyByProfileTemplate(srcWs, r, currentSectionKey, rowImportKind, p)

If existingIdentityRows.Exists(rowIdentityKey) Then
    existingRowNum = CLng(existingIdentityRows(rowIdentityKey))

    'Same line already exists: update it in place instead of duplicating it
    SyncSourceRowToExistingDeliveryRowTemplate srcWs, r, dataWs, existingRowNum, p, rowImportKind

Else
    If Not additionsBySection.Exists(currentSectionKey) Then
        Set pendingRows = New Collection
        additionsBySection.Add currentSectionKey, pendingRows
    End If

    additionsBySection(currentSectionKey).Add r

    'Reserve this logical line identity so repeated source rows do not duplicate during this same run
    If Not existingIdentityRows.Exists(rowIdentityKey) Then
        existingIdentityRows.Add rowIdentityKey, -1
    End If

    If Not existingKeys.Exists(rowKey) Then
        existingKeys.Add rowKey, True
    End If

    If Not addedKeys.Exists(rowKey) Then
        addedKeys.Add rowKey, True
    End If

    addedCount = addedCount + 1
End If
        End If
    Next r

    If addedCount = 0 Then
        MsgBox "No new additions were found." & vbCrLf & vbCrLf & _
               "Existing scans, comments, and manual edits were left unchanged.", _
               vbInformation, "No Update Needed"
        GoTo SafeExit
    End If

    For Each sectionKey In additionsBySection.Keys
        Set rowsForSection = additionsBySection(sectionKey)
        insertRow = FindSectionInsertRow(dataWs, CStr(sectionKey), destFirstRow, destOrderCol, destItemCol)

        If insertRow > 0 Then
            dataWs.rows(insertRow & ":" & (insertRow + rowsForSection.Count - 1)).Insert _
                Shift:=xlDown, CopyOrigin:=xlFormatFromLeftOrAbove

            For i = 1 To rowsForSection.Count
                rowImportKind = GetSourceRowImportKindTemplate(srcWs, CLng(rowsForSection(i)), importKind, p.RemakeCol)
                CopySourceRowIntoDestination srcWs, CLng(rowsForSection(i)), dataWs, insertRow + i - 1
                NormalizeImportedRowToNewLayoutTemplate dataWs, insertRow + i - 1, False, (rowImportKind = "REMAKE")

                addedRows(CStr(insertRow + i - 1)) = True
                ApplyDeliveryListRowStyleTemplate dataWs, insertRow + i - 1, True
            Next i

        Else
            appendRow = FindLastRealDeliveryRowTemplate(dataWs, destOrderCol, destItemCol, destFirstRow) + 1
            dataWs.rows(appendRow & ":" & (appendRow + rowsForSection.Count)).Insert _
                Shift:=xlDown, CopyOrigin:=xlFormatFromLeftOrAbove

            If sourceSectionHeaderRows.Exists(sectionKey) Then
                CopySourceRowIntoDestination srcWs, CLng(sourceSectionHeaderRows(sectionKey)), dataWs, appendRow, True
                NormalizeImportedRowToNewLayoutTemplate dataWs, appendRow, True, False
                ApplyImportedSectionHeaderFormatTemplate dataWs, appendRow, destFirstRow, destOrderCol, destItemCol
            Else
                UnmergeRangeSafeTemplate dataWs.Range("A" & appendRow & ":N" & appendRow)
                dataWs.Range("A" & appendRow & ":N" & appendRow).ClearContents
                dataWs.Cells(appendRow, 1).Value = CStr(sourceSectionNames(sectionKey))
                dataWs.Range("O" & appendRow & ":AV" & appendRow).ClearContents
                ApplyImportedSectionHeaderFormatTemplate dataWs, appendRow, destFirstRow, destOrderCol, destItemCol
            End If

            For i = 1 To rowsForSection.Count
                rowImportKind = GetSourceRowImportKindTemplate(srcWs, CLng(rowsForSection(i)), importKind, p.RemakeCol)
                CopySourceRowIntoDestination srcWs, CLng(rowsForSection(i)), dataWs, appendRow + i
                NormalizeImportedRowToNewLayoutTemplate dataWs, appendRow + i, False, (rowImportKind = "REMAKE")

                addedRows(CStr(appendRow + i)) = True
                ApplyDeliveryListRowStyleTemplate dataWs, appendRow + i, True
            Next i
        End If
    Next sectionKey

    srcWb.Close SaveChanges:=False
    Set srcWb = Nothing

    ForceRow3HeightTemplate dataWs
    ScannerValidation.EnsureScanLayout dataWs

    'Do NOT call RemoveImportedFooterNotes during update.
    'Do NOT call EnsureDeliveryListColumnLayoutTemplate during update.

    NormalizeImportedRowHeights dataWs
    AutoFitImportedDeliveryListColumns dataWs
    StandardizeImportedDetailFontSize dataWs
    ReapplyDeliveryListRowStylesTemplate dataWs, destFirstRow, destOrderCol, destItemCol, addedRows, addedKeys
    AutoFitCommentColumnsTemplate dataWs

    'Restore preserved scans/comments after row inserts/reformatting
    RestoreScanPanelStateByKeyTemplate dataWs, savedScanState, destFirstRow, destOrderCol, destItemCol

    'Now rebuild process states and scanner sheets from the restored master sheet
    ThisWorkbook.RefreshAllDeliveryListProcessStates dataWs
ReapplyDeliveryListRowStylesTemplate dataWs, destFirstRow, destOrderCol, destItemCol, addedRows, addedKeys

ClearAllStoredScanHighlightsTemplate

RebuildAllScannerSheetsFromMain dataWs

CreateOrUpdateTopSummaryPanels dataWs
dataWs.Calculate

ThisWorkbook.RefreshAllOperationalSheets dataWs

'Delivery list structure changed â publish a new revision
BumpCurrentDeliveryListRevision
RecordDeliveryListImportMetadataTemplate CStr(filePath), "Update existing delivery list"
PublishAllStageSnapshots False, False
RegisterThisMasterDeliveryList
ProtectViewOnlyTemplate dataWs
CreateOrRefreshHomeMenu
dataWs.Activate
ShowUpdateNoticeOnce addedCount



SafeExit:
    On Error Resume Next
    FinalizeUpdateStateSheetTemplate
    If Not srcWb Is Nothing Then srcWb.Close SaveChanges:=False
    Application.DisplayAlerts = True
    Application.EnableEvents = True
    Application.ScreenUpdating = True
    Exit Sub

ErrHandler:
    Application.DisplayAlerts = True
    Application.EnableEvents = True
    Application.ScreenUpdating = True
    MsgBox "UpdateExistingDeliveryList error " & Err.Number & ":" & vbCrLf & Err.Description, vbCritical, "Update Error"
End Sub

'------------------------------------------------------------------------------
' Procedure: GetOrCreateUpdateStateSheetTemplate
' Scope: Private Function
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   GetOrCreateUpdateStateSheetTemplate.
'
' Why it exists:
'   Delivery timing, queue timestamps, and scan timestamps drive status
'   messages such as Early, On-Time, Late, Processing, and Done.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetOrCreateUpdateStateSheetTemplate() As Worksheet
    Const STATE_SHEET_NAME As String = "__UPDATE_STATE__"
    Dim ws As Worksheet

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(STATE_SHEET_NAME)
    On Error GoTo 0

    If ws Is Nothing Then
        Set ws = ThisWorkbook.Worksheets.Add(After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
        ws.Name = STATE_SHEET_NAME
    End If

    On Error Resume Next
    ws.Visible = xlSheetVisible
    ws.Unprotect Password:=""
    ws.Cells.Clear
    ws.Range("A1").Value = "RowKey"
    ws.Visible = xlSheetVeryHidden
    On Error GoTo 0

    Set GetOrCreateUpdateStateSheetTemplate = ws
End Function

'------------------------------------------------------------------------------
' Procedure: FinalizeUpdateStateSheetTemplate
' Scope: Private Sub
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   FinalizeUpdateStateSheetTemplate.
'
' Why it exists:
'   Delivery timing, queue timestamps, and scan timestamps drive status
'   messages such as Early, On-Time, Late, Processing, and Done.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub FinalizeUpdateStateSheetTemplate()
    Const STATE_SHEET_NAME As String = "__UPDATE_STATE__"
    Dim ws As Worksheet

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(STATE_SHEET_NAME)
    If Not ws Is Nothing Then
        ws.Visible = xlSheetVisible
        ws.Unprotect Password:=""
        ws.Cells.Clear
        ws.Range("A1").Value = "RowKey"
        ws.Visible = xlSheetVeryHidden
    End If
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: CaptureScanPanelStateByKeyTemplate
' Scope: Private Function
'
' What it does:
'   Builds, formats, deletes, or wires workbook UI shapes/buttons/panels for
'   CaptureScanPanelStateByKeyTemplate.
'
' Why it exists:
'   Buttons and utility panels are the operator-facing control surface, so
'   they must be rebuilt consistently after imports or sheet refreshes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function CaptureScanPanelStateByKeyTemplate(ByVal ws As Worksheet, ByVal firstDataRow As Long, ByVal orderCol As Long, ByVal itemCol As Long) As Object
    Dim dict As Object
    Dim stateWs As Worksheet
    Dim lastRealRow As Long
    Dim currentSectionKey As String
    Dim r As Long
    Dim rowKey As String
    Dim saveRow As Long

    Set dict = CreateObject("Scripting.Dictionary")
    Set stateWs = GetOrCreateUpdateStateSheetTemplate()
    
    stateWs.Cells.Clear
    stateWs.Range("A1").Value = "RowKey"

    lastRealRow = FindLastRealDeliveryRowTemplate(ws, orderCol, itemCol, firstDataRow)
    currentSectionKey = vbNullString
    saveRow = 2

    For r = firstDataRow To lastRealRow
        If IsSectionHeaderRowTemplate(ws, r, orderCol, itemCol) Then
            currentSectionKey = NormalizeSectionKey(CStr(ws.Cells(r, 1).Value))

        ElseIf IsRealDeliveryLineTemplate(ws, r, orderCol, itemCol) Then
            If Len(currentSectionKey) = 0 Then currentSectionKey = "__UNSECTIONED__"

            rowKey = BuildCurrentDeliveryLineKeyWithKindTemplate(ws, r, currentSectionKey, orderCol, itemCol)

            If Not dict.Exists(rowKey) Then
                stateWs.Cells(saveRow, 1).Value = rowKey

                ws.Range("O" & r & ":AV" & r).Copy
                stateWs.Range("B" & saveRow).PasteSpecial xlPasteAll
                Application.CutCopyMode = False

                dict.Add rowKey, saveRow
                saveRow = saveRow + 1
            End If
        End If
    Next r

    Set CaptureScanPanelStateByKeyTemplate = dict
End Function

'------------------------------------------------------------------------------
' Procedure: RestoreScanPanelStateByKeyTemplate
' Scope: Private Sub
'
' What it does:
'   Builds, formats, deletes, or wires workbook UI shapes/buttons/panels for
'   RestoreScanPanelStateByKeyTemplate.
'
' Why it exists:
'   Buttons and utility panels are the operator-facing control surface, so
'   they must be rebuilt consistently after imports or sheet refreshes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub RestoreScanPanelStateByKeyTemplate(ByVal ws As Worksheet, ByVal stateMap As Object, ByVal firstDataRow As Long, ByVal orderCol As Long, ByVal itemCol As Long)
    Const STATE_SHEET_NAME As String = "__UPDATE_STATE__"

    Dim stateWs As Worksheet
    Dim lastRealRow As Long
    Dim currentSectionKey As String
    Dim r As Long
    Dim rowKey As String
    Dim saveRow As Long

    If stateMap Is Nothing Then Exit Sub

    On Error Resume Next
    Set stateWs = ThisWorkbook.Worksheets(STATE_SHEET_NAME)
    On Error GoTo 0
    If stateWs Is Nothing Then Exit Sub

    lastRealRow = FindLastRealDeliveryRowTemplate(ws, orderCol, itemCol, firstDataRow)
    currentSectionKey = vbNullString

    For r = firstDataRow To lastRealRow
        If IsSectionHeaderRowTemplate(ws, r, orderCol, itemCol) Then
            currentSectionKey = NormalizeSectionKey(CStr(ws.Cells(r, 1).Value))

        ElseIf IsRealDeliveryLineTemplate(ws, r, orderCol, itemCol) Then
            If Len(currentSectionKey) = 0 Then currentSectionKey = "__UNSECTIONED__"

            rowKey = BuildCurrentDeliveryLineKeyWithKindTemplate(ws, r, currentSectionKey, orderCol, itemCol)

            If stateMap.Exists(rowKey) Then
                saveRow = CLng(stateMap(rowKey))

                stateWs.Range("B" & saveRow & ":AI" & saveRow).Copy
                ws.Range("O" & r & ":AV" & r).PasteSpecial xlPasteAll
                Application.CutCopyMode = False
            End If
        End If
    Next r
End Sub

'------------------------------------------------------------------------------
' Procedure: BuildExistingDeliveryKeySet
' Scope: Private Function
'
' What it does:
'   Builds a derived value, key, JSON block, layout, collection, or workbook
'   object used later by the workflow (BuildExistingDeliveryKeySet).
'
' Why it exists:
'   The project uses generated keys/layouts to keep repeated logic consistent
'   instead of hand-building values in multiple places.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BuildExistingDeliveryKeySet(ByVal ws As Worksheet, ByVal firstDataRow As Long, ByVal orderCol As Long, ByVal itemCol As Long) As Object
    Dim dict As Object
    Dim lastRealRow As Long
    Dim currentSectionKey As String
    Dim r As Long
    Dim rowKey As String

    Set dict = CreateObject("Scripting.Dictionary")
    lastRealRow = FindLastRealDeliveryRowTemplate(ws, orderCol, itemCol, firstDataRow)
    currentSectionKey = vbNullString

    For r = firstDataRow To lastRealRow
        If IsSectionHeaderRowTemplate(ws, r, orderCol, itemCol) Then
            currentSectionKey = NormalizeSectionKey(CStr(ws.Cells(r, 1).Value))

        ElseIf IsRealDeliveryLineTemplate(ws, r, orderCol, itemCol) Then
            If Len(currentSectionKey) = 0 Then currentSectionKey = "__UNSECTIONED__"

            rowKey = BuildDeliveryLineKey(ws, r, currentSectionKey, orderCol, itemCol)

            If Not dict.Exists(rowKey) Then
                dict.Add rowKey, True
            End If
        End If
    Next r

    Set BuildExistingDeliveryKeySet = dict
End Function

'------------------------------------------------------------------------------
' Procedure: BuildDeliveryLineKey
' Scope: Private Function
'
' What it does:
'   Builds a derived value, key, JSON block, layout, collection, or workbook
'   object used later by the workflow (BuildDeliveryLineKey).
'
' Why it exists:
'   The project uses generated keys/layouts to keep repeated logic consistent
'   instead of hand-building values in multiple places.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BuildDeliveryLineKey(ByVal ws As Worksheet, ByVal rowNum As Long, ByVal sectionKey As String, ByVal orderCol As Long, ByVal itemCol As Long) As String
    Dim ordTxt As String
    Dim itemTxt As String

    ordTxt = Trim$(CStr(ws.Cells(rowNum, orderCol).Value))

    If IsNumeric(ws.Cells(rowNum, itemCol).Value) Then
        itemTxt = Format$(CLng(Val(ws.Cells(rowNum, itemCol).Value)), "000")
    Else
        itemTxt = Trim$(CStr(ws.Cells(rowNum, itemCol).Value))
    End If

    BuildDeliveryLineKey = NormalizeSectionKey(sectionKey) & "|" & ordTxt & "|" & itemTxt
End Function

'------------------------------------------------------------------------------
' Procedure: NormalizeSectionKey
' Scope: Private Function
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   NormalizeSectionKey.
'
' Why it exists:
'   Remakes need separate visual and print/export handling so replacement
'   glass is not confused with regular delivery-list work.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function NormalizeSectionKey(ByVal s As String) As String
    NormalizeSectionKey = UCase$(Trim$(s))
End Function

'------------------------------------------------------------------------------
' Procedure: IsSectionHeaderRowTemplate
' Scope: Private Function
'
' What it does:
'   Finds, writes, validates, or uses worksheet header cells for
'   IsSectionHeaderRowTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function IsSectionHeaderRowTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, ByVal orderCol As Long, ByVal itemCol As Long) As Boolean
    Dim leftText As String
    Dim ordTxt As String
    Dim itemTxt As String

    leftText = CleanLayoutTextTemplate(ws.Cells(rowNum, 1).Value)
    ordTxt = CleanLayoutTextTemplate(ws.Cells(rowNum, orderCol).Value)
    itemTxt = CleanLayoutTextTemplate(ws.Cells(rowNum, itemCol).Value)

    IsSectionHeaderRowTemplate = (Len(leftText) > 0 And Len(ordTxt) = 0 And Len(itemTxt) = 0)
End Function

'------------------------------------------------------------------------------
' Procedure: FindSectionInsertRow
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   FindSectionInsertRow.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function FindSectionInsertRow(ByVal ws As Worksheet, ByVal targetSectionKey As String, ByVal firstDataRow As Long, ByVal orderCol As Long, ByVal itemCol As Long) As Long
    Dim lastRealRow As Long
    Dim currentSectionKey As String
    Dim lastRowInSection As Long
    Dim r As Long

    lastRealRow = FindLastRealDeliveryRowTemplate(ws, orderCol, itemCol, firstDataRow)
    currentSectionKey = vbNullString
    lastRowInSection = 0

    For r = firstDataRow To lastRealRow
        If IsSectionHeaderRowTemplate(ws, r, orderCol, itemCol) Then
            currentSectionKey = NormalizeSectionKey(CStr(ws.Cells(r, 1).Value))

        ElseIf IsRealDeliveryLineTemplate(ws, r, orderCol, itemCol) Then
            If Len(currentSectionKey) = 0 Then currentSectionKey = "__UNSECTIONED__"

            If StrComp(currentSectionKey, NormalizeSectionKey(targetSectionKey), vbTextCompare) = 0 Then
                lastRowInSection = r
            End If
        End If
    Next r

    If lastRowInSection > 0 Then
        FindSectionInsertRow = lastRowInSection + 1
    Else
        FindSectionInsertRow = 0
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: CopySourceRowIntoDestination
' Scope: Private Sub
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   CopySourceRowIntoDestination.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub CopySourceRowIntoDestination(ByVal srcWs As Worksheet, ByVal srcRow As Long, _
                                         ByVal destWs As Worksheet, ByVal destRow As Long, _
                                         Optional ByVal isSectionHeader As Boolean = False, _
                                         Optional ByVal preserveScanPanels As Boolean = False)
    Dim p As SourceLayoutProfile

    p = ResolveSourceLayoutProfileTemplate(srcWs)
    If Not p.IsValid Then
        Err.Raise vbObjectError + 7401, "CopySourceRowIntoDestination", "Could not detect source layout profile."
    End If

    MapSourceRowToDeliveryListByProfileTemplate srcWs, srcRow, destWs, destRow, p, isSectionHeader

    If Not preserveScanPanels Then
        destWs.Range("O" & destRow & ":AV" & destRow).ClearContents
    End If

    destWs.rows(destRow).RowHeight = srcWs.rows(srcRow).RowHeight
End Sub

'------------------------------------------------------------------------------
' Procedure: FindAnySectionHeaderStyleRowTemplate
' Scope: Private Function
'
' What it does:
'   Finds, writes, validates, or uses worksheet header cells for
'   FindAnySectionHeaderStyleRowTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function FindAnySectionHeaderStyleRowTemplate(ByVal ws As Worksheet, ByVal firstDataRow As Long, _
                                                      ByVal orderCol As Long, ByVal itemCol As Long, _
                                                      Optional ByVal excludeRow As Long = 0) As Long
    Dim lastRealRow As Long
    Dim r As Long

    lastRealRow = FindLastRealDeliveryRowTemplate(ws, orderCol, itemCol, firstDataRow)

    For r = firstDataRow To lastRealRow
        If r <> excludeRow Then
            If IsSectionHeaderRowTemplate(ws, r, orderCol, itemCol) Then
                FindAnySectionHeaderStyleRowTemplate = r
                Exit Function
            End If
        End If
    Next r
End Function

'------------------------------------------------------------------------------
' Procedure: ApplyImportedSectionHeaderFormatTemplate
' Scope: Private Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   ApplyImportedSectionHeaderFormatTemplate.
'
' Why it exists:
'   Remakes need separate visual and print/export handling so replacement
'   glass is not confused with regular delivery-list work.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ApplyImportedSectionHeaderFormatTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, _
                                                     ByVal firstDataRow As Long, ByVal orderCol As Long, ByVal itemCol As Long)
    Dim templateRow As Long
    Dim headerText As String

    headerText = CStr(ws.Cells(rowNum, 1).Value)
    templateRow = FindAnySectionHeaderStyleRowTemplate(ws, firstDataRow, orderCol, itemCol, rowNum)

    If templateRow = 0 Then Exit Sub

    ws.Range("A" & templateRow & ":N" & templateRow).Copy
    ws.Range("A" & rowNum & ":N" & rowNum).PasteSpecial xlPasteFormats
    Application.CutCopyMode = False

    ws.rows(rowNum).RowHeight = ws.rows(templateRow).RowHeight

    UnmergeRangeSafeTemplate ws.Range("A" & rowNum & ":N" & rowNum)
    ws.Range("A" & rowNum & ":N" & rowNum).ClearContents

    ws.Cells(rowNum, 1).Value = headerText
    ws.Cells(rowNum, REMAKE_MARKER_COL_FIXED).ClearContents
    ws.Cells(rowNum, ROUTE_COL_FIXED).ClearContents
    ws.Cells(rowNum, PROCESS_STATE_COL_FIXED).ClearContents
    ws.Cells(rowNum, 14).ClearContents

    NormalizeMergedDisplayColumnsForRowTemplate ws, rowNum
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplyNewestAdditionMarkTemplate
' Scope: Private Sub
'
' What it does:
'   Applies formatting, filters, protection, selection state, or business-
'   state changes for ApplyNewestAdditionMarkTemplate.
'
' Why it exists:
'   Separating apply steps makes it easier to rebuild sheets and then
'   consistently reapply the visual/workflow rules operators rely on.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ApplyNewestAdditionMarkTemplate(ByVal rng As Range)
    If rng Is Nothing Then Exit Sub

    With rng
        .Interior.Color = RGB(221, 217, 238)
        .Borders.LineStyle = xlContinuous
        .Borders.Weight = xlThin
        .Borders.Color = RGB(112, 48, 160)
        .Font.Bold = True
        .Font.Color = RGB(64, 0, 96)
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: HideOtherPanelTemplate
' Scope: Private Sub
'
' What it does:
'   Builds, formats, deletes, or wires workbook UI shapes/buttons/panels for
'   HideOtherPanelTemplate.
'
' Why it exists:
'   Buttons and utility panels are the operator-facing control surface, so
'   they must be rebuilt consistently after imports or sheet refreshes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub HideOtherPanelTemplate(ByVal ws As Worksheet, ByVal mode As String)
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

    'AE is always unused on the inbound scanner panel
    ws.Columns("AE").ColumnWidth = 0.1
    ws.Columns("AE").EntireColumn.Hidden = True
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplyOperationalFreezePane
' Scope: Public Sub
'
' What it does:
'   Controls the active sheet/window view, freeze panes, navigation, or
'   selected cell for ApplyOperationalFreezePane.
'
' Why it exists:
'   The workbook is used by scanners/operators, so opening the right view and
'   scan area reduces missed scans and operator confusion.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub ApplyOperationalFreezePane(ByVal ws As Worksheet)
    Dim prevSheet As Worksheet
    Dim evtState As Boolean
    Dim scrState As Boolean

    If ws Is Nothing Then Exit Sub

    On Error Resume Next
    Set prevSheet = ActiveSheet
    evtState = Application.EnableEvents
    scrState = Application.ScreenUpdating

    Application.EnableEvents = False
    Application.ScreenUpdating = False

    ThisWorkbook.Activate
    ws.Activate

    If Not ActiveWindow Is Nothing Then
        With ActiveWindow
            .FreezePanes = False
            .SplitColumn = 0
            .SplitRow = 5
            .ScrollRow = 1
            .ScrollColumn = 1
        End With

        ws.Range("A6").Select
        ActiveWindow.FreezePanes = True
    End If

SafeExit:
    If Not prevSheet Is Nothing Then prevSheet.Activate
    Application.EnableEvents = evtState
    Application.ScreenUpdating = scrState
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: ProtectLockColumnsAtoNTemplate
' Scope: Private Sub
'
' What it does:
'   Controls worksheet/workbook protection or read-only safety behavior for
'   ProtectLockColumnsAtoNTemplate.
'
' Why it exists:
'   Protection keeps operators from accidentally editing formula/layout areas
'   while still allowing the intended scan or comment cells to work.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ProtectLockColumnsAtoNTemplate(ByVal ws As Worksheet)
    Dim unlockRng As Range

    On Error Resume Next
    ws.Unprotect Password:=""
    On Error GoTo 0

    'Unlock the working area first
    On Error Resume Next
    Set unlockRng = ws.UsedRange
    If Not unlockRng Is Nothing Then unlockRng.Locked = False
    On Error GoTo 0

    'Then hard-lock the delivery-list side on scanner sheets
    On Error Resume Next
    ws.Columns("A:N").Locked = True
    ws.rows("1:5").Locked = True
    On Error GoTo 0

    'Users can only click unlocked cells outside A:N
    ws.EnableSelection = xlUnlockedCells

    ApplyOperationalFreezePane ws

    ws.Protect Password:="", UserInterfaceOnly:=True, DrawingObjects:=False, Contents:=True, Scenarios:=True
End Sub

'------------------------------------------------------------------------------
' Procedure: ProtectViewOnlyTemplate
' Scope: Private Sub
'
' What it does:
'   Controls worksheet/workbook protection or read-only safety behavior for
'   ProtectViewOnlyTemplate.
'
' Why it exists:
'   Protection keeps operators from accidentally editing formula/layout areas
'   while still allowing the intended scan or comment cells to work.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ProtectViewOnlyTemplate(ByVal ws As Worksheet)
    On Error Resume Next
    ws.Unprotect Password:=""
    On Error GoTo 0

    'Safer than touching the entire worksheet cell grid
    On Error Resume Next
    ws.UsedRange.Locked = True
    On Error GoTo 0

    If UCase$(ws.Name) = UCase$("Delivery List") Then
        ws.EnableSelection = xlNoSelection
    Else
        ws.EnableSelection = xlNoRestrictions
    End If

    ApplyOperationalFreezePane ws

    ws.Protect Password:="", UserInterfaceOnly:=True, DrawingObjects:=False, Contents:=True, Scenarios:=True
End Sub

'------------------------------------------------------------------------------
' Procedure: AutoFitCommentColumnsTemplate
' Scope: Private Sub
'
' What it does:
'   Finds, sizes, hides, formats, or uses worksheet columns for
'   AutoFitCommentColumnsTemplate.
'
' Why it exists:
'   The system depends on fixed scan blocks and discovered delivery-list
'   columns, so column handling must be centralized and predictable.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub AutoFitCommentColumnsTemplate(ByVal ws As Worksheet)
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
' Procedure: RemovePicturesFromSheet
' Scope: Private Sub
'
' What it does:
'   Finds, creates, deletes, rebuilds, protects, or synchronizes worksheets
'   for RemovePicturesFromSheet.
'
' Why it exists:
'   The master workbook creates multiple operational views from one delivery
'   list; worksheet helpers keep those views from drifting apart.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub RemovePicturesFromSheet(ByVal ws As Worksheet)
    Dim shp As Shape

    On Error Resume Next
    For Each shp In ws.Shapes
        If shp.Type = msoPicture Or shp.Type = msoLinkedPicture Then
            shp.Delete
        End If
    Next shp
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: DeleteSheetIfExists
' Scope: Private Sub
'
' What it does:
'   Finds, creates, deletes, rebuilds, protects, or synchronizes worksheets
'   for DeleteSheetIfExists.
'
' Why it exists:
'   The master workbook creates multiple operational views from one delivery
'   list; worksheet helpers keep those views from drifting apart.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub DeleteSheetIfExists(ByVal wb As Workbook, ByVal sheetName As String)
    Dim ws As Worksheet
    Dim safeWs As Worksheet
    Dim oldAlerts As Boolean
    Dim oldEvents As Boolean
    Dim oldScreen As Boolean

    On Error Resume Next
    Set ws = wb.Worksheets(sheetName)
    On Error GoTo 0

    If ws Is Nothing Then Exit Sub
    If wb.Worksheets.Count <= 1 Then Exit Sub

    oldAlerts = Application.DisplayAlerts
    oldEvents = Application.EnableEvents
    oldScreen = Application.ScreenUpdating

    Application.DisplayAlerts = False
    Application.EnableEvents = False
    Application.ScreenUpdating = False

    On Error Resume Next

    'Make sure a different visible sheet is active before deleting
    For Each safeWs In wb.Worksheets
        If safeWs.Name <> ws.Name Then
            safeWs.Visible = xlSheetVisible
            safeWs.Activate
            Exit For
        End If
    Next safeWs

    ws.Unprotect Password:=""
    ws.Visible = xlSheetVisible
    ws.Delete

    Application.DisplayAlerts = oldAlerts
    Application.EnableEvents = oldEvents
    Application.ScreenUpdating = oldScreen
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: GetLastUsedRowTemplate
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   GetLastUsedRowTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetLastUsedRowTemplate(ByVal ws As Worksheet) As Long
    Dim f As Range
    Set f = ws.Cells.Find(What:="*", LookIn:=xlFormulas, SearchOrder:=xlByRows, SearchDirection:=xlPrevious)

    If f Is Nothing Then
        GetLastUsedRowTemplate = 0
    Else
        GetLastUsedRowTemplate = f.Row
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: GetUsedRangeLastRowTemplate
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   GetUsedRangeLastRowTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetUsedRangeLastRowTemplate(ByVal ws As Worksheet) As Long
    Dim rng As Range

    On Error Resume Next
    Set rng = ws.UsedRange
    On Error GoTo 0

    If rng Is Nothing Then
        GetUsedRangeLastRowTemplate = 0
    Else
        GetUsedRangeLastRowTemplate = rng.Row + rng.rows.Count - 1
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: CreateOrRefreshActionButtons
' Scope: Public Sub
'
' What it does:
'   Builds, formats, deletes, or wires workbook UI shapes/buttons/panels for
'   CreateOrRefreshActionButtons.
'
' Why it exists:
'   Buttons and utility panels are the operator-facing control surface, so
'   they must be rebuilt consistently after imports or sheet refreshes.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub CreateOrRefreshActionButtons()
    CreateOrRefreshHomeMenu
End Sub

'------------------------------------------------------------------------------
' Procedure: CreateOrRefreshHomeMenu
' Scope: Public Sub
'
' What it does:
'   Builds, formats, deletes, or wires workbook UI shapes/buttons/panels for
'   CreateOrRefreshHomeMenu.
'
' Why it exists:
'   Buttons and utility panels are the operator-facing control surface, so
'   they must be rebuilt consistently after imports or sheet refreshes.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub CreateOrRefreshHomeMenu()
    Dim ws As Worksheet
    Dim thm As BtnTheme
    thm = ThemePrimary()
    
    ' Per-button theme colors (only the Fill is different; Font stays white)
Dim thmImport As BtnTheme, thmUpdate As BtnTheme, thmPrint As BtnTheme, thmSave As BtnTheme
Dim thmExport As BtnTheme, thmSync As BtnTheme, thmManual As BtnTheme, thmEdit As BtnTheme

' Base each one on your current ThemePrimary() so the font color remains consistent
thmImport = ThemePrimary(): thmImport.Fill = RGB(47, 75, 117)   ' steel blue (current default)
thmUpdate = ThemePrimary(): thmUpdate.Fill = RGB(58, 84, 132)   ' slightly deeper
thmPrint = ThemePrimary(): thmPrint.Fill = RGB(63, 99, 151)    ' brighter steel
thmSave = ThemePrimary(): thmSave.Fill = RGB(52, 92, 140)      ' save (share) tone
thmExport = ThemePrimary(): thmExport.Fill = RGB(66, 110, 160)  ' export (upload) tone
thmSync = ThemePrimary(): thmSync.Fill = RGB(52, 82, 124)      ' sync tone
thmManual = ThemePrimary(): thmManual.Fill = RGB(69, 105, 155)  ' manual scan tone
thmEdit = ThemePrimary(): thmEdit.Fill = RGB(60, 95, 145)      ' edit mode tone

    EnsureReceiveDestinationName
    Set ws = EnsureHomeSheet()

    ' Style sheet & clear shapes
    StyleHomeSheet ws
    Dim shp As Shape
    On Error Resume Next
    For Each shp In ws.Shapes: shp.Delete: Next shp
    On Error GoTo 0

    ' === Title (rename to "Utility Panel") ===
    With ws.Range("H2:Q4")
        .Merge
        .Value = "Utility Panel"
        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
        .Font.Name = FONT_BASE
        .Font.Size = 20
        .Font.Bold = True
        .Font.Color = RGB(HEADER_TXT_R, HEADER_TXT_G, HEADER_TXT_B)
        .Interior.Color = RGB(HEADER_BG_R, HEADER_BG_G, HEADER_BG_B)
        .Borders.LineStyle = xlNone
    End With

    ' Subtitle
    With ws.Range("H5:Q6")
        .Merge
        .Value = "Streamlined actions for importing, updating, printing, exporting, syncing, and editing."
        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
        .WrapText = True
        .Font.Name = FONT_BASE
        .Font.Size = 11
        .Font.Color = RGB(INFO_TXT_R, INFO_TXT_G, INFO_TXT_B)
        .Interior.Color = RGB(INFO_BG_R, INFO_BG_G, INFO_BG_B)
        .Borders.LineStyle = xlNone
    End With

    ' === Section header spanning both columns ===
    With ws.Range("H8:Q8")
        .Merge
        .Value = "ACTIONS"
        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
        .Font.Name = FONT_BASE
        .Font.Bold = True
        .Font.Size = 11
        .Font.Color = RGB(HEADER_TXT_R, HEADER_TXT_G, HEADER_TXT_B)
        .Interior.Color = RGB(HEADER_BG_R, HEADER_BG_G, HEADER_BG_B)
    End With

    ' === Two symmetric action cards (no Help card) ===
    StylePanelCardRange ws.Range("H9:K31"), RGB(CARD_BG_R, CARD_BG_G, CARD_BG_B), RGB(CARD_BORDER_R, CARD_BORDER_G, CARD_BORDER_B)
    StylePanelCardRange ws.Range("N9:Q31"), RGB(CARD_BG_R, CARD_BG_G, CARD_BG_B), RGB(CARD_BORDER_R, CARD_BORDER_G, CARD_BORDER_B)


AddIconButton ws, "H11:K12", "btnHomeImport", GlyphFromCP(CP_IMPORT), _
              "IMPORT NEW DELIVERY LIST", "Loads a new delivery list", _
              "RunImportNewDeliveryListSafe", thm, RGB(255, 84, 61)

AddIconButton ws, "H14:K15", "btnHomeUpdate", GlyphFromCP(CP_UPDATE_ALT), _
              "UPDATE EXISTING LIST", "Appends new orders / remakes into the list", _
              "RunUpdateExistingDeliveryListSafe", thm, RGB(161, 59, 255)

AddIconButton ws, "H17:K18", "btnHomePrint", GlyphFromCP(CP_PRINT), _
              "PRINT LISTS", "Prints delivery / remake list for manual tracking", _
              "RunPrintDeliveryListBySectionSafe", thm, RGB(196, 196, 196)

AddIconButton ws, "H20:K21", "btnHomeSave", GlyphFromCP(CP_SHARE), _
              "SAVE SHAREPOINT COPY", "Save a copy ready for the Sharepoint", _
              "RunSaveCopyForSharePointSafe", thm, RGB(15, 235, 255)

AddIconButton ws, "H23:K24", "btnHomePublishSnapshots", GlyphFromCP(CP_UPDATE), _
              "PUBLISH SNAPSHOTS", "Posts latest snapshots to SharePoint", _
              "RunManualPublishAllStageSnapshotsSafe", thm, RGB(255, 117, 200)
              
AddIconButton ws, "H26:K27", "btnHomeRushOrders", GlyphFromCP(CP_PRINT), _
              "RUSH ORDERS", "Mark rush orders and print rush forms", _
              "RunRushOrdersFromUtilityPanelSafe", thm, RGB(255, 40, 40)

AddIconButton ws, "N20:Q21", "btnHomeExport", GlyphFromCP(CP_UP_ARROW), _
              "EXPORT EXCEL FILE", "Creates a excel file for manual tracking", _
              "RunExportListsFromUtilityPanelSafe", thm, RGB(15, 255, 179)

AddIconButton ws, "N17:Q18", "btnHomeSync", GlyphFromCP(CP_UPDATE), _
              "REFRESH SCANNER SHEETS", "Refreshes all scanner sheets", _
              "RunSyncDeliveryListToScannerSheetsSafe", thm, RGB(155, 255, 15)

AddIconButton ws, "N11:Q12", "btnHomeManualScan", GlyphFromCP(CP_KEYBOARD), _
              "MANUAL SCAN ENTRY", "Used to manualy scan a missed tag", _
              "RunManualScanFromUtilityPanelSafe", thm, RGB(255, 181, 54)

AddIconButton ws, "N14:Q15", "btnHomeEdit", GlyphFromCP(CP_EDIT), _
              "OPEN DELIVERY LIST (EDIT MODE)", "Temporarily unlocks the list for manual edits.", _
              "RunOpenDeliveryListForEditingSafe", thm, RGB(255, 239, 15)
              
If IsExternalQueuePaused() Then
    AddIconButton ws, "N23:Q24", "btnHomeQueueToggle", GlyphFromCP(CP_UPDATE), _
                  "QUEUE PAUSED", "Click to resume scan processing", _
                  "ToggleQueueMaintenanceMode", thm, RGB(255, 84, 61)
Else
    AddIconButton ws, "N23:Q24", "btnHomeQueueToggle", GlyphFromCP(CP_UPDATE), _
                  "QUEUE RUNNING", "Click to pause for maintenance", _
                  "ToggleQueueMaintenanceMode", thm, RGB(15, 235, 255)
End If

    ProtectUtilityPanel ws
End Sub

'------------------------------------------------------------------------------
' Procedure: EnsureHomeSheet
' Scope: Private Function
'
' What it does:
'   Finds, creates, deletes, rebuilds, protects, or synchronizes worksheets
'   for EnsureHomeSheet.
'
' Why it exists:
'   The master workbook creates multiple operational views from one delivery
'   list; worksheet helpers keep those views from drifting apart.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function EnsureHomeSheet() As Worksheet
    Dim ws As Worksheet
    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets("Utility Panel")
    On Error GoTo 0

    If ws Is Nothing Then
        Set ws = ThisWorkbook.Worksheets.Add(Before:=ThisWorkbook.Worksheets(1))
        ws.Name = "Utility Panel"
    ElseIf ws.Index <> 1 Then
        ws.Move Before:=ThisWorkbook.Worksheets(1)
    End If

    Set EnsureHomeSheet = ws
End Function

'------------------------------------------------------------------------------
' Procedure: StyleHomeSheet
' Scope: Private Sub
'
' What it does:
'   Finds, creates, deletes, rebuilds, protects, or synchronizes worksheets
'   for StyleHomeSheet.
'
' Why it exists:
'   The master workbook creates multiple operational views from one delivery
'   list; worksheet helpers keep those views from drifting apart.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub StyleHomeSheet(ByVal ws As Worksheet)
    On Error Resume Next: ws.Unprotect Password:="": On Error GoTo 0
    ws.Activate
    ActiveWindow.DisplayGridlines = False

    ' Reset and set background first
    ws.Cells.Clear
    ws.Cells.Locked = False
    ws.Tab.Color = RGB(153, 0, 0)

    ws.Cells.Interior.Pattern = xlSolid
    ws.Cells.Interior.Color = RGB(THEME_BG_R, THEME_BG_G, THEME_BG_B)

    ' Layout
    ws.Columns("A:G").ColumnWidth = 7
    ws.Columns("H:K").ColumnWidth = 18.5
    ws.Columns("L:M").ColumnWidth = 0.25
    ws.Columns("N:Q").ColumnWidth = 18.5
    ws.Columns("R:S").ColumnWidth = 4

    ws.rows("1:36").RowHeight = 20
    ws.rows(2).RowHeight = 28
    ws.rows(3).RowHeight = 28
    ws.rows(5).RowHeight = 24

    ws.Protect Password:="", UserInterfaceOnly:=True
End Sub

'------------------------------------------------------------------------------
' Procedure: ClearHomeMenuShapes
' Scope: Private Sub
'
' What it does:
'   Builds, formats, deletes, or wires workbook UI shapes/buttons/panels for
'   ClearHomeMenuShapes.
'
' Why it exists:
'   Buttons and utility panels are the operator-facing control surface, so
'   they must be rebuilt consistently after imports or sheet refreshes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ClearHomeMenuShapes(ByVal ws As Worksheet)
    Dim shp As Shape
    On Error Resume Next
    For Each shp In ws.Shapes
        shp.Delete
    Next shp
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: ProtectUtilityPanel
' Scope: Private Sub
'
' What it does:
'   Controls worksheet/workbook protection or read-only safety behavior for
'   ProtectUtilityPanel.
'
' Why it exists:
'   Protection keeps operators from accidentally editing formula/layout areas
'   while still allowing the intended scan or comment cells to work.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ProtectUtilityPanel(ByVal ws As Worksheet)
    On Error Resume Next: ws.Unprotect Password:="": On Error GoTo 0
    ws.Cells.Locked = True
    ws.EnableSelection = xlNoRestrictions
    ws.Protect Password:="", UserInterfaceOnly:=True, DrawingObjects:=False, Contents:=True, Scenarios:=True
End Sub
' Draw a clean card background with ONLY the outer border (no inner gridlines)

'------------------------------------------------------------------------------
' Procedure: StylePanelCardRange
' Scope: Private Sub
'
' What it does:
'   Builds, formats, deletes, or wires workbook UI shapes/buttons/panels for
'   StylePanelCardRange.
'
' Why it exists:
'   Buttons and utility panels are the operator-facing control surface, so
'   they must be rebuilt consistently after imports or sheet refreshes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub StylePanelCardRange(ByVal rng As Range, ByVal fillRgb As Long, Optional ByVal borderRgb As Long = -1)
    If borderRgb = -1 Then borderRgb = RGB(CARD_BORDER_R, CARD_BORDER_G, CARD_BORDER_B)

    ' Fill the whole card area
    rng.Interior.Color = fillRgb

    ' Clear any existing inside lines
    With rng.Borders(xlInsideHorizontal)
        .LineStyle = xlNone
    End With
    With rng.Borders(xlInsideVertical)
        .LineStyle = xlNone
    End With

    ' Draw ONLY the outer frame
    With rng.Borders(xlEdgeLeft)
        .LineStyle = xlContinuous
        .Weight = xlThin
        .Color = borderRgb
    End With
    With rng.Borders(xlEdgeTop)
        .LineStyle = xlContinuous
        .Weight = xlThin
        .Color = borderRgb
    End With
    With rng.Borders(xlEdgeRight)
        .LineStyle = xlContinuous
        .Weight = xlThin
        .Color = borderRgb
    End With
    With rng.Borders(xlEdgeBottom)
        .LineStyle = xlContinuous
        .Weight = xlThin
        .Color = borderRgb
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: BuildUtilityCaptionTemplate
' Scope: Private Function
'
' What it does:
'   Builds a derived value, key, JSON block, layout, collection, or workbook
'   object used later by the workflow (BuildUtilityCaptionTemplate).
'
' Why it exists:
'   The project uses generated keys/layouts to keep repeated logic consistent
'   instead of hand-building values in multiple places.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BuildUtilityCaptionTemplate(ByVal titleText As String, Optional ByVal subtitleText As String = "") As String
    If Len(subtitleText) > 0 Then
        BuildUtilityCaptionTemplate = titleText & vbLf & subtitleText
    Else
        BuildUtilityCaptionTemplate = titleText
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: BuildUtilityHelpTextTemplate
' Scope: Private Function
'
' What it does:
'   Builds a derived value, key, JSON block, layout, collection, or workbook
'   object used later by the workflow (BuildUtilityHelpTextTemplate).
'
' Why it exists:
'   The project uses generated keys/layouts to keep repeated logic consistent
'   instead of hand-building values in multiple places.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BuildUtilityHelpTextTemplate() As String
    Dim txt As String

    txt = "SYNC = rebuilds the scanner tabs after manual edits." & vbLf & _
          "SCAN = applies a manual scan when a barcode cannot be scanned." & vbLf & _
          "SAVE = creates a SharePoint-ready macro copy." & vbLf & _
          "EDIT = opens the Delivery List for direct changes." & vbLf & _
          "LIST / OUTBOUND / RECEIVE = jump straight to the main working sheets." & vbLf

    If GreenvilleSheetExistsTemplate() Then
        txt = txt & "GREENVILLE = opens the separate Greenville inbound sheet." & vbLf
    End If

    If CPUSheetExistsTemplate() Then
        txt = txt & "CPU = opens the Customer Pickup sheet." & vbLf
    End If

    txt = txt & "Current receiving sheet: " & GetReceiveSheetName() & vbLf & _
                "Gridlines stay off each time the Utility Panel is rebuilt."

    BuildUtilityHelpTextTemplate = txt
End Function

'------------------------------------------------------------------------------
' Procedure: GetUtilityGlyphTemplate
' Scope: Private Function
'
' What it does:
'   Returns a workbook object, setting, status value, parsed value, or
'   calculated result used by other procedures (GetUtilityGlyphTemplate).
'
' Why it exists:
'   Using one getter keeps callers from duplicating lookup logic and protects
'   them from missing sheets, missing names, or blank values.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetUtilityGlyphTemplate(ByVal glyphKey As String) As String
    Select Case UCase$(glyphKey)
        Case "IMPORT"
            GetUtilityGlyphTemplate = ChrW(&HE118)
        Case "UPDATE"
            GetUtilityGlyphTemplate = ChrW(&HE72C)
        Case "PRINT"
            GetUtilityGlyphTemplate = ChrW(&HE749)
        Case "EXPORT"
            GetUtilityGlyphTemplate = ChrW(&HE74E)
        Case "SCAN"
            GetUtilityGlyphTemplate = ChrW(&HE721)
        Case "SAVE"
            GetUtilityGlyphTemplate = ChrW(&HE74E)
        Case "EDIT"
            GetUtilityGlyphTemplate = ChrW(&HE70F)
        Case "LIST"
            GetUtilityGlyphTemplate = ChrW(&HE14C)
        Case "OUTBOUND"
            GetUtilityGlyphTemplate = ChrW(&HE7C3)
        Case "RECEIVE"
            GetUtilityGlyphTemplate = ChrW(&HE8F9)
        Case "GREENVILLE"
            GetUtilityGlyphTemplate = ChrW(&HE707)
        Case "CPU"
            GetUtilityGlyphTemplate = ChrW(&HE719)
        Case Else
            GetUtilityGlyphTemplate = ChrW(&H25A0)
    End Select
End Function

'------------------------------------------------------------------------------
' Procedure: AddIconButtonTemplate
' Scope: Private Sub
'
' What it does:
'   Builds, formats, deletes, or wires workbook UI shapes/buttons/panels for
'   AddIconButtonTemplate.
'
' Why it exists:
'   Buttons and utility panels are the operator-facing control surface, so
'   they must be rebuilt consistently after imports or sheet refreshes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub AddIconButtonTemplate(ByVal ws As Worksheet, ByVal anchorRangeAddress As String, _
                                  ByVal shapeName As String, _
                                  ByVal btnW As Double, ByVal btnH As Double, _
                                  ByVal glyphKey As String, _
                                  ByVal captionText As String, ByVal macroName As String, _
                                  ByVal fillRgb As Long, ByVal fontRgb As Long)

    Dim r As Range
    Dim btn As Shape
    Dim iconBox As Shape
    Dim leftPos As Double
    Dim topPos As Double
    Dim iconPad As Double
    Dim iconW As Double
    Dim arr(1) As Variant

    Set r = ws.Range(anchorRangeAddress)

    btnW = FitInTemplate(r.Width, btnW, 120)
    btnH = FitInTemplate(r.Height, btnH, 24)

    leftPos = r.Left + (r.Width - btnW) / 2
    topPos = r.Top + (r.Height - btnH) / 2

    Set btn = ws.Shapes.AddShape(msoShapeRoundedRectangle, leftPos, topPos, btnW, btnH)

    With btn
        .Name = shapeName & "_btn"
        .Fill.Visible = msoTrue
        .Fill.Solid
        .Fill.foreColor.RGB = fillRgb
        .Line.Visible = msoTrue
        .Line.foreColor.RGB = RGB(255, 255, 255)
        .Line.Transparency = 0.82
        .Line.Weight = 1

        On Error Resume Next
        .Shadow.Visible = msoTrue
        .Shadow.foreColor.RGB = RGB(120, 120, 120)
        .Shadow.Transparency = 0.68
        .Shadow.OffsetX = 1
        .Shadow.OffsetY = 1.25
        .SoftEdge.Radius = 1.5
        On Error GoTo 0

        With .TextFrame2
            .VerticalAnchor = msoAnchorMiddle
            .WordWrap = msoTrue
            .MarginLeft = IIf(btnH >= 40, 44, 38)
            .MarginRight = 10
            .MarginTop = 4
            .MarginBottom = 4
            .TextRange.Text = captionText
            .TextRange.ParagraphFormat.Alignment = msoAlignLeft
            .TextRange.ParagraphFormat.SpaceWithin = 1
            .TextRange.ParagraphFormat.SpaceAfter = 0

            With .TextRange.Font
                .Name = UP_FONT_BASE
                .Size = IIf(btnH >= 40, 11.5, 10)
                .Bold = msoTrue
                .Fill.foreColor.RGB = fontRgb
            End With

            If InStr(captionText, vbLf) > 0 Then
                On Error Resume Next
                With .TextRange.Paragraphs(2).Font
                    .Name = UP_FONT_BASE
                    .Size = IIf(btnH >= 40, 8.75, 8)
                    .Bold = msoFalse
                    .Fill.foreColor.RGB = fontRgb
                End With
                On Error GoTo 0
            End If
        End With
    End With

    iconPad = 6
    iconW = btnH - (iconPad * 2)

    Set iconBox = AddGlyphShapeTemplate(ws, leftPos + iconPad, topPos + iconPad, iconW, iconW, _
                                        GetUtilityGlyphTemplate(glyphKey), fillRgb, fontRgb)

    arr(0) = btn.Name
    arr(1) = iconBox.Name
    ws.Shapes.Range(arr).Group.Name = shapeName
    ws.Shapes(shapeName).OnAction = "'" & ThisWorkbook.Name & "'!" & macroName
End Sub

'------------------------------------------------------------------------------
' Procedure: AddGlyphShapeTemplate
' Scope: Private Function
'
' What it does:
'   Builds, formats, deletes, or wires workbook UI shapes/buttons/panels for
'   AddGlyphShapeTemplate.
'
' Why it exists:
'   Buttons and utility panels are the operator-facing control surface, so
'   they must be rebuilt consistently after imports or sheet refreshes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function AddGlyphShapeTemplate(ByVal ws As Worksheet, ByVal leftPos As Double, ByVal topPos As Double, _
                                       ByVal boxW As Double, ByVal boxH As Double, ByVal glyphText As String, _
                                       ByVal backColor As Long, ByVal foreColor As Long) As Shape
    Dim s As Shape

    Set s = ws.Shapes.AddShape(msoShapeRoundedRectangle, leftPos, topPos, boxW, boxH)

    With s
        .Name = "ico_" & Format$(Timer * 1000, "0")
        .Fill.Solid
        .Fill.foreColor.RGB = backColor
        .Line.Visible = msoFalse

        With .TextFrame2
            .VerticalAnchor = msoAnchorMiddle
            .WordWrap = msoFalse
            .MarginLeft = 0
            .MarginRight = 0
            .MarginTop = 0
            .MarginBottom = 0
            .TextRange.Text = glyphText
            .TextRange.ParagraphFormat.Alignment = msoAlignCenter

            With .TextRange.Font
                .Name = UP_FONT_ICON
                .Size = boxH * 0.72
                .Bold = msoTrue
                .Fill.foreColor.RGB = foreColor
            End With
        End With
    End With

    Set AddGlyphShapeTemplate = s
End Function

'------------------------------------------------------------------------------
' Procedure: FitInTemplate
' Scope: Private Function
'
' What it does:
'   Performs the workbook-specific step named FitInTemplate inside
'   TemplateImporter.
'
' Why it exists:
'   The master workbook uses this module to turn a raw delivery list into the
'   operational sheets used by scanning, printing, exports, and intake
'   snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function FitInTemplate(ByVal slotValue As Double, ByVal targetValue As Double, ByVal minValue As Double) As Double
    Dim v As Double

    v = targetValue
    If v > slotValue Then v = slotValue
    If v < minValue Then v = minValue

    FitInTemplate = v
End Function

'------------------------------------------------------------------------------
' Procedure: StyleActionButton
' Scope: Private Sub
'
' What it does:
'   Builds, formats, deletes, or wires workbook UI shapes/buttons/panels for
'   StyleActionButton.
'
' Why it exists:
'   Buttons and utility panels are the operator-facing control surface, so
'   they must be rebuilt consistently after imports or sheet refreshes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub StyleActionButton(ByVal shp As Shape, ByVal fillRgb As Long, ByVal fontRgb As Long, _
                              ByVal borderRgb As Long, Optional ByVal isPrimary As Boolean = False)

    Dim fontSize As Double

    If shp.Height >= 40 Then
        fontSize = 12.25
    Else
        fontSize = 10.5
    End If

    With shp
        .Line.Visible = msoTrue
        .Line.foreColor.RGB = borderRgb
        .Line.Weight = IIf(isPrimary, 1.35, 1#)

        With .Fill
            .Visible = msoTrue
            .Solid
            .foreColor.RGB = fillRgb
            .Transparency = 0#
        End With

        On Error Resume Next
        .Shadow.Visible = msoTrue
        .Shadow.foreColor.RGB = RGB(120, 120, 120)
        .Shadow.Transparency = 0.72
        .Shadow.OffsetX = 1
        .Shadow.OffsetY = 1.25
        .SoftEdge.Radius = 1.5
        On Error GoTo 0

        With .TextFrame2
            .VerticalAnchor = msoAnchorMiddle
            .WordWrap = msoTrue
            .MarginLeft = 14
            .MarginRight = 10
            .MarginTop = 5
            .MarginBottom = 5
            .TextRange.ParagraphFormat.Alignment = msoAlignLeft
            .TextRange.ParagraphFormat.SpaceWithin = 1
            .TextRange.ParagraphFormat.SpaceAfter = 0

            With .TextRange.Font
                .Name = "Segoe UI"
                .Size = fontSize
                .Bold = msoTrue
                .Fill.foreColor.RGB = fontRgb
            End With

            If InStr(.TextRange.Text, vbLf) > 0 Then
                On Error Resume Next
                With .TextRange.Paragraphs(2).Font
                    .Name = "Segoe UI"
                    .Size = fontSize - 2
                    .Bold = msoFalse
                    .Fill.foreColor.RGB = fontRgb
                End With
                On Error GoTo 0
            End If
        End With
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: BuildMenuCaptionTemplate
' Scope: Private Function
'
' What it does:
'   Builds, formats, deletes, or wires workbook UI shapes/buttons/panels for
'   BuildMenuCaptionTemplate.
'
' Why it exists:
'   Buttons and utility panels are the operator-facing control surface, so
'   they must be rebuilt consistently after imports or sheet refreshes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BuildMenuCaptionTemplate(ByVal iconKey As String, ByVal titleText As String, _
                                          Optional ByVal subtitleText As String = "") As String
    Dim txt As String

    txt = GetUtilityIconTextTemplate(iconKey) & "  " & titleText

    If Len(subtitleText) > 0 Then
        txt = txt & vbLf & subtitleText
    End If

    BuildMenuCaptionTemplate = txt
End Function

'------------------------------------------------------------------------------
' Procedure: GetUtilityIconTextTemplate
' Scope: Private Function
'
' What it does:
'   Builds, formats, deletes, or wires workbook UI shapes/buttons/panels for
'   GetUtilityIconTextTemplate.
'
' Why it exists:
'   Buttons and utility panels are the operator-facing control surface, so
'   they must be rebuilt consistently after imports or sheet refreshes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetUtilityIconTextTemplate(ByVal iconKey As String) As String
    Select Case UCase$(iconKey)
        Case "IMPORT"
            GetUtilityIconTextTemplate = ChrW(&H21E9)   '?
        Case "UPDATE"
            GetUtilityIconTextTemplate = ChrW(&H21BB)   '?
        Case "PRINT"
            GetUtilityIconTextTemplate = ChrW(&H2399)   '?
        Case "EXPORT"
            GetUtilityIconTextTemplate = ChrW(&H21AA)   '?
        Case "SYNC"
            GetUtilityIconTextTemplate = ChrW(&H21C4)   '?
        Case "SCAN"
            GetUtilityIconTextTemplate = ChrW(&H2328)   '?
        Case "SAVE"
            GetUtilityIconTextTemplate = ChrW(&H21E3)   '?
        Case "EDIT"
            GetUtilityIconTextTemplate = ChrW(&H270E)   '?
        Case "LIST"
            GetUtilityIconTextTemplate = ChrW(&H2630)   '?
        Case "OUTBOUND"
            GetUtilityIconTextTemplate = ChrW(&H21E2)   '?
        Case "RECEIVE"
            GetUtilityIconTextTemplate = ChrW(&H21E3)   '?
        Case "GREENVILLE"
            GetUtilityIconTextTemplate = ChrW(&H2198)   '?
        Case "CPU"
            GetUtilityIconTextTemplate = ChrW(&H25C6)   '?
        Case Else
            GetUtilityIconTextTemplate = ChrW(&H2022)   'â¢
    End Select
End Function

'------------------------------------------------------------------------------
' Procedure: SyncDeliveryListToScannerSheets
' Scope: Public Sub
'
' What it does:
'   Pushes the current Delivery List into the operational scanner sheets and
'   refreshes related formatting/summary state.
'
' Why it exists:
'   The master needs each stage sheet to reflect the same order rows while
'   keeping stage-specific scan blocks and filters.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub SyncDeliveryListToScannerSheets(Optional ByVal showCompleteMessage As Boolean = True, _
                                          Optional ByVal backgroundMode As Boolean = False)
    Dim dataWs As Worksheet
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim firstDataRow As Long
    Dim orderCol As Long
    Dim itemCol As Long
    Dim prevSheet As Worksheet

    On Error GoTo ErrHandler

    On Error Resume Next
    Set prevSheet = ActiveSheet
    On Error GoTo ErrHandler

    If Not backgroundMode Then
        Application.ScreenUpdating = False
    End If

    Application.EnableEvents = False
    Application.DisplayAlerts = False

    Set dataWs = ThisWorkbook.Worksheets("Delivery List")

    On Error Resume Next
    dataWs.Unprotect Password:=""
    On Error GoTo ErrHandler

    ForceRow3HeightTemplate dataWs
    ScannerValidation.EnsureScanLayout dataWs
    ThisWorkbook.RefreshAllDeliveryListProcessStates dataWs
    AutoFitCommentColumnsTemplate dataWs

    Set orderHdr = FindHeaderCellTemplateInCols(dataWs, Array("Order Nr."), "A:N", 250)
    Set itemHdr = FindHeaderCellTemplateInCols(dataWs, Array("Item Nr.", "Item"), "A:N", 250)

    If Not orderHdr Is Nothing And Not itemHdr Is Nothing Then
        firstDataRow = orderHdr.Row + 1
        orderCol = orderHdr.Column
        itemCol = itemHdr.Column
        ReapplyRemakeMarkersTemplate dataWs, firstDataRow, orderCol, itemCol
    End If

RebuildAllScannerSheetsFromMain dataWs

'Main Delivery List summary only
CreateOrUpdateTopSummaryPanels dataWs
dataWs.Calculate

'Refresh scanner sheets through the normal mode-specific path
ThisWorkbook.RefreshAllOperationalSheets dataWs

'One more final correction after the full sync path
ThisWorkbook.FinalizeReceiveLocationSummaries

    ProtectViewOnlyTemplate dataWs

    If Not backgroundMode Then
        ApplyFreezePanesToOperationalSheets
        CreateOrRefreshHomeMenu

        On Error Resume Next
        ThisWorkbook.Worksheets("Utility Panel").Activate
        On Error GoTo ErrHandler
    Else
        If Not prevSheet Is Nothing Then
            On Error Resume Next
            prevSheet.Activate
            On Error GoTo ErrHandler
        End If
    End If

SafeExit:
    Application.DisplayAlerts = True
    Application.EnableEvents = True
    Application.ScreenUpdating = True

    If showCompleteMessage And Not backgroundMode Then
        MsgBox "Scanner sheets rebuilt from the Delivery List master sheet.", vbInformation, "Sync Complete"
    End If

    Exit Sub

ErrHandler:
    Application.DisplayAlerts = True
    Application.EnableEvents = True
    Application.ScreenUpdating = True

    If Err.Number <> 0 Then
        MsgBox "SyncDeliveryListToScannerSheets error " & Err.Number & ":" & vbCrLf & Err.Description, vbCritical, "Sync Error"
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplyTopTwoRowFreeze
' Scope: Private Sub
'
' What it does:
'   Controls the active sheet/window view, freeze panes, navigation, or
'   selected cell for ApplyTopTwoRowFreeze.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ApplyTopTwoRowFreeze(ByVal ws As Worksheet)
    Dim prevSheet As Worksheet

    If ws Is Nothing Then Exit Sub

    On Error Resume Next
    Set prevSheet = ActiveSheet
    On Error GoTo 0

    ws.Activate
    With ActiveWindow
        .FreezePanes = False
        .SplitColumn = 0
        .SplitRow = 5
    End With
    ws.Range("A6").Select
    ActiveWindow.FreezePanes = True

    On Error Resume Next
    If Not prevSheet Is Nothing Then prevSheet.Activate
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplyFreezePanesToOperationalSheets
' Scope: Public Sub
'
' What it does:
'   Controls the active sheet/window view, freeze panes, navigation, or
'   selected cell for ApplyFreezePanesToOperationalSheets.
'
' Why it exists:
'   The workbook is used by scanners/operators, so opening the right view and
'   scan area reduces missed scans and operator confusion.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub ApplyFreezePanesToOperationalSheets()
    On Error Resume Next

    ApplyTopTwoRowFreeze ThisWorkbook.Worksheets("Delivery List")
    ApplyTopTwoRowFreeze ThisWorkbook.Worksheets("Staging - Airport Rd")
    ApplyTopTwoRowFreeze ThisWorkbook.Worksheets("Outbound - Airport Rd")
    ApplyTopTwoRowFreeze GetReceiveSheet()

    If GreenvilleSheetExistsTemplate() Then
        ApplyTopTwoRowFreeze ThisWorkbook.Worksheets(GREENVILLE_RECV_SHEET_NAME)
    End If

    If CPUSheetExistsTemplate() Then
        ApplyTopTwoRowFreeze ThisWorkbook.Worksheets(CPU_SHEET_NAME)
    End If

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: PrintDeliveryListBySection
' Scope: Public Sub
'
' What it does:
'   Prints or prepares print preview output for delivery/remake lists
'   (PrintDeliveryListBySection).
'
' Why it exists:
'   Print output needs consistent filtering, page setup, titles, and sections
'   so shop paperwork matches the selected workflow.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub PrintDeliveryListBySection()
    Dim ws As Worksheet
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim orderCol As Long
    Dim itemCol As Long
    Dim firstDataRow As Long
    Dim lastRealRow As Long
    Dim destinationMode As String
    Dim printKind As String
    Dim selectedGlassKeys As String
    Dim selectedAction As String
    Dim sections As Collection
    Dim selectedCopies As Long

    On Error GoTo ErrHandler

    Set ws = ThisWorkbook.Worksheets("Delivery List")

    Set orderHdr = FindHeaderCellTemplateInCols(ws, Array("Order Nr."), "A:N", 250)
    Set itemHdr = FindHeaderCellTemplateInCols(ws, Array("Item Nr.", "Item"), "A:N", 250)

    If orderHdr Is Nothing Or itemHdr Is Nothing Then
        MsgBox "Could not find the Delivery List headers.", vbExclamation, "Print Delivery List"
        Exit Sub
    End If

    orderCol = orderHdr.Column
    itemCol = itemHdr.Column
    firstDataRow = orderHdr.Row + 1
    lastRealRow = FindLastRealDeliveryRowTemplate(ws, orderCol, itemCol, firstDataRow)

    If lastRealRow < firstDataRow Then
        MsgBox "There are no printable delivery lines on the Delivery List.", vbExclamation, "Print Delivery List"
        Exit Sub
    End If

    If Not PromptForPrintOptionsTemplate(ws, firstDataRow, lastRealRow, orderCol, itemCol, _
                                         printKind, destinationMode, selectedGlassKeys, selectedAction, selectedCopies) Then
        Exit Sub
    End If

    Set sections = GetDeliveryListSectionsForPrintKind(ws, firstDataRow, lastRealRow, orderCol, itemCol, destinationMode, printKind)
    If sections Is Nothing Or sections.Count = 0 Then
        MsgBox "There are no rows that match the selected destination/filter.", vbInformation, "Print Delivery List"
        Exit Sub
    End If

    If UCase$(printKind) = "REMAKES" Or UCase$(printKind) = "UPDATED_REMAKES" Then
        BuildAndPreviewRemakePrintFromTemplate ws, 0, 0, firstDataRow, lastRealRow, _
                                               orderCol, itemCol, destinationMode, _
                                               selectedGlassKeys, printKind, selectedAction, selectedCopies
    Else
        BuildAndPreviewDeliveryListPrint ws, 0, 0, firstDataRow, lastRealRow, _
                                         orderCol, itemCol, destinationMode, _
                                         selectedGlassKeys, printKind, selectedAction, selectedCopies
    End If

    Exit Sub

ErrHandler:
    MsgBox "PrintDeliveryListBySection error " & Err.Number & ":" & vbCrLf & Err.Description, vbCritical, "Print Error"
End Sub

'------------------------------------------------------------------------------
' Procedure: PromptForPrintDestinationMode
' Scope: Private Function
'
' What it does:
'   Performs the workbook-specific step named PromptForPrintDestinationMode
'   inside TemplateImporter.
'
' Why it exists:
'   The master workbook uses this module to turn a raw delivery list into the
'   operational sheets used by scanning, printing, exports, and intake
'   snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function PromptForPrintDestinationMode() As String
    Dim choice As Variant
    Dim raw As String

    choice = Application.InputBox( _
        "Select destination(s):" & vbCrLf & vbCrLf & _
        "0 = All destinations" & vbCrLf & _
        "1 = Indian Trail" & vbCrLf & _
        "2 = Greenville" & vbCrLf & _
        "3 = Customer Pickup" & vbCrLf & vbCrLf & _
        "You can enter multiple values separated by commas." & vbCrLf & _
        "Example: 1,3", _
        "Select Destination(s)", Type:=2)

    If VarType(choice) = vbBoolean Then Exit Function

    raw = Trim$(CStr(choice))
    raw = Replace$(raw, " ", "")
    raw = Replace$(raw, ";", ",")

    If raw = "0" Then
        PromptForPrintDestinationMode = "ALL"
        Exit Function
    End If

    PromptForPrintDestinationMode = BuildDestinationModeListTemplate(raw)

    If Len(PromptForPrintDestinationMode) = 0 Then
        MsgBox "Invalid destination selection.", vbExclamation, "Print Selection"
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: BuildDestinationModeListTemplate
' Scope: Private Function
'
' What it does:
'   Builds a derived value, key, JSON block, layout, collection, or workbook
'   object used later by the workflow (BuildDestinationModeListTemplate).
'
' Why it exists:
'   The project uses generated keys/layouts to keep repeated logic consistent
'   instead of hand-building values in multiple places.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BuildDestinationModeListTemplate(ByVal raw As String) As String
    Dim parts() As String
    Dim i As Long
    Dim token As String
    Dim outText As String

    If Len(raw) = 0 Then Exit Function

    parts = Split(raw, ",")

    For i = LBound(parts) To UBound(parts)
        Select Case Trim$(parts(i))
            Case "1"
                AddTokenTemplate outText, "STANDARD"
            Case "2"
                AddTokenTemplate outText, "GREENVILLE"
            Case "3"
                AddTokenTemplate outText, "CPU"
            Case "0"
                BuildDestinationModeListTemplate = "ALL"
                Exit Function
            Case Else
                BuildDestinationModeListTemplate = vbNullString
                Exit Function
        End Select
    Next i

    BuildDestinationModeListTemplate = outText
End Function

'------------------------------------------------------------------------------
' Procedure: AddTokenTemplate
' Scope: Private Sub
'
' What it does:
'   Performs the workbook-specific step named AddTokenTemplate inside
'   TemplateImporter.
'
' Why it exists:
'   The master workbook uses this module to turn a raw delivery list into the
'   operational sheets used by scanning, printing, exports, and intake
'   snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub AddTokenTemplate(ByRef tokenList As String, ByVal token As String)
    If Len(token) = 0 Then Exit Sub

    If Not TokenListContainsTemplate(tokenList, token) Then
        If Len(tokenList) > 0 Then
            tokenList = tokenList & "|"
        End If
        tokenList = tokenList & UCase$(token)
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: TokenListContainsTemplate
' Scope: Private Function
'
' What it does:
'   Performs the workbook-specific step named TokenListContainsTemplate inside
'   TemplateImporter.
'
' Why it exists:
'   The master workbook uses this module to turn a raw delivery list into the
'   operational sheets used by scanning, printing, exports, and intake
'   snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function TokenListContainsTemplate(ByVal tokenList As String, ByVal token As String) As Boolean
    Dim parts() As String
    Dim i As Long

    token = UCase$(Trim$(token))
    tokenList = UCase$(Trim$(tokenList))

    If tokenList = "ALL" Then
        TokenListContainsTemplate = True
        Exit Function
    End If

    If Len(tokenList) = 0 Then Exit Function

    parts = Split(tokenList, "|")
    For i = LBound(parts) To UBound(parts)
        If Trim$(parts(i)) = token Then
            TokenListContainsTemplate = True
            Exit Function
        End If
    Next i
End Function

'------------------------------------------------------------------------------
' Procedure: DestinationNeedsRouteColumnTemplate
' Scope: Private Function
'
' What it does:
'   Finds, sizes, hides, formats, or uses worksheet columns for
'   DestinationNeedsRouteColumnTemplate.
'
' Why it exists:
'   The system depends on fixed scan blocks and discovered delivery-list
'   columns, so column handling must be centralized and predictable.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function DestinationNeedsRouteColumnTemplate(ByVal destinationMode As String) As Boolean
    DestinationNeedsRouteColumnTemplate = _
        TokenListContainsTemplate(destinationMode, "ALL") Or _
        TokenListContainsTemplate(destinationMode, "CPU")
End Function

'------------------------------------------------------------------------------
' Procedure: PromptForGlassSectionChoice
' Scope: Private Function
'
' What it does:
'   Performs the workbook-specific step named PromptForGlassSectionChoice
'   inside TemplateImporter.
'
' Why it exists:
'   The master workbook uses this module to turn a raw delivery list into the
'   operational sheets used by scanning, printing, exports, and intake
'   snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function PromptForGlassSectionChoice(ByVal sections As Collection, ByVal destinationMode As String) As Long
    Dim promptText As String
    Dim choice As Variant
    Dim i As Long
    Dim sectionInfo As Variant

    promptText = "Select glass type for " & GetDestinationLabel(destinationMode) & ":" & vbCrLf & vbCrLf & _
                 "0 = All glass types"

    For i = 1 To sections.Count
        sectionInfo = sections(i)
        promptText = promptText & vbCrLf & CStr(i) & " = " & CStr(sectionInfo(0))
    Next i

    choice = Application.InputBox(promptText, "Select Glass Type", Type:=1)

    If VarType(choice) = vbBoolean Then
        PromptForGlassSectionChoice = -1
        Exit Function
    End If

    If CLng(choice) = 0 Then
        PromptForGlassSectionChoice = 0
        Exit Function
    End If

    If CLng(choice) < 1 Or CLng(choice) > sections.Count Then
        MsgBox "Invalid glass selection.", vbExclamation, "Print Delivery List"
        PromptForGlassSectionChoice = -1
        Exit Function
    End If

    PromptForGlassSectionChoice = CLng(choice)
End Function

'------------------------------------------------------------------------------
' Procedure: GetDestinationLabel
' Scope: Private Function
'
' What it does:
'   Returns a workbook object, setting, status value, parsed value, or
'   calculated result used by other procedures (GetDestinationLabel).
'
' Why it exists:
'   Using one getter keeps callers from duplicating lookup logic and protects
'   them from missing sheets, missing names, or blank values.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetDestinationLabel(ByVal destinationMode As String) As String
    Dim txt As String

    If UCase$(Trim$(destinationMode)) = "ALL" Then
        GetDestinationLabel = "all destinations"
        Exit Function
    End If

    If TokenListContainsTemplate(destinationMode, "STANDARD") Then
        txt = "Indian Trail"
    End If

    If TokenListContainsTemplate(destinationMode, "GREENVILLE") Then
        If Len(txt) > 0 Then txt = txt & ", "
        txt = txt & "Greenville"
    End If

    If TokenListContainsTemplate(destinationMode, "CPU") Then
        If Len(txt) > 0 Then txt = txt & ", "
        txt = txt & "Customer Pickup"
    End If

    If Len(txt) = 0 Then txt = "selected destination(s)"
    GetDestinationLabel = txt
End Function

'------------------------------------------------------------------------------
' Procedure: GetDeliveryListSectionsForDestination
' Scope: Private Function
'
' What it does:
'   Returns a workbook object, setting, status value, parsed value, or
'   calculated result used by other procedures
'   (GetDeliveryListSectionsForDestination).
'
' Why it exists:
'   Using one getter keeps callers from duplicating lookup logic and protects
'   them from missing sheets, missing names, or blank values.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetDeliveryListSectionsForDestination(ByVal ws As Worksheet, ByVal firstDataRow As Long, ByVal lastRealRow As Long, _
                                                       ByVal orderCol As Long, ByVal itemCol As Long, _
                                                       ByVal destinationMode As String) As Collection
    Dim sections As Collection
    Dim currentTitle As String
    Dim currentStart As Long
    Dim r As Long

    Set sections = New Collection
    currentTitle = vbNullString
    currentStart = 0

    For r = firstDataRow To lastRealRow
        If IsSectionHeaderRowTemplate(ws, r, orderCol, itemCol) Then
            If currentStart > 0 Then
                If SectionContainsDestinationRows(ws, currentStart, r - 1, orderCol, itemCol, destinationMode) Then
                    sections.Add Array(currentTitle, currentStart, r - 1)
                End If
            End If

            currentTitle = Trim$(CStr(ws.Cells(r, 1).Value))
            currentStart = r
        End If
    Next r

    If currentStart > 0 Then
        If SectionContainsDestinationRows(ws, currentStart, lastRealRow, orderCol, itemCol, destinationMode) Then
            sections.Add Array(currentTitle, currentStart, lastRealRow)
        End If
    End If

    Set GetDeliveryListSectionsForDestination = sections
End Function

'------------------------------------------------------------------------------
' Procedure: SectionContainsDestinationRows
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   SectionContainsDestinationRows.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SectionContainsDestinationRows(ByVal ws As Worksheet, ByVal startRow As Long, ByVal endRow As Long, _
                                                ByVal orderCol As Long, ByVal itemCol As Long, _
                                                ByVal destinationMode As String) As Boolean
    Dim r As Long

    For r = startRow To endRow
        If IsRealDeliveryLineTemplate(ws, r, orderCol, itemCol) Then
            If DoesDestinationMatchRowTemplate(ws, r, destinationMode) Then
                SectionContainsDestinationRows = True
                Exit Function
            End If
        End If
    Next r
End Function

'------------------------------------------------------------------------------
' Procedure: DoesDestinationMatchRowTemplate
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   DoesDestinationMatchRowTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function DoesDestinationMatchRowTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, ByVal destinationMode As String) As Boolean
    If UCase$(Trim$(destinationMode)) = "ALL" Then
        DoesDestinationMatchRowTemplate = True
        Exit Function
    End If

    If TokenListContainsTemplate(destinationMode, "STANDARD") Then
        If (Not IsGreenvilleRowTemplate(ws, rowNum) And Not IsCPURowTemplate(ws, rowNum)) Then
            DoesDestinationMatchRowTemplate = True
            Exit Function
        End If
    End If

    If TokenListContainsTemplate(destinationMode, "GREENVILLE") Then
        If IsGreenvilleRowTemplate(ws, rowNum) Then
            DoesDestinationMatchRowTemplate = True
            Exit Function
        End If
    End If

    If TokenListContainsTemplate(destinationMode, "CPU") Then
        If IsCPURowTemplate(ws, rowNum) Then
            DoesDestinationMatchRowTemplate = True
            Exit Function
        End If
    End If

    DoesDestinationMatchRowTemplate = False
End Function

'------------------------------------------------------------------------------
' Procedure: BuildAndPreviewDeliveryListPrint
' Scope: Private Sub
'
' What it does:
'   Controls the active sheet/window view, freeze panes, navigation, or
'   selected cell for BuildAndPreviewDeliveryListPrint.
'
' Why it exists:
'   The workbook is used by scanners/operators, so opening the right view and
'   scan area reduces missed scans and operator confusion.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub BuildAndPreviewDeliveryListPrint(ByVal srcWs As Worksheet, _
                                             ByVal sectionStartRow As Long, ByVal sectionEndRow As Long, _
                                             ByVal firstDataRow As Long, ByVal lastRealRow As Long, _
                                             ByVal orderCol As Long, ByVal itemCol As Long, _
                                             ByVal destinationMode As String, _
                                             ByVal selectedGlassKeys As String, _
                                             Optional ByVal printKind As String = "ORDERS", _
                                             Optional ByVal selectedAction As String = "PREVIEW", _
                                             Optional ByVal selectedCopies As Long = 1)
    Dim baseWs As Worksheet
    Dim previewWs As Worksheet
    Dim prevSheet As Worksheet
    Dim oldDisplayAlerts As Boolean
    Dim oldScreenUpdating As Boolean
    Dim destRow As Long
    Dim r As Long
    Dim scanStart As Long
    Dim scanEnd As Long
    Dim currentSectionTitle As String
    Dim currentHeaderRow As Long
    Dim printedAnyInSection As Boolean
    Dim printedAnyRows As Boolean
    Dim baseLastRow As Long
    Dim previewLastRow As Long
    Dim breakRows As Collection
    Dim i As Long
    Dim visibleLastCol As String

    On Error GoTo SafeExit

    oldDisplayAlerts = Application.DisplayAlerts
    oldScreenUpdating = Application.ScreenUpdating
    Application.DisplayAlerts = False
    Application.ScreenUpdating = False

    Set prevSheet = ActiveSheet
    visibleLastCol = GetPrintLastColForDestination(destinationMode)

    DeleteSheetIfExists ThisWorkbook, "__PRINT_BASE__"
    DeleteSheetIfExists ThisWorkbook, "__PRINT_PREVIEW__"

    Set baseWs = ThisWorkbook.Worksheets.Add(After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
    baseWs.Name = "__PRINT_BASE__"

    srcWs.Range("A:" & visibleLastCol).Copy
    baseWs.Range("A1").PasteSpecial xlPasteColumnWidths
    Application.CutCopyMode = False

    srcWs.Range("A1:" & visibleLastCol & "5").Copy
    baseWs.Range("A1").PasteSpecial xlPasteAll
    Application.CutCopyMode = False

    For i = 1 To 5
        baseWs.rows(i).RowHeight = srcWs.rows(i).RowHeight
    Next i

    ApplyDestinationAwareDeliveryTitleTemplate baseWs, srcWs, destinationMode
    CopyDeliveryListLogoToSheetTemplate srcWs, baseWs
    RepositionPrintPreviewLogoTemplate baseWs

    If sectionStartRow > 0 And sectionEndRow > 0 Then
        scanStart = sectionStartRow
        scanEnd = sectionEndRow
    Else
        scanStart = firstDataRow
        scanEnd = lastRealRow
    End If

    destRow = 6
    currentSectionTitle = vbNullString
    currentHeaderRow = 0
    printedAnyInSection = False
    printedAnyRows = False

    For r = scanStart To scanEnd
        If IsSectionHeaderRowTemplate(srcWs, r, orderCol, itemCol) Then
            currentSectionTitle = Trim$(CStr(srcWs.Cells(r, 1).Value))
            currentHeaderRow = r
            printedAnyInSection = False

        ElseIf IsRealDeliveryLineTemplate(srcWs, r, orderCol, itemCol) Then
    If DoesPrintModeMatchRowTemplate(srcWs, r, destinationMode, printKind) _
        And IsGlassSectionSelectedTemplate(currentSectionTitle, selectedGlassKeys) Then

        If Not printedAnyInSection And currentHeaderRow > 0 Then
            CopyPrintableRowForPrint srcWs, currentHeaderRow, baseWs, destRow, currentSectionTitle, "HEADER", visibleLastCol, destinationMode
            destRow = destRow + 1
            printedAnyInSection = True
        End If

        CopyPrintableRowForPrint srcWs, r, baseWs, destRow, currentSectionTitle, "LINE", visibleLastCol, destinationMode
        destRow = destRow + 1
        printedAnyRows = True
    End If
End If
    Next r

    If Not printedAnyRows Then
        MsgBox "There are no rows to preview for " & GetDestinationLabel(destinationMode) & ".", vbInformation, "Print Delivery List"
        GoTo SafeExit
    End If

    baseLastRow = destRow - 1
    ConfigureDeliveryListPrintPage baseWs, baseLastRow, visibleLastCol

    Set breakRows = GetPrintBreakRows(baseWs)

    Set previewWs = ThisWorkbook.Worksheets.Add(After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
previewWs.Name = "__PRINT_PREVIEW__"

'Copy only the visible print columns
baseWs.Range("A:" & visibleLastCol).Copy
previewWs.Range("A1").PasteSpecial xlPasteColumnWidths
Application.CutCopyMode = False

baseWs.Range("A1:" & visibleLastCol & baseLastRow).Copy
previewWs.Range("A1").PasteSpecial xlPasteAll
Application.CutCopyMode = False

'Copy helper columns separately so page-break logic still works
baseWs.Range("N:O").Copy
previewWs.Range("N1").PasteSpecial xlPasteColumnWidths
Application.CutCopyMode = False

baseWs.Range("N1:O" & baseLastRow).Copy
previewWs.Range("N1").PasteSpecial xlPasteAll
Application.CutCopyMode = False

ApplyDestinationAwareDeliveryTitleTemplate previewWs, srcWs, destinationMode
CopyDeliveryListLogoToSheetTemplate srcWs, previewWs
RepositionPrintPreviewLogoTemplate previewWs

previewLastRow = baseLastRow

If Not DestinationNeedsRouteColumnTemplate(destinationMode) Then
    On Error Resume Next
    baseWs.Range("K:N").EntireColumn.Delete
    previewWs.Range("K:N").EntireColumn.Delete
    On Error GoTo SafeExit

    visibleLastCol = "J"
End If

ApplyContinuationHeadersFromBaseBreaks baseWs, previewWs, breakRows, previewLastRow, baseLastRow
ConfigureDeliveryListPrintPage previewWs, previewLastRow, visibleLastCol

baseWs.Columns("N:O").Hidden = True
previewWs.Columns("N:O").Hidden = True

previewWs.Activate
previewWs.Range("A1").Select

If UCase$(selectedAction) = "PRINT" Then
    If selectedCopies < 1 Then selectedCopies = 1
    previewWs.PrintOut Copies:=selectedCopies
Else
    previewWs.PrintPreview
End If
SafeExit:
    On Error Resume Next

    If Not prevSheet Is Nothing Then prevSheet.Activate
    If Not previewWs Is Nothing Then previewWs.Delete
    If Not baseWs Is Nothing Then baseWs.Delete

    Application.DisplayAlerts = oldDisplayAlerts
    Application.ScreenUpdating = oldScreenUpdating
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: RemoveRouteFromNonCPUPrint
' Scope: Private Sub
'
' What it does:
'   Identifies, filters, formats, or routes Customer Pickup rows for
'   RemoveRouteFromNonCPUPrint.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub RemoveRouteFromNonCPUPrint(ByVal ws As Worksheet)
    If ws Is Nothing Then Exit Sub

    On Error Resume Next
    ws.Range("K1:K" & GetLastUsedRowTemplate(ws)).ClearContents
    ws.Columns("K").Hidden = True
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: GetPrintBreakRows
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   GetPrintBreakRows.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetPrintBreakRows(ByVal ws As Worksheet) As Collection
    Dim breaks As New Collection
    Dim i As Long

    If ws Is Nothing Then
        Set GetPrintBreakRows = breaks
        Exit Function
    End If

    ws.Activate
    DoEvents

    On Error Resume Next
    ws.DisplayPageBreaks = True
    On Error GoTo 0

    For i = 1 To ws.HPageBreaks.Count
        breaks.Add ws.HPageBreaks(i).Location.Row
    Next i

    On Error Resume Next
    ws.DisplayPageBreaks = False
    On Error GoTo 0

    Set GetPrintBreakRows = breaks
End Function

'------------------------------------------------------------------------------
' Procedure: ApplyContinuationHeadersFromBaseBreaks
' Scope: Private Sub
'
' What it does:
'   Finds, writes, validates, or uses worksheet header cells for
'   ApplyContinuationHeadersFromBaseBreaks.
'
' Why it exists:
'   Header locations can move during import/rebuild, so the code uses header
'   discovery to target the correct columns instead of guessing.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ApplyContinuationHeadersFromBaseBreaks(ByVal baseWs As Worksheet, ByVal previewWs As Worksheet, _
                                                   ByVal breakRows As Collection, ByRef previewLastRow As Long, _
                                                   ByVal baseLastRow As Long)
    Dim i As Long
    Dim breakRow As Long
    Dim targetRow As Long
    Dim sectionTitle As String
    Dim templateHeaderRow As Long

    If baseWs Is Nothing Or previewWs Is Nothing Then Exit Sub
    If breakRows Is Nothing Then Exit Sub
    If breakRows.Count = 0 Then Exit Sub

    On Error Resume Next
    previewWs.ResetAllPageBreaks
    On Error GoTo 0

    For i = breakRows.Count To 1 Step -1
        breakRow = CLng(breakRows(i))

        If breakRow > 6 And breakRow <= baseLastRow Then
            targetRow = FindFirstHelperLineAtOrBelow(baseWs, breakRow, baseLastRow)

            If targetRow > 0 Then
                sectionTitle = Trim$(CStr(baseWs.Cells(targetRow, PRINT_HELPER_SECTION_COL).Value))

                If Len(sectionTitle) > 0 Then
                    templateHeaderRow = FindPrintHeaderTemplateAbove(baseWs, targetRow - 1, sectionTitle)

                    If templateHeaderRow > 0 Then
                        previewWs.rows(targetRow).Insert Shift:=xlDown, CopyOrigin:=xlFormatFromLeftOrAbove

                        baseWs.Range("A" & templateHeaderRow & ":O" & templateHeaderRow).Copy
                        previewWs.Range("A" & targetRow).PasteSpecial xlPasteAll
                        Application.CutCopyMode = False

                        previewWs.rows(targetRow).RowHeight = baseWs.rows(templateHeaderRow).RowHeight
                        previewWs.Cells(targetRow, 1).Value = BuildContinuationHeaderText(sectionTitle)
                        previewWs.Cells(targetRow, PRINT_HELPER_SECTION_COL).Value = sectionTitle
                        previewWs.Cells(targetRow, PRINT_HELPER_ROWTYPE_COL).Value = "CONT"

                        On Error Resume Next
                        previewWs.HPageBreaks.Add Before:=previewWs.rows(targetRow)
                        On Error GoTo 0

                        previewLastRow = previewLastRow + 1
                    End If
                End If
            End If
        End If
    Next i
End Sub

'------------------------------------------------------------------------------
' Procedure: CopyPrintableRowForPrint
' Scope: Private Sub
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   CopyPrintableRowForPrint.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub CopyPrintableRowForPrint(ByVal srcWs As Worksheet, ByVal srcRow As Long, ByVal destWs As Worksheet, _
                                     ByVal destRow As Long, ByVal sectionTitle As String, _
                                     ByVal rowType As String, ByVal visibleLastCol As String, _
                                     ByVal destinationMode As String)

    srcWs.Range("A" & srcRow & ":" & visibleLastCol & srcRow).Copy
    destWs.Range("A" & destRow).PasteSpecial xlPasteAll
    Application.CutCopyMode = False

    destWs.rows(destRow).RowHeight = srcWs.rows(srcRow).RowHeight
    destWs.Cells(destRow, PRINT_HELPER_SECTION_COL).Value = sectionTitle
    destWs.Cells(destRow, PRINT_HELPER_ROWTYPE_COL).Value = UCase$(rowType)

    'Plain print copy only: remove fills, font colors, and borders
    With destWs.Range("A" & destRow & ":" & visibleLastCol & destRow)
        .Interior.Pattern = xlNone
        .Font.ColorIndex = xlAutomatic
        .Font.Italic = False
        .Font.Underline = xlUnderlineStyleNone
        .Borders.LineStyle = xlNone
    End With

    'Keep section headers readable
    If UCase$(rowType) = "HEADER" Or UCase$(rowType) = "CONT" Then
        destWs.Range("A" & destRow & ":" & visibleLastCol & destRow).Font.Bold = True
    Else
        destWs.Range("A" & destRow & ":" & visibleLastCol & destRow).Font.Bold = False
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: ConfigureDeliveryListPrintPage
' Scope: Private Sub
'
' What it does:
'   Performs the workbook-specific step named ConfigureDeliveryListPrintPage
'   inside TemplateImporter.
'
' Why it exists:
'   The master workbook uses this module to turn a raw delivery list into the
'   operational sheets used by scanning, printing, exports, and intake
'   snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ConfigureDeliveryListPrintPage(ByVal ws As Worksheet, ByVal lastPrintRow As Long, ByVal lastPrintCol As String)
    With ws.PageSetup
        .PrintArea = ws.Range("A1:" & lastPrintCol & lastPrintRow).Address
        .Orientation = xlPortrait
        .PaperSize = xlPaperLetter
        .Zoom = False
        .FitToPagesWide = 1
        .FitToPagesTall = False
        .CenterHorizontally = True
        .CenterVertically = False
        .LeftMargin = Application.InchesToPoints(0.2)
        .RightMargin = Application.InchesToPoints(0.2)
        .TopMargin = Application.InchesToPoints(0.35)
        .BottomMargin = Application.InchesToPoints(0.35)
        .HeaderMargin = Application.InchesToPoints(0.15)
        .FooterMargin = Application.InchesToPoints(0.15)
        .PrintTitleRows = ""
        .CenterFooter = "Page &P of &N"
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: GetPrintLastColForDestination
' Scope: Private Function
'
' What it does:
'   Finds, sizes, hides, formats, or uses worksheet columns for
'   GetPrintLastColForDestination.
'
' Why it exists:
'   The system depends on fixed scan blocks and discovered delivery-list
'   columns, so column handling must be centralized and predictable.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetPrintLastColForDestination(ByVal destinationMode As String) As String
    GetPrintLastColForDestination = "L"
End Function

'------------------------------------------------------------------------------
' Procedure: FindPrintHeaderTemplateAbove
' Scope: Private Function
'
' What it does:
'   Finds, writes, validates, or uses worksheet header cells for
'   FindPrintHeaderTemplateAbove.
'
' Why it exists:
'   Header locations can move during import/rebuild, so the code uses header
'   discovery to target the correct columns instead of guessing.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function FindPrintHeaderTemplateAbove(ByVal ws As Worksheet, ByVal startRow As Long, ByVal sectionTitle As String) As Long
    Dim r As Long
    Dim rowType As String
    Dim rowSection As String

    For r = startRow To 6 Step -1
        rowType = UCase$(Trim$(CStr(ws.Cells(r, PRINT_HELPER_ROWTYPE_COL).Value)))
        rowSection = Trim$(CStr(ws.Cells(r, PRINT_HELPER_SECTION_COL).Value))

        If (rowType = "HEADER" Or rowType = "CONT") And _
           StrComp(rowSection, sectionTitle, vbTextCompare) = 0 Then
            FindPrintHeaderTemplateAbove = r
            Exit Function
        End If
    Next r
End Function

'------------------------------------------------------------------------------
' Procedure: FindSourceSectionHeaderAbove
' Scope: Private Function
'
' What it does:
'   Finds, writes, validates, or uses worksheet header cells for
'   FindSourceSectionHeaderAbove.
'
' Why it exists:
'   Header locations can move during import/rebuild, so the code uses header
'   discovery to target the correct columns instead of guessing.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function FindSourceSectionHeaderAbove(ByVal ws As Worksheet, ByVal startRow As Long, _
                                              ByVal orderCol As Long, ByVal itemCol As Long) As Long
    Dim r As Long

    For r = startRow To 6 Step -1
        If IsSectionHeaderRowTemplate(ws, r, orderCol, itemCol) Then
            FindSourceSectionHeaderAbove = r
            Exit Function
        End If
    Next r
End Function

'------------------------------------------------------------------------------
' Procedure: BuildContinuationHeaderText
' Scope: Private Function
'
' What it does:
'   Finds, writes, validates, or uses worksheet header cells for
'   BuildContinuationHeaderText.
'
' Why it exists:
'   Header locations can move during import/rebuild, so the code uses header
'   discovery to target the correct columns instead of guessing.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BuildContinuationHeaderText(ByVal headerText As String) As String
    headerText = Trim$(headerText)

    If Len(headerText) = 0 Then
        BuildContinuationHeaderText = "(cont.)"
    ElseIf InStr(1, headerText, "(cont.)", vbTextCompare) > 0 Then
        BuildContinuationHeaderText = headerText
    Else
        BuildContinuationHeaderText = headerText & " (cont.)"
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: FindFirstHelperLineAtOrBelow
' Scope: Private Function
'
' What it does:
'   Searches the workbook for a matching row, header, shape, request, or
'   related object (FindFirstHelperLineAtOrBelow).
'
' Why it exists:
'   The workbook layout can shift during imports/rebuilds, so code should
'   locate important positions instead of relying only on hardcoded
'   references.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function FindFirstHelperLineAtOrBelow(ByVal ws As Worksheet, ByVal startRow As Long, ByVal lastRow As Long) As Long
    Dim r As Long
    Dim rowType As String

    For r = startRow To lastRow
        rowType = UCase$(Trim$(CStr(ws.Cells(r, PRINT_HELPER_ROWTYPE_COL).Value)))
        If rowType = "LINE" Then
            FindFirstHelperLineAtOrBelow = r
            Exit Function
        End If
    Next r
End Function

'------------------------------------------------------------------------------
' Procedure: RebuildScannerSheetFromMain
' Scope: Private Sub
'
' What it does:
'   Recreates one operational scanner sheet from the master Delivery List
'   using the requested mode/profile.
'
' Why it exists:
'   Rebuilding from the main list is safer than letting old sheet copies drift
'   out of sync.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub RebuildScannerSheetFromMain(ByVal dataWs As Worksheet, ByVal sheetName As String, ByVal mode As String)
    Dim ws As Worksheet

    DeleteSheetIfExists ThisWorkbook, sheetName

    dataWs.Copy After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count)
    Set ws = ActiveSheet
    ws.Name = sheetName
    
    ForceRow3HeightTemplate ws
    RemovePicturesFromSheet ws
    RemoveActionButtonsFromSheet ws
    AutoFitCommentColumnsTemplate ws
    HideOtherPanelTemplate ws, mode
    ApplyGreenvilleReceiveFilterTemplate ws

    'Make sure the scanner layout and top summaries are present immediately
    ScannerValidation.EnsureScanLayout ws

    If UCase$(mode) = "RECV" Then
        ThisWorkbook.RefreshReceiveLocationSummary ws
    Else
        CreateOrUpdateTopSummaryPanels ws
    End If

    ws.Calculate

    ProtectLockColumnsAtoNTemplate ws
End Sub

'------------------------------------------------------------------------------
' Procedure: RemoveActionButtonsFromOperationalSheets
' Scope: Private Sub
'
' What it does:
'   Builds, formats, deletes, or wires workbook UI shapes/buttons/panels for
'   RemoveActionButtonsFromOperationalSheets.
'
' Why it exists:
'   Buttons and utility panels are the operator-facing control surface, so
'   they must be rebuilt consistently after imports or sheet refreshes.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub RemoveActionButtonsFromOperationalSheets()
    On Error Resume Next
    RemoveActionButtonsFromSheet ThisWorkbook.Worksheets("Delivery List")
    RemoveActionButtonsFromSheet ThisWorkbook.Worksheets("Staging - Airport Rd")
    RemoveActionButtonsFromSheet ThisWorkbook.Worksheets("Outbound - Airport Rd")

    If Not GetReceiveSheet() Is Nothing Then
        RemoveActionButtonsFromSheet GetReceiveSheet()
    End If

    RemoveActionButtonsFromSheet ThisWorkbook.Worksheets(GREENVILLE_RECV_SHEET_NAME)
    RemoveActionButtonsFromSheet ThisWorkbook.Worksheets(CPU_SHEET_NAME)
    On Error GoTo 0
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
    ws.Shapes("btnGoDeliveryListEdit").Delete
    ws.Shapes("btnApplyDestination").Delete
    ws.Shapes("btnGoReceiveSheet").Delete
    ws.Shapes("btnHomePrintDelivery").Delete
    ws.Shapes("btnHomeManualScan").Delete
    ws.Shapes("btnHomeExport").Delete

    ws.Shapes("btnHomeImport").Delete
    ws.Shapes("btnHomeUpdate").Delete
    ws.Shapes("btnHomeSave").Delete
    ws.Shapes("btnHomeSync").Delete
    ws.Shapes("btnGoDeliveryList").Delete
    ws.Shapes("btnGoAirportRd").Delete
    ws.Shapes("btnGoIndianTrail").Delete
    ws.Shapes("btnGoGreenville").Delete
    ws.Shapes("btnGoCPU").Delete
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: GoToUtilityPanel
' Scope: Public Sub
'
' What it does:
'   Builds, formats, deletes, or wires workbook UI shapes/buttons/panels for
'   GoToUtilityPanel.
'
' Why it exists:
'   Buttons and utility panels are the operator-facing control surface, so
'   they must be rebuilt consistently after imports or sheet refreshes.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub GoToUtilityPanel()
    ThisWorkbook.Worksheets("Utility Panel").Activate
End Sub

'------------------------------------------------------------------------------
' Procedure: GoToDeliveryList
' Scope: Public Sub
'
' What it does:
'   Controls the active sheet/window view, freeze panes, navigation, or
'   selected cell for GoToDeliveryList.
'
' Why it exists:
'   The workbook is used by scanners/operators, so opening the right view and
'   scan area reduces missed scans and operator confusion.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub GoToDeliveryList()
    ThisWorkbook.Worksheets("Delivery List").Activate
End Sub

'------------------------------------------------------------------------------
' Procedure: GoToAirportRd
' Scope: Public Sub
'
' What it does:
'   Controls the active sheet/window view, freeze panes, navigation, or
'   selected cell for GoToAirportRd.
'
' Why it exists:
'   The workbook is used by scanners/operators, so opening the right view and
'   scan area reduces missed scans and operator confusion.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub GoToAirportRd()
    ThisWorkbook.Worksheets("Outbound - Airport Rd").Activate
End Sub

'------------------------------------------------------------------------------
' Procedure: GoToIndianTrail
' Scope: Public Sub
'
' What it does:
'   Controls the active sheet/window view, freeze panes, navigation, or
'   selected cell for GoToIndianTrail.
'
' Why it exists:
'   The workbook is used by scanners/operators, so opening the right view and
'   scan area reduces missed scans and operator confusion.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub GoToIndianTrail()
    GoToReceiveSheet
End Sub

'------------------------------------------------------------------------------
' Procedure: GoToGreenvilleReceiveSheet
' Scope: Public Sub
'
' What it does:
'   Identifies, filters, formats, or routes Greenville-specific delivery rows
'   for GoToGreenvilleReceiveSheet.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub GoToGreenvilleReceiveSheet()
    On Error Resume Next
    ThisWorkbook.Worksheets("Inbound - Greenville").Activate
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: GoToCPUSheet
' Scope: Public Sub
'
' What it does:
'   Identifies, filters, formats, or routes Customer Pickup rows for
'   GoToCPUSheet.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub GoToCPUSheet()
    On Error Resume Next
    ThisWorkbook.Worksheets(CPU_SHEET_NAME).Activate
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: SaveCopyForSharePoint
' Scope: Public Sub
'
' What it does:
'   Saves workbook state, settings, or external output for
'   SaveCopyForSharePoint.
'
' Why it exists:
'   Persisting state lets the workbook recover correctly after refresh,
'   reopen, or sheet rebuild operations.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub SaveCopyForSharePoint()
    Dim savePath As Variant
    Dim suggestedName As String

    On Error GoTo ErrHandler

    'Bake scanner layouts/widths into the workbook before saving for SharePoint/web
    PrepareWorkbookForSharePointSave

    suggestedName = CleanFileName(BuildSuggestedSharePointFileName())

    savePath = Application.GetSaveAsFilename( _
        InitialFileName:=suggestedName & ".xlsm", _
        FileFilter:="Excel Macro-Enabled Workbook (*.xlsm), *.xlsm", _
        Title:="Save Copy for SharePoint")

    If VarType(savePath) = vbBoolean Then Exit Sub

    Application.DisplayAlerts = False
    ThisWorkbook.SaveAs Filename:=CStr(savePath), FileFormat:=xlOpenXMLWorkbookMacroEnabled
    Application.DisplayAlerts = True

    MsgBox "Saved successfully as:" & vbCrLf & CStr(savePath), vbInformation, "Saved for SharePoint"
    Exit Sub

ErrHandler:
    Application.DisplayAlerts = True
    MsgBox "SaveCopyForSharePoint error " & Err.Number & ":" & vbCrLf & Err.Description, vbCritical, "Save Error"
End Sub

'------------------------------------------------------------------------------
' Procedure: NormalizeXlsxSavePathTemplate
' Scope: Private Function
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   NormalizeXlsxSavePathTemplate.
'
' Why it exists:
'   Remakes need separate visual and print/export handling so replacement
'   glass is not confused with regular delivery-list work.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function NormalizeXlsxSavePathTemplate(ByVal rawPath As String) As String
    rawPath = Trim$(rawPath)

    If Len(rawPath) = 0 Then Exit Function
    If UCase$(rawPath) = "FALSE" Then Exit Function

    If LCase$(Right$(rawPath, 5)) <> ".xlsx" Then
        rawPath = rawPath & ".xlsx"
    End If

    NormalizeXlsxSavePathTemplate = rawPath
End Function

'------------------------------------------------------------------------------
' Procedure: PromptForXlsxSavePathTemplate
' Scope: Private Function
'
' What it does:
'   Performs the workbook-specific step named PromptForXlsxSavePathTemplate
'   inside TemplateImporter.
'
' Why it exists:
'   The master workbook uses this module to turn a raw delivery list into the
'   operational sheets used by scanning, printing, exports, and intake
'   snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function PromptForXlsxSavePathTemplate(ByVal suggestedName As String, _
                                               ByVal dialogTitle As String) As String
    Dim pickedPath As Variant

    On Error Resume Next
    Application.DisplayAlerts = True
    Application.ScreenUpdating = True
    ThisWorkbook.Activate
    AppActivate Application.Caption
    On Error GoTo 0

    DoEvents

    pickedPath = Application.GetSaveAsFilename( _
        InitialFileName:=suggestedName & ".xlsx", _
        FileFilter:="Excel Workbook (*.xlsx), *.xlsx", _
        Title:=dialogTitle)

    If VarType(pickedPath) = vbBoolean Then Exit Function

    PromptForXlsxSavePathTemplate = NormalizeXlsxSavePathTemplate(CStr(pickedPath))
End Function

'------------------------------------------------------------------------------
' Procedure: ExportListsFromUtilityPanel
' Scope: Public Sub
'
' What it does:
'   Builds, formats, deletes, or wires workbook UI shapes/buttons/panels for
'   ExportListsFromUtilityPanel.
'
' Why it exists:
'   Buttons and utility panels are the operator-facing control surface, so
'   they must be rebuilt consistently after imports or sheet refreshes.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub ExportListsFromUtilityPanel()
    Dim srcWs As Worksheet
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim firstDataRow As Long
    Dim lastRealRow As Long
    Dim orderCol As Long
    Dim itemCol As Long

    Dim exportKind As String
    Dim destinationMode As String
    Dim selectedGlassKeys As String
    Dim selectedAction As String

    On Error GoTo ErrHandler

    Set srcWs = ThisWorkbook.Worksheets("Delivery List")

    Set orderHdr = FindHeaderCellTemplate(srcWs, Array("Order Nr."))
    Set itemHdr = FindHeaderCellTemplate(srcWs, Array("Item Nr.", "Item"))

    If orderHdr Is Nothing Or itemHdr Is Nothing Then
        MsgBox "Could not find Order Nr. / Item headers for export.", vbExclamation, "Export List"
        Exit Sub
    End If

    firstDataRow = orderHdr.Row + 1
    orderCol = orderHdr.Column
    itemCol = itemHdr.Column
    lastRealRow = FindLastRealDeliveryRowTemplate(srcWs, orderCol, itemCol, firstDataRow)

    If lastRealRow < firstDataRow Then
        MsgBox "No delivery rows were found to export.", vbInformation, "Export List"
        Exit Sub
    End If

    If Not PromptForExportOptionsTemplate(srcWs, firstDataRow, lastRealRow, orderCol, itemCol, _
                                          exportKind, destinationMode, selectedGlassKeys, selectedAction) Then
        Exit Sub
    End If

    Application.ScreenUpdating = False
    Application.EnableEvents = False
    Application.DisplayAlerts = True

    Select Case UCase$(exportKind)
        Case "ORDERS", "UPDATED_ORDERS", "UPDATED_ALL", "ALL"
            ExportDeliveryListWorkbookTemplate srcWs, destinationMode, selectedGlassKeys, exportKind

        Case "REMAKES", "UPDATED_REMAKES"
            ExportRemakeListWorkbookTemplate srcWs, destinationMode, selectedGlassKeys, exportKind
    End Select

SafeExit:
    Application.DisplayAlerts = True
    Application.EnableEvents = True
    Application.ScreenUpdating = True
    Exit Sub

ErrHandler:
    Application.DisplayAlerts = True
    Application.EnableEvents = True
    Application.ScreenUpdating = True
    MsgBox "ExportListsFromUtilityPanel error " & Err.Number & ":" & vbCrLf & Err.Description, vbCritical, "Export Error"
End Sub

'------------------------------------------------------------------------------
' Procedure: PromptForExportTypeTemplate
' Scope: Private Function
'
' What it does:
'   Performs the workbook-specific step named PromptForExportTypeTemplate
'   inside TemplateImporter.
'
' Why it exists:
'   The master workbook uses this module to turn a raw delivery list into the
'   operational sheets used by scanning, printing, exports, and intake
'   snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function PromptForExportTypeTemplate() As String
    Dim choice As Variant

    choice = Application.InputBox( _
        "Select export type:" & vbCrLf & vbCrLf & _
        "1 = Delivery List (regular only)" & vbCrLf & _
        "2 = Remake List" & vbCrLf & _
        "3 = Delivery List + Remakes", _
        "Export List", Type:=1)

    If VarType(choice) = vbBoolean Then Exit Function

    Select Case CLng(Val(choice))
        Case 1
            PromptForExportTypeTemplate = "DELIVERY"
        Case 2
            PromptForExportTypeTemplate = "REMAKES"
        Case 3
            PromptForExportTypeTemplate = "DELIVERY_WITH_REMAKES"
        Case Else
            MsgBox "Please enter 1, 2, or 3.", vbExclamation, "Export List"
    End Select
End Function

'------------------------------------------------------------------------------
' Procedure: BuildSuggestedExportFileNameTemplate
' Scope: Private Function
'
' What it does:
'   Builds a derived value, key, JSON block, layout, collection, or workbook
'   object used later by the workflow (BuildSuggestedExportFileNameTemplate).
'
' Why it exists:
'   The project uses generated keys/layouts to keep repeated logic consistent
'   instead of hand-building values in multiple places.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BuildSuggestedExportFileNameTemplate(ByVal exportType As String) As String
    Dim ws As Worksheet
    Dim listDate As Date
    Dim dtText As String
    Dim baseName As String

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets("Delivery List")
    On Error GoTo 0

    Select Case UCase$(exportType)
        Case "REMAKES"
            baseName = "RemakeList"
        Case Else
            baseName = "DeliveryList"
    End Select

    If Not ws Is Nothing Then
        listDate = GetDeliveryListDateForFileName(ws)
    End If

    If listDate > 0 Then
        dtText = Format$(listDate, "m.d.yy")
    Else
        dtText = vbNullString
    End If

    BuildSuggestedExportFileNameTemplate = CleanFileName(baseName & dtText)
End Function

'------------------------------------------------------------------------------
' Procedure: SheetExistsInWorkbookTemplate
' Scope: Private Function
'
' What it does:
'   Finds, creates, deletes, rebuilds, protects, or synchronizes worksheets
'   for SheetExistsInWorkbookTemplate.
'
' Why it exists:
'   The master workbook creates multiple operational views from one delivery
'   list; worksheet helpers keep those views from drifting apart.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function SheetExistsInWorkbookTemplate(ByVal wb As Workbook, ByVal sheetName As String) As Boolean
    Dim ws As Worksheet

    On Error Resume Next
    Set ws = wb.Worksheets(sheetName)
    On Error GoTo 0

    SheetExistsInWorkbookTemplate = Not ws Is Nothing
End Function

'------------------------------------------------------------------------------
' Procedure: FractionTextToDecimalTemplate
' Scope: Private Function
'
' What it does:
'   Performs the workbook-specific step named FractionTextToDecimalTemplate
'   inside TemplateImporter.
'
' Why it exists:
'   The master workbook uses this module to turn a raw delivery list into the
'   operational sheets used by scanning, printing, exports, and intake
'   snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function FractionTextToDecimalTemplate(ByVal s As String) As String
    Dim parts() As String
    Dim n As Double
    Dim d As Double

    s = Trim$(s)
    If InStr(1, s, "/", vbTextCompare) = 0 Then
        FractionTextToDecimalTemplate = s
        Exit Function
    End If

    parts = Split(s, "/")
    If UBound(parts) <> 1 Then
        FractionTextToDecimalTemplate = s
        Exit Function
    End If

    If Not IsNumeric(parts(0)) Or Not IsNumeric(parts(1)) Then
        FractionTextToDecimalTemplate = s
        Exit Function
    End If

    n = CDbl(parts(0))
    d = CDbl(parts(1))
    If d = 0 Then
        FractionTextToDecimalTemplate = s
        Exit Function
    End If

    FractionTextToDecimalTemplate = Trim$(Format$(n / d, "0.###"))
End Function

'------------------------------------------------------------------------------
' Procedure: ConvertFractionsInExportSheetNameTemplate
' Scope: Private Function
'
' What it does:
'   Finds, creates, deletes, rebuilds, protects, or synchronizes worksheets
'   for ConvertFractionsInExportSheetNameTemplate.
'
' Why it exists:
'   The master workbook creates multiple operational views from one delivery
'   list; worksheet helpers keep those views from drifting apart.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function ConvertFractionsInExportSheetNameTemplate(ByVal rawName As String) As String
    Dim re As Object
    Dim matches As Object
    Dim m As Object
    Dim resultText As String
    Dim fractionText As String
    Dim decimalText As String

    resultText = rawName

    Set re = CreateObject("VBScript.RegExp")
    re.Global = True
    re.IgnoreCase = True
    re.Pattern = "(\d+/\d+)"

    If re.Test(resultText) Then
        Set matches = re.Execute(resultText)

        For Each m In matches
            fractionText = CStr(m.Value)
            decimalText = FractionTextToDecimalTemplate(fractionText)
            resultText = Replace$(resultText, fractionText, decimalText)
        Next m
    End If

    'Optional cleanup so tabs look cleaner
    resultText = Replace$(resultText, """", "")
    resultText = Replace$(resultText, "'", "")

    ConvertFractionsInExportSheetNameTemplate = resultText
End Function

'------------------------------------------------------------------------------
' Procedure: BuildUniqueExportSheetNameTemplate
' Scope: Private Function
'
' What it does:
'   Finds, creates, deletes, rebuilds, protects, or synchronizes worksheets
'   for BuildUniqueExportSheetNameTemplate.
'
' Why it exists:
'   The master workbook creates multiple operational views from one delivery
'   list; worksheet helpers keep those views from drifting apart.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BuildUniqueExportSheetNameTemplate(ByVal wb As Workbook, ByVal rawName As String) As String
    Dim baseName As String
    Dim tryName As String
    Dim suffix As String
    Dim i As Long

    baseName = ConvertFractionsInExportSheetNameTemplate(rawName)
    baseName = CleanSheetTabName(baseName)

    If Len(baseName) = 0 Then baseName = "Section"

    tryName = baseName
    i = 1

    Do While SheetExistsInWorkbookTemplate(wb, tryName)
        i = i + 1
        suffix = " (" & CStr(i) & ")"

        If Len(baseName) + Len(suffix) > 31 Then
            tryName = Left$(baseName, 31 - Len(suffix)) & suffix
        Else
            tryName = baseName & suffix
        End If
    Loop

    BuildUniqueExportSheetNameTemplate = tryName
End Function

'------------------------------------------------------------------------------
' Procedure: RowMatchesDeliveryExportTemplate
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   RowMatchesDeliveryExportTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function RowMatchesDeliveryExportTemplate(ByVal ws As Worksheet, _
                                                  ByVal rowNum As Long, _
                                                  ByVal destinationMode As String, _
                                                  Optional ByVal exportKind As String = "ORDERS") As Boolean
    RowMatchesDeliveryExportTemplate = DoesPrintModeMatchRowTemplate(ws, rowNum, destinationMode, exportKind)
End Function

'------------------------------------------------------------------------------
' Procedure: PrepareDeliveryExportSheetTemplate
' Scope: Private Sub
'
' What it does:
'   Finds, creates, deletes, rebuilds, protects, or synchronizes worksheets
'   for PrepareDeliveryExportSheetTemplate.
'
' Why it exists:
'   The master workbook creates multiple operational views from one delivery
'   list; worksheet helpers keep those views from drifting apart.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub PrepareDeliveryExportSheetTemplate(ByVal srcWs As Worksheet, _
                                               ByVal destWs As Worksheet, _
                                               ByVal visibleLastCol As String, _
                                               Optional ByVal destinationMode As String = "ALL")
    Dim i As Long

    srcWs.Range("A:" & visibleLastCol).Copy
    destWs.Range("A1").PasteSpecial xlPasteColumnWidths
    Application.CutCopyMode = False

    srcWs.Range("A1:" & visibleLastCol & "5").Copy
    destWs.Range("A1").PasteSpecial xlPasteAll
    Application.CutCopyMode = False

    For i = 1 To 5
        destWs.rows(i).RowHeight = srcWs.rows(i).RowHeight
    Next i

    CopyDeliveryListLogoToSheetTemplate srcWs, destWs
    ApplyDestinationAwareDeliveryTitleTemplate destWs, srcWs, destinationMode
End Sub

'------------------------------------------------------------------------------
' Procedure: DeleteDefaultFirstSheetIfNeededTemplate
' Scope: Private Sub
'
' What it does:
'   Finds, creates, deletes, rebuilds, protects, or synchronizes worksheets
'   for DeleteDefaultFirstSheetIfNeededTemplate.
'
' Why it exists:
'   The master workbook creates multiple operational views from one delivery
'   list; worksheet helpers keep those views from drifting apart.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub DeleteDefaultFirstSheetIfNeededTemplate(ByVal wb As Workbook)
    Dim ws As Worksheet

    If wb Is Nothing Then Exit Sub
    If wb.Worksheets.Count <= 1 Then Exit Sub

    Set ws = wb.Worksheets(1)

    If LCase$(Left$(ws.Name, 5)) = "sheet" Then
        Application.DisplayAlerts = False
        ws.Delete
        Application.DisplayAlerts = True
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: CreateDeliveryExportSectionSheetTemplate
' Scope: Private Function
'
' What it does:
'   Finds, creates, deletes, rebuilds, protects, or synchronizes worksheets
'   for CreateDeliveryExportSectionSheetTemplate.
'
' Why it exists:
'   The master workbook creates multiple operational views from one delivery
'   list; worksheet helpers keep those views from drifting apart.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function CreateDeliveryExportSectionSheetTemplate(ByVal srcWs As Worksheet, _
                                                          ByVal newWb As Workbook, _
                                                          ByVal sectionTitle As String, _
                                                          ByVal headerRow As Long, _
                                                          ByVal startRow As Long, _
                                                          ByVal endRow As Long, _
                                                          ByVal orderCol As Long, _
                                                          ByVal itemCol As Long, _
                                                          ByVal destinationMode As String, _
                                                          ByVal selectedGlassKeys As String, _
                                                          ByVal visibleLastCol As String, _
                                                          Optional ByVal exportKind As String = "ORDERS") As Boolean
    Dim destWs As Worksheet
    Dim destRow As Long
    Dim r As Long
    Dim hasAny As Boolean

    If headerRow <= 0 Then Exit Function
    If startRow > endRow Then Exit Function
    If Not IsGlassSectionSelectedTemplate(sectionTitle, selectedGlassKeys) Then Exit Function

    For r = startRow To endRow
        If IsRealDeliveryLineTemplate(srcWs, r, orderCol, itemCol) Then
            If RowMatchesDeliveryExportTemplate(srcWs, r, destinationMode, exportKind) Then
                hasAny = True
                Exit For
            End If
        End If
    Next r

    If Not hasAny Then Exit Function

    Set destWs = newWb.Worksheets.Add(After:=newWb.Worksheets(newWb.Worksheets.Count))
    destWs.Name = BuildUniqueExportSheetNameTemplate(newWb, sectionTitle)

    PrepareDeliveryExportSheetTemplate srcWs, destWs, visibleLastCol, destinationMode

    destRow = 6
    CopyPrintableRowForPrint srcWs, headerRow, destWs, destRow, sectionTitle, "HEADER", visibleLastCol, destinationMode
    destRow = destRow + 1

    For r = startRow To endRow
        If IsRealDeliveryLineTemplate(srcWs, r, orderCol, itemCol) Then
            If RowMatchesDeliveryExportTemplate(srcWs, r, destinationMode, exportKind) Then
                CopyPrintableRowForPrint srcWs, r, destWs, destRow, sectionTitle, "LINE", visibleLastCol, destinationMode
                destRow = destRow + 1
            End If
        End If
    Next r

    CreateDeliveryExportSectionSheetTemplate = True
End Function

'------------------------------------------------------------------------------
' Procedure: CreateRemakeExportSectionSheetTemplate
' Scope: Private Function
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   CreateRemakeExportSectionSheetTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function CreateRemakeExportSectionSheetTemplate(ByVal srcWs As Worksheet, _
                                                        ByVal newWb As Workbook, _
                                                        ByVal templateWs As Worksheet, _
                                                        ByVal sectionTitle As String, _
                                                        ByVal startRow As Long, _
                                                        ByVal endRow As Long, _
                                                        ByVal orderCol As Long, _
                                                        ByVal itemCol As Long, _
                                                        ByVal qtyCol As Long, _
                                                        ByVal dimCol As Long, _
                                                        ByVal destinationMode As String, _
                                                        ByVal selectedGlassKeys As String, _
                                                        ByVal listDate As Date, _
                                                        Optional ByVal exportKind As String = "REMAKES") As Boolean
    Dim destWs As Worksheet
    Dim bodyLastRow As Long
    Dim bodyStartRow As Long
    Dim destRow As Long
    Dim r As Long
    Dim hasAny As Boolean

    If startRow > endRow Then Exit Function
    If Not IsGlassSectionSelectedTemplate(sectionTitle, selectedGlassKeys) Then Exit Function

    For r = startRow To endRow
        If IsRealDeliveryLineTemplate(srcWs, r, orderCol, itemCol) Then
            If DoesPrintModeMatchRowTemplate(srcWs, r, destinationMode, exportKind) Then
                hasAny = True
                Exit For
            End If
        End If
    Next r

    If Not hasAny Then Exit Function

    templateWs.Visible = xlSheetVisible
    templateWs.Copy After:=newWb.Worksheets(newWb.Worksheets.Count)
    Set destWs = newWb.Worksheets(newWb.Worksheets.Count)
    templateWs.Visible = xlSheetVeryHidden

    destWs.Name = BuildUniqueExportSheetNameTemplate(newWb, sectionTitle)

    On Error Resume Next
    destWs.Unprotect Password:=""
    On Error GoTo 0

    If listDate > 0 Then
        destWs.Range("A2").Value = REMAKE_TITLE_PREFIX & Format$(listDate, "m/d/yyyy")
    End If

    ApplyRemakePrintColumnHeadersTemplate destWs

    bodyLastRow = GetLastUsedRowTemplate(destWs)
    bodyStartRow = GetRemakePrintBodyStartRowTemplate(destWs)

    If bodyLastRow < bodyStartRow Then bodyLastRow = bodyStartRow
    destWs.Range("A" & bodyStartRow & ":M" & bodyLastRow).ClearContents

    destRow = bodyStartRow
    WriteRemakeSectionHeaderTemplate destWs, destRow, sectionTitle
    WriteRemakeBlankSpacerTemplate destWs, destRow + 1
    destRow = destRow + 2

    For r = startRow To endRow
        If IsRealDeliveryLineTemplate(srcWs, r, orderCol, itemCol) Then
            If DoesPrintModeMatchRowTemplate(srcWs, r, destinationMode, exportKind) Then
                WriteRemakeLineTemplate srcWs, r, destWs, destRow, orderCol, itemCol, qtyCol, dimCol
                destRow = destRow + 1
            End If
        End If
    Next r

    ConfigureRemakePrintPageTemplate destWs, destRow - 1
    CreateRemakeExportSectionSheetTemplate = True
End Function

'------------------------------------------------------------------------------
' Procedure: ExportDeliveryListWorkbookTemplate
' Scope: Private Sub
'
' What it does:
'   Exports a delivery/remake list or workbook copy for downstream use
'   (ExportDeliveryListWorkbookTemplate).
'
' Why it exists:
'   Export routines produce controlled output instead of requiring users to
'   manually copy filtered workbook data.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ExportDeliveryListWorkbookTemplate(ByVal srcWs As Worksheet, _
                                               ByVal destinationMode As String, _
                                               ByVal selectedGlassKeys As String, _
                                               Optional ByVal exportKind As String = "ORDERS")
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim firstDataRow As Long
    Dim lastRealRow As Long
    Dim orderCol As Long
    Dim itemCol As Long

    On Error GoTo ErrHandler

    Set orderHdr = FindHeaderCellTemplate(srcWs, Array("Order Nr."))
    Set itemHdr = FindHeaderCellTemplate(srcWs, Array("Item Nr.", "Item"))

    If orderHdr Is Nothing Or itemHdr Is Nothing Then
        MsgBox "Could not find Order Nr. / Item headers for delivery export.", vbExclamation, "Export Delivery List"
        Exit Sub
    End If

    firstDataRow = orderHdr.Row + 1
    orderCol = orderHdr.Column
    itemCol = itemHdr.Column
    lastRealRow = FindLastRealDeliveryRowTemplate(srcWs, orderCol, itemCol, firstDataRow)

    If lastRealRow < firstDataRow Then
        MsgBox "No delivery rows were found to export.", vbInformation, "Export Delivery List"
        Exit Sub
    End If

    ExportDeliveryListWorkbookFromPrintTemplate srcWs, 0, 0, firstDataRow, lastRealRow, _
                                                orderCol, itemCol, destinationMode, selectedGlassKeys, exportKind
    Exit Sub

ErrHandler:
    MsgBox "ExportDeliveryListWorkbookTemplate error " & Err.Number & ":" & vbCrLf & Err.Description, vbCritical, "Export Error"
End Sub

'------------------------------------------------------------------------------
' Procedure: ExportDeliveryListWorkbookFromPrintTemplate
' Scope: Private Sub
'
' What it does:
'   Exports a delivery/remake list or workbook copy for downstream use
'   (ExportDeliveryListWorkbookFromPrintTemplate).
'
' Why it exists:
'   Export routines produce controlled output instead of requiring users to
'   manually copy filtered workbook data.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ExportDeliveryListWorkbookFromPrintTemplate(ByVal srcWs As Worksheet, _
                                                        ByVal sectionStartRow As Long, ByVal sectionEndRow As Long, _
                                                        ByVal firstDataRow As Long, ByVal lastRealRow As Long, _
                                                        ByVal orderCol As Long, ByVal itemCol As Long, _
                                                        ByVal destinationMode As String, _
                                                        ByVal selectedGlassKeys As String, _
                                                        Optional ByVal exportKind As String = "ORDERS")
    Dim newWb As Workbook
    Dim visibleLastCol As String
    Dim scanStart As Long
    Dim scanEnd As Long
    Dim r As Long
    Dim currentSectionTitle As String
    Dim currentHeaderRow As Long
    Dim currentSectionStart As Long
    Dim madeAnySheets As Boolean
    Dim savePath As Variant
    Dim suggestedName As String
    Dim oldDisplayAlerts As Boolean
    Dim oldScreenUpdating As Boolean

    On Error GoTo ErrHandler

    oldDisplayAlerts = Application.DisplayAlerts
    oldScreenUpdating = Application.ScreenUpdating
    Application.DisplayAlerts = False
    Application.ScreenUpdating = False

    visibleLastCol = GetPrintLastColForDestination(destinationMode)

    If sectionStartRow > 0 And sectionEndRow > 0 Then
        scanStart = sectionStartRow
        scanEnd = sectionEndRow
    Else
        scanStart = firstDataRow
        scanEnd = lastRealRow
    End If

    Set newWb = Workbooks.Add(xlWBATWorksheet)

    currentSectionTitle = vbNullString
    currentHeaderRow = 0
    currentSectionStart = 0
    madeAnySheets = False

    For r = scanStart To scanEnd
        If IsSectionHeaderRowTemplate(srcWs, r, orderCol, itemCol) Then
            If currentHeaderRow > 0 Then
                If CreateDeliveryExportSectionSheetTemplate(srcWs, newWb, currentSectionTitle, currentHeaderRow, _
                                                            currentSectionStart, r - 1, orderCol, itemCol, _
                                                            destinationMode, selectedGlassKeys, visibleLastCol, exportKind) Then
                    madeAnySheets = True
                End If
            End If

            currentSectionTitle = Trim$(CStr(srcWs.Cells(r, 1).Value))
            currentHeaderRow = r
            currentSectionStart = r + 1
        End If
    Next r

    If currentHeaderRow > 0 Then
        If CreateDeliveryExportSectionSheetTemplate(srcWs, newWb, currentSectionTitle, currentHeaderRow, _
                                                    currentSectionStart, scanEnd, orderCol, itemCol, _
                                                    destinationMode, selectedGlassKeys, visibleLastCol, exportKind) Then
            madeAnySheets = True
        End If
    End If

    If Not madeAnySheets Then
        MsgBox "There were no delivery rows to export for the selected glass section(s).", _
               vbInformation, "Export Delivery List"
        GoTo SafeExit
    End If

    DeleteDefaultFirstSheetIfNeededTemplate newWb

    Select Case UCase$(exportKind)
        Case "UPDATED_ORDERS"
            suggestedName = BuildSuggestedExportFileNameTemplate("DELIVERY") & "_Updated"
        Case "UPDATED_ALL"
            suggestedName = BuildSuggestedExportFileNameTemplate("DELIVERY") & "_Updated"
        Case "ALL"
            suggestedName = BuildSuggestedExportFileNameTemplate("DELIVERY") & ""
        Case Else
            suggestedName = BuildSuggestedExportFileNameTemplate("DELIVERY")
    End Select

    newWb.Activate
    DoEvents

    savePath = PromptForXlsxSavePathTemplate(suggestedName, "Export Delivery List")
    If Len(CStr(savePath)) = 0 Then GoTo SafeExit

    newWb.SaveAs Filename:=CStr(savePath), FileFormat:=xlOpenXMLWorkbook
    MsgBox "Delivery export created successfully.", vbInformation, "Export Delivery List"

SafeExit:
    On Error Resume Next
    Application.DisplayAlerts = False
    If Not newWb Is Nothing Then newWb.Close SaveChanges:=False
    Application.DisplayAlerts = oldDisplayAlerts
    Application.ScreenUpdating = oldScreenUpdating
    On Error GoTo 0
    Exit Sub

ErrHandler:
    Application.DisplayAlerts = False
    On Error Resume Next
    If Not newWb Is Nothing Then newWb.Close SaveChanges:=False
    Application.DisplayAlerts = oldDisplayAlerts
    Application.ScreenUpdating = oldScreenUpdating
    MsgBox "ExportDeliveryListWorkbookFromPrintTemplate error " & Err.Number & ":" & vbCrLf & Err.Description, _
           vbCritical, "Export Error"
End Sub

'------------------------------------------------------------------------------
' Procedure: ExportRemakeListWorkbookTemplate
' Scope: Private Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   ExportRemakeListWorkbookTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ExportRemakeListWorkbookTemplate(ByVal srcWs As Worksheet, _
                                             ByVal destinationMode As String, _
                                             ByVal selectedGlassKeys As String, _
                                             Optional ByVal exportKind As String = "REMAKES")
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim orderCol As Long
    Dim itemCol As Long
    Dim firstDataRow As Long
    Dim lastRealRow As Long

    On Error GoTo ErrHandler

    Set orderHdr = FindHeaderCellTemplateInCols(srcWs, Array("Order Nr."), "A:N", 250)
    Set itemHdr = FindHeaderCellTemplateInCols(srcWs, Array("Item Nr.", "Item"), "A:N", 250)

    If orderHdr Is Nothing Or itemHdr Is Nothing Then
        MsgBox "Could not find the Delivery List headers needed for remake export.", vbExclamation, "Export Remake List"
        Exit Sub
    End If

    orderCol = orderHdr.Column
    itemCol = itemHdr.Column
    firstDataRow = orderHdr.Row + 1
    lastRealRow = FindLastRealDeliveryRowTemplate(srcWs, orderCol, itemCol, firstDataRow)

    If lastRealRow < firstDataRow Then
        MsgBox "There are no remake rows to export.", vbInformation, "Export Remake List"
        Exit Sub
    End If

    ExportRemakeListWorkbookFromTemplate srcWs, 0, 0, firstDataRow, lastRealRow, _
                                         orderCol, itemCol, destinationMode, selectedGlassKeys, exportKind
    Exit Sub

ErrHandler:
    MsgBox "ExportRemakeListWorkbookTemplate error " & Err.Number & ":" & vbCrLf & Err.Description, vbCritical, "Export Error"
End Sub

'------------------------------------------------------------------------------
' Procedure: ExportRemakeListWorkbookFromTemplate
' Scope: Private Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   ExportRemakeListWorkbookFromTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ExportRemakeListWorkbookFromTemplate(ByVal srcWs As Worksheet, _
                                                 ByVal sectionStartRow As Long, ByVal sectionEndRow As Long, _
                                                 ByVal firstDataRow As Long, ByVal lastRealRow As Long, _
                                                 ByVal orderCol As Long, ByVal itemCol As Long, _
                                                 ByVal destinationMode As String, _
                                                 ByVal selectedGlassKeys As String, _
                                                 Optional ByVal exportKind As String = "REMAKES")
    Dim newWb As Workbook
    Dim templateWs As Worksheet
    Dim qtyHdr As Range
    Dim dimHdr As Range
    Dim qtyCol As Long
    Dim dimCol As Long
    Dim listDate As Date
    Dim savePath As Variant
    Dim suggestedName As String
    Dim oldDisplayAlerts As Boolean
    Dim oldScreenUpdating As Boolean
    Dim scanStart As Long
    Dim scanEnd As Long
    Dim r As Long
    Dim currentSectionTitle As String
    Dim currentSectionStart As Long
    Dim madeAnySheets As Boolean

    On Error GoTo ErrHandler

    Set qtyHdr = FindHeaderCellTemplate(srcWs, Array("Qty.", "Qty"))
    Set dimHdr = FindHeaderCellTemplate(srcWs, Array("Dimensions"))

    If qtyHdr Is Nothing Or dimHdr Is Nothing Then
        MsgBox "Could not find Qty. / Dimensions headers needed for remake export.", _
               vbExclamation, "Export Remake List"
        Exit Sub
    End If

    qtyCol = qtyHdr.Column
    dimCol = dimHdr.Column
    listDate = GetDeliveryListDateForFileName(srcWs)

    oldDisplayAlerts = Application.DisplayAlerts
    oldScreenUpdating = Application.ScreenUpdating
    Application.DisplayAlerts = False
    Application.ScreenUpdating = False

    Set templateWs = ThisWorkbook.Worksheets(REMAKE_PRINT_TEMPLATE_SHEET)
    Set newWb = Workbooks.Add(xlWBATWorksheet)

    If sectionStartRow > 0 And sectionEndRow > 0 Then
        scanStart = sectionStartRow
        scanEnd = sectionEndRow
    Else
        scanStart = firstDataRow
        scanEnd = lastRealRow
    End If

    currentSectionTitle = vbNullString
    currentSectionStart = 0
    madeAnySheets = False

    For r = scanStart To scanEnd
        If IsSectionHeaderRowTemplate(srcWs, r, orderCol, itemCol) Then
            If currentSectionStart > 0 Then
                If CreateRemakeExportSectionSheetTemplate(srcWs, newWb, templateWs, currentSectionTitle, _
                                                          currentSectionStart, r - 1, orderCol, itemCol, _
                                                          qtyCol, dimCol, destinationMode, selectedGlassKeys, _
                                                          listDate, exportKind) Then
                    madeAnySheets = True
                End If
            End If

            currentSectionTitle = Trim$(CStr(srcWs.Cells(r, 1).Value))
            currentSectionStart = r + 1
        End If
    Next r

    If currentSectionStart > 0 Then
        If CreateRemakeExportSectionSheetTemplate(srcWs, newWb, templateWs, currentSectionTitle, _
                                                  currentSectionStart, scanEnd, orderCol, itemCol, _
                                                  qtyCol, dimCol, destinationMode, selectedGlassKeys, _
                                                  listDate, exportKind) Then
            madeAnySheets = True
        End If
    End If

    If Not madeAnySheets Then
        MsgBox "There were no remake rows to export for the selected glass section(s).", _
               vbInformation, "Export Remake List"
        GoTo SafeExit
    End If

    DeleteDefaultFirstSheetIfNeededTemplate newWb

    If UCase$(exportKind) = "UPDATED_REMAKES" Then
        suggestedName = BuildSuggestedExportFileNameTemplate("REMAKES") & "_Updated"
    Else
        suggestedName = BuildSuggestedExportFileNameTemplate("REMAKES")
    End If

    newWb.Activate
    DoEvents

    savePath = PromptForXlsxSavePathTemplate(suggestedName, "Export Remake List")
    If Len(CStr(savePath)) = 0 Then GoTo SafeExit

    newWb.SaveAs Filename:=CStr(savePath), FileFormat:=xlOpenXMLWorkbook
    MsgBox "Remake export created successfully.", vbInformation, "Export Remake List"

SafeExit:
    On Error Resume Next
    Application.DisplayAlerts = False
    If Not newWb Is Nothing Then newWb.Close SaveChanges:=False
    If Not templateWs Is Nothing Then templateWs.Visible = xlSheetVeryHidden
    Application.DisplayAlerts = oldDisplayAlerts
    Application.ScreenUpdating = oldScreenUpdating
    On Error GoTo 0
    Exit Sub

ErrHandler:
    Application.DisplayAlerts = False
    On Error Resume Next
    If Not newWb Is Nothing Then newWb.Close SaveChanges:=False
    If Not templateWs Is Nothing Then templateWs.Visible = xlSheetVeryHidden
    Application.DisplayAlerts = oldDisplayAlerts
    Application.ScreenUpdating = oldScreenUpdating
    MsgBox "ExportRemakeListWorkbookFromTemplate error " & Err.Number & ":" & vbCrLf & Err.Description, _
           vbCritical, "Export Error"
End Sub

'------------------------------------------------------------------------------
' Procedure: BuildSuggestedSharePointFileName
' Scope: Private Function
'
' What it does:
'   Builds a derived value, key, JSON block, layout, collection, or workbook
'   object used later by the workflow (BuildSuggestedSharePointFileName).
'
' Why it exists:
'   The project uses generated keys/layouts to keep repeated logic consistent
'   instead of hand-building values in multiple places.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BuildSuggestedSharePointFileName() As String
    Dim ws As Worksheet
    Dim listDate As Date
    Dim dtText As String

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets("Delivery List")
    On Error GoTo 0

    If ws Is Nothing Then
        BuildSuggestedSharePointFileName = "DeliveryList"
        Exit Function
    End If

    listDate = GetDeliveryListDateForFileName(ws)

    If listDate > 0 Then
        dtText = Format$(listDate, "m.d.yy")
        BuildSuggestedSharePointFileName = "DeliveryList" & dtText
    Else
        BuildSuggestedSharePointFileName = "DeliveryList"
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: TryParseDateFromTitleTextTemplate
' Scope: Private Function
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   TryParseDateFromTitleTextTemplate.
'
' Why it exists:
'   Delivery timing, queue timestamps, and scan timestamps drive status
'   messages such as Early, On-Time, Late, Processing, and Done.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function TryParseDateFromTitleTextTemplate(ByVal s As String) As Date
    Dim p As Long
    Dim candidate As String

    s = Trim$(CStr(s))
    p = InStr(1, UCase$(s), "DELIVERY LIST FOR", vbTextCompare)

    If p > 0 Then
        candidate = Trim$(Mid$(s, p + Len("DELIVERY LIST FOR")))
        On Error Resume Next
        TryParseDateFromTitleTextTemplate = DateValue(candidate)
        On Error GoTo 0
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: GetDeliveryListDateForFileName
' Scope: Public Function
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   GetDeliveryListDateForFileName.
'
' Why it exists:
'   Delivery timing, queue timestamps, and scan timestamps drive status
'   messages such as Early, On-Time, Late, Processing, and Done.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function GetDeliveryListDateForFileName(ByVal ws As Worksheet) As Date
    Dim hdr As Range
    Dim r As Range
    Dim c As Range
    Dim dt As Date

    Set r = ws.Range("A1:AG5")
    Set hdr = r.Find(What:="DELIVERY LIST FOR", LookIn:=xlValues, LookAt:=xlPart)

    If Not hdr Is Nothing Then
        'First: old behavior - look for a standalone date cell on the same row
        For Each c In ws.Range(ws.Cells(hdr.Row, hdr.Column), ws.Cells(hdr.Row, ws.Columns.Count)).Cells
            If IsDate(c.Value) Then
                GetDeliveryListDateForFileName = DateValue(c.Value)
                Exit Function
            End If
        Next c

        'Second: new behavior - parse the date from the title text itself
        dt = TryParseDateFromTitleTextTemplate(CStr(hdr.Value))
        If dt > 0 Then
            GetDeliveryListDateForFileName = dt
            Exit Function
        End If
    End If

    'Fallback: any standalone date in the top area
    For Each c In ws.Range("A1:AG3").Cells
        If IsDate(c.Value) Then
            GetDeliveryListDateForFileName = DateValue(c.Value)
            Exit Function
        End If
    Next c

    GetDeliveryListDateForFileName = 0
End Function

'------------------------------------------------------------------------------
' Procedure: NormalizeDeliveryListTitleKeyTemplate
' Scope: Private Function
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   NormalizeDeliveryListTitleKeyTemplate.
'
' Why it exists:
'   Remakes need separate visual and print/export handling so replacement
'   glass is not confused with regular delivery-list work.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function NormalizeDeliveryListTitleKeyTemplate(ByVal s As String) As String
    s = UCase$(Trim$(s))
    s = Replace$(s, vbCr, " ")
    s = Replace$(s, vbLf, " ")
    s = Replace$(s, Chr$(160), " ")

    Do While InStr(s, "  ") > 0
        s = Replace$(s, "  ", " ")
    Loop

    NormalizeDeliveryListTitleKeyTemplate = s
End Function

'------------------------------------------------------------------------------
' Procedure: GetDeliveryListTitleKeyTemplate
' Scope: Private Function
'
' What it does:
'   Returns a workbook object, setting, status value, parsed value, or
'   calculated result used by other procedures
'   (GetDeliveryListTitleKeyTemplate).
'
' Why it exists:
'   Using one getter keeps callers from duplicating lookup logic and protects
'   them from missing sheets, missing names, or blank values.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetDeliveryListTitleKeyTemplate(ByVal ws As Worksheet) As String
    Dim topRange As Range
    Dim hdr As Range
    Dim c As Range
    Dim rawTitle As String
    Dim dt As Date

    On Error Resume Next
    Set topRange = ws.Range("A1:AG5")
    On Error GoTo 0
    If topRange Is Nothing Then Exit Function

    Set hdr = topRange.Find(What:="DELIVERY LIST FOR", LookIn:=xlValues, LookAt:=xlPart)

    If Not hdr Is Nothing Then
        rawTitle = Trim$(CStr(hdr.Value))

        'Old style: separate date somewhere on the same row
        For Each c In ws.Range(ws.Cells(hdr.Row, 1), ws.Cells(hdr.Row, ws.Columns.Count)).Cells
            If IsDate(c.Value) Then
                dt = DateValue(c.Value)
                GetDeliveryListTitleKeyTemplate = NormalizeDeliveryListTitleKeyTemplate(rawTitle & "|" & Format$(dt, "yyyymmdd"))
                Exit Function
            End If
        Next c

        'New style: date embedded in the title text itself
        dt = TryParseDateFromTitleTextTemplate(rawTitle)
        If dt > 0 Then
            GetDeliveryListTitleKeyTemplate = NormalizeDeliveryListTitleKeyTemplate("DELIVERY LIST FOR|" & Format$(dt, "yyyymmdd"))
            Exit Function
        End If

        GetDeliveryListTitleKeyTemplate = NormalizeDeliveryListTitleKeyTemplate(rawTitle)
        Exit Function
    End If

    dt = GetDeliveryListDateForFileName(ws)
    If dt > 0 Then
        GetDeliveryListTitleKeyTemplate = "DELIVERY LIST FOR|" & Format$(dt, "yyyymmdd")
    Else
        GetDeliveryListTitleKeyTemplate = vbNullString
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: ValidateMatchingDeliveryListsTemplate
' Scope: Private Function
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   ValidateMatchingDeliveryListsTemplate.
'
' Why it exists:
'   Delivery timing, queue timestamps, and scan timestamps drive status
'   messages such as Early, On-Time, Late, Processing, and Done.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function ValidateMatchingDeliveryListsTemplate(ByVal currentWs As Worksheet, ByVal importWs As Worksheet) As Boolean
    Dim currentKey As String
    Dim importKey As String
    Dim currentDt As Date
    Dim importDt As Date
    Dim currentTitle As String
    Dim importTitle As String

    currentKey = GetDeliveryListTitleKeyTemplate(currentWs)
    importKey = GetDeliveryListTitleKeyTemplate(importWs)

    currentDt = GetDeliveryListDateForFileName(currentWs)
    importDt = GetDeliveryListDateForFileName(importWs)

    currentTitle = IIf(currentDt > 0, "Delivery List For " & Format$(currentDt, "m/d/yyyy"), "Not Found")
    importTitle = IIf(importDt > 0, "Delivery List For " & Format$(importDt, "m/d/yyyy"), "Not Found")

    If currentDt = 0 Or importDt = 0 Then
        MsgBox "The delivery list dates could not be verified." & vbCrLf & vbCrLf & _
               "Current Delivery List title: " & currentTitle & vbCrLf & _
               "Selected update file title: " & importTitle & vbCrLf & vbCrLf & _
               "Update canceled.", _
               vbCritical, "Delivery List Verification Failed"
        Exit Function
    End If

    If currentDt <> importDt Then
        MsgBox "The selected update file is for a different delivery date." & vbCrLf & vbCrLf & _
               "Current Delivery List: " & currentTitle & vbCrLf & _
               "Selected update file: " & importTitle & vbCrLf & vbCrLf & _
               "Please choose the matching delivery list file.", _
               vbCritical, "Delivery List Date Mismatch"
        Exit Function
    End If

    If Len(currentKey) > 0 And Len(importKey) > 0 Then
        If StrComp(currentKey, importKey, vbTextCompare) <> 0 Then
            MsgBox "The selected update file title does not match the current Delivery List." & vbCrLf & vbCrLf & _
                   "Current Delivery List: " & currentTitle & vbCrLf & _
                   "Selected update file: " & importTitle & vbCrLf & vbCrLf & _
                   "Please choose the correct delivery list update file.", _
                   vbCritical, "Delivery List Mismatch"
            Exit Function
        End If
    End If

    ValidateMatchingDeliveryListsTemplate = True
End Function

'------------------------------------------------------------------------------
' Procedure: PrepareWorkbookForSharePointSave
' Scope: Private Sub
'
' What it does:
'   Performs the workbook-specific step named PrepareWorkbookForSharePointSave
'   inside TemplateImporter.
'
' Why it exists:
'   The master workbook uses this module to turn a raw delivery list into the
'   operational sheets used by scanning, printing, exports, and intake
'   snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub PrepareWorkbookForSharePointSave()
    Dim dataWs As Worksheet

    On Error Resume Next
    Set dataWs = ThisWorkbook.Worksheets("Delivery List")
    If dataWs Is Nothing Then Exit Sub

    dataWs.Unprotect Password:=""
    On Error GoTo 0

    EnsureDeliveryListColumnLayoutTemplate dataWs
    EnsureImportedDeliveryListTitleTemplate dataWs
    NormalizeDeliveryListTitleTemplate dataWs

    'IMPORTANT:
    'Clean delivery-list-side junk BEFORE scan layout exists
    NormalizeImportedRowHeights dataWs
    RemoveImportedFooterNotesForSharePointSafe dataWs

    ThisWorkbook.RefreshAllDeliveryListProcessStates dataWs
    ScannerValidation.EnsureScanLayout dataWs

    HighlightGreenvilleRowsTemplate dataWs
    AutoFitCommentColumnsTemplate dataWs

    RebuildAllScannerSheetsFromMain dataWs

    ProtectViewOnlyTemplate dataWs
End Sub

'------------------------------------------------------------------------------
' Procedure: CleanFileName
' Scope: Private Function
'
' What it does:
'   Cleans or normalizes text so comparisons, keys, and operator messages are
'   stable (CleanFileName).
'
' Why it exists:
'   The workbook compares text from Excel, barcodes, SharePoint, and Power
'   Automate; normalization prevents small formatting differences from
'   breaking logic.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function CleanFileName(ByVal s As String) As String
    Dim badChars As Variant
    Dim i As Long

    badChars = Array("\", "/", ":", "*", "?", """", "<", ">", "|")

    For i = LBound(badChars) To UBound(badChars)
        s = Replace(s, CStr(badChars(i)), "-")
    Next i

    CleanFileName = Trim$(s)
End Function

'------------------------------------------------------------------------------
' Procedure: GetTemplateNoticeAuditSheet
' Scope: Private Function
'
' What it does:
'   Builds or displays the operator-facing notice/message used by
'   GetTemplateNoticeAuditSheet.
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
Private Function GetTemplateNoticeAuditSheet() As Worksheet
    Dim ws As Worksheet

    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets("__ChangeAudit")
    On Error GoTo 0

    If ws Is Nothing Then
        Set ws = ThisWorkbook.Worksheets.Add(After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
        ws.Name = "__ChangeAudit"
        ws.Visible = xlSheetVeryHidden
    End If

    If Len(Trim$(CStr(ws.Range("D5").Value))) = 0 Then
        ws.Range("D5").Value = "PopupUser"
        ws.Range("E5").Value = "PopupNoticeKey"
        ws.Range("F5").Value = "SeenAt"
    End If

    Set GetTemplateNoticeAuditSheet = ws
End Function

'------------------------------------------------------------------------------
' Procedure: GetTemplateNoticeUserName
' Scope: Private Function
'
' What it does:
'   Builds or displays the operator-facing notice/message used by
'   GetTemplateNoticeUserName.
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
Private Function GetTemplateNoticeUserName() As String
    GetTemplateNoticeUserName = Trim$(Environ$("Username"))
    If Len(GetTemplateNoticeUserName) = 0 Then
        GetTemplateNoticeUserName = Trim$(Application.userName)
    End If
    If Len(GetTemplateNoticeUserName) = 0 Then
        GetTemplateNoticeUserName = "Unknown User"
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: HasUserSeenTemplateNotice
' Scope: Private Function
'
' What it does:
'   Builds or displays the operator-facing notice/message used by
'   HasUserSeenTemplateNotice.
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
Private Function HasUserSeenTemplateNotice(ByVal noticeKey As String) As Boolean
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim r As Long
    Dim userName As String

    Set ws = GetTemplateNoticeAuditSheet()
    userName = GetTemplateNoticeUserName()

    lastRow = ws.Cells(ws.rows.Count, 4).End(xlUp).Row
    If lastRow < 6 Then Exit Function

    For r = 6 To lastRow
        If StrComp(CStr(ws.Cells(r, 4).Value), userName, vbTextCompare) = 0 _
           And StrComp(CStr(ws.Cells(r, 5).Value), noticeKey, vbTextCompare) = 0 Then
            HasUserSeenTemplateNotice = True
            Exit Function
        End If
    Next r
End Function

'------------------------------------------------------------------------------
' Procedure: MarkUserSeenTemplateNotice
' Scope: Private Sub
'
' What it does:
'   Builds or displays the operator-facing notice/message used by
'   MarkUserSeenTemplateNotice.
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
Private Sub MarkUserSeenTemplateNotice(ByVal noticeKey As String)
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim r As Long
    Dim userName As String

    Set ws = GetTemplateNoticeAuditSheet()
    userName = GetTemplateNoticeUserName()

    lastRow = ws.Cells(ws.rows.Count, 4).End(xlUp).Row
    If lastRow < 6 Then lastRow = 5

    For r = 6 To lastRow
        If StrComp(CStr(ws.Cells(r, 4).Value), userName, vbTextCompare) = 0 _
           And StrComp(CStr(ws.Cells(r, 5).Value), noticeKey, vbTextCompare) = 0 Then
            ws.Cells(r, 6).Value = Format$(Now, "m/d/yyyy h:mm AM/PM")
            Exit Sub
        End If
    Next r

    ws.Cells(lastRow + 1, 4).Value = userName
    ws.Cells(lastRow + 1, 5).Value = noticeKey
    ws.Cells(lastRow + 1, 6).Value = Format$(Now, "m/d/yyyy h:mm AM/PM")
End Sub

'------------------------------------------------------------------------------
' Procedure: ShowUpdateNoticeOnce
' Scope: Private Sub
'
' What it does:
'   Builds or displays the operator-facing notice/message used by
'   ShowUpdateNoticeOnce.
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
Private Sub ShowUpdateNoticeOnce(ByVal addedCount As Long)
    If HasUserSeenTemplateNotice(UPDATE_COMPLETE_NOTICE_KEY) Then Exit Sub

    MarkUserSeenTemplateNotice UPDATE_COMPLETE_NOTICE_KEY

    MsgBox "Delivery List was updated." & vbCrLf & vbCrLf & _
           CStr(addedCount) & " new line(s) were appended." & vbCrLf & _
           "Newest additions are highlighted in purple." & vbCrLf & _
           "See the Delivery List sheet.", _
           vbInformation, "Delivery List Updated"
End Sub

'------------------------------------------------------------------------------
' Procedure: OpenDeliveryListForEditing
' Scope: Public Sub
'
' What it does:
'   Tracks, applies, clears, or persists manual-edit state for
'   OpenDeliveryListForEditing.
'
' Why it exists:
'   Manual edits need visible/persistent marking so later imports, scanner-
'   sheet rebuilds, and updates do not silently hide operator changes.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub OpenDeliveryListForEditing()
    Dim ws As Worksheet
    Dim resp As VbMsgBoxResult

    resp = MsgBox( _
        "You are about to edit the Delivery List directly." & vbCrLf & vbCrLf & _
        "Changes made here may affect the Staging, Outbound, and Inbound sheets after syncing." & vbCrLf & vbCrLf & _
        "Are you sure you would like to continue?", _
        vbYesNo + vbExclamation + vbDefaultButton2, _
        "Confirm Delivery List Edit")

    If resp <> vbYes Then Exit Sub

    Set ws = ThisWorkbook.Worksheets("Delivery List")

    On Error Resume Next
    ws.Unprotect Password:=""
    ThisWorkbook.names("_DeliveryEditMode").Delete
    On Error GoTo 0

    ThisWorkbook.names.Add Name:="_DeliveryEditMode", RefersTo:="=TRUE"
    ThisWorkbook.BeginDeliveryListEditSession
    ws.Tab.Color = RGB(255, 192, 0)

    ws.Activate
End Sub

'------------------------------------------------------------------------------
' Procedure: AutoFitImportedDeliveryListColumns
' Scope: Private Sub
'
' What it does:
'   Finds, sizes, hides, formats, or uses worksheet columns for
'   AutoFitImportedDeliveryListColumns.
'
' Why it exists:
'   The system depends on fixed scan blocks and discovered delivery-list
'   columns, so column handling must be centralized and predictable.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub AutoFitImportedDeliveryListColumns(ByVal ws As Worksheet)
    On Error Resume Next
    ws.Unprotect Password:=""
    On Error GoTo 0

    'Auto-fit only the imported business columns
    ws.Columns("E:M").EntireColumn.AutoFit
    ws.Columns("D").ColumnWidth = 7

    If ws.Columns("E").ColumnWidth < 10 Then ws.Columns("E").ColumnWidth = 10   'Order Nr.
    If ws.Columns("F").ColumnWidth < 7 Then ws.Columns("F").ColumnWidth = 7     'Item
    If ws.Columns("G").ColumnWidth < 6 Then ws.Columns("G").ColumnWidth = 6     'Qty.
    If ws.Columns("H").ColumnWidth < 14 Then ws.Columns("H").ColumnWidth = 14   'Dimensions
    If ws.Columns("I").ColumnWidth < 16 Then ws.Columns("I").ColumnWidth = 16   'Customer
    If ws.Columns("J").ColumnWidth < 12 Then ws.Columns("J").ColumnWidth = 12   'Customer / info
    If ws.Columns("K").ColumnWidth < 9 Then ws.Columns("K").ColumnWidth = 6      'Route (+1)
    If ws.Columns("L").ColumnWidth < 3 Then ws.Columns("L").ColumnWidth = 3      'RM
    If ws.Columns("M").ColumnWidth < 19 Then ws.Columns("M").ColumnWidth = 13    'Process State (+1)
    ws.Columns("N").ColumnWidth = 1
End Sub

'------------------------------------------------------------------------------
' Procedure: StandardizeImportedDetailFontSize
' Scope: Private Sub
'
' What it does:
'   Performs the workbook-specific step named
'   StandardizeImportedDetailFontSize inside TemplateImporter.
'
' Why it exists:
'   The master workbook uses this module to turn a raw delivery list into the
'   operational sheets used by scanning, printing, exports, and intake
'   snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub StandardizeImportedDetailFontSize(ByVal ws As Worksheet)
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim firstDataRow As Long
    Dim lastRealRow As Long
    Dim orderCol As Long
    Dim itemCol As Long
    Dim r As Long

    On Error Resume Next
    ws.Unprotect Password:=""
    On Error GoTo 0

    Set orderHdr = FindHeaderCellTemplate(ws, Array("Order Nr."))
    Set itemHdr = FindHeaderCellTemplate(ws, Array("Item Nr.", "Item"))

    If orderHdr Is Nothing Or itemHdr Is Nothing Then Exit Sub

    firstDataRow = orderHdr.Row + 1
    orderCol = orderHdr.Column
    itemCol = itemHdr.Column

    lastRealRow = FindLastRealDeliveryRowTemplate(ws, orderCol, itemCol, firstDataRow)
    If lastRealRow = 0 Then Exit Sub

    For r = firstDataRow To lastRealRow
        If IsRealDeliveryLineTemplate(ws, r, orderCol, itemCol) Then
            ws.Range("A" & r & ":J" & r).Font.Size = 8
            ws.Range("K" & r & ":AV" & r).Font.Size = 10
        End If
    Next r
End Sub

'------------------------------------------------------------------------------
' Procedure: UnmergeUsedRangeFromRowTemplate
' Scope: Private Sub
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   UnmergeUsedRangeFromRowTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub UnmergeUsedRangeFromRowTemplate(ByVal ws As Worksheet, ByVal startRow As Long)
    Dim usedRng As Range
    Dim targetRng As Range

    Set usedRng = GetWholeUsedRangeTemplate(ws)
    If usedRng Is Nothing Then Exit Sub

    If startRow < 1 Then startRow = 1

    Set targetRng = Intersect(usedRng, ws.Range(startRow & ":" & ws.rows.Count))
    If targetRng Is Nothing Then Exit Sub

    UnmergeRangeSafeTemplate targetRng
End Sub

'------------------------------------------------------------------------------
' Procedure: NormalizeDeliveryListTitleTemplate
' Scope: Private Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   NormalizeDeliveryListTitleTemplate.
'
' Why it exists:
'   Remakes need separate visual and print/export handling so replacement
'   glass is not confused with regular delivery-list work.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub NormalizeDeliveryListTitleTemplate(ByVal ws As Worksheet)
    Dim dt As Date
    Dim titleText As String

    On Error Resume Next
    ws.Unprotect Password:=""
    On Error GoTo 0

    dt = GetDeliveryListDateForFileName(ws)

    If dt > 0 Then
        titleText = "DELIVERY LIST FOR " & Format$(dt, "m/d/yyyy")
    Else
        titleText = "DELIVERY LIST"
    End If

    UnmergeRangeSafeTemplate ws.Range("A1:N4")
    ws.Range("A1:N4").ClearContents

    With ws.Range("A2:N3")
        .Merge
        .Value = titleText
        .HorizontalAlignment = xlCenter
        .VerticalAlignment = xlCenter
        .Font.Bold = True
        .Font.Size = 20
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: NormalizeImportedRowHeights
' Scope: Private Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   NormalizeImportedRowHeights.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub NormalizeImportedRowHeights(ByVal ws As Worksheet)
    Dim lastRow As Long
    Dim r As Long
    Dim maxAllowedHeight As Double
    Dim normalDataHeight As Double

    lastRow = GetUsedRangeLastRowTemplate(ws)
    If lastRow < 1 Then Exit Sub

    maxAllowedHeight = 30
    normalDataHeight = 13

    ws.rows.Hidden = False

    For r = 7 To lastRow
        If ws.rows(r).RowHeight > maxAllowedHeight Then
            ws.rows(r).RowHeight = normalDataHeight
        End If
    Next r
End Sub

'------------------------------------------------------------------------------
' Procedure: CleanUserSelectionTextTemplate
' Scope: Private Function
'
' What it does:
'   Cleans or normalizes text so comparisons, keys, and operator messages are
'   stable (CleanUserSelectionTextTemplate).
'
' Why it exists:
'   The workbook compares text from Excel, barcodes, SharePoint, and Power
'   Automate; normalization prevents small formatting differences from
'   breaking logic.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function CleanUserSelectionTextTemplate(ByVal s As String, Optional ByVal removeSpaces As Boolean = False) As String
    s = Replace$(s, Chr$(160), " ")
    s = Replace$(s, vbCr, "")
    s = Replace$(s, vbLf, "")
    s = Replace$(s, vbTab, " ")
    On Error Resume Next
    s = Application.WorksheetFunction.Clean(s)
    On Error GoTo 0
    s = Trim$(s)
    s = Replace$(s, ";", ",")

    If removeSpaces Then
        s = Replace$(s, " ", "")
    End If

    CleanUserSelectionTextTemplate = s
End Function

'------------------------------------------------------------------------------
' Procedure: ShouldDeleteImportedSpacerRowTemplate
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   ShouldDeleteImportedSpacerRowTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function ShouldDeleteImportedSpacerRowTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, ByVal orderCol As Long, ByVal itemCol As Long) As Boolean
    Dim ordTxt As String
    Dim itemTxt As String

    ordTxt = Trim$(CStr(ws.Cells(rowNum, orderCol).Value))
    itemTxt = Trim$(CStr(ws.Cells(rowNum, itemCol).Value))

    'Keep real delivery lines
    If Len(ordTxt) > 0 Or Len(itemTxt) > 0 Then Exit Function

    'Keep section headers
    If IsSectionHeaderRowTemplate(ws, rowNum, orderCol, itemCol) Then Exit Function

    'Delete completely blank delivery-list-side rows
    ShouldDeleteImportedSpacerRowTemplate = _
        (Application.WorksheetFunction.CountA(ws.Range("A" & rowNum & ":N" & rowNum)) = 0)
End Function

'------------------------------------------------------------------------------
' Procedure: RemoveImportedFooterNotes
' Scope: Private Sub
'
' What it does:
'   Performs the workbook-specific step named RemoveImportedFooterNotes inside
'   TemplateImporter.
'
' Why it exists:
'   The master workbook uses this module to turn a raw delivery list into the
'   operational sheets used by scanning, printing, exports, and intake
'   snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub RemoveImportedFooterNotes(ByVal ws As Worksheet)
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim firstDataRow As Long
    Dim lastUsedRow As Long
    Dim orderCol As Long
    Dim itemCol As Long
    Dim r As Long

    Set orderHdr = FindHeaderCellTemplate(ws, Array("Order Nr."))
    Set itemHdr = FindHeaderCellTemplate(ws, Array("Item Nr.", "Item"))

    If orderHdr Is Nothing Or itemHdr Is Nothing Then Exit Sub

    firstDataRow = orderHdr.Row + 1
    orderCol = orderHdr.Column
    itemCol = itemHdr.Column
    lastUsedRow = GetUsedRangeLastRowTemplate(ws)

    ws.rows.Hidden = False

    For r = lastUsedRow To firstDataRow Step -1
        If IsSectionHeaderRowTemplate(ws, r, orderCol, itemCol) Then
            'keep section headers

        ElseIf IsRealDeliveryLineTemplate(ws, r, orderCol, itemCol) Then
            'keep real rows

        ElseIf Application.WorksheetFunction.CountA(ws.Range("A" & r & ":N" & r)) = 0 Then
            ws.rows(r).Delete Shift:=xlUp

        Else
            ClearImportedNonLineRowTemplate ws, r
        End If
    Next r
End Sub

'------------------------------------------------------------------------------
' Procedure: ShouldClearImportedNonLineRowTemplate
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   ShouldClearImportedNonLineRowTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function ShouldClearImportedNonLineRowTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, ByVal orderCol As Long, ByVal itemCol As Long) As Boolean
    Dim ordTxt As String
    Dim itemTxt As String

    ordTxt = Trim$(CStr(ws.Cells(rowNum, orderCol).Value))
    itemTxt = Trim$(CStr(ws.Cells(rowNum, itemCol).Value))

    'Keep real line items
    If Len(ordTxt) > 0 Or Len(itemTxt) > 0 Then Exit Function

    'Keep section headers like 1/4" Mirror
    If IsSectionHeaderRowTemplate(ws, rowNum, orderCol, itemCol) Then Exit Function

    'Only clear rows that still contain imported content on the delivery-list side
    ShouldClearImportedNonLineRowTemplate = _
        (Application.WorksheetFunction.CountA(ws.Range("A" & rowNum & ":N" & rowNum)) > 0)
End Function

'------------------------------------------------------------------------------
' Procedure: ClearImportedNonLineRowTemplate
' Scope: Private Sub
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   ClearImportedNonLineRowTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ClearImportedNonLineRowTemplate(ByVal ws As Worksheet, ByVal rowNum As Long)
    Dim c As Range

    On Error Resume Next
    For Each c In ws.Range("A" & rowNum & ":N" & rowNum)
        If c.MergeCells Then
            c.MergeArea.UnMerge
        End If
    Next c
    On Error GoTo 0

    ws.rows(rowNum).Hidden = False
    ws.Range("A" & rowNum & ":N" & rowNum).ClearContents
    ws.rows(rowNum).Delete Shift:=xlUp
End Sub

'------------------------------------------------------------------------------
' Procedure: ClearImportedNonLineRowTemplate_NoDelete
' Scope: Private Sub
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   ClearImportedNonLineRowTemplate_NoDelete.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ClearImportedNonLineRowTemplate_NoDelete(ByVal ws As Worksheet, ByVal rowNum As Long)
    Dim c As Range

    On Error Resume Next
    For Each c In ws.Range("A" & rowNum & ":N" & rowNum)
        If c.MergeCells Then
            c.MergeArea.UnMerge
        End If
    Next c
    On Error GoTo 0

    ws.rows(rowNum).Hidden = False

    With ws.Range("A" & rowNum & ":N" & rowNum)
        .ClearContents
        .Interior.Pattern = xlNone
        .Font.Bold = False
        .Font.Italic = False
        .Font.Underline = xlUnderlineStyleNone
        .Font.Strikethrough = False
        .Font.ColorIndex = xlAutomatic
        .Borders.LineStyle = xlNone
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: RemoveImportedFooterNotesForSharePointSafe
' Scope: Private Sub
'
' What it does:
'   Performs the workbook-specific step named
'   RemoveImportedFooterNotesForSharePointSafe inside TemplateImporter.
'
' Why it exists:
'   The master workbook uses this module to turn a raw delivery list into the
'   operational sheets used by scanning, printing, exports, and intake
'   snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub RemoveImportedFooterNotesForSharePointSafe(ByVal ws As Worksheet)
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim firstDataRow As Long
    Dim lastUsedRow As Long
    Dim orderCol As Long
    Dim itemCol As Long
    Dim r As Long

    Set orderHdr = FindHeaderCellTemplate(ws, Array("Order Nr."))
    Set itemHdr = FindHeaderCellTemplate(ws, Array("Item Nr.", "Item"))

    If orderHdr Is Nothing Or itemHdr Is Nothing Then Exit Sub

    firstDataRow = orderHdr.Row + 1
    orderCol = orderHdr.Column
    itemCol = itemHdr.Column
    lastUsedRow = GetUsedRangeLastRowTemplate(ws)

    ws.rows.Hidden = False

    For r = lastUsedRow To firstDataRow Step -1
        If IsSectionHeaderRowTemplate(ws, r, orderCol, itemCol) Then
            'keep section headers

        ElseIf IsRealDeliveryLineTemplate(ws, r, orderCol, itemCol) Then
            'keep real rows

        ElseIf Application.WorksheetFunction.CountA(ws.Range("A" & r & ":N" & r)) = 0 Then
            'Do NOT delete rows during SharePoint save prep
            ClearImportedNonLineRowTemplate_NoDelete ws, r

        Else
            ClearImportedNonLineRowTemplate_NoDelete ws, r
        End If
    Next r
End Sub

'------------------------------------------------------------------------------
' Procedure: FindHeaderCellTemplateInCols
' Scope: Private Function
'
' What it does:
'   Finds, writes, validates, or uses worksheet header cells for
'   FindHeaderCellTemplateInCols.
'
' Why it exists:
'   Header locations can move during import/rebuild, so the code uses header
'   discovery to target the correct columns instead of guessing.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function FindHeaderCellTemplateInCols(ByVal ws As Worksheet, ByVal names As Variant, ByVal colAddress As String, Optional ByVal topRows As Long = 250) As Range
    Dim searchRange As Range
    Dim nm As Variant
    Dim f As Range

    Set searchRange = Intersect(ws.Range("1:" & topRows), ws.Columns(colAddress))
    If searchRange Is Nothing Then
        Set FindHeaderCellTemplateInCols = Nothing
        Exit Function
    End If

    For Each nm In names
        Set f = searchRange.Find(What:=CStr(nm), LookIn:=xlValues, LookAt:=xlWhole)
        If Not f Is Nothing Then
            Set FindHeaderCellTemplateInCols = f
            Exit Function
        End If
    Next nm

    For Each nm In names
        Set f = searchRange.Find(What:=CStr(nm), LookIn:=xlValues, LookAt:=xlPart)
        If Not f Is Nothing Then
            Set FindHeaderCellTemplateInCols = f
            Exit Function
        End If
    Next nm

    Set FindHeaderCellTemplateInCols = Nothing
End Function

'------------------------------------------------------------------------------
' Procedure: FindHeaderCellTemplate
' Scope: Private Function
'
' What it does:
'   Finds, writes, validates, or uses worksheet header cells for
'   FindHeaderCellTemplate.
'
' Why it exists:
'   Header locations can move during import/rebuild, so the code uses header
'   discovery to target the correct columns instead of guessing.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function FindHeaderCellTemplate(ByVal ws As Worksheet, ByVal names As Variant, Optional ByVal topRows As Long = 250) As Range
    Dim searchRange As Range
    Dim nm As Variant
    Dim f As Range

    Set searchRange = ws.Range(ws.Cells(1, 1), ws.Cells(topRows, ws.Columns.Count))

    For Each nm In names
        Set f = searchRange.Find(What:=CStr(nm), LookIn:=xlValues, LookAt:=xlWhole)
        If Not f Is Nothing Then
            Set FindHeaderCellTemplate = f
            Exit Function
        End If
    Next nm

    For Each nm In names
        Set f = searchRange.Find(What:=CStr(nm), LookIn:=xlValues, LookAt:=xlPart)
        If Not f Is Nothing Then
            Set FindHeaderCellTemplate = f
            Exit Function
        End If
    Next nm

    Set FindHeaderCellTemplate = Nothing
End Function

'------------------------------------------------------------------------------
' Procedure: FindLastRealDeliveryRowTemplate
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   FindLastRealDeliveryRowTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function FindLastRealDeliveryRowTemplate(ByVal ws As Worksheet, ByVal orderCol As Long, ByVal itemCol As Long, ByVal firstDataRow As Long) As Long
    Dim lastUsedRow As Long
    Dim r As Long

    lastUsedRow = GetLastUsedRowTemplate(ws)

    For r = lastUsedRow To firstDataRow Step -1
        If IsRealDeliveryLineTemplate(ws, r, orderCol, itemCol) Then
            FindLastRealDeliveryRowTemplate = r
            Exit Function
        End If
    Next r

    FindLastRealDeliveryRowTemplate = 0
End Function

'------------------------------------------------------------------------------
' Procedure: IsRealDeliveryLineTemplate
' Scope: Private Function
'
' What it does:
'   Returns a True/False decision used by higher-level workflow code
'   (IsRealDeliveryLineTemplate).
'
' Why it exists:
'   Boolean helpers make business rules readable and keep condition checks
'   consistent across modules.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function IsRealDeliveryLineTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, ByVal orderCol As Long, ByVal itemCol As Long) As Boolean
    Dim ordTxt As String
    Dim itemTxt As String

    ordTxt = CleanLayoutTextTemplate(ws.Cells(rowNum, orderCol).Value)
    itemTxt = CleanLayoutTextTemplate(ws.Cells(rowNum, itemCol).Value)

    ordTxt = Replace$(ordTxt, ",", "")
    itemTxt = Replace$(itemTxt, ",", "")

    IsRealDeliveryLineTemplate = False

    If Len(ordTxt) = 0 Or Len(itemTxt) = 0 Then Exit Function

    If IsNumeric(ordTxt) And IsNumeric(itemTxt) Then
        If CLng(Val(ordTxt)) > 0 And CLng(Val(itemTxt)) > 0 Then
            IsRealDeliveryLineTemplate = True
        End If
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: ForceRow3HeightTemplate
' Scope: Private Sub
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   ForceRow3HeightTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ForceRow3HeightTemplate(ByVal ws As Worksheet)
    If ws Is Nothing Then Exit Sub

    On Error Resume Next
    ws.rows(3).RowHeight = 55
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: BeginQuietUiTemplate
' Scope: Private Sub
'
' What it does:
'   Performs the workbook-specific step named BeginQuietUiTemplate inside
'   TemplateImporter.
'
' Why it exists:
'   The master workbook uses this module to turn a raw delivery list into the
'   operational sheets used by scanning, printing, exports, and intake
'   snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub BeginQuietUiTemplate(Optional ByVal statusText As String = "Updating delivery list...")
    mPrevCalc = Application.Calculation
    mPrevScreenUpdating = Application.ScreenUpdating
    mPrevEnableEvents = Application.EnableEvents
    mPrevDisplayAlerts = Application.DisplayAlerts
    mPrevStatusBar = Application.StatusBar
    mPrevCursor = Application.Cursor

    Application.ScreenUpdating = False
    Application.EnableEvents = False
    Application.DisplayAlerts = False
    Application.Calculation = xlCalculationManual
    Application.Cursor = xlWait
    Application.StatusBar = statusText
End Sub

'------------------------------------------------------------------------------
' Procedure: EndQuietUiTemplate
' Scope: Private Sub
'
' What it does:
'   Performs the workbook-specific step named EndQuietUiTemplate inside
'   TemplateImporter.
'
' Why it exists:
'   The master workbook uses this module to turn a raw delivery list into the
'   operational sheets used by scanning, printing, exports, and intake
'   snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub EndQuietUiTemplate()
    On Error Resume Next
    Application.StatusBar = False
    Application.Cursor = mPrevCursor
    Application.Calculation = mPrevCalc
    Application.DisplayAlerts = mPrevDisplayAlerts
    Application.EnableEvents = mPrevEnableEvents
    Application.ScreenUpdating = mPrevScreenUpdating
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: ManualScanFromUtilityPanel
' Scope: Public Sub
'
' What it does:
'   Builds, formats, deletes, or wires workbook UI shapes/buttons/panels for
'   ManualScanFromUtilityPanel.
'
' Why it exists:
'   Buttons and utility panels are the operator-facing control surface, so
'   they must be rebuilt consistently after imports or sheet refreshes.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub ManualScanFromUtilityPanel()
    Dim dataWs As Worksheet

    On Error GoTo ErrHandler

    Set dataWs = ThisWorkbook.Worksheets("Delivery List")
    dataWs.Activate

    On Error Resume Next
    Application.GoTo dataWs.Range("A1"), True
    On Error GoTo ErrHandler

    Unload frmManualScanEntry
    Load frmManualScanEntry
    frmManualScanEntry.LoadDefaults
    frmManualScanEntry.Show vbModeless

    Exit Sub

ErrHandler:
    MsgBox "ManualScanFromUtilityPanel error " & Err.Number & ":" & vbCrLf & Err.Description, vbCritical, "Manual Scan Error"
End Sub

'------------------------------------------------------------------------------
' Procedure: ManualScanNotice
' Scope: Private Sub
'
' What it does:
'   Builds or displays the operator-facing notice/message used by
'   ManualScanNotice.
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
Private Sub ManualScanNotice(ByVal messageText As String, Optional ByVal titleText As String = "Manual Scan", Optional ByVal style As VbMsgBoxStyle = vbExclamation)
    If Not SuppressManualScanPopups Then
        MsgBox messageText, style, titleText
    End If
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplyManualScanEntryTemplate
' Scope: Public Function
'
' What it does:
'   Applies formatting, filters, protection, selection state, or business-
'   state changes for ApplyManualScanEntryTemplate.
'
' Why it exists:
'   Separating apply steps makes it easier to rebuild sheets and then
'   consistently reapply the visual/workflow rules operators rely on.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function ApplyManualScanEntryTemplate(ByVal mode As String, _
                                             ByVal ord As Long, _
                                             ByVal itm As Long, _
                                             ByVal qty As Long, _
                                             Optional ByVal skipPostSync As Boolean = False, _
                                             Optional ByVal sourceScanTime As Variant) As Boolean

    Dim dataWs As Worksheet
    Dim matchRow As Long
    Dim successCount As Long
    Dim i As Long
    Dim scanCode As String
    Dim commentCol As Long
    Dim modeLabel As String

    Dim oldScreenUpdating As Boolean
    Dim oldEnableEvents As Boolean
    Dim oldDisplayAlerts As Boolean
    Dim oldStatusBar As Variant

    On Error GoTo ErrHandler

    oldScreenUpdating = Application.ScreenUpdating
    oldEnableEvents = Application.EnableEvents
    oldDisplayAlerts = Application.DisplayAlerts
    oldStatusBar = Application.StatusBar

    Application.ScreenUpdating = False
    Application.EnableEvents = False
    Application.DisplayAlerts = False
    Application.StatusBar = "Applying manual scan."

    Set dataWs = ThisWorkbook.Worksheets("Delivery List")

    On Error Resume Next
    dataWs.Unprotect Password:=""
    On Error GoTo ErrHandler

    ScannerValidation.EnsureScanLayout dataWs

    matchRow = FindManualMatchRowTemplate(dataWs, ord, itm)
    If matchRow = 0 Then
    ManualScanNotice "Could not find this line on the Delivery List:" & vbCrLf & vbCrLf & _
                     "Order Number: " & ord & vbCrLf & _
                     "Item Number: " & Format$(itm, "000"), _
                     "Manual Scan - Line Not Found", vbExclamation
    GoTo SafeExit
End If

    modeLabel = GetManualModeLabelTemplate(dataWs, mode, matchRow)

    For i = 1 To qty
        scanCode = GetManualBarcodeForModeTemplate(dataWs, matchRow, mode, ord, itm)

        If IsMissing(sourceScanTime) Then
    ScannerValidation.ProcessScan dataWs, scanCode, mode
ElseIf IsDate(sourceScanTime) Then
    ScannerValidation.ProcessScan dataWs, scanCode, mode, CDate(sourceScanTime)
Else
    ScannerValidation.ProcessScan dataWs, scanCode, mode
End If

        If Not ScannerValidation.LastScanSuccess Then Exit For
        successCount = successCount + 1
    Next i

        If successCount > 0 Then
        matchRow = FindManualMatchRowTemplate(dataWs, ord, itm)
        commentCol = GetManualCommentsColTemplate(dataWs, mode)

        If commentCol > 0 And matchRow > 0 Then
            AppendManualScanCommentTemplate dataWs.Cells(matchRow, commentCol), _
                "Manual scan entered"
        End If

                'Refresh main-sheet state first
        ThisWorkbook.RefreshAllDeliveryListProcessStates dataWs
        ForceRow3HeightTemplate dataWs
        HighlightGreenvilleRowsTemplate dataWs
        AutoFitCommentColumnsTemplate dataWs

                If Not skipPostSync Then
            'Make Delivery List the active sheet BEFORE the sync,
            'so background sync returns here instead of Utility Panel
            dataWs.Activate

            'Use the normal full sync path so scanner sheets keep the correct hidden columns
            SyncDeliveryListToScannerSheets False, True

            'Keep the user on the Delivery List sheet after manual scan
            dataWs.Activate
        End If

        If successCount = qty Then
            ManualScanNotice "Manual scan complete." & vbCrLf & vbCrLf & _
                             "Mode: " & modeLabel & vbCrLf & _
                             "Order Number: " & ord & vbCrLf & _
                             "Item Number: " & Format$(itm, "000") & vbCrLf & _
                             "Quantity Applied: " & successCount, _
                             "Manual Scan Complete", vbInformation

            ApplyManualScanEntryTemplate = True
        Else
            ManualScanNotice "Manual scan partially completed." & vbCrLf & vbCrLf & _
                             "Mode: " & modeLabel & vbCrLf & _
                             "Order Number: " & ord & vbCrLf & _
                             "Item Number: " & Format$(itm, "000") & vbCrLf & _
                             "Quantity Applied: " & successCount & " of " & qty & vbCrLf & vbCrLf & _
                             "The scan stopped when the normal scan rules blocked the next quantity.", _
                             "Manual Scan Partial", vbExclamation

            ApplyManualScanEntryTemplate = False
        End If
    End If

SafeExit:
    Application.StatusBar = False
    Application.DisplayAlerts = oldDisplayAlerts
    Application.EnableEvents = oldEnableEvents
    Application.ScreenUpdating = oldScreenUpdating
    Exit Function

ErrHandler:
    Application.StatusBar = False
    Application.DisplayAlerts = oldDisplayAlerts
    Application.EnableEvents = oldEnableEvents
    Application.ScreenUpdating = oldScreenUpdating
    ManualScanNotice "ApplyManualScanEntryTemplate error " & Err.Number & ":" & vbCrLf & Err.Description, _
                     "Manual Scan Error", vbCritical
End Function

'------------------------------------------------------------------------------
' Procedure: PromptForManualScanModeTemplate
' Scope: Private Function
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   PromptForManualScanModeTemplate.
'
' Why it exists:
'   Remakes need separate visual and print/export handling so replacement
'   glass is not confused with regular delivery-list work.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function PromptForManualScanModeTemplate() As String
    Dim choice As Variant

    choice = Application.InputBox( _
        "Choose manual scan type:" & vbCrLf & vbCrLf & _
        "1 = Staging" & vbCrLf & _
        "2 = Outbound" & vbCrLf & _
        "3 = Inbound / Receive", _
        "Manual Scan - Select Type", Type:=1)

    If VarType(choice) = vbBoolean Then Exit Function

    Select Case CLng(Val(choice))
        Case 1
            PromptForManualScanModeTemplate = "STAGING"
        Case 2
            PromptForManualScanModeTemplate = "SEND"
        Case 3
            PromptForManualScanModeTemplate = "RECV"
        Case Else
            MsgBox "Please enter 1, 2, or 3.", vbExclamation, "Manual Scan"
    End Select
End Function

'------------------------------------------------------------------------------
' Procedure: PromptForPositiveLongTemplate
' Scope: Private Function
'
' What it does:
'   Performs the workbook-specific step named PromptForPositiveLongTemplate
'   inside TemplateImporter.
'
' Why it exists:
'   The master workbook uses this module to turn a raw delivery list into the
'   operational sheets used by scanning, printing, exports, and intake
'   snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function PromptForPositiveLongTemplate(ByVal promptText As String, ByVal titleText As String, _
                                               ByVal minValue As Long, ByVal maxValue As Long) As Long
    Dim v As Variant

    Do
        v = Application.InputBox(promptText, titleText, Type:=1)

        If VarType(v) = vbBoolean Then
            PromptForPositiveLongTemplate = -1
            Exit Function
        End If

        If IsNumeric(v) Then
            If CLng(v) >= minValue And CLng(v) <= maxValue Then
                PromptForPositiveLongTemplate = CLng(v)
                Exit Function
            End If
        End If

        MsgBox "Please enter a whole number between " & minValue & " and " & maxValue & ".", _
               vbExclamation, titleText
    Loop
End Function

'------------------------------------------------------------------------------
' Procedure: FindManualMatchRowTemplate
' Scope: Private Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   FindManualMatchRowTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function FindManualMatchRowTemplate(ByVal dataWs As Worksheet, ByVal ord As Long, ByVal itm As Long) As Long
    Dim orderHdr As Range
    Dim itemHdr As Range
    Dim orderCol As Long
    Dim itemCol As Long
    Dim firstRow As Long
    Dim lastRow As Long
    Dim rng As Range
    Dim f As Range
    Dim firstAddr As String

    Set orderHdr = FindHeaderCellTemplateInCols(dataWs, Array("Order Nr."), "A:N", 250)
    Set itemHdr = FindHeaderCellTemplateInCols(dataWs, Array("Item Nr.", "Item"), "A:N", 250)

    If orderHdr Is Nothing Or itemHdr Is Nothing Then Exit Function

    orderCol = orderHdr.Column
    itemCol = itemHdr.Column
    firstRow = orderHdr.Row + 1
    lastRow = dataWs.Cells(dataWs.rows.Count, orderCol).End(xlUp).Row

    If lastRow < firstRow Then Exit Function

    Set rng = dataWs.Range(dataWs.Cells(firstRow, orderCol), dataWs.Cells(lastRow, orderCol))
    Set f = rng.Find(What:=CStr(ord), LookIn:=xlValues, LookAt:=xlWhole)

    If Not f Is Nothing Then
        firstAddr = f.Address
        Do
            If IsNumeric(dataWs.Cells(f.Row, itemCol).Value) Then
                If CLng(Val(dataWs.Cells(f.Row, itemCol).Value)) = itm Then
                    FindManualMatchRowTemplate = f.Row
                    Exit Function
                End If
            End If
            Set f = rng.FindNext(f)
        Loop While Not f Is Nothing And f.Address <> firstAddr
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: GetManualModeLabelTemplate
' Scope: Private Function
'
' What it does:
'   Returns a workbook object, setting, status value, parsed value, or
'   calculated result used by other procedures (GetManualModeLabelTemplate).
'
' Why it exists:
'   Using one getter keeps callers from duplicating lookup logic and protects
'   them from missing sheets, missing names, or blank values.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetManualModeLabelTemplate(ByVal ws As Worksheet, ByVal mode As String, ByVal rowNum As Long) As String
    Select Case UCase$(mode)
        Case "STAGING"
            GetManualModeLabelTemplate = "Staging"

        Case "SEND"
            GetManualModeLabelTemplate = "Outbound"

        Case "RECV"
            If IsCPURowTemplate(ws, rowNum) Then
                GetManualModeLabelTemplate = "Inbound - Customer Pickup"
            ElseIf IsGreenvilleRowTemplate(ws, rowNum) Then
                GetManualModeLabelTemplate = "Inbound - Greenville"
            Else
                GetManualModeLabelTemplate = GetReceiveSheetName()
            End If

        Case Else
            GetManualModeLabelTemplate = UCase$(mode)
    End Select
End Function

'------------------------------------------------------------------------------
' Procedure: BuildManualBarcodeTemplate
' Scope: Private Function
'
' What it does:
'   Cleans, decodes, validates, writes, or displays barcode data for
'   BuildManualBarcodeTemplate.
'
' Why it exists:
'   The barcode is the link between the physical glass label and the
'   order/item row, so the project must parse and validate it consistently.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BuildManualBarcodeTemplate(ByVal ord As Long, ByVal itm As Long) As String
    'ScannerValidation.ProcessScan requires: T200 + 12 digits = 16 total chars
    'Order = 6 digits, Item = 3 digits, plus 3 filler digits on the end
    BuildManualBarcodeTemplate = "T200" & Format$(ord, "000000") & Format$(itm, "000") & "000"
End Function

'------------------------------------------------------------------------------
' Procedure: GetManualBarcodeForModeTemplate
' Scope: Private Function
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   GetManualBarcodeForModeTemplate.
'
' Why it exists:
'   Remakes need separate visual and print/export handling so replacement
'   glass is not confused with regular delivery-list work.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetManualBarcodeForModeTemplate(ByVal ws As Worksheet, ByVal rowNum As Long, ByVal mode As String, _
                                                 ByVal ord As Long, ByVal itm As Long) As String
    Dim barCol As Long
    Dim existingCode As String

    barCol = GetManualBarcodeColTemplate(ws, mode)

    If barCol > 0 Then
        existingCode = Trim$(CStr(ws.Cells(rowNum, barCol).Value))
        If Len(existingCode) > 0 Then
            GetManualBarcodeForModeTemplate = existingCode
            Exit Function
        End If
    End If

    GetManualBarcodeForModeTemplate = BuildManualBarcodeTemplate(ord, itm)
End Function

'------------------------------------------------------------------------------
' Procedure: GetManualBarcodeColTemplate
' Scope: Private Function
'
' What it does:
'   Cleans, decodes, validates, writes, or displays barcode data for
'   GetManualBarcodeColTemplate.
'
' Why it exists:
'   The barcode is the link between the physical glass label and the
'   order/item row, so the project must parse and validate it consistently.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetManualBarcodeColTemplate(ByVal ws As Worksheet, ByVal mode As String) As Long
    Dim hdr As Range

    Select Case UCase$(mode)
        Case "STAGING"
            Set hdr = FindHeaderCellTemplateInCols(ws, Array(ScannerValidation.HEADER_TEXT_BAR_STAGING), "AP:AV", 60)

        Case "SEND"
            Set hdr = FindHeaderCellTemplateInCols(ws, Array(ScannerValidation.HEADER_TEXT_BAR_SEND), "P:W", 60)

        Case "RECV"
            Set hdr = FindHeaderCellTemplateInCols(ws, Array(ScannerValidation.HEADER_TEXT_BAR_RECV), "Y:AG", 60)
    End Select

    If Not hdr Is Nothing Then GetManualBarcodeColTemplate = hdr.Column
End Function

'------------------------------------------------------------------------------
' Procedure: GetManualCommentsColTemplate
' Scope: Private Function
'
' What it does:
'   Finds, sizes, hides, formats, or uses worksheet columns for
'   GetManualCommentsColTemplate.
'
' Why it exists:
'   The system depends on fixed scan blocks and discovered delivery-list
'   columns, so column handling must be centralized and predictable.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetManualCommentsColTemplate(ByVal ws As Worksheet, ByVal mode As String) As Long
    Dim hdr As Range

    Select Case UCase$(mode)
        Case "STAGING"
            Set hdr = FindHeaderCellTemplateInCols(ws, Array("Comments"), "AP:AV", 60)

        Case "SEND"
            Set hdr = FindHeaderCellTemplateInCols(ws, Array("Comments"), "P:W", 60)

        Case "RECV"
            Set hdr = FindHeaderCellTemplateInCols(ws, Array("Comments"), "Y:AG", 60)
    End Select

    If Not hdr Is Nothing Then GetManualCommentsColTemplate = hdr.Column
End Function

'------------------------------------------------------------------------------
' Procedure: AppendManualScanCommentTemplate
' Scope: Private Sub
'
' What it does:
'   Appends text or state to an existing cell/message for
'   AppendManualScanCommentTemplate.
'
' Why it exists:
'   Append helpers preserve prior context while adding audit or override
'   information for the operator.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub AppendManualScanCommentTemplate(ByVal c As Range, ByVal msg As String)
    Dim cur As String

    cur = Trim$(CStr(c.Value))

    If Len(cur) = 0 Then
        c.Value = msg
    ElseIf InStr(1, cur, msg, vbTextCompare) = 0 Then
        c.Value = cur & " | " & msg
    End If

    c.WrapText = False
    c.HorizontalAlignment = xlCenter
    c.VerticalAlignment = xlCenter
End Sub

'------------------------------------------------------------------------------
' Procedure: ApplyRemakePrintColumnHeadersTemplate
' Scope: Private Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   ApplyRemakePrintColumnHeadersTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ApplyRemakePrintColumnHeadersTemplate(ByVal ws As Worksheet)
    Dim hdrRow As Long

    hdrRow = GetRemakePrintHeaderRowTemplate(ws)

    On Error Resume Next
    ws.Range("A" & hdrRow & ":K" & hdrRow).UnMerge
    On Error GoTo 0

    ws.Range("A" & hdrRow & ":K" & hdrRow).ClearContents

    ws.Range("A" & hdrRow).Value = "Job Nr."
    ws.Range("C" & hdrRow).Value = "Order"
    ws.Range("E" & hdrRow).Value = "Item"
    ws.Range("G" & hdrRow).Value = "Qty."
    ws.Range("I" & hdrRow).Value = "Dimensions"
    ws.Range("K" & hdrRow).Value = "Check Off"

    With ws.Range("A" & hdrRow & ":K" & hdrRow)
        .Font.Bold = True
        .Font.Underline = xlUnderlineStyleNone
        .VerticalAlignment = xlCenter
    End With

    ws.Range("A" & hdrRow).HorizontalAlignment = xlLeft
    ws.Range("C" & hdrRow).HorizontalAlignment = xlCenter
    ws.Range("E" & hdrRow).HorizontalAlignment = xlCenter
    ws.Range("G" & hdrRow).HorizontalAlignment = xlCenter
    ws.Range("I" & hdrRow).HorizontalAlignment = xlLeft
    ws.Range("K" & hdrRow).HorizontalAlignment = xlCenter
End Sub

'------------------------------------------------------------------------------
' Procedure: ClearRemakePreviewCheckBoxes
' Scope: Private Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   ClearRemakePreviewCheckBoxes.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub ClearRemakePreviewCheckBoxes(ByVal ws As Worksheet)
    Dim i As Long
    Dim shp As Shape
    Dim bodyStartRow As Long

    bodyStartRow = GetRemakePrintBodyStartRowTemplate(ws)

    On Error Resume Next
    For i = ws.Shapes.Count To 1 Step -1
        Set shp = ws.Shapes(i)

        If shp.Type <> msoPicture And shp.Type <> msoLinkedPicture Then
            If shp.TopLeftCell.Row >= bodyStartRow And shp.TopLeftCell.Column >= 11 Then
                shp.Delete
            End If
        End If
    Next i
    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: AddRemakeCheckbox
' Scope: Private Sub
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   AddRemakeCheckbox.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub AddRemakeCheckbox(ByVal ws As Worksheet, ByVal destRow As Long)
    Dim shp As Shape
    Dim boxSize As Double
    Dim leftPos As Double
    Dim topPos As Double

    boxSize = 8

    leftPos = ws.Cells(destRow, 11).Left + (ws.Cells(destRow, 11).Width - boxSize) / 2
    topPos = ws.Cells(destRow, 11).Top + (ws.rows(destRow).RowHeight - boxSize) / 2

    Set shp = ws.Shapes.AddShape(msoShapeRectangle, leftPos, topPos, boxSize, boxSize)

    With shp
        .Name = "rmChk_" & destRow & "_" & Format$(Timer * 1000, "0")
        .Placement = xlMoveAndSize
        .Fill.Visible = msoFalse
        .Line.Visible = msoTrue
        .Line.foreColor.RGB = RGB(0, 0, 0)
        .Line.Weight = 0.75
    End With
End Sub

'------------------------------------------------------------------------------
' Procedure: ProcessQueuedScansBridge
' Scope: Public Sub
'
' What it does:
'   Handles queue/request state used by the shared ScanQueue workflow for
'   ProcessQueuedScansBridge.
'
' Why it exists:
'   Queue state must be tracked carefully so buffered intake scans, master
'   processing, retries, and final results stay aligned.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub ProcessQueuedScansBridge()
    ThisWorkbook.ProcessQueuedScansInternal
End Sub

'------------------------------------------------------------------------------
' Procedure: GetRemakePrintHeaderRowTemplate
' Scope: Private Function
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   GetRemakePrintHeaderRowTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetRemakePrintHeaderRowTemplate(ByVal ws As Worksheet) As Long
    Dim f As Range

    On Error Resume Next
    Set f = ws.Cells.Find(What:="Job Nr.", LookIn:=xlValues, LookAt:=xlWhole, _
                          SearchOrder:=xlByRows, SearchDirection:=xlNext, MatchCase:=False)
    On Error GoTo 0

    If Not f Is Nothing Then
        GetRemakePrintHeaderRowTemplate = f.Row
    Else
        'Fallback to old layout if header not found
        GetRemakePrintHeaderRowTemplate = 5
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: GetRemakePrintBodyStartRowTemplate
' Scope: Private Function
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   GetRemakePrintBodyStartRowTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetRemakePrintBodyStartRowTemplate(ByVal ws As Worksheet) As Long
    'Old layout:
    'header row = 5
    'section template row = 7
    'so body starts header + 2
    GetRemakePrintBodyStartRowTemplate = GetRemakePrintHeaderRowTemplate(ws) + 2
End Function

'------------------------------------------------------------------------------
' Procedure: GetRemakePrintSectionTemplateRowTemplate
' Scope: Private Function
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   GetRemakePrintSectionTemplateRowTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetRemakePrintSectionTemplateRowTemplate(ByVal ws As Worksheet) As Long
    GetRemakePrintSectionTemplateRowTemplate = GetRemakePrintHeaderRowTemplate(ws) + 2
End Function

'------------------------------------------------------------------------------
' Procedure: GetRemakePrintSpacerTemplateRowTemplate
' Scope: Private Function
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   GetRemakePrintSpacerTemplateRowTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetRemakePrintSpacerTemplateRowTemplate(ByVal ws As Worksheet) As Long
    GetRemakePrintSpacerTemplateRowTemplate = GetRemakePrintHeaderRowTemplate(ws) + 3
End Function

'------------------------------------------------------------------------------
' Procedure: GetRemakePrintLineTemplateRowTemplate
' Scope: Private Function
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   GetRemakePrintLineTemplateRowTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function GetRemakePrintLineTemplateRowTemplate(ByVal ws As Worksheet) As Long
    GetRemakePrintLineTemplateRowTemplate = GetRemakePrintHeaderRowTemplate(ws) + 4
End Function

'------------------------------------------------------------------------------
' Procedure: HasUpdatedRowPurpleBorderTemplate
' Scope: Private Function
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   HasUpdatedRowPurpleBorderTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function HasUpdatedRowPurpleBorderTemplate(ByVal rng As Range) As Boolean
    If rng Is Nothing Then Exit Function

    On Error Resume Next

    HasUpdatedRowPurpleBorderTemplate = _
        (rng.Borders(xlEdgeLeft).LineStyle <> xlNone And rng.Borders(xlEdgeLeft).Color = RGB(112, 48, 160)) And _
        (rng.Borders(xlEdgeRight).LineStyle <> xlNone And rng.Borders(xlEdgeRight).Color = RGB(112, 48, 160))

    On Error GoTo 0
End Function

'------------------------------------------------------------------------------
' Procedure: BuildExistingUpdatedRowKeySetTemplate
' Scope: Private Function
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   BuildExistingUpdatedRowKeySetTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BuildExistingUpdatedRowKeySetTemplate(ByVal ws As Worksheet, _
                                                       ByVal firstDataRow As Long, _
                                                       ByVal orderCol As Long, _
                                                       ByVal itemCol As Long) As Object
    Dim dict As Object
    Dim lastRealRow As Long
    Dim r As Long
    Dim currentSectionKey As String
    Dim rowKey As String

    Set dict = CreateObject("Scripting.Dictionary")

    lastRealRow = FindLastRealDeliveryRowTemplate(ws, orderCol, itemCol, firstDataRow)
    If lastRealRow < firstDataRow Then
        Set BuildExistingUpdatedRowKeySetTemplate = dict
        Exit Function
    End If

    currentSectionKey = vbNullString

    For r = firstDataRow To lastRealRow
        If IsSectionHeaderRowTemplate(ws, r, orderCol, itemCol) Then
            currentSectionKey = NormalizeSectionKey(CStr(ws.Cells(r, 1).Value))

        ElseIf IsRealDeliveryLineTemplate(ws, r, orderCol, itemCol) Then
            If Len(currentSectionKey) = 0 Then currentSectionKey = "__UNSECTIONED__"

            If HasUpdatedRowPurpleBorderTemplate(ws.Range("A" & r & ":J" & r)) Then
                rowKey = BuildCurrentDeliveryLineKeyWithKindTemplate(ws, r, currentSectionKey, orderCol, itemCol)
                If Len(rowKey) > 0 Then
                    If Not dict.Exists(rowKey) Then dict.Add rowKey, True
                End If
            End If
        End If
    Next r

    Set BuildExistingUpdatedRowKeySetTemplate = dict
End Function

'------------------------------------------------------------------------------
' Procedure: GetSafeVisibleDestinationModeTemplate
' Scope: Public Function
'
' What it does:
'   Returns a workbook object, setting, status value, parsed value, or
'   calculated result used by other procedures
'   (GetSafeVisibleDestinationModeTemplate).
'
' Why it exists:
'   Using one getter keeps callers from duplicating lookup logic and protects
'   them from missing sheets, missing names, or blank values.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function GetSafeVisibleDestinationModeTemplate(ByVal indianTrailOn As Boolean, _
                                                       ByVal greenvilleOn As Boolean, _
                                                       ByVal cpuOn As Boolean) As String
    Dim outText As String

    If indianTrailOn Then AddTokenTemplate outText, "STANDARD"
    If greenvilleOn Then AddTokenTemplate outText, "GREENVILLE"
    If cpuOn Then AddTokenTemplate outText, "CPU"

    GetSafeVisibleDestinationModeTemplate = outText
End Function

'------------------------------------------------------------------------------
' Procedure: HasPrintableRowsForTemplate
' Scope: Public Function
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   HasPrintableRowsForTemplate.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function HasPrintableRowsForTemplate(ByVal ws As Worksheet, _
                                             ByVal firstDataRow As Long, _
                                             ByVal lastRealRow As Long, _
                                             ByVal orderCol As Long, _
                                             ByVal itemCol As Long, _
                                             ByVal destinationMode As String, _
                                             ByVal printKind As String) As Boolean
    Dim r As Long

    For r = firstDataRow To lastRealRow
        If IsRealDeliveryLineTemplate(ws, r, orderCol, itemCol) Then
            If DoesPrintModeMatchRowTemplate(ws, r, destinationMode, printKind) Then
                HasPrintableRowsForTemplate = True
                Exit Function
            End If
        End If
    Next r
End Function

'------------------------------------------------------------------------------
' Procedure: PromptForPrintOptionsTemplate
' Scope: Private Function
'
' What it does:
'   Performs the workbook-specific step named PromptForPrintOptionsTemplate
'   inside TemplateImporter.
'
' Why it exists:
'   The master workbook uses this module to turn a raw delivery list into the
'   operational sheets used by scanning, printing, exports, and intake
'   snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function PromptForPrintOptionsTemplate(ByVal ws As Worksheet, _
                                               ByVal firstDataRow As Long, _
                                               ByVal lastRealRow As Long, _
                                               ByVal orderCol As Long, _
                                               ByVal itemCol As Long, _
                                               ByRef printKind As String, _
                                               ByRef destinationMode As String, _
                                               ByRef selectedGlassKeys As String, _
                                               ByRef selectedAction As String, _
                                               ByRef selectedCopies As Long) As Boolean
    Dim frm As frmPrintOptions

    Set frm = New frmPrintOptions
    frm.LoadOptions ws, firstDataRow, lastRealRow, orderCol, itemCol
    frm.Show vbModal

    If frm.WasCancelled Then GoTo SafeExit

    printKind = frm.SelectedPrintKind
    destinationMode = frm.SelectedDestinationMode
    selectedGlassKeys = frm.selectedGlassKeys
    selectedAction = frm.selectedAction
    selectedCopies = frm.selectedCopies

    PromptForPrintOptionsTemplate = _
        (Len(printKind) > 0 And Len(destinationMode) > 0 And Len(selectedGlassKeys) > 0 And Len(selectedAction) > 0)

SafeExit:
    On Error Resume Next
    Unload frm
    Set frm = Nothing
    On Error GoTo 0
End Function

'------------------------------------------------------------------------------
' Procedure: PromptForExportOptionsTemplate
' Scope: Private Function
'
' What it does:
'   Performs the workbook-specific step named PromptForExportOptionsTemplate
'   inside TemplateImporter.
'
' Why it exists:
'   The master workbook uses this module to turn a raw delivery list into the
'   operational sheets used by scanning, printing, exports, and intake
'   snapshots.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function PromptForExportOptionsTemplate(ByVal ws As Worksheet, _
                                                ByVal firstDataRow As Long, _
                                                ByVal lastRealRow As Long, _
                                                ByVal orderCol As Long, _
                                                ByVal itemCol As Long, _
                                                ByRef exportKind As String, _
                                                ByRef destinationMode As String, _
                                                ByRef selectedGlassKeys As String, _
                                                ByRef selectedAction As String) As Boolean
    Dim frm As frmExportOptions

    Set frm = New frmExportOptions
    frm.LoadOptions ws, firstDataRow, lastRealRow, orderCol, itemCol
    frm.Show vbModal

    If frm.WasCancelled Then GoTo SafeExit

    exportKind = frm.SelectedExportKind
    destinationMode = frm.SelectedDestinationMode
    selectedGlassKeys = frm.selectedGlassKeys
    selectedAction = frm.selectedAction

    PromptForExportOptionsTemplate = _
        (Len(exportKind) > 0 And Len(destinationMode) > 0 And Len(selectedGlassKeys) > 0 And Len(selectedAction) > 0)

SafeExit:
    On Error Resume Next
    Unload frm
    Set frm = Nothing
    On Error GoTo 0
End Function

'------------------------------------------------------------------------------
' Procedure: PromptForManualScanOptionsTemplate
' Scope: Private Function
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   PromptForManualScanOptionsTemplate.
'
' Why it exists:
'   Remakes need separate visual and print/export handling so replacement
'   glass is not confused with regular delivery-list work.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function PromptForManualScanOptionsTemplate(ByRef mode As String, _
                                                    ByRef ord As Long, _
                                                    ByRef itm As Long, _
                                                    ByRef qty As Long) As Boolean
    Dim frm As frmManualScanEntry

    Set frm = New frmManualScanEntry
    frm.LoadDefaults
    frm.Show vbModal

    If frm.WasCancelled Then GoTo SafeExit

    mode = frm.SelectedMode
    ord = frm.SelectedOrderNumber
    itm = frm.SelectedItemNumber
    qty = frm.SelectedQuantity

    PromptForManualScanOptionsTemplate = _
        (Len(mode) > 0 And ord > 0 And itm > 0 And qty > 0)

SafeExit:
    On Error Resume Next
    Unload frm
    Set frm = Nothing
    On Error GoTo 0
End Function

'------------------------------------------------------------------------------
' Procedure: ForceRow3HeightAll
' Scope: Public Sub
'
' What it does:
'   Classifies, copies, formats, finds, or updates delivery-list rows for
'   ForceRow3HeightAll.
'
' Why it exists:
'   The imported delivery list contains special row types and destinations;
'   this helper keeps those rows classified and formatted correctly after
'   imports/updates.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Sub ForceRow3HeightAll()
    On Error Resume Next

    ForceRow3HeightTemplate ThisWorkbook.Worksheets("Delivery List")
    ForceRow3HeightTemplate ThisWorkbook.Worksheets("Staging - Airport Rd")
    ForceRow3HeightTemplate ThisWorkbook.Worksheets("Outbound - Airport Rd")

    If Not GetReceiveSheet() Is Nothing Then
        ForceRow3HeightTemplate GetReceiveSheet()
    End If

    If SheetExistsTemplate(GREENVILLE_RECV_SHEET_NAME) Then
        ForceRow3HeightTemplate ThisWorkbook.Worksheets(GREENVILLE_RECV_SHEET_NAME)
    End If

    If SheetExistsTemplate(CPU_SHEET_NAME) Then
        ForceRow3HeightTemplate ThisWorkbook.Worksheets(CPU_SHEET_NAME)
    End If

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: FinalRefreshAfterDeliveryListUpdate
' Scope: Private Sub
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   FinalRefreshAfterDeliveryListUpdate.
'
' Why it exists:
'   Delivery timing, queue timestamps, and scan timestamps drive status
'   messages such as Early, On-Time, Late, Processing, and Done.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub FinalRefreshAfterDeliveryListUpdate(ByVal dataWs As Worksheet)
    If dataWs Is Nothing Then Exit Sub

    On Error Resume Next
    dataWs.Unprotect Password:=""
    On Error GoTo 0

    'Make sure main sheet scan layout/summaries are current
    ScannerValidation.EnsureScanLayout dataWs
    CreateOrUpdateTopSummaryPanels dataWs
    dataWs.Calculate

    'Refresh all operational/scanner sheets from the final updated state
    ThisWorkbook.RefreshAllOperationalSheets dataWs

    'Rebuild any buttons / row heights that need to be restored
    ForceRow3HeightAll
    CreateOrRefreshActionButtons
End Sub


