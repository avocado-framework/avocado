import ast
import os
import unittest

from avocado.core.safeloader.module import PythonModule
from selftests.unit.test_safeloader_core import get_this_file
from selftests.utils import BASEDIR


class PythonModuleSelf(unittest.TestCase):
    """
    Has tests based on this source code file
    """

    def setUp(self):
        self.path = os.path.abspath(os.path.dirname(get_this_file()))
        self.module = PythonModule(self.path)

    def test_add_imported_empty(self):
        self.assertEqual(self.module.imported_symbols, {})

    def test_add_imported_symbols_from_module(self):
        import_stm = ast.ImportFrom(module='foo', names=[ast.Name(name='bar',
                                                                  asname=None)])
        self.module.add_imported_symbol(import_stm)
        self.assertEqual(self.module.imported_symbols['bar'].module_path, 'foo')
        self.assertEqual(self.module.imported_symbols['bar'].symbol, 'bar')

    def test_add_imported_object_from_module_asname(self):
        import_stm = ast.ImportFrom(module='foo', names=[ast.Name(name='bar',
                                                                  asname='baz')])
        self.module.add_imported_symbol(import_stm)
        self.assertEqual(self.module.imported_symbols['baz'].module_path, 'foo')
        self.assertEqual(self.module.imported_symbols['baz'].symbol, 'bar')

    def test_is_not_avocado_test(self):
        self.assertFalse(self.module.is_matching_klass(ast.ClassDef()))

    def test_is_not_avocado_tests(self):
        for klass in self.module.iter_classes():
            self.assertFalse(self.module.is_matching_klass(klass))


class PythonModuleTest(unittest.TestCase):
    """
    Has tests based on other Python source code files
    """

    def test_is_avocado_test(self):
        passtest_path = os.path.join(BASEDIR, 'examples', 'tests', 'passtest.py')
        passtest_module = PythonModule(passtest_path)
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
        module = PythonModule(path, 'unittest', 'TestCase')
        for _ in module.iter_classes():
            pass
        self.assertIn('unittest', module.mod_imports)

    def test_import_relative(self):
        """Tests if relative imports are tracked on the module object."""
        path = os.path.join(BASEDIR, 'selftests', 'functional', 'test_basic.py')
        module = PythonModule(path)
        for _ in module.iter_classes():
            pass
        self.assertIn('TestCaseTmpDir', module.imported_symbols)
