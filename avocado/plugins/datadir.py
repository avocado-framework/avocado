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
        view.log_ui_header('Avocado Data Directories:')
        view.log('    base dir        ' + data_dir.get_base_dir())
        view.log('    tests dir       ' + data_dir.get_test_dir())
        view.log('    data dir        ' + data_dir.get_data_dir())
        view.log('    logs dir        ' + data_dir.get_logs_dir())
        view.log('    tmp dir         ' + data_dir.get_tmp_dir())
