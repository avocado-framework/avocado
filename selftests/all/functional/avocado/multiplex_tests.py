#!/usr/bin/env python

import unittest
import os
import sys
import tempfile

# simple magic for using scripts within a source tree
basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')
basedir = os.path.abspath(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.append(basedir)

from avocado.utils import process

timeout_multiplex = """
sleeptest:
    sleep_length: 5.0
    timeout: 3
"""


class MultiplexTests(unittest.TestCase):

    def run_and_check(self, cmd_line, expected_rc, expected_lines=None):
        os.chdir(basedir)
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout + result.stderr
        if expected_lines is not None:
            for line in output.splitlines():
                if 'JOB LOG' in line:
                    debug_log = line.split()[-1]
                    debug_log_obj = open(debug_log, 'r')
                    job_log_lines = debug_log_obj.readlines()
                    lines_output = len(job_log_lines)
                    debug_log_obj.close()
            self.assertGreaterEqual(lines_output, expected_lines,
                                    'The multiplexed job log output has less '
                                    'lines than expected\n%s' %
                                    "".join(job_log_lines))
        self.assertEqual(result.exit_status, expected_rc,
                         "Command %s did not return rc "
                         "%d:\n%s" % (cmd_line, expected_rc, result))

    def test_mplex_plugin(self):
        cmd_line = './scripts/avocado multiplex examples/tests/sleeptest.py.data/sleeptest.yaml'
        expected_rc = 0
        self.run_and_check(cmd_line, expected_rc)

    def test_mplex_plugin_nonexistent(self):
        cmd_line = './scripts/avocado multiplex nonexist'
        expected_rc = 2
        self.run_and_check(cmd_line, expected_rc)

    def test_run_mplex_noid(self):
        cmd_line = './scripts/avocado run --multiplex examples/tests/sleeptest.py.data/sleeptest.yaml'
        expected_rc = 2
        self.run_and_check(cmd_line, expected_rc)

    def test_run_mplex_passtest(self):
        cmd_line = './scripts/avocado run passtest --multiplex examples/tests/sleeptest.py.data/sleeptest.yaml'
        expected_rc = 0
        # A typical pass has about 14 lines of output,
        # so we expect the full job log has at least 4 times
        # this value. If that is not the case, something is wrong with
        # the output.
        self.run_and_check(cmd_line, expected_rc, 14*4)

    def test_run_mplex_doublepass(self):
        cmd_line = './scripts/avocado run passtest passtest --multiplex examples/tests/sleeptest.py.data/sleeptest.yaml'
        # Should run 2-times 4 variants of pass test
        self.run_and_check(cmd_line, expected_rc=0, expected_lines=2*4*14)

    def test_run_mplex_failtest(self):
        cmd_line = './scripts/avocado run passtest failtest --multiplex examples/tests/sleeptest.py.data/sleeptest.yaml'
        expected_rc = 1
        self.run_and_check(cmd_line, expected_rc)

    def test_run_mplex_timeout(self):
        # FIXME: Use envtest and check the printed value instead of wait
        with tempfile.NamedTemporaryFile(delete=False) as multiplex_file:
            multiplex_file.write(timeout_multiplex)
            multiplex_file.close()
            cmd_line = ('./scripts/avocado run sleeptest --multiplex %s' %
                        multiplex_file.name)
            expected_rc = 1
            try:
                self.run_and_check(cmd_line, expected_rc)
            finally:
                os.unlink(multiplex_file.name)

if __name__ == '__main__':
    unittest.main()
