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
import platform
import glob
import logging


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
    with open('/proc/cpuinfo') as proc_cpuinfo:
        for line in proc_cpuinfo:
            if line == '\n':
                break
            cpuinfo.append(line)
    return cpuinfo


def _get_cpu_status(cpu):
    """
    Check if a CPU is online or offline

    :pram cpu: CPU number 1 or 2 or 39
    :type cpu: integer
    :returns: `bool` True if online or False if not
    :rtype: 'bool'
    """
    with open('/sys/devices/system/cpu/cpu%s/online' % cpu) as online:
        if '1' in online.read():
            return True
    return False


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
                 ('(ARM|^CPU implementer|^CPU part|^CPU variant'
                  '|^Features|^BogoMIPS|^CPU revision)', 'arm'),
                 ('(^cpu MHz dynamic|^cpu MHz static|^features'
                  '|^bogomips per cpu|^max thread id)', 's390'),
                 ('^type', 'sparc64'),
                 ('^flags.*:.* lm .*', 'x86_64'),
                 ('^flags', 'i386'),
                 ('^hart\\s*: 1$', 'riscv')]
    cpuinfo = _get_cpu_info()
    for (pattern, arch) in cpu_table:
        if _list_matches(cpuinfo, pattern):
            # ARM is a special situation, which matches both 32 bits
            # (v7) and 64 bits (v8).
            if arch == 'arm':
                arm_v8_arch_name = 'aarch64'
                if arm_v8_arch_name == platform.machine():
                    return arm_v8_arch_name
            return arch
    return platform.machine()


def cpu_online_list():
    """
    Reports a list of indexes of the online cpus
    """
    cpus = []
    search_str = 'processor'
    index = 2
    if platform.machine() == 's390x':
        search_str = 'cpu number'
        index = 3
    with open('/proc/cpuinfo', 'r') as proc_cpuinfo:
        for line in proc_cpuinfo:
            if line.startswith(search_str):
                cpus.append(int(line.split()[index]))  # grab cpu number
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


def online(cpu):
    """
    Online given CPU
    """
    with open("/sys/devices/system/cpu/cpu%s/online" % cpu, "w") as fd:
        fd.write('1')
    if _get_cpu_status(cpu):
        return 0
    return 1


def offline(cpu):
    """
    Offline given CPU
    """
    with open("/sys/devices/system/cpu/cpu%s/online" % cpu, "w") as fd:
        fd.write('0')
    if _get_cpu_status(cpu):
        return 1
    return 0


def get_cpuidle_state():
    """
    Get current cpu idle values

    :return: Dict of cpuidle states values for all cpus
    :rtype: Dict of dicts
    """
    cpus_list = cpu_online_list()
    states = range(len(glob.glob("/sys/devices/system/cpu/cpu0/cpuidle/state*")))
    cpu_idlestate = {}
    for cpu in cpus_list:
        cpu_idlestate[cpu] = {}
        for state_no in states:
            state_file = "/sys/devices/system/cpu/cpu%s/cpuidle/state%s/disable" % (cpu, state_no)
            try:
                cpu_idlestate[cpu][state_no] = int(open(state_file).read())
            except IOError as err:
                logging.warning("Failed to read idle state on cpu %s "
                                "for state %s:\n%s", cpu, state_no, err)
    return cpu_idlestate


def set_cpuidle_state(state_number="all", disable=1, setstate=None):
    """
    Set/Reset cpu idle states for all cpus

    :param state_number: cpuidle state number, default: `all` all states
    :param disable: whether to disable/enable given cpu idle state, default: 1
    :param setstate: cpuidle state value, output of `get_cpuidle_state()`
    """
    cpus_list = cpu_online_list()
    if not setstate:
        states = []
        if state_number == 'all':
            states = range(0, len(glob.glob("/sys/devices/system/cpu/cpu0/cpuidle/state*")))
        else:
            states.append(state_number)
        for cpu in cpus_list:
            for state_no in states:
                state_file = "/sys/devices/system/cpu/cpu%s/cpuidle/state%s/disable" % (cpu, state_no)
                try:
                    open(state_file, "w").write(str(disable))
                except IOError as err:
                    logging.warning("Failed to set idle state on cpu %s "
                                    "for state %s:\n%s", cpu, state_no, err)
    else:
        for cpu, stateval in setstate.items():
            for state_no, value in stateval.items():
                state_file = "/sys/devices/system/cpu/cpu%s/cpuidle/state%s/disable" % (cpu, state_no)
                try:
                    open(state_file, "w").write(str(value))
                except IOError as err:
                    logging.warning("Failed to set idle state on cpu %s "
                                    "for state %s:\n%s", cpu, state_no, err)
