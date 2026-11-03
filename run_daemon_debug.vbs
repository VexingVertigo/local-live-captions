Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = scriptDir

pythonPath = scriptDir & "\.venv\Scripts\python.exe"

' If .venv does not exist, prompt user to run installer
If Not fso.FileExists(pythonPath) Then
    res = MsgBox("Virtual environment not found." & vbCrLf & vbCrLf & _
                 "Would you like to run the installer (scripts\install_windows.ps1) now?", _
                 vbYesNo + vbExclamation, "Setup Required")
    If res = vbYes Then
        WshShell.Run "powershell.exe -ExecutionPolicy Bypass -File """ & scriptDir & "\scripts\install_windows.ps1""", 1, True
    Else
        WScript.Quit
    End If
End If

serverPath = Chr(34) & scriptDir & "\daemon\server.py" & Chr(34)
WshShell.Run "cmd.exe /k title Live Captions Server ^& """ & pythonPath & """ " & serverPath, 1, False

Set WshShell = Nothing
Set fso = Nothing