Attribute VB_Name = "modPowerAutomateBridge"
Option Explicit

'==============================================================================
' Module: modPowerAutomateBridge
' Workbook: Intake_Scanning_Test.xlsm / Intake scanner workbook
'
' What this module does:
'   HTTP/JSON bridge between intake VBA and Power Automate flows for queue
'   requests, status checks, active delivery lists, and snapshot retrieval.
'
' Why this module exists:
'   Centralizing flow URLs, payload builders, JSON parsing, and date
'   conversion keeps all SharePoint/Power Automate communication consistent.
'
' Commenting standard used in this rewrite:
'   Comments explain both what each procedure/section does and why it
'   matters to the scanning, SharePoint, Power Automate, buffering, and
'   operator-safety workflow. The code behavior and public procedure names
'   are intentionally kept stable so existing buttons/forms/timers keep working.
'==============================================================================

#If VBA7 Then
    Private Declare PtrSafe Function GetTimeZoneInformation Lib "kernel32" ( _
        ByRef lpTimeZoneInformation As TIME_ZONE_INFORMATION) As Long
#Else
    Private Declare Function GetTimeZoneInformation Lib "kernel32" ( _
        ByRef lpTimeZoneInformation As TIME_ZONE_INFORMATION) As Long
#End If

Private Type SYSTEMTIME
    wYear As Integer
    wMonth As Integer
    wDayOfWeek As Integer
    wDay As Integer
    wHour As Integer
    wMinute As Integer
    wSecond As Integer
    wMilliseconds As Integer
End Type

Private Type TIME_ZONE_INFORMATION
    Bias As Long
    StandardName(0 To 31) As Integer
    StandardDate As SYSTEMTIME
    StandardBias As Long
    DaylightName(0 To 31) As Integer
    DaylightDate As SYSTEMTIME
    DaylightBias As Long
End Type
'=========================================================
' modPowerAutomateBridge
' Power Automate bridge for SharePoint queue/list system
'=========================================================

Public Const PA_URL_QUEUE_GET_PENDING As String = "https://default2506d8b9503e40968f98d094e76b67.a5.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/db0f1a1583664e9580f89d86401e3cfb/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=1OVM6knogffPDCgvXND0WNxZwTgsLid3pG4DGkpQq_s"
Public Const PA_URL_QUEUE_ADD_REQUEST As String = "https://default2506d8b9503e40968f98d094e76b67.a5.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/464b9c0262714ceabb55b300589dfeec/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=KiT_JW6oSSQOY4NdMsBoTgHdY5xVbL2GOFcxLxWc97w"
Public Const PA_URL_QUEUE_UPDATE_STATUS As String = "https://default2506d8b9503e40968f98d094e76b67.a5.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/f337565833d94891b550be7bd3a57319/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=EhCFUi0WvemJvWxN2qDXDLlK4ugnFGaTdZxe2ol57QY"
Public Const PA_URL_ACTIVE_UPSERT_HEARTBEAT As String = "https://default2506d8b9503e40968f98d094e76b67.a5.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/f3e34b2948124caab80998b7a0cdbbf4/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=TchKWrHzb63_9WFH-AUReu93L595kj_p3OXkymEt_Hg"
Public Const PA_URL_ACTIVE_CHECK_DUPLICATE As String = "https://default2506d8b9503e40968f98d094e76b67.a5.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/5814a5d03bd64ded888b705f605f9f8b/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=vBgRIlFlIe9nrHK9lx4k9PhRx5F5DgV_tR4ybzyCXWw"
Public Const PA_URL_ACTIVE_LISTS_GET_ONLINE As String = "https://default2506d8b9503e40968f98d094e76b67.a5.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/70c0224ebb1b4ccda2470823b25cf177/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=ThxEGAoP05pVYG_EBO7F5YOjB6T6Qj00PmqbqmwdW-E"
Public Const PA_URL_QUEUE_GET_REQUEST_STATUS As String = "https://default2506d8b9503e40968f98d094e76b67.a5.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/f3476b6ae3814627a78cae8a242f622a/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=weaYiPhbbFCoQVbGTfiaUNKbDDkXCe8F9YT9D3dFJRk"
Public Const PA_URL_SNAPSHOT_GET As String = "https://default2506d8b9503e40968f98d094e76b67.a5.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/fa089dd1a80b474085a4af7f32dc7cac/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=ZkD5YruHtrcppJcRBt0DNm61ytBplT_SrmKS4vlEGzs"
Public Const PA_URL_INDIAN_TRAIL_BAY_ASSIGN_OR_GET As String = "https://default2506d8b9503e40968f98d094e76b67.a5.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/2d21ac5fcba1458a83a306223b33c712/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=U2sPcRkqxxiT1yZaCfudNKT_Hl-nOF7oZBA0HxsEdtc"

Private Const PA_HTTP_TIMEOUT_SECONDS As Long = 30
Private Const PA_DEBUG_MAX_ROWS As Long = 750
Private Const ACTIVE_LIST_HEARTBEAT_STALE_MINUTES As Long = 5

'------------------------------------------------------------------------------
' Procedure: PA_DictText
' Scope: Public Function
'
' What it does:
'   Wraps a Power Automate/SharePoint operation or timestamp conversion for
'   PA_DictText.
'
' Why it exists:
'   Centralized bridge procedures prevent every scanner workflow from manually
'   building HTTP calls and parsing responses.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
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
'   Parses SharePoint/Power Automate ISO timestamp text and converts UTC
'   values to local time when needed.
'
' Why it exists:
'   Operators need readable local queue times; raw UTC timestamps are
'   confusing on the panel/audit sheet.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function PA_ParseIsoDate(ByVal rawText As String) As Date
    Dim s As String
    Dim hasUtcMarker As Boolean
    Dim p As Long
    Dim parsedDate As Date

    s = Trim$(rawText)
    If Len(s) = 0 Then Exit Function

    hasUtcMarker = (InStr(1, s, "Z", vbTextCompare) > 0)

    s = Replace$(s, "T", " ")
    s = Replace$(s, "Z", "")

    If InStr(1, s, ".", vbTextCompare) > 0 Then
        s = Split(s, ".")(0)
    End If

    'Remove timezone suffixes like +00:00 or -04:00 if Power Automate ever returns them.
    p = InStrRev(s, "+")
    If p > 10 Then s = Trim$(Left$(s, p - 1))

    p = InStrRev(s, "-")
    If p > 10 Then s = Trim$(Left$(s, p - 1))

    On Error Resume Next
    parsedDate = CDate(s)
    On Error GoTo 0

    If parsedDate <= 0 Then Exit Function

    If hasUtcMarker Then
        PA_ParseIsoDate = DateAdd("n", LocalUtcOffsetMinutes(), parsedDate)
    Else
        PA_ParseIsoDate = parsedDate
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: LocalUtcOffsetMinutes
' Scope: Private Function
'
' What it does:
'   Wraps a Power Automate/SharePoint operation or timestamp conversion for
'   LocalUtcOffsetMinutes.
'
' Why it exists:
'   Centralized bridge procedures prevent every scanner workflow from manually
'   building HTTP calls and parsing responses.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function LocalUtcOffsetMinutes() As Long
    Dim tzi As TIME_ZONE_INFORMATION
    Dim rc As Long
    Dim totalBias As Long

    On Error GoTo Fallback

    rc = GetTimeZoneInformation(tzi)

    totalBias = tzi.Bias

    Select Case rc
        Case 1 'Standard time
            totalBias = totalBias + tzi.StandardBias

        Case 2 'Daylight time
            totalBias = totalBias + tzi.DaylightBias
    End Select

    'Windows bias is minutes to add to local time to get UTC.
    'For UTC -> local, use the negative.
    LocalUtcOffsetMinutes = -totalBias
    Exit Function

Fallback:
    'Fallback for Eastern Daylight Time. This prevents the obvious 4-hour SharePoint UTC issue.
    LocalUtcOffsetMinutes = -240
End Function

'------------------------------------------------------------------------------
' Procedure: PA_PostJson
' Scope: Private Function
'
' What it does:
'   Sends a synchronous JSON POST request to a Power Automate HTTP trigger and
'   returns the response body.
'
' Why it exists:
'   All SharePoint interaction in the intake workbook goes through Power
'   Automate, so one sender keeps HTTP behavior and errors consistent.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function PA_PostJson(ByVal urlText As String, ByVal bodyText As String, ByRef responseText As String) As Boolean
    Dim http As Object
    Dim startedAt As Single

    Set http = CreateObject("MSXML2.XMLHTTP.6.0")
    startedAt = Timer

    http.Open "POST", urlText, False
    http.setRequestHeader "Content-Type", "application/json"
    http.send bodyText

    responseText = CStr(http.responseText)

    If http.Status >= 200 And http.Status < 300 Then
        PA_PostJson = True
    Else
        Err.Raise vbObjectError + 7100, , _
            "HTTP " & http.Status & " - " & http.statusText & vbCrLf & vbCrLf & responseText
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: JsonEscape
' Scope: Private Function
'
' What it does:
'   Parses, decodes, builds, or extracts JSON text used by the Power Automate
'   bridge (JsonEscape).
'
' Why it exists:
'   The intake workbook avoids an external JSON library, so these helpers keep
'   JSON handling available in standard Excel VBA.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
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
'   Parses, decodes, builds, or extracts JSON text used by the Power Automate
'   bridge (JsonStringLiteral).
'
' Why it exists:
'   The intake workbook avoids an external JSON library, so these helpers keep
'   JSON handling available in standard Excel VBA.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function JsonStringLiteral(ByVal s As String) As String
    JsonStringLiteral = """" & JsonEscape(s) & """"
End Function

'------------------------------------------------------------------------------
' Procedure: JsonNullableString
' Scope: Private Function
'
' What it does:
'   Parses, decodes, builds, or extracts JSON text used by the Power Automate
'   bridge (JsonNullableString).
'
' Why it exists:
'   The intake workbook avoids an external JSON library, so these helpers keep
'   JSON handling available in standard Excel VBA.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function JsonNullableString(ByVal s As String) As String
    If Len(s) = 0 Then
        JsonNullableString = "null"
    Else
        JsonNullableString = JsonStringLiteral(s)
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: JsonStringOrEmpty
' Scope: Private Function
'
' What it does:
'   Parses, decodes, builds, or extracts JSON text used by the Power Automate
'   bridge (JsonStringOrEmpty).
'
' Why it exists:
'   The intake workbook avoids an external JSON library, so these helpers keep
'   JSON handling available in standard Excel VBA.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function JsonStringOrEmpty(ByVal s As String) As String
    JsonStringOrEmpty = JsonStringLiteral(s)
End Function

'------------------------------------------------------------------------------
' Procedure: JsonNullableLong
' Scope: Private Function
'
' What it does:
'   Parses, decodes, builds, or extracts JSON text used by the Power Automate
'   bridge (JsonNullableLong).
'
' Why it exists:
'   The intake workbook avoids an external JSON library, so these helpers keep
'   JSON handling available in standard Excel VBA.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
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
'   Parses, decodes, builds, or extracts JSON text used by the Power Automate
'   bridge (JsonSkipWs).
'
' Why it exists:
'   The intake workbook avoids an external JSON library, so these helpers keep
'   JSON handling available in standard Excel VBA.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
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
'   Parses, decodes, builds, or extracts JSON text used by the Power Automate
'   bridge (JsonValueTextForKey).
'
' Why it exists:
'   The intake workbook avoids an external JSON library, so these helpers keep
'   JSON handling available in standard Excel VBA.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
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
'   Parses, decodes, builds, or extracts JSON text used by the Power Automate
'   bridge (JsonDecodeString).
'
' Why it exists:
'   The intake workbook avoids an external JSON library, so these helpers keep
'   JSON handling available in standard Excel VBA.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
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
'   Parses, decodes, builds, or extracts JSON text used by the Power Automate
'   bridge (JsonGetString).
'
' Why it exists:
'   The intake workbook avoids an external JSON library, so these helpers keep
'   JSON handling available in standard Excel VBA.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
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
'   Parses, decodes, builds, or extracts JSON text used by the Power Automate
'   bridge (JsonGetNumber).
'
' Why it exists:
'   The intake workbook avoids an external JSON library, so these helpers keep
'   JSON handling available in standard Excel VBA.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
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
'   Parses, decodes, builds, or extracts JSON text used by the Power Automate
'   bridge (JsonGetBoolean).
'
' Why it exists:
'   The intake workbook avoids an external JSON library, so these helpers keep
'   JSON handling available in standard Excel VBA.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function JsonGetBoolean(ByVal jsonText As String, ByVal keyText As String) As Boolean
    Dim rawText As String
    rawText = LCase$(Trim$(JsonValueTextForKey(jsonText, keyText)))
    JsonGetBoolean = (rawText = "true")
End Function

Private Function JsonGetBooleanFlexible(ByVal jsonText As String, ByVal keyText As String) As Boolean
    Dim rawText As String
    Dim stringText As String

    rawText = LCase$(Trim$(JsonValueTextForKey(jsonText, keyText)))
    stringText = LCase$(Trim$(JsonGetString(jsonText, keyText)))

    JsonGetBooleanFlexible = _
        (rawText = "true") Or _
        (stringText = "true") Or _
        (stringText = "yes") Or _
        (stringText = "1")
End Function

'------------------------------------------------------------------------------
' Procedure: JsonSplitTopLevelObjects
' Scope: Private Function
'
' What it does:
'   Parses, decodes, builds, or extracts JSON text used by the Power Automate
'   bridge (JsonSplitTopLevelObjects).
'
' Why it exists:
'   The intake workbook avoids an external JSON library, so these helpers keep
'   JSON handling available in standard Excel VBA.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
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
'   Builds and sends the QueueAddRequest payload for barcode/manual/comment
'   work.
'
' Why it exists:
'   The intake workbook should not directly edit SharePoint; it asks Power
'   Automate to create the queue row.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function PA_QueueAddRequest(ByVal requestId As String, _
                                   ByVal deliveryListKey As String, _
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
              """requestId"":" & JsonStringLiteral(requestId) & "," & _
              """deliveryListKey"":" & JsonStringLiteral(deliveryListKey) & "," & _
              """requestType"":" & JsonStringLiteral(UCase$(Trim$(requestType))) & "," & _
              """barcode"":" & JsonStringOrEmpty(UCase$(Trim$(barcodeText))) & "," & _
              """mode"":" & JsonStringLiteral(UCase$(Trim$(modeText))) & "," & _
              """orderNumber"":" & CStr(orderNumber) & "," & _
              """itemNumber"":" & CStr(itemNumber) & "," & _
              """quantity"":" & CStr(quantity) & "," & _
              """targetSheet"":" & JsonStringOrEmpty(targetSheet) & "," & _
              """stationName"":" & JsonStringOrEmpty(stationName) & "," & _
              """requestComment"":" & JsonStringOrEmpty(requestComment) & _
              "}"

    Call PA_PostJson(PA_URL_QUEUE_ADD_REQUEST, payload, responseText)
    PA_QueueAddRequest = JsonGetBoolean(responseText, "ok")
End Function

'------------------------------------------------------------------------------
' Procedure: PA_QueueAddBarcodeRequest
' Scope: Public Function
'
' What it does:
'   Wraps a Power Automate/SharePoint operation or timestamp conversion for
'   PA_QueueAddBarcodeRequest.
'
' Why it exists:
'   Centralized bridge procedures prevent every scanner workflow from manually
'   building HTTP calls and parsing responses.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function PA_QueueAddBarcodeRequest(ByVal requestId As String, _
                                          ByVal deliveryListKey As String, _
                                          ByVal modeText As String, _
                                          ByVal barcodeText As String, _
                                          ByVal targetSheet As String, _
                                          ByVal stationName As String, _
                                          Optional ByVal requestComment As String = vbNullString) As Boolean
    PA_QueueAddBarcodeRequest = PA_QueueAddRequest( _
                                requestId, _
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
'   Wraps a Power Automate/SharePoint operation or timestamp conversion for
'   PA_QueueGetPending.
'
' Why it exists:
'   Centralized bridge procedures prevent every scanner workflow from manually
'   building HTTP calls and parsing responses.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function PA_QueueGetPending(ByVal deliveryListKey As String, Optional ByVal maxRows As Long = 100) As Collection
    Dim payload As String
    Dim responseText As String
    Dim arrayText As String
    Dim objects As Collection
    Dim objText As Variant
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
        Set d = CreateObject("Scripting.Dictionary")
        d("id") = CLng(JsonGetNumber(CStr(objText), "id"))
        d("requestId") = JsonGetString(CStr(objText), "requestId")
        d("deliveryListKey") = JsonGetString(CStr(objText), "deliveryListKey")
        d("requestType") = JsonGetString(CStr(objText), "requestType")
        d("barcode") = JsonGetString(CStr(objText), "barcode")
        d("mode") = JsonGetString(CStr(objText), "mode")
        d("orderNumber") = CLng(JsonGetNumber(CStr(objText), "orderNumber"))
        d("itemNumber") = CLng(JsonGetNumber(CStr(objText), "itemNumber"))
        d("quantity") = CLng(JsonGetNumber(CStr(objText), "quantity"))
        d("targetSheet") = JsonGetString(CStr(objText), "targetSheet")
        d("stationName") = JsonGetString(CStr(objText), "stationName")
        d("queuedAt") = JsonGetString(CStr(objText), "queuedAt")
        d("status") = JsonGetString(CStr(objText), "status")
        d("processedAt") = JsonGetString(CStr(objText), "processedAt")
        d("resultCode") = JsonGetString(CStr(objText), "resultCode")
        d("resultMessage") = JsonGetString(CStr(objText), "resultMessage")
        d("requestComment") = JsonGetString(CStr(objText), "requestComment")
        out.Add d
    Next objText

    Set PA_QueueGetPending = out
End Function

'------------------------------------------------------------------------------
' Procedure: PA_QueueUpdateStatus
' Scope: Public Function
'
' What it does:
'   Wraps a Power Automate/SharePoint operation or timestamp conversion for
'   PA_QueueUpdateStatus.
'
' Why it exists:
'   Centralized bridge procedures prevent every scanner workflow from manually
'   building HTTP calls and parsing responses.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function PA_QueueUpdateStatus(ByVal itemId As Long, _
                                     ByVal statusText As String, _
                                     Optional ByVal resultCode As String = vbNullString, _
                                     Optional ByVal resultMessage As String = vbNullString) As Boolean
    Dim payload As String
    Dim responseText As String
    Dim flowMessage As String

    payload = "{" & _
              """itemId"":" & CStr(itemId) & "," & _
              """status"":" & JsonStringLiteral(statusText) & "," & _
              """resultCode"":" & JsonStringOrEmpty(resultCode) & "," & _
              """resultMessage"":" & JsonStringOrEmpty(resultMessage) & _
              "}"

    Call PA_PostJson(PA_URL_QUEUE_UPDATE_STATUS, payload, responseText)

    PA_QueueUpdateStatus = JsonGetBoolean(responseText, "ok")
    If Not PA_QueueUpdateStatus Then
        flowMessage = JsonGetString(responseText, "message")
        If Len(flowMessage) = 0 Then flowMessage = responseText

        Err.Raise vbObjectError + 7101, , _
            "QueueUpdateStatus returned ok = false." & vbCrLf & vbCrLf & _
            "Status: " & statusText & vbCrLf & _
            "ResultCode: " & resultCode & vbCrLf & _
            "ResultMessage: " & resultMessage & vbCrLf & vbCrLf & _
            flowMessage
    End If
End Function

'------------------------------------------------------------------------------
' Procedure: PA_ActiveUpsertHeartbeat
' Scope: Public Function
'
' What it does:
'   Wraps a Power Automate/SharePoint operation or timestamp conversion for
'   PA_ActiveUpsertHeartbeat.
'
' Why it exists:
'   Centralized bridge procedures prevent every scanner workflow from manually
'   building HTTP calls and parsing responses.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
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
'   Wraps a Power Automate/SharePoint operation or timestamp conversion for
'   PA_ActiveCheckDuplicate.
'
' Why it exists:
'   Centralized bridge procedures prevent every scanner workflow from manually
'   building HTTP calls and parsing responses.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
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
        d("lastHeartbeat") = JsonGetString(CStr(objText), "lastHeartbeat")
        d("processorStatus") = ActiveDeliveryListStatusWithHeartbeat( _
            JsonGetString(CStr(objText), "processorStatus"), _
            CStr(d("lastHeartbeat")))
        d("processorWorkbook") = JsonGetString(CStr(objText), "processorWorkbook")
        d("sessionId") = JsonGetString(CStr(objText), "sessionId")
        d("machineName") = JsonGetString(CStr(objText), "machineName")
        out.Add d
    Next objText

    Set PA_ActiveCheckDuplicate = out
End Function

Private Function ActiveDeliveryListStatusWithHeartbeat(ByVal rawStatus As String, ByVal heartbeatText As String) As String
    Dim statusText As String
    Dim heartbeatAt As Date

    statusText = Trim$(rawStatus)
    If Len(statusText) = 0 Then statusText = "Not registered"

    Select Case UCase$(statusText)
        Case "ONLINE", "OPEN", "ACTIVE", "PAUSED"
            heartbeatAt = PA_ParseIsoDate(heartbeatText)

            If heartbeatAt <= 0 Then
                ActiveDeliveryListStatusWithHeartbeat = "Offline"
            ElseIf DateDiff("n", heartbeatAt, Now) >= ACTIVE_LIST_HEARTBEAT_STALE_MINUTES Then
                ActiveDeliveryListStatusWithHeartbeat = "Offline"
            Else
                ActiveDeliveryListStatusWithHeartbeat = statusText
            End If

        Case Else
            ActiveDeliveryListStatusWithHeartbeat = statusText
    End Select
End Function

'------------------------------------------------------------------------------
' Procedure: PA_ActiveDeliveryListsGetOnline
' Scope: Public Function
'
' What it does:
'   Gets online/paused delivery-list processor records for scanner settings
'   and revision checks.
'
' Why it exists:
'   Operators choose a live delivery list from this data instead of manually
'   browsing for the master workbook.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function PA_ActiveDeliveryListsGetOnline(Optional ByVal includePaused As Boolean = True) As Collection
    Dim payload As String
    Dim responseText As String
    Dim arrayText As String
    Dim objects As Collection
    Dim objText As Variant
    Dim d As Object
    Dim out As New Collection

    payload = "{" & _
              """includePaused"":" & LCase$(CStr(includePaused)) & _
              "}"

    Call PA_PostJson(PA_URL_ACTIVE_LISTS_GET_ONLINE, payload, responseText)

    arrayText = JsonValueTextForKey(responseText, "items")
    Set objects = JsonSplitTopLevelObjects(arrayText)

    For Each objText In objects
        Set d = CreateObject("Scripting.Dictionary")
        d("id") = CLng(JsonGetNumber(CStr(objText), "id"))
        d("deliveryListKey") = JsonGetString(CStr(objText), "deliveryListKey")
        d("displayName") = JsonGetString(CStr(objText), "displayName")
        d("listDate") = JsonGetString(CStr(objText), "listDate")
        d("lastHeartbeat") = JsonGetString(CStr(objText), "lastHeartbeat")
        d("processorStatus") = ActiveDeliveryListStatusWithHeartbeat( _
            JsonGetString(CStr(objText), "processorStatus"), _
            CStr(d("lastHeartbeat")))
        d("processorWorkbook") = JsonGetString(CStr(objText), "processorWorkbook")
        d("sessionId") = JsonGetString(CStr(objText), "sessionId")
        d("machineName") = JsonGetString(CStr(objText), "machineName")
        d("revisionToken") = JsonGetString(CStr(objText), "revisionToken")
        d("revisionUpdatedAt") = JsonGetString(CStr(objText), "revisionUpdatedAt")
        out.Add d
    Next objText

    Set PA_ActiveDeliveryListsGetOnline = out
End Function

'------------------------------------------------------------------------------
' Procedure: PA_FindActiveDeliveryListInfo
' Scope: Public Function
'
' What it does:
'   Finds the active delivery-list metadata matching a selected
'   deliveryListKey.
'
' Why it exists:
'   Scanner settings and revision checks need one current record for the
'   selected master/list.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function PA_FindActiveDeliveryListInfo(ByVal deliveryListKey As String, Optional ByVal includePaused As Boolean = True) As Object
    Dim items As Collection
    Dim item As Object

    Set items = PA_ActiveDeliveryListsGetOnline(includePaused)

    For Each item In items
        If StrComp(PA_DictText(item, "deliveryListKey"), deliveryListKey, vbTextCompare) = 0 Then
            Set PA_FindActiveDeliveryListInfo = item
            Exit Function
        End If
    Next item
End Function

'------------------------------------------------------------------------------
' Procedure: PA_QueueGetRequestStatus
' Scope: Public Function
'
' What it does:
'   Looks up one queue request by request ID and converts the response into a
'   dictionary for the intake UI.
'
' Why it exists:
'   The intake station uses this to learn the masterâ€™s final
'   Done/Error/override result for a buffered scan.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function PA_QueueGetRequestStatus(ByVal requestId As String) As Object
    Dim payload As String
    Dim responseText As String
    Dim itemText As String
    Dim sourceText As String
    Dim d As Object
    Dim okRaw As String
    Dim foundRaw As String
    Dim statusText As String
    Dim resultCode As String
    Dim resultMessage As String

    On Error GoTo FailLookup

    requestId = Trim$(CStr(requestId))
    If Len(requestId) = 0 Then Exit Function

    payload = "{" & _
              """requestId"":" & JsonStringLiteral(requestId) & _
              "}"

    Call PA_PostJson(PA_URL_QUEUE_GET_REQUEST_STATUS, payload, responseText)

    okRaw = Trim$(JsonValueTextForKey(responseText, "ok"))
    foundRaw = Trim$(JsonValueTextForKey(responseText, "found"))
    itemText = Trim$(JsonValueTextForKey(responseText, "item"))

    PA_LogQueueStatusLookup requestId, "POST_OK", payload, responseText, foundRaw, itemText, "", "", ""

    If Len(Trim$(responseText)) = 0 Then
        PA_LogQueueStatusLookup requestId, "EMPTY_RESPONSE", payload, responseText, foundRaw, itemText, "", "", ""
        Exit Function
    End If

    If Len(okRaw) > 0 Then
        If Not JsonGetBoolean(responseText, "ok") Then
            PA_LogQueueStatusLookup requestId, "OK_FALSE", payload, responseText, foundRaw, itemText, "", "", ""
            Exit Function
        End If
    End If

    If Len(foundRaw) > 0 Then
        If Not JsonGetBoolean(responseText, "found") Then
            PA_LogQueueStatusLookup requestId, "FOUND_FALSE", payload, responseText, foundRaw, itemText, "", "", ""
            Exit Function
        End If
    End If

    If Len(itemText) > 0 And LCase$(itemText) <> "null" Then
        sourceText = itemText
    ElseIf Len(JsonGetString(responseText, "requestId")) > 0 Then
        sourceText = responseText
    Else
        PA_LogQueueStatusLookup requestId, "NO_ITEM", payload, responseText, foundRaw, itemText, "", "", ""
        Exit Function
    End If

    Set d = CreateObject("Scripting.Dictionary")

    d("id") = CLng(JsonGetNumber(sourceText, "id"))
    d("requestId") = PA_FirstJsonString(sourceText, "requestId", "RequestId", "Title", "title")
    d("deliveryListKey") = PA_FirstJsonString(sourceText, "deliveryListKey", "DeliveryListKey")
    d("requestType") = PA_FirstJsonString(sourceText, "requestType", "RequestType")
    d("barcode") = PA_FirstJsonString(sourceText, "barcode", "Barcode")
    d("mode") = PA_FirstJsonString(sourceText, "mode", "Mode")
    d("orderNumber") = CLng(PA_FirstJsonNumber(sourceText, "orderNumber", "OrderNumber"))
    d("itemNumber") = CLng(PA_FirstJsonNumber(sourceText, "itemNumber", "ItemNumber"))
    d("quantity") = CLng(PA_FirstJsonNumber(sourceText, "quantity", "Quantity"))
    d("targetSheet") = PA_FirstJsonString(sourceText, "targetSheet", "TargetSheet")
    d("stationName") = PA_FirstJsonString(sourceText, "stationName", "StationName")
    d("queuedAt") = PA_FirstJsonString(sourceText, "queuedAt", "QueuedAt", "Created")
    d("status") = PA_FirstJsonString(sourceText, "status", "Status", "queueStatus", "QueueStatus")
    d("processedAt") = PA_FirstJsonString(sourceText, "processedAt", "ProcessedAt", "Modified")
    d("resultCode") = PA_FirstJsonString(sourceText, "resultCode", "ResultCode")
    d("resultMessage") = PA_FirstJsonString(sourceText, "resultMessage", "ResultMessage", "message", "Message")
    d("requestComment") = PA_FirstJsonString(sourceText, "requestComment", "RequestComment", "comment", "Comment")

    If Len(PA_DictText(d, "requestId")) = 0 Then
        d("requestId") = requestId
    End If

    statusText = PA_DictText(d, "status")
    resultCode = PA_DictText(d, "resultCode")
    resultMessage = PA_DictText(d, "resultMessage")

    PA_LogQueueStatusLookup requestId, "RETURN_ITEM", payload, responseText, foundRaw, itemText, statusText, resultCode, resultMessage

    Set PA_QueueGetRequestStatus = d
    Exit Function

FailLookup:
    PA_LogQueueStatusLookup requestId, "ERROR", payload, responseText, foundRaw, itemText, "", "", "Error " & Err.Number & ": " & Err.Description
    Set PA_QueueGetRequestStatus = Nothing
End Function

'------------------------------------------------------------------------------
' Procedure: PA_FirstJsonString
' Scope: Private Function
'
' What it does:
'   Wraps a Power Automate/SharePoint operation or timestamp conversion for
'   PA_FirstJsonString.
'
' Why it exists:
'   Centralized bridge procedures prevent every scanner workflow from manually
'   building HTTP calls and parsing responses.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function PA_FirstJsonString(ByVal jsonText As String, ParamArray keyNames() As Variant) As String
    Dim keyName As Variant
    Dim valueText As String

    For Each keyName In keyNames
        valueText = JsonGetString(jsonText, CStr(keyName))
        If Len(Trim$(valueText)) > 0 Then
            PA_FirstJsonString = valueText
            Exit Function
        End If
    Next keyName
End Function

'------------------------------------------------------------------------------
' Procedure: PA_FirstJsonNumber
' Scope: Private Function
'
' What it does:
'   Wraps a Power Automate/SharePoint operation or timestamp conversion for
'   PA_FirstJsonNumber.
'
' Why it exists:
'   Centralized bridge procedures prevent every scanner workflow from manually
'   building HTTP calls and parsing responses.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Function PA_FirstJsonNumber(ByVal jsonText As String, ParamArray keyNames() As Variant) As Double
    Dim keyName As Variant
    Dim valueNumber As Double

    For Each keyName In keyNames
        valueNumber = JsonGetNumber(jsonText, CStr(keyName))
        If valueNumber <> 0 Then
            PA_FirstJsonNumber = valueNumber
            Exit Function
        End If
    Next keyName
End Function

'------------------------------------------------------------------------------
' Procedure: PA_LogQueueStatusLookup
' Scope: Private Sub
'
' What it does:
'   Wraps a Power Automate/SharePoint operation or timestamp conversion for
'   PA_LogQueueStatusLookup.
'
' Why it exists:
'   Centralized bridge procedures prevent every scanner workflow from manually
'   building HTTP calls and parsing responses.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub PA_LogQueueStatusLookup(ByVal requestId As String, _
                                    ByVal stepText As String, _
                                    ByVal payloadText As String, _
                                    ByVal responseText As String, _
                                    ByVal foundRaw As String, _
                                    ByVal itemText As String, _
                                    ByVal statusText As String, _
                                    ByVal resultCode As String, _
                                    ByVal resultMessage As String)
    Dim ws As Worksheet
    Dim nextRow As Long

    On Error Resume Next

    Set ws = ThisWorkbook.Worksheets("__PA_Status_Debug")

    If ws Is Nothing Then
        Set ws = ThisWorkbook.Worksheets.Add(After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
        ws.Name = "__PA_Status_Debug"
        ws.Visible = xlSheetVisible

        ws.Range("A1:J1").Value = Array( _
            "CheckedAt", _
            "RequestId", _
            "Step", _
            "FoundRaw", _
            "Status", _
            "ResultCode", _
            "ResultMessage", _
            "Payload", _
            "ItemPreview", _
            "ResponsePreview")
        ws.Rows(1).Font.Bold = True
        ws.Columns("A:J").ColumnWidth = 18
        ws.Columns("G:J").ColumnWidth = 45
    End If

    nextRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row + 1

    ws.Cells(nextRow, 1).Value = Now
    ws.Cells(nextRow, 2).Value = requestId
    ws.Cells(nextRow, 3).Value = stepText
    ws.Cells(nextRow, 4).Value = foundRaw
    ws.Cells(nextRow, 5).Value = statusText
    ws.Cells(nextRow, 6).Value = resultCode
    ws.Cells(nextRow, 7).Value = resultMessage
    ws.Cells(nextRow, 8).Value = Left$(payloadText, 500)
    ws.Cells(nextRow, 9).Value = Left$(itemText, 1500)
    ws.Cells(nextRow, 10).Value = Left$(responseText, 1500)

    ws.Cells(nextRow, 1).NumberFormat = "m/d/yyyy h:mm:ss AM/PM"
    PA_TrimDebugSheetRows ws, PA_DEBUG_MAX_ROWS

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: PA_TrimDebugSheetRows
' Scope: Private Sub
'
' What it does:
'   Keeps generated Power Automate debug sheets from growing forever.
'
' Why it exists:
'   Scanner workbooks can poll queue/request status frequently. Without a row
'   cap, hidden/debug sheets eventually become large enough to slow ordinary
'   scanning and saving.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub PA_TrimDebugSheetRows(ByVal ws As Worksheet, ByVal maxDataRows As Long)
    Dim lastRow As Long
    Dim deleteThroughRow As Long

    If ws Is Nothing Then Exit Sub
    If maxDataRows < 1 Then Exit Sub

    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row
    If lastRow <= maxDataRows + 1 Then Exit Sub

    deleteThroughRow = lastRow - maxDataRows
    If deleteThroughRow < 2 Then Exit Sub

    ws.Rows("2:" & CStr(deleteThroughRow)).Delete
End Sub

'------------------------------------------------------------------------------
' Procedure: Test_QueueUpdateStatus_Done
' Scope: Public Sub
'
' What it does:
'   Handles local buffer, queue request, polling, or queue-status state for
'   Test_QueueUpdateStatus_Done.
'
' Why it exists:
'   Scans move through local buffer, SharePoint ScanQueue, master processing,
'   and final intake confirmation; this state must stay traceable.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Sub Test_QueueUpdateStatus_Done()
    Dim ok As Boolean

    On Error GoTo ErrHandler

    ok = PA_QueueUpdateStatus(2, "Done", "OK", "Manual scan complete.")
    MsgBox "Done update returned: " & CStr(ok), vbInformation, "Test"
    Exit Sub

ErrHandler:
    MsgBox "Done update failed:" & vbCrLf & vbCrLf & _
           "Error " & Err.Number & ": " & Err.Description, vbExclamation, "Test"
End Sub

'------------------------------------------------------------------------------
' Procedure: PA_SnapshotGet
' Scope: Public Function
'
' What it does:
'   Gets the published DeliveryListSnapshots item for one delivery list and
'   stage key.
'
' Why it exists:
'   This is how the intake workbook loads sheet data without opening the
'   master workbook.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function PA_SnapshotGet(ByVal deliveryListKey As String, ByVal stageKey As String) As Object
    Dim payload As String
    Dim responseText As String
    Dim d As Object
    Dim snapshotJsonText As String

    On Error GoTo FailGet

    deliveryListKey = Trim$(CStr(deliveryListKey))
    stageKey = Trim$(CStr(stageKey))

    If Len(deliveryListKey) = 0 Then Exit Function
    If Len(stageKey) = 0 Then Exit Function

    payload = "{" & _
              """deliveryListKey"":" & JsonStringLiteral(deliveryListKey) & "," & _
              """stageKey"":" & JsonStringLiteral(stageKey) & _
              "}"

    Call PA_PostJson(PA_URL_SNAPSHOT_GET, payload, responseText)

    PA_LogSnapshotGet deliveryListKey, stageKey, "POST_OK", payload, responseText

    If Len(Trim$(responseText)) = 0 Then Exit Function

    Set d = CreateObject("Scripting.Dictionary")

    d("ok") = JsonGetBoolean(responseText, "ok")
    d("found") = JsonGetBoolean(responseText, "found")

    d("snapshotKey") = PA_FirstJsonString(responseText, "snapshotKey", "SnapshotKey", "Title")
    d("id") = PA_FirstJsonString(responseText, "id", "ID")
    d("deliveryListKey") = PA_FirstJsonString(responseText, "deliveryListKey", "DeliveryListKey", "field_1")
    d("stageKey") = PA_FirstJsonString(responseText, "stageKey", "StageKey", "field_2")
    d("stageProfile") = PA_FirstJsonString(responseText, "stageProfile", "StageProfile", "field_3")
    d("mode") = PA_FirstJsonString(responseText, "mode", "Mode", "field_4")
    d("stageSheetName") = PA_FirstJsonString(responseText, "stageSheetName", "StageSheetName", "field_5")
    d("revisionToken") = PA_FirstJsonString(responseText, "revisionToken", "RevisionToken", "field_6")
    d("snapshotUpdatedAt") = PA_FirstJsonString(responseText, "snapshotUpdatedAt", "SnapshotUpdatedAt", "field_7")
    d("updatedAtText") = PA_FirstJsonString(responseText, "updatedAtText", "SnapshotUpdatedAt", "field_7")
    d("rowCount") = PA_FirstJsonString(responseText, "rowCount", "RowCount", "field_8")
    d("snapshotJson") = PA_FirstJsonString(responseText, "snapshotJson", "SnapshotJson", "field_9")
    d("message") = PA_FirstJsonString(responseText, "message", "Message")

    snapshotJsonText = CStr(d("snapshotJson"))

    If Len(snapshotJsonText) > 0 Then
        If Not CBool(d("found")) Then d("found") = True
        If Not CBool(d("ok")) Then d("ok") = True
    End If

    PA_LogSnapshotGet deliveryListKey, stageKey, "RETURN_DICT", payload, _
                      "ok=" & CStr(d("ok")) & _
                      " | found=" & CStr(d("found")) & _
                      " | snapshotKey=" & CStr(d("snapshotKey")) & _
                      " | rowCount=" & CStr(d("rowCount")) & _
                      " | snapshotJsonLen=" & CStr(Len(snapshotJsonText)) & _
                      " | message=" & CStr(d("message"))

    Set PA_SnapshotGet = d
    Exit Function

FailGet:
    PA_LogSnapshotGet deliveryListKey, stageKey, "ERROR", payload, _
                      "Error " & Err.Number & ": " & Err.Description & vbCrLf & responseText
    Set PA_SnapshotGet = Nothing
End Function

'------------------------------------------------------------------------------
' Procedure: PA_LogSnapshotGet
' Scope: Private Sub
'
' What it does:
'   Wraps a Power Automate/SharePoint operation or timestamp conversion for
'   PA_LogSnapshotGet.
'
' Why it exists:
'   Centralized bridge procedures prevent every scanner workflow from manually
'   building HTTP calls and parsing responses.
'
' Workflow note:
'   Private helper: this is intentionally scoped to this module so the larger
'   workflow has fewer public moving parts.
'------------------------------------------------------------------------------
Private Sub PA_LogSnapshotGet(ByVal deliveryListKey As String, _
                              ByVal stageKey As String, _
                              ByVal stepText As String, _
                              ByVal payloadText As String, _
                              ByVal responseText As String)
    Dim ws As Worksheet
    Dim nextRow As Long

    On Error Resume Next

    Set ws = ThisWorkbook.Worksheets("__PA_SnapshotGet_Debug")

    If ws Is Nothing Then
        Set ws = ThisWorkbook.Worksheets.Add(After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
        ws.Name = "__PA_SnapshotGet_Debug"
        ws.Visible = xlSheetVisible

        ws.Range("A1:F1").Value = Array( _
            "CheckedAt", _
            "DeliveryListKey", _
            "StageKey", _
            "Step", _
            "Payload", _
            "ResponsePreview")
        ws.Rows(1).Font.Bold = True
        ws.Columns("A:F").ColumnWidth = 24
        ws.Columns("F").ColumnWidth = 120
    End If

    nextRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row + 1

    ws.Cells(nextRow, 1).Value = Now
    ws.Cells(nextRow, 2).Value = deliveryListKey
    ws.Cells(nextRow, 3).Value = stageKey
    ws.Cells(nextRow, 4).Value = stepText
    ws.Cells(nextRow, 5).Value = Left$(payloadText, 1000)
    ws.Cells(nextRow, 6).Value = Left$(responseText, 5000)

    ws.Cells(nextRow, 1).NumberFormat = "m/d/yyyy h:mm:ss AM/PM"
    PA_TrimDebugSheetRows ws, PA_DEBUG_MAX_ROWS

    On Error GoTo 0
End Sub

'------------------------------------------------------------------------------
' Procedure: PA_JsonValueForKey
' Scope: Public Function
'
' What it does:
'   Wraps a Power Automate/SharePoint operation or timestamp conversion for
'   PA_JsonValueForKey.
'
' Why it exists:
'   Centralized bridge procedures prevent every scanner workflow from manually
'   building HTTP calls and parsing responses.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function PA_JsonValueForKey(ByVal jsonText As String, ByVal keyText As String) As String
    PA_JsonValueForKey = JsonValueTextForKey(jsonText, keyText)
End Function

'------------------------------------------------------------------------------
' Procedure: PA_JsonGetStringValue
' Scope: Public Function
'
' What it does:
'   Wraps a Power Automate/SharePoint operation or timestamp conversion for
'   PA_JsonGetStringValue.
'
' Why it exists:
'   Centralized bridge procedures prevent every scanner workflow from manually
'   building HTTP calls and parsing responses.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function PA_JsonGetStringValue(ByVal jsonText As String, ByVal keyText As String) As String
    PA_JsonGetStringValue = JsonGetString(jsonText, keyText)
End Function

'------------------------------------------------------------------------------
' Procedure: PA_JsonGetNumberValue
' Scope: Public Function
'
' What it does:
'   Wraps a Power Automate/SharePoint operation or timestamp conversion for
'   PA_JsonGetNumberValue.
'
' Why it exists:
'   Centralized bridge procedures prevent every scanner workflow from manually
'   building HTTP calls and parsing responses.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function PA_JsonGetNumberValue(ByVal jsonText As String, ByVal keyText As String) As Double
    PA_JsonGetNumberValue = JsonGetNumber(jsonText, keyText)
End Function

'------------------------------------------------------------------------------
' Procedure: PA_JsonSplitObjects
' Scope: Public Function
'
' What it does:
'   Wraps a Power Automate/SharePoint operation or timestamp conversion for
'   PA_JsonSplitObjects.
'
' Why it exists:
'   Centralized bridge procedures prevent every scanner workflow from manually
'   building HTTP calls and parsing responses.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function PA_JsonSplitObjects(ByVal arrayText As String) As Collection
    Set PA_JsonSplitObjects = JsonSplitTopLevelObjects(arrayText)
End Function

'------------------------------------------------------------------------------
' Procedure: PA_JsonDecodeLiteral
' Scope: Public Function
'
' What it does:
'   Wraps a Power Automate/SharePoint operation or timestamp conversion for
'   PA_JsonDecodeLiteral.
'
' Why it exists:
'   Centralized bridge procedures prevent every scanner workflow from manually
'   building HTTP calls and parsing responses.
'
' Workflow note:
'   Public entry point: keep this name/signature stable unless every button,
'   form, timer, workbook event, and cross-module call is updated too.
'------------------------------------------------------------------------------
Public Function PA_JsonDecodeLiteral(ByVal rawText As String) As String
    rawText = Trim$(CStr(rawText))

    If Len(rawText) = 0 Then Exit Function
    If LCase$(rawText) = "null" Then Exit Function

    If Left$(rawText, 1) = """" Then
        PA_JsonDecodeLiteral = JsonDecodeString(rawText)
    Else
        PA_JsonDecodeLiteral = rawText
    End If
End Function
Public Function PA_IndianTrailBayLookup(ByVal deliveryListKey As String, _
                                        ByVal orderNumber As Long, _
                                        Optional ByVal itemNumber As Long = 0) As Object
    Dim payload As String
    Dim responseText As String
    Dim d As Object

    Set d = CreateObject("Scripting.Dictionary")

    deliveryListKey = Trim$(CStr(deliveryListKey))

    If Len(deliveryListKey) = 0 Or orderNumber <= 0 Then
        d("ok") = False
        d("found") = False
        d("message") = "Missing delivery list key or order number."
        Set PA_IndianTrailBayLookup = d
        Exit Function
    End If

    payload = "{" & _
              """deliveryListKey"":" & JsonStringOrEmpty(deliveryListKey) & "," & _
              """orderNumber"":" & CStr(orderNumber) & "," & _
              """normalizedOrderNumber"":" & JsonStringOrEmpty(CStr(orderNumber)) & "," & _
              """itemNumber"":" & CStr(itemNumber) & "," & _
              """glassHeader"":" & JsonStringOrEmpty(vbNullString) & "," & _
              """glassCategory"":" & JsonStringOrEmpty(vbNullString) & "," & _
              """bayCategory"":" & JsonStringOrEmpty(vbNullString) & "," & _
              """scanStage"":" & JsonStringOrEmpty("LOOKUP_ONLY") & "," & _
              """targetSheet"":" & JsonStringOrEmpty("Inbound - Indian Trail") & "," & _
              """stationName"":" & JsonStringOrEmpty(GetStationName()) & "," & _
              """sourceWorkbook"":" & JsonStringOrEmpty(ThisWorkbook.Name) & "," & _
              """barcode"":" & JsonStringOrEmpty(vbNullString) & "," & _
              """notes"":" & JsonStringOrEmpty(vbNullString) & "," & _
              """lookupOnly"":true" & _
              "}"

    On Error GoTo FailLookup

    Call PA_PostJson(PA_URL_INDIAN_TRAIL_BAY_ASSIGN_OR_GET, payload, responseText)

    d("ok") = JsonGetBooleanFlexible(responseText, "ok")
    d("found") = JsonGetBooleanFlexible(responseText, "found")
    d("resultCode") = JsonGetString(responseText, "resultCode")
    d("message") = JsonGetString(responseText, "message")
    d("bayKey") = JsonGetString(responseText, "bayKey")
    d("bayDisplayName") = JsonGetString(responseText, "bayDisplayName")
    d("assignmentStatus") = JsonGetString(responseText, "assignmentStatus")
    d("glassCategory") = JsonGetString(responseText, "glassCategory")
    d("glassHeader") = JsonGetString(responseText, "glassHeader")
    d("assignmentId") = JsonGetString(responseText, "assignmentId")
    d("rawResponse") = responseText

    Set PA_IndianTrailBayLookup = d
    Exit Function

FailLookup:
    d("ok") = False
    d("found") = False
    d("message") = "Bay lookup failed. Error " & Err.Number & ": " & Err.Description
    Err.Clear

    Set PA_IndianTrailBayLookup = d
End Function

