import unittest.mock
import os
import tempfile

from avocado.core import settings, data_dir
from avocado.plugins import vmimage as vmimage_plugin
from avocado.utils import vmimage as vmiage_util
from .. import temp_dir_prefix
from ..functional.test_plugin_vmimage import missing_binary


class VMImagePlugin(unittest.TestCase):

    def _get_temporary_dirs_mapping_and_config(self):
        """
        Creates a temporary bogus base data dir

        And returns a dictionary containing the temporary data dir paths and
        the path to a configuration file contain those same settings
        """
        prefix = temp_dir_prefix(__name__, self, 'setUp')
        base_dir = tempfile.TemporaryDirectory(prefix=prefix)
        data_directory = os.path.join(base_dir.name, 'data')
        os.mkdir(data_directory)
        os.mkdir(os.path.join(data_directory, 'cache'))
        mapping = {'base_dir': base_dir.name,
                   'data_dir': data_directory}
        temp_settings = ('[datadir.paths]\n'
                         'base_dir = %(base_dir)s\n'
                         'data_dir = %(data_dir)s\n') % mapping
        config_file = tempfile.NamedTemporaryFile('w', delete=False)
        config_file.write(temp_settings)
        config_file.close()
        return base_dir, mapping, config_file.name

    def _create_test_files(self):
        with unittest.mock.patch('avocado.core.data_dir.settings.settings', self.stg):
            expected_images = [{'name': 'CentOS', 'file': 'CentOS-{version}-{arch}-GenericCloud-{build}.qcow2.xz$'},
                               {'name': 'Debian', 'file': 'debian-{version}-openstack-{arch}.qcow2$'},
                               {'name': 'JeOS', 'file': 'jeos-{version}-{arch}.qcow2.xz$'},
                               {'name': 'OpenSUSE', 'file': 'openSUSE-Leap-{version}-OpenStack.{arch}-{build}.qcow2$'},
                               {'name': 'Ubuntu', 'file': 'ubuntu-{version}-server-cloudimg-{arch}.img'}
                               ]
            cache_dir = data_dir.get_cache_dirs()[0]
            providers = [provider() for provider in vmiage_util.list_providers()]

            for provider in providers:
                for image in expected_images:
                    if image['name'] == provider.name:
                        path = os.path.join(cache_dir, "vmimage", image['name'],
                                            str(provider.version), provider.arch)
                        os.makedirs(path)
                        image['version'] = str(provider.version)
                        image['arch'] = provider.arch
                        image['build'] = "1234"
                        image['file'] = os.path.join(path, image['file'].format(
                            version=provider.version,
                            build=image['build'],
                            arch=provider.arch).replace('$', ''))
                        open(image["file"], "a").close()
            return sorted(expected_images, key=lambda i: i['name'])

    def setUp(self):
        (self.base_dir, self.mapping,
         self.config_file_path) = self._get_temporary_dirs_mapping_and_config()
        self.stg = settings.Settings(self.config_file_path)
        self.expected_images = self._create_test_files()

    def test_list_downloaded_images(self):
        with unittest.mock.patch('avocado.core.data_dir.settings.settings', self.stg):
            images = sorted(vmimage_plugin.list_downloaded_images(), key=lambda i: i['name'])
            for index, image in enumerate(images):
                for key in image:
                    self.assertEqual(self.expected_images[index][key], image[key],
                                     "Founded image is different from the expected one")

    @unittest.skipIf(int(os.environ.get("AVOCADO_CHECK_LEVEL", 0)) < 2,
                     "Skipping test that take a long time to run, are "
                     "resource intensive or time sensitve")
    @unittest.skipIf(missing_binary('qemu-img'),
                     "QEMU disk image utility is required by the vmimage utility ")
    def test_download_image(self):
        with unittest.mock.patch('avocado.core.data_dir.settings.settings', self.stg):
            expected_image_info = vmiage_util.get_best_provider(name="Fedora")
            image_info = vmimage_plugin.download_image(distro="Fedora")
            self.assertEqual(expected_image_info.name, image_info['name'],
                             "Downloaded image is different from the expected one")
            self.assertEqual(expected_image_info.version, image_info['version'],
                             "Downloaded image is different from the expected one")
            self.assertEqual(expected_image_info.arch, image_info['arch'],
                             "Downloaded image is different from the expected one")
            self.assertTrue(os.path.isfile(image_info["file"]),
                            "The image wasn't downloaded")

    def tearDown(self):
        self.base_dir.cleanup()


if __name__ == '__main__':
    unittest.main()
