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

"""
JSON output module.
"""

from avocado.core.jsonresult import JSONTestResult
from avocado.core.result import register_test_result_class

from .base import CLI


class JSON(CLI):

    """
    JSON output
    """

    name = 'json'
    description = "JSON output options for 'run' command"

    def configure(self, parser):
        run_subcommand_parser = parser.subcommands.choices.get('run', None)
        if run_subcommand_parser is None:
            return

        run_subcommand_parser.output.add_argument(
            '--json', type=str,
            dest='json_output', metavar='FILE',
            help='Enable JSON result format and write it to FILE. '
                 "Use '-' to redirect to the standard output.")

    def run(self, args):
        if 'json_output' in args and args.json_output is not None:
            register_test_result_class(args, JSONTestResult)
