import os
import shutil
import tempfile

from avocado.core.plugin_interfaces import JobPre, JobPost


class TestsTmpDir(JobPre, JobPost):

    name = 'teststmpdir'
    description = 'Creates a temporary directory for tests consumption'

    def __init__(self):
        self._varname = 'AVOCADO_TESTS_COMMON_TMPDIR'
        self._dirname = None

    def pre(self, job):
        if os.environ.get(self._varname) is None:
            self._dirname = tempfile.mkdtemp(prefix='avocado_')
            os.environ[self._varname] = self._dirname

    def post(self, job):
        if (self._dirname is not None and
                os.environ.get(self._varname) == self._dirname and
                os.path.exists(self._dirname)):
            del os.environ[self._varname]
            shutil.rmtree(self._dirname)
