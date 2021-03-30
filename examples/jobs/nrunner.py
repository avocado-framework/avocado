#!/usr/bin/env python3

import sys

from avocado.core.job import Job
from avocado.core.suite import TestSuite
from avocado.utils.network.ports import find_free_port

status_server = '127.0.0.1:%u' % find_free_port()

config = {
    'run.test_runner': 'nrunner',
    'nrunner.status_server_listen': status_server,
    'nrunner.status_server_uri': status_server,
    'run.references': [
        'selftests/unit/plugin/test_resolver.py',
        'selftests/functional/test_argument_parsing.py',
        '/bin/true',
    ],
    }

suite = TestSuite.from_config(config)
with Job(config, [suite]) as j:
    sys.exit(j.run())
