import enum
import os

from avocado.core.settings import settings
from avocado.core.spawners.exceptions import SpawnerException


class SpawnMethod(enum.Enum):
    """The method employed to spawn a runnable or task."""

    #: Spawns by running executing Python code, that is, having access to
    #: a runnable or task instance, it calls its run() method.
    PYTHON_CLASS = object()
    #: Spawns by running a command, that is having either a path to an
    #: executable or a list of arguments, it calls a function that will
    #: execute that command (such as with os.system())
    STANDALONE_EXECUTABLE = object()
    #: Spawns with any method available, that is, it doesn't declare or
    #: require a specific spawn method
    ANY = object()


class SpawnerMixin:
    """Common utilities for Spawner implementations."""

    METHODS = []

    def __init__(self, config=None, job=None):
        if config is None:
            config = settings.as_dict()
        self.config = config
        self._job = job

    def task_output_dir(self, runtime_task):
        if self._job is None:
            raise SpawnerException("Job wasn't set properly")
        return os.path.join(
            self._job.test_results_path, runtime_task.task.identifier.str_filesystem
        )
