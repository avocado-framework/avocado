# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; specifically version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# This code was inspired in the autotest project,
# client/shared/settings.py
#
# Authors: Travis Miller <raphtee@google.com>
#          Beraldo Leal <bleal@redhat.com>

"""
This module is a new and experimental configuration handler.

This will handle both, command line args and configuration files.
Settings() = configparser + argparser

Settings() is an attempt to implement part of BP001 and concentrate all
default values in one place. This module will read the Avocado configuration
options from many sources, in the following order:

  1. Default values: This is a "source code" defined. When plugins or core
     needs a settings, basically needs to call settings.register_option() with
     default value as argument. Developers only need to register the default
     value once, here when calling this methods.

  2. User/System configuration files (/etc/avocado or ~/.avocado/): This is
     configured by the user, on a more "permanent way".

  3. Command-line options parsed in runtime. This is configured by the user, on
     a more "temporary way";

ATTENTION: This is a future module, and will be moved out from this package
soon.
"""

import configparser
import glob
import json
import os

from ..settings_dispatcher import SettingsDispatcher
from ...utils import path


class SettingsError(Exception):
    """
    Base settings error.
    """


class DuplicatedNamespace(SettingsError):
    """
    Raised when a namespace is already registered.
    """


class NamespaceNotRegistered(SettingsError):
    """
    Raised when a namespace is not registered.
    """


class ConfigFileNotFound(SettingsError):
    """
    Error thrown when the main settings file could not be found.
    """

    def __init__(self, path_list):
        super(ConfigFileNotFound, self).__init__()
        self.path_list = path_list

    def __str__(self):
        return ("Could not find the avocado config file after looking in: %s" %
                self.path_list)


class ConfigOption:
    def __init__(self, namespace, help_msg, key_type=str, default=None,
                 parser=None, short_arg=None, long_arg=None,
                 positional_arg=False, choices=None, nargs=None,
                 metavar=None, required=None, action=None):
        self.namespace = namespace
        self.help_msg = help_msg
        self.key_type = key_type
        self.default = default
        self.parser = parser
        self.short_arg = short_arg
        self.long_arg = long_arg
        self.positional_arg = positional_arg
        self.choices = choices
        self.nargs = nargs
        self._metavar = metavar
        self.required = required
        self._action = action
        self._value = None

        self._update_argparser()

    @property
    def action(self):
        if self.key_type is bool:
            # action is automatic when using bool types
            if self.default is False:
                return 'store_true'
            else:
                return 'store_false'
        return self._action

    @property
    def section(self):
        return '.'.join(self.namespace.split('.')[:-1])

    @property
    def key(self):
        return self.namespace.split('.')[-1]

    @property
    def value(self):
        if self._value:
            return self._value
        return self.default

    @property
    def name_or_tags(self):
        if self.positional_arg:
            return self.key
        tags = []
        if self.short_arg:
            tags.append(self.short_arg)
        if self.long_arg:
            tags.append(self.long_arg)
        return tags

    @property
    def argparse_type(self):
        # type is automatic when using lists because Argparse do not support
        # list on command-line. They are comma separated strings that will be
        # converted to list here.
        if self.key_type is list:
            return str
        else:
            return self.key_type

    @property
    def metavar(self):
        if self.positional_arg:
            if self._metavar is None:
                return self.key
        return self._metavar

    @property
    def arg_parse_args(self):
        args = {'help': self.help_msg,
                'default': None}

        if self.nargs:
            args['nargs'] = self.nargs
        if self.metavar:
            args['metavar'] = self.metavar
        if self.choices:
            args['choices'] = self.choices
        if self.action:
            args['action'] = self.action

        if self.key_type is not bool:
            # We don't specify type for bool
            args['type'] = self.argparse_type

        if not self.positional_arg:
            args['required'] = self.required
            args['dest'] = self.namespace  # most of the magic is here

        return args

    def _as_list(self, value):
        if value == '':
            return []

        if isinstance(value, str):
            return [v for v in value.strip('[]').split(',') if v]

        if isinstance(value, list):
            return value

        raise ValueError("{} could not be converted into a list".format(value))

    def _update_argparser(self):
        if not self.parser:
            return

        if self.positional_arg:
            self.parser.add_argument(self.namespace, **self.arg_parse_args)
        else:
            self.parser.add_argument(*self.name_or_tags, **self.arg_parse_args)

    def add_argparser(self, parser, long_arg, short_arg=None,
                      positional_arg=False, choices=None, nargs=None,
                      metavar=None, required=None, action=None):
        """Add an command-line argparser to this option."""

        self.parser = parser
        self.short_arg = short_arg
        self.long_arg = long_arg
        self.positional_arg = positional_arg
        self.choices = choices
        self.nargs = nargs
        self._metavar = metavar
        self.required = required
        self._action = action

        self._update_argparser()

    def set_value(self, value, convert=False):
        dst_type = self.key_type

        if convert is False:
            self._value = value
        else:
            if dst_type is list:
                self._value = self._as_list(value)
            elif dst_type is bool:
                self._value = value.lower() in ['true', 'on', 'y', 'yes', '1']
            else:
                self._value = dst_type(value)


class Settings:
    """Settings, an experimental Avocado configuration handler.

    It is a simple wrapper around configparser and argparse.

    Also, one object of this class could be passed as config to plugins and
    modules.

    Basically, if you are going to have options (configuration options), either
    via config file or via command line, you should use this class. You don't
    need to instantiate a new settings, just import and use
    `register_option()`.

        from avocado.core.future.settings import settings
        settings.register_option(...)

    And when you needs get the current value, check on your configuration for
    the namespace (section.key) that you registered. i.e:

        value = config.get('a.section.with.subsections.key')

    .. note:: Please, do not use a default value when using `get()` here. If
              you are using an existing namespace, get will always return a
              value, either the default value, or the value set by the user.

    Please, note that most of methods and attributes here are private. Only
    public methods and attributes should be used outside this module.
    """

    def __init__(self, config_path=None):
        """Constructor. Tries to find the main settings files and load them.

        :param config_path: Path to a config file. Useful for unittesting.
        """
        self._config = configparser.ConfigParser()
        self._all_config_paths = []
        self._config_paths = []
        self._namespaces = {}

        # 1. Prepare config paths
        if config_path is None:
            self._prepare_base_dirs()
            self._append_config_paths()
        else:
            # Only used by unittests (the --config parses the file later)
            self._all_config_paths.append(config_path)

        # 2. Parse/read all config paths
        self._config_paths = self._config.read(self._all_config_paths)

        if not self._config_paths:
            raise ConfigFileNotFound(self._all_config_paths)

    def _append_config_paths(self):
        # Override with system config
        self._append_system_config()

        # Allow plugins to modify/extend the list of configs
        dispatcher = SettingsDispatcher()
        if dispatcher.extensions:
            dispatcher.map_method('adjust_settings_paths',
                                  self._all_config_paths)

        # Override with the user's local config
        self._append_user_config()

    def _append_system_config(self):
        self._all_config_paths.append(self._config_path_system)
        configs = glob.glob(os.path.join(self._config_dir_system_extra,
                                         '*.conf'))
        for extra_file in configs:
            self._all_config_paths.append(extra_file)

    def _append_user_config(self):
        if not os.path.exists(self._config_path_local):
            self._create_empty_config()
        self._all_config_paths.append(self._config_path_local)

    def _create_empty_config(self):
        try:
            path.init_dir(self._config_dir_local)
            with open(self._config_path_local, 'w') as config_local_fileobj:
                content = ("# You can use this file to override "
                           "configuration values from '%s and %s\n"
                           % (self._config_path_system,
                              self._config_dir_system_extra))
                config_local_fileobj.write(content)
        except IOError:     # Some users can't write it (docker)
            pass

    def _prepare_base_dirs(self):
        cfg_dir = '/etc'
        user_dir = os.path.expanduser("~")

        if 'VIRTUAL_ENV' in os.environ:
            cfg_dir = os.path.join(os.environ['VIRTUAL_ENV'], 'etc')
            user_dir = os.environ['VIRTUAL_ENV']

        self._config_dir_system = os.path.join(cfg_dir, 'avocado')
        self._config_dir_system_extra = os.path.join(cfg_dir,
                                                     'avocado',
                                                     'conf.d')
        self._config_dir_local = os.path.join(user_dir, '.config', 'avocado')
        self._config_path_system = os.path.join(self._config_dir_system,
                                                'avocado.conf')
        self._config_path_local = os.path.join(self._config_dir_local,
                                               'avocado.conf')

    def add_argparser_to_option(self, namespace, parser, long_arg,
                                short_arg=None, positional_arg=False,
                                choices=None, nargs=None, metavar=None,
                                required=None, action=None,
                                allow_multiple=False):
        """Add a command-line argument parser to an existing option.

        This method is useful to add a parser when the option is registered
        without any command-line argument options. You should call the
        "register_option()" method for the namespace before calling this
        method.

        Arguments

        namespace : str
            What is the namespace of the option (section.key)

        parser : argparser parser
            Since that you would like to have a command-line option, you should
            specify what is the parser or parser group that we should add this
            option.

        long_arg: : str
            A long option for the command-line. i.e: `--debug` for debug.

        short_arg : str
            A short option for the command-line. i.e: `-d` for debug.

        positional_arg : bool
            If this option is an positional argument or not. Default is
            `False`.

        choices : tuple
            If you would like to limit the option to a few choices. i.e:
            ('foo', 'bar')

        nargs : int or str
            The number of command-line arguments that should be consumed. Could
            be a int, '?', '*' or '+'. For more information visit the argparser
            documentation.

        metavar : str
            String presenting available sub-commands in help, if None we will
            use the section+key as metavar.

        required : bool
            If this is a required option or not when on command-line. Default
            is False.

        action :
            The basic type of action to be taken when this argument is
            encountered at the command line. For more information visit the
            argparser documentation.

        allow_multiple :
            Whether the same option may be available on different parsers.
            This is useful when the same option is avaiable on different
            commands, such as "avocado run" or "avocado list".
        """
        option = None
        try:
            option = self._namespaces[namespace]
        except KeyError:
            msg = "Namespace not found: {}".format(namespace)
            raise NamespaceNotRegistered(msg)

        if option and option.parser and not allow_multiple:
            msg = "Parser already registered for this namespace"
            raise SettingsError(msg)

        option.add_argparser(parser, short_arg, long_arg, positional_arg,
                             choices, nargs, metavar, required, action)

    def as_dict(self):
        """Return an dictionary with the current active settings.

        This will return a dict with all parsed options (either via config file
        or via command-line).
        """
        result = {}
        for namespace, option in self._namespaces.items():
            result[namespace] = option.value
        return result

    def as_json(self):
        """Return a JSON with the current active settings.

        This will return a JSON with all parsed options (either via config file
        or via command-line).
        """
        return json.dumps(self.as_dict(), indent=4)

    def merge_with_arguments(self, arg_parse_config):
        """Merge the current settings with the command-line args.

        After parsing argument options this method should be executed to have
        an unified settings.

        :param arg_parse_config: argparse.config dictionary with all
                                 command-line parsed arguments.
        """
        for tag, value in arg_parse_config.items():
            # This check is important! For argparse when an option is
            # not passed will return None. We need to update only the
            # options that the user has specified.
            if value is not None:
                try:
                    option = self._namespaces[tag]
                except KeyError:
                    continue  # Not registered yet, using the new module
                self.update_option("{}.{}".format(option.section,
                                                  option.key),
                                   value)

    def merge_with_configs(self):
        """Merge the current settings with the config file options.

        After parsing config file options this method should be executed to
        have an unified settings.
        """
        for section in self._config:
            items = self._config.items(section)
            for key, value in items:
                namespace = "{}.{}".format(section, key)
                self.update_option(namespace, value, convert=True)

    def register_option(self, section, key, default, help_msg, key_type=str,
                        parser=None, positional_arg=False, short_arg=None,
                        long_arg=None, choices=None, nargs=None, metavar=None,
                        required=False, action=None, allow_multiple=False):
        """Method used to register a configuration option inside Avocado.

        This should be used to register a settings option (either config file
        option or command-line option). This is the central point that plugins
        and core should use to register a new configuration option.

        This method will take care of the 'under the hood dirt', registering
        the configparse option and, if desired, the argparse too.  Instead of
        using argparse and/or configparser, Avocado's contributors should use
        this method.

        Using this method, you need to specify a "section", "key", "default"
        value and a "help_msg" always. This will create a relative
        configuration file option for you.

        For instance:

            settings.reigster_option(section='foo', key='bar', default='hello',
                                     help_msg='this is just a test')

        This will register a 'foo.bar' namespace inside Avocado internals
        settings. And this could be now, be changed by the users or system
        configuration option:

           [foo]
           bar = a different message replacing 'hello'

        If you would like to provide also the flexibility to the user change
        the values via command-line, you should pass the other arguments.

        Arguments

        section : str
            The configuration file section that your option should be present.
            You can specify subsections with dots. i.e: run.output.json

        key : str
            What is the key name of your option inside that section.

        default : typeof(key_type)
            What is the default value of your option if the key is not present
            inside the section on all configuration files.

        help_msg : str
            The help message that will be displayed at command-line (-h) and
            configuration file template.

        key_type : any method
            What is the type of your option? Currently supported: int, list,
            str or a custom method. Default is `str`.

        parser : argparser parser
            Since that you would like to have a command-line option, you should
            specify what is the parser or parser group that we should add this
            option.

        positional_arg : bool
            If this option is an positional argument or not. Default is
            `False`.

        short_arg : str
            A short option for the command-line. i.e: `-d` for debug.

        long_arg: : str
            A long option for the command-line. i.e: `--debug` for debug.

        choices : tuple
            If you would like to limit the option to a few choices. i.e:
            ('foo', 'bar')

        nargs : int or str
            The number of command-line arguments that should be consumed. Could
            be a int, '?', '*' or '+'. For more information visit the argparser
            documentation.

        metavar : str
            String presenting available sub-commands in help, if None we will
            use the section+key as metavar.

        required : bool
            If this is a required option or not when on command-line. Default
            is False.

        action :
            The basic type of action to be taken when this argument is
            encountered at the command line. For more information visit the
            argparser documentation.

        allow_multiple :
            Whether the same option may be available on different parsers.
            This is useful when the same option is avaiable on different
            commands, such as "avocado run" or "avocado list".

        .. note:: Most of the arguments here (like parser, positional_arg,
                  short_arg, long_arg, choices, nargs, metavar, required and
                  action) are only necessary if you would like to add a
                  command-line option.
        """
        namespace = "{}.{}".format(section, key)
        # Check if namespace is already registered
        if namespace in self._namespaces:
            if not allow_multiple:
                msg = 'Key "{}" already registered under section "{}"'.format(key,
                                                                              section)
                raise DuplicatedNamespace(msg)
            else:
                self.add_argparser_to_option(namespace, parser, long_arg,
                                             short_arg, positional_arg,
                                             choices, nargs, metavar,
                                             required, action,
                                             allow_multiple)
        else:
            option = ConfigOption(namespace, help_msg, key_type, default,
                                  parser, short_arg, long_arg, positional_arg,
                                  choices, nargs, metavar, required, action)

            # Register the option to a dynamic in-memory namespaces
            self._namespaces[namespace] = option

    def update_option(self, namespace, value, convert=False):
        """Convenient method to change the option's value.

        This will update the value on Avocado internals and if necessary the
        type conversion will be realized.

        For instance, if an option was registered as bool and you call:

            settings.register_option(namespace='foo.bar', value='true',
                                     convert=True)

        This will be stored as True, because Avocado will get the 'key_type'
        registered and apply here for the conversion.

        This method is useful when getting values from config files where
        everything is stored as string and a conversion is needed.

        Arguments

        namespace : str
            Your section plus your key, separated by dots. The last
            part of the namespace is your key. i.e: run.outputs.json.enabled
            (section is `run.outputs.json` and key is `enabled`)

        value : any type
            This is the new value to update.

        convert : bool
            If Avocado should try to convert the value and store it as the
            'key_type' specified during the register. Default is False.
        """
        if namespace not in self._namespaces:
            return

        self._namespaces[namespace].set_value(value, convert)


settings = Settings()  # pylint: disable-msg=invalid-name
