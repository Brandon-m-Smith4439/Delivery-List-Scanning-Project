Attribute VB_Name = "frmProcessingNotice"
Attribute VB_Base = "0{4190BB66-21F7-4E2E-A5B4-DF481C2CA6A4}{489C6415-38CB-4E05-86D3-79D24D7F0DB2}"
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
