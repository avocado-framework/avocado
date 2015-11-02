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
# Authors: Lucas Meneghel Rodrigues <lmr@redhat.com>
#          Ruda Moura <rmoura@redhat.com>

"""
Test runner module.
"""

import logging
import multiprocessing
from multiprocessing import queues
import os
import signal
import sys
import time

from . import test
from . import exceptions
from . import output
from . import status
from . import exit_codes
from .loader import loader
from ..utils import wait
from ..utils import stacktrace
from ..utils import runtime


class TestRunner(object):

    """
    A test runner class that displays tests results.
    """
    DEFAULT_TIMEOUT = 86400

    def __init__(self, job, test_result):
        """
        Creates an instance of TestRunner class.

        :param job: an instance of :class:`avocado.core.job.Job`.
        :param test_result: an instance of :class:`avocado.core.result.TestResult`.
        """
        self.job = job
        self.result = test_result

    def _run_test(self, test_factory, queue):
        """
        Run a test instance.

        :param test_factory: Test factory (test class and parameters).
        :type test_factory: tuple of :class:`avocado.core.test.Test` and dict.
        :param queue: Multiprocess queue.
        :type queue: :class`multiprocessing.Queue` instance.
        """
        def timeout_handler(signum, frame):
            e_msg = "Timeout reached waiting for %s to end" % instance
            raise exceptions.TestTimeoutError(e_msg)

        def interrupt_handler(signum, frame):
            e_msg = "Test %s interrupted by user" % instance
            raise exceptions.TestInterruptedError(e_msg)
        logger_list_stdout = [logging.getLogger('avocado.test.stdout'),
                              logging.getLogger('avocado.test'),
                              logging.getLogger('paramiko')]
        logger_list_stderr = [logging.getLogger('avocado.test.stderr'),
                              logging.getLogger('avocado.test'),
                              logging.getLogger('paramiko')]
        sys.stdout = output.LoggingFile(logger=logger_list_stdout)
        sys.stderr = output.LoggingFile(logger=logger_list_stderr)

        try:
            instance = loader.load_test(test_factory)
            if instance.runner_queue is None:
                instance.runner_queue = queue
            runtime.CURRENT_TEST = instance
            early_state = instance.get_state()
            queue.put(early_state)
        except Exception:
            exc_info = sys.exc_info()
            app_logger = logging.getLogger('avocado.app')
            app_logger.exception('Exception loading test')
            tb_info = stacktrace.tb_info(exc_info)
            queue.put({'load_exception': tb_info})
            return

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

    def run_test(self, test_factory, queue, failures, job_deadline=0):
        """
        Run a test instance inside a subprocess.

        :param test_factory: Test factory (test class and parameters).
        :type test_factory: tuple of :class:`avocado.core.test.Test` and dict.
        :param queue: Multiprocess queue.
        :type queue: :class`multiprocessing.Queue` instance.
        :param failures: Store tests failed.
        :type failures: list.
        :param job_deadline: Maximum time to execute.
        :type job_deadline: int.
        """
        proc = multiprocessing.Process(target=self._run_test,
                                       args=(test_factory, queue,))

        cycle_timeout = 1
        time_started = time.time()
        test_state = None

        proc.start()

        end = time.time() + 10
        while queue.empty():
            if not proc.is_alive() and queue.empty():
                raise exceptions.TestError("Process died before it pushed "
                                           "early state.")
            if time.time() > end:
                msg = ("Unable to receive test's early-state in 10s, "
                       "something wrong happened probably in the "
                       "avocado framework.")
                os.kill(proc.pid, 9)
                raise exceptions.TestError(msg)
            time.sleep(0)
        early_state = queue.get()

        if 'load_exception' in early_state:
            raise exceptions.TestError('Avocado crashed during test load. '
                                       'Some reports might have not been '
                                       'generated. Aborting...')

        # At this point, the test is already initialized and we know
        # for sure if there's a timeout set.
        timeout = float(early_state.get('params', {}).get('timeout') or
                        self.DEFAULT_TIMEOUT)

        test_deadline = time_started + timeout
        if job_deadline > 0:
            deadline = min(test_deadline, job_deadline)
        else:
            deadline = test_deadline

        ctrl_c_count = 0
        ignore_window = 2.0
        ignore_time_started = time.time()
        stage_1_msg_displayed = False
        stage_2_msg_displayed = False
        first = 0.01
        step = 0.1

        while True:
            try:
                if time.time() >= deadline:
                    os.kill(proc.pid, signal.SIGUSR1)
                    break
                wait.wait_for(lambda: not queue.empty() or not proc.is_alive(),
                              cycle_timeout, first, step)
                if not queue.empty():
                    test_state = queue.get()
                    if not test_state['running']:
                        break
                    else:
                        self.job.result_proxy.notify_progress(False)
                        if test_state['paused']:
                            msg = test_state['paused_msg']
                            if msg:
                                self.job.view.notify(event='partial', msg=msg)

                elif proc.is_alive():
                    if ctrl_c_count == 0:
                        if test_state and not test_state.get('running'):
                            self.job.result_proxy.notify_progress(False)
                        else:
                            self.job.result_proxy.notify_progress(True)
                else:
                    break
            except KeyboardInterrupt:
                time_elapsed = time.time() - ignore_time_started
                ctrl_c_count += 1
                if ctrl_c_count == 1:
                    if not stage_1_msg_displayed:
                        k_msg_1 = ('\nInterrupt requested. Waiting %d seconds '
                                   'for test to finish '
                                   '(ignoring new Ctrl+C until then)' %
                                   ignore_window)
                        self.job.view.notify(event='message', msg=k_msg_1)
                        stage_1_msg_displayed = True
                    ignore_time_started = time.time()
                if (ctrl_c_count > 1) and (time_elapsed > ignore_window):
                    if not stage_2_msg_displayed:
                        k_msg_2 = "Killing test subprocess %s" % proc.pid
                        self.job.view.notify(event='message', msg=k_msg_2)
                        stage_2_msg_displayed = True
                    os.kill(proc.pid, signal.SIGKILL)

        # If test_state is None, the test was aborted before it ended.
        if test_state is None:
            if proc.is_alive() and wait.wait_for(lambda: not queue.empty(),
                                                 cycle_timeout, first, step):
                test_state = queue.get()
            else:
                early_state['time_elapsed'] = time.time() - time_started
                test_state = self._fill_aborted_test_state(early_state)
                test_log = logging.getLogger('avocado.test')
                test_log.error('ERROR %s -> TestAbortedError: '
                               'Test aborted unexpectedly',
                               test_state['name'])

        # don't process other tests from the list
        if ctrl_c_count > 0:
            self.job.view.notify(event='minor', msg='')

        self.result.check_test(test_state)
        if not status.mapping[test_state['status']]:
            failures.append(test_state['name'])

        if ctrl_c_count > 0:
            return False
        return True

    def run_suite(self, test_suite, mux, timeout=0):
        """
        Run one or more tests and report with test result.

        :param test_suite: a list of tests to run.
        :param mux: the multiplexer.
        :param timeout: maximum amount of time (in seconds) to execute.
        :return: a list of test failures.
        """
        failures = []
        if self.job.sysinfo is not None:
            self.job.sysinfo.start_job_hook()
        self.result.start_tests()
        queue = queues.SimpleQueue()

        if timeout > 0:
            deadline = time.time() + timeout
        else:
            deadline = None

        for test_template in test_suite:
            test_template[1]['base_logdir'] = self.job.logdir
            test_template[1]['job'] = self.job
            break_loop = False
            for test_factory in mux.itertests(test_template):
                if deadline is not None and time.time() > deadline:
                    test_parameters = test_factory[1]
                    if 'methodName' in test_parameters:
                        del test_parameters['methodName']
                    test_factory = (test.TimeOutSkipTest, test_parameters)
                    break_loop = not self.run_test(test_factory, queue,
                                                   failures)
                    if break_loop:
                        break
                else:
                    break_loop = not self.run_test(test_factory, queue, failures,
                                                   deadline)
                    if break_loop:
                        break
            runtime.CURRENT_TEST = None
            if break_loop:
                break
        self.result.end_tests()
        if self.job.sysinfo is not None:
            self.job.sysinfo.end_job_hook()
        return failures
