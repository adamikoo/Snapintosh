# SPDX-License-Identifier: MIT
"""Native physical hardware execution boundaries.

Specifies hardware addresses, physical interrupt lines, and PCIe BAR structures
for the bare-metal Snapdragon X1/X2 Elite targets.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class NativeHardwareContract:
    bootloader_chain: str = "slbounce.efi -> tcblaunch.exe -> q1n1.efi -> xnuboot.bin"
    entry_exception_level: int = 2
    qualcomm_gicd_base: int = 0x17000000
    qualcomm_gicr_base: int = 0x17080000
    qualcomm_geni_uart_base: int = 0x00894000
    qualcomm_geni_i2c_keyboard_base: int = 0x0088C000
    qualcomm_geni_i2c_touchpad_base: int = 0x00B80000
    physical_timer_hz: int = 19_200_000
    physical_nvme_direct_bar: bool = True
    physical_framebuffer_pa: int = 0x00000000E4800000
    vivobook_dram_placement_base: int = 0x0000000880000000


NATIVE_HARDWARE_CONTRACT = NativeHardwareContract()
