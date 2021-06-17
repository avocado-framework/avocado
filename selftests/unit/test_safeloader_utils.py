import ast
import collections
import unittest

from avocado.core.safeloader.utils import get_statement_import_as


class StatementImportAs(unittest.TestCase):

    def test_import(self):
        statement = ast.parse("import os").body[0]
        self.assertEqual({"os": "os"},
                         get_statement_import_as(statement))

    def test_import_alias(self):
        statement = ast.parse("import os as operatingsystem").body[0]
        self.assertEqual({"os": "operatingsystem"},
                         get_statement_import_as(statement))

    def test_import_from(self):
        statement = ast.parse("from os import path").body[0]
        self.assertEqual({"path": "path"},
                         get_statement_import_as(statement))

    def test_import_from_alias(self):
        statement = ast.parse("from os import path as stdlibpath").body[0]
        self.assertEqual({"path": "stdlibpath"},
                         get_statement_import_as(statement))

    def test_import_order(self):
        statement = ast.parse("import z, a").body[0]
        self.assertEqual(collections.OrderedDict({"z": "z", "a": "a"}),
                         get_statement_import_as(statement))

    def test_incorrect_statement_type(self):
        statement = ast.parse("pass").body[0]
        with self.assertRaises(ValueError):
            _ = get_statement_import_as(statement)
