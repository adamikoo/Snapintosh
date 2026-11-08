# SPDX-License-Identifier: MIT
"""Shared platform contracts and backend abstractions."""
from .backend import ExecutionBackend, BackendConfig, get_active_backend, get_backend_config
from .apple_contract import (
    SPTMContract, AICContract, TimebaseContract, ANSStorageContract,
    SHARED_SPTM_CONTRACT, SHARED_AIC_CONTRACT, SHARED_TIMEBASE_CONTRACT, SHARED_ANS_CONTRACT
)

__all__ = [
    'ExecutionBackend',
    'BackendConfig',
    'get_active_backend',
    'get_backend_config',
    'SPTMContract',
    'AICContract',
    'TimebaseContract',
    'ANSStorageContract',
    'SHARED_SPTM_CONTRACT',
    'SHARED_AIC_CONTRACT',
    'SHARED_TIMEBASE_CONTRACT',
    'SHARED_ANS_CONTRACT',
]
