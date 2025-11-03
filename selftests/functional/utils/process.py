import os
import stat
import sys
import time

from avocado.utils import process
from selftests.utils import TestCaseTmpDir, skipOnLevelsInferiorThan

# What is commonly known as "0775" or "u=rwx,g=rwx,o=rx"
DEFAULT_MODE = (
    stat.S_IRUSR
    | stat.S_IWUSR
    | stat.S_IXUSR
    | stat.S_IRGRP
    | stat.S_IWGRP
    | stat.S_IXGRP
    | stat.S_IROTH
    | stat.S_IXOTH
)

FAKE_VMSTAT_CONTENTS = f"""#!{sys.executable}
import time
import random
import signal
import sys

class FakeVMStat:
    def __init__(self, interval, interrupt_delay=0):
        self.interval = interval
        self._sysrand = random.SystemRandom()
        def interrupt_handler(signum, frame):
            time.sleep(interrupt_delay)
            sys.exit(0)
        signal.signal(signal.SIGINT, interrupt_handler)
        signal.signal(signal.SIGTERM, interrupt_handler)

    def get_r(self):
        return self._sysrand.randint(0, 2)

    def get_b(self):
        return 0

    def get_swpd(self):
        return 0

    def get_free(self):
        return self._sysrand.randint(1500000, 1600000)

    def get_buff(self):
        return self._sysrand.randint(290000, 300000)

    def get_cache(self):
        return self._sysrand.randint(2900000, 3000000)

    def get_si(self):
        return 0

    def get_so(self):
        return 0

    def get_bi(self):
        return self._sysrand.randint(0, 50)

    def get_bo(self):
        return self._sysrand.randint(0, 500)

    def get_in(self):
        return self._sysrand.randint(200, 3000)

    def get_cs(self):
        return self._sysrand.randint(1000, 4000)

    def get_us(self):
        return self._sysrand.randint(0, 40)

    def get_sy(self):
        return self._sysrand.randint(1, 5)

    def get_id(self):
        return self._sysrand.randint(50, 100)

    def get_wa(self):
        return 0

    def get_st(self):
        return 0

    def start(self):
        print("procs -----------memory---------- ---swap-- -----io---- -system-- ------cpu-----")
        print(" r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st")
        while True:
            r = self.get_r()
            b = self.get_b()
            swpd = self.get_swpd()
            free = self.get_free()
            buff = self.get_buff()
            cache = self.get_cache()
            si = self.get_si()
            so = self.get_so()
            bi = self.get_bi()
            bo = self.get_bo()
            m_in = self.get_in()
            cs = self.get_cs()
            us = self.get_us()
            sy = self.get_sy()
            m_id = self.get_id()
            wa = self.get_wa()
            st = self.get_st()
            print("%2d %2d  %2d   %7d %6d %7d    %1d    %1d    %2d  %3d %4d %2d %2d %1d  %3d  %1d  %1d" %
                  (r, b, swpd, free, buff, cache, si, so, bi, bo, m_in, cs,
                   us, sy, m_id, wa, st))
            time.sleep(self.interval)

if __name__ == '__main__':
    vmstat = FakeVMStat(interval=float(sys.argv[1]), interrupt_delay=float(sys.argv[2]))
    vmstat.start()
"""

FAKE_UPTIME_CONTENTS = f"""#!{sys.executable}
if __name__ == '__main__':
    print("17:56:34 up  8:06,  7 users,  load average: 0.26, 0.20, 0.21")

"""

ENV_TEST_SCRIPT = """#!{interpreter}
import os
print(os.environ.get('TEST_VAR', 'NOT_SET'))
"""

SUCCESS_SCRIPT = """#!{interpreter}
print('success')
"""

LARGE_OUTPUT_SCRIPT = """#!{interpreter}
for i in range(1000):
    print(f'Line {{i}}' * 100)
"""

UNICODE_TEST_SCRIPT = """#!{interpreter}
# -*- coding: utf-8 -*-
print('Avokádo')
"""


class ProcessTest(TestCaseTmpDir):
    def setUp(self):
        super().setUp()
        self.fake_vmstat = os.path.join(self.tmpdir.name, "vmstat")
        with open(self.fake_vmstat, "w", encoding="utf-8") as fake_vmstat_obj:
            fake_vmstat_obj.write(FAKE_VMSTAT_CONTENTS)
        os.chmod(self.fake_vmstat, DEFAULT_MODE)

        self.fake_uptime = os.path.join(self.tmpdir.name, "uptime")
        with open(self.fake_uptime, "w", encoding="utf-8") as fake_uptime_obj:
            fake_uptime_obj.write(FAKE_UPTIME_CONTENTS)
        os.chmod(self.fake_uptime, DEFAULT_MODE)

    def _create_script(self, name, contents):
        """Create a script file from a template with the interpreter substituted.

        :param name: Name for the script file
        :param contents: Script contents template with {interpreter} placeholder
        :returns: Path to the created script
        """
        script_path = os.path.join(self.tmpdir.name, name)
        with open(script_path, "w", encoding="utf-8") as script_file:
            script_file.write(contents.format(interpreter=sys.executable))
        os.chmod(script_path, DEFAULT_MODE)
        return script_path

    @skipOnLevelsInferiorThan(2)
    def test_process_start(self):
        """
        :avocado: tags=parallel:1
        """
        proc = process.SubProcess(f"{self.fake_vmstat} 1 0")
        proc.start()
        time.sleep(3)
        proc.terminate()
        proc.wait(timeout=1)
        stdout = proc.get_stdout().decode()
        self.assertIn("memory", stdout, f"result: {stdout}")
        self.assertRegex(stdout, "[0-9]+")

    @skipOnLevelsInferiorThan(2)
    def test_process_stop_interrupted(self):
        """
        :avocado: tags=parallel:1
        """
        proc = process.SubProcess(f"{self.fake_vmstat} 1 3")
        proc.start()
        time.sleep(3)
        proc.stop(2)
        result = proc.result
        self.assertIn("timeout after", result.interrupted, "Process wasn't interrupted")

    @skipOnLevelsInferiorThan(2)
    def test_process_stop_uninterrupted(self):
        """
        :avocado: tags=parallel:1
        """
        proc = process.SubProcess(f"{self.fake_vmstat} 1 3")
        proc.start()
        time.sleep(3)
        proc.stop(4)
        result = proc.result
        self.assertFalse(result.interrupted, "Process was interrupted to early")

    def test_process_run(self):
        proc = process.SubProcess(self.fake_uptime)
        result = proc.run()
        self.assertEqual(result.exit_status, 0, f"result: {result}")
        self.assertIn(b"load average", result.stdout)

    def test_run_and_system_output_with_environment(self):
        """Test process.run() and process.system_output() with environment variables"""
        env_script = self._create_script("env_test.py", ENV_TEST_SCRIPT)

        # Test process.run() with custom environment variable
        result = process.run(env_script, env={"TEST_VAR": "custom_value"})
        self.assertEqual(result.stdout.strip(), b"custom_value")
        self.assertEqual(result.exit_status, 0)

        # Test process.system_output() also respects environment
        output = process.system_output(
            env_script, env={"TEST_VAR": "from_system_output"}
        )
        self.assertEqual(output.strip(), b"from_system_output")

    def test_getstatusoutput_integration(self):
        """Test getstatusoutput function with real commands"""
        success_script = self._create_script("success.py", SUCCESS_SCRIPT)

        status, output = process.getstatusoutput(success_script)
        self.assertEqual(status, 0)
        self.assertEqual(output, "success")

    def test_multiple_subprocess_instances(self):
        """Test running multiple subprocess instances concurrently"""
        procs = []
        for i in range(3):
            proc = process.SubProcess(
                f"{sys.executable} -c 'import time; time.sleep(1); print({i})'"
            )
            proc.start()
            procs.append(proc)

        # Wait for all processes to complete
        for i, proc in enumerate(procs):
            proc.wait()
            self.assertEqual(proc.result.exit_status, 0)
            self.assertIn(str(i).encode(), proc.result.stdout)

    @skipOnLevelsInferiorThan(2)
    def test_process_with_large_output(self):
        """Test process captures complete large stdout output"""
        large_output_script = self._create_script(
            "large_output.py", LARGE_OUTPUT_SCRIPT
        )

        result = process.run(large_output_script)
        self.assertEqual(result.exit_status, 0)

        # Verify we captured EXACTLY the expected output
        lines = result.stdout.decode().strip().split("\n")
        self.assertEqual(len(lines), 1000, "Should capture exactly 1000 lines")

        # Verify format of first and last lines to ensure no corruption
        self.assertEqual(lines[0], "Line 0" * 100)
        self.assertEqual(lines[999], "Line 999" * 100)

    def test_cmdresult_encoding(self):
        """Test CmdResult with different character encoding"""
        unicode_script = self._create_script("unicode_test.py", UNICODE_TEST_SCRIPT)

        result = process.run(unicode_script, encoding="utf-8")
        self.assertEqual(result.encoding, "utf-8")
        self.assertIn("Avokádo", result.stdout_text)

    def test_binary_from_shell_cmd_realworld(self):
        """Test binary_from_shell_cmd with real-world command patterns"""
        # Simulating common command patterns
        cmd1 = "FOO=bar BAR=baz /usr/bin/python script.py --arg value"
        self.assertEqual(process.binary_from_shell_cmd(cmd1), "/usr/bin/python")

        cmd2 = "sudo -u user /bin/bash -c 'echo test'"
        self.assertEqual(process.binary_from_shell_cmd(cmd2), "sudo")
