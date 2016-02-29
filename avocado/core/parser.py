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
import sys

from . import exit_codes
from . import tree
from . import settings
from .version import VERSION

PROG = 'avocado'
DESCRIPTION = 'Avocado Test Runner'


def log_type(value):
    value = value.split(',')
    if '?' in value:
        msg = ("Enable stdout/stderr console streams. Special values are:\n"
               " app - application output\n"
               " test - test output\n"
               " debug - tracebacks and other debugging info\n"
               " remote - fabric/paramiko debug\n"
               " early - early logging of other streams (very verbose)\n"
               " all - all of the above\n"
               " none - disable console logging\n"
               " ? - this help\n"
               "Additionally you can specify any (non-colliding) stream, "
               "eg. 'my.stream'.\n")
        sys.stderr.write(msg)
        sys.exit(0)

    if 'all' in value:
        return ["app", "test", "debug", "remote", "early"]
    elif 'none' in value:
        return []
    else:
        return value


class ArgumentParser(argparse.ArgumentParser):

    """
    Class to override argparse functions
    """

    def error(self, message):
        msg = '%s: error: %s\n' % (self.prog, message)
        self.print_help(sys.stderr)
        self.exit(exit_codes.AVOCADO_FAIL, msg)


class Parser(object):

    """
    Class to Parse the command line arguments.
    """

    def __init__(self):
        self.args = None
        self.subcommands = None
        self.application = ArgumentParser(prog=PROG,
                                          add_help=False,  # see parent parsing
                                          description=DESCRIPTION)
        self.application.add_argument('-v', '--version', action='version',
                                      version='Avocado %s' % VERSION)
        self.application.add_argument('--config', metavar='CONFIG_FILE',
                                      help='Use custom configuration from a file')
        self.application.add_argument('--show', action="store",
                                      type=log_type,
                                      metavar="STREAM[:LVL]",
                                      default=['app'], help="Comma separated "
                                      "list of logging streams to be enabled "
                                      "optionally followed by LEVEL (INFO,"
                                      "DEBUG,WARNING,CRITICAL). "
                                      "Use '?' to get info about streams; "
                                      "By default 'app:DEBUG'")
        self.application.add_argument('-s', '--silent',
                                      default=argparse.SUPPRESS,
                                      action="store_true",
                                      help='Silence stdout')

    def start(self):
        """
        Start to parsing arguments.

        At the end of this method, the support for subparsers is activated.
        Side effect: update attribute `args` (the namespace).
        """
        self.args, _ = self.application.parse_known_args()

        # Load settings from file, if user provides one
        if self.args.config is not None:
            settings.settings.process_config_path(self.args.config)

        # Use parent parsing to avoid breaking the output of --help option
        self.application = ArgumentParser(prog=PROG,
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
        self.args, extra = self.application.parse_known_args(namespace=self.args)
        if extra:
            msg = 'unrecognized arguments: %s' % ' '.join(extra)
            for sub in self.application._subparsers._actions:
                if sub.dest == 'subcommand':
                    sub.choices[self.args.subcommand].error(msg)

            self.application.error(msg)
