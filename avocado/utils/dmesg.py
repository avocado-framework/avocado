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
# Copyright: 2020 IBM
# Author: Praveen K Pandey <praveen@linux.vnet.ibm.com>
#

"""
Module for manipulate dmesg while running test.
"""


import time
import os
import tempfile
import logging

from . import process, genio

LOGGER = logging.getLogger('avocado.test')


class DmesgError(Exception):
    """Base Exception Class for all dmesg  utils exceptions"""
    pass


def clear_dmesg():
    """This function clear dmesg of system and save older dmesg in a file

    dmesg operation is privilege user task . This Function need sudo
    permissions enabled on the target host
    """
    cmd = "dmesg -c"
    status = process.system(cmd, timeout=30, ignore_status=True,
                            verbose=False, shell=True, sudo=True)
    if status:
        raise DmesgError(
            "Unable to clear dmesg as some issue while clearing")


def collect_dmesg(output_file=None):
    """This Function collect dmesg and save in file

    dmesg operation is privilege user task . This Function need
    sudo permissions enabled on the target host

    :parm output_file : File use for save dmesg output if not provided it use
                        tmp file which located in system  /tmp path
    :return: file which contain dmesg
    """
    if output_file is None:
        fd, output_file = tempfile.mkstemp(
            suffix=".-%s" % time.strftime("%Y-%m-%d:%H:%M:%S"), dir=tempfile.gettempdir())
    dmesg = process.system_output(
        "dmesg", ignore_status=True, sudo=True).decode()
    genio.write_file(output_file, dmesg)
    if not os.path.isfile(output_file):
        raise DmesgError("{} is not a valid file.".format(output_file))
    return output_file


def verify_patterns_dmesg(patterns):
    """Check patterns in dmesg

    :param patterns  :  List variable to search in dmesg

    :return error log in form of list
    """
    error = []
    dmesg_log_file = collect_dmesg(None)
    for fail_pattern in patterns:
        for log in genio.read_file(dmesg_log_file).splitlines():
            if fail_pattern in log:
                error.append(log)
    return error


def verify_dmesg_by_level(dmesg_log_file=None, level_check=5):
    """Verify dmesg having severity level of OS issue(s)

    :param dmesg_log_file: The file used to save dmesg
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
        err = "Found failures in dmesg"
        dmsg_log = "dmesg log:\n%s" % out.stdout_text
        if dmesg_log_file:
            with open(dmesg_log_file, "w+") as log_f:
                log_f.write(dmsg_log)
            err += " Please check  dmesg log %s." % (dmesg_log_file)
        else:
            err += " Please check  dmesg log in debug log."
            LOGGER.debug(dmsg_log)
        raise DmesgError("Test is failed {}".format(err))
