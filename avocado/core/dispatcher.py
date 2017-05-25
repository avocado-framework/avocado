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

"""Extensions/plugins dispatchers."""

import copy
import sys

from stevedore import EnabledExtensionManager

from .settings import settings
from .settings import SettingsError
from .output import LOG_UI
from ..utils import stacktrace


class Dispatcher(EnabledExtensionManager):

    """
    Base dispatcher for various extension types
    """

    #: Default namespace prefix for Avocado extensions
    NAMESPACE_PREFIX = 'avocado.plugins.'

    def __init__(self, namespace, invoke_kwds={}):
        self.load_failures = []
        super(Dispatcher, self).__init__(namespace=namespace,
                                         check_func=self.enabled,
                                         invoke_on_load=True,
                                         invoke_kwds=invoke_kwds,
                                         on_load_failure_callback=self.store_load_failure,
                                         propagate_map_exceptions=True)

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

        :param extension: an Stevedore Extension instance
        :type extension: :class:`stevedore.extension.Extension`
        """
        return "%s.%s" % (self.plugin_type(), extension.entry_point.name)

    def settings_section(self):
        """
        Returns the config section name for the plugin type handled by itself
        """
        return "plugins.%s" % self.plugin_type()

    def enabled(self, extension):
        """
        Checks configuration for explicit mention of plugin in a disable list

        If configuration section or key doesn't exist, it means no plugin
        is disabled.
        """
        try:
            disabled = settings.get_value('plugins', 'disable', key_type=list)
            return self.fully_qualified_name(extension) not in disabled
        except SettingsError:
            return True

    def names(self):
        """
        Returns the names of the discovered extensions

        This differs from :func:`stevedore.extension.ExtensionManager.names`
        in that it returns names in a predictable order, by using standard
        :func:`sorted`.
        """
        return sorted(super(Dispatcher, self).names())

    def _init_plugins(self, extensions):
        super(Dispatcher, self)._init_plugins(extensions)
        self.extensions.sort(key=lambda x: x.name)
        configured_order = settings.get_value(self.settings_section(), "order",
                                              key_type=list, default=[])
        ordered = []
        for name in configured_order:
            for ext in self.extensions:
                if name == ext.name:
                    ordered.append(ext)
        for ext in self.extensions:
            if ext not in ordered:
                ordered.append(ext)
        self.extensions = ordered

    @staticmethod
    def store_load_failure(manager, entrypoint, exception):
        manager.load_failures.append((entrypoint, exception))


class CLIDispatcher(Dispatcher):

    """
    Calls extensions on configure/run

    Automatically adds all the extension with entry points registered under
    'avocado.plugins.cli'
    """

    def __init__(self):
        super(CLIDispatcher, self).__init__('avocado.plugins.cli')


class CLICmdDispatcher(Dispatcher):

    """
    Calls extensions on configure/run

    Automatically adds all the extension with entry points registered under
    'avocado.plugins.cli.cmd'
    """

    def __init__(self):
        super(CLICmdDispatcher, self).__init__('avocado.plugins.cli.cmd')


class JobPrePostDispatcher(Dispatcher):

    """
    Calls extensions before Job execution

    Automatically adds all the extension with entry points registered under
    'avocado.plugins.job.prepost'
    """

    def __init__(self):
        super(JobPrePostDispatcher, self).__init__('avocado.plugins.job.prepost')

    def map_method(self, method_name, job):
        for ext in self.extensions:
            try:
                if hasattr(ext.obj, method_name):
                    method = getattr(ext.obj, method_name)
                    method(job)
            except SystemExit:
                raise
            except KeyboardInterrupt:
                raise
            except:
                job.log.error('Error running method "%s" of plugin "%s": %s',
                              method_name, ext.name, sys.exc_info()[1])


class ResultDispatcher(Dispatcher):

    def __init__(self):
        super(ResultDispatcher, self).__init__('avocado.plugins.result')

    def map_method(self, method_name, result, job):
        for ext in self.extensions:
            try:
                if hasattr(ext.obj, method_name):
                    method = getattr(ext.obj, method_name)
                    method(result, job)
            except SystemExit:
                raise
            except KeyboardInterrupt:
                raise
            except:
                job.log.error('Error running method "%s" of plugin "%s": %s',
                              method_name, ext.name, sys.exc_info()[1])


class ResultEventsDispatcher(Dispatcher):

    def __init__(self, args):
        super(ResultEventsDispatcher, self).__init__(
            'avocado.plugins.result_events',
            invoke_kwds={'args': args})

    def map_method(self, method_name, *args):
        for ext in self.extensions:
            try:
                if hasattr(ext.obj, method_name):
                    method = getattr(ext.obj, method_name)
                    method(*args)
            except SystemExit:
                raise
            except KeyboardInterrupt:
                raise
            except:
                LOG_UI.error('Error running method "%s" of plugin "%s": %s',
                             method_name, ext.name, sys.exc_info()[1])


class VarianterDispatcher(Dispatcher):

    def __init__(self):
        super(VarianterDispatcher, self).__init__('avocado.plugins.varianter')

    def __getstate__(self):
        """
        Very fragile pickle which works when all Varianter plugins are
        available on both machines.

        TODO: Replace this with per-plugin-refresh-mechanism
        """
        return {"extensions": getattr(self, "extensions")}

    def __setstate__(self, state):
        """
        Very fragile pickle which works when all Varianter plugins are
        available on both machines.

        TODO: Replace this with per-plugin-refresh-mechanism
        """
        self.__init__()
        self.extensions = state.get("extensions")

    def _map_method(self, method_name, deepcopy=False, *args, **kwargs):
        """
        :warning: **kwargs are not supported for deepcopy=True
        """
        ret = []
        for ext in self.extensions:
            try:
                if hasattr(ext.obj, method_name):
                    method = getattr(ext.obj, method_name)
                    if deepcopy:
                        copied_args = [copy.deepcopy(arg) for arg in args]
                        ret.append(method(*copied_args))
                    else:
                        ret.append(method(*args, **kwargs))
            except SystemExit:
                raise
            except KeyboardInterrupt:
                raise
            except:     # catch any exception pylint: disable=W0702
                stacktrace.log_exc_info(sys.exc_info(), logger='avocado.debug')
                LOG_UI.error('Error running method "%s" of plugin "%s": %s',
                             method_name, ext.name, sys.exc_info()[1])
        return ret

    def map_method(self, method_name, *args, **kwargs):
        return self._map_method(method_name, False, *args, **kwargs)

    def map_method_copy(self, method_name, *args):
        """
        The same as map_method, but use copy.deepcopy on each passed arg
        """
        return self._map_method(method_name, True, *args)
