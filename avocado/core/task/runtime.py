import itertools
import os
from enum import Enum

from avocado.core.dispatcher import TestPostDispatcher, TestPreDispatcher
from avocado.core.nrunner.task import TASK_DEFAULT_CATEGORY, Task
from avocado.core.test_id import TestID


class RuntimeTaskStatus(Enum):
    INTERRUPTED = "FINISHED INTERRUPTED"
    WAIT_DEPENDENCIES = "WAITING DEPENDENCIES"
    WAIT = "WAITING"
    FINISHED = "FINISHED"
    TIMEOUT = "FINISHED TIMEOUT"
    IN_CACHE = "FINISHED IN CACHE"
    FAILFAST = "FINISHED FAILFAST"
    FAIL_TRIAGE = "FINISHED WITH FAILURE ON TRIAGE"
    FAIL_START = "FINISHED FAILING TO START"
    STARTED = "STARTED"

    @staticmethod
    def finished_statuses():
        return [
            status
            for _, status in RuntimeTaskStatus.__members__.items()
            if "FINISHED" in status.value
        ]


class RuntimeTaskMixin:
    """Common utilities for RuntimeTask implementations."""

    @classmethod
    def from_runnable(
        cls,
        runnable,
        no_digits,
        index,
        base_dir,
        test_suite_name=None,
        status_server_uri=None,
        job_id=None,
        satisfiable_deps_execution_statuses=None,
    ):
        """Creates runtime task for test from runnable

        :param runnable: the "description" of what the task should run.
        :type runnable: :class:`avocado.core.nrunner.Runnable`
        :param no_digits: number of digits of the test uid
        :type no_digits: int
        :param index: index of tests inside test suite
        :type index: int
        :param base_dir: Path to the job base directory.
        :type base_dir: str
        :param test_suite_name: test suite name which this test is related to
        :type test_suite_name: str
        :param status_server_uri: the URIs for the status servers that this
                                  task should send updates to.
        :type status_server_uri: list
        :param job_id: the ID of the job, for authenticating messages that get
                       sent to the destination job's status server and will
                       make into the job's results.
        :type job_id: str
        :param satisfiable_deps_execution_statuses: The dependency result types that
        satisfy the execution of this RuntimeTask.
        :type satisfiable_deps_execution_statuses: list of test results.
        :returns: RuntimeTask of the test from runnable
        """

        # create test ID
        if test_suite_name:
            prefix = f"{test_suite_name}-{index}"
        else:
            prefix = index
        if cls.category is TASK_DEFAULT_CATEGORY:
            name = runnable.identifier
        else:
            name = f'{runnable.kind}-{runnable.kwargs.get("name")}'

        test_id = TestID(prefix, name, runnable.variant, no_digits)

        if not runnable.output_dir:
            runnable.output_dir = os.path.join(base_dir, test_id.str_filesystem)
        # handles the test task
        task = Task(
            runnable,
            identifier=test_id,
            status_uris=status_server_uri,
            category=cls.category,
            job_id=job_id,
        )
        return cls(task, satisfiable_deps_execution_statuses)


class RuntimeTask(RuntimeTaskMixin):
    """Task with extra status information on its life cycle status.

    The :class:`avocado.core.nrunner.Task` class contains information
    that is necessary to describe its persistence and execution by itself.

    This class wraps a :class:`avocado.core.nrunner.Task`, with extra
    information about its execution by a spawner within a state machine.
    """

    category = TASK_DEFAULT_CATEGORY

    def __init__(self, task, satisfiable_deps_execution_statuses=None):
        """Instantiates a new RuntimeTask.

        :param task: The task to keep additional information about
        :type task: :class:`avocado.core.nrunner.Task`
        :param satisfiable_deps_execution_statuses: The dependency result types that
        satisfy the execution of this RuntimeTask.
        :type satisfiable_deps_execution_statuses: list of test results.
        """
        #: The :class:`avocado.core.nrunner.Task`
        self.task = task
        #: The task status, a value from the enum
        #: :class:`avocado.core.task.runtime.RuntimeTaskStatus`
        self.status = None
        #: Information about task result when it is finished
        self._result = None
        #: Timeout limit for the completion of the task execution
        self.execution_timeout = None
        #: A handle that may be set by a spawner, and that may be
        #: spawner implementation specific, to keep track the task
        #: execution.  This may be a PID, a container ID, a FQDN+PID
        #: etc.
        self.spawner_handle = None
        #: The result of the spawning of a Task
        self.spawning_result = None
        self.dependencies = []
        self._satisfiable_deps_execution_statuses = ["pass"]
        if satisfiable_deps_execution_statuses:
            self._satisfiable_deps_execution_statuses = [
                status.lower() for status in satisfiable_deps_execution_statuses
            ]
        #: Flag to detect if the task should be save to cache
        self.is_cacheable = False

    def __repr__(self):
        if self.status is None:
            return f'<RuntimeTask Task Identifier: "{self.task.identifier}">'
        else:
            return (
                f'<RuntimeTask Task Identifier: "{self.task.identifier}" '
                f'Status: "{self.status}">'
            )

    def __hash__(self):
        return hash(self.task.identifier)

    def __eq__(self, other):
        if isinstance(other, RuntimeTask):
            return hash(self) == hash(other)
        return False

    @property
    def result(self):
        return self._result

    @property
    def satisfiable_deps_execution_statuses(self):
        return self._satisfiable_deps_execution_statuses

    @result.setter
    def result(self, result):
        self._result = result.lower()

    def are_dependencies_finished(self):
        for dependency in self.dependencies:
            if dependency.status not in RuntimeTaskStatus.finished_statuses():
                return False
        return True

    def get_finished_dependencies(self):
        """Returns all dependencies which already finished."""
        return [
            dep
            for dep in self.dependencies
            if dep.status in RuntimeTaskStatus.finished_statuses()
        ]

    def can_run(self):
        if not self.are_dependencies_finished():
            return False

        for dependency in self.dependencies:
            if dependency.result not in self.satisfiable_deps_execution_statuses:
                return False
        return True


class PrePostRuntimeTaskMixin(RuntimeTask):
    """Common utilities for PrePostRuntimeTask implementations."""

    @classmethod
    def get_tasks_from_test_task(
        cls,
        test_task,
        no_digits,
        base_dir,
        test_suite_name=None,
        status_server_uri=None,
        job_id=None,
        suite_config=None,
    ):
        """Creates runtime tasks for preTest task from test task.

        :param test_task: Runtime test task.
        :type test_task: :class:`avocado.core.task.runtime.RuntimeTask`
        :param no_digits: number of digits of the test uid
        :type no_digits: int
        :param base_dir: Path to the job base directory.
        :type base_dir: str
        :param test_suite_name: test suite name which this test is related to
        :type test_suite_name: str
        :param status_server_uri: the URIs for the status servers that this
                                  task should send updates to.
        :type status_server_uri: list
        :param job_id: the ID of the job, for authenticating messages that get
                       sent to the destination job's status server and will
                       make into the job's results.
        :type job_id: str
        :param suite_config: Configuration dict relevant for the whole suite.
        :type suite_config: dict
        :returns: Pre/Post RuntimeTasks of the dependencies from runnable
        :rtype: list
        """
        tasks = []
        plugins = cls.dispatcher().get_extentions_by_priority()
        runnable = test_task.task.runnable
        prefix = f"{test_task.task.identifier.str_filesystem}"
        for plugin in plugins:
            plugin = plugin.obj
            is_cacheable = getattr(plugin, "is_cacheable", False)
            test_runnables_method = getattr(plugin, f"{cls.category}_runnables")
            runnables = test_runnables_method(runnable, suite_config)
            for runnable in runnables:
                satisfiable_deps_execution_statuses = None
                if isinstance(runnable, tuple):
                    runnable, satisfiable_deps_execution_statuses = runnable
                output_dir_not_exists = runnable.output_dir is None
                task = cls.from_runnable(
                    runnable,
                    no_digits,
                    prefix,
                    base_dir,
                    test_suite_name,
                    status_server_uri,
                    job_id,
                    satisfiable_deps_execution_statuses,
                )
                if output_dir_not_exists:
                    runnable.output_dir = os.path.join(
                        os.path.abspath(os.path.join(base_dir, os.pardir)),
                        "dependencies",
                        str(task.task.identifier),
                    )
                    task.task.metadata["symlink"] = os.path.join(
                        test_task.task.runnable.output_dir,
                        "dependencies",
                        f'{runnable.kind}-{runnable.kwargs.get("name")}',
                    )
                task.is_cacheable = is_cacheable
                tasks.append(task)
        return tasks


class PreRuntimeTask(PrePostRuntimeTaskMixin):
    """Runtime task for tasks run before test"""

    category = "pre_test"
    dispatcher = TestPreDispatcher


class PostRuntimeTask(PrePostRuntimeTaskMixin):
    """Runtime task for tasks run after test"""

    category = "post_test"
    dispatcher = TestPostDispatcher


class RuntimeTaskGraph:
    """Graph representing dependencies between runtime tasks."""

    def __init__(
        self,
        tests,
        test_suite_name,
        status_server_uri,
        job_id,
        base_dir,
        suite_config=None,
    ):
        """Instantiates a new RuntimeTaskGraph.

        From the list of tests, it will create runtime tasks and connects them
        inside the graph by its dependencies.

        :param tests: runnables from test suite
        :type tests: list
        :param test_suite_name: test suite name which this test is related to
        :type test_suite_name: str
        :param status_server_uri: the URIs for the status servers that this
                                  task should send updates to.
        :type status_server_uri: list
        :param job_id: the ID of the job, for authenticating messages that get
                       sent to the destination job's status server and will
                       make into the job's results.
        :type job_id: str
        :param base_dir: Path to the job base directory.
        :type base_dir: str
        :param suite_config: Configuration dict relevant for the whole suite.
        :type suite_config: dict
        """
        self.graph = {}
        # create graph
        no_digits = len(str(len(tests)))
        for index, runnable in enumerate(tests, start=1):
            runtime_test = RuntimeTask.from_runnable(
                runnable,
                no_digits,
                index,
                base_dir,
                test_suite_name,
                status_server_uri,
                job_id,
            )
            self.graph[runtime_test] = runtime_test

            # with --dry-run we don't want to run dependencies
            if runnable.kind != "dry-run":
                pre_tasks = PreRuntimeTask.get_tasks_from_test_task(
                    runtime_test,
                    no_digits,
                    base_dir,
                    test_suite_name,
                    status_server_uri,
                    job_id,
                    suite_config,
                )
                post_tasks = PostRuntimeTask.get_tasks_from_test_task(
                    runtime_test,
                    no_digits,
                    base_dir,
                    test_suite_name,
                    status_server_uri,
                    job_id,
                    suite_config,
                )
                if pre_tasks or post_tasks:
                    self._connect_tasks(pre_tasks, [runtime_test], post_tasks)

    def _connect_tasks(self, pre_tasks, tasks, post_tasks):
        connections = list(itertools.product(pre_tasks, tasks))
        connections += list(itertools.product(tasks, post_tasks))
        for dependency, task in connections:
            self.graph[task] = task
            self.graph[dependency] = dependency
            task.dependencies.append(dependency)

    def get_tasks_in_topological_order(self):
        """Computes the topological order of runtime tasks in graph

        :returns: runtime tasks in topological order
        :rtype: list
        """

        def topological_order_util(vertex, visited, topological_order):
            visited[vertex] = True
            for v in vertex.dependencies:
                if not visited[v]:
                    topological_order_util(v, visited, topological_order)
            topological_order.append(vertex)

        visited = dict.fromkeys(self.graph, False)
        topological_order = []

        for vertex in self.graph.values():
            if not visited[vertex]:
                topological_order_util(vertex, visited, topological_order)
        return topological_order
