import os
import sys
import tempfile
import shutil

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

from avocado import VERSION
from avocado.core import exit_codes
from avocado.utils import process
from avocado.utils import script

basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
basedir = os.path.abspath(basedir)


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
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        self.script = script.TemporaryScript(
            'version.sh',
            SCRIPT_CONTENT,
            'avocado_env_vars_functional')
        self.script.save()

    def test_environment_vars(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --job-results-dir %s --sysinfo=on %s' % (self.tmpdir, self.script.path)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))

    def tearDown(self):
        self.script.remove()
        shutil.rmtree(self.tmpdir)

if __name__ == '__main__':
    unittest.main()
