from copy import deepcopy
from itertools import chain

from avocado.core.dispatcher import TestPostDispatcher, TestPreDispatcher
from avocado.core.nrunner import RUNNERS_REGISTRY_PYTHON_CLASS, Task
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
            return '<RuntimeTask Task Identifier: "%s">' % self.task.identifier
        else:
            return '<RuntimeTask Task Identifier: "%s" Status: "%s">' % (
                self.task.identifier,
                self.status)

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
            prefix = "{}-{}".format(test_suite_name, index)
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
                    known_runners=RUNNERS_REGISTRY_PYTHON_CLASS,
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
        :returns: Pre and Post RuntimeTasks of the dependencies from runnable
        :rtype: (list, list)
        """

        def _crete_runtime_tasks(dependencies):
            # creates the tasks and runtime tasks for the dependencies
            dependencies_runtime_tasks = []
            for dependency_runnable in dependencies:
                name = '%s-%s' % (dependency_runnable.kind,
                                  dependency_runnable.kwargs.get('name'))
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

        pre_runnables = list(chain.from_iterable(
            TestPreDispatcher().map_method_with_return('pre_test_runnables',
                                                       runnable)))
        post_runnables = list(chain.from_iterable(
            TestPostDispatcher().map_method_with_return('post_test_runnables',
                                                        runnable)))

        return (_crete_runtime_tasks(pre_runnables),
                _crete_runtime_tasks(post_runnables))

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

            pre_tasks, post_tasks = RuntimeTask.get_dependencies_form_runnable(
                runnable,
                status_server_uri,
                job_id)
            self._connect_tasks(pre_tasks, [runtime_test])
            self._connect_tasks([runtime_test], post_tasks)

    def _connect_tasks(self, dependencies, tasks):
        def _get_task_from_graph(task):
            if task in self.graph:
                task = self.graph.get(task)
            else:
                self.graph[task] = task
            return task

        for dependency_task in dependencies:
            dependency_task = _get_task_from_graph(dependency_task)
            for task in tasks:
                task = _get_task_from_graph(task)
                task.dependencies.append(dependency_task)

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
