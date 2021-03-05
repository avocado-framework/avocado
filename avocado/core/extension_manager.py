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
# Copyright: Red Hat Inc. 2015-2019
# Author: Cleber Rosa <cleber@redhat.com>

"""
Base extension manager

This is a mix of stevedore-like APIs and behavior, with Avocado's
own look and feel.
"""

import copy
import logging
import sys

import pkg_resources

from ..utils import stacktrace

# This is also defined in avocado.core.output, but this avoids a
# circular import
LOG_UI = logging.getLogger("avocado.app")


class Extension:
    """
    This is a verbatim copy from the stevedore.extension class with the
    same name
    """

    def __init__(self, name, entry_point, plugin, obj):
        self.name = name
        self.entry_point = entry_point
        self.plugin = plugin
        self.obj = obj


class ExtensionManager:

    #: Default namespace prefix for Avocado extensions
    NAMESPACE_PREFIX = 'avocado.plugins.'

    def __init__(self, namespace, invoke_kwds=None):
        self.namespace = namespace
        self.extensions = []
        self.load_failures = []
        if invoke_kwds is None:
            invoke_kwds = {}

        # load plugins
        for ep in pkg_resources.iter_entry_points(self.namespace):
            try:
                plugin = ep.load()
                obj = plugin(**invoke_kwds)
            except ImportError as exception:
                self.load_failures.append((ep, exception))
            else:
                ext = Extension(ep.name, ep, plugin, obj)
                if self.enabled(ext):  # lgtm [py/init-calls-subclass]
                    self.extensions.append(ext)
        self.extensions.sort(key=lambda x: x.name)

    def enabled(self, extension):  # pylint: disable=W0613,R0201
        """
        Checks if a plugin is enabled

        Sub classes can change this implementation to determine their own
        criteria.
        """
        return True

    def plugin_type(self):
        """
        Subset of entry points namespace for this dispatcher

        Given an entry point `avocado.plugins.foo`, plugin type is `foo`.  If
        entry point does not conform to the Avocado standard prefix, it's
        returned unchanged.
        """
        if self.namespace.startswith(self.NAMESPACE_PREFIX):
            return self.namespace[len(self.NAMESPACE_PREFIX):]
        else:
            return self.namespace

    def fully_qualified_name(self, extension):
        """
        Returns the Avocado fully qualified plugin name

        :param extension: an Extension instance
        :type extension: :class:`Extension`
        """
        return "%s.%s" % (self.plugin_type(), extension.entry_point.name)

    def settings_section(self):
        """
        Returns the config section name for the plugin type handled by itself
        """
        return "plugins.%s" % self.plugin_type()

    def names(self):
        """
        Returns the names of the discovered extensions

        This differs from :func:`stevedore.extension.ExtensionManager.names`
        in that it returns names in a predictable order, by using standard
        :func:`sorted`.
        """
        return sorted(super(ExtensionManager, self).names())

    def map_method_with_return(self, method_name, *args, **kwargs):
        """
        The same as `map_method` but additionally reports the list of returned
        values and optionally deepcopies the passed arguments

        :param method_name: Name of the method to be called on each ext
        :param args: Arguments to be passed to all called functions
        :param kwargs: Key-word arguments to be passed to all called functions
                        if `"deepcopy" == True` is present in kwargs the
                        args and kwargs are deepcopied before passing it
                        to each called function.
        """
        deepcopy = kwargs.pop("deepcopy", False)
        ret = []
        for ext in self.extensions:
            try:
                if hasattr(ext.obj, method_name):
                    method = getattr(ext.obj, method_name)
                    if deepcopy:
                        copied_args = [copy.deepcopy(arg) for arg in args]
                        copied_kwargs = copy.deepcopy(kwargs)
                        ret.append(method(*copied_args, **copied_kwargs))
                    else:
                        ret.append(method(*args, **kwargs))
            except SystemExit:
                raise
            except KeyboardInterrupt:
                raise
            except:     # catch any exception pylint: disable=W0702
                stacktrace.log_exc_info(sys.exc_info(),
                                        logger='avocado.app.debug')
                LOG_UI.error('Error running method "%s" of plugin "%s": %s',
                             method_name, ext.name, sys.exc_info()[1])
        return ret

    def map_method(self, method_name, *args):
        """
        Maps method_name on each extension in case the extension has the attr

        :param method_name: Name of the method to be called on each ext
        :param args: Arguments to be passed to all called functions
        """
        for ext in self.extensions:
            try:
                if hasattr(ext.obj, method_name):
                    method = getattr(ext.obj, method_name)
                    method(*args)
            except SystemExit:
                raise
            except KeyboardInterrupt:
                raise
            except:     # catch any exception pylint: disable=W0702
                stacktrace.log_exc_info(sys.exc_info(),
                                        logger='avocado.app.debug')
                LOG_UI.error('Error running method "%s" of plugin "%s": %s',
                             method_name, ext.name, sys.exc_info()[1])

    def __getitem__(self, name):
        for ext in self.extensions:
            if ext.name == name:
                return ext
        raise KeyError

    def __iter__(self):
        return iter(self.extensions)
