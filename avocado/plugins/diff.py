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
import json
import os
import subprocess
import sys
import tempfile

from difflib import unified_diff, HtmlDiff

from avocado.core import exit_codes
from avocado.core import jobdata
from avocado.core import output

from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLICmd
from avocado.core.settings import settings


class Diff(CLICmd):

    """
    Implements the avocado 'diff' subcommand
    """

    name = 'diff'
    description = 'Shows the difference between 2 jobs.'

    def __init__(self):
        self.term = output.TERM_SUPPORT
        self.std_diff_output = True

    def configure(self, parser):
        """
        Add the subparser for the diff action.

        :param parser: Main test runner parser.
        """
        parser = super(Diff, self).configure(parser)

        parser.add_argument("jobids",
                            default=[], nargs=2,
                            metavar="<JOB>",
                            help='A job reference, identified by a (partial) '
                            'unique ID (SHA1) or test results directory.')

        parser.add_argument('--html', type=str,
                            metavar='FILE',
                            help='Enable HTML output to the FILE where the '
                            'result should be written.')

        parser.add_argument('--open-browser',
                            action='store_true',
                            default=False,
                            help='Generate and open a HTML report in your '
                            'preferred browser. If no --html file is '
                            'provided, create a temporary file.')

        parser.add_argument('--diff-filter',
                            dest='diff_filter',
                            type=self._validate_filters,
                            default=['cmdline', 'time', 'variants',
                                     'results', 'config', 'sysinfo'],
                            help='Comma separated filter of diff sections: '
                            '(no)cmdline,(no)time,(no)variants,(no)results,\n'
                            '(no)config,(no)sysinfo (defaults to all '
                            'enabled).')

        parser.add_argument('--paginator',
                            choices=('on', 'off'), default='on',
                            help='Turn the paginator on/off. '
                            'Current: %(default)s')

        parser.add_argument('--create-reports', action='store_true',
                            help='Create temporary files with job reports '
                            '(to be used by other diff tools)')

        parser.epilog = 'By default, a textual diff report is generated '\
                        'in the standard output.'

    def run(self, args):
        job1_dir, job1_id = self._setup_job(args.jobids[0])
        job2_dir, job2_id = self._setup_job(args.jobids[1])

        job1_data = self._get_job_data(job1_dir)
        job2_data = self._get_job_data(job2_dir)

        report_header = 'Avocado Job Report\n'
        job1_results = [report_header]
        job2_results = [report_header]

        if 'cmdline' in args.diff_filter:
            cmdline1 = self._get_command_line(job1_dir)
            cmdline2 = self._get_command_line(job2_dir)

            if str(cmdline1) != str(cmdline2):
                command_line_header = ['\n',
                                       '# COMMAND LINE\n']
                job1_results.extend(command_line_header)
                job1_results.append(cmdline1)
                job2_results.extend(command_line_header)
                job2_results.append(cmdline2)

        if 'time' in args.diff_filter:
            time1 = '%.2f s\n' % job1_data['time']
            time2 = '%.2f s\n' % job2_data['time']

            if str(time1) != str(time2):
                total_time_header = ['\n',
                                     '# TOTAL TIME\n']
                job1_results.extend(total_time_header)
                job1_results.append(time1)
                job2_results.extend(total_time_header)
                job2_results.append(time2)

        if 'variants' in args.diff_filter:
            variants1 = self._get_variants(job1_dir)
            variants2 = self._get_variants(job2_dir)

            if str(variants1) != str(variants2):
                variants_header = ['\n',
                                   '# VARIANTS\n']
                job1_results.extend(variants_header)
                job1_results.extend(variants1)
                job2_results.extend(variants_header)
                job2_results.extend(variants2)

        if 'results' in args.diff_filter:
            results1 = []
            for test in job1_data['tests']:
                test_result = '%s: %s\n' % (str(test['url']),
                                            str(test['status']))
                results1.append(test_result)
            results2 = []
            for test in job2_data['tests']:
                test_result = '%s: %s\n' % (str(test['url']),
                                            str(test['status']))
                results2.append(test_result)

            if str(results1) != str(results2):
                test_results_header = ['\n',
                                       '# TEST RESULTS\n']
                job1_results.extend(test_results_header)
                job1_results.extend(results1)
                job2_results.extend(test_results_header)
                job2_results.extend(results2)

        if 'config' in args.diff_filter:
            config1 = self._get_config(job1_dir)
            config2 = self._get_config(job2_dir)

            if str(config1) != str(config2):
                config_header = ['\n',
                                 '# SETTINGS\n']
                job1_results.extend(config_header)
                job1_results.extend(config1)
                job2_results.extend(config_header)
                job2_results.extend(config2)

        if 'sysinfo' in args.diff_filter:
            sysinfo_pre1 = self._get_sysinfo(job1_dir, 'pre')
            sysinfo_pre2 = self._get_sysinfo(job2_dir, 'pre')

            if str(sysinfo_pre1) != str(sysinfo_pre2):
                sysinfo_header_pre = ['\n',
                                      '# SYSINFO PRE\n']
                job1_results.extend(sysinfo_header_pre)
                job1_results.extend(sysinfo_pre1)
                job2_results.extend(sysinfo_header_pre)
                job2_results.extend(sysinfo_pre2)

            sysinfo_post1 = self._get_sysinfo(job1_dir, 'post')
            sysinfo_post2 = self._get_sysinfo(job2_dir, 'post')

            if str(sysinfo_post1) != str(sysinfo_post2):
                sysinfo_header_post = ['\n',
                                       '# SYSINFO POST\n']
                job1_results.extend(sysinfo_header_post)
                job1_results.extend(sysinfo_post1)
                job2_results.extend(sysinfo_header_post)
                job2_results.extend(sysinfo_post2)

        if getattr(args, 'create_reports', False):
            self.std_diff_output = False
            prefix = 'avocado_diff_%s_' % job1_id[:7]
            tmp_file1 = tempfile.NamedTemporaryFile(prefix=prefix,
                                                    suffix='.txt',
                                                    delete=False)
            tmp_file1.writelines(job1_results)
            tmp_file1.close()

            prefix = 'avocado_diff_%s_' % job2_id[:7]
            tmp_file2 = tempfile.NamedTemporaryFile(prefix=prefix,
                                                    suffix='.txt',
                                                    delete=False)
            tmp_file2.writelines(job2_results)
            tmp_file2.close()

            LOG_UI.info('%s %s', tmp_file1.name, tmp_file2.name)

        if (getattr(args, 'open_browser', False) and
                getattr(args, 'html', None) is None):

            prefix = 'avocado_diff_%s_%s_' % (job1_id[:7], job2_id[:7])
            tmp_file = tempfile.NamedTemporaryFile(prefix=prefix,
                                                   suffix='.html',
                                                   delete=False)

            setattr(args, 'html', tmp_file.name)

        if getattr(args, 'html', None) is not None:
            self.std_diff_output = False
            try:
                html_diff = HtmlDiff()
                html_diff._legend = """
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

                job_diff_html = html_diff.make_file((_.decode("utf-8")
                                                     for _ in job1_results),
                                                    (_.decode("utf-8")
                                                     for _ in job2_results),
                                                    fromdesc=job1_id,
                                                    todesc=job2_id)

                with open(args.html, 'w') as html_file:
                    html_file.writelines(job_diff_html.encode("utf-8"))

                LOG_UI.info(args.html)

            except IOError as exception:
                LOG_UI.error(exception)
                sys.exit(exit_codes.AVOCADO_FAIL)

        if getattr(args, 'open_browser', False):
            setsid = getattr(os, 'setsid', None)
            if not setsid:
                setsid = getattr(os, 'setpgrp', None)
            with open(os.devnull, "r+") as inout:
                cmd = ['xdg-open', args.html]
                subprocess.Popen(cmd, close_fds=True, stdin=inout,
                                 stdout=inout, stderr=inout,
                                 preexec_fn=setsid)

        if self.std_diff_output:
            if self.term.enabled:
                for line in self._cdiff(unified_diff(job1_results,
                                                     job2_results,
                                                     fromfile=job1_id,
                                                     tofile=job2_id)):
                    LOG_UI.debug(line.strip())
            else:
                for line in unified_diff(job1_results,
                                         job2_results,
                                         fromfile=job1_id,
                                         tofile=job2_id):
                    LOG_UI.debug(line.strip())

    @staticmethod
    def _validate_filters(string):
        input_filter = set(string.split(','))
        include_options = ["cmdline",
                           "time",
                           "variants",
                           "results",
                           "config",
                           "sysinfo"]
        exclude_options = ["nocmdline",
                           "notime",
                           "novariants",
                           "noresults",
                           "noconfig",
                           "nosysinfo"]
        invalid = input_filter.difference(include_options +
                                          exclude_options + ["all"])
        if invalid:
            msg = "Invalid option(s) '%s'" % ','.join(invalid)
            raise argparse.ArgumentTypeError(msg)
        if input_filter.intersection(exclude_options):
            output_filter = [_ for _ in include_options
                             if ("no" + _) not in input_filter]
        elif "all" in input_filter:
            output_filter = include_options
        else:
            output_filter = input_filter

        return output_filter

    @staticmethod
    def _get_job_data(jobdir):
        results_json = os.path.join(jobdir, 'results.json')
        with open(results_json, 'r') as json_file:
            data = json.load(json_file)

        return data

    @staticmethod
    def _setup_job(job_id):
        if os.path.isdir(job_id):
            resultsdir = os.path.expanduser(job_id)
            job_id = ''
        elif os.path.isfile(job_id):
            resultsdir = os.path.dirname(os.path.expanduser(job_id))
            job_id = ''
        else:
            logdir = settings.get_value(section='datadir.paths',
                                        key='logs_dir', key_type='path',
                                        default=None)
            try:
                resultsdir = jobdata.get_resultsdir(logdir, job_id)
            except ValueError as exception:
                LOG_UI.error(exception.message)
                sys.exit(exit_codes.AVOCADO_FAIL)

        if resultsdir is None:
            LOG_UI.error("Can't find job results directory for '%s' in '%s'",
                         job_id, logdir)
            sys.exit(exit_codes.AVOCADO_FAIL)

        sourcejob = jobdata.get_id(os.path.join(resultsdir, 'id'), job_id)
        if sourcejob is None:
            LOG_UI.error("Can't find matching job id '%s' in '%s' directory.",
                         job_id, resultsdir)
            sys.exit(exit_codes.AVOCADO_FAIL)

        return resultsdir, sourcejob

    @staticmethod
    def _get_command_line(resultsdir):
        command_line = jobdata.retrieve_cmdline(resultsdir)
        if command_line is not None:
            return '%s\n' % ' '.join(command_line)

        return 'Not found\n'

    @staticmethod
    def _get_variants(resultsdir):
        results = []
        variants = jobdata.retrieve_variants(resultsdir)
        if variants is not None:
            results.extend(variants.to_str(variants=2).splitlines())
        else:
            results.append('Not found\n')

        return results

    @staticmethod
    def _get_config(resultsdir):
        config_file = os.path.join(resultsdir, 'replay', 'config')
        try:
            with open(config_file, 'r') as conf:
                return conf.readlines()
        except IOError:
            return ['Not found\n']

    @staticmethod
    def _get_sysinfo(resultsdir, pre_post):
        sysinfo_dir = os.path.join(resultsdir, 'sysinfo', pre_post)
        sysinfo = []
        for path, _, files in os.walk(sysinfo_dir):
            for name in sorted(files):
                name_header = ['\n', '** %s **\n' % name]
                sysinfo.extend(name_header)
                with open(os.path.join(path, name), 'r') as sysinfo_file:
                    sysinfo.extend(sysinfo_file.readlines())

        if sysinfo:
            del sysinfo[0]

        return sysinfo

    def _cdiff(self, diff):
        for line in diff:
            if line.startswith('+'):
                yield self.term.COLOR_GREEN + line
            elif line.startswith('-'):
                yield self.term.COLOR_RED + line
            elif line.startswith('@'):
                yield self.term.COLOR_BLUE + line
            else:
                yield line
