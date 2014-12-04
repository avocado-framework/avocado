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

from avocado.plugins import plugin
from avocado.core import output
from avocado.core import data_dir
from avocado.settings import settings


class DataDirList(plugin.Plugin):

    """
    Implements the avocado 'datadir' subcommand
    """

    name = 'datadir'
    enabled = True

    def configure(self, parser):
        self.parser = parser.subcommands.add_parser(
            'datadir',
            help='List all relevant directories used by avocado')
        super(DataDirList, self).configure(self.parser)

    def run(self, args):
        view = output.View()
        view.notify(event="message", msg='Config files read (in order):')
        for cfg_path in settings.config_paths:
            view.notify(event="message", msg='    %s' % cfg_path)
        if settings.config_paths_failed:
            view.notify(event="minor", msg='')
            view.notify(event="error", msg='Config files that failed to read:')
            for cfg_path in settings.config_paths_failed:
                view.notify(event="error", msg='    %s' % cfg_path)
        view.notify(event="message", msg='')
        view.notify(event="minor", msg="Avocado replaces config dirs that can't be accessed")
        view.notify(event="minor", msg="with sensible defaults. Please edit your local config")
        view.notify(event="minor", msg="file to customize values")
        view.notify(event="message", msg='')
        view.notify(event="message", msg='Avocado Data Directories:')
        view.notify(event="minor", msg='    base dir  ' + data_dir.get_base_dir())
        view.notify(event="minor", msg='    tests dir ' + data_dir.get_test_dir())
        view.notify(event="minor", msg='    data dir  ' + data_dir.get_data_dir())
        view.notify(event="minor", msg='    logs dir  ' + data_dir.get_logs_dir())
        view.notify(event="minor", msg='    tmp dir   ' + data_dir.get_tmp_dir())
