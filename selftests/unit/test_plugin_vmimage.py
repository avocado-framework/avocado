import unittest.mock
import os
import tempfile

from avocado.core import settings, data_dir
from avocado.plugins import vmimage as vmimage_plugin
from avocado.utils import vmimage as vmiage_util
from .. import temp_dir_prefix


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

    def setUp(self):
        (self.base_dir, self.mapping,
         self.config_file_path) = self._get_temporary_dirs_mapping_and_config()
        self.stg = settings.Settings(self.config_file_path)

    def test_list_downloaded_images(self):
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
                        image['version'] = str(provider.version)
                        image['arch'] = provider.arch
                        image['build'] = "1234"
                        image['file'] = os.path.join(cache_dir, image['file'].
                                                     format(version=provider.version,
                                                            build=image['build'],
                                                            arch=provider.arch).replace('$', ''))
                        open(image["file"], "a").close()
            expected_images = sorted(expected_images, key=lambda i: i['name'])
            images = sorted(vmimage_plugin.list_downloaded_images(), key=lambda i: i['name'])
            for index, image in enumerate(images):
                for key in image:
                    self.assertEqual(expected_images[index][key], image[key])

    def tearDown(self):
        self.base_dir.cleanup()


if __name__ == '__main__':
    unittest.main()
