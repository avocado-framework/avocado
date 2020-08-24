import asyncio
import json
import os
import subprocess

from avocado.core.plugin_interfaces import Spawner
from avocado.core.spawners.common import SpawnerMixin, SpawnMethod


class PodmanSpawner(Spawner, SpawnerMixin):

    description = 'Podman (container) based spawner'
    METHODS = [SpawnMethod.STANDALONE_EXECUTABLE]
    IMAGE = 'fedora:31'
    PODMAN_BIN = "/usr/bin/podman"

    @staticmethod
    def is_task_alive(runtime_task):
        if runtime_task.spawner_handle is None:
            return False

        cmd = [PodmanSpawner.PODMAN_BIN, "ps", "--all", "--format={{.State}}",
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
        try:
            # pylint: disable=E1133
            proc = await asyncio.create_subprocess_exec(
                self.PODMAN_BIN, "create",
                "--net=host",
                entry_point_arg,
                self.IMAGE,
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
                self.PODMAN_BIN,
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
                self.PODMAN_BIN,
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
