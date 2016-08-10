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
# Copyright: Red Hat Inc. 2016
# Author: Amador Pahim <apahim@redhat.com>

"""
Job Diff
"""

from __future__ import absolute_import
import argparse
import difflib
import json
import logging
import os
import subprocess
import sys
import tempfile

from avocado.core import exit_codes
from avocado.core import replay
from avocado.core import output

from avocado.core.plugin_interfaces import CLICmd
from avocado.core.settings import settings


LOG = logging.getLogger("avocado.app")


class HtmlDiff(difflib.HtmlDiff):
    """
    Override class to customize the diff page legends.
    """
    _legend = """
    <table class="diff" summary="Legends">
        <tr> <td> <table border="" summary="Colors">
                      <tr><th> Colors </th> </tr>
                      <tr><td class="diff_add">&nbsp;Added&nbsp;</td></tr>
                      <tr><td class="diff_chg">Changed</td> </tr>
                      <tr><td class="diff_sub">Deleted</td> </tr>
                  </table></td>
             <td> <table border="" summary="Links">
                      <tr><th colspan="2"> Links </th> </tr>
                      <tr><td>(f)irst change</td> </tr>
                      <tr><td>(n)ext change</td> </tr>
                      <tr><td>(t)op</td> </tr>
                  </table></td> </tr>
    </table>"""


class Diff(CLICmd):

    """
    Implements the avocado 'diff' subcommand
    """

    name = 'diff'
    description = 'Shows the difference between 2 jobs.'

    def configure(self, parser):
        """
        Add the subparser for the diff action.

        :param parser: Main test runner parser.
        """
        parser = super(Diff, self).configure(parser)

        parser.add_argument("jobids",
                            default=[], nargs=2,
                            metavar="<JOB_ID>",
                            help='Provide two Job IDs to compare.')

        parser.add_argument('--html',
                            action='store_true',
                            default=False,
                            help='Generate a HTML report file. '
                            'Current: False.')

        parser.add_argument('--open-browser',
                            action='store_true',
                            default=False,
                            help='Generate and open a HTML report in your '
                            'preferred browser. Current: False.')

        parser.add_argument('--diff-filter',
                            dest='diff_filter',
                            type=self._validate_filters,
                            default=['all'],
                            help='Diff filter: all,(-)cmdline,(-)time,'
                            '(-)variants,(-)results,(-)config,(-)sysinfo '
                            '(defaults to all).')

        self.term = output.TERM_SUPPORT

    def run(self, args):
        job1_dir, job1_id = self._setup_job(args.jobids[0])
        job2_dir, job2_id = self._setup_job(args.jobids[1])

        job1_data = self._get_job_data(job1_dir)
        job2_data = self._get_job_data(job2_dir)

        job1_results = []
        job2_results = []

        if (('all' in args.diff_filter or 'cmdline' in args.diff_filter) and
           '-cmdline' not in args.diff_filter):

            cmdline1 = self._get_command_line(job1_dir)
            cmdline2 = self._get_command_line(job2_dir)

            if self._has_diff([cmdline1], [cmdline2]):
                command_line_header = ['\n', 'COMMAND LINE\n']
                job1_results.extend(command_line_header)
                job1_results.append(cmdline1)
                job2_results.extend(command_line_header)
                job2_results.append(cmdline2)

        if (('all' in args.diff_filter or 'time' in args.diff_filter) and
           '-time' not in args.diff_filter):

            time1 = '%s (secs)\n' % job1_data['time']
            time2 = '%s (secs)\n' % job2_data['time']

            if self._has_diff([time1], [time2]):
                total_time_header = ['\n', 'TOTAL TIME\n']
                job1_results.extend(total_time_header)
                job1_results.append(time1)
                job2_results.extend(total_time_header)
                job2_results.append(time2)

        if (('all' in args.diff_filter or 'variants' in args.diff_filter) and
           '-variants' not in args.diff_filter):

            variants1 = self._get_variants(job1_dir)
            variants2 = self._get_variants(job2_dir)

            if self._has_diff(variants1, variants2):
                variants_header = ['\n', 'VARIANTS\n']
                job1_results.extend(variants_header)
                job1_results.extend(variants1)
                job2_results.extend(variants_header)
                job2_results.extend(variants2)

        if (('all' in args.diff_filter or 'results' in args.diff_filter) and
           '-results' not in args.diff_filter):

            results1 = []
            for test in job1_data['tests']:
                test_result = '%s: %s\n' % (test['url'], test['status'])
                results1.append(test_result)
            results2 = []
            for test in job2_data['tests']:
                test_result = '%s: %s\n' % (test['url'], test['status'])
                results2.append(test_result)

            if self._has_diff(results1, results2):
                test_results_header = ['\n', 'TEST RESULTS\n']
                job1_results.extend(test_results_header)
                job1_results.extend(results1)
                job2_results.extend(test_results_header)
                job2_results.extend(results2)

        if (('all' in args.diff_filter or 'config' in args.diff_filter) and
           '-config' not in args.diff_filter):

            config1 = self._get_config(job1_dir)
            config2 = self._get_config(job2_dir)

            if self._has_diff(config1, config2):
                config_header = ['\n', 'AVOCADO SETTINGS\n']
                job1_results.extend(config_header)
                job1_results.extend(config1)
                job2_results.extend(config_header)
                job2_results.extend(config2)

        if (('all' in args.diff_filter or 'sysinfo' in args.diff_filter) and
           '-sysinfo' not in args.diff_filter):

            sysinfo_pre1 = self._get_sysinfo(job1_dir, 'pre')
            sysinfo_pre2 = self._get_sysinfo(job2_dir, 'pre')

            if self._has_diff(sysinfo_pre1, sysinfo_pre2):
                sysinfo_header_pre = ['\n', 'SYSINFO PRE\n']
                job1_results.extend(sysinfo_header_pre)
                job1_results.extend(sysinfo_pre1)
                job2_results.extend(sysinfo_header_pre)
                job2_results.extend(sysinfo_pre2)

            sysinfo_post1 = self._get_sysinfo(job1_dir, 'post')
            sysinfo_post2 = self._get_sysinfo(job2_dir, 'post')

            if self._has_diff(sysinfo_post1, sysinfo_post2):
                sysinfo_header_post = ['\n', 'SYSINFO POST\n']
                job1_results.extend(sysinfo_header_post)
                job1_results.extend(sysinfo_post1)
                job2_results.extend(sysinfo_header_post)
                job2_results.extend(sysinfo_post2)

        job_diff = difflib.unified_diff(job1_results,
                                        job2_results,
                                        fromfile=job1_id,
                                        tofile=job2_id)
        if self.term.enabled:
            job_diff = self._color_diff(job_diff)
        sys.stdout.writelines(job_diff)

        if getattr(args, 'open_browser', False):
            setattr(args, 'html', True)

        if getattr(args, 'html', False):
            job_diff_html = HtmlDiff().make_file(job1_results,
                                                 job2_results,
                                                 fromdesc=job1_id,
                                                 todesc=job2_id)
            prefix = 'avocado_diff_%s_%s_' % (job1_id[:7], job2_id[:7])
            with tempfile.NamedTemporaryFile("w",
                                             prefix=prefix,
                                             suffix='.html',
                                             delete=False) as tmp_file:
                tmp_file.writelines(job_diff_html)
            sys.stdout.write('\n--\n%s\n' % tmp_file.name)

        if getattr(args, 'open_browser', False):
            setsid = getattr(os, 'setsid', None)
            if not setsid:
                setsid = getattr(os, 'setpgrp', None)
            inout = file(os.devnull, "r+")
            cmd = ['xdg-open', tmp_file.name]
            subprocess.Popen(cmd, close_fds=True, stdin=inout, stdout=inout,
                             stderr=inout, preexec_fn=setsid)

    def _validate_filters(self, string):
        diff_filters = string.split(',')
        valid_filters = ['all',
                         'cmdline',
                         '-cmdline',
                         'time',
                         '-time',
                         'variants',
                         '-variants',
                         'results',
                         '-results',
                         'config',
                         '-config',
                         'sysinfo',
                         '-sysinfo']
        add_all = False
        for diff_filter in diff_filters:
            if diff_filter in valid_filters:
                if diff_filter.startswith('-') and 'all' not in diff_filters:
                    add_all = True
            else:
                msg = "Invalid option '%s'" % diff_filter
                raise argparse.ArgumentTypeError(msg)

        if add_all:
            diff_filters.append('all')

        return diff_filters

    def _get_job_data(self, jobdir):
        results_json = os.path.join(jobdir, 'results.json')
        with open(results_json, 'r') as f:
            data = json.load(f)

        return data

    def _setup_job(self, job_id, job_data=None):
        if job_data is not None:
            resultsdir = job_data
        else:
            logs_dir = settings.get_value('datadir.paths', 'logs_dir',
                                          default=None)
            logdir = os.path.expanduser(logs_dir)
            resultsdir = replay.get_resultsdir(logdir, job_id)

        if resultsdir is None:
            LOG.error("Can't find job results directory for '%s' in '%s'",
                      job_id, logdir)
            sys.exit(exit_codes.AVOCADO_FAIL)

        sourcejob = replay.get_id(os.path.join(resultsdir, 'id'), job_id)
        if sourcejob is None:
            msg = ("Can't find matching job id '%s' in '%s' directory."
                   % (job_id, resultsdir))
            LOG.error(msg)
            sys.exit(exit_codes.AVOCADO_FAIL)

        return resultsdir, sourcejob

    def _get_command_line(self, resultsdir):
        command_line = replay.retrieve_cmdline(resultsdir)
        if command_line is not None:
            return '%s\n' % ' '.join(command_line)

        return 'Not found\n'

    def _get_variants(self, resultsdir):
        results = []
        mux = replay.retrieve_mux(resultsdir)
        if mux is not None:
            env = set()
            for (index, tpl) in enumerate(mux.variants):
                paths = ', '.join([x.path for x in tpl])
                results.append('Variant %s: %s\n' % (index + 1, paths))
                for node in tpl:
                    for key, value in node.environment.iteritems():
                        origin = node.environment_origin[key].path
                        env.add(("%s:%s" % (origin, key), str(value)))
                if not env:
                    continue
                fmt = '    %%-%ds => %%s\n' % max([len(_[0]) for _ in env])
                for record in sorted(env):
                    results.append(fmt % record)
        else:
            results.append('Not found\n')

        return results

    def _get_config(self, resultsdir):
        config_file = os.path.join(resultsdir, 'replay', 'config')
        try:
            with open(config_file, 'r') as f:
                return f.readlines()
        except:
            return ['Not found\n']

    def _get_sysinfo(self, resultsdir, pre_post):
        sysinfo_dir = os.path.join(resultsdir, 'sysinfo', pre_post)
        sysinfo = []
        for path, subdirs, files in os.walk(sysinfo_dir):
            for name in files:
                name_header = ['\n', '**%s**\n' % name]
                sysinfo.extend(name_header)
                with open(os.path.join(path, name), 'r') as f:
                    sysinfo.extend(f.readlines())

        return sysinfo

    def _color_diff(self, diff):
        for line in diff:
            if line.startswith('+'):
                yield self.term.COLOR_GREEN + line + self.term.ENDC
            elif line.startswith('-'):
                yield self.term.COLOR_RED + line + self.term.ENDC
            elif line.startswith('@'):
                yield self.term.COLOR_BLUE + line + self.term.ENDC
            else:
                yield line

    def _has_diff(self, a, b):
        # This ugly line checks if the diff has any actual difference
        if sum(1 for _ in difflib.ndiff(a, b)
               if _.startswith('-') or _.startswith('+')) > 0:
            return True
        return False
