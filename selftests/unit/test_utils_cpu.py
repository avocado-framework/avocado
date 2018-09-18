import io
import unittest

try:
    from unittest import mock
except ImportError:
    import mock

from .. import recent_mock
from avocado.utils import cpu


class Cpu(unittest.TestCase):

    @staticmethod
    def _get_file_mock(content):
        file_mock = mock.Mock()
        file_mock.__enter__ = mock.Mock(return_value=io.BytesIO(content))
        file_mock.__exit__ = mock.Mock()
        return file_mock

    @unittest.skipUnless(recent_mock(),
                         "mock library version cannot (easily) patch open()")
    def test_s390x_cpu_online(self):
        s390x = b"""vendor_id       : IBM/S390
# processors    : 2
bogomips per cpu: 2913.00
max thread id   : 0
features        : esan3 zarch stfle msa ldisp eimm dfp edat etf3eh highgprs te sie
facilities      : 0 1 2 3 4 6 7 8 9 10 12 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 30 31 32 33 34 35 36 37 40 41 42 43 44 45 46 47 48 49 50 51 52 57 73 74 75 76 77
cache0          : level=1 type=Data scope=Private size=96K line_size=256 associativity=6
cache1          : level=1 type=Instruction scope=Private size=64K line_size=256 associativity=4
cache2          : level=2 type=Data scope=Private size=1024K line_size=256 associativity=8
cache3          : level=2 type=Instruction scope=Private size=1024K line_size=256 associativity=8
cache4          : level=3 type=Unified scope=Shared size=49152K line_size=256 associativity=12
cache5          : level=4 type=Unified scope=Shared size=393216K line_size=256 associativity=24
processor 0: version = FF,  identification = 32C047,  machine = 2827
processor 1: version = FF,  identification = 32C047,  machine = 2827

cpu number      : 0
cpu MHz dynamic : 5504
cpu MHz static  : 5504

cpu number      : 1
cpu MHz dynamic : 5504
cpu MHz static  : 5504

"""

        s390x_2 = b"""vendor_id       : IBM/S390
# processors    : 4
bogomips per cpu: 2913.00
max thread id   : 0
features        : esan3 zarch stfle msa ldisp eimm dfp edat etf3eh highgprs te sie
facilities      : 0 1 2 3 4 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 30 31 32 33 34 35 36 37 40 41 42 43 44 45 46 47 48 49 50 51 52 57 64 65 66 67 68 69 70 71 72 73 75 76 77 78 131 132
cache0          : level=1 type=Data scope=Private size=96K line_size=256 associativity=6
cache1          : level=1 type=Instruction scope=Private size=64K line_size=256 associativity=4
cache2          : level=2 type=Data scope=Private size=1024K line_size=256 associativity=8
cache3          : level=2 type=Instruction scope=Private size=1024K line_size=256 associativity=8
cache4          : level=3 type=Unified scope=Shared size=49152K line_size=256 associativity=12
cache5          : level=4 type=Unified scope=Shared size=393216K line_size=256 associativity=24
processor 0: version = 00,  identification = 3FC047,  machine = 2827
processor 1: version = 00,  identification = 3FC047,  machine = 2827
processor 2: version = 00,  identification = 3FC047,  machine = 2827
processor 3: version = 00,  identification = 3FC047,  machine = 2827

cpu number      : 0
cpu MHz dynamic : 5504
cpu MHz static  : 5504

cpu number      : 1
cpu MHz dynamic : 5504
cpu MHz static  : 5504

cpu number      : 2
cpu MHz dynamic : 5504
cpu MHz static  : 5504

cpu number      : 3
cpu MHz dynamic : 5504
cpu MHz static  : 5504
"""

        with mock.patch('avocado.utils.cpu.platform.machine', return_value='s390x'):
            with mock.patch('avocado.utils.cpu.open',
                            return_value=self._get_file_mock(s390x)):
                self.assertEqual(len(cpu.cpu_online_list()), 2)
            with mock.patch('avocado.utils.cpu.open',
                            return_value=self._get_file_mock(s390x_2)):
                self.assertEqual(len(cpu.cpu_online_list()), 4)

    @unittest.skipUnless(recent_mock(),
                         "mock library version cannot (easily) patch open()")
    def test_x86_64_cpu_online(self):
        x86_64 = b"""processor	: 0
vendor_id	: GenuineIntel
cpu family	: 6
model		: 60
model name	: Intel(R) Core(TM) i7-4710MQ CPU @ 2.50GHz
stepping	: 3
microcode	: 0x22
cpu MHz		: 2494.301
cache size	: 6144 KB
physical id	: 0
siblings	: 8
core id		: 0
cpu cores	: 4
apicid		: 0
initial apicid	: 0
fpu		: yes
fpu_exception	: yes
cpuid level	: 13
wp		: yes
flags		: fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht tm pbe syscall nx pdpe1gb rdtscp lm constant_tsc arch_perfmon pebs bts rep_good nopl xtopology nonstop_tsc cpuid aperfmperf pni pclmulqdq dtes64 monitor ds_cpl vmx est tm2 ssse3 sdbg fma cx16 xtpr pdcm pcid sse4_1 sse4_2 movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand lahf_lm abm cpuid_fault epb tpr_shadow vnmi flexpriority ept vpid fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid xsaveopt dtherm ida arat pln pts
bugs		:
bogomips	: 4988.60
clflush size	: 64
cache_alignment	: 64
address sizes	: 39 bits physical, 48 bits virtual
power management:

processor	: 1
vendor_id	: GenuineIntel
cpu family	: 6
model		: 60
model name	: Intel(R) Core(TM) i7-4710MQ CPU @ 2.50GHz
stepping	: 3
microcode	: 0x22
cpu MHz		: 2494.301
cache size	: 6144 KB
physical id	: 0
siblings	: 8
core id		: 0
cpu cores	: 4
apicid		: 1
initial apicid	: 1
fpu		: yes
fpu_exception	: yes
cpuid level	: 13
wp		: yes
flags		: fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht tm pbe syscall nx pdpe1gb rdtscp lm constant_tsc arch_perfmon pebs bts rep_good nopl xtopology nonstop_tsc cpuid aperfmperf pni pclmulqdq dtes64 monitor ds_cpl vmx est tm2 ssse3 sdbg fma cx16 xtpr pdcm pcid sse4_1 sse4_2 movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand lahf_lm abm cpuid_fault epb tpr_shadow vnmi flexpriority ept vpid fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid xsaveopt dtherm ida arat pln pts
bugs		:
bogomips	: 4988.60
clflush size	: 64
cache_alignment	: 64
address sizes	: 39 bits physical, 48 bits virtual
power management:

processor	: 2
vendor_id	: GenuineIntel
cpu family	: 6
model		: 60
model name	: Intel(R) Core(TM) i7-4710MQ CPU @ 2.50GHz
stepping	: 3
microcode	: 0x22
cpu MHz		: 2494.301
cache size	: 6144 KB
physical id	: 0
siblings	: 8
core id		: 1
cpu cores	: 4
apicid		: 2
initial apicid	: 2
fpu		: yes
fpu_exception	: yes
cpuid level	: 13
wp		: yes
flags		: fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht tm pbe syscall nx pdpe1gb rdtscp lm constant_tsc arch_perfmon pebs bts rep_good nopl xtopology nonstop_tsc cpuid aperfmperf pni pclmulqdq dtes64 monitor ds_cpl vmx est tm2 ssse3 sdbg fma cx16 xtpr pdcm pcid sse4_1 sse4_2 movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand lahf_lm abm cpuid_fault epb tpr_shadow vnmi flexpriority ept vpid fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid xsaveopt dtherm ida arat pln pts
bugs		:
bogomips	: 4988.60
clflush size	: 64
cache_alignment	: 64
address sizes	: 39 bits physical, 48 bits virtual
power management:

processor	: 3
vendor_id	: GenuineIntel
cpu family	: 6
model		: 60
model name	: Intel(R) Core(TM) i7-4710MQ CPU @ 2.50GHz
stepping	: 3
microcode	: 0x22
cpu MHz		: 2494.301
cache size	: 6144 KB
physical id	: 0
siblings	: 8
core id		: 1
cpu cores	: 4
apicid		: 3
initial apicid	: 3
fpu		: yes
fpu_exception	: yes
cpuid level	: 13
wp		: yes
flags		: fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht tm pbe syscall nx pdpe1gb rdtscp lm constant_tsc arch_perfmon pebs bts rep_good nopl xtopology nonstop_tsc cpuid aperfmperf pni pclmulqdq dtes64 monitor ds_cpl vmx est tm2 ssse3 sdbg fma cx16 xtpr pdcm pcid sse4_1 sse4_2 movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand lahf_lm abm cpuid_fault epb tpr_shadow vnmi flexpriority ept vpid fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid xsaveopt dtherm ida arat pln pts
bugs		:
bogomips	: 4988.60
clflush size	: 64
cache_alignment	: 64
address sizes	: 39 bits physical, 48 bits virtual
power management:

processor	: 4
vendor_id	: GenuineIntel
cpu family	: 6
model		: 60
model name	: Intel(R) Core(TM) i7-4710MQ CPU @ 2.50GHz
stepping	: 3
microcode	: 0x22
cpu MHz		: 2494.301
cache size	: 6144 KB
physical id	: 0
siblings	: 8
core id		: 2
cpu cores	: 4
apicid		: 4
initial apicid	: 4
fpu		: yes
fpu_exception	: yes
cpuid level	: 13
wp		: yes
flags		: fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht tm pbe syscall nx pdpe1gb rdtscp lm constant_tsc arch_perfmon pebs bts rep_good nopl xtopology nonstop_tsc cpuid aperfmperf pni pclmulqdq dtes64 monitor ds_cpl vmx est tm2 ssse3 sdbg fma cx16 xtpr pdcm pcid sse4_1 sse4_2 movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand lahf_lm abm cpuid_fault epb tpr_shadow vnmi flexpriority ept vpid fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid xsaveopt dtherm ida arat pln pts
bugs		:
bogomips	: 4988.60
clflush size	: 64
cache_alignment	: 64
address sizes	: 39 bits physical, 48 bits virtual
power management:

processor	: 5
vendor_id	: GenuineIntel
cpu family	: 6
model		: 60
model name	: Intel(R) Core(TM) i7-4710MQ CPU @ 2.50GHz
stepping	: 3
microcode	: 0x22
cpu MHz		: 2494.301
cache size	: 6144 KB
physical id	: 0
siblings	: 8
core id		: 2
cpu cores	: 4
apicid		: 5
initial apicid	: 5
fpu		: yes
fpu_exception	: yes
cpuid level	: 13
wp		: yes
flags		: fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht tm pbe syscall nx pdpe1gb rdtscp lm constant_tsc arch_perfmon pebs bts rep_good nopl xtopology nonstop_tsc cpuid aperfmperf pni pclmulqdq dtes64 monitor ds_cpl vmx est tm2 ssse3 sdbg fma cx16 xtpr pdcm pcid sse4_1 sse4_2 movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand lahf_lm abm cpuid_fault epb tpr_shadow vnmi flexpriority ept vpid fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid xsaveopt dtherm ida arat pln pts
bugs		:
bogomips	: 4988.60
clflush size	: 64
cache_alignment	: 64
address sizes	: 39 bits physical, 48 bits virtual
power management:

processor	: 6
vendor_id	: GenuineIntel
cpu family	: 6
model		: 60
model name	: Intel(R) Core(TM) i7-4710MQ CPU @ 2.50GHz
stepping	: 3
microcode	: 0x22
cpu MHz		: 2494.301
cache size	: 6144 KB
physical id	: 0
siblings	: 8
core id		: 3
cpu cores	: 4
apicid		: 6
initial apicid	: 6
fpu		: yes
fpu_exception	: yes
cpuid level	: 13
wp		: yes
flags		: fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht tm pbe syscall nx pdpe1gb rdtscp lm constant_tsc arch_perfmon pebs bts rep_good nopl xtopology nonstop_tsc cpuid aperfmperf pni pclmulqdq dtes64 monitor ds_cpl vmx est tm2 ssse3 sdbg fma cx16 xtpr pdcm pcid sse4_1 sse4_2 movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand lahf_lm abm cpuid_fault epb tpr_shadow vnmi flexpriority ept vpid fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid xsaveopt dtherm ida arat pln pts
bugs		:
bogomips	: 4988.60
clflush size	: 64
cache_alignment	: 64
address sizes	: 39 bits physical, 48 bits virtual
power management:

processor	: 7
vendor_id	: GenuineIntel
cpu family	: 6
model		: 60
model name	: Intel(R) Core(TM) i7-4710MQ CPU @ 2.50GHz
stepping	: 3
microcode	: 0x22
cpu MHz		: 2494.301
cache size	: 6144 KB
physical id	: 0
siblings	: 8
core id		: 3
cpu cores	: 4
apicid		: 7
initial apicid	: 7
fpu		: yes
fpu_exception	: yes
cpuid level	: 13
wp		: yes
flags		: fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht tm pbe syscall nx pdpe1gb rdtscp lm constant_tsc arch_perfmon pebs bts rep_good nopl xtopology nonstop_tsc cpuid aperfmperf pni pclmulqdq dtes64 monitor ds_cpl vmx est tm2 ssse3 sdbg fma cx16 xtpr pdcm pcid sse4_1 sse4_2 movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand lahf_lm abm cpuid_fault epb tpr_shadow vnmi flexpriority ept vpid fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid xsaveopt dtherm ida arat pln pts
bugs		:
bogomips	: 4988.60
clflush size	: 64
cache_alignment	: 64
address sizes	: 39 bits physical, 48 bits virtual
power management:

"""
        with mock.patch('avocado.utils.cpu.platform.machine', return_value='x86_64'):
            with mock.patch('avocado.utils.cpu.open',
                            return_value=self._get_file_mock(x86_64)):
                self.assertEqual(len(cpu.cpu_online_list()), 8)

    @unittest.skipUnless(recent_mock(),
                         "mock library version cannot (easily) patch open()")
    def test_cpu_arch_i386(self):
        cpu_output = b"""processor       : 0
vendor_id       : GenuineIntel
cpu family      : 6
model           : 13
model name      : Intel(R) Pentium(R) M processor 2.00GHz
stepping        : 8
microcode       : 0x20
cpu MHz         : 2000.000
cache size      : 2048 KB
physical id     : 0
siblings        : 1
core id         : 0
cpu cores       : 1
apicid          : 0
initial apicid  : 0
fdiv_bug        : no
f00f_bug        : no
coma_bug        : no
fpu             : yes
fpu_exception   : yes
cpuid level     : 2
wp              : yes
flags           : fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov clflush dts acpi mmx fxsr sse sse2 ss tm pbe nx bts cpuid est tm2
bugs            : cpu_meltdown spectre_v1 spectre_v2
bogomips        : 3990.09
clflush size    : 64
cache_alignment : 64
address sizes   : 32 bits physical, 32 bits virtual
power management:
"""
        with mock.patch('avocado.utils.cpu.open',
                        return_value=self._get_file_mock(cpu_output)):
            self.assertEqual(cpu.get_cpu_arch(), "i386")

    @unittest.skipUnless(recent_mock(),
                         "mock library version cannot (easily) patch open()")
    def test_cpu_arch_x86_64(self):
        cpu_output = b"""processor       : 0
vendor_id       : GenuineIntel
cpu family      : 6
model           : 60
model name      : Intel(R) Core(TM) i7-4810MQ CPU @ 2.80GHz
stepping        : 3
microcode       : 0x24
cpu MHz         : 1766.058
cache size      : 6144 KB
physical id     : 0
siblings        : 8
core id         : 0
cpu cores       : 4
apicid          : 0
initial apicid  : 0
fpu             : yes
fpu_exception   : yes
cpuid level     : 13
wp              : yes
flags           : fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht tm pbe syscall nx pdpe1gb rdtscp lm constant_tsc arch_perfmon pebs bts rep_good nopl xtopology nonstop_tsc cpuid aperfmperf pni pclmulqdq dtes64 monitor ds_cpl vmx smx est tm2 ssse3 sdbg fma cx16 xtpr pdcm pcid sse4_1 sse4_2 x2apic movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand lahf_lm abm cpuid_fault epb invpcid_single pti tpr_shadow vnmi flexpriority ept vpid fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid xsaveopt ibpb ibrs stibp dtherm ida arat pln pts
bugs            : cpu_meltdown spectre_v1 spectre_v2
bogomips        : 5586.93
clflush size    : 64
cache_alignment : 64
address sizes   : 39 bits physical, 48 bits virtual
power management:
"""
        with mock.patch('avocado.utils.cpu.open',
                        return_value=self._get_file_mock(cpu_output)):
            self.assertEqual(cpu.get_cpu_arch(), "x86_64")

    @unittest.skipUnless(recent_mock(),
                         "mock library version cannot (easily) patch open()")
    def test_cpu_arch_ppc64_power8(self):
        cpu_output = b"""processor       : 88
cpu             : POWER8E (raw), altivec supported
clock           : 3325.000000MHz
revision        : 2.1 (pvr 004b 0201)

timebase        : 512000000
platform        : PowerNV
model           : 8247-21L
machine         : PowerNV 8247-21L
firmware        : OPAL v3
"""
        with mock.patch('avocado.utils.cpu.open',
                        return_value=self._get_file_mock(cpu_output)):
            self.assertEqual(cpu.get_cpu_arch(), "power8")

    @unittest.skipUnless(recent_mock(),
                         "mock library version cannot (easily) patch open()")
    def test_cpu_arch_ppc64_le_power8(self):
        cpu_output = b"""processor       : 88
cpu             : POWER8E (raw), altivec supported
clock           : 3325.000000MHz
revision        : 2.1 (pvr 004b 0201)

timebase        : 512000000
platform        : PowerNV
model           : 8247-21L
machine         : PowerNV 8247-21L
firmware        : OPAL v3
"""
        with mock.patch('avocado.utils.cpu.open',
                        return_value=self._get_file_mock(cpu_output)):
            self.assertEqual(cpu.get_cpu_arch(), "power8")

    @unittest.skipUnless(recent_mock(),
                         "mock library version cannot (easily) patch open()")
    def test_cpu_arch_ppc64_le_power9(self):
        cpu_output = b"""processor	: 20
cpu		: POWER9 (raw), altivec supported
clock		: 2050.000000MHz
revision	: 1.0 (pvr 004e 0100)

timebase	: 512000000
platform	: PowerNV
model		: 8375-42A
machine		: PowerNV 8375-42A
firmware	: OPAL
"""
        with mock.patch('avocado.utils.cpu.open',
                        return_value=self._get_file_mock(cpu_output)):
            self.assertEqual(cpu.get_cpu_arch(), "power9")

    @unittest.skipUnless(recent_mock(),
                         "mock library version cannot (easily) patch open()")
    def test_cpu_arch_s390(self):
        cpu_output = b"""vendor_id       : IBM/S390
# processors    : 2
bogomips per cpu: 2913.00
max thread id   : 0
features        : esan3 zarch stfle msa ldisp eimm dfp edat etf3eh highgprs te sie
facilities      : 0 1 2 3 4 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 30 31 32 33 34 35 36 37 40 41 42 43 44 45 46 47 48 49 50 51 52 57 64 65 66 67 68 69 70 71 72 73 75 76 77 78 81 82 131 132
cache0          : level=1 type=Data scope=Private size=96K line_size=256 associativity=6
cache1          : level=1 type=Instruction scope=Private size=64K line_size=256 associativity=4
cache2          : level=2 type=Data scope=Private size=1024K line_size=256 associativity=8
cache3          : level=2 type=Instruction scope=Private size=1024K line_size=256 associativity=8
cache4          : level=3 type=Unified scope=Shared size=49152K line_size=256 associativity=12
cache5          : level=4 type=Unified scope=Shared size=393216K line_size=256 associativity=24
processor 0: version = 00,  identification = 3FC047,  machine = 2827
processor 1: version = 00,  identification = 3FC047,  machine = 2827

cpu number      : 0
cpu MHz dynamic : 5504
cpu MHz static  : 5504

cpu number      : 1
cpu MHz dynamic : 5504
cpu MHz static  : 5504
"""
        with mock.patch('avocado.utils.cpu.open',
                        return_value=self._get_file_mock(cpu_output)):
            self.assertEqual(cpu.get_cpu_arch(), "s390")

    @unittest.skipUnless(recent_mock(),
                         "mock library version cannot (easily) patch open()")
    def test_cpu_arch_arm_v7(self):
        cpu_output = b"""Processor       : ARMv7 Processor rev 2 (v7l)
BogoMIPS        : 994.65
Features        : swp half thumb fastmult vfp edsp thumbee neon vfpv3
CPU implementer : 0x41
CPU architecture: 7
CPU variant     : 0x2
CPU part        : 0xc08
CPU revision    : 2

Hardware        : herring
Revision        : 0034
Serial          : 3534268a5e0700ec
"""
        with mock.patch('avocado.utils.cpu.open',
                        return_value=self._get_file_mock(cpu_output)):
            self.assertEqual(cpu.get_cpu_arch(), "arm")

    @unittest.skipUnless(recent_mock(),
                         "mock library version cannot (easily) patch open()")
    def test_cpu_arch_arm_v8(self):
        cpu_output = b"""processor       : 0
BogoMIPS        : 200.00
Features        : fp asimd evtstrm aes pmull sha1 sha2 crc32 cpuid
CPU implementer : 0x43
CPU architecture: 8
CPU variant     : 0x1
CPU part        : 0x0a1
CPU revision    : 1
"""
        with mock.patch('avocado.utils.cpu.open',
                        return_value=self._get_file_mock(cpu_output)):
            self.assertEqual(cpu.get_cpu_arch(), "aarch64")

    @unittest.skipUnless(recent_mock(),
                         "mock library version cannot (easily) patch open()")
    def test_cpu_arch_risc_v(self):
        cpu_output = b"""hart	: 1
isa	: rv64imafdc
mmu	: sv39
uarch	: sifive,rocket0
"""
        with mock.patch('avocado.utils.cpu.open',
                        return_value=self._get_file_mock(cpu_output)):
            self.assertEqual(cpu.get_cpu_arch(), "riscv")

    @unittest.skipUnless(recent_mock(),
                         "mock library version cannot (easily) patch open()")
    def test_get_cpuidle_state_off(self):
        retval = {0: {0: 0}}
        with mock.patch('avocado.utils.cpu.cpu_online_list', return_value=[0]):
            with mock.patch('glob.glob', return_value=['/sys/devices/system/cpu/cpu0/cpuidle/state1']):
                with mock.patch('avocado.utils.cpu.open', return_value=io.BytesIO(b'0')):
                    self.assertEqual(cpu.get_cpuidle_state(), retval)

    @unittest.skipUnless(recent_mock(),
                         "mock library version cannot (easily) patch open()")
    def test_get_cpuidle_state_on(self):
        retval = {0: {0: 1}}
        with mock.patch('avocado.utils.cpu.cpu_online_list', return_value=[0]):
            with mock.patch('glob.glob', return_value=['/sys/devices/system/cpu/cpu0/cpuidle/state1']):
                with mock.patch('avocado.utils.cpu.open', return_value=io.BytesIO(b'1')):
                    self.assertEqual(cpu.get_cpuidle_state(), retval)

    @unittest.skipUnless(recent_mock(),
                         "mock library version cannot (easily) patch open()")
    def test_set_cpuidle_state_default(self):
        output = io.BytesIO()
        with mock.patch('avocado.utils.cpu.cpu_online_list', return_value=[0]):
            with mock.patch('glob.glob', return_value=['/sys/devices/system/cpu/cpu0/cpuidle/state1']):
                with mock.patch('avocado.utils.cpu.open', return_value=output):
                    cpu.set_cpuidle_state()
                    self.assertEqual(output.getvalue(), b'1')

    @unittest.skipUnless(recent_mock(),
                         "mock library version cannot (easily) patch open()")
    def test_set_cpuidle_state_withstateno(self):
        output = io.BytesIO()
        with mock.patch('avocado.utils.cpu.cpu_online_list', return_value=[0]):
            with mock.patch('glob.glob', return_value=['/sys/devices/system/cpu/cpu0/cpuidle/state2']):
                with mock.patch('avocado.utils.cpu.open', return_value=output):
                    cpu.set_cpuidle_state(disable=False, state_number='2')
                    self.assertEqual(output.getvalue(), b'0')

    @unittest.skipUnless(recent_mock(),
                         "mock library version cannot (easily) patch open()")
    def test_set_cpuidle_state_withsetstate(self):
        output = io.BytesIO()
        with mock.patch('avocado.utils.cpu.cpu_online_list', return_value=[0, 2]):
            with mock.patch('glob.glob', return_value=['/sys/devices/system/cpu/cpu0/cpuidle/state1']):
                with mock.patch('avocado.utils.cpu.open', return_value=output):
                    cpu.set_cpuidle_state(setstate={0: {0: 1}, 2: {0: 0}})
                    self.assertEqual(output.getvalue(), b'10')


if __name__ == "__main__":
    unittest.main()
