# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: 2025 Advanced Micro Devices, Inc.
# Author: Dheeraj Kumar Srivastava <dheerajkumar.srivastava@amd.com>

"""
APIs for vfio ioctls.
"""

import os
import ctypes
import struct
from fcntl import ioctl
from avocado.utils import pci


def get_vfio_container_fd():
    """
    Get VFIO container file descriptor
    """
    container_fd = ctypes.c_int(os.open("/dev/vfio/vfio", os.O_RDWR))
    if container_fd.value < 0:
        raise ValueError("Failed to open VFIO container")
    return container_fd.value


def check_vfio_container(
    container_fd,
    VFIO_GET_API_VERSION,
    VFIO_API_VERSION,
    VFIO_CHECK_EXTENSION,
    VFIO_TYPE_IOMMU,
):
    """
    Validate the VFIO container by verifying the API version and ensuring the required
    IOMMU extension is supported. If either validation fails, the test is cancelled with
    an appropriate message.

    :param container_fd: VFIO container file descriptor
    :param VFIO_GET_API_VERSION: ioctl to retrieve the VFIO container API version
    :param VFIO_API_VERSION: expected VFIO API version
    :param VFIO_CHECK_EXTENSION:  ioctl to check IOMMU extension support
    :param VFIO_TYPE_IOMMU: expected VFIO IOMMU type
    """
    if ioctl(container_fd, VFIO_GET_API_VERSION) != VFIO_API_VERSION:
        raise ValueError("Failed to get right API version")

    if not ioctl(container_fd, VFIO_CHECK_EXTENSION, VFIO_TYPE_IOMMU):
        raise ValueError("Does not support type 1 IOMMU")


def get_iommu_group_fd(device, VFIO_GROUP_GET_STATUS, VFIO_GROUP_FLAGS_VIABLE):
    """
    Get IOMMU group fd for the PCI device

    :param device: full pci address including domain (0000:03:00.0)
    :param VFIO_GROUP_GET_STATUS: ioctl to get IOMMU group status
    :param VFIO_GROUP_FLAGS_VIABLE: ioctl to check if IOMMU group is viable
    """
    vfio_group = f"/dev/vfio/{pci.get_iommu_group(device)}"
    group_fd = os.open(vfio_group, os.O_RDWR)
    if group_fd < 0:
        raise ValueError(f"Failed to open {vfio_group}, {group_fd}")

    argsz = struct.calcsize("II")
    group_status_request = struct.pack("II", argsz, 2)
    group_status_response = ioctl(group_fd, VFIO_GROUP_GET_STATUS, group_status_request)
    group_status = struct.unpack("II", group_status_response)

    if not group_status[1] & VFIO_GROUP_FLAGS_VIABLE:
        raise ValueError("Group not viable, are all devices attached to vfio?")

    return group_fd


def attach_group_to_container(group_fd, container_fd, VFIO_GROUP_SET_CONTAINER):
    """
    Attach the IOMMU group of PCI device to the VFIO container.

    :param group_fd: IOMMU group file descriptor
    :param container_fd: VFIO container file descriptor
    :param VFIO_GROUP_SET_CONTAINER: vfio ioctl to add IOMMU group to the container fd
    """

    ret = ioctl(group_fd, VFIO_GROUP_SET_CONTAINER, ctypes.c_void_p(container_fd))
    if ret:
        raise ValueError(
            "Failed to Attached PCI device's IOMMU group to the VFIO container"
        )


def deattach_group_from_container(group_fd, container_fd, VFIO_GROUP_UNSET_CONTAINER):
    """
    Deattach the IOMMU group of PCI device from VFIO container

    """
    ret = ioctl(group_fd, VFIO_GROUP_UNSET_CONTAINER, ctypes.c_void_p(container_fd))
    if ret:
        raise ValueError(
            "Failed to deattach PCI device's IOMMU group from VFIO container"
        )


def get_device_fd(device, group_fd, VFIO_GROUP_GET_DEVICE_FD):
    """
    Get device file descriptor

    :param device: full pci address including domain (0000:03:00.0)
    :param group_fd: IOMMU group file descriptor
    :param VFIO_GROUP_GET_DEVICE_FD: ioctl to get device fd
    """
    buf = ctypes.create_string_buffer(device.encode("utf-8") + b"\x00")
    device_fd = ioctl(group_fd, VFIO_GROUP_GET_DEVICE_FD, buf)
    if device_fd < 0:
        raise ValueError("Failed to get VFIO device FD")

    return device_fd


def vfio_device_supports_irq(
    device_fd, VFIO_PCI_MSIX_IRQ_INDEX, VFIO_DEVICE_GET_IRQ_INFO, count
):
    """
    Check if device supports atleast count number of interrupts

    :param device_fd: device file descriptor
    :param VFIO_PCI_MSIX_IRQ_INDEX: vfio ioctl to get irq index for MSIX
    :param VFIO_DEVICE_GET_IRQ_INFO: vfio ioctl to get vfio device irq information
    :param count: Number of IRQs the device should support
    :return: True if supported, False otherwise
    """
    argsz = struct.calcsize("IIII")
    index = VFIO_PCI_MSIX_IRQ_INDEX
    irq_info_request = struct.pack("IIII", argsz, 1, index, 1)
    irq_info_response = ioctl(device_fd, VFIO_DEVICE_GET_IRQ_INFO, irq_info_request)
    nirq = (struct.unpack("IIII", irq_info_response))[3]
    if nirq < count:
        return False
    return True
