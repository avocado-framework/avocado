#: Builtin special keywords to enable set of logging streams
BUILTIN_STREAMS = {'app': 'application output',
                   'test': 'test output',
                   'debug': 'tracebacks and other debugging info',
                   'early':  ('early logging of other streams, including test '
                              '(very verbose)')}

#: Groups of builtin streams
BUILTIN_STREAM_SETS = {'all': 'all builtin streams',
                       'none': ('disables regular output (leaving only errors '
                                'enabled)')}
