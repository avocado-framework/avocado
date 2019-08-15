import argparse
import asyncio
import base64
import io
import json
import multiprocessing
import subprocess
import time
import unittest
import socket

#: The amount of time (in seconds) between each internal status check
RUNNER_RUN_CHECK_INTERVAL = 0.01

#: The amount of time (in seconds) between a status report from a
#: runner that performs its work asynchronously
RUNNER_RUN_STATUS_INTERVAL = 0.5


class Runnable:
    """
    Describes an entity that be executed in the context of a task

    A instance of :class:`BaseRunner` is the entity that will actually
    execute a runnable.
    """
    def __init__(self, kind, uri=None, *args, **kwargs):
        self.kind = kind
        self.uri = uri
        self.args = args
        self.kwargs = kwargs

    def __repr__(self):
        fmt = '<Runnable kind="{}" uri="{}" args="{}" kwargs="{}"'
        return fmt.format(self.kind, self.uri,
                          self.args, self.kwargs)


def runnable_from_recipe(recipe_path):
    """
    Returns a runnable from a runnable recipe file
    """
    with open(recipe_path) as recipe_file:
        recipe = json.load(recipe_file)
    return Runnable(recipe.get('kind'),
                    recipe.get('uri'),
                    *recipe.get('args', ()))


class BaseRunner:
    """
    Base interface for a Runner
    """

    def __init__(self, runnable):
        self.runnable = runnable

    def run(self):
        yield {}


class NoOpRunner(BaseRunner):
    """
    Sample runner that performs no action before reporting FINISHED status
    """
    def run(self):
        yield {'status': 'finished'}


class ExecRunner(BaseRunner):
    """
    Runner for standalone executables with or without arguments
    """
    def run(self):
        process = subprocess.Popen(
            [self.runnable.uri] + list(self.runnable.args),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)

        last_status = None
        while process.poll() is None:
            time.sleep(RUNNER_RUN_CHECK_INTERVAL)
            now = time.time()
            if last_status is None or now > last_status + RUNNER_RUN_STATUS_INTERVAL:
                last_status = now
                yield {'status': 'running'}

        stdout = process.stdout.read()
        process.stdout.close()
        stderr = process.stderr.read()
        process.stderr.close()

        yield {'status': 'finished',
               'returncode': process.returncode,
               'stdout': stdout,
               'stderr': stderr}


class ExecTestRunner(ExecRunner):
    """
    Runner for standalone executables treated as tests

    This is similar in concept to the Avocado "SIMPLE" test type, in which an
    executable returning 0 means that a test passed, and anything else means
    that a test failed.
    """
    def run(self):
        for status in super(ExecTestRunner, self).run():
            if 'returncode' in status:
                if status['returncode'] == 0:
                    status['status'] = 'pass'
                else:
                    status['status'] = 'fail'
            yield status


class PythonUnittestRunner(BaseRunner):
    """
    Runner for Python unittests

    The runnable uri is used as the test name that the native unittest
    TestLoader will use to find the test.  A native unittest test
    runner (TextTestRunner) will be used to execute the test.
    """
    @staticmethod
    def _run_unittest(uri, queue):
        stream = io.StringIO()
        suite = unittest.TestLoader().loadTestsFromName(uri)
        runner = unittest.TextTestRunner(stream=stream, verbosity=0)
        unittest_result = runner.run(suite)

        if len(unittest_result.errors) > 0:
            status = 'error'
        elif len(unittest_result.failures) > 0:
            status = 'fail'
        elif len(unittest_result.skipped) > 0:
            status = 'skip'
        else:
            status = 'pass'

        stream.seek(0)
        result = {'status': status,
                  'output': stream.read()}
        stream.close()
        queue.put(result)

    def run(self):
        if not self.runnable.uri:
            yield {'status': 'error',
                   'output': 'uri is required but was not given'}
            return

        queue = multiprocessing.SimpleQueue()
        process = multiprocessing.Process(target=self._run_unittest,
                                          args=(self.runnable.uri, queue))
        process.start()

        last_status = None
        while queue.empty():
            time.sleep(RUNNER_RUN_CHECK_INTERVAL)
            now = time.time()
            if last_status is None or now > last_status + RUNNER_RUN_STATUS_INTERVAL:
                last_status = now
                yield {'status': 'running'}

        yield queue.get()


def runner_from_runnable(runnable):
    """
    Gets a Runner instance from a Runnable
    """
    if runnable.kind == 'noop':
        return NoOpRunner(runnable)
    if runnable.kind == 'exec':
        return ExecRunner(runnable)
    if runnable.kind == 'exec-test':
        return ExecTestRunner(runnable)
    if runnable.kind == 'python-unittest':
        return PythonUnittestRunner(runnable)
    raise ValueError('Unsupported kind of runnable: %s' % runnable.kind)


CMD_RUNNABLE_RUN_ARGS = (
    (("-k", "--kind"),
     {'type': str, 'required': True, 'help': 'Kind of runnable'}),

    (("-u", "--uri"),
     {'type': str, 'default': None, 'help': 'URI of runnable'}),

    (("-a", "--arg"),
     {'action': "append", 'default': [], 'help': 'Positional arguments to runnable'})
    )


def runnable_from_args(args):
    return Runnable(args.get('kind'),
                    args.get('uri'),
                    *args.get('arg', ()))


def subcommand_runnable_run(args, echo=print):
    runnable = runnable_from_args(args)
    runner = runner_from_runnable(runnable)

    for status in runner.run():
        echo(status)


CMD_RUNNABLE_RUN_RECIPE_ARGS = (
    (("recipe", ),
     {'type': str, 'help': 'Path to the runnable recipe file'}),
    )


def subcommand_runnable_run_recipe(args, echo=print):
    runnable = runnable_from_recipe(args.get('recipe'))
    runner = runner_from_runnable(runnable)

    for status in runner.run():
        echo(status)


class StatusEncoder(json.JSONEncoder):

    # pylint: disable=E0202
    def default(self, o):
        if isinstance(o, bytes):
            return {'__base64_encoded__': base64.b64encode(o).decode('ascii')}
        return json.JSONEncoder.default(self, o)


def json_base64_decode(dct):
    if '__base64_encoded__' in dct:
        return base64.b64decode(dct['__base64_encoded__'])
    return dct


def json_dumps(data):
    return json.dumps(data, ensure_ascii=True, cls=StatusEncoder)


def json_loads(data):
    if isinstance(data, bytes):
        data = data.decode()
    return json.loads(data, object_hook=json_base64_decode)


class TaskStatusService:
    """
    Implementation of interface that a task can use to post status updates

    TODO: make the interface generic and this just one of the implementations
    """
    def __init__(self, uri):
        self.uri = uri
        self.connection = None

    def post(self, status):
        host, port = self.uri.split(':')
        port = int(port)
        if self.connection is None:
            self.connection = socket.create_connection((host, port))

        data = json_dumps(status)
        self.connection.send(data.encode('ascii') + "\n".encode('ascii'))

    def close(self):
        if self.connection is not None:
            self.connection.close()

    def __repr__(self):
        return '<TaskStatusService uri="{}">'.format(self.uri)


class Task:
    """
    Wraps the execution of a runnable

    While a runnable describes what to be run, and gets run by a
    runner, a task should be a unique entity to track its state,
    that is, whether it is pending, is running or has finished.

    :param identifier:
    :param runnable:
    """
    def __init__(self, identifier, runnable, status_uris=None):
        self.identifier = identifier
        self.runnable = runnable
        self.status_services = []
        if status_uris is not None:
            for status_uri in status_uris:
                self.status_services.append(TaskStatusService(status_uri))

    def run(self):
        runner = runner_from_runnable(self.runnable)
        for status in runner.run():
            status.update({"id": self.identifier})
            for status_service in self.status_services:
                status_service.post(status)
            yield status

    def __repr__(self):
        fmt = '<Task identifier="{}" runnable="{}" status_services="{}"'
        return fmt.format(self.identifier, self.runnable, self.status_services)


def task_from_recipe(task_path):
    """
    Creates a task (which contains a runnable) from a task recipe file
    """
    with open(task_path) as recipe_file:
        recipe = json.load(recipe_file)
    identifier = recipe.get('id')
    runnable_recipe = recipe.get('runnable')
    runnable = Runnable(runnable_recipe.get('kind'),
                        runnable_recipe.get('uri'),
                        *runnable_recipe.get('args', ()))
    status_uris = recipe.get('status_uris')
    return Task(identifier, runnable, status_uris)


class StatusServer:

    def __init__(self, uri, tasks_pending=None):
        self.uri = uri
        self.server_task = None
        self.status = {}
        if tasks_pending is None:
            tasks_pending = []
        self.tasks_pending = tasks_pending
        self.wait_on_tasks_pending = len(self.tasks_pending) > 0

    @asyncio.coroutine
    def cb(self, reader, _):
        while True:
            if self.wait_on_tasks_pending:
                if not self.tasks_pending:
                    print('Status server: exiting due to all tasks finished')
                    self.server_task.cancel()
                    yield from self.server_task
                    return True

            message = yield from reader.readline()
            if message == b'bye\n':
                print('Status server: exiting due to user request')
                self.server_task.cancel()
                yield from self.server_task
                return True

            if not message:
                return False

            data = json_loads(message.strip())

            if data['status'] not in ["init", "running"]:
                try:
                    self.tasks_pending.remove(data['id'])
                    print('Task complete (%s): %s' % (data['status'],
                                                      data['id']))
                except IndexError:
                    pass
                except ValueError:
                    pass
                if data['status'] in self.status:
                    self.status[data['status']] += 1
                else:
                    self.status[data['status']] = 1

                if data['status'] not in ('pass', 'skip'):
                    stdout = data.get('stdout', b'')
                    if stdout:
                        print('Task %s stdout:\n%s\n' % (data['id'], stdout))
                    stderr = data.get('stderr', b'')
                    if stderr:
                        print('Task %s stderr:\n%s\n' % (data['id'], stderr))
                    output = data.get('output', b'')
                    if output:
                        print('Task %s output:\n%s\n' % (data['id'], output))

    @asyncio.coroutine
    def create_server_task(self):
        host, port = self.uri.split(':')
        port = int(port)
        server = yield from asyncio.start_server(self.cb, host=host, port=port)
        print("Results server started at:", self.uri)
        yield from server.wait_closed()

    def start(self):
        loop = asyncio.get_event_loop()
        self.server_task = loop.create_task(self.create_server_task())

    @asyncio.coroutine
    def wait(self):
        while not self.server_task.done():
            yield from asyncio.sleep(0.1)


CMD_TASK_RUN_ARGS = (
    (("-i", "--identifier"),
     {'type': str, 'required': True, 'help': 'Task unique identifier'}),
    (("-s", "--status-uri"),
     {'action': "append", 'default': None,
      'help': 'URIs of status services to report to'}),
    )
CMD_TASK_RUN_ARGS += CMD_RUNNABLE_RUN_ARGS


def task_run(task, echo):
    for status in task.run():
        echo(status)


def subcommand_task_run(args, echo=print):
    runnable = runnable_from_args(args)
    task = Task(args.get('identifier'), runnable,
                args.get('status_uri', []))
    task_run(task, echo)


CMD_TASK_RUN_RECIPE_ARGS = (
    (("recipe", ),
     {'type': str, 'help': 'Path to the task recipe file'}),
    )


def subcommand_task_run_recipe(args, echo=print):
    task = task_from_recipe(args.get('recipe'))
    task_run(task, echo)


CMD_STATUS_SERVER_ARGS = (
    (("uri", ),
     {'type': str, 'help': 'URI to bind a status server to'}),
    )


def subcommand_status_server(args):
    server = StatusServer(args.get('uri'))
    server.start()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(server.wait())


def parse():
    parser = argparse.ArgumentParser(prog='nrunner')
    subcommands = parser.add_subparsers(dest='subcommand')
    subcommands.required = True
    runnable_run_parser = subcommands.add_parser('runnable-run')
    for arg in CMD_RUNNABLE_RUN_ARGS:
        runnable_run_parser.add_argument(*arg[0], **arg[1])
    runnable_run_recipe_parser = subcommands.add_parser('runnable-run-recipe')
    for arg in CMD_RUNNABLE_RUN_RECIPE_ARGS:
        runnable_run_recipe_parser.add_argument(*arg[0], **arg[1])
    runnable_task_parser = subcommands.add_parser('task-run')
    for arg in CMD_TASK_RUN_ARGS:
        runnable_task_parser.add_argument(*arg[0], **arg[1])
    runnable_task_recipe_parser = subcommands.add_parser('task-run-recipe')
    for arg in CMD_TASK_RUN_RECIPE_ARGS:
        runnable_task_recipe_parser.add_argument(*arg[0], **arg[1])
    status_server_parser = subcommands.add_parser('status-server')
    for arg in CMD_STATUS_SERVER_ARGS:
        status_server_parser.add_argument(*arg[0], **arg[1])

    return parser.parse_args()


def main():
    args = vars(parse())
    subcommand = args.get('subcommand')
    if subcommand == 'runnable-run':
        subcommand_runnable_run(args)
    elif subcommand == 'runnable-run-recipe':
        subcommand_runnable_run_recipe(args)
    elif subcommand == 'task-run':
        subcommand_task_run(args)
    elif subcommand == 'task-run-recipe':
        subcommand_task_run_recipe(args)
    elif subcommand == 'status-server':
        subcommand_status_server(args)


if __name__ == '__main__':
    main()
