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
# Copyright: Red Hat Inc. 2017
# Authors: Amador Pahim <apahim@redhat.com>

"""
Plugin to run Robot Framework tests in Avocado
"""

import logging
import re

from avocado.core import loader
from avocado.core import output
from avocado.core import test
from avocado.core.plugin_interfaces import CLI
from robot import run
from robot.errors import DataError
from robot.parsing.model import TestData
from robot.model import SuiteNamePatterns


class RobotTest(test.SimpleTest):

    """
    Run a Robot command as a SIMPLE test.
    """

    def __init__(self,
                 name,
                 params=None,
                 base_logdir=None,
                 job=None):
        super(RobotTest, self).__init__(name, params, base_logdir, job)

    @property
    def filename(self):
        """
        Returns the path of the robot test suite.
        """
        return self.name.name.split(':')[0]

    def test(self):
        """
        Create the Robot command and execute it.
        """
        suite_name, test_name = self.name.name.split(':')[1].split('.')
        log_stdout = output.LoggingFile(logger=[self.log], level=logging.INFO)
        log_stderr = output.LoggingFile(logger=[self.log], level=logging.ERROR)
        result = run(self.filename,
                     suite=suite_name,
                     test=test_name,
                     outputdir=self.outputdir,
                     stdout=log_stdout,
                     stderr=log_stderr)
        if result:
            self.fail('Robot execution returned a '
                      'non-0 exit code (%s)' % result)


class NotRobotTest(object):

    """
    Not a robot test (for reporting purposes)
    """


class RobotLoader(loader.TestLoader):
    """
    Robot loader class
    """
    name = "robot"

    def __init__(self, args, extra_params):
        super(RobotLoader, self).__init__(args, extra_params)

    def discover(self, url, which_tests=loader.DEFAULT):
        avocado_suite = []
        subtests_filter = None

        if url is None:
            return []

        if ':' in url:
            url, _subtests_filter = url.split(':', 1)
            subtests_filter = re.compile(_subtests_filter)
        try:
            test_data = TestData(parent=None,
                                 source=url,
                                 include_suites=SuiteNamePatterns())
            robot_suite = self._find_tests(test_data, test_suite={})
        except Exception as data:
            if which_tests == loader.ALL:
                return [(NotRobotTest, {"name": "%s: %s" % (url, data)})]
            return []

        for item in robot_suite:
            for robot_test in robot_suite[item]:
                test_name = "%s:%s.%s" % (robot_test['test_source'],
                                          item,
                                          robot_test['test_name'])
                if subtests_filter and not subtests_filter.search(test_name):
                    continue
                avocado_suite.append((RobotTest, {'name': test_name}))
        if which_tests is loader.ALL and not avocado_suite:
            return [(NotRobotTest, {"name": "%s: No robot-like tests found"
                                    % url})]
        return avocado_suite

    def _find_tests(self, data, test_suite):
        test_suite[data.name] = []
        for test_case in data.testcase_table:
            test_suite[data.name].append({'test_name': test_case.name,
                                          'test_source': test_case.source})
        for child_data in data.children:
            self._find_tests(child_data, test_suite)
        return test_suite

    @staticmethod
    def get_type_label_mapping():
        return {RobotTest: 'ROBOT',
                NotRobotTest: "!ROBOT"}

    @staticmethod
    def get_decorator_mapping():
        return {RobotTest: output.TERM_SUPPORT.healthy_str,
                NotRobotTest: output.TERM_SUPPORT.fail_header_str}


class RobotCLI(CLI):

    """
    Run Robot Framework tests
    """

    name = 'robot'
    description = "Robot Framework options for 'run' subcommand"

    def configure(self, parser):
        pass

    def run(self, args):
        loader.loader.register_plugin(RobotLoader)
