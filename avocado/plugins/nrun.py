import asyncio
import enum
import json
import multiprocessing
import os
import random
import sys

from avocado.core import exit_codes
from avocado.core import job
from avocado.core import nrunner
from avocado.core import parser_common_args
from avocado.core import resolver
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLICmd
from avocado.utils import path as utils_path


#: All the known runners
KNOWN_EXTERNAL_RUNNERS = {}


class TaskSpawnStatus(enum.Enum):
    #: The spawning of a task was perceived to be correct
    SUCCESS = object()
    #: The status has progressed further and the task has
    #: produced and notified of some execution update, or
    #: the spawning system could check the execution model
    #: is up and running
    RUNNING = object()
    #: The spawning of the task has failed early and it's
    #: not expected that it will produce any status
    FAILURE = object()


class BaseTaskIsolationModel:

    def pre(self):
        pass

    def spawn(self, task, args=None):
        pass

    def is_running(self, task):
        pass

    def cleanup(self):
        pass


class ProcessTaskIsolationModel(BaseTaskIsolationModel):

    def _pick_runner_or_default(self, task):
        runner = pick_runner(task, KNOWN_EXTERNAL_RUNNERS)
        if runner is None:
            runner = [sys.executable, '-m', 'avocado.core.nrunner']
        return runner

    @asyncio.coroutine
    def spawn(self, task, args=None):
        runner = self._pick_runner_or_default(task)
        args = runner[1:] + ['task-run'] + task.get_command_args()
        runner = runner[0]

        #pylint: disable=E1133
        yield from asyncio.create_subprocess_exec(
            runner,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)


class PodmanTaskIsolationModel(BaseTaskIsolationModel):

    PODMAN_IMAGE = 'fedora:31'

    @asyncio.coroutine
    def spawn(self, task, args=None):
        entry_point_cmd = '/tmp/avocado-runner'
        entry_point_args = task.get_command_args()
        entry_point_args.insert(0, "task-run")
        entry_point_args.insert(0, entry_point_cmd)
        entry_point = json.dumps(entry_point_args)
        entry_point_arg = "--entrypoint=" + entry_point

        proc = yield from asyncio.create_subprocess_exec(
            "/usr/bin/podman", "create",
            "--net=host",
            entry_point_arg,
            self.PODMAN_IMAGE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)

        res = yield from proc.wait()
        stdout = yield from proc.stdout.read()
        container_id = stdout.decode().strip()

        # Currently limited to avocado-runner, we'll expand on that
        # when the runner requirements system is in place
        this_path = os.path.abspath(__file__)
        common_path = os.path.dirname(os.path.dirname(this_path))
        avocado_runner_path = os.path.join(common_path, 'core', 'nrunner.py')
        proc = yield from asyncio.create_subprocess_exec(
            "/usr/bin/podman",
            "cp",
            avocado_runner_path,
            f"{container_id}:{entry_point_cmd}")
        yield from proc.wait()

        proc = yield from asyncio.create_subprocess_exec("/usr/bin/podman",
                                                         "start",
                                                         container_id,
                                                         stdout=asyncio.subprocess.PIPE,
                                                         stderr=asyncio.subprocess.PIPE)
        yield from proc.wait()


def pick_runner(task, runners_registry):
    """
    Selects a runner based on the task and keeps found runners in registry

    This utility function will look at the given task and try to find
    a matching runner.  The matching runner probe results are kept in
    a registry (that is modified by this function) so that further
    executions take advantage of previous probes.

    :param task: the task that needs a runner to be selected
    :type task: :class:`avocado.core.nrunner.Task`
    :param runners_registry: a registry with previously found (and not
                             found) runners keyed by task kind
    :param runners_registry: dict
    :returns: command line arguments to execute the runner
    :rtype: list of str
    """
    kind = task.runnable.kind
    runner = runners_registry.get(kind)
    if runner is False:
        return None
    if runner is not None:
        return runner

    # first attempt to find Python module files that are named
    # after the runner convention within the avocado.core
    # namespace dir.  Looking for the file only avoids an attempt
    # to load the module and should be a lot faster
    core_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    module_name = kind.replace('-', '_')
    module_filename = 'nrunner_%s.py' % module_name
    if os.path.exists(os.path.join(core_dir, module_filename)):
        full_module_name = 'avocado.core.%s' % module_name
        runner = [sys.executable, '-m', full_module_name]
        runners_registry[kind] = runner
        return runner

    # try to find executable in the path
    runner_by_name = 'avocado-runner-%s' % kind
    try:
        runner = utils_path.find_command(runner_by_name)
        runners_registry[kind] = [runner]
        return [runner]
    except utils_path.CmdNotFoundError:
        runners_registry[kind] = False


def check_tasks_requirements(tasks, runners_registry):
    """
    Checks if tasks have runner requirements fulfilled

    :param tasks: the tasks whose runner requirements will be checked
    :type tasks: list of :class:`avocado.core.nrunner.Task`
    :param runners_registry: a registry with previously found (and not
                             found) runners keyed by task kind
    :param runners_registry: dict
    """
    result = []
    for task in tasks:
        runner = pick_runner(task, runners_registry)
        if runner:
            result.append(task)
        else:
            LOG_UI.warning('Task will not be run due to missing requirements: %s', task)
    return result


class NRun(CLICmd):

    name = 'nrun'
    description = "*EXPERIMENTAL* runner: runs one or more tests"


    def configure(self, parser):
        parser = super(NRun, self).configure(parser)
        parser.add_argument("references", type=str, default=[], nargs='*',
                            metavar="TEST_REFERENCE",
                            help='List of test references (aliases or paths)')
        parser.add_argument("--disable-task-randomization",
                            action="store_true", default=False)
        parser.add_argument("--status-server", default="127.0.0.1:8888",
                            metavar="HOST:PORT",
                            help="Host and port for status server, default is: %(default)s")
        parser.add_argument("--podman", action="store_true", default=False)
        parser_common_args.add_tag_filter_args(parser)

    @asyncio.coroutine
    def spawn_tasks(self):
        number_of_runnables = 2 * multiprocessing.cpu_count() - 1
        while True:
            while len(set(self.status_server.tasks_pending).intersection(self.spawned_tasks)) >= number_of_runnables:
                yield from asyncio.sleep(0.1)

            try:
                task = self.pending_tasks[0]
            except IndexError:
                print("Finished spawning tasks")
                break

            self.isolation_model.pre()
            yield from self.isolation_model.spawn(task)
            self.isolation_model.cleanup()

            identifier = task.identifier
            self.pending_tasks.remove(task)
            self.spawned_tasks.append(identifier)
            print("%s spawned" % identifier)

    def run(self, config):
        resolutions = resolver.resolve(config.get('references'))
        tasks = job.resolutions_to_tasks(resolutions, config)
        self.pending_tasks = check_tasks_requirements(   # pylint: disable=W0201
            tasks,
            KNOWN_EXTERNAL_RUNNERS)

        if not self.pending_tasks:
            LOG_UI.error('No test to be executed, exiting...')
            sys.exit(exit_codes.AVOCADO_JOB_FAIL)

        if not config.get('disable_task_randomization'):
            random.shuffle(self.pending_tasks)

        self.spawned_tasks = []  # pylint: disable=W0201

        try:
            if config.get('podman'):
                self.isolation_model = PodmanTaskIsolationModel()  # pylint: disable=W0201
            else:
                self.isolation_model = ProcessTaskIsolationModel() # pylint: disable=W0201

            loop = asyncio.get_event_loop()
            self.status_server = nrunner.StatusServer(config.get('status_server'),  # pylint: disable=W0201
                                                      [t.identifier for t in
                                                       self.pending_tasks])
            self.status_server.start()
            loop.run_until_complete(self.spawn_tasks())
            loop.run_until_complete(self.status_server.wait())
            print(self.status_server.status)
            exit_code = exit_codes.AVOCADO_ALL_OK
            if self.status_server.status.get('fail') is not None:
                exit_code |= exit_codes.AVOCADO_TESTS_FAIL
            elif self.status_server.status.get('error') is not None:
                exit_code |= exit_codes.AVOCADO_TESTS_FAIL
            return exit_code
        except Exception as e:  # pylint: disable=W0703
            LOG_UI.error(e)
            return exit_codes.AVOCADO_FAIL
