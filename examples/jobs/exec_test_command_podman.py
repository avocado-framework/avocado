#!/usr/bin/env python3
import sys

from avocado.core.job import Job

job_config = {'resolver.references': ['/etc/fedora-release'],
              'resolver.exec_test.command': '/bin/cat',
              'nrunner.spawner': 'podman',
              'spawner.podman.image': 'fedora:rawhide',
              'run.test_runner': 'nrunner'}

with Job.from_config(job_config=job_config) as job:
    sys.exit(job.run())
