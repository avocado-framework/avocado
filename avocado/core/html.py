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
import urllib

import pystache

from .result import TestResult
from ..utils import path as utils_path
from ..utils import runtime


def check_resource_requirements():
    """
    Checks if necessary resource files to render the report are in place

    Currently, only the template file is looked for
    """
    base_path = os.path.dirname(sys.modules[__name__].__file__)
    html_resources_path = os.path.join(base_path, 'resources', 'htmlresult')
    template = os.path.join(html_resources_path, 'templates', 'report.mustache')
    return os.path.exists(template)


class ReportModel(object):

    """
    Prepares JSON that can be passed up to mustache for rendering.
    """

    def __init__(self, json_input, html_output):
        """
        Base JSON that comes from test results.
        """
        self.json = json_input
        self.html_output = html_output
        self.html_output_dir = os.path.abspath(os.path.dirname(html_output))

    def update(self, **kwargs):
        """
        Hook for updates not supported
        """
        pass

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

    def results_dir(self, relative_links=True):
        results_dir = os.path.abspath(os.path.dirname(self.json['debuglog']))
        if relative_links:
            return os.path.relpath(results_dir, self.html_output_dir)
        else:
            return results_dir

    def results_dir_basename(self):
        return os.path.basename(self.results_dir(False))

    def logdir(self):
        return os.path.relpath(self.json['logdir'], self.html_output_dir)

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
        sysinfo_path = os.path.join(self.results_dir(False),
                                    'sysinfo', 'pre', sysinfo_file)
        try:
            with open(sysinfo_path, 'r') as sysinfo_file:
                sysinfo_contents = sysinfo_file.read()
        except OSError as details:
            sysinfo_contents = "Error reading %s: %s" % (sysinfo_path, details)
        except IOError as details:
            sysinfo_contents = os.uname()[1]
        return sysinfo_contents

    def hostname(self):
        return self._get_sysinfo('hostname').strip()

    @property
    def tests(self):
        mapping = {"SKIP": "warning",
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
        results_dir = self.results_dir(False)
        for t in test_info:
            logdir = os.path.join(results_dir, 'test-results', t['logdir'])
            t['logdir'] = os.path.relpath(logdir, self.html_output_dir)
            logfile = os.path.join(logdir, 'debug.log')
            t['logfile'] = os.path.relpath(logfile, self.html_output_dir)
            t['logfile_basename'] = os.path.basename(logfile)
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

    def _sysinfo_phase(self, phase):
        """
        Returns a list of system information for a given sysinfo phase

        :param section: a valid sysinfo phase, such as pre, post or profile
        """
        sysinfo_list = []
        base_path = os.path.join(self.results_dir(False), 'sysinfo', phase)
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
                with codecs.open(sysinfo_path, 'r', encoding="utf-8") as sysinfo_file:
                    sysinfo_dict['file'] = " ".join(s_f.split("_"))
                    sysinfo_dict['contents'] = sysinfo_file.read()
                    sysinfo_dict['element_id'] = '%s_heading_%s' % (phase, s_id)
                    sysinfo_dict['collapse_id'] = '%s_collapse_%s' % (phase, s_id)
            except OSError:
                sysinfo_dict[s_f] = ('Error reading sysinfo file %s' %
                                     sysinfo_path)
            sysinfo_list.append(sysinfo_dict)
            s_id += 1
        return sysinfo_list

    def sysinfo_pre(self):
        return self._sysinfo_phase('pre')

    def sysinfo_profile(self):
        return self._sysinfo_phase('profile')

    def sysinfo_post(self):
        return self._sysinfo_phase('post')


class HTMLTestResult(TestResult):

    """
    HTML Test Result class.
    """

    command_line_arg_name = '--html'

    def __init__(self, job, force_html_file=None):
        """
        :param job: Job which defines this result
        :param force_html_file: Override the output html file location
        """
        TestResult.__init__(self, job)
        if force_html_file:
            self.output = force_html_file
        else:
            self.output = self.args.html_output
        self.json = None

    def start_tests(self):
        """
        Called once before any tests are executed.
        """
        TestResult.start_tests(self)
        self.json = {'debuglog': self.logfile,
                     'job_id': runtime.CURRENT_JOB.unique_id,
                     'tests': []}

    def end_test(self, state):
        """
        Called when the given test has been run.

        :param state: result of :class:`avocado.core.test.Test.get_state`.
        :type state: dict
        """
        TestResult.end_test(self, state)
        t = {'test': str(state.get('name', "<unknown>")),
             'url': state.get('name', "<unknown>"),
             'time_start': state.get('time_start', -1),
             'time_end': state.get('time_end', -1),
             'time': state.get('time_elapsed', -1),
             'status': state.get('status', "ERROR"),
             'fail_reason': str(state.get('fail_reason', "<unknown>")),
             'whiteboard': state.get('whiteboard', "<unknown>"),
             'logdir': urllib.quote(state.get('logdir', "<unknown>")),
             'logfile': urllib.quote(state.get('logfile', "<unknown>"))
             }
        self.json['tests'].append(t)

    def end_tests(self):
        """
        Called once after all tests are executed.
        """
        TestResult.end_tests(self)
        self.json.update({
            'total': len(self.json['tests']),
            'pass': self.passed,
            'errors': self.errors,
            'failures': self.failed,
            'skip': self.skipped,
            'time': self.total_time
        })
        self._render_report()

    def _render_report(self):
        context = ReportModel(json_input=self.json, html_output=self.output)
        base_path = os.path.dirname(sys.modules[__name__].__file__)
        html_resources_path = os.path.join(base_path, 'resources', 'htmlresult')
        template = os.path.join(html_resources_path, 'templates', 'report.mustache')

        # pylint: disable=E0611
        try:
            if hasattr(pystache, 'Renderer'):
                renderer = pystache.Renderer('utf-8', 'utf-8')
                report_contents = renderer.render(open(template, 'r').read(), context)
            else:
                from pystache import view
                v = view.View(open(template, 'r').read(), context)
                report_contents = v.render('utf8')  # encodes into ascii
                report_contents = codecs.decode("utf8")  # decode to unicode
        except UnicodeDecodeError as details:
            # FIXME: Removeme when UnicodeDecodeError problem is fixed
            import logging
            ui = logging.getLogger("avocado.app")
            ui.critical("\n" + ("-" * 80))
            ui.critical("HTML failed to render the template: %s\n\n",
                        open(template, 'r').read())
            ui.critical("-" * 80)
            ui.critical("%s:\n\n", details)
            ui.critical("%r\n\n", self.json)
            ui.critical("%r", getattr(details, "object", "object not found"))
            ui.critical("-" * 80)
            raise

        static_basedir = os.path.join(html_resources_path, 'static')
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
            if getattr(self.args, 'open_browser', False):
                # if possible, put browser in separate process group, so
                # keyboard interrupts don't affect browser as well as Python
                setsid = getattr(os, 'setsid', None)
                if not setsid:
                    setsid = getattr(os, 'setpgrp', None)
                inout = file(os.devnull, "r+")
                cmd = ['xdg-open', self.output]
                subprocess.Popen(cmd, close_fds=True, stdin=inout, stdout=inout,
                                 stderr=inout, preexec_fn=setsid)
