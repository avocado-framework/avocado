import argparse
import os
import shutil
import tempfile
import unittest

try:
    from unittest import mock
except ImportError:
    import mock

from avocado.core import data_dir
from avocado.core import exceptions
from avocado.core import exit_codes
from avocado.core import job
from avocado.core import test
from avocado.utils import path as utils_path


class JobTest(unittest.TestCase):

    def setUp(self):
        self.job = None
        data_dir._tmp_tracker.unittest_refresh_dir_tracker()
        self.tmpdir = tempfile.mkdtemp(prefix="avocado_" + __name__)

    @staticmethod
    def _find_simple_test_candidates(candidates=None):
        if candidates is None:
            candidates = ['true', 'time', 'uptime']
        found = []
        for candidate in candidates:
            try:
                found.append(utils_path.find_command(candidate))
            except utils_path.CmdNotFoundError:
                pass
        return found

    def test_job_empty_suite(self):
        args = argparse.Namespace(base_logdir=self.tmpdir)
        self.job = job.Job(args)
        self.assertIsNone(self.job.test_suite)

    def test_job_empty_has_id(self):
        args = argparse.Namespace(base_logdir=self.tmpdir)
        self.job = job.Job(args)
        self.assertIsNotNone(self.job.unique_id)

    def test_two_jobs(self):
        args = argparse.Namespace(base_logdir=self.tmpdir)
        self.job = job1 = job.Job(args)
        job2 = None
        try:
            job2 = job.Job(args)
            # uids, logdirs and tmpdirs must be different
            self.assertNotEqual(job1.unique_id, job2.unique_id)
            self.assertNotEqual(job1.logdir, job2.logdir)
            self.assertNotEqual(job1.tmpdir, job2.tmpdir)
            # tmpdirs should share the same base-dir per process
            self.assertEqual(os.path.dirname(job1.tmpdir), os.path.dirname(job2.tmpdir))
            # due to args logdirs should share the same base-dir
            self.assertEqual(os.path.dirname(job1.logdir), os.path.dirname(job2.logdir))
        finally:
            job2.cleanup()

    def test_job_test_suite_not_created(self):
        args = argparse.Namespace(base_logdir=self.tmpdir)
        self.job = job.Job(args)
        self.assertIsNone(self.job.test_suite)

    def test_job_create_test_suite_empty(self):
        args = argparse.Namespace(base_logdir=self.tmpdir)
        self.job = job.Job(args)
        self.assertRaises(exceptions.OptionValidationError,
                          self.job.create_test_suite)

    def test_job_create_test_suite_simple(self):
        simple_tests_found = self._find_simple_test_candidates()
        args = argparse.Namespace(reference=simple_tests_found,
                                  base_logdir=self.tmpdir)
        self.job = job.Job(args)
        self.job.create_test_suite()
        self.assertEqual(len(simple_tests_found), len(self.job.test_suite))

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
        args = argparse.Namespace(reference=simple_tests_found,
                                  base_logdir=self.tmpdir)
        self.job = JobFilterTime(args)
        self.job.create_test_suite()
        try:
            self.job.pre_tests()
        finally:
            self.job.post_tests()
        self.assertLessEqual(len(self.job.test_suite), 1)

    def test_job_run_tests(self):
        simple_tests_found = self._find_simple_test_candidates(['true'])
        args = argparse.Namespace(reference=simple_tests_found,
                                  base_logdir=self.tmpdir)
        self.job = job.Job(args)
        self.job.create_test_suite()
        self.assertEqual(self.job.run_tests(),
                         exit_codes.AVOCADO_ALL_OK)

    def test_job_post_tests(self):
        class JobLogPost(job.Job):
            def post_tests(self):
                with open(os.path.join(self.logdir, "reversed_id"), "w") as f:
                    f.write(self.unique_id[::-1])
                super(JobLogPost, self).post_tests()
        simple_tests_found = self._find_simple_test_candidates()
        args = argparse.Namespace(reference=simple_tests_found,
                                  base_logdir=self.tmpdir)
        self.job = JobLogPost(args)
        self.job.create_test_suite()
        try:
            self.job.pre_tests()
            self.job.run_tests()
        finally:
            self.job.post_tests()
        with open(os.path.join(self.job.logdir, "reversed_id")) as reverse_id_file:
            self.assertEqual(self.job.unique_id[::-1],
                             reverse_id_file.read())

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
        args = argparse.Namespace(reference=simple_tests_found,
                                  base_logdir=self.tmpdir)
        self.job = JobFilterLog(args)
        self.assertEqual(self.job.run(),
                         exit_codes.AVOCADO_ALL_OK)
        self.assertLessEqual(len(self.job.test_suite), 1)
        with open(os.path.join(self.job.logdir, "reversed_id")) as reverse_id_file:
            self.assertEqual(self.job.unique_id[::-1],
                             reverse_id_file.read())

    def test_job_run_account_time(self):
        args = argparse.Namespace(base_logdir=self.tmpdir)
        self.job = job.Job(args)
        self.job.run()
        self.assertNotEqual(self.job.time_start, -1)
        self.assertNotEqual(self.job.time_end, -1)
        self.assertNotEqual(self.job.time_elapsed, -1)

    def test_job_self_account_time(self):
        args = argparse.Namespace(base_logdir=self.tmpdir)
        self.job = job.Job(args)
        self.job.time_start = 10.0
        self.job.run()
        self.job.time_end = 20.0
        # forcing a different value to check if it's not being
        # calculated when time_start or time_end are manually set
        self.job.time_elapsed = 100.0
        self.assertEqual(self.job.time_start, 10.0)
        self.assertEqual(self.job.time_end, 20.0)
        self.assertEqual(self.job.time_elapsed, 100.0)

    def test_job_dryrun_no_unique_job_id(self):
        args = argparse.Namespace(dry_run=True, base_logdir=self.tmpdir)
        self.job = job.Job(args)
        self.assertIsNotNone(self.job.args.unique_job_id)

    def test_job_no_base_logdir(self):
        args = argparse.Namespace()
        with mock.patch('avocado.core.job.data_dir.get_logs_dir',
                        return_value=self.tmpdir):
            self.job = job.Job(args)
        self.assertTrue(os.path.isdir(self.job.logdir))
        self.assertEqual(os.path.dirname(self.job.logdir), self.tmpdir)
        self.assertTrue(os.path.isfile(os.path.join(self.job.logdir, 'id')))

    def test_job_dryrun_no_base_logdir(self):
        args = argparse.Namespace(dry_run=True)
        self.job = job.Job(args)
        try:
            self.assertTrue(os.path.isdir(self.job.logdir))
            self.assertTrue(os.path.isfile(os.path.join(self.job.logdir, 'id')))
        finally:
            shutil.rmtree(self.job.args.base_logdir)

    def tearDown(self):
        data_dir._tmp_tracker.unittest_refresh_dir_tracker()
        shutil.rmtree(self.tmpdir)
        if self.job is not None:
            self.job.cleanup()


if __name__ == '__main__':
    unittest.main()
