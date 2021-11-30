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

import os
import signal
import time

from avocado.core import exceptions
from avocado.core.output import LOG_JOB as TEST_LOG
from avocado.core.settings import settings
from avocado.utils import wait


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
        with open(test_log, "a") as log_file:
            log_file.write('\n' + message + '\n')
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


class TestStatus:

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
        except Exception as details:  # pylint: disable=W0703
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
        end = time.monotonic() + timeout
        while not self.early_status:
            if not proc.is_alive():
                if not self.early_status:
                    raise exceptions.TestError("Process died before it pushed "
                                               "early test_status.")
            if time.monotonic() > end and not self.early_status:
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
                self.job.result_events_dispatcher.map_method('test_progress', False)
                paused_msg = msg['paused']
                if paused_msg:
                    self.job.log.warning(paused_msg)
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
        wait.wait_for(lambda: not proc.is_alive() or self.status, 1, 0, step)
        config = settings.as_dict()
        if self.status:     # status exists, wait for process to finish
            timeout_process_alive = config.get('runner.timeout.process_alive')
            deadline = min(deadline, time.monotonic() + timeout_process_alive)
            while time.monotonic() < deadline:
                result_dispatcher.map_method('test_progress', False)
                if wait.wait_for(lambda: not proc.is_alive(), 1, 0, step):
                    return self._add_status_failures(self.status)
            err = "Test reported status but did not finish"
        else:   # proc finished, wait for late status delivery
            timeout_process_died = config.get('runner.timeout.process_died')
            deadline = min(deadline, time.monotonic() + timeout_process_died)
            while time.monotonic() < deadline:
                result_dispatcher.map_method('test_progress', False)
                if wait.wait_for(lambda: self.status, 1, 0, step):
                    # Status delivered after the test process finished, pass
                    return self._add_status_failures(self.status)
            err = "Test died without reporting the status."
        # At this point there were failures, fill the new test status
        TEST_LOG.debug("Original status: %s", str(self.status))
        test_state = self.early_status
        test_state['time_start'] = started
        test_state['time_elapsed'] = time.monotonic() - started
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
        TEST_LOG.error('ERROR %s -> TestAbortError: %s.', err,
                       test_state['name'])
        if proc.is_alive():
            TEST_LOG.warning("Killing hanged test process %s", proc.pid)
            os.kill(proc.pid, signal.SIGTERM)
            if not wait.wait_for(lambda: not proc.is_alive(), 1, 0, 0.01):
                os.kill(proc.pid, signal.SIGKILL)
                end_time = time.monotonic() + 60
                while time.monotonic() < end_time:
                    if not proc.is_alive():
                        break
                    time.sleep(0.1)
                else:
                    raise exceptions.TestError("Unable to destroy test's "
                                               "process (%s)" % proc.pid)
        return self._add_status_failures(test_state)
