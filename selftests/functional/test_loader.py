import os
import sys
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


AVOCADO_TEST_OK = """#!/usr/bin/python
from avocado import Test
from avocado import main

class PassTest(Test):
    def test(self):
        pass

if __name__ == "__main__":
    main()
"""

AVOCADO_TEST_BUGGY = """#!/usr/bin/python
from avocado import Test
from avocado import main
import adsh

class PassTest(Test):
    def test(self):
        pass

if __name__ == "__main__":
    main()
"""

NOT_A_TEST = """
def hello():
    print('Hello World!')
"""

PY_SIMPLE_TEST = """#!/usr/bin/python
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
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_loader')

    def _test(self, name, content, exp_str, mode=0664):
        test_script = script.TemporaryScript(name, content,
                                             'avocado_loader_test',
                                             mode=mode)
        test_script.save()
        cmd_line = ('./scripts/avocado list -V %s' % test_script.path)
        result = process.run(cmd_line)
        self.assertIn('%s: 1' % exp_str, result.stdout)
        test_script.remove()

    def test_simple(self):
        self._test('simpletest.sh', SIMPLE_TEST, 'SIMPLE', 0775)

    def test_simple_not_exec(self):
        self._test('simpletest.sh', SIMPLE_TEST, 'NOT_A_TEST')

    def test_pass(self):
        self._test('passtest.py', AVOCADO_TEST_OK, 'INSTRUMENTED')

    def test_buggy_exec(self):
        self._test('buggytest.py', AVOCADO_TEST_BUGGY, 'SIMPLE', 0775)

    def test_buggy_not_exec(self):
        self._test('buggytest.py', AVOCADO_TEST_BUGGY, 'BUGGY')

    def test_load_not_a_test(self):
        self._test('notatest.py', NOT_A_TEST, 'SIMPLE', 0775)

    def test_load_not_a_test_not_exec(self):
        self._test('notatest.py', NOT_A_TEST, 'NOT_A_TEST')

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
