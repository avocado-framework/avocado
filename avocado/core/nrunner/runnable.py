import base64
import collections
import json
import os
import subprocess
import sys

import pkg_resources

from avocado.core.nrunner.config import ConfigDecoder, ConfigEncoder

#: All known runner commands, capable of being used by a
#: SpawnMethod.STANDALONE_EXECUTABLE compatible spawners
RUNNERS_REGISTRY_STANDALONE_EXECUTABLE = {}

#: The configuration that is known to be used by standalone runners
STANDALONE_EXECUTABLE_CONFIG_USED = {}


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


class Runnable:
    """
    Describes an entity that be executed in the context of a task

    A instance of :class:`BaseRunner` is the entity that will actually
    execute a runnable.
    """

    def __init__(self, kind, uri, *args, config=None, **kwargs):
        self.kind = kind
        #: The main reference to what needs to be run.  This is free
        #: form, but commonly set to the path to a file containing the
        #: test or being the test, or an actual URI with multiple
        #: parts
        self.uri = uri
        #: This attributes holds configuration from Avocado proper
        #: that is passed to runners, as long as a runner declares
        #: its interest in using them with
        #: attr:`avocado.core.nrunner.runner.BaseRunner.CONFIGURATION_USED`
        self.config = config or {}
        self.args = args
        self.tags = kwargs.pop('tags', None)
        self.dependencies = kwargs.pop('dependencies', None)
        self.variant = kwargs.pop('variant', None)
        self.output_dir = kwargs.pop('output_dir', None)
        self.kwargs = kwargs

    def __repr__(self):
        fmt = ('<Runnable kind="{}" uri="{}" config="{}" args="{}" '
               'kwargs="{}" tags="{}" dependencies="{}"> variant="{}"')
        return fmt.format(self.kind, self.uri, self.config, self.args,
                          self.kwargs, self.tags, self.dependencies,
                          self.variant)

    @property
    def identifier(self):
        """Runnable identifier respecting user's format string.

        This is still experimental and we have room for improvements.

        This property it will return an unique identifier for this runnable.
        Please use this property in order to respect user's customization.

        By default runnables has its '{uri}' as identifier.

        Custom formatter can be configured and currently we accept the
        following values as normal f-strings replacements: {uri}, {args},
        and {kwargs}. "args" and "kwargs" are special cases.

        For args, since it is a list, you can use in two different ways:
        "{args}" for the entire list, or "{args[n]}" for a specific element
        inside this list.  The same is valid when using "{kwargs}". With
        kwargs, since it is a dictionary, you have to specify a key as index
        and then the values are used. For instance if you have a kwargs value
        named 'DEBUG', a valid usage could be: "{kwargs[DEBUG]}" and this will
        print the current value to this variable (i.e: True or False).

        Since this is formatter, combined values can be used. Example:
        "{uri}-{args}".
        """
        fmt = self.config.get("runner.identifier_format")

        # For the cases where there is no config (when calling the Runnable
        # directly
        if not fmt:
            return self.uri

        # For args we can use the entire list of arguments or with a specific
        # index.
        args = '-'.join(self.args)
        if 'args' in fmt and '[' in fmt:
            args = self.args

        # For kwargs we can use the entire list of values or with a specific
        # index.
        kwargs = '-'.join(self.kwargs.values())
        if 'kwargs' in fmt and '[' in fmt:
            kwargs = self.kwargs

        options = {'uri': self.uri,
                   'args': args,
                   'kwargs': kwargs}

        return fmt.format(**options)

    @classmethod
    def from_args(cls, args):
        """Returns a runnable from arguments"""
        decoded_args = [_arg_decode_base64(arg) for arg in args.get('arg', ())]
        return cls(args.get('kind'),
                   args.get('uri'),
                   *decoded_args,
                   config=json.loads(args.get('config', '{}'),
                                     cls=ConfigDecoder),
                   **_key_val_args_to_kwargs(args.get('kwargs', [])))

    @classmethod
    def from_recipe(cls, recipe_path):
        """
        Returns a runnable from a runnable recipe file

        :param recipe_path: Path to a recipe file

        :rtype: instance of :class:`Runnable`
        """
        with open(recipe_path, encoding='utf-8') as recipe_file:
            recipe = json.load(recipe_file)
        config = ConfigDecoder.decode_set(recipe.get('config', {}))
        return cls(recipe.get('kind'),
                   recipe.get('uri'),
                   *recipe.get('args', ()),
                   config=config,
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

        if self.config:
            args.append('-c')
            args.append(json.dumps(self.config, cls=ConfigEncoder))

        for arg in self.args:
            args.append('-a')
            if arg.startswith('-'):
                arg = f"base64:{base64.b64encode(arg.encode()).decode('ascii')}"
            args.append(arg)

        if self.tags is not None:
            args.append(f'tags=json:{json.dumps(self.get_serializable_tags())}')

        if self.variant is not None:
            args.append(f'variant=json:{json.dumps(self.variant)}')

        if self.output_dir is not None:
            args.append(f'output_dir={self.output_dir}')

        for key, val in self.kwargs.items():
            if not isinstance(val, str) or isinstance(val, int):
                val = f"json:{json.dumps(val)}"
            args.append(f'{key}={val}')

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
        if self.variant is not None:
            kwargs['variant'] = self.variant
        if self.output_dir is not None:
            kwargs['output_dir'] = self.output_dir
        if kwargs:
            recipe['kwargs'] = kwargs
        return recipe

    def get_json(self):
        """
        Returns a JSON representation

        :rtype: str
        """
        return json.dumps(self.get_dict(), cls=ConfigEncoder)

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
        with open(recipe_path, 'w', encoding='utf-8') as recipe_file:
            recipe_file.write(self.get_json())

    @staticmethod
    def get_capabilities_from_runner_command(runner_command, env=None):
        """Returns the capabilities of a given runner from a command.

        In case of failures, an empty capabilities dictionary is returned.

        When the capabilities are obtained, it also updates the
        :data:`STANDALONE_EXECUTABLE_CONFIG_USED` info.
        """
        cmd = runner_command + ['capabilities']
        try:
            process = subprocess.Popen(cmd,
                                       stdin=subprocess.DEVNULL,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.DEVNULL,
                                       env=env)
        except (FileNotFoundError, PermissionError):
            return {}
        out, _ = process.communicate()

        try:
            capabilities = json.loads(out.decode())
        except json.decoder.JSONDecodeError:
            capabilities = {}

        # lists are not hashable, and here it'd make more sense to have
        # a command as it'd be seen in a command line anyway
        cmd = " ".join(runner_command)
        if cmd not in STANDALONE_EXECUTABLE_CONFIG_USED:
            STANDALONE_EXECUTABLE_CONFIG_USED[cmd] = capabilities.get(
                'configuration_used', [])
        return capabilities

    def is_kind_supported_by_runner_command(self, runner_cmd,
                                            capabilities=None, env=None):
        """Checks if a runner command that seems a good fit declares support."""
        if capabilities is None:
            capabilities = self.get_capabilities_from_runner_command(
                runner_cmd,
                env)
        return self.kind in capabilities.get('runnables', [])

    @staticmethod
    def _module_exists(module_name):
        """Returns whether a nrunner "runner" module exists."""
        module_filename = f'{module_name}.py'
        mod_path = os.path.join('plugins', 'runners', module_filename)
        return pkg_resources.resource_exists('avocado', mod_path)

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

        # When running Avocado Python modules, the interpreter on the new
        # process needs to know where Avocado can be found.
        env = os.environ.copy()
        env['PYTHONPATH'] = ':'.join(p for p in sys.path)

        standalone_executable_cmd = [f'avocado-runner-{self.kind}']
        if self.is_kind_supported_by_runner_command(standalone_executable_cmd):
            runners_registry[self.kind] = standalone_executable_cmd
            return standalone_executable_cmd

        # attempt to find Python module files that are named after the
        # runner convention within the avocado.plugins.runners namespace dir.
        # Looking for the file only avoids an attempt to load the module
        # and should be a lot faster
        module_name = self.kind.replace('-', '_')
        if self._module_exists(module_name):
            full_module_name = f'avocado.plugins.runners.{module_name}'
            candidate_cmd = [sys.executable, '-m', full_module_name]
            if self.is_kind_supported_by_runner_command(candidate_cmd,
                                                        env=env):
                runners_registry[self.kind] = candidate_cmd
                return candidate_cmd

        # look for the runner commands implemented in the base nrunner module
        candidate_cmd = [sys.executable, '-m', 'avocado.core.nrunner']
        if self.is_kind_supported_by_runner_command(candidate_cmd,
                                                    env=env):
            runners_registry[self.kind] = candidate_cmd
            return candidate_cmd

        # exhausted probes, let's save the negative on the cache and avoid
        # future similar problems
        runners_registry[self.kind] = False

    def pick_runner_class_from_entry_point(self):
        """Selects a runner class from entry points based on kind.

        This is related to the :data:`SpawnMethod.PYTHON_CLASS`.

        :returns: a class that inherits from :class:`BaseRunner` or None
        """
        namespace = 'avocado.plugins.runnable.runner'
        for ep in pkg_resources.iter_entry_points(namespace, self.kind):
            try:
                obj = ep.load()
                return obj
            except ImportError:
                return

    def pick_runner_class(self):
        """Selects a runner class from the registry based on kind.

        This is related to the :data:`SpawnMethod.PYTHON_CLASS`

        :param runners_registry: a registry with previously registered
                                 runner classes, keyed by runnable kind
        :param runners_registry: dict
        :returns: a class that inherits from :class:`BaseRunner`
        :raises: ValueError if kind there's no runner from kind of runnable
        """
        runner = self.pick_runner_class_from_entry_point()
        if runner is not None:
            return runner
        raise ValueError(f'Unsupported kind of runnable: {self.kind}')
