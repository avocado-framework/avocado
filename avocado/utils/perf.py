# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; specifically version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Authors: Nageswara R Sastry <rnsastry@linux.vnet.ibm.com>

"""
Avocado perf related functions.
"""

from . import process


def get_events(pattern):
    """
    Run 'perf list' command and when matches with the pattern creates a
    list and return it.

    :param pattern: Pattern to search.
    :type pattern: str.

    :return: list of events matching the 'pattern'.
    :rtype: list of str.
    """
    list_of_events = []
    for line in process.run("perf list").stdout.split('\n'):
        if pattern in line:
            list_of_events.append(line)
    return list_of_events
