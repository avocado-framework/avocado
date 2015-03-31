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
"""
Libexec PATHs modifier
"""

import os
import sys

from avocado.core import exit_codes, output
from avocado.plugins import plugin


class ExecPath(plugin.Plugin):

    """
    Implements the avocado 'exec-path' subcommand
    """

    name = 'exec_path'
    enabled = True
    priority = 0
    view = None

    def configure(self, parser):
        """
        Add the subparser for the exec-path action.

        :param parser: Main test runner parser.
        """
        self.parser = parser.subcommands.add_parser(
            'exec-path',
            help='Returns path to avocado bash libraries and exits.')

        super(ExecPath, self).configure(self.parser)

    def run(self, args):
        """
        Print libexec path and finish

        :param args: Command line args received from the run subparser.
        """
        self.view = output.View(app_args=args, use_paginator=False)
        if 'VIRTUAL_ENV' in os.environ:
            self.view.notify(event='minor', msg='libexec')
        elif os.path.exists('/usr/libexec/avocado'):
            self.view.notify(event='minor', msg='/usr/libexec/avocado')
        elif os.path.exists('/usr/lib/avocado'):
            self.view.notify(event='minor', msg='/usr/lib/avocado')
        else:
            for path in os.environ.get('PATH').split(':'):
                if (os.path.exists(os.path.join(path, 'avocado')) and
                    os.path.exists(os.path.join(os.path.dirname(path),
                                                'libexec'))):
                    self.view.notify(event='minor',
                                     msg=os.path.join(os.path.dirname(path),
                                                      'libexec'))
                    break
            else:
                self.view.notify(event='error',
                                 msg="Can't locate avocado libexec path")
                sys.exit(exit_codes.AVOCADO_FAIL)
        return sys.exit(exit_codes.AVOCADO_ALL_OK)
