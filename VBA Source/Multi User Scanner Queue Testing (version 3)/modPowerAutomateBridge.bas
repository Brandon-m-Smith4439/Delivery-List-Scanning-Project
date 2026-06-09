Attribute VB_Name = "modPowerAutomateBridge"
Option Explicit

'==============================================================================
' Module: modPowerAutomateBridge
' Workbook: Multi User Scanner Queue Testing.xlsm / Master Delivery List
'
' What this module does:
'   Central HTTP/JSON bridge between VBA and the Power Automate flows that
'   read/write SharePoint lists.
'
' Why this module exists:
'   Keeping all flow URLs, payload builders, retry handling, and lightweight
'   JSON parsing in one module prevents every workflow module from duplicating
'   HTTP logic.
'
' Commenting standard used in this rewrite:
'   Procedure comments explain both what the code does and why that
'   behavior matters in the scanning / SharePoint / Power Automate workflow.
'   The code logic and public signatures are intentionally kept stable; this
'   pass is primarily a readability, maintainability, and safety pass.
'==============================================================================



'=========================================================
' modPowerAutomateBridge
' Power Automate bridge for SharePoint queue/list system
'=========================================================

Public Const PA_URL_QUEUE_GET_PENDING As String = "https://default2506d8b9503e40968f98d094e76b67.a5.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/db0f1a1583664e9580f89d86401e3cfb/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=1OVM6knogffPDCgvXND0WNxZwTgsLid3pG4DGkpQq_s"
Public Const PA_URL_QUEUE_ADD_REQUEST As String = "https://default2506d8b9503e40968f98d094e76b67.a5.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/464b9c0262714ceabb55b300589dfeec/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=KiT_JW6oSSQOY4NdMsBoTgHdY5xVbL2GOFcxLxWc97w"
Public Const PA_URL_QUEUE_UPDATE_STATUS As String = "https://default2506d8b9503e40968f98d094e76b67.a5.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/f337565833d94891b550be7bd3a57319/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=EhCFUi0WvemJvWxN2qDXDLlK4ugnFGaTdZxe2ol57QY"
Public Const PA_URL_ACTIVE_UPSERT_HEARTBEAT As String = "https://default2506d8b9503e40968f98d094e76b67.a5.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/f3e34b2948124caab80998b7a0cdbbf4/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=TchKWrHzb63_9WFH-AUReu93L595kj_p3OXkymEt_Hg"
Public Const PA_URL_ACTIVE_CHECK_DUPLICATE As String = "https://default2506d8b9503e40968f98d094e76b67.a5.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/5814a5d03bd64ded888b705f605f9f8b/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=vBgRIlFlIe9nrHK9lx4k9PhRx5F5DgV_tR4ybzyCXWw"
Public Const PA_URL_QUEUE_GET_REQUEST_STATUS As String = "https://default2506d8b9503e40968f98d094e76b67.a5.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/f3476b6ae3814627a78cae8a242f622a/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=weaYiPhbbFCoQVbGTfiaUNKbDDkXCe8F9YT9D3dFJRk"
Public Const PA_URL_SNAPSHOT_UPSERT As String = "https://default2506d8b9503e40968f98d094e76b67.a5.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/b395792e27194d4a8300330d9607d7a8/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=NVk5BjWYTjvFTY3VcnfNvAeWdXZbIkkMk8YgSvhAOTQ"
Public Const PA_URL_SNAPSHOT_GET As String = "https://default2506d8b9503e40968f98d094e76b67.a5.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/fa089dd1a80b474085a4af7f32dc7cac/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=ZkD5YruHtrcppJcRBt0DNm61ytBplT_SrmKS4vlEGzs"
Public Const PA_URL_INDIAN_TRAIL_BAY_ASSIGN_OR_GET As String = "https://default2506d8b9503e40968f98d094e76b67.a5.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/2d21ac5fcba1458a83a306223b33c712/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=U2sPcRkqxxiT1yZaCfudNKT_Hl-nOF7oZBA0HxsEdtc"

Private Const PA_HTTP_TIMEOUT_SECONDS As Long = 30

'------------------------------------------------------------------------------
' Procedure: PA_IndianTrailBayAssignOrGet
' Scope: Public Function
'
' What it does:
'   Wraps one Power Automate/SharePoint operation and converts between VBA
'   values and flow JSON for PA_IndianTrailBayAssignOrGet.
'
' Why it exists:
'   Centralizing flow calls keeps SharePoint communication consistent and
'   makes URL/payload changes easier to manage.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function PA_IndianTrailBayAssignOrGet(ByVal deliveryListKey As String, _
                                             ByVal orderNumber As Long, _
                                             ByVal normalizedOrderNumber As String, _
                                             ByVal itemNumber As Long, _
                                             ByVal glassHeader As String, _
                                             ByVal glassCategory As String, _
                                             ByVal bayCategory As String, _
                                             ByVal scanStage As String, _
                                             ByVal targetSheet As String, _
                                             ByVal stationName As String, _
                                             ByVal sourceWorkbook As String, _
                                             Optional ByVal barcodeText As String = vbNullString, _
                                             Optional ByVal notesText As String = vbNullString) As Object
    Dim payload As String
    Dim responseText As String
    Dim d As Object

    deliveryListKey = Trim$(CStr(deliveryListKey))
    normalizedOrderNumber = Trim$(CStr(normalizedOrderNumber))
    glassHeader = Trim$(CStr(glassHeader))
    glassCategory = Trim$(CStr(glassCategory))
    bayCategory = Trim$(CStr(bayCategory))
    scanStage = UCase$(Trim$(CStr(scanStage)))
    targetSheet = Trim$(CStr(targetSheet))
    stationName = Trim$(CStr(stationName))
    sourceWorkbook = Trim$(CStr(sourceWorkbook))
    barcodeText = UCase$(Trim$(CStr(barcodeText)))
    notesText = Trim$(CStr(notesText))

    Set d = CreateObject("Scripting.Dictionary")

    If Len(PA_URL_INDIAN_TRAIL_BAY_ASSIGN_OR_GET) = 0 _
       Or InStr(1, PA_URL_INDIAN_TRAIL_BAY_ASSIGN_OR_GET, "PASTE_YOUR", vbTextCompare) > 0 Then
        d("ok") = False
        d("resultCode") = "FLOW_URL_MISSING"
        d("message") = "Indian Trail bay assignment flow URL has not been pasted into modPowerAutomateBridge."
        Set PA_IndianTrailBayAssignOrGet = d
        Exit Function
    End If

    If Len(deliveryListKey) = 0 Then deliveryListKey = "DL_UNKNOWN"
    If Len(normalizedOrderNumber) = 0 And orderNumber > 0 Then normalizedOrderNumber = CStr(orderNumber)
    If Len(scanStage) = 0 Then scanStage = "UNKNOWN"

    payload = "{" & _
          """deliveryListKey"":" & JsonStringOrEmpty(deliveryListKey) & "," & _
          """orderNumber"":" & CStr(orderNumber) & "," & _
          """normalizedOrderNumber"":" & JsonStringOrEmpty(normalizedOrderNumber) & "," & _
          """itemNumber"":" & CStr(itemNumber) & "," & _
          """glassHeader"":" & JsonStringOrEmpty(glassHeader) & "," & _
          """glassCategory"":" & JsonStringOrEmpty(glassCategory) & "," & _
          """bayCategory"":" & JsonStringOrEmpty(bayCategory) & "," & _
          """scanStage"":" & JsonStringOrEmpty(scanStage) & "," & _
          """targetSheet"":" & JsonStringOrEmpty(targetSheet) & "," & _
          """stationName"":" & JsonStringOrEmpty(stationName) & "," & _
          """sourceWorkbook"":" & JsonStringOrEmpty(sourceWorkbook) & "," & _
          """barcode"":" & JsonStringOrEmpty(barcodeText) & "," & _
          """notes"":" & JsonStringOrEmpty(notesText) & _
          "}"

    Call PA_PostJson(PA_URL_INDIAN_TRAIL_BAY_ASSIGN_OR_GET, payload, responseText)

    d("ok") = JsonGetBoolean(responseText, "ok")
    d("resultCode") = JsonGetString(responseText, "resultCode")
    d("message") = JsonGetString(responseText, "message")
    d("bayKey") = JsonGetString(responseText, "bayKey")
    d("bayDisplayName") = JsonGetString(responseText, "bayDisplayName")
    d("assignmentStatus") = JsonGetString(responseText, "assignmentStatus")
    d("wasExistingAssignment") = JsonGetBoolean(responseText, "wasExistingAssignment")
    d("assignmentId") = CLng(JsonGetNumber(responseText, "assignmentId"))

    Set PA_IndianTrailBayAssignOrGet = d
End Function

'------------------------------------------------------------------------------
' Procedure: PA_DictText
' Scope: Public Function
'
' What it does:
'   Wraps one Power Automate/SharePoint operation and converts between VBA
'   values and flow JSON for PA_DictText.
'
' Why it exists:
'   Centralizing flow calls keeps SharePoint communication consistent and
'   makes URL/payload changes easier to manage.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function PA_DictText(ByVal d As Object, ByVal keyText As String, Optional ByVal defaultText As String = vbNullString) As String
    On Error Resume Next
    If Not d Is Nothing Then
        If d.Exists(keyText) Then
            If Not IsNull(d(keyText)) Then
                PA_DictText = CStr(d(keyText))
                Exit Function
            End If
        End If
    End If
    On Error GoTo 0
    PA_DictText = defaultText
End Function

'------------------------------------------------------------------------------
' Procedure: PA_ParseIsoDate
' Scope: Public Function
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for PA_ParseIsoDate.
'
' Why it exists:
'   Power Automate/SharePoint timestamps can arrive in UTC; converting them
'   prevents misleading processed/updated times in Excel.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function PA_ParseIsoDate(ByVal rawText As String) As Date
    Dim s As String
    Dim parsedDate As Date
    Dim hasUtcMarker As Boolean

    s = Trim$(rawText)
    If Len(s) = 0 Then Exit Function

    hasUtcMarker = (Right$(UCase$(s), 1) = "Z")

    s = Replace$(s, "T", " ")

    If Right$(UCase$(s), 1) = "Z" Then
        s = Left$(s, Len(s) - 1)
    End If

    If InStr(1, s, ".", vbTextCompare) > 0 Then
        s = Split(s, ".")(0)
    End If

    'Strip timezone offset if Power Automate returns one like:
    '2026-05-13 14:22:00-04:00
    If Len(s) >= 25 Then
        If Mid$(s, 20, 1) = "+" Or Mid$(s, 20, 1) = "-" Then
            s = Left$(s, 19)
        End If
    End If

    On Error Resume Next
    parsedDate = CDate(s)
    On Error GoTo 0

    If parsedDate <= 0 Then Exit Function

    If hasUtcMarker Then
        PA_ParseIsoDate = PA_UtcToLocalDate(parsedDate)
    Else
        PA_ParseIsoDate = parsedDate
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: PA_UtcToLocalDate
' Scope: Private Function
'
' What it does:
'   Parses, calculates, formats, or compares dates/times for
'   PA_UtcToLocalDate.
'
' Why it exists:
'   Power Automate/SharePoint timestamps can arrive in UTC; converting them
'   prevents misleading processed/updated times in Excel.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function PA_UtcToLocalDate(ByVal utcDate As Date) As Date
    PA_UtcToLocalDate = DateAdd("n", -PA_WindowsTimeZoneBiasMinutes(), utcDate)
End Function

'------------------------------------------------------------------------------
' Procedure: PA_WindowsTimeZoneBiasMinutes
' Scope: Private Function
'
' What it does:
'   Controls the active sheet/window view, freeze panes, navigation, or
'   selected cell for PA_WindowsTimeZoneBiasMinutes.
'
' Why it exists:
'   Power Automate/SharePoint timestamps can arrive in UTC; converting them
'   prevents misleading processed/updated times in Excel.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function PA_WindowsTimeZoneBiasMinutes() As Long
    Static hasCachedBias As Boolean
    Static cachedBias As Long

    Dim wmi As Object
    Dim zones As Object
    Dim zone As Object

    If hasCachedBias Then
        PA_WindowsTimeZoneBiasMinutes = cachedBias
        Exit Function
    End If

    On Error GoTo Fallback

    Set wmi = GetObject("winmgmts:\\.\root\cimv2")
    Set zones = wmi.ExecQuery("SELECT Bias FROM Win32_TimeZone")

    For Each zone In zones
        cachedBias = CLng(zone.Bias)
        hasCachedBias = True
        PA_WindowsTimeZoneBiasMinutes = cachedBias
        Exit Function
    Next zone

Fallback:
    hasCachedBias = True
    PA_WindowsTimeZoneBiasMinutes = cachedBias
End Function

'------------------------------------------------------------------------------
' Procedure: PA_PostJson
' Scope: Private Function
'
' What it does:
'   Sends a JSON POST request to a Power Automate HTTP trigger and returns the
'   response text.
'
' Why it exists:
'   All SharePoint list actions flow through Power Automate, so this shared
'   sender keeps timeout, retry, and error behavior consistent.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function PA_PostJson(ByVal urlText As String, ByVal bodyText As String, ByRef responseText As String) As Boolean
    Const MAX_ATTEMPTS As Long = 4
    Const WAIT_SECONDS_FIRST As Long = 2

    Dim http As Object
    Dim attemptNum As Long
    Dim waitSeconds As Long
    Dim statusCode As Long
    Dim statusText As String
    Dim lastErrorText As String

    responseText = vbNullString
    waitSeconds = WAIT_SECONDS_FIRST

    For attemptNum = 1 To MAX_ATTEMPTS
        On Error GoTo HttpFail

        Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")

        'Timeouts are milliseconds:
        'resolve, connect, send, receive
        http.setTimeouts 10000, 10000, 30000, 60000

        http.Open "POST", urlText, False
        http.setRequestHeader "Content-Type", "application/json"
        http.send bodyText

        statusCode = CLng(http.status)
        statusText = CStr(http.statusText)
        responseText = CStr(http.responseText)

        If statusCode >= 200 And statusCode < 300 Then
            PA_PostJson = True
            Exit Function
        End If

        lastErrorText = "HTTP " & statusCode & " - " & statusText & vbCrLf & vbCrLf & responseText

        If Not PA_ShouldRetryHttpStatus(statusCode) Then
            Exit For
        End If

        If attemptNum < MAX_ATTEMPTS Then
            PA_WaitSeconds waitSeconds
            waitSeconds = waitSeconds * 2
        End If
    Next attemptNum

    Err.Raise vbObjectError + 7100, , _
        "Power Automate request failed after " & MAX_ATTEMPTS & " attempt(s)." & vbCrLf & vbCrLf & _
        lastErrorText

    Exit Function

HttpFail:
    lastErrorText = "HTTP call failed on attempt " & attemptNum & "." & vbCrLf & vbCrLf & _
                    "Error " & Err.Number & ": " & Err.Description

    Err.Clear
    On Error GoTo 0

    If attemptNum < MAX_ATTEMPTS Then
        PA_WaitSeconds waitSeconds
        waitSeconds = waitSeconds * 2
        Resume Next
    End If

    Err.Raise vbObjectError + 7100, , _
        "Power Automate request failed after " & MAX_ATTEMPTS & " attempt(s)." & vbCrLf & vbCrLf & _
        lastErrorText
End Function

'------------------------------------------------------------------------------
' Procedure: PA_ShouldRetryHttpStatus
' Scope: Private Function
'
' What it does:
'   Retries a fragile operation and records the final success/failure state
'   for PA_ShouldRetryHttpStatus.
'
' Why it exists:
'   SharePoint and Power Automate calls can temporarily fail; retrying avoids
'   losing scans because of one short network or service hiccup.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function PA_ShouldRetryHttpStatus(ByVal statusCode As Long) As Boolean
    Select Case statusCode
        Case 408, 429, 500, 502, 503, 504
            PA_ShouldRetryHttpStatus = True
    End Select
End Function

'------------------------------------------------------------------------------
' Procedure: PA_WaitSeconds
' Scope: Private Sub
'
' What it does:
'   Wraps one Power Automate/SharePoint operation and converts between VBA
'   values and flow JSON for PA_WaitSeconds.
'
' Why it exists:
'   Centralizing flow calls keeps SharePoint communication consistent and
'   makes URL/payload changes easier to manage.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Sub PA_WaitSeconds(ByVal secondsToWait As Long)
    Dim untilTime As Date

    If secondsToWait < 1 Then secondsToWait = 1

    untilTime = DateAdd("s", secondsToWait, Now)

    Do While Now < untilTime
        DoEvents
    Loop
End Sub

'------------------------------------------------------------------------------
' Procedure: JsonEscape
' Scope: Private Function
'
' What it does:
'   Parses, builds, or safely transforms JSON text used by the Power Automate
'   bridge (JsonEscape).
'
' Why it exists:
'   The project avoids external JSON references, so these helpers provide
'   lightweight parsing that works inside standard Excel VBA.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function JsonEscape(ByVal s As String) As String
    s = Replace$(s, "\", "\\")
    s = Replace$(s, """", "\""")
    s = Replace$(s, "/", "\/")
    s = Replace$(s, vbCrLf, "\n")
    s = Replace$(s, vbCr, "\n")
    s = Replace$(s, vbLf, "\n")
    s = Replace$(s, vbTab, "\t")
    JsonEscape = s
End Function

'------------------------------------------------------------------------------
' Procedure: JsonStringLiteral
' Scope: Private Function
'
' What it does:
'   Parses, builds, or safely transforms JSON text used by the Power Automate
'   bridge (JsonStringLiteral).
'
' Why it exists:
'   The project avoids external JSON references, so these helpers provide
'   lightweight parsing that works inside standard Excel VBA.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function JsonStringLiteral(ByVal s As String) As String
    JsonStringLiteral = """" & JsonEscape(s) & """"
End Function

Private Function JsonStringOrEmpty(ByVal s As String) As String
    JsonStringOrEmpty = JsonStringLiteral(Trim$(CStr(s)))
End Function

'------------------------------------------------------------------------------
' Procedure: JsonNullableString
' Scope: Private Function
'
' What it does:
'   Parses, builds, or safely transforms JSON text used by the Power Automate
'   bridge (JsonNullableString).
'
' Why it exists:
'   The project avoids external JSON references, so these helpers provide
'   lightweight parsing that works inside standard Excel VBA.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function JsonNullableString(ByVal s As String) As String
    If Len(s) = 0 Then
        JsonNullableString = "null"
    Else
        JsonNullableString = JsonStringLiteral(s)
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: JsonNullableLong
' Scope: Private Function
'
' What it does:
'   Parses, builds, or safely transforms JSON text used by the Power Automate
'   bridge (JsonNullableLong).
'
' Why it exists:
'   The project avoids external JSON references, so these helpers provide
'   lightweight parsing that works inside standard Excel VBA.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function JsonNullableLong(ByVal n As Long) As String
    If n <= 0 Then
        JsonNullableLong = "null"
    Else
        JsonNullableLong = CStr(n)
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: JsonSkipWs
' Scope: Private Function
'
' What it does:
'   Parses, builds, or safely transforms JSON text used by the Power Automate
'   bridge (JsonSkipWs).
'
' Why it exists:
'   The project avoids external JSON references, so these helpers provide
'   lightweight parsing that works inside standard Excel VBA.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function JsonSkipWs(ByVal s As String, ByVal pos As Long) As Long
    Do While pos <= Len(s)
        Select Case Mid$(s, pos, 1)
            Case " ", vbTab, vbCr, vbLf
                pos = pos + 1
            Case Else
                Exit Do
        End Select
    Loop
    JsonSkipWs = pos
End Function

'------------------------------------------------------------------------------
' Procedure: JsonValueTextForKey
' Scope: Private Function
'
' What it does:
'   Parses, builds, or safely transforms JSON text used by the Power Automate
'   bridge (JsonValueTextForKey).
'
' Why it exists:
'   The project avoids external JSON references, so these helpers provide
'   lightweight parsing that works inside standard Excel VBA.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function JsonValueTextForKey(ByVal jsonText As String, ByVal keyText As String) As String
    Dim findText As String
    Dim p As Long
    Dim c As String
    Dim i As Long
    Dim startPos As Long
    Dim depth As Long
    Dim inString As Boolean
    Dim escaped As Boolean

    findText = """" & keyText & """"
    p = InStr(1, jsonText, findText, vbTextCompare)
    If p = 0 Then Exit Function

    p = InStr(p + Len(findText), jsonText, ":")
    If p = 0 Then Exit Function

    p = JsonSkipWs(jsonText, p + 1)
    If p > Len(jsonText) Then Exit Function

    c = Mid$(jsonText, p, 1)

    If c = """" Then
        inString = True
        escaped = False

        For i = p + 1 To Len(jsonText)
            c = Mid$(jsonText, i, 1)

            If escaped Then
                escaped = False
            ElseIf c = "\" Then
                escaped = True
            ElseIf c = """" Then
                JsonValueTextForKey = Mid$(jsonText, p, i - p + 1)
                Exit Function
            End If
        Next i

    ElseIf c = "{" Or c = "[" Then
        startPos = p
        depth = 0
        inString = False
        escaped = False

        For i = p To Len(jsonText)
            c = Mid$(jsonText, i, 1)

            If inString Then
                If escaped Then
                    escaped = False
                ElseIf c = "\" Then
                    escaped = True
                ElseIf c = """" Then
                    inString = False
                End If
            Else
                If c = """" Then
                    inString = True
                ElseIf c = "{" Or c = "[" Then
                    depth = depth + 1
                ElseIf c = "}" Or c = "]" Then
                    depth = depth - 1
                    If depth = 0 Then
                        JsonValueTextForKey = Mid$(jsonText, startPos, i - startPos + 1)
                        Exit Function
                    End If
                End If
            End If
        Next i

    Else
        startPos = p
        For i = p To Len(jsonText)
            c = Mid$(jsonText, i, 1)
            If c = "," Or c = "}" Or c = "]" Then
                JsonValueTextForKey = Trim$(Mid$(jsonText, startPos, i - startPos))
                Exit Function
            End If
        Next i
        JsonValueTextForKey = Trim$(Mid$(jsonText, startPos))
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: JsonDecodeString
' Scope: Private Function
'
' What it does:
'   Parses, builds, or safely transforms JSON text used by the Power Automate
'   bridge (JsonDecodeString).
'
' Why it exists:
'   The project avoids external JSON references, so these helpers provide
'   lightweight parsing that works inside standard Excel VBA.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function JsonDecodeString(ByVal rawText As String) As String
    Dim s As String

    s = rawText
    If Left$(s, 1) = """" And Right$(s, 1) = """" Then
        s = Mid$(s, 2, Len(s) - 2)
    End If

    s = Replace$(s, "\""", """")
    s = Replace$(s, "\\", "\")
    s = Replace$(s, "\/", "/")
    s = Replace$(s, "\r", vbCr)
    s = Replace$(s, "\n", vbLf)
    s = Replace$(s, "\t", vbTab)

    JsonDecodeString = s
End Function

'------------------------------------------------------------------------------
' Procedure: JsonGetString
' Scope: Private Function
'
' What it does:
'   Parses, builds, or safely transforms JSON text used by the Power Automate
'   bridge (JsonGetString).
'
' Why it exists:
'   The project avoids external JSON references, so these helpers provide
'   lightweight parsing that works inside standard Excel VBA.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function JsonGetString(ByVal jsonText As String, ByVal keyText As String) As String
    Dim rawText As String

    rawText = JsonValueTextForKey(jsonText, keyText)
    If Len(rawText) = 0 Then Exit Function
    If LCase$(rawText) = "null" Then Exit Function

    If Left$(rawText, 1) = """" Then
        JsonGetString = JsonDecodeString(rawText)
    Else
        JsonGetString = rawText
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: JsonGetNumber
' Scope: Private Function
'
' What it does:
'   Parses, builds, or safely transforms JSON text used by the Power Automate
'   bridge (JsonGetNumber).
'
' Why it exists:
'   The project avoids external JSON references, so these helpers provide
'   lightweight parsing that works inside standard Excel VBA.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function JsonGetNumber(ByVal jsonText As String, ByVal keyText As String) As Double
    Dim rawText As String
    rawText = JsonValueTextForKey(jsonText, keyText)
    If Len(rawText) = 0 Then Exit Function
    If LCase$(rawText) = "null" Then Exit Function
    JsonGetNumber = Val(rawText)
End Function

'------------------------------------------------------------------------------
' Procedure: JsonGetBoolean
' Scope: Private Function
'
' What it does:
'   Parses, builds, or safely transforms JSON text used by the Power Automate
'   bridge (JsonGetBoolean).
'
' Why it exists:
'   The project avoids external JSON references, so these helpers provide
'   lightweight parsing that works inside standard Excel VBA.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function JsonGetBoolean(ByVal jsonText As String, ByVal keyText As String) As Boolean
    Dim rawText As String
    rawText = LCase$(Trim$(JsonValueTextForKey(jsonText, keyText)))
    JsonGetBoolean = (rawText = "true")
End Function

'------------------------------------------------------------------------------
' Procedure: JsonSplitTopLevelObjects
' Scope: Private Function
'
' What it does:
'   Parses, builds, or safely transforms JSON text used by the Power Automate
'   bridge (JsonSplitTopLevelObjects).
'
' Why it exists:
'   The project avoids external JSON references, so these helpers provide
'   lightweight parsing that works inside standard Excel VBA.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function JsonSplitTopLevelObjects(ByVal arrayText As String) As Collection
    Dim out As New Collection
    Dim s As String
    Dim i As Long
    Dim c As String
    Dim depth As Long
    Dim startPos As Long
    Dim inString As Boolean
    Dim escaped As Boolean

    s = Trim$(arrayText)
    If Len(s) = 0 Then
        Set JsonSplitTopLevelObjects = out
        Exit Function
    End If

    If Left$(s, 1) = "[" And Right$(s, 1) = "]" Then
        s = Mid$(s, 2, Len(s) - 2)
    End If

    depth = 0
    startPos = 0
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
                Case "{"
                    If depth = 0 Then startPos = i
                    depth = depth + 1
                Case "}"
                    depth = depth - 1
                    If depth = 0 And startPos > 0 Then
                        out.Add Mid$(s, startPos, i - startPos + 1)
                        startPos = 0
                    End If
            End Select
        End If
    Next i

    Set JsonSplitTopLevelObjects = out
End Function

'------------------------------------------------------------------------------
' Procedure: PA_QueueAddRequest
' Scope: Public Function
'
' What it does:
'   Builds the JSON payload for a scan/manual request and submits it to the
'   QueueAddRequest flow.
'
' Why it exists:
'   Intake workbooks and queue-related helpers need one stable way to create
'   ScanQueue rows without directly editing SharePoint.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function PA_QueueAddRequest(ByVal deliveryListKey As String, _
                                   ByVal requestType As String, _
                                   ByVal modeText As String, _
                                   Optional ByVal barcodeText As String = vbNullString, _
                                   Optional ByVal orderNumber As Long = 0, _
                                   Optional ByVal itemNumber As Long = 0, _
                                   Optional ByVal quantity As Long = 0, _
                                   Optional ByVal targetSheet As String = vbNullString, _
                                   Optional ByVal stationName As String = vbNullString, _
                                   Optional ByVal requestComment As String = vbNullString) As Boolean
    Dim payload As String
    Dim responseText As String

    payload = "{" & _
              """deliveryListKey"":" & JsonStringLiteral(deliveryListKey) & "," & _
              """requestType"":" & JsonStringLiteral(UCase$(Trim$(requestType))) & "," & _
              """barcode"":" & JsonNullableString(UCase$(Trim$(barcodeText))) & "," & _
              """mode"":" & JsonStringLiteral(UCase$(Trim$(modeText))) & "," & _
              """orderNumber"":" & JsonNullableLong(orderNumber) & "," & _
              """itemNumber"":" & JsonNullableLong(itemNumber) & "," & _
              """quantity"":" & JsonNullableLong(quantity) & "," & _
              """targetSheet"":" & JsonNullableString(targetSheet) & "," & _
              """stationName"":" & JsonNullableString(stationName) & "," & _
              """requestComment"":" & JsonNullableString(requestComment) & _
              "}"

    Call PA_PostJson(PA_URL_QUEUE_ADD_REQUEST, payload, responseText)
    PA_QueueAddRequest = JsonGetBoolean(responseText, "ok")
End Function

'------------------------------------------------------------------------------
' Procedure: PA_QueueAddBarcodeRequest
' Scope: Public Function
'
' What it does:
'   Cleans, decodes, validates, writes, or displays barcode data for
'   PA_QueueAddBarcodeRequest.
'
' Why it exists:
'   The barcode is the link between the physical glass label and the
'   order/item row, so the project must parse and validate it consistently.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function PA_QueueAddBarcodeRequest(ByVal deliveryListKey As String, _
                                          ByVal modeText As String, _
                                          ByVal barcodeText As String, _
                                          ByVal targetSheet As String, _
                                          ByVal stationName As String, _
                                          Optional ByVal requestComment As String = vbNullString) As Boolean
    PA_QueueAddBarcodeRequest = PA_QueueAddRequest( _
                                deliveryListKey, _
                                "BARCODE", _
                                modeText, _
                                barcodeText, _
                                0, _
                                0, _
                                0, _
                                targetSheet, _
                                stationName, _
                                requestComment)
End Function

'------------------------------------------------------------------------------
' Procedure: PA_QueueGetPending
' Scope: Public Function
'
' What it does:
'   Requests pending ScanQueue items for the current delivery list from Power
'   Automate and converts each JSON object into a dictionary.
'
' Why it exists:
'   The master processor uses this to pull work from SharePoint without
'   needing a direct SharePoint VBA connection.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function PA_QueueGetPending(ByVal deliveryListKey As String, Optional ByVal maxRows As Long = 100) As Collection
    Dim payload As String
    Dim responseText As String
    Dim arrayText As String
    Dim objects As Collection
    Dim objText As Variant
    Dim itemJson As String
    Dim d As Object
    Dim out As New Collection

    payload = "{" & _
              """deliveryListKey"":" & JsonStringLiteral(deliveryListKey) & "," & _
              """maxRows"":" & CStr(maxRows) & _
              "}"

    Call PA_PostJson(PA_URL_QUEUE_GET_PENDING, payload, responseText)

    arrayText = JsonValueTextForKey(responseText, "items")
    Set objects = JsonSplitTopLevelObjects(arrayText)

    For Each objText In objects
        itemJson = CStr(objText)

        Set d = CreateObject("Scripting.Dictionary")

        d("id") = CLng(JsonGetNumberAny(itemJson, Array("id", "ID")))
d("requestId") = JsonGetStringAny(itemJson, Array("requestId", "Title", "RequestId"))
d("deliveryListKey") = JsonGetStringAny(itemJson, Array("deliveryListKey", "DeliveryListKey"))
d("requestType") = JsonGetStringAny(itemJson, Array("RequestType#Value", "RequestType.Value", "requestType", "RequestType"))

'Read order/item/qty BEFORE barcode fallback.
d("orderNumber") = CLng(JsonGetNumberAny(itemJson, Array("orderNumber", "OrderNumber")))
d("itemNumber") = CLng(JsonGetNumberAny(itemJson, Array("itemNumber", "ItemNumber")))
d("quantity") = CLng(JsonGetNumberAny(itemJson, Array("quantity", "Quantity")))

'Use the stored barcode if valid. If not, rebuild from order/item.
d("barcode") = QueueBarcodeOrFallback( _
                    JsonGetStringAny(itemJson, Array("barcode", "Barcode")), _
                    CLng(d("orderNumber")), _
                    CLng(d("itemNumber")))

d("mode") = JsonGetStringAny(itemJson, Array("Mode#Value", "Mode.Value", "mode", "Mode"))
d("targetSheet") = JsonGetStringAny(itemJson, Array("targetSheet", "TargetSheet"))
d("stationName") = JsonGetStringAny(itemJson, Array("stationName", "StationName"))
d("queuedAt") = JsonGetStringAny(itemJson, Array("queuedAt", "QueuedAt"))
d("status") = JsonGetStringAny(itemJson, Array("Status#Value", "Status.Value", "status", "Status"))
d("processedAt") = JsonGetStringAny(itemJson, Array("processedAt", "ProcessedAt"))
d("resultCode") = JsonGetStringAny(itemJson, Array("resultCode", "ResultCode"))
d("resultMessage") = JsonGetStringAny(itemJson, Array("resultMessage", "ResultMessage"))
d("requestComment") = JsonGetStringAny(itemJson, Array("requestComment", "RequestComment"))

        out.Add d
    Next objText

    Set PA_QueueGetPending = out
End Function

'------------------------------------------------------------------------------
' Procedure: NormalizeQueueBarcodeText
' Scope: Private Function
'
' What it does:
'   Detects, formats, prints, exports, or preserves remake-row state for
'   NormalizeQueueBarcodeText.
'
' Why it exists:
'   Remakes need separate visual and print/export handling so replacement
'   glass is not confused with regular delivery-list work.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function NormalizeQueueBarcodeText(ByVal barcodeText As String) As String
    Dim s As String
    Dim i As Long
    Dim ch As String
    Dim out As String

    s = Trim$(CStr(barcodeText))

    If Len(s) = 0 Then Exit Function
    If LCase$(s) = "null" Then Exit Function
    If s = "0" Then Exit Function

    s = Replace$(s, "*", vbNullString)
    s = Replace$(s, vbCr, vbNullString)
    s = Replace$(s, vbLf, vbNullString)
    s = Replace$(s, vbTab, vbNullString)
    s = Replace$(s, " ", vbNullString)

    For i = 1 To Len(s)
        ch = Mid$(s, i, 1)

        If ch Like "[0-9A-Za-z]" Then
            out = out & ch
        End If
    Next i

    NormalizeQueueBarcodeText = UCase$(out)
End Function

'------------------------------------------------------------------------------
' Procedure: IsQueueBarcodeValid
' Scope: Private Function
'
' What it does:
'   Cleans, decodes, validates, writes, or displays barcode data for
'   IsQueueBarcodeValid.
'
' Why it exists:
'   The barcode is the link between the physical glass label and the
'   order/item row, so the project must parse and validate it consistently.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function IsQueueBarcodeValid(ByVal barcodeText As String) As Boolean
    barcodeText = NormalizeQueueBarcodeText(barcodeText)

    IsQueueBarcodeValid = _
        (Len(barcodeText) = 16 And barcodeText Like "T200############")
End Function

'------------------------------------------------------------------------------
' Procedure: BuildQueueBarcodeFromOrderItem
' Scope: Private Function
'
' What it does:
'   Cleans, decodes, validates, writes, or displays barcode data for
'   BuildQueueBarcodeFromOrderItem.
'
' Why it exists:
'   The barcode is the link between the physical glass label and the
'   order/item row, so the project must parse and validate it consistently.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function BuildQueueBarcodeFromOrderItem(ByVal orderNumber As Long, ByVal itemNumber As Long) As String
    If orderNumber <= 0 Then Exit Function
    If itemNumber <= 0 Then Exit Function

    BuildQueueBarcodeFromOrderItem = _
        "T200" & Format$(orderNumber, "000000") & Format$(itemNumber, "000") & "000"
End Function

'------------------------------------------------------------------------------
' Procedure: QueueBarcodeOrFallback
' Scope: Private Function
'
' What it does:
'   Cleans, decodes, validates, writes, or displays barcode data for
'   QueueBarcodeOrFallback.
'
' Why it exists:
'   The barcode is the link between the physical glass label and the
'   order/item row, so the project must parse and validate it consistently.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function QueueBarcodeOrFallback(ByVal barcodeText As String, _
                                        ByVal orderNumber As Long, _
                                        ByVal itemNumber As Long) As String
    Dim cleanBarcode As String
    Dim rebuiltBarcode As String

    cleanBarcode = NormalizeQueueBarcodeText(barcodeText)

    If IsQueueBarcodeValid(cleanBarcode) Then
        QueueBarcodeOrFallback = cleanBarcode
        Exit Function
    End If

    rebuiltBarcode = BuildQueueBarcodeFromOrderItem(orderNumber, itemNumber)

    If IsQueueBarcodeValid(rebuiltBarcode) Then
        QueueBarcodeOrFallback = rebuiltBarcode
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: JsonGetStringAny
' Scope: Private Function
'
' What it does:
'   Parses, builds, or safely transforms JSON text used by the Power Automate
'   bridge (JsonGetStringAny).
'
' Why it exists:
'   The project avoids external JSON references, so these helpers provide
'   lightweight parsing that works inside standard Excel VBA.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function JsonGetStringAny(ByVal jsonText As String, ByVal keyNames As Variant) As String
    Dim keyName As Variant
    Dim valueText As String

    For Each keyName In keyNames
        valueText = JsonGetStringFlexible(jsonText, CStr(keyName))

        If Len(valueText) > 0 Then
            JsonGetStringAny = valueText
            Exit Function
        End If
    Next keyName
End Function

'------------------------------------------------------------------------------
' Procedure: JsonGetNumberAny
' Scope: Private Function
'
' What it does:
'   Parses, builds, or safely transforms JSON text used by the Power Automate
'   bridge (JsonGetNumberAny).
'
' Why it exists:
'   The project avoids external JSON references, so these helpers provide
'   lightweight parsing that works inside standard Excel VBA.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function JsonGetNumberAny(ByVal jsonText As String, ByVal keyNames As Variant) As Double
    Dim keyName As Variant
    Dim valueNum As Double
    Dim rawText As String

    For Each keyName In keyNames
        rawText = JsonValueTextForFlexibleKey(jsonText, CStr(keyName))
        If Len(rawText) > 0 And LCase$(Trim$(rawText)) <> "null" Then
            valueNum = Val(rawText)
            If valueNum <> 0 Then
                JsonGetNumberAny = valueNum
                Exit Function
            End If
        End If
    Next keyName
End Function

'------------------------------------------------------------------------------
' Procedure: JsonGetStringFlexible
' Scope: Private Function
'
' What it does:
'   Parses, builds, or safely transforms JSON text used by the Power Automate
'   bridge (JsonGetStringFlexible).
'
' Why it exists:
'   The project avoids external JSON references, so these helpers provide
'   lightweight parsing that works inside standard Excel VBA.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function JsonGetStringFlexible(ByVal jsonText As String, ByVal keyText As String) As String
    Dim rawText As String
    Dim valueText As String

    rawText = JsonValueTextForFlexibleKey(jsonText, keyText)
    rawText = Trim$(rawText)

    If Len(rawText) = 0 Then Exit Function
    If LCase$(rawText) = "null" Then Exit Function

    'SharePoint choice fields sometimes come back as:
    '{"@odata.type":"...","Id":3,"Value":"SNAPSHOT"}'
    'When that happens, return the Value property.
    If Left$(rawText, 1) = "{" Then
        valueText = JsonValueTextForKey(rawText, "Value")

        If Len(Trim$(valueText)) > 0 Then
            valueText = Trim$(valueText)

            If Left$(valueText, 1) = """" Then
                JsonGetStringFlexible = JsonDecodeString(valueText)
            Else
                JsonGetStringFlexible = valueText
            End If

            Exit Function
        End If
    End If

    If Left$(rawText, 1) = """" Then
        JsonGetStringFlexible = JsonDecodeString(rawText)
    Else
        JsonGetStringFlexible = rawText
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: JsonValueTextForFlexibleKey
' Scope: Private Function
'
' What it does:
'   Parses, builds, or safely transforms JSON text used by the Power Automate
'   bridge (JsonValueTextForFlexibleKey).
'
' Why it exists:
'   The project avoids external JSON references, so these helpers provide
'   lightweight parsing that works inside standard Excel VBA.
'
' Workflow note:
'   Private helper: only this module should call it, which keeps the larger
'   workflow easier to reason about.
'------------------------------------------------------------------------------
Private Function JsonValueTextForFlexibleKey(ByVal jsonText As String, ByVal keyText As String) As String
    Dim parts As Variant
    Dim objectText As String
    Dim partIndex As Long

    If InStr(1, keyText, "#", vbBinaryCompare) > 0 Then
        parts = Split(keyText, "#")
    ElseIf InStr(1, keyText, ".", vbBinaryCompare) > 0 Then
        parts = Split(keyText, ".")
    Else
        JsonValueTextForFlexibleKey = JsonValueTextForKey(jsonText, keyText)
        Exit Function
    End If

    objectText = jsonText

    For partIndex = LBound(parts) To UBound(parts)
        objectText = JsonValueTextForKey(objectText, CStr(parts(partIndex)))
        If Len(objectText) = 0 Then Exit Function
    Next partIndex

    JsonValueTextForFlexibleKey = objectText
End Function

'------------------------------------------------------------------------------
' Procedure: PA_QueueUpdateStatus
' Scope: Public Function
'
' What it does:
'   Sends updated queue status/result information back to SharePoint for one
'   ScanQueue item.
'
' Why it exists:
'   Intake stations depend on these final statuses to know whether a locally
'   buffered scan was accepted, rejected, or needs override review.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function PA_QueueUpdateStatus(ByVal itemId As Long, _
                                     ByVal statusText As String, _
                                     Optional ByVal resultCode As String = vbNullString, _
                                     Optional ByVal resultMessage As String = vbNullString) As Boolean
    Dim payload As String
    Dim responseText As String

    payload = "{" & _
              """itemId"":" & CStr(itemId) & "," & _
              """status"":" & JsonStringLiteral(statusText) & "," & _
              """resultCode"":" & JsonNullableString(resultCode) & "," & _
              """resultMessage"":" & JsonNullableString(resultMessage) & _
              "}"

    Call PA_PostJson(PA_URL_QUEUE_UPDATE_STATUS, payload, responseText)
    PA_QueueUpdateStatus = JsonGetBoolean(responseText, "ok")
End Function

'------------------------------------------------------------------------------
' Procedure: PA_ActiveUpsertHeartbeat
' Scope: Public Function
'
' What it does:
'   Wraps one Power Automate/SharePoint operation and converts between VBA
'   values and flow JSON for PA_ActiveUpsertHeartbeat.
'
' Why it exists:
'   Centralizing flow calls keeps SharePoint communication consistent and
'   makes URL/payload changes easier to manage.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function PA_ActiveUpsertHeartbeat(ByVal deliveryListKey As String, _
                                         ByVal displayName As String, _
                                         ByVal listDateValue As Date, _
                                         ByVal processorStatus As String, _
                                         ByVal processorWorkbook As String, _
                                         ByVal sessionId As String, _
                                         ByVal machineName As String, _
                                         Optional ByVal revisionToken As String = vbNullString, _
                                         Optional ByVal revisionUpdatedAt As String = vbNullString) As Boolean
    Dim payload As String
    Dim responseText As String
    Dim listDateText As String

    If listDateValue > 0 Then
        listDateText = Format$(listDateValue, "yyyy-mm-dd")
    Else
        listDateText = vbNullString
    End If

    payload = "{" & _
              """deliveryListKey"":" & JsonStringLiteral(deliveryListKey) & "," & _
              """displayName"":" & JsonNullableString(displayName) & "," & _
              """listDate"":" & JsonNullableString(listDateText) & "," & _
              """processorStatus"":" & JsonStringLiteral(processorStatus) & "," & _
              """processorWorkbook"":" & JsonNullableString(processorWorkbook) & "," & _
              """sessionId"":" & JsonNullableString(sessionId) & "," & _
              """machineName"":" & JsonNullableString(machineName) & "," & _
              """revisionToken"":" & JsonNullableString(revisionToken) & "," & _
              """revisionUpdatedAt"":" & JsonNullableString(revisionUpdatedAt) & _
              "}"

    Call PA_PostJson(PA_URL_ACTIVE_UPSERT_HEARTBEAT, payload, responseText)
    PA_ActiveUpsertHeartbeat = JsonGetBoolean(responseText, "ok")
End Function

'------------------------------------------------------------------------------
' Procedure: PA_ActiveCheckDuplicate
' Scope: Public Function
'
' What it does:
'   Wraps one Power Automate/SharePoint operation and converts between VBA
'   values and flow JSON for PA_ActiveCheckDuplicate.
'
' Why it exists:
'   Centralizing flow calls keeps SharePoint communication consistent and
'   makes URL/payload changes easier to manage.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function PA_ActiveCheckDuplicate(ByVal deliveryListKey As String, ByVal sessionId As String) As Collection
    Dim payload As String
    Dim responseText As String
    Dim arrayText As String
    Dim objects As Collection
    Dim objText As Variant
    Dim d As Object
    Dim out As New Collection

    payload = "{" & _
              """deliveryListKey"":" & JsonStringLiteral(deliveryListKey) & "," & _
              """sessionId"":" & JsonStringLiteral(sessionId) & _
              "}"

    Call PA_PostJson(PA_URL_ACTIVE_CHECK_DUPLICATE, payload, responseText)

    arrayText = JsonValueTextForKey(responseText, "duplicates")
    Set objects = JsonSplitTopLevelObjects(arrayText)

    For Each objText In objects
        Set d = CreateObject("Scripting.Dictionary")
        d("id") = CLng(JsonGetNumber(CStr(objText), "id"))
        d("deliveryListKey") = JsonGetString(CStr(objText), "deliveryListKey")
        d("displayName") = JsonGetString(CStr(objText), "displayName")
        d("listDate") = JsonGetString(CStr(objText), "listDate")
        d("processorStatus") = JsonGetString(CStr(objText), "processorStatus")
        d("lastHeartbeat") = JsonGetString(CStr(objText), "lastHeartbeat")
        d("processorWorkbook") = JsonGetString(CStr(objText), "processorWorkbook")
        d("sessionId") = JsonGetString(CStr(objText), "sessionId")
        d("machineName") = JsonGetString(CStr(objText), "machineName")
        out.Add d
    Next objText

    Set PA_ActiveCheckDuplicate = out
End Function

'------------------------------------------------------------------------------
' Procedure: PA_QueueGetRequestStatus
' Scope: Public Function
'
' What it does:
'   Wraps one Power Automate/SharePoint operation and converts between VBA
'   values and flow JSON for PA_QueueGetRequestStatus.
'
' Why it exists:
'   Centralizing flow calls keeps SharePoint communication consistent and
'   makes URL/payload changes easier to manage.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function PA_QueueGetRequestStatus(ByVal requestId As String) As Object
    Dim payload As String
    Dim responseText As String
    Dim itemText As String
    Dim sourceText As String
    Dim d As Object
    Dim okRaw As String
    Dim foundRaw As String

    On Error GoTo FailLookup

    requestId = Trim$(CStr(requestId))
    If Len(requestId) = 0 Then Exit Function

    payload = "{" & _
              """requestId"":" & JsonStringLiteral(requestId) & _
              "}"

    Call PA_PostJson(PA_URL_QUEUE_GET_REQUEST_STATUS, payload, responseText)

    If Len(Trim$(responseText)) = 0 Then Exit Function

    okRaw = Trim$(JsonValueTextForKey(responseText, "ok"))
    If Len(okRaw) > 0 Then
        If Not JsonGetBoolean(responseText, "ok") Then Exit Function
    End If

    foundRaw = Trim$(JsonValueTextForKey(responseText, "found"))
    If Len(foundRaw) > 0 Then
        If Not JsonGetBoolean(responseText, "found") Then Exit Function
    End If

    itemText = Trim$(JsonValueTextForKey(responseText, "item"))

    If Len(itemText) > 0 And LCase$(itemText) <> "null" Then
        sourceText = itemText
    ElseIf Len(JsonGetString(responseText, "requestId")) > 0 Then
        sourceText = responseText
    Else
        Exit Function
    End If

    Set d = CreateObject("Scripting.Dictionary")

    d("id") = CLng(JsonGetNumber(sourceText, "id"))
    d("requestId") = JsonGetString(sourceText, "requestId")
    d("deliveryListKey") = JsonGetString(sourceText, "deliveryListKey")
    d("requestType") = JsonGetString(sourceText, "requestType")
    d("barcode") = JsonGetString(sourceText, "barcode")
    d("mode") = JsonGetString(sourceText, "mode")
    d("orderNumber") = CLng(JsonGetNumber(sourceText, "orderNumber"))
    d("itemNumber") = CLng(JsonGetNumber(sourceText, "itemNumber"))
    d("quantity") = CLng(JsonGetNumber(sourceText, "quantity"))
    d("targetSheet") = JsonGetString(sourceText, "targetSheet")
    d("stationName") = JsonGetString(sourceText, "stationName")
    d("queuedAt") = JsonGetString(sourceText, "queuedAt")
    d("status") = JsonGetString(sourceText, "status")
    d("processedAt") = JsonGetString(sourceText, "processedAt")
    d("resultCode") = JsonGetString(sourceText, "resultCode")
    d("resultMessage") = JsonGetString(sourceText, "resultMessage")
    d("requestComment") = JsonGetString(sourceText, "requestComment")

    If Len(PA_DictText(d, "requestId")) = 0 Then
        d("requestId") = requestId
    End If

    Set PA_QueueGetRequestStatus = d
    Exit Function

FailLookup:
    Set PA_QueueGetRequestStatus = Nothing
End Function

'------------------------------------------------------------------------------
' Procedure: PA_SnapshotUpsert
' Scope: Public Function
'
' What it does:
'   Uploads or updates one DeliveryListSnapshots SharePoint item with the
'   latest snapshot JSON and revision data.
'
' Why it exists:
'   This is the handoff between the master workbook and all intake workbooks.
'
' Workflow note:
'   Public entry point: keep the name/signature stable because buttons,
'   events, forms, timers, or other modules may call it.
'------------------------------------------------------------------------------
Public Function PA_SnapshotUpsert(ByVal deliveryListKey As String, _
                                  ByVal stageKey As String, _
                                  ByVal stageProfile As String, _
                                  ByVal modeText As String, _
                                  ByVal stageSheetName As String, _
                                  ByVal revisionToken As String, _
                                  ByVal updatedAtText As String, _
                                  ByVal rowCount As Long, _
                                  ByVal snapshotJson As String) As Boolean
    Dim payload As String
    Dim responseText As String

    deliveryListKey = Trim$(CStr(deliveryListKey))
    stageKey = Trim$(CStr(stageKey))
    stageProfile = Trim$(CStr(stageProfile))
    modeText = Trim$(CStr(modeText))
    stageSheetName = Trim$(CStr(stageSheetName))
    revisionToken = Trim$(CStr(revisionToken))
    updatedAtText = Trim$(CStr(updatedAtText))

    If Len(deliveryListKey) = 0 Then Exit Function
    If Len(stageKey) = 0 Then Exit Function
    If Len(stageProfile) = 0 Then Exit Function
    If Len(modeText) = 0 Then Exit Function
    If Len(stageSheetName) = 0 Then Exit Function
    If Len(revisionToken) = 0 Then Exit Function
    If Len(snapshotJson) = 0 Then Exit Function

    payload = "{" & _
              """deliveryListKey"":" & JsonStringLiteral(deliveryListKey) & "," & _
              """stageKey"":" & JsonStringLiteral(stageKey) & "," & _
              """stageProfile"":" & JsonStringLiteral(stageProfile) & "," & _
              """mode"":" & JsonStringLiteral(UCase$(modeText)) & "," & _
              """stageSheetName"":" & JsonStringLiteral(stageSheetName) & "," & _
              """revisionToken"":" & JsonStringLiteral(revisionToken) & "," & _
              """updatedAt"":" & JsonStringLiteral(updatedAtText) & "," & _
              """rowCount"":" & CStr(rowCount) & "," & _
              """snapshotJson"":" & JsonStringLiteral(snapshotJson) & "," & _
              """isActive"":true" & _
              "}"

    Call PA_PostJson(PA_URL_SNAPSHOT_UPSERT, payload, responseText)

    PA_SnapshotUpsert = JsonGetBoolean(responseText, "ok")

    If Not PA_SnapshotUpsert Then
        Err.Raise vbObjectError + 7201, "PA_SnapshotUpsert", _
                  "SnapshotUpsert returned ok = false." & vbCrLf & vbCrLf & responseText
    End If
End Function


