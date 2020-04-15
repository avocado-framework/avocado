import asyncio
import json
import subprocess
import os

from .common import BaseSpawner
from .common import SpawnMethod


class PodmanSpawner(BaseSpawner):

    METHODS = [SpawnMethod.STANDALONE_EXECUTABLE]
    IMAGE = 'fedora:31'
    PODMAN_BIN = "/usr/bin/podman"

    @staticmethod
    def is_task_alive(task):
        if task.spawn_handle is None:
            return False

        cmd = [PodmanSpawner.PODMAN_BIN, "ps", "--all", "--format={{.State}}",
               "--filter=id=%s" % task.spawn_handle]
        process = subprocess.Popen(cmd,
                                   stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL)
        out, _ = process.communicate()
        # we have to be lenient and allow for the configured state to
        # be considered "alive" because it happens before the
        # container transitions into "running"
        return out in [b'configured\n', b'running\n']

    @asyncio.coroutine
    def spawn_task(self, task):
        entry_point_cmd = '/tmp/avocado-runner'
        entry_point_args = task.get_command_args()
        entry_point_args.insert(0, "task-run")
        entry_point_args.insert(0, entry_point_cmd)
        entry_point = json.dumps(entry_point_args)
        entry_point_arg = "--entrypoint=" + entry_point
        # pylint: disable=E1133
        proc = yield from asyncio.create_subprocess_exec(
            self.PODMAN_BIN, "create",
            "--net=host",
            entry_point_arg,
            self.IMAGE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)

        _ = yield from proc.wait()
        stdout = yield from proc.stdout.read()
        container_id = stdout.decode().strip()

        task.spawn_handle = container_id

        # Currently limited to avocado-runner, we'll expand on that
        # when the runner requirements system is in place
        this_path = os.path.abspath(__file__)
        common_path = os.path.dirname(os.path.dirname(this_path))
        avocado_runner_path = os.path.join(common_path, 'core', 'nrunner.py')
        proc = yield from asyncio.create_subprocess_exec(
            self.PODMAN_BIN,
            "cp",
            avocado_runner_path,
            "%s:%s" % (container_id, entry_point_cmd))
        yield from proc.wait()

        proc = yield from asyncio.create_subprocess_exec(self.PODMAN_BIN,
                                                         "start",
                                                         container_id,
                                                         stdout=asyncio.subprocess.PIPE,
                                                         stderr=asyncio.subprocess.PIPE)
        yield from proc.wait()

    def create_output_dir_for_task(self, task):
        """In this case is a remote folder."""
        local_dir = '/tmp/avocado/tasks/{}/output'.format(task.identifier)
        os.mkdirs(local_dir, exist_ok=True)
        task.set_output_dir(local_dir)
