Attribute VB_Name = "Sheet6"
Attribute VB_Base = "0{00020820-0000-0000-C000-000000000046}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = True
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = True
Option Explicit

Private Sub Worksheet_BeforeDoubleClick(ByVal Target As Range, Cancel As Boolean)
    If StrComp(Me.Name, "Bay Map", vbTextCompare) <> 0 Then Exit Sub
    If ITIM_HandleMapDoubleClick(Target) Then Cancel = True
End Sub

