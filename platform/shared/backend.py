# SPDX-License-Identifier: MIT
"""Platform backend abstraction for Snapintosh.

Enables seamless switching between native hardware execution (ASUS Vivobook /
Zenbook on Qualcomm Oryon) and conventional virtual machine execution
(QEMU, VirtualBox, VMware) without code duplication.
"""
from dataclasses import dataclass
from enum import Enum
import os
from pathlib import Path
from typing import Optional


class ExecutionBackend(str, Enum):
    NATIVE_HARDWARE = 'native_hardware'
    VIRTUAL_MACHINE = 'virtual_machine'


@dataclass(frozen=True)
class BackendConfig:
    backend: ExecutionBackend
    platform_id: str
    description: str
    allows_physical_storage: bool
    requires_hardware_el2: bool
    firmware_type: str


NATIVE_CONFIG = BackendConfig(
    backend=ExecutionBackend.NATIVE_HARDWARE,
    platform_id='x1e-vivobook-s15',
    description='Direct execution on Qualcomm Snapdragon X1/X2 Elite physical hardware',
    allows_physical_storage=True,
    requires_hardware_el2=True,
    firmware_type='UEFI + Secure Launch (slbounce + q1n1)'
)

VIRTUAL_CONFIG = BackendConfig(
    backend=ExecutionBackend.VIRTUAL_MACHINE,
    platform_id='virtual-arm64',
    description='Conventional ARM64 Virtual Machine (QEMU / VirtualBox / VMware)',
    allows_physical_storage=False,
    requires_hardware_el2=False,
    firmware_type='Standard EDK2 / UEFI'
)


def get_active_backend() -> ExecutionBackend:
    """Retrieve active backend from environment or configuration file.

    Defaults to VIRTUAL_MACHINE when running inside a VM environment or when
    requested via SNAPINTOSH_BACKEND=virtual. Defaults to NATIVE_HARDWARE for
    bare-metal USB booting.
    """
    env_backend = os.environ.get('SNAPINTOSH_BACKEND', '').strip().lower()
    if env_backend in ('virtual', 'vm', 'qemu', 'vbox', 'virtualbox', 'vmware'):
        return ExecutionBackend.VIRTUAL_MACHINE
    if env_backend in ('native', 'hardware', 'metal', 'baremetal'):
        return ExecutionBackend.NATIVE_HARDWARE

    config_path = Path(__file__).resolve().parents[2] / 'config' / 'backend.json'
    if config_path.is_file():
        try:
            import json
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                b = data.get('backend', '').strip().lower()
                if b == 'virtual_machine':
                    return ExecutionBackend.VIRTUAL_MACHINE
                if b == 'native_hardware':
                    return ExecutionBackend.NATIVE_HARDWARE
        except Exception:
            pass

    # Default to virtual machine mode when operating inside conventional host OS
    return ExecutionBackend.VIRTUAL_MACHINE


def get_backend_config(backend: Optional[ExecutionBackend] = None) -> BackendConfig:
    if backend is None:
        backend = get_active_backend()
    if backend == ExecutionBackend.VIRTUAL_MACHINE:
        return VIRTUAL_CONFIG
    return NATIVE_CONFIG
