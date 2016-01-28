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

"""Run tests on Virtual Machine."""

import getpass
import logging
import sys

from avocado.core import exit_codes
from avocado.core import virt
from avocado.core.remote import VMTestResult
from avocado.core.remote import VMTestRunner
from avocado.core.result import register_test_result_class

from .base import CLI


class VM(CLI):

    """
    Run tests on a Virtual Machine
    """

    name = 'vm'
    description = "Virtual Machine options for 'run' subcommand"

    def configure(self, parser):
        if virt.VIRT_CAPABLE is False:
            return

        run_subcommand_parser = parser.subcommands.choices.get('run', None)
        if run_subcommand_parser is None:
            return

        msg = 'test execution on a Virtual Machine'
        self.vm_parser = run_subcommand_parser.add_argument_group(msg)
        self.vm_parser.add_argument('--vm-domain',
                                    help=('Specify Libvirt Domain Name'))
        self.vm_parser.add_argument('--vm-hypervisor-uri',
                                    default='qemu:///system',
                                    help=('Specify hypervisor URI driver '
                                          'connection. Current: %(default)s'))
        self.vm_parser.add_argument('--vm-hostname', default=None,
                                    help=('Specify VM hostname to login. By '
                                          'default Avocado attempts to '
                                          'automatically find the VM IP '
                                          'address.'))
        self.vm_parser.add_argument('--vm-port', dest='vm_port',
                                    default=22, type=int, help='Specify '
                                    'the port number to login on VM. '
                                    'Current: 22')
        self.vm_parser.add_argument('--vm-username', default=getpass.getuser(),
                                    help='Specify the username to login on VM')
        self.vm_parser.add_argument('--vm-password',
                                    default=None,
                                    help='Specify the password to login on VM')
        self.vm_parser.add_argument('--vm-key-file',
                                    dest='vm_key_file', default=None,
                                    help='Specify an identity file with '
                                    'a private key instead of a password '
                                    '(Example: .pem files from Amazon EC2)')
        self.vm_parser.add_argument('--vm-cleanup',
                                    action='store_true', default=False,
                                    help='Restore VM to a previous state, '
                                    'before running tests')
        self.vm_parser.add_argument('--vm-no-copy', action='store_true',
                                    help="Don't copy tests and use the "
                                    "exact uri on VM machine.")
        self.vm_parser.add_argument('--vm-timeout', metavar='SECONDS',
                                    help=("Amount of time (in seconds) to "
                                          "wait for a successful connection"
                                          " to the virtual machine. Defaults"
                                          " to %(default)s seconds."),
                                    default=120, type=int)
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
        if self._check_required_args(args, 'vm_domain', ('vm_domain',)):
            register_test_result_class(args, VMTestResult)
            args.test_runner = VMTestRunner
