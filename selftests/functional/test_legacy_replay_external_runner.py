import glob
import os
import unittest

from avocado.core import exit_codes
from avocado.utils import process, script
from selftests.utils import AVOCADO, TestCaseTmpDir


class ReplayExtRunnerTests(TestCaseTmpDir):

    def setUp(self):
        super(ReplayExtRunnerTests, self).setUp()
        test = script.make_script(os.path.join(self.tmpdir.name, 'test'), 'exit 0')
        cmd_line = ('%s run %s '
                    '--external-runner /bin/bash '
                    '--job-results-dir %s --disable-sysinfo --json -'
                    % (AVOCADO, test, self.tmpdir.name))
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc)
        self.jobdir = ''.join(glob.glob(os.path.join(self.tmpdir.name, 'job-*')))
        idfile = ''.join(os.path.join(self.jobdir, 'id'))
        with open(idfile, 'r') as f:
            self.jobid = f.read().strip('\n')

    def run_and_check(self, cmd_line, expected_rc):
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, expected_rc,
                         "Command %s did not return rc "
                         "%d:\n%s" % (cmd_line, expected_rc, result))
        return result

    def test_run_replay_external_runner(self):
        cmd_line = ('%s run --replay %s '
                    '--external-runner /bin/sh '
                    '--job-results-dir %s --disable-sysinfo'
                    % (AVOCADO, self.jobid, self.tmpdir.name))
        expected_rc = exit_codes.AVOCADO_ALL_OK
        result = self.run_and_check(cmd_line, expected_rc)
        msg = (b"Overriding the replay external-runner with the "
               b"--external-runner value given on the command line.")
        self.assertIn(msg, result.stderr)


if __name__ == '__main__':
    unittest.main()
