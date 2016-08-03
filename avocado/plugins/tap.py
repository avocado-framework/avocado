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
from avocado.core.plugin_interfaces import CLI
from avocado.core.result import register_test_result_class, Result


class TAPResult(Result):
    """
    TAP output class
    """

    def __init__(self, job, force_output_file=None):
        def writeln(msg, *args):
            """
            Format msg and append '\n'
            """
            return self.output.write(msg % args + "\n")
        super(TAPResult, self).__init__(job)
        self.output = force_output_file or getattr(self.args, 'tap', '-')
        if self.output != '-':
            self.output = open(self.output, "w", 1)
            self.__write = writeln
        else:
            self.__write = logging.getLogger(
                "avocado.app").debug   # pylint: disable=R0204

    def start_tests(self):
        """
        Log the test plan
        """
        super(TAPResult, self).start_tests()
        self.__write("1..%s", self.tests_total)

    def end_test(self, state):
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
        self.__write("# debug.log of %s:" % name)
        if state.get('text_output'):
            for line in state['text_output'].splitlines():
                self.__write("#   " + line)
        if status in ("PASS", "WARN"):
            self.__write("ok %s %s" % (self.tests_run, name))
        elif status == "SKIP":
            self.__write("ok %s %s  # SKIP %s" % (self.tests_run, name,
                                                  state.get("fail_reason")))
        else:
            self.__write("not ok %s %s" % (self.tests_run, name))
        super(TAPResult, self).end_test(state)

    def end_tests(self):
        if self.output is not '-':
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
        if getattr(args, "tap", False):
            register_test_result_class(args, TAPResult)
