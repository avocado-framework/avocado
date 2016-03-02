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
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>
"""
HTML output module.
"""

import logging
import sys

from avocado.core import exit_codes
from avocado.core.html import HTMLTestResult
from avocado.core.result import register_test_result_class

from .base import CLI


class HTML(CLI):

    """
    HTML job report
    """

    name = 'htmlresult'
    description = "HTML job report options for 'run' subcommand"

    def configure(self, parser):
        run_subcommand_parser = parser.subcommands.choices.get('run', None)
        if run_subcommand_parser is None:
            return

        run_subcommand_parser.output.add_argument(
            '--html', type=str,
            dest='html_output', metavar='FILE',
            help=('Enable HTML output to the FILE where the result should be '
                  'written. The value - (output to stdout) is not supported '
                  'since not all HTML resources can be embedded into a '
                  'single file (page resources will be copied to the '
                  'output file dir)'))
        run_subcommand_parser.output.add_argument(
            '--open-browser',
            dest='open_browser',
            action='store_true',
            default=False,
            help='Open the generated report on your preferred browser. '
                 'This works even if --html was not explicitly passed, '
                 'since an HTML report is always generated on the job '
                 'results dir. Current: %s' % False)

    def run(self, args):
        if 'html_output' in args and args.html_output == '-':
            log = logging.getLogger("avocado.app")
            log.error('HTML to stdout not supported (not all HTML resources '
                      'can be embedded on a single file)')
            sys.exit(exit_codes.AVOCADO_JOB_FAIL)

        if 'html_output' in args and args.html_output is not None:
            register_test_result_class(args, HTMLTestResult)
