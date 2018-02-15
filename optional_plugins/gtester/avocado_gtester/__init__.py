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
# Copyright: Red Hat Inc. 2018
# Authors: Amador Pahim <apahim@redhat.com>

"""
Plugin to run GLib Test Framework tests in Avocado
"""

import re

from avocado.utils import path as utils_path
from avocado.utils import process

from avocado.core import exceptions
from avocado.core import loader
from avocado.core import output
from avocado.core import test
from avocado.core.plugin_interfaces import CLI


try:
    _GTESTER_BIN = utils_path.find_command('gtester')
except utils_path.CmdNotFoundError:
    _GTESTER_BIN = None


class GtesterTest(test.SimpleTest):

    """
    Run a Gtester command as a SIMPLE test.
    """

    def __init__(self, name, params=None, base_logdir=None, job=None):
        super(GtesterTest, self).__init__(name, params, base_logdir, job)

    @property
    def filename(self):
        """
        Returns the path of the gtester test suite.
        """
        return self.name.name.split(':')[0]

    def test(self):
        """
        Create the Gtester command and execute it.
        """

        if _GTESTER_BIN is None:
            raise exceptions.TestError("gtester binary not found")

        test_name = self.name.name.split(':')[1]
        cmd = '%s -p=%s %s' % (_GTESTER_BIN, test_name, self.filename)
        result = process.run(cmd, ignore_status=True)
        if result.exit_status != 0:
            self.fail('Gtester Test execution returned a '
                      'non-0 exit code (%s)' % result)


class NotGtesterTest(object):

    """
    Not a gtester test (for reporting purposes)
    """


class GtesterLoader(loader.TestLoader):
    """
    Gtester loader class
    """
    name = "gtester"

    def __init__(self, args, extra_params):
        super(GtesterLoader, self).__init__(args, extra_params)

    def discover(self, reference, which_tests=loader.DEFAULT):
        if _GTESTER_BIN is None:
            raise exceptions.TestError("gtester binary not found")

        avocado_suite = []
        subtests_filter = None

        if reference is None:
            return []

        if ':' in reference:
            reference, _subtests_filter = reference.split(':', 1)
            subtests_filter = re.compile(_subtests_filter)
        try:
            cmd = '%s --quiet -l %s' % (_GTESTER_BIN, reference)
            result = process.run(cmd)
        except Exception as details:
            if which_tests == loader.ALL:
                return [(NotGtesterTest, {"name": "%s: %s" % (reference, details)})]
            return []

        for test in result.stdout.splitlines():
            test_name = "%s:%s" % (reference, test)
            try:
                # Avoiding duplicates
                # FIXME: https://bugzilla.gnome.org/show_bug.cgi?id=793749
                for item in avocado_suite:
                    if item[1]['name'] == test_name:
                        raise ValueError

                if subtests_filter and not subtests_filter.search(test_name):
                    continue
                avocado_suite.append((GtesterTest, {'name': test_name}))
            except ValueError:
                continue

        if which_tests is loader.ALL and not avocado_suite:
            return [(NotGtesterTest,
                     {"name": "%s: No gtester-like tests found" % reference})]
        return avocado_suite

    @staticmethod
    def get_type_label_mapping():
        return {GtesterTest: 'GTESTER',
                NotGtesterTest: "!GTESTER"}

    @staticmethod
    def get_decorator_mapping():
        return {GtesterTest: output.TERM_SUPPORT.healthy_str,
                NotGtesterTest: output.TERM_SUPPORT.fail_header_str}


class GtesterCLI(CLI):

    """
    Run Gtester Test Framework tests
    """

    name = 'gtester'
    description = "Gtester Framework options for 'run' subcommand"

    def configure(self, parser):
        pass

    def run(self, args):
        loader.loader.register_plugin(GtesterLoader)
