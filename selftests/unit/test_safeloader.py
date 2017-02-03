import ast
import re
import unittest

from avocado.core import safeloader
from avocado.utils import script


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

    NO_TAGS = [":AVOCADO: TAGS:FAST",
               ":AVOCADO: TAGS=FAST",
               ":avocado: mytags=fast",
               ":avocado: tags",
               ":avocado: tag",
               ":avocado: tag=",
               ":this is not avocado: tags=foo",
               ":neither is this :avocado: tags:foo",
               ":tags:foo,bar",
               "tags=foo,bar"]

    VALID_TAGS = {":avocado: tags=fast": set(["fast"]),
                  ":avocado: tags=fast,network": set(["fast", "network"]),
                  ":avocado: tags=fast,,network": set(["fast", "network"]),
                  ":avocado: tags=slow,DISK": set(["slow", "DISK"]),
                  ":avocado: tags=SLOW,disk,disk": set(["SLOW", "disk"]),
                  ":avocado: tags=SLOW,disk, invalid": set(["SLOW", "disk"]),
                  ":avocado: tags=SLOW,disk , invalid": set(["SLOW", "disk"]),
                  ":avocado:\ttags=FAST": set(["FAST"]),
                  ":avocado: tags=": set([])}

    def test_longline(self):
        docstring = ("This is a very long docstring in a single line. "
                     "Since we have nothing useful to put in here let's just "
                     "mention avocado: it's awesome, but that was not a "
                     "directive. a tag would be something line this: "
                     ":avocado: enable")
        self.assertIsNotNone(safeloader.get_docstring_directive(docstring))

    def test_newlines(self):
        docstring = ("\n\n\nThis is a docstring with many new\n\nlines "
                     "followed by an avocado tag\n"
                     "\n\n:avocado: enable\n\n")
        self.assertIsNotNone(safeloader.get_docstring_directive(docstring))

    def test_enabled(self):
        self.assertTrue(safeloader.is_docstring_directive_enable(":avocado: enable"))
        self.assertTrue(safeloader.is_docstring_directive_enable(":avocado:\tenable"))
        self.assertFalse(safeloader.is_docstring_directive_enable(":AVOCADO: ENABLE"))
        self.assertFalse(safeloader.is_docstring_directive_enable(":avocado: enabled"))

    def test_disabled(self):
        self.assertTrue(safeloader.is_docstring_directive_disable(":avocado: disable"))
        self.assertTrue(safeloader.is_docstring_directive_disable(":avocado:\tdisable"))
        self.assertFalse(safeloader.is_docstring_directive_disable(":AVOCADO: DISABLE"))
        self.assertFalse(safeloader.is_docstring_directive_disable(":avocado: disabled"))

    def test_is_tags(self):
        for tag in self.VALID_TAGS:
            self.assertTrue(safeloader.is_docstring_directive_tags(tag))
        for tag in self.NO_TAGS:
            self.assertFalse(safeloader.is_docstring_directive_tags(tag))

    def test_get_tags_empty(self):
        for tag in self.NO_TAGS:
            self.assertEqual([], safeloader.get_docstring_directive_tags(tag))

    def test_get_tags(self):
        for raw, tags in self.VALID_TAGS.items():
            self.assertEqual(safeloader.get_docstring_directive_tags(raw), tags)


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
            'ModuleImportedAs': ['_test',
                                 'test_foo',
                                 'test_foo_as_bar',
                                 'test_foo_as_foo',
                                 'test_import_inside_class'],
            'DocstringDirectives': ['test_longline',
                                    'test_newlines',
                                    'test_enabled',
                                    'test_disabled',
                                    'test_is_tags',
                                    'test_get_tags_empty',
                                    'test_get_tags'],
            'FindClassAndMethods': ['test_self',
                                    'test_with_pattern',
                                    'test_with_base_class',
                                    'test_with_pattern_and_base_class'],
            'UnlimitedDiff': ['setUp']
        }
        found = safeloader.find_class_and_methods(get_this_file())
        self.assertEqual(reference, found)

    def test_with_pattern(self):
        reference = {
            'ModuleImportedAs': ['test_foo',
                                 'test_foo_as_bar',
                                 'test_foo_as_foo',
                                 'test_import_inside_class'],
            'DocstringDirectives': ['test_longline',
                                    'test_newlines',
                                    'test_enabled',
                                    'test_disabled',
                                    'test_is_tags',
                                    'test_get_tags_empty',
                                    'test_get_tags'],
            'FindClassAndMethods': ['test_self',
                                    'test_with_pattern',
                                    'test_with_base_class',
                                    'test_with_pattern_and_base_class'],
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
                                    'test_with_pattern_and_base_class'],
        }
        found = safeloader.find_class_and_methods(get_this_file(),
                                                  base_class='UnlimitedDiff')
        self.assertEqual(reference, found)

    def test_with_pattern_and_base_class(self):
        reference = {
            'FindClassAndMethods': ['test_with_pattern',
                                    'test_with_base_class',
                                    'test_with_pattern_and_base_class'],
        }
        found = safeloader.find_class_and_methods(get_this_file(),
                                                  re.compile(r'test_with.*'),
                                                  'UnlimitedDiff')
        self.assertEqual(reference, found)


if __name__ == '__main__':
    unittest.main()
