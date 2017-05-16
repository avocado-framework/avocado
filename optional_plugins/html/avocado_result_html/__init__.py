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
import logging
import os
import shutil
import subprocess
import sys
import time

import pkg_resources
import pystache

from avocado.core import exit_codes
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLI, Result


class ReportModel(object):

    """
    Prepares an object that can be passed up to mustache for rendering.
    """

    def __init__(self, result, html_output):
        self.result = result
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

    def job_unique_id(self):
        return self.result.job_unique_id

    def tests_total_time(self):
        return "%.2f" % self.result.tests_total_time

    def results_dir(self, relative_links=True):
        results_dir = os.path.abspath(os.path.dirname(
            self.result.logfile))
        if relative_links:
            return os.path.relpath(results_dir, self.html_output_dir)
        else:
            return results_dir

    def results_dir_basename(self):
        return os.path.basename(self.results_dir(False))

    def tests_total(self):
        return self.result.tests_total

    def passed(self):
        return self.result.passed

    def pass_rate(self):
        total = float(self.result.tests_total)
        passed = float(self.result.passed)
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
                   "INTERRUPTED": "danger",
                   "CANCEL": "warning"}
        test_info = []
        results_dir = self.results_dir(False)
        for tst in self.result.tests:
            formatted = {}
            formatted['uid'] = tst['name'].uid
            formatted['name'] = tst['name'].name
            params = ''
            try:
                parameters = 'Params:\n'
                for path, key, value in tst['params'].iteritems():
                    parameters += '  %s:%s => %s\n' % (path, key, value)
            except KeyError:
                pass
            else:
                params = parameters
            formatted['params'] = params
            formatted['variant'] = tst['name'].variant or ''
            formatted['status'] = tst['status']
            logdir = os.path.join(results_dir, 'test-results', tst['logdir'])
            formatted['logdir'] = os.path.relpath(logdir, self.html_output_dir)
            logfile = os.path.join(logdir, 'debug.log')
            formatted['logfile'] = os.path.relpath(logfile,
                                                   self.html_output_dir)
            formatted['logfile_basename'] = os.path.basename(logfile)
            formatted['time'] = "%.2f" % tst['time_elapsed']
            local_time_start = time.localtime(tst['time_start'])
            formatted['time_start'] = time.strftime("%Y-%m-%d %H:%M:%S",
                                                    local_time_start)
            formatted['row_class'] = mapping[tst['status']]
            exhibition_limit = 40
            fail_reason = tst.get('fail_reason')
            if fail_reason is None:
                fail_reason = '<unknown>'
            fail_reason = str(fail_reason)
            if len(fail_reason) > exhibition_limit:
                fail_reason = ('<a data-container="body" '
                               'data-toggle="popover" '
                               'data-placement="top" '
                               'title="Error Details" '
                               'data-content="%s">%s...</a>' %
                               (fail_reason,
                                fail_reason[:exhibition_limit]))
            formatted['fail_reason'] = fail_reason
            test_info.append(formatted)
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
            sysinfo_dict['file'] = " ".join(s_f.split("_"))
            sysinfo_dict['element_id'] = '%s_heading_%s' % (phase, s_id)
            sysinfo_dict['collapse_id'] = '%s_collapse_%s' % (phase, s_id)
            try:
                with codecs.open(sysinfo_path, 'r',
                                 encoding="utf-8") as sysinfo_file:
                    sysinfo_dict['contents'] = sysinfo_file.read()
            except (OSError, UnicodeDecodeError) as details:
                path = os.path.relpath(sysinfo_path, self.html_output_dir)
                sysinfo_dict['err'] = ("Error reading sysinfo file, check out"
                                       "the file <a href=%s>%s</a>: %s"
                                       % (path, path, details))
            sysinfo_list.append(sysinfo_dict)
            s_id += 1
        return sysinfo_list

    def sysinfo_pre(self):
        return self._sysinfo_phase('pre')

    def sysinfo_profile(self):
        return self._sysinfo_phase('profile')

    def sysinfo_post(self):
        return self._sysinfo_phase('post')


class HTMLResult(Result):

    """
    HTML Test Result class.
    """

    name = 'html'
    description = 'HTML result support'

    @staticmethod
    def _copy_static_resources(html_path):
        module = 'avocado_result_html'
        base_path = 'resources/static'

        for top_dir in pkg_resources.resource_listdir(module, base_path):
            rsrc_dir = base_path + '/%s' % top_dir
            if pkg_resources.resource_isdir(module, rsrc_dir):
                rsrc_files = pkg_resources.resource_listdir(module, rsrc_dir)
                for rsrc_file in rsrc_files:
                    source = pkg_resources.resource_filename(
                        module,
                        rsrc_dir + '/%s' % rsrc_file)
                    dest = os.path.join(
                        os.path.dirname(os.path.abspath(html_path)),
                        top_dir,
                        os.path.basename(source))
                    pkg_resources.ensure_directory(dest)
                    shutil.copy(source, dest)

    @staticmethod
    def _open_browser(html_path):
        # if possible, put browser in separate process
        # group, so keyboard interrupts don't affect
        # browser as well as Python
        setsid = getattr(os, 'setsid', None)
        if not setsid:
            setsid = getattr(os, 'setpgrp', None)
        inout = file(os.devnull, "r+")
        cmd = ['xdg-open', html_path]
        subprocess.Popen(cmd, close_fds=True, stdin=inout,
                         stdout=inout, stderr=inout,
                         preexec_fn=setsid)

    def _render(self, result, output_path):
        context = ReportModel(result=result, html_output=output_path)
        template = pkg_resources.resource_string(
            'avocado_result_html',
            'resources/templates/report.mustache')

        # pylint: disable=E0611
        try:
            if hasattr(pystache, 'Renderer'):
                renderer = pystache.Renderer('utf-8', 'utf-8')
                report_contents = renderer.render(template, context)
            else:
                from pystache import view
                v = view.View(template, context)
                report_contents = v.render('utf8')
        except UnicodeDecodeError as details:
            # FIXME: Remove me when UnicodeDecodeError problem is fixed
            LOG_UI.critical("\n" + ("-" * 80))
            LOG_UI.critical("HTML failed to render the template: %s\n\n",
                            template)
            LOG_UI.critical("-" * 80)
            LOG_UI.critical("%s:\n\n", details)
            LOG_UI.critical("%r", getattr(details, "object",
                                          "object not found"))
            LOG_UI.critical("-" * 80)
            raise

        self._copy_static_resources(output_path)
        with codecs.open(output_path, 'w', 'utf-8') as report_file:
            report_file.write(report_contents)

    def render(self, result, job):
        if job.status == "RUNNING":
            return  # Don't create results on unfinished jobs
        if not (hasattr(job.args, 'html_job_result') or
                hasattr(job.args, 'html_output')):
            return

        open_browser = getattr(job.args, 'open_browser', False)
        if getattr(job.args, 'html_job_result', 'off') == 'on':
            html_dir = os.path.join(job.logdir, 'html')
            if os.path.exists(html_dir):    # update the html result if exists
                shutil.rmtree(html_dir)
            os.makedirs(html_dir)
            html_path = os.path.join(html_dir, 'results.html')
            self._render(result, html_path)
            if getattr(job.args, 'stdout_claimed_by', None) is None:
                LOG_UI.info("JOB HTML   : %s", html_path)
            if open_browser:
                self._open_browser(html_path)
                open_browser = False

        html_path = getattr(job.args, 'html_output', 'None')
        if html_path is not None:
            # Avoid removing static content in user-provided path as it might
            # also contain other user file/dirs (eg. "/tmp/report.html" would
            # otherwise delete "/tmp"
            self._render(result, html_path)
            if open_browser:
                self._open_browser(html_path)


class HTML(CLI):

    """
    HTML job report
    """

    name = 'htmlresult'
    description = "HTML job report options for 'run' subcommand"

    def configure(self, parser):
        run_subcommand_parser = parser.subcommands.choices.get('run', None)
        if run_subcommand_parser is None:
            return

        run_subcommand_parser.output.add_argument(
            '--html', type=str,
            dest='html_output', metavar='FILE',
            help=('Enable HTML output to the FILE where the result should be '
                  'written. The value - (output to stdout) is not supported '
                  'since not all HTML resources can be embedded into a '
                  'single file (page resources will be copied to the '
                  'output file dir)'))
        run_subcommand_parser.output.add_argument(
            '--open-browser',
            dest='open_browser',
            action='store_true',
            default=False,
            help='Open the generated report on your preferred browser. '
                 'This works even if --html was not explicitly passed, '
                 'since an HTML report is always generated on the job '
                 'results dir. Current: %s' % False)

        run_subcommand_parser.output.add_argument(
            '--html-job-result', dest='html_job_result',
            choices=('on', 'off'), default='on',
            help=('Enables default HTML result in the job results directory. '
                  'File will be located at "html/results.html".'))

    def run(self, args):
        if 'html_output' in args and args.html_output == '-':
            LOG_UI.error('HTML to stdout not supported (not all HTML resources'
                         ' can be embedded on a single file)')
            sys.exit(exit_codes.AVOCADO_JOB_FAIL)
