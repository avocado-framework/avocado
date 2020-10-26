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

"""
Avocado Utilities exit codes.

These codes are returned on the command-line and may be used by the Avocado
command-line utilities.
"""

#: The utility finished successfully
UTILITY_OK = 0x0000

#: The utility ran, but needs to signalize something minor, like a check
#: returning FALSE.
UTILITY_LOW = 0x0001

#: The utility ran, but needs to signalize a failure, like an internal action
#: that failed to execute.
UTILITY_MEDIUM = 0x0002

#: Something else went wrong and the utility failed (or crashed).
UTILITY_HIGH = 0x0004

#: The utility was explicitly interrupted. Usually this means that a user
#: hit CTRL+C while the utility was still running.
UTILITY_INTERRUPTED = 0x0008

#: Utility generic crash
UTILITY_GENERIC_CRASH = -1
