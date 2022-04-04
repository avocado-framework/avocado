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
                                          'teardown status: CANCEL',
                                          'teardown post']),

                    'CancelTest.test': ('CANCEL',
                                        ['setup pre',
                                         'setup post',
                                         'test pre',
                                         'teardown pre',
                                         'teardown status: CANCEL',
                                         'teardown post']),
                    'CancelTeardown.test': ('CANCEL',
                                            ['setup pre',
                                             'setup post',
                                             'test pre',
                                             'test post',
                                             'teardown pre',
                                             'teardown status: PASS']),
                    'FailSetup.test': ('ERROR',
                                       ['setup pre',
                                        'teardown pre',
                                        'teardown status: ERROR',
                                        'teardown post']),
                    'FailTest.test': ('FAIL',
                                      ['setup pre',
                                       'setup post',
                                       'test pre',
                                       'teardown pre',
                                       'teardown status: FAIL',
                                       'teardown post']),
                    'FailTeardown.test': ('ERROR',
                                          ['setup pre',
                                           'setup post',
                                           'test pre',
                                           'test post',
                                           'teardown pre',
                                           'teardown status: PASS']),
                    'WarnSetup.test': ('WARN',
                                       ['setup pre',
                                        'setup post',
                                        'test pre',
                                        'test post',
                                        'teardown pre',
                                        'teardown status: WARN',
                                        'teardown post']),
                    'WarnTest.test': ('WARN',
                                      ['setup pre',
                                       'setup post',
                                       'test pre',
                                       'test post',
                                       'teardown pre',
                                       'teardown status: WARN',
                                       'teardown post']),
                    'WarnTeardown.test': ('WARN',
                                          ['setup pre',
                                           'setup post',
                                           'test pre',
                                           'test post',
                                           'teardown pre',
                                           'teardown status: PASS',
                                           'teardown post']),
                    'ExitSetup.test': ('ERROR',
                                       ['setup pre',
                                        'teardown pre',
                                        'teardown status: ERROR',
                                        'teardown post']),
                    'ExitTest.test': ('ERROR',
                                      ['setup pre',
                                       'setup post',
                                       'test pre',
                                       'teardown pre',
                                       'teardown status: ERROR',
                                       'teardown post']),
                    'ExitTeardown.test': ('ERROR',
                                          ['setup pre',
                                           'setup post',
                                           'test pre',
                                           'test post',
                                           'teardown pre',
                                           'teardown status: PASS']),
                    'ExceptionSetup.test': ('ERROR',
                                            ['setup pre',
                                             'teardown pre',
                                             'teardown status: ERROR',
                                             'teardown post']),
                    'ExceptionTest.test': ('ERROR',
                                           ['setup pre',
                                            'setup post',
                                            'test pre',
                                            'teardown pre',
                                            'teardown status: ERROR',
                                            'teardown post']),
                    'ExceptionTeardown.test': ('ERROR',
                                               ['setup pre',
                                                'setup post',
                                                'test pre',
                                                'test post',
                                                'teardown pre',
                                                'teardown status: PASS']),
                    }


class TestStatuses(TestCaseTmpDir):

    def setUp(self):
        super().setUp()
        test_file = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                 os.path.pardir,
                                                 ".data",
                                                 'test_statuses.py'))

        cmd = (f'{AVOCADO} run {test_file} --disable-sysinfo '
               f'--job-results-dir {self.tmpdir.name} --json - ')

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
                         (f"Expected results not found for class/method: "
                          f"{missing_msg}"))

    def _check_test(self, test, expected):
        klass_method = test['id'].split(':')[1]
        self.assertEqual(expected[0], test['status'],
                         (f"Status error: '{expected[0]}' != "
                          f"'{test['status']}' ({klass_method})"))
        debug_log = genio.read_file(test['logfile'])
        for msg in expected[1]:
            self.assertIn(msg, debug_log,
                          (f"Message '{msg}' should be in the log "
                           f"({klass_method})."
                           f"\nJSON results:\n{test}"
                           f"\nDebug Log:\n{debug_log}"))
        for msg in set(ALL_MESSAGES) - set(expected[1]):
            self.assertNotIn(msg, debug_log,
                             (f"Message '{msg}' should not be in the log "
                              "({klass_method})"
                              f"\nJSON results:\n{test}"
                              f"\nDebug Log:\n{debug_log}"))


if __name__ == '__main__':
    unittest.main()
