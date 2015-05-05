# This rogram is free software; you can redistribute it and/or modify
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

"""Remote test results."""

import os

from avocado.core import exceptions
from avocado.core import data_dir
from avocado.core.result import HumanTestResult
from avocado.utils import remote
from avocado.utils import virt


class RemoteTestResult(HumanTestResult):

    """
    Remote Machine Test Result class.
    """

    def __init__(self, stream, args):
        """
        Creates an instance of RemoteTestResult.

        :param stream: an instance of :class:`avocado.core.output.View`.
        :param args: an instance of :class:`argparse.Namespace`.
        """
        HumanTestResult.__init__(self, stream, args)
        self.test_dir = os.getcwd()
        self.remote_test_dir = '~/avocado/tests'
        self.urls = self.args.url
        self.remote = None      # Remote runner initialized during setup
        self.output = '-'
        self.command_line_arg_name = '--remote-hostname'

    def _copy_tests(self):
        """
        Gather test directories and copy them recursively to
        $remote_test_dir + $test_absolute_path.
        :note: Default tests execution is translated into absolute paths too
        """
        # TODO: Use `avocado.core.loader.TestLoader` instead
        self.remote.makedir(self.remote_test_dir)
        if self.args.remote_no_copy:    # Leave everything as is
            return
        paths = set()
        for i in xrange(len(self.urls)):
            url = self.urls[i]
            if not os.path.exists(url):     # use test_dir path + py
                url = os.path.join(data_dir.get_test_dir(), '%s.py' % url)
            url = os.path.abspath(url)  # always use abspath; avoid clashes
            # modify url to remote_path + abspath
            paths.add(os.path.dirname(url))
            self.urls[i] = self.remote_test_dir + url
        previous = ' NOT ABSOLUTE PATH'
        for path in sorted(paths):
            if os.path.commonprefix((path, previous)) == previous:
                continue    # already copied
            rpath = self.remote_test_dir + path
            self.remote.makedir(rpath)
            self.remote.send_files(path, os.path.dirname(rpath))
            previous = path

    def setup(self):
        """ Setup remote environment and copy test directories """
        self.stream.notify(event='message',
                           msg=("LOGIN      : %s@%s:%d"
                                % (self.args.remote_username,
                                   self.args.remote_hostname,
                                   self.args.remote_port)))
        self.remote = remote.Remote(self.args.remote_hostname,
                                    self.args.remote_username,
                                    self.args.remote_password,
                                    self.args.remote_port,
                                    quiet=True)
        self._copy_tests()

    def tear_down(self):
        """ Cleanup after test execution """
        pass


class VMTestResult(RemoteTestResult):

    """
    Virtual Machine Test Result class.
    """

    def __init__(self, stream, args):
        super(VMTestResult, self).__init__(stream, args)
        self.vm = None
        self.command_line_arg_name = '--vm-domain'

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
        self.stream.notify(event='message', msg="DOMAIN     : %s"
                           % self.args.vm_domain)
        self.vm = virt.vm_connect(self.args.vm_domain,
                                  self.args.vm_hypervisor_uri)
        if self.vm is None:
            self.stream.notify(event='error',
                               msg="Could not connect to VM '%s'"
                               % self.args.vm_domain)
            raise exceptions.TestSetupFail()
        if self.vm.start() is False:
            self.stream.notify(event='error', msg="Could not start VM '%s'"
                               % self.args.vm_domain)
            raise exceptions.TestSetupFail()
        assert self.vm.domain.isActive() is not False
        if self.args.vm_cleanup is True:
            self.vm.create_snapshot()
            if self.vm.snapshot is None:
                self.stream.notify(event='error', msg="Could not create "
                                   "snapshot on VM '%s'" % self.args.vm_domain)
                raise exceptions.TestSetupFail()
        try:
            # Finish remote setup and copy the tests
            self.args.remote_hostname = self.args.vm_hostname
            self.args.remote_username = self.args.vm_username
            self.args.remote_password = self.args.vm_password
            self.args.remote_no_copy = self.args.vm_no_copy
            super(VMTestResult, self).setup()
        except Exception:
            self.tear_down()
            raise

    def tear_down(self):
        super(VMTestResult, self).tear_down()
        if self.args.vm_cleanup is True and self.vm.snapshot is not None:
            self.vm.restore_snapshot()
