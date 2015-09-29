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

from .. import remoter
from .. import data_dir
from .. import exceptions
from ..result import HumanTestResult
from ...core import virt


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

    def copy_files(self):
        """
        Gather test directories and copy them recursively to
        $remote_test_dir + $test_absolute_path.
        :note: Default tests execution is translated into absolute paths too
        """
        if self.args.remote_no_copy:    # Leave everything as is
            return

        # TODO: Use `avocado.core.loader.TestLoader` instead
        self.remote.makedir(self.remote_test_dir)
        paths = set()
        for i in xrange(len(self.urls)):
            url = self.urls[i]
            if not os.path.exists(url):     # use test_dir path + py
                url = os.path.join(data_dir.get_test_dir(), '%s.py' % url)
            url = os.path.abspath(url)  # always use abspath; avoid clashes
            # modify url to remote_path + abspath
            paths.add(url)
            self.urls[i] = self.remote_test_dir + url
        for path in sorted(paths):
            rpath = self.remote_test_dir + path
            self.remote.makedir(os.path.dirname(rpath))
            self.remote.send_files(path, os.path.dirname(rpath))
            test_data = path + '.data'
            if os.path.isdir(test_data):
                self.remote.send_files(test_data, os.path.dirname(rpath))
        for mux_file in getattr(self.args, 'multiplex_files') or []:
            rpath = os.path.join(self.remote_test_dir, mux_file)
            self.remote.makedir(os.path.dirname(rpath))
            self.remote.send_files(mux_file, rpath)

    def setup(self):
        """ Setup remote environment and copy test directories """
        self.stream.notify(event='message',
                           msg=("LOGIN      : %s@%s:%d"
                                % (self.args.remote_username,
                                   self.args.remote_hostname,
                                   self.args.remote_port)))
        self.remote = remoter.Remote(self.args.remote_hostname,
                                     self.args.remote_username,
                                     self.args.remote_password,
                                     self.args.remote_port)

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
            raise exceptions.JobError(e_msg)
        if self.args.vm_hostname is None:
            e_msg = ('Please set Virtual Machine hostname with option '
                     '--vm-hostname.')
            self.stream.notify(event='error', msg=e_msg)
            raise exceptions.JobError(e_msg)
        self.stream.notify(event='message', msg="DOMAIN     : %s"
                           % self.args.vm_domain)
        self.vm = virt.vm_connect(self.args.vm_domain,
                                  self.args.vm_hypervisor_uri)
        if self.vm is None:
            e_msg = "Could not connect to VM '%s'" % self.args.vm_domain
            raise exceptions.JobError(e_msg)
        if self.vm.start() is False:
            e_msg = "Could not start VM '%s'" % self.args.vm_domain
            raise exceptions.JobError(e_msg)
        assert self.vm.domain.isActive() is not False
        if self.args.vm_cleanup is True:
            self.vm.create_snapshot()
            if self.vm.snapshot is None:
                e_msg = ("Could not create snapshot on VM '%s'" %
                         self.args.vm_domain)
                raise exceptions.JobError(e_msg)
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
        if self.args.vm_cleanup is True:
            self.vm.stop()
            if self.vm.snapshot is not None:
                self.vm.restore_snapshot()
