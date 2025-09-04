"""Utility helpers for executing shell commands on local or remote hosts.

This module centralizes the logic used by network utilities to
run commands either on the local machine or through a remote session,
with optional privilege escalation via 'sudo'.
"""

from avocado.utils import process


def run_command(command, host, sudo=False):
    """Executes a given command on a specified host, either locally or remotely.

    This function determines if the command should be run on the local machine
    or a remote host based on the type of the 'host' object. It can also
    execute commands with superuser privileges if specified.

    :param command: The command string to be executed.
    :type command: str
    :param host: The host object where the command will be run.
                 If host.__class__.__name__ is "LocalHost", the command
                 is run locally. Otherwise, it's treated as a remote host
                 with a 'remote_session' attribute supporting a 'cmd' method.
    :type host: object
    :param sudo: If True, the command will be executed with 'sudo'.
                 Defaults to False.
    :type sudo: bool
    :return: The standard output of the executed command, decoded as UTF-8.
    :rtype: str
    :raises AttributeError: If 'host' is not "LocalHost" and does not have
                            a 'remote_session.cmd' method.
    """
    if host.__class__.__name__ == "LocalHost":
        return process.system_output(command, sudo=sudo).decode("utf-8")

    if sudo:
        command = f"sudo {command}"
    return host.remote_session.cmd(command).stdout.decode("utf-8")
