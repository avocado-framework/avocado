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
# Copyright: Red Hat Inc. 2019
# Authors: Cleber Rosa <crosa@redhat.com>

"""
Avocado nrunner for Robot Framework tests
"""

import io
import multiprocessing
import tempfile
import time

from robot import run

from avocado.core.nrunner.app import BaseRunnerApp
from avocado.core.nrunner.runner import (RUNNER_RUN_CHECK_INTERVAL,
                                         RUNNER_RUN_STATUS_INTERVAL,
                                         BaseRunner)
from avocado.core.utils import messages


class RobotRunner(BaseRunner):

    name = 'robot'
    description = 'Runner for Robot Framework tests'

    def _uri_to_file_suite_test(self):
        """Converts the uri to a file name, suit name and test name"""
        if not self.runnable.uri:
            return (None, None, None)

        file_name_suite_test = self.runnable.uri.split(':', 1)
        if len(file_name_suite_test) == 1:
            return (file_name_suite_test[0], None, None)

        file_name, suite_test = file_name_suite_test
        suite_name_test_name = suite_test.split('.', 1)
        if len(suite_name_test_name) == 1:
            return (file_name, suite_test, None)
        suite_name, test_name = suite_name_test_name

        return (file_name, suite_name, test_name)

    def _run(self, file_name, suite_name, test_name, queue):
        stdout = io.StringIO()
        stderr = io.StringIO()
        output_dir = tempfile.mkdtemp(prefix=".avocado-robot")
        native_robot_result = run(file_name,
                                  suite=suite_name,
                                  test=test_name,
                                  outputdir=output_dir,
                                  stdout=stdout,
                                  stderr=stderr)
        if native_robot_result:
            result = 'fail'
        else:
            result = 'pass'

        stdout.seek(0)
        stderr.seek(0)
        output = self.prepare_status('finished',
                                     {'result': result,
                                      'stdout': stdout.read().encode(),
                                      'stderr': stderr.read().encode()})
        stdout.close()
        stderr.close()
        queue.put(output)

    def run(self, runnable):
        # pylint: disable=W0201
        self.runnable = runnable
        file_name, suite_name, test_name = self._uri_to_file_suite_test()
        if not all([file_name, suite_name, test_name]):

            yield messages.FinishedMessage.get('error',
                                               fail_reason='Invalid URI given')
            return

        queue = multiprocessing.SimpleQueue()
        process = multiprocessing.Process(target=self._run,
                                          args=(file_name, suite_name,
                                                test_name, queue))
        process.start()
        yield messages.StartedMessage.get()

        most_current_execution_state_time = None
        while queue.empty():
            time.sleep(RUNNER_RUN_CHECK_INTERVAL)
            now = time.monotonic()
            if most_current_execution_state_time is not None:
                next_execution_state_mark = (most_current_execution_state_time +
                                             RUNNER_RUN_STATUS_INTERVAL)
            if (most_current_execution_state_time is None or
                    now > next_execution_state_mark):
                most_current_execution_state_time = now
                yield messages.RunningMessage.get()

        status = queue.get()
        yield messages.StdoutMessage.get(status['stdout'])
        yield messages.StderrMessage.get(status['stderr'])
        yield messages.FinishedMessage.get(status['result'])


class RunnerApp(BaseRunnerApp):
    PROG_NAME = 'avocado-runner-robot'
    PROG_DESCRIPTION = '*nrunner application for robot tests'
    RUNNABLE_KINDS_CAPABLE = ['robot']


def main():
    app = RunnerApp(print)
    app.run()


if __name__ == '__main__':
    main()
