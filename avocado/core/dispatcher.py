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

from .enabled_extension_manager import EnabledExtensionManager


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

    def __init__(self, config):
        super(ResultEventsDispatcher, self).__init__(
            'avocado.plugins.result_events',
            invoke_kwds={'config': config})


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

    def map_method_with_return(self, method_name, *args, **kwargs):
        return super(VarianterDispatcher, self).map_method_with_return(
            method_name, deepcopy=False, *args, **kwargs)

    def map_method_with_return_copy(self, method_name, *args, **kwargs):
        """
        The same as map_method_with_return, but use copy.deepcopy on each passed arg
        """
        return super(VarianterDispatcher, self).map_method_with_return(
            method_name, deepcopy=True, *args, **kwargs)


class RunnerDispatcher(EnabledExtensionManager):

    def __init__(self):
        super(RunnerDispatcher, self).__init__('avocado.plugins.runner')


class InitDispatcher(EnabledExtensionManager):

    def __init__(self):
        super(InitDispatcher, self).__init__('avocado.plugins.init')


class SpawnerDispatcher(EnabledExtensionManager):

    def __init__(self, config=None):
        super(SpawnerDispatcher, self).__init__('avocado.plugins.spawner',
                                                invoke_kwds={'config': config})
