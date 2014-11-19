#!/usr/bin/env python

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2014
# Author: Ruda Moura <rmoura@redhat.com>

import os
import sys
import unittest
import tempfile

# simple magic for using scripts within a source tree
basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')
basedir = os.path.abspath(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.append(basedir)

from avocado.utils import process
from avocado.utils import script

SCRIPT_CONTENT = """#!/bin/sh
touch %s_success
exec -- $@
"""

DUMMY_CONTENT = """#!/bin/sh
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
        cmd_line = './scripts/avocado run datadir --wrapper %s' % self.script.path
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 0
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertTrue(os.path.exists(self.tmpfile + '_success'),
                        "Wrapper did not create file *_success")

    def test_process_wrapper(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run datadir --wrapper %s:datadir' % self.script.path
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 0
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertTrue(os.path.exists(self.tmpfile + '_success'),
                        "Wrapper did not create file *_success")

    def test_both_wrappers(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run datadir --wrapper %s --wrapper %s:datadir' % (self.dummy.path, self.script.path)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 0
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertTrue(os.path.exists(self.tmpfile + '_success'),
                        "Wrapper did not create file *_success")

    def tearDown(self):
        self.script.remove()
        self.dummy.remove()
        try:
            os.remove(self.tmpfile)
            os.remove(self.tmpfile + '_success')
        except OSError:
            pass


if __name__ == '__main__':
    unittest.main()
