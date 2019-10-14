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

from avocado.core.plugin_interfaces import CLICmd
from avocado.core.plugin_interfaces import JobPre
from avocado.core.plugin_interfaces import JobPost
from avocado.core import sysinfo
from avocado.utils import path


class SysInfoJob(JobPre, JobPost):

    name = 'sysinfo'
    description = 'Collects system information before/after the job is run'

    def __init__(self):
        self.sysinfo = None

    def _init_sysinfo(self, job_logdir):
        if self.sysinfo is None:
            basedir = path.init_dir(job_logdir, 'sysinfo')
            self.sysinfo = sysinfo.SysInfo(basedir=basedir)

    def pre(self, job):
        if job.config.get('sysinfo', None) != 'on':
            return
        self._init_sysinfo(job.logdir)
        self.sysinfo.start_job_hook()

    def post(self, job):
        if job.config.get('sysinfo', None) != 'on':
            return
        self._init_sysinfo(job.logdir)
        self.sysinfo.end_job_hook()


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
        parser.add_argument('sysinfodir', type=str,
                            help='Dir where to dump sysinfo',
                            nargs='?', default='')

    def run(self, config):
        sysinfo.collect_sysinfo(config.get('sysinfodir'))
