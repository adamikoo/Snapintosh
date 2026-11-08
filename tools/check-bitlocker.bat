@echo off
setlocal
echo =======================================================
echo Snapintosh - Windows Device Encryption / BitLocker Check
echo =======================================================
echo.

:: Check for admin rights
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting Administrator privileges to query encryption keys...
    powershell -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

echo [1/3] Checking BitLocker / Device Encryption status...
manage-bde -status C:

echo.
echo [2/3] Querying Recovery Key Protectors for C:...
manage-bde -protectors -get C: > "%USERPROFILE%\Desktop\BitLocker_Recovery_Key.txt" 2>&1
type "%USERPROFILE%\Desktop\BitLocker_Recovery_Key.txt"

echo.
echo =======================================================
echo Output saved to:
echo   %USERPROFILE%\Desktop\BitLocker_Recovery_Key.txt
echo =======================================================
echo.
echo If a 48-digit Recovery Password is shown above, write it down
echo or save a copy to your phone or a USB stick!
echo.
echo If it says 'Protection Off' or 'No key protectors found',
echo then your drive is NOT encrypted and there is no risk of lockout.
echo =======================================================
echo.
pause
