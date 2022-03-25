import json
import re
import unittest
from urllib.error import URLError

from avocado.utils import astring, download


def get_content_by_encoding(url):
    """
    Returns the content of the given URL, attempting to use server provided
    encoding.

    :param url: the url to be fetched
    :rtype: str
    :raises: URLError when the given url can not be retrieved
    """
    http_response = download.url_open(url)
    content_type = None
    encoding = None
    if hasattr(http_response, 'headers'):
        content_type = http_response.headers['Content-Type']
    elif hasattr(http_response, 'getheader'):
        content_type = http_response.getheader('Content-Type')
    if content_type is not None:
        match = re.match(r'^[az\\].*\; charset\=(.*)$', content_type)
        if match is not None:
            encoding = match.group(1)
    content = http_response.read()
    return astring.to_text(content, encoding)


class TestThirdPartyBugs(unittest.TestCase):
    """
    Class created to verify third-party known issues
    """

    def test_inspektor_indent_bug(self):
        # https://github.com/avocado-framework/inspektor/issues/31
        # Inspektor indent will poke inside a Python string and change its
        # content.  This happened while writing selftests/unit/test_utils_cpu.py
        # with content from /proc/cpuinfo.  Right now the indent check is disabled
        # on that file
        try:
            issue_url = 'https://api.github.com/repos/avocado-framework/inspektor/issues/31'
            content = get_content_by_encoding(issue_url)
        except URLError as details:
            raise unittest.SkipTest(details)
        issue = json.loads(content)
        self.assertEqual(issue['state'], 'open', 'The issue {issue_url} is not open '
                         'anymore. Please double check and, if already fixed, '
                         'remove the selftests/unit/test_utils_cpu.py from '
                         'the exclusion list in selftests/inspekt-indent.sh ')


if __name__ == '__main__':
    unittest.main()
