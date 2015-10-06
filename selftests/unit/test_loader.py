import os
import re
import sys
import multiprocessing
import tempfile
import shutil

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

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

AVOCADO_TEST_OK_DISABLED = """#!/usr/bin/python
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

PY_SIMPLE_TEST = """#!/usr/bin/python
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
        self.assertTrue(test_class == 'PassTest', test_class)
        avocado_pass_test.remove()

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
                                                   0664)
        avocado_pass_test.save()
        test_class, test_parameters = (
            self.loader.discover(avocado_pass_test.path, True)[0])
        self.assertTrue(test_class == test.NotATest)
        avocado_pass_test.remove()


class DocstringTagTests(unittest.TestCase):

    def test_longline(self):
        docstring = ("This is a very long docstring in a single line. "
                     "Since we have nothing useful to put in here let's just "
                     "mention avocado: it's awesome, but that was not a tag. "
                     "a tag would be something line this: :avocado: enable")
        self.assertIsNotNone(loader.get_docstring_tag(docstring))

    def test_newlines(self):
        docstring = ("\n\n\nThis is a docstring with many new\n\nlines "
                     "followed by an avocado tag\n"
                     "\n\n:avocado: enable\n\n")
        self.assertIsNotNone(loader.get_docstring_tag(docstring))

    def test_enabled(self):
        self.assertTrue(loader.is_docstring_tag_enable(":avocado: enable"))
        self.assertTrue(loader.is_docstring_tag_enable(":avocado:\tenable"))
        self.assertFalse(loader.is_docstring_tag_enable(":AVOCADO: ENABLE"))
        self.assertFalse(loader.is_docstring_tag_enable(":avocado: enabled"))

    def test_disabled(self):
        self.assertTrue(loader.is_docstring_tag_disable(":avocado: disable"))
        self.assertTrue(loader.is_docstring_tag_disable(":avocado:\tdisable"))
        self.assertFalse(loader.is_docstring_tag_disable(":AVOCADO: DISABLE"))
        self.assertFalse(loader.is_docstring_tag_disable(":avocado: disabled"))

if __name__ == '__main__':
    unittest.main()
