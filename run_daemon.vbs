Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = scriptDir

pythonPath = scriptDir & "\.venv\Scripts\pythonw.exe"
serverPath = Chr(34) & scriptDir & "\daemon\server.py" & Chr(34)

' Check if the virtual environment exists
If Not fso.FileExists(pythonPath) Then
    res = MsgBox("Setup has not been completed." & vbCrLf & vbCrLf & _
                 "The virtual environment (.venv) was not found." & vbCrLf & vbCrLf & _
                 "Would you like to run the installer (scripts\install_windows.ps1) now?", _
                 vbYesNo + vbExclamation, "Local Live Captions - Setup Required")
    If res = vbYes Then
        ' Run PowerShell installer visible so user can see installation progress
        WshShell.Run "powershell.exe -ExecutionPolicy Bypass -File """ & scriptDir & "\scripts\install_windows.ps1""", 1, True
    Else
        WScript.Quit
    End If
End If

' Run completely hidden in the background (Window style 0)
WshShell.Run Chr(34) & pythonPath & Chr(34) & " " & serverPath, 0, False

Set WshShell = Nothing
Set fso = Nothing