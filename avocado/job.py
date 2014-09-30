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
import sys
import signal
import time
import traceback
import Queue

from avocado.core import data_dir
from avocado.core import output
from avocado.core import status
from avocado.core import exceptions
from avocado.core import error_codes
from avocado.core import job_id
from avocado.utils import archive
from avocado.utils import path
from avocado import multiplexer
from avocado import test
from avocado import result
from avocado import sysinfo
from avocado import runtime
from avocado.plugins import xunit
from avocado.plugins import jsonresult

_NEW_ISSUE_LINK = 'https://github.com/avocado-framework/avocado/issues/new'


class TestRunner(object):

    """
    A test runner class that displays tests results.
    """
    DEFAULT_TIMEOUT = 60 * 60 * 24

    def __init__(self, job, test_result):
        """
        Creates an instance of TestRunner class.

        :param job: an instance of :class:`avocado.job.Job`.
        :param test_result: an instance of :class:`avocado.result.TestResult`.
        """
        self.job = job
        self.result = test_result

    def load_test(self, params, queue):
        """
        Resolve and load the test url from the the test shortname.

        This method should now be called by the test runner process.

        :param params: Dictionary with test params.
        :type params: dict
        :param queue: a Queue for communicating with the test runner
        :type queue: an instance of :class:`multiprocessing.Queue`.
        :return: an instance of :class:`avocado.test.Test`.
        """
        t_id = params.get('id')
        test_path = os.path.abspath(t_id)
        path_analyzer = path.PathInspector(test_path)
        module_name = os.path.basename(test_path).split('.')[0]
        if not os.path.exists(test_path):
            # Try to resolve test ID (keep compatibility)
            rel_path = '%s.py' % t_id
            test_path = os.path.join(data_dir.get_test_dir(), rel_path)
            if os.path.exists(test_path):
                path_analyzer = path.PathInspector(test_path)
                t_id = rel_path
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
                                           job=self.job,
                                           runner_queue=queue)

        else:
            test_class = test.DropinTest
            test_instance = test_class(path=test_path,
                                       base_logdir=self.job.logdir,
                                       job=self.job)

        return test_instance

    def run_test(self, params, queue):
        """
        Run a test instance in a subprocess.

        :param instance: Test instance.
        :type instance: :class:`avocado.test.Test` instance.
        :param queue: Multiprocess queue.
        :type queue: :class`multiprocessing.Queue` instance.
        """
        sys.stdout = output.LoggingFile(logger=logging.getLogger('avocado.test.stdout'))
        sys.sterr = output.LoggingFile(logger=logging.getLogger('avocado.test.stderr'))
        instance = self.load_test(params, queue)
        runtime.CURRENT_TEST = instance
        early_state = instance.get_state()
        queue.put(early_state)

        def timeout_handler(signum, frame):
            e_msg = "Timeout reached waiting for %s to end" % instance
            raise exceptions.TestTimeoutError(e_msg)

        def interrupt_handler(signum, frame):
            e_msg = "Test %s interrupted by user" % instance
            raise exceptions.TestInterruptedError(e_msg)

        signal.signal(signal.SIGUSR1, timeout_handler)
        signal.signal(signal.SIGINT, interrupt_handler)

        self.result.start_test(early_state)
        try:
            instance.run_avocado()
        finally:
            queue.put(instance.get_state())

    def _fill_aborted_test_state(self, test_state):
        """
        Fill details necessary to process aborted tests.

        :param test_state: Test state.
        :type test_state: dict
        :param time_started: When the test started
        """
        test_state['fail_reason'] = 'Test process aborted'
        test_state['status'] = exceptions.TestAbortError.status
        test_state['fail_class'] = exceptions.TestAbortError.__class__.__name__
        test_state['traceback'] = 'Traceback not available'
        with open(test_state['logfile'], 'r') as log_file_obj:
            test_state['text_output'] = log_file_obj.read()
        return test_state

    def run(self, params_list):
        """
        Run one or more tests and report with test result.

        :param params_list: a list of param dicts.

        :return: a list of test failures.
        """
        failures = []
        self.result.start_tests()
        q = multiprocessing.Queue()
        for params in params_list:
            p = multiprocessing.Process(target=self.run_test,
                                        args=(params, q,))

            cycle_timeout = 1
            time_started = time.time()
            test_state = None

            p.start()

            early_state = q.get()
            # At this point, the test is already initialized and we know
            # for sure if there's a timeout set.
            if 'timeout' in early_state['params'].keys():
                timeout = float(early_state['params']['timeout'])
            else:
                timeout = self.DEFAULT_TIMEOUT

            time_deadline = time_started + timeout

            ctrl_c_count = 0
            ignore_window = 2.0
            ignore_time_started = time.time()
            stage_1_msg_displayed = False
            stage_2_msg_displayed = False

            while True:
                try:
                    if time.time() >= time_deadline:
                        os.kill(p.pid, signal.SIGUSR1)
                        break

                    test_state = q.get(timeout=cycle_timeout)
                    if test_state is not None:
                        if not test_state['running']:
                            break
                        else:
                            self.job.result_proxy.notify_progress(True)
                            if test_state['paused']:
                                msg = test_state['paused_msg']
                                if msg:
                                    self.job.view.log_partial(msg)

                except Queue.Empty:
                    if p.is_alive():
                        if ctrl_c_count == 0:
                            self.job.result_proxy.notify_progress()
                    else:
                        break

                except KeyboardInterrupt:
                    time_elapsed = time.time() - ignore_time_started
                    ctrl_c_count += 1
                    if ctrl_c_count == 2:
                        if not stage_1_msg_displayed:
                            k_msg_1 = ("SIGINT sent to tests, waiting for their "
                                       "reaction")
                            k_msg_2 = ("Ignoring Ctrl+C during the next "
                                       "%d seconds so they can try to finish" %
                                       ignore_window)
                            k_msg_3 = ("A new Ctrl+C sent after that will send a "
                                       "SIGKILL to them")
                            self.job.view.notify(event='message', msg=k_msg_1)
                            self.job.view.notify(event='message', msg=k_msg_2)
                            self.job.view.notify(event='message', msg=k_msg_3)
                            stage_1_msg_displayed = True
                        ignore_time_started = time.time()
                    if (ctrl_c_count > 2) and (time_elapsed > ignore_window):
                        if not stage_2_msg_displayed:
                            k_msg_3 = ("Ctrl+C received after the ignore window. "
                                       "Killing all active tests")
                            self.job.view.notify(event='message', msg=k_msg_3)
                            stage_2_msg_displayed = True
                        os.kill(p.pid, signal.SIGKILL)

            # If test_state is None, the test was aborted before it ended.
            if test_state is None:
                try:
                    test_state = q.get(timeout=cycle_timeout)
                except Queue.Empty:
                    early_state['time_elapsed'] = time.time() - time_started
                    test_state = self._fill_aborted_test_state(early_state)
                    test_log = logging.getLogger('avocado.test')
                    test_log.error('ERROR %s -> TestAbortedError: '
                                   'Test aborted unexpectedly',
                                   test_state['name'])

            # don't process other tests from the list
            if ctrl_c_count > 0:
                self.job.view.notify(event='minor', msg='')
                break

            self.result.check_test(test_state)
            if not status.mapping[test_state['status']]:
                failures.append(test_state['name'])
        runtime.CURRENT_TEST = None
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
            self.unique_id = args.unique_job_id or job_id.create_unique_job_id()
        else:
            self.unique_id = job_id.create_unique_job_id()
        self.logdir = data_dir.get_job_logs_dir(self.args, self.unique_id)
        self.logfile = os.path.join(self.logdir, "job.log")
        self.idfile = os.path.join(self.logdir, "id")

        with open(self.idfile, 'w') as id_file_obj:
            id_file_obj.write("%s\n" % self.unique_id)

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
        self.view = output.View()

    def _make_test_runner(self):
        if hasattr(self.args, 'test_runner'):
            test_runner_class = self.args.test_runner
        else:
            test_runner_class = TestRunner

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

        op_set_stdout = self.result_proxy.output_plugins_using_stdout()
        if len(op_set_stdout) > 1:
            msg = ('Options %s are trying to use stdout simultaneously' %
                   " ".join(op_set_stdout))
            self.view.notify(event='error', msg=msg)
            msg = ('Please set at least one of them to a file to avoid '
                   'conflicts')
            self.view.notify(event='error', msg=msg)
            sys.exit(error_codes.numeric_status['AVOCADO_JOB_FAIL'])

        if not op_set_stdout and not self.args.silent:
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
        self.sysinfo_logger.start_job_hook()
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
                        for variant in variants:
                            var = variant[0]
                            if not var.value.has_key('id'):
                                var.value.update({'id': url})
                            params_list.append(var.environment)
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
