#!/usr/bin/env python

import unittest

# simple magic for using scripts within a source tree
from avocado.plugins import remote


def mock_function(name, executed, ret=None):
    """
    Creates function which logs itself into executed and returns ret value
    """
    def new_fction(*args, **kwargs):
        """ Logs itself and return expected return """
        executed.append("%s %s %s" % (name, args, kwargs))
        return ret
    return new_fction


def mock(originals, func, log, ret=None):   # UsedByEval pylint: disable=W0613
    """
    Ugly way to override existing functions from other modules:
    :param originals: Dictionary with original functions
    :param func: Name of the function you wan't to mock
    :param log: In which log this function should append itself when executed
    :param ret: Return value of new function
    """
    originals[func] = eval(func)    # pylint: disable=W0123
    exec("%s = mock_function(func, log, ret)" % func)  # pylint: disable=W0122


def unmock_all(originals):
    """
    Ugly way to restore original functions.
    :param originals: Dict of original names and functions.
    """
    for name in originals.iterkeys():
        exec("%s = originals[name]" % name)  # pylint: disable=W0122


class BetterObject(object):     # pylint: disable=R0903

    """ Original 'object' doesn't allow setattr. This one does """
    pass


class Remote(object):   # pylint: disable=R0903

    """ Fake remote class """

    def __init__(self, log):
        self.receive_files = mock_function('Remote.receive_files', log)
        stdout = ('Something other than json\n'
                  '{"tests": [{"test": "sleeptest.1", "url": "sleeptest", '
                  '"status": "PASS", "time": 1.23, "start": 0, "end": 1.23}],'
                  '"debuglog": "/home/user/avocado/logs/run-2014-05-26-15.45.'
                  '37/debug.log", "errors": 0, "skip": 0, "time": 1.4, '
                  '"start": 0, "end": 1.4, "pass": 1, "failures": 0, "total": '
                  '1}\nAdditional stuff other than json')
        result = BetterObject()
        result.stdout = stdout
        self.run = mock_function('Remote.run', log, result)
        self.makedir = mock_function('Remote.makedir', log)
        self.rsync = mock_function('Remote.rsync', log)


class Results(object):  # pylint: disable=R0902,R0903

    """ Fake results class """

    def __init__(self, log):
        self.remote = Remote(log)
        self.setup = mock_function('Results.setup', log)
        self.urls = ['sleeptest']
        self.start_tests = mock_function('Results.start_tests', log)
        self.stream = BetterObject()
        self.stream.job_unique_id = 'sleeptest.1'
        self.stream.debuglog = '/local/path'
        self.start_test = mock_function('Results.start_test', log)
        self.check_test = mock_function('Results.check_test', log)
        self.end_tests = mock_function('Results.end_tests', log)
        self.tear_down = mock_function('Results.tear_down', log)


class RemoteTestRunnerTest(unittest.TestCase):

    """ Tests RemoteTestRunner """

    def setUp(self):
        self.log = []
        self.__mock = {}
        mock(self.__mock, 'remote.os.remove', self.log)
        mock(self.__mock, 'remote.archive.uncompress', self.log)
        remote.RemoteTestRunner.__init__ = lambda self: None
        self.remote = remote.RemoteTestRunner()
        self.remote.result = Results(self.log)

    def tearDown(self):
        unmock_all(self.__mock)

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
            for line in self.log:
                if line == exp:
                    exp = iexps.next()
            self.assertTrue(False, "Expected log:\n%s\nActual log:\n%s\n"
                            "Fail to find:\n  %s"
                            % ("\n  ".join(exps), "\n  ".join(self.log), exp))
        except StopIteration:
            pass


class Stream(object):  # pylint: disable=R0903

    """ Fake stream object """

    def __init__(self, log):
        self.notify = mock_function('Stream.notify', log)


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
        self.log = []
        self.__mock = {}
        mock(self.__mock, 'remote.os.getcwd', self.log, "/currrent/directory")
        mock(self.__mock, 'remote.os.path.exists', self.log, True)
        mock(self.__mock, 'remote.remote.Remote', self.log, Remote(self.log))
        self.remote = remote.RemoteTestResult(Stream(self.log), Args())

    def tearDown(self):
        unmock_all(self.__mock)

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
            for line in self.log:
                if line == exp:
                    exp = iexps.next()
            self.assertTrue(False, "Expected log:\n%s\nActual log:\n%s\n"
                            "Fail to find:\n  %s"
                            % ("\n  ".join(exps), "\n  ".join(self.log), exp))
        except StopIteration:
            pass


if __name__ == '__main__':
    unittest.main()
