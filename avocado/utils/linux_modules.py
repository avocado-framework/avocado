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
# This code was inspired in the autotest project,
#
# client/base_utils.py
# Original author: Ross Brattain <ross.b.brattain@intel.com>
#
# Copyright: 2016 IBM
# Authors : Praveen K Pandey <praveen@linux.vnet.ibm.com>

"""
Linux kernel modules APIs
"""

import logging
import platform
import re
from enum import Enum

from avocado.utils import astring, data_structures, process

LOG = logging.getLogger(__name__)


class ModuleConfig(Enum):
    #: Config commented out or not set
    NOT_SET = object()
    #: Config compiled as loadable module (`=m`)
    MODULE = object()
    #: Config built-in to kernel (`=y`)
    BUILTIN = object()


def load_module(module_name):
    """
    Checks if a module has already been loaded.
    :param module_name: Name of module to check
    :return: True if module is loaded, False otherwise
    :rtype: Bool
    """
    if module_is_loaded(module_name):
        return True

    if process.system('/sbin/modprobe ' + module_name, ignore_status=True):
        return False
    return True


def parse_lsmod_for_module(l_raw, module_name, escape=True):
    """
    Use a regex to parse raw lsmod output and get module information
    :param l_raw: raw output of lsmod
    :type l_raw:  str
    :param module_name: Name of module to search for
    :type module_name: str
    :param escape: Escape regex tokens in module_name, default True
    :type escape: bool
    :return: Dictionary of module info, name, size, submodules if present
    :rtype: dict
    """
    # re.escape the module name for safety
    if escape:
        module_search = re.escape(module_name)
    else:
        module_search = module_name
    # ^module_name spaces size spaces used optional spaces optional submodules
    # use multiline regex to scan the entire output as one string without
    # having to splitlines use named matches so we can extract the dictionary
    # with groupdict
    pattern = (r"^(?P<name>%s)\s+(?P<size>\d+)\s+(?P<used>\d+)"
               r"\s*(?P<submodules>\S+)?$")
    lsmod = re.search(pattern % module_search, l_raw, re.M)
    if lsmod:
        # default to empty list if no submodules
        module_info = lsmod.groupdict([])
        # convert size to integer because it is an integer
        module_info['size'] = int(module_info['size'])
        module_info['used'] = int(module_info['used'])
        if module_info['submodules']:
            module_info['submodules'] = module_info['submodules'].split(',')
        return module_info
    else:
        # return empty dict to be consistent
        return {}


def loaded_module_info(module_name):
    """
    Get loaded module details: Size and Submodules.

    :param module_name: Name of module to search for
    :type module_name: str
    :return: Dictionary of module name, size, submodules if present, filename,
             version, number of modules using it, list of modules it is
             dependent on, list of dictionary of param name and type
    :rtype: dict
    """
    l_raw = process.system_output('/sbin/lsmod').decode('utf-8')
    modinfo_dic = parse_lsmod_for_module(l_raw, module_name)
    output = process.system_output(
        f"/sbin/modinfo {module_name}").decode('utf-8')
    if output:
        param_list = []
        for line in output.splitlines():
            items = line.split()
            if not items:
                continue
            key = items[0].rstrip(':')
            value = None
            if len(items) > 1:
                if key == 'filename' or key == 'version':
                    value = str(items[-1])
                elif key == 'depends':
                    value = items[1].split(',')
                elif key == 'parm':
                    param_dic = {'type': None}
                    param_dic['name'] = items[1].split(':')[0]
                    param_type = re.search(r"\((\w+)\)", items[-1])
                    if param_type is not None:
                        param_dic['type'] = param_type.group(1)
                    param_list.append(param_dic)
            if value:
                modinfo_dic[key] = value
        if param_list:
            modinfo_dic['params'] = param_list
    return modinfo_dic


def get_submodules(module_name):
    """
    Get all submodules of the module.

    :param module_name: Name of module to search for
    :type module_name: str
    :return: List of the submodules
    :rtype: builtin.list
    """
    module_info = loaded_module_info(module_name)
    module_list = []
    try:
        submodules = module_info["submodules"]
    except KeyError:
        LOG.info("Module %s is not loaded", module_name)
    else:
        module_list = submodules
        for module in submodules:
            module_list += get_submodules(module)
    return data_structures.ordered_list_unique(module_list)


def unload_module(module_name):
    """
    Removes a module. Handles dependencies. If even then it's not possible
    to remove one of the modules, it will throw an error.CmdError exception.

    :param module_name: Name of the module we want to remove.
    :type module_name: str
    """
    module_info = loaded_module_info(module_name)
    try:
        submodules = module_info['submodules']
    except KeyError:
        LOG.info("Module %s is already unloaded", module_name)
    else:
        for module in submodules:
            unload_module(module)
        module_info = loaded_module_info(module_name)
        try:
            module_used = module_info['used']
        except KeyError:
            LOG.info("Module %s is already unloaded", module_name)
            return
        if module_used != 0:
            raise RuntimeError(f"Module {module_name} is still in use. "
                               f"Can not unload it.")
        process.system(f"/sbin/modprobe -r {module_name}")
        LOG.info("Module %s unloaded", module_name)


def module_is_loaded(module_name):
    """
    Is module loaded

    :param module_name: Name of module to search for
    :type module_name: str
    :return: True if module is loaded
    :rtype: bool
    """
    module_name = module_name.replace('-', '_')
    return module_name in get_loaded_modules()


def get_loaded_modules():
    """
    Gets list of loaded modules.
    :return: List of loaded modules.
    """
    with open('/proc/modules', 'rb') as proc_modules:  # pylint: disable=W1514
        return [astring.to_text(_.split(b' ', 1)[0]) for _ in proc_modules]


def check_kernel_config(config_name):
    """
    Reports the configuration of $config_name of the current kernel

    :param config_name: Name of kernel config to search
    :type config_name: str
    :return: Config status in running kernel (NOT_SET, BUILTIN, MODULE)
    :rtype: :class:`ModuleConfig`
    """

    kernel_version = platform.uname()[2]

    config_file = '/boot/config-' + kernel_version
    with open(config_file, 'r') as kernel_config:  # pylint: disable=W1514
        for line in kernel_config:
            line = line.split('=')

            if len(line) != 2:
                continue

            config = line[0].strip()
            if config == config_name:
                option = line[1].strip()
                if option == "m":
                    return ModuleConfig.MODULE
                else:
                    return ModuleConfig.BUILTIN
    return ModuleConfig.NOT_SET


def get_modules_dir():
    """
    Return the modules dir for the running kernel version

    :return: path of module directory
    :rtype: String
    """
    kernel_version = platform.uname()[2]

    return f'/lib/modules/{kernel_version}/kernel'
