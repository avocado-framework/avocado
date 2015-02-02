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
# Copyright: Red Hat Inc. 2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>
# Author: Lukas Doktor <ldoktor@redhat.com>
"""
This file contains tools for (not only) Avocado developers.
"""
import logging
import time


# Use this for debug logging
LOGGER = logging.getLogger("avocado.debug")

# measure_duration global storage
__MEASURE_DURATION = {}


def measure_duration(func):
    """
    Use this as decorator to measure duration of the function execution.
    The output is "Function $name: ($current_duration, $accumulated_duration)"
    """
    def wrapper(*args, **kwargs):
        """ Wrapper function """
        start = time.time()
        try:
            return func(*args, **kwargs)
        finally:
            duration = time.time() - start
            __MEASURE_DURATION[func] = (__MEASURE_DURATION.get(func, 0)
                                        + duration)
            LOGGER.debug("PERF: %s: (%ss, %ss)", func, duration,
                         __MEASURE_DURATION[func])
    return wrapper


class Mocker(object):

    """ Class for mocking functions with propper cleanup """

    def __init__(self, log=None):
        """
        :param log: List in which to log function calls
        """
        if log:
            self.log = log
        else:
            self.log = []
        self.originals = []

    def log_function(self, name, ret=None):
        """
        Generate function which logs itself and returns some value.
        :param name: Under which name to log this function's calls
        :param ret: What this function returns
        """
        def new_fction(*args, **kwargs):
            """ Logs itself and return expected return """
            self.log.append("%s %s %s" % (name, args, kwargs))
            return ret
        return new_fction

    def mock(self, name, module, attr, ret=None):
        """
        Replaces function of the module for dummy one and records the original.
        :param name: Under which name to log this function's call
        :param module: Module/class to be mocked
        :param attr: Name of the function inside the module
        :param ret: Return value of the dummy function
        """
        if hasattr(module, attr):
            self.originals.append((module, attr, getattr(module, attr)))
        else:
            self.originals.append((module, attr))
        setattr(module, attr, self.log_function(name, ret))

    def unmock_all(self):
        """ Restore the original functions """
        while True:
            try:
                params = self.originals.pop()
            except IndexError:
                break
            if len(params) == 3:
                setattr(params[0], params[1], params[2])
            else:
                delattr(params[0], params[1])

    def __del__(self):
        """ Don't rely on this and unmock_all manually """
        self.unmock_all()
