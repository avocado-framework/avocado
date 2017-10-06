import argparse
import shutil
import unittest

try:
    from unittest import mock
except ImportError:
    import mock

from avocado.core.job import Job
from avocado.core import version
from avocado.utils import process
import avocado_runner_remote


JSON_RESULTS = ('Something other than json\n'
                '{"tests": [{"test": "1-sleeptest;0",'
                '"reference": "sleeptest", '
                '"fail_reason": "None", '
                '"status": "PASS", "time": 1.23, "start": 0, "end": 1.23}],'
                '"debuglog": "/home/user/avocado/logs/run-2014-05-26-15.45.'
                '37/debug.log", "errors": 0, "skip": 0, "time": 1.4, '
                '"logdir": "/local/path/test-results/sleeptest", '
                '"logdir": "/local/path/test-results/sleeptest", '
                '"start": 0, "end": 1.4, "pass": 1, "failures": 0, "total": '
                '1}\nAdditional stuff other than json')


class RemoteTestRunnerTest(unittest.TestCase):

    """ Tests RemoteTestRunner """

    def test_run_suite(self):
        """
        Test RemoteTestRunner.run_suite()

        The general idea of this test is to:

        1) Create the machinery necessary to get a RemoteTestRunner
           setup inside a job, or looking at it the other way around, to
           have a runner that is created with a valid job.

        2) Mock the interactions with a remote host.  This is done here
           basically by mocking 'Remote' and 'fabric' usage.

        3) Provide a polluted JSON to be parsed by the RemoteTestRunner

        4) Assert that those results are properly parsed into the
           job's result
        """
        job_args = argparse.Namespace(test_result_total=1,
                                      remote_username='username',
                                      remote_hostname='hostname',
                                      remote_port=22,
                                      remote_password='password',
                                      remote_key_file=None,
                                      remote_timeout=60,
                                      show_job_log=False,
                                      mux_yaml=['~/avocado/tests/foo.yaml',
                                                '~/avocado/tests/bar/baz.yaml'],
                                      dry_run=True,
                                      env_keep=None,
                                      reference=['/tests/sleeptest.py',
                                                 '/tests/other/test',
                                                 'passtest.py'])

        try:
            job = Job(job_args)
            runner = avocado_runner_remote.RemoteTestRunner(job, job.result)
            return_value = (True, (version.MAJOR, version.MINOR))
            runner.check_remote_avocado = mock.Mock(return_value=return_value)

            # These are mocked at their source, and will prevent fabric from
            # trying to contact remote hosts
            with mock.patch('avocado_runner_remote.Remote'):
                runner.remote = avocado_runner_remote.Remote(job_args.remote_hostname)

                # This is the result that the run_suite() will get from remote.run
                remote_run_result = process.CmdResult()
                remote_run_result.stdout = JSON_RESULTS
                remote_run_result.exit_status = 0
                runner.remote.run = mock.Mock(return_value=remote_run_result)

                # We have to fake the uncompressing and removal of the zip
                # archive that was never generated on the "remote" end
                # This test could be expand by mocking creating an actual
                # zip file instead, but it's really overkill
                with mock.patch('avocado_runner_remote.archive.uncompress'):
                    with mock.patch('avocado_runner_remote.os.remove'):
                        runner.run_suite(None, None, 61)

            # The job was created with dry_run so it should have a zeroed id
            self.assertEqual(job.result.job_unique_id, '0' * 40)
            self.assertEqual(job.result.tests_run, 1)
            self.assertEqual(job.result.passed, 1)
            cmd_line = ('avocado run --force-job-id '
                        '0000000000000000000000000000000000000000 --json - '
                        '--archive /tests/sleeptest.py /tests/other/test '
                        'passtest.py -m ~/avocado/tests/foo.yaml '
                        '~/avocado/tests/bar/baz.yaml --dry-run')
            runner.remote.run.assert_called_with(cmd_line,
                                                 ignore_status=True,
                                                 timeout=61)
        finally:
            shutil.rmtree(job.args.base_logdir)


if __name__ == '__main__':
    unittest.main()
