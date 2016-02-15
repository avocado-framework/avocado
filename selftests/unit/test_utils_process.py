import os
import sys
from mock import MagicMock, patch

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

from avocado.utils import gdb
from avocado.utils import process
from avocado.utils import path


class TestGDBProcess(unittest.TestCase):

    def setUp(self):
        self.current_runtime_expr = gdb.GDB_RUN_BINARY_NAMES_EXPR[:]

    def cleanUp(self):
        gdb.GDB_RUN_BINARY_NAMES_EXPR = self.current_runtime_expr

    def test_should_run_inside_gdb(self):
        gdb.GDB_RUN_BINARY_NAMES_EXPR = ['foo']
        self.assertTrue(process.should_run_inside_gdb('foo'))
        self.assertTrue(process.should_run_inside_gdb('/usr/bin/foo'))
        self.assertFalse(process.should_run_inside_gdb('/usr/bin/fooz'))

        gdb.GDB_RUN_BINARY_NAMES_EXPR.append('foo:main')
        self.assertTrue(process.should_run_inside_gdb('foo'))
        self.assertFalse(process.should_run_inside_gdb('bar'))

        gdb.GDB_RUN_BINARY_NAMES_EXPR.append('bar:main.c:5')
        self.assertTrue(process.should_run_inside_gdb('bar'))
        self.assertFalse(process.should_run_inside_gdb('baz'))
        self.assertTrue(process.should_run_inside_gdb('bar 1 2 3'))
        self.assertTrue(process.should_run_inside_gdb('/usr/bin/bar 1 2 3'))

    def test_should_run_inside_gdb_malformed_command(self):
        gdb.GDB_RUN_BINARY_NAMES_EXPR = ['/bin/virsh']
        cmd = """/bin/virsh node-memory-tune --shm-sleep-millisecs ~!@#$%^*()-=[]{}|_+":;'`,>?. """
        self.assertTrue(process.should_run_inside_gdb(cmd))
        self.assertFalse(process.should_run_inside_gdb("foo bar baz"))
        self.assertFalse(process.should_run_inside_gdb("foo ' "))

    def test_get_sub_process_klass(self):
        gdb.GDB_RUN_BINARY_NAMES_EXPR = []
        self.assertIs(process.get_sub_process_klass('/bin/true'),
                      process.SubProcess)

        gdb.GDB_RUN_BINARY_NAMES_EXPR.append('/bin/false')
        self.assertIs(process.get_sub_process_klass('/bin/false'),
                      process.GDBSubProcess)
        self.assertIs(process.get_sub_process_klass('false'),
                      process.GDBSubProcess)
        self.assertIs(process.get_sub_process_klass('true'),
                      process.SubProcess)

    def test_split_gdb_expr(self):
        binary, breakpoint = process.split_gdb_expr('foo:debug_print')
        self.assertEqual(binary, 'foo')
        self.assertEqual(breakpoint, 'debug_print')
        binary, breakpoint = process.split_gdb_expr('bar')
        self.assertEqual(binary, 'bar')
        self.assertEqual(breakpoint, 'main')
        binary, breakpoint = process.split_gdb_expr('baz:main.c:57')
        self.assertEqual(binary, 'baz')
        self.assertEqual(breakpoint, 'main.c:57')
        self.assertIsInstance(process.split_gdb_expr('foo'), tuple)
        self.assertIsInstance(process.split_gdb_expr('foo:debug_print'), tuple)


def mock_fail_find_cmd(cmd, default=None):
    path_paths = ["/usr/libexec", "/usr/local/sbin", "/usr/local/bin",
                  "/usr/sbin", "/usr/bin", "/sbin", "/bin"]
    raise path.CmdNotFoundError(cmd, path_paths)


class TestProcessRun(unittest.TestCase):

    @patch.object(path, 'find_command',
                  MagicMock(return_value='/bin/true'))
    @patch.object(os, 'getuid', MagicMock(return_value=1000))
    def test_subprocess_nosudo(self):
        expected_command = 'ls -l'
        p = process.SubProcess(cmd='ls -l')
        self.assertEqual(p.cmd, expected_command)

    @patch.object(path, 'find_command',
                  MagicMock(return_value='/bin/true'))
    @patch.object(os, 'getuid', MagicMock(return_value=0))
    def test_subprocess_nosudo_uid_0(self):
        expected_command = 'ls -l'
        p = process.SubProcess(cmd='ls -l')
        self.assertEqual(p.cmd, expected_command)

    @patch.object(path, 'find_command',
                  MagicMock(return_value='/bin/true'))
    @patch.object(os, 'getuid', MagicMock(return_value=1000))
    def test_subprocess_sudo(self):
        expected_command = '/bin/true -n ls -l'
        p = process.SubProcess(cmd='ls -l', sudo=True)
        self.assertEqual(p.cmd, expected_command)

    @patch.object(path, 'find_command', mock_fail_find_cmd)
    @patch.object(os, 'getuid', MagicMock(return_value=1000))
    def test_subprocess_sudo_no_sudo_installed(self):
        expected_command = 'ls -l'
        p = process.SubProcess(cmd='ls -l', sudo=True)
        self.assertEqual(p.cmd, expected_command)

    @patch.object(path, 'find_command',
                  MagicMock(return_value='/bin/true'))
    @patch.object(os, 'getuid', MagicMock(return_value=0))
    def test_subprocess_sudo_uid_0(self):
        expected_command = 'ls -l'
        p = process.SubProcess(cmd='ls -l', sudo=True)
        self.assertEqual(p.cmd, expected_command)

    @patch.object(path, 'find_command',
                  MagicMock(return_value='/bin/true'))
    @patch.object(os, 'getuid', MagicMock(return_value=1000))
    def test_subprocess_sudo_shell(self):
        expected_command = '/bin/true -n -s ls -l'
        p = process.SubProcess(cmd='ls -l', sudo=True, shell=True)
        self.assertEqual(p.cmd, expected_command)

    @patch.object(path, 'find_command', mock_fail_find_cmd)
    @patch.object(os, 'getuid', MagicMock(return_value=1000))
    def test_subprocess_sudo_shell_no_sudo_installed(self):
        expected_command = 'ls -l'
        p = process.SubProcess(cmd='ls -l', sudo=True, shell=True)
        self.assertEqual(p.cmd, expected_command)

    @patch.object(path, 'find_command',
                  MagicMock(return_value='/bin/true'))
    @patch.object(os, 'getuid', MagicMock(return_value=0))
    def test_subprocess_sudo_shell_uid_0(self):
        expected_command = 'ls -l'
        p = process.SubProcess(cmd='ls -l', sudo=True, shell=True)
        self.assertEqual(p.cmd, expected_command)

    @patch.object(path, 'find_command',
                  MagicMock(return_value='/bin/true'))
    @patch.object(os, 'getuid', MagicMock(return_value=1000))
    def test_run_nosudo(self):
        expected_command = 'ls -l'
        p = process.run(cmd='ls -l', ignore_status=True)
        self.assertEqual(p.command, expected_command)

    @patch.object(path, 'find_command',
                  MagicMock(return_value='/bin/true'))
    @patch.object(os, 'getuid', MagicMock(return_value=0))
    def test_run_nosudo_uid_0(self):
        expected_command = 'ls -l'
        p = process.run(cmd='ls -l', ignore_status=True)
        self.assertEqual(p.command, expected_command)

    @patch.object(path, 'find_command',
                  MagicMock(return_value='/bin/true'))
    @patch.object(os, 'getuid', MagicMock(return_value=1000))
    def test_run_sudo(self):
        expected_command = '/bin/true -n ls -l'
        p = process.run(cmd='ls -l', sudo=True, ignore_status=True)
        self.assertEqual(p.command, expected_command)

    @patch.object(path, 'find_command', mock_fail_find_cmd)
    @patch.object(os, 'getuid', MagicMock(return_value=1000))
    def test_run_sudo_no_sudo_installed(self):
        expected_command = 'ls -l'
        p = process.run(cmd='ls -l', sudo=True, ignore_status=True)
        self.assertEqual(p.command, expected_command)

    @patch.object(path, 'find_command',
                  MagicMock(return_value='/bin/true'))
    @patch.object(os, 'getuid', MagicMock(return_value=0))
    def test_run_sudo_uid_0(self):
        expected_command = 'ls -l'
        p = process.run(cmd='ls -l', sudo=True, ignore_status=True)
        self.assertEqual(p.command, expected_command)

    @patch.object(path, 'find_command',
                  MagicMock(return_value='/bin/true'))
    @patch.object(os, 'getuid', MagicMock(return_value=1000))
    def test_run_sudo_shell(self):
        expected_command = '/bin/true -n -s ls -l'
        p = process.run(cmd='ls -l', sudo=True, shell=True, ignore_status=True)
        self.assertEqual(p.command, expected_command)

    @patch.object(path, 'find_command', mock_fail_find_cmd)
    @patch.object(os, 'getuid', MagicMock(return_value=1000))
    def test_run_sudo_shell_no_sudo_installed(self):
        expected_command = 'ls -l'
        p = process.run(cmd='ls -l', sudo=True, shell=True, ignore_status=True)
        self.assertEqual(p.command, expected_command)

    @patch.object(path, 'find_command',
                  MagicMock(return_value='/bin/true'))
    @patch.object(os, 'getuid', MagicMock(return_value=0))
    def test_run_sudo_shell_uid_0(self):
        expected_command = 'ls -l'
        p = process.run(cmd='ls -l', sudo=True, shell=True, ignore_status=True)
        self.assertEqual(p.command, expected_command)


class MiscProcessTests(unittest.TestCase):

    def test_binary_from_shell(self):
        self.assertEqual("binary", process.binary_from_shell_cmd("binary"))
        res = process.binary_from_shell_cmd("MY_VAR=foo myV4r=123 "
                                            "quote='a b c' QUOTE=\"1 2 && b\" "
                                            "QuOtE=\"1 2\"foo' 3 4' first_bin "
                                            "second_bin VAR=xyz")
        self.assertEqual("first_bin", res)
        res = process.binary_from_shell_cmd("VAR=VALUE 1st_binary var=value "
                                            "second_binary")
        self.assertEqual("1st_binary", res)
        res = process.binary_from_shell_cmd("FOO=bar ./bin var=value")
        self.assertEqual("./bin", res)

if __name__ == "__main__":
    unittest.main()
