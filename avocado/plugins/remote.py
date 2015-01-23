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

"""Run tests on a remote machine."""

import os
import getpass
import json

from avocado.core import exceptions
from avocado.core import status
from avocado.core import data_dir
from avocado.runner import TestRunner
from avocado.result import TestResult
from avocado.plugins import plugin
from avocado.utils import remote
from avocado.utils import archive
from avocado.test import RemoteTest


class RemoteTestRunner(TestRunner):
    remote_test_dir = '~/avocado/tests'

    def run_test(self, urls):
        """
        Run tests.

        :param urls: a string with test URLs.
        :return: a dictionary with test results.
        """
        avocado_cmd = ('cd %s; avocado run --force-job-id %s --json - --archive %s' %
                       (self.remote_test_dir, self.result.stream.job_unique_id, " ".join(urls)))
        result = self.result.remote.run(avocado_cmd, ignore_status=True)
        for json_output in result.stdout.splitlines():
            # We expect dictionary:
            if json_output.startswith('{') and json_output.endswith('}'):
                try:
                    return json.loads(json_output)
                except ValueError:
                    pass
        raise ValueError("Can't parse json out of remote's avocado output:"
                         "\n%s" % result.stdout)

    def run_suite(self, params_list):
        """
        Run one or more tests and report with test result.

        :param params_list: a list of param dicts.

        :return: a list of test failures.
        """
        failures = []
        self.result.setup()
        results = self.run_test(self.result.urls)
        remote_log_dir = os.path.dirname(results['debuglog'])
        self.result.start_tests()
        for tst in results['tests']:
            test = RemoteTest(name=tst['test'],
                              time=tst['time'],
                              start=tst['start'],
                              end=tst['end'],
                              status=tst['status'])
            state = test.get_state()
            self.result.start_test(state)
            self.result.check_test(state)
            if not status.mapping[state['status']]:
                failures.append(state['tagged_name'])
        local_log_dir = os.path.dirname(self.result.stream.debuglog)
        zip_filename = remote_log_dir + '.zip'
        zip_path_filename = os.path.join(local_log_dir, os.path.basename(zip_filename))
        self.result.remote.receive_files(local_log_dir, zip_filename)
        archive.uncompress(zip_path_filename, local_log_dir)
        os.remove(zip_path_filename)
        self.result.end_tests()
        self.result.tear_down()
        return failures


class RemoteTestResult(TestResult):

    """
    Remote Machine Test Result class.
    """

    def __init__(self, stream, args):
        """
        Creates an instance of RemoteTestResult.

        :param stream: an instance of :class:`avocado.core.output.View`.
        :param args: an instance of :class:`argparse.Namespace`.
        """
        TestResult.__init__(self, stream, args)
        self.test_dir = os.getcwd()
        self.remote_test_dir = '~/avocado/tests'
        self.output = '-'

    def _copy_tests(self):
        self.remote.makedir(self.remote_test_dir)
        uniq_urls = list(set(self.urls))
        for url in uniq_urls:
            parent_dir = url.split(os.path.sep)[0]
            if os.path.isdir(parent_dir):
                test_path = os.path.abspath(parent_dir)
            else:
                test_path = os.path.join(data_dir.get_test_dir(), "%s*" % url)
            self.remote.send_files(test_path, self.remote_test_dir)

    def setup(self):
        self.urls = self.args.url
        if self.args.remote_hostname is None:
            e_msg = ('Please set remote machine hostname with option '
                     '--remote-hostname.')
            self.stream.notify(event='error', msg=e_msg)
            raise exceptions.TestSetupFail(e_msg)
        self.stream.notify(event='message', msg="REMOTE LOGIN  : %s@%s:%d" % (self.args.remote_username,
                                                                              self.args.remote_hostname,
                                                                              self.args.remote_port))
        self.remote = remote.Remote(self.args.remote_hostname,
                                    self.args.remote_username,
                                    self.args.remote_password,
                                    self.args.remote_port,
                                    quiet=True)
        self._copy_tests()

    def tear_down(self):
        pass

    def start_tests(self):
        """
        Called once before any tests are executed.
        """
        TestResult.start_tests(self)
        self.stream.notify(event='message', msg="JOB ID    : %s" % self.stream.job_unique_id)
        self.stream.notify(event='message', msg="JOB LOG   : %s" % self.stream.logfile)
        if self.args is not None:
            if 'html_output' in self.args:
                logdir = os.path.dirname(self.stream.logfile)
                html_file = os.path.join(logdir, 'html', 'results.html')
                self.stream.notify(event="message", msg="JOB HTML  : %s" % html_file)
        self.stream.notify(event='message', msg="TESTS     : %s" % self.tests_total)
        self.stream.set_tests_info({'tests_total': self.tests_total})

    def end_tests(self):
        """
        Called once after all tests are executed.
        """
        self.stream.notify(event='message', msg="PASS       : %d" % len(self.passed))
        self.stream.notify(event='message', msg="ERROR      : %d" % len(self.errors))
        self.stream.notify(event='message', msg="NOT FOUND  : %d" % len(self.not_found))
        self.stream.notify(event='message', msg="NOT A TEST : %d" % len(self.not_a_test))
        self.stream.notify(event='message', msg="FAIL       : %d" % len(self.failed))
        self.stream.notify(event='message', msg="SKIP       : %d" % len(self.skipped))
        self.stream.notify(event='message', msg="WARN       : %d" % len(self.warned))
        self.stream.notify(event='message', msg="TIME       : %.2f s" % self.total_time)

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
        Called when a test path was not found.

        :param test: :class:`avocado.test.Test` instance.
        """
        TestResult.add_not_found(self, test)
        self.stream.set_test_status(status='NOT_FOUND', state=test)

    def add_not_a_test(self, test):
        """
        Called when a file is not an avocado test.

        :param test: :class:`avocado.test.Test` instance.
        """
        TestResult.add_not_a_test(self, test)
        self.stream.set_test_status(status='NOT_A_TEST', state=test)

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


class RunRemote(plugin.Plugin):

    """
    Run tests on a remote machine
    """

    name = 'run_remote'
    enabled = True

    def configure(self, parser):
        if remote.remote_capable is False:
            self.enabled = False
            return
        username = getpass.getuser()
        self.remote_parser = parser.runner.add_argument_group('run on a remote machine '
                                                              'arguments')
        self.remote_parser.add_argument('--remote-hostname', dest='remote_hostname',
                                        default=None,
                                        help='Specify the hostname to login on remote machine')
        self.remote_parser.add_argument('--remote-port', dest='remote_port',
                                        default=22, type=int,
                                        help='Specify the port number to login on remote machine. '
                                             'Current: 22')
        self.remote_parser.add_argument('--remote-username', dest='remote_username',
                                        default=username,
                                        help=('Specify the username to login on remote machine. '
                                              'Current: %(default)s'))
        self.remote_parser.add_argument('--remote-password', dest='remote_password',
                                        default=None,
                                        help='Specify the password to login on remote machine')
        self.configured = True

    def activate(self, app_args):
        try:
            if app_args.remote_hostname is not None:
                self.remote_parser.set_defaults(remote_result=RemoteTestResult,
                                                test_runner=RemoteTestRunner)
        except AttributeError:
            pass
