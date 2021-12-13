#: All known runner commands, capable of being used by a
#: SpawnMethod.STANDALONE_EXECUTABLE compatible spawners
RUNNERS_REGISTRY_STANDALONE_EXECUTABLE = {}

#: All known runner Python classes.  This is a dictionary keyed by a
#: runnable kind, and value is a class that inherits from
#: :class:`BaseRunner`.  Suitable for spawners compatible with
#: SpawnMethod.PYTHON_CLASS
RUNNERS_REGISTRY_PYTHON_CLASS = {}
