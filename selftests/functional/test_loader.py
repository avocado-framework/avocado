import json
import os
import signal
import stat
import subprocess
import time
import unittest

from avocado.core import exit_codes
from avocado.utils import process, script
from selftests.utils import (AVOCADO, BASEDIR, TestCaseTmpDir,
                             skipOnLevelsInferiorThan, skipUnlessPathExists)

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


class LoaderTestFunctional(TestCaseTmpDir):

    MODE_0664 = (stat.S_IRUSR | stat.S_IWUSR |
                 stat.S_IRGRP | stat.S_IWGRP |
                 stat.S_IROTH)

    MODE_0775 = (stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                 stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP |
                 stat.S_IROTH | stat.S_IXOTH)

    def _test(self, name, content, exp_str, mode=MODE_0664, count=1):
        test_script = script.TemporaryScript(name, content,
                                             'avocado_loader_test',
                                             mode=mode)
        test_script.save()
        cmd_line = ('%s -V list %s' % (AVOCADO, test_script.path))
        result = process.run(cmd_line)
        self.assertIn('%s: %s' % (exp_str, count), result.stdout_text)
        test_script.remove()

    def _run_with_timeout(self, cmd_line, timeout):
        current_time = time.time()
        deadline = current_time + timeout
        test_process = subprocess.Popen(cmd_line, stdout=subprocess.PIPE,  # pylint: disable=W1509
                                        stderr=subprocess.PIPE,
                                        preexec_fn=os.setsid, shell=True)
        while not test_process.poll():
            if time.time() > deadline:
                os.killpg(os.getpgid(test_process.pid), signal.SIGKILL)
                self.fail("Failed to run test under %s seconds" % timeout)
            time.sleep(0.05)
        self.assertEqual(test_process.returncode, exit_codes.AVOCADO_TESTS_FAIL)

    def test_simple(self):
        self._test('simpletest.sh', SIMPLE_TEST, 'simple', self.MODE_0775)

    def test_simple_not_exec(self):
        # 2 because both FileLoader and the TAP loader cannot recognize the test
        self._test('simpletest.sh', SIMPLE_TEST, 'not_a_test', count=2)

    def test_pass(self):
        self._test('passtest.py', AVOCADO_TEST_OK, 'instrumented')

    def test_not_python_module(self):
        # 2 because both FileLoader and the TAP loader cannot recognize the test
        self._test('passtest', AVOCADO_TEST_OK, 'not_a_test', count=2)

    @skipOnLevelsInferiorThan(2)
    def test_sleep_a_lot(self):
        """
        Verifies that the test loader, at list time, does not load the Python
        module and thus executes its contents.

        :avocado: tags=parallel:1
        """
        test_script = script.TemporaryScript('sleepeleven.py',
                                             AVOCADO_TEST_SLEEP_ELEVEN,
                                             'avocado_loader_test',
                                             mode=self.MODE_0664)
        test_script.save()
        cmd_line = ('%s -V list %s' % (AVOCADO, test_script.path))
        initial_time = time.time()
        result = process.run(cmd_line, ignore_status=True)
        test_script.remove()
        actual_time = time.time() - initial_time
        self.assertLess(actual_time, 3.0,
                        ("Took more than 3 seconds to list tests. Loader "
                         "probably loaded/executed Python code and slept for "
                         "eleven seconds."))
        self.assertIn(b'instrumented: 2', result.stdout)

    def test_multiple_class(self):
        self._test('multipleclasses.py', AVOCADO_TEST_MULTIPLE_CLASSES,
                   'instrumented', self.MODE_0664, 2)

    def test_multiple_methods_same_name(self):
        self._test('multiplemethods.py', AVOCADO_TEST_MULTIPLE_METHODS_SAME_NAME,
                   'instrumented', self.MODE_0664, 1)

    def test_load_not_a_test(self):
        self._test('notatest.py', NOT_A_TEST, 'simple', self.MODE_0775)

    def test_load_not_a_test_not_exec(self):
        # 2 because both FileLoader and the TAP loader cannot recognize the test
        self._test('notatest.py', NOT_A_TEST, 'not_a_test', count=2)

    @skipOnLevelsInferiorThan(2)
    def test_runner_simple_python_like_multiple_files(self):
        """
        :avocado: tags=parallel:1
        """
        mylib = script.TemporaryScript(
            'test2.py',
            AVOCADO_SIMPLE_PYTHON_LIKE_MULTIPLE_FILES_LIB,
            'avocado_simpletest_functional',
            self.MODE_0664)
        mylib.save()
        mytest = script.Script(
            os.path.join(os.path.dirname(mylib.path), 'test.py'),
            AVOCADO_SIMPLE_PYTHON_LIKE_MULTIPLE_FILES)
        os.chdir(BASEDIR)
        mytest.save()
        cmd_line = "%s -V list %s" % (AVOCADO, mytest)
        result = process.run(cmd_line)
        self.assertIn(b'simple: 1', result.stdout)
        # job should be able to finish under 5 seconds. If this fails, it's
        # possible that we hit the "simple test fork bomb" bug
        cmd_line = ("%s run --disable-sysinfo --job-results-dir '%s' -- '%s'"
                    % (AVOCADO, self.tmpdir.name, mytest))
        self._run_with_timeout(cmd_line, 5)

    @skipOnLevelsInferiorThan(2)
    def test_simple_using_main(self):
        """
        :avocado: tags=parallel:1
        """
        mytest = script.TemporaryScript("simple_using_main.py",
                                        AVOCADO_TEST_SIMPLE_USING_MAIN,
                                        'avocado_simpletest_functional')
        mytest.save()
        os.chdir(BASEDIR)
        # job should be able to finish under 5 seconds. If this fails, it's
        # possible that we hit the "simple test fork bomb" bug
        cmd_line = ("%s run --disable-sysinfo --job-results-dir '%s' -- '%s'"
                    % (AVOCADO, self.tmpdir.name, mytest))
        self._run_with_timeout(cmd_line, 5)

    def test_python_unittest(self):
        test_path = os.path.join(BASEDIR, "selftests", ".data", "unittests.py")
        cmd = ("%s run --disable-sysinfo --job-results-dir %s --json - -- %s"
               % (AVOCADO, self.tmpdir.name, test_path))
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
        expected = (b"INSTRUMENTED examples/tests/assert.py:Assert.test_fails_to_raise\n"
                    b"INSTRUMENTED examples/tests/doublefail.py:DoubleFail.test\n"
                    b"INSTRUMENTED examples/tests/fail_on_exception.py:FailOnException.test\n"
                    b"INSTRUMENTED examples/tests/failtest.py:FailTest.test\n"
                    b"SIMPLE       examples/tests/failtest.sh\n")
        self.assertEqual(expected, result.stdout)

    @skipUnlessPathExists('/bin/sh')
    def test_loader_and_external_runner_incompatibility(self):
        """
        Check if the user is inform about incompatibility between loader and
        external_runner.
        """
        test_script = script.TemporaryScript('simpletest.sh', SIMPLE_TEST,
                                             'avocado_loader_test',
                                             mode=self.MODE_0775)
        test_script.save()

        cmd = ("%s run --loaders=FOO "
               "--external-runner=/bin/sh %s") % (AVOCADO, test_script.path)
        result = process.run(cmd)
        expected_warning = ("The loaders and external-runner are incompatible."
                            "The values in loaders will be ignored.")
        self.assertIn(expected_warning, result.stderr_text)

        cmd = "%s run --external-runner=/bin/sh %s" % (AVOCADO,
                                                       test_script.path)
        result = process.run(cmd)
        self.assertNotIn(expected_warning, result.stderr_text)

        test_script.remove()


if __name__ == '__main__':
    unittest.main()
