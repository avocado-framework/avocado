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

import sys
import argparse

from avocado.version import VERSION
from avocado.settings import Settings

PROG = 'avocado'
DESCRIPTION = 'Avocado Test Runner'


class Parser(object):

    """
    Class to Parse the command line arguments.
    """

    def __init__(self):
        self.application = argparse.ArgumentParser(
            prog=PROG,
            add_help=False,  # see parent parsing
            description=DESCRIPTION)
        self.application.add_argument('-v', '--version', action='version',
                                      version='Avocado %s' % VERSION)
        self.application.add_argument('-c', '--config',
                                      dest='avocado_conf', default=None)
        self.application.add_argument('--plugins', action='store',
                                      help='Load extra plugins from directory',
                                      dest='plugins_dir', default='')

    def start(self):
        """
        Start to parsing arguments.

        At the end of this method, the support for subparsers is activated.
        Side effect: update attribute `args` (the namespace).
        """
        self.args, _ = self.application.parse_known_args()
        self.args.settings = Settings(self.args.avocado_conf)

        # Use parent parsing to avoid breaking the output of --help option
        self.application = argparse.ArgumentParser(prog=PROG,
                                                   description=DESCRIPTION,
                                                   parents=[self.application])

        # Subparsers where Avocado subcommands are plugged
        self.subcommands = self.application.add_subparsers(
            title='subcommands',
            description='valid subcommands',
            help='subcommand help')

    def resume(self):
        """
        Resume the parsing of arguments.

        Side effect: update attribute `args` (the namespace).
        """
        # Inject --help if no arguments is present
        default_args = ['--help'] if not sys.argv[1:] else None
        self.args, rest = self.application.parse_known_args(args=default_args)
        if not hasattr(self.args, 'func'):
            self.application.set_defaults(func=self.application.print_help)

    def finish(self):
        """
        Finish the process of parsing arguments.

        Side effects:
        - Set the final value for attribute `args`.
        - Set the configuration settings to attribute `settings`.
        """
        self.args = self.application.parse_args()
        self.args.settings = Settings(self.args.avocado_conf)

    def take_action(self):
        """
        Take some action after parsing arguments.
        """
        return self.args.func(self.args)
