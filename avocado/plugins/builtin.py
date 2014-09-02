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

import os
import logging
from importlib import import_module

from avocado.plugins.plugin import Plugin

log = logging.getLogger("avocado.plugins")

__all__ = ['load_builtins']

Modules = ['avocado.plugins.' + x[:-3]
           for x in os.listdir(os.path.dirname(__file__))
           if x.endswith('.py')]

Exclude = ['avocado.plugins.__init__',
           'avocado.plugins.builtin',
           'avocado.plugins.plugin',
           'avocado.plugins.manager']

Builtins = [x for x in Modules if x not in Exclude]


def load_builtins():
    """
    Load builtin plugins.

    :return: a list of plugin classes, ordered by `priority`.
    """
    plugins = []
    for module in Builtins:
        try:
            plugin_mod = import_module(module)
        except ImportError as err:
            log.error("Could not import module plugin '%s': %s", module, err)
            continue
        except Exception as err:
            log.error("Module plugin '%s' with error: %s", module, err)
            continue
        for name in plugin_mod.__dict__:
            obj = getattr(plugin_mod, name)
            if isinstance(obj, type) and issubclass(obj, Plugin):
                plugin = getattr(plugin_mod, name)
                plugins.append(plugin)
    return sorted(plugins, key=lambda plugin: plugin.priority)
