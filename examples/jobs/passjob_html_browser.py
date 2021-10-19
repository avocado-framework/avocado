#!/usr/bin/env python3

import sys

from avocado.core.job import Job
from avocado.core.suite import TestSuite

config = {'resolver.references': ['examples/tests/passtest.py:PassTest.test'],
          'job.run.result.html.enabled': True,
          'job.run.result.html.open_browser': True}

suite = TestSuite.from_config(config)
with Job(config, [suite]) as j:
    sys.exit(j.run())
