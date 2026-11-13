Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
root = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))
shell.Run "powershell -NoProfile -WindowStyle Hidden -Command ""while (-not (Get-Process Spotify -ErrorAction SilentlyContinue)) { Start-Sleep -Seconds 10 }""", 0, True
pythonw = root & "\.venv\Scripts\pythonw.exe"
If fso.FileExists(pythonw) Then
    shell.CurrentDirectory = root
    shell.Run """" & pythonw & """ """ & root & "\web.py""", 0, False
End If
