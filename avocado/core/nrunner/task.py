import base64
import json
import socket
import tempfile
from uuid import uuid1

from avocado.core.nrunner.runnable import (
    RUNNERS_REGISTRY_STANDALONE_EXECUTABLE, Runnable)

#: The default category for tasks, and the value that will cause the
#: task results to be included in the job results
TASK_DEFAULT_CATEGORY = 'test'


class StatusEncoder(json.JSONEncoder):

    # pylint: disable=E0202
    def default(self, o):
        if isinstance(o, bytes):
            return {'__base64_encoded__': base64.b64encode(o).decode('ascii')}
        return json.JSONEncoder.default(self, o)


def json_dumps(data):
    return json.dumps(data, ensure_ascii=True, cls=StatusEncoder)


class TaskStatusService:
    """
    Implementation of interface that a task can use to post status updates

    TODO: make the interface generic and this just one of the implementations
    """

    def __init__(self, uri):
        self.uri = uri
        self.connection = None

    def post(self, status):
        if ':' in self.uri:
            host, port = self.uri.split(':')
            port = int(port)
            if self.connection is None:
                self.connection = socket.create_connection((host, port))
        else:
            if self.connection is None:
                self.connection = socket.socket(socket.AF_UNIX,
                                                socket.SOCK_STREAM)
                self.connection.connect(self.uri)

        data = json_dumps(status)
        self.connection.send(data.encode('ascii') + "\n".encode('ascii'))

    def close(self):
        if self.connection is not None:
            self.connection.close()

    def __repr__(self):
        return f'<TaskStatusService uri="{self.uri}">'


class Task:
    """
    Wraps the execution of a runnable

    While a runnable describes what to be run, and gets run by a
    runner, a task should be a unique entity to track its state,
    that is, whether it is pending, is running or has finished.
    """

    def __init__(self, runnable, identifier=None, status_uris=None,
                 category=TASK_DEFAULT_CATEGORY, job_id=None):
        """Instantiates a new Task.

        :param runnable: the "description" of what the task should run.
        :type runnable: :class:`avocado.core.nrunner.Runnable`
        :param identifier: any identifier that is guaranteed to be unique
                           within the context of a Job. A recommended value
                           is a :class:`avocado.core.test_id.TestID` instance
                           when a task represents a test, because besides the
                           uniqueness aspect, it's also descriptive.  If an
                           identifier is not given, an automatically generated
                           one will be set.
        :param status_uri: the URIs for the status servers that this task
                           should send updates to.
        :type status_uri: list
        :param category: category of this task. Defaults to
                         :data:`TASK_DEFAULT_CATEGORY`.
        :type category: str
        :param job_id: the ID of the job, for authenticating messages that get
                       sent to the destination job's status server and will make
                       into the job's results.
        :type job_id: str
        """
        # pylint: disable=W0201
        self.runnable = runnable
        self.identifier = identifier or str(uuid1())
        #: Category of the task.  If the category is not "test", it
        #: will not be accounted for on a Job's test results.
        self.category = category
        self.job_id = job_id
        self.status_services = []
        status_uris = status_uris or self.runnable.config.get('nrunner.status_server_uri')
        if status_uris is not None:
            if type(status_uris) is not list:
                status_uris = [status_uris]
            for status_uri in status_uris:
                self.status_services.append(TaskStatusService(status_uri))
        self.spawn_handle = None
        self.metadata = {}

    def __repr__(self):
        fmt = ('<Task identifier="{}" runnable="{}" status_services="{}"'
               ' category="{}" job_id="{}">')
        return fmt.format(self.identifier, self.runnable, self.status_services,
                          self.category, self.job_id)

    def are_dependencies_available(self, runners_registry=None):
        """Verifies if dependencies needed to run this task are available.

        This currently checks the runner command only, but can be expanded once
        the handling of other types of dependencies are implemented.  See
        :doc:`/blueprints/BP002`.
        """
        if runners_registry is None:
            runners_registry = RUNNERS_REGISTRY_STANDALONE_EXECUTABLE
        return self.runnable.pick_runner_command(runners_registry)

    def setup_output_dir(self, output_dir=None):
        if not self.runnable.output_dir:
            output_dir = output_dir or tempfile.mkdtemp(prefix='.avocado-task-')
            self.runnable.output_dir = output_dir

    @classmethod
    def from_recipe(cls, task_path):
        """
        Creates a task (which contains a runnable) from a task recipe file

        :param task_path: Path to a recipe file

        :rtype: instance of :class:`Task`
        """
        with open(task_path, encoding='utf-8') as recipe_file:
            recipe = json.load(recipe_file)

        identifier = recipe.get('id')
        runnable_recipe = recipe.get('runnable')
        runnable = Runnable(runnable_recipe.get('kind'),
                            runnable_recipe.get('uri'),
                            *runnable_recipe.get('args', ()),
                            config=runnable_recipe.get('config'))
        status_uris = recipe.get('status_uris')
        category = recipe.get('category')
        return cls(runnable, identifier, status_uris, category)

    def get_command_args(self):
        """
        Returns the command arguments that adhere to the runner interface

        This is useful for building 'task-run' commands that can be
        executed on a command line interface.

        :returns: the arguments that can be used on an avocado-runner command
        :rtype: list
        """
        args = ['-i', str(self.identifier), '-j', str(self.job_id)]
        args += self.runnable.get_command_args()

        for status_service in self.status_services:
            args.append('-s')
            args.append(status_service.uri)

        return args

    def run(self):
        self.setup_output_dir()
        runner_klass = self.runnable.pick_runner_class()
        runner = runner_klass()
        for status in runner.run(self.runnable):
            if status['status'] == 'started':
                status.update({'output_dir': self.runnable.output_dir})
            status.update({"id": self.identifier})
            if self.job_id is not None:
                status.update({"job_id": self.job_id})
            for status_service in self.status_services:
                status_service.post(status)
            yield status
