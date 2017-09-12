import asyncio
import multiprocessing
import random
import sys

from avocado.core import nrunner
from avocado.core import resolver
from avocado.core import exit_codes
from avocado.core import test
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLICmd


class NRun(CLICmd):

    name = 'nrun'
    description = "*EXPERIMENTAL* runner: runs one or more tests"

    def configure(self, parser):
        parser = super(NRun, self).configure(parser)
        parser.add_argument("reference", type=str, default=[], nargs='*',
                            metavar="TEST_REFERENCE",
                            help='List of test references (aliases or paths)')
        parser.add_argument("--disable-task-randomization",
                            action="store_true", default=False)
        parser.add_argument("--status-server", default="127.0.0.1:8888",
                            metavar="HOST:PORT",
                            help="Host and port for status server, default is: %(default)s")

    @staticmethod
    def resolutions_to_tasks(resolutions, status_uris):
        tasks = []
        index = 0
        resolutions = [res for res in resolutions if
                       res.result == resolver.ReferenceResolutionResult.SUCCESS]
        no_digits = len(str(len(resolutions)))
        for resolution in resolutions:
            name = resolution.reference
            for runnable in resolution.resolutions:
                if runnable.uri:
                    name = runnable.uri
                identifier = str(test.TestID(index + 1, name, None, no_digits))
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

    def run(self, args):
        resolutions = resolver.resolve(args.reference)
        self.pending_tasks = self.resolutions_to_tasks(resolutions, [args.status_server])

        if not args.disable_task_randomization:
            random.shuffle(self.pending_tasks)

        self.spawned_tasks = []

        try:
            loop = asyncio.get_event_loop()
            self.status_server = nrunner.StatusServer(args.status_server,
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
