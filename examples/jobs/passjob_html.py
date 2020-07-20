#!/usr/bin/env python3

import sys

from avocado.core.job import Job

config = {'run.references': ['examples/tests/passtest.py:PassTest.test'],
          'job.run.result.html.enabled': 'on',
          'run.open_browser': True}

with Job(config) as j:
    sys.exit(j.run())
