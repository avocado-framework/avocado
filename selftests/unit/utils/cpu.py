import io
import unittest.mock

from avocado import Test
from avocado.utils import cpu


class Cpu(Test):
    @staticmethod
    def _get_file_mock(content):
        file_mock = unittest.mock.Mock()
        file_mock.__enter__ = unittest.mock.Mock(return_value=io.BytesIO(content))
        file_mock.__exit__ = unittest.mock.Mock()
        return file_mock

    def _get_data_mock(self, data_name):
        with open(self.get_data(data_name), "rb") as data_file:
            content = data_file.read()
        return self._get_file_mock(content)

    def test_s390x_cpu_online(self):
        with unittest.mock.patch(
            "avocado.utils.cpu.platform.machine", return_value="s390x"
        ):
            with unittest.mock.patch(
                "builtins.open", return_value=self._get_data_mock("s390x")
            ):
                self.assertEqual(len(cpu.online_list()), 2)
            with unittest.mock.patch(
                "builtins.open", return_value=self._get_data_mock("s390x_2")
            ):
                self.assertEqual(len(cpu.online_list()), 4)
            with unittest.mock.patch(
                "builtins.open", return_value=self._get_data_mock("s390x_3")
            ):
                self.assertEqual(len(cpu.online_list()), 6)
            with unittest.mock.patch(
                "builtins.open", return_value=self._get_data_mock("s390x_4")
            ):
                self.assertEqual(len(cpu.online_list()), 16)

    def test_x86_64_cpu_online(self):
        with unittest.mock.patch(
            "avocado.utils.cpu.platform.machine", return_value="x86_64"
        ):
            with unittest.mock.patch(
                "builtins.open", return_value=self._get_data_mock("x86_64")
            ):
                self.assertEqual(len(cpu.online_list()), 8)

    def test_cpu_arch_i386(self):
        with unittest.mock.patch(
            "builtins.open", return_value=self._get_data_mock("i386")
        ):
            self.assertEqual(cpu.get_arch(), "i386")

    def test_cpu_arch_x86_64(self):
        with unittest.mock.patch(
            "builtins.open", return_value=self._get_data_mock("x86_64")
        ):
            self.assertEqual(cpu.get_arch(), "x86_64")

    def test_cpu_has_flags(self):
        with unittest.mock.patch(
            "builtins.open", return_value=self._get_data_mock("x86_64")
        ):
            self.assertTrue(cpu.cpu_has_flags("flexpriority"))
            self.assertTrue(cpu.cpu_has_flags(["sse4_2", "xsaveopt"]))
            self.assertFalse(cpu.cpu_has_flags("THIS_WILL_NEVER_BE_A_FLAG_NAME"))
            self.assertFalse(
                cpu.cpu_has_flags(
                    ["THIS_WILL_NEVER_BE_A_FLAG_NAME", "NEITHER_WILL_THIS_WILL_EVER_BE"]
                )
            )

    def test_cpu_arch_power8(self):
        with unittest.mock.patch(
            "builtins.open", return_value=self._get_data_mock("power8")
        ):
            self.assertEqual(cpu.get_arch(), "powerpc")

    def test_cpu_arch_power9(self):
        with unittest.mock.patch(
            "builtins.open", return_value=self._get_data_mock("power9")
        ):
            self.assertEqual(cpu.get_arch(), "powerpc")

    def test_cpu_arch_s390(self):
        with unittest.mock.patch(
            "builtins.open", return_value=self._get_data_mock("s390x")
        ):
            self.assertEqual(cpu.get_arch(), "s390")

    def test_cpu_arch_arm_v7(self):
        with unittest.mock.patch(
            "builtins.open", return_value=self._get_data_mock("armv7")
        ):
            self.assertEqual(cpu.get_arch(), "arm")

    def test_cpu_arch_arm_v8(self):
        with unittest.mock.patch(
            "builtins.open", return_value=self._get_data_mock("armv8")
        ):
            self.assertEqual(cpu.get_arch(), "aarch64")

    def test_cpu_arch_risc_v(self):
        with unittest.mock.patch(
            "builtins.open", return_value=self._get_data_mock("risc_v")
        ):
            self.assertEqual(cpu.get_arch(), "riscv")

    def test_cpu_vendor_intel(self):
        with unittest.mock.patch(
            "builtins.open", return_value=self._get_data_mock("x86_64")
        ):
            self.assertEqual(cpu.get_vendor(), "intel")

    def test_cpu_vendor_power8(self):
        with unittest.mock.patch(
            "builtins.open", return_value=self._get_data_mock("power8")
        ):
            self.assertEqual(cpu.get_vendor(), "ibm")

    def test_cpu_vendor_power9(self):
        with unittest.mock.patch(
            "builtins.open", return_value=self._get_data_mock("power9")
        ):
            self.assertEqual(cpu.get_vendor(), "ibm")

    def test_get_vendor_none(self):
        """Test get_vendor returns None when cpuinfo matches no known vendor."""
        cpuinfo = b"processor : 0\ncpu : Unknown\n"
        with unittest.mock.patch(
            "builtins.open", return_value=self._get_file_mock(cpuinfo)
        ):
            self.assertIsNone(cpu.get_vendor())

    def test_s390x_get_version(self):
        with unittest.mock.patch(
            "avocado.utils.cpu.platform.machine", return_value="s390x"
        ):
            with unittest.mock.patch(
                "builtins.open", return_value=self._get_data_mock("s390x")
            ):
                self.assertEqual(cpu.get_version(), "2827")

    def test_intel_get_version(self):
        with unittest.mock.patch(
            "avocado.utils.cpu.platform.machine", return_value="x86_64"
        ):
            with unittest.mock.patch(
                "builtins.open", return_value=self._get_data_mock("x86_64")
            ):
                self.assertEqual(cpu.get_version(), "i7-4710MQ")

    def test_get_version_unsupported_arch(self):
        """Test get_version returns empty string when arch has no version pattern."""
        with unittest.mock.patch(
            "builtins.open", return_value=self._get_data_mock("risc_v")
        ):
            self.assertEqual(cpu.get_version(), "")

    def test_power8_get_version(self):
        with unittest.mock.patch(
            "avocado.utils.cpu.platform.machine", return_value="powerpc"
        ):
            with unittest.mock.patch(
                "builtins.open", return_value=self._get_data_mock("power8")
            ):
                self.assertEqual(cpu.get_version(), "2.1")

    def test_power9_get_version(self):
        with unittest.mock.patch(
            "avocado.utils.cpu.platform.machine", return_value="powerpc"
        ):
            with unittest.mock.patch(
                "builtins.open", return_value=self._get_data_mock("power9")
            ):
                self.assertEqual(cpu.get_version(), "1.0")

    def test_s390x_get_family(self):
        with unittest.mock.patch("avocado.utils.cpu.get_arch", return_value="s390"):
            with unittest.mock.patch(
                "avocado.utils.cpu.get_version", return_value="8561"
            ):
                self.assertEqual(cpu.get_family(), "z15")

    def test_intel_get_family(self):
        with unittest.mock.patch("avocado.utils.cpu.get_arch", return_value="x86_64"):
            with unittest.mock.patch(
                "avocado.utils.cpu.get_vendor", return_value="intel"
            ):
                with unittest.mock.patch(
                    "builtins.open", return_value=self._get_file_mock(b"broadwell")
                ):
                    self.assertEqual(cpu.get_family(), "broadwell")

    def test_get_family_intel_file_not_found(self):
        """Test get_family raises FamilyException when pmu_name missing (Intel)."""
        with unittest.mock.patch("avocado.utils.cpu.get_arch", return_value="x86_64"):
            with unittest.mock.patch(
                "avocado.utils.cpu.get_vendor", return_value="intel"
            ):
                with unittest.mock.patch(
                    "builtins.open", side_effect=FileNotFoundError("No such file")
                ):
                    with self.assertRaises(cpu.FamilyException):
                        cpu.get_family()

    def test_get_family_not_implemented(self):
        """Test get_family raises NotImplementedError for unsupported arch."""
        with unittest.mock.patch("avocado.utils.cpu.get_arch", return_value="aarch64"):
            with self.assertRaises(NotImplementedError):
                cpu.get_family()

    def test_power8_get_family(self):
        with unittest.mock.patch("avocado.utils.cpu.get_arch", return_value="powerpc"):
            with unittest.mock.patch(
                "builtins.open", return_value=self._get_data_mock("power8")
            ):
                self.assertEqual(cpu.get_family(), "power8")

    def test_power9_get_family(self):
        with unittest.mock.patch("avocado.utils.cpu.get_arch", return_value="powerpc"):
            with unittest.mock.patch(
                "builtins.open", return_value=self._get_data_mock("power9")
            ):
                self.assertEqual(cpu.get_family(), "power9")

    def test_get_idle_state_off(self):
        retval = {0: {0: False}}
        with unittest.mock.patch("avocado.utils.cpu.online_list", return_value=[0]):
            with unittest.mock.patch(
                "glob.glob",
                return_value=["/sys/devices/system/cpu/cpu0/cpuidle/state1"],
            ):
                mocked_open = unittest.mock.mock_open(read_data=b"0")
                with unittest.mock.patch("builtins.open", mocked_open):
                    self.assertEqual(cpu.get_idle_state(), retval)

    def test_get_idle_state_io_error(self):
        """Test get_idle_state handles IOError when reading state file."""
        with unittest.mock.patch("avocado.utils.cpu.online_list", return_value=[0]):
            with unittest.mock.patch(
                "glob.glob",
                return_value=["/sys/devices/system/cpu/cpu0/cpuidle/state1"],
            ):
                with unittest.mock.patch(
                    "builtins.open", side_effect=IOError("Permission denied")
                ):
                    result = cpu.get_idle_state()
                    self.assertEqual(result, {0: {}})

    def test_get_idle_state_on(self):
        retval = {0: {0: True}}
        with unittest.mock.patch("avocado.utils.cpu.online_list", return_value=[0]):
            with unittest.mock.patch(
                "glob.glob",
                return_value=["/sys/devices/system/cpu/cpu0/cpuidle/state1"],
            ):
                mocked_open = unittest.mock.mock_open(read_data=b"1")
                with unittest.mock.patch("builtins.open", mocked_open):
                    self.assertEqual(cpu.get_idle_state(), retval)

    def test_set_idle_state_default(self):
        with unittest.mock.patch("avocado.utils.cpu.online_list", return_value=[0]):
            with unittest.mock.patch(
                "glob.glob",
                return_value=["/sys/devices/system/cpu/cpu0/cpuidle/state1"],
            ):
                mocked_open = unittest.mock.mock_open()
                with unittest.mock.patch("builtins.open", mocked_open):
                    cpu.set_idle_state()
                mocked_open.assert_called_with(
                    "/sys/devices/system/cpu/cpu0/cpuidle/state0/disable", "wb"
                )
                mocked_fo = mocked_open()
                mocked_fo.write.assert_called_once_with(b"1")

    def test_set_idle_state_withstateno(self):
        with unittest.mock.patch("avocado.utils.cpu.online_list", return_value=[0]):
            with unittest.mock.patch(
                "glob.glob",
                return_value=["/sys/devices/system/cpu/cpu0/cpuidle/state2"],
            ):
                mocked_open = unittest.mock.mock_open()
                with unittest.mock.patch("builtins.open", mocked_open):
                    cpu.set_idle_state(disable=False, state_number="2")
                mocked_open.assert_called_with(
                    "/sys/devices/system/cpu/cpu0/cpuidle/state2/disable", "wb"
                )
                mocked_fo = mocked_open()
                mocked_fo.write.assert_called_once_with(b"0")

    def test_set_idle_state_withsetstate(self):
        with unittest.mock.patch("avocado.utils.cpu.online_list", return_value=[0, 2]):
            with unittest.mock.patch(
                "glob.glob",
                return_value=["/sys/devices/system/cpu/cpu0/cpuidle/state1"],
            ):
                mocked_open = unittest.mock.mock_open()
                with unittest.mock.patch("builtins.open", mocked_open):
                    cpu.set_idle_state(setstate={0: {0: True}, 2: {0: False}})
                mocked_open.assert_called_with(
                    "/sys/devices/system/cpu/cpu2/cpuidle/state0/disable", "wb"
                )
                mocked_fo = mocked_open()
                mocked_fo.write.assert_called_with(b"0")

    def test_set_idle_state_disable(self):
        function = "avocado.utils.cpu.online_list"
        state_file = "/sys/devices/system/cpu/cpu0/cpuidle/state1"
        with unittest.mock.patch(function, return_value=[0, 2]):
            with unittest.mock.patch("glob.glob", return_value=[state_file]):
                mocked_open = unittest.mock.mock_open()
                with unittest.mock.patch("builtins.open", mocked_open):
                    with self.assertRaises(TypeError):
                        cpu.set_idle_state(disable=1)

    def test_set_idle_state_io_error(self):
        """Test set_idle_state handles IOError when writing state file."""
        with unittest.mock.patch("avocado.utils.cpu.online_list", return_value=[0]):
            with unittest.mock.patch(
                "glob.glob",
                return_value=["/sys/devices/system/cpu/cpu0/cpuidle/state1"],
            ):
                with unittest.mock.patch(
                    "builtins.open", side_effect=IOError("Permission denied")
                ):
                    cpu.set_idle_state()

    def test_get_revision(self):
        """Test get_revision parses revision from cpuinfo."""
        cpuinfo = "processor : 0\nrevision  : 0080\n"
        with unittest.mock.patch(
            "avocado.utils.cpu.genio.read_file", return_value=cpuinfo
        ):
            self.assertEqual(cpu.get_revision(), "0080")

    def test_get_revision_no_revision(self):
        """Test get_revision returns None when no revision line."""
        with unittest.mock.patch(
            "avocado.utils.cpu.genio.read_file", return_value="processor : 0\n"
        ):
            self.assertIsNone(cpu.get_revision())

    def test_get_va_bits(self):
        """Test get_va_bits extracts VA bits from address sizes line."""
        cpuinfo = "address sizes : 39 bits physical, 48 bits virtual\n"
        with unittest.mock.patch(
            "avocado.utils.cpu.genio.read_file", return_value=cpuinfo
        ):
            self.assertEqual(cpu.get_va_bits(), "48")

    def test_get_va_bits_empty(self):
        """Test get_va_bits returns empty string when no address sizes."""
        with unittest.mock.patch(
            "avocado.utils.cpu.genio.read_file", return_value="processor : 0\n"
        ):
            self.assertEqual(cpu.get_va_bits(), "")

    def test_get_model_x86_64(self):
        """Test get_model extracts model for x86_64."""
        with unittest.mock.patch("avocado.utils.cpu.get_arch", return_value="x86_64"):
            with unittest.mock.patch(
                "builtins.open", return_value=self._get_data_mock("x86_64")
            ):
                result = cpu.get_model()
                self.assertIsInstance(result, int)
                self.assertGreaterEqual(result, 0)

    def test_get_model_not_implemented(self):
        """Test get_model raises NotImplementedError for non-x86_64."""
        with unittest.mock.patch("avocado.utils.cpu.get_arch", return_value="powerpc"):
            with self.assertRaises(NotImplementedError):
                cpu.get_model()

    def test_get_model_no_model_line(self):
        """Test get_model returns None when cpuinfo has no model line."""
        cpuinfo = b"processor : 0\nvendor_id : GenuineIntel\n"
        with unittest.mock.patch("avocado.utils.cpu.get_arch", return_value="x86_64"):
            with unittest.mock.patch(
                "builtins.open", return_value=self._get_file_mock(cpuinfo)
            ):
                self.assertIsNone(cpu.get_model())

    def test_get_x86_amd_zen_with_params(self):
        """Test get_x86_amd_zen with explicit family/model."""
        self.assertEqual(cpu.get_x86_amd_zen(family=23, model=0), 1)
        self.assertEqual(cpu.get_x86_amd_zen(family=23, model=0x30), 2)
        self.assertEqual(cpu.get_x86_amd_zen(family=25, model=0), 3)
        self.assertIsNone(cpu.get_x86_amd_zen(family=0x99, model=0))

    def test_get_x86_amd_zen_family_match_model_no_match(self):
        """Test get_x86_amd_zen returns None when family matches but model outside ranges."""
        # Family 0x17 (Zen) but model 0x80 is in gap between Zen 1/2 ranges
        self.assertIsNone(cpu.get_x86_amd_zen(family=23, model=0x80))

    def test_total_count(self):
        """Test total_count returns sysconf value."""
        with unittest.mock.patch("os.sysconf", return_value=8):
            self.assertEqual(cpu.total_count(), 8)

    def test_deprecated_alias(self):
        """Test deprecated total_cpus_count alias calls total_count."""
        with unittest.mock.patch("os.sysconf", return_value=8):
            with self.assertWarns(DeprecationWarning):
                self.assertEqual(cpu.total_cpus_count(), 8)

    def test_online_count(self):
        """Test online_count returns sysconf value."""
        with unittest.mock.patch("os.sysconf", return_value=8):
            self.assertEqual(cpu.online_count(), 8)

    def test_is_hotpluggable_true(self):
        """Test is_hotpluggable when cpu online file exists."""
        with unittest.mock.patch("os.path.exists", return_value=True):
            self.assertTrue(cpu.is_hotpluggable(1))

    def test_is_hotpluggable_false(self):
        """Test is_hotpluggable when cpu online file does not exist."""
        with unittest.mock.patch("os.path.exists", return_value=False):
            self.assertFalse(cpu.is_hotpluggable(0))

    def test_online_already_online(self):
        """Test online returns 1 when CPU is already online."""
        with unittest.mock.patch("avocado.utils.cpu._get_status", return_value=True):
            self.assertEqual(cpu.online(1), 1)

    def test_online_cpu_failure(self):
        """Test online returns 0 when write to sysfs does not persist."""
        with unittest.mock.patch(
            "avocado.utils.cpu._get_status", side_effect=[False, False]
        ):
            with unittest.mock.patch("builtins.open", unittest.mock.mock_open()):
                self.assertEqual(cpu.online(1), 0)

    def test_offline_already_offline(self):
        """Test offline returns 0 when CPU is already offline."""
        with unittest.mock.patch("avocado.utils.cpu._get_status", return_value=False):
            self.assertEqual(cpu.offline(1), 0)

    def test_offline_cpu_failure(self):
        """Test offline returns 1 when write to sysfs does not persist."""
        with unittest.mock.patch(
            "avocado.utils.cpu._get_status", side_effect=[True, True]
        ):
            with unittest.mock.patch("builtins.open", unittest.mock.mock_open()):
                self.assertEqual(cpu.offline(1), 1)

    def test_get_freq_governor(self):
        """Test get_freq_governor reads scaling_governor."""
        with unittest.mock.patch(
            "builtins.open",
            unittest.mock.mock_open(read_data="performance"),
        ):
            self.assertEqual(cpu.get_freq_governor(), "performance")

    def test_get_freq_governor_io_error(self):
        """Test get_freq_governor returns empty on IOError."""
        with unittest.mock.patch("builtins.open", side_effect=IOError("No such file")):
            self.assertEqual(cpu.get_freq_governor(), "")

    def test_set_freq_governor_no_current(self):
        """Test set_freq_governor returns False when get_freq_governor is empty."""
        with unittest.mock.patch(
            "avocado.utils.cpu.get_freq_governor", return_value=""
        ):
            self.assertFalse(cpu.set_freq_governor("performance"))

    def test_get_numa_node_has_cpus(self):
        """Test get_numa_node_has_cpus parses has_cpu file."""
        with unittest.mock.patch(
            "avocado.utils.cpu.genio.read_file", return_value="0-3\n"
        ):
            self.assertEqual(cpu.get_numa_node_has_cpus(), ["0", "3"])

    def test_lscpu(self):
        """Test lscpu parses output."""
        output = unittest.mock.Mock()
        output.stdout = (
            b"Core(s) per socket: 4\n"
            b"Thread(s) per core: 2\n"
            b"Socket(s): 2\n"
            b"Physical cores/chip: 4\n"
            b"Physical sockets: 2\n"
            b"Physical chips: 2\n"
        )
        with unittest.mock.patch("avocado.utils.cpu.process.run", return_value=output):
            result = cpu.lscpu()
            self.assertEqual(result["virtual_cores"], 4)
            self.assertEqual(result["threads_per_core"], 2)
            self.assertEqual(result["sockets"], 2)
            self.assertEqual(result["chips"], 4)


if __name__ == "__main__":
    unittest.main()
