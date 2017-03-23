import json
import os
import shutil
import tempfile
import unittest

from avocado.core import exit_codes
from avocado.utils import process
from avocado.utils import script

basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
basedir = os.path.abspath(basedir)

AVOCADO = os.environ.get("UNITTEST_AVOCADO_CMD", "./scripts/avocado")

TEST_CANCEL = """
import avocado

class AvocadoCancelTest(avocado.Test):

    def setUp(self):
        self.log.info('setup code cancel')

    def test(self):
        self.log.info('test code before cancel')
        self.cancel()
        self.log.info('test code after cancel')

    def tearDown(self):
        self.log.info('teardown code')
"""

TEST_CANCEL_ON_SETUP = """
import avocado

class AvocadoCancelTest(avocado.Test):

    def setUp(self):
        self.log.info('setup code before cancel')
        self.cancel()
        self.log.info('setup code after cancel')

    def test(self):
        self.log.info('test code')

    def tearDown(self):
        self.log.info('teardown code')
"""


class TestCancel(unittest.TestCase):

    def setUp(self):
        os.chdir(basedir)
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)

        test_path = os.path.join(self.tmpdir, 'test_cancel.py')
        self._test_cancel = script.Script(test_path,
                                          TEST_CANCEL)
        self._test_cancel.save()

        test_path = os.path.join(self.tmpdir, 'test_cancel_on_setup.py')
        self._test_cancel_on_setup = script.Script(test_path,
                                                   TEST_CANCEL_ON_SETUP)
        self._test_cancel_on_setup.save()

    def test_cancel(self):
        os.chdir(basedir)
        cmd_line = [AVOCADO,
                    'run',
                    '--sysinfo=off',
                    '--job-results-dir',
                    '%s' % self.tmpdir,
                    '%s' % self._test_cancel,
                    '--json -']
        result = process.run(' '.join(cmd_line), ignore_status=True)
        json_results = json.loads(result.stdout)
        debuglog = json_results['debuglog']
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertEqual(json_results['cancel'], 1)
        self.assertIn('setup code', open(debuglog, 'r').read())
        self.assertIn('test code before cancel', open(debuglog, 'r').read())
        self.assertNotIn('test code after cancel', open(debuglog, 'r').read())
        self.assertIn('teardown code', open(debuglog, 'r').read())

    def test_cancel_on_setup(self):
        os.chdir(basedir)
        cmd_line = [AVOCADO,
                    'run',
                    '--sysinfo=off',
                    '--job-results-dir',
                    '%s' % self.tmpdir,
                    '%s' % self._test_cancel_on_setup,
                    '--json -']
        result = process.run(' '.join(cmd_line), ignore_status=True)
        json_results = json.loads(result.stdout)
        debuglog = json_results['debuglog']
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertEqual(json_results['cancel'], 1)
        self.assertIn('setup code before cancel', open(debuglog, 'r').read())
        self.assertNotIn('setup code after cancel', open(debuglog, 'r').read())
        self.assertNotIn('test code', open(debuglog, 'r').read())
        self.assertIn('teardown code', open(debuglog, 'r').read())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
