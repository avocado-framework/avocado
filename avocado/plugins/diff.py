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

import argparse
import json
import os
import subprocess
import sys
import tempfile
from difflib import HtmlDiff, unified_diff

from avocado.core import data_dir, exit_codes, jobdata, output
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLICmd
from avocado.core.settings import settings
from avocado.core.varianter import Varianter


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

        :param parser: The Avocado command line application parser
        :type parser: :class:`avocado.core.parser.ArgumentParser`
        """
        parser = super().configure(parser)

        parser.epilog = 'By default, a textual diff report is generated '\
                        'in the standard output.'

        help_msg = ('A job reference, identified by a (partial) unique ID '
                    '(SHA1) or test results directory.')
        settings.register_option(section='diff',
                                 key='jobids',
                                 default=[],
                                 key_type=list,
                                 nargs=2,
                                 help_msg=help_msg,
                                 parser=parser,
                                 metavar="JOB",
                                 positional_arg='jobids')

        help_msg = ('Enable HTML output to the FILE where the result should '
                    'be written.')
        settings.register_option(section='diff',
                                 key='html',
                                 default=None,
                                 metavar='FILE',
                                 help_msg=help_msg,
                                 parser=parser,
                                 long_arg='--html')

        help_msg = ('Generate and open a HTML report in your preferred '
                    'browser. If no --html file is provided, create a '
                    'temporary file.')
        settings.register_option(section='diff',
                                 key='open_browser',
                                 default=False,
                                 key_type=bool,
                                 help_msg=help_msg,
                                 parser=parser,
                                 long_arg='--open-browser')

        help_msg = ('Comma separated filter of diff sections: '
                    '(no)cmdline,(no)time,(no)variants,(no)results, '
                    '(no)config,(no)sysinfo (defaults to all enabled).')
        settings.register_option(section='diff',
                                 key='filter',
                                 metavar='DIFF_FILTER',
                                 key_type=self._validate_filters,
                                 help_msg=help_msg,
                                 default=['cmdline', 'time', 'variants',
                                          'results', 'config', 'sysinfo'],
                                 parser=parser,
                                 long_arg='--diff-filter')

        help_msg = ('Strip the "id" from "id-name;variant" when comparing '
                    'test results.')
        settings.register_option(section='diff',
                                 key='strip_id',
                                 default=False,
                                 key_type=bool,
                                 help_msg=help_msg,
                                 parser=parser,
                                 long_arg='--diff-strip-id')

        help_msg = ('Create temporary files with job reports to be used by '
                    'other diff tools')
        settings.register_option(section='diff',
                                 key='create_reports',
                                 default=False,
                                 key_type=bool,
                                 help_msg=help_msg,
                                 parser=parser,
                                 long_arg='--create-reports')

    def run(self, config):
        def _get_name(test):
            return str(test['id'])

        def _get_name_no_id(test):
            return str(test['id']).split('-', 1)[1]

        job1_dir, job1_id = self._setup_job(config.get('diff.jobids')[0])
        job2_dir, job2_id = self._setup_job(config.get('diff.jobids')[1])

        job1_data = self._get_job_data(job1_dir)
        job2_data = self._get_job_data(job2_dir)

        report_header = 'Avocado Job Report\n'
        job1_results = [report_header]
        job2_results = [report_header]

        diff_filter = config.get('diff.filter')
        if 'cmdline' in diff_filter:
            cmdline1 = self._get_command_line(job1_dir)
            cmdline2 = self._get_command_line(job2_dir)

            if str(cmdline1) != str(cmdline2):
                command_line_header = ['\n',
                                       '# COMMAND LINE\n']
                job1_results.extend(command_line_header)
                job1_results.append(cmdline1)
                job2_results.extend(command_line_header)
                job2_results.append(cmdline2)

        if 'time' in diff_filter:
            time1 = f"{job1_data['time']:.2f} s\n"
            time2 = f"{job2_data['time']:.2f} s\n"

            if str(time1) != str(time2):
                total_time_header = ['\n',
                                     '# TOTAL TIME\n']
                job1_results.extend(total_time_header)
                job1_results.append(time1)
                job2_results.extend(total_time_header)
                job2_results.append(time2)

        if 'variants' in diff_filter:
            variants1 = self._get_variants(job1_dir)
            variants2 = self._get_variants(job2_dir)

            if str(variants1) != str(variants2):
                variants_header = ['\n',
                                   '# VARIANTS\n']
                job1_results.extend(variants_header)
                job1_results.extend(variants1)
                job2_results.extend(variants_header)
                job2_results.extend(variants2)

        if 'results' in diff_filter:
            results1 = []
            if config.get('diff.strip_id'):
                get_name = _get_name_no_id
            else:
                get_name = _get_name
            for test in job1_data['tests']:
                test_result = f"{get_name(test)}: {str(test['status'])}\n"
                results1.append(test_result)
            results2 = []
            for test in job2_data['tests']:
                test_result = f"{get_name(test)}: {str(test['status'])}\n"
                results2.append(test_result)

            if str(results1) != str(results2):
                test_results_header = ['\n',
                                       '# TEST RESULTS\n']
                job1_results.extend(test_results_header)
                job1_results.extend(results1)
                job2_results.extend(test_results_header)
                job2_results.extend(results2)

        if 'config' in diff_filter:
            config1 = self._get_config(job1_dir)
            config2 = self._get_config(job2_dir)

            if str(config1) != str(config2):
                config_header = ['\n',
                                 '# SETTINGS\n']
                job1_results.extend(config_header)
                job1_results.extend(config1)
                job2_results.extend(config_header)
                job2_results.extend(config2)

        if 'sysinfo' in diff_filter:
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

        if config.get('diff.create_reports'):
            self.std_diff_output = False
            prefix = f'avocado_diff_{job1_id[:7]}_'
            tmp_file1 = tempfile.NamedTemporaryFile(mode='w',
                                                    prefix=prefix,
                                                    suffix='.txt',
                                                    delete=False)
            tmp_file1.writelines(job1_results)
            tmp_file1.close()

            prefix = f'avocado_diff_{job2_id[:7]}_'
            tmp_file2 = tempfile.NamedTemporaryFile(mode='w',
                                                    prefix=prefix,
                                                    suffix='.txt',
                                                    delete=False)
            tmp_file2.writelines(job2_results)
            tmp_file2.close()

            LOG_UI.info('%s %s', tmp_file1.name, tmp_file2.name)

        html_file = config.get('diff.html')
        open_browser = config.get('diff.open_browser')
        if open_browser and html_file is None:
            prefix = f'avocado_diff_{job1_id[:7]}_{job2_id[:7]}_'
            tmp_file = tempfile.NamedTemporaryFile(mode='w',
                                                   prefix=prefix,
                                                   suffix='.html',
                                                   delete=False)

            html_file = tmp_file.name

        if html_file is not None:
            self.std_diff_output = False
            try:
                html_diff = HtmlDiff()
                # pylint: disable=W0212
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

                job_diff_html = html_diff.make_file((_ for _ in job1_results),
                                                    (_ for _ in job2_results),
                                                    fromdesc=job1_id,
                                                    todesc=job2_id)

                with open(html_file, 'w', encoding='utf-8') as fp:
                    fp.writelines(job_diff_html)
                LOG_UI.info(html_file)

            except IOError as exception:
                LOG_UI.error(exception)
                sys.exit(exit_codes.AVOCADO_FAIL)

        if open_browser:
            setsid = getattr(os, 'setsid', None)
            if not setsid:
                setsid = getattr(os, 'setpgrp', None)
            with open(os.devnull, "r+", encoding='utf-8') as inout:
                cmd = ['xdg-open', html_file]
                subprocess.Popen(cmd, close_fds=True, stdin=inout,  # pylint: disable=W1509
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
            msg = f"Invalid option(s) '{','.join(invalid)}'"
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
        with open(results_json, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)

        return data

    @staticmethod
    def _setup_job(job_id):
        resultsdir = data_dir.get_job_results_dir(job_id)
        if resultsdir is None:
            LOG_UI.error("Can't find job results directory for '%s'", job_id)
            sys.exit(exit_codes.AVOCADO_FAIL)

        with open(os.path.join(resultsdir, 'id'), 'r', encoding='utf-8') as id_file:
            sourcejob = id_file.read().strip()

        return resultsdir, sourcejob

    @staticmethod
    def _get_command_line(resultsdir):
        command_line = jobdata.retrieve_cmdline(resultsdir)
        if command_line is not None:
            return f"{' '.join(command_line)}\n"

        return 'Not found\n'

    @staticmethod
    def _get_variants(resultsdir):
        results = []
        variants = Varianter.from_resultsdir(resultsdir)
        if variants is not None:
            for variant in variants:
                results.extend(variant.to_str(variants=2).splitlines())
        else:
            results.append('Not found\n')

        return results

    @staticmethod
    def _get_config(resultsdir):
        config_file = os.path.join(resultsdir, 'replay', 'config')
        try:
            with open(config_file, 'r', encoding='utf-8') as conf:
                return conf.readlines()
        except IOError:
            return ['Not found\n']

    @staticmethod
    def _get_sysinfo(resultsdir, pre_post):
        sysinfo_dir = os.path.join(resultsdir, 'sysinfo', pre_post)
        sysinfo = []
        for path, _, files in os.walk(sysinfo_dir):
            for name in sorted(files):
                name_header = ['\n', f'** {name} **\n']
                sysinfo.extend(name_header)
                with open(os.path.join(path, name), 'r', encoding='utf-8') as sysinfo_file:
                    try:
                        sysinfo.extend(sysinfo_file.readlines())
                    except UnicodeDecodeError:
                        msg = f"Ignoring file {name} as it cannot be decoded."
                        LOG_UI.debug(msg)
                        continue

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
