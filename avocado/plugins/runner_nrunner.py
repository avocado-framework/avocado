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

import asyncio
import json
import multiprocessing
import os
import random
from copy import copy

from avocado.core import nrunner
from avocado.core.dispatcher import SpawnerDispatcher
from avocado.core.plugin_interfaces import CLI, Init
from avocado.core.plugin_interfaces import Runner as RunnerInterface
from avocado.core.settings import settings
from avocado.core.status.repo import StatusRepo
from avocado.core.status.server import StatusServer
from avocado.core.task.runtime import RuntimeTask
from avocado.core.task.statemachine import TaskStateMachine, Worker
from avocado.core.test_id import TestID
from avocado.core.teststatus import mapping


class RunnerInit(Init):

    name = 'nrunner'
    description = 'nrunner initialization'

    def initialize(self):
        section = 'nrunner'
        help_msg = 'Shuffle the tasks to be executed'
        settings.register_option(section=section,
                                 key='shuffle',
                                 default=False,
                                 help_msg=help_msg,
                                 key_type=bool)

        help_msg = 'URI for the status server, usually a "HOST:PORT" string'
        settings.register_option(section=section,
                                 key='status_server_uri',
                                 default='127.0.0.1:8888',
                                 metavar="HOST:PORT",
                                 help_msg=help_msg)

        help_msg = ('Number of maximum number tasks running in parallel. You '
                    'can disable parallel execution by setting this to 1. '
                    'Defaults to the amount of CPUs on this machine.')
        settings.register_option(section=section,
                                 key='max_parallel_tasks',
                                 default=multiprocessing.cpu_count(),
                                 key_type=int,
                                 help_msg=help_msg)

        help_msg = ("Spawn tasks in a specific spawner. Available spawners: "
                    "'process' and 'podman'")
        settings.register_option(section=section,
                                 key="spawner",
                                 default='process',
                                 help_msg=help_msg)


class RunnerCLI(CLI):

    name = 'nrunner'
    description = 'nrunner command line options for "run"'

    def configure(self, parser):
        super(RunnerCLI, self).configure(parser)
        parser = parser.subcommands.choices.get('run', None)
        if parser is None:
            return

        parser = parser.add_argument_group('nrunner specific options')
        settings.add_argparser_to_option(namespace='nrunner.shuffle',
                                         parser=parser,
                                         long_arg='--nrunner-shuffle',
                                         action='store_true')

        settings.add_argparser_to_option(namespace='nrunner.status_server_uri',
                                         parser=parser,
                                         long_arg='--nrunner-status-server-uri')

        settings.add_argparser_to_option(namespace='nrunner.max_parallel_tasks',
                                         parser=parser,
                                         long_arg='--nrunner-max-parallel-tasks')

        settings.add_argparser_to_option(namespace='nrunner.spawner',
                                         parser=parser,
                                         long_arg='--nrunner-spawner')

    def run(self, config):
        pass


class Runner(RunnerInterface):

    name = 'nrunner'
    description = 'nrunner based implementation of job compliant runner'

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
        task_path = os.path.join(base_path, task.identifier.str_filesystem)
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

    def _get_all_runtime_tasks(self, test_suite):
        result = []
        no_digits = len(str(len(test_suite)))
        for index, task in enumerate(test_suite.tests, start=1):
            task.known_runners = nrunner.RUNNERS_REGISTRY_PYTHON_CLASS
            # this is all rubbish data
            if test_suite.name:
                prefix = "{}-{}".format(test_suite.name, index)
            else:
                prefix = index
            test_id = TestID(prefix,
                             task.runnable.uri,
                             None,
                             no_digits)
            task.identifier = test_id
            result.append(RuntimeTask(task))
        return result

    def _start_status_server(self, status_server_uri):
        # pylint: disable=W0201
        self.status_repo = StatusRepo()
        # pylint: disable=W0201
        self.status_server = StatusServer(status_server_uri,
                                          self.status_repo)
        asyncio.ensure_future(self.status_server.serve_forever())

    async def _update_status(self, job):
        tasks_by_id = {str(runtime_task.task.identifier): runtime_task.task
                       for runtime_task in self.tasks}
        while True:
            try:
                (task_id, status, _) = self.status_repo.status_journal_summary.pop(0)

            except IndexError:
                await asyncio.sleep(0.05)
                continue

            task = tasks_by_id.get(task_id)
            early_state = {'name': task.identifier,
                           'job_logdir': job.logdir,
                           'job_unique_id': job.unique_id}
            if status  == 'started':
                job.result.start_test(early_state)
                job.result_events_dispatcher.map_method('start_test',
                                                        job.result,
                                                        early_state)
            elif status == 'finished':
                this_task_data = self.status_repo.get_task_data(task_id)
                last_task_status = this_task_data[-1]
                test_state = {'status': last_task_status.get('result').upper()}
                test_state.update(early_state)

                time_start = this_task_data[0]['time']
                time_end = last_task_status['time']
                time_elapsed = time_end - time_start
                test_state['time_start'] = time_start
                test_state['time_end'] = time_end
                test_state['time_elapsed'] = time_elapsed

                # fake log dir, needed by some result plugins such as HTML
                test_state['logdir'] = ''

                base_path = os.path.join(job.logdir, 'test-results')
                self._populate_task_logdir(base_path,
                                           task,
                                           this_task_data,
                                           job.config.get('core.debug'))

                job.result.check_test(test_state)
                job.result_events_dispatcher.map_method('end_test',
                                                        job.result,
                                                        test_state)

                if not mapping[test_state['status']]:
                    self.summary.add("FAIL")

    def run_suite(self, job, test_suite):
        # pylint: disable=W0201
        self.summary = set()

        test_suite.tests, _ = nrunner.check_tasks_requirements(test_suite.tests)
        job.result.tests_total = test_suite.size  # no support for variants yet

        status_server_uri = test_suite.config.get('nrunner.status_server_uri')
        self._start_status_server(status_server_uri)

        # pylint: disable=W0201
        self.tasks = self._get_all_runtime_tasks(test_suite)
        if test_suite.config.get('nrunner.shuffle'):
            random.shuffle(self.tasks)
        tsm = TaskStateMachine(self.tasks)
        spawner_name = test_suite.config.get('nrunner.spawner')
        spawner = SpawnerDispatcher(test_suite.config)[spawner_name].obj
        max_running = test_suite.config.get('nrunner.max_parallel_tasks')
        workers = [Worker(tsm, spawner, max_running=max_running).run()
                   for _ in range(max_running)]
        asyncio.ensure_future(self._update_status(job))
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(asyncio.wait_for(asyncio.gather(*workers),
                                                     job.timeout or None))
        except (KeyboardInterrupt, asyncio.TimeoutError):
            self.summary.add("INTERRUPTED")

        # Wait until all messages may have been processed by the
        # status_updater. This should be replaced by a mechanism
        # that only waits if there are missing status messages to
        # be processed, and, only for a given amount of time.
        # Tests with non received status will always show as SKIP
        # because of result reconciliation.
        loop.run_until_complete(asyncio.sleep(0.05))

        job.result.end_tests()
        return self.summary
