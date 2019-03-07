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

from . import exit_codes
from . import varianter
from . import settings
from .output import BUILTIN_STREAMS, BUILTIN_STREAM_SETS, LOG_UI
from .version import VERSION

PROG = 'avocado'
DESCRIPTION = 'Avocado Test Runner'


class ArgumentParser(argparse.ArgumentParser):

    """
    Class to override argparse functions
    """

    def error(self, message):
        LOG_UI.debug(self.format_help())
        LOG_UI.error("%s: error: %s", self.prog, message)
        if "unrecognized arguments" in message:
            LOG_UI.warning("Perhaps a plugin is missing; run 'avocado"
                           " plugins' to list the installed ones")
        self.exit(exit_codes.AVOCADO_FAIL)

    def _get_option_tuples(self, option_string):
        return []


class FileOrStdoutAction(argparse.Action):

    """
    Controls claiming the right to write to the application standard output
    """

    def __call__(self, parser, namespace, values, option_string=None):
        if values == '-':
            stdout_claimed_by = getattr(namespace, 'stdout_claimed_by', None)
            if stdout_claimed_by is not None:
                msg = ('Options %s %s are trying to use stdout '
                       'simultaneously' % (stdout_claimed_by,
                                           option_string))
                raise argparse.ArgumentError(self, msg)
            else:
                setattr(namespace, 'stdout_claimed_by', option_string)
        setattr(namespace, self.dest, values)


class Parser(object):

    """
    Class to Parse the command line arguments.
    """

    def __init__(self):
        self.args = argparse.Namespace()
        self.subcommands = None
        self.application = ArgumentParser(prog=PROG,
                                          add_help=False,  # see parent parsing
                                          description=DESCRIPTION)
        self.application.add_argument('-v', '--version', action='version',
                                      version='Avocado %s' % VERSION)
        self.application.add_argument('--config', metavar='CONFIG_FILE',
                                      nargs='?',
                                      help='Use custom configuration from a file')
        streams = (['"%s": %s' % _ for _ in BUILTIN_STREAMS.items()] +
                   ['"%s": %s' % _ for _ in BUILTIN_STREAM_SETS.items()])
        streams = "; ".join(streams)
        self.application.add_argument('--show', action="store",
                                      type=lambda value: value.split(","),
                                      metavar="STREAM[:LVL]", nargs='?',
                                      default=['app'], help="List of comma "
                                      "separated builtin logs, or logging "
                                      "streams optionally followed by LEVEL "
                                      "(DEBUG,INFO,...). Builtin streams "
                                      "are: %s. By default: 'app'"
                                      % streams)
        self.application.add_argument('-s', '--silent',
                                      default=argparse.SUPPRESS,
                                      action="store_true",
                                      help=BUILTIN_STREAM_SETS['none'])

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
        # On Python 2, required doesn't make a difference because a
        # subparser is considered an unconsumed positional arguments,
        # and not providing one will error with a "too few arguments"
        # message.  On Python 3, required arguments are used instead.
        # Unfortunately, there's no way to pass this as an option when
        # constructing the sub parsers, but it is possible to set that
        # option afterwards.
        self.subcommands.required = True

        # Allow overriding default params by plugins
        variants = varianter.Varianter(getattr(self.args, "varianter_debug", False))
        self.args.avocado_variants = variants

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
