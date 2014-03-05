import logging
import subprocess
import shlex
import time

from avocado.core import exceptions

log = logging.getLogger('avocado.utils')


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
