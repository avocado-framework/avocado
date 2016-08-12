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
import time
import subprocess
import urllib

import pystache
import pkg_resources

from .result import Result


def check_resource_requirements():
    """
    Checks if necessary resource files to render the report are in place

    Currently, only the template file is looked for
    """
    return pkg_resources.resource_exists(
        'avocado.core',
        'resources/htmlresult/templates/report.mustache')


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

    def job_id(self):
        return self.result.job_unique_id

    def execution_time(self):
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

    def logdir(self):
        logdir = os.path
        path = os.path.relpath(self.result.logdir,
                               self.html_output_dir)
        return urllib.quote(path)

    def total(self):
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
                   "INTERRUPTED": "danger"}
        test_info = []
        results_dir = self.results_dir(False)
        for tst in self.result.tests:
            tst = tst.copy()    # we don't want to override other's results
            tst["test"] = str(tst["name"])
            logdir = os.path.join(results_dir, 'test-results', tst['logdir'])
            tst['logdir'] = os.path.relpath(logdir, self.html_output_dir)
            logfile = os.path.join(logdir, 'debug.log')
            tst['logfile'] = os.path.relpath(logfile, self.html_output_dir)
            tst['logfile_basename'] = os.path.basename(logfile)
            tst['time'] = "%.2f" % tst['time_elapsed']
            tst['time_start'] = time.strftime("%Y-%m-%d %H:%M:%S",
                                              time.localtime(tst['time_start']))
            tst['row_class'] = mapping[tst['status']]
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
                               ('fail_reason',
                                'fail_reason'[:exhibition_limit]))
            tst['fail_reason'] = fail_reason
            test_info.append(tst)
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


class HTMLResult(Result):

    """
    HTML Test Result class.
    """

    def __init__(self, job, force_html_file=None):
        """
        :param job: Job which defines this result
        :param force_html_file: Override the output html file location
        """
        Result.__init__(self, job)
        if force_html_file:
            self.output = force_html_file
        else:
            self.output = self.args.html_output

    def end_tests(self):
        """
        Called once after all tests are executed.
        """
        Result.end_tests(self)
        self._render_report()

    def _copy_static_resources(self):
        module = 'avocado.core'
        base_path = 'resources/htmlresult/static'

        for top_dir in pkg_resources.resource_listdir(module, base_path):
            rsrc_dir = base_path + '/%s' % top_dir
            if pkg_resources.resource_isdir(module, rsrc_dir):
                rsrc_files = pkg_resources.resource_listdir(module, rsrc_dir)
                for rsrc_file in rsrc_files:
                    source = pkg_resources.resource_filename(
                        module,
                        rsrc_dir + '/%s' % rsrc_file)
                    dest = os.path.join(
                        os.path.dirname(os.path.abspath(self.output)),
                        top_dir,
                        os.path.basename(source))
                    pkg_resources.ensure_directory(dest)
                    shutil.copy(source, dest)

    def _render_report(self):
        context = ReportModel(result=self,
                              html_output=self.output)
        template = pkg_resources.resource_string(
            'avocado.core',
            'resources/htmlresult/templates/report.mustache')

        # pylint: disable=E0611
        try:
            if hasattr(pystache, 'Renderer'):
                renderer = pystache.Renderer('utf-8', 'utf-8')
                report_contents = renderer.render(template, context)
            else:
                from pystache import view
                v = view.View(template, context)
                report_contents = v.render('utf8')  # encodes into ascii
                report_contents = codecs.decode("utf8")  # decode to unicode
        except UnicodeDecodeError as details:
            # FIXME: Removeme when UnicodeDecodeError problem is fixed
            import logging
            ui = logging.getLogger("avocado.app")
            ui.critical("\n" + ("-" * 80))
            ui.critical("HTML failed to render the template: %s\n\n",
                        template)
            ui.critical("-" * 80)
            ui.critical("%s:\n\n", details)
            ui.critical("%r", getattr(details, "object", "object not found"))
            ui.critical("-" * 80)
            raise

        self._copy_static_resources()
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
