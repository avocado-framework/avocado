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
# Copyright: Red Hat Inc. 2013-2014
# Author: Yiqiao Pu <ypu@redhat.com>
#
# This code was inspired in the autotest project,
# client/shared/utils.py
# Authors: Yiqiao Pu <ypu@redhat.com>


import glob
import logging
import math
import os
import re

from avocado.utils import data_structures, genio, process, wait
from avocado.utils.data_structures import DataSize

LOG = logging.getLogger(__name__)


class MemError(Exception):
    """
    called when memory operations fails
    """


def get_blk_string(block):
    """
    Format the given block id to string

    :param block: memory block id or block string.
    :type string: like 198 or memory198
    :return: returns string memory198 if id 198 is given
    :rtype: string
    """
    if not block.startswith("memory"):
        return f"memory{block}"
    return block


def _check_memory_state(block):
    """
    Check the given memory block is online or offline

    :param block: memory block id.
    :type string: like 198 or memory198
    :return: 'True' if online or 'False' if offline
    :rtype: bool
    """
    def _is_online():
        path = f'/sys/devices/system/memory/{get_blk_string(block)}/state'
        if genio.read_file(path) == 'online\n':
            return True
        return False

    return wait.wait_for(_is_online, timeout=10, step=0.2) or False


def check_hotplug():
    """
    Check kernel support for memory hotplug

    :return: True if hotplug supported,  else False
    :rtype: 'bool'
    """
    if glob.glob('/sys/devices/system/memory/memory*'):
        return True
    return False


def is_hot_pluggable(block):
    """
    Check if the given memory block is hotpluggable

    :param block: memory block id.
    :type string: like 198 or memory198
    :return: True if hotpluggable, else False
    :rtype: 'bool'
    """
    path = f'/sys/devices/system/memory/{get_blk_string(block)}/removable'
    return bool(int(genio.read_file(path)))


def hotplug(block):
    """
    Online the memory for the given block id.

    :param block: memory block id or or memory198
    :type string: like 198
    """
    block = get_blk_string(block)
    with open(f'/sys/devices/system/memory/{block}/state', 'w') as state_file:  # pylint: disable=W1514
        state_file.write('online')
    if not _check_memory_state(block):
        raise MemError(
            f"unable to hot-plug {block} block, not supported ?")


def hotunplug(block):
    """
    Offline the memory for the given block id.

    :param block: memory block id.
    :type string: like 198 or memory198
    """
    block = get_blk_string(block)
    with open(f'/sys/devices/system/memory/{block}/state', 'w') as state_file:  # pylint: disable=W1514
        state_file.write('offline')
    if _check_memory_state(block):
        raise MemError(
            f"unable to hot-unplug {block} block. Device busy?")


def read_from_meminfo(key):
    """
    Retrieve key from meminfo.

    :param key: Key name, such as ``MemTotal``.
    """
    for line in genio.read_file("/proc/meminfo").splitlines():
        if key in line:
            return int(re.search(r"(\d+)\s*(?:kB)?$", line).group(1))


def memtotal():
    """
    Read ``Memtotal`` from meminfo.
    """
    return read_from_meminfo('MemTotal')


def memtotal_sys():
    """
    Reports actual memory size according to online-memory
    blocks available via "/sys"

    :return: system memory in Kb as float
    """
    sys_mempath = '/sys/devices/system/memory'
    no_memblocks = 0
    for directory in os.listdir(sys_mempath):
        if directory.startswith('memory'):
            path = os.path.join(sys_mempath, directory, 'online')
            if genio.read_file(path).strip() == '1':
                no_memblocks += 1
    path = os.path.join(sys_mempath, 'block_size_bytes')
    block_size = int(genio.read_file(path).strip(), 16)
    return (no_memblocks * block_size) / 1024.0


def freememtotal():
    """
    Read ``MemFree`` from meminfo.
    """
    return read_from_meminfo('MemFree')


def rounded_memtotal():
    """
    Get memtotal, properly rounded.

    :return: Total memory, KB.
    """
    # Get total of all physical mem, in kbytes
    usable_kbytes = memtotal()
    # usable_kbytes is system's usable DRAM in kbytes,
    #   as reported by memtotal() from device /proc/meminfo memtotal
    #   after Linux deducts 1.5% to 5.1% for system table overhead
    # Undo the unknown actual deduction by rounding up
    #   to next small multiple of a big power-of-two
    #   eg  12GB - 5.1% gets rounded back up to 12GB
    mindeduct = 0.015  # 1.5 percent
    maxdeduct = 0.055  # 5.5 percent
    # deduction range 1.5% .. 5.5% supports physical mem sizes
    #    6GB .. 12GB in steps of .5GB
    #   12GB .. 24GB in steps of 1 GB
    #   24GB .. 48GB in steps of 2 GB ...
    # Finer granularity in physical mem sizes would require
    #   tighter spread between min and max possible deductions

    # increase mem size by at least min deduction, without rounding
    min_kbytes = int(usable_kbytes / (1.0 - mindeduct))
    # increase mem size further by 2**n rounding, by 0..roundKb or more
    round_kbytes = int(usable_kbytes / (1.0 - maxdeduct)) - min_kbytes
    # find least binary roundup 2**n that covers worst-cast roundKb
    mod2n = 1 << int(math.ceil(math.log(round_kbytes, 2)))
    # have round_kbytes <= mod2n < round_kbytes*2
    # round min_kbytes up to next multiple of mod2n
    phys_kbytes = min_kbytes + mod2n - 1
    phys_kbytes -= (phys_kbytes % mod2n)  # clear low bits
    return phys_kbytes


def numa_nodes():
    """
    Get a list of NUMA nodes present on the system.

    :return: List with nodes.
    """
    node_paths = glob.glob('/sys/devices/system/node/node*')
    nodes = [int(re.sub(r'.*node(\d+)', r'\1', x)) for x in node_paths]
    return (sorted(nodes))


def numa_nodes_with_memory():
    """
    Get a list of NUMA nodes present with memory on the system.

    :return: List with nodes which has memory.
    """
    mem_path = '/sys/devices/system/node/has_normal_memory'
    if not os.path.exists(mem_path):
        mem_path = '/sys/devices/system/node/has_memory'
        if not os.path.exists(mem_path):
            raise MemError("No NUMA nodes have memory")

    node_list = str(genio.read_file(mem_path).rstrip('\n'))
    return data_structures.comma_separated_ranges_to_list(node_list)


def node_size():
    """
    Return node size.

    :return: Node size.
    """
    nodes = max(len(numa_nodes()), 1)
    return ((memtotal() * 1024) / nodes)


def get_page_size():
    """
    Get linux page size for this system.

    :return Kernel page size (Bytes).
    """
    output = process.system_output('getconf PAGESIZE')
    return int(output)


def get_supported_huge_pages_size():
    """
    Get all supported huge page sizes for this system.

    :return: list of Huge pages size (kB).
    """
    output = os.listdir('/sys/kernel/mm/hugepages/')
    # Given the items in this directory are in the format hugepages-<size>kB,
    # the <size> will always start from index 10.
    output = [int(each[10:].rstrip('kB')) for each in output]
    if os.uname()[4] in ['ppc64', 'ppc64le'] and b'PowerVM'\
            in process.system_output("pseries_platform", ignore_status=True)\
            and 'MMU\t\t: Hash' in genio.read_file('/proc/cpuinfo').rstrip('\t\r\n\0'):
        output.remove(16777216)
    return output


def get_huge_page_size():
    """
    Get size of the huge pages for this system.

    :return: Huge pages size (KB).
    """
    output = process.system_output('grep Hugepagesize /proc/meminfo')
    return int(output.split()[1])  # Assumes units always in kB. :(


def get_num_huge_pages():
    """
    Get number of huge pages for this system.

    :return: Number of huge pages.
    """
    raw_hugepages = process.system_output('/sbin/sysctl vm.nr_hugepages')
    return int(raw_hugepages.split()[2])


def set_num_huge_pages(num):
    """
    Set number of huge pages.

    :param num: Target number of huge pages.
    """
    process.system(f'/sbin/sysctl vm.nr_hugepages={int(num)}')


def drop_caches():
    """
    Writes back all dirty pages to disk and clears all the caches.
    """
    process.run("sync", verbose=False)
    # We ignore failures here as this will fail on 2.6.11 kernels.
    process.run("/bin/sh -c 'echo 3 > /proc/sys/vm/drop_caches'",
                ignore_status=True, verbose=False, sudo=True)


def read_from_vmstat(key):
    """
    Get specific item value from vmstat

    :param key: The item you want to check from vmstat
    :type key: String
    :return: The value of the item
    :rtype: int
    """
    with open("/proc/vmstat") as vmstat:  # pylint: disable=W1514
        vmstat_info = vmstat.read()
        return int(re.findall(fr"{key}\s+(\d+)", vmstat_info)[0])


def read_from_smaps(pid, key):
    """
    Get specific item value from the smaps of a process include all sections.

    :param pid: Process id
    :type pid: String
    :param key: The item you want to check from smaps
    :type key: String
    :return: The value of the item in kb
    :rtype: int
    """
    with open(f"/proc/{pid}/smaps") as smaps:  # pylint: disable=W1514
        smaps_info = smaps.read()

        memory_size = 0
        for each_number in re.findall(fr"{key}:\s+(\d+)", smaps_info):
            memory_size += int(each_number)

        return memory_size


def read_from_numa_maps(pid, key):
    """
    Get the process numa related info from numa_maps. This function
    only use to get the numbers like anon=1.

    :param pid: Process id
    :type pid: String
    :param key: The item you want to check from numa_maps
    :type key: String
    :return: A dict using the address as the keys
    :rtype: dict
    """
    with open(f"/proc/{pid}/numa_maps") as numa_maps:  # pylint: disable=W1514
        numa_map_info = numa_maps.read()

        numa_maps_dict = {}
        numa_pattern = fr"(^[\dabcdfe]+)\s+.*{key}[=:](\d+)"
        for address, number in re.findall(numa_pattern, numa_map_info, re.M):
            numa_maps_dict[address] = number

        return numa_maps_dict


def _get_buddy_info_content():
    buddy_info_content = ''
    with open("/proc/buddyinfo") as buddy_info:  # pylint: disable=W1514
        buddy_info_content = buddy_info.read()
    return buddy_info_content


def get_buddy_info(chunk_sizes, nodes="all", zones="all"):
    """
    Get the fragment status of the host.

    It uses the same method to get the page size in buddyinfo. The expression
    to evaluate it is::

        2^chunk_size * page_size

    The chunk_sizes can be string make up by all orders that you want to check
    split with blank or a mathematical expression with ``>``, ``<`` or ``=``.

    For example:
        * The input of chunk_size could be: ``0 2 4``, and the return  will be
          ``{'0': 3, '2': 286, '4': 687}``
        * If you are using expression: ``>=9`` the return will be
          ``{'9': 63, '10': 225}``

    :param chunk_size: The order number shows in buddyinfo. This is not
                       the real page size.
    :type chunk_size: string
    :param nodes: The numa node that you want to check. Default value is all
    :type nodes: string
    :param zones: The memory zone that you want to check. Default value is all
    :type zones: string
    :return: A dict using the chunk_size as the keys
    :rtype: dict
    """
    buddy_info_content = _get_buddy_info_content()

    re_buddyinfo = r"Node\s+"
    if nodes == "all":
        re_buddyinfo += r"(\d+)"
    else:
        re_buddyinfo += f"({'|'.join(nodes.split())})"

    if not re.findall(re_buddyinfo, buddy_info_content):
        LOG.warning("Can not find Nodes %s", nodes)
        return None
    re_buddyinfo += r".*?zone\s+"
    if zones == "all":
        re_buddyinfo += r"(\w+)"
    else:
        re_buddyinfo += f"({'|'.join(zones.split())})"
    if not re.findall(re_buddyinfo, buddy_info_content):
        LOG.warning("Can not find zones %s", zones)
        return None
    re_buddyinfo += r"\s+([\s\d]+)"

    buddy_list = re.findall(re_buddyinfo, buddy_info_content)

    if re.findall("[<>=]", chunk_sizes) and buddy_list:
        size_list = len(buddy_list[-1][-1].strip().split())
        chunk_sizes = [str(_) for _ in range(size_list)
                       if eval(f"{_} {chunk_sizes}")]  # pylint: disable=W0123

        chunk_sizes = ' '.join(chunk_sizes)

    buddyinfo_dict = {}
    for chunk_size in chunk_sizes.split():
        buddyinfo_dict[chunk_size] = 0
        for _, _, chunk_info in buddy_list:
            chunk_info = chunk_info.strip().split()[int(chunk_size)]
            buddyinfo_dict[chunk_size] += int(chunk_info)

    return buddyinfo_dict


def set_thp_value(feature, value):
    """
    Sets THP feature to a given value

    :param feature: Thp feature to set
    :type feature: str
    :param value: Value to be set to feature
    :type value: str
    """
    thp_path = '/sys/kernel/mm/transparent_hugepage/'
    thp_feature_to_set = os.path.join(thp_path, feature)
    genio.write_file_or_fail(thp_feature_to_set, value)


def get_thp_value(feature):
    """
    Gets the value of the thp feature arg passed

    :Param feature: Thp feature to get value
    :type feature: str
    """
    thp_path = '/sys/kernel/mm/transparent_hugepage/'
    thp_feature_to_get = os.path.join(thp_path, feature)
    value = genio.read_file(thp_feature_to_get)
    if feature in ("enabled", "defrag", "shmem_enabled"):
        return (re.search(r"\[(\w+)\]", value)).group(1)
    else:
        return value


class _MemInfoItem:
    """
    Representation of one item from /proc/meminfo
    """

    def __init__(self, name):
        self.name = name

    def __getattr__(self, attr):
        datasize = DataSize(f'{read_from_meminfo(self.name)}k')
        return getattr(datasize, attr)


class MemInfo:
    """
    Representation of /proc/meminfo
    """

    def __init__(self):
        with open('/proc/meminfo', 'r') as meminfo_file:  # pylint: disable=W1514
            for line in meminfo_file.readlines():
                name = line.strip().split()[0].strip(':')
                safe_name = name.replace('(', '_').replace(')', '_')
                setattr(self, safe_name, _MemInfoItem(name))

    def __iter__(self):
        for item in self.__dict__.items():
            yield item


meminfo = MemInfo()
