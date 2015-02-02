import unittest

# simple magic for using scripts within a source tree
from avocado.plugins import remote
from avocado.utils.debug import Mocker


class BetterObject(object):     # pylint: disable=R0903

    """ Original 'object' doesn't allow setattr. This one does """
    pass


class Remote(object):   # pylint: disable=R0903

    """ Fake remote class """

    def __init__(self, mocker):
        self.receive_files = mocker.log_function('Remote.receive_files')
        stdout = ('Something other than json\n'
                  '{"tests": [{"test": "sleeptest.1", "url": "sleeptest", '
                  '"status": "PASS", "time": 1.23, "start": 0, "end": 1.23}],'
                  '"debuglog": "/home/user/avocado/logs/run-2014-05-26-15.45.'
                  '37/debug.log", "errors": 0, "skip": 0, "time": 1.4, '
                  '"start": 0, "end": 1.4, "pass": 1, "failures": 0, "total": '
                  '1}\nAdditional stuff other than json')
        result = BetterObject()
        result.stdout = stdout
        self.run = mocker.log_function('Remote.run', result)
        self.makedir = mocker.log_function('Remote.makedir')
        self.rsync = mocker.log_function('Remote.rsync')


class Results(object):  # pylint: disable=R0902,R0903

    """ Fake results class """

    def __init__(self, mocker):
        self.remote = Remote(mocker)
        self.setup = mocker.log_function('Results.setup')
        self.urls = ['sleeptest']
        self.start_tests = mocker.log_function('Results.start_tests')
        self.stream = BetterObject()
        self.stream.job_unique_id = 'sleeptest.1'
        self.stream.debuglog = '/local/path'
        self.start_test = mocker.log_function('Results.start_test')
        self.check_test = mocker.log_function('Results.check_test')
        self.end_tests = mocker.log_function('Results.end_tests')
        self.tear_down = mocker.log_function('Results.tear_down')


class RemoteTestRunnerTest(unittest.TestCase):

    """ Tests RemoteTestRunner """

    def setUp(self):
        self.mocker = Mocker()
        self.mocker.mock('remote.os.remove', remote.os, 'remove')
        self.mocker.mock('remote.archive.uncompress', remote.archive,
                         'uncompress')
        self.mocker.mock('remote.RemoteTestRunner.__init__',
                         remote.RemoteTestRunner, '__init__')
        self.remote = remote.RemoteTestRunner(None, None)
        self.remote.result = Results(self.mocker)

    def tearDown(self):
        self.mocker.unmock_all()

    def test_run_suite(self):
        """ Test RemoteTestRunner.run_suite() """
        self.remote.run_suite(None)
        # FIXME: Why remote.archive.uncompress path is /local when /local/path
        # is set?
        exps = ["Results.setup () {}",
                ("Remote.run ('cd ~/avocado/tests; avocado run --force-job-id "
                 "sleeptest.1 --json - --archive sleeptest',) "
                 "{'ignore_status': True}"),
                "Results.start_tests () {}",
                ("Results.start_test ({'status': u'PASS', 'whiteboard': '', "
                 "'time_start': 0, 'name': u'sleeptest.1', 'class_name': "
                 "'RemoteTest', 'traceback': 'Not supported yet', "
                 "'text_output': 'Not supported yet', 'time_end': 1.23, "
                 "'tagged_name': u'sleeptest.1', 'time_elapsed': 1.23, "
                 "'fail_class': 'Not supported yet', 'job_unique_id': '', "
                 "'fail_reason': 'Not supported yet'},) {}"),
                ("Results.check_test ({'status': u'PASS', 'whiteboard': '', "
                 "'time_start': 0, 'name': u'sleeptest.1', 'class_name': "
                 "'RemoteTest', 'traceback': 'Not supported yet', "
                 "'text_output': 'Not supported yet', 'time_end': 1.23, "
                 "'tagged_name': u'sleeptest.1', 'time_elapsed': 1.23, "
                 "'fail_class': 'Not supported yet', 'job_unique_id': '', "
                 "'fail_reason': 'Not supported yet'},) {}"),
                ("Remote.receive_files ('/local', u'/home/user/avocado/logs/"
                 "run-2014-05-26-15.45.37.zip') {}"),
                "Results.end_tests () {}",
                "Results.tear_down () {}"]
        iexps = iter(exps)
        try:
            exp = iexps.next()
            for line in self.mocker.log:
                if line == exp:
                    exp = iexps.next()
            self.assertTrue(False, "Expected log:\n%s\nActual log:\n%s\n"
                            "Fail to find:\n  %s"
                            % ("\n  ".join(exps), "\n  ".join(self.mocker.log),
                               exp))
        except StopIteration:
            pass


class Stream(object):  # pylint: disable=R0903

    """ Fake stream object """

    def __init__(self, mocker):
        self.notify = mocker.log_function('Stream.notify')


class Args(object):     # pylint: disable=R0903

    """ Fake args object """

    def __init__(self):
        self.test_result_total = 1
        self.url = ['/tests/sleeptest', '/tests/other/test',
                    '/other/tests/test']
        self.remote_username = 'username'
        self.remote_hostname = 'hostname'
        self.remote_port = 22
        self.remote_password = 'password'


class RemoteTestResultTest(unittest.TestCase):

    """ Tests the RemoteTestResult """

    def setUp(self):
        self.mocker = Mocker()
        self.mocker.mock('remote.os.getcwd', remote.os, 'getcwd',
                         '/current/directory')
        self.mocker.mock('remote.os.path.exists', remote.os.path, 'exists',
                         True)
        self.mocker.mock('remote.remote.Remote', remote.remote, 'Remote',
                         Remote(self.mocker))
        self.remote = remote.RemoteTestResult(Stream(self.mocker), Args())

    def tearDown(self):
        self.mocker.unmock_all()

    def test_setup(self):
        """ Tests RemoteTestResult.test_setup() """
        self.remote.setup()
        exps = [("remote.remote.Remote "
                 "('hostname', 'username', 'password', 22) {'quiet': True}"),
                "Remote.makedir ('~/avocado/tests',) {}",
                "Remote.makedir ('~/avocado/tests/other/tests',) {}",
                "Remote.rsync ('/other/tests', '~/avocado/tests/other') {}",
                "Remote.makedir ('~/avocado/tests/tests',) {}",
                "Remote.rsync ('/tests', '~/avocado/tests') {}"]
        iexps = iter(exps)
        try:
            exp = iexps.next()
            for line in self.mocker.log:
                if line == exp:
                    exp = iexps.next()
            self.assertTrue(False, "Expected log:\n%s\nActual log:\n%s\n"
                            "Fail to find:\n  %s"
                            % ("\n  ".join(exps), "\n  ".join(self.mocker.log),
                               exp))
        except StopIteration:
            pass

if __name__ == '__main__':
    unittest.main()
