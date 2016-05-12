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


basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
basedir = os.path.abspath(basedir)


class ReplayTests(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        cmd_line = ('./scripts/avocado run passtest.py '
                    '--multiplex '
                    'examples/tests/sleeptest.py.data/sleeptest.yaml '
                    '--job-results-dir %s --sysinfo=off --json -' %
                    self.tmpdir)
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

    def test_run_replay_noid(self):
        cmd_line = ('./scripts/avocado run --replay %s'
                    '--job-results-dir %s --replay-data-dir %s --sysinfo=off' %
                    ('foo', self.tmpdir, self.jobdir))
        expected_rc = exit_codes.AVOCADO_JOB_FAIL
        self.run_and_check(cmd_line, expected_rc)

    def test_run_replay_data(self):
        file_list = ['multiplex', 'config', 'urls', 'pwd', 'args']
        for filename in file_list:
            path = os.path.join(self.jobdir, 'replay', filename)
            self.assertTrue(glob.glob(path))

    def test_run_replay(self):
        cmd_line = ('./scripts/avocado run --replay %s '
                    '--job-results-dir %s --replay-data-dir %s --sysinfo=off'
                    % (self.jobid, self.tmpdir, self.jobdir))
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc)

    def test_run_replay_partialid(self):
        partial_id = self.jobid[:5]
        cmd_line = ('./scripts/avocado run --replay %s '
                    '--job-results-dir %s --replay-data-dir %s --sysinfo=off'
                    % (partial_id, self.tmpdir, self.jobdir))
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc)

    def test_run_replay_invalidignore(self):
        cmd_line = ('./scripts/avocado run --replay %s --replay-ignore foo'
                    '--job-results-dir %s --replay-data-dir %s --sysinfo=off'
                    % (self.jobid, self.tmpdir, self.jobdir))
        expected_rc = exit_codes.AVOCADO_FAIL
        result = self.run_and_check(cmd_line, expected_rc)
        msg = 'Invalid --replay-ignore option. Valid options are ' \
              '(more than one allowed): mux,config'
        self.assertIn(msg, result.stderr)

    def test_run_replay_ignoremux(self):
        cmd_line = ('./scripts/avocado run --replay %s --replay-ignore mux '
                    '--job-results-dir %s --replay-data-dir %s --sysinfo=off'
                    % (self.jobid, self.tmpdir, self.jobdir))
        expected_rc = exit_codes.AVOCADO_ALL_OK
        result = self.run_and_check(cmd_line, expected_rc)
        msg = 'Ignoring multiplex from source job with --replay-ignore.'
        self.assertIn(msg, result.stderr)

    def test_run_replay_invalidstatus(self):
        cmd_line = ('./scripts/avocado run --replay %s --replay-test-status E '
                    '--job-results-dir %s --replay-data-dir %s --sysinfo=off'
                    % (self.jobid, self.tmpdir, self.jobdir))
        expected_rc = exit_codes.AVOCADO_FAIL
        result = self.run_and_check(cmd_line, expected_rc)
        msg = 'Invalid --replay-test-status option. Valid options are (more ' \
              'than one allowed): SKIP,ERROR,FAIL,WARN,PASS,INTERRUPTED'
        self.assertIn(msg, result.stderr)

    def test_run_replay_statusfail(self):
        cmd_line = ('./scripts/avocado run --replay %s --replay-test-status '
                    'FAIL --job-results-dir %s --replay-data-dir %s '
                    '--sysinfo=off' % (self.jobid, self.tmpdir, self.jobdir))
        expected_rc = exit_codes.AVOCADO_ALL_OK
        result = self.run_and_check(cmd_line, expected_rc)
        msg = 'RESULTS    : PASS 0 | ERROR 0 | FAIL 0 | SKIP 4 | WARN 0 | INTERRUPT 0'
        self.assertIn(msg, result.stdout)

    def test_run_replay_remotefail(self):
        cmd_line = ('./scripts/avocado run --replay %s --remote-hostname '
                    'localhost --job-results-dir %s --replay-data-dir %s '
                    '--sysinfo=off' % (self.jobid, self.tmpdir, self.jobdir))
        expected_rc = exit_codes.AVOCADO_FAIL
        result = self.run_and_check(cmd_line, expected_rc)
        msg = "Currently we don't replay jobs in remote hosts."
        self.assertIn(msg, result.stderr)

    def test_run_replay_status_and_mux(self):
        cmd_line = ('./scripts/avocado run --replay %s --multiplex '
                    'examples/mux-environment.yaml --replay-test-status FAIL '
                    '--job-results-dir %s --replay-data-dir %s '
                    '--sysinfo=off' % (self.jobid, self.tmpdir, self.jobdir))
        expected_rc = exit_codes.AVOCADO_FAIL
        result = self.run_and_check(cmd_line, expected_rc)
        msg = "Option --replay-test-status is incompatible with "\
              "--multiplex."
        self.assertIn(msg, result.stderr)

    def test_run_replay_status_and_urls(self):
        cmd_line = ('./scripts/avocado run sleeptest --replay %s '
                    '--replay-test-status FAIL --job-results-dir %s '
                    '--replay-data-dir %s --sysinfo=off' %
                    (self.jobid, self.tmpdir, self.jobdir))
        expected_rc = exit_codes.AVOCADO_FAIL
        result = self.run_and_check(cmd_line, expected_rc)
        msg = "Option --replay-test-status is incompatible with "\
              "test URLs given on the command line."
        self.assertIn(msg, result.stderr)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
