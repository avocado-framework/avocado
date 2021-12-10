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

import contextlib
import errno
import fnmatch
import glob
import logging
import os
import re
import select
import shlex
import signal
import subprocess
import threading
import time
from io import BytesIO, UnsupportedOperation

from avocado.utils import astring, path
from avocado.utils.wait import wait_for

LOG = logging.getLogger(__name__)

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

# variable=value bash assignment
_RE_BASH_SET_VARIABLE = re.compile(r"[a-zA-Z]\w*=.*")


class CmdError(Exception):

    def __init__(self, command=None, result=None, additional_text=None):  # pylint: disable=W0231
        self.command = command
        self.result = result
        self.additional_text = additional_text

    def __str__(self):
        return ("Command '%s' failed.\nstdout: %r\nstderr: %r\nadditional_info: %s" %
                (self.command, self.result.stdout, self.result.stderr, self.additional_text))


class CmdInputError(Exception):
    """Raised when the command given is invalid, such as an empty command."""


def can_sudo(cmd=None):
    """
    Check whether sudo is available (or running as root)

    :param cmd: unicode string with the commands
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


def get_capabilities(pid=None):
    """Gets a list of all capabilities for a process.

    In case the getpcaps command is not available, and empty list will be
    returned.

    It supports getpcaps' two different formats, the current and the so
    called legacy/ugly.

    :param pid: the process ID (PID), if one is not given, the current
                PID is used (given by :func:`os.getpid`)
    :type pid: int
    :returns: all capabilities
    :rtype: list
    """
    if pid is None:
        pid = os.getpid()
    result = run('getpcaps %u' % pid, ignore_status=True)
    if result.exit_status != 0:
        return []
    if result.stderr_text.startswith('Capabilities '):
        info = result.stderr_text
        separator = '='
    else:
        info = result.stdout_text
        separator = ':'
    return info.split(separator, 1)[1].strip().split(',')


def has_capability(capability, pid=None):
    """Checks if a process has a given capability.

    This is a simple wrapper around getpcaps, part of the libcap package.
    In case the getpcaps command is not available, the capability will be
    considered *not* to be available.

    :param capability: the name of the capability, refer to capabilities(7)
                       man page for more information.
    :type capability: str
    :returns: whether the capability is available or not
    :rtype: bool
    """
    return capability in get_capabilities(pid)


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


def safe_kill(pid, signal):  # pylint: disable=W0621
    """
    Attempt to send a signal to a given process that may or may not exist.

    :param signal: Signal number.
    """
    if get_owner_id(int(pid)) == 0:
        kill_cmd = 'kill -%d %d' % (int(signal), int(pid))
        try:
            run(kill_cmd, sudo=True)
            return True
        except CmdError:
            return False

    try:
        os.kill(pid, signal)
        return True
    except Exception:  # pylint: disable=W0703
        return False


def get_parent_pid(pid):
    """
    Returns the parent PID for the given process

    :note: This is currently Linux specific.

    :param pid: The PID of child process
    :returns: The parent PID
    :rtype: int
    """
    with open('/proc/%d/stat' % pid, 'rb') as proc_stat:
        parent_pid = proc_stat.read().split(b' ')[-49]
        return int(parent_pid)


def _get_pid_from_proc_pid_stat(proc_path):
    match = re.match(r'\/proc\/([0-9]+)\/.*', proc_path)
    if match is not None:
        return int(match.group(1))


def get_children_pids(parent_pid, recursive=False):
    """
    Returns the children PIDs for the given process

    :note: This is currently Linux specific.

    :param parent_pid: The PID of parent child process
    :returns: The PIDs for the children processes
    :rtype: list of int
    """
    proc_stats = glob.glob('/proc/[123456789]*/stat')
    children = []
    for proc_stat in proc_stats:
        try:
            with open(proc_stat, 'rb') as proc_stat_fp:
                this_parent_pid = int(proc_stat_fp.read().split(b' ')[-49])
        except IOError:
            continue

        if this_parent_pid == parent_pid:
            children.append(_get_pid_from_proc_pid_stat(proc_stat))

    if recursive:
        for child in children:
            children.extend(get_children_pids(child))
    return children


def kill_process_tree(pid, sig=None, send_sigcont=True, timeout=0):
    """
    Signal a process and all of its children.

    If the process does not exist -- return.

    :param pid: The pid of the process to signal.
    :param sig: The signal to send to the processes, defaults to
                :data:`signal.SIGKILL`
    :param send_sigcont: Send SIGCONT to allow killing stopped processes
    :param timeout: How long to wait for the pid(s) to die
                    (negative=infinity, 0=don't wait,
                    positive=number_of_seconds)
    :return: list of all PIDs we sent signal to
    :rtype: list
    """
    def _all_pids_dead(killed_pids):
        for pid in killed_pids:
            if pid_exists(pid):
                return False
        return True

    if sig is None:
        sig = signal.SIGKILL

    if timeout > 0:
        start = time.monotonic()

    if not safe_kill(pid, signal.SIGSTOP):
        return [pid]
    killed_pids = [pid]
    for child in get_children_pids(pid):
        killed_pids.extend(kill_process_tree(int(child), sig, False))
    safe_kill(pid, sig)
    if send_sigcont:
        for pid in killed_pids:
            safe_kill(pid, signal.SIGCONT)
    if timeout == 0:
        return killed_pids
    elif timeout > 0:
        if not wait_for(_all_pids_dead, timeout + start - time.monotonic(),
                        step=0.01, args=(killed_pids[::-1],)):
            raise RuntimeError("Timeout reached when waiting for pid %s "
                               "and children to die (%s)" % (pid, timeout))
    else:
        while not _all_pids_dead(killed_pids[::-1]):
            time.sleep(0.01)
    return killed_pids


def kill_process_by_pattern(pattern):
    """
    Send SIGTERM signal to a process with matched pattern.

    :param pattern: normally only matched against the process name
    """
    cmd = "pkill -f %s" % pattern
    result = run(cmd, ignore_status=True)
    if result.exit_status:
        LOG.error("Failed to run '%s': %s", cmd, result)
    else:
        LOG.info("Succeed to run '%s'.", cmd)


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


def binary_from_shell_cmd(cmd):
    """
    Tries to find the first binary path from a simple shell-like command.

    :note: It's a naive implementation, but for commands like:
           `VAR=VAL binary -args || true` gives the right result (binary)
    :param cmd: simple shell-like binary
    :type cmd: unicode string
    :return: first found binary from the cmd
    """
    cmds = shlex.split(cmd)
    for item in cmds:
        if not _RE_BASH_SET_VARIABLE.match(item):
            return item
    raise ValueError("Unable to parse first binary from '%s'" % cmd)


#: This is kept for compatibility purposes, but is now deprecated and
#: will be removed in later versions.  Please use :func:`shlex.split`
#: instead.
cmd_split = shlex.split


class CmdResult:

    """
    Command execution result.

    :param command: the command line itself
    :type command: str
    :param exit_status: exit code of the process
    :type exit_status: int
    :param stdout: content of the process stdout
    :type stdout: bytes
    :param stderr: content of the process stderr
    :type stderr: bytes
    :param duration: elapsed wall clock time running the process
    :type duration: float
    :param pid: ID of the process
    :type pid: int
    :param encoding: the encoding to use for the text version
                     of stdout and stderr, by default
                     :data:`avocado.utils.astring.ENCODING`
    :type encoding: str
    """

    def __init__(self, command="", stdout=b"", stderr=b"",
                 exit_status=None, duration=0, pid=None,
                 encoding=None):
        self.command = command
        self.exit_status = exit_status
        #: The raw stdout (bytes)
        self.stdout = stdout
        #: The raw stderr (bytes)
        self.stderr = stderr
        self.duration = duration
        self.interrupted = False
        self.pid = pid
        if encoding is None:
            encoding = astring.ENCODING
        self.encoding = encoding

    def __str__(self):
        return '\n'.join("%s: %r" % (key, getattr(self, key, "MISSING"))
                         for key in ('command', 'exit_status', 'duration',
                                     'interrupted', 'pid', 'encoding',
                                     'stdout', 'stderr'))

    @property
    def stdout_text(self):
        if hasattr(self.stdout, 'decode'):
            return self.stdout.decode(self.encoding)
        if isinstance(self.stdout, str):
            return self.stdout
        raise TypeError("Unable to decode stdout into a string-like type")

    @property
    def stderr_text(self):
        if hasattr(self.stderr, 'decode'):
            return self.stderr.decode(self.encoding)
        if isinstance(self.stderr, str):
            return self.stderr
        raise TypeError("Unable to decode stderr into a string-like type")


class FDDrainer:

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

    def _log_line(self, line, newline_for_stream='\n'):
        line = astring.to_text(line, self._result.encoding,
                               'replace')
        if self._logger is not None:
            self._logger.debug(self._logger_prefix, line)
        if self._stream_logger is not None:
            self._stream_logger.debug(line + newline_for_stream)

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
                lines = bfr.splitlines()
                for line in lines[:-1]:
                    self._log_line(line)
                if bfr.endswith(b'\n'):
                    self._log_line(lines[-1])
                else:
                    self._log_line(lines[-1], '')
                bfr = b''

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
                if (stream is not None) and (not stream.closed):
                    if hasattr(stream, 'fileno'):
                        try:
                            fileno = stream.fileno()
                            os.fsync(fileno)
                        except UnsupportedOperation:
                            pass
                if hasattr(handler, 'close'):
                    handler.close()


class SubProcess:

    """
    Run a subprocess in the background, collecting stdout/stderr streams.
    """

    def __init__(self, cmd, verbose=True, shell=False, env=None, sudo=False,
                 ignore_bg_processes=False, encoding=None, logger=None):
        """
        Creates the subprocess object, stdout/err, reader threads and locks.

        :param cmd: Command line to run.
        :type cmd: str
        :param verbose: Whether to log the command run and stdout/stderr.
        :type verbose: bool
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
        :param encoding: the encoding to use for the text representation
                         of the command result stdout and stderr, by default
                         :data:`avocado.utils.astring.ENCODING`
        :type encoding: str
        :param logger: User's custom logger, which will be logging the subprocess
                       outputs. When this parameter is not set, the
                       `avocado.utils.process` logger will be used.
        :type logger: logging.Logger
        :raises: ValueError if incorrect values are given to parameters
        """
        if encoding is None:
            encoding = astring.ENCODING
        if sudo:
            self.cmd = self._prepend_sudo(cmd, shell)
        else:
            self.cmd = cmd
        self.verbose = verbose
        self.result = CmdResult(self.cmd, encoding=encoding)
        self.shell = shell
        if env:
            self.env = os.environ.copy()
            self.env.update(env)
        else:
            self.env = None
        self._popen = None

        self.logger = logger or LOG
        self.stdout_logger = self.logger.getChild('stdout')
        self.stderr_logger = self.logger.getChild('stderr')
        self.output_logger = self.logger.getChild('output')
        # Drainers used when reading from the PIPEs and writing to
        # files and logs
        self._stdout_drainer = None
        self._stderr_drainer = None

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
                sudo_cmd = '%s -n' % path.find_command('sudo', check_exec=False)
            except path.CmdNotFoundError as details:
                LOG.error(details)
                LOG.error('Parameter sudo=True provided, but sudo was '
                          'not found. Please consider adding sudo to '
                          'your OS image')
                return cmd
            if shell:
                if ' -s' not in sudo_cmd:
                    sudo_cmd = '%s -s' % sudo_cmd
            cmd = '%s %s' % (sudo_cmd, cmd)
        return cmd

    def _init_subprocess(self):
        def signal_handler(signum, frame):  # pylint: disable=W0613
            self.result.interrupted = "signal/ctrl+c"
            self.wait()
            signal.default_int_handler()

        if self._popen is not None:
            return

        if self.verbose:
            LOG.info("Running '%s'", self.cmd)
        if self.shell is False:
            cmd = shlex.split(self.cmd)
        else:
            cmd = self.cmd
        try:
            self._popen = subprocess.Popen(cmd,
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE,
                                           shell=self.shell,
                                           env=self.env)
        except OSError as details:
            details.strerror += " (%s)" % self.cmd
            raise details

        self.start_time = time.monotonic()  # pylint: disable=W0201

        # prepare fd drainers
        self._stdout_drainer = FDDrainer(
            self._popen.stdout.fileno(),
            self.result,
            name="%s-stdout" % self.cmd,
            logger=self.logger,
            logger_prefix="[stdout] %s",
            stream_logger=None,
            ignore_bg_processes=self._ignore_bg_processes,
            verbose=self.verbose)
        self._stderr_drainer = FDDrainer(
            self._popen.stderr.fileno(),
            self.result,
            name="%s-stderr" % self.cmd,
            logger=self.logger,
            logger_prefix="[stderr] %s",
            stream_logger=None,
            ignore_bg_processes=self._ignore_bg_processes,
            verbose=self.verbose)

        # start stdout/stderr threads
        self._stdout_drainer.start()
        self._stderr_drainer.start()

        try:
            signal.signal(signal.SIGINT, signal_handler)
        except ValueError:
            if self.verbose:
                LOG.info("Command %s running on a thread", self.cmd)

    def _fill_results(self, rc):
        self._init_subprocess()
        self.result.exit_status = rc
        if self.result.duration == 0:
            self.result.duration = time.monotonic() - self.start_time
        if self.verbose:
            LOG.info("Command '%s' finished with %s after %.9fs", self.cmd, rc,
                     self.result.duration)
        self.result.pid = self._popen.pid
        self._fill_streams()

    def _fill_streams(self):
        """
        Close subprocess stdout and stderr, and put values into result obj.
        """
        # Cleaning up threads
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
        return self._stdout_drainer.data.getvalue()

    def get_stderr(self):
        """
        Get the full stderr of the subprocess so far.

        :return: Standard error of the process.
        :rtype: str
        """
        self._init_subprocess()
        return self._stderr_drainer.data.getvalue()

    def terminate(self):
        """
        Send a :attr:`signal.SIGTERM` to the process.
        Please consider using :meth:`stop` instead if you want to
        do all that's possible to finalize the process and wait for it to finish.
        """
        self._init_subprocess()
        self.send_signal(signal.SIGTERM)

    def kill(self):
        """
        Send a :attr:`signal.SIGKILL` to the process.
        Please consider using :meth:`stop` instead if you want to
        do all that's possible to finalize the process and wait for it to finish.
        """
        self._init_subprocess()
        self.send_signal(signal.SIGKILL)

    def send_signal(self, sig):
        """
        Send the specified signal to the process.

        :param sig: Signal to send.
        """
        self._init_subprocess()
        if self.is_sudo_enabled():
            pids = get_children_pids(self.get_pid())
            pids.append(self.get_pid())
            for pid in pids:
                kill_cmd = 'kill -%d %d' % (int(sig), pid)
                with contextlib.suppress(Exception):
                    run(kill_cmd, sudo=True)
        else:
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

    def wait(self, timeout=None, sig=signal.SIGTERM):
        """
        Call the subprocess poll() method, fill results if rc is not None.

        :param timeout: Time (seconds) we'll wait until the process is
                        finished. If it's not, we'll try to terminate it
                        and it's children using ``sig`` and get a
                        status. When the process refuses to die
                        within 1s we use SIGKILL and report the status
                        (be it exit_code or zombie)
        :param sig: Signal to send to the process in case it did not end after
                    the specified timeout.
        """
        def nuke_myself():
            self.result.interrupted = ("timeout after %.9fs"
                                       % (time.monotonic() - self.start_time))
            try:
                kill_process_tree(self.get_pid(), sig, timeout=1)
            except RuntimeError:
                try:
                    kill_process_tree(self.get_pid(), signal.SIGKILL,
                                      timeout=1)
                    LOG.warning("Process '%s' refused to die in 1s after "
                                "sending %s to, destroyed it successfully "
                                "using SIGKILL.", self.cmd, sig)
                except RuntimeError:
                    LOG.error("Process '%s' refused to die in 1s after "
                              "sending %s, followed by SIGKILL, probably "
                              "dealing with a zombie process.", self.cmd,
                              sig)

        self._init_subprocess()
        rc = None

        if timeout is None:
            rc = self._popen.wait()
        elif timeout > 0.0:
            timer = threading.Timer(timeout, nuke_myself)
            try:
                timer.start()
                rc = self._popen.wait()
            finally:
                timer.cancel()

        if rc is None:
            stop_time = time.monotonic() + 1
            while time.monotonic() < stop_time:
                rc = self._popen.poll()
                if rc is not None:
                    break
            else:
                nuke_myself()
                rc = self._popen.poll()

        if rc is None:
            # If all this work fails, we're dealing with a zombie process.
            raise AssertionError('Zombie Process %s' % self._popen.pid)
        self._fill_results(rc)
        return rc

    def stop(self, timeout=None):
        """
        Stop background subprocess.

        Call this method to terminate the background subprocess and
        wait for it results.

        :param timeout: Time (seconds) we'll wait until the process is
                        finished. If it's not, we'll try to terminate it
                        and it's children using ``sig`` and get a
                        status. When the process refuses to die
                        within 1s we use SIGKILL and report the status
                        (be it exit_code or zombie)
        """
        self._init_subprocess()
        if self.result.exit_status is None:
            self.terminate()
        return self.wait(timeout)

    def get_pid(self):
        """
        Reports PID of this process
        """
        self._init_subprocess()
        return self._popen.pid

    def get_user_id(self):
        """
        Reports user id of this process
        """
        self._init_subprocess()
        return get_owner_id(self.get_pid())

    def is_sudo_enabled(self):
        """
        Returns whether the subprocess is running with sudo enabled
        """
        self._init_subprocess()
        return self.get_user_id() == 0

    def run(self, timeout=None, sig=signal.SIGTERM):
        """
        Start a process and wait for it to end, returning the result attr.

        If the process was already started using .start(), this will simply
        wait for it to end.

        :param timeout: Time (seconds) we'll wait until the process is
                        finished. If it's not, we'll try to terminate it
                        and it's children using ``sig`` and get a
                        status. When the process refuses to die
                        within 1s we use SIGKILL and report the status
                        (be it exit_code or zombie)
        :type timeout: float
        :param sig: Signal to send to the process in case it did not end after
                    the specified timeout.
        :type sig: int
        :returns: The command result object.
        :rtype: A :class:`CmdResult` instance.
        """
        self._init_subprocess()
        self.wait(timeout, sig)
        return self.result


class WrapSubProcess(SubProcess):

    """
    Wrap subprocess inside an utility program.
    """

    def __init__(self, cmd, verbose=True,
                 shell=False, env=None, wrapper=None, sudo=False,
                 ignore_bg_processes=False, encoding=None, logger=None):
        if wrapper is None and CURRENT_WRAPPER is not None:
            wrapper = CURRENT_WRAPPER
        self.wrapper = wrapper
        if self.wrapper:
            if not os.path.exists(self.wrapper):
                raise IOError("No such wrapper: '%s'" % self.wrapper)
            cmd = wrapper + ' ' + cmd
        super(WrapSubProcess, self).__init__(cmd, verbose,
                                             shell, env, sudo,
                                             ignore_bg_processes, encoding,
                                             logger)


def should_run_inside_wrapper(cmd):
    """
    Whether the given command should be run inside the wrapper utility.

    :param cmd: the command arguments, from where we extract the binary name
    """
    global CURRENT_WRAPPER  # pylint: disable=W0603
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
    if should_run_inside_wrapper(cmd):
        return WrapSubProcess
    else:
        return SubProcess


def run(cmd, timeout=None, verbose=True, ignore_status=False,
        shell=False, env=None, sudo=False, ignore_bg_processes=False,
        encoding=None, logger=None):
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
    :param encoding: the encoding to use for the text representation
                     of the command result stdout and stderr, by default
                     :data:`avocado.utils.astring.ENCODING`
    :type encoding: str
    :param logger: User's custom logger, which will be logging the subprocess
                   outputs. When this parameter is not set, the
                   `avocado.utils.process` logger will be used.
    :type logger: logging.Logger

    :return: An :class:`CmdResult` object.
    :raise: :class:`CmdError`, if ``ignore_status=False``.
    """
    if not cmd:
        raise CmdInputError("Invalid empty command")
    if encoding is None:
        encoding = astring.ENCODING
    klass = get_sub_process_klass(cmd)
    sp = klass(cmd=cmd, verbose=verbose,
               shell=shell, env=env,
               sudo=sudo, ignore_bg_processes=ignore_bg_processes,
               encoding=encoding, logger=logger)
    cmd_result = sp.run(timeout=timeout)
    fail_condition = cmd_result.exit_status != 0 or cmd_result.interrupted
    if fail_condition and not ignore_status:
        raise CmdError(cmd, sp.result)
    return cmd_result


def system(cmd, timeout=None, verbose=True, ignore_status=False,
           shell=False, env=None, sudo=False, ignore_bg_processes=False,
           encoding=None, logger=None):
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
    :param encoding: the encoding to use for the text representation
                     of the command result stdout and stderr, by default
                     :data:`avocado.utils.astring.ENCODING`
    :type encoding: str
    :param logger: User's custom logger, which will be logging the subprocess
                   outputs. When this parameter is not set, the
                   `avocado.utils.process` logger will be used.
    :type logger: logging.Logger

    :return: Exit code.
    :rtype: int
    :raise: :class:`CmdError`, if ``ignore_status=False``.
    """
    cmd_result = run(cmd=cmd, timeout=timeout, verbose=verbose, ignore_status=ignore_status,
                     shell=shell, env=env, sudo=sudo, ignore_bg_processes=ignore_bg_processes,
                     encoding=encoding, logger=logger)
    return cmd_result.exit_status


def system_output(cmd, timeout=None, verbose=True, ignore_status=False,
                  shell=False, env=None, sudo=False, ignore_bg_processes=False,
                  strip_trail_nl=True, encoding=None, logger=None):
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
    :param encoding: the encoding to use for the text representation
                     of the command result stdout and stderr, by default
                     :data:`avocado.utils.astring.ENCODING`
    :type encoding: str
    :param logger: User's custom logger, which will be logging the subprocess
                   outputs. When this parameter is not set, the
                   `avocado.utils.process` logger will be used.
    :type logger: logging.Logger

    :return: Command output.
    :rtype: bytes
    :raise: :class:`CmdError`, if ``ignore_status=False``.
    """
    cmd_result = run(cmd=cmd, timeout=timeout, verbose=verbose, ignore_status=ignore_status,
                     shell=shell, env=env, sudo=sudo, ignore_bg_processes=ignore_bg_processes,
                     encoding=encoding, logger=logger)
    if strip_trail_nl:
        return cmd_result.stdout.rstrip(b'\n\r')
    return cmd_result.stdout


def getoutput(cmd, timeout=None, verbose=False, ignore_status=True,
              shell=True, env=None, sudo=False, ignore_bg_processes=False,
              logger=None):
    """
    Because commands module is removed in Python3 and it redirect stderr
    to stdout, we port commands.getoutput to make code compatible
    Return output (stdout or stderr) of executing cmd in a shell.

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
    :param logger: User's custom logger, which will be logging the subprocess
                   outputs. When this parameter is not set, the
                   `avocado.utils.process` logger will be used.
    :type logger: logging.Logger

    :return: Command output(stdout or stderr).
    :rtype: str
    """
    return getstatusoutput(cmd=cmd, timeout=timeout, verbose=verbose,
                           ignore_status=ignore_status,
                           shell=shell,
                           env=env, sudo=sudo,
                           ignore_bg_processes=ignore_bg_processes,
                           logger=logger)[1]


def getstatusoutput(cmd, timeout=None, verbose=False, ignore_status=True,
                    shell=True, env=None, sudo=False,
                    ignore_bg_processes=False, logger=None):
    """
    Because commands module is removed in Python3 and it redirect stderr
    to stdout, we port commands.getstatusoutput to make code compatible
    Return (status, output) of executing cmd in a shell.

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
    :param logger: User's custom logger, which will be logging the subprocess
                   outputs. When this parameter is not set, the
                   `avocado.utils.process` logger will be used.
    :type logger: logging.Logger

    :return: Exit status and command output(stdout and stderr).
    :rtype: tuple
    """
    cmd_result = run(cmd=cmd, timeout=timeout, verbose=verbose,
                     ignore_status=ignore_status,
                     shell=shell, env=env, sudo=sudo,
                     ignore_bg_processes=ignore_bg_processes, logger=logger)
    text = cmd_result.stdout_text
    sts = cmd_result.exit_status
    if text[-1:] == '\n':
        text = text[:-1]
    return (sts, text)


def get_owner_id(pid):
    """
    Get the owner's user id of a process

    :param pid: the process id
    :return: user id of the process owner
    """
    try:
        return os.stat('/proc/%d/' % pid).st_uid
    except OSError:
        return None


def get_command_output_matching(command, pattern):
    """
    Runs a command, and if the pattern is in in the output, returns it.

    :param command: the command to execute
    :type command: str
    :param pattern: pattern to search in the output, in a line by line basis
    :type pattern: str

    :return: list of lines matching the pattern
    :rtype: list of str
    """
    return [line for line in run(command).stdout_text.splitlines()
            if pattern in line]
