"""Functional tests for the cpu module.

These tests validate the cpu module against the real system, reading from
/proc/cpuinfo, sysfs, and other system interfaces. They exercise the happy-path
behavior of the public API without requiring privileged access or specific
hardware.
"""

import os
import sys
import unittest

from avocado import skipIf
from avocado.utils import cpu
from selftests.utils import missing_binary, skipUnlessPathExists


@skipIf(
    sys.platform.startswith("darwin"),
    "Linux-only: /proc/cpuinfo and sysfs not available on macOS; "
    "os.sysconf(SC_NPROCESSORS_*) can hang on macOS with Python 3.11",
)
@skipUnlessPathExists("/proc/cpuinfo")
class CpuBasicTest(unittest.TestCase):
    """Functional tests for basic CPU information available on any Linux system."""

    def setUp(self):
        super().setUp()
        if sys.platform.startswith("darwin"):
            self.skipTest(
                "Linux-only: os.sysconf(SC_NPROCESSORS_*) can hang on macOS with Python 3.11"
            )

    def test_total_count_positive(self):
        """total_count returns a positive integer."""
        count = cpu.total_count()
        self.assertIsInstance(count, int)
        self.assertGreater(count, 0)

    def test_online_count_positive(self):
        """online_count returns a positive integer."""
        count = cpu.online_count()
        self.assertIsInstance(count, int)
        self.assertGreater(count, 0)

    def test_online_count_lte_total_count(self):
        """online_count is at most total_count."""
        self.assertLessEqual(cpu.online_count(), cpu.total_count())

    def test_online_list_length_matches_online_count(self):
        """online_list length equals online_count."""
        online = cpu.online_list()
        self.assertEqual(len(online), cpu.online_count())

    def test_online_list_contains_valid_indices(self):
        """online_list contains non-negative integers within total_count."""
        total = cpu.total_count()
        online = cpu.online_list()
        for idx in online:
            self.assertIsInstance(idx, int)
            self.assertGreaterEqual(idx, 0)
            self.assertLess(idx, total)

    def test_get_arch_returns_string(self):
        """get_arch returns a non-empty string."""
        arch = cpu.get_arch()
        self.assertIsInstance(arch, str)
        self.assertGreater(len(arch), 0)

    def test_get_vendor_returns_string_or_none(self):
        """get_vendor returns a known vendor string or None."""
        vendor = cpu.get_vendor()
        if vendor is not None:
            self.assertIn(vendor, ("intel", "amd", "ibm"))

    def test_get_version_returns_string(self):
        """get_version returns a string (may be empty on unsupported arch)."""
        version = cpu.get_version()
        self.assertIsInstance(version, str)


@skipUnlessPathExists("/proc/cpuinfo")
@unittest.skipUnless(
    os.path.exists("/sys/devices/system/node"),
    "NUMA not available on this system",
)
class CpuNumaTest(unittest.TestCase):
    """Functional tests for NUMA-related CPU functions."""

    def test_get_numa_node_has_cpus_returns_list(self):
        """get_numa_node_has_cpus returns a list of node identifiers."""
        nodes = cpu.get_numa_node_has_cpus()
        self.assertIsInstance(nodes, list)
        self.assertGreater(len(nodes), 0)

    def test_numa_nodes_with_assigned_cpus_returns_dict(self):
        """numa_nodes_with_assigned_cpus returns a dict with valid structure."""
        result = cpu.numa_nodes_with_assigned_cpus()
        self.assertIsInstance(result, dict)
        for node_id, cpus in result.items():
            self.assertIsInstance(node_id, int)
            self.assertIsInstance(cpus, list)
            self.assertTrue(all(isinstance(c, int) for c in cpus))


@skipUnlessPathExists("/proc/cpuinfo")
class CpuProcessTest(unittest.TestCase):
    """Functional tests for process-CPU affinity functions."""

    def test_get_pid_cpus_returns_list(self):
        """get_pid_cpus returns a list of CPU indices for current process."""
        pid = os.getpid()
        cpus = cpu.get_pid_cpus(pid)
        self.assertIsInstance(cpus, list)
        self.assertGreater(len(cpus), 0)
        online = set(cpu.online_list())
        for c in cpus:
            # get_pid_cpus returns strings; convert for comparison
            self.assertIn(int(c), online)


@skipUnlessPathExists("/proc/cpuinfo")
@unittest.skipIf(missing_binary("lscpu"), "lscpu command not available")
class CpuLscpuTest(unittest.TestCase):
    """Functional tests for lscpu integration."""

    def test_lscpu_returns_dict(self):
        """lscpu returns a dictionary with expected keys."""
        result = cpu.lscpu()
        self.assertIsInstance(result, dict)
        # At least one of these keys should be present depending on lscpu output
        known_keys = (
            "cores_per_chip",
            "virtual_cores",
            "physical_sockets",
            "physical_chips",
            "threads_per_core",
            "sockets",
            "chips",
            "physical_cores",
        )
        self.assertTrue(
            any(k in result for k in known_keys),
            f"lscpu returned no known keys: {result}",
        )


@skipUnlessPathExists("/proc/cpuinfo")
@unittest.skipUnless(
    cpu.get_arch() in ("x86_64", "i386"),
    "cpu_has_flags and get_va_bits are x86-specific",
)
class CpuX86Test(unittest.TestCase):
    """Functional tests for x86-specific CPU functions."""

    def test_cpu_has_flags_with_common_flag(self):
        """cpu_has_flags returns bool for common x86 flags."""
        # 'lm' (long mode) is present on all 64-bit x86
        result = cpu.cpu_has_flags("lm")
        self.assertIsInstance(result, bool)

    def test_get_va_bits_returns_string(self):
        """get_va_bits returns a string (may be empty)."""
        result = cpu.get_va_bits()
        self.assertIsInstance(result, str)
        if result:
            self.assertTrue(result.isdigit())
