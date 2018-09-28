import unittest
try:
    from unittest import mock
except ImportError:
    import mock

from six.moves.urllib.error import HTTPError

from avocado.utils import vmimage


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

    @mock.patch('avocado.utils.vmimage.urlopen')
    def test_get_version(self, urlopen_mock):
        html_fixture = self.get_html_with_versions([10, 11, 12])
        urlread_mocked = mock.Mock(return_value=html_fixture)
        urlopen_mock.return_value = mock.Mock(read=urlread_mocked)
        base_image = vmimage.ImageProviderBase(version='[0-9]+', build=None, arch=None)
        self.assertEqual(base_image.get_version(), 12)

    @mock.patch('avocado.utils.vmimage.urlopen')
    def test_get_version_with_float_versions(self, urlopen_mock):
        html_fixture = self.get_html_with_versions([10.1, 10.3, 10.2])
        urlread_mocked = mock.Mock(return_value=html_fixture)
        urlopen_mock.return_value = mock.Mock(read=urlread_mocked)
        base_image = vmimage.ImageProviderBase(version=r'[0-9]+\.[0-9]+', build=None, arch=None)
        self.assertEqual(base_image.get_version(), 10.3)

    @mock.patch('avocado.utils.vmimage.urlopen')
    def test_get_version_with_string_versions(self, urlopen_mock):
        html_fixture = self.get_html_with_versions(['abc', 'abcd', 'abcde'])
        urlread_mocked = mock.Mock(return_value=html_fixture)
        urlopen_mock.return_value = mock.Mock(read=urlread_mocked)
        base_image = vmimage.ImageProviderBase(version=r'[\w]+', build=None, arch=None)
        self.assertEqual(base_image.get_version(), 'abcde')

    @mock.patch('avocado.utils.vmimage.urlopen')
    def test_get_version_from_bad_url_open(self, urlopen_mock):
        urlopen_mock.side_effect = HTTPError(None, None, None, None, None)
        base_image = vmimage.ImageProviderBase(version='[0-9]+', build=None, arch=None)

        with self.assertRaises(vmimage.ImageProviderError) as exc:
            base_image.get_version()

        self.assertIn('Cannot open', exc.exception.args[0])

    @mock.patch('avocado.utils.vmimage.urlopen')
    def test_get_version_versions_not_found(self, urlopen_mock):
        html_fixture = self.get_html_with_versions([])
        urlread_mocked = mock.Mock(return_value=html_fixture)
        urlopen_mock.return_value = mock.Mock(read=urlread_mocked)
        base_image = vmimage.ImageProviderBase(version='[0-9]+', build=None, arch=None)

        with self.assertRaises(vmimage.ImageProviderError) as exc:
            base_image.get_version()

        self.assertIn('Version not available at', exc.exception.args[0])

    def test_get_image_url_with_none_url_images_and_image_pattern(self):
        base_image = vmimage.ImageProviderBase(version='[0-9]+', build=None, arch=None)

        with self.assertRaises(vmimage.ImageProviderError) as exc:
            base_image.get_image_url()

        self.assertIn('attributes are required to get image url', exc.exception.args[0])


if __name__ == '__main__':
    unittest.main()
