# SPDX-License-Identifier: MIT
"""Oracle VirtualBox ARM64 appliance generator for Snapintosh.

Produces an importable Open Virtualization Appliance (.ovf) and native (.vbox)
configuration tailored for Windows 11 ARM64 and the Snapdragon X1 Elite.
"""
from dataclasses import dataclass
from pathlib import Path
import uuid
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Dict, Any


@dataclass(frozen=True)
class VirtualBoxConfig:
    vm_name: str = "Snapintosh-macOS-Sequoia"
    guest_os_type: str = "MacOS_ARM64"
    cpu_count: int = 6                  # 6 vCPUs for optimal scheduling on 12-core X1 Elite
    memory_mb: int = 6144               # 6 GiB RAM (conservative allocation for 16 GB host)
    vram_mb: int = 128                  # 128 MB VRAM for 1920x1080 display
    firmware: str = "EFI"
    storage_controller: str = "NVMe"
    network_adapter: str = "VirtIO"
    pointing_device: str = "USBTablet"
    keyboard_type: str = "USBKeyboard"


class VirtualBoxApplianceBuilder:
    """Constructs importable appliances and machine configurations for VirtualBox 7.x."""

    @classmethod
    def generate_vbox_xml(cls, disk_vdi_path: Path, output_vbox_path: Path,
                          config: VirtualBoxConfig = VirtualBoxConfig()) -> Path:
        """Generates a native VirtualBox 7.x .vbox XML file."""
        vm_uuid = str(uuid.uuid4())
        disk_uuid = str(uuid.uuid4())
        output_vbox_path.parent.mkdir(parents=True, exist_ok=True)

        vbox_content = f"""<?xml version="1.0"?>
<VirtualBox xmlns="http://www.virtualbox.org/" version="1.19-windows">
  <Machine uuid="{{{vm_uuid}}}" name="{config.vm_name}" OSType="{config.guest_os_type}" currentSnapshot="{{00000000-0000-0000-0000-000000000000}}">
    <MediaRegistry>
      <HardDisks>
        <HardDisk uuid="{{{disk_uuid}}}" location="{disk_vdi_path.name}" format="VDI" type="Normal"/>
      </HardDisks>
    </MediaRegistry>
    <Hardware>
      <CPU count="{config.cpu_count}">
        <PAE enabled="true"/>
        <LongMode enabled="true"/>
        <HardwareVirtExLargePages enabled="true"/>
      </CPU>
      <Memory RAMSize="{config.memory_mb}"/>
      <Firmware type="{config.firmware}"/>
      <HID Pointing="{config.pointing_device}" Keyboard="{config.keyboard_type}"/>
      <Display VRAMSize="{config.vram_mb}" monitorCount="1" accelerate3D="false"/>
      <BIOS>
        <IOAPIC enabled="true"/>
        <SmbiosUuidLittleEndian enabled="true"/>
      </BIOS>
      <Network>
        <Adapter slot="0" enabled="true" MACAddress="080027A16C28" type="{config.network_adapter}">
          <NAT/>
        </Adapter>
      </Network>
      <AudioAdapter enabled="false"/>
      <StorageControllers>
        <StorageController name="{config.storage_controller}" type="NVMe" PortCount="1" useHostIOCache="false" Bootable="true">
          <AttachedDevice type="HardDisk" hotpluggable="false" port="0" device="0">
            <Image uuid="{{{disk_uuid}}}"/>
          </AttachedDevice>
        </StorageController>
      </StorageControllers>
    </Hardware>
  </Machine>
</VirtualBox>
"""
        with open(output_vbox_path, 'w', encoding='utf-8') as f:
            f.write(vbox_content)
        return output_vbox_path

    @classmethod
    def generate_ovf_descriptor(cls, disk_vmdk_path: Path, output_ovf_path: Path,
                                config: VirtualBoxConfig = VirtualBoxConfig()) -> Path:
        """Generates an Open Virtualization Format (.ovf) descriptor for 1-click appliance import."""
        output_ovf_path.parent.mkdir(parents=True, exist_ok=True)
        file_size = disk_vmdk_path.stat().st_size if disk_vmdk_path.is_file() else 0
        capacity_bytes = 64 * (1024 ** 3)

        ovf_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Envelope xmlns="http://schemas.dmtf.org/ovf/envelope/1"
          xmlns:cim="http://schemas.dmtf.org/wbem/wscim/1/common"
          xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1"
          xmlns:rasd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData"
          xmlns:vssd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <References>
    <File ovf:href="{disk_vmdk_path.name}" ovf:id="file1" ovf:size="{file_size}"/>
  </References>
  <DiskSection>
    <Info>Virtual disk information</Info>
    <Disk ovf:capacity="{capacity_bytes}" ovf:diskId="vmdisk1" ovf:fileRef="file1"
          ovf:format="http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized"/>
  </DiskSection>
  <VirtualSystem ovf:id="{config.vm_name}">
    <Info>Snapintosh macOS 27 Sequoia Virtual Appliance</Info>
    <Name>{config.vm_name}</Name>
    <OperatingSystemSection ovf:id="100">
      <Info>macOS 27 Sequoia ARM64 Guest</Info>
      <Description>Apple macOS (ARM64)</Description>
    </OperatingSystemSection>
    <VirtualHardwareSection>
      <Info>Virtual hardware requirements</Info>
      <System>
        <vssd:ElementName>Virtual Hardware Family</vssd:ElementName>
        <vssd:InstanceID>0</vssd:InstanceID>
        <vssd:VirtualSystemType>virtualbox-2.2</vssd:VirtualSystemType>
      </System>
      <Item>
        <rasd:Caption>{config.cpu_count} virtual CPUs</rasd:Caption>
        <rasd:Description>Number of virtual CPUs</rasd:Description>
        <rasd:ElementName>CPU</rasd:ElementName>
        <rasd:InstanceID>1</rasd:InstanceID>
        <rasd:ResourceType>3</rasd:ResourceType>
        <rasd:VirtualQuantity>{config.cpu_count}</rasd:VirtualQuantity>
      </Item>
      <Item>
        <rasd:AllocationUnits>byte * 2^20</rasd:AllocationUnits>
        <rasd:Caption>{config.memory_mb} MB of memory</rasd:Caption>
        <rasd:Description>Memory Size</rasd:Description>
        <rasd:ElementName>Memory</rasd:ElementName>
        <rasd:InstanceID>2</rasd:InstanceID>
        <rasd:ResourceType>4</rasd:ResourceType>
        <rasd:VirtualQuantity>{config.memory_mb}</rasd:VirtualQuantity>
      </Item>
      <Item>
        <rasd:Address>0</rasd:Address>
        <rasd:Caption>NVMe Controller</rasd:Caption>
        <rasd:Description>Apple ANS2 / NVMe Storage Controller</rasd:Description>
        <rasd:ElementName>NVMe Controller</rasd:ElementName>
        <rasd:InstanceID>3</rasd:InstanceID>
        <rasd:ResourceSubType>NVMe</rasd:ResourceSubType>
        <rasd:ResourceType>20</rasd:ResourceType>
      </Item>
      <Item>
        <rasd:AddressOnParent>0</rasd:AddressOnParent>
        <rasd:Caption>disk1</rasd:Caption>
        <rasd:Description>Snapintosh Dedicated Virtual Disk</rasd:Description>
        <rasd:ElementName>Hard Disk</rasd:ElementName>
        <rasd:HostResource>/disk/vmdisk1</rasd:HostResource>
        <rasd:InstanceID>4</rasd:InstanceID>
        <rasd:Parent>3</rasd:Parent>
        <rasd:ResourceType>17</rasd:ResourceType>
      </Item>
    </VirtualHardwareSection>
  </VirtualSystem>
</Envelope>
"""
        with open(output_ovf_path, 'w', encoding='utf-8') as f:
            f.write(ovf_xml)
        return output_ovf_path
