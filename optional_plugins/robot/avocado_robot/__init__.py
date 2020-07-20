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

from robot import run
from robot.errors import DataError
from robot.model import SuiteNamePatterns
from robot.output.logger import LOGGER
from robot.parsing.model import TestData

from avocado.core import loader, output, test
from avocado.core.nrunner import Runnable
from avocado.core.plugin_interfaces import CLI, Resolver
from avocado.core.resolver import (ReferenceResolution,
                                   ReferenceResolutionResult, check_file)

LOGGER.unregister_console_logger()


class RobotTest(test.SimpleTest):

    """
    Run a Robot command as a SIMPLE test.
    """

    @property
    def filename(self):
        """
        Returns the path of the robot test suite.
        """
        return self._filename.split(':')[0]

    def test(self):
        """
        Create the Robot command and execute it.
        """
        suite_name, test_name = self._filename.split(':')[1].split('.')
        log_stdout = output.LoggingFile(loggers=[self.log], level=logging.INFO)
        log_stderr = output.LoggingFile(loggers=[self.log], level=logging.ERROR)
        result = run(self.filename,
                     suite=suite_name,
                     test=test_name,
                     outputdir=self.outputdir,
                     stdout=log_stdout,
                     stderr=log_stderr)
        if result:
            self.fail('Robot execution returned a '
                      'non-0 exit code (%s)' % result)


class NotRobotTest:

    """
    Not a robot test (for reporting purposes)
    """


def find_tests(reference, test_suite):
    data = TestData(parent=None,
                    source=reference,
                    include_suites=SuiteNamePatterns())
    test_suite[data.name] = []
    for test_case in data.testcase_table:
        test_suite[data.name].append({'test_name': test_case.name,
                                      'test_source': test_case.source})
    for child_data in data.children:
        find_tests(child_data, test_suite)
    return test_suite


class RobotLoader(loader.TestLoader):
    """
    Robot loader class
    """
    name = "robot"

    def discover(self, reference, which_tests=loader.DiscoverMode.DEFAULT):
        avocado_suite = []
        subtests_filter = None

        if reference is None:
            return []

        if ':' in reference:
            reference, _subtests_filter = reference.split(':', 1)
            subtests_filter = re.compile(_subtests_filter)
        try:
            robot_suite = find_tests(reference, test_suite={})
        except Exception as data:  # pylint: disable=W0703
            if which_tests == loader.DiscoverMode.ALL:
                return [(NotRobotTest, {"name": "%s: %s" % (reference, data)})]
            return []

        for item in robot_suite:
            for robot_test in robot_suite[item]:
                test_name = "%s:%s.%s" % (robot_test['test_source'],
                                          item,
                                          robot_test['test_name'])
                if subtests_filter and not subtests_filter.search(test_name):
                    continue
                avocado_suite.append((RobotTest, {'name': test_name,
                                                  'executable': test_name}))
        if which_tests == loader.DiscoverMode.ALL and not avocado_suite:
            return [(NotRobotTest, {"name": "%s: No robot-like tests found"
                                            % reference})]
        return avocado_suite

    @staticmethod
    def get_type_label_mapping():
        return {RobotTest: 'ROBOT',
                NotRobotTest: "!ROBOT"}

    @staticmethod
    def get_decorator_mapping():
        return {RobotTest: output.TERM_SUPPORT.healthy_str,
                NotRobotTest: output.TERM_SUPPORT.fail_header_str}


class RobotResolver(Resolver):

    name = 'robot'
    description = 'Test resolver for Robot Framework tests'

    @staticmethod
    def resolve(reference):

        # It may be possible to have Robot Framework tests in other
        # types of files such as reStructuredText (.rst), but given
        # that we're not testing that, let's restrict to files ending
        # in .robot files
        criteria_check = check_file(reference, reference, suffix='.robot')
        if criteria_check is not True:
            return criteria_check

        robot_suite = find_tests(reference, test_suite={})
        runnables = []
        for item in robot_suite:
            for robot_test in robot_suite[item]:
                uri = "%s:%s.%s" % (robot_test['test_source'],
                                    item,
                                    robot_test['test_name'])

                runnables.append(Runnable('robot', uri=uri))

        if runnables:
            return ReferenceResolution(reference,
                                       ReferenceResolutionResult.SUCCESS,
                                       runnables)

        return ReferenceResolution(reference,
                                   ReferenceResolutionResult.NOTFOUND)


class RobotCLI(CLI):

    """
    Run Robot Framework tests
    """

    name = 'robot'
    description = "Robot Framework options for 'run' subcommand"

    def configure(self, parser):
        pass

    def run(self, config):
        loader.loader.register_plugin(RobotLoader)
