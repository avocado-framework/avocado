import json
import unittest

from avocado.utils import download


class CirrusCI(unittest.TestCase):

    def test(self):
        url = 'https://api.cirrus-ci.com/github/avocado-framework/avocado.json'
        http_response = download.url_open(url)
        self.assertEqual(http_response.code, 200)
        content = http_response.read()
        data = json.loads(content)
        self.assertIn('status', data)
        self.assertEqual(data['status'], 'passing')
