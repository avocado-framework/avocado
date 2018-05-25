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
# Copyright: 2018 IBM
# Author: Praveen K Pandey <praveen@linux.vnet.ibm.com>
#

"""
Module for manipulate dmesg while running test.
"""


import time
import os
from . import process, genio

_dmesg_log_file = '%s/dmesglog-%s' % (genio._log_file_dir,
                                      time.strftime("%Y-%m-%d:%H:%M:%S"))


class DmesgError(Exception):
    """
    Base Exception Class for all dmesg  utils exceptions
    """
    pass


def clear_dmesg():
    """
    This function clear dmesg of system
    and save older dmesg in a file
    """

    cmd = "dmesg -c"
    out = process.system(cmd, timeout=30, ignore_status=True,
                         verbose=False, shell=True, sudo=True)
    if out:
        raise DmesgError(
            "unable to clear dmesg as some issue while clearing")


def collect_dmesg():
    """
    This Function collect dmesg and save in a tmp file
    :return: tmp file which contain dmesg
    """

    dmesg = process.system_output("dmesg", ignore_status=True, sudo=True)
    genio.write_file(_dmesg_log_file, dmesg)
    if not os.path.isfile(_dmesg_log_file):
        raise DmesgError("issue with dmesg store in file")
    return _dmesg_log_file


def verify_pattern_dmesg(dmesg_log_file=None, pattern=None):
    """
    check pattern in dmesg

    :dmesg_log_file: Used for process and find pattern
                     If None use internal collect_dmesg
                     get tmp demsg file
    :pattern      :  List variable to search in dmesg
                     If None  assign  default pattern to "Call Trace:"
    :return error log in form of list
    """
    ERROR = []
    if not dmesg_log_file:
        dmesg_log_file = collect_dmesg()
    if not pattern:
        pattern = ["Call Trace:"]
    for fail_pattern in pattern:
        for log in genio.read_file(_dmesg_log_file).splitlines():
            if fail_pattern in log:
                ERROR.append(log)
    return ERROR


def verify_dmesg(dmesg_log_file=None, level_check=5, ignore_result=False):
    """
    find call trace in dmesg log

    :param dmesg_log_file: The file used to save host dmesg.
                           If None, will save /tmp
    :param ignore_result: True or False, whether to fail test case on issues
    :param level_check: level of severity of issues to be checked
                        1 - emerg
                        2 - emerg,alert
                        3 - emerg,alert,crit
                        4 - emerg,alert,crit,err
                        5 - emerg,alert,crit,err,warn
    """

    cmd = "dmesg -T -l %s|grep ." % ",".join(
        map(str, range(0, int(level_check))))
    out = process.run(cmd, timeout=30, ignore_status=True,
                      verbose=False, shell=True)

    if out.exit_status == 0:
        if not dmesg_log_file:
            dmesg_log_file = _dmesg_log_file
        with open(dmesg_log_file, "w+") as log_f:
            log_f.write(out.stdout)
        if not ignore_result:
            raise DmesgError(
                "test is failed due to error check dmesg file  %s"
                % dmesg_log_file)
