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

import fabric.api
import fabric.operations


class Remote(object):

    """
    Performs remote operations.
    """

    def __init__(self, hostname, username=None, password=None, quiet=True):
        """
        Creates an instance of Remote.

        :param hostname: the hostname.
        :param username: the username. Default: autodetect.
        :param password: the password. Default: try to use public key.
        :param quiet: performs quiet operations. Default: True.
        """
        self.hostname = hostname
        if username is None:
            username = getpass.getuser()
        self.username = username
        # None = use public key
        self.password = password
        self.quiet = quiet
        self._setup_environment(host_string=hostname,
                                user=username,
                                password=password)

    def _setup_environment(self, **kwargs):
        fabric.api.env.update(kwargs)

    def run(self, command):
        """
        Run an remote command.

        :param command: the command string to execute.

        :returns: the result of the remote program's output.
        """
        return fabric.operations.run(command,
                                     quiet=self.quiet,
                                     warn_only=True)

    def uptime(self):
        """
        Performs uptime (good to check connection).

        :return: the uptime string or empty string if fails.
        """
        res = self.run('uptime')
        if res.succeeded:
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
        with fabric.context_managers.quiet():
            try:
                fabric.operations.put(local_path,
                                      remote_path)
            except ValueError as err:
                return False
        return True

    def receive_files(self, local_path, remote_path):
        """
        receive remote files.

        :param local_path: the local path.
        :param remote_path: the remote path.
        """
        with fabric.context_managers.quiet():
            try:
                fabric.operations.get(remote_path,
                                      local_path)
            except ValueError as err:
                return False
        return True
