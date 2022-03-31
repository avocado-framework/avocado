from copy import deepcopy

from avocado.core.dependencies.resolver import DependencyResolver
from avocado.core.nrunner.task import Task
from avocado.core.test_id import TestID
from avocado.core.varianter import dump_variant


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
            return (f'<RuntimeTask Task Identifier: "{self.task.identifier}"'
                    f'Status: "{self.status}">')

    def __hash__(self):
        if self.task.category == "test":
            return hash(self.task.identifier)
        return hash((str(self.task.runnable), self.task.job_id,
                     self.task.category))

    def __eq__(self, other):
        if isinstance(other, RuntimeTask):
            return hash(self) == hash(other)
        return False

    @classmethod
    def get_test_from_runnable(cls, runnable, no_digits, index, variant,
                               test_suite_name=None, status_server_uri=None,
                               job_id=None):
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
        :returns: RUntimeTask of the test from runnable
        """

        # create test ID
        if test_suite_name:
            prefix = f"{test_suite_name}-{index}"
        else:
            prefix = index
        test_id = TestID(prefix,
                         runnable.identifier,
                         variant,
                         no_digits)
        # inject variant on runnable
        runnable.variant = dump_variant(variant)

        # handles the test task
        task = Task(runnable,
                    identifier=test_id,
                    status_uris=status_server_uri,
                    job_id=job_id)
        return cls(task)

    @classmethod
    def get_dependencies_form_runnable(cls, runnable, status_server_uri=None,
                                       job_id=None):
        """Creates runtime tasks for dependencies from runnable

        :param runnable: the "description" of what the task should run.
        :type runnable: :class:`avocado.core.nrunner.Runnable`
        :param status_server_uri: the URIs for the status servers that this
                                  task should send updates to.
        :type status_server_uri: list
        :param job_id: the ID of the job, for authenticating messages that get
                       sent to the destination job's status server and will
                       make into the job's results.
        :type job_id: str
        :returns: RUntimeTasks of the dependencies from runnable
        :rtype: list
        """
        if runnable.dependencies is None:
            return []

        # creates the runnables for the dependencies
        dependencies_runnables = DependencyResolver.resolve(runnable)
        dependencies_runtime_tasks = []
        # creates the tasks and runtime tasks for the dependencies
        for dependency_runnable in dependencies_runnables:
            name = (f"{dependency_runnable.kind}-"
                    f"{dependency_runnable.kwargs.get('name')}")
            prefix = 0
            # the human UI works with TestID objects, so we need to
            # use it to name Task
            task_id = TestID(prefix, name)
            # with --dry-run we don't want to run dependencies
            if runnable.kind == 'dry-run':
                dependency_runnable.kind = 'noop'
            # creates the dependency task
            dependency_task = Task(dependency_runnable,
                                   identifier=task_id,
                                   status_uris=status_server_uri,
                                   category='dependency',
                                   job_id=job_id)
            dependencies_runtime_tasks.append(cls(dependency_task))

        return dependencies_runtime_tasks

    def is_dependencies_finished(self):
        for dependency in self.dependencies:
            if not dependency.status or not ("FINISHED" in dependency.status
                                             or "FAILED" in dependency.status):
                return False
        return True


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
            runtime_test = RuntimeTask.get_test_from_runnable(
                runnable,
                no_digits,
                index,
                variant,
                test_suite_name,
                status_server_uri,
                job_id)
            self.graph[runtime_test] = runtime_test

            dependencies_tasks = RuntimeTask.get_dependencies_form_runnable(
                runnable,
                status_server_uri,
                job_id)
            self._connect_dependencies_with_test(dependencies_tasks,
                                                 runtime_test)

    def _connect_dependencies_with_test(self, dependencies, runtime_test):
        for dependency_task in dependencies:
            if dependency_task in self.graph:
                dependency_task = self.graph.get(dependency_task)
            else:
                self.graph[dependency_task] = dependency_task
            runtime_test.dependencies.append(dependency_task)

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
