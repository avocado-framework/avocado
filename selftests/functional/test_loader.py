import os
import sys
import subprocess
import time
import stat
import tempfile
import shutil
import signal

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

from avocado.core import exit_codes
from avocado.utils import script
from avocado.utils import process


basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
basedir = os.path.abspath(basedir)


AVOCADO_TEST_OK = """#!/usr/bin/env python
from avocado import Test
from avocado import main

class PassTest(Test):
    def test(self):
        pass

if __name__ == "__main__":
    main()
"""


AVOCADO_TEST_SLEEP_ELEVEN = """#!/usr/bin/env python
import time

from avocado import Test
from avocado import main

class SleepEleven(Test):
    def test(self):
        time.sleep(10)
    def test_2(self):
        time.sleep(1)

time.sleep(11)

if __name__ == "__main__":
    main()
"""


AVOCADO_TEST_MULTIPLE_CLASSES = """#!/usr/bin/env python
import time

from avocado import Test
from avocado import main

class First(Test):
    def test(self):
        pass

class Second(Test):
    def test(self):
        pass

if __name__ == "__main__":
    main()
"""

AVOCADO_TEST_MULTIPLE_METHODS_SAME_NAME = """#!/usr/bin/env python
from avocado import Test
from avocado import main

class Multiple(Test):
    def test(self):
        raise

    def test(self):
        pass

if __name__ == "__main__":
    main()
"""

NOT_A_TEST = """
def hello():
    print('Hello World!')
"""

PY_SIMPLE_TEST = """#!/usr/bin/env python
def hello():
    print('Hello World!')

if __name__ == "__main__":
    hello()
"""

SIMPLE_TEST = """#!/bin/sh
true
"""

AVOCADO_SIMPLE_PYTHON_LIKE_MULTIPLE_FILES = """#!/usr/bin/env python
# A simple test (executable bit set when saved to file) that looks like
# an Avocado instrumented test, with base class on separate file
from avocado import Test
from avocado import main
from test2 import *

class BasicTestSuite(SuperTest):

    def test1(self):
        self.xxx()
        self.assertTrue(True)

if __name__ == '__main__':
    main()
"""

AVOCADO_SIMPLE_PYTHON_LIKE_MULTIPLE_FILES_LIB = """
#!/usr/bin/python

from avocado import Test

class SuperTest(Test):
    def xxx(self):
        print "ahoj"
"""

AVOCADO_TEST_SIMPLE_USING_MAIN = """#!/usr/bin/env python
from avocado import main

if __name__ == "__main__":
    main()
"""


class LoaderTestFunctional(unittest.TestCase):

    MODE_0664 = (stat.S_IRUSR | stat.S_IWUSR |
                 stat.S_IRGRP | stat.S_IWGRP |
                 stat.S_IROTH)

    MODE_0775 = (stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                 stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP |
                 stat.S_IROTH | stat.S_IXOTH)

    def setUp(self):
        os.chdir(basedir)
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)

    def _test(self, name, content, exp_str, mode=MODE_0664, count=1):
        test_script = script.TemporaryScript(name, content,
                                             'avocado_loader_test',
                                             mode=mode)
        test_script.save()
        cmd_line = ('./scripts/avocado list -V %s' % test_script.path)
        result = process.run(cmd_line)
        self.assertIn('%s: %s' % (exp_str, count), result.stdout)
        test_script.remove()

    def _run_with_timeout(self, cmd_line, timeout):
        current_time = time.time()
        deadline = current_time + timeout
        test_process = subprocess.Popen(cmd_line, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        preexec_fn=os.setsid)
        while not test_process.poll():
            if time.time() > deadline:
                os.killpg(os.getpgid(test_process.pid), signal.SIGKILL)
                self.fail("Failed to run test under %s seconds" % timeout)
            time.sleep(0.05)
        self.assertEquals(test_process.returncode, exit_codes.AVOCADO_TESTS_FAIL)

    def test_simple(self):
        self._test('simpletest.sh', SIMPLE_TEST, 'SIMPLE', self.MODE_0775)

    def test_simple_not_exec(self):
        self._test('simpletest.sh', SIMPLE_TEST, 'NOT_A_TEST')

    def test_pass(self):
        self._test('passtest.py', AVOCADO_TEST_OK, 'INSTRUMENTED')

    def test_sleep_a_lot(self):
        """
        Verifies that the test loader, at list time, does not load the Python
        module and thus executes its contents.
        """
        test_script = script.TemporaryScript('sleepeleven.py',
                                             AVOCADO_TEST_SLEEP_ELEVEN,
                                             'avocado_loader_test',
                                             mode=self.MODE_0664)
        test_script.save()
        cmd_line = ('./scripts/avocado list -V %s' % test_script.path)
        initial_time = time.time()
        result = process.run(cmd_line, ignore_status=True)
        test_script.remove()
        actual_time = time.time() - initial_time
        self.assertLess(actual_time, 3.0,
                        ("Took more than 3 seconds to list tests. Loader "
                         "probably loaded/executed Python code and slept for "
                         "eleven seconds."))
        self.assertIn('INSTRUMENTED: 2', result.stdout)

    def test_multiple_class(self):
        self._test('multipleclasses.py', AVOCADO_TEST_MULTIPLE_CLASSES,
                   'INSTRUMENTED', self.MODE_0664, 2)

    def test_multiple_methods_same_name(self):
        self._test('multiplemethods.py', AVOCADO_TEST_MULTIPLE_METHODS_SAME_NAME,
                   'INSTRUMENTED', 0664, 1)

    def test_load_not_a_test(self):
        self._test('notatest.py', NOT_A_TEST, 'SIMPLE', self.MODE_0775)

    def test_load_not_a_test_not_exec(self):
        self._test('notatest.py', NOT_A_TEST, 'NOT_A_TEST')

    def test_runner_simple_python_like_multiple_files(self):
        mylib = script.TemporaryScript(
            'test2.py',
            AVOCADO_SIMPLE_PYTHON_LIKE_MULTIPLE_FILES_LIB,
            'avocado_simpletest_functional',
            0644)
        mylib.save()
        mytest = script.Script(
            os.path.join(os.path.dirname(mylib.path), 'test.py'),
            AVOCADO_SIMPLE_PYTHON_LIKE_MULTIPLE_FILES)
        os.chdir(basedir)
        mytest.save()
        cmd_line = "./scripts/avocado list -V %s" % mytest
        result = process.run(cmd_line)
        self.assertIn('SIMPLE: 1', result.stdout)
        # job should be able to finish under 5 seconds. If this fails, it's
        # possible that we hit the "simple test fork bomb" bug
        cmd_line = ['./scripts/avocado',
                    'run',
                    '--sysinfo=off',
                    '--job-results-dir',
                    "%s" % self.tmpdir,
                    "%s" % mytest]
        self._run_with_timeout(cmd_line, 5)

    def test_simple_using_main(self):
        mytest = script.TemporaryScript("simple_using_main.py",
                                        AVOCADO_TEST_SIMPLE_USING_MAIN,
                                        'avocado_simpletest_functional')
        mytest.save()
        os.chdir(basedir)
        # job should be able to finish under 5 seconds. If this fails, it's
        # possible that we hit the "simple test fork bomb" bug
        cmd_line = ['./scripts/avocado',
                    'run',
                    '--sysinfo=off',
                    '--job-results-dir',
                    "%s" % self.tmpdir,
                    "%s" % mytest]
        self._run_with_timeout(cmd_line, 5)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
