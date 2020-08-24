from unittest import TestCase

from avocado.core.nrunner import Runnable, Task
from avocado.core.task.info import TaskInfo


class Info(TestCase):

    def setUp(self):
        runnable = Runnable('noop', 'noop')
        task = Task('1-noop', runnable)
        self.task_info = TaskInfo(task)

    def test_empty(self):
        self.assertIsNone(self.task_info.status)
        self.assertIsNone(self.task_info.execution_timeout)
        self.assertIsNone(self.task_info.spawner_handle)
        self.assertIsNone(self.task_info.spawning_result)

    def test(self):
        self.task_info.status = 'LOST CONTACT'
        self.assertEqual(self.task_info.task.runnable.kind, 'noop')
        self.assertEqual(self.task_info.task.runnable.uri, 'noop')
        self.assertEqual(self.task_info.status, 'LOST CONTACT')
