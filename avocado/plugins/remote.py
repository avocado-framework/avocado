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

from avocado.plugins import plugin
from avocado.remote import RemoteTestResult, RemoteTestRunner
from avocado.utils import remote


class RunRemote(plugin.Plugin):

    """
    Run tests on a remote machine
    """

    name = 'run_remote'
    enabled = True
    remote_parser = None

    def configure(self, parser):
        if remote.REMOTE_CAPABLE is False:
            self.enabled = False
            return
        username = getpass.getuser()
        msg = 'run on a remote machine arguments'
        self.remote_parser = parser.runner.add_argument_group(msg)
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
                                        default=username,
                                        help='Specify the username to login on'
                                        ' remote machine. Current: '
                                        '%(default)s')
        self.remote_parser.add_argument('--remote-password',
                                        dest='remote_password', default=None,
                                        help='Specify the password to login on'
                                        ' remote machine')
        self.remote_parser.add_argument('--remote-no-copy',
                                        dest='remote_no_copy',
                                        action='store_true',
                                        help="Don't copy tests and use the "
                                        "exact uri on guest machine.")
        self.configured = True

    @staticmethod
    def _check_required_args(app_args, enable_arg, required_args):
        """
        :return: True when enable_arg enabled and all required args are set
        :raise sys.exit: When missing required argument.
        """
        if (not hasattr(app_args, enable_arg) or
                not getattr(app_args, enable_arg)):
            return False
        missing = []
        for arg in required_args:
            if not getattr(app_args, arg):
                missing.append(arg)
        if missing:
            from avocado.core import output, exit_codes
            import sys
            view = output.View(app_args=app_args)
            e_msg = ('Use of %s requires %s arguments to be set. Please set %s'
                     '.' % (enable_arg, ', '.join(required_args),
                            ', '.join(missing)))

            view.notify(event='error', msg=e_msg)
            return sys.exit(exit_codes.AVOCADO_FAIL)
        return True

    def activate(self, app_args):
        if self._check_required_args(app_args, 'remote_hostname',
                                     ('remote_hostname',)):
            self.remote_parser.set_defaults(remote_result=RemoteTestResult,
                                            test_runner=RemoteTestRunner)
