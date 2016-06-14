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
# Copyright: Red Hat Inc. 2016
# Author: Amador Pahim <apahim@redhat.com>

from avocado.core.plugin_interfaces import CLI


class EnvKeep(CLI):

    """
    Keep environment variables on remote executions
    """

    name = 'envkeep'
    description = "Keep variables in remote environment"

    def configure(self, parser):
        run_subcommand_parser = parser.subcommands.choices.get('run', None)
        if run_subcommand_parser is None:
            return

        msg = 'keep environment variables'
        env_keep_parser = run_subcommand_parser.add_argument_group(msg)
        env_keep_parser.add_argument('--env-keep', dest='env_keep',
                                     default=None,
                                     type=self._parse_env_keep,
                                     help='Keep environment variables in '
                                          'remote executions')

    def _parse_env_keep(self, string):
        return string.split(',')

    def run(self, args):
        pass
