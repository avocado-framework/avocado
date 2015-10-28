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
# Copyright: Red Hat Inc. 2013-2014
# Author: Ruda Moura <rmoura@redhat.com>

"""Plugin Managers."""

import logging

from .builtin import load_builtins


DefaultPluginManager = None

log = logging.getLogger("avocado.plugins")


class PluginManager(object):

    """
    Base class for plugins manager.

    You'll inherit from this to write you own plugins manager.
    """

    def __init__(self):
        self.plugins = []

    def add_plugin(self, plugin):
        self.plugins.append(plugin)

    def load_plugins(self):
        raise NotImplementedError('Managers must implement the method load_plugins')

    def configure(self, parser):
        for plugin in self.plugins:
            if plugin.enabled:
                try:
                    plugin.configure(parser)
                except Exception as err:
                    log.error("Could not configure plugin '%s': %s",
                              plugin.name, err)

    def activate(self, app_args):
        for plugin in self.plugins:
            if plugin.configured:
                try:
                    plugin.activate(app_args)
                except Exception as err:
                    log.error("Could not activate plugin '%s': %s",
                              plugin.name, err)


class BuiltinPluginManager(PluginManager):

    """
    Builtins plugin manager.
    """

    def load_plugins(self):
        for plugin in load_builtins():
            try:
                self.add_plugin(plugin())
            except Exception as err:
                if hasattr(plugin, 'name'):
                    name = plugin.name
                else:
                    name = str(plugin)
                log.error("Could not activate builtin plugin '%s': %s",
                          name, err)


class AvocadoPluginManager(BuiltinPluginManager):

    """
    Avocado Plugin Manager.

    Load builtins and external plugins.
    """

    def __init__(self):
        BuiltinPluginManager.__init__(self)

    def load_plugins(self):
        BuiltinPluginManager.load_plugins(self)


def get_plugin_manager():
    """
    Get default plugin manager.
    """
    global DefaultPluginManager
    if DefaultPluginManager is None:
        DefaultPluginManager = AvocadoPluginManager()
    return DefaultPluginManager
