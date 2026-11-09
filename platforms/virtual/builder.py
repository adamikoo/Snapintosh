# SPDX-License-Identifier: MIT
"""Virtual Machine backend builder for Snapintosh.

Builds xnuboot monitor and guest image configured specifically for
the standard ARM64 virtual hardware memory map (0x40000000 DRAM base).
"""
from dataclasses import dataclass, replace
import os
from pathlib import Path
import struct
import sys
from typing import Optional, Tuple, Dict, Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'probes'))
sys.path.insert(0, str(ROOT / 'tools'))

from platforms.virtual.profile import PLATFORM_VIRTUAL_ARM64, VIRTUAL_MACHINE_SPECS
from platforms.shared.apple_contract import SHARED_SPTM_CONTRACT, SHARED_ANS_CONTRACT
from platforms.virtual.storage import VirtualDiskManager, DiskFormat


class VirtualBackendBuilder:
    """Configures and builds Snapintosh images for the virtual machine backend."""

    @classmethod
    def get_virtual_memory_layout(cls) -> Dict[str, int]:
        """Calculates memory regions for standard ARM64 virt machine (DRAM at 0x40000000)."""
        base = VIRTUAL_MACHINE_SPECS.dram_base            # 0x40000000 (1 GiB)
        guest_span = VIRTUAL_MACHINE_SPECS.guest_memory_bytes # 6 GiB
        total_span = 8 * (1024 ** 3)                     # 8 GiB

        return {
            'dram_base': base,
            'dram_size': total_span,
            'guest_base': base,
            'guest_span': guest_span,
            'ramfb_base': VIRTUAL_MACHINE_SPECS.ramfb_base,
            'ramfb_size': VIRTUAL_MACHINE_SPECS.framebuffer_height * VIRTUAL_MACHINE_SPECS.framebuffer_stride,
            'gicd_base': VIRTUAL_MACHINE_SPECS.gicd_base,
            'gicr_base': VIRTUAL_MACHINE_SPECS.gicr_base,
            'uart_base': VIRTUAL_MACHINE_SPECS.uart_base,
        }

    @classmethod
    def create_virtual_boot_config(cls, output_cfg_path: Path,
                                   disk_image_name: str = "snapintosh_macos.qcow2") -> Path:
        """Generates snapintosh_boot.cfg tailored for the virtual machine backend."""
        output_cfg_path.parent.mkdir(parents=True, exist_ok=True)
        layout = cls.get_virtual_memory_layout()

        content = f"""# Snapintosh Virtual Machine Boot Configuration
platform=virtual-arm64
guest_ram_mb={VIRTUAL_MACHINE_SPECS.guest_memory_bytes // (1024 * 1024)}
display_mode={VIRTUAL_MACHINE_SPECS.framebuffer_width}x{VIRTUAL_MACHINE_SPECS.framebuffer_height}@60
framebuffer_pa=0x{layout['ramfb_base']:08x}
framebuffer_stride={VIRTUAL_MACHINE_SPECS.framebuffer_stride}
boot_args=-v serial=3 debug=0x8
thermal_guard=0
gpu_dvfs=0
storage_backend=virtual_disk
virtual_disk_file={disk_image_name}
"""
        with open(output_cfg_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return output_cfg_path

    @classmethod
    def prepare_virtual_environment(cls, work_dir: Path, disk_size_gb: int = 64) -> Dict[str, Path]:
        """Prepares a complete virtual machine bundle with disk, config, and scripts."""
        work_dir.mkdir(parents=True, exist_ok=True)
        disk_path = work_dir / "snapintosh_macos.qcow2"
        cfg_path = work_dir / "snapintosh_boot.cfg"
        vbox_path = work_dir / "Snapintosh.vbox"
        vmx_path = work_dir / "Snapintosh.vmx"
        launcher_bat = work_dir / "Run-Snapintosh-VM.bat"
        launcher_ps1 = work_dir / "Run-Snapintosh-VM.ps1"

        # 1. Create dedicated sparse virtual disk (QCOW2)
        if not disk_path.is_file():
            VirtualDiskManager.create_disk(
                disk_path,
                capacity_bytes=disk_size_gb * (1024 ** 3),
                disk_format=DiskFormat.QCOW2,
                sparse=True
            )

        # 2. Write virtual boot configuration
        cls.create_virtual_boot_config(cfg_path, disk_image_name=disk_path.name)

        # 3. Generate VirtualBox & VMware companion configs
        from platforms.virtual.virtualbox_appliance import VirtualBoxApplianceBuilder
        from platforms.virtual.vmware_profile import VMwareProfileBuilder
        from platforms.virtual.qemu_runner import QEMURunner, QEMULaunchConfig

        vdi_dummy = work_dir / "snapintosh_macos.vdi"
        vmdk_dummy = work_dir / "snapintosh_macos.vmdk"
        VirtualBoxApplianceBuilder.generate_vbox_xml(vdi_dummy, vbox_path)
        VMwareProfileBuilder.generate_vmx(vmdk_dummy, vmx_path)

        # 4. Generate standalone runners
        launch_cfg = QEMULaunchConfig(
            cpu_cores=6,
            memory_mb=6144,
            disk_image=disk_path,
            enable_el2_virtualization=True,
            display_mode='ramfb',
            serial_mode='stdio'
        )
        QEMURunner.generate_launch_script(launch_cfg, launcher_bat)
        QEMURunner.generate_launch_script(launch_cfg, launcher_ps1)

        return {
            'disk': disk_path,
            'config': cfg_path,
            'vbox': vbox_path,
            'vmx': vmx_path,
            'launcher_bat': launcher_bat,
            'launcher_ps1': launcher_ps1,
        }
