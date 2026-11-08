# SPDX-License-Identifier: MIT
# Prepares a bootable USB drive for Snapintosh on ASUS Vivobook S 15

$appDataBoot = "$env:LOCALAPPDATA\Snapintosh\boot"
$efiSource = "$appDataBoot\q1n1.efi"
$stageSource = "$appDataBoot\q1n1-stage.bin"
$cfgSource = "$appDataBoot\snapintosh_boot.cfg"

if (-not (Test-Path $efiSource)) {
    Write-Host "[!] Error: q1n1.efi not found in $appDataBoot. Run Snapintosh Option 3 first." -ForegroundColor Red
    exit 1
}

$removables = Get-Volume | Where-Object { $_.DriveType -eq 'Removable' -and $_.DriveLetter }

if (-not $removables) {
    Write-Host "No removable USB drive detected." -ForegroundColor Yellow
    Write-Host "Please plug in a USB flash drive and re-run this script." -ForegroundColor White
    exit 0
}

Write-Host "Found USB drive(s):" -ForegroundColor Green
foreach ($vol in $removables) {
    Write-Host ("  " + $vol.DriveLetter + ": - " + $vol.FileSystemLabel + " (" + $vol.FileSystem + ", " + [math]::Round($vol.Size / 1GB, 2) + " GB)")
}

$targetDrive = $removables[0].DriveLetter + ":"
$fsType = $removables[0].FileSystem

Write-Host ("Staging Snapintosh UEFI bootloader to " + $targetDrive + "...") -ForegroundColor Cyan

$targetBootDir = $targetDrive + "\EFI\BOOT"
if (-not (Test-Path $targetBootDir)) {
    New-Item -ItemType Directory -Path $targetBootDir -Force | Out-Null
}

Copy-Item -Path $efiSource -Destination ($targetBootDir + "\BOOTAA64.EFI") -Force
Write-Host "  [✓] Copied: $targetBootDir\BOOTAA64.EFI" -ForegroundColor Green

if (Test-Path $stageSource) {
    Copy-Item -Path $stageSource -Destination ($targetDrive + "\q1n1-stage.bin") -Force
    Write-Host "  [✓] Copied: $targetDrive\q1n1-stage.bin" -ForegroundColor Green
}

if (Test-Path $cfgSource) {
    Copy-Item -Path $cfgSource -Destination ($targetDrive + "\snapintosh_boot.cfg") -Force
    Write-Host "  [✓] Copied: $targetDrive\snapintosh_boot.cfg" -ForegroundColor Green
}

Write-Host ""
Write-Host "Files successfully copied to $targetDrive!" -ForegroundColor Green

if ($fsType -ne "FAT32") {
    Write-Host "NOTICE: Drive $targetDrive is formatted as $fsType." -ForegroundColor Yellow
    Write-Host "Standard UEFI firmware requires FAT32 to boot from USB." -ForegroundColor Yellow
    Write-Host "If your laptop boot menu does not show the USB drive, format it as FAT32 or use Direct Boot." -ForegroundColor Yellow
} else {
    Write-Host "File system is FAT32 - perfectly compatible with UEFI boot!" -ForegroundColor Green
}

Write-Host "To boot: Restart, tap Esc or F2, and choose your USB drive from the boot menu." -ForegroundColor White
Write-Host ""
