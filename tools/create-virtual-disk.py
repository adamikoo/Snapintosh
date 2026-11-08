#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""CLI tool for creating and managing Snapintosh dedicated virtual disks."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from platforms.virtual.storage import VirtualDiskManager, DiskFormat, DiskMode


def main():
    parser = argparse.ArgumentParser(description="Create and manage Snapintosh dedicated virtual disks.")
    sub = parser.add_subparsers(dest='command', required=True)

    # create
    create_p = sub.add_parser('create', help="Create a new virtual disk")
    create_p.add_argument('path', type=Path, help="Target virtual disk file path")
    create_p.add_argument('--size-gb', type=int, default=64, help="Capacity in GiB (default: 64)")
    create_p.add_argument('--format', choices=['qcow2', 'vdi', 'vmdk', 'raw'], default='qcow2',
                          help="Virtual disk format (default: qcow2)")

    # inspect
    inspect_p = sub.add_parser('inspect', help="Inspect an existing virtual disk")
    inspect_p.add_argument('path', type=Path, help="Virtual disk file path")

    # overlay
    overlay_p = sub.add_parser('overlay', help="Create a disposable copy-on-write overlay")
    overlay_p.add_argument('base', type=Path, help="Base virtual disk path")
    overlay_p.add_argument('overlay', type=Path, help="Disposable overlay file path")

    args = parser.parse_args()

    if args.command == 'create':
        fmt = DiskFormat(args.format)
        meta = VirtualDiskManager.create_disk(
            args.path,
            capacity_bytes=args.size_gb * (1024 ** 3),
            disk_format=fmt,
            sparse=True
        )
        print(f"[+] Created {meta.format.value.upper()} disk: {meta.path}")
        print(f"    Virtual Capacity: {meta.capacity_bytes / (1024**3):.1f} GiB")
        print(f"    Host Footprint:   {meta.actual_file_bytes / 1024:.1f} KiB (sparse)")
        print(f"    Sector Size:      {meta.sector_size} bytes (Apple 4K LBA standard)")

    elif args.command == 'inspect':
        meta = VirtualDiskManager.validate_disk(args.path)
        print(f"[+] Virtual Disk Information: {meta.path}")
        print(f"    Format:           {meta.format.value.upper()}")
        print(f"    Virtual Capacity: {meta.capacity_bytes / (1024**3):.1f} GiB")
        print(f"    Host Footprint:   {meta.actual_file_bytes / (1024*1024):.2f} MiB")
        print(f"    Mode:             {meta.mode.value}")

    elif args.command == 'overlay':
        meta = VirtualDiskManager.create_disposable_overlay(args.base, args.overlay)
        print(f"[+] Created disposable overlay: {meta.path}")
        print(f"    Backing file:     {args.base.resolve()}")
        print(f"    Virtual Capacity: {meta.capacity_bytes / (1024**3):.1f} GiB")
        print(f"    Mode:             DISPOSABLE (guest changes will not touch base disk)")


if __name__ == '__main__':
    main()
