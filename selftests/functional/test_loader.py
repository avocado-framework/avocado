import os
import json
import subprocess
import time
import stat
import tempfile
import shutil
import signal
import sys
import unittest

from avocado.core import exit_codes
from avocado.utils import script
from avocado.utils import process

from .. import AVOCADO, BASEDIR


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
    '''
    :avocado: disable
    '''

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

    MODE_0644 = (stat.S_IRUSR | stat.S_IWUSR |
                 stat.S_IRGRP |
                 stat.S_IROTH)

    MODE_0664 = (stat.S_IRUSR | stat.S_IWUSR |
                 stat.S_IRGRP | stat.S_IWGRP |
                 stat.S_IROTH)

    MODE_0775 = (stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                 stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP |
                 stat.S_IROTH | stat.S_IXOTH)

    def setUp(self):
        os.chdir(BASEDIR)
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)

    def _test(self, name, content, exp_str, mode=MODE_0664, count=1):
        test_script = script.TemporaryScript(name, content,
                                             'avocado_loader_test',
                                             mode=mode)
        test_script.save()
        cmd_line = ('%s list -V %s' % (AVOCADO, test_script.path))
        result = process.run(cmd_line)
        self.assertIn('%s: %s' % (exp_str, count), result.stdout_text)
        test_script.remove()

    def _run_with_timeout(self, cmd_line, timeout):
        current_time = time.time()
        deadline = current_time + timeout
        test_process = subprocess.Popen(cmd_line, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        preexec_fn=os.setsid, shell=True)
        while not test_process.poll():
            if time.time() > deadline:
                os.killpg(os.getpgid(test_process.pid), signal.SIGKILL)
                self.fail("Failed to run test under %s seconds" % timeout)
            time.sleep(0.05)
        self.assertEqual(test_process.returncode, exit_codes.AVOCADO_TESTS_FAIL)

    def test_simple(self):
        self._test('simpletest.sh', SIMPLE_TEST, 'SIMPLE', self.MODE_0775)

    def test_simple_not_exec(self):
        self._test('simpletest.sh', SIMPLE_TEST, 'NOT_A_TEST')

    def test_pass(self):
        self._test('passtest.py', AVOCADO_TEST_OK, 'INSTRUMENTED')

    def test_not_python_module(self):
        self._test('passtest', AVOCADO_TEST_OK, 'NOT_A_TEST')

    @unittest.skipIf(int(os.environ.get("AVOCADO_CHECK_LEVEL", 0)) < 2,
                     "Skipping test that take a long time to run, are "
                     "resource intensive or time sensitve")
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
        cmd_line = ('%s list -V %s' % (AVOCADO, test_script.path))
        initial_time = time.time()
        result = process.run(cmd_line, ignore_status=True)
        test_script.remove()
        actual_time = time.time() - initial_time
        self.assertLess(actual_time, 3.0,
                        ("Took more than 3 seconds to list tests. Loader "
                         "probably loaded/executed Python code and slept for "
                         "eleven seconds."))
        self.assertIn(b'INSTRUMENTED: 2', result.stdout)

    def test_multiple_class(self):
        self._test('multipleclasses.py', AVOCADO_TEST_MULTIPLE_CLASSES,
                   'INSTRUMENTED', self.MODE_0664, 2)

    def test_multiple_methods_same_name(self):
        self._test('multiplemethods.py', AVOCADO_TEST_MULTIPLE_METHODS_SAME_NAME,
                   'INSTRUMENTED', self.MODE_0664, 1)

    def test_load_not_a_test(self):
        self._test('notatest.py', NOT_A_TEST, 'SIMPLE', self.MODE_0775)

    def test_load_not_a_test_not_exec(self):
        self._test('notatest.py', NOT_A_TEST, 'NOT_A_TEST')

    @unittest.skipIf(int(os.environ.get("AVOCADO_CHECK_LEVEL", 0)) < 2,
                     "Skipping test that take a long time to run, are "
                     "resource intensive or time sensitve")
    def test_runner_simple_python_like_multiple_files(self):
        mylib = script.TemporaryScript(
            'test2.py',
            AVOCADO_SIMPLE_PYTHON_LIKE_MULTIPLE_FILES_LIB,
            'avocado_simpletest_functional',
            self.MODE_0644)
        mylib.save()
        mytest = script.Script(
            os.path.join(os.path.dirname(mylib.path), 'test.py'),
            AVOCADO_SIMPLE_PYTHON_LIKE_MULTIPLE_FILES)
        os.chdir(BASEDIR)
        mytest.save()
        cmd_line = "%s list -V %s" % (AVOCADO, mytest)
        result = process.run(cmd_line)
        self.assertIn(b'SIMPLE: 1', result.stdout)
        # job should be able to finish under 5 seconds. If this fails, it's
        # possible that we hit the "simple test fork bomb" bug
        cmd_line = ("%s run --sysinfo=off --job-results-dir '%s' -- '%s'"
                    % (AVOCADO, self.tmpdir, mytest))
        self._run_with_timeout(cmd_line, 5)

    @unittest.skipIf(int(os.environ.get("AVOCADO_CHECK_LEVEL", 0)) < 2,
                     "Skipping test that take a long time to run, are "
                     "resource intensive or time sensitve")
    def test_simple_using_main(self):
        mytest = script.TemporaryScript("simple_using_main.py",
                                        AVOCADO_TEST_SIMPLE_USING_MAIN,
                                        'avocado_simpletest_functional')
        mytest.save()
        os.chdir(BASEDIR)
        # job should be able to finish under 5 seconds. If this fails, it's
        # possible that we hit the "simple test fork bomb" bug
        cmd_line = ("%s run --sysinfo=off --job-results-dir '%s' -- '%s'"
                    % (AVOCADO, self.tmpdir, mytest))
        self._run_with_timeout(cmd_line, 5)

    @unittest.skipIf(sys.version_info[0] == 3,
                     "Test currently broken on Python 3")
    @unittest.skipUnless(os.path.exists("/bin/true"), "/bin/true not "
                         "available")
    @unittest.skipUnless(os.path.exists("/bin/echo"), "/bin/echo not "
                         "available")
    def test_yaml_loader_list(self):
        # Verifies that yaml_loader list won't crash and is able to detect
        # various test types
        result = process.run("%s list -V --loaders yaml_testsuite -- "
                             "examples/yaml_to_mux_loader/loaders.yaml"
                             % AVOCADO)
        # This has to be defined like this as pep8 complains about tailing
        # empty spaces when using """
        self.assertRegexpMatches(result.stdout_text, r"Type *Test *Tag\(s\)\n"
                                 r"INSTRUMENTED *passtest.py:PassTest.test *"
                                 "fast\n"
                                 r"SIMPLE.*passtest.sh *\n"
                                 r"EXTERNAL *external_echo *\n"
                                 r"EXTERNAL *external_false *\n")
        # Also check whether list without loaders won't crash
        result = process.run("%s list -V -- "
                             "examples/yaml_to_mux_loader/loaders.yaml"
                             % AVOCADO)

    def test_yaml_loader_run(self):
        # Checks that yaml_loader supplies correct params and that
        # --mux-suite-only filters the test suite
        result = process.run("%s --show test run --dry-run --mux-suite-only "
                             "/run/tests/sleeptest -- examples/yaml_to_mux_"
                             "loader/advanced.yaml" % AVOCADO)
        test = -1
        exp_timeouts = [2] * 4 + [6] * 4 + [None] * 4
        exp_timeout = None
        exp_sleep_lengths = [0.5, 1, 5, 10] * 3
        exp_sleep_length = None
        for line in result.stdout_text.splitlines():
            if line.startswith("START "):
                self.assertFalse(exp_timeout, "%s was not found in test %ss "
                                 "output:\n%s" % (exp_timeout, test, result))
                self.assertFalse(exp_timeout, "%s was not found in test %ss "
                                 "output:\n%s" % (exp_sleep_length, test,
                                                  result))
                self.assertLess(test, 12, "Number of tests is greater than "
                                "12:\n%s" % result)
                test += 1
                timeout = exp_timeouts[test]
                if timeout:
                    exp_timeout = "timeout ==> %s" % timeout
                else:
                    exp_timeout = "(key=timeout, path=*, default=None) => None"
                exp_sleep_length = ("sleep_length ==> %s"
                                    % exp_sleep_lengths[test])
            elif exp_timeout and exp_timeout in line:
                exp_timeout = None
            elif exp_sleep_length and exp_sleep_length in line:
                exp_sleep_length = None
        self.assertEqual(test, 11, "Number of tests is not 12 (%s):\n%s"
                         % (test, result))

    def test_python_unittest(self):
        test_path = os.path.join(BASEDIR, "selftests", ".data", "unittests.py")
        cmd = ("%s run --sysinfo=off --job-results-dir %s --json - -- %s"
               % (AVOCADO, self.tmpdir, test_path))
        result = process.run(cmd, ignore_status=True)
        jres = json.loads(result.stdout_text)
        self.assertEqual(result.exit_status, 1, result)
        exps = [("unittests.Second.test_fail", "FAIL"),
                ("unittests.Second.test_error", "ERROR"),
                ("unittests.Second.test_skip", "CANCEL"),
                ("unittests.First.test_pass", "PASS")]
        for test in jres["tests"]:
            for exp in exps:
                if exp[0] in test["id"]:
                    self.assertEqual(test["status"], exp[1], "Status of %s not"
                                     " as expected\n%s" % (exp, result))
                    exps.remove(exp)
                    break
            else:
                self.fail("No expected result for %s\n%s\n\nexps = %s"
                          % (test["id"], result, exps))
        self.assertFalse(exps, "Some expected result not matched to actual"
                         "results:\n%s\n\nexps = %s" % (result, exps))

    def test_list_subtests_filter(self):
        """
        Check whether the subtests filter works for both INSTRUMENTED
        and SIMPLE in a directory list.
        """
        cmd = "%s list examples/tests/:fail" % AVOCADO
        result = process.run(cmd)
        expected = (b"INSTRUMENTED examples/tests/doublefail.py:DoubleFail.test\n"
                    b"INSTRUMENTED examples/tests/fail_on_exception.py:FailOnException.test\n"
                    b"INSTRUMENTED examples/tests/failtest.py:FailTest.test\n"
                    b"SIMPLE       examples/tests/failtest.sh\n")
        self.assertEqual(expected, result.stdout)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
