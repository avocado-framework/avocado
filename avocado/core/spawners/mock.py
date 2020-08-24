import asyncio
import random

from ...core.plugin_interfaces import Spawner
from .common import SpawnMethod


class MockSpawner(Spawner):
    """A mocking spawner that performs no real operation.

    Tasks asked to be spawned by this spawner will initially reported to
    be alive, and on the next check, will report not being alive.
    """

    METHODS = [SpawnMethod.PYTHON_CLASS, SpawnMethod.STANDALONE_EXECUTABLE]

    def __init__(self):
        self._known_tasks = {}

    def is_task_alive(self, task_info):
        alive = self._known_tasks.get(task_info, None)
        # task was never spawned
        if alive is None:
            return False
        # task was spawned and should signal it's alive for the first time
        if alive:
            self._known_tasks[task_info] = False
            return True
        else:
            # signal it's *not* alive after first check
            return False

    async def spawn_task(self, task_info):
        self._known_tasks[task_info] = True
        return True

    async def wait_task(self, task_info):
        while True:
            if self.is_task_alive(task_info):
                return
            await asyncio.sleep(0.1)

    @staticmethod
    async def check_task_requirements(task_info):
        return True


class MockRandomAliveSpawner(MockSpawner):
    """A mocking spawner that simulates randomness about tasks being alive."""

    def is_task_alive(self, task_info):
        alive = self._known_tasks.get(task_info, None)
        # task was never spawned
        if alive is None:
            return False
        return random.choice([True, True, True, True, False])
