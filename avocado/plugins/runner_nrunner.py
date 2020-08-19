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
# Copyright: Red Hat Inc. 2019-2020
# Authors: Cleber Rosa <crosa@redhat.com>

"""
NRunner based implementation of job compliant runner
"""

import json
import os
import time
from copy import copy

from avocado.core import nrunner
from avocado.core.plugin_interfaces import Runner as RunnerInterface
from avocado.core.status.repo import StatusRepo
from avocado.core.test_id import TestID


class Runner(RunnerInterface):

    name = 'nrunner'
    description = '*EXPERIMENTAL* nrunner based implementation of job compliant runner'

    def _save_to_file(self, filename, buff, mode='wb'):
        with open(filename, mode) as fp:
            fp.write(buff)

    def _populate_task_logdir(self, base_path, task, statuses, debug=False):
        # We are copying here to avoid printing duplicated information
        local_statuses = copy(statuses)
        last = local_statuses[-1]
        try:
            stdout = last.pop('stdout')
        except KeyError:
            stdout = None
        try:
            stderr = last.pop('stderr')
        except KeyError:
            stderr = None

        # Create task dir
        task_path = os.path.join(base_path, task.identifier.replace('/', '_'))
        os.makedirs(task_path, exist_ok=True)

        # Save stdout and stderr
        if stdout is not None:
            stdout_file = os.path.join(task_path, 'stdout')
            self._save_to_file(stdout_file, stdout)
        if stderr is not None:
            stderr_file = os.path.join(task_path, 'stderr')
            self._save_to_file(stderr_file, stderr)

        # Save debug
        if debug:
            debug = os.path.join(task_path, 'debug')
            with open(debug, 'w') as fp:
                json.dump(local_statuses, fp)

        data_file = os.path.join(task_path, 'data')
        with open(data_file, 'w') as fp:
            fp.write("{}\n".format(task.output_dir))

    def run_suite(self, job, test_suite):
        summary = set()
        if job.timeout > 0:
            deadline = time.time() + job.timeout
        else:
            deadline = None

        test_suite.tests, _ = nrunner.check_tasks_requirements(test_suite.tests)
        job.result.tests_total = test_suite.size  # no support for variants yet
        result_dispatcher = job.result_events_dispatcher
        no_digits = len(str(len(test_suite)))
        status_repo = StatusRepo()

        for index, task in enumerate(test_suite.tests, start=1):
            if deadline is not None and time.time() > deadline:
                break

            task.known_runners = nrunner.RUNNERS_REGISTRY_PYTHON_CLASS
            # this is all rubbish data
            test_id = TestID("{}-{}".format(test_suite.name, index),
                             task.runnable.uri,
                             None,
                             no_digits)
            task.identifier = str(test_id)
            early_state = {
                'name': test_id,
                'job_logdir': job.logdir,
                'job_unique_id': job.unique_id,
            }
            job.result.start_test(early_state)
            job.result_events_dispatcher.map_method('start_test',
                                                    job.result,
                                                    early_state)

            task.status_services = []
            for status in task.run():
                status_repo.process_message(status)
                result_dispatcher.map_method('test_progress', False)

                if status['status'] not in ["started", "running"]:
                    break

            # test execution time is currently missing
            # since 358e800e81 all runners all produce the result in a key called
            # 'result', instead of 'status'.  But the Avocado result plugins rely
            # on the current runner approach
            this_task_data = status_repo.get_task_data(task.identifier)
            test_state = {'status': this_task_data[-1]['result'].upper()}
            test_state.update(early_state)

            time_start = this_task_data[0]['time']
            time_end = this_task_data[-1]['time']
            time_elapsed = time_end - time_start
            test_state['time_start'] = time_start
            test_state['time_end'] = time_end
            test_state['time_elapsed'] = time_elapsed

            # fake log dir, needed by some result plugins such as HTML
            test_state['logdir'] = ''

            # Populate task dir
            base_path = os.path.join(job.logdir, 'test-results')
            self._populate_task_logdir(base_path,
                                       task,
                                       this_task_data,
                                       job.config.get('core.debug'))

            job.result.check_test(test_state)
            result_dispatcher.map_method('end_test', job.result, test_state)
        job.result.end_tests()
        return summary
