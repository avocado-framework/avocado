#!/usr/bin/env python3

import os
import sys
import tempfile

from avocado.core.job import Job
from avocado.core.suite import TestSuite

status_server_dir = tempfile.TemporaryDirectory()
status_server = os.path.join(status_server_dir.name, "status_server.socket")

test_results_dir = tempfile.TemporaryDirectory()

config = {
    "run.results_dir": test_results_dir.name,
    "run.status_server_auto": False,
    "run.status_server_listen": status_server,
    "run.status_server_uri": status_server,
    "resolver.references": ["examples/tests/passtest.py"],
}

suite = TestSuite.from_config(config, name="1")
with Job(config, [suite]) as j:
    result = j.run()
    test_results_dir.cleanup()

# Check that one test actually ran and results were recorded. The
# test's success will be checked by the job execution result
assert len(j.result.tests) == 1

status_server_dir.cleanup()
sys.exit(result)
