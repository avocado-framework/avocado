import argparse
import sys
if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

from avocado.core import job


class JobTest(unittest.TestCase):

    def test_job_empty_suite(self):
        args = argparse.Namespace()
        empty_job = job.Job(args)
        self.assertIsNone(empty_job.test_suite)

    def test_job_empty_has_id(self):
        args = argparse.Namespace()
        empty_job = job.Job(args)
        self.assertIsNotNone(empty_job.unique_id)
