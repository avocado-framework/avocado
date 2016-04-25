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
# Copyright: Red Hat Inc. 2014-2015
# Author: Ruda Moura <rmoura@redhat.com>

"""Run tests on a remote machine."""

import getpass
import logging
import sys

from avocado.core import exit_codes
from avocado.core import remoter
from avocado.core.remote import RemoteTestResult
from avocado.core.remote import RemoteTestRunner
from avocado.core.result import register_test_result_class

from .base import CLI


class Remote(CLI):

    """
    Run tests on a remote machine
    """

    name = 'remote'
    description = "Remote machine options for 'run' subcommand"

    def configure(self, parser):
        if remoter.REMOTE_CAPABLE is False:
            return

        run_subcommand_parser = parser.subcommands.choices.get('run', None)
        if run_subcommand_parser is None:
            return

        msg = 'test execution on a remote machine'
        self.remote_parser = run_subcommand_parser.add_argument_group(msg)
        self.remote_parser.add_argument('--remote-hostname',
                                        dest='remote_hostname', default=None,
                                        help='Specify the hostname to login on'
                                        ' remote machine')
        self.remote_parser.add_argument('--remote-port', dest='remote_port',
                                        default=22, type=int, help='Specify '
                                        'the port number to login on remote '
                                        'machine. Current: 22')
        self.remote_parser.add_argument('--remote-username',
                                        dest='remote_username',
                                        default=getpass.getuser(),
                                        help='Specify the username to login on'
                                        ' remote machine. Current: '
                                        '%(default)s')
        self.remote_parser.add_argument('--remote-password',
                                        dest='remote_password', default=None,
                                        help='Specify the password to login on'
                                        ' remote machine')
        self.remote_parser.add_argument('--remote-key-file',
                                        dest='remote_key_file', default=None,
                                        help='Specify an identity file with '
                                        'a private key instead of a password '
                                        '(Example: .pem files from Amazon EC2)')
        self.remote_parser.add_argument('--remote-no-copy',
                                        dest='remote_no_copy',
                                        action='store_true',
                                        help="Don't copy tests and use the "
                                        "exact uri on guest machine.")
        self.remote_parser.add_argument('--remote-timeout', metavar='SECONDS',
                                        help=("Amount of time (in seconds) to "
                                              "wait for a successful connection"
                                              " to the remote machine. Defaults"
                                              " to %(default)s seconds."),
                                        default=60, type=int)
        self.configured = True

    @staticmethod
    def _check_required_args(args, enable_arg, required_args):
        """
        :return: True when enable_arg enabled and all required args are set
        :raise sys.exit: When missing required argument.
        """
        if (not hasattr(args, enable_arg) or
                not getattr(args, enable_arg)):
            return False
        missing = []
        for arg in required_args:
            if not getattr(args, arg):
                missing.append(arg)
        if missing:
            log = logging.getLogger("avocado.app")
            log.error("Use of %s requires %s arguments to be set. Please set "
                      "%s.", enable_arg, ', '.join(required_args),
                      ', '.join(missing))

            return sys.exit(exit_codes.AVOCADO_FAIL)
        return True

    def run(self, args):
        if self._check_required_args(args, 'remote_hostname',
                                     ('remote_hostname',)):
            register_test_result_class(args, RemoteTestResult)
            args.test_runner = RemoteTestRunner
