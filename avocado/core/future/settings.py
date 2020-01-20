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
AvocadoSettings = configparser + argparser

AvocadoSettings is an attempt to implement part of BP001 and concentrate all
default values in one place. This module will read the Avocado configuration
options from many sources, in the following order:

  1. Default values (defaults.conf or defaults.py). This is a "source code"
     file and should not be changed by the Avocado' user.

  2. User/System configuration files (/etc/avocado or ~/.avocado/). This is
     configured by the user, on a more "permanent way".

  3. Command-line options parsed in runtime. This is configured by the user, on
     a more "temporary way";

ATTENTION: This is a future module, and will be moved out from this package
soon.
"""

import configparser
import glob
import os
import re

from pkg_resources import resource_filename

from ..settings_dispatcher import SettingsDispatcher
from ...utils import path


class SettingsError(Exception):
    """
    Base settings error.
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


class AvocadoSettings:
    """AvocadoSettings, an experimental Avocado configuration handler.

    It is a simple wrapper around configparser and argparse.

    Also, one object of this class could be passed as config to plugins and
    modules.

    Please, not that most of methods and attributes here are private. Only
    public methods and attributes should be used outside this module.
    """

    def __init__(self, config_path=None):
        """Constructor. Tries to find the main settings files and load them.

        :param config_path: Path to a config file. Useful for unittesting.
        """
        self._config = configparser.ConfigParser()
        self._all_config_paths = []
        self._config_paths = []
        self._short_mapping = {}
        self._long_mapping = {}
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
        # 1. Append Defaults
        self._append_pkg_defaults()

        # 2. Override with system config
        self._append_system_config()

        # Allow plugins to modify/extend the list of configs
        dispatcher = SettingsDispatcher()
        if dispatcher.extensions:
            dispatcher.map_method('adjust_settings_paths',
                                  self._all_config_paths)

        # 3. Override with the user's local config
        self._append_user_config()

    def _append_pkg_defaults(self):
        config_pkg_base = os.path.join('etc', 'avocado', 'defaults.conf')
        config_path_pkg = resource_filename('avocado', config_pkg_base)
        self._all_config_paths.append(config_path_pkg)

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

    def _get_option_from_tag(self, tag):
        try:
            mapping = self._long_mapping[tag]
            return self._namespaces[mapping]
        except KeyError:
            msg = "{} not found in internal mapping.".format(tag)
            raise SettingsError(msg)

    def _prepare_base_dirs(self):
        def get_base_dirs():
            if 'VIRTUAL_ENV' in os.environ:
                cfg_dir = os.path.join(os.environ['VIRTUAL_ENV'], 'etc')
                user_dir = os.environ['VIRTUAL_ENV']
            else:
                cfg_dir = '/etc'
                user_dir = os.path.expanduser("~")
            return cfg_dir, user_dir

        cfg_dir, user_dir = get_base_dirs()

        self._config_dir_system = os.path.join(cfg_dir, 'avocado')
        self._config_dir_system_extra = os.path.join(cfg_dir,
                                                     'avocado',
                                                     'conf.d')
        self._config_dir_local = os.path.join(user_dir, '.config', 'avocado')
        self._config_path_system = os.path.join(self._config_dir_system,
                                                'avocado.conf')
        self._config_path_local = os.path.join(self._config_dir_local,
                                               'avocado.conf')

    def as_dict(self):
        """Return an ordered dictionary with the current active settings.

        This will return a ordered dict of both: configparse and merged
        argparse options.
        """
        result = {}
        for section in self._config.sections():
            result[section] = dict(self._config.items(section))
        return result

    def get(self, section, key, key_type=str):
        """Returns the current value inside a setion + key.

        If this section do not exists on config files but it was registered
        dynamicaly with `register_option` by a plugin, this will also get this
        value.

        :param section: Section in configuration file.
        :param key: name of key inside that section.
        :param key_type: how we should handle and return this value.
        """
        try:
            if key_type is str:
                return self._config.get(section, key)
            elif key_type is bool:
                return self._config.getboolean(section, key)
            elif key_type is int:
                return self._config.getint(section, key)
            elif key_type is float:
                return self._config.getfloat(section, key)
            else:
                msg = "Not implemented yet, this will be implemented soon."
                raise SettingsError(msg)
        except configparser.NoSectionError:
            raise SettingsError("Section {} is invalid.".format(section))
        except configparser.Error:
            raise SettingsError("{} is invalid.".format(key))

    def merge_with_arguments(self, arg_parse_config):
        """This method will merge the configparse with argparse.

        After parsing argument options this method should be executed to have
        an unified settings.

        :param arg_parse_config: argparse.config dictionary with all command
        line parsed arguments.
        """
        for tag, value in arg_parse_config.items():
            if value is not None:  # Ignoring None values
                try:
                    option = self._get_option_from_tag(tag)
                except SettingsError:
                    continue  # Not registered yet, using the new module
                section = option.get('section')
                key = option.get('key')
                self.update_settings(section, key, value, False)

    def register_option(self, section, key, default, key_type=str, parser=None,
                        arg_parse_args=None):
        """Register an option dinamically.

        An "option" is a configuration option that could be a config file entry
        alone or associated with a command line equivalent.

        When there is a need for a plugin to register new command line options,
        the plugin should use this method for convinience.

        From now on, all command line options MUST have an associeted config
        file option.

        Make sure that default and key_type are equal to the arg_parse_args for
        consistency.

        :param section: Section name to be registered on configuration.
        :param key: Key name inside the section.
        :param default: Default value to be used if the key is not found on
                        users' config file.
        :param key_type: The option type. Default is str.
        :param parser: Optional. This is the parser that the option should be
                       added, only if there is a command line option too.
                       Default is None.
        :param arg_parse_args: Optional. This is a tuple with the arg parse
                               arguments.

        Example on how to call this method:

        sysinfo = (('-S', '--sysinfo'), {'choices': ('on', 'off'),
                                         'default': 'on',
                                         'help': 'Enable or disable sysinfo '
                                                 'information. Like hardware '
                                                 'details, profiles, etc. '
                                                 'Default is enabled.'})


        register_option(section='sysinfo.collect', key='enabled', default=True,
                        key_type=str, parser=parser, arg_parse_args=sysinfo)


        Note: For now, this is example uses str as key_type, but soon this will
              be converted into a bool.
        """
        def is_long_arg(tag):
            regex = re.compile('^--[a-zA-Z].*')
            return regex.match(tag)

        def is_short_arg(tag):
            regex = re.compile('^-[a-zA-Z].*')
            return regex.match(tag)

        def get_tags(arg_parse_args):
            try:
                return arg_parse_args[0]
            except TypeError:
                raise SettingsError("You need to pass arg_parse_args.")
            except KeyError:
                raise SettingsError("Your arg_parse_args must be a tuple.")

        def get_long_arg(arg_parse_args, remove_dashes=True):
            for tag in get_tags(arg_parse_args):
                if is_long_arg(tag):
                    if remove_dashes:
                        return tag[2:]
                    else:
                        return tag
            raise SettingsError("You need a long arg.")

        def get_short_arg(arg_parse_args, remove_dash=True):
            for tag in get_tags(arg_parse_args):
                if is_short_arg(tag):
                    if remove_dash:
                        return tag[1:]
                    else:
                        return tag

        namespace = "{}.{}".format(section, key)

        # Check if namespace is already registered
        if namespace in self._namespaces:
            msg = "Key {} already registered on section {}".format(key,
                                                                   section)
            raise SettingsError(msg)

        # Register the option to a dynamic in-memory namespaces
        self._namespaces[namespace] = {'section': section,
                                       'key': key,
                                       'default': default,
                                       'key_type': key_type,
                                       'parser': parser,
                                       'arg_parse_args': arg_parse_args}

        if not parser:
            # Nothing else to do here
            return

        long_arg = get_long_arg(arg_parse_args)
        short_arg = get_short_arg(arg_parse_args)

        # Check if long_arg is already registered
        if long_arg and long_arg in self._long_mapping:
            msg = "Option {} already registered.".format(long_arg)
            raise SettingsError(msg)
        self._long_mapping[long_arg] = namespace

        # Add long_arg and short_arg to mappings. long_arg is mandatory here.
        if short_arg:
            self._short_mapping[short_arg] = long_arg

        # Register the option argument equivalent to argparse
        parser.add_argument(*arg_parse_args[0], **arg_parse_args[1])

    def update_settings(self, section, key, value, raise_exception=True):
        try:
            # For configparser optionvalues must be string. The conversion
            # happens on getting the value.
            self._config[section][key] = str(value)
        except KeyError:
            if raise_exception:
                raise SettingsError("{} not found in {}".format(key, section))


settings = AvocadoSettings()  # pylint: disable-msg=invalid-name
