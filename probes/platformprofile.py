# SPDX-License-Identifier: MIT
"""Hardware Platform Profiles for Snapdragon X-series host devices.

Encapsulates SoC-specific, board-specific, and memory-boundary properties,
decoupling the guest kernel profile from fixed machine assumptions.
Supports both the ASUS Zenbook A16 (X2 Elite) and ASUS Vivobook S 15 (X1 Elite).
"""
from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class DisplayGeometry:
    width: int
    height: int
    refresh_rate: int
    stride_bytes: int
    depth_bpp: int = 32
    dpu_intf_index: int = 5

    @property
    def fb_bytes(self) -> int:
        return self.stride_bytes * self.height


@dataclass(frozen=True)
class MemoryProfile:
    total_physical_bytes: int
    host_reserve_bytes: int
    guest_default_bytes: int
    gpu_va_bits: int
    stage2_address_bits: int = 36

    @property
    def max_guest_bytes(self) -> int:
        return self.total_physical_bytes - self.host_reserve_bytes


@dataclass(frozen=True)
class GPUProfile:
    name: str
    generation: str          # 'a8xx' or 'a7xx'
    chip_id: int
    firmware_gmu: str
    firmware_sqe: str
    supports_metal_3d: bool
    requires_gop_fallback: bool


@dataclass(frozen=True)
class InputProfile:
    keyboard_model: str
    keyboard_pa: int
    touchpad_model: str
    touchpad_pa: int


@dataclass(frozen=True)
class PlatformProfile:
    id: str
    name: str
    soc_sku: str
    soc_generation: str      # 'X2E' or 'X1E'
    cpu_cores: int
    guest_vcpus: int
    gicd_base: int
    gicr_base: int
    timer_physical_hz: int
    timer_guest_hz: int
    uart_base: int
    display: DisplayGeometry
    memory: MemoryProfile
    gpu: GPUProfile
    input: InputProfile


# Baseline reference target: ASUS Zenbook A16 UX3607OA
PLATFORM_ZENBOOK_A16 = PlatformProfile(
    id='x2e-zenbook-a16',
    name='ASUS Zenbook A16 (UX3607OA)',
    soc_sku='Qualcomm Snapdragon X2 Elite X2E-96-100',
    soc_generation='X2E',
    cpu_cores=12,
    guest_vcpus=6,
    gicd_base=0x17000000,
    gicr_base=0x17080000,
    timer_physical_hz=19_200_000,
    timer_guest_hz=24_000_000,
    uart_base=0x00894000,
    display=DisplayGeometry(
        width=2880,
        height=1800,
        refresh_rate=60,
        stride_bytes=11520,
        depth_bpp=32,
        dpu_intf_index=5,
    ),
    memory=MemoryProfile(
        total_physical_bytes=32 * (1024 ** 3),
        host_reserve_bytes=2 * (1024 ** 3),
        guest_default_bytes=16 * (1024 ** 3),
        gpu_va_bits=34,
        stage2_address_bits=36,
    ),
    gpu=GPUProfile(
        name='Qualcomm Adreno X2-90',
        generation='a8xx',
        chip_id=0x44070041,
        firmware_gmu='gen80100_gmu.bin',
        firmware_sqe='gen80100_sqe.fw',
        supports_metal_3d=True,
        requires_gop_fallback=False,
    ),
    input=InputProfile(
        keyboard_model='ECKB/QTEC0001',
        keyboard_pa=0x0088C000,
        touchpad_model='TCPD/ASUF1209',
        touchpad_pa=0x00B80000,
    ),
)


# New target: ASUS Vivobook S 15 S5507QA (Snapdragon X1 Elite)
PLATFORM_VIVOBOOK_S15 = PlatformProfile(
    id='x1e-vivobook-s15',
    name='ASUS Vivobook S 15 (S5507QA)',
    soc_sku='Qualcomm Snapdragon X Elite X1E-78-100',
    soc_generation='X1E',
    cpu_cores=12,
    guest_vcpus=6,
    gicd_base=0x17000000,
    gicr_base=0x17080000,
    timer_physical_hz=19_200_000,
    timer_guest_hz=24_000_000,
    uart_base=0x00894000,
    display=DisplayGeometry(
        width=2880,
        height=1620,
        refresh_rate=120,
        stride_bytes=11520,
        depth_bpp=32,
        dpu_intf_index=5,
    ),
    memory=MemoryProfile(
        total_physical_bytes=16 * (1024 ** 3),
        host_reserve_bytes=2 * (1024 ** 3),
        guest_default_bytes=8 * (1024 ** 3),  # Conservative 8 GiB for 16 GB hardware
        gpu_va_bits=32,
        stage2_address_bits=36,
    ),
    gpu=GPUProfile(
        name='Qualcomm Adreno X1-85',
        generation='a7xx',
        chip_id=0x43050001,
        firmware_gmu='gen70500_gmu.bin',
        firmware_sqe='gen70500_sqe.fw',
        supports_metal_3d=False,               # A8XX Metal plugin requires A7XX lowerer
        requires_gop_fallback=True,            # Uses verified GOP/BootFramebuffer for UI
    ),
    input=InputProfile(
        keyboard_model='ECKB/QTEC0001',
        keyboard_pa=0x0088C000,
        touchpad_model='ASCE1200/ASUF1209',
        touchpad_pa=0x00B80000,
    ),
)


PLATFORM_VIRTUAL_ARM64 = PlatformProfile(
    id='virtual-arm64',
    name='Standard ARM64 Virtual Machine (QEMU / VirtualBox / VMware)',
    soc_sku='Generic ARM64 Virtual Platform (Virt)',
    soc_generation='VIRT',
    cpu_cores=8,
    guest_vcpus=6,
    gicd_base=0x08000000,
    gicr_base=0x080A0000,
    timer_physical_hz=24_000_000,
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
        total_physical_bytes=8 * (1024 ** 3),
        host_reserve_bytes=1 * (1024 ** 3),
        guest_default_bytes=6 * (1024 ** 3),
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
        requires_gop_fallback=True,
    ),
    input=InputProfile(
        keyboard_model='USB-KBD/VirtIO',
        keyboard_pa=0x00000000,
        touchpad_model='USB-Tablet/VirtIO',
        touchpad_pa=0x00000000,
    ),
)


PLATFORMS: Dict[str, PlatformProfile] = {
    PLATFORM_ZENBOOK_A16.id: PLATFORM_ZENBOOK_A16,
    PLATFORM_VIVOBOOK_S15.id: PLATFORM_VIVOBOOK_S15,
    PLATFORM_VIRTUAL_ARM64.id: PLATFORM_VIRTUAL_ARM64,
    # Aliases
    'a16': PLATFORM_ZENBOOK_A16,
    'x2e': PLATFORM_ZENBOOK_A16,
    's15': PLATFORM_VIVOBOOK_S15,
    'x1e': PLATFORM_VIVOBOOK_S15,
    'vivobook': PLATFORM_VIVOBOOK_S15,
    'virtual': PLATFORM_VIRTUAL_ARM64,
    'vm': PLATFORM_VIRTUAL_ARM64,
    'qemu': PLATFORM_VIRTUAL_ARM64,
    'vbox': PLATFORM_VIRTUAL_ARM64,
    'virtualbox': PLATFORM_VIRTUAL_ARM64,
}


def get_platform_profile(name_or_alias: str) -> PlatformProfile:
    key = name_or_alias.strip().lower()
    if key in PLATFORMS:
        return PLATFORMS[key]
    raise ValueError(f'Unknown platform profile {name_or_alias!r}. Available: '
                     f'{", ".join(sorted(set(p.id for p in PLATFORMS.values())))}')


def detect_host_platform() -> PlatformProfile:
    """Detect current host hardware environment on Windows or fallback to default."""
    import sys
    if sys.platform == 'win32':
        try:
            import subprocess
            out = subprocess.check_output(
                ['powershell', '-Command', '(Get-CimInstance Win32_ComputerSystem).Model'],
                text=True, stderr=subprocess.DEVNULL
            ).strip()
            if 'S5507' in out or 'Vivobook' in out:
                return PLATFORM_VIVOBOOK_S15
            if 'UX3607' in out or 'Zenbook' in out:
                return PLATFORM_ZENBOOK_A16
        except Exception:
            pass
    return PLATFORM_VIVOBOOK_S15
