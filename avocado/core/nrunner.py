#!/usr/bin/env python3

import abc
import argparse
import base64
import collections
import inspect
import io
import json
import multiprocessing
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from uuid import uuid1

try:
    import pkg_resources
    PKG_RESOURCES_AVAILABLE = True
except ImportError:
    PKG_RESOURCES_AVAILABLE = False


#: The amount of time (in seconds) between each internal status check
RUNNER_RUN_CHECK_INTERVAL = 0.01

#: The amount of time (in seconds) between a status report from a
#: runner that performs its work asynchronously
RUNNER_RUN_STATUS_INTERVAL = 0.5

#: All known runner commands, capable of being used by a
#: SpawnMethod.STANDALONE_EXECUTABLE compatible spawners
RUNNERS_REGISTRY_STANDALONE_EXECUTABLE = {}

#: All known runner Python classes.  This is a dictionary keyed by a
#: runnable kind, and value is a class that inherits from
#: :class:`BaseRunner`.  Suitable for spawners compatible with
#: SpawnMethod.PYTHON_CLASS
RUNNERS_REGISTRY_PYTHON_CLASS = {}


def check_runnables_runner_requirements(runnables, runners_registry=None):
    """
    Checks if runnables have runner requirements fulfilled

    :param runnables: the tasks whose runner requirements will be checked
    :type runnable: list of :class:`Runnable`
    :param runners_registry: a registry with previously found (and not found)
                             runners keyed by a task's runnable kind. Defaults
                             to :attr:`RUNNERS_REGISTRY_STANDALONE_EXECUTABLE`
    :type runners_registry: dict
    :return: two list of tasks in a tuple, with the first being the tasks
             that pass the requirements check and the second the tasks that
             fail the requirements check
    :rtype: tuple of (list, list)
    """
    if runners_registry is None:
        runners_registry = RUNNERS_REGISTRY_STANDALONE_EXECUTABLE
    ok = []
    missing = []

    for runnable in runnables:
        runner = runnable.pick_runner_command(runners_registry)
        if runner:
            ok.append(runnable)
        else:
            missing.append(runnable)
    return (ok, missing)


class Runnable:
    """
    Describes an entity that be executed in the context of a task

    A instance of :class:`BaseRunner` is the entity that will actually
    execute a runnable.
    """

    def __init__(self, kind, uri, *args, config=None, **kwargs):
        self.kind = kind
        self.uri = uri
        self.config = config or {}
        self.args = args
        self.tags = kwargs.pop('tags', None)
        self.requirements = kwargs.pop('requirements', None)
        self.kwargs = kwargs

    def __repr__(self):
        fmt = ('<Runnable kind="{}" uri="{}" config="{}" args="{}" '
               'kwargs="{}" tags="{}" requirements="{}">')
        return fmt.format(self.kind, self.uri, self.config, self.args,
                          self.kwargs, self.tags, self.requirements)

    @classmethod
    def from_args(cls, args):
        """Returns a runnable from arguments"""
        decoded_args = [_arg_decode_base64(arg) for arg in args.get('arg', ())]
        return cls(args.get('kind'),
                   args.get('uri'),
                   *decoded_args,
                   config=json.loads(args.get('config', '{}')),
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
                   config=recipe.get('config', {}),
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

        if self.config is not None:
            args.append('-c')
            args.append(json.dumps(self.config))

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
        recipe['config'] = self.config
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

    def is_kind_supported_by_runner_command(self, runner_command):
        """Checks if a runner command that seems a good fit declares support."""
        cmd = runner_command + ['capabilities']
        try:
            process = subprocess.Popen(cmd,
                                       stdin=subprocess.DEVNULL,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.DEVNULL)
        except (FileNotFoundError, PermissionError):
            return False
        out, _ = process.communicate()

        try:
            capabilities = json.loads(out.decode())
        except json.decoder.JSONDecodeError:
            return False

        return self.kind in capabilities.get('runnables', [])

    def pick_runner_command(self, runners_registry=None):
        """Selects a runner command based on the runner.

        And when finding a suitable runner, keeps found runners in registry.

        This utility function will look at the given task and try to find
        a matching runner.  The matching runner probe results are kept in
        a registry (that is modified by this function) so that further
        executions take advantage of previous probes.

        This is related to the :data:`SpawnMethod.STANDALONE_EXECUTABLE`

        :param runners_registry: a registry with previously found (and not
                                 found) runners keyed by runnable kind
        :param runners_registry: dict
        :returns: command line arguments to execute the runner
        :rtype: list of str or None
        """
        if runners_registry is None:
            runners_registry = RUNNERS_REGISTRY_STANDALONE_EXECUTABLE
        runner_cmd = runners_registry.get(self.kind)
        if runner_cmd is False:
            return None
        if runner_cmd is not None:
            return runner_cmd

        standalone_executable_cmd = ['avocado-runner-%s' % self.kind]
        if self.is_kind_supported_by_runner_command(standalone_executable_cmd):
            runners_registry[self.kind] = standalone_executable_cmd
            return standalone_executable_cmd

        # attempt to find Python module files that are named after the
        # runner convention within the avocado.core namespace dir.
        # Looking for the file only avoids an attempt to load the module
        # and should be a lot faster
        core_dir = os.path.dirname(os.path.abspath(__file__))
        module_name = self.kind.replace('-', '_')
        module_filename = '%s.py' % module_name
        if os.path.exists(os.path.join(core_dir, 'runners', module_filename)):
            full_module_name = 'avocado.core.runners.%s' % module_name
            candidate_cmd = [sys.executable, '-m', full_module_name]
            if self.is_kind_supported_by_runner_command(candidate_cmd):
                runners_registry[self.kind] = candidate_cmd
                return candidate_cmd

        # exhausted probes, let's save the negative on the cache and avoid
        # future similar problems
        runners_registry[self.kind] = False

    def pick_runner_class_from_entry_point(self):
        """Selects a runner class from entry points based on kind.

        This is related to the :data:`SpawnMethod.PYTHON_CLASS`. This
        complements the :data:`RUNNERS_REGISTRY_PYTHON_CLASS` on systems
        that have setuptools available.

        :returns: a class that inherits from :class:`BaseRunner` or None
        """
        if not PKG_RESOURCES_AVAILABLE:
            return
        namespace = 'avocado.plugins.runnable.runner'
        for ep in pkg_resources.iter_entry_points(namespace):
            if ep.name == self.kind:
                try:
                    obj = ep.load()
                    return obj
                except ImportError:
                    return

    def pick_runner_class(self, runners_registry=None):
        """Selects a runner class from the registry based on kind.

        This is related to the :data:`SpawnMethod.PYTHON_CLASS`

        :param runners_registry: a registry with previously registered
                                 runner classes, keyed by runnable kind
        :param runners_registry: dict
        :returns: a class that inherits from :class:`BaseRunner`
        :raises: ValueError if kind there's no runner from kind of runnable
        """
        if runners_registry is None:
            runners_registry = RUNNERS_REGISTRY_PYTHON_CLASS

        runner = runners_registry.get(self.kind, None)
        if runner is None:
            runner = self.pick_runner_class_from_entry_point()
        if runner is not None:
            return runner
        raise ValueError('Unsupported kind of runnable: %s' % self.kind)


class BaseRunner(abc.ABC):
    """
    Base interface for a Runner
    """

    def __init__(self, runnable):
        self.runnable = runnable

    @staticmethod
    def prepare_status(status_type, additional_info=None):
        """Prepare a status dict with some basic information.

        This will add the keyword 'status' and 'time' to all status.

        :param: status_type: The type of event ('started', 'running',
                             'finished')
        :param: addional_info: Any additional information that you
                               would like to add to the dict. This must be a
                               dict.

        :rtype: dict
        """
        status = {}
        if isinstance(additional_info, dict):
            status = additional_info
        status.update({'status': status_type,
                       'time': time.monotonic()})
        return status

    @abc.abstractmethod
    def run(self):
        """Runner main method

        Yields dictionary as output, containing status as well as relevant
        information concerning the results.
        """


class NoOpRunner(BaseRunner):
    """
    Sample runner that performs no action before reporting FINISHED status

    Runnable attributes usage:

     * uri: not used

     * args: not used
    """

    def run(self):
        yield self.prepare_status('started')
        yield self.prepare_status('finished', {'result': 'pass'})


RUNNERS_REGISTRY_PYTHON_CLASS['noop'] = NoOpRunner


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

    def _process_final_status(self, process,
                              stdout=None, stderr=None):  # pylint: disable=W0613
        return self.prepare_status('finished',
                                   {'returncode': process.returncode})

    def run(self):
        env = None
        if self.runnable.kwargs:
            current = dict(os.environ)
            current.update(self.runnable.kwargs)
            env = current

        if env and 'PATH' not in env:
            env['PATH'] = os.environ.get('PATH')
        process = subprocess.Popen(
            [self.runnable.uri] + list(self.runnable.args),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env)

        yield self.prepare_status('started')
        most_current_execution_state_time = None
        timeout = RUNNER_RUN_CHECK_INTERVAL
        while process.returncode is None:
            time.sleep(timeout)
            try:
                stdout, stderr = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                # Let's just try again at the next loop
                pass
            now = time.monotonic()
            if most_current_execution_state_time is not None:
                next_execution_state_mark = (most_current_execution_state_time +
                                             RUNNER_RUN_STATUS_INTERVAL)
            if (most_current_execution_state_time is None or
                    now > next_execution_state_mark):
                most_current_execution_state_time = now
                yield self.prepare_status('running')
        yield self.prepare_status('running', {'type': 'stdout', 'log': stdout})
        yield self.prepare_status('running', {'type': 'stderr', 'log': stderr})
        yield self._process_final_status(process, stdout, stderr)


RUNNERS_REGISTRY_PYTHON_CLASS['exec'] = ExecRunner


class ExecTestRunner(ExecRunner):
    """
    Runner for standalone executables treated as tests

    This is similar in concept to the Avocado "SIMPLE" test type, in which an
    executable returning 0 means that a test passed, and anything else means
    that a test failed.

    Runnable attributes usage is identical to :class:`ExecRunner`
    """

    def _process_final_status(self, process,
                              stdout=None, stderr=None):  # pylint: disable=W0613
        # Since Runners are standalone, and could be executed on a remote
        # machine in an "isolated" way, there is no way to assume a default
        # value, at this moment.
        skip_codes = self.runnable.config.get('runner.exectest.exitcodes.skip',
                                              [])
        final_status = {}
        if process.returncode in skip_codes:
            final_status['result'] = 'skip'
        elif process.returncode == 0:
            final_status['result'] = 'pass'
        else:
            final_status['result'] = 'fail'

        final_status['returncode'] = process.returncode
        return self.prepare_status('finished', final_status)


RUNNERS_REGISTRY_PYTHON_CLASS['exec-test'] = ExecTestRunner


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
    def _uri_to_unittest_name(uri):
        if ':' in uri:
            module, class_method = uri.rsplit(':', 1)
        else:
            module = uri
            class_method = None
        if module.endswith('.py'):
            module = module[:-3]
        if module.startswith(os.path.curdir):
            module = module[1:]
            if module.startswith(os.path.sep):
                module = module[1:]
        module = module.replace(os.path.sep, ".")
        if class_method:
            return '%s.%s' % (module, class_method)
        return module

    @staticmethod
    def _run_unittest(uri, queue):
        sys.path.insert(0, ".")
        stream = io.StringIO()
        unittest_name = PythonUnittestRunner._uri_to_unittest_name(uri)
        suite = unittest.TestLoader().loadTestsFromName(unittest_name)
        runner = unittest.TextTestRunner(stream=stream, verbosity=0)
        unittest_result = runner.run(suite)

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
                  'output': stream.read()}
        stream.close()
        queue.put(output)

    def run(self):
        if not self.runnable.uri:
            error_msg = 'uri is required but was not given'
            yield self.prepare_status('finished', {'result': 'error',
                                                   'output': error_msg})
            return

        queue = multiprocessing.SimpleQueue()
        process = multiprocessing.Process(target=self._run_unittest,
                                          args=(self.runnable.uri, queue))
        process.start()
        yield self.prepare_status('started')

        most_current_execution_state_time = None
        while queue.empty():
            time.sleep(RUNNER_RUN_CHECK_INTERVAL)
            now = time.monotonic()
            if most_current_execution_state_time is not None:
                next_execution_state_mark = (most_current_execution_state_time +
                                             RUNNER_RUN_STATUS_INTERVAL)
            if (most_current_execution_state_time is None or
                    now > next_execution_state_mark):
                most_current_execution_state_time = now
                yield self.prepare_status('running')

        status = queue.get()
        yield self.prepare_status('running',
                                  {'type': 'stdout',
                                   'log': status.pop('output').encode()})
        status['time'] = time.monotonic()
        yield status


RUNNERS_REGISTRY_PYTHON_CLASS['python-unittest'] = PythonUnittestRunner


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


def json_dumps(data):
    return json.dumps(data, ensure_ascii=True, cls=StatusEncoder)


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
    """

    def __init__(self, runnable, identifier=None, status_uris=None,
                 known_runners=None, category='test'):
        """Instantiates a new Task.

        :param runnable: the "description" of what the task should run.
        :type runnable: :class:`avocado.core.nrunner.Runnable`
        :param identifier: any identifier that is guaranteed to be unique
                           within the context of a Job. A recommended value
                           is a :class:`avocado.core.test_id.TestID` instance
                           when a task represents a test, because besides the
                           uniqueness aspect, it's also descriptive.  If an
                           identifier is not given, an automatically generated
                           one will be set.
        :param status_uri: the URIs for the status servers that this task
                           should send updates to.
        :type status_uri: list
        :param known_runners: a mapping of runnable kinds to runners.
        :type known_runners: dict
        :param category: category of this task. Defaults to 'test'.
        :type category: str
        """
        self.runnable = runnable
        self.identifier = identifier or str(uuid1())
        #: Category of the task.  If the category is not "test", it
        #: will not be accounted for on a Job's test results.
        self.category = category
        self.status_services = []
        if status_uris is not None:
            for status_uri in status_uris:
                self.status_services.append(TaskStatusService(status_uri))
        if known_runners is None:
            known_runners = {}
        self.known_runners = known_runners
        self.dependencies = set()
        self.spawn_handle = None
        self.output_dir = None
        self.metadata = {}

    def __repr__(self):
        fmt = ('<Task identifier="{}" runnable="{}" dependencies="{}"'
               ' status_services="{}"')
        return fmt.format(self.identifier, self.runnable, self.dependencies,
                          self.status_services)

    def are_requirements_available(self, runners_registry=None):
        """Verifies if requirements needed to run this task are available.

        This currently checks the runner command only, but can be expanded once
        the handling of other types of requirements are implemented.  See
        :doc:`/blueprints/BP002`.
        """
        if runners_registry is None:
            runners_registry = RUNNERS_REGISTRY_STANDALONE_EXECUTABLE
        return self.runnable.pick_runner_command(runners_registry)

    def setup_output_dir(self):
        self.output_dir = tempfile.mkdtemp(prefix='.avocado-task-')
        env_var = {'AVOCADO_TEST_OUTPUT_DIR': self.output_dir}
        self.runnable.kwargs.update(env_var)

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
                            *runnable_recipe.get('args', ()),
                            config=runnable_recipe.get('config'))
        status_uris = recipe.get('status_uris')
        return cls(runnable, identifier, status_uris, known_runners)

    def get_command_args(self):
        """
        Returns the command arguments that adhere to the runner interface

        This is useful for building 'task-run' commands that can be
        executed on a command line interface.

        :returns: the arguments that can be used on an avocado-runner command
        :rtype: list
        """
        args = ['-i', str(self.identifier)]
        args += self.runnable.get_command_args()

        for status_service in self.status_services:
            args.append('-s')
            args.append(status_service.uri)

        return args

    def run(self):
        self.setup_output_dir()
        runner_klass = self.runnable.pick_runner_class(self.known_runners)
        runner = runner_klass(self.runnable)
        for status in runner.run():
            if status['status'] == 'started':
                status.update({'output_dir': self.output_dir})
            status.update({"id": self.identifier})
            for status_service in self.status_services:
                status_service.post(status)
            yield status


def _get_kind_options_from_executable_name():
    executable_name = os.path.basename(sys.argv[0])
    match = re.match(r'^avocado\-runner\-(.+)$', executable_name)
    options = {'type': str, 'help': 'Kind of runnable'}
    if match:
        options['required'] = False
        options['default'] = match.group(1)
        options['help'] += ', defaults to "%(default)s"'
    else:
        options['required'] = True
    return options


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
        (('-k', '--kind'),
         _get_kind_options_from_executable_name()),

        (('-u', '--uri'),
         {'type': str, 'default': None, 'help': 'URI of runnable'}),

        (('-c', '--config'),
         {'type': str, 'default': '{}', 'help': 'A config JSON data'}),

        (('-a', '--arg'),
         {'action': 'append', 'default': [],
          'help': 'Simple arguments to runnable'}),

        (('kwargs',),
         {'default': [], 'type': _parse_key_val, 'nargs': '*',
          'metavar': 'KEY_VAL',
          'help': 'Keyword (key=val) arguments to runnable'}),
    )

    CMD_RUNNABLE_RUN_RECIPE_ARGS = (
        (('recipe', ),
         {'type': str, 'help': 'Path to the runnable recipe file'}),
    )

    CMD_TASK_RUN_ARGS = (
        (('-i', '--identifier'),
         {'type': str, 'required': True, 'help': 'Task unique identifier'}),
        (('-s', '--status-uri'),
         {'action': 'append', 'default': None,
          'help': 'URIs of status services to report to'}),
    )
    CMD_TASK_RUN_ARGS += CMD_RUNNABLE_RUN_ARGS

    CMD_TASK_RUN_RECIPE_ARGS = (
        (('recipe', ),
         {'type': str, 'help': 'Path to the task recipe file'}),
    )

    CMD_STATUS_SERVER_ARGS = (
        (('uri', ),
         {'type': str, 'help': 'URI to bind a status server to'}),
    )

    def __init__(self, echo=print, prog=None, description=None):
        self.echo = echo
        self.parser = None
        if prog is None:
            prog = self.PROG_NAME
        if description is None:
            description = self.PROG_DESCRIPTION
        self._class_commands_method = self._get_commands_method()
        self._setup_parser(prog, description)

    def _setup_parser(self, prog, description):
        self.parser = argparse.ArgumentParser(prog=prog,
                                              description=description)
        subcommands = self.parser.add_subparsers(dest='subcommand')
        subcommands.required = True
        for command, method in self._class_commands_method.items():
            command_args = "CMD_%s_ARGS" % command.upper().replace('-', '_')
            command_parser = subcommands.add_parser(
                command,
                help=self._get_command_method_help_message(method))
            if hasattr(self, command_args):
                for arg in getattr(self, command_args):
                    command_parser.add_argument(*arg[0], **arg[1])

    def _get_commands_method(self):
        prefix = 'command_'
        return {c[0][len(prefix):].replace('_', '-'): getattr(self, c[0])
                for c in inspect.getmembers(self, inspect.ismethod)
                if c[0].startswith(prefix)}

    @staticmethod
    def _get_command_method_help_message(command_method):
        help_message = ''
        docstring = command_method.__doc__
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
        kallable = self._class_commands_method.get(subcommand, None)
        if kallable is not None:
            return kallable(args)

    def get_commands(self):
        """
        Return the command names, as seen on the command line application

        For every method whose name starts with "command", and the name of
        the command follows, with underscores replaced by dashes.  So, a
        method named "command_foo_bar", will be a command available on the
        command line as "foo-bar".

        :rtype: list
        """
        return list(self._class_commands_method.keys())

    def get_capabilities(self):
        """
        Returns the runner capabilities, including runnables and commands

        This can be used by higher level tools, such as the entity spawning
        runners, to know which runner can be used to handle each runnable
        type.

        :rtype: dict
        """
        return {"runnables": list(self.RUNNABLE_KINDS_CAPABLE.keys()),
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
        task = Task(runnable, args.get('identifier'),
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


class RunnerApp(BaseRunnerApp):
    PROG_NAME = 'avocado-runner'
    PROG_DESCRIPTION = 'nrunner base application'
    RUNNABLE_KINDS_CAPABLE = RUNNERS_REGISTRY_PYTHON_CLASS


def main(app_class=RunnerApp):
    app = app_class(print)
    app.run()


if __name__ == '__main__':
    main()
