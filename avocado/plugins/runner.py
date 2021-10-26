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
# Copyright: Red Hat Inc. 2014-2019
# Authors: Lucas Meneghel Rodrigues <lmr@redhat.com>
#          Ruda Moura <rmoura@redhat.com>
#          Cleber Rosa <crosa@redhat.com>

"""
Conventional Test Runner Plugin
"""

import multiprocessing
import os
import signal
import sys
import time
from queue import Full as queueFullException

from avocado.core import output, tree, varianter
from avocado.core.output import LOG_JOB as TEST_LOG
from avocado.core.output import LOG_UI as APP_LOG
from avocado.core.plugin_interfaces import Runner
from avocado.core.runner import TestStatus, add_runner_failure
from avocado.core.test import TimeOutSkipTest
from avocado.core.test_id import TestID
from avocado.core.teststatus import STATUSES, STATUSES_MAPPING
from avocado.core.utils import loader
from avocado.utils import process, stacktrace, wait


class TestRunner(Runner):

    """
    A test runner class that displays tests results.
    """

    name = 'runner'
    description = 'The conventional test runner'

    DEFAULT_TIMEOUT = 86400

    def __init__(self):
        """
        Creates an instance of TestRunner class.
        """
        self.sigstopped = False

    @staticmethod
    def _run_test(job, test_factory, queue):
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
        sys.stdout = output.LoggingFile(["[stdout] "], loggers=[TEST_LOG])
        sys.stderr = output.LoggingFile(["[stderr] "], loggers=[TEST_LOG])

        def sigterm_handler(signum, frame):     # pylint: disable=W0613
            """ Produce traceback on SIGTERM """
            raise RuntimeError("Test interrupted by SIGTERM")

        signal.signal(signal.SIGTERM, sigterm_handler)

        # At this point, the original `sys.stdin` has already been
        # closed and replaced with `os.devnull` by
        # `multiprocessing.Process()` (not directly from Avocado
        # code).  Still, tests trying to use file descriptor 0 would
        # be able to read from the tty, and would hang. Let's replace
        # STDIN fd (0), with the same fd previously set by
        # `multiprocessing.Process()`
        os.dup2(sys.stdin.fileno(), 0)

        instance = loader.load_test(test_factory)
        if instance.runner_queue is None:
            instance.set_runner_queue(queue)
        early_state = instance.get_state()
        early_state['early_status'] = True
        early_state['job_logdir'] = job.logdir
        early_state['job_unique_id'] = job.unique_id
        try:
            queue.put(early_state)
        except queueFullException:
            instance.error(stacktrace.str_unpickable_object(early_state))

        job.result.start_test(early_state)
        job.result_events_dispatcher.map_method('start_test',
                                                job.result,
                                                early_state)
        if job.config.get('run.log_test_data_directories'):
            data_sources = getattr(instance, "DATA_SOURCES", [])
            if data_sources:
                locations = []
                for source in data_sources:
                    locations.append(instance.get_data("", source=source,
                                                       must_exist=False))
                TEST_LOG.info('Test data directories: ')
                for source, location in zip(data_sources, locations):
                    if location is not None:
                        TEST_LOG.info('  %s: %s', source, location)
                TEST_LOG.info('')
        try:
            instance.run_avocado()
        finally:
            try:
                state = instance.get_state()
                state['job_logdir'] = job.logdir
                state['job_unique_id'] = job.unique_id
                queue.put(state)
            except queueFullException:
                instance.error(stacktrace.str_unpickable_object(state))

    def run_test(self, job, test_factory, queue, summary, job_deadline=0):
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
                app_log_msg = '\n%s' % msg
                if self.sigstopped:
                    APP_LOG.info(app_log_msg, "resumming")
                    TEST_LOG.info(msg, "resumming")
                    process.kill_process_tree(proc.pid, signal.SIGCONT, False)
                    self.sigstopped = False
                else:
                    APP_LOG.info(app_log_msg, "stopping")
                    TEST_LOG.info(msg, "stopping")
                    process.kill_process_tree(proc.pid, signal.SIGSTOP, False)
                    self.sigstopped = True

        proc = multiprocessing.Process(target=self._run_test,
                                       args=(job, test_factory, queue,))
        test_status = TestStatus(job, queue)

        cycle_timeout = 1
        time_started = time.monotonic()
        signal.signal(signal.SIGTSTP, signal.SIG_IGN)
        proc.start()
        signal.signal(signal.SIGTSTP, sigtstp_handler)
        test_status.wait_for_early_status(proc, 60)

        # At this point, the test is already initialized and we know
        # for sure if there's a timeout set.
        timeout = test_status.early_status.get('timeout')
        timeout = float(timeout or self.DEFAULT_TIMEOUT)

        test_deadline = time_started + timeout
        if job_deadline is not None and job_deadline > 0:
            deadline = min(test_deadline, job_deadline)
        else:
            deadline = test_deadline

        ctrl_c_count = 0
        ignore_window = 2.0
        ignore_time_started = time.monotonic()
        stage_1_msg_displayed = False
        stage_2_msg_displayed = False
        first = 0.01
        step = 0.01
        abort_reason = None
        result_dispatcher = job.result_events_dispatcher

        while True:
            try:
                if time.monotonic() >= deadline:
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
                time_elapsed = time.monotonic() - ignore_time_started
                ctrl_c_count += 1
                if ctrl_c_count == 1:
                    if not stage_1_msg_displayed:
                        abort_reason = "Interrupted by ctrl+c"
                        job.log.debug("\nInterrupt requested. Waiting %d "
                                      "seconds for test to finish "
                                      "(ignoring new Ctrl+C until then)",
                                      ignore_window)
                        stage_1_msg_displayed = True
                    ignore_time_started = time.monotonic()
                    process.kill_process_tree(proc.pid, signal.SIGINT)
                if (ctrl_c_count > 1) and (time_elapsed > ignore_window):
                    if not stage_2_msg_displayed:
                        abort_reason = "Interrupted by ctrl+c (multiple-times)"
                        job.log.debug("Killing test subprocess %s",
                                      proc.pid)
                        stage_2_msg_displayed = True
                    process.kill_process_tree(proc.pid, signal.SIGKILL)

        # Get/update the test status (decrease timeout on abort)
        if abort_reason:
            after_interrupted = job.config.get('runner.timeout.after_interrupted')
            finish_deadline = time.monotonic() + after_interrupted
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
            job.log.debug('')

        # Make sure the test status is correct
        if test_state.get('status') not in STATUSES:
            test_state = add_runner_failure(test_state, "ERROR", "Test reports"
                                            " unsupported test status.")

        job.result.check_test(test_state)
        result_dispatcher.map_method('end_test', job.result, test_state)
        if test_state['status'] == "INTERRUPTED":
            summary.add("INTERRUPTED")
        elif not STATUSES_MAPPING[test_state['status']]:
            summary.add("FAIL")

            if job.config.get('run.failfast'):
                summary.add("INTERRUPTED")
                job.interrupted_reason = "Interrupting job (failfast)."
                return False

        if ctrl_c_count > 0:
            return False
        return True

    @staticmethod
    def _template_to_factory(test_parameters, template, variant):
        """
        Applies test params from variant to the test template

        :param test_parameters: a simpler set of parameters (currently
                                given to the run command via "-p" parameters)
        :param template: a test template, containing the class name,
                         followed by parameters to the class
        :type template: tuple
        :param variant: variant to be applied, usually containing
                        the keys: paths, variant and variant_id
        :type variant: dict
        :return: tuple(new_test_factory, applied_variant)
        """
        var = variant.get("variant")
        paths = variant.get("paths")

        original_params_to_klass = template[1]
        if "params" not in original_params_to_klass:
            params_to_klass = original_params_to_klass.copy()
            if test_parameters:
                var[0] = tree.TreeNode().get_node("/", True)
                var[0].value = test_parameters
                paths = ["/"]
            params_to_klass["params"] = (var, paths)
            factory = [template[0], params_to_klass]
            return factory, variant

        return template, {"variant": var,
                          "variant_id": varianter.generate_variant_id(var),
                          "paths": paths}

    def _iter_suite(self, test_suite, execution_order):
        """
        Iterates through test_suite and variants in defined order

        :param test_suite: a TestSuite object to run
        :param execution_order: way of iterating through tests/variants
        :return: generator yielding tuple(test_factory, variant)
        """
        if execution_order == "variants-per-test":
            return (self._template_to_factory(test_suite.test_parameters,
                                              template, variant)
                    for template in test_suite.tests
                    for variant in test_suite.variants.itertests())
        elif execution_order == "tests-per-variant":
            return (self._template_to_factory(test_suite.test_parameters,
                                              template, variant)
                    for variant in test_suite.variants.itertests()
                    for template in test_suite.tests)
        else:
            raise NotImplementedError("Suite_order %s is not supported"
                                      % execution_order)

    def run_suite(self, job, test_suite):
        """
        Run one or more tests and report with test result.

        :param job: an instance of :class:`avocado.core.job.Job`.
        :param test_suite: a list of tests to run.
        :return: a set with types of test failures.
        """
        summary = set()
        replay_map = job.config.get('replay_map')
        execution_order = job.config.get('run.execution_order')
        queue = multiprocessing.SimpleQueue()
        if job.timeout > 0:
            deadline = time.monotonic() + job.timeout
        else:
            deadline = None

        test_result_total = test_suite.variants.get_number_of_tests(test_suite.tests)
        no_digits = len(str(test_result_total))
        job.result.tests_total = test_result_total
        index = 1
        try:
            for test_factory, variant in self._iter_suite(test_suite,
                                                          execution_order):
                test_parameters = test_factory[1]
                test_parameters["base_logdir"] = job.logdir
                test_parameters["config"] = job.config
                name = test_parameters.get("name")
                if test_suite.name:
                    prefix = "{}-{}".format(test_suite.name, index)
                else:
                    prefix = index
                test_parameters["name"] = TestID(prefix,
                                                 name,
                                                 variant,
                                                 no_digits)
                if deadline is not None and time.monotonic() > deadline:
                    summary.add('INTERRUPTED')
                    if 'methodName' in test_parameters:
                        del test_parameters['methodName']
                    test_factory = (TimeOutSkipTest, test_parameters)
                    if not self.run_test(job, test_factory, queue, summary):
                        break
                else:
                    if (replay_map is not None and
                            replay_map[index - 1] is not None):
                        test_factory = (replay_map[index - 1], test_parameters)
                    if not self.run_test(job, test_factory, queue, summary,
                                         deadline):
                        break
                index += 1
        except KeyboardInterrupt:
            TEST_LOG.error('Job interrupted by ctrl+c.')
            summary.add('INTERRUPTED')

        job.result.end_tests()
        job.funcatexit.run()
        signal.signal(signal.SIGTSTP, signal.SIG_IGN)
        return summary
