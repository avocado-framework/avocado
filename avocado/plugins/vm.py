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
# Copyright: Red Hat Inc. 2014
# Author: Ruda Moura <rmoura@redhat.com>

"""Run tests on Virtual Machine."""

import getpass

from avocado.core import exceptions
from avocado.plugins.remote import RemoteTestRunner
from avocado.plugins.remote import RemoteTestResult
from avocado.plugins import plugin
from avocado.utils import virt


class VMTestResult(RemoteTestResult):

    """
    Virtual Machine Test Result class.
    """

    def __init__(self, stream, args):
        super(VMTestResult, self).__init__(stream, args)
        self.vm = None

    def setup(self):
        # Super called after VM is found and initialized
        if self.args.vm_domain is None:
            e_msg = ('Please set Virtual Machine Domain with option '
                     '--vm-domain.')
            self.stream.notify(event='error', msg=e_msg)
            raise exceptions.TestSetupFail(e_msg)
        if self.args.vm_hostname is None:
            e_msg = ('Please set Virtual Machine hostname with option '
                     '--vm-hostname.')
            self.stream.notify(event='error', msg=e_msg)
            raise exceptions.TestSetupFail(e_msg)
        self.stream.notify(event='message', msg="VM DOMAIN : %s" % self.args.vm_domain)
        self.vm = virt.vm_connect(self.args.vm_domain,
                                  self.args.vm_hypervisor_uri)
        if self.vm is None:
            self.stream.notify(event='error', msg="Could not connect to VM '%s'" % self.args.vm_domain)
            raise exceptions.TestSetupFail()
        if self.vm.start() is False:
            self.stream.notify(event='error', msg="Could not start VM '%s'" % self.args.vm_domain)
            raise exceptions.TestSetupFail()
        assert self.vm.domain.isActive() is not False
        if self.args.vm_cleanup is True:
            self.vm.create_snapshot()
            if self.vm.snapshot is None:
                self.stream.notify(event='error', msg="Could not create snapshot on VM '%s'" % self.args.vm_domain)
                raise exceptions.TestSetupFail()
        try:
            # Finish remote setup and copy the tests
            self.args.remote_hostname = self.args.vm_hostname
            self.args.remote_username = self.args.vm_username
            self.args.remote_password = self.args.vm_password
            super(VMTestResult, self).setup()
        except Exception:
            self.tear_down()
            raise

    def tear_down(self):
        super(VMTestResult, self).tear_down()
        if self.args.vm_cleanup is True and self.vm.snapshot is not None:
            self.vm.restore_snapshot()


class RunVM(plugin.Plugin):

    """
    Run tests on a Virtual Machine
    """

    name = 'run_vm'
    enabled = True

    def configure(self, parser):
        if virt.virt_capable is False:
            self.enabled = False
            return
        username = getpass.getuser()
        default_hypervisor_uri = 'qemu:///system'
        self.vm_parser = parser.runner.add_argument_group('run on a libvirt domain '
                                                          'arguments')

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
                                    help=('Restore VM to a previous state, before '
                                          'running tests'))
        self.configured = True

    @staticmethod
    def _check_required_args(app_args, enable_arg, required_args):
        """
        :return: True when enable_arg enabled and all required args are set
        :raise sys.exit: When missing required argument.
        """
        if not getattr(app_args, enable_arg):
            return False
        missing = []
        for arg in required_args:
            if not getattr(app_args, arg):
                missing.append(arg)
        if missing:
            from avocado.core import output, exit_codes
            import sys
            view = output.View(app_args=app_args, use_paginator=True)
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
