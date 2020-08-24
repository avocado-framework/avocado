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

    def is_task_alive(self, runtime_task):
        alive = self._known_tasks.get(runtime_task, None)
        # task was never spawned
        if alive is None:
            return False
        # task was spawned and should signal it's alive for the first time
        if alive:
            self._known_tasks[runtime_task] = False
            return True
        else:
            # signal it's *not* alive after first check
            return False

    async def spawn_task(self, runtime_task):
        self._known_tasks[runtime_task] = True
        return True

    async def wait_task(self, runtime_task):
        while True:
            if self.is_task_alive(runtime_task):
                return
            await asyncio.sleep(0.1)

    @staticmethod
    async def check_task_requirements(runtime_task):
        return True


class MockRandomAliveSpawner(MockSpawner):
    """A mocking spawner that simulates randomness about tasks being alive."""

    def is_task_alive(self, runtime_task):
        alive = self._known_tasks.get(runtime_task, None)
        # task was never spawned
        if alive is None:
            return False
        return random.choice([True, True, True, True, False])
