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

from avocado.core import output
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
        view = output.View(use_paginator=(args.paginator == 'on'))
        try:
            view.notify(event="message", msg='Config files read (in order):')
            for cfg_path in settings.config_paths:
                view.notify(event="message", msg='    %s' % cfg_path)
            if settings.config_paths_failed:
                view.notify(event="minor", msg='')
                view.notify(event="error", msg='Config files that failed to read:')
                for cfg_path in settings.config_paths_failed:
                    view.notify(event="error", msg='    %s' % cfg_path)
            view.notify(event="minor", msg='')
            if not args.datadir:
                blength = 0
                for section in settings.config.sections():
                    for value in settings.config.items(section):
                        clength = len('%s.%s' % (section, value[0]))
                        if clength > blength:
                            blength = clength

                format_str = "    %-" + str(blength) + "s %s"

                view.notify(event="minor", msg=format_str % ('Section.Key', 'Value'))
                for section in settings.config.sections():
                    for value in settings.config.items(section):
                        config_key = ".".join((section, value[0]))
                        view.notify(event="minor", msg=format_str % (config_key, value[1]))
            else:
                view.notify(event="minor", msg="Avocado replaces config dirs that can't be accessed")
                view.notify(event="minor", msg="with sensible defaults. Please edit your local config")
                view.notify(event="minor", msg="file to customize values")
                view.notify(event="message", msg='')
                view.notify(event="message", msg='Avocado Data Directories:')
                view.notify(event="minor", msg='    base     ' + data_dir.get_base_dir())
                view.notify(event="minor", msg='    tests    ' + data_dir.get_test_dir())
                view.notify(event="minor", msg='    data     ' + data_dir.get_data_dir())
                view.notify(event="minor", msg='    logs     ' + data_dir.get_logs_dir())
        finally:
            view.cleanup()
