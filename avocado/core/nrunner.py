import argparse
import asyncio
import base64
import collections
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
    def __init__(self, kind, uri, *args, **kwargs):
        self.kind = kind
        self.uri = uri
        self.args = args
        self.tags = kwargs.pop('tags', None)
        self.kwargs = kwargs

    def __repr__(self):
        fmt = '<Runnable kind="{}" uri="{}" args="{}" kwargs="{}" tags="{}">'
        return fmt.format(self.kind, self.uri,
                          self.args, self.kwargs, self.tags)

    @classmethod
    def from_args(cls, args):
        """Returns a runnable from arguments"""
        decoded_args = [_arg_decode_base64(arg) for arg in args.get('arg', ())]
        return cls(args.get('kind'),
                   args.get('uri'),
                   *decoded_args,
                   **_key_val_args_to_kwargs(args.get('kwargs', [])))

    @classmethod
    def from_recipe(cls, recipe_path):
        """
        Returns a runnable from a runnable recipe file

        :param recipe_path: Path to a recipe file

        :rtype: instance of :class:`Runnable`
        """
        with open(recipe_path) as recipe_file:
            recipe = json.load(recipe_file)
        return cls(recipe.get('kind'),
                   recipe.get('uri'),
                   *recipe.get('args', ()),
                   **recipe.get('kwargs', {}))

    def get_command_args(self):
        """
        Returns the command arguments that adhere to the runner interface

        This is useful for building 'runnable-run' and 'task-run' commands
        that can be executed on a command line interface.

        :returns: the arguments that can be used on an avocado-runner command
        :rtype: list
        """
        args = ['-k', self.kind]
        if self.uri is not None:
            args.append('-u')
            args.append(self.uri)

        for arg in self.args:
            args.append('-a')
            args.append(arg)

        if self.tags is not None:
            args.append('tags=json:%s' % json.dumps(self.get_serializable_tags()))

        for key, val in self.kwargs.items():
            if not isinstance(val, str) or isinstance(val, int):
                val = "json:%s" % json.dumps(val)
            args.append('%s=%s' % (key, val))

        return args

    def get_dict(self):
        """
        Returns a dictionary representation for the current runnable

        This is usually the format that will be converted to a format
        that can be serialized to disk, such as JSON.

        :rtype: :class:`collections.OrderedDict`
        """
        recipe = collections.OrderedDict(kind=self.kind)
        if self.uri is not None:
            recipe['uri'] = self.uri
        if self.args is not None:
            recipe['args'] = self.args
        kwargs = self.kwargs.copy()
        if self.tags is not None:
            kwargs['tags'] = self.get_serializable_tags()
        if kwargs:
            recipe['kwargs'] = kwargs
        return recipe

    def get_json(self):
        """
        Returns a JSON representation

        :rtype: str
        """
        return json.dumps(self.get_dict())

    def get_serializable_tags(self):
        tags = {}
        # sets are not serializable in json
        for key, val in self.tags.items():
            if isinstance(val, set):
                val = list(val)
            tags[key] = val
        return tags

    def write_json(self, recipe_path):
        """
        Writes a file with a JSON representation (also known as a recipe)
        """
        with open(recipe_path, 'w') as recipe_file:
            recipe_file.write(self.get_json())


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

    Runnable attributes usage:

     * uri: not used

     * args: not used
    """
    def run(self):
        time_start = time.time()
        yield {'status': 'finished',
               'time_start': time_start,
               'time_end': time.time()}


class ExecRunner(BaseRunner):
    """
    Runner for standalone executables with or without arguments

    Runnable attributes usage:

     * uri: path to a binary to be executed as another process

     * args: arguments to be given on the command line to the
       binary given by path

     * kwargs: key=val to be set as environment variables to the
       process
    """
    def run(self):
        env = self.runnable.kwargs or None
        time_start = time.time()
        time_start_sent = False
        process = subprocess.Popen(
            [self.runnable.uri] + list(self.runnable.args),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env)

        last_status = None
        while process.poll() is None:
            time.sleep(RUNNER_RUN_CHECK_INTERVAL)
            now = time.time()
            if last_status is None or now > last_status + RUNNER_RUN_STATUS_INTERVAL:
                last_status = now
                if not time_start_sent:
                    time_start_sent = True
                    yield {'status': 'running',
                           'time_start': time_start}
                yield {'status': 'running'}

        stdout = process.stdout.read()
        process.stdout.close()
        stderr = process.stderr.read()
        process.stderr.close()

        yield {'status': 'finished',
               'returncode': process.returncode,
               'stdout': stdout,
               'stderr': stderr,
               'time_end': time.time()}


class ExecTestRunner(ExecRunner):
    """
    Runner for standalone executables treated as tests

    This is similar in concept to the Avocado "SIMPLE" test type, in which an
    executable returning 0 means that a test passed, and anything else means
    that a test failed.

    Runnable attributes usage is identical to :class:`ExecRunner`
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

    Runnable attributes usage:

     * uri: path to a binary to be executed as another process

     * args: not used
    """
    @staticmethod
    def _run_unittest(uri, queue):
        stream = io.StringIO()
        suite = unittest.TestLoader().loadTestsFromName(uri)
        runner = unittest.TextTestRunner(stream=stream, verbosity=0)
        unittest_result = runner.run(suite)
        time_end = time.time()

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
                  'output': stream.read(),
                  'time_end': time_end}
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
        time_start = time.time()
        time_start_sent = False
        process.start()

        last_status = None
        while queue.empty():
            time.sleep(RUNNER_RUN_CHECK_INTERVAL)
            now = time.time()
            if last_status is None or now > last_status + RUNNER_RUN_STATUS_INTERVAL:
                last_status = now
                if not time_start_sent:
                    time_start_sent = True
                    yield {'status': 'running',
                           'time_start': time_start}
                yield {'status': 'running'}

        yield queue.get()


#: The runnables this specific application is capable of handling
RUNNABLE_KIND_CAPABLE = {'noop': NoOpRunner,
                         'exec': ExecRunner,
                         'exec-test': ExecTestRunner,
                         'python-unittest': PythonUnittestRunner}


def runner_from_runnable(runnable, capables=None):
    """
    Gets a Runner instance from a Runnable
    """
    if capables is None:
        capables = RUNNABLE_KIND_CAPABLE
    runner = capables.get(runnable.kind, None)
    if runner is not None:
        return runner(runnable)
    raise ValueError('Unsupported kind of runnable: %s' % runnable.kind)


def _parse_key_val(argument):
    key_value = argument.split('=', 1)
    if len(key_value) < 2:
        msg = ('Invalid keyword parameter: "%s". Valid option must '
               'be a "KEY=VALUE" like expression' % argument)
        raise argparse.ArgumentTypeError(msg)
    return tuple(key_value)


CMD_RUNNABLE_RUN_ARGS = (
    (("-k", "--kind"),
     {'type': str, 'required': True, 'help': 'Kind of runnable'}),

    (("-u", "--uri"),
     {'type': str, 'default': None, 'help': 'URI of runnable'}),

    (("-a", "--arg"),
     {'action': "append", 'default': [], 'help': 'Simple arguments to runnable'}),

    (('kwargs',),
     {'default': [], 'type': _parse_key_val, 'nargs': '*',
      'metavar': 'KEY_VAL', 'help': 'Keyword (key=val) arguments to runnable'}),
    )


def _arg_decode_base64(arg):
    """
    Decode arguments possibly encoded as base64

    :param arg: the possibly encoded argument
    :type arg: str
    :returns: the decoded argument
    :rtype: str
    """
    prefix = 'base64:'
    if arg.startswith(prefix):
        content = arg[len(prefix):]
        return base64.decodebytes(content.encode()).decode()
    return arg


def _kwarg_decode_json(value):
    """
    Decode arguments possibly encoded as base64

    :param value: the possibly encoded argument
    :type value: str
    :returns: the decoded keyword argument as Python object
    """
    prefix = 'json:'
    if value.startswith(prefix):
        content = value[len(prefix):]
        return json.loads(content)
    return value


def _key_val_args_to_kwargs(kwargs):
    result = {}
    for key, val in kwargs:
        result[key] = _kwarg_decode_json(val)
    return result


def subcommand_runnable_run(args, echo=print):
    runnable = Runnable.from_args(args)
    runner = runner_from_runnable(runnable)

    for status in runner.run():
        echo(status)


CMD_RUNNABLE_RUN_RECIPE_ARGS = (
    (("recipe", ),
     {'type': str, 'help': 'Path to the runnable recipe file'}),
    )


def subcommand_runnable_run_recipe(args, echo=print):
    runnable = Runnable.from_recipe(args.get('recipe'))
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
        self.capables = RUNNABLE_KIND_CAPABLE

    def __repr__(self):
        fmt = '<Task identifier="{}" runnable="{}" status_services="{}"'
        return fmt.format(self.identifier, self.runnable, self.status_services)

    @classmethod
    def from_recipe(cls, task_path):
        """
        Creates a task (which contains a runnable) from a task recipe file

        :param task_path: Path to a recipe file

        :rtype: instance of :class:`Task`
        """
        with open(task_path) as recipe_file:
            recipe = json.load(recipe_file)

        identifier = recipe.get('id')
        runnable_recipe = recipe.get('runnable')
        runnable = Runnable(runnable_recipe.get('kind'),
                            runnable_recipe.get('uri'),
                            *runnable_recipe.get('args', ()))
        status_uris = recipe.get('status_uris')
        return cls(identifier, runnable, status_uris)

    def get_command_args(self):
        """
        Returns the command arguments that adhere to the runner interface

        This is useful for building 'task-run' commands that can be
        executed on a command line interface.

        :returns: the arguments that can be used on an avocado-runner command
        :rtype: list
        """
        args = ['-i', self.identifier]
        args += self.runnable.get_command_args()

        for status_service in self.status_services:
            args.append('-s')
            args.append(status_service.uri)

        return args

    def run(self):
        runner = runner_from_runnable(self.runnable, self.capables)
        for status in runner.run():
            status.update({"id": self.identifier})
            for status_service in self.status_services:
                status_service.post(status)
            yield status


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
    runnable = Runnable.from_args(args)
    task = Task(args.get('identifier'), runnable,
                args.get('status_uri', []))
    task_run(task, echo)


CMD_TASK_RUN_RECIPE_ARGS = (
    (("recipe", ),
     {'type': str, 'help': 'Path to the task recipe file'}),
    )


def subcommand_task_run_recipe(args, echo=print):
    task = Task.from_recipe(args.get('recipe'))
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


def subcommand_capabilities(_, echo=print):
    data = {"runnables": [k for k in RUNNABLE_KIND_CAPABLE.keys()],
            "commands": [k for k in COMMANDS_CAPABLE.keys()]}
    echo(json.dumps(data))


COMMANDS_CAPABLE = {'capabilities': subcommand_capabilities,
                    'runnable-run': subcommand_runnable_run,
                    'runnable-run-recipe': subcommand_runnable_run_recipe,
                    'task-run': subcommand_task_run,
                    'task-run-recipe': subcommand_task_run_recipe,
                    'status-server': subcommand_status_server}


def parse():
    parser = argparse.ArgumentParser(prog='avocado-runner',
                                     description='*EXPERIMENTAL* N(ext) Runner')
    subcommands = parser.add_subparsers(dest='subcommand')
    subcommands.required = True
    subcommands.add_parser('capabilities')
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
    kallable = COMMANDS_CAPABLE.get(subcommand)
    if kallable is not None:
        kallable(args)


if __name__ == '__main__':
    main()
