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
import multiprocessing
import os
import platform
import random
import tempfile

from avocado.core.dispatcher import SpawnerDispatcher
from avocado.core.exceptions import JobError, TestFailFast
from avocado.core.messages import MessageHandler
from avocado.core.nrunner.runnable import (
    RUNNERS_REGISTRY_STANDALONE_EXECUTABLE, STANDALONE_EXECUTABLE_CONFIG_USED)
from avocado.core.nrunner.runner import check_runnables_runner_requirements
from avocado.core.output import LOG_JOB
from avocado.core.plugin_interfaces import CLI, Init
from avocado.core.plugin_interfaces import Runner as RunnerInterface
from avocado.core.settings import settings
from avocado.core.status.repo import StatusRepo
from avocado.core.status.server import StatusServer
from avocado.core.task.runtime import RuntimeTaskGraph
from avocado.core.task.statemachine import TaskStateMachine, Worker


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

        help_msg = ('If the status server should automatically choose '
                    'a "status_server_listen" and "status_server_uri" '
                    'configuration. Default is to auto configure a '
                    'status server.')
        settings.register_option(section=section,
                                 key='status_server_auto',
                                 default=True,
                                 key_type=bool,
                                 help_msg=help_msg)

        help_msg = ('URI for listing the status server. Usually '
                    'a "HOST:PORT" string')
        settings.register_option(section=section,
                                 key='status_server_listen',
                                 default='127.0.0.1:8888',
                                 metavar="HOST:PORT",
                                 help_msg=help_msg)

        help_msg = ('URI for connecting to the status server, usually '
                    'a "HOST:PORT" string. Use this if your status server '
                    'is in another host, or different port')
        settings.register_option(section=section,
                                 key='status_server_uri',
                                 default='127.0.0.1:8888',
                                 metavar="HOST:PORT",
                                 help_msg=help_msg)

        help_msg = ('Buffer size that status server uses.  This should '
                    'generally not be a concern to most users, but '
                    'it can be tuned in case a runner generates very large '
                    'status messages, which is common if a test generates a '
                    'lot of output. Default is 33554432 (32MiB)')
        settings.register_option(section=section,
                                 key='status_server_buffer_size',
                                 key_type=int,
                                 default=2 ** 25,
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

        help_msg = "The amount of time a test has to complete in seconds."
        settings.register_option(section='task.timeout',
                                 key='running',
                                 default=None,
                                 key_type=int,
                                 help_msg=help_msg)


class RunnerCLI(CLI):

    name = 'nrunner'
    description = 'nrunner command line options for "run"'

    def configure(self, parser):
        super().configure(parser)
        parser = parser.subcommands.choices.get('run', None)
        if parser is None:
            return

        parser = parser.add_argument_group('nrunner specific options')
        settings.add_argparser_to_option(namespace='nrunner.shuffle',
                                         parser=parser,
                                         long_arg='--nrunner-shuffle',
                                         action='store_true')

        settings.add_argparser_to_option(
            namespace='nrunner.status_server_auto',
            parser=parser,
            long_arg='--nrunner-status-server-disable-auto',
            action='store_false')

        settings.add_argparser_to_option(
            namespace='nrunner.status_server_listen',
            parser=parser,
            long_arg='--nrunner-status-server-listen',
            metavar='HOST_PORT')

        settings.add_argparser_to_option(
            namespace='nrunner.status_server_uri',
            parser=parser,
            long_arg='--nrunner-status-server-uri',
            metavar='HOST_PORT')

        settings.add_argparser_to_option(
            namespace='nrunner.max_parallel_tasks',
            parser=parser,
            long_arg='--nrunner-max-parallel-tasks',
            metavar='NUMBER_OF_TASKS')

        settings.add_argparser_to_option(
            namespace='nrunner.spawner',
            parser=parser,
            long_arg='--nrunner-spawner',
            metavar='SPAWNER')

    def run(self, config):
        pass


class Runner(RunnerInterface):

    name = 'nrunner'
    description = 'nrunner based implementation of job compliant runner'

    @staticmethod
    def _update_avocado_configuration_used_on_runnables(runnables, config):
        """Updates the config used on runnables with this suite's config values

        :param runnables: the tasks whose runner requirements will be checked
        :type runnables: list of :class:`Runnable`
        :param config: A config dict to be used on the desired test suite.
        :type config: dict
        """
        for runnable in runnables:
            command = RUNNERS_REGISTRY_STANDALONE_EXECUTABLE.get(runnable.kind)
            if command is None:
                continue
            command = " ".join(command)
            configuration_used = STANDALONE_EXECUTABLE_CONFIG_USED.get(command)
            for config_item in configuration_used:
                if config_item in config:
                    runnable.config[config_item] = config.get(config_item)

    def _determine_status_server_uri(self, test_suite):
        # pylint: disable=W0201
        self.status_server_dir = None
        if test_suite.config.get('nrunner.status_server_auto'):
            # no UNIX domain sockets on Windows
            if platform.system() != 'Windows':
                self.status_server_dir = tempfile.TemporaryDirectory(
                    prefix='avocado_')
                return os.path.join(self.status_server_dir.name,
                                    '.status_server.sock')
        return test_suite.config.get('nrunner.status_server_listen')

    def _create_status_server(self, test_suite, job):
        listen = self._determine_status_server_uri(test_suite)
        # pylint: disable=W0201
        self.status_repo = StatusRepo(job.unique_id)
        # pylint: disable=W0201
        self.status_server = StatusServer(listen,
                                          self.status_repo)

    async def _update_status(self, job):
        tasks_by_id = {str(runtime_task.task.identifier): runtime_task.task
                       for runtime_task in self.runtime_tasks}
        message_handler = MessageHandler()
        while True:
            try:
                (task_id, _, _, index) = \
                    self.status_repo.status_journal_summary.pop(0)

            except IndexError:
                await asyncio.sleep(0.05)
                continue

            message = self.status_repo.get_task_data(task_id, index)
            task = tasks_by_id.get(task_id)
            message_handler.process_message(message, task, job)

    @staticmethod
    def _abort_if_missing_runners(runnables):
        if runnables:
            missing_kinds = set([runnable.kind for runnable in runnables])
            msg = (f"Could not find runners for runnable(s) of kind(s): "
                   f"{', '.join(missing_kinds)}")
            raise JobError(msg)

    def run_suite(self, job, test_suite):
        summary = set()

        if not test_suite.enabled:
            job.interrupted_reason = f"Suite {test_suite.name} is disabled."
            return summary

        test_suite.tests, missing_requirements = check_runnables_runner_requirements(
            test_suite.tests)

        self._update_avocado_configuration_used_on_runnables(test_suite.tests,
                                                             test_suite.config)

        self._abort_if_missing_runners(missing_requirements)

        job.result.tests_total = test_suite.variants.get_number_of_tests(test_suite.tests)

        self._create_status_server(test_suite, job)

        graph = RuntimeTaskGraph(test_suite.get_test_variants(),
                                 test_suite.name,
                                 self.status_server.uri,
                                 job.unique_id)
        # pylint: disable=W0201
        self.runtime_tasks = graph.get_tasks_in_topological_order()

        # Start the status server
        asyncio.ensure_future(self.status_server.serve_forever())

        if test_suite.config.get('nrunner.shuffle'):
            random.shuffle(self.runtime_tasks)
        test_ids = [rt.task.identifier for rt in self.runtime_tasks
                    if rt.task.category == 'test']
        tsm = TaskStateMachine(self.runtime_tasks, self.status_repo)
        spawner_name = test_suite.config.get('nrunner.spawner')
        spawner = SpawnerDispatcher(test_suite.config, job)[spawner_name].obj
        max_running = min(test_suite.config.get('nrunner.max_parallel_tasks'),
                          len(self.runtime_tasks))
        timeout = test_suite.config.get('task.timeout.running')
        failfast = test_suite.config.get('run.failfast')
        workers = [Worker(state_machine=tsm,
                          spawner=spawner,
                          max_running=max_running,
                          task_timeout=timeout,
                          failfast=failfast).run()
                   for _ in range(max_running)]
        asyncio.ensure_future(self._update_status(job))
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(asyncio.wait_for(asyncio.gather(*workers),
                                                     job.timeout or None))
        except (KeyboardInterrupt, asyncio.TimeoutError, TestFailFast) as ex:
            LOG_JOB.info(str(ex))
            job.interrupted_reason = str(ex)
            summary.add("INTERRUPTED")

        # Wait until all messages may have been processed by the
        # status_updater. This should be replaced by a mechanism
        # that only waits if there are missing status messages to
        # be processed, and, only for a given amount of time.
        # Tests with non received status will always show as SKIP
        # because of result reconciliation.
        loop.run_until_complete(asyncio.sleep(0.05))

        job.result.end_tests()
        self.status_server.close()
        if self.status_server_dir is not None:
            self.status_server_dir.cleanup()

        # Update the overall summary with found test statuses, which will
        # determine the Avocado command line exit status
        summary.update([status.upper() for status in
                        self.status_repo.get_result_set_for_tasks(test_ids)])
        return summary
