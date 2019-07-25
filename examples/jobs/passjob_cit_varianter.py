#!/usr/bin/env python3

import sys
from avocado.core.job import Job

config = {'references': ['examples/tests/passtest.py:PassTest.test'],
          'cit_parameter_file': 'examples/varianter_cit/test_params.cit'}

with Job(config) as j:
    sys.exit(j.run())
