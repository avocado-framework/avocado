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
Valid test statuses and whether they signal success (or failure).
"""

#: Maps the different status strings in avocado to booleans.
STATUSES_MAPPING = {"SKIP": True,
                    "ERROR": False,
                    "FAIL": False,
                    "WARN": True,
                    "PASS": True,
                    "INTERRUPTED": False,
                    "CANCEL": True}

#: Valid test statuses, if a returned status is not listed here, it
#: should be handled as error condition.
STATUSES = [key for key in STATUSES_MAPPING.keys()]
