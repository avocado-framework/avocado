import unittest

from avocado.utils import aurl


class TestAUrl(unittest.TestCase):
    def test_valid_urls(self):
        valid_urls = [
            "http://www.example.com",
            "https://www.example.com/path",
            "ftp://ftp.example.com",
            "git://github.com/user/repo.git",
        ]
        for url in valid_urls:
            self.assertTrue(aurl.is_url(url), f"Expected {url} to be a valid URL")

        invalid_urls = [
            "www.example.com",
            "htt://example",
            "file:///path/to/file",
        ]
        for url in invalid_urls:
            self.assertFalse(aurl.is_url(url), f"Expected {url} to be an invalid URL")

        non_urls = [
            "/path/to/file",
            "not a url",
            "",
        ]
        for path in non_urls:
            self.assertFalse(aurl.is_url(path), f"Expected {path} to not be a URL")
