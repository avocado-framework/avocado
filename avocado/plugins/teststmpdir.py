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
# Copyright: Red Hat, Inc. 2016
# Author: Amador Pahim <apahim@redhat.com>
"""
Tests temporary directory plugin
"""

import os
import shutil
import tempfile

from avocado.core import test
from avocado.core.plugin_interfaces import JobPost, JobPre


class TestsTmpDir(JobPre, JobPost):

    name = 'teststmpdir'
    description = 'Creates a temporary directory for tests consumption'

    def __init__(self):
        self._varname = test.COMMON_TMPDIR_NAME
        self._dirname = None

    def pre(self, job):
        if os.environ.get(self._varname) is None:
            self._dirname = tempfile.mkdtemp(prefix='avocado_')
            os.environ[self._varname] = self._dirname

    def post(self, job):
        if (self._dirname is not None and
                os.environ.get(self._varname) == self._dirname):
            try:
                shutil.rmtree(self._dirname)
                del os.environ[self._varname]
            except Exception:  # pylint: disable=W0703
                pass
