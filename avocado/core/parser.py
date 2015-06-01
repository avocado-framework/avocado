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

from avocado.core import tree
from avocado.version import VERSION

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
        self.args, _ = self.application.parse_known_args(args=default_args)
        if not hasattr(self.args, 'dispatch'):
            self.application.set_defaults(dispatch=self.application.print_help)
        if tree.MULTIPLEX_CAPABLE:
            # Allow overriding multiplex variants by plugins args
            self.args.default_multiplex_tree = tree.TreeNode()

    def finish(self):
        """
        Finish the process of parsing arguments.

        Side effect: set the final value for attribute `args`.
        """
        self.args = self.application.parse_args(namespace=self.args)

    def take_action(self):
        """
        Take some action after parsing arguments.
        """
        return self.args.dispatch(self.args)
