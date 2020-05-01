import asyncio
import unittest

from avocado.core import nrunner
from avocado.core.spawners.mock import MockSpawner
from avocado.core.scheduler import Scheduler, SchedulerNoPendingTasksException


EVENT_LOOP_SKIP_MSG = ("Test interacts with the asyncio main loop, "
                       "and it's already running")


class Test(unittest.TestCase):

    def setUp(self):
        loop = asyncio.get_event_loop()
        if loop.is_running():
            self.skipTest(EVENT_LOOP_SKIP_MSG)
        runnable = nrunner.Runnable('noop', 'none')
        self.task1 = nrunner.Task('1', runnable)
        self.task2 = nrunner.Task('2', runnable)
        self.tasks = [self.task1, self.task2]
        self.scheduler = Scheduler(self.tasks, spawner=MockSpawner())

    def test_initial_state(self):
        self.assertEqual(self.scheduler.pending_tasks, self.tasks)
        self.assertEqual(self.scheduler.finished_tasks, [])

    def test_spawn_task_not_pending(self):
        task = nrunner.Task('3', nrunner.Runnable('noop', 'none'))
        loop = asyncio.get_event_loop()
        spawn = loop.run_until_complete(self.scheduler.spawn_task(task))
        self.assertTrue(spawn)

    def test_spawn_task(self):
        loop = asyncio.get_event_loop()
        spawn = loop.run_until_complete(self.scheduler.spawn_task(self.task1))
        self.assertTrue(spawn)
        self.assertNotIn(self.task1, self.scheduler.pending_tasks)

    def test_spawn_next_task(self):
        loop = asyncio.get_event_loop()
        spawn = loop.run_until_complete(self.scheduler.spawn_next_task())
        self.assertTrue(spawn)
        self.assertIn(self.task1, self.scheduler.started_tasks)
        self.assertNotIn(self.task1, self.scheduler.pending_tasks)
        self.assertNotIn(self.task1, self.scheduler.start_failed_tasks)
        self.assertIn(self.task2, self.scheduler.pending_tasks)

    def test_is_complete_nothing_spawned(self):
        self.assertFalse(self.scheduler.is_complete())

    def test_is_complete(self):
        loop = asyncio.get_event_loop()
        spawn = loop.run_until_complete(self.scheduler.spawn_next_task())
        self.assertTrue(spawn)
        loop.run_until_complete(self.scheduler.reconcile_task_status())
        spawn = loop.run_until_complete(self.scheduler.spawn_next_task())
        self.assertTrue(spawn)
        loop.run_until_complete(self.scheduler.reconcile_task_status())
        # give a chance for tasks to finish
        loop.run_until_complete(asyncio.sleep(self.scheduler.INTERVAL * 10))
        loop.run_until_complete(self.scheduler.reconcile_task_status())
        self.assertTrue(self.scheduler.is_complete())

    def test_tick(self):
        loop = asyncio.get_event_loop()
        tick_count = 0
        while tick_count < 2:
            # wait for two positive ticks.  In theory they should be the
            # first two attempts given that the tasks are very lightweight
            # but this is safer
            result = loop.run_until_complete(self.scheduler.tick())
            if result:
                tick_count += 1
            # an arbitrary number to avoid this running forever
            self.assertLess(tick_count, 1000,
                            "Too many ticks to spawn two tasks")
        # The next tick will report False since we don't have more tasks
        self.assertFalse(loop.run_until_complete(self.scheduler.tick()))


class TestException(unittest.TestCase):

    def setUp(self):
        loop = asyncio.get_event_loop()
        if loop.is_running():
            self.skipTest(EVENT_LOOP_SKIP_MSG)

    def test(self):
        scheduler = Scheduler([], spawner=MockSpawner())
        loop = asyncio.get_event_loop()
        with self.assertRaises(SchedulerNoPendingTasksException):
            loop.run_until_complete(scheduler.spawn_next_task())


if __name__ == '__main__':
    unittest.main()
