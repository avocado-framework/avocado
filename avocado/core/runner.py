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
from ..utils import runtime
from ..utils import process
from ..utils import stacktrace

from .output import LOG_UI as APP_LOG
from .output import LOG_JOB as TEST_LOG

#: when test was interrupted (ctrl+c/timeout)
TIMEOUT_TEST_INTERRUPTED = 1
#: when the process died but the status was not yet delivered
TIMEOUT_PROCESS_DIED = 10
#: when test reported status but the process did not finish
TIMEOUT_PROCESS_ALIVE = 60


def add_runner_failure(test_state, new_status, message):
    """
    Append runner failure to the overall test status.

    :param test_state: Original test state (dict)
    :param new_status: New test status (PASS/FAIL/ERROR/INTERRUPTED/...)
    :param message: The error message
    """
    # Try to propagate the message everywhere
    message = ("Runner error occurred: %s\nOriginal status: %s\n%s"
               % (message, test_state.get("status"), test_state))
    TEST_LOG.error(message)
    test_log = test_state.get("logfile")
    if test_state.get("text_output"):
        test_state["text_output"] = "%s\n%s\n" % (test_state["text_output"],
                                                  message)
    else:
        test_state["text_output"] = message + "\n"
    if test_log:
        open(test_log, "a").write('\n' + message + '\n')
    # Update the results
    if test_state.get("fail_reason"):
        test_state["fail_reason"] = "%s\n%s" % (test_state["fail_reason"],
                                                message)
    else:
        test_state["fail_reason"] = message
    if test_state.get("fail_class"):
        test_state["fail_class"] = "%s\nRUNNER" % test_state["fail_class"]
    else:
        test_state["fail_class"] = "RUNNER"
    test_state["status"] = new_status
    return test_state


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
        self._failed = False

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
            self._failed = True
            TEST_LOG.error("RUNNER: Failed to read queue: %s", details)
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
        step = 0.01
        end = time.time() + timeout
        while not self.early_status:
            if not proc.is_alive():
                if not self.early_status:
                    raise exceptions.TestError("Process died before it pushed "
                                               "early test_status.")
            if time.time() > end and not self.early_status:
                os.kill(proc.pid, signal.SIGTERM)
                if not wait.wait_for(lambda: not proc.is_alive(), 1, 0, 0.01):
                    os.kill(proc.pid, signal.SIGKILL)
                msg = ("Unable to receive test's early-status in %ss, "
                       "something wrong happened probably in the "
                       "avocado framework." % timeout)
                raise exceptions.TestError(msg)
            time.sleep(step)

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
                self.job._result_events_dispatcher.map_method('test_progress',
                                                              False)
                if msg['paused']:
                    reason = msg['paused_msg']
                    if reason:
                        self.job.log.warning(reason)
            else:       # test_status
                self.status = msg

    def _add_status_failures(self, test_state):
        """
        Append TestStatus error to test_state in case there were any.
        """
        if self._failed:
            return add_runner_failure(test_state, "ERROR", "TestStatus failed,"
                                      " see overall job.log for details.")
        return test_state

    def finish(self, proc, started, step, deadline, result_dispatcher):
        """
        Wait for the test process to finish and report status or error status
        if unable to obtain the status till deadline.

        :param proc: The test's process
        :param started: Time when the test started
        :param first: Delay before first check
        :param step: Step between checks for the status
        :param deadline: Test execution deadline
        :param result_dispatcher: Result dispatcher (for test_progress
               notifications)
        """
        # Wait for either process termination or test status
        wait.wait_for(lambda: not proc.is_alive() or self.status, 1, 0,
                      step)
        if self.status:     # status exists, wait for process to finish
            deadline = min(deadline, time.time() + TIMEOUT_PROCESS_ALIVE)
            while time.time() < deadline:
                result_dispatcher.map_method('test_progress', False)
                if wait.wait_for(lambda: not proc.is_alive(), 1, 0,
                                 step):
                    return self._add_status_failures(self.status)
            err = "Test reported status but did not finish"
        else:   # proc finished, wait for late status delivery
            deadline = min(deadline, time.time() + TIMEOUT_PROCESS_DIED)
            while time.time() < deadline:
                result_dispatcher.map_method('test_progress', False)
                if wait.wait_for(lambda: self.status, 1, 0, step):
                    # Status delivered after the test process finished, pass
                    return self._add_status_failures(self.status)
            err = "Test died without reporting the status."
        # At this point there were failures, fill the new test status
        TEST_LOG.debug("Original status: %s", str(self.status))
        test_state = self.early_status
        test_state['time_elapsed'] = time.time() - started
        test_state['fail_reason'] = err
        test_state['status'] = exceptions.TestAbortError.status
        test_state['fail_class'] = (exceptions.TestAbortError.__class__.
                                    __name__)
        test_state['traceback'] = 'Traceback not available'
        try:
            with open(test_state['logfile'], 'r') as log_file_obj:
                test_state['text_output'] = log_file_obj.read()
        except IOError:
            test_state["text_output"] = "Not available, file not created yet"
        TEST_LOG.error('ERROR %s -> TestAbortedError: %s.', err,
                       test_state['name'])
        if proc.is_alive():
            TEST_LOG.warning("Killing hanged test process %s" % proc.pid)
            os.kill(proc.pid, signal.SIGTERM)
            if not wait.wait_for(lambda: not proc.is_alive(), 1, 0, 0.01):
                os.kill(proc.pid, signal.SIGKILL)
                end_time = time.time() + 60
                while time.time() < end_time:
                    if not proc.is_alive():
                        break
                    time.sleep(0.1)
                else:
                    raise exceptions.TestError("Unable to destroy test's "
                                               "process (%s)" % proc.pid)
        return self._add_status_failures(test_state)


class TestRunner(object):

    """
    A test runner class that displays tests results.
    """
    DEFAULT_TIMEOUT = 86400

    def __init__(self, job, result):
        """
        Creates an instance of TestRunner class.

        :param job: an instance of :class:`avocado.core.job.Job`.
        :param result: an instance of :class:`avocado.core.result.Result`
        """
        self.job = job
        self.result = result
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
        logger_list_stdout = [TEST_LOG,
                              logging.getLogger('paramiko')]
        logger_list_stderr = [TEST_LOG,
                              logging.getLogger('paramiko')]
        sys.stdout = output.LoggingFile(logger=logger_list_stdout)
        sys.stderr = output.LoggingFile(logger=logger_list_stderr)

        def sigterm_handler(signum, frame):     # pylint: disable=W0613
            """ Produce traceback on SIGTERM """
            raise RuntimeError("Test interrupted by SIGTERM")

        signal.signal(signal.SIGTERM, sigterm_handler)

        # Replace STDIN (0) with the /dev/null's fd
        os.dup2(sys.stdin.fileno(), 0)

        instance = loader.load_test(test_factory)
        if instance.runner_queue is None:
            instance.set_runner_queue(queue)
        runtime.CURRENT_TEST = instance
        early_state = instance.get_state()
        early_state['early_status'] = True
        try:
            queue.put(early_state)
        except Exception:
            instance.error(stacktrace.str_unpickable_object(early_state))

        self.result.start_test(early_state)
        self.job._result_events_dispatcher.map_method('start_test',
                                                      self.result,
                                                      early_state)
        try:
            instance.run_avocado()
        finally:
            try:
                state = instance.get_state()
                queue.put(state)
            except Exception:
                instance.error(stacktrace.str_unpickable_object(state))

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

        test_status.wait_for_early_status(proc, 60)

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
        step = 0.01
        abort_reason = None
        result_dispatcher = self.job._result_events_dispatcher

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
                            result_dispatcher.map_method('test_progress',
                                                         False)
                        else:
                            result_dispatcher.map_method('test_progress', True)
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

        # Get/update the test status (decrease timeout on abort)
        if abort_reason:
            finish_deadline = TIMEOUT_TEST_INTERRUPTED
        else:
            finish_deadline = deadline
        test_state = test_status.finish(proc, time_started, step,
                                        finish_deadline,
                                        result_dispatcher)

        # Try to log the timeout reason to test's results and update test_state
        if abort_reason:
            test_state = add_runner_failure(test_state, "INTERRUPTED",
                                            abort_reason)

        # don't process other tests from the list
        if ctrl_c_count > 0:
            self.job.log.debug('')

        # Make sure the test status is correct
        if test_state.get('status') not in status.user_facing_status:
            test_state = add_runner_failure(test_state, "ERROR", "Test reports"
                                            " unsupported test status.")

        self.result.check_test(test_state)
        result_dispatcher.map_method('end_test', self.result, test_state)
        if test_state['status'] == "INTERRUPTED":
            summary.add("INTERRUPTED")
        elif not mapping[test_state['status']]:
            summary.add("FAIL")

            if getattr(self.job.args, 'failfast', 'off') == 'on':
                summary.add("INTERRUPTED")
                self.job.log.debug("Interrupting job (failfast).")
                return False

        if ctrl_c_count > 0:
            return False
        return True

    @staticmethod
    def _template_to_factory(template, variant):
        """
        Applies test params from variant to the test template

        :param template: a test template
        :param variant: variant to be applied
        :return: tuple(new_test_factory, applied_variant)
        """
        params = variant.get("variant"), variant.get("mux_path")
        if params:
            if "params" in template[1]:
                msg = ("Unable to use test variants %s, params are already"
                       " present in test factory: %s"
                       % (template[0], template[1]))
                raise ValueError(msg)
            factory = [template[0], template[1].copy()]
            factory[1]["params"] = params
        else:
            factory = template
        return factory, variant

    def _iter_suite(self, test_suite, variants, execution_order):
        """
        Iterates through test_suite and variants in defined order

        :param test_suite: a list of tests to run
        :param variants: a varianter object to produce test params
        :param execution_order: way of iterating through tests/variants
        :return: generator yielding tuple(test_factory, variant)
        """
        if execution_order in ("variants-per-test", None):
            return (self._template_to_factory(template, variant)
                    for template in test_suite
                    for variant in variants.itertests())
        elif execution_order == "tests-per-variant":
            return (self._template_to_factory(template, variant)
                    for variant in variants.itertests()
                    for template in test_suite)
        else:
            raise NotImplementedError("Suite_order %s is not supported"
                                      % execution_order)

    def run_suite(self, test_suite, variants, timeout=0, replay_map=None,
                  execution_order=None):
        """
        Run one or more tests and report with test result.

        :param test_suite: a list of tests to run.
        :param variants: A varianter iterator to produce test params.
        :param timeout: maximum amount of time (in seconds) to execute.
        :param replay_map: optional list to override test class based on test
                           index.
        :param execution_order: Mode in which we should iterate through tests
                            resp. variants.
        :return: a set with types of test failures.
        """
        summary = set()
        if self.job.sysinfo is not None:
            self.job.sysinfo.start_job_hook()
        queue = queues.SimpleQueue()

        if timeout > 0:
            deadline = time.time() + timeout
        else:
            deadline = None

        test_result_total = variants.get_number_of_tests(test_suite)
        no_digits = len(str(test_result_total))
        self.result.tests_total = test_result_total
        index = -1
        try:
            for test_template in test_suite:
                test_template[1]["base_logdir"] = self.job.logdir
                test_template[1]["job"] = self.job
            for test_factory, variant in self._iter_suite(test_suite, variants,
                                                          execution_order):
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
                    if not self.run_test(test_factory, queue, summary):
                        break
                else:
                    if (replay_map is not None and
                            replay_map[index] is not None):
                        test_parameters["methodName"] = "test"
                        test_factory = (replay_map[index], test_parameters)

                    if not self.run_test(test_factory, queue, summary,
                                         deadline):
                        break
                runtime.CURRENT_TEST = None
        except KeyboardInterrupt:
            TEST_LOG.error('Job interrupted by ctrl+c.')
            summary.add('INTERRUPTED')

        if self.job.sysinfo is not None:
            self.job.sysinfo.end_job_hook()
        self.result.end_tests()
        self.job.funcatexit.run()
        signal.signal(signal.SIGTSTP, signal.SIG_IGN)
        return summary
