@echo off
title Snapintosh macOS 27 VM Launcher
cls
echo ======================================================================
echo          SNAPINTOSH macOS 27 SEQUOIA ARM64 VIRTUAL MACHINE
echo ======================================================================
echo.
echo Target System: Apple Silicon Mac17,5 / J700AP
echo Target OS:     macOS 27 Sequoia (Darwin 26A428)
echo Architecture:  ARM64 with EL2 Hypervisor Monitor
echo.
echo Choose an execution mode:
echo   [1] Start Interactive macOS VM with GUI Window (Default)
echo   [2] Start macOS VM in Headless / Fast Console Mode
echo   [3] Configure and Launch Oracle VirtualBox 7.x Appliance
echo   [4] Exit
echo.
set /p CHOICE="Enter choice [1-4] (default: 1): "
if "%CHOICE%"=="" set CHOICE=1

if "%CHOICE%"=="1" (
    echo.
    echo [+] Starting Snapintosh interactive graphical VM...
    echo [+] Live display window opening...
    set SNAP_QEMU_DISPLAY=default
    set SNAP_WATCHDOG=1800
    python tools\run-qemu-xnuboot.py
    pause
    exit /b 0
)

if "%CHOICE%"=="2" (
    echo.
    echo [+] Starting Snapintosh headless VM with live screenshot captures...
    set SNAP_QEMU_DISPLAY=none
    set SNAP_WATCHDOG=1800
    python tools\run-qemu-xnuboot.py
    pause
    exit /b 0
)

if "%CHOICE%"=="3" (
    echo.
    echo [+] Configuring Oracle VirtualBox 7.x Appliance...
    call build\virtualbox\Import-To-VirtualBox.bat
    exit /b 0
)

if "%CHOICE%"=="4" (
    exit /b 0
)
