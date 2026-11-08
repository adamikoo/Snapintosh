# SPDX-License-Identifier: MIT
# Cleans up the Snapintosh entries from Windows Boot Manager
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Start-Process powershell.exe -Verb RunAs -ArgumentList "-ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit 0
}

Write-Host "Cleaning up Windows Boot Manager..." -ForegroundColor Cyan
$rawBcd = cmd /c "bcdedit /enum all"
$matches = [regex]::Matches($rawBcd, '(?ms)identifier\s+(\{[a-f0-9\-]+\}).*?description\s+Snapintosh')
foreach ($m in $matches) {
    $id = $m.Groups[1].Value
    Write-Host "  [-] Removing entry: $id" -ForegroundColor Yellow
    cmd /c "bcdedit /delete $id" | Out-Null
}

cmd /c "bcdedit /set {bootmgr} displaybootmenu No" | Out-Null
cmd /c "bcdedit /set {bootmgr} timeout 5" | Out-Null
Write-Host "Windows Boot Manager restored to clean default state." -ForegroundColor Green
Read-Host "Press Enter to finish"
