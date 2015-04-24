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
# Copyright: Red Hat Inc. 2013-2015
# Authors: Lucas Meneghel Rodrigues <lmr@redhat.com>
#          Ruda Moura <rmoura@redhat.com>

"""
Job module - describes a sequence of automated test operations.
"""

import argparse
import logging
import os
import sys
import traceback
import tempfile
import shutil
import fnmatch

from avocado import multiplexer
from avocado import runtime
from avocado import data_dir
from avocado.core import runner
from avocado.core import loader
from avocado.core import sysinfo
from avocado.core import result
from avocado.core import exit_codes
from avocado.core import exceptions
from avocado.core import job_id
from avocado.core import output
from avocado.core.plugins import jsonresult
from avocado.core.plugins import xunit
from avocado.utils import archive
from avocado.utils import path
from avocado.settings import settings

try:
    from avocado.core.plugins import htmlresult
except ImportError:
    HTML_REPORT_SUPPORT = False
else:
    HTML_REPORT_SUPPORT = htmlresult.HTML_REPORT_CAPABLE

_NEW_ISSUE_LINK = 'https://github.com/avocado-framework/avocado/issues/new'

_TEST_LOGGER = logging.getLogger('avocado.test')


class Job(object):

    """
    A Job is a set of operations performed on a test machine.

    Most of the time, we are interested in simply running tests,
    along with setup operations and event recording.
    """

    def __init__(self, args=None):
        """
        Creates an instance of Job class.

        :param args: an instance of :class:`argparse.Namespace`.
        """
        if args is None:
            args = argparse.Namespace()
        self.args = args
        self.standalone = getattr(self.args, 'standalone', False)
        unique_id = getattr(self.args, 'unique_job_id', None)
        if unique_id is None:
            unique_id = job_id.create_unique_job_id()
        self.unique_id = unique_id
        self.view = output.View(app_args=self.args)
        self.logdir = None
        raw_log_level = settings.get_value('job.output', 'loglevel',
                                           default='debug')
        mapping = {'info': logging.INFO,
                   'debug': logging.DEBUG,
                   'warning': logging.WARNING,
                   'error': logging.ERROR,
                   'critical': logging.CRITICAL}
        if raw_log_level in mapping:
            self.loglevel = mapping[raw_log_level]
        else:
            self.loglevel = logging.DEBUG
        self.show_job_log = getattr(self.args, 'show_job_log', False)
        self.silent = getattr(self.args, 'silent', False)

        if self.standalone:
            self.show_job_log = True
            if self.args is not None:
                setattr(self.args, 'show_job_log', True)

        if self.show_job_log:
            if not self.silent:
                output.add_console_handler(_TEST_LOGGER)
                _TEST_LOGGER.setLevel(self.loglevel)

        self.test_dir = data_dir.get_test_dir()
        self.test_index = 1
        self.status = "RUNNING"
        self.result_proxy = result.TestResultProxy()
        self.sysinfo = None
        self.timeout = getattr(self.args, 'job_timeout', 0)

    def _setup_job_results(self):
        logdir = getattr(self.args, 'logdir', None)
        if self.standalone:
            if logdir is not None:
                logdir = os.path.abspath(logdir)
                self.logdir = data_dir.create_job_logs_dir(logdir=logdir,
                                                           unique_id=self.unique_id)
            else:
                self.logdir = tempfile.mkdtemp(prefix='avocado-')
        else:
            if logdir is None:
                self.logdir = data_dir.create_job_logs_dir(unique_id=self.unique_id)
            else:
                logdir = os.path.abspath(logdir)
                self.logdir = data_dir.create_job_logs_dir(logdir=logdir,
                                                           unique_id=self.unique_id)
        self.logfile = os.path.join(self.logdir, "job.log")
        self.idfile = os.path.join(self.logdir, "id")
        with open(self.idfile, 'w') as id_file_obj:
            id_file_obj.write("%s\n" % self.unique_id)

    def _update_latest_link(self):
        data_dir.update_latest_job_logs_dir(self.logdir)

    def _start_sysinfo(self):
        if hasattr(self.args, 'sysinfo'):
            if self.args.sysinfo == 'on':
                sysinfo_dir = path.init_dir(self.logdir, 'sysinfo')
                self.sysinfo = sysinfo.SysInfo(basedir=sysinfo_dir)

    def _remove_job_results(self):
        shutil.rmtree(self.logdir, ignore_errors=True)

    def _make_test_loader(self):
        if hasattr(self.args, 'test_loader'):
            test_loader_class = self.args.test_loader
        else:
            test_loader_class = loader.TestLoader

        self.test_loader = test_loader_class(job=self)

    def _make_test_runner(self):
        if hasattr(self.args, 'test_runner'):
            test_runner_class = self.args.test_runner
        else:
            test_runner_class = runner.TestRunner

        self.test_runner = test_runner_class(job=self,
                                             test_result=self.result_proxy)

    def _set_output_plugins(self):
        for key in self.args.__dict__:
            if key.endswith('_result'):
                result_class = getattr(self.args, key)
                if issubclass(result_class, result.TestResult):
                    result_plugin = result_class(self.view,
                                                 self.args)
                    self.result_proxy.add_output_plugin(result_plugin)

    def _make_test_result(self):
        """
        Set up output plugins.

        The basic idea behind the output plugins is:

        * If there are any active output plugins, use them
        * Always add Xunit and JSON plugins outputting to files inside the
          results dir
        * If at the end we only have 2 output plugins (Xunit and JSON), we can
          add the human output plugin.
        """
        if self.args:
            # If there are any active output plugins, let's use them
            self._set_output_plugins()

        # Setup the xunit plugin to output to the debug directory
        xunit_file = os.path.join(self.logdir, 'results.xml')
        args = argparse.Namespace()
        args.xunit_output = xunit_file
        xunit_plugin = xunit.xUnitTestResult(self.view, args)
        self.result_proxy.add_output_plugin(xunit_plugin)

        # Setup the json plugin to output to the debug directory
        json_file = os.path.join(self.logdir, 'results.json')
        args = argparse.Namespace()
        args.json_output = json_file
        json_plugin = jsonresult.JSONTestResult(self.view, args)
        self.result_proxy.add_output_plugin(json_plugin)

        # Setup the json plugin to output to the debug directory
        if HTML_REPORT_SUPPORT:
            html_file = os.path.join(self.logdir, 'html', 'results.html')
            args = argparse.Namespace()
            args.html_output = html_file
            args.open_browser = getattr(self.args, 'open_browser', False)
            args.relative_links = True
            html_plugin = htmlresult.HTMLTestResult(self.view, args)
            self.result_proxy.add_output_plugin(html_plugin)

        op_set_stdout = self.result_proxy.output_plugins_using_stdout()
        if len(op_set_stdout) > 1:
            msg = ('Options %s are trying to use stdout simultaneously' %
                   " ".join(op_set_stdout))
            self.view.notify(event='error', msg=msg)
            msg = ('Please set at least one of them to a file to avoid '
                   'conflicts')
            self.view.notify(event='error', msg=msg)
            sys.exit(exit_codes.AVOCADO_JOB_FAIL)

        if not op_set_stdout and not self.standalone:
            human_plugin = result.HumanTestResult(self.view, self.args)
            self.result_proxy.add_output_plugin(human_plugin)

    def _handle_urls(self, urls):
        if urls is None:
            urls = getattr(self.args, 'url', None)

        if isinstance(urls, str):
            urls = urls.split()

        if not urls:
            e_msg = "Empty test ID. A test path or alias must be provided"
            raise exceptions.OptionValidationError(e_msg)

        return urls

    def _make_test_suite(self, urls=None):
        """
        Prepares a test suite to be used for running tests

        :param urls: String with tests to run, separated by whitespace.
                     Optionally, a list of tests (each test a string).
        :returns: a test suite (a list of test factories)
        """
        urls = self._handle_urls(urls)

        self._make_test_loader()

        params_list = self.test_loader.discover_urls(urls)
        test_suite = self.test_loader.discover(params_list)
        return test_suite

    def _validate_test_suite(self, test_suite):
        try:
            # Do not attempt to validate the tests given on the command line if
            # the tests will not be copied from this system to a remote one
            # using the remote plugin features
            if not getattr(self.args, 'remote_no_copy', False):
                error_msg_parts = self.test_loader.validate_ui(test_suite)
            else:
                error_msg_parts = []
        except KeyboardInterrupt:
            raise exceptions.JobError('Command interrupted by user...')

        if error_msg_parts:
            self._remove_job_results()
            e_msg = '\n'.join(error_msg_parts)
            raise exceptions.OptionValidationError(e_msg)

    def _filter_test_suite(self, test_suite):
        # Filter tests methods with params.filter and methodName
        filtered_suite = []
        for test_template in test_suite:
            test_factory, test_parameters = test_template
            filter_pattern = test_parameters['params'].get('filter', None)
            method = test_parameters.get('methodName')
            if not filter_pattern:
                filtered_suite.append(test_template)
            else:
                if method and fnmatch.fnmatch(method, filter_pattern):
                    filtered_suite.append(test_template)
        return filtered_suite

    def _run(self, urls=None):
        """
        Unhandled job method. Runs a list of test URLs to its completion.

        :param urls: String with tests to run, separated by whitespace.
                     Optionally, a list of tests (each test a string).
        :return: Integer with overall job status. See
                 :mod:`avocado.core.exit_codes` for more information.
        :raise: Any exception (avocado crashed), or
                :class:`avocado.core.exceptions.JobBaseException` errors,
                that configure a job failure.
        """
        self._setup_job_results()

        test_suite = self._make_test_suite(urls)
        self._validate_test_suite(test_suite)
        test_suite = self._filter_test_suite(test_suite)
        if not test_suite:
            e_msg = ("No tests found within the specified path(s) "
                     "(Possible reasons: File ownership, permissions, "
                     "filters, typos)")
            raise exceptions.OptionValidationError(e_msg)

        try:
            mux = multiplexer.Mux(self.args)
        except IOError, details:
            raise exceptions.OptionValidationError(details.strerror)
        self.args.test_result_total = mux.get_number_of_tests(test_suite)

        self._make_test_result()
        self._make_test_runner()
        self._start_sysinfo()

        self.view.start_file_logging(self.logfile,
                                     self.loglevel,
                                     self.unique_id)
        _TEST_LOGGER.info('Job ID: %s', self.unique_id)
        _TEST_LOGGER.info('')

        self.view.logfile = self.logfile
        failures = self.test_runner.run_suite(test_suite, mux,
                                              timeout=self.timeout)
        self.view.stop_file_logging()
        if not self.standalone:
            self._update_latest_link()
        # If it's all good so far, set job status to 'PASS'
        if self.status == 'RUNNING':
            self.status = 'PASS'
        # Let's clean up test artifacts
        if getattr(self.args, 'archive', False):
            filename = self.logdir + '.zip'
            archive.create(filename, self.logdir)
        if not settings.get_value('runner.behavior', 'keep_tmp_files',
                                  key_type=bool, default=False):
            data_dir.clean_tmp_files()
        _TEST_LOGGER.info('Test results available in %s', self.logdir)

        tests_status = not bool(failures)
        if tests_status:
            return exit_codes.AVOCADO_ALL_OK
        else:
            return exit_codes.AVOCADO_TESTS_FAIL

    def run(self, urls=None):
        """
        Handled main job method. Runs a list of test URLs to its completion.

        Note that the behavior is as follows:

        * If urls is provided alone, just make a simple list with no specific
          params (all tests use default params).
        * If urls and multiplex_files are provided, multiplex provides params
          and variants to all tests it can.
        * If multiplex_files are provided alone, just use the matrix produced
          by the file

        The test runner figures out which tests need to be run on an empty urls
        list by assuming the first component of the shortname is the test url.

        :param urls: String with tests to run, separated by whitespace.
                     Optionally, a list of tests (each test a string).
        :return: Integer with overall job status. See
                 :mod:`avocado.core.exit_codes` for more information.
        """
        runtime.CURRENT_JOB = self
        try:
            return self._run(urls)
        except exceptions.JobBaseException, details:
            self.status = details.status
            fail_class = details.__class__.__name__
            self.view.notify(event='error', msg=('Avocado job failed: %s: %s' %
                                                 (fail_class, details)))
            return exit_codes.AVOCADO_JOB_FAIL
        except exceptions.OptionValidationError, details:
            self.view.notify(event='error', msg=str(details))
            return exit_codes.AVOCADO_JOB_FAIL

        except Exception, details:
            self.status = "ERROR"
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tb_info = traceback.format_exception(exc_type, exc_value,
                                                 exc_traceback.tb_next)
            fail_class = details.__class__.__name__
            self.view.notify(event='error', msg=('Avocado crashed: %s: %s' %
                                                 (fail_class, details)))
            for line in tb_info:
                self.view.notify(event='minor', msg=line)
            self.view.notify(event='error', msg=('Please include the traceback '
                                                 'info and command line used on '
                                                 'your bug report'))
            self.view.notify(event='error', msg=('Report bugs visiting %s' %
                                                 _NEW_ISSUE_LINK))
            return exit_codes.AVOCADO_FAIL


class TestProgram(object):

    """
    Convenience class to make avocado test modules executable.
    """

    def __init__(self):
        self.defaultTest = sys.argv[0]
        self.progName = os.path.basename(sys.argv[0])
        self.parseArgs(sys.argv[1:])
        self.runTests()

    def parseArgs(self, argv):
        self.parser = argparse.ArgumentParser(prog=self.progName)
        self.parser.add_argument('-r', '--remove-test-results', action='store_true',
                                 help='remove all test results files after test execution')
        self.parser.add_argument('-d', '--test-results-dir', dest='logdir', default=None,
                                 metavar='TEST_RESULTS_DIR',
                                 help='use an alternative test results directory')
        self.args = self.parser.parse_args(argv)

    def runTests(self):
        exit_status = exit_codes.AVOCADO_ALL_OK
        self.args.standalone = True
        self.job = Job(self.args)
        if self.defaultTest is not None:
            exit_status = self.job.run(urls=[self.defaultTest])
        if self.args.remove_test_results is True:
            shutil.rmtree(self.job.logdir)
        sys.exit(exit_status)


main = TestProgram
