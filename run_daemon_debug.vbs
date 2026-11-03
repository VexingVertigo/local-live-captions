Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = scriptDir

pythonPath = scriptDir & "\.venv\Scripts\python.exe"
serverPath = Chr(34) & scriptDir & "\daemon\server.py" & Chr(34)

' If .venv does not exist, prompt user to run installer
If Not fso.FileExists(pythonPath) Then
    res = MsgBox("Setup has not been completed." & vbCrLf & vbCrLf & _
                 "The virtual environment (.venv) was not found." & vbCrLf & vbCrLf & _
                 "Would you like to run the installer (scripts\install_windows.ps1) now?", _
                 vbYesNo + vbExclamation, "Local Live Captions - Setup Required")
    If res = vbYes Then
        WshShell.Run "powershell.exe -ExecutionPolicy Bypass -File """ & scriptDir & "\scripts\install_windows.ps1""", 1, True
    Else
        WScript.Quit
    End If
End If

' Launch command prompt, title it, and execute server.py
cmdString = "cmd.exe /k " & Chr(34) & "title Live Captions Server && " & Chr(34) & pythonPath & Chr(34) & " " & serverPath & Chr(34)
WshShell.Run cmdString, 1, False

Set WshShell = Nothing
Set fso = Nothing