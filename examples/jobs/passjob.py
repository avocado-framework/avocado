#!/usr/bin/env python3
import sys

from avocado.core.job import Job

job_config = {'run.references': ['examples/tests/passtest.py:PassTest.test']}

# Automatic helper method (Avocado will try to discovery things from config
# dicts. Since there is magic here, we don't need to pass suite names or suites,
# and test/task id will be prepend with the suite index (in this case 1 and 2)

with Job.from_config(job_config=job_config) as job:
    sys.exit(job.run())
