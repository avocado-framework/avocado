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

import errno
import fnmatch
import logging
import os
import re
import select
import shlex
import shutil
import signal
import stat
import subprocess
import threading
import time

from io import BytesIO

from . import gdb
from . import runtime
from . import path
from . import genio

log = logging.getLogger('avocado.test')
stdout_log = logging.getLogger('avocado.test.stdout')
stderr_log = logging.getLogger('avocado.test.stderr')
output_log = logging.getLogger('avocado.test.output')

#: The active wrapper utility script.
CURRENT_WRAPPER = None

#: The global wrapper.
#: If set, run every process under this wrapper.
WRAP_PROCESS = None

#: Set wrapper per program names.
#: A list of wrappers and program names.
#: Format: [ ('/path/to/wrapper.sh', 'progname'), ... ]
WRAP_PROCESS_NAMES_EXPR = []

#: Exception to be raised when users of this API need to know that the
#: execution of a given process resulted in undefined behavior. One
#: concrete example when a user, in an interactive session, let the
#: inferior process exit before before avocado resumed the debugger
#: session. Since the information is unknown, and the behavior is
#: undefined, this situation will be flagged by an exception.
UNDEFINED_BEHAVIOR_EXCEPTION = None

#: The current output record mode.  It's not possible to record
#: both the 'stdout' and 'stderr' streams, and at the same time
#: in the right order, the combined 'output' stream.  So this
#: setting defines the mode.
OUTPUT_CHECK_RECORD_MODE = None

# variable=value bash assignment
_RE_BASH_SET_VARIABLE = re.compile(r"[a-zA-Z]\w*=.*")


class CmdError(Exception):

    def __init__(self, command=None, result=None, additional_text=None):
        self.command = command
        self.result = result
        self.additional_text = additional_text

    def __str__(self):
        if self.result is not None:
            if self.result.interrupted:
                msg = "Command '%s' interrupted by %s"
                msg %= (self.command, self.result.interrupted)
            elif self.result.exit_status is None:
                msg = "Command '%s' failed and is not responding to signals"
                msg %= self.command
            else:
                msg = "Command '%s' failed (rc=%d)"
                msg %= (self.command, self.result.exit_status)
            if self.additional_text:
                msg += ", " + self.additional_text
            return msg
        else:
            return "CmdError"


def can_sudo(cmd=None):
    """
    Check whether sudo is available (or running as root)
    """
    if os.getuid() == 0:    # Root
        return True

    try:    # Does sudo binary exists?
        path.find_command('sudo')
    except path.CmdNotFoundError:
        return False

    try:
        if cmd:     # Am I able to run the cmd or plain sudo id?
            return not system(cmd, ignore_status=True, sudo=True)
        elif system_output("id -u", ignore_status=True, sudo=True).strip() == "0":
            return True
        else:
            return False
    except OSError:     # Broken sudo binary
        return False


def pid_exists(pid):
    """
    Return True if a given PID exists.

    :param pid: Process ID number.
    """
    try:
        os.kill(pid, 0)
    except OSError as detail:
        if detail.errno == errno.ESRCH:
            return False
    return True


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


def kill_process_tree(pid, sig=signal.SIGKILL, send_sigcont=True):
    """
    Signal a process and all of its children.

    If the process does not exist -- return.

    :param pid: The pid of the process to signal.
    :param sig: The signal to send to the processes.
    """
    # TODO: This relies on the GNU version of ps (need to fix MacOS support)
    if not safe_kill(pid, signal.SIGSTOP):
        return
    children = system_output("ps --ppid=%d -o pid=" % pid, ignore_status=True,
                             verbose=False).split()
    for child in children:
        kill_process_tree(int(child), sig)
    safe_kill(pid, sig)
    if send_sigcont:
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
    # TODO: This relies on the GNU version of ps (need to fix MacOS support)
    defunct = False
    try:
        pids = get_children_pids(ppid)
    except CmdError:  # Process doesn't exist
        return True
    for pid in pids:
        cmd = "ps --no-headers -o cmd %d" % int(pid)
        proc_name = system_output(cmd, ignore_status=True, verbose=False)
        if '<defunct>' in proc_name:
            defunct = True
            break
    return defunct


def get_children_pids(ppid, recursive=False):
    """
    Get all PIDs of children/threads of parent ppid
    param ppid: parent PID
    param recursive: True to return all levels of sub-processes
    return: list of PIDs of all children/threads of ppid
    """
    # TODO: This relies on the GNU version of ps (need to fix MacOS support)

    cmd = "ps -L --ppid=%d -o lwp"

    # Getting first level of sub-processes
    children = system_output(cmd % ppid, verbose=False).split('\n')[1:]
    if not recursive:
        return children

    # Recursion to get all levels of sub-processes
    for child in children:
        children.extend(system_output(cmd % int(child),
                                      verbose=False,
                                      ignore_status=True).split('\n')[1:])

    return children


def binary_from_shell_cmd(cmd):
    """
    Tries to find the first binary path from a simple shell-like command.

    :note: It's a naive implementation, but for commands like:
           `VAR=VAL binary -args || true` gives the right result (binary)
    :param cmd: simple shell-like binary
    :return: first found binary from the cmd
    """
    try:
        cmds = shlex.split(cmd)
    except ValueError:
        log.warning("binary_from_shell_cmd: Shlex split of %s failed, using "
                    "using simple split.", cmd)
        cmds = cmd.split(" ")
    for item in cmds:
        if not _RE_BASH_SET_VARIABLE.match(item):
            return item
    raise ValueError("Unable to parse first binary from '%s'" % cmd)


class CmdResult(object):

    """
    Command execution result.

    :param command: String containing the command line itself
    :param exit_status: Integer exit code of the process
    :param stdout: String containing stdout of the process
    :param stderr: String containing stderr of the process
    :param duration: Elapsed wall clock time running the process
    :param pid: ID of the process
    """

    def __init__(self, command="", stdout="", stderr="",
                 exit_status=None, duration=0, pid=None):
        self.command = command
        self.exit_status = exit_status
        self.stdout = stdout
        self.stderr = stderr
        self.duration = duration
        self.interrupted = False
        self.pid = pid

    def __repr__(self):
        cmd_rep = ("Command: %s\n"
                   "Exit status: %s\n"
                   "Duration: %s\n"
                   "Stdout:\n%s\n"
                   "Stderr:\n%s\n"
                   "PID:\n%s\n" % (self.command, self.exit_status,
                                   self.duration, self.stdout, self.stderr,
                                   self.pid))
        if self.interrupted:
            cmd_rep += "Command interrupted by %s\n" % self.interrupted
        return cmd_rep


class FDDrainer(object):

    def __init__(self, fd, result, name=None, logger=None, logger_prefix='%s',
                 stream_logger=None, ignore_bg_processes=False, verbose=False):
        """
        Reads data from a file descriptor in a thread, storing locally in
        a file-like :attr:`data` object.

        :param fd: a file descriptor that will be read (drained) from
        :type fd: int
        :param result: a :class:`CmdResult` instance associated with the process
                       used to detect if the process is still running and
                       if there's still data to be read.
        :type result: a :class:`CmdResult` instance
        :param name: a descriptive name that will be passed to the Thread name
        :type name: str
        :param logger: the logger that will be used to (interactively) write
                       the content from the file descriptor
        :type logger: :class:`logging.Logger`
        :param logger_prefix: the prefix used when logging the data
        :type logger_prefix: str with one %-style string formatter
        :param ignore_bg_processes: When True the process does not wait for
                    child processes which keep opened stdout/stderr streams
                    after the main process finishes (eg. forked daemon which
                    did not closed the stdout/stderr). Note this might result
                    in missing output produced by those daemons after the
                    main thread finishes and also it allows those daemons
                    to be running after the process finishes.
        :type ignore_bg_processes: boolean
        :param verbose: whether to log in both the logger and stream_logger
        :type verbose: boolean
        """
        self.fd = fd
        self.name = name
        self.data = BytesIO()
        # TODO: check if, when the process finishes, the FD doesn't
        # automatically close.  This may be used as the detection
        # instead.
        self._result = result
        self._thread = None
        self._logger = logger
        self._logger_prefix = logger_prefix
        self._stream_logger = stream_logger
        self._ignore_bg_processes = ignore_bg_processes
        self._verbose = verbose

    def _drainer(self):
        """
        Read from fd, storing and optionally logging the output
        """
        bfr = b''
        while True:
            if self._ignore_bg_processes:
                has_io = select.select([self.fd], [], [], 1)[0]
                if (not has_io and self._result.exit_status is not None):
                    # Exit if no new data and main process has finished
                    break
                if not has_io:
                    # Don't read unless there are new data available
                    continue
            tmp = os.read(self.fd, 8192)
            if not tmp:
                break
            self.data.write(tmp)
            if self._verbose:
                bfr += tmp
                if tmp.endswith(b'\n'):
                    for line in bfr.splitlines():
                        if self._logger is not None:
                            self._logger.debug(self._logger_prefix, line)
                        if self._stream_logger is not None:
                            self._stream_logger.debug('%s\n', line)
                    bfr = b''
        # Write the rest of the bfr unfinished by \n
        if self._verbose and bfr:
            for line in bfr.splitlines():
                if self._logger is not None:
                    self._logger.debug(self._logger_prefix, line)
                if self._stream_logger is not None:
                    self._stream_logger.debug(line)

    def start(self):
        self._thread = threading.Thread(target=self._drainer, name=self.name)
        self._thread.daemon = True
        self._thread.start()

    def flush(self):
        self._thread.join()
        if self._stream_logger is not None:
            for handler in self._stream_logger.handlers:
                # FileHandler has a close() method, which we expect will
                # flush the file on disk.  SocketHandler, MemoryHandler
                # and other logging handlers (custom ones?) also have
                # the same interface, so let's try to use it if available
                stream = getattr(handler, 'stream', None)
                if stream is not None:
                    os.fsync(stream.fileno())
                if hasattr(handler, 'close'):
                    handler.close()


class SubProcess(object):

    """
    Run a subprocess in the background, collecting stdout/stderr streams.
    """

    def __init__(self, cmd, verbose=True, allow_output_check=None,
                 shell=False, env=None, sudo=False,
                 ignore_bg_processes=False):
        """
        Creates the subprocess object, stdout/err, reader threads and locks.

        :param cmd: Command line to run.
        :type cmd: str
        :param verbose: Whether to log the command run and stdout/stderr.
        :type verbose: bool
        :param allow_output_check: Whether to record the output from this
                                   process (from stdout and stderr) in the
                                   test's output record files. Valid values:
                                   'stdout', for standard output *only*,
                                   'stderr' for standard error *only*,
                                   'both' for both standard output and error
                                   in separate files, 'combined' for
                                   standard output and error in a single file,
                                   and 'none' to disable all recording. 'all'
                                   is also a valid, but deprecated, option that
                                   is a synonym of 'both'.  If an explicit value
                                   is not given to this parameter, that is, if
                                   None is given, it defaults to using the module
                                   level configuration, as set by
                                   :data:`OUTPUT_CHECK_RECORD_MODE`.  If the
                                   module level configuration itself is not set,
                                   it defaults to 'none'.
        :type allow_output_check: str
        :param shell: Whether to run the subprocess in a subshell.
        :type shell: bool
        :param env: Use extra environment variables.
        :type env: dict
        :param sudo: Whether the command requires admin privileges to run,
                     so that sudo will be prepended to the command.
                     The assumption here is that the user running the command
                     has a sudo configuration such that a password won't be
                     prompted. If that's not the case, the command will
                     straight out fail.
        :type sudo: bool
        :param ignore_bg_processes: When True the process does not wait for
                    child processes which keep opened stdout/stderr streams
                    after the main process finishes (eg. forked daemon which
                    did not closed the stdout/stderr). Note this might result
                    in missing output produced by those daemons after the
                    main thread finishes and also it allows those daemons
                    to be running after the process finishes.
        :raises: ValueError if incorrect values are given to parameters
        """
        if sudo:
            self.cmd = self._prepend_sudo(cmd, shell)
        else:
            self.cmd = cmd
        self.verbose = verbose
        if allow_output_check is None:
            allow_output_check = OUTPUT_CHECK_RECORD_MODE
        if allow_output_check is None:
            allow_output_check = 'both'
        if allow_output_check not in ('stdout', 'stderr', 'both',
                                      'combined', 'none', 'all'):
            msg = ("Invalid value (%s) set in allow_output_check" %
                   allow_output_check)
            raise ValueError(msg)
        self.allow_output_check = allow_output_check
        self.result = CmdResult(self.cmd)
        self.shell = shell
        if env:
            self.env = os.environ.copy()
            self.env.update(env)
        else:
            self.env = None
        self._popen = None

        # Drainers used when reading from the PIPEs and writing to
        # files and logs
        self._stdout_drainer = None
        self._stderr_drainer = None
        self._combined_drainer = None

        self._ignore_bg_processes = ignore_bg_processes

    def __repr__(self):
        if self._popen is None:
            rc = '(not started)'
        elif self.result.exit_status is None:
            rc = '(running)'
        else:
            rc = self.result.exit_status
        return '%s(cmd=%r, rc=%r)' % (self.__class__.__name__, self.cmd, rc)

    def __str__(self):
        if self._popen is None:
            rc = '(not started)'
        elif self.result.exit_status is None:
            rc = '(running)'
        else:
            rc = '(finished with exit status=%d)' % self.result.exit_status
        return '%s %s' % (self.cmd, rc)

    @staticmethod
    def _prepend_sudo(cmd, shell):
        if os.getuid() != 0:
            try:
                sudo_cmd = '%s -n' % path.find_command('sudo')
            except path.CmdNotFoundError as details:
                log.error(details)
                log.error('Parameter sudo=True provided, but sudo was '
                          'not found. Please consider adding sudo to '
                          'your OS image')
                return cmd
            if shell:
                if ' -s' not in sudo_cmd:
                    sudo_cmd = '%s -s' % sudo_cmd
            cmd = '%s %s' % (sudo_cmd, cmd)
        return cmd

    def _init_subprocess(self):
        if self._popen is None:
            if self.verbose:
                log.info("Running '%s'", self.cmd)
            if self.shell is False:
                cmd = shlex.split(self.cmd)
            else:
                cmd = self.cmd
            try:
                if self.allow_output_check == 'combined':
                    stderr = subprocess.STDOUT
                else:
                    stderr = subprocess.PIPE
                self._popen = subprocess.Popen(cmd,
                                               stdout=subprocess.PIPE,
                                               stderr=stderr,
                                               shell=self.shell,
                                               env=self.env)
            except OSError as details:
                details.strerror += " (%s)" % self.cmd
                raise details

            self.start_time = time.time()

            # prepare fd drainers
            if self.allow_output_check == 'combined':
                self._combined_drainer = FDDrainer(
                    self._popen.stdout.fileno(),
                    self.result,
                    name="%s-combined" % self.cmd,
                    logger=log,
                    logger_prefix="[output] %s",
                    # FIXME, in fact, a new log has to be used here
                    stream_logger=output_log,
                    ignore_bg_processes=self._ignore_bg_processes,
                    verbose=self.verbose)
                self._combined_drainer.start()

            else:
                if self.allow_output_check == 'none':
                    stdout_stream_logger = None
                    stderr_stream_logger = None
                else:
                    stdout_stream_logger = stdout_log
                    stderr_stream_logger = stderr_log
                self._stdout_drainer = FDDrainer(
                    self._popen.stdout.fileno(),
                    self.result,
                    name="%s-stdout" % self.cmd,
                    logger=log,
                    logger_prefix="[stdout] %s",
                    stream_logger=stdout_stream_logger,
                    ignore_bg_processes=self._ignore_bg_processes,
                    verbose=self.verbose)
                self._stderr_drainer = FDDrainer(
                    self._popen.stderr.fileno(),
                    self.result,
                    name="%s-stderr" % self.cmd,
                    logger=log,
                    logger_prefix="[stderr] %s",
                    stream_logger=stderr_stream_logger,
                    ignore_bg_processes=self._ignore_bg_processes,
                    verbose=self.verbose)

                # start stdout/stderr threads
                self._stdout_drainer.start()
                self._stderr_drainer.start()

            def signal_handler(signum, frame):
                self.result.interrupted = "signal/ctrl+c"
                self.wait()
                signal.default_int_handler()
            try:
                signal.signal(signal.SIGINT, signal_handler)
            except ValueError:
                if self.verbose:
                    log.info("Command %s running on a thread", self.cmd)

    def _fill_results(self, rc):
        self._init_subprocess()
        self.result.exit_status = rc
        if self.result.duration == 0:
            self.result.duration = time.time() - self.start_time
        if self.verbose:
            log.info("Command '%s' finished with %s after %ss", self.cmd, rc,
                     self.result.duration)
        self.result.pid = self._popen.pid
        self._fill_streams()

    def _fill_streams(self):
        """
        Close subprocess stdout and stderr, and put values into result obj.
        """
        # Cleaning up threads
        if self._combined_drainer is not None:
            self._combined_drainer.flush()
        if self._stdout_drainer is not None:
            self._stdout_drainer.flush()
        if self._stderr_drainer is not None:
            self._stderr_drainer.flush()
        # Clean subprocess pipes and populate stdout/err
        self.result.stdout = self.get_stdout()
        self.result.stderr = self.get_stderr()

    def start(self):
        """
        Start running the subprocess.

        This method is particularly useful for background processes, since
        you can start the subprocess and not block your test flow.

        :return: Subprocess PID.
        :rtype: int
        """
        self._init_subprocess()
        return self._popen.pid

    def get_stdout(self):
        """
        Get the full stdout of the subprocess so far.

        :return: Standard output of the process.
        :rtype: str
        """
        self._init_subprocess()
        if self._combined_drainer is not None:
            return self._combined_drainer.data.getvalue()
        return self._stdout_drainer.data.getvalue()

    def get_stderr(self):
        """
        Get the full stderr of the subprocess so far.

        :return: Standard error of the process.
        :rtype: str
        """
        self._init_subprocess()
        if self._combined_drainer is not None:
            return ''
        return self._stderr_drainer.data.getvalue()

    def terminate(self):
        """
        Send a :attr:`signal.SIGTERM` to the process.
        """
        self._init_subprocess()
        self.send_signal(signal.SIGTERM)

    def kill(self):
        """
        Send a :attr:`signal.SIGKILL` to the process.
        """
        self._init_subprocess()
        self.send_signal(signal.SIGKILL)

    def send_signal(self, sig):
        """
        Send the specified signal to the process.

        :param sig: Signal to send.
        """
        self._init_subprocess()
        self._popen.send_signal(sig)

    def poll(self):
        """
        Call the subprocess poll() method, fill results if rc is not None.
        """
        self._init_subprocess()
        rc = self._popen.poll()
        if rc is not None:
            self._fill_results(rc)
        return rc

    def wait(self):
        """
        Call the subprocess poll() method, fill results if rc is not None.
        """
        self._init_subprocess()
        rc = self._popen.wait()
        if rc is not None:
            self._fill_results(rc)
        return rc

    def stop(self):
        """
        Stop background subprocess.

        Call this method to terminate the background subprocess and
        wait for it results.
        """
        self._init_subprocess()
        if self.result.exit_status is None:
            self.terminate()
        return self.wait()

    def get_pid(self):
        """
        Reports PID of this process
        """
        self._init_subprocess()
        return self._popen.pid

    def run(self, timeout=None, sig=signal.SIGTERM):
        """
        Start a process and wait for it to end, returning the result attr.

        If the process was already started using .start(), this will simply
        wait for it to end.

        :param timeout: Time (seconds) we'll wait until the process is
                        finished. If it's not, we'll try to terminate it
                        and get a status.
        :type timeout: float
        :param sig: Signal to send to the process in case it did not end after
                    the specified timeout.
        :type sig: int
        :returns: The command result object.
        :rtype: A :class:`CmdResult` instance.
        """
        def timeout_handler():
            self.send_signal(sig)
            self.result.interrupted = "timeout after %ss" % timeout

        self._init_subprocess()

        if timeout is None:
            self.wait()
        elif timeout > 0.0:
            timer = threading.Timer(timeout, timeout_handler)
            try:
                timer.start()
                self.wait()
            finally:
                timer.cancel()

        if self.result.exit_status is None:
            stop_time = time.time() + 1
            while time.time() < stop_time:
                self.poll()
                if self.result.exit_status is not None:
                    break
            else:
                self.kill()
                self.poll()

        # If all this work fails, we're dealing with a zombie process.
        e_msg = 'Zombie Process %s' % self._popen.pid
        assert self.result.exit_status is not None, e_msg

        return self.result


class WrapSubProcess(SubProcess):

    """
    Wrap subprocess inside an utility program.
    """

    def __init__(self, cmd, verbose=True,
                 allow_output_check=None,
                 shell=False, env=None, wrapper=None, sudo=False,
                 ignore_bg_processes=False):
        if wrapper is None and CURRENT_WRAPPER is not None:
            wrapper = CURRENT_WRAPPER
        self.wrapper = wrapper
        if self.wrapper:
            if not os.path.exists(self.wrapper):
                raise IOError("No such wrapper: '%s'" % self.wrapper)
            cmd = wrapper + ' ' + cmd
        super(WrapSubProcess, self).__init__(cmd, verbose, allow_output_check,
                                             shell, env, sudo,
                                             ignore_bg_processes)


class GDBSubProcess(object):

    """
    Runs a subprocess inside the GNU Debugger
    """

    def __init__(self, cmd, verbose=True,
                 allow_output_check=None, shell=False,
                 env=None, sudo=False, ignore_bg_processes=False):
        """
        Creates the subprocess object, stdout/err, reader threads and locks.

        :param cmd: Command line to run.
        :type cmd: str
        :param verbose: Whether to log the command run and stdout/stderr.
                        Currently unused and provided for compatibility only.
        :type verbose: bool
        :param allow_output_check: Whether to log the command stream outputs
                                   (stdout and stderr) in the test stream
                                   files. Valid values: 'stdout', for
                                   allowing only standard output, 'stderr',
                                   to allow only standard error, 'all',
                                   to allow both standard output and error
                                   (default), and 'none', to allow
                                   none to be recorded. Currently unused and
                                   provided for compatibility only.
        :type allow_output_check: str
        :param sudo: This param will be ignored in this implementation,
                     since the GDB wrapping code does not have support to run
                     commands under sudo just yet.
        :param ignore_bg_processes: This param will be ignored in this
                     implementation, since the GDB wrapping code does not have
                     support to run commands in that way.
        """

        self.cmd = cmd

        self.args = shlex.split(cmd)
        self.binary = self.args[0]
        self.binary_path = os.path.abspath(self.cmd)
        self.result = CmdResult(cmd)

        self.gdb_server = gdb.GDBServer(gdb.GDBSERVER_PATH)
        self.gdb = gdb.GDB(gdb.GDB_PATH)
        self.gdb.connect(self.gdb_server.port)
        self.gdb.set_file(self.binary)

    def _get_breakpoints(self):
        breakpoints = []
        for expr in gdb.GDB_RUN_BINARY_NAMES_EXPR:
            expr_binary_name, breakpoint = split_gdb_expr(expr)
            binary_name = os.path.basename(self.binary)
            if expr_binary_name == binary_name:
                breakpoints.append(breakpoint)

        if not breakpoints:
            breakpoints.append(gdb.GDB.DEFAULT_BREAK)
        return breakpoints

    def create_and_wait_on_resume_fifo(self, path):
        """
        Creates a FIFO file and waits until it's written to

        :param path: the path that the file will be created
        :type path: str
        :returns: first character that was written to the fifo
        :rtype: str
        """
        os.mkfifo(path)
        with open(path, 'r') as fifo_file:
            c = fifo_file.read(1)
        os.unlink(path)
        return c

    def generate_gdb_connect_cmds(self):
        current_test = runtime.CURRENT_TEST
        if current_test is not None:
            binary_name = os.path.basename(self.binary)
            script_name = '%s.gdb.connect_commands' % binary_name
            path = os.path.join(current_test.outputdir, script_name)
            with open(path, 'w') as cmds_file:
                cmds_file.write('file %s\n' % os.path.abspath(self.binary))
                cmds_file.write('target extended-remote :%s\n' % self.gdb_server.port)
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

            with open(script_path, 'w') as script_file:
                script_file.write("#!/bin/sh\n")
                script_file.write("%s -x %s\n" % (gdb.GDB_PATH, cmds))
                script_file.write("echo -n 'C' > %s\n" % fifo_path)
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

        runtime.CURRENT_TEST.paused = msg
        runtime.CURRENT_TEST.report_state()
        runtime.CURRENT_TEST.paused = ''

        ret = self.create_and_wait_on_resume_fifo(fifo_path)
        runtime.CURRENT_TEST.paused = ("\rResuming ...")
        runtime.CURRENT_TEST.report_state()
        runtime.CURRENT_TEST.paused = ''
        return ret

    def handle_fatal_signal(self, response):
        script_path, fifo_path = self.generate_gdb_connect_sh()

        msg = ("\n\nTEST PAUSED because inferior process received a FATAL SIGNAL. "
               "To DEBUG your application run:\n%s\n\n" % script_path)

        if gdb.GDB_ENABLE_CORE:
            core = self.generate_core()
            msg += ("\nAs requested, a core dump has been generated "
                    "automatically at the following location:\n%s\n") % core

        self.gdb.disconnect()

        runtime.CURRENT_TEST.paused = msg
        runtime.CURRENT_TEST.report_state()
        runtime.CURRENT_TEST.paused = ''

        ret = self.create_and_wait_on_resume_fifo(fifo_path)
        runtime.CURRENT_TEST.paused = ("\rResuming ...")
        runtime.CURRENT_TEST.report_state()
        runtime.CURRENT_TEST.paused = ''
        return ret

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
            except Exception:
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
                            # pylint: disable=E0702
                            if UNDEFINED_BEHAVIOR_EXCEPTION is not None:
                                raise UNDEFINED_BEHAVIOR_EXCEPTION

                elif gdb.is_fatal_signal(parsed_msg):
                    # waits on fifo read() until end of debug session is notified
                    r = self.handle_fatal_signal(parsed_msg)
                    log.warn('Because "%s" received a fatal signal, this test '
                             'is going to be skipped.', self.binary)
                    # pylint: disable=E0702
                    if UNDEFINED_BEHAVIOR_EXCEPTION is not None:
                        raise UNDEFINED_BEHAVIOR_EXCEPTION

            except IndexError:
                continue

        return result

    def _run_pre_commands(self):
        """
        Run commands if user passed a commands file with --gdb-prerun-commands
        """
        binary_name = os.path.basename(self.binary)
        # The commands file can be specific to a given binary or universal,
        # start checking for specific ones first
        prerun_commands_path = gdb.GDB_PRERUN_COMMANDS.get(
            binary_name,
            gdb.GDB_PRERUN_COMMANDS.get('', None))

        if prerun_commands_path is not None:
            for command in genio.read_all_lines(prerun_commands_path):
                self.gdb.cmd(command)

    def run(self, timeout=None):
        for b in self._get_breakpoints():
            self.gdb.set_break(b, ignore_error=True)

        self._run_pre_commands()
        result = self.gdb.run(self.args[1:])

        # Collect gdbserver stdout and stderr file information for debugging
        # based on its process ID and stream (stdout or stderr)
        current_test = runtime.CURRENT_TEST
        if current_test is not None:
            stdout_name = 'gdbserver.%s.stdout' % self.gdb_server.process.pid
            stdout_path = os.path.join(current_test.logdir, stdout_name)
            stderr_name = 'gdbserver.%s.stderr' % self.gdb_server.process.pid
            stderr_path = os.path.join(current_test.logdir, stderr_name)

        while True:
            r = self.wait_for_exit()
            if r:
                self.gdb.disconnect()

                # Now collect the gdbserver stdout and stderr file themselves
                # and populate the CommandResult stdout and stderr
                if current_test is not None:
                    if os.path.exists(self.gdb_server.stdout_path):
                        shutil.copy(self.gdb_server.stdout_path, stdout_path)
                        self.result.stdout = genio.read_file(stdout_path)
                    if os.path.exists(self.gdb_server.stderr_path):
                        shutil.copy(self.gdb_server.stderr_path, stderr_path)
                        self.result.stderr = genio.read_file(stderr_path)

                self.gdb_server.exit()
                return self.result


def split_gdb_expr(expr):
    """
    Splits a GDB expr into (binary_name, breakpoint_location)

    Returns :attr:`avocado.gdb.GDB.DEFAULT_BREAK` as the default breakpoint
    if one is not given.

    :param expr: an expression of the form <binary_name>[:<breakpoint>]
    :type expr: str
    :returns: a (binary_name, breakpoint_location) tuple
    :rtype: tuple
    """
    expr_split = expr.split(':', 1)
    if len(expr_split) == 2:
        r = tuple(expr_split)
    else:
        r = (expr_split[0], gdb.GDB.DEFAULT_BREAK)
    return r


def should_run_inside_gdb(cmd):
    """
    Wether the given command should be run inside the GNU debugger

    :param cmd: the command arguments, from where we extract the binary name
    """
    if not gdb.GDB_RUN_BINARY_NAMES_EXPR:
        return False

    try:
        args = shlex.split(cmd)
    except ValueError:
        log.warning("Unable to check whether command '%s' should run inside "
                    "GDB, fallback to simplified method...", cmd)
        args = cmd.split()
    cmd_binary_name = os.path.basename(args[0])

    for expr in gdb.GDB_RUN_BINARY_NAMES_EXPR:
        binary_name = os.path.basename(expr.split(':', 1)[0])
        if cmd_binary_name == binary_name:
            return True
    return False


def should_run_inside_wrapper(cmd):
    """
    Wether the given command should be run inside the wrapper utility.

    :param cmd: the command arguments, from where we extract the binary name
    """
    global CURRENT_WRAPPER
    CURRENT_WRAPPER = None
    args = shlex.split(cmd)
    cmd_binary_name = args[0]

    for script, cmd_expr in WRAP_PROCESS_NAMES_EXPR:
        if fnmatch.fnmatch(cmd_binary_name, cmd_expr):
            CURRENT_WRAPPER = script

    if WRAP_PROCESS is not None and CURRENT_WRAPPER is None:
        CURRENT_WRAPPER = WRAP_PROCESS

    if CURRENT_WRAPPER is None:
        return False
    else:
        return True


def get_sub_process_klass(cmd):
    """
    Which sub process implementation should be used

    Either the regular one, or the GNU Debugger version

    :param cmd: the command arguments, from where we extract the binary name
    """
    if should_run_inside_gdb(cmd):
        return GDBSubProcess
    elif should_run_inside_wrapper(cmd):
        return WrapSubProcess
    else:
        return SubProcess


def run(cmd, timeout=None, verbose=True, ignore_status=False,
        allow_output_check=None, shell=False,
        env=None, sudo=False, ignore_bg_processes=False):
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
    :param shell: Whether to run the command on a subshell
    :type shell: bool
    :param env: Use extra environment variables
    :type env: dict
    :param sudo: Whether the command requires admin privileges to run,
                 so that sudo will be prepended to the command.
                 The assumption here is that the user running the command
                 has a sudo configuration such that a password won't be
                 prompted. If that's not the case, the command will
                 straight out fail.

    :return: An :class:`CmdResult` object.
    :raise: :class:`CmdError`, if ``ignore_status=False``.
    """
    klass = get_sub_process_klass(cmd)
    sp = klass(cmd=cmd, verbose=verbose,
               allow_output_check=allow_output_check, shell=shell, env=env,
               sudo=sudo, ignore_bg_processes=ignore_bg_processes)
    cmd_result = sp.run(timeout=timeout)
    fail_condition = cmd_result.exit_status != 0 or cmd_result.interrupted
    if fail_condition and not ignore_status:
        raise CmdError(cmd, sp.result)
    return cmd_result


def system(cmd, timeout=None, verbose=True, ignore_status=False,
           allow_output_check=None, shell=False,
           env=None, sudo=False, ignore_bg_processes=False):
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
    :param shell: Whether to run the command on a subshell
    :type shell: bool
    :param env: Use extra environment variables.
    :type env: dict
    :param sudo: Whether the command requires admin privileges to run,
                 so that sudo will be prepended to the command.
                 The assumption here is that the user running the command
                 has a sudo configuration such that a password won't be
                 prompted. If that's not the case, the command will
                 straight out fail.

    :return: Exit code.
    :rtype: int
    :raise: :class:`CmdError`, if ``ignore_status=False``.
    """
    cmd_result = run(cmd=cmd, timeout=timeout, verbose=verbose, ignore_status=ignore_status,
                     allow_output_check=allow_output_check, shell=shell, env=env,
                     sudo=sudo, ignore_bg_processes=ignore_bg_processes)
    return cmd_result.exit_status


def system_output(cmd, timeout=None, verbose=True, ignore_status=False,
                  allow_output_check=None, shell=False,
                  env=None, sudo=False, ignore_bg_processes=False,
                  strip_trail_nl=True):
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
    :param shell: Whether to run the command on a subshell
    :type shell: bool
    :param env: Use extra environment variables
    :type env: dict
    :param sudo: Whether the command requires admin privileges to run,
                 so that sudo will be prepended to the command.
                 The assumption here is that the user running the command
                 has a sudo configuration such that a password won't be
                 prompted. If that's not the case, the command will
                 straight out fail.
    :type sudo: bool
    :param ignore_bg_processes: Whether to ignore background processes
    :type ignore_bg_processes: bool
    :param strip_trail_nl: Whether to strip the trailing newline
    :type strip_trail_nl: bool

    :return: Command output.
    :rtype: str
    :raise: :class:`CmdError`, if ``ignore_status=False``.
    """
    cmd_result = run(cmd=cmd, timeout=timeout, verbose=verbose, ignore_status=ignore_status,
                     allow_output_check=allow_output_check, shell=shell, env=env,
                     sudo=sudo, ignore_bg_processes=ignore_bg_processes)
    if strip_trail_nl:
        return cmd_result.stdout.rstrip('\n\r')
    return cmd_result.stdout
