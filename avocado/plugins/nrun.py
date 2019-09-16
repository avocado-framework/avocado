import asyncio
import multiprocessing
import os
import random
import sys

from avocado.core import nrunner
from avocado.core import loader
from avocado.core import exit_codes
from avocado.core import exceptions
from avocado.core import test
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLICmd
from avocado.utils import stacktrace
from avocado.utils import path as utils_path


class NRun(CLICmd):

    name = 'nrun'
    description = "*EXPERIMENTAL* runner: runs one or more tests"

    KNOWN_EXTERNAL_RUNNERS = {}

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

    @staticmethod
    def create_test_suite(references):
        """
        Creates the test suite for this Job

        This is a public Job API as part of the documented Job phases

        NOTE: This is similar to avocado.core.Job.create_test_suite
        """
        try:
            suite = loader.loader.discover(references)
        except loader.LoaderError as details:
            stacktrace.log_exc_info(sys.exc_info(), LOG_UI.getChild("debug"))
            raise exceptions.OptionValidationError(details)

        if not suite:
            if references:
                references = " ".join(references)
                e_msg = ("No tests found for given test references, try "
                         "'avocado list -V %s' for details" % references)
            else:
                e_msg = ("No test references provided nor any other arguments "
                         "resolved into tests. Please double check the "
                         "executed command.")
            raise exceptions.OptionValidationError(e_msg)

        return suite

    @staticmethod
    def suite_to_tasks(suite, status_uris):
        tasks = []
        index = 0
        no_digits = len(str(len(suite)))
        for factory in suite:
            klass, args = factory
            name = args.get("name")
            identifier = str(test.TestID(index + 1, name, None, no_digits))
            if klass == test.PythonUnittest:
                test_dir = args.get("test_dir")
                module_prefix = test_dir.split(os.getcwd())[1][1:]
                module_prefix = module_prefix.replace("/", ".")
                unittest_path = "%s.%s" % (module_prefix, args.get("name"))
                runnable = nrunner.Runnable('python-unittest', unittest_path)
            elif klass == test.SimpleTest:
                runnable = nrunner.Runnable('exec-test', args.get('executable'))
            elif isinstance(klass, str):
                runnable = nrunner.Runnable('avocado-instrumented', name)
            else:
                # FIXME: This should instead raise an error
                print('WARNING: unknown test type "%s", using "noop"' % factory[0])
                runnable = nrunner.Runnable('noop')

            tasks.append(nrunner.Task(identifier, runnable, status_uris))
            index += 1
        return tasks

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

            yield from self.spawn_task(task)
            identifier = task.identifier
            self.pending_tasks.remove(task)
            self.spawned_tasks.append(identifier)
            print("%s spawned" % identifier)

    def pick_runner(self, task):
        kind = task.runnable.kind
        runner = self.KNOWN_EXTERNAL_RUNNERS.get(kind)
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
            self.KNOWN_EXTERNAL_RUNNERS[kind] = runner
            return runner

        # try to find executable in the path
        runner_by_name = 'avocado-runner-%s' % kind
        try:
            runner = utils_path.find_command(runner_by_name)
            self.KNOWN_EXTERNAL_RUNNERS[kind] = [runner]
            return [runner]
        except utils_path.CmdNotFoundError:
            self.KNOWN_EXTERNAL_RUNNERS[kind] = False

    @asyncio.coroutine
    def spawn_task(self, task):
        status_service_args = []
        for status_service in task.status_services:
            status_service_args.append('-s')
            status_service_args.append(status_service.uri)

        runnable_args = nrunner.runnable_to_command_line_args(task.runnable)

        args = ['task-run',
                '-i', task.identifier]

        args += list(runnable_args)
        args += list(status_service_args)

        runner = self.pick_runner(task)
        if runner is None:
            runner = [sys.executable, '-m', 'avocado.core.nrunner']

        args = runner[1:] + args
        runner = runner[0]

        #pylint: disable=E1133
        yield from asyncio.create_subprocess_exec(
            runner,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)

    def run(self, config):
        try:
            loader.loader.load_plugins(config)
        except loader.LoaderError as details:
            sys.stderr.write(str(details))
            sys.stderr.write('\n')
            sys.exit(exit_codes.AVOCADO_FAIL)

        suite = self.create_test_suite(config.get('references'))
        self.pending_tasks = self.suite_to_tasks(suite, [config.get('status_server')])  # pylint: disable=W0201

        if not self.pending_tasks:
            LOG_UI.error('No test to be executed, exiting...')
            sys.exit(exit_codes.AVOCADO_JOB_FAIL)

        if not config.get('disable_task_randomization'):
            random.shuffle(self.pending_tasks)

        self.spawned_tasks = []  # pylint: disable=W0201

        try:
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
        except Exception as e:
            LOG_UI.error(e)
            return exit_codes.AVOCADO_FAIL
