import os
import sys
import time
import tempfile
import shutil

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

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


class LoaderTestFunctional(unittest.TestCase):

    def setUp(self):
        os.chdir(basedir)
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)

    def _test(self, name, content, exp_str, mode=0664, count=1):
        test_script = script.TemporaryScript(name, content,
                                             'avocado_loader_test',
                                             mode=mode)
        test_script.save()
        cmd_line = ('./scripts/avocado list -V %s' % test_script.path)
        result = process.run(cmd_line)
        self.assertIn('%s: %s' % (exp_str, count), result.stdout)
        test_script.remove()

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_simple(self):
        self._test('simpletest.sh', SIMPLE_TEST, 'SIMPLE', 0775)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_simple_not_exec(self):
        self._test('simpletest.sh', SIMPLE_TEST, 'NOT_A_TEST')

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_pass(self):
        self._test('passtest.py', AVOCADO_TEST_OK, 'INSTRUMENTED')

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_sleep_a_lot(self):
        """
        Verifies that the test loader, at list time, does not load the Python
        module and thus executes its contents.
        """
        test_script = script.TemporaryScript('sleepeleven.py',
                                             AVOCADO_TEST_SLEEP_ELEVEN,
                                             'avocado_loader_test',
                                             mode=0664)
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

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_multiple_class(self):
        self._test('multipleclasses.py', AVOCADO_TEST_MULTIPLE_CLASSES,
                   'INSTRUMENTED', 0664, 2)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_load_not_a_test(self):
        self._test('notatest.py', NOT_A_TEST, 'SIMPLE', 0775)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_load_not_a_test_not_exec(self):
        self._test('notatest.py', NOT_A_TEST, 'NOT_A_TEST')

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
