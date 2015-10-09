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

"""
APIs to list and load/unload linux kernel modules.
"""

import re
import logging

from . import process

LOG = logging.getLogger('avocado.test')


def load_module(module_name):
    # Checks if a module has already been loaded
    if module_is_loaded(module_name):
        return False

    process.system('/sbin/modprobe ' + module_name)
    return True


def parse_lsmod_for_module(l_raw, module_name, escape=True):
    """
    Use a regexp to parse raw lsmod output and get module information
    :param l_raw: raw output of lsmod
    :type l_raw:  str
    :param module_name: Name of module to search for
    :type module_name: str
    :param escape: Escape regexp tokens in module_name, default True
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
               "\s*(?P<submodules>\S+)?$")
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
    :return: Dictionary of module info, name, size, submodules if present
    :rtype: dict
    """
    l_raw = process.system_output('/sbin/lsmod')
    return parse_lsmod_for_module(l_raw, module_name)


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
        LOG.info("Module %s is not loaded" % module_name)
    else:
        module_list = submodules
        for module in submodules:
            module_list += get_submodules(module)
    return module_list


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
        LOG.info("Module %s is already unloaded" % module_name)
    else:
        for module in submodules:
            unload_module(module)
        module_info = loaded_module_info(module_name)
        try:
            module_used = module_info['used']
        except KeyError:
            LOG.info("Module %s is already unloaded" % module_name)
            return
        if module_used != 0:
            raise RuntimeError("Module %s is still in use. "
                               "Can not unload it." % module_name)
        process.system("/sbin/modprobe -r %s" % module_name)
        LOG.info("Module %s unloaded" % module_name)


def module_is_loaded(module_name):
    """
    Is module loaded

    :param module_name: Name of module to search for
    :type module_name: str
    :return: True is module is loaded
    :rtype: bool
    """
    module_name = module_name.replace('-', '_')
    return bool(loaded_module_info(module_name))


def get_loaded_modules():
    lsmod_output = process.system_output('/sbin/lsmod').splitlines()[1:]
    return [line.split(None, 1)[0] for line in lsmod_output]
