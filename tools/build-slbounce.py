#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Native Windows ARM64 build script for slbounce.efi."""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SL_ROOT = ROOT / 'build' / 'deps' / 'slbounce'
OUT = ROOT / 'build' / 'uefi'
OBJ_DIR = ROOT / 'build' / 'slbounce-objs'

OUT.mkdir(parents=True, exist_ok=True)
OBJ_DIR.mkdir(parents=True, exist_ok=True)

LLVM_BIN = Path("C:/Program Files/LLVM/bin")
CLANG = str(LLVM_BIN / "clang.exe") if (LLVM_BIN / "clang.exe").exists() else "clang"
LD_LLD = str(LLVM_BIN / "ld.lld.exe") if (LLVM_BIN / "ld.lld.exe").exists() else "ld.lld"
OBJCOPY = str(LLVM_BIN / "llvm-objcopy.exe") if (LLVM_BIN / "llvm-objcopy.exe").exists() else "llvm-objcopy"

GNUEFI_DIR = SL_ROOT / 'external' / 'gnu-efi'
LIBFDT_DIR = SL_ROOT / 'external' / 'dtc' / 'libfdt'
SYSREG_DIR = SL_ROOT / 'external' / 'arm64-sysreg-lib' / 'include'

# Make sure elf.h exists
elf_h = GNUEFI_DIR / 'inc' / 'elf.h'
if not elf_h.exists():
    q1n1_elf = ROOT / '..' / 'q1n1' / 'tools' / 'uefi-elf.h'
    if q1n1_elf.exists():
        import shutil
        shutil.copy(q1n1_elf, elf_h)

INCLUDES = [
    f"-I{GNUEFI_DIR / 'inc'}",
    f"-I{GNUEFI_DIR / 'inc' / 'aarch64'}",
    f"-I{GNUEFI_DIR / 'inc' / 'protocol'}",
    f"-I{SYSREG_DIR}",
    f"-I{LIBFDT_DIR}",
    f"-I{SL_ROOT / 'src' / 'include'}",
]

CFLAGS = [
    "--target=aarch64-unknown-none-elf",
    "-O2",
    "-fpic",
    "-fshort-wchar",
    "-fno-stack-protector",
    "-ffreestanding",
    "-fno-builtin",
    "-mno-outline-atomics",
    "-mstrict-align",
    "-DCONFIG_aarch64",
    "-D__MAKEWITH_GNUEFI",
    "-DGNU_EFI_USE_MS_ABI",
    "-DSLBOUNCE_ALWAYS_SWITCH=1",
    "-DEFI_DEBUG=1",
    "-DEFI_SUBSYSTEM=0xa",
    "-Wall",
    "-Wno-pointer-sign",
    "-Wno-unused-function",
] + INCLUDES

# 1. Compile gnu-efi lib
GNUEFI_SRCS = list((GNUEFI_DIR / 'lib').glob('*.c')) + list((GNUEFI_DIR / 'lib' / 'runtime').glob('*.c')) + [
    GNUEFI_DIR / 'lib' / 'aarch64' / 'initplat.c',
    GNUEFI_DIR / 'lib' / 'aarch64' / 'math.c',
    GNUEFI_DIR / 'lib' / 'aarch64' / 'setjmp.S',
    GNUEFI_DIR / 'lib' / 'aarch64' / 'efi_stub.S',
]

LIBFDT_SRCS = [
    LIBFDT_DIR / 'fdt.c',
    LIBFDT_DIR / 'fdt_ro.c',
    LIBFDT_DIR / 'fdt_wip.c',
    LIBFDT_DIR / 'fdt_sw.c',
    LIBFDT_DIR / 'fdt_rw.c',
    LIBFDT_DIR / 'fdt_empty_tree.c',
    LIBFDT_DIR / 'fdt_addresses.c',
    LIBFDT_DIR / 'fdt_check.c',
]

SL_SRCS = [
    SL_ROOT / 'src' / 'bounce_main.c',
    SL_ROOT / 'src' / 'sl.c',
    SL_ROOT / 'src' / 'arch.c',
    SL_ROOT / 'src' / 'util.c',
    SL_ROOT / 'src' / 'libc.c',
    SL_ROOT / 'src' / 'trans.s',
]

CRT0 = GNUEFI_DIR / 'gnuefi' / 'crt0-efi-aarch64.S'
RELOC = GNUEFI_DIR / 'gnuefi' / 'reloc_aarch64.c'
LDS = GNUEFI_DIR / 'gnuefi' / 'elf_aarch64_efi.lds'

all_objs = []

print("=== Compiling slbounce and dependencies ===")
for src in [CRT0, RELOC] + GNUEFI_SRCS + LIBFDT_SRCS + SL_SRCS:
    src = Path(src)
    obj = OBJ_DIR / f"{src.stem}_{src.suffix[1:]}.o"
    all_objs.append(obj)
    
    cmd = [CLANG] + CFLAGS + ["-c", str(src), "-o", str(obj)]
    res = subprocess.run(cmd)
    if res.returncode != 0:
        print(f"FAILED: {src}")
        sys.exit(1)

print(f"Compiled {len(all_objs)} object files.")

# 2. Link into ELF shared object
SO_OUT = OBJ_DIR / "slbounce.so"
LDFLAGS = [
    "-nostdlib",
    "-shared",
    "-Bsymbolic",
    "-T", str(LDS),
    "-e", "_start",
    "-o", str(SO_OUT),
] + [str(o) for o in all_objs]

print("=== Linking slbounce.so ===")
res = subprocess.run([LD_LLD] + LDFLAGS)
if res.returncode != 0:
    print("Linking failed!")
    sys.exit(1)

# 3. Convert ELF shared object to PE/COFF .efi binary
EFI_OUT = OUT / "slbounce.efi"
print(f"=== Converting to {EFI_OUT} ===")
OBJCOPY_ARGS = [
    "-O", "binary",
    str(SO_OUT),
    str(EFI_OUT),
]
res = subprocess.run([OBJCOPY] + OBJCOPY_ARGS)
if res.returncode != 0:
    print("llvm-objcopy conversion failed!")
    sys.exit(1)

size = EFI_OUT.stat().st_size
print(f"SUCCESS: Built {EFI_OUT} ({size} bytes)")
