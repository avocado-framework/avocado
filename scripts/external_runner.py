#!/usr/bin/env python

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; specifically version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2021
# Author: Cleber Rosa <cleber@redhat.com>
#         Beraldo Leal <bleal@redhat.com>

# Command line helper, wrap command line ops to avocado friendly way. Use this
# as the new external-runner.
#
# For more information, please execute:
#
#  $ avocado-external-runner -h
#
# Note: Here we are using "{uri}-{args[0]}" as the runnable identifier because
#       it will be suitable for most of the cases. However feel free to adapt
#       the "identifier_format" to your needs.

import argparse
import sys

from avocado.core.job import Job
from avocado.core.nrunner import Runnable
from avocado.core.suite import TestSuite
from avocado.utils.path import find_command


def main():

    epilog = """Examples:

    $ avocado-external-runner curl redhat.com
    $ avocado-external-runner curl "redhat.com -v" google.com

 Note: If you have multiple arguments please use quotes as in
 the example above.
 """

    parser = argparse.ArgumentParser(
        description="Process some integers.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=epilog,
    )
    parser.add_argument(
        "runner",
        metavar="RUNNER",
        type=str,
        help="The external runner to process the arguments.",
    )
    parser.add_argument(
        "args",
        metavar="ARGS",
        type=str,
        nargs="+",
        help=(
            "Arguments to be executed. If you have multiple "
            "arguments, please quote them."
        ),
    )

    args = parser.parse_args()
    tests = []
    for arg in args.args:
        runnable = Runnable.from_args(
            {"kind": "exec-test", "uri": find_command(args.runner), "arg": arg.split()}
        )
        tests.append(runnable)

    config = {"runner.identifier_format": "{uri}-{args[0]}"}
    suite = TestSuite(tests=tests, name="external-runner", config=config)
    with Job({}, [suite]) as j:
        sys.exit(j.run())


if __name__ == "__main__":
    main()
