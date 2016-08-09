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
# Copyright: Red Hat Inc. 2014-2015
# Author: Ruda Moura <rmoura@redhat.com>

"""Remote test results."""

import os

from ..result import HumanResult


class RemoteResult(HumanResult):

    """
    Remote Machine Test Result class.
    """

    def __init__(self, job):
        """
        Creates an instance of RemoteResult.

        :param job: an instance of :class:`avocado.core.job.Job`.
        """
        HumanResult.__init__(self, job)
        self.test_dir = os.getcwd()
        self.remote_test_dir = '~/avocado/tests'
        self.urls = self.args.url
        self.remote = None      # Remote runner initialized during setup
        self.output = '-'

    def tear_down(self):
        """ Cleanup after test execution """
        pass


class VMResult(RemoteResult):

    """
    Virtual Machine Test Result class.
    """

    def __init__(self, job):
        super(VMResult, self).__init__(job)
        self.vm = None
