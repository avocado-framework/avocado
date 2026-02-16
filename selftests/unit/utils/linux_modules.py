import io
import sys
import unittest.mock

from avocado import Test, skipIf
from avocado.utils import linux_modules


class Lsmod(Test):
    def setUp(self):
        with open(self.get_data("lsmod"), encoding="utf-8") as lsmod_file:
            self.lsmod_out = lsmod_file.read()

    def test_parse_lsmod(self):
        lsmod_info = linux_modules.parse_lsmod_for_module(self.lsmod_out, "ebtables")
        self.assertEqual(
            lsmod_info,
            {
                "name": "ebtables",
                "size": 30758,
                "used": 3,
                "submodules": ["ebtable_broute", "ebtable_nat", "ebtable_filter"],
            },
        )

    def test_parse_lsmod_is_empty(self):
        lsmod_info = linux_modules.parse_lsmod_for_module("", "ebtables")
        self.assertEqual(lsmod_info, {})

    def test_parse_lsmod_no_submodules(self):
        lsmod_info = linux_modules.parse_lsmod_for_module(self.lsmod_out, "ccm")
        self.assertEqual(
            lsmod_info, {"name": "ccm", "size": 17773, "used": 2, "submodules": []}
        )

    def test_parse_lsmod_single_submodules(self):
        lsmod_info = linux_modules.parse_lsmod_for_module(self.lsmod_out, "bridge")
        self.assertEqual(
            lsmod_info,
            {
                "name": "bridge",
                "size": 110862,
                "used": 1,
                "submodules": ["ebtable_broute"],
            },
        )


class Modules(Test):
    def _get_data_mock(self, data_name):
        with open(self.get_data(data_name), "rb") as data_file:
            content = data_file.read()
        file_mock = unittest.mock.Mock()
        file_mock.__enter__ = unittest.mock.Mock(return_value=io.BytesIO(content))
        file_mock.__exit__ = unittest.mock.Mock()
        return file_mock

    @skipIf(sys.platform.startswith("darwin"), "macOS does not support Linux Modules")
    def test_is_module_loaded(self):
        with unittest.mock.patch(
            "builtins.open", return_value=self._get_data_mock("proc_modules")
        ):
            self.assertTrue(linux_modules.module_is_loaded("rfcomm"))
            self.assertFalse(linux_modules.module_is_loaded("unknown_module"))

    @unittest.mock.patch("avocado.utils.linux_modules.check_kernel_config")
    def test_configure_module_1(self, mock_check_kernel_config):
        mock_check_kernel_config.return_value = linux_modules.ModuleConfig.NOT_SET
        self.assertFalse(linux_modules.configure_module("mod", "CONFIG_MOD"))

    @unittest.mock.patch("avocado.utils.linux_modules.module_is_loaded")
    @unittest.mock.patch("avocado.utils.linux_modules.load_module")
    @unittest.mock.patch("avocado.utils.linux_modules.check_kernel_config")
    def test_configure_module_2(self, mock_check, mock_load, mock_loaded):
        mock_check.return_value = linux_modules.ModuleConfig.BUILTIN
        self.assertTrue(linux_modules.configure_module("mod", "CONFIG_MOD"))
        mock_load.assert_not_called()
        mock_loaded.assert_not_called()

    @unittest.mock.patch("avocado.utils.linux_modules.module_is_loaded")
    @unittest.mock.patch("avocado.utils.linux_modules.load_module")
    @unittest.mock.patch("avocado.utils.linux_modules.check_kernel_config")
    def test_configure_module_3(self, mock_check, mock_load, mock_loaded):
        mock_check.return_value = linux_modules.ModuleConfig.MODULE
        mock_load.return_value = True
        mock_loaded.return_value = True
        self.assertTrue(linux_modules.configure_module("mod", "CONFIG_MOD"))

    @unittest.mock.patch("avocado.utils.linux_modules.module_is_loaded")
    @unittest.mock.patch("avocado.utils.linux_modules.load_module")
    @unittest.mock.patch("avocado.utils.linux_modules.check_kernel_config")
    def test_configure_module_4(self, mock_check, mock_load, mock_loaded):
        mock_check.return_value = linux_modules.ModuleConfig.MODULE
        mock_load.return_value = False
        mock_loaded.return_value = False
        self.assertFalse(linux_modules.configure_module("mod", "CONFIG_MOD"))


if __name__ == "__main__":
    unittest.main()
