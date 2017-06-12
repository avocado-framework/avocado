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

    VALID_TAGS = {":avocado: tags=fast": set(["fast"]),
                  ":avocado: tags=fast,network": set(["fast", "network"]),
                  ":avocado: tags=fast,,network": set(["fast", "network"]),
                  ":avocado: tags=slow,DISK": set(["slow", "DISK"]),
                  ":avocado: tags=SLOW,disk,disk": set(["SLOW", "disk"]),
                  ":avocado:\ttags=FAST": set(["FAST"]),
                  ":avocado: tags=": set([]),
                  ":avocado: enable\n:avocado: tags=fast": set(["fast"]),
                  ":avocado: tags=fast,slow\n:avocado: enable": set(["fast", "slow"])
                  }

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
            self.assertEqual(set([]), safeloader.get_docstring_directives_tags(tag))

    def test_get_tags(self):
        for raw, tags in self.VALID_TAGS.items():
            self.assertEqual(safeloader.get_docstring_directives_tags(raw), tags)

    def test_directives_regex(self):
        """
        Tests the regular expressions that deal with docstring directives
        """
        for directive in self.VALID_DIRECTIVES:
            self.assertRegexpMatches(directive, safeloader.DOCSTRING_DIRECTIVE_RE)
        for directive in self.INVALID_DIRECTIVES:
            self.assertNotRegexpMatches(directive, safeloader.DOCSTRING_DIRECTIVE_RE)


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
                                    'test_get_tags_empty',
                                    'test_get_tags',
                                    'test_directives_regex'],
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
                                    'test_get_tags_empty',
                                    'test_get_tags',
                                    'test_directives_regex'],
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
