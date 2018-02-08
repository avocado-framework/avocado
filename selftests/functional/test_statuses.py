import json
import os
import shutil
import tempfile
import unittest

from avocado.utils import genio
from avocado.utils import process


basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
basedir = os.path.abspath(basedir)

AVOCADO = os.environ.get("UNITTEST_AVOCADO_CMD", "./scripts/avocado")

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
                                       ['setup pre',
                                        "[WARNING: self.skip() will be "
                                        "deprecated. Use 'self.cancel()' "
                                        "or the skip decorators]"]),
                    'Skip.test': ('ERROR',
                                  ['setup pre',
                                   'setup post',
                                   'test pre',
                                   'teardown pre',
                                   'teardown post',
                                   "Calling skip() in places other "
                                   "than setUp() is not allowed in "
                                   "avocado, you must fix your "
                                   "test."]),
                    'SkipTeardown.test': ('ERROR',
                                          ['setup pre',
                                           'setup post',
                                           'test pre',
                                           'test post',
                                           'teardown pre',
                                           "Calling skip() in places other "
                                           "than setUp() is not allowed in "
                                           "avocado, you must fix your "
                                           "test."]),
                    'CancelSetup.test': ('CANCEL',
                                         ['setup pre',
                                          'teardown pre',
                                          'teardown post']),

                    'Cancel.test': ('CANCEL',
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
                    'Fail.test': ('FAIL',
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
                    'Warn.test': ('WARN',
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
                    'Exit.test': ('ERROR',
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
                    'Exception.test': ('ERROR',
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
                    'Kill.test': ('ERROR',
                                  ['setup pre',
                                   'setup post',
                                   'test pre']),
                    }


class TestStatuses(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        test_file = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                 os.path.pardir,
                                                 ".data",
                                                 'test_statuses.py'))

        os.chdir(basedir)
        cmd = ('%s run %s --sysinfo=off --job-results-dir %s --json -' %
               (AVOCADO, test_file, self.tmpdir))

        results = process.run(cmd, ignore_status=True)
        self.results = json.loads(results.stdout)

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

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
