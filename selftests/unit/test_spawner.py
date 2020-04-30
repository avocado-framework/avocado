import asyncio
import unittest

from avocado.core import nrunner
from avocado.core.spawners.process import ProcessSpawner
from avocado.core.spawners.mock import MockSpawner
from avocado.core.spawners.mock import MockRandomAliveSpawner


class Process(unittest.TestCase):
    def setUp(self):
        runnable = nrunner.Runnable('noop', 'uri')
        self.task = nrunner.Task('1', runnable)
        self.spawner = ProcessSpawner()

    def test_spawned(self):
        loop = asyncio.get_event_loop()
        spawned = loop.run_until_complete(self.spawner.spawn_task(self.task))
        self.assertTrue(spawned)

    def test_never_spawned(self):
        self.assertFalse(self.spawner.is_task_alive(self.task))
        self.assertFalse(self.spawner.is_task_alive(self.task))


class Mock(Process):

    def setUp(self):
        runnable = nrunner.Runnable('noop', 'uri')
        self.task = nrunner.Task('1', runnable)
        self.spawner = MockSpawner()

    def test_spawned_is_alive(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.spawner.spawn_task(self.task))
        self.assertTrue(self.spawner.is_task_alive(self.task))
        self.assertFalse(self.spawner.is_task_alive(self.task))


class RandomMock(Mock):

    def setUp(self):
        runnable = nrunner.Runnable('noop', 'uri')
        self.task = nrunner.Task('1', runnable)
        self.spawner = MockRandomAliveSpawner()

    def test_spawned_is_alive(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.spawner.spawn_task(self.task))
        # The likelihood of the random spawner returning the task is
        # not alive is 1 in 5.  This gives the random code 10000
        # chances of returning False, so it should, famous last words,
        # be pretty safe
        finished = False
        for _ in range(10000):
            if not self.spawner.is_task_alive(self.task):
                finished = True
                break
        self.assertTrue(finished)


if __name__ == '__main__':
    unittest.main()
