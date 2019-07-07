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

"""
Extensions/plugins dispatchers

Besides the dispatchers listed here, there's also a lower level
dispatcher that these depend upon:
:class:`avocado.core.settings_dispatcher.SettingsDispatcher`
"""

from .extension_manager import ExtensionManager
from .settings import settings
from .settings import SettingsError


class EnabledExtensionManager(ExtensionManager):

    def __init__(self, namespace, invoke_kwds=None):
        super(EnabledExtensionManager, self).__init__(namespace, invoke_kwds)
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


class CLIDispatcher(EnabledExtensionManager):

    """
    Calls extensions on configure/run

    Automatically adds all the extension with entry points registered under
    'avocado.plugins.cli'
    """

    def __init__(self):
        super(CLIDispatcher, self).__init__('avocado.plugins.cli')


class CLICmdDispatcher(EnabledExtensionManager):

    """
    Calls extensions on configure/run

    Automatically adds all the extension with entry points registered under
    'avocado.plugins.cli.cmd'
    """

    def __init__(self):
        super(CLICmdDispatcher, self).__init__('avocado.plugins.cli.cmd')


class JobPrePostDispatcher(EnabledExtensionManager):

    """
    Calls extensions before Job execution

    Automatically adds all the extension with entry points registered under
    'avocado.plugins.job.prepost'
    """

    def __init__(self):
        super(JobPrePostDispatcher, self).__init__('avocado.plugins.job.prepost')


class ResultDispatcher(EnabledExtensionManager):

    def __init__(self):
        super(ResultDispatcher, self).__init__('avocado.plugins.result')


class ResultEventsDispatcher(EnabledExtensionManager):

    def __init__(self, args):
        super(ResultEventsDispatcher, self).__init__(
            'avocado.plugins.result_events',
            invoke_kwds={'args': args})


class VarianterDispatcher(EnabledExtensionManager):

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

    def map_method(self, method_name, *args, **kwargs):
        return self.map_method_with_return(method_name, deepcopy=False, *args,
                                           **kwargs)

    def map_method_copy(self, method_name, *args, **kwargs):
        """
        The same as map_method, but use copy.deepcopy on each passed arg
        """
        return self.map_method_with_return(method_name, deepcopy=True, *args,
                                           **kwargs)
