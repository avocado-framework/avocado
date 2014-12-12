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

import imp
import logging
import multiprocessing
from multiprocessing import queues
import os
import signal
import sys
import time

from avocado import runtime
from avocado import sysinfo
from avocado import test
from avocado.core import data_dir
from avocado.core import exceptions
from avocado.core import output
from avocado.core import status
from avocado.utils import path
from avocado.utils import wait


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
        sysinfo_dir = path.init_dir(self.job.logdir, 'sysinfo')
        self.sysinfo = sysinfo.SysInfo(basedir=sysinfo_dir)

    def run_test(self, test_factory, queue):
        """
        Run a test instance in a subprocess.

        :param instance: Test instance.
        :type instance: :class:`avocado.test.Test` instance.
        :param queue: Multiprocess queue.
        :type queue: :class`multiprocessing.Queue` instance.
        """
        sys.stdout = output.LoggingFile(logger=logging.getLogger('avocado.test.stdout'))
        sys.sterr = output.LoggingFile(logger=logging.getLogger('avocado.test.stderr'))
        instance = self.job.test_loader.load_test(test_factory)
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

    def run_suite(self, params_list):
        """
        Run one or more tests and report with test result.

        :param params_list: a list of param dicts.

        :return: a list of test failures.
        """
        failures = []
        self.sysinfo.start_job_hook()
        self.result.start_tests()
        q = queues.SimpleQueue()
        test_suite = self.job.test_loader.discover(params_list, q)

        for test_factory in test_suite:
            p = multiprocessing.Process(target=self.run_test,
                                        args=(test_factory, q,))

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
                        logging.error("timeout")
                        os.kill(p.pid, signal.SIGUSR1)
                        break
                    wait.wait_for(lambda: not q.empty() or not p.is_alive(),
                                  cycle_timeout, step=0.1)
                    if not q.empty():
                        test_state = q.get()
                        if not test_state['running']:
                            break
                        else:
                            self.job.result_proxy.notify_progress(True)
                            if test_state['paused']:
                                msg = test_state['paused_msg']
                                if msg:
                                    self.job.view.notify(event='partial', msg=msg)

                    elif p.is_alive():
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
                if p.is_alive() and wait.wait_for(lambda: not q.empty(),
                                                  cycle_timeout, step=0.1):
                    test_state = q.get()
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
                break

            self.result.check_test(test_state)
            if not status.mapping[test_state['status']]:
                failures.append(test_state['name'])
        runtime.CURRENT_TEST = None
        self.result.end_tests()
        self.sysinfo.end_job_hook()
        return failures
