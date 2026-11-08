# SPDX-License-Identifier: MIT
"""Virtual storage and disk image management for Snapintosh VM backend.

Provides dedicated virtual disk creation, validation, snapshotting, and safe I/O
without ever accessing the host's physical Windows SSD.
"""
from dataclasses import dataclass
from enum import Enum
import math
import os
from pathlib import Path
import struct
from typing import Optional, Dict, Any


class DiskFormat(str, Enum):
    QCOW2 = 'qcow2'
    RAW = 'raw'
    VDI = 'vdi'
    VMDK = 'vmdk'


class DiskMode(str, Enum):
    PERSISTENT = 'persistent'
    DISPOSABLE = 'disposable'


@dataclass(frozen=True)
class VirtualDiskMetadata:
    path: Path
    format: DiskFormat
    capacity_bytes: int
    actual_file_bytes: int
    sector_size: int
    mode: DiskMode
    is_sparse: bool
    cluster_size: int = 65536


class VirtualDiskManager:
    """Manages dedicated virtual disk images for the macOS virtual machine."""

    # Prohibited device paths ensuring strict physical disk isolation
    PROHIBITED_DEVICE_PREFIXES = (
        r'\\.\physicaldrive',
        r'\\.\',
        '/dev/sd',
        '/dev/nvme',
        '/dev/hd',
        '/dev/disk',
    )

    @classmethod
    def _assert_safe_path(cls, path: Path) -> Path:
        """Enforces that the path is an ordinary file and never a physical disk device."""
        resolved = str(path.resolve()).lower()
        for prohibited in cls.PROHIBITED_DEVICE_PREFIXES:
            if resolved.startswith(prohibited):
                raise PermissionError(
                    f"Physical disk access is strictly prohibited! Blocked device target: {path}"
                )
        return path

    @classmethod
    def create_disk(cls, path: Path, capacity_bytes: int = 64 * (1024 ** 3),
                    disk_format: DiskFormat = DiskFormat.QCOW2,
                    sparse: bool = True) -> VirtualDiskMetadata:
        """Creates a dedicated virtual disk with sparse backing."""
        cls._assert_safe_path(path)
        path = path.resolve()
        path.parent.mkdir(parents=True, exist_ok=True)

        if disk_format == DiskFormat.QCOW2:
            cls._create_qcow2(path, capacity_bytes)
        elif disk_format == DiskFormat.VDI:
            cls._create_vdi(path, capacity_bytes)
        elif disk_format == DiskFormat.VMDK:
            cls._create_vmdk(path, capacity_bytes)
        elif disk_format == DiskFormat.RAW:
            cls._create_raw(path, capacity_bytes, sparse=sparse)
        else:
            raise ValueError(f"Unsupported disk format: {disk_format}")

        actual_size = path.stat().st_size
        return VirtualDiskMetadata(
            path=path,
            format=disk_format,
            capacity_bytes=capacity_bytes,
            actual_file_bytes=actual_size,
            sector_size=4096,  # Apple 4 KiB LBA standard
            mode=DiskMode.PERSISTENT,
            is_sparse=sparse,
            cluster_size=65536
        )

    @staticmethod
    def _create_qcow2(path: Path, capacity_bytes: int):
        """Creates a valid QCOW2 v3 sparse disk header."""
        # QCOW2 v3 Header:
        # magic: 'QFI\xfb' (4 bytes)
        # version: 3 (uint32)
        # backing_file_offset: 0 (uint64)
        # backing_file_size: 0 (uint32)
        # cluster_bits: 16 (uint32, 64 KiB clusters)
        # size: virtual disk size in bytes (uint64)
        # crypt_method: 0 (uint32)
        # l1_size: uint32
        # l1_table_offset: uint64
        # refcount_table_offset: uint64
        # refcount_table_clusters: uint32
        # nb_snapshots: 0 (uint32)
        # snapshots_offset: 0 (uint64)
        # incompatible_features: uint64
        # compatible_features: uint64
        # autoclear_features: uint64
        # refcount_order: 4 (uint32, 16-bit refcounts)
        # header_length: 104 (uint32)
        cluster_bits = 16
        cluster_size = 1 << cluster_bits
        l2_entries = cluster_size // 8
        l1_size = int(math.ceil(capacity_bytes / (cluster_size * l2_entries)))

        header = bytearray(104)
        struct.pack_into(
            '>4sIIQIIQI',
            header, 0,
            b'QFI\xfb',      # magic
            3,              # version 3
            0,              # backing_file_offset
            0,              # backing_file_size
            cluster_bits,   # cluster_bits (16 = 64 KiB)
            capacity_bytes, # virtual size
            0               # crypt_method
        )
        struct.pack_into(
            '>IQIQIIQ',
            header, 40,
            l1_size,        # l1_size
            cluster_size,   # l1_table_offset (cluster 1)
            cluster_size * 2, # refcount_table_offset (cluster 2)
            1,              # refcount_table_clusters
            0,              # nb_snapshots
            0               # snapshots_offset
        )
        struct.pack_into(
            '>QQQII',
            header, 72,
            0,              # incompatible_features
            0,              # compatible_features
            0,              # autoclear_features
            4,              # refcount_order (16-bit refcount)
            104             # header_length
        )

        with open(path, 'wb') as f:
            f.write(header)
            # Pad to first cluster boundary
            f.write(b'\x00' * (cluster_size - len(header)))
            # Cluster 1: L1 table (all zeros = unallocated)
            f.write(b'\x00' * cluster_size)
            # Cluster 2: Refcount table
            f.write(b'\x00' * cluster_size)

    @staticmethod
    def _create_vdi(path: Path, capacity_bytes: int):
        """Creates a valid VirtualBox VDI sparse disk header."""
        # VDI Pre-header:
        # text: "<<< Oracle VM VirtualBox Disk Image >>>\n" (64 bytes)
        # signature: 0xBEDA107F
        # version: 0x00010001 (1.1)
        # Header:
        # header_size: 400
        # image_type: 1 (dynamic/sparse)
        # image_flags: 0
        # description: 256 bytes text
        # offset_bmap: uint32
        # offset_data: uint32
        # cylinders, heads, sectors, sector_size (512)
        # disk_size: uint64
        # block_size: uint32 (1 MiB default = 0x100000)
        # block_extra: 0
        # total_blocks: uint32
        # allocated_blocks: uint32
        # uuid_create, uuid_modify, uuid_linkage, uuid_parent_modify: 16 bytes each
        block_size = 1024 * 1024  # 1 MiB
        total_blocks = int(math.ceil(capacity_bytes / block_size))
        bmap_size = total_blocks * 4
        # Align offset_data to 1 MiB boundary
        offset_bmap = 512
        offset_data = ((offset_bmap + bmap_size + block_size - 1) // block_size) * block_size

        pre_header = bytearray(512)
        text = b"<<< Oracle VM VirtualBox Disk Image >>>\n\x1a"
        pre_header[:len(text)] = text
        struct.pack_into('<II', pre_header, 64, 0xBEDA107F, 0x00010001)

        # Main header at offset 68
        struct.pack_into(
            '<III256sIIIIIIQIIII16s16s16s16s',
            pre_header, 68,
            400,            # header_size
            1,              # image_type dynamic
            0,              # image_flags
            b'Snapintosh macOS Dedicated Virtual Disk',
            offset_bmap,    # offset_bmap
            offset_data,    # offset_data
            capacity_bytes // (16 * 63 * 512), # cylinders
            16,             # heads
            63,             # sectors
            512,            # sector_size
            capacity_bytes, # disk_size
            block_size,     # block_size
            0,              # block_extra
            total_blocks,   # total_blocks
            0,              # allocated_blocks
            os.urandom(16), # uuid_create
            os.urandom(16), # uuid_modify
            os.urandom(16), # uuid_linkage
            os.urandom(16)  # uuid_parent_modify
        )

        with open(path, 'wb') as f:
            f.write(pre_header)
            # Write unallocated block map entries (-1 / 0xFFFFFFFF)
            f.write(b'\xFF' * bmap_size)
            # Pad to offset_data
            padding = offset_data - (offset_bmap + bmap_size)
            if padding > 0:
                f.write(b'\x00' * padding)

    @staticmethod
    def _create_vmdk(path: Path, capacity_bytes: int):
        """Creates a VMware monolithicSparse VMDK disk."""
        # A sparse VMDK starts with a binary SparseExtentHeader:
        # magic: 0x564d444b ('KDMV')
        # version: 1
        # flags: 3
        # capacity: sectors (512-byte sectors)
        # grainSize: 128 (64 KiB grains)
        # descriptorOffset: 1
        # descriptorSize: 20
        # numGTEsPerGT: 512
        # rgdOffset: 0
        # gdOffset: grain directory offset
        # overhead: total metadata sectors
        sectors = capacity_bytes // 512
        grain_size = 128  # 64 KiB
        num_grains = int(math.ceil(sectors / grain_size))
        gtes_per_gt = 512
        num_gts = int(math.ceil(num_grains / gtes_per_gt))

        desc_text = f"""# Disk DescriptorFile
version=1
encoding="UTF-8"
CID=7a9b1c2d
parentCID=ffffffff
createType="monolithicSparse"

# Extent description
RW {sectors} SPARSE "{path.name}"

# The Disk Data Base 
#DDB

ddb.virtualHWVersion = "21"
ddb.geometry.cylinders = "{sectors // (16 * 63)}"
ddb.geometry.heads = "16"
ddb.geometry.sectors = "63"
ddb.adapterType = "nvme"
""".encode('utf-8')

        header = bytearray(512)
        struct.pack_into(
            '<IIIIQQQIIQ',
            header, 0,
            0x564D444B,     # 'KDMV' magic
            1,              # version 1
            3,              # flags (valid newline detection)
            sectors,        # capacity in 512-byte sectors
            grain_size,     # grainSize
            1,              # descriptorOffset (sector 1)
            int(math.ceil(len(desc_text) / 512)), # descriptorSize
            gtes_per_gt,    # numGTEsPerGT
            0,              # rgdOffset
            128             # gdOffset
        )

        with open(path, 'wb') as f:
            f.write(header)
            f.write(desc_text)
            pad = (512 - (len(desc_text) % 512)) % 512
            if pad:
                f.write(b'\x00' * pad)

    @staticmethod
    def _create_raw(path: Path, capacity_bytes: int, sparse: bool = True):
        """Creates a RAW disk image with sparse truncate."""
        with open(path, 'wb') as f:
            if sparse and hasattr(f, 'truncate'):
                f.seek(capacity_bytes - 1)
                f.write(b'\x00')
            else:
                f.write(b'\x00' * min(capacity_bytes, 4096))

    @classmethod
    def validate_disk(cls, path: Path) -> VirtualDiskMetadata:
        """Validates disk image integrity and parses format header."""
        cls._assert_safe_path(path)
        if not path.is_file():
            raise FileNotFoundError(f"Virtual disk not found: {path}")

        file_size = path.stat().st_size
        with open(path, 'rb') as f:
            magic_lead = f.read(64)

        if magic_lead.startswith(b'QFI\xfb'):
            # QCOW2
            version, size = struct.unpack_from('>x4sIQ', magic_lead, 0)[1:]
            return VirtualDiskMetadata(
                path=path, format=DiskFormat.QCOW2, capacity_bytes=size,
                actual_file_bytes=file_size, sector_size=4096,
                mode=DiskMode.PERSISTENT, is_sparse=True
            )
        elif magic_lead.startswith(b'<<< Oracle VM VirtualBox Disk Image'):
            # VDI
            with open(path, 'rb') as f:
                f.seek(68)
                header_data = f.read(150)
            size = struct.unpack_from('<Q', header_data, 72)[0]
            return VirtualDiskMetadata(
                path=path, format=DiskFormat.VDI, capacity_bytes=size,
                actual_file_bytes=file_size, sector_size=4096,
                mode=DiskMode.PERSISTENT, is_sparse=True
            )
        elif magic_lead.startswith(b'KDMV'):
            # VMDK
            sectors = struct.unpack_from('<I', magic_lead, 12)[0]
            size = sectors * 512
            return VirtualDiskMetadata(
                path=path, format=DiskFormat.VMDK, capacity_bytes=size,
                actual_file_bytes=file_size, sector_size=4096,
                mode=DiskMode.PERSISTENT, is_sparse=True
            )
        else:
            # Fallback to RAW
            return VirtualDiskMetadata(
                path=path, format=DiskFormat.RAW, capacity_bytes=file_size,
                actual_file_bytes=file_size, sector_size=4096,
                mode=DiskMode.PERSISTENT, is_sparse=False
            )

    @classmethod
    def create_disposable_overlay(cls, base_disk: Path, overlay_path: Path) -> VirtualDiskMetadata:
        """Creates a QCOW2 copy-on-write overlay for disposable VM execution."""
        cls._assert_safe_path(base_disk)
        cls._assert_safe_path(overlay_path)
        base_meta = cls.validate_disk(base_disk)

        # Create overlay referencing backing file
        overlay_path = overlay_path.resolve()
        overlay_path.parent.mkdir(parents=True, exist_ok=True)
        backing_path_str = str(base_disk.resolve())

        cluster_bits = 16
        cluster_size = 1 << cluster_bits
        l2_entries = cluster_size // 8
        l1_size = int(math.ceil(base_meta.capacity_bytes / (cluster_size * l2_entries)))

        header = bytearray(104)
        backing_offset = 104
        backing_len = len(backing_path_str.encode('utf-8'))

        struct.pack_into(
            '>4sIIQIIQI',
            header, 0,
            b'QFI\xfb', 3, backing_offset, backing_len,
            cluster_bits, base_meta.capacity_bytes, 0
        )
        struct.pack_into(
            '>IQIQIIQ',
            header, 40,
            l1_size, cluster_size, cluster_size * 2, 1, 0, 0
        )
        struct.pack_into(
            '>QQQII',
            header, 72,
            0, 0, 0, 4, 104
        )

        with open(overlay_path, 'wb') as f:
            f.write(header)
            f.write(backing_path_str.encode('utf-8'))
            pad_lead = (cluster_size - (104 + backing_len)) % cluster_size
            f.write(b'\x00' * pad_lead)
            f.write(b'\x00' * cluster_size)  # L1 Table
            f.write(b'\x00' * cluster_size)  # Refcount Table

        return VirtualDiskMetadata(
            path=overlay_path, format=DiskFormat.QCOW2,
            capacity_bytes=base_meta.capacity_bytes,
            actual_file_bytes=overlay_path.stat().st_size,
            sector_size=4096, mode=DiskMode.DISPOSABLE, is_sparse=True
        )
