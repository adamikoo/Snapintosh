# SPDX-License-Identifier: MIT
"""Virtual machine backend package for Snapintosh."""
from .profile import PLATFORM_VIRTUAL_ARM64, VIRTUAL_MACHINE_SPECS, VirtualMachineSpecs
from .storage import (
    DiskFormat, DiskMode, VirtualDiskMetadata, VirtualDiskManager
)
from .virtualbox_appliance import VirtualBoxConfig, VirtualBoxApplianceBuilder
from .vmware_profile import (
    VMwareProductAssessment, VMWARE_ASSESSMENTS, VMwareProfileBuilder
)
from .qemu_runner import QEMULaunchConfig, QEMURunner
from .builder import VirtualBackendBuilder

__all__ = [
    'PLATFORM_VIRTUAL_ARM64',
    'VIRTUAL_MACHINE_SPECS',
    'VirtualMachineSpecs',
    'DiskFormat',
    'DiskMode',
    'VirtualDiskMetadata',
    'VirtualDiskManager',
    'VirtualBoxConfig',
    'VirtualBoxApplianceBuilder',
    'VMwareProductAssessment',
    'VMWARE_ASSESSMENTS',
    'VMwareProfileBuilder',
    'QEMULaunchConfig',
    'QEMURunner',
    'VirtualBackendBuilder',
]
