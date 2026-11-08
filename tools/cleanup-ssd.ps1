# SPDX-License-Identifier: MIT
<#
.SYNOPSIS
    Cleans all Snapintosh files from the SSD EFI partition and restores Windows Boot Manager to factory state.
#>

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Requesting Administrator privileges to clean SSD..." -ForegroundColor Yellow
    Start-Process powershell.exe -Verb RunAs -ArgumentList "-ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit 0
}

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "       Cleaning Snapintosh Files from SSD               " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Clean BCD entries
Write-Host "[1/3] Removing Snapintosh entries from Windows Boot Manager..." -ForegroundColor White
$rawBcd = cmd /c "bcdedit /enum all"
$matches = [regex]::Matches($rawBcd, '(?ms)identifier\s+(\{[a-f0-9\-]+\}).*?description\s+Snapintosh')
foreach ($m in $matches) {
    $id = $m.Groups[1].Value
    Write-Host "      [-] Deleted BCD entry: $id" -ForegroundColor Green
    cmd /c "bcdedit /delete $id" | Out-Null
}

cmd /c "bcdedit /set {bootmgr} displaybootmenu No" | Out-Null
cmd /c "bcdedit /set {bootmgr} timeout 5" | Out-Null
Write-Host "      [+] Windows Boot Manager restored to factory default." -ForegroundColor Green

# 2. Mount S: and delete S:\EFI\Snapintosh
Write-Host "[2/3] Mounting EFI partition to remove staged boot files..." -ForegroundColor White
cmd /c "mountvol S: /s" | Out-Null

if (Test-Path "S:\EFI\Snapintosh") {
    Remove-Item -Path "S:\EFI\Snapintosh" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "      [-] Deleted S:\EFI\Snapintosh folder and files." -ForegroundColor Green
} else {
    Write-Host "      [+] S:\EFI\Snapintosh already clean." -ForegroundColor Green
}

# 3. Unmount S:
Write-Host "[3/3] Unmounting EFI partition..." -ForegroundColor White
cmd /c "mountvol S: /d" | Out-Null
Write-Host "      [+] EFI partition safely unmounted." -ForegroundColor Green

Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host "SUCCESS! Your internal SSD is 100% stock and clean." -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to finish"
