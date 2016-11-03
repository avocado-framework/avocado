import argparse
import os
import sys
if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

from avocado.core import exceptions
from avocado.core import test
from avocado.core import job
from avocado.core import exit_codes
from avocado.utils import path as utils_path


class JobTest(unittest.TestCase):

    @staticmethod
    def _find_simple_test_candidates(candidates=['true', 'time', 'uptime']):
        found = []
        for candidate in candidates:
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
        self.assertRaises(exceptions.OptionValidationError,
                          myjob.create_test_suite)

    def test_job_create_test_suite_simple(self):
        simple_tests_found = self._find_simple_test_candidates()
        args = argparse.Namespace(reference=simple_tests_found)
        myjob = job.Job(args)
        myjob.create_test_suite()
        self.assertEqual(len(simple_tests_found), len(myjob.test_suite))

    def test_job_pre_tests(self):
        class JobFilterTime(job.Job):
            def pre_tests(self):
                filtered_test_suite = []
                for test_factory in self.test_suite:
                    if test_factory[0] is test.SimpleTest:
                        if not test_factory[1].get('name', '').endswith('time'):
                            filtered_test_suite.append(test_factory)
                self.test_suite = filtered_test_suite
                super(JobFilterTime, self).pre_tests()
        simple_tests_found = self._find_simple_test_candidates()
        args = argparse.Namespace(reference=simple_tests_found)
        myjob = JobFilterTime(args)
        myjob.create_test_suite()
        myjob.pre_tests()
        self.assertLessEqual(len(myjob.test_suite), 1)

    def test_job_run_tests(self):
        simple_tests_found = self._find_simple_test_candidates(['true'])
        args = argparse.Namespace(reference=simple_tests_found)
        myjob = job.Job(args)
        myjob.create_test_suite()
        self.assertEqual(myjob.run_tests(),
                         exit_codes.AVOCADO_ALL_OK)

    def test_job_post_tests(self):
        class JobLogPost(job.Job):
            def post_tests(self):
                with open(os.path.join(self.logdir, "reversed_id"), "w") as f:
                    f.write(self.unique_id[::-1])
                super(JobLogPost, self).post_tests()
        simple_tests_found = self._find_simple_test_candidates()
        args = argparse.Namespace(reference=simple_tests_found)
        myjob = JobLogPost(args)
        myjob.create_test_suite()
        myjob.pre_tests()
        myjob.run_tests()
        myjob.post_tests()
        self.assertEqual(myjob.unique_id[::-1],
                         open(os.path.join(myjob.logdir, "reversed_id")).read())

    @unittest.skip("Issue described at https://trello.com/c/qgSTIK0Y")
    def test_job_run(self):
        class JobFilterLog(job.Job):
            def pre_tests(self):
                filtered_test_suite = []
                for test_factory in self.test_suite:
                    if test_factory[0] is test.SimpleTest:
                        if not test_factory[1].get('name', '').endswith('time'):
                            filtered_test_suite.append(test_factory)
                self.test_suite = filtered_test_suite
                super(JobFilterLog, self).pre_tests()

            def post_tests(self):
                with open(os.path.join(self.logdir, "reversed_id"), "w") as f:
                    f.write(self.unique_id[::-1])
                super(JobFilterLog, self).post_tests()
        simple_tests_found = self._find_simple_test_candidates()
        args = argparse.Namespace(reference=simple_tests_found)
        myjob = JobFilterLog(args)
        self.assertEqual(myjob.run(),
                         exit_codes.AVOCADO_ALL_OK)
        self.assertLessEqual(len(myjob.test_suite), 1)
        self.assertEqual(myjob.unique_id[::-1],
                         open(os.path.join(myjob.logdir, "reversed_id")).read())

if __name__ == '__main__':
    unittest.main()
