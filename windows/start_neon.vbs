Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
root = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))
pythonw = root & "\.venv\Scripts\pythonw.exe"
If fso.FileExists(pythonw) Then
    shell.CurrentDirectory = root
    shell.Run """" & pythonw & """ """ & root & "\web.py""", 0, False
End If
