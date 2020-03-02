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

from avocado.core import nrunner

from robot import run


class RobotRunner(nrunner.BaseRunner):

    @staticmethod
    def _run(uri, queue):
        stdout = io.StringIO()
        stderr = io.StringIO()
        output_dir = tempfile.mkdtemp()
        file_name, suit_test = uri.split(':', 1)
        suite_name, test_name = suit_test.split('.', 1)
        result = run(file_name,
                     suite=suite_name,
                     test=test_name,
                     outputdir=output_dir,
                     stdout=stdout,
                     stderr=stderr)
        time_end = time.time()
        if result:
            status = 'fail'
        else:
            status = 'pass'

        stdout.seek(0)
        stderr.seek(0)
        result = {'status': status,
                  'stdout': stdout.read(),
                  'stderr': stderr.read(),
                  'time_end': time_end}
        stdout.close()
        stderr.close()
        queue.put(result)

    def run(self):
        if not self.runnable.uri:
            yield {'status': 'error',
                   'output': 'uri is required but was not given'}
            return

        queue = multiprocessing.SimpleQueue()
        process = multiprocessing.Process(target=self._run,
                                          args=(self.runnable.uri, queue))
        time_start = time.time()
        time_start_sent = False
        process.start()

        last_status = None
        while queue.empty():
            time.sleep(nrunner.RUNNER_RUN_CHECK_INTERVAL)
            now = time.time()
            if last_status is None or now > last_status + nrunner.RUNNER_RUN_STATUS_INTERVAL:
                last_status = now
                if not time_start_sent:
                    time_start_sent = True
                    yield {'status': 'running',
                           'time_start': time_start}
                yield {'status': 'running'}

        yield queue.get()


class RunnerApp(nrunner.BaseRunnerApp):
    PROG_NAME = 'avocado-runner-robot'
    PROG_DESCRIPTION = '*EXPERIMENTAL* N(ext) Runner for robot tests'
    RUNNABLE_KINDS_CAPABLE = {'robot': RobotRunner}


def main():
    nrunner.main(RunnerApp)


if __name__ == '__main__':
    main()
