#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Export portable VMware virtual machine configuration for Snapintosh."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from platforms.virtual.storage import VirtualDiskManager, DiskFormat
from platforms.virtual.vmware_profile import VMwareProfileBuilder, VMWARE_ASSESSMENTS


def main():
    parser = argparse.ArgumentParser(description="Export portable VMware VM configuration for Snapintosh.")
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'build' / 'vmware',
                        help="Target output directory for VMware files")
    parser.add_argument('--disk-size-gb', type=int, default=64,
                        help="Virtual disk capacity in GiB (default: 64)")
    parser.add_argument('--memory-mb', type=int, default=6144,
                        help="Virtual RAM in MB (default: 6144 = 6 GiB)")
    parser.add_argument('--cpus', type=int, default=6,
                        help="Number of vCPUs (default: 6)")

    args = parser.parse_args()
    out_dir = args.output_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    disk_vmdk = out_dir / "Snapintosh-Disk.vmdk"
    vmx_file = out_dir / "Snapintosh-macOS-Sequoia.vmx"

    print("======================================================================")
    print("   SNAPINTOSH VMWARE PORTABLE PROFILE EXPORTER")
    print("======================================================================")

    # 1. Create sparse VMDK
    if not disk_vmdk.is_file():
        print(f"[1/2] Creating {args.disk_size_gb} GiB sparse VMDK virtual disk...")
        VirtualDiskManager.create_disk(disk_vmdk, capacity_bytes=args.disk_size_gb * (1024**3),
                                      disk_format=DiskFormat.VMDK, sparse=True)
    else:
        print(f"[1/2] Using existing VMDK virtual disk: {disk_vmdk.name}")

    # 2. Generate portable .vmx configuration
    print("[2/2] Generating portable VMware .vmx virtual machine configuration...")
    VMwareProfileBuilder.generate_vmx(
        vmdk_path=disk_vmdk,
        output_vmx_path=vmx_file,
        vm_name="Snapintosh-macOS-Sequoia",
        num_vcpus=args.cpus,
        memory_mb=args.memory_mb
    )

    print("\n======================================================================")
    print("SUCCESS! Portable VMware configuration created.")
    print("======================================================================")
    print(f"Output Directory: {out_dir}")
    print(f"  - VM Definition:   {vmx_file.name}")
    print(f"  - Dedicated Disk:  {disk_vmdk.name}")
    print("\nIMPORTANT COMPATIBILITY NOTE:")
    print("  VMware Workstation Pro on Windows does NOT have an ARM64-native host build.")
    print("  This portable profile is designed to be opened in:")
    print("    - VMware Fusion Pro 13.5+ on Apple Silicon macOS hosts")
    print("    - VMware ESXi-Arm on bare-metal ARM64 enterprise servers")


if __name__ == '__main__':
    main()
