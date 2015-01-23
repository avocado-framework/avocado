#!/usr/bin/env python

import os
import sys
import unittest
import tempfile

# simple magic for using scripts within a source tree
basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..',
                       '..', '..')
basedir = os.path.abspath(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.append(basedir)

from avocado.utils import process
from avocado.utils import script

SCRIPT_CONTENT = """#!/bin/bash
touch %s
exec -- $@
"""

DUMMY_CONTENT = """#!/bin/bash
exec -- $@
"""


class WrapperTest(unittest.TestCase):

    def setUp(self):
        self.tmpfile = tempfile.mktemp()
        self.script = script.TemporaryScript(
            'success.sh',
            SCRIPT_CONTENT % self.tmpfile,
            'avocado_wrapper_functional')
        self.script.save()
        self.dummy = script.TemporaryScript(
            'dummy.sh',
            DUMMY_CONTENT,
            'avocado_wrapper_functional')
        self.dummy.save()

    def test_global_wrapper(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --wrapper %s '
                    'examples/tests/datadir.py' % self.script.path)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 0
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertTrue(os.path.exists(self.tmpfile),
                        "Wrapper did not touch the tmp file %s\nStdout: "
                        "%s\nCmdline: %s" %
                        (self.tmpfile, result.stdout, cmd_line))

    def test_process_wrapper(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --wrapper %s:*/datadir '
                    'examples/tests/datadir.py' % self.script.path)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 0
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertTrue(os.path.exists(self.tmpfile),
                        "Wrapper did not touch the tmp file %s\nStdout: "
                        "%s\nStdout: %s" %
                        (self.tmpfile, cmd_line, result.stdout))

    def test_both_wrappers(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --wrapper %s --wrapper %s:*/datadir '
                    'examples/tests/datadir.py' % (self.dummy.path,
                                                   self.script.path))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 0
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertTrue(os.path.exists(self.tmpfile),
                        "Wrapper did not touch the tmp file %s\nStdout: "
                        "%s\nStdout: %s" %
                        (self.tmpfile, cmd_line, result.stdout))

    def tearDown(self):
        self.script.remove()
        self.dummy.remove()
        try:
            os.remove(self.tmpfile)
        except OSError:
            pass


if __name__ == '__main__':
    unittest.main()
