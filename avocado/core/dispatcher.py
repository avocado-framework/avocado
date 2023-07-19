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

import inspect
import sys

from avocado.core.enabled_extension_manager import EnabledExtensionManager


def get_dispatchers(module_name):
    """Returns the classes that implement plugin dispatching

    These should inherit from the *ExtensionManager base classes
    and contain suitable descriptions.

    The produced values are tuples that contain the dispatcher class
    and two booleans that indicates whether the configuration and job
    is needed to instantiate the class.
    """
    module = sys.modules[module_name]
    for _, klass in inspect.getmembers(module):
        if (
            inspect.isclass(klass)
            and issubclass(klass, EnabledExtensionManager)
            and hasattr(klass, "PLUGIN_DESCRIPTION")
        ):
            params = list(inspect.signature(klass.__init__).parameters)
            if len(params) == 1:
                yield (klass, False, False)
            elif len(params) == 2 and params[1] == "config":
                yield (klass, True, False)
            elif len(params) == 3 and params[1] == "config" and params[2] == "job":
                yield (klass, True, True)


class CLIDispatcher(EnabledExtensionManager):

    """
    Calls extensions on configure/run

    Automatically adds all the extension with entry points registered under
    'avocado.plugins.cli'
    """

    PLUGIN_DESCRIPTION = "Plugins that add new options to commands (cli)"

    def __init__(self):
        super().__init__("avocado.plugins.cli")


class CLICmdDispatcher(EnabledExtensionManager):

    """
    Calls extensions on configure/run

    Automatically adds all the extension with entry points registered under
    'avocado.plugins.cli.cmd'
    """

    PLUGIN_DESCRIPTION = "Plugins that add new commands (cli.cmd)"

    def __init__(self):
        super().__init__("avocado.plugins.cli.cmd")


class JobPrePostDispatcher(EnabledExtensionManager):

    """
    Calls extensions before Job execution

    Automatically adds all the extension with entry points registered under
    'avocado.plugins.job.prepost'
    """

    PLUGIN_DESCRIPTION = (
        "Plugins that run before/after the execution of jobs (job.prepost)"
    )

    def __init__(self):
        super().__init__("avocado.plugins.job.prepost")


class TestPreDispatcher(EnabledExtensionManager):

    """
    Calls extensions before Test execution

    Automatically adds all the extension with entry points registered under
    'avocado.plugins.test.pre'
    """

    PLUGIN_DESCRIPTION = "Plugins that run before the execution of each test (test.pre)"

    def __init__(self):
        super().__init__("avocado.plugins.test.pre")


class TestPostDispatcher(EnabledExtensionManager):

    """
    Calls extensions after Test execution

    Automatically adds all the extension with entry points registered under
    'avocado.plugins.test.post'
    """

    PLUGIN_DESCRIPTION = "Plugins that run after the execution of each test (test.post)"

    def __init__(self):
        super().__init__("avocado.plugins.test.post")


class ResultDispatcher(EnabledExtensionManager):

    PLUGIN_DESCRIPTION = (
        "Plugins that generate job result in different formats (result)"
    )

    def __init__(self):
        super().__init__("avocado.plugins.result")


class ResultEventsDispatcher(EnabledExtensionManager):

    PLUGIN_DESCRIPTION = (
        "Plugins that generate job result based on job/test events (result_events)"
    )

    def __init__(self, config):
        super().__init__(
            "avocado.plugins.result_events", invoke_kwds={"config": config}
        )


class VarianterDispatcher(EnabledExtensionManager):

    PLUGIN_DESCRIPTION = "Plugins that generate test variants (varianter)"

    def __init__(self):
        super().__init__("avocado.plugins.varianter")

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
        return super().map_method_with_return(
            method_name, deepcopy=False, *args, **kwargs
        )

    def map_method_with_return_copy(self, method_name, *args, **kwargs):
        """
        The same as map_method_with_return, but use copy.deepcopy on each passed arg
        """
        return super().map_method_with_return(
            method_name, deepcopy=True, *args, **kwargs
        )


class SuiteRunnerDispatcher(EnabledExtensionManager):

    PLUGIN_DESCRIPTION = "Plugins that run test suites on a job (suite.runner)"

    def __init__(self):
        super().__init__("avocado.plugins.suite.runner")


class InitDispatcher(EnabledExtensionManager):

    PLUGIN_DESCRIPTION = "Plugins that always need to be initialized (init)"

    def __init__(self):
        super().__init__("avocado.plugins.init")


class SpawnerDispatcher(EnabledExtensionManager):

    PLUGIN_DESCRIPTION = (
        "Plugins that spawn tasks and know about their status (spawner)"
    )

    def __init__(self, config=None, job=None):
        super().__init__(
            "avocado.plugins.spawner", invoke_kwds={"job": job, "config": config}
        )


class RunnableRunnerDispatcher(EnabledExtensionManager):

    PLUGIN_DESCRIPTION = (
        "Plugins that run runnables (under a task and spawner) (runnable.runner)"
    )

    def __init__(self):
        super().__init__("avocado.plugins.runnable.runner")


class CacheDispatcher(EnabledExtensionManager):

    PLUGIN_DESCRIPTION = "Plugins that manipulates with avocado cache (cache)"

    def __init__(self):
        super().__init__("avocado.plugins.cache")
