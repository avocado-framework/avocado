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
# Copyright: 2020 IBM
# Author: Narasimhan V <sim@linux.vnet.ibm.com>
# Author: Venkat Rao B <vrbagal1@linux.vnet.ibm.com>

"""
This module provides APIs to work with software raid.
"""


import logging
import time

from avocado.utils import process

LOG = logging.getLogger(__name__)


class SoftwareRaid:
    """
    Perform software raid related operations.

    :param name: Name of the software raid to be created
    :type name: str
    :param level: Level of software raid to be created
    :type name: str
    :param disks: List of disks for software raid
    :type disks: list
    :param metadata: Metadata level for software raid
    :type metadata: str
    :param spare_disks: List of spare disks for software raid
    :type spare_disks: list
    """

    def __init__(self, name, level, disks, metadata, spare_disks=None):
        self.name = name
        self.level = level
        self.metadata = metadata
        self.disks = disks
        self.remadd = ""
        if not spare_disks:
            self.spare_disks = []
        else:
            self.spare_disks = spare_disks

    def _run_command(self, cmd, log_details=True, check_recovery=False):
        if process.system(cmd, ignore_status=True, shell=True) != 0:
            if log_details:
                self.get_detail()
            return False
        if check_recovery:
            while self.is_recovering():
                time.sleep(30)
        if log_details:
            self.get_detail()
        return True

    def add_disk(self, disk):
        """
        Adds disk specified to software raid.

        :param disk: disk to be added.
        :type disk: str

        :return: True if add is successful, False otherwise.
        :rtype: bool
        """
        cmd = f"mdadm {self.name} --add {disk}"
        return self._run_command(cmd)

    def assemble(self):
        """
        Assembles software raid.

        :return: True if assembled, False otherwise.
        :rtype: bool
        """
        cmd = f"mdadm --assemble {self.name} {' '.join(self.disks)}"
        if self.spare_disks:
            cmd += f" {' '.join(self.spare_disks)}"
        return self._run_command(cmd, check_recovery=True)

    def clear_superblock(self):
        """
        Zeroes superblocks in member devices of raid.

        :return: True if zeroed, False otherwise.
        :rtype: bool
        """
        cmd = f"mdadm --zero-superblock {' '.join(self.disks)}"
        if self.spare_disks:
            cmd += f" {' '.join(self.spare_disks)}"
        return self._run_command(cmd, log_details=False)

    def create(self):
        """
        Creates software raid.

        :return: True if raid is created. False otherwise.
        :rtype: bool
        """
        cmd = f"yes | mdadm --create --assume-clean {self.name}"
        cmd += f" --level={self.level}"
        cmd += f" --raid-devices={len(self.disks)} {' '.join(self.disks)}"
        cmd += f" --metadata={self.metadata}"
        if self.spare_disks:
            cmd += (
                f" --spare-devices={len(self.spare_disks)} "
                f"{' '.join(self.spare_disks)}"
            )
        cmd += " --verbose --force"
        return self._run_command(cmd)

    def get_detail(self):
        """
        Returns mdadm details.

        :return: mdadm --detail output
        :rtype: str
        """
        cmd = f"mdadm --detail {self.name}"
        output = process.run(cmd, ignore_status=True, shell=True)
        return output.stdout_text

    def is_recovering(self):
        """
        Checks if raid is recovering.

        :return: True if recovering, False otherwise.
        :rtype: bool
        """
        LOG.debug("RECOVERY")
        for line in self.get_detail().splitlines():
            if "State" in line and "recovering" in line:
                return True
        return False

    def remove_disk(self, disk):
        """
        Removes disk specified from software raid.

        :param disk: disk to be removed.
        :type disk: str

        :return: True if remove is successful, False otherwise.
        :rtype: bool
        """
        cmd = f"mdadm {self.name} --fail {disk} --remove {disk}"
        return self._run_command(cmd)

    def stop(self):
        """
        Stops software raid.

        :return: True if stopped, False otherwise.
        :rtype: bool
        """
        cmd = f"mdadm --manage {self.name} --stop"
        return self._run_command(cmd, log_details=False)

    def exists(self):
        """
        checks if softwareraid exists or not

        :mdadm: must be super-user(root) to perform this action

        :return: True if exists, False otherwise.
        :rtype: bool
        """
        cmd = f"mdadm --detail --test {self.name}"
        result = process.run(cmd, shell=True, sudo=True, ignore_status=True)
        if result.exit_status == 4:
            return False
        return True
