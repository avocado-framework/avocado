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
import codecs
import os
import shutil
import sys
import time
import subprocess

try:
    import pystache
except ImportError:
    HTML_REPORT_CAPABLE = False
else:
    HTML_REPORT_CAPABLE = True

from avocado import runtime
from avocado.core import exit_codes
from avocado.core import output
from avocado.result import TestResult
from avocado.utils import path as utils_path
from avocado.plugins import plugin


class ReportModel(object):

    """
    Prepares JSON that can be passed up to mustache for rendering.
    """

    def __init__(self, json_input, html_output, relative_links):
        """
        Base JSON that comes from test results.
        """
        self.json = json_input
        self.relative_links = relative_links
        self.html_output = html_output

    def get(self, key, default):
        value = getattr(self, key, default)
        if callable(value):
            return value()
        else:
            return value

    def job_id(self):
        return self.json['job_id']

    def execution_time(self):
        return "%.2f" % self.json['time']

    def _results_dir(self, relative_links=True):
        debuglog_abspath = os.path.abspath(os.path.dirname(
            self.json['debuglog']))
        html_output_abspath = os.path.abspath(os.path.dirname(self.html_output))
        if relative_links:
            return os.path.relpath(debuglog_abspath, html_output_abspath)
        else:
            return debuglog_abspath

    def results_dir(self):
        return self._results_dir(relative_links=self.relative_links)

    def results_dir_basename(self):
        return os.path.basename(self._results_dir(relative_links=False))

    def total(self):
        return self.json['total']

    def passed(self):
        return self.json['pass']

    def pass_rate(self):
        total = float(self.json['total'])
        passed = float(self.json['pass'])
        if total > 0:
            pr = 100 * (passed / total)
        else:
            pr = 0
        return "%.2f" % pr

    def _get_sysinfo(self, sysinfo_file):
        sysinfo_path = os.path.join(self._results_dir(relative_links=False),
                                    'sysinfo', 'pre', sysinfo_file)
        try:
            with open(sysinfo_path, 'r') as sysinfo_file:
                sysinfo_contents = sysinfo_file.read()
        except OSError, details:
            sysinfo_contents = "Error reading %s: %s" % (sysinfo_path, details)
        except IOError, details:
            sysinfo_contents = os.uname()[1]
        return sysinfo_contents

    def hostname(self):
        return self._get_sysinfo('hostname')

    @property
    def tests(self):
        mapping = {"TEST_NA": "warning",
                   "ABORT": "danger",
                   "ERROR": "danger",
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
            t['logdir'] = os.path.join(self._results_dir(
                                       relative_links=self.relative_links),
                                       'test-results', t['logdir'])
            t['logfile'] = os.path.join(self._results_dir(
                                        relative_links=self.relative_links),
                                        'test-results', t['logdir'],
                                        'debug.log')
            t['logfile_basename'] = os.path.basename(t['logfile'])
            t['time'] = "%.2f" % t['time']
            t['time_start'] = time.strftime("%Y-%m-%d %H:%M:%S",
                                            time.localtime(t['time_start']))
            t['row_class'] = mapping[t['status']]
            exhibition_limit = 40
            if len(t['fail_reason']) > exhibition_limit:
                t['fail_reason'] = ('<a data-container="body" '
                                    'data-toggle="popover" '
                                    'data-placement="top" '
                                    'title="Error Details" '
                                    'data-content="%s">%s...</a>' %
                                    (t['fail_reason'],
                                     t['fail_reason'][:exhibition_limit]))
        return test_info

    def sysinfo(self):
        sysinfo_list = []
        base_path = os.path.join(self._results_dir(relative_links=False),
                                 'sysinfo', 'pre')
        try:
            sysinfo_files = os.listdir(base_path)
        except OSError:
            return sysinfo_list
        sysinfo_files.sort()
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
                sysinfo_dict[s_f] = ('Error reading sysinfo file %s' %
                                     sysinfo_path)
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
        self.output = getattr(self.args, 'html_output')
        self.args = args
        self.view = output.View(app_args=args)
        self.json = None

    def start_tests(self):
        """
        Called once before any tests are executed.
        """
        TestResult.start_tests(self)
        self.json = {'debuglog': self.stream.logfile,
                     'job_id': runtime.CURRENT_JOB.unique_id,
                     'tests': []}

    def end_test(self, state):
        """
        Called when the given test has been run.

        :param state: result of :class:`avocado.test.Test.get_state`.
        :type state: dict
        """
        TestResult.end_test(self, state)
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
             'logdir': state['logdir'],
             'logfile': state['logfile']
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
            'failures': len(self.failed),
            'skip': len(self.skipped),
            'time': self.total_time
        })
        self._render_report()

    def _render_report(self):
        if self.args is not None:
            relative_links = getattr(self.args, 'relative_links')
        else:
            relative_links = False

        context = ReportModel(json_input=self.json, html_output=self.output,
                              relative_links=relative_links)
        html = HTML()
        template = html.get_resource_path('templates', 'report.mustache')

        if hasattr(pystache, 'Renderer'):
            renderer = pystache.Renderer('utf-8', 'utf-8')
            report_contents = renderer.render(open(template, 'r').read(), context)
        else:
            from pystache import view
            v = view.View(open(template, 'r').read(), context)
            report_contents = v.render('utf8')
 
        static_basedir = html.get_resource_path('static')
        output_dir = os.path.dirname(os.path.abspath(self.output))
        utils_path.init_dir(output_dir)
        for resource_dir in os.listdir(static_basedir):
            res_dir = os.path.join(static_basedir, resource_dir)
            out_dir = os.path.join(output_dir, resource_dir)
            if os.path.exists(out_dir):
                shutil.rmtree(out_dir)
            shutil.copytree(res_dir, out_dir)
        with codecs.open(self.output, 'w', 'utf-8') as report_file:
            report_file.write(report_contents)

        if self.args is not None:
            if getattr(self.args, 'open_browser'):
                # if possible, put browser in separate process group, so
                # keyboard interrupts don't affect browser as well as Python
                setsid = getattr(os, 'setsid', None)
                if not setsid:
                    setsid = getattr(os, 'setpgrp', None)
                inout = file(os.devnull, "r+")
                cmd = ['xdg-open', self.output]
                subprocess.Popen(cmd, close_fds=True, stdin=inout, stdout=inout,
                                 stderr=inout, preexec_fn=setsid)


class HTML(plugin.Plugin):

    """
    HTML job report.
    """

    name = 'htmlresult'
    enabled = True

    def configure(self, parser):
        if HTML_REPORT_CAPABLE is False:
            self.enabled = False
            return
        self.parser = parser
        self.parser.runner.add_argument(
            '--html', type=str,
            dest='html_output',
            help=('Enable HTML output to the file where the result should be '
                  'written. The value - (output to stdout) is not supported '
                  'since not all HTML resources can be embedded into a '
                  'single file (page resources will be copied to the '
                  'output file dir)'))
        self.parser.runner.add_argument(
            '--relative-links',
            dest='relative_links',
            action='store_true',
            default=False,
            help=('On the HTML report, generate anchor links with relative '
                  'instead of absolute paths. Current: %s' % False))
        self.parser.runner.add_argument(
            '--open-browser',
            dest='open_browser',
            action='store_true',
            default=False,
            help='Open the generated report on your preferred browser. '
                 'This works even if --html was not explicitly passed, '
                 'since an HTML report is always generated on the job '
                 'results dir. Current: %s' % False)
        self.configured = True

    def activate(self, app_args):
        try:
            if app_args.html_output:
                if app_args.html_output == '-':
                    view = output.View(app_args=app_args)
                    view.notify(event='error',
                                msg='HTML to stdout not supported '
                                    '(not all HTML resources can be embedded '
                                    'on a single file)')
                    sys.exit(exit_codes.AVOCADO_JOB_FAIL)
                else:
                    self.parser.application.set_defaults(
                        html_result=HTMLTestResult)
        except AttributeError:
            pass
