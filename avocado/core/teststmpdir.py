# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; specifically version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.


import os
import shutil
import tempfile


class TestsTmpDir(object):

    def __init__(self, varname='XXX_TESTS_COMMON_TMPDIR'):
        self._varname = varname

    def create(self):
        tmpdir = tempfile.mkdtemp(prefix='avocado_')
        os.environ[self._varname] = tmpdir
        return tmpdir

    def destroy(self):
        if os.environ.get(self._varname) is not None:
            shutil.rmtree(os.environ.get(self._varname))

teststmpdir = TestsTmpDir()
