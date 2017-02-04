import json
import os
import shutil
import sys
import tempfile

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

from avocado.core import exit_codes
from avocado.utils import process

basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
basedir = os.path.abspath(basedir)


AVOCADO_TEST_SKIP_DECORATORS = """#!/usr/bin/env python
import avocado
from avocado_test_skip_lib import check_condition

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


AVOCADO_TEST_SKIP_LIB = """#!/usr/bin/env python

def check_condition(condition):
    if condition:
        return True
    return False
"""


class TestSkipDecorators(unittest.TestCase):

    def setUp(self):
        os.chdir(basedir)
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        self.test_module = os.path.join(self.tmpdir,
                                        'avocado_test_skip_decorators.py')
        with open(self.test_module, 'w') as f_test_module:
            f_test_module.write(AVOCADO_TEST_SKIP_DECORATORS)
        self.test_lib = os.path.join(self.tmpdir,
                                     'avocado_test_skip_lib.py')
        with open(self.test_lib, 'w') as f_test_lib:
            f_test_lib.write(AVOCADO_TEST_SKIP_LIB)

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
