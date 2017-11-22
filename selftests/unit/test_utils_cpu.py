import io
import unittest

try:
    from unittest import mock
except ImportError:
    import mock


from avocado.utils import cpu


class Cpu(unittest.TestCase):

    @staticmethod
    def _get_file_mock(content):
        file_mock = mock.Mock()
        file_mock.__enter__ = mock.Mock(return_value=io.StringIO(content))
        file_mock.__exit__ = mock.Mock()
        return file_mock

    def test_s390x(self):
        s390x = u"""vendor_id       : IBM/S390
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

        s390x_2 = u"""vendor_id       : IBM/S390
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


if __name__ == "__main__":
    unittest.main()
