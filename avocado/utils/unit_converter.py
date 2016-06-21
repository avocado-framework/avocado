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
# Copyright: Red Hat Inc. 2016

"""
Unit Convertion related functions.
"""

import logging


def time_to_seconds(time):
    """
    Convert time in minutes, hours and days to seconds.
    :param time: Time including the unit (i.e. '10d')
    """
    units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
    mult = 1
    if time is not None:
        try:
            unit = time[-1].lower()
            if unit in units:
                mult = units[unit]
                seconds = int(time[:-1]) * mult
            else:
                seconds = int(time)
            if seconds < 1:
                raise ValueError()
        except (ValueError, TypeError):
            log = logging.getLogger("avocado.app")
            log.error("Invalid value '%s' for time. Use an integer number "
                      "greater than 0 or a string with the number and "
                      "the time unit (s, m, h or d).", time)
            return None
    else:
        seconds = 0
    return seconds
