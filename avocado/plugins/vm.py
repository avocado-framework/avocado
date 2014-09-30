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
from avocado.core import status
from avocado.core import data_dir
from avocado.job import TestRunner
from avocado.result import TestResult
from avocado.plugins import plugin
from avocado.utils import virt
from avocado.utils import archive


class Test(object):

    """
    Mimics :class:`avocado.test.Test`.
    """

    def __init__(self, name, status, time):
        note = "Not supported yet"
        self.name = name
        self.tagged_name = name
        self.status = status
        self.time_elapsed = time
        self.fail_class = note
        self.traceback = note
        self.text_output = note
        self.fail_reason = note
        self.whiteboard = ''
        self.job_unique_id = ''

    def get_state(self):
        """
        Serialize selected attributes representing the test state

        :returns: a dictionary containing relevant test state data
        :rtype: dict
        """
        d = self.__dict__
        d['class_name'] = self.__class__.__name__
        return d


class VMTestRunner(TestRunner):
    remote_test_dir = '~/avocado/tests'

    def run_test(self, urls):
        """
        Run tests.

        :param urls: a string with test URLs.
        :return: a dictionary with test results.
        """
        urls = urls.split()
        avocado_cmd = ('cd %s; avocado run --force-job-id %s --json - --archive %s' %
                       (self.remote_test_dir, self.result.stream.job_unique_id, " ".join(urls)))
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
        urls = [x['id'] for x in params_list]
        self.result.urls = urls
        self.result.setup()
        results = self.run_test(' '.join(urls))
        remote_log_dir = os.path.dirname(results['debuglog'])
        self.result.start_tests()
        for tst in results['tests']:
            test = Test(name=tst['test'],
                        time=tst['time'],
                        status=tst['status'])
            state = test.get_state()
            self.result.start_test(state)
            self.result.check_test(state)
            if not status.mapping[state['status']]:
                failures.append(state['tagged_name'])
        self.result.end_tests()
        local_log_dir = os.path.dirname(self.result.stream.debuglog)
        zip_filename = remote_log_dir + '.zip'
        zip_path_filename = os.path.join(local_log_dir, os.path.basename(zip_filename))
        self.result.vm.remote.receive_files(local_log_dir, zip_filename)
        archive.uncompress(zip_path_filename, local_log_dir)
        os.remove(zip_path_filename)
        self.result.tear_down()
        return failures


class VMTestResult(TestResult):

    """
    Virtual Machine Test Result class.
    """

    command_line_arg_name = '--vm'

    def __init__(self, stream, args):
        """
        Creates an instance of VMTestResult.

        :param stream: an instance of :class:`avocado.core.output.View`.
        :param args: an instance of :class:`argparse.Namespace`.
        """
        TestResult.__init__(self, stream, args)
        self.test_dir = os.getcwd()
        self.remote_test_dir = '~/avocado/tests'
        self.output = '-'

    def _copy_tests(self):
        self.vm.remote.makedir(self.remote_test_dir)
        uniq_urls = list(set(self.urls))
        for url in uniq_urls:
            parent_dir = url.split(os.path.sep)[0]
            if os.path.isdir(parent_dir):
                test_path = os.path.abspath(parent_dir)
            else:
                test_path = os.path.join(data_dir.get_test_dir(), "%s*" % url)
            self.vm.remote.send_files(test_path, self.remote_test_dir)

    def setup(self):
        self.urls = self.args.url
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
        self.stream.notify(event='message', msg="VM LOGIN  : %s@%s" % (self.args.vm_username, self.args.vm_hostname))
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
            self.vm.setup_login(self.args.vm_hostname,
                                self.args.vm_username,
                                self.args.vm_password)
        except Exception as err:
            self.stream.notify(event='error', msg="Could not login on VM '%s': %s" % (self.args.vm_hostname, err))
            self.tear_down()
            raise exceptions.TestSetupFail()
        if self.vm.logged is False or self.vm.remote.uptime() is '':
            self.stream.notify(event='error', msg="Could not login on VM '%s'" % self.args.vm_hostname)
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
        self.stream.notify(event='message', msg="JOB ID    : %s" % self.stream.job_unique_id)
        self.stream.notify(event='message', msg="JOB LOG   : %s" % self.stream.logfile)
        self.stream.notify(event='message', msg="TESTS     : %s" % self.tests_total)
        self.stream.set_tests_info({'tests_total': self.tests_total})

    def end_tests(self):
        """
        Called once after all tests are executed.
        """
        self.stream.notify(event='message', msg="PASS      : %d" % len(self.passed))
        self.stream.notify(event='message', msg="ERROR     : %d" % len(self.errors))
        self.stream.notify(event='message', msg="NOT FOUND : %d" % len(self.not_found))
        self.stream.notify(event='message', msg="FAIL      : %d" % len(self.failed))
        self.stream.notify(event='message', msg="SKIP      : %d" % len(self.skipped))
        self.stream.notify(event='message', msg="WARN      : %d" % len(self.warned))
        self.stream.notify(event='message', msg="TIME      : %.2f s" % self.total_time)

    def start_test(self, test):
        """
        Called when the given test is about to run.

        :param test: :class:`avocado.test.Test` instance.
        """
        self.stream.add_test(test)

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
        self.stream.set_test_status(status='PASS', state=test)

    def add_error(self, test):
        """
        Called when a test had a setup error.

        :param test: :class:`avocado.test.Test` instance.
        """
        TestResult.add_error(self, test)
        self.stream.set_test_status(status='ERROR', state=test)

    def add_not_found(self, test):
        """
        Called when a test had a setup error.

        :param test: :class:`avocado.test.Test` instance.
        """
        TestResult.add_not_found(self, test)
        self.stream.set_test_status(status='NOT_FOUND', state=test)

    def add_fail(self, test):
        """
        Called when a test fails.

        :param test: :class:`avocado.test.Test` instance.
        """
        TestResult.add_fail(self, test)
        self.stream.set_test_status(status='FAIL', state=test)

    def add_skip(self, test):
        """
        Called when a test is skipped.

        :param test: :class:`avocado.test.Test` instance.
        """
        TestResult.add_skip(self, test)
        self.stream.set_test_status(status='SKIP', state=test)

    def add_warn(self, test):
        """
        Called when a test had a warning.

        :param test: :class:`avocado.test.Test` instance.
        """
        TestResult.add_warn(self, test)
        self.stream.set_test_status(status='WARN', state=test)


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

        self.vm_parser.add_argument('--vm', action='store_true', default=False,
                                    help=('Run tests on a Virtual Machine '
                                          '(Libvirt Domain)'))
        self.vm_parser.add_argument('--vm-hypervisor-uri',
                                    dest='vm_hypervisor_uri',
                                    default=default_hypervisor_uri,
                                    help=('Specify hypervisor URI driver '
                                          'connection. Default: %s' %
                                          default_hypervisor_uri))
        self.vm_parser.add_argument('--vm-domain', dest='vm_domain',
                                    help=('Specify Libvirt Domain Name'))
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

    def activate(self, app_args):
        try:
            if app_args.vm:
                self.vm_parser.set_defaults(vm_result=VMTestResult,
                                            test_runner=VMTestRunner)
        except AttributeError:
            pass
