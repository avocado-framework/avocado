"""Builtin plugins."""

import logging

from importlib import import_module

__all__ = ['load_builtins']

Builtins = [('avocado.plugins.runner', 'TestListerRunner'),
            ('avocado.plugins.runner', 'SimpleTestRunner'), ]


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
