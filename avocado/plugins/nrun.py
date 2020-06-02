import asyncio
import multiprocessing
import os
import random
import sys

from avocado.core import exit_codes
from avocado.core import job
from avocado.core import nrunner
from avocado.core import parser_common_args
from avocado.core import resolver
from avocado.core.spawners.process import ProcessSpawner
from avocado.core.spawners.podman import PodmanSpawner
from avocado.core.future.settings import settings
from avocado.core.output import LOG_UI
from avocado.core.parser import HintParser
from avocado.core.test_id import TestID
from avocado.core.plugin_interfaces import CLICmd


class NRun(CLICmd):

    name = 'nrun'
    description = "*EXPERIMENTAL* runner: runs one or more tests"

    def configure(self, parser):
        parser = super(NRun, self).configure(parser)
        help_msg = 'List of test references (aliases or paths)'
        settings.register_option(section='nrun',
                                 key='references',
                                 default=[],
                                 key_type=list,
                                 help_msg=help_msg,
                                 nargs='*',
                                 parser=parser,
                                 metavar="TEST_REFERENCE",
                                 positional_arg=True)

        help_msg = 'Disable task shuffle'
        settings.register_option(section='nrun',
                                 key='disable_task_randomization',
                                 default=False,
                                 help_msg=help_msg,
                                 key_type=bool,
                                 parser=parser,
                                 long_arg='--disable-task-randomization')

        help_msg = ('Number of parallel tasks to run the tests. You can '
                    'disable parallel execution by passing 1.')
        settings.register_option(section='nrun',
                                 key='parallel_tasks',
                                 default=2 * multiprocessing.cpu_count() - 1,
                                 key_type=int,
                                 help_msg=help_msg,
                                 parser=parser,
                                 long_arg='--parallel-tasks')

        help_msg = 'Host and port for the status server'
        settings.register_option(section='nrun.status_server',
                                 key='listen',
                                 default='127.0.0.1:8888',
                                 metavar="HOST:PORT",
                                 help_msg=help_msg,
                                 parser=parser,
                                 long_arg='--status-server')

        help_msg = ("Spawn tests in a specific spawner. Available spawners: "
                    "'process' and 'podman'")
        settings.register_option(section="nrun",
                                 key="spawner",
                                 default='process',
                                 help_msg=help_msg,
                                 parser=parser,
                                 long_arg="--spawner")

        parser_common_args.add_tag_filter_args(parser)

    async def spawn_tasks(self, parallel_tasks):
        while True:
            while len(set(self.status_server.tasks_pending).intersection(self.spawned_tasks)) >= parallel_tasks:
                await asyncio.sleep(0.1)

            try:
                task = self.pending_tasks[0]
            except IndexError:
                LOG_UI.info("Finished spawning tasks")
                break

            spawn_result = await self.spawner.spawn_task(task)
            identifier = task.identifier
            self.pending_tasks.remove(task)
            self.spawned_tasks.append(identifier)
            if not spawn_result:
                LOG_UI.error("ERROR: failed to spawn task: %s", identifier)
                continue

            alive = self.spawner.is_task_alive(task)
            if not alive:
                LOG_UI.warning("%s is not alive shortly after being spawned", identifier)
            else:
                LOG_UI.info("%s spawned and alive", identifier)

    def report_results(self):
        """Reports a summary, with verbose listing of fail/error tasks."""
        summary = {status: len(tasks)
                   for (status, tasks) in self.status_server.result.items()}
        LOG_UI.info("Tasks result summary: %s", summary)
        for status, tasks in self.status_server.result.items():
            if status in ('fail', 'error'):
                LOG_UI.error("Tasks ended with '%s': %s",
                             status, ", ".join(tasks))

    def run(self, config):
        hint_filepath = '.avocado.hint'
        hint = None
        if os.path.exists(hint_filepath):
            hint = HintParser(hint_filepath)
        resolutions = resolver.resolve(config.get('nrun.references'), hint)
        tasks = job.resolutions_to_tasks(resolutions, config)
        # pylint: disable=W0201
        self.pending_tasks, missing_requirements = nrunner.check_tasks_requirements(tasks)
        if missing_requirements:
            missing_tasks_msg = "\n".join([str(t) for t in missing_requirements])
            LOG_UI.warning('Tasks will not be run due to missing requirements: %s',
                           missing_tasks_msg)

        if not self.pending_tasks:
            LOG_UI.error('No test to be executed, exiting...')
            sys.exit(exit_codes.AVOCADO_JOB_FAIL)

        for index, task in enumerate(self.pending_tasks, start=1):
            task.identifier = str(TestID(index, task.runnable.uri))

        if not config.get('nrun.disable_task_randomization'):
            random.shuffle(self.pending_tasks)

        self.spawned_tasks = []  # pylint: disable=W0201

        try:
            if config.get('nrun.spawner') == 'podman':
                if not os.path.exists(PodmanSpawner.PODMAN_BIN):
                    msg = ('Podman Spawner selected, but podman binary "%s" '
                           'is not available on the system.  Please install '
                           'podman before attempting to use this feature.')
                    msg %= PodmanSpawner.PODMAN_BIN
                    LOG_UI.error(msg)
                    sys.exit(exit_codes.AVOCADO_JOB_FAIL)
                self.spawner = PodmanSpawner()  # pylint: disable=W0201
            elif config.get('nrun.spawner') == 'process':
                self.spawner = ProcessSpawner()  # pylint: disable=W0201
            else:
                LOG_UI.error("Spawner not implemented or invalid.")
                sys.exit(exit_codes.AVOCADO_JOB_FAIL)

            listen = config.get('nrun.status_server.listen')
            verbose = config.get('core.verbose')
            self.status_server = nrunner.StatusServer(listen,  # pylint: disable=W0201
                                                      [t.identifier for t in
                                                       self.pending_tasks],
                                                      verbose)
            self.status_server.start()
            parallel_tasks = config.get('nrun.parallel_tasks')
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.spawn_tasks(parallel_tasks))
            loop.run_until_complete(self.status_server.wait())
            self.report_results()
            exit_code = exit_codes.AVOCADO_ALL_OK
            if self.status_server.result.get('fail') is not None:
                exit_code |= exit_codes.AVOCADO_TESTS_FAIL
            elif self.status_server.result.get('error') is not None:
                exit_code |= exit_codes.AVOCADO_TESTS_FAIL
            return exit_code
        except Exception as e:  # pylint: disable=W0703
            LOG_UI.error(e)
            return exit_codes.AVOCADO_FAIL
