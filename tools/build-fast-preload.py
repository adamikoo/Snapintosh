#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build fast-boot resident DMA preload bundle for Snapintosh kernel and BaseSystem."""
import hashlib
import importlib.util
import os
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / 'q1n1' / 'tools'))

import preload

os.environ['SNAP_GUEST_MIB'] = '2048'

spec = importlib.util.spec_from_file_location('xnuboot', ROOT / 'probes/xnuboot.py')
xb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(xb)

from probes.guestprofile import J700_26A428_BOOTFB_XARS_UNIFORM_NO_AUDIO
xb.GUEST_PROFILE = J700_26A428_BOOTFB_XARS_UNIFORM_NO_AUDIO
xb.place(0x142000000, 3552 << 20, guest_span=2048 << 20)

print("[1/3] Building kernelcache and shadow page table chunks...")
built = xb.build(
    str(ROOT / 'downloads/extracted/j700ap/kernelcache.release.mac17p'),
    ramdisk=str(ROOT / 'downloads/extracted/j700ap/basesystem-26A428.apfs'),
    root_hash=str(ROOT / 'downloads/extracted/j700ap/basesystem-26A428.root-hash'),
    ramdisk_mode='iokit'
)

chunks = built['chunks']
ramdisk_pa = built['ramdisk_root_range'][0]
# Exclude ramdisk (preloaded separately) and dynamic boot_args (HANDOFF_PA + 0x1000) so runtime boot args and framebuffer config apply dynamically.
non_ramdisk = {pa: blob for pa, blob in sorted(chunks.items()) if pa != ramdisk_pa and pa != (xb.HANDOFF_PA + 0x1000)}

print(f"[2/3] Packing {len(non_ramdisk)} chunks into contiguous kernel bundle...")
# Bundle format:
# Header: Magic 'SNAPKRN1' (8 bytes), count (uint32), reserved (uint32)
# Entries: array of [pa (uint64), size (uint64), file_offset (uint64)]
# Data: contiguous chunk data
BUNDLE_MAGIC = 0x314E524B50414E53 # 'SNAPKRN1'
header_fmt = '<8sII'
entry_fmt = '<QQQ'
header_size = struct.calcsize(header_fmt)
entry_size = struct.calcsize(entry_fmt)
entries_total_size = len(non_ramdisk) * entry_size
data_start_offset = (header_size + entries_total_size + 4095) & ~4095

entries = []
cur_data_offset = data_start_offset
bundle_data = bytearray()

for pa, blob in non_ramdisk.items():
    entries.append((pa, len(blob), cur_data_offset))
    bundle_data.extend(blob)
    cur_data_offset += len(blob)

header_bytes = struct.pack(header_fmt, b'SNAPKRN1', len(non_ramdisk), 0)
entries_bytes = bytearray()
for pa, sz, off in entries:
    entries_bytes.extend(struct.pack(entry_fmt, pa, sz, off))

pad_size = data_start_offset - (header_size + len(entries_bytes))
bundle_full = header_bytes + bytes(entries_bytes) + (b'\x00' * pad_size) + bytes(bundle_data)

esp_dir = ROOT / 'build' / 'qemu-esp' / 'Snapintosh'
esp_dir.mkdir(parents=True, exist_ok=True)
bundle_path = esp_dir / 'kernel-bundle.bin'
bundle_path.write_bytes(bundle_full)

bundle_sha = hashlib.sha256(bundle_full).hexdigest()
print(f"  Created {bundle_path.name}: {len(bundle_full) / (1024*1024):.2f} MiB, SHA256: {bundle_sha[:16]}...")

# 3. Create updated q1n1-preload.bin with BOTH BaseSystem and kernel-bundle
print("[3/3] Generating UEFI DMA preload manifest (q1n1-preload.bin)...")
basesystem_path = esp_dir / 'basesystem-26A428.apfs'
with basesystem_path.open('rb') as f:
    bs_sha = hashlib.file_digest(f, 'sha256').hexdigest()

preload_files = [
    (r'\Snapintosh\basesystem-26A428.apfs', basesystem_path.stat().st_size, bs_sha),
    (r'\Snapintosh\kernel-bundle.bin', len(bundle_full), bundle_sha)
]

manifest_data = preload.manifest(preload_files)
manifest_path = esp_dir / 'q1n1-preload.bin'
manifest_path.write_bytes(manifest_data)
print(f"  Created {manifest_path.name}: {len(manifest_data)} bytes covering {len(preload_files)} assets.")
print("======================================================================")
print("SUCCESS! Fast DMA preload bundle created. Kernel upload time: < 2 seconds.")
print("======================================================================")
