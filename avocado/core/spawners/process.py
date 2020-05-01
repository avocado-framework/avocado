import asyncio
import multiprocessing

from .common import BaseSpawner
from .common import SpawnMethod
from .. import nrunner


class ProcessSpawner(BaseSpawner):

    METHODS = [SpawnMethod.STANDALONE_EXECUTABLE, SpawnMethod.PYTHON_CLASS]

    @asyncio.coroutine
    def _collect_task(self, task_handle):
        yield from task_handle.wait()

    @staticmethod
    def is_task_alive(task):
        if getattr(task, 'spawn_handle', None) is None:
            return False
        if hasattr(task.spawn_handle, 'exitcode'):
            return task.spawn_handle.exitcode is None
        elif hasattr(task.spawn_handle, 'returncode'):
            return task.spawn_handle.returncode is None

    @staticmethod
    def _run_task(task):
        for _ in task.run():
            pass

    @asyncio.coroutine
    def spawn_task(self, task):
        # Attempt to spawn the task as a Python class
        # runner_klass = task.runnable.pick_runner_class()
        # runner = runner_klass(task.runnable)
        task.known_runners = nrunner.RUNNERS_REGISTRY_PYTHON_CLASS
        python_class = False
        try:
            python_class = task.runnable.pick_runner_class()
        except ValueError:
            pass

        if python_class:
            proc = multiprocessing.Process(target=self._run_task,
                                           args=(task, ))
            task.spawn_handle = proc
            proc.start()
            return True

        runner = task.runnable.pick_runner_command()
        args = runner[1:] + ['task-run'] + task.get_command_args()
        runner = runner[0]

        # pylint: disable=E1133
        try:
            task.spawn_handle = yield from asyncio.create_subprocess_exec(
                runner,
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
        except (FileNotFoundError, PermissionError):
            return False
        asyncio.ensure_future(self._collect_task(task.spawn_handle))
        return True
