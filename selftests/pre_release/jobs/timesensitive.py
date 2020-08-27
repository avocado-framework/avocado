#!/bin/env python3

import os
import sys

from avocado.core.job import Job

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(THIS_DIR)))


CONFIG = {
    'run.test_runner': 'nrunner',
    'run.references': [os.path.join(ROOT_DIR, 'selftests', 'unit'),
                       os.path.join(ROOT_DIR, 'selftests', 'functional')],
    'filter.by_tags.tags': ['parallel:1'],
    'nrunner.status_server_uri': '127.0.0.1:8888',
    'nrunner.max_parallel_tasks': 1,
    }


if __name__ == '__main__':
    with Job.from_config(CONFIG) as j:
        os.environ['AVOCADO_CHECK_LEVEL'] = '3'
        sys.exit(j.run())
