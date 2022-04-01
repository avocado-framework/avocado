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
Plugins information plugin
"""
from avocado.core import dispatcher
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLICmd
from avocado.core.resolver import Resolver
from avocado.core.settings import settings
from avocado.utils import astring


class Plugins(CLICmd):

    """
    Plugins information
    """

    name = 'plugins'
    description = 'Displays plugin information'

    def configure(self, parser):
        parser = super().configure(parser)
        help_msg = 'Will list the plugins in execution order'
        settings.register_option(section='plugins',
                                 key='ordered_list',
                                 default=False,
                                 key_type=bool,
                                 action='store_true',
                                 help_msg=help_msg,
                                 parser=parser,
                                 long_arg='--ordered',
                                 short_arg='-o')

    def run(self, config):
        plugin_types = [
            (dispatcher.InitDispatcher(),
             'Plugins that always need to be initialized (init): '),
            (dispatcher.CLICmdDispatcher(),
             'Plugins that add new commands (cli.cmd):'),
            (dispatcher.CLIDispatcher(),
             'Plugins that add new options to commands (cli):'),
            (dispatcher.JobPrePostDispatcher(),
             'Plugins that run before/after the execution of jobs (job.prepost):'),
            (dispatcher.ResultDispatcher(),
             'Plugins that generate job result in different formats (result):'),
            (dispatcher.ResultEventsDispatcher(config),
             ('Plugins that generate job result based on job/test events '
              '(result_events):')),
            (dispatcher.VarianterDispatcher(),
             'Plugins that generate test variants (varianter): '),
            (Resolver(),
             'Plugins that resolve test references (resolver): '),
            (dispatcher.RunnerDispatcher(),
             'Plugins that run test suites on a job (runners): '),
            (dispatcher.SpawnerDispatcher(),
             'Plugins that spawn tasks and know about their status (spawner): '),
            (dispatcher.RunnableRunnerDispatcher(),
             'Plugins that run runnables (under a task and spawner) (runnable.runner): '),
        ]
        for plugins_active, msg in plugin_types:
            LOG_UI.info(msg)
            plugin_matrix = []
            if config.get('plugins.ordered_list'):
                sorted_plugins = plugins_active.get_extentions_by_priority()
            else:
                sorted_plugins = plugins_active.get_extentions_by_name()
            for plugin in sorted_plugins:
                plugin_matrix.append((plugin.name, plugin.obj.description))

            if not plugin_matrix:
                LOG_UI.debug("(No active plugin)")
            else:
                for line in astring.iter_tabular_output(plugin_matrix):
                    LOG_UI.debug(line)
                LOG_UI.debug("")
