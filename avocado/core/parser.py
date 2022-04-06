# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2013-2014
# Author: Ruda Moura <rmoura@redhat.com>

"""
Avocado application command line parsing.
"""

import argparse
from configparser import ConfigParser, NoOptionError
from glob import glob

from avocado.core import exit_codes
from avocado.core.nrunner.runnable import Runnable
from avocado.core.output import LOG_UI
from avocado.core.resolver import (ReferenceResolution,
                                   ReferenceResolutionResult)
from avocado.core.settings import ConfigFileNotFound, SettingsError, settings
from avocado.core.version import VERSION

PROG = 'avocado'
DESCRIPTION = 'Avocado Test Runner'


class ArgumentParser(argparse.ArgumentParser):

    """
    Class to override argparse functions
    """

    def error(self, message):
        LOG_UI.debug(self.format_help())
        LOG_UI.error("%s: error: %s", self.prog, message)
        if "unrecognized arguments" in message:
            LOG_UI.warning("Perhaps a plugin is missing; run 'avocado"
                           " plugins' to list the installed ones")
        self.exit(exit_codes.AVOCADO_FAIL)

    def _get_option_tuples(self, option_string):
        return []


class FileOrStdoutAction(argparse.Action):

    """
    Controls claiming the right to write to the application standard output
    """

    def __call__(self, parser, namespace, values, option_string=None):
        if values == '-':
            stdout_claimed_by = getattr(namespace, 'stdout_claimed_by', None)
            if stdout_claimed_by is not None:
                msg = (f'Options {stdout_claimed_by} {option_string} '
                       f'are trying to use stdout simultaneously.'
                       f' Please set at least one of them to a file to avoid '
                       f'conflicts')
                raise argparse.ArgumentError(self, msg)
            else:
                setattr(namespace, 'stdout_claimed_by', option_string)
        setattr(namespace, self.dest, values)


class Parser:

    """
    Class to Parse the command line arguments.
    """

    def __init__(self):
        self.args = argparse.Namespace()
        self.config = {}
        self.subcommands = None
        self.application = ArgumentParser(prog=PROG,
                                          add_help=False,  # see parent parsing
                                          description=DESCRIPTION)
        self.application.add_argument('-v', '--version', action='version',
                                      version=f'Avocado {VERSION}')
        self.application.add_argument('--config', metavar='CONFIG_FILE',
                                      nargs='?',
                                      help='Use custom configuration from a file')

        help_msg = 'Turn the paginator on. Useful when output is too long.'
        settings.register_option(section='core',
                                 key='paginator',
                                 help_msg=help_msg,
                                 key_type=bool,
                                 default=False,
                                 action='store_true',
                                 parser=self.application,
                                 long_arg='--enable-paginator')

        help_msg = ('Some commands can produce more information. This option '
                    'will enable the verbosity when applicable.')
        settings.register_option(section='core',
                                 key='verbose',
                                 help_msg=help_msg,
                                 default=False,
                                 key_type=bool,
                                 parser=self.application,
                                 long_arg='--verbose',
                                 short_arg='-V')

        settings.add_argparser_to_option(namespace='core.show',
                                         parser=self.application,
                                         long_arg='--show')

    def start(self):
        """
        Start to parsing arguments.

        At the end of this method, the support for subparsers is activated.
        Side effect: update attribute `args` (the namespace).
        """
        self.args, _ = self.application.parse_known_args()

        # Load settings from file, if user provides one
        if self.args.config is not None:
            settings.process_config_path(self.args.config)

        # Use parent parsing to avoid breaking the output of --help option
        self.application = ArgumentParser(prog=PROG,
                                          description=DESCRIPTION,
                                          parents=[self.application])

        # Subparsers where Avocado subcommands are plugged
        self.subcommands = self.application.add_subparsers(
            title='subcommands',
            description='valid subcommands',
            help='subcommand help',
            dest='subcommand')
        # On Python 2, required doesn't make a difference because a
        # subparser is considered an unconsumed positional arguments,
        # and not providing one will error with a "too few arguments"
        # message.  On Python 3, required arguments are used instead.
        # Unfortunately, there's no way to pass this as an option when
        # constructing the sub parsers, but it is possible to set that
        # option afterwards.
        self.subcommands.required = True

    def finish(self):
        """
        Finish the process of parsing arguments.

        Side effect: set the final value on attribute `config`.
        """
        args, extra = self.application.parse_known_args(namespace=self.args)
        if extra:
            msg = f"unrecognized arguments: {' '.join(extra)}"
            for sub in self.application._subparsers._actions:  # pylint: disable=W0212
                if sub.dest == 'subcommand':
                    sub.choices[self.args.subcommand].error(msg)

            self.application.error(msg)
        # from this point on, config is a dictionary based on a argparse.Namespace
        self.config = vars(args)


class HintParser:
    def __init__(self, filename):
        self.filename = filename
        self.config = None
        self.hints = []
        self._parse()

    def _get_args_from_section(self, section):
        try:
            args = self.config.get(section, 'args')
            if args == '$testpath':
                return [args]
            return args.split(',')
        except NoOptionError:
            return []

    def _get_kwargs_from_section(self, section):
        result = {}
        kwargs = self.config.get(section, 'kwargs', fallback='')
        for kwarg in kwargs.split(','):
            if kwarg == '':
                continue
            key, value = kwarg.split('=')
            result[key] = value
        return result

    def _get_resolutions_by_kind(self, kind, paths):
        self.validate_kind_section(kind)

        resolutions = []
        success = ReferenceResolutionResult.SUCCESS

        config = {'uri': self._get_uri_from_section(kind),
                  'args': self._get_args_from_section(kind),
                  'kwargs': self._get_kwargs_from_section(kind)}
        for path in paths:
            uri = config.get('uri')
            args = config.get('args')
            kwargs = config.get('kwargs')
            if uri == '$testpath':
                uri = path
            if '$testpath' in args:
                args = [item.replace('$testpath', path) for item in args]
            if '$testpath' in kwargs.values():
                kwargs = {k: v.replace('$testpath', path)
                          for k, v in kwargs.items()}
            runnable = Runnable(kind, uri, *args, **kwargs)
            resolutions.append(ReferenceResolution(reference=path,
                                                   result=success,
                                                   resolutions=[runnable],
                                                   origin=path))
        return resolutions

    def _get_uri_from_section(self, section):
        return self.config.get(section, 'uri')

    def _parse(self):
        self.config = ConfigParser()
        config_paths = self.config.read(self.filename)
        if not config_paths:
            raise ConfigFileNotFound(self.filename)

    def get_resolutions(self):
        """Return a list of resolutions based on the file definitions."""
        resolutions = []
        for kind in self.config['kinds']:
            files = self.config.get('kinds', kind)
            resolutions.extend(self._get_resolutions_by_kind(kind,
                                                             glob(files)))
        return resolutions

    def validate_kind_section(self, kind):
        """Validates a specific "kind section".

        This method will raise a `settings.SettingsError` if any problem is
        found on the file.

        :param kind: a string with the specific section.
        """
        if kind not in self.config:
            msg = 'Section {} is not defined. Please check your hint file.'
            raise SettingsError(msg.format(kind))

        uri = self._get_uri_from_section(kind)
        if uri is None:
            msg = f"uri needs to be defined inside {kind}"
            raise SettingsError(msg)
