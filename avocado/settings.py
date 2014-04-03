"""
Reads the avocado settings from a .ini file (from python ConfigParser).
"""
import ConfigParser
import os
import sys


config_filename = 'settings.ini'
_config_dir_system = os.path.join('/etc', 'avocado')
config_path_system = os.path.join(_config_dir_system, config_filename)
_config_dir_local = os.path.join(os.path.expanduser("~"), '.config', 'avocado')
config_path_local = os.path.join(_config_dir_local, config_filename)
_source_tree_root = os.path.join(sys.modules[__name__].__file__, "..", "..")
_config_path_intree = os.path.join(os.path.abspath(_source_tree_root), 'etc')
config_path_intree = os.path.join(_config_path_intree, config_filename)


class SettingsError(Exception):
    pass


class SettingsValueError(SettingsError):
    pass


class ConfigFileNotFound(SettingsError):

    def __init__(self, path_list):
        super(ConfigFileNotFound, self).__init__()
        self.path_list = path_list

    def __str__(self):
        return ("Could not find the avocado config file after looking in: %s" %
                self.path_list)


def convert_value_type(key, section, value, value_type):
    """
    Convert a string to another data type.
    """
    # strip off leading and trailing white space
    sval = value.strip()

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
        # Split the string using ',' and return a list
        return [val.strip() for val in sval.split(',')]

    try:
        conv_val = value_type(sval)
        return conv_val
    except Exception:
        msg = ("Could not convert %s value %r in section %s to type %s" %
              (key, sval, section, value_type))
        raise SettingsValueError(msg)


class Settings(object):

    no_default = object()

    def __init__(self):
        self.config = ConfigParser.ConfigParser()
        config_system = os.path.exists(config_path_system)
        config_local = os.path.exists(config_path_local)
        config_intree = os.path.exists(config_path_intree)
        self.intree = False
        if not config_local and not config_system:
            if not config_intree:
                raise ConfigFileNotFound([config_path_system,
                                          config_path_local,
                                          config_path_intree])
            self.config_path = config_path_intree
            self.intree = True
        else:
            if config_local:
                self.config_path = config_path_local
            else:
                self.config_path = config_path_system
        self.parse_file()

    def parse_file(self):
        self.config.read(self.config_path)

    def _handle_no_value(self, section, key, default):
        if default is self.no_default:
            msg = ("Value '%s' not found in section '%s'" %
                   (key, section))
            raise SettingsError(msg)
        else:
            return default

    def get_value(self, section, key, key_type=str, default=no_default,
                  allow_blank=False):
        try:
            val = self.config.get(section, key)
        except ConfigParser.Error:
            return self._handle_no_value(section, key, default)

        if not val.strip() and not allow_blank:
            return self._handle_no_value(section, key, default)

        return convert_value_type(key, section, val, key_type)


settings = Settings()
