Attribute VB_Name = "frmProcessingNotice"
Attribute VB_Base = "0{F595E249-1C37-4B72-BECF-DA0D0AE8715A}{F616950D-D39F-482D-981A-45BA41D48922}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = False
Private Sub UserForm_QueryClose(Cancel As Integer, CloseMode As Integer)
    On Error Resume Next
    mProcessingNoticeVisible = False
End Sub
