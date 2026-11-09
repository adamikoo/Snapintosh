# SPDX-License-Identifier: MIT
"""Virtual machine platform profile for conventional ARM64 hypervisors.

Defines a standardized ARM64 virtual hardware specification compatible with
QEMU virt board, Oracle VirtualBox 7.x, and VMware ARM64 platforms.
"""
from dataclasses import dataclass
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'probes'))

from platformprofile import (
    PlatformProfile, DisplayGeometry, MemoryProfile, GPUProfile, InputProfile
)

# Standard ARM64 Virtual Machine Profile:
# DRAM Base: 0x40000000 (1 GiB)
# Standard Virt GICv3: GICD 0x08000000, GICR 0x080A0000
# Standard Virt PL011 UART: 0x09000000
# Virtual Display: 1920x1080 @ 60 Hz 32 bpp (RAMFB / GOP)
PLATFORM_VIRTUAL_ARM64 = PlatformProfile(
    id='virtual-arm64',
    name='Standard ARM64 Virtual Machine (QEMU / VirtualBox / VMware)',
    soc_sku='Generic ARM64 Virtual Platform (QEMU virt / VirtualBox VM)',
    soc_generation='VIRT',
    cpu_cores=8,
    guest_vcpus=6,
    gicd_base=0x08000000,
    gicr_base=0x080A0000,
    timer_physical_hz=24_000_000,   # Virtual timer matched 1:1 with Apple guest timebase
    timer_guest_hz=24_000_000,
    uart_base=0x09000000,
    display=DisplayGeometry(
        width=1920,
        height=1080,
        refresh_rate=60,
        stride_bytes=1920 * 4,
        depth_bpp=32,
        dpu_intf_index=0,
    ),
    memory=MemoryProfile(
        total_physical_bytes=8 * (1024 ** 3),    # 8 GiB virtual RAM assigned to VM
        host_reserve_bytes=1 * (1024 ** 3),     # 1 GiB reserved for virtual firmware
        guest_default_bytes=6 * (1024 ** 3),    # 6 GiB allocated to macOS guest
        gpu_va_bits=32,
        stage2_address_bits=36,
    ),
    gpu=GPUProfile(
        name='Standard Virtual Framebuffer (RAMFB / GOP)',
        generation='virt',
        chip_id=0x00000000,
        firmware_gmu='',
        firmware_sqe='',
        supports_metal_3d=False,
        requires_gop_fallback=True,            # Uses linear frame buffer for boot & desktop UI
    ),
    input=InputProfile(
        keyboard_model='USB-KBD/VirtIO',
        keyboard_pa=0x00000000,
        touchpad_model='USB-Tablet/VirtIO',
        touchpad_pa=0x00000000,
    ),
)


@dataclass(frozen=True)
class VirtualMachineSpecs:
    dram_base: int = 0x40000000
    guest_memory_bytes: int = 6 * (1024 ** 3)
    vcpu_count: int = 6
    gic_version: int = 3
    gicd_base: int = 0x08000000
    gicr_base: int = 0x080A0000
    uart_base: int = 0x09000000
    ramfb_base: int = 0x7E000000
    framebuffer_width: int = 1920
    framebuffer_height: int = 1080
    framebuffer_stride: int = 7680
    disk_format: str = 'qcow2'
    disk_capacity_bytes: int = 64 * (1024 ** 3)


VIRTUAL_MACHINE_SPECS = VirtualMachineSpecs()
