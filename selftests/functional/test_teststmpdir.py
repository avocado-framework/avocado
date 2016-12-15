#!/usr/bin/env python

import os
import sys
import tempfile
import shutil

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

from avocado.core import exit_codes
from avocado.utils import process
from avocado.utils import script


basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
basedir = os.path.abspath(basedir)

INSTRUMENTED_SCRIPT = """import os
from avocado import Test
class MyTest(Test):
    def test1(self):
        file = os.path.join(self.teststmpdir, 'file1.txt')
        open(file, "w+").close()
        path, dirs, files = os.walk(self.teststmpdir).next()
        if len(files) != 1:
            self.fail()

"""

SIMPLE_SCRIPT = """#!/bin/bash
touch ${AVOCADO_TESTS_COMMON_TMPDIR}/file1.txt
if [ $(ls ${AVOCADO_TESTS_COMMON_TMPDIR} | wc -l) == 1 ]
then
    exit 0
else
    exit 1
fi
"""


class TestsTmpDirTests(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)

    def run_and_check(self, cmd_line, expected_rc):
        os.chdir(basedir)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, expected_rc,
                         "Command %s did not return rc "
                         "%d:\n%s" % (cmd_line, expected_rc, result))
        return result

    def test_instrumented(self):
        instrumented_test = script.TemporaryScript(
            'test_instrumented.py',
            INSTRUMENTED_SCRIPT)
        instrumented_test.save()
        cmd_line = ("./scripts/avocado run --sysinfo=off --job-results-dir %s "
                    "%s" % (self.tmpdir, instrumented_test))
        self.run_and_check(cmd_line, exit_codes.AVOCADO_ALL_OK)

    def test_simple(self):
        simple_test = script.TemporaryScript(
            'test_simple.py',
            SIMPLE_SCRIPT)
        simple_test.save()
        cmd_line = ("./scripts/avocado run --sysinfo=off --job-results-dir %s "
                    "%s" % (self.tmpdir, simple_test))
        self.run_and_check(cmd_line, exit_codes.AVOCADO_ALL_OK)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
