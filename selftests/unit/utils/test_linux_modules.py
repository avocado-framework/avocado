import io
import unittest.mock

from avocado import Test
from avocado.utils import linux_modules


class Lsmod(Test):

    def setUp(self):
        with open(self.get_data('lsmod'), encoding='utf-8') as lsmod_file:
            self.lsmod_out = lsmod_file.read()

    def test_parse_lsmod(self):
        lsmod_info = linux_modules.parse_lsmod_for_module(
            self.lsmod_out, "ebtables")
        self.assertEqual(lsmod_info, {'name': "ebtables",
                                      'size': 30758,
                                      'used': 3,
                                      'submodules': ['ebtable_broute',
                                                     'ebtable_nat',
                                                     'ebtable_filter']})

    def test_parse_lsmod_is_empty(self):
        lsmod_info = linux_modules.parse_lsmod_for_module("", "ebtables")
        self.assertEqual(lsmod_info, {})

    def test_parse_lsmod_no_submodules(self):
        lsmod_info = linux_modules.parse_lsmod_for_module(self.lsmod_out, "ccm")
        self.assertEqual(lsmod_info, {'name': "ccm",
                                      'size': 17773,
                                      'used': 2,
                                      'submodules': []})

    def test_parse_lsmod_single_submodules(self):
        lsmod_info = linux_modules.parse_lsmod_for_module(
            self.lsmod_out, "bridge")
        self.assertEqual(lsmod_info, {'name': "bridge",
                                      'size': 110862,
                                      'used': 1,
                                      'submodules': ['ebtable_broute']})


class Modules(Test):

    def _get_data_mock(self, data_name):
        with open(self.get_data(data_name), 'rb') as data_file:
            content = data_file.read()
        file_mock = unittest.mock.Mock()
        file_mock.__enter__ = unittest.mock.Mock(
            return_value=io.BytesIO(content))
        file_mock.__exit__ = unittest.mock.Mock()
        return file_mock

    def test_is_module_loaded(self):
        with unittest.mock.patch('builtins.open',
                                 return_value=self._get_data_mock('proc_modules')):
            self.assertTrue(linux_modules.module_is_loaded("rfcomm"))
            self.assertFalse(linux_modules.module_is_loaded("unknown_module"))


if __name__ == '__main__':
    unittest.main()
