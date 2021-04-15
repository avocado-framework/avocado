import ast
import os
import re
import sys
import unittest.mock

from avocado.core import safeloader
from avocado.utils import script
from selftests.utils import BASEDIR, TestCaseTmpDir, setup_avocado_loggers

setup_avocado_loggers()


KEEP_METHODS_ORDER = '''
from avocado import Test

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
# used on tests bellow

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


class ModuleImportedAs(unittest.TestCase):

    def _test(self, content, result):
        temp_script = script.TemporaryScript('temp.py', content,
                                             'avocado_loader_unittest')
        temp_script.save()
        module = ast.parse(content, temp_script.path)
        temp_script.remove()
        self.assertEqual(result, safeloader.modules_imported_as(module))

    def test_foo(self):
        self._test('import foo', {'foo': 'foo'})

    def test_foo_as_bar(self):
        self._test('import foo as bar', {'foo': 'bar'})

    def test_foo_as_foo(self):
        self._test('import foo as foo', {'foo': 'foo'})

    def test_import_inside_class(self):
        self._test("class Foo: import foo as foo", {})


class DocstringDirectives(unittest.TestCase):

    VALID_DIRECTIVES = [":avocado: foo",
                        " :avocado: foo",
                        " :avocado: foo ",
                        ":avocado:\tfoo",
                        ":avocado: \tfoo",
                        ":avocado: foo:",
                        ":avocado: foo=",
                        ":avocado: foo=bar:123",
                        ":avocado: 42=life",
                        ":avocado: foo,bar,baz",
                        ":avocado: foo,bar,baz:extra",
                        ":avocado: a=,,,",
                        ":avocado: a=x:y:z,None"]

    INVALID_DIRECTIVES = [":avocado:\nfoo",
                          ":avocado: \nfoo",
                          ":avocado:foo",
                          ":avocado:_foo",
                          ":avocado: ?notsure",
                          ":avocado: ,foo,bar,baz",
                          ":avocado: foo,bar,baz!!!",
                          ":avocado: =",
                          ":avocado: ,"]

    NO_TAGS = [":AVOCADO: TAGS:FAST",
               ":AVOCADO: TAGS=FAST",
               ":avocado: mytags=fast",
               ":avocado: tags",
               ":avocado: tag",
               ":avocado: tag=",
               ":this is not avocado: tags=foo",
               ":neither is this :avocado: tags:foo",
               ":tags:foo,bar",
               "tags=foo,bar",
               ":avocado: tags=SLOW,disk, invalid",
               ":avocado: tags=SLOW,disk , invalid"]

    NO_REQS = [":AVOCADO: REQUIREMENT=['FOO':'BAR']",
               ":avocado: requirement={'foo':'bar'}",
               ":avocado: requirement={foo",
               ":avocado: requirements=",
               ":avocado: requirement="]

    def test_longline(self):
        docstring = ("This is a very long docstring in a single line. "
                     "Since we have nothing useful to put in here let's just "
                     "mention avocado: it's awesome, but that was not a "
                     "directive. a tag would be something line this: "
                     ":avocado: enable")
        self.assertIsNotNone(safeloader.get_docstring_directives(docstring))

    def test_newlines(self):
        docstring = ("\n\n\nThis is a docstring with many new\n\nlines "
                     "followed by an avocado tag\n"
                     "\n\n:avocado: enable\n\n")
        self.assertIsNotNone(safeloader.get_docstring_directives(docstring))

    def test_enabled(self):
        self.assertTrue(safeloader.check_docstring_directive(":avocado: enable", 'enable'))
        self.assertTrue(safeloader.check_docstring_directive(":avocado:\tenable", 'enable'))
        self.assertTrue(safeloader.check_docstring_directive(":avocado: enable\n:avocado: tags=fast", 'enable'))
        self.assertFalse(safeloader.check_docstring_directive(":AVOCADO: ENABLE", 'enable'))
        self.assertFalse(safeloader.check_docstring_directive(":avocado: enabled", 'enable'))

    def test_disabled(self):
        self.assertTrue(safeloader.check_docstring_directive(":avocado: disable", 'disable'))
        self.assertTrue(safeloader.check_docstring_directive(":avocado:\tdisable", 'disable'))
        self.assertFalse(safeloader.check_docstring_directive(":AVOCADO: DISABLE", 'disable'))
        self.assertFalse(safeloader.check_docstring_directive(":avocado: disabled", 'disable'))

    def test_get_tags_empty(self):
        for tag in self.NO_TAGS:
            self.assertEqual({}, safeloader.get_docstring_directives_tags(tag))

    def test_tag_single(self):
        raw = ":avocado: tags=fast"
        exp = {"fast": None}
        self.assertEqual(safeloader.get_docstring_directives_tags(raw), exp)

    def test_tag_double(self):
        raw = ":avocado: tags=fast,network"
        exp = {"fast": None, "network": None}
        self.assertEqual(safeloader.get_docstring_directives_tags(raw), exp)

    def test_tag_double_with_empty(self):
        raw = ":avocado: tags=fast,,network"
        exp = {"fast": None, "network": None}
        self.assertEqual(safeloader.get_docstring_directives_tags(raw), exp)

    def test_tag_lowercase_uppercase(self):
        raw = ":avocado: tags=slow,DISK"
        exp = {"slow": None, "DISK": None}
        self.assertEqual(safeloader.get_docstring_directives_tags(raw), exp)

    def test_tag_duplicate(self):
        raw = ":avocado: tags=SLOW,disk,disk"
        exp = {"SLOW": None, "disk": None}
        self.assertEqual(safeloader.get_docstring_directives_tags(raw), exp)

    def test_tag_tab_separator(self):
        raw = ":avocado:\ttags=FAST"
        exp = {"FAST": None}
        self.assertEqual(safeloader.get_docstring_directives_tags(raw), exp)

    def test_tag_empty(self):
        raw = ":avocado: tags="
        exp = {}
        self.assertEqual(safeloader.get_docstring_directives_tags(raw), exp)

    def test_tag_newline_before(self):
        raw = ":avocado: enable\n:avocado: tags=fast"
        exp = {"fast": None}
        self.assertEqual(safeloader.get_docstring_directives_tags(raw), exp)

    def test_tag_newline_after(self):
        raw = ":avocado: tags=fast,slow\n:avocado: enable"
        exp = {"fast": None, "slow": None}
        self.assertEqual(safeloader.get_docstring_directives_tags(raw), exp)

    def test_tag_keyval_single(self):
        raw = ":avocado: tags=fast,arch:x86_64"
        exp = {"fast": None, "arch": set(["x86_64"])}
        self.assertEqual(safeloader.get_docstring_directives_tags(raw), exp)

    def test_tag_keyval_double(self):
        raw = ":avocado: tags=fast,arch:x86_64,arch:ppc64"
        exp = {"fast": None, "arch": set(["x86_64", "ppc64"])}
        self.assertEqual(safeloader.get_docstring_directives_tags(raw), exp)

    def test_tag_keyval_duplicate(self):
        raw = ":avocado: tags=fast,arch:x86_64,arch:ppc64,arch:x86_64"
        exp = {"fast": None, "arch": set(["x86_64", "ppc64"])}
        self.assertEqual(safeloader.get_docstring_directives_tags(raw), exp)

    def test_get_requirement_empty(self):
        for req in self.NO_REQS:
            self.assertEqual([], safeloader.get_docstring_directives_requirements(req))

    def test_requirement_single(self):
        raw = ":avocado: requirement={\"foo\":\"bar\"}"
        exp = [{"foo": "bar"}]
        self.assertEqual(safeloader.get_docstring_directives_requirements(raw), exp)

    def test_requirement_double(self):
        raw = ":avocado: requirement={\"foo\":\"bar\"}\n:avocado: requirement={\"uri\":\"http://foo.bar\"}"
        exp = [{"foo": "bar"}, {"uri": "http://foo.bar"}]
        self.assertEqual(safeloader.get_docstring_directives_requirements(raw), exp)

    def test_directives_regex(self):
        """
        Tests the regular expressions that deal with docstring directives
        """
        for directive in self.VALID_DIRECTIVES:
            self.assertTrue(safeloader.DOCSTRING_DIRECTIVE_RE.match(directive))
        for directive in self.INVALID_DIRECTIVES:
            self.assertFalse(safeloader.DOCSTRING_DIRECTIVE_RE.match(directive))


class UnlimitedDiff(unittest.TestCase):

    """
    Serves two purposes: as a base class to test safeloader.find_class_and_methods
    and, while at it, to set unlimited diff on failure results.
    """

    def setUp(self):
        self.maxDiff = None


class FindClassAndMethods(UnlimitedDiff):

    def test_self(self):
        reference = {
            'PythonModuleSelf': ['setUp',
                                 'test_add_imported_empty',
                                 'test_add_imported_object_from_module',
                                 'test_add_imported_object_from_module_asname',
                                 'test_is_not_avocado_test',
                                 'test_is_not_avocado_tests'],
            'PythonModule': ['test_is_avocado_test',
                             'test_import_of_all_module_level',
                             'test_import_relative'],
            'ModuleImportedAs': ['_test',
                                 'test_foo',
                                 'test_foo_as_bar',
                                 'test_foo_as_foo',
                                 'test_import_inside_class'],
            'DocstringDirectives': ['test_longline',
                                    'test_newlines',
                                    'test_enabled',
                                    'test_disabled',
                                    'test_get_tags_empty',
                                    'test_tag_single',
                                    'test_tag_double',
                                    'test_tag_double_with_empty',
                                    'test_tag_lowercase_uppercase',
                                    'test_tag_duplicate',
                                    'test_tag_tab_separator',
                                    'test_tag_empty',
                                    'test_tag_newline_before',
                                    'test_tag_newline_after',
                                    'test_tag_keyval_single',
                                    'test_tag_keyval_double',
                                    'test_tag_keyval_duplicate',
                                    'test_get_requirement_empty',
                                    'test_requirement_single',
                                    'test_requirement_double',
                                    'test_directives_regex'],
            'FindClassAndMethods': ['test_self',
                                    'test_with_pattern',
                                    'test_with_base_class',
                                    'test_with_pattern_and_base_class',
                                    'test_methods_order',
                                    'test_import_not_on_parent',
                                    'test_recursive_discovery',
                                    'test_recursive_discovery_python_unittest'],
            'UnlimitedDiff': ['setUp'],
            'MultiLevel': ['setUp',
                           'test_base_level0',
                           'test_relative_level0_name_from_level1',
                           'test_relative_level0_from_level1',
                           'test_relative_level0_name_from_level2',
                           'test_relative_level0_from_level2',
                           'test_non_relative_level0_from_level2'],
        }
        found = safeloader.find_class_and_methods(get_this_file())
        self.assertEqual(reference, found)

    def test_with_pattern(self):
        reference = {
            'PythonModuleSelf': ['test_add_imported_empty',
                                 'test_add_imported_object_from_module',
                                 'test_add_imported_object_from_module_asname',
                                 'test_is_not_avocado_test',
                                 'test_is_not_avocado_tests'],
            'PythonModule': ['test_is_avocado_test',
                             'test_import_of_all_module_level',
                             'test_import_relative'],
            'ModuleImportedAs': ['test_foo',
                                 'test_foo_as_bar',
                                 'test_foo_as_foo',
                                 'test_import_inside_class'],
            'DocstringDirectives': ['test_longline',
                                    'test_newlines',
                                    'test_enabled',
                                    'test_disabled',
                                    'test_get_tags_empty',
                                    'test_tag_single',
                                    'test_tag_double',
                                    'test_tag_double_with_empty',
                                    'test_tag_lowercase_uppercase',
                                    'test_tag_duplicate',
                                    'test_tag_tab_separator',
                                    'test_tag_empty',
                                    'test_tag_newline_before',
                                    'test_tag_newline_after',
                                    'test_tag_keyval_single',
                                    'test_tag_keyval_double',
                                    'test_tag_keyval_duplicate',
                                    'test_get_requirement_empty',
                                    'test_requirement_single',
                                    'test_requirement_double',
                                    'test_directives_regex'],
            'FindClassAndMethods': ['test_self',
                                    'test_with_pattern',
                                    'test_with_base_class',
                                    'test_with_pattern_and_base_class',
                                    'test_methods_order',
                                    'test_import_not_on_parent',
                                    'test_recursive_discovery',
                                    'test_recursive_discovery_python_unittest'],
            'UnlimitedDiff': [],
            'MultiLevel': ['test_base_level0',
                           'test_relative_level0_name_from_level1',
                           'test_relative_level0_from_level1',
                           'test_relative_level0_name_from_level2',
                           'test_relative_level0_from_level2',
                           'test_non_relative_level0_from_level2'],
        }
        found = safeloader.find_class_and_methods(get_this_file(),
                                                  re.compile(r'test.*'))
        self.assertEqual(reference, found)

    def test_with_base_class(self):
        reference = {
            'FindClassAndMethods': ['test_self',
                                    'test_with_pattern',
                                    'test_with_base_class',
                                    'test_with_pattern_and_base_class',
                                    'test_methods_order',
                                    'test_import_not_on_parent',
                                    'test_recursive_discovery',
                                    'test_recursive_discovery_python_unittest'],
        }
        found = safeloader.find_class_and_methods(get_this_file(),
                                                  base_class='UnlimitedDiff')
        self.assertEqual(reference, found)

    def test_with_pattern_and_base_class(self):
        reference = {
            'FindClassAndMethods': ['test_with_pattern',
                                    'test_with_base_class',
                                    'test_with_pattern_and_base_class']
        }
        found = safeloader.find_class_and_methods(get_this_file(),
                                                  re.compile(r'test_with.*'),
                                                  'UnlimitedDiff')
        self.assertEqual(reference, found)

    def test_methods_order(self):
        avocado_keep_methods_order = script.TemporaryScript(
            'keepmethodsorder.py',
            KEEP_METHODS_ORDER)
        avocado_keep_methods_order.save()
        expected_order = ['test2', 'testA', 'test1', 'testZZZ', 'test']
        tests = safeloader.find_avocado_tests(avocado_keep_methods_order.path)[0]
        methods = [method[0] for method in tests['MyClass']]
        self.assertEqual(expected_order, methods)
        avocado_keep_methods_order.remove()

    def test_import_not_on_parent(self):
        avocado_test = script.TemporaryScript(
            'import_not_not_parent_test.py',
            IMPORT_NOT_NOT_PARENT_TEST)
        avocado_test.save()
        expected = ['test_something']
        tests = safeloader.find_avocado_tests(avocado_test.path)[0]
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
        tests = safeloader.find_avocado_tests(avocado_recursive_discovery_test2.path)[0]
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
        tests = safeloader.find_python_unittests(temp_test.path)
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


class PythonModuleSelf(unittest.TestCase):
    """
    Has tests based on this source code file
    """

    def setUp(self):
        self.path = os.path.abspath(os.path.dirname(get_this_file()))
        self.module = safeloader.PythonModule(self.path)

    def test_add_imported_empty(self):
        self.assertEqual(self.module.imported_objects, {})

    def test_add_imported_object_from_module(self):
        import_stm = ast.ImportFrom(module='foo', names=[ast.Name(name='bar',
                                                                  asname=None)])
        self.module.add_imported_object(import_stm)
        self.assertEqual(self.module.imported_objects['bar'],
                         os.path.join(self.path, 'foo', 'bar'))

    def test_add_imported_object_from_module_asname(self):
        import_stm = ast.ImportFrom(module='foo', names=[ast.Name(name='bar',
                                                                  asname='baz')])
        self.module.add_imported_object(import_stm)
        self.assertEqual(self.module.imported_objects['baz'],
                         os.path.join(self.path, 'foo', 'bar'))

    def test_is_not_avocado_test(self):
        self.assertFalse(self.module.is_matching_klass(ast.ClassDef()))

    def test_is_not_avocado_tests(self):
        for klass in self.module.iter_classes():
            self.assertFalse(self.module.is_matching_klass(klass))


class PythonModule(unittest.TestCase):
    """
    Has tests based on other Python source code files
    """

    def test_is_avocado_test(self):
        passtest_path = os.path.join(BASEDIR, 'examples', 'tests', 'passtest.py')
        passtest_module = safeloader.PythonModule(passtest_path)
        classes = [klass for klass in passtest_module.iter_classes()]
        # there's only one class and one *worthy* Test import in passtest.py
        self.assertEqual(len(classes), 1)
        self.assertEqual(len(passtest_module.klass_imports), 1)
        self.assertEqual(len(passtest_module.mod_imports), 0)
        self.assertTrue(passtest_module.is_matching_klass(classes[0]))

    def test_import_of_all_module_level(self):
        """
        Checks if all levels of a module import are taken into account

        This specific source file imports unittest.mock, and we want to
        make sure that unittest is accounted for.
        """
        path = os.path.join(BASEDIR, 'selftests', 'unit', 'test_loader.py')
        module = safeloader.PythonModule(path, 'unittest', 'TestCase')
        for _ in module.iter_classes():
            pass
        self.assertIn('unittest', module.mod_imports)

    def test_import_relative(self):
        """Tests if relative imports are tracked on the module object."""
        path = os.path.join(BASEDIR, 'selftests', 'functional', 'test_basic.py')
        module = safeloader.PythonModule(path)
        for _ in module.iter_classes():
            pass
        self.assertIn('TestCaseTmpDir', module.imported_objects)


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
        self.assertEqual(safeloader.find_avocado_tests(path)[0],
                         {'BaseL0': [('test_l0', {}, [])]})

    def test_relative_level0_name_from_level1(self):
        path = os.path.join(self.tmpdir.name, 'l1', 'l1lib1.py')
        self.assertEqual(safeloader.find_avocado_tests(path)[0],
                         {'BaseL1': [('test_l1', {}, []),
                                     ('test_l0', {}, [])]})

    def test_relative_level0_from_level1(self):
        path = os.path.join(self.tmpdir.name, 'l1', 'l1lib2.py')
        self.assertEqual(safeloader.find_avocado_tests(path)[0],
                         {'BaseL1': [('test_l1', {}, []),
                                     ('test_l0', {}, [])]})

    def test_relative_level0_name_from_level2(self):
        path = os.path.join(self.tmpdir.name, 'l1', 'l2', 'l2lib1.py')
        self.assertEqual(safeloader.find_avocado_tests(path)[0],
                         {'BaseL2': [('test_l2', {}, []),
                                     ('test_l0', {}, [])]})

    def test_relative_level0_from_level2(self):
        path = os.path.join(self.tmpdir.name, 'l1', 'l2', 'l2lib2.py')
        self.assertEqual(safeloader.find_avocado_tests(path)[0],
                         {'BaseL2': [('test_l2', {}, []),
                                     ('test_l0', {}, [])]})

    def test_non_relative_level0_from_level2(self):
        path = os.path.join(self.tmpdir.name, 'l1', 'l2', 'l2lib3.py')
        sys_path = sys.path + [self.tmpdir.name]
        with unittest.mock.patch('sys.path', sys_path):
            self.assertEqual(safeloader.find_avocado_tests(path)[0],
                             {'BaseL2': [('test_l3', {}, []),
                                         ('test_l0', {}, [])]})


if __name__ == '__main__':
    unittest.main()
