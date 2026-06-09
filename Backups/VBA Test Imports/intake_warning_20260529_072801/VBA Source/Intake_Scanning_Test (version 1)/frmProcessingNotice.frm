Attribute VB_Name = "frmProcessingNotice"
Attribute VB_Base = "0{56E86998-8621-44C0-87DC-C5B1EAF19C58}{697D72F9-3B3E-4564-8952-1C1CA4E87B09}"
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
