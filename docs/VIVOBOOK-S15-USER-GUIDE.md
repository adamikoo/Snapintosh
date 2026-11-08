# ASUS Vivobook S 15 Snapintosh User Guide

This guide describes how to run and operate the Snapintosh environment on the **ASUS Vivobook S 15 (S5507QA)** powered by the **Qualcomm Snapdragon X Elite (X1E-78-100)**.

---

## 1. Quick Start

1. Look on your Windows Desktop for the **Snapintosh** shortcut (`Snapintosh.lnk`).
2. Double-click **Snapintosh** (or run `Snapintosh.exe` in this repository).
3. The launcher will automatically:
   - Verify your processor architecture (Native ARM64).
   - Verify your memory status and activate the **16 GB Hardware Profile** (8 GiB guest allocation).
   - Check power status and enforce safety thermal/battery guards (> 50% battery or AC power).
   - Audit required Apple firmware and prerequisite files.
   - Stage the bootloader environment under `%LOCALAPPDATA%\Snapintosh\`.

---

## 2. Supply Your Apple Firmware Files

Per project licensing and safety rules, proprietary Apple software and restore images are not distributed in this repository.

To supply the required macOS 27 (build 26A428) components:
1. Place the Apple restore image `UniversalMac_27.0_26A428_Restore.ipsw` in the `downloads/` directory.
2. Run the extraction utility:
   ```cmd
   python tools/extract-firmware.py downloads/UniversalMac_27.0_26A428_Restore.ipsw j700ap
   ```
3. This creates:
   - `downloads/extracted/j700ap/kernelcache.release.mac17p`
   - `downloads/extracted/j700ap/DeviceTree.j700ap`
   - `downloads/extracted/j700ap/sptm.t8140.release`
   - `downloads/extracted/j700ap/txm.macosx.release`
4. Re-open **Snapintosh** and select Option `2` to verify all prerequisites are satisfied.

---

## 3. Launcher Options Explained

- **Option 1: Run Full System Diagnostic & Hardware Audit**
  Re-queries system processors, display mode (2880x1620 @ 120Hz), memory availability, and power supply.
- **Option 2: Audit Apple Firmware & Prerequisite Files**
  Checks whether the extracted J700 macOS boot components are present and correctly hashed.
- **Option 3: Prepare Boot Environment (16 GB S15 Profile)**
  Generates `snapintosh_boot.cfg` and stages all loader files into `%LOCALAPPDATA%\Snapintosh\boot\`.
- **Option 4: Rerun As Administrator (Request UAC Elevation)**
  Elevates the launcher with Administrator privileges for modifying UEFI/BCD firmware boot sequences.
- **Option 5: Restart Into UEFI Firmware Settings (Safe Mode)**
  Executes an orderly Windows restart directly into the Insyde UEFI BIOS settings screen.
- **Option 6: View Safety & System Recovery Instructions**
  Displays critical guidelines regarding Windows preservation and BitLocker recovery.
- **Option 7: Refresh Desktop Shortcut**
  Re-creates or repairs the desktop shortcut `%USERPROFILE%\Desktop\Snapintosh.lnk`.
- **Option 0: Exit**
  Safely saves logs and closes the launcher.

---

## 4. Hardware Safety & System Recovery

- **Windows Protection:** Snapintosh NEVER touches, formats, or overwrites your primary Windows partition (`C:`).
- **BitLocker:** Snapintosh does not disable BitLocker. Always keep your 48-digit BitLocker recovery key backed up on your Microsoft Account or a separate USB drive.
- **Emergency Windows Boot:** If a boot sequence does not complete, simply power off the laptop (hold the power button for 8 seconds). At power on, press **Esc** or **F2** to select **Windows Boot Manager**. Windows will boot completely normally.
- **Battery Guard:** Do not attempt boot experiments below 50% battery. Always keep the official USB-C PD charger connected.
