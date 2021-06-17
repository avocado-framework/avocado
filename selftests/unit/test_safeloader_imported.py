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


class SymbolAndModulePath(unittest.TestCase):

    def _check(self, input_symbol, input_module_path, input_statement):
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
        self.assertEqual(imported_symbol.to_str(), input_statement)
        self.assertEqual(imported_symbol,
                         ImportedSymbol.from_statement(statement))

    def test_symbol_only(self):
        self._check("os", "", "import os")

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
