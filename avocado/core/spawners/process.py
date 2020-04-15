import asyncio

from .common import BaseSpawner
from .common import SpawnMethod


class ProcessSpawner(BaseSpawner):

    METHODS = [SpawnMethod.STANDALONE_EXECUTABLE]

    @staticmethod
    def is_task_alive(task):
        return task.spawn_handle.returncode is None

    @asyncio.coroutine
    def spawn_task(self, task):
        runner = task.runnable.pick_runner_command()
        args = runner[1:] + ['task-run'] + task.get_command_args()
        runner = runner[0]

        #pylint: disable=E1133
        task.spawn_handle = yield from asyncio.create_subprocess_exec(
            runner,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
