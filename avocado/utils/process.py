# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2013-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

"""
Functions dedicated to find and run external commands.
"""

import logging
import os
import StringIO
import signal
import subprocess
import time
import stat
import fcntl
import shlex
import shutil
import threading

from avocado import gdb
from avocado import runtime
from avocado.core import exceptions

log = logging.getLogger('avocado.test')
stdout_log = logging.getLogger('avocado.test.stdout')
stderr_log = logging.getLogger('avocado.test.stderr')


class CmdNotFoundError(Exception):

    """
    Indicates that the command was not found in the system after a search.

    :param cmd: String with the command.
    :param paths: List of paths where we looked after.
    """

    def __init__(self, cmd, paths):
        super(CmdNotFoundError, self)
        self.cmd = cmd
        self.paths = paths

    def __str__(self):
        return ("Command '%s' could not be found in any of the PATH dirs: %s" %
                (self.cmd, self.paths))


class GDBInferiorProcessExitedError(exceptions.TestNAError):

    """
    Debugged process exited/finished outside of avocado control

    This probably means that the user, in an interactive session, let the
    inferior process exit before before avocado resumed the debugger session.

    Since the information is unknown, and the behavior is undefined, the
    test will be skipped.
    """
    pass


def find_command(cmd):
    """
    Try to find a command in the PATH, paranoid version.

    :param cmd: Command to be found.
    :raise: :class:`avocado.utils.process.CmdNotFoundError` in case the
            command was not found.
    """
    common_bin_paths = ["/usr/libexec", "/usr/local/sbin", "/usr/local/bin",
                        "/usr/sbin", "/usr/bin", "/sbin", "/bin"]
    try:
        path_paths = os.environ['PATH'].split(":")
    except IndexError:
        path_paths = []
    path_paths = list(set(common_bin_paths + path_paths))

    for dir_path in path_paths:
        cmd_path = os.path.join(dir_path, cmd)
        if os.path.isfile(cmd_path):
            return os.path.abspath(cmd_path)

    raise CmdNotFoundError(cmd, path_paths)


def pid_exists(pid):
    """
    Return True if a given PID exists.

    :param pid: Process ID number.
    """
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def safe_kill(pid, signal):
    """
    Attempt to send a signal to a given process that may or may not exist.

    :param signal: Signal number.
    """
    try:
        os.kill(pid, signal)
        return True
    except Exception:
        return False


def kill_process_tree(pid, sig=signal.SIGKILL):
    """
    Signal a process and all of its children.

    If the process does not exist -- return.

    :param pid: The pid of the process to signal.
    :param sig: The signal to send to the processes.
    """
    if not safe_kill(pid, signal.SIGSTOP):
        return
    children = system_output("ps --ppid=%d -o pid=" % pid).split()
    for child in children:
        kill_process_tree(int(child), sig)
    safe_kill(pid, sig)
    safe_kill(pid, signal.SIGCONT)


def kill_process_by_pattern(pattern):
    """
    Send SIGTERM signal to a process with matched pattern.

    :param pattern: normally only matched against the process name
    """
    cmd = "pkill -f %s" % pattern
    result = run(cmd, ignore_status=True)
    if result.exit_status:
        logging.error("Failed to run '%s': %s", cmd, result)
    else:
        logging.info("Succeed to run '%s'.", cmd)


def process_in_ptree_is_defunct(ppid):
    """
    Verify if any processes deriving from PPID are in the defunct state.

    Attempt to verify if parent process and any children from PPID is defunct
    (zombie) or not.

    :param ppid: The parent PID of the process to verify.
    """
    defunct = False
    try:
        pids = get_children_pids(ppid)
    except exceptions.CmdError:  # Process doesn't exist
        return True
    for pid in pids:
        cmd = "ps --no-headers -o cmd %d" % int(pid)
        proc_name = system_output(cmd, ignore_status=True)
        if '<defunct>' in proc_name:
            defunct = True
            break
    return defunct


def get_children_pids(ppid):
    """
    Get all PIDs of children/threads of parent ppid
    param ppid: parent PID
    return: list of PIDs of all children/threads of ppid
    """
    return (system_output("ps -L --ppid=%d -o lwp" % ppid).split('\n')[1:])


class CmdResult(object):

    """
    Command execution result.

    :param command: String containing the command line itself
    :param exit_status: Integer exit code of the process
    :param stdout: String containing stdout of the process
    :param stderr: String containing stderr of the process
    :param duration: Elapsed wall clock time running the process
    """

    def __init__(self, command="", stdout="", stderr="",
                 exit_status=None, duration=0):
        self.command = command
        self.exit_status = exit_status
        self.stdout = stdout
        self.stderr = stderr
        self.duration = duration
        self.interrupted = False

    def __repr__(self):
        cmd_rep = ("Command: %s\n"
                   "Exit status: %s\n"
                   "Duration: %s\n"
                   "Stdout:\n%s\n"
                   "Stderr:\n%s\n" % (self.command, self.exit_status,
                                      self.duration, self.stdout, self.stderr))
        if self.interrupted:
            cmd_rep += "Command interrupted by user (Ctrl+C)\n"
        return cmd_rep


class SubProcess(object):

    """
    Run a subprocess in the background, collecting stdout/stderr streams.
    """

    def __init__(self, cmd, verbose=True, allow_output_check='all'):
        """
        Creates the subprocess object, stdout/err, reader threads and locks.

        :param cmd: Command line to run.
        :type cmd: str
        :param verbose: Whether to log the command run and stdout/stderr.
        :type verbose: bool
        :param allow_output_check: Whether to log the command stream outputs
                                   (stdout and stderr) in the test stream
                                   files. Valid values: 'stdout', for
                                   allowing only standard output, 'stderr',
                                   to allow only standard error, 'all',
                                   to allow both standard output and error
                                   (default), and 'none', to allow
                                   none to be recorded.
        :type allow_output_check: str
        """
        self.cmd = cmd
        self.verbose = verbose
        if self.verbose:
            log.info("Running '%s'", cmd)
        self.sp = subprocess.Popen(cmd,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   shell=True)
        self.allow_output_check = allow_output_check
        self.start_time = time.time()
        self.result = CmdResult(cmd)
        self.stdout_file = StringIO.StringIO()
        self.stderr_file = StringIO.StringIO()
        self.stdout_lock = threading.Lock()
        self.stdout_thread = threading.Thread(target=self._fd_drainer,
                                              name="%s-stdout" % cmd,
                                              args=[self.sp.stdout])
        self.stdout_thread.daemon = True
        self.stderr_lock = threading.Lock()
        self.stderr_thread = threading.Thread(target=self._fd_drainer,
                                              name="%s-stderr" % cmd,
                                              args=[self.sp.stderr])
        self.stderr_thread.daemon = True
        self.stdout_thread.start()
        self.stderr_thread.start()

        def signal_handler(signum, frame):
            self.result.interrupted = True
            self.wait()

        signal.signal(signal.SIGINT, signal_handler)

    def __str__(self):
        if self.result.exit_status is None:
            rc = '(still running)'
        else:
            rc = self.result.exit_status
        return 'SubProcess(cmd="%s", rc="%s")' % (self.cmd, rc)

    def _fd_drainer(self, input_pipe):
        """
        Read from input_pipe, storing and logging output.

        :param input_pipe: File like object to the stream.
        """
        stream_prefix = "%s"
        if input_pipe == self.sp.stdout:
            prefix = '[stdout] %s'
            if self.allow_output_check in ['none', 'stderr']:
                stream_logger = None
            else:
                stream_logger = stdout_log
            output_file = self.stdout_file
            lock = self.stdout_lock
        elif input_pipe == self.sp.stderr:
            prefix = '[stderr] %s'
            if self.allow_output_check in ['none', 'stdout']:
                stream_logger = None
            else:
                stream_logger = stderr_log
            output_file = self.stderr_file
            lock = self.stderr_lock

        fileno = input_pipe.fileno()

        bfr = ''
        while True:
            tmp = os.read(fileno, 1024)
            if tmp == '':
                break
            lock.acquire()
            try:
                output_file.write(tmp)
                if self.verbose:
                    bfr += tmp
                    if tmp.endswith('\n'):
                        for l in bfr.splitlines():
                            log.debug(prefix, l)
                            if stream_logger is not None:
                                stream_logger.debug(stream_prefix, l)
                        bfr = ''
            finally:
                lock.release()

    def _fill_results(self, rc):
        self.result.exit_status = rc
        if self.result.duration == 0:
            self.result.duration = time.time() - self.start_time
        self._fill_streams()

    def _fill_streams(self):
        """
        Close subprocess stdout and stderr, and put values into result obj.
        """
        # Cleaning up threads
        self.stdout_thread.join()
        self.stderr_thread.join()
        # Clean subprocess pipes and populate stdout/err
        self.sp.stdout.close()
        self.sp.stderr.close()
        self.result.stdout = self.get_stdout()
        self.result.stderr = self.get_stderr()

    def get_stdout(self):
        """
        Get the full stdout of the subprocess so far.

        :return: Standard output of the process.
        :rtype: str
        """
        self.stdout_lock.acquire()
        stdout = self.stdout_file.getvalue()
        self.stdout_lock.release()
        return stdout

    def get_stderr(self):
        """
        Get the full stderr of the subprocess so far.

        :return: Standard error of the process.
        :rtype: str
        """
        self.stderr_lock.acquire()
        stderr = self.stderr_file.getvalue()
        self.stderr_lock.release()
        return stderr

    def terminate(self):
        """
        Send a :attr:`signal.SIGTERM` to the process.
        """
        self.send_signal(signal.SIGTERM)

    def kill(self):
        """
        Send a :attr:`signal.SIGKILL` to the process.
        """
        self.send_signal(signal.SIGKILL)

    def send_signal(self, sig):
        """
        Send the specified signal to the process.

        :param sig: Signal to send.
        """
        self.sp.send_signal(sig)

    def poll(self):
        """
        Call the subprocess poll() method, fill results if rc is not None.
        """
        rc = self.sp.poll()
        if rc is not None:
            self._fill_results(rc)
        return rc

    def wait(self):
        """
        Call the subprocess poll() method, fill results if rc is not None.
        """
        rc = self.sp.wait()
        if rc is not None:
            self._fill_results(rc)
        return rc

    def run(self, timeout=None, sig=signal.SIGTERM):
        """
        Wait for the process to end, filling and returning the result attr.

        :param timeout: Time (seconds) we'll wait until the process is
                        finished. If it's not, we'll try to terminate it
                        and get a status.
        :type timeout: float
        :returns: The command result object.
        :rtype: A :class:`avocado.utils.process.CmdResult` instance.
        """
        start_time = time.time()

        if timeout is None:
            self.wait()

        if timeout > 0.0:
            while time.time() - start_time < timeout:
                self.poll()
                if self.result.exit_status is not None:
                    break

        if self.result.exit_status is None:
            internal_timeout = 1.0
            self.send_signal(sig)
            stop_time = time.time() + internal_timeout
            while time.time() < stop_time:
                self.poll()
                if self.result.exit_status is not None:
                    break
            else:
                self.kill()
                self.poll()

        # If all this work fails, we're dealing with a zombie process.
        e_msg = 'Zombie Process %s' % self.sp.pid
        assert self.result.exit_status is not None, e_msg

        return self.result


class GDBSubProcess(object):

    '''
    Runs a subprocess inside the GNU Debugger
    '''

    def __init__(self, cmd, verbose=True, record_stream_files=False):
        self.cmd = cmd

        self.args = shlex.split(cmd)
        self.binary = self.args[0]
        self.binary_path = os.path.abspath(self.cmd)
        self.result = CmdResult(cmd)

        self.gdb_server = gdb.GDBServer()
        self.gdb = gdb.GDB()
        self.gdb.connect(self.gdb_server.port)
        self.gdb.set_file(self.binary)

    def _get_breakpoints(self):
        breakpoints = []
        for expr in runtime.GDB_RUN_BINARY_NAMES_EXPR:
            expr_binary_name, breakpoint = split_gdb_expr(expr)
            binary_name = os.path.basename(self.binary)
            if expr_binary_name == binary_name:
                breakpoints.append(breakpoint)

        if not breakpoints:
            breakpoints.append(gdb.GDB.DEFAULT_BREAK)
        return breakpoints

    def create_and_wait_on_resume_fifo(self, path):
        '''
        Creates a FIFO file and waits until it's written to

        :param path: the path that the file will be created
        :type path: str
        :returns: first character that was written to the fifo
        :rtype: str
        '''
        os.mkfifo(path)
        f = open(path, 'r')
        c = f.read(1)
        f.close()
        os.unlink(path)
        return c

    def generate_gdb_connect_cmds(self):
        current_test = runtime.CURRENT_TEST
        if current_test is not None:
            binary_name = os.path.basename(self.binary)
            script_name = '%s.gdb.connect_commands' % binary_name
            path = os.path.join(current_test.outputdir, script_name)
            cmds = open(path, 'w')
            cmds.write('file %s\n' % self.binary)
            cmds.write('target extended-remote :%s\n' % self.gdb_server.port)
            cmds.close()
            return path

    def generate_gdb_connect_sh(self):
        cmds = self.generate_gdb_connect_cmds()
        if not cmds:
            return

        current_test = runtime.CURRENT_TEST
        if current_test is not None:
            binary_name = os.path.basename(self.binary)

            fifo_name = "%s.gdb.cont.fifo" % os.path.basename(binary_name)
            fifo_path = os.path.join(current_test.outputdir, fifo_name)

            script_name = '%s.gdb.sh' % binary_name
            script_path = os.path.join(current_test.outputdir, script_name)

            script = open(script_path, 'w')
            script.write("#!/bin/sh\n")
            script.write("%s -x %s\n" % (gdb.GDB.GDB_PATH, cmds))
            script.write("echo -n 'C' > %s\n" % fifo_path)
            script.close()
            os.chmod(script_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
            return (script_path, fifo_path)

    def generate_core(self):
        core_name = "%s.core" % os.path.basename(self.binary)
        core_path = os.path.join(runtime.CURRENT_TEST.outputdir, core_name)
        gcore_cmd = 'gcore %s' % core_path
        r = self.gdb.cli_cmd(gcore_cmd)
        if not r.result.class_ == 'done':
            raise gdb.UnexpectedResponseError
        # also copy the binary as it's needed with the core
        shutil.copy(self.binary, runtime.CURRENT_TEST.outputdir)
        return core_path

    def handle_break_hit(self, response):
        self.gdb.disconnect()
        script_path, fifo_path = self.generate_gdb_connect_sh()

        msg = ("\n\nTEST PAUSED because of debugger breakpoint. "
               "To DEBUG your application run:\n%s\n\n"
               "NOTE: please use *disconnect* command in gdb before exiting, "
               "or else the debugged process will be KILLED\n" % script_path)

        runtime.CURRENT_TEST.paused = True
        runtime.CURRENT_TEST.paused_msg = msg
        runtime.CURRENT_TEST.report_state()
        runtime.CURRENT_TEST.paused_msg = ''

        return self.create_and_wait_on_resume_fifo(fifo_path)

    def handle_fatal_signal(self, response):
        script_path, fifo_path = self.generate_gdb_connect_sh()

        msg = ("\n\nTEST PAUSED because inferior process received a FATAL SIGNAL. "
               "To DEBUG your application run:\n%s\n\n" % script_path)

        if runtime.GDB_ENABLE_CORE:
            core = self.generate_core()
            msg += ("\nAs requested, a core dump has been generated "
                    "automatically at the following location:\n%s\n") % core

        self.gdb.disconnect()

        runtime.CURRENT_TEST.paused = True
        runtime.CURRENT_TEST.paused_msg = msg
        runtime.CURRENT_TEST.report_state()
        runtime.CURRENT_TEST.paused_msg = ''

        return self.create_and_wait_on_resume_fifo(fifo_path)

    def _is_thread_stopped(self):
        result = False
        thread_info_result = self.gdb.cmd("-thread-info")
        thread_info_mi_result = thread_info_result.result
        if hasattr(thread_info_mi_result, 'result'):
            thread_info = thread_info_mi_result.result
            current_thread = thread_info.current_thread_id
            for thread in thread_info.threads:
                if current_thread == thread.id and thread.state == "stopped":
                    result = True
                    break
        return result

    @staticmethod
    def _get_exit_status(parsed_msg):
        """
        Returns the exit code converted to an integer
        """
        code = parsed_msg.result.exit_code
        if (code.startswith('0x') and len(code) > 2):
            return int(code[2:], 16)
        elif (code.startswith('0') and len(code) > 1):
            return int(code[1:], 8)
        else:
            return int(code)

    def wait_for_exit(self):
        """
        Waits until debugger receives a message about the binary exit
        """
        result = False
        messages = []
        while True:
            try:
                msgs = self.gdb.read_until_break()
                messages += msgs
            except:
                pass

            try:
                msg = messages.pop(0)
                parsed_msg = gdb.parse_mi(msg)

                if gdb.is_exit(parsed_msg):
                    self.result.exit_status = self._get_exit_status(parsed_msg)
                    result = True
                    break

                elif gdb.is_break_hit(parsed_msg):
                    # waits on fifo read() until end of debug session is notified
                    r = self.handle_break_hit(parsed_msg)
                    if r == 'C':
                        self.gdb.connect(self.gdb_server.port)
                        if self._is_thread_stopped():
                            r = self.gdb.cli_cmd("continue")
                        else:
                            log.warn('Binary "%s" terminated inside the '
                                     'debugger before avocado was resumed. '
                                     'Because important information about the '
                                     'process was lost the results is '
                                     'undefined. The test is going to be '
                                     'skipped. Please let avocado finish the '
                                     'the execution of your binary to have '
                                     'dependable results.', self.binary)
                            raise GDBInferiorProcessExitedError

                elif gdb.is_fatal_signal(parsed_msg):
                    # waits on fifo read() until end of debug session is notified
                    r = self.handle_fatal_signal(parsed_msg)
                    log.warn('Because "%s" received a fatal signal, this test '
                             'is going to be skipped.', self.binary)
                    raise GDBInferiorProcessExitedError

            except IndexError:
                continue

        return result

    def run(self, timeout=None):
        self.gdb.allocate_pts()

        for b in self._get_breakpoints():
            self.gdb.set_break(b, ignore_error=True)

        result = self.gdb.run(self.args[1:])
        while True:
            r = self.wait_for_exit()
            if r:
                self.gdb.disconnect()
                self.gdb_server.exit()
                self.result.stdout = self.get_stdout()
                self.result.stderr = self.result.stdout
                return self.result

    def get_stdout(self):
        """
        Get the full stdout of the subprocess so far.

        :return: Standard output of the process.
        :rtype: str
        """
        out = ''
        buff_size = 1024

        if self.gdb.inferior_tty_master_fd is None:
            return out

        while True:
            read = os.read(self.gdb.inferior_tty_master_fd, buff_size)
            out += read
            if len(read) < buff_size:
                break
        return out

    get_stderr = get_stdout


def split_gdb_expr(expr):
    '''
    Splits a GDB expr into (binary_name, breakpoint_location)

    Returns :attr:`avocado.gdb.GDB.DEFAULT_BREAK` as the default breakpoint
    if one is not given.

    :param expr: an expression of the form <binary_name>[:<breakpoint>]
    :type expr: str
    :returns: a (binary_name, breakpoint_location) tuple
    :rtype: tuple
    '''
    expr_split = expr.split(':', 1)
    if len(expr_split) == 2:
        r = tuple(expr_split)
    else:
        r = (expr_split[0], gdb.GDB.DEFAULT_BREAK)
    return r


def should_run_inside_gdb(cmd):
    '''
    Wether the given command should be run inside the GNU debugger

    :param cmd: the command arguments, from where we extract the binary name
    '''
    args = shlex.split(cmd)
    cmd_binary_name = os.path.basename(args[0])

    for expr in runtime.GDB_RUN_BINARY_NAMES_EXPR:
        binary_name = os.path.basename(expr.split(':', 1)[0])
        if cmd_binary_name == binary_name:
            return True
    return False


def get_sub_process_klass(cmd):
    '''
    Which sub process implementation should be used

    Either the regular one, or the GNU Debugger version

    :param cmd: the command arguments, from where we extract the binary name
    '''
    if should_run_inside_gdb(cmd):
        return GDBSubProcess
    else:
        return SubProcess


def run(cmd, timeout=None, verbose=True, ignore_status=False, allow_output_check='all'):
    """
    Run a subprocess, returning a CmdResult object.

    :param cmd: Command line to run.
    :type cmd: str
    :param timeout: Time limit in seconds before attempting to kill the
                    running process. This function will take a few seconds
                    longer than 'timeout' to complete if it has to kill the
                    process.
    :type timeout: float
    :param verbose: Whether to log the command run and stdout/stderr.
    :type verbose: bool
    :param ignore_status: Whether to raise an exception when command returns
                          =! 0 (False), or not (True).
    :type ignore_status: bool
    :param allow_output_check: Whether to log the command stream outputs
                               (stdout and stderr) in the test stream
                               files. Valid values: 'stdout', for
                               allowing only standard output, 'stderr',
                               to allow only standard error, 'all',
                               to allow both standard output and error
                               (default), and 'none', to allow
                               none to be recorded.
    :type allow_output_check: str

    :return: An :class:`avocado.utils.process.CmdResult` object.
    :raise: :class:`avocado.core.exceptions.CmdError`, if ``ignore_status=False``.
    """
    klass = get_sub_process_klass(cmd)
    sp = klass(cmd=cmd, verbose=verbose,
               allow_output_check=allow_output_check)
    cmd_result = sp.run(timeout=timeout)
    fail_condition = cmd_result.exit_status != 0 or cmd_result.interrupted
    if fail_condition and not ignore_status:
        raise exceptions.CmdError(cmd, sp.result)
    return cmd_result


def system(cmd, timeout=None, verbose=True, ignore_status=False,
           allow_output_check='all'):
    """
    Run a subprocess, returning its exit code.

    :param cmd: Command line to run.
    :type cmd: str
    :param timeout: Time limit in seconds before attempting to kill the
                    running process. This function will take a few seconds
                    longer than 'timeout' to complete if it has to kill the
                    process.
    :type timeout: float
    :param verbose: Whether to log the command run and stdout/stderr.
    :type verbose: bool
    :param ignore_status: Whether to raise an exception when command returns
                          =! 0 (False), or not (True).
    :type ignore_status: bool
    :param allow_output_check: Whether to log the command stream outputs
                               (stdout and stderr) in the test stream
                               files. Valid values: 'stdout', for
                               allowing only standard output, 'stderr',
                               to allow only standard error, 'all',
                               to allow both standard output and error
                               (default), and 'none', to allow
                               none to be recorded.
    :type allow_output_check: str
    :return: Exit code.
    :rtype: int
    :raise: :class:`avocado.core.exceptions.CmdError`, if ``ignore_status=False``.
    """
    cmd_result = run(cmd=cmd, timeout=timeout, verbose=verbose, ignore_status=ignore_status,
                     allow_output_check=allow_output_check)
    return cmd_result.exit_status


def system_output(cmd, timeout=None, verbose=True, ignore_status=False, allow_output_check='all'):
    """
    Run a subprocess, returning its output.

    :param cmd: Command line to run.
    :type cmd: str
    :param timeout: Time limit in seconds before attempting to kill the
                    running process. This function will take a few seconds
                    longer than 'timeout' to complete if it has to kill the
                    process.
    :type timeout: float
    :param verbose: Whether to log the command run and stdout/stderr.
    :type verbose: bool
    :param ignore_status: Whether to raise an exception when command returns
                          =! 0 (False), or not (True).
    :param allow_output_check: Whether to log the command stream outputs
                               (stdout and stderr) in the test stream
                               files. Valid values: 'stdout', for
                               allowing only standard output, 'stderr',
                               to allow only standard error, 'all',
                               to allow both standard output and error
                               (default), and 'none', to allow
                               none to be recorded.
    :type allow_output_check: str
    :return: Command output.
    :rtype: str
    :raise: :class:`avocado.core.exceptions.CmdError`, if ``ignore_status=False``.
    """
    cmd_result = run(cmd=cmd, timeout=timeout, verbose=verbose, ignore_status=ignore_status,
                     allow_output_check=allow_output_check)
    return cmd_result.stdout
