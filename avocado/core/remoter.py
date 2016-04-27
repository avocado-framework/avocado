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
# Copyright: Red Hat Inc. 2014
# Author: Ruda Moura <rmoura@redhat.com>

"""
Module to provide remote operations.
"""

import getpass
import logging
import time

from .settings import settings
from ..utils import process

LOG = logging.getLogger('avocado.test')

try:
    import fabric.api
    import fabric.network
    import fabric.operations
    import fabric.tasks
except ImportError:
    REMOTE_CAPABLE = False
    LOG.info('Remote module is disabled: could not import fabric')
    fabric = None
else:
    REMOTE_CAPABLE = True


class RemoterError(Exception):
    pass


class ConnectionError(RemoterError):
    pass


def run(command, ignore_status=False, quiet=True, timeout=60):
    """
    Executes a command on the defined fabric hosts.

    This is basically a wrapper to fabric.operations.run, encapsulating
    the result on an avocado process.CmdResult object. This also assumes
    the fabric environment was previously (and properly) initialized.

    :param command: the command string to execute.
    :param ignore_status: Whether to not raise exceptions in case the
        command's return code is different than zero.
    :param timeout: Maximum time allowed for the command to return.
    :param quiet: Whether to not log command stdout/err. Default: True.

    :return: the result of the remote program's execution.
    :rtype: :class:`avocado.utils.process.CmdResult`.
    :raise fabric.exceptions.CommandTimeout: When timeout exhausted.
    """

    result = process.CmdResult()
    start_time = time.time()
    end_time = time.time() + (timeout or 0)   # Support timeout=None
    # Fabric sometimes returns NetworkError even when timeout not reached
    fabric_result = None
    fabric_exception = None
    while True:
        try:
            fabric_result = fabric.operations.run(command=command,
                                                  quiet=quiet,
                                                  warn_only=True,
                                                  timeout=timeout)
            break
        except fabric.network.NetworkError, details:
            fabric_exception = details
            timeout = end_time - time.time()
        if time.time() < end_time:
            break
    if fabric_result is None:
        if fabric_exception is not None:
            raise fabric_exception  # it's not None pylint: disable=E0702
        else:
            raise fabric.network.NetworkError("Remote execution of '%s'"
                                              "failed without any "
                                              "exception. This should not "
                                              "happen." % command)
    end_time = time.time()
    duration = end_time - start_time
    result.command = command
    result.stdout = str(fabric_result)
    result.stderr = fabric_result.stderr
    result.duration = duration
    result.exit_status = fabric_result.return_code
    result.failed = fabric_result.failed
    result.succeeded = fabric_result.succeeded
    if not ignore_status:
        if result.failed:
            raise process.CmdError(command=command, result=result)
    return result


def send_files(local_path, remote_path):
    """
    Send files to the defined fabric host.

    This assumes the fabric environment was previously (and properly)
    initialized.

    :param local_path: the local path.
    :param remote_path: the remote path.
    """
    try:
        fabric.operations.put(local_path, remote_path,
                              mirror_local_mode=True)
    except ValueError:
        return False
    return True


def receive_files(local_path, remote_path):
    """
    Receive files from the defined fabric host.

    This assumes the fabric environment was previously (and properly)
    initialized.

    :param local_path: the local path.
    :param remote_path: the remote path.
    """
    try:
        fabric.operations.get(remote_path,
                              local_path)
    except ValueError:
        return False
    return True


def _update_fabric_env(method):
    """
    Update fabric env with the appropriate parameters.

    :param method: Remote method to wrap.
    :return: Wrapped method.
    """
    def wrapper(*args, **kwargs):
        fabric.api.env.update(host_string=args[0].hostname,
                              user=args[0].username,
                              key_filename=args[0].key_filename,
                              password=args[0].password,
                              port=args[0].port)
        return method(*args, **kwargs)
    return wrapper


class Remote(object):

    """
    Performs remote operations.
    """

    def __init__(self, hostname, username=None, password=None,
                 key_filename=None, port=22, timeout=60, attempts=10):
        """
        Creates an instance of :class:`Remote`.

        :param hostname: the hostname.
        :param username: the username. Default: autodetect.
        :param password: the password. Default: try to use public key.
        :param key_filename: path to an identity file (Example: .pem files
            from Amazon EC2).
        :param timeout: remote command timeout, in seconds. Default: 60.
        :param attempts: number of attempts to connect. Default: 10.
        """
        self.hostname = hostname
        if username is None:
            username = getpass.getuser()
        self.username = username
        self.key_filename = key_filename
        # None = use public key
        self.password = password
        self.port = port
        reject_unknown_hosts = settings.get_value('remoter.behavior',
                                                  'reject_unknown_hosts',
                                                  key_type=bool,
                                                  default=False)
        disable_known_hosts = settings.get_value('remoter.behavior',
                                                 'disable_known_hosts',
                                                 key_type=bool,
                                                 default=False)
        fabric.api.env.update(host_string=hostname,
                              user=username,
                              password=password,
                              key_filename=key_filename,
                              port=port,
                              timeout=timeout / attempts,
                              connection_attempts=attempts,
                              linewise=True,
                              abort_on_prompts=True,
                              abort_exception=ConnectionError,
                              reject_unknown_hosts=reject_unknown_hosts,
                              disable_known_hosts=disable_known_hosts)

    @_update_fabric_env
    def run(self, command, ignore_status=False, quiet=True, timeout=60):
        """
        Run a command on the remote host.

        :param command: the command string to execute.
        :param ignore_status: Whether to not raise exceptions in case the
            command's return code is different than zero.
        :param timeout: Maximum time allowed for the command to return.
        :param quiet: Whether to not log command stdout/err. Default: True.

        :return: the result of the remote program's execution.
        :rtype: :class:`avocado.utils.process.CmdResult`.
        :raise fabric.exceptions.CommandTimeout: When timeout exhausted.
        """
        return_dict = fabric.tasks.execute(run, command, ignore_status,
                                           quiet, timeout,
                                           hosts=[self.hostname])
        return return_dict[self.hostname]

    @staticmethod
    def _run(command, ignore_status=False, quiet=True, timeout=60):
        result = process.CmdResult()
        start_time = time.time()
        end_time = time.time() + (timeout or 0)   # Support timeout=None
        # Fabric sometimes returns NetworkError even when timeout not reached
        fabric_result = None
        fabric_exception = None
        while True:
            try:
                fabric_result = fabric.operations.run(command=command,
                                                      quiet=quiet,
                                                      warn_only=True,
                                                      timeout=timeout,
                                                      pty=False)
                break
            except fabric.network.NetworkError as details:
                fabric_exception = details
                if 'not found in known_hosts' in details.message:
                    break
                timeout = end_time - time.time()
            if time.time() > end_time:
                break
        if fabric_result is None:
            if fabric_exception is not None:
                raise fabric_exception  # it's not None pylint: disable=E0702
            else:
                raise fabric.network.NetworkError("Remote execution of '%s'"
                                                  "failed without any "
                                                  "exception. This should not "
                                                  "happen." % command)
        end_time = time.time()
        duration = end_time - start_time
        result.command = command
        result.stdout = str(fabric_result)
        result.stderr = fabric_result.stderr
        result.duration = duration
        result.exit_status = fabric_result.return_code
        result.failed = fabric_result.failed
        result.succeeded = fabric_result.succeeded
        if not ignore_status:
            if result.failed:
                raise process.CmdError(command=command, result=result)
        return result

    def uptime(self):
        """
        Performs uptime (good to check connection).

        :return: the uptime string or empty string if fails.
        """
        res = self.run('uptime', ignore_status=True)
        if res.exit_status == 0:
            return res
        else:
            return ''

    def makedir(self, remote_path):
        """
        Create a directory.

        :param remote_path: the remote path to create.
        """
        self.run('mkdir -p %s' % remote_path)

    @_update_fabric_env
    def send_files(self, local_path, remote_path):
        """
        Send files to remote host.

        :param local_path: the local path.
        :param remote_path: the remote path.
        """
        result_dict = fabric.tasks.execute(send_files, local_path,
                                           remote_path, hosts=[self.hostname])
        return result_dict[self.hostname]

    @_update_fabric_env
    def receive_files(self, local_path, remote_path):
        """
        Receive files from the remote host.

        :param local_path: the local path.
        :param remote_path: the remote path.
        """
        result_dict = fabric.tasks.execute(receive_files, local_path,
                                           remote_path, hosts=[self.hostname])
        return result_dict[self.hostname]
