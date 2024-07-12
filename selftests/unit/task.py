import unittest

from avocado.core.nrunner.runnable import Runnable
from avocado.core.nrunner.task import Task


class TaskTest(unittest.TestCase):
    def test_default_category(self):
        runnable = Runnable("noop", "noop_uri")
        task = Task(runnable, "task_id")
        self.assertEqual(task.category, "test")

    def test_set_category(self):
        runnable = Runnable("noop", "noop_uri")
        task = Task(runnable, "task_id", category="new_category")
        self.assertEqual(task.category, "new_category")
