import re
import json
import unittest

try:
    from urllib2 import URLError
except ImportError:
    from urllib.error import URLError

from avocado.utils import download


def get_content_by_encoding(url):
    """
    Returns the content of the given URL, attempting to use server provided
    encoding.

    :rtype: str
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
    if hasattr(content, 'decode'):
        if encoding is not None:
            content = content.decode(encoding)
        else:
            content = content.decode()  # Python default encoding
    return content


class TestThirdPartyBugs(unittest.TestCase):
    """
    Class created to verify third-party known issues
    """

    def test_paramiko_ecsda_bug(self):
        # https://github.com/paramiko/paramiko/issues/243
        # Problems with using ECDSA known_hosts keys when negotiation also
        # accepts RSA or DSS keys
        try:
            issue_url = 'https://api.github.com/repos/paramiko/paramiko/issues/243'
            content = get_content_by_encoding(issue_url)
            issue = json.loads(content)
            self.assertEqual(issue['state'], 'open', 'The issue %s is not open '
                             'anymore. Please double check and, if already fixed, '
                             'change the avocado.conf option '
                             '"reject_unknown_hosts" defaults to True.' %
                             'https://github.com/paramiko/paramiko/issues/243')
        except URLError as details:
            raise unittest.SkipTest(details)

    def test_inspektor_indent_bug(self):
        # https://github.com/avocado-framework/inspektor/issues/31
        # Inspektor indent will poke inside a Python string and change its
        # content.  This happened while writing selftests/unit/test_utils_cpu.py
        # with content from /proc/cpuinfo.  Right now the indent check is disabled
        # on that file
        try:
            issue_url = 'https://api.github.com/repos/avocado-framework/inspektor/issues/31'
            content = get_content_by_encoding(issue_url)
            issue = json.loads(content)
            self.assertEqual(issue['state'], 'open', 'The issue %s is not open '
                             'anymore. Please double check and, if already fixed, '
                             'remove the selftests/unit/test_utils_cpu.py from '
                             'the exclusion list of indent in selftests/checkall' %
                             'https://github.com/avocado-framework/inspektor/issues/31')
        except URLError as details:
            raise unittest.SkipTest(details)


if __name__ == '__main__':
    unittest.main()
