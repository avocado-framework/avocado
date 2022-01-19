import os
from unittest import TestCase

from avocado.core.nrunner import Runnable, Task
from avocado.core.suite import TestSuite
from avocado.core.task.runtime import RuntimeGraph, RuntimeTask
from avocado.utils import script
from selftests.utils import TestCaseTmpDir

SINGLE_REQUIREMENT = '''#!/usr/bin/env python3

from avocado import Test


class SuccessTest(Test):

    def test_a(self):
       pass
    def test_b(self):
        """
        :avocado: requirement={"type": "package", "name": "hello"}
        """
    def test_c(self):
        """
        :avocado: requirement={"type": "package", "name": "hello"}
        """
'''

MULTIPLE_REQUIREMENT = '''#!/usr/bin/env python3

from avocado import Test


class FailTest(Test):

    def test_a(self):
        """
        :avocado: requirement={"type": "package", "name": "hello"}
        """
    def test_b(self):
        pass
    def test_c(self):
        """
        :avocado: requirement={"type": "package", "name": "hello"}
        :avocado: requirement={"type": "package", "name": "-foo-bar-"}
        """
'''


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


class DependencyGraph(TestCaseTmpDir):

    def test_one_requirement(self):
        with script.Script(os.path.join(self.tmpdir.name,
                                        'test_single_requirment.py'),
                           SINGLE_REQUIREMENT) as test:
            config = {'resolver.references': [test.path]}
            suite = TestSuite.from_config(config=config)
            graph = RuntimeGraph(suite, 1, "")
            runtime_tests = graph.get_all_runtime_tasks()
            self.assertTrue(
                runtime_tests[0].task.identifier.name.endswith("test_a"))
            self.assertTrue(
                runtime_tests[1].task.identifier.name.endswith("hello"))
            self.assertTrue(
                runtime_tests[2].task.identifier.name.endswith("test_b"))
            self.assertTrue(
                runtime_tests[3].task.identifier.name.endswith("test_c"))

    def test_multiple_requirement(self):
        with script.Script(os.path.join(self.tmpdir.name,
                                        'test_multiple_requirement.py'),
                           MULTIPLE_REQUIREMENT) as test:
            config = {'resolver.references': [test.path]}
            suite = TestSuite.from_config(config=config)
            graph = RuntimeGraph(suite, 1, "")
            runtime_tests = graph.get_all_runtime_tasks()
            self.assertTrue(
                runtime_tests[0].task.identifier.name.endswith("hello"))
            self.assertTrue(
                runtime_tests[1].task.identifier.name.endswith("test_a"))
            self.assertTrue(
                runtime_tests[2].task.identifier.name.endswith("test_b"))
            self.assertTrue(
                runtime_tests[3].task.identifier.name.endswith("-foo-bar-"))
            self.assertTrue(
                runtime_tests[4].task.identifier.name.endswith("test_c"))
