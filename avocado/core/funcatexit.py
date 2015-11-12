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
# This code was inspired in the virttest project,
# virttest/funcatexit.py
# Copyright: Red Hat Inc. 2015
# Authors: Lukas Doktor <ldoktor@redhat.com>


import sys
import logging

log = logging.getLogger("avocado.test")


class FuncAtExit(object):

    """
    Class for handling cleanups. Don't forget to call `destroy()`.
    """

    def __init__(self, name):
        """
        :param name: Human readable identificator/purpose of this destroyer
        """
        self._name = name
        self._items = []

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

    def destroy(self):
        """
        Call all registered function
        """
        while self._items:
            item = self._items.pop()
            try:
                func, args, kwargs = item
                func(*args, **kwargs)
            except:     # Ignore all exceptions pylint: disable=W0702
                log.error("%s failed to destroy %s:\n%s",
                          self._name, item, sys.exc_info()[1])

    def __del__(self):
        """
        :warning: Always call self.destroy() manually, this is not guarranteed
                  to be executed!
        """
        self.destroy()
