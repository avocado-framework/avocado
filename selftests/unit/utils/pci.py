import errno
import unittest.mock

from avocado.utils import pci


class UtilsPciTest(unittest.TestCase):
    def test_get_slot_from_sysfs(self):
        pcid = "0002:01:00.1"
        file_values = [
            "S0001",
            "S0001[",
            "Slot2",
            "SLOT1",
            "Backplane USB",
            "U78CB.001.WZS07CU-P1-C9-T1",
            "PLX Slot1",
            "Onboard USB",
            "U78D5.001.CSS130E-P1-P2-P2-C1-T1",
        ]
        expected_values = [
            "S0001",
            "S0001",
            "Slot2",
            "SLOT1",
            "Backplane USB",
            "U78CB.001.WZS07CU-P1-C9",
            "PLX Slot1",
            "Onboard USB",
            "U78D5.001.CSS130E-P1-P2-P2-C1",
        ]
        for value, exp in zip(file_values, expected_values):
            with unittest.mock.patch("os.path.isfile", return_value=True):
                with unittest.mock.patch(
                    "avocado.utils.genio.read_file", return_value=value
                ):
                    self.assertEqual(pci.get_slot_from_sysfs(pcid), exp)

    def test_get_slot_from_sysfs_negative(self):
        with unittest.mock.patch("os.path.isfile", return_value=True):
            with unittest.mock.patch(
                "avocado.utils.genio.read_file", return_value=".....bad-value....."
            ):
                self.assertRaises(ValueError, pci.get_slot_from_sysfs, "0002:01:00.1")

    @unittest.mock.patch("avocado.utils.pci.get_vendor_id")
    @unittest.mock.patch("avocado.utils.pci.genio.write_file")
    def test_add_vendor_id_success(self, mock_write, mock_get_vid):
        mock_get_vid.return_value = "1234:abcd"
        pci.add_vendor_id("0000:03:00.0", "driver")
        mock_get_vid.assert_called_once_with("0000:03:00.0")
        mock_write.assert_called_once_with(
            "/sys/bus/pci/drivers/driver/new_id", "1234 abcd\n"
        )

    @unittest.mock.patch("avocado.utils.pci.get_vendor_id", return_value="1234:abcd")
    @unittest.mock.patch(
        "avocado.utils.pci.genio.write_file",
        side_effect=OSError(errno.EEXIST, "File exists"),
    )
    def test_add_vendor_id_already_exists(self, mock_write, mock_get_vid):
        pci.add_vendor_id("0000:03:00.0", "driver")
        mock_get_vid.assert_called_once_with("0000:03:00.0")
        mock_write.assert_called_once_with(
            "/sys/bus/pci/drivers/driver/new_id", "1234 abcd\n"
        )

    @unittest.mock.patch("avocado.utils.pci.bind")
    @unittest.mock.patch("avocado.utils.pci.unbind")
    @unittest.mock.patch("avocado.utils.pci.get_driver")
    @unittest.mock.patch("avocado.utils.pci.add_vendor_id")
    def test_attach_driver(self, mock_add_vid, mock_get_driver, mock_unbind, mock_bind):
        mock_get_driver.return_value = "old_driver"
        pci.attach_driver("0000:03:00.0", "new_driver")
        mock_add_vid.assert_called_once()
        mock_unbind.assert_called_once_with("old_driver", "0000:03:00.0")
        mock_bind.assert_called_once_with("new_driver", "0000:03:00.0")

    @unittest.mock.patch("avocado.utils.pci.process.run")
    def test_check_msix_capability_supported(self, mock_run):
        mock_run.return_value.exit_status = 0
        mock_run.return_value.stdout_text = "Capabilities: [90] MSI-X: Enable+ Count=16"
        self.assertTrue(pci.check_msix_capability("0000:03:00.0"))

    @unittest.mock.patch("avocado.utils.pci.process.run")
    def test_check_msix_capability_unsupported(self, mock_run):
        mock_run.return_value.exit_status = 0
        mock_run.return_value.stdout_text = "Capabilities: [90] MSI: Enable+ Count=16"
        self.assertFalse(pci.check_msix_capability("0000:03:00.0"))

    @unittest.mock.patch("avocado.utils.pci.process.run")
    def test_device_supports_irqs_enough(self, mock_run):
        mock_run.return_value.exit_status = 0
        mock_run.return_value.stdout_text = "MSI-X: Enable+ Count=64"
        self.assertTrue(pci.device_supports_irqs("0000:03:00.0", 32))

    @unittest.mock.patch("avocado.utils.pci.process.run")
    def test_device_supports_irqs_insufficient(self, mock_run):
        mock_run.return_value.exit_status = 0
        mock_run.return_value.stdout_text = "MSI-X: Enable+ Count=4"
        self.assertFalse(pci.device_supports_irqs("0000:03:00.0", 16))

    @unittest.mock.patch("avocado.utils.pci.process.run")
    def test_device_supports_irqs_no_msix(self, mock_run):
        mock_run.return_value.exit_status = 0
        mock_run.return_value.stdout_text = "Capabilities: [90] MSI: Enable+ Count=16"
        self.assertFalse(pci.device_supports_irqs("0000:03:00.0", 8))


if __name__ == "__main__":
    unittest.main()
