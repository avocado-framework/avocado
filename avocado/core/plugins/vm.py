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

from . import plugin
from ..remote import VMTestResult
from ..remote import RemoteTestRunner
from avocado.utils import virt


class RunVM(plugin.Plugin):

    """
    Run tests on a Virtual Machine
    """

    name = 'run_vm'
    enabled = True
    vm_parser = None

    def configure(self, parser):
        if virt.VIRT_CAPABLE is False:
            self.enabled = False
            return
        username = getpass.getuser()
        default_hypervisor_uri = 'qemu:///system'
        self.vm_parser = parser.runner.add_argument_group('run on a libvirt '
                                                          'domain arguments')

        self.vm_parser.add_argument('--vm-domain', dest='vm_domain',
                                    help=('Specify Libvirt Domain Name'))
        self.vm_parser.add_argument('--vm-hypervisor-uri',
                                    dest='vm_hypervisor_uri',
                                    default=default_hypervisor_uri,
                                    help=('Specify hypervisor URI driver '
                                          'connection. Current: %s' %
                                          default_hypervisor_uri))
        self.vm_parser.add_argument('--vm-hostname', dest='vm_hostname',
                                    help='Specify VM hostname to login')
        self.vm_parser.add_argument('--vm-username', dest='vm_username',
                                    default=username,
                                    help='Specify the username to login on VM')
        self.vm_parser.add_argument('--vm-password', dest='vm_password',
                                    default=None,
                                    help='Specify the password to login on VM')
        self.vm_parser.add_argument('--vm-cleanup', dest='vm_cleanup',
                                    action='store_true',
                                    default=False,
                                    help='Restore VM to a previous state, '
                                    'before running tests')
        self.vm_parser.add_argument('--vm-no-copy',
                                    dest='vm_no_copy',
                                    action='store_true',
                                    help="Don't copy tests and use the "
                                    "exact uri on VM machine.")
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
        if self._check_required_args(app_args, 'vm_domain',
                                     ('vm_domain', 'vm_hostname')):
            self.vm_parser.set_defaults(remote_result=VMTestResult,
                                        test_runner=RemoteTestRunner)
