import asyncio

from avocado.core.plugin_interfaces import Spawner
from avocado.core.spawners.common import SpawnerMixin, SpawnMethod


class ProcessSpawner(Spawner, SpawnerMixin):

    description = 'Process based spawner'
    METHODS = [SpawnMethod.STANDALONE_EXECUTABLE]

    async def _collect_task(self, task_handle):
        await task_handle.wait()

    @staticmethod
    def is_task_alive(task_info):
        if task_info.spawner_handle is None:
            return False
        return task_info.spawner_handle.returncode is None

    async def spawn_task(self, task_info):
        task = task_info.task
        runner = task.runnable.pick_runner_command()
        args = runner[1:] + ['task-run'] + task.get_command_args()
        runner = runner[0]

        # pylint: disable=E1133
        try:
            task_info.spawner_handle = await asyncio.create_subprocess_exec(
                runner,
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
        except (FileNotFoundError, PermissionError):
            return False
        asyncio.ensure_future(self._collect_task(task_info.spawner_handle))
        return True

    @staticmethod
    async def wait_task(task_info):
        await task_info.spawner_handle.wait()
