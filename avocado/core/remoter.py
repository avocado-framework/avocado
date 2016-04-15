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

from ..utils import process

LOG = logging.getLogger('avocado.test')

try:
    import fabric.api
    import fabric.network
    import fabric.operations
except ImportError:
    REMOTE_CAPABLE = False
    LOG.info('Remote module is disabled: could not import fabric')
    fabric = None
else:
    REMOTE_CAPABLE = True


class Remote(object):

    """
    Performs remote operations.
    """

    def __init__(self, hostname, username=None, password=None,
                 port=22, timeout=60, attempts=10, quiet=False):
        """
        Creates an instance of :class:`Remote`.

        :param hostname: the hostname.
        :param username: the username. Default: autodetect.
        :param password: the password. Default: try to use public key.
        :param timeout: remote command timeout, in seconds. Default: 60.
        :param attempts: number of attempts to connect. Default: 10.
        :param quiet: performs quiet operations. Default: True.
        """
        self.hostname = hostname
        if username is None:
            username = getpass.getuser()
        self.username = username
        # None = use public key
        self.password = password
        self.port = port
        self.quiet = quiet
        self._setup_environment(host_string=hostname,
                                user=username,
                                password=password,
                                port=port,
                                timeout=timeout / attempts,
                                connection_attempts=attempts,
                                linewise=True,
                                abort_on_prompts=True,
                                abort_exception=FabricException)

    @staticmethod
    def _setup_environment(**kwargs):
        """ Setup fabric environemnt """
        fabric.api.env.update(kwargs)

    def run(self, command, ignore_status=False, timeout=60):
        """
        Run a remote command.

        :param command: the command string to execute.

        :return: the result of the remote program's output.
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
                                                      quiet=self.quiet,
                                                      warn_only=True,
                                                      timeout=timeout,
                                                      pty=False)
                break
            except fabric.network.NetworkError as details:
                fabric_exception = details
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

    def send_files(self, local_path, remote_path):
        """
        Send files to remote.

        :param local_path: the local path.
        :param remote_path: the remote path.
        """
        try:
            fabric.operations.put(local_path, remote_path,
                                  mirror_local_mode=True)
        except ValueError:
            return False
        return True

    def receive_files(self, local_path, remote_path):
        """
        receive remote files.

        :param local_path: the local path.
        :param remote_path: the remote path.
        """
        try:
            fabric.operations.get(remote_path,
                                  local_path)
        except ValueError:
            return False
        return True


class FabricException(Exception):

    def __init__(self, msg):
        self.fabric_msg = msg

    def __str__(self):
        return self.fabric_msg
