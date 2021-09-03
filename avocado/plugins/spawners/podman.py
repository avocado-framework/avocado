import asyncio
import json
import os
import subprocess

from avocado.core.plugin_interfaces import CLI, Init, Spawner
from avocado.core.settings import settings
from avocado.core.spawners.common import SpawnerMixin, SpawnMethod
from avocado.utils import distro


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


class PodmanSpawner(Spawner, SpawnerMixin):

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

    async def spawn_task(self, runtime_task):

        podman_bin = self.config.get('spawner.podman.bin')
        if not os.path.exists(podman_bin):
            msg = 'Podman binary "%s" is not available on the system'
            msg %= podman_bin
            runtime_task.status = msg
            return False

        mount_status_server_socket = False
        mounted_status_server_socket = '/tmp/.status_server.sock'
        status_server_uri = runtime_task.task.status_services[0].uri
        if ':' not in status_server_uri:
            # a unix domain socket is being used
            mount_status_server_socket = True
            runtime_task.task.status_services[0].uri = mounted_status_server_socket

        task = runtime_task.task
        entry_point_cmd = '/tmp/avocado-runner'
        entry_point_args = task.get_command_args()
        entry_point_args.insert(0, "task-run")
        entry_point_args.insert(0, entry_point_cmd)
        entry_point = json.dumps(entry_point_args)
        entry_point_arg = "--entrypoint=" + entry_point

        if mount_status_server_socket:
            status_server_opts = (
                "--privileged",
                "-v", "%s:%s" % (status_server_uri, mounted_status_server_socket)
            )
        else:
            status_server_opts = ("--net=host", )

        image = self.config.get('spawner.podman.image')
        try:
            # pylint: disable=E1133
            proc = await asyncio.create_subprocess_exec(
                podman_bin, "create",
                *status_server_opts,
                entry_point_arg,
                image,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
        except (FileNotFoundError, PermissionError):
            return False

        await proc.wait()
        if proc.returncode != 0:
            return False

        stdout = await proc.stdout.read()
        container_id = stdout.decode().strip()

        runtime_task.spawner_handle = container_id

        # Currently limited to avocado-runner, we'll expand on that
        # when the runner requirements system is in place
        this_path = os.path.abspath(__file__)
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(this_path)))
        avocado_runner_path = os.path.join(base_path, 'core', 'nrunner.py')
        try:
            # pylint: disable=E1133
            proc = await asyncio.create_subprocess_exec(
                podman_bin,
                "cp",
                avocado_runner_path,
                "%s:%s" % (container_id, entry_point_cmd))
        except (FileNotFoundError, PermissionError):
            return False

        await proc.wait()
        if proc.returncode != 0:
            return False

        try:
            # pylint: disable=E1133
            proc = await asyncio.create_subprocess_exec(
                podman_bin,
                "start",
                container_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
        except (FileNotFoundError, PermissionError):
            return False

        await proc.wait()
        return proc.returncode == 0

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
