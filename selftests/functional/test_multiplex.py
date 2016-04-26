#!/usr/bin/env python

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


DEBUG_OUT = """Variant 16:    amd@examples/mux-environment.yaml, virtio@examples/mux-environment.yaml, mint@examples/mux-environment.yaml, debug@examples/mux-environment.yaml
    /distro/mint:init         => systemv@examples/mux-environment.yaml:/distro/mint
    /env/debug:opt_CFLAGS     => -O0 -g@examples/mux-environment.yaml:/env/debug
    /hw/cpu/amd:cpu_CFLAGS    => -march=athlon64@examples/mux-environment.yaml:/hw/cpu/amd
    /hw/cpu/amd:joinlist      => ['first_item']@examples/mux-selftest.yaml:/hw/cpu + ['second', 'third']@examples/mux-selftest.yaml:/hw/cpu/amd
    /hw/disk/virtio:disk_type => virtio@examples/mux-environment.yaml:/hw/disk/virtio
    /hw/disk:corruptlist      => nonlist@examples/mux-selftest.yaml:/hw/disk
    /hw:corruptlist           => ['upper_node_list']@examples/mux-selftest.yaml:/hw
"""


class MultiplexTests(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)

    def run_and_check(self, cmd_line, expected_rc):
        os.chdir(basedir)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, expected_rc,
                         "Command %s did not return rc "
                         "%d:\n%s" % (cmd_line, expected_rc, result))
        return result

    def test_mplex_plugin(self):
        cmd_line = './scripts/avocado multiplex examples/tests/sleeptest.py.data/sleeptest.yaml'
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc)

    def test_mplex_plugin_nonexistent(self):
        cmd_line = './scripts/avocado multiplex nonexist'
        expected_rc = exit_codes.AVOCADO_JOB_FAIL
        result = self.run_and_check(cmd_line, expected_rc)
        self.assertIn('No such file or directory', result.stderr)

    def test_mplex_debug(self):
        cmd_line = ('./scripts/avocado multiplex -c -d '
                    '/:examples/mux-selftest.yaml '
                    '/:examples/mux-environment.yaml '
                    '/:examples/mux-selftest.yaml '
                    '/:examples/mux-environment.yaml')
        expected_rc = exit_codes.AVOCADO_ALL_OK
        result = self.run_and_check(cmd_line, expected_rc)
        self.assertIn(DEBUG_OUT, result.stdout)

    def test_run_mplex_noid(self):
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    '--multiplex examples/tests/sleeptest.py.data/sleeptest.yaml' % self.tmpdir)
        expected_rc = exit_codes.AVOCADO_JOB_FAIL
        self.run_and_check(cmd_line, expected_rc)

    def test_run_mplex_passtest(self):
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    'passtest.py --multiplex '
                    'examples/tests/sleeptest.py.data/sleeptest.yaml'
                    % self.tmpdir)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc)

    def test_run_mplex_doublepass(self):
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    'passtest.py passtest.py --multiplex '
                    'examples/tests/sleeptest.py.data/sleeptest.yaml'
                    % self.tmpdir)
        self.run_and_check(cmd_line, expected_rc=0)

    def test_run_mplex_failtest(self):
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    'passtest.py failtest.py --multiplex '
                    'examples/tests/sleeptest.py.data/sleeptest.yaml'
                    % self.tmpdir)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.run_and_check(cmd_line, expected_rc)

    def test_run_double_mplex(self):
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    'passtest.py --multiplex '
                    'examples/tests/sleeptest.py.data/sleeptest.yaml '
                    'examples/tests/sleeptest.py.data/sleeptest.yaml'
                    % self.tmpdir)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc)

    def test_run_mplex_params(self):
        for variant_msg in (('/run/short', 'A'),
                            ('/run/medium', 'ASDFASDF'),
                            ('/run/long', 'This is very long\nmultiline\ntext.')):
            variant, msg = variant_msg
            cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off examples/tests/env_variables.sh '
                        '--multiplex examples/tests/env_variables.sh.data/env_variables.yaml '
                        '--filter-only %s --show-job-log' % (self.tmpdir, variant))
            expected_rc = exit_codes.AVOCADO_ALL_OK
            result = self.run_and_check(cmd_line, expected_rc)

            msg_lines = msg.splitlines()
            msg_header = '[stdout] Custom variable: %s' % msg_lines[0]
            self.assertIn(msg_header, result.stdout,
                          "Multiplexed variable should produce:"
                          "\n  %s\nwhich is not present in the output:\n  %s"
                          % (msg_header, "\n  ".join(result.stdout.splitlines())))
            for msg_remain in msg_lines[1:]:
                self.assertIn('[stdout] %s' % msg_remain, result.stdout,
                              "Multiplexed variable should produce:"
                              "\n  %s\nwhich is not present in the output:\n  %s"
                              % (msg_remain, "\n  ".join(result.stdout.splitlines())))

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

if __name__ == '__main__':
    unittest.main()
