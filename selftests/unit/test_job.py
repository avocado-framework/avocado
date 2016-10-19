import argparse
import sys
if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

from avocado.core import job
from avocado.utils import path as utils_path


class JobTest(unittest.TestCase):

    @staticmethod
    def _find_simple_test_candidates():
        simple_test_candidates = ['true', 'time', 'uptime']
        found = []
        for candidate in simple_test_candidates:
            try:
                found.append(utils_path.find_command(candidate))
            except utils_path.CmdNotFoundError:
                pass
        return found

    def test_job_empty_suite(self):
        args = argparse.Namespace()
        empty_job = job.Job(args)
        self.assertIsNone(empty_job.test_suite)

    def test_job_empty_has_id(self):
        args = argparse.Namespace()
        empty_job = job.Job(args)
        self.assertIsNotNone(empty_job.unique_id)

    def test_job_test_suite_not_created(self):
        args = argparse.Namespace()
        myjob = job.Job(args)
        self.assertIsNone(myjob.test_suite)

    def test_job_create_test_suite_empty(self):
        args = argparse.Namespace()
        myjob = job.Job(args)
        myjob.create_test_suite()
        self.assertEqual(myjob.test_suite, [])

    def test_job_create_test_suite_simple(self):
        simple_tests_found = self._find_simple_test_candidates()
        args = argparse.Namespace(url=simple_tests_found)
        myjob = job.Job(args)
        myjob.create_test_suite()
        self.assertEqual(len(simple_tests_found), len(myjob.test_suite))

if __name__ == '__main__':
    unittest.main()
