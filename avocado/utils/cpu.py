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
# Original author: Martin J Bligh <mbligh@google.com>
# Original author: John Admanski <jadmanski@google.com>


"""
Get information from the current's machine CPU.
"""

import re
import os


def _list_matches(lst, pattern):
    """
    True if any item in list matches the specified pattern.
    """
    compiled = re.compile(pattern)
    for element in lst:
        match = compiled.search(element)
        if match:
            return 1
    return 0


def _get_cpu_info():
    """
    Returns info on the 1st CPU entry from /proc/cpuinfo as a list of lines

    :returns: `list` of lines 1st CPU entry from /proc/cpuinfo file
    :rtype: `list`
    """
    cpuinfo = []
    for line in open('/proc/cpuinfo').readlines():
        if line == '\n':
            break
        cpuinfo.append(line)
    return cpuinfo


def cpu_has_flags(flags):
    """
    Check if a list of flags are available on current CPU info

    :param flags: A `list` of cpu flags that must exists on the current CPU.
    :type flags: `list`
    :returns: `bool` True if all the flags were found or False if not
    :rtype: `list`
    """
    cpu_info = _get_cpu_info()

    if not isinstance(flags, list):
        flags = [flags]

    for flag in flags:
        if not _list_matches(cpu_info, '.*%s.*' % flag):
            return False
    return True


def get_cpu_vendor_name():
    """
    Get the current cpu vendor name

    :returns: string 'intel' or 'amd' or 'power7' depending on the
         current CPU architecture.
    :rtype: `string`
    """
    vendors_map = {
        'intel': ("GenuineIntel", ),
        'amd': ("AMD", ),
        'power7': ("POWER7", ),
        'power8': ("POWER8", )
    }

    cpu_info = _get_cpu_info()
    for vendor, identifiers in vendors_map.items():
        for identifier in identifiers:
            if _list_matches(cpu_info, identifier):
                return vendor
    return None


def get_cpu_arch():
    """
    Work out which CPU architecture we're running on
    """
    cpu_table = [('^cpu.*(RS64|POWER3|Broadband Engine)', 'power'),
                 ('^cpu.*POWER4', 'power4'),
                 ('^cpu.*POWER5', 'power5'),
                 ('^cpu.*POWER6', 'power6'),
                 ('^cpu.*POWER7', 'power7'),
                 ('^cpu.*POWER8', 'power8'),
                 ('^cpu.*POWER9', 'power9'),
                 ('^cpu.*PPC970', 'power970'),
                 ('ARM', 'arm'),
                 ('^flags.*:.* lm .*', 'x86_64')]
    cpuinfo = _get_cpu_info()
    for (pattern, arch) in cpu_table:
        if _list_matches(cpuinfo, pattern):
            return arch
    return 'i386'


def cpu_online_list():
    """
    Reports a list of indexes of the online cpus
    """
    cpus = []
    for line in open('/proc/cpuinfo', 'r'):
        if line.startswith('processor'):
            cpus.append(int(line.split()[2]))  # grab cpu number
    return cpus


def total_cpus_count():
    """
    Return Number of Total cpus in the system including offline cpus
    """
    return os.sysconf('SC_NPROCESSORS_CONF')


def online_cpus_count():
    """
    Return Number of Online cpus in the system
    """
    return os.sysconf('SC_NPROCESSORS_ONLN')
