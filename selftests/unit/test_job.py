import logging
import os
import tempfile
import unittest.mock

from avocado.core import data_dir, exit_codes, job, nrunner, test
from avocado.core.exceptions import JobBaseException
from avocado.core.suite import TestSuite, TestSuiteStatus
from avocado.utils import path as utils_path

from .. import setup_avocado_loggers, temp_dir_prefix

setup_avocado_loggers()


class JobTest(unittest.TestCase):

    def setUp(self):
        self.job = None
        data_dir._tmp_tracker.unittest_refresh_dir_tracker()
        prefix = temp_dir_prefix(__name__, self, 'setUp')
        self.tmpdir = tempfile.TemporaryDirectory(prefix=prefix)

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
        config = {'job.output.loglevel': 'DEBUG',
                  'run.results_dir': self.tmpdir.name,
                  'run.store_logging_stream': [],
                  'core.show': ['none']}
        self.job = job.Job(config)
        # Job without setup called
        self.assertIsNone(self.job.logdir)
        self.assertIsNone(self.job.logfile)
        self.assertIsNone(self.job.replay_sourcejob)
        self.assertIsNone(self.job.result)
        self.assertIsNone(self.job.test_suite)
        self.assertIsNone(self.job.tmpdir)
        self.assertTrue(self.job._Job__keep_tmpdir)
        self.assertEqual(self.job.exitcode, exit_codes.AVOCADO_ALL_OK)
        self.assertEqual(self.job.status, "RUNNING")
        for cfg, value in config.items():
            self.assertEqual(self.job.config[cfg], value)
        uid = self.job.unique_id

        # Job with setup called
        self.job.setup()
        self.assertIsNotNone(self.job.logdir)
        self.assertIsNotNone(self.job.logfile)
        self.assertIsNotNone(self.job.result)
        self.assertIsNotNone(self.job.tmpdir)
        self.assertFalse(self.job._Job__keep_tmpdir)
        self.assertEqual(uid, self.job.unique_id)
        self.assertEqual(self.job.status, "RUNNING")

        # Calling setup twice
        self.assertRaises(AssertionError, self.job.setup)

        # Job with cleanup called
        self.job.cleanup()

    def test_job_empty_has_id(self):
        config = {'run.results_dir': self.tmpdir.name,
                  'core.show': ['none']}
        self.job = job.Job(config)
        self.assertIsNotNone(self.job.unique_id)

    def test_two_jobs(self):
        config = {'run.results_dir': self.tmpdir.name,
                  'run.store_logging_stream': [],
                  'core.show': ['none']}
        with job.Job(config) as self.job, job.Job(config) as job2:
            job1 = self.job
            # uids, logdirs and tmpdirs must be different
            self.assertNotEqual(job1.unique_id, job2.unique_id)
            self.assertNotEqual(job1.logdir, job2.logdir)
            self.assertNotEqual(job1.tmpdir, job2.tmpdir)
            # tmpdirs should share the same base-dir per process
            self.assertEqual(os.path.dirname(job1.tmpdir), os.path.dirname(job2.tmpdir))
            # due to config logdirs should share the same base-dir
            self.assertEqual(os.path.dirname(job1.logdir), os.path.dirname(job2.logdir))

    def test_job_test_suite_not_created(self):
        config = {'run.results_dir': self.tmpdir.name,
                  'core.show': ['none']}
        self.job = job.Job(config)
        self.assertIsNone(self.job.test_suite)

    def test_suite_not_started(self):
        suite = TestSuite('empty-suite', {'run.test_runner': 'nrunner'})
        self.assertEqual(suite.status, TestSuiteStatus.RESOLUTION_NOT_STARTED)

    def test_suite_tests_found(self):
        suite = TestSuite.from_config({'run.references': ['/bin/true'],
                                       'run.test_runner': 'nrunner'})
        self.assertEqual(suite.status, TestSuiteStatus.TESTS_FOUND)

    def test_suite_tests_not_found(self):
        suite = TestSuite.from_config({'run.references': ['/bin/not-found'],
                                       'run.test_runner': 'nrunner',
                                       'run.ignore_missing_references': True})
        self.assertEqual(suite.status, TestSuiteStatus.TESTS_NOT_FOUND)

    def test_job_create_test_suite_empty(self):
        config = {'run.results_dir': self.tmpdir.name,
                  'run.store_logging_stream': [],
                  'core.show': ['none']}
        self.job = job.Job(config)
        self.job.setup()
        with self.assertRaises(JobBaseException):
            self.job.create_test_suite()

    def test_job_create_test_suite_simple(self):
        simple_tests_found = self._find_simple_test_candidates()
        config = {'core.show': ['none'],
                  'run.results_dir': self.tmpdir.name,
                  'run.store_logging_stream': [],
                  'run.references': simple_tests_found}
        self.job = job.Job.from_config(config)
        self.job.setup()
        self.assertEqual(len(simple_tests_found), len(self.job.test_suites[0]))

    def test_job_pre_tests(self):
        class JobFilterTime(job.Job):
            def pre_tests(self):
                filtered_test_suite = []
                for test_factory in self.test_suite.tests:
                    if self.config.get('run.test_runner') == 'runner':
                        if test_factory[0] is test.SimpleTest:
                            if not test_factory[1].get('name', '').endswith('time'):
                                filtered_test_suite.append(test_factory)
                    elif self.config.get('run.test_runner') == 'nrunner':
                        task = test_factory
                        if not task.runnable.url.endswith('time'):
                            filtered_test_suite.append(test_factory)
                self.test_suite.tests = filtered_test_suite
                super(JobFilterTime, self).pre_tests()
        simple_tests_found = self._find_simple_test_candidates()
        config = {'core.show': ['none'],
                  'run.results_dir': self.tmpdir.name,
                  'run.store_logging_stream': [],
                  'run.references': simple_tests_found}
        self.job = JobFilterTime.from_config(config)
        self.job.setup()
        try:
            self.job.pre_tests()
        finally:
            self.job.post_tests()
        self.assertLessEqual(len(self.job.test_suite), 1)

    def test_job_run_tests(self):
        simple_tests_found = self._find_simple_test_candidates(['true'])
        config = {'core.show': ['none'],
                  'run.results_dir': self.tmpdir.name,
                  'run.store_logging_stream': [],
                  'run.references': simple_tests_found}
        self.job = job.Job.from_config(config)
        self.job.setup()
        self.assertEqual(self.job.run_tests(),
                         exit_codes.AVOCADO_ALL_OK)

    def test_job_post_tests(self):
        class JobLogPost(job.Job):
            def post_tests(self):
                with open(os.path.join(self.logdir, "reversed_id"), "w") as f:
                    f.write(self.unique_id[::-1])
                super(JobLogPost, self).post_tests()
        simple_tests_found = self._find_simple_test_candidates()
        config = {'core.show': ['none'],
                  'run.results_dir': self.tmpdir.name,
                  'run.store_logging_stream': [],
                  'run.references': simple_tests_found}
        self.job = JobLogPost(config)
        self.job.setup()
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
                for suite in self.test_suites:
                    filtered_test_suite = []
                    for test_factory in suite.tests:
                        if self.config.get('run.test_runner') == 'runner':
                            if test_factory[0] is test.SimpleTest:
                                if not test_factory[1].get('name', '').endswith('time'):
                                    filtered_test_suite.append(test_factory)
                        elif self.config.get('run.test_runner') == 'nrunner':
                            task = test_factory
                            if not task.runnable.url.endswith('time'):
                                filtered_test_suite.append(test_factory)
                    suite.tests = filtered_test_suite
                    super(JobFilterLog, self).pre_tests()

            def post_tests(self):
                with open(os.path.join(self.logdir, "reversed_id"), "w") as f:
                    f.write(self.unique_id[::-1])
                super(JobFilterLog, self).post_tests()
        simple_tests_found = self._find_simple_test_candidates()
        config = {'core.show': ['none'],
                  'run.results_dir': self.tmpdir.name,
                  'run.store_logging_stream': [],
                  'run.references': simple_tests_found}
        self.job = JobFilterLog.from_config(config)
        self.job.setup()
        self.assertEqual(self.job.run(),
                         exit_codes.AVOCADO_ALL_OK)
        self.assertLessEqual(len(self.job.test_suites), 1)
        with open(os.path.join(self.job.logdir, "reversed_id")) as reverse_id_file:
            self.assertEqual(self.job.unique_id[::-1],
                             reverse_id_file.read())

    def test_job_run_account_time(self):
        config = {'core.show': ['none'],
                  'run.results_dir': self.tmpdir.name,
                  'run.store_logging_stream': []}
        self.job = job.Job(config)
        self.job.setup()
        # temporarily disable logging on console
        logging.disable(logging.ERROR)
        self.job.run()
        logging.disable(logging.NOTSET)
        self.assertNotEqual(self.job.time_start, -1)
        self.assertNotEqual(self.job.time_end, -1)
        self.assertNotEqual(self.job.time_elapsed, -1)

    def test_job_self_account_time(self):
        config = {'core.show': ['none'],
                  'run.results_dir': self.tmpdir.name,
                  'run.store_logging_stream': []}
        self.job = job.Job(config)
        self.job.setup()
        self.job.time_start = 10.0
        # temporarily disable logging on console
        logging.disable(logging.ERROR)
        self.job.run()
        logging.disable(logging.NOTSET)
        self.job.time_end = 20.0
        # forcing a different value to check if it's not being
        # calculated when time_start or time_end are manually set
        self.job.time_elapsed = 100.0
        self.assertEqual(self.job.time_start, 10.0)
        self.assertEqual(self.job.time_end, 20.0)
        self.assertEqual(self.job.time_elapsed, 100.0)

    def test_job_suites_config(self):
        config = {'run.results_dir': self.tmpdir.name,
                  'core.show': ['none'],
                  'run.references': ['/bin/true']}

        suite_config = {'run.references': ['/bin/false']}
        self.job = job.Job.from_config(config, [suite_config])
        self.assertEqual(self.job.config.get('run.references'), ['/bin/true'])

    def test_job_dryrun_no_unique_job_id(self):
        config = {'run.results_dir': self.tmpdir.name,
                  'run.store_logging_stream': [],
                  'run.dry_run.enabled': True,
                  'core.show': ['none']}
        self.job = job.Job(config)
        self.job.setup()
        self.assertIsNotNone(self.job.config.get('run.unique_job_id'))

    def test_job_no_base_logdir(self):
        config = {'core.show': ['none'],
                  'run.store_logging_stream': []}
        with unittest.mock.patch('avocado.core.job.data_dir.get_logs_dir',
                                 return_value=self.tmpdir.name):
            self.job = job.Job(config)
            self.job.setup()
        self.assertTrue(os.path.isdir(self.job.logdir))
        self.assertEqual(os.path.dirname(self.job.logdir), self.tmpdir.name)
        self.assertTrue(os.path.isfile(os.path.join(self.job.logdir, 'id')))

    def test_job_dryrun_no_base_logdir(self):
        config = {'core.show': ['none'],
                  'run.store_logging_stream': [],
                  'run.dry_run.enabled': True}
        self.job = job.Job(config)
        with self.job:
            self.assertTrue(os.path.isdir(self.job.logdir))
            self.assertTrue(os.path.isfile(os.path.join(self.job.logdir, 'id')))
        self.assertFalse(os.path.isdir(self.job.logdir))

    def test_job_make_test_suite_resolver(self):
        simple_tests_found = self._find_simple_test_candidates()
        config = {'run.results_dir': self.tmpdir.name,
                  'run.store_logging_stream': [],
                  'run.references': simple_tests_found,
                  'run.test_runner': 'nrunner',
                  'core.show': ['none']}
        self.job = job.Job.from_config(config)
        self.job.setup()
        self.assertEqual(len(simple_tests_found), len(self.job.test_suite))
        if self.job.test_suite:
            self.assertIsInstance(self.job.test_suite.tests[0], nrunner.Task)

    def tearDown(self):
        data_dir._tmp_tracker.unittest_refresh_dir_tracker()
        self.tmpdir.cleanup()
        if self.job is not None:
            self.job.cleanup()


if __name__ == '__main__':
    unittest.main()
