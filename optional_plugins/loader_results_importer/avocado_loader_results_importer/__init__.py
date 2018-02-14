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
# Author: Lukas Doktor <ldoktor@redhat.com>
"""Avocado Plugin that imports various result types and reports them as test
results"""
# Supported result statuses


import copy
import os
import re

import avocado
from avocado.core import loader
from avocado.core import output
from avocado.core import parameters
from avocado.core.plugin_interfaces import CLI

from six import iteritems


PASS = 0
WARN = 1
CANCEL = 2
FAIL = -1
ERROR = -2
UNKNOWN = -99


class ResultsImporterTest(avocado.Test):
    """
    Test that logs what's expected and finishes with defined status
    """

    __status = 0
    __content = None
    __details = ""

    def __init__(self, **kwargs):
        state = kwargs.pop("results_importer_state", None)
        if state:
            self.__status = state.get("status")
            self.__content = state.get("content")
            self.__details = str(state.get("details"))
        super(ResultsImporterTest, self).__init__(**kwargs)

    def test(self):
        """
        Report the content and finish with expected status
        """
        if self.__content:
            self.log.info("---< Beginning of the imported content >---")
            for line in self.__content:
                self.log.info(line)
            self.log.info("---< End of the imported content >---")
        if self.__status == PASS:
            pass
        elif self.__status == WARN:
            self.log.warning(self.__details)
        elif self.__status == CANCEL:
            self.cancel(self.__details)
        elif self.__status == FAIL:
            self.fail(self.__details)
        else:
            self.error(self.__details)


class NotResultsImporterTest(avocado.Test):
    """
    Class representing not a results importer test
    """


class TapDiscoverer(object):
    """
    Class to discover TAP results into test factories
    """
    def __init__(self):
        self.__re_no_tests = re.compile(r"^1..(\d+)")
        self.__re_test_result = re.compile(r"^(not )?ok( \d+)?( .*)?")

    @staticmethod
    def add_test(tests, test, content):
        """
        Insert test factory into list of test factories
        """
        _status, idx, _name = test
        if '#' in _name:
            name, details = _name.split('#', 1)
        else:
            name = _name
            details = None
        if _status is None:
            if details is None:
                status = PASS
            elif details[1:5].lower() == "skip":
                status = CANCEL
            else:
                status = WARN
        else:
            status = FAIL
        state = {"status": status, "content": content, "details": details}
        kwargs = {"name": name, "results_importer_state": state}
        if idx is not None:
            # idx starts from 1 but we store into list starting with 0
            idx = int(idx)
            _idx = idx - 1
            len_tests = len(tests)
            if _idx == len_tests:
                tests.append((ResultsImporterTest, kwargs))
            elif _idx > len_tests:
                tests += [None] * _idx - len_tests
                tests[-1] = (ResultsImporterTest, kwargs)
            else:
                if tests[_idx] is None:
                    tests[_idx] = (ResultsImporterTest, kwargs)
                else:
                    raise ValueError("Failed to insert result %s, results with"
                                     " index %s already present (%s)"
                                     % (test, idx, tests))

    def discover(self, reference, which_tests):
        """
        Discover "tap://$url" as tap result
        """
        url = reference[6:]
        if not os.path.isfile(url):
            if which_tests is loader.DEFAULT:
                return []
            return [(ResultsImporterTest, {"name": "%s: %s file not found"
                                                   % (reference, url)})]

        tests = []
        with open(url, 'r') as results:
            no_tests = None
            _test = None
            _content = []
            try:
                for line in results:
                    if no_tests is None:
                        no_tests = self.__re_no_tests.match(line)
                        if no_tests:
                            no_tests = no_tests.group(1)
                            continue
                    match = self.__re_test_result.match(line)
                    if match:
                        if _test:
                            self.add_test(tests, _test, _content)
                        _content = []
                        _test = match.groups()
                    else:
                        _content.append(line[:-1])
            except ValueError as details:
                if which_tests is loader.DEFAULT:
                    return []
                return [(ResultsImporterTest, {"name": "%s: %s"
                                                       % (reference,
                                                          details)})]
        if _test:
            self.add_test(tests, _test, _content)
        if no_tests is None:
            if which_tests is loader.DEFAULT:
                return []
            return [(ResultsImporterTest, {"name": "%s: Number of tests not "
                                                   "specified in TAP file."
                                                   % reference})]
        for i, test in enumerate(tests):
            if test is None:
                kwargs = {"name": "Missing",
                          "results_importer_state": {"status": ERROR}}
                tests[i] = (ResultsImporterTest, kwargs)
        return tests


class ResultsImporterLoader(loader.TestLoader):

    """
    Uses $type://$url format to find results in supported $type and loads
    them as tests so they can be integrated into overall results.
    """

    name = "results_importer"
    _tap_loader = None

    @staticmethod
    def get_type_label_mapping():
        """
        No type is discovered by default, uses "full_*_mappings" to report
        the actual types after "discover()" is called.
        """
        return {ResultsImporterTest: 'IMPORTED',
                NotResultsImporterTest: '!IMPORTED'}

    @staticmethod
    def get_decorator_mapping():
        return {ResultsImporterTest: output.TERM_SUPPORT.healthy_str,
                NotResultsImporterTest: output.TERM_SUPPORT.fail_header_str}

    def discover(self, reference, which_tests=loader.DEFAULT):
        if reference is None:
            return []
        if reference.startswith("tap://"):
            if self._tap_loader is None:
                self._tap_loader = TapDiscoverer()
            return self._tap_loader.discover(reference, which_tests)
        return []


class ResultsImporterPlugin(CLI):
    """
    Registers the ResultsImporterLoader
    """

    name = 'loader_yaml'
    description = "YAML test loader options for the 'run' subcommand"

    def configure(self, parser):
        pass

    def run(self, args):
        loader.loader.register_plugin(ResultsImporterLoader)
