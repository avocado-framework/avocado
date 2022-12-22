#!/usr/bin/env python3
import sys
import tempfile

from avocado.core.job import Job

test_results_dir = tempfile.TemporaryDirectory()

job_config = {
    "run.results_dir": test_results_dir.name,
    "resolver.references": ["examples/tests/passtest.py:PassTest.test"],
}

# Automatic helper method (Avocado will try to discovery things from config
# dicts. Since there is magic here, we don't need to pass suite names or suites,
# and test/task id will be prepend with the suite index (in this case 1 and 2)

with Job.from_config(job_config=job_config) as job:
    exit_code = job.run()
    test_results_dir.cleanup()
    sys.exit(exit_code)
