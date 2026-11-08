@echo off
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -NoProfile -Command "Start-Process cmd.exe -ArgumentList '/c mountvol S: /d' -Verb RunAs"
    exit /b
)
mountvol S: /d
echo Drive letter S: unmounted and hidden.
