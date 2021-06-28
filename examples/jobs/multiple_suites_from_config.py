#!/usr/bin/env python3

import sys

from avocado.core.job import Job
from avocado.core.suite import TestSuite

JOB_CONFIG = {'run.test_runner': 'nrunner'}

ORDERLY_CONFIG = {'run.test_runner': 'nrunner',
                  'run.references': ['/bin/true', '/bin/true', '/bin/last'],
                  'nrunner.max_parallel_tasks': 1}

RANDOM_CONFIG = {'run.test_runner': 'nrunner',
                 'run.references': ['/bin/true', '/bin/true', '/bin/true',
                                    '/bin/true', '/bin/true', '/bin/last'],
                 'nrunner.shuffle': True,
                 'nrunner.max_parallel_tasks': 3}

with Job(JOB_CONFIG,
         [TestSuite.from_config(ORDERLY_CONFIG, name='orderly'),
          TestSuite.from_config(RANDOM_CONFIG, name='random')]) as j:
    sys.exit(j.run())
