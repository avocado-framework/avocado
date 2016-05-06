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
from .loader import loader
from .status import mapping
from ..utils import wait
from ..utils import stacktrace
from ..utils import runtime
from ..utils import process

TEST_LOG = logging.getLogger("avocado.test")
APP_LOG = logging.getLogger("avocado.app")


class TestStatus(object):

    """
    Test status handler
    """

    def __init__(self, job, queue):
        """
        :param job: Associated job
        :param queue: test message queue
        """
        self.job = job
        self.queue = queue
        self._early_status = None
        self.status = {}
        self.interrupt = None

    def _get_msg_from_queue(self):
        """
        Helper method to handle safely getting messages from the queue.

        :return: Message, None if exception happened.
        :rtype: dict
        """
        try:
            return self.queue.get()
        # Let's catch all exceptions, since errors here mean a
        # crash in avocado.
        except Exception as details:
            APP_LOG.error("\nError receiving message from test: %s -> %s",
                          details.__class__, details)
            stacktrace.log_exc_info(sys.exc_info(),
                                    'avocado.app.tracebacks')
            return None

    @property
    def early_status(self):
        """
        Get early status
        """
        if self._early_status:
            return self._early_status
        else:
            queue = []
            while not self.queue.empty():
                msg = self._get_msg_from_queue()
                if msg is None:
                    break
                if "early_status" in msg:
                    self._early_status = msg
                    for _ in queue:     # Return all unprocessed messages back
                        self.queue.put(_)
                    return msg
                else:   # Not an early_status message
                    queue.append(msg)

    def __getattribute__(self, name):
        # Update state before returning the value
        if name in ("status", "interrupt"):
            self._tick()
        return super(TestStatus, self).__getattribute__(name)

    def wait_for_early_status(self, proc, timeout):
        """
        Wait until early_status is obtained
        :param proc: test process
        :param timeout: timeout for early_state
        :raise exceptions.TestError: On timeout/error
        """
        end = time.time() + timeout
        while not self.early_status:
            if not proc.is_alive():
                if not self.early_status:
                    raise exceptions.TestError("Process died before it pushed "
                                               "early test_status.")
            if time.time() > end and not self.early_status:
                msg = ("Unable to receive test's early-status in %ss, "
                       "something wrong happened probably in the "
                       "avocado framework." % timeout)
                os.kill(proc.pid, signal.SIGKILL)
                raise exceptions.TestError(msg)
            time.sleep(0)

    def _tick(self):
        """
        Process the queue and update current status
        """
        while not self.queue.empty():
            msg = self._get_msg_from_queue()
            if msg is None:
                break
            if "func_at_exit" in msg:
                self.job.funcatexit.register(msg["func_at_exit"],
                                             msg.get("args", tuple()),
                                             msg.get("kwargs", {}),
                                             msg.get("once", False))
            elif not msg.get("running", True):
                self.status = msg
                self.interrupt = True
            elif "paused" in msg:
                self.status = msg
                self.job.result_proxy.notify_progress(False)
                if msg['paused']:
                    reason = msg['paused_msg']
                    if reason:
                        self.job.log.warning(reason)
            else:       # test_status
                self.status = msg

    def abort(self, proc, started, timeout, first, step):
        """
        Handle job abortion
        :param proc: The test's process
        :param started: Time when the test started
        :param timeout: Timeout for waiting on status
        :param first: Delay before first check
        :param step: Step between checks for the status
        """
        if proc.is_alive() and wait.wait_for(lambda: self.status, timeout,
                                             first, step):
            status = self.status
        else:
            test_state = self.early_status
            test_state['time_elapsed'] = time.time() - started
            test_state['fail_reason'] = 'Test process aborted'
            test_state['status'] = exceptions.TestAbortError.status
            test_state['fail_class'] = (exceptions.TestAbortError.__class__.
                                        __name__)
            test_state['traceback'] = 'Traceback not available'
            with open(test_state['logfile'], 'r') as log_file_obj:
                test_state['text_output'] = log_file_obj.read()
            TEST_LOG.error('ERROR %s -> TestAbortedError: '
                           'Test aborted unexpectedly',
                           test_state['name'])
            status = test_state
        if proc.is_alive():
            for _ in xrange(5):     # I really want to destroy it
                os.kill(proc.pid, signal.SIGKILL)
                if not proc.is_alive():
                    break
                time.sleep(0.1)
            else:
                raise exceptions.TestError("Unable to destroy test's process "
                                           "(%s)" % proc.pid)
        return status


class TestRunner(object):

    """
    A test runner class that displays tests results.
    """
    DEFAULT_TIMEOUT = 86400

    def __init__(self, job, test_result):
        """
        Creates an instance of TestRunner class.

        :param job: an instance of :class:`avocado.core.job.Job`.
        :param test_result: an instance of
                            :class:`avocado.core.result.TestResultProxy`.
        """
        self.job = job
        self.result = test_result
        self.sigstopped = False

    def _run_test(self, test_factory, queue):
        """
        Run a test instance.

        This code is the first thing that runs inside a new process, known here
        as the test process. It communicates to the test runner by using
        :param:`queue`. It's important that this early state is given to the
        test runner in a reliable way.

        :param test_factory: Test factory (test class and parameters).
        :type test_factory: tuple of :class:`avocado.core.test.Test` and dict.
        :param queue: Multiprocess queue.
        :type queue: :class:`multiprocessing.Queue` instance.
        """
        signal.signal(signal.SIGTSTP, signal.SIG_IGN)
        logger_list_stdout = [logging.getLogger('avocado.test.stdout'),
                              TEST_LOG,
                              logging.getLogger('paramiko')]
        logger_list_stderr = [logging.getLogger('avocado.test.stderr'),
                              TEST_LOG,
                              logging.getLogger('paramiko')]
        sys.stdout = output.LoggingFile(logger=logger_list_stdout)
        sys.stderr = output.LoggingFile(logger=logger_list_stderr)

        def sigterm_handler(signum, frame):     # pylint: disable=W0613
            """ Produce traceback on SIGTERM """
            raise SystemExit("Test interrupted by SIGTERM")

        signal.signal(signal.SIGTERM, sigterm_handler)

        instance = loader.load_test(test_factory)
        if instance.runner_queue is None:
            instance.runner_queue = queue
        runtime.CURRENT_TEST = instance
        early_state = instance.get_state()
        early_state['early_status'] = True
        queue.put(early_state)

        self.result.start_test(early_state)
        try:
            instance.run_avocado()
        finally:
            queue.put(instance.get_state())

    def setup(self):
        """
        (Optional) initialization method for the test runner
        """
        pass

    def tear_down(self):
        """
        (Optional) cleanup method for the test runner
        """
        pass

    def run_test(self, test_factory, queue, summary, job_deadline=0):
        """
        Run a test instance inside a subprocess.

        :param test_factory: Test factory (test class and parameters).
        :type test_factory: tuple of :class:`avocado.core.test.Test` and dict.
        :param queue: Multiprocess queue.
        :type queue: :class`multiprocessing.Queue` instance.
        :param summary: Contains types of test failures.
        :type summary: set.
        :param job_deadline: Maximum time to execute.
        :type job_deadline: int.
        """
        proc = None
        sigtstp = multiprocessing.Lock()

        def sigtstp_handler(signum, frame):     # pylint: disable=W0613
            """ SIGSTOP all test processes on SIGTSTP """
            if not proc:    # Ignore ctrl+z when proc not yet started
                return
            with sigtstp:
                msg = "ctrl+z pressed, %%s test (%s)" % proc.pid
                if self.sigstopped:
                    APP_LOG.info("\n" + msg, "resumming")
                    TEST_LOG.info(msg, "resumming")
                    process.kill_process_tree(proc.pid, signal.SIGCONT, False)
                    self.sigstopped = False
                else:
                    APP_LOG.info("\n" + msg, "stopping")
                    TEST_LOG.info(msg, "stopping")
                    process.kill_process_tree(proc.pid, signal.SIGSTOP, False)
                    self.sigstopped = True

        signal.signal(signal.SIGTSTP, sigtstp_handler)

        proc = multiprocessing.Process(target=self._run_test,
                                       args=(test_factory, queue,))
        test_status = TestStatus(self.job, queue)

        cycle_timeout = 1
        time_started = time.time()
        proc.start()

        test_status.wait_for_early_status(proc, 10)

        # At this point, the test is already initialized and we know
        # for sure if there's a timeout set.
        timeout = test_status.early_status.get('timeout')
        timeout = float(timeout or self.DEFAULT_TIMEOUT)

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
        abort_reason = None

        while True:
            try:
                if time.time() >= deadline:
                    abort_reason = "Timeout reached"
                    try:
                        os.kill(proc.pid, signal.SIGTERM)
                    except OSError:
                        pass
                    break
                wait.wait_for(lambda: not queue.empty() or not proc.is_alive(),
                              cycle_timeout, first, step)
                if test_status.interrupt:
                    break
                if proc.is_alive():
                    if ctrl_c_count == 0:
                        if (test_status.status.get('running') or
                                self.sigstopped):
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
                        abort_reason = "Interrupted by ctrl+c"
                        self.job.log.debug("\nInterrupt requested. Waiting %d "
                                           "seconds for test to finish "
                                           "(ignoring new Ctrl+C until then)",
                                           ignore_window)
                        stage_1_msg_displayed = True
                    ignore_time_started = time.time()
                if (ctrl_c_count > 1) and (time_elapsed > ignore_window):
                    if not stage_2_msg_displayed:
                        abort_reason = "Interrupted by ctrl+c (multiple-times)"
                        self.job.log.debug("Killing test subprocess %s",
                                           proc.pid)
                        stage_2_msg_displayed = True
                    os.kill(proc.pid, signal.SIGKILL)

        # Get/update the test status
        if test_status.status:
            test_state = test_status.status
        else:
            test_state = test_status.abort(proc, time_started, cycle_timeout,
                                           first, step)

        # Try to log the timeout reason to test's results and update test_state
        if abort_reason:
            TEST_LOG.error(abort_reason)
            test_log = test_state.get("logfile")
            if test_log:
                open(test_log, "a").write("\nRUNNER: " + abort_reason + "\n")
            if test_state.get("text_output"):
                test_state["text_output"] += "\nRUNNER: " + abort_reason + "\n"
            else:
                test_state["text_output"] = abort_reason
            test_state["status"] = "INTERRUPTED"
            test_state["fail_reason"] = abort_reason
            test_state["fail_class"] = "RUNNER"

        # don't process other tests from the list
        if ctrl_c_count > 0:
            self.job.log.debug('')

        # Make sure the test status is correct
        if test_state.get('status') not in status.user_facing_status:
            test_state['fail_reason'] = ("Test reports unsupported test "
                                         "status %s.\nOriginal fail_reason: %s"
                                         "\nOriginal fail_class: %s"
                                         % (test_state.get('status'),
                                            test_state.get('fail_reason'),
                                            test_state.get('fail_class')))
            test_state['fail_class'] = "RUNNER"
            test_state['status'] = 'ERROR'

        self.result.check_test(test_state)
        if test_state['status'] == "INTERRUPTED":
            summary.add("INTERRUPTED")
        elif not mapping[test_state['status']]:
            summary.add("FAIL")

        if ctrl_c_count > 0:
            return False
        return True

    def run_suite(self, test_suite, mux, timeout=0, replay_map=None,
                  test_result_total=0):
        """
        Run one or more tests and report with test result.

        :param test_suite: a list of tests to run.
        :param mux: the multiplexer.
        :param timeout: maximum amount of time (in seconds) to execute.
        :return: a set with types of test failures.
        """
        summary = set()
        if self.job.sysinfo is not None:
            self.job.sysinfo.start_job_hook()
        self.result.start_tests()
        queue = queues.SimpleQueue()

        if timeout > 0:
            deadline = time.time() + timeout
        else:
            deadline = None

        no_digits = len(str(test_result_total))

        index = -1
        try:
            for test_template in test_suite:
                test_template[1]['base_logdir'] = self.job.logdir
                test_template[1]['job'] = self.job
                break_loop = False
                for test_factory, variant in mux.itertests(test_template):
                    index += 1
                    test_parameters = test_factory[1]
                    name = test_parameters.get("name")
                    test_parameters["name"] = test.TestName(index + 1, name,
                                                            variant,
                                                            no_digits)
                    if deadline is not None and time.time() > deadline:
                        summary.add('INTERRUPTED')
                        if 'methodName' in test_parameters:
                            del test_parameters['methodName']
                        test_factory = (test.TimeOutSkipTest, test_parameters)
                        break_loop = not self.run_test(test_factory, queue,
                                                       summary)
                        if break_loop:
                            break
                    else:
                        if (replay_map is not None and
                                replay_map[index] is not None):
                            test_parameters["methodName"] = "test"
                            test_factory = (replay_map[index], test_parameters)

                        break_loop = not self.run_test(test_factory, queue,
                                                       summary, deadline)
                        if break_loop:
                            break
                runtime.CURRENT_TEST = None
                if break_loop:
                    break
        except KeyboardInterrupt:
            TEST_LOG.error('Job interrupted by ctrl+c.')
            summary.add('INTERRUPTED')

        if self.job.sysinfo is not None:
            self.job.sysinfo.end_job_hook()
        self.result.end_tests()
        self.job.funcatexit.run()
        signal.signal(signal.SIGTSTP, signal.SIG_IGN)
        return summary
