import os
import tempfile
import unittest

from avocado.core import exit_codes
from avocado.utils import process
from avocado.utils import script

from .. import AVOCADO, BASEDIR, temp_dir_prefix, skipOnLevelsInferiorThan


COMMANDS_TIMEOUT_CONF = """
[sysinfo.collect]
commands_timeout = %s

[sysinfo.collectibles]
commands = %s
"""


class SysInfoTest(unittest.TestCase):

    def setUp(self):
        prefix = temp_dir_prefix(__name__, self, 'setUp')
        self.tmpdir = tempfile.TemporaryDirectory(prefix=prefix)

    def test_sysinfo_enabled(self):
        os.chdir(BASEDIR)
        cmd_line = ('%s run --job-results-dir %s --sysinfo=on '
                    'passtest.py' % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd_line)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         'Avocado did not return rc %d:\n%s' % (expected_rc,
                                                                result))
        output = result.stdout_text + result.stderr_text
        sysinfo_dir = None
        for line in output.splitlines():
            if 'JOB LOG' in line:
                job_log = line.split()[-1]
                sysinfo_dir = os.path.join(os.path.dirname(job_log), 'sysinfo')
        self.assertIsNotNone(sysinfo_dir,
                             ('Could not find sysinfo dir from human output. '
                              'Output produced: "%s" % output'))
        msg = "Avocado didn't create sysinfo directory %s:\n%s" % (sysinfo_dir,
                                                                   result)
        self.assertTrue(os.path.isdir(sysinfo_dir), msg)
        msg = 'The sysinfo directory is empty:\n%s' % result
        self.assertGreater(len(os.listdir(sysinfo_dir)), 0, msg)
        for hook in ('pre', 'post'):
            sysinfo_subdir = os.path.join(sysinfo_dir, hook)
            msg = 'The sysinfo/%s subdirectory does not exist:\n%s' % (hook,
                                                                       result)
            self.assertTrue(os.path.exists(sysinfo_subdir), msg)

    def test_sysinfo_disabled(self):
        os.chdir(BASEDIR)
        cmd_line = ('%s run --job-results-dir %s --sysinfo=off passtest.py'
                    % (AVOCADO, self.tmpdir.name))
        result = process.run(cmd_line)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         'Avocado did not return rc %d:\n%s' % (expected_rc,
                                                                result))
        output = result.stdout_text + result.stderr_text
        sysinfo_dir = None
        for line in output.splitlines():
            if 'JOB LOG' in line:
                job_log = line.split()[-1]
                sysinfo_dir = os.path.join(os.path.dirname(job_log), 'sysinfo')
        self.assertIsNotNone(sysinfo_dir,
                             ('Could not find sysinfo dir from human output. '
                              'Output produced: "%s" % output'))
        msg = 'Avocado created sysinfo directory %s:\n%s' % (sysinfo_dir,
                                                             result)
        self.assertFalse(os.path.isdir(sysinfo_dir), msg)

    def test_sysinfo_html_output(self):
        os.chdir(BASEDIR)
        html_output = "{}/output.html".format(self.tmpdir.name)
        cmd_line = ('{} run --html {} --job-results-dir {} --sysinfo=on '
                    'passtest.py'.format(AVOCADO, html_output,
                                         self.tmpdir.name))
        result = process.run(cmd_line)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         'Avocado did not return rc %d:\n%s' % (expected_rc,
                                                                result))
        with open(html_output, 'rt') as fp:
            output = fp.read()

        # Try to find some strings on HTML
        self.assertNotEqual(output.find('Filesystem'), -1)
        self.assertNotEqual(output.find('root='), -1)
        self.assertNotEqual(output.find('MemAvailable'), -1)

    def tearDown(self):
        self.tmpdir.cleanup()

    def run_sysinfo_interrupted(self, sleep, timeout, exp_duration):
        os.chdir(BASEDIR)
        commands_path = os.path.join(self.tmpdir.name, "commands")
        script.make_script(commands_path, "sleep %s" % sleep)
        config_path = os.path.join(self.tmpdir.name, "config.conf")
        script.make_script(config_path,
                           COMMANDS_TIMEOUT_CONF % (timeout, commands_path))
        cmd_line = ("%s --show all --config %s run --job-results-dir %s "
                    "--sysinfo=on passtest.py"
                    % (AVOCADO, config_path, self.tmpdir.name))
        result = process.run(cmd_line)
        if timeout > 0:
            self.assertLess(result.duration, exp_duration, "Execution took "
                            "longer than %ss which is likely due to "
                            "malfunctioning commands_timeout "
                            "sysinfo.collect feature:\n%s"
                            % (exp_duration, result))
        else:
            self.assertGreater(result.duration, exp_duration, "Execution took "
                               "less than %ss which is likely due to "
                               "malfunctioning commands_timeout "
                               "sysinfo.collect feature:\n%s"
                               % (exp_duration, result))
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         'Avocado did not return rc %d:\n%s'
                         % (expected_rc, result))
        sleep_log = os.path.join(self.tmpdir.name, "latest", "sysinfo", "pre",
                                 "sleep %s" % sleep)
        if not os.path.exists(sleep_log):
            path = os.path.abspath(sleep_log)
            while not os.path.exists(path):
                tmp = os.path.split(path)[0]
                if tmp == path:
                    break
                path = tmp
            raise AssertionError("Sleep output not recorded in '%s', first "
                                 "existing location '%s' contains:\n%s"
                                 % (sleep_log, path, os.listdir(path)))

    @skipOnLevelsInferiorThan(2)
    def test_sysinfo_interrupted(self):
        self.run_sysinfo_interrupted(10, 1, 15)

    @skipOnLevelsInferiorThan(2)
    def test_sysinfo_not_interrupted(self):
        self.run_sysinfo_interrupted(5, -1, 10)


if __name__ == '__main__':
    unittest.main()
