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
import commands
import logging
import os
import sys
import traceback
import tempfile
import shutil
import fnmatch

from . import version
from . import data_dir
from . import runner
from . import loader
from . import sysinfo
from . import result
from . import exit_codes
from . import exceptions
from . import job_id
from . import output
from . import multiplexer
from . import tree
from . import test
from . import xunit
from .settings import settings
from .plugins import jsonresult
from ..utils import archive
from ..utils import astring
from ..utils import path
from ..utils import runtime
from ..utils import stacktrace
from ..utils import data_structures


try:
    from .plugins import htmlresult
    HTML_REPORT_SUPPORT = True
except ImportError:
    HTML_REPORT_SUPPORT = False


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
        if getattr(self.args, "dry_run", False):  # Modify args for dry-run
            if not self.args.unique_job_id:
                self.args.unique_job_id = "0" * 40
            self.args.sysinfo = False
            if self.args.logdir is None:
                self.args.logdir = tempfile.mkdtemp(prefix="avocado-dry-run-")

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
                output.add_console_handler(logging.getLogger())
                _TEST_LOGGER.setLevel(self.loglevel)
                _TEST_LOGGER.propagate = False

        self.test_dir = data_dir.get_test_dir()
        self.test_index = 1
        self.status = "RUNNING"
        self.result_proxy = result.TestResultProxy()
        self.sysinfo = None
        self.timeout = getattr(self.args, 'job_timeout', 0)
        self.funcatexit = data_structures.CallbackRegister("JobExit %s"
                                                           % self.unique_id,
                                                           _TEST_LOGGER)

    def _setup_job_results(self):
        logdir = getattr(self.args, 'logdir', None)
        if self.standalone:
            if logdir is not None:
                logdir = os.path.abspath(logdir)
                self.logdir = data_dir.create_job_logs_dir(logdir=logdir,
                                                           unique_id=self.unique_id)
            else:
                self.logdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
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
        """
        Update the latest job result symbolic link [avocado-logs-dir]/latest.
        """
        basedir = os.path.dirname(self.logdir)
        basename = os.path.basename(self.logdir)
        latest = os.path.join(basedir, "latest")
        if os.path.exists(latest) and not os.path.islink(latest):
            raise OSError('"%s" already exists and is not a symlink' % latest)
        try:
            os.unlink(latest)
        except OSError:
            pass
        os.symlink(basename, latest)

    def _start_sysinfo(self):
        if hasattr(self.args, 'sysinfo'):
            if self.args.sysinfo == 'on':
                sysinfo_dir = path.init_dir(self.logdir, 'sysinfo')
                self.sysinfo = sysinfo.SysInfo(basedir=sysinfo_dir)

    def _remove_job_results(self):
        shutil.rmtree(self.logdir, ignore_errors=True)

    def _make_test_runner(self):
        if hasattr(self.args, 'test_runner'):
            test_runner_class = self.args.test_runner
        else:
            test_runner_class = runner.TestRunner

        self.test_runner = test_runner_class(job=self,
                                             test_result=self.result_proxy)

    def _set_output_plugins(self):
        for key in self.args.__dict__.keys():
            result_class_candidate = getattr(self.args, key)
            try:
                if issubclass(result_class_candidate, result.TestResult):
                    result_plugin = result_class_candidate(self.view,
                                                           self.args)
                    self.result_proxy.add_output_plugin(result_plugin)
            except TypeError:
                pass

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

        return urls

    def _make_test_suite(self, urls=None):
        """
        Prepares a test suite to be used for running tests

        :param urls: String with tests to run, separated by whitespace.
                     Optionally, a list of tests (each test a string).
        :returns: a test suite (a list of test factories)
        """
        urls = self._handle_urls(urls)
        loader.loader.load_plugins(self.args)
        try:
            suite = loader.loader.discover(urls)
        except loader.LoaderUnhandledUrlError, details:
            self._remove_job_results()
            raise exceptions.OptionValidationError(details)
        except KeyboardInterrupt:
            self._remove_job_results()
            raise exceptions.JobError('Command interrupted by user...')

        if not getattr(self.args, "dry_run", False):
            return suite
        for i in xrange(len(suite)):
            suite[i] = [test.DryRunTest, suite[i][1]]
        return suite

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

    def _log_job_id(self):
        job_log = _TEST_LOGGER
        job_log.info('Job ID: %s', self.unique_id)
        job_log.info('')

    @staticmethod
    def _log_cmdline():
        job_log = _TEST_LOGGER
        cmdline = " ".join(sys.argv)
        job_log.info("Command line: %s", cmdline)
        job_log.info('')

    @staticmethod
    def _log_avocado_version():
        job_log = _TEST_LOGGER
        job_log.info('Avocado version: %s', version.VERSION)
        if os.path.exists('.git') and os.path.exists('avocado.spec'):
            cmd = "git show --summary --pretty='%H' | head -1"
            status, top_commit = commands.getstatusoutput(cmd)
            cmd2 = "git rev-parse --abbrev-ref HEAD"
            status2, branch = commands.getstatusoutput(cmd2)
            # Let's display information only if git is installed
            # (commands succeed).
            if status == 0 and status2 == 0:
                job_log.info('Avocado git repo info')
                job_log.info("Top commit: %s", top_commit)
                job_log.info("Branch: %s", branch)
        job_log.info('')

    @staticmethod
    def _log_avocado_config():
        job_log = _TEST_LOGGER
        job_log.info('Config files read (in order):')
        for cfg_path in settings.config_paths:
            job_log.info(cfg_path)
        if settings.config_paths_failed:
            job_log.info('Config files failed to read (in order):')
            for cfg_path in settings.config_paths_failed:
                job_log.info(cfg_path)
        job_log.info('')

        job_log.info('Avocado config:')
        header = ('Section.Key', 'Value')
        config_matrix = []
        for section in settings.config.sections():
            for value in settings.config.items(section):
                config_key = ".".join((section, value[0]))
                config_matrix.append([config_key, value[1]])

        for line in astring.iter_tabular_output(config_matrix, header):
            job_log.info(line)
        job_log.info('')

    @staticmethod
    def _log_avocado_datadir():
        job_log = _TEST_LOGGER
        job_log.info('Avocado Data Directories:')
        job_log.info('')
        job_log.info("Avocado replaces config dirs that can't be accessed")
        job_log.info('with sensible defaults. Please edit your local config')
        job_log.info('file to customize values')
        job_log.info('')
        job_log.info('base     ' + data_dir.get_base_dir())
        job_log.info('tests    ' + data_dir.get_test_dir())
        job_log.info('data     ' + data_dir.get_data_dir())
        job_log.info('logs     ' + data_dir.get_logs_dir())
        job_log.info('')

    def _log_mux_tree(self, mux):
        job_log = _TEST_LOGGER
        tree_repr = tree.tree_view(mux.variants.root, verbose=True,
                                   use_utf8=False)
        if tree_repr:
            job_log.info('Multiplex tree representation:')
            for line in tree_repr.splitlines():
                job_log.info(line)
            job_log.info('')

    def _log_tmp_dir(self):
        job_log = _TEST_LOGGER
        job_log.info('Temporary dir: %s', data_dir.get_tmp_dir())
        job_log.info('')

    def _log_mux_variants(self, mux):
        job_log = _TEST_LOGGER

        for (index, tpl) in enumerate(mux.variants):
            paths = ', '.join([x.path for x in tpl])
            job_log.info('Variant %s:    %s', index + 1, paths)

        if mux.variants:
            job_log.info('')

    def _log_job_debug_info(self, mux):
        """
        Log relevant debug information to the job log.
        """
        self._log_cmdline()
        self._log_avocado_version()
        self._log_avocado_config()
        self._log_avocado_datadir()
        self._log_mux_tree(mux)
        self._log_tmp_dir()
        self._log_mux_variants(mux)
        self._log_job_id()

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
        self.view.start_file_logging(self.logfile,
                                     self.loglevel,
                                     self.unique_id)
        try:
            test_suite = self._make_test_suite(urls)
        except loader.LoaderError, details:
            stacktrace.log_exc_info(sys.exc_info(), 'avocado.app.tracebacks')
            self._remove_job_results()
            raise exceptions.OptionValidationError(details)
        if not test_suite:
            self._remove_job_results()
            e_msg = ("No tests found for given urls, try 'avocado list -V %s' "
                     "for details" % (" ".join(urls) if urls else "\b"))
            raise exceptions.OptionValidationError(e_msg)

        try:
            mux = multiplexer.Mux(self.args)
        except (IOError, ValueError), details:
            raise exceptions.OptionValidationError(details)
        self.args.test_result_total = mux.get_number_of_tests(test_suite)

        self._make_test_result()
        if not (self.standalone or getattr(self.args, "dry_run", False)):
            self._update_latest_link()
        self._make_test_runner()
        self._start_sysinfo()

        self._log_job_debug_info(mux)

        self.view.logfile = self.logfile
        failures = self.test_runner.run_suite(test_suite, mux,
                                              timeout=self.timeout)
        self.view.stop_file_logging()
        # If it's all good so far, set job status to 'PASS'
        if self.status == 'RUNNING':
            self.status = 'PASS'
        # Let's clean up test artifacts
        if getattr(self.args, 'archive', False):
            filename = self.logdir + '.zip'
            archive.create(filename, self.logdir)
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
            self.view.notify(event='error', msg=('\nAvocado job failed: %s: %s'
                                                 % (fail_class, details)))
            return exit_codes.AVOCADO_JOB_FAIL
        except exceptions.OptionValidationError, details:
            self.view.notify(event='error', msg='\n' + str(details))
            return exit_codes.AVOCADO_JOB_FAIL

        except Exception, details:
            self.status = "ERROR"
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tb_info = traceback.format_exception(exc_type, exc_value,
                                                 exc_traceback.tb_next)
            fail_class = details.__class__.__name__
            self.view.notify(event='error', msg=('\nAvocado crashed: %s: %s' %
                                                 (fail_class, details)))
            for line in tb_info:
                self.view.notify(event='minor', msg=line)
            self.view.notify(event='error', msg=('Please include the traceback '
                                                 'info and command line used on '
                                                 'your bug report'))
            self.view.notify(event='error', msg=('Report bugs visiting %s' %
                                                 _NEW_ISSUE_LINK))
            return exit_codes.AVOCADO_FAIL
        finally:
            if not settings.get_value('runner.behavior', 'keep_tmp_files',
                                      key_type=bool, default=False):
                data_dir.clean_tmp_files()


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
