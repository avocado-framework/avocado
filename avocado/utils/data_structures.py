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
# Copyright: Red Hat Inc. 2014
#
# Authors: Ruda Moura <rmoura@redhat.com>
#          Lucas Meneghel Rodrigues <lmr@redhat.com>
#
"""
This module contains handy classes that can be used inside
avocado core code or plugins.
"""


class Borg:

    """
    Multiple instances of this class will share the same state.

    This is considered a better design pattern in Python than
    more popular patterns, such as the Singleton. Inspired by
    Alex Martelli's article mentioned below:

    :see: http://www.aleax.it/5ep.html
    """

    __shared_state = {}

    def __init__(self):
        self.__dict__ = self.__shared_state


class LazyProperty(object):

    """
    Lazily instantiated property.

    Use this decorator when you want to set a property that will only be
    evaluated the first time it's accessed. Inspired by the discussion in
    the Stack Overflow thread below:

    :see: http://stackoverflow.com/questions/15226721/
    """

    def __init__(self, f_get):
        self.f_get = f_get
        self.func_name = f_get.__name__

    def __get__(self, obj, cls):
        if obj is None:
            return None
        value = self.f_get(obj)
        setattr(obj, self.func_name, value)
        return value
