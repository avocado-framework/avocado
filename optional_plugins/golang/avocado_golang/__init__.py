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
import glob
import os
import re

from avocado.core import exceptions, loader, output, test
from avocado.core.nrunner import Runnable
from avocado.core.plugin_interfaces import CLI, Resolver
from avocado.core.resolver import (ReferenceResolution,
                                   ReferenceResolutionResult)
from avocado.utils import path as utils_path
from avocado.utils import process

try:
    GO_BIN = utils_path.find_command('go')
except utils_path.CmdNotFoundError:
    GO_BIN = None


TEST_RE = re.compile(r'^func\s(Test|Example)[A-Z]')


def find_tests(test_path):
    test_suite = []
    with open(test_path, 'r') as test_file_fd:
        for line in test_file_fd.readlines():
            if TEST_RE.match(line):
                test_suite.append(line.split()[1].split('(')[0])

    return test_suite


def find_files(path, recursive=True):
    pattern = '*_test.go'
    if recursive:
        matches = []
        for root, _, filenames in os.walk(path):
            for filename in fnmatch.filter(filenames, pattern):
                matches.append(os.path.join(root, filename))
        return matches

    if path != os.path.curdir:
        pattern = os.path.join(path, pattern)
    return glob.iglob(pattern)


class GolangTest(test.SimpleTest):

    """
    Run a Golang Test command as a SIMPLE test.
    """

    def __init__(self, name, params=None, base_logdir=None, job=None,
                 subtest=None, executable=None):
        super(GolangTest, self).__init__(name, params, base_logdir, job,
                                         executable)
        self.subtest = subtest

    @property
    def filename(self):
        """
        Returns the path of the golang test suite.
        """
        return self._filename.split(':')[0]

    def test(self):
        """
        Create the Golang command and execute it.
        """
        if GO_BIN is None:
            raise exceptions.TestError("go binary not found")

        test_name = '%s$' % self._filename.split(':')[1]
        if self.subtest is not None:
            test_name += '/%s' % self.subtest

        cmd = '%s test -v %s -run %s' % (GO_BIN, self.filename, test_name)

        result = process.run(cmd, ignore_status=True)
        if result.exit_status != 0:
            self.fail('Golang Test execution returned a '
                      'non-0 exit code (%s)' % result)


class NotGolangTest:

    """
    Not a golang test (for reporting purposes)
    """


class GolangLoader(loader.TestLoader):
    """
    Golang loader class
    """
    name = "golang"

    def discover(self, reference, which_tests=loader.DiscoverMode.DEFAULT):
        if GO_BIN is None:
            return self._no_tests(which_tests, reference, 'Go binary not found.')

        if reference is None:
            return []

        avocado_suite = []
        test_files = []
        subtest = None
        tests_filter = None

        if ':' in reference:
            reference, _tests_filter = reference.split(':', 1)
            parsed_filter = re.split(r'(?<!\\)/', _tests_filter, 1)
            _tests_filter = parsed_filter[0]
            if len(parsed_filter) > 1:
                subtest = parsed_filter[1]
            tests_filter = re.compile(_tests_filter)

        # When a file is provided
        if os.path.isfile(reference):
            for item in find_tests(reference):
                test_name = "%s:%s" % (reference, item)
                if tests_filter and not tests_filter.search(test_name):
                    continue
                avocado_suite.append((GolangTest, {'name': test_name,
                                                   'subtest': subtest,
                                                   'executable': test_name}))

            return avocado_suite or self._no_tests(which_tests, reference,
                                                   'No test matching this '
                                                   'reference.')

        # When a directory is provided
        if os.path.isdir(reference):
            for test_file in find_files(reference, recursive=False):
                for item in find_tests(test_file):
                    test_name = "%s:%s" % (item, item)
                    if tests_filter and not tests_filter.search(test_name):
                        continue
                    avocado_suite.append((GolangTest, {'name': test_name,
                                                       'subtest': subtest,
                                                       'executable': test_name}))

            return avocado_suite or self._no_tests(which_tests, reference,
                                                   'No test matching this '
                                                   'reference.')

        # When a package is provided
        package_paths = []
        go_root = os.environ.get('GOROOT')
        go_path = os.environ.get('GOPATH')

        if go_root is not None:
            for directory in go_root.split(os.pathsep):
                pkg_path = os.path.join(os.path.expanduser(directory), 'src')
                package_paths.append(pkg_path)

        if go_path is not None:
            for directory in go_path.split(os.pathsep):
                pkg_path = os.path.join(os.path.expanduser(directory), 'src')
                package_paths.append(pkg_path)

        for package_path in package_paths:
            url_path = os.path.join(package_path, reference)
            files = find_files(url_path)
            if files:
                test_files.append((package_path, files))
                break

        for package_path, test_files_list in test_files:
            for test_file in test_files_list:
                for item in find_tests(test_file):
                    common_prefix = os.path.commonprefix([package_path,
                                                          test_file])
                    match_package = os.path.relpath(test_file, common_prefix)
                    test_name = "%s:%s" % (os.path.dirname(match_package),
                                           item)
                    if tests_filter and not tests_filter.search(test_name):
                        continue
                    avocado_suite.append((GolangTest,
                                          {'name': test_name,
                                           'subtest': subtest,
                                           'executable': test_name}))

        return avocado_suite or self._no_tests(which_tests, reference,
                                               'No test matching this '
                                               'reference.')

    @staticmethod
    def _no_tests(which_tests, url, msg):
        if which_tests == loader.DiscoverMode.ALL:
            return [(NotGolangTest, {"name": "%s: %s" % (url, msg)})]
        return []

    @staticmethod
    def get_type_label_mapping():
        return {GolangTest: 'GOLANG',
                NotGolangTest: "!GOLANG"}

    @staticmethod
    def get_decorator_mapping():
        return {GolangTest: output.TERM_SUPPORT.healthy_str,
                NotGolangTest: output.TERM_SUPPORT.fail_header_str}


class GolangResolver(Resolver):

    name = 'golang'
    description = 'Test resolver for Go language tests'

    @staticmethod
    def resolve(reference):

        if GO_BIN is None:
            return ReferenceResolution(reference,
                                       ReferenceResolutionResult.NOTFOUND,
                                       info="go binary not found")

        package_paths = []
        test_files = []
        go_path = os.environ.get('GOPATH')
        if go_path is not None:
            for directory in go_path.split(os.pathsep):
                pkg_path = os.path.join(os.path.expanduser(directory), 'src')
                package_paths.append(pkg_path)

        for package_path in package_paths:
            url_path = os.path.join(package_path, reference)
            files = find_files(url_path)
            if files:
                test_files.append((package_path, files))
                break

        runnables = []
        for package_path, test_files_list in test_files:
            for test_file in test_files_list:
                for item in find_tests(test_file):
                    common_prefix = os.path.commonprefix([package_path,
                                                          test_file])
                    match_package = os.path.relpath(test_file, common_prefix)
                    test_name = "%s:%s" % (os.path.dirname(match_package),
                                           item)
                    runnables.append(Runnable('golang', uri=test_name))

        if runnables:
            return ReferenceResolution(reference,
                                       ReferenceResolutionResult.SUCCESS,
                                       runnables)

        return ReferenceResolution(reference,
                                   ReferenceResolutionResult.NOTFOUND)


class GolangCLI(CLI):

    """
    Run Golang tests
    """

    name = 'golang'
    description = "Golang options for 'run' subcommand"

    def configure(self, parser):
        pass

    def run(self, config):
        loader.loader.register_plugin(GolangLoader)
