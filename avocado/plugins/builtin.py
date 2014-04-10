# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; specifically version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: RedHat 2013-2014
# Author: Ruda Moura <rmoura@redhat.com>

"""Builtin plugins."""

from importlib import import_module

__all__ = ['load_builtins']

Builtins = [('avocado.plugins.runner', 'TestLister'),
            ('avocado.plugins.runner', 'SystemInformation'),
            ('avocado.plugins.runner', 'TestRunner'),
            ('avocado.plugins.xunit', 'XUnit'), ]


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
