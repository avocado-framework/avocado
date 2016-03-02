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


import sys


def ordered_list_unique(object_list):
    """
    Returns an unique list of objects, with their original order preserved
    """
    seen = set()
    seen_add = seen.add
    return [x for x in object_list if not (x in seen or seen_add(x))]


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


class CallbackRegister(object):

    """
    Registers pickable functions to be executed later.
    """

    def __init__(self, name, log):
        """
        :param name: Human readable identifier of this register
        """
        self._name = name
        self._items = []
        self._log = log

    def register(self, func, args, kwargs, once=False):
        """
        Register function/args to be called on self.destroy()
        :param func: Pickable function
        :param args: Pickable positional arguments
        :param kwargs: Pickable keyword arguments
        :param once: Add unique (func,args,kwargs) combination only once
        """
        item = (func, args, kwargs)
        if not once or item not in self._items:
            self._items.append(item)

    def unregister(self, func, args, kwargs):
        """
        Unregister (func,args,kwargs) combination
        :param func: Pickable function
        :param args: Pickable positional arguments
        :param kwargs: Pickable keyword arguments
        """
        item = (func, args, kwargs)
        if item in self._items:
            self._items.remove(item)

    def run(self):
        """
        Call all registered function
        """
        while self._items:
            item = self._items.pop()
            try:
                func, args, kwargs = item
                func(*args, **kwargs)
            except:     # Ignore all exceptions pylint: disable=W0702
                self._log.error("%s failed to destroy %s:\n%s",
                                self._name, item, sys.exc_info()[1])

    def __del__(self):
        """
        :warning: Always call self.run() manually, this is not guaranteed
                  to be executed!
        """
        self.run()
