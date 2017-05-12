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
# Authors: Ruda Moura <rmoura@redhat.com>
#          Cleber Rosa <crosa@redhat.com>

"""xUnit module."""

import datetime
import os
import string
from xml.dom.minidom import Document, Element

from avocado.core.parser import FileOrStdoutAction
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLI, Result


class XUnitResult(Result):

    name = 'xunit'
    description = 'XUnit result support'

    UNKNOWN = '<unknown>'
    PRINTABLE = string.ascii_letters + string.digits + string.punctuation + '\n\r '

    def _escape_attr(self, attrib):
        attrib = ''.join(_ if _ in self.PRINTABLE else "\\x%02x" % ord(_)
                         for _ in str(attrib))
        return attrib

    def _escape_cdata(self, cdata):
        cdata = ''.join(_ if _ in self.PRINTABLE else "\\x%02x" % ord(_)
                        for _ in str(cdata))
        return cdata.replace(']]>', ']]>]]&gt;<![CDATA[')

    def _get_attr(self, container, attrib):
        return self._escape_attr(container.get(attrib, self.UNKNOWN))

    def _create_testcase_element(self, document, state):
        testcase = document.createElement('testcase')
        testcase.setAttribute('classname', self._get_attr(state, 'class_name'))
        testcase.setAttribute('name', self._get_attr(state, 'name'))
        testcase.setAttribute('time', self._get_attr(state, 'time_elapsed'))
        return testcase

    def _create_failure_or_error(self, document, test, element_type):
        element = Element(element_type)
        element.setAttribute('type', self._get_attr(test, 'fail_class'))
        element.setAttribute('message', self._get_attr(test, 'fail_reason'))
        traceback_content = self._escape_cdata(test.get('traceback', self.UNKNOWN))
        traceback = document.createCDATASection(traceback_content)
        element.appendChild(traceback)
        system_out = Element('system-out')
        try:
            with open(test.get("logfile"), "r") as logfile_obj:
                text_output = logfile_obj.read()
        except (TypeError, IOError):
            text_output = self.UNKNOWN
        system_out_cdata_content = self._escape_cdata(text_output)
        system_out_cdata = document.createCDATASection(system_out_cdata_content)
        system_out.appendChild(system_out_cdata)
        return element, system_out

    def _render(self, result):
        document = Document()
        testsuite = document.createElement('testsuite')
        testsuite.setAttribute('name', 'avocado')
        testsuite.setAttribute('tests', self._escape_attr(result.tests_total))
        testsuite.setAttribute('errors', self._escape_attr(result.errors + result.interrupted))
        testsuite.setAttribute('failures', self._escape_attr(result.failed))
        testsuite.setAttribute('skipped', self._escape_attr(result.skipped + result.cancelled))
        testsuite.setAttribute('time', self._escape_attr(result.tests_total_time))
        testsuite.setAttribute('timestamp', self._escape_attr(datetime.datetime.now()))
        document.appendChild(testsuite)
        for test in result.tests:
            testcase = self._create_testcase_element(document, test)
            status = test.get('status', 'ERROR')
            if status in ('PASS', 'WARN'):
                pass
            elif status == 'SKIP':
                testcase.appendChild(Element('skipped'))
            elif status == 'FAIL':
                element, system_out = self._create_failure_or_error(document,
                                                                    test,
                                                                    'failure')
                testcase.appendChild(element)
                testcase.appendChild(system_out)
            elif status == 'CANCEL':
                testcase.appendChild(Element('skipped'))
            else:
                element, system_out = self._create_failure_or_error(document,
                                                                    test,
                                                                    'error')
                testcase.appendChild(element)
                testcase.appendChild(system_out)
            testsuite.appendChild(testcase)
        return document.toprettyxml(encoding='UTF-8')

    def render(self, result, job):
        if not (hasattr(job.args, 'xunit_job_result') or
                hasattr(job.args, 'xunit_output')):
            return

        if not result.tests_total:
            return

        content = self._render(result)
        if getattr(job.args, 'xunit_job_result', 'off') == 'on':
            xunit_path = os.path.join(job.logdir, 'results.xml')
            with open(xunit_path, 'w') as xunit_file:
                xunit_file.write(content)

        xunit_path = getattr(job.args, 'xunit_output', 'None')
        if xunit_path is not None:
            if xunit_path == '-':
                LOG_UI.debug(content)
            else:
                with open(xunit_path, 'w') as xunit_file:
                    xunit_file.write(content)


class XUnitCLI(CLI):

    """
    xUnit output
    """

    name = 'xunit'
    description = 'xUnit output options'

    def configure(self, parser):
        run_subcommand_parser = parser.subcommands.choices.get('run', None)
        if run_subcommand_parser is None:
            return

        self.parser = parser
        run_subcommand_parser.output.add_argument(
            '--xunit', type=str, action=FileOrStdoutAction,
            dest='xunit_output', metavar='FILE',
            help=('Enable xUnit result format and write it to FILE. '
                  "Use '-' to redirect to the standard output."))

        run_subcommand_parser.output.add_argument(
            '--xunit-job-result', dest='xunit_job_result',
            choices=('on', 'off'), default='on',
            help=('Enables default xUnit result in the job results directory. '
                  'File will be named "results.xml".'))

    def run(self, args):
        pass
