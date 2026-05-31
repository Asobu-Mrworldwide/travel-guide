On Error Resume Next

Dim fso, sDir, appPath, q, cmd
Set fso = CreateObject("Scripting.FileSystemObject")
sDir    = fso.GetParentFolderName(WScript.ScriptFullName)
appPath = sDir & "\assets\tools\app.py"
q       = Chr(34)

If Not fso.FileExists(appPath) Then
    MsgBox "app.py not found:" & vbCrLf & appPath, 16, "Launch Error"
    WScript.Quit
End If

Set WshShell = CreateObject("WScript.Shell")
cmd = "cmd /c start " & q & q & " /b python -m streamlit run " & q & appPath & q
WshShell.Run cmd, 0, False

If Err.Number <> 0 Then
    MsgBox "Launch failed: " & Err.Description, 16, "Launch Error"
End If
