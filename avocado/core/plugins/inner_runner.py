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
# Copyright: Red Hat Inc. 2015
# Author: Cleber Rosa <cleber@redhat.com>

"""Allows the use of an intermediary (inner level) test runner."""

import os
import sys
import shlex

from . import plugin
from .. import test
from .. import output
from .. import exit_codes


class InnerRunner(plugin.Plugin):

    """
    Allows the use of an intermediary (inner level) test runner
    """

    name = 'inner_runner'
    enabled = True

    def configure(self, parser):
        inner_grp = parser.runner.add_argument_group('inner test runner support')
        inner_grp.add_argument('--inner-runner', default=None,
                               metavar='EXECUTABLE',
                               help=('Path to an specific test runner that '
                                     'allows the use of its own tests. This '
                                     'should be used for running tests that '
                                     'do not conform to Avocado\' SIMPLE test'
                                     'interface and can not run standalone'))

        chdir_help = ('Change directory before executing tests. This option '
                      'may be necessary because of requirements and/or '
                      'limitations of the inner test runner. If the inner '
                      'runner requires to be run from its own base directory,'
                      'use "runner" here. If the inner runner runs tests based'
                      ' on files and requires to be run from the directory '
                      'where those files are located, use "test" here and '
                      'specify the test directory with the option '
                      '"--inner-runner-testdir". Defaults to "%(default)s"')
        inner_grp.add_argument('--inner-runner-chdir', default='off',
                               choices=('runner', 'test', 'off'),
                               help=chdir_help)

        inner_grp.add_argument('--inner-runner-testdir', metavar='DIRECTORY',
                               default=None,
                               help=('Where test files understood by the inner'
                                     ' test runner are located in the '
                                     'filesystem. Obviously this assumes and '
                                     'only applies to inner test runners that '
                                     'run tests from files'))
        self.configured = True

    def activate(self, app_args):
        self.view = output.View(app_args=app_args)

        if hasattr(app_args, 'inner_runner'):
            if app_args.inner_runner:
                inner_runner_and_args = shlex.split(app_args.inner_runner)
                if len(inner_runner_and_args) > 1:
                    executable = inner_runner_and_args[0]
                else:
                    executable = app_args.inner_runner
                if not os.path.exists(executable):
                    msg = 'Could not find the inner runner executable "%s"' % executable
                    self.view.notify(event='error', msg=msg)
                    sys.exit(exit_codes.AVOCADO_FAIL)
                test.INNER_RUNNER = app_args.inner_runner

        if hasattr(app_args, 'inner_runner_testdir'):
            if app_args.inner_runner_testdir:
                test.INNER_RUNNER_TESTDIR = app_args.inner_runner_testdir

        if hasattr(app_args, 'inner_runner_chdir'):
            if app_args.inner_runner_chdir:
                if app_args.inner_runner_chdir == 'test':
                    if app_args.inner_runner_testdir is None:
                        msg = ('Option "--inner-runner-testdir" is mandatory '
                               'when "--inner-runner-chdir=test" is used.')
                        self.view.notify(event='error', msg=msg)
                        sys.exit(exit_codes.AVOCADO_FAIL)
                test.INNER_RUNNER_CHDIR = app_args.inner_runner_chdir
