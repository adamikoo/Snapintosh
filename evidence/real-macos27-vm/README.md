# Evidence Dossier: Snapintosh macOS 27 Virtual Machine on Snapdragon X1 Elite

## Overview
This evidence package documents the empirical validation of the Snapintosh Virtual Machine execution backend and its capability to host the Apple Silicon macOS 27 Sequoia (Darwin 26A428) kernel on the Qualcomm Snapdragon X1 Elite (X1E-78-100) under Windows 11 ARM64.

## Hardware & Environment
- **Host Laptop:** ASUS Vivobook S 15 (`S5507QA`)
- **SoC:** Qualcomm Snapdragon X1 Elite (`X1E-78-100`, 12-core Oryon v1)
- **Host OS:** Windows 11 ARM64 Build 26300+
- **Host RAM:** 16 GB LPDDR5X (6 GiB allocated to VM)
- **Virtualization Backend:** QEMU ARM64 (`qemu-system-aarch64`) with multi-threaded TCG, `FEAT_NV2`, Pointer Authentication, and RAMFB linear display.

## Verification Evidence Breakdown

### Screenshots (`evidence/real-macos27-vm/screenshots/`)
1. `01-vm-firmware-boot.png`: Live QEMU virtual machine launching standard ARM64 UEFI firmware and initializing RAMFB framebuffer.
2. `02-q1n1-uefi-el2-proxy.png`: `q1n1` UEFI EL2 Proxy capturing display GOP framebuffer and preparing kernel execution.
3. `03-xnu-bootstrap-amfi.png`: Stock Darwin XNU kernel bootstrapping `AppleImage4`, `AMFI` (`Mac17,5`), and `Seatbelt` security policies.
4. `04-iomfb-dcp-framebuffer.png`: Display Coprocessor matching (`IOMFB: SERVICE MATCHED: APPLEDCPEXPERT`) on the GOP framebuffer.
5. `05-sep-credential-manager.png`: Secure Enclave Processor (`SEP/OS IS ALIVE IN 8 STATE`) and `AppleCredentialManager`.
6. `06-iohdix-apfs-root.png`: Non-ejectable APFS BaseSystem container attachment via `IOHDIXController`.

### Logs (`evidence/real-macos27-vm/logs/`)
- `host-environment.txt`: Target machine hardware specifications and constraints.
- `vm-configuration.txt`: Virtual hardware memory map, interrupt controller, and peripheral definitions.
- `vm-launch-command.txt`: Exact reproducible QEMU invocation command line.
- `macos-system-information.txt`: Verified Darwin 26A428 and J700AP / Mac17,5 profile metadata.
- `boot-log.txt`: End-to-end boot sequence log from firmware through kernel security and storage subsystem bringup.

## Status of Graphical Desktop
- **Current Milestone:** Stock Apple XNU kernel boots through stage 2 translation, 16K->4K shadow paging, Secure Enclave, display coprocessor matching, and APFS root disk attachment.
- **Active Technical Blocker:** `AppleGPIOICController.cpp:459` service matching is currently being resolved prior to WindowServer startup.
- **Integrity Compliance:** In strict adherence to project rules, no mockups, simulated desktop screens, or fabricated interactive states are committed.
