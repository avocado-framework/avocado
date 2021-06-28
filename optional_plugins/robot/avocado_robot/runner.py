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

from avocado.core import nrunner
from avocado.core.runners.utils import messages


class RobotRunner(nrunner.BaseRunner):

    def _run(self, uri, queue):
        stdout = io.StringIO()
        stderr = io.StringIO()
        output_dir = tempfile.mkdtemp(prefix=".avocado-robot")
        file_name, suit_test = uri.split(':', 1)
        suite_name, test_name = suit_test.split('.', 1)
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

    def run(self):
        if not self.runnable.uri:
            yield messages.FinishedMessage.get('error',
                                               fail_reason='uri is required '
                                                           'but was not given')
            return

        queue = multiprocessing.SimpleQueue()
        process = multiprocessing.Process(target=self._run,
                                          args=(self.runnable.uri, queue))
        process.start()
        yield messages.StartedMessage.get()

        most_current_execution_state_time = None
        while queue.empty():
            time.sleep(nrunner.RUNNER_RUN_CHECK_INTERVAL)
            now = time.monotonic()
            if most_current_execution_state_time is not None:
                next_execution_state_mark = (most_current_execution_state_time +
                                             nrunner.RUNNER_RUN_STATUS_INTERVAL)
            if (most_current_execution_state_time is None or
                    now > next_execution_state_mark):
                most_current_execution_state_time = now
                yield messages.RunningMessage.get()

        status = queue.get()
        yield messages.StdoutMessage.get(status['stdout'])
        yield messages.StderrMessage.get(status['stderr'])
        yield messages.FinishedMessage.get(status['result'])


class RunnerApp(nrunner.BaseRunnerApp):
    PROG_NAME = 'avocado-runner-robot'
    PROG_DESCRIPTION = '*nrunner application for robot tests'
    RUNNABLE_KINDS_CAPABLE = {'robot': RobotRunner}


def main():
    nrunner.main(RunnerApp)


if __name__ == '__main__':
    main()
