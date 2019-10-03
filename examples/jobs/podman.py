#!/usr/bin/env python3

import sys
from avocado.core.job import Job

config = {'references': ['/bin/true'],
          'test_runner': 'docker',
          'docker': 'ldoktor/fedora-avocado',
          'docker_cmd': 'podman',
          'docker_options': '',
          'docker_no_cleanup': False}

with Job(config) as j:
    sys.exit(j.run())
