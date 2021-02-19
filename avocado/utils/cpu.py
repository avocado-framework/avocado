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

import glob
import logging
import os
import platform
import random
import re
import warnings

#: Map vendor's name with expected string in /proc/cpuinfo.
VENDORS_MAP = {
    'intel': (b"GenuineIntel", ),
    'amd': (b"AMD", ),
    'ibm': (rb"POWER\d", rb"IBM/S390", ),
}


class FamilyException(Exception):
    pass


def _list_matches(content_list, pattern):
    """
    Checks if any item in list matches the specified pattern.

    :param content_list: items to match
    :type content_list: list
    :param pattern: pattern to match from content_list
    :type pattern: str
    :return: if the pattern was found or not
    :rtype: bool
    """
    for content in content_list:
        match = re.search(pattern, content)
        if match:
            return True
    return False


def _get_info():
    """
    Returns info on the 1st CPU entry from /proc/cpuinfo as a list of lines.

    :return: `list` of lines 1st CPU entry from /proc/cpuinfo file
    :rtype: list
    """
    cpuinfo = []
    with open('/proc/cpuinfo', 'rb') as proc_cpuinfo:
        for line in proc_cpuinfo:
            if line == b'\n':
                break
            cpuinfo.append(line)
    return cpuinfo


def _get_status(cpu):
    """
    Check if a CPU is online or offline.

    :param cpu: CPU number (e.g. 1, 2 or 39)
    :type cpu: int
    :return: `bool` True if online or False if not
    :rtype: bool
    """
    with open('/sys/devices/system/cpu/cpu%s/online' % cpu, 'rb') as cpu_online:
        if b'1' in cpu_online.read():
            return True
    return False


def cpu_has_flags(flags):
    """
    Check if a list of flags are available on current CPU info.

    :param flags: A `list` of cpu flags that must exists on the current CPU.
    :type flags: list of str
    :return: True if all the flags were found or False if not
    :rtype: bool
    """
    cpu_info = _get_info()

    if not isinstance(flags, list):
        flags = [flags]

    for flag in flags:
        if not any([flag.encode() in line for line in cpu_info]):
            return False
    return True


def get_version():
    """
    Get cpu version.

    :return: cpu version of given machine
             e.g.:- 'i5-5300U' for Intel and 'POWER9' for IBM machines in
             case of unknown/unsupported machines, return an empty string.
    :rtype: str
    """
    version_pattern = {'x86_64': rb'\s([\S,\d]+)\sCPU',
                       'i386': rb'\s([\S,\d]+)\sCPU',
                       'powerpc': rb'revision\s+:\s+(\S+)',
                       's390': rb'.*machine\s=\s(\d+)'
                       }
    cpu_info = _get_info()
    arch = get_arch()
    try:
        version_pattern[arch]
    except KeyError as Err:
        logging.warning("No pattern string for arch: %s\n Error: %s", arch, Err)
        return None
    for line in cpu_info:
        version_out = re.findall(version_pattern[arch], line)
        if version_out:
            return version_out[0].decode('utf-8')
    return ''


def get_vendor():
    """
    Get the current cpu vendor name.

    :return: a key of :data:`VENDORS_MAP` (e.g. 'intel') depending on the
             current CPU architecture. Return None if it was unable to
             determine the vendor name.
    :rtype: str or None
    """
    cpu_info = _get_info()
    for vendor, identifiers in VENDORS_MAP.items():
        for identifier in identifiers:
            if _list_matches(cpu_info, identifier):
                return vendor
    return None


def get_arch():
    """Work out which CPU architecture we're running on."""
    cpu_table = [(b'^cpu.*(RS64|Broadband Engine)', 'powerpc'),
                 (rb'^cpu.*POWER\d+', 'powerpc'),
                 (b'^cpu.*PPC970', 'powerpc'),
                 (b'(ARM|^CPU implementer|^CPU part|^CPU variant'
                  b'|^Features|^BogoMIPS|^CPU revision)', 'arm'),
                 (b'(^cpu MHz dynamic|^cpu MHz static|^features'
                  b'|^bogomips per cpu|^max thread id)', 's390'),
                 (b'^type', 'sparc64'),
                 (b'^flags.*:.* lm .*', 'x86_64'),
                 (b'^flags', 'i386'),
                 (b'^hart\\s*: 1$', 'riscv')]
    cpuinfo = _get_info()
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


def get_family():
    """Get family name of the cpu like Broadwell, Haswell, power8, power9."""
    family = None
    arch = get_arch()
    if arch == 'x86_64' or arch == 'i386':
        if get_vendor() == 'amd':
            raise NotImplementedError
        try:
            # refer below links for microarchitectures names
            # https://en.wikipedia.org/wiki/List_of_Intel_CPU_microarchitectures
            # https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/x86/events/intel/core.c#n4613
            with open('/sys/devices/cpu/caps/pmu_name', 'rb') as mico_arch:
                family = mico_arch.read().decode('utf-8').strip('\n').lower()
        except FileNotFoundError as err:
            msg = "Could not find micro-architecture/family, Error: %s" % err
            logging.warning(msg)
            raise FamilyException(msg)
    elif arch == 'powerpc':
        res = []
        try:
            for line in _get_info():
                res = re.findall(rb'cpu\s+:\s+(POWER\d+)', line)
                if res:
                    break
            family = res[0].decode('utf-8').lower()
        except IndexError as err:
            msg = "Unable to parse cpu family %s" % err
            logging.warning(msg)
            raise FamilyException(msg)
    elif arch == 's390':
        zfamily_map = {'2964': 'z13',
                       '3906': 'z14',
                       '8561': 'z15'
                       }
        try:
            family = zfamily_map[get_version()].lower()
        except KeyError as err:
            msg = "Could not find family for %s\nError: %s" % (get_version(), err)
            logging.warning(msg)
            raise FamilyException(msg)
    else:
        raise NotImplementedError
    return family


def online_list():
    """Reports a list of indexes of the online cpus."""
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


def total_count():
    """Return Number of Total cpus in the system including offline cpus."""
    return os.sysconf('SC_NPROCESSORS_CONF')


def online_count():
    """Return Number of Online cpus in the system."""
    return os.sysconf('SC_NPROCESSORS_ONLN')


def online(cpu):
    """Online given CPU."""
    if _get_status(cpu) is False:
        with open("/sys/devices/system/cpu/cpu%s/online" % cpu, "wb") as fd:
            fd.write(b'1')
        if _get_status(cpu):
            return 0
    return 1


def offline(cpu):
    """Offline given CPU."""
    if _get_status(cpu):
        with open("/sys/devices/system/cpu/cpu%s/online" % cpu, "wb") as fd:
            fd.write(b'0')
        if _get_status(cpu):
            return 1
    return 0


def get_idle_state():
    """
    Get current cpu idle values.

    :return: Dict of cpuidle states values for all cpus
    :rtype: dict
    """
    cpus_list = online_list()
    states = len(glob.glob("/sys/devices/system/cpu/cpu0/cpuidle/state*"))
    cpu_idlestate = {}
    for cpu in cpus_list:
        cpu_idlestate[cpu] = {}
        for state_no in range(states):
            state_file = "/sys/devices/system/cpu/cpu%s/cpuidle/state%s/disable" % (cpu, state_no)
            try:
                cpu_idlestate[cpu][state_no] = bool(int(open(state_file, 'rb').read()))
            except IOError as err:
                logging.warning("Failed to read idle state on cpu %s "
                                "for state %s:\n%s", cpu, state_no, err)
    return cpu_idlestate


def _bool_to_binary(value):
    """
    Turns a Python boolean value (True or False) into binary data.

    This function is suitable for writing to /proc/* and /sys/* files.
    """
    if value is True:
        return b'1'
    if value is False:
        return b'0'
    raise TypeError("Value is not a boolean: %s" % value)


def set_idle_state(state_number="all", disable=True, setstate=None):
    """
    Set/Reset cpu idle states for all cpus.

    :param state_number: cpuidle state number, default: `all` all states
    :type state_number: str
    :param disable: whether to disable/enable given cpu idle state,
                    default is to disable.
    :type disable: bool
    :param setstate: cpuidle state value, output of `get_idle_state()`
    :type setstate: dict
    """
    cpus_list = online_list()
    if not setstate:
        states = []
        if state_number == 'all':
            states = list(range(len(glob.glob("/sys/devices/system/cpu/cpu0/cpuidle/state*"))))
        else:
            states.append(state_number)
        disable = _bool_to_binary(disable)
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
                disable = _bool_to_binary(value)
                try:
                    open(state_file, "wb").write(disable)
                except IOError as err:
                    logging.warning("Failed to set idle state on cpu %s "
                                    "for state %s:\n%s", cpu, state_no, err)


def set_freq_governor(governor="random"):
    """
    To change the given cpu frequency governor.

    :param governor: frequency governor profile name whereas `random` is default
                     option to choose random profile among available ones.
    :type governor: str
    """
    avl_gov_file = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors"
    cur_gov_file = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
    cur_gov = get_freq_governor()
    if not cur_gov:
        return False
    if not (os.access(avl_gov_file, os.R_OK) and os.access(cur_gov_file, os.W_OK)):
        logging.error("Could not locate frequency governor sysfs entries or\n"
                      " No proper permissions to read/write sysfs entries")
        return False
    cpus_list = total_count()
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
    for cpu in range(cpus_list):
        cur_gov_file = "/sys/devices/system/cpu/cpu%s/cpufreq/scaling_governor" % cpu
        try:
            with open(cur_gov_file, 'w') as fl:
                fl.write(governor)
        except IOError as err:
            logging.warning("Unable to write a given frequency "
                            "governor %s profile for cpu "
                            "%s\n %s", governor, cpu, err)
    return True


def get_freq_governor():
    """Get current cpu frequency governor."""
    cur_gov_file = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
    try:
        with open(cur_gov_file, 'r') as fl:
            return fl.read().strip()
    except IOError as err:
        logging.error("Unable to get the current governor\n %s", err)
        return ""


def get_pid_cpus(pid):
    """
    Get all the cpus being used by the process according to pid informed.

    :param pid: process id
    :type pid: str
    :return: A list include all cpus the process is using
    :rtype: list
    """
    # processor id index is defined according proc documentation
    # the negative index is necessary because backward data
    # access has no misleading whitespaces
    processor_id_index = -14
    cpus = set()
    proc_stat_files = glob.glob('/proc/%s/task/[123456789]*/stat' % pid)

    for proc_stat_file in proc_stat_files:
        try:
            with open(proc_stat_file) as proc_stat:
                cpus.add(
                    proc_stat.read().split(' ')[processor_id_index]
                )
        except IOError:
            continue
    return list(cpus)


def _deprecated(newfunc, oldfuncname):
    """
    Print a warning to user and return the new function.

    :param newfunc: new function to be assigned
    :param oldfunctionname: Old function name string
    :rtype: `function`
    """
    def wrap(*args, **kwargs):
        fmt_str = "avocado.utils.cpu.{}() it is getting deprecat".format(oldfuncname)
        fmt_str += "ed, Use avocado.utils.cpu.{}() instead".format(newfunc.__name__)
        warnings.warn((fmt_str), DeprecationWarning, stacklevel=2)
        return newfunc(*args, **kwargs)
    return wrap


total_cpus_count = _deprecated(total_count, "total_cpus_count")
_get_cpu_info = _deprecated(_get_info, "_get_cpu_info")
_get_cpu_status = _deprecated(_get_status, "_get_cpu_status")
get_cpu_vendor_name = _deprecated(get_vendor, "get_cpu_vendor_name")
get_cpu_arch = _deprecated(get_arch, "get_cpu_arch")
cpu_online_list = _deprecated(online_list, "cpu_online_list")
online_cpus_count = _deprecated(online_count, "online_cpus_count")
get_cpuidle_state = _deprecated(get_idle_state, "get_cpuidle_state")
set_cpuidle_state = _deprecated(set_idle_state, "set_cpuidle_state")
set_cpufreq_governor = _deprecated(set_freq_governor, "set_cpufreq_governor")
get_cpufreq_governor = _deprecated(get_freq_governor, "get_cpufreq_governor")
