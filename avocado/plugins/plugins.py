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
from avocado.utils import astring


class Plugins(CLICmd):

    """
    Plugins information
    """

    name = 'plugins'
    description = 'Displays plugin information'

    def configure(self, parser):
        parser = super(Plugins, self).configure(parser)
        parser.add_argument('--paginator',
                            choices=('on', 'off'), default='on',
                            help='Turn the paginator on/off. '
                            'Current: %(default)s')

    def run(self, args):
        plugin_types = [
            (dispatcher.CLICmdDispatcher(),
             'Plugins that add new commands (cli.cmd):'),
            (dispatcher.CLIDispatcher(),
             'Plugins that add new options to commands (cli):'),
            (dispatcher.JobPrePostDispatcher(),
             'Plugins that run before/after the execution of jobs (job.prepost):'),
            (dispatcher.ResultDispatcher(),
             'Plugins that generate job result in different formats (result):'),
            (dispatcher.ResultEventsDispatcher(args),
             ('Plugins that generate job result based on job/test events '
              '(result_events):')),
            (dispatcher.VarianterDispatcher(),
             'Plugins that generate test variants (varianter): ')
        ]
        for plugins_active, msg in plugin_types:
            LOG_UI.info(msg)
            plugin_matrix = []
            for plugin in sorted(plugins_active, key=lambda x: x.name):
                plugin_matrix.append((plugin.name, plugin.obj.description))

            if not plugin_matrix:
                LOG_UI.debug("(No active plugin)")
            else:
                for line in astring.iter_tabular_output(plugin_matrix):
                    LOG_UI.debug(line)
                LOG_UI.debug("")
