import asyncio

from .common import BaseSpawner, SpawnMethod


class ProcessSpawner(BaseSpawner):

    METHODS = [SpawnMethod.STANDALONE_EXECUTABLE]

    async def _collect_task(self, task_handle):
        await task_handle.wait()

    @staticmethod
    def is_task_alive(task):
        if getattr(task, 'spawn_handle', None) is None:
            return False
        return task.spawn_handle.returncode is None

    async def check_requirements(self, task):
        """Checks if the requirements described within a task are available."""
        if not task.runnable.requirements:
            return True

        for requirements in task.runnable.requirements:
            for (req_type, req_value) in requirements.items():
                # The fact that this is avocado code means this
                # requirement is fulfilled
                if req_type == 'core' and req_value == 'avocado':
                    continue
        return True

    async def spawn_task(self, task):
        runner = task.runnable.pick_runner_command()
        args = runner[1:] + ['task-run'] + task.get_command_args()
        runner = runner[0]

        # pylint: disable=E1133
        try:
            task.spawn_handle = await asyncio.create_subprocess_exec(
                runner,
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
        except (FileNotFoundError, PermissionError):
            return False
        asyncio.ensure_future(self._collect_task(task.spawn_handle))
        return True
