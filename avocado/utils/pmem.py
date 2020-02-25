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
# Copyright (C) IBM 2020 - Harish <harish@linux.vnet.ibm.com>
#
# Author: Harish <harish@linux.vnet.ibm.com>
#


import re
import json
import glob
import logging

from . import process
from . import genio

log = logging.getLogger('avocado.test')


class PMemException(Exception):
    """
    Error raised for all PMem failures
    """
    def __init__(self, additional_text=None):  # pylint: disable=W0231
        self.additional_text = additional_text

    def __str__(self):
        return ("Command failed.\ninfo: %s" % self.additional_text)


class PMem:
    """
    PMem class which provides function to perform ndctl and daxctl operations

    This class can be used only if ndctl binaries are provided before hand
    """

    def __init__(self, ndctl='ndctl', daxctl='daxctl'):
        """
        Initialize PMem object

        :param ndctl: path to ndctl binary, defaults to ndctl
        :param daxctl: path to daxctl binary, defaults to ndctl
        """
        for lib_bin in [ndctl, daxctl]:
            if process.system('which %s' % lib_bin, shell=True, ignore_status=True):
                raise PMemException("Cannot use library without "
                                    "proper binary %s" % lib_bin)
        self.ndctl = ndctl
        self.daxctl = daxctl

    def run_ndctl_list(self, option=''):
        """
        Get the json of each provided options

        :param option: optional arguments to ndctl list command
        :return: By default returns entire list of json objects
        :rtype: list of json objects
        """
        try:
            json_op = json.loads(process.system_output(
                '%s list %s' % (self.ndctl, option), shell=True))
        except ValueError:
            json_op = []
        return json_op

    @staticmethod
    def run_ndctl_list_val(json_op, field):
        """
        Get the value of a field in given json

        :param json_op: Input Json object
        :param field: Field to find the value from json_op object

        :rtype: Found value type, None ig not found
        """
        for key, value in json_op.items():
            if key == field:
                return value
        return None

    def run_daxctl_list(self, options=''):
        """
        Get the json of each provided options

        :param options: optional arguments to daxctl list command
        :return: By default returns entire list of json objects
        :rtype: list of json objects
        """
        return json.loads(process.system_output(
            '%s list %s' % (self.daxctl, options), shell=True))

    def get_slot_count(self, region):
        """
        Get max slot count in the index area for a  dimm backing a region
        We use region0 - > nmem0

        :param region: Region for which slot count is found
        :return: Number of slots for given region
                 0 in case region is not available/command fails
        :rtype: int
        """
        nmem = "nmem%s" % re.findall(r'\d+', region)[0]
        try:
            json_op = json.loads(process.system_output(
                '%s read-labels -j %s ' % (self.ndctl, nmem), shell=True))
        except ValueError:
            return []
        first_dict = json_op[0]
        index_dict = self.run_ndctl_list_val(first_dict, 'index')[0]
        return self.run_ndctl_list_val(index_dict, 'nslot') - 2

    @staticmethod
    def is_region_legacy(region):
        """
        Check whether we have label index namespace. If legacy we can't create
        new namespaces.

        :param region: Region for which legacy check is made
        :return: True if given region is legacy, else False
        """
        nstype = genio.read_file("/sys/bus/nd/devices/%s"
                                 "/nstype" % region).rstrip("\n")
        if nstype == "4":
            return True
        return False

    @staticmethod
    def check_buses():
        """
        Get buses from sys subsystem to verify persisment devices exist

        :return: List of buses available
        :rtype: list
        """
        return glob.glob('/sys/bus/nd/drivers/nd_bus/ndbus*')

    def disable_region(self, name='all'):
        """
        Disable given region

        :param name: name of the region to be disabled
        :return: True on success
        :raise: :class:`PMemException`, if command fails.
        """
        if process.system('%s disable-region %s' % (self.ndctl, name),
                          shell=True, ignore_status=True):
            raise PMemException("Failed to disable %s region(s)" % name)
        return True

    def enable_region(self, name='all'):
        """
        Enable given region

        :param name: name of the region to be enabled
        :return: True on success
        :raise: :class:`PMemException`, if command fails.
        """
        if process.system('%s enable-region %s' % (self.ndctl, name),
                          shell=True, ignore_status=True):
            raise PMemException("Failed to enable %s region(s)" % name)
        return True

    def disable_namespace(self, namespace='all', region='', bus='',
                          verbose=False):
        """
        Disable namepsaces

        :param namespace: name of the namespace to be disabled
        :param region: Filter namespace by region
        :param bus: Filter namespace by bus
        :param verbose: Enable True command with debug information

        :return: True on success
        :raise: :class:`PMemException`, if command fails.
        """
        args = namespace
        if region:
            args = '%s -r %s' % (args, region)
        if bus:
            args = '%s -b %s' % (args, bus)
        if verbose:
            args = '%s -v' % args

        if process.system('%s disable-namespace %s' % (self.ndctl, args),
                          shell=True, ignore_status=True):
            raise PMemException('Namespace disable failed for %s' % namespace)
        return True

    def enable_namespace(self, namespace='all', region='', bus='',
                         verbose=False):
        """
        Enable namepsaces

        :param namespace: name of the namespace to be enabled
        :param region: Filter namespace by region
        :param bus: Filter namespace by bus
        :param verbose: Enable True command with debug information

        return: True on success
        :raise: :class:`PMemException`, if command fails.
        """
        args = namespace
        if region:
            args = '%s -r %s' % (args, region)
        if bus:
            args = '%s -b %s' % (args, bus)
        if verbose:
            args = '%s -v' % args

        if process.system('%s enable-namespace %s' % (self.ndctl, args),
                          shell=True, ignore_status=True):
            raise PMemException('Namespace enable failed for "%s"' % namespace)
        return True

    def create_namespace(self, region='', bus='', n_type='pmem', mode='fsdax',
                         memmap='dev', name='', size='', uuid='',
                         sector_size='', align='', reconfig='', force=False,
                         autolabel=False):
        """
        Creates namespace with specified options

        :param region: Region on which namespace has to be created
        :param bus: Bus with which namespace has to be created
        :param n_type: Type of namespace to be created [pmem/blk]
        :param mode: Mode of namespace to be created, defaults to fsdax
        :param memmap: Metadata mapping for created namespace
        :param name: Optional name provided for namespace
        :param size: Size with which namespace has to be created
        :param uuid: Optional uuid provided for namespace
        :param sector_size: Sector size with which namespace has to be created
        :param align: Alignment with which namespace has to be created
        :param reconfig: Optionally reconfigure namespace providing existing
                         namespace/region name
        :param force: Force creation of namespace
        :param autolabel: Optionally autolabel the namespace
        :return: True on success
        :raise: :class:`PMemException`, if command fails.
        """
        args_dict = {region: '-r', bus: '-b', name: '-n', size: '-s',
                     uuid: '-u', sector_size: '-l', align: '-a',
                     reconfig: '-e'}
        minor_dict = {force: '-f', autolabel: '-L'}
        args = '-t %s -m %s ' % (n_type, mode)

        if mode in ['fsdax', 'devdax']:
            args += ' -M %s' % memmap
        for option in list(args_dict.keys()):
            if option:
                args += ' %s %s' % (args_dict[option], option)
        for option in list(minor_dict.keys()):
            if option:
                args += ' %s' % minor_dict[option]

        if (self.is_region_legacy(region) and not reconfig):
            namespace = "namespace%s.0" % re.findall(r'\d+', region)[0]
            args += " -f -e " + namespace

        if process.system('%s create-namespace %s' % (self.ndctl, args),
                          shell=True, ignore_status=True):
            raise PMemException('Namespace create command failed')
        return True

    def destroy_namespace(self, namespace='all', region='', bus='',
                          force=False):
        """
        Destroy namepsaces, skipped in case of legacy namespace

        :param namespace: name of the namespace to be destroyed
        :param region: Filter namespace by region
        :param bus: Filter namespace by bus
        :param force: Force a namesapce to be destroyed

        :return: True on Success
        :raise: :class:`PMemException`, if command fails.
        """
        if (region and self.is_region_legacy(region)):
            return True

        args = namespace
        args_dict = {region: '-r', bus: '-b'}
        for option in list(args_dict.keys()):
            if option:
                args += ' %s %s' % (args_dict[option], option)
        if force:
            args += ' -f'

        if process.system('%s destroy-namespace %s' % (self.ndctl, args),
                          shell=True, ignore_status=True):
            raise PMemException('Namespace destroy command failed')
        return True
