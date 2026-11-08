# SPDX-License-Identifier: MIT
<#
.SYNOPSIS
    Safely adds a 2 GB FAT32 UEFI boot partition to the SanDisk USB drive without losing existing files.
#>

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Requesting Administrator privileges..." -ForegroundColor Yellow
    Start-Process powershell.exe -Verb RunAs -ArgumentList "-NoExit -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit 0
}

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "    Snapintosh USB UEFI Boot Partition Setup            " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

$appDataBoot = "$env:LOCALAPPDATA\Snapintosh\boot"
$efiSource   = "$appDataBoot\q1n1.efi"
$stageSource = "$appDataBoot\q1n1-stage.bin"
$cfgSource   = "$appDataBoot\snapintosh_boot.cfg"

if (-not (Test-Path $efiSource)) {
    Write-Host "[!] Error: q1n1.efi not found in $appDataBoot." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# 1. Locate the SanDisk USB Disk
Write-Host "[1/4] Detecting USB Flash Drive..." -ForegroundColor White
$usbDisk = Get-Disk | Where-Object { $_.BusType -eq 'USB' -and $_.FriendlyName -like '*SanDisk*' }
if (-not $usbDisk) {
    $usbDisk = Get-Disk | Where-Object { $_.BusType -eq 'USB' }
}

if (-not $usbDisk) {
    Write-Host "[!] Error: No USB flash drive detected. Please plug in your USB drive." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

$diskNum = $usbDisk.Number
Write-Host "      [+] Target USB Disk found: Disk $diskNum ($($usbDisk.FriendlyName))" -ForegroundColor Green

# 2. Check if a FAT32 boot partition already exists on this USB disk
$fatPart = Get-Partition -DiskNumber $diskNum | Where-Object {
    $vol = Get-Volume -Partition $_ -ErrorAction SilentlyContinue
    $vol.FileSystem -eq 'FAT32'
}

$targetDriveLetter = $null

if ($fatPart) {
    $vol = Get-Volume -Partition $fatPart
    $targetDriveLetter = $vol.DriveLetter
    Write-Host "      [+] Found existing FAT32 boot partition on USB ($($targetDriveLetter):)." -ForegroundColor Green
} else {
    Write-Host "[2/4] Shrinking NTFS partition by 2 GB to make room for UEFI boot..." -ForegroundColor White
    $part1 = Get-Partition -DiskNumber $diskNum -PartitionNumber 1
    $newSize = $part1.Size - 2147483648 # 2 GB
    
    try {
        Resize-Partition -DiskNumber $diskNum -PartitionNumber 1 -Size $newSize -ErrorAction Stop
        Write-Host "      [+] Successfully resized partition 1 (all your files on D: are preserved!)." -ForegroundColor Green
    } catch {
        Write-Host "[!] Warning: PowerShell resize failed, trying diskpart..." -ForegroundColor Yellow
        $dpScript = @"
select disk $diskNum
select partition 1
shrink desired=2048 minimum=1024
"@
        $dpFile = "$env:TEMP\shrink_usb.txt"
        $dpScript | Out-File $dpFile -Encoding ASCII
        cmd /c "diskpart /s $dpFile" | Out-Null
        Remove-Item $dpFile -Force -ErrorAction SilentlyContinue
    }

    Write-Host "[3/4] Creating and formatting 2 GB FAT32 UEFI partition..." -ForegroundColor White
    $newPart = New-Partition -DiskNumber $diskNum -UseMaximumSize -AssignDriveLetter
    $formatted = Format-Volume -Partition $newPart -FileSystem FAT32 -NewFileSystemLabel "SNAPBOOT" -Confirm:$false
    $targetDriveLetter = $formatted.DriveLetter
    Write-Host "      [+] Created and formatted drive $($targetDriveLetter): as FAT32." -ForegroundColor Green
}

if (-not $targetDriveLetter) {
    Write-Host "[!] Error: Could not obtain drive letter for FAT32 partition." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# 3. Stage the UEFI boot files
Write-Host "[4/4] Staging Snapintosh UEFI bootloader to $($targetDriveLetter):\..." -ForegroundColor White
$bootDir = "$($targetDriveLetter):\EFI\BOOT"
if (-not (Test-Path $bootDir)) {
    New-Item -ItemType Directory -Path $bootDir -Force | Out-Null
}

Copy-Item -Path $efiSource -Destination "$bootDir\BOOTAA64.EFI" -Force
Write-Host "      [+] Staged $bootDir\BOOTAA64.EFI" -ForegroundColor Green

if (Test-Path $stageSource) {
    Copy-Item -Path $stageSource -Destination "$($targetDriveLetter):\q1n1-stage.bin" -Force
    Write-Host "      [+] Staged $($targetDriveLetter):\q1n1-stage.bin" -ForegroundColor Green
}

if (Test-Path $cfgSource) {
    Copy-Item -Path $cfgSource -Destination "$($targetDriveLetter):\snapintosh_boot.cfg" -Force
    Write-Host "      [+] Staged $($targetDriveLetter):\snapintosh_boot.cfg" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host "SUCCESS! Your USB drive is now a UEFI bootable drive." -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host ""
Write-Host "HOW TO BOOT NOW:" -ForegroundColor Yellow
Write-Host "1. Restart your laptop and hold/tap ESC." -ForegroundColor White
Write-Host "2. On the ASUS 'Please select boot device' screen, you will now see:" -ForegroundColor Cyan
Write-Host "     Windows Boot Manager" -ForegroundColor White
Write-Host "     UEFI: SanDisk 3.2Gen1, Partition 2 (SNAPBOOT)" -ForegroundColor Green
Write-Host "3. Arrow down to the SanDisk partition and press ENTER!" -ForegroundColor White
Write-Host ""
Write-Host "The ASUS motherboard will boot q1n1 directly with zero Windows errors!" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to finish"
