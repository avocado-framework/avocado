#!/usr/bin/env python3
#
# command line helper, wrap command line ops to avocado friendly way
#
# Example: avocado-run-inplace.py dnf update -y
#

import sys

from avocado.core.job import Job
from avocado.core.nrunner import Runnable
from avocado.core.suite import TestSuite
from avocado.utils.path import find_command


def create_runnable_from_command(command_parts):
    executable = find_command(command_parts[0])
    return Runnable('exec-test',
                    executable,
                    *command_parts[1:])


if __name__ == '__main__':
    command = sys.argv[1:]
    if not command:
        print("ERROR: no command given", file=sys.stderr)
        sys.exit(2)

    suite = TestSuite(tests=[create_runnable_from_command(command)],
                      name="")
    with Job({}, [suite]) as j:
        sys.exit(j.run())
