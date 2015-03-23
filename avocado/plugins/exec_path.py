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
Libexec PATHs modifier
"""

import os
import sys

from avocado.core import exit_codes
from avocado.plugins import plugin


class TestRunner(plugin.Plugin):

    """
    Implements the avocado 'exec-path' subcommand
    """

    name = 'test_runner'
    enabled = True
    priority = 0

    def configure(self, parser):
        """
        Add the subparser for the exec-path action.

        :param parser: Main test runner parser.
        """
        self.parser = parser.subcommands.add_parser(
            'exec-path',
            help='Returns path to avocado bash libraries and exits.')

        super(TestRunner, self).configure(self.parser)
        # Export the test runner parser back to the main parser
        parser.runner = self.parser

    def run(self, args):
        """
        Print libexec path and finish

        :param args: Command line args received from the run subparser.
        """
        if 'VIRTUAL_ENV' in os.environ:
            sys.stdout.write(os.path.join("libexec"))
        elif os.path.exists('/usr/libexec/avocado'):
            sys.stdout.write('/usr/libexec/avocado')
        elif os.path.exists('/usr/lib/avocado'):
            sys.stdout.write('/usr/lib/avocado')
        else:
            sys.stdout.write("Can't locate avocado libexec path")
            sys.exit(exit_codes.AVOCADO_FAIL)
        return sys.exit(exit_codes.AVOCADO_ALL_OK)
