import os
import sys
import unittest
import multiprocessing
import tempfile
import shutil

# simple magic for using scripts within a source tree
basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..',
                       '..', '..')
basedir = os.path.abspath(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.append(basedir)

from avocado.core import exceptions
from avocado.utils import script
from avocado import loader
from avocado import test

AVOCADO_TEST_OK = """#!/usr/bin/python
from avocado import main
from avocado import test

class PassTest(test.Test):
    def runTest(self):
        pass

if __name__ == "__main__":
    main()
"""

AVOCADO_TEST_BUGGY = """#!/usr/bin/python
from avocado import main
from avocado import test
import adsh

class PassTest(test.Test):
    def runTest(self):
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

AVOCADO_BASE_CLASS_TEST = """from avocado import test

class MyBaseTest(test.Test):
    pass
"""

AVOCADO_INHERITED_CLASS_TEST = """from base import MyBaseTest

class MyInheritedTest(MyBaseTest):
    pass
"""

AVOCADO_MULTIPLE_TESTS = """from avocado import test

class MultipleMethods(test.Test):
    def test_one(self):
        pass
    def testTwo(self):
        pass
    def foo(self):
        pass
"""


class _DebugJob(object):
    logdir = tempfile.mkdtemp()


class LoaderTest(unittest.TestCase):

    def setUp(self):
        self.job = _DebugJob
        self.loader = loader.TestLoader(job=self.job)
        self.queue = multiprocessing.Queue()

    def test_load_simple(self):
        simple_test = script.TemporaryScript('simpletest.sh', SIMPLE_TEST,
                                             'avocado_loader_unittest')
        simple_test.save()
        test_class, test_parameters = (
            self.loader.discover_tests(params={'id': simple_test.path})[0])
        self.assertTrue(test_class == test.SimpleTest, test_class)
        tc = test_class(**test_parameters)
        tc.runTest()
        simple_test.remove()

    def test_load_simple_not_exec(self):
        simple_test = script.TemporaryScript('simpletest.sh', SIMPLE_TEST,
                                             'avocado_loader_unittest',
                                             mode=0664)
        simple_test.save()
        test_class, test_parameters = (
            self.loader.discover_tests(params={'id': simple_test.path})[0])
        self.assertTrue(test_class == test.NotATest, test_class)
        tc = test_class(**test_parameters)
        self.assertRaises(exceptions.NotATestError, tc.runTest)
        simple_test.remove()

    def test_load_pass(self):
        avocado_pass_test = script.TemporaryScript('passtest.py',
                                                   AVOCADO_TEST_OK,
                                                   'avocado_loader_unittest')
        avocado_pass_test.save()
        test_class, test_parameters = (
            self.loader.discover_tests(params={'id': avocado_pass_test.path})[0])
        self.assertTrue(str(test_class) == "<class 'passtest.PassTest'>",
                        str(test_class))
        self.assertTrue(issubclass(test_class, test.Test))
        tc = test_class(**test_parameters)
        tc.runTest()
        avocado_pass_test.remove()

    def test_load_inherited(self):
        avocado_base_test = script.TemporaryScript('base.py',
                                                   AVOCADO_BASE_CLASS_TEST,
                                                   'avocado_loader_unittest')
        avocado_base_test.save()
        test_class, test_parameters = (
            self.loader.discover_tests(params={'id': avocado_base_test.path})[0])
        self.assertTrue(str(test_class) == "<class 'base.MyBaseTest'>",
                        str(test_class))

        avocado_inherited_test = script.TemporaryScript('inherited.py',
                                                        AVOCADO_INHERITED_CLASS_TEST,
                                                        'avocado_loader_unittest')
        avocado_inherited_test.save()
        test_class, test_parameters = (
            self.loader.discover_tests(params={'id': avocado_inherited_test.path})[0])
        self.assertTrue(str(test_class) == "<class 'inherited.MyInheritedTest'>",
                        str(test_class))
        avocado_base_test.remove()
        avocado_inherited_test.remove()

    def test_load_buggy_exec(self):
        avocado_buggy_test = script.TemporaryScript('buggytest.py',
                                                    AVOCADO_TEST_BUGGY,
                                                    'avocado_loader_unittest')
        avocado_buggy_test.save()
        test_class, test_parameters = (
            self.loader.discover_tests(params={'id': avocado_buggy_test.path})[0])
        self.assertTrue(test_class == test.SimpleTest, test_class)
        tc = test_class(**test_parameters)
        self.assertRaises(exceptions.TestFail, tc.runTest)
        avocado_buggy_test.remove()

    def test_load_buggy_not_exec(self):
        avocado_buggy_test = script.TemporaryScript('buggytest.py',
                                                    AVOCADO_TEST_BUGGY,
                                                    'avocado_loader_unittest',
                                                    mode=0664)
        avocado_buggy_test.save()
        test_class, test_parameters = (
            self.loader.discover_tests(params={'id': avocado_buggy_test.path})[0])
        self.assertTrue(test_class == test.BuggyTest, test_class)
        tc = test_class(**test_parameters)
        self.assertRaises(ImportError, tc.runTest)
        avocado_buggy_test.remove()

    def test_load_not_a_test(self):
        avocado_not_a_test = script.TemporaryScript('notatest.py',
                                                    NOT_A_TEST,
                                                    'avocado_loader_unittest',
                                                    mode=0664)
        avocado_not_a_test.save()
        test_class, test_parameters = (
            self.loader.discover_tests(params={'id': avocado_not_a_test.path})[0])
        self.assertTrue(test_class == test.NotATest, test_class)
        tc = test_class(**test_parameters)
        self.assertRaises(exceptions.NotATestError, tc.runTest)
        avocado_not_a_test.remove()

    def test_load_not_a_test_exec(self):
        avocado_not_a_test = script.TemporaryScript('notatest.py', NOT_A_TEST,
                                                    'avocado_loader_unittest')
        avocado_not_a_test.save()
        test_class, test_parameters = (
            self.loader.discover_tests(params={'id': avocado_not_a_test.path})[0])
        self.assertTrue(test_class == test.SimpleTest, test_class)
        tc = test_class(**test_parameters)
        # The test can't be executed (no shebang), raising an OSError
        # (OSError: [Errno 8] Exec format error)
        self.assertRaises(OSError, tc.runTest)
        avocado_not_a_test.remove()

    def test_py_simple_test(self):
        avocado_simple_test = script.TemporaryScript('simpletest.py',
                                                     PY_SIMPLE_TEST,
                                                     'avocado_loader_unittest')
        avocado_simple_test.save()
        test_class, test_parameters = (
            self.loader.discover_tests(params={'id': avocado_simple_test.path})[0])
        self.assertTrue(test_class == test.SimpleTest)
        tc = test_class(**test_parameters)
        tc.runTest()
        avocado_simple_test.remove()

    def test_py_simple_test_notexec(self):
        avocado_simple_test = script.TemporaryScript('simpletest.py',
                                                     PY_SIMPLE_TEST,
                                                     'avocado_loader_unittest',
                                                     mode=0664)
        avocado_simple_test.save()
        test_class, test_parameters = (
            self.loader.discover_tests(params={'id': avocado_simple_test.path})[0])
        self.assertTrue(test_class == test.NotATest)
        tc = test_class(**test_parameters)
        self.assertRaises(exceptions.NotATestError, tc.runTest)
        avocado_simple_test.remove()

    def test_multiple_methods(self):
        avocado_multiple_tests = script.TemporaryScript('multipletests.py',
                                                        AVOCADO_MULTIPLE_TESTS,
                                                        'avocado_multiple_tests_unittest',
                                                        mode=0664)
        avocado_multiple_tests.save()
        suite = self.loader.discover_tests(params={'id': avocado_multiple_tests.path})
        self.assertEqual(len(suite), 2)
        avocado_multiple_tests.remove()

    def tearDown(self):
        if os.path.isdir(self.job.logdir):
            shutil.rmtree(self.job.logdir)

if __name__ == '__main__':
    unittest.main()
