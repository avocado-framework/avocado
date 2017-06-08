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

TEST_SETUP_EXCEPTION = """
import avocado

class AvocadoTest(avocado.Test):

    def setUp(self):
        self.log.info('setup code before')
        raise
        self.log.info('setup code after')

    def test(self):
        self.log.info('test code')

    def tearDown(self):
        self.log.info('teardown code')
"""


class TestTest(unittest.TestCase):

    def setUp(self):
        os.chdir(basedir)
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)

        test_path = os.path.join(self.tmpdir, 'test_setup_exception.py')
        self.test_setup_exception = script.Script(test_path,
                                                  TEST_SETUP_EXCEPTION)
        self.test_setup_exception.save()

    def test_setup_exception(self):
        os.chdir(basedir)
        cmd_line = [AVOCADO,
                    'run',
                    '--sysinfo=off',
                    '--job-results-dir',
                    '%s' % self.tmpdir,
                    '%s' % self.test_setup_exception,
                    '--json -']
        result = process.run(' '.join(cmd_line), ignore_status=True)
        json_results = json.loads(result.stdout)
        debuglog = json_results['debuglog']
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_TESTS_FAIL)
        self.assertEqual(json_results['errors'], 1)
        self.assertIn('setup code before', open(debuglog, 'r').read())
        self.assertNotIn('setup code after', open(debuglog, 'r').read())
        self.assertNotIn('test code', open(debuglog, 'r').read())
        self.assertIn('teardown code', open(debuglog, 'r').read())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
