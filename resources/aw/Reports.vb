' File: resources/aw/Reports.vb
' VB.NET-Skript for Executing various Reports
'
' Version: 2.32.0
'
' History:
' 04.02.2011 THG, JMO : #211288: Leere Seiten im Report sollen ignoriert werden. Dies führte bisher zu einer Fehlermeldung beim Freigeben von Läufen.
' 03.12.2010 THG, JMO : #216042: rufe KeepReportSettings = 1 IMMER auf, also auch bei Bildschirmausgabe und VOR SelectPrinterByName().
' 14.09.2010 THG : Do not use COM-Objects for Tracing, use Classes in loaded Assemblies instead.
'                  Thus improves the Performance and Stability for that Script.
' 29.01.2010 THG :     #188564: 0 pages -> no execution. Process will return as successful!
' 06.11.2009 THG :     #184540: Error handling if method 'OutputToPrinter2' fails.
' 13.03.2009 THG :     Korrekturen
' 30.01.2009 DK        Variablen ExportDir , FormatType, ExportDir und ExportIndex eingeführt + Dokulinks  
' 26.01.2009 DK, THG : #167886: Can use the AlcimRun.AlcimReport2.Export()-Method dependent on the
'                      variables 'ExportFile' and 'FormatType' are set.
'                      Additional tracing with AlcimTools enabled.
' 04.12.2008 THG : Set KeepReportSettings = 1 as default when printing.
' 02.09.2008 THG : Do not call oRpt.SelectPrinterByName() if no printer was set in parameters.
' 07.09.2007 THG : Implemented

'Exportformate 
' Export Formate 
' crEFTNoFormat = 0,                crEFTText = 8,                crEFTExcel30 = 19,
' crEFTCrystalReport = 1,           crEFTTabSeparatedText = 9,    crEFTExcel40 = 20,
' crEFTDataInterchange = 2,         crEFTPaginatedText = 10,      crEFTExcel50 = 21,
' crEFTRecordStyle = 3,             crEFTLotus123WKS = 11,        crEFTExcel50Tabular = 22,
' crEFTRichText = 4,                crEFTLotus123WK1 = 12,        crEFTODBC = 23,
' crEFTCommaSeparatedValues = 5,    crEFTLotus123WK3 = 13,        crEFTHTML32Standard = 24,
' crEFTTabSeparatedValues = 6,      crEFTWordForWindows = 14,     crEFTExplorer32Extend = 25,
' crEFTCharSeparatedValues = 7,     crEFTExcel21 = 18,            crEFTNetScape20 = 26,
' crEFTExcel70Tabular = 28,         crEFTPortableDocFormat = 31,  crEFTExcel70 = 27,
' crEFTExcel80 = 29,                crEFTHTML40 = 32,             crEFTReportDefinition = 34
' crEFTExcel80Tabular = 30,         crEFTCrystalReport70 = 33,
'                         




Imports System
Imports System.IO
Imports System.Diagnostics
Imports Microsoft.VisualBasic
Imports Albwir.Basis.Tracing
 
Module AWScript_Reports
    Function Main(ByVal Schedule As String, ByVal Params As String, ByVal Modulname As String) As Integer
        Dim Resultcode As Integer = 0 '0=Successful
        Dim DBConnect As String
        Dim StationID As String
        Dim oRpt As Object = Nothing 'Interface AlcimRun.AlcimReport2
        Dim AlReg As Object = Nothing 'Interface AlcimRun.AlcimRegistry
        ' #167886: Needed for Export-functions:
        Dim ExportFile As String
        Dim ExportDir As String
        Dim ExportName As String
        Dim ExportIndex As String
        Dim FormatType As String
        Dim RegPath As String
        Dim traceSwitch As New TraceSwitch("Albwir.Alcim.Scripting", "Tracing for REPORTS.VB")

        Const MessageLevelForReport2 As Integer = 2

        ' Variables extracted from String-Argument 'Params':
        Dim Listenname As String 'Report-File (.rpt)

        Try
            ' Prepare the Modulname:
            If (String.IsNullOrEmpty(Modulname)) Then
                Modulname = "REPORTS.VB_" & Schedule
            Else
                Modulname = Modulname & "_" & Schedule
            End If

            ' Read the Connection-String and the StationId from the Registry:
            AlReg = CreateObject("AlcimRun.AlcimRegistry")
            DBConnect = AlReg.GetConnectString()
            If (DBConnect.Length = 0) Then
                Throw New Exception("Could not find 'Database' in Registry")
            End If

            StationID = AlReg.GetStationId()
            If (StationID.Length = 0) Then
                Throw New Exception("Could not find 'StationId' in Registry")
            End If

            Listenname = Convert.ToString(GetVariableFromParamstring(Params, "Report"))
            AWTrace.WriteLineIf(TraceLevel.Verbose, traceSwitch, "Listenname = " & Listenname)

            ' #167886: Retrieve parameter ExportFile und FormatType from Parameterstring
            ExportDir = Convert.ToString(GetVariableFromParamstring(Params, "ExportDir"))
            AWTrace.WriteLineIf(TraceLevel.Verbose, traceSwitch, "ExportDir = " & ExportDir)
            ExportFile = Convert.ToString(GetVariableFromParamstring(Params, "ExportFile"))
            AWTrace.WriteLineIf(TraceLevel.Verbose, traceSwitch, "ExportFile = " & ExportFile)
            FormatType = Convert.ToString(GetVariableFromParamstring(Params, "FormatType"))
            AWTrace.WriteLineIf(TraceLevel.Verbose, traceSwitch, "FormatType = " & FormatType)
            ExportIndex = Convert.ToString(GetVariableFromParamstring(Params, "ExportIndex"))
            AWTrace.WriteLineIf(TraceLevel.Verbose, traceSwitch, "ExportIndex = " & ExportIndex)

            ' create the AlcimReport2-Interface:
            oRpt = CreateObject("AlcimRun.AlcimReport2")
            oRpt.ErrorReset()
            Resultcode = oRpt.OpenReport(Listenname, MessageLevelForReport2)
            If (Resultcode <> 0) Then
                Throw New Exception("'AlcimRun.AlcimReport2' - OpenReport() failed with code " & Resultcode)
            End If

            Resultcode = oRpt.LogOnServerEx("ALL_REPORTS", "ALCIMDBREP", DBConnect)
            If (Resultcode <> 0) Then
                Throw New Exception("'AlcimRun.AlcimReport2' - LogOnServerEx(ALCIMDBREP) failed with code " & Resultcode)
            End If

            Resultcode = oRpt.LogOnServerEx("ALL_REPORTS", "AlcimSkizzen", DBConnect)
            If (Resultcode <> 0) Then
                Throw New Exception("'AlcimRun.AlcimReport2' - LogOnServerEx(AlcimSkizzen) failed with code " & Resultcode)
            End If

            Resultcode = oRpt.SetParameter("schedule", Convert.ToInt32(Schedule))
            If (Resultcode <> 0) Then
                Throw New Exception("'AlcimRun.AlcimReport2' - SetParameter(schedule) failed with code " & Resultcode)
            End If

            Dim ParamFileName As String = GetReportParamName(Listenname)
            AWTrace.WriteLineIf(TraceLevel.Verbose, traceSwitch, "ParamFileName = " & ParamFileName)
            If (0 < ParamFileName.Length) Then
                Resultcode = oRpt.SetParameter("paramstring", ParamFileName)
                If (Resultcode <> 0) Then
                    Throw New Exception("'AlcimRun.AlcimReport2' - SetParameter(ParamFileName) failed with code " & Resultcode)
                End If
            End If

            ' #167886: Parameters 'ExportFile' and 'FormatType' set?
            If (False = String.IsNullOrEmpty(ExportFile)) And (False = String.IsNullOrEmpty(FormatType)) And (False = String.IsNullOrEmpty(ExportDir)) Then
                ' export 
                'PK,NG,DK Wichtig bei Export im Textformat z.B.: als Schnittstellendatei !!!
                ' Der Eintrag "PromtAgain=1" macht es möglich, dass Du beim Export wieder gefragt wirst, wieviel Zeichen pro Inch ausgegeben werden sollen. 
                ' Der ist also nur wichtig, wenn Du direkt mit Crystal-Report arbeitest.Mit dem  Eintrag "CharPerInch" wird sichergestellt 
                ' dass die ganze Zeile ausgegeben wird ( wenn nicht gesetzt so wird sie ab einer bestimmten Stelle abgeschnitten 
                RegPath = "HKEY_CURRENT_USER\Software\Crystal Decisions\10.0\Crystal Reports\Export\Text"

                Resultcode = AlReg.RegSetLong(RegPath, "PromptAgain", "1")
                If (Resultcode <> 0) Then
                    Throw New Exception(RegPath & "PromptAgain " & Resultcode)
                End If

                Resultcode = AlReg.RegSetLong(RegPath, "CharPerInch", "24")
                If (Resultcode <> 0) Then
                    Throw New Exception(RegPath & "CharPerInch " & Resultcode)
                End If

                Resultcode = oRpt.SetExportFormatType(Convert.ToInt16(FormatType))
                If (Resultcode <> 0) Then
                    Throw New Exception("'AlcimRun.AlcimReport2' - oRpt.SetExportFormatType(Convert.ToInt32(FormatType)) " & Resultcode)
                End If



                Select Case ExportIndex
                    Case "DATETIME"
                        ExportIndex = Convert.ToString(DateTime.Now)
                        ExportIndex = ExportIndex.Replace(":", "_")
                        ExportIndex = ExportIndex.Replace(".", "_")
                        ExportIndex = ExportIndex.Replace("/", "_")
                        ExportName = ExportDir & Convert.ToString(Schedule) & "_" & ExportIndex & ExportFile

                    Case Else
                        ExportName = ExportDir & Convert.ToString(Schedule) & "_" & ExportFile

                End Select

                Resultcode = oRpt.SetExportFileName(ExportName)
                If (Resultcode <> 0) Then
                    Throw New Exception("'AlcimRun.AlcimReport2' - oRpt.SetExportFileName(ExportFile) " & Resultcode)
                End If

                Resultcode = oRpt.Export(0)
                If (Resultcode <> 0) Then
                    Throw New Exception("'AlcimRun.AlcimReport2' - oRpt.Export(0) " & Resultcode)
                Else
                    AWTrace.WriteLineIf(TraceLevel.Verbose, traceSwitch, "Export successful")
                    'Call RunSelectInsert(ExportName, schedule)
                End If

            Else ' #167886
                ' normal print or display on screen: 
                Dim outputToPrinter As Boolean = Convert.ToBoolean(GetVariableFromParamstring(Params, "OutputToPrinter"))

                ' [03.12.2010 THG, JMO] #216042: rufe KeepReportSettings = 1 IMMER auf, also auch bei Bildschirmausgabe.
                ' Dabei ist wichtig, dass dies VOR dem Aufruf von SelectPrinterByName(.) geschieht!:
                oRpt.KeepReportSettings = 1
                ' [04.02.2011 THG, JMO] #211288: Leere Seiten sollen ignoriert werden. Achtung: Ist dieser Schalter
                ' nicht gesetzt, so führt dies im Falle von leeren Reports zu einem XAH54356-Fehler beim Freigeben!
                oRpt.SupressEmptyPages = 1

                ' If no printer was set we should not call oRpt.SelectPrinterByName():
                Dim printer As String = Convert.ToString(GetVariableFromParamstring(Params, "Printer"))
                If (False = String.IsNullOrEmpty(printer)) Then
                    Resultcode = oRpt.SelectPrinterByName(printer)
                    If (Resultcode <> 0) Then
                        Throw New Exception("'AlcimRun.AlcimReport2' - SelectPrinterByName(Printer) failed with code " & Resultcode)
                    End If
                End If

                Dim numberOfCopies As Integer = Convert.ToInt32(GetVariableFromParamstring(Params, "Pages"))
                ' [29.01.2010 THG] #188564: No pages -> no execution!
                If (numberOfCopies < 1) Then
                    Exit Function
                End If

                If (outputToPrinter = True) Then
                    ' [06.11.2009 THG] #184540: Error handling if method 'OutputToPrinter2' fails:
                    If (oRpt.OutputToPrinter2(0, numberOfCopies) <> 0) Then ' Do not set Resultcode = oRpt.OutputToPrinter2(..)
                        Dim errortext As String = ""
                        Dim datatext As String = ""
                        Dim errorcode As Integer = 0
                        Dim msg As String = ""
                        If (oRpt.ErrorLast(errorcode, errortext, datatext) > 0) Then
                            msg = "'AlcimRun.AlcimReport2' - OutputToPrinter2(..) failed with errorcode " & errorcode
                            If (False = String.IsNullOrEmpty(errortext)) Then
                                msg = msg & Environment.NewLine & errortext
                            End If
                            Throw New Exception(msg)
                        End If
                    End If
                Else
                    oRpt.OutputToWindow(90) ' Do not set Resultcode = oRpt.OutputToWindow(.)
                End If
            End If ' #167886

        Catch e As Exception
            Resultcode = -1
            WriteExceptionMessageToFile(Modulname, e.Message)
            ' Trace the exception message also to the logfile:
            AWTrace.WriteLineIf(TraceLevel.Error, traceSwitch, e.Message)
        Finally
            If (oRpt IsNot Nothing) Then
                System.Runtime.InteropServices.Marshal.ReleaseComObject(oRpt)
            End If
            oRpt = Nothing

            If (AlReg IsNot Nothing) Then
                System.Runtime.InteropServices.Marshal.ReleaseComObject(AlReg)
            End If
            AlReg = Nothing
        End Try

        Return Resultcode
    End Function

    ' Writes the message to a textfile within the users Temp-Folder:
    Sub WriteExceptionMessageToFile(ByVal modulname As String, ByVal message As String)
        Dim filename As String
        filename = Path.Combine(Path.GetTempPath(), modulname & ".txt") 'i.e. "C:\Dokumente und Einstellungen\tgross\Lokale Einstellungen\Temp\PID980_REPORTS.VB_1225.txt"
        ' open the file
        Dim fs As FileStream = New FileStream(filename, FileMode.Create, FileAccess.Write)
        Using sw As StreamWriter = New StreamWriter(fs)
            sw.WriteLine(message) ' write the message
        End Using
        fs.Close()
    End Sub

    ' Function to extract a Variable from a Parameter String:
    Function GetVariableFromParamstring(ByVal parameterString As String, ByVal variableToSearch As String) As Object
        Dim retVal As Object = Nothing
        Dim delimiterStr As String = ",;"
        Dim delimiter() As Char = delimiterStr.ToCharArray()
        Dim pParams() As String = parameterString.Split(delimiter)
        Dim substring As String
        Dim split() As String

        For Each substring In pParams
            substring = substring.Trim()
            split = substring.Split("=")
            If (2 = split.Length) Then
                split(0) = split(0).Trim()
                If (0 = String.Compare(variableToSearch, split(0), True)) Then ' compare case insensitiv!
                    retVal = split(1).Trim()
                    Exit For
                End If
            End If
        Next

        Return retVal
    End Function

    ' Function to build the param-filename
    Function GetReportParamName(ByVal ReportName As String) As String
        Dim ParamName As String = ""

        If (0 < ReportName.Length) Then
            'ParamName = System.IO.Path.ChangeExtension(ReportName, ".param")
            ParamName = ReportName + ".param"
            ' Check Existance of this File:
            Dim file As System.IO.FileInfo
            file = New System.IO.FileInfo(ParamName)
            If (file.Exists() = False) Then
                ParamName = ""
            End If
        End If

        Return ParamName
    End Function

    Sub RunSelectInsert(ByVal Link As String, ByVal Schedule As String)
        Dim SQL As String
        Dim oDBRunSelect As Object
        Dim Resultat As Integer
        Dim Auftnr As String
        Dim Pos As String

        SQL = "select distinct auftnr, pos from pool_teile where teile_nr=0 and lauf=" & Schedule

        oDBRunSelect = CreateObject("AlcimRun.alcimDB")
        Resultat = oDBRunSelect.Init("DEFAULT")
        Resultat = oDBRunSelect.SelectExec(SQL)

        While (oDBRunSelect.SelectFetch)
            Auftnr = Convert.ToString(oDbRunSelect.GetLong(1))
            Pos = Convert.ToString(oDbRunSelect.GetLong(2))


            SQL = "delete from pool_dokumente where typ=99 and auftnr= " & Auftnr & " and pos= " & Pos
            Call DBUpdate(SQL)
            SQL = "INSERT INTO  pool_dokumente ( sperrstation,sperrzeit,lastmodstation,lastmodzeit,auftnr,pos,u_pos,typ,dokumentenlink) "
            SQL = SQL & " VALUES ( '------', '2009-01-27 00:00:00.0', 'DKPK','2009-01-27 00:00:00.0', "
            SQL = SQL & Auftnr & " , " & pos & " , 0,99, '" & Link & "')"
            Call DBUpdate(SQL)

        End While
        Resultat = oDBRunSelect.SelectDone
        oDBRunSelect = Nothing
    End Sub



    Sub DBUpdate(ByVal STMT As String)
        Dim Resultat As Integer
        Dim oDBUpd As Object
        Dim Rows As Integer

        oDBUpd = CreateObject("AlcimRun.AlcimDB")
        Resultat = oDBUpd.Init("DEFAULT") ' Öffne Verbindung
        Resultat = oDBUpd.Transact(STMT, Rows)
        Resultat = oDBUpd.Done     ' Schließe Datenbankverbindung
        oDBUpd = Nothing
    End Sub



End Module

