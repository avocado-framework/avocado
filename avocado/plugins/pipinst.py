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
# Copyright: 2020 IBM Corp
# Author: Satheesh Rajendran <sathnaga@linux.vnet.ibm.com>
"""
Install additional python packages required for test using pip
"""

import sys

from avocado.core import exit_codes
from avocado.core.plugin_interfaces import JobPre
from avocado.core.plugin_interfaces import JobPost
from avocado.core.settings import settings
from avocado.utils import process


class PipInst(JobPre, JobPost):

    name = 'PipInst'
    description = 'Install new python packages required for test'

    def __init__(self):
        self.enabled = settings.get_value('job.pipinst', 'enabled',
                                          key_type='bool', default=False)
        self.uninstall = settings.get_value('job.pipinst', 'uninstall',
                                            key_type='bool', default=False)
        self.packages = settings.get_value('job.pipinst', 'packages',
                                           key_type='str', default="").split(',')
        self.exit_job = settings.get_value('job.pipinst', 'exit_job_on_failure',
                                           key_type='bool', default=False)

    def pre(self, job):
        self.enabled = job.config.get('job.pipinst.enabled')
        if not self.enabled:
            return
        for item in self.packages:
            output = process.run('pip install --user %s' % item,
                                 ignore_status=True,
                                 shell=True)
            if output.exit_status != 0 and self.exit_job:
                print("Exiting job due to pipinstall failure")
                sys.exit(exit_codes.AVOCADO_JOB_FAIL)

    def post(self, job):
        self.enabled = job.config.get('job.pipinst.enabled')
        if not (self.enabled and self.uninstall):
            return
        for item in self.packages:
            process.run('pip uninstall -y %s' % item,
                        ignore_status=True,
                        shell=True)
