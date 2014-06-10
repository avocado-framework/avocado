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

import os
import getpass
import json

from avocado.core import exceptions
from avocado.core import data_dir
from avocado.core import status
from avocado.job import TestRunner
from avocado.result import TestResult
from avocado.plugins import plugin
from avocado.utils import virt
from avocado.utils import archive
from avocado.utils.misc import unique


class Test(object):

    """
    Mimics :class:`avocado.test.Test`.
    """

    def __init__(self, name, status, time):
        self.tagged_name = name
        self.status = status
        self.time_elapsed = time


class VMTestRunner(TestRunner):

    def run_test(self, urls):
        """
        Run tests.

        :param urls: a string with test URLs.
        :return: a dictionary with test results.
        """
        avocado_cmd = 'avocado --json run --archive "%s"' % urls
        stdout = self.result.vm.remote.run(avocado_cmd)
        try:
            results = json.loads(stdout)
        except Exception, details:
            raise ValueError('Error loading JSON '
                             '(full output below): %s\n"""\n%s\n"""' %
                             (details, stdout))
        return results

    def run(self, params_list):
        """
        Run one or more tests and report with test result.

        :param params_list: a list of param dicts.

        :return: a list of test failures.
        """
        failures = []
        urls = [x['shortname'] for x in params_list]
        self.result.urls = urls
        self.result.setup()
        results = self.run_test(' '.join(urls))
        remote_log_dir = os.path.dirname(results['debuglog'])
        self.result.start_tests()
        for tst in results['tests']:
            test = Test(name=tst['test'],
                        time=tst['time'],
                        status=tst['status'])
            self.result.start_test(test)
            self.result.check_test(test)
            if not status.mapping[test.status]:
                failures.append(test.tagged_name)
        self.result.end_tests()
        local_log_dir = os.path.dirname(self.result.stream.debuglog)
        zip_filename = remote_log_dir + '.zip'
        zip_path_filename = os.path.join(local_log_dir, os.path.basename(zip_filename))
        self.result.vm.remote.receive_files(local_log_dir, zip_filename)
        archive.uncompress_zip(zip_path_filename,
                               local_log_dir)
        os.remove(zip_path_filename)
        self.result.tear_down()
        return failures


class VMTestResult(TestResult):

    """
    Virtual Machine Test Result class.
    """

    def __init__(self, stream, args):
        """
        Creates an instance of VMTestResult.

        :param stream: an instance of :class:`avocado.core.output.OutputManager`.
        :param args: an instance of :class:`argparse.Namespace`.
        """
        TestResult.__init__(self, stream, args)
        self.test_dir = data_dir.get_test_dir()
        self.remote_test_dir = '~/avocado/tests'

    def _copy_tests(self):
        self.vm.remote.makedir(self.remote_test_dir)
        uniq_urls = unique(self.urls)
        for url in uniq_urls:
            test_path = os.path.join(self.test_dir, url)
            self.vm.remote.send_files(test_path, self.remote_test_dir)

    def setup(self):
        self.urls = self.args.url.split()
        if self.args.vm_domain is None:
            e_msg = ('Please set Virtual Machine Domain with option '
                     '--vm-domain.')
            self.stream.error(e_msg)
            raise exceptions.TestSetupFail(e_msg)
        if self.args.vm_hostname is None:
            e_msg = ('Please set Virtual Machine hostname with option '
                     '--vm-hostname.')
            self.stream.error(e_msg)
            raise exceptions.TestSetupFail(e_msg)
        self.stream.log_header("REMOTE TESTS: Virtual Machine Domain '%s'" %
                               self.args.vm_domain)
        self.stream.log_header("REMOTE TESTS: Host login '%s@%s'" %
                               (self.args.vm_username, self.args.vm_hostname))
        self.vm = virt.vm_connect(self.args.vm_domain,
                                  self.args.vm_hypervisor_uri)
        if self.vm is None:
            self.stream.error("Could not connect to VM '%s'" % self.args.vm_domain)
            raise exceptions.TestSetupFail()
        if self.vm.start() is False:
            self.stream.error("Could not start VM '%s'" % self.args.vm_domain)
            raise exceptions.TestSetupFail()
        assert self.vm.domain.isActive() is not False
        if self.args.vm_cleanup is True:
            self.vm.create_snapshot()
            if self.vm.snapshot is None:
                self.stream.error("Could not create snapshot on VM '%s'" % self.args.vm_domain)
                raise exceptions.TestSetupFail()
        try:
            self.vm.setup_login(self.args.vm_hostname,
                                self.args.vm_username,
                                self.args.vm_password)
        except Exception as err:
            self.stream.error("Could not login on VM '%s': %s" % (self.args.vm_hostname,
                                                                  err))
            self.tear_down()
            raise exceptions.TestSetupFail()
        if self.vm.logged is False or self.vm.remote.uptime() is '':
            self.stream.error("Could not login on VM '%s'" % self.args.vm_hostname)
            self.tear_down()
            raise exceptions.TestSetupFail()
        self._copy_tests()

    def tear_down(self):
        if self.args.vm_cleanup is True and self.vm.snapshot is not None:
            self.vm.restore_snapshot()

    def start_tests(self):
        """
        Called once before any tests are executed.
        """
        TestResult.start_tests(self)
        self.stream.log_header("TOTAL TESTS: %s" % self.tests_total)

    def end_tests(self):
        """
        Called once after all tests are executed.
        """
        self.stream.log_header("TOTAL PASSED: %d" % len(self.passed))
        self.stream.log_header("TOTAL ERROR: %d" % len(self.errors))
        self.stream.log_header("TOTAL FAILED: %d" % len(self.failed))
        self.stream.log_header("TOTAL SKIPPED: %d" % len(self.skipped))
        self.stream.log_header("TOTAL WARNED: %d" % len(self.warned))
        self.stream.log_header("ELAPSED TIME: %.2f s" % self.total_time)
        self.stream.log_header("DEBUG LOG: %s" % self.stream.debuglog)

    def start_test(self, test):
        """
        Called when the given test is about to run.

        :param test: :class:`avocado.test.Test` instance.
        """
        self.test_label = '(%s/%s) %s: ' % (self.tests_run,
                                            self.tests_total,
                                            test.tagged_name)

        self.stream.info(msg=self.test_label, skip_newline=True)

    def end_test(self, test):
        """
        Called when the given test has been run.

        :param test: :class:`avocado.test.Test` instance.
        """
        TestResult.end_test(self, test)

    def add_pass(self, test):
        """
        Called when a test succeeded.

        :param test: :class:`avocado.test.Test` instance.
        """
        TestResult.add_pass(self, test)
        self.stream.log_pass(test.time_elapsed)

    def add_error(self, test):
        """
        Called when a test had a setup error.

        :param test: :class:`avocado.test.Test` instance.
        """
        TestResult.add_error(self, test)
        self.stream.log_error(test.time_elapsed)

    def add_fail(self, test):
        """
        Called when a test fails.

        :param test: :class:`avocado.test.Test` instance.
        """
        TestResult.add_fail(self, test)
        self.stream.log_fail(test.time_elapsed)

    def add_skip(self, test):
        """
        Called when a test is skipped.

        :param test: :class:`avocado.test.Test` instance.
        """
        TestResult.add_skip(self, test)
        self.stream.log_skip(test.time_elapsed)

    def add_warn(self, test):
        """
        Called when a test had a warning.

        :param test: :class:`avocado.test.Test` instance.
        """
        TestResult.add_warn(self, test)
        self.stream.log_warn(test.time_elapsed)


class RunVM(plugin.Plugin):

    """
    Run tests on Virtual Machine plugin.
    """

    name = 'run_vm'
    enabled = True

    def configure(self, app_parser, cmd_parser):
        if virt.virt_capable is False:
            self.enabled = False
            return
        username = getpass.getuser()
        self.parser = app_parser
        app_parser.add_argument('--vm', action='store_true', default=False,
                                help='Run tests on Virtual Machine')
        app_parser.add_argument('--vm-hypervisor-uri', dest='vm_hypervisor_uri',
                                default='qemu:///system',
                                help='Specify hypervisor URI driver connection')
        app_parser.add_argument('--vm-domain', dest='vm_domain',
                                help='Specify domain name (Virtual Machine name)')
        app_parser.add_argument('--vm-hostname', dest='vm_hostname',
                                help='Specify VM hostname to login')
        app_parser.add_argument('--vm-username', dest='vm_username',
                                default=username,
                                help='Specify the username to login on VM')
        app_parser.add_argument('--vm-password', dest='vm_password',
                                default=None,
                                help='Specify the password to login on VM')
        app_parser.add_argument('--vm-cleanup', dest='vm_cleanup', action='store_true',
                                default=False,
                                help='Restore VM to a previous state, before running the tests')
        self.configured = True

    def activate(self, app_args):
        if app_args.vm:
            self.parser.set_defaults(vm_result=VMTestResult,
                                     test_runner=VMTestRunner)
