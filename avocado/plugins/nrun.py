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

    @staticmethod
    @asyncio.coroutine
    def spawn_task(task):
        status_service_args = []
        for status_service in task.status_services:
            status_service_args.append('-s')
            status_service_args.append(status_service.uri)

        task_args = []
        if task.runnable.args is not None:
            for arg in task.runnable.args:
                task_args.append('-a')
                task_args.append(arg)

        runner_args = []
        if task.runnable.uri is not None:
            runner_args += ['-u', task.runnable.uri]

        args = ['-m', 'avocado.core.nrunner',
                'task-run',
                '-i', task.identifier,
                '-k', task.runnable.kind]

        args += list(task_args)
        args += list(runner_args)
        args += list(status_service_args)

        #pylint: disable=E1133
        yield from asyncio.create_subprocess_exec(
            sys.executable,
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
        self.pending_tasks = self.suite_to_tasks(suite, [config.get('status_server')])

        if not self.pending_tasks:
            LOG_UI.error('No test to be executed, exiting...')
            sys.exit(exit_codes.AVOCADO_JOB_FAIL)

        if not config.get('disable_task_randomization'):
            random.shuffle(self.pending_tasks)

        self.spawned_tasks = []

        try:
            loop = asyncio.get_event_loop()
            self.status_server = nrunner.StatusServer(config.get('status_server'),
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
