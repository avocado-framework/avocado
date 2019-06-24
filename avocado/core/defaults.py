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
# Copyright: Red Hat Inc. 2018
# Author: Cleber Rosa <crosa@redhat.com>

"""
The Avocado core defaults
"""

#: The encoding used by default on all data input
ENCODING = 'utf-8'

#: The amount of time to give to the test process after it it has been
#: interrupted (such as with CTRL+C)
TIMEOUT_AFTER_INTERRUPTED = 60

#: The amount of to wait for a test status after the process
#: has been noticed to be dead
TIMEOUT_PROCESS_DIED = 10

#: The amount of time to wait after a test has reported status
#: but the test process has not finished
TIMEOUT_PROCESS_ALIVE = 60
