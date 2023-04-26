import enum

from avocado.core.settings import settings


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
        return runtime_task.task.runnable.output_dir
