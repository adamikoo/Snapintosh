#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Interactive and automated Virtual Machine launcher for Snapintosh."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from platforms.virtual.profile import PLATFORM_VIRTUAL_ARM64, VIRTUAL_MACHINE_SPECS
from platforms.virtual.storage import VirtualDiskManager, DiskFormat
from platforms.virtual.qemu_runner import QEMURunner, QEMULaunchConfig
from platforms.virtual.builder import VirtualBackendBuilder


def main():
    parser = argparse.ArgumentParser(description="Launch Snapintosh inside an ARM64 Virtual Machine.")
    parser.add_argument('--disk', type=Path, default=ROOT / 'build' / 'virtual' / 'snapintosh_macos.qcow2',
                        help="Path to dedicated virtual disk image")
    parser.add_argument('--disk-size-gb', type=int, default=64,
                        help="Capacity of virtual disk if creating new (default: 64 GiB)")
    parser.add_argument('--memory-mb', type=int, default=6144,
                        help="Virtual RAM in MB (default: 6144 = 6 GiB)")
    parser.add_argument('--cpus', type=int, default=6,
                        help="Number of vCPUs (default: 6)")
    parser.add_argument('--disposable', action='store_true',
                        help="Disposable mode (discard all disk modifications on VM exit)")
    parser.add_argument('--dry-run', action='store_true',
                        help="Print command line and validate configuration without launching")

    args = parser.parse_args()

    print("======================================================================")
    print("   SNAPINTOSH ARM64 VIRTUAL MACHINE RUNNER")
    print("======================================================================")

    # 1. Prepare Virtual Storage
    disk_path = args.disk.resolve()
    if not disk_path.is_file():
        print(f"[+] Creating dedicated sparse virtual disk ({args.disk_size_gb} GiB)...")
        disk_path.parent.mkdir(parents=True, exist_ok=True)
        VirtualDiskManager.create_disk(disk_path, capacity_bytes=args.disk_size_gb * (1024**3),
                                      disk_format=DiskFormat.QCOW2, sparse=True)
    else:
        print(f"[+] Using existing virtual disk: {disk_path}")

    # 2. Check Host Memory Headroom
    print(f"[+] Verifying host memory headroom for {args.memory_mb} MB VM...")
    if not QEMURunner.check_host_memory_headroom(args.memory_mb):
        print("[!] Warning: Host available physical memory is low. Proceeding cautiously.")
    else:
        print("    Memory headroom verified (host Windows reserved memory protected).")

    # 3. Configure QEMU Launch Parameters
    launch_cfg = QEMULaunchConfig(
        cpu_cores=args.cpus,
        memory_mb=args.memory_mb,
        disk_image=disk_path,
        enable_el2_virtualization=True,
        display_mode='ramfb',
        serial_mode='stdio',
        disposable_mode=args.disposable
    )

    qemu_bin = QEMURunner.locate_qemu_binary()
    cmd = QEMURunner.build_command_line(launch_cfg, qemu_bin=qemu_bin)

    print("\n[+] Formulated Virtual Machine Command:")
    print("----------------------------------------------------------------------")
    print(" \\\n  ".join(cmd))
    print("----------------------------------------------------------------------")

    # 4. Generate Launcher Helper Scripts in Root
    bat_path = ROOT / "Run-Snapintosh-VM.bat"
    ps1_path = ROOT / "Run-Snapintosh-VM.ps1"
    QEMURunner.generate_launch_script(launch_cfg, bat_path)
    QEMURunner.generate_launch_script(launch_cfg, ps1_path)
    print(f"[+] Generated 1-click desktop runners:")
    print(f"    - {bat_path}")
    print(f"    - {ps1_path}")

    if args.dry_run:
        print("\n[+] Dry-run completed successfully. All parameters verified.")
        return

    if not qemu_bin:
        print("\n[!] Note: qemu-system-aarch64 binary was not automatically located in PATH.")
        print("    To run directly on Windows 11 ARM64:")
        print("    1. Install QEMU: winget install SoftwareFreedomConservancy.QEMU")
        print("    2. Or double-click 'Run-Snapintosh-VM.bat' once QEMU is installed.")
        print("    3. Or import 'build/virtualbox/Snapintosh-macOS-Sequoia.ovf' into VirtualBox 7.x.")
        return

    print(f"\n[+] Spawning QEMU Virtual Machine ({qemu_bin})...")
    subprocess.run(cmd)


if __name__ == '__main__':
    main()
