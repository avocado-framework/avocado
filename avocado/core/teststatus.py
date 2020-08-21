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
Maps the different status strings in avocado to booleans.

This is used by methods and functions to return a cut and dry answer to whether
a test or a job in avocado PASSed or FAILed.
"""

mapping = {"SKIP": True,
           "ABORT": False,
           "ERROR": False,
           "FAIL": False,
           "WARN": True,
           "PASS": True,
           "START": True,
           "ALERT": False,
           "RUNNING": False,
           "NOSTATUS": False,
           "INTERRUPTED": False,
           "CANCEL": True}

user_facing_status = ["SKIP",
                      "ERROR",
                      "FAIL",
                      "WARN",
                      "PASS",
                      "INTERRUPTED",
                      "CANCEL"]
