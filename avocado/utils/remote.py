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
import os
import tempfile
import time

from avocado.core import exceptions
from avocado.core import output
from avocado.utils import process

LOG = logging.getLogger('avocado.test')

try:
    import fabric.api
    import fabric.operations
    from fabric.contrib.project import rsync_project
except ImportError:
    REMOTE_CAPABLE = False
    LOG.info('Remote module is disabled: could not import fabric')
else:
    REMOTE_CAPABLE = True


class Remote(object):

    """
    Performs remote operations.
    """

    def __init__(self, hostname, username=None, password=None,
                 port=22, timeout=60, attempts=3, quiet=False):
        """
        Creates an instance of :class:`Remote`.

        :param hostname: the hostname.
        :param username: the username. Default: autodetect.
        :param password: the password. Default: try to use public key.
        :param timeout: remote command timeout, in seconds. Default: 60.
        :param attempts: number of attempts to connect. Default: 3.
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
                                connection_timeout=timeout,
                                connection_attempts=attempts,
                                linewise=True)

    @staticmethod
    def _setup_environment(**kwargs):
        """ Setup fabric environemnt """
        fabric.api.env.update(kwargs)

    def run(self, command, ignore_status=False):
        """
        Run a remote command.

        :param command: the command string to execute.

        :return: the result of the remote program's output.
        :rtype: :class:`avocado.utils.process.CmdResult`.
        """
        if not self.quiet:
            LOG.info('[%s] Running command %s', self.hostname, command)
        result = process.CmdResult()
        stdout = output.LoggingFile(logger=logging.getLogger('avocado.test'))
        stderr = output.LoggingFile(logger=logging.getLogger('avocado.test'))
        start_time = time.time()
        fabric_result = fabric.operations.run(command=command,
                                              quiet=self.quiet,
                                              stdout=stdout,
                                              stderr=stderr,
                                              warn_only=True)
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
                raise exceptions.CmdError(command=command, result=result)
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
        if not self.quiet:
            LOG.info('[%s] Sending files %s -> %s', self.hostname,
                     local_path, remote_path)
        with fabric.context_managers.quiet():
            try:
                fabric.operations.put(local_path,
                                      remote_path)
            except ValueError:
                return False
        return True

    def rsync(self, local_path, remote_path):
        """
        Send files to remote.

        :param local_path: the local path.
        :param remote_path: the remote path.
        """
        if not self.quiet:
            LOG.info('[%s] rsync-ing files %s -> %s', self.hostname,
                     local_path, remote_path)
        with fabric.context_managers.quiet():
            try:
                # rsync in fabric doesn't support password passing, using file
                passwdfile = None
                try:
                    _, passwdfile = tempfile.mkstemp(text=self.password)
                    rsync_project(remote_path, local_path,
                                  ssh_opts=('--password-file %s'
                                            % passwdfile))
                finally:
                    if passwdfile:
                        os.unlink(passwdfile)
            except ValueError:
                return False
        return True

    def receive_files(self, local_path, remote_path):
        """
        receive remote files.

        :param local_path: the local path.
        :param remote_path: the remote path.
        """
        if not self.quiet:
            LOG.info('[%s] Receive remote files %s -> %s', self.hostname,
                     local_path, remote_path)
        with fabric.context_managers.quiet():
            try:
                fabric.operations.get(remote_path,
                                      local_path)
            except ValueError:
                return False
        return True
