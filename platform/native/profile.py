# SPDX-License-Identifier: MIT
"""Native hardware backend profile and configuration."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'probes'))

from platformprofile import (
    PlatformProfile, DisplayGeometry, MemoryProfile, GPUProfile, InputProfile,
    PLATFORM_ZENBOOK_A16, PLATFORM_VIVOBOOK_S15, get_platform_profile, detect_host_platform
)

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
]
