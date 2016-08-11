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
import logging
import os
import subprocess
import sys
import tempfile

from difflib import unified_diff, HtmlDiff

from avocado.core import exit_codes
from avocado.core import replay
from avocado.core import output

from avocado.core.plugin_interfaces import CLICmd
from avocado.core.settings import settings


LOG = logging.getLogger("avocado.app")


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
                            metavar="<JOB>",
                            help='Provide two Jobs, identified by their Job '
                            '(partial) ID or test results directory.')

        parser.add_argument('--html', type=str,
                            dest='html_output',
                            metavar='FILE',
                            help='Enable HTML output to the FILE where the '
                            'result should be written.')

        parser.add_argument('--open-browser',
                            action='store_true',
                            default=False,
                            help='Generate and open a HTML report in your '
                            'preferred browser. If no --html file is '
                            'provided, we create a temporary file. '
                            'Current: False.')

        parser.add_argument('--diff-filter',
                            dest='diff_filter',
                            type=self._validate_filters,
                            default=['all'],
                            help='Diff filter: (no)cmdline,(no)time,'
                            '(no)variants,(no)results,(no)config,(no)sysinfo '
                            '(defaults to all enabled).')

        parser.add_argument('--paginator',
                            choices=('on', 'off'), default='on',
                            help='Turn the paginator on/off. '
                            'Current: %(default)s')

        parser.add_argument('--create-reports', action='store_true',
                            help='Instead of show the diff using Avocado '
                            'Diff utility, create temporary files to use '
                            'in a custom diff tool.')

        self.term = output.TERM_SUPPORT
        self.std_diff_output = True

    def run(self, args):
        job1_dir, job1_id = self._setup_job(args.jobids[0])
        job2_dir, job2_id = self._setup_job(args.jobids[1])

        job1_data = self._get_job_data(job1_dir)
        job2_data = self._get_job_data(job2_dir)

        report_header = 'Avocado Job Report\n'
        job1_results = [report_header]
        job2_results = [report_header]

        if (('all' in args.diff_filter or 'cmdline' in args.diff_filter) and
           'nocmdline' not in args.diff_filter):

            cmdline1 = self._get_command_line(job1_dir)
            cmdline2 = self._get_command_line(job2_dir)

            if str(cmdline1) != str(cmdline2):
                command_line_header = ['\n',
                                       'COMMAND LINE\n',
                                       '============\n']
                job1_results.extend(command_line_header)
                job1_results.append(cmdline1)
                job2_results.extend(command_line_header)
                job2_results.append(cmdline2)

        if (('all' in args.diff_filter or 'time' in args.diff_filter) and
           'notime' not in args.diff_filter):

            time1 = '%.2f s\n' % job1_data['time']
            time2 = '%.2f s\n' % job2_data['time']

            if str(time1) != str(time2):
                total_time_header = ['\n',
                                     'TOTAL TIME\n',
                                     '==========\n']
                job1_results.extend(total_time_header)
                job1_results.append(time1)
                job2_results.extend(total_time_header)
                job2_results.append(time2)

        if (('all' in args.diff_filter or 'variants' in args.diff_filter) and
           'novariants' not in args.diff_filter):

            variants1 = self._get_variants(job1_dir)
            variants2 = self._get_variants(job2_dir)

            if str(variants1) != str(variants2):
                variants_header = ['\n',
                                   'VARIANTS\n',
                                   '========\n']
                job1_results.extend(variants_header)
                job1_results.extend(variants1)
                job2_results.extend(variants_header)
                job2_results.extend(variants2)

        if (('all' in args.diff_filter or 'results' in args.diff_filter) and
           'noresults' not in args.diff_filter):

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
                                       'TEST RESULTS\n',
                                       '============\n']
                job1_results.extend(test_results_header)
                job1_results.extend(results1)
                job2_results.extend(test_results_header)
                job2_results.extend(results2)

        if (('all' in args.diff_filter or 'config' in args.diff_filter) and
           'noconfig' not in args.diff_filter):

            config1 = self._get_config(job1_dir)
            config2 = self._get_config(job2_dir)

            if str(config1) != str(config2):
                config_header = ['\n',
                                 'SETTINGS\n',
                                 '========\n']
                job1_results.extend(config_header)
                job1_results.extend(config1)
                job2_results.extend(config_header)
                job2_results.extend(config2)

        if (('all' in args.diff_filter or 'sysinfo' in args.diff_filter) and
           'nosysinfo' not in args.diff_filter):

            sysinfo_pre1 = self._get_sysinfo(job1_dir, 'pre')
            sysinfo_pre2 = self._get_sysinfo(job2_dir, 'pre')

            if str(sysinfo_pre1) != str(sysinfo_pre2):
                sysinfo_header_pre = ['\n',
                                      'SYSINFO PRE\n',
                                      '===========\n']
                job1_results.extend(sysinfo_header_pre)
                job1_results.extend(sysinfo_pre1)
                job2_results.extend(sysinfo_header_pre)
                job2_results.extend(sysinfo_pre2)

            sysinfo_post1 = self._get_sysinfo(job1_dir, 'post')
            sysinfo_post2 = self._get_sysinfo(job2_dir, 'post')

            if str(sysinfo_post1) != str(sysinfo_post2):
                sysinfo_header_post = ['\n',
                                       'SYSINFO POST\n',
                                       '============\n']
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

            LOG.info('Job Reports: %s %s' % (tmp_file1.name, tmp_file2.name))

        if (getattr(args, 'open_browser', False) and
           getattr(args, 'html_output', None) is None):

            prefix = 'avocado_diff_%s_%s_' % (job1_id[:7], job2_id[:7])
            tmp_file = tempfile.NamedTemporaryFile(prefix=prefix,
                                                   suffix='.html',
                                                   delete=False)

            setattr(args, 'html_output', tmp_file.name)

        if getattr(args, 'html_output', None) is not None:
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

                with open(args.html_output, 'w') as f:
                    f.writelines(job_diff_html.encode("utf-8"))

                LOG.info('HTML diff file: %s' % args.html_output)

            except Exception as e:
                LOG.error(e)
                sys.exit(exit_codes.AVOCADO_FAIL)

        if getattr(args, 'open_browser', False):
            setsid = getattr(os, 'setsid', None)
            if not setsid:
                setsid = getattr(os, 'setpgrp', None)
            inout = file(os.devnull, "r+")
            cmd = ['xdg-open', args.html_output]
            subprocess.Popen(cmd, close_fds=True, stdin=inout, stdout=inout,
                             stderr=inout, preexec_fn=setsid)

        if self.std_diff_output:
            if self.term.enabled:
                for line in self._cdiff(unified_diff(job1_results,
                                                     job2_results,
                                                     fromfile=job1_id,
                                                     tofile=job2_id)):
                    LOG.debug(line.strip())
            else:
                for line in unified_diff(job1_results,
                                         job2_results,
                                         fromfile=job1_id,
                                         tofile=job2_id):
                    LOG.debug(line.strip())

    def _validate_filters(self, string):
        diff_filters = string.split(',')
        valid_filters = ['cmdline',
                         'nocmdline',
                         'time',
                         'notime',
                         'variants',
                         'novariants',
                         'results',
                         'noresults',
                         'config',
                         'noconfig',
                         'sysinfo',
                         'nosysinfo']
        add_all = False
        for diff_filter in diff_filters:
            if diff_filter in valid_filters:
                if diff_filter.startswith('no'):
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

    def _setup_job(self, job_id):
        if os.path.isdir(job_id):
            resultsdir = os.path.expanduser(job_id)
            job_id = ''
        elif os.path.isfile(job_id):
            resultsdir = os.path.dirname(os.path.expanduser(job_id))
            job_id = ''
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
            for name in sorted(files):
                name_header = ['\n', '**%s**\n' % name]
                sysinfo.extend(name_header)
                with open(os.path.join(path, name), 'r') as f:
                    sysinfo.extend(f.readlines())

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
