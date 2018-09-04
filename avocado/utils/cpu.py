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
import random


def _list_matches(content_list, pattern):
    """
    Checks if any item in list matches the specified pattern
    """
    for content in content_list:
        match = re.search(pattern, content)
        if match:
            return True
    return False


def _get_cpu_info():
    """
    Returns info on the 1st CPU entry from /proc/cpuinfo as a list of lines

    :returns: `list` of lines 1st CPU entry from /proc/cpuinfo file
    :rtype: `list`
    """
    cpuinfo = []
    with open('/proc/cpuinfo', 'rb') as proc_cpuinfo:
        for line in proc_cpuinfo:
            if line == b'\n':
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
    with open('/sys/devices/system/cpu/cpu%s/online' % cpu, 'rb') as cpu_online:
        if b'1' in cpu_online.read():
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
    cpu_table = [(b'^cpu.*(RS64|POWER3|Broadband Engine)', 'power'),
                 (b'^cpu.*POWER4', 'power4'),
                 (b'^cpu.*POWER5', 'power5'),
                 (b'^cpu.*POWER6', 'power6'),
                 (b'^cpu.*POWER7', 'power7'),
                 (b'^cpu.*POWER8', 'power8'),
                 (b'^cpu.*POWER9', 'power9'),
                 (b'^cpu.*PPC970', 'power970'),
                 (b'(ARM|^CPU implementer|^CPU part|^CPU variant'
                  b'|^Features|^BogoMIPS|^CPU revision)', 'arm'),
                 (b'(^cpu MHz dynamic|^cpu MHz static|^features'
                  b'|^bogomips per cpu|^max thread id)', 's390'),
                 (b'^type', 'sparc64'),
                 (b'^flags.*:.* lm .*', 'x86_64'),
                 (b'^flags', 'i386'),
                 (b'^hart\\s*: 1$', 'riscv')]
    cpuinfo = _get_cpu_info()
    for (pattern, arch) in cpu_table:
        if _list_matches(cpuinfo, pattern):
            if arch == 'arm':
                # ARM is a special situation, which matches both 32 bits
                # (v7) and 64 bits (v8).
                for line in cpuinfo:
                    if line.startswith(b"CPU architecture"):
                        version = int(line.split(b':', 1)[1])
                        if version >= 8:
                            return 'aarch64'
                        else:
                            # For historical reasons return arm
                            return 'arm'
            return arch
    return platform.machine()


def cpu_online_list():
    """
    Reports a list of indexes of the online cpus
    """
    cpus = []
    search_str = b'processor'
    index = 2
    if platform.machine() == 's390x':
        search_str = b'cpu number'
        index = 3
    with open('/proc/cpuinfo', 'rb') as proc_cpuinfo:
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
    with open("/sys/devices/system/cpu/cpu%s/online" % cpu, "wb") as fd:
        fd.write(b'1')
    if _get_cpu_status(cpu):
        return 0
    return 1


def offline(cpu):
    """
    Offline given CPU
    """
    with open("/sys/devices/system/cpu/cpu%s/online" % cpu, "wb") as fd:
        fd.write(b'0')
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
                cpu_idlestate[cpu][state_no] = int(open(state_file, 'rb').read())
            except IOError as err:
                logging.warning("Failed to read idle state on cpu %s "
                                "for state %s:\n%s", cpu, state_no, err)
    return cpu_idlestate


def _bool_to_binary(value):
    '''
    Turns a boolean value (True or False) into data suitable for writing to
    /proc/* and /sys/* files.
    '''
    if value is True:
        return b'1'
    if value is False:
        return b'0'
    raise TypeError('Value is not a boolean: %s', value)


def _legacy_disable(value):
    '''
    Support for the original acceptable disable parameter values

    TODO: this should be removed in the near future
    Reference: https://trello.com/c/aJzNUeA5/
    '''
    if value is 0:
        return b'0'
    if value is 1:
        return b'1'
    return _bool_to_binary(value)


def set_cpuidle_state(state_number="all", disable=True, setstate=None):
    """
    Set/Reset cpu idle states for all cpus

    :param state_number: cpuidle state number, default: `all` all states
    :param disable: whether to disable/enable given cpu idle state,
                    default is to disable (True)
    :param setstate: cpuidle state value, output of `get_cpuidle_state()`
    """
    cpus_list = cpu_online_list()
    if not setstate:
        states = []
        if state_number == 'all':
            states = range(0, len(glob.glob("/sys/devices/system/cpu/cpu0/cpuidle/state*")))
        else:
            states.append(state_number)
        disable = _legacy_disable(disable)
        for cpu in cpus_list:
            for state_no in states:
                state_file = "/sys/devices/system/cpu/cpu%s/cpuidle/state%s/disable" % (cpu, state_no)
                try:
                    open(state_file, "wb").write(disable)
                except IOError as err:
                    logging.warning("Failed to set idle state on cpu %s "
                                    "for state %s:\n%s", cpu, state_no, err)
    else:
        for cpu, stateval in setstate.items():
            for state_no, value in stateval.items():
                state_file = "/sys/devices/system/cpu/cpu%s/cpuidle/state%s/disable" % (cpu, state_no)
                disable = _legacy_disable(value)
                try:
                    open(state_file, "wb").write(disable)
                except IOError as err:
                    logging.warning("Failed to set idle state on cpu %s "
                                    "for state %s:\n%s", cpu, state_no, err)


def set_cpufreq_governor(governor="random"):
    """
    To change the given cpu frequency governor

    :param governor: frequency governor profile name whereas `random` is default
                     option to choose random profile among available ones.
    """
    avl_gov_file = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors"
    cur_gov_file = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
    cur_gov = get_cpufreq_governor()
    if not cur_gov:
        return False
    if not (os.access(avl_gov_file, os.R_OK) and os.access(cur_gov_file, os.W_OK)):
        logging.error("Could not locate frequency governor sysfs entries or\n"
                      " No proper permissions to read/write sysfs entries")
        return False
    cpus_list = range(total_cpus_count())
    with open(avl_gov_file, 'r') as fl:
        avl_govs = fl.read().strip().split(' ')
    if governor == "random":
        avl_govs.remove(cur_gov)
        if not avl_govs:
            logging.error("No other frequency governors to pick from...")
            return False
        governor = random.choice(avl_govs)
    if governor not in avl_govs:
        logging.warning("Trying to change unknown frequency "
                        "governor: %s", governor)
    for cpu in cpus_list:
        cur_gov_file = "/sys/devices/system/cpu/cpu%s/cpufreq/scaling_governor" % cpu
        try:
            with open(cur_gov_file, 'w') as fl:
                fl.write(governor)
        except IOError as err:
            logging.warning("Unable to write a given frequency "
                            "governor %s profile for cpu "
                            "%s\n %s", governor, cpu, err)
    return True


def get_cpufreq_governor():
    """
    Get current cpu frequency governor
    """
    cur_gov_file = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
    try:
        with open(cur_gov_file, 'r') as fl:
            return fl.read().strip()
    except IOError as err:
        logging.error("Unable to get the current governor\n %s", err)
        return ""
