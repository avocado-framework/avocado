import json
import os
import unittest

from avocado.utils import genio, process
from selftests.utils import AVOCADO, TestCaseTmpDir

ALL_MESSAGES = ['setup pre',
                'setup post',
                'test pre',
                'test post',
                'teardown pre',
                'teardown post']

# Format: {klass.test_method: (status,
#                              [msg_in, ...]),
#          ...}
EXPECTED_RESULTS = {'SkipSetup.test': ('SKIP',
                                       ['TestSkipError: from setUp()']),
                    'SkipTest.test': ('SKIP',
                                      ['TestSkipError: from test()']),
                    'SkipTeardown.test': ('ERROR',
                                          ['setup pre',
                                           'setup post',
                                           'test pre',
                                           'test post',
                                           'TestError: Using skip decorators '
                                           'in tearDown() is not allowed in '
                                           'avocado, you must fix your test. '
                                           'Original skip exception: from '
                                           'tearDown()']),
                    'CancelSetup.test': ('CANCEL',
                                         ['setup pre',
                                          'teardown pre',
                                          'teardown post']),

                    'CancelTest.test': ('CANCEL',
                                        ['setup pre',
                                         'setup post',
                                         'test pre',
                                         'teardown pre',
                                         'teardown post']),
                    'CancelTeardown.test': ('CANCEL',
                                            ['setup pre',
                                             'setup post',
                                             'test pre',
                                             'test post',
                                             'teardown pre']),
                    'FailSetup.test': ('ERROR',
                                       ['setup pre',
                                        'teardown pre',
                                        'teardown post']),
                    'FailTest.test': ('FAIL',
                                      ['setup pre',
                                       'setup post',
                                       'test pre',
                                       'teardown pre',
                                       'teardown post']),
                    'FailTeardown.test': ('ERROR',
                                          ['setup pre',
                                           'setup post',
                                           'test pre',
                                           'test post',
                                           'teardown pre']),
                    'WarnSetup.test': ('WARN',
                                       ['setup pre',
                                        'setup post',
                                        'test pre',
                                        'test post',
                                        'teardown pre',
                                        'teardown post']),
                    'WarnTest.test': ('WARN',
                                      ['setup pre',
                                       'setup post',
                                       'test pre',
                                       'test post',
                                       'teardown pre',
                                       'teardown post']),
                    'WarnTeardown.test': ('WARN',
                                          ['setup pre',
                                           'setup post',
                                           'test pre',
                                           'test post',
                                           'teardown pre',
                                           'teardown post']),
                    'ExitSetup.test': ('ERROR',
                                       ['setup pre',
                                        'teardown pre',
                                        'teardown post']),
                    'ExitTest.test': ('ERROR',
                                      ['setup pre',
                                       'setup post',
                                       'test pre',
                                       'teardown pre',
                                       'teardown post']),
                    'ExitTeardown.test': ('ERROR',
                                          ['setup pre',
                                           'setup post',
                                           'test pre',
                                           'test post',
                                           'teardown pre']),
                    'ExceptionSetup.test': ('ERROR',
                                            ['setup pre',
                                             'teardown pre',
                                             'teardown post']),
                    'ExceptionTest.test': ('ERROR',
                                           ['setup pre',
                                            'setup post',
                                            'test pre',
                                            'teardown pre',
                                            'teardown post']),
                    'ExceptionTeardown.test': ('ERROR',
                                               ['setup pre',
                                                'setup post',
                                                'test pre',
                                                'test post',
                                                'teardown pre']),
                    'KillTest.test': ('ERROR',
                                      ['setup pre',
                                       'setup post',
                                       'test pre']),
                    }


class TestStatuses(TestCaseTmpDir):

    def setUp(self):
        super(TestStatuses, self).setUp()
        test_file = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                 os.path.pardir,
                                                 ".data",
                                                 'test_statuses.py'))

        cmd = ('%s run %s --disable-sysinfo --job-results-dir %s --json - '
               '--test-runner=runner '
               % (AVOCADO, test_file, self.tmpdir.name))

        results = process.run(cmd, ignore_status=True)
        self.results = json.loads(results.stdout_text)

    def test(self):
        missing_tests = []

        # Testing each individual test results
        for test in self.results['tests']:
            klass_method = test['id'].split(':')[1]
            expected = EXPECTED_RESULTS.get(klass_method, False)
            if not expected:
                missing_tests.append(klass_method)
            else:
                self._check_test(test, expected)

        # Testing if all class/methods were covered
        missing_msg = ' '.join(missing_tests)
        self.assertEqual(missing_msg, '',
                         "Expected results not found for class/method: %s" %
                         missing_msg)

    def _check_test(self, test, expected):
        klass_method = test['id'].split(':')[1]
        self.assertEqual(expected[0], test['status'],
                         "Status error: '%s' != '%s' (%s)" %
                         (expected[0], test['status'], klass_method))
        debug_log = genio.read_file(test['logfile'])
        for msg in expected[1]:
            self.assertIn(msg, debug_log,
                          "Message '%s' should be in the log (%s)."
                          "\nJSON results:\n%s"
                          "\nDebug Log:\n%s" %
                          (msg, klass_method, test, debug_log))
        for msg in set(ALL_MESSAGES) - set(expected[1]):
            self.assertNotIn(msg, debug_log,
                             "Message '%s' should not be in the log (%s)"
                             "\nJSON results:\n%s"
                             "\nDebug Log:\n%s" %
                             (msg, klass_method, test, debug_log))


if __name__ == '__main__':
    unittest.main()
