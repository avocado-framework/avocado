from copy import deepcopy
from enum import Enum
from itertools import chain

from avocado.core.dispatcher import TestPreDispatcher
from avocado.core.nrunner.task import Task
from avocado.core.test_id import TestID
from avocado.core.varianter import dump_variant


class RuntimeTaskStatus(Enum):
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


class RuntimeTask:
    """Task with extra status information on its life cycle status.

    The :class:`avocado.core.nrunner.Task` class contains information
    that is necessary to describe its persistence and execution by itself.

    This class wraps a :class:`avocado.core.nrunner.Task`, with extra
    information about its execution by a spawner within a state machine.
    """

    def __init__(self, task):
        """Instantiates a new RuntimeTask.

        :param task: The task to keep additional information about
        :type task: :class:`avocado.core.nrunner.Task`
        """
        #: The :class:`avocado.core.nrunner.Task`
        self.task = task
        #: Additional descriptive information about the task status
        self.status = None
        #: Information about task result when it is finished
        self.result = None
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
            if dependency.result != "pass":
                return False
        return True

    @classmethod
    def from_runnable(
        cls,
        runnable,
        no_digits,
        index,
        variant,
        test_suite_name=None,
        status_server_uri=None,
        job_id=None,
    ):
        """Creates runtime task for test from runnable

        :param runnable: the "description" of what the task should run.
        :type runnable: :class:`avocado.core.nrunner.Runnable`
        :param no_digits: number of digits of the test uid
        :type no_digits: int
        :param index: index of tests inside test suite
        :type index: int
        :param test_suite_name: test suite name which this test is related to
        :type test_suite_name: str
        :param status_server_uri: the URIs for the status servers that this
                                  task should send updates to.
        :type status_server_uri: list
        :param job_id: the ID of the job, for authenticating messages that get
                       sent to the destination job's status server and will
                       make into the job's results.
        :type job_id: str
        :returns: RuntimeTask of the test from runnable
        """

        # create test ID
        if test_suite_name:
            prefix = f"{test_suite_name}-{index}"
        else:
            prefix = index
        test_id = TestID(prefix, runnable.identifier, variant, no_digits)
        # inject variant on runnable
        runnable.variant = dump_variant(variant)

        # handles the test task
        task = Task(
            runnable, identifier=test_id, status_uris=status_server_uri, job_id=job_id
        )
        return cls(task)


class PreRuntimeTask(RuntimeTask):
    @classmethod
    def from_runnable(
        cls, pre_runnable, status_server_uri=None, job_id=None
    ):  # pylint: disable=W0221
        """Creates runtime task for pre_test plugin from runnable

        :param pre_runnable: the "description" of what the task should run.
        :type runnable: :class:`avocado.core.nrunner.Runnable`
        :param status_server_uri: the URIs for the status servers that this
                                  task should send updates to.
        :type status_server_uri: list
        :param job_id: the ID of the job, for authenticating messages that get
                       sent to the destination job's status server and will
                       make into the job's results.
        :type job_id: str
        :returns: RuntimeTask of the test from runnable
        """
        name = f'{pre_runnable.kind}-{pre_runnable.kwargs.get("name")}'
        prefix = 0
        # the human UI works with TestID objects, so we need to
        # use it to name Task
        task_id = TestID(prefix, name)
        # creates the dependency task
        task = Task(
            pre_runnable,
            identifier=task_id,
            status_uris=status_server_uri,
            category="pre_test",
            job_id=job_id,
        )
        return cls(task)

    @classmethod
    def get_pre_tasks_from_runnable(cls, runnable, status_server_uri=None, job_id=None):
        """Creates runtime tasks for preTest task from runnable

        :param runnable: the "description" of what the task should run.
        :type runnable: :class:`avocado.core.nrunner.Runnable`
        :param status_server_uri: the URIs for the status servers that this
                                  task should send updates to.
        :type status_server_uri: list
        :param job_id: the ID of the job, for authenticating messages that get
                       sent to the destination job's status server and will
                       make into the job's results.
        :type job_id: str
        :returns: Pre RuntimeTasks of the dependencies from runnable
        :rtype: list
        """

        pre_runnables = list(
            chain.from_iterable(
                TestPreDispatcher().map_method_with_return(
                    "pre_test_runnables", runnable
                )
            )
        )
        pre_test_tasks = []
        for pre_runnable in pre_runnables:
            pre_task = cls.from_runnable(pre_runnable, status_server_uri, job_id)
            pre_test_tasks.append(pre_task)
        return pre_test_tasks


class RuntimeTaskGraph:
    """Graph representing dependencies between runtime tasks."""

    def __init__(self, tests, test_suite_name, status_server_uri, job_id):
        """Instantiates a new RuntimeTaskGraph.

        From the list of tests, it will create runtime tasks and connects them
        inside the graph by its dependencies.

        :param tests: variants of runnables from test suite
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
        """
        self.graph = {}
        # create graph
        no_digits = len(str(len(tests)))
        for index, (runnable, variant) in enumerate(tests, start=1):
            runnable = deepcopy(runnable)
            runtime_test = RuntimeTask.from_runnable(
                runnable,
                no_digits,
                index,
                variant,
                test_suite_name,
                status_server_uri,
                job_id,
            )
            self.graph[runtime_test] = runtime_test

            # with --dry-run we don't want to run dependencies
            if runnable.kind != "dry-run":
                pre_tasks = PreRuntimeTask.get_pre_tasks_from_runnable(
                    runnable, status_server_uri, job_id
                )
                if pre_tasks:
                    pre_tasks.append(runtime_test)
                    self._connect_tasks(pre_tasks)

    def _connect_tasks(self, tasks):
        for dependency, task in zip(tasks, tasks[1:]):
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
