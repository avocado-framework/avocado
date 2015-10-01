import os
import sys
import unittest
import multiprocessing
import tempfile
import shutil

from avocado.core import test
from avocado.core import exceptions
from avocado.core import loader
from avocado.utils import script

# We need to access protected members pylint: disable=W0212

AVOCADO_TEST_OK = """#!/usr/bin/python
from avocado import Test
from avocado import main

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

AVOCADO_BASE_CLASS_TEST = """from avocado import Test

class MyBaseTest(Test):
    pass
"""

AVOCADO_INHERITED_CLASS_TEST = """from base import MyBaseTest

class MyInheritedTest(MyBaseTest):
    pass
"""

AVOCADO_MULTIPLE_TESTS = """from avocado import Test

class MultipleMethods(Test):
    def test_one(self):
        pass
    def testTwo(self):
        pass
    def foo(self):
        pass
"""


class LoaderTest(unittest.TestCase):

    def setUp(self):
        self.loader = loader.FileLoader(None, {})
        self.queue = multiprocessing.Queue()

    def test_load_simple(self):
        simple_test = script.TemporaryScript('simpletest.sh', SIMPLE_TEST,
                                             'avocado_loader_unittest')
        simple_test.save()
        test_class, test_parameters = (
            self.loader.discover(simple_test.path, True)[0])
        self.assertTrue(test_class == test.SimpleTest, test_class)
        tc = test_class(**test_parameters)
        tc.test()
        simple_test.remove()

    def test_load_simple_not_exec(self):
        simple_test = script.TemporaryScript('simpletest.sh', SIMPLE_TEST,
                                             'avocado_loader_unittest',
                                             mode=0664)
        simple_test.save()
        test_class, test_parameters = (
            self.loader.discover(simple_test.path, True)[0])
        self.assertTrue(test_class == test.NotATest, test_class)
        tc = test_class(**test_parameters)
        self.assertRaises(exceptions.NotATestError, tc.test)
        simple_test.remove()

    def test_load_pass(self):
        avocado_pass_test = script.TemporaryScript('passtest.py',
                                                   AVOCADO_TEST_OK,
                                                   'avocado_loader_unittest')
        avocado_pass_test.save()
        test_class, test_parameters = (
            self.loader.discover(avocado_pass_test.path, True)[0])
        self.assertTrue(str(test_class) == "<class 'passtest.PassTest'>",
                        str(test_class))
        self.assertTrue(issubclass(test_class, test.Test))
        tc = test_class(**test_parameters)
        tc.test()
        avocado_pass_test.remove()

    def test_load_inherited(self):
        avocado_base_test = script.TemporaryScript('base.py',
                                                   AVOCADO_BASE_CLASS_TEST,
                                                   'avocado_loader_unittest')
        avocado_base_test.save()
        test_class, test_parameters = (
            self.loader.discover(avocado_base_test.path, True)[0])
        self.assertTrue(str(test_class) == "<class 'base.MyBaseTest'>",
                        str(test_class))

        avocado_inherited_test = script.TemporaryScript('inherited.py',
                                                        AVOCADO_INHERITED_CLASS_TEST,
                                                        'avocado_loader_unittest')
        avocado_inherited_test.save()
        test_class, test_parameters = (
            self.loader.discover(avocado_inherited_test.path, True)[0])
        self.assertTrue(str(test_class) == "<class 'inherited.MyInheritedTest'>",
                        str(test_class))
        avocado_base_test.remove()
        avocado_inherited_test.remove()

    def test_load_not_a_test(self):
        avocado_not_a_test = script.TemporaryScript('notatest.py',
                                                    NOT_A_TEST,
                                                    'avocado_loader_unittest',
                                                    mode=0664)
        avocado_not_a_test.save()
        test_class, test_parameters = (
            self.loader.discover(avocado_not_a_test.path, True)[0])
        self.assertTrue(test_class == test.NotATest, test_class)
        tc = test_class(**test_parameters)
        self.assertRaises(exceptions.NotATestError, tc.test)
        avocado_not_a_test.remove()

    def test_load_not_a_test_exec(self):
        avocado_not_a_test = script.TemporaryScript('notatest.py', NOT_A_TEST,
                                                    'avocado_loader_unittest')
        avocado_not_a_test.save()
        test_class, test_parameters = (
            self.loader.discover(avocado_not_a_test.path, True)[0])
        self.assertTrue(test_class == test.SimpleTest, test_class)
        tc = test_class(**test_parameters)
        # The test can't be executed (no shebang), raising an OSError
        # (OSError: [Errno 8] Exec format error)
        self.assertRaises(OSError, tc.test)
        avocado_not_a_test.remove()

    def test_py_simple_test(self):
        avocado_simple_test = script.TemporaryScript('simpletest.py',
                                                     PY_SIMPLE_TEST,
                                                     'avocado_loader_unittest')
        avocado_simple_test.save()
        test_class, test_parameters = (
            self.loader.discover(avocado_simple_test.path, True)[0])
        self.assertTrue(test_class == test.SimpleTest)
        tc = test_class(**test_parameters)
        tc.test()
        avocado_simple_test.remove()

    def test_py_simple_test_notexec(self):
        avocado_simple_test = script.TemporaryScript('simpletest.py',
                                                     PY_SIMPLE_TEST,
                                                     'avocado_loader_unittest',
                                                     mode=0664)
        avocado_simple_test.save()
        test_class, test_parameters = (
            self.loader.discover(avocado_simple_test.path, True)[0])
        self.assertTrue(test_class == test.NotATest)
        tc = test_class(**test_parameters)
        self.assertRaises(exceptions.NotATestError, tc.test)
        avocado_simple_test.remove()

    def test_multiple_methods(self):
        avocado_multiple_tests = script.TemporaryScript('multipletests.py',
                                                        AVOCADO_MULTIPLE_TESTS,
                                                        'avocado_multiple_tests_unittest',
                                                        mode=0664)
        avocado_multiple_tests.save()
        suite = self.loader.discover(avocado_multiple_tests.path, True)
        self.assertEqual(len(suite), 2)
        avocado_multiple_tests.remove()


if __name__ == '__main__':
    unittest.main()
