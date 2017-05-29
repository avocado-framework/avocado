import json
import os
import shutil
import tempfile
import unittest

from avocado.utils import process
from avocado.utils import script


basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
basedir = os.path.abspath(basedir)

AVOCADO = os.environ.get("UNITTEST_AVOCADO_CMD", "./scripts/avocado")

TEST_CONTENT = """
import os
import sys
from avocado import Test

class StatusTest(Test):

    def setUp(self):
        self.log.info('setup pre')
        if self.params.get('location') == 'setUp':
            exec(self.params.get('command'))
        self.log.info('setup post')

    def test(self):
        self.log.info('test pre')
        if self.params.get('location') == 'test':
            exec(self.params.get('command'))
        self.log.info('test post')

    def tearDown(self):
        self.log.info('teardown pre')
        if self.params.get('location') == 'tearDown':
            exec(self.params.get('command'))
        self.log.info('teardown post')
"""

YAML_CONTENT = """
locations: !mux
    setup:
        location: setUp
    test:
        location: test
    teardown:
        location: tearDown

commands: !mux
    skip:
        command: self.skip()
    cancel:
        command: self.cancel()
    fail:
        command: self.fail()
    warn:
        command: self.log.warn('')
    exception:
        command: raise Exception
    exit:
        command: sys.exit(-1)
    kill:
        command: os.kill(os.getpid(), 9)
"""

# Format: {variant1: (status,
#                    [msg_in, ...],
#                    [msg_not_in, ...]),
#          variant2: (status,
#                     [msg_in, ...],
#                     [msg_not_in, ...])}
EXPECTED_RESULTS = {'skip-setup-d304': ('SKIP',
                                        ['setup pre',
                                         'teardown pre',
                                         'teardown post',
                                         "[WARNING: self.skip() will be "
                                         "deprecated. Use 'self.cancel()' "
                                         "or the skip decorators]"],
                                        ['setup post',
                                         'test pre',
                                         'test post']),
                    'skip-test-914e': ('ERROR',
                                       ['setup pre',
                                        'setup post',
                                        'test pre',
                                        'teardown pre',
                                        'teardown post',
                                        "Calling skip() in places other "
                                        "than setUp() is not allowed in "
                                        "avocado, you must fix your "
                                        "test."],
                                       ['test post']),
                    'skip-teardown-d105': ('ERROR',
                                           ['setup pre',
                                            'setup post',
                                            'test pre',
                                            'test post',
                                            'teardown pre',
                                            "Calling skip() in places other "
                                            "than setUp() is not allowed in "
                                            "avocado, you must fix your "
                                            "test."],
                                           ['teardown post']),
                    'cancel-setup-965f': ('CANCEL',
                                          ['setup pre',
                                           'teardown pre',
                                           'teardown post'],
                                          ['setup post',
                                           'test pre',
                                           'test post']),
                    'cancel-test-9699': ('CANCEL',
                                         ['setup pre',
                                          'setup post',
                                          'test pre',
                                          'teardown pre',
                                          'teardown post'],
                                         ['test post']),
                    'cancel-teardown-8867': ('CANCEL',
                                             ['setup pre',
                                              'setup post',
                                              'test pre',
                                              'test post',
                                              'teardown pre'],
                                             ['teardown post']),
                    'fail-setup-6c89': ('ERROR',
                                        ['setup pre',
                                         'teardown pre',
                                         'teardown post'],
                                        ['setup post',
                                         'test pre',
                                         'test post']),
                    'fail-test-f361': ('FAIL',
                                       ['setup pre',
                                        'setup post',
                                        'test pre',
                                        'teardown pre',
                                        'teardown post'],
                                       ['test post']),
                    'fail-teardown-a0b0': ('ERROR',
                                           ['setup pre',
                                            'setup post',
                                            'test pre',
                                            'test post',
                                            'teardown pre'],
                                           ['teardown post']),
                    'warn-setup-0730': ('WARN',
                                        ['setup pre',
                                         'setup post',
                                         'test pre',
                                         'test post',
                                         'teardown pre',
                                         'teardown post'],
                                        []),
                    'warn-test-b0e3': ('WARN',
                                       ['setup pre',
                                        'setup post',
                                        'test pre',
                                        'test post',
                                        'teardown pre',
                                        'teardown post'],
                                       []),
                    'warn-teardown-3d38': ('WARN',
                                           ['setup pre',
                                            'setup post',
                                            'test pre',
                                            'test post',
                                            'teardown pre',
                                            'teardown post'],
                                           []),
                    'exit-setup-1d82': ('ERROR',
                                        ['setup pre',
                                         'teardown pre',
                                         'teardown post'],
                                        ['setup post',
                                         'test pre',
                                         'test post']),
                    'exit-test-f12d': ('ERROR',
                                       ['setup pre',
                                        'setup post',
                                        'test pre',
                                        'teardown pre',
                                        'teardown post'],
                                       ['test post']),
                    'exit-teardown-8255': ('ERROR',
                                           ['setup pre',
                                            'setup post',
                                            'test pre',
                                            'test post',
                                            'teardown pre'],
                                           ['teardown post']),
                    'exception-setup-37d3': ('ERROR',
                                             ['setup pre',
                                              'teardown pre',
                                              'teardown post'],
                                             ['setup post',
                                              'test pre',
                                              'test post']),
                    'exception-test-8f7d': ('ERROR',
                                            ['setup pre',
                                             'setup post',
                                             'test pre',
                                             'teardown pre',
                                             'teardown post'],
                                            ['test post']),
                    'exception-teardown-dfb1': ('ERROR',
                                                ['setup pre',
                                                 'setup post',
                                                 'test pre',
                                                 'test post',
                                                 'teardown pre'],
                                                ['teardown post']),
                    'kill-setup-e415': ('ERROR',
                                        ['setup pre'],
                                        ['setup post',
                                         'test pre',
                                         'test post'
                                         'teardown pre',
                                         'teardown post']),
                    'kill-test-27e3': ('ERROR',
                                       ['setup pre',
                                        'setup post',
                                        'test pre'],
                                       ['test post',
                                        'teardown pre',
                                        'teardown post']),
                    'kill-teardown-94c9': ('ERROR',
                                           ['setup pre',
                                            'setup post',
                                            'test pre',
                                            'test post',
                                            'teardown pre'],
                                           ['teardown post']),
                    }


class TestStatuses(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        test_file = script.TemporaryScript('test.py', TEST_CONTENT)
        test_file.save()
        yaml_file = script.TemporaryScript('test.yaml', YAML_CONTENT)
        yaml_file.save()

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
                          "Message '%s' should be in the log (%s)" %
                          (msg, variant))
        for msg in expected[2]:
            self.assertNotIn(msg, debug_log,
                             "Message '%s' should not be in the log (%s)" %
                             (msg, variant))

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
