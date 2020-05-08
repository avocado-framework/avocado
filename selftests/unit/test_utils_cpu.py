import io
import unittest.mock

from avocado import Test
from avocado.utils import cpu


class Cpu(Test):

    @staticmethod
    def _get_file_mock(content):
        file_mock = unittest.mock.Mock()
        file_mock.__enter__ = unittest.mock.Mock(
            return_value=io.BytesIO(content))
        file_mock.__exit__ = unittest.mock.Mock()
        return file_mock

    def _get_data_mock(self, data_name):
        with open(self.get_data(data_name), 'rb') as data_file:
            content = data_file.read()
        return self._get_file_mock(content)

    def test_s390x_cpu_online(self):
        with unittest.mock.patch('avocado.utils.cpu.platform.machine',
                                 return_value='s390x'):
            with unittest.mock.patch(
                    'builtins.open',
                    return_value=self._get_data_mock('s390x')):
                self.assertEqual(len(cpu.online_list()), 2)
            with unittest.mock.patch(
                    'builtins.open',
                    return_value=self._get_data_mock('s390x_2')):
                self.assertEqual(len(cpu.online_list()), 4)

    def test_x86_64_cpu_online(self):
        with unittest.mock.patch('avocado.utils.cpu.platform.machine',
                                 return_value='x86_64'):
            with unittest.mock.patch('builtins.open',
                                     return_value=self._get_data_mock('x86_64')):
                self.assertEqual(len(cpu.online_list()), 8)

    def test_cpu_arch_i386(self):
        with unittest.mock.patch('builtins.open',
                                 return_value=self._get_data_mock('i386')):
            self.assertEqual(cpu.get_arch(), "i386")

    def test_cpu_arch_x86_64(self):
        with unittest.mock.patch('builtins.open',
                                 return_value=self._get_data_mock('x86_64')):
            self.assertEqual(cpu.get_arch(), "x86_64")

    def test_cpu_has_flags(self):
        with unittest.mock.patch('builtins.open',
                                 return_value=self._get_data_mock('x86_64')):
            self.assertTrue(cpu.cpu_has_flags('flexpriority'))
            self.assertTrue(cpu.cpu_has_flags(['sse4_2', 'xsaveopt']))
            self.assertFalse(cpu.cpu_has_flags('THIS_WILL_NEVER_BE_A_FLAG_NAME'))
            self.assertFalse(cpu.cpu_has_flags(['THIS_WILL_NEVER_BE_A_FLAG_NAME',
                                                'NEITHER_WILL_THIS_WILL_EVER_BE']))

    def test_cpu_arch_power8(self):
        with unittest.mock.patch('builtins.open',
                                 return_value=self._get_data_mock('power8')):
            self.assertEqual(cpu.get_arch(), "powerpc")

    def test_cpu_arch_power9(self):
        with unittest.mock.patch('builtins.open',
                                 return_value=self._get_data_mock('power9')):
            self.assertEqual(cpu.get_arch(), "powerpc")

    def test_cpu_arch_s390(self):
        with unittest.mock.patch(
                'builtins.open',
                return_value=self._get_data_mock('s390x')):
            self.assertEqual(cpu.get_arch(), "s390")

    def test_cpu_arch_arm_v7(self):
        with unittest.mock.patch('builtins.open',
                                 return_value=self._get_data_mock('armv7')):
            self.assertEqual(cpu.get_arch(), "arm")

    def test_cpu_arch_arm_v8(self):
        with unittest.mock.patch('builtins.open',
                                 return_value=self._get_data_mock('armv8')):
            self.assertEqual(cpu.get_arch(), "aarch64")

    def test_cpu_arch_risc_v(self):
        with unittest.mock.patch('builtins.open',
                                 return_value=self._get_data_mock('risc_v')):
            self.assertEqual(cpu.get_arch(), "riscv")

    def test_cpu_vendor_intel(self):
        with unittest.mock.patch('builtins.open',
                                 return_value=self._get_data_mock('x86_64')):
            self.assertEqual(cpu.get_vendor(), "intel")

    def test_cpu_vendor_power8(self):
        with unittest.mock.patch('builtins.open',
                                 return_value=self._get_data_mock('power8')):
            self.assertEqual(cpu.get_vendor(), "ibm")

    def test_cpu_vendor_power9(self):
        with unittest.mock.patch('builtins.open',
                                 return_value=self._get_data_mock('power9')):
            self.assertEqual(cpu.get_vendor(), "ibm")

    def test_s390x_get_version(self):
        with unittest.mock.patch('avocado.utils.cpu.platform.machine',
                                 return_value='s390x'):
            with unittest.mock.patch(
                    'builtins.open',
                    return_value=self._get_data_mock('s390x')):
                self.assertEqual(cpu.get_version(), "2827")

    def test_intel_get_version(self):
        with unittest.mock.patch('avocado.utils.cpu.platform.machine',
                                 return_value='x86_64'):
            with unittest.mock.patch('builtins.open',
                                     return_value=self._get_data_mock('x86_64')):
                self.assertEqual(cpu.get_version(), "i7-4710MQ")

    def test_power8_get_version(self):
        with unittest.mock.patch('avocado.utils.cpu.platform.machine',
                                 return_value='powerpc'):
            with unittest.mock.patch('builtins.open',
                                     return_value=self._get_data_mock('power8')):
                self.assertEqual(cpu.get_version(), "2.1")

    def test_power9_get_version(self):
        with unittest.mock.patch('avocado.utils.cpu.platform.machine',
                                 return_value='powerpc'):
            with unittest.mock.patch('builtins.open',
                                     return_value=self._get_data_mock('power9')):
                self.assertEqual(cpu.get_version(), "1.0")

    def test_s390x_get_family(self):
        with unittest.mock.patch('avocado.utils.cpu.get_arch',
                                 return_value='s390'):
            with unittest.mock.patch('avocado.utils.cpu.get_version',
                                     return_value='8561'):
                self.assertEqual(cpu.get_family(), "z15")

    def test_intel_get_family(self):
        with unittest.mock.patch('avocado.utils.cpu.get_arch',
                                 return_value='x86_64'):
            with unittest.mock.patch('avocado.utils.cpu.get_vendor',
                                     return_value='intel'):
                with unittest.mock.patch(
                        'builtins.open',
                        return_value=self._get_file_mock(b'broadwell')):
                    self.assertEqual(cpu.get_family(), "broadwell")

    def test_power8_get_family(self):
        with unittest.mock.patch('avocado.utils.cpu.get_arch',
                                 return_value='powerpc'):
            with unittest.mock.patch('builtins.open',
                                     return_value=self._get_data_mock('power8')):
                self.assertEqual(cpu.get_family(), "power8")

    def test_power9_get_family(self):
        with unittest.mock.patch('avocado.utils.cpu.get_arch', return_value='powerpc'):
            with unittest.mock.patch('builtins.open',
                                     return_value=self._get_data_mock('power9')):
                self.assertEqual(cpu.get_family(), "power9")

    def test_get_idle_state_off(self):
        retval = {0: {0: False}}
        with unittest.mock.patch('avocado.utils.cpu.online_list',
                                 return_value=[0]):
            with unittest.mock.patch('glob.glob',
                                     return_value=['/sys/devices/system/cpu/cpu0/cpuidle/state1']):
                with unittest.mock.patch('builtins.open',
                                         return_value=io.BytesIO(b'0')):
                    self.assertEqual(cpu.get_idle_state(), retval)

    def test_get_idle_state_on(self):
        retval = {0: {0: True}}
        with unittest.mock.patch('avocado.utils.cpu.online_list',
                                 return_value=[0]):
            with unittest.mock.patch('glob.glob',
                                     return_value=['/sys/devices/system/cpu/cpu0/cpuidle/state1']):
                with unittest.mock.patch('builtins.open',
                                         return_value=io.BytesIO(b'1')):
                    self.assertEqual(cpu.get_idle_state(), retval)

    def test_set_idle_state_default(self):
        output = io.BytesIO()
        with unittest.mock.patch('avocado.utils.cpu.online_list',
                                 return_value=[0]):
            with unittest.mock.patch('glob.glob',
                                     return_value=['/sys/devices/system/cpu/cpu0/cpuidle/state1']):
                with unittest.mock.patch('builtins.open',
                                         return_value=output):
                    cpu.set_idle_state()
                    self.assertEqual(output.getvalue(), b'1')

    def test_set_idle_state_withstateno(self):
        output = io.BytesIO()
        with unittest.mock.patch('avocado.utils.cpu.online_list',
                                 return_value=[0]):
            with unittest.mock.patch('glob.glob',
                                     return_value=['/sys/devices/system/cpu/cpu0/cpuidle/state2']):
                with unittest.mock.patch('builtins.open',
                                         return_value=output):
                    cpu.set_idle_state(disable=False, state_number='2')
                    self.assertEqual(output.getvalue(), b'0')

    def test_set_idle_state_withsetstate(self):
        output = io.BytesIO()
        with unittest.mock.patch('avocado.utils.cpu.online_list',
                                 return_value=[0, 2]):
            with unittest.mock.patch('glob.glob',
                                     return_value=['/sys/devices/system/cpu/cpu0/cpuidle/state1']):
                with unittest.mock.patch('builtins.open',
                                         return_value=output):
                    cpu.set_idle_state(setstate={0: {0: True}, 2: {0: False}})
                    self.assertEqual(output.getvalue(), b'10')

    def test_set_idle_state_disable(self):
        output = io.BytesIO()
        function = 'avocado.utils.cpu.online_list'
        state_file = '/sys/devices/system/cpu/cpu0/cpuidle/state1'
        with unittest.mock.patch(function, return_value=[0, 2]):
            with unittest.mock.patch('glob.glob', return_value=[state_file]):
                with unittest.mock.patch('builtins.open', return_value=output):
                    with self.assertRaises(TypeError):
                        cpu.set_idle_state(disable=1)


if __name__ == "__main__":
    unittest.main()
