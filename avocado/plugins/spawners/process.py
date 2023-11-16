import asyncio
import os
import socket

from avocado.core.dependencies.requirements import cache
from avocado.core.plugin_interfaces import Spawner
from avocado.core.spawners.common import SpawnerMixin, SpawnMethod
from avocado.core.teststatus import STATUSES_NOT_OK
from avocado.core.utils.eggenv import get_python_path_env_if_egg

ENVIRONMENT_TYPE = "local"
ENVIRONMENT = socket.gethostname()


class ProcessSpawnerHandle:
    def __init__(self, process):
        self.process = process
        self._wait_task = None

    def create_wait_task(self):
        if self._wait_task is None:
            loop = asyncio.get_event_loop()
            self._wait_task = loop.create_task(self.process.wait())

    @property
    def wait_task(self):
        self.create_wait_task()
        return self._wait_task


class ProcessSpawner(Spawner, SpawnerMixin):

    description = "Process based spawner"
    METHODS = [SpawnMethod.STANDALONE_EXECUTABLE]

    @staticmethod
    def is_task_alive(runtime_task):
        if runtime_task.spawner_handle is None:
            return False
        if runtime_task.spawner_handle.wait_task.done():
            return False
        return True

    async def spawn_task(self, runtime_task):
        self.create_task_output_dir(runtime_task)
        task = runtime_task.task
        runner = task.runnable.runner_command()
        args = runner[1:] + ["task-run"] + task.get_command_args()
        runner = runner[0]

        # pylint: disable=E1133
        try:
            proc = await asyncio.create_subprocess_exec(
                runner,
                *args,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
                env=get_python_path_env_if_egg(),
            )
        except (FileNotFoundError, PermissionError):
            return False
        runtime_task.spawner_handle = ProcessSpawnerHandle(proc)
        return True

    def create_task_output_dir(self, runtime_task):
        output_dir_path = self.task_output_dir(runtime_task)
        os.makedirs(output_dir_path, exist_ok=True)
        with open(os.path.join(output_dir_path, "debug.log"), mode="ba"):
            pass
        runtime_task.task.setup_output_dir(output_dir_path)

    @staticmethod
    async def wait_task(runtime_task):  # pylint: disable=W0221
        await runtime_task.spawner_handle.wait_task

    async def terminate_task(self, runtime_task):
        try:
            runtime_task.spawner_handle.process.terminate()
        except ProcessLookupError:
            return True
        soft_interval = self.config.get(
            "runner.task.interval.from_soft_to_hard_termination"
        )
        returncode = None
        try:
            returncode = await asyncio.wait_for(
                runtime_task.spawner_handle.process.wait(), soft_interval
            )
        except asyncio.TimeoutError:
            try:
                runtime_task.spawner_handle.process.kill()
            except ProcessLookupError:
                return True
            hard_interval = self.config.get(
                "runner.task.interval.from_hard_termination_to_verification"
            )
            try:
                returncode = await asyncio.wait_for(
                    runtime_task.spawner_handle.process.wait(), hard_interval
                )
            except asyncio.TimeoutError:
                pass
        return returncode is not None

    @staticmethod
    async def check_task_requirements(runtime_task):
        """Check the runtime task requirements needed to be able to run"""
        # right now, limit the check to the runner availability.
        if runtime_task.task.runnable.runner_command() is None:
            return False
        return True

    @staticmethod
    async def update_requirement_cache(runtime_task, result):
        kind = runtime_task.task.runnable.kind
        name = runtime_task.task.runnable.kwargs.get("name")
        cache.set_requirement(ENVIRONMENT_TYPE, ENVIRONMENT, kind, name)
        if result in STATUSES_NOT_OK:
            cache.delete_requirement(ENVIRONMENT_TYPE, ENVIRONMENT, kind, name)
            return
        cache.update_requirement_status(ENVIRONMENT_TYPE, ENVIRONMENT, kind, name, True)

    @staticmethod
    async def is_requirement_in_cache(runtime_task):
        kind = runtime_task.task.runnable.kind
        name = runtime_task.task.runnable.kwargs.get("name")
        return cache.is_requirement_in_cache(ENVIRONMENT_TYPE, ENVIRONMENT, kind, name)

    @staticmethod
    async def save_requirement_in_cache(runtime_task):
        kind = runtime_task.task.runnable.kind
        name = runtime_task.task.runnable.kwargs.get("name")
        cache.set_requirement(ENVIRONMENT_TYPE, ENVIRONMENT, kind, name, False)
