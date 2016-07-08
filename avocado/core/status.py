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
           "INTERRUPTED": False}

user_facing_status = ["SKIP",
                      "ERROR",
                      "FAIL",
                      "WARN",
                      "PASS",
                      "INTERRUPTED"]

feedback = {
    # Test did not advertise current status, but process running the test is
    # known to be still running
    '.': 'Process Running',

    # Test advertised its current status explicitly (by means of a formal test
    # API, so user can be sure his test not only has a process running, but
    # is performing its intended tasks
    'T': 'Test Running',

    # The process is paused because a binary was run under a debugger and hit
    # a breakpoint. The breakpoint may be a breakpoint explicitly set by the
    # user or a signal that is automatically caught, such as a SIGSEGV
    'D': 'Paused for debugging',

    # The test has ended and either passed or failed. After this message, a
    # proper test result should be passed so that it is presented to the
    # user and passed along other result plugins.
    'P': 'Passed (ended)',
    'F': 'Failed (ended)'
}
