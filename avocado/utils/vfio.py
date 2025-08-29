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
# Author: Dheeraj Kumar Srivastava <dheerajkumar.srivastava@amd.com> # pylint: disable=C0401

# pylint: disable=C0402

"""APIs for virtual function I/O management."""


import ctypes
import os
import struct
from fcntl import ioctl

from avocado.utils import pci


def get_vfio_container_fd():
    """get vfio container file descriptor

    :return: file descriptor of the vfio container.
    :rtype: int
    :raises ValueError: if the vfio container cannot be opened.
    """
    try:
        return os.open("/dev/vfio/vfio", os.O_RDWR | os.O_CLOEXEC)
    except OSError as e:
        raise ValueError(f"Failed to open VFIO container: {e}") from e


def check_vfio_container(
    container_fd,
    vfio_get_api_version,
    vfio_api_version,
    vfio_check_extension,
    vfio_type_iommu,
):
    """Validate a vfio container by verifying the api version and ensuring that the
    required iommu extension is supported. If either validation fails, an exception
    is raised with an appropriate message

    :param container_fd: vfio container file descriptor
    :type container_fd: int
    :param vfio_get_api_version: ioctl to retrieve the vfio container api version
    :type vfio_get_api_version: int
    :param vfio_api_version: expected vfio api version
    :type vfio_api_version: int
    :param vfio_check_extension:  ioctl to check iommu extension support
    :type vfio_check_extension: int
    :param vfio_type_iommu: expected vfio iommu type
    :type vfio_type_iommu: int
    :raises ValueError: if the vfio api version is invalid or if the required
                        iommu extension is not supported.
    :return: True if vfio container fd check passes.
    :rtype: bool
    """
    try:
        if ioctl(container_fd, vfio_get_api_version) != vfio_api_version:
            raise OSError("Failed to get right API version")
    except OSError as e:
        raise ValueError(f"Failed to get API version: {e}") from e

    try:
        ioctl(container_fd, vfio_check_extension, vfio_type_iommu)
    except OSError as e:
        raise ValueError(f"does not support type 1 iommu: {e}") from e

    return True


def get_iommu_group_fd(device, vfio_group_get_status, vfio_group_flags_viable):
    """get iommu group fd for the pci device

    :param device: full pci address including domain (0000:03:00.0)
    :type device: str
    :param vfio_group_get_status: ioctl to get iommu group status
    :type vfio_group_get_status: int
    :param vfio_group_flags_viable: ioctl to check if iommu group is viable
    :type vfio_group_flags_viable: int
    :raises ValueError: if the vfio group device cannot be opened or the group
                        is not viable.
    :return: file descriptor for the iommu group.
    :rtype: int
    """
    vfio_group = f"/dev/vfio/{pci.get_iommu_group(device)}"
    try:
        group_fd = os.open(vfio_group, os.O_RDWR)
    except OSError as e:
        raise ValueError(f"Failed to open {vfio_group}: {e}") from e

    argsz = struct.calcsize("II")
    group_status_request = struct.pack("II", argsz, 2)
    group_status_response = ioctl(group_fd, vfio_group_get_status, group_status_request)
    group_status = struct.unpack("II", group_status_response)

    if not group_status[1] & vfio_group_flags_viable:
        raise ValueError("Group not viable, are all devices attached to vfio?")

    return group_fd


def attach_group_to_container(group_fd, container_fd, vfio_group_set_container):
    """attach the iommu group of pci device to the vfio container.

    :param group_fd: iommu group file descriptor
    :type group_fd: int
    :param container_fd: vfio container file descriptor
    :type container_fd: int
    :param vfio_group_set_container: vfio ioctl to add iommu group to the container fd
    :type vfio_group_set_container: int
    :raises ValueError: if attaching the group to the container fails.
    """

    try:
        ioctl(group_fd, vfio_group_set_container, ctypes.c_void_p(container_fd))
    except OSError as e:
        raise ValueError(
            f"failed to attach pci device's iommu group to the vfio container: {e}"
        ) from e


def detach_group_from_container(group_fd, container_fd, vfio_group_unset_container):
    """detach the iommu group of pci device from vfio container

    :param group_fd: iommu group file descriptor
    :type group_fd: int
    :param container_fd: vfio container file descriptor
    :type container_fd: int
    :param vfio_group_unset_container: vfio ioctl to detach iommu group from the
                                       container fd
    :type vfio_group_unset_container: int
    :raises ValueError: if detaching the group to the container fails.
    """

    try:
        ioctl(group_fd, vfio_group_unset_container, ctypes.c_void_p(container_fd))
    except OSError as e:
        raise ValueError(
            f"failed to detach pci device's iommu group from vfio container: {e}"
        ) from e


def get_device_fd(device, group_fd, vfio_group_get_device_fd):
    """Get device file descriptor

    :param device: full pci address including domain (0000:03:00.0)
    :type device: str
    :param group_fd: iommu group file descriptor
    :type group_fd: int
    :param vfio_group_get_device_fd: ioctl to get device fd
    :type vfio_group_get_device_fd: int
    :raises ValueError: if not able to get device descriptor
    :return: device descriptor
    :rtype: int
    """
    buf = ctypes.create_string_buffer(device.encode("utf-8") + b"\x00")
    try:
        device_fd = ioctl(group_fd, vfio_group_get_device_fd, buf)
    except OSError as e:
        raise ValueError("failed to get vfio device fd") from e

    return device_fd


def vfio_device_supports_irq(
    device_fd, vfio_pci_msix_irq_index, vfio_device_get_irq_info, count
):
    """Check if device supports at least count number of interrupts

    :param device_fd: device file descriptor
    :type device_fd: int
    :param vfio_pci_msix_irq_index: vfio ioctl to get irq index for msix
    :type vfio_pci_msix_irq_index: int
    :param vfio_device_get_irq_info: vfio ioctl to get vfio device irq information
    :type vfio_device_get_irq_info: int
    :param count: number of irqs the device should support
    :type count: int
    :return: true if supported, false otherwise
    :rtype: bool
    """
    argsz = struct.calcsize("IIII")
    index = vfio_pci_msix_irq_index
    irq_info_request = struct.pack("IIII", argsz, 1, index, 1)
    irq_info_response = ioctl(device_fd, vfio_device_get_irq_info, irq_info_request)
    nirq = (struct.unpack("IIII", irq_info_response))[3]
    if nirq < count:
        return False
    return True
