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


import glob
import json
import logging
import re

from . import genio, path, process

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
        abs_ndctl = path.find_command(ndctl, False)
        if not abs_ndctl:
            raise PMemException("Cannot use library without "
                                "proper ndctl binary")
        self.ndctl = abs_ndctl

        abs_daxctl = path.find_command(daxctl, False)
        if not abs_daxctl:
            raise PMemException("Cannot use library without "
                                "proper daxctl binary")
        self.daxctl = abs_daxctl

    @staticmethod
    def check_subcmd(binary, command):
        """Check if given sub command is supported by binary

        :param command: sub command of ndctl to check for existence
        :return: True if sub command is available
        :rtype: bool
        """
        cmd = "%s --list-cmds" % binary
        out = process.system_output(cmd).decode().splitlines()
        if command in out:
            return True

        return False

    def check_ndctl_subcmd(self, command):
        """Check if given sub command is supported by ndctl"""
        return self.check_subcmd(self.ndctl, command)

    def check_daxctl_subcmd(self, command):
        """Check if given sub command is supported by daxctl"""
        return self.check_subcmd(self.daxctl, command)

    def run_ndctl_list(self, option=''):
        """
        Get the json of each provided options

        :param option: optional arguments to ndctl list command
        :return: By default returns entire list of json objects
        :rtype: list of json objects
        """
        try:
            cmd = '%s list %s' % (self.ndctl, option)
            json_op = json.loads(process.system_output(cmd))
        except ValueError:
            json_op = []
        return json_op

    @staticmethod
    def run_ndctl_list_val(json_op, field):
        """
        Get the value of a field in given json

        :param json_op: Input Json object
        :param field: Field to find the value from json_op object

        :rtype: Found value type, None if not found
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
        cmd = '%s list %s' % (self.daxctl, options)
        return json.loads(process.system_output(cmd))

    def set_dax_memory_online(self, device, region=None, no_movable=False):
        """Set memory from a given devdax device online

        :param device: Device from which memory is to be online
        :param region: Optionally filter device by region
        :param no_movable: Optionally make the memory non-movable

        :return: True if command succeeds
        :rtype: bool
        :raise: :class:`PMemException`, if command fails.
        """
        cmd = '%s online-memory %s' % (self.daxctl, device)
        if region:
            cmd += ' -r %s' % region
        if no_movable:
            cmd += ' --no-movable'
        if process.system(cmd, shell=True, ignore_status=True):
            raise PMemException("Failed to online memory with %s" % device)
        return True

    def set_dax_memory_offline(self, device, region=None):
        """Set memory from a given devdax device offline

        :param device: Device from which memory is to be offline
        :param region: Optionally filter device by region

        :return: True if command succeeds
        :rtype: bool
        :raise: :class:`PMemException`, if command fails.
        """
        cmd = '%s offline-memory %s' % (self.daxctl, device)
        if region:
            cmd += ' -r %s' % region
        if process.system(cmd, shell=True, ignore_status=True):
            raise PMemException("Failed to offline memory with %s" % device)
        return True

    def reconfigure_dax_device(self, device, mode='devdax', region=None,
                               no_online=False, no_movable=False):
        """Reconfigure devdax device into devdax or system-ram mode

        :param device: Device from which memory is to be online
        :param mode: Mode with which device is to be configured, default:devdax
        :param region: Optionally filter device by region
        :param no_online: Optionally don't online the memory(only system-ram)
        :param no_movable: Optionally mark memory non-movable(only system-ram)

        :return: Property of configured device
        :rtype: str
        :raise: :class:`PMemException`, if command fails.
        """
        cmd = '%s reconfigure-device %s -m %s' % (self.daxctl, device, mode)
        if region:
            cmd += ' -r %s' % region
        if no_online:
            cmd += ' -N'
        if no_movable:
            cmd += ' --no-movable'
        device_property = process.run(cmd, shell=True, ignore_status=True)
        if device_property.exit_status:
            raise PMemException("Failed to reconfigure device %s" % device)
        return device_property.stdout_text

    def get_slot_count(self, region):
        """
        Get max slot count in the index area for a dimm backing a region
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
        Get buses from sys subsystem to verify persistent devices exist

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
        Disable namespaces

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
        Enable namespaces

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
        Destroy namespaces, skipped in case of legacy namespace

        :param namespace: name of the namespace to be destroyed
        :param region: Filter namespace by region
        :param bus: Filter namespace by bus
        :param force: Force a namespace to be destroyed

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

    @staticmethod
    def _check_arg(key, kwargs):
        if key in kwargs and kwargs[key]:
            return True
        return False

    @staticmethod
    def _check_add_arg(args_dict, key, kwargs, pop=False):
        if PMem._check_arg(key, kwargs):
            if pop:
                return " %s" % args_dict[key] % kwargs.pop(key)
            return " %s" % args_dict[key] % kwargs.get(key)
        return ""

    @staticmethod
    def _filter_ns_infoblock(namespace, args_dict, kwargs):
        args = ""
        if namespace == "all":
            for key in ['region', 'bus']:
                args += PMem._check_add_arg(args_dict, key, kwargs, pop=True)
        return args

    def write_infoblock(self, namespace='', stdout=False, output=None,
                        **kwargs):
        """
        Write an infoblock to the specified medium.

        :param namespace: Write the infoblock to given namespace
        :param stdout: Write the infoblock to stdout if True
        :param output: Write the infoblock to the file path specified
        :param kwargs:

        Example:
           pmem.write_infoblock(namespace=ns_name, align=align,
                                size=size, mode='devdax')

        :return: True if command succeeds
        :rtype: bool
        :raise: :class:`PMemException`, if command fails.
        """
        if not (namespace or stdout or output):
            raise PMemException("Specify atleast one output medium")

        args_dict = {'region': '-r %s', 'bus': '-b %s', 'mode': '-m %s',
                     'memmap': '-M %s', 'size': '-s %s', 'align': '-a %s',
                     'uuid': '-u %s', 'parent_uuid': '-p %', 'offset': '-O %s'}

        if namespace:
            args = namespace
        elif stdout:
            args = "-c"
        elif output:
            args = "-o %s" % output

        args += self._filter_ns_infoblock(namespace, args_dict, kwargs)
        args += " %s" % args_dict['mode'] % kwargs.pop('mode', 'fsdax')
        args += " %s" % args_dict['memmap'] % kwargs.pop('memmap', 'dev')

        for key, value in kwargs.items():
            if not value:
                continue
            if key in args_dict:
                args += " %s" % args_dict[key] % value
            else:
                raise PMemException("Input not supported for write-infoblock")

        write_cmd = "%s write-infoblock %s" % (self.ndctl, args)
        if process.system(write_cmd, shell=True, ignore_status=True):
            raise PMemException("write-infoblock command failed")
        return True

    def read_infoblock(self, namespace='', inp_file='', **kwargs):
        """
        Read an infoblock from the specified medium

        :param namespace: Read the infoblock from given namespace
        :param inp_file: Input file to read the infoblock from
        :param kwargs:

        Example:
           self.plib.read_infoblock(namespace=ns_name, json_form=True)

        :return: By default return list of json objects, if json_form is True
                 Return as raw data, if json_form is False
                 Return file path if op_file is specified
        :raise: :class:`PMemException`, if command fails.
        """
        if not (namespace or inp_file):
            raise PMemException("Namespace or input file must be specified")

        args_dict = {"region": "-r %s", "bus": "-b %s", "op_file": "-o %s"}
        if namespace:
            args = namespace
        elif inp_file:
            args = "-i %s" % inp_file

        args += self._filter_ns_infoblock(namespace, args_dict, kwargs)
        args += self._check_add_arg(args_dict, 'op_file', kwargs)

        json_form = kwargs.pop('json_form', True)
        verify = kwargs.pop('verify', False)
        if verify:
            args += " -V"
        if json_form:
            args += " -j"

        read_cmd = "%s read-infoblock %s" % (self.ndctl, args)
        ret = process.run(read_cmd, shell=True, ignore_status=True)
        if ret.exit_status:
            raise PMemException("read-infoblock command failed")
        if self._check_arg('op_file', kwargs):
            return kwargs.get('op_file')
        read_op = ret.stdout.decode()
        if json_form:
            read_op = json.loads(read_op)

        return read_op
