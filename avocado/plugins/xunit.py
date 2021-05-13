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
from xml.dom.minidom import Document

from avocado.core.output import LOG_UI
from avocado.core.parser import FileOrStdoutAction
from avocado.core.plugin_interfaces import CLI, Init, Result
from avocado.core.settings import settings
from avocado.utils import astring
from avocado.utils.data_structures import DataSize


class XUnitResult(Result):

    name = 'xunit'
    description = 'XUnit result support'

    UNKNOWN = '<unknown>'
    PRINTABLE = string.ascii_letters + string.digits + string.punctuation + '\n\r '

    def _escape_attr(self, attrib):
        attrib = ''.join(_ if _ in self.PRINTABLE else "\\x%02x" % ord(_)
                         for _ in astring.to_text(attrib, encoding='utf-8'))
        return attrib

    def _escape_cdata(self, cdata):
        cdata = ''.join(_ if _ in self.PRINTABLE else "\\x%02x" % ord(_)
                        for _ in str(cdata))
        return cdata.replace(']]>', ']]>]]&gt;<![CDATA[')

    def _get_attr(self, container, attrib):
        return self._escape_attr(container.get(attrib, self.UNKNOWN))

    @staticmethod
    def _format_time(time):
        return "{:.3f}".format(float(time))

    def _create_testcase_element(self, document, state):
        testcase = document.createElement('testcase')
        testcase.setAttribute('classname', self._get_attr(state, 'class_name'))
        testcase.setAttribute('name', self._get_attr(state, 'name'))
        testcase.setAttribute('time', self._format_time(self._get_attr(state, 'time_elapsed')))
        return testcase

    def _create_failure_or_error(self, document, test, element_type,
                                 max_log_size=None):
        element = document.createElement(element_type)
        element.setAttribute('type', self._get_attr(test, 'fail_class'))
        element.setAttribute('message', self._get_attr(test, 'fail_reason'))
        traceback_content = self._escape_cdata(test.get('traceback', self.UNKNOWN))
        traceback = document.createCDATASection(traceback_content)
        element.appendChild(traceback)
        system_out = document.createElement('system-out')
        try:
            with open(test.get("logfile"), "r") as logfile_obj:
                if max_log_size is not None:
                    logfile_obj.seek(0, 2)
                    log_size = logfile_obj.tell()
                    logfile_obj.seek(0, 0)
                    if log_size < max_log_size:
                        text_output = logfile_obj.read()
                    else:
                        size = int(max_log_size / 2)
                        text_output = logfile_obj.read(size)
                        text_output += ("\n\n--[ CUT DUE TO XML PER TEST "
                                        "LIMIT ]--\n\n")
                        logfile_obj.seek(log_size - size, 0)
                        text_output += logfile_obj.read()
                else:
                    text_output = logfile_obj.read()
        except (TypeError, IOError):
            text_output = self.UNKNOWN
        system_out_cdata_content = self._escape_cdata(text_output)
        system_out_cdata = document.createCDATASection(system_out_cdata_content)
        system_out.appendChild(system_out_cdata)
        return element, system_out

    def _render(self, result, max_test_log_size, job_name):
        document = Document()
        testsuite = document.createElement('testsuite')
        if job_name:
            testsuite.setAttribute('name', job_name)
        else:
            testsuite.setAttribute('name', os.path.basename(os.path.dirname(result.logfile)))
        testsuite.setAttribute('tests', self._escape_attr(result.tests_total))
        testsuite.setAttribute('errors', self._escape_attr(result.errors + result.interrupted))
        testsuite.setAttribute('failures', self._escape_attr(result.failed))
        testsuite.setAttribute('skipped', self._escape_attr(result.skipped + result.cancelled))
        testsuite.setAttribute('time', self._escape_attr(self._format_time(result.tests_total_time)))
        testsuite.setAttribute('timestamp', self._escape_attr(datetime.datetime.now().isoformat()))
        document.appendChild(testsuite)
        for test in result.tests:
            testcase = self._create_testcase_element(document, test)
            status = test.get('status', 'ERROR')
            if status in ('PASS', 'WARN'):
                pass
            elif status == 'SKIP':
                testcase.appendChild(document.createElement('skipped'))
            elif status == 'FAIL':
                element, system_out = self._create_failure_or_error(document,
                                                                    test,
                                                                    'failure',
                                                                    max_test_log_size)
                testcase.appendChild(element)
                testcase.appendChild(system_out)
            elif status == 'CANCEL':
                testcase.appendChild(document.createElement('skipped'))
            else:
                element, system_out = self._create_failure_or_error(document,
                                                                    test,
                                                                    'error',
                                                                    max_test_log_size)
                testcase.appendChild(element)
                testcase.appendChild(system_out)
            testsuite.appendChild(testcase)
        return document.toprettyxml(encoding='UTF-8')

    def render(self, result, job):
        xunit_enabled = job.config.get('job.run.result.xunit.enabled')
        xunit_output = job.config.get('job.run.result.xunit.output')
        if not (xunit_enabled or xunit_output):
            return

        if not result.tests_total:
            return

        max_test_log_size = job.config.get(
            'job.run.result.xunit.max_test_log_chars')
        job_name = job.config.get('job.run.result.xunit.job_name')
        content = self._render(result, max_test_log_size, job_name)
        if xunit_enabled:
            xunit_path = os.path.join(job.logdir, 'results.xml')
            with open(xunit_path, 'wb') as xunit_file:
                xunit_file.write(content)

        xunit_path = xunit_output
        if xunit_path is not None:
            if xunit_path == '-':
                LOG_UI.debug(content.decode('UTF-8'))
            else:
                with open(xunit_path, 'wb') as xunit_file:
                    xunit_file.write(content)


class XUnitInit(Init):

    name = 'xunit'
    description = 'xUnit job result initialization'

    def initialize(self):
        section = 'job.run.result.xunit'
        help_msg = ('Enable xUnit result format and write it to FILE. '
                    'Use "-" to redirect to the standard output.')
        settings.register_option(section=section,
                                 key='output',
                                 help_msg=help_msg,
                                 default=None)

        help_msg = ('Enables default xUnit result in the job results '
                    'directory. File will be named "results.xml".')
        settings.register_option(section=section,
                                 key='enabled',
                                 key_type=bool,
                                 default=True,
                                 help_msg=help_msg)

        help_msg = ('Override the reported job name. By default uses the '
                    'Avocado job name which is always unique. This is useful '
                    'for reporting in Jenkins as it only evaluates '
                    'first-failure from jobs of the same name.')
        settings.register_option(section=section,
                                 key='job_name',
                                 default=None,
                                 help_msg=help_msg)

        help_msg = ('Limit the attached job log to given number of characters '
                    '(k/m/g suffix allowed)')
        settings.register_option(section=section,
                                 key='max_test_log_chars',
                                 help_msg=help_msg,
                                 key_type=lambda x: DataSize(x).b,
                                 default=DataSize('100000').b)


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
        settings.add_argparser_to_option(
            namespace='job.run.result.xunit.output',
            metavar='FILE',
            action=FileOrStdoutAction,
            parser=run_subcommand_parser.output,
            long_arg='--xunit')

        settings.add_argparser_to_option(
            namespace='job.run.result.xunit.enabled',
            parser=run_subcommand_parser.output,
            long_arg='--disable-xunit-job-result')

        settings.add_argparser_to_option(
            namespace='job.run.result.xunit.job_name',
            parser=run_subcommand_parser.output,
            long_arg='--xunit-job-name',
            metavar='XUNIT_JOB_NAME')

        settings.add_argparser_to_option(
            namespace='job.run.result.xunit.max_test_log_chars',
            metavar='SIZE',
            parser=run_subcommand_parser.output,
            long_arg='--xunit-max-test-log-chars')

    def run(self, config):
        pass
