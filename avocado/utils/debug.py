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
