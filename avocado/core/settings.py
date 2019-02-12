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
# Author: Travis Miller <raphtee@google.com>

"""
Reads the avocado settings from a .ini file (from python ConfigParser).
"""
import ast
import os
import glob

try:
    import ConfigParser
except ImportError:
    import configparser as ConfigParser

from pkg_resources import resource_filename
from pkg_resources import resource_isdir
from pkg_resources import resource_listdir
from six import string_types
from stevedore import ExtensionManager

from ..utils import path


class SettingsDispatcher(ExtensionManager):

    """
    Dispatchers that allows plugins to modify settings

    It's not the standard "avocado.core.dispatcher" because that one depends
    on settings. This dispatcher is the bare-stevedore dispatcher which is
    executed before settings is parsed.
    """

    def __init__(self):
        super(SettingsDispatcher, self).__init__('avocado.plugins.settings',
                                                 invoke_on_load=True,
                                                 invoke_kwds={},
                                                 propagate_map_exceptions=True)


class SettingsError(Exception):
    """
    Base settings error.
    """


class SettingsValueError(SettingsError):
    """
    Error thrown when we could not convert successfully a key to a value.
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


def convert_value_type(value, value_type):
    """
    Convert a string value to a given value type.

    :param value: Value we want to convert.
    :type value: str.
    :param value_type: Type of the value we want to convert.
    :type value_type: str or type.

    :return: Converted value type.
    :rtype: Dependent on value_type.

    :raise: TypeError, in case it was not possible to convert values.
    """
    # strip off leading and trailing white space
    try:
        sval = value.strip()
    except Exception:
        sval = value

    if isinstance(value_type, string_types):
        if value_type == 'str':
            value_type = str
        elif value_type == 'bool':
            value_type = bool
        elif value_type == 'int':
            value_type = int
        elif value_type == 'float':
            value_type = float
        elif value_type == 'list':
            value_type = list
        elif value_type == 'path':
            value_type = os.path.expanduser

    if value_type is None:
        value_type = str

    # if length of string is zero then return None
    if not sval:
        if value_type == str:
            return ""
        if value_type == os.path.expanduser:
            return ""
        if value_type == bool:
            return False
        if value_type == int:
            return 0
        if value_type == float:
            return 0.0
        if value_type == list:
            return []
        return None

    if value_type == bool:
        if sval.lower() == "false":
            return False
        return True

    if value_type == list:
        return ast.literal_eval(sval)

    conv_val = value_type(sval)
    return conv_val


class Settings(object):

    """
    Simple wrapper around ConfigParser, with a key type conversion available.
    """

    no_default = object()

    def __init__(self, config_path=None):
        """
        Constructor. Tries to find the main settings file and load it.

        :param config_path: Path to a config file. Useful for unittesting.
        """
        self.config = ConfigParser.ConfigParser()
        self.config_paths = []
        self.all_config_paths = []
        _source_tree_root = os.path.dirname(os.path.dirname(os.path.dirname(
            __file__)))
        # In case "examples" file exists in root, we are running from tree
        self.intree = bool(os.path.exists(os.path.join(_source_tree_root,
                                                       'examples')))
        if config_path is None:
            if 'VIRTUAL_ENV' in os.environ:
                cfg_dir = os.path.join(os.environ['VIRTUAL_ENV'], 'etc')
                user_dir = os.environ['VIRTUAL_ENV']
            else:
                cfg_dir = '/etc'
                user_dir = os.path.expanduser("~")

            _config_dir_system = os.path.join(cfg_dir, 'avocado')
            _config_dir_system_extra = os.path.join(cfg_dir, 'avocado', 'conf.d')
            _config_dir_local = os.path.join(user_dir, '.config', 'avocado')

            config_filename = 'avocado.conf'
            config_path_system = os.path.join(_config_dir_system, config_filename)
            config_path_local = os.path.join(_config_dir_local, config_filename)

            config_pkg_base = os.path.join('etc', 'avocado', config_filename)
            config_path_pkg = resource_filename('avocado', config_pkg_base)
            _config_pkg_extra = os.path.join('etc', 'avocado', 'conf.d')
            if resource_isdir('avocado', _config_pkg_extra):
                config_pkg_extra = resource_listdir('avocado',
                                                    _config_pkg_extra)
                _config_pkg_extra = resource_filename('avocado', _config_pkg_extra)
            else:
                config_pkg_extra = []
            # First try pkg/in-tree config
            self.all_config_paths.append(config_path_pkg)
            for extra_file in (os.path.join(_config_pkg_extra, _)
                               for _ in config_pkg_extra
                               if _.endswith('.conf')):
                self.all_config_paths.append(extra_file)
            # Override with system config
            self.all_config_paths.append(config_path_system)
            for extra_file in glob.glob(os.path.join(_config_dir_system_extra,
                                                     '*.conf')):
                self.all_config_paths.append(extra_file)
            # And the local config
            if not os.path.exists(config_path_local):
                try:
                    path.init_dir(_config_dir_local)
                    with open(config_path_local, 'w') as config_local_fileobj:
                        content = ("# You can use this file to override "
                                   "configuration values from '%s and %s\n"
                                   % (config_path_system,
                                      _config_dir_system_extra))
                        config_local_fileobj.write(content)
                except IOError:     # Some users can't write it (docker)
                    pass
            # Allow plugins to modify/extend the list of configs
            dispatcher = SettingsDispatcher()
            if dispatcher.extensions:
                dispatcher.map_method('adjust_settings_paths',
                                      self.all_config_paths)
            # Register user config as last to always take precedence
            self.all_config_paths.append(config_path_local)
        else:
            # Only used by unittests (the --config parses the file later)
            self.all_config_paths.append(config_path)
        self.config_paths = self.config.read(self.all_config_paths)
        if not self.config_paths:
            raise ConfigFileNotFound(self.all_config_paths)

    def process_config_path(self, path_):
        """
        Update list of config paths and process the given path
        """
        self.all_config_paths.append(path_)
        self.config_paths.extend(self.config.read(path_))

    def _handle_no_value(self, section, key, default):
        """
        What to do if key in section has no value.

        :param section: Config file section.
        :param key: Config file key, relative to section.
        :param default: Default value for key, in case it does not exist.

        :returns: Default value, if a default value was provided.

        :raises: SettingsError, in case no default was provided.
        """
        if default is self.no_default:
            msg = ("Value '%s' not found in section '%s'" %
                   (key, section))
            raise SettingsError(msg)
        else:
            return default

    def _handle_no_section(self, section, default):
        """
        What to do if section doesn't exist.

        :param section: Config file section.
        :param default: Default value for key, in case it does not exist.

        :returns: Default value, if a default value was provided.

        :raises: SettingsError, in case no default was provided.
        """
        if default is self.no_default:
            msg = "Section '%s' doesn't exist in configuration" % section
            raise SettingsError(msg)
        else:
            return default

    def get_value(self, section, key, key_type=str, default=no_default,
                  allow_blank=False):
        """
        Get value from key in a given config file section.

        :param section: Config file section.
        :type section: str
        :param key: Config file key, relative to section.
        :type key: str
        :param key_type: Type of key.
        :type key_type: either string based names representing types,
                        including `str`, `int`, `float`, `bool`,
                        `list` and `path`, or the types themselves
                        limited to :class:`str`, :class:`int`,
                        :class:`float`, :class:`bool` and
                        :class:`list`.
        :param default: Default value for the key, if none found.
        :param allow_blank: Whether an empty value for the key is allowed.

        :returns: value, if one available in the config.
                default value, if one provided.

        :raises: SettingsError, in case key is not set and no default
                 was provided.
        """
        try:
            val = self.config.get(section, key)
        except ConfigParser.NoSectionError:
            return self._handle_no_section(section, default)
        except ConfigParser.Error:
            return self._handle_no_value(section, key, default)

        if not val.strip() and not allow_blank:
            return self._handle_no_value(section, key, default)

        try:
            return convert_value_type(val, key_type)
        except Exception as details:
            raise SettingsValueError("Could not convert value %r to type %s "
                                     "(settings key %s, section %s): %s" %
                                     (val, key_type, key, section, details))


settings = Settings()
