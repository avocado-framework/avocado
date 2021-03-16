from unittest import TestCase

from avocado.core.nrunner import Runnable, Task
from avocado.core.task.runtime import RuntimeTask


class Runtime(TestCase):

    def setUp(self):
        runnable = Runnable('noop', 'noop')
        task = Task(runnable, '1-noop')
        self.runtime_task = RuntimeTask(task)

    def test_empty(self):
        self.assertIsNone(self.runtime_task.status)
        self.assertIsNone(self.runtime_task.execution_timeout)
        self.assertIsNone(self.runtime_task.spawner_handle)
        self.assertIsNone(self.runtime_task.spawning_result)

    def test(self):
        self.runtime_task.status = 'LOST CONTACT'
        self.assertEqual(self.runtime_task.task.runnable.kind, 'noop')
        self.assertEqual(self.runtime_task.task.runnable.uri, 'noop')
        self.assertEqual(self.runtime_task.status, 'LOST CONTACT')
