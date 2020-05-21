#!/usr/bin/env python3

import sys
from avocado.core.job import Job

config = {'run.references': ['examples/tests/passtest.py:PassTest.test'],
          'run.html_job_result': 'on',
          'run.open_browser': True}

with Job(config) as j:
    sys.exit(j.run())
