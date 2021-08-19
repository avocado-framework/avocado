import json
import os
import unittest.mock

from avocado.core import exit_codes
from avocado.utils import path, process
from selftests.utils import AVOCADO, get_temporary_config


def missing_binary(binary):
    try:
        path.find_command(binary)
        return False
    except path.CmdNotFoundError:
        return True


def create_metadata_file(image_file, metadata):
    basename = os.path.splitext(image_file)[0]
    metadata_file = "%s_metadata.json" % basename
    metadata = json.dumps(metadata)
    with open(metadata_file, "w") as f:
        f.write(metadata)


class VMImagePlugin(unittest.TestCase):

    @unittest.skipUnless(os.environ.get('AVOCADO_SELFTESTS_NETWORK_ENABLED', False),
                         "Network required to run these tests")
    def setUp(self):
        (self.base_dir, self.mapping, self.config_file) = get_temporary_config(self)

    @unittest.skipIf(missing_binary('qemu-img'),
                     "QEMU disk image utility is required by the vmimage utility ")
    def test_download_image(self):
        expected_output = "Fedora-Cloud-Base-30-1.2.x86_64.qcow2"
        image_dir = os.path.join(self.mapping['cache_dir'], 'by_location',
                                 '89b7a3293bbc1dd73bb143b15fa06f0f9c7188b8')
        os.makedirs(image_dir)
        open(os.path.join(image_dir, expected_output), "w").close()
        cmd_line = "%s --config %s vmimage get --distro fedora --distro-version " \
                   "30 --arch x86_64" % (AVOCADO, self.config_file.name)
        result = process.run(cmd_line)
        self.assertIn(expected_output, result.stdout_text)

    def test_download_image_fail(self):
        cmd_line = "%s --config %s vmimage get --distro=SHOULD_NEVER_EXIST " \
                   "999 --arch zzz_64" % (AVOCADO, self.config_file.name)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_FAIL)

    def test_list_images(self):
        expected_output = "Fedora-Cloud-Base-30-1.2.x86_64.qcow2"
        metadata = {"type": "vmimage", "name": "Fedora", "version": 30,
                    "arch": "x86_64", "build": 1.2}
        image_dir = os.path.join(self.mapping['cache_dir'], 'by_location',
                                 '89b7a3293bbc1dd73bb143b15fa06f0f9c7188b8')
        os.makedirs(image_dir)
        expected_file = os.path.join(image_dir, expected_output)
        open(expected_file, "w").close()
        create_metadata_file(expected_file, metadata)
        cmd_line = "%s --config %s vmimage list" % (AVOCADO,
                                                    self.config_file.name)
        result = process.run(cmd_line)
        self.assertIn(expected_output, result.stdout_text)

    def tearDown(self):
        self.base_dir.cleanup()


if __name__ == '__main__':
    unittest.main()
