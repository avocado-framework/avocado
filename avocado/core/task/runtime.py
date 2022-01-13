from copy import deepcopy

from avocado.core import nrunner
from avocado.core.requirements.resolver import RequirementsResolver
from avocado.core.test_id import TestID
from avocado.core.tree import TreeNode
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


class RuntimeGraph:

    def __init__(self, test_suite, job_id, status_server_uri):
        self.test_suite = test_suite
        self.job_id = job_id
        self.status_server_uri = status_server_uri

    def _get_requirements_runtime_tasks(self, runnable, prefix):
        if runnable.requirements is None:
            return

        # creates the runnables for the requirements
        requirements_runnables = RequirementsResolver.resolve(runnable)
        requirements_runtime_tasks = []
        # creates the tasks and runtime tasks for the requirements
        for requirement_runnable in requirements_runnables:
            name = '%s-%s' % (requirement_runnable.kind,
                              requirement_runnable.kwargs.get('name'))
            # the human UI works with TestID objects, so we need to
            # use it to name other tasks
            task_id = TestID(prefix,
                             name,
                             None)
            # with --dry-run we don't want to run requirement
            if runnable.kind == 'dry-run':
                requirement_runnable.kind = 'noop'
            # creates the requirement task
            requirement_task = nrunner.Task(requirement_runnable,
                                            identifier=task_id,
                                            status_uris=[self.status_server_uri],
                                            category='requirement',
                                            job_id=self.job_id)
            # make sure we track the dependencies of a task
            # runtime_task.task.dependencies.add(requirement_task)
            # created the requirement runtime task
            requirements_runtime_tasks.append(RuntimeTask(requirement_task))

        return requirements_runtime_tasks

    def _create_runtime_tasks_for_test(self, runnable, no_digits,
                                       index, variant):
        """Creates runtime tasks for both tests, and for its requirements."""
        result = []

        # test related operations
        # create test ID
        if self.test_suite.name:
            prefix = "{}-{}".format(self.test_suite.name, index)
        else:
            prefix = index
        test_id = TestID(prefix,
                         runnable.identifier,
                         variant,
                         no_digits)
        # inject variant on runnable
        runnable.variant = dump_variant(variant)

        # handles the test task
        task = nrunner.Task(runnable,
                            identifier=test_id,
                            known_runners=nrunner.RUNNERS_REGISTRY_PYTHON_CLASS,
                            status_uris=[self.status_server_uri],
                            job_id=self.job_id)
        runtime_task = RuntimeTask(task)
        result.append(runtime_task)

        # handles the requirements
        requirements_runtime_tasks = (
            self._get_requirements_runtime_tasks(runnable,
                                                 prefix))
        # extend the list of tasks with the requirements runtime tasks
        if requirements_runtime_tasks is not None:
            for requirement_runtime_task in requirements_runtime_tasks:
                # make sure we track the dependencies of a task
                runtime_task.task.dependencies.add(
                    requirement_runtime_task.task)
            result.extend(requirements_runtime_tasks)

        return result

    def _get_test_variants(self):
        """Computes test variants based on the test_suite"""

        if self.test_suite.test_parameters:
            paths = ['/']
            tree_nodes = TreeNode().get_node(paths[0], True)
            tree_nodes.value = self.test_suite.test_parameters
            variant = {"variant": tree_nodes,
                       "variant_id": None,
                       "paths": paths}
            test_variant = [(test, variant) for test in self.test_suite.tests]

        else:
            # let's use variants when parameters are not available
            # define execution order
            execution_order = self.test_suite.config.get('run.execution_order')
            if execution_order == "variants-per-test":
                test_variant = [(test, variant)
                                for test in self.test_suite.tests
                                for variant in self.test_suite.variants.itertests()]
            elif execution_order == "tests-per-variant":
                test_variant = [(test, variant)
                                for variant in self.test_suite.variants.itertests()
                                for test in self.test_suite.tests]
        return test_variant

    def get_all_runtime_tasks(self):
        test_result_total = self.test_suite.variants.get_number_of_tests(
            self.test_suite.tests)
        no_digits = len(str(test_result_total))

        # decide if a copy of the runnable is needed, in case of more
        # variants than tests
        test_variant = self._get_test_variants()
        copy_runnable = len(test_variant) > len(self.test_suite.tests)
        # create runtime tasks
        runtime_tasks = []
        for index, (runnable, variant) in enumerate(test_variant, start=1):
            if copy_runnable:
                runnable = deepcopy(runnable)
            runtime_tasks.extend(self._create_runtime_tasks_for_test(
                runnable,
                no_digits,
                index,
                variant))
        # remove duplicates from runtime_tasks
        return list(dict.fromkeys(runtime_tasks))
