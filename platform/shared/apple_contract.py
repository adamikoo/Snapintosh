# SPDX-License-Identifier: MIT
"""Apple Silicon hardware and software contracts required by stock macOS 27 Sequoia.

These contracts are invariant across execution backends: whether running directly on
physical Qualcomm silicon or inside a conventional virtual machine, the guest
kernel expects these exact semantics.
"""
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class SPTMContract:
    boot_magic: int = 0xD00FCAFEF00D2024
    boot_version: int = 1
    page_granule_bytes: int = 16384     # XNU 16 KiB translation granule
    shadow_granule_bytes: int = 4096   # Hardware MMU 4 KiB granule
    aperture_va_base: int = 0xFFFFFE0100000000
    kernel_text_va: int = 0xFFFFFE0007004000
    sptm_data_va: int = 0xFFFFFE0000000000
    uat_granule_bytes: int = 16384


@dataclass(frozen=True)
class AICContract:
    aic_version: int = 3
    die_count: int = 1
    cluster_count: int = 1
    total_irq_lines: int = 1280
    event_reg_offset: int = 0x0000
    mask_set_offset: int = 0x0004
    mask_clr_offset: int = 0x0008
    timer_fiq_vector: int = 1
    fast_ipi_registers: bool = True


@dataclass(frozen=True)
class TimebaseContract:
    guest_counter_hz: int = 24_000_000   # Apple Silicon 24.0 MHz counter
    wd1_timeout_seconds: int = 30
    event_stream_enabled: bool = True


@dataclass(frozen=True)
class ANSStorageContract:
    controller_name: str = "Apple NVMe Storage v2 (ANS2)"
    sector_size_bytes: int = 4096        # 4 KiB LBA
    max_queue_entries: int = 65
    completion_timeout_ms: int = 10000
    wait_device_active_magic: int = 0xDE71CE55
    dma_alignment_bytes: int = 4096


SHARED_SPTM_CONTRACT = SPTMContract()
SHARED_AIC_CONTRACT = AICContract()
SHARED_TIMEBASE_CONTRACT = TimebaseContract()
SHARED_ANS_CONTRACT = ANSStorageContract()
