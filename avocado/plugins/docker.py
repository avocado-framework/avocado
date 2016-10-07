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
# Copyright: 2016 Red Hat, Inc.
# Author: Lukas Doktor <ldoktor@redhat.com>
"""Run the job inside a docker container."""

import logging
import os
import socket
import time

import aexpect
from avocado.core.plugin_interfaces import CLI
from avocado.core.remote.runner import RemoteTestRunner
from avocado.utils import process
from avocado.utils.wait import wait_for


LOG = logging.getLogger('avocado.remote')


class DockerRemoter(object):

    """
    Remoter object similar to `avocado.core.remoter` which implements subset
    of the commands on docker container.
    """

    def __init__(self, dkrcmd, image, options, name=None):
        """
        Executes docker container and attaches it.

        :param dkrcmd: The base docker binary (or command)
        :param image: docker image to be used in this instance
        """
        self._dkrcmd = dkrcmd
        self._docker = None

        if name is not None:
            options += " --name %s --hostname %s" % \
                       (name, name + '.' + socket.gethostname())

        run_cmd = "%s run -t -i -d %s '%s' bash" % (self._dkrcmd, options, image)
        self._docker_id = (process.system_output(run_cmd, None).splitlines()[-1]
                           .strip())
        self._docker = aexpect.ShellSession("%s attach %s"
                                            % (self._dkrcmd, self._docker_id))
        # Disable echo to avoid duplicate output
        self._docker.cmd("stty -echo")

    def get_cid(self):
        """ Return this remoter's container ID """
        return self._docker_id

    def makedir(self, remote_path):
        """
        Create a directory on the container

        :warning: No other process must be running on foreground
        :param remote_path: the remote path to create.
        """
        self._docker.cmd("mkdir -p %s" % remote_path)

    def send_files(self, local_path, remote_path):
        """
        Send files to the container
        """
        process.run("%s cp %s %s:%s" % (self._dkrcmd, local_path,
                                        self._docker_id, remote_path))

    def receive_files(self, local_path, remote_path):
        """
        Receive files from the container
        """
        process.run("%s cp %s:%s %s" % (self._dkrcmd, self._docker_id,
                                        remote_path, local_path))

    def run(self, command, ignore_status=False, quiet=None, timeout=60):
        """
        Run command inside the container
        """
        def print_func(*args, **kwargs):    # pylint: disable=W0613
            """ Accept anything and does nothing """
            pass
        if timeout is None:
            timeout = 31536000  # aexpect does not support None, use one year
        start = time.time()
        if quiet is not False:
            print_func = LOG.debug
        status, output = self._docker.cmd_status_output(command,
                                                        timeout=timeout,
                                                        print_func=print_func)
        result = process.CmdResult(command, output, '', status,
                                   time.time() - start)
        if status and not ignore_status:
            raise process.CmdError(command, result, "in container %s"
                                   % self._docker_id)
        return result

    def cleanup(self):
        """
        Stop the container and remove it
        """
        process.system("%s stop -t 1 %s" % (self._dkrcmd, self._docker_id))
        process.system("%s rm %s" % (self._dkrcmd, self._docker_id))

    def close(self):
        """
        Safely postprocess the container

        :note: It won't remove the container, you need to do it manually
        """
        if self._docker:
            self._docker.sendline("exit")
            # Leave the process up to 10s to finish, then nuke it
            wait_for(lambda: not self._docker.is_alive(), 10)
            self._docker.close()


class DockerTestRunner(RemoteTestRunner):

    """
    Test runner which runs the job inside a docker container
    """

    remote_test_dir = "/avocado_remote_test_dir"  # Absolute path only

    def __init__(self, job, test_result):
        super(DockerTestRunner, self).__init__(job, test_result)
        self.remote = None      # Will be set in `setup`

    def setup(self):
        dkrcmd = self.job.args.docker_cmd
        dkr_opt = self.job.args.docker_options
        dkr_name = os.path.basename(self.job.logdir) + '.' + 'avocado'
        self.remote = DockerRemoter(dkrcmd, self.job.args.docker, dkr_opt, dkr_name)
        # We need to create the base dir, otherwise docker creates it as root
        self.remote.makedir(self.remote_test_dir)
        self.job.log.info("DOCKER     : Container id '%s'"
                          % self.remote.get_cid())
        self.job.log.debug("DOCKER     : Container name '%s'" % dkr_name)
        self.job.args.remote_no_copy = self.job.args.docker_no_copy

    def tear_down(self):
        try:
            if self.remote:
                self.remote.close()
                if not self.job.args.docker_no_cleanup:
                    self.remote.cleanup()
        except Exception as details:
            self.job.log.warn("DOCKER     : Fail to cleanup: %s" % details)


class Docker(CLI):

    """
    Run the job inside a docker container
    """

    name = 'docker'
    description = "Run tests inside docker container"

    def configure(self, parser):
        run_subcommand_parser = parser.subcommands.choices.get('run', None)
        if run_subcommand_parser is None:
            return

        msg = 'test execution inside docker container'
        cmd_parser = run_subcommand_parser.add_argument_group(msg)
        cmd_parser.add_argument("--docker", help="Name of the docker image to"
                                "run tests on.", metavar="IMAGE")
        cmd_parser.add_argument("--docker-cmd", default="docker",
                                help="Override the docker command, eg. 'sudo "
                                "docker' or other base docker options like "
                                "hypervisor. Default: '%(default)s'",
                                metavar="CMD")
        cmd_parser.add_argument("--docker-options", default="",
                                help="Extra options for docker run cmd."
                                " (see: man docker-run)", metavar="OPT")

        cmd_parser.add_argument("--docker-no-copy", action="store_true",
                                help="Assume tests are already in the "
                                "container")
        cmd_parser.add_argument("--docker-no-cleanup", action="store_true",
                                help="Preserve container after test")

    def run(self, args):
        if getattr(args, "docker", None):
            args.test_runner = DockerTestRunner
