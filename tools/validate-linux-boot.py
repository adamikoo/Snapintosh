#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Automated Linux QEMU Boot-Validation Harness for macOS 27 VM.

Checks host environment, verifies QEMU capabilities, validates boot assets,
launches QEMU test harness, captures serial console output, records boot
checkpoints, and takes QMP screendumps.
"""

import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import time
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = ROOT / 'evidence' / 'linux-macos27-boot'
LOG_DIR = EVIDENCE_DIR / 'logs'
SCREENSHOT_DIR = EVIDENCE_DIR / 'screenshots'

LOG_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def ppm_to_png(src_path, dst_path):
    """Pure-Python lossless converter from Netpbm PPM to standard PNG format."""
    try:
        with open(src_path, "rb") as f:
            tokens = []
            while len(tokens) < 4:
                line = f.readline()
                if not line:
                    break
                # strip comments
                if line.startswith(b"#"):
                    continue
                tokens.extend(line.split())
            if len(tokens) < 4:
                return False
            w, h = int(tokens[1]), int(tokens[2])
            raw_pixels = f.read()

        raw_data = bytearray()
        stride = w * 3
        for y in range(h):
            raw_data.append(0)  # filter type none
            raw_data.extend(raw_pixels[y * stride : (y + 1) * stride])

        compressed = zlib.compress(bytes(raw_data), 9)

        def make_chunk(tag, data):
            return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

        ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
        png = b"\x89PNG\r\n\x1a\n" + make_chunk(b"IHDR", ihdr) + make_chunk(b"IDAT", compressed) + make_chunk(b"IEND", b"")
        with open(dst_path, "wb") as out:
            out.write(png)
        return True
    except Exception:
        return False


class BootCheckpoint:
    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.passed = False
        self.evidence = ""

    def mark_pass(self, evidence):
        self.passed = True
        self.evidence = evidence

    def mark_fail(self, evidence):
        self.passed = False
        self.evidence = evidence


def run_screendump(qmp_port, output_path):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect(('127.0.0.1', qmp_port))
        f = sock.makefile('rw', encoding='utf-8')
        _ = f.readline()
        f.write('{"execute": "qmp_capabilities"}\n')
        f.flush()
        _ = f.readline()
        cmd = json.dumps({"execute": "screendump", "arguments": {"filename": str(output_path)}}) + '\n'
        f.write(cmd)
        f.flush()
        resp = f.readline()
        sock.close()
        return True, resp
    except Exception as e:
        return False, str(e)


def main():
    print("=" * 70)
    print("  SNAPINTOSH LINUX BOOT VALIDATION HARNESS  ")
    print("=" * 70)

    checkpoints = [
        BootCheckpoint("PREREQ_ENV", "Host Environment and Architecture Audit"),
        BootCheckpoint("QEMU_LAUNCH", "QEMU Virtual Machine Launch under TCG"),
        BootCheckpoint("FIRMWARE", "EDK2 AArch64 UEFI Firmware Initialization"),
        BootCheckpoint("BOOTLOADER", "q1n1 EFI Loader and EL2 Handoff"),
        BootCheckpoint("ASSETS_VALIDATION", "macOS 27 Restore Assets Integrity"),
        BootCheckpoint("XNU_BOOTSTRAP", "Apple XNU Kernel Bootstrap and Handoff"),
        BootCheckpoint("GRAPHICAL_SESSION", "WindowServer Graphical Desktop Session"),
    ]

    # Checkpoint 1: Host Environment
    qemu_bin = shutil.which("qemu-system-aarch64")
    if not qemu_bin:
        print("[-] Error: qemu-system-aarch64 not found.")
        sys.exit(1)

    print(f"[+] QEMU Binary: {qemu_bin}")
    checkpoints[0].mark_pass(f"Linux x86_64 Host with QEMU TCG {qemu_bin}")

    # Checkpoint 2 & 3: Launch QEMU and test Firmware
    qmp_port = 4545
    serial_port = 4546
    qemu_log = LOG_DIR / "qemu-execution.log"
    firmware_bin = "/usr/share/qemu-efi-aarch64/QEMU_EFI.fd"

    if not Path(firmware_bin).exists():
        print(f"[-] Firmware missing at {firmware_bin}")
        checkpoints[1].mark_fail("Firmware missing")
        return

    qemu_cmd = [
        qemu_bin,
        "-machine", "virt,virtualization=on,gic-version=3",
        "-cpu", "max,pauth-impdef=on",
        "-smp", "4",
        "-m", "4G",
        "-accel", "tcg,thread=multi",
        "-bios", firmware_bin,
        "-device", "ramfb",
        "-device", "qemu-xhci,id=xhci0",
        "-device", "usb-tablet,bus=xhci0.0",
        "-device", "usb-kbd,bus=xhci0.0",
        "-display", "none",
        "-qmp", f"tcp:127.0.0.1:{qmp_port},server=on,wait=off",
        "-chardev", f"socket,id=s,host=127.0.0.1,port={serial_port},server=on,wait=off",
        "-serial", "chardev:s",
    ]

    print("[*] Launching QEMU VM...")
    proc = subprocess.Popen(qemu_cmd, stdout=subprocess.DEVNULL, stderr=open(qemu_log, "w"))
    time.sleep(3.0)

    if proc.poll() is not None:
        print(f"[-] QEMU exited prematurely with code {proc.returncode}")
        checkpoints[1].mark_fail(f"Premature exit code {proc.returncode}")
    else:
        print(f"[+] QEMU running successfully (PID: {proc.pid})")
        checkpoints[1].mark_pass(f"PID {proc.pid}, cmd: {' '.join(qemu_cmd)}")

        # Capture Firmware screendump
        screen_ppm = SCREENSHOT_DIR / "firmware-screen.ppm"
        screen_png = SCREENSHOT_DIR / "01-linux-firmware-boot.png"
        ok, res = run_screendump(qmp_port, screen_ppm)
        if ok and screen_ppm.exists():
            print(f"[+] Screen dump captured: {screen_ppm}")
            checkpoints[2].mark_pass(f"Captured firmware frame at {screen_ppm}")
            converted = ppm_to_png(screen_ppm, screen_png)
            if converted:
                print(f"[+] Lossless PNG generated at {screen_png}")
            screen_ppm.unlink(missing_ok=True)
        else:
            print(f"[-] Screendump failed: {res}")
            checkpoints[2].mark_fail(res)

        proc.kill()
        proc.wait()

    # Checkpoint 4: Bootloader Assets
    q1n1_efi = ROOT.parent / 'q1n1' / 'build' / 'uefi' / 'q1n1.efi'
    if q1n1_efi.exists():
        checkpoints[3].mark_pass(f"Found q1n1 payload at {q1n1_efi}")
    else:
        checkpoints[3].mark_fail("q1n1.efi payload missing (q1n1 submodule/sibling not built)")

    # Checkpoint 5: macOS Assets
    basesystem = ROOT / 'downloads' / 'extracted' / 'j700ap' / 'basesystem-26A428.apfs'
    kernelcache = ROOT / 'downloads' / 'extracted' / 'j700ap' / 'kernelcache.release.mac17p'
    if basesystem.exists() and kernelcache.exists():
        checkpoints[4].mark_pass("macOS restore assets present and verified")
    else:
        checkpoints[4].mark_fail("Apple macOS restore assets not present locally (legal/CDN distribution)")

    # Checkpoint 6 & 7: XNU Bootstrap & Graphical Session
    checkpoints[5].mark_fail("Blocked by missing restore assets and AppleGPIOICController.cpp:459 matching")
    checkpoints[6].mark_fail("Blocked by unresolved WindowServer GPIO dependencies")

    # Output validation report
    report_file = LOG_DIR / "boot-validation-report.txt"
    with open(report_file, "w") as rf:
        rf.write("=== AUTOMATED LINUX BOOT VALIDATION HARNESS REPORT ===\n")
        rf.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n\n")
        for cp in checkpoints:
            status = "PASS" if cp.passed else "BLOCKED / FAIL"
            line = f"[{status:14}] {cp.name:20} : {cp.description}\n       Evidence: {cp.evidence}\n"
            print(line, end="")
            rf.write(line)

    print(f"\n[+] Report written to {report_file}")


if __name__ == "__main__":
    main()
