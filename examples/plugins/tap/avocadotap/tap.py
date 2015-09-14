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


import os
import tempfile

from avocado.plugins.base import CLIRunBase, JobResultBase


TAP_VERSION = None


class TAPRun(CLIRunBase):

    def configure(self, parser):
        parser.runner.add_argument('--tap-version', action='store',
                                   default='12', metavar='VERSION',
                                   help='TAP version to output')

    def activate(self, args):
        global TAP_VERSION
        if args.tap_version:
            TAP_VERSION = args.tap_version

    def before_run(self, args):
        pass

    def after_run(self, args):
        pass


class TAPResult(JobResultBase):

    DEFAULT_OUTPUT_FILENAME = 'results.tap'

    def __init__(self, **kwargs):
        self.count = 0
        self.current = 0

    def start(self, output):
        if os.path.isdir(output):
            output = os.path.join(output,
                                  self.DEFAULT_OUTPUT_FILENAME)
        self.output = output

    def start_tests(self, count):
        """
        Prints the plan, in TAP lingo
        """
        self.count = count
        self.current = 1
        with open(self.output, 'w') as tap:
            tap.write('%i..%i\n' % (self.current, self.count))

    def end_tests(self):
        pass

    def end(self):
        # TAP doesn't require any signalling when the whole job is finished
        pass

    def update_test(self, **kwargs):
        if 'status' in kwargs:
            status = kwargs['status']
            if status == 'PASS':
                with open(self.output, 'a') as tap:
                    tap.write('ok %i\n' % self.current)
            elif status in ('FAIL', 'ERROR'):
                with open(self.output, 'a') as tap:
                    tap.write('not ok %i\n' % self.current)

        if status in ('PASS', 'FAIL', 'ERROR'):
            self.current += 1
