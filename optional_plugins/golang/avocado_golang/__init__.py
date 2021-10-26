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

from avocado.core import exceptions, output
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
