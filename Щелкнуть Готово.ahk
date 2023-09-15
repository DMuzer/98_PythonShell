#NoEnv  ; Recommended for performance and compatibility with future AutoHotkey releases.
; #Warn  ; Enable warnings to assist with detecting common errors.
SendMode Input  ; Recommended for new scripts due to its superior speed and reliability.
SetWorkingDir %A_ScriptDir%  ; Ensures a consistent starting directory.
F12::
MouseGetPos, xpos, ypos
;SendEvent {Click 130 160}
Click, 130, 160
MouseMove, xpos, ypos
return
F11::
ControlClick, Готово, ahk_exe revit.exe



