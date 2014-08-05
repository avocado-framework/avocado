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
Module that describes a sequence of automated test operations.
"""

import argparse
import imp
import logging
import multiprocessing
import os
import signal
import sys
import time
import traceback
import uuid

from avocado.core import data_dir
from avocado.core import output
from avocado.core import status
from avocado.core import exceptions
from avocado.core import error_codes
from avocado.utils import archive
from avocado.utils import path
from avocado import multiplex_config
from avocado import test
from avocado import result
from avocado import sysinfo
from avocado.plugins import xunit
from avocado.plugins import jsonresult

_NEW_ISSUE_LINK = 'https://github.com/avocado-framework/avocado/issues/new'


class TestRunner(object):

    """
    A test runner class that displays tests results.
    """

    def __init__(self, job, test_result):
        """
        Creates an instance of TestRunner class.

        :param job: an instance of :class:`avocado.job.Job`.
        :param test_result: an instance of :class:`avocado.result.TestResult`.
        """
        self.job = job
        self.result = test_result

    def load_test(self, params):
        """
        Resolve and load the test url from the the test shortname.

        :param params: Dictionary with test params.
        :type params: dict
        :return: an instance of :class:`avocado.test.Test`.
        """
        t_id = params.get('id')
        test_path = os.path.abspath(t_id)
        path_analyzer = path.PathInspector(test_path)
        module_name = os.path.basename(test_path).split('.')[0]
        if not os.path.exists(test_path):
            # Try to resolve test ID (keep compatibility)
            test_path = os.path.join(data_dir.get_test_dir(), '%s.py' % t_id)
            if os.path.exists(test_path):
                path_analyzer = path.PathInspector(test_path)
            else:
                test_class = test.MissingTest
                test_instance = test_class(name=t_id,
                                           base_logdir=self.job.logdir,
                                           params=params,
                                           job=self.job)
                return test_instance

        if path_analyzer.is_python():
            try:
                test_module_dir = os.path.dirname(test_path)
                f, p, d = imp.find_module(module_name, [test_module_dir])
                test_module = imp.load_module(module_name, f, p, d)
                f.close()
                test_class = getattr(test_module, module_name)
            except ImportError:
                test_class = test.MissingTest
            finally:
                test_instance = test_class(name=t_id,
                                           base_logdir=self.job.logdir,
                                           params=params,
                                           job=self.job)

        else:
            test_class = test.DropinTest
            test_instance = test_class(path=test_path,
                                       base_logdir=self.job.logdir,
                                       job=self.job)

        return test_instance

    def run_test(self, instance, queue):
        """
        Run a test instance in a subprocess.

        :param instance: Test instance.
        :type instance: :class:`avocado.test.Test` instance.
        :param queue: Multiprocess queue.
        :type queue: :class`multiprocessing.Queue` instance.
        """
        def timeout_handler(signum, frame):
            e_msg = "Timeout reached waiting for %s to end" % instance
            raise exceptions.TestTimeoutError(e_msg)

        signal.signal(signal.SIGUSR1, timeout_handler)
        try:
            instance.run_avocado()
        finally:
            queue.put(instance)

    def run(self, params_list):
        """
        Run one or more tests and report with test result.

        :param params_list: a list of param dicts.

        :return: a list of test failures.
        """
        def send_signal(p, sig):
            if p.exitcode is None:
                os.kill(p.pid, sig)
                time.sleep(0.1)

        failures = []
        self.result.start_tests()
        q = multiprocessing.Queue()
        for params in params_list:
            test_instance = self.load_test(params)
            self.result.start_test(test_instance)
            p = multiprocessing.Process(target=self.run_test,
                                        args=(test_instance, q,))
            p.start()
            # The test timeout can come from:
            # 1) Test params dict (params)
            # 2) Test default params dict (test_instance.params.timeout)
            timeout = params.get('timeout')
            if timeout is None:
                if hasattr(test_instance.params, 'timeout'):
                    timeout = test_instance.params.timeout
            if timeout is not None:
                timeout = float(timeout)
            # Wait for the test to end for [timeout] s
            try:
                test_instance = q.get(timeout=timeout)
            except Exception:
                # If there's nothing inside the queue after timeout, the process
                # must be terminated.
                send_signal(p, signal.SIGUSR1)
                test_instance = q.get()

            self.result.check_test(test_instance)
            if not status.mapping[test_instance.status]:
                failures.append(test_instance.name)
        self.result.end_tests()
        return failures


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
            self.unique_id = args.unique_id or str(uuid.uuid4())
        else:
            self.unique_id = str(uuid.uuid4())
        self.logdir = data_dir.get_job_logs_dir(self.args)
        self.logfile = os.path.join(self.logdir, "debug.log")
        if self.args is not None:
            self.loglevel = args.log_level or logging.DEBUG
            self.multiplex_file = args.multiplex_file
        else:
            self.loglevel = logging.DEBUG
            self.multiplex_file = None
        self.test_dir = data_dir.get_test_dir()
        self.test_index = 1
        self.status = "RUNNING"
        self.result_proxy = result.TestResultProxy()
        self.sysinfo_dir = path.init_dir(self.logdir, 'sysinfo')
        self.sysinfo_logger = sysinfo.SysInfo(basedir=self.sysinfo_dir)
        self.output_manager = output.OutputManager()
        # Let plugins populate this. In case there's data here, it is
        # going to be passed to every test's params.
        self.extra_params = {}

    def update_extra_params(self):
        """
        Populate with options from your test runner plugin.

        Runner plugins may override this method. It will populate the extra
        params dict with data passed directly from the plugin options. Those
        options are going to be passed to each new test.
        """
        pass

    def _make_test_runner(self):
        if hasattr(self.args, 'test_runner'):
            test_runner_class = self.args.test_runner
        else:
            test_runner_class = TestRunner

        self.test_runner = test_runner_class(job=self,
                                             test_result=self.result_proxy)

    def _set_output_plugins(self):
        plugin_using_stdout = None
        e_msg = ("Avocado could not set %s and %s both to output to stdout. ")
        e_msg_2 = ("Please set the output flag of one of them to a file "
                   "to avoid conflicts.")
        for key in self.args.__dict__:
            if key.endswith('_result'):
                result_class = getattr(self.args, key)
                if issubclass(result_class, result.TestResult):
                    result_plugin = result_class(self.output_manager,
                                                 self.args)
                    if result_plugin.output == '-':
                        if plugin_using_stdout is not None:
                            e_msg %= (plugin_using_stdout.output_option,
                                      result_plugin.output_option)
                            self.output_manager.log_fail_header(e_msg)
                            self.output_manager.log_fail_header(e_msg_2)
                            sys.exit(error_codes.numeric_status['AVOCADO_JOB_FAIL'])
                        else:
                            plugin_using_stdout = result_plugin
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
        xunit_plugin = xunit.xUnitTestResult(self.output_manager, args)
        self.result_proxy.add_output_plugin(xunit_plugin)

        # Setup the json plugin to output to the debug directory
        json_file = os.path.join(self.logdir, 'results.json')
        args = argparse.Namespace()
        args.json_output = json_file
        json_plugin = jsonresult.JSONTestResult(self.output_manager, args)
        self.result_proxy.add_output_plugin(json_plugin)

        # If there are no active output plugins besides xunit and json,
        # set up the human output.
        if len(self.result_proxy.output_plugins) == 2:
            human_plugin = result.HumanTestResult(self.output_manager, self.args)
            self.result_proxy.add_output_plugin(human_plugin)

    def run_unhandled(self, urls=None, multiplex_file=None):
        """
        Runs a list of test URLs to its completion without exception handling.

        :param urls: String with tests to run.
        :param multiplex_file: File that multiplexes a given test url.

        :return: Integer with overall job status. See
                 :mod:`avocado.core.error_codes` for more information.
        :raise: Any exception (avocado crashed), or
                :class:`avocado.core.exceptions.JobBaseException` errors,
                that configure a job failure.
        """
        self.update_extra_params()
        self.sysinfo_logger.start_job_hook()
        params_list = []
        if urls is None:
            if self.args and self.args.url is not None:
                urls = self.args.url.split()
        else:
            if isinstance(urls, str):
                urls = urls.split()

        if urls is not None:
            for url in urls:
                dct = {'id': url}
                if self.extra_params:
                    dct.update(self.extra_params)
                params_list.append(dct)

        if multiplex_file is None:
            if self.args and self.args.multiplex_file is not None:
                multiplex_file = os.path.abspath(self.args.multiplex_file)
        else:
            multiplex_file = os.path.abspath(multiplex_file)

        if multiplex_file is not None:
            params_list = []
            if urls is not None:
                for url in urls:
                    test_module = os.path.basename(url).split('.')[0]
                    parser = multiplex_config.Parser(multiplex_file)
                    parser.only_filter(test_module)
                    dcts = [d for d in parser.get_dicts()]
                    if dcts:
                        for dct in dcts:
                            dct['id'] = url
                            if self.extra_params:
                                dct.update(self.extra_params)
                            params_list.append(dct)
                    else:
                        params_list.append({'id': url})
            else:
                e_msg = "Empty test ID. A test path or alias must be provided"
                raise exceptions.OptionValidationError(e_msg)

        if self.args is not None:
            self.args.test_result_total = len(params_list)

        self._make_test_result()
        self._make_test_runner()

        self.output_manager.start_file_logging(self.logfile,
                                               self.loglevel)
        self.output_manager.logfile = self.logfile
        failures = self.test_runner.run(params_list)
        self.output_manager.stop_file_logging()
        self.sysinfo_logger.end_job_hook()
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
            return self.run_unhandled(urls, multiplex_file)
        except exceptions.JobBaseException, details:
            self.status = details.status
            fail_class = details.__class__.__name__
            self.output_manager.log_fail_header('Avocado job failed: %s: %s' %
                                                (fail_class, details))
            return error_codes.numeric_status['AVOCADO_JOB_FAIL']
        except exceptions.OptionValidationError, details:
            self.output_manager.log_fail_header(str(details))
            return error_codes.numeric_status['AVOCADO_JOB_FAIL']

        except Exception, details:
            self.status = "ERROR"
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tb_info = traceback.format_exception(exc_type, exc_value,
                                                 exc_traceback.tb_next)
            fail_class = details.__class__.__name__
            self.output_manager.log_fail_header('Avocado crashed: %s: %s' %
                                                (fail_class, details))
            for line in tb_info:
                self.output_manager.error(line)
            self.output_manager.log_fail_header('Please include the traceback '
                                                'info and command line used on '
                                                'your bug report')
            self.output_manager.log_fail_header('Report bugs visiting %s' %
                                                _NEW_ISSUE_LINK)
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
