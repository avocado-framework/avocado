#!/usr/bin/env python

import os

from avocado import Test
from avocado import main
from avocado.utils import gdb
from avocado.utils import process


class GdbTest(Test):

    """
    Execute the gdb test

    :avocado: tags=requires_c_compiler
    """

    VALID_CMDS = ["-list-target-features",
                  "-break-info",
                  "-break-list",
                  "-thread-info",
                  "-stack-info-frame",
                  "-stack-info-depth"]

    INVALID_CMDS = ["-foobar",
                    "-magic8ball",
                    "-find-me-the-bug",
                    "-auto-debug-it"]

    def setUp(self):
        self.return99_binary_path = os.path.join(self.outputdir, 'return99')
        return99_source_path = os.path.join(self.datadir, 'return99.c')
        process.system('gcc -O0 -g %s -o %s' % (return99_source_path,
                                                self.return99_binary_path))

        self.segfault_binary_path = os.path.join(self.outputdir, 'segfault')
        segfault_source_path = os.path.join(self.datadir, 'segfault.c')
        process.system('gcc -O0 -g %s -o %s' % (segfault_source_path,
                                                self.segfault_binary_path))

    @staticmethod
    def is_process_alive(process):
        """
        Checks if a process is still alive

        :param process: a :class:`subprocess.POpen` instance
        :type process: :class:`subprocess.POpen`
        :returns: True or False
        :rtype: bool
        """
        return process.poll() is None

    def test_start_exit(self):
        """
        Tests execution of multiple GDB instances without any blocking or race
        """
        self.log.info("Testing execution of multiple GDB instances")
        process_count = 10
        gdb_instances = []
        for i in xrange(0, process_count):
            gdb_instances.append(gdb.GDB())

        for i in xrange(0, process_count):
            self.assertEqual(gdb_instances[i].exit(), 0)

    def test_existing_commands_raw(self):
        """
        Tests the GDB response to commands that exist and to those that do not
        """
        g = gdb.GDB()
        self.log.info("Testing existing (valid) GDB commands using raw commands")
        for cmd in self.VALID_CMDS:
            info_cmd = "-info-gdb-mi-command %s" % cmd[1:]
            r = g.cmd(info_cmd)
            self.assertEqual(r.result.result.command.exists, 'true')

        self.log.info("Testing non-existing (invalid) GDB commands using raw "
                      "commands")
        for cmd in self.INVALID_CMDS:
            info_cmd = "-info-gdb-mi-command %s" % cmd[1:]
            r = g.cmd(info_cmd)
            self.assertEqual(r.result.result.command.exists, 'false')

    def test_existing_commands(self):
        g = gdb.GDB()

        self.log.info("Testing existing (valid) GDB commands using utility "
                      "methods")
        for cmd in self.VALID_CMDS:
            self.assertTrue(g.cmd_exists(cmd))
            g.cmd(cmd)

        self.log.info("Testing non-existing (invalid) GDB commands using "
                      "utility methods")
        for cmd in self.INVALID_CMDS:
            self.assertFalse(g.cmd_exists(cmd))

    def test_load_set_breakpoint_run_exit_raw(self):
        """
        Test a common GDB cycle using raw commands: load, set break, run, exit
        """
        self.log.info("Testing that GDB loads a file and sets a breakpoint")
        g = gdb.GDB()

        file_cmd = "-file-exec-and-symbols %s" % self.return99_binary_path
        r = g.cmd(file_cmd)
        self.assertEqual(r.result.class_, 'done')

        break_cmd = "-break-insert 5"
        r = g.cmd(break_cmd)
        self.assertEqual(r.result.class_, 'done')
        self.assertEqual(r.result.result.bkpt.number, '1')
        self.assertEqual(r.result.result.bkpt.enabled, 'y')

        break_del_cmd = "-break-delete 1"
        r = g.cmd(break_del_cmd)
        self.assertEqual(r.result.class_, 'done')

        run_cmd = "-exec-run"
        r = g.cmd(run_cmd)
        self.assertEqual(r.result.class_, 'running')

        g.cmd("-gdb-exit")
        self.assertEqual(g.process.wait(), 0)

    def test_load_set_breakpoint_run_exit(self):
        """
        Test a common GDB cycle: load, set break, del break, run, exit
        """
        self.log.info("Testing a common GDB cycle")
        g = gdb.GDB()
        g.set_file(self.return99_binary_path)
        g.set_break("5")
        g.del_break(1)
        g.run()
        g.exit()

    def test_generate_core(self):
        """
        Load a file that will cause a segfault and produce a core dump
        """
        self.log.info("Testing that a core dump will be generated")

        g = gdb.GDB()
        file_cmd = "-file-exec-and-symbols %s" % self.segfault_binary_path
        r = g.cmd(file_cmd)
        self.assertEqual(r.result.class_, 'done')

        run_cmd = "-exec-run"
        r = g.cmd(run_cmd)
        self.assertEqual(r.result.class_, 'running')

        other_messages = g.read_until_break()
        core_path = None
        for msg in other_messages:
            parsed_msg = gdb.parse_mi(msg)
            if (hasattr(parsed_msg, 'class_') and
                (parsed_msg.class_ == 'stopped') and
                    (parsed_msg.result.signal_name == 'SIGSEGV')):
                core_path = "%s.core" % self.segfault_binary_path
                gcore_cmd = 'gcore %s' % core_path
                gcore_cmd = gdb.encode_mi_cli(gcore_cmd)
                r = g.cmd(gcore_cmd)
                self.assertEqual(r.result.class_, 'done')

        self.assertTrue(os.path.exists(core_path))
        g.exit()

    def test_set_multiple_break(self):
        """
        Tests that multiple breakpoints do not interfere with each other
        """
        self.log.info("Testing setting multiple breakpoints")
        g = gdb.GDB()
        g.set_file(self.return99_binary_path)
        g.set_break('empty')
        g.set_break('7')
        g.exit()

    def test_disconnect_raw(self):
        """
        Connect/disconnect repeatedly from a remote debugger using raw commands
        """
        self.log.info("Testing connecting and disconnecting repeatedly using "
                      "raw commands")
        s = gdb.GDBServer()
        g = gdb.GDB()

        # Do 100 cycle of target (kind of connects) and disconnects
        for i in xrange(0, 100):
            cmd = '-target-select extended-remote :%s' % s.port
            r = g.cmd(cmd)
            self.assertEqual(r.result.class_, 'connected')
            r = g.cmd('-target-disconnect')
            self.assertEqual(r.result.class_, 'done')

        # manual server shutdown
        cmd = '-target-select extended-remote :%s' % s.port
        r = g.cmd(cmd)
        self.assertEqual(r.result.class_, 'connected')
        r = g.cli_cmd('monitor exit')
        self.assertEqual(r.result.class_, 'done')

        g.exit()
        s.exit()

    def test_disconnect(self):
        """
        Connect/disconnect repeatedly from a remote debugger using utilities
        """
        self.log.info("Testing connecting and disconnecting repeatedly")
        s = gdb.GDBServer()
        g = gdb.GDB()

        for i in xrange(0, 100):
            r = g.connect(s.port)
            self.assertEqual(r.result.class_, 'connected')
            r = g.disconnect()
            self.assertEqual(r.result.class_, 'done')

        g.exit()
        s.exit()

    def test_remote_exec(self):
        """
        Tests execution on a remote target
        """
        self.log.info("Testing execution on a remote target")
        hit_breakpoint = False

        s = gdb.GDBServer()
        g = gdb.GDB()

        cmd = '-file-exec-and-symbols %s' % self.return99_binary_path
        r = g.cmd(cmd)
        self.assertEqual(r.result.class_, 'done')

        cmd = 'set remote exec-file %s' % self.return99_binary_path
        r = g.cmd(cmd)
        self.assertEqual(r.result.class_, 'done')

        cmd = "-break-insert %s" % 'main'
        r = g.cmd(cmd)
        self.assertEqual(r.result.class_, 'done')

        r = g.cmd('-exec-run')

        other_messages = g.read_until_break()
        for msg in other_messages:
            parsed_msg = gdb.parse_mi(msg)
            if (hasattr(parsed_msg, 'class_') and
                parsed_msg.class_ == 'stopped' and
                    parsed_msg.result.reason == 'breakpoint-hit'):
                hit_breakpoint = True

        self.assertTrue(hit_breakpoint)
        g.exit()
        s.exit()

    def test_stream_messages(self):
        """
        Tests if the expected response appears in the result stream messages
        """
        self.log.info("Testing that messages appears in the result stream")
        g = gdb.GDB()
        r = g.cmd("-gdb-version")
        self.assertIn("GNU GPL version", r.get_stream_messages_text())

    def test_connect_multiple_clients(self):
        """
        Tests two or more connections to the same server raise an exception
        """
        self.log.info("Testing that multiple clients cannot connect at once")
        s = gdb.GDBServer()
        c1 = gdb.GDB()
        c1.connect(s.port)
        c2 = gdb.GDB()
        self.assertRaises(ValueError, c2.connect, s.port)
        s.exit()

    def test_server_exit(self):
        """
        Tests that the server is shutdown by using a monitor exit command
        """
        self.log.info("Testing that a single server exits cleanly")
        s = gdb.GDBServer()
        s.exit()
        self.assertFalse(self.is_process_alive(s.process))

    def test_multiple_servers(self):
        """
        Tests multiple server instances without any blocking or race condition
        """
        self.log.info("Testing execution of multiple GDB server instances")
        process_count = 10
        server_instances = []
        for i in xrange(0, process_count):
            s = gdb.GDBServer()
            c = gdb.GDB()
            c.connect(s.port)
            c.cmd('show-version')
            c.disconnect()
            server_instances.append(s)

        for i in xrange(0, process_count):
            self.assertTrue(self.is_process_alive(server_instances[i].process))
            server_instances[i].exit()
            self.assertFalse(self.is_process_alive(server_instances[i].process))

    def test_interactive(self):
        """
        Tests avocado's GDB plugin features

        If GDB command line options are given, `--gdb-run-bin=return99` for
        this particular test, the test will stop at binary main() function.
        """
        self.log.info('Testing GDB interactivity')
        process.run(self.return99_binary_path, ignore_status=True)

    def test_interactive_args(self):
        """
        Tests avocado's GDB plugin features with an executable and args

        If GDB command line options are given, `--gdb-run-bin=return99` for
        this particular test, the test will stop at binary main() function.

        This test uses `process.run()` without an `ignore_status` parameter
        """
        self.log.info('Testing GDB interactivity with arguments')
        result = process.run("%s 0" % self.return99_binary_path)
        self.assertEquals(result.exit_status, 0)

    def test_exit_status(self):
        """
        Tests avocado's GDB plugin features

        If GDB command line options are given, `--gdb-run-bin=return99` for
        this particular test, the test will stop at binary main() function.
        """
        self.log.info('Testing process exit statuses')
        for arg, exp in [(-1, 255), (8, 8)]:
            self.log.info('Expecting exit status "%s"', exp)
            cmd = "%s %s" % (self.return99_binary_path, arg)
            result = process.run(cmd, ignore_status=True)
            self.assertEquals(result.exit_status, exp)

    def test_server_stderr(self):
        self.log.info('Testing server stderr collection')
        s = gdb.GDBServer()
        s.exit()
        self.assertTrue(os.path.exists(s.stderr_path))

        stderr_lines = open(s.stderr_path, 'r').readlines()
        listening_line = "Listening on port %s\n" % s.port
        self.assertIn(listening_line, stderr_lines)

    def test_server_stdout(self):
        self.log.info('Testing server stdout/stderr collection')
        s = gdb.GDBServer()
        c = gdb.GDB()
        c.connect(s.port)
        c.set_file(self.return99_binary_path)
        c.run()
        s.exit()

        self.assertTrue(os.path.exists(s.stdout_path))
        self.assertTrue(os.path.exists(s.stderr_path))

        stdout_lines = open(s.stdout_path, 'r').readlines()
        self.assertIn("return 99\n", stdout_lines)

    def test_interactive_stdout(self):
        """
        Tests avocado's GDB plugin features

        If GDB command line options are given, `--gdb-run-bin=return99` for
        this particular test, the test will stop at binary main() function.
        """
        self.log.info('Testing GDB interactivity')
        result = process.run(self.return99_binary_path, ignore_status=True)
        self.assertIn("return 99\n", result.stdout)

    def test_remote(self):
        """
        Tests GDBRemote interaction with a GDBServer
        """
        s = gdb.GDBServer()
        r = gdb.GDBRemote('127.0.0.1', s.port)
        r.connect()
        r.cmd("qSupported")
        r.cmd("qfThreadInfo")
        s.exit()


if __name__ == '__main__':
    main()
