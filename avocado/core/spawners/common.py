import enum


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


class BaseSpawner:
    """Defines an interface to be followed by all implementations."""

    METHODS = []

    @staticmethod
    def is_task_alive(task):
        pass

    def spawn_task(self, task):
        pass
