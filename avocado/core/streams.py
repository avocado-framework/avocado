#: Builtin special keywords to enable set of logging streams
BUILTIN_STREAMS = {
    "app": "avocado.app",
    "test": "avocado.test",
    "job": "avocado.job",
    "early": "avocado",
}

BUILTIN_STREAMS_DESCRIPTION = {
    "app": "application output",
    "test": "test output",
    "job": "job output",
    "early": ("early logging of other streams, including test " "(very verbose)"),
}

#: Groups of builtin streams
BUILTIN_STREAM_SETS = {
    "all": "all builtin streams",
    "none": ("disables regular output (leaving only errors " "enabled)"),
}
