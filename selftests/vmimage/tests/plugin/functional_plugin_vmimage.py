import json
import os
import unittest.mock

from avocado.core import exit_codes
from avocado.utils import process
from selftests.utils import AVOCADO, get_temporary_config, missing_binary


def create_metadata_file(image_file, metadata):
    basename = os.path.splitext(image_file)[0]
    metadata_file = f"{basename}_metadata.json"
    metadata = json.dumps(metadata)
    with open(metadata_file, "w", encoding="utf-8") as f:
        f.write(metadata)


class VMImagePlugin(unittest.TestCase):
    def setUp(self):
        (self.base_dir, self.mapping, self.config_file) = get_temporary_config(self)

    @unittest.skipIf(
        missing_binary("qemu-img"),
        "QEMU disk image utility is required by the vmimage utility ",
    )
    def test_download_image(self):
        expected_output = "Fedora-Cloud-Base-30-1.2.x86_64.qcow2"
        image_dir = os.path.join(
            self.mapping["cache_dir"],
            "by_location",
            "89b7a3293bbc1dd73bb143b15fa06f0f9c7188b8",
        )
        os.makedirs(image_dir)
        open(os.path.join(image_dir, expected_output), "w", encoding="utf-8").close()
        cmd_line = (
            f"{AVOCADO} --config {self.config_file.name} vmimage "
            f"get --distro fedora --distro-version 30 --arch x86_64"
        )
        result = process.run(cmd_line)
        self.assertIn(expected_output, result.stdout_text)

    def test_download_image_fail(self):
        cmd_line = (
            f"{AVOCADO} --config {self.config_file.name} vmimage "
            f"get --distro=SHOULD_NEVER_EXIST 999 --arch zzz_64"
        )
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_FAIL)

    def test_list_images(self):
        expected_output = "Fedora-Cloud-Base-30-1.2.x86_64.qcow2"
        metadata = {
            "type": "vmimage",
            "name": "Fedora",
            "version": 30,
            "arch": "x86_64",
            "build": 1.2,
        }
        image_dir = os.path.join(
            self.mapping["cache_dir"],
            "by_location",
            "89b7a3293bbc1dd73bb143b15fa06f0f9c7188b8",
        )
        os.makedirs(image_dir)
        expected_file = os.path.join(image_dir, expected_output)
        open(expected_file, "w", encoding="utf-8").close()
        create_metadata_file(expected_file, metadata)
        cmd_line = f"{AVOCADO} --config {self.config_file.name} vmimage list"
        result = process.run(cmd_line)
        self.assertIn(expected_output, result.stdout_text)

    def test_get_debug(self):
        cmd_line = (
            f"{AVOCADO} --config {self.config_file.name} vmimage "
            f"get --debug --distro=SHOULD_NEVER_EXIST --arch zzz_64"
        )
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_FAIL)
        self.assertIn(
            "Provider for should_never_exist not available", result.stdout_text
        )

    def tearDown(self):
        self.base_dir.cleanup()


if __name__ == "__main__":
    unittest.main()
