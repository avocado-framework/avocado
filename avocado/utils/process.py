"""
Functions dedicated to find and run external commands.
"""

import logging
import os
import subprocess
import shlex
import time

from avocado.core import exceptions
from avocado.utils import misc

log = logging.getLogger('avocado.utils')


class CmdNotFoundError(Exception):

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
    :raise: ValueError in case the command was not found.
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


class CmdResult(object):

    """
    Command execution result.

    command:     String containing the command line itself
    exit_status: Integer exit code of the process
    stdout:      String containing stdout of the process
    stderr:      String containing stderr of the process
    duration:    Elapsed wall clock time running the process
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


def run(cmd, verbose=True, ignore_status=False):
    if verbose:
        log.info("Running '%s'", cmd)
    args = shlex.split(cmd)
    start = time.time()
    p = subprocess.Popen(args,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    duration = time.time() - start
    result = CmdResult(cmd)
    result.exit_status = p.returncode
    result.stdout = stdout
    result.stderr = stderr
    result.duration = duration
    if p.returncode != 0 and not ignore_status:
        raise exceptions.CmdError(cmd, result)
    return result


def system(cmd, verbose=True, ignore_status=False):
    cmd_result = run(cmd, verbose, ignore_status)
    return cmd_result.exit_status


def system_output(cmd, verbose=True, ignore_status=False):
    cmd_result = run(cmd, verbose, ignore_status)
    return cmd_result.stdout
