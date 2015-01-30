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
# Copyright (c) 2013-2015 Red Hat
# Author: Cleber Rosa <cleber@redhat.com>

"""
This module defines the command line arguments that will be available on
the avocado-rest-client tool when the top level command (and module) job
is executed
"""

from avocado.restclient.cli.args import base


__all__ = ['ACTION_ARGUMENTS',
           'ARGUMENTS']

#
# Action arguments
#
ACTION_ADD = (('-a', '--add'),
              {'help': 'add (create) a new job',
               'action': 'store_true',
               'default': False})

ACTION_DELETE = (('-d', '--delete'),
                 {'help': 'delete (abort) a queued or running job',
                  'default': False,
                  'metavar': 'JOB_ID'})

ACTION_SHOW = (('-s', '--show'),
               {'help': 'shows details about a job',
                'default': False,
                'type': int,
                'metavar': 'JOB_ID'})

#
# Arguments that are treated as actions
#
ACTION_ARGUMENTS = [base.LIST_BRIEF,
                    ACTION_ADD,
                    ACTION_DELETE,
                    ACTION_SHOW]


#
# Other arguments that will influence action behaviour
#
ARGUMENTS = []
