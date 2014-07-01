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


import os
import re
import glob
import math
import logging

from avocado.utils import process
from avocado.utils import path

log = logging.getLogger("avocado.test")


def cpu_str_to_list(origin_str):
    """
    Convert the cpu string to a list. The string may include comma and
    hyphen.

    :param origin_str: the cpu info string read from system
    :type origin_str: string
    :return: A list of the cpu ids
    :rtype: list
    """
    if isinstance(origin_str, str):
        cpu_list = []
        for cpu in origin_str.strip().split(","):
            if "-" in cpu:
                start, end = cpu.split("-")
                for cpu_id in range(int(start), int(end) + 1):
                    cpu_list.append(cpu_id)
            else:
                try:
                    cpu_id = int(cpu)
                    cpu_list.append(cpu_id)
                except ValueError:
                    logging.error("Illegimate string in cpu "
                                  "informations: %s" % cpu)
                    cpu_list = []
                    break
        cpu_list.sort()
        return cpu_list


class NumaInfo(object):

    """
    Numa topology for host. Also provide the function for check the memory status
    of the node.
    """

    def __init__(self, all_nodes_path=None, online_nodes_path=None):
        """
        :param all_nodes_path: Alternative path to
                /sys/devices/system/node/possible. Useful for unittesting.
        :param all_nodes_path: Alternative path to
                /sys/devices/system/node/online. Useful for unittesting.
        """
        self.numa_sys_path = "/sys/devices/system/node"
        self.all_nodes = self.get_all_nodes(all_nodes_path)
        self.online_nodes = self.get_online_nodes(online_nodes_path)
        self.nodes = {}
        self.distances = {}
        for node_id in self.online_nodes:
            self.nodes[node_id] = NumaNode(node_id + 1)
            self.distances[node_id] = self.get_node_distance(node_id)

    def get_all_nodes(self, all_nodes_path=None):
        """
        Get all node ids in host.

        :return: All node ids in host
        :rtype: list
        """
        if all_nodes_path is None:
            all_nodes = path.get_path(self.numa_sys_path, "possible")
        else:
            all_nodes = all_nodes_path
        all_nodes_file = open(all_nodes, "r")
        nodes_info = all_nodes_file.read()
        all_nodes_file.close()

        return cpu_str_to_list(nodes_info)

    def get_online_nodes(self, online_nodes_path=None):
        """
        Get node ids online in host

        :return: The ids of node which is online
        :rtype: list
        """
        if online_nodes_path is None:
            online_nodes = path.get_path(self.numa_sys_path, "online")
        else:
            online_nodes = online_nodes_path
        online_nodes_file = open(online_nodes, "r")
        nodes_info = online_nodes_file.read()
        online_nodes_file.close()

        return cpu_str_to_list(nodes_info)

    def get_node_distance(self, node_id):
        """
        Get the distance from the give node to other nodes include itself.

        :param node_id: Node that you want to check
        :type node_id: string
        :return: A list in of distance for the node in positive-sequence
        :rtype: list
        """
        cmd = process.run("numactl --hardware")
        try:
            node_distances = cmd.stdout.split("node distances:")[-1].strip()
            node_distance = re.findall("%s:" % node_id, node_distances)[0]
            node_distance = node_distance.split(":")[-1]
        except Exception:
            logging.warn("Get unexpect information from numctl")
            numa_sys_path = self.numa_sys_path
            distance_path = path.get_path(numa_sys_path,
                                          "node%s/distance" % node_id)
            if not os.path.isfile(distance_path):
                logging.error("Can not get distance information for"
                              " node %s" % node_id)
                return []
            node_distance_file = open(distance_path, 'r')
            node_distance = node_distance_file.read()
            node_distance_file.close()

        return node_distance.strip().split()

    def read_from_node_meminfo(self, node_id, key):
        """
        Get specific value of a given node from memoinfo file

        :param node_id: The node you want to check
        :type node_id: string
        :param key: The value you want to check such as MemTotal etc.
        :type key: string
        :return: The value in KB
        :rtype: string
        """
        memory_path = os.path.join(self.numa_sys_path,
                                   "node%s/meminfo" % node_id)
        memory_file = open(memory_path, "r")
        memory_info = memory_file.read()
        memory_file.close()

        return re.findall("%s:\s+(\d+)" % key, memory_info)[0]


class NumaNode(object):

    """
    Numa node to control processes and shared memory.
    """

    def __init__(self, i=-1, all_nodes_path=None, online_nodes_path=None):
        """
        :param all_nodes_path: Alternative path to
                /sys/devices/system/node/possible. Useful for unittesting.
        :param all_nodes_path: Alternative path to
                /sys/devices/system/node/online. Useful for unittesting.
        """
        self.extra_cpus = []
        if i < 0:
            host_numa_info = NumaInfo(all_nodes_path, online_nodes_path)
            available_nodes = host_numa_info.nodes.keys()
            self.cpus = self.get_node_cpus(available_nodes[-1]).split()
            if len(available_nodes) > 1:
                self.extra_cpus = self.get_node_cpus(
                    available_nodes[-2]).split()
            self.node_id = available_nodes[-1]
        else:
            self.cpus = self.get_node_cpus(i - 1).split()
            self.extra_cpus = self.get_node_cpus(i).split()
            self.node_id = i - 1
        self.dict = {}
        for i in self.cpus:
            self.dict[i] = []
        for i in self.extra_cpus:
            self.dict[i] = []

    def get_node_cpus(self, i):
        """
        Get cpus of a specific node

        :param i: Index of the CPU inside the node.
        """
        cmd = process.run("numactl --hardware")
        cpus = re.findall("node %s cpus: (.*)" % i, cmd.stdout)
        if cpus:
            cpus = cpus[0]
        else:
            break_flag = False
            cpulist_path = "/sys/devices/system/node/node%s/cpulist" % i
            try:
                cpulist_file = open(cpulist_path, 'r')
                cpus = cpulist_file.read()
                cpulist_file.close()
            except IOError:
                logging.warn("Can not find the cpu list information from both"
                             "numactl and sysfs. Please check your system.")
                break_flag = True
            if not break_flag:
                # Try to expand the numbers with '-' to a string of numbers
                # separated by blank. There number of '-' in the list depends
                # on the physical architecture of the hardware.
                try:
                    convert_list = re.findall("\d+-\d+", cpus)
                    for cstr in convert_list:
                        _ = " "
                        start = min(int(cstr.split("-")[0]),
                                    int(cstr.split("-")[1]))
                        end = max(int(cstr.split("-")[0]),
                                  int(cstr.split("-")[1]))
                        for n in range(start, end + 1, 1):
                            _ += "%s " % str(n)
                        cpus = re.sub(cstr, _, cpus)
                except (IndexError, ValueError):
                    logging.warn("The format of cpu list is not the same as"
                                 " expected.")
                    break_flag = False
            if break_flag:
                cpus = ""

        return cpus

    def free_cpu(self, i, thread=None):
        """
        Release pin of one node.

        :param i: Index of the node.
        :param thread: Thread ID, remove all threads if thread ID isn't set
        """
        if not thread:
            self.dict[i] = []
        else:
            self.dict[i].remove(thread)

    def _flush_pin(self):
        """
        Flush pin dict, remove the record of exited process.
        """
        cmd = process.run("ps -eLf | awk '{print $4}'")
        all_pids = cmd.stdout
        for i in self.cpus:
            for j in self.dict[i]:
                if str(j) not in all_pids:
                    self.free_cpu(i, j)

    def pin_cpu(self, process, cpu=None, extra=False):
        """
        Pin one process to a single cpu.

        :param process: Process ID.
        :param cpu: CPU ID, pin thread to free CPU if cpu ID isn't set
        """
        self._flush_pin()
        if cpu:
            log.info("Pinning process %s to the CPU(%s)" % (process, cpu))
        else:
            log.info("Pinning process %s to the available CPU" % (process))

        cpus = self.cpus
        if extra:
            cpus = self.extra_cpus

        for i in cpus:
            if (cpu is not None and cpu == i) or (cpu is None and not self.dict[i]):
                self.dict[i].append(process)
                cmd = "taskset -p %s %s" % (hex(2 ** int(i)), process)
                logging.debug("NumaNode (%s): " % i + cmd)
                process.run(cmd)
                return i

    def show(self):
        """
        Display the record dict in a convenient way.
        """
        logging.info("Numa Node record dict:")
        for i in self.cpus:
            logging.info("    %s: %s" % (i, self.dict[i]))


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
    phys_kbytes = phys_kbytes - (phys_kbytes % mod2n)  # clear low bits
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


def get_node_cpus(i=0):
    """
    Get cpu ids of one node

    :return: the cpu lists
    :rtype: list
    """
    cmd = process.run("numactl --hardware")
    return re.findall("node %s cpus: (.*)" % i, cmd.stdout)[0].split()


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
