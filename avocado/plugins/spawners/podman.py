import asyncio
import json
import logging
import os
import subprocess

from avocado.core.plugin_interfaces import CLI, DeploymentSpawner, Init
from avocado.core.settings import settings
from avocado.core.spawners.common import SpawnerMixin, SpawnMethod
from avocado.core.version import VERSION
from avocado.utils import distro
from avocado.utils.asset import Asset
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

    _PYTHON_VERSIONS_CACHE = {}

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

    def _fetch_asset(self, url):
        cachedirs = self.config.get('datadir.paths.cache_dirs')
        asset = Asset(url, cache_dirs=cachedirs)
        return asset.fetch()

    def get_eggs_paths(self, py_major, py_minor):
        """Return the basic eggs needed to bootstrap Avocado.

        This will return a tuple with the current location and where this
        should be deployed.
        """
        result = []
        # Setuptools
        # For now let's pin to setuptools 59.2.
        # TODO: Automatically get latest setuptools version.
        eggs = [f"https://github.com/avocado-framework/setuptools/releases/download/v59.2.0/setuptools-59.2.0-py{py_major}.{py_minor}.egg",
                f"https://github.com/avocado-framework/avocado/releases/download/{VERSION}/avocado_framework-{VERSION}-py{py_major}.{py_minor}.egg"]
        for url in eggs:
            path = self._fetch_asset(url)
            to = os.path.join('/tmp/', os.path.basename(path))
            result.append((path, to))
        return result

    @property
    async def python_version(self):
        image = self.config.get('spawner.podman.image')
        if image not in self._PYTHON_VERSIONS_CACHE:
            if not self.podman:
                msg = "Cannot get Python version: self.podman not defined."
                LOG.debug(msg)
                return None, None, None
            result = await self.podman.get_python_version(image)
            self._PYTHON_VERSIONS_CACHE[image] = result
        return self._PYTHON_VERSIONS_CACHE[image]

    async def deploy_artifacts(self):
        pass

    async def deploy_avocado(self, where):
        # Deploy all the eggs to container inside /tmp/
        major, minor, _ = await self.python_version
        eggs = self.get_eggs_paths(major, minor)

        for egg, to in eggs:
            await self.podman.copy_to_container(where, egg, to)

    async def _create_container_for_task(self, runtime_task, env_args,
                                         test_output=None):
        mount_status_server_socket = False
        mounted_status_server_socket = '/tmp/.status_server.sock'
        status_server_uri = runtime_task.task.status_services[0].uri
        if ':' not in status_server_uri:
            # a unix domain socket is being used
            mount_status_server_socket = True
            runtime_task.task.status_services[0].uri = mounted_status_server_socket

        _, _, python_binary = await self.python_version
        entry_point_args = [python_binary,
                            '-m',
                            'avocado.core.nrunner',
                            'task-run']

        task = runtime_task.task
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

        output_opts = ()
        if test_output:
            podman_output = runtime_task.task.runnable.output_dir
            output_opts = ("-v", "%s:%s" % (test_output, podman_output))

        image = self.config.get('spawner.podman.image')

        envs = [f"-e={k}={v}" for k, v in env_args.items()]
        try:
            # pylint: disable=W0201
            _, stdout, _ = await self.podman.execute("create",
                                                     *status_server_opts,
                                                     *output_opts,
                                                     entry_point_arg,
                                                     *envs,
                                                     image)
        except PodmanException as ex:
            msg = f"Could not create podman container: {ex}"
            runtime_task.status = msg
            return False

        return stdout.decode().strip()

    async def spawn_task(self, runtime_task):
        self.create_task_output_dir(runtime_task)
        podman_bin = self.config.get('spawner.podman.bin')
        try:
            # pylint: disable=W0201
            self.podman = Podman(podman_bin)
        except PodmanException as ex:
            runtime_task.status = str(ex)
            return False

        major, minor, _ = await self.python_version
        # Return only the "to" location
        eggs = self.get_eggs_paths(major, minor)
        destination_eggs = ":".join(map(lambda egg: str(egg[1]), eggs))
        env_args = {'PYTHONPATH': destination_eggs}
        output_dir_path = self.task_output_dir(runtime_task)
        container_id = await self._create_container_for_task(runtime_task,
                                                             env_args,
                                                             output_dir_path)

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

    def create_task_output_dir(self, runtime_task):
        output_dir_path = self.task_output_dir(runtime_task)
        output_podman_path = '~/avocado/job-results/spawner/task'

        os.makedirs(output_dir_path, exist_ok=True)
        runtime_task.task.setup_output_dir(output_podman_path)

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
