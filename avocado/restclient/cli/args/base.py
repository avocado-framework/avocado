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
This module has base action arguments that are used on other top level commands

These top level commands import these definitions for uniformity and
consistency sake
"""

__all__ = ['ADD', 'LIST_BRIEF', 'LIST_FULL', 'DELETE', 'NAME', 'ID']


#
# Arguments that are treated as actions
#
ADD = (('-a', '--add',),
       {'help': 'add a new entry',
        'action': 'store_true',
        'default': False})


LIST_BRIEF = (('-l', '--list-brief',),
              {'help': 'list all records briefly',
               'action': 'store_true',
               'default': False})


LIST_FULL = (('-L', '--list-full',),
             {'help': 'list all records with all information',
              'action': 'store_true',
              'default': False})


DELETE = (('-d', '--delete',),
          {'help': 'delete an existing object',
           'action': 'store_true',
           'default': False})


#
# Other arguments that will influence action behaviour
#
NAME = (('-n', '--name'),
        {'help': 'name of the object'})


ID = (('-i', '--id'),
      {'help': 'numeric identification of the object',
       'type': int})
