import ast
import sys
import os
import re
import unittest

from avocado.core import safeloader
from avocado.utils import script

from .. import BASEDIR, setup_avocado_loggers


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

RECURSIVE_DISCOVERY_TEST1 = """
from avocado import Test

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
        self._test("class Foo(object): import foo as foo", {})


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
            'AvocadoModule': ['setUp',
                              'test_add_imported_empty',
                              'test_add_imported_object_from_module',
                              'test_add_imported_object_from_module_asname',
                              'test_is_not_avocado_test',
                              'test_is_avocado_test'],
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
                                    'test_directives_regex'],
            'FindClassAndMethods': ['test_self',
                                    'test_with_pattern',
                                    'test_with_base_class',
                                    'test_with_pattern_and_base_class',
                                    'test_methods_order',
                                    'test_recursive_discovery'],
            'UnlimitedDiff': ['setUp']
        }
        found = safeloader.find_class_and_methods(get_this_file())
        self.assertEqual(reference, found)

    def test_with_pattern(self):
        reference = {
            'AvocadoModule': ['test_add_imported_empty',
                              'test_add_imported_object_from_module',
                              'test_add_imported_object_from_module_asname',
                              'test_is_not_avocado_test',
                              'test_is_avocado_test'],
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
                                    'test_directives_regex'],
            'FindClassAndMethods': ['test_self',
                                    'test_with_pattern',
                                    'test_with_base_class',
                                    'test_with_pattern_and_base_class',
                                    'test_methods_order',
                                    'test_recursive_discovery'],
            'UnlimitedDiff': []
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
                                    'test_recursive_discovery'],
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
        expected = {'ThirdChild': [('test_third_child', {}),
                                   ('test_second_child', {}),
                                   ('test_first_child', {}),
                                   ('test_basic', {})]}
        self.assertEqual(expected, tests)


class AvocadoModule(unittest.TestCase):

    def setUp(self):
        self.path = os.path.abspath(os.path.dirname(get_this_file()))
        self.module = safeloader.AvocadoModule(self.path)

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
        self.assertFalse(self.module.is_avocado_test(ast.ClassDef()))

    def test_is_avocado_test(self):
        passtest_path = os.path.join(BASEDIR, 'examples', 'tests', 'passtest.py')
        passtest_module = safeloader.AvocadoModule(passtest_path)
        classes = [klass for klass in passtest_module.iter_classes()]
        # there's only one class and one *worthy* Test import in passtest.py
        self.assertEqual(len(classes), 1)
        self.assertEqual(len(passtest_module.test_imports), 1)
        self.assertEqual(len(passtest_module.mod_imports), 0)
        self.assertTrue(passtest_module.is_avocado_test(classes[0]))


if __name__ == '__main__':
    unittest.main()
