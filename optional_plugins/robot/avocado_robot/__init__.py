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
from robot.api import TestSuite, get_model
from robot.errors import DataError
from robot.output.logger import LOGGER

from avocado.core import output, test
from avocado.core.nrunner import Runnable
from avocado.core.plugin_interfaces import CLI, Resolver
from avocado.core.resolver import (ReferenceResolution,
                                   ReferenceResolutionResult, check_file)

LOGGER.unregister_console_logger()


def find_tests(reference, test_suite):

    model = get_model(reference)
    data = TestSuite.from_model(model)

    test_suite[data.name] = []
    for test_case in data.tests:
        test_suite[data.name].append({'test_name': test_case,
                                      'test_source': data.source})
    for child_data in data.suites:
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
