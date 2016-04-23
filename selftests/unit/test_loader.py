import stat
import sys
import multiprocessing

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

from avocado.core import test
from avocado.core import exceptions
from avocado.core import loader
from avocado.utils import script

# We need to access protected members pylint: disable=W0212

#: What is commonly known as "0664" or "u=rw,g=rw,o=r"
DEFAULT_NON_EXEC_MODE = (stat.S_IRUSR | stat.S_IWUSR |
                         stat.S_IRGRP | stat.S_IWGRP |
                         stat.S_IROTH)


AVOCADO_TEST_OK = """#!/usr/bin/env python
from avocado import Test
from avocado import main

class PassTest(Test):
    def test(self):
        pass

if __name__ == "__main__":
    main()
"""

AVOCADO_TEST_OK_DISABLED = """#!/usr/bin/env python
from avocado import Test
from avocado import main

class PassTest(Test):
    '''
    Instrumented test, but disabled using an Avocado docstring tag
    :avocado: disable
    '''
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

AVOCADO_MULTIPLE_TESTS = """from avocado import Test

class MultipleMethods(Test):
    def test_one(self):
        pass
    def testTwo(self):
        pass
    def foo(self):
        pass
"""

AVOCADO_MULTIPLE_TESTS_SAME_NAME = """from avocado import Test

class MultipleMethods(Test):
    def test(self):
        raise
    def test(self):
        raise
    def test(self):
        pass
"""

AVOCADO_FOREIGN_TAGGED_ENABLE = """from foreignlib import Base

class First(Base):
    '''
    First actual test based on library base class

    This Base class happens to, fictionally, inherit from avocado.Test. Because
    Avocado can't tell that, a tag is necessary to signal that.

    :avocado: enable
    '''
    def test(self):
        pass
"""

AVOCADO_TEST_NESTED_TAGGED = """from avocado import Test
import avocado
import fmaslkfdsaf

class First(Test):
    '''
    :avocado: disable
    '''
    def test(self):
        class Third(Test):
            '''
            :avocado: enable
            '''
            def test_2(self):
                pass
        class Fourth(Second):
            '''
            :avocado: enable
            '''
            def test_3(self):
                pass
        pass
"""

AVOCADO_TEST_MULTIPLE_IMPORTS = """from avocado import Test
import avocado

class Second(avocado.Test):
    def test_1(self):
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
        test_parameters['name'] = test.TestName(0, test_parameters['name'])
        tc = test_class(**test_parameters)
        tc.test()
        # Load with params
        simple_with_params = simple_test.path + " 'foo bar' --baz"
        suite = self.loader.discover(simple_with_params, True)
        self.assertEqual(len(suite), 1)
        self.assertEqual(suite[0][1]["name"], simple_with_params)
        simple_test.remove()

    def test_load_simple_not_exec(self):
        simple_test = script.TemporaryScript('simpletest.sh', SIMPLE_TEST,
                                             'avocado_loader_unittest',
                                             mode=DEFAULT_NON_EXEC_MODE)
        simple_test.save()
        test_class, test_parameters = (
            self.loader.discover(simple_test.path, True)[0])
        self.assertTrue(test_class == test.NotATest, test_class)
        test_parameters['name'] = test.TestName(0, test_parameters['name'])
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
        self.assertTrue(test_class == 'PassTest', test_class)
        avocado_pass_test.remove()

    def test_load_not_a_test(self):
        avocado_not_a_test = script.TemporaryScript('notatest.py',
                                                    NOT_A_TEST,
                                                    'avocado_loader_unittest',
                                                    mode=DEFAULT_NON_EXEC_MODE)
        avocado_not_a_test.save()
        test_class, test_parameters = (
            self.loader.discover(avocado_not_a_test.path, True)[0])
        self.assertTrue(test_class == test.NotATest, test_class)
        test_parameters['name'] = test.TestName(0, test_parameters['name'])
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
        test_parameters['name'] = test.TestName(0, test_parameters['name'])
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
        test_parameters['name'] = test.TestName(0, test_parameters['name'])
        tc = test_class(**test_parameters)
        tc.test()
        avocado_simple_test.remove()

    def test_py_simple_test_notexec(self):
        avocado_simple_test = script.TemporaryScript('simpletest.py',
                                                     PY_SIMPLE_TEST,
                                                     'avocado_loader_unittest',
                                                     mode=DEFAULT_NON_EXEC_MODE)
        avocado_simple_test.save()
        test_class, test_parameters = (
            self.loader.discover(avocado_simple_test.path, True)[0])
        self.assertTrue(test_class == test.NotATest)
        test_parameters['name'] = test.TestName(0, test_parameters['name'])
        tc = test_class(**test_parameters)
        self.assertRaises(exceptions.NotATestError, tc.test)
        avocado_simple_test.remove()

    def test_multiple_methods(self):
        avocado_multiple_tests = script.TemporaryScript('multipletests.py',
                                                        AVOCADO_MULTIPLE_TESTS,
                                                        'avocado_multiple_tests_unittest',
                                                        mode=DEFAULT_NON_EXEC_MODE)
        avocado_multiple_tests.save()
        suite = self.loader.discover(avocado_multiple_tests.path, True)
        self.assertEqual(len(suite), 2)
        # Try to load only some of the tests
        suite = self.loader.discover(avocado_multiple_tests.path +
                                     ':MultipleMethods.testTwo', True)
        self.assertEqual(len(suite), 1)
        self.assertEqual(suite[0][1]["methodName"], 'testTwo')
        # Load using regexp
        suite = self.loader.discover(avocado_multiple_tests.path +
                                     ':.*_one', True)
        self.assertEqual(len(suite), 1)
        self.assertEqual(suite[0][1]["methodName"], 'test_one')
        # Load booth
        suite = self.loader.discover(avocado_multiple_tests.path +
                                     ':test.*', True)
        self.assertEqual(len(suite), 2)
        # Load none should return no tests
        self.assertTrue(not self.loader.discover(avocado_multiple_tests.path +
                                                 ":no_match", True))
        avocado_multiple_tests.remove()

    def test_multiple_methods_same_name(self):
        avocado_multiple_tests = script.TemporaryScript('multipletests.py',
                                                        AVOCADO_MULTIPLE_TESTS_SAME_NAME,
                                                        'avocado_multiple_tests_unittest',
                                                        mode=DEFAULT_NON_EXEC_MODE)
        avocado_multiple_tests.save()
        suite = self.loader.discover(avocado_multiple_tests.path, True)
        self.assertEqual(len(suite), 1)
        # Try to load only some of the tests
        suite = self.loader.discover(avocado_multiple_tests.path +
                                     ':MultipleMethods.test', True)
        self.assertEqual(len(suite), 1)
        self.assertEqual(suite[0][1]["methodName"], 'test')
        avocado_multiple_tests.remove()

    def test_load_foreign(self):
        avocado_pass_test = script.TemporaryScript('foreign.py',
                                                   AVOCADO_FOREIGN_TAGGED_ENABLE,
                                                   'avocado_loader_unittest')
        avocado_pass_test.save()
        test_class, test_parameters = (
            self.loader.discover(avocado_pass_test.path, True)[0])
        self.assertTrue(test_class == 'First', test_class)
        avocado_pass_test.remove()

    def test_load_pass_disable(self):
        avocado_pass_test = script.TemporaryScript('disable.py',
                                                   AVOCADO_TEST_OK_DISABLED,
                                                   'avocado_loader_unittest',
                                                   DEFAULT_NON_EXEC_MODE)
        avocado_pass_test.save()
        test_class, test_parameters = (
            self.loader.discover(avocado_pass_test.path, True)[0])
        self.assertTrue(test_class == test.NotATest)
        avocado_pass_test.remove()

    def test_load_tagged_nested(self):
        avocado_nested_test = script.TemporaryScript('nested.py',
                                                     AVOCADO_TEST_NESTED_TAGGED,
                                                     'avocado_loader_unittest',
                                                     DEFAULT_NON_EXEC_MODE)
        avocado_nested_test.save()
        test_class, test_parameters = (
            self.loader.discover(avocado_nested_test.path, True)[0])
        results = self.loader.discover(avocado_nested_test.path, True)
        self.assertTrue(test_class == test.NotATest)
        avocado_nested_test.remove()

    def test_load_multiple_imports(self):
        avocado_multiple_imp_test = script.TemporaryScript(
            'multipleimports.py',
            AVOCADO_TEST_MULTIPLE_IMPORTS,
            'avocado_loader_unittest')
        avocado_multiple_imp_test.save()
        test_class, test_parameters = (
            self.loader.discover(avocado_multiple_imp_test.path, True)[0])
        self.assertTrue(test_class == 'Second', test_class)
        avocado_multiple_imp_test.remove()


if __name__ == '__main__':
    unittest.main()
