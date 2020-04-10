#!/usr/bin/env python3

import argparse
import asyncio
import base64
import collections
import enum
import inspect
import io
import json
import multiprocessing
import os
import socket
import subprocess
import sys
import time
import unittest

#: The amount of time (in seconds) between each internal status check
RUNNER_RUN_CHECK_INTERVAL = 0.01

#: The amount of time (in seconds) between a status report from a
#: runner that performs its work asynchronously
RUNNER_RUN_STATUS_INTERVAL = 0.5

#: All known runners
KNOWN_RUNNERS = {}


class SpawnMethod(enum.Enum):
    """The method employed to spawn a runnable or task."""
    #: Spawns by running executing Python code, that is, having access to
    #: a runnable or task instance, it calls its run() method.
    PYTHON_CLASS = object()
    #: Spawns by running a command, that is having either a path to an
    #: executable or a list of arguments, it calls a function that will
    #: execute that command (such as with os.system())
    STANDALONE_EXECUTABLE = object()
    #: Spawns with any method available, that is, it doesn't declare or
    #: require a specific spawn method
    ANY = object()


def check_tasks_requirements(tasks, runners_registry=None):
    """
    Checks if tasks have runner requirements fulfilled

    :param tasks: the tasks whose runner requirements will be checked
    :type tasks: list of :class:`Task`
    :param runners_registry: a registry with previously found (and not
                             found) runners keyed by task kind
    :type runners_registry: dict
    :return: two list of tasks in a tuple, with the first being the tasks
             that pass the requirements check and the second the tasks that
             fail the requirements check
    :rtype: tuple of (list, list)
    """
    if runners_registry is None:
        runners_registry = KNOWN_RUNNERS
    ok = []
    missing = []
    for task in tasks:
        runner = task.pick_runner_command(runners_registry)
        if runner:
            ok.append(task)
        else:
            missing.append(task)
    return (ok, missing)


class BaseSpawner:
    """Defines an interface to be followed by all implementations."""

    METHODS = []

    @staticmethod
    def is_task_alive(task):
        pass

    def spawn_task(self, task):
        pass


class ProcessSpawner(BaseSpawner):

    METHODS = [SpawnMethod.STANDALONE_EXECUTABLE]

    @staticmethod
    def is_task_alive(task):
        return task.spawn_handle.returncode is None

    @asyncio.coroutine
    def spawn_task(self, task):
        runner = task.pick_runner_command()
        args = runner[1:] + ['task-run'] + task.get_command_args()
        runner = runner[0]

        #pylint: disable=E1133
        task.spawn_handle = yield from asyncio.create_subprocess_exec(
            runner,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)


class PodmanSpawner(BaseSpawner):

    METHODS = [SpawnMethod.STANDALONE_EXECUTABLE]
    IMAGE = 'fedora:31'
    PODMAN_BIN = "/usr/bin/podman"

    @staticmethod
    def is_task_alive(task):
        if task.spawn_handle is None:
            return False

        cmd = [PodmanSpawner.PODMAN_BIN, "ps", "--all", "--format={{.State}}",
               "--filter=id=%s" % task.spawn_handle]
        process = subprocess.Popen(cmd,
                                   stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL)
        out, _ = process.communicate()
        # we have to be lenient and allow for the configured state to
        # be considered "alive" because it happens before the
        # container transitions into "running"
        return out in [b'configured\n', b'running\n']

    @asyncio.coroutine
    def spawn_task(self, task):
        entry_point_cmd = '/tmp/avocado-runner'
        entry_point_args = task.get_command_args()
        entry_point_args.insert(0, "task-run")
        entry_point_args.insert(0, entry_point_cmd)
        entry_point = json.dumps(entry_point_args)
        entry_point_arg = "--entrypoint=" + entry_point
        # pylint: disable=E1133
        proc = yield from asyncio.create_subprocess_exec(
            self.PODMAN_BIN, "create",
            "--net=host",
            entry_point_arg,
            self.IMAGE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)

        _ = yield from proc.wait()
        stdout = yield from proc.stdout.read()
        container_id = stdout.decode().strip()

        task.spawn_handle = container_id

        # Currently limited to avocado-runner, we'll expand on that
        # when the runner requirements system is in place
        this_path = os.path.abspath(__file__)
        common_path = os.path.dirname(os.path.dirname(this_path))
        avocado_runner_path = os.path.join(common_path, 'core', 'nrunner.py')
        proc = yield from asyncio.create_subprocess_exec(
            self.PODMAN_BIN,
            "cp",
            avocado_runner_path,
            "%s:%s" % (container_id, entry_point_cmd))
        yield from proc.wait()

        proc = yield from asyncio.create_subprocess_exec(self.PODMAN_BIN,
                                                         "start",
                                                         container_id,
                                                         stdout=asyncio.subprocess.PIPE,
                                                         stderr=asyncio.subprocess.PIPE)
        yield from proc.wait()


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
            if arg.startswith('-'):
                arg = 'base64:%s' % base64.b64encode(arg.encode()).decode('ascii')
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
               'result': 'pass',
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

        most_current_execution_state_time = None
        while process.poll() is None:
            time.sleep(RUNNER_RUN_CHECK_INTERVAL)
            now = time.time()
            if most_current_execution_state_time is not None:
                next_execution_state_mark = (most_current_execution_state_time +
                                             RUNNER_RUN_STATUS_INTERVAL)
            if (most_current_execution_state_time is None or
                    now > next_execution_state_mark):
                most_current_execution_state_time = now
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
        for most_current_execution_state in super(ExecTestRunner, self).run():
            if 'returncode' in most_current_execution_state:
                if most_current_execution_state['returncode'] == 0:
                    most_current_execution_state['result'] = 'pass'
                else:
                    most_current_execution_state['result'] = 'fail'
            yield most_current_execution_state


class PythonUnittestRunner(BaseRunner):
    """
    Runner for Python unittests

    The runnable uri is used as the test name that the native unittest
    TestLoader will use to find the test.  A native unittest test
    runner (TextTestRunner) will be used to execute the test.

    Runnable attributes usage:

     * uri: a "dotted name" that can be given to Python standard
            library's :meth:`unittest.TestLoader.loadTestsFromName`
            method. While it's not enforced, it's highly recommended
            that this is "a test method within a test case class" within
            a test module.  Example is: "module.Class.test_method".

     * args: not used

     * kwargs: not used
    """
    @staticmethod
    def _run_unittest(uri, queue):
        stream = io.StringIO()
        suite = unittest.TestLoader().loadTestsFromName(uri)
        runner = unittest.TextTestRunner(stream=stream, verbosity=0)
        unittest_result = runner.run(suite)
        time_end = time.time()

        if len(unittest_result.errors) > 0:
            result = 'error'
        elif len(unittest_result.failures) > 0:
            result = 'fail'
        elif len(unittest_result.skipped) > 0:
            result = 'skip'
        else:
            result = 'pass'

        stream.seek(0)
        output = {'status': 'finished',
                  'result': result,
                  'output': stream.read(),
                  'time_end': time_end}
        stream.close()
        queue.put(output)

    def run(self):
        if not self.runnable.uri:
            yield {'status': 'finished',
                   'result': 'error',
                   'output': 'uri is required but was not given'}
            return

        queue = multiprocessing.SimpleQueue()
        process = multiprocessing.Process(target=self._run_unittest,
                                          args=(self.runnable.uri, queue))
        time_start = time.time()
        time_start_sent = False
        process.start()

        most_current_execution_state_time = None
        while queue.empty():
            time.sleep(RUNNER_RUN_CHECK_INTERVAL)
            now = time.time()
            if most_current_execution_state_time is not None:
                next_execution_state_mark = (most_current_execution_state_time +
                                             RUNNER_RUN_STATUS_INTERVAL)
            if (most_current_execution_state_time is None or
                    now > next_execution_state_mark):
                most_current_execution_state_time = now
                if not time_start_sent:
                    time_start_sent = True
                    yield {'status': 'running',
                           'time_start': time_start}
                yield {'status': 'running'}

        yield queue.get()


def runner_from_runnable(runnable, known_runners):
    """
    Gets a Runner instance from a Runnable
    """
    runner = known_runners.get(runnable.kind, None)
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
    def __init__(self, identifier, runnable, status_uris=None, known_runners=None):
        self.identifier = identifier
        self.runnable = runnable
        self.status_services = []
        if status_uris is not None:
            for status_uri in status_uris:
                self.status_services.append(TaskStatusService(status_uri))
        if known_runners is None:
            known_runners = {}
        self.known_runners = known_runners
        self.spawn_handle = None

    def __repr__(self):
        fmt = '<Task identifier="{}" runnable="{}" status_services="{}"'
        return fmt.format(self.identifier, self.runnable, self.status_services)

    def are_requirements_available(self, runners_registry=None):
        """Verifies if requirements needed to run this task are available.

        This currently checks the runner command only, but can be expanded once
        the handling of other types of requirements are implemented.  See
        :doc:`/blueprints/BP002`.
        """
        if runners_registry is None:
            runners_registry = KNOWN_RUNNERS
        return self.pick_runner_command(runners_registry)

    @classmethod
    def from_recipe(cls, task_path, known_runners):
        """
        Creates a task (which contains a runnable) from a task recipe file

        :param task_path: Path to a recipe file
        :param known_runners: Dictionary with runner names and implementations

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
        return cls(identifier, runnable, status_uris, known_runners)

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

    def is_kind_supported_by_runner_command(self, runner_command):
        """Checks if a runner command that seems a good fit declares support."""
        cmd = runner_command + ['capabilities']
        try:
            process = subprocess.Popen(cmd,
                                       stdin=subprocess.DEVNULL,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            return False
        out, _ = process.communicate()

        try:
            capabilities = json.loads(out.decode())
        except json.decoder.JSONDecodeError:
            return False

        return self.runnable.kind in capabilities.get('runnables', [])

    def pick_runner_command(self, runners_registry=None):
        """Selects a runner command based on the task.

        And when finding a suitable runner, keeps found runners in registry.

        This utility function will look at the given task and try to find
        a matching runner.  The matching runner probe results are kept in
        a registry (that is modified by this function) so that further
        executions take advantage of previous probes.

        This is related to the :data:`SpawnMethod.STANDALONE_EXECUTABLE`

        :param runners_registry: a registry with previously found (and not
                                 found) runners keyed by task kind
        :param runners_registry: dict
        :returns: command line arguments to execute the runner
        :rtype: list of str or None
        """
        if runners_registry is None:
            runners_registry = KNOWN_RUNNERS
        kind = self.runnable.kind
        runner_cmd = runners_registry.get(kind)
        if runner_cmd is False:
            return None
        if runner_cmd is not None:
            return runner_cmd

        standalone_executable_cmd = ['avocado-runner-%s' % kind]
        if self.is_kind_supported_by_runner_command(standalone_executable_cmd):
            runners_registry[kind] = standalone_executable_cmd
            return standalone_executable_cmd

        # attempt to find Python module files that are named after the
        # runner convention within the avocado.core namespace dir.
        # Looking for the file only avoids an attempt to load the module
        # and should be a lot faster
        core_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        module_name = kind.replace('-', '_')
        module_filename = 'nrunner_%s.py' % module_name
        if os.path.exists(os.path.join(core_dir, module_filename)):
            full_module_name = 'avocado.core.%s' % module_name
            candidate_cmd = [sys.executable, '-m', full_module_name]
            if self.is_kind_supported_by_runner_command(candidate_cmd):
                runners_registry[kind] = candidate_cmd
                return candidate_cmd

        # exhausted probes, let's save the negative on the cache and avoid
        # future similar problems
        runners_registry[kind] = False

    def run(self):
        runner = runner_from_runnable(self.runnable, self.known_runners)
        for status in runner.run():
            status.update({"id": self.identifier})
            for status_service in self.status_services:
                status_service.post(status)
            yield status


class StatusServer:

    def __init__(self, uri, tasks_pending=None):
        self.uri = uri
        self.server_task = None
        self.result = {}
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
                    print('Task complete (%s): %s' % (data['result'],
                                                      data['id']))
                except IndexError:
                    pass
                except ValueError:
                    pass
                if data['result'] in self.result:
                    self.result[data['result']] += 1
                else:
                    self.result[data['result']] = 1

                if data['result'] not in ('pass', 'skip'):
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


class BaseRunnerApp:
    '''
    Helper base class for common runner application behavior
    '''

    #: The name of the command line application given to the command line
    #: parser
    PROG_NAME = ''

    #: The description of the command line application given to the
    #: command line parser
    PROG_DESCRIPTION = ''

    #: The types of runnables that this runner can handle.  Dictionary key
    #: is a name, and value is a class that inherits from :class:`BaseRunner`
    RUNNABLE_KINDS_CAPABLE = {}

    #: The command line arguments to the "runnable-run" command
    CMD_RUNNABLE_RUN_ARGS = (
        (("-k", "--kind"),
         {'type': str, 'required': True, 'help': 'Kind of runnable'}),

        (("-u", "--uri"),
         {'type': str, 'default': None, 'help': 'URI of runnable'}),

        (("-a", "--arg"),
         {'action': "append", 'default': [],
          'help': 'Simple arguments to runnable'}),

        (('kwargs',),
         {'default': [], 'type': _parse_key_val, 'nargs': '*',
          'metavar': 'KEY_VAL',
          'help': 'Keyword (key=val) arguments to runnable'}),
    )

    CMD_RUNNABLE_RUN_RECIPE_ARGS = (
        (("recipe", ),
         {'type': str, 'help': 'Path to the runnable recipe file'}),
    )

    CMD_TASK_RUN_ARGS = (
        (("-i", "--identifier"),
         {'type': str, 'required': True, 'help': 'Task unique identifier'}),
        (("-s", "--status-uri"),
         {'action': "append", 'default': None,
          'help': 'URIs of status services to report to'}),
    )
    CMD_TASK_RUN_ARGS += CMD_RUNNABLE_RUN_ARGS

    CMD_TASK_RUN_RECIPE_ARGS = (
        (("recipe", ),
         {'type': str, 'help': 'Path to the task recipe file'}),
    )

    CMD_STATUS_SERVER_ARGS = (
        (("uri", ),
         {'type': str, 'help': 'URI to bind a status server to'}),
    )

    def __init__(self, echo=print, prog=None, description=None):
        self.echo = echo
        self.parser = None
        if prog is None:
            prog = self.PROG_NAME
        if description is None:
            description = self.PROG_DESCRIPTION
        self._setup_parser(prog, description)

    def _setup_parser(self, prog, description):
        self.parser = argparse.ArgumentParser(prog=prog,
                                              description=description)
        subcommands = self.parser.add_subparsers(dest='subcommand')
        subcommands.required = True
        for cmd_meth in self._get_commands_method_without_prefix():
            attr = "CMD_%s_ARGS" % cmd_meth.upper()
            cmd = cmd_meth.replace('_', '-')
            cmd_parser = subcommands.add_parser(
                cmd,
                help=self._get_command_method_help_message(cmd_meth))
            if hasattr(self, attr):
                for arg in getattr(self, attr):
                    cmd_parser.add_argument(*arg[0], **arg[1])

    def _get_commands_method_without_prefix(self):
        prefix = 'command_'
        return [c[0][len(prefix):]
                for c in inspect.getmembers(self, inspect.ismethod)
                if c[0].startswith(prefix)]

    def _get_command_method_help_message(self, command_method):
        help_message = ''
        docstring = getattr(self, 'command_%s' % command_method).__doc__
        if docstring:
            docstring_lines = docstring.strip().splitlines()
            if docstring_lines:
                help_message = docstring_lines[0]
        return help_message

    def run(self):
        """
        Runs the application by finding a suitable command method to call
        """
        args = vars(self.parser.parse_args())
        subcommand = args.get('subcommand')
        if subcommand in self.get_commands():
            meth_name = 'command_' + subcommand.replace('-', '_')
            if hasattr(self, meth_name):
                kallable = getattr(self, meth_name)
                return kallable(args)

    def get_commands(self):
        """
        Return the command names, as seen on the command line application

        For every method whose name starts with "command_", a the name of
        the command follows, with underscores replaced by dashes.  So, a
        method named "command_foo_bar", will be a command available on the
        command line as "foo-bar".

        :rtype: list
        """
        return [c.replace('_', '-') for c in
                self._get_commands_method_without_prefix()]

    def get_capabilities(self):
        """
        Returns the runner capabilities, including runnables and commands

        This can be used by higher level tools, such as the entity spawning
        runners, to know which runner can be used to handle each runnable
        type.

        :rtype: dict
        """
        return {"runnables": [k for k in self.RUNNABLE_KINDS_CAPABLE.keys()],
                "commands": self.get_commands()}

    def get_runner_from_runnable(self, runnable):
        """
        Returns a runner that is suitable to run the given runnable

        :rtype: instance of class inheriting from :class:`BaseRunner`
        :raises: ValueError if runnable is now supported
        """
        runner = self.RUNNABLE_KINDS_CAPABLE.get(runnable.kind, None)
        if runner is not None:
            return runner(runnable)
        raise ValueError('Unsupported kind of runnable: %s' % runnable.kind)

    def command_capabilities(self, _):
        """
        Outputs capabilities, including runnables and commands

        The output is intended to be consumed by upper layers of Avocado, such
        as the Job layer selecting the right runner script to handle a runnable
        of a given kind, or identifying if a runner script has a given feature
        (as implemented by a command).
        """
        self.echo(json.dumps(self.get_capabilities()))

    def command_runnable_run(self, args):
        """
        Runs a runnable definition from arguments

        This defines a Runnable instance purely from the command line
        arguments, then selects a suitable Runner, and runs it.

        :param args: parsed command line arguments turned into a dictionary
        :type args: dict
        """
        runnable = Runnable.from_args(args)
        runner = self.get_runner_from_runnable(runnable)
        for status in runner.run():
            self.echo(status)

    def command_runnable_run_recipe(self, args):
        """
        Runs a runnable definition from a recipe

        :param args: parsed command line arguments turned into a dictionary
        :type args: dict
        """
        runnable = Runnable.from_recipe(args.get('recipe'))
        runner = self.get_runner_from_runnable(runnable)
        for status in runner.run():
            self.echo(status)

    def command_task_run(self, args):
        """
        Runs a task from arguments

        :param args: parsed command line arguments turned into a dictionary
        :type args: dict
        """
        runnable = Runnable.from_args(args)
        task = Task(args.get('identifier'), runnable,
                    args.get('status_uri', []),
                    known_runners=self.RUNNABLE_KINDS_CAPABLE)
        for status in task.run():
            self.echo(status)

    def command_task_run_recipe(self, args):
        """
        Runs a task from a recipe

        :param args: parsed command line arguments turned into a dictionary
        :type args: dict
        """
        task = Task.from_recipe(args.get('recipe'),
                                self.RUNNABLE_KINDS_CAPABLE)
        for status in task.run():
            self.echo(status)

    def command_status_server(self, args):
        """
        Runs a status server

        :param args: parsed command line arguments turned into a dictionary
        :type args: dict
        """
        server = StatusServer(args.get('uri'))
        server.start()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(server.wait())


class RunnerApp(BaseRunnerApp):
    PROG_NAME = 'avocado-runner'
    PROG_DESCRIPTION = '*EXPERIMENTAL* N(ext) Runner'
    RUNNABLE_KINDS_CAPABLE = {
        'noop': NoOpRunner,
        'exec': ExecRunner,
        'exec-test': ExecTestRunner,
        'python-unittest': PythonUnittestRunner
    }


def main(app_class=RunnerApp):
    app = app_class(print)
    app.run()


if __name__ == '__main__':
    main()
