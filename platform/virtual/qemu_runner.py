# SPDX-License-Identifier: MIT
"""QEMU ARM64 system emulation runner for Snapintosh.

Formulates and executes QEMU virtual machine instances with architectural EL2,
FEAT_NV2, pointer authentication, and virtual hardware devices.
"""
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import List, Optional, Dict, Any


@dataclass(frozen=True)
class QEMULaunchConfig:
    cpu_cores: int = 6
    memory_mb: int = 6144               # 6 GiB RAM
    disk_image: Optional[Path] = None
    kernel_image: Optional[Path] = None
    firmware_path: Optional[Path] = None
    enable_el2_virtualization: bool = True
    display_mode: str = 'ramfb'          # 'ramfb', 'gtk', or 'default'
    accel: str = 'tcg'                   # 'tcg,thread=multi' or 'whpx'
    serial_mode: str = 'stdio'
    disposable_mode: bool = False


class QEMURunner:
    """Manages execution of Snapintosh under QEMU system emulation on Windows ARM64."""

    COMMON_QEMU_PATHS = [
        Path(r"C:\Program Files\qemu\qemu-system-aarch64.exe"),
        Path(r"C:\Program Files (x86)\qemu\qemu-system-aarch64.exe"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "qemu" / "qemu-system-aarch64.exe",
    ]

    @classmethod
    def locate_qemu_binary(cls) -> Optional[Path]:
        """Searches system PATH and standard directories for qemu-system-aarch64."""
        which_path = shutil.which("qemu-system-aarch64")
        if which_path:
            return Path(which_path)
        for cand in cls.COMMON_QEMU_PATHS:
            if cand.is_file():
                return cand
        return None

    @classmethod
    def check_host_memory_headroom(cls, requested_mb: int) -> bool:
        """Verifies that requested VM memory does not exhaust host physical RAM."""
        try:
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                avail_mb = stat.ullAvailPhys // (1024 * 1024)
                # Ensure at least 1500 MB remains for host Windows
                return (avail_mb - requested_mb) >= 1500
        except Exception:
            pass
        return True

    @classmethod
    def build_command_line(cls, config: QEMULaunchConfig,
                           qemu_bin: Optional[Path] = None) -> List[str]:
        """Constructs the exact QEMU invocation parameter list."""
        bin_str = str(qemu_bin) if qemu_bin else "qemu-system-aarch64"
        cmd = [bin_str]

        # Machine model: ARM virt with architectural virtualization (EL2) and GICv3
        if config.enable_el2_virtualization:
            cmd.extend(["-machine", "virt,virtualization=on,gic-version=3"])
            cmd.extend(["-cpu", "max,pauth-impdef=on"])
        else:
            cmd.extend(["-machine", "virt,gic-version=3"])
            cmd.extend(["-cpu", "cortex-a76"])

        # CPU topology & Memory
        cmd.extend(["-smp", f"cores={config.cpu_cores},threads=1,sockets=1"])
        cmd.extend(["-m", f"{config.memory_mb}M"])

        # Acceleration
        if config.accel.startswith('tcg'):
            cmd.extend(["-accel", "tcg,thread=multi"])
        else:
            cmd.extend(["-accel", config.accel])

        # Firmware / BIOS
        if config.firmware_path and config.firmware_path.is_file():
            cmd.extend(["-bios", str(config.firmware_path)])

        # Linear Framebuffer Display
        if config.display_mode == 'ramfb':
            cmd.extend(["-device", "ramfb"])

        # Input devices (USB Tablet & Keyboard)
        cmd.extend(["-device", "qemu-xhci,id=xhci0"])
        cmd.extend(["-device", "usb-tablet,bus=xhci0.0"])
        cmd.extend(["-device", "usb-kbd,bus=xhci0.0"])

        # Diagnostic serial console
        if config.serial_mode:
            cmd.extend(["-serial", config.serial_mode])

        # Dedicated Virtual Disk Storage
        if config.disk_image and config.disk_image.is_file():
            disk_fmt = "qcow2" if config.disk_image.suffix.lower() == '.qcow2' else "raw"
            snap_flag = ",snapshot=on" if config.disposable_mode else ""
            cmd.extend([
                "-drive",
                f"file={config.disk_image},format={disk_fmt},if=none,id=disk0{snap_flag}",
                "-device",
                "nvme,serial=SNAPANS001,drive=disk0"
            ])

        # Guest Kernel / Standalone Blob (if direct kernel boot)
        if config.kernel_image and config.kernel_image.is_file():
            cmd.extend(["-kernel", str(config.kernel_image)])

        return cmd

    @classmethod
    def generate_launch_script(cls, config: QEMULaunchConfig, script_path: Path) -> Path:
        """Generates a standalone .bat or .ps1 launcher script for Windows."""
        cmd = cls.build_command_line(config)
        script_path.parent.mkdir(parents=True, exist_ok=True)
        is_ps1 = script_path.suffix.lower() == '.ps1'

        if is_ps1:
            content = f"""# Auto-generated Snapintosh Virtual Machine Launcher
$ErrorActionPreference = 'Stop'
Write-Host '===================================================' -ForegroundColor Cyan
Write-Host '   Snapintosh macOS ARM64 Virtual Machine Runner   ' -ForegroundColor Cyan
Write-Host '===================================================' -ForegroundColor Cyan

$qemuCmd = @(
{chr(10).join(f'    "{arg}"' for arg in cmd[1:])}
)

& "{cmd[0]}" @qemuCmd
"""
        else:
            content = f"""@echo off
rem Auto-generated Snapintosh Virtual Machine Launcher
echo ===================================================
echo    Snapintosh macOS ARM64 Virtual Machine Runner   
echo ===================================================

"{cmd[0]}" ^
  {" ^\n  ".join(cmd[1:])}

pause
"""
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return script_path
