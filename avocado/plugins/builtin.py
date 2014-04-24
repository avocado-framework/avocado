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

"""Builtin plugins."""

from importlib import import_module

__all__ = ['load_builtins']

Builtins = [('avocado.plugins.runner', 'TestLister'),
            ('avocado.plugins.runner', 'SystemInformation'),
            ('avocado.plugins.runner', 'TestRunner'),
            ('avocado.plugins.xunit', 'XUnit'),
            ('avocado.plugins.lister', 'PluginsList')]


def load_builtins(set_globals=True):
    """Load builtin plugins."""
    plugins = []
    for module, klass in Builtins:
        try:
            plugin_mod = import_module(module)
        except ImportError:
            continue
        if hasattr(plugin_mod, klass):
            plugin = getattr(plugin_mod, klass)
            plugins.append(plugin)
            if set_globals is True:
                globals()[klass] = plugin
    return plugins
