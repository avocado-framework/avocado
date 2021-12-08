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
#
# Copyright: 2021 Red Hat Inc.
# Authors : Beraldo Leal <bleal@redhat.com>

"""
This module provides an basic API for interacting with podman.

This module it was designed to be executed in async mode. Remember this when
consuming this API.
"""

import json
import logging
from asyncio import create_subprocess_exec, subprocess
from shutil import which

LOG = logging.getLogger(__name__)


class PodmanException(Exception):
    pass


class Podman:
    def __init__(self, podman_bin=None):
        path = which(podman_bin or 'podman')
        if not path:
            msg = f"Podman binary {podman_bin} is not available on the system."
            raise PodmanException(msg)

        self.podman_bin = path

    async def execute(self, *args):
        """Execute a command and return the returncode, stdout and stderr.

        :param *args: Variable length argument list to be used as argument
                      during execution.
        :rtype: tuple with returncode, stdout and stderr.
        """
        try:
            LOG.debug("Executing %s", args[0])
            proc = await create_subprocess_exec(self.podman_bin,
                                                *args,
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.PIPE)
            stdout, stderr = await proc.communicate()
            LOG.debug("Return code: %s", proc.returncode)
            LOG.debug("Stdout: %s", stdout.decode("utf-8", "replace"))
            LOG.debug("Stderr: %s", stderr.decode("utf-8", "replace"))
        except (FileNotFoundError, PermissionError) as ex:
            # Since this method is also used by other methods, let's
            # log here as well.
            msg = "Could not execute the command."
            LOG.error("%s: %s", msg, str(ex))
            raise PodmanException(msg) from ex

        if proc.returncode != 0:
            msg = f"Could not execute the command: {proc.returncode}:{stderr}."
            LOG.error(msg)
            raise PodmanException(msg)

        return proc.returncode, stdout, stderr

    async def copy_to_container(self, container_id, src, dst):
        """Copy artifacts from src to container:dst.

        This method allows copying the contents of src to the dst. Files will
        be copied from the local machine to the container. The "src" argument
        can be a file or a directory.

        :param str container_id: string with the container identification.
        :param str src: what file or directory you are trying to copy.
        :param str dst: the destination inside the container.
        :rtype: tuple with returncode, stdout and stderr.
        """
        try:
            return await self.execute("cp", src, f"{container_id}:{dst}")
        except PodmanException as ex:
            error = f"Failed copying data to container {container_id}"
            raise PodmanException(error) from ex

    async def get_python_version(self, image):
        """Return the current Python version installed in an image.

        :param str image: Image name. i.e: 'fedora:33'.
        :rtype: tuple with both: major, minor numbers and executable path.
        """

        entrypoint = json.dumps(["/usr/bin/env", "python3", "-c",
                                 ("import sys; print(sys.version_info.major, "
                                  "sys.version_info.minor, sys.executable)")])

        try:
            _, stdout, _ = await self.execute("run",
                                              "--rm",
                                              f"--entrypoint={entrypoint}",
                                              image)
        except PodmanException as ex:
            raise PodmanException("Failed getting Python version.") from ex

        if stdout:
            output = stdout.decode().strip().split()
            return int(output[0]), int(output[1]), output[2]

    async def start(self, container_id):
        """Starts a container and return the returncode, stdout and stderr.

        :param str container_id: Container identification string to start.
        :rtype: tuple with returncode, stdout and stderr.
        """
        try:
            return await self.execute("start", container_id)
        except PodmanException as ex:
            raise PodmanException("Failed to start the container.") from ex
