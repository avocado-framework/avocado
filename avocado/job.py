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
# Copyright: Red Hat Inc. 2013-2014
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

from avocado import multiplexer
from avocado import result
from avocado import runner
from avocado import loader
from avocado import runtime
from avocado import sysinfo
from avocado.core import data_dir, tree
from avocado.core import exit_codes
from avocado.core import exceptions
from avocado.core import job_id
from avocado.core import output
from avocado.plugins import jsonresult
from avocado.plugins import xunit
from avocado.utils import archive
from avocado.utils import path
from avocado.plugins import htmlresult

HTML_REPORT_SUPPORT = htmlresult.HTML_REPORT_CAPABLE
_NEW_ISSUE_LINK = 'https://github.com/avocado-framework/avocado/issues/new'


class Job(object):

    """
    A Job is a set of operations performed on a test machine.

    Most of the time, we are interested in simply running tests,
    along with setup operations and event recording.
    """

    def __init__(self, args=None, standalone=False):
        """
        Creates an instance of Job class.

        :param args: an instance of :class:`argparse.Namespace`.
        :param standalone: do not create any content and present the job log
                           on the output.
        """
        self.args = args
        self.standalone = standalone
        if args is not None:
            self.unique_id = args.unique_job_id or job_id.create_unique_job_id()
        else:
            self.unique_id = job_id.create_unique_job_id()
        self.view = output.View(app_args=self.args)
        self.logdir = None
        if self.args is not None:
            raw_log_level = args.job_log_level
            mapping = {'info': logging.INFO,
                       'debug': logging.DEBUG,
                       'warning': logging.WARNING,
                       'error': logging.ERROR,
                       'critical': logging.CRITICAL}
            if raw_log_level is not None and raw_log_level in mapping:
                self.loglevel = mapping[raw_log_level]
            else:
                self.loglevel = logging.DEBUG
            if multiplexer.MULTIPLEX_CAPABLE:
                self.multiplex_files = args.multiplex_files
            self.show_job_log = args.show_job_log
            self.silent = args.silent
        else:
            self.loglevel = logging.DEBUG
            self.multiplex_files = None
            self.show_job_log = False
            self.silent = False

        if standalone:
            self.show_job_log = True
            if self.args is not None:
                setattr(self.args, 'show_job_log', True)

        if self.show_job_log:
            if not self.silent:
                test_logger = logging.getLogger('avocado.test')
                output.add_console_handler(test_logger)
                test_logger.setLevel(self.loglevel)
        self.test_dir = data_dir.get_test_dir()
        self.test_index = 1
        self.status = "RUNNING"
        self.result_proxy = result.TestResultProxy()
        self.sysinfo = None

    def _setup_job_results(self):
        if self.standalone:
            self.logdir = tempfile.mkdtemp()
        else:
            self.logdir = data_dir.get_job_logs_dir(self.args, self.unique_id)
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
            if self.args is not None:
                args.open_browser = getattr(self.args, 'open_browser')
            else:
                args.open_browser = False
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

    def _multiplex_params_list(self, params_list, multiplex_files):
        for mux_file in multiplex_files:
            if not os.path.exists(mux_file):
                e_msg = "Multiplex file %s doesn't exist." % mux_file
                raise exceptions.OptionValidationError(e_msg)
        result = []
        for params in params_list:
            try:
                variants = multiplexer.multiplex_yamls(multiplex_files,
                                                       self.args.filter_only,
                                                       self.args.filter_out)
            except SyntaxError:
                variants = None
            if variants:
                tag = 1
                for variant in variants:
                    env = {}
                    for t in variant:
                        env.update(dict(t.environment))
                    env.update({'tag': tag})
                    env.update({'id': params['id']})
                    result.append(env)
                    tag += 1
            else:
                result.append(params)
        return result

    def _run(self, urls=None, multiplex_files=None):
        """
        Unhandled job method. Runs a list of test URLs to its completion.

        :param urls: String with tests to run, separated by whitespace.
                     Optionally, a list of tests (each test a string).
        :param multiplex_files: File that multiplexes a given test url.

        :return: Integer with overall job status. See
                 :mod:`avocado.core.exit_codes` for more information.
        :raise: Any exception (avocado crashed), or
                :class:`avocado.core.exceptions.JobBaseException` errors,
                that configure a job failure.
        """
        if urls is None:
            if self.args and self.args.url is not None:
                urls = self.args.url

        if isinstance(urls, str):
            urls = urls.split()

        if not urls:
            e_msg = "Empty test ID. A test path or alias must be provided"
            raise exceptions.OptionValidationError(e_msg)

        self._make_test_loader()

        params_list = self.test_loader.discover_urls(urls)

        if multiplexer.MULTIPLEX_CAPABLE:
            if multiplex_files is None:
                if self.args and self.args.multiplex_files is not None:
                    multiplex_files = self.args.multiplex_files

            if multiplex_files is not None:
                mpx_pools = multiplexer.parse_yamls(multiplex_files,
                                                    self.args.filter_only,
                                                    self.args.filter_out)
            else:
                mpx_pools = [[tree.TreeNode()]]
        else:
            mpx_pools = [[tree.TreeNode()]]    # void multiplex params

        self._setup_job_results()

        try:
            test_suite = self.test_loader.discover(params_list)
            error_msg_parts = self.test_loader.validate_ui(test_suite)
        except KeyboardInterrupt:
            raise exceptions.JobError('Command interrupted by user...')

        if error_msg_parts:
            self._remove_job_results()
            e_msg = '\n'.join(error_msg_parts)
            raise exceptions.OptionValidationError(e_msg)

        if not test_suite:
            e_msg = ("No tests found within the specified path(s) "
                     "(Possible reasons: File ownership, permissions, typos)")
            raise exceptions.OptionValidationError(e_msg)

        if self.args is not None:
            self.args.test_result_total = len(test_suite)

        self._make_test_result()
        self._make_test_runner()
        self._start_sysinfo()

        self.view.start_file_logging(self.logfile,
                                     self.loglevel,
                                     self.unique_id)
        self.view.logfile = self.logfile
        failures = self.test_runner.run_suite(test_suite, mpx_pools)
        self.view.stop_file_logging()
        self._update_latest_link()
        # If it's all good so far, set job status to 'PASS'
        if self.status == 'RUNNING':
            self.status = 'PASS'
        # Let's clean up test artifacts
        if self.args is not None:
            if self.args.archive:
                filename = self.logdir + '.zip'
                archive.create(filename, self.logdir)
            if not self.args.keep_tmp_files:
                data_dir.clean_tmp_files()

        tests_status = not bool(failures)
        if tests_status:
            return exit_codes.AVOCADO_ALL_OK
        else:
            return exit_codes.AVOCADO_TESTS_FAIL

    def run(self, urls=None, multiplex_files=None):
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
        :param multiplex_files: File that multiplexes a given test url.

        :return: Integer with overall job status. See
                 :mod:`avocado.core.exit_codes` for more information.
        """
        runtime.CURRENT_JOB = self
        try:
            return self._run(urls, multiplex_files)
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


class TestModuleRunner(object):

    """
    Convenience class to make avocado test modules executable.
    """

    def __init__(self):
        self.url = sys.argv[0]
        self.job = Job(standalone=True)
        if self.url is not None:
            sys.exit(self.job.run(urls=[self.url]))
        shutil.rmtree(self.job.logdir)
        sys.exit(exit_codes.AVOCADO_ALL_OK)

main = TestModuleRunner
