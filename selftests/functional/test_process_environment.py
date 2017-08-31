import os
import stat
import sys
import tempfile
import unittest
import shutil

from avocado.utils import script
from avocado.utils import process
from avocado.core import exit_codes


AVOCADO = os.environ.get("UNITTEST_AVOCADO_CMD", "./scripts/avocado")


EXECUTABLE_MODE = (stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                   stat.S_IRGRP | stat.S_IXGRP |
                   stat.S_IROTH | stat.S_IXOTH)

NON_EXECUTABLE_MODE = (stat.S_IRUSR | stat.S_IWUSR |
                       stat.S_IRGRP |
                       stat.S_IROTH)


READ_STDIN_SIMPLE = """#!%s
import os
import sys
if sys.stdin.read(1):
    sys.exit(-1)

if os.read(0, 1):
    sys.exit(-1)

if os.path.exists('/dev/stdin'):
    if open('/dev/stdin', 'r').read(1):
        sys.exit(-1)
""" % sys.executable


READ_STDIN_INSTRUMENTED = """
import os
import sys
from avocado import Test

class ReadStdIn(Test):
    def test(self):
        self.assertEquals(sys.stdin.read(1), '')
        self.assertEquals(os.read(0, 1), '')
        if os.path.exists('/dev/stdin'):
            self.assertEquals(open('/dev/stdin', 'r').read(1), '')
"""


MAGIC = 'MAGIC_STRING_THAT_SHOULD_NOT_CAUSE_A_CLASH'


WRITE_STDOUT_SIMPLE = """#!%s
import os
import sys
magic = '%s'

sys.stdout.write(magic)
os.write(1, magic)
if os.path.exists('/dev/stdout'):
    open('/dev/stdout', 'a').write(magic)
""" % (sys.executable, MAGIC)


WRITE_STDOUT_INSTRUMENTED = """
import os
import sys
from avocado import Test

magic = '%s'

class WriteStdOut(Test):
    def test(self):
        sys.stdout.write(magic)
        os.write(1, magic)
        if os.path.exists('/dev/stdout'):
            open('/dev/stdout', 'a').write(magic)
""" % MAGIC


WRITE_STDERR_SIMPLE = """#!%s
import os
import sys
magic = '%s'

sys.stderr.write(magic)
os.write(2, magic)
if os.path.exists('/dev/stderr'):
    open('/dev/stderr', 'a').write(magic)
""" % (sys.executable, MAGIC)


WRITE_STDERR_INSTRUMENTED = """
import os
import sys
from avocado import Test

magic = '%s'

class WriteStdErr(Test):
    def test(self):
        sys.stderr.write(magic)
        os.write(2, magic)
        if os.path.exists('/dev/stderr'):
            open('/dev/stderr', 'a').write(magic)
""" % MAGIC


class ProcessStdInOutErr(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)

    @unittest.skipIf(int(os.environ.get("AVOCADO_CHECK_LEVEL", 0)) < 1,
                     "Skipping test that take a long time to run, are "
                     "resource intensive or time sensitve")
    def _test_stdin(self, content, mode):
        with script.TemporaryScript('tst.py',
                                    content,
                                    'avocado_test',
                                    mode=mode) as tst:
            cmd = '%s run %s --job-timeout=5 --job-results-dir=%s'
            cmd %= (AVOCADO, tst.path, self.tmpdir)
            result = process.run(cmd, ignore_status=True)
            self.assertEqual(result.exit_status,
                             exit_codes.AVOCADO_ALL_OK,
                             "Avocado did not return rc %d:\n%s" % (
                                 exit_codes.AVOCADO_ALL_OK,
                                 result))

    def _test_stdout_stderr(self, content, mode, stdout=False, stderr=False):
        with script.TemporaryScript('tst.py',
                                    content,
                                    'avocado_test',
                                    mode=mode) as tst:
            cmd = '%s run %s --job-results-dir=%s'
            cmd %= (AVOCADO, tst.path, self.tmpdir)
            result = process.run(cmd, ignore_status=True)
            self.assertEqual(result.exit_status,
                             exit_codes.AVOCADO_ALL_OK,
                             "Avocado did not return rc %d:\n%s" % (
                                 exit_codes.AVOCADO_ALL_OK,
                                 result))
            if stdout:
                self.assertNotIn(MAGIC, result.stdout)
            if stderr:
                self.assertNotIn(MAGIC, result.stderr)

    def test_read_stdin_simple(self):
        self._test_stdin(READ_STDIN_SIMPLE, EXECUTABLE_MODE)

    def test_read_stdin_instrumented(self):
        self._test_stdin(READ_STDIN_INSTRUMENTED, NON_EXECUTABLE_MODE)

    def test_write_stdout_simple(self):
        self._test_stdout_stderr(WRITE_STDOUT_SIMPLE, EXECUTABLE_MODE, stdout=True)

    def test_write_stdout_instrumented(self):
        self._test_stdout_stderr(WRITE_STDOUT_INSTRUMENTED, NON_EXECUTABLE_MODE, stdout=True)

    def test_write_stderr_simple(self):
        self._test_stdout_stderr(WRITE_STDERR_SIMPLE, EXECUTABLE_MODE, stderr=True)

    def test_write_stderr_instrumented(self):
        self._test_stdout_stderr(WRITE_STDERR_INSTRUMENTED, NON_EXECUTABLE_MODE, stderr=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
