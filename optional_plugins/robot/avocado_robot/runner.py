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

import argparse
import io
import json
import multiprocessing
import tempfile
import time

from avocado.core.nrunner import BaseRunner
from avocado.core.nrunner import CMD_RUNNABLE_RUN_ARGS
from avocado.core.nrunner import CMD_TASK_RUN_ARGS
from avocado.core.nrunner import RUNNER_RUN_CHECK_INTERVAL
from avocado.core.nrunner import RUNNER_RUN_STATUS_INTERVAL
from avocado.core.nrunner import Task
from avocado.core.nrunner import runnable_from_args
from avocado.core.nrunner import runner_from_runnable
from avocado.core.nrunner import task_run

from robot import run


class RobotRunner(BaseRunner):

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
            time.sleep(RUNNER_RUN_CHECK_INTERVAL)
            now = time.time()
            if last_status is None or now > last_status + RUNNER_RUN_STATUS_INTERVAL:
                last_status = now
                if not time_start_sent:
                    time_start_sent = True
                    yield {'status': 'running',
                           'time_start': time_start}
                yield {'status': 'running'}

        yield queue.get()


def subcommand_capabilities(_, echo=print):
    data = {"runnables": [k for k in RUNNABLE_KIND_CAPABLE.keys()],
            "commands": [k for k in COMMANDS_CAPABLE.keys()]}
    echo(json.dumps(data))


def subcommand_runnable_run(args, echo=print):
    runnable = runnable_from_args(args)
    runner = runner_from_runnable(runnable, RUNNABLE_KIND_CAPABLE)

    for status in runner.run():
        echo(status)


def subcommand_task_run(args, echo=print):
    runnable = runnable_from_args(args)
    task = Task(args.get('identifier'), runnable,
                args.get('status_uri', []))
    task.capables = RUNNABLE_KIND_CAPABLE
    task_run(task, echo)


COMMANDS_CAPABLE = {'capabilities': subcommand_capabilities,
                    'runnable-run': subcommand_runnable_run,
                    'task-run': subcommand_task_run}


RUNNABLE_KIND_CAPABLE = {'robot': RobotRunner}


def parse():
    parser = argparse.ArgumentParser(
        prog='avocado-runner-robot',
        description='*EXPERIMENTAL* N(ext) Runner for robot tests')
    subcommands = parser.add_subparsers(dest='subcommand')
    subcommands.required = True
    subcommands.add_parser('capabilities')
    runnable_run_parser = subcommands.add_parser('runnable-run')
    for arg in CMD_RUNNABLE_RUN_ARGS:
        runnable_run_parser.add_argument(*arg[0], **arg[1])
    runnable_task_parser = subcommands.add_parser('task-run')
    for arg in CMD_TASK_RUN_ARGS:
        runnable_task_parser.add_argument(*arg[0], **arg[1])
    return parser.parse_args()


def main():
    args = vars(parse())
    subcommand = args.get('subcommand')
    kallable = COMMANDS_CAPABLE.get(subcommand)
    if kallable is not None:
        kallable(args)


if __name__ == '__main__':
    main()
