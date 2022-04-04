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

from robot.api import TestSuite, get_model
from robot.output.logger import LOGGER

from avocado.core.nrunner.runnable import Runnable
from avocado.core.plugin_interfaces import Resolver
from avocado.core.resolver import (ReferenceResolution,
                                   ReferenceResolutionResult, check_file)

LOGGER.unregister_console_logger()


def find_tests(reference, test_suite):

    model = get_model(reference)
    data = TestSuite.from_model(model)

    test_suite[data.name] = []
    # data.tests is a list
    for test_case in data.tests:  # pylint: disable=E1133
        test_suite[data.name].append({'test_name': test_case,
                                      'test_source': data.source})

    # data.suites is a list
    for child_data in data.suites:  # pylint: disable=E1133
        find_tests(child_data, test_suite)
    return test_suite


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
        for key, value in robot_suite.items():
            for robot_test in value:
                uri = (f"{robot_test['test_source']}:"
                       f"{key}.{robot_test['test_name']}")

                runnables.append(Runnable('robot', uri=uri))

        if runnables:
            return ReferenceResolution(reference,
                                       ReferenceResolutionResult.SUCCESS,
                                       runnables)

        return ReferenceResolution(reference,
                                   ReferenceResolutionResult.NOTFOUND)
