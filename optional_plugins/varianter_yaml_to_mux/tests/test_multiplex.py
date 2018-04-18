import os
import tempfile
import shutil
import unittest
import sys

from avocado.core import exit_codes
from avocado.utils import process


basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
basedir = os.path.abspath(basedir)

AVOCADO = os.environ.get("UNITTEST_AVOCADO_CMD", "./scripts/avocado")

DEBUG_OUT = b"""
Variant mint-debug-amd-virtio-935e:    amd@optional_plugins/varianter_yaml_to_mux/tests/.data/mux-environment.yaml, virtio@optional_plugins/varianter_yaml_to_mux/tests/.data/mux-environment.yaml, mint@optional_plugins/varianter_yaml_to_mux/tests/.data/mux-environment.yaml, debug@optional_plugins/varianter_yaml_to_mux/tests/.data/mux-environment.yaml
    /distro/mint:init         => systemv@optional_plugins/varianter_yaml_to_mux/tests/.data/mux-environment.yaml:/distro/mint
    /env/debug:opt_CFLAGS     => -O0 -g@optional_plugins/varianter_yaml_to_mux/tests/.data/mux-environment.yaml:/env/debug
    /hw/cpu/amd:cpu_CFLAGS    => -march=athlon64@optional_plugins/varianter_yaml_to_mux/tests/.data/mux-environment.yaml:/hw/cpu/amd
    /hw/cpu/amd:joinlist      => ['first_item']@optional_plugins/varianter_yaml_to_mux/tests/.data/mux-selftest.yaml:/hw/cpu + ['second', 'third']@optional_plugins/varianter_yaml_to_mux/tests/.data/mux-selftest.yaml:/hw/cpu/amd
    /hw/disk/virtio:disk_type => virtio@optional_plugins/varianter_yaml_to_mux/tests/.data/mux-environment.yaml:/hw/disk/virtio
    /hw/disk:corruptlist      => nonlist@optional_plugins/varianter_yaml_to_mux/tests/.data/mux-selftest.yaml:/hw/disk
    /hw:corruptlist           => ['upper_node_list']@optional_plugins/varianter_yaml_to_mux/tests/.data/mux-selftest.yaml:/hw
"""


class MultiplexTests(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)

    def run_and_check(self, cmd_line, expected_rc, tests=None):
        os.chdir(basedir)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, expected_rc,
                         "Command %s did not return rc "
                         "%d:\n%s" % (cmd_line, expected_rc, result))
        if tests is not None:
            exp = ("PASS %s | ERROR 0 | FAIL %s | SKIP 0 | WARN 0 | "
                   "INTERRUPT 0" % tests)
            self.assertIn(exp, result.stdout_text, "%s not in stdout:\n%s"
                          % (exp, result))
        return result

    def test_mplex_plugin(self):
        cmd_line = ('%s variants -m examples/tests/sleeptest.py.data/'
                    'sleeptest.yaml' % AVOCADO)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc)

    def test_mplex_plugin_nonexistent(self):
        cmd_line = '%s variants -m nonexist' % AVOCADO
        expected_rc = exit_codes.AVOCADO_FAIL
        result = self.run_and_check(cmd_line, expected_rc)
        self.assertIn('No such file or directory', result.stderr_text)

    @unittest.skipIf(sys.version_info[0] == 3,
                     "Test currently broken on Python 3")
    def test_mplex_debug(self):
        cmd_line = ('%s variants -c -d -m '
                    '/:optional_plugins/varianter_yaml_to_mux/tests/.data/mux-selftest.yaml '
                    '/:optional_plugins/varianter_yaml_to_mux/tests/.data/mux-environment.yaml '
                    '/:optional_plugins/varianter_yaml_to_mux/tests/.data/mux-selftest.yaml '
                    '/:optional_plugins/varianter_yaml_to_mux/tests/.data/mux-environment.yaml'
                    % AVOCADO)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        result = self.run_and_check(cmd_line, expected_rc)
        self.assertIn(DEBUG_OUT, result.stdout)

    def test_run_mplex_noid(self):
        cmd_line = ('%s run --job-results-dir %s --sysinfo=off '
                    '-m examples/tests/sleeptest.py.data/sleeptest.yaml'
                    % (AVOCADO, self.tmpdir))
        expected_rc = exit_codes.AVOCADO_JOB_FAIL
        self.run_and_check(cmd_line, expected_rc)

    def test_run_mplex_passtest(self):
        cmd_line = ('%s run --job-results-dir %s --sysinfo=off '
                    'passtest.py -m '
                    'examples/tests/sleeptest.py.data/sleeptest.yaml'
                    % (AVOCADO, self.tmpdir))
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc, (4, 0))
        # Also check whether jobdata contains correct parameter paths
        variants = open(os.path.join(self.tmpdir, "latest", "jobdata",
                        "variants.json")).read()
        self.assertIn('["/run/*"]', variants, "parameter paths stored in "
                      "jobdata does not contains [\"/run/*\"]\n%s" % variants)

    def test_run_mplex_doublepass(self):
        cmd_line = ('%s run --job-results-dir %s --sysinfo=off '
                    'passtest.py passtest.py -m '
                    'examples/tests/sleeptest.py.data/sleeptest.yaml '
                    '--mux-path /foo/\\* /bar/\\* /baz/\\*'
                    % (AVOCADO, self.tmpdir))
        self.run_and_check(cmd_line, exit_codes.AVOCADO_ALL_OK, (8, 0))
        # Also check whether jobdata contains correct parameter paths
        variants = open(os.path.join(self.tmpdir, "latest", "jobdata",
                        "variants.json")).read()
        exp = '["/foo/*", "/bar/*", "/baz/*"]'
        self.assertIn(exp, variants, "parameter paths stored in jobdata "
                      "does not contains %s\n%s" % (exp, variants))

    def test_run_mplex_failtest(self):
        cmd_line = ('%s run --job-results-dir %s --sysinfo=off '
                    'passtest.py failtest.py -m '
                    'examples/tests/sleeptest.py.data/sleeptest.yaml'
                    % (AVOCADO, self.tmpdir))
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        result = self.run_and_check(cmd_line, expected_rc, (4, 4))
        self.assertIn(b"(1/8) passtest.py:PassTest.test;short", result.stdout)
        self.assertIn(b"(2/8) passtest.py:PassTest.test;medium", result.stdout)
        self.assertIn(b"(8/8) failtest.py:FailTest.test;longest",
                      result.stdout)

    def test_run_mplex_failtest_tests_per_variant(self):
        cmd_line = ("%s run --job-results-dir %s --sysinfo=off "
                    "passtest.py failtest.py -m "
                    "examples/tests/sleeptest.py.data/sleeptest.yaml "
                    "--execution-order tests-per-variant"
                    % (AVOCADO, self.tmpdir))
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        result = self.run_and_check(cmd_line, expected_rc, (4, 4))
        self.assertIn(b"(1/8) passtest.py:PassTest.test;short", result.stdout)
        self.assertIn(b"(2/8) failtest.py:FailTest.test;short", result.stdout)
        self.assertIn(b"(8/8) failtest.py:FailTest.test;longest",
                      result.stdout)

    def test_run_double_mplex(self):
        cmd_line = ('%s run --job-results-dir %s --sysinfo=off '
                    'passtest.py -m '
                    'examples/tests/sleeptest.py.data/sleeptest.yaml '
                    'examples/tests/sleeptest.py.data/sleeptest.yaml'
                    % (AVOCADO, self.tmpdir))
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.run_and_check(cmd_line, expected_rc, (4, 0))

    def test_empty_file(self):
        cmd_line = ("%s run --job-results-dir %s -m optional_plugins/"
                    "varianter_yaml_to_mux/tests/.data/empty_file -- "
                    "passtest.py" % (AVOCADO, self.tmpdir))
        self.run_and_check(cmd_line, exit_codes.AVOCADO_ALL_OK, (1, 0))

    @unittest.skipIf(sys.version_info[0] == 3,
                     "Test currently broken on Python 3")
    def test_run_mplex_params(self):
        for variant_msg in (('/run/short', 'A'),
                            ('/run/medium', 'ASDFASDF'),
                            ('/run/long', 'This is very long\nmultiline\ntext.')):
            variant, msg = variant_msg
            cmd_line = ('%s run --job-results-dir %s --sysinfo=off '
                        'examples/tests/env_variables.sh '
                        '-m examples/tests/env_variables.sh.data/env_variables.yaml '
                        '--mux-filter-only %s --show-job-log'
                        % (AVOCADO, self.tmpdir, variant))
            expected_rc = exit_codes.AVOCADO_ALL_OK
            result = self.run_and_check(cmd_line, expected_rc)

            msg_lines = msg.splitlines()
            msg_header = '[stdout] Custom variable: %s' % msg_lines[0]
            self.assertIn(msg_header, result.stdout_text,
                          "Multiplexed variable should produce:"
                          "\n  %s\nwhich is not present in the output:\n  %s"
                          % (msg_header, "\n  ".join(result.stdout_text.splitlines())))
            for msg_remain in msg_lines[1:]:
                self.assertIn('[stdout] %s' % msg_remain, result.stdout_text,
                              "Multiplexed variable should produce:"
                              "\n  %s\nwhich is not present in the output:\n  %s"
                              % (msg_remain, "\n  ".join(result.stdout_text.splitlines())))

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
