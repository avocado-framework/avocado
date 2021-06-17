import ast
import unittest

from avocado.core.safeloader.imported import ImportedSymbol


class ModulePathComponents(unittest.TestCase):

    def test_single(self):
        self.assertEqual(ImportedSymbol._split_last_module_path_component('os'),
                         ('', 'os'))

    def test_compound(self):
        self.assertEqual(ImportedSymbol._split_last_module_path_component('os.path'),
                         ('os', 'path'))

    def test_relative_simple(self):
        self.assertEqual(ImportedSymbol._split_last_module_path_component('..utils'),
                         ('', 'utils'))

    def test_relative_compound(self):
        res = ImportedSymbol._split_last_module_path_component('...a.b.c.d')
        self.assertEqual(res, ('a.b.c', 'd'))


class ModuleRelativePath(unittest.TestCase):

    def test_no_relative_import(self):
        statement = ast.parse('import os').body[0]
        self.assertEqual(ImportedSymbol._get_relative_prefix(statement), '')

    def test_no_relative_import_from(self):
        statement = ast.parse('from os import path').body[0]
        self.assertEqual(ImportedSymbol._get_relative_prefix(statement), '')

    def test_relative_import_from_upper(self):
        statement = ast.parse('from ..selftests import utils').body[0]
        self.assertEqual(ImportedSymbol._get_relative_prefix(statement), '..')

    def test_relative_import_from_same(self):
        statement = ast.parse('from .utils import function').body[0]
        self.assertEqual(ImportedSymbol._get_relative_prefix(statement), '.')


class SymbolAndModulePathCommon(unittest.TestCase):

    def _check_basic(self, input_symbol, input_module_path, input_statement):
        """Checks all but to_str(), returning the imported_symbol instance."""
        statement = ast.parse(input_statement).body[0]
        symbol = ImportedSymbol.get_symbol_from_statement(statement)
        msg = 'Expected symbol name "%s", found "%s"' % (input_symbol,
                                                         symbol)
        self.assertEqual(symbol, input_symbol, msg)
        module_path = ImportedSymbol.get_module_path_from_statement(statement)
        msg = 'Expected module path "%s", found "%s"' % (input_module_path,
                                                         module_path)
        self.assertEqual(module_path, input_module_path, msg)
        imported_symbol = ImportedSymbol(symbol, module_path)
        self.assertEqual(imported_symbol,
                         ImportedSymbol.from_statement(statement))
        return imported_symbol

    def _check(self, input_symbol, input_module_path, *input_statements):
        statement_str_matches = []
        for input_statement in input_statements:
            imported_symbol = self._check_basic(input_symbol,
                                                input_module_path,
                                                input_statement)
            match = imported_symbol.to_str() == input_statement
            statement_str_matches.append(match)
        self.assertIn(True, statement_str_matches)


class SymbolAndModulePathImport(SymbolAndModulePathCommon):

    def test_symbol_only(self):
        self._check("os", "", "import os")

    def test_symbol_only_alias(self):
        self._check_basic("os", "", "import os as operatingsystem")

    def test_compound(self):
        self._check("path", "os", "import os.path", "from os import path")


class SymbolAndModulePathImportFrom(SymbolAndModulePathCommon):

    def test_symbol_module_path(self):
        self._check("path", "os", "from os import path")

    def test_symbol_module_path_compound(self):
        self._check("mock_open", "unittest.mock",
                    "from unittest.mock import mock_open")

    def test_symbol_module_path_only_relative(self):
        self._check("utils", "..", "from .. import utils")

    def test_symbol_module_path_from_relative(self):
        self._check("utils", "..selftests", "from ..selftests import utils")

    def test_symbol_module_path_from_relative_multiple(self):
        self._check("mod", "..selftests.utils",
                    "from ..selftests.utils import mod")


class SymbolAndModulePathErrors(unittest.TestCase):

    def test_incorrect_statement_type(self):
        statement = ast.parse("pass").body[0]
        with self.assertRaises(ValueError):
            _ = ImportedSymbol.get_symbol_from_statement(statement)


class RelativePath(unittest.TestCase):

    def test_same(self):
        imported_symbol = ImportedSymbol("symbol", ".module",
                                         "/abs/fs/location/test.py")
        self.assertEqual(imported_symbol.get_relative_module_fs_path(),
                         "/abs/fs/location")

    def test_upper(self):
        imported_symbol = ImportedSymbol("symbol", "..module",
                                         "/abs/fs/location/test.py")
        self.assertEqual(imported_symbol.get_relative_module_fs_path(),
                         "/abs/fs")

    def test_upper_from_statement(self):
        statement = ast.parse("from ..utils import utility").body[0]
        importer = "/abs/fs/location/of/selftests/unit/test_foo.py"
        symbol = ImportedSymbol.from_statement(statement,
                                               importer)
        self.assertEqual(symbol.get_relative_module_fs_path(),
                         "/abs/fs/location/of/selftests")

    def test_same_from_statement(self):
        statement = ast.parse("from .test_bar import symbol").body[0]
        importer = "/abs/fs/location/of/selftests/unit/test_foo.py"
        symbol = ImportedSymbol.from_statement(statement,
                                               importer)
        self.assertEqual(symbol.get_relative_module_fs_path(),
                         "/abs/fs/location/of/selftests/unit")


class ParentPath(unittest.TestCase):

    def test_compound(self):
        statement = ast.parse("from path import parent3").body[0]
        importer = "/abs/fs/location/of/imports.py"
        symbol = ImportedSymbol.from_statement(statement,
                                               importer)
        self.assertEqual(symbol.get_parent_fs_path(),
                         "/abs/fs/location/of/path")

    def test_compound_levels(self):
        statement = ast.parse("from .path.parent8 import Class8").body[0]
        importer = "/abs/fs/location/of/imports.py"
        symbol = ImportedSymbol.from_statement(statement,
                                               importer)
        self.assertEqual(symbol.get_parent_fs_path(),
                         "/abs/fs/location/of")
