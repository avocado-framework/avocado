#!/usr/bin/env python

import unittest

from flexmock import flexmock, flexmock_teardown

from avocado.plugins import remote


JSON_RESULTS = ('Something other than json\n'
                '{"tests": [{"test": "sleeptest.1", "url": "sleeptest", '
                '"status": "PASS", "time": 1.23, "start": 0, "end": 1.23}],'
                '"debuglog": "/home/user/avocado/logs/run-2014-05-26-15.45.'
                '37/debug.log", "errors": 0, "skip": 0, "time": 1.4, '
                '"start": 0, "end": 1.4, "pass": 1, "failures": 0, "total": '
                '1}\nAdditional stuff other than json')


class RemoteTestRunnerTest(unittest.TestCase):

    """ Tests RemoteTestRunner """

    def setUp(self):
        flexmock(remote.RemoteTestRunner).should_receive('__init__')
        self.remote = remote.RemoteTestRunner(None, None)
        test_results = flexmock(stdout=JSON_RESULTS)
        stream = flexmock(job_unique_id='sleeptest.1',
                          debuglog='/local/path/dirname')
        Remote = flexmock()
        args = ("cd ~/avocado/tests; avocado run --force-job-id sleeptest.1 "
                "--json - --archive sleeptest")
        (Remote.should_receive('run').with_args(args, ignore_status=True)
         .once().and_return(test_results))
        Results = flexmock(remote=Remote, urls=['sleeptest'],
                           stream=stream)
        Results.should_receive('setup').once().ordered()
        Results.should_receive('start_tests').once().ordered()
        args = {'status': u'PASS', 'whiteboard': '', 'time_start': 0,
                'name': u'sleeptest.1', 'class_name': 'RemoteTest',
                'traceback': 'Not supported yet',
                'text_output': 'Not supported yet', 'time_end': 1.23,
                'tagged_name': u'sleeptest.1', 'time_elapsed': 1.23,
                'fail_class': 'Not supported yet', 'job_unique_id': '',
                'fail_reason': 'Not supported yet'}
        Results.should_receive('start_test').once().with_args(args).ordered()
        Results.should_receive('check_test').once().with_args(args).ordered()
        (Remote.should_receive('receive_files')
         .with_args('/local/path', '/home/user/avocado/logs/run-2014-05-26-'
                    '15.45.37.zip')).once().ordered()
        (flexmock(remote.archive).should_receive('uncompress')
         .with_args('/local/path/run-2014-05-26-15.45.37.zip', '/local/path')
         .once().ordered())
        (flexmock(remote.os).should_receive('remove')
         .with_args('/local/path/run-2014-05-26-15.45.37.zip').once()
         .ordered())
        Results.should_receive('end_tests').once().ordered()
        Results.should_receive('tear_down').once().ordered()
        self.remote.result = Results

    def tearDown(self):
        flexmock_teardown()

    def test_run_suite(self):
        """ Test RemoteTestRunner.run_suite() """
        self.remote.run_suite(None)
        flexmock_teardown()  # Checks the expectations


class RemoteTestResultTest(unittest.TestCase):

    """ Tests the RemoteTestResult """

    def setUp(self):
        Remote = flexmock()
        Stream = flexmock()
        (flexmock(remote.os).should_receive('getcwd')
         .and_return('/current/directory').ordered())
        Stream.should_receive('notify').once().ordered()
        remote_remote = flexmock(remote.remote)
        (remote_remote.should_receive('Remote')
         .with_args('hostname', 'username', 'password', 22, quiet=True)
         .once().ordered()
         .and_return(Remote))
        (Remote.should_receive('makedir').with_args('~/avocado/tests')
         .once().ordered())
        (flexmock(remote.os.path).should_receive('exists')
         .with_args('/tests/sleeptest').once().and_return(True).ordered())
        (flexmock(remote.os.path).should_receive('exists')
         .with_args('/tests/other/test').once().and_return(True).ordered())
        (flexmock(remote.os.path).should_receive('exists')
         .with_args('passtest').once().and_return(False).ordered())
        (flexmock(remote.data_dir).should_receive('get_test_dir').once()
         .and_return('/path/to/default/tests/location').ordered())
        (Remote.should_receive('makedir')
         .with_args("~/avocado/tests/path/to/default/tests/location")
         .once().ordered())
        (Remote.should_receive('send_files')
         .with_args("/path/to/default/tests/location",
                    "~/avocado/tests/path/to/default/tests").once().ordered())
        (Remote.should_receive('makedir')
         .with_args("~/avocado/tests/tests")
         .once().ordered())
        (Remote.should_receive('send_files')
         .with_args("/tests", "~/avocado/tests").once().ordered())
        Args = flexmock(test_result_total=1,
                        url=['/tests/sleeptest', '/tests/other/test',
                             'passtest'],
                        remote_username='username',
                        remote_hostname='hostname',
                        remote_port=22,
                        remote_password='password',
                        remote_no_copy=False)
        self.remote = remote.RemoteTestResult(Stream, Args)

    def tearDown(self):
        flexmock_teardown()

    def test_setup(self):
        """ Tests RemoteTestResult.test_setup() """
        self.remote.setup()
        flexmock_teardown()

if __name__ == '__main__':
    unittest.main()
