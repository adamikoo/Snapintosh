#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Export the complete macOS guest image and xnuboot monitor for standalone booting."""
import os
import shutil
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'probes'))
sys.path.insert(0, str(ROOT / 'tools'))

from dataclasses import replace
import xnuboot as xb
import run

print("=== Building xnuboot.bin Hypervisor Monitor ===")
build_dir = ROOT / 'build' / 'standalone'
build_dir.mkdir(parents=True, exist_ok=True)
run.FLAGS.append('-DSNAP_SPMI_SCRATCH=1')
xnuboot_blob = run.build('xnuboot', build_dir)
print(f"Built xnuboot.bin: {len(xnuboot_blob)} bytes")

print("\n=== Building XNU Address Space and Memory Chunks ===")
kernel_path = ROOT / 'downloads' / 'extracted' / 'j700ap' / 'kernelcache.release.mac17p'
firmware_dir = ROOT / 'downloads' / 'extracted' / 'j700ap'
ramdisk_path = ROOT / 'downloads' / 'extracted' / 'j700ap' / 'basesystem-26A428.apfs'
root_hash_path = ROOT / 'downloads' / 'extracted' / 'j700ap' / 'basesystem-26A428.root-hash'

# Configure base guest profile with bootfb, uniform clusters, and deferred audio:
xb.configure_guest('j700ap-26A428-bootfb-xars-uniform-no-audio', directory=str(firmware_dir))

# Bind BaseSystem SHA256 root hash and enable SPMI PMU RTC:
spec = replace(
    xb.GUEST_PROFILE.root_hash,
    image_sha256='7aacbbefadf4adcf830f72cd077b48e8a705a58636f177bba0efbabaf3910c2c'
)
xb.GUEST_PROFILE = replace(
    xb.GUEST_PROFILE,
    root_hash=spec,
    trust_cache=None,
    spmi_boot=tuple(replace(s, rtc=True) if s.node == '/device-tree/arm-io/nub-spmi0' else s
                    for s in xb.GUEST_PROFILE.spmi_boot)
)

# Configure placement for ASUS Vivobook S 15:
# High RAM: 3.3 GB available starting at 0x880000000
phys_base = 0x880000000
guest_span = 2048 << 20
total_span = 2560 << 20
xb.place(phys_base, total_span, guest_span)

# Framebuffer & Console:
# 2880x1620 OLED, base 0xe4800000, 32 bpp, stride 11520 bytes
xb.FRAMEBUFFER = (0xe4800000, 2880, 1620, 2880 * 4, 32)
xb.BOOT_CMDLINE = '-v debug=0x8 serial=2 cluster_power=0 wdt=-1'

# Build XNU address space with authenticated IOKit APFS root RAMDisk:
built = xb.build(
    str(kernel_path),
    ramdisk=str(ramdisk_path),
    root_hash=str(root_hash_path),
    ramdisk_mode='iokit'
)

# Generous 24h watchdog budget and allow kernel panic reporting:
built['watchdog'] = 86400
built['let_panic'] = True

# Seed virtual UTC epoch if SPMI PMU RTC is enabled:
if any(m.kind == 48 for m in built.get('device_models', ())):
    import time
    from devicemodel import seed_rtc_models
    epoch_us = time.time_ns() // 1000
    built['device_models'] = seed_rtc_models(built['device_models'], epoch_us)
    print(f"[+] Seeded virtual PMU RTC epoch: {epoch_us} us")

chunks = dict(built['chunks'])
for pa, page in built['tables'].chunks():
    chunks[pa] = bytes(page)
chunks[xb.PARAMS_PA] = xb.params_blob(built)

entry_pc = built['entry']
entry_x0 = 0
entry_x1 = built['x1']
entry_x2 = built['x2']
ttbr1_pa = built['tables'].root
params_pa = xb.PARAMS_PA
work_pa = (xb.BOOTSTRAP_PA + xb.BOOTSTRAP_SPAN + 65535) & ~65535
work_size = 64 * 1024 * 1024
out_pa = work_pa + work_size

print(f"Chunks:     {len(chunks)}")
print(f"Total Size: {sum(len(b) for b in chunks.values()) / (1024*1024):.2f} MiB")
print(f"Entry PC:   {entry_pc:#018x}")
print(f"X0:         {entry_x0:#018x}")
print(f"X1:         {entry_x1:#018x}")
print(f"X2:         {entry_x2:#018x}")
print(f"PARAMS_PA:  {params_pa:#018x}")
print(f"WORK_PA:    {work_pa:#018x} ({work_size // (1024*1024)} MiB)")
print(f"OUT_PA:     {out_pa:#018x}")
print(f"TTBR1:      {ttbr1_pa:#018x}")

# Write to USB E:\Snapintosh\
usb_dir = Path("E:/Snapintosh")
usb_dir.mkdir(parents=True, exist_ok=True)

# 1. Write xnuboot.bin
xnuboot_dest = usb_dir / "xnuboot.bin"
xnuboot_dest.write_bytes(xnuboot_blob)
print(f"\n[+] Saved {len(xnuboot_blob)} bytes to {xnuboot_dest}")

# 2. Write guest_image.bin
image_dest = usb_dir / "guest_image.bin"
print(f"[+] Writing guest image to {image_dest}...")

with open(image_dest, 'wb') as f:
    magic = b"SNAPBOOT"
    version = 1
    flags = 0
    num_chunks = len(chunks)
    f.write(struct.pack("<8sIIQQQQQQQQQQ",
        magic,
        version,
        flags,
        num_chunks,
        entry_pc,
        entry_x0,
        entry_x1,
        entry_x2,
        params_pa,
        work_pa,
        work_size,
        out_pa,
        ttbr1_pa,
    ))
    
    # Chunks
    for pa, data in sorted(chunks.items()):
        f.write(struct.pack("<QQ", pa, len(data)))
        f.write(data)

file_size = image_dest.stat().st_size
print(f"[+] SUCCESS! Wrote {file_size / (1024*1024):.2f} MiB to {image_dest}")
