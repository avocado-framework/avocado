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
import shlex
import subprocess
import time
import threading

from avocado.core import exceptions
import misc
import io


log = logging.getLogger('avocado.test')


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
    path_paths = misc.unique(common_bin_paths + path_paths)

    for dir_path in path_paths:
        cmd_path = os.path.join(dir_path, cmd)
        if os.path.isfile(cmd_path):
            return os.path.abspath(cmd_path)

    raise CmdNotFoundError(cmd, path_paths)


def pid_exists(pid):
    """
    Return True if a given PID is running.

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

    If the process does not exist, return.

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


def get_children_pids(ppid):
    """
    Get all PIDs of children/threads of parent ppid
    param ppid: parent PID
    return: list of PIDs of all children/threads of ppid
    """
    return (system_output("ps -L --ppid=%d -o lwp" % ppid).split('\n')[1:])


def is_zombie(ppid):
    """
    Verify if any processes from PPID are in zombie state.

    Attempt to verify if parent process and any children from PPID is a zombie.

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


def pid_is_alive(pid):
    """
    True if process pid exists and is not yet stuck in Zombie state.
    Zombies are impossible to move between cgroups, etc.
    pid can be integer, or text of integer.
    """
    path = '/proc/%s/stat' % pid

    try:
        stat = io.read_one_line(path)
    except IOError:
        if not os.path.exists(path):
            # file went away
            return False
        raise

    return stat.split()[2] != 'Z'


def get_pid_path(program_name, pid_files_dir=None):
    if not pid_files_dir:
        base_dir = os.path.dirname(__file__)
        pid_path = os.path.abspath(os.path.join(base_dir, "..", "..",
                                                "%s.pid" % program_name))
    else:
        pid_path = os.path.join(pid_files_dir, "%s.pid" % program_name)

    return pid_path


def get_pid_from_file(program_name, pid_files_dir=None):
    """
    Reads the pid from <program_name>.pid in the autotest directory.

    :param program_name the name of the program
    :return: the pid if the file exists, None otherwise.
    """
    pidfile_path = get_pid_path(program_name, pid_files_dir)
    if not os.path.exists(pidfile_path):
        return None

    pidfile = open(get_pid_path(program_name, pid_files_dir), 'r')

    try:
        try:
            pid = int(pidfile.readline())
        except IOError:
            if not os.path.exists(pidfile_path):
                return None
            raise
    finally:
        pidfile.close()

    return pid


def is_alive(program_name, pid_files_dir=None):
    """
    Checks if the process is alive and not in Zombie state.

    :param program_name the name of the program
    :return: True if still alive, False otherwise
    """
    pid = get_pid_from_file(program_name, pid_files_dir)
    if pid is None:
        return False
    return pid_is_alive(pid)


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

    def __repr__(self):
        return ("Command: %s\n"
                "Exit status: %s\n"
                "Duration: %s\n"
                "Stdout:\n%s\n"
                "Stderr:\n%s\n" % (self.command, self.exit_status,
                                   self.duration, self.stdout, self.stderr))


class SubProcess(object):

    """
    Run a subprocess in the background, collecting stdout/stderr streams.
    """

    def __init__(self, cmd, verbose=True):
        """
        Creates the subprocess object, stdout/err, reader threads and locks.

        :param cmd: Command line to run.
        :type cmd: str
        :param verbose: Whether to log the command run and stdout/stderr.
        :type verbose: bool
        """
        args = shlex.split(cmd)
        self.verbose = verbose
        if self.verbose:
            log.info("Running '%s'", cmd)
        self.sp = subprocess.Popen(args,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
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

    def _fd_drainer(self, input_pipe):
        """
        Read from input_pipe, storing and logging output.

        :param input_pipe: File like object to the stream.
        """
        if input_pipe == self.sp.stdout:
            prefix = '[stdout] %s'
            output_file = self.stdout_file
            lock = self.stdout_lock
        elif input_pipe == self.sp.stderr:
            prefix = '[stderr] %s'
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
                        bfr = ''
            finally:
                lock.release()

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
        try:
            os.kill(self.sp.pid, signal.SIGTERM)
        except:
            pass

    def kill(self):
        """
        Send a :attr:`signal.SIGKILL` to the process.
        """
        try:
            os.kill(self.sp.pid, signal.SIGKILL)
        except:
            pass

    def wait(self, timeout=None):
        """
        Wait for the process to end, filling and returning the result attr.

        :param timeout: Time (seconds) we'll wait until the process is
                        finished. If it's not, we'll try to terminate it
                        and get a status.
        :type timeout: float
        :returns: The command result object.
        :rtype: A :class:`avocado.utils.process.CmdResult` instance.
        """
        if timeout is None:
            self.sp.wait()
            self.result.exit_status = self.sp.returncode

        if timeout > 0:
            start_time = time.time()
            while time.time() - start_time < timeout:
                self.result.exit_status = self.sp.poll()
                if self.result.exit_status is not None:
                    break
        else:
            # Give one second to check if we can successfully kill the process
            timeout = 1

        if self.result.exit_status is None:
            self.terminate()
            # Timeout here should be 1 second (see comment above)
            stop_time = time.time() + timeout
            while time.time() < stop_time:
                self.result.exit_status = self.sp.poll()
                if self.result.exit_status is not None:
                    break
            else:
                self.kill()
                self.result.exit_status = self.sp.poll()

        duration = time.time() - self.start_time
        self.result.duration = duration

        self.cleanup()

        return self.result

    def cleanup(self):
        """
        Close subprocess stdout and stderr, and put values into result obj.
        """
        # Cleaning up threads
        self.stdout_thread.join(1)
        self.stderr_thread.join(1)
        # Last sanity check
        e_msg = 'Stdout thread for %s is still alive' % self.sp.pid
        assert not self.stdout_thread.isAlive(), e_msg
        e_msg = 'Stderr thread for %s is still alive' % self.sp.pid
        assert not self.stderr_thread.isAlive(), e_msg
        # If this fails, we're dealing with a zombie process
        e_msg = 'Zombie Process %s' % self.sp.pid
        assert self.result.exit_status is not None, e_msg
        # Clean subprocess pipes and populate stdout/err
        self.sp.stdout.close()
        self.sp.stderr.close()
        self.result.stdout = self.get_stdout()
        self.result.stderr = self.get_stderr()


def run(cmd, timeout=None, verbose=True, ignore_status=False):
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
    :return: An :class:`avocado.utils.process.CmdResult` object.
    :raise: :class:`avocado.core.exceptions.CmdError`, if ``ignore_status=False``.
    """
    sp = SubProcess(cmd=cmd, verbose=verbose)
    cmd_result = sp.wait(timeout=timeout)
    if cmd_result.exit_status != 0 and not ignore_status:
        raise exceptions.CmdError(cmd, sp.result)
    return cmd_result


def system(cmd, timeout=None, verbose=True, ignore_status=False):
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
    :return: Exit code.
    :rtype: int
    :raise: :class:`avocado.core.exceptions.CmdError`, if ``ignore_status=False``.
    """
    cmd_result = run(cmd=cmd, timeout=timeout, verbose=verbose,
                     ignore_status=ignore_status)
    return cmd_result.exit_status


def system_output(cmd, timeout=None, verbose=True, ignore_status=False):
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
    :return: Command output.
    :rtype: str
    :raise: :class:`avocado.core.exceptions.CmdError`, if ``ignore_status=False``.
    """
    cmd_result = run(cmd=cmd, timeout=timeout, verbose=verbose,
                     ignore_status=ignore_status)
    return cmd_result.stdout
