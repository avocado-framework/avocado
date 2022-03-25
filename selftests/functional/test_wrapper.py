import os
import tempfile
import unittest

from avocado.core import exit_codes
from avocado.utils import path as utils_path
from avocado.utils import process, script
from selftests.utils import AVOCADO, BASEDIR, TestCaseTmpDir

SCRIPT_CONTENT = """#!/bin/bash
touch %s
exec -- $@
"""

DUMMY_CONTENT = """#!/bin/bash
exec -- $@
"""


def missing_binary(binary):
    try:
        utils_path.find_command(binary)
        return False
    except utils_path.CmdNotFoundError:
        return True


class WrapperTest(TestCaseTmpDir):

    def setUp(self):
        super().setUp()
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

    @unittest.skipIf(missing_binary('cc'),
                     "C compiler is required by the underlying datadir.py test")
    def test_global_wrapper(self):
        os.chdir(BASEDIR)
        cmd_line = (f'{AVOCADO} run --job-results-dir {self.tmpdir.name} '
                    f'--disable-sysinfo --wrapper {self.script.path} '
                    f'--test-runner=runner examples/tests/datadir.py')
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")
        self.assertTrue(os.path.exists(self.tmpfile),
                        (f"Wrapper did not touch the tmp file {self.tmpfile}\n"
                         f"Stdout: {result.stdout}\nCmdline: {cmd_line}"))

    @unittest.skipIf(missing_binary('cc'),
                     "C compiler is required by the underlying datadir.py test")
    def test_process_wrapper(self):
        os.chdir(BASEDIR)
        cmd_line = (f'{AVOCADO} run --job-results-dir {self.tmpdir.name} '
                    f'--disable-sysinfo --test-runner=runner --wrapper '
                    f'{self.script.path}:*/datadir examples/tests/datadir.py')
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")
        self.assertTrue(os.path.exists(self.tmpfile),
                        (f"Wrapper did not touch the tmp file {self.tmpfile}\n"
                         f"Stdout: {cmd_line}\nStdout: {result.stdout}"))

    @unittest.skipIf(missing_binary('cc'),
                     "C compiler is required by the underlying datadir.py test")
    def test_both_wrappers(self):
        os.chdir(BASEDIR)
        cmd_line = (f'{AVOCADO} run --job-results-dir {self.tmpdir.name} '
                    f'--disable-sysinfo '
                    f'--wrapper {self.dummy.path} --test-runner=runner '
                    f'--wrapper '
                    f'{self.script.path}:*/datadir examples/tests/datadir.py')
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")
        self.assertTrue(os.path.exists(self.tmpfile),
                        (f"Wrapper did not touch the tmp file {self.tmpfile}\n"
                         f"Stdout: {cmd_line}\nStdout: {result.stdout}"))

    def tearDown(self):
        super().tearDown()
        self.script.remove()
        self.dummy.remove()
        try:
            os.remove(self.tmpfile)
        except OSError:
            pass


if __name__ == '__main__':
    unittest.main()
