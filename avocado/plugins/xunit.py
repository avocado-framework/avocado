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

import sys
import datetime
from xml.sax.saxutils import quoteattr

from avocado.plugins import plugin
from avocado.result import TestResult


class XmlResult(object):

    """
    Handles the XML details for xUnit output.
    """

    def __init__(self, output):
        self.xml = ['<?xml version="1.0" encoding="UTF-8"?>']
        self.output = output

    def _escape_attr(self, attrib):
        return quoteattr(attrib)

    def _escape_cdata(self, cdata):
        return cdata.replace(']]>', ']]>]]&gt;<![CDATA[')

    def save(self, filename=None):
        """
        Save the XML document to a file or standard output.

        :param filename: File name to save. Use '-' for standard output.
        """
        if filename is None:
            filename = self.output
        xml = '\n'.join(self.xml)
        xml += '\n'
        if filename == '-':
            sys.stdout.write(xml)
        else:
            with open(filename, 'w') as fresult:
                fresult.write(xml)

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

    def add_success(self, test):
        """
        Add a testcase node of kind succeed.

        :param test: an instance of :class:`avocado.test.Test`.
        """
        tc = '\t<testcase classname={class} name={name} time="{time}"/>'
        values = {'class': self._escape_attr(test.__class__.__name__),
                  'name': self._escape_attr(test.tagged_name),
                  'time': test.time_elapsed}
        self.testcases.append(tc.format(**values))

    def add_skip(self, test):
        """
        Add a testcase node of kind skipped.

        :param test: an instance of :class:`avocado.test.Test`.
        """
        tc = '''\t<testcase classname={class} name={name} time="{time}">
\t\t<skipped />
\t</testcase>'''
        values = {'class': self._escape_attr(test.__class__.__name__),
                  'name': self._escape_attr(test.tagged_name),
                  'time': test.time_elapsed}
        self.testcases.append(tc.format(**values))

    def add_failure(self, test):
        """
        Add a testcase node of kind failed.

        :param test: an instance of :class:`avocado.test.Test`.
        """
        tc = '''\t<testcase classname={class} name={name} time="{time}">
\t\t<failure type={type} message={reason}><![CDATA[{traceback}]]></failure>
\t\t<system-out><![CDATA[{systemout}]]></system-out>
\t</testcase>'''
        values = {'class': self._escape_attr(test.__class__.__name__),
                  'name': self._escape_attr(test.tagged_name),
                  'time': test.time_elapsed,
                  'type': self._escape_attr(test.fail_class),
                  'traceback': self._escape_cdata(test.traceback),
                  'systemout': self._escape_cdata(test.text_output),
                  'reason': self._escape_attr(str(test.fail_reason))}
        self.testcases.append(tc.format(**values))

    def add_error(self, test):
        """
        Add a testcase node of kind error.

        :param test: an instance of :class:`avocado.test.Test`.
        """
        tc = '''\t<testcase classname={class} name={name} time="{time}">
\t\t<error type={type} message={reason}><![CDATA[{traceback}]]></error>
\t\t<system-out><![CDATA[{systemout}]]></system-out>
\t</testcase>'''
        values = {'class': self._escape_attr(test.__class__.__name__),
                  'name': self._escape_attr(test.tagged_name),
                  'time': test.time_elapsed,
                  'type': self._escape_attr(test.fail_class),
                  'traceback': self._escape_cdata(test.traceback),
                  'systemout': self._escape_cdata(test.text_output),
                  'reason': self._escape_attr(str(test.fail_reason))}
        self.testcases.append(tc.format(**values))


class xUnitTestResult(TestResult):

    """
    xUnit Test Result class.
    """

    def __init__(self, stream=None, args=None):
        """
        Creates an instance of xUnitTestResult.

        :param stream: an instance of :class:`avocado.core.output.OutputManager`.
        :param args: an instance of :class:`argparse.Namespace`.
        """
        TestResult.__init__(self, stream, args)
        self.xml = XmlResult(self.output)

    def set_output(self):
        self.output = getattr(self.args, 'xunit_output', '-')

    def set_output_option(self):
        self.output_option = '--xunit'

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

    def end_test(self, test):
        """
        Record an end test event, accord to the given test status.
        """
        TestResult.end_test(self, test)
        if test.status == 'PASS':
            self.xml.add_success(test)
        if test.status == 'TEST_NA':
            self.xml.add_skip(test)
        if test.status == 'FAIL':
            self.xml.add_failure(test)
        if test.status == 'ERROR':
            self.xml.add_error(test)

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
        self.xml.save()


class XUnit(plugin.Plugin):

    """
    xUnit output plugin.
    """

    name = 'xunit'
    enabled = True

    def configure(self, app_parser, cmd_parser):
        self.parser = app_parser
        app_parser.add_argument('--xunit', action='store_true')
        app_parser.add_argument('--xunit-output',
                                default='-', type=str,
                                dest='xunit_output',
                                help='the file where the result should be written')
        self.configured = True

    def activate(self, app_args):
        if app_args.xunit:
            self.parser.set_defaults(xunit_result=xUnitTestResult)
