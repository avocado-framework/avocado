#!/bin/env python3

import os
import sys

from avocado.core.job import Job


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG = {
    'run.test_runner': 'nrunner',
    'nrun.references': [os.path.join(ROOT_DIR, 'selftests', 'unit'),
                        os.path.join(ROOT_DIR, 'selftests', 'functional')],
    'filter_by_tags': ['parallel:1'],
    # These are not currently supported by plugins/runner_nrunner.py, but better
    # be prepared
    'nrun.parallel_tasks': 1,
    'nrun.disable_task_randomization': True,
    }


if __name__ == '__main__':
    with Job(CONFIG) as j:
        os.environ['AVOCADO_CHECK_LEVEL'] = '3'
        sys.exit(j.run())
