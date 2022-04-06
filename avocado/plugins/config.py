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
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>
#         Beraldo Leal <bleal@redhat.com>

import textwrap

from avocado.core import data_dir
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLICmd
from avocado.core.settings import settings


class Config(CLICmd):

    """
    Implements the avocado 'config' subcommand
    """

    name = 'config'
    description = 'Shows avocado config keys'

    def configure(self, parser):
        parser = super().configure(parser)
        help_msg = ('Shows the data directories currently being used by '
                    'Avocado')
        settings.register_option(section='config',
                                 key='datadir',
                                 key_type=bool,
                                 default=False,
                                 help_msg=help_msg,
                                 parser=parser,
                                 long_arg='--datadir')

        subcommands = parser.add_subparsers(dest='config_subcommand',
                                            metavar='sub-command')

        help_msg = 'Show a configuration reference with all registered options'
        subcommands.add_parser('reference', help=help_msg)

    def run(self, config):
        if config.get('config_subcommand') == 'reference':
            self.handle_reference(LOG_UI.debug)
        else:
            self.handle_default()

    @staticmethod
    def handle_reference(print_function):
        full = settings.as_full_dict()
        for namespace, option in full.items():
            print_function(namespace)
            print_function("~" * len(namespace))
            help_lines = textwrap.wrap(option.get('help'))
            for line in help_lines:
                print_function(line)
            print_function("")
            print_function(f"* Default: {option.get('default')}")
            print_function(f"* Type: {option.get('type')}")
            print_function("")

    @staticmethod
    def handle_default():
        LOG_UI.info("Config files read (in order, '*' means the file exists "
                    "and had been read):")

        # Getting from settings because is already sorted
        config = settings.as_dict()
        for cfg_path in settings.all_config_paths:
            if cfg_path in settings.config_paths:
                LOG_UI.debug('    * %s', cfg_path)
            else:
                LOG_UI.debug('      %s', cfg_path)
        LOG_UI.debug("")
        if not config.get('config.datadir'):
            blength = 0
            for namespace, value in config.items():
                clength = len(namespace)
                if clength > blength:
                    blength = clength

            format_str = "    %-" + str(blength) + "s %s"

            LOG_UI.debug(format_str, 'Section.Key', 'Value')
            for namespace, value in config.items():
                LOG_UI.debug(format_str, namespace, value)
        else:
            cache_dirs = config.get('datadir.paths.cache_dirs')
            LOG_UI.debug("Avocado replaces config dirs that can't be accessed")
            LOG_UI.debug("with sensible defaults. Please edit your local config")
            LOG_UI.debug("file to customize values")
            LOG_UI.debug('')
            LOG_UI.info('Avocado Data Directories:')
            LOG_UI.debug('   base    %s', config.get('datadir.paths.base_dir'))
            LOG_UI.debug('   tests   %s', data_dir.get_test_dir())
            LOG_UI.debug('   data    %s', config.get('datadir.paths.data_dir'))
            LOG_UI.debug('   logs    %s', config.get('datadir.paths.logs_dir'))
            LOG_UI.debug('   cache   %s', ", ".join(cache_dirs))
