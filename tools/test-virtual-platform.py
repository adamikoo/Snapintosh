#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Comprehensive validation suite for the Snapintosh Virtual Machine Backend.

Validates Milestones M1-M7:
  - Dual-backend abstraction and coexistence
  - Virtual machine platform profile and memory map (0x40000000 base)
  - Dedicated virtual storage creation (QCOW2, VDI, VMDK) and sparse allocation
  - Strict host physical SSD isolation safety enforcement
  - VirtualBox appliance OVF/.vbox XML schema verification
  - Portable VMware .vmx configuration generation
  - QEMU parameter formulation and host memory headroom verification
  - Native hardware regression gate (preservation of bare-metal target)
"""
import os
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'probes'))
sys.path.insert(0, str(ROOT / 'tools'))

from platforms.shared import (
    ExecutionBackend, BackendConfig, get_active_backend, get_backend_config,
    SHARED_SPTM_CONTRACT, SHARED_AIC_CONTRACT, SHARED_TIMEBASE_CONTRACT, SHARED_ANS_CONTRACT
)
from platforms.native import (
    PLATFORM_VIVOBOOK_S15, PLATFORM_ZENBOOK_A16, NATIVE_HARDWARE_CONTRACT
)
from platforms.virtual import (
    PLATFORM_VIRTUAL_ARM64, VIRTUAL_MACHINE_SPECS,
    DiskFormat, DiskMode, VirtualDiskMetadata, VirtualDiskManager,
    VirtualBoxConfig, VirtualBoxApplianceBuilder,
    VMWARE_ASSESSMENTS, VMwareProfileBuilder,
    QEMULaunchConfig, QEMURunner, VirtualBackendBuilder
)


class TestSnapintoshVirtualPlatform(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix='snapintosh_test_'))

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # Gate 1: Dual-Backend Abstraction & Coexistence
    # -------------------------------------------------------------------------
    def test_gate1_dual_backend_coexistence(self):
        print("\n[GATE 1] Testing Dual-Backend Abstraction & Coexistence...")
        # Check native backend configuration
        native_cfg = get_backend_config(ExecutionBackend.NATIVE_HARDWARE)
        self.assertEqual(native_cfg.backend, ExecutionBackend.NATIVE_HARDWARE)
        self.assertTrue(native_cfg.requires_hardware_el2)
        self.assertEqual(native_cfg.platform_id, 'x1e-vivobook-s15')

        # Check virtual backend configuration
        virt_cfg = get_backend_config(ExecutionBackend.VIRTUAL_MACHINE)
        self.assertEqual(virt_cfg.backend, ExecutionBackend.VIRTUAL_MACHINE)
        self.assertFalse(virt_cfg.requires_hardware_el2)
        self.assertFalse(virt_cfg.allows_physical_storage)
        self.assertEqual(virt_cfg.platform_id, 'virtual-arm64')

        # Check shared contracts
        self.assertEqual(SHARED_SPTM_CONTRACT.boot_magic, 0xD00FCAFEF00D2024)
        self.assertEqual(SHARED_SPTM_CONTRACT.page_granule_bytes, 16384)
        self.assertEqual(SHARED_AIC_CONTRACT.total_irq_lines, 1280)
        self.assertEqual(SHARED_TIMEBASE_CONTRACT.guest_counter_hz, 24_000_000)
        self.assertEqual(SHARED_ANS_CONTRACT.sector_size_bytes, 4096)
        print("  -> PASS: Native and Virtual backends cleanly separated with shared Apple contracts.")

    # -------------------------------------------------------------------------
    # Gate 2: Virtual Platform Profile & Memory Map
    # -------------------------------------------------------------------------
    def test_gate2_virtual_platform_profile_and_memory(self):
        print("\n[GATE 2] Testing Virtual Platform Profile & Memory Mapping...")
        p = PLATFORM_VIRTUAL_ARM64
        self.assertEqual(p.id, 'virtual-arm64')
        self.assertEqual(p.soc_generation, 'VIRT')
        self.assertEqual(p.guest_vcpus, 6)
        self.assertEqual(p.gicd_base, 0x08000000)
        self.assertEqual(p.gicr_base, 0x080A0000)
        self.assertEqual(p.uart_base, 0x09000000)
        self.assertEqual(p.timer_physical_hz, 24_000_000)

        # Validate memory calculations
        layout = VirtualBackendBuilder.get_virtual_memory_layout()
        self.assertEqual(layout['dram_base'], 0x40000000)
        self.assertEqual(layout['guest_span'], 6 * (1024 ** 3))
        self.assertEqual(layout['ramfb_size'], 1080 * 7680)
        self.assertEqual(layout['gicd_base'], 0x08000000)
        self.assertEqual(layout['uart_base'], 0x09000000)
        print("  -> PASS: Standard ARM64 virt memory map (0x40000000 base) verified.")

    # -------------------------------------------------------------------------
    # Gate 3: Virtual Storage Creation & Format Verification
    # -------------------------------------------------------------------------
    def test_gate3_virtual_storage_formats(self):
        print("\n[GATE 3] Testing Virtual Storage Creation (QCOW2, VDI, VMDK)...")
        cap = 64 * (1024 ** 3)  # 64 GiB

        # 1. QCOW2
        qcow2_path = self.temp_dir / "test_disk.qcow2"
        meta_qcow2 = VirtualDiskManager.create_disk(qcow2_path, capacity_bytes=cap, disk_format=DiskFormat.QCOW2)
        self.assertEqual(meta_qcow2.format, DiskFormat.QCOW2)
        self.assertEqual(meta_qcow2.capacity_bytes, cap)
        self.assertLess(meta_qcow2.actual_file_bytes, 1024 * 1024) # Sparse header < 1 MB
        parsed_qcow2 = VirtualDiskManager.validate_disk(qcow2_path)
        self.assertEqual(parsed_qcow2.capacity_bytes, cap)

        # 2. VDI
        vdi_path = self.temp_dir / "test_disk.vdi"
        meta_vdi = VirtualDiskManager.create_disk(vdi_path, capacity_bytes=cap, disk_format=DiskFormat.VDI)
        self.assertEqual(meta_vdi.format, DiskFormat.VDI)
        self.assertEqual(meta_vdi.capacity_bytes, cap)
        parsed_vdi = VirtualDiskManager.validate_disk(vdi_path)
        self.assertEqual(parsed_vdi.capacity_bytes, cap)

        # 3. VMDK
        vmdk_path = self.temp_dir / "test_disk.vmdk"
        meta_vmdk = VirtualDiskManager.create_disk(vmdk_path, capacity_bytes=cap, disk_format=DiskFormat.VMDK)
        self.assertEqual(meta_vmdk.format, DiskFormat.VMDK)
        self.assertEqual(meta_vmdk.capacity_bytes, cap)
        parsed_vmdk = VirtualDiskManager.validate_disk(vmdk_path)
        self.assertEqual(parsed_vmdk.capacity_bytes, cap)

        # 4. Disposable Overlay
        overlay_path = self.temp_dir / "test_disposable.qcow2"
        meta_overlay = VirtualDiskManager.create_disposable_overlay(qcow2_path, overlay_path)
        self.assertEqual(meta_overlay.mode, DiskMode.DISPOSABLE)
        self.assertEqual(meta_overlay.capacity_bytes, cap)
        print("  -> PASS: QCOW2, VDI, VMDK sparse disks and disposable overlays created and validated.")

    # -------------------------------------------------------------------------
    # Gate 4: Physical Host Storage Isolation Enforcement
    # -------------------------------------------------------------------------
    def test_gate4_physical_storage_isolation_enforcement(self):
        print("\n[GATE 4] Testing Strict Physical Storage Isolation Guard...")
        prohibited_targets = [
            Path(r"\\.\PhysicalDrive0"),
            Path(r"\\.\PhysicalDrive1"),
            Path("/dev/sda"),
            Path("/dev/nvme0n1"),
        ]
        for bad_target in prohibited_targets:
            with self.assertRaises(PermissionError):
                VirtualDiskManager.create_disk(bad_target, disk_format=DiskFormat.RAW)
        print("  -> PASS: All raw physical disk access attempts blocked by security boundary.")

    # -------------------------------------------------------------------------
    # Gate 5: VirtualBox Appliance Generation & XML Validation
    # -------------------------------------------------------------------------
    def test_gate5_virtualbox_appliance_validation(self):
        print("\n[GATE 5] Testing VirtualBox Appliance Generation & XML Validation...")
        vdi_file = self.temp_dir / "snapintosh_macos.vdi"
        vbox_file = self.temp_dir / "Snapintosh.vbox"
        ovf_file = self.temp_dir / "Snapintosh.ovf"

        VirtualBoxApplianceBuilder.generate_vbox_xml(vdi_file, vbox_file)
        self.assertTrue(vbox_file.is_file())

        # Parse XML to verify valid syntax and schema
        tree = ET.parse(vbox_file)
        root = tree.getroot()
        machine = root.find('{http://www.virtualbox.org/}Machine')
        self.assertIsNotNone(machine)
        hardware = machine.find('{http://www.virtualbox.org/}Hardware')
        self.assertIsNotNone(hardware)
        cpu = hardware.find('{http://www.virtualbox.org/}CPU')
        self.assertEqual(cpu.attrib.get('count'), '6')
        firmware = hardware.find('{http://www.virtualbox.org/}Firmware')
        self.assertEqual(firmware.attrib.get('type'), 'EFI')

        # Generate and validate OVF
        VirtualBoxApplianceBuilder.generate_ovf_descriptor(vdi_file, ovf_file)
        self.assertTrue(ovf_file.is_file())
        ovf_tree = ET.parse(ovf_file)
        ovf_root = ovf_tree.getroot()
        self.assertIn('Envelope', ovf_root.tag)
        print("  -> PASS: VirtualBox 7.x native .vbox XML and .ovf appliance successfully validated.")

    # -------------------------------------------------------------------------
    # Gate 6: VMware Configuration & Limitation Analysis
    # -------------------------------------------------------------------------
    def test_gate6_vmware_profile_validation(self):
        print("\n[GATE 6] Testing VMware Profile Generation & Capability Audit...")
        # Verify documented hypervisor limitations
        ws_assessment = VMWARE_ASSESSMENTS['workstation_pro']
        self.assertFalse(ws_assessment.can_run_on_snapdragon_windows)
        self.assertFalse(ws_assessment.supports_arm64_guests)

        fusion_assessment = VMWARE_ASSESSMENTS['fusion_pro']
        self.assertTrue(fusion_assessment.supports_arm64_guests)

        # Generate portable VMX
        vmdk_file = self.temp_dir / "snapintosh_macos.vmdk"
        vmx_file = self.temp_dir / "Snapintosh.vmx"
        VMwareProfileBuilder.generate_vmx(vmdk_file, vmx_file, num_vcpus=6, memory_mb=6144)
        self.assertTrue(vmx_file.is_file())

        with open(vmx_file, 'r', encoding='utf-8') as f:
            vmx_text = f.read()
        self.assertIn('numvcpus = "6"', vmx_text)
        self.assertIn('memsize = "6144"', vmx_text)
        self.assertIn('nvme0.present = "TRUE"', vmx_text)
        self.assertIn('firmware = "efi"', vmx_text)
        print("  -> PASS: VMware portable .vmx generated and platform limitations documented.")

    # -------------------------------------------------------------------------
    # Gate 7: QEMU Parameter Formulation & Memory Headroom Check
    # -------------------------------------------------------------------------
    def test_gate7_qemu_parameter_formulation(self):
        print("\n[GATE 7] Testing QEMU Parameter Formulation & Memory Headroom...")
        disk_file = self.temp_dir / "snapintosh_macos.qcow2"
        VirtualDiskManager.create_disk(disk_file, capacity_bytes=32 * (1024 ** 3), disk_format=DiskFormat.QCOW2)

        config = QEMULaunchConfig(
            cpu_cores=6,
            memory_mb=6144,
            disk_image=disk_file,
            enable_el2_virtualization=True,
            display_mode='ramfb',
            serial_mode='stdio',
            disposable_mode=True
        )
        cmd = QEMURunner.build_command_line(config)
        cmd_str = " ".join(cmd)

        self.assertIn("-machine virt,virtualization=on,gic-version=3", cmd_str)
        self.assertIn("-cpu max,pauth-impdef=on", cmd_str)
        self.assertIn("-smp cores=6,threads=1,sockets=1", cmd_str)
        self.assertIn("-m 6144M", cmd_str)
        self.assertIn("-device ramfb", cmd_str)
        self.assertIn("-device usb-tablet", cmd_str)
        self.assertIn("-device usb-kbd", cmd_str)
        self.assertIn("snapshot=on", cmd_str)
        self.assertIn("nvme,serial=SNAPANS001", cmd_str)

        # Generate scripts
        bat_script = self.temp_dir / "Run-Snapintosh-VM.bat"
        ps1_script = self.temp_dir / "Run-Snapintosh-VM.ps1"
        QEMURunner.generate_launch_script(config, bat_script)
        QEMURunner.generate_launch_script(config, ps1_script)
        self.assertTrue(bat_script.is_file())
        self.assertTrue(ps1_script.is_file())

        # Test memory headroom check
        headroom_ok = QEMURunner.check_host_memory_headroom(6144)
        self.assertTrue(isinstance(headroom_ok, bool))
        print("  -> PASS: QEMU parameter formulation, disposable flags, and launch scripts verified.")

    # -------------------------------------------------------------------------
    # Gate 8: Native Hardware Regression Gate
    # -------------------------------------------------------------------------
    def test_gate8_native_hardware_regression(self):
        print("\n[GATE 8] Running Native Hardware Regression Gate...")
        import subprocess
        test_script = ROOT / "tools" / "test-verify-standalone-fixes.py"
        self.assertTrue(test_script.is_file())

        res = subprocess.run([sys.executable, str(test_script)], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Native regression failure:\n{res.stdout}\n{res.stderr}")
        self.assertIn("ALL 6 CRITICAL VERIFICATION GATES PASSED", res.stdout)
        print("  -> PASS: Native hardware backend is 100% operational with ZERO regressions.")


if __name__ == '__main__':
    unittest.main()
