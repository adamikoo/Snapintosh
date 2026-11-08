# SPDX-License-Identifier: MIT
<#
.SYNOPSIS
    Configures Windows Boot Manager on the internal SSD to display Snapintosh.
#>

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Requesting Administrator privileges..." -ForegroundColor Yellow
    Start-Process powershell.exe -Verb RunAs -ArgumentList "-NoExit -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit 0
}

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "       Snapintosh Windows Boot Menu Setup               " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

$appDataBoot = "$env:LOCALAPPDATA\Snapintosh\boot"
$efiSource   = "$appDataBoot\q1n1.efi"
$stageSource = "$appDataBoot\q1n1-stage.bin"
$cfgSource   = "$appDataBoot\snapintosh_boot.cfg"

if (-not (Test-Path $efiSource)) {
    Write-Host "[!] Error: q1n1.efi not found in $appDataBoot." -ForegroundColor Red
    Write-Host "    Please run Snapintosh launcher Option 3 first." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[1/6] Mounting EFI System Partition to S:..." -ForegroundColor White
cmd /c "mountvol S: /s" | Out-Null

if (-not (Test-Path "S:\EFI")) {
    Write-Host "[!] Error: Failed to mount EFI System Partition to S:." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

try {
    Write-Host "[2/6] Staging bootloader files to S:\EFI\Snapintosh..." -ForegroundColor White
    $targetDir = "S:\EFI\Snapintosh"
    if (-not (Test-Path $targetDir)) {
        New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    }

    Copy-Item -Path $efiSource -Destination "$targetDir\q1n1.efi" -Force
    Write-Host "      [+] Copied q1n1.efi" -ForegroundColor Green

    if (Test-Path $stageSource) {
        Copy-Item -Path $stageSource -Destination "$targetDir\q1n1-stage.bin" -Force
        Write-Host "      [+] Copied q1n1-stage.bin" -ForegroundColor Green
    }

    if (Test-Path $cfgSource) {
        Copy-Item -Path $cfgSource -Destination "$targetDir\snapintosh_boot.cfg" -Force
        Write-Host "      [+] Copied snapintosh_boot.cfg" -ForegroundColor Green
    }

    Write-Host "[3/6] Cleaning up old or invalid Snapintosh BCD entries..." -ForegroundColor White
    $rawBcd = cmd /c "bcdedit /enum all"
    $matches = [regex]::Matches($rawBcd, '(?ms)identifier\s+(\{[a-f0-9\-]+\}).*?description\s+Snapintosh')
    foreach ($m in $matches) {
        $oldId = $m.Groups[1].Value
        Write-Host "      [-] Removing obsolete entry: $oldId" -ForegroundColor Yellow
        cmd /c "bcdedit /delete $oldId" | Out-Null
    }

    Write-Host "[4/6] Creating brand new genuine OS boot entry..." -ForegroundColor White
    $copyOut = cmd /c 'bcdedit /copy {current} /d "Snapintosh (macOS)"'
    $newGuid = $null
    if ($copyOut -match '(\{[a-f0-9\-]+\})') {
        $newGuid = $matches[1]
        Write-Host "      [+] Created new OS loader entry: $newGuid" -ForegroundColor Green
    } else {
        Write-Host "[!] Error: bcdedit copy failed: $copyOut" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }

    Write-Host "[5/6] Pointing entry to Snapintosh q1n1.efi..." -ForegroundColor White
    cmd /c "bcdedit /set $newGuid device partition=S:" | Out-Null
    cmd /c "bcdedit /set $newGuid osdevice partition=S:" | Out-Null
    cmd /c "bcdedit /set $newGuid path \EFI\Snapintosh\q1n1.efi" | Out-Null
    cmd /c "bcdedit /set $newGuid nointegritychecks Yes" | Out-Null
    cmd /c "bcdedit /set $newGuid testsigning Yes" | Out-Null
    Write-Host "      [+] Entry configured to boot S:\EFI\Snapintosh\q1n1.efi" -ForegroundColor Green

    Write-Host "[6/6] Activating OS boot menu with 20-second timeout..." -ForegroundColor White
    cmd /c "bcdedit /set {bootmgr} displayorder $newGuid /addlast" | Out-Null
    cmd /c "bcdedit /set {bootmgr} displaybootmenu Yes" | Out-Null
    cmd /c "bcdedit /set {bootmgr} timeout 20" | Out-Null
    Write-Host "      [+] OS boot menu activated." -ForegroundColor Green

}
finally {
    Write-Host ""
    Write-Host "Safely unmounting S:..." -ForegroundColor White
    cmd /c "mountvol S: /d" | Out-Null
    Write-Host "  [+] S: unmounted safely." -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host "CURRENT WINDOWS BOOT MANAGER CONFIGURATION:" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
cmd /c "bcdedit /enum {bootmgr}"
Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host "SUCCESS! The boot menu is now configured on your SSD." -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host ""
Write-Host "WHAT HAPPENS ON RESTART:" -ForegroundColor Yellow
Write-Host "1. Restart your laptop." -ForegroundColor White
Write-Host "2. On the ASUS screen (from your photo), press ENTER on 'Windows Boot Manager'." -ForegroundColor White
Write-Host "3. Windows Boot Manager will now STOP and display:" -ForegroundColor Cyan
Write-Host "     Windows 11" -ForegroundColor Cyan
Write-Host "     Snapintosh (macOS)" -ForegroundColor Cyan
Write-Host "4. Use your arrow keys to select 'Snapintosh (macOS)' and press Enter!" -ForegroundColor White
Write-Host ""
Write-Host "REMINDER: Secure Boot Control must be [Disabled] in BIOS (F2)" -ForegroundColor Yellow
Write-Host "so the hardware allows q1n1.efi to execute." -ForegroundColor Yellow
Write-Host "========================================================" -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to finish"
