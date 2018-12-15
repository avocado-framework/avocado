import io
import logging
import os
import shlex
import unittest
import sys

try:
    from unittest import mock
except ImportError:
    import mock


from .. import recent_mock
from avocado.utils import astring
from avocado.utils import gdb
from avocado.utils import process
from avocado.utils import path

from six import string_types, PY2

from .. import setup_avocado_loggers


setup_avocado_loggers()


def probe_binary(binary):
    try:
        return path.find_command(binary)
    except path.CmdNotFoundError:
        return None


ECHO_CMD = probe_binary('echo')
FICTIONAL_CMD = '/usr/bin/fictional_cmd'


class TestSubProcess(unittest.TestCase):

    def test_allow_output_check_parameter(self):
        self.assertRaises(ValueError, process.SubProcess,
                          FICTIONAL_CMD, False, "invalid")

    @mock.patch('avocado.utils.process.SubProcess._init_subprocess')
    @mock.patch('avocado.utils.process.SubProcess.is_sudo_enabled')
    @mock.patch('avocado.utils.process.SubProcess.get_pid')
    @mock.patch('avocado.utils.process.get_children_pids')
    @mock.patch('avocado.utils.process.run')
    def test_send_signal_sudo_enabled(self, run, get_children, pid, sudo, init):  # pylint: disable=W0613
        signal = 1
        child_pid = 123
        sudo.return_value = True
        get_children.return_value = [child_pid]

        subprocess = process.SubProcess(FICTIONAL_CMD)
        subprocess.send_signal(signal)

        expected_cmd = 'kill -%d %d' % (signal, child_pid)
        run.assert_called_with(expected_cmd, sudo=True)

    @mock.patch('avocado.utils.process.SubProcess._init_subprocess')
    @mock.patch('avocado.utils.process.SubProcess.is_sudo_enabled')
    @mock.patch('avocado.utils.process.SubProcess.get_pid')
    @mock.patch('avocado.utils.process.get_children_pids')
    @mock.patch('avocado.utils.process.run')
    def test_send_signal_sudo_enabled_with_exception(
            self, run, get_children, pid, sudo, init):  # pylint: disable=W0613
        signal = 1
        child_pid = 123
        sudo.return_value = True
        get_children.return_value = [child_pid]
        run.side_effect = Exception()

        subprocess = process.SubProcess(FICTIONAL_CMD)
        subprocess.send_signal(signal)

        expected_cmd = 'kill -%d %d' % (signal, child_pid)
        run.assert_called_with(expected_cmd, sudo=True)

    @mock.patch('avocado.utils.process.SubProcess._init_subprocess')
    @mock.patch('avocado.utils.process.SubProcess.get_pid')
    @mock.patch('avocado.utils.process.get_owner_id')
    def test_get_user_id(self, get_owner, get_pid, init):  # pylint: disable=W0613
        user_id = 1
        process_id = 123
        get_pid.return_value = process_id
        get_owner.return_value = user_id

        subprocess = process.SubProcess(FICTIONAL_CMD)

        self.assertEqual(subprocess.get_user_id(), user_id)
        get_owner.assert_called_with(process_id)

    @mock.patch('avocado.utils.process.SubProcess._init_subprocess')
    @mock.patch('avocado.utils.process.SubProcess.get_pid')
    @mock.patch('avocado.utils.process.get_owner_id')
    def test_is_sudo_enabled_false(self, get_owner, get_pid, init):  # pylint: disable=W0613
        user_id = 1
        process_id = 123
        get_pid.return_value = process_id
        get_owner.return_value = user_id

        subprocess = process.SubProcess(FICTIONAL_CMD)

        self.assertFalse(subprocess.is_sudo_enabled())
        get_owner.assert_called_with(process_id)

    @mock.patch('avocado.utils.process.SubProcess._init_subprocess')
    @mock.patch('avocado.utils.process.SubProcess.get_pid')
    @mock.patch('avocado.utils.process.get_owner_id')
    def test_is_sudo_enabled_true(self, get_owner, get_pid, init):  # pylint: disable=W0613
        user_id = 0
        process_id = 123
        get_pid.return_value = process_id
        get_owner.return_value = user_id

        subprocess = process.SubProcess(FICTIONAL_CMD)

        self.assertTrue(subprocess.is_sudo_enabled())
        get_owner.assert_called_with(process_id)


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
        self.assertIs(process.get_sub_process_klass(FICTIONAL_CMD),
                      process.SubProcess)

        gdb.GDB_RUN_BINARY_NAMES_EXPR.append('/bin/false')
        self.assertIs(process.get_sub_process_klass('/bin/false'),
                      process.GDBSubProcess)
        self.assertIs(process.get_sub_process_klass('false'),
                      process.GDBSubProcess)
        self.assertIs(process.get_sub_process_klass(FICTIONAL_CMD),
                      process.SubProcess)

    def test_split_gdb_expr(self):
        binary, break_point = process.split_gdb_expr('foo:debug_print')
        self.assertEqual(binary, 'foo')
        self.assertEqual(break_point, 'debug_print')
        binary, break_point = process.split_gdb_expr('bar')
        self.assertEqual(binary, 'bar')
        self.assertEqual(break_point, 'main')
        binary, break_point = process.split_gdb_expr('baz:main.c:57')
        self.assertEqual(binary, 'baz')
        self.assertEqual(break_point, 'main.c:57')
        self.assertIsInstance(process.split_gdb_expr('foo'), tuple)
        self.assertIsInstance(process.split_gdb_expr('foo:debug_print'), tuple)


def mock_fail_find_cmd(cmd, default=None):  # pylint: disable=W0613
    path_paths = ["/usr/libexec", "/usr/local/sbin", "/usr/local/bin",
                  "/usr/sbin", "/usr/bin", "/sbin", "/bin"]
    raise path.CmdNotFoundError(cmd, path_paths)


class TestProcessRun(unittest.TestCase):

    @mock.patch.object(os, 'getuid',
                       mock.Mock(return_value=1000))
    def test_subprocess_nosudo(self):
        expected_command = 'ls -l'
        p = process.SubProcess(cmd='ls -l')
        self.assertEqual(p.cmd, expected_command)

    @mock.patch.object(os, 'getuid', mock.Mock(return_value=0))
    def test_subprocess_nosudo_uid_0(self):
        expected_command = 'ls -l'
        p = process.SubProcess(cmd='ls -l')
        self.assertEqual(p.cmd, expected_command)

    @mock.patch.object(path, 'find_command',
                       mock.Mock(return_value='/bin/sudo'))
    @mock.patch.object(os, 'getuid',
                       mock.Mock(return_value=1000))
    def test_subprocess_sudo(self):
        expected_command = '/bin/sudo -n ls -l'
        p = process.SubProcess(cmd='ls -l', sudo=True)
        path.find_command.assert_called_once_with('sudo')
        self.assertEqual(p.cmd, expected_command)

    @mock.patch.object(path, 'find_command', mock_fail_find_cmd)
    @mock.patch.object(os, 'getuid', mock.Mock(return_value=1000))
    def test_subprocess_sudo_no_sudo_installed(self):
        expected_command = 'ls -l'
        p = process.SubProcess(cmd='ls -l', sudo=True)
        self.assertEqual(p.cmd, expected_command)

    @mock.patch.object(os, 'getuid', mock.Mock(return_value=0))
    def test_subprocess_sudo_uid_0(self):
        expected_command = 'ls -l'
        p = process.SubProcess(cmd='ls -l', sudo=True)
        self.assertEqual(p.cmd, expected_command)

    @mock.patch.object(path, 'find_command',
                       mock.Mock(return_value='/bin/sudo'))
    @mock.patch.object(os, 'getuid', mock.Mock(return_value=1000))
    def test_subprocess_sudo_shell(self):
        expected_command = '/bin/sudo -n -s ls -l'
        p = process.SubProcess(cmd='ls -l', sudo=True, shell=True)
        path.find_command.assert_called_once_with('sudo')
        self.assertEqual(p.cmd, expected_command)

    @mock.patch.object(path, 'find_command', mock_fail_find_cmd)
    @mock.patch.object(os, 'getuid', mock.Mock(return_value=1000))
    def test_subprocess_sudo_shell_no_sudo_installed(self):
        expected_command = 'ls -l'
        p = process.SubProcess(cmd='ls -l', sudo=True, shell=True)
        self.assertEqual(p.cmd, expected_command)

    @mock.patch.object(os, 'getuid', mock.Mock(return_value=0))
    def test_subprocess_sudo_shell_uid_0(self):
        expected_command = 'ls -l'
        p = process.SubProcess(cmd='ls -l', sudo=True, shell=True)
        self.assertEqual(p.cmd, expected_command)

    @mock.patch.object(os, 'getuid', mock.Mock(return_value=1000))
    def test_run_nosudo(self):
        expected_command = 'ls -l'
        p = process.run(cmd='ls -l', ignore_status=True)
        self.assertEqual(p.command, expected_command)

    @mock.patch.object(os, 'getuid', mock.Mock(return_value=0))
    def test_run_nosudo_uid_0(self):
        expected_command = 'ls -l'
        p = process.run(cmd='ls -l', ignore_status=True)
        self.assertEqual(p.command, expected_command)

    @unittest.skipUnless(os.path.exists('/bin/sudo'),
                         "/bin/sudo not available")
    @mock.patch.object(path, 'find_command',
                       mock.Mock(return_value='/bin/sudo'))
    @mock.patch.object(os, 'getuid', mock.Mock(return_value=1000))
    def test_run_sudo(self):
        expected_command = '/bin/sudo -n ls -l'
        p = process.run(cmd='ls -l', sudo=True, ignore_status=True)
        path.find_command.assert_called_once_with('sudo')
        self.assertEqual(p.command, expected_command)

    @mock.patch.object(path, 'find_command', mock_fail_find_cmd)
    @mock.patch.object(os, 'getuid', mock.Mock(return_value=1000))
    def test_run_sudo_no_sudo_installed(self):
        expected_command = 'ls -l'
        p = process.run(cmd='ls -l', sudo=True, ignore_status=True)
        self.assertEqual(p.command, expected_command)

    @mock.patch.object(os, 'getuid', mock.Mock(return_value=0))
    def test_run_sudo_uid_0(self):
        expected_command = 'ls -l'
        p = process.run(cmd='ls -l', sudo=True, ignore_status=True)
        self.assertEqual(p.command, expected_command)

    @mock.patch.object(path, 'find_command',
                       mock.Mock(return_value='/bin/sudo'))
    @mock.patch.object(os, 'getuid', mock.Mock(return_value=1000))
    def test_run_sudo_shell(self):
        expected_command = '/bin/sudo -n -s ls -l'
        p = process.run(cmd='ls -l', sudo=True, shell=True, ignore_status=True)
        path.find_command.assert_called_once_with('sudo')
        self.assertEqual(p.command, expected_command)

    @mock.patch.object(path, 'find_command', mock_fail_find_cmd)
    @mock.patch.object(os, 'getuid', mock.Mock(return_value=1000))
    def test_run_sudo_shell_no_sudo_installed(self):
        expected_command = 'ls -l'
        p = process.run(cmd='ls -l', sudo=True, shell=True, ignore_status=True)
        self.assertEqual(p.command, expected_command)

    @mock.patch.object(os, 'getuid', mock.Mock(return_value=0))
    def test_run_sudo_shell_uid_0(self):
        expected_command = 'ls -l'
        p = process.run(cmd='ls -l', sudo=True, shell=True, ignore_status=True)
        self.assertEqual(p.command, expected_command)

    @unittest.skipUnless(ECHO_CMD, "Echo command not available in system")
    def test_run_unicode_output(self):
        # Using encoded string as shlex does not support decoding
        # but the behavior is exactly the same as if shell binary
        # produced unicode
        text = u"Avok\xe1do"
        # Even though code point used is "LATIN SMALL LETTER A WITH ACUTE"
        # (http://unicode.scarfboy.com/?s=u%2B00e1) when encoded to proper
        # utf-8, it becomes two bytes because it is >= 0x80
        # See https://en.wikipedia.org/wiki/UTF-8
        encoded_text = b'Avok\xc3\xa1do'
        self.assertEqual(text.encode('utf-8'), encoded_text)
        self.assertEqual(encoded_text.decode('utf-8'), text)
        cmd = u"%s -n %s" % (ECHO_CMD, text)
        result = process.run(cmd, encoding='utf-8')
        self.assertEqual(result.stdout, encoded_text)
        self.assertEqual(result.stdout_text, text)


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

    def test_cmd_split(self):
        plain_str = ''
        unicode_str = u''
        empty_bytes = b''
        # shlex.split() can work with "plain_str" and "unicode_str" on both
        # Python 2 and Python 3.  While we're not testing Python itself,
        # this will help us catch possible differences in the Python
        # standard library should they arise.
        self.assertEqual(shlex.split(plain_str), [])
        self.assertEqual(shlex.split(astring.to_text(plain_str)), [])
        self.assertEqual(shlex.split(unicode_str), [])
        self.assertEqual(shlex.split(astring.to_text(unicode_str)), [])
        # on Python 3, shlex.split() won't work with bytes, raising:
        # AttributeError: 'bytes' object has no attribute 'read'.
        # To turn bytes into text (when necessary), that is, on
        # Python 3 only, use astring.to_text()
        self.assertEqual(shlex.split(astring.to_text(empty_bytes)), [])
        # Now let's test our specific implementation to split commands
        self.assertEqual(process.cmd_split(plain_str), [])
        self.assertEqual(process.cmd_split(unicode_str), [])
        self.assertEqual(process.cmd_split(empty_bytes), [])
        unicode_command = u"avok\xe1do_test_runner arguments"
        self.assertEqual(process.cmd_split(unicode_command),
                         [u"avok\xe1do_test_runner",
                          u"arguments"])

    @unittest.skipUnless(recent_mock(),
                         "mock library version cannot (easily) patch open()")
    def test_get_parent_pid(self):
        stat = b'18405 (bash) S 24139 18405 18405 34818 8056 4210688 9792 170102 0 7 11 4 257 84 20 0 1 0 44336493 235409408 4281 18446744073709551615 94723230367744 94723231442728 140723100226000 0 0 0 65536 3670020 1266777851 0 0 0 17 1 0 0 0 0 0 94723233541456 94723233588580 94723248717824 140723100229613 140723100229623 140723100229623 140723100233710 0'
        with mock.patch('avocado.utils.process.open',
                        return_value=io.BytesIO(stat)):
            self.assertTrue(process.get_parent_pid(0), 24139)

    @unittest.skipUnless(sys.platform.startswith('linux'),
                         'Linux specific feature and test')
    def test_get_children_pids(self):
        '''
        Gets the list of children process.  Linux only.
        '''
        self.assertGreaterEqual(len(process.get_children_pids(1)), 1)

    @mock.patch('avocado.utils.process.os.kill')
    @mock.patch('avocado.utils.process.get_owner_id')
    def test_safe_kill(self, owner_mocked, kill_mocked):
        owner_id = 1
        process_id = 123
        signal = 1
        owner_mocked.return_value = owner_id

        killed = process.safe_kill(process_id, signal)
        self.assertTrue(killed)
        kill_mocked.assert_called_with(process_id, signal)

    @mock.patch('avocado.utils.process.os.kill')
    @mock.patch('avocado.utils.process.get_owner_id')
    def test_safe_kill_with_exception(self, owner_mocked, kill_mocked):
        owner_id = 1
        process_id = 123
        signal = 1
        owner_mocked.return_value = owner_id
        kill_mocked.side_effect = Exception()

        killed = process.safe_kill(process_id, signal)
        self.assertFalse(killed)
        kill_mocked.assert_called_with(process_id, signal)

    @mock.patch('avocado.utils.process.run')
    @mock.patch('avocado.utils.process.get_owner_id')
    def test_safe_kill_sudo_enabled(self, owner_mocked, run_mocked):
        owner_id = 0
        process_id = 123
        signal = 1
        owner_mocked.return_value = owner_id
        expected_cmd = 'kill -%d %d' % (signal, process_id)

        killed = process.safe_kill(process_id, signal)
        self.assertTrue(killed)
        run_mocked.assert_called_with(expected_cmd, sudo=True)

    @mock.patch('avocado.utils.process.run')
    @mock.patch('avocado.utils.process.get_owner_id')
    def test_safe_kill_sudo_enabled_with_exception(self, owner_mocked, run_mocked):
        owner_id = 0
        process_id = 123
        signal = 1
        owner_mocked.return_value = owner_id
        expected_cmd = 'kill -%d %d' % (signal, process_id)
        run_mocked.side_effect = Exception()

        killed = process.safe_kill(process_id, signal)
        self.assertFalse(killed)
        run_mocked.assert_called_with(expected_cmd, sudo=True)

    @mock.patch('avocado.utils.process.os.stat')
    def test_process_get_owner_id(self, stat_mock):
        process_id = 123
        owner_user_id = 13
        stat_mock.return_value = mock.Mock(st_uid=owner_user_id)

        returned_owner_id = process.get_owner_id(process_id)

        self.assertEqual(returned_owner_id, owner_user_id)
        stat_mock.assert_called_with('/proc/%d/' % process_id)

    @mock.patch('avocado.utils.process.os.stat')
    def test_process_get_owner_id_with_pid_not_found(self, stat_mock):
        process_id = 123
        stat_mock.side_effect = OSError()

        returned_owner_id = process.get_owner_id(process_id)

        self.assertIsNone(returned_owner_id)
        stat_mock.assert_called_with('/proc/%d/' % process_id)

    @mock.patch('avocado.utils.process.time.sleep')
    @mock.patch('avocado.utils.process.safe_kill')
    @mock.patch('avocado.utils.process.get_children_pids')
    def test_kill_process_tree_nowait(self, get_children_pids, safe_kill,
                                      sleep):
        safe_kill.return_value = True
        get_children_pids.return_value = []
        self.assertEqual([1], process.kill_process_tree(1))
        self.assertEqual(sleep.call_count, 0)

    @mock.patch('avocado.utils.process.safe_kill')
    @mock.patch('avocado.utils.process.get_children_pids')
    @mock.patch('avocado.utils.process.time.time')
    @mock.patch('avocado.utils.process.time.sleep')
    @mock.patch('avocado.utils.process.pid_exists')
    def test_kill_process_tree_timeout_3s(self, pid_exists, sleep, p_time,
                                          get_children_pids, safe_kill):
        safe_kill.return_value = True
        get_children_pids.return_value = []
        p_time.side_effect = [500, 502, 502, 502, 502, 502, 502,
                              504, 504, 504, 520, 520, 520]
        sleep.return_value = None
        pid_exists.return_value = True
        self.assertRaises(RuntimeError, process.kill_process_tree, 17,
                          timeout=3)
        self.assertLess(p_time.call_count, 10)

    @mock.patch('avocado.utils.process.safe_kill')
    @mock.patch('avocado.utils.process.get_children_pids')
    @mock.patch('avocado.utils.process.time.time')
    @mock.patch('avocado.utils.process.time.sleep')
    @mock.patch('avocado.utils.process.pid_exists')
    def test_kill_process_tree_dont_timeout_3s(self, pid_exists, sleep,
                                               p_time, get_children_pids,
                                               safe_kill):
        safe_kill.return_value = True
        get_children_pids.return_value = []
        p_time.side_effect = [500, 502, 502, 502, 502, 502, 502, 502, 502, 503]
        sleep.return_value = None
        pid_exists.side_effect = [True, False]
        self.assertEqual([76], process.kill_process_tree(76, timeout=3))
        self.assertLess(p_time.call_count, 10)

    @mock.patch('avocado.utils.process.safe_kill')
    @mock.patch('avocado.utils.process.get_children_pids')
    @mock.patch('avocado.utils.process.time.sleep')
    @mock.patch('avocado.utils.process.pid_exists')
    def test_kill_process_tree_dont_timeout_infinity(self, pid_exists, sleep,
                                                     get_children_pids,
                                                     safe_kill):
        safe_kill.return_value = True
        get_children_pids.return_value = []
        sleep.return_value = None
        pid_exists.side_effect = [True, True, True, True, True, False]

        self.assertEqual([31], process.kill_process_tree(31, timeout=-7.354))

        self.assertEqual(pid_exists.call_count, 6)
        self.assertEqual(sleep.call_count, 5)

    @mock.patch('avocado.utils.process.time.sleep')
    @mock.patch('avocado.utils.process.safe_kill')
    @mock.patch('avocado.utils.process.get_children_pids')
    def test_kill_process_tree_children(self, get_children_pids, safe_kill,
                                        sleep):
        safe_kill.return_value = True
        get_children_pids.side_effect = [[53, 12], [78, 58, 41], [], [13],
                                         [], [], []]
        self.assertEqual([31, 53, 78, 58, 13, 41, 12],
                         process.kill_process_tree(31))
        self.assertEqual(sleep.call_count, 0)


class CmdResultTests(unittest.TestCase):

    def test_nasty_str(self):
        result = process.CmdResult("ls", b"unicode_follows: \xc5\xa1",
                                   b"cp1250 follows: \xfd", 1, 2, 3,
                                   "wrong_encoding")
        if PY2:
            prefix = ''
        else:
            prefix = 'b'
        self.assertEqual(str(result), "command: 'ls'\nexit_status: 1"
                         "\nduration: 2\ninterrupted: False\npid: "
                         "3\nencoding: 'wrong_encoding'\nstdout: "
                         "%s'unicode_follows: \\xc5\\xa1'\nstderr: "
                         "%s'cp1250 follows: \\xfd'" % (prefix, prefix))

    def test_cmd_result_stdout_stderr_bytes(self):
        result = process.CmdResult()
        self.assertTrue(isinstance(result.stdout, bytes))
        self.assertTrue(isinstance(result.stderr, bytes))

    def test_cmd_result_stdout_stderr_text(self):
        result = process.CmdResult()
        self.assertTrue(isinstance(result.stdout_text, string_types))
        self.assertTrue(isinstance(result.stderr_text, string_types))

    def test_cmd_result_stdout_stderr_already_text(self):
        result = process.CmdResult()
        result.stdout = "supposed command output, but not as bytes"
        result.stderr = "supposed command error, but not as bytes"
        self.assertEqual(result.stdout, result.stdout_text)
        self.assertEqual(result.stderr, result.stderr_text)

    def test_cmd_result_stdout_stderr_other_type(self):
        result = process.CmdResult()
        result.stdout = None
        result.stderr = None
        self.assertRaises(TypeError, lambda x: result.stdout_text)
        self.assertRaises(TypeError, lambda x: result.stderr_text)


class CmdErrorTests(unittest.TestCase):

    def test_nasty_str(self):
        result = process.CmdResult("ls", b"unicode_follows: \xc5\xa1",
                                   b"cp1250 follows: \xfd", 1, 2, 3,
                                   "wrong_encoding")
        err = process.CmdError("ls", result, "please don't crash")
        if PY2:
            prefix = ''
        else:
            prefix = 'b'
        self.assertEqual(str(err), "Command 'ls' failed.\nstdout: "
                         "%s'unicode_follows: \\xc5\\xa1'\nstderr: "
                         "%s'cp1250 follows: \\xfd'\nadditional_info: "
                         "please don't crash" % (prefix, prefix))


class FDDrainerTests(unittest.TestCase):

    def test_drain_from_pipe_fd(self):
        read_fd, write_fd = os.pipe()
        result = process.CmdResult()
        fd_drainer = process.FDDrainer(read_fd, result, "test")
        fd_drainer.start()
        for content in (b"foo", b"bar", b"baz", b"foo\nbar\nbaz\n\n"):
            os.write(write_fd, content)
        os.write(write_fd, b"finish")
        os.close(write_fd)
        fd_drainer.flush()
        self.assertEqual(fd_drainer.data.getvalue(),
                         b"foobarbazfoo\nbar\nbaz\n\nfinish")

    def test_log(self):
        class CatchHandler(logging.NullHandler):
            """
            Handler used just to confirm that a logging event happened
            """
            def __init__(self, *args, **kwargs):
                super(CatchHandler, self).__init__(*args, **kwargs)
                self.caught_record = False

            def handle(self, record):
                self.caught_record = True

        read_fd, write_fd = os.pipe()
        result = process.CmdResult()
        logger = logging.getLogger("FDDrainerTests.test_log")
        handler = CatchHandler()
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        fd_drainer = process.FDDrainer(read_fd, result, "test",
                                       logger=logger, verbose=True)
        fd_drainer.start()
        os.write(write_fd, b"should go to the log\n")
        os.close(write_fd)
        fd_drainer.flush()
        self.assertEqual(fd_drainer.data.getvalue(),
                         b"should go to the log\n")
        self.assertTrue(handler.caught_record)

    def test_flush_on_closed_handler(self):
        handler = logging.StreamHandler(io.StringIO())
        log = logging.getLogger("test_flush_on_closed_handler")
        log.addHandler(handler)
        read_fd, write_fd = os.pipe()
        result = process.CmdResult()
        fd_drainer = process.FDDrainer(read_fd, result, name="test",
                                       stream_logger=log)
        fd_drainer.start()
        os.close(write_fd)
        self.assertIsNotNone(fd_drainer._stream_logger)
        one_stream_closed = False
        for handler in fd_drainer._stream_logger.handlers:
            stream = getattr(handler, 'stream', None)
            if stream is not None:
                if hasattr(stream, 'close'):
                    # force closing the handler's stream to check if
                    # flush will adapt to it
                    stream.close()
                    one_stream_closed = True
        self.assertTrue(one_stream_closed)
        fd_drainer.flush()

    def test_flush_on_handler_with_no_fileno(self):
        handler = logging.StreamHandler(io.StringIO())
        log = logging.getLogger("test_flush_on_handler_with_no_fileno")
        log.addHandler(handler)
        read_fd, write_fd = os.pipe()
        result = process.CmdResult()
        fd_drainer = process.FDDrainer(read_fd, result, name="test",
                                       stream_logger=log)
        fd_drainer.start()
        os.close(write_fd)
        fd_drainer.flush()

    def test_replace_incorrect_characters_in_log(self):
        data = io.StringIO()
        handler = logging.StreamHandler(data)
        log = logging.getLogger("test_replace_incorrect_characters_in_log")
        log.addHandler(handler)
        log.setLevel(logging.DEBUG)
        read_fd, write_fd = os.pipe()
        result = process.CmdResult(encoding='ascii')
        fd_drainer = process.FDDrainer(read_fd, result, name="test",
                                       stream_logger=log, verbose=True)
        fd_drainer.start()
        os.write(write_fd, b"Avok\xc3\xa1do")
        os.close(write_fd)
        fd_drainer._thread.join(60)
        self.assertFalse(fd_drainer._thread.is_alive())
        # \n added by StreamLogger
        self.assertEqual(data.getvalue(), u"Avok\ufffd\ufffddo\n")


if __name__ == "__main__":
    unittest.main()
