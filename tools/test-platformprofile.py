#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Unit tests for Snapdragon X-series hardware platform profiles."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'probes'))
from platformprofile import (
    PLATFORM_ZENBOOK_A16, PLATFORM_VIVOBOOK_S15, PLATFORM_VIRTUAL_ARM64,
    get_platform_profile, detect_host_platform
)


class PlatformProfileTests(unittest.TestCase):
    def test_zenbook_baseline(self):
        p = get_platform_profile('x2e-zenbook-a16')
        self.assertEqual(p.soc_generation, 'X2E')
        self.assertEqual(p.display.width, 2880)
        self.assertEqual(p.display.height, 1800)
        self.assertEqual(p.memory.total_physical_bytes, 32 * (1024 ** 3))
        self.assertEqual(p.gpu.generation, 'a8xx')
        self.assertTrue(p.gpu.supports_metal_3d)

    def test_vivobook_target(self):
        p = get_platform_profile('x1e-vivobook-s15')
        self.assertEqual(p.soc_generation, 'X1E')
        self.assertEqual(p.display.width, 2880)
        self.assertEqual(p.display.height, 1620)
        self.assertEqual(p.display.refresh_rate, 120)
        self.assertEqual(p.memory.total_physical_bytes, 16 * (1024 ** 3))
        # Conservative memory allocation for 16 GB machine
        self.assertLessEqual(p.memory.guest_default_bytes, 8 * (1024 ** 3))
        self.assertEqual(p.gpu.generation, 'a7xx')
        self.assertTrue(p.gpu.requires_gop_fallback)

    def test_aliases(self):
        self.assertEqual(get_platform_profile('x1e'), PLATFORM_VIVOBOOK_S15)
        self.assertEqual(get_platform_profile('s15'), PLATFORM_VIVOBOOK_S15)
        self.assertEqual(get_platform_profile('x2e'), PLATFORM_ZENBOOK_A16)
        self.assertEqual(get_platform_profile('a16'), PLATFORM_ZENBOOK_A16)
        self.assertEqual(get_platform_profile('virtual'), PLATFORM_VIRTUAL_ARM64)
        self.assertEqual(get_platform_profile('vm'), PLATFORM_VIRTUAL_ARM64)
        self.assertEqual(get_platform_profile('qemu'), PLATFORM_VIRTUAL_ARM64)
        self.assertEqual(get_platform_profile('vbox'), PLATFORM_VIRTUAL_ARM64)

    def test_virtual_arm64_profile(self):
        p = get_platform_profile('virtual-arm64')
        self.assertEqual(p.soc_generation, 'VIRT')
        self.assertEqual(p.gicd_base, 0x08000000)
        self.assertEqual(p.gicr_base, 0x080A0000)
        self.assertEqual(p.uart_base, 0x09000000)
        self.assertEqual(p.timer_physical_hz, 24_000_000)
        self.assertEqual(p.display.width, 1920)
        self.assertEqual(p.display.height, 1080)
        self.assertEqual(p.memory.total_physical_bytes, 8 * (1024 ** 3))
        self.assertEqual(p.memory.guest_default_bytes, 6 * (1024 ** 3))
        self.assertTrue(p.gpu.requires_gop_fallback)

    def test_host_detection(self):
        detected = detect_host_platform()
        self.assertIn(detected.id, ['x1e-vivobook-s15', 'x2e-zenbook-a16'])


if __name__ == '__main__':
    unittest.main()
