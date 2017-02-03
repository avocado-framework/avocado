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


AVOCADO_TEST_SKIP_DECORATORS = """
import avocado
from lib_skip_decorators import check_condition

class AvocadoSkipTests(avocado.Test):

    @avocado.skip('Test skipped')
    def test1(self):
        pass

    @avocado.skipIf(check_condition(True),
                    'Skipped due to the True condition')
    def test2(self):
        pass

    @avocado.skipUnless(check_condition(False),
                        'Skipped due to the False condition')
    def test3(self):
        pass

    @avocado.skipIf(False)
    def test4(self):
        pass

    @avocado.skipUnless(True)
    def test5(self):
        pass

    @avocado.skip()
    def test6(self):
        pass
"""


AVOCADO_TEST_SKIP_LIB = """
def check_condition(condition):
    if condition:
        return True
    return False
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

    def test_skip_decorators(self):
        os.chdir(basedir)
        cmd_line = ['./scripts/avocado',
                    'run',
                    '--sysinfo=off',
                    '--job-results-dir',
                    '%s' % self.tmpdir,
                    '%s' % self.test_module,
                    '--json -']
        result = process.run(' '.join(cmd_line), ignore_status=True)
        json_results = json.loads(result.stdout)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertEquals(json_results['pass'], 2)
        self.assertEquals(json_results['skip'], 4)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
