#!/usr/bin/env python3

import sys

from avocado.core.job import Job
from avocado.core.suite import TestSuite

config = {
    'run.test_runner': 'nrunner',
    'nrunner.status_server_uri': '127.0.0.1:9999',
    'run.references': [
        'selftests/unit/test_resolver.py',
        'selftests/functional/test_argument_parsing.py',
        '/bin/true',
    ],
    }

suite = TestSuite.from_config(config)
with Job(config, [suite]) as j:
    sys.exit(j.run())
