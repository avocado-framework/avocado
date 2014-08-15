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

    def configure(self, app_parser, cmd_parser):
        parser = cmd_parser.add_parser(
            'datadir',
            help='List all relevant directories used by avocado')
        parser.set_defaults(func=self.list_data_dirs)
        self.configured = True

    def list_data_dirs(self, args):
        bcolors = output.term_support
        pipe = output.get_paginator()
        pipe.write(bcolors.header_str('Avocado Data Directories:'))
        pipe.write('\n    base dir:        ' + data_dir.get_base_dir())
        pipe.write('\n    tests dir:       ' + data_dir.get_test_dir())
        pipe.write('\n    data dir:        ' + data_dir.get_data_dir())
        pipe.write('\n    logs dir:        ' + data_dir.get_logs_dir())
        pipe.write('\n    tmp dir:         ' + data_dir.get_tmp_dir())
