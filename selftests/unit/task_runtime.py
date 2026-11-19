import asyncio
import os
import tempfile
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import Mock

from avocado.core.messages import MessageHandler
from avocado.core.nrunner.runnable import Runnable
from avocado.core.nrunner.task import Task
from avocado.core.status.repo import StatusRepo
from avocado.core.suite import TestSuite
from avocado.core.task.runtime import RuntimeTask, RuntimeTaskGraph
from avocado.core.task.statemachine import TaskStateMachine, Worker
from avocado.core.utils import messages
from avocado.utils import script
from selftests.utils import TestCaseTmpDir

SINGLE_REQUIREMENT = '''from avocado import Test
class SuccessTest(Test):
    def test_a(self):
       pass
    def test_b(self):
        """
        :avocado: dependency={"type": "package", "name": "hello"}
        """
    def test_c(self):
        """
        :avocado: dependency={"type": "package", "name": "hello"}
        """
'''

MULTIPLE_REQUIREMENT = '''from avocado import Test
class FailTest(Test):
    def test_a(self):
        """
        :avocado: dependency={"type": "package", "name": "hello"}
        """
    def test_b(self):
        pass
    def test_c(self):
        """
        :avocado: dependency={"type": "package", "name": "hello"}
        :avocado: dependency={"type": "package", "name": "-foo-bar-"}
        """
'''


class Runtime(TestCase):
    def setUp(self):
        runnable = Runnable("noop", "noop")
        task = Task(runnable, "1-noop")
        self.runtime_task = RuntimeTask(task)

    def test_empty(self):
        self.assertIsNone(self.runtime_task.status)
        self.assertIsNone(self.runtime_task.execution_timeout)
        self.assertIsNone(self.runtime_task.spawner_handle)
        self.assertIsNone(self.runtime_task.spawning_result)

    def test(self):
        self.runtime_task.status = "LOST CONTACT"
        self.assertEqual(self.runtime_task.task.runnable.kind, "noop")
        self.assertEqual(self.runtime_task.task.runnable.uri, "noop")
        self.assertEqual(self.runtime_task.status, "LOST CONTACT")


class WorkerMonitor(IsolatedAsyncioTestCase):
    async def test_late_start_after_interruption_does_not_repeat_reporting(self):
        def report_messages(status_repo, handler, task, job):
            while True:
                try:
                    entry = status_repo.status_journal_summary_pop()
                except IndexError:
                    return
                _, task_id, _, index = entry
                message = status_repo.get_task_data(task_id, index)
                handler.process_message(message.copy(), task, job)

        for delivery in ("before_reporting", "after_reporting", "never"):
            with self.subTest(delivery=delivery), tempfile.TemporaryDirectory() as root:
                runnable = Runnable(
                    "noop", "noop", output_dir=os.path.join(root, "task")
                )
                task = Task(runnable, "1-noop", job_id="job")
                task.metadata["symlink"] = os.path.join(root, "link")
                runtime_task = RuntimeTask(task)
                status_repo = StatusRepo(task.job_id)
                state_machine = TaskStateMachine([runtime_task], status_repo)
                worker = Worker(state_machine, Mock())
                job = Mock(logdir=root, unique_id="job", test_results_path=root)
                handler = MessageHandler()

                late_start = messages.StartedMessage.get(
                    output_dir=runnable.output_dir,
                    id=task.identifier,
                    job_id=task.job_id,
                )
                await worker._send_finished_tasks_message([runtime_task], "timeout")
                start_time = status_repo.get_all_task_data(task.identifier)[0]["time"]
                if delivery == "before_reporting":
                    status_repo.process_message(late_start)
                report_messages(status_repo, handler, task, job)
                if delivery == "after_reporting":
                    status_repo.process_message(late_start)
                status_repo.process_message(
                    messages.LogMessage.get(
                        "later message", id=task.identifier, job_id=task.job_id
                    )
                )
                report_messages(status_repo, handler, task, job)

                job.result.start_test.assert_called_once()
                job.result.check_test.assert_called_once()
                self.assertEqual(task.metadata["time_start"], start_time)
                self.assertEqual(
                    os.readlink(task.metadata["symlink"]), runnable.output_dir
                )
                with open(task.metadata["logfile"], encoding="utf-8") as logfile:
                    self.assertIn("later message", logfile.read())

    async def test_first_finished_result_survives_late_messages(self):
        for delayed in (False, True):
            with self.subTest(delayed=delayed):
                task = Task(Runnable("noop", "noop"), "1-noop", job_id="job")
                runtime_task = RuntimeTask(task)
                status_repo = StatusRepo(task.job_id)
                state_machine = TaskStateMachine([runtime_task], status_repo)
                state_machine.started.append(state_machine.requested.popleft())
                spawner = Mock()
                spawner.is_task_alive.return_value = False
                worker = Worker(state_machine, spawner)
                monitor = asyncio.create_task(worker.monitor())
                if delayed:
                    # Let monitoring reach its polling loop before messages arrive.
                    await asyncio.sleep(0)

                for timestamp, fields in enumerate(
                    (
                        {"status": "finished", "result": "pass"},
                        {"status": "running"},
                        {"status": "finished", "result": "fail"},
                    ),
                    1,
                ):
                    status_repo.process_message(
                        {
                            "id": str(task.identifier),
                            "job_id": task.job_id,
                            "time": timestamp,
                            **fields,
                        }
                    )

                await asyncio.wait_for(monitor, 1)

                self.assertEqual(runtime_task.result, "pass")
                self.assertEqual(state_machine.finished, [runtime_task])
                self.assertEqual(
                    status_repo.get_finished_task_data("1-noop")["result"], "pass"
                )


class DependencyGraph(TestCaseTmpDir):
    def test_one_dependency(self):
        with script.Script(
            os.path.join(self.tmpdir.name, "test_single_dependency.py"),
            SINGLE_REQUIREMENT,
        ) as test:
            config = {"resolver.references": [test.path]}
            suite = TestSuite.from_config(config=config)
            tests = suite.tests
            graph = RuntimeTaskGraph(tests, suite.name, 1, "", "")
            runtime_tests = graph.get_tasks_in_topological_order()
            self.assertTrue(runtime_tests[0].task.identifier.name.endswith("test_a"))
            self.assertTrue(runtime_tests[1].task.identifier.name.endswith("hello"))
            self.assertTrue(runtime_tests[2].task.identifier.name.endswith("test_b"))
            self.assertTrue(runtime_tests[3].task.identifier.name.endswith("hello"))
            self.assertTrue(runtime_tests[4].task.identifier.name.endswith("test_c"))

    def test_multiple_dependencies(self):
        with script.Script(
            os.path.join(self.tmpdir.name, "test_multiple_dependencies.py"),
            MULTIPLE_REQUIREMENT,
        ) as test:
            config = {"resolver.references": [test.path]}
            suite = TestSuite.from_config(config=config)
            tests = suite.tests
            graph = RuntimeTaskGraph(tests, suite.name, 1, "", "")
            runtime_tests = graph.get_tasks_in_topological_order()
            self.assertTrue(runtime_tests[0].task.identifier.name.endswith("hello"))
            self.assertTrue(runtime_tests[1].task.identifier.name.endswith("test_a"))
            self.assertTrue(runtime_tests[2].task.identifier.name.endswith("test_b"))
            self.assertTrue(runtime_tests[3].task.identifier.name.endswith("hello"))
            self.assertTrue(runtime_tests[4].task.identifier.name.endswith("-foo-bar-"))
            self.assertTrue(runtime_tests[5].task.identifier.name.endswith("test_c"))
