import unittest

from avocado.core.nrunner.runnable import Runnable
from avocado.core.nrunner.task import Task
from avocado.core.spawners.mock import MockRandomAliveSpawner, MockSpawner
from avocado.core.task.runtime import RuntimeTask
from avocado.plugins.spawners.process import ProcessSpawner


class Process(unittest.TestCase):
    def setUp(self):
        runnable = Runnable('noop', 'uri')
        task = Task(runnable, '1')
        self.runtime_task = RuntimeTask(task)
        self.spawner = ProcessSpawner()

    async def test_spawned(self):
        spawned = await self.spawner.spawn_task(self.runtime_task)
        self.assertTrue(spawned)

    def test_never_spawned(self):
        self.assertFalse(self.spawner.is_task_alive(self.runtime_task))
        self.assertFalse(self.spawner.is_task_alive(self.runtime_task))


class Mock(Process):

    def setUp(self):
        runnable = Runnable('noop', 'uri')
        task = Task(runnable, '1')
        self.runtime_task = RuntimeTask(task)
        self.spawner = MockSpawner()

    async def test_spawned_is_alive(self):
        await self.spawner.spawn_task(self.runtime_task)
        self.assertTrue(self.spawner.is_task_alive(self.runtime_task))
        self.assertFalse(self.spawner.is_task_alive(self.runtime_task))


class RandomMock(Mock):

    def setUp(self):
        runnable = Runnable('noop', 'uri')
        task = Task(runnable, '1')
        self.runtime_task = RuntimeTask(task)
        self.spawner = MockRandomAliveSpawner()

    async def test_spawned_is_alive(self):
        await self.spawner.spawn_task(self.runtime_task)
        # The likelihood of the random spawner returning the task is
        # not alive is 1 in 5.  This gives the random code 10000
        # chances of returning False, so it should, famous last words,
        # be pretty safe
        finished = False
        for _ in range(10000):
            if not self.spawner.is_task_alive(self.runtime_task):
                finished = True
                break
        self.assertTrue(finished)


if __name__ == '__main__':
    unittest.main()
