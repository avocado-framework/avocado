import unittest.mock

from avocado.utils import pci


class UtilsPciTest(unittest.TestCase):

    def test_get_slot_from_sysfs(self):
        pcid = '0002:01:00.1'
        file_values = ['S0001', 'S0001[', 'Slot2', 'SLOT1', 'Backplane USB', 'U78CB.001.WZS07CU-P1-C9-T1', 'PLX Slot1', 'Onboard USB', 'U78D5.001.CSS130E-P1-P2-P2-C1-T1']
        expected_values = ['S0001', 'S0001', 'Slot2', 'SLOT1', 'Backplane USB', 'U78CB.001.WZS07CU-P1-C9', 'PLX Slot1', 'Onboard USB', 'U78D5.001.CSS130E-P1-P2-P2-C1']
        for value, exp in zip(file_values, expected_values):
            with unittest.mock.patch('os.path.isfile', return_value=True):
                with unittest.mock.patch('avocado.utils.genio.read_file',
                                         return_value=value):
                    self.assertEqual(pci.get_slot_from_sysfs(pcid), exp)

    def test_get_slot_from_sysfs_negative(self):
        with unittest.mock.patch('os.path.isfile', return_value=True):
            with unittest.mock.patch('avocado.utils.genio.read_file',
                                     return_value='.....bad-value.....'):
                self.assertRaises(ValueError, pci.get_slot_from_sysfs,
                                  '0002:01:00.1')


if __name__ == '__main__':
    unittest.main()
