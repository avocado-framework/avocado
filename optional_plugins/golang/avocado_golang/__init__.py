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
Plugin to run Golang tests in Avocado
"""

import fnmatch
import logging
import os
import re

from avocado.core import loader
from avocado.core import output
from avocado.core import test
from avocado.core.plugin_interfaces import CLI
from avocado.utils import path as utils_path
from avocado.utils import process


class GolangTest(test.SimpleTest):

    """
    Run a Golang Test command as a SIMPLE test.
    """

    def __init__(self,
                 name,
                 params=None,
                 base_logdir=None,
                 job=None,
                 subtest=None):
        super(GolangTest, self).__init__(name, params, base_logdir, job)
        self.subtest = subtest

    @property
    def filename(self):
        """
        Returns the path of the golang test suite.
        """
        return self.name.name.split(':')[0]

    def test(self):
        """
        Create the Golang command and execute it.
        """
        test_name = '%s$' % self.name.name.split(':')[1]
        if self.subtest is not None:
            test_name += '/%s' % self.subtest

        go_bin = utils_path.find_command('go')
        cmd = '%s test -v %s -run %s' % (go_bin, self.filename, test_name)

        result = process.run(cmd, ignore_status=True)
        if result.exit_status != 0:
            self.fail('Golang Test execution returned a '
                      'non-0 exit code (%s)' % result)


class NotGolangTest(object):

    """
    Not a golang test (for reporting purposes)
    """


class GolangLoader(loader.TestLoader):
    """
    Golang loader class
    """
    name = "golang"

    def __init__(self, args, extra_params):
        super(GolangLoader, self).__init__(args, extra_params)

    def discover(self, url, which_tests=loader.DEFAULT):
        avocado_suite = []
        test_files = []
        _subtest = None
        tests_filter = None
        go_src = os.path.join(os.environ.get('GOPATH'), 'src')

        if url is not None:
            if ':' in url:
                url, _tests_filter = url.split(':', 1)
                if '/' in _tests_filter:
                    _tests_filter, _subtest = _tests_filter.split('/', 1)
                tests_filter = re.compile(_tests_filter)

            package_path = os.path.join(go_src, url)
            test_files.extend(self._find_files(package_path))
        else:
            test_files.extend(self._find_files(go_src))

        if not test_files:
            if which_tests == loader.ALL:
                msg = ('No directory, file or package matching '
                       'this reference.')
                return [(NotGolangTest,
                         {"name": "%s: %s" % (url, msg)})]
            return []

        for test_file in test_files:
            test_suite = self._find_tests(test_file)
            for item in test_suite:
                common_prefix = os.path.commonprefix([go_src, test_file])
                match_package = os.path.relpath(test_file, common_prefix)
                test_name = "%s:%s" % (os.path.dirname(match_package), item)
                if tests_filter and not tests_filter.search(test_name):
                    continue
                avocado_suite.append((GolangTest,
                                      {'name': test_name,
                                       'subtest': _subtest}))
        return avocado_suite

    @staticmethod
    def _find_tests(test_path):
        test_suite = []
        with open(test_path, 'r') as test_file_fd:
            for line in test_file_fd.readlines():
                if line.startswith('func Test'):
                    test_suite.append(line.split()[1].split('(')[0])

        return test_suite

    @staticmethod
    def _find_files(path):
        matches = []
        for root, dirnames, filenames in os.walk(path):
            for filename in fnmatch.filter(filenames, '*_test.go'):
                matches.append(os.path.join(root, filename))

        return matches

    @staticmethod
    def get_type_label_mapping():
        return {GolangTest: 'GOLANG',
                NotGolangTest: "!GOLANG"}

    @staticmethod
    def get_decorator_mapping():
        return {GolangTest: output.TERM_SUPPORT.healthy_str,
                NotGolangTest: output.TERM_SUPPORT.fail_header_str}


class GolangCLI(CLI):

    """
    Run Golang tests
    """

    name = 'golang'
    description = "Golang options for 'run' subcommand"

    def configure(self, parser):
        pass

    def run(self, args):
        loader.loader.register_plugin(GolangLoader)
