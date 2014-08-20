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
# Copyright: Red Hat Inc. 2013-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

"""
The core Avocado application.
"""

import os
import sys

from argparse import ArgumentParser

from avocado.plugins.manager import get_plugin_manager
from avocado.version import VERSION


class AvocadoApp(object):

    """
    Avocado application.
    """

    def __init__(self, external_plugins=None):

        # Catch all libc runtime errors to STDERR
        os.environ['LIBC_FATAL_STDERR_'] = '1'

        self.external_plugins = external_plugins
        self.plugin_manager = None
        self.app_parser = ArgumentParser(prog='avocado',
                                         version=VERSION,
                                         add_help=False,  # see parent parse
                                         description='Avocado Test Runner')
        self.app_parser.add_argument('-V', '--verbose', action='store_true',
                                     help='print extra debug messages',
                                     dest='verbose')
        self.app_parser.add_argument('--logdir', action='store',
                                     help='Alternate logs directory',
                                     dest='logdir', default='')
        self.app_parser.add_argument('--loglevel', action='store',
                                     help='Debug Level',
                                     dest='log_level', default='')
        self.app_parser.add_argument('--plugins', action='store',
                                     help='Load extra plugins from directory',
                                     dest='plugins_dir', default='')
        args, _ = self.app_parser.parse_known_args()

        # Use parent parsing to avoid break output of --help option
        self.app_parser = ArgumentParser(parents=[self.app_parser])

        # Subparsers where Avocado subcommands are plugged
        self.cmd_parser = self.app_parser.add_subparsers(
            title='subcommands',
            description='valid subcommands',
            help='subcommand help')
        self.load_plugin_manager(args.plugins_dir)

        default_args = None
        if not sys.argv[1:]:
            default_args = ['--help']
        args, _ = self.app_parser.parse_known_args(args=default_args)

        self.plugin_manager.activate(args)
        self.args = self.app_parser.parse_args()

    def load_plugin_manager(self, plugins_dir):
        """Load Plugin Manager.

        :param plugins_dir: Extra plugins directory.
        """
        self.plugin_manager = get_plugin_manager()
        self.plugin_manager.load_plugins(plugins_dir)
        if self.external_plugins:
            self.plugin_manager.add_plugins(self.external_plugins)
        self.plugin_manager.configure(self.app_parser, self.cmd_parser)

    def run(self):
        return self.args.func(self.args)
