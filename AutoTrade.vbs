Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.Run "cmd /c py server.py --serve 8000", 0, False
WScript.Sleep 1500
WshShell.Run "http://localhost:8000"
