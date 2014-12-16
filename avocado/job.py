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

from avocado import multiplexer
from avocado import result
from avocado import test
from avocado import runner
from avocado.core import data_dir
from avocado.core import error_codes
from avocado.core import exceptions
from avocado.core import job_id
from avocado.core import output
from avocado.plugins import jsonresult
from avocado.plugins import xunit
from avocado.utils import archive

try:
    from avocado.plugins import htmlresult
    HTML_REPORT_SUPPORT = True
except ImportError:
    HTML_REPORT_SUPPORT = False

_NEW_ISSUE_LINK = 'https://github.com/avocado-framework/avocado/issues/new'


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
        self.args = args
        if args is not None:
            self.unique_id = args.unique_job_id or job_id.create_unique_job_id()
        else:
            self.unique_id = job_id.create_unique_job_id()
        self.logdir = data_dir.get_job_logs_dir(self.args, self.unique_id)
        self.logfile = os.path.join(self.logdir, "job.log")
        self.idfile = os.path.join(self.logdir, "id")

        with open(self.idfile, 'w') as id_file_obj:
            id_file_obj.write("%s\n" % self.unique_id)

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
            self.multiplex_file = args.multiplex_file
            self.show_job_log = args.show_job_log
            self.silent = args.silent
        else:
            self.loglevel = logging.DEBUG
            self.multiplex_file = None
            self.show_job_log = False
            self.silent = False
        if self.show_job_log:
            if not self.silent:
                test_logger = logging.getLogger('avocado.test')
                output.add_console_handler(test_logger)
                test_logger.setLevel(self.loglevel)
        self.test_dir = data_dir.get_test_dir()
        self.test_index = 1
        self.status = "RUNNING"
        self.result_proxy = result.TestResultProxy()
        self.view = output.View(app_args=self.args)

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
            sys.exit(error_codes.numeric_status['AVOCADO_JOB_FAIL'])

        if not op_set_stdout:
            human_plugin = result.HumanTestResult(self.view, self.args)
            self.result_proxy.add_output_plugin(human_plugin)

    def _run(self, urls=None, multiplex_file=None):
        """
        Unhandled job method. Runs a list of test URLs to its completion.

        :param urls: String with tests to run.
        :param multiplex_file: File that multiplexes a given test url.

        :return: Integer with overall job status. See
                 :mod:`avocado.core.error_codes` for more information.
        :raise: Any exception (avocado crashed), or
                :class:`avocado.core.exceptions.JobBaseException` errors,
                that configure a job failure.
        """
        params_list = []
        if urls is None:
            if self.args and self.args.url:
                urls = self.args.url
        else:
            if isinstance(urls, str):
                urls = urls.split()

        if urls is not None:
            for url in urls:
                params_list.append({'id': url})
        else:
            e_msg = "Empty test ID. A test path or alias must be provided"
            raise exceptions.OptionValidationError(e_msg)

        if multiplex_file is None:
            if self.args and self.args.multiplex_file is not None:
                multiplex_file = os.path.abspath(self.args.multiplex_file)
        else:
            multiplex_file = os.path.abspath(multiplex_file)

        if multiplex_file is not None:
            params_list = []
            if urls is not None:
                for url in urls:
                    try:
                        variants = multiplexer.create_variants_from_yaml(open(multiplex_file),
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
                            env.update({'id': url})
                            params_list.append(env)
                            tag += 1
                    else:
                        params_list.append({'id': url})

        if not params_list:
            e_msg = "Test(s) with empty parameter list or the number of variants is zero"
            raise exceptions.OptionValidationError(e_msg)

        if self.args is not None:
            self.args.test_result_total = len(params_list)

        self._make_test_result()
        self._make_test_runner()

        self.view.start_file_logging(self.logfile,
                                     self.loglevel,
                                     self.unique_id)
        self.view.logfile = self.logfile
        failures = self.test_runner.run(params_list)
        self.view.stop_file_logging()
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
            return error_codes.numeric_status['AVOCADO_ALL_OK']
        else:
            return error_codes.numeric_status['AVOCADO_TESTS_FAIL']

    def run(self, urls=None, multiplex_file=None):
        """
        Handled main job method. Runs a list of test URLs to its completion.

        Note that the behavior is as follows:

        * If urls is provided alone, just make a simple list with no specific
          params (all tests use default params).
        * If urls and multiplex_file are provided, multiplex provides params
          and variants to all tests it can.
        * If multiplex_file is provided alone, just use the matrix produced by
          the file

        The test runner figures out which tests need to be run on an empty urls
        list by assuming the first component of the shortname is the test url.

        :param urls: String with tests to run.
        :param multiplex_file: File that multiplexes a given test url.

        :return: Integer with overall job status. See
                 :mod:`avocado.core.error_codes` for more information.
        """
        try:
            return self._run(urls, multiplex_file)
        except exceptions.JobBaseException, details:
            self.status = details.status
            fail_class = details.__class__.__name__
            self.view.notify(event='error', msg=('Avocado job failed: %s: %s' %
                                                 (fail_class, details)))
            return error_codes.numeric_status['AVOCADO_JOB_FAIL']
        except exceptions.OptionValidationError, details:
            self.view.notify(event='error', msg=str(details))
            return error_codes.numeric_status['AVOCADO_JOB_FAIL']

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
            return error_codes.numeric_status['AVOCADO_CRASH']


class TestModuleRunner(object):

    """
    Convenience class to make avocado test modules executable.
    """

    def __init__(self, module='__main__'):
        if isinstance(module, basestring):
            self.module = __import__(module)
            for part in module.split('.')[1:]:
                self.module = getattr(self.module, part)
        else:
            self.module = module
        self.url = None
        for key, value in self.module.__dict__.iteritems():
            try:
                if issubclass(value, test.Test):
                    self.url = key
            except TypeError:
                pass
        self.job = Job()
        if self.url is not None:
            sys.exit(self.job.run(urls=[self.url]))
        sys.exit(error_codes.numeric_status['AVOCADO_ALL_OK'])

main = TestModuleRunner
