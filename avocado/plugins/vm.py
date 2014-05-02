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
import json

import libvirt
import fabric.api
import fabric.operations

from avocado.core import exceptions
from avocado.core import data_dir
from avocado.core import status
from avocado.result import TestResult
from avocado.plugins import plugin
from avocado.utils.misc import unique


class Hypervisor(object):

    """
    Hypervisor connection class.
    """

    def __init__(self, uri=None):
        self.uri = uri
        self.connected = False
        self.connection = None
        self.domains = []

    def _get_domains(self):
        self.domains = self.connection.listAllDomains()

    def connect(self):
        if self.connected is False:
            try:
                self.connection = libvirt.open(self.uri)
            except libvirt.libvirtError as err:
                self.connected = False
                return None
            else:
                self.connected = True
        self._get_domains()
        return self.connection

    def find_domain_by_name(self, name):
        self._get_domains()
        for domain in self.domains:
            if name == domain.name():
                return domain
        return None

    def start_domain(self, xml):
        try:
            self.connection.createXML(xml)
        except libvirt.libvirtError as err:
            return False
        else:
            return True


class VirtMachine(object):

    """
    Virtual Machine handler class.
    """

    def __init__(self, hypervisor, domain):
        self.connection = hypervisor
        self.domain = domain
        self.logged = False

    def start(self):
        if not self.domain:
            return False
        if self.domain and self.domain.isActive():
            return True
        xml = self.domain.XMLDesc()
        if self.connection.start_domain(xml):
            return True
        return False

    def create_snapshot(self):
        pass

    def restore_snapshot(self):
        pass

    def cleanup(self):
        self.restore_snapshot()

    def get_hostname(self, domain):
        pass

    def _setenv(self, **kwargs):
        fabric.api.env.update(kwargs)

    def execute(self, command, quiet=True):
        return fabric.operations.run(command, quiet=quiet)

    def setup_login(self, hostname, username, password=None):
        if not self.logged:
            self._setenv(host_string=hostname,
                         user=username,
                         password=password)
            res = self.execute('uptime')
            if res.succeeded:
                self.logged = True
        else:
            self.logged = False

    def makedir(self, remote_path, quiet=True):
        cmd = 'mkdir -p %s' % remote_path
        self.execute(cmd, quiet=quiet)

    def send_files(self, local_path, remote_path):
        with fabric.context_managers.quiet():
            try:
                fabric.operations.put(local_path,
                                      remote_path)
            except ValueError as err:
                return False
        return True

    def receive_files(self, local_path, remote_path):
        with fabric.context_managers.quiet():
            try:
                fabric.operations.get(remote_path,
                                      local_path)
            except ValueError as err:
                return False
        return True


class VirtMachineTestResult(TestResult):

    """
    Virtual Machine Test Result class.
    """

    def __init__(self, stream=None, debuglog=None, loglevel=None,
                 urls=[], args=None):
        """
        :param stream: Stream where to write output, such as :attr:`sys.stdout`.
        :param debuglog: Debug log file path.
        :param loglevel: Log level in the :mod:`logging` module.
        :param tests_total: Total of tests executed
        :param args: :class:`argparse.Namespace` with cmdline arguments.
        """
        TestResult.__init__(self, stream, debuglog, loglevel, urls, args)
        self.test_dir = data_dir.get_test_dir()
        self.remote_test_dir = '~/avocado/tests'

    def _copy_tests(self):
        self.vm.makedir(self.remote_test_dir)
        uniq_urls = unique(self.urls)
        for url in uniq_urls:
            test_path = os.path.join(self.test_dir, url)
            self.vm.send_files(test_path, self.remote_test_dir)

    def setup(self):
        self.stream.log_header("REMOTE TESTS: Virtual Machine Domain '%s'" % self.args.vm_domain)
        self.stream.log_header("REMOTE TESTS: Host login '%s@%s'" % (self.args.vm_username, self.args.vm_hostname))
        self.hyper = Hypervisor(self.args.vm_hypervisor_uri)
        self.hyper.connect()
        if self.hyper.connected is False:
            self.stream.error('Could not connect to the hypervisor')
            raise exceptions.TestSetupFail()
        self.vm = VirtMachine(self.hyper,
                              self.hyper.find_domain_by_name(self.args.vm_domain))
        if self.vm.start() is False:
            self.stream.error("Could not start VM '%s'" % self.args.vm_domain)
            raise exceptions.TestSetupFail()
        assert self.vm.domain.isActive()
        self.vm.create_snapshot()
        self.vm.setup_login(self.args.vm_hostname,
                            self.args.vm_username,
                            self.args.vm_password)
        if self.vm.logged is False:
            self.stream.error("Could not logging on '%s'" % self.args.vm_hostname)
            raise exceptions.TestSetupFail()
        self._copy_tests()

    def tear_down(self):
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
        self.stream.log_header("DEBUG LOG: %s" % self.debuglog)
        self.stream.log_header("TOTAL PASSED: %d" % len(self.passed))
        self.stream.log_header("TOTAL ERROR: %d" % len(self.errors))
        self.stream.log_header("TOTAL FAILED: %d" % len(self.failed))
        self.stream.log_header("TOTAL SKIPPED: %d" % len(self.skipped))
        self.stream.log_header("TOTAL WARNED: %d" % len(self.warned))
        self.stream.log_header("ELAPSED TIME: %.2f s" % self.total_time)

    def start_test(self, test):
        """
        Called when the given test is about to run.

        :param test: :class:`avocado.test.Test` instance.
        """
        self.test_label = '(%s/%s) %s: ' % (self.tests_run,
                                            self.tests_total,
                                            test.tagged_name)

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
        self.stream.log_pass(self.test_label, test.time_elapsed)

    def add_error(self, test):
        """
        Called when a test had a setup error.

        :param test: :class:`avocado.test.Test` instance.
        """
        TestResult.add_error(self, test)
        self.stream.log_error(self.test_label, test.time_elapsed)

    def add_fail(self, test):
        """
        Called when a test fails.

        :param test: :class:`avocado.test.Test` instance.
        """
        TestResult.add_fail(self, test)
        self.stream.log_fail(self.test_label, test.time_elapsed)

    def add_skip(self, test):
        """
        Called when a test is skipped.

        :param test: :class:`avocado.test.Test` instance.
        """
        TestResult.add_skip(self, test)
        self.stream.log_skip(self.test_label, test.time_elapsed)

    def add_warn(self, test):
        """
        Called when a test had a warning.

        :param test: :class:`avocado.test.Test` instance.
        """
        TestResult.add_warn(self, test)
        self.stream.log_warn(self.test_label, test.time_elapsed)


class Test(object):

    """
    Duck types :class:`avocado.test.Test`.
    """

    def __init__(self, name, status, time):
        self.tagged_name = name
        self.status = status
        self.time_elapsed = time

#
# Plugin registration
#


class RunVM(plugin.Plugin):

    """
    Run tests on Virtual Machine plugin.
    """

    name = 'virtual_machine'
    enabled = True

    def configure(self, app_parser, cmd_parser):
        self.parser = app_parser
        app_parser.add_argument('--vm', action='store_true')
        app_parser.add_argument('--vm-hypervisor-uri',
                                default='qemu:///system', type=str,
                                dest='vm_hypervisor_uri',
                                help='Specify hypervisor URI driver connection')
        app_parser.add_argument('--vm-domain', type=str, dest='vm_domain',
                                help='Specify domain name (Virtual Machine name)')
        app_parser.add_argument('--vm-hostname', type=str, dest='vm_hostname',
                                help='Specify VM hostname to login')
        app_parser.add_argument('--vm-username', type=str, dest='vm_username',
                                help='Specify the username to login on VM')
        app_parser.add_argument('--vm-password', type=str, dest='vm_password',
                                help='Specify the password to login on VM')
        self.configured = True

    def activate(self, app_args):
        if app_args.vm:
            self.parser.set_defaults(test_result=VirtMachineTestResult,
                                     test_runner=vm_test_runner)


#
# Test Runner alternative.
#

def vm_run_test(urls):
    """
    Run tests.
    """
    avocado_cmd = 'avocado --collect run "%s"' % urls
    stdout = fabric.operations.run(avocado_cmd,
                                   warn_only=True,
                                   quiet=True)
    results = json.loads(stdout)
    return results


def vm_test_runner(urls, test_result):
    """
    Run one or more tests and report with test result.

    :param urls: a list of tests URLs.
    :param test_result: An instance of :class:`avocado.result.TestResult`.
    :return: a list of test failures.
    """
    failures = []
    urls = ' '.join(urls)
    results = vm_run_test(urls)
    remote_log_dir = os.path.dirname(results['debuglog'])
    for tst in results['tests']:
        test = Test(name=tst['test'],
                    time=tst['time'],
                    status=tst['status'])
        test_result.check_test(test)
        if not status.mapping[test.status]:
            failures.append(test.tagged_name)
    # FIXME: Ugly but works, improve later
    local_log_dir = os.path.dirname(test_result.debuglog)
    remote_files = '%s/*' % remote_log_dir
    test_result.vm.receive_files(local_log_dir, remote_files)
    return failures
