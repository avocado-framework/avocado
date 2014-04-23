#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
# Copyright: 2014 Red Hat
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

__author__ = 'Lucas Meneghel Rodrigues <lmr@redhat.com>'

from nose.selector import Selector

from nose.plugins import Plugin
from nose.plugins.attrib import AttributeSelector
from nose.plugins.xunit import Xunit
from nose.plugins.cover import Coverage

import logging
import os
import nose
import sys


logger = logging.getLogger(__name__)


class AvocadoTestSelector(Selector):

    def wantDirectory(self, dirname):
        return True

    def wantModule(self, module):
        return True

    def wantFile(self, filename):
        if not filename.endswith('_unittest.py'):
            return False

        skip_tests = []
        if self.config.options.skip_tests:
            skip_tests = self.config.options.skip_tests.split()

        if os.path.basename(filename)[:-3] in skip_tests:
            logger.debug('Skipping test: %s' % filename)
            return False

        if self.config.options.debug:
            logger.debug('Adding %s as a valid test' % filename)

        return True


class AvocadoTestRunner(Plugin):

    enabled = True
    name = 'avocado_test_runner'

    def configure(self, options, config):
        self.result_stream = sys.stdout

        config.logStream = self.result_stream
        self.testrunner = nose.core.TextTestRunner(stream=self.result_stream,
                                                   descriptions=True,
                                                   verbosity=2,
                                                   config=config)

    def options(self, parser, env):
        parser.add_option("--avocado-skip-tests",
                          dest="skip_tests",
                          default=[],
                          help='A space separated list of tests to skip')

    def prepareTestLoader(self, loader):
        loader.selector = AvocadoTestSelector(loader.config)


def run_test():
    nose.main(addplugins=[AvocadoTestRunner(),
                          AttributeSelector(),
                          Xunit(),
                          Coverage()])


def main():
    run_test()


if __name__ == '__main__':
    main()
