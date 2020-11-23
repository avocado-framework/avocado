#!/usr/bin/env python3

import sys

from avocado.core.job import Job
from avocado.core.suite import TestSuite

config = {'run.references': ['examples/tests/passtest.py:PassTest.test'],
          'job.run.result.html.enabled': True}

suite = TestSuite.from_config(config)
with Job(config, [suite]) as j:
    sys.exit(j.run())
