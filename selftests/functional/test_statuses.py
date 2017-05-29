import json
import os
import shutil
import tempfile
import unittest

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

# Format: {variant1: (status,
#                     [msg_in, ...])
#          variant2: (status,
#                     [msg_in, ...])
EXPECTED_RESULTS = {'skip-setup-d304': ('SKIP',
                                        ['setup pre',
                                         'teardown pre',
                                         'teardown post',
                                         "[WARNING: self.skip() will be "
                                         "deprecated. Use 'self.cancel()' "
                                         "or the skip decorators]"]),
                    'skip-test-914e': ('ERROR',
                                       ['setup pre',
                                        'setup post',
                                        'test pre',
                                        'teardown pre',
                                        'teardown post',
                                        "Calling skip() in places other "
                                        "than setUp() is not allowed in "
                                        "avocado, you must fix your "
                                        "test."]),
                    'skip-teardown-d105': ('ERROR',
                                           ['setup pre',
                                            'setup post',
                                            'test pre',
                                            'test post',
                                            'teardown pre',
                                            "Calling skip() in places other "
                                            "than setUp() is not allowed in "
                                            "avocado, you must fix your "
                                            "test."]),
                    'cancel-setup-965f': ('CANCEL',
                                          ['setup pre',
                                           'teardown pre',
                                           'teardown post']),
                    'cancel-test-9699': ('CANCEL',
                                         ['setup pre',
                                          'setup post',
                                          'test pre',
                                          'teardown pre',
                                          'teardown post']),
                    'cancel-teardown-8867': ('CANCEL',
                                             ['setup pre',
                                              'setup post',
                                              'test pre',
                                              'test post',
                                              'teardown pre']),
                    'fail-setup-6c89': ('ERROR',
                                        ['setup pre',
                                         'teardown pre',
                                         'teardown post']),
                    'fail-test-f361': ('FAIL',
                                       ['setup pre',
                                        'setup post',
                                        'test pre',
                                        'teardown pre',
                                        'teardown post']),
                    'fail-teardown-a0b0': ('ERROR',
                                           ['setup pre',
                                            'setup post',
                                            'test pre',
                                            'test post',
                                            'teardown pre']),
                    'warn-setup-0730': ('WARN',
                                        ['setup pre',
                                         'setup post',
                                         'test pre',
                                         'test post',
                                         'teardown pre',
                                         'teardown post']),
                    'warn-test-b0e3': ('WARN',
                                       ['setup pre',
                                        'setup post',
                                        'test pre',
                                        'test post',
                                        'teardown pre',
                                        'teardown post']),
                    'warn-teardown-3d38': ('WARN',
                                           ['setup pre',
                                            'setup post',
                                            'test pre',
                                            'test post',
                                            'teardown pre',
                                            'teardown post']),
                    'exit-setup-0eba': ('ERROR',
                                        ['setup pre',
                                         'teardown pre',
                                         'teardown post']),
                    'exit-test-f680': ('ERROR',
                                       ['setup pre',
                                        'setup post',
                                        'test pre',
                                        'teardown pre',
                                        'teardown post']),
                    'exit-teardown-6304': ('ERROR',
                                           ['setup pre',
                                            'setup post',
                                            'test pre',
                                            'test post',
                                            'teardown pre']),
                    'exception-setup-37d3': ('ERROR',
                                             ['setup pre',
                                              'teardown pre',
                                              'teardown post']),
                    'exception-test-8f7d': ('ERROR',
                                            ['setup pre',
                                             'setup post',
                                             'test pre',
                                             'teardown pre',
                                             'teardown post']),
                    'exception-teardown-dfb1': ('ERROR',
                                                ['setup pre',
                                                 'setup post',
                                                 'test pre',
                                                 'test post',
                                                 'teardown pre']),
                    'kill-test-57fe': ('ERROR',
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
        yaml_file = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                 os.path.pardir,
                                                 ".data",
                                                 'test_statuses.yaml'))

        cmd = ('%s run %s -m %s --sysinfo=off --job-results-dir %s --json -' %
               (AVOCADO, test_file, yaml_file, self.tmpdir))

        results = process.run(cmd, ignore_status=True)
        self.results = json.loads(results.stdout)

    def test(self):
        missing_tests = []

        # Testing each individual test results
        for test in self.results['tests']:
            variant = test['id'].split(';')[1]
            expected = EXPECTED_RESULTS.get(variant, False)
            if not expected:
                missing_tests.append(variant)
            else:
                self._check_test(test, expected)

        # Testing if all variants were covered
        missing_msg = ' '.join(missing_tests)
        self.assertEqual(missing_msg, '',
                         "Expected results not found for variants: %s" %
                         missing_msg)

    def _check_test(self, test, expected):
        variant = test['id'].split(';')[1]
        self.assertEqual(expected[0], test['status'],
                         "Status error: '%s' != '%s' (%s)" %
                         (expected[0], test['status'], variant))
        debug_log = open(test['logfile'], 'r').read()
        for msg in expected[1]:
            self.assertIn(msg, debug_log,
                          "Message '%s' should be in the log (%s)."
                          "\nJSON results:\n%s"
                          "\nDebug Log:\n%s" %
                          (msg, variant, test, debug_log))
        for msg in set(ALL_MESSAGES) - set(expected[1]):
            self.assertNotIn(msg, debug_log,
                             "Message '%s' should not be in the log (%s)"
                             "\nJSON results:\n%s"
                             "\nDebug Log:\n%s" %
                             (msg, variant, test, debug_log))

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
