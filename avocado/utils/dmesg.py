# This program is free software; you can redistribute it and/or modify.
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

"""Module for manipulate dmesg while running test."""


import logging
import os
import tempfile
import time
from functools import wraps

from avocado.utils import genio, process

LOGGER = logging.getLogger(__name__)


class TestFail(AssertionError, Exception):
    """
    Indicates that the test failed.

    This is here, just because of an impossible circular import.
    """
    status = "FAIL"


class DmesgError(Exception):
    """Base Exception Class for all dmesg  utils exceptions."""


def fail_on_dmesg(level=5):
    """Dmesg fail method decorator

    Returns a class decorator used to signal the test when DmesgError
    exception is raised.

    :param level: Dmesg Level based on which the test failure should be raised
    :type level: int
    :return: Class decorator
    :rtype: class
    """
    def dmesg_fail(cls):
        def raise_dmesg_fail(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    data = func(*args, **kwargs)
                    collect_errors_by_level(level_check=level)
                    return data
                except DmesgError as details:
                    raise TestFail(repr(details)) from details
            return wrapper

        for key, value in list(vars(cls).items()):
            if callable(value) and value.__name__.startswith('test'):
                setattr(cls, key, raise_dmesg_fail(value))
        return cls
    return dmesg_fail


def clear_dmesg():
    """function clear dmesg.

    The dmesg operation is a privileged user task.
    This function needs sudo permissions enabled on the target host
    """
    cmd = "dmesg -c"
    status = process.system(cmd, timeout=30, ignore_status=True,
                            verbose=False, shell=True, sudo=True)
    if status:
        raise DmesgError(
            "Unable to clear dmesg as some issue while clearing")


def collect_dmesg(output_file=None):
    """Function collect dmesg and save in file.

    The dmesg operation is a privileged user task.
    This function needs sudo permissions enabled on the target host

    :param output_file: File use for save dmesg output if not provided it use
                        tmp file which located in system  /tmp path
    :type output_file: str
    :returns: file which contain dmesg
    :rtype: str
    """
    if output_file is None:
        _, output_file = tempfile.mkstemp(suffix=".-%s" % time.strftime("%Y-%m-%d:%H:%M:%S"),
                                          dir=tempfile.gettempdir())
    dmesg = process.system_output(
        "dmesg", ignore_status=True, sudo=True).decode()
    genio.write_file(output_file, dmesg)
    if not os.path.isfile(output_file):
        raise DmesgError("{} is not a valid file.".format(output_file))
    return output_file


def collect_errors_dmesg(patterns):
    """Check patterns in dmesg.

    :param patterns : list variable to search in dmesg
    :returns: error log in form of list
    :rtype: list of str
    """
    error = []
    dmesg_log_file = collect_dmesg(None)
    for fail_pattern in patterns:
        for log in genio.read_file(dmesg_log_file).splitlines():
            if fail_pattern in log:
                error.append(log)
    return error


def collect_errors_by_level(output_file=None, level_check=5, skip_errors=None):
    """Verify dmesg having severity level of OS issue(s).

    :param output_file: The file used to save dmesg
    :type output_file: str
    :param level_check: level of severity of issues to be checked
                        1 - emerg
                        2 - emerg,alert
                        3 - emerg,alert,crit
                        4 - emerg,alert,crit,err
                        5 - emerg,alert,crit,err,warn
    :type level_check: int
    :skip_errors: list of dmesg error messages which want skip
    :type skip_errors: list
    """
    if not isinstance(level_check, int):
        raise DmesgError("level_check param should be integer")
    dmsg_log = ""
    cmd = "dmesg -T -l %s|grep ." % ",".join(
        map(str, range(0, int(level_check))))  # pylint: disable=W1638
    out = process.run(cmd, timeout=30, ignore_status=True,
                      verbose=False, shell=True)
    if out.exit_status == 0:
        err = "Found failures in dmesg"
        if skip_errors:
            dmsg_log = skip_dmesg_messages(out.stdout_text, skip_errors)
        else:
            dmsg_log = "dmesg log:\n%s" % out.stdout_text
    if dmsg_log:
        if output_file:
            with open(output_file, "w+") as log_f:
                log_f.write(dmsg_log)
            err += " Please check  dmesg log %s." % (output_file)
        else:
            err += " Please check  dmesg log in debug log."
            LOGGER.debug(dmsg_log)
        raise DmesgError("Test is failed {}".format(err))


def skip_dmesg_messages(dmesg_stdout, skip_messages):
    """Remove some messages from a dmesg buffer.

      This method will remove some lines in a dmesg buffer if some strings are
      present. Returning the same buffer, but with less lines (in case of match).

      :dmesg_stdout: dmesg messages from which filter should be applied. This
                     must be a decoded output buffer with new lines.
      :type dmesg_stdout: str
      :skip_messages: list of strings to be removed
      :type skip_messages: list
    """
    def filter_strings(line):
        return not any([string in line for string in skip_messages])

    return '\n'.join(filter(None,
                            filter(filter_strings,
                                   dmesg_stdout.splitlines())))
