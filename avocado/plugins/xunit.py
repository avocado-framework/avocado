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
# Copyright: Red Hat Inc. 2014
# Author: Ruda Moura <rmoura@redhat.com>

"""xUnit module."""

from avocado.core.result import register_test_result_class
from avocado.core.xunit import xUnitTestResult
from .base import CLI


class XUnit(CLI):

    """
    xUnit output
    """

    name = 'xunit'
    description = 'xUnit output options'

    def configure(self, parser):
        run_subcommand_parser = parser.subcommands.choices.get('run', None)
        if run_subcommand_parser is None:
            return

        self.parser = parser
        run_subcommand_parser.output.add_argument(
            '--xunit', type=str, dest='xunit_output', metavar='FILE',
            help=('Enable xUnit result format and write it to FILE. '
                  "Use '-' to redirect to the standard output."))

    def run(self, args):
        if 'xunit_output' in args and args.xunit_output is not None:
            register_test_result_class(args, xUnitTestResult)
