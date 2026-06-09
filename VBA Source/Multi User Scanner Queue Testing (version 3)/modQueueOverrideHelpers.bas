Attribute VB_Name = "modQueueOverrideHelpers"
Option Explicit

Public Const QUEUE_RECV_OVERRIDE_FLAG As String = "__OVERRIDE_RECV_OUTBOUND__"
Public Const QUEUE_RECV_OVERRIDE_AVAILABLE_FLAG As String = "OVERRIDE_AVAILABLE|"

Public Const QUEUE_SEND_OVERRIDE_FLAG As String = "__OVERRIDE_SEND_STAGING__"
Public Const QUEUE_SEND_OVERRIDE_AVAILABLE_FLAG As String = "SEND_OVERRIDE_AVAILABLE|"

Public Function IsReceiveOverrideRequestComment(ByVal requestComment As String) As Boolean
    IsReceiveOverrideRequestComment = _
        (InStr(1, UCase$(CStr(requestComment)), UCase$(QUEUE_RECV_OVERRIDE_FLAG), vbTextCompare) > 0)
End Function

Public Function StripReceiveOverrideFlag(ByVal requestComment As String) As String
    Dim s As String

    s = CStr(requestComment)

    s = Replace$(s, QUEUE_RECV_OVERRIDE_FLAG, vbNullString, 1, -1, vbTextCompare)
    s = Replace$(s, "||", "|")

    Do While Left$(Trim$(s), 1) = "|"
        s = Mid$(Trim$(s), 2)
    Loop

    StripReceiveOverrideFlag = Trim$(s)
End Function

'------------------------------------------------------------------------------
' Procedure: IsSendOverrideRequestComment
'
' Returns True when a queue request was intentionally approved to send outbound
' even though staging quantity is behind.
'------------------------------------------------------------------------------
Public Function IsSendOverrideRequestComment(ByVal requestComment As String) As Boolean
    IsSendOverrideRequestComment = _
        (InStr(1, UCase$(CStr(requestComment)), UCase$(QUEUE_SEND_OVERRIDE_FLAG), vbTextCompare) > 0)
End Function

'------------------------------------------------------------------------------
' Procedure: StripSendOverrideFlag
'
' Removes the outbound/staging override marker from request comments before
' operator-facing comments are written to the sheet.
'------------------------------------------------------------------------------
Public Function StripSendOverrideFlag(ByVal requestComment As String) As String
    Dim s As String

    s = CStr(requestComment)
    s = Replace$(s, QUEUE_SEND_OVERRIDE_FLAG, vbNullString, 1, -1, vbTextCompare)

    Do While InStr(1, s, "||", vbBinaryCompare) > 0
        s = Replace$(s, "||", "|")
    Loop

    Do While Left$(Trim$(s), 1) = "|"
        s = Mid$(Trim$(s), 2)
    Loop

    StripSendOverrideFlag = Trim$(s)
End Function

'------------------------------------------------------------------------------
' Procedure: StripQueueOverrideFlags
'
' Removes all hidden queue override markers from a request comment.
'------------------------------------------------------------------------------
Public Function StripQueueOverrideFlags(ByVal requestComment As String) As String
    Dim s As String

    s = CStr(requestComment)
    s = StripReceiveOverrideFlag(s)
    s = StripSendOverrideFlag(s)

    Do While InStr(1, s, "||", vbBinaryCompare) > 0
        s = Replace$(s, "||", "|")
    Loop

    Do While Left$(Trim$(s), 1) = "|"
        s = Mid$(Trim$(s), 2)
    Loop

    StripQueueOverrideFlags = Trim$(s)
End Function

Public Function QueueResultAllowsReceiveOverride(ByVal resultMessage As String) As Boolean
    Dim s As String

    s = UCase$(CStr(resultMessage))

    QueueResultAllowsReceiveOverride = _
        (InStr(1, s, UCase$(QUEUE_RECV_OVERRIDE_AVAILABLE_FLAG), vbTextCompare) > 0) Or _
        (InStr(1, s, "NO OUTBOUND", vbTextCompare) > 0) Or _
        (InStr(1, s, "EXCEED OUTBOUND", vbTextCompare) > 0) Or _
        (InStr(1, s, "EXCEED AIRPORT", vbTextCompare) > 0)
End Function

'------------------------------------------------------------------------------
' Procedure: QueueResultAllowsSendOverride
'
' Returns True when the master rejected an outbound scan only because staging
' quantity is behind and the intake station should offer an override button.
'------------------------------------------------------------------------------
Public Function QueueResultAllowsSendOverride(ByVal resultMessage As String) As Boolean
    Dim s As String

    s = UCase$(CStr(resultMessage))

    QueueResultAllowsSendOverride = _
        (InStr(1, s, UCase$(QUEUE_SEND_OVERRIDE_AVAILABLE_FLAG), vbTextCompare) > 0) Or _
        (InStr(1, s, "OUTBOUND WOULD EXCEED STAGED", vbTextCompare) > 0) Or _
        (InStr(1, s, "NOT BEEN FULLY STAGED", vbTextCompare) > 0) Or _
        (InStr(1, s, "STAGING MISMATCH", vbTextCompare) > 0)
End Function

Public Function CompactQueueResultMessage(ByVal resultMessage As String) As String
    Dim s As String
    Dim p As Long

    s = Trim$(CStr(resultMessage))

    s = Replace$(s, QUEUE_RECV_OVERRIDE_AVAILABLE_FLAG, vbNullString, 1, -1, vbTextCompare)
    s = Replace$(s, QUEUE_SEND_OVERRIDE_AVAILABLE_FLAG, vbNullString, 1, -1, vbTextCompare)
    s = Replace$(s, "[MASTER FINAL]", vbNullString, 1, -1, vbTextCompare)
    s = Replace$(s, "This was sent back to the intake form for review.", vbNullString, 1, -1, vbTextCompare)
    s = Replace$(s, "This applies to all inbound locations, including Indian Trail, Greenville, and Customer Pickup.", vbNullString, 1, -1, vbTextCompare)
    s = Replace$(s, "This requires review on the intake form.", vbNullString, 1, -1, vbTextCompare)

    s = Replace$(s, vbCrLf & vbCrLf, vbCrLf)
    s = Replace$(s, vbCrLf & vbCrLf, vbCrLf)
    s = Trim$(s)

    If InStr(1, s, "Processor step failed", vbTextCompare) > 0 Then
        p = InStr(1, s, "Error ", vbTextCompare)
        If p > 0 Then s = Mid$(s, p)
    End If

    If Len(s) > 220 Then
        s = Left$(s, 217) & "..."
    End If

    CompactQueueResultMessage = s
End Function

