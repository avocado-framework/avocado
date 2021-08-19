import os
import tempfile
import unittest.mock
from urllib.error import URLError

from avocado.core.settings import Settings
from avocado.plugins import vmimage as vmimage_plugin
from avocado.utils import vmimage as vmimage_util
from selftests.functional.plugin.test_vmimage import (create_metadata_file,
                                                      missing_binary)
from selftests.utils import skipOnLevelsInferiorThan, temp_dir_prefix

#: extracted from https://dl.fedoraproject.org/pub/fedora/linux/releases/
FEDORA_PAGE = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
<html>
 <head>
  <title>Index of /pub/fedora/linux/releases</title>
 </head>
 <body>
<h1>Index of /pub/fedora/linux/releases</h1>
<pre><img src="/icons/blank.gif" alt="Icon "> <a href="?C=N;O=D">Name</a>
<a href="?C=M;O=A">Last modified</a>      <a href="?C=S;O=A">Size</a>
<a href="?C=D;O=A">Description</a><hr><img src="/icons/back.gif" alt="[PARENTDIR]">
<a href="/pub/fedora/linux/">Parent Directory</a>                             -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="30/">30/</a>                     2019-04-26 20:58    -
<hr></pre>
</body></html>"""

JEOS_PAGE = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
<html>
 <head>
  <title>Index of /data/assets/jeos</title>
 </head>
 <body>
<h1>Index of /data/assets/jeos</h1>
<table><tr><th><img src="/icons/blank.gif" alt="[ICO]"></th><th>
<a href="?C=N;O=D">Name</a></th><th><a href="?C=M;O=A">Last modified</a></th><th>
<a href="?C=S;O=A">Size</a></th><th><a href="?C=D;O=A">Description</a></th></tr><tr><th colspan="5"><hr></th></tr>
<tr><td valign="top"><img src="/icons/back.gif" alt="[DIR]"></td><td>
<a href="/data/assets/">Parent Directory</a></td><td>&nbsp;</td><td align="right">  - </td><td>&nbsp;</td></tr>
<tr><td valign="top"><img src="/icons/folder.gif" alt="[DIR]"></td><td><a href="27/">27/</a>
</td><td align="right">11-Dec-2017 17:43  </td><td align="right">  - </td><td>&nbsp;</td></tr>
<tr><th colspan="5"><hr></th></tr>
</table>
</body></html>"""

#: extracted from https://download.cirros-cloud.net/
CIRROS_PAGE = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
<html>
 <head>
  <title>Index of /</title>
 </head>
 <body>
<h1>Index of /</h1>
<pre>      <a href="?C=N;O=D">Name</a>
<a href="?C=M;O=A">Last modified</a>
 <a href="?C=S;O=A">Size</a>  <a href="?C=D;O=A">Description</a><hr>
 <a href="0.3.0/">0.3.0/</a>                                             2017-11-20 07:20    -

      <a href="0.4.0/">0.4.0/</a>                                             2017-11-19 20:01    -

<hr></pre>
</body></html>"""


class VMImagePlugin(unittest.TestCase):

    def _get_temporary_dirs_mapping_and_config(self):
        """
        Creates a temporary bogus base data dir
        And returns a dictionary containing the temporary data dir paths and
        the path to a configuration file contain those same settings
        """
        prefix = temp_dir_prefix(self)
        base_dir = tempfile.TemporaryDirectory(prefix=prefix)
        data_directory = os.path.join(base_dir.name, 'data')
        cache_directory = os.path.join(data_directory, 'cache')
        os.mkdir(data_directory)
        os.mkdir(cache_directory)
        mapping = {'base_dir': base_dir.name,
                   'data_dir': data_directory,
                   'cache_dirs': [cache_directory]}
        temp_settings = ('[datadir.paths]\n'
                         'base_dir = %(base_dir)s\n'
                         'data_dir = %(data_dir)s\n'
                         'cache_dirs = %(cache_dirs)s\n') % mapping
        config_file = tempfile.NamedTemporaryFile('w', dir=base_dir.name, delete=False)
        config_file.write(temp_settings)
        config_file.close()
        return base_dir, mapping, config_file.name

    @unittest.mock.patch('avocado.utils.vmimage.urlopen')
    def _create_test_files(self, urlopen_mock):
        with unittest.mock.patch('avocado.core.data_dir.settings', self.stg):
            expected_images = [{'name': 'Fedora', 'file': 'Fedora-Cloud-Base-{version}-{build}.{arch}.qcow2',
                                'url': FEDORA_PAGE},
                               {'name': 'JeOS', 'file': 'jeos-{version}-{arch}.qcow2.xz', 'url': JEOS_PAGE},
                               {'name': 'CirrOS', 'file': 'cirros-{version}-{arch}-disk.img', 'url': CIRROS_PAGE}
                               ]
            cache_dir = self.mapping.get('cache_dirs')[0]
            providers = [provider() for provider in vmimage_util.list_providers()]

            for provider in providers:
                for image in expected_images:
                    if image['name'] == provider.name:
                        urlread_mocked = unittest.mock.Mock(return_value=image["url"])
                        urlopen_mock.return_value = unittest.mock.Mock(read=urlread_mocked)
                        image['type'] = "vmimage"
                        image['version'] = provider.version
                        image['arch'] = provider.arch
                        image['build'] = "1234"
                        image['file'] = os.path.join(cache_dir, image['file'].format(
                            version=image['version'],
                            build=image['build'],
                            arch=image['arch']))
                        open(image["file"], "w").close()
                        create_metadata_file(image['file'], image)
            return sorted(expected_images, key=lambda i: i['name'])

    def setUp(self):
        (self.base_dir, self.mapping,
         self.config_file_path) = self._get_temporary_dirs_mapping_and_config()
        self.stg = Settings()
        with unittest.mock.patch('avocado.core.stgs', self.stg):
            import avocado.core
            avocado.core.register_core_options()
        self.stg.process_config_path(self.config_file_path)
        self.stg.merge_with_configs()
        self.expected_images = self._create_test_files()

    def test_list_downloaded_images(self):
        with unittest.mock.patch('avocado.core.data_dir.settings', self.stg):
            with unittest.mock.patch('avocado.utils.vmimage.ImageProviderBase.get_version'):
                images = sorted(vmimage_plugin.list_downloaded_images(), key=lambda i: i['name'])
                for index, image in enumerate(images):
                    for key in image:
                        self.assertEqual(self.expected_images[index][key], image[key],
                                         "Found image is different from the expected one")

    @skipOnLevelsInferiorThan(2)
    @unittest.skipIf(missing_binary('qemu-img'),
                     "QEMU disk image utility is required by the vmimage utility ")
    def test_download_image(self):
        """
        :avocado: tags=parallel:1
        """
        with unittest.mock.patch('avocado.core.data_dir.settings', self.stg):
            try:
                expected_image_info = vmimage_util.get_best_provider(name="CirrOS")
                image_info = vmimage_plugin.download_image(distro="CirrOS")
            except URLError as details:
                raise unittest.SkipTest(details)
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
