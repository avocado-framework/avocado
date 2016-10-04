#!/usr/bin/env python

import glob
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


class ReplayExtRunnerTests(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        test = script.make_script(os.path.join(self.tmpdir, 'test'), 'exit 0')
        cmd_line = ('./scripts/avocado run %s '
                    '-m examples/tests/sleeptest.py.data/sleeptest.yaml '
                    '--external-runner /bin/bash '
                    '--job-results-dir %s --sysinfo=off --json -' %
                    (test, self.tmpdir))
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc)
        self.jobdir = ''.join(glob.glob(os.path.join(self.tmpdir, 'job-*')))
        idfile = ''.join(os.path.join(self.jobdir, 'id'))
        with open(idfile, 'r') as f:
            self.jobid = f.read().strip('\n')

    def run_and_check(self, cmd_line, expected_rc):
        os.chdir(basedir)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, expected_rc,
                         "Command %s did not return rc "
                         "%d:\n%s" % (cmd_line, expected_rc, result))
        return result

    def test_run_replay_external_runner(self):
        cmd_line = ('./scripts/avocado run --replay %s '
                    '--external-runner /bin/sh '
                    '--job-results-dir %s --replay-data-dir %s --sysinfo=off' %
                    (self.jobid, self.tmpdir, self.jobdir))
        expected_rc = exit_codes.AVOCADO_ALL_OK
        result = self.run_and_check(cmd_line, expected_rc)
        msg = "Overriding the replay external-runner with the "\
              "--external-runner value given on the command line."
        self.assertIn(msg, result.stderr)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
