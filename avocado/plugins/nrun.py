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
from avocado.core.future.settings import settings
from avocado.core.output import LOG_UI
from avocado.core.parser import HintParser
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

        settings.register_option(section="nrun.spawners.podman",
                                 key="enabled",
                                 default=False,
                                 key_type=bool,
                                 help_msg="Spawn tests in podman containers",
                                 parser=parser,
                                 long_arg="--podman-spawner")

        parser_common_args.add_tag_filter_args(parser)

    @asyncio.coroutine
    def spawn_tasks(self, parallel_tasks):
        while True:
            while len(set(self.status_server.tasks_pending).intersection(self.spawned_tasks)) >= parallel_tasks:
                yield from asyncio.sleep(0.1)

            try:
                task = self.pending_tasks[0]
            except IndexError:
                print("Finished spawning tasks")
                break

            yield from self.spawner.spawn_task(task)
            identifier = task.identifier
            self.pending_tasks.remove(task)
            self.spawned_tasks.append(identifier)
            alive = self.spawner.is_task_alive(task)
            if not alive:
                LOG_UI.warning("%s is not alive shortly after being spawned", identifier)
            else:
                LOG_UI.info("%s spawned and alive", identifier)

    @asyncio.coroutine
    def spawn_task(self, task):
        runner = task.pick_runner_command()
        if runner is False:
            LOG_UI.error('Task "%s" has no matching runner. ', task)
            LOG_UI.error('This is an error condition and should have been caught '
                         'when checking task requirements.')
            sys.exit(exit_codes.AVOCADO_FAIL)

        args = runner[1:] + ['task-run'] + task.get_command_args()
        runner = runner[0]

        #pylint: disable=E1133
        yield from asyncio.create_subprocess_exec(
            runner,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)

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

        if not config.get('nrun.disable_task_randomization'):
            random.shuffle(self.pending_tasks)

        self.spawned_tasks = []  # pylint: disable=W0201

        try:
            if config.get('nrun.spawners.podman.enabled'):
                if not os.path.exists(nrunner.PodmanSpawner.PODMAN_BIN):
                    msg = ('Podman Spawner selected, but podman binary "%s" '
                           'is not available on the system.  Please install '
                           'podman before attempting to use this feature.')
                    msg %= nrunner.PodmanSpawner.PODMAN_BIN
                    LOG_UI.error(msg)
                    sys.exit(exit_codes.AVOCADO_JOB_FAIL)
                self.spawner = nrunner.PodmanSpawner()  # pylint: disable=W0201
            else:
                self.spawner = nrunner.ProcessSpawner()  # pylint: disable=W0201
            loop = asyncio.get_event_loop()
            listen = config.get('nrun.status_server.listen')
            self.status_server = nrunner.StatusServer(listen,  # pylint: disable=W0201
                                                      [t.identifier for t in
                                                       self.pending_tasks])
            self.status_server.start()
            parallel_tasks = config.get('nrun.parallel_tasks')
            loop.run_until_complete(self.spawn_tasks(parallel_tasks))
            loop.run_until_complete(self.status_server.wait())
            print(self.status_server.result)
            exit_code = exit_codes.AVOCADO_ALL_OK
            if self.status_server.result.get('fail') is not None:
                exit_code |= exit_codes.AVOCADO_TESTS_FAIL
            elif self.status_server.result.get('error') is not None:
                exit_code |= exit_codes.AVOCADO_TESTS_FAIL
            return exit_code
        except Exception as e:  # pylint: disable=W0703
            LOG_UI.error(e)
            return exit_codes.AVOCADO_FAIL
