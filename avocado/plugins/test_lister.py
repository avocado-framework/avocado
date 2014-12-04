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

import os

from avocado.core import data_dir
from avocado.core import output
from avocado.settings import settings
from avocado.utils import path
from avocado.plugins import plugin


class TestLister(plugin.Plugin):

    """
    Implements the avocado 'list' subcommand
    """

    name = 'test_lister'
    enabled = True

    def configure(self, parser):
        """
        Add the subparser for the list action.

        :param parser: Main test runner parser.
        """
        self.parser = parser.subcommands.add_parser(
            'list',
            help='List available test modules')
        super(TestLister, self).configure(self.parser)

    def run(self, args):
        """
        List available test modules.

        :param args: Command line args received from the list subparser.
        """
        view = output.View(app_args=args, use_paginator=True)
        base_test_dir = data_dir.get_test_dir()
        test_files = os.listdir(base_test_dir)
        test_dirs = []
        blength = 0
        for t in test_files:
            inspector = path.PathInspector(path=t)
            if inspector.is_python():
                clength = len((t.split('.')[0]))
                if clength > blength:
                    blength = clength
                test_dirs.append((t.split('.')[0], os.path.join(base_test_dir, t)))
        format_string = "    %-" + str(blength) + "s %s"
        view.notify(event="message", msg='Config files read (in order):')
        for cfg_path in settings.config_paths:
            view.notify(event="message", msg='    %s' % cfg_path)
        view.notify(event="minor", msg='')
        view.notify(event="message", msg='Tests dir: %s' % base_test_dir)
        if len(test_dirs) > 0:
            view.notify(event="minor", msg=format_string % ('Alias', 'Path'))
            for test_dir in test_dirs:
                view.notify(event="minor", msg=format_string % test_dir)
        else:
            view.notify(event="error", msg='No tests were found on current tests dir')
