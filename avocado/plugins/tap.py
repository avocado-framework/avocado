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
from avocado.core.plugin_interfaces import CLI, Init, ResultEvents
from avocado.core.settings import settings


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
                raise TypeError(f"{details}: msg='{msg}' args='{writeargs}'")
        ret = log_file.write(msg + "\n")
        return ret
    return writeln


class TAPResult(ResultEvents):

    """
    TAP output class
    """

    name = 'tap'
    description = "TAP - Test Anything Protocol results"

    def __init__(self, config):  # pylint: disable=W0613
        self.__logs = []
        self.__open_files = []
        self.config = config
        output = self.config.get('job.run.result.tap.output')
        if output == '-':
            log = LOG_UI.debug
            self.__logs.append(log)
        elif output is not None:
            log = open(output, "w", 1, encoding='utf-8')
            self.__open_files.append(log)
            self.__logs.append(file_log_factory(log))
        self.__include_logs = self.config.get('job.run.result.tap.include_logs')
        self.is_header_printed = False

    def __write(self, msg, *writeargs):
        """
        Pass through the message to all registered log functions
        """
        for log in self.__logs:
            log(msg, *writeargs)

    def __flush(self):
        """
        Force-flush the output to opened files.
        """
        for opened_file in self.__open_files:
            opened_file.flush()
            os.fsync(opened_file)

    def pre_tests(self, job):
        """
        Log the test plan
        """
        # Should we add default results.tap?
        if self.config.get('job.run.result.tap.enabled'):
            log = open(os.path.join(job.logdir, 'results.tap'), "w", 1, encoding='utf-8')
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
            self.__flush()
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
        if self.__include_logs:
            self.__write("# debug.log of %s:", name)
            with open(state.get("logfile"), "r", encoding='utf-8') as logfile_obj:
                for line in logfile_obj:
                    self.__write("#   %s", line.rstrip())

        # Then the status
        if status == "PASS":
            self.__write("ok %s %s", result.tests_run, name)
        elif status == "WARN":
            self.__write("ok %s %s  # Warnings were printed into warn log",
                         result.tests_run, name)
        elif status in ("SKIP", "CANCEL"):
            self.__write("ok %s %s  # SKIP %s", result.tests_run, name,
                         state.get("fail_reason"))
        else:
            self.__write("not ok %s %s", result.tests_run, name)
        self.__flush()

    def test_progress(self, progress=False):
        pass

    def post_tests(self, job):
        if job.interrupted_reason is not None:
            for pending_test in range(job.result.tests_run + 1, job.result.tests_total + 1):
                self.__write("ok %s # SKIP %s", pending_test, job.interrupted_reason)
            self.__flush()

        for open_file in self.__open_files:
            open_file.close()


class TAPInit(Init):

    name = 'TAP'
    description = "TAP - Test Anything Protocol - result plugin initialization"

    def initialize(self):
        section = 'job.run.result.tap'
        help_msg = ('Enable TAP result output and write it to FILE. Use '
                    '"-" to redirect to standard output.')
        settings.register_option(
            section=section,
            key='output',
            help_msg=help_msg,
            default=None)

        help_msg = ('Enables default TAP result in the job results directory. '
                    'File will be named "results.tap"')
        settings.register_option(
            section=section,
            key='enabled',
            key_type=bool,
            default=True,
            help_msg=help_msg)

        help_msg = 'Include test logs as comments in TAP output.'
        settings.register_option(
            section=section,
            key='include_logs',
            default=False,
            key_type=bool,
            help_msg=help_msg)


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

        settings.add_argparser_to_option(
            namespace='job.run.result.tap.output',
            metavar='FILE',
            action=FileOrStdoutAction,
            parser=cmd_parser,
            long_arg='--tap')

        settings.add_argparser_to_option(
            namespace='job.run.result.tap.enabled',
            parser=cmd_parser,
            long_arg='--disable-tap-job-result')

        settings.add_argparser_to_option(
            namespace='job.run.result.tap.include_logs',
            parser=cmd_parser,
            long_arg='--tap-include-logs')

    def run(self, config):
        pass
