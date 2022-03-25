import os
import unittest

from avocado.core import exit_codes
from avocado.utils import process, script
from selftests.utils import AVOCADO, TestCaseTmpDir, skipOnLevelsInferiorThan

COMMANDS_TIMEOUT_CONF = """
[sysinfo.collect]
commands_timeout = %s

[sysinfo.collectibles]
commands = %s
"""


class SysInfoTest(TestCaseTmpDir):

    def test_sysinfo_enabled(self):
        cmd_line = (f'{AVOCADO} run --job-results-dir {self.tmpdir.name} '
                    f'examples/tests/passtest.py')
        result = process.run(cmd_line)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")
        output = result.stdout_text + result.stderr_text
        sysinfo_dir = None
        for line in output.splitlines():
            if 'JOB LOG' in line:
                job_log = line.split()[-1]
                sysinfo_dir = os.path.join(os.path.dirname(job_log), 'sysinfo')
        self.assertIsNotNone(sysinfo_dir,
                             ('Could not find sysinfo dir from human output. '
                              'Output produced: "%s" % output'))
        msg = (f"Avocado didn't create sysinfo directory {sysinfo_dir}:"
               f"\n{result}")
        self.assertTrue(os.path.isdir(sysinfo_dir), msg)
        msg = f'The sysinfo directory is empty:\n{result}'
        self.assertGreater(len(os.listdir(sysinfo_dir)), 0, msg)
        for hook in ('pre', 'post'):
            sysinfo_subdir = os.path.join(sysinfo_dir, hook)
            msg = f'The sysinfo/{hook} subdirectory does not exist:\n{result}'
            self.assertTrue(os.path.exists(sysinfo_subdir), msg)

    def test_sysinfo_disabled(self):
        cmd_line = (f'{AVOCADO} run --job-results-dir {self.tmpdir.name} '
                    f'--disable-sysinfo examples/tests/passtest.py')
        result = process.run(cmd_line)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")
        output = result.stdout_text + result.stderr_text
        sysinfo_dir = None
        for line in output.splitlines():
            if 'JOB LOG' in line:
                job_log = line.split()[-1]
                sysinfo_dir = os.path.join(os.path.dirname(job_log), 'sysinfo')
        self.assertIsNotNone(sysinfo_dir,
                             ('Could not find sysinfo dir from human output. '
                              'Output produced: "%s" % output'))
        msg = f'Avocado created sysinfo directory {sysinfo_dir}:\n{result}'
        self.assertFalse(os.path.isdir(sysinfo_dir), msg)

    def run_sysinfo_interrupted(self, sleep, timeout, exp_duration):
        commands_path = os.path.join(self.tmpdir.name, "commands")
        script.make_script(commands_path, f"sleep {sleep}")
        config_path = os.path.join(self.tmpdir.name, "config.conf")
        script.make_script(config_path,
                           COMMANDS_TIMEOUT_CONF % (timeout, commands_path))
        cmd_line = (f"{AVOCADO} --show all --config {config_path} run "
                    f"--job-results-dir {self.tmpdir.name} "
                    f"examples/tests/passtest.py")
        result = process.run(cmd_line)
        if timeout > 0:
            self.assertLess(result.duration, exp_duration,
                            (f"Execution took "
                             f"longer than {exp_duration}s which is likely "
                             f"due to malfunctioning commands_timeout "
                             f"sysinfo.collect feature:\n{result}"))
        else:
            self.assertGreater(result.duration, exp_duration,
                               (f"Execution took "
                                f"less than {exp_duration}s which is likely "
                                f"due to malfunctioning commands_timeout "
                                f"sysinfo.collect feature:\n{result}"))
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         f"Avocado did not return rc {expected_rc}:\n{result}")
        sleep_log = os.path.join(self.tmpdir.name, "latest", "sysinfo", "pre",
                                 f"sleep {sleep}")
        if not os.path.exists(sleep_log):
            path = os.path.abspath(sleep_log)
            while not os.path.exists(path):
                tmp = os.path.split(path)[0]
                if tmp == path:
                    break
                path = tmp
            raise AssertionError(f"Sleep output not recorded in '{sleep_log}',"
                                 f"first existing location '{path}' contains:"
                                 f"\n{os.listdir(path)}")

    @skipOnLevelsInferiorThan(2)
    def test_sysinfo_interrupted(self):
        """
        :avocado: tags=parallel:1
        """
        self.run_sysinfo_interrupted(10, 1, 15)

    @skipOnLevelsInferiorThan(2)
    def test_sysinfo_not_interrupted(self):
        """
        :avocado: tags=parallel:1
        """
        self.run_sysinfo_interrupted(5, -1, 10)


if __name__ == '__main__':
    unittest.main()
