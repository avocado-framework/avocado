import asyncio
import json
import os
import re
import subprocess

from avocado.core.plugin_interfaces import Init, Spawner
from avocado.core.requirements import cache
from avocado.core.settings import settings
from avocado.core.spawners.common import SpawnerMixin, SpawnMethod


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

        help_msg = 'Image name to use when creating the container'
        settings.register_option(
            section=section,
            key='image',
            help_msg=help_msg,
            default='fedora:31')


class PodmanSpawner(Spawner, SpawnerMixin):

    description = 'Podman (container) based spawner'
    METHODS = [SpawnMethod.STANDALONE_EXECUTABLE]

    @staticmethod
    def is_task_alive(runtime_task):
        if runtime_task.spawner_handle is None:
            return False
        podman_bin = settings.as_dict().get('spawner.podman.bin')
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
        task = runtime_task.task
        entry_point_cmd = '/tmp/avocado-runner'
        entry_point_args = task.get_command_args()
        entry_point_args.insert(0, "task-run")
        entry_point_args.insert(0, entry_point_cmd)
        entry_point = json.dumps(entry_point_args)
        entry_point_arg = "--entrypoint=" + entry_point

        podman_bin = self.config.get('spawner.podman.bin')

        if not os.path.exists(podman_bin):
            msg = 'Podman binary "%s" is not available on the system'
            msg %= podman_bin
            runtime_task.status = msg
            return False

        image = self.config.get('spawner.podman.image')
        try:
            # pylint: disable=E1133
            proc = await asyncio.create_subprocess_exec(
                podman_bin, "create",
                "--net=host",
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

    @staticmethod
    async def wait_task(runtime_task):
        while True:
            if not PodmanSpawner.is_task_alive(runtime_task):
                return
            await asyncio.sleep(0.1)

    @staticmethod
    async def _check_requirement_core_avocado():
        env_type = 'podman'
        env = settings.as_dict().get('spawner.podman.image')
        req_type = 'core'
        req = 'avocado'

        on_cache = cache.get_requirement(env_type, env,
                                         req_type, req)
        if on_cache:
            return True

        podman_bin = settings.as_dict().get('spawner.podman.bin')
        try:
            # pylint: disable=E1133
            proc = await asyncio.create_subprocess_exec(
                podman_bin, "run", env,
                "avocado", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
        except (FileNotFoundError, PermissionError):
            return False

        await proc.wait()
        if proc.returncode != 0:
            return False

        stdout = await proc.stdout.read()
        if re.match(rb'^Avocado (\d+)\.(\d+)\r?$', stdout):
            cache.set_requirement(env_type, env,
                                  req_type, req)
            return True
        return False

    @staticmethod
    async def check_task_requirements(runtime_task):
        runnable_requirements = runtime_task.task.runnable.requirements
        if not runnable_requirements:
            return True
        for requirements in runnable_requirements:
            for (req_type, req_value) in requirements.items():
                # This is currently limited to one requirement type as a PoC
                if req_type == 'core' and req_value == 'avocado':
                    avocado_capable = await PodmanSpawner._check_requirement_core_avocado()
                    return avocado_capable
                else:
                    # current implementation can not check any other type of
                    # requirement at this moment so fail
                    return False
        return True
