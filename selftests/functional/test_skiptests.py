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
from avocado.utils import script
from avocado.utils import process

basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
basedir = os.path.abspath(basedir)


AVOCADO_TEST_SKIP_DECORATORS = """#!/usr/bin/env python
from avocado import Test

class AvocadoSkipTests(Test):

    @Test.skipIf(True, 'Skipped due to the True condition')
    def test1(self):
        pass

    @Test.skipUnless(False, 'Skipped due to the False condition')
    def test2(self):
        pass
"""


class TestSkipDecorators(unittest.TestCase):

    def setUp(self):
        os.chdir(basedir)
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)

    def test_skip_decorators(self):
        test_decorators = script.TemporaryScript(
            'avocado_test_skip_decorators.py',
            AVOCADO_TEST_SKIP_DECORATORS)
        test_decorators.save()
        os.chdir(basedir)
        cmd_line = ['./scripts/avocado',
                    'run',
                    '--sysinfo=off',
                    '--job-results-dir',
                    '%s' % self.tmpdir,
                    '%s' % test_decorators,
                    '--json -']
        result = process.run(' '.join(cmd_line))
        json_results = json.loads(result.stdout)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertEquals(json_results['skip'], 2)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
