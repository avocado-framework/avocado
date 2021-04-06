import asyncio

from avocado.core.plugin_interfaces import Spawner
from avocado.core.spawners.common import SpawnerMixin, SpawnMethod


class ProcessSpawner(Spawner, SpawnerMixin):

    description = 'Process based spawner'
    METHODS = [SpawnMethod.STANDALONE_EXECUTABLE]

    async def _collect_task(self, task_handle):
        await task_handle.wait()

    @staticmethod
    def is_task_alive(runtime_task):
        if runtime_task.spawner_handle is None:
            return False
        return runtime_task.spawner_handle.returncode is None

    async def spawn_task(self, runtime_task):
        task = runtime_task.task
        runner = task.runnable.pick_runner_command()
        args = runner[1:] + ['task-run'] + task.get_command_args()
        runner = runner[0]

        # pylint: disable=E1133
        try:
            runtime_task.spawner_handle = await asyncio.create_subprocess_exec(
                runner,
                *args,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL)
        except (FileNotFoundError, PermissionError):
            return False
        asyncio.ensure_future(self._collect_task(runtime_task.spawner_handle))
        return True

    @staticmethod
    async def wait_task(runtime_task):
        await runtime_task.spawner_handle.wait()

    @staticmethod
    async def check_task_requirements(runtime_task):
        """Check the runtime task requirements needed to be able to run"""
        # right now, limit the check to the runner availability.
        if runtime_task.task.runnable.pick_runner_command() is None:
            return False
        return True
