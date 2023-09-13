#!/usr/bin/env python3

import sys

from avocado.core.job import Job

config = {"resolver.references": ["examples/tests/failtest.py:FailTest.test"]}

with Job.from_config(job_config=config) as j:
    sys.exit(j.run())
