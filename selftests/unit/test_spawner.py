import asyncio
import unittest

from avocado.core import nrunner
from avocado.core.spawners.mock import MockRandomAliveSpawner, MockSpawner
from avocado.core.task.info import TaskInfo
from avocado.plugins.spawners.process import ProcessSpawner


class Process(unittest.TestCase):
    def setUp(self):
        runnable = nrunner.Runnable('noop', 'uri')
        task = nrunner.Task('1', runnable)
        self.task_info = TaskInfo(task)
        self.spawner = ProcessSpawner()

    def test_spawned(self):
        loop = asyncio.get_event_loop()
        spawned = loop.run_until_complete(self.spawner.spawn_task(self.task_info))
        self.assertTrue(spawned)

    def test_never_spawned(self):
        self.assertFalse(self.spawner.is_task_alive(self.task_info))
        self.assertFalse(self.spawner.is_task_alive(self.task_info))


class Mock(Process):

    def setUp(self):
        runnable = nrunner.Runnable('noop', 'uri')
        task = nrunner.Task('1', runnable)
        self.task_info = TaskInfo(task)
        self.spawner = MockSpawner()

    def test_spawned_is_alive(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.spawner.spawn_task(self.task_info))
        self.assertTrue(self.spawner.is_task_alive(self.task_info))
        self.assertFalse(self.spawner.is_task_alive(self.task_info))


class RandomMock(Mock):

    def setUp(self):
        runnable = nrunner.Runnable('noop', 'uri')
        task = nrunner.Task('1', runnable)
        self.task_info = TaskInfo(task)
        self.spawner = MockRandomAliveSpawner()

    def test_spawned_is_alive(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.spawner.spawn_task(self.task_info))
        # The likelihood of the random spawner returning the task is
        # not alive is 1 in 5.  This gives the random code 10000
        # chances of returning False, so it should, famous last words,
        # be pretty safe
        finished = False
        for _ in range(10000):
            if not self.spawner.is_task_alive(self.task_info):
                finished = True
                break
        self.assertTrue(finished)


if __name__ == '__main__':
    unittest.main()
