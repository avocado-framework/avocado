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

import logging

from avocado.core import data_dir
from avocado.core.settings import settings

from .base import CLICmd


class Config(CLICmd):

    """
    Implements the avocado 'config' subcommand
    """

    name = 'config'
    description = 'Shows avocado config keys'

    def configure(self, parser):
        parser = super(Config, self).configure(parser)
        parser.add_argument('--datadir', action='store_true', default=False,
                            help='Shows the data directories currently being used by avocado')
        parser.add_argument('--paginator',
                            choices=('on', 'off'), default='on',
                            help='Turn the paginator on/off. '
                            'Current: %(default)s')

    def run(self, args):
        log = logging.getLogger("avocado.app")
        log.info('Config files read (in order):')
        for cfg_path in settings.config_paths:
            log.debug('    %s' % cfg_path)
        if settings.config_paths_failed:
            log.error('\nConfig files that failed to read:')
            for cfg_path in settings.config_paths_failed:
                log.error('    %s' % cfg_path)
        log.debug("")
        if not args.datadir:
            blength = 0
            for section in settings.config.sections():
                for value in settings.config.items(section):
                    clength = len('%s.%s' % (section, value[0]))
                    if clength > blength:
                        blength = clength

            format_str = "    %-" + str(blength) + "s %s"

            log.debug(format_str, 'Section.Key', 'Value')
            for section in settings.config.sections():
                for value in settings.config.items(section):
                    config_key = ".".join((section, value[0]))
                    log.debug(format_str, config_key, value[1])
        else:
            log.debug("Avocado replaces config dirs that can't be accessed")
            log.debug("with sensible defaults. Please edit your local config")
            log.debug("file to customize values")
            log.debug('')
            log.info('Avocado Data Directories:')
            log.debug('    base     ' + data_dir.get_base_dir())
            log.debug('    tests    ' + data_dir.get_test_dir())
            log.debug('    data     ' + data_dir.get_data_dir())
            log.debug('    logs     ' + data_dir.get_logs_dir())
