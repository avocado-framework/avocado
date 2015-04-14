#!/usr/bin/env python

import os
import sys
import tempfile
import shutil

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

# simple magic for using scripts within a source tree
basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..',
                       '..', '..')
basedir = os.path.abspath(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.append(basedir)

from avocado.utils import process

DEBUG_OUT = """Variant 16:    amd@examples/mux-environment.yaml, virtio@examples/mux-environment.yaml, mint@examples/mux-environment.yaml, debug@examples/mux-environment.yaml
    corruptlist: nonlist@examples/mux-selftest.yaml:/hw/disk
    cpu_CFLAGS: -march=athlon64@examples/mux-environment.yaml:/hw/cpu/amd
    disk_type: virtio@examples/mux-environment.yaml:/hw/disk/virtio
    init: systemv@examples/mux-environment.yaml:/distro/mint
    joinlist: ['first_item']@examples/mux-selftest.yaml:/hw/cpu + ['second', 'third']@examples/mux-selftest.yaml:/hw/cpu/amd
    opt_CFLAGS: -O0 -g@examples/mux-environment.yaml:/env/debug
"""


class MultiplexTests(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def run_and_check(self, cmd_line, expected_rc, expected_lines=None):
        os.chdir(basedir)
        result = process.run(cmd_line, ignore_status=True)
        if expected_lines is not None:
            for line in result.stdout.splitlines():
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
            self.assertLess(lines_output, expected_lines * 1.2,
                            'The multiplexed job log output has more '
                            'lines than expected\n%s'
                            % "".join(job_log_lines))
        self.assertEqual(result.exit_status, expected_rc,
                         "Command %s did not return rc "
                         "%d:\n%s" % (cmd_line, expected_rc, result))
        return result

    def test_mplex_plugin(self):
        cmd_line = './scripts/avocado multiplex examples/tests/sleeptest.py.data/sleeptest.yaml'
        expected_rc = 0
        self.run_and_check(cmd_line, expected_rc)

    def test_mplex_plugin_nonexistent(self):
        cmd_line = './scripts/avocado multiplex nonexist'
        expected_rc = 2
        result = self.run_and_check(cmd_line, expected_rc)
        self.assertIn('No such file or directory', result.stderr)

    def test_mplex_debug(self):
        cmd_line = ('./scripts/avocado multiplex -c -d '
                    'examples/mux-selftest.yaml examples/mux-environment.yaml '
                    'examples/mux-selftest.yaml examples/mux-environment.yaml')
        expected_rc = 0
        result = self.run_and_check(cmd_line, expected_rc)
        self.assertIn(DEBUG_OUT, result.stdout)

    def test_run_mplex_noid(self):
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    '--multiplex examples/tests/sleeptest.py.data/sleeptest.yaml' % self.tmpdir)
        expected_rc = 2
        self.run_and_check(cmd_line, expected_rc)

    def test_run_mplex_passtest(self):
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off passtest '
                    '--multiplex examples/tests/sleeptest.py.data/sleeptest.yaml' % self.tmpdir)
        expected_rc = 0
        # Header is 2 lines + 5 lines per each test
        self.run_and_check(cmd_line, expected_rc, 2 + 5 * 4)

    def test_run_mplex_doublepass(self):
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off passtest passtest '
                    '--multiplex examples/tests/sleeptest.py.data/sleeptest.yaml' % self.tmpdir)
        # Header is 2 lines + 5 lines per each test * 2 tests
        self.run_and_check(cmd_line, expected_rc=0,
                           expected_lines=2 + 2 * 5 * 4)

    def test_run_mplex_failtest(self):
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off passtest failtest '
                    '--multiplex examples/tests/sleeptest.py.data/sleeptest.yaml' % self.tmpdir)
        expected_rc = 1
        self.run_and_check(cmd_line, expected_rc)

    def test_run_double_mplex(self):
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off passtest --multiplex '
                    'examples/tests/sleeptest.py.data/sleeptest.yaml '
                    'examples/tests/sleeptest.py.data/sleeptest.yaml' % self.tmpdir)
        expected_rc = 0
        # Header is 2 lines + 5 lines per each test (mux files are merged thus
        # only 1x4 variants are generated as in mplex_doublepass test)
        self.run_and_check(cmd_line, expected_rc, 2 + 5 * 4)

    def test_run_mplex_params(self):
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off examples/tests/env_variables.sh '
                    '--multiplex examples/tests/env_variables.sh.data'
                    '/env_variables.yaml '
                    '--show-job-log' % self.tmpdir)
        expected_rc = 0
        result = self.run_and_check(cmd_line, expected_rc)
        for msg in ('A', 'ASDFASDF', 'This is very long\nmultiline\ntext.'):
            msg = ('[stdout] Custom variable: ' +
                   '\n[stdout] '.join(msg.splitlines()))
            self.assertIn(msg, result.stdout, "Multiplexed variable should "
                                              "produce:"
                          "\n  %s\nwhich is not present in the output:\n  %s"
                          % ("\n  ".join(msg.splitlines()),
                             "\n  ".join(result.stdout.splitlines())))

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

if __name__ == '__main__':
    unittest.main()
