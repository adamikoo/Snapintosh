# Snapintosh Linux Boot-Validation & Diagnostic Audit

**Target Evaluation Environment:** Linux x86_64 host (Ubuntu 24.04 LTS, QEMU 8.2.2 AArch64 TCG)
**Final Target Architecture:** Snapdragon X1 Elite (X1E-78-100), Windows 11 ARM64
**Date:** March 2026
**Status:** In Progress (Tooling, Firmware, & Virtual Platform verified; XNU/GUI blocked by unredistributed restore images and GPIO interrupt controller matching)

---

## 1. Linux Execution Environment & Architectural Capabilities

* **Host Machine:** Linux devbox `6.8.0 #1 SMP PREEMPT_DYNAMIC` x86_64
* **Host Processor:** Intel(R) Xeon(R) CPU @ 2.30GHz (4 vCPUs allocated)
* **Host RAM:** 7.8 GiB total (~7.0 GiB available)
* **KVM Acceleration (`/dev/kvm`):** Absent. Furthermore, x86_64 KVM cannot execute an AArch64 guest directly.
* **QEMU Acceleration Mode:** `tcg,thread=multi` (`qemu-system-aarch64` 8.2.2).
* **Virtual CPU Profile:** `-cpu max,pauth-impdef=on`
* **Virtualization Extensions (EL2):** Emulated via QEMU TCG `FEAT_NV2` and stage-2 translation.
* **Display / Input:** RAMFB (Linear Framebuffer) + QEMU XHCI (USB Keyboard & Tablet).

---

## 2. Validation Checkpoints & Observed Runtime Status

| Checkpoint | Scope | Verified Status | Observed Evidence & Blocking Factor |
| :--- | :--- | :--- | :--- |
| **QEMU Launch** | Process & Arguments | **PASS** | `qemu-system-aarch64` boots with `virt,virtualization=on,gic-version=3`. |
| **Firmware** | EDK2 UEFI Init | **PASS** | EDK2 AArch64 UEFI initializes; framebuffer renders TianoCore splash (`evidence/linux-macos27-boot/screenshots/01-linux-firmware-boot.png`). |
| **Bootloader** | q1n1 Loader & Proxy | **BLOCKED** | Standalone `q1n1.efi` payload not built/present in repository tree (`q1n1` submodule required). |
| **Restore Assets** | macOS 27 Files | **BLOCKED** | Non-redistributable Apple restore files (`kernelcache.release.mac17p`, `basesystem-26A428.apfs`, `DeviceTree.j700ap`) not checked into git repository. |
| **XNU Kernel Boot** | Kernel Handoff | **BLOCKED** | Blocked pending restore assets and resolving `AppleGPIOICController.cpp:459` service matching. |
| **Graphical Session** | WindowServer Desktop | **BLOCKED** | Dependent on resolving GPIO interrupt dependencies and display initialization under macOS userspace. |

---

## 3. Detailed Technical Investigation: `AppleGPIOICController.cpp:459`

In upstream Apple Silicon device matching:
1. `AppleGPIOICController` verifies device-tree nodes under `/device-tree/arm-io/gpio0`, `aop-gpio`, `mtp-gpio`, `nub-gpio`, and `smc-gpio`.
2. Line 459 in `AppleGPIOICController.cpp` validates the phandle resolution and interrupt group routing for peripheral pin multiplexers.
3. When booting in a synthetic virtualized device tree without matching physical pins or interrupt parent linkages, `AppleGPIOICController` fails registration, stalling driver initialization for dependent input and display interfaces needed by `WindowServer`.

---

## 4. Automated Reproduction Instructions

To run the automated boot validation harness on Linux:
```bash
python3 tools/validate-linux-boot.py
```
Outputs and logs are saved to `evidence/linux-macos27-boot/logs/`.
