import io
import logging
import os
import unittest

try:
    from unittest import mock
except ImportError:
    import mock


from avocado.utils import gdb
from avocado.utils import process
from avocado.utils import path

from six import string_types


def probe_binary(binary):
    try:
        return path.find_command(binary)
    except path.CmdNotFoundError:
        return None


TRUE_CMD = probe_binary('true')


class TestSubProcess(unittest.TestCase):

    def test_allow_output_check_parameter(self):
        self.assertRaises(ValueError, process.SubProcess,
                          TRUE_CMD, False, "invalid")


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

    @unittest.skipUnless(TRUE_CMD,
                         '"true" binary not available')
    def test_get_sub_process_klass(self):
        gdb.GDB_RUN_BINARY_NAMES_EXPR = []
        self.assertIs(process.get_sub_process_klass(TRUE_CMD),
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

    @unittest.skipUnless(TRUE_CMD,
                         '"true" binary not available')
    @mock.patch.object(path, 'find_command',
                       mock.Mock(return_value=TRUE_CMD))
    @mock.patch.object(os, 'getuid',
                       mock.Mock(return_value=1000))
    def test_subprocess_nosudo(self):
        expected_command = 'ls -l'
        p = process.SubProcess(cmd='ls -l')
        self.assertEqual(p.cmd, expected_command)

    @unittest.skipUnless(TRUE_CMD,
                         '"true" binary not available')
    @mock.patch.object(path, 'find_command',
                       mock.Mock(return_value=TRUE_CMD))
    @mock.patch.object(os, 'getuid', mock.Mock(return_value=0))
    def test_subprocess_nosudo_uid_0(self):
        expected_command = 'ls -l'
        p = process.SubProcess(cmd='ls -l')
        self.assertEqual(p.cmd, expected_command)

    @unittest.skipUnless(TRUE_CMD,
                         '"true" binary not available')
    @mock.patch.object(path, 'find_command',
                       mock.Mock(return_value=TRUE_CMD))
    @mock.patch.object(os, 'getuid',
                       mock.Mock(return_value=1000))
    def test_subprocess_sudo(self):
        expected_command = '%s -n ls -l' % TRUE_CMD
        p = process.SubProcess(cmd='ls -l', sudo=True)
        self.assertEqual(p.cmd, expected_command)

    @mock.patch.object(path, 'find_command', mock_fail_find_cmd)
    @mock.patch.object(os, 'getuid', mock.Mock(return_value=1000))
    def test_subprocess_sudo_no_sudo_installed(self):
        expected_command = 'ls -l'
        p = process.SubProcess(cmd='ls -l', sudo=True)
        self.assertEqual(p.cmd, expected_command)

    @unittest.skipUnless(TRUE_CMD,
                         '"true" binary not available')
    @mock.patch.object(path, 'find_command',
                       mock.Mock(return_value=TRUE_CMD))
    @mock.patch.object(os, 'getuid', mock.Mock(return_value=0))
    def test_subprocess_sudo_uid_0(self):
        expected_command = 'ls -l'
        p = process.SubProcess(cmd='ls -l', sudo=True)
        self.assertEqual(p.cmd, expected_command)

    @unittest.skipUnless(TRUE_CMD,
                         '"true" binary not available')
    @mock.patch.object(path, 'find_command',
                       mock.Mock(return_value=TRUE_CMD))
    @mock.patch.object(os, 'getuid', mock.Mock(return_value=1000))
    def test_subprocess_sudo_shell(self):
        expected_command = '%s -n -s ls -l' % TRUE_CMD
        p = process.SubProcess(cmd='ls -l', sudo=True, shell=True)
        self.assertEqual(p.cmd, expected_command)

    @mock.patch.object(path, 'find_command', mock_fail_find_cmd)
    @mock.patch.object(os, 'getuid', mock.Mock(return_value=1000))
    def test_subprocess_sudo_shell_no_sudo_installed(self):
        expected_command = 'ls -l'
        p = process.SubProcess(cmd='ls -l', sudo=True, shell=True)
        self.assertEqual(p.cmd, expected_command)

    @unittest.skipUnless(TRUE_CMD,
                         '"true" binary not available')
    @mock.patch.object(path, 'find_command',
                       mock.Mock(return_value=TRUE_CMD))
    @mock.patch.object(os, 'getuid', mock.Mock(return_value=0))
    def test_subprocess_sudo_shell_uid_0(self):
        expected_command = 'ls -l'
        p = process.SubProcess(cmd='ls -l', sudo=True, shell=True)
        self.assertEqual(p.cmd, expected_command)

    @unittest.skipUnless(TRUE_CMD,
                         '"true" binary not available')
    @mock.patch.object(path, 'find_command',
                       mock.Mock(return_value=TRUE_CMD))
    @mock.patch.object(os, 'getuid', mock.Mock(return_value=1000))
    def test_run_nosudo(self):
        expected_command = 'ls -l'
        p = process.run(cmd='ls -l', ignore_status=True)
        self.assertEqual(p.command, expected_command)

    @unittest.skipUnless(TRUE_CMD,
                         '"true" binary not available')
    @mock.patch.object(path, 'find_command',
                       mock.Mock(return_value=TRUE_CMD))
    @mock.patch.object(os, 'getuid', mock.Mock(return_value=0))
    def test_run_nosudo_uid_0(self):
        expected_command = 'ls -l'
        p = process.run(cmd='ls -l', ignore_status=True)
        self.assertEqual(p.command, expected_command)

    @unittest.skipUnless(TRUE_CMD,
                         '"true" binary not available')
    @mock.patch.object(path, 'find_command',
                       mock.Mock(return_value=TRUE_CMD))
    @mock.patch.object(os, 'getuid', mock.Mock(return_value=1000))
    def test_run_sudo(self):
        expected_command = '%s -n ls -l' % TRUE_CMD
        p = process.run(cmd='ls -l', sudo=True, ignore_status=True)
        self.assertEqual(p.command, expected_command)

    @mock.patch.object(path, 'find_command', mock_fail_find_cmd)
    @mock.patch.object(os, 'getuid', mock.Mock(return_value=1000))
    def test_run_sudo_no_sudo_installed(self):
        expected_command = 'ls -l'
        p = process.run(cmd='ls -l', sudo=True, ignore_status=True)
        self.assertEqual(p.command, expected_command)

    @unittest.skipUnless(TRUE_CMD,
                         '"true" binary not available')
    @mock.patch.object(path, 'find_command',
                       mock.Mock(return_value=TRUE_CMD))
    @mock.patch.object(os, 'getuid', mock.Mock(return_value=0))
    def test_run_sudo_uid_0(self):
        expected_command = 'ls -l'
        p = process.run(cmd='ls -l', sudo=True, ignore_status=True)
        self.assertEqual(p.command, expected_command)

    @unittest.skipUnless(TRUE_CMD,
                         '"true" binary not available')
    @mock.patch.object(path, 'find_command',
                       mock.Mock(return_value=TRUE_CMD))
    @mock.patch.object(os, 'getuid', mock.Mock(return_value=1000))
    def test_run_sudo_shell(self):
        expected_command = '%s -n -s ls -l' % TRUE_CMD
        p = process.run(cmd='ls -l', sudo=True, shell=True, ignore_status=True)
        self.assertEqual(p.command, expected_command)

    @mock.patch.object(path, 'find_command', mock_fail_find_cmd)
    @mock.patch.object(os, 'getuid', mock.Mock(return_value=1000))
    def test_run_sudo_shell_no_sudo_installed(self):
        expected_command = 'ls -l'
        p = process.run(cmd='ls -l', sudo=True, shell=True, ignore_status=True)
        self.assertEqual(p.command, expected_command)

    @unittest.skipUnless(TRUE_CMD,
                         '"true" binary not available')
    @mock.patch.object(path, 'find_command',
                       mock.Mock(return_value=TRUE_CMD))
    @mock.patch.object(os, 'getuid', mock.Mock(return_value=0))
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


class CmdResultTests(unittest.TestCase):

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


if __name__ == "__main__":
    unittest.main()
