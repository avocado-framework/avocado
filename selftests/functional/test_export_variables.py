import os
import unittest

from avocado import VERSION
from avocado.core import exit_codes
from avocado.utils import process, script
from selftests.utils import AVOCADO, BASEDIR, TestCaseTmpDir

SCRIPT_CONTENT = """#!/bin/sh
echo "Avocado Version: $AVOCADO_VERSION"
echo "Avocado Test basedir: $AVOCADO_TEST_BASEDIR"
echo "Avocado Test workdir: $AVOCADO_TEST_WORKDIR"
echo "Avocado Test logdir: $AVOCADO_TEST_LOGDIR"
echo "Avocado Test logfile: $AVOCADO_TEST_LOGFILE"
echo "Avocado Test outputdir: $AVOCADO_TEST_OUTPUTDIR"

test "$AVOCADO_VERSION" = "{version}" -a \
     -d "$AVOCADO_TEST_BASEDIR" -a \
     -d "$AVOCADO_TEST_WORKDIR" -a \
     -d "$AVOCADO_TEST_LOGDIR" -a \
     -f "$AVOCADO_TEST_LOGFILE" -a \
     -d "$AVOCADO_TEST_OUTPUTDIR"
""".format(version=VERSION)


class EnvironmentVariablesTest(TestCaseTmpDir):

    def setUp(self):
        super(EnvironmentVariablesTest, self).setUp()
        self.script = script.TemporaryScript(
            'version.sh',
            SCRIPT_CONTENT,
            'avocado_env_vars_functional')
        self.script.save()

    def test_environment_vars(self):
        os.chdir(BASEDIR)
        cmd_line = ('%s run --job-results-dir %s %s'
                    % (AVOCADO, self.tmpdir.name, self.script.path))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))

    def tearDown(self):
        super(EnvironmentVariablesTest, self).tearDown()
        self.script.remove()


if __name__ == '__main__':
    unittest.main()
