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


import re
import glob
import math
import logging

from . import process


# Returns total memory in kb


def read_from_meminfo(key):
    """
    Retrieve key from meminfo.

    :param key: Key name, such as ``MemTotal``.
    """
    cmd_result = process.run('grep %s /proc/meminfo' % key, verbose=False)
    meminfo = cmd_result.stdout
    return int(re.search(r'\d+', meminfo).group(0))


def memtotal():
    """
    Read ``Memtotal`` from meminfo.
    """
    return read_from_meminfo('MemTotal')


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


def node_size():
    """
    Return node size.

    :return: Node size.
    """
    nodes = max(len(numa_nodes()), 1)
    return ((memtotal() * 1024) / nodes)


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
    process.system('/sbin/sysctl vm.nr_hugepages=%d' % num)


def drop_caches():
    """
    Writes back all dirty pages to disk and clears all the caches.
    """
    process.run("sync", verbose=False)
    # We ignore failures here as this will fail on 2.6.11 kernels.
    process.run("echo 3 > /proc/sys/vm/drop_caches", ignore_status=True,
                verbose=False)


def read_from_vmstat(key):
    """
    Get specific item value from vmstat

    :param key: The item you want to check from vmstat
    :type key: String
    :return: The value of the item
    :rtype: int
    """
    vmstat = open("/proc/vmstat")
    vmstat_info = vmstat.read()
    vmstat.close()
    return int(re.findall("%s\s+(\d+)" % key, vmstat_info)[0])


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
    smaps = open("/proc/%s/smaps" % pid)
    smaps_info = smaps.read()
    smaps.close()

    memory_size = 0
    for each_number in re.findall("%s:\s+(\d+)" % key, smaps_info):
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
    numa_maps = open("/proc/%s/numa_maps" % pid)
    numa_map_info = numa_maps.read()
    numa_maps.close()

    numa_maps_dict = {}
    numa_pattern = r"(^[\dabcdfe]+)\s+.*%s[=:](\d+)" % key
    for address, number in re.findall(numa_pattern, numa_map_info, re.M):
        numa_maps_dict[address] = number

    return numa_maps_dict


def get_buddy_info(chunk_sizes, nodes="all", zones="all"):
    """
    Get the fragement status of the host.

    It uses the same method to get the page size in buddyinfo. The expression
    to evaluate it is::

        2^chunk_size * page_size

    The chunk_sizes can be string make up by all orders that you want to check
    splited with blank or a mathematical expression with ``>``, ``<`` or ``=``.

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
    buddy_info = open("/proc/buddyinfo")
    buddy_info_content = buddy_info.read()
    buddy_info.close()

    re_buddyinfo = "Node\s+"
    if nodes == "all":
        re_buddyinfo += "(\d+)"
    else:
        re_buddyinfo += "(%s)" % "|".join(nodes.split())

    if not re.findall(re_buddyinfo, buddy_info_content):
        logging.warn("Can not find Nodes %s" % nodes)
        return None
    re_buddyinfo += ".*?zone\s+"
    if zones == "all":
        re_buddyinfo += "(\w+)"
    else:
        re_buddyinfo += "(%s)" % "|".join(zones.split())
    if not re.findall(re_buddyinfo, buddy_info_content):
        logging.warn("Can not find zones %s" % zones)
        return None
    re_buddyinfo += "\s+([\s\d]+)"

    buddy_list = re.findall(re_buddyinfo, buddy_info_content)

    if re.findall("[<>=]", chunk_sizes) and buddy_list:
        size_list = range(len(buddy_list[-1][-1].strip().split()))
        chunk_sizes = [str(_) for _ in size_list if eval("%s %s" % (_,
                                                                    chunk_sizes))]

        chunk_sizes = ' '.join(chunk_sizes)

    buddyinfo_dict = {}
    for chunk_size in chunk_sizes.split():
        buddyinfo_dict[chunk_size] = 0
        for _, _, chunk_info in buddy_list:
            chunk_info = chunk_info.strip().split()[int(chunk_size)]
            buddyinfo_dict[chunk_size] += int(chunk_info)

    return buddyinfo_dict
