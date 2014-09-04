#!/usr/bin/python

import unittest

from avocado import runtime
from avocado.utils import process


class TestGDBProcess(unittest.TestCase):

    def setUp(self):
        self.current_runtime_expr = runtime.GDB_RUN_BINARY_NAMES_EXPR[:]

    def cleanUp(self):
        runtime.GDB_RUN_BINARY_NAMES_EXPR = self.current_runtime_expr

    def test_should_run_inside_gdb(self):
        runtime.GDB_RUN_BINARY_NAMES_EXPR = ['foo']
        self.assertTrue(process.should_run_inside_gdb('foo'))
        self.assertTrue(process.should_run_inside_gdb('/usr/bin/foo'))
        self.assertFalse(process.should_run_inside_gdb('/usr/bin/fooz'))

        runtime.GDB_RUN_BINARY_NAMES_EXPR.append('foo:main')
        self.assertTrue(process.should_run_inside_gdb('foo'))
        self.assertFalse(process.should_run_inside_gdb('bar'))

        runtime.GDB_RUN_BINARY_NAMES_EXPR.append('bar:main.c:5')
        self.assertTrue(process.should_run_inside_gdb('bar'))
        self.assertFalse(process.should_run_inside_gdb('baz'))
        self.assertTrue(process.should_run_inside_gdb('bar 1 2 3'))
        self.assertTrue(process.should_run_inside_gdb('/usr/bin/bar 1 2 3'))

    def test_get_sub_process_klass(self):
        runtime.GDB_RUN_BINARY_NAMES_EXPR = []
        self.assertIs(process.get_sub_process_klass('/bin/true'),
                      process.SubProcess)

        runtime.GDB_RUN_BINARY_NAMES_EXPR.append('/bin/false')
        self.assertIs(process.get_sub_process_klass('/bin/false'),
                      process.GDBSubProcess)
        self.assertIs(process.get_sub_process_klass('false'),
                      process.GDBSubProcess)
        self.assertIs(process.get_sub_process_klass('true'),
                      process.SubProcess)

if __name__ == "__main__":
    unittest.main()
