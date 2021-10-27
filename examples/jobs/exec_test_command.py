#!/usr/bin/env python3
import sys

from avocado.core.job import Job

job_config = {'resolver.references': ['https://avocado-project.org'],
              'resolver.exec_test.command': '/usr/bin/curl',
              'run.test_runner': 'nrunner'}

with Job.from_config(job_config=job_config) as job:
    sys.exit(job.run())
