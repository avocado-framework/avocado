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
import sys
import glob

try:
    import ConfigParser
except ImportError:
    import configparser as ConfigParser

from ..utils import path

if 'VIRTUAL_ENV' in os.environ:
    CFG_DIR = os.path.join(os.environ['VIRTUAL_ENV'], 'etc')
else:
    CFG_DIR = '/etc'

_config_dir_system = os.path.join(CFG_DIR, 'avocado')
_config_dir_system_extra = os.path.join(CFG_DIR, 'avocado', 'conf.d')
_config_dir_local = os.path.join(os.path.expanduser("~"), '.config', 'avocado')
_source_tree_root = os.path.join(sys.modules[__name__].__file__, "..", "..", "..")
_config_path_intree = os.path.join(os.path.abspath(_source_tree_root), 'etc', 'avocado')
_config_path_intree_extra = os.path.join(_config_path_intree, 'conf.d')

config_filename = 'avocado.conf'
config_path_system = os.path.join(_config_dir_system, config_filename)
config_path_local = os.path.join(_config_dir_local, config_filename)
config_path_intree = os.path.join(_config_path_intree, config_filename)


class SettingsError(Exception):

    """
    Base settings error.
    """
    pass


class SettingsValueError(SettingsError):

    """
    Error thrown when we could not convert successfully a key to a value.
    """
    pass


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

    if isinstance(value_type, str):
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

    if value_type is None:
        value_type = str

    # if length of string is zero then return None
    if len(sval) == 0:
        if value_type == str:
            return ""
        elif value_type == bool:
            return False
        elif value_type == int:
            return 0
        elif value_type == float:
            return 0.0
        elif value_type == list:
            return []
        else:
            return None

    if value_type == bool:
        if sval.lower() == "false":
            return False
        else:
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
        self.intree = False
        self.config_paths = []
        self.config_paths_failed = []
        if config_path is None:
            config_system = os.path.exists(config_path_system)
            config_system_extra = os.path.exists(_config_dir_system_extra)
            config_local = os.path.exists(config_path_local)
            config_intree = os.path.exists(config_path_intree)
            config_intree_extra = os.path.exists(_config_path_intree_extra)
            if (not config_system) and (not config_local) and (not config_intree):
                raise ConfigFileNotFound([config_path_system,
                                          config_path_local,
                                          config_path_intree])
            if config_intree:
                # In this case, respect only the intree config
                self.process_config_path(config_path_intree)
                if config_intree_extra:
                    for extra_file in glob.glob(os.path.join(_config_path_intree_extra, '*.conf')):
                        self.process_config_path(extra_file)
                self.intree = True
            else:
                # In this case, load first the global config, then the
                # local config overrides the global one
                if config_system:
                    self.process_config_path(config_path_system)
                    if config_system_extra:
                        for extra_file in glob.glob(os.path.join(_config_dir_system_extra, '*.conf')):
                            self.process_config_path(extra_file)
            if not config_local:
                path.init_dir(_config_dir_local)
                with open(config_path_local, 'w') as config_local_fileobj:
                    config_local_fileobj.write('# You can use this file to override configuration values from '
                                               '%s and %s\n' % (config_path_system, _config_dir_system_extra))
            else:
                self.process_config_path(config_path_local)
        else:
            # Unittests
            self.process_config_path(config_path)

    def process_config_path(self, pth):
        read_configs = self.config.read(pth)
        if read_configs:
            self.config_paths += read_configs
        else:
            self.config_paths_failed.append(pth)

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

    def get_value(self, section, key, key_type=str, default=no_default,
                  allow_blank=False):
        """
        Get value from key in a given config file section.

        :param section: Config file section.
        :param key: Config file key, relative to section.
        :param key_type: Type of key.
                It can be either of: str, int, float, bool, list
        :param default: Default value for the key, if none found.
        :param allow_blank: Whether an empty value for the key is allowed.

        :returns: value, if one available in the config.
                default value, if one provided.

        :raises: SettingsError, in case no default was provided.
        """
        try:
            val = self.config.get(section, key)
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
