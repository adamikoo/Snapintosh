# Snapintosh Virtual Machine Architecture & Feasibility Assessment

**Document ID:** ARCH-VM-001  
**Status:** Approved Architectural Specification  
**Target Environments:** Conventional ARM64 Virtual Machines (QEMU, VirtualBox, VMware)  
**Host Hardware:** ASUS Vivobook S 15 (Qualcomm Snapdragon X1 Elite X1E-78-100, 16 GB LPDDR5X, Windows 11 ARM64 Build 26300)

---

## 1. Executive Summary & Objective

Snapintosh has successfully demonstrated a bare-metal standalone bootloader chain on Qualcomm Snapdragon hardware (`slbounce.efi` $\to$ `tcblaunch.exe` $\to$ `q1n1.efi` $\to$ `xnuboot.bin` $\to$ stock macOS 27 Sequoia kernelcache `kernelcache.release.mac17p`).

The objective of this architectural milestone is to **decouple Snapintosh from physical host hardware execution**, enabling it to run as a **conventional virtual machine** inside Windows 11 ARM64 without requiring the user to reboot out of Windows, partition the host SSD, or flash USB boot drives.

The project introduces a dual-backend architecture:
1. **Native Hardware Backend (`platform/native`):** Preserved in its entirety for direct execution on the ASUS Vivobook S 15 / Zenbook A16.
2. **Virtual Machine Backend (`platform/virtual`):** Designed to execute inside a standardized ARM64 virtual hardware platform, utilizing dedicated virtual disks (`.qcow2`, `.vdi`, `.vmdk`), virtual framebuffers, and standard virtual peripherals.

---

## 2. In-Depth Inspection of Current Implementation

### 2.1 The Existing Boot Chain
```
[ UEFI Firmware ] 
       │ (slbounce.efi on USB)
       ▼
[ Secure Launch / TCB Launch ]
       │ (Windows tcblaunch.exe SMC switches CPU from EL1 to EL2)
       ▼
[ q1n1 EL2 Proxy ]
       │ (Unpacks guest chunks into physical DRAM, flushes caches)
       ▼
[ Snapintosh xnuboot Monitor (EL2) ]
       │ (Initializes stage 2, shadow page tables, AIC, SPTM/TXM handlers)
       ▼
[ macOS 27 Sequoia XNU Kernel (EL1) ]
       │ (FEAT_NV2 redirects EL2 register writes to memory; believes it is EL2)
       ▼
[ macOS Userspace (EL0) ]
```

### 2.2 Privilege, Exception Handling & Memory Mechanics
* **EL2 Monitor (`probes/xnuboot/`):** Owns Stage 2 translation (`VTCR_EL2`, `VTTBR_EL2`), traps IMPDEF system registers via `HCR_EL2.TIDCP`, and manages per-vCPU state in `VNCR_EL2`.
* **SPTM / TXM Emulation (`compat/sptm.c`, `compat/txm.c`):** Apple Silicon uses Guarded Execution Feature (GXF) for SPTM (GL2) and TXM (GL1). On Snapdragon, XNU's `genter` calls are intercepted via Stage 2 execute-never trampolines or direct `HVC` calls. The monitor implements `MAP_PAGE`, `UNMAP`, `UPDATE_REGION`, `RETYPE`, and DART translations.
* **16 KiB to 4 KiB Shadow MMU (`shadow/mmu.c`, `shadow/shadow.c`):** XNU assumes a 16 KiB translation granule. Because Oryon v1 hardware only supports 4 KiB and 64 KiB page sizes, the monitor builds and synchronizes a 4 KiB hardware shadow table in `TTBR0_EL1` and `TTBR1_EL1`.
* **Apple Interrupt Controller (`compat/aic.c`):** Emulates an Apple AIC3 with 1,280 interrupt lines. Level-triggered hardware SPIs are forwarded to virtual AIC lines (`compat/irq-forward.c`).
* **Storage (`compat/ans.c`):** Emulates Apple's ANS2 (Apple NVMe Storage) controller. In the native backend, requests are mapped directly to physical NVMe controller BAR registers via `compat/nvme-host.c`.

### 2.3 Physical Hardware Assumptions to be Decoupled
The following components currently assume exclusive physical hardware ownership:

| Component | Physical Native Assumption | Virtual Machine Requirement |
| :--- | :--- | :--- |
| **CPU / Privilege** | Physical Oryon v1 core at EL2 via Secure Launch | Standard ARM64 vCPU with EL2 virtualization support |
| **Clock / Timer** | Physical 19.2 MHz counter scaled to 24.0 MHz | Standard virtual timer (24 MHz or standard frequency) |
| **Interrupts** | Physical Qualcomm GICv3 (`0x17000000`, redist `0x17080000`) | Standard ARM GICv3 (`0x08000000`, redist `0x080A0000`) |
| **DRAM Layout** | Hardcoded physical addresses (`0x909000000`, `0x88000C000`) | VM-allocated memory aperture starting at base `0x40000000` |
| **Storage** | Host Micron 2400 NVMe controller BARs on physical PCIe | Isolated virtual disk file (`.qcow2`, `.vdi`, `.vmdk`) |
| **Display** | Hardcoded 2880x1620 OLED eDP panel (`0xe4800000`) | Standard linear RAMFB / VirtIO-GPU / GOP framebuffer |
| **Input** | Qualcomm GENI I2C bus (`0x0088C000`) keyboard/touchpad | Standard USB HID keyboard and tablet pointer |
| **UART Console** | Qualcomm GENI UART (`0x00894000`) | Standard ARM PL011 UART (`0x09000000`) |

---

## 3. Analysis of Target Hypervisors on Windows 11 ARM64

### 3.1 Oracle VirtualBox 7.x
* **Status on Windows 11 ARM64:** VirtualBox 7.1+ provides an ARM64 native build, but it executes via the Windows Hypervisor Platform (WHPX / Microsoft Hyper-V APIs).
* **Architectural Limitation:** Microsoft Hyper-V on ARM64 **does not support nested EL2 virtualization** (`-ExposeVirtualizationExtensions` is explicitly unsupported on ARM64 by Microsoft).
* **Implication:** Inside a VirtualBox ARM64 guest, execution is restricted to **EL1**. Attempting to execute `MSR HCR_EL2` or enter EL2 triggers an `UNDEFINED INSTRUCTION` trap.
* **Compatibility Strategy:** VirtualBox can be targeted via an importable appliance specification (`.ovf` / `.vbox` + `.vdi`) when running in hosted monitor mode or when Microsoft enables nested ARM64 virtualization.

### 3.2 VMware Workstation
* **Status on Windows 11 ARM64:** Broadcom **does not provide an ARM64 release of VMware Workstation** for Windows hosts. VMware Workstation is strictly x86-64. VMware Fusion is exclusive to Apple Silicon macOS.
* **Implication:** VMware Workstation cannot execute ARM64 virtual machines on a Snapdragon Windows laptop.
* **Compatibility Strategy:** Provide a portable `.vmx` + `.vmdk` specification for users who transfer the VM image to VMware Fusion on Apple Silicon or VMware ESXi on ARM, while prioritizing QEMU and VirtualBox on Windows ARM64.

### 3.3 QEMU ARM64 System Emulation (The Primary Working Path)
* **Status on Windows 11 ARM64:** Fully supported natively.
* **Capabilities:**
  1. **Full Architectural EL2:** Executing `qemu-system-aarch64 -machine virt,virtualization=on -cpu max,pauth-impdef=on` provides complete architectural ARMv8.6-A EL2, `FEAT_NV2`, pointer authentication, GICv3, and 16 KiB translation granules directly in user space.
  2. **Zero Modification to Host:** Runs as an ordinary Windows user application without rebooting, without touching BitLocker, and without altering firmware settings.
  3. **Complete Device Emulation:** Provides PL011 UART, standard GICv3, USB tablet/keyboard, RAMFB linear display, and VirtIO / NVMe virtual disk backing.

---

## 4. Dual-Backend Architecture Design

```
                     ┌─────────────────────────────────────────┐
                     │     Shared Apple Compatibility Core     │
                     │           (platform/shared/)            │
                     │                                         │
                     │  - SPTM / TXM Monitor Contracts         │
                     │  - 16 KiB -> 4 KiB Shadow Page Tables   │
                     │  - Virtual Apple Interrupt Controller   │
                     │  - Virtual Apple Timebase & Watchdog    │
                     │  - Virtual Apple NVMe Storage (ANS2)    │
                     │  - Apple DeviceTree Serializer          │
                     └────────────────────┬────────────────────┘
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  ▼                                               ▼
   ┌─────────────────────────────┐                 ┌─────────────────────────────┐
   │    Native Hardware Backend  │                 │   Virtual Machine Backend   │
   │     (platform/native/)      │                 │    (platform/virtual/)      │
   │                             │                 │                             │
   │ - Qualcomm Oryon v1 SoC     │                 │ - Standard ARM64 Virt Model │
   │ - slbounce + Secure Launch  │                 │ - QEMU System Emulation     │
   │ - q1n1 Hardware Stager      │                 │ - VirtualBox Appliance OVF  │
   │ - Physical GICv3 & GENI     │                 │ - Portable VMware VMX/VMDK  │
   │ - Direct Host NVMe Access   │                 │ - Dedicated Virtual Disk    │
   │ - Physical 2880x1620 OLED   │                 │ - Standard RAMFB / GOP      │
   └─────────────────────────────┘                 └─────────────────────────────┘
```

---

## 5. Virtual Storage & Disk Management Specification

1. **Isolation Guarantee:** The virtual backend operates exclusively against a self-contained disk image (`.qcow2`, `.vdi`, or `.vmdk`). Raw physical drive access (`\\.\PhysicalDriveX`) is strictly prohibited.
2. **ANS2 Block Bridge:** The virtual ANS2 controller maps Apple NVMe I/O commands to the virtual disk file:
   - Sector size: 4096 bytes (Apple 4K LBA contract).
   - Default capacity: 64 GiB (sparse allocation).
   - Snapshot support: Differential QCOW2 backing chains or VDI snapshot trees.
   - Persistence modes: Persistent (read/write committed to disk) or Disposable (writes discarded on VM exit).

---

## 6. Testing Milestones & Validation Gates

* **M1 — Virtual Platform Initialization:** VM initializes virtual CPU, memory map, GICv3, and boot firmware.
* **M2 — Snapintosh Monitor Initialization:** Virtual backend initializes the EL2 monitor without touching host hardware.
* **M3 — Guest Kernel Boot:** Unmodified stock macOS 27 kernelcache boots in the virtualized environment.
* **M4 — Userspace Initialization:** Kernel mounts root filesystem from virtual disk and launches launchd.
* **M5 — Graphical Desktop:** WindowServer initializes framebuffer and renders macOS desktop.
* **M6 — Basic Usability:** Virtual keyboard, mouse, storage, and networking function reliably.
* **M7 — VM Stability:** Validate clean shutdown, restart, snapshot save, and snapshot restoration.
