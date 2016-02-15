import ast
import sys

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

from avocado.core import safeloader
from avocado.utils import script


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


class DocstringTag(unittest.TestCase):

    def test_longline(self):
        docstring = ("This is a very long docstring in a single line. "
                     "Since we have nothing useful to put in here let's just "
                     "mention avocado: it's awesome, but that was not a tag. "
                     "a tag would be something line this: :avocado: enable")
        self.assertIsNotNone(safeloader.get_docstring_tag(docstring))

    def test_newlines(self):
        docstring = ("\n\n\nThis is a docstring with many new\n\nlines "
                     "followed by an avocado tag\n"
                     "\n\n:avocado: enable\n\n")
        self.assertIsNotNone(safeloader.get_docstring_tag(docstring))

    def test_enabled(self):
        self.assertTrue(safeloader.is_docstring_tag_enable(":avocado: enable"))
        self.assertTrue(safeloader.is_docstring_tag_enable(":avocado:\tenable"))
        self.assertFalse(safeloader.is_docstring_tag_enable(":AVOCADO: ENABLE"))
        self.assertFalse(safeloader.is_docstring_tag_enable(":avocado: enabled"))

    def test_disabled(self):
        self.assertTrue(safeloader.is_docstring_tag_disable(":avocado: disable"))
        self.assertTrue(safeloader.is_docstring_tag_disable(":avocado:\tdisable"))
        self.assertFalse(safeloader.is_docstring_tag_disable(":AVOCADO: DISABLE"))
        self.assertFalse(safeloader.is_docstring_tag_disable(":avocado: disabled"))


if __name__ == '__main__':
    unittest.main()
