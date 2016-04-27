#!/usr/bin/env python

import unittest
import os

from flexmock import flexmock, flexmock_teardown

from avocado.core import remoter
from avocado.core import remote
from avocado.utils import archive
import logging

cwd = os.getcwd()

JSON_RESULTS = ('Something other than json\n'
                '{"tests": [{"test": "1-sleeptest;0", "url": "sleeptest", '
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

    def setUp(self):
        Args = flexmock(test_result_total=1,
                        remote_username='username',
                        remote_hostname='hostname',
                        remote_port=22,
                        remote_password='password',
                        remote_key_file=None,
                        remote_no_copy=False,
                        remote_timeout=60,
                        show_job_log=False,
                        multiplex_files=['foo.yaml', 'bar/baz.yaml'],
                        dry_run=True)
        log = flexmock()
        log.should_receive("info")
        job = flexmock(args=Args, log=log,
                       urls=['/tests/sleeptest', '/tests/other/test',
                             'passtest'], unique_id='1-sleeptest;0',
                       logdir="/local/path")

        flexmock(remote.RemoteTestRunner).should_receive('__init__')
        self.runner = remote.RemoteTestRunner(job, None)
        self.runner.job = job
        self.runner._copy_files = lambda: True  # Skip _copy_files

        filehandler = logging.StreamHandler()
        flexmock(logging).should_receive("FileHandler").and_return(filehandler)

        test_results = flexmock(stdout=JSON_RESULTS, exit_status=0)
        stream = flexmock(job_unique_id='1-sleeptest;0',
                          debuglog='/local/path/dirname')
        Remote = flexmock()
        Remoter = flexmock(remoter.Remote)
        Remoter.new_instances(Remote)
        args_version = 'avocado -v'
        version_result = flexmock(stdout='Avocado 1.2', exit_status=0)
        args_env = 'env'
        env_result = flexmock(stdout='''XDG_SESSION_ID=20
HOSTNAME=rhel7.0
SELINUX_ROLE_REQUESTED=
SHELL=/bin/bash
TERM=vt100
HISTSIZE=1000
SSH_CLIENT=192.168.124.1 52948 22
SELINUX_USE_CURRENT_RANGE=
SSH_TTY=/dev/pts/0
USER=root
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/root/bin
MAIL=/var/spool/mail/root
PWD=/root
LANG=en_US.UTF-8
SELINUX_LEVEL_REQUESTED=
HISTCONTROL=ignoredups
HOME=/root
SHLVL=2
LOGNAME=root
SSH_CONNECTION=192.168.124.1 52948 192.168.124.65 22
LESSOPEN=||/usr/bin/lesspipe.sh %s
XDG_RUNTIME_DIR=/run/user/0
_=/usr/bin/env''', exit_status=0)
        (Remote.should_receive('run')
         .with_args(args_env, ignore_status=True, timeout=60)
         .once().and_return(env_result))

        (Remote.should_receive('run')
         .with_args(args_version, ignore_status=True, timeout=60)
         .once().and_return(version_result))

        args = ('cd ~/avocado/tests; avocado list /tests/sleeptest '
                '/tests/other/test passtest --paginator=off')
        urls_result = flexmock(exit_status=0)
        (Remote.should_receive('run')
         .with_args(args, ignore_status=True, timeout=60)
         .once().and_return(urls_result))

        args = ("cd ~/avocado/tests; avocado run --force-job-id 1-sleeptest;0 "
                "--json - --archive /tests/sleeptest /tests/other/test "
                "passtest --multiplex ~/avocado/tests/foo.yaml "
                "~/avocado/tests/bar/baz.yaml --dry-run")
        (Remote.should_receive('run')
         .with_args(args, timeout=61, ignore_status=True)
         .once().and_return(test_results))
        Results = flexmock(remote=Remote, urls=['sleeptest'],
                           stream=stream, timeout=None,
                           args=flexmock(show_job_log=False,
                                         multiplex_files=['foo.yaml', 'bar/baz.yaml'],
                                         dry_run=True))
        Results.should_receive('start_tests').once().ordered()
        args = {'status': u'PASS', 'whiteboard': '', 'time_start': 0,
                'name': '1-sleeptest;0', 'class_name': 'RemoteTest',
                'traceback': 'Not supported yet',
                'text_output': 'Not supported yet', 'time_end': 1.23,
                'time_elapsed': 1.23,
                'fail_class': 'Not supported yet', 'job_unique_id': '',
                'fail_reason': u'None',
                'logdir': u'/local/path/test-results/1-sleeptest;0',
                'logfile': u'/local/path/test-results/1-sleeptest;0/debug.log'}
        Results.should_receive('start_test').once().with_args(args).ordered()
        Results.should_receive('check_test').once().with_args(args).ordered()
        (Remote.should_receive('receive_files')
         .with_args('/local/path', '/home/user/avocado/logs/run-2014-05-26-'
                    '15.45.37.zip')).once().ordered()
        (flexmock(archive).should_receive('uncompress')
         .with_args('/local/path/run-2014-05-26-15.45.37.zip', '/local/path')
         .once().ordered())
        (flexmock(os).should_receive('remove')
         .with_args('/local/path/run-2014-05-26-15.45.37.zip').once()
         .ordered())
        Results.should_receive('end_tests').once().ordered()
        self.runner.result = Results

    def tearDown(self):
        flexmock_teardown()

    def test_run_suite(self):
        """ Test RemoteTestRunner.run_suite() """
        self.runner.run_suite(None, None, 61)
        flexmock_teardown()  # Checks the expectations


class RemoteTestRunnerSetup(unittest.TestCase):

    """ Tests the RemoteTestRunner setup() method"""

    def setUp(self):
        Remote = flexmock()
        remote_remote = flexmock(remoter)
        (remote_remote.should_receive('Remote')
         .with_args(hostname='hostname', username='username',
                    password='password', key_filename=None, port=22, timeout=60)
         .once().ordered()
         .and_return(Remote))
        Args = flexmock(test_result_total=1,
                        url=['/tests/sleeptest', '/tests/other/test',
                             'passtest'],
                        remote_username='username',
                        remote_hostname='hostname',
                        remote_port=22,
                        remote_password='password',
                        remote_key_file=None,
                        remote_no_copy=False,
                        remote_timeout=60,
                        show_job_log=False)
        log = flexmock()
        log.should_receive("info")
        job = flexmock(args=Args, log=log)
        self.runner = remote.RemoteTestRunner(job, None)

    def tearDown(self):
        flexmock_teardown()

    def test_setup(self):
        """ Tests RemoteTestResult.test_setup() """
        self.runner.setup()
        flexmock_teardown()

if __name__ == '__main__':
    unittest.main()
