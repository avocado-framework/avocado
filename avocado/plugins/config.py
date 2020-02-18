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

import warnings

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
        parser = super(Config, self).configure(parser)
        parser.add_argument('--datadir', action='store_true', default=False,
                            help='Shows the data directories currently being used by avocado')
        parser.add_argument('--paginator',
                            choices=('on', 'off'), default='on',
                            help='Turn the paginator on/off. Will be '
                                 'deprecated soon. Current: %(default)s')

    def run(self, config):
        LOG_UI.info("Config files read (in order, '*' means the file exists "
                    "and had been read):")

        warnings.warn("avocado config --paginator will be deprecated soon: "
                      "avocado --paginator config will be used instead.",
                      FutureWarning)

        for cfg_path in settings.all_config_paths:
            if cfg_path in settings.config_paths:
                LOG_UI.debug('    * %s', cfg_path)
            else:
                LOG_UI.debug('      %s', cfg_path)
        LOG_UI.debug("")
        if not config.get("datadir"):
            blength = 0
            for section in settings.config.sections():
                for value in settings.config.items(section):
                    clength = len('%s.%s' % (section, value[0]))
                    if clength > blength:
                        blength = clength

            format_str = "    %-" + str(blength) + "s %s"

            LOG_UI.debug(format_str, 'Section.Key', 'Value')
            for section in settings.config.sections():
                for value in settings.config.items(section):
                    config_key = ".".join((section, value[0]))
                    LOG_UI.debug(format_str, config_key, value[1])
        else:
            LOG_UI.debug("Avocado replaces config dirs that can't be accessed")
            LOG_UI.debug("with sensible defaults. Please edit your local config")
            LOG_UI.debug("file to customize values")
            LOG_UI.debug('')
            LOG_UI.info('Avocado Data Directories:')
            LOG_UI.debug('    base     %s', data_dir.get_base_dir())
            LOG_UI.debug('    tests    %s', data_dir.get_test_dir())
            LOG_UI.debug('    data     %s', data_dir.get_data_dir())
            LOG_UI.debug('    logs     %s', data_dir.get_logs_dir())
            LOG_UI.debug('    cache    %s', ", ".join(data_dir.get_cache_dirs()))
