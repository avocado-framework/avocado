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
import shutil
import tempfile
import unittest

# simple magic for using scripts within a source tree
basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')
basedir = os.path.abspath(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.append(basedir)

from avocado.version import VERSION
from avocado.utils import process

SCRIPT_CONTENT = """#!/bin/sh
echo "Avocado Version: $AVOCADO_VERSION"
echo "Avocado Test basedir: $AVOCADO_TEST_BASEDIR"
echo "Avocado Test datadir: $AVOCADO_TEST_DATADIR"
echo "Avocado Test workdir: $AVOCADO_TEST_WORKDIR"
echo "Avocado Test srcdir: $AVOCADO_TEST_SRCDIR"
echo "Avocado Test logdir: $AVOCADO_TEST_LOGDIR"
echo "Avocado Test logfile: $AVOCADO_TEST_LOGFILE"
echo "Avocado Test outputdir: $AVOCADO_TEST_OUTPUTDIR"
echo "Avocado Test sysinfodir: $AVOCADO_TEST_SYSINFODIR"

test "$AVOCADO_VERSION" = "{version}" -a \
     -d "$AVOCADO_TEST_BASEDIR" -a \
     -d "$AVOCADO_TEST_WORKDIR" -a \
     -d "$AVOCADO_TEST_SRCDIR" -a \
     -d "$AVOCADO_TEST_LOGDIR" -a \
     -f "$AVOCADO_TEST_LOGFILE" -a \
     -d "$AVOCADO_TEST_OUTPUTDIR" -a \
     -d "$AVOCADO_TEST_SYSINFODIR"
""".format(version=VERSION)


class EnvironmentVariablesTest(unittest.TestCase):

    def setUp(self):
        self.base_logdir = tempfile.mkdtemp(prefix='avocado_env_vars_functional')
        self.script = os.path.join(self.base_logdir, 'version.sh')
        with open(self.script, 'w') as script_obj:
            script_obj.write(SCRIPT_CONTENT)
        os.chmod(self.script, 0775)

    def test_environment_vars(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run %s' % self.script
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 0
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))

    def tearDown(self):
        if os.path.isdir(self.base_logdir):
            shutil.rmtree(self.base_logdir, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
