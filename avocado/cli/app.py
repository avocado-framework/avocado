# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; specifically version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: RedHat 2013-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

"""
The core Avocado application.
"""

from argparse import ArgumentParser

from avocado.plugins.manager import get_plugin_manager
from avocado.version import VERSION


class AvocadoApp(object):

    """
    Avocado application.
    """

    def __init__(self, external_plugins=None):
        self.external_plugins = external_plugins
        self.plugin_manager = None
        self.arg_parser = ArgumentParser(prog='avocado',
                                         version=VERSION,
                                         description='Avocado Test Runner')
        self.arg_parser.add_argument('-V', '--verbose', action='store_true',
                                     help='print extra debug messages',
                                     dest='verbose')
        self.arg_parser.add_argument('--logdir', action='store',
                                     help='Alternate logs directory',
                                     dest='logdir', default='')
        self.arg_parser.add_argument('--loglevel', action='store',
                                     help='Debug Level',
                                     dest='log_level', default='')
        self.arg_parser.add_argument('--plugins', action='store',
                                     help='Load extra plugins from directory',
                                     dest='plugins_dir', default='')

        args, _ = self.arg_parser.parse_known_args()
        subparsers = self.arg_parser.add_subparsers(title='subcommands',
                                                    description='valid subcommands',
                                                    help='subcommand help')

        self.load_plugin_manager(subparsers, args.plugins_dir)
        self.args = self.arg_parser.parse_args()

    def load_plugin_manager(self, parser, plugins_dir):
        """Load Plugin Manager.

        :param parser: Main argument parser.
        :param plugins_dir: Extra plugins directory.
        """
        self.plugin_manager = get_plugin_manager()
        self.plugin_manager.load_plugins(plugins_dir)
        if self.external_plugins:
            self.plugin_manager.add_plugins(self.external_plugins)
        self.plugin_manager.configure(parser)

    def run(self):
        return self.args.func(self.args)
