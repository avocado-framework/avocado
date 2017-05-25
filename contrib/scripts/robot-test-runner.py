#!/usr/bin/python
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; specifically version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: 2017 Red Hat, Inc.
# Author: Amador Pahim <apahim@redhat.com>

#
# This script expects an argument in the following format:
#   "<path_to_robot_suite>:<suite name>:<test name>"
#
# Example:
#   "/tmp/WebDemo/login_tests/:Gherkin Login:Valid Login"
#
# Usage:
#   ./robot-test-runner.py "<path_to_robot_suite>:<suite name>:<test name>"
#
# Example:
#   ./robot-test-runner.py "/tmp/WebDemo/login_tests/:Gherkin Login:Valid Login"
#
# The argument will then be parsed and the robot command will be
# executed to run the test, exiting with the same exit code returned by
# the robot command.


import os
import subprocess
import sys


suite_dir, suite_name, test_name = sys.argv[1].split(':')

try:
    robot_bin = subprocess.check_output(['which', 'robot']).strip()
except subprocess.CalledProcessError as details:
    sys.exit(details.returncode)

cmd = [robot_bin]
cmd.extend(['--log', 'NONE'])
cmd.extend(['--output', 'NONE'])
cmd.extend(['--report', 'NONE'])
cmd.extend(['--suite', suite_name])
cmd.extend(['--test', test_name])
cmd.append(os.path.expanduser(suite_dir))

sys.exit(subprocess.call(cmd))
