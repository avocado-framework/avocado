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


"""Utilities for querying and managing CPU information on the current machine.

This module provides functions to read CPU details from /proc/cpuinfo and sysfs,
including architecture, vendor, version, online/offline status, NUMA topology,
and frequency governor settings. It supports x86_64, i386, powerpc, s390,
aarch64, and other architectures.
"""
import glob
import logging
import os
import platform
import random
import re
import warnings

from avocado.utils import genio, process

#: Map vendor's name with expected string in /proc/cpuinfo.
VENDORS_MAP = {
    "intel": (b"GenuineIntel",),
    "amd": (b"AMD",),
    "ibm": (
        rb"POWER\d",
        rb"IBM/S390",
        rb"Power\d",
    ),
}

LOG = logging.getLogger(__name__)


class FamilyException(Exception):
    """Raised when CPU family cannot be determined for the current architecture."""


def _list_matches(content_list, pattern):
    """Check if any item in list matches the specified pattern.

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
    """Return info on the 1st CPU entry from /proc/cpuinfo as a list of lines.

    :return: `list` of lines 1st CPU entry from /proc/cpuinfo file
    :rtype: list
    """
    cpuinfo = []
    with open("/proc/cpuinfo", "rb") as proc_cpuinfo:  # pylint: disable=W1514
        for line in proc_cpuinfo:
            if line == b"\n" and len(cpuinfo) > 0:
                break
            cpuinfo.append(line)
    return cpuinfo


def _get_status(cpu):
    """Check if a CPU is online or offline.

    :param cpu: CPU number (e.g. 1, 2 or 39)
    :type cpu: int
    :return: `bool` True if online or False if not
    :rtype: bool
    """
    with open(
        f"/sys/devices/system/cpu/cpu{cpu}/online", "rb"
    ) as cpu_online:  # pylint: disable=W1514
        if b"1" in cpu_online.read():
            return True
    return False


def cpu_has_flags(flags):
    """Check if a list of flags are available on current CPU info.

    :param flags: A `list` of cpu flags that must exists on the current CPU.
    :type flags: list of str
    :return: True if all the flags were found or False if not
    :rtype: bool
    """
    cpu_info = _get_info()

    if not isinstance(flags, list):
        flags = [flags]

    for flag in flags:
        if not any(flag.encode() in line for line in cpu_info):
            return False
    return True


def get_version():
    """Get cpu version.

    :return: cpu version of given machine
             e.g.:- 'i5-5300U' for Intel and 'POWER9' for IBM machines in
             case of unknown/unsupported machines, return an empty string.
    :rtype: str
    """
    version_pattern = {
        "x86_64": rb"\s([\S,\d]+)\sCPU",
        "i386": rb"\s([\S,\d]+)\sCPU",
        "powerpc": rb"revision\s+:\s+(\S+)",
        "s390": rb".*machine\s=\s(\d+)",
    }
    cpu_info = _get_info()
    arch = get_arch()
    pattern = version_pattern.get(arch)
    if not pattern:
        LOG.warning("No pattern string for arch: %s", arch)
        return ""

    for line in cpu_info:
        version_out = re.findall(pattern, line)
        if version_out:
            return version_out[0].decode("utf-8")
    return ""


def get_vendor():
    """Get the current cpu vendor name.

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


def get_revision():
    """Get revision from /proc/cpuinfo.

    :return: Revision entry from /proc/cpuinfo (e.g. '0080' for IBM POWER10),
             or None if no revision line is found.
    :rtype: str or None
    """
    rev = None
    proc_cpuinfo = genio.read_file("/proc/cpuinfo")
    for line in proc_cpuinfo.splitlines():
        if "revision" in line:
            rev = line.split(" ")[3].strip()
    return rev


def get_va_bits():
    """Get virtual address bit size from /proc/cpuinfo (x86).

    :return: VA address bit size as string (e.g. '48'), or empty string
             if not found or on non-x86 architectures.
    :rtype: str
    """
    cpu_info = genio.read_file("/proc/cpuinfo")
    for line in cpu_info.splitlines():
        if "address sizes" in line:
            return line.split()[-3].strip()
    return ""


def get_arch():
    """Detect the CPU architecture of the current machine.

    :return: Architecture string (e.g. 'x86_64', 'powerpc', 's390', 'aarch64').
    :rtype: str
    """
    cpu_table = [
        (b"^cpu.*(RS64|Broadband Engine)", "powerpc"),
        (rb"^cpu.*POWER\d+", "powerpc"),
        (rb"^cpu.*Power\d+", "powerpc"),
        (b"^cpu.*PPC970", "powerpc"),
        (
            b"(ARM|^CPU implementer|^CPU part|^CPU variant"
            b"|^Features|^BogoMIPS|^CPU revision)",
            "arm",
        ),
        (
            b"(^cpu MHz dynamic|^cpu MHz static|^features"
            b"|^bogomips per cpu|^max thread id)",
            "s390",
        ),
        (b"^type", "sparc64"),
        (b"^flags.*:.* lm .*", "x86_64"),
        (b"^flags", "i386"),
        (b"^hart\\s*: 1$", "riscv"),
    ]
    cpuinfo = _get_info()
    for pattern, arch in cpu_table:
        if _list_matches(cpuinfo, pattern):
            if arch != "arm":
                return arch
            # ARM is a special situation, which matches both 32 bits
            # (v7) and 64 bits (v8).
            for line in cpuinfo:
                if line.startswith(b"CPU architecture"):
                    version = int(line.split(b":", 1)[1])
                    if version >= 8:
                        return "aarch64"
                    # For historical reasons return arm
                    return "arm"
    return platform.machine()


def get_family():
    """Get CPU family or microarchitecture name.

    :return: Family string (e.g. 'broadwell', 'haswell', 'power8', 'power9',
             'z15') depending on architecture.
    :rtype: str
    :raises FamilyException: When family cannot be determined.
    :raises NotImplementedError: On unsupported architectures.
    """
    family = None
    arch = get_arch()
    if arch in ("x86_64", "i386"):
        if get_vendor() == "amd":
            cpu_info = _get_info()
            pattern = r"cpu family\s*:"
            for line in cpu_info:
                line = line.decode("utf-8")
                if re.search(pattern, line):
                    family = int(line.split(":")[1])
                    return family
        try:
            # refer below links for microarchitectures names
            # https://en.wikipedia.org/wiki/List_of_Intel_CPU_microarchitectures
            # https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/x86/events/intel/core.c#n4613
            with open(
                "/sys/devices/cpu/caps/pmu_name", "rb"
            ) as mico_arch:  # pylint: disable=W1514
                family = mico_arch.read().decode("utf-8").strip("\n").lower()
        except FileNotFoundError as err:
            msg = f"Could not find micro-architecture/family, Error: {err}"
            LOG.warning(msg)
            raise FamilyException(msg) from err
    elif arch == "powerpc":
        res = []
        try:
            for line in _get_info():
                res = re.findall(rb"cpu\s+:\s+(POWER\d+|Power\d+)", line, re.IGNORECASE)
                if res:
                    break
            family = res[0].decode("utf-8").lower()
        except IndexError as err:
            msg = f"Unable to parse cpu family {err}"
            LOG.warning(msg)
            raise FamilyException(msg) from err
    elif arch == "s390":
        zfamily_map = {"2964": "z13", "3906": "z14", "8561": "z15", "3931": "z16"}
        try:
            family = zfamily_map[get_version()].lower()
        except KeyError as err:
            msg = f"Could not find family for {get_version()}\nError: {err}"
            LOG.warning(msg)
            raise FamilyException(msg) from err
    else:
        raise NotImplementedError
    return family


def get_model():
    """Get CPU model number (x86 only).

    :return: Model integer from /proc/cpuinfo, or None if not found.
    :rtype: int or None
    :raises NotImplementedError: On non-x86 architectures.
    """
    arch = get_arch()
    if arch == "x86_64":
        cpu_info = _get_info()
        pattern = r"model\s*:"
        for line in cpu_info:
            line = line.decode("utf-8")
            if re.search(pattern, line):
                model = int(line.split(":")[1])
                return model
        return None
    raise NotImplementedError


def get_x86_amd_zen(family=None, model=None):
    """Get the AMD Zen architecture version for x86 AMD CPUs.

    :param family: AMD CPU family (default: from get_family()).
    :type family: int or None
    :param model: AMD CPU model (default: from get_model()).
    :type model: int or None
    :return: Zen generation (1-6), or None if not an AMD Zen CPU.
    :rtype: int or None
    """

    x86_amd_zen = {
        0x17: {
            1: [(0x00, 0x2F), (0x50, 0x5F)],
            2: [(0x30, 0x4F), (0x60, 0x7F), (0x90, 0x91), (0xA0, 0xAF)],
        },
        0x19: {3: [(0x00, 0x0F), (0x20, 0x5F)], 4: [(0x10, 0x1F), (0x60, 0xAF)]},
        0x1A: {
            5: [(0x00, 0x0F), (0x20, 0x2F), (0x40, 0x4F), (0x60, 0x7F)],
            6: [(0x50, 0x5F), (0x80, 0xAF), (0xC0, 0xCF)],
        },
    }
    if family is None:
        family = get_family()
    if model is None:
        model = get_model()

    for _family, _zen_model in x86_amd_zen.items():
        if _family == family:
            for _zen, _model in _zen_model.items():
                if any(lower <= model <= upper for (lower, upper) in _model):
                    return _zen
    return None


def online_list():
    """Report a list of indexes of the online CPUs.

    :return: List of online CPU indices.
    :rtype: list of int
    """
    cpus = []
    search_str = b"processor"
    index = 2
    if platform.machine() == "s390x":
        search_str = b"cpu number"
        index = 3
    with open("/proc/cpuinfo", "rb") as proc_cpuinfo:  # pylint: disable=W1514
        for line in proc_cpuinfo:
            if line.startswith(search_str):
                cpus.append(int(line.split()[index]))  # grab cpu number
    return cpus


def total_count():
    """Return number of total CPUs in the system including offline CPUs.

    :return: Total CPU count.
    :rtype: int
    """
    return os.sysconf("SC_NPROCESSORS_CONF")


def online_count():
    """Return number of online CPUs in the system.

    :return: Online CPU count.
    :rtype: int
    """
    return os.sysconf("SC_NPROCESSORS_ONLN")


def is_hotpluggable(cpu):
    """Check whether a CPU can be hot-plugged (offlined/onlined).

    :param cpu: CPU index to check.
    :type cpu: int
    :return: True if the CPU has an 'online' sysfs interface.
    :rtype: bool
    """
    return os.path.exists(f"/sys/devices/system/cpu/cpu{cpu}/online")


def online(cpu):
    """Bring a CPU online.

    :param cpu: CPU index to bring online.
    :type cpu: int
    :return: 1 on success, 0 on failure (requires root).
    :rtype: int
    """
    if _get_status(cpu) is False:
        with open(
            f"/sys/devices/system/cpu/cpu{cpu}/online", "wb"
        ) as fd:  # pylint: disable=W1514
            fd.write(b"1")
        if _get_status(cpu) is False:
            return 0
    return 1


def offline(cpu):
    """Take a CPU offline.

    :param cpu: CPU index to take offline.
    :type cpu: int
    :return: 0 on success, 1 on failure (requires root).
    :rtype: int
    """
    if _get_status(cpu):
        with open(
            f"/sys/devices/system/cpu/cpu{cpu}/online", "wb"
        ) as fd:  # pylint: disable=W1514
            fd.write(b"0")
        if _get_status(cpu):
            return 1
    return 0


def get_idle_state():
    """Get current CPU idle state values.

    :return: Dict of cpuidle state values for all CPUs
    :rtype: dict
    """
    cpus_list = online_list()
    states = len(glob.glob("/sys/devices/system/cpu/cpu0/cpuidle/state*"))
    cpu_idlestate = {}
    for cpu in cpus_list:
        cpu_idlestate[cpu] = {}
        for state_no in range(states):
            state_file = (
                f"/sys/devices/system/cpu/cpu{cpu}/cpuidle/state{state_no}/disable"
            )
            try:
                with open(state_file, "rb") as fl:  # pylint: disable=W1514
                    cpu_idlestate[cpu][state_no] = bool(int(fl.read()))
            except IOError as err:
                LOG.warning(
                    "Failed to read idle state on cpu %s for state %s:\n%s",
                    cpu,
                    state_no,
                    err,
                )
    return cpu_idlestate


def _bool_to_binary(value):
    """Turn a Python boolean value (True or False) into binary data.

    This function is suitable for writing to /proc/* and /sys/* files.

    :param value: Boolean to convert.
    :type value: bool
    :return: b'1' for True, b'0' for False.
    :rtype: bytes
    :raises TypeError: When value is not a boolean.
    """
    if value is True:
        return b"1"
    if value is False:
        return b"0"
    raise TypeError(f"Value is not a boolean: {value}")


def set_idle_state(state_number="all", disable=True, setstate=None):
    """Set or reset CPU idle states for all CPUs.

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
        if state_number == "all":
            states = list(
                range(len(glob.glob("/sys/devices/system/cpu/cpu0/cpuidle/state*")))
            )
        else:
            states.append(state_number)
        disable = _bool_to_binary(disable)
        for cpu in cpus_list:
            for state_no in states:
                state_file = (
                    f"/sys/devices/system/cpu/cpu{cpu}/cpuidle/state{state_no}/disable"
                )
                try:
                    with open(state_file, "wb") as fl:  # pylint: disable=W1514
                        fl.write(disable)
                except IOError as err:
                    LOG.warning(
                        "Failed to set idle state on cpu %s for state %s:\n%s",
                        cpu,
                        state_no,
                        err,
                    )
    else:
        for cpu, stateval in setstate.items():
            for state_no, value in stateval.items():
                state_file = (
                    f"/sys/devices/system/cpu/cpu{cpu}/cpuidle/state{state_no}/disable"
                )
                disable = _bool_to_binary(value)
                try:
                    with open(state_file, "wb") as fl:  # pylint: disable=W1514
                        fl.write(disable)
                except IOError as err:
                    LOG.warning(
                        "Failed to set idle state on cpu %s for state %s:\n%s",
                        cpu,
                        state_no,
                        err,
                    )


def set_freq_governor(governor="random"):
    """Change the CPU frequency governor for all CPUs.

    :param governor: Governor name (e.g. 'performance', 'powersave'), or
                     'random' to pick one randomly from available governors.
    :type governor: str
    :return: True on success, False on failure.
    :rtype: bool
    """
    avl_gov_file = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors"
    cur_gov_file = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
    cur_gov = get_freq_governor()
    if not cur_gov:
        return False
    if not (os.access(avl_gov_file, os.R_OK) and os.access(cur_gov_file, os.W_OK)):
        LOG.error(
            "Could not locate frequency governor sysfs entries or\n"
            " No proper permissions to read/write sysfs entries"
        )
        return False
    cpus_list = total_count()
    with open(avl_gov_file, "r") as fl:  # pylint: disable=W1514
        avl_govs = fl.read().strip().split(" ")
    if governor == "random":
        avl_govs.remove(cur_gov)
        if not avl_govs:
            LOG.error("No other frequency governors to pick from...")
            return False
        governor = random.choice(avl_govs)
    if governor not in avl_govs:
        LOG.warning("Trying to change unknown frequency governor: %s", governor)
    for cpu in range(cpus_list):
        cur_gov_file = f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/scaling_governor"
        try:
            with open(cur_gov_file, "w") as fl:  # pylint: disable=W1514
                fl.write(governor)
        except IOError as err:
            LOG.warning(
                "Unable to write a given frequency "
                "governor %s profile for cpu "
                "%s\n %s",
                governor,
                cpu,
                err,
            )
    return True


def get_freq_governor():
    """Get the current CPU frequency governor.

    :return: Governor name (e.g. 'performance'), or empty string on error.
    :rtype: str
    """
    cur_gov_file = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
    try:
        with open(cur_gov_file, "r") as fl:  # pylint: disable=W1514
            return fl.read().strip()
    except IOError as err:
        LOG.error("Unable to get the current governor\n %s", err)
        return ""


def get_pid_cpus(pid):
    """Get CPU indices used by a process (from ``/proc/<pid>/task/*/stat``).

    :param pid: Process ID.
    :type pid: int or str
    :return: List of CPU index strings the process threads are running on.
    :rtype: list of str
    """
    # processor id index is defined according proc documentation
    # the negative index is necessary because backward data
    # access has no misleading whitespaces
    processor_id_index = -14
    cpus = set()
    proc_stat_files = glob.glob(f"/proc/{pid}/task/[123456789]*/stat")

    for proc_stat_file in proc_stat_files:
        try:
            with open(proc_stat_file) as proc_stat:  # pylint: disable=W1514
                cpus.add(proc_stat.read().split(" ")[processor_id_index])
        except IOError:
            continue
    return list(cpus)


def get_numa_node_has_cpus():
    """Get NUMA node numbers that have CPUs assigned.

    :return: List of NUMA node identifiers that have CPUs.
    :rtype: list of str
    """
    cpu_path = "/sys/devices/system/node/has_cpu"
    delim = ",", "-"
    regex_pat = "|".join(map(re.escape, delim))
    read_cpu_path = genio.read_file(cpu_path).rstrip("\n")
    nodes_with_cpus = re.split(regex_pat, read_cpu_path)
    return nodes_with_cpus


def numa_nodes_with_assigned_cpus():
    """Get NUMA nodes with their associated CPU indices.

    :return: Dict mapping NUMA node ID to sorted list of CPU indices.
    :rtype: dict
    """
    numa_nodes_with_cpus = {}
    for path in glob.glob("/sys/devices/system/node/node[0-9]*"):
        node = int(re.search(r".node(\d+)$", path).group(1))
        node_dir = os.path.join(path + "/")
        pinned_cpus = []
        for cpu_numbers in glob.glob(node_dir + "cpu[0-9]*"):
            cpu = int(re.search(r".cpu(\d+)$", cpu_numbers).group(1))
            if pinned_cpus is not None:
                pinned_cpus.append(cpu)
                numa_nodes_with_cpus[node] = sorted(pinned_cpus)
    return numa_nodes_with_cpus


def _deprecated(newfunc, oldfuncname):
    """Print a deprecation warning and return the new function.

    :param newfunc: New function to be assigned.
    :param oldfuncname: Old function name string.
    :return: Wrapper that warns and calls newfunc.
    :rtype: function
    """

    def wrap(*args, **kwargs):
        """Wrapper that emits deprecation warning and delegates to newfunc.

        :param args: Positional arguments passed through to newfunc.
        :param kwargs: Keyword arguments passed through to newfunc.
        :return: Result of newfunc(`*args`, `**kwargs`).
        :rtype: any
        """
        fmt_str = f"avocado.utils.cpu.{oldfuncname}() is deprecated, please use avocado.utils.cpu.{newfunc.__name__}() instead"
        warnings.warn((fmt_str), DeprecationWarning, stacklevel=2)
        return newfunc(*args, **kwargs)

    return wrap


def lscpu():
    """Get CPU topology by executing the 'lscpu' command.

    :return: Dict with keys such as 'cores_per_chip', 'physical_sockets',
             'physical_chips', 'threads_per_core', 'sockets', 'chips',
             'physical_cores' (depending on lscpu output).
    :rtype: dict
    """
    output = process.run("LANG=en_US.UTF-8;lscpu", shell=True)
    res = {}
    for line in output.stdout.decode("utf-8").split("\n"):
        if "Physical cores/chip:" in line:
            res["cores_per_chip"] = int(line.split(":")[1].strip())
        if "Core(s) per socket:" in line:
            res["virtual_cores"] = int(line.split(":")[1].strip())
        if "Physical sockets:" in line:
            res["physical_sockets"] = int(line.split(":")[1].strip())
        if "Physical chips:" in line:
            res["physical_chips"] = int(line.split(":")[1].strip())
        if "Thread(s) per core:" in line:
            res["threads_per_core"] = int(line.split(":")[1].strip())
        if "Socket(s):" in line:
            res["sockets"] = int(line.split(":")[1].strip())
    if "physical_sockets" in res and "physical_chips" in res:
        res["chips"] = res["physical_sockets"] * res["physical_chips"]
    if (
        "physical_sockets" in res
        and "physical_chips" in res
        and "cores_per_chip" in res
    ):
        res["physical_cores"] = (
            res["physical_sockets"] * res["physical_chips"] * res["cores_per_chip"]
        )
    return res


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

# pylint: disable=wrong-import-position
from avocado.utils.deprecation import log_deprecation

log_deprecation.warning("cpu")
