# SPDX-License-Identifier: MIT
"""Native hardware platform package."""
from .profile import (
    PlatformProfile, DisplayGeometry, MemoryProfile, GPUProfile, InputProfile,
    PLATFORM_ZENBOOK_A16, PLATFORM_VIVOBOOK_S15, get_platform_profile, detect_host_platform
)
from .hardware_contract import NativeHardwareContract, NATIVE_HARDWARE_CONTRACT

__all__ = [
    'PlatformProfile',
    'DisplayGeometry',
    'MemoryProfile',
    'GPUProfile',
    'InputProfile',
    'PLATFORM_ZENBOOK_A16',
    'PLATFORM_VIVOBOOK_S15',
    'get_platform_profile',
    'detect_host_platform',
    'NativeHardwareContract',
    'NATIVE_HARDWARE_CONTRACT',
]
