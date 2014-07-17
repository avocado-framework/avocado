# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2014
# Authors: Cleber Rosa <cleber@redhat.com>

"""
Module that provides communication with GDB via its GDB/MI interpreter
"""

# prefixed with a "^"
RESULT_STATEMENTS = ["done",
                     "running",
                     "connected",
                     "error",
                     "exit"]

# prefixed with a "*"
ASYNC_STATE_STATEMENTS = ["running",
                          "stopped"]

# prefixed with a "="
ASYNC_OTHER_STATEMENTS = ["thread-group-added",
                          "thread-group-removed",
                          "thread-group-exited",
                          "thread-created",
                          "thread-exited",
                          "thread-selected",
                          "library-loaded",
                          "library-unloaded",
                          "traceframe-changed",
                          "tsv-created",
                          "tsv-deleted",
                          "tsv-modified",
                          "breakpoint-created",
                          "breakpoint-modified",
                          "breakpoint-deleted",
                          "record-started",
                          "record-stopped",
                          "cmd-param-changed",
                          "memory-changed"]

GDB_RECORD_KEYS = {'^': RESULT_STATEMENTS,
                   '*': ASYNC_STATE_STATEMENTS,
                   '=': ASYNC_OTHER_STATEMENTS,
                   '~': 'console_output',
                   '@': 'string_output',
                   '&': 'debugging_messages'}

GDB_PROMPT = '(gdb)'
GDB_EXIT = '^exit'

GDB_BREAK_CONTITIONS = [GDB_PROMPT, GDB_EXIT]

class UnknownKeyError(Exception):

    """
    Line contains a key that is unknown to the GDB/MI language
    """
    def __init__(self, key=None):
        self.key = key

    def __str__(self):
        if self.key is not None:
            msg = 'Key "%s" not recognized by GDB/MI parser' % self.key
        else:
            msg = 'Key not recognized by GDB/MI parser'
        return msg

def parse_line(line):
    """
    Parse a line, that is, a line that starts with
    """
    key = line[0]
    if key not in GDB_RECORD_KEYS:
        raise UnknownKeyError(key)

    value = GDB_RECORD_KEYS[key]
    if isinstance(value, list):
        allowed_statements = value
    else:
        allowed_statements = []

    line = line[1:]
    statement, args = line.split(',', 1)
    if allowed_statements:
        if statement not in allowed_statements:
            raise ValueError('Statement not recognized "%s"' % statement)

    return statement, args

def encode_cli_command(command):
    """
    Returns a regular GDB command

    :param command:

    """
    return '-interpreter-exec console "%s"' % command
