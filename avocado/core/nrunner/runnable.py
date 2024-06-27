import base64
import collections
import json
import logging
import os
import subprocess
import sys

import pkg_resources

try:
    import jsonschema

    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False

from avocado.core.dependencies.dependency import Dependency
from avocado.core.nrunner.config import ConfigDecoder, ConfigEncoder
from avocado.core.settings import settings
from avocado.core.utils.eggenv import get_python_path_env_if_egg

LOG = logging.getLogger(__name__)

#: All known runner commands, capable of being used by a
#: SpawnMethod.STANDALONE_EXECUTABLE compatible spawners
RUNNERS_REGISTRY_STANDALONE_EXECUTABLE = {}

#: The configuration that is known to be used by standalone runners
STANDALONE_EXECUTABLE_CONFIG_USED = {}

#: Location used for schemas when packaged (as in RPMs)
SYSTEM_WIDE_SCHEMA_PATH = "/usr/share/avocado/schemas"

#: Configuration used by all runnables, no matter what its kind.  The
#: configuration that a kind uses in addition to this is set in their
#: own class attribute "CONFIGURATION_USED"
CONFIGURATION_USED = ["runner.identifier_format"]


class RunnableRecipeInvalidError(Exception):
    """Signals that a runnable recipe is not well formed, contains
    missing or bad data"""


def _arg_decode_base64(arg):
    """
    Decode arguments possibly encoded as base64

    :param arg: the possibly encoded argument
    :type arg: str
    :returns: the decoded argument
    :rtype: str
    """
    prefix = "base64:"
    if arg.startswith(prefix):
        content = arg[len(prefix) :]
        return base64.decodebytes(content.encode()).decode()
    return arg


def _kwarg_decode_json(value):
    """
    Decode arguments possibly encoded as base64

    :param value: the possibly encoded argument
    :type value: str
    :returns: the decoded keyword argument as Python object
    """
    prefix = "json:"
    if value.startswith(prefix):
        content = value[len(prefix) :]
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
        self._config = {}
        if config is None:
            config = self.filter_runnable_config(kind, {})
        self.config = config or {}
        self.args = args
        self.tags = kwargs.pop("tags", None)
        self.dependencies = self.read_dependencies(kwargs.pop("dependencies", None))
        self.variant = kwargs.pop("variant", None)
        self.output_dir = kwargs.pop("output_dir", None)
        #: list of (:class:`ReferenceResolutionAssetType`, str) tuples
        #: expressing assets that the test will require in order to run.
        self.assets = kwargs.pop("assets", None)
        self.kwargs = kwargs

    def __repr__(self):
        fmt = (
            '<Runnable kind="{}" uri="{}" config="{}" args="{}" '
            'kwargs="{}" tags="{}" dependencies="{}" variant="{}">'
        )
        return fmt.format(
            self.kind,
            self.uri,
            self.config,
            self.args,
            self.kwargs,
            self.tags,
            self.dependencies,
            self.variant,
        )

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
        fmt = self.config.get("runner.identifier_format", "{uri}")

        # Optimize for the most common scenario
        if fmt == "{uri}":
            return self.uri

        # For args we can use the entire list of arguments or with a specific
        # index.
        args = "-".join(self.args)
        if "args" in fmt and "[" in fmt:
            args = self.args

        # For kwargs we can use the entire list of values or with a specific
        # index.
        kwargs = "-".join(str(self.kwargs.values()))
        if "kwargs" in fmt and "[" in fmt:
            kwargs = self.kwargs

        options = {"uri": self.uri, "args": args, "kwargs": kwargs}

        return fmt.format(**options)

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, config):
        """Sets the config values based on the runnable kind.

        This is not avocado config, it is a runnable config which is a subset
        of avocado config based on `STANDALONE_EXECUTABLE_CONFIG_USED` which
        describes essential configuration values for each runner kind.

        :param config: A config dict with new values for Runnable.
        :type config: dict
        """
        configuration_used = Runnable.get_configuration_used_by_kind(self.kind)
        if not set(configuration_used).issubset(set(config.keys())):
            LOG.warning(
                "The runnable config should have only values "
                "essential for its runner. In the next version of "
                "avocado, this will raise a Value Error. Please "
                "use avocado.core.nrunner.runnable.Runnable.filter_runnable_config "
                "or avocado.core.nrunner.runnable.Runnable.from_avocado_config"
            )
        self._config = config

    @classmethod
    def from_args(cls, args):
        """Returns a runnable from arguments"""
        decoded_args = [_arg_decode_base64(arg) for arg in args.get("arg", ())]
        return cls.from_avocado_config(
            args.get("kind"),
            args.get("uri"),
            *decoded_args,
            config=json.loads(args.get("config", "{}"), cls=ConfigDecoder),
            **_key_val_args_to_kwargs(args.get("kwargs", [])),
        )

    @staticmethod
    def _validate_recipe_json_schema(recipe):
        """Attempts to validate the runnable recipe using a JSON schema

        :param recipe: the recipe already parsed from JSON into a dict
        :type recipe: dict
        :returns: whether the runnable recipe JSON was attempted to be
                  validated with a JSON schema
        :rtype: bool
        :raises: RunnableRecipeInvalidError if the recipe is invalid
        """
        if not JSONSCHEMA_AVAILABLE:
            return False
        schema_filename = "runnable-recipe.schema.json"
        schema_path = pkg_resources.resource_filename(
            "avocado", os.path.join("schemas", schema_filename)
        )
        if not os.path.exists(schema_path):
            schema_path = os.path.join(SYSTEM_WIDE_SCHEMA_PATH, schema_filename)
            if not os.path.exists(schema_path):
                return False
        with open(schema_path, "r", encoding="utf-8") as schema:
            try:
                jsonschema.validate(recipe, json.load(schema))
            except jsonschema.exceptions.ValidationError as details:
                raise RunnableRecipeInvalidError(details)
        return True

    @classmethod
    def _validate_recipe(cls, recipe):
        """Validates a recipe using either JSON schema or builtin logic

        :param recipe: the recipe already parsed from JSON into a dict
        :type recipe: dict
        :returns: None
        :raises: RunnableRecipeInvalidError if the recipe is invalid
        """
        if not cls._validate_recipe_json_schema(recipe):
            # This is a simplified validation of the recipe
            allowed = set(["kind", "uri", "args", "kwargs", "config"])
            if not "kind" in recipe:
                raise RunnableRecipeInvalidError('Missing required property "kind"')
            if not set(recipe.keys()).issubset(allowed):
                raise RunnableRecipeInvalidError(
                    "Additional properties are not allowed"
                )

    @classmethod
    def from_dict(cls, recipe_dict):
        """
        Returns a runnable from a runnable dictionary

        :param recipe_dict: a dictionary with runnable keys and values

        :rtype: instance of :class:`Runnable`
        """
        cls._validate_recipe(recipe_dict)
        config = ConfigDecoder.decode_set(recipe_dict.get("config", {}))
        return cls.from_avocado_config(
            recipe_dict.get("kind"),
            recipe_dict.get("uri"),
            *recipe_dict.get("args", ()),
            config=config,
            **recipe_dict.get("kwargs", {}),
        )

    @classmethod
    def from_recipe(cls, recipe_path):
        """
        Returns a runnable from a runnable recipe file

        :param recipe_path: Path to a recipe file

        :rtype: instance of :class:`Runnable`
        """
        with open(recipe_path, encoding="utf-8") as recipe_file:
            recipe_dict = json.load(recipe_file)
        return cls.from_dict(recipe_dict)

    @classmethod
    def from_avocado_config(cls, kind, uri, *args, config=None, **kwargs):
        """Creates runnable with only essential config for runner of specific kind."""
        if not config:
            config = {}
        config = cls.filter_runnable_config(kind, config)
        return cls(kind, uri, *args, config=config, **kwargs)

    @classmethod
    def get_configuration_used_by_kind(cls, kind):
        """Returns the configuration used by a runner of a given kind

        :param kind: Kind of runner which should use the configuration.
        :type kind: str
        :returns: the configuration used by a runner of a given kind
        :rtype: list
        """
        configuration_used = []
        klass = cls.pick_runner_class_from_entry_point_kind(kind)
        if klass is not None:
            configuration_used = klass.CONFIGURATION_USED
        else:
            command = Runnable.pick_runner_command(kind)
            if command is not None:
                command = " ".join(command)
                configuration_used = STANDALONE_EXECUTABLE_CONFIG_USED.get(command)
        return configuration_used

    @classmethod
    def filter_runnable_config(cls, kind, config):
        """
        Returns only essential values for specific runner.

        It will use configuration from argument completed by values from
        config file and avocado default configuration.

        :param kind: Kind of runner which should use the configuration.
        :type kind: str
        :param config: Configuration values for runner. If some values will be
                       missing the default ones and from config file will be
                       used.
        :type config: dict
        :returns: Config dict, which has only values essential for runner
                  based on STANDALONE_EXECUTABLE_CONFIG_USED
        :rtype: dict
        """
        whole_config = settings.as_dict()
        filtered_config = {}
        config_items = cls.get_configuration_used_by_kind(kind) + CONFIGURATION_USED
        for config_item in config_items:
            filtered_config[config_item] = config.get(
                config_item, whole_config.get(config_item)
            )
        return filtered_config

    def read_dependencies(self, dependencies_dict):
        """
        Converts dependencies from json to avocado.core.dependencies.dependency.Dependency

        :param dependencies: Runnable dependencies
        :type dependencies: list of dict, or list of Dependency
        :returns: Runnable dependencies in avocado.core.dependencies.dependency.Dependency format.
        :rtype: list of Dependency
        """
        if isinstance(dependencies_dict, list):
            return list(
                map(
                    lambda d: (
                        Dependency.from_dictionary(d) if isinstance(d, dict) else d
                    ),
                    dependencies_dict,
                )
            )

    def get_command_args(self):
        """
        Returns the command arguments that adhere to the runner interface

        This is useful for building 'runnable-run' and 'task-run' commands
        that can be executed on a command line interface.

        :returns: the arguments that can be used on an avocado-runner command
        :rtype: list
        """
        args = ["-k", self.kind]
        if self.uri is not None:
            args.append("-u")
            args.append(self.uri)

        if self.config:
            args.append("-c")
            args.append(json.dumps(self.config, cls=ConfigEncoder))

        for arg in self.args:
            args.append("-a")
            if arg.startswith("-"):
                arg = f"base64:{base64.b64encode(arg.encode()).decode('ascii')}"
            args.append(arg)

        if self.tags is not None:
            args.append(f"tags=json:{json.dumps(self.get_serializable_tags())}")

        if self.variant is not None:
            args.append(f"variant=json:{json.dumps(self.variant)}")

        if self.output_dir is not None:
            args.append(f"output_dir={self.output_dir}")

        for key, val in self.kwargs.items():
            if not isinstance(val, str) or isinstance(val, int):
                val = f"json:{json.dumps(val)}"
            args.append(f"{key}={val}")

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
            recipe["uri"] = self.uri
        recipe["config"] = self.config
        if self.args is not None:
            recipe["args"] = self.args
        kwargs = self.kwargs.copy()
        if self.tags is not None:
            kwargs["tags"] = self.get_serializable_tags()
        if self.variant is not None:
            kwargs["variant"] = self.variant
        if self.output_dir is not None:
            kwargs["output_dir"] = self.output_dir
        if kwargs:
            recipe["kwargs"] = kwargs
        return recipe

    def get_json(self):
        """
        Returns a JSON representation

        :rtype: str
        """
        return json.dumps(self.get_dict(), cls=ConfigEncoder)

    def get_serializable_tags(self):
        if self.tags is None:
            return {}
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
        with open(recipe_path, "w", encoding="utf-8") as recipe_file:
            recipe_file.write(self.get_json())

    @staticmethod
    def get_capabilities_from_runner_command(runner_command, env=None):
        """Returns the capabilities of a given runner from a command.

        In case of failures, an empty capabilities dictionary is returned.

        When the capabilities are obtained, it also updates the
        :data:`STANDALONE_EXECUTABLE_CONFIG_USED` info.
        """
        cmd = runner_command + ["capabilities"]
        try:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                env=env,
            )
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
                "configuration_used", []
            )
        return capabilities

    @staticmethod
    def is_kind_supported_by_runner_command(
        kind, runner_cmd, capabilities=None, env=None
    ):
        """Checks if a runner command that seems a good fit declares support."""
        if capabilities is None:
            capabilities = Runnable.get_capabilities_from_runner_command(
                runner_cmd, env
            )
        return kind in capabilities.get("runnables", [])

    @staticmethod
    def pick_runner_command(kind, runners_registry=None):
        """Selects a runner command based on the runner kind.

        And when finding a suitable runner, keeps found runners in registry.

        This utility function will look at the given kind and try to find
        a matching runner.  The matching runner probe results are kept in
        a registry (that is modified by this function) so that further
        executions take advantage of previous probes.

        This is related to the :data:`SpawnMethod.STANDALONE_EXECUTABLE`

        :param kind: runners' kind
        :type kind: str
        :param runners_registry: a registry with previously found (and not
                                 found) runners keyed by runnable kind
        :type runners_registry: dict
        :returns: command line arguments to execute the runner
        :rtype: list of str or None
        """
        if runners_registry is None:
            runners_registry = RUNNERS_REGISTRY_STANDALONE_EXECUTABLE
        runner_cmd = runners_registry.get(kind)
        if runner_cmd is False:
            return None
        if runner_cmd is not None:
            return runner_cmd

        standalone_executable_cmd = [f"avocado-runner-{kind}"]
        if Runnable.is_kind_supported_by_runner_command(
            kind, standalone_executable_cmd
        ):
            runners_registry[kind] = standalone_executable_cmd
            return standalone_executable_cmd

        # attempt to find Python module files that are named after the
        # runner convention within the avocado.plugins.runners namespace dir.
        # Looking for the file only avoids an attempt to load the module
        # and should be a lot faster
        module_name = Runnable.pick_runner_module_from_entry_point_kind(kind)
        if module_name is not None:
            candidate_cmd = [sys.executable, "-m", module_name]
            if Runnable.is_kind_supported_by_runner_command(
                kind, candidate_cmd, env=get_python_path_env_if_egg()
            ):
                runners_registry[kind] = candidate_cmd
                return candidate_cmd

        # exhausted probes, let's save the negative on the cache and avoid
        # future similar problems
        runners_registry[kind] = False

    def runner_command(self, runners_registry=None):
        """Selects a runner command based on the runner.

        And when finding a suitable runner, keeps found runners in registry.

        This utility function will look at the given task and try to find
        a matching runner.  The matching runner probe results are kept in
        a registry (that is modified by this function) so that further
        executions take advantage of previous probes.

        This is related to the :data:`SpawnMethod.STANDALONE_EXECUTABLE`

        :param runners_registry: a registry with previously found (and not
                                 found) runners keyed by runnable kind
        :type runners_registry: dict
        :returns: command line arguments to execute the runner
        :rtype: list of str or None
        """
        return Runnable.pick_runner_command(self.kind, runners_registry)

    @staticmethod
    def pick_runner_module_from_entry_point_kind(kind):
        """Selects a runner module from entry points based on kind.

        This is related to the :data:`SpawnMethod.STANDALONE_EXECUTABLE`.
        The module found (if any) will be one that can be used with the
        Python interpreter using the "python -m $module" command.

        :param kind: Kind of runner
        :type kind: str
        :returns: a module that can be run with "python -m" or None"""
        namespace = "console_scripts"
        section = f"avocado-runner-{kind}"
        for ep in pkg_resources.iter_entry_points(namespace, section):
            return ep.module_name

    @staticmethod
    def pick_runner_class_from_entry_point_kind(kind):
        """Selects a runner class from entry points based on kind.

        This is related to the :data:`SpawnMethod.PYTHON_CLASS`.

        :param kind: Kind of runner
        :type kind: str
        :returns: a class that inherits from :class:`BaseRunner` or None
        """
        namespace = "avocado.plugins.runnable.runner"
        for ep in pkg_resources.iter_entry_points(namespace, kind):
            try:
                obj = ep.load()
                return obj
            except ImportError:
                return

    def pick_runner_class_from_entry_point(self):
        """Selects a runner class from entry points based on kind.

        This is related to the :data:`SpawnMethod.PYTHON_CLASS`.

        :returns: a class that inherits from :class:`BaseRunner` or None
        """
        return Runnable.pick_runner_class_from_entry_point_kind(self.kind)

    def pick_runner_class(self):
        """Selects a runner class from the registry based on kind.

        This is related to the :data:`SpawnMethod.PYTHON_CLASS`

        :returns: a class that inherits from :class:`BaseRunner`
        :raises: ValueError if kind there's no runner from kind of runnable
        """
        runner = self.pick_runner_class_from_entry_point()
        if runner is not None:
            return runner
        raise ValueError(f"Unsupported kind of runnable: {self.kind}")
