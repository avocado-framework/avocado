import json
import os
import tempfile
import unittest.mock

from avocado.utils import process, path
from .. import AVOCADO, temp_dir_prefix


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

    def _get_temporary_config(self):
        """
        Creates a temporary bogus config file
        returns base directory, dictionary containing the temporary data dir
        paths and the configuration file contain those same settings
        """
        prefix = temp_dir_prefix(__name__, self, 'setUp')
        base_dir = tempfile.TemporaryDirectory(prefix=prefix)
        test_dir = os.path.join(base_dir.name, 'tests')
        os.mkdir(test_dir)
        data_directory = os.path.join(base_dir.name, 'data')
        os.mkdir(data_directory)
        cache_dir = os.path.join(data_directory, 'cache')
        os.mkdir(cache_dir)
        mapping = {'base_dir': base_dir.name,
                   'test_dir': test_dir,
                   'data_dir': data_directory,
                   'logs_dir': os.path.join(base_dir.name, 'logs'),
                   'cache_dir': cache_dir}
        temp_settings = ('[datadir.paths]\n'
                         'base_dir = %(base_dir)s\n'
                         'test_dir = %(test_dir)s\n'
                         'data_dir = %(data_dir)s\n'
                         'logs_dir = %(logs_dir)s\n') % mapping
        config_file = tempfile.NamedTemporaryFile('w', delete=False)
        config_file.write(temp_settings)
        config_file.close()
        return base_dir, mapping, config_file

    @unittest.skipUnless(os.environ.get('AVOCADO_SELFTESTS_NETWORK_ENABLED', False),
                         "Network required to run these tests")
    def setUp(self):
        (self.base_dir, self.mapping, self.config_file) = self._get_temporary_config()

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
