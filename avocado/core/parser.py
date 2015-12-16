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
# Author: Ruda Moura <rmoura@redhat.com>


"""
Avocado application command line parsing.
"""

import argparse
import os

from . import replay
from . import tree
from . import settings
from .version import VERSION

PROG = 'avocado'
DESCRIPTION = 'Avocado Test Runner'


class Parser(object):

    """
    Class to Parse the command line arguments.
    """

    def __init__(self):
        self.args = None
        self.subcommands = None
        self.application = argparse.ArgumentParser(
            prog=PROG,
            add_help=False,  # see parent parsing
            description=DESCRIPTION)
        self.application.add_argument('-v', '--version', action='version',
                                      version='Avocado %s' % VERSION)
        self.application.add_argument('--config', metavar='CONFIG_FILE',
                                      help='Use custom configuration from a file')

    def start(self):
        """
        Start to parsing arguments.

        At the end of this method, the support for subparsers is activated.
        Side effect: update attribute `args` (the namespace).
        """
        self.args, extra = self.application.parse_known_args()

        # Load settings from the source job, if this is a replay job
        if '--replay' in extra:
            self.application.add_argument('--replay')
            self.application.add_argument('--replay-ignore')
            self.args, extra = self.application.parse_known_args()
            if (self.args.replay_ignore is not None and
               'config' not in self.args.replay_ignore):
                logs_dir = settings.settings.get_value('datadir.paths',
                                                       'logs_dir',
                                                       default=None)
                logs = os.path.expanduser(logs_dir)
                resultsdir, _ = replay.get_resultsdir(logs, self.args.replay)
                replay_config = os.path.join(resultsdir, 'replay', 'config')
                with open(replay_config, 'r') as f:
                    settings.settings.process_config_path(f.read())

        # Load settings from file, if user provides one
        if self.args.config is not None:
            settings.settings.process_config_path(self.args.config)

        # Use parent parsing to avoid breaking the output of --help option
        self.application = argparse.ArgumentParser(prog=PROG,
                                                   description=DESCRIPTION,
                                                   parents=[self.application])

        # Subparsers where Avocado subcommands are plugged
        self.subcommands = self.application.add_subparsers(
            title='subcommands',
            description='valid subcommands',
            help='subcommand help',
            dest='subcommand')

        if tree.MULTIPLEX_CAPABLE:
            # Allow overriding multiplex variants by plugins args
            self.args.default_multiplex_tree = tree.TreeNode()

    def finish(self):
        """
        Finish the process of parsing arguments.

        Side effect: set the final value for attribute `args`.
        """
        self.args = self.application.parse_args(namespace=self.args)
