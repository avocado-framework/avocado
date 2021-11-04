import asyncio
import json
import logging
import os
import subprocess

from avocado.core.plugin_interfaces import CLI, DeploymentSpawner, Init
from avocado.core.settings import settings
from avocado.core.spawners.common import SpawnerMixin, SpawnMethod
from avocado.utils import distro
from avocado.utils.podman import Podman, PodmanException

LOG = logging.getLogger(__name__)


ENTRY_POINT_CMD = "/tmp/avocado-runner"


class PodmanSpawnerInit(Init):

    description = 'Podman (container) based spawner initialization'

    def initialize(self):
        section = 'spawner.podman'

        help_msg = 'Path to the podman binary'
        settings.register_option(
            section=section,
            key='bin',
            help_msg=help_msg,
            default='/usr/bin/podman')

        this_distro = distro.detect()
        if this_distro != distro.UNKNOWN_DISTRO:
            default_distro = '{0}:{1}'.format(this_distro.name,
                                              this_distro.version)
        else:
            default_distro = 'fedora:latest'
        help_msg = ('Image name to use when creating the container. '
                    'The first default choice is a container image '
                    'matching the current OS. If unable to detect, '
                    'default becomes the latest Fedora release. Default '
                    'on this system: {0}'.format(default_distro))
        settings.register_option(
            section=section,
            key='image',
            help_msg=help_msg,
            default=default_distro)


class PodmanCLI(CLI):

    name = 'podman'
    description = 'podman spawner command line options for "run"'

    def configure(self, parser):
        super(PodmanCLI, self).configure(parser)
        parser = parser.subcommands.choices.get('run', None)
        if parser is None:
            return

        parser = parser.add_argument_group('podman spawner specific options')
        settings.add_argparser_to_option(namespace='spawner.podman.bin',
                                         parser=parser,
                                         long_arg='--spawner-podman-bin',
                                         metavar='PODMAN_BIN')

        settings.add_argparser_to_option(namespace='spawner.podman.image',
                                         parser=parser,
                                         long_arg='--spawner-podman-image',
                                         metavar='CONTAINER_IMAGE')

    def run(self, config):
        pass


class PodmanSpawner(DeploymentSpawner, SpawnerMixin):

    description = 'Podman (container) based spawner'
    METHODS = [SpawnMethod.STANDALONE_EXECUTABLE]

    def is_task_alive(self, runtime_task):
        if runtime_task.spawner_handle is None:
            return False
        podman_bin = self.config.get('spawner.podman.bin')
        cmd = [podman_bin, "ps", "--all", "--format={{.State}}",
               "--filter=id=%s" % runtime_task.spawner_handle]
        process = subprocess.Popen(cmd,
                                   stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL)
        out, _ = process.communicate()
        # FIXME: check how podman 2.x is reporting valid "OK" states
        return out.startswith(b'Up ')

    async def deploy_artifacts(self):
        pass

    async def deploy_avocado(self, where):
        # Currently limited to avocado-runner, we'll expand on that
        # when the runner requirements system is in place
        this_path = os.path.abspath(__file__)
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(this_path)))
        avocado_runner_path = os.path.join(base_path, 'core', 'nrunner.py')
        try:
            # pylint: disable=W0201
            await self.podman.execute("cp",
                                      avocado_runner_path,
                                      "%s:%s" % (where,
                                                 ENTRY_POINT_CMD))
        except PodmanException:
            return False

    async def _create_container_for_task(self, runtime_task):
        mount_status_server_socket = False
        mounted_status_server_socket = '/tmp/.status_server.sock'
        status_server_uri = runtime_task.task.status_services[0].uri
        if ':' not in status_server_uri:
            # a unix domain socket is being used
            mount_status_server_socket = True
            runtime_task.task.status_services[0].uri = mounted_status_server_socket

        task = runtime_task.task
        entry_point_args = [ENTRY_POINT_CMD, "task-run"]
        entry_point_args.extend(task.get_command_args())
        entry_point = json.dumps(entry_point_args)
        entry_point_arg = "--entrypoint=" + entry_point

        if mount_status_server_socket:
            status_server_opts = (
                "--privileged",
                "-v", "%s:%s" % (status_server_uri,
                                 mounted_status_server_socket)
            )
        else:
            status_server_opts = ("--net=host", )

        image = self.config.get('spawner.podman.image')

        try:
            # pylint: disable=W0201
            _, stdout, _ = await self.podman.execute("create",
                                                     *status_server_opts,
                                                     entry_point_arg, image)
        except PodmanException as ex:
            msg = f"Could not create podman container: {ex}"
            runtime_task.status = msg
            return False

        return stdout.decode().strip()

    async def spawn_task(self, runtime_task):

        podman_bin = self.config.get('spawner.podman.bin')
        try:
            # pylint: disable=W0201
            self.podman = Podman(podman_bin)
        except PodmanException as ex:
            runtime_task.status = str(ex)
            return False

        container_id = await self._create_container_for_task(runtime_task)

        runtime_task.spawner_handle = container_id

        await self.deploy_avocado(container_id)

        try:
            # pylint: disable=W0201
            returncode, _, _ = await self.podman.start(container_id)
        except PodmanException as ex:
            msg = f"Could not start container: {ex}"
            runtime_task.status = msg
            LOG.error(msg)
            return False

        return returncode == 0

    async def wait_task(self, runtime_task):
        while True:
            if not self.is_task_alive(runtime_task):
                return
            await asyncio.sleep(0.1)

    @staticmethod
    async def check_task_requirements(runtime_task):
        """Check the runtime task requirements needed to be able to run"""
        # right now, limit the check to the runner availability.
        if runtime_task.task.runnable.pick_runner_command() is None:
            return False
        return True
