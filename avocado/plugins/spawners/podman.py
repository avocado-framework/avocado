import asyncio
import json
import os
import subprocess

from avocado.core.plugin_interfaces import CLI, Init, Spawner
from avocado.core.settings import settings
from avocado.core.spawners.common import SpawnerMixin, SpawnMethod
from avocado.core.version import VERSION
from avocado.utils import asset, distro


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

    def _fetch_avocado_egg(self, python_major, python_minor):
        egg_name = 'avocado_framework-%s-py%s.%s.egg' % (VERSION,
                                                         python_major,
                                                         python_minor)
        url = os.path.join('https://cleber.fedorapeople.org/', egg_name)
        cachedirs = self.config.get('datadir.paths.cache_dirs')
        return asset.Asset(name=url, cache_dirs=cachedirs).fetch()

    def _fetch_setuptools_egg(self, python_major, python_minor):
        egg_name = 'setuptools-57.4.0-py%s.%s.egg' % (python_major,
                                                      python_minor)
        url = os.path.join('https://cleber.fedorapeople.org/', egg_name)
        cachedirs = self.config.get('datadir.paths.cache_dirs')
        return asset.Asset(name=url, cache_dirs=cachedirs).fetch()

    @classmethod
    async def _copy_to_container(cls, podman_bin, container_id, src, dst):

        try:
            # pylint: disable=E1133
            proc = await asyncio.create_subprocess_exec(
                podman_bin,
                "cp",
                src,
                "%s:%s" % (container_id, dst))
        except (FileNotFoundError, PermissionError):
            return False

        await proc.wait()
        if proc.returncode != 0:
            return False

    @staticmethod
    async def _get_python_and_version(podman_bin, image):
        binaries = ['/usr/bin/python3', '/usr/bin/python']
        for binary in binaries:
            try:
                ep = ('--entrypoint=["%s", "-c", "import sys; '
                      'print(sys.version_info.major, '
                      'sys.version_info.minor)"]' % binary)
                # pylint: disable=E1133
                proc = await asyncio.create_subprocess_exec(
                    podman_bin, "run", "--rm", ep, image,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE)
            except (FileNotFoundError, PermissionError):
                continue

            await proc.wait()
            if proc.returncode != 0:
                continue

            stdout = await proc.stdout.read()
            (major, minor) = stdout.decode().strip().split(' ')
            return (binary, major, minor)

    async def spawn_task(self, runtime_task):

        podman_bin = self.config.get('spawner.podman.bin')
        if not os.path.exists(podman_bin):
            msg = 'Podman binary "%s" is not available on the system'
            msg %= podman_bin
            runtime_task.status = msg
            return False

        image = self.config.get('spawner.podman.image')
        bin_major_minor = await self._get_python_and_version(podman_bin, image)
        if bin_major_minor is None:
            runtime_task.status = 'Could not find Python version on container image'
            return False
        (python_binary, python_major, python_minor) = bin_major_minor

        avocado_egg_src = self._fetch_avocado_egg(python_major, python_minor)
        avocado_egg_dst = os.path.join('/tmp', os.path.basename(avocado_egg_src))

        setuptools_egg_src = self._fetch_setuptools_egg(python_major, python_minor)
        setuptools_egg_dst = os.path.join('/tmp', os.path.basename(setuptools_egg_src))

        mount_status_server_socket = False
        mounted_status_server_socket = '/tmp/.status_server.sock'
        status_server_uri = runtime_task.task.status_services[0].uri
        if ':' not in status_server_uri:
            # a unix domain socket is being used
            mount_status_server_socket = True
            runtime_task.task.status_services[0].uri = mounted_status_server_socket

        task = runtime_task.task
        entry_point_args = task.get_command_args()
        entry_point_args.insert(0, "task-run")
        entry_point_args.insert(0, "avocado.core.nrunner")
        entry_point_args.insert(0, "-m")
        entry_point_args.insert(0, python_binary)
        entry_point = json.dumps(entry_point_args)
        entry_point_arg = "--entrypoint=" + entry_point

        if mount_status_server_socket:
            status_server_opts = (
                "--privileged",
                "-v", "%s:%s" % (status_server_uri, mounted_status_server_socket)
            )
        else:
            status_server_opts = ("--net=host", )

        try:
            # pylint: disable=E1133
            proc = await asyncio.create_subprocess_exec(
                podman_bin, "create",
                *status_server_opts,
                entry_point_arg,
                '--env=PYTHONPATH=%s:%s' % (avocado_egg_dst,
                                            setuptools_egg_dst),
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
        await self._copy_to_container(podman_bin, container_id,
                                      avocado_egg_src, avocado_egg_dst)
        await self._copy_to_container(podman_bin, container_id,
                                      setuptools_egg_src, setuptools_egg_dst)

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
