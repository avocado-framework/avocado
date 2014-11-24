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
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

"""
HTML output module.
"""

import pystache
import os
import time
import shutil
import sys

from avocado.core import output
from avocado.plugins import plugin
from avocado.result import TestResult


class ReportModel(object):

    """
    Prepares JSON that can be passed up to mustache for rendering.
    """

    def __init__(self, json_input):
        """
        Base JSON that comes from test results.
        """
        self.json = json_input

    def job_id(self):
        return self.json['job_id']

    def execution_time(self):
        return "%.2f" % self.json['time']

    def results_dir(self):
        return os.path.dirname(self.json['debuglog'])

    def results_dir_basename(self):
        return os.path.basename(os.path.dirname(self.json['debuglog']))

    def total(self):
        return self.json['total']

    def passed(self):
        return self.json['pass']

    def pass_rate(self):
        pr = 100 * (float(self.json['pass']) / float(self.json['total']))
        return "%.2f" % pr

    def _get_sysinfo(self, sysinfo_file):
        sysinfo_path = os.path.join(self.results_dir(), 'sysinfo', 'pre', sysinfo_file)
        try:
            with open(sysinfo_path, 'r') as sysinfo_file:
                sysinfo_contents = sysinfo_file.read()
        except OSError, details:
            sysinfo_contents = "Error reading %s: %s" % (sysinfo_path, details)
        return sysinfo_contents

    def hostname(self):
        return self._get_sysinfo('hostname')

    @property
    def tests(self):
        mapping = {"TEST_NA": "danger",
                   "ABORT": "danger",
                   "ERROR": "danger",
                   "NOT_FOUND": "warning",
                   "FAIL": "danger",
                   "WARN": "warning",
                   "PASS": "success",
                   "START": "info",
                   "ALERT": "danger",
                   "RUNNING": "info",
                   "NOSTATUS": "info",
                   "INTERRUPTED": "danger"}
        test_info = self.json['tests']
        for t in test_info:
            t['link'] = os.path.join(self.results_dir(), 'test-results', t['url'], 'debug.log')
            t['link_basename'] = os.path.basename(t['link'])
            t['time'] = "%.2f" % t['time']
            t['time_start'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t['time_start']))
            t['row_class'] = mapping[t['status']]
            exibition_limit = 40
            if len(t['fail_reason']) > exibition_limit:
                t['fail_reason'] = ('<a data-container="body" data-toggle="popover" '
                                    'data-placement="top" title="Error Details" data-content="%s">%s...</a>' %
                                    (t['fail_reason'], t['fail_reason'][:exibition_limit]))
        return test_info

    def sysinfo(self):
        base_path = os.path.join(self.results_dir(), 'sysinfo', 'pre')
        sysinfo_files = os.listdir(base_path)
        sysinfo_files.sort()
        sysinfo_list = []
        s_id = 1
        for s_f in sysinfo_files:
            sysinfo_dict = {}
            sysinfo_path = os.path.join(base_path, s_f)
            try:
                with open(sysinfo_path, 'r') as sysinfo_file:
                    sysinfo_dict['file'] = " ".join(s_f.split("_"))
                    sysinfo_dict['contents'] = sysinfo_file.read()
                    sysinfo_dict['element_id'] = 'heading_%s' % s_id
                    sysinfo_dict['collapse_id'] = 'collapse_%s' % s_id
            except OSError:
                sysinfo_dict[s_f] = 'Error reading sysinfo file %s' % sysinfo_path
            sysinfo_list.append(sysinfo_dict)
            s_id += 1
        return sysinfo_list


class HTMLTestResult(TestResult):

    """
    HTML Test Result class.
    """

    command_line_arg_name = '--html'

    def __init__(self, stream=None, args=None):
        TestResult.__init__(self, stream, args)
        self.output = getattr(self.args, 'html_output', '-')
        self.args = args
        self.view = output.View(app_args=args)
        self.json = None

    def start_tests(self):
        """
        Called once before any tests are executed.
        """
        TestResult.start_tests(self)
        self.json = {'debuglog': self.stream.logfile,
                     'tests': []}

    def end_test(self, state):
        """
        Called when the given test has been run.

        :param state: result of :class:`avocado.test.Test.get_state`.
        :type state: dict
        """
        TestResult.end_test(self, state)
        if 'job_id' not in self.json:
            self.json['job_id'] = state['job_unique_id']
        if state['fail_reason'] is None:
            state['fail_reason'] = ''
        else:
            state['fail_reason'] = str(state['fail_reason'])
        t = {'test': state['tagged_name'],
             'url': state['name'],
             'time_start': state['time_start'],
             'time_end': state['time_end'],
             'time': state['time_elapsed'],
             'status': state['status'],
             'fail_reason': state['fail_reason'],
             'whiteboard': state['whiteboard'],
             }
        self.json['tests'].append(t)

    def end_tests(self):
        """
        Called once after all tests are executed.
        """
        TestResult.end_tests(self)
        self.json.update({
            'total': len(self.json['tests']),
            'pass': len(self.passed),
            'errors': len(self.errors),
            'not_found': len(self.not_found),
            'failures': len(self.failed),
            'skip': len(self.skipped),
            'time': self.total_time
        })
        self._render_report()

    def _get_resource_path(self, *args):
        plugins_dir = os.path.dirname(sys.modules[__name__].__file__)
        resources_dir = os.path.join(plugins_dir, 'resources', 'htmlresult')
        return os.path.join(resources_dir, *args)

    def _render_report(self):
        context = ReportModel(json_input=self.json)
        renderer = pystache.Renderer()
        template = self._get_resource_path('templates', 'report.mustache')
        report_contents = renderer.render(open(template, 'r').read(), context)
        static_basedir = self._get_resource_path('static')
        if self.output == '-':
            self.view.notify(event='minor', msg=report_contents)
        else:
            output_dir = os.path.dirname(os.path.abspath(self.output))
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            for resource_dir in os.listdir(static_basedir):
                res_dir = os.path.join(static_basedir, resource_dir)
                out_dir = os.path.join(output_dir, resource_dir)
                shutil.copytree(res_dir, out_dir)
            with open(self.output, 'w') as report_file:
                report_file.write(report_contents)

            if self.args is not None:
                if getattr(self.args, 'open_browser'):
                    os.popen('xdg-open %s 2>&1>/dev/null' % self.output)


class HTML(plugin.Plugin):

    """
    HTML job report.
    """

    name = 'htmlresult'
    enabled = True
    parser = None

    def configure(self, parser):
        self.parser = parser
        self.parser.runner.add_argument(
            '--html', type=str,
            dest='html_output',
            help='Enable HTML output to the file where the result should be written. '
                 'Use - to redirect the HTML contents to the standard output (css and '
                 'js files will not be embedded on the html)')
        self.parser.runner.add_argument(
            '--open-browser',
            dest='open_browser',
            action='store_true',
            default=False,
            help='Open the generated report on your preferred browser (uses xdg-open)')
        self.configured = True

    def activate(self, app_args):
        try:
            if app_args.html_output:
                self.parser.application.set_defaults(html_result=HTMLTestResult)
        except AttributeError:
            pass
