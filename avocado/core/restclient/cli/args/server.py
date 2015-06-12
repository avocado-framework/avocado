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
# Copyright: Red Hat Inc. 2015
# Author: Cleber Rosa <cleber@redhat.com>

"""
This module has actions for the server command
"""

from . import base


__all__ = ['ACTION_STATUS', 'ACTION_ARGUMENTS', 'ARGUMENTS']


#
# Arguments that are treated as actions
#
ACTION_STATUS = (('-s', '--status',),
                 {'help': 'shows the avocado-server status',
                  'action': 'store_true',
                  'default': False})

#
# Arguments that are treated as actions
#
ACTION_ARGUMENTS = [base.LIST_BRIEF,
                    ACTION_STATUS]

#
# Other arguments that will influence action behaviour
#
ARGUMENTS = []
