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
# Copyright: Red Hat, Inc. 2016
# Author: Lukas Doktor <ldoktor@redhat.com>
"""
TAP output module.
"""

import logging

from avocado.core.parser import FileOrStdoutAction
from avocado.core.plugin_interfaces import CLI, ResultEvents


class TAPResult(ResultEvents):

    """
    TAP output class
    """

    name = 'tap'
    description = "TAP - Test Anything Protocol results"

    def __init__(self, args):
        def writeln(msg, *writeargs):
            """
            Format msg and append '\n'
            """
            if writeargs:
                try:
                    msg %= writeargs
                except TypeError, details:
                    raise TypeError("%s: msg='%s' args='%s'" %
                                    (details, msg, writeargs))
            return self.output.write(msg + "\n")

        def silent(msg, *writeargs):
            pass

        self.output = getattr(args, 'tap', None)
        if self.output is None:
            self.__write = silent
        elif self.output == '-':
            self.__write = logging.getLogger(
                "avocado.app").debug   # pylint: disable=R0204
        else:
            self.output = open(self.output, "w", 1)
            self.__write = writeln

    def pre_tests(self, job):
        """
        Log the test plan
        """
        tests = len(job.test_suite)
        if tests > 0:
            self.__write("1..%d", tests)

    def start_test(self, result, state):
        pass

    def end_test(self, result, state):
        """
        Log the test status and details
        """
        status = state.get("status", "ERROR")
        name = state.get("name")
        if not name:
            name = "Unknown"
        else:
            name = name.name + name.str_variant
            name.replace('#', '_')  # Name must not contain #
            if name[0].isdigit():   # Name must not start with digit
                name = "_" + name
        # First log the system output
        self.__write("# debug.log of %s:", name)
        if state.get('text_output'):
            for line in state['text_output'].splitlines():
                self.__write("#   %s", line)
        if status in ("PASS", "WARN"):
            self.__write("ok %s %s", result.tests_run, name)
        elif status == "SKIP":
            self.__write("ok %s %s  # SKIP %s", result.tests_run, name, state.get("fail_reason"))
        else:
            self.__write("not ok %s %s", result.tests_run, name)

    def test_progress(self, progress=False):
        pass

    def post_tests(self, job):
        if self.output not in (None, '-'):
            self.output.close()


class TAP(CLI):

    """
    TAP Test Anything Protocol output avocado plugin
    """

    name = 'TAP'
    description = "TAP - Test Anything Protocol results"

    def configure(self, parser):
        cmd_parser = parser.subcommands.choices.get('run', None)
        if cmd_parser is None:
            return

        cmd_parser.output.add_argument('--tap', type=str, metavar='FILE',
                                       action=FileOrStdoutAction,
                                       help="Enable TAP result output and "
                                       "write it to FILE. Use '-' to redirect "
                                       "to the standard output.")

    def run(self, args):
        pass
