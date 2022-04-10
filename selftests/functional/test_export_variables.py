import os
import unittest

from avocado import VERSION
from avocado.core import exit_codes
from avocado.utils import process, script
from selftests.utils import AVOCADO, BASEDIR, TestCaseTmpDir

SCRIPT_CONTENT = (f"""#!/bin/sh
echo "Avocado Version: $AVOCADO_VERSION"
echo "Avocado Test workdir: $AVOCADO_TEST_WORKDIR"
echo "Avocado Test outputdir: $AVOCADO_TEST_OUTPUTDIR"

test "$AVOCADO_VERSION" = "{VERSION}" -a \
     -d "$AVOCADO_TEST_WORKDIR" -a \
     -d "$AVOCADO_TEST_OUTPUTDIR"
""")


class EnvironmentVariablesTest(TestCaseTmpDir):

    def setUp(self):
        super().setUp()
        self.script = script.TemporaryScript(
            'version.sh',
            SCRIPT_CONTENT,
            'avocado_env_vars_functional')
        self.script.save()

    def test_environment_vars(self):
        os.chdir(BASEDIR)
        cmd_line = (f'{AVOCADO} run --job-results-dir {self.tmpdir.name} '
                    f'{self.script.path}')
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")

    def tearDown(self):
        super().tearDown()
        self.script.remove()


if __name__ == '__main__':
    unittest.main()
