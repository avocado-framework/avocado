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
from avocado.core.exceptions import JobError, JobFailFast
from avocado.core.messages import MessageHandler
from avocado.core.nrunner.runnable import Runnable
from avocado.core.nrunner.runner import check_runnables_runner_requirements
from avocado.core.output import LOG_JOB
from avocado.core.plugin_interfaces import CLI, Init, SuiteRunner
from avocado.core.settings import settings
from avocado.core.status.repo import StatusRepo
from avocado.core.status.server import StatusServer
from avocado.core.task.runtime import RuntimeTaskGraph
from avocado.core.task.statemachine import TaskStateMachine, Worker


class RunnerInit(Init):

    name = "nrunner"
    description = "nrunner initialization"

    def initialize(self):
        section = "run"
        help_msg = "Shuffle the tasks to be executed"
        settings.register_option(
            section=section,
            key="shuffle",
            default=False,
            help_msg=help_msg,
            key_type=bool,
        )

        help_msg = (
            "If the status server should automatically choose "
            'a "status_server_listen" and "status_server_uri" '
            "configuration. Default is to auto configure a "
            "status server."
        )
        settings.register_option(
            section=section,
            key="status_server_auto",
            default=True,
            key_type=bool,
            help_msg=help_msg,
        )

        help_msg = (
            'URI where status server will listen on. Usually a "HOST:PORT" '
            'string. This is only effective if "status_server_auto" is disabled'
        )
        settings.register_option(
            section=section,
            key="status_server_listen",
            default="127.0.0.1:8888",
            metavar="HOST:PORT",
            help_msg=help_msg,
        )

        help_msg = (
            "URI for connecting to the status server, usually "
            'a "HOST:PORT" string. Use this if your status server '
            "is in another host, or different port. This is only "
            'effective if "status_server_auto" is disabled'
        )
        settings.register_option(
            section=section,
            key="status_server_uri",
            default="127.0.0.1:8888",
            metavar="HOST:PORT",
            help_msg=help_msg,
        )

        help_msg = (
            "Buffer size that status server uses.  This should "
            "generally not be a concern to most users, but "
            "it can be tuned in case a runner generates very large "
            "status messages, which is common if a test generates a "
            "lot of output. Default is 33554432 (32MiB)"
        )
        settings.register_option(
            section=section,
            key="status_server_buffer_size",
            key_type=int,
            default=2**25,
            help_msg=help_msg,
        )

        help_msg = (
            "Number of maximum number tasks running in parallel. You "
            "can disable parallel execution by setting this to 1. "
            "Defaults to the amount of CPUs on this machine."
        )
        settings.register_option(
            section=section,
            key="max_parallel_tasks",
            default=multiprocessing.cpu_count(),
            key_type=int,
            help_msg=help_msg,
        )

        help_msg = (
            "Spawn tasks in a specific spawner. Available spawners: "
            "'process' and 'podman'"
        )
        settings.register_option(
            section=section, key="spawner", default="process", help_msg=help_msg
        )

        help_msg = "The amount of time a test has to complete in seconds."
        settings.register_option(
            section="task.timeout",
            key="running",
            default=None,
            key_type=int,
            help_msg=help_msg,
        )


class RunnerCLI(CLI):

    name = "nrunner"
    description = 'nrunner command line options for "run"'

    def configure(self, parser):
        super().configure(parser)
        parser = parser.subcommands.choices.get("run", None)
        if parser is None:
            return

        parser = parser.add_argument_group("nrunner specific options")
        settings.add_argparser_to_option(
            namespace="run.shuffle",
            parser=parser,
            long_arg="--shuffle",
            action="store_true",
        )

        settings.add_argparser_to_option(
            namespace="run.status_server_auto",
            parser=parser,
            long_arg="--status-server-disable-auto",
            action="store_false",
        )

        settings.add_argparser_to_option(
            namespace="run.status_server_listen",
            parser=parser,
            long_arg="--status-server-listen",
            metavar="HOST_PORT",
        )

        settings.add_argparser_to_option(
            namespace="run.status_server_uri",
            parser=parser,
            long_arg="--status-server-uri",
            metavar="HOST_PORT",
        )

        settings.add_argparser_to_option(
            namespace="run.max_parallel_tasks",
            parser=parser,
            long_arg="--max-parallel-tasks",
            metavar="NUMBER_OF_TASKS",
        )

        settings.add_argparser_to_option(
            namespace="run.spawner",
            parser=parser,
            long_arg="--spawner",
            metavar="SPAWNER",
        )

    def run(self, config):
        pass


class Runner(SuiteRunner):

    name = "nrunner"
    description = "nrunner based implementation of job compliant runner"

    def __init__(self):
        super().__init__()
        self.status_server_dir = None

    @staticmethod
    def _update_avocado_configuration_used_on_runnables(runnables, config):
        """Updates the config used on runnables with this suite's config values

        :param runnables: the tasks whose runner requirements will be checked
        :type runnables: list of :class:`Runnable`
        :param config: A config dict to be used on the desired test suite.
        :type config: dict
        """
        for runnable in runnables:
            runnable.config = Runnable.filter_runnable_config(runnable.kind, config)

    def _determine_status_server(self, test_suite, config_key):
        if test_suite.config.get("run.status_server_auto"):
            # no UNIX domain sockets on Windows
            if platform.system() != "Windows":
                if self.status_server_dir is None:
                    self.status_server_dir = tempfile.TemporaryDirectory(
                        prefix="avocado_"
                    )
                return os.path.join(self.status_server_dir.name, ".status_server.sock")
        return test_suite.config.get(config_key)

    def _create_status_server(self, test_suite, job):
        listen = self._determine_status_server(test_suite, "run.status_server_listen")
        # pylint: disable=W0201
        self.status_repo = StatusRepo(job.unique_id)
        # pylint: disable=W0201
        self.status_server = StatusServer(listen, self.status_repo)

    async def _update_status(self, job):
        message_handler = MessageHandler()
        while True:
            try:
                (_, task_id, _, index) = self.status_repo.status_journal_summary_pop()

            except IndexError:
                await asyncio.sleep(0.05)
                continue

            message = self.status_repo.get_task_data(task_id, index)
            task = self.tsm.tasks_by_id.get(task_id)
            message_handler.process_message(message, task, job)

    @staticmethod
    def _abort_if_missing_runners(runnables):
        if runnables:
            missing_kinds = set([runnable.kind for runnable in runnables])
            msg = (
                f"Could not find runners for runnable(s) of kind(s): "
                f"{', '.join(missing_kinds)}"
            )
            raise JobError(msg)

    def run_suite(self, job, test_suite):
        summary = set()

        if not test_suite.enabled:
            job.interrupted_reason = f"Suite {test_suite.name} is disabled."
            return summary

        test_suite.tests, missing_requirements = check_runnables_runner_requirements(
            test_suite.tests
        )

        self._update_avocado_configuration_used_on_runnables(
            test_suite.tests, test_suite.config
        )

        self._abort_if_missing_runners(missing_requirements)

        job.result.tests_total = len(test_suite.tests)

        self._create_status_server(test_suite, job)

        graph = RuntimeTaskGraph(
            test_suite.tests,
            test_suite.name,
            self._determine_status_server(test_suite, "run.status_server_uri"),
            job.unique_id,
            job.test_results_path,
            test_suite.config,
        )
        # pylint: disable=W0201
        self.runtime_tasks = graph.get_tasks_in_topological_order()

        # Start the status server
        asyncio.ensure_future(self.status_server.serve_forever())

        if test_suite.config.get("run.shuffle"):
            random.shuffle(self.runtime_tasks)
        test_ids = [
            rt.task.identifier
            for rt in self.runtime_tasks
            if rt.task.category == "test"
        ]
        self.tsm = TaskStateMachine(self.runtime_tasks, self.status_repo)
        spawner_name = test_suite.config.get("run.spawner")
        spawner = SpawnerDispatcher(test_suite.config, job)[spawner_name].obj
        max_running = min(
            test_suite.config.get("run.max_parallel_tasks"), len(self.runtime_tasks)
        )
        timeout = test_suite.config.get("task.timeout.running")
        failfast = test_suite.config.get("run.failfast")
        workers = [
            Worker(
                state_machine=self.tsm,
                spawner=spawner,
                max_running=max_running,
                task_timeout=timeout,
                failfast=failfast,
            ).run()
            for _ in range(max_running)
        ]
        asyncio.ensure_future(self._update_status(job))
        loop = asyncio.get_event_loop()
        try:
            try:
                loop.run_until_complete(
                    asyncio.wait_for(
                        asyncio.shield(asyncio.gather(*workers)), job.timeout or None
                    )
                )
            except asyncio.TimeoutError:
                terminate_worker = Worker(
                    state_machine=self.tsm,
                    spawner=spawner,
                    max_running=max_running,
                    task_timeout=timeout,
                    failfast=failfast,
                )
                loop.run_until_complete(
                    asyncio.wait_for(terminate_worker.terminate_tasks_timeout(), None)
                )
                raise
            except KeyboardInterrupt:
                terminate_worker = Worker(
                    state_machine=self.tsm,
                    spawner=spawner,
                    max_running=max_running,
                    task_timeout=timeout,
                    failfast=failfast,
                )
                loop.run_until_complete(
                    asyncio.wait_for(
                        terminate_worker.terminate_tasks_interrupted(), None
                    )
                )
                raise
        except (KeyboardInterrupt, asyncio.TimeoutError, JobFailFast) as ex:
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
        summary.update(
            [
                status.upper()
                for status in self.status_repo.get_result_set_for_tasks(test_ids)
            ]
        )
        return summary
