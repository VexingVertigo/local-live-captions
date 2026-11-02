Set WshShell = CreateObject("WScript.Shell")
' Runs pythonw.exe in window style 0 (completely hidden)
WshShell.Run Chr(34) & WshShell.CurrentDirectory & "\.venv\Scripts\pythonw.exe" & Chr(34) & " daemon\server.py", 0, False
Set WshShell = Nothing