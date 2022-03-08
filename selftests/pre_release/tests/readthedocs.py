import json
import os
import urllib.request

from avocado import Test


class ReadtheDocs(Test):

    def test(self):
        token_from_env = os.environ.get('AVOCADO_READTHEDOCS_TOKEN', None)
        token = self.params.get('token', default=token_from_env)
        if not token:
            self.fail('Please provide a readthedocs.org token either '
                      'via the "token" parameter or the '
                      '"AVOCADO_READTHEDOCS_TOKEN" environment variable')

        headers = {'Authorization': f'Token {token}',
                   # readthedocs.org throws a 403 without User-Agent header
                   'User-Agent': ''}

        url = ('https://readthedocs.org/api/v3/projects/avocado-framework/'
               'builds/?limit=1&?version=latest')

        http_request = urllib.request.Request(url, headers=headers)
        http_response = urllib.request.urlopen(http_request)
        content = http_response.read()
        data = json.loads(content)
        self.assertTrue(data['results'][0]['success'])
