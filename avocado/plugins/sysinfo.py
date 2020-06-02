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
# Copyright: Red Hat Inc. 2013-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>
"""
System information plugin
"""

from avocado.core.future.settings import settings
from avocado.core.plugin_interfaces import Init
from avocado.core.plugin_interfaces import CLICmd
from avocado.core.plugin_interfaces import JobPreTests
from avocado.core.plugin_interfaces import JobPostTests
from avocado.core import sysinfo
from avocado.utils import path


class SysinfoInit(Init):

    name = 'sysinfo'
    description = 'Initializes sysinfo settings'

    def initialize(self):
        help_msg = ('Enable or disable sysinfo information. Like hardware '
                    'details, profiles, etc.')
        settings.register_option(section='sysinfo.collect',
                                 key='enabled',
                                 default='on',
                                 key_type=str,
                                 help_msg=help_msg,
                                 choices=('on', 'off'))

        help_msg = 'Enable sysinfo collection per-test'
        settings.register_option(section='sysinfo.collect',
                                 key='per_test',
                                 default=False,
                                 key_type=bool,
                                 help_msg=help_msg)


class SysInfoJob(JobPreTests, JobPostTests):

    name = 'sysinfo'
    description = 'Collects system information before/after the job is run'

    def __init__(self, config):
        self.sysinfo = None
        self.sysinfo_enabled = config.get('sysinfo.collect.enabled') == 'on'

    def _init_sysinfo(self, job_logdir):
        if self.sysinfo is None:
            basedir = path.init_dir(job_logdir, 'sysinfo')
            self.sysinfo = sysinfo.SysInfo(basedir=basedir)

    def pre_tests(self, job):
        if not self.sysinfo_enabled:
            return
        self._init_sysinfo(job.logdir)
        self.sysinfo.start()

    def post_tests(self, job):
        if not self.sysinfo_enabled:
            return
        self._init_sysinfo(job.logdir)
        self.sysinfo.end()


class SysInfo(CLICmd):

    """
    Collect system information
    """

    name = 'sysinfo'
    description = 'Collect system information'

    def configure(self, parser):
        """
        Add the subparser for the run action.

        :param parser: The Avocado command line application parser
        :type parser: :class:`avocado.core.parser.ArgumentParser`
        """
        parser = super(SysInfo, self).configure(parser)

        help_msg = ('Directory where Avocado will dump sysinfo data.  If one '
                    'is not given explicitly, it will default to a directory '
                    'named "sysinfo-" followed by a timestamp in the current '
                    'working directory.')
        settings.register_option(section='sysinfo.collect',
                                 key='sysinfodir',
                                 default=None,
                                 help_msg=help_msg,
                                 parser=parser,
                                 positional_arg=True,
                                 nargs='?')

    def run(self, config):
        sysinfodir = config.get('sysinfo.collect.sysinfodir')
        sysinfo.collect_sysinfo(sysinfodir)
