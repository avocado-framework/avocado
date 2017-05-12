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

import os

from avocado.core.output import LOG_UI
from avocado.core.parser import FileOrStdoutAction
from avocado.core.plugin_interfaces import CLI, ResultEvents


def file_log_factory(log_file):
    """
    Generates a function which simulates writes to logger and outputs to file

    :param log_file: The output file
    """
    def writeln(msg, *writeargs):
        """
        Format msg and append '\n'
        """
        if writeargs:
            try:
                msg %= writeargs
            except TypeError as details:
                raise TypeError("%s: msg='%s' args='%s'" %
                                (details, msg, writeargs))
        ret = log_file.write(msg + "\n")
        log_file.flush()
        os.fsync(log_file)
        return ret
    return writeln


class TAPResult(ResultEvents):

    """
    TAP output class
    """

    name = 'tap'
    description = "TAP - Test Anything Protocol results"

    def __init__(self, args):

        def silent(msg, *writeargs):
            pass

        self.__logs = []
        self.__open_files = []
        output = getattr(args, 'tap', None)
        if output == '-':
            log = LOG_UI.debug
            self.__logs.append(log)
        elif output is not None:
            log = open(output, "w", 1)
            self.__open_files.append(log)
            self.__logs.append(file_log_factory(log))
        self.is_header_printed = False

    def __write(self, msg, *writeargs):
        """
        Pass through the message to all registered log functions
        """
        for log in self.__logs:
            log(msg, *writeargs)

    def pre_tests(self, job):
        """
        Log the test plan
        """
        # Should we add default results.tap?
        if getattr(job.args, 'tap_job_result', 'off') == 'on':
            log = open(os.path.join(job.logdir, 'results.tap'), "w", 1)
            self.__open_files.append(log)
            self.__logs.append(file_log_factory(log))

    def start_test(self, result, state):
        pass

    def end_test(self, result, state):
        """
        Log the test status and details
        """
        if not self.is_header_printed:
            self.__write("1..%d", result.tests_total)
            self.is_header_printed = True

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
        elif status == "CANCEL":
            self.__write("ok %s %s  # CANCEL %s",
                         result.tests_run, name, state.get("fail_reason"))
        else:
            self.__write("not ok %s %s", result.tests_run, name)

    def test_progress(self, progress=False):
        pass

    def post_tests(self, job):
        for open_file in self.__open_files:
            open_file.close()


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

        cmd_parser.output.add_argument('--tap-job-result', default="on",
                                       choices=("on", "off"), help="Enables "
                                       "default TAP result in the job results"
                                       " directory. File will be named "
                                       "\"results.tap\".")

    def run(self, args):
        pass
