import asyncio
import os
import sys

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
        self.create_task_output_dir(runtime_task)
        task = runtime_task.task
        runner = task.runnable.pick_runner_command()
        args = runner[1:] + ['task-run'] + task.get_command_args()
        runner = runner[0]
        # When running Avocado Python modules, the interpreter on the new
        # process needs to know where Avocado can be found.
        env = os.environ.copy()
        env['PYTHONPATH'] = ':'.join(p for p in sys.path)

        # pylint: disable=E1133
        try:
            runtime_task.spawner_handle = await asyncio.create_subprocess_exec(
                runner,
                *args,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
                env=env)
        except (FileNotFoundError, PermissionError):
            return False
        asyncio.ensure_future(self._collect_task(runtime_task.spawner_handle))
        return True

    def create_task_output_dir(self, runtime_task):
        output_dir_path = self.task_output_dir(runtime_task)
        os.makedirs(output_dir_path, exist_ok=True)
        runtime_task.task.setup_output_dir(output_dir_path)

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
