#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Export importable Oracle VirtualBox appliance bundle for Snapintosh."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from platforms.virtual.storage import VirtualDiskManager, DiskFormat
from platforms.virtual.virtualbox_appliance import VirtualBoxConfig, VirtualBoxApplianceBuilder


def main():
    parser = argparse.ArgumentParser(description="Export importable VirtualBox appliance for Snapintosh.")
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'build' / 'virtualbox',
                        help="Target output directory for appliance files")
    parser.add_argument('--disk-size-gb', type=int, default=64,
                        help="Virtual disk capacity in GiB (default: 64)")
    parser.add_argument('--memory-mb', type=int, default=6144,
                        help="Virtual RAM in MB (default: 6144 = 6 GiB)")
    parser.add_argument('--cpus', type=int, default=6,
                        help="Number of vCPUs (default: 6)")

    args = parser.parse_args()
    out_dir = args.output_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    disk_vdi = out_dir / "Snapintosh-Disk.vdi"
    disk_vmdk = out_dir / "Snapintosh-Disk.vmdk"
    vbox_file = out_dir / "Snapintosh-macOS-Sequoia.vbox"
    ovf_file = out_dir / "Snapintosh-macOS-Sequoia.ovf"
    import_bat = out_dir / "Import-To-VirtualBox.bat"

    print("======================================================================")
    print("   SNAPINTOSH VIRTUALBOX 7.x APPLIANCE EXPORTER")
    print("======================================================================")

    # 1. Create sparse VDI
    if not disk_vdi.is_file():
        print(f"[1/4] Creating {args.disk_size_gb} GiB sparse VDI virtual disk...")
        VirtualDiskManager.create_disk(disk_vdi, capacity_bytes=args.disk_size_gb * (1024**3),
                                      disk_format=DiskFormat.VDI, sparse=True)
    else:
        print(f"[1/4] Using existing VDI virtual disk: {disk_vdi.name}")

    # 2. Create sparse VMDK descriptor for OVF
    if not disk_vmdk.is_file():
        VirtualDiskManager.create_disk(disk_vmdk, capacity_bytes=args.disk_size_gb * (1024**3),
                                      disk_format=DiskFormat.VMDK, sparse=True)

    # 3. Generate native .vbox XML
    print("[2/4] Generating native VirtualBox 7.x (.vbox) machine definition...")
    vb_cfg = VirtualBoxConfig(
        vm_name="Snapintosh-macOS-Sequoia",
        cpu_count=args.cpus,
        memory_mb=args.memory_mb,
        firmware="EFI",
        storage_controller="NVMe"
    )
    VirtualBoxApplianceBuilder.generate_vbox_xml(disk_vdi, vbox_file, vb_cfg)

    # 4. Generate Open Virtualization Format (.ovf)
    print("[3/4] Generating Open Virtualization Format (.ovf) appliance descriptor...")
    VirtualBoxApplianceBuilder.generate_ovf_descriptor(disk_vmdk, ovf_file, vb_cfg)

    # 5. Generate 1-click import script
    print("[4/4] Generating automated import script...")
    with open(import_bat, 'w', encoding='utf-8') as f:
        f.write(f"""@echo off
echo ======================================================================
echo    Configuring Snapintosh ARM64 Virtual Machine in VirtualBox
echo ======================================================================

set VBOXMANAGE="C:\\Program Files\\Oracle\\VirtualBox\\VBoxManage.exe"
if not exist %VBOXMANAGE% (
    where VBoxManage >nul 2>nul
    if %errorlevel% equ 0 (
        set VBOXMANAGE=VBoxManage
    ) else (
        echo [!] VBoxManage not found in standard location or PATH.
        pause
        exit /b 1
    )
)

echo [+] Checking for existing machine...
%VBOXMANAGE% unregistervm "Snapintosh-macOS-Sequoia" --delete >nul 2>nul
if exist "%USERPROFILE%\\VirtualBox VMs\\Snapintosh-macOS-Sequoia" rmdir /s /q "%USERPROFILE%\\VirtualBox VMs\\Snapintosh-macOS-Sequoia" >nul 2>nul

echo [+] Creating native ARM64 virtual machine...
%VBOXMANAGE% createvm --name "Snapintosh-macOS-Sequoia" --platform-architecture arm --ostype "Other_arm64" --register
if %errorlevel% neq 0 (
    echo [!] Failed to create ARM VM.
    pause
    exit /b 1
)

echo [+] Configuring ARM hardware (6 vCPUs, {args.memory_mb} MB RAM, EFI, RAMFB display)...
%VBOXMANAGE% modifyvm "Snapintosh-macOS-Sequoia" --memory {args.memory_mb} --cpus {args.cpus} --vram 128 --firmware efi --graphicscontroller qemuramfb --mouse usbtablet --keyboard usb

echo [+] Adding NVMe storage controller...
%VBOXMANAGE% storagectl "Snapintosh-macOS-Sequoia" --name "NVMe" --add pcie --controller NVMe --bootable on

echo [+] Attaching Snapintosh virtual disk ({disk_vmdk.name})...
%VBOXMANAGE% storageattach "Snapintosh-macOS-Sequoia" --storagectl "NVMe" --port 0 --device 0 --type hdd --medium "%~dp0{disk_vmdk.name}"

echo.
echo ======================================================================
echo SUCCESS! Snapintosh is configured as a native ARM VirtualBox VM.
echo Open Oracle VirtualBox and press Start on "Snapintosh-macOS-Sequoia"!
echo ======================================================================
pause
""")

    print("\n======================================================================")
    print("SUCCESS! VirtualBox appliance bundle created successfully.")
    print("======================================================================")
    print(f"Output Directory: {out_dir}")
    print(f"  - Native Machine:  {vbox_file.name}")
    print(f"  - OVF Appliance:   {ovf_file.name}")
    print(f"  - Dedicated Disk:  {disk_vdi.name}")
    print(f"  - Import Helper:   {import_bat.name}")
    print("\nHOW TO USE IN VIRTUALBOX:")
    print("  1. Open VirtualBox 7.x.")
    print(f"  2. Click 'File' -> 'Import Appliance', and choose '{ovf_file.name}'.")
    print("  3. Click Finish and press 'Start' to boot Snapintosh!")


if __name__ == '__main__':
    main()
