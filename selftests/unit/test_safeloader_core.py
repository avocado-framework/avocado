import os
import sys
import unittest
import unittest.mock
from collections import OrderedDict

from avocado.core.safeloader.core import (find_avocado_tests,
                                          find_python_unittests)
from avocado.utils import script
from selftests.utils import TestCaseTmpDir, setup_avocado_loggers

setup_avocado_loggers()


KEEP_METHODS_ORDER = '''
from avocado import Test
from collections.abs import Sequence

class NotATest(Sequence[None]):
    pass

class MyClass(Test):
    def test2(self):
        pass

    def testA(self):
        pass

    def test1(self):
        pass

    def testZZZ(self):
        pass

    def test(self):
        pass
'''

IMPORT_NOT_NOT_PARENT_TEST = '''
from avocado import Test
class SomeClass(Test):
    def test_something(self): pass

from logging import Logger, LogRecord
class Anyclass(LogRecord): pass
class Anyclass(Logger): pass
'''

RECURSIVE_DISCOVERY_TEST1 = """
# skip is not used, but stresses the safeloader
from avocado import skip, Test

class BaseClass(Test):
    def test_basic(self):
        pass

class FirstChild(BaseClass):
    def test_first_child(self):
        pass

class SecondChild(FirstChild):
    '''
    :avocado: disable
    '''
    def test_second_child(self):
        pass
"""

RECURSIVE_DISCOVERY_TEST2 = """
from avocado import Test
from recursive_discovery_test1 import SecondChild

class ThirdChild(Test, SecondChild):
    '''
    :avocado: recursive
    '''
    def test_third_child(self):
        pass
"""


RECURSIVE_DISCOVERY_PYTHON_UNITTEST = """
# main is not used, but stresses the safeloader
from unittest import main, TestCase

class BaseClass(TestCase):
    '''
    :avocado: tags=base-tag
    :avocado: tags=base.tag
    '''
    def test_maybe_replaced_by_child(self):
        pass

    def test_basic(self):
        pass

class Child(BaseClass):
    '''
    :avocado: tags=child-tag
    :avocado: tags=child.tag
    '''
    def test_maybe_replaced_by_child(self):
        pass

    def test_child(self):
        pass
"""

# The following definitions will be used while creating a directory
# structure that contains a pre-defined set of modules that will be
# used on tests below

# A level 0 library containing a base test class
L0_LIB = """
from avocado import Test
class BaseL0(Test):
    def test_l0(self):
        pass
"""

L1_LIB1 = """
from ..l0lib import BaseL0
class BaseL1(BaseL0):
    def test_l1(self):
        pass
"""

L1_LIB2 = """
from .. import l0lib
class BaseL1(l0lib.BaseL0):
    def test_l1(self):
        pass
"""

L2_LIB1 = """
from ...l0lib import BaseL0
class BaseL2(BaseL0):
    def test_l2(self):
        pass
"""

L2_LIB2 = """
from ... import l0lib
class BaseL2(l0lib.BaseL0):
    def test_l2(self):
        pass
"""

L2_LIB3 = """
from l0lib import BaseL0
class BaseL2(BaseL0):
    def test_l3(self):
        pass
"""


def get_this_file():
    this_file = __file__
    if this_file.endswith('.py'):
        return this_file
    elif (this_file.endswith('.pyc') or this_file.endswith('.pyo')):
        return this_file[:-1]
    else:
        raise ValueError("Could not find the Python file associated with this "
                         "module")


class UnlimitedDiff(unittest.TestCase):

    """
    Serves two purposes: as a base class to test safeloader.find_class_and_methods
    and, while at it, to set unlimited diff on failure results.
    """

    def setUp(self):
        self.maxDiff = None


class FindClassAndMethods(UnlimitedDiff):

    def test_self(self):
        reference = OrderedDict({
            'UnlimitedDiff': [],

            'FindClassAndMethods': [('test_self', {}, []),
                                    ('test_methods_order', {}, []),
                                    ('test_import_not_on_parent', {}, []),
                                    ('test_recursive_discovery', {}, []),
                                    ('test_recursive_discovery_python_unittest', {}, [])],

            'MultiLevel': [('test_base_level0', {}, []),
                           ('test_relative_level0_name_from_level1', {}, []),
                           ('test_relative_level0_from_level1', {}, []),
                           ('test_relative_level0_name_from_level2', {}, []),
                           ('test_relative_level0_from_level2', {}, []),
                           ('test_non_relative_level0_from_level2', {}, [])]
             })
        found = find_python_unittests(get_this_file())
        self.assertEqual(reference, found)

    def test_methods_order(self):
        avocado_keep_methods_order = script.TemporaryScript(
            'keepmethodsorder.py',
            KEEP_METHODS_ORDER)
        avocado_keep_methods_order.save()
        expected_order = ['test2', 'testA', 'test1', 'testZZZ', 'test']
        tests = find_avocado_tests(avocado_keep_methods_order.path)[0]
        methods = [method[0] for method in tests['MyClass']]
        self.assertEqual(expected_order, methods)
        avocado_keep_methods_order.remove()

    def test_import_not_on_parent(self):
        avocado_test = script.TemporaryScript(
            'import_not_not_parent_test.py',
            IMPORT_NOT_NOT_PARENT_TEST)
        avocado_test.save()
        expected = ['test_something']
        tests = find_avocado_tests(avocado_test.path)[0]
        methods = [method[0] for method in tests['SomeClass']]
        self.assertEqual(expected, methods)
        avocado_test.remove()

    def test_recursive_discovery(self):
        avocado_recursive_discovery_test1 = script.TemporaryScript(
            'recursive_discovery_test1.py',
            RECURSIVE_DISCOVERY_TEST1)
        avocado_recursive_discovery_test1.save()
        avocado_recursive_discovery_test2 = script.TemporaryScript(
            'recursive_discovery_test2.py',
            RECURSIVE_DISCOVERY_TEST2)
        avocado_recursive_discovery_test2.save()

        sys.path.append(os.path.dirname(avocado_recursive_discovery_test1.path))
        tests = find_avocado_tests(avocado_recursive_discovery_test2.path)[0]
        expected = {'ThirdChild': [('test_third_child', {}, []),
                                   ('test_second_child', {}, []),
                                   ('test_first_child', {}, []),
                                   ('test_basic', {}, [])]}
        self.assertEqual(expected, tests)

    def test_recursive_discovery_python_unittest(self):
        temp_test = script.TemporaryScript(
            'recursive_discovery_python_unittest.py',
            RECURSIVE_DISCOVERY_PYTHON_UNITTEST)
        temp_test.save()
        tests = find_python_unittests(temp_test.path)
        expected = {'BaseClass': [('test_maybe_replaced_by_child',
                                   {'base-tag': None,
                                    'base.tag': None},
                                   []),
                                  ('test_basic',
                                   {'base-tag': None,
                                    'base.tag': None}, [])],
                    'Child': [('test_maybe_replaced_by_child',
                               {'child-tag': None,
                                'child.tag': None},
                               []),
                              ('test_child', {'child-tag': None,
                                              'child.tag': None},
                               []),
                              ('test_basic', {'base-tag': None,
                                              'base.tag': None},
                               [])]}
        self.assertEqual(expected, tests)


class MultiLevel(TestCaseTmpDir):

    def setUp(self):
        super(MultiLevel, self).setUp()
        init = script.Script(os.path.join(self.tmpdir.name, '__init__.py'),
                             '', mode=script.READ_ONLY_MODE)
        init.save()
        l0 = script.Script(os.path.join(self.tmpdir.name, 'l0lib.py'),
                           L0_LIB, mode=script.READ_ONLY_MODE)
        l0.save()

        l1_dir = os.path.join(self.tmpdir.name, 'l1')
        os.mkdir(l1_dir)
        l11 = script.Script(os.path.join(l1_dir, 'l1lib1.py'),
                            L1_LIB1, mode=script.READ_ONLY_MODE)
        l11.save()
        l12 = script.Script(os.path.join(l1_dir, 'l1lib2.py'),
                            L1_LIB2, mode=script.READ_ONLY_MODE)
        l12.save()

        l2_dir = os.path.join(l1_dir, 'l2')
        os.mkdir(l2_dir)
        l21 = script.Script(os.path.join(l2_dir, 'l2lib1.py'),
                            L2_LIB1, mode=script.READ_ONLY_MODE)
        l21.save()
        l22 = script.Script(os.path.join(l2_dir, 'l2lib2.py'),
                            L2_LIB2, mode=script.READ_ONLY_MODE)
        l22.save()
        l23 = script.Script(os.path.join(l2_dir, 'l2lib3.py'),
                            L2_LIB3, mode=script.READ_ONLY_MODE)
        l23.save()

    def test_base_level0(self):
        path = os.path.join(self.tmpdir.name, 'l0lib.py')
        self.assertEqual(find_avocado_tests(path)[0],
                         {'BaseL0': [('test_l0', {}, [])]})

    def test_relative_level0_name_from_level1(self):
        path = os.path.join(self.tmpdir.name, 'l1', 'l1lib1.py')
        self.assertEqual(find_avocado_tests(path)[0],
                         {'BaseL1': [('test_l1', {}, []),
                                     ('test_l0', {}, [])]})

    def test_relative_level0_from_level1(self):
        path = os.path.join(self.tmpdir.name, 'l1', 'l1lib2.py')
        self.assertEqual(find_avocado_tests(path)[0],
                         {'BaseL1': [('test_l1', {}, []),
                                     ('test_l0', {}, [])]})

    def test_relative_level0_name_from_level2(self):
        path = os.path.join(self.tmpdir.name, 'l1', 'l2', 'l2lib1.py')
        self.assertEqual(find_avocado_tests(path)[0],
                         {'BaseL2': [('test_l2', {}, []),
                                     ('test_l0', {}, [])]})

    def test_relative_level0_from_level2(self):
        path = os.path.join(self.tmpdir.name, 'l1', 'l2', 'l2lib2.py')
        self.assertEqual(find_avocado_tests(path)[0],
                         {'BaseL2': [('test_l2', {}, []),
                                     ('test_l0', {}, [])]})

    def test_non_relative_level0_from_level2(self):
        path = os.path.join(self.tmpdir.name, 'l1', 'l2', 'l2lib3.py')
        sys_path = sys.path + [self.tmpdir.name]
        with unittest.mock.patch('sys.path', sys_path):
            self.assertEqual(find_avocado_tests(path)[0],
                             {'BaseL2': [('test_l3', {}, []),
                                         ('test_l0', {}, [])]})


if __name__ == '__main__':
    unittest.main()
