import unittest.mock
from urllib.error import HTTPError

from avocado.utils import vmimage

from .. import setup_avocado_loggers


setup_avocado_loggers()


class VMImage(unittest.TestCase):

    def test_list_providers(self):
        self.assertIsNotNone(vmimage.list_providers())

    def test_concrete_providers_have_name(self):
        for provider in vmimage.list_providers():
            self.assertTrue(hasattr(provider, 'name'))


class VMImageHtmlParser(unittest.TestCase):
    def setUp(self):
        pattern = '^[0-9]+/$'
        self.parser = vmimage.VMImageHtmlParser(pattern)

    def test_handle_starttag_no_a(self):
        self.parser.feed('<html><head><title>Test</title></head>'
                         '<body><h1>VMImage</h1></body></html>')
        self.assertFalse(self.parser.items)

    def test_handle_starttag_with_a_pattern_not_match(self):
        self.parser.feed('<html><head><title>Test</title></head>'
                         '<body><a href="https://test.com/" /></body></html>')
        self.assertFalse(self.parser.items)

    def test_handle_starttag_with_a_pattern_match(self):
        version = '12'
        self.parser.feed('<html><head><title>Test</title></head>'
                         '<body><a href="%s/" /></body></html>' % version)
        self.assertTrue(self.parser.items)
        self.assertEqual(self.parser.items[0], version)

    def test_handle_starttag_with_a_pattern_match_multiple(self):
        versions = ['12', '13', '14']
        links = ['<a href="%s/" />' % version for version in versions]
        html = ('<html><head><title>Test</title></head>'
                '<body>%s</body></html>' % ''.join(links))
        self.parser.feed(html)
        self.assertTrue(self.parser.items)
        self.assertEqual(len(self.parser.items), len(versions))
        self.assertTrue(all(version in self.parser.items for version in versions))


class ImageProviderBase(unittest.TestCase):
    @staticmethod
    def get_html_with_versions(versions):
        html = '<html><head><title>Test</title></head><body>%s</body></html>'
        return html % ''.join(['<a href="%s/" />' % v for v in versions])

    @unittest.mock.patch('avocado.utils.vmimage.urlopen')
    def test_get_version(self, urlopen_mock):
        html_fixture = self.get_html_with_versions([10, 11, 12])
        urlread_mocked = unittest.mock.Mock(return_value=html_fixture)
        urlopen_mock.return_value = unittest.mock.Mock(read=urlread_mocked)
        base_image = vmimage.ImageProviderBase(version='[0-9]+', build=None, arch=None)
        self.assertEqual(base_image.get_version(), 12)

    @unittest.mock.patch('avocado.utils.vmimage.urlopen')
    def test_get_version_with_float_versions(self, urlopen_mock):
        html_fixture = self.get_html_with_versions([10.1, 10.3, 10.2])
        urlread_mocked = unittest.mock.Mock(return_value=html_fixture)
        urlopen_mock.return_value = unittest.mock.Mock(read=urlread_mocked)
        base_image = vmimage.ImageProviderBase(version=r'[0-9]+\.[0-9]+', build=None, arch=None)
        self.assertEqual(base_image.get_version(), 10.3)

    @unittest.mock.patch('avocado.utils.vmimage.urlopen')
    def test_get_version_with_string_versions(self, urlopen_mock):
        html_fixture = self.get_html_with_versions(['abc', 'abcd', 'abcde'])
        urlread_mocked = unittest.mock.Mock(return_value=html_fixture)
        urlopen_mock.return_value = unittest.mock.Mock(read=urlread_mocked)
        base_image = vmimage.ImageProviderBase(version=r'[\w]+', build=None, arch=None)
        self.assertEqual(base_image.get_version(), 'abcde')

    @unittest.mock.patch('avocado.utils.vmimage.urlopen')
    def test_get_version_from_bad_url_open(self, urlopen_mock):
        urlopen_mock.side_effect = HTTPError(None, None, None, None, None)
        base_image = vmimage.ImageProviderBase(version='[0-9]+', build=None, arch=None)

        with self.assertRaises(vmimage.ImageProviderError) as exc:
            base_image.get_version()

        self.assertIn('Cannot open', exc.exception.args[0])

    @unittest.mock.patch('avocado.utils.vmimage.urlopen')
    def test_get_version_versions_not_found(self, urlopen_mock):
        html_fixture = self.get_html_with_versions([])
        urlread_mocked = unittest.mock.Mock(return_value=html_fixture)
        urlopen_mock.return_value = unittest.mock.Mock(read=urlread_mocked)
        base_image = vmimage.ImageProviderBase(version='[0-9]+', build=None, arch=None)

        with self.assertRaises(vmimage.ImageProviderError) as exc:
            base_image.get_version()

        self.assertIn('Version not available at', exc.exception.args[0])

    def test_get_image_url_with_none_url_images_and_image_pattern(self):
        base_image = vmimage.ImageProviderBase(version='[0-9]+', build=None, arch=None)

        with self.assertRaises(vmimage.ImageProviderError) as exc:
            base_image.get_image_url()

        self.assertIn('attributes are required to get image url', exc.exception.args[0])


class OpenSUSEImageProvider(unittest.TestCase):
    def setUp(self):
        self.suse_available_versions = ['Leap_15.0', 'Leap_42.1', 'Leap_42.2', 'Leap_42.3']
        self.base_images_url = 'https://download.opensuse.org/repositories/Cloud:/Images:/Leap_15.0/images/'

    @staticmethod
    def get_html_with_image_link(image_link):
        return '''
            <a href="openSUSE-Leap-15.0-OpenStack.x86_64-0.0.4-Buildlp150.12.30.packages"></a>
            <a href="%s"></a>
            <a href="openSUSE-Leap-15.0-OpenStack.x86_64-0.0.4-Buildlp150.12.30.qcow2.sha256"></a>
        ''' % image_link

    def test_get_best_version_default(self):
        suse_latest_version = 15.0
        suse_provider = vmimage.OpenSUSEImageProvider(arch='x86_64')
        self.assertEqual(suse_provider.get_best_version(self.suse_available_versions),
                         suse_latest_version)

    def test_get_best_version_leap_4_series(self):
        suse_latest_version = 42.3
        suse_provider = vmimage.OpenSUSEImageProvider(version='4(.)*', arch='x86_64')
        self.assertEqual(suse_provider.get_best_version(self.suse_available_versions),
                         suse_latest_version)

    @unittest.mock.patch('avocado.utils.vmimage.urlopen')
    def test_get_image_url(self, urlopen_mock):
        image = 'openSUSE-Leap-15.0-OpenStack.x86_64-0.0.4-Buildlp150.12.30.qcow2'
        html_fixture = self.get_html_with_image_link(image)
        urlread_mocked = unittest.mock.Mock(return_value=html_fixture)
        urlopen_mock.return_value = unittest.mock.Mock(read=urlread_mocked)
        expected_image_url = self.base_images_url + image

        suse_provider = vmimage.OpenSUSEImageProvider(arch='x86_64')
        suse_provider.get_version = unittest.mock.Mock(return_value='15.0')
        self.assertEqual(suse_provider.get_image_url(), expected_image_url)

    @unittest.mock.patch('avocado.utils.vmimage.urlopen')
    def test_get_image_url_defining_build(self, urlopen_mock):
        image = 'openSUSE-Leap-15.0-OpenStack.x86_64-1.1.1-Buildlp111.11.11.qcow2'
        html_fixture = self.get_html_with_image_link(image)
        urlread_mocked = unittest.mock.Mock(return_value=html_fixture)
        urlopen_mock.return_value = unittest.mock.Mock(read=urlread_mocked)
        expected_image_url = self.base_images_url + image

        suse_provider = vmimage.OpenSUSEImageProvider(build='1.1.1-Buildlp111.11.11',
                                                      arch='x86_64')
        suse_provider.get_version = unittest.mock.Mock(return_value='15.0')
        self.assertEqual(suse_provider.get_image_url(), expected_image_url)


class FedoraImageProvider(unittest.TestCase):

    #: extracted from https://dl.fedoraproject.org/pub/fedora/linux/releases/
    VERSION_LISTING = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
<html>
 <head>
  <title>Index of /pub/fedora/linux/releases</title>
 </head>
 <body>
<h1>Index of /pub/fedora/linux/releases</h1>
<pre><img src="/icons/blank.gif" alt="Icon "> <a href="?C=N;O=D">Name</a>                    <a href="?C=M;O=A">Last modified</a>      <a href="?C=S;O=A">Size</a>  <a href="?C=D;O=A">Description</a><hr><img src="/icons/back.gif" alt="[PARENTDIR]"> <a href="/pub/fedora/linux/">Parent Directory</a>                             -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="10/">10/</a>                     2013-04-25 08:48    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="11/">11/</a>                     2013-04-25 08:48    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="12/">12/</a>                     2013-04-25 08:48    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="13/">13/</a>                     2013-04-25 08:48    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="14/">14/</a>                     2013-04-25 08:48    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="15/">15/</a>                     2013-09-05 19:09    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="16/">16/</a>                     2013-09-05 19:20    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="17/">17/</a>                     2013-09-05 19:25    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="18/">18/</a>                     2015-02-24 00:45    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="19/">19/</a>                     2015-02-24 00:57    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="20/">20/</a>                     2015-07-16 17:32    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="21/">21/</a>                     2016-05-17 20:38    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="22/">22/</a>                     2017-09-21 17:00    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="23/">23/</a>                     2017-09-21 17:27    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="24/">24/</a>                     2017-09-22 17:36    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="25/">25/</a>                     2018-07-09 23:26    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="26/">26/</a>                     2018-07-09 23:31    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="27/">27/</a>                     2019-04-01 20:08    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="28/">28/</a>                     2019-09-02 20:37    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="29/">29/</a>                     2018-10-26 17:27    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="30/">30/</a>                     2019-04-26 20:58    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="7/">7/</a>                      2016-05-21 03:28    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="8/">8/</a>                      2016-05-21 02:12    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="9/">9/</a>                      2013-04-25 08:48    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="test/">test/</a>                   2019-07-16 14:04    -
<hr></pre>
</body></html>"""

    @unittest.mock.patch('avocado.utils.vmimage.urlopen')
    def test_get_image_parameters_match(self, urlopen_mock):
        expected_version = '30'
        expected_arch = 'x86_64'
        expected_build = '1234'
        urlread_mocked = unittest.mock.Mock(return_value=self.VERSION_LISTING)
        urlopen_mock.return_value = unittest.mock.Mock(read=urlread_mocked)
        provider = vmimage.FedoraImageProvider(expected_version, expected_build,
                                               expected_arch)
        image = "Fedora-Cloud-Base-%s-%s.%s.qcow2" % (expected_version, expected_build,
                                                      expected_arch)
        parameters = provider.get_image_parameters(image)
        self.assertEqual(expected_version, parameters['version'])
        self.assertEqual(expected_build, parameters['build'])
        self.assertEqual(expected_arch, parameters['arch'])

    @unittest.mock.patch('avocado.utils.vmimage.urlopen')
    def test_get_image_parameters_not_match(self, urlopen_mock):
        urlread_mocked = unittest.mock.Mock(return_value=self.VERSION_LISTING)
        urlopen_mock.return_value = unittest.mock.Mock(read=urlread_mocked)

        provider = vmimage.FedoraImageProvider('30', '1234',
                                               'x86_64')
        image = 'openSUSE-Leap-15.0-OpenStack.x86_64-1.1.1-Buildlp111.11.11.qcow2'
        parameters = provider.get_image_parameters(image)
        self.assertIsNone(parameters, "get_image_parameters() finds parameters "
                                      "where there should be none")


if __name__ == '__main__':
    unittest.main()
