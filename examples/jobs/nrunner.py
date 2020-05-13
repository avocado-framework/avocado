#!/usr/bin/env python3

import sys
from avocado.core.job import Job

config = {
    'run.test_runner': 'nrunner',
    'run.references': [
        'selftests/unit/test_resolver.py',
        'selftests/functional/test_argument_parsing.py',
        '/bin/true',
        '/bin/false',
    ],
    }

with Job(config) as j:
    sys.exit(j.run())
