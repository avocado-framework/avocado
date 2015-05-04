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
# Copyright: Red Hat Inc. 2014
# Author: Ruda Moura <rmoura@redhat.com>

"""xUnit module."""

import datetime
from xml.sax.saxutils import quoteattr

from avocado.core import output
from avocado.core.result import TestResult
from avocado.plugins import plugin


# We use a subset of the XML format defined in this URL:
# https://svn.jenkins-ci.org/trunk/hudson/dtkit/dtkit-format/dtkit-junit-model/src/main/resources/com/thalesgroup/dtkit/junit/model/xsd/junit-4.xsd

class XmlResult(object):

    """
    Handles the XML details for xUnit output.
    """

    def __init__(self):
        self.xml = ['<?xml version="1.0" encoding="UTF-8"?>']

    def _escape_attr(self, attrib):
        return quoteattr(attrib)

    def _escape_cdata(self, cdata):
        try:
            return cdata.replace(']]>', ']]>]]&gt;<![CDATA[')
        except AttributeError:
            try:
                str(cdata).replace(']]>', ']]>]]&gt;<![CDATA[')
            except TypeError:
                return 'ERROR: UnparsableObject'

    def get_contents(self):
        return '\n'.join(self.xml)

    def start_testsuite(self, timestamp):
        """
        Start a new testsuite node.

        :param timestamp: Timestamp string in date/time format.
        """
        self.testsuite = '<testsuite name="avocado" tests="{tests}" errors="{errors}" failures="{failures}" skip="{skip}" time="{total_time}" timestamp="%s">' % timestamp
        self.testcases = []

    def end_testsuite(self, tests, errors, failures, skip, total_time):
        """
        End of testsuite node.

        :param tests: Number of tests.
        :param errors: Number of test errors.
        :param failures: Number of test failures.
        :param skip: Number of test skipped.
        :param total_time: The total time of test execution.
        """
        values = {'tests': tests,
                  'errors': errors,
                  'failures': failures,
                  'skip': skip,
                  'total_time': total_time}
        self.xml.append(self.testsuite.format(**values))
        for tc in self.testcases:
            self.xml.append(tc)
        self.xml.append('</testsuite>')

    def add_success(self, state):
        """
        Add a testcase node of kind succeed.

        :param state: result of :class:`avocado.test.Test.get_state`.
        :type state: dict
        """
        tc = '\t<testcase classname={class} name={name} time="{time}"/>'
        values = {'class': self._escape_attr(state['class_name']),
                  'name': self._escape_attr(state['tagged_name']),
                  'time': state['time_elapsed']}
        self.testcases.append(tc.format(**values))

    def add_skip(self, state):
        """
        Add a testcase node of kind skipped.

        :param state: result of :class:`avocado.test.Test.get_state`.
        :type state: dict
        """
        tc = '''\t<testcase classname={class} name={name} time="{time}">
\t\t<skipped />
\t</testcase>'''
        values = {'class': self._escape_attr(state['class_name']),
                  'name': self._escape_attr(state['tagged_name']),
                  'time': state['time_elapsed']}
        self.testcases.append(tc.format(**values))

    def add_failure(self, state):
        """
        Add a testcase node of kind failed.

        :param state: result of :class:`avocado.test.Test.get_state`.
        :type state: dict
        """
        tc = '''\t<testcase classname={class} name={name} time="{time}">
\t\t<failure type={type} message={reason}><![CDATA[{traceback}]]></failure>
\t\t<system-out><![CDATA[{systemout}]]></system-out>
\t</testcase>'''
        values = {'class': self._escape_attr(state['class_name']),
                  'name': self._escape_attr(state['tagged_name']),
                  'time': state['time_elapsed'],
                  'type': self._escape_attr(state['fail_class']),
                  'traceback': self._escape_cdata(state['traceback']),
                  'systemout': self._escape_cdata(state['text_output']),
                  'reason': self._escape_attr(str(state['fail_reason']))}
        self.testcases.append(tc.format(**values))

    def add_error(self, state):
        """
        Add a testcase node of kind error.

        :param state: result of :class:`avocado.test.Test.get_state`.
        :type state: dict
        """
        tc = '''\t<testcase classname={class} name={name} time="{time}">
\t\t<error type={type} message={reason}><![CDATA[{traceback}]]></error>
\t\t<system-out><![CDATA[{systemout}]]></system-out>
\t</testcase>'''
        values = {'class': self._escape_attr(state['class_name']),
                  'name': self._escape_attr(state['tagged_name']),
                  'time': state['time_elapsed'],
                  'type': self._escape_attr(state['fail_class']),
                  'traceback': self._escape_cdata(state['traceback']),
                  'systemout': self._escape_cdata(state['text_output']),
                  'reason': self._escape_attr(str(state['fail_reason']))}
        self.testcases.append(tc.format(**values))


class xUnitTestResult(TestResult):

    """
    xUnit Test Result class.
    """

    command_line_arg_name = '--xunit'

    def __init__(self, stream=None, args=None):
        """
        Creates an instance of xUnitTestResult.

        :param stream: an instance of :class:`avocado.core.output.View`.
        :param args: an instance of :class:`argparse.Namespace`.
        """
        TestResult.__init__(self, stream, args)
        self.output = getattr(self.args, 'xunit_output', '-')
        self.stream = output.View(app_args=args)
        self.xml = XmlResult()

    def start_tests(self):
        """
        Record a start tests event.
        """
        TestResult.start_tests(self)
        self.xml.start_testsuite(datetime.datetime.now())

    def start_test(self, test):
        """
        Record a start test event.
        """
        TestResult.start_test(self, test)

    def end_test(self, state):
        """
        Record an end test event, accord to the given test status.

        :param state: result of :class:`avocado.test.Test.get_state`.
        :type state: dict
        """
        TestResult.end_test(self, state)
        if state['status'] in ('PASS', 'WARN'):
            self.xml.add_success(state)
        elif state['status'] == 'TEST_NA':
            self.xml.add_skip(state)
        elif state['status'] == 'FAIL':
            self.xml.add_failure(state)
        elif state['status'] == 'ERROR':
            self.xml.add_error(state)

    def end_tests(self):
        """
        Record an end tests event.
        """
        TestResult.end_tests(self)
        values = {'tests': self.tests_total,
                  'errors': len(self.errors),
                  'failures': len(self.failed),
                  'skip': len(self.skipped),
                  'total_time': self.total_time}
        self.xml.end_testsuite(**values)
        contents = self.xml.get_contents()
        if self.output == '-':
            self.stream.notify(event='minor', msg=contents)
        else:
            with open(self.output, 'w') as xunit_output:
                xunit_output.write(contents)


class XUnit(plugin.Plugin):

    """
    xUnit output
    """

    name = 'xunit'
    enabled = True

    def configure(self, parser):
        self.parser = parser
        self.parser.runner.output.add_argument(
            '--xunit', type=str, dest='xunit_output',
            help=('Enable xUnit output to the file where the result should be written. '
                  "Use '-' to redirect to the standard output."))
        self.configured = True

    def activate(self, app_args):
        try:
            if app_args.xunit_output:
                self.parser.application.set_defaults(xunit_result=xUnitTestResult)
        except AttributeError:
            pass
