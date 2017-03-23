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

AVOCADO_TEST_SKIP_DECORATORS = """
import avocado
from lib_skip_decorators import check_condition

class AvocadoSkipTests(avocado.Test):

    def setUp(self):
        self.log.info('setup executed')

    @avocado.skip('Test skipped')
    def test1(self):
        self.log.info('test executed')

    @avocado.skipIf(check_condition(True),
                    'Skipped due to the True condition')
    def test2(self):
        self.log.info('test executed')

    @avocado.skipUnless(check_condition(False),
                        'Skipped due to the False condition')
    def test3(self):
        self.log.info('test executed')

    def tearDown(self):
        self.log.info('teardown executed')
"""


AVOCADO_TEST_SKIP_LIB = """
def check_condition(condition):
    if condition:
        return True
    return False
"""


AVOCADO_SKIP_DECORATOR_SETUP = """
import avocado

class AvocadoSkipTests(avocado.Test):

    @avocado.skip('Test skipped')
    def setUp(self):
        pass

    def test1(self):
        pass
"""


AVOCADO_SKIP_DECORATOR_TEARDOWN = """
import avocado

class AvocadoSkipTests(avocado.Test):

    def test1(self):
        pass

    @avocado.skip('Test skipped')
    def tearDown(self):
        pass
"""


class TestSkipDecorators(unittest.TestCase):

    def setUp(self):
        os.chdir(basedir)
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)

        test_path = os.path.join(self.tmpdir, 'test_skip_decorators.py')
        self.test_module = script.Script(test_path,
                                         AVOCADO_TEST_SKIP_DECORATORS)
        self.test_module.save()

        lib_path = os.path.join(self.tmpdir, 'lib_skip_decorators.py')
        self.test_lib = script.Script(lib_path, AVOCADO_TEST_SKIP_LIB)
        self.test_lib.save()

        skip_setup_path = os.path.join(self.tmpdir,
                                       'test_skip_decorator_setup.py')
        self.skip_setup = script.Script(skip_setup_path,
                                        AVOCADO_SKIP_DECORATOR_SETUP)
        self.skip_setup.save()

        bad_teardown_path = os.path.join(self.tmpdir,
                                         'test_skip_decorator_teardown.py')
        self.bad_teardown = script.Script(bad_teardown_path,
                                          AVOCADO_SKIP_DECORATOR_TEARDOWN)
        self.bad_teardown.save()

    def test_skip_decorators(self):
        os.chdir(basedir)
        cmd_line = [AVOCADO,
                    'run',
                    '--sysinfo=off',
                    '--job-results-dir',
                    '%s' % self.tmpdir,
                    '%s' % self.test_module,
                    '--json -']
        result = process.run(' '.join(cmd_line), ignore_status=True)
        json_results = json.loads(result.stdout)
        debuglog = json_results['debuglog']

        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertEquals(json_results['skip'], 3)
        self.assertFalse('setup executed' in open(debuglog, 'r').read())
        self.assertFalse('test executed' in open(debuglog, 'r').read())
        self.assertFalse('teardown executed' in open(debuglog, 'r').read())

    def test_skip_setup(self):
        os.chdir(basedir)
        cmd_line = ['./scripts/avocado',
                    'run',
                    '--sysinfo=off',
                    '--job-results-dir',
                    '%s' % self.tmpdir,
                    '%s' % self.skip_setup,
                    '--json -']
        result = process.run(' '.join(cmd_line), ignore_status=True)
        json_results = json.loads(result.stdout)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertEquals(json_results['skip'], 1)

    def test_skip_teardown(self):
        os.chdir(basedir)
        cmd_line = ['./scripts/avocado',
                    'run',
                    '--sysinfo=off',
                    '--job-results-dir',
                    '%s' % self.tmpdir,
                    '%s' % self.bad_teardown,
                    '--json -']
        result = process.run(' '.join(cmd_line), ignore_status=True)
        json_results = json.loads(result.stdout)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_TESTS_FAIL)
        self.assertEquals(json_results['errors'], 1)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
